import math

import pytest

from py01.generator.figure import draw_figure, num
from py01.generator.params import ParamError

from .helpers import parse, src


def fig(fields: str) -> str:
    return '{"params":' + fields + "}"


@pytest.mark.parametrize(
    ("v", "want"),
    [
        (50, "50"),
        (12.5, "12.5"),
        (58.660254, "58.66"),
        (-0.0001, "0"),
        (0.1 + 0.2, "0.3"),
        (-20, "-20"),
        (0.0025, "0.003"),
        (-0.0025, "-0.003"),
        (1e16, "10000000000000000"),
        (1e-7, "0"),
        (-0.0, "0"),
        (math.inf, "+Inf"),
        (-math.inf, "-Inf"),
    ],
)
def test_num_matches_go(v: float, want: str) -> None:
    assert num(v) == want


@pytest.mark.parametrize(
    ("kind", "fields", "want"),
    [
        (
            "rect",
            '{"width":40,"height":20,"fill":"#4353D3","transform":180}',
            (
                '<rect x="30" y="40" width="40" height="20" fill="#4353D3" '
                'transform="rotate(180 50 50)"/>'
            ),
        ),
        ("square", '{"width":10}', '<rect x="45" y="45" width="10" height="10"/>'),
        ("circle", '{"width":10}', '<circle cx="50" cy="50" r="5"/>'),
        (
            "line",
            '{"width":20,"fill":"#f00","stroke":"#000","stroke-width":2}',
            '<line x1="40" y1="50" x2="60" y2="50" stroke="#000" stroke-width="2"/>',
        ),
        ("triangle", '{"width":20}', '<polygon points="50,40 58.66,55 41.34,55"/>'),
        (
            "polygon",
            '{"width":20,"sides":4}',
            '<polygon points="50,40 60,50 50,60 40,50"/>',
        ),
        (
            "circle",
            (
                '{"transform":45,"stroke-linecap":"round","stroke-opacity":0.8,'
                '"stroke-width":2,"stroke":"#222","opacity":0.5,"fill":"#111","width":10}'
            ),
            (
                '<circle cx="50" cy="50" r="5" fill="#111" opacity="0.5" stroke="#222" '
                'stroke-width="2" stroke-opacity="0.8" stroke-linecap="round" '
                'transform="rotate(45 50 50)"/>'
            ),
        ),
    ],
)
def test_draw_figure_shapes(kind: str, fields: str, want: str) -> None:
    assert draw_figure(kind, 50, 50, parse(fig(fields)), src()) == want


def test_draw_figure_applies_rules() -> None:
    p = parse(fig('{"width":["ri",[10,10]],"fill":["rc",[["#a","#b"]]]}'))
    got = draw_figure("circle", 50, 50, p, src())
    assert 'r="5"' in got
    assert 'fill="#a"' in got or 'fill="#b"' in got


def test_draw_figure_escapes_attribute_values() -> None:
    p = parse(fig('{"width":10,"fill":"a\\"b<c"}'))
    want = '<circle cx="50" cy="50" r="5" fill="a&#34;b&lt;c"/>'
    assert draw_figure("circle", 50, 50, p, src()) == want


def test_escape_single_quote() -> None:
    p = parse(fig('{"width":10,"fill":"a\'b&c>"}'))
    assert 'fill="a&#39;b&amp;c&gt;"' in draw_figure("circle", 50, 50, p, src())


def test_draw_figure_too_many_sides_fails() -> None:
    with pytest.raises(ParamError, match="sides"):
        draw_figure("polygon", 50, 50, parse(fig('{"width":10,"sides":1001}')), src())
    draw_figure("polygon", 50, 50, parse(fig('{"width":10,"sides":1000}')), src())


@pytest.mark.parametrize(
    ("kind", "fields", "want_err"),
    [
        ("hexagon", '{"width":10}', "hexagon"),
        ("circle", "{}", "width"),
        ("rect", '{"width":10}', "height"),
        ("polygon", '{"width":10,"sides":2}', "sides"),
        ("polygon", '{"width":10,"sides":3.5}', "sides"),
    ],
)
def test_draw_figure_errors(kind: str, fields: str, want_err: str) -> None:
    with pytest.raises(ParamError, match=want_err):
        draw_figure(kind, 50, 50, parse(fig(fields)), src())
