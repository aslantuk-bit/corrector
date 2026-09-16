"""У каждого встроенного правила есть таблица примеров в docs/rules-ru.md или docs/rules-kk.md."""

from corrector.core import paths
from corrector.rules import doctests, engine, resources

DEFAULT_OFF = {"rep.near"}  # есть в коде, в набор по умолчанию не входит


def test_every_rule_documented():
    documented = {c.rule_id for c in doctests.parse_rule_docs(paths.app_dir() / "docs" / "rules-ru.md")}
    documented |= {c.rule_id for c in doctests.parse_rule_docs(paths.app_dir() / "docs" / "rules-kk.md")}
    used = {rule.id for rule in engine.default_rules(resources.RuleResources())}
    missing = used - documented
    assert not missing, f"правила без таблицы примеров: {sorted(missing)}"


def test_documented_rules_exist_in_default_set():
    documented = {c.rule_id for c in doctests.parse_rule_docs(paths.app_dir() / "docs" / "rules-ru.md")}
    documented |= {c.rule_id for c in doctests.parse_rule_docs(paths.app_dir() / "docs" / "rules-kk.md")}
    used = {rule.id for rule in engine.default_rules(resources.RuleResources())}
    stale = documented - used - DEFAULT_OFF
    assert not stale, f"в docs есть таблицы для правил, которых нет в наборе: {sorted(stale)}"
