import sys
from pathlib import Path

import pytest

from launchcheck import __version__, report
from tests.launchcheck.conftest import make_fake_java


def sample(java_ok=True):
    return {
        "версия": "0.1.0",
        "время": "15.09.2026 12:00",
        "папка": "E:\\Проверка_запуска",
        "система": "Windows 10.0 сборка 19045 (AMD64)",
        "память_гб": 7.9,
        "процессоры": 4,
        "диск": "съёмный (флешка)",
        "свободно_гб": 12.3,
        "запись": True,
        "qt": "6.11.2",
        "java_ok": java_ok,
        "java": 'openjdk version "21.0.12.1"' if java_ok else "файл не найден: E:\\java\\bin\\java.exe",
        "java_путь": "E:\\Проверка_запуска\\java\\bin\\java.exe",
    }


def test_build_report_lists_every_value():
    text = report.build_report(sample())
    for piece in ["0.1.0", "15.09.2026 12:00", "E:\\Проверка_запуска", "сборка 19045", "7.9 ГБ", "4",
                  "съёмный (флешка)", "12.3 ГБ", "Запись в папку программы: да", "Qt: 6.11.2",
                  'Java: OK — openjdk version "21.0.12.1"']:
        assert piece in text
    assert text.rstrip().splitlines()[-1] == report.OK_LINE


def test_build_report_failure_summary():
    text = report.build_report(sample(java_ok=False))
    assert "Java: ОШИБКА — файл не найден" in text
    assert text.rstrip().splitlines()[-1] == "ИТОГ: Java не запустилась — пришлите этот отчёт автору"


def test_build_report_unknown_memory():
    data = sample()
    data["память_гб"] = None
    assert "Память: неизвестно" in report.build_report(data)


def test_run_all_with_fake_java(tmp_path):
    results = report.run_all(tmp_path, java_exe=make_fake_java(tmp_path))
    assert results["версия"] == __version__
    assert results["java_ok"] is True
    assert results["папка"] == str(tmp_path)
    assert results["запись"] is True
    assert set(results) == {"версия", "время", "папка", "система", "память_гб", "процессоры", "диск",
                            "свободно_гб", "запись", "qt", "java_ok", "java", "java_путь"}


def test_run_all_default_java_path(tmp_path):
    results = report.run_all(tmp_path)
    assert results["java_путь"] == str(tmp_path / "java" / "bin" / ("java.exe" if sys.platform == "win32" else "java"))
    assert results["java_ok"] is False


def test_save_report_writes_utf8_bom(tmp_path):
    path = report.save_report("Проверка\n", tmp_path)
    assert path == tmp_path / report.REPORT_NAME
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert path.read_text(encoding="utf-8-sig") == "Проверка\n"


def test_save_report_falls_back_to_desktop(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / "Desktop").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    path = report.save_report("x", tmp_path / "нет-такой-папки")
    assert path == home / "Desktop" / report.REPORT_NAME


def test_save_report_raises_when_nowhere(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "нет-дома"))
    with pytest.raises(OSError):
        report.save_report("x", tmp_path / "нет-такой-папки")
