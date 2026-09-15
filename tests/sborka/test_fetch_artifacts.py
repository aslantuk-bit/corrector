import hashlib
import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from sborka import fetch_artifacts as fa


def make_zip(path: Path, files: dict[str, bytes]) -> str:
    with zipfile.ZipFile(path, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_targz(path: Path, files: dict[str, bytes]) -> str:
    with tarfile.open(path, "w:gz") as t:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_lock_file_has_both_jres():
    lock = fa.load_lock()
    assert set(lock) >= {"jre-windows-x64", "jre-mac-aarch64"}
    for entry in lock.values():
        assert len(entry["sha256"]) == 64
        assert entry["url"].startswith("https://")
        assert entry.get("unpack_root") or entry.get("path")


def test_sha256_of(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"abc")
    assert fa.sha256_of(f) == hashlib.sha256(b"abc").hexdigest()


def test_fetch_zip_unpacks_root_and_writes_stamp(tmp_path):
    archive = tmp_path / "jre.zip"
    digest = make_zip(archive, {"root-1/bin/java.exe": b"java", "root-1/release": b"JAVA_VERSION=21"})
    entry = {"url": archive.as_uri(), "sha256": digest, "unpack_root": "root-1"}
    target = fa.fetch("jre-test", entry, vendor=tmp_path / "vendor")
    assert target == tmp_path / "vendor" / "jre-test"
    assert (target / "bin" / "java.exe").read_bytes() == b"java"
    assert (target / ".artifact-sha256").read_text() == digest


def test_fetch_targz_with_inner_folder(tmp_path):
    archive = tmp_path / "jre.tar.gz"
    digest = make_targz(archive, {"root-1/Contents/Home/bin/java": b"java"})
    entry = {"url": archive.as_uri(), "sha256": digest, "unpack_root": "root-1", "inner": "Contents/Home"}
    target = fa.fetch("jre-mac", entry, vendor=tmp_path / "vendor")
    assert (target / "bin" / "java").read_bytes() == b"java"


def test_fetch_rejects_wrong_checksum(tmp_path):
    archive = tmp_path / "jre.zip"
    make_zip(archive, {"root-1/bin/java.exe": b"java"})
    entry = {"url": archive.as_uri(), "sha256": "0" * 64, "unpack_root": "root-1"}
    with pytest.raises(ValueError, match="контрольная сумма"):
        fa.fetch("jre-bad", entry, vendor=tmp_path / "vendor")
    assert not (tmp_path / "vendor" / "jre-bad").exists()


def test_fetch_skips_when_stamp_matches(tmp_path):
    archive = tmp_path / "jre.zip"
    digest = make_zip(archive, {"root-1/bin/java.exe": b"java"})
    entry = {"url": archive.as_uri(), "sha256": digest, "unpack_root": "root-1"}
    vendor = tmp_path / "vendor"
    fa.fetch("jre-test", entry, vendor=vendor)
    archive.unlink()  # второй раз скачивать нечего — и не нужно
    assert fa.fetch("jre-test", entry, vendor=vendor) == vendor / "jre-test"


def test_main_unknown_name_returns_two(capsys):
    assert fa.main(["нет-такого"]) == 2
    assert "нет в artifacts.lock" in capsys.readouterr().err


def test_fetch_file_writes_to_path_and_verifies(tmp_path):
    source = tmp_path / "src.dic"
    source.write_bytes(b"word/1\n")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    entry = {"url": source.as_uri(), "sha256": digest, "path": "data/x/x.dic"}
    target = fa.fetch_file("x.dic", entry, root=tmp_path / "repo")
    assert target == tmp_path / "repo" / "data" / "x" / "x.dic"
    assert target.read_bytes() == b"word/1\n"


def test_fetch_file_skips_when_present_and_matching(tmp_path):
    source = tmp_path / "src.dic"
    source.write_bytes(b"word/1\n")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    entry = {"url": source.as_uri(), "sha256": digest, "path": "data/x/x.dic"}
    fa.fetch_file("x.dic", entry, root=tmp_path / "repo")
    source.unlink()
    assert fa.fetch_file("x.dic", entry, root=tmp_path / "repo").exists()


def test_fetch_file_rejects_wrong_checksum(tmp_path):
    source = tmp_path / "src.dic"
    source.write_bytes(b"word/1\n")
    entry = {"url": source.as_uri(), "sha256": "0" * 64, "path": "data/x/x.dic"}
    with pytest.raises(ValueError, match="контрольная сумма"):
        fa.fetch_file("x.dic", entry, root=tmp_path / "repo")
    assert not (tmp_path / "repo" / "data" / "x" / "x.dic").exists()
