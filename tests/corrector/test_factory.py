from corrector.core.userdict import UserDictionary
from corrector.engines import factory


def test_no_lt_uses_spell_engines(tmp_path):
    engines = factory.build_engines(UserDictionary(tmp_path / "словарь.txt"), no_lt=True)
    try:
        assert engines.ru.name == "ru_spell" and engines.kk.name == "kk_spell"
        assert engines.server is None
        names = {s.name: s.available for s in engines.statuses()}
        assert names["kk_spell"] and names["ru_spell"]
        assert "lt" in names and names["lt"] is False
    finally:
        engines.close()


def test_missing_java_falls_back_with_note(tmp_path):
    engines = factory.build_engines(UserDictionary(tmp_path / "словарь.txt"), java_home=tmp_path / "нет-java", lt_home=tmp_path / "нет-lt")
    try:
        assert engines.ru.name == "ru_spell"
        assert any("Java" in note or "LanguageTool" in note for note in engines.notes)
    finally:
        engines.close()


def test_lt_config_prefers_copy_inside_languagetool_dir(tmp_path):
    data = tmp_path / "data" / "lt"
    data.mkdir(parents=True)
    (data / "lt.properties").write_text("a=1", encoding="utf-8")
    lt_dir = tmp_path / "languagetool"
    lt_dir.mkdir()
    assert factory.lt_config_path(lt_dir, tmp_path / "data") == data / "lt.properties"
    (lt_dir / "lt.properties").write_text("a=1", encoding="utf-8")
    assert factory.lt_config_path(lt_dir, tmp_path / "data") == lt_dir / "lt.properties"
