"""Документ Word как список абзацев с картой фрагментов форматирования (run)."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

import docx
from docx.document import Document as _Document
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.hyperlink import Hyperlink
from docx.text.paragraph import Paragraph
from docx.text.run import Run

BROKEN_MESSAGE = (
    "Файл повреждён, защищён паролем или это не документ Word (.docx). "
    "Старый формат .doc откройте в Word и сохраните как .docx."
)


class DocxError(Exception):
    pass


@dataclass
class RunSpan:
    run: Run
    start: int
    end: int


@dataclass
class Para:
    index: int
    text: str
    runs: list[RunSpan]
    where: str
    paragraph: Paragraph


@dataclass
class DocumentModel:
    path: Path
    document: _Document
    paragraphs: list[Para]

    def texts(self) -> list[str]:
        return [p.text for p in self.paragraphs]


def load(path: Path) -> DocumentModel:
    path = Path(path)
    if not path.is_file():
        raise DocxError(f"Файл не найден: {path}")
    try:
        document = docx.Document(str(path))
    except (PackageNotFoundError, KeyError, ValueError, zipfile.BadZipFile, OSError) as error:
        raise DocxError(BROKEN_MESSAGE) from error
    paragraphs: list[Para] = []

    def add(paragraph: Paragraph, where: str) -> None:
        spans, parts, position = [], [], 0
        for item in paragraph.iter_inner_content():
            if isinstance(item, Run):
                runs = [item]
            elif isinstance(item, Hyperlink):
                runs = list(item.runs)
            else:
                runs = []
            for run in runs:
                text = run.text
                if text:
                    spans.append(RunSpan(run, position, position + len(text)))
                    parts.append(text)
                    position += len(text)
        paragraphs.append(Para(len(paragraphs), "".join(parts), spans, where, paragraph))

    def walk(container, where: str) -> None:
        for item in container.iter_inner_content():
            if isinstance(item, Paragraph):
                add(item, where)
            elif isinstance(item, Table):
                seen = []
                for row in item.rows:
                    for cell in row.cells:
                        if any(cell._tc is tc for tc in seen):
                            continue
                        seen.append(cell._tc)
                        walk(cell, "table")

    walk(document, "body")
    for section in document.sections:
        for paragraph in section.header.paragraphs:
            add(paragraph, "header")
        for paragraph in section.footer.paragraphs:
            add(paragraph, "footer")
    return DocumentModel(path, document, paragraphs)
