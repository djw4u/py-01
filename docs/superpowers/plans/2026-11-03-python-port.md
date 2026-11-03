# py-01 Python-Portierung Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** go-02 als `~/code/py-01` / `djw4u/py-01` (öffentlich) 1:1 in Python neu bauen, mit gleichem Verhalten und gleichem SQLite-Schema.

**Architecture:** Paket `py01` unter `src/`: `generator` (rein, ohne Flask/DB), `store` (sqlite3), `web` (Flask-App-Factory + Jinja2), `__main__` (Flags, Werkzeug-Server). Jede Go-Datei hat ein Python-Gegenstück; jeder Go-Test ein pytest-Gegenstück.

**Tech Stack:** Python 3.14 (`requires-python >=3.12`), uv, Flask, sqlite3, pytest, ruff, mypy (strict).

**Spec:** `docs/superpowers/specs/2026-11-03-python-port-design.md`. Fachliche Referenz: Go-Code in `~/code/go-02` (Datei für Datei lesen, bevor die jeweilige Python-Datei entsteht).

## Global Constraints

- Verhalten, Texte, Statuscodes, Grenzen exakt wie go-02; Abweichungen nur die in der Spec genannten.
- Laufzeit-Abhängigkeit nur `flask`; Dev: `pytest`, `ruff`, `mypy`. Nichts weiter ohne Rückfrage.
- Name in Oberfläche und Doku: `py-01`; Paketname `py01`; Default-DB `py-01.db`; Default-Adresse `127.0.0.1:8080`.
- Kommentare/Docstrings/Nutzertexte deutsch; Fehlertexte, Logs, Bezeichner englisch.
- Commit-Nachrichten: Imperativ, kurz, **ohne Präfix**, Schlusszeile `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Vor jedem Commit grün: `uv run pytest`, `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`.
- Tests deterministisch: `random.Random(seed)`, DB nur in `tmp_path`.

## Review Focus

1. `true`/`false` als Zahl (`"width": true`) → Fehler „want number“, nicht 1/0 (Python `bool` ist `int`). Test in Task 2.
2. `NaN`/`Infinity` im JSON → `parse params`-Fehler wie in Go. Test in Task 2.
3. Speichern eines SVG zwischen 500 KB und 1 MiB → 303 und gespeichert (Werkzeug-Formulargrenze). Test in Task 5.
4. IDs `0`, `-1`, `1_0`, ` 5`, `abc` in Query/Form/Pfad → 404, `+5` → wie `5`. Test in Task 5.
5. Rundung wie Go: `num(0.0025) == "0.003"`, `num(-0.0025) == "-0.003"`, `num(1e16) == "10000000000000000"`, `num(inf) == "+Inf"`. Test in Task 3.

---

### Task 1: Repo anlegen und Python-Gerüst

**Files:**
- Create: `~/code/py-01/` (Kopie von go-02 ohne `.git`)
- Delete: `go.mod`, `go.sum`, `cmd/`, `internal/` (vorher `internal/web/templates/` und `internal/web/static/style.css` nach `src/py01/web/` verschieben), `.golangci.yml`, `bin/`, `go-02.db`
- Create: `pyproject.toml`, `.python-version`, `uv.lock`, `src/py01/__init__.py`, `tests/test_smoke.py`
- Create: `docs/superpowers/specs/2026-11-03-python-port-design.md`, `docs/superpowers/plans/2026-11-03-python-port.md` (aus dem Scratchpad)
- Modify: `.gitignore` (+ `__pycache__/`, `.venv/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `*.db`)

**Interfaces:**
- Produces: Paket `py01` importierbar; Script `py-01 = "py01.__main__:main"` (Ziel entsteht in Task 6, bis dahin nicht aufrufen).

