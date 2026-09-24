# -*- coding: utf-8 -*-
"""Единая глубинная сортировка мира (painter's algorithm).

Всё, что рисуется в мире, проходит через один список отрисовки:
земляные декали (кровь) -> объекты/дома/деревья/жерди -> пиксели-осколки
-> люди и звери. Ключ глубины у объёмных предметов — центр основания
(footprint), у точечных сущностей (люди, звери) — их ноги, у осколков —
их точка. Благодаря этому человек, проходящий ЗА домом или ёлкой,
рисуется раньше них и корректно скрывается, а проходящий ПЕРЕД ними —
позже и рисуется поверх. Никаких отдельных проходов «поверх мира».
"""

from game.render.camera import (
    _proj_pt)


def depth_key(ctx, x, y):
    """Глубина точки в мировых координатах с учётом поворота камеры."""
    rot, W, D = ctx[0], ctx[1], ctx[2]
    if rot == 0:
        return x + y
    if rot == 1:
        return D - y + x
    if rot == 2:
        return W - x + (D - y)
    return y + (W - x)


# типы в порядке отрисовки при равной глубине
T_DECAL = 0     # кровь, пятна на земле
T_OBJECT = 1    # коробки, дома, деревья, жерди, костёр
T_PIXEL = 2     # летящие осколки
T_ACTOR = 3     # люди и звери


def collect_world(cam, objects, pixels, extras=()):
    """Собрать и отсортировать всё видимое.

    extras — готовые кортежи (k, z, typ, payload, sx, sy) от поселения
    и зверей (они сами знают свои экранные координаты и отсечение).
    """
    ctx = None
    items = []
    _w0, _h0 = cam.win_w, cam.win_h
    for o in objects:
        x, y, z, w, d = o["x"], o["y"], o["z"], o["w"], o["d"]
        if ctx is None:
            from game.render.camera import _proj_ctx
            ctx = _proj_ctx(cam)
        _pxc, _pyc = _proj_pt(ctx, x + w / 2, y + d / 2, z)
        if (_pxc < -90 or _pxc > _w0 + 90 or _pyc < -220
                or _pyc > _h0 + 90):
            continue  # мимо камеры — без сортировки и рендера
        # ключ глубины — центр основания: человек у южной или восточной
        # стены имеет ключ больше и рисуется поверх стены, а за домом —
        # меньше и скрывается за ним
        _k = depth_key(ctx, x + w / 2, y + d / 2)
        items.append((_k, z, T_OBJECT, ("o", o)))
    for p in pixels:
        if ctx is None:
            from game.render.camera import _proj_ctx
            ctx = _proj_ctx(cam)
        _k = depth_key(ctx, p["x"], p["y"])
        items.append((_k, p["z"], T_PIXEL, ("p", p)))
    items.extend(extras)
    items.sort(key=lambda t: (t[0], t[1], t[2]))
    return items
