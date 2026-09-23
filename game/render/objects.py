# -*- coding: utf-8 -*-
"""Дерево/камни/эрозия: отрисовка объектов."""

import math
import pygame
from game.core.config import (
    BASE_COLORS, LEFT_N, MAT_GRAIN, PLANK_MATS, PZ, RIGHT_N, SP, STONE_MATS,
    WOOD_MATS, _BASE_ORDER)
from game.core.utils import (
    hash01, quad_pt)
from game.render.lighting import (
    shade, tone)
from game.render.normalmaps import (
    nshade)
from game.render.primitives import (
    box_corner_points)
from game.render.materials import (
    _rot_normal, draw_chip_notches)

OBJ_SPRITES = {}      # id(o) -> готовый спрайт объекта
# Бюджет пере-рендера спрайтов за кадр: смена запечённого света (течение
# суток) не вызывает единый тяжёлый кадр — устаревшие спрайты обновляются
# по чуть-чуть в течение ~полсекунды (старый и новый свет незаметно смешиваются).
_SPRITE_BUDGET = [48]


def _wood_cell_color(base, n, seed, inner, mat="wood_dark"):
    v = 0.90 + 0.20 * hash01(seed, 5, 6)
    if inner:
        v *= 0.78
        v *= 0.94 + 0.12 * hash01(seed, 12, 13)
    return tone(nshade(base, mat, seed, 9, n, 0.7), v)


def _wood_cell_detail(window, q, n, seed, inner, mat, z0, z1, o):
    gr = MAT_GRAIN.get(mat)
    end = gr is not None and (n == gr or (n[0] == -gr[0]
                                        and n[1] == -gr[1]
                                        and n[2] == -gr[2]))
    base = BASE_COLORS[o["color"]]
    lit = shade(base, n)
    if end:
        for k in range(3):
            u = 0.2 + 0.6 * hash01(seed, k, 21)
            t = 0.2 + 0.6 * hash01(seed, k, 22)
            x, y = quad_pt(q, u, t)
            pygame.draw.rect(window, tone(lit, 0.62),
                             (int(x), int(y), 1, 1))
    else:
        t = 0.25 + 0.5 * hash01(seed, 3, 23)
        wob = (hash01(seed, 4, 24) - 0.5) * 0.1
        if mat in PLANK_MATS:
            a, b = quad_pt(q, 0.06, t), quad_pt(q, 0.94, t + wob)
        else:
            a, b = quad_pt(q, t, 0.06), quad_pt(q, t + wob, 0.94)
        pygame.draw.line(window, tone(lit, 0.70), a, b, 1)
    if inner:
        for k in range(2):
            t = 0.2 + 0.6 * hash01(seed, k, 25)
            wob = (hash01(seed, k, 26) - 0.5) * 0.2
            pygame.draw.line(window, tone(lit, 1.25),
                             quad_pt(q, 0.1, t), quad_pt(q, 0.9, t + wob), 1)
    if mat in PLANK_MATS and n[2] == 0:
        for k in (1, 2, 3):
            zb = o["z"] + o["h"] * k / 4
            if z0 < zb < z1:
                t = (z1 - zb) / (z1 - z0)
                pygame.draw.line(window, tone(lit, 0.40),
                                 quad_pt(q, 0, t), quad_pt(q, 1, t), 1)


