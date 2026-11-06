from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class Receipt(BaseModel):
    ok: bool
    summary: str
    external_id: str | None = None
    raw: dict[str, Any] = {}


class Params(BaseModel):
    """Base for every action's params: unknown keys are an error, values are immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ConnectorError(Exception):
    pass


@runtime_checkable
class Connector(Protocol):
    name: str
    actions: dict[str, type[BaseModel]]
    secret_name: str
    descriptions: dict[str, str]

    def check(self, action: str, p: BaseModel) -> None:
        """Raise ConnectorError if params fall outside this connector's configured scope."""
        ...

    def preview(self, action: str, p: BaseModel) -> str: ...

    async def execute(self, action: str, p: BaseModel, secret: str) -> Receipt: ...


def target_of(p: BaseModel) -> str | None:
    for field in ("zone", "integration", "channel"):
        v = getattr(p, field, None)
        if v:
            return str(v)
    return None
