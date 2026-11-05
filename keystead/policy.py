"""allow / approve / deny. First matching rule wins, default deny.

Condition matching evaluation: every condition in a rule must hold (AND), and a
condition that cannot be evaluated (the param is absent) resolves by the rule's
polarity, fail-closed: a restrictive rule (approve, deny) treats it as matched,
a permissive rule (allow) treats it as not matched. Doubt can only make a
request stricter, never looser."""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .config import Condition, Rule

_MISSING = object()


@dataclass(frozen=True)
class Decision:
    effect: str  # allow | approve | deny
    rule_index: int | None
    reason: str


def _norm(v: Any) -> Any:
    return v.casefold() if isinstance(v, str) else v


def condition_holds(c: Condition, value: Any, restrictive: bool) -> bool:
    if value is _MISSING or value is None:
        return restrictive
    if c.equals is not None and _norm(value) != _norm(c.equals):
        return False
    if c.in_ is not None and _norm(value) not in {_norm(x) for x in c.in_}:
        return False
    if c.matches is not None and (not isinstance(value, str) or re.fullmatch(c.matches, value) is None):
        return False
    if c.ends_with is not None and (not isinstance(value, str) or not value.casefold().endswith(c.ends_with.casefold())):
        return False
    return True


def rule_matches(rule: Rule, action: str, params: dict[str, Any]) -> bool:
    if not fnmatch.fnmatchcase(action, rule.action):
        return False
    restrictive = rule.effect != "allow"
    return all(condition_holds(c, params.get(k, _MISSING), restrictive) for k, c in rule.when.items())


def evaluate(rules: list[Rule], action: str, params: dict[str, Any], count_today: Callable[[str], int]) -> Decision:
    for i, rule in enumerate(rules):
        if not rule_matches(rule, action, params):
            continue
        if rule.effect != "deny" and rule.limit_per_day is not None:
            used = count_today(action)
            if used >= rule.limit_per_day:
                return Decision("deny", i, f"daily limit of {rule.limit_per_day} {action} reached")
        reason = {"allow": f"allowed by rule {i + 1}", "approve": f"needs approval (rule {i + 1})", "deny": f"denied by rule {i + 1}"}[rule.effect]
        return Decision(rule.effect, i, reason)
    return Decision("deny", None, "no rule matches, default deny")


def offered(rules: list[Rule], action: str) -> list[tuple[int, Rule]]:
    """Rules that could allow or send this action for approval, in order, stopping at an
    unconditional deny that would shadow everything after it."""
    out = []
    for i, rule in enumerate(rules):
        if not fnmatch.fnmatchcase(action, rule.action):
            continue
        if rule.effect == "deny":
            if not rule.when:
                break
            continue
        out.append((i, rule))
        if not rule.when:
            break
    return out