- [ ] **Step 1:** `rsync -a --exclude=.git --exclude=bin --exclude='*.db' ~/code/go-02/ ~/code/py-01/`, Templates und CSS verschieben, Go-Dateien löschen, Spec und Plan aus dem Scratchpad nach `docs/superpowers/` kopieren.
- [ ] **Step 2:** `pyproject.toml`: Name `py-01`, Version `0.1.0`, `requires-python = ">=3.12"`, Abhängigkeit `flask`, Dev-Gruppe `pytest`, `ruff`, `mypy`; Build-Backend `uv_build` mit Modul `py01`; `[tool.ruff.lint] extend-select = ["I", "B", "UP"]`; `[tool.mypy] strict = true`, `files = ["src", "tests"]`; `[tool.pytest.ini_options] testpaths = ["tests"]`. `.python-version` = `3.14`. `uv sync`.
- [ ] **Step 3:** `tests/test_smoke.py`: `def test_package_imports() -> None: import py01` – `uv run pytest` PASS, ruff und mypy grün.
- [ ] **Step 4:** `git init -b main`, Commit „Start py-01 as Python port of go-02“, `gh repo create djw4u/py-01 --public --source=. --push`.

### Task 2: Generator – Parameter und Regeln

**Files:**
- Create: `src/py01/generator/__init__.py`, `params.py`, `rules.py`
- Test: `tests/generator/conftest.py`, `tests/generator/test_params.py`, `tests/generator/test_rules.py`

**Interfaces:**
- Produces:
  - `class ParamError(ValueError)`
  - `class Source(Protocol)`: `randrange(self, n: int, /) -> int`, `random(self) -> float`
  - `class Params`: `Params.parse(raw: str | bytes) -> Params`, `has(name: str) -> bool`, `value(name: str, src: Source) -> object`, `float_value(name, src) -> float`, `string_value(name, src) -> str`, `fixed_float(name) -> float`, `fixed_int(name) -> int`
  - `rules.as_rule(v: object) -> tuple[str, list[object]] | None`, `rules.eval_rule(name: str, args: list[object], src: Source) -> object`
  - `tests/generator/conftest.py`: Fixture-freie Helfer `parse(raw: str) -> Params` und `src(seed: int = 1) -> random.Random`
- Fehlertexte wortgleich zu `params.go`/`rules.go`; `%T` → JSON-Typname (`number`, `string`, `bool`, `array`, `object`, `null`).

- [ ] **Step 1: Failing tests** – Gegenstücke zu allen Tests in `params_test.go` und `rules_test.go` (gleiche Eingaben, gleiche Erwartungen, gleiche Teilstrings in Fehlertexten) plus:

```python
@pytest.mark.parametrize("raw", ['{"params":{"w":NaN}}', '{"params":{"w":Infinity}}', '{"params":{"w":-Infinity}}'])
def test_parse_rejects_non_finite(raw: str) -> None:
    with pytest.raises(ParamError, match="parse params"):
        Params.parse(raw)

def test_bool_is_not_a_number() -> None:
    p = parse('{"params":{"b":true,"r":["rc",[[false]]]}}')
    for name in ("b", "r"):
        with pytest.raises(ParamError, match="want number, got bool"):
            p.float_value(name, src())
    with pytest.raises(ParamError):
        p.fixed_int("b")

def test_ri_rejects_bool_bounds() -> None:
    with pytest.raises(ParamError, match="rule ri"):
        parse('{"params":{"x":["ri",[true,5]]}}').value("x", src())
```

- [ ] **Step 2:** `uv run pytest tests/generator -v` → FAIL (ImportError).
- [ ] **Step 3:** Implementieren. `parse` mit `json.loads(raw, parse_constant=...)` das `ParamError` wirft. Zahl = `int | float` und nicht `bool`. `ri`: Grenzen müssen ganzzahlig sein (`float.is_integer()` bzw. `int`), Betrag ≤ `2**31`, Ergebnis `lo + src.randrange(hi - lo + 1)` als `int`. `rc`: `choices[src.randrange(len(choices))]`.
- [ ] **Step 4:** Tests, ruff, mypy grün.
- [ ] **Step 5:** Commit „Add generator params and rules“.

### Task 3: Generator – Figuren, Anordnungen, SVG

