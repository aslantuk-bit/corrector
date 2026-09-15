"""Скачивает сторонние артефакты по sborka/artifacts.lock, сверяет SHA-256 и распаковывает в vendor/<имя>/."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "sborka" / "artifacts.lock"
VENDOR = ROOT / "vendor"
STAMP = ".artifact-sha256"


def load_lock(path: Path = LOCK) -> dict[str, dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url) as response, dest.open("wb") as out:
        shutil.copyfileobj(response, out)


def unpack(archive: Path, target: Path, unpack_root: str, inner: str | None) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="unpack-", dir=target.parent))
    try:
        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive) as z:
                z.extractall(tmp)
        else:
            with tarfile.open(archive) as t:
                t.extractall(tmp, filter="data")
        source = tmp / unpack_root
        if inner:
            source = source / inner
        if not source.is_dir():
            raise FileNotFoundError(f"в архиве {archive.name} нет папки {unpack_root}/{inner or ''}")
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(source), str(target))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def fetch(name: str, entry: dict, vendor: Path = VENDOR) -> Path:
    target = vendor / name
    stamp = target / STAMP
    if stamp.exists() and stamp.read_text().strip() == entry["sha256"]:
        return target
    cache = vendor / "_cache"
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / entry["url"].rsplit("/", 1)[-1]
    if not archive.exists() or sha256_of(archive) != entry["sha256"]:
        download(entry["url"], archive)
    actual = sha256_of(archive)
    if actual != entry["sha256"]:
        archive.unlink(missing_ok=True)
        raise ValueError(f"{name}: контрольная сумма не совпала: {actual} вместо {entry['sha256']}")
    unpack(archive, target, entry["unpack_root"], entry.get("inner"))
    stamp.write_text(entry["sha256"])
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Скачать артефакты из artifacts.lock в vendor/")
    parser.add_argument("names", nargs="+", help="имена записей из artifacts.lock")
    parser.add_argument("--vendor", type=Path, default=VENDOR)
    args = parser.parse_args(argv)
    lock = load_lock()
    for name in args.names:
        if name not in lock:
            print(f"нет в artifacts.lock: {name}", file=sys.stderr)
            return 2
        print(f"{name} → {fetch(name, lock[name], args.vendor)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
