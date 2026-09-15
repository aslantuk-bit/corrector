"""Контекст абзаца и документа для правил: токены, предложения, язык, ресурсы."""

from __future__ import annotations

from dataclasses import dataclass, field

from corrector.core.settings import Settings
from corrector.core.text import Token, sentences, tokenize
from corrector.docx_io.model import DocumentModel
from corrector.rules.resources import RuleResources


@dataclass
class ParaContext:
    index: int
    text: str
    lang: str
    where: str
    tokens: list[Token]
    words: list[Token]
    sentences: list[tuple[int, int]]

    def sentence_of(self, position: int) -> tuple[int, int] | None:
        for start, end in self.sentences:
            if start <= position < end:
                return start, end
        return None

    def word_before(self, token: Token) -> Token | None:
        previous = [t for t in self.tokens if t.end <= token.start and t.kind != "space"]
        return previous[-1] if previous else None


@dataclass
class DocContext:
    paragraphs: list[ParaContext]
    settings: Settings
    resources: RuleResources
    extra: dict = field(default_factory=dict)


def build_contexts(model: DocumentModel, languages: list[str], settings: Settings, resources: RuleResources) -> DocContext:
    paragraphs = []
    for para, lang in zip(model.paragraphs, languages):
        tokens = tokenize(para.text)
        paragraphs.append(ParaContext(
            index=para.index, text=para.text, lang=lang, where=para.where, tokens=tokens,
            words=[t for t in tokens if t.kind == "word"],
            sentences=sentences(para.text, "kk" if lang == "kk" else "ru"),
        ))
    return DocContext(paragraphs, settings, resources)
