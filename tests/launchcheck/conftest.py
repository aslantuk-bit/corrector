import sys
from pathlib import Path


def make_fake_java(directory: Path, exit_code: int = 0, sleep: float = 0, path_sensitive: bool = False) -> Path:
    """Поддельная java: печатает строку версии в stderr, как настоящая, и выходит с нужным кодом.

    path_sensitive=True воспроизводит поведение настоящего запускателя Windows: если в собственном пути
    есть «Проверка», java «не находит java.dll» и выходит с кодом 1.
    """
    if sys.platform == "win32":
        path = directory / "java.bat"
        wait = f"ping -n {int(sleep) + 1} 127.0.0.1 >nul\r\n" if sleep else ""  # timeout не работает без консоли
        guard = ('echo %~dp0 | findstr /C:"Проверка" >nul && (>&2 echo Error: could not find java.dll & exit /b 1)\r\n'
                 if path_sensitive else "")
        path.write_text(
            "@echo off\r\n" + wait + guard + '>&2 echo openjdk version "21.0.12.1"\r\n' + f"exit /b {exit_code}\r\n",
            encoding="utf-8",
        )
    else:
        path = directory / "java"
        guard = ('case "$0" in *Проверка*) echo "Error: could not find java.dll" >&2; exit 1;; esac\n'
                 if path_sensitive else "")
        path.write_text(
            f"#!/bin/sh\nsleep {sleep}\n" + guard + "echo 'openjdk version \"21.0.12.1\"' >&2\n" + f"exit {exit_code}\n"
        )
        path.chmod(0o755)
    return path
