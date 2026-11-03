"""Zeichnet einzelne Figuren als SVG-Elemente."""

from __future__ import annotations

import math
from decimal import Decimal

from .params import Params
from .values import ParamError, Source, format_value

# Optionale Attribute in fester Reihenfolge: (Name, numerisch).
STYLE_ATTRS = (
    ("fill", False),
    ("opacity", True),
    ("stroke", False),
    ("stroke-width", True),
    ("stroke-opacity", True),
    ("stroke-linecap", False),
)

KINDS = frozenset({"rect", "square", "circle", "line", "polygon", "triangle"})
DEFAULT_SIDES = 5
# Obergrenze der Eckenzahl, damit das SVG klein bleibt.
MAX_SIDES = 1000

# Maskierung wie Gos html.EscapeString.
_ESCAPES = str.maketrans(
    {"&": "&amp;", "'": "&#39;", "<": "&lt;", ">": "&gt;", '"': "&#34;"}
)


def escape(s: str) -> str:
    """Maskiert einen Attributwert wie Gos html.EscapeString."""
    return s.translate(_ESCAPES)


def num(v: float) -> str:
    """Zahl mit höchstens drei Nachkommastellen, ohne nachgestellte Nullen.

    Rundet wie Gos math.Round (halbe Werte weg von null) und gibt nie
    Exponentschreibweise aus.
    """
    if math.isinf(v):
        return "+Inf" if v > 0 else "-Inf"
    s = v * 1000
    r = math.copysign(math.floor(abs(s) + 0.5), s) / 1000
    if r == 0:
        return "0"
    t = format(Decimal(repr(r)), "f")
    return t.rstrip("0").rstrip(".") if "." in t else t


def draw_figure(kind: str, x: float, y: float, p: Params, src: Source) -> str:
    """Liefert das SVG-Element einer Figur mit Mittelpunkt (x, y)."""
    if kind not in KINDS:
        raise ParamError(f'unknown figure kind "{kind}"')
    try:
        width = p.float_value("width", src)
        if kind == "rect":
            shape = _rect(x, y, width, p.float_value("height", src))
        elif kind == "square":
            shape = _rect(x, y, width, width)
        elif kind == "circle":
            shape = f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(width / 2)}"'
        elif kind == "line":
            shape = (
                f'<line x1="{num(x - width / 2)}" y1="{num(y)}" '
                f'x2="{num(x + width / 2)}" y2="{num(y)}"'
            )
        elif kind == "triangle":
            shape = _polygon(x, y, width / 2, 3)
        else:
            shape = _polygon(x, y, width / 2, _sides(p, src))
        return shape + _style(kind, x, y, p, src) + "/>"
    except ParamError as e:
        raise ParamError(f'figure "{kind}": {e}') from e


def _rect(x: float, y: float, w: float, h: float) -> str:
    return (
        f'<rect x="{num(x - w / 2)}" y="{num(y - h / 2)}" '
        f'width="{num(w)}" height="{num(h)}"'
    )


def _polygon(x: float, y: float, r: float, n: int) -> str:
    """Regelmäßiges n-Eck mit Umkreisradius r, erster Punkt oben."""
    points = []
    for k in range(n):
        angle = -math.pi / 2 + 2 * math.pi * k / n
        points.append(num(x + r * math.cos(angle)) + "," + num(y + r * math.sin(angle)))
    return '<polygon points="' + " ".join(points) + '"'


def _sides(p: Params, src: Source) -> int:
    if not p.has("sides"):
        return DEFAULT_SIDES
    v = p.float_value("sides", src)
    if not v.is_integer() or v < 3 or v > MAX_SIDES:
        raise ParamError(
            f'field "sides": want integer 3..{MAX_SIDES}, got {format_value(v)}'
        )
    return int(v)


def _style(kind: str, x: float, y: float, p: Params, src: Source) -> str:
    out = []
    for name, numeric in STYLE_ATTRS:
        if not p.has(name) or (kind == "line" and name == "fill"):
            continue
        if numeric:
            out.append(f' {name}="{num(p.float_value(name, src))}"')
        else:
            out.append(f' {name}="{escape(p.string_value(name, src))}"')
    if p.has("transform"):
        angle = p.float_value("transform", src)
        out.append(f' transform="rotate({num(angle)} {num(x)} {num(y)})"')
    return "".join(out)
