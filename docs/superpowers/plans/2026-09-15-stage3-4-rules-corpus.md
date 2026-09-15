# Этапы 3–4 «Слой правил и настройка по корпусу» — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Собственный слой правил для обоих языков (типографика, смешанные алфавиты, повторы, длинные предложения, разнобой имён, официальные названия, русские юридические шаблоны, казахская пунктуация и дефисы, правила пользователя из `правила.yaml`), описанный таблицами примеров в `docs/rules-ru.md` и `docs/rules-kk.md`, которые читаются тестами; затем настройка по корпусу: список отключённых правил LanguageTool по цифрам, лексиконы слов и имён из 41 760 актов, смешанные абзацы, имена собственные без шума, ленивые подсказки.

**Architecture:** Пакет `corrector/rules`: `context.py` (контекст абзаца и документа), `base.py` (правило и фабрика замечаний), `patterns.py` (правило-шаблон на регулярном выражении с заменой), наборы правил по файлам (`typography.py`, `alphabets.py`, `repeats.py`, `sentences.py`, `names.py`, `official.py`, `legal_ru.py`, `punct_kk.py`), `userrules.py` (`правила.yaml`), `engine.py` (прогон по документу), `doctests.py` (таблицы из docs как тесты). Конвейер вызывает движок правил после словарных движков; дубли снимаются в пользу правил. Инструменты этапа 4 в `tools/` работают только на Mac с `~/court-analytics/corpus.db`.

**Tech Stack:** Python 3.13, pymorphy3 2.0.6 (морфология русского для правил), PyYAML 6.0.3 (правила пользователя), kazsearch (основы казахских слов), difflib (сверка названий), существующие движки.

**Spec:** `docs/superpowers/specs/2026-09-15-corrector-design.md` (разделы 5.4, 6, 9, 14; этапы 3–4 раздела 15).

## Global Constraints

- Правило — объект с идентификатором `<набор>.<имя>` (латиницей, например `typo.double_space`), языком `ru | kk | any`, категорией и уровнем из `corrector.core.issue`, сообщением по-русски; замечание правил имеет `engine="rules"`, правил пользователя — `engine="user"`.
- Каждое встроенное правило описано в `docs/rules-ru.md` или `docs/rules-kk.md` таблицей «Неправильно | Правильно»; тесты читают таблицы напрямую (задача 1). Правило без таблицы не считается готовым.
- Правила не меняют текст сами: только замечания с вариантами; применение варианта — `text[:start] + suggestion + text[end:]`.
- Русские шаблоны добавляются только там, где LanguageTool молчит (проверено прогоном 15.09.2026: «в соответствие с», «согласно + родительный падеж», запятая перед «что/который/если» отсутствуют у LanguageTool).
- Шумность измеряется прогоном по выборке корпуса (60 русских, 60 казахских актов): правило, срабатывающее чаще чем в трети актов, без ручного разбора не включается.
- Все прежние ограничения: ветка `stage3-4` от `main`, тесты первыми, коммит после задачи, тексты по-русски.

---

## Структура файлов

```
corrector/rules/
  __init__.py
  context.py        ParaContext, DocContext, build_contexts(model, languages, resources)
  base.py           Rule (базовый класс), make_issue
  patterns.py       PatternRule (регулярное выражение + замена)
  typography.py     TYPOGRAPHY_RULES (общие)
  alphabets.py      MixedAlphabetRule, RomanNumeralRule
  repeats.py        DoubleWordRule, NearRepeatRule
  sentences.py      LongSentenceRule
  names.py          NamesConsistencyRule (разнобой имён по документу)
  official.py       OfficialNamesRule (эталонные названия органов и законов)
  legal_ru.py       русские юридические шаблоны и морфологические правила
  punct_kk.py       казахская пунктуация и дефисы
  userrules.py      load_user_rules(path) -> (rules, errors)
  engine.py         RulesEngine, default_rules(resources)
  resources.py      RuleResources: morph (pymorphy3), stemmer (kazsearch), стоп-списки, официальные названия, правила пользователя
  doctests.py       parse_rule_docs(path) -> list[DocCase]
corrector/engines/pipeline.py   + прогон правил, смешанные абзацы, имена собственные
corrector/engines/spell.py      + suggestions=False (ленивые подсказки), политика имён собственных
corrector/core/lang.py          + "mixed"
data/
  names_official_ru.txt, names_official_kk.txt     эталонные названия (одно на строку)
  stop_ru.txt, stop_kk.txt                          частотные слова для правила повторов (из корпуса)
  names_corpus_ru.txt, names_corpus_kk.txt          имена и названия из корпуса (регистр важен)
  lexicon_ru_legal.txt, lexicon_kk_legal.txt        пополняются из корпуса
  lt/lt_disabled_rules.txt                          заполняется по цифрам с пояснениями
  правила.yaml (образец в поставке: sborka/правила.yaml)
docs/rules-ru.md, docs/rules-kk.md, docs/corpus-report.md
tools/corpus_sample.py, tools/corpus_run.py, tools/build_lexicon.py
tests/corrector/test_rule_docs.py, test_rules_engine.py, test_patterns.py, test_userrules.py, test_names.py,
                test_official.py, test_legal_ru.py, test_punct_kk.py, test_repeats.py, test_lang_mixed.py,
                test_spell_names.py, test_pipeline_rules.py
```

---

### Task 1: Каркас правил: контексты, базовое правило, движок, таблицы docs как тесты

**Files:**
- Create: `corrector/rules/__init__.py`, `corrector/rules/context.py`, `corrector/rules/base.py`, `corrector/rules/resources.py`, `corrector/rules/engine.py`, `corrector/rules/doctests.py`, `docs/rules-ru.md`, `docs/rules-kk.md` (заголовки и формат, без правил), `tests/corrector/test_rules_engine.py`, `tests/corrector/test_rule_docs.py`
- Modify: `requirements.txt` (+ `pymorphy3==2.0.6`, `pymorphy3-dicts-ru==2.4.417150.4580142`, `PyYAML==6.0.3`)

**Interfaces:**
- Produces:
  - `context.ParaContext(index, text, lang, where, tokens, words, sentences)`; `context.DocContext(paragraphs: list[ParaContext], settings: Settings, resources: RuleResources)`; `context.build_contexts(model, languages, settings, resources) -> DocContext` (для абзацев с языком `mixed` берутся оба списка сокращений).
  - `base.Rule`: атрибуты класса `id: str`, `lang: str`, `category: Category`, `level: Level`, `message: str`; метод `check(self, para: ParaContext, doc: DocContext) -> list[Issue]`; для правил по всему документу `document_level = True` и метод `check_document(self, doc) -> list[Issue]`; `base.make_issue(rule, para, start, end, suggestions=(), message=None) -> Issue` (engine="rules").
  - `resources.RuleResources(morph=None, stemmer=None, stop_ru=set(), stop_kk=set(), official_ru=[], official_kk=[], user_rules=[])`, `resources.load_resources(data_dir, user_dir) -> RuleResources` (pymorphy3 и стеммер создаются лениво через свойства `morph`/`stemmer`).
  - `engine.RulesEngine(rules: list[Rule])`: `run(doc: DocContext) -> list[Issue]` — правила с подходящим языком (`any` или язык абзаца; для `mixed` — правила `any`) по каждому абзацу плюс правила уровня документа; `engine.default_rules(resources) -> list[Rule]` — все встроенные наборы (пополняется задачами 3–8) плюс правила пользователя.
  - `doctests.DocCase(rule_id, lang, wrong, right, line)` и `doctests.parse_rule_docs(path: Path) -> list[DocCase]`; формат таблиц: заголовок `## <rule_id> — <название>`, строка `Категория: … · Уровень: … · Язык: ru|kk|any`, таблица `| Неправильно | Правильно |`; в правой колонке `✓` — отрицательный пример (замечания быть не должно), `—` — замечание ожидается, автозамены нет.
  - `tests/corrector/test_rule_docs.py`: параметризованный тест по всем строкам обеих таблиц: строит документ из одного абзаца, прогоняет `RulesEngine(default_rules(...))` с языком из таблицы; ожидает замечание с `rule_id` (или его отсутствие для `✓`); если «Правильно» не `—`, применяет первый вариант первого замечания этого правила и сравнивает с «Правильно».

- [ ] **Step 1: Зависимости, формат docs, падающие тесты**

Добавить в `requirements.txt` строки `pymorphy3==2.0.6`, `pymorphy3-dicts-ru==2.4.417150.4580142`, `PyYAML==6.0.3`; выполнить `uv pip install --python .venv/bin/python -r requirements-dev.txt`.

`docs/rules-ru.md` (начало; таблицы правил добавляются задачами 3–7):
```markdown
# Правила Корректора: русский и общие

Каждое правило — заголовок `## идентификатор — название`, строка с категорией, уровнем и языком, таблица примеров.
Правая колонка: исправленный текст, `✓` — замечания быть не должно, `—` — замечание без автозамены.
Тесты `tests/corrector/test_rule_docs.py` читают эти таблицы напрямую.
```
`docs/rules-kk.md` — то же с заголовком «Правила Корректора: казахский».

`tests/corrector/test_rules_engine.py`:
```python
from corrector.core.issue import Category, Level
from corrector.core.settings import Settings
from corrector.docx_io import model
from corrector.rules import base, context, engine, resources
from tests.corrector.conftest import make_docx


class HelloRule(base.Rule):
    id = "test.hello"
    lang = "ru"
    category = Category.STYLE
    level = Level.HINT
    message = "нашли «привет»"

    def check(self, para, doc):
        position = para.text.find("привет")
        return [base.make_issue(self, para, position, position + 6, ["здравствуйте"])] if position >= 0 else []


class CountRule(base.Rule):
    id = "test.count"
    lang = "any"
    category = Category.STYLE
    level = Level.HINT
    message = "абзацев"
    document_level = True

    def check_document(self, doc):
        first = doc.paragraphs[0]
        return [base.make_issue(self, first, 0, 1, message=f"абзацев: {len(doc.paragraphs)}")]


def make_doc(tmp_path, texts, langs, settings=None):
    doc = model.load(make_docx(tmp_path / "а.docx", body=list(texts)))
    return context.build_contexts(doc, list(langs), settings or Settings(), resources.RuleResources())


def test_contexts_have_tokens_and_sentences(tmp_path):
    doc = make_doc(tmp_path, ["Суд решил. Иск удовлетворить.", "Сот шешті."], ["ru", "kk"])
    first = doc.paragraphs[0]
    assert first.lang == "ru" and first.where == "body"
    assert [t.text for t in first.words] == ["Суд", "решил", "Иск", "удовлетворить"]
    assert len(first.sentences) == 2 and doc.paragraphs[1].lang == "kk"


def test_engine_runs_rules_by_language_and_document_level(tmp_path):
    doc = make_doc(tmp_path, ["привет суду", "привет сотқа"], ["ru", "kk"])
    issues = engine.RulesEngine([HelloRule(), CountRule()]).run(doc)
    assert [(i.rule_id, i.paragraph, i.engine) for i in issues] == [("test.count", 0, "rules"), ("test.hello", 0, "rules")]
    assert issues[1].suggestions == ["здравствуйте"] and issues[1].message == "нашли «привет»"
    assert issues[0].message == "абзацев: 2"


def test_make_issue_uses_rule_fields(tmp_path):
    doc = make_doc(tmp_path, ["привет"], ["ru"])
    issue = base.make_issue(HelloRule(), doc.paragraphs[0], 0, 6)
    assert (issue.category, issue.level, issue.rule_id, issue.engine) == (Category.STYLE, Level.HINT, "test.hello", "rules")
```

`tests/corrector/test_rule_docs.py`:
```python
from pathlib import Path

import pytest

from corrector.core import paths
from corrector.core.settings import Settings
from corrector.docx_io import model
from corrector.rules import context, doctests, engine, resources
from tests.corrector.conftest import make_docx

CASES = doctests.parse_rule_docs(paths.app_dir() / "docs" / "rules-ru.md") + doctests.parse_rule_docs(paths.app_dir() / "docs" / "rules-kk.md")


@pytest.fixture(scope="module")
def rules_engine():
    return engine.RulesEngine(engine.default_rules(resources.load_resources(paths.data_dir(), Path("/nonexistent"))))


def test_docs_have_cases():
    assert len(CASES) >= 1  # заполняется задачами 3–8


@pytest.mark.parametrize("case", CASES, ids=[f"{c.lang}:{c.rule_id}:{c.line}" for c in CASES])
def test_rule_doc_case(case, rules_engine, tmp_path):
    doc = model.load(make_docx(tmp_path / "п.docx", body=[case.wrong]))
    ctx = context.build_contexts(doc, [case.lang], Settings(), rules_engine.resources)
    issues = [i for i in rules_engine.run(ctx) if i.rule_id == case.rule_id]
    if case.right == "✓":
        assert issues == [], f"лишнее замечание: {[(i.start, i.end, i.message) for i in issues]}"
        return
    assert issues, f"правило {case.rule_id} не сработало на «{case.wrong}»"
    if case.right != "—":
        first = issues[0]
        assert first.suggestions, "нет варианта замены"
        fixed = case.wrong[: first.start] + first.suggestions[0] + case.wrong[first.end:]
        assert fixed == case.right
```
Добавить в `docs/rules-ru.md` временную таблицу для проверки механизма (удаляется в задаче 3, когда появятся настоящие правила):
```markdown
## test.hello — Проверочное правило
Категория: style · Уровень: hint · Язык: ru

| Неправильно | Правильно |
|---|---|
| привет суду | здравствуйте суду |
| добрый день | ✓ |
```
и зарегистрировать `HelloRule` временно в `default_rules` (удалить в задаче 3).

- [ ] **Step 2: Убедиться, что тесты падают** — `ModuleNotFoundError: corrector.rules`.

- [ ] **Step 3: Написать каркас**

`corrector/rules/resources.py`:
```python
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
```
(`userrules.load_user_rules` появится в задаче 2; до неё в `load_resources` временно `rules, errors = [], []` — или сразу создать `userrules.py` с заглушкой, возвращающей пустые списки.)

`corrector/rules/context.py`:
```python
"""Контекст абзаца и документа для правил: токены, предложения, язык, ресурсы."""

from __future__ import annotations

from dataclasses import dataclass, field

from corrector.core.settings import Settings
from corrector.core.text import Token, sentences, tokenize
from corrector.docx_io.model import DocumentModel
from corrector.rules.resources import RuleResources


@dataclass
class ParaContext:
    index: int
    text: str
    lang: str
    where: str
    tokens: list[Token]
    words: list[Token]
    sentences: list[tuple[int, int]]

    def sentence_of(self, position: int) -> tuple[int, int] | None:
        for start, end in self.sentences:
            if start <= position < end:
                return start, end
        return None

    def word_before(self, token: Token) -> Token | None:
        previous = [t for t in self.tokens if t.end <= token.start and t.kind != "space"]
        return previous[-1] if previous else None


