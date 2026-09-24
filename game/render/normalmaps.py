# -*- coding: utf-8 -*-
"""Карты нормалей земли/камня/черепицы/дерева/штукатурки (numpy)."""

import math
import numpy as np
import pygame
from game.core import state as G
from game.core.config import (
    BASE_COLORS, DIRT_COLOR, GRASS, TILE_H, TILE_W, WOOD_MATS)
from game.core.utils import (
    unrot_vec)
from game.render.lighting import (
    GROUND_BASE, GROUND_CACHE, shade)

# ---------------------------------------------------------------------------
# Карты нормалей земли (numpy) — как в этапе 3
# ---------------------------------------------------------------------------
def _value_noise(w, h, cx, cy, seed):
    r = np.random.RandomState(seed)
    g = r.rand(cy + 1, cx + 1)
    xs = np.linspace(0, cx, w)
    ys = np.linspace(0, cy, h)
    x0 = np.floor(xs).astype(np.int32)
    y0 = np.floor(ys).astype(np.int32)
    x1 = np.clip(x0 + 1, 0, cx)
    y1 = np.clip(y0 + 1, 0, cy)
    x0 = np.clip(x0, 0, cx)
    y0 = np.clip(y0, 0, cy)
    fx = (xs - np.floor(xs))
    fy = (ys - np.floor(ys))
    sx = fx * fx * (3 - 2 * fx)
    sy = fy * fy * (3 - 2 * fy)
    g00 = g[y0[:, None], x0[None, :]]
    g10 = g[y0[:, None], x1[None, :]]
    g01 = g[y1[:, None], x0[None, :]]
    g11 = g[y1[:, None], x1[None, :]]
    top = g00 * (1 - sx)[None, :] + g10 * sx[None, :]
    bot = g01 * (1 - sx)[None, :] + g11 * sx[None, :]
    return top * (1 - sy)[:, None] + bot * sy[:, None]


