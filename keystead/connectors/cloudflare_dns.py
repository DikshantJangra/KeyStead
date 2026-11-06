"""dns.add_record / dns.delete_record / dns.list_records via cloudflare-python.

Token scope: Zone > DNS > Edit, on the listed zones only."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from cloudflare import AsyncCloudflare
from pydantic import AfterValidator, BaseModel, Field, field_validator

from .base import ConnectorError, Params, Receipt


def _zone(v: str) -> str:
    return v.strip().rstrip(".").lower()


Zone = Annotated[str, AfterValidator(_zone)]
RecordType = Literal["A", "AAAA", "CNAME", "TXT", "MX", "CAA", "SRV", "NS"]


class AddRecord(Params):
    zone: Zone = Field(description="the zone (domain) to change, e.g. clientsite.com")
    type: RecordType = Field(description="record type")
    name: str = Field(min_length=1, description='"@" for the apex, else the subdomain label')
    content: str = Field(min_length=1, max_length=2048, description="record value")
    ttl: int = Field(1, description="seconds; 1 means automatic")
    proxied: bool | None = Field(None, description="A/AAAA/CNAME only: proxy through Cloudflare")
    priority: int | None = Field(None, ge=0, le=65535, description="MX only")

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        if any(c.isspace() for c in v):
            raise ValueError("name cannot contain whitespace or newlines")
        return v

    @field_validator("ttl")
    @classmethod
    def _ttl(cls, v: int) -> int:
        if v != 1 and not 30 <= v <= 86400:
            raise ValueError("ttl must be 1 (auto) or 30..86400")
        return v


class DeleteRecord(Params):
    zone: Zone = Field(description="the zone the record is in")
    record_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9]+$", description="id from dns.list_records")


class ListRecords(Params):
    zone: Zone = Field(description="the zone to list")
    type: RecordType | None = Field(None, description="only this type")
    name: str | None = Field(None, description="only this full name, e.g. www.clientsite.com")


def fqdn(name: str, zone: str) -> str:
    name = name.strip().rstrip(".").lower()
    if name in ("@", "", zone):
        return zone
    return name if name.endswith("." + zone) else f"{name}.{zone}"


def _ttl_label(ttl: int) -> str:
    return "TTL auto" if ttl == 1 else f"TTL {ttl}s"


class CloudflareDNS:
    name = "cloudflare_dns"
    actions: dict[str, type[BaseModel]] = {
        "dns.add_record": AddRecord,
        "dns.delete_record": DeleteRecord,
        "dns.list_records": ListRecords,
    }
    descriptions = {
        "dns.add_record": "Add one DNS record",
        "dns.delete_record": "Delete one DNS record by id",
        "dns.list_records": "List DNS records in a zone (read-only)",
    }

    def __init__(self, secret_name: str, zones: list[str] | None, client_factory=AsyncCloudflare):
        self.secret_name = secret_name
        self.zones = {_zone(z) for z in zones} if zones else None
        self.client_factory = client_factory

    def check(self, action: str, p: Any) -> None:
        if self.zones is not None and p.zone not in self.zones:
            raise ConnectorError(f"zone {p.zone} is not managed by this gate")

    def preview(self, action: str, p: Any) -> str:
        if action == "dns.add_record":
            extra = ""
            if p.priority is not None:
                extra += f"  priority {p.priority}"
            if p.proxied is not None:
                extra += "  proxied" if p.proxied else "  DNS only"
            return f'{p.type}  {p.name}  "{p.content}"  {_ttl_label(p.ttl)}{extra}'
        if action == "dns.delete_record":
            return f"delete record {p.record_id}"
        if action == "dns.list_records":
            return "list records" + (f" type {p.type}" if p.type else "") + (f" name {p.name}" if p.name else "")
        raise ConnectorError(f"unknown action {action}")

    async def _zone_id(self, cf: AsyncCloudflare, zone: str) -> str:
        async for z in cf.zones.list(name=zone):
            return z.id
        raise ConnectorError(f"zone {zone} not found for this token")

    async def execute(self, action: str, p: Any, secret: str) -> Receipt:
        cf = self.client_factory(api_token=secret)
        zid = await self._zone_id(cf, p.zone)
        if action == "dns.add_record":
            kwargs: dict[str, Any] = dict(
                zone_id=zid, type=p.type, name=fqdn(p.name, p.zone), content=p.content, ttl=p.ttl
            )
            if p.proxied is not None:
                kwargs["proxied"] = p.proxied
            if p.priority is not None:
                kwargs["priority"] = p.priority
            r = await cf.dns.records.create(**kwargs)
            return Receipt(
                ok=True,
                summary=f"{p.type} {p.name} is live, record id {r.id[:4]}…",
                external_id=r.id,
                raw=r.model_dump(mode="json"),
            )
        if action == "dns.delete_record":
            await cf.dns.records.delete(p.record_id, zone_id=zid)
            return Receipt(ok=True, summary=f"record {p.record_id} deleted", external_id=p.record_id, raw={})
        if action == "dns.list_records":
            kwargs = {"zone_id": zid}
            if p.type:
                kwargs["type"] = p.type
            if p.name:
                kwargs["name"] = {"exact": fqdn(p.name, p.zone)}
            rows = []
            async for rec in cf.dns.records.list(**kwargs):
                rows.append({"id": rec.id, "type": rec.type, "name": rec.name, "content": getattr(rec, "content", None), "ttl": rec.ttl})
                if len(rows) >= 50:
                    break
            lines = "\n".join(f"  {r['id']}  {r['type']}  {r['name']}  {r['content']}" for r in rows) or "  (none)"
            return Receipt(ok=True, summary=f"{len(rows)} record(s) in {p.zone}:\n{lines}", raw={"records": rows})
        raise ConnectorError(f"unknown action {action}")
