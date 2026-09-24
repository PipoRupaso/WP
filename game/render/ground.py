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
    _FARMAP, _vnoise, ground_height_at, height_normal_at)
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


def _draw_crater_field(window, cam, x, y):
    """Воронка и вал выброса: цвет — непрерывное поле по всему острову.

    Геометрия ступенчатая (пиксельный стиль), а тон земли интерполирован
    между углами клетки и продолжен за её пределы тем же полем, поэтому
    соседние клетки продолжают друг друга без швов и «плитки».
    """
    SUB = 4
    n = height_normal_at(x, y)
    gx0, gy0 = x * SUB, y * SUB
    # непрерывный шум пятна и крошки (общий для всех клеток)
    patch = 0.86 + 0.26 * _vnoise((x + 0.5) * 1.9, (y + 0.5) * 1.9, 77)
    grass = shade(GRASS, n)
    dirt = shade(DIRT_COLOR, n)
    deep = shade(DIRT_DEEP, n)

    def _dig_at(wx, wy):
        ix = int(wx)
        iy = int(wy)
        if not (0 <= ix < GRID_W and 0 <= iy < GRID_D):
            return 0.0, 0.0
        fx = wx - ix
        fy = wy - iy
        h = (G.GH[iy][ix] * (1 - fx) * (1 - fy)
             + G.GH[iy][ix + 1] * fx * (1 - fy)
             + G.GH[iy + 1][ix] * (1 - fx) * fy
             + G.GH[iy + 1][ix + 1] * fx * fy)
        b = (G.BASE_H[iy][ix] * (1 - fx) * (1 - fy)
             + G.BASE_H[iy][ix + 1] * fx * (1 - fy)
             + G.BASE_H[iy + 1][ix] * (1 - fx) * fy
             + G.BASE_H[iy + 1][ix + 1] * fx * fy)
        return max(0.0, b - h), max(0.0, h - b)

    for sy in range(SUB):
        for sx in range(SUB):
            fx0, fy0 = sx / SUB, sy / SUB
            h = _plate_h(x, y, fx0 + 0.5 / SUB, fy0 + 0.5 / SUB)
            # тон: билинейно поDig в углах субклетки — поле непрерывно
            d00, r00 = _dig_at(x + fx0, y + fy0)
            d10, r10 = _dig_at(x + fx0 + 1 / SUB, y + fy0)
            d01, r01 = _dig_at(x + fx0, y + fy0 + 1 / SUB)
            d11, r11 = _dig_at(x + fx0 + 1 / SUB, y + fy0 + 1 / SUB)
            d = (d00 + d10 + d01 + d11) * 0.25
            r = (r00 + r10 + r01 + r11) * 0.25
            depth = clamp(d / 0.12, 0.0, 1.0)
            rimk = clamp(r / 0.06, 0.0, 1.0) * 0.55
            dd = tuple(int(dirt[i] + (deep[i] - dirt[i]) * depth ** 0.7)
                       for i in range(3))
            sc = clamp((depth - 0.55) / 0.45, 0.0, 1.0)
            base = tuple(int(grass[i] + (dd[i] - grass[i]) * depth)
                         for i in range(3))
            base = tone(base, 1.0 - 0.45 * sc)          # пригар в центре
            base = tuple(int(base[i] + (dirt[i] * 1.05 - base[i]) * rimk)
                         for i in range(3))
            base = tone(base, patch)
            c = [cam.world_to_screen(x + fx0, y + fy0, h),
                 cam.world_to_screen(x + fx0 + 1 / SUB, y + fy0, h),
                 cam.world_to_screen(x + fx0 + 1 / SUB, y + fy0 + 1 / SUB, h),
                 cam.world_to_screen(x + fx0, y + fy0 + 1 / SUB, h)]
            pygame.draw.polygon(window, base, c)
            # рваная крошка: сид непрерывен в мировых координатах
            cx = sum(p[0] for p in c) / 4
            cy = sum(p[1] for p in c) / 4
            wx0, wy0 = x + fx0 + 0.5 / SUB, y + fy0 + 0.5 / SUB
            for k in range(2):
                corner = c[k % 4]
                f = 0.15 + 0.6 * _vnoise(wx0 * 4, wy0 * 4, k)
                px = cx + (corner[0] - cx) * f
                py = cy + (corner[1] - cy) * f
                rv = _vnoise(wx0 * 4, wy0 * 4, k + 300)
                if depth > 0.25 or rimk > 0.25:
                    if rv < 0.30:
                        draw_pebble(window, cam, px, py, deep)
                    else:
                        nn = tilt_normal(n, wx0 * 4, wy0 * 4, k, 0.7)
                        speckle(window, cam, px, py,
                                tone(shade(DIRT_DEEP, nn),
                                     0.85 if rv < 0.6 else 1.1))


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
        if ((x, y) in G.DENTED or (x, y) in G._RIMTILES
                or (x + 1, y) in G.DENTED or (x - 1, y) in G.DENTED
                or (x, y + 1) in G.DENTED or (x, y - 1) in G.DENTED
                or (x + 1, y) in G._RIMTILES or (x - 1, y) in G._RIMTILES
                or (x, y + 1) in G._RIMTILES or (x, y - 1) in G._RIMTILES):
            # поле продолжается и на соседей: край воронки без ступени
            _draw_crater_field(window, cam, x, y)


