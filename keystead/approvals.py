"""approve / deny KS-NNNN. One approval binds to one proposal hash, once, before expiry."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .proposals import Proposal, now_ms, payload_hash

DECISION_RE = re.compile(r"\s*(approve|deny)\s+(KS-\d{4,})\s*", re.I)


class Rejected(Exception):
    """The decision does not count. str() is the reason shown in chat."""

    def __init__(self, reason: str, expired: bool = False):
        super().__init__(reason)
        self.expired = expired


@dataclass(frozen=True)
class Decision:
    verb: str  # approve | deny
    proposal_id: str


def parse_decision(body: str) -> Decision | None:
    m = DECISION_RE.fullmatch(body or "")
    if not m:
        return None
    return Decision(m.group(1).lower(), m.group(2).upper())


def check_sender(sender_id: str, sender_kind: str | None, on_behalf_of: str | None, approver_ids: set[str], agent_ids: set[str], proposal_id: str) -> None:
    if sender_kind == "platform" or on_behalf_of:
        raise Rejected(f"A message posted by Switch on someone's behalf cannot decide {proposal_id}")
    if sender_kind == "agent" or sender_id in agent_ids:
        raise Rejected(f"Only the client can approve {proposal_id}. Agents never can")
    if sender_id not in approver_ids:
        raise Rejected(f"Only the client can approve {proposal_id}")


def check_proposal(p: Proposal | None, proposal_id: str, now: int | None = None) -> Proposal:
    if p is None:
        raise Rejected(f"{proposal_id} does not exist")
    if p.status != "pending":
        raise Rejected(f"{p.id} is already {p.status}")
    if (now if now is not None else now_ms()) >= p.expires_at:
        raise Rejected(f"{p.id} expired; ask the agency to propose it again", expired=True)
    if payload_hash(p.action, p.params) != p.payload_hash:
        raise Rejected(f"{p.id} changed after it was proposed and will not run")
    return p
