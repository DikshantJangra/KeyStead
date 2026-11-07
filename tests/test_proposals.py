import pytest

from keystead.proposals import ProposalError, Store, parse_block, payload_hash

GOOD = """@keystead propose
```keystead
{"action": "dns.add_record",
 "params": {"zone": "clientsite.com", "type": "TXT", "name": "@",
            "content": "google-site-verification=abc123", "ttl": 1},
 "reason": "Verify clientsite.com in Google Search Console"}
```"""


def test_good_block(connectors):
    p = parse_block(GOOD, connectors)
    assert p.action == "dns.add_record"
    assert p.params_json["content"] == "google-site-verification=abc123"
    assert p.params_json["zone"] == "clientsite.com"
    assert p.payload_hash == payload_hash("dns.add_record", p.params_json)
    assert len(p.payload_hash) == 64


def test_hash_is_canonical(connectors):
    a = parse_block(GOOD, connectors)
    reordered = GOOD.replace('"zone": "clientsite.com", "type": "TXT"', '"type": "TXT", "zone": "ClientSite.com."')
    assert parse_block(reordered, connectors).payload_hash == a.payload_hash


@pytest.mark.parametrize(
    "body,err",
    [
        ("@keystead propose add a txt record please", "no ```keystead block"),
        ("@keystead propose\n```keystead\n{not json}\n```", "not valid JSON"),
        ('@keystead propose\n```keystead\n{"action": "dns.add_record", "params": {}}\n```', "reason"),
        ('@keystead propose\n```keystead\n{"action": "shell.exec", "params": {}, "reason": "x"}\n```', "unknown action"),
        ('@keystead propose\n```keystead\n{"action": "dns.add_record", "params": {"zone": "clientsite.com", "type": "TXT", "name": "@", "content": "x", "evil": 1}, "reason": "x"}\n```', "evil"),
        ('@keystead propose\n```keystead\n{"action": "dns.add_record", "params": {"zone": "other.com", "type": "TXT", "name": "@", "content": "x"}, "reason": "x"}\n```', "not managed"),
        ('@keystead propose\n```keystead\n{"action": "dns.add_record", "params": {"zone": "clientsite.com", "type": "PTR", "name": "@", "content": "x"}, "reason": "x"}\n```', "type"),
        ('@keystead propose\n```keystead\n{"action": "dns.add_record", "params": {"zone": "clientsite.com", "type": "TXT", "name": "foo bar", "content": "x"}, "reason": "x"}\n```', "whitespace or newlines"),
        ('@keystead propose\n```keystead\n{"action": "dns.add_record", "params": {"zone": "clientsite.com", "type": "TXT", "name": "foo\\nbar", "content": "x"}, "reason": "x"}\n```', "whitespace or newlines"),
        ('@keystead propose\n```keystead\n{"action": "dns.add_record", "params": {"zone": "clientsite.com", "type": "TXT", "name": "@", "content": "x"}, "reason": "1"}\n```\n```keystead\n{"action": "dns.add_record", "params": {"zone": "clientsite.com", "type": "TXT", "name": "@", "content": "x"}, "reason": "2"}\n```', "multiple ```keystead blocks"),
    ],
)
def test_bad_blocks(connectors, body, err):
    with pytest.raises(ProposalError, match=err):
        parse_block(body, connectors)


def test_store_ids_and_immutability(tmp_path, connectors):
    s = Store(tmp_path / "k.db")
    parsed = parse_block(GOOD, connectors)
    a = s.create(parsed, "@a:x", "agency", "room", None, 30)
    b = s.create(parsed, "@a:x", "agency", "room", None, 30)
    assert (a.id, b.id) == ("KS-0001", "KS-0002")
    assert a.status == "pending" and a.expires_at - a.created_at == 30 * 60_000
    with pytest.raises(Exception, match="immutable"):
        s.db.execute("UPDATE proposals SET params='{}' WHERE id='KS-0001'")
    assert s.transition("KS-0001", "pending", "approved", "@c:x")
    assert not s.transition("KS-0001", "pending", "approved", "@c:x")
