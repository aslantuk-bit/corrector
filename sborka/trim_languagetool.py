"""Урезает снимок LanguageTool до русского: данные других языков и словарные jar долой, классы остаются."""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

KEEP_LANGS = {"ru"}
LANG_DIR = re.compile(r"[a-z]{2,3}(_[A-Z]{2})?")
DROP_JARS = [
    "dutch-pos-dict.jar", "languagetool-ga-dicts.jar", "catalan-pos-dict.jar", "lucene-gosen-ipadic.jar", "hanlp.jar",
    "morfologik-ukrainian-lt.jar", "opennlp-postag-models.jar", "opennlp-chunk-models.jar", "opennlp-tokenize-models.jar",
    "english-pos-dict.jar", "portuguese-pos-dict.jar", "spanish-pos-dict.jar", "morfologik-crh-lt.jar", "german-pos-dict.jar",
    "french-pos-dict.jar", "asturian-pos-dict.jar", "languagetool-core-tests.jar", "junit.jar", "hamcrest-core.jar",
]
DROP_FILES = ["languagetool.jar", "languagetool-commandline.jar", "testrules.bat", "testrules.sh"]


def trim(source: Path, target: Path) -> int:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    removed = 0
    resources = target / "org" / "languagetool" / "resource"
    for folder in resources.iterdir():
        if folder.is_dir() and LANG_DIR.fullmatch(folder.name) and folder.name not in KEEP_LANGS:
            for file in folder.rglob("*"):
                if file.is_file() and file.name != "common_words.txt":
                    file.unlink()
                    removed += 1
    for name in DROP_JARS:
        jar = target / "libs" / name
        if jar.exists():
            jar.unlink()
            removed += 1
    for name in DROP_FILES:
        file = target / name
        if file.exists():
            file.unlink()
            removed += 1
    return removed


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 2:
        print("использование: trim_languagetool.py <папка снимка> <папка результата>", file=sys.stderr)
        return 2
    print("удалено:", trim(Path(args[0]), Path(args[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
