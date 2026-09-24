# -*- coding: utf-8 -*-
"""Кэш спрайтов объектов, тропинки, сборка и порядок отрисовки."""

import pygame
from game.core import state as G
from game.core.config import (
    BASE_COLORS, STONE_MATS, WOOD_MATS, _BASE_ORDER)
from game.render.camera import (
    _box_bbox, _proj_ctx)
from game.render.materials import (
    _draw_face_detail, _draw_timber_dressing, _draw_timber_eroded,
    draw_box_faces, draw_chip_notches, draw_cylinder, draw_gable,
    draw_pixel, draw_pyramid)
from game.render.objects import (
    OBJ_SPRITES, _SPRITE_BUDGET, _draw_eroded_box, _draw_wood_dressing,
    draw_rock)
from game.render.trees import (
    _draw_fir_at, _mixc)
from game.render.depth import (
    collect_world)

# Циклические ссылки: поселение рисует себя само, импорт в конце файла.
from game.village import draw as _vdraw  # noqa: E402
from game.village import animals as _animals  # noqa: E402

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


def _collect_render_items(cam, objects, pixels, extras=()):
    """Отсечь и отсортировать видимые элементы один раз — вместе с
    людьми, зверями и предметами поселения (общая глубина мира)."""
    return collect_world(cam, objects, pixels, extras)


def _draw_render_items(window, cam, items, preset_idx):
    ctx = _proj_ctx(cam)
    for _it in items:
        payload = _it[3]
        tag = payload[0]
        if tag == "o":
            o = payload[1]
            if o.get("shape") == "tree":
                _draw_fir_at(window, cam, o, preset_idx, ctx)
            else:
                _blit_object(window, cam, o, preset_idx, ctx)
        elif tag == "p":
            draw_pixel(window, cam, payload[1], ctx)
        elif tag == "hum":
            _vdraw.draw_human_full(window, cam, ctx, payload[1])
        elif tag == "animal":
            _animals.draw_animal(window, cam, ctx, payload[1])
        elif tag == "vi":
            _vdraw.draw_village_item(window, cam, ctx, payload[1],
                                     payload[2])
        elif tag == "blood":
            _vdraw.draw_blood(window, cam, ctx, payload[1])


def draw_objects_and_pixels(window, cam, objects, pixels, preset_idx,
                            extras=()):
    prune_object_sprites(objects)
    _draw_render_items(window, cam,
                       _collect_render_items(cam, objects, pixels, extras),
                       preset_idx)
