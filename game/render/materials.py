# -*- coding: utf-8 -*-
"""Текстуры стен/крыш по материалам, фахверк, цилиндры, пиксели, сколы."""

import math
import pygame
from game.core import state as G
from game.core.config import (
    BASE_COLORS, LEFT_N, PZ, RIGHT_N, TILE_H, TILE_W, TILE_Z, WOOD_MATS)
from game.core.utils import (
    clamp, hash01, quad_pt)
from game.world.world_state import (
    HOUSE_BURNING, LIGHTS_OFF)
from game.render.lighting import (
    grain_color, shade, tilt_normal, tone)
from game.render.normalmaps import (
    nshade)
from game.render.camera import (
    _proj_ctx, _proj_pt)
from game.render.island import (
    speckle)
from game.render.primitives import (
    box_corner_points, face_texels)

# ---------------------------------------------------------------------------
# Текстуры стен и крыш по материалам (стабильные, без «снега» между кадрами)
# ---------------------------------------------------------------------------
_PANEL_MATS = {"panel", "panel_dark", "concrete", "concrete_g"}
_EARTH_MATS = {"adobe", "dirt", "earth"}
_FIBRE_MATS = {"wattle", "straw", "cloth", "leather", "hide"}
_BRICK_MATS = {"brick", "brick_red"}
_TILES_MATS = {"tile", "tile_red", "tile_blue", "tile_gray", "tile_dark"}


def _quad_mottle(window, quad, lit, seed, n, t_lo, t_hi, f_lo, f_hi,
                 u_lo, u_hi, wu, wt, size_jitter=False):
    for k in range(n):
        u0 = u_lo + hash01(seed, k * 13, 7) * (u_hi - u_lo - wu)
        t0 = t_lo + hash01(seed, k * 17, 29) * (t_hi - t_lo - wt)
        ww = wu * (0.7 + 0.6 * hash01(seed, k * 7, 11)) if size_jitter else wu
        tt = wt * (0.7 + 0.6 * hash01(seed, k * 23, 41)) if size_jitter else wt
        f = f_lo + (f_hi - f_lo) * hash01(seed, k * 31, 53)
        pygame.draw.polygon(window, tone(lit, f),
                            [quad_pt(quad, u0, t0), quad_pt(quad, u0 + ww, t0),
                             quad_pt(quad, u0 + ww, t0 + tt),
                             quad_pt(quad, u0, t0 + tt)])


