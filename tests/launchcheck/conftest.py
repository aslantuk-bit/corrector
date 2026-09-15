import sys
from pathlib import Path


def make_fake_java(directory: Path, exit_code: int = 0, sleep: float = 0) -> Path:
    """Поддельная java: печатает строку версии в stderr, как настоящая, и выходит с нужным кодом."""
    if sys.platform == "win32":
        path = directory / "java.bat"
        wait = f"ping -n {int(sleep) + 1} 127.0.0.1 >nul\r\n" if sleep else ""  # timeout не работает без консоли
        path.write_text(
            "@echo off\r\n" + wait + '>&2 echo openjdk version "21.0.12.1"\r\n' + f"exit /b {exit_code}\r\n"
        )
    else:
        path = directory / "java"
        path.write_text(
            f"#!/bin/sh\nsleep {sleep}\necho 'openjdk version \"21.0.12.1\"' >&2\nexit {exit_code}\n"
        )
        path.chmod(0o755)
    return path
