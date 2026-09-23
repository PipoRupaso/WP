# -*- coding: utf-8 -*-
"""Планировщик стройки, твёрдые тела, выбор задач жителями."""

import math
from game.core import state as G
from game.core.config import (
    rng)
from game.core.utils import (
    hash01)
from game.village.core import (
    _VIL_BEDS, _tpl_size, _vil_beds, _vil_new_plot, _vil_plot_hid, _vil_pop)

def _vil_planner(v):
    """Уровни и очередь demand: кровати, мастерская, особые постройки."""
    pop = _vil_pop(v)
    beds = _vil_beds(v)
    if v["lit"]:
        lvl = 0
        if beds >= pop and pop > 0 and all(
                h.get("stone") for h in v["workers"]
                if not h.get("dead")):
            lvl = 1
        if (lvl >= 1 and v["res"]["logs"] >= 1
                and any(p["state"] == "done" for p in v["plots"]
                        if p["tpl"]["hid"] == 12)):
            lvl = 2
        v["lvl"] = max(v["lvl"], lvl)
    add = []
    if not _vil_plot_hid(v, 10):
        add.append(10)
    if not _vil_plot_hid(v, 9):
        add.append(9)
    if v["lvl"] >= 1:
        # кухня и мастерская — со второго этапа жизни
        if not _vil_plot_hid(v, 8):
            add.append(8)
        if not _vil_plot_hid(v, 12):
            add.append(12)
    if v["lvl"] < 2:
        planned = beds + sum(_VIL_BEDS.get(p["tpl"]["hid"], 0)
                             for p in v["plots"]
                             if p["state"] != "done")
        if planned < pop:
            pool = (10, 9)
            hid = pool[rng.randint(0, len(pool) - 1)]
            if v["_plots_by_hid"].get(hid, 0) < 4:
                add.append(hid)
    elif v["lvl"] >= 2:
        # дома ур.3-5 — не более двух одновременно: рабочие не распыляются
        n_sp = sum(1 for p in v["plots"]
                   if p["tpl"]["hid"] in (72, 67, 68)
                   and p["state"] != "done")
        if v["_plots_by_hid"].get(72, 0) < 2 and n_sp < 2:
            add.append(72)
        elif v["plan_t"] > 12.0 and rng.random() < 0.5 \
                and n_sp < 2:
            opts = [h for h in (67, 68)
                    if not _vil_plot_hid(v, h)
                    and v["_plots_by_hid"].get(h, 0)
                    < (2 if h == 67 else 1)]
            if opts:
                add.append(opts[rng.randint(0, len(opts) - 1)])
                v["plan_t"] = 0.0
    for hid in add:
        _vil_new_plot(v, hid)


def _vil_solids(v):
    """Твёрдые объекты для коллизий: огонь, участки, деревья."""
    lst = [tuple(v["fire"]) + (0.55,)]
    for p in v["plots"]:
        if p["state"] in ("work", "done", "repair"):
            fw, fd = _tpl_size(p["tpl"])
            lst.append((p["x"] + fw / 2, p["y"] + fd / 2,
                        max(fw, fd) / 2 + 0.18))
    for t in G.VIL_TREES:
        if not t["o"].get("dead") and \
                math.hypot(t["x"] - v["fire"][0],
                           t["y"] - v["fire"][1]) < 22:
            lst.append((t["x"], t["y"], 0.24))
    v["solids"] = lst


def _vil_blocked(v, x, y):
    for sx, sy, r in v["solids"]:
        dx, dy = x - sx, y - sy
        rr = r + 0.10
        if dx * dx + dy * dy < rr * rr:
            return True
    return False


