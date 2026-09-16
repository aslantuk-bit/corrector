"""Собирает папку поставки из результата PyInstaller и JRE, кладёт инструкцию и упаковывает в zip."""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import corrector  # noqa: E402 — версии приложений
import launchcheck  # noqa: E402

APPS = {
    "launchcheck": {
        "folder": "Проверка_запуска",
        "zip": "proverka-zapuska",
        "version": launchcheck.__version__,
        "instruction": ROOT / "sborka" / "ИНСТРУКЦИЯ-проверка-запуска.txt",
        "extras": [],
    },
    "corrector": {
        "folder": "Корректор",
        "zip": "korrektor",
        "version": corrector.__version__,
        "instruction": ROOT / "data" / "ИНСТРУКЦИЯ.txt",
        # (что копировать, куда внутри папки поставки); languagetool берётся из vendor/languagetool-ru
        "extras": [
            (ROOT / "data", "data"),
            (ROOT / "vendor" / "languagetool-ru", "languagetool"),
            # настройки сервера внутри папки languagetool: Java не читает файлы по пути с символами вне кодовой страницы
            (ROOT / "data" / "lt" / "lt.properties", "languagetool/lt.properties"),
            (ROOT / "sborka" / "правила.yaml", "правила.yaml"),
            (ROOT / "sborka" / "ЛИЦЕНЗИИ", "ЛИЦЕНЗИИ"),
        ],
    },
}
EXCLUDE_DATA = shutil.ignore_patterns("review", "*.part", ".DS_Store")


def assemble(
    app_name: str,
    version: str,
    dist: Path = ROOT / "dist",
    vendor: Path = ROOT / "vendor",
    jre: str = "jre-windows-x64",
    instruction: Path | None = None,
    zip_name: str | None = None,
    extras: list[tuple[Path, str]] = (),
) -> Path:
    source = dist / app_name
    if not source.is_dir():
        raise FileNotFoundError(f"нет папки {source}: сначала соберите программу PyInstaller")
    jre_dir = vendor / jre
    if not jre_dir.is_dir():
        raise FileNotFoundError(f"нет папки {jre_dir}: сначала выполните python sborka/fetch_artifacts.py {jre}")

    bundle_root = dist / "bundle"
    bundle = bundle_root / app_name
    if bundle.exists():
        shutil.rmtree(bundle)
    shutil.copytree(source, bundle)
    shutil.copytree(jre_dir, bundle / "java", ignore=shutil.ignore_patterns(".artifact-sha256"))
    if instruction is not None:
        shutil.copy(instruction, bundle / "ИНСТРУКЦИЯ.txt")
    for source_path, relative in extras:
        target = bundle / relative
        if not source_path.exists():
            raise FileNotFoundError(f"нет {source_path}: подготовьте его перед сборкой")
        if source_path.is_dir():
            shutil.copytree(source_path, target, ignore=EXCLUDE_DATA)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source_path, target)

    zip_path = bundle_root / (zip_name or f"{app_name}-{version}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(bundle.rglob("*")):
            if file.is_file():
                archive.write(file, file.relative_to(bundle_root).as_posix())
    return zip_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Собрать папку поставки и архив")
    parser.add_argument("app", choices=sorted(APPS))
    parser.add_argument("--jre", default="jre-windows-x64", help="имя JRE из artifacts.lock")
    args = parser.parse_args(argv)
    app = APPS[args.app]
    suffix = "win64" if args.jre.startswith("jre-windows") else "mac"
    zip_path = assemble(
        app["folder"],
        app["version"],
        jre=args.jre,
        instruction=app["instruction"],
        zip_name=f"{app['zip']}-{app['version']}-{suffix}.zip",
        extras=app.get("extras", []),
    )
    print(zip_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
