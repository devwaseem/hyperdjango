from __future__ import annotations

import atexit
import codecs
import copy
import logging
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, TextIO

from django.apps import apps
from django.conf import settings
from django.contrib.staticfiles.management.commands.runserver import (
    Command as StaticRunserverCommand,
)
from django.core.management.base import CommandError
from django.core.management.commands.runserver import Command as DjangoRunserverCommand
from django.utils import autoreload

from hyperdjango.integrations.devtools.request_logging import (
    SUPERVISED_RUNSERVER_ENV,
    enrich_request_log_record,
)


VITE_URL_ENV = "HYPER_VITE_DEV_SERVER_URL"
DJANGO_PORT_ENV = "HYPER_DJANGO_DEV_SERVER_PORT"
ANSI_ESCAPE_RE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
VITE_LOCAL_URL_RE = re.compile(r"(?:Local:\s+)(https?://[^\s]+)")
VITE_STARTUP_LINES = ("VITE v", "Local:", "Network:", "press h + enter")
HYPER_BOOLEAN_OPTIONS = frozenset(
    ("--no-vite", "--auto-port", "--open", "--verbose")
)
HYPER_VALUE_OPTIONS = frozenset(
    (
        "--vite-host",
        "--vite-public-host",
        "--vite-port",
        "--vite-timeout",
        "--package-manager",
    )
)
DJANGO_VALUE_OPTIONS = frozenset(("--verbosity", "-v", "--settings", "--pythonpath"))
STATICFILES_OPTIONS = frozenset(("--nostatic", "--insecure"))


