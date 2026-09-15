"""Собирает папку поставки из результата PyInstaller и JRE, кладёт инструкцию и упаковывает в zip."""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import launchcheck  # noqa: E402 — версия приложения

APPS = {
    "launchcheck": {
        "folder": "Проверка_запуска",
        "zip": "proverka-zapuska",
        "version": launchcheck.__version__,
        "instruction": ROOT / "sborka" / "ИНСТРУКЦИЯ-проверка-запуска.txt",
    },
}


def assemble(
    app_name: str,
    version: str,
    dist: Path = ROOT / "dist",
    vendor: Path = ROOT / "vendor",
    jre: str = "jre-windows-x64",
    instruction: Path | None = None,
    zip_name: str | None = None,
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
    )
    print(zip_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
