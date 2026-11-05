"""Parse the ```keystead block, validate it, hash it, and store proposals in SQLite."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .audit import canonical_json
from .connectors.base import Connector, ConnectorError

BLOCK_RE = re.compile(r"```keystead\s*(\{.*?\})\s*```", re.S)
STATUSES = ("pending", "approved", "denied", "expired", "executed", "failed", "cancelled", "rejected")


class ProposalError(Exception):
    pass


class Block(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(min_length=1, max_length=64)
    params: dict[str, Any]
    reason: str = Field(min_length=1, max_length=500)


@dataclass(frozen=True)
class Parsed:
    action: str
    params: BaseModel
    params_json: dict[str, Any]
    reason: str
    payload_hash: str


def payload_hash(action: str, params: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json({"action": action, "params": params}).encode()).hexdigest()


def parse_block(body: str, connectors: dict[str, Connector]) -> Parsed:
    matches = BLOCK_RE.findall(body)
    if len(matches) > 1:
        raise ProposalError("multiple ```keystead blocks found; send one proposal per message")
    m = BLOCK_RE.search(body)
    if not m:
        raise ProposalError("no ```keystead block with a JSON object found")
    try:
        raw = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        raise ProposalError(f"the keystead block is not valid JSON: {e.msg} at char {e.pos}") from e
    try:
        block = Block.model_validate(raw)
    except ValidationError as e:
        raise ProposalError("bad proposal: " + "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())) from e
    conn = connectors.get(block.action)
    if conn is None:
        raise ProposalError(f"unknown action {block.action!r}; send help for the list")
    try:
        p = conn.actions[block.action].model_validate(block.params)
    except ValidationError as e:
        raise ProposalError(f"bad params for {block.action}: " + "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())) from e
    try:
        conn.check(block.action, p)
    except ConnectorError as e:
        raise ProposalError(str(e)) from e
    pj = p.model_dump(mode="json")
    return Parsed(block.action, p, pj, block.reason.strip(), payload_hash(block.action, pj))


@dataclass
class Proposal:
    id: str
    action: str
    params: dict[str, Any]
    reason: str
    payload_hash: str
    proposer_id: str
    proposer_name: str
    room_id: str
    thread_id: str | None
    status: str
    created_at: int
    expires_at: int
    decided_by: str | None
    decided_at: int | None
    result: dict[str, Any] | None


SCHEMA = """
CREATE TABLE IF NOT EXISTS proposals (
  n INTEGER PRIMARY KEY AUTOINCREMENT,
  id TEXT UNIQUE NOT NULL,
  action TEXT NOT NULL,
  params TEXT NOT NULL,
  reason TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  proposer_id TEXT NOT NULL,
  proposer_name TEXT NOT NULL,
  room_id TEXT NOT NULL,
  thread_id TEXT,
  status TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  decided_by TEXT,
  decided_at INTEGER,
  result TEXT
);
CREATE TABLE IF NOT EXISTS state (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS identities (sender_id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL, kind TEXT NOT NULL, pinned_at INTEGER NOT NULL);
CREATE TRIGGER IF NOT EXISTS proposals_immutable BEFORE UPDATE OF action, params, payload_hash, proposer_id ON proposals
BEGIN SELECT RAISE(ABORT, 'proposals are immutable'); END;
"""


def now_ms() -> int:
    return int(time.time() * 1000)


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)

    def _row(self, r: sqlite3.Row | None) -> Proposal | None:
        if r is None:
            return None
        d = dict(r)
        d.pop("n")
        d["params"] = json.loads(d["params"])
        d["result"] = json.loads(d["result"]) if d["result"] else None
        return Proposal(**d)

    def create(self, parsed: Parsed, proposer_id: str, proposer_name: str, room_id: str, thread_id: str | None, ttl_minutes: int, status: str = "pending") -> Proposal:
        created = now_ms()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            n = self.db.execute("SELECT COALESCE(MAX(n), 0) + 1 FROM proposals").fetchone()[0]
            pid = f"KS-{n:04d}"
            self.db.execute(
                "INSERT INTO proposals (n,id,action,params,reason,payload_hash,proposer_id,proposer_name,room_id,thread_id,status,created_at,expires_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (n, pid, parsed.action, canonical_json(parsed.params_json), parsed.reason, parsed.payload_hash, proposer_id, proposer_name, room_id, thread_id, status, created, created + ttl_minutes * 60_000),
            )
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        p = self.get(pid)
        assert p
        return p

    def get(self, pid: str) -> Proposal | None:
        return self._row(self.db.execute("SELECT * FROM proposals WHERE id = ?", (pid.upper(),)).fetchone())

    def transition(self, pid: str, from_status: str, to_status: str, decided_by: str | None = None) -> bool:
        """Atomic compare-and-set. Returns False if the proposal was not in from_status."""
        if to_status not in STATUSES:
            raise ValueError(to_status)
        if decided_by is not None:
            cur = self.db.execute("UPDATE proposals SET status=?, decided_by=?, decided_at=? WHERE id=? AND status=?", (to_status, decided_by, now_ms(), pid, from_status))
        else:
            cur = self.db.execute("UPDATE proposals SET status=? WHERE id=? AND status=?", (to_status, pid, from_status))
        return cur.rowcount == 1

    def set_result(self, pid: str, status: str, result: dict) -> None:
        self.db.execute("UPDATE proposals SET status=?, result=? WHERE id=?", (status, canonical_json(result), pid))

    def pending(self) -> list[Proposal]:
        return [self._row(r) for r in self.db.execute("SELECT * FROM proposals WHERE status='pending' ORDER BY n")]  # type: ignore[misc]

    def recent(self, limit: int = 10) -> list[Proposal]:
        return [self._row(r) for r in self.db.execute("SELECT * FROM proposals ORDER BY n DESC LIMIT ?", (limit,))]  # type: ignore[misc]

    def count_since(self, action: str, since_ms: int) -> int:
        return self.db.execute(
            "SELECT COUNT(*) FROM proposals WHERE action=? AND created_at>=? AND status IN ('pending','approved','executed','failed')",
            (action, since_ms),
        ).fetchone()[0]

    def get_state(self, k: str, default: str = "") -> str:
        r = self.db.execute("SELECT v FROM state WHERE k=?", (k,)).fetchone()
        return r[0] if r else default

    def set_state(self, k: str, v: str) -> None:
        self.db.execute("INSERT INTO state (k,v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))

    # ---------- identities: Switch transport sender id <-> room participant name ----------

    def identity(self, sender_id: str) -> tuple[str, str] | None:
        r = self.db.execute("SELECT name, kind FROM identities WHERE sender_id=?", (sender_id,)).fetchone()
        return (r[0], r[1]) if r else None

    def id_for_name(self, name: str) -> str | None:
        r = self.db.execute("SELECT sender_id FROM identities WHERE name=?", (name,)).fetchone()
        return r[0] if r else None

    def pin(self, sender_id: str, name: str, kind: str) -> None:
        self.db.execute("INSERT INTO identities (sender_id,name,kind,pinned_at) VALUES (?,?,?,?)", (sender_id, name, kind, now_ms()))

    def force_pin(self, sender_id: str, name: str, kind: str) -> None:
        self.db.execute("DELETE FROM identities WHERE sender_id=? OR name=?", (sender_id, name))
        self.pin(sender_id, name, kind)

    def identities(self) -> list[tuple[str, str, str, int]]:
        return [tuple(r) for r in self.db.execute("SELECT name, kind, sender_id, pinned_at FROM identities ORDER BY name")]

    def clear_identities(self) -> None:
        self.db.execute("DELETE FROM identities")
