from __future__ import annotations

import logging
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management.base import CommandError
from django.core.management.base import OutputWrapper
from django.test import override_settings
from django.utils.log import ServerFormatter

from hyperdjango.conf import get_vite_dev_server_url
from hyperdjango.integrations.devtools.request_logging import set_request_log_context
from hyperdjango.management.commands.hyper_runserver import (
    Command,
    _DjangoLogPrefixFilter,
    _PrefixedOutput,
    _ViteSupervisor,
    _available_port,
    _forward_vite_output,
    _server_url,
    _startup_banner,
    _vite_command,
    _vite_host,
    _vite_launch,
    _vite_server_args,
    _vite_url,
)


def test_available_port_returns_bindable_port() -> None:
    with patch("hyperdjango.management.commands.hyper_runserver.socket.socket") as factory:
        sock = factory.return_value.__enter__.return_value
        sock.getsockname.return_value = ("127.0.0.1", 43123)

        assert _available_port("127.0.0.1") == 43123
        sock.bind.assert_called_once_with(("127.0.0.1", 0))


def test_vite_url_uses_browser_address_for_wildcard_host() -> None:
    assert _vite_url("0.0.0.0", 43123) == "http://localhost:43123/"
    assert _vite_url("127.0.0.1", 43123) == "http://127.0.0.1:43123/"
    assert _vite_url("devbox.local", 43123) == "http://devbox.local:43123/"


def test_vite_host_defaults_to_django_bind_host() -> None:
    assert _vite_host(None, "0.0.0.0") == "0.0.0.0"
    assert _vite_host(None, "127.0.0.1") == "127.0.0.1"


def test_vite_host_can_override_django_bind_host() -> None:
    assert _vite_host("127.0.0.1", "0.0.0.0") == "127.0.0.1"


def test_vite_server_args_disable_terminal_clearing() -> None:
    assert _vite_server_args("0.0.0.0", 43123) == [
        "--host",
        "0.0.0.0",
        "--port",
        "43123",
        "--strictPort",
        "--no-clearScreen",
    ]
    assert _vite_server_args("127.0.0.1", 0) == [
        "--host",
        "127.0.0.1",
        "--no-clearScreen",
    ]


def test_vite_output_is_merged_with_a_prefix() -> None:
    output = StringIO()
    _forward_vite_output(StringIO("\nVITE ready\nchanged: entry.ts\n"), output)
    assert output.getvalue() == "[vite] VITE ready\n[vite] changed: entry.ts\n"


class _FakeProcess:
    def __init__(self, output: str, return_code: int | None = None) -> None:
        self.stdout = StringIO(output)
        self.return_code = return_code

    def poll(self):
        return self.return_code


def test_vite_supervisor_discovers_actual_port_from_readiness_output(tmp_path) -> None:
    output = StringIO()
    supervisor = _ViteSupervisor(command=["vite"], cwd=tmp_path, output=output)
    supervisor.process = _FakeProcess(
        "VITE v7 ready\n  ➜  Local:   http://localhost:54321/\n"
    )

    supervisor._read_output()

    assert supervisor.wait_until_ready(0.1) == 54321


def test_vite_supervisor_reports_captured_output_when_process_fails(tmp_path) -> None:
    supervisor = _ViteSupervisor(command=["vite"], cwd=tmp_path, output=StringIO())
    supervisor.process = _FakeProcess("error: port is in use\n", return_code=1)
    supervisor._read_output()

    with pytest.raises(CommandError, match="port is in use"):
        supervisor.wait_until_ready(0.1)


def test_vite_supervisor_strips_colors_when_requested(tmp_path) -> None:
    output = StringIO()
    supervisor = _ViteSupervisor(
        command=["vite"], cwd=tmp_path, output=output, strip_colors=True
    )
    supervisor.process = _FakeProcess(
        "Local: http://localhost:54321/\n\x1b[31mhmr update failed\x1b[0m\n"
    )
    supervisor._read_output()
    assert output.getvalue() == "[vite] hmr update failed\n"


def test_autoreload_child_does_not_start_another_vite(monkeypatch) -> None:
    command = Command()
    called = []
    monkeypatch.setenv("RUN_MAIN", "true")
    monkeypatch.setattr(command, "_run_django", lambda **options: called.append(options))

    command.run(auto_port=False, no_vite=False)

    assert len(called) == 1


