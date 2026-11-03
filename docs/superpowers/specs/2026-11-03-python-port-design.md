# py-01: Python-Portierung von go-02 – Design

Stand: 2026-11-03 · Status: Entwurf zur Freigabe

## Zweck

py-01 ist dieselbe App wie go-02 – lokale Web-App, die aus JSON-Parametern
SVG-Bilder mit geometrischen Figuren erzeugt und Varianten und Bilder in
SQLite ablegt –, aber in Python geschrieben. Es ist eine **1:1-Übersetzung**:
gleiche Seiten, gleiche Routen, gleiches Parameterformat, gleiches
Datenbankschema. Eine Datenbank von go-02 funktioniert in py-01 und umgekehrt.

Fachliche Referenz bleibt das go-02-Design
(`docs/superpowers/specs/2026-11-01-bildgenerator-design.md`) und der Go-Code
im Repo `djw4u/go-02`. Wo dieses Dokument schweigt, gilt das Verhalten von go-02.

## Ziele

- Gleiches sichtbares Verhalten wie go-02: Werkstatt, Galerie, Bildauslieferung,
  Fehlermeldungen in der Oberfläche, HTTP-Statuscodes, Weiterleitungen.
- Gleiches SQL-Schema, Import weiter per `scripts/import_params.sql` (unverändert).
- Generator ohne HTTP und ohne Datenbank nutzbar (wie go-02).
- Alle 52 Go-Tests haben ein pytest-Gegenstück, das dasselbe Verhalten prüft.

## Nicht-Ziele

- Neue Funktionen oder geänderte Oberfläche. Die zurückgestellten Punkte aus
  go-02 (`start-server.md`, „Bekannte Grenzen“) bleiben zurückgestellt.
- Bitgleiche Bilder bei gleichem Seed wie go-02 (andere Zufallsgeneratoren).
- Produktionsbetrieb im Netz.

## Anti-Ziele

- Stille Fehler: ungültige Parameter führen immer zu einer Meldung.
- Abschwächung der Sicherheit: CSP, `nosniff`, Vorschau nur als `<img>` mit
  `data:`-URI, Formular- und SVG-Größengrenzen bleiben.
- Logik in der Web-Schicht, die in den Generator gehört.

## Ansätze

- **A: Flask + Jinja2 + `sqlite3` (Standardbibliothek)** – entspricht
  `net/http` + `html/template`; Autoescaping, Test-Client wie `httptest`,
  nur zwei Abhängigkeiten.
- **B: Nur Standardbibliothek** (`http.server`) – keine Abhängigkeiten, aber
  keine sicher maskierende Template-Engine; Formular-, Größen- und
  Timeout-Logik selbst gebaut. Mehr Code, mehr Sicherheitsrisiko.
- **C: FastAPI + Jinja2 + Uvicorn** – asynchron und modern, für eine lokale
  Einzelnutzer-App ohne JSON-API überdimensioniert.

**Gewählt (Eigentümer): A**, mit `uv`, `pytest`, `ruff`, `mypy`.

## Rahmenbedingungen

- Python 3.14 (über mise installiert); `requires-python = ">=3.12"`,
  `.python-version` = `3.14`. *(Entscheidung des Entwurfs-Autors)*
- Projekt und Abhängigkeiten mit `uv` (`pyproject.toml`, `uv.lock` eingecheckt).
- Laufzeit-Abhängigkeit: nur `flask` (bringt Jinja2/Werkzeug mit).
  Entwicklung: `pytest`, `ruff`, `mypy`.
- `sqlite3` aus der Standardbibliothek; kein ORM.

## Repo und Herkunft

- Lokal `~/code/py-01`, GitHub `djw4u/py-01` (öffentlich, Eigentümer),
  Branch `main`.
- Eigene Standard-Datenbank `py-01.db` (Eigentümer); go-02-Daten mit
  `-db ../go-02/go-02.db` nutzbar.
- Entsteht als Kopie von go-02 **ohne Git-Historie** (wie go-02 aus go-01),
  danach werden die Go-Dateien durch Python ersetzt.
- Bleiben unverändert: `scripts/import_params.sql`, `style.css`,
  `docs/superpowers/` (go-02-Spec und -Plan als Herkunft; neue Spec und Plan
  kommen dazu).