class Command(StaticRunserverCommand):
    help = "Start the Django development server and a project-local Vite server"

    def create_parser(
        self, prog_name: str, subcommand: str, **kwargs: Any
    ) -> Any:
        # The reload child receives only Django's built-in options. Disallow
        # argparse abbreviations so every HyperDjango-only option can be
        # removed from that child command without guessing what it meant.
        kwargs.setdefault("allow_abbrev", False)
        return super().create_parser(prog_name, subcommand, **kwargs)

    def add_arguments(self, parser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "--no-vite",
            action="store_true",
            help="Start Django without starting Vite",
        )
        parser.add_argument(
            "--vite-host",
            default=None,
            help="Host for Vite (default: use the Django server host)",
        )
        parser.add_argument(
            "--vite-public-host",
            default=None,
            help="Browser-facing Vite hostname for LAN, containers, or remote dev",
        )
        parser.add_argument(
            "--vite-port",
            type=int,
            default=0,
            help="Port for Vite; 0 selects an available port (default: 0)",
        )
        parser.add_argument(
            "--vite-timeout",
            type=float,
            default=15.0,
            help="Seconds to wait for Vite readiness (default: 15)",
        )
        parser.add_argument(
            "--package-manager",
            choices=("npm", "pnpm", "yarn", "bun"),
            default=None,
            help="Override package-manager auto-detection",
        )
        parser.add_argument(
            "--auto-port",
            action="store_true",
            help="Select an available Django port as well as a Vite port",
        )
        parser.add_argument(
            "--open",
            action="store_true",
            help="Open the Django URL when it becomes ready",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show unfiltered Vite startup output",
        )

    def get_handler(self, *args: Any, **options: Any):
        if not apps.is_installed("django.contrib.staticfiles"):
            return DjangoRunserverCommand.get_handler(self, *args, **options)
        return super().get_handler(*args, **options)

    def run(self, **options: Any) -> None:
        inherited_port = os.environ.get(DJANGO_PORT_ENV)
        if inherited_port:
            self.port = inherited_port
        elif options.get("auto_port"):
            self.port = str(_available_port(self.addr))
            os.environ[DJANGO_PORT_ENV] = self.port
        if options.get("no_vite"):
            if options.get("open"):
                _open_when_ready(self.addr, int(self.port))
            self._run_django(**options)
            return

        # A process started by an older HyperDjango parent may still re-execute
        # this command. Do not start another Vite server in that child.
        if os.environ.get(autoreload.DJANGO_AUTORELOAD_ENV) == "true":
            self._run_django(**options)
            return

        host = _vite_host(options.get("vite_host"), self.addr)
        requested_port = int(options["vite_port"])
        if requested_port < 0 or requested_port > 65535:
            raise CommandError("--vite-port must be between 0 and 65535")

        cwd = Path(settings.BASE_DIR)
        launch = _vite_launch(cwd, options.get("package_manager"))
        port = requested_port
        command = [*launch.command, *_vite_server_args(host, port)]

        if launch.install_command and not (cwd / "package.json").is_file():
            raise CommandError(
                f"Vite package.json was not found in {cwd}. "
                "Set BASE_DIR to the frontend project or HYPER_VITE_COMMAND explicitly."
            )
        if shutil.which(command[0]) is None:
            raise CommandError(
                f"{launch.manager} was not found. Install it or pass "
                "--package-manager with an available package manager."
            )
        if launch.install_command and not (cwd / "node_modules").is_dir():
            raise CommandError(
                f"Frontend dependencies are not installed in {cwd}. "
                f"Run `{launch.install_command}` first."
            )

        previous_url = os.environ.get(VITE_URL_ENV)
        supervisor = _ViteSupervisor(
            command=command,
            cwd=cwd,
            output=self.stdout,
            verbose=bool(options.get("verbose")),
            strip_colors=bool(options.get("no_color")),
        )
        started_at = time.monotonic()
        try:
            supervisor.start()
            actual_port = supervisor.wait_until_ready(float(options["vite_timeout"]))
            public_host = options.get("vite_public_host") or host
            url = _vite_url(str(public_host), actual_port)
            os.environ[VITE_URL_ENV] = url
            elapsed_ms = round((time.monotonic() - started_at) * 1000)
            django_url = _server_url(_browser_host(self.addr), int(self.port))
            network_urls = _network_urls(self.addr, int(self.port))
            self.stdout.write(
                _startup_banner(
                    django_url,
                    url,
                    elapsed_ms=elapsed_ms,
                    package_manager=launch.manager,
                    network_urls=network_urls,
                ),
                self.style.SUCCESS,
            )
            if options.get("open"):
                _open_when_ready(self.addr, int(self.port), django_url)
            supervisor.interrupt_if_vite_exits()
            self._run_django(**options)
        finally:
            supervisor.stop()
            _restore_env(previous_url)

    def _run_django(self, **options: Any) -> None:
        stdout = self.stdout
        stderr = self.stderr
        log_filter = _DjangoLogPrefixFilter()
        loggers = _django_loggers()
        self.stdout = _PrefixedOutput(stdout, "django")
        self.stderr = _PrefixedOutput(stderr, "django")
        for logger in loggers:
            logger.addFilter(log_filter)
        try:
            if options.get("use_reloader") and not _is_autoreload_child():
                child_args = _django_child_arguments(
                    sys.argv,
                    addr=self.addr,
                    port=int(self.port),
                    original_addrport=options.get("addrport"),
                    use_staticfiles=apps.is_installed("django.contrib.staticfiles"),
                )
                child_args = _preserve_child_color(
                    child_args,
                    output=stdout,
                    no_color=bool(options.get("no_color")),
                    force_color=bool(options.get("force_color")),
                )
                _run_django_reloader(child_args, stdout)
            else:
                super().run(**options)
        finally:
            for logger in loggers:
                logger.removeFilter(log_filter)
            self.stdout = stdout
            self.stderr = stderr


class _PrefixedOutput:
    def __init__(self, output: Any, prefix: str) -> None:
        self.output = output
        self.prefix = f"[{prefix}] "

    def __getattr__(self, name: str) -> Any:
        return getattr(self.output, name)

    def write(
        self,
        message: str = "",
        style_func: Any = None,
        ending: str | None = None,
    ) -> None:
        actual_ending = self.output.ending if ending is None else ending
        if actual_ending and not message.endswith(actual_ending):
            message += actual_ending
        prefixed = "".join(
            f"{self.prefix}{line}" if line.strip() else line
            for line in message.splitlines(keepends=True)
        )
        self.output.write(prefixed, style_func=style_func, ending="")


