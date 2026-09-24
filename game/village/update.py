# -*- coding: utf-8 -*-
"""Главный шаг обновления поселения."""

import math
from game.core import state as G
from game.core.config import (
    GRID_D, GRID_W, rng)
from game.core.utils import (
    clamp, hash01)
from game.world.world_state import (
    SMOKES, fx_rng)
from game.world.terrain import (
    ground_height_at)
from game.village.core import (
    _HTUNIC_LEADER, _vil_gz, _vil_pop)
from game.village.planner import (
    _vil_planner, _vil_sleep_spot, _vil_solids)
from game.village.worker import (
    _vil_worker_step)
from game.village.construction import (
    _plot_broken, _vil_human_die, _vil_puff)
from game.village.tribe import (
    _vil_leader_step, _vil_make_spear, _vil_release_prey, _vil_spawn_animal)

def update_village(dt, objects=None):
    """Обновление поселения: фазы, люди, жерди, костёр, город."""
    v = G.VIL
    if v is None:
        return
    if objects is not None:
        v["objects"] = objects
    G.VIL_T += dt
    v["t"] += dt
    # --- падение жердей с деревьев ---
    active = sum(1 for s in v["sticks"] if not s.get("old"))
    if v["t"] >= v["next_drop"] and len(v["sticks"]) < 24:
        v["next_drop"] = v["t"] + 1.6 + hash01(G.VIL_T * 0.7, 1, 2) * 2.8
        fx_, fy_ = v["fire"]
        # жерди: часть падает с веток, часть «находится» на земле
        # у самого костра (короткий круг до кучи)
        for k in range(2 if hash01(G.VIL_T, 13, 14) < 0.4 else 1):
            if hash01(G.VIL_T, 15 + k, 16 + k) < 0.5:
                sx = fx_ + (hash01(G.VIL_T, 5 + k, 6 + k) - 0.5) * 10.0
                sy = fy_ + (hash01(G.VIL_T, 7 + k, 8 + k) - 0.5) * 10.0
                gz = _vil_gz(sx, sy)
                v["sticks"].append(dict(
                    x=sx, y=sy, z=gz, vz=0.0,
                    falling=False, t=0.0,
                    owner=None, ang=hash01(G.VIL_T, 11 + k, 12 + k)
                    * 6.283))
                continue
            trees = [t for t in G.VIL_TREES
                     if not t["o"].get("dead")
                     and math.hypot(t["x"] - fx_, t["y"] - fy_) < 13]
            if not trees:
                continue
            t = trees[int(hash01(G.VIL_T, 3 + k, 4 + k)
                          * len(trees)) % len(trees)]
            sx = t["x"] + (hash01(G.VIL_T, 5 + k, 6 + k) - 0.5) * 1.1
            sy = t["y"] + (hash01(G.VIL_T, 7 + k, 8 + k) - 0.5) * 1.1
            if 1 < sx < GRID_W - 1 and 1 < sy < GRID_D - 1:
                gz = _vil_gz(sx, sy)
                v["sticks"].append(dict(
                    x=sx, y=sy, z=gz + 1.7 + k * 0.25, vz=0.0,
                    falling=True, t=0.0,
                    owner=None, ang=hash01(G.VIL_T, 11 + k, 12 + k)
                    * 6.283))
    for s in v["sticks"]:
        if s["falling"]:
            s["vz"] -= 6.0 * dt
            s["z"] += s["vz"] * dt
            gz = _vil_gz(s["x"], s["y"])
            if s["z"] <= gz:
                s["z"] = gz
                if s["vz"] < -2.5:
                    s["vz"] = -s["vz"] * 0.3
                else:
                    s["vz"] = 0.0
                    s["falling"] = False
        else:
            s["t"] += dt
            if s["t"] > 120 and s["owner"] is None and active > 4:
                s["old"] = True
    v["sticks"] = [s for s in v["sticks"]
                   if not s.get("old") or s["owner"] is not None]
    # --- фазы ---
    ph = v["phase"]
    if ph == "gather" and v["pile_n"] >= 8:
        v["phase"] = "council"
        v["t"] = 0.0
        top = max(v["workers"], key=lambda h: (h["sticks"], -h["id"]))
        v["leader"] = top
        top["tunic"] = _HTUNIC_LEADER
    elif ph == "council" and v["t"] >= 4.8:
        v["phase"] = "fire_stones"
        v["t"] = 0.0
    # --- план: уровни, новые участки, копьё ---
    v["plan_t"] += dt
    v["plan_cd"] = v.get("plan_cd", 0.0) - dt
    if v["plan_cd"] <= 0 and v["lit"]:
        v["plan_cd"] = 2.0
        _vil_planner(v)
        _vil_make_spear(v)
    # --- твёрдые объекты для коллизий ---
    v["sol_t"] -= dt
    if v["sol_t"] <= 0:
        v["sol_t"] = 0.5
        _vil_solids(v)
    # --- пополнение камней: на землю для каменей и склада ---
    _pcap = 10 if v["lvl"] >= 2 else 8
    if v["lit"] and v["t"] >= v.get("peb_cd", 0.0) \
            and len(v["pebbles"]) < _pcap:
        v["peb_cd"] = v["t"] + 9.0 + rng.uniform(0, 8.0)
        fx, fy = v["fire"]
        a = rng.uniform(0, 6.283)
        rr = 2.5 + rng.uniform(0, 10.0)
        px = clamp(fx + math.cos(a) * rr, 2, GRID_W - 2)
        py = clamp(fy + math.sin(a) * rr, 2, GRID_D - 2)
        if ground_height_at(px, py) is not None:
            v["pebbles"].append(dict(x=px, y=py, z=_vil_gz(px, py),
                                     falling=False, owner=None, t=0.0,
                                     old=False,
                                     ang=rng.uniform(0, 6.283)))
    # --- звери: блуждание, бегство, пополнение ---
    _fx_, _fy_ = v["fire"]
    v["an_t"] = v.get("an_t", 0.0) - dt
    if v["an_t"] <= 0:
        v["an_t"] = 8.0
        n_rab = sum(1 for a in v["animals"] if a["kind"] == "rabbit")
        n_dee = sum(1 for a in v["animals"] if a["kind"] == "deer")
        for _ in range(40):
            if n_rab >= 6 and n_dee >= 2:
                break
            kind = ("deer" if n_dee < 2 and (n_rab >= 4
                     or rng.random() < 0.3) else "rabbit")
            a = rng.uniform(0, 6.283)
            rr = 9.0 + rng.uniform(0, 8.0)
            px = clamp(_fx_ + math.cos(a) * rr, 3, GRID_W - 3)
            py = clamp(_fy_ + math.sin(a) * rr, 3, GRID_D - 3)
            if ground_height_at(px, py) is None:
                continue
            _vil_spawn_animal(v, kind, px, py)
            if kind == "deer":
                n_dee += 1
            else:
                n_rab += 1
    for an in list(v["animals"]):
        an["t"] -= dt
        hbid = an.get("hunt_by")
        hx = hy = None
        if hbid is not None:
            hh = next((h for h in v["workers"] if h["id"] == hbid), None)
            if hh is None or hh.get("dead"):
                an["hunt_by"] = None
            else:
                hx, hy = hh["x"], hh["y"]
        fleeing = (hx is not None and
                   math.hypot(hx - an["x"], hy - an["y"]) < 7.0)
        if an["t"] <= 0 or fleeing:
            an["t"] = 2.0 + rng.uniform(0, 3.0)
            if fleeing:
                dx = an["x"] - hx
                dy = an["y"] - hy
                l = max(0.3, math.hypot(dx, dy))
                an["tx"] = clamp(an["x"] + dx / l * 5.0, 2, GRID_W - 2)
                an["ty"] = clamp(an["y"] + dy / l * 5.0, 2, GRID_D - 2)
                an["spd"] = an["base"] * (1.35 if an["kind"] == "deer"
                                          else 1.3)
                an["eating"] = 0.0
            else:
                an["tx"] = clamp(an["home"][0] + rng.uniform(-4, 4),
                                 2, GRID_W - 2)
                an["ty"] = clamp(an["home"][1] + rng.uniform(-4, 4),
                                 2, GRID_D - 2)
                an["spd"] = an["base"] * 0.5
                an["eating"] = rng.uniform(0.0, 3.0)
        dx = an["tx"] - an["x"]
        dy = an["ty"] - an["y"]
        l = math.hypot(dx, dy)
        if l > 0.1:
            k = min(1.0, an["spd"] * dt / l)
            nx = an["x"] + dx * k
            ny = an["y"] + dy * k
            gz = _vil_gz(nx, ny)
            an["x"], an["y"], an["z"] = nx, ny, gz
            if (dx - dy) < 0:
                an["flip"] = True
            elif (dx - dy) > 0:
                an["flip"] = False
        else:
            an["eating"] = an.get("eating", 0.0) - dt
        # походка: у оленя 4 фазы ног, у зайца — цикл прыжка
        if an["kind"] == "rabbit":
            an["ph"] += dt * an["spd"] * 1.15
        else:
            an["ph"] += dt * an["spd"] * 0.62
    # тушки протухают
    for o in list(v["objects"]):
        ct = o.get("carcass")
        if ct is not None:
            o["carcass"] = ct - dt
            if o["carcass"] <= 0:
                v["objects"].remove(o)
    # --- еда: потребление, сбор, готовка в кухне ---
    _pop = _vil_pop(v)
    if _pop:
        _kdone = any(p["tpl"]["hid"] == 8 and p["state"] == "done"
                     for p in v["plots"])
        v["food"] = v.get("food", 0.0) - _pop * 0.040 * dt
        v["food"] += 0.36 * dt  # ягоды, коренья (держат баланс;
        # охота и кухня дают излишек)
        v["cook_t"] = v.get("cook_t", 0.0) - dt
        if v["cook_t"] <= 0:
            v["cook_t"] = 6.0
            if _kdone and v["food"] >= 1.5:
                v["food"] += 1.0  # более сытная еда для всех
                k = next(p for p in v["plots"] if p["tpl"]["hid"] == 8
                         and p["state"] == "done")
                _vil_puff(v, k["x"] + 0.5, k["y"] + 0.5, 0.7, small=True)
        v["food"] = max(0.0, min(v["food"], 80.0))
        if v["food"] <= 0.001:
            v["hunger_t"] = v.get("hunger_t", 0.0) + dt
        else:
            v["hunger_t"] = 0.0
        v["work_mult"] = (0.8 if v.get("hunger_t", 0.0) > 30.0
                          else 1.0) * (1.15 if _kdone else 1.0)
    # --- тропинки: там, где чаще всего ходят ---
    v["wear_t"] = v.get("wear_t", 0.0) - dt
    if v["wear_t"] <= 0:
        v["wear_t"] = 0.15
        v["wear_ver"] = v.get("wear_ver", 0) + 1
        for hum in v["workers"]:
            if hum.get("dead"):
                continue
            if hum["state"] not in ("walk", "run", "hunt"):
                continue
            key = (round(hum["x"] * 2) / 2, round(hum["y"] * 2) / 2)
            if 0 <= key[0] < GRID_W and 0 <= key[1] < GRID_D:
                v["wear"][key] = min(6.0, v["wear"].get(key, 0.0) + 0.4)
        if len(v["wear"]) > 900:
            for k2 in list(v["wear"]):
                v["wear"][k2] *= 0.97
                if v["wear"][k2] < 0.3:
                    del v["wear"][k2]
    # лес восстанавливается: из пня вырастает новая ёлка
    for tr in G.VIL_TREES:
        o = tr["o"]
        if o.get("dead") == "stump" \
                and v["t"] - o.get("stump_t", 0.0) > 240.0:
            o["dead"] = None
            o["vx"] = o["vy"] = o["vz"] = 0.0
            _vil_puff(v, o["x"] + 0.5, o["y"] + 0.5,
                      _vil_gz(o["x"], o["y"]) + 0.6, small=True)
    # --- люди ---
    _night = G.DAYT >= 0.60 and G.DAYT < 0.97
    for hum in v["workers"]:
        if hum.get("dead"):
            continue
        # рассвет: сон заканчивается (не спать до обеда)
        if not _night and hum.get("act") == "sleep" \
                and hum["state"] == "sit":
            hum["st"] = min(hum["st"], 0.4)
        # ночь: НИКТО на улице — даже работающий идёт спать
        # (факелы не отменяют отдых)
        if _night and v["phase"] == "settle" \
                and hum["state"] not in ("sit", "air", "dead") \
                and not (hum["state"] == "sit"
                         and hum.get("act") == "sleep"):
            spot = _vil_sleep_spot(v, hum)
            if spot is not None:
                if hum.get("carry"):
                    v["sticks"].append(dict(
                        x=hum["x"], y=hum["y"],
                        z=ground_height_at(hum["x"], hum["y"]) or 0.0,
                        vz=0.0, falling=False, t=0.0, owner=None,
                        ang=rng.uniform(0, 6.283)))
                    hum["carry"] = False
                    hum["sticks"] = 0
                _vil_release_prey(v, hum)
                hum["tx"], hum["ty"] = spot
                hum["act"] = "sleep"
                hum["state"] = "walk"
                hum["work_plot"] = -1
                hum["work_job"] = None
        if hum is v["leader"] and ph in ("council", "fire_stones",
                                         "fire_sticks", "fire_light"):
            if ph == "council" and v["t"] < 2.6:
                _vil_worker_step(v, hum, dt)
            else:
                _vil_leader_step(v, hum, dt)
                if hum["state"] in ("walk", "run"):
                    _vil_worker_step(v, hum, dt)
                    if hum["act"] == "log_get" and hum["state"] == "idle":
                        hum["carried_log"] = True
                        hum["state"] = "walk"
                        hum["tx"], hum["ty"] = v["fire"]
                        hum["act"] = "log"
            continue
        _vil_worker_step(v, hum, dt)
        # зомби-страховка: застрял в движении
        if hum["state"] in ("walk", "run") and hum["st"] < 0:
            hum["st"] = 0.2
    # --- люди: отлёты, ранения, кровь, поражение ---
    for hum in v["workers"]:
        if hum.get("dead"):
            continue
        if hum["state"] == "air":
            hum["x"] = clamp(hum["x"] + hum.get("vx", 0.0) * dt,
                             1.0, GRID_W - 1.0)
            hum["y"] = clamp(hum["y"] + hum.get("vy", 0.0) * dt,
                             1.0, GRID_D - 1.0)
            hum["vz"] -= 16.0 * dt
            hum["z"] += hum.get("vz", 0.0) * dt
            gz = _vil_gz(hum["x"], hum["y"])
            if hum["z"] <= gz:
                hum["z"] = gz
                hum["vx"] = hum["vy"] = hum["vz"] = 0.0
                if hum.get("dead_mark"):
                    _vil_human_die(v, hum)
                else:
                    hum["state"] = "stun"
                    hum["st"] = 1.0 + 2.5 * hum.get("air_k", 0.0)
                    hum["act"] = "task"
                    if hum.get("air_k", 0.0) > 0.35:
                        v["blood"].append(dict(x=hum["x"], y=hum["y"],
                                               r=0.10, t=0.0, big=False))
    for b in v["blood"]:
        b["t"] += dt
    v["blood"] = [b for b in v["blood"] if b["t"] < 90.0]
    # участки: проверка разрушений от взрывов
    v["chk_t"] -= dt
    if v["chk_t"] <= 0 and v.get("objects") is not None:
        v["chk_t"] = 0.25
        ids_ = set(id(o) for o in v["objects"])
        for p in v["plots"]:
            if p["state"] not in ("work", "done"):
                continue
            crit = None
            for si in range(p["stage"]):
                stg = p["stages"][si]
                bads = [k for k, ob in enumerate(stg["objs"])
                        if ob is None or id(ob) not in ids_
                        or ob.get("over", 0) >= 3]
                if bads:
                    crit = si
                    break
            if crit is not None:
                _plot_broken(v, p, crit)
                continue
            if p["state"] == "done":
                # лёгкие сколы: зачистка без обломков — дом
                # возвращается в прежний вид
                scr = None
                for s2 in range(p["stage"]):
                    if any(ob is not None and id(ob) in ids_ and (
                            ob.get("over", 0) > 0 or ob.get("chips"))
                           for ob in p["stages"][s2]["objs"]):
                        scr = s2
                        break
                if scr is not None:
                    _plot_broken(v, p, scr, light=True)
    # поражение: всё племя убито
    if v["defeat"] is None and v["phase"] in ("settle",) \
            and not any(h for h in v["workers"] if not h.get("dead")):
        v["defeat"] = G.VIL_T
    # --- дым костра ---
    if v["lit"]:
        v["smoke_t"] += dt
        if v["smoke_t"] >= 0.5 and len(SMOKES) < 110:
            v["smoke_t"] = 0.0
            fx, fy = v["fire"]
            SMOKES.append(dict(x=fx + fx_rng.uniform(-0.05, 0.05),
                               y=fy + fx_rng.uniform(-0.05, 0.05),
                               z=_vil_gz(fx, fy) + 0.55, t=0.0,
                               life=2.6 + fx_rng.random(),
                               r=0.20 + fx_rng.random() * 0.14,
                               c=(120, 108, 96), a=110, rise=1.5))
