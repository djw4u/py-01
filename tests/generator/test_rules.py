import pytest

from py01.generator.params import ParamError

from .helpers import parse, src


def test_ri_within_inclusive_bounds() -> None:
    p = parse('{"params":{"x":["ri",[-20,120]]}}')
    s = src()
    seen = set()
    for _ in range(2000):
        v = p.float_value("x", s)
        assert v == int(v) and -20 <= v <= 120
        seen.add(v)
    assert -20 in seen and 120 in seen


def test_ri_single_value() -> None:
    assert parse('{"params":{"x":["ri",[5,5]]}}').float_value("x", src()) == 5


def test_ri_min_greater_max_fails() -> None:
    with pytest.raises(ParamError):
        parse('{"params":{"x":["ri",[10,5]]}}').value("x", src())


def test_rc_picks_only_listed() -> None:
    p = parse('{"params":{"t":["rc",[[0,180]]]}}')
    s = src()
    seen = {p.float_value("t", s) for _ in range(200)}
    assert seen == {0, 180}


def test_rc_strings() -> None:
    p = parse('{"params":{"f":["rc",[["rect","circle"]]]}}')
    s = src()
    for _ in range(50):
        assert p.string_value("f", s) in ("rect", "circle")


def test_rc_empty_list_fails() -> None:
    with pytest.raises(ParamError):
        parse('{"params":{"f":["rc",[[]]]}}').value("f", src())


def test_unknown_rule_fails() -> None:
    with pytest.raises(ParamError, match="xx"):
        parse('{"params":{"f":["xx",[1]]}}').value("f", src())


@pytest.mark.parametrize("bounds", ["[-9e18,9e18]", "[0,1e300]", "[-3000000000,0]"])
def test_ri_huge_bounds_fail(bounds: str) -> None:
    with pytest.raises(ParamError):
        parse('{"params":{"x":["ri",' + bounds + "]}}").value("x", src())


def test_ri_rejects_bool_bounds() -> None:
    with pytest.raises(ParamError, match="rule ri"):
        parse('{"params":{"x":["ri",[true,5]]}}').value("x", src())


def test_same_seed_same_values() -> None:
    p = parse('{"params":{"x":["ri",[0,1000]]}}')
    a, b = src(7), src(7)
    assert [p.value("x", a) for _ in range(20)] == [p.value("x", b) for _ in range(20)]
