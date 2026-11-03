"""Regeln: ["ri",[min,max]] und ["rc",[[...]]]."""

from __future__ import annotations

from .values import ParamError, Source, as_number, format_value, type_name

# Grenze für "ri", damit die Spanne sicher in einen int passt (wie go-02).
MAX_RULE_BOUND = 1 << 31


def as_rule(v: object) -> tuple[str, list[object]] | None:
    """Erkennt eine Regel: Array der Länge 2 aus Text und Array."""
    if isinstance(v, list) and len(v) == 2:
        name, args = v
        if isinstance(name, str) and isinstance(args, list):
            return name, args
    return None


def eval_rule(name: str, args: list[object], src: Source) -> object:
    """Wertet eine Regel aus."""
    if name == "ri":
        return _random_int(args, src)
    if name == "rc":
        return _random_choice(args, src)
    raise ParamError(f'unknown rule "{name}"')


def _random_int(args: list[object], src: Source) -> int:
    if len(args) != 2:
        raise ParamError(f"rule ri: want [min,max], got {len(args)} arguments")
    lo, hi = as_number(args[0]), as_number(args[1])
    if lo is None or hi is None or not lo.is_integer() or not hi.is_integer():
        raise ParamError(
            f"rule ri: min and max must be integers, got {format_value(args)}"
        )
    if abs(lo) > MAX_RULE_BOUND or abs(hi) > MAX_RULE_BOUND:
        raise ParamError(
            f"rule ri: bounds must be within ±{MAX_RULE_BOUND}, "
            f"got {format_value(args)}"
        )
    if lo > hi:
        raise ParamError(
            f"rule ri: min {format_value(lo)} is greater than max {format_value(hi)}"
        )
    return int(lo) + src.randrange(int(hi) - int(lo) + 1)


def _random_choice(args: list[object], src: Source) -> object:
    if len(args) != 1:
        raise ParamError(f"rule rc: want [[choices]], got {len(args)} arguments")
    choices = args[0]
    if not isinstance(choices, list):
        raise ParamError(
            f"rule rc: first argument must be a list, got {type_name(choices)}"
        )
    if not choices:
        raise ParamError("rule rc: list of choices is empty")
    return choices[src.randrange(len(choices))]