def _wood_face_finish(window, q, base, n, gr, mat, o):
    lit = shade(base, n)
    end = gr is not None and (n == gr or (n[0] == -gr[0]
                                        and n[1] == -gr[1]
                                        and n[2] == -gr[2]))
    if mat in PLANK_MATS and n[2] == 0:
        for b in range(4):
            t0, t1 = b / 4, (b + 1) / 4
            bq = [quad_pt(q, 0, t0), quad_pt(q, 1, t0),
                  quad_pt(q, 1, t1), quad_pt(q, 0, t1)]
            pygame.draw.polygon(window, tone(lit, 0.93 + 0.07 * (b % 2)), bq)
            mid = (t0 + t1) / 2
            wob = (hash01(b, 3, 77) - 0.5) * 0.05
            pygame.draw.line(window, tone(lit, 0.72),
                             quad_pt(q, 0.02, mid),
                             quad_pt(q, 0.98, mid + wob), 1)
        for k in (1, 2, 3):
            t = k / 4
            pygame.draw.line(window, tone(lit, 0.42),
                             quad_pt(q, 0, t), quad_pt(q, 1, t), 1)
        return
    if end:
        cx, cy = quad_pt(q, 0.5, 0.5)
        r = max(2.0, math.hypot(q[1][0] - q[0][0],
                                q[1][1] - q[0][1]) * 0.16)
        prev = None
        for a in range(11):
            ang = a / 10 * math.pi * 2
            pt = (cx + math.cos(ang) * r, cy + math.sin(ang) * r * 0.5)
            if prev is not None:
                pygame.draw.line(window, tone(lit, 0.65), prev, pt, 1)
            prev = pt
        for k in range(8):
            u = 0.15 + 0.7 * hash01(k, 5, 81)
            t = 0.15 + 0.7 * hash01(k, 6, 82)
            x, y = quad_pt(q, u, t)
            pygame.draw.rect(window, tone(lit, 0.60),
                             (int(x), int(y), 1, 1))
        return
    for i in range(7):
        t = (i + 0.5) / 7
        wob = (hash01(i, 9, 83) - 0.5) * 0.06
        tonev = 0.70 + 0.15 * hash01(i, 10, 84)
        pygame.draw.line(window, tone(lit, tonev),
                         quad_pt(q, t, 0.03), quad_pt(q, t + wob, 0.97), 1)
    kx, ky = quad_pt(q, 0.3 + 0.4 * hash01(3, 1, 85),
                     0.3 + 0.4 * hash01(3, 2, 86))
    pygame.draw.rect(window, tone(lit, 0.50),
                     (int(kx), int(ky), 2, 2))


def _draw_wood_dressing(window, cam, o, base):
    mat = o.get("mat", "concrete")
    gr = MAT_GRAIN.get(mat)
    p1, p2, p3, p4, p2b, p3b, p4b = box_corner_points(cam, o["x"], o["y"],
                                                     o["z"], o["w"], o["d"], o["h"])
    faces = [(RIGHT_N[cam.rot], [p2, p3, p3b, p2b]),
             (LEFT_N[cam.rot], [p4, p3, p3b, p4b]),
             (PZ, [p1, p2, p3, p4])]
    for n, q in faces:
        _wood_face_finish(window, q, base, n, gr, mat, o)


def _obj_idx(o):
    """Стабильный сид объекта (такой же, как в _render_object_sprite)."""
    try:
        _ci = _BASE_ORDER.index(o["color"])
    except ValueError:
        _ci = 0
    return int(o["x"] * 12.7 + o["y"] * 57.3 + o["z"] * 101.1 + o["w"] * 3.1
              + o["d"] * 7.7 + o["h"] * 13.9 + _ci * 37.3) % 100000


def _rock_poly(o):
    """Рваные контуры валуна (низ и верх) — одна формула для рендера
    и для тени, чтобы тень всегда совпадала с силуэтом."""
    x, y, z, w, d, h = o["x"], o["y"], o["z"], o["w"], o["d"], o["h"]
    cx = x + w / 2
    cy = y + d / 2
    idx = _obj_idx(o)
    nv = 5 + idx % 3
    foot = []
    for i in range(nv):
        a = math.pi * 2 * i / nv + (hash01(i, idx, 31) - 0.5) * 0.9
        rx = (w / 2) * (0.72 + 0.28 * hash01(i, idx, 32))
        ry = (d / 2) * (0.72 + 0.28 * hash01(i, idx, 33))
        foot.append((cx + math.cos(a) * rx, cy + math.sin(a) * ry))
    tx = cx + (hash01(idx, 1, 33) - 0.5) * w * 0.25
    ty = cy + (hash01(idx, 2, 33) - 0.5) * d * 0.25
    tz = z + h * (0.85 + 0.3 * hash01(idx, 3, 33))
    top = [(tx + (fx - cx) * 0.45, ty + (fy - cy) * 0.45)
           for fx, fy in foot]
    return foot, top, tz


