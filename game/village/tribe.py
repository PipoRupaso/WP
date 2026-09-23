# -*- coding: utf-8 -*-
"""Вожак, копья, охота."""

import math
from game.village.core import (
    _vil_gz)
from game.village.construction import (
    _vil_phase_hut)

def _vil_leader_step(v, hum, dt):
    fx, fy = v["fire"]
    ph = v["phase"]
    if ph == "council":
        t = v["t"]
        if t < 2.6:
            # встать в круг
            i = hum["id"]
            ang = i * 6.283 / 10 + 0.31
            hum["tx"] = fx + math.cos(ang) * 1.7
            hum["ty"] = fy + math.sin(ang) * 1.7
            hum["state"] = "walk"
            hum["act"] = "council"
        elif t < 3.6:
            # шагнуть в центр
            hum["tx"], hum["ty"] = fx, fy
            hum["state"] = "walk"
            hum["act"] = "leader_walk"
        else:
            hum["state"] = "idle"
    elif ph in ("fire_stones", "fire_sticks", "fire_light"):
        if hum["state"] in ("work", "place", "light"):
            hum["st"] -= dt
            if hum["st"] <= 0:
                _vil_leader_done(v, hum)
            return
        if hum.get("carried_log"):
            # везёт жердь к огню — не перегенерировать цель
            hum["tx"], hum["ty"] = fx, fy
            hum["act"] = "log"
            hum["state"] = "walk"
            return
        # следующая цель
        if ph == "fire_stones":
            i = v["stones"]
            ang = i * 6.283 / 6 + 0.26
            hum["tx"] = fx + math.cos(ang) * 0.30
            hum["ty"] = fy + math.sin(ang) * 0.30
            hum["act"] = "stone"
        elif ph == "fire_sticks":
            if v["pile_n"] > 0:
                hum["tx"], hum["ty"] = v["pile"]
                hum["act"] = "log_get"
            else:
                hum["tx"], hum["ty"] = fx, fy
                hum["act"] = "log"
        else:  # fire_light
            hum["tx"], hum["ty"] = fx + 0.12, fy + 0.12
            hum["act"] = "light"
        hum["state"] = "walk"


def _vil_leader_done(v, hum):
    ph = v["phase"]
    if ph == "fire_stones":
        v["stones"] += 1
        if v["stones"] >= 6:
            v["phase"] = "fire_sticks"
            v["t"] = 0.0
    elif ph == "fire_sticks":
        if hum.get("carried_log"):
            hum["carried_log"] = False
            v["fire_logs"] += 1
            if v["fire_logs"] >= 4:
                v["phase"] = "fire_light"
                v["t"] = 0.0
        else:
            v["pile_n"] -= 1  # подобрал жердь с кучи
        hum["state"] = "idle"
        hum["st"] = 0.3
    elif ph == "fire_light":
        v["lit"] = True
        _vil_phase_hut(v)
    hum["state"] = "idle"
    hum["st"] = 0.5


def _vil_make_spear(v):
    """Копьё (камень + жерди) в мастерской, пока хватает ресурсов."""
    if v["lvl"] < 2 or v["res"]["spears"] >= 10:
        return
    p12 = next((p for p in v["plots"] if p["tpl"]["hid"] == 12
                and p["state"] == "done"), None)
    if p12 is None or v["res"]["stones"] < 2 or v["pile_n"] < 2:
        return
    v["res"]["stones"] -= 2
    for _ in range(2):
        if v["stones_placed"]:
            v["stones_placed"].pop(0)
    v["pile_n"] -= 2
    v["res"]["spears"] += 1
    bx, by = p12["x"] + 0.62, p12["y"] + 0.20
    z0 = _vil_gz(bx, by)
    v["objects"].append(dict(
        x=bx, y=by, z=z0 + 0.02, w=0.05, d=0.03, h=0.66,
        color="wood_light", shape="box", mat="wood_light",
        vx=0.0, vy=0.0, vz=0.0, erode=1.2, vox=0.04, sort_min=True,
        vid=-2))
    v["objects"].append(dict(
        x=bx - 0.012, y=by - 0.008, z=z0 + 0.62, w=0.07, d=0.05, h=0.10,
        color="gray", shape="box", mat="stone",
        vx=0.0, vy=0.0, vz=0.0, erode=0.6, vox=0.035, sort_min=True,
        vid=-2))