class _DjangoLogPrefixFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> logging.LogRecord:
        if not record.name.startswith("django"):
            return record
        if record.name == "django.server":
            record = enrich_request_log_record(record)
        prefixed_record = copy.copy(record)
        prefixed_record.msg = f"[django] {record.msg}"
        return prefixed_record


def _django_loggers() -> tuple[logging.Logger, ...]:
    return (
        logging.getLogger("django.server"),
        logging.getLogger("django.utils.autoreload"),
    )


@dataclass(frozen=True)
class _ViteLaunch:
    manager: str
    command: list[str]
    install_command: str | None


PACKAGE_MANAGERS = {
    "npm": _ViteLaunch("npm", ["npm", "run", "--silent", "dev", "--"], "npm install"),
    "pnpm": _ViteLaunch("pnpm", ["pnpm", "run", "dev", "--"], "pnpm install"),
    "yarn": _ViteLaunch("yarn", ["yarn", "dev"], "yarn install"),
    "bun": _ViteLaunch("bun", ["bun", "run", "dev", "--"], "bun install"),
}
LOCKFILE_MANAGERS = (
    ("bun.lock", "bun"),
    ("bun.lockb", "bun"),
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("package-lock.json", "npm"),
)


def _vite_launch(cwd: Path, requested_manager: str | None = None) -> _ViteLaunch:
    configured = getattr(settings, "HYPER_VITE_COMMAND", None)
    if configured is not None:
        command = _split_command(configured)
        return _ViteLaunch(command[0], command, None)

    manager = requested_manager
    if manager is None:
        manager = next(
            (name for lockfile, name in LOCKFILE_MANAGERS if (cwd / lockfile).is_file()),
            "npm",
        )
    return PACKAGE_MANAGERS[manager]


def _split_command(configured: Any) -> list[str]:
    if isinstance(configured, str):
        command = shlex.split(configured)
    else:
        command = [str(part) for part in configured]
    if not command:
        raise CommandError("HYPER_VITE_COMMAND cannot be empty")
    return command


def _vite_command() -> list[str]:
    """Backward-compatible helper used by integrations and tests."""
    return _vite_launch(Path.cwd()).command