def draw_wall_face(window, quad, mat, base_raw, face_n, seed, preset_idx,
                   cam, world_w, world_h, face_id=1):
    """Грань стены с текстурой материала. quad: [верх-0, верх-1, низ-1, низ-0]."""
    fw = math.hypot(quad[1][0] - quad[0][0], quad[1][1] - quad[0][1])
    lit = shade(base_raw, face_n)
    f_t = 0.95 + 0.10 * hash01(seed, face_id * 7, 3)  # собственный тон стены
    pygame.draw.polygon(window, tone(lit, f_t), quad)
    if fw < 11:
        return
    m = mat or "concrete"
    if m in WOOD_MATS:
        rows = max(2, min(16, int(round(world_h / 0.30))))
        for r in range(rows):
            t0, t1 = r / rows, (r + 1) / rows
            f = f_t * (0.89 + 0.20 * hash01(seed, r * 13, 1))
            pygame.draw.polygon(window, tone(lit, f),
                                [quad_pt(quad, 0, t0), quad_pt(quad, 1, t0),
                                 quad_pt(quad, 1, t1), quad_pt(quad, 0, t1)])
            pygame.draw.line(window, tone(lit, f_t * 0.62),
                             quad_pt(quad, 0, t1 - 0.012),
                             quad_pt(quad, 1, t1 - 0.012), 1)
            pygame.draw.line(window, tone(lit, f * 1.10),
                             quad_pt(quad, 0, t0 + 0.014),
                             quad_pt(quad, 1, t0 + 0.014), 1)
        if fw >= 26:  # сучки
            for k in range(3):
                kk = int(hash01(seed, 91, k * 7) * rows)
                u = 0.12 + 0.76 * hash01(seed, 97, k * 13)
                t = (kk + 0.45) / rows
                px, py = quad_pt(quad, u, t)
                pygame.draw.ellipse(window, tone(lit, f_t * 0.58),
                                    (px - 1, py - 1, 2, 2))
    elif m in _PANEL_MATS:
        ncols = max(2, min(8, int(round(world_w / 1.1))))
        for c in range(ncols):
            u0, u1 = c / ncols, (c + 1) / ncols
            f = f_t * (0.91 + 0.14 * hash01(seed, c * 29, 5))
            pygame.draw.polygon(window, tone(lit, f),
                                [quad_pt(quad, u0, 0), quad_pt(quad, u1, 0),
                                 quad_pt(quad, u1, 1), quad_pt(quad, u0, 1)])
            if u1 < 1.0:
                pygame.draw.line(window, tone(lit, f_t * 0.70),
                                 quad_pt(quad, u1, 0.02),
                                 quad_pt(quad, u1, 0.98), 1)
        pygame.draw.line(window, tone(lit, f_t * 0.72),
                         quad_pt(quad, 0.02, 0.5), quad_pt(quad, 0.98, 0.5), 1)
        if fw >= 30:
            _quad_mottle(window, quad, lit, seed + 733, 8, 0.07, 0.85,
                         0.90, 1.10, 0.05, 0.92, 0.13, 0.11)
    elif m in _EARTH_MATS:
        rows = max(2, min(12, int(round(world_h / 0.34))))
        for r in range(rows):
            t0, t1 = r / rows, (r + 1) / rows
            f = f_t * (0.89 + 0.20 * hash01(seed, r * 13, 1))
            pygame.draw.polygon(window, tone(lit, f),
                                [quad_pt(quad, 0, t0), quad_pt(quad, 1, t0),
                                 quad_pt(quad, 1, t1), quad_pt(quad, 0, t1)])
            pygame.draw.line(window, tone(lit, f_t * 0.64),
                             quad_pt(quad, 0, t1 - 0.01),
                             quad_pt(quad, 1, t1 - 0.01), 1)
        if fw >= 20:  # вертикальные швы со смещением
            ncol = max(3, min(9, int(round(world_w / 0.55))))
            for r in range(rows):
                t0, t1 = r / rows, (r + 1) / rows
                off = 0.5 if r % 2 else 0.0
                for c in range(ncol + 1):
                    u = (c + off) / ncol
                    if u <= 0.02 or u >= 0.98:
                        continue
                    pygame.draw.line(window, tone(lit, f_t * 0.72),
                                     quad_pt(quad, u, t0 + 0.05),
                                     quad_pt(quad, u, t1 - 0.05), 1)
    elif m in _FIBRE_MATS:
        rows = max(3, min(18, int(round(world_h / 0.16))))
        for r in range(rows):
            t0, t1 = r / rows, (r + 1) / rows
            f = f_t * (0.93 + 0.14 * hash01(seed, r * 11, 2))
            pygame.draw.polygon(window, tone(lit, f),
                                [quad_pt(quad, 0, t0), quad_pt(quad, 1, t0),
                                 quad_pt(quad, 1, t1), quad_pt(quad, 0, t1)])
        if fw >= 18:  # прутья/нити: штрихи со смещением
            nd = max(4, min(14, int(round(world_w / 0.22))))
            for r in range(rows):
                t0, t1 = r / rows, (r + 1) / rows
                off = 0.5 if r % 2 else 0.0
                f = f_t * (0.84 + 0.22 * hash01(seed, r * 19, 4))
                for k in range(nd):
                    u0 = (k + off) / nd
                    u1 = u0 + 0.42 / nd
                    if u1 <= 0.02 or u0 >= 0.98:
                        continue
                    pygame.draw.line(window, tone(lit, f),
                                     quad_pt(quad, clamp(u0, 0, 1), t0 + 0.04),
                                     quad_pt(quad, clamp(u1, 0, 1), t1 - 0.04), 1)
    elif m in _BRICK_MATS:
        rows = max(2, min(14, int(round(world_h / 0.24))))
        ncol = max(3, min(12, int(round(world_w / 0.5))))
        for r in range(rows):
            t0, t1 = r / rows, (r + 1) / rows
            off = 0.5 if r % 2 else 0.0
            for c in range(ncol + 1):
                u0 = (c + off) / ncol
                u1 = (c + 1 + off) / ncol
                u0c, u1c = clamp(u0, 0, 1), clamp(u1, 0, 1)
                if u1c <= 0.01 or u0c >= 0.99:
                    continue
                f = f_t * (0.92 + 0.16 * hash01(seed, r * 31 + c, 6))
                pygame.draw.polygon(window, tone(lit, f),
                                    [quad_pt(quad, u0c, t0 + 0.02),
                                     quad_pt(quad, u1c, t0 + 0.02),
                                     quad_pt(quad, u1c, t1 - 0.02),
                                     quad_pt(quad, u0c, t1 - 0.02)])
    elif m in _TILES_MATS:
        rows = max(3, min(8, int(round(world_h / 0.34))))
        for r in range(rows):
            t0, t1 = r / rows, (r + 1) / rows
            f = f_t * (0.94 + 0.12 * hash01(seed, r * 11, 3))
            pygame.draw.polygon(window, tone(lit, f),
                                [quad_pt(quad, 0, t0), quad_pt(quad, 1, t0),
                                 quad_pt(quad, 1, t1), quad_pt(quad, 0, t1)])
            pygame.draw.line(window, tone(lit, f_t * 0.62),
                             quad_pt(quad, 0.02, t1 - 0.015),
                             quad_pt(quad, 0.98, t1 - 0.015), 1)
            pygame.draw.line(window, tone(lit, f * 1.12),
                             quad_pt(quad, 0.02, t0 + 0.02),
                             quad_pt(quad, 0.98, t0 + 0.02), 1)
    else:  # штукатурка / краска / прочее: разводы + трещины
        _quad_mottle(window, quad, lit, seed + 91, 10, 0.05, 0.84,
                     0.89, 1.11, 0.04, 0.88, 0.17, 0.15, size_jitter=True)
        if fw >= 40:
            for k in range(2):
                u = 0.15 + 0.7 * hash01(seed, k * 43, 17)
                pts = []
                uu, tt = u, 0.1 + 0.3 * hash01(seed, k * 57, 23)
                for s in range(3):
                    pts.append(quad_pt(quad,
                                       clamp(uu + (hash01(seed, k * 71, s) - 0.5) * 0.12, 0.03, 0.97),
                                       tt))
                    tt += 0.16 + 0.1 * hash01(seed, k * 83, s + 5)
                pygame.draw.lines(window, tone(lit, f_t * 0.72), False, pts, 1)
    # зерно штукатурки крупным планом (стабильное, кэшированное)
    if m in ("plaster", "white", "concrete", "concrete_g", "panel") and fw >= 30:
        rows = max(2, min(5, int(round(world_h / 0.5))))
        cols = max(2, min(6, int(round(world_w / 0.5))))
        for r in range(rows):
            t0, t1 = r / rows, (r + 1) / rows
            for c in range(cols):
                u0, u1 = c / cols, (c + 1) / cols
                g = grain_color(preset_idx, base_raw, face_n,
                                seed + c * 7 + face_id * 101, r * 13)
                pygame.draw.polygon(window, g,
                                    [quad_pt(quad, u0, t0), quad_pt(quad, u1, t0),
                                     quad_pt(quad, u1, t1), quad_pt(quad, u0, t1)])


def draw_top_face(window, cam, quad, mat, base_raw, seed, w, d):
    """Верхняя грань бокса: устойчивый тон + рисунок материала."""
    lit = shade(base_raw, PZ)
    f_t = 0.97 + 0.08 * hash01(seed, 5, 9)
    pygame.draw.polygon(window, tone(lit, f_t), quad)
    fw = max(math.hypot(quad[1][0] - quad[0][0], quad[1][1] - quad[0][1]),
             math.hypot(quad[3][0] - quad[0][0], quad[3][1] - quad[0][1]))
    if fw < 20:
        return
    m = mat or "concrete"
    if m in _TILES_MATS or (m == "tile"):
        rows = 4
        for r in range(1, rows):
            t = r / rows
            pygame.draw.line(window, tone(lit, f_t * 0.72),
                             quad_pt(quad, 0.03, t), quad_pt(quad, 0.97, t), 1)
            pygame.draw.line(window, tone(lit, f_t * 1.10),
                             quad_pt(quad, 0.03, t + 0.02),
                             quad_pt(quad, 0.97, t + 0.02), 1)
    elif m in _FIBRE_MATS:
        nd = max(6, min(16, int(round(max(w, d) / 0.3))))
        for k in range(nd):
            u = (k + 0.5) / nd
            tt = 0.08 + 0.8 * hash01(seed, k * 13, 7)
            f = f_t * (0.9 + 0.2 * hash01(seed, k * 7, 3))
            pygame.draw.line(window, tone(lit, f),
                             quad_pt(quad, u, tt),
                             quad_pt(quad, u + 0.05, tt + 0.1), 1)
    elif m in ("turf", "dirt", "grass") or base_raw == BASE_COLORS.get("turf"):
        for k in range(14):
            u = hash01(seed, k * 13, 11)
            t = hash01(seed, k * 17, 13)
            f = f_t * (0.88 + 0.24 * hash01(seed, k * 23, 29))
            pygame.draw.ellipse(window, tone(lit, f),
                                (quad_pt(quad, u, t)[0] - 1,
                                 quad_pt(quad, u, t)[1] - 1, 2, 2))
    elif m in WOOD_MATS:
        rows = max(2, min(6, int(round(min(w, d) / 0.35))))
        for r in range(1, rows):
            t = r / rows
            pygame.draw.line(window, tone(lit, f_t * 0.70),
                             quad_pt(quad, 0.05, t), quad_pt(quad, 0.95, t), 1)
    elif m in _PANEL_MATS:
        for t in (0.33, 0.66):
            pygame.draw.line(window, tone(lit, f_t * 0.78),
                             quad_pt(quad, 0.08, t), quad_pt(quad, 0.92, t), 1)
    else:
        _quad_mottle(window, quad, lit, seed + 41, 6, 0.08, 0.78,
                     0.94, 1.06, 0.06, 0.84, 0.14, 0.12, size_jitter=True)


