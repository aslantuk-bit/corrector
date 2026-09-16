"""Сборка движков: словари, LanguageTool с обходом ловушки Java и запасным путём."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from corrector.core import javaenv, paths
from corrector.core.userdict import UserDictionary
from corrector.engines.base import EngineStatus
from corrector.engines.hunspell import SpellDictionary
from corrector.engines.lt import LanguageToolClient, LanguageToolEngine, LanguageToolServer, LTStartError, load_disabled_rules
from corrector.engines.spell import SpellEngine, load_lexicon, load_names
from corrector.rules.engine import RulesEngine, default_rules
from corrector.rules.resources import RuleResources, load_resources

log = logging.getLogger(__name__)
FOREIGN_KK = "Русское слово в казахском тексте"


@dataclass
class Engines:
    ru: object
    kk: SpellEngine
    kk_names: SpellEngine
    ru_spell: SpellEngine
    server: LanguageToolServer | None = None
    notes: list[str] = field(default_factory=list)
    rules: RulesEngine | None = None
    rule_resources: RuleResources | None = None

    def statuses(self) -> list[EngineStatus]:
        result = [self.kk.status(), self.ru_spell.status()]
        if self.ru is not self.ru_spell:
            result.insert(0, self.ru.status())
        else:
            result.insert(0, EngineStatus("lt", False, "; ".join(self.notes) or "LanguageTool выключен"))
        if self.rules is not None:
            note = f"правил: {len(self.rules.rules)}"
            errors = self.rule_resources.user_rule_errors if self.rule_resources else []
            if errors:
                note += f"; ошибок в правила.yaml: {len(errors)}"
            result.append(EngineStatus("rules", True, note))
        return result

    def suggest(self, word: str, lang: str) -> list[str]:
        """Варианты замены по требованию (окно запрашивает их при выборе замечания)."""
        dictionary = self.kk.dictionary if lang == "kk" else self.ru_spell.dictionary
        return dictionary.suggest(word)

    def close(self) -> None:
        if self.server is not None:
            self.server.stop()
            self.server = None


def build_engines(
    user_dict: UserDictionary,
    no_lt: bool = False,
    java_home: Path | None = None,
    lt_home: Path | None = None,
    data_dir: Path | None = None,
    user_dir: Path | None = None,
    suggestions: bool = True,
) -> Engines:
    data = data_dir or paths.data_dir()
    ru_dict = SpellDictionary(data / "ru" / "ru_RU")
    kk_dict = SpellDictionary(data / "kk" / "kk_KZ")
    ru_spell = SpellEngine("ru_spell", ru_dict, load_lexicon(data / "lexicon_ru_legal.txt"), user_dict, suggestions=suggestions,
                           names=load_names(data / "names_corpus_ru.txt"))
    kk_spell = SpellEngine("kk_spell", kk_dict, load_lexicon(data / "lexicon_kk_legal.txt"), user_dict, other=ru_dict,
                           foreign_message=FOREIGN_KK, suggestions=suggestions, names=load_names(data / "names_corpus_kk.txt"))
    engines = Engines(ru=ru_spell, kk=kk_spell, kk_names=kk_spell, ru_spell=ru_spell)
    resources = load_resources(data, user_dir or paths.user_dir())
    engines.rules = RulesEngine(default_rules(resources), resources)
    engines.rule_resources = resources
    if no_lt:
        return engines
    java_home = java_home or paths.java_home()
    lt_home = lt_home or paths.lt_home()
    encoding = javaenv.active_code_page()
    java_dir, note = javaenv.safe_dir(java_home, "java", encoding)
    if note:
        engines.notes.append(f"Java: {note}")
    lt_dir, note = javaenv.safe_dir(lt_home, "languagetool", encoding)
    if note:
        engines.notes.append(f"LanguageTool: {note}")
    server = LanguageToolServer(paths.java_exe(java_dir), lt_dir, data / "lt" / "lt.properties")
    try:
        server.start()
    except LTStartError as error:
        engines.notes.append(f"LanguageTool не запущен: {error}")
        log.warning("LanguageTool не запущен: %s", error)
        return engines
    client = LanguageToolClient(server.url, load_disabled_rules(data / "lt" / "lt_disabled_rules.txt"))
    engines.ru = LanguageToolEngine(client)
    engines.server = server
    return engines
