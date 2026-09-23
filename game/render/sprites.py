# -*- coding: utf-8 -*-
"""Кэш спрайтов объектов, тропинки, сборка и порядок отрисовки."""

import pygame
from game.core import state as G
from game.core.config import (
    BASE_COLORS, STONE_MATS, WOOD_MATS, _BASE_ORDER)
from game.world.terrain import (
    ground_height_at)
from game.render.camera import (
    _box_bbox, _proj_ctx, _proj_pt)
from game.render.materials import (
    _draw_face_detail, _draw_timber_dressing, _draw_timber_eroded,
    draw_box_faces, draw_chip_notches, draw_cylinder, draw_gable,
    draw_pixel, draw_pyramid)
from game.render.objects import (
    OBJ_SPRITES, _SPRITE_BUDGET, _draw_eroded_box, _draw_wood_dressing,
    draw_rock)
from game.render.trees import (
    _draw_fir_at, _mixc)

_PATH_CACHE = {"key": None, "surf": None}


def _draw_village_paths(window, cam, wear):
    """Вытоптанные тропинки: пятна грунта там, где чаще всего ходили."""
    if not wear:
        return
    key = ((cam.win_w, cam.win_h), round(cam.zoom, 3), cam.rot,
           round(cam.x + cam.shx, 1), round(cam.y + cam.shy, 1),
           0 if G.VIL is None else G.VIL.get("wear_ver", 0))
    if _PATH_CACHE["key"] == key:
        window.blit(_PATH_CACHE["surf"], (0, 0))
        return
    ctx = _proj_ctx(cam)
    lay = pygame.Surface((cam.win_w, cam.win_h), pygame.SRCALPHA)
    cr, cg, cb = 148, 120, 79
    drawn = 0
    for (tx, ty), wv in wear.items():
        if wv < 1.1 or drawn > 600:
            continue
        pts = []
        ok = True
        for dx, dy in ((0, 0), (1, 0), (1, 1), (0, 1)):
            gz = ground_height_at(tx + dx + 0.5, ty + dy + 0.5)
            if gz is None:
                ok = False
                break
            pts.append(_proj_pt(ctx, tx + dx + 0.5, ty + dy + 0.5, gz))
        if not ok:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if (max(xs) < 0 or min(xs) > cam.win_w
                or max(ys) < 0 or min(ys) > cam.win_h):
            continue
        a = int(min(170, (wv - 1.0) * 22 + 24))
        c0 = (pts[0][0] + pts[2][0]) / 2
        c1 = (pts[0][1] + pts[2][1]) / 2

        def _sq(t):
            return [(c0 + (p[0] - c0) * t, c1 + (p[1] - c1) * t)
                    for p in pts]
        pygame.draw.polygon(lay, (cr, cg, cb, max(30, a - 60)), _sq(0.94))
        pygame.draw.polygon(lay, (cr - 18, cg - 18, cb - 18, a), _sq(0.62))
        drawn += 1
    if drawn:
        _PATH_CACHE["key"], _PATH_CACHE["surf"] = key, lay
        window.blit(lay, (0, 0))


