from pathlib import Path

from PySide6.QtWidgets import QApplication

from launchcheck import report
from launchcheck.window import ReportWindow


def test_window_shows_report_and_success_headline(qtbot):
    text = "Java: OK — openjdk\n\n" + report.OK_LINE + "\nОтчёт сохранён: E:\\отчёт_запуска.txt\n"
    window = ReportWindow(text, Path("E:/"))
    qtbot.addWidget(window)
    assert window.windowTitle() == "Проверка запуска Корректора"
    assert window.headline.text() == "Всё запустилось. Пришлите автору файл отчёт_запуска.txt"
    assert window.view.toPlainText() == text
    assert window.view.isReadOnly()


def test_window_failure_headline(qtbot):
    window = ReportWindow("Java: ОШИБКА — файл не найден\n\n" + report.FAIL_LINE + "\n", Path("E:/"))
    qtbot.addWidget(window)
    assert window.headline.text() == "Есть проблема. Пришлите автору файл отчёт_запуска.txt"


def test_copy_button_puts_text_on_clipboard(qtbot):
    text = "строка отчёта\n" + report.OK_LINE + "\n"
    window = ReportWindow(text, Path("E:/"))
    qtbot.addWidget(window)
    window.copy_button.click()
    assert QApplication.clipboard().text() == text
    assert window.headline.text() == "Отчёт скопирован — вставьте его в сообщение автору"