def draw_stone_face(window, quad, base_raw, face_n, seed, h_px, zoom):
    top_len = math.hypot(quad[1][0] - quad[0][0], quad[1][1] - quad[0][1])
    rows = max(1, int(round(h_px / (TILE_Z * zoom / G.PIXEL) / 0.5)))
    world_len = top_len / (math.hypot(TILE_W / 2, TILE_H / 2) * (zoom / G.PIXEL))
    cols = max(1, int(round(world_len / 0.6)))
    lit = shade(base_raw, face_n)
    mortar = tone(lit, 0.52)
    pygame.draw.polygon(window, mortar, quad)
    elev_f = clamp(G.SUN[2] * 1.6, 0.25, 1.0)
    for r in range(rows):
        t0, t1 = r / rows, (r + 1) / rows
        tc = (t0 + t1) / 2
        band_f = 1.0 if tc < 0.58 else (0.94 if tc < 0.84 else 0.85)
        off = 0.5 if r % 2 else 0.0
        for c in range(-1, cols + 1):
            u0 = (c + off) / cols
            u1 = (c + 1 + off) / cols
            if u1 < 0 or u0 > 1:
                continue
            u0c, u1c = clamp(u0, 0, 1), clamp(u1, 0, 1)
            bn = tilt_normal(face_n, seed + r * 131, c * 17 + 3, 5, 0.5)
            tint = (0.90 + 0.18 * hash01(seed, r * 31 + c, 5)) * band_f
            cell = tone(shade(base_raw, bn), tint)
            pts = [quad_pt(quad, u0c, t0), quad_pt(quad, u1c, t0),
                   quad_pt(quad, u1c, t1), quad_pt(quad, u0c, t1)]
            pygame.draw.polygon(window, cell, pts)
            pygame.draw.line(window, tone(cell, 1 + 0.20 * elev_f),
                             pts[0], pts[1], 1)
            pygame.draw.line(window, tone(cell, 1 - 0.26 * elev_f),
                             pts[3], pts[2], 1)
    mw = 1 if zoom < 1.2 else 2
    for r in range(1, rows):
        t = r / rows
        pygame.draw.line(window, mortar, quad_pt(quad, 0, t), quad_pt(quad, 1, t), mw)
    for r in range(rows):
        t0, t1 = r / rows, (r + 1) / rows
        off = 0.5 if r % 2 else 0.0
        for c in range(cols + 1):
            u = (c + off) / cols
            if 0 < u < 1:
                pygame.draw.line(window, mortar,
                                 quad_pt(quad, u, t0), quad_pt(quad, u, t1), mw)


def draw_stone_top(window, diamond, base_raw, cam, seed):
    q = diamond
    lit = shade(base_raw, PZ)
    mortar = tone(lit, 0.55)
    pygame.draw.polygon(window, mortar, q)
    for r in range(2):
        for c in range(2):
            bn = tilt_normal(PZ, seed + r, c, 9, 0.4)
            tint = 0.92 + 0.14 * hash01(seed, r * 2 + c, 9)
            pygame.draw.polygon(window, tone(shade(base_raw, bn), tint),
                                [quad_pt(q, c / 2, r / 2), quad_pt(q, (c + 1) / 2, r / 2),
                                 quad_pt(q, (c + 1) / 2, (r + 1) / 2),
                                 quad_pt(q, c / 2, (r + 1) / 2)])
    pygame.draw.line(window, mortar, quad_pt(q, 0.5, 0), quad_pt(q, 0.5, 1), 1)
    pygame.draw.line(window, mortar, quad_pt(q, 0, 0.5), quad_pt(q, 1, 0.5), 1)
    cx = (q[0][0] + q[2][0]) / 2
    cy = (q[0][1] + q[2][1]) / 2
    for k in range(8):
        corner = q[k % 4]
        f = 0.15 + 0.6 * hash01(seed, k, 13)
        nn = tilt_normal(PZ, seed, k, 14, 0.5)
        speckle(window, cam, cx + (corner[0] - cx) * f,
                cy + (corner[1] - cy) * f,
                tone(shade(base_raw, nn), 0.8 if k % 2 else 1.15))


def draw_box_faces(window, cam, x, y, z, w, d, h, base, seed, stone, preset_idx, mat=None):
    p1, p2, p3, p4, p2b, p3b, p4b = box_corner_points(cam, x, y, z, w, d, h)
    h_px = h * TILE_Z * cam.zoom / G.PIXEL
    if stone:
        draw_stone_face(window, [p2, p3, p3b, p2b], base, RIGHT_N[cam.rot],
                        seed * 3 + 1, h_px, cam.zoom)
        draw_stone_face(window, [p4, p3, p3b, p4b], base, LEFT_N[cam.rot],
                        seed * 3 + 2, h_px, cam.zoom)
        draw_stone_top(window, [p1, p2, p3, p4], base, cam, seed * 3 + 3)
    else:
        rw = d if cam.rot % 2 == 0 else w
        lw = w if cam.rot % 2 == 0 else d
        draw_wall_face(window, [p2, p3, p3b, p2b], mat, base, RIGHT_N[cam.rot],
                       seed * 5 + 1, preset_idx, cam, rw, h, face_id=1)
        draw_wall_face(window, [p4, p3, p3b, p4b], mat, base, LEFT_N[cam.rot],
                       seed * 5 + 2, preset_idx, cam, lw, h, face_id=2)
        draw_top_face(window, cam, [p1, p2, p3, p4], mat, base, seed * 5 + 3,
                      w, d)


def draw_pyramid(window, cam, x, y, z, w, d, h, base, seed, stone, preset_idx,
                 mat=None):
    levels = 3
    for i in range(levels):
        # пропорциональный спад: и маленькие шалаши читаются как пирамида
        f = 1.0 - i * 0.36
        ww = max(0.14, w * f)
        dd = max(0.14, d * f)
        xi = x + (w - ww) / 2
        yi = y + (d - dd) / 2
        draw_box_faces(window, cam, xi, yi, z + h * i / levels, ww, dd,
                       h / levels, tone(base, 1.0 + i * 0.05),
                       seed + i * 977, stone, preset_idx, mat)


