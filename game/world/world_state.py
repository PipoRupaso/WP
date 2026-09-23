# -*- coding: utf-8 -*-
"""Общие контейнеры мира: эффекты, состояние домов, ветер, версии мира."""

import random
from game.core import state as G

# ---------------------------------------------------------------------------
# Воксельные разрушения (Teardown в 2D) + пиксели + физика
# ---------------------------------------------------------------------------
FLASHES, RINGS, SMOKES, SPARKS, FLAMES, DUST = [], [], [], [], [], []
HOUSE_HIT = {i: False for i in range(1, 41)}  # дом под атакой: дым гаснет
LIGHTS_OFF = set()         # дом разрушен на 30%+ — свет в его окнах гаснет
HOUSE_BURNING = set()      # в доме что-то горит (окна светятся огнём)
HOUSE_TOTAL, HOUSE_DMG = {}, {}   # урон дома в вокселях
LIGHTS_OFF_FRACTION = 0.30
VENTS = {}  # дом -> объект-труба
CHIMNEY_T = {i: 0.0 for i in range(1, 41)}
fx_rng = random.Random(9182)  # свой ГСЧ дымка, боевой rng не трогаем
# --- ветер: направление/сила плывут к целям, цели меняются порывами ---
WIND = dict(ang=0.8, str=0.35, t_ang=0.8, t_str=0.35, next=10.0, t=0.0,
            kick=0.0, wx=1.0, wy=0.6, mag=0.4)
wind_rng = random.Random(20260917)
_PHYS_AUDIT = {"version": -1, "cursor": 0}
_CRATER_TILES = set()  # клетки воронок для инкрементной перекраски
_STATIC_REQ = dict(full=False)  # обрушение требует полный перестрой
_SUP_IDX = {}  # id(списка) -> (WORLD_VERSION, список, grid)
FLYERS = []  # вырванные ёлки в полёте  # индекс опоры


def bump_world():
    G.WORLD_VERSION += 1
    G.STATIC_VER += 1


_TREECNT = {"key": None, "n": 0}


def tree_count(objects):
    """Счётчик ёлок для HUD: пересчёт только при смене состава мира
    (взрыв/стройка/сброс/удаление фигуры меняют len и/или версию)."""
    key = (id(objects), G.WORLD_VERSION, len(objects))
    if _TREECNT["key"] != key:
        _TREECNT["n"] = sum(1 for o in objects if o.get("shape") == "tree")
        _TREECNT["key"] = key
    return _TREECNT["n"]
