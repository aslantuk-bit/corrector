"""Главное окно Корректора."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from corrector import __version__
from corrector.app import theme
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
        self.resize(1240, 800)
        self.setAcceptDrops(True)
        self.setStyleSheet(theme.STYLE)

        header = QWidget()
        header.setObjectName("header")
        header.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title = QLabel("Корректор")
        title.setObjectName("title")
        subtitle = QLabel("Орфография, пунктуация и стиль документов Word на русском и казахском")
        subtitle.setObjectName("subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        self.open_button = QPushButton("Открыть документ")
        self.open_button.setProperty("kind", "primary")
        self.open_button.clicked.connect(self.open_file)
        self.check_button = QPushButton("Проверить снова")
        self.check_button.clicked.connect(self.start_check)
        self.save_button = QPushButton("Сохранить копию")
        self.save_button.clicked.connect(lambda: self.save(False))
        self.save_comments_button = QPushButton("Сохранить с примечаниями")
        self.save_comments_button.clicked.connect(lambda: self.save(True))
        self.help_button = QPushButton("Справка")
        self.help_button.setProperty("kind", "quiet")
        self.help_button.clicked.connect(self.show_help)
        self.open_button.setToolTip("Выбрать документ Word (.docx); можно также перетащить файл в окно")
        self.check_button.setToolTip("Проверить открытый документ ещё раз")
        self.save_button.setToolTip("Сохранить копию «имя_проверено.docx» с внесёнными исправлениями")
        self.save_comments_button.setToolTip("То же плюс примечания Word к оставшимся замечаниям")
        self.help_button.setToolTip("Инструкция и слово от автора")
        for button in (self.open_button, self.check_button, self.save_button, self.save_comments_button, self.help_button):
            button.setFixedHeight(34)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            header_layout.addWidget(button)
            header_layout.addSpacing(6)
        self.update_buttons()

        self.boxes: list[tuple[QCheckBox, list[str]]] = []
        categories = QHBoxLayout()
        categories.setContentsMargins(0, 0, 0, 0)
        categories.setSpacing(8)
        categories.addWidget(QLabel("Показывать:"))
        for title_text, keys in CATEGORY_BOXES:
            box = QCheckBox(title_text)
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
        self.view.document().setDocumentMargin(28)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.view)
        splitter.addWidget(self.panel)
        splitter.setSizes([780, 460])

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header, 0)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 12, 20, 12)
        body_layout.setSpacing(10)
        body_layout.addLayout(categories)
        body_layout.addWidget(splitter)
        layout.addWidget(body, 1)
        self.setCentralWidget(central)

        self.counters = QLabel("Откройте документ .docx или перетащите его в окно")
        self.counters.setTextFormat(Qt.TextFormat.RichText)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setMaximumWidth(160)
        self.engines_label = QLabel("")
        self.engines_label.setObjectName("engine")
        self.signature = QLabel(theme.SIGNATURE)
        self.signature.setObjectName("signature")
        self.statusBar().addWidget(self.counters, 1)
        self.statusBar().addWidget(self.progress)
        self.statusBar().addPermanentWidget(self.engines_label)
        self.statusBar().addPermanentWidget(self.signature)
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
        self.update_buttons()
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
        self.counters.setText(theme.counters_html(counts))
        self.update_engines_label()

    def update_buttons(self) -> None:
        """Кнопки, которым нужен открытый документ, выключены, пока его нет."""
        loaded = self.session.model is not None
        for button in (self.check_button, self.save_button, self.save_comments_button):
            button.setEnabled(loaded)

    def update_engines_label(self) -> None:
        lt = next((s for s in self.session.statuses() if s.name == "lt"), None)
        if lt is None or lt.available:
            self.engines_label.setText("LanguageTool готов")
            self.engines_label.setProperty("state", "on")
        else:
            self.engines_label.setText(f"Пунктуация русского недоступна: {lt.note}")
            self.engines_label.setProperty("state", "off")
        self.engines_label.style().unpolish(self.engines_label)
        self.engines_label.style().polish(self.engines_label)

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
        text += f"\n\nПапка словаря, правил и настроек: {self.session.user_dir}\n\nКорректор {__version__}. {theme.SIGNATURE}"
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
