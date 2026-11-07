"""A fake Switch agent bridge: SSE event stream, heartbeat and the ops the gate uses."""

from __future__ import annotations

import asyncio
import json
import uuid

from aiohttp import web

ROOM = "room-1"
GATE = "@switch-agent-gate:local"
AGENCY = "@switch-agent-agency:local"
DJ = "@switch-user-dj:local"
CLIENT = "@switch-user-client:local"
SWITCH_APP = "@switch-admin:local"
NAMES = {GATE: "keystead", AGENCY: "clientsite-agency", DJ: "dj", CLIENT: "client", SWITCH_APP: "switch"}
# Real Switch: list_participants ids (UUIDs) and message sender ids are different id spaces.
PARTICIPANTS = [
    {"id": "26fe52c1-gate", "name": "keystead", "type": "agent", "status": "live", "alias": None},
    {"id": "f7bc3729-agency", "name": "clientsite-agency", "type": "agent", "status": None, "alias": None},
    {"id": "8434d29a-dj", "name": "dj", "type": "user", "status": None, "alias": None},
    {"id": "729d6c36-client", "name": "client", "type": "user", "status": None, "alias": None},
]


class FakeSwitch:
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.posts: list[dict] = []
        self.seq = 0
        self.beats = 0
        self.beat_status = 200
        self.open_connections: set[str] = set()
        self.opens = 0
        self.api_key = "agent-key"
        self.new_post = asyncio.Event()
        app = web.Application()
        app.router.add_get("/health", self.health)
        app.router.add_get("/agents/{id}/events", self.events)
        app.router.add_post("/agents/{id}/connection/beat", self.beat)
        app.router.add_post("/agents/{id}/ops/{name}", self.op)
        self.app = app

    async def health(self, request):
        return web.json_response({"ok": True})

    def _auth(self, request):
        if request.headers.get("Authorization") != f"Bearer {self.api_key}":
            raise web.HTTPUnauthorized()

    async def events(self, request):
        self._auth(request)
        self.opens += 1
        self.open_connections.add(request.query["connection_id"])
        self.last_event_id = request.headers.get("Last-Event-ID")
        resp = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await resp.prepare(request)
        state = {"connection_id": request.query["connection_id"], "rooms": [ROOM], "heartbeat_interval_seconds": 2}
        await resp.write(f"event: connection_state\ndata: {json.dumps(state)}\n\n".encode())
        while True:
            ev = await self.queue.get()
            if ev is None:
                self.open_connections.discard(request.query["connection_id"])
                break
            await resp.write(f"id: {ev['sequence']}\nevent: message\ndata: {json.dumps(ev)}\n\n".encode())
        return resp

    async def beat(self, request):
        self._auth(request)
        self.beats += 1
        if self.beat_status != 200:
            status, self.beat_status = self.beat_status, 200
            self.queue.put_nowait(None)
            return web.json_response({"error": "no stream"}, status=status)
        return web.json_response({"rooms": [ROOM], "cursor": self.seq})

    async def op(self, request):
        self._auth(request)
        name = request.match_info["name"]
        args = await request.json()
        conn = request.headers.get("X-Switch-Connection-Id")
        if conn is not None and conn not in self.open_connections:
            return web.json_response({"detail": f"connection {conn} is not open"}, status=409)
        if name != "list_rooms" and conn is None:
            return web.json_response({"detail": "needs a connection"}, status=409)
        if name == "list_rooms":
            return web.json_response({"result": [{"room_id": ROOM, "name": "keystead-clientsite", "description": "", "connected": False, "archived": False}]})
        if name == "connect_to_room":
            assert request.headers.get("X-Switch-Connection-Id")
            return web.json_response({"result": {"room_id": args["room_id"], "participants": PARTICIPANTS}})
        if name == "list_participants":
            return web.json_response({"result": PARTICIPANTS})
        if name in ("post_message", "send_targeted_message"):
            body = args["body"]
            if name == "send_targeted_message":
                body = " ".join(f"@{n}" for n in args["target_names"]) + " " + body
            self.posts.append({"op": name, "body": body, "thread_id": args.get("thread_id"), "targets": args.get("target_names")})
            self.new_post.set()
            event_id = str(uuid.uuid4())
            self.say(GATE, body, message_id=event_id)  # the room echoes the gate's own post back to it
            return web.json_response({"result": {"event_id": event_id}})
        return web.json_response({"error": f"unknown op {name}"}, status=404)

    def say(self, sender: str, body: str, kind: str | None = None, on_behalf_of: str | None = None, name: str | None = None, message_id: str | None = None) -> None:
        self.seq += 1
        payload = {"addressed": False, "sender": sender, "sender_name": name or NAMES.get(sender, sender), "message_id": message_id or f"m{self.seq}", "body": body, "timestamp": 0, "thread_id": None, "attachments": []}
        if kind:
            payload["sender_kind"] = kind
        if on_behalf_of:
            payload["on_behalf_of"] = on_behalf_of
        self.queue.put_nowait({"type": "message", "room_id": ROOM, "bridge_id": None, "channel_type": "channel_private", "payload": payload, "sequence": self.seq})

    async def wait_posts(self, n: int, timeout: float = 5) -> list[dict]:
        async def _wait():
            while len(self.posts) < n:
                self.new_post.clear()
                await self.new_post.wait()

        await asyncio.wait_for(_wait(), timeout)
        return self.posts
