"""The @keystead gate: read room events, route proposals and approvals. No LLM."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from . import cards
from .approvals import Rejected, check_proposal, check_sender, parse_decision
from .audit import Ledger
from .config import KeysteadConfig
from .connectors.base import Connector, Receipt
from .help import catalog
from .policy import evaluate
from .proposals import Proposal, ProposalError, Store, now_ms, parse_block, payload_hash
from .vault import Redactor, Vault

log = logging.getLogger("keystead.gate")
DAY_MS = 24 * 3600 * 1000


class GateStartError(Exception):
    pass


@dataclass
class People:
    """Switch transport sender ids, filled in as identities are pinned."""

    approvers: set[str] = field(default_factory=set)
    proposers: set[str] = field(default_factory=set)
    agents: set[str] = field(default_factory=set)
    names: dict[str, str] = field(default_factory=dict)
    self_id: str | None = None


def build_roster(cfg: KeysteadConfig, participants: list[dict], strict: bool) -> dict[str, str]:
    """name (casefolded) -> "agent" | "user" | "ambiguous", from list_participants.

    Refuses an approver who is an agent, missing, or ambiguous, and a gate that is
    itself a proposer or approver."""
    roster: dict[str, str] = {}
    for p in participants:
        kind = "agent" if p.get("type") == "agent" else "user"
        for n in {(p.get("name") or "").casefold(), (p.get("alias") or "").casefold()} - {""}:
            roster[n] = kind if roster.get(n, kind) == kind else "ambiguous"
    gate = cfg.gate.name.casefold()
    if gate in cfg.people.approvers or gate in cfg.people.proposers:
        raise GateStartError("the gate cannot be its own proposer or approver")
    for name in cfg.people.approvers:
        kind = roster.get(name)
        if kind is None and strict:
            raise GateStartError(f"approver {name!r} is not in the room")
        if kind == "agent":
            raise GateStartError(f"approver {name!r} is an agent; agents can never approve")
        if kind == "ambiguous":
            raise GateStartError(f"approver {name!r} names both a person and an agent in this room")
    for name in cfg.people.proposers:
        if name not in roster:
            log.warning("proposer %r is not in the room yet", name)
    return roster


class Gate:
    def __init__(self, cfg: KeysteadConfig, client: Any, store: Store, ledger: Ledger, vault: Vault, connectors: dict[str, Connector]):
        self.cfg = cfg
        self.client = client
        self.store = store
        self.ledger = ledger
        self.vault = vault
        self.connectors = connectors
        self.room_id: str | None = None
        self.people = People()
        self.roster: dict[str, str] = {}
        self.my_events: set[str] = set()
        self._last_refresh = 0.0
        name = re.escape(cfg.gate.name)
        self.help_re = re.compile(rf"(?<![\w@])@{name}\s+help\b", re.I)
        self.propose_re = re.compile(rf"(?<![\w@])@{name}\s+propose\b", re.I)
        self.command_re = re.compile(rf"\s*@?{name}\s+(status|audit|pause|resume|revoke)\s*", re.I)

    # ---------- startup ----------

    async def resolve_room(self) -> str:
        rooms = await self.client.list_rooms()
        match = [r for r in rooms if r.get("name") == self.cfg.switch.room or r.get("room_id") == self.cfg.switch.room]
        if not match:
            raise GateStartError(f"room {self.cfg.switch.room!r} not found; add @{self.cfg.gate.name} to it first (have: {[r.get('name') for r in rooms]})")
        self.room_id = match[0]["room_id"]
        return self.room_id

    async def start(self) -> None:
        """Called once the event stream is open: claim the room, check people, announce."""
        assert self.room_id
        await self.client.connect(self.room_id)
        self.roster = build_roster(self.cfg, await self.client.list_participants(self.room_id), strict=True)
        self._last_refresh = time.monotonic()
        for name, sid in self.cfg.people.pins.items():
            kind = self.roster.get(name, "user")
            self.store.force_pin(sid, name, kind)
        self.people.self_id = self.store.get_state("self_id") or None
        state = "PAUSED" if self.paused else "running"
        await self.say(
            f"{self.cfg.gate.name} online ({state}). Only {', '.join(self.cfg.people.approvers)} can approve. "
            f"Send @{self.cfg.gate.name} help for the action catalog."
        )

    async def refresh_roster(self) -> None:
        if time.monotonic() - self._last_refresh < 5 or not self.room_id:
            return
        self._last_refresh = time.monotonic()
        try:
            self.roster = build_roster(self.cfg, await self.client.list_participants(self.room_id), strict=False)
        except GateStartError as e:
            log.error("participant refresh refused, keeping previous roster: %s", e)

    async def identify(self, m: dict) -> tuple[str, str] | None:
        """Map a message's transport sender id to a room participant (name, kind).

        Switch's participant ids and message sender ids are different id spaces, so
        the gate pins sender id -> participant name on first sight (names are unique
        per messaging app) and refuses any later, different id for a pinned name."""
        sid = m.get("sender") or ""
        pinned = self.store.identity(sid)
        if pinned:
            return pinned
        if m.get("sender_kind") == "platform" or m.get("on_behalf_of"):
            return None
        name = (m.get("sender_name") or "").casefold()
        if name not in self.roster:
            await self.refresh_roster()
        kind = self.roster.get(name)
        if kind in (None, "ambiguous"):
            return None
        said = m.get("sender_kind")
        if said in ("agent", "user") and said != kind:
            log.error("sender %s says it is %s but %s is a %s in this room", sid, said, name, kind)
            return None
        other = self.store.id_for_name(name)
        if other and other != sid:
            self.ledger.append("rejected", None, sid, name, None, f"identity conflict: {name} is pinned to another sender id")
            log.error("identity conflict for %s: %s is pinned, %s refused", name, other, sid)
            return None
        self.store.pin(sid, name, kind)
        self.ledger.append("pinned", None, sid, name, None, kind)
        return name, kind

    def _learn(self, sid: str, ident: tuple[str, str] | None, m: dict) -> None:
        if m.get("sender_kind") == "agent":
            self.people.agents.add(sid)
        if not ident:
            return
        name, kind = ident
        self.people.names[sid] = name
        if kind == "agent":
            self.people.agents.add(sid)
        if name in self.cfg.people.approvers and kind == "user":
            self.people.approvers.add(sid)
        if name in self.cfg.people.proposers:
            self.people.proposers.add(sid)

    # ---------- state ----------

    @property
    def paused(self) -> bool:
        return self.store.get_state("paused") == "1"

    @property
    def revoked(self) -> bool:
        return self.store.get_state("revoked") == "1"

    # ---------- output ----------

    async def say(self, body: str, thread_id: str | None = None, targets: list[str] | None = None) -> None:
        assert self.room_id
        clean = Redactor(self.vault.all_values())(body)
        res = await self.client.post(self.room_id, clean, thread_id, targets=targets)
        if isinstance(res, dict) and res.get("event_id"):
            self.my_events.add(res["event_id"])

    def _redact(self, obj):
        return Redactor(self.vault.all_values()).scrub(obj)

    def _name(self, pid: str) -> str:
        return self.people.names.get(pid, pid)

    def _proposer_target(self, p: Proposal) -> list[str]:
        return [p.proposer_name]

    def _approver_targets(self) -> list[str]:
        return list(self.cfg.people.approvers)

    # ---------- event routing ----------

    async def handle(self, event: dict) -> None:
        if event.get("type") != "message" or event.get("room_id") != self.room_id:
            return
        m = event["payload"]
        sender = m.get("sender") or ""
        body = (m.get("body") or "").strip()
        thread = m.get("thread_id")
        sender_name = m.get("sender_name") or sender
        if m.get("message_id") in self.my_events:
            self.my_events.discard(m["message_id"])
            if self.people.self_id != sender:
                self.people.self_id = sender
                self.store.set_state("self_id", sender)
            return
        if sender == self.people.self_id or (self.people.self_id is None and sender_name.casefold() == self.cfg.gate.name.casefold()):
            return
        self._learn(sender, await self.identify(m), m)

        if self.help_re.search(body):
            await self.say(catalog(self.cfg.gate.name, self.connectors, self.cfg.rules), thread)
            return
        if self.propose_re.search(body):
            await self.on_propose(m, sender, sender_name, body, thread)
            return
        decision = parse_decision(body)
        if decision:
            await self.on_decision(m, sender, sender_name, decision.verb, decision.proposal_id, thread)
            return
        cmd = self.command_re.fullmatch(body)
        if cmd:
            await self.on_command(m, sender, sender_name, cmd.group(1).lower(), thread)

    # ---------- proposals ----------

    async def on_propose(self, m: dict, sender: str, sender_name: str, body: str, thread: str | None) -> None:
        if self.revoked or sender not in self.people.proposers or m.get("sender_kind") == "platform" or m.get("on_behalf_of"):
            why = "proposer access was revoked by the client" if self.revoked else "not on the proposer list"
            self.ledger.append("rejected", None, sender, sender_name, None, f"proposal refused: {why}")
            await self.say(cards.not_proposer(sender_name) + (" Access was revoked." if self.revoked else ""), thread)
            return
        if self.paused:
            self.ledger.append("rejected", None, sender, sender_name, None, "proposal refused: paused")
            await self.say(f"{self.cfg.gate.name} is paused by the client. Nothing changed.", thread)
            return
        try:
            parsed = parse_block(body, self.connectors)
        except ProposalError as e:
            self.ledger.append("rejected", None, sender, sender_name, None, f"bad proposal: {e}"[:300])
            await self.say(cards.bad_proposal(str(e)), thread)
            return
        decision = evaluate(self.cfg.rules, parsed.action, parsed.params_json, lambda a: self.store.count_since(a, now_ms() - DAY_MS))
        if decision.effect == "deny":
            self.ledger.append("rejected", None, sender, sender_name, parsed.payload_hash, decision.reason)
            await self.say(cards.policy_denial(parsed.action, decision.reason, sender_name), thread, targets=[sender_name])
            return
        status = "approved" if decision.effect == "allow" else "pending"
        prop = self.store.create(parsed, sender, sender_name, self.room_id or "", thread, self.cfg.gate.proposal_ttl_minutes, status=status)
        self.ledger.append("proposed", prop.id, sender, sender_name, prop.payload_hash, decision.reason)
        conn = self.connectors[prop.action]
        if decision.effect == "allow":
            self.store.transition(prop.id, "approved", "approved", decided_by="policy")
            await self.execute(self.store.get(prop.id), None)  # type: ignore[arg-type]
            return
        await self.say(cards.proposal_card(prop, conn.preview(prop.action, parsed.params)), thread, targets=self._approver_targets())

    # ---------- approvals ----------

    async def on_decision(self, m: dict, sender: str, sender_name: str, verb: str, pid: str, thread: str | None) -> None:
        prop = self.store.get(pid)
        try:
            check_sender(sender, m.get("sender_kind"), m.get("on_behalf_of"), self.people.approvers, self.people.agents, pid)
            if self.paused:
                raise Rejected(f"{self.cfg.gate.name} is paused; resume first")
            check_proposal(prop, pid)
        except Rejected as e:
            if e.expired and prop and self.store.transition(prop.id, "pending", "expired"):
                self.ledger.append("expired", prop.id, None, None, prop.payload_hash)
            self.ledger.append("rejected", pid if prop else None, sender, sender_name, prop.payload_hash if prop else None, f"{verb}: {e}")
            await self.say(str(e) + ".", thread)
            return
        assert prop
        if verb == "deny":
            if not self.store.transition(prop.id, "pending", "denied", decided_by=sender):
                await self.say(f"{prop.id} was already decided.", thread)
                return
            line = self.ledger.append("denied", prop.id, sender, sender_name, prop.payload_hash)
            await self.say(cards.denied_by_client(prop, sender_name, line["seq"], line["hash"]), prop.thread_id, targets=self._proposer_target(prop))
            return
        if not self.store.transition(prop.id, "pending", "approved", decided_by=sender):
            await self.say(f"{prop.id} was already decided.", thread)
            return
        self.ledger.append("approved", prop.id, sender, sender_name, prop.payload_hash)
        await self.execute(self.store.get(prop.id), sender_name)  # type: ignore[arg-type]

    async def execute(self, prop: Proposal, approver_name: str | None) -> None:
        """Run one approved proposal exactly once. Only place a secret is read."""
        conn = self.connectors[prop.action]
        try:
            params = conn.actions[prop.action].model_validate(prop.params)
            if payload_hash(prop.action, params.model_dump(mode="json")) != prop.payload_hash:
                raise RuntimeError("payload changed after approval")
            conn.check(prop.action, params)
            secret = self.vault.get(conn.secret_name)
            receipt: Receipt = await conn.execute(prop.action, params, secret)
            del secret
            if not receipt.ok:
                raise RuntimeError(receipt.summary)
        except Exception as e:  # one failed action must not take the gate down
            err = self._redact(f"{type(e).__name__}: {e}")[:400]
            self.store.set_result(prop.id, "failed", {"error": err})
            line = self.ledger.append("failed", prop.id, prop.decided_by, approver_name, prop.payload_hash, err)
            log.error("%s failed: %s", prop.id, err)
            await self.say(cards.failure(prop, err, line["seq"], line["hash"]), prop.thread_id, targets=self._proposer_target(prop))
            return
        safe = Receipt.model_validate(self._redact(receipt.model_dump(mode="json")))
        self.store.set_result(prop.id, "executed", safe.model_dump(mode="json"))
        line = self.ledger.append("executed", prop.id, prop.decided_by, approver_name or "policy", prop.payload_hash, safe.external_id)
        await self.say(cards.receipt(prop, safe, approver_name, line["seq"], line["hash"]), prop.thread_id, targets=self._proposer_target(prop))

    # ---------- commands ----------

    async def on_command(self, m: dict, sender: str, sender_name: str, cmd: str, thread: str | None) -> None:
        try:
            check_sender(sender, m.get("sender_kind"), m.get("on_behalf_of"), self.people.approvers, self.people.agents, f"keystead {cmd}")
        except Rejected:
            self.ledger.append("rejected", None, sender, sender_name, None, f"command {cmd} from non-approver")
            await self.say(f"Only the client can run {self.cfg.gate.name} {cmd}.", thread)
            return
        if cmd == "status":
            ok, msg = self.ledger.verify()
            await self.say(cards.status(self.paused, self.revoked, self.store.pending(), self.store.recent(5), msg), thread)
        elif cmd == "audit":
            ok, msg = self.ledger.verify()
            await self.say(cards.audit_tail(self.ledger.lines(), msg), thread)
        elif cmd == "pause":
            self.store.set_state("paused", "1")
            self.ledger.append("paused", None, sender, sender_name)
            await self.say(f"{self.cfg.gate.name} paused. Nothing will run until resume.", thread)
        elif cmd == "resume":
            self.store.set_state("paused", "0")
            self.ledger.append("resumed", None, sender, sender_name)
            await self.say(f"{self.cfg.gate.name} resumed.", thread)
        elif cmd == "revoke":
            cancelled = revoke(self.store, self.ledger, sender, sender_name)
            await self.say(f"Proposer access revoked. Cancelled: {', '.join(cancelled) or 'none'}. Remove the agency from the room to finish.", thread)

    # ---------- expiry ----------

    async def sweep(self) -> None:
        now = now_ms()
        for p in self.store.pending():
            if now >= p.expires_at and self.store.transition(p.id, "pending", "expired"):
                self.ledger.append("expired", p.id, None, None, p.payload_hash)
                await self.say(cards.expired(p), p.thread_id, targets=self._proposer_target(p))

    async def _sweeper(self) -> None:
        while True:
            await asyncio.sleep(15)
            try:
                await self.sweep()
            except Exception as e:
                log.error("sweep failed: %s", e)

    async def run(self) -> None:
        room_id = await self.resolve_room()
        sweeper: asyncio.Task | None = None
        try:
            async for event in self.client.events([room_id]):
                if event.get("type") == "connection_state":
                    if sweeper is None:
                        await self.start()
                        sweeper = asyncio.create_task(self._sweeper())
                    else:
                        await self.client.connect(room_id)
                    continue
                try:
                    await self.handle(event)
                except Exception:
                    log.exception("event handling failed")
        finally:
            if sweeper:
                sweeper.cancel()


def revoke(store: Store, ledger: Ledger, actor_id: str | None, actor_name: str | None) -> list[str]:
    """Empty the proposer list (persisted), cancel every pending proposal, log it."""
    store.set_state("revoked", "1")
    cancelled = []
    for p in store.pending():
        if store.transition(p.id, "pending", "cancelled", decided_by=actor_id):
            ledger.append("cancelled", p.id, actor_id, actor_name, p.payload_hash)
            cancelled.append(p.id)
    ledger.append("revoked", None, actor_id, actor_name, None, f"cancelled {len(cancelled)}")
    return cancelled
