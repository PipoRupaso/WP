# -*- coding: utf-8 -*-
"""Библиотека зданий по эпохам, каталог классов/вместимости, установка в мир."""

import math
import pygame
from game.core import state as G
from game.world.world_state import (
    VENTS, bump_world)
from game.world.terrain import (
    ground_height_at)
from game.world.scene import (
    make_test_scene)

# ---------------------------------------------------------------------------
# Библиотека зданий по эпохам + установка в мир (панель по Y)
# ---------------------------------------------------------------------------
EPOCH_NAMES = ["Каменный век", "Раннее дерево", "Рубленые избы",
               "Средневековье", "Саман", "Замки", "Бетон и стекло", "Сегодня"]
CLASS_NAMES = [
    ["Навес с кострищем", "Шалаш из шкур", "Палатка из жердей",
     "Двускатный шалаш", "Мастерская на жердях", "Шалаш-вышка",
     "База охотников", "Охотничья будка", "Склад камней", "Склад брёвен",
     "Шалаш-двойной"],
    ["Круглая хижина", "Длинный дом", "Хижина на сваях", "Хижина вождя",
     "Хижина-галерея"],
    ["Рубленая изба", "Изба с крыльцом", "Изба с дровенником",
     "Изба L-образная", "Изба с частоколом"],
    ["Коттедж C1", "Двухэтажный C2", "Изба-терем C3", "Терем C4",
     "Большой терем C5", "Фахверк-лавка", "Таверна"],
    ["Саман-куб", "Саман 2-ярусный", "Саман L-дом", "Купол-улей",
     "Пуэбло 3-ярусный", "Саман с аркой", "Общинный длинный",
     "Саман с лестницей", "Башенка-саман", "Храм-ступени"],
    ["Донжон с аркой", "Замок-двор", "Часовня", "Королевский донжон",
     "Сторожевая башня", "Воротная башня", "Замок-усадьба", "Бастион"],
    ["Куб-студия", "Двухэтажный с балконом", "L-дом модерн",
     "Дуплекс нижний", "Дуплекс студия", "Дом с эркером", "Лофт 3эт.",
     "Дом с гаражом", "Вилла с террасой", "Офисный куб", "Пентхаус-вилла"],
    ["Коттедж витражный", "Коттедж витражный-2", "Таунхаус 3эт.",
     "Таунхаус 4эт.", "Панелька 5эт.", "Панелька 9эт.", "Кирпичный дом",
     "Магазин-витрина", "Особняк с колоннами", "Дом с мансардой",
     "Свечка-новостройка", "Панелька с балконами", "Дуплекс-таун",
     "Дачный домик", "Особняк с гаражом"],
]
# класс жильцов по замыслу (0 = худший, 4 = лучший); порядок в палитре
HOUSE_ORDER = {
    8: 5, 9: 1, 10: 0, 11: 2, 12: 6, 67: 3, 68: 4,
    69: 7, 70: 8, 71: 9, 72: 10,                          # каменный век
    13: 0, 14: 2, 15: 1, 16: 3, 17: 4,                     # раннее дерево
    18: 0, 19: 1, 20: 2, 21: 3, 22: 4,                     # рубленые избы
    1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6,              # средневековье
    28: 0, 27: 1, 29: 2, 23: 3, 26: 4, 24: 5, 25: 6, 30: 7,  # замки
    42: 0, 44: 1, 45: 2, 43: 3, 46: 4, 47: 5, 50: 6,
    49: 7, 51: 8, 41: 9, 48: 10,                            # бетон и стекло
    66: 0, 63: 1, 56: 2, 57: 3, 62: 4,
    52: 5, 53: 6, 54: 7, 55: 8, 58: 9, 59: 10, 60: 11,
    61: 12, 64: 13, 65: 14,                                 # сегодня
}
# вместимость (чел.) у жилых классов
HOUSE_CAP = {
    10: 1, 9: 2, 11: 2, 67: 4, 68: 5, 72: 3,
    13: 1, 15: 2, 14: 3, 16: 4, 17: 5,
    18: 1, 19: 2, 20: 3, 21: 4, 22: 5,
    1: 1, 2: 3, 3: 4, 4: 5, 5: 6,
    28: 2, 27: 3, 29: 4, 23: 5, 26: 6,
    42: 2, 44: 2, 45: 2, 43: 3, 46: 3, 47: 3, 50: 5,
    49: 6, 51: 8,
    66: 3, 63: 4, 56: 6, 57: 8, 62: 10,
}
NEXT_HOUSE = [41]  # пул id для устанавливаемых домов