def _vil_pick_tree(v, hum):
    """Ближайшее живое дерево у поселения (один рубящий на дерево)."""
    best, bd = None, 14.0
    fx, fy = v["fire"]
    for t in G.VIL_TREES:
        o = t["o"]
        if o.get("dead") or o.get("chop_by") is not None:
            continue
        d1 = math.hypot(t["x"] - fx, t["y"] - fy)
        if d1 > 13.0:
            continue
        d = math.hypot(t["x"] - hum["x"], t["y"] - hum["y"])
        if d < bd:
            bd, best = d, t
    if best is not None:
        best["o"]["chop_by"] = hum["id"]
    return best


def _vil_sleep_spot(v, hum):
    """Ночёвка: дверь ближайшей готовой хижины, иначе — костёр."""
    beds = 0
    best, bd = None, 1e9
    for p in v["plots"]:
        if p["state"] != "done":
            continue
        if _VIL_BEDS.get(p["tpl"]["hid"], 0) <= 0:
            continue
        beds += _VIL_BEDS[p["tpl"]["hid"]]
        d = math.hypot(p["x"] - hum["x"], p["y"] - hum["y"])
        if d < bd:
            bd, best = d, p
    if best is None:
        return None
    fw, fd = _tpl_size(best["tpl"])
    # полукруг перед дверью: каждый — на своём месте (не в кучу)
    ang = -1.25 + 2.5 * hash01(hum["id"], 3, 7)
    rad = 0.5 + 0.35 * hash01(hum["id"], 5, 11)
    return (best["x"] + fw / 2 + math.sin(ang) * rad,
            best["y"] + fd + 0.15 + abs(math.cos(ang)) * rad * 0.6)


