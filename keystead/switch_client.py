"""A scripted (non-LLM) Switch agent client: register, event stream, heartbeat, ops, post.

"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import aiohttp

log = logging.getLogger("keystead.switch")


class SwitchError(Exception):
    pass


class _Reopen(Exception):
    pass


async def register(
    switch_url: str, reg_token: str, name: str, description: str, overwrite: bool
) -> dict:
    """POST /agents with connector_type=custom, connection_model=always_on.

    The registration token's user becomes the agent's owner. Switch returns the
    API key once."""
    async with aiohttp.ClientSession() as http:
        async with http.post(
            f"{switch_url}/agents",
            headers={"Authorization": f"Bearer {reg_token}"},
            json={
                "name": name,
                "description": description,
                "connector_type": "custom",
                "overwrite": overwrite,
                "integration_profile": {
                    "connection_model": "always_on",
                    "message_exchange": True,
                    "pre_invocation_mediation": [],
                    "post_invocation_mediation": [],
                    "event_reporting": [],
                },
            },
        ) as r:
            try:
                body = await r.json()
            except aiohttp.ContentTypeError:
                body = {"error": await r.text()}
            if r.status != 200:
                raise SwitchError(f"register {name}: {r.status} {body}")
            return {"id": body["id"], "api_key": body["api_key"]}


async def health(switch_url: str) -> int:
    async with aiohttp.ClientSession() as http:
        async with http.get(f"{switch_url}/health") as r:
            return r.status


class SwitchClient:
    def __init__(self, switch_url: str, agent_file: Path):
        if not agent_file.exists():
            raise SwitchError(f"{agent_file} missing (run `keystead register`)")
        self.agent_file = agent_file
        self.agent = json.loads(agent_file.read_text())
        if not self.agent.get("connection_id"):
            self.agent["connection_id"] = str(uuid.uuid4())
            agent_file.write_text(json.dumps(self.agent, indent=2))
        self.url = switch_url.rstrip("/")
        self.connection_id: str = self.agent["connection_id"]
        self.http: aiohttp.ClientSession | None = None
        self.connected_room: str | None = None
        self.last_event_id: str | None = None
        self._reopen = asyncio.Event()
        self._resp: aiohttp.ClientResponse | None = None

    @property
    def agent_id(self) -> str:
        return self.agent["id"]

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.agent['api_key']}"}

    async def __aenter__(self) -> SwitchClient:
        self.http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None, sock_connect=10))
        return self

    async def __aexit__(self, *exc) -> None:
        if self.http:
            await self.http.close()

    async def op(self, name: str, args: dict, on_connection: bool = True) -> dict | list:
        """Call an operation. on_connection=False for ops that need no open stream (list_rooms)."""
        assert self.http
        headers = dict(self._headers)
        if on_connection:
            headers["X-Switch-Connection-Id"] = self.connection_id
        async with self.http.post(
            f"{self.url}/agents/{self.agent_id}/ops/{name}", headers=headers, json=args
        ) as r:
            try:
                body = await r.json()
            except aiohttp.ContentTypeError:
                body = {"error": await r.text()}
            if r.status != 200:
                raise SwitchError(f"{name} failed {r.status}: {body}")
            return body["result"]

    async def list_rooms(self) -> list[dict]:
        return await self.op("list_rooms", {}, on_connection=False)  # type: ignore[return-value]

    async def connect(self, room_id: str) -> dict:
        res = await self.op(
            "connect_to_room", {"room_id": room_id, "include_general_instructions": False}
        )
        self.connected_room = room_id
        return res  # type: ignore[return-value]

    async def list_participants(self, room_id: str) -> list[dict]:
        if self.connected_room != room_id:
            await self.connect(room_id)
        return await self.op("list_participants", {})  # type: ignore[return-value]

    async def post(self, room_id: str, body: str, thread_id: str | None = None, targets: list[str] | None = None) -> dict:
        """post_message, or send_targeted_message when targets are named (so agents get it addressed)."""
        if self.connected_room != room_id:
            await self.connect(room_id)
        args: dict = {"body": body}
        if thread_id:
            args["thread_id"] = thread_id
        if targets:
            args["target_names"] = targets
            return await self.op("send_targeted_message", args)  # type: ignore[return-value]
        return await self.op("post_message", args)  # type: ignore[return-value]

    async def _beat(self) -> None:
        assert self.http
        while True:
            await asyncio.sleep(2)
            try:
                async with self.http.post(
                    f"{self.url}/agents/{self.agent_id}/connection/beat",
                    headers=self._headers,
                    json={"connection_id": self.connection_id},
                ) as r:
                    await r.read()
                    if r.status in (404, 409):
                        log.warning("beat %s: reopening stream", r.status)
                        self._reopen.set()
                        if self._resp is not None:
                            self._resp.close()
                        return
            except aiohttp.ClientError as e:
                log.warning("beat failed: %s", e)

    async def _stream_once(self, rooms: list[str]) -> AsyncIterator[dict]:
        assert self.http
        url = (
            f"{self.url}/agents/{self.agent_id}/events?connection_id={self.connection_id}"
            "&scope=all&filter=all&start_from=head&client=keystead-gate"
        )
        if rooms:
            url += "&rooms=" + ",".join(rooms)
        headers = {**self._headers, "Accept": "text/event-stream"}
        if self.last_event_id:
            headers["Last-Event-ID"] = self.last_event_id
        async with self.http.get(url, headers=headers) as stream:
            if stream.status != 200:
                raise SwitchError(f"stream: {stream.status} {await stream.text()}")
            self._reopen.clear()
            self._resp = stream
            beater = asyncio.create_task(self._beat())
            try:
                data_lines: list[str] = []
                event_id: str | None = None
                event_name: str | None = None
                async for raw in stream.content:
                    if self._reopen.is_set():
                        raise _Reopen()
                    line = raw.decode().rstrip("\r\n")
                    if line.startswith("data:"):
                        data_lines.append(line[5:].strip())
                        continue
                    if line.startswith("id:"):
                        event_id = line[3:].strip()
                        continue
                    if line.startswith("event:"):
                        event_name = line[6:].strip()
                        continue
                    if line or not data_lines:
                        continue
                    try:
                        event = json.loads("\n".join(data_lines))
                    except json.JSONDecodeError:
                        log.error("bad SSE frame: %r", data_lines)
                        data_lines = []
                        continue
                    data_lines = []
                    if event_name:
                        event.setdefault("type", event_name)
                        event_name = None
                    if event_id:
                        self.last_event_id = event_id
                        event_id = None
                    if event.get("type") == "evicted":
                        raise _Reopen()
                    yield event
            finally:
                beater.cancel()

    async def events(self, rooms: list[str]) -> AsyncIterator[dict]:
        """Yield domain events forever, reopening the stream with the same connection id."""
        backoff = 1.0
        while True:
            try:
                async for event in self._stream_once(rooms):
                    backoff = 1.0
                    if event.get("type") == "connection_state":
                        self.connected_room = None
                    yield event
                log.warning("stream ended, reopening")
            except (_Reopen, aiohttp.ClientPayloadError):
                log.warning("reopening stream")
                self.connected_room = None
            except (TimeoutError, aiohttp.ClientError, SwitchError) as e:
                log.error("stream error: %s (retry in %.0fs)", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
