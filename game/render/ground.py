# -*- coding: utf-8 -*-
"""Земля: тайлы, детали, воронки, дальний LOD."""

import math
import numpy as np
import pygame
from game.core import state as G
from game.core.config import (
    DIRT_COLOR, DIRT_DEEP, GRASS, GRASS_DARK, GRASS_LIGHT, GRID_D, GRID_W,
    PZ, SP, STONE_GRAY, TILE_H, TILE_W, TILE_Z)
from game.core.utils import (
    clamp, hash01)
from game.render.lighting import (
    shade, tilt_normal, tone)
from game.render.normalmaps import (
    ground_sprite)
from game.world.terrain import (
    _FARMAP, _base_plate_h, ground_height_at, height_normal_at)
from game.render.island import (
    draw_pebble, speckle)

# ---------------------------------------------------------------------------
# Земля
# ---------------------------------------------------------------------------
FLOWER_COLORS = [(240, 240, 245), (240, 200, 120), (235, 150, 180)]
CHECKER_CACHE = {}


def checker_sprite(sw, sh):
    key = (sw, sh)
    s = CHECKER_CACHE.get(key)
    if s is None:
        if len(CHECKER_CACHE) > 30:
            CHECKER_CACHE.clear()
        s = pygame.Surface((sw, sh), pygame.SRCALPHA)
        w2, h2 = sw / 2, sh / 2
        pygame.draw.polygon(s, (10, 20, 10, 26),
                            [(w2, 1), (sw - 1, h2), (w2, sh - 1), (1, h2)])
        CHECKER_CACHE[key] = s
    return s


def draw_tile_details(window, cam, x, y, pts, is_dirt):
    cx = (pts[0][0] + pts[2][0]) / 2
    cy = (pts[0][1] + pts[2][1]) / 2

    def inside(k, spread=0.7):
        corner = pts[k % 4]
        f = 0.12 + spread * hash01(x, y, k)
        return (cx + (corner[0] - cx) * f, cy + (corner[1] - cy) * f)

    if is_dirt:
        dt = shade(DIRT_COLOR, PZ)
        for k in range(6):
            px, py = inside(k)
            r = hash01(x, y, k + 50)
            if r < 0.18:
                draw_pebble(window, cam, px, py, dt)
            elif r < 0.6:
                speckle(window, cam, px, py, tone(dt, 0.7))
    else:
        g_dark = shade(GRASS_DARK, PZ)
        g_light = shade(GRASS_LIGHT, PZ)
        for k in range(6):
            px, py = inside(k + 100, 0.7)
            lean = (hash01(x, y, k + 120) - 0.5) * 2
            hgt = SP(2 + int(hash01(x, y, k + 130) * 2))
            x0, y0 = int(px), int(py)
            if 0 <= x0 < cam.win_w and 1 <= y0 < cam.win_h:
                pygame.draw.line(window, g_dark, (x0, y0),
                                 (int(x0 + lean), y0 - hgt), 1)
                speckle(window, cam, x0 + lean, y0 - hgt, g_light)
        if hash01(x, y, 200) < 0.05:
            px, py = inside(7, 0.5)
            fx, fy = int(px), int(py)
            pygame.draw.line(window, g_dark, (fx, fy), (fx, fy - SP(3)), 1)
            pet = FLOWER_COLORS[int(hash01(x, y, 201) * 3) % 3]
            n = SP(2)
            for ox in range(n):
                for oy in range(n):
                    speckle(window, cam, fx + ox - 1, fy - 5 + oy, pet)
        if hash01(x, y, 210) < 0.07:
            px, py = inside(9, 0.6)
            draw_pebble(window, cam, px, py, shade(STONE_GRAY, PZ))


def _plate_h(x, y, fx, fy):
    h = ground_height_at(x + fx, y + fy)
    if h is None:
        return 0.0
    return round(h / 0.15) * 0.15  # ступени: воронка полностью пиксельная


