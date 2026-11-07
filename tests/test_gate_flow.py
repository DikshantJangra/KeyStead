"""Full propose -> forged approvals -> client approve -> execute once, over a fake Switch."""

import asyncio
import json

import pytest
from aiohttp.test_utils import TestServer

from keystead.audit import Ledger
from keystead.gate import Gate, GateStartError, build_roster
from keystead.proposals import Store
from keystead.switch_client import SwitchClient
from keystead.vault import Vault

from .conftest import SECRET
from .fake_switch import AGENCY, CLIENT, DJ, PARTICIPANTS, FakeSwitch
from .test_proposals import GOOD


@pytest.fixture
async def env(tmp_path, cfg, connectors, master_key, fake_cf):
    fake = FakeSwitch()
    server = TestServer(fake.app)
    await server.start_server()
    (tmp_path / "agent.json").write_text(json.dumps({"id": "gate-id", "api_key": fake.api_key}))
    vault = Vault(tmp_path / "vault.json", master_key)
    vault.set("cloudflare_token", SECRET)
    store = Store(tmp_path / "keystead.db")
    ledger = Ledger(tmp_path / "audit.jsonl")
    client = SwitchClient(str(server.make_url("")), tmp_path / "agent.json")
    await client.__aenter__()
    gate = Gate(cfg, client, store, ledger, vault, connectors)
    task = asyncio.create_task(gate.run())
    await fake.wait_posts(1)
    yield fake, gate, store, ledger, tmp_path
    task.cancel()
    fake.queue.put_nowait(None)
    await client.__aexit__()
    await server.close()


async def step(fake, sender, body, **kw):
    n = len(fake.posts)
    fake.say(sender, body, **kw)
    return (await fake.wait_posts(n + 1))[n]["body"]


async def test_full_flow(env, fake_cf):
    fake, gate, store, ledger, tmp = env
    assert fake.posts[0]["body"].startswith("keystead online")
    assert json.loads((tmp / "agent.json").read_text())["connection_id"]

    out = await step(fake, AGENCY, "@keystead help")
    assert "dns.add_record" in out and "social.publish_post" not in out

    card = await step(fake, AGENCY, GOOD)
    assert card.startswith("@client KS-0001 · dns.add_record on clientsite.com")
    assert 'TXT  @  "google-site-verification=abc123"  TTL auto' in card
    assert "Asked by clientsite-agency for: Verify clientsite.com" in card
    assert 'Reply "approve KS-0001" or "deny KS-0001". Expires ' in card

    assert "Agents never" in await step(fake, AGENCY, "approve KS-0001")
    assert "Only the client can approve KS-0001" in await step(fake, DJ, "approve KS-0001")
    assert "on someone's behalf" in await step(fake, CLIENT, "approve KS-0001", kind="platform", on_behalf_of="client")
    assert fake_cf.instances == []
    assert store.get("KS-0001").status == "pending"

    receipt = await step(fake, CLIENT, "approve KS-0001")
    assert receipt.startswith("@clientsite-agency KS-0001 done. TXT @ is live, record id 9f2c…. Approved by client at ")
    assert "Ledger #" in receipt
    assert len(fake_cf.instances) == 1
    assert fake_cf.instances[0].records.created == [{"zone_id": "zone-123", "type": "TXT", "name": "clientsite.com", "content": "google-site-verification=abc123", "ttl": 1}]
    assert store.get("KS-0001").status == "executed"
    assert store.get("KS-0001").decided_by == CLIENT

    assert "already executed" in await step(fake, CLIENT, "approve KS-0001")
    assert len(fake_cf.instances) == 1

    ok, msg = ledger.verify()
    assert ok, msg
    events = [line["event"] for line in ledger.lines() if line["event"] != "pinned"]
    assert events == ["proposed", "rejected", "rejected", "rejected", "approved", "executed", "rejected"]

    for f in ("keystead.db", "audit.jsonl", "vault.json"):
        assert SECRET.encode() not in (tmp / f).read_bytes(), f
    assert all(SECRET not in p["body"] for p in fake.posts)


async def test_policy_paths(env, fake_cf):
    fake, gate, store, ledger, tmp = env
    out = await step(fake, AGENCY, GOOD.replace('"TXT"', '"A"').replace("google-site-verification=abc123", "1.2.3.4"))
    assert "Refused dns.add_record" in out and "denied by rule 4" in out

    out = await step(fake, AGENCY, '@keystead propose\n```keystead\n{"action":"dns.list_records","params":{"zone":"clientsite.com"},"reason":"look"}\n```')
    assert "KS-0001 done. 1 record(s)" in out and "Allowed by policy" in out

    out = await step(fake, CLIENT, GOOD)
    assert "client is not allowed to propose" in out

    out = await step(fake, AGENCY, '@keystead propose\n```keystead\n{"action":"shell.run","params":{},"reason":"x"}\n```')
    assert "unknown action" in out

    card = await step(fake, DJ, GOOD)
    assert "KS-0002" in card
    out = await step(fake, CLIENT, "deny KS-0002")
    assert "KS-0002 denied by client" in out and store.get("KS-0002").status == "denied"
    assert fake_cf.instances[-1].records.created == []