def _render_object_sprite(cam, o, preset_idx):
    base = BASE_COLORS[o["color"]]
    if o.get("burn"):
        base = _mixc(base, (40, 34, 30),
                     0.75 * min(1.0, o["burn"] * 1.15))  # обугливание
    stone = o["color"] in STONE_MATS
    try:
        _ci = _BASE_ORDER.index(o["color"])
    except ValueError:
        _ci = 0
    # стабильный сид текстур (id() прыгал от запуска к запуску)
    idx = int(o["x"] * 12.7 + o["y"] * 57.3 + o["z"] * 101.1 + o["w"] * 3.1
              + o["d"] * 7.7 + o["h"] * 13.9 + _ci * 37.3) % 100000
    sx, sy, ssx, ssy = cam.x, cam.y, cam.shx, cam.shy
    win_w, win_h = cam.win_w, cam.win_h
    cam.x = cam.y = cam.shx = cam.shy = 0.0
    # Храним оффсет спрайта от начала проекции, а не от центра
    # текущего Surface. Так один спрайт годится и для холста, и для экрана.
    cam.update_win_size(0, 0)
    x, y, z, w, d, h = o["x"], o["y"], o["z"], o["w"], o["d"], o["h"]
    pts = [cam.world_to_screen(px, py, pz)
           for px in (x, x + w) for py in (y, y + d)
           for pz in (z, z + h)]
    pad = 4
    minx = int(min(p[0] for p in pts)) - pad
    miny = int(min(p[1] for p in pts)) - pad
    maxx = int(max(p[0] for p in pts)) + pad + 1
    maxy = int(max(p[1] for p in pts)) + pad + 1
    cam.x, cam.y = -minx, -miny
    surf = pygame.Surface((max(1, maxx - minx), max(1, maxy - miny)),
                          pygame.SRCALPHA)
    G._SPRITE_MODE = True
    try:
        if o["shape"] == "box" and o.get("chips"):
            _draw_eroded_box(surf, cam, o, base, preset_idx)
        elif o["shape"] == "box":
            draw_box_faces(surf, cam, x, y, z, w, d, h, base, idx,
                           stone, preset_idx, o.get("mat", "concrete"))
            if o.get("mat", "concrete") in WOOD_MATS:
                _draw_wood_dressing(surf, cam, o, base)
        elif o["shape"] == "gable" and o.get("chips"):
            _draw_eroded_box(surf, cam, o, base, preset_idx)
        elif o["shape"] == "gable":
            draw_gable(surf, cam, x, y, z, w, d, h, base, idx,
                       preset_idx, o.get("ends", "timber"))
        elif o["shape"] == "pyramid":
            draw_pyramid(surf, cam, x, y, z, w, d, h, base, idx,
                         stone, preset_idx)
        elif o["shape"] == "cylinder":
            draw_cylinder(surf, cam, x, y, z, w, d, h, base, idx,
                          preset_idx)
        elif o["shape"] == "rock":
            draw_rock(surf, cam, o, base, idx)
        if o.get("frame") and o["shape"] == "box":
            if o.get("chips"):
                _draw_timber_eroded(surf, cam, o)
            else:
                _draw_timber_dressing(surf, cam, o, False)
        if o.get("detail") and o["shape"] in ("box", "gable"):
            _draw_face_detail(surf, cam, o)
        if not (o["shape"] in ("box", "gable") and o.get("chips")):
            draw_chip_notches(surf, cam, o)
    finally:
        G._SPRITE_MODE = False
        cam.x, cam.y, cam.shx, cam.shy = sx, sy, ssx, ssy
        cam.update_win_size(win_w, win_h)
    return surf, minx, miny


def _blit_object(window, cam, o, preset_idx, ctx=None):
    x, y, z, w, d, h = o["x"], o["y"], o["z"], o["w"], o["d"], o["h"]
    if ctx is None:
        ctx = _proj_ctx(cam)
    x0, y0, x1, y1 = _box_bbox(ctx, x, y, z, w, d, h)
    if (x1 < -6 or x0 > cam.win_w + 6
            or y1 < -6 or y0 > cam.win_h + 6):
        return  # мимо камеры — даже не рендерим
    # ключ БЕЗ версии мира: взрыв перерисует только задетые спрайты
    # Zoom не инвалидирует дорогую векторную отрисовку: готовый
    # пиксельный спрайт масштабируется дешёвым nearest-neighbour.
    key = (preset_idx, cam.rot, o.get("over", 0),
           len(o.get("chips") or ()), round(o["x"], 3),
           round(o["y"], 3), round(o["z"], 3), round(o["w"], 3),
           round(o["d"], 3), round(o["h"], 3), o.get("color"),
           o.get("shape"), o.get("mat", "concrete"))
    e = OBJ_SPRITES.get(id(o))
    if e is None:
        surf, minx, miny = _render_object_sprite(cam, o, preset_idx)
        e = dict(key=key, surf=surf, minx=minx, miny=miny,
                 zoom=cam.zoom, scaled=None)
        OBJ_SPRITES[id(o)] = e
    elif e["key"] != key and _SPRITE_BUDGET[0] > 0:
        # устарел (сменился свет/повреждение): обновляем в рамках бюджета
        _SPRITE_BUDGET[0] -= 1
        surf, minx, miny = _render_object_sprite(cam, o, preset_idx)
        e = dict(key=key, surf=surf, minx=minx, miny=miny,
                 zoom=cam.zoom, scaled=None)
        OBJ_SPRITES[id(o)] = e
    ratio = cam.zoom / max(1e-6, e.get("zoom", cam.zoom))
    spr = e["surf"]
    if abs(ratio - 1.0) > 1e-5:
        scale_key = round(cam.zoom, 3)
        scaled = e.get("scaled")
        if scaled is None or scaled[0] != scale_key:
            sw0, sh0 = spr.get_size()
            spr = pygame.transform.scale(
                spr, (max(1, int(round(sw0 * ratio))),
                      max(1, int(round(sh0 * ratio)))))
            e["scaled"] = (scale_key, spr)
        else:
            spr = scaled[1]
    dx = e["minx"] * ratio + cam.win_w / 2 + cam.x + cam.shx
    dy = e["miny"] * ratio + cam.win_h / 2 + cam.y + cam.shy
    sw, sh = spr.get_size()
    if dx + sw < 0 or dy + sh < 0 or dx > cam.win_w or dy > cam.win_h:
        return
    window.blit(spr, (int(dx), int(dy)))