**Files:**
- Create: `src/py01/generator/figure.py`, `layout.py`, `generator.py`; `__init__.py` exportiert `generate`, `Params`, `ParamError`, `Source`
- Test: `tests/generator/test_figure.py`, `test_layout.py` (Go `generator_test.go`)

**Interfaces:**
- Consumes: Task 2.
- Produces: `generate(p: Params, src: Source) -> str` (SVG-Text, exakt Gos Format inkl. Zeilenumbrüchen); intern `num(v: float) -> str`, `draw_figure(kind: str, x: float, y: float, p: Params, src: Source) -> str`, `layout_for(structure: str) -> Callable[[Params, Source], list[tuple[float, float]]] | None`.

- [ ] **Step 1: Failing tests** – Gegenstücke zu allen Tests in `figure_test.go` und `generator_test.go` mit identischen erwarteten SVG-Strings (die Formen-Tabelle ist deterministisch, Escape-Test erwartet `fill="a&#34;b&lt;c"`). Seed-Tests: „gleicher Seed → gleiches SVG“, „anderer Seed → anderes SVG“ statt Go-Werten. Zusätzlich:

```python
@pytest.mark.parametrize(("v", "want"), [
    (0.0025, "0.003"), (-0.0025, "-0.003"), (1e16, "10000000000000000"),
    (1e-7, "0"), (-0.0, "0"), (math.inf, "+Inf"), (-math.inf, "-Inf"),
])
def test_num_matches_go(v: float, want: str) -> None:
    assert num(v) == want

def test_escape_single_quote() -> None:
    assert "fill=\"a&#39;b&amp;c\"" in draw_figure("circle", 50, 50, parse('{"params":{"width":10,"fill":"a\'b&c"}}'), src())
```

- [ ] **Step 2:** `uv run pytest tests/generator -v` → FAIL.
- [ ] **Step 3:** Implementieren, Reihenfolge der Zufallsaufrufe wie Go (je Punkt: `figures`, dann `width`, ggf. `height`/`sides`, dann Stilattribute in Gos Reihenfolge, zuletzt `transform`). `num`:

```python
def num(v: float) -> str:
    if math.isinf(v):
        return "+Inf" if v > 0 else "-Inf"
    s = v * 1000
    r = math.copysign(math.floor(abs(s) + 0.5), s) / 1000
    if r == 0:
        return "0"
    t = format(Decimal(repr(r)), "f")
    return t.rstrip("0").rstrip(".") if "." in t else t
```

  Maskierung: eigene Funktion mit Ersetzungen `&`→`&amp;`, `'`→`&#39;`, `<`→`&lt;`, `>`→`&gt;`, `"`→`&#34;` (Gos Tabelle). PDS: Abstand mit `math.hypot`, Versuche `100 * n`.
- [ ] **Step 4:** Tests, ruff, mypy grün.
- [ ] **Step 5:** Commit „Add generator figures, layouts and SVG output“.

### Task 4: Store

**Files:**
- Create: `src/py01/store.py`
- Test: `tests/test_store.py`, `tests/test_import_script.py`

**Interfaces:**
- Produces:
  - `class NotFoundError(LookupError)`
  - `@dataclass(frozen=True) class Variant`: `id: int`, `name: str`, `params: str`, `source_file: str | None`, `parent_id: int | None`, `created_at: datetime`
  - `@dataclass(frozen=True) class Image`: `id: int`, `variant_id: int`, `svg: str`, `created_at: datetime`
  - `class Store`: `Store.open(path: str | Path) -> Store`, `close()`, `list_variants() -> list[Variant]`, `get_variant(id: int) -> Variant`, `create_variant(name: str, params: str, parent_id: int = 0) -> int`, `save_image(variant_id: int, svg: str) -> int`, `list_images(variant_id: int = 0) -> list[Image]`, `get_image(id: int) -> Image`
- Schema-SQL wörtlich aus `store.go`. `created_at` UTC aus `"%Y-%m-%d %H:%M:%S"`. Fremdschlüssel- und JSON-Verstöße (`sqlite3.IntegrityError`) als Ausnahme weiterreichen.

