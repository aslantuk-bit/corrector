from pathlib import Path

from corrector.core import javaenv


def make_tree(root: Path, files: dict[str, str]) -> Path:
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


def test_path_fits_code_page():
    assert javaenv.path_fits_code_page(Path("C:/Корректор/java"), "cp1252") is False
    assert javaenv.path_fits_code_page(Path("C:/Корректор/java"), "cp1251") is True
    assert javaenv.path_fits_code_page(Path("C:/Users/Әсел/java"), "cp1251") is False
    assert javaenv.path_fits_code_page(Path("C:/plain"), None) is True


def test_copy_java_goes_to_jre_subfolder(tmp_path):
    src = make_tree(tmp_path / "Корректор" / "java", {"bin/java": "j", "release": "JAVA_VERSION=21"})
    (tmp_path / "public").mkdir()
    target, note = javaenv.copy_to_safe_dir(src, "java", fallback_roots=[tmp_path / "public"])
    assert target == tmp_path / "public" / "corrector-java" / "jre"
    assert (target / "bin" / "java").read_text() == "j"
    assert note == f"копия в {target}"


def test_copy_languagetool_goes_to_named_folder(tmp_path):
    src = make_tree(tmp_path / "Корректор" / "languagetool", {"languagetool-server.jar": "x", "libs/a.jar": "y"})
    (tmp_path / "public").mkdir()
    target, note = javaenv.copy_to_safe_dir(src, "languagetool", fallback_roots=[tmp_path / "public"])
    assert target == tmp_path / "public" / "corrector-languagetool" / "languagetool"
    assert (target / "libs" / "a.jar").read_text() == "y"
    assert (target / ".corrector-copy").exists()


def test_copy_skipped_when_marker_matches(tmp_path):
    src = make_tree(tmp_path / "Корректор" / "languagetool", {"languagetool-server.jar": "x"})
    (tmp_path / "public").mkdir()
    target, _ = javaenv.copy_to_safe_dir(src, "languagetool", fallback_roots=[tmp_path / "public"])
    (target / "languagetool-server.jar").write_text("уже есть", encoding="utf-8")
    target2, note = javaenv.copy_to_safe_dir(src, "languagetool", fallback_roots=[tmp_path / "public"])
    assert target2 == target
    assert (target / "languagetool-server.jar").read_text(encoding="utf-8") == "уже есть"
    assert note.endswith("(уже была)")


def test_copy_redone_when_source_changed(tmp_path):
    src = make_tree(tmp_path / "Корректор" / "languagetool", {"languagetool-server.jar": "x"})
    (tmp_path / "public").mkdir()
    target, _ = javaenv.copy_to_safe_dir(src, "languagetool", fallback_roots=[tmp_path / "public"])
    (src / "libs").mkdir()
    (src / "libs" / "new.jar").write_text("n", encoding="utf-8")
    javaenv.copy_to_safe_dir(src, "languagetool", fallback_roots=[tmp_path / "public"])
    assert (target / "libs" / "new.jar").exists()


def test_safe_dir_returns_source_when_it_fits(tmp_path):
    src = make_tree(tmp_path / "Корректор" / "java", {"bin/java": "j"})
    assert javaenv.safe_dir(src, "java", encoding="cp1251", fallback_roots=[tmp_path]) == (src, "")


def test_safe_dir_copies_when_it_does_not_fit(tmp_path):
    src = make_tree(tmp_path / "Корректор" / "java", {"bin/java": "j"})
    (tmp_path / "public").mkdir()
    target, note = javaenv.safe_dir(src, "java", encoding="cp1252", fallback_roots=[tmp_path / "public"])
    assert target == tmp_path / "public" / "corrector-java" / "jre"
    assert note.startswith("копия в")


def test_safe_dir_reports_failure(tmp_path):
    src = make_tree(tmp_path / "Корректор" / "java", {"bin/java": "j"})
    target, note = javaenv.safe_dir(src, "java", encoding="cp1252", fallback_roots=[tmp_path / "нет"])
    assert target == src
    assert note.startswith("копия не удалась")
