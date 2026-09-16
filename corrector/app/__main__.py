"""Запуск окна: заставка → движки в фоне → главное окно."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox

from corrector import __version__
from corrector.app.session import Session
from corrector.app.window import MainWindow
from corrector.app.worker import EnginesWorker
from corrector.core import paths
from corrector.core.issue import Level
from corrector.core.log import setup_logging
from corrector.core.userdict import FILE_NAME as DICT_FILE
from corrector.core.userdict import UserDictionary


def run_self_test(app: QApplication, window: MainWindow, path: Path | None, out_dir: Path | None) -> None:
    """Самопроверка окна на сборщике: открыть файл, дождаться проверки, сохранить копию с примечаниями, выйти с кодом 0."""
    out = out_dir or (path.parent if path else Path.cwd())
    report = out / "самопроверка.txt"

    def finish(code: int, text: str) -> None:
        out.mkdir(parents=True, exist_ok=True)
        report.write_text(text + "\n", encoding="utf-8")
        app.exit(code)

    if path is None:
        finish(2, "самопроверка: не указан файл .docx")
        return

    def on_checked() -> None:
        try:
            target = window.save(with_comments=True) if out_dir is None else window.session.save(True, out_dir)
            counts = window.session.counts()
            counts = f"ошибок {counts[Level.ERROR]}, предупреждений {counts[Level.WARNING]}, подсказок {counts[Level.HINT]}"
            finish(0, f"самопроверка: окно открылось, {counts}; {window.engines_label.text()}; копия: {target}")
        except Exception as error:  # noqa: BLE001
            finish(1, f"самопроверка: сохранение не удалось: {error}")

    window.check_finished.connect(on_checked)
    QTimer.singleShot(180_000, lambda: finish(3, "самопроверка: проверка не завершилась за 180 с"))
    window.load_path(path)


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

    self_test = "--self-test" in argv
    out_dir = Path(argv[argv.index("--out") + 1]) if "--out" in argv and argv.index("--out") + 1 < len(argv) else None

    def on_ready(engines) -> None:
        window = MainWindow(Session(engines, user_dir, user_dict), help_text, interactive=not self_test)
        state["window"] = window
        window.show()
        splash.close()
        files = [a for a in argv[1:] if a.lower().endswith(".docx")]
        if self_test:
            run_self_test(app, window, Path(files[0]) if files else None, out_dir)
        elif files:
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
