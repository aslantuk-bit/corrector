"""Где что лежит: программа, данные, Java, LanguageTool, папка пользователя."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Корректор"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    return app_dir() / "data"


def java_home() -> Path:
    env = os.environ.get("CORRECTOR_JAVA")
    if env:
        return Path(env)
    if getattr(sys, "frozen", False):
        return app_dir() / "java"
    return app_dir() / "vendor" / ("jre-windows-x64" if sys.platform == "win32" else "jre-mac-aarch64")


def java_exe(home: Path | None = None) -> Path:
    home = home or java_home()
    return home / "bin" / ("java.exe" if sys.platform == "win32" else "java")


def lt_home() -> Path:
    env = os.environ.get("CORRECTOR_LT")
    if env:
        return Path(env)
    if getattr(sys, "frozen", False):
        return app_dir() / "languagetool"
    return app_dir() / "vendor" / "languagetool-ru"


def user_dir() -> Path:
    """Словарь, правила, настройки, журналы: рядом с программой, если туда можно писать, иначе папка пользователя."""
    base = app_dir()
    if _writable(base):
        return base
    if sys.platform == "win32":
        fallback = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / APP_NAME
    elif sys.platform == "darwin":
        fallback = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        fallback = Path.home() / ".config" / "corrector"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _writable(directory: Path) -> bool:
    probe = directory / ".~проверка-записи"
    try:
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False
