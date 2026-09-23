# -*- coding: utf-8 -*-
"""Стройка/ремонт домов поэтапно, гибель людей."""

import math
from game.core.config import (
    GRID_D, GRID_W, rng)
from game.core.utils import (
    clamp, hash01)
from game.world.world_state import (
    SMOKES, fx_rng)
from game.village.core import (
    _vil_gz)

def _plot_plan(tpl):
    # Порядок сборки: фундамент -> полы -> стены -> крыша -> внутреннее.
    # Каждый этап — 1-3 детали (видно, как появляется каркас и т.д.)
    pcs = [dict(p) for p in tpl["pieces"]]

    def rank(p):
        sh = p.get("shape", "box")
        z = p["z"]
        if sh in ("gable", "pyramid"):
            return (3, z)
        if p.get("inside"):
            return (4, z)
        if z < 0.09:
            return (0, z)
        if p.get("h", 0) < 0.08:
            return (1, z)
        return (2, z)

    pcs.sort(key=rank)
    per = 1 if len(pcs) <= 7 else (2 if len(pcs) <= 14 else 3)
    stages = []
    i = 0
    while i < len(pcs):
        stg = pcs[i:i + per]
        stages.append(dict(pieces=stg, objs=[None] * len(stg)))
        i += per
    return stages


def _plot_spawn_stage(v, p):
    z0 = _vil_gz(p["x"], p["y"])
    stg = p["stages"][p["stage"]]
    for k, pc in enumerate(stg["pieces"]):
        q = dict(pc)
        q["x"] = p["x"] + pc["x"]
        q["y"] = p["y"] + pc["y"]
        q["z"] = z0 + pc["z"]
        q["vx"] = q["vy"] = q["vz"] = 0.0
        q["house"] = 0
        q["vid"] = p["idx"]
        q["erode"] = q.get("erode", 1.0) * 0.55  # стройка хрупче
        q.pop("house_total", None)
        v["objects"].append(q)
        stg["objs"][k] = q
        _vil_puff(v, p["x"] + pc["x"] + pc["w"] / 2,
                  p["y"] + pc["y"] + pc["d"] / 2, z0 + pc["h"])
    p["stage"] += 1
    if p["stage"] >= len(p["stages"]):
        p["state"] = "done"
        p["was_done"] = True


def _vil_puff(v, wx, wy, wz, small=False):
    SMOKES.append(dict(x=wx, y=wy, z=wz + 0.05, t=0.0,
                       life=(0.35 + fx_rng.random() * 0.25) if small
                       else 0.8 + fx_rng.random() * 0.5,
                       r=(0.09 + fx_rng.random() * 0.05) if small
                       else 0.16 + fx_rng.random() * 0.1,
                       c=(196, 178, 140), a=100,
                       rise=0.5 if small else 0.8))


def _vil_next_plot(v, hum=None):
    cands = []
    for p in v["plots"]:
        if p["state"] == "clear":
            cands.append((0, p))
        elif p["state"] in ("work", "wait") \
                and p["stage"] < len(p["stages"]):
            cands.append((1, p))
        elif p["state"] == "repair" and p["jobs"]:
            cands.append((1, p))
        else:
            continue
    if not cands:
        return None

    def dist(p):
        hx = hum["x"] if hum is not None else v["fire"][0]
        hy = hum["y"] if hum is not None else v["fire"][1]
        return math.hypot(p["x"] - hx, p["y"] - hy)

    cands.sort(key=lambda t: (t[0], dist(t[1])))
    return cands[0][1]


def _vil_assign_plot(v, p, hum=None):
    busy = sum(1 for h in v["workers"]
               if h.get("work_plot") == p["idx"]
               and h["state"] in ("walk", "run", "work", "place", "clean")
               and h.get("act") in ("build", "clean", "repair"))
    if p["state"] == "clear":
        if not p["debris"] or busy >= 2:
            return
        d = p["debris"][0]
        spot = (d["x"], d["y"])
        job, st = "clean", 0.7
    elif p["state"] == "repair":
        if not p["jobs"] or busy >= 4:
            return
        pc = p["jobs"][0]["piece"]
        spot = (p["x"] + pc["x"] + pc["w"] / 2 + 0.2,
                p["y"] + pc["y"] + pc["d"] / 2 + 0.2)
        job = "repair"
        st = 0.7 + pc["h"] * 0.8
    else:
        if p["stage"] >= len(p["stages"]) or busy >= 3:
            return
        # стоимость этапа: 1 жердь (ур.0) / 1 бревно (ур.1+)
        if v["lvl"] == 0:
            if v["pile_n"] < 1:
                return
            v["pile_n"] -= 1
        else:
            if v["res"]["logs"] < 1:
                return
            v["res"]["logs"] -= 1
            lo = next((l for l in reversed(v["logs"])
                       if l["placed"]), None)
            if lo is not None:
                v["logs"].remove(lo)
        pc = p["stages"][p["stage"]]["pieces"][0]
        spot = (p["x"] + pc["x"] + pc["w"] / 2 + 0.3,
                p["y"] + pc["y"] + pc["d"] / 2 + 0.3)
        job = "build"
        st = 0.5 + 0.13 * len(p["stages"][p["stage"]]["pieces"])
        p["state"] = "work"
    order = ([hum] if hum is not None else []) + \
        [h for h in v["workers"] if h is not hum]
    for h in order:
        if h.get("dead"):
            continue
        if h is v["leader"] and v["phase"] in ("council", "fire_stones",
                                               "fire_sticks",
                                               "fire_light"):
            continue
        if h["state"] in ("work", "place", "light", "sit", "air", "stun",
                          "pick", "drop"):
            continue
        if h is hum and hum["state"] not in ("walk", "run", "idle"):
            continue
        _village_tribe._vil_release_prey(v, h)
        h["work_plot"], h["work_job"] = p["idx"], job
        h["work_el"] = p["stage"]
        h["tx"], h["ty"] = spot
        h["act"] = job
        h["state"] = "walk"
        h["st"] = st
        return


