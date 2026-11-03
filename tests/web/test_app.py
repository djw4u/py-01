import html
import io
import random
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from flask.testing import FlaskClient

from py01.store import Store
from py01.web import create_app

GRID_PARAMS = (
    '{"params":{"structure":"GRID","rows":2,"columns":2,"figures":"circle","width":10}}'
)


@dataclass
class Env:
    store: Store
    client: FlaskClient

    def variant(self, name: str, params: str) -> int:
        return self.store.create_variant(name, params)


@pytest.fixture
def env(tmp_path: Path) -> Iterator[Env]:
    s = Store.open(tmp_path / "test.db")
    app = create_app(s, lambda: random.Random(1))
    yield Env(s, app.test_client())
    s.close()


def test_werkstatt_lists_variants_and_shows_params(env: Env) -> None:
    vid = env.variant("Rasterbild", GRID_PARAMS)
    env.variant("Zweite", GRID_PARAMS)
    r = env.client.get(f"/werkstatt?variant={vid}")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    for want in ("Rasterbild", "Zweite", "&#34;structure&#34;", "py-01"):
        assert want in body


@pytest.mark.parametrize("target", ["/werkstatt?variant=999", "/werkstatt?variant=abc"])
def test_werkstatt_not_found(env: Env, target: str) -> None:
    assert env.client.get(target).status_code == 404


def test_werkstatt_without_variants_shows_hint(env: Env) -> None:
    r = env.client.get("/werkstatt")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "import_params.sql" in body
    assert "py-01.db" in body


def test_generate_valid(env: Env) -> None:
    vid = env.variant("v", GRID_PARAMS)
    r = env.client.post(
        "/werkstatt/generate", data={"variant_id": str(vid), "params": GRID_PARAMS}
    )
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "data:image/svg+xml;base64," in html.unescape(body)
    assert 'name="svg"' in body
    assert env.store.list_images() == []


def test_generate_invalid_json(env: Env) -> None:
    vid = env.variant("v", GRID_PARAMS)
    r = env.client.post(
        "/werkstatt/generate", data={"variant_id": str(vid), "params": "{"}
    )
    assert r.status_code == 422
    body = r.get_data(as_text=True)
    assert "data:image" not in body
    assert 'class="error"' in body
    assert env.store.list_images() == []


def test_generate_invalid_parameters(env: Env) -> None:
    vid = env.variant("v", GRID_PARAMS)
    r = env.client.post(
        "/werkstatt/generate",
        data={"variant_id": str(vid), "params": '{"params":{"structure":"SPIRAL"}}'},
    )
    assert r.status_code == 422
    assert "SPIRAL" in r.get_data(as_text=True)


def test_save_image(env: Env) -> None:
    vid = env.variant("v", GRID_PARAMS)
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"></svg>'
    r = env.client.post(
        "/werkstatt/save-image", data={"variant_id": str(vid), "svg": svg}
    )
    assert r.status_code == 303
    assert r.headers["Location"] == f"/galerie?variant={vid}"
    assert [i.svg for i in env.store.list_images(vid)] == [svg]


def test_save_image_rejects_non_svg_and_unknown_variant(env: Env) -> None:
    vid = env.variant("v", GRID_PARAMS)
    r = env.client.post(
        "/werkstatt/save-image",
        data={"variant_id": str(vid), "svg": "<html>kein svg</html>"},
    )
    assert r.status_code == 422
    r = env.client.post(
        "/werkstatt/save-image", data={"variant_id": "999", "svg": "<svg ></svg>"}
    )
    assert r.status_code == 404
    assert env.store.list_images() == []


def test_save_image_rejects_too_large_svg(env: Env) -> None:
    vid = env.variant("v", GRID_PARAMS)
    svg = "<svg " + "x" * (1024 * 1024)
    r = env.client.post(
        "/werkstatt/save-image", data={"variant_id": str(vid), "svg": svg}
    )
    assert r.status_code == 422
    assert env.store.list_images() == []


def test_save_large_svg(env: Env) -> None:
    vid = env.variant("v", GRID_PARAMS)
    svg = "<svg " + "x" * (900 * 1024) + "</svg>"
    r = env.client.post(
        "/werkstatt/save-image", data={"variant_id": str(vid), "svg": svg}
    )
    assert r.status_code == 303
    assert len(env.store.list_images(vid)) == 1


