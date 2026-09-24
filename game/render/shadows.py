# -*- coding: utf-8 -*-
"""Падающие тени по рельефу, подсветка наведения."""

import math
import pygame
from game.core import state as G
from game.core.config import (
    GRID_D, GRID_W, HIGHLIGHT, TILE_W)
from game.core.utils import (
    convex_hull)
from game.world.terrain import (
    ground_height_at)
from game.render.camera import (
    _proj_ctx, _proj_pt)
from game.world.queries import (
    stack_height_at)
from game.render.objects import (
    _rock_poly)

# ---------------------------------------------------------------------------
# Тени
# ---------------------------------------------------------------------------
def object_corners_world(o):
    if o["shape"] == "cylinder":
        cx, cy = o["x"] + o["w"] / 2, o["y"] + o["d"] / 2
        pts = []
        for i in range(8):
            a = math.pi * 2 * i / 8
            pts.append((cx + (o["w"] / 2) * math.cos(a),
                        cy + (o["d"] / 2) * math.sin(a)))
        return pts
    x, y, w, d = o["x"], o["y"], o["w"], o["d"]
    return [(x, y), (x + w, y), (x + w, y + d), (x, y + d)]


def draw_shadows(layer, cam, objects):
    # Быстрый путь: инлайн-проекция _proj_pt (без вызовов методов камеры)
    ctx = _proj_ctx(cam)
    _w0, _h0 = cam.win_w, cam.win_h
    sdX, sdY = G.SHADOW_DX, G.SHADOW_DY
    rgba = G.SHADOW_RGBA

    def _pt(wx, wy):
        # тень лежит НА рельефе, а не на плоскости z=0
        gz = ground_height_at(wx, wy)
        if gz is None:
            gz = 0.0
        return _proj_pt(ctx, wx, wy, gz)

    for o in objects:
        shape = o.get("shape")
        if shape == "tree":
            _pxc, _pyc = _proj_pt(ctx, o["x"] + 0.5, o["y"] + 0.5, o["z"])
        else:
            _pxc, _pyc = _proj_pt(ctx, o["x"] + o["w"] * 0.5,
                                  o["y"] + o["d"] * 0.5, o["z"])
        if (_pxc < -140 or _pxc > _w0 + 140 or _pyc < -140
                or _pyc > _h0 + 140):
            continue
        pts = []
        if shape == "tree":
            # вытянутая тень: диск у основания + верх кроны вдоль солнца
            cx, cy = o["x"] + 0.5, o["y"] + 0.5
            sz = o.get("sz", 1.0)
            # верх кроны ≈ 1.65*sz (такой же, как высота спрайта ёлки)
            zb, zt = o["z"], o["z"] + (0.25 if o.get("dead") else 1.65 * sz)
            r = 0.30 * sz
            rr = r
            for i in range(6):
                a = math.pi * 2 * i / 6
                wx = cx + math.cos(a) * rr
                wy = cy + math.sin(a) * rr
                pts.append(_pt(wx + sdX * zb, wy + sdY * zb))
            for i in range(6):
                a = math.pi * 2 * i / 6 + 0.5
                wx = cx + math.cos(a) * rr * 0.55
                wy = cy + math.sin(a) * rr * 0.55
                pts.append(_pt(wx + sdX * (zb + zt) * 0.5,
                               wy + sdY * (zb + zt) * 0.5))
            for i in range(4):
                a = math.pi * 2 * i / 4 + 0.4
                wx = cx + math.cos(a) * r * 0.45
                wy = cy + math.sin(a) * r * 0.45
                pts.append(_pt(wx + sdX * zt, wy + sdY * zt))
        elif shape == "rock":
            # тень точно по рваному силуэту (тот же контур, что и в рендере)
            foot, top, tz = _rock_poly(o)
            z = o["z"]
            for wx, wy in foot:
                pts.append(_pt(wx + sdX * z, wy + sdY * z))
            for wx, wy in top:
                pts.append(_pt(wx + sdX * tz, wy + sdY * tz))
        else:
            z0, z1 = o["z"], o["z"] + o["h"]
            for wx, wy in object_corners_world(o):
                pts.append(_pt(wx + sdX * z0, wy + sdY * z0))
                pts.append(_pt(wx + sdX * z1, wy + sdY * z1))
        hull = convex_hull(pts)
        if len(hull) >= 3:
            pygame.draw.polygon(layer, rgba, hull)
            if shape in ("tree", "rock"):
                pygame.draw.polygon(layer, rgba, hull)


def draw_hover(window, cam, objects, mpos, blast_mode, power):
    wx, wy = cam.screen_to_world(mpos[0], mpos[1], 0)
    for _ in range(3):
        _gz = ground_height_at(wx, wy)
        if _gz is None:
            break
        wx, wy = cam.screen_to_world(mpos[0], mpos[1], _gz)
    tx, ty = math.floor(wx), math.floor(wy)
    if not (0 <= tx < GRID_W and 0 <= ty < GRID_D):
        return None
    gz0 = ground_height_at(tx + 0.5, ty + 0.5) or 0.0
    p1 = cam.world_to_screen(tx, ty, gz0)
    p2 = cam.world_to_screen(tx + 1, ty, gz0)
    p3 = cam.world_to_screen(tx + 1, ty + 1, gz0)
    p4 = cam.world_to_screen(tx, ty + 1, gz0)
    col = (255, 120, 90) if blast_mode else HIGHLIGHT
    pygame.draw.polygon(window, col, [p1, p2, p3, p4], 1)
    if not blast_mode:
        z = stack_height_at(objects, tx, ty)
        rx0, ry0, wr, dr = cam.rotated_footprint(tx, ty, 1, 1)
        rx1, ry1 = rx0 + wr, ry0 + dr
        c1 = cam.iso_project(rx0, ry0, z + 1)
        c2 = cam.iso_project(rx1, ry0, z + 1)
        c3 = cam.iso_project(rx1, ry1, z + 1)
        c4 = cam.iso_project(rx0, ry1, z + 1)
        c3b = cam.iso_project(rx1, ry1, z)
        pygame.draw.polygon(window, HIGHLIGHT, [c1, c2, c3, c4], 1)
        pygame.draw.line(window, HIGHLIGHT, c3, c3b, 1)
    else:
        cx = (p1[0] + p3[0]) / 2
        cy = (p1[1] + p3[1]) / 2
        r = (1.5 * power + 0.4) * (TILE_W / 2) * cam.zoom / G.PIXEL
        pygame.draw.ellipse(window, col, (cx - r, cy - r / 2, r * 2, r), 1)
    return (tx, ty)
