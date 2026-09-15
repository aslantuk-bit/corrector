"""Правила пользователя из правила.yaml: найти → заменить → сообщение."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from corrector.core.issue import Category, Level
from corrector.rules.patterns import PatternRule

FILE_NAME = "правила.yaml"
LEVELS = {"ошибка": Level.ERROR, "предупреждение": Level.WARNING, "подсказка": Level.HINT}
CATEGORIES = {"орфография": Category.SPELLING, "грамматика": Category.GRAMMAR, "пунктуация": Category.PUNCTUATION,
              "типографика": Category.TYPOGRAPHY, "стиль": Category.STYLE}
SPECIAL = set(r"\.^$*+?{}[]|()")


def load_user_rules(path: Path) -> tuple[list[PatternRule], list[str]]:
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return [], []
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as error:
        return [], [f"{path.name}: не удалось прочитать YAML: {error}"]
    if data is None:
        return [], []
    if not isinstance(data, list):
        return [], [f"{path.name}: ожидается список правил (строки, начинающиеся с «- »)"]
    rules, errors = [], []
    for number, entry in enumerate(data, 1):
        rule_id = str(entry.get("id", number)) if isinstance(entry, dict) else str(number)
        try:
            rules.append(_build(entry, rule_id))
        except ValueError as error:
            errors.append(f"правило {number} ({rule_id}): {error}")
    return rules, errors


def _build(entry, rule_id: str) -> PatternRule:
    if not isinstance(entry, dict):
        raise ValueError("каждое правило — набор полей «найти», «заменить», «сообщение»")
    find = entry.get("найти")
    message = entry.get("сообщение")
    if not find or not message:
        raise ValueError("нужны поля «найти» и «сообщение»")
    find = str(find)
    pattern = find if any(ch in SPECIAL for ch in find) else rf"\b{re.escape(find)}\b"
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
    except re.error as error:
        raise ValueError(f"неверное регулярное выражение «{find}»: {error}") from error
    lang = str(entry.get("язык", "any"))
    if lang not in ("ru", "kk", "any"):
        raise ValueError("«язык» должен быть ru, kk или any")
    level = LEVELS.get(str(entry.get("уровень", "предупреждение")))
    category = CATEGORIES.get(str(entry.get("категория", "стиль")))
    if level is None or category is None:
        raise ValueError("«уровень»: ошибка/предупреждение/подсказка; «категория»: орфография/грамматика/пунктуация/типографика/стиль")
    replacement = entry.get("заменить")
    return PatternRule(f"user.{rule_id}", lang, category, level, str(message), compiled,
                       None if replacement is None else str(replacement), engine="user")