@dataclass
class DocContext:
    paragraphs: list[ParaContext]
    settings: Settings
    resources: RuleResources
    extra: dict = field(default_factory=dict)


def build_contexts(model: DocumentModel, languages: list[str], settings: Settings, resources: RuleResources) -> DocContext:
    paragraphs = []
    for para, lang in zip(model.paragraphs, languages):
        tokens = tokenize(para.text)
        paragraphs.append(ParaContext(
            index=para.index, text=para.text, lang=lang, where=para.where, tokens=tokens,
            words=[t for t in tokens if t.kind == "word"],
            sentences=sentences(para.text, "kk" if lang == "kk" else "ru"),
        ))
    return DocContext(paragraphs, settings, resources)
```

`corrector/rules/base.py`:
```python
"""Базовое правило и фабрика замечаний."""

from __future__ import annotations

from corrector.core.issue import Category, Issue, Level
from corrector.rules.context import DocContext, ParaContext


class Rule:
    id: str = ""
    lang: str = "any"  # ru | kk | any
    category: Category = Category.STYLE
    level: Level = Level.HINT
    message: str = ""
    document_level: bool = False

    def applies(self, lang: str) -> bool:
        return self.lang == "any" or self.lang == lang

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        return []

    def check_document(self, doc: DocContext) -> list[Issue]:
        return []


def make_issue(rule: Rule, para: ParaContext, start: int, end: int, suggestions=(), message: str | None = None,
               engine: str = "rules") -> Issue:
    return Issue(para.index, start, end, rule.category, rule.level, rule.id, engine, message or rule.message, list(suggestions))
```

`corrector/rules/engine.py`:
```python
"""Прогон правил по документу."""

from __future__ import annotations

from corrector.core.issue import Issue
from corrector.rules.base import Rule
from corrector.rules.context import DocContext
from corrector.rules.resources import RuleResources


class RulesEngine:
    name = "rules"

    def __init__(self, rules: list[Rule], resources: RuleResources | None = None) -> None:
        self.rules = rules
        self.resources = resources or RuleResources()

    def run(self, doc: DocContext) -> list[Issue]:
        issues: list[Issue] = []
        for rule in self.rules:
            if rule.document_level:
                issues += rule.check_document(doc)
        for para in doc.paragraphs:
            if not para.text.strip():
                continue
            for rule in self.rules:
                if not rule.document_level and rule.applies(para.lang):
                    issues += rule.check(para, doc)
        return issues


def default_rules(resources: RuleResources) -> list[Rule]:
    rules: list[Rule] = []
    # наборы добавляются задачами 3–8: typography, alphabets, repeats, sentences, names, official, legal_ru, punct_kk
    rules += list(resources.user_rules)
    return rules
