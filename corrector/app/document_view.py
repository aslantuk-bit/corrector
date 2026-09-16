"""Текст документа как лист: настоящие таблицы, жирный и курсив по фрагментам, подсветка замечаний."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QBrush, QColor, QFont, QTextCharFormat, QTextCursor, QTextLength, QTextTableFormat
from PySide6.QtWidgets import QTextEdit

from corrector.core.issue import Level
from corrector.docx_io.model import DocumentModel, ParagraphBlock, TableBlock

COLORS = {Level.ERROR: QColor("#F9D6D2"), Level.WARNING: QColor("#FCE9C4"), Level.HINT: QColor("#D8E6F7")}
SELECTED = {Level.ERROR: QColor("#F2A9A1"), Level.WARNING: QColor("#F6CF86"), Level.HINT: QColor("#A9C7EE")}
TEXTBOX_TINT = QColor("#F3F4F6")


class DocumentView(QTextEdit):
    issue_clicked = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setObjectName("document")
        self.block_starts: list[int] = []
        self.spans: list[tuple[int, int, int]] = []  # (начало, конец, id замечания) в координатах всего текста
        self.selected_id: int | None = None
        self.levels: dict[int, Level] = {}

    # --- построение листа ---
    def set_model(self, model: DocumentModel) -> None:
        self.block_starts = [0] * len(model.paragraphs)
        document = self.document()
        document.clear()
        base = QFont(self.font())
        cursor = QTextCursor(document)
        self._render_blocks(cursor, model, model.blocks, base)
        self.setTextCursor(QTextCursor(document))

    def _render_blocks(self, cursor: QTextCursor, model: DocumentModel, blocks: list, base: QFont) -> None:
        first = True
        for block in blocks:
            if isinstance(block, ParagraphBlock):
                if not first:
                    cursor.insertBlock()
                self._render_paragraph(cursor, model.paragraphs[block.index], base)
            elif isinstance(block, TableBlock):
                if not first:
                    cursor.insertBlock()
                self._render_table(cursor, model, block, base)
            first = False

    def _render_paragraph(self, cursor: QTextCursor, para, base: QFont) -> None:
        self.block_starts[para.index] = cursor.position()
        if para.where == "textbox":
            block_format = cursor.blockFormat()
            block_format.setBackground(QBrush(TEXTBOX_TINT))
            block_format.setLeftMargin(12)
            cursor.setBlockFormat(block_format)
        if not para.runs:
            cursor.insertText(para.text)
            return
        for span in para.runs:
            fmt = QTextCharFormat()
            font = QFont(base)
            if span.run.bold:
                font.setBold(True)
            if span.run.italic:
                font.setItalic(True)
            if span.run.underline:
                font.setUnderline(True)
            fmt.setFont(font)
            cursor.insertText(span.run.text, fmt)

    def _render_table(self, cursor: QTextCursor, model: DocumentModel, table: TableBlock, base: QFont) -> None:
        rows = len(table.rows)
        cols = max((len(r) for r in table.rows), default=1)
        if rows == 0 or cols == 0:
            return
        fmt = QTextTableFormat()
        fmt.setBorder(1)
        fmt.setBorderBrush(QBrush(QColor("#B8C0CA")))
        fmt.setCellPadding(5)
        fmt.setCellSpacing(0)
        fmt.setTopMargin(6)
        fmt.setBottomMargin(6)
        fmt.setWidth(QTextLength(QTextLength.Type.PercentageLength, 100))
        qtable = cursor.insertTable(rows, cols, fmt)
        for r, row in enumerate(table.rows):
            for c, cell_blocks in enumerate(row):
                cell_cursor = qtable.cellAt(r, c).firstCursorPosition()
                self._render_blocks(cell_cursor, model, cell_blocks, base)
        cursor.setPosition(qtable.lastPosition())
        cursor.movePosition(QTextCursor.MoveOperation.NextBlock)

    # --- подсветка и выбор ---
    def absolute(self, paragraph: int, offset: int) -> int:
        return self.block_starts[paragraph] + offset

    def set_highlights(self, session, items) -> None:
        self.spans, self.levels = [], {}
        selections = []
        for item in items:
            issue = item.issue
            start, end = self.absolute(issue.paragraph, issue.start), self.absolute(issue.paragraph, issue.end)
            self.spans.append((start, end, item.id))
            self.levels[item.id] = issue.level
            selection = QTextEdit.ExtraSelection()
            cursor = QTextCursor(self.document())
            cursor.setPosition(start)
            cursor.setPosition(max(end, start), QTextCursor.MoveMode.KeepAnchor)
            fmt = QTextCharFormat()
            palette = SELECTED if item.id == self.selected_id else COLORS
            fmt.setBackground(palette[issue.level])
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