def _vil_spawn_animal(v, kind, px, py):
    """Зверь: зайец (добыча палкой/камнем) или олень (только копьё)."""
    gz = _vil_gz(px, py)
    v["_an_n"] = v.get("_an_n", 0) + 1
    aid = v["_an_n"]
    if kind == "rabbit":
        specs = ((0.0, 0.0, 0.0, 0.16, 0.11, 0.09, "bone", "bone"),
                 (0.14, 0.015, 0.02, 0.09, 0.08, 0.07, "bone", "bone"))
        base = 2.1
    else:
        specs = ((0.0, 0.0, 0.05, 0.42, 0.18, 0.26, "wood_light",
                  "wood_light"),
                 (0.36, 0.02, 0.16, 0.14, 0.10, 0.12, "wood_light",
                  "wood_light"),
                 (0.39, 0.03, 0.26, 0.045, 0.045, 0.09, "bone", "bone"),
                 (0.44, 0.03, 0.26, 0.045, 0.045, 0.09, "bone", "bone"))
        base = 3.4
    boxes = []
    for dx, dy, zz, w_, d_, h_, cc, mm in specs:
        b = dict(x=px + dx, y=py + dy, z=gz + zz, w=w_, d=d_, h=h_,
                 color=cc, shape="box", mat=mm,
                 vx=0.0, vy=0.0, vz=0.0, erode=0.8, vox=0.05,
                 sort_min=True, animal=kind, aid=aid, zoff=zz)
        v["objects"].append(b)
        boxes.append(b)
    v["animals"].append(dict(o=boxes[0], boxes=boxes, kind=kind,
                             home=(px, py), tx=px, ty=py, t=1.0,
                             base=base, spd=base * 0.5))


def _vil_pick_prey(v, hum):
    """Ближайшая добыча: олень — только если копья на всех охотников."""
    if v["lvl"] < 1 or not v["animals"]:
        return None
    n_sp_use = sum(1 for h in v["workers"] if h is not hum
                   and h.get("spear"))
    best, bd = None, 16.0
    for an in v["animals"]:
        o = an["o"]
        if o.get("hunt_by") is not None:
            continue
        if an["kind"] == "deer" and \
                v["res"]["spears"] <= n_sp_use:
            continue  # на оленя — только с копьём
        d = math.hypot(o["x"] - hum["x"], o["y"] - hum["y"])
        if d < bd:
            bd, best = d, an
    return best


def _vil_kill_prey(v, hum, an):
    o = an["o"]
    for b in an["boxes"]:
        try:
            v["objects"].remove(b)
        except ValueError:
            pass
    try:
        v["animals"].remove(an)
    except ValueError:
        pass
    v["food"] = min(80.0, v.get("food", 0.0) + (3.0 if an["kind"] == "deer"
                                                else 1.0))
    v["blood"].append(dict(x=o["x"] + 0.1, y=o["y"] + 0.1, r=0.16,
                           t=0.0, big=False))
    # тушка на земле (протухнет)
    v["objects"].append(dict(
        x=o["x"], y=o["y"], z=_vil_gz(o["x"], o["y"]),
        w=0.16, d=0.10, h=0.05,
        color="bone", shape="box", mat="bone",
        vx=0.0, vy=0.0, vz=0.0, erode=0.6, vox=0.05, sort_min=True,
        carcass=45.0))


def _vil_release_prey(v, hum):
    for an in v["animals"]:
        if an["o"].get("hunt_by") == hum["id"]:
            an["o"]["hunt_by"] = None
    hum["spear"] = False
    hum["prey"] = None