- Entfallen: `go.mod`, `go.sum`, `cmd/`, `internal/`, `.golangci.yml`.
- Angepasst: `README.md`, `start-server.md`, `CLAUDE.md`,
  `.claude/settings.json`, `.gitignore` – alle Erwähnungen von go-02/Go auf
  py-01/Python, Befehle auf uv/pytest/ruff/mypy.
- Name in der Oberfläche (`<title>`, Navigation, Hinweistexte): `py-01`.

## Architektur

```
src/py01/
  __main__.py        Einstieg: Flags, Verdrahtung, Serverstart (wie cmd/go-02)
  generator/         Parameter -> SVG; ohne Flask, ohne Datenbank
    params.py rules.py layout.py figure.py generator.py
  store.py           SQLite-Zugriff (wie internal/store)
  web/
    app.py           Flask-App-Factory create_app(store, new_source)
    templates/       layout.html, werkstatt.html, galerie.html (Jinja2)
    static/style.css unverändert aus go-02
tests/               pytest, gespiegelt nach Paket
scripts/import_params.sql
```

Paketname `py01` (Bindestrich ist in Python-Namen nicht erlaubt).
Abhängigkeitsrichtung wie go-02: `web` nutzt `generator` und `store`;
`generator` kennt keines von beiden. `web` definiert ein eigenes kleines
`Store`-Protokoll (`typing.Protocol`) statt der konkreten Klasse.

## Generator

Übersetzung von `internal/generator` Funktion für Funktion; Fehler als eigene
Ausnahme `ParamError(ValueError)`, deren Text in der Oberfläche erscheint.

- **Zufallsquelle:** Protokoll `Source` mit `randrange(n) -> int` und
  `random() -> float` (entspricht `IntN`/`Float64`); `random.Random` erfüllt
  es. App: pro Anfrage `random.Random()` frisch gesät. Tests: fester Seed.
- **JSON-Zahlen:** Go liest jede Zahl als `float64`. Python liefert `int` oder
  `float`; beide gelten als Zahl. **`bool` ist in Python ein `int` und muss
  überall ausdrücklich abgelehnt werden.**
- **JSON-Parsing:** `json.loads` akzeptiert `NaN`/`Infinity`, Go nicht. Mit
  `parse_constant` ablehnen, damit dieselben Eingaben gültig sind.
- **Fehlertexte:** gleicher Wortlaut wie go-02. Wo Go den Typ ausgibt (`%T`,
  z. B. `float64`, `[]interface {}`), stehen JSON-Typnamen: `number`,
  `string`, `bool`, `array`, `object`, `null`. *(Entscheidung des
  Entwurfs-Autors: Go-Typnamen wären in Python sinnlos.)*
- **`num()`:** höchstens 3 Nachkommastellen, kaufmännisch gerundet **weg von
  null** wie Go `math.Round` (nicht Pythons `round()`, das zur geraden Zahl
  rundet), keine nachgestellten Nullen, ganze Zahlen ohne `.0`, nie
  Exponentschreibweise, `-0` wird `0`, unendlich bleibt `+Inf`/`-Inf` wie in
  go-02 (bekannte Grenze, nicht beheben). Tabelle aus `TestNum` übernehmen.
- **Attributmaskierung:** wie Go `html.EscapeString`: `<` `&lt;`, `>` `&gt;`,
  `&` `&amp;`, `'` `&#39;`, `"` `&#34;`. Python `html.escape` liefert
  `&#x27;` und `&quot;` – Go-Ausgabe nachbilden.
- Regeln, Anordnungen, Figuren, Grenzen (10000 Figuren, 1000 Ecken, `ri` bis
  2^31, PDS 100 Versuche je Figur), Attributreihenfolge und
  Auswertungsreihenfolge der Regeln je Figur exakt wie go-02.

## Store

- `sqlite3.connect(path, check_same_thread=False)`, eine Verbindung,
  serialisiert mit `threading.Lock` (entspricht `SetMaxOpenConns(1)`).
- `PRAGMA foreign_keys = ON`, Schema per `executescript` mit identischem SQL.
- Pfad direkt öffnen (keine `file:`-URI); damit entfällt die go-02-Grenze mit
  `?`/`#` im Pfad. *(Entscheidung des Entwurfs-Autors, einfachste Lösung.)*
