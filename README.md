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

## Где взять архив

GitHub → репозиторий `aslantuk-bit/corrector` → «Releases» → `proverka-zapuska-<версия>-win64.zip`.
Между релизами свежий архив лежит в артефактах последнего запуска на вкладке «Actions».
Лист приёмки на рабочем ПК: `docs/acceptance-stage0.md`.

## Командная строка (этапы 1–2)

    .venv/bin/python -m corrector --check акт.docx --report          # с LanguageTool из vendor/
    .venv/bin/python -m corrector --check папка --report --out отчёты
    .venv/bin/python -m corrector --check акт.docx --json --no-lt    # только словари

Отчёт `<имя>_отчёт.txt` кладётся рядом с файлом или в `--out`. Словарь исключений `словарь.txt`
и `настройки.json` читаются из папки программы (или из папки пользователя, если она защищена от записи).

## Правила и файлы для коллег (этапы 3–4)

- Каталог правил с примерами: `docs/rules-ru.md` (русский и общие), `docs/rules-kk.md` (казахский). Таблицы читаются тестами:
  правило без таблицы не считается готовым.
- Свои правила: файл `правила.yaml` рядом с программой (образец в `sborka/правила.yaml`): `найти → заменить → сообщение`.
- Словарь исключений: `словарь.txt` рядом с программой, по слову или фразе на строку.
- Шум правил по выборке корпуса: `docs/corpus-report.md` (`tools/corpus_sample.py`, `tools/corpus_run.py`);
  лексиконы и имена из корпуса: `tools/build_lexicon.py --lang ru|kk` (только Mac, нужен `~/court-analytics/corpus.db`).
- Отключённые правила LanguageTool с обоснованием: `data/lt/lt_disabled_rules.txt`.
