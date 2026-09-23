# -*- coding: utf-8 -*-
"""Поселение: состояние, люди, сброс сцены, размещение."""

import math
from game.core import state as G
from game.core.config import (
    GRID_D, GRID_W, rng)
from game.core.utils import (
    clamp, hash01)
from game.world.terrain import (
    ground_height_at)
from game.world.buildings import (
    make_building_library)

# ---------------------------------------------------------------------------
# Люди: первое поселение — вожак, костёр, хижины. «С этого всё начнётся».
# ---------------------------------------------------------------------------
VIL_HUM_SPR = {}    # кэш спрайтов человечков

_HSKIN = (226, 186, 146)
_HHAIR = [(86, 60, 40), (44, 38, 34), (148, 84, 48), (120, 96, 60)]
_HTUNIC = [(126, 88, 54), (158, 116, 62), (110, 118, 96), (128, 64, 52),
           (140, 120, 90)]
_HTUNIC_LEADER = (178, 66, 48)
_HLEGS = (66, 48, 34)
_HBOOTS = (46, 34, 24)


def _vil_pick_site():
    """Плоская поляна в центре острова, поближе к лесу."""
    cands = [(44, 44), (40, 46), (48, 40), (46, 48), (38, 40), (50, 48)]
    best, best_score = None, -1e9
    for cx, cy in cands:
        hs = []
        for dx in (-2, 0, 2):
            for dy in (-2, 0, 2):
                g = ground_height_at(cx + dx, cy + dy)
                if g is not None:
                    hs.append(g)
        if not hs:
            continue
        flat = 1.0 - (max(hs) - min(hs)) * 2.0
        ntrees = sum(1 for t in G.VIL_TREES
                     if math.hypot(t["x"] - cx, t["y"] - cy) < 13)
        score = flat * 4 + min(10, ntrees) * 0.3
        if score > best_score:
            best_score, best = score, (cx, cy)
    return best or (44, 44)


def _vil_make_human(i, x, y):
    z = ground_height_at(x, y) or 0.0
    return dict(id=i, x=x, y=y, z=z, z0=z, tx=x, ty=y,
                state="wander", st=0.5 + (i % 5) * 0.3,
                carry=False, sticks=0,
                hair=_HHAIR[i % 4],
                tunic=_HTUNIC[i % 5],
                ph=i * 1.37, flip=False,
                act="task", work_hut=-1, work_el=-1,
                sit_ang=0.0, idle_t=0.0)


