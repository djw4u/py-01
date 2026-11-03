"""Gemeinsame Typen und Hilfen des Generators."""

from __future__ import annotations

from typing import Protocol


class ParamError(ValueError):
    """Ungültige Parameter; der Text erscheint in der Oberfläche."""


class Source(Protocol):
    """Injizierte Zufallsquelle; random.Random erfüllt sie."""

    def randrange(self, n: int, /) -> int: ...

    def random(self) -> float: ...


def type_name(v: object) -> str:
    """JSON-Typname eines Wertes für Fehlermeldungen."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int | float):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    return type(v).__name__


def as_number(v: object) -> float | None:
    """Liefert v als Zahl oder None; bool zählt nicht als Zahl."""
    if isinstance(v, bool) or not isinstance(v, int | float):
        return None
    return float(v)


def format_value(v: object) -> str:
    """Kurzform eines Wertes für Fehlermeldungen (wie Gos %v)."""
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e21:
        return str(int(v))
    if isinstance(v, list):
        return "[" + " ".join(format_value(x) for x in v) + "]"
    return str(v)
