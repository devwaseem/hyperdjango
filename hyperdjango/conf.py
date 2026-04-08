from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_frontend_dir() -> Path:
    try:
        frontend_dir = getattr(settings, "HYPER_FRONTEND_DIR", "")
    except ImproperlyConfigured as exc:
        raise RuntimeError(
            "Django settings are not configured. Configure settings before using HyperDjango."
        ) from exc
    if not frontend_dir:
        raise RuntimeError(
            "HYPER_FRONTEND_DIR is not set in settings.py. "
            "Set it to your frontend directory (for example BASE_DIR / 'frontend')."
        )
    path = Path(frontend_dir)
    if not path.exists() or not path.is_dir():
        raise RuntimeError(f"HYPER_FRONTEND_DIR path is invalid: {path}")
    return path


def get_vite_output_dir() -> Path:
    try:
        output_dir = getattr(settings, "HYPER_VITE_OUTPUT_DIR", "")
    except ImproperlyConfigured as exc:
        raise RuntimeError(
            "Django settings are not configured. Configure settings before using HyperDjango."
        ) from exc
    if not output_dir:
        raise RuntimeError(
            "HYPER_VITE_OUTPUT_DIR is not set in settings.py. "
            "Set it to Vite build output directory (for example BASE_DIR / 'dist')."
        )
    path = Path(output_dir)
    if not path.exists() or not path.is_dir():
        raise RuntimeError(f"HYPER_VITE_OUTPUT_DIR path is invalid: {path}")
    return path


def is_dev_env() -> bool:
    try:
        return bool(getattr(settings, "HYPER_DEV", getattr(settings, "DEBUG", False)))
    except ImproperlyConfigured:
        return True


def get_vite_dev_server_url() -> str:
    try:
        return str(
            getattr(settings, "HYPER_VITE_DEV_SERVER_URL", "http://localhost:5173/")
        )
    except ImproperlyConfigured:
        return "http://localhost:5173/"


def get_append_slash() -> bool:
    try:
        return bool(getattr(settings, "APPEND_SLASH", True))
    except ImproperlyConfigured:
        return True
