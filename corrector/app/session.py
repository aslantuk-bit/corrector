"""Сеанс проверки: документ, замечания и действия над ними (принять, пропустить, в словарь, отключить правило, сохранить)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from corrector.core.issue import CATEGORY_TITLES, LEVEL_TITLES, Category, Issue, Level
from corrector.core.settings import FILE_NAME as SETTINGS_FILE
from corrector.core.settings import Settings
from corrector.core.userdict import FILE_NAME as DICT_FILE
from corrector.core.userdict import UserDictionary
from corrector.docx_io import edit
from corrector.docx_io import model as docx_model
from corrector.engines import pipeline
from corrector.engines.base import EngineStatus
from corrector.engines.factory import Engines


@dataclass
class IssueState:
    id: int
    issue: Issue
    status: str = "open"  # open | applied | skipped | closed


def comment_text(issue: Issue) -> str:
    text = f"{CATEGORY_TITLES[issue.category]} ({LEVEL_TITLES[issue.level]}): {issue.message}"
    if issue.suggestions:
        text += " Варианты: " + ", ".join(issue.suggestions)
    return text


class Session:
    def __init__(self, engines: Engines, user_dir: Path, user_dict: UserDictionary | None = None) -> None:
        self.engines = engines
        self.user_dir = Path(user_dir)
        self.settings = Settings.load(self.user_dir / SETTINGS_FILE)
        self.user_dict = user_dict or UserDictionary(self.user_dir / DICT_FILE)
        self.model: docx_model.DocumentModel | None = None
        self.path: Path | None = None
        self.items: list[IssueState] = []
        self.saved_path: Path | None = None

    # --- документ и проверка ---
    def open(self, path: Path) -> None:
        self.path = Path(path)
        self.model = docx_model.load(self.path)
        self.items = []
        self.saved_path = None

    def check(self) -> list[IssueState]:
        assert self.model is not None
        issues = pipeline.check_document(self.model, self.engines, self.user_dict, self.settings)
        self.items = [IssueState(number, issue) for number, issue in enumerate(issues, 1)]
        return self.items

    # --- доступ ---
    def _get(self, item_id: int) -> IssueState:
        for item in self.items:
            if item.id == item_id:
                return item
        raise KeyError(item_id)

    def fragment(self, item: IssueState) -> str:
        return self.model.paragraphs[item.issue.paragraph].text[item.issue.start:item.issue.end]

    def open_items(self) -> list[IssueState]:
        return [i for i in self.items if i.status == "open"]

    def visible_items(self) -> list[IssueState]:
        return [i for i in self.open_items() if self.settings.categories.get(i.issue.category.value, True)]

    def counts(self) -> dict[Level, int]:
        visible = self.visible_items()
        return {level: sum(1 for i in visible if i.issue.level is level) for level in Level}

    def statuses(self) -> list[EngineStatus]:
        return self.engines.statuses()

    # --- действия ---
    def apply(self, item_id: int, replacement: str) -> None:
        item = self._get(item_id)
        issue = item.issue
        para = self.model.paragraphs[issue.paragraph]
        delta = edit.apply_replacement(para, issue.start, issue.end, replacement)
        item.status = "applied"
        for other in self.items:
            if other is item or other.issue.paragraph != issue.paragraph or other.status != "open":
                continue
            if other.issue.start >= issue.end:
                other.issue.start += delta
                other.issue.end += delta
            elif other.issue.end > issue.start:
                other.status = "closed"  # пересекается с заменённым отрезком

    def skip(self, item_id: int) -> None:
        self._get(item_id).status = "skipped"

    def add_to_dictionary(self, item_id: int) -> None:
        item = self._get(item_id)
        word = self.fragment(item)
        self.user_dict.add(word)
        for other in self.open_items():
            if other.issue.category is Category.SPELLING and self.fragment(other).lower() == word.lower():
                other.status = "closed"
        item.status = "closed"

    def disable_rule(self, item_id: int) -> None:
        item = self._get(item_id)
        rule = item.issue.rule_id
        if rule not in self.settings.disabled_rules:
            self.settings.disabled_rules.append(rule)
            self.settings.save(self.user_dir / SETTINGS_FILE)
        for other in self.open_items():
            if other.issue.rule_id == rule:
                other.status = "closed"
        item.status = "closed"

    def set_category(self, category: str, enabled: bool) -> None:
        self.settings.categories[category] = enabled
        self.settings.save(self.user_dir / SETTINGS_FILE)

    # --- сохранение ---
    def save(self, with_comments: bool, out_dir: Path | None = None) -> Path:
        assert self.model is not None and self.path is not None
        if with_comments:
            for item in self.visible_items():
                para = self.model.paragraphs[item.issue.paragraph]
                edit.add_comment(self.model, para, item.issue.start, item.issue.end, comment_text(item.issue))
        if out_dir is not None:
            Path(out_dir).mkdir(parents=True, exist_ok=True)
        target = edit.save_copy(self.model, edit.output_path(self.path, out_dir))
        self.saved_path = target
        return target
