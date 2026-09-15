"""Настройки пользователя в настройки.json; испорченный файл не роняет программу."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

FILE_NAME = "настройки.json"
log = logging.getLogger(__name__)


@dataclass
class Settings:
    categories: dict[str, bool] = field(
        default_factory=lambda: {"spelling": True, "grammar": True, "punctuation": True, "typography": True, "style": True}
    )
    disabled_rules: list[str] = field(default_factory=list)
    sentence_words_limit: int = 60
    language: str = "auto"  # auto | ru | kk
    last_folder: str = ""

    @classmethod
    def load(cls, path: Path) -> "Settings":
        settings = cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return settings
        except (OSError, ValueError) as error:
            log.warning("настройки не прочитаны (%s), взяты значения по умолчанию", error)
            return settings
        if not isinstance(data, dict):
            return settings
        for key, value in data.items():
            if hasattr(settings, key) and isinstance(value, type(getattr(settings, key))):
                setattr(settings, key, value)
        return settings

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
