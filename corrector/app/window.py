"""Главное окно Корректора."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QTextBrowser,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from corrector import __version__
from corrector.app.document_view import DocumentView
from corrector.app.issue_panel import IssuePanel
from corrector.app.session import Session
from corrector.app.worker import CheckWorker
from corrector.core.issue import Level
from corrector.docx_io.model import DocxError

CATEGORY_BOXES = [
    ("Орфография", ["spelling"]),
    ("Пунктуация и грамматика", ["punctuation", "grammar"]),
    ("Типографика", ["typography"]),
    ("Стиль", ["style"]),
]


class MainWindow(QMainWindow):
    check_finished = Signal()

    def __init__(self, session: Session, help_text: str = "", interactive: bool = True) -> None:
        super().__init__()
        self.session, self.help_text, self.interactive = session, help_text, interactive
        self.worker: CheckWorker | None = None
        self.setWindowTitle(f"Корректор {__version__}")
        self.resize(1200, 760)
        self.setAcceptDrops(True)

        toolbar = QToolBar("Действия")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        self.open_action = QAction("Открыть", self)
        self.open_action.triggered.connect(self.open_file)
        self.check_action = QAction("Проверить", self)
        self.check_action.triggered.connect(self.start_check)
        self.save_action = QAction("Сохранить копию", self)
        self.save_action.triggered.connect(lambda: self.save(False))
        self.save_comments_action = QAction("Сохранить с примечаниями", self)
        self.save_comments_action.triggered.connect(lambda: self.save(True))
        self.help_action = QAction("Справка", self)
        self.help_action.triggered.connect(self.show_help)
        for action in (self.open_action, self.check_action, self.save_action, self.save_comments_action, self.help_action):
            toolbar.addAction(action)

        self.boxes: list[tuple[QCheckBox, list[str]]] = []
        categories = QHBoxLayout()
        for title, keys in CATEGORY_BOXES:
            box = QCheckBox(title)
            box.setChecked(all(self.session.settings.categories.get(k, True) for k in keys))
            box.toggled.connect(lambda checked, keys=keys: self.toggle_category(keys, checked))
            categories.addWidget(box)
            self.boxes.append((box, keys))
        categories.addStretch()

        self.view = DocumentView()
        self.view.issue_clicked.connect(self.panel_select)
        self.panel = IssuePanel()
        self.panel.selected.connect(self.on_selected)
        self.panel.apply_requested.connect(self.on_apply)
        self.panel.skip_requested.connect(self.on_skip)
        self.panel.dictionary_requested.connect(self.on_dictionary)
        self.panel.disable_requested.connect(self.on_disable)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.view)
        splitter.addWidget(self.panel)
        splitter.setSizes([760, 440])

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(categories)
        layout.addWidget(splitter)
        self.setCentralWidget(central)

        self.counters = QLabel("Откройте документ .docx")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setMaximumWidth(160)
        self.engines_label = QLabel("")
        self.statusBar().addWidget(self.counters, 1)
        self.statusBar().addWidget(self.progress)
        self.statusBar().addPermanentWidget(self.engines_label)
        self.update_engines_label()

    # --- документ ---
    def open_file(self) -> None:
        start = self.session.settings.last_folder or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(self, "Открыть документ", start, "Документы Word (*.docx)")
        if path:
            self.session.settings.last_folder = str(Path(path).parent)
            self.load_path(Path(path))

    def load_path(self, path: Path) -> None:
        try:
            self.session.open(Path(path))
        except DocxError as error:
            self.warn("Не удалось открыть файл", str(error))
            return
        self.setWindowTitle(f"Корректор {__version__} — {Path(path).name}")
        self.view.set_model(self.session.model)
        self.view.set_highlights(self.session, [])
        self.panel.set_items(self.session, [])
        self.start_check()

    def start_check(self) -> None:
        if self.session.model is None or (self.worker is not None and self.worker.isRunning()):
            return
        self.progress.setVisible(True)
        self.counters.setText("Проверяю…")
        self.worker = CheckWorker(self.session)
        self.worker.done.connect(self.on_check_done)
        self.worker.failed.connect(self.on_check_failed)
        self.worker.start()

    def on_check_done(self, _items) -> None:
        self.progress.setVisible(False)
        self.refresh()
        self.check_finished.emit()

    def on_check_failed(self, message: str) -> None:
        self.progress.setVisible(False)
        self.counters.setText("Проверка не удалась")
        self.warn("Проверка не удалась", message)
        self.check_finished.emit()

    def refresh(self, select_id: int | None = None) -> None:
        items = self.session.visible_items()
        self.view.set_model(self.session.model)
        self.view.selected_id = select_id
        self.view.set_highlights(self.session, items)
        self.panel.set_items(self.session, items)
        if select_id is not None:
            self.panel.select(select_id)
        counts = self.session.counts()
        self.counters.setText(
            f"Ошибок {counts[Level.ERROR]} · предупреждений {counts[Level.WARNING]} · подсказок {counts[Level.HINT]}"
        )
        self.update_engines_label()

    def update_engines_label(self) -> None:
        lt = next((s for s in self.session.statuses() if s.name == "lt"), None)
        if lt is None or lt.available:
            self.engines_label.setText("LanguageTool готов")
            self.engines_label.setStyleSheet("")
        else:
            self.engines_label.setText(f"Пунктуация русского недоступна: {lt.note}")
            self.engines_label.setStyleSheet("background: #ffe680; padding: 2px 6px;")

    # --- действия с замечаниями ---
    def on_selected(self, item_id: int) -> None:
        self.view.select(item_id)
        self.view.set_highlights(self.session, self.session.visible_items())

    def panel_select(self, item_id: int) -> None:
        self.panel.select(item_id)

    def _next_after(self, item_id: int) -> int | None:
        visible = [i.id for i in self.session.visible_items()]
        if not visible:
            return None
        later = [i for i in visible if i > item_id]
        return later[0] if later else visible[-1]

    def on_apply(self, item_id: int, replacement: str) -> None:
        self.session.apply(item_id, replacement)
        self.refresh(self._next_after(item_id))

    def on_skip(self, item_id: int) -> None:
        self.session.skip(item_id)
        self.refresh(self._next_after(item_id))

    def on_dictionary(self, item_id: int) -> None:
        self.session.add_to_dictionary(item_id)
        self.refresh(self._next_after(item_id))

    def on_disable(self, item_id: int) -> None:
        self.session.disable_rule(item_id)
        self.refresh(self._next_after(item_id))

    def toggle_category(self, keys: list[str], checked: bool) -> None:
        for key in keys:
            self.session.set_category(key, checked)
        if self.session.model is not None:
            self.refresh()

    # --- сохранение ---
    def save(self, with_comments: bool) -> Path | None:
        if self.session.model is None:
            return None
        target = self.session.save(with_comments)
        if self.interactive:
            box = QMessageBox(self)
            box.setWindowTitle("Сохранено")
            box.setText(f"Копия сохранена:\n{target}")
            open_button = box.addButton("Открыть в Word", QMessageBox.ButtonRole.ActionRole)
            box.addButton("Закрыть", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is open_button:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
        return target

    # --- прочее ---
    def show_help(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Справка")
        dialog.resize(720, 560)
        browser = QTextBrowser()
        text = self.help_text or "Инструкция не найдена."
        text += f"\n\nПапка словаря, правил и настроек: {self.session.user_dir}"
        browser.setPlainText(text)
        layout = QVBoxLayout(dialog)
        layout.addWidget(browser)
        dialog.exec() if self.interactive else dialog.show()

    def warn(self, title: str, message: str) -> None:
        if self.interactive:
            QMessageBox.warning(self, title, message)
        else:
            self.counters.setText(f"{title}: {message}")

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if any(url.toLocalFile().lower().endswith(".docx") for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local.lower().endswith(".docx"):
                self.load_path(Path(local))
                break
