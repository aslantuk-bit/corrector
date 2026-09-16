"""LanguageTool: локальный сервер на приложенной Java и клиент /v2/check."""

from __future__ import annotations

import json
import logging
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from corrector.core.issue import Category, Issue, Level
from corrector.engines.base import EngineStatus

log = logging.getLogger(__name__)

LT_CATEGORY_MAP = {
    "TYPOS": Category.SPELLING,
    "PUNCTUATION": Category.PUNCTUATION,
    "TYPOGRAPHY": Category.TYPOGRAPHY,
    "GRAMMAR": Category.GRAMMAR,
    "CASING": Category.GRAMMAR,
    "NEG": Category.GRAMMAR,
    "EXTEND": Category.GRAMMAR,
    "LOGIC": Category.GRAMMAR,
    "STYLE": Category.STYLE,
    "MISC": Category.STYLE,
}
LEVELS = {
    Category.SPELLING: Level.ERROR,
    Category.PUNCTUATION: Level.ERROR,
    Category.GRAMMAR: Level.ERROR,
    Category.TYPOGRAPHY: Level.WARNING,
    Category.STYLE: Level.WARNING,
}
SEPARATOR = "\n\n"


def level_for(category: Category) -> Level:
    return LEVELS[category]


class LTStartError(Exception):
    pass


class LTUnavailable(Exception):
    pass


def load_disabled_rules(path: Path) -> list[str]:
    try:
        lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return []
    rules = []
    for line in lines:
        rule = line.split("#", 1)[0].strip()
        if rule:
            rules.append(rule)
    return rules


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class LanguageToolServer:
    def __init__(self, java: Path, home: Path, config: Path | None = None, xmx: str = "768m", startup_timeout: float = 60) -> None:
        self.java, self.home, self.config, self.xmx, self.startup_timeout = Path(java), Path(home), config, xmx, startup_timeout
        self.port = 0
        self.process: subprocess.Popen | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self) -> None:
        jar = self.home / "languagetool-server.jar"
        if not self.java.exists():
            raise LTStartError(f"нет Java: {self.java}")
        if not jar.exists():
            raise LTStartError(f"нет LanguageTool: {jar}")
        self.port = _free_port()
        command = [str(self.java), f"-Xmx{self.xmx}", "-Djava.awt.headless=true", "-cp", str(jar),
                   "org.languagetool.server.HTTPServer", "--port", str(self.port), "--allow-origin"]
        if self.config is not None:
            command += ["--config", str(self.config)]
        extra = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
        log.info("запуск LanguageTool: %s", " ".join(command))
        self.process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                                        encoding="utf-8", errors="replace", **extra)
        deadline = time.time() + self.startup_timeout
        while time.time() < deadline:
            if self.process.poll() is not None:
                tail = (self.process.stderr.read() or "")[-800:]
                raise LTStartError(f"LanguageTool завершился при старте (код {self.process.returncode}): {tail.strip()}")
            try:
                with urllib.request.urlopen(f"{self.url}/v2/languages", timeout=2):
                    return
            except (urllib.error.URLError, OSError):
                time.sleep(0.3)
        self.stop()
        raise LTStartError(f"LanguageTool не ответил за {self.startup_timeout:g} с")

    def stop(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
        if self.process.stderr:
            self.process.stderr.close()
        self.process = None


class LanguageToolClient:
    def __init__(self, url: str, disabled_rules: list[str] | None = None, timeout: float = 120) -> None:
        self.url, self.disabled_rules, self.timeout = url.rstrip("/"), list(disabled_rules or []), timeout

    def languages(self) -> list[dict]:
        try:
            with urllib.request.urlopen(f"{self.url}/v2/languages", timeout=self.timeout) as response:
                return json.load(response)
        except (urllib.error.URLError, OSError, ValueError) as error:
            raise LTUnavailable(str(error)) from error

    def check_text(self, text: str, language: str = "ru-RU") -> list[dict]:
        fields = {"language": language, "text": text}
        if self.disabled_rules:
            fields["disabledRules"] = ",".join(self.disabled_rules)
        request = urllib.request.Request(f"{self.url}/v2/check", data=urllib.parse.urlencode(fields).encode("utf-8"))
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.load(response)["matches"]
        except (urllib.error.URLError, OSError, ValueError, KeyError) as error:
            raise LTUnavailable(str(error)) from error


def batches(paragraphs: list[tuple[int, str]], limit: int = 20000) -> list[list[tuple[int, str]]]:
    result: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    length = 0
    for index, text in paragraphs:
        extra = len(text) + (len(SEPARATOR) if current else 0)
        if current and length + extra > limit:
            result.append(current)
            current, length = [], 0
            extra = len(text)
        current.append((index, text))
        length += extra
    if current:
        result.append(current)
    return result


def join_batch(batch: list[tuple[int, str]]) -> tuple[str, list[tuple[int, int, int]]]:
    parts, offsets, position = [], [], 0
    for index, text in batch:
        if parts:
            position += len(SEPARATOR)
        offsets.append((index, position, len(text)))
        parts.append(text)
        position += len(text)
    return SEPARATOR.join(parts), offsets


def map_matches(matches: list[dict], offsets: list[tuple[int, int, int]]) -> list[Issue]:
    issues: list[Issue] = []
    for match in matches:
        start, end = match["offset"], match["offset"] + match["length"]
        for index, base, length in offsets:
            if base <= start and end <= base + length:
                category = LT_CATEGORY_MAP.get(match["rule"]["category"]["id"], Category.STYLE)
                issues.append(Issue(
                    paragraph=index, start=start - base, end=end - base, category=category, level=level_for(category),
                    rule_id=match["rule"]["id"], engine="lt", message=match.get("message", "").strip(),
                    suggestions=[r["value"] for r in match.get("replacements", [])[:5]],
                ))
                break
    return issues


class LanguageToolEngine:
    name = "lt"

    def __init__(self, client: LanguageToolClient, batch_limit: int = 20000) -> None:
        self.client, self.batch_limit = client, batch_limit
        self.available, self.note = True, ""

    def status(self) -> EngineStatus:
        return EngineStatus(self.name, self.available, self.note)

    def check(self, paragraphs: list[tuple[int, str]]) -> list[Issue]:
        if not self.available:
            return []
        issues: list[Issue] = []
        for batch in batches(paragraphs, self.batch_limit):
            text, offsets = join_batch(batch)
            try:
                matches = self.client.check_text(text)
            except LTUnavailable as error:
                self.available, self.note = False, f"LanguageTool недоступен: {error}"
                log.warning(self.note)
                return issues
            issues += map_matches(matches, offsets)
        return issues
