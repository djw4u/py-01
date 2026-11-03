# py-01

Lokale Web-App, die aus JSON-Parametern SVG-Bilder mit geometrischen Figuren erzeugt. Parameter-Varianten und gespeicherte Bilder liegen in SQLite. py-01 ist die 1:1-Übersetzung von [go-02](https://github.com/djw4u/go-02) nach Python (Flask); Seiten, Parameterformat und Datenbankschema sind gleich. Entwickelt spec-driven mit Superpowers; Entwürfe und Pläne stehen unter `docs/superpowers/`.

## Start

Voraussetzung: [uv](https://docs.astral.sh/uv/). Python 3.12 oder neuer holt uv bei Bedarf selbst.

```
uv sync
uv run py-01
```

Danach ist die App unter <http://127.0.0.1:8080> erreichbar.

| Flag    | Standard         | Bedeutung                    |
|---------|------------------|------------------------------|
| `-db`   | `py-01.db`       | Pfad der SQLite-Datenbank    |
| `-addr` | `127.0.0.1:8080` | Adresse des HTTP-Servers     |

Die Datenbank und ihr Schema legt die App beim ersten Start selbst an. Eine Datenbank von go-02 funktioniert unverändert: `uv run py-01 -db ../go-02/go-02.db`.

## Parameter importieren

Der Import läuft außerhalb der App per SQL. Die App muss einmal gestartet worden sein. Im Verzeichnis, das den Ordner `params/` mit den `*.json`-Dateien enthält:

```
sqlite3 py-01.db < scripts/import_params.sql
```

Bereits importierte Dateien werden übersprungen, ungültiges JSON ebenfalls.

## Bedienung

- **Werkstatt:** Variante wählen, JSON ändern, „Generieren“ zeigt eine Vorschau (noch nicht gespeichert). „SVG speichern“ legt das Bild ab, „Neue Variante“ speichert geänderte Parameter unter einem neuen Namen.
- **Galerie:** Alle gespeicherten Bilder, filterbar nach Variante. Ein Klick öffnet das SVG im eigenen Fenster.

Gespeicherte SVGs gelten als fremder Inhalt: Sie werden nur als `<img>` und mit einer strengen Content-Security-Policy ausgeliefert.

## Entwicklung

```
uv run pytest
uv run ruff check
uv run ruff format --check
uv run mypy
```
