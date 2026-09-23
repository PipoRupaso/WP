# -*- coding: utf-8 -*-
"""Отрисовка хижин, костра, свечения и всего поселения."""

import math
import pygame
from game.core import state as G
from game.core.config import (
    BASE_COLORS, DIRT_COLOR, GRASS, PZ, SP, TILE_W, TILE_Z)
from game.core.utils import (
    clamp, hash01)
from game.render.lighting import (
    shade, tone)
from game.render.camera import (
    _proj_ctx)
from game.village.core import (
    _vil_gz)
from game.village.people_draw import (
    _hum_pose, _hum_sprite)

def _draw_hut_a(window, cam, hx, hy, z0, prog, ctx):
    """Двускатный шалаш, конёк вдоль X. Этапы: 4 стойки, стены, крыша."""
    W, D = 1.5, 1.1

    def pt(x, y, z):
        return cam.world_to_screen(hx + x, hy + y, z0 + z)

    wood_d = BASE_COLORS["wood_dark"]
    wood_l = BASE_COLORS["plank_light"]
    straw = BASE_COLORS["straw"]
    # 0: утоптанная поляна (появляется с началом стройки)
    if prog > 0:
        pygame.draw.polygon(window, tone(shade(GRASS, PZ), 0.90),
                            [pt(0, 0, 0), pt(W, 0, 0), pt(W, D, 0), pt(0, D, 0)])
    # 1-4: стойки
    for i, (px, py) in enumerate(((0.05, 0.05), (W - 0.05, 0.05),
                                  (W - 0.05, D - 0.05), (0.05, D - 0.05))):
        if prog <= i:
            continue
        h = 0.5
        pygame.draw.polygon(window, shade(wood_d, (1, 0, 0)),
                            [pt(px + 0.03, py, 0), pt(px + 0.03, py + 0.06, 0),
                             pt(px + 0.03, py + 0.06, h),
                             pt(px + 0.03, py, h)])
        pygame.draw.polygon(window, shade(wood_d, (0, 1, 0)),
                            [pt(px, py + 0.06, 0), pt(px + 0.06, py + 0.06, 0),
                             pt(px + 0.06, py + 0.06, h),
                             pt(px, py + 0.06, h)])
    # 5-6: задняя стена (доски)
    if prog > 4:
        wall_t = 1.0 if prog > 5 else 0.55
        q = [pt(0, D - 0.02, 0), pt(W, D - 0.02, 0),
             pt(W, D - 0.02, 0.5 * wall_t), pt(0, D - 0.02, 0.5 * wall_t)]
        pygame.draw.polygon(window, shade(wood_l, (0, 1, 0)), q)
        for k in range(1, 4):
            t = 0.5 * wall_t * k / 4
            pygame.draw.line(window, tone(shade(wood_d, (0, 1, 0)), 0.6),
                             pt(0, D - 0.02, t), pt(W, D - 0.02, t), 1)
    # 7-8: передняя стена с проёмом
    if prog > 6:
        for xa, xb in ((0.0, 0.95), (1.15, W)):
            q = [pt(xa, 0.02, 0), pt(xb, 0.02, 0),
                 pt(xb, 0.02, 0.48), pt(xa, 0.02, 0.48)]
            pygame.draw.polygon(window, shade(wood_l, (0, -1, 0)), q)
            for k in range(1, 4):
                t = 0.48 * k / 4
                pygame.draw.line(window, tone(shade(wood_d, (0, -1, 0)), 0.6),
                                 pt(xa, 0.02, t), pt(xb, 0.02, t), 1)
        pygame.draw.polygon(window, tone(shade(wood_d, (0, 1, 0)), 0.35),
                            [pt(0.95, 0.02, 0), pt(1.15, 0.02, 0),
                             pt(1.15, 0.02, 0.48), pt(0.95, 0.02, 0.48)])
    # 9: крыша-щипец
    if prog > 8:
        r = 0.14
        zf, zt = 0.52, 0.86
        front = [pt(-r, -r, zf), pt(W + r, -r, zf),
                 pt(W + r, D / 2, zt), pt(-r, D / 2, zt)]
        back = [pt(-r, D + r, zf), pt(W + r, D + r, zf),
                pt(W + r, D / 2, zt), pt(-r, D / 2, zt)]
        pygame.draw.polygon(window, shade(straw, (0, 0.62, 0.79)), back)
        pygame.draw.polygon(window, shade(straw, (0, -0.62, 0.79)), front)
        for s, q in ((-1, front), (1, back)):
            pygame.draw.line(window, tone(shade(straw, (0, 0, 1)), 0.55),
                             q[0], q[1], 2)
        # торцы-фронтоны (плетёнка)
        for xe in (-r, W + r):
            pygame.draw.polygon(window, tone(shade(straw, (1, 0, 0)), 0.82),
                                [pt(xe, 0, 0.5), pt(xe, D, 0.5),
                                 pt(xe, D / 2, zt)])
        pygame.draw.line(window, tone(shade(straw, (0, 0, 1)), 1.2),
                         pt(-r, D / 2, zt), pt(W + r, D / 2, zt), 2)


