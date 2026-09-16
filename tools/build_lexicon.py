"""Лексиконы и имена из корпуса: слова, неизвестные словарю, но частые в актах разных судов (только Mac)."""

from __future__ import annotations

import argparse
import collections
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from corrector.core import paths  # noqa: E402
from corrector.core.text import LETTERS, words  # noqa: E402
from corrector.engines.hunspell import SpellDictionary  # noqa: E402
from corrector.engines.spell import load_lexicon  # noqa: E402

DB = Path.home() / "court-analytics" / "corpus.db"
LATIN = re.compile(r"[A-Za-z]")
KK_SHARE = "(length(text) - length(replace(replace(replace(replace(text,'ә',''),'қ',''),'ң',''),'ү',''))) * 100.0 / length(text)"
SENTENCE_START = re.compile(rf"(?:^|[.!?»]\s+)([{LETTERS}])", re.MULTILINE)


def scan(db: Path, lang: str):
    con = sqlite3.connect(db)
    condition = "share > 1" if lang == "kk" else "share <= 1"
    # суд как ключ: код дела до дефиса в имени файла («6АП-2598.docx» → «6АП»), иначе папка инстанции
    query = (f"select d.id, d.text, coalesce(a.court, upper(substr(d.filename, 1, instr(d.filename, '-') - 1))) "
             f"from (select id, text, filename, {KK_SHARE} as share from documents where text is not null and length(text) > 500) d "
             f"left join acts a on a.doc_id = d.id where {condition}")
    lower_docs, lower_courts, examples = collections.defaultdict(set), collections.defaultdict(set), {}
    name_docs, name_courts = collections.defaultdict(set), collections.defaultdict(set)
    frequency = collections.Counter()
    for doc_id, text, court in con.execute(query):
        starts = {m.start(1) for m in SENTENCE_START.finditer(text)}
        for token in words(text):
            w = token.text
            if len(w) < 3 or any(ch.isdigit() for ch in w) or LATIN.search(w):
                continue
            frequency[w.lower()] += 1
            if w[0].isupper() and w[1:].islower() and token.start not in starts:
                name_docs[w].add(doc_id)
                name_courts[w].add(court)
            elif w.islower():
                lower_docs[w].add(doc_id)
                lower_courts[w].add(court)
                examples.setdefault(w, text[max(0, token.start - 30):token.end + 30].replace("\n", " "))
    return lower_docs, lower_courts, examples, name_docs, name_courts, frequency


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", choices=["ru", "kk"], required=True)
    parser.add_argument("--min-docs", type=int, default=5)
    parser.add_argument("--min-courts", type=int, default=3)
    parser.add_argument("--stop", type=int, default=300)
    parser.add_argument("--db", type=Path, default=DB)
    args = parser.parse_args(argv)
    data = paths.data_dir()
    review = data / "review"
    review.mkdir(exist_ok=True)
    dictionary = SpellDictionary(data / args.lang / ("ru_RU" if args.lang == "ru" else "kk_KZ"))
    lexicon_path = data / f"lexicon_{args.lang}_legal.txt"
    known = load_lexicon(lexicon_path)
    lower_docs, lower_courts, examples, name_docs, name_courts, frequency = scan(args.db, args.lang)

    morph = None
    if args.lang == "ru":
        import pymorphy3

        morph = pymorphy3.MorphAnalyzer()

    accepted, candidates = [], []
    for w, docs in sorted(lower_docs.items(), key=lambda kv: -len(kv[1])):
        if len(docs) < args.min_docs or len(lower_courts[w]) < args.min_courts or w in known or dictionary.known(w):
            continue
        parts = [p for p in w.split("-") if p]
        if len(parts) > 1 and all(dictionary.known(p) for p in parts):
            accepted.append(w)
            continue
        if morph is not None and any(p.is_known for p in morph.parse(w)):
            accepted.append(w)
            continue
        # для казахского автоприём по основе не используется: стеммер принимает частые опечатки («қамтамсыз», «сәйке»)
        candidates.append((w, len(docs), len(lower_courts[w]), examples[w]))

    with lexicon_path.open("a", encoding="utf-8") as stream:
        stream.write(f"\n# Из корпуса (tools/build_lexicon.py, не менее {args.min_docs} актов и {args.min_courts} судов)\n")
        stream.writelines(w + "\n" for w in accepted)
    (review / f"lexicon_{args.lang}_candidates.tsv").write_text(
        "слово\tактов\tсудов\tпример\n" + "".join(f"{w}\t{d}\t{c}\t{e}\n" for w, d, c, e in candidates), encoding="utf-8")

    # имя — то, что почти не пишется со строчной: частая опечатка («Соттын») встречается и строчными, имя — нет
    names = [w for w, docs in sorted(name_docs.items(), key=lambda kv: -len(kv[1]))
             if len(docs) >= 3 and len(name_courts[w]) >= 2 and not dictionary.known(w)
             and len(lower_docs.get(w.lower(), ())) <= 0.1 * len(docs)]
    (data / f"names_corpus_{args.lang}.txt").write_text(
        "# Имена и названия из корпуса (регистр важен): не менее 3 актов и 2 судов\n" + "\n".join(names) + "\n", encoding="utf-8")
    (data / f"stop_{args.lang}.txt").write_text(
        "# Самые частые слова корпуса для правила повторов\n" + "\n".join(w for w, _ in frequency.most_common(args.stop)) + "\n",
        encoding="utf-8")
    print(f"{args.lang}: в лексикон {len(accepted)}, кандидатов {len(candidates)}, имён {len(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
