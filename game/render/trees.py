# -*- coding: utf-8 -*-
"""Ёлки: спрайты, качание, тени, вырванные деревья."""

import math
import pygame
from game.core import state as G
from game.core.config import (
    BASE_COLORS, DIRT_COLOR, GRASS, NY, PZ, TILE_H, TILE_W, TILE_Z)
from game.core.utils import (
    clamp)
from game.world.world_state import (
    FLYERS, WIND)
from game.render.lighting import (
    shade, tone)
from game.world.terrain import (
    ground_height_at)
from game.render.camera import (
    _proj_ctx, _proj_pt)
from game.render.objects import (
    OBJ_SPRITES)

def _occ_rects(cam, objects):
    """Спрайты фигур: прямоугольники + ключ живописи (раз на кадр)."""
    rects = []
    for o2 in objects:
        if o2.get("shape") == "tree":
            continue
        e = OBJ_SPRITES.get(id(o2))
        if e is None:
            continue
        ratio = cam.zoom / max(1e-6, e.get("zoom", cam.zoom))
        dx = e["minx"] * ratio + cam.win_w / 2 + cam.x + cam.shx
        dy = e["miny"] * ratio + cam.win_h / 2 + cam.y + cam.shy
        sw2 = e["surf"].get_width() * ratio
        sh2 = e["surf"].get_height() * ratio
        qx0, qy0, qwr, qdr = cam.rotated_footprint(o2["x"], o2["y"],
                                                   o2["w"], o2["d"])
        rects.append((dx + 3, dy + 3, dx + sw2 - 3, dy + sh2 - 3,
                      qx0 + qwr + qy0 + qdr))
    return rects


def _fir_occluded2(lx, ly, tkey, rects):
    for x0, y0, x1, y1, k in rects:
        if x0 <= lx < x1 and y0 <= ly < y1 and k > tkey + 0.01:
            return True
    return False


def _fir_shadowed(cam, lx, ly):
    """Ёлка в тени постройки? Точечная проба готового слоя теней."""
    shadow = G._SHADOW_ARR
    if shadow is None:
        return False
    offx, offy = G._STATIC_OFF
    scale = G._STATIC_SCALE
    ix = int((lx - offx) / scale)
    iy = int((ly - offy) / scale)
    sw, sh = shadow.get_size()
    if 0 <= ix < sw and 0 <= iy < sh:
        return shadow.get_at((ix, iy)).a > 40
    return False



def _mixc(a, b, k):
    return (int(a[0] + (b[0] - a[0]) * k),
            int(a[1] + (b[1] - a[1]) * k),
            int(a[2] + (b[2] - a[2]) * k))


def _fir_tones(o, fade, shadowed=False):
    base = BASE_COLORS[o["color"]]
    main = tone(shade(base, PZ), 1.0)
    side = tone(shade(base, NY), 0.82)
    lite = tone(shade(base, PZ), 1.22)
    dark = tone(shade(base, NY), 0.55)
    trunk_c = tone(shade(BASE_COLORS["wood_dark"], NY), 1.0)
    if fade < 1.0:
        gcol = tone(shade(GRASS, PZ), 0.9)
        k = 1.0 - fade
        main = _mixc(main, gcol, k)
        side = _mixc(side, gcol, k)
        lite = _mixc(lite, gcol, k)
        dark = _mixc(dark, gcol, k)
        trunk_c = _mixc(trunk_c, gcol, k)
    if shadowed:
        main = tone(main, 0.55)
        side = tone(side, 0.55)
        lite = tone(lite, 0.55)
        dark = tone(dark, 0.55)
        trunk_c = tone(trunk_c, 0.55)
    return main, side, lite, dark, trunk_c