def _draw_hut_c(window, cam, hx, hy, z0, prog, ctx):
    # Круглая хижина: колья, стена-цилиндр, конус соломы
    R, HC = 0.65, 0.46

    def pt(x, y, z):
        return cam.world_to_screen(hx + x, hy + y, z0 + z)

    wood_d = BASE_COLORS["wood_dark"]
    wood_l = BASE_COLORS["plank_light"]
    straw = BASE_COLORS["straw"]
    if prog > 0:  # утоптанная поляна
        c0 = pt(R, R, 0)
        rx = abs(pt(R * 2, R, 0)[0] - c0[0]) + 2
        ry = abs(pt(R, R * 2, 0)[1] - c0[1]) + 2
        pygame.draw.ellipse(window, tone(shade(GRASS, PZ), 0.90),
                            (c0[0] - rx, c0[1] - ry * 0.35, rx * 2,
                             ry * 0.7))
    # 1-4: колья-стойки в квадрантах
    for i, (px, py) in enumerate(((R * 0.7, R * 0.7), (R * 1.3, R * 0.7),
                                  (R * 1.3, R * 1.3), (R * 0.7, R * 1.3))):
        if prog <= i:
            continue
        pygame.draw.polygon(window, shade(wood_d, (1, 0, 0)),
                            [pt(px + 0.03, py, 0), pt(px + 0.03, py + 0.06, 0),
                             pt(px + 0.03, py + 0.06, HC),
                             pt(px + 0.03, py, HC)])
        pygame.draw.polygon(window, shade(wood_d, (0, 1, 0)),
                            [pt(px, py + 0.06, 0), pt(px + 0.06, py + 0.06, 0),
                             pt(px + 0.06, py + 0.06, HC),
                             pt(px, py + 0.06, HC)])
    # 5-6: стена-цилиндр (задняя дуга темнее, передняя светлее)
    if prog > 4:
        n = 12
        wfull = 1.0 if prog > 5 else 0.5
        for back in (True, False):
            bot, top = [], []
            for k in range(n + 1):
                a = math.pi * k / n + (math.pi if back else 0.0)
                bot.append(pt(R + R * math.cos(a), R + R * math.sin(a), 0))
                top.append(pt(R + R * math.cos(a), R + R * math.sin(a),
                              HC * wfull))
            col = (tone(shade(wood_l, (0, 1, 0)), 0.72) if back
                   else shade(wood_l, (0, -1, 0)))
            pygame.draw.polygon(window, col, bot + top[::-1])
        if prog > 5:  # швы досок
            for k3 in range(1, 3):
                zt = HC * k3 / 3
                for k2 in range(0, n + 1, 2):
                    a1 = math.pi * k2 / n
                    a2 = math.pi * (k2 + 1) / n
                    pygame.draw.line(window,
                                     tone(shade(wood_d, (0, -1, 0)), 0.65),
                                     pt(R + R * math.cos(a1),
                                        R + R * math.sin(a1), zt),
                                     pt(R + R * math.cos(a2),
                                        R + R * math.sin(a2), zt), 1)
    # 7-8: конус соломы
    if prog > 6:
        ht = HC + 0.42 * (1.0 if prog > 7 else 0.55)
        n = 12
        for back in (True, False):
            poly = []
            for k in range(n + 1):
                a = math.pi * k / n + (math.pi if back else 0.0)
                poly.append(pt(R + R * math.cos(a),
                               R + R * math.sin(a), HC))
            apex = pt(R, R, ht)
            poly.append(apex)
            poly.append(apex)
            pygame.draw.polygon(window,
                                tone(shade(straw, (0, 1, 0)), 0.78)
                                if back else shade(straw, (0, -1, 0)),
                                poly)
    # 9: дверь + дымарь
    if prog > 8:
        pygame.draw.polygon(window, tone(shade(wood_d, (0, -1, 0)), 0.4),
                            [pt(R - 0.14, R + 0.62, 0),
                             pt(R + 0.14, R + 0.62, 0),
                             pt(R + 0.14, R + 0.62, 0.34),
                             pt(R - 0.14, R + 0.62, 0.34)])
        p1 = pt(R, R, HC + 0.42)
        p2 = pt(R + 0.05, R + 0.05, HC + 0.62)
        pygame.draw.line(window, tone(shade(wood_d, (0, 1, 0)), 1.1),
                         p1, p2, 2)