def _vil_pick_task(v, hum):
    """Новое занятие по фазе поселения."""
    ph = v["phase"]
    if v["defeat"] is not None:
        return  # поражены — новых заданий нет
    night = G.DAYT >= 0.60 and G.DAYT < 0.97
    if night and ph == "settle":
        # ночью ВСЕ спят (даже с факелами): в хижине, вне дома никого
        spot = _vil_sleep_spot(v, hum)
        if spot is not None:
            hum["tx"], hum["ty"] = spot
            hum["act"] = "sleep"
            hum["state"] = "walk"
            return
        _vil_send_sit(hum)
        return
    hum["torch"] = night
    if ph == "settle":
        # голод: охота важнее стройки (еда = выживание)
        if v["lvl"] >= 1 and v["food"] < 2.0:
            an = _village_tribe._vil_pick_prey(v, hum)
            if an is not None:
                an["o"]["hunt_by"] = hum["id"]
                if an["kind"] == "deer":
                    hum["spear"] = True
                hum["act"] = "hunt"
                hum["prey"] = id(an)
                hum["tx"], hum["ty"] = an["o"]["x"], an["o"]["y"]
                hum["state"] = "walk"
                return
        # город: ближайший участок на стройку/починку/уборку
        p = _village_construction._vil_next_plot(v, hum)
        if p is not None:
            _village_construction._vil_assign_plot(v, p, hum)
            if hum["act"] in ("build", "clean", "repair") \
                    and hum["state"] == "walk":
                return
    if ph in ("gather", "settle"):
        # жердь рядом?
        stick = None
        bd = 14.0
        for s in v["sticks"]:
            if s["owner"] is not None or s["falling"]:
                continue
            d = math.hypot(s["x"] - hum["x"], s["y"] - hum["y"])
            if d < bd:
                bd, stick = d, s
        _pcap = 1 if v["lvl"] >= 1 else 4
        if stick is not None and (ph != "settle"
                                  or v["pile_n"] < _pcap):
            stick["owner"] = hum["id"]
            hum["act"] = "to_stick"
            hum["tx"], hum["ty"] = stick["x"], stick["y"]
            hum["state"] = "walk"
            return
        # L1: каждому нужен камень с земли (тогда можно рубить)
        if v["lit"] and not hum["stone"] and ph == "settle":
            pb = None
            bd = 12.0
            for s2 in v["pebbles"]:
                if s2["owner"] is not None:
                    continue
                d = math.hypot(s2["x"] - hum["x"], s2["y"] - hum["y"])
                if d < bd:
                    bd, pb = d, s2
            if pb is not None:
                pb["owner"] = hum["id"]
                hum["act"] = "to_pebble"
                hum["tx"], hum["ty"] = pb["x"], pb["y"]
                hum["state"] = "walk"
                return
        # L1: сначала везём срубленные брёвна, потом рубим дальше
        if v["lvl"] >= 1 and ph == "settle":
            lo = None
            bd = 20.0
            for lg in v["logs"]:
                if lg["owner"] is not None or lg["placed"]:
                    continue
                d = math.hypot(lg["x"] - hum["x"], lg["y"] - hum["y"])
                if d < bd:
                    bd, lo = d, lg
            if lo is not None:
                lo["owner"] = hum["id"]
                hum["act"] = "to_log"
                hum["log"] = lo
                hum["tx"], hum["ty"] = lo["x"], lo["y"]
                hum["state"] = "walk"
                return
        # L1+: охота, чтобы выжить (заяц — палкой/камнем,
        # олень — только с копьём)
        if v["lvl"] >= 1 and ph == "settle" \
                and v["food"] < _vil_pop(v) * 1.5:
            an = _village_tribe._vil_pick_prey(v, hum)
            if an is not None:
                an["o"]["hunt_by"] = hum["id"]
                if an["kind"] == "deer":
                    hum["spear"] = True
                hum["act"] = "hunt"
                hum["prey"] = id(an)
                hum["tx"], hum["ty"] = an["o"]["x"], an["o"]["y"]
                hum["state"] = "walk"
                return
        # L2: камень в склад — каждый третий идёт на склад,
        # остальные — только если никто на склад не идёт
        if v["lvl"] >= 2 and ph == "settle" and \
                v["res"]["stones"] < 36:
            _spn = sum(1 for h in v["workers"] if not h.get("dead")
                       and (h.get("sp") is not None
                            or h.get("act") == "to_sp"))
            if hum["id"] % 3 == 0 or _spn == 0:
                sp = None
                bd = 16.0
                for s2 in v["pebbles"]:
                    if s2["owner"] is not None:
                        continue
                    d = math.hypot(s2["x"] - hum["x"],
                                   s2["y"] - hum["y"])
                    if d < bd:
                        bd, sp = d, s2
                if sp is not None:
                    sp["owner"] = hum["id"]
                    hum["act"] = "to_sp"
                    hum["sp"] = sp
                    hum["tx"], hum["ty"] = sp["x"], sp["y"]
                    hum["state"] = "walk"
                    return
        # L1: рубка дерева камнем -> пенёк + 2 бревна
        if v["lvl"] >= 1 and hum["stone"] and ph == "settle":
            t = _vil_pick_tree(v, hum)
            if t is not None:
                hum["act"] = "to_tree"
                hum["tree"] = id(t["o"])
                hum["tx"] = t["x"] + 0.1
                hum["ty"] = t["y"] + 0.3
                hum["state"] = "walk"
                return
        # сидеть у огня (лимит — трое)
        if ph in ("settle", "hut1", "hut2") and v["lit"]:
            sitting = sum(1 for h in v["workers"] if h["state"] == "sit")
            if sitting < 2 and hash01(G.VIL_T, hum["id"], 5) < 0.22:
                _vil_send_sit(hum)
                return
        # слоняться возле поселения
        fx, fy = v["fire"]
        ang = hash01(G.VIL_T, hum["id"], 9) * 6.283
        rr = 0.8 + hash01(G.VIL_T, hum["id"], 11) * 2.6
        hum["act"] = "task"
        hum["tx"] = fx + math.cos(ang) * rr
        hum["ty"] = fy + math.sin(ang) * rr
        hum["state"] = "walk"
    elif ph == "council":
        fx, fy = v["fire"]
        i = hum["id"]
        ang = i * 6.283 / 10 + 0.31
        hum["act"] = "council"
        hum["tx"] = fx + math.cos(ang) * 1.7
        hum["ty"] = fy + math.sin(ang) * 1.7
        hum["state"] = "walk"
    else:
        fx, fy = v["fire"]
        hum["act"] = "task"
        hum["tx"] = fx + (hash01(hum["id"], 3, 13) - 0.5) * 4.0
        hum["ty"] = fy + (hash01(hum["id"], 5, 15) - 0.5) * 4.0
        hum["state"] = "walk"