async def test_expiry_and_revoke(env, fake_cf):
    fake, gate, store, ledger, tmp = env
    await step(fake, AGENCY, GOOD)
    store.db.execute("UPDATE proposals SET expires_at = 0 WHERE id='KS-0001'")
    out = await step(fake, CLIENT, "approve KS-0001")
    assert "expired" in out and store.get("KS-0001").status == "expired"

    await step(fake, AGENCY, GOOD)
    assert "only the client can run" in (await step(fake, DJ, "keystead revoke")).lower()
    out = await step(fake, CLIENT, "keystead revoke")
    assert "revoked" in out and "KS-0002" in out
    assert store.get("KS-0002").status == "cancelled"
    out = await step(fake, AGENCY, GOOD)
    assert "not allowed to propose" in out and "revoked" in out
    out = await step(fake, CLIENT, "keystead status")
    assert "proposers revoked" in out and "ledger ok" in out
    assert fake_cf.instances == []
    assert ledger.verify()[0]


async def test_pause(env):
    fake, gate, store, ledger, tmp = env
    await step(fake, AGENCY, GOOD)
    assert "paused" in await step(fake, CLIENT, "keystead pause")
    assert "paused" in await step(fake, CLIENT, "approve KS-0001")
    assert "paused" in await step(fake, AGENCY, GOOD)
    assert "resumed" in await step(fake, CLIENT, "keystead resume")
    assert "done" in await step(fake, CLIENT, "approve KS-0001")


def test_roster_refusals(cfg):
    from keystead.config import KeysteadConfig

    raw = cfg.model_dump(by_alias=True)
    agent_approver = KeysteadConfig.model_validate({**raw, "people": {"approvers": ["clientsite-agency"], "proposers": []}})
    with pytest.raises(GateStartError, match="agents can never approve"):
        build_roster(agent_approver, PARTICIPANTS, strict=True)
    missing = KeysteadConfig.model_validate({**raw, "people": {"approvers": ["nobody"], "proposers": []}})
    with pytest.raises(GateStartError, match="not in the room"):
        build_roster(missing, PARTICIPANTS, strict=True)
    ambiguous = [*PARTICIPANTS, {"id": "x", "name": "client", "type": "agent", "alias": None}]
    with pytest.raises(GateStartError, match="both a person and an agent"):
        build_roster(cfg, ambiguous, strict=True)
    gate_proposer = KeysteadConfig.model_validate({**raw, "people": {"approvers": ["client"], "proposers": ["keystead"]}})
    with pytest.raises(GateStartError, match="its own proposer"):
        build_roster(gate_proposer, PARTICIPANTS, strict=True)
    with pytest.raises(Exception, match="both approver and proposer"):
        KeysteadConfig.model_validate({**raw, "people": {"approvers": ["client"], "proposers": ["Client"]}})


async def test_identity_pinning(env, fake_cf):
    fake, gate, store, ledger, tmp = env
    await step(fake, AGENCY, GOOD)
    assert "Only the client" in await step(fake, DJ, "approve KS-0001")
    # client speaks first and is pinned; an impostor reusing the name "client" with another id is refused
    assert "status" in await step(fake, CLIENT, "keystead status")
    out = await step(fake, "@switch-user-impostor:local", "approve KS-0001", name="client")
    assert "Only the client" in out
    assert any("identity conflict" in (line.get("detail") or "") for line in ledger.lines())
    # an agent sending as a user-named participant is refused too
    out = await step(fake, "@switch-agent-x:local", "approve KS-0001", kind="agent", name="dj")
    assert "Agents never" in out
    assert store.get("KS-0001").status == "pending" and fake_cf.instances == []
    assert {n for n, *_ in store.identities()} == {"clientsite-agency", "dj", "client"}
    assert store.get_state("self_id") == "@switch-agent-gate:local"
    assert "done" in await step(fake, CLIENT, "approve KS-0001")


async def test_reopens_stream_on_409_beat(env):
    fake, gate, store, ledger, tmp = env
    await step(fake, AGENCY, "@keystead help")
    fake.beat_status = 409
    for _ in range(50):
        if fake.opens >= 2:
            break
        await asyncio.sleep(0.1)
    assert fake.opens >= 2 and fake.last_event_id == str(fake.seq)
    assert "KS-0001" in await step(fake, AGENCY, GOOD)
