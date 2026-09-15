"""Журнал в logs/corrector.log с ротацией: пять файлов по мегабайту."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path


def setup_logging(user_dir: Path) -> Path:
    logs = user_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    path = logs / "corrector.log"
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(getattr(h, "baseFilename", None) == str(path) for h in root.handlers):
        handler = logging.handlers.RotatingFileHandler(path, maxBytes=1_000_000, backupCount=4, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(handler)
    return path