def village_reset(objects=None):
    """Новое поселение: люди прибывают, начинают собирать дрова."""
    G.VIL_TREES = [dict(x=o["x"] + 0.5, y=o["y"] + 0.5, o=o)
                 for o in (objects or []) if o.get("shape") == "tree"]
    cx, cy = _vil_pick_site()
    fx, fy = clamp(cx, 8, GRID_W - 8), clamp(cy, 8, GRID_D - 8)
    # стройка: сначала класс 1 (землянка), потом класс 2 (шкура),
    # далее кольцо — дома каталога (каменный век + раннее дерево)
    lib = make_building_library()
    by_hid = {t["hid"]: t for t in lib}
    roster = [10, 9]  # дальше — динамический план (_vil_planner)
    plots = []
    _pos0 = (fx + 3.4, fy + 1.6)
    _pos1 = (fx - 3.0, fy + 3.2)
    for k, hid_ in enumerate(roster):
        if k < 2:
            px, py = _pos0 if k == 0 else _pos1
        else:
            kk = k - 2
            ang = 0.55 + kk * (6.283 / 14) + hash01(k, fx, 91) * 0.4
            rr = 5.2 + (kk % 3) * 2.3 + hash01(k, fy, 93) * 1.1
            px = clamp(fx + math.cos(ang) * rr, 4, GRID_W - 4)
            py = clamp(fy + math.sin(ang) * rr, 4, GRID_D - 4)
        t = by_hid.get(hid_)
        if t is None:
            continue
        plots.append(dict(idx=k, x=px, y=py, tpl=t, name=t["name"],
                          cls=t["cls"], stages=_village_construction._plot_plan(t), stage=0,
                          st_time=0.0, state="wait", debris=[], jobs=[],
                          broken_from=0, was_done=False, relocs=0))
    v = dict(fire=(fx, fy), plots=plots, pile=(fx + 0.9, fy - 0.9),
             phase="gather", t=0.0, leader=None,
             pile_n=0, stones=0, fire_logs=0,
             workers=[], next_drop=1.5, smoke_t=0.0, lit=False,
             sparks=0, blood=[], parts=[], defeat=None, chk_t=0.0,
             objects=[])
    # --- экономика и уровни (L0: огонь -> L1: все в укрытии + камень
    #     -> L2: мастерская + брёвна; склады и колья) ---
    v["lvl"] = 0
    v["res"] = dict(logs=0, stones=0, spears=0)
    v["logs"] = []            # брёвна: у пня / везут / на складе
    v["logpile"] = (fx + 2.1, fy - 1.7)
    v["stonepile"] = (fx - 2.1, fy + 1.7)
    v["stones_placed"] = []   # камни на складе/куче
    v["pebbles"] = []         # мелкие камни на земле
    for i in range(8):
        ang = hash01(i, cx, 91) * 6.283
        rr = 1.5 + hash01(i, cy, 93) * 7.5
        px = clamp(fx + math.cos(ang) * rr, 2, GRID_W - 2)
        py = clamp(fy + math.sin(ang) * rr, 2, GRID_D - 2)
        v["pebbles"].append(dict(x=px, y=py, z=_vil_gz(px, py),
                                 falling=False, owner=None, t=0.0,
                                 old=False,
                                 ang=hash01(i, cx, 95) * 6.283))
    v["_plots_by_hid"] = {}
    for p in plots:
        h = p["tpl"]["hid"]
        v["_plots_by_hid"][h] = v["_plots_by_hid"].get(h, 0) + 1
    v["_rocks"] = [o for o in (objects or [])
                   if o.get("shape") == "rock"]
    v["plan_t"] = 0.0
    v["solids"] = []
    v["sol_t"] = 0.0
    # еда и охота (L1+): зайцы — палками/камнями, олени — с копьём
    v["food"] = 4.0
    v["animals"] = []
    v["_an_n"] = 0
    v["an_t"] = 3.0
    v["cook_t"] = 0.0
    v["work_mult"] = 1.0
    # вытоптанные тропинки: (плитка) -> износ
    v["wear"] = {}
    v["wear_t"] = 0.0
    v["wear_ver"] = 0
    G.VIL = v
    G.VIL_T = 0.0
    hs = []
    for i in range(10):
        x, y = fx, fy
        for _ in range(40):  # разные точки острова
            x = rng.uniform(6, GRID_W - 6)
            y = rng.uniform(6, GRID_D - 6)
            if ground_height_at(x, y) is None:
                continue
            if 9 < math.hypot(x - fx, y - fy) < 34:
                break
        h = _vil_make_human(i, x, y)
        h["tx"], h["ty"] = fx, fy  # сначала — к костру
        h["state"] = "walk"
        h["act"] = "task"
        h["stone"] = False
        h["torch"] = False
        hs.append(h)
    v["workers"] = hs
    # первые жерди уже лежат на поляне
    v["sticks"] = []
    for i in range(6):
        ang = hash01(i, cx, 77) * 6.283
        rr = 2.0 + hash01(i, cy, 79) * 9.0
        sx = clamp(fx + math.cos(ang) * rr, 2, GRID_W - 2)
        sy = clamp(fy + math.sin(ang) * rr, 2, GRID_D - 2)
        v["sticks"].append(dict(x=sx, y=sy, z=ground_height_at(sx, sy) or 0.0,
                                vz=0.0, falling=False, t=0.0, owner=None,
                                ang=hash01(i, cx, 83) * 6.283))


def _vil_gz(x, y):
    g = ground_height_at(x, y)
    return 0.0 if g is None else g


_VIL_BEDS = {8: 0, 9: 2, 10: 1, 11: 2, 12: 0, 67: 4, 68: 5,
             72: 3}  # 69/70/71 (будка/склады) удалены


