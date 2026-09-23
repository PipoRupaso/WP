# -*- coding: utf-8 -*-
"""Взрывы, воронки, урон домам."""

import math
from game.core import state as G
from game.core.config import (
    BURN_MATS, GRASS, GRID_D, GRID_W, MIN_H, rng)
from game.world.world_state import (
    DUST, FLAMES, FLASHES, HOUSE_DMG, HOUSE_TOTAL, LIGHTS_OFF,
    LIGHTS_OFF_FRACTION, RINGS, SMOKES, SPARKS, WIND, _CRATER_TILES,
    _STATIC_REQ, bump_world, fx_rng)
from game.render.lighting import (
    shade, tilt_normal, tone)
from game.world.terrain import (
    ground_height_at, height_normal_at)
from game.sim.pixels import (
    add_pixel, add_shard, object_chip_grid)
from game.sim.chipping import (
    chip_object)
from game.sim.picking import (
    _pick_index)

def _dent_crater(wx, wy, R):
    """Вмятины + клетки перекраски только в радиусе воронки."""
    x0 = max(0, int(wx - R) - 2)
    x1 = min(GRID_W - 1, int(wx + R) + 2)
    y0 = max(0, int(wy - R) - 2)
    y1 = min(GRID_D - 1, int(wy + R) + 2)
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            d = math.hypot(x + 0.5 - wx, y + 0.5 - wy)
            if d >= R + 1.8:
                continue
            _CRATER_TILES.add((x, y))
            if R - 0.5 <= d < R + 1.8:  # вал выброса
                lip = 0.10 * (1 - (d - R + 0.5) / 2.3)
                G.GH[y][x] += lip * 0.5
                G.GH[y][x + 1] += lip * 0.5
                G.GH[y + 1][x] += lip * 0.5
                G.GH[y + 1][x + 1] += lip * 0.5
                G._RIMTILES.add((x, y))
            dig = max(G.BASE_H[y][x] - G.GH[y][x],
                      G.BASE_H[y][x + 1] - G.GH[y][x + 1],
                      G.BASE_H[y + 1][x] - G.GH[y + 1][x],
                      G.BASE_H[y + 1][x + 1] - G.GH[y + 1][x + 1])
            if dig > 0.03:
                G.DENTED.add((x, y))
                G._RIMTILES.discard((x, y))


def _seg_aabb(x0, y0, x1, y1, ax0, ay0, ax1, ay1):
    """Отрезок пересекает AABB (slab-тест, 2D)."""
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, d, lo, hi in ((x0, dx, ax0, ax1), (y0, dy, ay0, ay1)):
        if abs(d) < 1e-9:
            if p < lo or p > hi:
                return False
        else:
            ta, tb = (lo - p) / d, (hi - p) / d
            t0 = max(t0, min(ta, tb))
            t1 = min(t1, max(ta, tb))
            if t0 > t1:
                return False
    return t0 < 0.999 and t1 > 0.001


def _house_shielded(objects, o, bx, by, bz):
    """Мебель/пол внутри дома: взрыв снаружи за целыми стенами не берёт."""
    hid = o.get("house")
    if hid is None or o.get("inside") is not True:
        return False
    cx, cy = o["x"] + o["w"] / 2, o["y"] + o["d"] / 2
    for w in objects:
        if w is o or w.get("house") != hid or w.get("inside") is True:
            continue
        if w.get("shape") == "gable":
            continue  # крыша — отдельно, только сверху
        if w["z"] + w["h"] <= min(bz, o["z"] + o["h"]) + 1e-6:
            continue  # стена целиком ниже линии взрыва — не щит
        if _seg_aabb(bx, by, cx, cy, w["x"], w["y"],
                     w["x"] + w["w"], w["y"] + w["d"]):
            return True
    if bz > o["z"] + o["h"] + 0.5:
        for w in objects:
            if w.get("house") != hid or w.get("shape") != "gable":
                continue
            g = w.get("_chipgrid")
            if g is None:
                return True  # крыша цела — держит удар сверху
            if len(w.get("chips", ())) < 0.5 * len(g["cells"]):
                return True
    return False


def _house_damage_add(objects, hid, cells_gone):
    """Нарастить урон дома; при 30%+ его свет больше не зажигается."""
    if not hid or cells_gone <= 0:
        return
    if hid not in HOUSE_TOTAL:
        HOUSE_TOTAL[hid] = sum(len(object_chip_grid(o)["cells"])
                               for o in objects if o.get("house") == hid)
    HOUSE_DMG[hid] = HOUSE_DMG.get(hid, 0) + cells_gone
    if HOUSE_DMG[hid] >= LIGHTS_OFF_FRACTION * max(1, HOUSE_TOTAL[hid]):
        LIGHTS_OFF.add(hid)


