"""Файлы data/ в репозитории совпадают с замком: провенанс словарей проверяется каждым прогоном."""

from sborka import fetch_artifacts as fa


def test_committed_data_files_match_lock():
    lock = fa.load_lock()
    entries = {name: entry for name, entry in lock.items() if "path" in entry}
    assert len(entries) >= 9
    for name, entry in entries.items():
        path = fa.ROOT / entry["path"]
        assert path.is_file(), f"{name}: нет файла {entry['path']} — выполните python sborka/fetch_artifacts.py --files"
        assert fa.sha256_of(path) == entry["sha256"], f"{name}: файл {entry['path']} отличается от замка"
