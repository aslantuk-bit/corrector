"""Выборка актов из corpus.db в .docx для измерения шума правил (только Mac)."""

from __future__ import annotations

import argparse
import random
import sqlite3
from pathlib import Path

import docx

DB = Path.home() / "court-analytics" / "corpus.db"
KK_SHARE = "(length(text) - length(replace(replace(replace(replace(text,'ә',''),'қ',''),'ң',''),'ү',''))) * 100.0 / length(text)"


def sample(db: Path, out: Path, ru: int, kk: int, seed: int) -> dict[str, int]:
    con = sqlite3.connect(db)
    rows = con.execute(f"select id, text, {KK_SHARE} as share from documents where length(text) between 4000 and 30000").fetchall()
    random.Random(seed).shuffle(rows)
    counts = {"ru": 0, "kk": 0}
    for doc_id, text, share in rows:
        lang = "kk" if share > 1 else "ru"
        limit = kk if lang == "kk" else ru
        if counts[lang] >= limit:
            continue
        target = out / lang / f"акт_{doc_id}.docx"
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            document = docx.Document()
            for line in text.splitlines():
                if line.strip():
                    document.add_paragraph(line.strip())
            document.save(str(target))
        counts[lang] += 1
        if counts["ru"] >= ru and counts["kk"] >= kk:
            break
    return counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ru", type=int, default=60)
    parser.add_argument("--kk", type=int, default=60)
    parser.add_argument("--out", type=Path, default=Path("vendor/corpus-sample"))
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--db", type=Path, default=DB)
    args = parser.parse_args(argv)
    print(sample(args.db, args.out, args.ru, args.kk, args.seed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
