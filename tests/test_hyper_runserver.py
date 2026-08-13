from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from django.core.management.base import CommandError
from django.core.management.base import OutputWrapper
from django.test import override_settings
from django.utils.log import ServerFormatter

from hyperdjango.conf import get_vite_dev_server_url
from hyperdjango.integrations.devtools.request_logging import (
    SupervisedRequestLogFilter,
    set_request_log_context,
)
from hyperdjango.management.commands.hyper_runserver import (
    Command,
    _DjangoLogPrefixFilter,
    _PrefixedOutput,
    _ViteSupervisor,
    _available_port,
    _django_runserver_argv,
    _forward_django_output,
    _forward_vite_output,
    _preserve_child_color,
    _run_django_reloader,
    _restart_django_with_reloader,
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

    def wait(self, timeout=None):
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


def test_django_reload_command_uses_builtin_runserver() -> None:
    argv = [
        "manage.py",
        "hyper_runserver",
        "0.0.0.0:8000",
        "--vite-host",
        "127.0.0.1",
        "--vite-public-host=devbox.local",
        "--vite-port",
        "5173",
        "--vite-timeout=20",
        "--package-manager",
        "npm",
        "--auto-port",
        "--open",
        "--verbose",
        "--no-vite",
        "--nothreading",
        "--settings=app.settings.dev",
    ]

    translated = _django_runserver_argv(
        argv,
        addr="0.0.0.0",
        port=43123,
        original_addrport="0.0.0.0:8000",
    )

    assert translated == [
        "manage.py",
        "runserver",
        "--nothreading",
        "--settings=app.settings.dev",
        "0.0.0.0:43123",
    ]


def test_hyper_runserver_rejects_abbreviated_options() -> None:
    parser = Command().create_parser("manage.py", "hyper_runserver")

    with pytest.raises(CommandError, match="unrecognized arguments: --vite-ho"):
        parser.parse_args(["--vite-ho", "127.0.0.1"])


def test_django_reload_command_distinguishes_option_values_from_addrport() -> None:
    translated = _django_runserver_argv(
        [
            "manage.py",
            "hyper_runserver",
            "--verbosity",
            "2",
            "--pythonpath",
            "2",
            "2",
        ],
        addr="127.0.0.1",
        port=43123,
        original_addrport="2",
    )

    assert translated == [
        "manage.py",
        "runserver",
        "--verbosity",
        "2",
        "--pythonpath",
        "2",
        "127.0.0.1:43123",
    ]


def test_django_reload_command_drops_unavailable_staticfiles_options() -> None:
    translated = _django_runserver_argv(
        [
            "manage.py",
            "hyper_runserver",
            "--nostatic",
            "--insecure",
            "8000",
        ],
        addr="127.0.0.1",
        port=8000,
        original_addrport="8000",
        use_staticfiles=False,
    )

    assert translated == ["manage.py", "runserver", "127.0.0.1:8000"]


def test_django_reload_command_preserves_color_for_terminal_output() -> None:
    output = Mock()
    output.isatty.return_value = True

    child_args = _preserve_child_color(
        [sys.executable, "manage.py", "runserver"],
        output=output,
        no_color=False,
        force_color=False,
    )

    assert child_args[-1] == "--force-color"


def test_django_reload_color_precedes_end_of_options_separator() -> None:
    output = Mock()
    output.isatty.return_value = True

    child_args = _preserve_child_color(
        [sys.executable, "manage.py", "runserver", "--", "127.0.0.1:8000"],
        output=output,
        no_color=False,
        force_color=False,
    )

    assert child_args[-3:] == ["--force-color", "--", "127.0.0.1:8000"]


@pytest.mark.parametrize(
    ("no_color", "force_color"),
    ((True, False), (False, True)),
)
def test_django_reload_command_does_not_duplicate_color_options(
    no_color: bool,
    force_color: bool,
) -> None:
    output = Mock()
    output.isatty.return_value = True
    original = [
        sys.executable,
        "manage.py",
        "runserver",
        "--no-color" if no_color else "--force-color",
    ]

    child_args = _preserve_child_color(
        original,
        output=output,
        no_color=no_color,
        force_color=force_color,
    )

    assert child_args == original


def test_django_reloader_restarts_builtin_child_and_prefixes_output(
    monkeypatch,
) -> None:
    processes = [
        _FakeProcess("first child\n", return_code=3),
        _FakeProcess("second child\n", return_code=0),
    ]
    output = StringIO()
    wrapped = OutputWrapper(output)
    popen = patch(
        "hyperdjango.management.commands.hyper_runserver.subprocess.Popen",
        side_effect=processes,
    )
    monkeypatch.delenv("RUN_MAIN", raising=False)
    monkeypatch.delenv("PYTHONUNBUFFERED", raising=False)

    with popen as factory:
        return_code = _restart_django_with_reloader(
            [sys.executable, "manage.py", "runserver", "127.0.0.1:8000"],
            wrapped,
        )

    assert return_code == 0
    assert output.getvalue() == (
        "[django] first child\n[django] second child\n"
    )
    assert factory.call_count == 2
    for call in factory.call_args_list:
        assert call.kwargs["env"]["RUN_MAIN"] == "true"
        assert call.kwargs["env"]["PYTHONUNBUFFERED"] == "1"


def test_django_output_forwards_a_flushed_prompt_before_eof() -> None:
    class PromptStream:
        def __init__(self) -> None:
            self.chunks = iter("(Pdb) ")
            self.output: StringIO | None = None
            self.wrapper: OutputWrapper | None = None

        def read(self, size: int = -1) -> str:
            try:
                chunk = next(self.chunks)
            except StopIteration:
                return ""
            if chunk == " ":
                assert self.output is not None
                assert self.output.getvalue() == "[django] (Pdb)"
                assert self.wrapper is not None
                self.wrapper.flush.assert_called()
            return chunk

    output = StringIO()
    stream = PromptStream()
    stream.output = output
    wrapper = Mock(wraps=OutputWrapper(output))
    stream.wrapper = wrapper

    _forward_django_output(stream, wrapper)

    assert output.getvalue() == "[django] (Pdb) "


def test_django_output_decodes_split_utf8_chunks() -> None:
    class BinaryChunks:
        def __init__(self) -> None:
            self.chunks = iter((b"\xe2", b"\x82", b"\xac\nready", b""))

        def read1(self, size: int = -1) -> bytes:
            return next(self.chunks)

    output = StringIO()

    _forward_django_output(BinaryChunks(), OutputWrapper(output))

    assert output.getvalue() == "[django] €\n[django] ready"


def test_django_reloader_restores_sigterm_handler(monkeypatch) -> None:
    previous = Mock()
    current = previous

    def get_handler(_signal):
        return current

    def set_handler(_signal, handler):
        nonlocal current
        current = handler

    monkeypatch.setattr(signal, "getsignal", get_handler)
    monkeypatch.setattr(signal, "signal", set_handler)
    monkeypatch.setattr(
        "hyperdjango.management.commands.hyper_runserver."
        "_restart_django_with_reloader",
        lambda child_args, output: 0,
    )

    with pytest.raises(SystemExit, match="0"):
        _run_django_reloader([], StringIO())

    assert current is previous


def test_django_reloader_sigterm_handler_always_exits(monkeypatch) -> None:
    previous = Mock()
    current = previous

    def get_handler(_signal):
        return current

    def set_handler(_signal, handler):
        nonlocal current
        current = handler

    def trigger_sigterm(child_args, output):
        current(signal.SIGTERM, None)

    monkeypatch.setattr(signal, "getsignal", get_handler)
    monkeypatch.setattr(signal, "signal", set_handler)
    monkeypatch.setattr(
        "hyperdjango.management.commands.hyper_runserver."
        "_restart_django_with_reloader",
        trigger_sigterm,
    )

    with pytest.raises(SystemExit, match="0"):
        _run_django_reloader([], StringIO())

    previous.assert_not_called()
    assert current is previous


def test_autoreload_survives_custom_command_disappearing(tmp_path: Path) -> None:
    """Simulate a package manager replacing HyperDjango during a reload."""
    raceapp = tmp_path / "raceapp"
    commands = raceapp / "management" / "commands"
    commands.mkdir(parents=True)
    for package in (raceapp, raceapp / "management", commands):
        (package / "__init__.py").write_text("")
    command_file = commands / "hyper_runserver.py"
    command_file.write_text(
        """
import sys
from pathlib import Path

from hyperdjango.management.commands.hyper_runserver import Command as HyperCommand


class Command(HyperCommand):
    def _run_django(self, **options):
        command_file = Path(__file__)
        command_file.rename(command_file.with_suffix(".gone"))
        sys.argv.append("--help")
        try:
            return super()._run_django(**options)
        finally:
            sys.argv.pop()
""".lstrip()
    )
    (tmp_path / "settings.py").write_text(
        """
SECRET_KEY = "test"
DEBUG = True
ALLOWED_HOSTS = ["*"]
ROOT_URLCONF = "urls"
INSTALLED_APPS = ["raceapp"]
MIDDLEWARE = []
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
""".lstrip()
    )
    (tmp_path / "urls.py").write_text("urlpatterns = []\n")
    manage = tmp_path / "manage.py"
    manage.write_text(
        """
import os
import sys

from django.core.management import execute_from_command_line

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
execute_from_command_line(sys.argv)
""".lstrip()
    )
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "settings",
        "PYTHONPATH": os.pathsep.join(
            filter(None, (str(tmp_path), os.environ.get("PYTHONPATH")))
        ),
    }
    env.pop("RUN_MAIN", None)
    env.pop("HYPER_DJANGO_RUNSERVER_SUPERVISED", None)
    env.pop("HYPER_DJANGO_DEV_SERVER_PORT", None)

    completed = subprocess.run(
        [
            sys.executable,
            str(manage),
            "hyper_runserver",
            "--no-vite",
            "--skip-checks",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Unknown command" not in completed.stdout + completed.stderr
    assert "usage:" in completed.stdout
    assert command_file.with_suffix(".gone").is_file()


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


def test_supervised_runserver_child_enriches_request_log_without_prefix() -> None:
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

    enriched = SupervisedRequestLogFilter().filter(record)

    assert enriched is not record
    assert enriched.getMessage().startswith('"GET / HTTP/1.1" 200 42 · 12.3 ms')
    assert "/__hyperdebug__/requests/abc/" in enriched.getMessage()
    assert not enriched.getMessage().startswith("[django]")


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
