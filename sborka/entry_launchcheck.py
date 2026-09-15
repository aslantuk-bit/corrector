"""Точка входа для PyInstaller: абсолютный импорт, чтобы пакет собирался целиком."""

import sys

from launchcheck.app import main

sys.exit(main())
