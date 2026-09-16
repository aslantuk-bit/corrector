"""Правка документа: замена внутри run, разрезание run, примечания Word, сохранение копии."""

from __future__ import annotations

import copy
from pathlib import Path

from docx.text.run import Run

from corrector.docx_io.model import DocumentModel, Para, RunSpan

AUTHOR = "Корректор"
SUFFIX = "_проверено"


def _rebuild_spans(para: Para, runs: list[Run]) -> None:
    spans, parts, position = [], [], 0
    for run in runs:
        text = run.text
        if text:
            spans.append(RunSpan(run, position, position + len(text)))
            parts.append(text)
            position += len(text)
    para.runs = spans
    para.text = "".join(parts)


def split_run(run: Run, offset: int) -> tuple[Run, Run]:
    """Разрезает run на два с одинаковым форматированием; левый получает первые offset символов."""
    text = run.text
    new_r = copy.deepcopy(run._r)
    run._r.addnext(new_r)
    right = Run(new_r, run._parent)
    run.text = text[:offset]
    right.text = text[offset:]
    return run, right


def _runs_in_order(para: Para) -> list[Run]:
    return [span.run for span in para.runs]


def _ensure_boundary(para: Para, position: int) -> None:
    """Делает position границей между run, при необходимости разрезая run."""
    for span in list(para.runs):
        if span.start < position < span.end:
            left, right = split_run(span.run, position - span.start)
            runs = _runs_in_order(para)
            index = runs.index(left)
            runs.insert(index + 1, right)
            _rebuild_spans(para, runs)
            return


def apply_replacement(para: Para, start: int, end: int, replacement: str) -> int:
    """Заменяет текст [start, end) абзаца, не трогая форматирование; возвращает сдвиг длины."""
    _ensure_boundary(para, start)
    _ensure_boundary(para, end)
    covered = [span for span in para.runs if start <= span.start and span.end <= end]
    if not covered:
        raise ValueError("отрезок не совпадает с границами run")
    first = covered[0].run
    first.text = replacement
    for span in covered[1:]:
        span.run.text = ""
    runs = [run for run in _runs_in_order(para) if run.text or run is first]
    _rebuild_spans(para, runs)
    return len(replacement) - (end - start)


def add_comment(model: DocumentModel, para: Para, start: int, end: int, text: str, author: str = AUTHOR) -> bool:
    """Примечание Word к фрагменту [start, end); в колонтитулах примечания невозможны — возвращает False."""
    if para.where in ("header", "footer"):
        return False
    _ensure_boundary(para, start)
    _ensure_boundary(para, end)
    covered = [span.run for span in para.runs if start <= span.start and span.end <= end]
    if not covered:
        return False
    model.document.add_comment(runs=[covered[0], covered[-1]], text=text, author=author, initials="К")
    return True


def output_path(original: Path, out_dir: Path | None = None) -> Path:
    original = Path(original)
    folder = Path(out_dir) if out_dir is not None else original.parent
    candidate = folder / f"{original.stem}{SUFFIX}{original.suffix}"
    number = 2
    while candidate.exists():
        candidate = folder / f"{original.stem}{SUFFIX} ({number}){original.suffix}"
        number += 1
    return candidate


def save_copy(model: DocumentModel, target: Path) -> Path:
    target = Path(target)
    model.document.save(str(target))
    return target
