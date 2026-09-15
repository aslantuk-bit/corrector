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
from corrector.engines.spell import SpellEngine, load_lexicon

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

    def statuses(self) -> list[EngineStatus]:
        result = [self.kk.status(), self.ru_spell.status()]
        if self.ru is not self.ru_spell:
            result.insert(0, self.ru.status())
        else:
            result.insert(0, EngineStatus("lt", False, "; ".join(self.notes) or "LanguageTool выключен"))
        return result

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
) -> Engines:
    data = data_dir or paths.data_dir()
    ru_dict = SpellDictionary(data / "ru" / "ru_RU")
    kk_dict = SpellDictionary(data / "kk" / "kk_KZ")
    ru_spell = SpellEngine("ru_spell", ru_dict, load_lexicon(data / "lexicon_ru_legal.txt"), user_dict)
    kk_spell = SpellEngine("kk_spell", kk_dict, load_lexicon(data / "lexicon_kk_legal.txt"), user_dict, other=ru_dict,
                           foreign_message=FOREIGN_KK)
    engines = Engines(ru=ru_spell, kk=kk_spell, kk_names=kk_spell, ru_spell=ru_spell)
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
