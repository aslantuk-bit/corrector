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


def test_path_fits_code_page():
    assert probes.path_fits_code_page(Path("C:/Проверка_запуска/java"), "cp1252") is False
    assert probes.path_fits_code_page(Path("C:/Проверка_запуска/java"), "cp1251") is True
    assert probes.path_fits_code_page(Path("C:/Users/Әсел/java"), "cp1251") is False
    assert probes.path_fits_code_page(Path("C:/plain/java"), "cp1252") is True
    assert probes.path_fits_code_page(Path("C:/Проверка"), None) is True


def make_java_dir(root: Path, name: str = "java") -> Path:
    java_dir = root / name
    (java_dir / "bin").mkdir(parents=True)
    (java_dir / "bin" / "java").write_bytes(b"java")
    (java_dir / "release").write_text("JAVA_VERSION=21\n")
    return java_dir


def test_copy_java_to_safe_dir_copies_into_first_writable_root(tmp_path):
    java_dir = make_java_dir(tmp_path / "Проверка_запуска")
    roots = [tmp_path / "нет-такой", tmp_path / "public"]
    (tmp_path / "public").mkdir()
    copy_dir, note = probes.copy_java_to_safe_dir(java_dir, fallback_roots=roots)
    assert copy_dir == tmp_path / "public" / "corrector-java" / "jre"
    assert (copy_dir / "bin" / "java").read_bytes() == b"java"
    assert note == f"копия в {copy_dir}"


def test_copy_java_to_safe_dir_reuses_existing_copy(tmp_path):
    java_dir = make_java_dir(tmp_path / "Проверка_запуска")
    roots = [tmp_path / "public"]
    (tmp_path / "public").mkdir()
    copy_dir, _ = probes.copy_java_to_safe_dir(java_dir, fallback_roots=roots)
    (copy_dir / "bin" / "java").write_bytes(b"already-there")
    copy_dir2, note = probes.copy_java_to_safe_dir(java_dir, fallback_roots=roots)
    assert copy_dir2 == copy_dir
    assert (copy_dir / "bin" / "java").read_bytes() == b"already-there"
    assert note == f"копия в {copy_dir} (уже была)"


def test_copy_java_to_safe_dir_recopies_when_release_differs(tmp_path):
    java_dir = make_java_dir(tmp_path / "Проверка_запуска")
    roots = [tmp_path / "public"]
    (tmp_path / "public").mkdir()
    copy_dir, _ = probes.copy_java_to_safe_dir(java_dir, fallback_roots=roots)
    (copy_dir / "release").write_text("JAVA_VERSION=17\n")
    (copy_dir / "bin" / "java").write_bytes(b"old")
    probes.copy_java_to_safe_dir(java_dir, fallback_roots=roots)
    assert (copy_dir / "bin" / "java").read_bytes() == b"java"


def test_copy_java_to_safe_dir_skips_roots_outside_code_page(tmp_path):
    java_dir = make_java_dir(tmp_path / "Проверка_запуска")
    cyr_root = tmp_path / "Общая"
    cyr_root.mkdir()
    ascii_root = tmp_path / "public"
    ascii_root.mkdir()
    copy_dir, _ = probes.copy_java_to_safe_dir(java_dir, encoding="cp1252", fallback_roots=[cyr_root, ascii_root])
    assert copy_dir == ascii_root / "corrector-java" / "jre"


def test_copy_java_to_safe_dir_without_roots(tmp_path):
    java_dir = make_java_dir(tmp_path / "Проверка_запуска")
    copy_dir, note = probes.copy_java_to_safe_dir(java_dir, fallback_roots=[])
    assert copy_dir is None
    assert note.startswith("копия не удалась")


def test_copy_java_to_safe_dir_missing_source(tmp_path):
    copy_dir, note = probes.copy_java_to_safe_dir(tmp_path / "нет", fallback_roots=[tmp_path])
    assert copy_dir is None
    assert "нет исходной папки" in note


@pytest.mark.skipif(sys.platform == "win32", reason="на Windows кодовая страница настоящая")
def test_active_code_page_outside_windows():
    assert probes.active_code_page() is None
