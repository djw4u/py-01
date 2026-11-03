"""SQLite-Zugriff auf Parameter-Varianten und erzeugte Bilder."""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

SCHEMA = """
CREATE TABLE IF NOT EXISTS param_variants (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  params      TEXT NOT NULL CHECK (json_valid(params)),
  source_file TEXT UNIQUE,
  parent_id   INTEGER REFERENCES param_variants(id),
  created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS images (
  id          INTEGER PRIMARY KEY,
  variant_id  INTEGER NOT NULL REFERENCES param_variants(id),
  svg         TEXT NOT NULL,
  created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);"""

_VARIANT_COLS = "id, name, params, source_file, parent_id, created_at"
_IMAGE_COLS = "id, variant_id, svg, created_at"


class NotFoundError(LookupError):
    """Ein gesuchter Datensatz existiert nicht."""


@dataclass(frozen=True)
class Variant:
    """Ein gespeicherter Parametersatz."""

    id: int
    name: str
    params: str  # komplette JSON-Datei inkl. äußerem "params"
    source_file: str | None
    parent_id: int | None
    created_at: datetime


@dataclass(frozen=True)
class Image:
    """Ein gespeichertes SVG, das aus einer Variante entstanden ist."""

    id: int
    variant_id: int
    svg: str
    created_at: datetime


def _time(s: str) -> datetime:
    return datetime.strptime(s, TIME_FORMAT).replace(tzinfo=UTC)


def _variant(row: tuple[int, str, str, str | None, int | None, str]) -> Variant:
    return Variant(row[0], row[1], row[2], row[3], row[4], _time(row[5]))


def _image(row: tuple[int, int, str, str]) -> Image:
    return Image(row[0], row[1], row[2], _time(row[3]))


class Store:
    """Zugriff auf die SQLite-Datenbank.

    Eine Verbindung, serialisiert durch ein Lock; das vermeidet SQLITE_BUSY
    innerhalb der App.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._lock = threading.Lock()

    @classmethod
    def open(cls, path: str | Path) -> Store:
        """Öffnet die Datenbank und legt das Schema an, falls es fehlt."""
        conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript(SCHEMA)
        except sqlite3.Error:
            conn.close()
            raise
        return cls(conn)

    def close(self) -> None:
        """Schließt die Datenbank."""
        with self._lock:
            self._conn.close()

    def list_variants(self) -> list[Variant]:
        """Alle Varianten nach id aufsteigend."""
        with self._lock:
            rows = self._conn.execute(
                f"SELECT {_VARIANT_COLS} FROM param_variants ORDER BY id"
            ).fetchall()
        return [_variant(r) for r in rows]

    def get_variant(self, id: int) -> Variant:
        """Variante mit der id; sonst NotFoundError."""
        with self._lock:
            row = self._conn.execute(
                f"SELECT {_VARIANT_COLS} FROM param_variants WHERE id = ?", (id,)
            ).fetchone()
        if row is None:
            raise NotFoundError(f"variant {id}")
        return _variant(row)

    def create_variant(self, name: str, params: str, parent_id: int = 0) -> int:
        """Legt eine Variante an; parent_id 0 heißt: keine Ausgangsvariante."""
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO param_variants (name, params, parent_id) VALUES (?, ?, ?)",
                (name, params, parent_id or None),
            )
        return _rowid(cur)

    def save_image(self, variant_id: int, svg: str) -> int:
        """Speichert ein SVG zur Variante."""
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO images (variant_id, svg) VALUES (?, ?)",
                (variant_id, svg),
            )
        return _rowid(cur)

    def list_images(self, variant_id: int = 0) -> list[Image]:
        """Bilder einer Variante, neueste zuerst; 0 liefert alle."""
        query = f"SELECT {_IMAGE_COLS} FROM images"
        args: tuple[int, ...] = ()
        if variant_id:
            query += " WHERE variant_id = ?"
            args = (variant_id,)
        query += " ORDER BY id DESC"
        with self._lock:
            rows = self._conn.execute(query, args).fetchall()
        return [_image(r) for r in rows]

    def get_image(self, id: int) -> Image:
        """Bild mit der id; sonst NotFoundError."""
        with self._lock:
            row = self._conn.execute(
                f"SELECT {_IMAGE_COLS} FROM images WHERE id = ?", (id,)
            ).fetchone()
        if row is None:
            raise NotFoundError(f"image {id}")
        return _image(row)


def _rowid(cur: sqlite3.Cursor) -> int:
    if cur.lastrowid is None:
        raise RuntimeError("insert returned no row id")
    return cur.lastrowid
