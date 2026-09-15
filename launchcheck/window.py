"""Окно с отчётом: заголовок-вывод, текст, кнопки «Скопировать» и «Закрыть»."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from launchcheck import report

SUCCESS = "Всё запустилось. Пришлите автору файл отчёт_запуска.txt"
FAILURE = "Есть проблема. Пришлите автору файл отчёт_запуска.txt"
COPIED = "Отчёт скопирован — вставьте его в сообщение автору"


class ReportWindow(QMainWindow):
    def __init__(self, text: str, base_dir: Path) -> None:
        super().__init__()
        self.text = text
        self.base_dir = base_dir
        self.setWindowTitle("Проверка запуска Корректора")
        self.resize(760, 520)

        self.headline = QLabel(SUCCESS if report.OK_LINE in text else FAILURE)
        self.headline.setStyleSheet("font-size: 16px; font-weight: bold; padding: 6px;")
        self.view = QPlainTextEdit(text)
        self.view.setReadOnly(True)
        self.copy_button = QPushButton("Скопировать")
        self.copy_button.clicked.connect(self.copy_report)
        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.close)

        buttons = QHBoxLayout()
        buttons.addWidget(self.copy_button)
        buttons.addStretch()
        buttons.addWidget(self.close_button)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.headline)
        layout.addWidget(self.view)
        layout.addLayout(buttons)
        self.setCentralWidget(central)

    def copy_report(self) -> None:
        QApplication.clipboard().setText(self.text)
        self.headline.setText(COPIED)


def show(text: str, base_dir: Path) -> int:
    app = QApplication.instance() or QApplication([])
    window = ReportWindow(text, base_dir)
    window.show()
    return app.exec()
