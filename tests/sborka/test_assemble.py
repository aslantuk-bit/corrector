import zipfile
from pathlib import Path

import pytest

from sborka import assemble as asm


def make_tree(root: Path, files: dict[str, bytes]) -> None:
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def test_assemble_builds_folder_and_zip(tmp_path):
    dist, vendor = tmp_path / "dist", tmp_path / "vendor"
    make_tree(dist / "Проверка_запуска", {"Проверка_запуска.exe": b"exe", "_internal/base.dll": b"dll"})
    make_tree(vendor / "jre-windows-x64", {"bin/java.exe": b"java", ".artifact-sha256": b"abc"})
    instruction = tmp_path / "инструкция.txt"
    instruction.write_text("Откройте программу", encoding="utf-8")

    zip_path = asm.assemble("Проверка_запуска", "0.1.0", dist=dist, vendor=vendor,
                            instruction=instruction, zip_name="proverka-zapuska-0.1.0-win64.zip")

    bundle = dist / "bundle" / "Проверка_запуска"
    assert (bundle / "Проверка_запуска.exe").read_bytes() == b"exe"
    assert (bundle / "_internal" / "base.dll").exists()
    assert (bundle / "java" / "bin" / "java.exe").read_bytes() == b"java"
    assert not (bundle / "java" / ".artifact-sha256").exists()
    assert (bundle / "ИНСТРУКЦИЯ.txt").read_text(encoding="utf-8") == "Откройте программу"
    assert zip_path == dist / "bundle" / "proverka-zapuska-0.1.0-win64.zip"
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
    assert {"Проверка_запуска/Проверка_запуска.exe", "Проверка_запуска/java/bin/java.exe",
            "Проверка_запуска/ИНСТРУКЦИЯ.txt", "Проверка_запуска/_internal/base.dll"} <= names


def test_assemble_requires_built_app(tmp_path):
    with pytest.raises(FileNotFoundError, match="сначала соберите"):
        asm.assemble("Проверка_запуска", "0.1.0", dist=tmp_path / "dist", vendor=tmp_path / "vendor")


def test_assemble_requires_jre(tmp_path):
    dist = tmp_path / "dist"
    make_tree(dist / "Проверка_запуска", {"Проверка_запуска.exe": b"exe"})
    with pytest.raises(FileNotFoundError, match="fetch_artifacts"):
        asm.assemble("Проверка_запуска", "0.1.0", dist=dist, vendor=tmp_path / "vendor")


def test_apps_registry_has_launchcheck():
    app = asm.APPS["launchcheck"]
    assert app["folder"] == "Проверка_запуска"
    assert app["zip"] == "proverka-zapuska"
    assert app["instruction"].exists()


def test_assemble_copies_extras(tmp_path):
    dist, vendor = tmp_path / "dist", tmp_path / "vendor"
    make_tree(dist / "Корректор", {"Корректор.exe": b"exe", "Корректор-cli.exe": b"cli"})
    make_tree(vendor / "jre-windows-x64", {"bin/java.exe": b"java"})
    make_tree(tmp_path / "data", {"ru/ru_RU.dic": b"d", "review/x.tsv": b"skip"})
    make_tree(tmp_path / "lt", {"languagetool-server.jar": b"jar"})
    zip_path = asm.assemble("Корректор", "0.3.0", dist=dist, vendor=vendor, zip_name="korrektor-0.3.0-win64.zip",
                            extras=[(tmp_path / "data", "data"), (tmp_path / "lt", "languagetool")])
    bundle = dist / "bundle" / "Корректор"
    assert (bundle / "data" / "ru" / "ru_RU.dic").exists() and not (bundle / "data" / "review").exists()
    assert (bundle / "languagetool" / "languagetool-server.jar").exists()
    with zipfile.ZipFile(zip_path) as z:
        assert "Корректор/languagetool/languagetool-server.jar" in z.namelist()


def test_apps_registry_has_corrector():
    app = asm.APPS["corrector"]
    assert app["folder"] == "Корректор" and app["zip"] == "korrektor" and app["instruction"].exists()