def draw_timber_face(window, q, base, n, wide, beams_only=False):
    """Фахверк: штукатурка + тёмные балки (стойки, обвязки, раскос)."""
    if not beams_only:
        pygame.draw.polygon(window, shade(base, n), q)
    fw = math.hypot(q[1][0] - q[0][0], q[1][1] - q[0][1])
    bl = nshade(BASE_COLORS["wood_dark"], "wood_dark",
                int(q[0][0] * 2.3), int(q[0][1] * 3.1), n, 0.5)
    if fw >= 48 and not beams_only:  # рельеф штукатурки из карты нормалей
        si = int(q[0][0] * 2.1 + q[0][1] * 3.7)
        flat = shade(base, n)
        for k, (uu0, uu1, tt0, tt1) in enumerate(
                ((0.08, 0.42, 0.15, 0.55), (0.55, 0.92, 0.45, 0.85))):
            pn = nshade(base, "plaster", si + k * 31, k * 17 + 3, n, 0.9)
            mix = tuple((pn[i] + flat[i]) // 2 for i in range(3))
            pygame.draw.polygon(window, mix,
                                [quad_pt(q, uu0, tt0), quad_pt(q, uu1, tt0),
                                 quad_pt(q, uu1, tt1), quad_pt(q, uu0, tt1)])
    if fw >= 30 and not beams_only:  # плетёнка: контрастная матовая стена
        flat = shade(base, n)
        si = int(q[0][0] * 2.1 + q[0][1] * 3.7)
        pygame.draw.polygon(window, tone(flat, 0.80),
                            [quad_pt(q, 0.10, 0.12), quad_pt(q, 0.90, 0.12),
                             quad_pt(q, 0.90, 0.88), quad_pt(q, 0.10, 0.88)])
        nlat = max(5, min(13, int(round(fw / 4.5))))
        for r in range(nlat):
            tt = 0.14 + 0.72 * (r + 0.5) / nlat
            f = 0.66 + 0.22 * hash01(si + r * 13, r * 7, 5)
            pygame.draw.line(window, tone(flat, f),
                             quad_pt(q, 0.10, tt), quad_pt(q, 0.90, tt), 1)
            tt2 = min(0.86, tt + 0.5 * 0.72 / nlat)
            pygame.draw.line(window, tone(flat, 1.02),
                             quad_pt(q, 0.10, tt2), quad_pt(q, 0.90, tt2), 1)
        nv = max(7, min(19, int(round(fw / 3.8))))
        for c in range(nv):
            uu = 0.12 + 0.76 * (c + 0.5) / nv
            f = 0.62 + 0.20 * hash01(si + c * 17, c * 11, 9)
            pygame.draw.line(window, tone(flat, f),
                             quad_pt(q, uu, 0.14), quad_pt(q, uu, 0.86), 1)
    if fw < 24:  # кроха (субпиксели x3): чистая штукатурка
        return
    if fw < 48:  # микро: чёткий контур 1px вместо заливок
        pygame.draw.line(window, bl, quad_pt(q, 0, 0), quad_pt(q, 0, 1), 1)
        pygame.draw.line(window, bl, quad_pt(q, 1, 0), quad_pt(q, 1, 1), 1)
        pygame.draw.line(window, bl, quad_pt(q, 0, 0.06), quad_pt(q, 1, 0.06),
                         1)
        pygame.draw.line(window, bl, quad_pt(q, 0, 0.94), quad_pt(q, 1, 0.94),
                         1)
        return
    bu = 0.07 if wide else 0.10
    for u0, u1 in ((0.0, bu), (1 - bu, 1.0)):
        pygame.draw.polygon(window, bl, [quad_pt(q, u0, 0), quad_pt(q, u1, 0),
                                        quad_pt(q, u1, 1), quad_pt(q, u0, 1)])
    for t0, t1 in ((0.0, 0.10), (0.90, 1.0)):
        pygame.draw.polygon(window, bl, [quad_pt(q, 0, t0), quad_pt(q, 1, t0),
                                        quad_pt(q, 1, t1), quad_pt(q, 0, t1)])
    elev_f = clamp(G.SUN[2] * 1.6, 0.25, 1.0)  # свет сверху, тень снизу балок
    pygame.draw.line(window, tone(bl, 1 + 0.18 * elev_f),
                     quad_pt(q, 0, 0.0), quad_pt(q, 1, 0.0), 1)
    pygame.draw.line(window, tone(bl, 1 - 0.22 * elev_f),
                     quad_pt(q, 0, 1.0), quad_pt(q, 1, 1.0), 1)
    if wide:
        for u0, u1 in ((0.31, 0.38), (0.62, 0.69)):
            pygame.draw.polygon(window, tone(bl, 0.95),
                                [quad_pt(q, u0, 0.1), quad_pt(q, u1, 0.1),
                                 quad_pt(q, u1, 0.9), quad_pt(q, u0, 0.9)])
        pygame.draw.line(window, tone(bl, 0.9),
                         quad_pt(q, 0.10, 0.88), quad_pt(q, 0.30, 0.12), 2)


def draw_tile_face(window, q, base, n):
    """Черепица: ряды с тенью и разбежкой вертикальных швов."""
    pygame.draw.polygon(window, shade(base, n), q)
    fw = math.hypot(q[1][0] - q[0][0], q[1][1] - q[0][1])
    if fw < 12:
        return
    lit = shade(base, n)
    facing = max(0.0, n[0] * G.SUN[0] + n[1] * G.SUN[1] + n[2] * G.SUN[2])
    sh_t = 0.60 - 0.16 * (1 - facing)  # тень глубже на теневой стороне
    rows, nt = 3, 6
    for r in range(rows):
        t0, t1 = r / rows, (r + 1) / rows
        rj = 0.96 + 0.08 * hash01(int(q[0][0] * 3.3) + r * 11,
                                      r * 7 + 1, 91)
        pygame.draw.line(window, tone(lit, sh_t * rj),
                         quad_pt(q, 0.02, t1 - 0.02),
                         quad_pt(q, 0.98, t1 - 0.02), 1)
        pygame.draw.line(window, tone(lit, (1.14 + 0.12 * facing) * rj),
                         quad_pt(q, 0.02, t0 + 0.03),
                         quad_pt(q, 0.98, t0 + 0.03), 1)
        off = 0.5 / nt if r % 2 else 0.0
        for k in range(nt + 1):
            u = (k + off) / nt
            if u <= 0.02 or u >= 0.98:
                continue
            pygame.draw.line(window, tone(lit, 0.72),
                             quad_pt(q, u, t0 + 0.06),
                             quad_pt(q, u, t1 - 0.04), 1)


def draw_gable(window, cam, x, y, z, w, d, h, base, seed, preset_idx,
               ends="timber"):
    """Щипцовая крыша: 3 уступа, скаты — черепица, торцы — фахверк/камень."""
    plaster = BASE_COLORS["plaster"]
    LV = 2 if h < 0.7 else 3
    step = (d / 2 - 0.2) / (LV - 1)
    h_px = (h / LV) * TILE_Z * cam.zoom / G.PIXEL
    top = None
    for i in range(LV):
        dd = d - 2 * i * step
        lvl = tone(base, 1.0 + i * 0.07)
        p1, p2, p3, p4, p2b, p3b, p4b = box_corner_points(
            cam, x, y + i * step, z + h * i / LV, w, dd, h / LV)
        def _hide_face(q, s2):
            # шкура: швы поперёк, жирные тёмные полосы (олений рисунок),
            # светлые пятна — узор крупный, читается на любом зуме
            pygame.draw.polygon(window, shade(lvl, n), q)
            for t in (0.26, 0.52, 0.78):
                pygame.draw.line(window, tone(lvl, 0.70),
                                 quad_pt(q, 0.05, t),
                                 quad_pt(q, 0.95, t), 1)
            lw = max(2, int(h_px * 0.2))
            for u0 in (0.16, 0.40, 0.62, 0.86):
                u = u0 + (hash01(s2, 11, 7) - 0.5) * 0.05
                pygame.draw.line(window, tone(lvl, 0.44),
                                 quad_pt(q, u, 0.08),
                                 quad_pt(q, u, 0.93), lw)
            r = max(2, int(h_px * 0.14))
            for u, t in ((0.28, 0.34), (0.52, 0.60), (0.78, 0.28),
                         (0.66, 0.78), (0.36, 0.72)):
                c = quad_pt(q, u, t)
                pygame.draw.circle(window, tone(lvl, 1.5),
                                   (int(c[0]), int(c[1])), r)
            for u, t in ((0.5, 0.4), (0.2, 0.55), (0.9, 0.6),
                         (0.45, 0.2)):
                c = quad_pt(q, u, t)
                pygame.draw.circle(window, tone(lvl, 1.3),
                                   (int(c[0]), int(c[1])),
                                   max(1, r // 2))

        for n, q in ((RIGHT_N[cam.rot], [p2, p3, p3b, p2b]),
                     (LEFT_N[cam.rot], [p4, p3, p3b, p4b])):
            if ends == "hide":
                _hide_face(q, seed + i * 131)
            elif n[0] != 0:
                if ends == "stone":
                    draw_stone_face(window, q, BASE_COLORS["gray"], n,
                                    seed + i * 977, h_px, cam.zoom)
                else:
                    draw_timber_face(window, q, tone(plaster, 0.92), n,
                                     True)
            else:
                draw_tile_face(window, q, lvl, n)
        pygame.draw.polygon(window, shade(lvl, PZ), [p1, p2, p3, p4])
        if ends == "hide":
            # шкуры на скатах: шов вдоль конька + светлые пятна —
            # каждый уступ выглядит как отдельная шкура
            bq = [p1, p2, p3, p4]
            for t in (0.3, 0.7):
                pygame.draw.line(window, tone(lvl, 0.66),
                                 quad_pt(bq, 0.06, t),
                                 quad_pt(bq, 0.94, t),
                                 1 if h_px < 8 else 2)
            for u, t in ((0.2, 0.5), (0.55, 0.38), (0.8, 0.62)):
                c = quad_pt(bq, u, t)
                pygame.draw.circle(window, tone(lvl, 1.45),
                                   (int(c[0]), int(c[1])),
                                   max(1, int(h_px * 0.1)))
        top = [p1, p2, p3, p4]
    if top is not None:  # конёк: светлый брус вдоль верха
        fw = math.hypot(top[1][0] - top[0][0], top[1][1] - top[0][1])
        if fw >= 6:
            pygame.draw.line(window, tone(shade(base, PZ), 1.35),
                             quad_pt(top, 0.04, 0.5),
                             quad_pt(top, 0.96, 0.5),
                             2 if fw >= 14 else 1)


def _draw_timber_eroded(window, cam, o):
    """Балки побитой стены: только по целым ячейкам, с разрывами."""
    g = o.get("_chipgrid")
    if g is None:
        return
    chips = o.get("chips", ())
    nx, ny, nz = g["nx"], g["ny"], g["nz"]
    cw, cd, ch = g["cw"], g["cd"], g["ch"]
    VR, VL = RIGHT_N[cam.rot], LEFT_N[cam.rot]

    def proj(x, y, z):
        xr, yr = cam.rotate_point(x, y)
        return cam.iso_project(xr, yr, z)

    for n in (VR, VL):
        beam = shade(BASE_COLORS["wood_dark"], n)
        if n[0] != 0:
            along, nn = "y", ny
            plane = o["x"] + o["w"] if n[0] == 1 else o["x"]
            fixed = nx - 1 if n[0] == 1 else 0
            wide = o["d"] > 1.1
        else:
            along, nn = "x", nx
            plane = o["y"] + o["d"] if n[1] == 1 else o["y"]
            fixed = ny - 1 if n[1] == 1 else 0
            wide = o["w"] > 1.1
        bu = 0.07 if wide else 0.10
        for j in range(nn):
            for k in range(nz):
                key = (fixed, j, k) if along == "y" else (j, fixed, k)
                if key in chips:
                    continue
                u, v = (j + 0.5) / nn, (k + 0.5) / nz
                is_beam = (u < bu or u > 1 - bu or v < 0.10 or v > 0.90)
                if wide and not is_beam:
                    is_beam = ((0.31 <= u <= 0.38 or 0.62 <= u <= 0.69)
                               and 0.10 <= v <= 0.90)
                if wide and not is_beam and 0.06 <= u <= 0.34:
                    vd = 0.12 + (0.88 - 0.12) * (u - 0.10) / 0.20
                    is_beam = abs(v - vd) < 0.07
                if not is_beam:
                    continue
                if along == "y":
                    y0, y1 = o["y"] + j * cd, o["y"] + (j + 1) * cd
                    z0, z1 = o["z"] + k * ch, o["z"] + (k + 1) * ch
                    q = [proj(plane, y0, z1), proj(plane, y1, z1),
                         proj(plane, y1, z0), proj(plane, y0, z0)]
                else:
                    x0, x1 = o["x"] + j * cw, o["x"] + (j + 1) * cw
                    z0, z1 = o["z"] + k * ch, o["z"] + (k + 1) * ch
                    q = [proj(x0, plane, z1), proj(x1, plane, z1),
                         proj(x1, plane, z0), proj(x0, plane, z0)]
                pygame.draw.polygon(window, beam, q)


def _draw_timber_dressing(window, cam, o, eroded):
    """Балки поверх стены; на битой — уцелевший каркас поверх дыр."""
    base = BASE_COLORS[o["color"]]
    p1, p2, p3, p4, p2b, p3b, p4b = box_corner_points(cam, o["x"], o["y"],
                                                     o["z"], o["w"], o["d"],
                                                     o["h"])
    rw = o["d"] if cam.rot % 2 == 0 else o["w"]
    lw = o["w"] if cam.rot % 2 == 0 else o["d"]
    draw_timber_face(window, [p2, p3, p3b, p2b], base, RIGHT_N[cam.rot],
                     rw > 1.1, eroded)
    draw_timber_face(window, [p4, p3, p3b, p4b], base, LEFT_N[cam.rot],
                     lw > 1.1, eroded)


def _glow_quad(window, q, color, alpha):
    xs = [p[0] for p in q]
    ys = [p[1] for p in q]
    x0, y0 = int(min(xs)) - 2, int(min(ys)) - 2
    w, h = int(max(xs)) - x0 + 4, int(max(ys)) - y0 + 4
    if w <= 0 or h <= 0:
        return
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, color + (alpha // 3,), s.get_rect())
    inner = s.get_rect().inflate(-4, -4)
    if inner.width > 0 and inner.height > 0:
        pygame.draw.rect(s, color + (alpha,), inner)
    window.blit(s, (x0, y0))


def _draw_face_detail(window, cam, o):
    """Дверь/окно/топка на грани: по ячейкам, сквозь сколы не рисуем."""
    d = o.get("detail")
    if not d:
        return
    n = d["n"]
    VR, VL = RIGHT_N[cam.rot], LEFT_N[cam.rot]
    if n not in (VR, VL):
        return
    g = o.get("_chipgrid") or _sim_pixels.object_chip_grid(o)
    chips = o.get("chips", ())
    nx, ny, nz = g["nx"], g["ny"], g["nz"]
    cw, cd, ch = g["cw"], g["cd"], g["ch"]
    kind = d["kind"]
    _rect = d.get("rect")
    if _rect is not None:
        u0, u1, v0, v1 = _rect
    elif kind == "door":
        u0, u1, v0, v1 = 0.20, 0.80, 0.0, 0.65
    elif kind == "window":
        u0, u1, v0, v1 = 0.15, 0.85, 0.38, 0.82
    elif kind == "band":
        u0, u1, v0, v1 = 0.04, 0.96, 0.14, 0.90
    elif kind == "panel":
        u0, u1, v0, v1 = 0.04, 0.97, 0.08, 0.97
    else:
        u0, u1, v0, v1 = 0.25, 0.75, 0.20, 0.60
    beam = shade(BASE_COLORS["wood_dark"], n)
    night = clamp((0.6 - G.LIGHT["amb"]) / 0.35, 0.0, 1.0)
    _hl = o.get("house")
    _lit = _hl is None or _hl not in LIGHTS_OFF
    _fire = _hl is not None and _hl in HOUSE_BURNING
    glass = (255, int(196 + 30 * night), int(120 + 40 * night))
    if not _lit:
        glass = (54, 60, 66)
    firec = (255, int(140 + 40 * night), int(50 + 30 * night))
    if n[0] != 0:
        along = "y"
        nn = ny
        plane = o["x"] + o["w"] if n[0] == 1 else o["x"]
        fixed = nx - 1 if n[0] == 1 else 0
    else:
        along = "x"
        nn = nx
        plane = o["y"] + o["d"] if n[1] == 1 else o["y"]
        fixed = ny - 1 if n[1] == 1 else 0
    du, dv = 1.0 / nn, 1.0 / nz
    vm = (v0 + v1) / 2
    shut = d.get("shut", False) and kind == "window"

    def proj(x, y, z):
        xr, yr = cam.rotate_point(x, y)
        return cam.iso_project(xr, yr, z)

    for j in range(nn):
        for k in range(nz):
            u, v = (j + 0.5) * du, (k + 0.5) * dv
            in_rect = (u0 <= u <= u1 and v0 <= v <= v1)
            is_shut = (shut and v0 <= v <= v1
                       and ((u < u0 and u >= u0 - 1.6 * du)
                            or (u > u1 and u <= u1 + 1.6 * du)))
            if not (in_rect or is_shut):
                continue
            key = (fixed, j, k) if along == "y" else (j, fixed, k)
            if key in chips:
                continue
            if along == "y":
                y0, y1 = o["y"] + j * cd, o["y"] + (j + 1) * cd
                z0, z1 = o["z"] + k * ch, o["z"] + (k + 1) * ch
                q = [proj(plane, y0, z1), proj(plane, y1, z1),
                     proj(plane, y1, z0), proj(plane, y0, z0)]
            else:
                x0, x1 = o["x"] + j * cw, o["x"] + (j + 1) * cw
                z0, z1 = o["z"] + k * ch, o["z"] + (k + 1) * ch
                q = [proj(x0, plane, z1), proj(x1, plane, z1),
                     proj(x1, plane, z0), proj(x0, plane, z0)]
            if is_shut:  # ставни: тёмные доски с пазом
                pygame.draw.polygon(window, beam, q)
                pygame.draw.line(window, tone(beam, 0.55),
                                 quad_pt(q, 0.5, 0.05),
                                 quad_pt(q, 0.5, 0.95), 1)
                continue
            _u_edge = kind != "firebox" and (u - du / 2 <= u0
                                                  or u + du / 2 >= u1)
            if d.get("frame", True) and (_u_edge or v - dv / 2 <= v0
                                         or v + dv / 2 >= v1):
                pygame.draw.polygon(window, beam, q)
                continue
            if kind == "door":
                pygame.draw.polygon(window, tone(beam, 0.55), q)
                for s in (0.36, 0.52, 0.68):
                    if j * du < s <= (j + 1) * du:
                        t = (s - j * du) / du
                        pygame.draw.line(window, tone(beam, 0.35),
                                         quad_pt(q, t, 0), quad_pt(q, t, 1), 1)
                if (j * du < 0.62 <= (j + 1) * du
                        and k * dv < 0.42 <= (k + 1) * dv):
                    kx, ky = quad_pt(q, (0.62 - j * du) / du,
                                     1 - (0.42 - k * dv) / dv)
                    pygame.draw.rect(window, (255, 220, 150),
                                     (int(kx), int(ky), 1, 1))
            elif kind in ("band", "panel"):  # стекло-лента / решётка панельки
                is_glass = (kind == "band"
                            or ((j % 3) in (1, 2) and (k % 3) == 1))
                if not is_glass:
                    continue
                lit_w = (night > 0.3 and _lit
                         and hash01(j * 7 + 3, k * 13 + (_hl or 0), 5)
                         < 0.55 + 0.2 * night)
                if lit_w:
                    pygame.draw.polygon(window, glass, q)
                    if night > 0.45:
                        _glow_quad(window, q, (255, 190, 110),
                                   int(70 * night))
                else:
                    col_w = (46, 56, 70) if night < 0.3 else (40, 48, 60)
                    pygame.draw.polygon(window, col_w, q)
                if _fire:
                    _glow_quad(window, q, (255, 145, 40),
                               int(120 + 60 * night))
            elif kind == "window":
                pygame.draw.polygon(window, glass, q)
                if night > 0.45 and _lit:  # ореол света ночью
                    _glow_quad(window, q, (255, 190, 110),
                               int(90 * night))
                if _fire:  # за окном бушует пожар
                    _glow_quad(window, q, (255, 145, 40),
                               int(120 + 60 * night))
                if j * du < 0.5 <= (j + 1) * du:
                    t = (0.5 - j * du) / du
                    pygame.draw.line(window, beam, quad_pt(q, t, 0),
                                     quad_pt(q, t, 1), 1)
                if k * dv < vm <= (k + 1) * dv:
                    t = 1 - (vm - k * dv) / dv
                    pygame.draw.line(window, beam, quad_pt(q, 0, t),
                                     quad_pt(q, 1, t), 1)
            else:
                pygame.draw.polygon(window, firec, q)
                if night > 0.45:
                    _glow_quad(window, q, (255, 150, 70),
                               int(90 * night))


def _rot_normal(nx, ny, rot):
    if rot == 0:
        return nx, ny
    if rot == 1:
        return -ny, nx
    if rot == 2:
        return -nx, -ny
    return ny, -nx


def draw_cylinder(window, cam, x, y, z, w, d, h, base, seed, preset_idx):
    cx, cy = cam.world_to_screen(x + w / 2, y + d / 2, z + h)
    rw = (w + d) / 2
    rx = (TILE_W / 2) * (rw / 2) * cam.zoom / G.PIXEL
    ry = (TILE_H / 2) * (rw / 2) * cam.zoom / G.PIXEL
    h_px = h * TILE_Z * cam.zoom / G.PIXEL
    n = 8
    top_pts, bot_pts = [], []
    for i in range(n):
        a = math.pi * 2 * i / n
        px = cx + rx * math.cos(a)
        py = cy + ry * math.sin(a)
        top_pts.append((px, py))
        bot_pts.append((px, py + h_px))

    for i in range(n):
        j = (i + 1) % n
        ai = math.pi * 2 * i / n
        aj = math.pi * 2 * j / n
        mid = (ai + aj) / 2
        if (math.sin(ai) + math.sin(aj)) / 2 > -0.05:
            wx, wy = _rot_normal(math.cos(mid), math.sin(mid), cam.rot)
            dd = max(0.0, wx * G.SUN[0] + wy * G.SUN[1])
            f = G.LIGHT["amb"] + G.LIGHT["dif"] * dd
            col = (clamp(int(base[0] * f), 0, 255),
                   clamp(int(base[1] * f), 0, 255),
                   clamp(int(base[2] * f), 0, 255))
            quad = [top_pts[i], top_pts[j], bot_pts[j], bot_pts[i]]
            pygame.draw.polygon(window, col, quad)
            face_texels(window, cam, quad, (wx, wy, 0.0), base,
                        seed + i * 31, preset_idx, math.pi * rw / 8, h)
    pygame.draw.polygon(window, shade(base, PZ), top_pts)
    tq = [top_pts[6], top_pts[0], top_pts[2], top_pts[4]]
    face_texels(window, cam, tq, PZ, base, seed + 777, preset_idx, rw, rw)


def draw_pixel(window, cam, p, ctx=None):
    if ctx is None:
        ctx = _proj_ctx(cam)
    px, py = _proj_pt(ctx, p["x"], p["y"], p["z"])
    zc = max(cam.zoom, 0.75)
    if p.get("kind") == "fib":
        ln = p["size"] * zc / G.PIXEL * p.get("fade", 1.0)
        ca, sa = math.cos(p["ang"]), math.sin(p["ang"])
        x1, y1 = px - ca * ln / 2, py - sa * ln / 2
        x2, y2 = px + ca * ln / 2, py + sa * ln / 2
        if -4 <= x1 < cam.win_w + 4 or -4 <= x2 < cam.win_w + 4:
            pygame.draw.line(window, p["color"], (x1, y1), (x2, y2), 1)
        return
    if p.get("kind") == "sh":
        fade = p.get("fade", 1.0)
        if p.get("face") is not None:
            (ax, ay, az), (bx, by, bz) = p["face"]
            ex = _proj_pt(ctx, p["x"] + ax, p["y"] + ay, p["z"] + az)
            ez = _proj_pt(ctx, p["x"] + bx, p["y"] + by, p["z"] + bz)
            ex = (ex[0] - px, ex[1] - py)
            ez = (ez[0] - px, ez[1] - py)
            ca, sa = math.cos(p["ang"]), math.sin(p["ang"])
            pts = []
            for su, sv in p["fverts"]:
                uu, vv = su * fade, sv * fade
                wx = ex[0] * uu + ez[0] * vv
                wy = ex[1] * uu + ez[1] * vv
                pts.append((px + wx * ca - wy * sa,
                            py + wx * sa + wy * ca))
            if any(-8 <= q[0] < cam.win_w + 8
                   and -8 <= q[1] < cam.win_h + 8 for q in pts):
                pygame.draw.polygon(window, p["color"], pts)
                if fade > 0.85:
                    pygame.draw.line(window, tone(p["color"], 1.35),
                                     pts[0], pts[1], 1)
            return
        sc = zc / G.PIXEL * fade
        ca, sa = math.cos(p["ang"]), math.sin(p["ang"])
        pts = [(px + (vx * ca - vy * sa) * sc,
                py + (vx * sa + vy * ca) * sc) for vx, vy in p["verts"]]
        if any(-8 <= q[0] < cam.win_w + 8 and -8 <= q[1] < cam.win_h + 8
               for q in pts):
            pygame.draw.polygon(window, p["color"], pts)
            if fade > 0.85 and len(pts) >= 2:
                pygame.draw.line(window, tone(p["color"], 1.35),
                                 pts[0], pts[1], 1)
        return
    s = max(1, int(round(p["size"] * zc / G.PIXEL * p.get("fade", 1.0))))
    ix, iy = int(px - s / 2), int(py - s / 2)
    if -4 <= ix < cam.win_w + 4 and -4 <= iy < cam.win_h + 4:
        pygame.draw.rect(window, p["color"], (ix, iy, s, s))
        if s >= 4:  # крупные куски: свет сверху, тень снизу
            r, g, b = p["color"]
            pygame.draw.rect(window, (min(255, r + 45), min(255, g + 45),
                                         min(255, b + 45)), (ix, iy, s, 1))
            pygame.draw.rect(window, (r * 3 // 5, g * 3 // 5, b * 3 // 5),
                             (ix, iy + s - 1, s, 1))


def _pit_edge(pts, C, dx, dy):
    """Ребро квада, наиболее развёрнутое к направлению (dx, dy)."""
    best, be = -1e9, (pts[0], pts[1])
    for i in range(4):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % 4]
        ex, ey = x2 - x1, y2 - y1
        L = math.hypot(ex, ey) or 1.0
        nx, ny = -ey / L, ex / L
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if (mx - C[0]) * nx + (my - C[1]) * ny < 0:
            nx, ny = -nx, -ny
        sc = nx * dx + ny * dy
        if sc > best:
            best, be = sc, ((x1, y1), (x2, y2))
    return be


def _draw_pit(window, q, base_lit, v, seed):
    """Выбоина-впадина: рваные края, устье, дно и стенки по свету."""
    C = (sum(p[0] for p in q) / 4, sum(p[1] for p in q) / 4)
    e0 = max(2.0, math.hypot(q[1][0] - q[0][0], q[1][1] - q[0][1]))
    e1 = max(2.0, math.hypot(q[3][0] - q[0][0], q[3][1] - q[0][1]))
    jq = []
    for k, (x, y) in enumerate(q):
        fr = 0.80 + 0.40 * hash01(seed, k * 2 + 1, 31)
        jx = (hash01(seed, k * 2 + 2, 47) - 0.5) * e0 * 0.22
        jy = (hash01(seed, k * 2 + 3, 53) - 0.5) * e1 * 0.22
        jq.append((C[0] + (x - C[0]) * fr + jx,
                   C[1] + (y - C[1]) * fr + jy))
    q = jq
    if hash01(seed, 7, 77) < 0.25:
        halo = [(C[0] + (x - C[0]) * 1.15, C[1] + (y - C[1]) * 1.15)
                for x, y in q]
        pygame.draw.polygon(window, tone(base_lit, 0.55), halo)
        in1 = [(C[0] + (x - C[0]) * 0.80, C[1] + (y - C[1]) * 0.80)
               for x, y in q]
        pygame.draw.polygon(window, tone(base_lit, 0.45), in1)
        return
    hs = 1.12 + 0.14 * hash01(seed, 9, 91)
    halo = [(C[0] + (x - C[0]) * hs, C[1] + (y - C[1]) * hs)
            for x, y in q]
    pygame.draw.polygon(window, tone(base_lit, 0.55), halo)
    ms = 0.76 + 0.12 * hash01(seed, 10, 92)
    in1 = [(C[0] + (x - C[0]) * ms, C[1] + (y - C[1]) * ms)
           for x, y in q]
    pygame.draw.polygon(window, tone(base_lit, v), in1)
    sunx, suny = G.SUN_SX, G.SUN_SY
    cell = max(2.0, math.hypot(q[1][0] - q[0][0], q[1][1] - q[0][1]))
    sh = min(3.0, cell * 0.15)
    Cb = (C[0] + sunx * sh, C[1] + suny * sh)
    bs = 0.44 + 0.16 * hash01(seed, 11, 93)
    bot = [(Cb[0] + (x - Cb[0]) * bs, Cb[1] + (y - Cb[1]) * bs)
           for x, y in q]
    pygame.draw.polygon(window, tone(base_lit, 0.07), bot)
    (ax, ay), (bx, by) = _pit_edge(q, C, -sunx, -suny)
    pygame.draw.polygon(window, tone(base_lit, 1.30),
                        [(ax, ay), (bx, by),
                         (C[0] + (bx - C[0]) * 0.5,
                          C[1] + (by - C[1]) * 0.5),
                         (C[0] + (ax - C[0]) * 0.5,
                          C[1] + (ay - C[1]) * 0.5)])
    (cx_, cy_), (dx_, dy_) = _pit_edge(q, C, sunx, suny)
    pygame.draw.polygon(window, tone(base_lit, 0.38),
                        [(cx_, cy_), (dx_, dy_),
                         (C[0] + (dx_ - C[0]) * 0.5,
                          C[1] + (dy_ - C[1]) * 0.5),
                         (C[0] + (cx_ - C[0]) * 0.5,
                          C[1] + (cy_ - C[1]) * 0.5)])
    pygame.draw.line(window, tone(base_lit, 1.45), (ax, ay), (bx, by), 1)


def draw_chip_notches(window, cam, o):
    """Выбоины как ВПАДИНЫ: устье с глубиной, дно и стенки на свету."""
    chips = o.get("chips")
    g = o.get("_chipgrid")
    if not chips or g is None:
        return
    base = BASE_COLORS[o["color"]]
    VR, VL = RIGHT_N[cam.rot], LEFT_N[cam.rot]
    nx, ny, nz = g["nx"], g["ny"], g["nz"]
    cw, cd, ch = g["cw"], g["cd"], g["ch"]
    # соль от координат: id() прыгал между прогонами, рендер терял повторяемость
    osalt = abs(int(o["x"] * 431 + o["y"] * 1021 + o["z"] * 67
                  + o["w"] * 131 + o["h"] * 53)) % 10007

    def proj(x, y, z):
        xr, yr = cam.rotate_point(x, y)
        return cam.iso_project(xr, yr, z)

    for key in chips:
        c = g["idx"].get(key)
        if c is None:
            continue
        ix, iy, iz = key
        cx, cy, cz = c[3], c[4], c[5]
        v = 0.18 + 0.06 * hash01(ix * 3 + 1, iy * 5 + iz, 9)
        if iz == nz - 1:  # верхняя грань
            x0, x1 = cx - cw / 2, cx + cw / 2
            y0, y1 = cy - cd / 2, cy + cd / 2
            z = o["z"] + o["h"]
            q = [proj(x0, y0, z), proj(x1, y0, z),
                 proj(x1, y1, z), proj(x0, y1, z)]
            _draw_pit(window, q, shade(base, PZ), v,
                      osalt * 100003 + ix * 131 + iy * 17 + iz * 13 + 1)
        sides = [((1, 0, 0), ix == nx - 1, o["x"] + o["w"], True),
                 ((-1, 0, 0), ix == 0, o["x"], True),
                 ((0, 1, 0), iy == ny - 1, o["y"] + o["d"], False),
                 ((0, -1, 0), iy == 0, o["y"], False)]
        for n, on_face, plane, along_y in sides:
            if not on_face or n not in (VR, VL):
                continue
            z0, z1 = cz - ch / 2, cz + ch / 2
            if along_y:
                y0, y1 = cy - cd / 2, cy + cd / 2
                q = [proj(plane, y0, z1), proj(plane, y1, z1),
                     proj(plane, y1, z0), proj(plane, y0, z0)]
            else:
                x0, x1 = cx - cw / 2, cx + cw / 2
                q = [proj(x0, plane, z1), proj(x1, plane, z1),
                     proj(x1, plane, z0), proj(x0, plane, z0)]
            salt = 2 if n[0] == 1 else (3 if n[0] == -1 else (5 if n[1] == 1 else 7))
            _draw_pit(window, q, shade(base, n), v,
                      osalt * 100003 + ix * 131 + iy * 17 + iz * 13 + salt)


# Циклические ссылки на модули выше по цепочке: импорт в конце файла,
# имена используются только внутри функций.
from game.sim import pixels as _sim_pixels  # noqa: E402