def _vil_work_done(v, hum):
    """Рабочий закончил этап стройки/починки/уборки."""
    job = hum.get("work_job")
    p = None
    if job in ("build", "clean", "repair"):
        pi = hum.get("work_plot", -1)
        if 0 <= pi < len(v["plots"]):
            p = v["plots"][pi]
    if p is not None and job == "build" and p["state"] == "work" \
            and hum.get("work_el", -1) == p["stage"]:
        _plot_spawn_stage(v, p)
    elif p is not None and job == "repair" and p["state"] == "repair" \
            and p["jobs"]:
        j = p["jobs"][0]
        z0 = _vil_gz(p["x"], p["y"])
        pc = j["piece"]
        q = dict(pc)
        q["x"] = p["x"] + pc["x"]
        q["y"] = p["y"] + pc["y"]
        q["z"] = z0 + pc["z"]
        q["vx"] = q["vy"] = q["vz"] = 0.0
        q["house"] = 0
        q["vid"] = p["idx"]
        q["erode"] = q.get("erode", 1.0)
        v["objects"].append(q)
        # фиксируем новую деталь в этапе — иначе чек снова посчитает
        # её пропавшей и дом будет «чиниться» вечно
        p["stages"][j["si"]]["objs"][j["k"]] = q
        _vil_puff(v, p["x"] + pc["x"] + pc["w"] / 2,
                  p["y"] + pc["y"] + pc["d"] / 2, z0 + pc["h"])
        p["jobs"].pop(0)
        if not p["jobs"]:
            p["state"] = "done"
    elif p is not None and job == "clean" and p["state"] == "clear" \
            and p["debris"]:
        d = p["debris"][0]
        try:
            v["objects"].remove(d["o"])
        except ValueError:
            pass
        _vil_puff(v, d["x"], d["y"], _vil_gz(d["x"], d["y"]) + 0.05)
        p["debris"].pop(0)
        if not p["debris"]:
            _plot_after_clear(v, p)
    hum["state"] = "idle"
    hum["st"] = 0.35
    hum["act"] = "task"
    hum["work_plot"] = -1
    hum["work_job"] = None


def _plot_broken(v, p, si, light=False):
    # взрыв повредил построенный этап: уборка обломков, потом — заново
    # или починка (для готового дома)
    p["was_done"] = p["state"] == "done"
    if light and p["state"] == "done":
        # лёгкие сколы: без обломков — сразу зачистка всех этапов
        # (дом возвращается в прежний вид)
        p["broken_from"] = 0
        _plot_after_clear(v, p)
        return
    p["state"] = "clear"
    p["broken_from"] = si
    stg = p["stages"][si]
    pc0 = stg["pieces"][0]
    ox = p["x"] + pc0["x"] + pc0["w"] / 2
    oy = p["y"] + pc0["y"] + pc0["d"] / 2
    for k in range(4 + rng.randint(0, 3)):
        wx = clamp(ox + rng.uniform(-0.8, 0.8), 1, GRID_W - 1)
        wy = clamp(oy + rng.uniform(-0.7, 0.7), 1, GRID_D - 1)
        q = dict(x=wx, y=wy, z=0.0,
                 w=rng.uniform(0.05, 0.11), d=rng.uniform(0.05, 0.11),
                 h=rng.uniform(0.04, 0.09),
                 color=rng.choice(["wood_dark", "plank_light",
                                   "plank_dark"]),
                 shape="box",
                 mat=rng.choice(["plank_dark", "plank_light", "wood_dark"]),
                 vx=0.0, vy=0.0, vz=0.0, erode=9.0, vox=0.06,
                 sort_min=True, rubble=True, vid=p["idx"])
        q["z"] = _vil_gz(wx, wy) - 0.01
        v["objects"].append(q)
        p["debris"].append(dict(x=wx, y=wy, o=q))
    # дым рухнувших деталей
    _vil_puff(v, ox, oy, _vil_gz(ox, oy) + 0.4)


