"""Текст документа с подсветкой замечаний; щелчок по подсветке выбирает замечание."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit

from corrector.core.issue import Level

COLORS = {Level.ERROR: QColor("#ffd0d0"), Level.WARNING: QColor("#ffe6b8"), Level.HINT: QColor("#d4e6ff")}
SELECTED = QColor("#b3ffb3")


class DocumentView(QTextEdit):
    issue_clicked = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)
        font = self.font()
        font.setPointSize(13)
        self.setFont(font)
        self.block_starts: list[int] = []
        self.spans: list[tuple[int, int, int]] = []  # (начало, конец, id замечания) в координатах всего текста
        self.selected_id: int | None = None

    def set_model(self, model) -> None:
        texts = [p.text for p in model.paragraphs]
        self.block_starts, position = [], 0
        for text in texts:
            self.block_starts.append(position)
            position += len(text) + 1
        self.setPlainText("\n".join(texts))

    def absolute(self, paragraph: int, offset: int) -> int:
        return self.block_starts[paragraph] + offset

    def set_highlights(self, session, items) -> None:
        self.spans = []
        selections = []
        for item in items:
            issue = item.issue
            start, end = self.absolute(issue.paragraph, issue.start), self.absolute(issue.paragraph, issue.end)
            self.spans.append((start, end, item.id))
            selection = QTextEdit.ExtraSelection()
            cursor = QTextCursor(self.document())
            cursor.setPosition(start)
            cursor.setPosition(max(end, start), QTextCursor.MoveMode.KeepAnchor)
            fmt = QTextCharFormat()
            fmt.setBackground(SELECTED if item.id == self.selected_id else COLORS[issue.level])
            selection.cursor, selection.format = cursor, fmt
            selections.append(selection)
        self.setExtraSelections(selections)

    def select(self, item_id: int | None) -> None:
        self.selected_id = item_id
        for start, end, current in self.spans:
            if current == item_id:
                cursor = self.textCursor()
                cursor.setPosition(start)
                self.setTextCursor(cursor)
                self.ensureCursorVisible()
                break

    def mousePressEvent(self, event) -> None:  # noqa: N802 — имя метода Qt
        super().mousePressEvent(event)
        position = self.cursorForPosition(event.position().toPoint()).position()
        for start, end, item_id in self.spans:
            if start <= position <= end:
                self.issue_clicked.emit(item_id)
                return