def test_save_large_svg_multipart(env: Env) -> None:
    vid = env.variant("v", GRID_PARAMS)
    svg = "<svg " + "x" * (900 * 1024) + "</svg>"
    r = env.client.post(
        "/werkstatt/save-image",
        data={"variant_id": str(vid), "svg": svg, "f": (io.BytesIO(b"x"), "f.txt")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 303
    assert len(env.store.list_images(vid)) == 1


def test_too_large_form_is_413(env: Env) -> None:
    r = env.client.post(
        "/werkstatt/generate",
        data={"variant_id": "1", "params": "x" * (2 * 1024 * 1024 + 1)},
    )
    assert r.status_code == 413
    assert "Anfrage zu groß" in r.get_data(as_text=True)


def test_save_variant(env: Env) -> None:
    parent = env.variant("Basis", GRID_PARAMS)
    changed = GRID_PARAMS.replace('"rows":2', '"rows":3', 1)
    r = env.client.post(
        "/werkstatt/save-variant",
        data={"variant_id": str(parent), "name": "Basis (neu)", "params": changed},
    )
    assert r.status_code == 303
    variants = env.store.list_variants()
    assert len(variants) == 2
    created = variants[1]
    assert r.headers["Location"] == f"/werkstatt?variant={created.id}"
    assert created.name == "Basis (neu)" and created.params == changed
    assert created.parent_id == parent and created.source_file is None


@pytest.mark.parametrize(
    ("name", "params"),
    [("  ", GRID_PARAMS), ("x", "{"), ("x", '{"a":1}')],
)
def test_save_variant_rejects_empty_name_and_invalid_params(
    env: Env, name: str, params: str
) -> None:
    parent = env.variant("Basis", GRID_PARAMS)
    r = env.client.post(
        "/werkstatt/save-variant",
        data={"variant_id": str(parent), "name": name, "params": params},
    )
    assert r.status_code == 422
    assert len(env.store.list_variants()) == 1


def test_galerie_filter_by_variant(env: Env) -> None:
    v1 = env.variant("eins", GRID_PARAMS)
    v2 = env.variant("zwei", GRID_PARAMS)
    i1 = env.store.save_image(v1, "<svg >1</svg>")
    i2 = env.store.save_image(v2, "<svg >2</svg>")

    everything = env.client.get("/galerie").get_data(as_text=True)
    assert f"/bilder/{i1}.svg" in everything and f"/bilder/{i2}.svg" in everything

    r = env.client.get(f"/galerie?variant={v1}")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert f"/bilder/{i1}.svg" in body
    assert f"/bilder/{i2}.svg" not in body
    assert 'target="_blank"' in body
    assert "eins ·" in body


def test_bild_headers(env: Env) -> None:
    vid = env.variant("v", GRID_PARAMS)
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    iid = env.store.save_image(vid, svg)
    r = env.client.get(f"/bilder/{iid}.svg")
    assert r.status_code == 200
    assert r.headers["Content-Type"] == "image/svg+xml"
    assert (
        r.headers["Content-Security-Policy"]
        == "default-src 'none'; style-src 'unsafe-inline'"
    )
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.get_data(as_text=True) == svg


@pytest.mark.parametrize("target", ["/bilder/999.svg", "/bilder/abc.svg", "/bilder/1"])
def test_bild_not_found(env: Env, target: str) -> None:
    assert env.client.get(target).status_code == 404


def test_root_redirects_and_static_css(env: Env) -> None:
    r = env.client.get("/")
    assert r.status_code == 303
    assert r.headers["Location"] == "/werkstatt"
    assert env.client.get("/static/style.css").status_code == 200
    assert env.client.get("/gibt-es-nicht").status_code == 404


def test_wrong_method_is_405(env: Env) -> None:
    assert env.client.get("/werkstatt/generate").status_code == 405


@pytest.mark.parametrize("bad", ["0", "-1", "1_0", " 1", "abc", "99999999999999999999"])
def test_invalid_ids_are_404(env: Env, bad: str) -> None:
    env.variant("v", GRID_PARAMS)
    assert (
        env.client.get("/werkstatt", query_string={"variant": bad}).status_code == 404
    )
    assert env.client.get(f"/bilder/{bad}.svg").status_code == 404


def test_plus_sign_id(env: Env) -> None:
    env.variant("v", GRID_PARAMS)
    assert env.client.get("/werkstatt?variant=%2B1").status_code == 200
