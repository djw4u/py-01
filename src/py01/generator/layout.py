"""Anordnungen: bestimmen die Mittelpunkte aller Figuren."""

from __future__ import annotations

import math
from collections.abc import Callable

from .params import Params
from .values import ParamError, Source, format_value

# Kantenlänge der quadratischen Zeichenfläche.
CANVAS_SIZE = 100.0
# Obergrenze der Figuren pro Bild.
MAX_FIGURES = 10000
# Versuche der PDS-Anordnung je Figur.
PDS_ATTEMPTS_PER_FIGURE = 100

Point = tuple[float, float]
Layout = Callable[[Params, Source], list[Point]]


def layout_for(structure: str) -> Layout | None:
    """Anordnung zum Feld "structure"; eine neue ist ein weiterer Eintrag."""
    return _LAYOUTS.get(structure)


def _figure_count(p: Params) -> int:
    n = p.fixed_int("nr_of_figures")
    if n < 1 or n > MAX_FIGURES:
        raise ParamError(f'field "nr_of_figures": want 1..{MAX_FIGURES}, got {n}')
    return n


def _random_layout(p: Params, src: Source) -> list[Point]:
    """x und y jeder Figur kommen aus den Feldern x und y."""
    points = []
    for _ in range(_figure_count(p)):
        x = p.float_value("x", src)
        y = p.float_value("y", src)
        points.append((x, y))
    return points


def _grid_layout(p: Params, src: Source) -> list[Point]:
    """Zellmittelpunkte eines rows x columns Rasters, zeilenweise."""
    rows = p.fixed_int("rows")
    columns = p.fixed_int("columns")
    if rows < 1 or columns < 1:
        raise ParamError(
            f'fields "rows" and "columns": want >= 1, got {rows} and {columns}'
        )
    if rows > MAX_FIGURES // columns:
        raise ParamError(f'fields "rows" and "columns": more than {MAX_FIGURES} cells')
    return [
        ((c + 0.5) * CANVAS_SIZE / columns, (r + 0.5) * CANVAS_SIZE / rows)
        for r in range(rows)
        for c in range(columns)
    ]


def _pds_layout(p: Params, src: Source) -> list[Point]:
    """Zufällige Punkte mit Mindestabstand (Dart-Throwing); passen nicht alle
    hinein, kommen ohne Fehler weniger heraus."""
    n = _figure_count(p)
    min_dist = p.fixed_float("min_distance")
    if min_dist <= 0:
        raise ParamError(
            f'field "min_distance": want > 0, got {format_value(min_dist)}'
        )
    points: list[Point] = []
    for _ in range(PDS_ATTEMPTS_PER_FIGURE * n):
        if len(points) >= n:
            break
        cand = (src.random() * CANVAS_SIZE, src.random() * CANVAS_SIZE)
        if all(math.hypot(cand[0] - q[0], cand[1] - q[1]) >= min_dist for q in points):
            points.append(cand)
    return points


_LAYOUTS: dict[str, Layout] = {
    "RANDOM": _random_layout,
    "GRID": _grid_layout,
    "PDS": _pds_layout,
}