- [ ] **Step 1: Failing tests** – Gegenstücke zu `store_test.go` und `import_script_test.go` (Skript über `Path(__file__).parents[1] / "scripts/import_params.sql"`, `subprocess.run(["sqlite3", db], cwd=tmp_path, input=...)`, `pytest.skip` ohne `sqlite3`). Zusätzlich: `test_opens_path_with_question_mark` (`tmp_path / "a?b#c.db"` öffnen, Variante anlegen und lesen).
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Implementieren: `sqlite3.connect(path, check_same_thread=False)`, `PRAGMA foreign_keys = ON`, `executescript(SCHEMA)`, alle Zugriffe unter einem `threading.Lock`, Autocommit (`isolation_level=None`).
- [ ] **Step 4:** Tests, ruff, mypy grün.
- [ ] **Step 5:** Commit „Add SQLite store“.

### Task 5: Web

**Files:**
- Create: `src/py01/web/__init__.py`, `src/py01/web/app.py`
- Modify: `src/py01/web/templates/layout.html`, `werkstatt.html`, `galerie.html` (Go-Template → Jinja2: `layout.html` mit `{% block content %}`, Seiten `{% extends "layout.html" %}`; Markup und Texte unverändert, `go-02` → `py-01`)
- Test: `tests/web/conftest.py`, `tests/web/test_app.py`

**Interfaces:**
- Consumes: Task 3 (`generate`, `Params`, `ParamError`, `Source`), Task 4 (`Variant`, `Image`, `NotFoundError`).
- Produces: `create_app(store: StoreLike, new_source: Callable[[], Source]) -> flask.Flask`; `StoreLike` = `typing.Protocol` mit den sechs Methoden `list_variants`, `get_variant`, `create_variant`, `save_image`, `list_images`, `get_image`.

- [ ] **Step 1: Failing tests** – Gegenstücke zu allen 14 Tests in `web_test.go` (Flask-Test-Client, echter Store in `tmp_path`, `new_source=lambda: random.Random(1)`, gleiche Status, `Location`-Header, Teilstrings, Header von `/bilder`). Zusätzlich:

```python
def test_save_large_svg(env: Env) -> None:
    vid = env.variant("v", GRID_PARAMS)
    svg = "<svg " + "x" * (900 * 1024) + "</svg>"
    r = env.client.post("/werkstatt/save-image", data={"variant_id": str(vid), "svg": svg})
    assert r.status_code == 303
    assert len(env.store.list_images(vid)) == 1

def test_too_large_form_is_413(env: Env) -> None:
    r = env.client.post("/werkstatt/generate", data={"variant_id": "1", "params": "x" * (2 * 1024 * 1024 + 1)})
    assert r.status_code == 413 and "Anfrage zu groß" in r.get_data(as_text=True)

@pytest.mark.parametrize("bad", ["0", "-1", "1_0", " 1", "abc", "99999999999999999999"])
def test_invalid_ids_are_404(env: Env, bad: str) -> None:
    env.variant("v", GRID_PARAMS)
    assert env.client.get("/werkstatt", query_string={"variant": bad}).status_code == 404
    assert env.client.get(f"/bilder/{bad}.svg").status_code == 404

def test_plus_sign_id(env: Env) -> None:
    env.variant("v", GRID_PARAMS)
    assert env.client.get("/werkstatt?variant=%2B1").status_code == 200
```

- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Implementieren wie `web.go`: Routen mit `methods=[...]`, `MAX_CONTENT_LENGTH = MAX_FORM_MEMORY_SIZE = 2 * 1024 * 1024`, Handler für `RequestEntityTooLarge` → 413 „Anfrage zu groß“, defekte Formulare → 400 „Ungültige Formulardaten“, unerwartete Ausnahmen → `logging.exception` + 500 „Interner Fehler“ (Plain-Text wie Gos `http.Error`). ID-Parsing `re.fullmatch(r"[+-]?[0-9]+", s)`, `0 < id < 2**63`. Vorschau als `data:image/svg+xml;base64,...` mit `markupsafe`-sicherem Attribut (Jinja autoescape). `/bilder/<file>`: Endung `.svg` Pflicht, Header `Content-Type: image/svg+xml`, CSP `default-src 'none'; style-src 'unsafe-inline'`, `X-Content-Type-Options: nosniff`. Galerie-Datum `"%Y-%m-%d %H:%M"`. Statische Datei über Flasks `static_folder`.
- [ ] **Step 4:** Tests, ruff, mypy grün.
- [ ] **Step 5:** Commit „Add Flask web layer and templates“.

