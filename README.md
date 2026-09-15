# Корректор

Проверка орфографии, пунктуации и стиля юридических текстов на русском и казахском.
Работает с флешки на Windows без установки и без интернета. Спецификация:
`docs/superpowers/specs/2026-09-15-corrector-design.md`.

## Этап 0: «Проверка запуска»

Пробная программа `Проверка_запуска.exe` с приложенной Java. Показывает, запускается ли
переносная сборка на рабочем ПК, и пишет `отчёт_запуска.txt`.

## Окружение на Mac

    tools/dev_setup.sh
    .venv/bin/python -m pytest -q

## Сборка

Собирает GitHub Actions (`.github/workflows/windows.yml`) при каждом пуше в `main`:
архив `proverka-zapuska-<версия>-win64.zip` лежит в артефактах запуска, а при тэге `v*` —
в релизе. Локально на Mac: `pyinstaller --noconfirm sborka/launchcheck.spec` и
`python sborka/assemble.py launchcheck` (получится сборка для Mac, для проверки скриптов).
