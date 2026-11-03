"""Parameter eines Bildes und ihr Zugriff."""

from __future__ import annotations

import json

from .rules import as_rule, eval_rule
from .values import ParamError, Source, as_number, format_value, type_name

__all__ = ["ParamError", "Params", "Source"]


def _reject_constant(name: str) -> float:
    raise ValueError(f"invalid number {name}")


class Params:
    """Die Parameter eines Bildes (der Inhalt von "params")."""

    def __init__(self, fields: dict[str, object]) -> None:
        self._fields = fields

    @classmethod
    def parse(cls, raw: str | bytes) -> Params:
        """Liest eine Parameterdatei der Form {"params":{...}}."""
        try:
            top = json.loads(raw, parse_constant=_reject_constant)
        except ValueError as e:
            raise ParamError(f"parse params: {e}") from e
        if not isinstance(top, dict) or "params" not in top:
            raise ParamError('parse params: missing key "params"')
        fields = top["params"]
        if not isinstance(fields, dict):
            raise ParamError('parse params: "params" is not an object')
        return cls(fields)

    def has(self, name: str) -> bool:
        """Meldet, ob das Feld vorhanden ist."""
        return name in self._fields

    def value(self, name: str, src: Source) -> object:
        """Fester Wert unverändert, Regel mit src ausgewertet."""
        if name not in self._fields:
            raise ParamError(f'missing field "{name}"')
        v = self._fields[name]
        rule = as_rule(v)
        if rule is None:
            return v
        try:
            return eval_rule(rule[0], rule[1], src)
        except ParamError as e:
            raise ParamError(f'field "{name}": {e}') from e

    def float_value(self, name: str, src: Source) -> float:
        """Wie value, das Ergebnis muss eine Zahl sein."""
        v = self.value(name, src)
        n = as_number(v)
        if n is None:
            raise ParamError(f'field "{name}": want number, got {type_name(v)}')
        return n

    def string_value(self, name: str, src: Source) -> str:
        """Wie value, das Ergebnis muss ein Text sein."""
        v = self.value(name, src)
        if not isinstance(v, str):
            raise ParamError(f'field "{name}": want string, got {type_name(v)}')
        return v

    def fixed_float(self, name: str) -> float:
        """Feste Zahl; Regeln sind hier nicht erlaubt."""
        if name not in self._fields:
            raise ParamError(f'missing field "{name}"')
        v = self._fields[name]
        if as_rule(v) is not None:
            raise ParamError(f'field "{name}": rule not allowed, want fixed number')
        n = as_number(v)
        if n is None:
            raise ParamError(f'field "{name}": want number, got {type_name(v)}')
        return n

    def fixed_int(self, name: str) -> int:
        """Feste ganze Zahl; Regeln sind hier nicht erlaubt."""
        n = self.fixed_float(name)
        if not n.is_integer():
            raise ParamError(f'field "{name}": want integer, got {format_value(n)}')
        return int(n)
