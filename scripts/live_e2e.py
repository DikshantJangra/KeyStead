"""Live end-to-end check: a real switch-core + Mattermost + the Keystead gate.

Needs a local Switch stack (see README, "Run the live check"):
    SWITCH_REPO=../switch uv run python scripts/live_e2e.py

It registers @keystead and a scripted @clientsite-agency stand-in, creates a private
room and the Mattermost people dj and client, then plays the demo: help, propose,
DJ's and the agent's forged approvals, the client's approval (Cloudflare is called
with a fake token, so the receipt is a redacted failure), revoke, and audit verify."""

import asyncio
import json
import os
import subprocess
import time
import uuid
from pathlib import Path

import aiohttp

KS = Path(__file__).resolve().parent.parent
SW_REPO = Path(os.environ.get("SWITCH_REPO", KS.parent / "switch")).resolve()
WORK = Path(os.environ.get("KS_E2E_WORK", "/tmp/keystead-live-e2e")).resolve()
SWITCH = "http://localhost:8000"
MM = "http://localhost:8065"
FAKE_TOKEN = "cf-live-e2e-NOT-A-REAL-TOKEN-42"


def env():
    out = {}
    for line in (SW_REPO / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


async def reg(http, token, name, desc):
    async with http.post(f"{SWITCH}/agents", headers={"Authorization": f"Bearer {token}"}, json={
        "name": name, "description": desc, "connector_type": "custom", "overwrite": True,
        "integration_profile": {"connection_model": "always_on", "message_exchange": True,
                                "pre_invocation_mediation": [], "post_invocation_mediation": [], "event_reporting": []}}) as r:
        b = await r.json()
        assert r.status == 200, b
        return {"id": b["id"], "api_key": b["api_key"]}


async def op(http, agent, name, args):
    async with http.post(f"{SWITCH}/agents/{agent['id']}/ops/{name}", headers={"Authorization": f"Bearer {agent['api_key']}"}, json=args) as r:
        b = await r.json()
        assert r.status == 200, (name, r.status, b)
        return b["result"]


async def mm_login(http, login, pw):
    async with http.post(f"{MM}/api/v4/users/login", json={"login_id": login, "password": pw}) as r:
        r.raise_for_status()
        return r.headers["Token"]


def H(t):
    return {"Authorization": f"Bearer {t}"}


async def mm_user(http, admin, team_id, username, pw):
    async with http.post(f"{MM}/api/v4/users", headers=H(admin), json={"username": username, "email": f"{username}@example.test", "password": pw}) as r:
        if r.status in (200, 201):
            uid = (await r.json())["id"]
        else:
            async with http.get(f"{MM}/api/v4/users/username/{username}", headers=H(admin)) as g:
                uid = (await g.json())["id"]
    async with http.post(f"{MM}/api/v4/teams/{team_id}/members", headers=H(admin), json={"team_id": team_id, "user_id": uid}) as r:
        r.raise_for_status()
    return uid


async def mm_posts(http, tok, ch):
    async with http.get(f"{MM}/api/v4/channels/{ch}/posts?per_page=200", headers=H(tok)) as r:
        d = await r.json()
    return sorted((d["posts"][i] for i in d["order"]), key=lambda p: p["create_at"])


async def main():
    e = env()
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "data").mkdir(exist_ok=True)
    async with aiohttp.ClientSession() as http:
        tok = e["AGENT_REGISTRATION_TOKEN"]
        gate = await reg(http, tok, "keystead", "Client-owned key-holder. No LLM.")
        agency = await reg(http, tok, "clientsite-agency", "Scripted stand-in for the agency's coding agent")
        await op(http, gate, "update_agent_detail", {"agent_id": agency["id"], "addressing": "anyone"})
        bridges = await op(http, agency, "list_bridges", {})
        bl = bridges if isinstance(bridges, list) else bridges.get("bridges", [])
        bridge = next(b["id"] for b in bl if b["type"] == "mattermost")
        room_name = f"keystead-clientsite-{uuid.uuid4().hex[:4]}"
        room = await op(http, agency, "create_room", {"name": room_name, "description": "Agency proposes, client approves, keystead executes",
                                                      "agent_names": ["clientsite-agency", "keystead"], "bridge_id": bridge, "channel_type": "channel_private"})
        admin = await mm_login(http, e["MATTERMOST_ADMIN_USER"], e["MATTERMOST_ADMIN_PASSWORD"])
        async with http.get(f"{MM}/api/v4/teams/name/{e['MATTERMOST_TEAM_NAME']}", headers=H(admin)) as r:
            team = (await r.json())["id"]
        pw = "Pw-" + uuid.uuid4().hex[:12]
        dj = await mm_user(http, admin, team, "dj", pw)
        client = await mm_user(http, admin, team, "client", pw)
        for uid in (dj, client):  # reruns: reset the password of an existing user
            async with http.put(f"{MM}/api/v4/users/{uid}/password", headers=H(admin), json={"new_password": pw}):
                pass
        ch = None
        for _ in range(30):
            async with http.get(f"{MM}/api/v4/teams/{team}/channels/name/{room_name}", headers=H(admin)) as r:
                if r.status == 200:
                    ch = (await r.json())["id"]
                    break
            await asyncio.sleep(1)
        assert ch, "no channel"
        for uid in (dj, client):
            async with http.post(f"{MM}/api/v4/channels/{ch}/members", headers=H(admin), json={"user_id": uid}) as r:
                r.raise_for_status()
        dj_t = await mm_login(http, "dj", pw)
        cl_t = await mm_login(http, "client", pw)

        async def say(t, msg):
            async with http.post(f"{MM}/api/v4/posts", headers=H(t), json={"channel_id": ch, "message": msg}) as r:
                r.raise_for_status()

        # gate files
        (WORK / "data" / "agent.json").write_text(json.dumps(gate))
        cfg = (KS / "config" / "keystead.example.yaml").read_text().replace("room: keystead-clientsite", f"room: {room_name}")
        (WORK / "keystead.yaml").write_text(cfg)
        genv = {**os.environ, "SWITCH_URL": SWITCH, "KEYSTEAD_DATA_DIR": str(WORK / "data"), "KEYSTEAD_CONFIG": str(WORK / "keystead.yaml")}
        key = subprocess.run(["uv", "run", "--project", str(KS), "python", "-c", "from keystead.vault import new_master_key;print(new_master_key())"], capture_output=True, text=True, env=genv, cwd=WORK).stdout.strip()
        genv["KEYSTEAD_MASTER_KEY"] = key
        subprocess.run(["uv", "run", "--project", str(KS), "keystead", "secret", "set", "cloudflare_token"], input=FAKE_TOKEN + "\n", text=True, env=genv, cwd=WORK, check=True)
        log = open(WORK / "gate.log", "w")
        proc = subprocess.Popen(["uv", "run", "--project", str(KS), "keystead", "run"], env=genv, cwd=WORK, stdout=log, stderr=subprocess.STDOUT)

        async def wait_for(text, after=0, timeout=40):
            t0 = time.time()
            while time.time() - t0 < timeout:
                posts = await mm_posts(http, cl_t, ch)
                for p in posts[after:]:
                    if text in p["message"]:
                        return p, len(posts)
                if proc.poll() is not None:
                    raise SystemExit("gate exited:\n" + (WORK / "gate.log").read_text())
                await asyncio.sleep(0.5)
            raise SystemExit(f"timeout waiting for {text!r}; last posts: {[p['message'][:120] for p in (await mm_posts(http, cl_t, ch))[-5:]]}\n" + (WORK / "gate.log").read_text()[-3000:])

        results = []

        def ok(name):
            results.append(name)
            print("PASS", name, flush=True)

        try:
            _, n = await wait_for("keystead online")
            ok("gate posts 'keystead online'")
            async def agency_say(body):
                async with http.post(f"{SWITCH}/agents/{agency['id']}/message", headers={"Authorization": f"Bearer {agency['api_key']}"}, json={"room_id": room["id"], "content": body}) as r:
                    assert r.status == 200, await r.text()
            await agency_say("@keystead help")
            _, n = await wait_for("dns.add_record: Add one DNS record", n)
            ok("help lists the catalog")
            await agency_say('@keystead propose\n```keystead\n{"action": "dns.add_record", "params": {"zone": "clientsite.com", "type": "TXT", "name": "@", "content": "google-site-verification=abc123", "ttl": 1}, "reason": "Verify clientsite.com in Google Search Console"}\n```')
            p, n = await wait_for("KS-0001 · dns.add_record on clientsite.com", n)
            print("   card:", p["message"].replace("\n", " | "))
            ok("proposal card posted")
            await say(dj_t, "approve KS-0001")
            p, n = await wait_for("Only the client can approve KS-0001", n)
            ok("DJ's approve refused")
            await agency_say("approve KS-0001")
            p, n = await wait_for("Agents never", n)
            ok("agency agent's approve refused")
            await say(cl_t, "approve KS-0001")
            p, n = await wait_for("KS-0001 ", n)
            print("   result:", p["message"])
            assert "failed" in p["message"] and "Ledger #" in p["message"] and FAKE_TOKEN not in p["message"]
            ok("client approve executed the connector once (fake CF token -> failure receipt, token redacted)")
            await say(cl_t, "keystead revoke")
            p, n = await wait_for("Proposer access revoked", n)
            await say(dj_t, '@keystead propose\n```keystead\n{"action": "dns.add_record", "params": {"zone": "clientsite.com", "type": "TXT", "name": "@", "content": "x"}, "reason": "again"}\n```')
            p, n = await wait_for("not allowed to propose", n)
            ok("after revoke, new proposals refused")
            v = subprocess.run(["uv", "run", "--project", str(KS), "keystead", "audit", "verify"], env=genv, cwd=WORK, capture_output=True, text=True)
            print("   ", v.stdout.strip())
            assert v.returncode == 0
            ok("audit verify passes")
            for f in ("keystead.db", "audit.jsonl", "vault.json"):
                assert FAKE_TOKEN.encode() not in (WORK / "data" / f).read_bytes(), f
            assert FAKE_TOKEN not in (WORK / "gate.log").read_text()
            assert all(FAKE_TOKEN not in p["message"] for p in await mm_posts(http, cl_t, ch))
            ok("no secret in chat, logs, db, ledger")
            print("\nTRANSCRIPT")
            for p in await mm_posts(http, cl_t, ch):
                print("---", p["message"][:400])
        finally:
            proc.terminate()
            proc.wait()
    print(f"\n{len(results)} live checks passed")


asyncio.run(main())
