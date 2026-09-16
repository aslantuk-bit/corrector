"""Запуск окна: заставка → движки в фоне → главное окно."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox

from corrector import __version__
from corrector.app.session import Session
from corrector.app.window import MainWindow
from corrector.app.worker import EnginesWorker
from corrector.core import paths
from corrector.core.log import setup_logging
from corrector.core.userdict import FILE_NAME as DICT_FILE
from corrector.core.userdict import UserDictionary


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    app = QApplication(argv)
    user_dir = paths.user_dir()
    log_path = setup_logging(user_dir)

    def excepthook(kind, value, tb) -> None:
        details = "".join(traceback.format_exception(kind, value, tb))
        with open(log_path, "a", encoding="utf-8") as stream:
            stream.write(details)
        QMessageBox.critical(None, "Что-то пошло не так", f"{value}\n\nЖурнал: {log_path}")

    sys.excepthook = excepthook

    splash = QLabel("Запуск Корректора…\nПри работе с флешки первый старт может занять до минуты.")
    splash.setAlignment(Qt.AlignmentFlag.AlignCenter)
    splash.setWindowFlags(Qt.WindowType.SplashScreen)
    splash.setStyleSheet("font-size: 15px; padding: 28px; background: white;")
    splash.show()
    app.processEvents()

    help_text = ""
    manual = paths.data_dir() / "ИНСТРУКЦИЯ.txt"
    if manual.exists():
        help_text = manual.read_text(encoding="utf-8")
    user_dict = UserDictionary(user_dir / DICT_FILE)
    state: dict = {}

    def on_ready(engines) -> None:
        window = MainWindow(Session(engines, user_dir, user_dict), help_text)
        state["window"] = window
        window.show()
        splash.close()
        files = [a for a in argv[1:] if a.lower().endswith(".docx")]
        if files:
            window.load_path(Path(files[0]))

    def on_failed(message: str) -> None:
        splash.close()
        QMessageBox.critical(None, "Не удалось запустить проверку", f"{message}\n\nЖурнал: {log_path}")
        app.quit()

    worker = EnginesWorker(user_dict, user_dir, no_lt="--no-lt" in argv)
    worker.ready.connect(on_ready)
    worker.failed.connect(on_failed)
    state["worker"] = worker
    worker.start()
    code = app.exec()
    engines = getattr(state.get("window"), "session", None)
    if engines is not None:
        engines.engines.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
