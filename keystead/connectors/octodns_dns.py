"""dns.add_record / dns.delete_record / dns.list_records through any octoDNS provider.

Config:
  octodns_dns:
    secret: route53_secret           # vault key
    provider: octodns_route53.Route53Provider
    secret_kwarg: secret_access_key  # provider kwarg that receives the secret
    options: {access_key_id: AKIA...}  # other, non-secret provider kwargs
    zones: [clientsite.com]

octoDNS has no record ids, so record_id is "TYPE:name", e.g. "TXT:@" or "CNAME:www".
Deleting removes that whole record set. Install with `uv sync --extra octodns`
plus the provider package (octodns-route53, octodns-ns1, ...)."""

from __future__ import annotations

import asyncio
import importlib
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, Field, field_validator

from .base import ConnectorError, Params, Receipt


def _zone(v: str) -> str:
    return v.strip().rstrip(".").lower()


Zone = Annotated[str, AfterValidator(_zone)]
OType = Literal["A", "AAAA", "CNAME", "TXT", "MX"]


class AddRecord(Params):
    zone: Zone = Field(description="the zone (domain) to change")
    type: OType = Field(description="record type")
    name: str = Field(min_length=1, description='"@" for the apex, else the subdomain label')
    content: str = Field(min_length=1, max_length=2048, description="record value")
    ttl: int = Field(1, description="seconds; 1 means provider default (3600)")
    priority: int | None = Field(None, ge=0, le=65535, description="MX only")

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        if any(c.isspace() for c in v):
            raise ValueError("name cannot contain whitespace or newlines")
        return v


class DeleteRecord(Params):
    zone: Zone = Field(description="the zone the record is in")
    record_id: str = Field(pattern=r"^(A|AAAA|CNAME|TXT|MX):[A-Za-z0-9_.@*-]+$", description='"TYPE:name" from dns.list_records')


class ListRecords(Params):
    zone: Zone = Field(description="the zone to list")
    type: OType | None = Field(None, description="only this type")
    name: str | None = Field(None, description="only this label")


def _label(name: str, zone: str) -> str:
    n = name.strip().rstrip(".").lower()
    if n in ("@", "", zone):
        return ""
    if n.endswith("." + zone):
        n = n[: -len(zone) - 1]
    return n


def _value(type_: str, content: str, priority: int | None) -> Any:
    if type_ == "TXT":
        return content.replace("\\;", ";").replace(";", "\\;")
    if type_ == "CNAME":
        return content if content.endswith(".") else content + "."
    if type_ == "MX":
        ex = content if content.endswith(".") else content + "."
        return {"preference": priority or 10, "exchange": ex}
    return content


class OctoDNS:
    name = "octodns_dns"
    actions: dict[str, type[BaseModel]] = {
        "dns.add_record": AddRecord,
        "dns.delete_record": DeleteRecord,
        "dns.list_records": ListRecords,
    }
    descriptions = {
        "dns.add_record": "Add one DNS record (value is merged into an existing set)",
        "dns.delete_record": 'Delete one record set by "TYPE:name"',
        "dns.list_records": "List DNS records in a zone (read-only)",
    }

    def __init__(self, secret_name: str, zones: list[str] | None, provider: str, secret_kwarg: str, options: dict | None = None, provider_factory=None):
        self.secret_name = secret_name
        self.zones = {_zone(z) for z in zones} if zones else None
        self.provider_path = provider
        self.secret_kwarg = secret_kwarg
        self.options = options or {}
        self.provider_factory = provider_factory

    def _provider(self, secret: str):
        if self.provider_factory:
            return self.provider_factory(secret)
        mod, _, cls = self.provider_path.rpartition(".")
        try:
            klass = getattr(importlib.import_module(mod), cls)
        except (ImportError, AttributeError) as e:
            raise ConnectorError(f"octoDNS provider {self.provider_path} not installed") from e
        return klass("keystead", **{**self.options, self.secret_kwarg: secret})

    def check(self, action: str, p: Any) -> None:
        if self.zones is not None and p.zone not in self.zones:
            raise ConnectorError(f"zone {p.zone} is not managed by this gate")

    def preview(self, action: str, p: Any) -> str:
        if action == "dns.add_record":
            ttl = "TTL default" if p.ttl == 1 else f"TTL {p.ttl}s"
            pr = f"  priority {p.priority}" if p.priority is not None else ""
            return f'{p.type}  {p.name}  "{p.content}"  {ttl}{pr}'
        if action == "dns.delete_record":
            return f"delete record set {p.record_id}"
        if action == "dns.list_records":
            return "list records"
        raise ConnectorError(f"unknown action {action}")

    def _run(self, action: str, p: Any, secret: str) -> Receipt:
        from octodns.record import Record
        from octodns.zone import Zone as OZone

        provider = self._provider(secret)
        existing = OZone(p.zone + ".", [])
        provider.populate(existing, target=True, lenient=True)

        if action == "dns.list_records":
            rows = []
            for r in sorted(existing.records, key=lambda r: (r.name, r._type)):
                if p.type and r._type != p.type:
                    continue
                if p.name is not None and r.name != _label(p.name, p.zone):
                    continue
                vals = getattr(r, "values", None) or [getattr(r, "value", None)]
                rows.append({"id": f"{r._type}:{r.name or '@'}", "type": r._type, "name": r.name or "@", "content": [str(v) for v in vals], "ttl": r.ttl})
            lines = "\n".join(f"  {r['id']}  {', '.join(r['content'])}" for r in rows) or "  (none)"
            return Receipt(ok=True, summary=f"{len(rows)} record set(s) in {p.zone}:\n{lines}", raw={"records": rows})

        desired = existing.copy()
        if action == "dns.add_record":
            label = _label(p.name, p.zone)
            value = _value(p.type, p.content, p.priority)
            ttl = 3600 if p.ttl == 1 else p.ttl
            current = next((r for r in existing.records if r.name == label and r._type == p.type), None)
            if p.type == "CNAME":
                data = {"type": "CNAME", "ttl": ttl, "value": value}
            else:
                old = [] if current is None else list(current.values)
                data = {"type": p.type, "ttl": ttl, "values": old if value in old else [*old, value]}
            desired.add_record(Record.new(desired, label, data, lenient=True), replace=True)
            rid = f"{p.type}:{label or '@'}"
        elif action == "dns.delete_record":
            type_, _, name = p.record_id.partition(":")
            label = _label(name, p.zone)
            current = next((r for r in desired.records if r.name == label and r._type == type_), None)
            if current is None:
                raise ConnectorError(f"no {type_} record named {name} in {p.zone}")
            desired.remove_record(current)
            rid = p.record_id
        else:
            raise ConnectorError(f"unknown action {action}")

        plan = provider.plan(desired)
        if plan is None or not plan.changes:
            return Receipt(ok=True, summary=f"{rid} already as requested, nothing changed", external_id=rid, raw={})
        n = provider.apply(plan)
        verb = "is live" if action == "dns.add_record" else "deleted"
        return Receipt(ok=True, summary=f"{rid} {verb} ({n} change(s))", external_id=rid, raw={"changes": n})

    async def execute(self, action: str, p: Any, secret: str) -> Receipt:
        return await asyncio.to_thread(self._run, action, p, secret)
