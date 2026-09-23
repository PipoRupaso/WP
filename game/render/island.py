# -*- coding: utf-8 -*-
"""Остров: боковые стенки, камешки, крапинки."""

import math
import pygame
from game.core import state as G
from game.core.config import (
    DIRT_DEEP, GRASS, GRID_D, GRID_W, ISLAND_T, LEFT_N, RIGHT_N, ROCK_DEEP,
    SP)
from game.core.utils import (
    hash01, lerp_pt, quad_pt)
from game.render.lighting import (
    shade, tilt_normal, tone)

# ---------------------------------------------------------------------------
# Остров
# ---------------------------------------------------------------------------
def speckle(window, cam, x, y, color):
    ix, iy = int(x), int(y)
    if G._SPRITE_MODE:
        ww, hh = window.get_size()
        if 0 <= ix < ww and 0 <= iy < hh:
            window.set_at((ix, iy), color)
    elif 0 <= ix < cam.win_w and 0 <= iy < cam.win_h:
        window.set_at((ix, iy), color)


def draw_pebble(window, cam, x, y, base):
    light = tone(base, 1.45)
    dark = tone(base, 0.62)
    mid = tone(base, 1.05)
    ix, iy = int(x), int(y)
    n = SP(2)
    for ox in range(n):
        for oy in range(n):
            s = (ox - 0.5) * G.SUN_SX + (oy - 0.5) * G.SUN_SY
            c = light if s > 0.15 else (dark if s < -0.15 else mid)
            speckle(window, cam, ix + ox, iy + oy, c)


def draw_island_sides(window, cam):
    W, D = GRID_W, GRID_D
    sides = [
        dict(a=(W, 0), b=(W, D), n=RIGHT_N[cam.rot], seed=11, wl=D),
        dict(a=(0, D), b=(W, D), n=LEFT_N[cam.rot], seed=77, wl=W),
    ]
    zf = min(cam.zoom, 1.6)
    for side in sides:
        n = side["n"]
        A = cam.iso_project(*side["a"], 0)
        B = cam.iso_project(*side["b"], 0)
        A2 = cam.iso_project(*side["a"], -ISLAND_T)
        B2 = cam.iso_project(*side["b"], -ISLAND_T)
        quad = [A, B, B2, A2]

        dirt = shade(DIRT_DEEP, n)
        rock = shade(ROCK_DEEP, n)

        bands = [(0.00, 0.30, tone(dirt, 1.04)),
                 (0.30, 0.58, tone(dirt, 0.96)),
                 (0.58, 0.80, tone(dirt, 1.00)),
                 (0.80, 1.00, rock)]
        for t0, t1, col in bands:
            pygame.draw.polygon(window, col,
                                [quad_pt(quad, 0, t0), quad_pt(quad, 1, t0),
                                 quad_pt(quad, 1, t1), quad_pt(quad, 0, t1)])

        edge_len = math.hypot(B[0] - A[0], B[1] - A[1])
        for t_edge in (0.30, 0.58, 0.80):
            steps = max(8, int(edge_len / (9 / G.PIXEL)))
            for i in range(steps + 1 if cam.zoom >= 99 else 0):
                u = i / steps
                wob = math.sin(u * 22 + side["seed"]) * SP(2) * zf
                px, py = quad_pt(quad, u, t_edge)
                speckle(window, cam, px, py + wob, tone(dirt, 0.72))

        nx = max(10, int(side["wl"] / 0.55))
        ny = max(4, int(ISLAND_T / 0.55))
        for gy in range(ny + 1 if cam.zoom >= 99 else 0):
            for gx in range(nx + 1):
                u, t = gx / nx, gy / ny
                px, py = quad_pt(quad, u, t)
                r = hash01(gx + side["seed"] * 131, gy, 7)
                raw = ROCK_DEEP if t > 0.80 else DIRT_DEEP
                stone_p = 0.16 if t > 0.80 else 0.06
                if r < stone_p:
                    draw_pebble(window, cam, px, py, shade(raw, n))
                else:
                    nn = tilt_normal(n, gx + side["seed"], gy, 21, 0.6)
                    f = 0.72 if r < 0.55 else 1.18
                    speckle(window, cam, px, py, tone(shade(raw, nn), f))

        lip = shade(GRASS, n)
        teeth = max(16, int(side["wl"] / 0.5))
        for i in range(teeth):
            t0 = i / teeth
            left = lerp_pt(A, B, t0)
            right = lerp_pt(A, B, min(1.0, t0 + 0.9 / teeth))
            mid = ((left[0] + right[0]) / 2, (left[1] + right[1]) / 2)
            depth = SP(4 + 7 * hash01(i, side["seed"], 3)) * zf
            pygame.draw.polygon(window, lip, [left, right, (mid[0], mid[1] + depth)])

        bottom_n = max(8, int(side["wl"] / 1.5))
        for i in range(bottom_n):
            t0 = (i + 0.5) / bottom_n
            c = lerp_pt(A2, B2, t0)
            hw = edge_len / bottom_n * 0.28
            depth = SP(8 + 14 * hash01(i, side["seed"], 5)) * zf
            pygame.draw.polygon(window, tone(rock, 0.8),
                                [(c[0] - hw, c[1]), (c[0] + hw, c[1]),
                                 (c[0], c[1] + depth)])
