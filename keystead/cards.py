"""The chat messages the gate posts."""

from __future__ import annotations

import time

from .connectors.base import Receipt
from .proposals import Proposal


def hhmm(ms: int) -> str:
    return time.strftime("%H:%M", time.localtime(ms / 1000))


def _on(p: Proposal) -> str:
    t = p.params.get("zone") or p.params.get("integration")
    return f" on {t}" if t else ""


def proposal_card(p: Proposal, preview: str) -> str:
    return (
        f"{p.id} · {p.action}{_on(p)}\n"
        f"{preview}\n"
        f"Asked by {p.proposer_name} for: {p.reason}\n"
        f'Reply "approve {p.id}" or "deny {p.id}". Expires {hhmm(p.expires_at)}.'
    )


def receipt(p: Proposal, r: Receipt, approver_name: str | None, seq: int, h: str) -> str:
    who = f"Approved by {approver_name} at {hhmm(p.decided_at or 0)}" if approver_name else "Allowed by policy, no approval needed"
    return f"{p.id} done. {r.summary}. {who}. Ledger #{seq} · {h[:6]}"


def failure(p: Proposal, error: str, seq: int, h: str) -> str:
    return f"{p.id} failed: {error}. Nothing else was tried. Ledger #{seq} · {h[:6]}"


def denied_by_client(p: Proposal, approver_name: str, seq: int, h: str) -> str:
    return f"{p.id} denied by {approver_name}. Nothing changed. Ledger #{seq} · {h[:6]}"


def policy_denial(action: str, reason: str, proposer_name: str) -> str:
    return f"Refused {action} from {proposer_name}: {reason}. Nothing changed."


def bad_proposal(error: str) -> str:
    return f"Proposal not accepted: {error}"


def not_proposer(name: str) -> str:
    return f"{name} is not allowed to propose changes here. Nothing changed."


def expired(p: Proposal) -> str:
    return f"{p.id} expired without a decision. Nothing changed."


def status(paused: bool, revoked: bool, pending: list[Proposal], recent: list[Proposal], ledger_msg: str) -> str:
    lines = [f"keystead status: {'PAUSED' if paused else 'running'}{', proposers revoked' if revoked else ''}"]
    lines.append(f"pending: {', '.join(p.id for p in pending) or 'none'}")
    for p in recent:
        lines.append(f"  {p.id}  {p.status:<9} {p.action}{_on(p)}  by {p.proposer_name}")
    lines.append(ledger_msg)
    return "\n".join(lines)


def audit_tail(lines: list[dict], verify_msg: str) -> str:
    out = [verify_msg]
    for line in lines[-10:]:
        out.append(f"  #{line['seq']} {hhmm(line['ts'])} {line['event']:<9} {line.get('proposal_id') or '-':<8} {line.get('actor_name') or '-'}  {line['hash'][:6]}")
    return "\n".join(out)
