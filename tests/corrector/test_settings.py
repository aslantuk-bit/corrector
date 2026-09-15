import json

from corrector.core.settings import FILE_NAME, Settings


def test_defaults():
    s = Settings()
    assert s.categories == {"spelling": True, "grammar": True, "punctuation": True, "typography": True, "style": True}
    assert s.sentence_words_limit == 60
    assert s.language == "auto"


def test_round_trip(tmp_path):
    s = Settings(sentence_words_limit=40, disabled_rules=["X"], language="kk")
    s.save(tmp_path / FILE_NAME)
    loaded = Settings.load(tmp_path / FILE_NAME)
    assert loaded == s
    assert json.loads((tmp_path / FILE_NAME).read_text(encoding="utf-8"))["language"] == "kk"


def test_missing_file_gives_defaults(tmp_path):
    assert Settings.load(tmp_path / "нет.json") == Settings()


def test_broken_file_gives_defaults(tmp_path):
    (tmp_path / FILE_NAME).write_text("{это не json", encoding="utf-8")
    assert Settings.load(tmp_path / FILE_NAME) == Settings()


def test_wrong_types_ignored(tmp_path):
    (tmp_path / FILE_NAME).write_text(json.dumps({"sentence_words_limit": "сорок", "language": "ru", "лишнее": 1}), encoding="utf-8")
    s = Settings.load(tmp_path / FILE_NAME)
    assert s.sentence_words_limit == 60
    assert s.language == "ru"
