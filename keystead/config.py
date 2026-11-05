"""Load config/keystead.yaml and the environment into pydantic models."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


class ConfigError(Exception):
    pass


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SwitchCfg(Strict):
    room: str


class GateCfg(Strict):
    name: str = "keystead"
    proposal_ttl_minutes: int = Field(30, gt=0, le=24 * 60)


class PeopleCfg(Strict):
    approvers: list[str] = Field(min_length=1)
    proposers: list[str] = []
    # Optional strict mode: name -> Switch sender id (the `sender` field of a message,
    # shown by `keystead identities`). Without it the first message from a room
    # participant pins its sender id, and a later different id for that name is refused.
    pins: dict[str, str] = {}

    @model_validator(mode="after")
    def _disjoint(self) -> PeopleCfg:
        self.approvers = [n.casefold() for n in self.approvers]
        self.proposers = [n.casefold() for n in self.proposers]
        self.pins = {k.casefold(): v for k, v in self.pins.items()}
        both = set(self.approvers) & set(self.proposers)
        if both:
            raise ValueError(f"{sorted(both)} cannot be both approver and proposer")
        return self


class ConnectorCfg(BaseModel):
    model_config = ConfigDict(extra="allow")
    secret: str
    zones: list[str] | None = None


class Condition(Strict):
    equals: Any = None
    in_: list[Any] | None = Field(None, alias="in")
    matches: str | None = None
    ends_with: str | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="after")
    def _one_op(self) -> Condition:
        ops = [k for k in ("equals", "in_", "matches", "ends_with") if getattr(self, k) is not None]
        if not ops:
            raise ValueError("a condition needs one of equals, in, matches, ends_with")
        return self


class Rule(Strict):
    action: str
    when: dict[str, Condition] = {}
    effect: Literal["allow", "approve", "deny"]
    limit_per_day: int | None = Field(None, gt=0)


class KeysteadConfig(Strict):
    switch: SwitchCfg
    gate: GateCfg = GateCfg()
    people: PeopleCfg
    connectors: dict[str, ConnectorCfg] = {}
    rules: list[Rule] = Field(min_length=1)

    @field_validator("connectors")
    @classmethod
    def _known(cls, v: dict[str, ConnectorCfg]) -> dict[str, ConnectorCfg]:
        known = {"cloudflare_dns", "octodns_dns", "postiz_social"}
        bad = set(v) - known
        if bad:
            raise ValueError(f"unknown connector(s) {sorted(bad)}; known: {sorted(known)}")
        return v


class Env(BaseModel):
    switch_url: str
    reg_token: str | None
    master_key: str | None
    data_dir: Path
    config_path: Path


def load_env() -> Env:
    return Env(
        switch_url=os.environ.get("SWITCH_URL", "http://localhost:8000").rstrip("/"),
        reg_token=os.environ.get("KEYSTEAD_REG_TOKEN") or None,
        master_key=os.environ.get("KEYSTEAD_MASTER_KEY") or None,
        data_dir=Path(os.environ.get("KEYSTEAD_DATA_DIR", "./data")),
        config_path=Path(os.environ.get("KEYSTEAD_CONFIG", "./config/keystead.yaml")),
    )


def load_config(path: Path) -> KeysteadConfig:
    if not path.exists():
        raise ConfigError(f"config not found: {path} (run `keystead init`)")
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"{path}: not valid YAML: {e}") from e
    try:
        return KeysteadConfig.model_validate(raw)
    except ValidationError as e:
        lines = [f"{path}: invalid config"]
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"]) or "(root)"
            lines.append(f"  {loc}: {err['msg']}")
        raise ConfigError("\n".join(lines)) from e


def load_dotenv(path: Path = Path(".env")) -> None:
    """Minimal .env reader; real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
