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
