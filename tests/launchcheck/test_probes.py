import os
import platform
import sys
from pathlib import Path

import pytest

from launchcheck import probes
from tests.launchcheck.conftest import make_fake_java


def test_os_info_names_the_system():
    text = probes.os_info()
    assert ("Windows" in text) or (platform.system() in text)
    assert platform.machine() in text


def test_memory_gb_is_positive_or_unknown():
    value = probes.memory_gb()
    assert value is None or value > 0


def test_cpu_count_positive():
    assert probes.cpu_count() >= 1


def test_free_disk_gb_positive(tmp_path):
    assert probes.free_disk_gb(tmp_path) > 0


def test_write_test_true_in_writable_dir(tmp_path):
    assert probes.write_test(tmp_path) is True
    assert list(tmp_path.iterdir()) == []  # временный файл удалён


@pytest.mark.skipif(sys.platform == "win32" or os.geteuid() == 0, reason="права каталога не действуют")
def test_write_test_false_in_readonly_dir(tmp_path):
    tmp_path.chmod(0o500)
    try:
        assert probes.write_test(tmp_path) is False
    finally:
        tmp_path.chmod(0o700)


@pytest.mark.skipif(sys.platform == "win32", reason="на Windows тип диска настоящий")
def test_drive_kind_outside_windows(tmp_path):
    assert probes.drive_kind(tmp_path) == "не Windows"


def test_java_version_missing_file(tmp_path):
    ok, text = probes.java_version(tmp_path / "java")
    assert ok is False
    assert text.startswith("файл не найден")


def test_java_version_ok(tmp_path):
    ok, text = probes.java_version(make_fake_java(tmp_path))
    assert ok is True
    assert text == 'openjdk version "21.0.12.1"'


def test_java_version_nonzero_exit(tmp_path):
    ok, text = probes.java_version(make_fake_java(tmp_path, exit_code=3))
    assert ok is False
    assert "21.0.12.1" in text


def test_java_version_timeout(tmp_path):
    ok, text = probes.java_version(make_fake_java(tmp_path, sleep=3), timeout=0.5)
    assert ok is False
    assert text == "не ответила за 0.5 с"


def test_qt_version_is_pyside_version():
    import PySide6

    assert probes.qt_version() == PySide6.__version__


def test_app_dir_from_sources_is_cwd():
    assert probes.app_dir() == Path.cwd()


def test_default_java_path(tmp_path):
    expected = tmp_path / "java" / "bin" / ("java.exe" if sys.platform == "win32" else "java")
    assert probes.default_java(tmp_path) == expected