_EPOCH_RANGES = [(1, 7, 3), (8, 12, 0), (13, 17, 1), (18, 22, 2),
                 (23, 30, 5), (31, 40, 4), (41, 51, 6), (52, 66, 7),
                 (67, 72, 0)]
_EPOCH_START = {3: 1, 0: 8, 1: 13, 2: 18, 4: 23, 5: 31, 6: 41, 7: 52}


def _epoch_of_id(h):
    for a_, b_, e_ in _EPOCH_RANGES:
        if a_ <= h <= b_:
            return e_
    return 7


def make_building_library():
    """40 шаблонов: epoch, cls, name, anchor, pieces (относительные коорд.)."""
    if G.LIB_TPL is not None:
        return G.LIB_TPL
    objs = make_test_scene(keep_buildings=True)
    by_house = {}
    for o in objs:
        if o.get("house"):
            by_house.setdefault(o["house"], []).append(o)
    lib = []
    for hid in sorted(by_house):
        ep = _epoch_of_id(hid)
        if ep == 4:  # эпоха самана удалена из каталога
            continue
        pieces = by_house[hid]
        ox = min(p["x"] for p in pieces)
        oy = min(p["y"] for p in pieces)
        oz = min(p["z"] for p in pieces)
        cls = HOUSE_ORDER.get(hid, 90 + hid)
        rel = []
        for p in pieces:
            q = {k: v for k, v in p.items()
                 if k not in ("house", "_chipgrid", "sup", "supt", "park_v",
                              "tmb", "fx_t", "sp_t", "ig", "burn", "dust_t",
                              "chips", "over")}
            q = dict(q)
            q["x"] = round(p["x"] - ox, 4)
            q["y"] = round(p["y"] - oy, 4)
            q["z"] = round(p["z"] - oz, 4)
            q["vx"] = q["vy"] = q["vz"] = 0.0
            rel.append(q)
        if hid in (67, 68):  # дома ур.4/5: моделька чуть больше
            _SC = 1.18
            for q in rel:
                for _kk in ("x", "y", "w", "d"):
                    q[_kk] = round(q[_kk] * _SC, 4)
                for _kk in ("z", "h"):
                    q[_kk] = round(q[_kk] * 1.08, 4)
        _idx = hid - _EPOCH_START[ep]
        nm = (CLASS_NAMES[ep][_idx]
              if _idx < len(CLASS_NAMES[ep]) else "Дом %d" % (hid))
        _cap = HOUSE_CAP.get(hid)
        if _cap:
            nm = "%s \u00b7 %d чел." % (nm, _cap)
        lib.append(dict(epoch=ep, cls=cls, hid=hid, name=nm,
                        anchor=(ox, oy), z0=oz, _raw=(ox, oy, oz),
                        pieces=rel, cap=_cap or 0))
    G.LIB_TPL = lib
    return lib


def _tpl_layout(tpl, rot):
    """Раскладка кусков шаблона с поворотом rot (90гр шаги), по якорю-мину."""
    raw = []
    for p in tpl["pieces"]:
        x, y, w, d = p["x"], p["y"], p["w"], p["d"]
        pts = [(x, y), (x + w, y), (x + w, y + d), (x, y + d)]
        for _ in range(rot % 4):
            pts = [(b_, -a_) for (a_, b_) in pts]
        xa = min(c[0] for c in pts)
        ya = min(c[1] for c in pts)
        xb = max(c[0] for c in pts)
        yb = max(c[1] for c in pts)
        raw.append([xa, ya, xb - xa, yb - ya, p])
    bx0 = min(r[0] for r in raw)
    by0 = min(r[1] for r in raw)
    return [(r[0] - bx0, r[1] - by0, r[2], r[3], r[4]) for r in raw]