# ---------------------------------------------------------------------------
# Тропинки и гарь: непрерывное поле износа вместо плиток по чанкам
# ---------------------------------------------------------------------------
_WEAR_CACHE = {"key": None, "surf": None}
_WEAR_RES = 6          # узлов сетки износа на клетку
_WEAR_W = 0.30         # ширина тропинки в клетках (ступня человека)


def _stamp_add(field, cx, cy, radius, amount):
    r = int(math.ceil(radius))
    h, w = field.shape
    x0, x1 = max(0, int(cx) - r), min(w, int(cx) + r + 1)
    y0, y1 = max(0, int(cy) - r), min(h, int(cy) + r + 1)
    if x1 <= x0 or y1 <= y0:
        return
    ys, xs = np.mgrid[y0:y1, x0:x1]
    d2 = ((xs - cx) ** 2 + (ys - cy) ** 2) / (radius * radius)
    kern = np.clip(1.0 - d2, 0.0, 1.0) ** 2
    field[y0:y1, x0:x1] += kern * amount


def draw_wear_layer(window, cam, wear, scorch):
    """Тонкие тропинки и потемнения от взрывов одним непрерывным полем.

    Износ копится в узлах мелкой сетки (тропинка шириной со ступню, а не
    с клетку), растеризуется в маску, размывается и тонируется крупным
    непрерывным шумом — никаких границ клеток, швов и «плитки».
    """
    if not wear and not scorch:
        return
    li = int(G.DAYT * 72) % 72
    key = ((cam.win_w, cam.win_h), round(cam.zoom, 3), cam.rot,
           round(cam.x + cam.shx, 1), round(cam.y + cam.shy, 1),
           0 if G.VIL is None else G.VIL.get("wear_ver", 0),
           len(scorch), li)
    if _WEAR_CACHE["key"] == key:
        e = _WEAR_CACHE["surf"]
        if e is not None:
            window.blit(e[0], (e[1], e[2]))
        return
    RES = _WEAR_RES
    NW, NH = GRID_W * RES + 1, GRID_D * RES + 1
    Fw = np.zeros((NH, NW), np.float32)
    Fs = np.zeros((NH, NW), np.float32)
    if wear:
        for (tx, ty), wv in wear.items():
            if wv < 1.1:
                continue
            _stamp_add(Fw, tx * RES, ty * RES, _WEAR_W * RES * 1.25,
                       min(1.0, (wv - 1.0) * 0.16 + 0.22))
    for (sx_, sy_, s_, r_) in scorch:
        _stamp_add(Fs, sx_ * RES, sy_ * RES, max(2.0, r_ * RES * 0.95),
                   0.85 * s_)
    act = np.maximum(Fw, Fs)
    ys, xs = np.nonzero(act > 0.04)
    if xs.size == 0:
        _WEAR_CACHE["key"], _WEAR_CACHE["surf"] = key, None
        return
    # экранные координаты всех узлов сетки (аффинно + высота рельефа)
    ox, oy = cam.world_to_screen(0, 0, 0)
    ax, ay = cam.world_to_screen(1, 0, 0)
    bx, by = cam.world_to_screen(0, 1, 0)
    dxx, dxy = ax - ox, ay - oy
    dyx, dyy = bx - ox, by - oy
    ze = cam.zoom / G.PIXEL
    Hg = np.array(G.GH, np.float32)
    gyy, gxx = np.mgrid[0:NH, 0:NW].astype(np.float32) / RES
    ix = np.clip(gxx.astype(int), 0, GRID_W - 1)
    iy = np.clip(gyy.astype(int), 0, GRID_D - 1)
    fx = gxx - ix
    fy = gyy - iy
    hz = (Hg[iy, ix] * (1 - fx) * (1 - fy) + Hg[iy, ix + 1] * fx * (1 - fy)
          + Hg[iy + 1, ix] * (1 - fx) * fy + Hg[iy + 1, ix + 1] * fx * fy)
    PX = ox + gxx * dxx + gyy * dyx
    PY = oy + gxx * dxy + gyy * dyy - hz * TILE_Z * ze
    pxs = PX[ys, xs]
    pys = PY[ys, xs]
    sx0 = int(max(0, pxs.min() - 4))
    sy0 = int(max(0, pys.min() - 4))
    sx1 = int(min(cam.win_w, pxs.max() + 5))
    sy1 = int(min(cam.win_h, pys.max() + 5))
    if sx1 <= sx0 or sy1 <= sy0:
        _WEAR_CACHE["key"], _WEAR_CACHE["surf"] = key, None
        return
    bw, bh = sx1 - sx0, sy1 - sy0
    # маска: ромбы между соседними узлами, где поле заметно
    mask = pygame.Surface((bw, bh), pygame.SRCALPHA)
    thr = 0.10
    quads = 0
    for n in range(xs.size):
        cx, cy = int(xs[n]), int(ys[n])
        if cx + RES >= NW or cy + RES >= NH:
            continue
        if act[cy, cx] < thr:
            continue
        pts = []
        ok = True
        for ddx, ddy in ((0, 0), (RES, 0), (RES, RES), (0, RES)):
            if act[cy + ddy, cx + ddx] < thr * 0.6:
                ok = False
                break
            pts.append((float(PX[cy + ddy, cx + ddx] - sx0),
                        float(PY[cy + ddy, cx + ddx] - sy0)))
        if not ok:
            continue
        pygame.draw.polygon(mask, (255, 255, 255, 255), pts)
        quads += 1
    if not quads:
        _WEAR_CACHE["key"], _WEAR_CACHE["surf"] = key, None
        return
    # surfarray отдаёт массив в порядке [x, y] — транпоним в [y, x]
    arr = (pygame.surfarray.array_alpha(mask).astype(np.float32)
           / 255.0).T
    for _ in range(2):  # размыв: мягкие границы без ступеней
        p = np.pad(arr, 1, mode="edge")
        arr = (p[:-2, :-2] + p[:-2, 1:-1] + p[:-2, 2:]
               + p[1:-1, :-2] + p[1:-1, 1:-1] + p[1:-1, 2:]
               + p[2:, :-2] + p[2:, 1:-1] + p[2:, 2:]) / 9.0
    # значение поля в пикселях экрана: обратная проекция + высота
    yy, xx = np.mgrid[sy0:sy1, sx0:sx1].astype(np.float32)
    det = dxx * dyy - dyx * dxy
    rx = xx - ox
    ry0 = yy - oy
    wx = (rx * dyy - ry0 * dyx) / det
    wy = (ry0 * dxx - rx * dxy) / det
    ixh = np.clip(wx.astype(int), 0, GRID_W - 1)
    iyh = np.clip(wy.astype(int), 0, GRID_D - 1)
    hx = (Hg[iyh, ixh] * 0.25 + Hg[iyh, ixh + 1] * 0.25
          + Hg[iyh + 1, ixh] * 0.25 + Hg[iyh + 1, ixh + 1] * 0.25)
    ry = ry0 + hx * TILE_Z * ze
    wx = (rx * dyy - ry * dyx) / det
    wy = (ry * dxx - rx * dxy) / det
    gx2 = np.clip(wx * RES, 0, NW - 1.001)
    gy2 = np.clip(wy * RES, 0, NH - 1.001)
    ix2 = gx2.astype(int)
    iy2 = gy2.astype(int)
    fx2 = (gx2 - ix2)
    fy2 = (gy2 - iy2)

    def bilerp(F):
        return (F[iy2, ix2] * (1 - fx2) * (1 - fy2)
                + F[iy2, ix2 + 1] * fx2 * (1 - fy2)
                + F[iy2 + 1, ix2] * (1 - fx2) * fy2
                + F[iy2 + 1, ix2 + 1] * fx2 * fy2)

    fw = bilerp(Fw)
    fs = bilerp(Fs)
    aw = np.clip(arr * np.clip(fw * 1.7, 0, 1), 0, 1) * 0.55
    as_ = np.clip(arr * np.clip(fs * 1.5, 0, 1), 0, 1) * 0.80
    # крупный непрерывный шум тона земли (без швов между клетками)
    qx = wx * 0.55
    qy = wy * 0.55
    ix3 = np.floor(qx).astype(int)
    iy3 = np.floor(qy).astype(int)
    fzx = qx - ix3
    fzy = qy - iy3
    u = fzx * fzx * (3 - 2 * fzx)
    vv = fzy * fzy * (3 - 2 * fzy)

    def h2(a, b):
        return np.abs(np.sin(a * 12.9898 + b * 78.233) * 43758.5453) % 1.0

    nz = (h2(ix3, iy3) * (1 - u) * (1 - vv) + h2(ix3 + 1, iy3) * u * (1 - vv)
          + h2(ix3, iy3 + 1) * (1 - u) * vv + h2(ix3 + 1, iy3 + 1) * u * vv)
    tonev = 0.86 + 0.28 * nz
    cw = np.array(shade((142, 122, 86), (0, 0, 1)), np.float32)
    cs = np.array(shade((62, 50, 40), (0, 0, 1)), np.float32)
    at = 1.0 - (1.0 - aw) * (1.0 - as_)
    mixw = aw / np.maximum(at, 1e-4)
    col = (cw[None, None, :] * mixw[:, :, None]
           + cs[None, None, :] * (1 - mixw)[:, :, None])
    col = col * tonev[:, :, None]
    rgba = np.empty((bh, bw, 4), np.uint8)
    rgba[:, :, :3] = np.clip(col, 0, 255).astype(np.uint8)
    rgba[:, :, 3] = np.clip(at * 255, 0, 255).astype(np.uint8)
    surf = pygame.image.frombuffer(rgba.tobytes(), (bw, bh), "RGBA")
    _WEAR_CACHE["key"], _WEAR_CACHE["surf"] = key, (surf, sx0, sy0)
    window.blit(surf, (sx0, sy0))