### Task 6: Einstieg und Server

**Files:**
- Create: `src/py01/__main__.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: Task 4 `Store.open`, Task 5 `create_app`.
- Produces: `run(argv: list[str], stop: threading.Event) -> None` (wirft `UsageError(ValueError)` bei ungültigen Flags, kehrt nach `stop.set()` nach geordnetem Shutdown zurück); `main() -> None` (SIGINT/Ctrl+C setzt `stop`; Fehler → `py-01: <meldung>` auf stderr, Exit 1).

- [ ] **Step 1: Failing tests** – `test_run_starts_and_stops`: freien Port holen, `run(["-addr", addr, "-db", str(tmp_path / "t.db")], stop)` im Thread, `/werkstatt` per `urllib` bis 200 (max. 5 s), `stop.set()`, Thread endet in 5 s ohne Ausnahme. `test_invalid_flag_fails`: `run(["-gibt-es-nicht"], Event())` wirft `UsageError`. `test_main_reports_error`: `main()` mit ungültigem Flag via `monkeypatch` auf `sys.argv` → `SystemExit(1)`, stderr beginnt mit `py-01:`.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Implementieren: `argparse.ArgumentParser(prog="py-01", add_help=False, exit_on_error=False)` mit `-db` (Default `py-01.db`), `-addr` (Default `127.0.0.1:8080`); `parse_known_args` und Reste/Fehler → `UsageError`. `werkzeug.serving.make_server(host, port, app, threaded=True)`, `serve_forever` im Thread, `stop.wait()`, `server.shutdown()`, Store schließen. Log `server listening addr=http://host:port` über `logging` (Level INFO).
- [ ] **Step 4:** Tests, ruff, mypy grün; manuell `uv run py-01 -db /tmp/x.db` startet, Ctrl+C beendet.
- [ ] **Step 5:** Commit „Add entry point and server“.

### Task 7: Doku, Projektregeln, Abschluss

**Files:**
- Modify: `README.md`, `start-server.md`, `CLAUDE.md`, `.claude/settings.json`

- [ ] **Step 1:** Alle Go-Befehle und -Begriffe ersetzen: Start `uv run py-01`, Tests `uv run pytest`, Lint `uv run ruff check`, Format `uv run ruff format --check`, Typen `uv run mypy`, Import `sqlite3 py-01.db < scripts/import_params.sql`. Struktur in `CLAUDE.md`/`start-server.md` auf `src/py01/...` umstellen, Abweichungen von go-02 (Timeouts, `?`/`#` im Pfad) bei „Bekannte Grenzen“ nachtragen, Erweiterungspunkte (`layout_for`, `draw_figure`, `eval_rule`). CLAUDE.md-Zeilen < 80 Zeichen.
- [ ] **Step 2:** `.claude/settings.json`: allow `uv run pytest:*`, `uv run ruff:*`, `uv run mypy:*`, `uv run py-01:*`, `uv sync`, `git status/diff/log`; ask `git commit`, `git push`, `uv add:*`; deny unverändert.
- [ ] **Step 3:** `grep -rn "go-02\|golang\|go test\|gofmt" --exclude-dir=.git --exclude-dir=docs .` → keine Treffer (außer bewussten Herkunftshinweisen).
- [ ] **Step 4:** Alle Prüfungen grün; App mit `uv run py-01 -db ../go-02/go-02.db` gegen die go-02-Datenbank starten, `/werkstatt`, Generieren und `/galerie` antworten 200.
- [ ] **Step 5:** Commit „Adapt docs and project rules to Python“, `git push`.