class _ViteSupervisor:
    def __init__(
        self,
        *,
        command: list[str],
        cwd: Path,
        output: Any,
        verbose: bool = False,
        strip_colors: bool = False,
    ) -> None:
        self.command = command
        self.cwd = cwd
        self.output = output
        self.verbose = verbose
        self.strip_colors = strip_colors
        self.process: subprocess.Popen[str] | None = None
        self.output_thread: threading.Thread | None = None
        self.ready = threading.Event()
        self.stopping = threading.Event()
        self.actual_port: int | None = None
        self.recent_output: deque[str] = deque(maxlen=40)
        self._watchdog: threading.Thread | None = None
        self._previous_sigterm: Any = None
        self._sigterm_handler: Any = None

    def start(self) -> None:
        popen_options: dict[str, Any] = {}
        if os.name == "posix":
            popen_options["start_new_session"] = True
        elif os.name == "nt":  # pragma: no cover - exercised on Windows CI
            popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            self.process = subprocess.Popen(
                self.command,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                **popen_options,
            )
        except OSError as exc:
            raise CommandError(f"Could not start Vite: {exc}") from exc
        self.output_thread = threading.Thread(
            target=self._read_output,
            name="hyperdjango-vite-output",
            daemon=True,
        )
        self.output_thread.start()
        atexit.register(self.stop)
        if threading.current_thread() is threading.main_thread():
            self._previous_sigterm = signal.getsignal(signal.SIGTERM)

            def handle_sigterm(signum: int, frame: Any) -> None:
                self.stop()
                if callable(self._previous_sigterm):
                    self._previous_sigterm(signum, frame)
                    return
                raise SystemExit(128 + signum)

            self._sigterm_handler = handle_sigterm
            signal.signal(signal.SIGTERM, handle_sigterm)

    def _read_output(self) -> None:
        if self.process is None or self.process.stdout is None:
            return
        for line in self.process.stdout:
            message = line.rstrip("\r\n")
            if not message:
                continue
            self.recent_output.append(message)
            plain = ANSI_ESCAPE_RE.sub("", message)
            match = VITE_LOCAL_URL_RE.search(plain)
            if match:
                try:
                    self.actual_port = int(match.group(1).rstrip("/").rsplit(":", 1)[1])
                except (IndexError, ValueError):
                    pass
                else:
                    self.ready.set()
            if self.verbose or (self.ready.is_set() and not _vite_startup_line(plain)):
                shown = plain if self.strip_colors else message
                self.output.write(f"[vite] {shown}\n")

    def wait_until_ready(self, timeout: float) -> int:
        if timeout <= 0:
            raise CommandError("--vite-timeout must be greater than zero")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.ready.wait(timeout=0.05) and self.actual_port is not None:
                return self.actual_port
            return_code = self.process.poll() if self.process else -1
            if return_code is not None:
                raise CommandError(self._failure_message(f"Vite exited with code {return_code}"))
        raise CommandError(
            self._failure_message(f"Vite did not become ready within {timeout:g} seconds")
        )

    def _failure_message(self, reason: str) -> str:
        details = "\n".join(ANSI_ESCAPE_RE.sub("", line) for line in self.recent_output)
        return f"{reason}." + (f"\n\nRecent Vite output:\n{details}" if details else "")

    def interrupt_if_vite_exits(self) -> None:
        if self.process is None:
            return

        def watch() -> None:
            return_code = self.process.wait()
            if not self.stopping.is_set():
                self.output.write(
                    f"[vite] Vite exited unexpectedly with code {return_code}. "
                    "Stopping Django.\n"
                )
                os.kill(os.getpid(), signal.SIGINT)

        self._watchdog = threading.Thread(
            target=watch,
            name="hyperdjango-vite-watchdog",
            daemon=True,
        )
        self._watchdog.start()

    def stop(self) -> None:
        if self.stopping.is_set():
            return
        self.stopping.set()
        if self.process is not None:
            _stop_process(self.process)
        if self.output_thread is not None:
            self.output_thread.join(timeout=1)
        try:
            atexit.unregister(self.stop)
        except Exception:  # pragma: no cover - interpreter shutdown edge case
            pass
        if (
            self._sigterm_handler is not None
            and threading.current_thread() is threading.main_thread()
            and signal.getsignal(signal.SIGTERM) is self._sigterm_handler
        ):
            signal.signal(signal.SIGTERM, self._previous_sigterm)


def _vite_startup_line(message: str) -> bool:
    stripped = message.strip()
    return any(fragment in stripped for fragment in VITE_STARTUP_LINES)


def _vite_host(configured_host: Any, django_host: str) -> str:
    return str(configured_host or django_host or "127.0.0.1")


def _vite_server_args(host: str, port: int) -> list[str]:
    args = ["--host", host]
    if port:
        args.extend(("--port", str(port), "--strictPort"))
    args.append("--no-clearScreen")
    return args


def _server_url(host: str, port: int) -> str:
    url_host = host
    if ":" in url_host and not url_host.startswith("["):
        url_host = f"[{url_host}]"
    return f"http://{url_host}:{port}/"


def _startup_banner(
    django_url: str,
    vite_url: str,
    *,
    elapsed_ms: int | None = None,
    package_manager: str | None = None,
    network_urls: list[str] | None = None,
) -> str:
    manager = f" via {package_manager}" if package_manager else ""
    lines = ["HyperDjango development server"]
    if elapsed_ms is not None:
        lines.append(f"  Ready    Vite in {elapsed_ms} ms")
    lines.extend((f"  Local    {django_url}", f"  Vite     {vite_url}{manager}"))
    lines.extend(f"  Network  {url}" for url in network_urls or [])
    return "\n".join(lines) + "\n\n"