@override_settings(HYPER_VITE_COMMAND=None)
def test_package_manager_is_detected_from_lockfile(tmp_path: Path) -> None:
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n")
    launch = _vite_launch(tmp_path)
    assert launch.manager == "pnpm"
    assert launch.install_command == "pnpm install"


def test_django_output_is_prefixed_without_filling_blank_lines() -> None:
    stream = StringIO()
    output = OutputWrapper(stream)
    wrapped = _PrefixedOutput(output, "django")
    wrapped.write("Performing system checks...\n\n")
    assert stream.getvalue() == "[django] Performing system checks...\n\n"


def test_django_request_log_records_are_prefixed_without_mutating_original() -> None:
    record = logging.LogRecord(
        "django.server",
        logging.INFO,
        __file__,
        1,
        '"GET / HTTP/1.1" 200 42',
        (),
        None,
    )
    record.status_code = 200
    log_filter = _DjangoLogPrefixFilter()

    prefixed = log_filter.filter(record)

    assert prefixed is not record
    assert prefixed.status_code == 200
    assert prefixed.getMessage() == '[django] "GET / HTTP/1.1" 200 42'
    assert record.getMessage() == '"GET / HTTP/1.1" 200 42'


def test_django_request_log_links_to_devtools_trace() -> None:
    set_request_log_context(
        duration_ms=12.345,
        trace_url="http://localhost:8000/__hyperdebug__/requests/abc/",
    )
    record = logging.LogRecord(
        "django.server",
        logging.INFO,
        __file__,
        1,
        '"GET / HTTP/1.1" 200 42',
        (),
        None,
    )

    rendered = _DjangoLogPrefixFilter().filter(record).getMessage()

    assert "12.3 ms" in rendered
    assert "/__hyperdebug__/requests/abc/" in rendered


def test_django_server_formatter_keeps_status_colors() -> None:
    record = logging.LogRecord(
        "django.server",
        logging.ERROR,
        __file__,
        1,
        '"GET /broken HTTP/1.1" 500 42',
        (),
        None,
    )
    record.status_code = 500
    prefixed = _DjangoLogPrefixFilter().filter(record)

    formatter = ServerFormatter(fmt="{message}", style="{")
    formatter.style.HTTP_SERVER_ERROR = lambda message: f"\x1b[31m{message}\x1b[0m"
    rendered = formatter.format(prefixed)

    assert "[django]" in rendered
    assert "\x1b[" in rendered
    assert record.getMessage() == '"GET /broken HTTP/1.1" 500 42'


def test_non_django_log_records_are_not_prefixed() -> None:
    record = logging.LogRecord(
        "myapp",
        logging.INFO,
        __file__,
        1,
        "background job complete",
        (),
        None,
    )
    filtered = _DjangoLogPrefixFilter().filter(record)
    assert filtered is record
    assert filtered.getMessage() == "background job complete"


def test_startup_banner_lists_both_servers() -> None:
    assert _server_url("::1", 8000) == "http://[::1]:8000/"
    assert _startup_banner("http://0.0.0.0:8000/", "http://localhost:43123/") == (
        "HyperDjango development server\n"
        "  Local    http://0.0.0.0:8000/\n"
        "  Vite     http://localhost:43123/\n\n"
    )


@override_settings(HYPER_VITE_COMMAND=["pnpm", "vite"])
def test_vite_command_accepts_sequence_setting() -> None:
    assert _vite_command() == ["pnpm", "vite"]


@override_settings(HYPER_VITE_COMMAND="npm run frontend --")
def test_vite_command_accepts_string_setting() -> None:
    assert _vite_command() == ["npm", "run", "frontend", "--"]


@override_settings(HYPER_VITE_DEV_SERVER_URL="http://localhost:5173/")
def test_runtime_vite_url_takes_precedence(monkeypatch) -> None:
    monkeypatch.setenv("HYPER_VITE_DEV_SERVER_URL", "http://127.0.0.1:43123")
    assert get_vite_dev_server_url() == "http://127.0.0.1:43123/"
