import json

import pytest

from keystead.audit import Ledger
from keystead.vault import Redactor, Vault, VaultError


def test_chain_and_tamper(tmp_path):
    led = Ledger(tmp_path / "audit.jsonl")
    for i in range(5):
        led.append("proposed", f"KS-000{i}", "@a:x", "agency", "h" * 64)
    ok, msg = led.verify()
    assert ok and "5 lines" in msg

    lines = (tmp_path / "audit.jsonl").read_text().splitlines()
    edited = json.loads(lines[2])
    edited["actor_name"] = "client"
    lines[2] = json.dumps(edited, sort_keys=True, separators=(",", ":"))
    (tmp_path / "audit.jsonl").write_text("\n".join(lines) + "\n")
    ok, msg = led.verify()
    assert not ok and msg.startswith("line 3 ") and "edited" in msg


def test_deleted_line(tmp_path):
    led = Ledger(tmp_path / "audit.jsonl")
    for _ in range(3):
        led.append("approved")
    lines = (tmp_path / "audit.jsonl").read_text().splitlines()
    (tmp_path / "audit.jsonl").write_text("\n".join([lines[0], lines[2]]) + "\n")
    ok, msg = led.verify()
    assert not ok and msg.startswith("line 2 ")


def test_vault_encrypts(tmp_path, master_key):
    v = Vault(tmp_path / "vault.json", master_key)
    v.set("cloudflare_token", "super-secret-value-123")
    raw = (tmp_path / "vault.json").read_text()
    assert "super-secret-value-123" not in raw
    assert v.get("cloudflare_token") == "super-secret-value-123"
    v.set("other", "super-secret-value-123")
    data = json.loads(raw if False else (tmp_path / "vault.json").read_text())
    assert data["cloudflare_token"]["nonce"] != data["other"]["nonce"]
    with pytest.raises(VaultError, match="cannot be decrypted"):
        Vault(tmp_path / "vault.json", master_key[:-4] + "AAA=").get("cloudflare_token")
    with pytest.raises(VaultError):
        Vault(tmp_path / "vault.json", None)


def test_redactor():
    r = Redactor(["tok-ABCDEF"])
    assert r("Bearer tok-ABCDEF failed") == "Bearer [redacted] failed"
    assert r.scrub({"a": ["tok-ABCDEF"]}) == {"a": ["[redacted]"]}