def _tpl_ground_z(layout):
    """Якорь детали к рельефу: минимум по углам объединённого прямоугольника."""
    ux1 = max(r[0] + r[2] for r in layout)
    uy1 = max(r[1] + r[3] for r in layout)
    best = 1e9
    for ux in (0.0, ux1):
        for uy in (0.0, uy1):
            g = ground_height_at(ux, uy)
            if g is not None and g < best:
                best = g
    if best > 1e8:
        best = 0.0
    return math.floor(best / 0.05) * 0.05 - 0.045


def place_building(objects, tpl, X, Y, rot=0):
    """Установить дом из шаблона в точку X,Y (метка = левый нижний угол)."""
    layout = _tpl_layout(tpl, rot)
    if not layout:
        return None
    zb = _tpl_ground_z(layout)
    hid = NEXT_HOUSE[0]
    NEXT_HOUSE[0] += 1
    for xa, ya, w, d, p in layout:
        q = dict(p)
        q["x"], q["y"] = xa + X, ya + Y
        q["w"], q["d"] = w, d
        q["z"] = p["z"] + zb
        q["house"] = hid
        if rot % 4 and q.get("detail") and q["detail"].get("n"):
            nx, ny, _nz = q["detail"]["n"]
            for _ in range(rot % 4):
                nx, ny = ny, -nx
            q["detail"] = dict(q["detail"])
            q["detail"]["n"] = (nx, ny, 0)
        if q.get("vent"):
            q["vent"] = hid
            VENTS[hid] = q
        objects.append(q)
    bump_world()
    return hid


def draw_ghost(window, cam, tpl, rot, wx, wy):
    """Зелёный 3D-контур макета, ползущий за мышью."""
    layout = _tpl_layout(tpl, rot)
    if not layout:
        return
    # сдвинуть так, чтобы прицел был центром объединённого прямоугольника
    ux0 = min(r[0] for r in layout)
    uy0 = min(r[1] for r in layout)
    ux1 = max(r[0] + r[2] for r in layout)
    uy1 = max(r[1] + r[3] for r in layout)
    cx, cy = (ux0 + ux1) / 2, (uy0 + uy1) / 2
    values = []
    for ux in (ux0, ux1, cx):
        for uy in (uy0, uy1, cy):
            g = ground_height_at(wx + ux - cx, wy + uy - cy)
            if g is not None:
                values.append(g)
    zb = (math.floor(min(values) / 0.05) * 0.05 - 0.045) if values else 0.0
    surf = pygame.Surface((cam.win_w, cam.win_h), pygame.SRCALPHA)
    lim = [(0, 0), (ux1, 0), (ux1, uy1), (0, uy1)]
    q = [cam.world_to_screen(wx + a - cx, wy + b - cy, zb) for a, b in lim]
    pygame.draw.polygon(surf, (110, 255, 140, 46), q)
    pygame.draw.polygon(surf, (110, 255, 140, 190), q, 1)
    for xa, ya, w, d, p in layout:
        X, Y = wx + xa - cx, wy + ya - cy
        z, h = p["z"] + zb, p["h"]
        pts = [(X, Y), (X + w, Y), (X + w, Y + d), (X, Y + d)]
        top = [cam.world_to_screen(a, b, z + h) for a, b in pts]
        bot = [cam.world_to_screen(a, b, z) for a, b in pts]
        pygame.draw.polygon(surf, (110, 255, 140, 42), top)
        for j in range(4):
            j2 = (j + 1) % 4
            pygame.draw.line(surf, (130, 255, 150, 120), top[j], top[j2], 1)
            pygame.draw.line(surf, (130, 255, 150, 90), bot[j], top[j], 1)
    window.blit(surf, (0, 0))
