"""keystead init | secret set | register | run | status | revoke | audit verify"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
from pathlib import Path

import typer

from . import cards
from .audit import Ledger
from .config import ConfigError, load_config, load_dotenv, load_env
from .connectors import ConnectorError, build_connectors
from .gate import Gate, GateStartError
from .gate import revoke as do_revoke
from .proposals import Store
from .switch_client import SwitchClient, SwitchError, health
from .switch_client import register as switch_register
from .vault import Vault, VaultError, new_master_key

app = typer.Typer(help="Keystead: your agency does the work, your keys stay with you.", no_args_is_help=True, add_completion=False)
secret_app = typer.Typer(help="Manage secrets in the encrypted vault.", no_args_is_help=True)
audit_app = typer.Typer(help="Inspect the hash-chained audit ledger.", no_args_is_help=True)
app.add_typer(secret_app, name="secret")
app.add_typer(audit_app, name="audit")

EXAMPLE = Path(__file__).resolve().parent.parent / "config" / "keystead.example.yaml"


def _env():
    load_dotenv()
    return load_env()


def _die(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    raise typer.Exit(1)


@app.command()
def init(force: bool = typer.Option(False, help="overwrite an existing config")) -> None:
    """Write config/keystead.yaml and a new master key into .env."""
    env = _env()
    env.data_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(env.data_dir, 0o700)
    if env.config_path.exists() and not force:
        typer.echo(f"{env.config_path} exists, kept (use --force to overwrite)")
    else:
        env.config_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(EXAMPLE, env.config_path)
        typer.echo(f"wrote {env.config_path}; edit room, people, zones")
    dotenv = Path(".env")
    text = dotenv.read_text() if dotenv.exists() else Path(".env.example").read_text() if Path(".env.example").exists() else ""
    if env.master_key:
        typer.echo("KEYSTEAD_MASTER_KEY already set, kept")
        return
    key = new_master_key()
    lines = [ln for ln in text.splitlines() if not ln.startswith("KEYSTEAD_MASTER_KEY=")]
    lines.append(f"KEYSTEAD_MASTER_KEY={key}")
    dotenv.write_text("\n".join(lines) + "\n")
    os.chmod(dotenv, 0o600)
    typer.echo("wrote a new KEYSTEAD_MASTER_KEY to .env (back it up; without it the vault is unreadable)")


@secret_app.command("set")
def secret_set(name: str, value: str = typer.Option(None, hidden=True, help="for scripts; prefer the hidden prompt")) -> None:
    """Store a secret, read with a hidden prompt."""
    env = _env()
    if value is None:
        if not sys.stdin.isatty():
            value = sys.stdin.readline().rstrip("\n")
        else:
            value = typer.prompt(f"value for {name}", hide_input=True, confirmation_prompt=True)
    try:
        Vault(env.data_dir / "vault.json", env.master_key).set(name, value)
    except VaultError as e:
        _die(str(e))
    typer.echo(f"stored {name} in {env.data_dir / 'vault.json'} (encrypted)")


@secret_app.command("list")
def secret_list() -> None:
    """List secret names (never values)."""
    env = _env()
    try:
        for n in Vault(env.data_dir / "vault.json", env.master_key).names():
            typer.echo(n)
    except VaultError as e:
        _die(str(e))


@app.command()
def register(overwrite: bool = typer.Option(False, help="replace an existing agent with this name")) -> None:
    """Register the gate with Switch as a custom always-on agent owned by the client."""
    env = _env()
    try:
        cfg = load_config(env.config_path)
    except ConfigError as e:
        _die(str(e))
    if not env.reg_token:
        _die("KEYSTEAD_REG_TOKEN is not set (the client's Switch registration token)")
    try:
        code = asyncio.run(health(env.switch_url))
    except Exception as e:
        _die(f"cannot reach SWITCH_URL={env.switch_url}: {e}")
    if code != 200:
        _die(f"GET {env.switch_url}/health returned {code}; 401 means right host, wrong path")
    try:
        agent = asyncio.run(switch_register(env.switch_url, env.reg_token, cfg.gate.name, "Client-owned key-holder. No LLM. Runs allowlisted actions only after the client types approve.", overwrite))
    except SwitchError as e:
        _die(str(e))
    env.data_dir.mkdir(parents=True, exist_ok=True)
    f = env.data_dir / "agent.json"
    f.write_text(json.dumps(agent, indent=2))
    os.chmod(f, 0o600)
    typer.echo(f"registered @{cfg.gate.name} (id {agent['id']}); key saved to {f}.")
    typer.echo(f"Next, in Switch Console: set @{cfg.gate.name}'s addressing to 'anyone' (the gate does its own checks)")
    typer.echo(f"and add @{cfg.gate.name} to room {cfg.switch.room}.")


def _open_all(env):
    cfg = load_config(env.config_path)
    vault = Vault(env.data_dir / "vault.json", env.master_key)
    connectors = build_connectors(cfg)
    missing = sorted({c.secret_name for c in connectors.values()} - set(vault.names()))
    if missing:
        raise VaultError(f"missing secret(s) {missing}; run `keystead secret set <name>`")
    return cfg, vault, connectors


@app.command()
def run(verbose: bool = typer.Option(False, "-v")) -> None:
    """Run the gate: connect, post 'keystead online', handle the room."""
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    env = _env()
    try:
        cfg, vault, connectors = _open_all(env)
    except (ConfigError, VaultError, ConnectorError) as e:
        _die(str(e))

    async def main() -> None:
        async with SwitchClient(env.switch_url, env.data_dir / "agent.json") as client:
            gate = Gate(cfg, client, Store(env.data_dir / "keystead.db"), Ledger(env.data_dir / "audit.jsonl"), vault, connectors)
            await gate.run()

    try:
        asyncio.run(main())
    except (GateStartError, SwitchError) as e:
        _die(f"gate refused to start: {e}")
    except KeyboardInterrupt:
        pass


@app.command()
def status() -> None:
    """Show pending and recent proposals and the ledger state."""
    env = _env()
    store = Store(env.data_dir / "keystead.db")
    ok, msg = Ledger(env.data_dir / "audit.jsonl").verify()
    typer.echo(cards.status(store.get_state("paused") == "1", store.get_state("revoked") == "1", store.pending(), store.recent(10), msg))


@app.command()
def revoke(undo: bool = typer.Option(False, "--undo", help="restore proposer access")) -> None:
    """Empty the proposer list, cancel pending proposals, log it."""
    env = _env()
    store = Store(env.data_dir / "keystead.db")
    ledger = Ledger(env.data_dir / "audit.jsonl")
    actor = os.environ.get("USER", "cli")
    if undo:
        store.set_state("revoked", "0")
        ledger.append("resumed", None, f"cli:{actor}", actor, None, "proposer access restored")
        typer.echo("proposer access restored")
        return
    cancelled = do_revoke(store, ledger, f"cli:{actor}", actor)
    typer.echo(f"revoked. cancelled: {', '.join(cancelled) or 'none'}. Also remove the agency agent from the room.")


@app.command()
def identities(reset: bool = typer.Option(False, "--reset", help="forget every pinned sender id")) -> None:
    """Show which Switch sender id each person and agent is pinned to."""
    env = _env()
    store = Store(env.data_dir / "keystead.db")
    if reset:
        store.clear_identities()
        Ledger(env.data_dir / "audit.jsonl").append("pinned", None, f"cli:{os.environ.get('USER', 'cli')}", None, None, "all identities reset")
        typer.echo("identities reset; the next message from each participant pins it again")
        return
    rows = store.identities()
    if not rows:
        typer.echo("no identities pinned yet")
    for name, kind, sid, _ in rows:
        typer.echo(f"{name:<24} {kind:<6} {sid}")


@audit_app.command("verify")
def audit_verify() -> None:
    """Recompute the hash chain; name the first broken line."""
    env = _env()
    ok, msg = Ledger(env.data_dir / "audit.jsonl").verify()
    if not ok:
        _die(f"BROKEN: {msg}")
    typer.secho(msg, fg=typer.colors.GREEN)


@audit_app.command("show")
def audit_show(n: int = 20) -> None:
    """Print the last N ledger lines."""
    env = _env()
    for line in Ledger(env.data_dir / "audit.jsonl").lines()[-n:]:
        typer.echo(json.dumps(line))


if __name__ == "__main__":
    app()
