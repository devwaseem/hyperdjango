from __future__ import annotations

from pathlib import Path

import hyperdjango

from hyperdjango.apps import HyperDjangoConfig, WATCH_GLOBS


class _Signal:
    def __init__(self) -> None:
        self.receiver = None
        self.dispatch_uid = None

    def connect(self, receiver, dispatch_uid=None) -> None:
        self.receiver = receiver
        self.dispatch_uid = dispatch_uid


class _Autoreload:
    def __init__(self) -> None:
        self.autoreload_started = _Signal()


class _Sender:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, str]] = []

    def watch_dir(self, path: Path, glob: str) -> None:
        self.calls.append((path, glob))


def test_ready_registers_hyper_frontend_watch(monkeypatch) -> None:
    frontend_dir = Path("/tmp/hyper")
    autoreload = _Autoreload()

    monkeypatch.setattr(
        "django.utils.autoreload.autoreload_started", autoreload.autoreload_started
    )
    monkeypatch.setattr("hyperdjango.conf.get_frontend_dir", lambda: frontend_dir)

    app = HyperDjangoConfig("hyperdjango", hyperdjango)
    app.ready()

    assert autoreload.autoreload_started.receiver is not None
    assert (
        autoreload.autoreload_started.dispatch_uid == "hyperdjango.watch_hyper_frontend"
    )

    sender = _Sender()
    autoreload.autoreload_started.receiver(sender=sender)

    assert sender.calls == [(frontend_dir, glob) for glob in WATCH_GLOBS]
