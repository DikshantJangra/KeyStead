"""Append-only, hash-chained JSONL ledger."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

GENESIS = "0" * 64
EVENTS = {"proposed", "approved", "denied", "executed", "failed", "rejected", "revoked", "expired", "cancelled", "paused", "resumed", "pinned"}


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(prev_hash: str, line: dict) -> str:
    return hashlib.sha256((prev_hash + canonical_json(line)).encode()).hexdigest()


class Ledger:
    def __init__(self, path: Path):
        self.path = path

    def _last(self) -> dict | None:
        if not self.path.exists():
            return None
        last = None
        with self.path.open() as f:
            for raw in f:
                if raw.strip():
                    last = raw
        return json.loads(last) if last else None

    def append(
        self,
        event: str,
        proposal_id: str | None = None,
        actor_id: str | None = None,
        actor_name: str | None = None,
        payload_hash: str | None = None,
        detail: str | None = None,
    ) -> dict:
        if event not in EVENTS:
            raise ValueError(f"unknown audit event {event}")
        last = self._last()
        line = {
            "seq": (last["seq"] + 1) if last else 1,
            "ts": int(time.time() * 1000),
            "event": event,
            "proposal_id": proposal_id,
            "actor_id": actor_id,
            "actor_name": actor_name,
            "payload_hash": payload_hash,
            "prev_hash": last["hash"] if last else GENESIS,
        }
        if detail is not None:
            line["detail"] = detail
        line["hash"] = _hash(line["prev_hash"], line)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(canonical_json(line) + "\n")
        return line

    def lines(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(r) for r in self.path.read_text().splitlines() if r.strip()]

    def verify(self) -> tuple[bool, str]:
        """Recompute the chain. Returns (ok, message naming the first broken line)."""
        if not self.path.exists():
            return True, "ledger is empty"
        prev = GENESIS
        n = 0
        for lineno, raw in enumerate(self.path.read_text().splitlines(), 1):
            if not raw.strip():
                continue
            try:
                line = json.loads(raw)
            except json.JSONDecodeError:
                return False, f"line {lineno}: not valid JSON"
            n += 1
            body = {k: v for k, v in line.items() if k != "hash"}
            if line.get("seq") != n:
                return False, f"line {lineno} (seq {line.get('seq')}): expected seq {n}"
            if line.get("prev_hash") != prev:
                return False, f"line {lineno} (seq {n}): prev_hash does not match line before"
            if _hash(prev, body) != line.get("hash"):
                return False, f"line {lineno} (seq {n}): hash mismatch, line was edited"
            prev = line["hash"]
        return True, f"ledger ok: {n} lines, head {prev[:6]}"
