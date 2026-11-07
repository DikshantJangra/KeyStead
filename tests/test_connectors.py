import pytest

from keystead.connectors.cloudflare_dns import AddRecord, DeleteRecord, ListRecords
from keystead.connectors.octodns_dns import AddRecord as OAdd
from keystead.connectors.octodns_dns import DeleteRecord as ODel
from keystead.connectors.octodns_dns import ListRecords as OList
from keystead.connectors.octodns_dns import OctoDNS

from .conftest import SECRET


async def test_cloudflare_create_gets_exact_params(connectors, fake_cf):
    c = connectors["dns.add_record"]
    p = AddRecord(zone="clientsite.com", type="TXT", name="@", content="google-site-verification=abc123", ttl=1)
    r = await c.execute("dns.add_record", p, SECRET)
    cf = fake_cf.instances[0]
    assert cf.api_token == SECRET
    assert cf.records.created == [{"zone_id": "zone-123", "type": "TXT", "name": "clientsite.com", "content": "google-site-verification=abc123", "ttl": 1}]
    assert r.ok and r.external_id == "9f2c0000aaaa"


async def test_cloudflare_delete_and_list(connectors, fake_cf):
    c = connectors["dns.delete_record"]
    await c.execute("dns.delete_record", DeleteRecord(zone="clientsite.com", record_id="abc123"), SECRET)
    assert fake_cf.instances[0].records.deleted == [("abc123", "zone-123")]
    r = await c.execute("dns.list_records", ListRecords(zone="clientsite.com"), SECRET)
    assert "1 record(s)" in r.summary


async def test_cloudflare_unknown_zone(connectors):
    with pytest.raises(Exception, match="not found"):
        await connectors["dns.add_record"].execute("dns.add_record", AddRecord(zone="nope.com", type="TXT", name="@", content="x"), SECRET)


async def test_octodns_add_and_delete_with_real_yaml_provider(tmp_path):
    from octodns.provider.yaml import YamlProvider

    c = OctoDNS("tok", ["clientsite.com"], "unused.Provider", "token",
                provider_factory=lambda secret: YamlProvider("keystead", str(tmp_path), supports_root_ns=False))
    r = await c.execute("dns.add_record", OAdd(zone="clientsite.com", type="TXT", name="@", content="a=b;c"), "tok")
    assert r.ok and r.external_id == "TXT:@"
    text = (tmp_path / "clientsite.com.yaml").read_text()
    assert "a=b\\;c" in text
    r = await c.execute("dns.add_record", OAdd(zone="clientsite.com", type="TXT", name="@", content="a=b;c"), "tok")
    assert "nothing changed" in r.summary
    r = await c.execute("dns.add_record", OAdd(zone="clientsite.com", type="CNAME", name="www", content="host.example.net"), "tok")
    assert r.ok
    r = await c.execute("dns.list_records", OList(zone="clientsite.com"), "tok")
    assert "TXT:@" in r.summary and "CNAME:www" in r.summary
    r = await c.execute("dns.delete_record", ODel(zone="clientsite.com", record_id="CNAME:www"), "tok")
    assert r.ok and "www" not in (tmp_path / "clientsite.com.yaml").read_text()
