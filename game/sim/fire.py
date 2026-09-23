# -*- coding: utf-8 -*-
"""Пожары: распространение и выгорание."""

import math
from game.core.config import (
    BURN_MATS, _BURN_RATE, rng)
from game.core.utils import (
    clamp)
from game.world.world_state import (
    FLAMES, HOUSE_BURNING, HOUSE_HIT, SMOKES, bump_world, fx_rng)
from game.sim.pixels import (
    add_pixel, object_chip_grid)
from game.sim.destruction import (
    _house_damage_add)

def _burn_fx_spawn(o):
    """Пламя и тёмный дым с поверхности горящего объекта."""
    k = fx_rng
    if o.get("shape") == "tree":
        x = o["x"] + 0.5 + k.uniform(-0.2, 0.2)
        y = o["y"] + 0.5 + k.uniform(-0.2, 0.2)
        z = o["z"] + k.uniform(0.2, 0.85)
    else:
        x = o["x"] + k.random() * o["w"]
        y = o["y"] + k.random() * o["d"]
        z = o["z"] + o["h"] * k.uniform(0.25, 1.0)
    sm = max(0.13, min(0.3, o.get("h", 0.35) * 0.26))
    if len(FLAMES) < 110:
        FLAMES.append(dict(x=x, y=y, z=z, t=0.0,
                           life=0.30 + k.random() * 0.22,
                           s=sm * k.uniform(0.7, 1.5),
                           ph=k.random() * 6.283))
    if len(SMOKES) < 120 and k.random() < 0.75:
        SMOKES.append(dict(x=x, y=y, z=z + 0.18, t=0.0,
                           life=2.4 + k.random() * 1.0,
                           r=0.24 + k.random() * 0.16,
                           c=(58, 53, 50), a=150, rise=1.6))


def _fire_neighbor(objects, o):
    """Ближайший горючий сосед в 1.15 клетки — туда перекинется огонь."""
    ox = o["x"] + o.get("w", 1) / 2
    oy = o["y"] + o.get("d", 1) / 2
    best, bd = None, 1.15
    for n in objects:
        if n is o or n.get("burn") or n.get("dead"):
            continue
        if n.get("shape") != "tree" and n.get("mat") not in BURN_MATS:
            continue
        nx = clamp(ox, n["x"], n["x"] + n.get("w", 1))
        ny = clamp(oy, n["y"], n["y"] + n.get("d", 1))
        d = math.hypot(nx - ox, ny - oy)
        if d < bd:
            bd, best = d, n
    return best


def _burn_out(objects, pixels, o):
    """Сгорело дотла: зола, угар и исчезновение объекта."""
    o.pop("burn", None)
    o.pop("fx_t", None)
    o.pop("sp_t", None)
    if o.get("shape") == "tree":
        o["dead"] = "stump"   # обгоревший пенёк остаётся
        o["char"] = True
        return
    g = object_chip_grid(o)
    cells = g["cells"]
    for c in rng.sample(cells, min(len(cells), 24)):
        add_pixel(pixels, c[3], c[4], c[5] + 0.02,
                  rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4),
                  rng.uniform(0.4, 1.4), 3, (40, 36, 32))
    if len(SMOKES) < 120:
        SMOKES.append(dict(x=o["x"] + o["w"] / 2, y=o["y"] + o["d"] / 2,
                           z=o["z"] + 0.3, t=0.0, life=1.8, r=0.4,
                           c=(52, 47, 44), a=150, rise=1.5))
    hid = o.get("house")
    if hid:
        _house_damage_add(objects, hid, len(cells))
    if o in objects:
        objects.remove(o)
    bump_world()  # опоры для висящих сверху блоков пересчитаются


def _fire_tick(objects, pixels, dt):
    """Таймеры поджига, прогресс горения, распространение пожара."""
    burning = HOUSE_BURNING
    burning.clear()
    for o in list(objects):
        ig = o.get("ig")
        if ig is not None:
            if ig <= dt:
                o.pop("ig", None)
                o["burn"] = 1e-4
                o["fx_t"] = o["sp_t"] = 0.0
                if o.get("house"):
                    HOUSE_HIT[o["house"]] = True  # пожар: дымка из трубы нет
            else:
                o["ig"] = ig - dt
                continue
        if o.get("burn") is None:
            continue
        if o.get("house"):
            burning.add(o["house"])
        o["burn"] += dt * (0.10 if o.get("shape") == "tree"
                             else _BURN_RATE.get(o.get("mat"), 0.055))
        o["fx_t"] = o.get("fx_t", 0.0) + dt
        while o["fx_t"] >= 0.075:
            o["fx_t"] -= 0.075
            _burn_fx_spawn(o)
        o["sp_t"] = o.get("sp_t", 0.0) + dt
        if o["sp_t"] > 0.55 and o["burn"] > 0.3:
            o["sp_t"] = 0.0
            if rng.random() < 0.6:
                n = _fire_neighbor(objects, o)
                if n is not None and n.get("ig") is None:
                    n["ig"] = rng.uniform(0.6, 1.4)
        if o["burn"] >= 1.0:
            _burn_out(objects, pixels, o)
