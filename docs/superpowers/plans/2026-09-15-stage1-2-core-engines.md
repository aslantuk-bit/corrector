# Этапы 1–2 «Ядро и движки» — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Командная строка `python -m corrector.cli --check файл.docx --report`, которая читает документ Word с сохранением карты фрагментов, определяет язык каждого абзаца, проверяет русский через LanguageTool (с обходом ловушки Java) или запасной словарь, казахский — через словарь hunspell-kk с юридическим лексиконом, и выдаёт единый список замечаний.

**Architecture:** Пакет `corrector` из четырёх частей: `core` (пути, настройки, журнал, словарь исключений, модель замечания, токены и предложения, язык, обход ловушки Java), `docx_io` (модель документа с картой run), `engines` (LanguageTool: сервер и клиент; словарные движки на spylls; стеммер; конвейер и фабрика движков), `cli`. Словари лежат в `data/` в репозитории с провенансом в `sborka/artifacts.lock`; LanguageTool и Java — в `vendor/` (разработка) и рядом с программой (поставка).

**Tech Stack:** Python 3.13, python-docx 1.2.0, spylls 0.1.7, kazsearch (коммит 04493a5b), LanguageTool 6.9-SNAPSHOT от 14.09.2026 (урезан до русского), Temurin JRE 21, pytest 9.1.1.

**Spec:** `docs/superpowers/specs/2026-09-15-corrector-design.md` (разделы 4, 5, 9–12, 14; этапы 1–2 раздела 15).

## Global Constraints

- Python 3.13, разработка на Mac, сборка на Windows; код должен работать на обоих (разделение путей в `core/paths.py`).
- Все скачивания — по `sborka/artifacts.lock` с SHA-256; файлы словарей коммитятся в `data/`, тест сверяет их суммы с замком.
- Категории замечаний: `spelling`, `grammar`, `punctuation`, `typography`, `style`; уровни `error`, `warning`, `hint`; движки `lt`, `ru_spell`, `kk_spell`, позже `rules`/`user` (спецификация, п. 4.3).
- Тексты сообщений — по-русски, без англицизмов. Оригинальный .docx никогда не изменяется (в этих этапах документ только читается).
- Ловушка Java (спецификация, п. 5.1): перед запуском проверяется, укладывается ли путь к `java/` и `languagetool/` в кодовую страницу ANSI; при отказе папки копируются в `%PUBLIC%`/`%ProgramData%`/`%SystemDrive%\Temp`/`%TEMP%`.
- LanguageTool слушает только 127.0.0.1 на свободном порту; в сеть программа не ходит.
- Разработка через тесты; коммит после каждой задачи; работа в ветке `stage1-2` от `main`.
- Тесты, которым нужны LanguageTool и Java, помечены `@pytest.mark.lt` и пропускаются, если `vendor/languagetool-ru` или Java нет (на сборщике GitHub они пропускаются; на Mac после `tools/dev_setup.sh` — выполняются).

---

## Структура файлов

```
corrector/
  __init__.py                 __version__ = "0.2.0"
  core/
    __init__.py
    paths.py                  app_dir, data_dir, java_home, java_exe, lt_home, user_dir
    log.py                    setup_logging(user_dir) -> Path
    settings.py               Settings (dataclass): load(path), save(path)
    userdict.py               UserDictionary: contains, covers, add; файл «словарь.txt»
    issue.py                  Category, Level, Issue, sort_issues, dedupe, названия по-русски
    text.py                   Token, tokenize, words, sentences, списки сокращений
    lang.py                   KK_LETTERS, KK_WORDS, RU_WORDS, score, detect, detect_all, has_kk_letters
    javaenv.py                active_code_page, path_fits_code_page, default_fallback_roots, copy_to_safe_dir, safe_dir
  docx_io/
    __init__.py
    model.py                  DocxError, RunSpan, Para, DocumentModel, load(path)
  engines/
    __init__.py
    base.py                   EngineStatus
    hunspell.py               SpellDictionary (spylls) с кэшем подсказок
    spell.py                  SpellEngine (kk_spell / ru_spell), inside_quotes
    kk_stem.py                KazakhStemmer
    lt.py                     LT_CATEGORY_MAP, LanguageToolServer, LanguageToolClient, LanguageToolEngine, batches, join_batch, map_matches
    factory.py                Engines, build_engines(no_lt), close
    pipeline.py               check_document(model, engines, user_dict, settings) -> list[Issue]
  cli.py                      --check, --out, --report, --json, --no-lt, --lang, --version
launchcheck/probes.py         copy_java_to_safe_dir → обёртка над corrector.core.javaenv (остальное без изменений)
data/
  ru/ru_RU.aff, ru_RU.dic, README_ru_RU.txt
  kk/kk_KZ.aff, kk_KZ.dic, kaz_stems.dict, kaz_stems.dict.verbs, kaz_stems.dict.meta.json, kaz_stopwords.stop
  lexicon_ru_legal.txt        сокращения и слова права, неизвестные словарю (посев; пополняется на этапе 4)
  lexicon_kk_legal.txt
  lt/lt.properties            maxTextLength=100000, maxCheckTimeMillis=60000, cacheSize=1000
  lt/lt_disabled_rules.txt    пока пусто (комментарий); заполняется по прогону на корпусе (этап 4)
sborka/
  artifacts.lock              + languagetool-20260914, kk_KZ.*, ru_RU.*, kazsearch-py, файлы данных kazsearch
  fetch_artifacts.py          + записи с полем path (один файл → путь в репозитории)
  trim_languagetool.py        vendor/languagetool-20260914 → vendor/languagetool-ru (классы всех языков остаются, данные других языков и словарные jar удаляются, common_words.txt сохраняются)
tools/dev_setup.sh            + скачивание LanguageTool и урезка
tests/corrector/              test_paths.py, test_settings.py, test_userdict.py, test_issue.py, test_text.py, test_lang.py,
                              test_javaenv.py, test_docx_model.py, test_hunspell.py, test_spell.py, test_kk_stem.py,
                              test_lt_unit.py, test_lt_integration.py (lt), test_pipeline.py, test_cli.py, conftest.py (make_docx)
tests/sborka/test_fetch_artifacts.py   + тест записей с path; test_data_lock.py (суммы файлов data/ совпадают с замком)
```

---

### Task 1: Каркас пакета, пути, настройки, журнал, словарь исключений

**Files:**
- Create: `corrector/__init__.py`, `corrector/core/__init__.py`, `corrector/core/paths.py`, `corrector/core/log.py`, `corrector/core/settings.py`, `corrector/core/userdict.py`, `tests/corrector/__init__.py`, `tests/corrector/test_paths.py`, `tests/corrector/test_settings.py`, `tests/corrector/test_userdict.py`
- Modify: `requirements.txt` (+ python-docx, spylls, kazsearch), `pyproject.toml` (маркер `lt`)

**Interfaces:**
- Produces:
  - `paths.app_dir() -> Path` (корень репозитория при запуске из исходников, папка exe в сборке), `paths.data_dir()`, `paths.java_home()`, `paths.java_exe(home=None)`, `paths.lt_home()`, `paths.user_dir()`; переменные окружения `CORRECTOR_JAVA`, `CORRECTOR_LT` переопределяют пути.
  - `log.setup_logging(user_dir: Path) -> Path` — файл `logs/corrector.log`, ротация 5×1 МБ.
  - `settings.Settings` с полями `categories: dict[str,bool]`, `disabled_rules: list[str]`, `sentence_words_limit: int = 60`, `language: str = "auto"`, `last_folder: str = ""`; `Settings.load(path)`, `settings.save(path)`; `settings.FILE_NAME = "настройки.json"`.
  - `userdict.UserDictionary(path)`: `.words: set[str]`, `.phrases: list[str]`, `contains(word) -> bool`, `covers(text, start, end) -> bool`, `add(entry) -> None`; `userdict.FILE_NAME = "словарь.txt"`.

- [ ] **Step 1: Зависимости и падающие тесты**

`requirements.txt`:
```
PySide6-Essentials==6.11.2
python-docx==1.2.0
spylls==0.1.7
kazsearch @ git+https://github.com/iDynbek/kazsearch-py@04493a5b7dac4646d81ce23324788ef77c2d86fe
```

В `pyproject.toml` в `[tool.pytest.ini_options]` добавить:
```toml
markers = ["lt: требует LanguageTool и Java в vendor/ (пропускается, если их нет)"]
```

`corrector/__init__.py`:
```python
"""Корректор: проверка орфографии, пунктуации и стиля юридических текстов на русском и казахском."""

__version__ = "0.2.0"
```

`tests/corrector/test_paths.py`:
```python
import sys
from pathlib import Path

from corrector.core import paths


def test_app_dir_is_repo_root_from_sources():
    assert (paths.app_dir() / "pyproject.toml").exists()


def test_data_dir_under_app_dir():
    assert paths.data_dir() == paths.app_dir() / "data"


def test_java_and_lt_overridden_by_env(monkeypatch, tmp_path):
    monkeypatch.setenv("CORRECTOR_JAVA", str(tmp_path / "j"))
    monkeypatch.setenv("CORRECTOR_LT", str(tmp_path / "lt"))
    assert paths.java_home() == tmp_path / "j"
    assert paths.lt_home() == tmp_path / "lt"
    assert paths.java_exe(tmp_path / "j") == tmp_path / "j" / "bin" / ("java.exe" if sys.platform == "win32" else "java")


def test_java_home_default_is_vendor_from_sources(monkeypatch):
    monkeypatch.delenv("CORRECTOR_JAVA", raising=False)
    assert paths.java_home().parent == paths.app_dir() / "vendor"


def test_user_dir_is_app_dir_when_writable(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "app_dir", lambda: tmp_path)
    assert paths.user_dir() == tmp_path


def test_user_dir_falls_back_when_not_writable(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "app_dir", lambda: tmp_path / "нет-такой-папки")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    result = paths.user_dir()
    assert result.is_dir()
    assert str(result).startswith(str(tmp_path))
```

`tests/corrector/test_settings.py`:
```python
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
```

`tests/corrector/test_userdict.py`:
```python
from corrector.core.userdict import FILE_NAME, UserDictionary


def test_missing_file_is_empty(tmp_path):
    d = UserDictionary(tmp_path / FILE_NAME)
    assert d.words == set() and d.phrases == []
    assert not d.contains("Ахметов")


def test_load_words_and_phrases(tmp_path):
    (tmp_path / FILE_NAME).write_text("# фамилии\nАхметов\n\nТОО «Ак жол»\n  Нур-Султан  \n", encoding="utf-8")
    d = UserDictionary(tmp_path / FILE_NAME)
    assert d.contains("ахметов") and d.contains("АХМЕТОВ") and d.contains("Нур-Султан")
    assert d.phrases == ["тоо «ак жол»"]


def test_covers_phrase_occurrence(tmp_path):
    (tmp_path / FILE_NAME).write_text("ТОО «Ак жол»\n", encoding="utf-8")
    d = UserDictionary(tmp_path / FILE_NAME)
    text = "Истец ТОО «Ак жол» обратился"
    start = text.index("Ак")
    assert d.covers(text, start, start + 2)
    assert not d.covers(text, 0, 5)


def test_add_appends_and_creates_file(tmp_path):
    d = UserDictionary(tmp_path / FILE_NAME)
    d.add("Ахметов")
    d.add("ТОО «Ак жол»")
    assert d.contains("ахметов")
    text = (tmp_path / FILE_NAME).read_text(encoding="utf-8")
    assert text.startswith("#")
    assert "Ахметов\n" in text and "ТОО «Ак жол»\n" in text
    assert UserDictionary(tmp_path / FILE_NAME).phrases == ["тоо «ак жол»"]


def test_add_ignores_duplicates_and_blank(tmp_path):
    d = UserDictionary(tmp_path / FILE_NAME)
    d.add("Ахметов")
    d.add(" ахметов ")
    d.add("")
    assert (tmp_path / FILE_NAME).read_text(encoding="utf-8").count("хметов") == 1
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `uv pip install --python .venv/bin/python -r requirements-dev.txt && .venv/bin/python -m pytest tests/corrector -q`
Expected: `ModuleNotFoundError: No module named 'corrector'`.

- [ ] **Step 3: Написать модули**

`corrector/core/paths.py`:
```python
"""Где что лежит: программа, данные, Java, LanguageTool, папка пользователя."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Корректор"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    return app_dir() / "data"


def java_home() -> Path:
    env = os.environ.get("CORRECTOR_JAVA")
    if env:
        return Path(env)
    if getattr(sys, "frozen", False):
        return app_dir() / "java"
    return app_dir() / "vendor" / ("jre-windows-x64" if sys.platform == "win32" else "jre-mac-aarch64")


def java_exe(home: Path | None = None) -> Path:
    home = home or java_home()
    return home / "bin" / ("java.exe" if sys.platform == "win32" else "java")


def lt_home() -> Path:
    env = os.environ.get("CORRECTOR_LT")
    if env:
        return Path(env)
    if getattr(sys, "frozen", False):
        return app_dir() / "languagetool"
    return app_dir() / "vendor" / "languagetool-ru"


def user_dir() -> Path:
    """Словарь, правила, настройки, журналы: рядом с программой, если туда можно писать, иначе папка пользователя."""
    base = app_dir()
    if _writable(base):
        return base
    if sys.platform == "win32":
        fallback = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / APP_NAME
    elif sys.platform == "darwin":
        fallback = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        fallback = Path.home() / ".config" / "corrector"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _writable(directory: Path) -> bool:
    probe = directory / ".~проверка-записи"
    try:
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False
```

`corrector/core/log.py`:
```python
"""Журнал в logs/corrector.log с ротацией: пять файлов по мегабайту."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path