def prune_object_sprites(objects):
    alive = {id(o) for o in objects}
    for k in [k for k in OBJ_SPRITES if k not in alive]:
        del OBJ_SPRITES[k]


def _collect_render_items(cam, objects, pixels):
    """Отсечь и отсортировать видимые элементы один раз.

    Отдельная функция нужна фоновой сборке: она рисует уже правильно
    отсортированный список маленькими порциями в разных кадрах.
    """
    ctx = _proj_ctx(cam)
    rot = ctx[0]
    _w0, _h0 = cam.win_w, cam.win_h
    items = []
    for o in objects:
        x, y, z, w, d = o["x"], o["y"], o["z"], o["w"], o["d"]
        _pxc, _pyc = _proj_pt(ctx, x + w / 2, y + d / 2, z)
        if (_pxc < -90 or _pxc > _w0 + 90 or _pyc < -220
                or _pyc > _h0 + 90):
            continue  # мимо камеры — без сортировки и рендера
        # ключ сортировки — в мировых координатах; footprint при поворотах
        # кратно 90° считается напрямую (без rotate_point по 4 углам)
        # ёлка — по дальнему углу своей плитки (человек за ёлкой
        # рисуется раньше и правильно скрывается)
        _sm = False if o.get("shape") == "tree" else o.get("sort_min")
        if rot == 0:
            _k = x + y if _sm else x + w + y + d
        elif rot == 1:
            _k = ctx[2] - y - d + x if _sm else ctx[2] - y + x + w
        elif rot == 2:
            _k = (ctx[1] - x - w) + (ctx[2] - y - d) if _sm \
                else (ctx[1] - x) + (ctx[2] - y)
        else:
            _k = y + ctx[1] - x - w if _sm else y + d + ctx[1] - x
        items.append((_k, z, 0, o))
    for p in pixels:
        rx, ry = cam.rotate_point(p["x"], p["y"])
        items.append((rx + ry, p["z"], 1, p))
    items.sort(key=lambda t: (t[0], t[1], t[2]))
    return items


def _draw_render_items(window, cam, items, preset_idx):
    ctx = _proj_ctx(cam)
    for _, _, kind, payload in items:
        if kind == 0:
            if payload.get("shape") == "tree":
                _draw_fir_at(window, cam, payload, preset_idx, ctx)
            else:
                _blit_object(window, cam, payload, preset_idx, ctx)
        else:
            draw_pixel(window, cam, payload, ctx)


def draw_objects_and_pixels(window, cam, objects, pixels, preset_idx):
    prune_object_sprites(objects)
    _draw_render_items(window, cam,
                       _collect_render_items(cam, objects, pixels), preset_idx)
