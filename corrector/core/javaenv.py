"""Обход ловушки запускателя Java на Windows: путь с символами вне кодовой страницы ANSI (JDK-8242283).

Если путь к папке не укладывается в кодовую страницу, папка копируется в первую подходящую папку
без таких символов, и Java (или LanguageTool) запускается оттуда.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import sys
import tempfile
from pathlib import Path

MARKER = ".corrector-copy"


def active_code_page() -> str | None:
    if sys.platform != "win32":
        return None
    acp = ctypes.windll.kernel32.GetACP()
    return "utf-8" if acp == 65001 else f"cp{acp}"


def path_fits_code_page(path: Path, encoding: str | None) -> bool:
    if encoding is None:
        return True
    try:
        str(path).encode(encoding)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


def default_fallback_roots() -> list[Path]:
    if sys.platform != "win32":
        return []
    roots = [
        os.environ.get("PUBLIC", r"C:\Users\Public"),
        os.environ.get("ProgramData", r"C:\ProgramData"),
        os.environ.get("SystemDrive", "C:") + r"\Temp",
        os.environ.get("TEMP", ""),
    ]
    return [Path(r) for r in roots if r]


def _writable(directory: Path) -> bool:
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix="~проверка-", delete=True):
            pass
        return True
    except OSError:
        return False


def _signature(source: Path) -> str:
    release = source / "release"
    if release.is_file():
        return release.read_text(encoding="utf-8", errors="replace")
    return "\n".join(sorted(p.name for p in source.iterdir()))


def _target_signature(target: Path) -> str | None:
    """Подпись имеющейся копии: её файл release (для Java) или метка копирования."""
    release = target / "release"
    if release.is_file():
        return release.read_text(encoding="utf-8", errors="replace")
    marker = target / MARKER
    if marker.is_file():
        return marker.read_text(encoding="utf-8", errors="replace")
    return None


def _target_for(root: Path, name: str) -> Path:
    return root / f"corrector-{name}" / ("jre" if name == "java" else name)


def copy_to_safe_dir(
    source: Path,
    name: str,
    encoding: str | None = None,
    fallback_roots: list[Path] | None = None,
) -> tuple[Path | None, str]:
    if not source.is_dir():
        return None, f"копия не удалась: нет исходной папки {source}"
    roots = default_fallback_roots() if fallback_roots is None else fallback_roots
    reasons = []
    signature = _signature(source)
    for root in roots:
        if not root.is_dir():
            reasons.append(f"{root}: нет папки")
            continue
        if not path_fits_code_page(root, encoding):
            reasons.append(f"{root}: символы вне кодовой страницы")
            continue
        if not _writable(root):
            reasons.append(f"{root}: нет записи")
            continue
        target = _target_for(root, name)
        marker = target / MARKER
        if _target_signature(target) == signature:
            return target, f"копия в {target} (уже была)"
        try:
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)
            marker.write_text(signature, encoding="utf-8")
        except OSError as error:
            reasons.append(f"{root}: {error}")
            continue
        return target, f"копия в {target}"
    return None, "копия не удалась: " + ("; ".join(reasons) if reasons else "нет подходящих папок")


def safe_dir(
    source: Path,
    name: str,
    encoding: str | None = None,
    fallback_roots: list[Path] | None = None,
) -> tuple[Path, str]:
    """Папка, из которой можно запускать Java: сама source, если её путь укладывается в кодовую страницу, иначе копия."""
    if path_fits_code_page(source, encoding):
        return source, ""
    target, note = copy_to_safe_dir(source, name, encoding, fallback_roots)
    return (target, note) if target is not None else (source, note)
