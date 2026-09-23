# -*- coding: utf-8 -*-
"""Базовые фигуры: углы коробок, тексели граней."""

import math
import pygame
from game.core import state as G
from game.core.utils import (
    quad_pt)
from game.render.lighting import (
    grain_color, shade)

# ---------------------------------------------------------------------------
# Фигуры (+ зерно нормалей на гранях)
# ---------------------------------------------------------------------------
def box_corner_points(cam, x, y, z, w, d, h):
    rx0, ry0, wr, dr = cam.rotated_footprint(x, y, w, d)
    rx1, ry1 = rx0 + wr, ry0 + dr
    p1 = cam.iso_project(rx0, ry0, z + h)
    p2 = cam.iso_project(rx1, ry0, z + h)
    p3 = cam.iso_project(rx1, ry1, z + h)
    p4 = cam.iso_project(rx0, ry1, z + h)
    p2b = cam.iso_project(rx1, ry0, z)
    p3b = cam.iso_project(rx1, ry1, z)
    p4b = cam.iso_project(rx0, ry1, z)
    return p1, p2, p3, p4, p2b, p3b, p4b


def face_texels(window, cam, quad, face_n, base_raw, seed, preset_idx,
                world_w, world_h):
    """Крупные пиксели-тексели на грани (сетка в мировых единицах)."""
    return  # выкл: вид как издали на любом зуме
    minx = min(p[0] for p in quad)
    maxx = max(p[0] for p in quad)
    miny = min(p[1] for p in quad)
    maxy = max(p[1] for p in quad)
    if not G._SPRITE_MODE and (maxx < 0 or minx > cam.win_w
                             or maxy < 0 or miny > cam.win_h):
        return
    TW = 0.28
    cols = max(1, int(round(world_w / TW)))
    rows = max(1, int(round(world_h / TW)))
    if cols * rows > 120:
        k = math.sqrt(cols * rows / 120)
        cols = max(1, int(cols / k))
        rows = max(1, int(rows / k))
    wpx = math.hypot(quad[1][0] - quad[0][0], quad[1][1] - quad[0][1])
    hpx = math.hypot(quad[3][0] - quad[0][0], quad[3][1] - quad[0][1])
    if wpx / cols < 4 / G.PIXEL or hpx / rows < 4 / G.PIXEL:
        return  # далеко: грань гладкая (быстро)
    for r in range(rows):
        t0, t1 = r / rows, (r + 1) / rows
        for c in range(cols):
            u0, u1 = c / cols, (c + 1) / cols
            col = grain_color(preset_idx, base_raw, face_n,
                              seed + c * 7, r * 13)
            pygame.draw.polygon(window, col,
                                [quad_pt(quad, u0, t0), quad_pt(quad, u1, t0),
                                 quad_pt(quad, u1, t1), quad_pt(quad, u0, t1)])


def draw_flat_side(window, quad, base_raw, face_n, seed, preset_idx, cam,
                   world_w, world_h):
    pygame.draw.polygon(window, shade(base_raw, face_n), quad)
    face_texels(window, cam, quad, face_n, base_raw, seed, preset_idx,
                world_w, world_h)
