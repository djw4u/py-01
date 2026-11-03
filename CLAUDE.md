# py-01

Lokale Web-App: JSON-Parameter -> SVG-Bilder, Ablage in SQLite.
1:1-Python-Portierung von go-02 (gleiche Seiten, Routen, DB-Schema).
Details: `README.md`, `start-server.md`, `docs/superpowers/`.

## Befehle

- Setup:  `uv sync`
- Start:  `uv run py-01`
- Flags:  `-db` (Default `py-01.db`), `-addr` (`127.0.0.1:8080`)
- Test:   `uv run pytest`
- Einzel: `uv run pytest tests/web/test_app.py -k name`
- Lint:   `uv run ruff check`
- Format: `uv run ruff format --check` (schreiben: ohne `--check`)
- Typen:  `uv run mypy` (strict, `src` und `tests`)
- Vor Abschluss: Test, Lint, Format, Typen grün.

Konfiguration aller Werkzeuge in `pyproject.toml`. Keine CI.
`docs/` ist von ruff ausgenommen (ruff formatiert sonst Markdown).

## Struktur

    src/py01/__main__.py  Flags, Verdrahtung, Werkzeug-Server
    src/py01/generator/   Parameter -> SVG (kein Flask, keine DB)
    src/py01/store.py     SQLite-Zugriff (sqlite3, kein ORM)
    src/py01/web/         Flask-App, Jinja2-Templates, CSS
    tests/                pytest, gespiegelt nach Paket
    scripts/              import_params.sql (Import per sqlite3)
    docs/superpowers/     Specs und Pläne

- `web` nutzt `generator` und `store`, nie umgekehrt.
- `web` definiert sein eigenes `StoreLike`-Protokoll.
- Erweitern: Anordnung in `_LAYOUTS` (`layout.py`), Figur in
  `draw_figure`, Regel in `eval_rule`.

## Konventionen

- Ungültige Parameter: `ParamError` mit Feldnamen,
  `field "x": want ..., got ...`; nie stilles Ergebnis.
- Fehlertexte, Log-Meldungen, Bezeichner: englisch.
- Kommentare, Docstrings, Nutzertexte (UI, HTTP): deutsch.
- Typannotationen überall (mypy strict).
- Zufall nur über `generator.Source`, nie global.
- Server rendert HTML (Jinja2, Autoescaping), kein JavaScript.
- Tests: pytest, `parametrize` statt Schleifen.

## Tests

- Deterministisch: `random.Random(seed)`, DB nur in `tmp_path`.
- Web-Tests mit dem Flask-Test-Client, keine echten Netzaufrufe.
- `test_import_script.py` braucht `sqlite3` im `PATH`,
  sonst wird der Test übersprungen (kein Fehler).

## Stolpersteine

- Gleichheit mit go-02 ist Absicht: Rundung wie Gos `math.Round`,
  Maskierung wie `html.EscapeString`, `bool` ist keine Zahl,
  `NaN`/`Infinity` im JSON ungültig. Nicht "pythonisch" vereinfachen.
- Laufzeit-Abhängigkeit nur `flask`. Keine Umgebungsvariablen.
- Eine DB-Verbindung mit Lock gegen `SQLITE_BUSY`.
- Formulargrenze 2 MiB (`MAX_CONTENT_LENGTH`,
  `MAX_FORM_MEMORY_SIZE`); SVG höchstens 1 MiB.
- Default-DB `py-01.db` im Arbeitsverzeichnis; `*.db` ist ignoriert.
- Parameterformat und Grenzen: `start-server.md`.
- `.superpowers/` ist ignoriert (Arbeitsdateien).
- Gespeicherte SVGs sind fremder Inhalt. CSP, `nosniff` und
  `<img>` mit `data:`-URI nicht abschwächen.
- Ruff-/mypy-Regeln nicht lockern; `# noqa`/`# type: ignore`
  nur mit Begründung.

## Arbeitsweise

- Neue Funktion: Brainstorming -> Spec (`docs/superpowers/specs/`)
  -> Plan (`docs/superpowers/plans/`) -> TDD, erst ein Test.
- Commit-Nachrichten: Imperativ, kurz und konkret, ohne Präfix.
- Ein Thema je Commit.
- Neue Abhängigkeit oder Umbau: erst kurz begründen.
- Kein `git push --force`; `uv.lock` nur über `uv` ändern.
- Keine Änderung an `.env`, Secrets oder CI ohne Rückfrage.
