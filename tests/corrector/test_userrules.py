from corrector.core.issue import Category, Level
from corrector.rules.userrules import FILE_NAME, load_user_rules

GOOD = """
- id: sootv
  язык: ru
  найти: "\\\\bв соответствие с\\\\b"
  заменить: "в соответствии с"
  сообщение: "Правильно: «в соответствии с»"
  уровень: ошибка
  категория: грамматика
- id: tenge
  найти: тнг
  заменить: тенге
  сообщение: "Пишите «тенге» полностью"
"""


def test_loads_rules(tmp_path):
    (tmp_path / FILE_NAME).write_text(GOOD, encoding="utf-8")
    rules, errors = load_user_rules(tmp_path / FILE_NAME)
    assert errors == []
    assert [r.id for r in rules] == ["user.sootv", "user.tenge"]
    assert rules[0].lang == "ru" and rules[0].category is Category.GRAMMAR and rules[0].level is Level.ERROR
    assert rules[1].lang == "any" and rules[1].level is Level.WARNING and rules[1].category is Category.STYLE
    assert rules[1].pattern.pattern == r"\bтнг\b"
    assert rules[0].engine == "user"


def test_missing_file_is_empty(tmp_path):
    assert load_user_rules(tmp_path / FILE_NAME) == ([], [])


def test_errors_are_reported_and_rest_loads(tmp_path):
    text = "- id: a\n  найти: \"[\"\n  сообщение: m\n- найти: x\n- id: b\n  найти: y\n  сообщение: ok\n"
    (tmp_path / FILE_NAME).write_text(text, encoding="utf-8")
    rules, errors = load_user_rules(tmp_path / FILE_NAME)
    assert [r.id for r in rules] == ["user.b"]
    assert len(errors) == 2 and "правило 1 (a)" in errors[0] and "правило 2" in errors[1]


def test_not_yaml(tmp_path):
    (tmp_path / FILE_NAME).write_text("{{{", encoding="utf-8")
    rules, errors = load_user_rules(tmp_path / FILE_NAME)
    assert rules == [] and len(errors) == 1
