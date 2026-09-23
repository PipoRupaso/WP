# -*- coding: utf-8 -*-
"""Физика пикселей/обломков/объектов."""

import math
from game.core import state as G
from game.core.config import (
    GRAVITY, rng)
from game.core.utils import (
    clamp)
from game.world.world_state import (
    CHIMNEY_T, DUST, FLYERS, HOUSE_HIT, SMOKES, VENTS, WIND, _PHYS_AUDIT,
    _SUP_IDX, fx_rng)
from game.world.queries import (
    _solids_of, _trees_of, support_height_obj, support_height_point)
from game.sim.destruction import (
    _landing_dust)
from game.sim.fire import (
    _fire_tick)

def step_physics(objects, pixels, dt):
    G._PHYS_TICK += 1
    alive_ids = {id(o) for o in objects} if VENTS else ()
    for h, vent in VENTS.items():  # дымок из целых труб
        if HOUSE_HIT.get(h):
            continue
        if id(vent) not in alive_ids:
            continue
        CHIMNEY_T[h] = CHIMNEY_T.get(h, 0.0) + dt
        if CHIMNEY_T[h] >= 0.25 and len(SMOKES) < 100:
            CHIMNEY_T[h] = 0.0
            SMOKES.append(dict(
                x=vent["x"] + vent["w"] / 2 + fx_rng.uniform(-0.03, 0.03),
                y=vent["y"] + vent["d"] / 2 + fx_rng.uniform(-0.03, 0.03),
                z=vent["z"] + vent["h"] + 0.05, t=0.0,
                life=2.2 + fx_rng.random() * 0.8,
                r=0.18 + fx_rng.random() * 0.12))
    G._FIRE_ACC += dt
    if G._FIRE_ACC >= 1.0 / 30.0:
        _fire_tick(objects, pixels, G._FIRE_ACC)
        G._FIRE_ACC = 0.0
    wx, wy = WIND["wx"], WIND["wy"]
    crowded = len(pixels) > 800
    solids = _solids_of(objects)
    # Опоры неподвижных тел могут измениться только после bump_world().
    # После этого проверяем их по 128 за кадр, а не весь мир за один кадр.
    if solids:
        _n = len(solids)
        if _PHYS_AUDIT["version"] != G.WORLD_VERSION:
            _PHYS_AUDIT["version"] = G.WORLD_VERSION
            _PHYS_AUDIT["cursor"] = 0
        _end = min(_n, _PHYS_AUDIT["cursor"] + 128)
        for _i in range(_PHYS_AUDIT["cursor"], _end):
            _o = solids[_i]
            _pv = _o.get("park_v")
            if _pv is None or _pv == G.WORLD_VERSION:
                continue
            if _o.get("burn") or \
                    _o["z"] - support_height_obj(solids, _o) > 0.055:
                _o["park_v"] = None
            else:
                _o["park_v"] = G.WORLD_VERSION
        _PHYS_AUDIT["cursor"] = _end
    # Деревьев больше всего. Каждое обновляется в 1/4 кадров, но с
    # увеличенным dt: физика сохраняет скорость, а CPU не обходит весь лес.
    dt4 = dt * 4.0
    for o in _trees_of(objects):
        if (G._PHYS_TICK + int(o.get("phase", 0.0) * 1000)) % 4:
            continue
        if o.get("shake", 0.0) > 0.0:
            o["shake"] = max(0.0, o["shake"] - dt4 * 0.9)
        if o.get("hop", 0.0) > 0.0 or o.get("hopv", 0.0) != 0.0:
            _hv = o.get("hopv", 0.0) - 13.0 * dt4
            _h = o.get("hop", 0.0) + _hv * dt4
            if _h < 0.0:
                _h = 0.0
                _hv = -_hv * 0.28 if _hv < -0.6 else 0.0
            o["hop"], o["hopv"] = _h, _hv
        if not o.get("dead"):
            o["lvx"] += (-20.0 * o["lx"] - 3.8 * o["lvx"]) * dt4
            o["lvy"] += (-20.0 * o["ly"] - 3.8 * o["lvy"]) * dt4
            o["lx"] = clamp(o["lx"] + o["lvx"] * dt4, -1.3, 1.3)
            o["ly"] = clamp(o["ly"] + o["lvy"] * dt4, -1.3, 1.3)
            _k1 = 1.0 - math.exp(-dt4 / o.get("sw_tau", 2.5))
            o["_swx"] = o.get("_swx", 0.0) + (wx - o.get("_swx", 0.0)) * _k1
            o["_swy"] = o.get("_swy", 0.0) + (wy - o.get("_swy", 0.0)) * _k1
            _svx = o.get("_svx", 0.0) + ((o["_swx"] * 0.14
                                          - o.get("_spx", 0.0)) * 3.0
                                         - o.get("_svx", 0.0) * 1.1) * dt4
            _svy = o.get("_svy", 0.0) + ((o["_swy"] * 0.14
                                          - o.get("_spy", 0.0)) * 3.0
                                         - o.get("_svy", 0.0) * 1.1) * dt4
            o["_svx"], o["_svy"] = _svx, _svy
            o["_spx"] = o.get("_spx", 0.0) + _svx * dt4
            o["_spy"] = o.get("_spy", 0.0) + _svy * dt4
    for o in solids:
        if o.get("park_v") is not None:
            continue  # упакован; надзор выше распакует при потере опоры
        sup = support_height_obj(solids, o)
        airborne = o["z"] > sup + 0.002 or abs(o["vz"]) > 1e-6
        if airborne:
            if not o.get("tmb"):  # обрушившийся кусок валится под углом
                o["tmb"] = True
                o["vx"] += rng.uniform(-0.35, 0.35)
                o["vy"] += rng.uniform(-0.35, 0.35)
            _SUP_IDX.clear()  # летящий блок: индекс протух
            o["vz"] -= GRAVITY * dt
            o["z"] += o["vz"] * dt
            o["vx"] *= max(0.0, 1 - 0.15 * dt)
            o["vy"] *= max(0.0, 1 - 0.15 * dt)
            if o["z"] <= sup:
                o["z"] = sup
                if o["vz"] < -5:
                    _landing_dust(o, sup)
                o["vz"] = -o["vz"] * 0.25 if o["vz"] < -3 else 0.0
                o["vx"] *= 0.6
                o["vy"] *= 0.6
        else:
            o["vx"] *= max(0.0, 1 - 6 * dt)
            o["vy"] *= max(0.0, 1 - 6 * dt)
            if abs(o["vx"]) < 0.05:
                o["vx"] = 0.0
            if abs(o["vy"]) < 0.05:
                o["vy"] = 0.0
            o["park_v"] = G.WORLD_VERSION  # упакован до смены мира
        o["x"] += o["vx"] * dt
        o["y"] += o["vy"] * dt
    for p in pixels:
        if p["rest"]:
            p["t"] += dt * (3.0 if crowded else 1.0)
            left = p.get("life", 9.0) - p["t"]
            p["fade"] = clamp(left / 1.2, 0.0, 1.0)
            continue
        if p.get("kind") in ("sh", "fib"):
            p["ang"] += p["spin"] * dt
        last_sup = p.get("sup")
        if (last_sup is None or G._PHYS_TICK - p.get("supt", -99) >= 2
                or p["z"] - last_sup < 1.0):
            last_sup = support_height_point(objects, p["x"], p["y"], p["z"])
            p["sup"], p["supt"] = last_sup, G._PHYS_TICK
        sup = last_sup
        p["vz"] -= GRAVITY * dt
        # ветер: лёгкая мелочь плывёт по ветру, тяжёлая почти нет
        wk = 0.55 if p.get("kind") == "fib" else (
            0.22 if p.get("kind") == "px" and p["size"] <= 3 else 0.06)
        p["vx"] += (wx - p["vx"]) * min(1.0, wk * dt)
        p["vy"] += (wy - p["vy"]) * min(1.0, wk * dt)
        drag = max(0.0, 1 - 0.7 * dt)  # воздушные: лёгкое сопротивление
        p["vx"] *= drag
        p["vy"] *= drag
        p["x"] += p["vx"] * dt
        p["y"] += p["vy"] * dt
        p["z"] += p["vz"] * dt
        if p["size"] >= 5 and p["vz"] < -4.0 and not p["rest"]:
            p["dust_t"] = p.get("dust_t", 0.0) + dt
            if p["dust_t"] >= 0.09 and len(DUST) < 240:
                p["dust_t"] = 0.0
                DUST.append(dict(x=p["x"], y=p["y"], z=p["z"], t=0.0,
                                 life=0.35, r=0.12, c=(125, 114, 96), a=55))
        if p["z"] <= sup:
            p["z"] = sup
            if (p["size"] >= 4 and len(DUST) < 240
                    and fx_rng.random() < 0.4):
                DUST.append(dict(x=p["x"], y=p["y"], z=sup + 0.08, t=0.0,
                                 life=0.45, r=0.14 + p["size"] * 0.03,
                                 c=(118, 106, 88), a=70))
            if abs(p["vz"]) > 1.2:
                p["vz"] = -p["vz"] * 0.35
                p["vx"] *= 0.6
                p["vy"] *= 0.6
            else:
                p["vz"] = 0.0
                p["vx"] *= max(0.0, 1 - 5 * dt)
                p["vy"] *= max(0.0, 1 - 5 * dt)
                if math.hypot(p["vx"], p["vy"]) < 0.4:
                    p["vx"] = p["vy"] = 0.0
                    p["spin"] = 0.0
                    p["rest"] = True
    pixels[:] = [p for p in pixels
                 if p["z"] > -6 and p.get("fade", 1.0) > 0.0]
    for f in FLYERS:
        if f["rest"]:
            f["t"] += dt
            f["fade"] = clamp(min(1.0, (7.5 - f["t"]) / 1.5), 0.0, 1.0)
            if f.get("et", 1.0) < 0.25:
                f["et"] = min(0.25, f["et"] + dt)
                k = f["et"] / 0.25
                k = k * k * (3 - 2 * k)
                f["spin"] = f["a0"] + (f["a1"] - f["a0"]) * k
            continue
        f["vz"] -= GRAVITY * 0.55 * dt
        dr = max(0.0, 1 - 0.4 * dt)
        f["vx"] *= dr
        f["vy"] *= dr
        f["vx"] += (wx - f["vx"]) * min(1.0, 0.8 * dt)
        f["vy"] += (wy - f["vy"]) * min(1.0, 0.8 * dt)
        f["x"] += f["vx"] * dt
        f["y"] += f["vy"] * dt
        f["z"] += f["vz"] * dt
        f["phase"] += f["spin_v"] * dt
        f["spin"] += f["spin_v"] * dt
        if f["z"] < -6:
            f["rest"], f["t"] = True, 99.0
            continue
        sup = support_height_point(objects, f["x"], f["y"], f["z"])
        if f["z"] <= sup:
            f["z"] = sup
            if f["vz"] < -3.0:
                f["vz"] = -f["vz"] * 0.25
                f["vx"] *= 0.5
                f["vy"] *= 0.5
            else:
                f["rest"] = True
                f["t"] = 0.0
                f["a0"] = f["spin"]
                f["a1"] = (round((f["spin"] - math.pi / 2) / math.pi)
                           * math.pi + math.pi / 2)
                f["et"] = 0.0
                sp = math.hypot(f["vx"], f["vy"])
                if sp > 0.5:
                    f["dx"], f["dy"] = f["vx"] / sp, f["vy"] / sp
                f["vx"] = f["vy"] = f["vz"] = 0.0
    FLYERS[:] = [f for f in FLYERS
                 if not f["rest"] or f.get("fade", 1.0) > 0.0]
