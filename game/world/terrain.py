# -*- coding: utf-8 -*-
"""Поле высот острова, воронки."""

import math
from game.core import state as G
from game.core.config import (
    GRID_D, GRID_W)
from game.core.utils import (
    clamp, hash01)

# ---------------------------------------------------------------------------
# Поле высот
# ---------------------------------------------------------------------------
_FARMAP = dict(key=None, colors=None, X=None, Y=None, H=None, buf=None,
               dkey=None, painted=set(), rpainted=set())


def _vnoise(x, y, seed):
    xi, yi = math.floor(x), math.floor(y)
    xf, yf = x - xi, y - yi
    u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)
    a = hash01(xi, yi, seed)
    b = hash01(xi + 1, yi, seed)
    c = hash01(xi, yi + 1, seed)
    d = hash01(xi + 1, yi + 1, seed)
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v




def _base_h():
    """Природный рельеф: холмы вдали, ровно у построек и дороги."""
    if G.BASE_H is None:
        H = [[0.0] * (GRID_W + 1) for _ in range(GRID_D + 1)]
        for y in range(GRID_D + 1):
            Hy = H[y]
            for x in range(GRID_W + 1):
                n = (_vnoise(x * 0.045, y * 0.045, 101) * 0.65
                     + _vnoise(x * 0.11, y * 0.11, 202) * 0.35)
                h = (n - 0.42) * 3.4
                fx = clamp((x - 44) / 10.0, 0.0, 1.0)
                fy = clamp((y - 44) / 10.0, 0.0, 1.0)
                f = max(fx, fy)
                f = f * f * (3 - 2 * f)
                e = min(x, y, GRID_W - x, GRID_D - y, 6) / 6.0
                Hy[x] = clamp(round(h * f * e / 0.15) * 0.15, -1.0, 2.2)
        G.BASE_H = H
    return G.BASE_H


def _base_plate_h(x, y, fx, fy):
    B = _base_h()
    gx, gy = x + fx, y + fy
    x0 = int(min(gx, GRID_W - 1e-6))
    y0 = int(min(gy, GRID_D - 1e-6))
    u, v = gx - x0, gy - y0
    return (B[y0][x0] * (1 - u) * (1 - v) + B[y0][x0 + 1] * u * (1 - v)
            + B[y0 + 1][x0] * (1 - u) * v + B[y0 + 1][x0 + 1] * u * v)


def reset_ground():
    _base_h()
    G.GH = [row[:] for row in G.BASE_H]
    G.DENTED = set()
    G._RIMTILES = set()
    _FARMAP["dkey"] = None


def ground_height_at(x, y):
    if not (0 <= x <= GRID_W and 0 <= y <= GRID_D):
        return None
    x0, y0 = int(min(x, GRID_W - 1e-6)), int(min(y, GRID_D - 1e-6))
    fx, fy = x - x0, y - y0
    return (G.GH[y0][x0] * (1 - fx) * (1 - fy) + G.GH[y0][x0 + 1] * fx * (1 - fy)
            + G.GH[y0 + 1][x0] * (1 - fx) * fy + G.GH[y0 + 1][x0 + 1] * fx * fy)


def height_normal_at(x, y):
    h00, h10 = G.GH[y][x], G.GH[y][x + 1]
    h01, h11 = G.GH[y + 1][x], G.GH[y + 1][x + 1]
    dhdx = ((h10 + h11) - (h00 + h01)) * 0.5
    dhdy = ((h01 + h11) - (h00 + h10)) * 0.5
    il = 1.0 / math.sqrt(dhdx * dhdx + dhdy * dhdy + 1.0)
    return (-dhdx * il, -dhdy * il, il)


def recompute_dented():
    G.DENTED = set()
    for y in range(GRID_D):
        for x in range(GRID_W):
            hs = (G.GH[y][x], G.GH[y][x + 1], G.GH[y + 1][x], G.GH[y + 1][x + 1])
            if max(abs(v) for v in hs) > 0.015:
                G.DENTED.add((x, y))
