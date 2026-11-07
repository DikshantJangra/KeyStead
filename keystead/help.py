"""The action catalog posted for `@keystead help`. Built from connector models and the rules."""

from __future__ import annotations

import json
import types
import typing

from .config import Rule
from .connectors.base import Connector
from .policy import offered


def _type_name(ann) -> str:
    origin = typing.get_origin(ann)
    if origin is typing.Literal:
        return "|".join(str(a) for a in typing.get_args(ann))
    args = [a for a in typing.get_args(ann) if a is not type(None)]
    if origin in (typing.Union, types.UnionType) and args:
        return _type_name(args[0])
    if origin is typing.Annotated:
        return _type_name(args[0])
    if origin is list:
        return f"list[{_type_name(args[0])}]" if args else "list"
    if origin is dict:
        return "object"
    return getattr(ann, "__name__", str(ann))


def _rule_text(rule: Rule) -> str:
    eff = {"allow": "runs at once", "approve": "needs the client's approval"}[rule.effect]
    conds = []
    for k, c in rule.when.items():
        if c.in_ is not None:
            conds.append(f"{k} in {c.in_}")
        if c.equals is not None:
            conds.append(f"{k} = {c.equals}")
        if c.matches is not None:
            conds.append(f"{k} matches /{c.matches}/")
        if c.ends_with is not None:
            conds.append(f"{k} ends with {c.ends_with}")
    lim = f", max {rule.limit_per_day}/day" if rule.limit_per_day else ""
    return eff + (f" when {', '.join(conds)}" if conds else "") + lim


def catalog(gate_name: str, connectors: dict[str, Connector], rules: list[Rule]) -> str:
    lines = [f"@{gate_name} actions. Anything not listed is denied."]
    for action in sorted(connectors):
        ok = offered(rules, action)
        if not ok:
            continue
        conn = connectors[action]
        model = conn.actions[action]
        lines.append("")
        lines.append(f"{action}: {conn.descriptions.get(action, '')}")
        for _, rule in ok:
            lines.append(f"  policy: {_rule_text(rule)}")
        for fname, f in model.model_fields.items():
            req = "required" if f.is_required() else f"default {json.dumps(f.default)}"
            lines.append(f"  - {fname} ({_type_name(f.annotation)}, {req}): {f.description or ''}")
    lines.append("")
    lines.append("One change per proposal, exactly like this:")
    lines.append(f"@{gate_name} propose")
    lines.append("```keystead")
    lines.append('{"action": "<action>", "params": {...}, "reason": "<why>"}')
    lines.append("```")
    lines.append('The client replies "approve KS-NNNN" or "deny KS-NNNN".')
    return "\n".join(lines)


def listed_actions(connectors: dict[str, Connector], rules: list[Rule]) -> list[str]:
    return sorted(a for a in connectors if offered(rules, a))