def _browser_host(host: str) -> str:
    return "localhost" if host in {"0.0.0.0", "::"} else host


def _network_urls(host: str, port: int) -> list[str]:
    if host not in {"0.0.0.0", "::"}:
        return []
    addresses: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            address = str(info[4][0])
            if not address.startswith(("127.", "169.254.")) and address != "::1":
                addresses.add(address.split("%", 1)[0])
    except OSError:
        return []
    return [_server_url(address, port) for address in sorted(addresses)]


def _open_when_ready(host: str, port: int, url: str | None = None) -> None:
    connect_host = _browser_host(host)
    browser_url = url or _server_url(connect_host, port)

    def open_browser() -> None:
        deadline = time.monotonic() + 15
        family = socket.AF_INET6 if ":" in connect_host else socket.AF_INET
        while time.monotonic() < deadline:
            try:
                with socket.socket(family, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.2)
                    if sock.connect_ex((connect_host, port)) == 0:
                        webbrowser.open(browser_url)
                        return
            except OSError:
                pass
            time.sleep(0.1)

    threading.Thread(
        target=open_browser,
        name="hyperdjango-browser-open",
        daemon=True,
    ).start()


def _forward_vite_output(stream: TextIO | None, output: Any) -> None:
    if stream is None:
        return
    for line in stream:
        message = line.rstrip("\r\n")
        if message:
            output.write(f"[vite] {message}\n")


def _is_autoreload_child() -> bool:
    return os.environ.get(autoreload.DJANGO_AUTORELOAD_ENV) == "true"


def _django_child_arguments(
    argv: list[str],
    *,
    addr: str,
    port: int,
    original_addrport: Any = None,
    use_staticfiles: bool = True,
) -> list[str]:
    django_argv = _django_runserver_argv(
        argv,
        addr=addr,
        port=port,
        original_addrport=original_addrport,
        use_staticfiles=use_staticfiles,
    )
    previous_argv = sys.argv
    try:
        sys.argv = django_argv
        return autoreload.get_child_arguments()
    finally:
        sys.argv = previous_argv


def _django_runserver_argv(
    argv: list[str],
    *,
    addr: str,
    port: int,
    original_addrport: Any = None,
    use_staticfiles: bool = True,
) -> list[str]:
    """Translate a hyper_runserver invocation into a built-in runserver one."""
    if len(argv) < 2:
        raise CommandError("Could not construct the Django autoreload command")

    translated = [argv[0], "runserver"]
    original_addrport = (
        str(original_addrport) if original_addrport is not None else None
    )
    index = 2
    while index < len(argv):
        argument = argv[index]
        if argument in HYPER_BOOLEAN_OPTIONS:
            index += 1
            continue
        if argument in HYPER_VALUE_OPTIONS:
            index += 2
            continue
        if any(argument.startswith(f"{option}=") for option in HYPER_VALUE_OPTIONS):
            index += 1
            continue
        if not use_staticfiles and argument in STATICFILES_OPTIONS:
            index += 1
            continue
        if argument in DJANGO_VALUE_OPTIONS and index + 1 < len(argv):
            translated.extend((argument, argv[index + 1]))
            index += 2
            continue
        if original_addrport is not None and argument == original_addrport:
            index += 1
            continue
        translated.append(argument)
        index += 1

    translated.append(_server_addrport(addr, port))
    return translated


def _server_addrport(addr: str, port: int) -> str:
    shown_addr = f"[{addr}]" if ":" in addr and not addr.startswith("[") else addr
    return f"{shown_addr}:{port}"


