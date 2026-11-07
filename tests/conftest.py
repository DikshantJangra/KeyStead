from __future__ import annotations

import base64
import os
from types import SimpleNamespace

import pytest

from keystead.config import KeysteadConfig
from keystead.connectors.cloudflare_dns import CloudflareDNS

SECRET = "cf-SECRET-token-0123456789abcdef"

CFG = {
    "switch": {"room": "keystead-clientsite"},
    "gate": {"name": "keystead", "proposal_ttl_minutes": 30},
    "people": {"approvers": ["client"], "proposers": ["clientsite-agency", "dj"]},
    "connectors": {"cloudflare_dns": {"secret": "cloudflare_token", "zones": ["clientsite.com"]}},
    "rules": [
        {"action": "dns.list_records", "effect": "allow"},
        {"action": "dns.add_record", "when": {"zone": {"in": ["clientsite.com"]}, "type": {"in": ["TXT", "CNAME"]}}, "effect": "approve", "limit_per_day": 10},
        {"action": "dns.delete_record", "effect": "approve"},
        {"action": "*", "effect": "deny"},
    ],
}


@pytest.fixture
def cfg() -> KeysteadConfig:
    return KeysteadConfig.model_validate(CFG)


class FakeRecords:
    def __init__(self):
        self.created: list[dict] = []
        self.deleted: list[tuple] = []

    async def create(self, **kw):
        self.created.append(kw)
        return SimpleNamespace(id="9f2c0000aaaa", model_dump=lambda mode="json": {"id": "9f2c0000aaaa", **kw})

    async def delete(self, record_id, *, zone_id):
        self.deleted.append((record_id, zone_id))

    def list(self, **kw):
        async def gen():
            yield SimpleNamespace(id="r1", type="TXT", name="clientsite.com", content="v=spf1", ttl=1)

        return gen()


class FakeCF:
    """Stands in for cloudflare.AsyncCloudflare; records every call and the token it was given."""

    instances: list[FakeCF] = []

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.records = FakeRecords()
        self.dns = SimpleNamespace(records=self.records)
        self.zones = SimpleNamespace(list=self._zones)
        FakeCF.instances.append(self)

    def _zones(self, name: str):
        async def gen():
            if name == "clientsite.com":
                yield SimpleNamespace(id="zone-123")

        return gen()


@pytest.fixture
def fake_cf():
    FakeCF.instances = []
    return FakeCF


@pytest.fixture
def connectors(fake_cf):
    c = CloudflareDNS("cloudflare_token", ["clientsite.com"], client_factory=fake_cf)
    return {a: c for a in c.actions}


@pytest.fixture
def master_key() -> str:
    return base64.b64encode(os.urandom(32)).decode()
