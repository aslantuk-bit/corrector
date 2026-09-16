"""Фоновые потоки: сборка движков при старте и проверка документа."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from corrector.core.userdict import UserDictionary
from corrector.engines import factory


class EnginesWorker(QThread):
    ready = Signal(object)
    failed = Signal(str)

    def __init__(self, user_dict: UserDictionary, user_dir: Path, no_lt: bool = False) -> None:
        super().__init__()
        self.user_dict, self.user_dir, self.no_lt = user_dict, user_dir, no_lt

    def run(self) -> None:
        try:
            self.ready.emit(factory.build_engines(self.user_dict, no_lt=self.no_lt, user_dir=self.user_dir))
        except Exception as error:  # noqa: BLE001 — любая ошибка старта должна дойти до окна
            self.failed.emit(str(error))


class CheckWorker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, session) -> None:
        super().__init__()
        self.session = session

    def run(self) -> None:
        try:
            self.done.emit(self.session.check())
        except Exception as error:  # noqa: BLE001
            self.failed.emit(str(error))