- Datenklassen `Variant`, `Image` (`dataclass(frozen=True)`), `created_at`
  als UTC-`datetime` aus `"%Y-%m-%d %H:%M:%S"`.
- `NotFoundError` statt `ErrNotFound`. Methoden und Semantik wie go-02
  (`parent_id` 0/None = keine Ausgangsvariante, `list_images(0)` = alle,
  neueste zuerst).

## Web

Routen, Statuscodes und Texte exakt wie go-02:

| Route | Verhalten |
|---|---|
| `GET /` | 303 nach `/werkstatt` |
| `GET /werkstatt?variant=ID` | 200; unbekannte/ungültige ID 404 |
| `POST /werkstatt/generate` | 200 mit Vorschau; ungültige Parameter 422 |
| `POST /werkstatt/save-image` | 303 nach `/galerie?variant=ID`; kein SVG/zu groß 422 |
| `POST /werkstatt/save-variant` | 303 nach `/werkstatt?variant=NEU`; leerer Name/ungültig 422 |
| `GET /galerie?variant=ID` | 200, Filter |
| `GET /bilder/<id>.svg` | SVG mit CSP und `nosniff`; sonst 404 |
| `GET /static/style.css` | 200 |

- Templates nach Jinja2 übersetzt, Markup unverändert. Autoescaping an.
- Formulargrenze 2 MiB: `MAX_CONTENT_LENGTH` **und** `MAX_FORM_MEMORY_SIZE`
  auf 2 MiB setzen (Werkzeug begrenzt ein Formularfeld sonst auf 500 KB, das
  SVG-Feld darf bis 1 MiB groß sein). Zu groß: 413 „Anfrage zu groß“.
- ID-Parsing wie Go `strconv.ParseInt` + `> 0`: nur `^[+-]?[0-9]+$`, Bereich
  int64. Python `int()` würde auch `" 5"` und `"1_0"` annehmen.
- Unerwartete Fehler: Log mit `logging`, Antwort 500 „Interner Fehler“.
- Methoden wie go-02: falsche Methode ergibt 405.

## Start und Server

- Aufruf: `uv run py-01` (Script-Eintrag in `pyproject.toml`) oder
  `uv run python -m py01`.
- Flags wie go-02 mit einem Bindestrich: `-db` (Default `py-01.db`),
  `-addr` (Default `127.0.0.1:8080`). Ungültige Flags: Fehler, Exit-Code 1.
- Server: `werkzeug.serving.make_server(..., threaded=True)`; Ctrl+C beendet
  geordnet. Log „server listening addr=http://…“.
- **Abweichung:** Der Werkzeug-Server kennt keine getrennten Lese-/Schreib-
  Timeouts wie go-02. Für eine lokale Einzelnutzer-App hingenommen; der Test
  `TestNewServer_SetsAllTimeouts` entfällt ersatzlos. *(Entscheidung des
  Entwurfs-Autors; Alternative wäre `waitress` als weitere Abhängigkeit.)*

## Tests

- Jeder der 52 Go-Tests bekommt ein pytest-Gegenstück (außer dem Timeout-Test).
  Tests prüfen Verhalten (Anzahl, Arten, Grenzen, Abstände, Fehlermeldungen),
  keine bei Go aufgezeichneten Zufallswerte.
- Deterministisch: `random.Random(seed)`, Datenbank nur in `tmp_path`.
- Web-Tests mit dem Flask-Test-Client gegen echten Store in `tmp_path`.
- Import-Skript-Test braucht `sqlite3` im `PATH`, sonst `pytest.skip`.
- Server-Start-Test: `run()` mit freiem Port in einem Thread starten,
  anfragen, stoppen.

## Werkzeuge und Prüfungen

- `uv run pytest`, `uv run ruff check`, `uv run ruff format --check`,
  `uv run mypy` (strict, auf `src` und `tests`) – alle grün vor Abschluss.
- Ruff: Standardregeln plus `I` (Importe), `B`, `UP`.
  *(Entscheidung des Entwurfs-Autors)*
- Keine CI (wie go-02).

## Was dem Umsetzenden überlassen bleibt

- Aufteilung in Tasks und Reihenfolge (Plan).
- Interne Hilfsfunktionen und Namen, solange die obigen Schnittstellen und das
  Verhalten von go-02 eingehalten werden.
