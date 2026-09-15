"""Общие ресурсы правил: морфология русского, стеммер казахского, стоп-списки, эталонные названия, правила пользователя."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


def _lines(path: Path) -> list[str]:
    try:
        return [l.strip() for l in path.read_text(encoding="utf-8-sig").splitlines() if l.strip() and not l.lstrip().startswith("#")]
    except FileNotFoundError:
        return []


@dataclass
class RuleResources:
    stop_ru: set[str] = field(default_factory=set)
    stop_kk: set[str] = field(default_factory=set)
    official_ru: list[str] = field(default_factory=list)
    official_kk: list[str] = field(default_factory=list)
    user_rules: list = field(default_factory=list)
    user_rule_errors: list[str] = field(default_factory=list)
    _morph: object = None
    _stemmer: object = None

    @property
    def morph(self):
        if self._morph is None:
            import pymorphy3

            self._morph = pymorphy3.MorphAnalyzer()
        return self._morph

    @property
    def stemmer(self):
        if self._stemmer is None:
            from corrector.engines import kk_stem

            self._stemmer = kk_stem.default()
        return self._stemmer


def load_resources(data_dir: Path, user_dir: Path) -> RuleResources:
    from corrector.rules.userrules import FILE_NAME, load_user_rules

    rules, errors = load_user_rules(user_dir / FILE_NAME)
    return RuleResources(
        stop_ru=set(w.lower() for w in _lines(data_dir / "stop_ru.txt")),
        stop_kk=set(w.lower() for w in _lines(data_dir / "stop_kk.txt")),
        official_ru=_lines(data_dir / "names_official_ru.txt"),
        official_kk=_lines(data_dir / "names_official_kk.txt"),
        user_rules=rules,
        user_rule_errors=errors,
    )
