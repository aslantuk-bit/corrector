import sys
from pathlib import Path

from corrector.core import paths


def test_app_dir_is_repo_root_from_sources():
    assert (paths.app_dir() / "pyproject.toml").exists()


def test_data_dir_under_app_dir():
    assert paths.data_dir() == paths.app_dir() / "data"


def test_java_and_lt_overridden_by_env(monkeypatch, tmp_path):
    monkeypatch.setenv("CORRECTOR_JAVA", str(tmp_path / "j"))
    monkeypatch.setenv("CORRECTOR_LT", str(tmp_path / "lt"))
    assert paths.java_home() == tmp_path / "j"
    assert paths.lt_home() == tmp_path / "lt"
    assert paths.java_exe(tmp_path / "j") == tmp_path / "j" / "bin" / ("java.exe" if sys.platform == "win32" else "java")


def test_java_home_default_is_vendor_from_sources(monkeypatch):
    monkeypatch.delenv("CORRECTOR_JAVA", raising=False)
    assert paths.java_home().parent == paths.app_dir() / "vendor"


def test_user_dir_is_app_dir_when_writable(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "app_dir", lambda: tmp_path)
    assert paths.user_dir() == tmp_path


def test_user_dir_falls_back_when_not_writable(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "app_dir", lambda: tmp_path / "нет-такой-папки")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    result = paths.user_dir()
    assert result.is_dir()
    assert str(result).startswith(str(tmp_path))
