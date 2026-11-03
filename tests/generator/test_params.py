import pytest

from py01.generator.params import ParamError, Params

from .helpers import parse, src


@pytest.mark.parametrize("raw", ["{", "{}", '{"params":5}'])
def test_parse_errors(raw: str) -> None:
    with pytest.raises(ParamError):
        Params.parse(raw)


@pytest.mark.parametrize(
    "raw",
    [
        '{"params":{"w":NaN}}',
        '{"params":{"w":Infinity}}',
        '{"params":{"w":-Infinity}}',
    ],
)
def test_parse_rejects_non_finite(raw: str) -> None:
    with pytest.raises(ParamError, match="parse params"):
        Params.parse(raw)


def test_value_fixed_passes_through() -> None:
    p = parse('{"params":{"structure":"RANDOM","nr_of_figures":32}}')
    assert p.value("structure", src()) == "RANDOM"
    assert p.fixed_int("nr_of_figures") == 32
    assert p.has("structure")
    assert not p.has("fehlt")


def test_missing_field_fails() -> None:
    with pytest.raises(ParamError, match="width"):
        parse('{"params":{}}').value("width", src())


def test_palette_is_not_a_rule() -> None:
    p = parse(
        '{"params":{"palette":["#4353D3","#32D761","#D5C734","#D532CE","#D83144"],'
        '"duo":["#000","#fff"]}}'
    )
    for name in ("palette", "duo"):
        assert isinstance(p.value(name, src()), list)


def test_fixed_values_reject_wrong_types() -> None:
    p = parse('{"params":{"a":1.5,"s":"x","r":["ri",[1,2]]}}')
    with pytest.raises(ParamError):
        p.fixed_int("a")
    with pytest.raises(ParamError):
        p.fixed_int("s")
    with pytest.raises(ParamError):
        p.fixed_float("r")
    assert p.fixed_float("a") == 1.5


def test_bool_is_not_a_number() -> None:
    p = parse('{"params":{"b":true,"r":["rc",[[false]]]}}')
    for name in ("b", "r"):
        with pytest.raises(ParamError, match="want number, got bool"):
            p.float_value(name, src())
    with pytest.raises(ParamError):
        p.fixed_int("b")


def test_string_value_rejects_number() -> None:
    with pytest.raises(ParamError, match="want string, got number"):
        parse('{"params":{"s":5}}').string_value("s", src())
