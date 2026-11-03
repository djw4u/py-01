import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest

from py01.__main__ import UsageError, main, run


def free_addr() -> str:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return f"127.0.0.1:{s.getsockname()[1]}"


def test_run_starts_and_stops(tmp_path: Path) -> None:
    addr = free_addr()
    stop = threading.Event()
    errors: list[BaseException] = []

    def target() -> None:
        try:
            run(["-addr", addr, "-db", str(tmp_path / "t.db")], stop)
        except BaseException as e:  # noqa: BLE001 - Fehler an den Test melden
            errors.append(e)

    t = threading.Thread(target=target)
    t.start()
    deadline = time.monotonic() + 5
    ready = False
    while not ready:
        assert t.is_alive(), f"run endete vorzeitig: {errors}"
        assert time.monotonic() < deadline, "Server wurde nicht erreichbar"
        try:
            with urllib.request.urlopen(f"http://{addr}/werkstatt") as resp:
                ready = resp.status == 200
        except OSError:
            time.sleep(0.01)

    stop.set()
    t.join(5)
    assert not t.is_alive(), "run endete nach Abbruch nicht"
    assert errors == []


def test_invalid_flag_fails() -> None:
    with pytest.raises(UsageError):
        run(["-gibt-es-nicht"], threading.Event())


def test_invalid_addr_fails() -> None:
    with pytest.raises(UsageError):
        run(["-addr", "kein-port"], threading.Event())


def test_main_reports_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["py-01", "-gibt-es-nicht"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert capsys.readouterr().err.startswith("py-01:")
