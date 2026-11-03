import shutil
import subprocess
from pathlib import Path

import pytest

from py01.store import Store

SCRIPT = Path(__file__).parents[1] / "scripts" / "import_params.sql"


def test_import_script(tmp_path: Path) -> None:
    if shutil.which("sqlite3") is None:
        pytest.skip("sqlite3 nicht im PATH")
    params = tmp_path / "params"
    params.mkdir()
    files = {
        "a.json": '{"params":{"nr_of_figures":1}}',
        "b.json": '{"params":{"nr_of_figures":2}}',
        "kaputt.json": "{",
        "notes.txt": "kein JSON-Import",
    }
    for name, content in files.items():
        (params / name).write_text(content)

    db = tmp_path / "py-01.db"
    Store.open(db).close()  # legt das Schema an
    sql = SCRIPT.read_text()

    for run in (1, 2):
        subprocess.run(
            ["sqlite3", str(db)], cwd=tmp_path, input=sql, text=True, check=True
        )
        s = Store.open(db)
        variants = s.list_variants()
        s.close()
        got = {v.name: v.source_file for v in variants}
        assert got == {"a": "params/a.json", "b": "params/b.json"}, f"Lauf {run}"