def draw_rock(window, cam, o, base, idx):
    """Валун: рваный многогранник с вкраплениями; форма — из сида idx."""
    x, y, z, w, d, h = o["x"], o["y"], o["z"], o["w"], o["d"], o["h"]
    foot, top, tz = _rock_poly(o)
    nv = len(foot)
    pf = [cam.world_to_screen(fx, fy, z) for fx, fy in foot]
    pt = [cam.world_to_screen(txx, tyy, tz) for txx, tyy in top]
    for i in range(nv):
        i2 = (i + 1) % nv
        a = math.pi * 2 * (i + 0.5) / nv
        wx, wy = _rot_normal(math.cos(a), math.sin(a), cam.rot)
        lit = shade(base, (wx, wy, 0.15))
        quad = [pf[i], pf[i2], pt[i2], pt[i]]
        pygame.draw.polygon(window, lit, quad)
        if hash01(i, idx, 34) < 0.7:
            mx = int((quad[0][0] + quad[2][0]) / 2)
            my = int((quad[0][1] + quad[2][1]) / 2)
            pygame.draw.rect(window, tone(lit, 0.8 + 0.4 * hash01(i, idx, 35)),
                             (mx - SP(1), my - SP(1), SP(2), SP(2)))
    pygame.draw.polygon(window, shade(base, PZ), pt)
    draw_chip_notches(window, cam, o)


def _draw_eroded_box(window, cam, o, base, preset_idx):
    """Блок с дырой в месте удара: целые воксели, полые — выбиты."""
    g = o["_chipgrid"]
    chips = o.get("chips", ())
    idx = g["idx"]
    VR, VL = RIGHT_N[cam.rot], LEFT_N[cam.rot]
    stone = o["color"] in STONE_MATS
    vis = (PZ, VR, VL)
    mat = o.get("mat", "concrete")
    _gb = o.get("shape") == "gable"
    _gbp = BASE_COLORS["gray"] if o.get("ends") == "stone" else BASE_COLORS[
        "plaster"]
    _gbe = o.get("ends") == "stone"
    nx = g["nx"]

    def proj(x, y, z):
        xr, yr = cam.rotate_point(x, y)
        return cam.iso_project(xr, yr, z)

    def solid(key):
        return key in idx and key not in chips

    cells = []
    for c in g["cells"]:
        key = (c[0], c[1], c[2])
        if key in chips:
            continue
        xr, yr = cam.rotate_point(c[3], c[4])
        cells.append((xr + yr, -c[5], c))
    cells.sort(key=lambda t: (t[0], t[1]))
    for _, _, c in cells:
        ix, iy, iz, cx, cy, cz, cw, cd, ch = c
        x0, x1 = cx - cw / 2, cx + cw / 2
        y0, y1 = cy - cd / 2, cy + cd / 2
        z0, z1 = cz - ch / 2, cz + ch / 2
        faces = [
            (PZ, (ix, iy, iz + 1),
             [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]),
            ((1, 0, 0), (ix + 1, iy, iz),
             [(x1, y0, z1), (x1, y1, z1), (x1, y1, z0), (x1, y0, z0)]),
            ((-1, 0, 0), (ix - 1, iy, iz),
             [(x0, y1, z1), (x0, y0, z1), (x0, y0, z0), (x0, y1, z0)]),
            ((0, 1, 0), (ix, iy + 1, iz),
             [(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)]),
            ((0, -1, 0), (ix, iy - 1, iz),
             [(x1, y0, z1), (x0, y0, z1), (x0, y0, z0), (x1, y0, z0)]),
        ]
        for n, nb, corners in faces:
            if n not in vis:
                continue
            if solid(nb):
                continue
            q = [proj(*pt) for pt in corners]
            inner = nb in chips
            seed = ix * 131 + iy * 17 + iz * 13 + n[0] * 3 + n[1] * 5
            _end = _gb and (ix == 0 or ix == nx - 1)
            bbase = _gbp if _end else base
            if stone or (_end and _gbe):
                if hash01(seed, 6, 7) < 0.30:
                    col = tone(shade(bbase, n), 0.52)
                else:
                    v = 0.90 + 0.18 * hash01(seed, 7, 8)
                    if inner:
                        v *= 0.48
                    col = tone(nshade(bbase, mat, seed, 3, n, 0.7), v)
            elif mat in WOOD_MATS:
                col = _wood_cell_color(bbase, n, seed, inner, mat)
                if mat in PLANK_MATS:
                    band = int((cz - o["z"]) / o["h"] * 4)
                    col = tone(col, 0.94 + 0.06 * (band % 2))
            else:
                v = 0.88 + 0.24 * hash01(seed, 5, 6)
                if inner:
                    v *= 0.48
                col = tone(nshade(bbase, mat, seed, 3, n, 0.7), v)
            pygame.draw.polygon(window, col, q)
            if mat in WOOD_MATS:
                _wood_cell_detail(window, q, n, seed, inner, mat,
                                  z0, z1, o)
