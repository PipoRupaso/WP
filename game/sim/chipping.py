# -*- coding: utf-8 -*-
"""Сколы: связные рваные куски, взрывы деревьев, пикселизация."""

import math
from game.core import state as G
from game.core.config import (
    BASE_COLORS, DIRT_COLOR, GRID_D, GRID_W, MAT_ERODE, MAT_GRAIN, MIN_H,
    NX, NY, PX, PY, PZ, STONE_MATS, WOOD_MATS, rng)
from game.core.utils import (
    clamp, hash01)
from game.world.world_state import (
    FLYERS, HOUSE_HIT, _CRATER_TILES)
from game.render.lighting import (
    shade, tilt_normal, tone)
from game.sim.pixels import (
    _cell_face, _cluster_cells, _wood_group_debris, add_face_shard,
    add_pixel, add_shard, object_chip_grid)

def chip_blob(pixels, o, cells, bx, by, bz, power, R):
    """Рваный кусок: крошка по ячейкам + крупный осколок на группу."""
    for c in cells:
        ix, iy, iz, cx, cy, cz, cw, cd, ch = c
        dx, dy, dz = cx - bx, cy - by, cz - bz
        dist = max(0.3, math.sqrt(dx * dx + dy * dy + dz * dz))
        ux, uy = dx / dist, dy / dist
        sp = (2.8 + rng.random() * 3.2) * power
        sp *= 1.0 + 0.35 * clamp(dist / max(R, 0.5), 0.0, 1.0)
        up = (3.0 + rng.random() * 4.2) * (0.55 + 0.45 * power)
        wmat = o.get("mat", "concrete") in WOOD_MATS
        npx = (2 if rng.random() < 0.6 else 3) if wmat else (4 if rng.random() < 0.6 else 6)
        csz = (3, 4) if wmat else (5, 6)
        for k in range(npx):
            col = pixel_color_for(o, rng.random(), int(cx * 37 + k * 11),
                                  int(cy * 53 + cz * 29 + k * 7))
            add_pixel(pixels,
                      cx + rng.uniform(-cw / 2, cw / 2),
                      cy + rng.uniform(-cd / 2, cd / 2),
                      cz + rng.uniform(-ch / 2, ch / 2),
                      ux * sp + rng.uniform(-0.7, 0.7),
                      uy * sp + rng.uniform(-0.7, 0.7),
                      up + max(0.0, dz / dist) * 3 + rng.uniform(-0.6, 0.6),
                      csz[0] if rng.random() < 0.6 else csz[1], col)
    # крупные куски: связная группа ячеек = один осколок её размаха
    for grp in _cluster_cells(cells):
        c0 = min(grp, key=lambda c: (c[3] - bx) ** 2
                 + (c[4] - by) ** 2 + (c[5] - bz) ** 2)
        f = _cell_face(o, c0, bx, by, bz)
        if f is None:
            continue
        fn, (bax, bay, baz), (bbx, bby, bbz) = f
        la = math.sqrt(bax * bax + bay * bay + baz * baz) or 1.0
        lb = math.sqrt(bbx * bbx + bby * bby + bbz * bbz) or 1.0
        aux, auy, auz = bax / la, bay / la, baz / la
        avx, avy, avz = bbx / lb, bby / lb, bbz / lb
        us, vs, gx, gy, gz = [], [], 0.0, 0.0, 0.0
        for c in grp:
            rx, ry, rz = c[3] - c0[3], c[4] - c0[4], c[5] - c0[5]
            us.append(rx * aux + ry * auy + rz * auz)
            vs.append(rx * avx + ry * avy + rz * avz)
            gx += c[3]
            gy += c[4]
            gz += c[5]
        gx, gy, gz = gx / len(grp), gy / len(grp), gz / len(grp)
        wu = (max(us) - min(us)) + la
        wv = (max(vs) - min(vs)) + lb
        ox, oy, oz = fn
        osp = (2.6 + rng.random() * 3.2) * power
        up = (3.2 + rng.random() * 4.4) * (0.55 + 0.45 * power)
        ddx, ddy = gx - bx, gy - by
        dd = max(0.3, math.hypot(ddx, ddy))
        if o.get("mat", "concrete") in WOOD_MATS:
            _wood_group_debris(pixels, o, grp, fn, aux, auy, auz,
                               avx, avy, avz, wu, wv, gx, gy, gz,
                               bx, by, osp, up, power)
            continue
        add_face_shard(pixels, gx + ox * 0.12, gy + oy * 0.12,
                       gz + oz * 0.12,
                       (aux * wu, auy * wu, auz * wu),
                       (avx * wv, avy * wv, avz * wv), fn, o,
                       ox * osp + ddx / dd * osp * 0.6
                       + rng.uniform(-0.8, 0.8),
                       oy * osp + ddy / dd * osp * 0.6
                       + rng.uniform(-0.8, 0.8),
                       oz * osp + up + rng.uniform(-0.6, 0.6),
                       int(gx * 91 + gy * 57 + gz * 31) + len(grp) * 3)

    # мелкая крошка вокруг куска
    for _ in range(len(cells) // 2 + 2):
        c = rng.choice(cells)
        ang = rng.uniform(0, math.pi * 2)
        sp = (3.0 + rng.random() * 4.0) * power
        col = pixel_color_for(o, rng.random(), rng.randrange(9999),
                              rng.randrange(9999))
        add_pixel(pixels, c[3], c[4], c[5],
                  math.cos(ang) * sp, math.sin(ang) * sp,
                  (3.2 + rng.random() * 5.0) * (0.55 + 0.45 * power),
                  3, col)


def _tree_blast(pixels, objects, o, bx, by, bz, R, power, dist):
    """Ёлка у взрыва: волна гнёт, вдали сруб, в центре — с корнем."""
    if o.get("dead"):
        return
    cx, cy = o["x"] + 0.5, o["y"] + 0.5
    dx, dy = cx - bx, cy - by
    dd = math.hypot(dx, dy)
    if dd < 0.35:
        dx, dy = math.cos(o["phase"]), math.sin(o["phase"])
        dd = 1.0
    ux, uy = dx / dd, dy / dd
    wr = R * 2.5 + 2.0  # волна дальше сколов
    if dist < wr:
        imp = power * 0.5 * (1.0 - dist / wr)
        o["lvx"] += ux * imp * 5.2
        o["lvy"] += uy * imp * 5.2
    if dist >= R + 0.6:
        return
    o["shake"] = min(1.3, o.get("shake", 0.0) + 0.35 + power)
    # подлёт: ёлка прыгает и мягко оседает
    o["hopv"] = o.get("hopv", 0.0) + (2.2 + 2.4 * power) * \
        (1.0 - dist / (R + 0.6))
    leaf = BASE_COLORS[o["color"]]
    n = 2 + (1 if power > 0.8 and dist < R * 0.5 else 0)
    for _ in range(n):  # уцелевшая роняет пару кусков хвои
        a = rng.uniform(0, math.pi * 2)
        rr = rng.uniform(0.05, 0.4)
        lx, ly = cx + math.cos(a) * rr, cy + math.sin(a) * rr
        ddx, ddy = lx - bx, ly - by
        ddd = max(0.3, math.hypot(ddx, ddy))
        sp = (2.0 + rng.random() * 3.0) * power
        add_shard(pixels, lx, ly, o["z"] + rng.uniform(0.2, 0.7),
                  ddx / ddd * sp + rng.uniform(-1, 1),
                  ddy / ddd * sp + rng.uniform(-1, 1),
                  rng.uniform(1.5, 4.0),
                  rng.uniform(3, 4.5),
                  tone(leaf, 0.85 + rng.random() * 0.3), quad=True)
    if dist >= R * 0.9:
        return
    wood = BASE_COLORS["wood_dark"]
    if dist < R * 0.45:
        # ВЫРВАНА С КОРНЕМ: летит целиком
        objects.remove(o)
        if len(FLYERS) > 20:
            del FLYERS[:len(FLYERS) - 20]
        sp = 3.0 + 3.0 * power
        FLYERS.append(dict(x=cx, y=cy, z=o["z"] + 0.3,
                           vx=ux * sp + rng.uniform(-1, 1),
                           vy=uy * sp + rng.uniform(-1, 1),
                           vz=(4.0 + rng.random() * 3.0) * (0.6 + 0.4 * power),
                           color=o["color"], phase=o["phase"],
                           sz=o.get("sz", 1.0), spin=0.0,
                           spin_v=rng.uniform(4, 9)
                           * (1 if rng.random() < 0.5 else -1),
                           t=0.0, rest=False, fade=1.0, dx=ux, dy=uy))
        for _ in range(2):  # обломанные ветви следом
            ang = rng.uniform(0, math.pi * 2)
            dsp = (2.0 + rng.random() * 2.5) * power
            add_shard(pixels, cx, cy, o["z"] + 0.5,
                      ux * dsp + math.cos(ang) * 1.5,
                      uy * dsp + math.sin(ang) * 1.5,
                      rng.uniform(2.0, 5.0),
                      rng.uniform(5, 7),
                      tone(leaf, 0.85 + rng.random() * 0.3), quad=True)
        tx, ty = int(o["x"]), int(o["y"])  # ямка от корней
        if 0 <= tx < GRID_W and 0 <= ty < GRID_D:
            G.GH[ty][tx] = max(MIN_H, G.GH[ty][tx] - 0.2)
            G.DENTED.add((tx, ty))
            _CRATER_TILES.add((tx, ty))
        for _ in range(6):  # комья вслед
            ang = rng.uniform(0, math.pi * 2)
            dsp = (1.5 + rng.random() * 2.5) * power
            nn = tilt_normal(PZ, rng.randrange(9999), rng.randrange(9999),
                             9, 0.7)
            add_pixel(pixels, cx + rng.uniform(-0.3, 0.3),
                      cy + rng.uniform(-0.3, 0.3), 0.15,
                      math.cos(ang) * dsp + ux * sp * 0.4,
                      math.sin(ang) * dsp + uy * sp * 0.4,
                      rng.uniform(2.0, 5.0),
                      3 if rng.random() < 0.6 else 4,
                      tone(shade(DIRT_COLOR, nn), 0.8 + rng.random() * 0.4))
    else:
        # СРУБЛЕНА: пенёк остаётся, крона — щепой в стороны
        o["dead"] = "stump"
        o["lx"] = o["ly"] = o["lvx"] = o["lvy"] = 0.0
        crown_z = o["z"] + 0.45
        for _ in range(3):  # куски кроны
            ang = rng.uniform(0, math.pi * 2)
            dsp = (2.5 + rng.random() * 3.5) * power
            add_shard(pixels, cx + rng.uniform(-0.2, 0.2),
                      cy + rng.uniform(-0.2, 0.2),
                      crown_z + rng.uniform(-0.1, 0.3),
                      ux * dsp + math.cos(ang) * 1.5,
                      uy * dsp + math.sin(ang) * 1.5,
                      rng.uniform(2.5, 6.0),
                      rng.uniform(7, 10),
                      tone(leaf, 0.85 + rng.random() * 0.3), quad=True)
        ang = rng.uniform(0, math.pi * 2)  # кусок ствола
        dsp = (2.0 + rng.random() * 3.0) * power
        add_shard(pixels, cx, cy, o["z"] + 0.25,
                  ux * dsp + math.cos(ang),
                  uy * dsp + math.sin(ang),
                  rng.uniform(2.0, 5.0),
                  rng.uniform(6, 8),
                  tone(wood, 0.85 + rng.random() * 0.3), quad=True)



def chip_object(objects, pixels, o, bx, by, bz, R, power, dist):
    """Скол: рваная связная выбоина у взрыва, объект стоит на месте."""
    if o.get("shape") == "tree":
        _tree_blast(pixels, objects, o, bx, by, bz, R, power, dist)
        return
    g = object_chip_grid(o)
    scored = []
    for c in g["cells"]:
        key = (c[0], c[1], c[2])
        if key in o["chips"]:
            continue
        d2 = (c[3] - bx) ** 2 + (c[4] - by) ** 2 + (c[5] - bz) ** 2
        if d2 < (R + 0.6) ** 2:
            scored.append((math.sqrt(d2), c))
    if not scored:
        return
    scored.sort(key=lambda t: t[0])
    hard = MAT_ERODE.get(o.get("mat", "concrete"), 1.0) * o.get("erode", 1.0)
    want = clamp(int((1 - dist / R) * (6 + 10 * power)
                     * rng.uniform(0.7, 1.3) * hard), 1, 40)
    if o.get("house"):
        want = clamp(int(want * 1.9 + 1), 1, 40)  # по домам сокрушительнее
    # направление удара: тянем скол поперёк + рваный шум (форма от удара)
    ocx, ocy = o["x"] + o["w"] / 2, o["y"] + o["d"] / 2
    _L = max(0.3, math.hypot(ocx - bx, ocy - by))
    bux, buy = (ocx - bx) / _L, (ocy - by) / _L
    start = rng.choice([c for _, c in scored[:3]])
    avail = {(c[0], c[1], c[2]): c for _, c in scored}
    chosen, seen = [start], {(start[0], start[1], start[2])}
    frontier = [start]
    w_side = rng.uniform(0.6, 1.2)
    w_along = -rng.uniform(0.2, 0.7)
    w_jag = rng.uniform(1.2, 2.0)
    w_take = rng.uniform(0.45, 0.75)
    gr = MAT_GRAIN.get(o.get("mat", "concrete"))
    w_grain = rng.uniform(0.7, 1.1) if gr else 0.0
    while frontier and len(chosen) < want:
        cands = {}
        for c in frontier:
            for nb in [(c[0] + 1, c[1], c[2]), (c[0] - 1, c[1], c[2]),
                       (c[0], c[1] + 1, c[2]), (c[0], c[1] - 1, c[2]),
                       (c[0], c[1], c[2] + 1), (c[0], c[1], c[2] - 1)]:
                if nb in avail and nb not in seen:
                    cands[nb] = avail[nb]
        if not cands:
            break
        scored_c = []
        for nb, c in cands.items():
            ox, oy = c[3] - start[3], c[4] - start[4]
            oz = c[5] - start[5]
            side = abs(ox * -buy + oy * bux)
            along = ox * bux + oy * buy
            jag = hash01(c[0] * 7 + c[1], c[2] * 3 + c[0], 5) - 0.5
            axial = abs(ox * gr[0] + oy * gr[1] + oz * gr[2]) if gr else 0.0
            scored_c.append((side * w_side + abs(along) * w_along
                             + jag * w_jag + axial * w_grain, c, nb))
        scored_c.sort(reverse=True)
        take = max(1, min(len(scored_c), int(len(scored_c) * w_take) or 1,
                           want - len(chosen)))
        frontier = []
        for _, c, nb in scored_c[:take]:
            seen.add(nb)
            chosen.append(c)
            frontier.append(c)
    if len(chosen) < want:  # добивка ближайшими
        for _, c in scored:
            if len(chosen) >= want:
                break
            nb = (c[0], c[1], c[2])
            if nb not in seen:
                seen.add(nb)
                chosen.append(c)
    if rng.random() < 0.35 and len(avail) > len(chosen) + 6:
        # спутник-щербинка в стороне
        far = [c for _, c in scored if (c[0], c[1], c[2]) not in seen]
        if far:
            f = far[rng.randrange(len(far))]
            extra = [f] + [avail[nb] for nb in
                           [(f[0] + 1, f[1], f[2]), (f[0], f[1], f[2] + 1)]
                           if nb in avail and nb not in seen][:2]
            for c in extra:
                nb = (c[0], c[1], c[2])
                if nb not in seen:
                    seen.add(nb)
                    chosen.append(c)
    _n0 = len(o["chips"])
    for c in chosen:
        o["chips"].add((c[0], c[1], c[2]))
    o["over"] = o.get("over", 0) + 1
    if o.get("house"):
        HOUSE_HIT[o["house"]] = True  # дом под атакой — дым гаснет
        _sim_destruction._house_damage_add(objects, o["house"], len(o["chips"]) - _n0)
    chip_blob(pixels, o, chosen, bx, by, bz, power, R)
    _lim = 0.55 if o.get("house") else 0.65
    if len(o["chips"]) > _lim * len(g["cells"]):
        if o.get("house"):
            _sim_destruction._house_damage_add(objects, o["house"],
                              len(g["cells"]) - len(o["chips"]))
        # истощён — рассыпается целиком
        left = [c for c in g["cells"] if (c[0], c[1], c[2]) not in o["chips"]]
        for i, c in enumerate(rng.sample(left, min(len(left), 160))):
            pixelize_cell(pixels, o, c, bx, by, bz, power)
            if i < 10:
                f = _cell_face(o, c, bx, by, bz)
                if f is not None:
                    fn, ba, bb = f
                    dx, dy = c[3] - bx, c[4] - by
                    dd = max(0.3, math.hypot(dx, dy))
                    sp = (2.5 + rng.random() * 3.0) * power
                    add_face_shard(pixels, c[3], c[4], c[5], ba, bb,
                                   fn, o, dx / dd * sp, dy / dd * sp,
                                   (3.0 + rng.random() * 4.0)
                                   * (0.55 + 0.45 * power), i * 13 + 5)
        objects.remove(o)


def pixel_color_for(o, face_pick, seed_a, seed_b, fixed_n=None):
    """Цвет пикселя = текстура оторванного куска (грань + нормаль + свет)."""
    base = BASE_COLORS[o["color"]]
    stone = o["color"] in STONE_MATS
    if fixed_n is not None:
        n = fixed_n
    elif face_pick < 0.40:
        n = PZ
    elif face_pick < 0.70:
        n = PX if hash01(seed_a, seed_b, 1) < 0.5 else NX
    else:
        n = PY if hash01(seed_a, seed_b, 2) < 0.5 else NY
    nn = tilt_normal(n, seed_a, seed_b, 3, 0.55)
    col = shade(base, nn)
    if stone:
        r = hash01(seed_a, seed_b, 4)
        if r < 0.28:
            col = tone(shade(base, nn), 0.52)  # раствор
        else:
            col = tone(col, 0.90 + 0.18 * hash01(seed_a, seed_b, 5))  # кирпич
    else:
        col = tone(col, 0.86 + 0.24 * hash01(seed_a, seed_b, 6))
    return col


def pixelize_cell(pixels, o, cell, bx, by, bz, power):
    if len(pixels) > 900 and rng.random() < 0.55:
        return
    _, _, _, cx, cy, cz, cw, cd, ch = cell
    vol = cw * cd * ch
    count = max(2, min(6, int(3 + vol * 22)))
    dx, dy, dz = cx - bx, (cy - by), (cz - bz)
    dist = max(0.3, math.sqrt(dx * dx + dy * dy + dz * dz))
    ux, uy = dx / dist, dy / dist
    for k in range(count):
        ang = rng.uniform(0, math.pi * 2)
        rsp = rng.uniform(0.5, 1.5)
        sp = (2.2 + rng.random() * 4.2) * power
        col = pixel_color_for(o, rng.random(), int(cx * 37 + k * 11),
                              int(cy * 53 + cz * 29 + k * 7))
        add_pixel(pixels,
                  cx + rng.uniform(-cw / 2, cw / 2),
                  cy + rng.uniform(-cd / 2, cd / 2),
                  cz + rng.uniform(-ch / 2, ch / 2),
                  ux * sp + math.cos(ang) * rsp,
                  uy * sp + math.sin(ang) * rsp,
                  (3.2 + rng.random() * 5.2) * (0.55 + 0.45 * power)
                  + max(0.0, dz / dist) * 3,
                  3 if rng.random() < 0.6 else 4, col)


# Циклические ссылки на модули выше по цепочке: импорт в конце файла,
# имена используются только внутри функций.
from game.sim import destruction as _sim_destruction  # noqa: E402
