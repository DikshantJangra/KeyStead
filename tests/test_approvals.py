import pytest

from keystead.approvals import Rejected, check_proposal, check_sender, parse_decision
from keystead.proposals import Store, now_ms, parse_block

from .test_proposals import GOOD

CLIENT = "@switch-user-c1:local"
DJ = "@switch-user-dj:local"
AGENCY = "@switch-agent-ag:local"
APPROVERS = {CLIENT}
AGENTS = {AGENCY, "@switch-agent-gate:local"}


def test_parse():
    assert parse_decision("approve KS-0007").verb == "approve"
    assert parse_decision("  DENY ks-0007 ").proposal_id == "KS-0007"
    assert parse_decision("please approve KS-0007") is None
    assert parse_decision("approve KS-0007 and KS-0008") is None
    assert parse_decision("approve KS-07") is None


def test_client_passes():
    check_sender(CLIENT, "user", None, APPROVERS, AGENTS, "KS-0001")


@pytest.mark.parametrize(
    "sender,kind,obo,msg",
    [
        (DJ, "user", None, "Only the client"),
        (AGENCY, None, None, "Agents never"),
        (AGENCY, "agent", None, "Agents never"),
        (CLIENT, "platform", None, "on someone's behalf"),
        (CLIENT, None, "client", "on someone's behalf"),
    ],
)
def test_rejects(sender, kind, obo, msg):
    with pytest.raises(Rejected, match=msg):
        check_sender(sender, kind, obo, APPROVERS, AGENTS, "KS-0001")


@pytest.fixture
def prop(tmp_path, connectors):
    s = Store(tmp_path / "k.db")
    return s, s.create(parse_block(GOOD, connectors), AGENCY, "agency", "room", None, 30)


def test_pending_ok(prop):
    s, p = prop
    assert check_proposal(s.get(p.id), p.id).id == p.id


def test_unknown_id(prop):
    with pytest.raises(Rejected, match="does not exist"):
        check_proposal(None, "KS-9999")


def test_expired(prop):
    s, p = prop
    with pytest.raises(Rejected, match="expired") as e:
        check_proposal(s.get(p.id), p.id, now=p.expires_at)
    assert e.value.expired


def test_already_decided(prop):
    s, p = prop
    s.transition(p.id, "pending", "executed")
    with pytest.raises(Rejected, match="already executed"):
        check_proposal(s.get(p.id), p.id)


def test_changed_hash(prop):
    s, p = prop
    s.db.execute("DROP TRIGGER proposals_immutable")
    s.db.execute("UPDATE proposals SET params=? WHERE id=?", ('{"zone":"clientsite.com","type":"TXT","name":"@","content":"EVIL","ttl":1,"proxied":null,"priority":null}', p.id))
    with pytest.raises(Rejected, match="changed"):
        check_proposal(s.get(p.id), p.id, now=now_ms())