def _draw_hut_b(window, cam, hx, hy, z0, prog):
    """Навес на стойках: односкатная крыша."""
    W, D = 1.4, 1.0
    wood_d = BASE_COLORS["wood_dark"]
    wood_l = BASE_COLORS["plank_light"]
    straw = BASE_COLORS["straw"]

    def pt(x, y, z):
        return cam.world_to_screen(hx + x, hy + y, z0 + z)

    if prog > 0:
        pygame.draw.polygon(window, tone(shade(GRASS, PZ), 0.90),
                            [pt(0, 0, 0), pt(W, 0, 0), pt(W, D, 0), pt(0, D, 0)])
    posts = ((0.05, D - 0.05, 0.62), (W - 0.05, D - 0.05, 0.62),
             (0.05, 0.05, 0.34), (W - 0.05, 0.05, 0.34))
    for i, (px, py, h) in enumerate(posts):
        if prog <= i:
            continue
        pygame.draw.polygon(window, shade(wood_d, (1, 0, 0)),
                            [pt(px + 0.03, py, 0), pt(px + 0.03, py + 0.06, 0),
                             pt(px + 0.03, py + 0.06, h),
                             pt(px + 0.03, py, h)])
        pygame.draw.polygon(window, shade(wood_d, (0, 1, 0)),
                            [pt(px, py + 0.06, 0), pt(px + 0.06, py + 0.06, 0),
                             pt(px + 0.06, py + 0.06, h),
                             pt(px, py + 0.06, h)])
    if prog > 4:
        q = [pt(0, D - 0.02, 0), pt(W, D - 0.02, 0),
             pt(W, D - 0.02, 0.6), pt(0, D - 0.02, 0.6)]
        pygame.draw.polygon(window, shade(wood_l, (0, 1, 0)), q)
        for k in range(1, 4):
            t = 0.6 * k / 4
            pygame.draw.line(window, tone(shade(wood_d, (0, 1, 0)), 0.6),
                             pt(0, D - 0.02, t), pt(W, D - 0.02, t), 1)
    if prog > 5:
        zf, zt = 0.32, 0.66
        front = [pt(-0.12, -0.12, zf), pt(W + 0.12, -0.12, zf),
                 pt(W + 0.12, D + 0.06, zt), pt(-0.12, D + 0.06, zt)]
        pygame.draw.polygon(window, shade(straw, (0, -0.55, 0.83)), front)
        pygame.draw.line(window, tone(shade(straw, (0, 0, 1)), 0.5),
                         front[0], front[1], 2)
        for xe in (-0.12, W + 0.12):
            pygame.draw.polygon(window, tone(shade(straw, (1, 0, 0)), 0.8),
                                [pt(xe, 0, zf), pt(xe, D, 0.62),
                                 pt(xe, D, 0.0)])
    if prog > 7:
        for xe in (0.35, 0.7, 1.05):
            pygame.draw.line(window, tone(shade(straw, (0, -0.55, 0.83)), 0.75),
                             pt(xe, -0.12, 0.32),
                             pt(xe, D + 0.06, 0.66), 1)


