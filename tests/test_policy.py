import pytest

from keystead.config import ConfigError, KeysteadConfig, Rule, load_config
from keystead.help import catalog, listed_actions
from keystead.policy import evaluate

TXT = {"zone": "clientsite.com", "type": "TXT", "name": "@", "content": "x"}


def ev(cfg, action, params, used=0):
    return evaluate(cfg.rules, action, params, lambda a: used)


def test_allow(cfg):
    assert ev(cfg, "dns.list_records", {"zone": "clientsite.com"}).effect == "allow"


def test_approve(cfg):
    d = ev(cfg, "dns.add_record", TXT)
    assert d.effect == "approve" and d.rule_index == 1


def test_condition_miss_falls_to_catch_all_deny(cfg):
    assert ev(cfg, "dns.add_record", {**TXT, "type": "A"}).effect == "deny"
    assert ev(cfg, "dns.add_record", {**TXT, "type": "txt"}).effect == "approve"  # case-insensitive


def test_catch_all_deny(cfg):
    d = ev(cfg, "social.publish_post", {})
    assert d.effect == "deny" and d.rule_index == 3


def test_default_deny_without_catch_all():
    rules = [Rule(action="dns.list_records", effect="allow")]
    d = evaluate(rules, "dns.add_record", TXT, lambda a: 0)
    assert d.effect == "deny" and d.rule_index is None


def test_limit_per_day(cfg):
    assert ev(cfg, "dns.add_record", TXT, used=9).effect == "approve"
    d = ev(cfg, "dns.add_record", TXT, used=10)
    assert d.effect == "deny" and "daily limit" in d.reason


def test_fail_closed_polarity():
    allow = Rule.model_validate({"action": "dns.*", "when": {"name": {"ends_with": ".dev"}}, "effect": "allow"})
    approve = Rule.model_validate({"action": "dns.*", "when": {"name": {"matches": "www|api"}}, "effect": "approve"})
    # name absent: allow must not grant, approve must still catch it
    assert evaluate([allow, approve], "dns.list_records", {}, lambda a: 0).effect == "approve"
    assert evaluate([allow], "dns.list_records", {}, lambda a: 0).effect == "deny"
    assert evaluate([allow], "dns.list_records", {"name": "x.DEV"}, lambda a: 0).effect == "allow"
    assert evaluate([approve], "dns.x", {"name": "wwwx"}, lambda a: 0).effect == "deny"  # fullmatch


def test_equals_and_glob():
    r = Rule.model_validate({"action": "dns.add_*", "when": {"type": {"equals": "TXT"}}, "effect": "approve"})
    assert evaluate([r], "dns.add_record", {"type": "TXT"}, lambda a: 0).effect == "approve"
    assert evaluate([r], "dns.delete_record", {"type": "TXT"}, lambda a: 0).effect == "deny"


def test_help_lists_only_offered(cfg, connectors):
    assert listed_actions(connectors, cfg.rules) == ["dns.add_record", "dns.delete_record", "dns.list_records"]
    raw = cfg.model_dump(by_alias=True)
    raw["rules"] = [r for r in raw["rules"] if r["action"] != "dns.delete_record"]
    cfg2 = KeysteadConfig.model_validate(raw)
    assert "dns.delete_record" not in listed_actions(connectors, cfg2.rules)
    assert "dns.delete_record:" not in catalog("keystead", connectors, cfg2.rules)
    shadowed = [Rule(action="*", effect="deny"), Rule(action="dns.list_records", effect="allow")]
    assert listed_actions(connectors, shadowed) == []


def test_bad_config_message(tmp_path):
    p = tmp_path / "k.yaml"
    p.write_text("switch: {room: r}\npeople: {approvers: [client], proposers: [client]}\nrules: [{action: '*', effect: maybe}]\n")
    with pytest.raises(ConfigError) as e:
        load_config(p)
    msg = str(e.value)
    assert "invalid config" in msg and "rules.0.effect" in msg and "both approver and proposer" in msg
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "missing.yaml")