def draw_dent_overlay(window, cam, x, y):
    SUB = 4
    n = height_normal_at(x, y)
    for sy in range(SUB):
        for sx in range(SUB):
            fx0, fy0 = sx / SUB, sy / SUB
            h = _plate_h(x, y, fx0 + 0.5 / SUB, fy0 + 0.5 / SUB)
            bh = _base_plate_h(x, y, fx0 + 0.5 / SUB, fy0 + 0.5 / SUB)
            depth = clamp((bh - h) / 0.30, 0.0, 1.0)
            patch = 0.85 + 0.30 * hash01(x * 4 + sx, y * 4 + sy, 77)
            g = tone(shade(GRASS, n), patch)
            dd = tuple(int(DIRT_COLOR[i] + (DIRT_DEEP[i] - DIRT_COLOR[i]) * depth ** 0.7) for i in range(3))
            e = tone(shade(dd, n), patch)
            base = tuple(int(g[i] + (e[i] - g[i]) * depth) for i in range(3))
            sc = clamp((depth - 0.55) / 0.45, 0.0, 1.0)
            base = tone(base, 1.0 - 0.45 * sc)  # пригар в центре
            c = [cam.world_to_screen(x + fx0, y + fy0, h),
                 cam.world_to_screen(x + fx0 + 1 / SUB, y + fy0, h),
                 cam.world_to_screen(x + fx0 + 1 / SUB, y + fy0 + 1 / SUB, h),
                 cam.world_to_screen(x + fx0, y + fy0 + 1 / SUB, h)]
            pygame.draw.polygon(window, base, c)
            # рваная крошка земли на пластине
            cx = sum(p[0] for p in c) / 4
            cy = sum(p[1] for p in c) / 4
            for k in range(3):
                corner = c[k % 4]
                f = 0.15 + 0.6 * hash01(x * 4 + sx, y * 4 + sy, k)
                px = cx + (corner[0] - cx) * f
                py = cy + (corner[1] - cy) * f
                r = hash01(x + sx, y + sy, k + 300)
                if r < 0.40:
                    draw_pebble(window, cam, px, py, shade(DIRT_DEEP, n))
                else:
                    nn = tilt_normal(n, x * 4 + sx, y * 4 + sy, k, 0.7)
                    speckle(window, cam, px, py,
                            tone(shade(DIRT_DEEP, nn), 0.75 if r < 0.6 else 1.2))


def _draw_rim_overlay(window, cam, x, y):
    """Вал выброса: приподнятые пластины + светлая крошка."""
    SUB = 4
    n = height_normal_at(x, y)
    for sy in range(SUB):
        for sx in range(SUB):
            fx0, fy0 = sx / SUB, sy / SUB
            h = _plate_h(x, y, fx0 + 0.5 / SUB, fy0 + 0.5 / SUB)
            patch = 0.90 + 0.25 * hash01(x * 4 + sx, y * 4 + sy, 78)
            g = tone(shade(GRASS, n), patch)
            e = tone(shade(DIRT_COLOR, n), patch * 1.05)
            col = tuple(int(g[i] + (e[i] - g[i]) * 0.45) for i in range(3))
            c = [cam.world_to_screen(x + fx0, y + fy0, h),
                 cam.world_to_screen(x + fx0 + 1 / SUB, y + fy0, h),
                 cam.world_to_screen(x + fx0 + 1 / SUB, y + fy0 + 1 / SUB, h),
                 cam.world_to_screen(x + fx0, y + fy0 + 1 / SUB, h)]
            pygame.draw.polygon(window, col, c)
            cx = sum(p[0] for p in c) / 4
            cy = sum(p[1] for p in c) / 4
            for k in range(2):
                corner = c[(k * 2 + 1) % 4]
                f = 0.2 + 0.55 * hash01(x * 4 + sx, y * 4 + sy, k + 50)
                px = cx + (corner[0] - cx) * f
                py = cy + (corner[1] - cy) * f
                nn = tilt_normal(n, x * 4 + sx, y * 4 + sy, k + 9, 0.7)
                speckle(window, cam, px, py,
                        tone(shade(DIRT_COLOR, nn), 1.15))


