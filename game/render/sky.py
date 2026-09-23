# -*- coding: utf-8 -*-
"""Небо, звёзды, солнце/луна, облака, свечение края."""

import math
import pygame
from game.core import state as G
from game.core.config import (
    SP)
from game.core.utils import (
    clamp, hash01)
from game.render.lighting import (
    tone)

# ---------------------------------------------------------------------------
# Небо, звёзды, солнце/луна, облака
# ---------------------------------------------------------------------------
_SKY_CACHE = {"key": None, "surf": None}


def make_sky(w, h):
    """Вертикальный градиент меняется только при переходе цвета на
    следующее целое значение. Между такими изменениями не создаём Surface
    и не рисуем сотни линий каждый кадр.
    """
    top, bot = G.LIGHT["sky"]
    key = (w, h, top, bot)
    if _SKY_CACHE["key"] == key:
        return _SKY_CACHE["surf"]
    sky = pygame.Surface((w, h))
    for yy in range(h):
        f = yy / max(1, h - 1)
        c = tuple(int(top[i] + (bot[i] - top[i]) * f) for i in range(3))
        pygame.draw.line(sky, c, (0, yy), (w, yy))
    _SKY_CACHE["key"], _SKY_CACHE["surf"] = key, sky
    return sky




def _stars_table():
    """Позиции/яркость/размер звёзд детерминированы — считаем один раз."""
    if G._STARS is None:
        G._STARS = [(hash01(i, 7, 1), hash01(i, 13, 2), i * 1.7,
                   hash01(i, 29, 3),
                   2 if hash01(i, 5, 4) > 0.85 else 1) for i in range(170)]
    return G._STARS


def draw_stars(window, w, h, frame):
    fade = G.LIGHT.get("star_a", 1.0)
    if fade <= 0.02:
        return  # звёзды плавно проявляются только к ночи
    for hx, hy, ph, hb, sz in _stars_table():
        x = hx * w
        y = hy * h * 0.7
        tw = 0.55 + 0.45 * math.sin(frame * 0.05 + ph)
        b = int((140 + 110 * tw * hb) * fade)
        if b < 10:
            continue
        pygame.draw.rect(window, (b, b, min(255, b + 20)),
                         (int(x), int(y), sz, sz))


def draw_disc(window, w, h):
    # солнце и луна плавно «сменяют» друг друга (кросс-фейд в сумерках)
    kind, fx, fy, col = G.LIGHT["disc"]
    night_w = G.LIGHT.get("star_a", 0.0)
    sun_w = clamp(1.0 - 2.0 * night_w, 0.0, 1.0)
    moon_w = clamp(2.0 * night_w - 1.0, 0.0, 1.0)
    if sun_w <= 0.02 and moon_w <= 0.02:
        return
    sx, sy = int(w * fx), int(h * fy)
    R = SP(110)
    glow = pygame.Surface((R * 2, R * 2), pygame.SRCALPHA)
    if sun_w > 0.02:
        for rr, aa in ((SP(105), 26), (SP(70), 42), (SP(45), 66)):
            pygame.draw.circle(glow, col + (int(aa * sun_w),), (R, R), rr)
        pygame.draw.circle(glow, col + (int(255 * sun_w),), (R, R), SP(24))
    if moon_w > 0.02:
        mcol = (235, 242, 255)
        for rr, aa in ((SP(105), 18), (SP(70), 30), (SP(45), 50)):
            pygame.draw.circle(glow, mcol + (int(aa * moon_w),), (R, R), rr)
        pygame.draw.circle(glow, mcol + (int(255 * moon_w),), (R, R), SP(20))
        for mx, my, mr in [(-SP(6), -SP(4), SP(5)), (SP(7), SP(5), SP(4)),
                           (-SP(2), SP(9), SP(3))]:
            pygame.draw.circle(glow, (205, 215, 235, int(200 * moon_w)),
                               (R + mx, R + my), mr)
    window.blit(glow, (sx - R, sy - R))
    if sun_w > 0.5:
        pygame.draw.circle(window, tone(col, 0.92), (sx, sy), SP(24), 1)


FAR_CLOUDS = []
NEAR_CLOUDS = []

_EDGE_CACHE = {}
_EDGE_FORM = [(0.07, 0.12, 90), (0.24, 0.05, 120), (0.46, 0.10, 80),
              (0.68, 0.055, 110), (0.88, 0.13, 95), (0.5, 0.34, 70),
              (0.16, 0.31, 62)]


def _glow_surf(r, col):
    s = pygame.Surface((r * 8, r * 8), pygame.SRCALPHA)
    c = r * 4
    for i in range(5):
        rr = max(2, int(r * (0.9 + 0.62 * i)))
        aa = int(200 / (i + 0.85))
        pygame.draw.circle(s, col + (aa,), (c, c), rr)
    return s


def draw_edge_glow(window, w, h, frame):
    """Мягкие анимированные засветы облаков у краёв неба (без облаков-объектов)."""
    key = (w, h, G.LIGHT["cloud_w"], G.LIGHT["cloud_s"])
    slots = _EDGE_CACHE.get(key)
    if slots is None:
        if len(_EDGE_CACHE) > 6:
            _EDGE_CACHE.clear()
        slots = []
        for i, (fx, fy, r) in enumerate(_EDGE_FORM):
            mix = hash01(i, 3, 91)
            # приближаем к чистому свету, чтобы пятно читалось на небе
            col = tuple(min(255, int(G.LIGHT["cloud_w"][c] * 0.72
                                     + 245 * 0.28 + 18 * mix))
                        for c in range(3))
            slots.append((_glow_surf(int(SP(r)), col), fx, fy, r,
                          hash01(i, 7, 92)))
        _EDGE_CACHE[key] = slots
    t = G.ANIM_T
    for spr, fx, fy, r, ph in slots:
        drift = t * (3.0 + r * 0.06) + G.CLOUD_OFF * (0.10 + ph * 0.25)
        span = w + r * 8
        px = (fx * span + drift * (1 if ph > 0.4 else -1)) % span - r * 4
        py = fy * h + math.sin(t * 0.30 + ph * 9.0) * r * 0.12
        spr.set_alpha(int(250 * (0.78 + 0.22 * math.sin(t * 0.42 + ph * 7.1))))
        window.blit(spr, (int(px - r * 4), int(py - r * 4)))
