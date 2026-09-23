# -*- coding: utf-8 -*-
"""Точка входа: python main.py [--test | --bench | --sim N | --closeup]

Код игры разложен по пакету game/ (см. README.md, раздел «Структура»).
"""
import sys

from game.app import main

if __name__ == "__main__":
    sys.exit(main())