def _tile_order_key(x, y, rot):
    if rot == 0:
        return x + y
    if rot == 1:
        return x - y
    if rot == 2:
        return -(x + y)
    return y - x


def _ordered_tiles(x0, x1, y0, y1, rot):
    """Клетки bbox сразу в порядке живописи (диагонали, без сортировки)."""
    if rot == 0:
        for s in range(x0 + y0, x1 + y1 + 1):
            for x in range(max(x0, s - y1), min(x1, s - y0) + 1):
                yield (x, s - x)
    elif rot == 1:
        for dd in range(x0 - y1, x1 - y0 + 1):
            for x in range(max(x0, y0 + dd), min(x1, y1 + dd) + 1):
                yield (x, x - dd)
    elif rot == 2:
        for s in range(x1 + y1, x0 + y0 - 1, -1):
            for x in range(max(x0, s - y1), min(x1, s - y0) + 1):
                yield (x, s - x)
    else:
        for dd in range(y0 - x1, y1 - x0 + 1):
            for x in range(max(x0, y0 - dd), min(x1, y1 - dd) + 1):
                yield (x, x + dd)


def _visible_tile_range(cam, rect=None):
    """Какие клетки в кадре (инверсия аффинной решётки)."""
    if rect is None:
        corners = ((0, 0), (cam.win_w, 0), (0, cam.win_h),
                   (cam.win_w, cam.win_h))
    else:
        corners = ((rect[0], rect[1]), (rect[0] + rect[2], rect[1]),
                   (rect[0], rect[1] + rect[3]),
                   (rect[0] + rect[2], rect[1] + rect[3]))
    ox, oy = cam.world_to_screen(0, 0, 0)
    ax, ay = cam.world_to_screen(1, 0, 0)
    bx, by = cam.world_to_screen(0, 1, 0)
    dxx, dxy = ax - ox, ay - oy
    dyx, dyy = bx - ox, by - oy
    det = dxx * dyy - dyx * dxy
    if abs(det) < 1e-9:
        return 0, GRID_W - 1, 0, GRID_D - 1
    xs, ys = [], []
    for qx, qy in corners:
        rx, ry = qx - ox, qy - oy
        xs.append((rx * dyy - ry * dyx) / det)
        ys.append((ry * dxx - rx * dxy) / det)
    return (max(0, int(min(xs)) - 8), min(GRID_W - 1, int(max(xs)) + 8),
            max(0, int(min(ys)) - 8), min(GRID_D - 1, int(max(ys)) + 8))


def _farmap_build(preset_idx):
    N = GRID_W * GRID_D
    X = np.empty(N, np.float32)
    Y = np.empty(N, np.float32)
    H = np.empty(N, np.float32)
    k = 0
    for y in range(GRID_D):
        r0, r1 = G.BASE_H[y], G.BASE_H[y + 1]
        for x in range(GRID_W):
            X[k] = x + 0.5
            Y[k] = y + 0.5
            H[k] = (r0[x] + r0[x + 1] + r1[x] + r1[x + 1]) * 0.25
            k += 1
    Hg = H.reshape(GRID_D, GRID_W)
    gx = np.zeros_like(Hg)
    gy = np.zeros_like(Hg)
    gx[:, 1:-1] = (Hg[:, 2:] - Hg[:, :-2]) * 0.5
    gy[1:-1, :] = (Hg[2:, :] - Hg[:-2, :]) * 0.5
    il = 1.0 / np.sqrt(gx * gx + gy * gy + 1.0)
    dot = (-gx * il) * G.SUN[0] + (-gy * il) * G.SUN[1] + il * G.SUN[2]
    hlev = np.clip(np.round((dot - 0.88) * 9 + 2), 0, 4)
    tint = (0.78 + 0.11 * hlev).reshape(N)
    grass = np.array(tone(shade(GRASS, PZ), 1.0), np.float32)
    dirt = np.array(tone(shade(DIRT_COLOR, PZ), 1.0), np.float32)
    colors = np.empty((N, 3), np.uint8)
    colors[:] = np.clip(grass * tint[:, None], 0, 255)
    _FARMAP["X"], _FARMAP["Y"], _FARMAP["H"] = X, Y, H
    _FARMAP["colors"], _FARMAP["key"] = colors, preset_idx
    _FARMAP["painted"] = set()
    _FARMAP["rpainted"] = set()
    _FARMAP["dkey"] = None


