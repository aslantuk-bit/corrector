"""Список замечаний и карточка выбранного замечания с кнопками действий."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from corrector.app import theme
from corrector.core.issue import CATEGORY_TITLES, LEVEL_TITLES, Category


class IssuePanel(QWidget):
    selected = Signal(int)
    apply_requested = Signal(int, str)
    skip_requested = Signal(int)
    dictionary_requested = Signal(int)
    disable_requested = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.current_id: int | None = None
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_current_changed)
        self.list.setIconSize(QSize(12, 12))
        self.caption = QLabel("Замечания")
        self.caption.setObjectName("subtitle")
        self.header = QLabel("Откройте документ")
        self.header.setObjectName("cardHeader")
        self.message = QLabel("")
        self.message.setObjectName("message")
        self.message.setWordWrap(True)
        self.fragment = QLabel("")
        self.fragment.setObjectName("fragment")
        self.fragment.setWordWrap(True)
        self.fragment.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.suggestions_box = QVBoxLayout()
        self.suggestions_box.setSpacing(6)
        self.custom = QLineEdit()
        self.custom.setPlaceholderText("Своё исправление")
        self.custom.returnPressed.connect(lambda: self._emit_apply(self.custom.text()))
        self.replace_button = QPushButton("Заменить")
        self.replace_button.setProperty("kind", "primary")
        self.replace_button.clicked.connect(lambda: self._emit_apply(self.custom.text()))
        self.skip_button = QPushButton("Пропустить")
        self.skip_button.clicked.connect(lambda: self._emit(self.skip_requested))
        self.dictionary_button = QPushButton("Добавить в словарь")
        self.dictionary_button.clicked.connect(lambda: self._emit(self.dictionary_requested))
        self.disable_button = QPushButton("Больше не показывать это правило")
        self.disable_button.setProperty("kind", "quiet")
        self.disable_button.clicked.connect(lambda: self._emit(self.disable_requested))
        for widget in (self.custom, self.replace_button, self.skip_button, self.dictionary_button):
            widget.setFixedHeight(34)

        custom_row = QHBoxLayout()
        custom_row.setSpacing(8)
        custom_row.addWidget(self.custom, 1)
        custom_row.addWidget(self.replace_button)
        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(self.skip_button)
        actions.addWidget(self.dictionary_button)
        card = QVBoxLayout()
        card.setSpacing(8)
        card.addWidget(self.header)
        card.addWidget(self.message)
        card.addWidget(self.fragment)
        card.addLayout(self.suggestions_box)
        card.addLayout(custom_row)
        card.addLayout(actions)
        card.addWidget(self.disable_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.caption)
        layout.addWidget(self.list, 3)
        layout.addLayout(card, 2)
        self._set_enabled(False)

    def set_items(self, session, items) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for item in items:
            issue = item.issue
            fragment = session.fragment(item).strip() or "пробел"
            row = QListWidgetItem(theme.level_icon(issue.level), f"«{fragment[:40]}»  {CATEGORY_TITLES[issue.category].lower()}, абз. {issue.paragraph + 1}")
            row.setData(Qt.ItemDataRole.UserRole, item.id)
            self.list.addItem(row)
        self.list.blockSignals(False)
        self._session = session
        self._items = {item.id: item for item in items}
        self.caption.setText(f"Замечания: {len(items)}" if items else "Замечания")
        if items:
            self.list.setCurrentRow(0)
        else:
            self.current_id = None
            self.header.setText("Замечаний нет")
            self.header.setStyleSheet("")
            self.message.setText("")
            self.fragment.setText("")
            self._clear_suggestions()
            self._set_enabled(False)

    def select(self, item_id: int) -> None:
        for row in range(self.list.count()):
            if self.list.item(row).data(Qt.ItemDataRole.UserRole) == item_id:
                self.list.setCurrentRow(row)
                return

    def _on_current_changed(self, current, _previous) -> None:
        if current is None:
            return
        item_id = current.data(Qt.ItemDataRole.UserRole)
        self.current_id = item_id
        self._show(self._items[item_id])
        self.selected.emit(item_id)

    def _show(self, item) -> None:
        issue = item.issue
        color = theme.LEVEL_COLORS[issue.level]
        self.header.setText(f"{CATEGORY_TITLES[issue.category]}, {LEVEL_TITLES[issue.level]}")
        self.header.setStyleSheet(f"color: {color};")
        self.message.setText(issue.message)
        self.fragment.setText(self._session.fragment(item) or "(пробел)")
        self._clear_suggestions()
        fragment = self._session.fragment(item)
        for suggestion in issue.suggestions[:5]:
            if not suggestion.strip():
                label = "Убрать лишний пробел"
            elif suggestion.strip() == fragment.strip():
                label = "Исправить пробелы"
            else:
                label = f"Заменить на «{suggestion}»"
            button = QPushButton(label)
            button.setProperty("kind", "primary")
            button.setFixedHeight(34)
            button.clicked.connect(lambda _checked=False, s=suggestion: self._emit_apply(s))
            self.suggestions_box.addWidget(button)
        self.custom.setText("")
        self._set_enabled(True)
        self.dictionary_button.setEnabled(issue.category is Category.SPELLING)

    def _clear_suggestions(self) -> None:
        while self.suggestions_box.count():
            widget = self.suggestions_box.takeAt(0).widget()
            if widget is not None:
                widget.deleteLater()

    def _set_enabled(self, enabled: bool) -> None:
        for widget in (self.custom, self.replace_button, self.skip_button, self.dictionary_button, self.disable_button):
            widget.setEnabled(enabled)

    def _emit(self, signal) -> None:
        if self.current_id is not None:
            signal.emit(self.current_id)

    def _emit_apply(self, text: str) -> None:
        if self.current_id is not None:
            self.apply_requested.emit(self.current_id, text)
