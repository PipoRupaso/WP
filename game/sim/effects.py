# -*- coding: utf-8 -*-
"""Ветер и визуальные эффекты (вспышки, кольца, дым, искры)."""

import math
import pygame
from game.core import state as G
from game.core.config import (
    GRAVITY, SP, TILE_W)
from game.core.utils import (
    clamp, hash01)
from game.world.world_state import (
    DUST, FLAMES, FLASHES, RINGS, SMOKES, SPARKS, WIND, wind_rng)

def update_wind(dt):
    """Ветер: порывы сильнее/слабее + смена направления. Детерминирован."""
    G.ANIM_T += dt
    W = WIND
    W["t"] += dt
    if W["t"] >= W["next"]:
        W["t"] = 0.0
        W["next"] = wind_rng.uniform(9.0, 22.0)
        r = wind_rng.random()
        if r < 0.20:  # штиль
            W["t_str"] = wind_rng.uniform(0.03, 0.15)
        elif r < 0.75:  # обычный
            W["t_str"] = wind_rng.uniform(0.25, 0.65)
        else:  # порыв
            W["t_str"] = wind_rng.uniform(0.9, 1.5)
        W["t_ang"] += wind_rng.uniform(-1.2, 1.2)
        if wind_rng.random() < 0.15:
            W["t_ang"] += wind_rng.uniform(-2.0, 2.0)
    k = 1.0 - math.exp(-dt * 0.7)
    W["str"] += (W["t_str"] - W["str"]) * k
    da = (W["t_ang"] - W["ang"] + math.pi) % (2 * math.pi) - math.pi
    W["ang"] += da * k
    W["kick"] *= math.exp(-dt * 1.4)
    fl = (1.0 + 0.22 * math.sin(G.ANIM_T * 2.3)
          + 0.13 * math.sin(G.ANIM_T * 5.1 + 1.0))
    mag = max(0.0, (W["str"] + W["kick"]) * fl)
    W["wx"] = math.cos(W["ang"]) * mag * 2.4  # сила 1.0 ~= 2.4 кл/с
    W["wy"] = math.sin(W["ang"]) * mag * 2.4
    W["mag"] = mag
    G.CLOUD_OFF += (W["wx"] - W["wy"]) * dt * 9.0


def update_fx(dt, frame):
    G.TRAUMA = max(0.0, G.TRAUMA - 1.8 * dt)
    for lst in (FLASHES, RINGS, SMOKES, SPARKS, FLAMES, DUST):
        for e in lst:
            e["t"] += dt
    for s in SMOKES:
        s["z"] += s.get("rise", 1.1) * dt
        s["x"] += (0.30 + WIND["wx"]) * dt
        s["y"] += WIND["wy"] * dt
    for s in DUST:
        s["z"] += 0.35 * dt
        s["x"] += (0.10 + WIND["wx"] * 0.35) * dt
        s["y"] += WIND["wy"] * 0.35 * dt
    for f in FLAMES:
        f["z"] += 0.25 * dt
    for s in SPARKS:
        s["vz"] -= GRAVITY * dt
        s["vx"] += WIND["wx"] * 0.4 * dt
        s["vy"] += WIND["wy"] * 0.4 * dt
        s["x"] += s["vx"] * dt
        s["y"] += s["vy"] * dt
        s["z"] += s["vz"] * dt
    for lst in (FLASHES, RINGS, SMOKES, SPARKS, FLAMES, DUST):
        lst[:] = [e for e in lst if e["t"] < e["life"]]


