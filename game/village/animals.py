# -*- coding: utf-8 -*-
"""Звери поселения: пиксельные модели и анимации.

Заяц и олень рисуются отдельными спрайтами (не коробками): у оленя на
ходу двигается каждая нога (диагональный аллюр, 4 фазы), заяц скачет
(фазы прыжка: толчок — полёт — приземление). Пиксель арта у зверей и
людей одного размера (масштаб мастера 32 строки = рост человека), поэтому
фигуры выглядят детальнее мира, но стиль единый.
"""

import math

import pygame

from game.core import state as G
from game.core.config import (
    TILE_Z)
from game.render.lighting import (
    shade, tone)
from game.village.core import (
    VIL_HUM_SPR)

AN_SPR = VIL_HUM_SPR  # общий кэш спрайтов фигур (ключи не пересекаются)

# ---------------------------------------------------------------------------
# Палитры
# ---------------------------------------------------------------------------
_RAB_FUR = (168, 148, 122)
_RAB_BACK = (126, 106, 82)
_RAB_BELLY = (214, 202, 184)
_RAB_EAR_IN = (196, 148, 140)
_RAB_EYE = (40, 30, 28)
_RAB_TAIL = (238, 234, 226)
_DEE_COAT = (154, 108, 62)
_DEE_BACK = (116, 78, 42)
_DEE_BELLY = (206, 178, 138)
_DEE_LEG = (104, 70, 38)
_DEE_HOOF = (52, 38, 28)
_DEE_MUZ = (122, 88, 54)
_DEE_NOSE = (44, 32, 26)
_DEE_EYE = (30, 22, 20)
_DEE_ANT = (208, 186, 148)
_DEE_TAIL = (226, 214, 190)


