# -*- coding: utf-8 -*-
"""3D-выбор точки удара по объектам."""

import math
from game.core import state as G
from game.world.terrain import (
    ground_height_at)

_PICK_IDX = dict(ver=-2, objs=None, grid={})


def _pick_index(objects):
    if _PICK_IDX["ver"] != G.WORLD_VERSION or _PICK_IDX["objs"] is not objects:
        grid = {}
        for o in objects:
            x0 = math.floor(o["x"])
            x1 = math.floor(o["x"] + o["w"] - 1e-6)
            y0 = math.floor(o["y"])
            y1 = math.floor(o["y"] + o["d"] - 1e-6)
            for ix in range(x0, x1 + 1):
                for iy in range(y0, y1 + 1):
                    grid.setdefault((ix, iy), []).append(o)
        _PICK_IDX["ver"], _PICK_IDX["objs"], _PICK_IDX["grid"] = (
            G.WORLD_VERSION, objects, grid)
    return _PICK_IDX["grid"]


def pick_blast_point(cam, objects, sx, sy):
    """3D-выбор точки: луч сверху вниз — блок раньше земли за ним."""
    grid = _pick_index(objects)
    z = 12.0
    while z >= 0:
        wx, wy = cam.screen_to_world(sx, sy, z)
        for o in grid.get((math.floor(wx), math.floor(wy)), ()):
            if (o["x"] - 0.03 <= wx < o["x"] + o["w"] + 0.03
                    and o["y"] - 0.03 <= wy < o["y"] + o["d"] + 0.03
                    and o["z"] - 0.03 <= z <= o["z"] + o["h"] + 0.03):
                return (wx, wy, z, o)
        z -= 0.1
    wx, wy = cam.screen_to_world(sx, sy, 0.0)
    for _ in range(3):
        _gz = ground_height_at(wx, wy)
        if _gz is None:
            break
        wx, wy = cam.screen_to_world(sx, sy, _gz)
    return (wx, wy, 0.0, None)
