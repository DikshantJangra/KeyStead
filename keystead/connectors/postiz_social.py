"""social.publish_post through a separately running Postiz (AGPL-3.0, HTTP only).

Endpoint read from gitroomhq/postiz-app apps/backend/src/public-api/routes/v1/
public.integrations.controller.ts: GET /public/v1/integrations and
POST /public/v1/posts, with the raw API key in the Authorization header.

Config:
  postiz_social:
    secret: postiz_api_key
    base_url: http://localhost:5000/api   # self-hosted backend; cloud is https://api.postiz.com
    integrations: [clientsite-instagram]  # channel names (or ids) the agency may post to
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import aiohttp
from pydantic import BaseModel, Field, field_validator

from .base import ConnectorError, Params, Receipt


class PublishPost(Params):
    integration: str = Field(min_length=1, description="Postiz channel name or id")
    content: str = Field(min_length=1, max_length=5000, description="post text")
    when: str = Field("now", description='"now", or an ISO-8601 time to schedule it')
    image_urls: list[str] = Field([], max_length=10, description="media already uploaded to Postiz")
    settings: dict[str, str] = Field({}, description="provider settings, e.g. {\"post_type\": \"post\"}")

    @field_validator("when")
    @classmethod
    def _when(cls, v: str) -> str:
        if v == "now":
            return v
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError('when must be "now" or an ISO-8601 time') from e
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


class PostizSocial:
    name = "postiz_social"
    actions: dict[str, type[BaseModel]] = {"social.publish_post": PublishPost}
    descriptions = {"social.publish_post": "Publish or schedule one social post via Postiz"}

    def __init__(self, secret_name: str, base_url: str, integrations: list[str] | None, session_factory=aiohttp.ClientSession):
        self.secret_name = secret_name
        self.base_url = base_url.rstrip("/")
        self.integrations = set(integrations) if integrations else None
        self.session_factory = session_factory

    def check(self, action: str, p: Any) -> None:
        if self.integrations is not None and p.integration not in self.integrations:
            raise ConnectorError(f"channel {p.integration} is not managed by this gate")

    def preview(self, action: str, p: Any) -> str:
        text = p.content if len(p.content) <= 280 else p.content[:277] + "..."
        media = f"  +{len(p.image_urls)} image(s)" if p.image_urls else ""
        when = "publish now" if p.when == "now" else f"schedule for {p.when}"
        return f'{when} on {p.integration}: "{text}"{media}'

    async def execute(self, action: str, p: Any, secret: str) -> Receipt:
        if action != "social.publish_post":
            raise ConnectorError(f"unknown action {action}")
        headers = {"Authorization": secret, "Content-Type": "application/json"}
        async with self.session_factory() as http:
            async with http.get(f"{self.base_url}/public/v1/integrations", headers=headers) as r:
                if r.status != 200:
                    raise ConnectorError(f"Postiz integrations: {r.status} {await r.text()}")
                channels = await r.json()
            ch = next((c for c in channels if p.integration in (c.get("id"), c.get("name"))), None)
            if ch is None:
                raise ConnectorError(f"Postiz has no channel {p.integration}")
            if ch.get("disabled"):
                raise ConnectorError(f"Postiz channel {p.integration} is disabled")
            now = p.when == "now"
            body = {
                "type": "now" if now else "schedule",
                "shortLink": False,
                "date": datetime.now(UTC).isoformat().replace("+00:00", "Z") if now else p.when,
                "tags": [],
                "posts": [
                    {
                        "integration": {"id": ch["id"]},
                        "value": [{"content": p.content, "image": [{"id": u, "path": u} for u in p.image_urls]}],
                        "settings": {"__type": ch.get("identifier"), **p.settings},
                    }
                ],
            }
            async with http.post(f"{self.base_url}/public/v1/posts", headers=headers, json=body) as r:
                text = await r.text()
                if r.status not in (200, 201):
                    raise ConnectorError(f"Postiz post: {r.status} {text[:300]}")
                try:
                    res = await r.json(content_type=None)
                except Exception:
                    res = {"text": text[:500]}
        post_id = None
        if isinstance(res, list) and res:
            post_id = res[0].get("postId") or res[0].get("id")
        elif isinstance(res, dict):
            post_id = res.get("postId") or res.get("id")
        verb = "published" if now else f"scheduled for {p.when}"
        return Receipt(ok=True, summary=f"post {verb} on {ch.get('name', p.integration)}", external_id=post_id, raw={"response": res})