def _draw_ground_far(window, cam, preset_idx):
    """Фар-план: все клетки — векторными точками 2x2 (точно по проекции)."""
    if _FARMAP["key"] != preset_idx or _FARMAP["colors"] is None:
        _farmap_build(preset_idx)
    dkey = (len(G.DENTED), len(G._RIMTILES))
    if _FARMAP["dkey"] != dkey:
        colors = _FARMAP["colors"]
        dd = tuple(int(v) for v in tone(shade(DIRT_DEEP, PZ), 0.62))
        de = tuple(int(v) for v in tone(shade(DIRT_COLOR, PZ), 1.08))
        for x, y in G.DENTED:
            if (x, y) not in _FARMAP["painted"]:
                colors[y * GRID_W + x] = dd
                _FARMAP["painted"].add((x, y))
        for x, y in G._RIMTILES:
            if (x, y) not in _FARMAP["rpainted"]:
                if (x, y) not in G.DENTED:
                    colors[y * GRID_W + x] = de
                _FARMAP["rpainted"].add((x, y))
        _FARMAP["dkey"] = dkey
    X, Y, H = _FARMAP["X"], _FARMAP["Y"], _FARMAP["H"]
    colors = _FARMAP["colors"]
    ox, oy = cam.world_to_screen(0, 0, 0)
    ax, ay = cam.world_to_screen(1, 0, 0)
    bx, by = cam.world_to_screen(0, 1, 0)
    dxx, dxy = ax - ox, ay - oy
    dyx, dyy = bx - ox, by - oy
    ze = cam.zoom / G.PIXEL
    w, h = cam.win_w, cam.win_h
    px = (ox + X * dxx + Y * dyx).astype(np.int32)
    py = (oy + X * dxy + Y * dyy - H * TILE_Z * ze).astype(np.int32)
    if cam.rot == 0:
        kk = X + Y
    elif cam.rot == 1:
        kk = X - Y
    elif cam.rot == 2:
        kk = -(X + Y)
    else:
        kk = Y - X
    order = np.argsort(kk, kind="stable")
    # фон = небо пресета (градиент + звёзды), не чёрный
    top, bot = G.LIGHT["sky"]
    _t = np.linspace(0.0, 1.0, max(1, h), dtype=np.float32)[:, None, None]
    img = (np.array(top, np.float32)[None, None, :] * (1.0 - _t)
           + np.array(bot, np.float32)[None, None, :] * _t)
    img = np.repeat(img, max(1, w), axis=1).astype(np.uint8)
    if G.LIGHT["stars"]:
        for _i in range(150):
            _sx = int(hash01(_i, 7, 1) * max(1, w - 1))
            _sy = int(hash01(_i, 13, 2) * h * 0.60)
            _b = int(150 + 100 * hash01(_i, 29, 3))
            img[_sy, _sx] = (_b, _b, min(255, _b + 20))
    # блоб клетки масштабируется под питч: сплошной ковёр без полос
    _blob = max(2, min(12, int(max(abs(dxx), abs(dyx), abs(dxy),
                                   abs(dyy)) * 1.9) + 1))
    ok = (px >= 0) & (px < w - _blob) & (py >= 0) & (py < h - _blob)
    idx = order[ok[order]]
    _py, _px = py[idx], px[idx]
    _col = colors[idx]
    for _a in range(_blob):
        for _b in range(_blob):
            img[_py + _a, _px + _b] = _col
    buf = img.tobytes()
    window.blit(pygame.image.frombuffer(buf, (w, h), "RGB"), (0, 0))
    _FARMAP["buf"] = buf