def _mk(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


# ---------------------------------------------------------------------------
# Заяц: мастер 16x10
# ---------------------------------------------------------------------------
def _rabbit_master(pose):
    W, H = 16, 10
    m = _mk(W, H)
    fur, back, belly = _RAB_FUR, _RAB_BACK, _RAB_BELLY

    def px(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            m.set_at((x, y), c)

    def rect(x0, y0, x1, y1, c):
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                px(xx, yy, c)

    if pose == "dead":
        rect(3, 6, 11, 8, fur)
        rect(3, 6, 11, 6, back)
        rect(12, 6, 14, 7, belly)
        px(13, 6, _RAB_EYE)
        rect(1, 7, 2, 8, _RAB_TAIL)
        return m
    if pose == "hop_a":  # полёт: тело вытянуто, ноги растянуты
        # уши заложены назад
        rect(4, 1, 7, 2, fur)
        px(5, 1, _RAB_EAR_IN)
        px(6, 2, _RAB_EAR_IN)
        # голова впереди
        rect(9, 2, 13, 5, fur)
        px(12, 3, _RAB_EYE)
        px(13, 4, _RAB_EAR_IN)
        # тело
        rect(4, 3, 10, 6, fur)
        rect(4, 3, 9, 3, back)
        rect(5, 6, 9, 6, belly)
        px(2, 4, _RAB_TAIL)
        px(2, 5, _RAB_TAIL)
        # задние ноги вытянуты назад
        rect(1, 6, 4, 7, back)
        px(0, 7, back)
        # передние тянутся вперёд
        rect(10, 7, 12, 8, back)
        px(9, 6, back)
        return m
    if pose == "hop_b":  # толчок/приземление: ноги под телом
        rect(5, 0, 6, 3, fur)
        rect(7, 0, 8, 3, fur)
        px(5, 1, _RAB_EAR_IN)
        px(8, 1, _RAB_EAR_IN)
        rect(9, 3, 13, 6, fur)
        px(12, 4, _RAB_EYE)
        px(13, 5, _RAB_EAR_IN)
        rect(4, 4, 10, 7, fur)
        rect(4, 4, 9, 4, back)
        rect(5, 7, 9, 7, belly)
        px(2, 5, _RAB_TAIL)
        px(2, 6, _RAB_TAIL)
        # задние лапы пружиной
        rect(4, 8, 6, 9, back)
        rect(3, 9, 6, 9, back)
        rect(9, 8, 11, 9, back)
        return m
    if pose == "eat":  # голова к земле
        rect(4, 0, 5, 3, fur)
        rect(6, 1, 7, 4, fur)
        px(4, 1, _RAB_EAR_IN)
        px(7, 2, _RAB_EAR_IN)
        rect(3, 4, 10, 7, fur)
        rect(3, 4, 9, 4, back)
        rect(4, 7, 9, 7, belly)
        rect(10, 6, 14, 8, fur)  # шея и голова вниз
        px(13, 7, _RAB_EYE)
        px(14, 8, _RAB_EAR_IN)
        px(1, 5, _RAB_TAIL)
        px(1, 6, _RAB_TAIL)
        rect(4, 8, 6, 9, back)
        rect(8, 8, 10, 9, back)
        return m
    # sit / stand
    rect(5, 0, 6, 3, fur)
    rect(8, 0, 9, 3, fur)
    px(5, 1, _RAB_EAR_IN)
    px(8, 1, _RAB_EAR_IN)
    rect(9, 3, 13, 6, fur)
    px(12, 4, _RAB_EYE)
    px(13, 5, _RAB_EAR_IN)
    px(13, 4, belly)
    rect(4, 4, 10, 7, fur)
    rect(4, 4, 9, 4, back)
    rect(5, 7, 9, 7, belly)
    px(2, 5, _RAB_TAIL)
    px(2, 6, _RAB_TAIL)
    px(3, 6, _RAB_TAIL)
    rect(8, 7, 9, 9, back)   # передние лапки
    rect(4, 8, 7, 9, back)   # задние
    rect(3, 9, 7, 9, back)
    return m


# ---------------------------------------------------------------------------
# Олень: мастер 30x20, ноги анимируются по фазам
# ---------------------------------------------------------------------------
_DEER_LEGS_X = (7, 10, 16, 19)   # FL FR BL BR
_WALK_OFF = (0.0, 0.5, 0.5, 0.0)  # диагональный аллюр


def _deer_master(pose, phase):
    W, H = 30, 24
    m = _mk(W, H)
    coat, back, belly = _DEE_COAT, _DEE_BACK, _DEE_BELLY

    def px(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            m.set_at((x, y), c)

    def rect(x0, y0, x1, y1, c):
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                px(xx, yy, c)

    if pose == "dead":
        rect(4, 14, 20, 18, coat)
        rect(4, 14, 20, 15, back)
        rect(21, 13, 26, 16, coat)
        px(24, 14, _DEE_EYE)
        rect(2, 15, 3, 17, _DEE_TAIL)
        rect(6, 19, 10, 20, _DEE_LEG)
        rect(16, 19, 20, 20, _DEE_LEG)
        return m

    eat = pose == "eat"
    alert = pose == "alert"
    run = pose == "run"
    bob = 1 if pose in ("walk", "run") and phase in (0, 2) else 0
    by = 12 + bob         # верх корпуса
    # корпус
    rect(4, by, 20, by + 6, coat)
    rect(4, by, 19, by, back)             # линия спины
    rect(5, by + 6, 19, by + 6, belly)
    rect(3, by + 1, 4, by + 3, _DEE_TAIL)  # хвост
    px(20, by + 1, back)
    # шея и голова
    if eat:
        rect(19, by - 1, 22, by + 2, coat)
        rect(21, by + 2, 25, by + 5, coat)     # голова опущена
        px(24, by + 3, _DEE_EYE)
        rect(25, by + 4, 27, by + 5, _DEE_MUZ)
        px(27, by + 5, _DEE_NOSE)
        rect(19, by - 3, 21, by - 1, coat)     # уши назад
        px(19, by - 3, back)
    else:
        dy0 = by - 8 - (2 if alert else 0)
        rect(19, dy0 + 4, 22, by + 1, coat)    # шея
        rect(19, dy0 + 4, 20, by + 1, back)
        rect(20, dy0 + 1, 25, dy0 + 5, coat)   # голова
        px(23, dy0 + 2, _DEE_EYE)
        rect(25, dy0 + 2, 27, dy0 + 4, _DEE_MUZ)
        px(27, dy0 + 3, _DEE_NOSE)
        rect(18, dy0, 19, dy0 + 2, coat)       # ухо
        px(18, dy0, back)
        # рога: два ствола с ветвями
        hy = dy0 + 1
        for ax in (21, 24):
            for k in range(4):
                px(ax + k // 2, hy - 1 - k, _DEE_ANT)
            px(ax + 2, hy - 3, _DEE_ANT)
            px(ax + 2, hy - 4, _DEE_ANT)
            px(ax - 1, hy - 2, _DEE_ANT)
    # ноги: каждая со своей фазой диагонального аллюра
    for i, lx in enumerate(_DEER_LEGS_X):
        if pose in ("walk", "run"):
            t = phase / 4.0 + _WALK_OFF[i]
            swing = math.cos(t * 2 * math.pi)
            lift = max(0.0, math.sin(t * 2 * math.pi))
            sw = int(round(swing * (2 if run else 1)))
            lf = int(round(lift * (3 if run else 2)))
        else:
            sw, lf = 0, 0
        y0 = by + 6
        y1 = 22 - lf
        for yy in range(y0, y1 + 1):
            px(lx + sw, yy, _DEE_LEG)
            px(lx + 1 + sw, yy, _DEE_LEG)
        px(lx + sw, min(y1 + 1, H - 1), _DEE_HOOF)
        px(lx + 1 + sw, min(y1 + 1, H - 1), _DEE_HOOF)
        px(lx, y0, coat)      # бедро
        px(lx + 1, y0, coat)
    return m


def _fir_like_key():
    return int(G.DAYT * 8) % 8


def _animal_sprite(an, pose, phase, S):
    kind = an["kind"]
    flip = an.get("flip", False)
    key = ("an", kind, pose, phase, S, flip, _fir_like_key())
    spr = AN_SPR.get(key)
    if spr is not None:
        return spr
    if kind == "rabbit":
        m = _rabbit_master(pose)
        rows = 10
        draw_h = 13   # заяц в холке ~0.4 роста человека + уши
    else:
        m = _deer_master(pose, phase)
        rows = 24
        draw_h = 26   # олень с шеей и ногами читается на любом зуме
    h = max(5, int(round(S * draw_h / 32)))
    w = max(6, int(round(h * m.get_width() / rows)))
    spr = pygame.transform.scale(m, (w, h))
    if flip:
        spr = pygame.transform.flip(spr, True, False)
    if len(AN_SPR) > 8192:
        AN_SPR.clear()
    AN_SPR[key] = spr
    return spr


def animal_pose(an):
    """Поза и фаза из состояния зверя."""
    if an.get("dead"):
        return "dead", 0
    if an["kind"] == "rabbit":
        if an["spd"] < an["base"] * 0.7:
            if an.get("eating", 0) > 0:
                return "eat", 0
            return "sit", 0
        t = an["ph"] % 1.0
        if t < 0.45:
            return "hop_a", 0
        return "hop_b", 0
    spd = an["spd"]
    if spd < an["base"] * 0.7:
        if an.get("eating", 0) > 0:
            return "eat", 0
        return "alert", 0
    phase = int(an["ph"] * 4) % 4
    return ("run" if spd > an["base"] * 1.1 else "walk"), phase


def draw_animal(window, cam, ctx, an):
    ze = ctx[3]
    sx, sy = cam.world_to_screen(an["x"], an["y"], an["z"])
    S = max(8, int(round(TILE_Z * ze * 1.1)))  # масштаб человека
    pose, phase = animal_pose(an)
    spr = _animal_sprite(an, pose, phase, S)
    # контактная тень
    shw = max(3, int(spr.get_width() * 0.7))
    pygame.draw.ellipse(window, tone(shade((96, 128, 74), (0, 0, 1)), 0.62),
                        (int(sx - shw / 2), int(sy - shw // 6),
                         shw, max(2, shw // 4)))
    hop = 0
    if an["kind"] == "rabbit" and pose == "hop_a":
        hop = int(S * 0.10 * math.sin((an["ph"] % 1.0) / 0.45 * math.pi))
    window.blit(spr, (int(sx - spr.get_width() / 2),
                      int(sy - spr.get_height() + 1 - hop)))
