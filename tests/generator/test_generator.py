import math
import re

import pytest

from py01.generator import generate
from py01.generator.params import ParamError

from .helpers import parse, src

RANDOM_PARAMS = """{"params":{"nr_of_figures":32,
 "figures":["rc",[["rect","polygon","circle","line"]]],
 "x":["ri",[-20,120]],"y":["ri",[-20,120]],
 "fill":["rc",[["#4353D3","#32D761","#D5C734","#D532CE","#D83144"]]],
 "transform":["rc",[[0,180]]],"structure":"RANDOM",
 "opacity":["rc",[[0.6,0.4]]],"height":["rc",[[40,20]]],"width":["rc",[[50,10]]],
 "palette":["#4353D3","#32D761","#D5C734","#D532CE","#D83144"],
 "stroke":["rc",[["#4353D3","#32D761","#D5C734","#D532CE","#D83144"]]],
 "stroke-linecap":["rc",[["round"]]],"stroke-width":["rc",[[6,4]]],
 "stroke-opacity":["rc",[[0.8,0.6]]]}}"""

FIGURE = re.compile(r"<(rect|circle|polygon|line)\b")
CENTER = re.compile(r'cx="([-0-9.]+)" cy="([-0-9.]+)"')


def gen(raw: str, seed: int = 1) -> str:
    return generate(parse(raw), src(seed))


def test_random_count_and_kinds() -> None:
    svg = gen(RANDOM_PARAMS)
    assert svg.startswith(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">\n'
    )
    assert svg.endswith("</svg>\n")
    assert len(FIGURE.findall(svg)) == 32


def test_same_seed_same_svg() -> None:
    assert gen(RANDOM_PARAMS, 1) == gen(RANDOM_PARAMS, 1)


def test_different_seed_differs() -> None:
    assert gen(RANDOM_PARAMS, 1) != gen(RANDOM_PARAMS, 2)


def test_grid() -> None:
    svg = gen(
        '{"params":{"structure":"GRID","rows":2,"columns":2,'
        '"figures":"circle","width":10}}'
    )
    last = -1
    for w in (
        'cx="25" cy="25"',
        'cx="75" cy="25"',
        'cx="25" cy="75"',
        'cx="75" cy="75"',
    ):
        i = svg.find(w)
        assert i > last, w
        last = i
    assert len(FIGURE.findall(svg)) == 4


def test_pds_min_distance() -> None:
    svg = gen(
        '{"params":{"structure":"PDS","nr_of_figures":20,"min_distance":10,'
        '"figures":"circle","width":4}}'
    )
    pts = [(float(x), float(y)) for x, y in CENTER.findall(svg)]
    assert 1 <= len(pts) <= 20
    for i, a in enumerate(pts):
        for b in pts[i + 1 :]:
            assert math.hypot(a[0] - b[0], a[1] - b[1]) >= 10 - 0.01


def test_pds_impossible_density_terminates() -> None:
    svg = gen(
        '{"params":{"structure":"PDS","nr_of_figures":10,"min_distance":200,'
        '"figures":"circle","width":4}}'
    )
    assert len(FIGURE.findall(svg)) == 1


@pytest.mark.parametrize(
    ("fields", "want_err"),
    [
        ('{"figures":"circle","width":10,"nr_of_figures":3}', "structure"),
        ('{"structure":"SPIRAL","figures":"circle","width":10}', "SPIRAL"),
        ('{"structure":"RANDOM","nr_of_figures":1,"x":1,"y":1,"width":10}', "figures"),
        (
            (
                '{"structure":"RANDOM","nr_of_figures":1,"x":1,"y":1,'
                '"figures":"hexagon","width":10}'
            ),
            "hexagon",
        ),
        (
            (
                '{"structure":"RANDOM","nr_of_figures":0,"x":1,"y":1,'
                '"figures":"circle","width":10}'
            ),
            "nr_of_figures",
        ),
        (
            (
                '{"structure":"RANDOM","nr_of_figures":10001,"x":1,"y":1,'
                '"figures":"circle","width":10}'
            ),
            "nr_of_figures",
        ),
        ('{"structure":"GRID","columns":2,"figures":"circle","width":10}', "rows"),
        (
            '{"structure":"GRID","rows":0,"columns":2,"figures":"circle","width":10}',
            "rows",
        ),
        (
            (
                '{"structure":"GRID","rows":101,"columns":100,'
                '"figures":"circle","width":10}'
            ),
            "rows",
        ),
        (
            (
                '{"structure":"PDS","nr_of_figures":3,"min_distance":0,'
                '"figures":"circle","width":10}'
            ),
            "min_distance",
        ),
        (
            '{"structure":"PDS","nr_of_figures":3,"figures":"circle","width":10}',
            "min_distance",
        ),
    ],
)
def test_generate_errors(fields: str, want_err: str) -> None:
    with pytest.raises(ParamError, match=want_err):
        generate(parse('{"params":' + fields + "}"), src())
