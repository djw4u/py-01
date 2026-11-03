"""Startet die lokale Web-App zum Erzeugen von SVG-Bildern."""

from __future__ import annotations

import argparse
import logging
import random
import signal
import sqlite3
import sys
import threading
from typing import NoReturn

from werkzeug.serving import make_server

from py01.generator import Source
from py01.store import Store
from py01.web import create_app

log = logging.getLogger("py01")


class UsageError(ValueError):
    """Ungültige Kommandozeile."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise UsageError(message)


def _new_source() -> Source:
    """Pro Aufruf eine frisch gesäte Zufallsquelle."""
    return random.Random()


def _split_addr(addr: str) -> tuple[str, int]:
    host, sep, port = addr.rpartition(":")
    if not sep or not port.isdigit() or int(port) > 65535:
        raise UsageError(f"invalid address {addr!r}, want host:port")
    return host, int(port)


def run(argv: list[str], stop: threading.Event) -> None:
    """Startet den Server und kehrt nach stop.set() zurück, sobald er
    geordnet heruntergefahren ist."""
    parser = _Parser(prog="py-01", add_help=False)
    parser.add_argument(
        "-db", "--db", default="py-01.db", help="Pfad der SQLite-Datenbank"
    )
    parser.add_argument(
        "-addr", "--addr", default="127.0.0.1:8080", help="Adresse des HTTP-Servers"
    )
    args, rest = parser.parse_known_args(argv)
    if rest:
        raise UsageError(f"unknown arguments: {' '.join(rest)}")
    host, port = _split_addr(args.addr)

    store = Store.open(args.db)
    try:
        server = make_server(host, port, create_app(store, _new_source), threaded=True)
        serving = threading.Thread(target=server.serve_forever, daemon=True)
        serving.start()
        log.info("server listening addr=http://%s:%d", host, server.server_port)
        stop.wait()
        server.shutdown()
        serving.join(5)
        server.server_close()
    finally:
        store.close()


def main() -> None:
    """Einstieg für `py-01` und `python -m py01`."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    try:
        run(sys.argv[1:], stop)
    except (UsageError, OSError, sqlite3.Error) as e:
        print(f"py-01: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
