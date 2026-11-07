import os

from typer.testing import CliRunner

from keystead.cli import app


def test_cli_end_to_end(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for k in ("KEYSTEAD_MASTER_KEY", "KEYSTEAD_DATA_DIR", "KEYSTEAD_CONFIG", "KEYSTEAD_REG_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    r = CliRunner()
    help_out = r.invoke(app, ["--help"]).output
    for cmd in ("init", "secret", "register", "run", "status", "revoke", "audit", "identities"):
        assert cmd in help_out
    assert r.invoke(app, ["init"]).exit_code == 0
    assert (tmp_path / "config" / "keystead.yaml").exists()
    assert "KEYSTEAD_MASTER_KEY=" in (tmp_path / ".env").read_text()
    out = r.invoke(app, ["secret", "set", "cloudflare_token"], input="tok-cli-SECRET-123\n")
    assert out.exit_code == 0, out.output
    assert b"tok-cli-SECRET-123" not in (tmp_path / "data" / "vault.json").read_bytes()
    assert "cloudflare_token" in r.invoke(app, ["secret", "list"]).output
    assert "revoked" in r.invoke(app, ["revoke"]).output
    assert "proposers revoked" in r.invoke(app, ["status"]).output
    assert r.invoke(app, ["audit", "verify"]).exit_code == 0
    lines = (tmp_path / "data" / "audit.jsonl").read_text().splitlines()
    (tmp_path / "data" / "audit.jsonl").write_text(lines[0].replace("revoked", "resumed") + "\n")
    bad = r.invoke(app, ["audit", "verify"])
    assert bad.exit_code == 1 and "line 1" in bad.output
    reg = r.invoke(app, ["register"])
    assert reg.exit_code == 1 and "KEYSTEAD_REG_TOKEN" in reg.output
    os.environ.pop("KEYSTEAD_MASTER_KEY", None)
