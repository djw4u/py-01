"""Erzeugt das SVG eines Bildes."""

from __future__ import annotations

from .figure import draw_figure
from .layout import layout_for
from .params import Params
from .values import ParamError, Source

SVG_OPEN = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">\n'


def generate(p: Params, src: Source) -> str:
    """SVG mit der Zeichenfläche "0 0 100 100"; ungültige Parameter führen
    zu ParamError, nie zu einem stillen Ergebnis."""
    structure = p.string_value("structure", src)
    place = layout_for(structure)
    if place is None:
        raise ParamError(f'unknown structure "{structure}"')
    try:
        points = place(p, src)
    except ParamError as e:
        raise ParamError(f"structure {structure}: {e}") from e
    out = [SVG_OPEN]
    for x, y in points:
        kind = p.string_value("figures", src)
        out.append(draw_figure(kind, x, y, p, src) + "\n")
    out.append("</svg>\n")
    return "".join(out)
