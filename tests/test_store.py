from collections.abc import Iterator
from pathlib import Path

import pytest

from py01.store import NotFoundError, Store


@pytest.fixture
def store(tmp_path: Path) -> Iterator[Store]:
    s = Store.open(tmp_path / "test.db")
    yield s
    s.close()


def test_open_is_idempotent(tmp_path: Path) -> None:
    for _ in range(2):
        Store.open(tmp_path / "test.db").close()


def test_create_variant_round_trip(store: Store) -> None:
    root_id = store.create_variant("Basis", '{"params":{"a":1}}')
    child_id = store.create_variant("Basis (neu)", '{"params":{"a":2}}', root_id)

    root = store.get_variant(root_id)
    assert root.name == "Basis"
    assert root.params == '{"params":{"a":1}}'
    assert root.parent_id is None and root.source_file is None
    assert root.created_at.year >= 2026
    assert root.created_at.tzinfo is not None

    assert store.get_variant(child_id).parent_id == root_id
    assert [v.id for v in store.list_variants()] == [root_id, child_id]


def test_create_variant_rejects_invalid_json(store: Store) -> None:
    with pytest.raises(Exception, match="CHECK"):
        store.create_variant("kaputt", "{")


def test_save_image_unknown_variant_fails(store: Store) -> None:
    with pytest.raises(Exception, match="FOREIGN KEY"):
        store.save_image(999, "<svg/>")


def test_get_variant_not_found(store: Store) -> None:
    with pytest.raises(NotFoundError):
        store.get_variant(42)


def test_get_image_not_found(store: Store) -> None:
    with pytest.raises(NotFoundError):
        store.get_image(42)


def test_list_images_filter_and_order(store: Store) -> None:
    v1 = store.create_variant("v1", '{"params":{}}')
    v2 = store.create_variant("v2", '{"params":{}}')
    a = store.save_image(v1, "<svg>a</svg>")
    b = store.save_image(v2, "<svg>b</svg>")
    c = store.save_image(v1, "<svg>c</svg>")

    got = store.list_images(v1)
    assert [i.id for i in got] == [c, a]
    assert got[0].svg == "<svg>c</svg>" and got[0].variant_id == v1
    assert [i.id for i in store.list_images()] == [c, b, a]

    one = store.get_image(b)
    assert one.svg == "<svg>b</svg>" and one.variant_id == v2


def test_opens_path_with_question_mark(tmp_path: Path) -> None:
    path = tmp_path / "a?b#c.db"
    s = Store.open(path)
    vid = s.create_variant("v", '{"params":{}}')
    assert s.get_variant(vid).name == "v"
    s.close()
    assert path.exists()
