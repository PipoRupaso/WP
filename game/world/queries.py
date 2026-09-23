# -*- coding: utf-8 -*-
"""Запросы к миру: высота стопки, опоры, индексы твёрдых тел и деревьев."""

import math
from game.core import state as G
from game.world.world_state import (
    _SUP_IDX)
from game.world.terrain import (
    ground_height_at)

def stack_height_at(objects, tx, ty):
    top = 0.0
    gh = ground_height_at(tx + 0.5, ty + 0.5)
    if gh is not None:
        top = gh
    for o in objects:
        if o["x"] <= tx < o["x"] + o["w"] and o["y"] <= ty < o["y"] + o["d"]:
            top = max(top, o["z"] + o["h"])
    return top


def top_object_at(objects, tx, ty):
    best, best_top = None, -1e9
    for o in objects:
        if o["x"] <= tx < o["x"] + o["w"] and o["y"] <= ty < o["y"] + o["d"]:
            if o["z"] + o["h"] >= best_top:
                best, best_top = o, o["z"] + o["h"]
    return best


def support_height_obj(objects, o):
    cx, cy = o["x"] + o["w"] / 2, o["y"] + o["d"] / 2
    sup = ground_height_at(cx, cy)
    if sup is None:
        sup = -1e9
    g = _support_index(objects)
    x0, x1 = o["x"], o["x"] + o["w"]
    y0, y1 = o["y"], o["y"] + o["d"]
    zlim = o["z"] + 0.06
    for ix in range(math.floor(x0), math.floor(x1 - 1e-6) + 1):
        for iy in range(math.floor(y0), math.floor(y1 - 1e-6) + 1):
            lst = g.get((ix, iy))
            if not lst:
                continue
            for top2, ox0, ox1, oy0, oy1, o2 in lst:
                if o2 is o or top2 > zlim or top2 <= sup:
                    continue
                if x0 < ox1 and ox0 < x1 and y0 < oy1 and oy0 < y1:
                    sup = top2
    return sup


def _support_index(objects):
    """Клетка 1x1 -> [(верх, x0, x1, y0, y1)] по убыванию верха.
    Кэш на пару списков (список не-ёлков и полный список): раньше индекс
    пересобирался на каждом физ-кадре, потому что solids создавался заново."""
    e = _SUP_IDX.get(id(objects))
    if e is not None and e[0] == G.WORLD_VERSION and e[1] is objects:
        return e[2]
    grid = {}
    for o in objects:
        if o.get("shape") == "tree":
            continue
        top = o["z"] + o["h"]
        x0, x1, y0, y1 = o["x"], o["x"] + o["w"], o["y"], o["y"] + o["d"]
        for ix in range(math.floor(x0), math.floor(x1 - 1e-6) + 1):
            for iy in range(math.floor(y0), math.floor(y1 - 1e-6) + 1):
                grid.setdefault((ix, iy), []).append((top, x0, x1, y0,
                                                     y1, o))
    for lst in grid.values():
        # key без dict: при равных геометриях не сравнивать сами объекты
        lst.sort(key=lambda t: (t[0], t[1], t[3]), reverse=True)
    if len(_SUP_IDX) > 4:
        _SUP_IDX.clear()
    _SUP_IDX[id(objects)] = (G.WORLD_VERSION, objects, grid)
    return grid


_SOLIDS_C = {"key": None, "lst": None}
_TREES_C = {"key": None, "lst": None}


def _solids_of(objects):
    """Не-ёлки: список со стабильной идентичностью (кэш _support_index
    привязан к id списка), пересборка только при смене мира/состава."""
    key = (id(objects), G.WORLD_VERSION, len(objects))
    if _SOLIDS_C["key"] != key:
        _SOLIDS_C["lst"] = [o for o in objects if o.get("shape") != "tree"]
        _SOLIDS_C["key"] = key
    return _SOLIDS_C["lst"]


def _trees_of(objects):
    """Ёлки с стабильной идентичностью списка для разнесённого апдейта."""
    key = (id(objects), G.WORLD_VERSION, len(objects))
    if _TREES_C["key"] != key:
        _TREES_C["lst"] = [o for o in objects if o.get("shape") == "tree"]
        _TREES_C["key"] = key
    return _TREES_C["lst"]


def support_height_point(objects, x, y, z):
    gh = ground_height_at(x, y)
    sup = gh if gh is not None else -1e9
    lst = _support_index(objects).get((math.floor(x), math.floor(y)))
    if lst:
        zlim = z + 0.06
        for top, x0, x1, y0, y1, _o in lst:
            if top > zlim:
                continue
            if x0 <= x < x1 and y0 <= y < y1:
                sup = top  # список по убыванию — первый годный и есть ответ
                break
    return sup
