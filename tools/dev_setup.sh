#!/bin/zsh
# Окружение разработчика на Mac: venv на Python 3.13 через uv, зависимости, JRE для тестов.
set -euo pipefail
cd "$(dirname "$0")/.."
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python sborka/fetch_artifacts.py jre-mac-aarch64
.venv/bin/python sborka/fetch_artifacts.py --files
.venv/bin/python sborka/fetch_artifacts.py languagetool-20260914
.venv/bin/python sborka/trim_languagetool.py vendor/languagetool-20260914 vendor/languagetool-ru
echo "Готово. Тесты: .venv/bin/python -m pytest -q"