def _fbm(w, h, seed, base_cells=4):
    return (_value_noise(w, h, base_cells, base_cells // 2 + 1, seed) * 0.55
            + _value_noise(w, h, base_cells * 3, base_cells * 2, seed + 101) * 0.30
            + _value_noise(w, h, base_cells * 7, base_cells * 5, seed + 202) * 0.15)


def _height_to_normal(h, strength):
    gy, gx = np.gradient(h)
    nx = -gx * strength
    ny = -gy * strength
    nz = np.ones_like(h)
    il = 1.0 / np.sqrt(nx * nx + ny * ny + 1.0)
    return nx * il, ny * il, il


def _diamond_mask(w, h):
    yy, xx = np.mgrid[0:h, 0:w]
    return ((np.abs(xx - (w - 1) / 2) / (w / 2)
             + np.abs(yy - (h - 1) / 2) / (h / 2)) <= 1.0)


def build_ground_base(mat, var):
    key = (mat, var)
    if key in GROUND_BASE:
        return GROUND_BASE[key]
    w, h = TILE_W, TILE_H
    seed = 1000 + var * 77 + (0 if mat == "grass" else 5000)
    mask = _diamond_mask(w, h)
    grain = np.random.RandomState(seed + 7).rand(h, w)
    if mat == "grass":
        base = np.array(GRASS, dtype=np.float32)
        patch = _fbm(w, h, seed, 4)
        height = (_fbm(w, h, seed + 21, 5) * 0.7 + grain * 0.18
                  + _value_noise(w, h, 24, 12, seed + 33) * 0.15)
        albedo = base[None, None, :] * (0.90 + 0.16 * patch[:, :, None])
        albedo *= (0.95 + 0.07 * grain[:, :, None])
        pits = np.random.RandomState(seed + 9).rand(h, w)
        albedo[pits < 0.025] *= 0.78
        albedo[pits > 0.975] *= 1.12
        nu, nv, nw = _height_to_normal(height, 1.7)
    else:
        base = np.array(DIRT_COLOR, dtype=np.float32)
        patch = _fbm(w, h, seed, 3)
        height = (_fbm(w, h, seed + 21, 4) * 0.75 + grain * 0.15)
        clumps = np.random.RandomState(seed + 11).rand(h, w)
        height -= (clumps < 0.06) * 0.55
        height += (clumps > 0.94) * 0.35
        albedo = base[None, None, :] * (0.88 + 0.20 * patch[:, :, None])
        albedo *= (0.94 + 0.07 * grain[:, :, None])
        albedo[clumps < 0.06] *= 0.72
        albedo[clumps > 0.94] *= 1.18
        nu, nv, nw = _height_to_normal(height, 2.5)
    data = dict(albedo=albedo.astype(np.float32), nu=nu, nv=nv, nw=nw, mask=mask)
    GROUND_BASE[key] = data
    return data


def ground_sprite(mat, var, sw, sh, preset_idx, rot, hlev=2):
    key = (mat, var, sw, sh, preset_idx, rot, hlev)
    hit = GROUND_CACHE.get(key)
    if hit is not None:
        return hit[0]
    if len(GROUND_CACHE) > 140:
        GROUND_CACHE.clear()
    d = build_ground_base(mat, var)
    tx = unrot_vec(0.7071, -0.7071, rot)
    ty = unrot_vec(0.7071, 0.7071, rot)
    sU = tx[0] * G.SUN[0] + tx[1] * G.SUN[1]
    sV = ty[0] * G.SUN[0] + ty[1] * G.SUN[1]
    sZ = G.SUN[2]
    dot = np.clip(d["nu"] * sU + d["nv"] * sV + d["nw"] * sZ, 0.0, 1.0)
    w_, c_ = np.array(G.LIGHT["warm"]), np.array(G.LIGHT["cool"])
    lit = d["albedo"] * (G.LIGHT["amb"] * c_ + G.LIGHT["dif"] * dot[:, :, None] * w_)
    lit = np.clip(lit, 0, 255).astype(np.uint8)
    # крупный пиксель: усреднение блоками 4x4 (маска остаётся чёткой)
    lb = lit.reshape(TILE_H // 4, 4, TILE_W // 4, 4, 3).mean(axis=(1, 3))
    lit = lb.repeat(4, axis=0).repeat(4, axis=1).astype(np.uint8)
    if hlev != 2:
        lit = np.clip(lit * (0.78 + 0.11 * hlev), 0, 255).astype(np.uint8)
    alpha = (d["mask"] * 255).astype(np.uint8)
    rgba = np.dstack([lit, alpha])
    buf = rgba.tobytes()
    surf = pygame.image.frombuffer(buf, (TILE_W, TILE_H), "RGBA")
    if (sw, sh) != (TILE_W, TILE_H):
        surf = pygame.transform.scale(surf, (sw, sh))
    GROUND_CACHE[key] = (surf, buf)
    return surf


def build_stone_maps(size=96):
    s = size
    rows, bh = 4, s // 4
    height = np.full((s, s), 0.25, np.float32)
    tint = np.full((s, s), 0.55, np.float32)
    r = np.random.RandomState(42)
    for row in range(rows):
        y0, y1 = row * bh, (row + 1) * bh
        off = (s // 8) if row % 2 else 0
        for x0 in range(-s // 4, s + s // 4, s // 4):
            xa, xb = max(0, x0 + off + 2), min(s, x0 + off + s // 4 - 2)
            ya, yb = y0 + 2, y1 - 2
            if xa >= xb or ya >= yb:
                continue
            height[ya:yb, xa:xb] = 1.0
            tint[ya:yb, xa:xb] = 0.92 + 0.14 * r.rand()
            for k in range(3):
                f = 0.55 + 0.15 * k
                height[ya + k, xa:xb] = min(1.0, f + 0.3)
                height[yb - 1 - k, xa:xb] = f
                height[ya:yb, xa + k] = np.minimum(height[ya:yb, xa + k], f + 0.25)
                height[ya:yb, xb - 1 - k] = np.minimum(height[ya:yb, xb - 1 - k], f + 0.1)
    nu, nv, nw = _height_to_normal(height, 2.0)
    base = np.array(BASE_COLORS["gray"], np.float32)
    albedo = base[None, None, :] * tint[:, :, None]
    return albedo, nu, nv, nw, height


def build_tile_maps(size=96):
    s = size
    rows, rh = 4, s // 4
    height = np.zeros((s, s), np.float32)
    tint = np.full((s, s), 0.90, np.float32)
    r = np.random.RandomState(7)
    tw = s // 6
    for row in range(rows):
        y0 = row * rh
        yy = np.arange(rh) / rh
        prof = np.sin(yy * math.pi) ** 0.7
        xx = np.arange(s) / tw * math.pi + row * 0.7
        arc = np.abs(np.sin(xx)) ** 0.8
        height[y0:y0 + rh, :] = prof[:, None] * 0.55 + arc[None, :] * 0.45
        tint[y0:y0 + rh, :] *= 0.94 + 0.10 * r.rand(rh, s)
        tint[y0 + rh - 2:y0 + rh, :] *= 0.68  # тень нахлёста
        height[y0 + rh - 2:y0 + rh, :] *= 0.4
    tint *= 0.92 + 0.08 * r.rand(s, s)
    nu, nv, nw = _height_to_normal(height, 2.0)
    base = np.array(BASE_COLORS["tile_blue"], np.float32)
    albedo = base[None, None, :] * tint[:, :, None]
    return albedo, nu, nv, nw, height


def build_wood_maps(size=96):
    s = size
    r = np.random.RandomState(11)
    xx = np.arange(s)
    warp = np.sin(xx * 0.25) * 2.0 + np.sin(xx * 0.09 + 2.0) * 3.0
    height = np.zeros((s, s), np.float32)
    for i in range(s):
        height[:, i] = (0.55 + 0.25 * np.sin(i * 0.55 + warp[i] * 0.25)
                        + 0.10 * np.sin(i * 1.7 + 1.0))
    cy, cx = s * 0.38, s * 0.62  # сучок
    yy, xxg = np.mgrid[0:s, 0:s]
    dd = np.sqrt(((xxg - cx) / 9) ** 2 + ((yy - cy) / 6) ** 2)
    height += np.clip(1.2 - dd, 0, 1) * 0.5
    for k in range(1, 4):  # швы досок
        y0 = k * s // 4
        height[y0 - 1:y0 + 1, :] *= 0.35
    tint = 0.86 + 0.16 * (height - height.min()) / max(1e-6, height.max()
                                                       - height.min())
    for k in range(1, 4):
        tint[k * s // 4 - 1:k * s // 4 + 1, :] *= 0.7
    nu, nv, nw = _height_to_normal(height, 1.6)
    base = np.array(BASE_COLORS["wood_light"], np.float32)
    albedo = base[None, None, :] * tint[:, :, None]
    return albedo, nu, nv, nw, height


def build_plaster_maps(size=96):
    s = size
    r = np.random.RandomState(23)
    height = r.rand(s, s).astype(np.float32) * 0.25
    for _ in range(14):
        cx, cy = r.rand() * s, r.rand() * s
        rad = 6 + r.rand() * 16
        yy, xx = np.mgrid[0:s, 0:s]
        height += (np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / rad ** 2)
                   * (0.3 + r.rand() * 0.5))
    height += r.rand(s, s).astype(np.float32) * 0.25
    nu, nv, nw = _height_to_normal(height, 1.2)
    base = np.array(BASE_COLORS["plaster"], np.float32)
    tint = 0.94 + 0.06 * (height - height.min()) / max(1e-6, height.max()
                                                       - height.min())
    albedo = base[None, None, :] * tint[:, :, None]
    return albedo, nu, nv, nw, height


_NMAP_CACHE = {}
_FACE_TAN = {(1, 0, 0): ((0, 1, 0), (0, 0, 1)),
             (-1, 0, 0): ((0, 1, 0), (0, 0, 1)),
             (0, 1, 0): ((1, 0, 0), (0, 0, 1)),
             (0, -1, 0): ((1, 0, 0), (0, 0, 1)),
             (0, 0, 1): ((1, 0, 0), (0, 1, 0))}


def _nmap_for_mat(mat):
    if mat == "tile":
        return build_tile_maps
    if mat in WOOD_MATS:
        return build_wood_maps
    if mat in ("plaster", "cloth"):
        return build_plaster_maps
    return build_stone_maps


def nshade(base, mat, ix, iy, face_n, strength=0.55):
    """Оттенок: нормаль грани возмущена картой нормалей материала."""
    mk = ("tile" if mat == "tile" else
          ("wood" if mat in WOOD_MATS else
           ("plaster" if mat in ("plaster", "cloth") else "stone")))
    e = _NMAP_CACHE.get(mk)
    if e is None:
        a, nu, nv, nw, h = _nmap_for_mat(mat)()
        e = _NMAP_CACHE[mk] = (nu, nv, nw)
    nu, nv, nw = e
    s = nu.shape[0]
    u = float(nu[iy % s, ix % s])
    v = float(nv[iy % s, ix % s])
    w = float(nw[iy % s, ix % s])
    t, b = _FACE_TAN.get(tuple(face_n), ((1, 0, 0), (0, 1, 0)))
    nx = face_n[0] * w + strength * (t[0] * u + b[0] * v)
    ny = face_n[1] * w + strength * (t[1] * u + b[1] * v)
    nz = face_n[2] * w + strength * (t[2] * u + b[2] * v)
    il = 1.0 / max(1e-6, math.sqrt(nx * nx + ny * ny + nz * nz))
    return shade(base, (nx * il, ny * il, nz * il))


def normal_preview_image(kind):
    if kind == "stone":
        albedo, nu, nv, nw, height = build_stone_maps()
        panel = (192, 192)
    elif kind == "tile":
        albedo, nu, nv, nw, height = build_tile_maps()
        panel = (192, 192)
    elif kind == "wood":
        albedo, nu, nv, nw, height = build_wood_maps()
        panel = (192, 192)
    elif kind == "plaster":
        albedo, nu, nv, nw, height = build_plaster_maps()
        panel = (192, 192)
    else:
        d = build_ground_base(kind, 0)
        albedo, nu, nv, nw = d["albedo"], d["nu"], d["nv"], d["nw"]
        height = None
        panel = (192, 96)
    font = pygame.font.Font(None, 24)

    def to_surf(arr):
        a = np.clip(arr, 0, 255).astype(np.uint8)
        return pygame.image.frombuffer(a.tobytes(), (a.shape[1], a.shape[0]),
                                       "RGB" if a.shape[2] == 3 else "RGBA")

    alb = to_surf(albedo)
    nrm = to_surf((np.dstack([nu, nv, nw]) * 0.5 + 0.5) * 255.0)
    if height is None:
        hgt = to_surf(np.dstack([albedo[:, :, 1]] * 3))
    else:
        hgt = to_surf(np.dstack([(height / height.max() * 255)] * 3))
    pw, ph = panel
    img = pygame.Surface((pw * 3 + 40, ph + 60))
    img.fill((24, 26, 34))
    for i, (s, cap) in enumerate([(alb, "albedo"), (nrm, "normal map"),
                                  (hgt, "height" if kind == "stone" else "green")]):
        img.blit(pygame.transform.scale(s, (pw, ph)), (10 + i * (pw + 10), 34))
        img.blit(font.render(cap, True, (220, 220, 230)), (10 + i * (pw + 10), 8))
    names = {"grass": "trava", "dirt": "zemlya", "stone": "kamen",
             "tile": "cherepitsa", "wood": "doski",
             "plaster": "shtukaturka"}
    img.blit(font.render(names[kind], True, (240, 200, 90)), (10, ph + 38))
    return img