def _preserve_child_color(
    child_args: list[str],
    *,
    output: Any,
    no_color: bool,
    force_color: bool,
) -> list[str]:
    isatty = getattr(output, "isatty", None)
    if (
        not no_color
        and not force_color
        and callable(isatty)
        and bool(isatty())
    ):
        color_args = list(child_args)
        try:
            separator = color_args.index("--")
        except ValueError:
            color_args.append("--force-color")
        else:
            color_args.insert(separator, "--force-color")
        return color_args
    return child_args


def _run_django_reloader(child_args: list[str], output: Any) -> None:
    # Match Django's parent-reloader signal behavior while keeping this process
    # alive as the Vite and output supervisor.
    previous_sigterm = signal.getsignal(signal.SIGTERM)

    def handle_sigterm(_signum: int, _frame: Any) -> None:
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)
    try:
        return_code = _restart_django_with_reloader(child_args, output)
        raise SystemExit(return_code)
    except KeyboardInterrupt:
        pass
    finally:
        if signal.getsignal(signal.SIGTERM) is handle_sigterm:
            signal.signal(signal.SIGTERM, previous_sigterm)


def _restart_django_with_reloader(child_args: list[str], output: Any) -> int:
    child_env = {
        **os.environ,
        autoreload.DJANGO_AUTORELOAD_ENV: "true",
        SUPERVISED_RUNSERVER_ENV: "true",
    }
    # Python uses block buffering when stdout is piped. Force prompt output so
    # startup messages and request logs remain useful in the unified terminal.
    child_env["PYTHONUNBUFFERED"] = "1"

    while True:
        popen_options: dict[str, Any] = {}
        if os.name == "posix":
            popen_options["start_new_session"] = True
        elif os.name == "nt":  # pragma: no cover - exercised on Windows CI
            popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            process = subprocess.Popen(
                child_args,
                env=child_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                **popen_options,
            )
        except OSError as exc:
            raise CommandError(f"Could not start Django: {exc}") from exc

        try:
            _forward_django_output(process.stdout, output)
            return_code = process.wait()
        finally:
            if process.poll() is None:
                _stop_process(process)
        if return_code != 3:
            return return_code


def _forward_django_output(stream: BinaryIO | TextIO | None, output: Any) -> None:
    if stream is None:
        return
    prefix = "[django] "
    at_line_start = True
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")

    def forward(chunk: str) -> None:
        nonlocal at_line_start
        rendered: list[str] = []
        for character in chunk:
            if at_line_start and character not in "\r\n":
                rendered.append(prefix)
                at_line_start = False
            rendered.append(character)
            if character in "\r\n":
                at_line_start = True
        if rendered:
            output.write("".join(rendered), ending="")
            output.flush()

    read1 = getattr(stream, "read1", None)
    if callable(read1):
        while chunk := read1(4096):
            forward(decoder.decode(chunk) if isinstance(chunk, bytes) else chunk)
        forward(decoder.decode(b"", final=True))
        return

    while True:
        chunk = stream.read(1)
        if not chunk:
            break
        forward(decoder.decode(chunk) if isinstance(chunk, bytes) else chunk)
    forward(decoder.decode(b"", final=True))


def _available_port(host: str) -> int:
    try:
        family = socket.AF_INET6 if ":" in host else socket.AF_INET
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])
    except OSError as exc:
        raise CommandError(f"Could not select a Vite port on {host}: {exc}") from exc


def _vite_url(host: str, port: int) -> str:
    url_host = "localhost" if host in {"0.0.0.0", "::"} else host
    if ":" in url_host and not url_host.startswith("["):
        url_host = f"[{url_host}]"
    return f"http://{url_host}:{port}/"


def _stop_process(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
    else:  # pragma: no cover - exercised on Windows CI
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:  # pragma: no cover - exercised on Windows CI
            process.kill()
        process.wait()


def _restore_env(previous_url: str | None) -> None:
    if previous_url is None:
        os.environ.pop(VITE_URL_ENV, None)
    else:
        os.environ[VITE_URL_ENV] = previous_url
