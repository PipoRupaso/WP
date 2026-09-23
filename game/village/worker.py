# -*- coding: utf-8 -*-
"""Шаг жителя: движение, работа, ноша, сон."""

import math
from game.core import state as G
from game.core.config import (
    rng)
from game.core.utils import (
    hash01)
from game.village.core import (
    _vil_gz)
from game.village.planner import (
    _vil_arrive, _vil_blocked, _vil_log_depot, _vil_pick_task,
    _vil_stone_depot)

def _vil_worker_step(v, hum, dt):
    fx, fy = v["fire"]
    ph = v["phase"]
    if hum["state"] == "air":
        return
    if hum["state"] == "stun":
        hum["st"] -= dt
        if hum["st"] <= 0:
            hum["state"] = "idle"
            hum["act"] = "task"
        return
    if hum["state"] in ("walk", "run", "hunt"):
        dx, dy = hum["tx"] - hum["x"], hum["ty"] - hum["y"]
        d = math.hypot(dx, dy)
        if hum["state"] == "hunt":
            # добыча двигается: цель обновляем каждый кадр
            an_ = next((a for a in v["animals"]
                        if id(a) == hum.get("prey")), None)
            if an_ is None:
                _village_tribe._vil_release_prey(v, hum)
                hum["state"] = "idle"
                hum["st"] = 0.3
                hum["act"] = "task"
                return
            o_ = an_
            hum["tx"], hum["ty"] = o_["x"], o_["y"]
            if an_["kind"] == "deer":
                if d < 2.3:
                    o_["hunt_by"] = None
                    hum["state"] = "aim"
                    hum["st"] = 1.1
                    return
            elif d < 0.5:
                hum["state"] = "attack"
                hum["st"] = 0.7
                return
        spd = 3.4 if hum["state"] == "hunt" else (
            2.8 if (hum["carry"] or hum.get("carry_log") or d > 6.0)
            else 2.2)
        if d < 0.14:
            hum["x"], hum["y"] = hum["tx"], hum["ty"]
            _vil_arrive(v, hum)
        else:
            k = spd * dt / d
            nx = hum["x"] + dx * k
            ny = hum["y"] + dy * k
            # все объекты твёрдые: скольжение по осям
            if not _vil_blocked(v, nx, hum["y"]):
                hum["x"] = nx
            if not _vil_blocked(v, hum["x"], ny):
                hum["y"] = ny
            # упёрся в твёрдое: рядом с целью — считаем, что дошёл;
            # иначе — обход вбок; совсем не может — другое занятие
            if hum["x"] == hum.get("_px") and hum["y"] == hum.get("_py"):
                hum["stuck_t"] = hum.get("stuck_t", 0.0) + dt
                if d < 2.0:
                    _vil_arrive(v, hum)
                    return
                dx0 = hum["tx"] - hum["x"]
                dy0 = hum["ty"] - hum["y"]
                l0 = max(0.3, math.hypot(dx0, dy0))
                sg = 1.0 if hum["id"] % 2 == 0 else -1.0
                sx_ = hum["x"] + (-dy0 / l0) * 0.55 * sg
                sy_ = hum["y"] + (dx0 / l0) * 0.55 * sg
                if not _vil_blocked(v, sx_, sy_):
                    hum["x"], hum["y"] = sx_, sy_
                    hum["stuck_t"] = 0.0
                elif hum["stuck_t"] > 3.5:
                    hum["stuck_t"] = 0.0
                    # недоборавшаяся жердь — пропадает (не зацикливаться)
                    if hum["act"] == "to_stick":
                        s0 = next((s for s in v["sticks"]
                                   if s["owner"] == hum["id"]), None)
                        if s0 is not None:
                            v["sticks"].remove(s0)
                    _village_tribe._vil_release_prey(v, hum)
                    # ношу вернуть на землю — не бросать «в воздухе»
                    lo = hum.get("log")
                    if lo is not None and lo.get("owner") == hum["id"]:
                        lo["owner"] = None
                    sp = hum.get("sp")
                    if sp is not None and sp.get("owner") == hum["id"]:
                        sp["owner"] = None
                    for st2 in v["sticks"]:
                        if st2["owner"] == hum["id"]:
                            st2["owner"] = None
                    if hum.get("carry"):
                        v["sticks"].append(dict(
                            x=hum["x"], y=hum["y"], z=hum["z"],
                            vz=0.0, falling=False, t=0.0, owner=None,
                            ang=rng.uniform(0, 6.283)))
                    hum["carry"] = False
                    hum["sticks"] = 0
                    hum["carry_log"] = False
                    hum["carry_sp"] = False
                    hum["state"] = "idle"
                    hum["st"] = 0.3
                    hum["act"] = "task"
                    hum["work_plot"] = -1
                    hum["work_job"] = None
                    return
            else:
                hum["stuck_t"] = 0.0
            hum["_px"], hum["_py"] = hum["x"], hum["y"]
            _gz2 = _vil_gz(hum["x"], hum["y"])
            hum["z"] += (_gz2 - hum["z"]) * min(1.0, 12.0 * dt)
            if (dx - dy) < 0:
                hum["flip"] = True
            elif (dx - dy) > 0:
                hum["flip"] = False
    elif hum["state"] == "pick":
        hum["st"] -= dt
        if hum["st"] <= 0:
            s = next((s for s in v["sticks"] if s["owner"] == hum["id"]),
                     None)
            if s is not None:
                v["sticks"].remove(s)
            hum["carry"] = True
            hum["sticks"] += 1
            hum["act"] = "to_pile"
            hum["tx"], hum["ty"] = v["pile"]
            hum["state"] = "run"
    elif hum["state"] == "drop":
        hum["st"] -= dt
        if hum["st"] <= 0:
            hum["carry"] = False
            v["pile_n"] += 1
            hum["act"] = "task"
            _vil_pick_task(v, hum)
    elif hum["state"] == "chop":
        o = next((t["o"] for t in G.VIL_TREES
                  if id(t["o"]) == hum.get("tree")), None)
        if o is None or o.get("dead"):
            hum["state"] = "idle"
            hum["st"] = 0.3
            hum["act"] = "task"
            return
        hum["st"] -= dt
        if hum["st"] <= 0:
            # срублено: пенёк остаётся, два бревна на земле
            o["dead"] = "stump"
            o["stump_t"] = v["t"]
            o["chop_by"] = None
            lx, ly = o["x"] + 0.5, o["y"] + 0.45
            for k in range(2):
                v["logs"].append(dict(
                    x=lx + (k - 0.5) * 0.35, y=ly + k * 0.2,
                    z=_vil_gz(lx, ly) + 0.04, owner=None, placed=False,
                    ang=rng.uniform(0, 3.14)))
            _village_construction._vil_puff(v, lx, ly, _vil_gz(lx, ly) + 1.1)
            _village_construction._vil_puff(v, lx, ly, _vil_gz(lx, ly) + 0.6)
            hum["state"] = "idle"
            hum["st"] = 0.4
            hum["act"] = "task"
    elif hum["state"] == "pebble":
        hum["st"] -= dt
        if hum["st"] <= 0:
            pb = next((s2 for s2 in v["pebbles"]
                       if s2["owner"] == hum["id"]), None)
            if pb is not None:
                v["pebbles"].remove(pb)
            hum["stone"] = True
            hum["state"] = "idle"
            hum["st"] = 0.3
            hum["act"] = "task"
    elif hum["state"] == "pick_log":
        hum["st"] -= dt
        if hum["st"] <= 0:
            lo = hum.get("log")
            if lo is None or lo["owner"] != hum["id"]:
                hum["state"] = "idle"
                hum["st"] = 0.3
                hum["act"] = "task"
                return
            hum["carry_log"] = True
            dep = _vil_log_depot(v)
            hum["tx"], hum["ty"] = dep
            hum["act"] = "drop_log"
            hum["state"] = "run"
    elif hum["state"] == "drop_log":
        hum["st"] -= dt
        if hum["st"] <= 0:
            lo = hum.get("log")
            hum["carry_log"] = False
            if lo is not None and lo["owner"] == hum["id"]:
                lo["owner"] = None
                lo["placed"] = True
                lo["x"], lo["y"] = hum["x"], hum["y"]
                v["res"]["logs"] = sum(1 for l in v["logs"]
                                        if l["placed"])
            hum["state"] = "idle"
            hum["st"] = 0.3
            hum["act"] = "task"
    elif hum["state"] == "pick_sp":
        hum["st"] -= dt
        if hum["st"] <= 0:
            sp = hum.get("sp")
            if sp is None or sp["owner"] != hum["id"]:
                hum["state"] = "idle"
                hum["st"] = 0.3
                hum["act"] = "task"
                return
            hum["carry_sp"] = True
            dep = _vil_stone_depot(v)
            hum["tx"], hum["ty"] = dep
            hum["act"] = "drop_sp"
            hum["state"] = "run"
    elif hum["state"] == "drop_sp":
        hum["st"] -= dt
        if hum["st"] <= 0:
            sp = hum.get("sp")
            hum["carry_sp"] = False
            if sp is not None and sp["owner"] == hum["id"]:
                # камень уходит в склад: галька с земли снимается
                if sp in v["pebbles"]:
                    v["pebbles"].remove(sp)
                dep = _vil_stone_depot(v)
                v["stones_placed"].append(dict(
                    x=dep[0] + (hash01(hum["id"], 3, 4) - 0.5) * 0.9,
                    y=dep[1] + (hash01(hum["id"], 5, 6) - 0.5) * 0.9))
                v["res"]["stones"] = len(v["stones_placed"])
            hum["state"] = "idle"
            hum["st"] = 0.3
            hum["act"] = "task"
    elif hum["state"] in ("work", "place", "clean"):
        hum["st"] -= dt * v.get("work_mult", 1.0)
        if hum["st"] <= 0:
            _village_construction._vil_work_done(v, hum)
    elif hum["state"] in ("attack", "aim"):
        hum["st"] -= dt
        if hum["st"] <= 0:
            an_ = next((a for a in v["animals"]
                        if id(a) == hum.get("prey")), None)
            if an_ is not None and \
                    math.hypot(an_["x"] - hum["x"],
                               an_["y"] - hum["y"]) <= 4.0:
                an_["hunt_by"] = None
                _village_tribe._vil_kill_prey(v, hum, an_)
            _village_tribe._vil_release_prey(v, hum)
            hum["state"] = "idle"
            hum["st"] = 0.4
            hum["act"] = "task"
    elif hum["state"] == "light":
        hum["st"] -= dt
        if hum["st"] <= 0:
            v["lit"] = True
            _village_construction._vil_phase_hut(v)
    elif hum["state"] == "sit":
        hum["st"] -= dt
        if hum["st"] <= 0:
            hum["sit_ang"] = 0.0
            _vil_pick_task(v, hum)
    else:  # idle
        hum["st"] -= dt
        if hum["st"] <= 0:
            _vil_pick_task(v, hum)


# Циклические ссылки на модули выше по цепочке: импорт в конце файла,
# имена используются только внутри функций.
from game.village import construction as _village_construction  # noqa: E402
from game.village import tribe as _village_tribe  # noqa: E402