def _vil_draw_fire(window, cam, ctx):
    v = G.VIL
    fx, fy = v["fire"]
    z0 = _vil_gz(fx, fy)
    ze = ctx[3]
    # подкладка-земля
    r0 = (0.34 * (TILE_W / 2) * ze)
    c0 = cam.world_to_screen(fx, fy, z0)
    pygame.draw.ellipse(window, tone(shade(DIRT_COLOR, PZ), 0.80),
                        (c0[0] - r0, c0[1] - r0 / 2, r0 * 2, r0))
    # кольцо камней
    for i in range(6):
        if v["stones"] < 1 and v["fire_logs"] < 1 and not v["lit"]:
            return
        ang = i * 6.283 / 6 + 0.26
        if v["stones"] > 0 and i >= v["stones"] and not v["lit"]:
            continue
        sx, sy = fx + math.cos(ang) * 0.30, fy + math.sin(ang) * 0.30
        p = cam.world_to_screen(sx, sy, z0)
        rs = max(2, int(0.11 * (TILE_W / 2) * ze))
        pygame.draw.ellipse(window, shade(BASE_COLORS["gray"], (0, 1, 0.3)),
                            (p[0] - rs, p[1] - rs / 2, rs * 2, rs))
        pygame.draw.ellipse(window, shade(BASE_COLORS["gray"], (0, 0, 1)),
                            (p[0] - rs * 0.6, p[1] - rs * 0.75, rs * 1.2,
                             rs * 0.6))
    nightv = clamp((0.6 - G.LIGHT["amb"]) / 0.35, 0.0, 1.0)
    if nightv > 0.2 and v["lit"]:
        r = max(24, int(TILE_W / 2 * ze * 3.2))
        gl = _radial_glow(("fire", r), r, (255, 150, 50), 46)
        window.blit(gl, (int(c0[0] - r), int(c0[1] - r * 0.7)))
    wood = BASE_COLORS["wood_dark"]
    if v["fire_logs"] < 1 and v["stones"] < 6:
        for i in range(3):
            a = i * 2.1 + 0.4
            x1 = fx + math.cos(a) * 0.26
            y1 = fy + math.sin(a) * 0.26
            x2 = fx + math.cos(a + 1.1) * 0.20
            y2 = fy + math.sin(a + 1.1) * 0.20
            p1 = cam.world_to_screen(x1, y1, z0 + 0.015)
            p2 = cam.world_to_screen(x2, y2, z0 + 0.015)
            pygame.draw.line(window,
                             tone(shade(BASE_COLORS["wood_light"], PZ), 0.85),
                             p1, p2, max(1, SP(1)))
    # жерди-шалашик
    for i in range(max(0, min(4, v["fire_logs"]))):
        ang = i * 1.7 + 0.5
        x1 = fx + math.cos(ang) * 0.22
        y1 = fy + math.sin(ang) * 0.22
        x2 = fx + math.cos(ang + 2.4) * 0.20
        y2 = fy + math.sin(ang + 2.4) * 0.20
        p1 = cam.world_to_screen(x1, y1, z0 + 0.02)
        p2 = cam.world_to_screen(x2, y2, z0 + 0.02)
        pt = cam.world_to_screen((x1 + x2) * 0.5 + 0.02,
                                 (y1 + y2) * 0.5 - 0.02, z0 + 0.34)
        pygame.draw.line(window, tone(shade(wood, (0, 1, 0)), 0.9),
                         p1, pt, max(1, SP(2)))
        pygame.draw.line(window, tone(shade(wood, (1, 0, 0)), 0.8),
                         p2, pt, max(1, SP(2)))
    if not v["lit"]:
        return
    # пламя: четыре яруса, мерцание плавное (синусы, не случайный снег)
    flick = (1 + 0.14 * math.sin(G.VIL_T * 7.3) + 0.09 * math.sin(G.VIL_T * 17.7))
    _LCRS = ((166, 44, 10, 150, 1.30, 0.30),
             (255, 96, 18, 190, 1.00, 0.55),
             (255, 166, 42, 220, 0.66, 0.80),
             (255, 236, 122, 235, 0.38, 1.05))
    night = clamp((0.6 - G.LIGHT["amb"]) / 0.35, 0.0, 1.0)
    R = 0.16 * (TILE_W / 2) * ze * flick
    tall = R * 2.4
    for cr, cg, cb, ca, cs, yoff in _LCRS:
        rr = R * cs
        cx_ = c0[0] + 0.14 * R * math.sin(G.VIL_T * 3.1 + yoff * 5)
        tip_y = c0[1] - tall * yoff
        pts = [(cx_, tip_y + rr * 0.9), (cx_ - rr * 0.62, tip_y),
               (cx_ + rr * 0.62, tip_y)]
        pygame.draw.polygon(window, (cr, cg, cb), pts)
    if R > 3:
        pygame.draw.circle(window, (255, 250, 235),
                           (int(c0[0]), int(c0[1] - tall * 0.18)),
                           max(1, int(R * 0.3)))
    if night > 0.2:  # отсвет на земле
        gr = int(R * (2.2 + 2.4 * night) * flick)
        if gr > 3:
            s = pygame.Surface((gr * 2 + 2, gr + 4), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (255, 150, 50, int(60 * night * flick)),
                                s.get_rect())
            window.blit(s, (int(c0[0]) - gr - 1, int(c0[1]) - gr // 2))


_GLOW_C = {}


def _radial_glow(key, radius, color, alpha):
    surf = _GLOW_C.get(key)
    if surf is None:
        r = max(4, int(radius))
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for rr in range(r, 0, -2):
            a = int(alpha * (1.0 - rr / r) ** 1.6)
            pygame.draw.circle(surf, (color[0], color[1], color[2], a),
                               (r, r), rr)
        _GLOW_C[key] = surf
    return surf


def draw_village(window, cam, frame):
    """Поселение: жерди, костёр, хижины, люди (по глубине)."""
    v = G.VIL
    if v is None:
        return
    ctx = _proj_ctx(cam)
    ze = ctx[3]
    items = []
    for s in v["sticks"]:
        sx, sy = cam.world_to_screen(s["x"], s["y"], s["z"])
        if sx < -40 or sy < -40 or sx > cam.win_w + 40 or sy > cam.win_h + 40:
            continue
        items.append((s["x"] + s["y"], 0, ("stick", s, sx, sy)))
    for lg in v["logs"]:
        if not lg.get("placed") or lg.get("owner") is not None:
            continue
        sx, sy = cam.world_to_screen(lg["x"], lg["y"], lg["z"])
        if sx < -40 or sy < -40 or sx > cam.win_w + 40 \
                or sy > cam.win_h + 40:
            continue
        items.append((lg["x"] + lg["y"], 0, ("log", lg, sx, sy)))
    for sp in v.get("stones_placed", ()):
        sx, sy = cam.world_to_screen(sp["x"], sp["y"],
                                     _vil_gz(sp["x"], sp["y"]))
        if sx < -40 or sy < -40 or sx > cam.win_w + 40 \
                or sy > cam.win_h + 40:
            continue
        items.append((sp["x"] + sp["y"], 0, ("stonep", sp, sx, sy)))
    for s2 in v.get("pebbles", ()):
        if s2["owner"] is not None:
            continue
        sx, sy = cam.world_to_screen(s2["x"], s2["y"], s2["z"])
        if sx < -40 or sy < -40 or sx > cam.win_w + 40 \
                or sy > cam.win_h + 40:
            continue
        items.append((s2["x"] + s2["y"], 0, ("pebble", s2, sx, sy)))
    fx, fy = v["fire"]
    items.append((fx + fy, 0, ("fire", None, None, None)))
    # кровь: рисуем под всеми предметами
    for b in v["blood"]:
        bx, by = b["x"], b["y"]
        sx, sy = cam.world_to_screen(bx, by, _vil_gz(bx, by))
        if sx < -40 or sy < -40 or sx > cam.win_w + 40 or sy > cam.win_h + 40:
            continue
        gr = min(1.0, b["t"] * 2.0)
        fade = max(0.3, 1.0 - max(0.0, b["t"] - 45.0) / 45.0)
        rr = max(2, int(b["r"] * 30.0 * ze * (0.45 + 0.55 * gr)))
        col = (int(118 * fade), int(16 * fade), int(15 * fade))
        pygame.draw.ellipse(window, col,
                            (sx - rr, sy - rr // 3, rr * 2,
                             rr * 2 // 3 + 1))
        if b["big"]:
            for k in range(5):
                a2 = hash01(k, int(bx * 13), int(by * 13)) * 6.283
                d2 = rr * (0.8 + hash01(k, 7, 1) * 0.5)
                pygame.draw.ellipse(window, col,
                                    (sx + math.cos(a2) * d2 - rr // 4,
                                     sy + math.sin(a2) * d2 / 3 - rr // 8,
                                     rr // 2, rr // 4 + 1))
    for hum in v["workers"]:
        sx, sy = cam.world_to_screen(hum["x"], hum["y"], hum["z"])
        if sx < -60 or sy < -60 or sx > cam.win_w + 60 or sy > cam.win_h + 60:
            continue
        items.append((hum["x"] + hum["y"], 1, ("hum", hum, sx, sy)))
    items.sort(key=lambda t: t[0])
    night = clamp((0.6 - G.LIGHT["amb"]) / 0.35, 0.0, 1.0)
    for _, _, (kind, payload, sx, sy) in items:
        if kind == "stick":
            s = payload
            ze2 = ctx[3]
            dxw = math.cos(s["ang"]) * 0.22
            dyw = math.sin(s["ang"]) * 0.16
            p1 = cam.world_to_screen(s["x"], s["y"], s["z"] + 0.02)
            p2 = cam.world_to_screen(s["x"] + dxw, s["y"] + dyw, s["z"] + 0.05)
            if s["falling"]:
                shx, shy = cam.world_to_screen(s["x"], s["y"],
                                               _vil_gz(s["x"], s["y"]))
                pygame.draw.ellipse(window, tone(shade(GRASS, PZ), 0.5),
                                    (shx - 3, shy - 1, 6, 3))
            pygame.draw.line(window, tone(shade(BASE_COLORS["wood_dark"],
                                                PZ), 0.95),
                             p1, p2, max(1, SP(2) if ze2 > 0.5 else 1))
        elif kind == "log":
            lg = payload
            dxw = math.cos(lg.get("ang", 0.0)) * 0.26
            dyw = math.sin(lg.get("ang", 0.0)) * 0.18
            p1 = cam.world_to_screen(lg["x"] - dxw / 2,
                                     lg["y"] - dyw / 2, lg["z"] + 0.05)
            p2 = cam.world_to_screen(lg["x"] + dxw / 2,
                                     lg["y"] + dyw / 2, lg["z"] + 0.05)
            pygame.draw.line(window,
                             tone(shade(BASE_COLORS["wood_light"], PZ), 0.85),
                             p1, p2, max(2, SP(3) if ze > 0.5 else 2))
            pygame.draw.line(window,
                             tone(shade(BASE_COLORS["wood_dark"], PZ), 0.8),
                             (p1[0], p1[1] + 1), (p2[0], p2[1] + 1),
                             max(1, SP(1)))
        elif kind in ("stonep", "pebble"):
            sp = payload
            rr = max(2, int((0.09 if kind == "stonep" else 0.06)
                            * (TILE_W / 2) * ze))
            cc = shade(BASE_COLORS["gray"], (0, 1, 0.3))
            pygame.draw.ellipse(window, cc,
                                (sx - rr, sy - rr // 2, rr * 2, rr))
        elif kind == "fire":
            _vil_draw_fire(window, cam, ctx)
        else:
            hum = payload
            moving = hum["state"] in ("walk", "run")
            if moving:
                hum["ph"] += (9.0 if hum["carry"] or
                              math.hypot(hum["tx"] - hum["x"],
                                         hum["ty"] - hum["y"]) > 6
                              else 6.0) * (1 / 60.0)
            else:
                hum["ph"] += 1.6 / 60.0
            S = max(6, int(round(TILE_Z * ze * 0.55)))  # мелкие, детализированные
            spd = 2.3 if (hum["carry"] or
                          math.hypot(hum["tx"] - hum["x"],
                                     hum["ty"] - hum["y"]) > 6) else 1.5
            pose = _hum_pose(hum, moving, spd)
            spr = _hum_sprite(pose, hum, S, hum["flip"])
            if pose == "dead":
                window.blit(spr, (int(sx - spr.get_width() / 2),
                                  int(sy - spr.get_height() / 2)))
            else:
                shw = max(4, int(S * 0.4))
                pygame.draw.ellipse(window, tone(shade(GRASS, PZ), 0.55),
                                    (sx - shw // 2, sy - shw // 6, shw,
                                     max(2, shw // 3)))
                window.blit(spr, (int(sx - spr.get_width() / 2),
                                  int(sy - spr.get_height())))
            if pose == "light" and hum["state"] == "light":
                # искра у кончиков пальцев
                k = 0.5 + 0.5 * math.sin(G.VIL_T * 21)
                pygame.draw.circle(window, (255, 220 + int(35 * k), 120),
                                   (int(sx + spr.get_width() * 0.28),
                                    int(sy - spr.get_height() * 0.55)),
                                   max(1, S // 9))
            if hum.get("carry_log"):
                p1 = cam.world_to_screen(hum["x"] - 0.06, hum["y"] - 0.04,
                                        hum["z"] + 0.30)
                p2 = cam.world_to_screen(hum["x"] + 0.13, hum["y"] + 0.07,
                                        hum["z"] + 0.26)
                pygame.draw.line(window,
                                 tone(shade(BASE_COLORS["wood_light"], PZ),
                                      0.9), p1, p2, max(2, S // 6))
            if hum.get("carry_sp"):
                pygame.draw.circle(
                    window, shade(BASE_COLORS["gray"], (0, 1, 0.3)),
                    (int(sx + S * 0.16), int(sy - S * 0.35)),
                    max(1, S // 9))
            nightv = clamp((0.6 - G.LIGHT["amb"]) / 0.35, 0.0, 1.0)
            if hum.get("torch") and nightv > 0.25:
                fx2 = int(sx + S * 0.17)
                fy2 = int(sy - spr.get_height() * 0.52)
                pygame.draw.circle(window, (255, 190, 80), (fx2, fy2),
                                   max(1, S // 10))
                pygame.draw.circle(window, (255, 130, 45), (fx2, fy2 + 1),
                                   max(1, S // 14))
                gl = _radial_glow(("torch", S), S * 2, (255, 150, 50), 30)
                window.blit(gl, (fx2 - gl.get_width() // 2,
                                 fy2 - gl.get_height() // 2))
    if v["defeat"] is not None:
        f_big = pygame.font.Font(None, 54)
        f_sm = pygame.font.Font(None, 24)
        t1 = f_big.render("ПОРАЖЕНИЕ", True, (214, 58, 46))
        t2 = f_sm.render("Племя вымерло — R: новое поселение",
                         True, (240, 240, 244))
        window.blit(t1, (cam.win_w / 2 - t1.get_width() / 2,
                         cam.win_h * 0.28))
        window.blit(t2, (cam.win_w / 2 - t2.get_width() / 2,
                         cam.win_h * 0.28 + 46))