def _tpl_size(tpl):
    mx = my = 0.0
    for p in tpl["pieces"]:
        mx = max(mx, p["x"] + p["w"])
        my = max(my, p["y"] + p["d"])
    return mx, my


def _vil_pop(v):
    return sum(1 for h in v["workers"] if not h.get("dead"))


def _vil_beds(v):
    n = 0
    for p in v["plots"]:
        if p["state"] == "done":
            n += _VIL_BEDS.get(p["tpl"]["hid"], 0)
    return n


def _vil_plot_hid(v, hid):
    return any(p["tpl"]["hid"] == hid for p in v["plots"])


def _vil_place(v, tpl):
    """Размещение участка: 24 попытки с отклонениями — не близко к
    огню/деревьям/участкам/валунам; выбор по плоскости + случайность.
    Каждое поселение строится иначе, чем предыдущее."""
    fw, fd = _tpl_size(tpl)
    R = max(fw, fd) / 2 + 0.3
    fx, fy = v["fire"]
    best, best_s = None, -1e9
    trees = [t for t in G.VIL_TREES if not t["o"].get("dead")]
    for _ in range(24):
        a = rng.uniform(0, 6.283)
        rr = 3.4 + rng.uniform(0, 15.0)
        x = clamp(fx + math.cos(a) * rr, 3, GRID_W - 3)
        y = clamp(fy + math.sin(a) * rr, 3, GRID_D - 3)
        hs = []
        for dx, dy in ((-R, 0), (R, 0), (0, -R), (0, R), (0, 0)):
            g = ground_height_at(x + dx, y + dy)
            if g is not None:
                hs.append(g)
        if len(hs) < 3 or max(hs) - min(hs) > 0.9:
            continue
        if math.hypot(x - fx, y - fy) < 3.2:
            continue
        ok = True
        for t in trees:
            if math.hypot(t["x"] - x, t["y"] - y) < 1.6 + R * 0.6:
                ok = False
                break
        if ok:
            for p in v["plots"]:
                pw, pd = _tpl_size(p["tpl"])
                need = (max(fw, fd) + max(pw, pd)) / 2 + 1.7
                if math.hypot(p["x"] - x, p["y"] - y) < need:
                    ok = False
                    break
                # прямоугольники не должны перекрываться (зазор 0.8)
                if (abs(p["x"] + pw / 2 - (x + fw / 2))
                        < (pw + fw) / 2 + 0.8
                        and abs(p["y"] + pd / 2 - (y + fd / 2))
                        < (pd + fd) / 2 + 0.8):
                    ok = False
                    break
        if ok:
            for o in v.get("_rocks", ()):
                if math.hypot(o["x"] - x, o["y"] - y) < 1.5 + R * 0.4:
                    ok = False
                    break
        if not ok:
            continue
        flat = 1.0 - (max(hs) - min(hs))
        sc = flat * 2.0 + rng.uniform(0, 2.5)
        if sc > best_s:
            best_s, best = sc, (x, y)
    if best is None:
        a = rng.uniform(0, 6.283)
        rr = 5.5 + rng.uniform(0, 7.0)
        best = (clamp(fx + math.cos(a) * rr, 4, GRID_W - 4),
                clamp(fy + math.sin(a) * rr, 4, GRID_D - 4))
    return best


def _vil_new_plot(v, hid, pos=None):
    lib = make_building_library()
    t = next((t for t in lib if t["hid"] == hid), None)
    if t is None or v["_plots_by_hid"].get(hid, 0) >= 4:
        return None
    if pos is None:
        pos = _vil_place(v, t)
    k = len(v["plots"])
    v["plots"].append(dict(idx=k, x=pos[0], y=pos[1], tpl=t,
                           name=t["name"], cls=t["cls"],
                           stages=_village_construction._plot_plan(t), stage=0,
                           st_time=0.0, state="wait", debris=[], jobs=[],
                           broken_from=0, was_done=False, relocs=0))
    v["_plots_by_hid"][hid] = v["_plots_by_hid"].get(hid, 0) + 1
    return v["plots"][-1]


# Циклические ссылки на модули выше по цепочке: импорт в конце файла,
# имена используются только внутри функций.
from game.village import construction as _village_construction  # noqa: E402
