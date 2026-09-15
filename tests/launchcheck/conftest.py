import sys
from pathlib import Path


def make_fake_java(directory: Path, exit_code: int = 0, sleep: float = 0, fail_if_path_contains: str = "") -> Path:
    """Поддельная java: печатает строку версии в stderr, как настоящая, и выходит с нужным кодом.

    fail_if_path_contains воспроизводит поведение настоящего запускателя Windows: если в собственном пути
    есть эта латинская метка, java «не находит java.dll» и выходит с кодом 1. Метка латинская нарочно:
    cmd читает .bat в кодировке OEM и кириллицу в нём не узнаёт.
    """
    marker = fail_if_path_contains
    if sys.platform == "win32":
        path = directory / "java.bat"
        wait = f"ping -n {int(sleep) + 1} 127.0.0.1 >nul\r\n" if sleep else ""  # timeout не работает без консоли
        guard = (f'echo %~dp0 | findstr /C:"{marker}" >nul && (>&2 echo Error: could not find java.dll & exit /b 1)\r\n'
                 if marker else "")
        path.write_text(
            "@echo off\r\n" + wait + guard + '>&2 echo openjdk version "21.0.12.1"\r\n' + f"exit /b {exit_code}\r\n"
        )
    else:
        path = directory / "java"
        guard = (f'case "$0" in *{marker}*) echo "Error: could not find java.dll" >&2; exit 1;; esac\n'
                 if marker else "")
        path.write_text(
            f"#!/bin/sh\nsleep {sleep}\n" + guard + "echo 'openjdk version \"21.0.12.1\"' >&2\n" + f"exit {exit_code}\n"
        )
        path.chmod(0o755)
    return path