def _plot_after_clear(v, p):
    ids_ = set(id(o) for o in v["objects"])
    if p["was_done"]:
        # готовый дом: починка — поштучно, этапами; сколы на
        # выживших деталях зачищаются — дом возвращается в прежний вид
        p["state"] = "repair"
        p["jobs"] = []
        for si in range(p["broken_from"], p["stage"]):
            stg = p["stages"][si]
            for k, (pc, ob) in enumerate(zip(stg["pieces"],
                                             stg["objs"])):
                bad = ob is None or id(ob) not in ids_ \
                    or ob.get("over", 0) >= 3
                if bad:
                    if ob is not None and id(ob) in ids_:
                        try:
                            v["objects"].remove(ob)
                        except ValueError:
                            pass
                        _vil_puff(v, ob["x"] + ob["w"] / 2,
                                  ob["y"] + ob["d"] / 2,
                                  ob["z"] + ob["h"] / 2)
                    stg["objs"][k] = None
                    p["jobs"].append(dict(piece=pc, si=si, k=k))
                elif ob is not None and (ob.get("over", 0) > 0
                                         or ob.get("chips")):
                    ob["over"] = 0
                    if ob.get("chips"):
                        ob["chips"].clear()
                    _vil_puff(v, ob["x"] + ob["w"] / 2,
                              ob["y"] + ob["d"] / 2,
                              ob["z"] + ob["h"] * 0.7,
                              small=True)
        p["jobs"].sort(key=lambda j: j["si"])
        if not p["jobs"]:
            p["state"] = "done"
            return
        p["state"] = "repair"
        return
    # недостроенный: снос остатков сломанных этапов, стройка заново
    for si in range(p["broken_from"], p["stage"]):
        for ob in p["stages"][si]["objs"]:
            if ob is not None and id(ob) in ids_:
                try:
                    v["objects"].remove(ob)
                except ValueError:
                    pass
                _vil_puff(v, ob["x"] + ob["w"] / 2, ob["y"] + ob["d"] / 2,
                          ob["z"] + ob["h"] / 2)
        p["stages"][si]["objs"] = [None] * len(p["stages"][si]["pieces"])
    p["stage"] = p["broken_from"]
    p["relocs"] += 1
    if p["relocs"] > 2:
        # уперлись в обломки — перебираемся на новое место
        fx, fy = v["fire"]
        ang = math.atan2(p["y"] - fy, p["x"] - fx) + 0.6
        rr = 5.0 + hash01(p["idx"], p["relocs"], 3) * 6.0
        p["x"] = clamp(fx + math.cos(ang) * rr, 4, GRID_W - 4)
        p["y"] = clamp(fy + math.sin(ang) * rr, 4, GRID_D - 4)
    p["state"] = "work"


def _vil_phase_hut(v):
    # огонь зажжён — начинаем город
    v["phase"] = "settle"
    v["t"] = 0.0


def _vil_human_die(v, hum):
    hum["dead"] = True
    hum["state"] = "dead"
    _village_tribe._vil_release_prey(v, hum)
    v["blood"].append(dict(x=hum["x"], y=hum["y"], r=0.34, t=0.0,
                           big=True))
    v["blood"].append(dict(x=hum["x"] + 0.18, y=hum["y"] - 0.12, r=0.13,
                           t=0.0, big=False))
    # обрывки — полноценные объекты мира: падают, остаются лежать
    # и при новом взрыве разрушаются так же, как всё остальное
    objs = v.get("objects")
    if objs is None:
        return
    dvx, dvy, dvz = hum.get("dvx", 0.0), hum.get("dvy", 0.0), \
        hum.get("dvz", 0.0)
    dl = max(0.4, math.hypot(dvx, dvy, dvz))
    ux, uy, uz = dvx / dl, dvy / dl, max(0.25, dvz / dl)
    cols = ["bone", "bone", "leather", "leather", "wood_dark", "bone",
            "leather"]
    for k in range(7):
        _a = rng.uniform(0, 6.28)
        _s = rng.uniform(0.9, 2.4)
        objs.append(dict(
            x=clamp(hum["x"] + math.cos(_a) * 0.06, 1, GRID_W - 1),
            y=clamp(hum["y"] + math.sin(_a) * 0.06, 1, GRID_D - 1),
            z=hum["z"] + 0.05,
            w=rng.uniform(0.05, 0.10), d=rng.uniform(0.04, 0.08),
            h=rng.uniform(0.04, 0.08),
            color=cols[k], shape="box", mat="stone",
            vx=ux * _s + rng.uniform(-1.2, 1.2),
            vy=uy * _s + rng.uniform(-1.2, 1.2),
            vz=uz * _s * 0.6 + rng.uniform(1.0, 3.5),
            erode=0.8, vox=0.05, sort_min=True, body_part=True))


# Циклические ссылки на модули выше по цепочке: импорт в конце файла,
# имена используются только внутри функций.
from game.village import tribe as _village_tribe  # noqa: E402