def _vil_send_sit(hum):
    fx, fy = G.VIL["fire"]
    if hum["sit_ang"] == 0.0:
        hum["sit_ang"] = (1.2 + hash01(hum["id"], 7, 17) * 5.0)
    ang = hum["sit_ang"]
    hum["tx"] = fx + math.cos(ang) * 0.75
    hum["ty"] = fy + math.sin(ang) * 0.75
    hum["act"] = "sit"
    hum["state"] = "walk"


def _vil_arrive(v, hum):
    act = hum["act"]
    if act == "to_stick":
        s = next((s for s in v["sticks"] if s["owner"] == hum["id"]), None)
        if s is None:
            _vil_pick_task(v, hum)
            return
        hum["state"] = "pick"
        hum["st"] = 0.7
    elif act == "to_pile":
        hum["state"] = "drop"
        hum["st"] = 0.55
    elif act == "sit":
        hum["state"] = "sit"
        hum["st"] = 3.5 + hash01(hum["id"], hum["sit_ang"], 19) * 4.5
    elif act == "council":
        hum["state"] = "idle"
    elif act in ("build", "repair"):
        hum["state"] = "work"
    elif act == "clean":
        hum["state"] = "clean"
    elif act == "stone":
        hum["state"] = "place"
        hum["st"] = 0.85
    elif act == "log":
        hum["state"] = "place"
        hum["st"] = 1.0
    elif act == "light":
        hum["state"] = "light"
        hum["st"] = 2.2
    elif act == "leader_walk":
        hum["state"] = "idle"
        hum["st"] = 0.9
    elif act == "log_get":
        hum["state"] = "idle"
        hum["st"] = 0.45
    elif act == "to_pebble":
        hum["state"] = "pebble"
        hum["st"] = 0.6
    elif act == "to_tree":
        hum["state"] = "chop"
        hum["st"] = 2.6
    elif act == "to_log":
        hum["state"] = "pick_log"
        hum["st"] = 0.7
    elif act == "to_sp":
        hum["state"] = "pick_sp"
        hum["st"] = 0.6
    elif act == "drop_log":
        hum["state"] = "drop_log"
        hum["st"] = 0.6
    elif act == "drop_sp":
        hum["state"] = "drop_sp"
        hum["st"] = 0.6
    elif act == "sleep":
        hum["state"] = "sit"
        hum["st"] = 150.0
    else:
        hum["state"] = "idle"
        hum["st"] = 0.4


def _vil_log_depot(v):
    p = next((p for p in v["plots"] if p["tpl"]["hid"] == 71), None)
    base = (p["x"] + 0.5, p["y"] + 0.7) if p is not None \
        else v["logpile"]
    n = sum(1 for lg in v["logs"] if lg["placed"])
    return (base[0] + (n % 3) * 0.28, base[1] + (n // 3) * 0.12)


def _vil_stone_depot(v):
    p = next((p for p in v["plots"] if p["tpl"]["hid"] == 70), None)
    base = (p["x"] + 0.5, p["y"] + 0.7) if p is not None \
        else v["stonepile"]
    n = len(v["stones_placed"])
    return (base[0] + (n % 4) * 0.16, base[1] + (n // 4) * 0.14)


# Циклические ссылки на модули выше по цепочке: импорт в конце файла,
# имена используются только внутри функций.
from game.village import construction as _village_construction  # noqa: E402
from game.village import tribe as _village_tribe  # noqa: E402