def _landing_dust(o, sup):
    """Приземление куска: слабый, еле заметный веер пыли."""
    for _ in range(4):
        DUST.append(dict(x=o["x"] + o["w"] * fx_rng.random(),
                         y=o["y"] + o["d"] * fx_rng.random(),
                         z=sup + 0.12, t=0.0,
                         life=0.5 + fx_rng.random() * 0.4,
                         r=0.26 + fx_rng.random() * 0.2,
                         c=(118, 106, 88), a=80))
        if len(DUST) > 240:
            del DUST[:len(DUST) - 240]


def explode(cam, objects, pixels, wx, wy, power=1.0, bz=0.3):
    # Сколы меняют картинку, но не геометрию опор. Раньше каждый
    # взрыв зря инвалидировал физический индекс всех ~1900 объектов.
    G.STATIC_VER += 1
    _nobj = len(objects)
    R = 1.5 * power + 0.4
    # мелкая воронка (с высоты — слабее)
    depth = 0.45 * power * max(0.3, 1.0 - max(0.0, bz - 0.3) * 0.25)
    _cx0 = max(0, int(wx - R) - 1)
    _cx1 = min(GRID_W, int(wx + R) + 1)
    _cy0 = max(0, int(wy - R) - 1)
    _cy1 = min(GRID_D, int(wy + R) + 1)
    for cy in range(_cy0, _cy1 + 1):
        for cx in range(_cx0, _cx1 + 1):
            d = math.hypot(cx - wx, cy - wy)
            if d < R:
                G.GH[cy][cx] = max(MIN_H, G.GH[cy][cx] - depth * (1 - d / R))
    _dent_crater(wx, wy, R)

    # Взрыв трогает только соседние ячейки. Индекс уже прогрет в
    # pick_blast_point(), поэтому здесь нет линейного обхода всего мира.
    search_r = R * 2.5 + 2.0
    grid = _pick_index(objects)
    candidates, seen_ids = [], set()
    for ix in range(math.floor(wx - search_r), math.floor(wx + search_r) + 1):
        for iy in range(math.floor(wy - search_r),
                        math.floor(wy + search_r) + 1):
            for o in grid.get((ix, iy), ()):
                oid = id(o)
                if oid not in seen_ids:
                    seen_ids.add(oid)
                    candidates.append(o)
    candidates.sort(key=lambda _o: 0 if _o.get("inside") is True else 1)
    for o in candidates:
        # расстояние от центра взрыва до бокса (3D)
        dx = max(o["x"] - wx, 0.0, wx - (o["x"] + o["w"]))
        dy = max(o["y"] - wy, 0.0, wy - (o["y"] + o["d"]))
        dz = max(o["z"] - bz, 0.0, bz - (o["z"] + o["h"]))
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        lim = R * 2.5 + 2.0 if o.get("shape") == "tree" else R + 0.6
        if dist < lim:
            # фигуры стоят на месте — только сколы (на краю радиуса царапина)
            if _house_shielded(candidates, o, wx, wy, bz):
                continue
            chip_object(objects, pixels, o, wx, wy, bz, R, power, dist)

    if len(objects) != _nobj:
        bump_world()
        _STATIC_REQ["full"] = True  # обрушение: тени поменялись
    else:
        # Рельеф изменился только у воронки: распаковываем лишь ближние
        # тела, чтобы они могли упасть в яму.
        for o in candidates:
            if o.get("shape") != "tree" and o.get("park_v") is not None:
                dx = max(o["x"] - wx, 0.0, wx - (o["x"] + o["w"]))
                dy = max(o["y"] - wy, 0.0, wy - (o["y"] + o["d"]))
                if dx * dx + dy * dy < (R + 1.8) ** 2:
                    o["park_v"] = None
    # --- люди: выброс взрывной волной ---
    if G.VIL is not None:
        for h in G.VIL["workers"]:
            if h.get("dead"):
                continue
            d = math.hypot(h["x"] - wx, h["y"] - wy)
            if d < R + 0.5:
                if d < 0.02:
                    d = 0.02
                    ux, uy = 0.7, 0.7
                else:
                    ux, uy = (h["x"] - wx) / d, (h["y"] - wy) / d
                fall = max(0.0, 1.0 - d / (R + 0.5))
                h["vx"] = h.get("vx", 0.0) + ux * (3.0 + 5.5 * power) * fall
                h["vy"] = h.get("vy", 0.0) + uy * (3.0 + 5.5 * power) * fall
                h["vz"] = h.get("vz", 0.0) + (2.0 + 4.5 * power) * fall
                h["air_k"] = fall * power
                h["dead_mark"] = fall * power > 0.5
                h["dvx"], h["dvy"], h["dvz"] = h["vx"], h["vy"], h["vz"]
                h["state"] = "air"
                h["act"] = "task"
                h["work_plot"] = -1
                # кровь разлетается вместе с обрывками сразу при взрыве
                if fall > 0.28:
                    for _k in range(int(8 + 12 * fall)):
                        _a = rng.uniform(0, 6.283)
                        _sp = (1.5 + rng.random() * 4.0) * (0.4 + fall)
                        add_pixel(pixels,
                                  h["x"] + rng.uniform(-0.08, 0.08),
                                  h["y"] + rng.uniform(-0.08, 0.08),
                                  h["z"] + 0.07,
                                  ux * _sp * 0.6
                                  + math.cos(_a) * _sp * 0.7,
                                  uy * _sp * 0.6
                                  + math.sin(_a) * _sp * 0.7,
                                  (2.0 + rng.random() * 4.5) * fall,
                                  3, (128, 18, 16))
                    for _k in range(3):
                        _a = rng.uniform(0, 6.283)
                        _rr = rng.uniform(0.25, 0.9) * (0.5 + fall)
                        G.VIL["blood"].append(dict(
                            x=h["x"] + math.cos(_a) * _rr,
                            y=h["y"] + math.sin(_a) * _rr,
                            r=0.05 + rng.random() * 0.07 * fall, t=0.0,
                            big=False))
                    # смертельный удар: человек разрушается СРАЗУ —
                    # обрывки летят от центра взрыва вместе с кровью
                    if h["dead_mark"]:
                        _village_construction._vil_human_die(G.VIL, h)
    # пиксели земли из воронки (меньше, когда мусора и так толпа)
    _q = 1.0 if len(pixels) < 500 else (0.6 if len(pixels) < 800 else 0.35)
    n_ground = int((30 * power + 15) * _q)
    for _ in range(n_ground):
        ang = rng.uniform(0, math.pi * 2)
        rr = rng.random() * R * 0.8
        gx, gy = wx + math.cos(ang) * rr, wy + math.sin(ang) * rr
        if not (0 <= gx < GRID_W and 0 <= gy < GRID_D):
            continue
        tx, ty = int(gx), int(gy)
        gz = ground_height_at(gx, gy) or 0.0
        is_dirt = False
        raw = GRASS
        n = height_normal_at(tx, ty)
        nn = tilt_normal(n, int(gx * 31), int(gy * 17), 9, 0.7)
        col = tone(shade(raw, nn), 0.8 + rng.random() * 0.4)
        sp = (2.0 + rng.random() * 4.0) * power
        add_pixel(pixels, gx, gy, gz + 0.1,
                  math.cos(ang) * sp, math.sin(ang) * sp,
                  (3.4 + rng.random() * 5.4) * (0.55 + 0.45 * power),
                  3 if rng.random() < 0.6 else 4, col)

    # рваные куски земли: связные комки пикселей
    n_blobs = 2 + int(power)
    for _ in range(n_blobs):
        ang = rng.uniform(0, math.pi * 2)
        rr = rng.uniform(0.2, R * 0.6)
        gx, gy = wx + math.cos(ang) * rr, wy + math.sin(ang) * rr
        if not (0 <= gx < GRID_W and 0 <= gy < GRID_D):
            continue
        tx, ty = int(gx), int(gy)
        gz = ground_height_at(gx, gy) or 0.0
        raw = GRASS
        n = height_normal_at(tx, ty)
        sp = (2.0 + rng.random() * 2.5) * power
        up = (3.0 + rng.random() * 4.0) * (0.55 + 0.45 * power)
        for _ in range(int(8 + 8 * power)):
            nn = tilt_normal(n, rng.randrange(9999), rng.randrange(9999), 9, 0.7)
            col = tone(shade(raw, nn), 0.8 + rng.random() * 0.4)
            add_pixel(pixels, gx + rng.uniform(-0.2, 0.2),
                      gy + rng.uniform(-0.2, 0.2), gz + 0.15,
                      math.cos(ang) * sp + rng.uniform(-0.6, 0.6),
                      math.sin(ang) * sp + rng.uniform(-0.6, 0.6),
                      up + rng.uniform(-0.6, 0.6),
                      4 if rng.random() < 0.6 else 5, col)
        nn = tilt_normal(n, rng.randrange(9999), rng.randrange(9999), 9, 0.7)
        col = tone(shade(raw, nn), 0.8 + rng.random() * 0.4)
        add_shard(pixels, gx, gy, gz + 0.15,
                  math.cos(ang) * sp + rng.uniform(-1.0, 1.0),
                  math.sin(ang) * sp + rng.uniform(-1.0, 1.0),
                  up + rng.uniform(-0.8, 0.8),
                  rng.uniform(4, 5 + 3 * power), col)

    # искры летят только в соседние горючие объекты
    _alive_after = ({id(o) for o in objects}
                    if len(objects) != _nobj else None)
    for o in candidates:
        if _alive_after is not None and id(o) not in _alive_after:
            continue
        if o.get("shape") == "tree":
            if o.get("dead"):
                continue
            oc = (o["x"] + 0.5, o["y"] + 0.5, o["z"] + 0.45)
        else:
            if o.get("mat") not in BURN_MATS:
                continue
            if o.get("vid") is not None:
                continue  # стройка/дома деревни — не горят
            oc = (o["x"] + o["w"] / 2, o["y"] + o["d"] / 2, o["z"] + o["h"] / 2)
        if math.hypot(oc[0] - wx, oc[1] - wy) + abs(oc[2] - bz) * 0.5 < R * 1.15:
            if rng.random() < 0.30 + 0.28 * power and o.get("burn") is None:
                cur = o.get("ig")
                new = rng.uniform(0.5, 1.6)
                o["ig"] = min(cur, new) if cur is not None else new
    # всполох огня в самом взрыве + огненный венец по радиусу
    for _ in range(4):
        FLAMES.append(dict(x=wx + rng.uniform(-0.3, 0.3),
                           y=wy + rng.uniform(-0.3, 0.3), z=bz + 0.1,
                           t=0.0, life=0.45 + rng.random() * 0.25,
                           s=(0.34 + rng.random() * 0.24) * max(0.7, power),
                           ph=rng.random() * 6.283))
    for _ in range(5):
        ang = rng.uniform(0, math.pi * 2)
        rr2 = rng.uniform(0.25, R * 0.75)
        FLAMES.append(dict(x=wx + math.cos(ang) * rr2,
                           y=wy + math.sin(ang) * rr2, z=bz + 0.08,
                           t=0.0, life=0.5 + rng.random() * 0.3,
                           s=(0.2 + rng.random() * 0.16) * max(0.7, power),
                           ph=rng.random() * 6.283))
    sx, sy = cam.world_to_screen(wx, wy, bz)
    FLASHES.append(dict(x=sx, y=sy, t=0.0, life=0.4 + 0.08 * power,
                        power=power, ph=rng.random() * 6.283))
    RINGS.append(dict(x=sx, y=sy, t=0.0, life=0.55, power=power))
    for _ in range(5):
        SMOKES.append(dict(x=wx + rng.uniform(-0.5, 0.5),
                           y=wy + rng.uniform(-0.5, 0.5),
                           z=bz + 0.1 + rng.random() * 0.5, t=0.0,
                           life=0.9 + rng.random() * 0.6,
                           r=0.35 + rng.random() * 0.3))
    for _ in range(2):  # тяжёлая головня после огненной вспышки
        SMOKES.append(dict(x=wx + rng.uniform(-0.4, 0.4),
                           y=wy + rng.uniform(-0.4, 0.4),
                           z=bz + 0.3 + rng.random() * 0.4, t=0.0,
                           life=1.5 + rng.random() * 0.5,
                           r=0.5 + rng.random() * 0.25,
                           c=(70, 60, 52), a=130, rise=1.3))
    for _ in range(22):
        ang = rng.uniform(0, math.pi * 2)
        sp = (4 + rng.random() * 7) * power
        SPARKS.append(dict(x=wx, y=wy, z=bz + 0.1, vx=math.cos(ang) * sp,
                           vy=math.sin(ang) * sp, vz=(4 + rng.random() * 6) * power,
                           t=0.0, life=0.4 + rng.random() * 0.4))
    if len(SMOKES) > 70:
        del SMOKES[:len(SMOKES) - 70]
    if len(SPARKS) > 160:
        del SPARKS[:len(SPARKS) - 160]
    if len(RINGS) > 40:
        del RINGS[:len(RINGS) - 40]
    if len(FLASHES) > 40:
        del FLASHES[:len(FLASHES) - 40]
    if len(FLAMES) > 140:
        del FLAMES[:len(FLAMES) - 140]
    G.TRAUMA = min(1.0, G.TRAUMA + 0.55 * power)
    WIND["kick"] = min(1.5, WIND["kick"] + 0.45 * power)  # порыв
    if G.BOOM_SOUND is not None:
        try:
            G.BOOM_SOUND.play()
        except Exception:
            pass


# Циклические ссылки на модули выше по цепочке: импорт в конце файла,
# имена используются только внутри функций.
from game.village import construction as _village_construction  # noqa: E402
