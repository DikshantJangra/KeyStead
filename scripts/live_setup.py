"""Provision a local Switch for Keystead, no tests: register @keystead and a scripted
@clientsite-agency, create the private room and Mattermost users dj and client, write
config/keystead.yaml and data/agent.json. Then `keystead run`.

    uv run python scripts/live_setup.py   (needs the local Switch stack; see README)
"""
import asyncio
import json
import os
import uuid
from pathlib import Path

import aiohttp

KS = Path(__file__).resolve().parent.parent
SW = Path(os.environ.get("SWITCH_REPO", KS.parent / "switch")).resolve()
SWITCH, MM = "http://localhost:8000", "http://localhost:8065"
H = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731


def env():
    return {k.strip(): v.strip() for k, _, v in (ln.partition("=") for ln in (SW / ".env").read_text().splitlines() if "=" in ln and not ln.lstrip().startswith("#"))}


async def reg(http, tok, name, desc):
    body = {"name": name, "description": desc, "connector_type": "custom", "overwrite": True,
            "integration_profile": {"connection_model": "always_on", "message_exchange": True, "pre_invocation_mediation": [], "post_invocation_mediation": [], "event_reporting": []}}
    async with http.post(f"{SWITCH}/agents", headers=H(tok), json=body) as r:
        b = await r.json()
        assert r.status == 200, b
        return {"id": b["id"], "api_key": b["api_key"]}


async def op(http, a, name, args):
    async with http.post(f"{SWITCH}/agents/{a['id']}/ops/{name}", headers=H(a["api_key"]), json=args) as r:
        b = await r.json()
        assert r.status == 200, (name, b)
        return b["result"]


async def main():
    e = env()
    async with aiohttp.ClientSession() as http:
        gate = await reg(http, e["AGENT_REGISTRATION_TOKEN"], "keystead", "Client-owned key-holder. No LLM.")
        agency = await reg(http, e["AGENT_REGISTRATION_TOKEN"], "clientsite-agency", "Scripted stand-in for the agency's coding agent")
        # an agent cannot change its own settings, so each sets the other's
        await op(http, gate, "update_agent_detail", {"agent_id": agency["id"], "addressing": "anyone"})
        await op(http, agency, "update_agent_detail", {"agent_id": gate["id"], "addressing": "anyone"})
        bl = await op(http, agency, "list_bridges", {})
        bridge = next(b["id"] for b in (bl if isinstance(bl, list) else bl["bridges"]) if b["type"] == "mattermost")
        room = f"keystead-clientsite-{uuid.uuid4().hex[:4]}"
        await op(http, agency, "create_room", {"name": room, "description": "Agency proposes, client approves, keystead executes",
                                               "agent_names": ["clientsite-agency", "keystead"], "bridge_id": bridge, "channel_type": "channel_private"})
        async with http.post(f"{MM}/api/v4/users/login", json={"login_id": e["MATTERMOST_ADMIN_USER"], "password": e["MATTERMOST_ADMIN_PASSWORD"]}) as r:
            admin = r.headers["Token"]
        async with http.get(f"{MM}/api/v4/teams/name/{e['MATTERMOST_TEAM_NAME']}", headers=H(admin)) as r:
            team = (await r.json())["id"]
        pw = "Pw-" + uuid.uuid4().hex[:12]
        uids = []
        for u in ("dj", "client"):
            async with http.post(f"{MM}/api/v4/users", headers=H(admin), json={"username": u, "email": f"{u}@example.test", "password": pw}) as r:
                if r.status in (200, 201):
                    uid = (await r.json())["id"]
                else:
                    async with http.get(f"{MM}/api/v4/users/username/{u}", headers=H(admin)) as g:
                        uid = (await g.json())["id"]
                    await http.put(f"{MM}/api/v4/users/{uid}/password", headers=H(admin), json={"new_password": pw})
            await http.post(f"{MM}/api/v4/teams/{team}/members", headers=H(admin), json={"team_id": team, "user_id": uid})
            uids.append(uid)
        for _ in range(30):
            async with http.get(f"{MM}/api/v4/teams/{team}/channels/name/{room}", headers=H(admin)) as r:
                if r.status == 200:
                    ch = (await r.json())["id"]
                    break
            await asyncio.sleep(1)
        for uid in uids:
            await http.post(f"{MM}/api/v4/channels/{ch}/members", headers=H(admin), json={"user_id": uid})
    (KS / "data").mkdir(exist_ok=True)
    (KS / "data" / "agent.json").write_text(json.dumps(gate))
    os.chmod(KS / "data" / "agent.json", 0o600)
    (KS / "data" / "agency-agent.json").write_text(json.dumps(agency))
    cfg = (KS / "config" / "keystead.example.yaml").read_text().replace("room: keystead-clientsite", f"room: {room}")
    (KS / "config" / "keystead.yaml").write_text(cfg)
    print(json.dumps({"room": room, "mattermost": MM, "team": e["MATTERMOST_TEAM_NAME"], "users": {"dj": pw, "client": pw}, "admin": e["MATTERMOST_ADMIN_USER"]}, indent=2))


asyncio.run(main())