```
(`RulesEngine(default_rules(res))` в тесте docs должен получать `resources`: сделать `default_rules` возвращающим правила, а тест строит `RulesEngine(rules, resources)`; поправить фикстуру: `res = load_resources(...); return engine.RulesEngine(engine.default_rules(res), res)`.)

`corrector/rules/doctests.py`:
```python
"""Таблицы примеров из docs/rules-*.md как тестовые случаи."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

HEADER_RE = re.compile(r"^## (?P<id>[a-z_]+\.[a-z0-9_]+) — ")
META_RE = re.compile(r"Язык: (?P<lang>ru|kk|any)")


@dataclass(frozen=True)
class DocCase:
    rule_id: str
    lang: str
    wrong: str
    right: str
    line: int


def parse_rule_docs(path: Path) -> list[DocCase]:
    cases: list[DocCase] = []
    rule_id, lang = None, "ru"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return cases
    for number, line in enumerate(lines, 1):
        header = HEADER_RE.match(line)
        if header:
            rule_id, lang = header.group("id"), "ru"
            continue
        meta = META_RE.search(line)
        if meta and rule_id:
            lang = meta.group("lang")
            continue
        if rule_id and line.startswith("|") and not line.startswith("|---") and "Неправильно" not in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0]:
                case_lang = "ru" if lang == "any" else lang
                cases.append(DocCase(rule_id, case_lang, cells[0], cells[1], number))
    return cases
```
Примеры в таблицах не могут содержать символ `|`; вертикальная черта в правилах не нужна.

- [ ] **Step 4: Запустить тесты** — `.venv/bin/python -m pytest tests/corrector/test_rules_engine.py tests/corrector/test_rule_docs.py -q` — проходят (2 случая из проверочной таблицы).

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Правила: контексты, базовое правило, движок, таблицы docs как тесты"`

---

### Task 2: Правила-шаблоны и правила пользователя (`правила.yaml`)

**Files:**
- Create: `corrector/rules/patterns.py`, `corrector/rules/userrules.py`, `sborka/правила.yaml` (образец для поставки), `tests/corrector/test_patterns.py`, `tests/corrector/test_userrules.py`

**Interfaces:**
- Produces:
  - `patterns.PatternRule(id, lang, category, level, message, pattern: str | re.Pattern, replacement: str | None = None, flags=re.IGNORECASE, condition=None, engine="rules")`: `check` находит все совпадения `pattern` в тексте абзаца; замечание на совпадение; вариант замены — `match.expand(replacement)` (если задана); `condition(match, para, doc) -> bool` отсекает ложные срабатывания. Замена, совпадающая с исходным фрагментом, не считается замечанием.
  - `userrules.FILE_NAME = "правила.yaml"`, `userrules.load_user_rules(path) -> tuple[list[PatternRule], list[str]]`: список записей с полями `id`, `язык` (`ru|kk|any`, по умолчанию `any`), `найти` (регулярное выражение; если нет спецсимволов — ищется как слово целиком), `заменить` (необязательно), `сообщение`, `уровень` (`ошибка|предупреждение|подсказка`, по умолчанию `предупреждение`), `категория` (`орфография|грамматика|пунктуация|типографика|стиль`, по умолчанию `стиль`). Ошибки (не YAML, не список, нет `найти`/`сообщение`, плохое выражение) попадают в список строк вида «правило 3 (user-3): …» и не мешают остальным; `engine="user"`, `rule_id = "user." + id`.

- [ ] **Step 1: Падающие тесты**

`tests/corrector/test_patterns.py`:
```python
import re

from corrector.core.issue import Category, Level
from corrector.core.settings import Settings
from corrector.docx_io import model
from corrector.rules import context, resources
from corrector.rules.patterns import PatternRule
from tests.corrector.conftest import make_docx


def para(tmp_path, text, lang="ru"):
    doc = model.load(make_docx(tmp_path / "п.docx", body=[text]))
    ctx = context.build_contexts(doc, [lang], Settings(), resources.RuleResources())
    return ctx.paragraphs[0], ctx


def test_pattern_rule_finds_and_replaces(tmp_path):
    rule = PatternRule("typo.test", "any", Category.TYPOGRAPHY, Level.WARNING, "двойной пробел", r" {2,}", " ")
    p, ctx = para(tmp_path, "Суд  решил   дело.")
    issues = rule.check(p, ctx)
    assert [(i.start, i.end, i.suggestions) for i in issues] == [(3, 5, [" "]), (10, 13, [" "])]
    assert issues[0].rule_id == "typo.test" and issues[0].engine == "rules"


def test_pattern_rule_groups_and_condition(tmp_path):
    rule = PatternRule("legal.test", "ru", Category.GRAMMAR, Level.ERROR, "в соответствии с",
                       r"\bв соответствие (с|со)\b", r"в соответствии \1",
                       condition=lambda m, p, d: not p.text[max(0, m.start() - 9):m.start()].lower().endswith("привести "))
    p, ctx = para(tmp_path, "Действуя в соответствие с законом, привести в соответствие с ним.")
    issues = rule.check(p, ctx)
    assert len(issues) == 1 and issues[0].suggestions == ["в соответствии с"]


def test_pattern_rule_ignores_identity_replacement(tmp_path):
    rule = PatternRule("x.y", "any", Category.STYLE, Level.HINT, "м", r"слово", r"слово")
    p, ctx = para(tmp_path, "слово")
    assert rule.check(p, ctx) == []
```

`tests/corrector/test_userrules.py`:
```python
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
```

- [ ] **Step 2: Убедиться, что тесты падают.**

- [ ] **Step 3: Написать модули**

`corrector/rules/patterns.py`:
```python
"""Правило-шаблон: регулярное выражение, замена с группами, условие."""

from __future__ import annotations

import re
from typing import Callable

from corrector.core.issue import Category, Issue, Level
from corrector.rules.base import Rule, make_issue
from corrector.rules.context import DocContext, ParaContext

Condition = Callable[[re.Match, ParaContext, DocContext], bool]


class PatternRule(Rule):
    def __init__(self, id: str, lang: str, category: Category, level: Level, message: str,
                 pattern: str | re.Pattern, replacement: str | None = None, flags: int = re.IGNORECASE,
                 condition: Condition | None = None, engine: str = "rules") -> None:
        self.id, self.lang, self.category, self.level, self.message = id, lang, category, level, message
        self.pattern = re.compile(pattern, flags) if isinstance(pattern, str) else pattern
        self.replacement, self.condition, self.engine = replacement, condition, engine

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        issues: list[Issue] = []
        for match in self.pattern.finditer(para.text):
            if self.condition is not None and not self.condition(match, para, doc):
                continue
            suggestions = []
            if self.replacement is not None:
                fixed = match.expand(self.replacement)
                if fixed == match.group():
                    continue
                suggestions = [fixed]
            issues.append(make_issue(self, para, match.start(), match.end(), suggestions, engine=self.engine))
        return issues
```

`corrector/rules/userrules.py`:
```python
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
        rule_id = entry.get("id", f"{number}") if isinstance(entry, dict) else f"{number}"
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
```

`sborka/правила.yaml` (образец, кладётся в поставку рядом с программой):
```yaml
# Свои правила Корректора. Каждое правило начинается с «- id:».
# найти — слово или регулярное выражение; заменить — необязательно; уровень — ошибка/предупреждение/подсказка;
# категория — орфография/грамматика/пунктуация/типографика/стиль; язык — ru/kk/any.
# Ошибка в одном правиле не мешает остальным: программа покажет номер правила.
- id: тнг
  найти: тнг
  заменить: тенге
  сообщение: "Пишите «тенге» полностью"
  уровень: подсказка
# - id: свой_пример
#   язык: ru
#   найти: "\\bв соответствие с\\b"
#   заменить: "в соответствии с"
#   сообщение: "Правильно: «в соответствии с»"
#   уровень: ошибка
#   категория: грамматика
```

- [ ] **Step 4: Запустить тесты** — `.venv/bin/python -m pytest tests/corrector -q` — проходят.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Правила: шаблоны с заменой и условием, правила пользователя из правила.yaml"`

---

### Task 3: Типографика и смешанные алфавиты (общие правила)

**Files:**
- Create: `corrector/rules/typography.py`, `corrector/rules/alphabets.py`, `tests/corrector/test_alphabets.py`
- Modify: `corrector/rules/engine.py` (`default_rules` += `TYPOGRAPHY_RULES`, `[MixedAlphabetRule(), RomanNumeralRule()]`; убрать `HelloRule`), `docs/rules-ru.md` (таблицы ниже; убрать `test.hello`)

**Interfaces:**
- Produces: `typography.TYPOGRAPHY_RULES: list[PatternRule]` с идентификаторами `typo.double_space`, `typo.space_before_punct`, `typo.no_space_after_punct`, `typo.quotes`, `typo.dash`, `typo.abbrev_space` («ст.5» → «ст. 5», «п.5», «№5», «г.Астана», «т.е.» не трогать), `typo.year_g` («2024г.» → «2024 г.»), `typo.initials` («Ахметов А.Б.» → «Ахметов А. Б.»); `alphabets.MixedAlphabetRule` (`alpha.mixed`, error, spelling) и `alphabets.RomanNumeralRule` (`alpha.roman`, warning, typography); `alphabets.LOOKALIKES: dict[str, str]` латиница → кириллица.

- [ ] **Step 1: Таблицы в docs и падающие тесты**

Добавить в `docs/rules-ru.md`:
```markdown
## typo.double_space — Двойной пробел
Категория: typography · Уровень: warning · Язык: any

| Неправильно | Правильно |
|---|---|
| Суд  решил. | Суд решил. |
| Суд решил. | ✓ |

## typo.space_before_punct — Пробел перед знаком препинания
Категория: typography · Уровень: warning · Язык: any

| Неправильно | Правильно |
|---|---|
| Иск удовлетворён , решение вступило в силу . | Иск удовлетворён, решение вступило в силу . |
| Иск удовлетворён; далее | ✓ |
| ст. 5 ГПК | ✓ |

## typo.no_space_after_punct — Нет пробела после знака препинания
Категория: typography · Уровень: warning · Язык: any

| Неправильно | Правильно |
|---|---|
| Иск удовлетворён,решение вступило в силу. | Иск удовлетворён, решение вступило в силу. |
| Сумма 5,5 млн тенге | ✓ |
| Дата 01.02.2024 | ✓ |
| ТОО «Ак жол»,ответчик | ТОО «Ак жол», ответчик |

## typo.quotes — Кавычки-лапки вместо «ёлочек»
Категория: typography · Уровень: warning · Язык: any

| Неправильно | Правильно |
|---|---|
| ТОО "Ак жол" подало иск. | ТОО «Ак жол» подало иск. |
| ТОО «Ак жол» подало иск. | ✓ |

## typo.dash — Дефис вместо тире между пробелами
Категория: typography · Уровень: warning · Язык: any

| Неправильно | Правильно |
|---|---|
| Истец - физическое лицо. | Истец — физическое лицо. |
| Нур-Султан | ✓ |
| Истец — физическое лицо. | ✓ |

## typo.abbrev_space — Нет пробела после сокращения
Категория: typography · Уровень: warning · Язык: any

| Неправильно | Правильно |
|---|---|
| согласно ст.5 ГПК | согласно ст. 5 ГПК |
| в п.3 договора | в п. 3 договора |
| дело №5 | дело № 5 |
| в г.Астана | в г. Астана |
| т.е. иное | ✓ |
| согласно ст. 5 ГПК | ✓ |

## typo.year_g — Год и «г.» без пробела
Категория: typography · Уровень: warning · Язык: any

| Неправильно | Правильно |
|---|---|
| решение от 12.05.2024г. | решение от 12.05.2024 г. |
| в 2024г. заключён договор | в 2024 г. заключён договор |
| 12.05.2024 г. | ✓ |

## typo.initials — Инициалы без пробела
Категория: typography · Уровень: warning · Язык: any

| Неправильно | Правильно |
|---|---|
| судья Ахметов А.Б. решил | судья Ахметов А. Б. решил |
| судья Ахметов А. Б. решил | ✓ |
| ТОО «А.Б.» | ✓ |

## alpha.mixed — Латинская буква в кириллическом слове
Категория: spelling · Уровень: error · Язык: any

| Неправильно | Правильно |
|---|---|
| Кazakhstan | — |
| иcтец подал иск | истец подал иск |
| ИнтерснабGas | — |
| Windows | ✓ |
| истец | ✓ |

## alpha.roman — Римская цифра набрана кириллическими буквами
Категория: typography · Уровень: warning · Язык: any

| Неправильно | Правильно |
|---|---|
| глава ІІ Кодекса | глава II Кодекса |
| часть ІV статьи | часть IV статьи |
| глава II Кодекса | ✓ |
```
Правило `typo.space_before_punct` в первом примере даёт два замечания; тест применяет первое (перед запятой) — поэтому в «Правильно» точка с пробелом остаётся.

`tests/corrector/test_alphabets.py`:
```python
from corrector.rules.alphabets import LOOKALIKES, fix_lookalikes, is_mixed


def test_is_mixed():
    assert is_mixed("Кazakhstan") and is_mixed("иcтец") and is_mixed("ИнтерснабGas")
    assert not is_mixed("Windows") and not is_mixed("истец") and not is_mixed("ҚР")


def test_fix_lookalikes_only_when_every_latin_letter_has_pair():
    assert fix_lookalikes("иcтец") == "истец"
    assert fix_lookalikes("Кazakhstan") is None  # k, z, h без кириллических двойников
    assert LOOKALIKES["c"] == "с" and LOOKALIKES["H"] == "Н"
```

- [ ] **Step 2: Убедиться, что тесты падают.**

- [ ] **Step 3: Написать правила**

`corrector/rules/typography.py`:
```python
"""Типографика, общая для обоих языков."""

from __future__ import annotations

import re

from corrector.core.issue import Category, Level
from corrector.rules.patterns import PatternRule

W, T = Level.WARNING, Category.TYPOGRAPHY
ABBREVIATIONS = r"(?:ст|стр|п|пп|ч|абз|гл|разд|г|ул|д|кв|каб|оф|т|бап|тарм|б|қ|көш)"


def _rule(id, message, pattern, replacement=None, flags=re.IGNORECASE, condition=None, lang="any"):
    return PatternRule(id, lang, T, W, message, pattern, replacement, flags, condition)


TYPOGRAPHY_RULES = [
    _rule("typo.double_space", "Двойной пробел", r"(?<=\S) {2,}(?=\S)", " "),
    _rule("typo.space_before_punct", "Пробел перед знаком препинания", r"(?<=\S) +(?=[,;:!?](?!\S*\w))", ""),
    _rule("typo.space_before_punct", "Пробел перед точкой", r"(?<=[^\s\d.]) +(?=\.(?:\s|$))", ""),
    _rule("typo.no_space_after_punct", "Нет пробела после знака препинания", r"(?<=[А-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі»)])[,;](?=[А-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі«(])", lambda m: None),
    _rule("typo.quotes", "Кавычки-лапки: в документах приняты «ёлочки»", r'"([^"\n]{1,120})"', r"«\1»"),
    _rule("typo.dash", "Между пробелами ставится тире, а не дефис", r"(?<=\S) - (?=\S)", " — "),
    _rule("typo.abbrev_space", "Нет пробела после сокращения", rf"\b({ABBREVIATIONS})\.(?=[\dА-ЯӘҒҚҢӨҰҮҺІ])", r"\1. "),
    _rule("typo.abbrev_space", "Нет пробела после знака номера", r"№(?=\d)", "№ "),
    _rule("typo.year_g", "Год и «г.» разделяются пробелом", r"(?<=\d{4})г\.", " г."),
    _rule("typo.initials", "Инициалы разделяются пробелом", r"(?<=\b[А-ЯӘҒҚҢӨҰҮҺІ]\.)(?=[А-ЯӘҒҚҢӨҰҮҺІ]\.(?!\S))", " ", flags=0,
          condition=lambda m, p, d: not (m.start() >= 2 and p.text[m.start() - 2] == "«")),
]
```
Правило `typo.no_space_after_punct` не может выразить замену лямбдой — вместо этого: `_rule(..., r"(?<=[…»)])([,;])(?=[…«(])", r"\1 ")`; исключения (числа «5,5» и даты) отсекаются самим классом символов (только буквы до и после знака). Для `typo.dash` пример «Нур-Султан» не совпадает, потому что нет пробелов вокруг дефиса. Для `typo.space_before_punct` два шаблона с одним идентификатором — допустимо (в списке два объекта с одинаковым `id`).

`corrector/rules/alphabets.py`:
```python
"""Смешанные алфавиты: латиница внутри кириллического слова и римские цифры кириллицей."""

from __future__ import annotations

import re

from corrector.core.issue import Category, Issue, Level
from corrector.rules.base import Rule, make_issue
from corrector.rules.context import DocContext, ParaContext

LATIN = re.compile(r"[A-Za-z]")
CYRILLIC = re.compile(r"[А-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі]")
LOOKALIKES = {"a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х", "y": "у", "i": "і",
              "A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н", "K": "К", "M": "М", "O": "О", "P": "Р", "T": "Т", "X": "Х", "I": "І"}
ROMAN_CYRILLIC = re.compile(r"(?<![\wА-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі])[ІХV]{1,5}(?![\wА-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі])")
ROMAN_MAP = {"І": "I", "Х": "X", "V": "V"}


def is_mixed(word: str) -> bool:
    return bool(LATIN.search(word)) and bool(CYRILLIC.search(word))


def fix_lookalikes(word: str) -> str | None:
    fixed = []
    for ch in word:
        if LATIN.match(ch):
            if ch not in LOOKALIKES:
                return None
            fixed.append(LOOKALIKES[ch])
        else:
            fixed.append(ch)
    return "".join(fixed)


class MixedAlphabetRule(Rule):
    id, lang, category, level = "alpha.mixed", "any", Category.SPELLING, Level.ERROR
    message = "В слове смешаны латинские и кириллические буквы"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        issues = []
        for token in para.words:
            if is_mixed(token.text):
                fixed = fix_lookalikes(token.text)
                issues.append(make_issue(self, para, token.start, token.end, [fixed] if fixed else []))
        return issues


class RomanNumeralRule(Rule):
    id, lang, category, level = "alpha.roman", "any", Category.TYPOGRAPHY, Level.WARNING
    message = "Римская цифра набрана кириллическими буквами: используйте латинские I, V, X"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        issues = []
        for match in ROMAN_CYRILLIC.finditer(para.text):
            if "І" in match.group() or "Х" in match.group():
                issues.append(make_issue(self, para, match.start(), match.end(), ["".join(ROMAN_MAP[c] for c in match.group())]))
        return issues
```
Правило `alpha.roman` срабатывает только на сочетания из букв І, Х, V без соседних букв (слово «ІІ», «ІV», «ХІ»); одиночная «І» как казахское слово не встречается, но добавить исключение: не срабатывать на одиночную «І»/«Х» без второй буквы, если абзац казахский (`len(match.group()) == 1 and para.lang == "kk"` → пропуск).

В `engine.default_rules`: `rules += TYPOGRAPHY_RULES; rules += [MixedAlphabetRule(), RomanNumeralRule()]`.

- [ ] **Step 4: Запустить тесты** — `.venv/bin/python -m pytest tests/corrector/test_rule_docs.py tests/corrector/test_alphabets.py -q` — проходят все строки таблиц. Подгонять правила под таблицу, а не таблицу под правила; если пример в таблице спорный — обсудить в коммите.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Правила: типографика и смешанные алфавиты с таблицами примеров"`

---

### Task 4: Повторы, длинные предложения, разнобой имён

**Files:**
- Create: `corrector/rules/repeats.py`, `corrector/rules/sentences.py`, `corrector/rules/names.py`, `data/stop_ru.txt`, `data/stop_kk.txt`, `tests/corrector/test_repeats.py`, `tests/corrector/test_names.py`
- Modify: `corrector/rules/engine.py`, `docs/rules-ru.md`, `docs/rules-kk.md`

**Interfaces:**
- Produces:
  - `repeats.DoubleWordRule` (`rep.double`, punctuation? нет — `Category.STYLE`, `Level.ERROR`): одно слово дважды подряд через пробел («в в», «что что»), регистр не важен; исключения `{"было", "всё", "все", "то", "да", "нет"}`? — нет: исключений нет, кроме случаев, когда между словами знак препинания.
  - `repeats.NearRepeatRule` (`rep.near`, style, hint): одно и то же знаменательное слово (лемма для ru через `resources.morph`, основа для kk через `resources.stemmer`) в соседних предложениях одного абзаца; слово длиннее 5 букв, его лемма не в стоп-списке (`stop_ru`/`stop_kk`), не с заглавной буквы. Замечание на второе вхождение, сообщение «Слово «…» уже было в предыдущем предложении».
  - `sentences.LongSentenceRule` (`sent.long`, style, hint): предложение длиннее `settings.sentence_words_limit` слов; сообщение «Предложение из N слов: разбейте на два».
  - `names.NamesConsistencyRule` (`names.variants`, style, warning, document_level): по всему документу собираются слова с заглавной буквы (не в начале предложения, длиной ≥ 4, только буквы) с частотами; для пар с разными написаниями, у которых леммы (ru: `morph.normal_forms[0]`, kk: основа) различны, но расстояние Левенштейна между леммами ≤ 1 (леммы до 7 букв) или ≤ 2 (длиннее), замечание на каждое вхождение более редкого варианта: «Похоже на разное написание одного имени: «Ахмедов» (1) и «Ахметов» (5)» с вариантом замены — частая форма с тем же окончанием, если лемма совпадает по длине, иначе без варианта.
  - `data/stop_ru.txt`, `data/stop_kk.txt`: 300 самых частых слов корпуса каждого языка (снимаются скриптом задачи 10; в этой задаче — посев вручную из списков `lang.RU_WORDS`/`KK_WORDS` плюс `суд, истец, ответчик, статья, решение, дело, сот, талап, шешім, іс, бап`).

- [ ] **Step 1: Таблицы и падающие тесты**

В `docs/rules-ru.md`:
```markdown
## rep.double — Слово повторяется дважды подряд
Категория: style · Уровень: error · Язык: any

| Неправильно | Правильно |
|---|---|
| Суд считает, что что доводы обоснованы. | Суд считает, что доводы обоснованы. |
| Истец в в суд не явился. | Истец в суд не явился. |
| Суд решил, что, что бы ни случилось, иск подлежит удовлетворению. | ✓ |
| 5 5 | ✓ |

## rep.near — Повтор слова в соседних предложениях
Категория: style · Уровень: hint · Язык: ru

| Неправильно | Правильно |
|---|---|
| Ответчик представил возражение. Возражение не мотивировано. | — |
| Суд рассмотрел дело. Суд решил. | ✓ |
| Ахметов явился. Ахметов возражал. | ✓ |

## sent.long — Слишком длинное предложение
Категория: style · Уровень: hint · Язык: any

| Неправильно | Правильно |
|---|---|
| Суд, рассмотрев в открытом судебном заседании гражданское дело по иску товарищества с ограниченной ответственностью к акционерному обществу о взыскании задолженности по договору поставки, пени за просрочку исполнения обязательства, судебных расходов, а также встречный иск акционерного общества к товариществу о признании договора недействительным в части условий о неустойке, установив обстоятельства дела и исследовав представленные сторонами доказательства, приходит к выводу о частичном удовлетворении первоначального иска и об отказе в удовлетворении встречного иска по следующим основаниям, изложенным ниже. | — |
| Суд решил удовлетворить иск. | ✓ |

## names.variants — Разное написание одного имени или названия
Категория: style · Уровень: warning · Язык: any

| Неправильно | Правильно |
|---|---|
| Истец Ахметов подал иск. Ахметов явился. Ответчик Ахмедов не явился. Ахметов настаивал. Ахметов победил. | — |
| Истец Ахметов подал иск. Ахметов явился. Ахметова тоже. | ✓ |
```
В `docs/rules-kk.md`:
```markdown
## rep.near — Көрші сөйлемдерде сөз қайталанады
Категория: style · Уровень: hint · Язык: kk

| Неправильно | Правильно |
|---|---|
| Жауапкер қарсылық білдірді. Қарсылықтың негізі жоқ. | — |
| Сот істі қарады. Сот шешті. | ✓ |
```

`tests/corrector/test_repeats.py`:
```python
from corrector.core import paths
from corrector.core.settings import Settings
from corrector.docx_io import model
from corrector.rules import context, resources
from corrector.rules.repeats import NearRepeatRule
from corrector.rules.sentences import LongSentenceRule
from tests.corrector.conftest import make_docx


def ctx(tmp_path, text, lang="ru", limit=60):
    doc = model.load(make_docx(tmp_path / "п.docx", body=[text]))
    res = resources.load_resources(paths.data_dir(), tmp_path)
    return context.build_contexts(doc, [lang], Settings(sentence_words_limit=limit), res)


def test_near_repeat_uses_lemmas_and_stoplist(tmp_path):
    d = ctx(tmp_path, "Ответчик представил возражение. Возражение не мотивировано.")
    issues = NearRepeatRule().check(d.paragraphs[0], d)
    assert len(issues) == 1 and d.paragraphs[0].text[issues[0].start:issues[0].end] == "Возражение"
    assert "уже было" in issues[0].message
    d = ctx(tmp_path, "Суд рассмотрел дело. Суд решил.")
    assert NearRepeatRule().check(d.paragraphs[0], d) == []


def test_near_repeat_kazakh_stems(tmp_path):
    d = ctx(tmp_path, "Жауапкер қарсылық білдірді. Қарсылықтың негізі жоқ.", "kk")
    assert len(NearRepeatRule().check(d.paragraphs[0], d)) == 1


def test_long_sentence_threshold(tmp_path):
    d = ctx(tmp_path, "раз два три четыре пять шесть. Семь восемь.", limit=5)
    issues = LongSentenceRule().check(d.paragraphs[0], d)
    assert len(issues) == 1 and issues[0].message == "Предложение из 6 слов: разбейте на два"
```

`tests/corrector/test_names.py`:
```python
from corrector.core import paths
from corrector.core.settings import Settings
from corrector.docx_io import model
from corrector.rules import context, resources
from corrector.rules.names import NamesConsistencyRule, levenshtein
from tests.corrector.conftest import make_docx


def test_levenshtein():
    assert levenshtein("ахметов", "ахмедов") == 1 and levenshtein("ак жол", "акжол") == 1 and levenshtein("а", "а") == 0


def test_variants_across_paragraphs(tmp_path):
    doc = model.load(make_docx(tmp_path / "д.docx", body=["Истец Ахметов подал иск.", "Ахметов явился, Ахметов возражал.", "Ответчик Ахмедов не явился."]))
    d = context.build_contexts(doc, ["ru"] * 3, Settings(), resources.load_resources(paths.data_dir(), tmp_path))
    issues = NamesConsistencyRule().check_document(d)
    assert [(i.paragraph, d.paragraphs[i.paragraph].text[i.start:i.end]) for i in issues] == [(2, "Ахмедов")]
    assert "«Ахмедов» (1) и «Ахметов» (3)" in issues[0].message
    assert issues[0].suggestions == ["Ахметов"]


def test_inflected_forms_are_not_variants(tmp_path):
    doc = model.load(make_docx(tmp_path / "д.docx", body=["Истец Ахметов подал иск. Ахметова тоже. Ахметову вручили."]))
    d = context.build_contexts(doc, ["ru"], Settings(), resources.load_resources(paths.data_dir(), tmp_path))
    assert NamesConsistencyRule().check_document(d) == []
```

- [ ] **Step 2: Убедиться, что тесты падают.**

- [ ] **Step 3: Написать правила**

`corrector/rules/repeats.py`:
```python
"""Повторы: слово дважды подряд; одно знаменательное слово в соседних предложениях."""

from __future__ import annotations

import re

from corrector.core.issue import Category, Issue, Level
from corrector.rules.base import Rule, make_issue
from corrector.rules.context import DocContext, ParaContext

DOUBLE_RE = re.compile(r"(?<![\w-])([А-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі]{2,})\s+\1(?![\w-])", re.IGNORECASE)


class DoubleWordRule(Rule):
    id, lang, category, level = "rep.double", "any", Category.STYLE, Level.ERROR
    message = "Слово повторяется дважды подряд"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        return [make_issue(self, para, m.start(), m.end(), [m.group(1)]) for m in DOUBLE_RE.finditer(para.text)]


def lemma(word: str, lang: str, doc: DocContext) -> str:
    if lang == "kk":
        return doc.resources.stemmer.stem(word)
    return doc.resources.morph.parse(word)[0].normal_form


class NearRepeatRule(Rule):
    id, lang, category, level = "rep.near", "any", Category.STYLE, Level.HINT
    message = "Повтор слова в соседних предложениях"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        stop = doc.resources.stop_kk if para.lang == "kk" else doc.resources.stop_ru
        issues, previous = [], {}
        for start, end in para.sentences:
            current = {}
            for token in para.words:
                if not (start <= token.start < end) or len(token.text) <= 5 or token.text[0].isupper():
                    continue
                key = lemma(token.text, para.lang, doc)
                if key in stop or token.text.lower() in stop:
                    continue
                current.setdefault(key, token)
            for key, token in current.items():
                if key in previous:
                    issues.append(make_issue(self, para, token.start, token.end, message=f"Слово «{token.text}» уже было в предыдущем предложении"))
            previous = current
        return issues
```

`corrector/rules/sentences.py`:
```python
"""Длина предложения."""

from __future__ import annotations

from corrector.core.issue import Category, Issue, Level
from corrector.rules.base import Rule, make_issue
from corrector.rules.context import DocContext, ParaContext


class LongSentenceRule(Rule):
    id, lang, category, level = "sent.long", "any", Category.STYLE, Level.HINT
    message = "Слишком длинное предложение"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        limit = doc.settings.sentence_words_limit
        issues = []
        for start, end in para.sentences:
            count = sum(1 for t in para.words if start <= t.start < end)
            if count > limit:
                issues.append(make_issue(self, para, start, end, message=f"Предложение из {count} слов: разбейте на два"))
        return issues
```

`corrector/rules/names.py`:
```python
"""Разнобой имён и названий: похожие, но не одинаковые слова с заглавной буквы в одном документе."""

from __future__ import annotations

from collections import Counter, defaultdict

from corrector.core.issue import Category, Issue, Level
from corrector.core.text import Token
from corrector.rules.base import Rule, make_issue
from corrector.rules.context import DocContext, ParaContext


def levenshtein(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def _lemma(word: str, lang: str, doc: DocContext) -> str:
    if lang == "kk":
        return doc.resources.stemmer.stem(word)
    return doc.resources.morph.parse(word)[0].normal_form


def _is_name(token: Token, para: ParaContext) -> bool:
    text = token.text
    if len(text) < 4 or not text[0].isupper() or not text[1:].islower():
        return False
    sentence = para.sentence_of(token.start)
    return sentence is None or sentence[0] != token.start


class NamesConsistencyRule(Rule):
    id, lang, category, level = "names.variants", "any", Category.STYLE, Level.WARNING
    message = "Похоже на разное написание одного имени"
    document_level = True

    def check_document(self, doc: DocContext) -> list[Issue]:
        occurrences: dict[str, list[tuple[ParaContext, Token]]] = defaultdict(list)
        lemmas: dict[str, str] = {}
        for para in doc.paragraphs:
            for token in para.words:
                if _is_name(token, para):
                    occurrences[token.text].append((para, token))
                    lemmas.setdefault(token.text, _lemma(token.text, para.lang, doc))
        counts = Counter({form: len(items) for form, items in occurrences.items()})
        by_lemma: dict[str, int] = defaultdict(int)
        for form, n in counts.items():
            by_lemma[lemmas[form]] += n
        issues: list[Issue] = []
        lemma_list = sorted(by_lemma, key=lambda l: -by_lemma[l])
        for i, rare in enumerate(lemma_list):
            for frequent in lemma_list[:i]:
                limit = 1 if len(rare) <= 7 else 2
                if by_lemma[frequent] > by_lemma[rare] and levenshtein(rare, frequent) <= limit:
                    frequent_form = max((f for f in counts if lemmas[f] == frequent), key=counts.get)
                    for form in (f for f in counts if lemmas[f] == rare):
                        suggestion = [frequent_form] if len(form) == len(frequent_form) else []
                        for para, token in occurrences[form]:
                            issues.append(make_issue(self, para, token.start, token.end, suggestion,
                                          f"Похоже на разное написание одного имени: «{form}» ({by_lemma[rare]}) и «{frequent_form}» ({by_lemma[frequent]})"))
                    break
        return issues
```

`data/stop_ru.txt` — посев: слова из `lang.RU_WORDS` плюс `суд, истец, ответчик, статья, статьи, решение, решения, дело, дела, заявление, договор, договора, требование, требования, кодекс, кодекса, республика, республики, казахстан, суда, судебный, судебного, заседание, заседания, лицо, лица, порядок, порядке, срок, срока`; `data/stop_kk.txt` — из `lang.KK_WORDS` плюс `сот, сотының, талап, талапкер, жауапкер, шешім, шешімі, іс, істі, бап, бабы, кодекс, кодексі, республика, республикасы, қазақстан, арыз, шарт, талаптар, мерзім, тәртіп, тұлға`. Стоп-списки берутся в нижнем регистре.

В `engine.default_rules`: `rules += [DoubleWordRule(), NearRepeatRule(), LongSentenceRule(), NamesConsistencyRule()]`.

- [ ] **Step 4: Запустить тесты** — `.venv/bin/python -m pytest tests/corrector -q` — проходят. Если `rep.near` для казахского не видит повтор из-за разных основ («қарсылық» и «Қарсылықтың»: вторая с заглавной буквы отсекается условием `token.text[0].isupper()`) — в таблице kk сделать второе вхождение строчным: «Жауапкер қарсылық білдірді. Бұл қарсылықтың негізі жоқ.».

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Правила: повторы, длинные предложения, разнобой имён по документу"`

---

### Task 5: Эталонные названия органов и законов

**Files:**
- Create: `corrector/rules/official.py`, `data/names_official_ru.txt`, `data/names_official_kk.txt`, `tests/corrector/test_official.py`
- Modify: `corrector/rules/engine.py`, `docs/rules-ru.md`, `docs/rules-kk.md`

**Interfaces:**
- Produces: `official.OfficialNamesRule` (`names.official`, style, hint): для каждого эталонного названия из ресурсов (списки по языку) ищет в абзаце фрагменты, начинающиеся с того же первого слова (регистр не важен) и той же длины в словах; если фрагмент отличается от эталона (регистр букв или 1–2 символа при коэффициенте сходства `difflib.SequenceMatcher(...).ratio() >= 0.85`), замечание с вариантом — эталон. Точное совпадение — тишина. Эталоны длиной от двух слов.

- [ ] **Step 1: Данные, таблицы, падающие тесты**

`data/names_official_ru.txt`:
```
# Эталонные названия органов и законов (русский). Одно название на строку; сверка по словам.
Верховный Суд Республики Казахстан
Конституция Республики Казахстан
Гражданский кодекс Республики Казахстан
Гражданский процессуальный кодекс Республики Казахстан
Уголовный кодекс Республики Казахстан
Уголовно-процессуальный кодекс Республики Казахстан
Кодекс Республики Казахстан об административных правонарушениях
Административный процедурно-процессуальный кодекс Республики Казахстан
Налоговый кодекс Республики Казахстан
Трудовой кодекс Республики Казахстан
Земельный кодекс Республики Казахстан
Предпринимательский кодекс Республики Казахстан
Бюджетный кодекс Республики Казахстан
Экологический кодекс Республики Казахстан
Социальный кодекс Республики Казахстан
Кодекс Республики Казахстан о браке (супружестве) и семье
Уголовно-исполнительный кодекс Республики Казахстан
Водный кодекс Республики Казахстан
Лесной кодекс Республики Казахстан
Генеральная прокуратура Республики Казахстан
Министерство юстиции Республики Казахстан
Министерство внутренних дел Республики Казахстан
Министерство финансов Республики Казахстан
Агентство Республики Казахстан по защите и развитию конкуренции
Агентство Республики Казахстан по делам государственной службы
Агентство Республики Казахстан по финансовому мониторингу
Национальный Банк Республики Казахстан
Судебная администрация Республики Казахстан
Высший Судебный Совет Республики Казахстан
```
`data/names_official_kk.txt`:
```
# Эталонные названия (казахский).
Қазақстан Республикасының Жоғарғы Соты
Қазақстан Республикасының Конституциясы
Қазақстан Республикасының Азаматтық кодексі
Қазақстан Республикасының Азаматтық процестік кодексі
Қазақстан Республикасының Қылмыстық кодексі
Қазақстан Республикасының Қылмыстық-процестік кодексі
Қазақстан Республикасының Әкімшілік құқық бұзушылық туралы кодексі
Қазақстан Республикасының Әкімшілік рәсімдік-процестік кодексі
Қазақстан Республикасының Салық кодексі
Қазақстан Республикасының Еңбек кодексі
Қазақстан Республикасының Жер кодексі
Қазақстан Республикасының Кәсіпкерлік кодексі
Қазақстан Республикасының Бюджет кодексі
Қазақстан Республикасының Экологиялық кодексі
Қазақстан Республикасының Әлеуметтік кодексі
Қазақстан Республикасының Неке (ерлі-зайыптылық) және отбасы туралы кодексі
Қазақстан Республикасының Бас прокуратурасы
Қазақстан Республикасының Әділет министрлігі
Қазақстан Республикасының Ішкі істер министрлігі
Қазақстан Республикасының Қаржы министрлігі
Қазақстан Республикасының Ұлттық Банкі
Қазақстан Республикасының Жоғары Сот Кеңесі
```
В `docs/rules-ru.md`:
```markdown
## names.official — Название органа или закона отличается от официального
Категория: style · Уровень: hint · Язык: ru

| Неправильно | Правильно |
|---|---|
| согласно Гражданскому Процессуальному Кодексу Республики Казахстан | согласно Гражданский процессуальный кодекс Республики Казахстан |
| постановление Верховного суда Республики Казахстан | постановление Верховный Суд Республики Казахстан |
| постановление Верховного Суда Республики Казахстан | ✓ |
| Гражданский процессуальный кодекс Республики Казахстан | ✓ |
```
Замечание указывает на отличие и предлагает эталон в именительном падеже (склонение оставляем человеку: подсказка, не ошибка); поэтому в «Правильно» стоит эталон без склонения. В `docs/rules-kk.md`:
```markdown
## names.official — Мекеме немесе заң атауы ресми атаудан өзгеше
Категория: style · Уровень: hint · Язык: kk

| Неправильно | Правильно |
|---|---|
| Қазақстан Республикасының Жоғарғы соты | Қазақстан Республикасының Жоғарғы Соты |
| Қазақстан Республикасының Жоғарғы Соты | ✓ |
```

`tests/corrector/test_official.py`:
```python
from corrector.rules.official import find_candidates


def test_find_candidates_matches_by_first_word_and_length():
    text = "постановление Верховного суда Республики Казахстан от 1 января"
    found = find_candidates(text, "Верховный Суд Республики Казахстан")
    assert [text[s:e] for s, e in found] == ["Верховного суда Республики Казахстан"]


def test_similarity_threshold():
    from corrector.rules.official import similar
    assert similar("Верховного суда Республики Казахстан", "Верховный Суд Республики Казахстан")
    assert not similar("Верховный Суд Российской Федерации", "Верховный Суд Республики Казахстан")
```

- [ ] **Step 2: Убедиться, что тесты падают.**

- [ ] **Step 3: Написать правило**

`corrector/rules/official.py`:
```python
"""Сверка названий органов и законов с эталонным списком."""

from __future__ import annotations

import difflib
import re

from corrector.core.issue import Category, Issue, Level
from corrector.core.text import words
from corrector.rules.base import Rule, make_issue
from corrector.rules.context import DocContext, ParaContext


def _stem4(word: str) -> str:
    return word.lower()[:4]


def find_candidates(text: str, canonical: str) -> list[tuple[int, int]]:
    """Отрезки текста той же длины в словах, что эталон, начинающиеся с того же слова (по первым буквам)."""
    canon_words = words(canonical)
    text_words = words(text)
    n = len(canon_words)
    result = []
    for i in range(len(text_words) - n + 1):
        window = text_words[i:i + n]
        if _stem4(window[0].text) == _stem4(canon_words[0].text) and _stem4(window[-1].text) == _stem4(canon_words[-1].text):
            result.append((window[0].start, window[-1].end))
    return result


def similar(fragment: str, canonical: str) -> bool:
    return difflib.SequenceMatcher(None, fragment.lower(), canonical.lower()).ratio() >= 0.85


class OfficialNamesRule(Rule):
    id, lang, category, level = "names.official", "any", Category.STYLE, Level.HINT
    message = "Название отличается от официального"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        canon_list = doc.resources.official_kk if para.lang == "kk" else doc.resources.official_ru
        issues, taken = [], []
        for canonical in canon_list:
            for start, end in find_candidates(para.text, canonical):
                fragment = para.text[start:end]
                if fragment == canonical or any(s <= start < e for s, e in taken):
                    continue
                if similar(fragment, canonical) and re.sub(r"\W", "", fragment) != re.sub(r"\W", "", canonical):
                    issues.append(make_issue(self, para, start, end, [canonical], f"Официальное название: «{canonical}»"))
                    taken.append((start, end))
                elif fragment != canonical and re.sub(r"\W", "", fragment).lower() == re.sub(r"\W", "", canonical).lower():
                    issues.append(make_issue(self, para, start, end, [canonical], f"Регистр букв: официально «{canonical}»"))
                    taken.append((start, end))
        return issues
```
Условие: отличающийся регистр («Верховного суда» → «Верховный Суд») — замечание; отличие в 1–2 буквах при сходстве ≥ 0,85 — замечание; склонение эталона («Гражданскому процессуальному кодексу») тоже проходит порог сходства и получает замечание с эталоном в именительном падеже — это шум. Чтобы его отсечь: считать фрагмент допустимым, если после приведения обоих к «основам слов» (первые 5 букв каждого слова, регистр как есть у эталона для слов из ≥ 2 букв…) они совпадают. Реализовать `_key(s) = " ".join(w.text[:5] for w in words(s))` с учётом регистра первой буквы: фрагмент считается верным, если `_key(fragment) == _key(canonical)`; замечание, если ключи различаются только регистром (сообщение про регистр) или похожи по `similar` (сообщение про написание). Таблица docs подстраивается под это: «Гражданскому Процессуальному Кодексу» (регистр) — замечание; «Гражданскому процессуальному кодексу Республики Казахстан» — `✓`.

В `engine.default_rules`: `rules.append(OfficialNamesRule())`.

- [ ] **Step 4: Запустить тесты** — проходят; добавить в таблицу ru строку `| согласно Гражданскому процессуальному кодексу Республики Казахстан | ✓ |`.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Правила: сверка названий органов и законов с эталонным списком"`

---

### Task 6: Русские юридические шаблоны и запятая перед союзом

**Files:**
- Create: `corrector/rules/legal_ru.py`, `tests/corrector/test_legal_ru.py`
- Modify: `corrector/rules/engine.py`, `docs/rules-ru.md`

**Interfaces:**
- Produces: `legal_ru.LEGAL_RU_RULES: list[Rule]`:
  - `legal.sootvetstvie` (grammar, error, PatternRule): «в соответствие с/со» → «в соответствии с/со», кроме «привести/приведение/приводить … в соответствие с».
  - `legal.soglasno` (grammar, error, Rule с морфологией): после «согласно» существительное или прилагательное в родительном падеже (по `morph`, если разбор с `gent` идёт первым и нет варианта `datv`) → вариант в дательном падеже (`parse.inflect({"datv"})`); «согласно приказа» → «согласно приказу», «согласно статьи 5» → «согласно статье 5»; «согласно решению» — тишина.
  - `legal.v_techenie` (grammar, error, PatternRule): «в течении» + слово в родительном падеже времени (срока, месяца, дней, года, лет, недели, часов, суток, времени, периода) → «в течение …».
  - `legal.oplatit_za` (grammar, warning): «оплатить/оплатил/оплачивает … за» → без «за» — уже есть у LanguageTool (`Upotreblenije_predlogov`): не дублировать; не делать.
  - `punct.comma_conj` (punctuation, error, Rule): перед союзами «что», «чтобы», «который/которая/которое/которые/которого/которой/которым/которых/которую», «если», «поскольку», «так как», «потому что», «хотя», «когда» (в середине предложения) нет запятой, а предыдущий токен — слово (не знак, не начало предложения) и не из списка исключений `{"то", "вот", "не", "а", "и", "лишь", "только", "едва", "потому", "так", "разве", "ли", "как", "тем", "прежде", "после", "до", "перед", "затем", "в", "о", "об", "при", "для"}`; «так как» и «потому что» проверяются как целое; вариант — вставка запятой: замечание на пробел перед союзом с вариантом «, ».
- Все правила русские (`lang="ru"`).

- [ ] **Step 1: Таблицы и падающие тесты**

В `docs/rules-ru.md`:
```markdown
## legal.sootvetstvie — «В соответствие с» вместо «в соответствии с»
Категория: grammar · Уровень: error · Язык: ru

| Неправильно | Правильно |
|---|---|
| Действуя в соответствие с законом, суд решил. | Действуя в соответствии с законом, суд решил. |
| Привести устав в соответствие с законом. | ✓ |
| Действуя в соответствии с законом. | ✓ |

## legal.soglasno — «Согласно» с родительным падежом
Категория: grammar · Уровень: error · Язык: ru

| Неправильно | Правильно |
|---|---|
| Согласно приказа директора. | Согласно приказу директора. |
| согласно статьи 5 Кодекса | согласно статье 5 Кодекса |
| согласно решению суда | ✓ |
| согласно договору поставки | ✓ |

## legal.v_techenie — «В течении срока» вместо «в течение срока»
Категория: grammar · Уровень: error · Язык: ru

| Неправильно | Правильно |
|---|---|
| оплатить в течении 10 дней | оплатить в течение 10 дней |
| в течении месяца | в течение месяца |
| в течении реки | ✓ |
| в течение месяца | ✓ |

## punct.comma_conj — Нет запятой перед союзом
Категория: punctuation · Уровень: error · Язык: ru

| Неправильно | Правильно |
|---|---|
| Суд считает что доводы обоснованы. | Суд считает, что доводы обоснованы. |
| Договор который заключён сторонами. | Договор, который заключён сторонами. |
| Иск удовлетворить если ответчик не явится. | Иск удовлетворить, если ответчик не явится. |
| Суд считает, что доводы обоснованы. | ✓ |
| Суд решил то что положено. | ✓ |
| Не что иное как ошибка. | ✓ |
| Что суд решил. | ✓ |
```

`tests/corrector/test_legal_ru.py`:
```python
from corrector.core import paths
from corrector.core.settings import Settings
from corrector.docx_io import model
from corrector.rules import context, resources
from corrector.rules.legal_ru import CommaBeforeConjunctionRule, SoglasnoRule
from tests.corrector.conftest import make_docx


def ctx(tmp_path, text):
    doc = model.load(make_docx(tmp_path / "п.docx", body=[text]))
    return context.build_contexts(doc, ["ru"], Settings(), resources.load_resources(paths.data_dir(), tmp_path))


def test_soglasno_inflects_to_dative(tmp_path):
    d = ctx(tmp_path, "Согласно приказа директора и согласно статьи 5.")
    issues = SoglasnoRule().check(d.paragraphs[0], d)
    assert [(d.paragraphs[0].text[i.start:i.end], i.suggestions) for i in issues] == [("приказа", ["приказу"]), ("статьи", ["статье"])]


def test_comma_rule_positions_and_exceptions(tmp_path):
    d = ctx(tmp_path, "Суд считает что доводы обоснованы, а то что сказано, неважно.")
    issues = CommaBeforeConjunctionRule().check(d.paragraphs[0], d)
    assert len(issues) == 1
    i = issues[0]
    assert d.paragraphs[0].text[i.start:i.end] == " " and i.suggestions == [", "] and i.end == d.paragraphs[0].text.index("что")
```

- [ ] **Step 2: Убедиться, что тесты падают.**

- [ ] **Step 3: Написать правила**

`corrector/rules/legal_ru.py`:
```python
"""Русские юридические шаблоны там, где LanguageTool молчит."""

from __future__ import annotations

import re

from corrector.core.issue import Category, Issue, Level
from corrector.rules.base import Rule, make_issue
from corrector.rules.context import DocContext, ParaContext
from corrector.rules.patterns import PatternRule

TIME_WORDS = r"(?:срока|месяца|месяцев|дня|дней|года|лет|недели|недель|часа|часов|суток|времени|периода|квартала|\d+)"
CONJUNCTIONS = {"что", "чтобы", "который", "которая", "которое", "которые", "которого", "которой", "которым", "которых",
                "которую", "которому", "если", "поскольку", "хотя", "когда"}
PAIRS = {("так", "как"), ("потому", "что")}
EXCEPTIONS = {"то", "вот", "не", "а", "и", "лишь", "только", "едва", "потому", "так", "разве", "ли", "как", "тем",
              "прежде", "после", "до", "перед", "затем", "в", "о", "об", "при", "для", "на", "за", "из", "с", "иное"}


def _not_after_privesti(match, para, doc):
    before = para.text[:match.start()].lower()
    return not re.search(r"(привест|привед|приводи|соответств\w* привед)\w*\s*(в|его|их|её|документ\w*|устав\w*)?\s*$", before[-60:])


SOOTVETSTVIE = PatternRule("legal.sootvetstvie", "ru", Category.GRAMMAR, Level.ERROR, "Правильно: «в соответствии с»",
                           r"\bв соответствие (с|со)\b", r"в соответствии \1", condition=_not_after_privesti)
V_TECHENIE = PatternRule("legal.v_techenie", "ru", Category.GRAMMAR, Level.ERROR, "О сроке пишется «в течение»",
                         rf"\bв течении(?= {TIME_WORDS}\b)", "в течение")


class SoglasnoRule(Rule):
    id, lang, category, level = "legal.soglasno", "ru", Category.GRAMMAR, Level.ERROR
    message = "После «согласно» — дательный падеж"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        issues = []
        for i, token in enumerate(para.words[:-1]):
            if token.text.lower() != "согласно":
                continue
            following = para.words[i + 1]
            parses = doc.resources.morph.parse(following.text)
            if not parses or parses[0].tag.POS not in ("NOUN", "ADJF", "PRTF") or "gent" not in parses[0].tag:
                continue
            if any("datv" in p.tag for p in parses):
                continue
            dative = parses[0].inflect({"datv"})
            suggestion = [dative.word] if dative else []
            issues.append(make_issue(self, para, following.start, following.end, suggestion))
        return issues


class CommaBeforeConjunctionRule(Rule):
    id, lang, category, level = "punct.comma_conj", "ru", Category.PUNCTUATION, Level.ERROR
    message = "Перед союзом нужна запятая"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        issues = []
        tokens = [t for t in para.tokens if t.kind != "space"]
        for i, token in enumerate(tokens):
            lowered = token.text.lower()
            if token.kind != "word" or i == 0:
                continue
            previous = tokens[i - 1]
            if previous.kind != "word":
                continue
            sentence = para.sentence_of(token.start)
            if sentence and sentence[0] == token.start:
                continue
            pair = (lowered, tokens[i + 1].text.lower()) if i + 1 < len(tokens) else None
            if pair in PAIRS:
                conjunction_ok = True
            elif lowered in CONJUNCTIONS:
                conjunction_ok = True
            else:
                continue
            if previous.text.lower() in EXCEPTIONS or (pair not in PAIRS and lowered == "как"):
                continue
            gap_start, gap_end = previous.end, token.start
            if para.text[gap_start:gap_end].strip() == "" and gap_end > gap_start:
                issues.append(make_issue(self, para, gap_start, gap_end, [", "]))
        return issues


LEGAL_RU_RULES: list[Rule] = [SOOTVETSTVIE, V_TECHENIE, SoglasnoRule(), CommaBeforeConjunctionRule()]
```
Оговорки: `CommaBeforeConjunctionRule` не срабатывает, если между словом и союзом нет пробела (например, кавычка или скобка); при «то, что» предыдущий токен — запятая, значит `previous.kind != "word"` и правило молчит; «Суд решил то что положено» — предыдущее слово «то» в исключениях. Для «так как» пара проверяется по первому слову «так» — но «так» само в исключениях для одиночного «как»; порядок проверок: сначала пара.

В `engine.default_rules`: `rules += LEGAL_RU_RULES`.

- [ ] **Step 4: Запустить тесты** — `.venv/bin/python -m pytest tests/corrector -q` — проходят; при расхождении в склонении («статьи» → pymorphy3 даёт «статье») сверить фактический вывод и поправить таблицу только если морфология права.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Правила: русские юридические шаблоны, согласно + дательный, запятая перед союзом"`

---

### Task 7: Казахская пунктуация и дефисы

**Files:**
- Create: `corrector/rules/punct_kk.py`, `tests/corrector/test_punct_kk.py`
- Modify: `corrector/rules/engine.py`, `docs/rules-kk.md`

**Interfaces:**
- Produces: `punct_kk.PUNCT_KK_RULES: list[Rule]` (все `lang="kk"`):
  - `kk.comma_conj` (punctuation, error, Rule): перед союзами «бірақ», «алайда», «дегенмен», «әйтпесе», «әйткенмен», «себебі», «өйткені», «сондықтан» и сочетаниями «сонда да», «сол себепті» в середине предложения нет запятой, предыдущий токен — слово → вариант «, » (аналогично русскому правилу, без исключений кроме «тек», «бірақ та»).
  - `kk.comma_intro` (punctuation, error, Rule): вводное слово в начале предложения без запятой после него: «Алайда», «Дегенмен», «Сондықтан», «Мысалы», «Әрине», «Демек», «Сонымен», «Біріншіден», «Екіншіден», «Үшіншіден», «Әлбетте», «Шамасы», «Меніңше», «Осылайша», «Сонымен қатар», «Бұдан басқа», «Жалпы алғанда», «Атап айтқанда»; вариант — вставка «, » после слова.
  - `kk.da_de` (punctuation, hint, Rule): повторяющиеся частицы «да/де/та/те» в одном предложении («X да Y да») без запятой между частями → подсказка «При повторяющихся да/де ставится запятая» (без автозамены).
  - `kk.hyphen_ordinal` (typography, error, PatternRule): число + пробел + «бап|тармақ|тармақша|бөлім|тарау|сынып|қабат|орын|топ|санат|деңгей|курс|кезең» (+ аффиксы) → дефис: «5 бап» → «5-бап», «2 тармақтың» → «2-тармақтың» (emle, дефис § 3).
  - `kk.hyphen_suffix` (typography, error, PatternRule): число + пробел + порядковый или падежный аффикс «ші|шы|нші|ншы|ке|ге|қа|ға|та|те|да|де|ты|ті|ды|ді|тан|тен|дан|ден|нан|нен|ның|нің|дың|дің|тың|тің» как отдельное «слово» (2–4 буквы) → «5-ші», «5-ке» (emle § 4).
  - `kk.hyphen_abbrev` (typography, error, PatternRule): аббревиатура заглавными (2–6 букв, допускается одна строчная) + аффикс строчными без дефиса («ҚРның», «ЖШСке») → «ҚР-ның», «ЖШС-ке» (emle § 7).

- [ ] **Step 1: Таблицы и падающие тесты**

В `docs/rules-kk.md`:
```markdown
## kk.comma_conj — Жалғаулықтың алдында үтір жоқ
Категория: punctuation · Уровень: error · Язык: kk

| Неправильно | Правильно |
|---|---|
| Талап қоюшы келді бірақ жауапкер келмеді. | Талап қоюшы келді, бірақ жауапкер келмеді. |
| Іс тоқтатылды себебі талап қоюшы бас тартты. | Іс тоқтатылды, себебі талап қоюшы бас тартты. |
| Шарт жарамсыз сондықтан талап қанағаттандырылмайды. | Шарт жарамсыз, сондықтан талап қанағаттандырылмайды. |
| Талап қоюшы келді, бірақ жауапкер келмеді. | ✓ |
| Бірақ жауапкер келмеді. | ✓ |

## kk.comma_intro — Қыстырма сөзден кейін үтір жоқ
Категория: punctuation · Уровень: error · Язык: kk

| Неправильно | Правильно |
|---|---|
| Алайда жауапкер келмеді. | Алайда, жауапкер келмеді. |
| Сондықтан талап қанағаттандырылмайды. | Сондықтан, талап қанағаттандырылмайды. |
| Мысалы шарт бойынша. | Мысалы, шарт бойынша. |
| Алайда, жауапкер келмеді. | ✓ |
| Сонымен қатар талап қоюшы. | Сонымен қатар, талап қоюшы. |

## kk.da_de — Қайталанатын да/де шылауы
Категория: punctuation · Уровень: hint · Язык: kk

| Неправильно | Правильно |
|---|---|
| Талап қоюшы да жауапкер де келмеді. | — |
| Талап қоюшы да, жауапкер де келмеді. | ✓ |

## kk.hyphen_ordinal — Сан мен зат есім арасында дефис жоқ
Категория: typography · Уровень: error · Язык: kk

| Неправильно | Правильно |
|---|---|
| Кодекстің 5 бабы | Кодекстің 5-бабы |
| 2 тармақтың талабы | 2-тармақтың талабы |
| Кодекстің 5-бабы | ✓ |
| 5 адам келді | ✓ |

## kk.hyphen_suffix — Саннан кейінгі қосымша дефиссіз
Категория: typography · Уровень: error · Язык: kk

| Неправильно | Правильно |
|---|---|
| 5 ші қабат | 5-ші қабат |
| 2024 тен бастап | 2024-тен бастап |
| 5-ші қабат | ✓ |

## kk.hyphen_abbrev — Қысқарған сөзге қосымша дефиссіз жалғанған
Категория: typography · Уровень: error · Язык: kk

| Неправильно | Правильно |
|---|---|
| ҚРның заңы | ҚР-ның заңы |
| ЖШСке қатысты | ЖШС-ке қатысты |
| ҚР-ның заңы | ✓ |
| ЖШС қатысты | ✓ |
```

`tests/corrector/test_punct_kk.py`:
```python
from corrector.core import paths
from corrector.core.settings import Settings
from corrector.docx_io import model
from corrector.rules import context, resources
from corrector.rules.punct_kk import CommaBeforeConjunctionKkRule, IntroCommaKkRule
from tests.corrector.conftest import make_docx


def ctx(tmp_path, text):
    doc = model.load(make_docx(tmp_path / "п.docx", body=[text]))
    return context.build_contexts(doc, ["kk"], Settings(), resources.load_resources(paths.data_dir(), tmp_path))


def test_conjunction_pairs_and_sentence_start(tmp_path):
    d = ctx(tmp_path, "Шарт жарамсыз сол себепті талап қанағаттандырылмайды. Бірақ бұл маңызды емес.")
    issues = CommaBeforeConjunctionKkRule().check(d.paragraphs[0], d)
    assert len(issues) == 1 and d.paragraphs[0].text[issues[0].end:].startswith("сол себепті")


def test_intro_only_at_sentence_start(tmp_path):
    d = ctx(tmp_path, "Сот, мысалы, шартты қарады. Мысалы шарт бойынша.")
    issues = IntroCommaKkRule().check(d.paragraphs[0], d)
    assert len(issues) == 1 and d.paragraphs[0].text[issues[0].start:issues[0].end] == " "
```

- [ ] **Step 2: Убедиться, что тесты падают.**

- [ ] **Step 3: Написать правила**

`corrector/rules/punct_kk.py`:
```python
"""Казахская пунктуация и дефисы по правилам emle.kz (үтір § 2, § 10; дефис § 3, § 4, § 7)."""

from __future__ import annotations

import re

from corrector.core.issue import Category, Issue, Level
from corrector.rules.base import Rule, make_issue
from corrector.rules.context import DocContext, ParaContext
from corrector.rules.patterns import PatternRule

CONJUNCTIONS = {"бірақ", "алайда", "дегенмен", "әйтпесе", "әйткенмен", "себебі", "өйткені", "сондықтан"}
CONJ_PAIRS = {("сонда", "да"), ("сол", "себепті")}
INTRO = {"алайда", "дегенмен", "сондықтан", "мысалы", "әрине", "демек", "сонымен", "біріншіден", "екіншіден",
         "үшіншіден", "әлбетте", "шамасы", "меніңше", "осылайша"}
INTRO_PAIRS = {("сонымен", "қатар"), ("бұдан", "басқа"), ("жалпы", "алғанда"), ("атап", "айтқанда")}
PARTICLES = {"да", "де", "та", "те"}
NOUNS_AFTER_NUMBER = r"(?:бап|тармақ|тармақша|бөлім|тарау|сынып|қабат|орын|топ|санат|деңгей|курс|кезең)"
SUFFIXES = r"(?:н?ші|н?шы|ке|ге|қа|ға|та|те|да|де|ты|ті|ды|ді|тан|тен|дан|ден|нан|нен|ның|нің|дың|дің|тың|тің)"


def _nonspace(para: ParaContext):
    return [t for t in para.tokens if t.kind != "space"]


class CommaBeforeConjunctionKkRule(Rule):
    id, lang, category, level = "kk.comma_conj", "kk", Category.PUNCTUATION, Level.ERROR
    message = "Перед союзом нужна запятая"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        issues, tokens = [], _nonspace(para)
        for i, token in enumerate(tokens):
            if i == 0 or token.kind != "word" or tokens[i - 1].kind != "word":
                continue
            lowered = token.text.lower()
            following = tokens[i + 1].text.lower() if i + 1 < len(tokens) else ""
            if not (lowered in CONJUNCTIONS or (lowered, following) in CONJ_PAIRS):
                continue
            sentence = para.sentence_of(token.start)
            if sentence and sentence[0] == token.start:
                continue
            gap = para.text[tokens[i - 1].end:token.start]
            if gap.strip() == "" and gap:
                issues.append(make_issue(self, para, tokens[i - 1].end, token.start, [", "]))
        return issues


class IntroCommaKkRule(Rule):
    id, lang, category, level = "kk.comma_intro", "kk", Category.PUNCTUATION, Level.ERROR
    message = "После вводного слова в начале предложения нужна запятая"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        issues, tokens = [], _nonspace(para)
        starts = {s for s, _ in para.sentences}
        for i, token in enumerate(tokens):
            if token.kind != "word" or token.start not in starts or i + 1 >= len(tokens):
                continue
            lowered = token.text.lower()
            following = tokens[i + 1]
            if (lowered, following.text.lower()) in INTRO_PAIRS and i + 2 < len(tokens):
                last, nxt = following, tokens[i + 2]
            elif lowered in INTRO:
                last, nxt = token, following
            else:
                continue
            if nxt.kind == "punct":
                continue
            gap = para.text[last.end:nxt.start]
            if gap.strip() == "" and gap:
                issues.append(make_issue(self, para, last.end, nxt.start, [", "]))
        return issues


class RepeatedParticleKkRule(Rule):
    id, lang, category, level = "kk.da_de", "kk", Category.PUNCTUATION, Level.HINT
    message = "При повторяющихся частицах да/де/та/те между частями ставится запятая"

    def check(self, para: ParaContext, doc: DocContext) -> list[Issue]:
        issues = []
        for start, end in para.sentences:
            tokens = [t for t in _nonspace(para) if start <= t.start < end]
            positions = [i for i, t in enumerate(tokens) if t.kind == "word" and t.text.lower() in PARTICLES]
            if len(positions) < 2:
                continue
            first, second = positions[0], positions[1]
            between = tokens[first + 1:second]
            if between and all(t.kind == "word" for t in between):
                issues.append(make_issue(self, para, tokens[first].start, tokens[second].end))
        return issues


HYPHEN_RULES = [
    PatternRule("kk.hyphen_ordinal", "kk", Category.TYPOGRAPHY, Level.ERROR, "Между числом и словом ставится дефис: «5-бап»",
                rf"\b(\d+) ({NOUNS_AFTER_NUMBER}[а-яәғқңөұүһі]*)\b", r"\1-\2", flags=0),
    PatternRule("kk.hyphen_suffix", "kk", Category.TYPOGRAPHY, Level.ERROR, "Аффикс после числа пишется через дефис: «5-ші»",
                rf"\b(\d+) ({SUFFIXES})\b", r"\1-\2", flags=0),
    PatternRule("kk.hyphen_abbrev", "kk", Category.TYPOGRAPHY, Level.ERROR, "Аффикс к аббревиатуре пишется через дефис: «ҚР-ның»",
                r"\b([А-ЯӘҒҚҢӨҰҮҺІ]{2,6})([а-яәғқңөұүһі]{2,4})\b", r"\1-\2", flags=0,
                condition=lambda m, p, d: m.group(2) in {"ның", "нің", "дың", "дің", "тың", "тің", "ке", "ге", "қа", "ға",
                                                          "та", "те", "да", "де", "ты", "ті", "ды", "ді", "тан", "тен",
                                                          "дан", "ден", "нан", "нен", "мен", "бен", "пен"}),
]

PUNCT_KK_RULES: list[Rule] = [CommaBeforeConjunctionKkRule(), IntroCommaKkRule(), RepeatedParticleKkRule(), *HYPHEN_RULES]
```
В `engine.default_rules`: `rules += PUNCT_KK_RULES`. `kk.hyphen_abbrev` не должно срабатывать на обычные слова из заглавных букв внутри слова с одной строчной («АҚБтК») — условие требует, чтобы хвост был именно аффиксом из списка.

- [ ] **Step 4: Запустить тесты** — проходят; строки таблиц kk проверяются на `lang="kk"`.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Правила: казахская пунктуация (союзы, вводные, да/де) и дефисы по emle.kz"`

---

### Task 8: Правила в конвейере и командной строке

**Files:**
- Modify: `corrector/engines/factory.py` (ресурсы правил и `RulesEngine` в `Engines`), `corrector/engines/pipeline.py` (прогон правил), `corrector/cli.py` (вывод ошибок `правила.yaml` в stderr и отчёт), `tests/corrector/test_pipeline.py` (+ тест), `tests/corrector/test_cli.py` (+ тест), `README.md`

**Interfaces:**
- Produces: `Engines.rules: RulesEngine`, `Engines.rule_resources: RuleResources`; `build_engines(..., user_dir: Path | None = None)` загружает `правила.yaml` из `user_dir` (по умолчанию `paths.user_dir()`); `pipeline.check_document` после словарных движков строит `DocContext` и добавляет замечания правил; `Engines.statuses()` включает `EngineStatus("rules", True, "правил: N; ошибок в правила.yaml: M")`; `cli` печатает ошибки правил пользователя в stderr одной строкой на ошибку.

- [ ] **Step 1: Падающие тесты**

Добавить в `tests/corrector/test_pipeline.py`:
```python
def test_rules_run_in_pipeline_and_win_over_lt(tmp_path):
    path = make_docx(tmp_path / "а.docx", body=["Суд  решил что иск обоснован."])
    doc = model.load(path)
    engines = build(tmp_path, FakeRu())
    try:
        issues = pipeline.check_document(doc, engines, UserDictionary(tmp_path / "словарь.txt"), Settings())
    finally:
        engines.close()
    ids = {i.rule_id for i in issues}
    assert {"typo.double_space", "punct.comma_conj"} <= ids
    assert all(i.engine in ("rules", "lt") for i in issues)


def test_user_rules_loaded_from_user_dir(tmp_path):
    (tmp_path / "правила.yaml").write_text("- id: тнг\n  найти: тнг\n  заменить: тенге\n  сообщение: 'Пишите «тенге»'\n", encoding="utf-8")
    path = make_docx(tmp_path / "а.docx", body=["Сумма 500 тнг взыскана."])
    doc = model.load(path)
    engines = factory.build_engines(UserDictionary(tmp_path / "словарь.txt"), no_lt=True, user_dir=tmp_path)
    try:
        issues = pipeline.check_document(doc, engines, UserDictionary(tmp_path / "словарь.txt"), Settings())
    finally:
        engines.close()
    assert [(i.rule_id, i.engine, i.suggestions) for i in issues if i.engine == "user"] == [("user.тнг", "user", ["тенге"])]
```
В `tests/corrector/test_cli.py`:
```python
def test_cli_reports_bad_user_rule(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("corrector.core.paths.user_dir", lambda: tmp_path)
    (tmp_path / "правила.yaml").write_text("- id: плохое\n  найти: '['\n  сообщение: m\n", encoding="utf-8")
    path = make_docx(tmp_path / "акт.docx", body=["Текст."])
    assert cli.main(["--check", str(path), "--no-lt"]) == 0
    assert "правило 1 (плохое)" in capsys.readouterr().err
```

- [ ] **Step 2: Убедиться, что тесты падают.**

- [ ] **Step 3: Подключить правила**

В `factory.py`: импорт `from corrector.rules.engine import RulesEngine, default_rules` и `from corrector.rules.resources import load_resources`; в `Engines` поля `rules: RulesEngine | None = None`, `rule_resources: RuleResources | None = None`; в `build_engines` параметр `user_dir: Path | None = None`; после словарей: `res = load_resources(data, user_dir or paths.user_dir()); engines.rules = RulesEngine(default_rules(res), res); engines.rule_resources = res`. В `statuses()` добавить `EngineStatus("rules", True, f"правил: {len(self.rules.rules)}" + (f"; ошибок в правила.yaml: {len(res.user_rule_errors)}" if res.user_rule_errors else ""))`.

В `pipeline.check_document` перед `dedupe(...)`:
```python
    if engines.rules is not None:
        ctx = context.build_contexts(model, languages, settings, engines.rule_resources)
        issues += engines.rules.run(ctx)
```
(импорт `from corrector.rules import context`).

В `cli.main` после `build_engines`: `for error in engines.rule_resources.user_rule_errors: print(f"правила.yaml: {error}", file=sys.stderr)`.

- [ ] **Step 4: Запустить тесты** — `.venv/bin/python -m pytest -q` — проходят. Прогнать три акта из `/tmp/акты` командной строкой с отчётом и посмотреть, какие правила сработали (ожидаются типографика и `punct.comma_conj`).

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Правила подключены к конвейеру и командной строке; ошибки правила.yaml показываются"`

---

### Task 9: Инструменты корпуса: выборка, прогон, отчёт о шуме

**Files:**
- Create: `tools/corpus_sample.py`, `tools/corpus_run.py`, `docs/corpus-report.md` (результат), `tests/corrector/test_corpus_tools.py`

**Interfaces:**
- Produces:
  - `tools/corpus_sample.py --ru 60 --kk 60 --out vendor/corpus-sample --seed 1`: выборка актов из `~/court-analytics/corpus.db` (русские: доля казахских букв ≤ 1 %, казахские: > 1 %; длина 4–30 тыс. символов; детерминированный порядок по `seed`) в `.docx` по абзацу на строку; повторный запуск не пересоздаёт существующие файлы.
  - `tools/corpus_run.py --sample vendor/corpus-sample --out docs/corpus-report.md [--no-lt] [--no-suggestions]`: прогон конвейера в одном процессе (движки создаются один раз), сохранение `vendor/corpus-sample/issues.json`; отчёт: таблица по правилам (замечаний, актов из N, доля актов, три примера «фрагмент → варианты»), топ-40 фрагментов орфографии по языкам, доля фрагментов с заглавной буквы, время прогона. Правила с долей актов > 33 % помечаются «⚠ разобрать».
  - `corrector.engines.spell.SpellEngine(..., suggestions=True)` — при `False` варианты не вычисляются (ускорение прогона); `factory.build_engines(..., suggestions=True)`.

- [ ] **Step 1: Падающий тест на форматирование отчёта**

`tests/corrector/test_corpus_tools.py`:
```python
import json

from tools import corpus_run


def test_report_table_marks_noisy_rules(tmp_path):
    issues = [
        {"file": "а.docx", "engine": "lt", "rule_id": "X", "category": "spelling", "fragment": "Кызылорда", "suggestions": ["Кызыл орда"], "message": "м"},
        {"file": "б.docx", "engine": "lt", "rule_id": "X", "category": "spelling", "fragment": "Астана", "suggestions": [], "message": "м"},
        {"file": "а.docx", "engine": "rules", "rule_id": "typo.dash", "category": "typography", "fragment": " - ", "suggestions": [" — "], "message": "м"},
    ]
    text = corpus_run.format_report(issues, files=["а.docx", "б.docx", "в.docx"], lang="ru", seconds=12.5)
    assert "| lt:X | 2 | 2/3 (67 %) ⚠ разобрать |" in text
    assert "| rules:typo.dash | 1 | 1/3 (33 %) |" in text
    assert "Кызылорда → Кызыл орда" in text
    assert "с заглавной буквы: 2 из 2" in text
```
(`tools/__init__.py` пустой, чтобы `tools.corpus_run` импортировался; `pythonpath = ["."]` уже есть.)

- [ ] **Step 2: Убедиться, что тест падает.**

- [ ] **Step 3: Написать инструменты**

`tools/corpus_sample.py`:
```python
"""Выборка актов из corpus.db в .docx для измерения шума правил (только Mac)."""

from __future__ import annotations

import argparse
import random
import sqlite3
from pathlib import Path

import docx

DB = Path.home() / "court-analytics" / "corpus.db"
KK_SHARE = "(length(text) - length(replace(replace(replace(replace(text,'ә',''),'қ',''),'ң',''),'ү',''))) * 100.0 / length(text)"


def sample(db: Path, out: Path, ru: int, kk: int, seed: int) -> dict[str, int]:
    con = sqlite3.connect(db)
    rows = con.execute(f"select id, text, {KK_SHARE} as share from documents where length(text) between 4000 and 30000").fetchall()
    random.Random(seed).shuffle(rows)
    counts = {"ru": 0, "kk": 0}
    for doc_id, text, share in rows:
        lang = "kk" if share > 1 else "ru"
        limit = kk if lang == "kk" else ru
        if counts[lang] >= limit:
            continue
        target = out / lang / f"акт_{doc_id}.docx"
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            document = docx.Document()
            for line in text.splitlines():
                if line.strip():
                    document.add_paragraph(line.strip())
            document.save(str(target))
        counts[lang] += 1
        if counts["ru"] >= ru and counts["kk"] >= kk:
            break
    return counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ru", type=int, default=60)
    parser.add_argument("--kk", type=int, default=60)
    parser.add_argument("--out", type=Path, default=Path("vendor/corpus-sample"))
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--db", type=Path, default=DB)
    args = parser.parse_args(argv)
    print(sample(args.db, args.out, args.ru, args.kk, args.seed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`tools/corpus_run.py`:
```python
"""Прогон конвейера по выборке и отчёт о шуме правил."""

from __future__ import annotations

import argparse
import collections
import json
import time
from pathlib import Path

from corrector.core import paths
from corrector.core.settings import Settings
from corrector.core.userdict import UserDictionary
from corrector.docx_io import model
from corrector.engines import factory, pipeline


def run(sample: Path, no_lt: bool, suggestions: bool) -> tuple[dict[str, list[dict]], dict[str, list[str]], float]:
    started = time.time()
    user_dict = UserDictionary(sample / "словарь-пустой.txt")
    engines = factory.build_engines(user_dict, no_lt=no_lt, suggestions=suggestions, user_dir=sample)
    issues_by_lang: dict[str, list[dict]] = {}
    files_by_lang: dict[str, list[str]] = {}
    try:
        for lang in ("ru", "kk"):
            folder = sample / lang
            files_by_lang[lang] = sorted(p.name for p in folder.glob("*.docx")) if folder.is_dir() else []
            issues_by_lang[lang] = []
            for name in files_by_lang[lang]:
                doc = model.load(folder / name)
                for issue in pipeline.check_document(doc, engines, user_dict, Settings()):
                    data = issue.to_dict()
                    data["file"] = name
                    data["fragment"] = doc.paragraphs[issue.paragraph].text[issue.start:issue.end]
                    issues_by_lang[lang].append(data)
    finally:
        engines.close()
    return issues_by_lang, files_by_lang, time.time() - started


def format_report(issues: list[dict], files: list[str], lang: str, seconds: float) -> str:
    total = len(files) or 1
    by_rule = collections.Counter(f"{i['engine']}:{i['rule_id']}" for i in issues)
    docs = collections.defaultdict(set)
    examples = collections.defaultdict(list)
    for i in issues:
        key = f"{i['engine']}:{i['rule_id']}"
        docs[key].add(i["file"])
        if len(examples[key]) < 3 and i["fragment"] not in [e.split(" → ")[0] for e in examples[key]]:
            examples[key].append(f"{i['fragment']} → {', '.join(i['suggestions'][:2]) or '—'}")
    lines = [f"### {lang}: {len(issues)} замечаний в {len(files)} актах, {len(issues)/total:.1f} на акт, {seconds:.0f} с", "",
             "| Правило | Замечаний | Актов | Примеры |", "|---|---|---|---|"]
    for key, count in by_rule.most_common():
        share = len(docs[key]) / total
        flag = " ⚠ разобрать" if share > 0.33 else ""
        lines.append(f"| {key} | {count} | {len(docs[key])}/{len(files)} ({share:.0%}){flag} | {'; '.join(examples[key])} |")
    spelling = [i for i in issues if i["category"] == "spelling"]
    capitalized = sum(1 for i in spelling if i["fragment"][:1].isupper())
    frag = collections.Counter(i["fragment"] for i in spelling)
    lines += ["", f"Орфография: {len(spelling)} замечаний, с заглавной буквы: {capitalized} из {len(spelling)}.",
              "Частые фрагменты: " + ", ".join(f"{w} ({n})" for w, n in frag.most_common(40)), ""]
    return "\n".join(lines).replace(" (0%)", " (0 %)").replace("%)", " %)") + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=Path, default=Path("vendor/corpus-sample"))
    parser.add_argument("--out", type=Path, default=Path("docs/corpus-report.md"))
    parser.add_argument("--no-lt", action="store_true")
    parser.add_argument("--no-suggestions", action="store_true")
    args = parser.parse_args(argv)
    issues, files, seconds = run(args.sample, args.no_lt, not args.no_suggestions)
    (args.sample / "issues.json").write_text(json.dumps(issues, ensure_ascii=False, indent=1), encoding="utf-8")
    report = "# Отчёт о шуме правил по выборке корпуса\n\nВыборка: `tools/corpus_sample.py`, прогон: `tools/corpus_run.py`. Правило с долей актов выше трети помечено «⚠ разобрать».\n\n"
    report += "".join(format_report(issues[lang], files[lang], lang, seconds) for lang in ("ru", "kk"))
    args.out.write_text(report, encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```
Форматирование долей: тест ожидает `2/3 (67 %)` — реализовать явно: `f"{len(docs[key])}/{len(files)} ({share*100:.0f} %)"` вместо `.0%` с последующей заменой (убрать `.replace`).

В `spell.py`: параметр `suggestions: bool = True` в `SpellEngine.__init__`; в `check_tokens` варианты вычисляются только при `self.suggestions`. В `factory.build_engines` параметр `suggestions: bool = True`, передаётся обоим словарным движкам.

- [ ] **Step 4: Прогнать выборку и посмотреть отчёт**

```bash
.venv/bin/python tools/corpus_sample.py
.venv/bin/python tools/corpus_run.py --no-suggestions
```
Ожидается: русские около 40 замечаний на акт до настройки, казахские около 27; в отчёте помечены `lt:MORFOLOGIK_RULE_RU_RU`, `lt:UPPERCASE_SENTENCE_START`, `kk_spell:unknown`, `kk_spell:foreign` и, возможно, новые правила слоя — их разобрать по примерам (задача 10 и 11 меняют данные и код, отчёт перегенерируется в задаче 12).

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Корпус: выборка актов, прогон, отчёт о шуме правил"`

---

### Task 10: Список отключённых правил LanguageTool и лексиконы из корпуса

**Files:**
- Create: `tools/build_lexicon.py`, `data/names_corpus_ru.txt`, `data/names_corpus_kk.txt`, `data/review/` (кандидаты для ручного разбора, в git не идут: `.gitignore` += `data/review/`)
- Modify: `data/lt/lt_disabled_rules.txt`, `data/lexicon_ru_legal.txt`, `data/lexicon_kk_legal.txt`, `data/stop_ru.txt`, `data/stop_kk.txt`, `corrector/engines/spell.py` (списки имён), `corrector/engines/factory.py`

**Interfaces:**
- Produces:
  - `data/lt/lt_disabled_rules.txt` с обоснованиями (по прогону 15.09.2026 на 60 русских актах): `UPPERCASE_SENTENCE_START` (306 срабатываний в 39 актах: строки шапки акта начинаются со строчной), `V_etoj_svyazy` (пуризм: «в этой связи» — норма делового стиля), `OPREDELENIA` (стилевое «избыточные определения», юридический текст без этого не обходится), `noun_genitive_3` (цепочки родительных — норма права), `Cap_Letters_Name` («аким», «ата» приняты за имена), `DoubleNOT` (стилевое), `NN_N_pril_prich` (ложная замена «названного → названого»), `Word_root_repeat` (стилевое), `O_P_padeg` (53 в 11 актах, срабатывает на заголовки с переносом строки, варианты «Об правонарушении» неверны).
  - `tools/build_lexicon.py --lang ru|kk --min-docs 5 --min-courts 3`: по всему `corpus.db` считает для каждого слова (без цифр, ≥ 3 букв) число актов и судов (`acts.court` через `doc_id`, при отсутствии — по имени файла до первого «_»); слова строчными, неизвестные словарю и лексикону → `data/review/lexicon_<lang>_candidates.tsv` (слово, актов, судов, пример контекста); слова с заглавной буквы не в начале предложения → `data/review/names_<lang>_candidates.tsv`; затем автоматический отбор: в `data/lexicon_<lang>_legal.txt` попадают кандидаты, у которых для ru pymorphy3 даёт разбор с `is_known` или слово состоит из известных словарю частей через дефис, для kk — основа по стеммеру известна словарю; остальное остаётся в кандидатах для ручного разбора; в `data/names_corpus_<lang>.txt` попадают имена с ≥ 3 актов и ≥ 2 судов (регистр сохраняется).
  - `SpellEngine(..., names: set[str] = set())` — слова из списка имён (точное совпадение с учётом регистра) считаются известными; `factory` загружает `data/names_corpus_*.txt`.
  - Стоп-списки `data/stop_ru.txt`, `data/stop_kk.txt` — 300 самых частых слов корпуса каждого языка (тот же скрипт, `--stop 300`).

- [ ] **Step 1: Список отключённых правил, падающие тесты**

`data/lt/lt_disabled_rules.txt`:
```
# Правила LanguageTool, отключённые для юридических текстов. Основание — прогон по 60 русским актам 15.09.2026
# (docs/corpus-report.md). Формат: идентификатор правила, после # — почему.
UPPERCASE_SENTENCE_START   # 306 срабатываний в 39 актах: строки шапки акта начинаются со строчной буквы
V_etoj_svyazy              # «в этой связи» — норма делового стиля, LanguageTool требует «в связи с этим»
OPREDELENIA                # «избыточные определения»: юридический текст без них невозможен
noun_genitive_3            # цепочки родительного падежа — норма права («рынка признаков нарушения законодательства»)
Cap_Letters_Name           # «аким», «ата» приняты за имена собственные
DoubleNOT                  # стилевое «два не подряд», в актах оправдано смыслом
NN_N_pril_prich            # ложная замена «названного → названого»
Word_root_repeat           # повтор однокоренных — норма терминологии («рассматриваемом… рассматривает»)
O_P_padeg                  # срабатывает на заголовки с переносом строки, варианты «Об правонарушении» неверны
```
`lt.load_disabled_rules` уже отбрасывает комментарии в начале строки; дописать: обрезать часть строки после `#` (тест в `test_lt_unit.py`: строка `"RULE   # пояснение"` → `"RULE"`).

Тест для лексикона: `tests/corrector/test_spell_names.py`:
```python
from corrector.core import paths
from corrector.core.userdict import UserDictionary
from corrector.engines.hunspell import SpellDictionary
from corrector.engines.spell import SpellEngine


def test_names_list_accepts_exact_case(tmp_path):
    ru = SpellDictionary(paths.data_dir() / "ru" / "ru_RU")
    engine = SpellEngine("ru_spell", ru, set(), UserDictionary(tmp_path / "с.txt"), names={"Кызылординской"})
    assert engine.check([(0, "Суд Кызылординской области")]) == []
    assert len(engine.check([(0, "Суд кызылординской области")])) == 1
```

- [ ] **Step 2: Убедиться, что тесты падают.**

- [ ] **Step 3: Скрипт лексикона и данные**

`tools/build_lexicon.py`:
```python
"""Лексиконы и имена из корпуса: слова, неизвестные словарю, но частые в актах разных судов (только Mac)."""

from __future__ import annotations

import argparse
import collections
import re
import sqlite3
from pathlib import Path

from corrector.core import paths
from corrector.core.text import LETTERS, words
from corrector.engines.hunspell import SpellDictionary
from corrector.engines.spell import load_lexicon

DB = Path.home() / "court-analytics" / "corpus.db"
KK_SHARE = "(length(text) - length(replace(replace(replace(replace(text,'ә',''),'қ',''),'ң',''),'ү',''))) * 100.0 / length(text)"
SENTENCE_START = re.compile(rf"(?:^|[.!?»]\s+)([{LETTERS}])")


def scan(db: Path, lang: str):
    con = sqlite3.connect(db)
    condition = "share > 1" if lang == "kk" else "share <= 1"
    query = f"select d.id, d.text, coalesce(a.court, substr(d.filename, 1, instr(d.filename, '_') - 1)) from (select id, text, filename, {KK_SHARE} as share from documents where text is not null) d left join acts a on a.doc_id = d.id where {condition}"
    lower_docs, lower_courts, lower_examples = collections.defaultdict(set), collections.defaultdict(set), {}
    name_docs, name_courts = collections.defaultdict(set), collections.defaultdict(set)
    frequency = collections.Counter()
    for doc_id, text, court in con.execute(query):
        starts = {m.start(1) for m in SENTENCE_START.finditer(text)}
        for token in words(text):
            w = token.text
            if len(w) < 3 or any(ch.isdigit() for ch in w):
                continue
            frequency[w.lower()] += 1
            if w[0].isupper() and w[1:].islower() and token.start not in starts:
                name_docs[w].add(doc_id)
                name_courts[w].add(court)
            elif w.islower():
                lower_docs[w].add(doc_id)
                lower_courts[w].add(court)
                lower_examples.setdefault(w, text[max(0, token.start - 30):token.end + 30].replace("\n", " "))
    return lower_docs, lower_courts, lower_examples, name_docs, name_courts, frequency


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", choices=["ru", "kk"], required=True)
    parser.add_argument("--min-docs", type=int, default=5)
    parser.add_argument("--min-courts", type=int, default=3)
    parser.add_argument("--stop", type=int, default=300)
    parser.add_argument("--db", type=Path, default=DB)
    args = parser.parse_args(argv)
    data = paths.data_dir()
    review = data / "review"
    review.mkdir(exist_ok=True)
    dictionary = SpellDictionary(data / args.lang / ("ru_RU" if args.lang == "ru" else "kk_KZ"))
    lexicon_path = data / f"lexicon_{args.lang}_legal.txt"
    known = load_lexicon(lexicon_path)
    lower_docs, lower_courts, examples, name_docs, name_courts, frequency = scan(args.db, args.lang)

    accepted, candidates = [], []
    for w, docs in sorted(lower_docs.items(), key=lambda kv: -len(kv[1])):
        if len(docs) < args.min_docs or len(lower_courts[w]) < args.min_courts or w in known or dictionary.known(w):
            continue
        parts = [p for p in w.split("-") if p]
        if len(parts) > 1 and all(dictionary.known(p) for p in parts):
            accepted.append(w)
            continue
        if args.lang == "ru":
            import pymorphy3
            morph = pymorphy3.MorphAnalyzer()
            if any(p.is_known for p in morph.parse(w)):
                accepted.append(w)
                continue
        else:
            from corrector.engines import kk_stem
            stem = kk_stem.default().stem(w)
            if len(stem) >= 3 and dictionary.known(stem):
                accepted.append(w)
                continue
        candidates.append((w, len(docs), len(lower_courts[w]), examples[w]))

    with lexicon_path.open("a", encoding="utf-8") as stream:
        stream.write(f"\n# Из корпуса (tools/build_lexicon.py, не менее {args.min_docs} актов и {args.min_courts} судов)\n")
        stream.writelines(w + "\n" for w in accepted)
    (review / f"lexicon_{args.lang}_candidates.tsv").write_text(
        "слово\tактов\tсудов\tпример\n" + "".join(f"{w}\t{d}\t{c}\t{e}\n" for w, d, c, e in candidates), encoding="utf-8")

    names = [w for w, docs in sorted(name_docs.items(), key=lambda kv: -len(kv[1]))
             if len(docs) >= 3 and len(name_courts[w]) >= 2 and not dictionary.known(w)]
    (data / f"names_corpus_{args.lang}.txt").write_text(
        "# Имена и названия из корпуса (регистр важен): не менее 3 актов и 2 судов\n" + "\n".join(names) + "\n", encoding="utf-8")
    (data / f"stop_{args.lang}.txt").write_text(
        "# Самые частые слова корпуса для правила повторов\n" + "\n".join(w for w, _ in frequency.most_common(args.stop)) + "\n", encoding="utf-8")
    print(f"{args.lang}: в лексикон {len(accepted)}, кандидатов {len(candidates)}, имён {len(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```
(pymorphy3 создаётся один раз — вынести создание `morph` до цикла.)

Run: `.venv/bin/python tools/build_lexicon.py --lang ru && .venv/bin/python tools/build_lexicon.py --lang kk` — по 5–15 минут на язык. Затем просмотреть `data/review/lexicon_*_candidates.tsv` (первые 200 строк): явные юридические слова («акимат», «обязание», «госрегистрация», «дауланып», «міндеттелсін», «кадастрлік») добавить в лексиконы руками; опечатки не добавлять. Стоп-списки перезаписываются (посев из задачи 4 заменяется корпусными).

В `spell.py`: `names: set[str] | None = None` в конструкторе; в `_accepted`: `if word in self.names: return True` (регистр важен). В `factory.py`: `names_ru = set(_lines(data / "names_corpus_ru.txt"))` и т. п. (взять `load_lexicon`, но без приведения к нижнему регистру: добавить в `spell.py` функцию `load_names(path) -> set[str]`).

- [ ] **Step 4: Запустить тесты и прогон** — `.venv/bin/python -m pytest -q`; `.venv/bin/python tools/corpus_run.py --no-suggestions` — среднее число замечаний на русский акт должно упасть примерно вдвое (ожидание: с 43 до 15–20), казахский — заметно (имена).

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Корпус: отключённые правила LanguageTool с обоснованием, лексиконы и имена из 41 760 актов"`

---

### Task 11: Смешанные абзацы, имена собственные без шума, ленивые подсказки

**Files:**
- Modify: `corrector/core/lang.py` (`mixed`), `corrector/engines/pipeline.py`, `corrector/engines/spell.py`, `corrector/engines/factory.py` (`suggest(word, lang)`), `tests/corrector/test_lang.py` (+ mixed), `tests/corrector/test_pipeline.py` (+ mixed), `tests/corrector/test_spell_names.py` (+ политика имён), `corrector/cli.py` (`--no-suggestions`)

**Interfaces:**
- Produces:
  - `lang.detect(text, previous)` возвращает `"mixed"`, если обе оценки не меньше 6 и меньшая ≥ 40 % большей; `detect_all` при `mixed` не меняет `previous` для следующих абзацев.
  - Конвейер: абзацы `mixed` — слова с казахскими буквами проверяет казахский движок без подсказок «русское слово», остальные слова — запасной русский словарь (`ru_spell`), LanguageTool такие абзацы не получает; правила уровня `any` выполняются.
  - Политика имён собственных в `SpellEngine.check(paragraphs)`: неизвестное слово с заглавной первой буквой и строчными остальными, не в начале предложения (первое слово абзаца или после `. ! ?`): если та же форма встречается в переданных абзацах ≥ 2 раз — пропуск; если один раз — замечание уровня `hint` категории `spelling` с сообщением «Незнакомое слово с заглавной буквы: имя или название? Проверьте написание» и без вариантов; слово в начале предложения проверяется как обычно.
  - `Engines.suggest(word: str, lang: str) -> list[str]` — подсказки по требованию (для окна на этапе 5); `SpellEngine.suggestions=False` по умолчанию в `--json` при флаге `--no-suggestions`; в отчёте `--report` подсказки остаются.

- [ ] **Step 1: Падающие тесты**

В `tests/corrector/test_lang.py`:
```python
def test_mixed_paragraph():
    text = "ҚАЗАҚСТАН РЕСПУБЛИКАСЫ ЖОҒАРҒЫ СОТЫ / ВЕРХОВНЫЙ СУД РЕСПУБЛИКИ КАЗАХСТАН, судебная коллегия по гражданским делам, сот алқасы"
    assert lang.detect(text) == "mixed"
    assert lang.detect_all([text, "№ 5"], ) == ["mixed", "ru"]
```
В `tests/corrector/test_pipeline.py`:
```python
def test_mixed_paragraph_has_no_foreign_hints_and_checks_both_dictionaries(tmp_path):
    text = "ҚАЗАҚСТАН РЕСПУБЛИКАСЫ ЖОҒАРҒЫ СОТЫ / ВЕРХОВНЫЙ СУД РЕСПУБЛИКИ КАЗАХСТАН, судебная колегия по гражданским делам, сот алқасы шешімі"
    path = make_docx(tmp_path / "а.docx", body=[text])
    doc = model.load(path)
    fake = FakeRu()
    engines = build(tmp_path, fake)
    try:
        issues = pipeline.check_document(doc, engines, UserDictionary(tmp_path / "словарь.txt"), Settings())
    finally:
        engines.close()
    assert fake.seen == []
    assert [doc.paragraphs[0].text[i.start:i.end] for i in issues if i.category is Category.SPELLING] == ["колегия"]
    assert not [i for i in issues if i.rule_id.endswith(":foreign")]
```
В `tests/corrector/test_spell_names.py`:
```python
def test_unknown_capitalized_word_policy(tmp_path):
    ru = SpellDictionary(paths.data_dir() / "ru" / "ru_RU")
    engine = SpellEngine("ru_spell", ru, set(), UserDictionary(tmp_path / "с.txt"))
    twice = engine.check([(0, "Истец Турматова подала иск."), (1, "Представитель Турматова явился.")])
    assert twice == []
    once = engine.check([(0, "Истец Турматова подала иск.")])
    assert len(once) == 1 and once[0].level is Level.HINT and once[0].suggestions == [] and "имя или название" in once[0].message
    start = engine.check([(0, "Турматова подала иск.")])
    assert len(start) == 1 and start[0].level is Level.ERROR
```

- [ ] **Step 2: Убедиться, что тесты падают.**

- [ ] **Step 3: Реализовать**

`lang.detect`:
```python
def detect(text: str, previous: str = "ru") -> str:
    kk, ru = score(text)
    if kk == 0 and ru == 0:
        return previous
    if min(kk, ru) >= 6 and min(kk, ru) >= 0.4 * max(kk, ru):
        return "mixed"
    return "kk" if kk > ru else "ru"
```
`detect_all`: `code = detect(text, previous); result.append(code); if code != "mixed": previous = code`.

`pipeline.check_document`: третий список `mixed`; для него: `tokens_kk = [t for t in words(text) if lang.has_kk_letters(t.text)]` → `engines.kk.check_tokens(index, text, tokens_kk, foreign_hints=False)`; `tokens_ru = остальные слова` → `engines.ru_spell.check_tokens(index, text, tokens_ru)`. В `SpellEngine.check_tokens` параметр `foreign_hints: bool = True`.

Политика имён в `SpellEngine.check`: перед циклом по абзацам посчитать `Counter` форм всех слов во всех переданных абзацах; в `check_tokens` передавать `counts` (параметр `counts: Counter | None = None`) и множество позиций начала предложений (`sentence_starts = {s for s, _ in sentences(text, ...)}`, вычисляется на абзац): для неизвестного слова `w` с `w[0].isupper() and w[1:].islower()` и `token.start not in sentence_starts`: если `counts and counts[w] >= 2` → пропуск; иначе → `Issue(..., Level.HINT, f"{self.name}:name", ..., NAME_MESSAGE, [])`. Константа `NAME_MESSAGE = "Незнакомое слово с заглавной буквы: имя или название? Проверьте написание"`.

`Engines.suggest(word, lang)`: `dictionary = self.kk.dictionary if lang == "kk" else self.ru_spell.dictionary; return dictionary.suggest(word)`.

`cli`: флаг `--no-suggestions` → `build_engines(..., suggestions=False)`.

- [ ] **Step 4: Запустить тесты и прогон** — `.venv/bin/python -m pytest -q`; `.venv/bin/python tools/corpus_run.py` (с подсказками, для времени) — казахская выборка должна пройти за минуты, а не за 25 минут, потому что имена больше не получают подсказок.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "Смешанные абзацы, имена собственные без шума, подсказки по требованию"`

---

### Task 12: Отчёт о корпусе как база, документация, слияние

**Files:**
- Modify: `docs/corpus-report.md` (перегенерировать), `docs/rules-ru.md`/`docs/rules-kk.md` (проверить полноту: у каждого правила из `default_rules` есть таблица — тест `test_every_rule_documented`), `README.md` (раздел «Правила и файлы для коллег»), спецификация (раздел 6 — ссылка на docs/rules-*.md как каталог), память проекта.
- Create: `tests/corrector/test_rules_documented.py`

**Interfaces:**
- Produces: тест `test_every_rule_documented`: множество `rule.id` из `default_rules(RuleResources())` (без правил пользователя) ⊆ множество идентификаторов из обеих таблиц docs.

- [ ] **Step 1:** тест полноты документации; запуск → починить пропуски.
- [ ] **Step 2:** `.venv/bin/python tools/corpus_run.py` → закоммитить `docs/corpus-report.md`; в нём не должно остаться правил с «⚠ разобрать» без строки-пояснения в `lt_disabled_rules.txt` или в docs правила (если правило слоя срабатывает чаще чем в трети актов — либо это норма (типографика, `typo.abbrev_space` в актах с «ст.5» повсюду), либо правило надо смягчить; решение записать в docs/rules-*.md под таблицей строкой «Шум по корпусу: …»).
- [ ] **Step 3:** README: как править `правила.yaml`, `словарь.txt`, где отчёт о шуме; спецификация: в раздел 6 добавить абзац «Каталог правил — docs/rules-ru.md и docs/rules-kk.md».
- [ ] **Step 4:** `git push -u origin stage3-4`, запуск сборщика через `workflow_dispatch` на ветке (тесты на Windows: правила, документы; `lt` пропускаются), зелёный → слияние в `main` (`--ff-only`), удаление ветки, обновление памяти проекта, отчёт пользователю: что ловится, сколько шума осталось, что дальше (этапы 5–6: окно и Word).

---

## Самопроверка плана

- Покрытие спецификации: п. 5.4 слой правил (шаблонные и программные, таблицы docs как тесты) — задачи 1–8; п. 6 каталог проверок: смешанные алфавиты, типографика, повторы, длинные предложения, разнобой имён, названия органов и законов, правила пользователя, русские шаблоны, казахская пунктуация и дефисы — задачи 3–7; числа и даты — только «2024г.» и типографика (единый формат дат и разряды сумм отложены с записью в docs, потому что на корпусе оба формата дат законны в одном акте); термины termincom — отложены (нужен разбор структуры сайта, 390 787 терминов без выгрузки); п. 9 `правила.yaml` — задача 2; п. 14 прогон по корпусу, порог трети актов, лексиконы, `lt_disabled_rules.txt`, `docs/corpus-report.md` — задачи 9–12.
- Заглушек нет: код или точные команды в каждом шаге; временные `HelloRule` и таблица `test.hello` удаляются в задаче 3.
- Имена согласованы: `ParaContext.sentence_of/word_before`, `DocContext.resources/settings`, `make_issue(rule, para, start, end, suggestions, message, engine)`, `PatternRule(id, lang, category, level, message, pattern, replacement, flags, condition, engine)`, `RulesEngine(rules, resources).run(doc)`, `default_rules(resources)`, `load_user_rules(path)`, `SpellEngine(..., suggestions, names)` и `check_tokens(index, text, tokens, foreign_hints, counts)`, `Engines.rules/rule_resources/suggest`, `lang.detect → mixed`.