def _draw_stump(window, o, sx, sy, S, shadowed=False):
    """Пенёк: короткий ствол с рваным светлым срезом."""
    trunk_c = tone(shade(BASE_COLORS["wood_dark"], NY), 1.0)
    lite = tone(shade(BASE_COLORS["wood_light"], PZ), 1.0)
    dark = tone(shade(BASE_COLORS["wood_dark"], NY), 0.55)
    if shadowed:
        trunk_c = tone(trunk_c, 0.55)
        lite = tone(lite, 0.55)
        dark = tone(dark, 0.55)
    if o.get("char"):
        trunk_c, lite, dark = (56, 47, 40), (74, 62, 52), (24, 21, 19)
    h = 2 + (int(o["x"] * 7 + o["y"] * 13) % 2)
    wdt = 2 if S >= 10 else 1
    bx = int(round(sx))
    by = int(round(sy))
    pygame.draw.ellipse(window, tone(shade(GRASS, PZ), 0.55),
                        (bx - 2, by - 1, 5, 2))
    pygame.draw.rect(window, trunk_c, (bx - wdt // 2, by - h, wdt, h))
    pygame.draw.rect(window, lite, (bx - wdt // 2, by - h, wdt, 1))
    pygame.draw.rect(window, dark, (bx - wdt // 2, by - 1, wdt, 1))



def _fir_row(r, Hc, T, maxW):
    """Ряд хвои: (ширина, вид) — 0 макушка, 1 ступень, 2 обычная."""
    if r == 0:
        return 1, 0
    tier = min(T - 1, int(r * T / Hc))
    prow = (r * T / Hc) - tier
    wfrac = (tier + 0.30 + 0.70 * prow) / T
    w = max(1, int(round(maxW * (0.16 + 0.84 * wfrac))))
    prev_tier = min(T - 1, int((r - 1) * T / Hc))
    if tier != prev_tier and tier > 0:
        return max(1, w - max(1, maxW // 6)), 1
    return w, 2


_FIR_SPR = {}
_FIR_WM = [1, 2, 3, 4, 3, 4, 5, 6, 5, 6, 7, 8, 9, 11, 13]  # ширины рядов хвои
_FIR_ZE = [0.0]  # текущий ze для hop-смещения


def _fir_sprite(cname, S, lean_ix=0.0, fade=1.0, shadowed=False, roots=False):
    """Кэшированная ёлка master 15x18: крупные пиксели при любом зуме."""
    fq = int(fade * 10 + 0.5)
    # грубый ключ света (1/8 суток): тон ёлок стабилен и не прыгает
    lkey = int(G.DAYT * 8) % 8
    key = (cname, int(round(S)), int(lean_ix * 2), fq, shadowed, roots, lkey)
    spr = _FIR_SPR.get(key)
    if spr is not None:
        return spr
    if len(_FIR_SPR) > 16384:
        _FIR_SPR.clear()
    o = dict(color=cname)
    main_, side, lite, dark, trunk_c = _fir_tones(o, fq / 10.0, shadowed)
    MW, MH = 15, 18
    m = pygame.Surface((MW, MH), pygame.SRCALPHA)
    for r, w in enumerate(_FIR_WM):
        sh = int(round(lean_ix * ((MH - 1 - r) / (MH - 1)) ** 1.5))
        x0 = (MW - w) // 2 + sh
        for j in range(w):
            if j == 0:
                c = lite
            elif j == w - 1:
                c = dark
            elif r % 5 == 4 or r == 14:
                c = side
            else:
                c = main_
            if 0 <= x0 + j < MW:
                m.set_at((x0 + j, r), c)
    for r in (15, 16, 17):  # ствол
        for j in (6, 7, 8):
            m.set_at((j, r), trunk_c)
    if roots:
        root_c = tone(shade(DIRT_COLOR, PZ), 0.9)
        if fq < 10:
            root_c = _mixc(root_c, tone(shade(GRASS, PZ), 0.9),
                           1.0 - fq / 10.0)
        for j in (4, 5, 9, 10):
            m.set_at((j, 17), root_c)
    th = max(4, int(round(S)))
    tw = max(3, int(round(th * MW / MH)))
    spr = pygame.transform.scale(m, (tw, th))
    _FIR_SPR[key] = spr
    return spr


def _render_fir_sprite(f, S, shadowed):
    """Ёлка-флаер в том же пиксель-стиле + корни для кувырка."""
    return _fir_sprite(f["color"], S, 0.0, f["fade"], shadowed, roots=True)


def _draw_flyer(window, cam, f, sx, sy, S):
    """Вырванная с корнем ёлка в полёте: тень на земле + кувырок."""
    ze = _FIR_ZE[0]
    gz = ground_height_at(f["x"], f["y"]) or 0.0
    sh_c = tone(shade(GRASS, PZ), 0.5)
    gx, gy = _proj_pt(_proj_ctx(cam), f["x"] + 0.5, f["y"] + 0.5, gz)
    hgt = max(0.0, f["z"] - gz)
    shr = max(3, int(S * 0.45 * (1.0 - 0.05 * hgt)))
    pygame.draw.ellipse(window, sh_c,
                        (int(gx - shr / 2), int(gy - shr / 6), shr,
                         max(2, shr // 4)))
    spr = _render_fir_sprite(f, S, _fir_shadowed(cam, sx, sy))
    spin = f.get("spin", 0.0)
    if abs(spin) > 0.01:
        spr = pygame.transform.rotozoom(spr, -math.degrees(spin), 1.0)
    if f.get("fade", 1.0) < 1.0:
        spr = spr.copy()
        spr.set_alpha(int(255 * f["fade"]))
    window.blit(spr, (int(sx - spr.get_width() / 2),
                      int(sy - spr.get_height() / 2)))



def _draw_mini_fir(window, o, sx, sy, S, wdx, wdy, mag01,
                   blox=0.0, bloy=0.0, fade=1.0, shadowed=False,
                   hop=0.0):
    """Ёлка из крупных пикселей: силуэт одинаков на любом зуме."""
    sh_c = tone(shade(GRASS, PZ), 0.55)
    bx = int(round(sx))
    base_y = int(round(sy))
    ze_ = (TILE_Z and _FIR_ZE[0]) or 0.0
    hop_k = max(0.0, min(1.4, hop))
    shw = max(4, int(S * 0.5 * (1.0 - 0.14 * hop_k)))  # тень под ёлкой
    pygame.draw.ellipse(window, sh_c,
                        (bx - shw // 2 + 1, base_y - 1,
                         shw, max(2, S // 7)))
    shake = o.get("shake", 0.0)
    if shake > 0.001:  # тяжёлая дрожь после удара (медленная, широкая)
        _wph = G.ANIM_T * 1.7 + o["phase"]
        _wA = shake * S * 0.15
        lean_x = (blox + wdx * _wA * math.sin(_wph)
                  + (-wdy) * 0.35 * _wA * math.sin(_wph * 1.31 + 1.0))
    else:
        lean_x = blox
    tw = max(3, int(round(S * 15 / 18)))
    # мягкое наклонение: вдали деревья почти прямые и стабильные,
    # сильный наклон — только вблизи при сильном ветре
    lean_ix = max(-4, min(4, int(round(lean_x * 4.5 / max(3.0, tw)))))
    spr = _fir_sprite(o["color"], S, lean_ix, fade, shadowed)
    hoppx = int(hop_k * TILE_Z * ze_)
    window.blit(spr, (bx - spr.get_width() // 2,
                      base_y - spr.get_height() + 2 - hoppx))


def _draw_fir_at(window, cam, o, preset_idx, ctx):
    """Одна ёлка в общей сортировке мира: люди и дома за ней
    рисуются раньше — объёмная иерархия работает корректно."""
    ze = ctx[3]
    sx, sy = _proj_pt(ctx, o["x"] + 0.5, o["y"] + 0.5, o["z"])
    S = max(12, int(round(1.65 * o.get("sz", 1.0) * TILE_Z * ze)))
    if (sx < -3 * S or sy < -S or sx > cam.win_w + 3 * S
            or sy > cam.win_h + S):
        return  # за кадром — culling
    shadowed = _fir_shadowed(cam, sx, sy)
    if o.get("dead"):
        if o["dead"] == "stump":
            _draw_stump(window, o, sx, sy, S, shadowed)
        return
    wrx, wry = cam.rotate_point(WIND.get("wx", 0.0), WIND.get("wy", 0.0))
    lx = (wrx - wry) * (TILE_W / 2) * ze
    ly = (wrx + wry) * (TILE_H / 2) * ze
    wl = math.hypot(lx, ly)
    wdx = lx / wl if wl > 1e-6 else 0.0
    wdy = ly / wl if wl > 1e-6 else 1.0
    mag01 = clamp(wl / 18.0, 0.0, 1.0)
    _FIR_ZE[0] = ze
    ox, oy = cam.rotate_point(o.get("lx", 0.0) + o.get("_spx", 0.0),
                              o.get("ly", 0.0) + o.get("_spy", 0.0))
    blox = (ox - oy) * (TILE_W / 2) * ze  # экранный сдвиг верхушки
    _draw_mini_fir(window, o, sx, sy, S, wdx, wdy, mag01,
                   blox=blox, fade=1.0, shadowed=shadowed,
                   hop=o.get("hop", 0.0))


def draw_fir_overlay(window, cam, objects, w, h):
    """Вырванные с корнем ёлки в полёте — поверх мира (они в воздухе)."""
    ctx = _proj_ctx(cam)
    ze = ctx[3]
    for f in FLYERS:
        sx, sy = _proj_pt(ctx, f["x"] + 0.5, f["y"] + 0.5, f["z"])
        S = max(12, int(round(1.65 * f.get("sz", 1.0) * TILE_Z * ze)))
        if (sx < -3 * S or sy < -3 * S or sx > cam.win_w + 3 * S
                or sy > cam.win_h + 3 * S):
            continue
        _draw_flyer(window, cam, f, sx, sy, S)