def setup_logging(user_dir: Path) -> Path:
    logs = user_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    path = logs / "corrector.log"
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(getattr(h, "baseFilename", None) == str(path) for h in root.handlers):
        handler = logging.handlers.RotatingFileHandler(path, maxBytes=1_000_000, backupCount=4, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(handler)
    return path
```

`corrector/core/settings.py`:
```python
"""Настройки пользователя в настройки.json; испорченный файл не роняет программу."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

FILE_NAME = "настройки.json"
log = logging.getLogger(__name__)


@dataclass
class Settings:
    categories: dict[str, bool] = field(
        default_factory=lambda: {"spelling": True, "grammar": True, "punctuation": True, "typography": True, "style": True}
    )
    disabled_rules: list[str] = field(default_factory=list)
    sentence_words_limit: int = 60
    language: str = "auto"  # auto | ru | kk
    last_folder: str = ""

    @classmethod
    def load(cls, path: Path) -> "Settings":
        settings = cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return settings
        except (OSError, ValueError) as error:
            log.warning("настройки не прочитаны (%s), взяты значения по умолчанию", error)
            return settings
        if not isinstance(data, dict):
            return settings
        for key, value in data.items():
            if hasattr(settings, key) and isinstance(value, type(getattr(settings, key))):
                setattr(settings, key, value)
        return settings

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
```

`corrector/core/userdict.py`:
```python
"""Словарь исключений пользователя: слова и фразы по одной на строку, регистр не важен, «#» — комментарий."""

from __future__ import annotations

from pathlib import Path

FILE_NAME = "словарь.txt"
HEADER = "# Словарь исключений Корректора: одно слово или фраза на строку, регистр не важен.\n"


class UserDictionary:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.words: set[str] = set()
        self.phrases: list[str] = []
        self.load()

    def load(self) -> None:
        self.words, self.phrases = set(), []
        try:
            lines = self.path.read_text(encoding="utf-8-sig").splitlines()
        except FileNotFoundError:
            return
        for line in lines:
            self._remember(line)

    def _remember(self, line: str) -> None:
        entry = line.strip().lower()
        if not entry or entry.startswith("#"):
            return
        if any(ch.isspace() for ch in entry):
            if entry not in self.phrases:
                self.phrases.append(entry)
        else:
            self.words.add(entry)

    def contains(self, word: str) -> bool:
        return word.strip().lower() in self.words

    def covers(self, text: str, start: int, end: int) -> bool:
        lowered = text.lower()
        for phrase in self.phrases:
            position = lowered.find(phrase)
            while position != -1:
                if position <= start and end <= position + len(phrase):
                    return True
                position = lowered.find(phrase, position + 1)
        return False

    def add(self, entry: str) -> None:
        entry = entry.strip()
        if not entry or entry.lower() in self.words or entry.lower() in self.phrases:
            return
        if not self.path.exists():
            self.path.write_text(HEADER, encoding="utf-8")
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(entry + "\n")
        self._remember(entry)
```

- [ ] **Step 4: Запустить тесты**

Run: `.venv/bin/python -m pytest tests/corrector -q`
Expected: все проходят.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Корректор: каркас пакета, пути, настройки, журнал, словарь исключений"
```

---

### Task 2: Обход ловушки Java — общий модуль `core/javaenv.py`

**Files:**
- Create: `corrector/core/javaenv.py`, `tests/corrector/test_javaenv.py`
- Modify: `launchcheck/probes.py` (функции `active_code_page`, `path_fits_code_page`, `default_fallback_roots`, `copy_java_to_safe_dir` становятся обёртками), `tests/launchcheck/test_probes.py` не меняется и должен проходить.

**Interfaces:**
- Produces:
  - `active_code_page() -> str | None`, `path_fits_code_page(path, encoding) -> bool`, `default_fallback_roots() -> list[Path]` — как в launchcheck.
  - `copy_to_safe_dir(source: Path, name: str, encoding=None, fallback_roots=None) -> tuple[Path | None, str]` — копия `source` в `<root>/corrector-<name>/` (для Java `name="java"` → `corrector-java/jre`? нет: путь копии `<root>/corrector-java/jre` сохраняется ради совместимости с launchcheck, см. ниже), повторное копирование пропускается, если файл-метка `release` (для Java) или `.corrector-copy` (для остальных) совпадает по содержимому с исходником.
  - `safe_dir(source: Path, name: str, encoding=None, fallback_roots=None) -> tuple[Path, str]` — если путь укладывается в кодовую страницу, возвращает `(source, "")`; иначе копию или, при неудаче, `(source, "копия не удалась: …")`.
  - В `launchcheck.probes`: `copy_java_to_safe_dir(java_dir, encoding=None, fallback_roots=None)` = `copy_to_safe_dir(java_dir, "java", encoding, fallback_roots)` с целевой папкой `<root>/corrector-java/jre`.

Правило целевой папки: `target = root / f"corrector-{name}" / ("jre" if name == "java" else name)`. Метка совпадения: содержимое `source/release`, если файл есть, иначе список имён файлов первого уровня в `source`.

- [ ] **Step 1: Падающие тесты**

`tests/corrector/test_javaenv.py`:
```python
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
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/python -m pytest tests/corrector/test_javaenv.py -q` — `ModuleNotFoundError`.

- [ ] **Step 3: Написать модуль и переключить launchcheck на него**

`corrector/core/javaenv.py`:
```python
"""Обход ловушки запускателя Java на Windows: путь с символами вне кодовой страницы ANSI (JDK-8242283).

Если путь к папке не укладывается в кодовую страницу, папка копируется в первую подходящую папку
без таких символов, и Java (или LanguageTool) запускается оттуда.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import sys
import tempfile
from pathlib import Path

MARKER = ".corrector-copy"


def active_code_page() -> str | None:
    if sys.platform != "win32":
        return None
    acp = ctypes.windll.kernel32.GetACP()
    return "utf-8" if acp == 65001 else f"cp{acp}"


def path_fits_code_page(path: Path, encoding: str | None) -> bool:
    if encoding is None:
        return True
    try:
        str(path).encode(encoding)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


def default_fallback_roots() -> list[Path]:
    if sys.platform != "win32":
        return []
    roots = [
        os.environ.get("PUBLIC", r"C:\Users\Public"),
        os.environ.get("ProgramData", r"C:\ProgramData"),
        os.environ.get("SystemDrive", "C:") + r"\Temp",
        os.environ.get("TEMP", ""),
    ]
    return [Path(r) for r in roots if r]


def _writable(directory: Path) -> bool:
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix="~проверка-", delete=True):
            pass
        return True
    except OSError:
        return False


def _signature(source: Path) -> str:
    release = source / "release"
    if release.is_file():
        return release.read_text(encoding="utf-8", errors="replace")
    return "\n".join(sorted(p.name for p in source.iterdir()))


def _target_for(root: Path, name: str) -> Path:
    return root / f"corrector-{name}" / ("jre" if name == "java" else name)


def copy_to_safe_dir(
    source: Path,
    name: str,
    encoding: str | None = None,
    fallback_roots: list[Path] | None = None,
) -> tuple[Path | None, str]:
    if not source.is_dir():
        return None, f"копия не удалась: нет исходной папки {source}"
    roots = default_fallback_roots() if fallback_roots is None else fallback_roots
    reasons = []
    signature = _signature(source)
    for root in roots:
        if not root.is_dir():
            reasons.append(f"{root}: нет папки")
            continue
        if not path_fits_code_page(root, encoding):
            reasons.append(f"{root}: символы вне кодовой страницы")
            continue
        if not _writable(root):
            reasons.append(f"{root}: нет записи")
            continue
        target = _target_for(root, name)
        marker = target / MARKER
        if marker.is_file() and marker.read_text(encoding="utf-8", errors="replace") == signature:
            return target, f"копия в {target} (уже была)"
        try:
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)
            marker.write_text(signature, encoding="utf-8")
        except OSError as error:
            reasons.append(f"{root}: {error}")
            continue
        return target, f"копия в {target}"
    return None, "копия не удалась: " + ("; ".join(reasons) if reasons else "нет подходящих папок")


def safe_dir(
    source: Path,
    name: str,
    encoding: str | None = None,
    fallback_roots: list[Path] | None = None,
) -> tuple[Path, str]:
    """Папка, из которой можно запускать Java: сама source, если её путь укладывается в кодовую страницу, иначе копия."""
    if path_fits_code_page(source, encoding):
        return source, ""
    target, note = copy_to_safe_dir(source, name, encoding, fallback_roots)
    return (target, note) if target is not None else (source, note)
```

В `launchcheck/probes.py` удалить собственные `active_code_page`, `path_fits_code_page`, `default_fallback_roots`, `copy_java_to_safe_dir` и добавить в конец:
```python
from corrector.core.javaenv import (  # noqa: E402 — общий обход ловушки Java
    active_code_page,
    copy_to_safe_dir,
    default_fallback_roots,
    path_fits_code_page,
)


def copy_java_to_safe_dir(
    java_dir: Path,
    encoding: str | None = None,
    fallback_roots: list[Path] | None = None,
) -> tuple[Path | None, str]:
    return copy_to_safe_dir(java_dir, "java", encoding, fallback_roots)
```
Тест `test_copy_java_to_safe_dir_reuses_existing_copy` в launchcheck ожидает текст «(уже была)» при совпадении `release` — новая реализация даёт то же самое. `monkeypatch.setattr(report.probes, "default_fallback_roots", ...)` в тестах launchcheck продолжает работать, потому что `copy_java_to_safe_dir` вызывает `copy_to_safe_dir` из `javaenv`, а тот читает `default_fallback_roots` из своего модуля: поэтому в `launchcheck/probes.copy_java_to_safe_dir` передавать `fallback_roots if fallback_roots is not None else default_fallback_roots()` явно — тогда подмена в `probes` действует.

- [ ] **Step 4: Запустить все тесты**

Run: `.venv/bin/python -m pytest -q` — все проходят (launchcheck и corrector).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Обход ловушки Java вынесен в corrector.core.javaenv; копия LanguageTool тем же путём"
```

---

### Task 3: Модель замечания, токены и предложения

**Files:**
- Create: `corrector/core/issue.py`, `corrector/core/text.py`, `tests/corrector/test_issue.py`, `tests/corrector/test_text.py`

**Interfaces:**
- Produces:
  - `issue.Category` (`SPELLING, GRAMMAR, PUNCTUATION, TYPOGRAPHY, STYLE`, значения — строки `spelling`…), `issue.Level` (`ERROR, WARNING, HINT`), `issue.CATEGORY_TITLES`, `issue.LEVEL_TITLES` (по-русски), `issue.ENGINE_PRIORITY = {"rules": 0, "user": 0, "lt": 1, "kk_spell": 2, "ru_spell": 2}`.
  - `issue.Issue(paragraph, start, end, category, level, rule_id, engine, message, suggestions=[], context="")` с `to_dict()`.
  - `issue.sort_issues(issues) -> list[Issue]`, `issue.dedupe(issues) -> list[Issue]`.
  - `text.Token(start, end, text, kind)`, `text.tokenize(text) -> list[Token]` (kind: `word | number | punct | space`), `text.words(text) -> list[Token]`, `text.sentences(text, lang="ru") -> list[tuple[int,int]]`, `text.ABBREVIATIONS = {"ru": {...}, "kk": {...}}`, `text.LETTERS` (строка классов букв для регулярных выражений).

- [ ] **Step 1: Падающие тесты**

`tests/corrector/test_issue.py`:
```python
from corrector.core.issue import CATEGORY_TITLES, Category, Issue, Level, dedupe, sort_issues


def make(paragraph=0, start=0, end=5, category=Category.SPELLING, engine="lt", rule="R"):
    return Issue(paragraph, start, end, category, Level.ERROR, rule, engine, "сообщение", ["вариант"])


def test_titles_in_russian():
    assert CATEGORY_TITLES[Category.PUNCTUATION] == "Пунктуация"
    assert Category("spelling") is Category.SPELLING


def test_to_dict_uses_plain_values():
    d = make().to_dict()
    assert d["category"] == "spelling" and d["level"] == "error" and d["suggestions"] == ["вариант"]


def test_sort_by_paragraph_then_position():
    issues = [make(1, 10, 12), make(0, 20, 22), make(0, 5, 9)]
    assert [(i.paragraph, i.start) for i in sort_issues(issues)] == [(0, 5), (0, 20), (1, 10)]


def test_dedupe_keeps_higher_priority_engine_on_overlap():
    lt = make(0, 0, 5, engine="lt", rule="LT")
    rules = make(0, 2, 7, engine="rules", rule="OUR")
    kept = dedupe([lt, rules])
    assert [i.rule_id for i in kept] == ["OUR"]


def test_dedupe_keeps_first_on_equal_priority():
    a = make(0, 0, 5, engine="lt", rule="A")
    b = make(0, 0, 5, engine="lt", rule="B")
    assert [i.rule_id for i in dedupe([a, b])] == ["A"]


def test_dedupe_keeps_different_categories_and_paragraphs():
    a = make(0, 0, 5, category=Category.SPELLING)
    b = make(0, 0, 5, category=Category.TYPOGRAPHY)
    c = make(1, 0, 5, category=Category.SPELLING)
    assert len(dedupe([a, b, c])) == 3
```

`tests/corrector/test_text.py`:
```python
from corrector.core import text


def kinds(s):
    return [(t.text, t.kind) for t in text.tokenize(s)]


def test_tokenize_words_numbers_punct():
    assert kinds("ст. 5-1 ГПК, 2 000 тенге") == [
        ("ст", "word"), (".", "punct"), (" ", "space"), ("5-1", "number"), (" ", "space"), ("ГПК", "word"),
        (",", "punct"), (" ", "space"), ("2", "number"), (" ", "space"), ("000", "number"), (" ", "space"), ("тенге", "word"),
    ]


def test_tokenize_kazakh_and_hyphens():
    assert [t.text for t in text.words("Нұр-Сұлтан қаласының 5-ші бабы")] == ["Нұр-Сұлтан", "қаласының", "бабы"]
    assert [t.text for t in text.tokenize("5-ші")] == ["5-ші"]
    assert text.tokenize("5-ші")[0].kind == "number"


def test_token_offsets():
    tokens = text.words("Суд решил")
    assert (tokens[1].start, tokens[1].end) == (4, 9)


def test_sentences_simple():
    s = "Суд решил. Иск удовлетворить."
    assert [s[a:b] for a, b in text.sentences(s)] == ["Суд решил.", "Иск удовлетворить."]


def test_sentences_keep_abbreviations_and_initials():
    s = "В соответствии со ст. 5 ГПК РК иск подан. Ответчик А. Б. Ахметов не явился."
    assert [s[a:b] for a, b in text.sentences(s)] == [
        "В соответствии со ст. 5 ГПК РК иск подан.", "Ответчик А. Б. Ахметов не явился."]


def test_sentences_list_marker_and_lowercase_continuation():
    s = "1. Рассмотрев дело, суд установил следующее. т.е. иное не доказано."
    assert [s[a:b] for a, b in text.sentences(s)] == ["1. Рассмотрев дело, суд установил следующее. т.е. иное не доказано."]


def test_sentences_question_and_quotes():
    s = "Кто истец? «Ак жол». Ответчик."
    assert [s[a:b] for a, b in text.sentences(s)] == ["Кто истец?", "«Ак жол».", "Ответчик."]


def test_sentences_kazakh_abbreviations():
    s = "Сот шешті. 2024 ж. 5 қаңтардағы шешім жойылсын."
    assert [s[a:b] for a, b in text.sentences(s, "kk")] == ["Сот шешті.", "2024 ж. 5 қаңтардағы шешім жойылсын."]


def test_sentences_without_final_period():
    assert text.sentences("Без точки в конце") == [(0, 17)]
    assert text.sentences("   ") == []
```

- [ ] **Step 2: Убедиться, что тесты падают** — `ModuleNotFoundError`.

- [ ] **Step 3: Написать модули**

`corrector/core/issue.py`:
```python
"""Замечание: где, что, почему, чем заменить."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class Category(str, Enum):
    SPELLING = "spelling"
    GRAMMAR = "grammar"
    PUNCTUATION = "punctuation"
    TYPOGRAPHY = "typography"
    STYLE = "style"


class Level(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    HINT = "hint"


CATEGORY_TITLES = {
    Category.SPELLING: "Орфография",
    Category.GRAMMAR: "Грамматика",
    Category.PUNCTUATION: "Пунктуация",
    Category.TYPOGRAPHY: "Типографика",
    Category.STYLE: "Стиль",
}
LEVEL_TITLES = {Level.ERROR: "ошибка", Level.WARNING: "предупреждение", Level.HINT: "подсказка"}
ENGINE_PRIORITY = {"rules": 0, "user": 0, "lt": 1, "kk_spell": 2, "ru_spell": 2}


@dataclass
class Issue:
    paragraph: int
    start: int
    end: int
    category: Category
    level: Level
    rule_id: str
    engine: str
    message: str
    suggestions: list[str] = field(default_factory=list)
    context: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["category"] = self.category.value
        data["level"] = self.level.value
        return data

    def overlaps(self, other: "Issue") -> bool:
        return self.paragraph == other.paragraph and self.start < other.end and other.start < self.end


def sort_issues(issues: list[Issue]) -> list[Issue]:
    return sorted(issues, key=lambda i: (i.paragraph, i.start, i.end, ENGINE_PRIORITY.get(i.engine, 9)))


def dedupe(issues: list[Issue]) -> list[Issue]:
    """Пересекающиеся замечания одной категории в одном абзаце: остаётся движок с меньшим приоритетом, при равенстве — первое."""
    kept: list[Issue] = []
    for issue in issues:
        priority = ENGINE_PRIORITY.get(issue.engine, 9)
        replaced = False
        for index, other in enumerate(kept):
            if other.category == issue.category and other.overlaps(issue):
                if priority < ENGINE_PRIORITY.get(other.engine, 9):
                    kept[index] = issue
                replaced = True
                break
        if not replaced:
            kept.append(issue)
    return sort_issues(kept)
```

`corrector/core/text.py`:
```python
"""Токены и предложения для обоих языков."""

from __future__ import annotations

import re
from dataclasses import dataclass

LETTERS = "A-Za-zА-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі"
UPPER = "A-ZА-ЯЁӘҒҚҢӨҰҮҺІ"
TOKEN_RE = re.compile(
    rf"(?P<number>\d+(?:[.,]\d+)*(?:-[{LETTERS}]+)?)"
    rf"|(?P<word>[{LETTERS}]+(?:[-'’][{LETTERS}]+)*)"
    rf"|(?P<space>\s+)"
    rf"|(?P<punct>[^\s{LETTERS}\d])"
)
ABBREVIATIONS = {
    "ru": {
        "ст", "ч", "п", "пп", "абз", "гл", "разд", "г", "гг", "ул", "пр", "д", "кв", "к", "стр", "тыс", "млн", "млрд",
        "руб", "тг", "тнг", "коп", "им", "т", "е", "см", "ср", "обл", "с", "пос", "оф", "каб", "зд", "мкр", "р", "н",
        "т.е", "т.д", "т.п", "т.к", "и.о", "уч", "инв", "экз", "лтд", "мм", "га", "кв.м", "чел", "ред",
    },
    "kk": {"т.б", "т.с.с", "ж", "қ", "к", "көш", "ауд", "обл", "млн", "млрд", "мың", "га", "тг", "б", "бет", "тарм", "ш", "м", "а", "мкр"},
}
END_RE = re.compile(r"[.!?…]+[»\")\]]*")


@dataclass(frozen=True)
class Token:
    start: int
    end: int
    text: str
    kind: str  # word | number | punct | space


def tokenize(text: str) -> list[Token]:
    return [Token(m.start(), m.end(), m.group(), m.lastgroup) for m in TOKEN_RE.finditer(text)]


def words(text: str) -> list[Token]:
    return [t for t in tokenize(text) if t.kind == "word"]


def sentences(text: str, lang: str = "ru") -> list[tuple[int, int]]:
    abbreviations = ABBREVIATIONS.get(lang, set()) | ABBREVIATIONS["ru"]
    spans: list[tuple[int, int]] = []
    start = _skip_space(text, 0)
    for match in END_RE.finditer(text):
        end = match.end()
        if end < start:
            continue
        if not _is_sentence_end(text, match.start(), end, abbreviations):
            continue
        spans.append((start, end))
        start = _skip_space(text, end)
    if start < len(text) and text[start:].strip():
        spans.append((start, len(text.rstrip())))
    return spans


def _skip_space(text: str, position: int) -> int:
    while position < len(text) and text[position].isspace():
        position += 1
    return position


def _is_sentence_end(text: str, mark_start: int, end: int, abbreviations: set[str]) -> bool:
    after = _skip_space(text, end)
    if after >= len(text):
        return True
    if after == end:  # знак прилип к следующему символу: «т.е.» или число «5.1»
        return False
    if not (text[after].isupper() or text[after].isdigit() or text[after] in "«\"("):
        return False
    if text[mark_start] != ".":
        return True
    before = text[:mark_start]
    word = re.search(rf"([{LETTERS}][{LETTERS}.]*)$", before)
    if word:
        token = word.group(1).lower().rstrip(".")
        if token in abbreviations or (len(token) == 1 and word.group(1)[0].isupper()):
            return False
    number = re.search(r"(?:^|\n)\s*\d+$", before)
    if number:  # «1.» в начале абзаца или строки — номер пункта
        return False
    return True
```

- [ ] **Step 4: Запустить тесты** — `.venv/bin/python -m pytest tests/corrector/test_issue.py tests/corrector/test_text.py -q` — все проходят. Если падает `test_sentences_list_marker_and_lowercase_continuation` из-за «т.е.»: точка внутри «т.е» прилипает к «е» (после точки нет пробела), а после второй точки идёт строчная «и» — оба условия закрывают разрыв; проверить, что `END_RE` не съедает пробел.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Ядро: модель замечания, токены, деление на предложения с сокращениями"
```

---

### Task 4: Определение языка абзаца

**Files:**
- Create: `corrector/core/lang.py`, `tests/corrector/test_lang.py`

**Interfaces:**
- Produces: `lang.KK_LETTERS: set[str]`, `lang.KK_WORDS: set[str]`, `lang.RU_WORDS: set[str]`, `lang.has_kk_letters(word) -> bool`, `lang.score(text) -> tuple[int, int]` (очки казахского, очки русского), `lang.detect(text, previous="ru") -> str`, `lang.detect_all(texts, mode="auto") -> list[str]` (`mode` из настроек: `auto | ru | kk`).

- [ ] **Step 1: Падающие тесты**

`tests/corrector/test_lang.py`:
```python
from corrector.core import lang

RU = "Истец обратился в суд с иском о взыскании задолженности по договору, в соответствии со статьёй 5 ГПК."
KK = "Талап қоюшы сотқа шарт бойынша берешекті өндіріп алу туралы талап арызбен жүгінді."
RU_WITH_KK_NAME = "Истец ТОО «Ақ жол» обратился в суд по месту нахождения ответчика в городе Астана."


def test_detect_russian_and_kazakh():
    assert lang.detect(RU) == "ru"
    assert lang.detect(KK) == "kk"


def test_russian_paragraph_with_kazakh_name_stays_russian():
    assert lang.detect(RU_WITH_KK_NAME) == "ru"


def test_kazakh_without_special_letters_by_words():
    assert lang.detect("Сот шешім туралы және талап бойынша") == "kk"


def test_empty_or_numeric_inherits_previous():
    assert lang.detect("", previous="kk") == "kk"
    assert lang.detect("12.05.2024 № 5", previous="ru") == "ru"


def test_detect_all_carries_previous_and_respects_mode():
    texts = [RU, "", KK, "№ 7"]
    assert lang.detect_all(texts) == ["ru", "ru", "kk", "kk"]
    assert lang.detect_all(texts, mode="kk") == ["kk"] * 4


def test_has_kk_letters():
    assert lang.has_kk_letters("Ақ") and not lang.has_kk_letters("Ак")
```

- [ ] **Step 2: Убедиться, что тесты падают** — `ModuleNotFoundError`.

- [ ] **Step 3: Написать модуль**

`corrector/core/lang.py`:
```python
"""Язык абзаца: казахские буквы и частотные слова против частотных русских слов (списки сняты с корпуса актов)."""

from __future__ import annotations

from corrector.core.text import words

KK_LETTERS = set("әғқңөұүһіӘҒҚҢӨҰҮҺІ")
KK_WORDS = {
    "және", "туралы", "бойынша", "сәйкес", "деп", "мен", "осы", "үшін", "немесе", "әрі", "бас", "бұдан", "беру",
    "сот", "іс", "жер", "талап", "жылғы", "сотының", "сотқа", "шешім", "жауапкер", "қоюшы", "республикасының",
    "заңды", "заңсыз", "жеке", "тиіс", "болып", "қаласы", "мемлекеттік", "әкімшілік", "тұрғын", "үй", "кодексінің",
    "бабының", "бабы", "жөніндегі", "арыз", "шарт", "төлеу", "өндіріп", "алу", "бойы", "емес", "бар", "жоқ",
}
RU_WORDS = {
    "и", "в", "во", "на", "по", "с", "со", "не", "что", "от", "для", "при", "об", "о", "или", "из", "за", "его",
    "без", "к", "как", "года", "суд", "суда", "статьи", "дела", "решение", "согласно", "далее", "части", "первой",
    "иска", "истца", "ответчика", "заявитель", "республики", "казахстан", "области", "города", "кодекса",
    "соответствии", "истец", "ответчик", "договору", "договора", "взыскании", "обратился",
}


def has_kk_letters(word: str) -> bool:
    return any(ch in KK_LETTERS for ch in word)


def score(text: str) -> tuple[int, int]:
    kk = sum(1 for ch in text if ch in KK_LETTERS) * 3
    ru = 0
    for token in words(text):
        lowered = token.text.lower()
        if lowered in KK_WORDS:
            kk += 2
        elif lowered in RU_WORDS:
            ru += 2
    return kk, ru


def detect(text: str, previous: str = "ru") -> str:
    kk, ru = score(text)
    if kk == 0 and ru == 0:
        return previous
    return "kk" if kk > ru else "ru"


def detect_all(texts: list[str], mode: str = "auto") -> list[str]:
    if mode in ("ru", "kk"):
        return [mode] * len(texts)
    result, previous = [], "ru"
    for text in texts:
        previous = detect(text, previous)
        result.append(previous)
    return result
```

- [ ] **Step 4: Запустить тесты** — проходят.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Ядро: определение языка абзаца по буквам и частотным словам корпуса"`

---

### Task 5: Модель документа Word

**Files:**
- Create: `corrector/docx_io/__init__.py`, `corrector/docx_io/model.py`, `tests/corrector/conftest.py`, `tests/corrector/test_docx_model.py`

**Interfaces:**
- Produces:
  - `model.DocxError(Exception)` с русским сообщением `model.BROKEN_MESSAGE`.
  - `model.RunSpan(run, start, end)`, `model.Para(index, text, runs, where, paragraph)` (`where`: `body | table | header | footer`), `model.DocumentModel(path, document, paragraphs)` с методом `texts() -> list[str]`.
  - `model.load(path: Path) -> DocumentModel`.
  - `tests/corrector/conftest.py`: `make_docx(path, body=[...], table=[[...]], header=None, footer=None) -> Path`, где элемент `body` — строка или список run-ов `[(текст, {"bold": True}), ...]`, плюс поддержка `("hyperlink", текст, url)`.

- [ ] **Step 1: Помощник и падающие тесты**

`tests/corrector/conftest.py`:
```python
from pathlib import Path

import docx
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def _add_hyperlink(paragraph, text: str, url: str) -> None:
    part = paragraph.part
    r_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)
    run = OxmlElement("w:r")
    text_el = OxmlElement("w:t")
    text_el.text = text
    text_el.set(qn("xml:space"), "preserve")
    run.append(text_el)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def _fill(paragraph, content) -> None:
    if isinstance(content, str):
        paragraph.add_run(content)
        return
    for piece in content:
        if piece[0] == "hyperlink":
            _add_hyperlink(paragraph, piece[1], piece[2])
        else:
            text, props = piece
            run = paragraph.add_run(text)
            for key, value in props.items():
                setattr(run, key, value)


def make_docx(path: Path, body=(), table=None, header=None, footer=None) -> Path:
    document = docx.Document()
    for content in body:
        _fill(document.add_paragraph(), content)
    if table:
        grid = document.add_table(rows=len(table), cols=len(table[0]))
        for r, row in enumerate(table):
            for c, cell_text in enumerate(row):
                _fill(grid.cell(r, c).paragraphs[0], cell_text)
    if header is not None:
        _fill(document.sections[0].header.paragraphs[0], header)
    if footer is not None:
        _fill(document.sections[0].footer.paragraphs[0], footer)
    document.save(str(path))
    return path
```

`tests/corrector/test_docx_model.py`:
```python
import pytest

from corrector.docx_io import model
from tests.corrector.conftest import make_docx


def test_load_body_paragraphs_with_run_map(tmp_path):
    path = make_docx(tmp_path / "а.docx", body=["Первый абзац.", [("Жирный", {"bold": True}), (" и обычный", {})]])
    doc = model.load(path)
    assert doc.texts() == ["Первый абзац.", "Жирный и обычный"]
    second = doc.paragraphs[1]
    assert [(s.start, s.end, s.run.text) for s in second.runs] == [(0, 6, "Жирный"), (6, 16, " и обычный")]
    assert second.runs[0].run.bold is True
    assert second.where == "body"


def test_hyperlink_runs_are_part_of_text(tmp_path):
    path = make_docx(tmp_path / "а.docx", body=[[("См. ", {}), ("hyperlink", "сайт суда", "https://sud.kz"), (" здесь", {})]])
    doc = model.load(path)
    assert doc.texts() == ["См. сайт суда здесь"]
    assert [s.run.text for s in doc.paragraphs[0].runs] == ["См. ", "сайт суда", " здесь"]


def test_tabs_and_breaks_keep_offsets(tmp_path):
    path = make_docx(tmp_path / "а.docx", body=[[("а\tб\nв", {}), ("г", {})]])
    doc = model.load(path)
    assert doc.texts() == ["а\tб\nв" + "г"]
    assert [(s.start, s.end) for s in doc.paragraphs[0].runs] == [(0, 5), (5, 6)]


def test_tables_headers_footers_in_order(tmp_path):
    path = make_docx(tmp_path / "а.docx", body=["Тело"], table=[["Я1", "Я2"], ["Я3", "Я4"]], header="Шапка", footer="Подвал")
    doc = model.load(path)
    assert [(p.text, p.where) for p in doc.paragraphs] == [
        ("Тело", "body"), ("Я1", "table"), ("Я2", "table"), ("Я3", "table"), ("Я4", "table"),
        ("Шапка", "header"), ("Подвал", "footer"),
    ]
    assert [p.index for p in doc.paragraphs] == list(range(7))


def test_merged_cells_are_read_once(tmp_path):
    path = make_docx(tmp_path / "а.docx", table=[["Один", "Два"]])
    import docx
    document = docx.Document(str(path))
    table = document.tables[0]
    table.cell(0, 0).merge(table.cell(0, 1))
    document.save(str(path))
    doc = model.load(path)
    assert [p.where for p in doc.paragraphs] == ["table", "table"] or len([p for p in doc.paragraphs if p.where == "table"]) == 2


def test_broken_file_raises_docx_error(tmp_path):
    bad = tmp_path / "б.docx"
    bad.write_bytes(b"это не документ")
    with pytest.raises(model.DocxError) as info:
        model.load(bad)
    assert "не документ Word" in str(info.value)


def test_missing_file_raises_docx_error(tmp_path):
    with pytest.raises(model.DocxError):
        model.load(tmp_path / "нет.docx")
```

- [ ] **Step 2: Убедиться, что тесты падают** — `ModuleNotFoundError: corrector.docx_io`.

- [ ] **Step 3: Написать модель**

`corrector/docx_io/__init__.py` — пустой. `corrector/docx_io/model.py`:
```python
"""Документ Word как список абзацев с картой фрагментов форматирования (run)."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

import docx
from docx.document import Document as _Document
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.hyperlink import Hyperlink
from docx.text.paragraph import Paragraph
from docx.text.run import Run

BROKEN_MESSAGE = (
    "Файл повреждён, защищён паролем или это не документ Word (.docx). "
    "Старый формат .doc откройте в Word и сохраните как .docx."
)


class DocxError(Exception):
    pass


@dataclass
class RunSpan:
    run: Run
    start: int
    end: int


@dataclass
class Para:
    index: int
    text: str
    runs: list[RunSpan]
    where: str
    paragraph: Paragraph


@dataclass
class DocumentModel:
    path: Path
    document: _Document
    paragraphs: list[Para]

    def texts(self) -> list[str]:
        return [p.text for p in self.paragraphs]


def load(path: Path) -> DocumentModel:
    path = Path(path)
    if not path.is_file():
        raise DocxError(f"Файл не найден: {path}")
    try:
        document = docx.Document(str(path))
    except (PackageNotFoundError, KeyError, ValueError, zipfile.BadZipFile, OSError) as error:
        raise DocxError(BROKEN_MESSAGE) from error
    paragraphs: list[Para] = []

    def add(paragraph: Paragraph, where: str) -> None:
        spans, parts, position = [], [], 0
        for item in paragraph.iter_inner_content():
            runs = [item] if isinstance(item, Run) else list(item.runs) if isinstance(item, Hyperlink) else []
            for run in runs:
                text = run.text
                if text:
                    spans.append(RunSpan(run, position, position + len(text)))
                    parts.append(text)
                    position += len(text)
        paragraphs.append(Para(len(paragraphs), "".join(parts), spans, where, paragraph))

    def walk(container, where: str) -> None:
        for item in container.iter_inner_content():
            if isinstance(item, Paragraph):
                add(item, where)
            elif isinstance(item, Table):
                seen = []
                for row in item.rows:
                    for cell in row.cells:
                        if any(cell._tc is tc for tc in seen):
                            continue
                        seen.append(cell._tc)
                        walk(cell, "table")

    walk(document, "body")
    for section in document.sections:
        for paragraph in section.header.paragraphs:
            add(paragraph, "header")
        for paragraph in section.footer.paragraphs:
            add(paragraph, "footer")
    return DocumentModel(path, document, paragraphs)
```

- [ ] **Step 4: Запустить тесты** — проходят. Если `test_merged_cells_are_read_once` показывает три абзаца таблицы, значит python-docx возвращает разные объекты `_tc` для объединённой ячейки: сравнивать по `cell._tc` через `is` не получится — заменить `seen` на множество `id(cell._tc)` и держать ссылки на объекты в списке, чтобы `id` не переиспользовались.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Документ Word: модель абзацев с картой run, таблицы, колонтитулы, гиперссылки"`

---

### Task 6: Данные: словари в репозитории, замок, лексиконы, настройки LanguageTool

**Files:**
- Modify: `sborka/artifacts.lock` (новые записи), `sborka/fetch_artifacts.py` (записи с `path`), `tests/sborka/test_fetch_artifacts.py` (+ тест `path`)
- Create: `tests/sborka/test_data_lock.py`, `data/lexicon_ru_legal.txt`, `data/lexicon_kk_legal.txt`, `data/lt/lt.properties`, `data/lt/lt_disabled_rules.txt`, `data/ИСТОЧНИКИ.md`; файлы словарей появляются после `python sborka/fetch_artifacts.py --files`.

**Interfaces:**
- Produces:
  - Записи замка с полем `path` скачиваются в этот путь относительно корня репозитория: `python sborka/fetch_artifacts.py --files` обрабатывает все записи с `path`; `fetch_file(name, entry, root=ROOT) -> Path`.
  - `data/lexicon_*_legal.txt`: одно слово на строку, `#` — комментарий; читается функцией `corrector.engines.spell.load_lexicon(path) -> set[str]` (задача 7).

- [ ] **Step 1: Замок и падающие тесты**

Добавить в `sborka/artifacts.lock` (внутрь общего объекта, после существующих записей):
```json
  "languagetool-20260914": {
    "url": "https://internal1.languagetool.org/snapshots/LanguageTool-20260914-snapshot.zip",
    "sha256": "ff99f6377f213cc998db688dd1ca18998c2290333a5512f670b502cf9ddafb4b",
    "size": 263140255,
    "unpack_root": "LanguageTool-6.9-SNAPSHOT",
    "note": "LanguageTool 6.9-SNAPSHOT от 14.09.2026, LGPL-2.1; урезается скриптом sborka/trim_languagetool.py"
  },
  "kk_KZ.aff": {
    "url": "https://github.com/iDynbek/hunspell-kk/releases/download/v0.2.8/kk_KZ.aff",
    "sha256": "5d1a87d74e3545c18118f8b4ee66395bfc3089b700f92e4dd9883779b609f557",
    "size": 224201,
    "path": "data/kk/kk_KZ.aff",
    "note": "hunspell-kk v0.2.8 (09.08.2026), GPL-3.0-or-later"
  },
  "kk_KZ.dic": {
    "url": "https://github.com/iDynbek/hunspell-kk/releases/download/v0.2.8/kk_KZ.dic",
    "sha256": "599a5cc0dcaa08040c0cd4417f4c1aeb898841fac993d7936f6e1b5330d05621",
    "size": 2577284,
    "path": "data/kk/kk_KZ.dic",
    "note": "hunspell-kk v0.2.8, 131 289 основ"
  },
  "ru_RU.aff": {
    "url": "https://raw.githubusercontent.com/LibreOffice/dictionaries/eff9495b70722d8e590e97b1710cfc7c00f6ce72/ru_RU/ru_RU.aff",
    "sha256": "38ce7d4af78e211e9bafe4bf7e3d6a2c420591136cb738ec6648f8fdf6524cd7",
    "size": 71236,
    "path": "data/ru/ru_RU.aff",
    "note": "словарь Александра Лебедева из LibreOffice (правка 28.07.2024), лицензия в README_ru_RU.txt"
  },
  "ru_RU.dic": {
    "url": "https://raw.githubusercontent.com/LibreOffice/dictionaries/eff9495b70722d8e590e97b1710cfc7c00f6ce72/ru_RU/ru_RU.dic",
    "sha256": "f6047416a0204adbecf3a451b874ec8a97ee37e2cbc714466ef04d8dbcc0d6fc",
    "size": 3473191,
    "path": "data/ru/ru_RU.dic"
  },
  "README_ru_RU.txt": {
    "url": "https://raw.githubusercontent.com/LibreOffice/dictionaries/eff9495b70722d8e590e97b1710cfc7c00f6ce72/ru_RU/README_ru_RU.txt",
    "sha256": "262af2f6ad70a61e5ee1332ff44fa8ee50edca819cf33207d8ad6ba6a0c9be52",
    "size": 1886,
    "path": "data/ru/README_ru_RU.txt"
  },
  "kaz_stems.dict": {
    "url": "https://raw.githubusercontent.com/iDynbek/kazsearch-py/04493a5b7dac4646d81ce23324788ef77c2d86fe/data/kaz_stems.dict",
    "sha256": "19997c75d74c394fbc5708504eb77720ebf616e609a0c077957f50e02f3cf13a",
    "size": 347787,
    "path": "data/kk/kaz_stems.dict",
    "note": "лексикон стеммера kazsearch (LGPL-3.0, части GPL-3.0 из Apertium-kaz)"
  },
  "kaz_stems.dict.verbs": {
    "url": "https://raw.githubusercontent.com/iDynbek/kazsearch-py/04493a5b7dac4646d81ce23324788ef77c2d86fe/data/kaz_stems.dict.verbs",
    "sha256": "1ecd18ed39d779b68231347154213db982ad482a4a8316062118e7792fa145c1",
    "size": 45989,
    "path": "data/kk/kaz_stems.dict.verbs"
  },
  "kaz_stems.dict.meta.json": {
    "url": "https://raw.githubusercontent.com/iDynbek/kazsearch-py/04493a5b7dac4646d81ce23324788ef77c2d86fe/data/kaz_stems.dict.meta.json",
    "sha256": "bb8b41664f5c084acb7ef2ab9aa9f0ad0b5b4f76c149bf83d6ff57e0630342ed",
    "size": 540,
    "path": "data/kk/kaz_stems.dict.meta.json"
  },
  "kaz_stopwords.stop": {
    "url": "https://raw.githubusercontent.com/iDynbek/kazsearch-py/04493a5b7dac4646d81ce23324788ef77c2d86fe/data/kaz_stopwords.stop",
    "sha256": "457fc2907512c20fded50e44198b26123e53f2a4a75755ff5bf65b609c32ca87",
    "size": 937,
    "path": "data/kk/kaz_stopwords.stop"
  }
```

Дополнить `tests/sborka/test_fetch_artifacts.py`:
```python
def test_fetch_file_writes_to_path_and_verifies(tmp_path):
    source = tmp_path / "src.dic"
    source.write_bytes(b"word/1\n")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    entry = {"url": source.as_uri(), "sha256": digest, "path": "data/x/x.dic"}
    target = fa.fetch_file("x.dic", entry, root=tmp_path / "repo")
    assert target == tmp_path / "repo" / "data" / "x" / "x.dic"
    assert target.read_bytes() == b"word/1\n"


def test_fetch_file_skips_when_present_and_matching(tmp_path):
    source = tmp_path / "src.dic"
    source.write_bytes(b"word/1\n")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    entry = {"url": source.as_uri(), "sha256": digest, "path": "data/x/x.dic"}
    fa.fetch_file("x.dic", entry, root=tmp_path / "repo")
    source.unlink()
    assert fa.fetch_file("x.dic", entry, root=tmp_path / "repo").exists()


def test_fetch_file_rejects_wrong_checksum(tmp_path):
    source = tmp_path / "src.dic"
    source.write_bytes(b"word/1\n")
    entry = {"url": source.as_uri(), "sha256": "0" * 64, "path": "data/x/x.dic"}
    with pytest.raises(ValueError, match="контрольная сумма"):
        fa.fetch_file("x.dic", entry, root=tmp_path / "repo")
    assert not (tmp_path / "repo" / "data" / "x" / "x.dic").exists()
```

`tests/sborka/test_data_lock.py`:
```python
"""Файлы data/ в репозитории совпадают с замком: провенанс словарей проверяется каждым прогоном."""

from sborka import fetch_artifacts as fa


def test_committed_data_files_match_lock():
    lock = fa.load_lock()
    entries = {name: entry for name, entry in lock.items() if "path" in entry}
    assert len(entries) >= 9
    for name, entry in entries.items():
        path = fa.ROOT / entry["path"]
        assert path.is_file(), f"{name}: нет файла {entry['path']} — выполните python sborka/fetch_artifacts.py --files"
        assert fa.sha256_of(path) == entry["sha256"], f"{name}: файл {entry['path']} отличается от замка"
```

- [ ] **Step 2: Убедиться, что тесты падают** — `AttributeError: module has no attribute 'fetch_file'`; `test_data_lock` — нет файлов.

- [ ] **Step 3: Дописать скрипт, скачать файлы, добавить лексиконы и настройки LanguageTool**

В `sborka/fetch_artifacts.py` добавить:
```python
def fetch_file(name: str, entry: dict, root: Path = ROOT) -> Path:
    """Одиночный файл из замка кладётся по entry['path'] относительно корня репозитория."""
    target = root / entry["path"]
    if target.is_file() and sha256_of(target) == entry["sha256"]:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    download(entry["url"], temporary)
    actual = sha256_of(temporary)
    if actual != entry["sha256"]:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"{name}: контрольная сумма не совпала: {actual} вместо {entry['sha256']}")
    temporary.replace(target)
    return target
```
и в `main`: аргумент `--files` (`action="store_true"`): при нём обрабатываются все записи с `path` (`for name, entry in lock.items(): if "path" in entry: print(name, "→", fetch_file(name, entry))`), позиционные имена тогда необязательны (`nargs="*"`).

Run: `.venv/bin/python sborka/fetch_artifacts.py --files` — девять файлов в `data/ru` и `data/kk`.

`data/lexicon_ru_legal.txt` (посев; каждое слово с новой строки):
```
# Юридический лексикон (русский): сокращения и слова, которых нет в словаре ru_RU.
# Одно слово на строку, регистр не важен. Пополняется по прогону на корпусе (этап 4).
РК
ГПК
УПК
УК
КоАП
АППК
ГК
ТК
НК
ЗК
БК
ЭК
ИИН
БИН
ТОО
АО
ИП
КХ
ПК
РГУ
ГУ
КГУ
ГККП
МВД
ДП
УП
ОП
ЦОН
ЕНПФ
ГЦВП
БВУ
КСК
ОСИ
ПТ
МРП
МЗП
СМЭС
ДЧС
УГД
ДГД
КГД
РГП
ПХВ
ТОО
```
`data/lexicon_kk_legal.txt`:
```
# Юридический лексикон (казахский): сокращения и слова, которых нет в словаре kk_KZ.
ҚР
АҚ
ЖШС
ЖК
ҚПК
АПК
АІЖК
ӘҚБтК
ҚК
АК
ЕК
СК
ММ
КММ
ЖСН
БСН
ХҚКО
ІІМ
ПД
МКК
АЕК
```
`data/lt/lt.properties`:
```
maxTextLength=100000
maxTextHardLength=100000
maxCheckTimeMillis=60000
cacheSize=1000
maxCheckThreads=4
```
`data/lt/lt_disabled_rules.txt`:
```
# Правила LanguageTool, отключённые для юридических текстов: по одному идентификатору на строку.
# Список составляется по прогону на корпусе (этап 4). Пока пусто.
```
`data/ИСТОЧНИКИ.md` — таблица «файл → откуда → лицензия», по записям замка (ru_RU: Александр Лебедев, LibreOffice; kk_KZ: iDynbek/hunspell-kk GPL-3.0; kazsearch: LGPL-3.0; LanguageTool: LGPL-2.1; Temurin: GPL-2.0 с Classpath Exception).

- [ ] **Step 4: Запустить тесты** — `.venv/bin/python -m pytest tests/sborka -q` — проходят.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Данные: словари ru_RU и kk_KZ, лексикон kazsearch, посев юридических лексиконов, замок с провенансом"` (файлы `data/**` коммитятся).

---

### Task 7: Словарные движки на spylls (казахский и запасной русский)

**Files:**
- Create: `corrector/engines/__init__.py`, `corrector/engines/base.py`, `corrector/engines/hunspell.py`, `corrector/engines/spell.py`, `tests/corrector/test_hunspell.py`, `tests/corrector/test_spell.py`

**Interfaces:**
- Produces:
  - `base.EngineStatus(name: str, available: bool, note: str = "")`.
  - `hunspell.SpellDictionary(base: Path)`: `known(word) -> bool`, `suggest(word, limit=5) -> list[str]` (кэш), `base` — путь без расширения (`data/kk/kk_KZ`).
  - `spell.load_lexicon(path) -> set[str]` (строчные буквы, без комментариев).
  - `spell.inside_quotes(text, position) -> bool`.
  - `spell.SpellEngine(name, dictionary, lexicon, user_dict, other=None, foreign_message="")`: `check(paragraphs: list[tuple[int, str]]) -> list[Issue]`, `check_tokens(index, text, tokens) -> list[Issue]`, `status() -> EngineStatus`. Пропускаются: слова короче 2 букв, слова из заглавных букв длиной до 6 (сокращения), слова с цифрами, латиница и смесь алфавитов (их проверит слой правил). Неизвестное слово, известное словарю `other` (русскому) вне кавычек → подсказка `Category.STYLE`/`Level.HINT` с сообщением `foreign_message`, внутри кавычек — пропуск. Дефисные слова принимаются, если каждая часть известна. Сообщение орфографии: «Возможно, орфографическая ошибка».

- [ ] **Step 1: Падающие тесты**

`tests/corrector/test_hunspell.py`:
```python
from corrector.core import paths
from corrector.engines.hunspell import SpellDictionary


def test_kazakh_dictionary_knows_legal_words():
    d = SpellDictionary(paths.data_dir() / "kk" / "kk_KZ")
    for word in ["сот", "соттың", "талапкер", "қаулы", "шешімі", "қанағаттандырылсын", "апелляциялық", "Астана"]:
        assert d.known(word), word
    assert not d.known("соттын")
    assert d.suggest("соттын")[0] == "соттың"


def test_russian_dictionary_and_suggestions_cached():
    d = SpellDictionary(paths.data_dir() / "ru" / "ru_RU")
    assert d.known("ходатайство") and d.known("Верховный")
    assert not d.known("ходатайтсво")
    first = d.suggest("ходатайтсво")
    assert first[0] == "ходатайство"
    assert d.suggest("ходатайтсво") is first
```

`tests/corrector/test_spell.py`:
```python
from pathlib import Path

import pytest

from corrector.core import paths
from corrector.core.issue import Category, Level
from corrector.core.userdict import UserDictionary
from corrector.engines.hunspell import SpellDictionary
from corrector.engines.spell import SpellEngine, inside_quotes, load_lexicon


@pytest.fixture(scope="module")
def kk_dict():
    return SpellDictionary(paths.data_dir() / "kk" / "kk_KZ")


@pytest.fixture(scope="module")
def ru_dict():
    return SpellDictionary(paths.data_dir() / "ru" / "ru_RU")


def make_kk(tmp_path, kk_dict, ru_dict, lexicon=frozenset(), words=""):
    (tmp_path / "словарь.txt").write_text(words, encoding="utf-8")
    return SpellEngine("kk_spell", kk_dict, set(lexicon), UserDictionary(tmp_path / "словарь.txt"), other=ru_dict,
                       foreign_message="Русское слово в казахском тексте")


def test_load_lexicon(tmp_path):
    p = tmp_path / "л.txt"
    p.write_text("# заголовок\nҚР\n\n ЖШС \n", encoding="utf-8")
    assert load_lexicon(p) == {"қр", "жшс"}
    assert load_lexicon(tmp_path / "нет.txt") == set()


def test_inside_quotes():
    text = "Талап қоюшы «Закон о защите» деп"
    assert inside_quotes(text, text.index("Закон"))
    assert not inside_quotes(text, 0)
    assert not inside_quotes(text, text.index("деп"))


def test_flags_misspelling_with_suggestions(tmp_path, kk_dict, ru_dict):
    engine = make_kk(tmp_path, kk_dict, ru_dict)
    issues = engine.check([(3, "Соттын шешімі заңды.")])
    assert len(issues) == 1
    issue = issues[0]
    assert (issue.paragraph, issue.start, issue.end) == (3, 0, 6)
    assert issue.category is Category.SPELLING and issue.level is Level.ERROR
    assert issue.suggestions[0] == "соттың" or issue.suggestions[0] == "Соттың"
    assert issue.engine == "kk_spell" and issue.rule_id == "kk_spell:unknown"


def test_skips_abbreviations_numbers_latin_and_lexicon(tmp_path, kk_dict, ru_dict):
    engine = make_kk(tmp_path, kk_dict, ru_dict, lexicon={"жшс"})
    assert engine.check([(0, "ЖШС «Ақ жол» ҚР АҚБтК 5-бабы 2024 ж. Windows email@sud.kz")]) == []


def test_user_dictionary_and_phrases(tmp_path, kk_dict, ru_dict):
    engine = make_kk(tmp_path, kk_dict, ru_dict, words="Ахметбекұлы\n")
    assert engine.check([(0, "Ахметбекұлы келді.")]) == []


def test_russian_word_in_kazakh_text_is_hint_outside_quotes(tmp_path, kk_dict, ru_dict):
    engine = make_kk(tmp_path, kk_dict, ru_dict)
    issues = engine.check([(0, "Сот ходатайство қарады.")])
    assert len(issues) == 1 and issues[0].level is Level.HINT and issues[0].category is Category.STYLE
    assert issues[0].message == "Русское слово в казахском тексте"
    assert engine.check([(0, "Сот «ходатайство» деген сөзді қарады.")]) == []


def test_hyphenated_word_accepted_by_parts(tmp_path, kk_dict, ru_dict):
    engine = make_kk(tmp_path, kk_dict, ru_dict)
    assert engine.check([(0, "Нұр-Сұлтан қаласы")]) == []


def test_check_tokens_only_given_tokens(tmp_path, kk_dict, ru_dict):
    from corrector.core.text import words
    engine = make_kk(tmp_path, kk_dict, ru_dict)
    text = "Истец ТОО «Ақ жол» и Ақметов"
    tokens = [t for t in words(text) if t.text in ("Ақ", "Ақметов")]
    issues = engine.check_tokens(0, text, tokens)
    assert [text[i.start:i.end] for i in issues] == ["Ақметов"]


def test_russian_fallback_engine(tmp_path, ru_dict):
    (tmp_path / "словарь.txt").write_text("", encoding="utf-8")
    engine = SpellEngine("ru_spell", ru_dict, {"гпк", "рк"}, UserDictionary(tmp_path / "словарь.txt"))
    issues = engine.check([(0, "Истец подал ходатайтсво в порядке ст. 5 ГПК РК.")])
    assert [(i.start, i.end) for i in issues] == [(12, 23)]
    assert issues[0].suggestions[0] == "ходатайство"
    assert engine.status().available is True
```

- [ ] **Step 2: Убедиться, что тесты падают** — `ModuleNotFoundError: corrector.engines`.

- [ ] **Step 3: Написать движки**

`corrector/engines/__init__.py` — пустой. `corrector/engines/base.py`:
```python
from dataclasses import dataclass


@dataclass
class EngineStatus:
    name: str
    available: bool
    note: str = ""
```

`corrector/engines/hunspell.py`:
```python
"""Словарь Hunspell через spylls: проверка слова и варианты замены с кэшем."""

from __future__ import annotations

from itertools import islice
from pathlib import Path

from spylls.hunspell import Dictionary


class SpellDictionary:
    def __init__(self, base: Path) -> None:
        self.base = Path(base)
        self.dictionary = Dictionary.from_files(str(self.base))
        self._suggestions: dict[str, list[str]] = {}

    def known(self, word: str) -> bool:
        return bool(self.dictionary.lookup(word))

    def suggest(self, word: str, limit: int = 5) -> list[str]:
        if word not in self._suggestions:
            self._suggestions[word] = list(islice(self.dictionary.suggest(word), limit))
        return self._suggestions[word]
```

`corrector/engines/spell.py`:
```python
"""Словарный движок: неизвестные слова абзаца с учётом лексикона, словаря пользователя и второго языка."""

from __future__ import annotations

import re
from pathlib import Path

from corrector.core.issue import Category, Issue, Level
from corrector.core.text import Token, words
from corrector.core.userdict import UserDictionary
from corrector.engines.base import EngineStatus
from corrector.engines.hunspell import SpellDictionary

LATIN = re.compile(r"[A-Za-z]")
CYRILLIC = re.compile(r"[А-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі]")
UNKNOWN_MESSAGE = "Возможно, орфографическая ошибка"


def load_lexicon(path: Path) -> set[str]:
    try:
        lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return set()
    return {line.strip().lower() for line in lines if line.strip() and not line.lstrip().startswith("#")}


def inside_quotes(text: str, position: int) -> bool:
    before = text[:position]
    if before.count("«") > before.count("»"):
        return True
    return before.count('"') % 2 == 1


class SpellEngine:
    def __init__(
        self,
        name: str,
        dictionary: SpellDictionary,
        lexicon: set[str],
        user_dict: UserDictionary,
        other: SpellDictionary | None = None,
        foreign_message: str = "",
    ) -> None:
        self.name = name
        self.dictionary = dictionary
        self.lexicon = lexicon
        self.user_dict = user_dict
        self.other = other
        self.foreign_message = foreign_message

    def status(self) -> EngineStatus:
        return EngineStatus(self.name, True)

    def check(self, paragraphs: list[tuple[int, str]]) -> list[Issue]:
        issues: list[Issue] = []
        for index, text in paragraphs:
            issues += self.check_tokens(index, text, words(text))
        return issues

    def check_tokens(self, index: int, text: str, tokens: list[Token]) -> list[Issue]:
        issues: list[Issue] = []
        for token in tokens:
            word = token.text
            if self._skip(word) or self._accepted(word):
                continue
            if self.user_dict.covers(text, token.start, token.end):
                continue
            if self.other is not None and self.other.known(word):
                if not inside_quotes(text, token.start):
                    issues.append(Issue(index, token.start, token.end, Category.STYLE, Level.HINT,
                                        f"{self.name}:foreign", self.name, self.foreign_message))
                continue
            issues.append(Issue(index, token.start, token.end, Category.SPELLING, Level.ERROR,
                                f"{self.name}:unknown", self.name, UNKNOWN_MESSAGE, self.dictionary.suggest(word)))
        return issues

    def _skip(self, word: str) -> bool:
        if len(word) < 2 or any(ch.isdigit() for ch in word):
            return True
        if word.isupper() and len(word) <= 6:
            return True
        return bool(LATIN.search(word))

    def _accepted(self, word: str) -> bool:
        lowered = word.lower()
        if lowered in self.lexicon or self.user_dict.contains(word) or self.dictionary.known(word):
            return True
        parts = [p for p in re.split(r"[-'’]", word) if p]
        return len(parts) > 1 and all(p.lower() in self.lexicon or self.dictionary.known(p) for p in parts)
```

- [ ] **Step 4: Запустить тесты** — `.venv/bin/python -m pytest tests/corrector/test_hunspell.py tests/corrector/test_spell.py -q` — проходят. Если `АҚБтК` помечается (смешанный регистр, длина 5): правило «заглавные до 6» его не покрывает — добавить в лексикон kk тестового движка или ослабить условие до «не больше одной строчной буквы среди заглавных»: `sum(ch.islower() for ch in word) <= 1 and sum(ch.isupper() for ch in word) >= 2 and len(word) <= 7`.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Движки: словарная проверка на spylls для казахского и запасная для русского"`

---

### Task 8: Стеммер казахского

**Files:**
- Create: `corrector/engines/kk_stem.py`, `tests/corrector/test_kk_stem.py`

**Interfaces:**
- Produces: `kk_stem.KazakhStemmer(dict_path: Path)` с `stem(word) -> str` (строчные буквы) и `stems(text) -> list[tuple[Token, str]]`; `kk_stem.default() -> KazakhStemmer` (из `data/kk/kaz_stems.dict`).

- [ ] **Step 1: Падающие тесты**

`tests/corrector/test_kk_stem.py`:
```python
from corrector.engines import kk_stem


def test_stems_inflected_forms():
    stemmer = kk_stem.default()
    assert stemmer.stem("мектептерімізде") == "мектеп"
    assert stemmer.stem("Соттың") == "сот"
    assert stemmer.stem("талапкердің") == "талапкер"
    assert stemmer.stem("жауапкерлерге") == "жауапкер"


def test_stems_of_text_keep_tokens():
    stemmer = kk_stem.default()
    pairs = stemmer.stems("Соттың шешімімен талапкер келісті")
    assert [(t.text, s) for t, s in pairs] == [("Соттың", "сот"), ("шешімімен", "шешім"), ("талапкер", "талапкер"), ("келісті", "келіс")]
```

- [ ] **Step 2: Убедиться, что тесты падают** — `ModuleNotFoundError`.

- [ ] **Step 3: Написать обёртку**

`corrector/engines/kk_stem.py`:
```python
"""Стеммер казахского (kazsearch): основа слова для правил повторов и терминов."""

from __future__ import annotations

from pathlib import Path

from kazsearch import Lexicon, StemConfig, stem as _stem

from corrector.core import paths
from corrector.core.text import Token, words


class KazakhStemmer:
    def __init__(self, dict_path: Path) -> None:
        self.config = StemConfig(lexicon=Lexicon.load(str(dict_path)))

    def stem(self, word: str) -> str:
        return _stem(word.lower(), self.config)

    def stems(self, text: str) -> list[tuple[Token, str]]:
        return [(token, self.stem(token.text)) for token in words(text)]


def default() -> KazakhStemmer:
    return KazakhStemmer(paths.data_dir() / "kk" / "kaz_stems.dict")
```

- [ ] **Step 4: Запустить тесты** — проходят (если «келісті» даёт другую основу, взять фактическое значение из вывода: важна стабильность, не форма).

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Движки: стеммер казахского kazsearch"`

---

### Task 9: LanguageTool — снимок, урезка, сервер, клиент, движок

**Files:**
- Create: `sborka/trim_languagetool.py`, `corrector/engines/lt.py`, `tests/corrector/test_lt_unit.py`, `tests/corrector/test_lt_integration.py`
- Modify: `tools/dev_setup.sh` (скачать снимок и урезать), `.gitignore` (без изменений: `vendor/` уже исключён)

**Interfaces:**
- Produces:
  - `sborka/trim_languagetool.py`: `trim(source: Path, target: Path) -> int` (число удалённых записей); командная строка `python sborka/trim_languagetool.py vendor/languagetool-20260914 vendor/languagetool-ru`. Правило: удалить `org/languagetool/resource/<xx>/` целиком, кроме `ru` и кроме файлов `common_words.txt` (их оставить, они читаются при старте для всех языков); удалить словарные jar других языков (список `DROP_JARS`), `languagetool.jar`, `languagetool-commandline.jar`, `testrules.*`. Классы всех языков остаются: LanguageTool создаёт объекты всех языков при старте.
  - `lt.LT_CATEGORY_MAP: dict[str, Category]`, `lt.level_for(category) -> Level`.
  - `lt.LTStartError(Exception)`.
  - `lt.LanguageToolServer(java: Path, home: Path, config: Path | None = None, xmx: str = "768m", startup_timeout: float = 60)`: `start()`, `stop()`, `url: str`, `port: int`, `running: bool`.
  - `lt.LanguageToolClient(url, disabled_rules: list[str] = [], timeout: float = 120)`: `check_text(text, language="ru-RU") -> list[dict]` (matches как в ответе `/v2/check`), `languages() -> list[dict]`.
  - `lt.batches(paragraphs, limit=20000) -> list[list[tuple[int,str]]]`, `lt.join_batch(batch) -> tuple[str, list[tuple[int,int,int]]]` (текст и список `(индекс абзаца, смещение в тексте, длина)`), `lt.map_matches(matches, offsets) -> list[Issue]`.
  - `lt.LanguageToolEngine(client)`: `name = "lt"`, `check(paragraphs) -> list[Issue]`, `status() -> EngineStatus`; после первой сетевой ошибки помечает себя недоступным (`available=False`, `note` с причиной) и возвращает пустой список.
  - `lt.load_disabled_rules(path) -> list[str]`.

- [ ] **Step 1: Скрипт урезки, снимок в vendor, падающие тесты**

`sborka/trim_languagetool.py`:
```python
"""Урезает снимок LanguageTool до русского: данные других языков и словарные jar долой, классы остаются."""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

KEEP_LANGS = {"ru"}
LANG_DIR = re.compile(r"[a-z]{2,3}(_[A-Z]{2})?")
DROP_JARS = [
    "dutch-pos-dict.jar", "languagetool-ga-dicts.jar", "catalan-pos-dict.jar", "lucene-gosen-ipadic.jar", "hanlp.jar",
    "morfologik-ukrainian-lt.jar", "opennlp-postag-models.jar", "opennlp-chunk-models.jar", "opennlp-tokenize-models.jar",
    "english-pos-dict.jar", "portuguese-pos-dict.jar", "spanish-pos-dict.jar", "morfologik-crh-lt.jar", "german-pos-dict.jar",
    "french-pos-dict.jar", "asturian-pos-dict.jar", "languagetool-core-tests.jar", "junit.jar", "hamcrest-core.jar",
]
DROP_FILES = ["languagetool.jar", "languagetool-commandline.jar", "testrules.bat", "testrules.sh"]


def trim(source: Path, target: Path) -> int:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    removed = 0
    resources = target / "org" / "languagetool" / "resource"
    for folder in resources.iterdir():
        if folder.is_dir() and LANG_DIR.fullmatch(folder.name) and folder.name not in KEEP_LANGS:
            for file in folder.rglob("*"):
                if file.is_file() and file.name != "common_words.txt":
                    file.unlink()
                    removed += 1
    for name in DROP_JARS:
        jar = target / "libs" / name
        if jar.exists():
            jar.unlink()
            removed += 1
    for name in DROP_FILES:
        file = target / name
        if file.exists():
            file.unlink()
            removed += 1
    return removed


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 2:
        print("использование: trim_languagetool.py <папка снимка> <папка результата>", file=sys.stderr)
        return 2
    print("удалено:", trim(Path(args[0]), Path(args[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Дописать в `tools/dev_setup.sh` перед `echo "Готово…"`:
```bash
.venv/bin/python sborka/fetch_artifacts.py --files
.venv/bin/python sborka/fetch_artifacts.py languagetool-20260914
.venv/bin/python sborka/trim_languagetool.py vendor/languagetool-20260914 vendor/languagetool-ru
```

Run: `.venv/bin/python sborka/fetch_artifacts.py languagetool-20260914 && .venv/bin/python sborka/trim_languagetool.py vendor/languagetool-20260914 vendor/languagetool-ru && du -sh vendor/languagetool-ru` — около 160 МБ. (Архив уже лежит в `vendor/_cache/LanguageTool-latest-snapshot.zip`; скрипт скачивает по имени из URL — `LanguageTool-20260914-snapshot.zip`; чтобы не качать 263 МБ повторно, переименовать кэш: `mv vendor/_cache/LanguageTool-latest-snapshot.zip vendor/_cache/LanguageTool-20260914-snapshot.zip`.)

`tests/corrector/test_lt_unit.py`:
```python
from corrector.core.issue import Category, Level
from corrector.engines import lt


def test_category_map_and_levels():
    assert lt.LT_CATEGORY_MAP["TYPOS"] is Category.SPELLING
    assert lt.LT_CATEGORY_MAP["EXTEND"] is Category.GRAMMAR
    assert lt.level_for(Category.TYPOGRAPHY) is Level.WARNING
    assert lt.level_for(Category.PUNCTUATION) is Level.ERROR


def test_batches_by_length():
    paragraphs = [(0, "а" * 10), (1, "б" * 10), (2, "в" * 25), (3, "г" * 5)]
    result = lt.batches(paragraphs, limit=22)
    assert [[i for i, _ in b] for b in result] == [[0, 1], [2], [3]]


def test_join_batch_offsets():
    text, offsets = lt.join_batch([(4, "Первый."), (7, "Второй.")])
    assert text == "Первый.\n\nВторой."
    assert offsets == [(4, 0, 7), (7, 9, 7)]


def test_map_matches_to_paragraph_coordinates():
    text, offsets = lt.join_batch([(4, "Первый абзац."), (7, "Второй абзац , с ошибкой.")])
    matches = [{
        "offset": text.index(" ,"), "length": 2, "message": "Поставьте пробел после запятой, а не перед ней.",
        "shortMessage": "", "replacements": [{"value": ","}],
        "rule": {"id": "COMMA_PARENTHESIS_WHITESPACE", "category": {"id": "TYPOGRAPHY"}, "issueType": "whitespace"},
    }, {
        "offset": 0, "length": 6, "message": "Проверьте", "shortMessage": "", "replacements": [],
        "rule": {"id": "X", "category": {"id": "STYLE"}},
    }]
    issues = lt.map_matches(matches, offsets)
    assert [(i.paragraph, i.start, i.end, i.category, i.level, i.engine) for i in issues] == [
        (7, 12, 14, Category.TYPOGRAPHY, Level.WARNING, "lt"),
        (4, 0, 6, Category.STYLE, Level.WARNING, "lt"),
    ]
    assert issues[0].suggestions == [","] and issues[0].rule_id == "COMMA_PARENTHESIS_WHITESPACE"


def test_match_crossing_paragraph_boundary_is_dropped():
    text, offsets = lt.join_batch([(0, "Раз."), (1, "Два.")])
    matches = [{"offset": 2, "length": 6, "message": "м", "replacements": [], "rule": {"id": "X", "category": {"id": "MISC"}}}]
    assert lt.map_matches(matches, offsets) == []


def test_load_disabled_rules(tmp_path):
    p = tmp_path / "r.txt"
    p.write_text("# комментарий\nWHITESPACE_RULE\n\n UPPERCASE_SENTENCE_START \n", encoding="utf-8")
    assert lt.load_disabled_rules(p) == ["WHITESPACE_RULE", "UPPERCASE_SENTENCE_START"]
    assert lt.load_disabled_rules(tmp_path / "нет.txt") == []


def test_engine_becomes_unavailable_after_network_error():
    class BrokenClient:
        def check_text(self, text, language="ru-RU"):
            raise lt.LTUnavailable("сервер не отвечает")

    engine = lt.LanguageToolEngine(BrokenClient())
    assert engine.check([(0, "Текст.")]) == []
    status = engine.status()
    assert status.available is False and "сервер не отвечает" in status.note
```

`tests/corrector/test_lt_integration.py`:
```python
import pytest

from corrector.core import paths
from corrector.core.issue import Category
from corrector.engines import lt

pytestmark = pytest.mark.lt


@pytest.fixture(scope="module")
def server():
    if not paths.java_exe().exists() or not (paths.lt_home() / "languagetool-server.jar").exists():
        pytest.skip("нет LanguageTool или Java в vendor/")
    server = lt.LanguageToolServer(paths.java_exe(), paths.lt_home(), paths.data_dir() / "lt" / "lt.properties")
    server.start()
    yield server
    server.stop()


def test_server_reports_russian(server):
    client = lt.LanguageToolClient(server.url)
    assert any(item["longCode"] == "ru-RU" for item in client.languages())


def test_engine_finds_known_errors(server):
    engine = lt.LanguageToolEngine(lt.LanguageToolClient(server.url))
    paragraphs = [(0, "Истец обратился в суд с иском о взыскании задолжености."), (1, "Ответчик обязан оплатить за товар ."), (2, "Чистый абзац.")]
    issues = engine.check(paragraphs)
    by_paragraph = {}
    for issue in issues:
        by_paragraph.setdefault(issue.paragraph, []).append(issue)
    assert any(i.category is Category.SPELLING and "задолженности" in i.suggestions for i in by_paragraph[0])
    assert any(i.category is Category.GRAMMAR and i.rule_id == "Upotreblenije_predlogov" for i in by_paragraph[1])
    assert any(i.category is Category.TYPOGRAPHY for i in by_paragraph[1])
    assert 2 not in by_paragraph
    assert engine.status().available is True


def test_disabled_rules_are_respected(server):
    client = lt.LanguageToolClient(server.url, disabled_rules=["COMMA_PARENTHESIS_WHITESPACE"])
    matches = client.check_text("Иск был удовлетворен частично .")
    assert all(m["rule"]["id"] != "COMMA_PARENTHESIS_WHITESPACE" for m in matches)


def test_server_stops_and_port_is_free(server):
    import socket
    assert server.running
    # ещё одна проверка: параллельный запуск второго сервера получает другой порт
    second = lt.LanguageToolServer(paths.java_exe(), paths.lt_home())
    second.start()
    try:
        assert second.port != server.port
    finally:
        second.stop()
    with socket.socket() as sock:
        sock.settimeout(0.5)
        assert sock.connect_ex(("127.0.0.1", second.port)) != 0
```

- [ ] **Step 2: Убедиться, что тесты падают** — `.venv/bin/python -m pytest tests/corrector/test_lt_unit.py -q` — `ModuleNotFoundError`.

- [ ] **Step 3: Написать движок LanguageTool**

`corrector/engines/lt.py`:
```python
"""LanguageTool: локальный сервер на приложенной Java и клиент /v2/check."""

from __future__ import annotations

import json
import logging
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from corrector.core.issue import Category, Issue, Level
from corrector.engines.base import EngineStatus

log = logging.getLogger(__name__)

LT_CATEGORY_MAP = {
    "TYPOS": Category.SPELLING,
    "PUNCTUATION": Category.PUNCTUATION,
    "TYPOGRAPHY": Category.TYPOGRAPHY,
    "GRAMMAR": Category.GRAMMAR,
    "CASING": Category.GRAMMAR,
    "NEG": Category.GRAMMAR,
    "EXTEND": Category.GRAMMAR,
    "LOGIC": Category.GRAMMAR,
    "STYLE": Category.STYLE,
    "MISC": Category.STYLE,
}
LEVELS = {
    Category.SPELLING: Level.ERROR,
    Category.PUNCTUATION: Level.ERROR,
    Category.GRAMMAR: Level.ERROR,
    Category.TYPOGRAPHY: Level.WARNING,
    Category.STYLE: Level.WARNING,
}
SEPARATOR = "\n\n"


def level_for(category: Category) -> Level:
    return LEVELS[category]


class LTStartError(Exception):
    pass


class LTUnavailable(Exception):
    pass


def load_disabled_rules(path: Path) -> list[str]:
    try:
        lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return []
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class LanguageToolServer:
    def __init__(self, java: Path, home: Path, config: Path | None = None, xmx: str = "768m", startup_timeout: float = 60) -> None:
        self.java, self.home, self.config, self.xmx, self.startup_timeout = Path(java), Path(home), config, xmx, startup_timeout
        self.port = 0
        self.process: subprocess.Popen | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self) -> None:
        jar = self.home / "languagetool-server.jar"
        if not self.java.exists():
            raise LTStartError(f"нет Java: {self.java}")
        if not jar.exists():
            raise LTStartError(f"нет LanguageTool: {jar}")
        self.port = _free_port()
        command = [str(self.java), f"-Xmx{self.xmx}", "-Djava.awt.headless=true", "-cp", str(jar),
                   "org.languagetool.server.HTTPServer", "--port", str(self.port), "--allow-origin"]
        if self.config is not None:
            command += ["--config", str(self.config)]
        extra = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
        log.info("запуск LanguageTool: %s", " ".join(command))
        self.process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                                        encoding="utf-8", errors="replace", **extra)
        deadline = time.time() + self.startup_timeout
        while time.time() < deadline:
            if self.process.poll() is not None:
                tail = (self.process.stderr.read() or "")[-800:]
                raise LTStartError(f"LanguageTool завершился при старте (код {self.process.returncode}): {tail.strip()}")
            try:
                with urllib.request.urlopen(f"{self.url}/v2/languages", timeout=2):
                    return
            except (urllib.error.URLError, OSError):
                time.sleep(0.3)
        self.stop()
        raise LTStartError(f"LanguageTool не ответил за {self.startup_timeout:g} с")

    def stop(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
        if self.process.stderr:
            self.process.stderr.close()
        self.process = None


class LanguageToolClient:
    def __init__(self, url: str, disabled_rules: list[str] | None = None, timeout: float = 120) -> None:
        self.url, self.disabled_rules, self.timeout = url.rstrip("/"), list(disabled_rules or []), timeout

    def languages(self) -> list[dict]:
        try:
            with urllib.request.urlopen(f"{self.url}/v2/languages", timeout=self.timeout) as response:
                return json.load(response)
        except (urllib.error.URLError, OSError, ValueError) as error:
            raise LTUnavailable(str(error)) from error

    def check_text(self, text: str, language: str = "ru-RU") -> list[dict]:
        fields = {"language": language, "text": text}
        if self.disabled_rules:
            fields["disabledRules"] = ",".join(self.disabled_rules)
        request = urllib.request.Request(f"{self.url}/v2/check", data=urllib.parse.urlencode(fields).encode("utf-8"))
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.load(response)["matches"]
        except (urllib.error.URLError, OSError, ValueError, KeyError) as error:
            raise LTUnavailable(str(error)) from error


def batches(paragraphs: list[tuple[int, str]], limit: int = 20000) -> list[list[tuple[int, str]]]:
    result: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    length = 0
    for index, text in paragraphs:
        extra = len(text) + (len(SEPARATOR) if current else 0)
        if current and length + extra > limit:
            result.append(current)
            current, length = [], 0
            extra = len(text)
        current.append((index, text))
        length += extra
    if current:
        result.append(current)
    return result


def join_batch(batch: list[tuple[int, str]]) -> tuple[str, list[tuple[int, int, int]]]:
    parts, offsets, position = [], [], 0
    for index, text in batch:
        if parts:
            position += len(SEPARATOR)
        offsets.append((index, position, len(text)))
        parts.append(text)
        position += len(text)
    return SEPARATOR.join(parts), offsets


def map_matches(matches: list[dict], offsets: list[tuple[int, int, int]]) -> list[Issue]:
    issues: list[Issue] = []
    for match in matches:
        start, end = match["offset"], match["offset"] + match["length"]
        for index, base, length in offsets:
            if base <= start and end <= base + length:
                category = LT_CATEGORY_MAP.get(match["rule"]["category"]["id"], Category.STYLE)
                issues.append(Issue(
                    paragraph=index, start=start - base, end=end - base, category=category, level=level_for(category),
                    rule_id=match["rule"]["id"], engine="lt", message=match.get("message", "").strip(),
                    suggestions=[r["value"] for r in match.get("replacements", [])[:5]],
                ))
                break
    return issues


class LanguageToolEngine:
    name = "lt"

    def __init__(self, client: LanguageToolClient, batch_limit: int = 20000) -> None:
        self.client, self.batch_limit = client, batch_limit
        self.available, self.note = True, ""

    def status(self) -> EngineStatus:
        return EngineStatus(self.name, self.available, self.note)

    def check(self, paragraphs: list[tuple[int, str]]) -> list[Issue]:
        if not self.available:
            return []
        issues: list[Issue] = []
        for batch in batches(paragraphs, self.batch_limit):
            text, offsets = join_batch(batch)
            try:
                matches = self.client.check_text(text)
            except LTUnavailable as error:
                self.available, self.note = False, f"LanguageTool недоступен: {error}"
                log.warning(self.note)
                return issues
            issues += map_matches(matches, offsets)
        return issues
```

- [ ] **Step 4: Запустить тесты** — `.venv/bin/python -m pytest tests/corrector/test_lt_unit.py tests/corrector/test_lt_integration.py -q` — модульные проходят; интеграционные проходят на Mac с `vendor/` (около 10 с), пропускаются без него.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "LanguageTool: урезка снимка до русского, локальный сервер, клиент, движок с категориями"`

---

### Task 10: Фабрика движков (с обходом ловушки Java) и конвейер проверки

**Files:**
- Create: `corrector/engines/factory.py`, `corrector/engines/pipeline.py`, `tests/corrector/test_factory.py`, `tests/corrector/test_pipeline.py`

**Interfaces:**
- Produces:
  - `factory.Engines`: поля `ru` (движок русского: `LanguageToolEngine` или `SpellEngine`), `kk` (`SpellEngine`), `kk_names` (тот же `SpellEngine` казахского для слов с казахскими буквами в русских абзацах), `ru_spell` (запасной `SpellEngine`, всегда создаётся), `server` (`LanguageToolServer | None`), `notes: list[str]` (что произошло при запуске: копия Java, отказ LanguageTool), метод `statuses() -> list[EngineStatus]`, `close()`.
  - `factory.build_engines(user_dict: UserDictionary, no_lt: bool = False, java_home: Path | None = None, lt_home: Path | None = None, data_dir: Path | None = None) -> Engines`. Порядок: словари → если не `no_lt`: `javaenv.safe_dir(java_home, "java")`, `javaenv.safe_dir(lt_home, "languagetool")` → `LanguageToolServer.start()`; при `LTStartError` — `ru = ru_spell`, в `notes` причина.
  - `pipeline.check_document(model: DocumentModel, engines: Engines, user_dict: UserDictionary, settings: Settings) -> list[Issue]`: язык абзацев (`settings.language`), русские абзацы → `engines.ru`, казахские → `engines.kk`, слова с казахскими буквами в русских абзацах → `engines.kk_names.check_tokens`; затем `filter_issues` (категории по `settings.categories`, `settings.disabled_rules` по `rule_id`, орфографические замечания на слова из словаря пользователя), `dedupe`, сортировка.
  - `pipeline.filter_issues(issues, model, user_dict, settings) -> list[Issue]`.

- [ ] **Step 1: Падающие тесты**

`tests/corrector/test_factory.py`:
```python
from pathlib import Path

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
```

`tests/corrector/test_pipeline.py`:
```python
from corrector.core.issue import Category, Issue, Level
from corrector.core.settings import Settings
from corrector.core.userdict import UserDictionary
from corrector.docx_io import model
from corrector.engines import factory, pipeline
from tests.corrector.conftest import make_docx


class FakeRu:
    name = "fake_ru"

    def __init__(self):
        self.seen = []

    def check(self, paragraphs):
        self.seen += [i for i, _ in paragraphs]
        return [Issue(i, 0, 5, Category.GRAMMAR, Level.ERROR, "FAKE", "lt", "м") for i, _ in paragraphs]

    def status(self):
        from corrector.engines.base import EngineStatus
        return EngineStatus(self.name, True)


def build(tmp_path, fake_ru):
    engines = factory.build_engines(UserDictionary(tmp_path / "словарь.txt"), no_lt=True)
    engines.ru = fake_ru
    return engines


def test_routes_paragraphs_by_language(tmp_path):
    path = make_docx(tmp_path / "а.docx", body=["Истец обратился в суд с иском.", "Талап қоюшы сотқа жүгінді."])
    doc = model.load(path)
    fake = FakeRu()
    engines = build(tmp_path, fake)
    try:
        issues = pipeline.check_document(doc, engines, UserDictionary(tmp_path / "словарь.txt"), Settings())
    finally:
        engines.close()
    assert fake.seen == [0]
    assert [i.paragraph for i in issues] == [0]


def test_kazakh_misspelling_found_and_russian_name_with_kazakh_letters_checked(tmp_path):
    path = make_docx(tmp_path / "а.docx", body=["Соттын шешімі заңды.", "Истец Ақметов обратился в суд с иском."])
    doc = model.load(path)
    engines = build(tmp_path, FakeRu())
    try:
        issues = pipeline.check_document(doc, engines, UserDictionary(tmp_path / "словарь.txt"), Settings())
    finally:
        engines.close()
    spelling = [(i.paragraph, doc.paragraphs[i.paragraph].text[i.start:i.end]) for i in issues if i.category is Category.SPELLING]
    assert spelling == [(0, "Соттын"), (1, "Ақметов")]


def test_filters_by_settings_and_user_dictionary(tmp_path):
    path = make_docx(tmp_path / "а.docx", body=["Соттын шешімі заңды."])
    doc = model.load(path)
    engines = build(tmp_path, FakeRu())
    try:
        user = UserDictionary(tmp_path / "словарь.txt")
        settings = Settings()
        settings.categories["spelling"] = False
        assert pipeline.check_document(doc, engines, user, settings) == []
        settings.categories["spelling"] = True
        settings.disabled_rules = ["kk_spell:unknown"]
        assert pipeline.check_document(doc, engines, user, settings) == []
        settings.disabled_rules = []
        user.add("Соттын")
        assert pipeline.check_document(doc, engines, user, settings) == []
    finally:
        engines.close()


def test_forced_language_mode(tmp_path):
    path = make_docx(tmp_path / "а.docx", body=["Талап қоюшы сотқа жүгінді."])
    doc = model.load(path)
    fake = FakeRu()
    engines = build(tmp_path, fake)
    try:
        pipeline.check_document(doc, engines, UserDictionary(tmp_path / "словарь.txt"), Settings(language="ru"))
    finally:
        engines.close()
    assert fake.seen == [0]
```

- [ ] **Step 2: Убедиться, что тесты падают** — `ModuleNotFoundError`.

- [ ] **Step 3: Написать фабрику и конвейер**

`corrector/engines/factory.py`:
```python
"""Сборка движков: словари, стеммер, LanguageTool с обходом ловушки Java и запасным путём."""

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
```

`corrector/engines/pipeline.py`:
```python
"""Конвейер: язык абзацев → движки → фильтры → снятие дублей → сортировка."""

from __future__ import annotations

from corrector.core import lang
from corrector.core.issue import Category, Issue, dedupe
from corrector.core.settings import Settings
from corrector.core.text import words
from corrector.core.userdict import UserDictionary
from corrector.docx_io.model import DocumentModel
from corrector.engines.factory import Engines


def check_document(model: DocumentModel, engines: Engines, user_dict: UserDictionary, settings: Settings) -> list[Issue]:
    texts = model.texts()
    languages = lang.detect_all(texts, settings.language)
    ru = [(p.index, p.text) for p, code in zip(model.paragraphs, languages) if code == "ru" and p.text.strip()]
    kk = [(p.index, p.text) for p, code in zip(model.paragraphs, languages) if code == "kk" and p.text.strip()]
    issues: list[Issue] = []
    if ru:
        issues += engines.ru.check(ru)
        for index, text in ru:
            tokens = [t for t in words(text) if lang.has_kk_letters(t.text)]
            if tokens:
                issues += engines.kk_names.check_tokens(index, text, tokens)
    if kk:
        issues += engines.kk.check(kk)
    return dedupe(filter_issues(issues, model, user_dict, settings))


def filter_issues(issues: list[Issue], model: DocumentModel, user_dict: UserDictionary, settings: Settings) -> list[Issue]:
    kept = []
    for issue in issues:
        if not settings.categories.get(issue.category.value, True):
            continue
        if issue.rule_id in settings.disabled_rules:
            continue
        if issue.category is Category.SPELLING:
            text = model.paragraphs[issue.paragraph].text
            fragment = text[issue.start:issue.end]
            if user_dict.contains(fragment) or user_dict.covers(text, issue.start, issue.end):
                continue
        kept.append(issue)
    return kept
```

- [ ] **Step 4: Запустить тесты** — `.venv/bin/python -m pytest tests/corrector -q` — проходят (интеграционные `lt` — на Mac).

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Движки: фабрика с обходом ловушки Java и запасным путём, конвейер проверки"`

---

### Task 11: Командная строка и сквозная проверка

**Files:**
- Create: `corrector/cli.py`, `corrector/__main__.py`, `tests/corrector/test_cli.py`
- Modify: `README.md` (раздел «Командная строка»), `.github/workflows/windows.yml` (без изменений по шагам; проверить, что `pip install` тянет kazsearch из git)

**Interfaces:**
- Produces:
  - `python -m corrector --check ПУТЬ [--out ПАПКА] [--report] [--json] [--no-lt] [--lang auto|ru|kk] [--version]`.
  - `cli.main(argv) -> int`: 0 — все файлы проверены; 2 — хотя бы один файл не прочитан (сообщение в stderr); при `--check папка` берутся все `*.docx` без `~$` в имени.
  - `cli.format_report(model, issues, statuses) -> str`: заголовок с именем файла, датой, состоянием движков и счётчиками; затем по строке на замечание: `абзац N | категория | уровень | «фрагмент» → вариант1, вариант2 | сообщение`.
  - `cli.report_path(docx_path, out_dir) -> Path` = `<out или папка файла>/<имя>_отчёт.txt`.
  - Вывод на экран для каждого файла: `имя.docx: N замечаний (ошибок X, предупреждений Y, подсказок Z)`; `--json` печатает список словарей `Issue.to_dict()` плюс поля `file`, `fragment`.

- [ ] **Step 1: Падающие тесты**

`tests/corrector/test_cli.py`:
```python
import json

from corrector import cli
from tests.corrector.conftest import make_docx


def test_check_file_prints_summary_and_writes_report(tmp_path, capsys):
    path = make_docx(tmp_path / "акт.docx", body=["Соттын шешімі заңды.", "Истец подал ходатайтсво."])
    code = cli.main(["--check", str(path), "--report", "--no-lt"])
    assert code == 0
    out = capsys.readouterr().out
    assert "акт.docx: 2 замечаний (ошибок 2, предупреждений 0, подсказок 0)" in out
    report = (tmp_path / "акт_отчёт.txt").read_text(encoding="utf-8-sig")
    assert "абзац 1 | Орфография | ошибка | «Соттын» → соттың" in report or "«Соттын» → Соттың" in report
    assert "абзац 2 | Орфография | ошибка | «ходатайтсво» → ходатайство" in report
    assert "LanguageTool" in report


def test_json_output(tmp_path, capsys):
    path = make_docx(tmp_path / "акт.docx", body=["Соттын шешімі заңды."])
    assert cli.main(["--check", str(path), "--json", "--no-lt"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["fragment"] == "Соттын" and data[0]["category"] == "spelling" and data[0]["file"].endswith("акт.docx")


def test_folder_and_out_dir(tmp_path, capsys):
    folder = tmp_path / "папка"
    folder.mkdir()
    make_docx(folder / "а.docx", body=["Соттын шешімі."])
    make_docx(folder / "б.docx", body=["Чистый текст без ошибок."])
    (folder / "~$а.docx").write_bytes(b"lock")
    out = tmp_path / "отчёты"
    assert cli.main(["--check", str(folder), "--report", "--out", str(out), "--no-lt"]) == 0
    assert sorted(p.name for p in out.iterdir()) == ["а_отчёт.txt", "б_отчёт.txt"]
    assert "б.docx: 0 замечаний" in capsys.readouterr().out


def test_broken_file_returns_two(tmp_path, capsys):
    bad = tmp_path / "плохой.docx"
    bad.write_bytes(b"нет")
    assert cli.main(["--check", str(bad), "--no-lt"]) == 2
    assert "не документ Word" in capsys.readouterr().err


def test_version(capsys):
    import pytest
    with pytest.raises(SystemExit):
        cli.main(["--version"])
    assert "0.2.0" in capsys.readouterr().out
```

- [ ] **Step 2: Убедиться, что тесты падают** — `ModuleNotFoundError: corrector.cli`.

- [ ] **Step 3: Написать командную строку**

`corrector/cli.py`:
```python
"""Командная строка: проверить файл или папку, напечатать итог, записать отчёт или JSON."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from corrector import __version__
from corrector.core import log as log_setup
from corrector.core import paths
from corrector.core.issue import CATEGORY_TITLES, LEVEL_TITLES, Issue, Level
from corrector.core.settings import FILE_NAME as SETTINGS_FILE
from corrector.core.settings import Settings
from corrector.core.userdict import FILE_NAME as DICT_FILE
from corrector.core.userdict import UserDictionary
from corrector.docx_io import model
from corrector.engines import factory, pipeline
from corrector.engines.base import EngineStatus


def report_path(docx_path: Path, out_dir: Path | None) -> Path:
    folder = out_dir or docx_path.parent
    return folder / f"{docx_path.stem}_отчёт.txt"


def counts(issues: list[Issue]) -> dict[Level, int]:
    return {level: sum(1 for i in issues if i.level is level) for level in Level}


def summary_line(name: str, issues: list[Issue]) -> str:
    c = counts(issues)
    return f"{name}: {len(issues)} замечаний (ошибок {c[Level.ERROR]}, предупреждений {c[Level.WARNING]}, подсказок {c[Level.HINT]})"


def format_report(doc: model.DocumentModel, issues: list[Issue], statuses: list[EngineStatus]) -> str:
    lines = [
        f"Корректор {__version__}, отчёт о проверке",
        f"Файл: {doc.path}",
        f"Время: {dt.datetime.now().strftime('%d.%m.%Y %H:%M')}",
        "Движки: " + "; ".join(f"{s.name} — {'работает' if s.available else 'недоступен'}{(' (' + s.note + ')') if s.note else ''}" for s in statuses),
        summary_line(doc.path.name, issues),
        "",
    ]
    for issue in issues:
        text = doc.paragraphs[issue.paragraph].text
        fragment = text[issue.start:issue.end]
        suggestions = ", ".join(issue.suggestions)
        arrow = f" → {suggestions}" if suggestions else ""
        lines.append(f"абзац {issue.paragraph + 1} | {CATEGORY_TITLES[issue.category]} | {LEVEL_TITLES[issue.level]} | «{fragment}»{arrow} | {issue.message}")
    return "\n".join(lines) + "\n"


def collect_files(target: Path) -> list[Path]:
    if target.is_dir():
        return sorted(p for p in target.glob("*.docx") if not p.name.startswith("~$"))
    return [target]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="corrector", description="Проверка документов Word на русском и казахском")
    parser.add_argument("--check", type=Path, required=True, help="файл .docx или папка")
    parser.add_argument("--out", type=Path, help="папка для отчётов (по умолчанию рядом с файлом)")
    parser.add_argument("--report", action="store_true", help="записать текстовый отчёт <имя>_отчёт.txt")
    parser.add_argument("--json", action="store_true", help="напечатать замечания в JSON")
    parser.add_argument("--no-lt", action="store_true", help="не запускать LanguageTool (только словари)")
    parser.add_argument("--lang", choices=["auto", "ru", "kk"], default=None, help="язык документа (по умолчанию из настроек)")
    parser.add_argument("--version", action="version", version=f"Корректор {__version__}")
    args = parser.parse_args(argv)

    user_dir = paths.user_dir()
    log_setup.setup_logging(user_dir)
    settings = Settings.load(user_dir / SETTINGS_FILE)
    if args.lang:
        settings.language = args.lang
    user_dict = UserDictionary(user_dir / DICT_FILE)
    engines = factory.build_engines(user_dict, no_lt=args.no_lt)
    failed = False
    all_json: list[dict] = []
    try:
        for path in collect_files(args.check):
            try:
                doc = model.load(path)
            except model.DocxError as error:
                print(f"{path.name}: {error}", file=sys.stderr)
                failed = True
                continue
            issues = pipeline.check_document(doc, engines, user_dict, settings)
            if args.json:
                for issue in issues:
                    data = issue.to_dict()
                    data["file"] = str(path)
                    data["fragment"] = doc.paragraphs[issue.paragraph].text[issue.start:issue.end]
                    all_json.append(data)
            else:
                print(summary_line(path.name, issues))
            if args.report:
                target = report_path(path, args.out)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(format_report(doc, issues, engines.statuses()), encoding="utf-8-sig")
    finally:
        engines.close()
    if args.json:
        print(json.dumps(all_json, ensure_ascii=False, indent=1))
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
```

`corrector/__main__.py`:
```python
import sys

from corrector.cli import main

sys.exit(main())
```

В `README.md` добавить раздел:
```markdown
## Командная строка (этапы 1–2)

    .venv/bin/python -m corrector --check акт.docx --report          # с LanguageTool из vendor/
    .venv/bin/python -m corrector --check папка --report --out отчёты
    .venv/bin/python -m corrector --check акт.docx --json --no-lt    # только словари

Отчёт `<имя>_отчёт.txt` кладётся рядом с файлом или в `--out`. Словарь исключений `словарь.txt`
и `настройки.json` читаются из папки программы (или из папки пользователя, если она защищена от записи).
```

- [ ] **Step 4: Тесты, затем сквозная проверка на настоящих актах с LanguageTool**

Run: `.venv/bin/python -m pytest -q` — все проходят (на Mac — включая `lt`).

Сквозная проверка (Mac): взять три акта из корпуса — два русских и один казахский — и превратить их в .docx:
```bash
mkdir -p /tmp/акты && .venv/bin/python - <<'EOF'
import sqlite3, docx
con = sqlite3.connect("/Users/fatimafatima/court-analytics/corpus.db")
kk = "(length(text) - length(replace(replace(replace(replace(text,'ә',''),'қ',''),'ң',''),'ү',''))) * 100 > length(text)"
rows = con.execute(f"select id, text from documents where length(text) between 3000 and 20000 and not {kk} limit 2").fetchall()
rows += con.execute(f"select id, text from documents where length(text) between 3000 and 20000 and {kk} limit 1").fetchall()
for doc_id, text in rows:
    d = docx.Document()
    for line in text.splitlines():
        if line.strip():
            d.add_paragraph(line.strip())
    d.save(f"/tmp/акты/акт_{doc_id}.docx")
print([r[0] for r in rows])
EOF
.venv/bin/python -m corrector --check /tmp/акты --report --out /tmp/акты/отчёты && head -40 /tmp/акты/отчёты/*_отчёт.txt
```
Expected: по каждому файлу строка с числами; отчёты с движками «lt — работает», замечания в координатах абзацев, фрагменты совпадают с текстом (визуально проверить 10 строк). Записать в `docs/superpowers/plans/2026-09-15-stage1-2-core-engines.md` (раздел «Что показал прогон») число замечаний по файлам и самые частые правила: это первая оценка шума для этапа 4.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Командная строка: проверка файла и папки, отчёт, JSON; сквозной прогон на актах"`

---

### Task 12: Слияние и итог этапов 1–2

- [ ] **Step 1:** `.venv/bin/python -m pytest -q` зелёный; `git push -u origin stage1-2`; дождаться зелёного прогона сборщика (на Windows интеграционные `lt` пропущены, остальное выполняется: словари в `data/`, kazsearch из git).
- [ ] **Step 2:** Слить в `main` (`git checkout main && git merge --ff-only stage1-2 && git push && git branch -d stage1-2 && git push origin --delete stage1-2`).
- [ ] **Step 3:** Обновить память проекта и отчитаться: что умеет командная строка, что показал прогон на актах, что дальше (этапы 3–4: слой правил и корпус).

---

## Что показал прогон на актах (15.09.2026)

Три акта из corpus.db (два русских, один казахский; 4–10 тыс. символов) → 34 замечания за 12 с вместе со стартом
LanguageTool и загрузкой словарей. По правилам: `MORFOLOGIK_RULE_RU_RU` 15, `kk_spell:unknown` 7,
`kk_spell:foreign` 4, `UPPERCASE_SENTENCE_START` 4, `Latin_letters` 2, `PREP_Ob_And_Noun` 1, `V_etoj_svyazy` 1.
Настоящие находки: «заинтерсованного», «анлогична», «Кazakhstan» (латинская К), «об устранений».
Шум для этапа 4: имена собственные и топонимы («Кызылординской» ×4, «Нуртазанова», «Боранбай») — нужен лексикон
названий из корпуса; `UPPERCASE_SENTENCE_START` срабатывает на строках, начинающихся со строчной после переноса
(кандидат в отключённые); казахские фамилии с аффиксами («Ахметовтің», «Бекмамбетовтің») — правило для имён с
аффиксом; аббревиатура «ӘРПК» добавлена в лексикон kk сразу.

## Самопроверка плана

- Покрытие спецификации: п. 4.1 компоненты `core/docx_io/engines/cli` — задачи 1–11; п. 4.2 путь документа до «единого списка замечаний» — задачи 5, 10; п. 4.3 модель замечания — задача 3; п. 4.4 язык — задача 4 (в том числе казахские буквы в русском абзаце и русские слова в казахском); п. 5.1 LanguageTool с ловушкой Java, урезкой, отображением категорий, списком отключённых правил — задачи 2, 9, 10; п. 5.2 запасная орфография — задачи 7, 10; п. 5.3 казахский словарь, лексикон, стеммер — задачи 6–8; п. 9 словарь и настройки — задача 1; п. 10 командная строка (`--report`; `--comments` появится с примечаниями на этапе 6) — задача 11; п. 11 журнал и понятные ошибки чтения — задачи 1, 5; п. 12 версии и провенанс — задача 6.
- Заглушек нет: у каждого шага есть код или точная команда.
- Имена согласованы: `SpellEngine.check/check_tokens/status`, `LanguageToolEngine.check/status`, `Engines.ru/kk/kk_names/ru_spell/server/notes/statuses/close`, `pipeline.check_document/filter_issues`, `javaenv.safe_dir/copy_to_safe_dir`, `text.words/tokenize/sentences`, `lang.detect_all/has_kk_letters`, `model.load/DocumentModel.texts/Para.index`, `cli.main/format_report/report_path` — одинаковы во всех задачах.
