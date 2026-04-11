from __future__ import annotations

from pathlib import Path

from hyperdjango.apps import WATCH_GLOBS, _watch_hyper_frontend


class _Sender:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, str]] = []

    def watch_dir(self, path: Path, glob: str) -> None:
        self.calls.append((path, glob))


def test_watch_hyper_frontend_registers_globs(monkeypatch) -> None:
    frontend_dir = Path("/tmp/hyper")
    monkeypatch.setattr("hyperdjango.conf.get_frontend_dir", lambda: frontend_dir)

    sender = _Sender()
    _watch_hyper_frontend(sender=sender)

    assert sender.calls == [(frontend_dir, glob) for glob in WATCH_GLOBS]