def _paint_ground_base(window, cam):
    c0 = cam.world_to_screen(0, 0, 0)
    c1 = cam.world_to_screen(GRID_W, 0, 0)
    c2 = cam.world_to_screen(GRID_W, GRID_D, 0)
    c3 = cam.world_to_screen(0, GRID_D, 0)
    pygame.draw.polygon(window, tone(shade(GRASS, PZ), 0.92),
                        [c0, c1, c2, c3])


def draw_ground(window, cam, show_checker, preset_idx, only=None):
    # вдали: растровый фар-план вместо тысяч спрайтов
    if cam.zoom < 0.35 and not show_checker:
        _draw_ground_far(window, cam, preset_idx)
        return
    # only: инкремент — красить только эти клетки (порядок тот же)
    # аффинная решётка: 3 проекции на кадр вместо тысяч вызовов
    ox, oy = cam.world_to_screen(0, 0, 0)
    ax, ay = cam.world_to_screen(1, 0, 0)
    bx, by = cam.world_to_screen(0, 1, 0)
    dxx, dxy = ax - ox, ay - oy
    dyx, dyy = bx - ox, by - oy
    ze = cam.zoom / G.PIXEL
    ov = 2 + int(cam.zoom * 3)  # нахлёст прячет уступы холмов
    sw = max(2, int(round(TILE_W * cam.zoom / G.PIXEL))) + ov
    sh = max(1, int(round(TILE_H * cam.zoom / G.PIXEL))) + ov
    chk = checker_sprite(sw, sh) if show_checker else None
    if only is not None:
        tiles = sorted(only, key=lambda t: (_tile_order_key(t[0], t[1],
                                                            cam.rot),
                                            t[0], t[1]))
    else:
        x0, x1, y0, y1 = _visible_tile_range(cam)
        tiles = _ordered_tiles(x0, x1, y0, y1, cam.rot)
    sun0, sun1, sun2 = G.SUN
    for x, y in tiles:
        px = ox + x * dxx + y * dyx
        py = oy + x * dxy + y * dyy
        gh00, gh10 = G.GH[y][x], G.GH[y][x + 1]
        gh01, gh11 = G.GH[y + 1][x], G.GH[y + 1][x + 1]
        havg = (gh00 + gh10 + gh01 + gh11) * 0.25
        if havg:
            py -= havg * TILE_Z * ze
        cx = px + (dxx + dyx) * 0.5
        cy = py + (dxy + dyy) * 0.5
        if cx < -sw or cx > cam.win_w + sw or cy < -sh or cy > cam.win_h + sh:
            continue
        dhdx = (gh10 + gh11 - gh00 - gh01) * 0.5
        dhdy = (gh01 + gh11 - gh00 - gh10) * 0.5
        if dhdx or dhdy:
            il = 1.0 / math.sqrt(dhdx * dhdx + dhdy * dhdy + 1.0)
            dot = (-dhdx * il) * sun0 + (-dhdy * il) * sun1 + il * sun2
            hlev = clamp(int(round((dot - 0.88) * 9 + 2)), 0, 4)
        else:
            hlev = 2
        is_dirt = False
        spr = ground_sprite("grass", int(hash01(x, y, 5) * 4) % 4,
                            sw, sh, preset_idx, cam.rot, hlev)
        _sx, _sy = math.floor(cx - sw / 2), math.floor(cy - sh / 2)
        window.blit(spr, (_sx, _sy))
        if chk is not None and (x + y) % 2 == 0:
            window.blit(chk, (_sx, _sy))
        if cam.zoom >= 99:
            draw_tile_details(window, cam, x, y, pts, is_dirt)
        if (x, y) in G.DENTED:
            draw_dent_overlay(window, cam, x, y)
        elif (x, y) in G._RIMTILES:
            _draw_rim_overlay(window, cam, x, y)