def draw_fx(window, cam):
    night = clamp((0.6 - G.LIGHT["amb"]) / 0.35, 0.0, 1.0)
    _c0 = cam.world_to_screen(20, 20, 1)
    _c1 = cam.world_to_screen(20 + WIND["wx"], 20 + WIND["wy"], 1)
    fwx, fwy = _c1[0] - _c0[0], _c1[1] - _c0[1]
    _l = math.hypot(fwx, fwy)
    if _l > 1e-6:
        fwx, fwy = fwx / _l, fwy / _l
    else:
        fwx, fwy = 0.7, 0.7
    _gust = min(1.4, WIND["mag"] + WIND.get("kick", 0.0) * 0.8)

    def _fireball(px, py, R, k, ph):
        # огненный шар: белый центр -> жёлто-оранжевый -> тёмные головни
        a = clamp(1 - k, 0.0, 1.0)
        if k < 0.25:
            col = (255, 252, 235)
        elif k < 0.55:
            col = (255, 204, 92)
        elif k < 0.8:
            col = (238, 118, 32)
        else:
            col = (86, 54, 40)
        grow = 1 - (1 - min(1.0, k * 1.6)) ** 2
        rr = max(2.0, R * (0.25 + 0.75 * grow))
        sz = int(rr * 2.6) + 6
        if sz < 6:
            return
        s = pygame.Surface((sz, sz), pygame.SRCALPHA)
        cc = sz // 2
        al = int(210 * a)
        for i in range(7):  # рваные лепестки по периметру
            ang = ph + i * (math.pi * 2 / 7)
            j = hash01(i * 7 + 3, int(ph * 60.0) + i, 5)
            rad = rr * (0.62 + 0.38 * j)
            ox, oy = math.cos(ang) * rr * 0.42, math.sin(ang) * rr * 0.42
            pygame.draw.circle(s, col + (al,), (int(cc + ox), int(cc + oy)),
                               max(1, int(rad)))
        pygame.draw.circle(s, col + (int(230 * a),), (cc, cc), int(rr))
        if k < 0.35:
            ic = (255, 255, 246)
        elif k < 0.6:
            ic = (255, 236, 180)
        else:
            ic = (252, 168, 74)
        pygame.draw.circle(s, ic + (int(240 * a),), (cc, cc),
                           max(1, int(rr * max(0.1, 0.55 - 0.3 * k))))
        window.blit(s, (int(px) - cc, int(py) - cc))

    for e in RINGS:
        k = e["t"] / e["life"]
        r = (20 + 340 * k) * e["power"] * cam.zoom / G.PIXEL
        a = int(170 * (1 - k))
        s = pygame.Surface((int(r * 2 + 4), int(r + 4)), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (255, 240, 220, a), s.get_rect(), SP(3))
        k2 = clamp(k * 1.3 - 0.12, 0.0, 1.0)  # вторая волна внутри
        r2 = (8 + 200 * k2) * e["power"] * cam.zoom / G.PIXEL
        a2 = int(120 * (1 - k2))
        pygame.draw.ellipse(s, (255, 250, 235, a2),
                            (int(r - r2) + 2, int(r / 2 - r2 / 2) + 2,
                             int(r2 * 2), int(r2)), SP(2))
        window.blit(s, (e["x"] - r - 2, e["y"] - r / 2 - 2))
    for e in DUST:  # лёгкая пыльца обломков
        k = e["t"] / e["life"]
        px, py = cam.world_to_screen(e["x"], e["y"], e["z"])
        r = int((e["r"] * (TILE_W / 2) + 10 * k) * cam.zoom / G.PIXEL)
        a = int(e["a"] * (1 - k))
        if r > 0:
            s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(s, e["c"] + (a,), (r + 1, r + 1), r)
            window.blit(s, (px - r - 1, py - r - 1))
    for e in SMOKES:  # пышный клуб дыма из четырёх под-кругов
        k = e["t"] / e["life"]
        px, py = cam.world_to_screen(e["x"], e["y"], e["z"])
        r = int((e["r"] * (TILE_W / 2) + 26 * k) * cam.zoom / G.PIXEL)
        a = int(e.get("a", 120) * (1 - k))
        if r > 1:
            col = e.get("c", G.LIGHT["smoke"])
            s = pygame.Surface((r * 4, int(r * 3.2)), pygame.SRCALPHA)
            cx0, cy0 = r * 2, r * 2
            for i, (dxx, dyy, sc) in enumerate(
                    ((-0.62, 0.10, 0.72), (0.58, 0.06, 0.78),
                     (0.0, -0.5, 0.85), (0.12, 0.28, 0.90))):
                j = hash01(i * 31 + 7, int(e["x"] * 37 + e["y"] * 91), 3)
                rr = r * sc * (0.85 + 0.3 * j)
                pygame.draw.circle(s, col + (a,),
                                   (int(cx0 + dxx * r), int(cy0 + dyy * r)),
                                   max(1, int(rr)))
            window.blit(s, (px - cx0, int(py - cy0)))
    for e in FLASHES:  # огненный шар + ночная вспышка на земле
        k = e["t"] / e["life"]
        R = (30 + 46 * e["power"]) * cam.zoom / G.PIXEL
        if night > 0.2:
            gr = int(R * 4.2)
            if gr > 3:
                s = pygame.Surface((gr * 2, gr), pygame.SRCALPHA)
                pygame.draw.ellipse(s, (255, 170, 70,
                                        int(70 * night * (1 - k))),
                                    s.get_rect())
                window.blit(s, (e["x"] - gr, e["y"] - gr / 2))
        _fireball(e["x"], e["y"], R, k, e.get("ph", 0.0))
    # огонь: четыре тлеющих яруса с трепетом, угли, ночной отсвет
    _LCRS = ((166, 44, 10, 150, 1.30, 0.30),
             (255, 96, 18, 190, 1.00, 0.55),
             (255, 166, 42, 220, 0.66, 0.80),
             (255, 236, 122, 235, 0.38, 1.05))
    for e in FLAMES:
        k = e["t"] / e["life"]
        px, py = cam.world_to_screen(e["x"], e["y"], e["z"])
        flick = (1 + 0.16 * math.sin(e["t"] * 43 + e["ph"])
                 + 0.07 * math.sin(e["t"] * 97 + e["ph"] * 2.3))
        flick *= 1 + 0.25 * WIND.get("kick", 0.0)  # порыв раздувает языки
        _fv = 0.78 + 0.55 * hash01(int(e["ph"] * 997) % 1000, 41, 9)
        r0 = e["s"] * _fv * (TILE_W / 2) * (0.75 + 0.5 * (1 - k)) * flick
        r = max(2.0, r0 * cam.zoom / G.PIXEL)
        _tv = 1.55 + 0.85 * hash01(int(e["ph"] * 881) % 1000, 43, 8)
        tall = r * (_tv + 0.30 * math.sin(e["t"] * 29 + e["ph"] * 1.7))
        tall *= 1 + 0.22 * WIND.get("kick", 0.0)
        _wl = fwx * (0.42 + 0.55 * _gust)
        lean = (_wl + 0.28 * math.sin(e["t"] * 21 + e["ph"])) * r
        if night > 0.25:  # пожар освещает землю в такт мерцанию языков
            gr = int(r * (1.4 + night) * flick)
            if gr > 2:
                s = pygame.Surface((gr * 2 + 2, gr + 4), pygame.SRCALPHA)
                pygame.draw.ellipse(s, (255, 140, 50,
                                        int(46 * night * flick)),
                                    s.get_rect())
                window.blit(s, (px - gr - 1, py - gr // 2))
        fade = (1 - k) * (0.4 + 0.6 * min(1.0, e["t"] / 0.08))
        for cr, cg, cb, ca, cs, yoff in _LCRS:
            rr = r * cs
            wide = 0.62 if cs > 0.5 else 0.55
            tip_y = py - tall * yoff + fwy * _gust * r * (yoff / _LCRS[-1][5]) * 0.5
            cx_i = px + lean * (yoff / _LCRS[-1][5])
            pts = [(cx_i, tip_y + rr * 0.9),
                   (cx_i - rr * wide, tip_y),
                   (cx_i + lean * 0.4, tip_y - rr * 1.15),
                   (cx_i + rr * wide, tip_y)]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            x0, y0 = min(xs) - 2, min(ys) - 2
            s = pygame.Surface((int(max(xs) - x0) + 4,
                                int(max(ys) - y0) + 4), pygame.SRCALPHA)
            pygame.draw.polygon(s, (cr, cg, cb, int(ca * fade)),
                                [(int(p[0] - x0) + 2, int(p[1] - y0) + 2)
                                 for p in pts])
            window.blit(s, (int(x0), int(y0)))
        if r > 4:  # ветряные угольки, танцующие над языками
            for i in range(2):
                t01 = (e["t"] * (2.2 + i * 0.7) + e["ph"] + i * 0.5) % 1.0
                ex = px + math.sin(t01 * 9 + e["ph"] * (3 + i)) * r * 0.45
                ey = py - tall * 0.6 - t01 * tall * 1.1
                ea = int(150 * (1 - t01) * flick * fade)
                if ea > 12:
                    pygame.draw.circle(window,
                                       (255, 170 + int(60 * (1 - t01)), 70),
                                       (int(ex), int(ey)), max(1, SP(2)))
    for e in SPARKS:  # искра: жёлтое сердце, оранжевый хвост, тёплый ореол
        px, py = cam.world_to_screen(e["x"], e["y"], e["z"])
        ox, oy = cam.world_to_screen(e["x"] - e["vx"] * 0.05,
                                     e["y"] - e["vy"] * 0.05,
                                     e["z"] - e["vz"] * 0.05)
        k = 1 - e["t"] / e["life"]
        pygame.draw.line(window, (255, int(140 + 80 * k), int(50 + 80 * k)),
                         (ox, oy), (px, py), SP(2) + 1)
        pygame.draw.line(window, (255, int(210 + 45 * k), 160),
                         (int(px - (px - ox) * 0.5),
                          int(py - (py - oy) * 0.5)), (px, py), SP(1))
        hr = max(1, int(2 * k + 1))
        s = pygame.Surface((hr * 4, hr * 4), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 220, 140, int(70 * k)),
                           (hr * 2, hr * 2), hr * 2)
        pygame.draw.circle(s, (255, 250, 230, int(220 * k)),
                           (hr * 2, hr * 2), hr)
        window.blit(s, (int(px) - hr * 2, int(py) - hr * 2))
