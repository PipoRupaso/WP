# -*- coding: utf-8 -*-
"""Пиксели-осколки: потолок, шарды, щепки, воксельные сетки."""

import math
from game.core.config import (
    CHIP_VOX, CRUMB_LIFE, MAT_GRAIN, PIXEL_CAP, PZ, SHARD_LIFE, VOX, rng)
from game.render.lighting import (
    tone)

# ---------------------------------------------------------------------------
# Потолок пикселей: амортизированный O(1) (указатель + короткий поиск rest)
# ---------------------------------------------------------------------------
_PIXEL_KILL = [0]


def _trim_pixels(pixels):
    if len(pixels) <= PIXEL_CAP:
        return
    n = len(pixels)
    s = _PIXEL_KILL[0] % n
    for j in range(min(n, 40)):
        i = (s + j) % n
        if pixels[i]["rest"]:
            pixels[i] = pixels[-1]
            pixels.pop()
            _PIXEL_KILL[0] = i % max(1, len(pixels))
            return
    i = s  # rest рядом нет — снять со скользящей позиции (старые крошки)
    pixels[i] = pixels[-1]
    pixels.pop()
    _PIXEL_KILL[0] = i % max(1, len(pixels)) if pixels else 0


def add_pixel(pixels, x, y, z, vx, vy, vz, size, color):
    pixels.append(dict(x=x, y=y, z=z, vx=vx, vy=vy, vz=vz,
                       size=size, color=color, rest=False, t=0.0,
                       life=CRUMB_LIFE, fade=1.0,
                       kind="px", ang=0.0, spin=0.0, verts=None))
    _trim_pixels(pixels)


def add_shard(pixels, x, y, z, vx, vy, vz, size, color, quad=False):
    """Осколок: треугольник/полигон; quad — chunky кусок кроны/ствола."""
    n = 4 if quad else (3 if rng.random() < 0.6 else 4)
    a0 = rng.uniform(0, math.pi * 2)
    verts = []
    for i in range(n):
        a = a0 + i * math.pi * 2 / n + rng.uniform(-0.5, 0.5)
        r = size * (rng.uniform(0.7, 1.0) if quad
                    else rng.uniform(0.5, 1.0))
        verts.append((math.cos(a) * r, math.sin(a) * r))
    pixels.append(dict(x=x, y=y, z=z, vx=vx, vy=vy, vz=vz,
                       size=size, color=color, rest=False, t=0.0,
                       life=SHARD_LIFE, fade=1.0,
                       kind="sh", ang=rng.uniform(0, 6.28),
                       spin=rng.uniform(-9, 9), verts=verts))
    _trim_pixels(pixels)


def voxel_grid(o, vox=VOX):
    """Разбиение объекта на воксели: (ix,iy,iz,cx,cy,cz,cw,cd,ch)."""
    nx = max(1, int(round(o["w"] / vox)))
    ny = max(1, int(round(o["d"] / vox)))
    nz = max(1, int(round(o["h"] / vox)))
    cw, cd, ch = o["w"] / nx, o["d"] / ny, o["h"] / nz
    cells = []
    for iz in range(nz):
        for iy in range(ny):
            for ix in range(nx):
                cx = o["x"] + (ix + 0.5) * cw
                cy = o["y"] + (iy + 0.5) * cd
                cz = o["z"] + (iz + 0.5) * ch
                if o["shape"] == "cylinder":
                    ex = (cx - (o["x"] + o["w"] / 2)) / (o["w"] / 2)
                    ey = (cy - (o["y"] + o["d"] / 2)) / (o["d"] / 2)
                    if ex * ex + ey * ey > 1.0:
                        continue
                elif o["shape"] == "gable":
                    # щипец: конёк вдоль X, уступы только по Y
                    LV = 2 if o["h"] < 0.7 else 3
                    step = (o["d"] / 2 - 0.2) / (LV - 1)
                    L = min(LV - 1, int((cz - o["z"]) / (o["h"] / LV)))
                    yi = o["y"] + L * step
                    if not (yi <= cy < yi + o["d"] - 2 * L * step):
                        continue
                elif o["shape"] == "pyramid":
                    lh = o["h"] / 3
                    L = min(2, int((cz - o["z"]) / lh))
                    inset = L * 0.5
                    ww = max(0.5, o["w"] - inset * 2)
                    dd = max(0.5, o["d"] - inset * 2)
                    xi = o["x"] + (o["w"] - ww) / 2
                    yi = o["y"] + (o["d"] - dd) / 2
                    if not (xi <= cx < xi + ww and yi <= cy < yi + dd):
                        continue
                cells.append((ix, iy, iz, cx, cy, cz, cw, cd, ch))
    return cells, (nx, ny, nz)


def object_chip_grid(o):
    """Сетка сколов объекта (строится один раз, объект неподвижен)."""
    g = o.get("_chipgrid")
    if g is None:
        cells, (nx, ny, nz) = voxel_grid(o, o.get("vox", CHIP_VOX))
        g = dict(cells=cells, nx=nx, ny=ny, nz=nz,
                 cw=o["w"] / nx, cd=o["d"] / ny, ch=o["h"] / nz,
                 idx={(c[0], c[1], c[2]): c for c in cells})
        o["_chipgrid"] = g
        o["chips"] = set()
    return g


def add_splinter(pixels, x, y, z, vx, vy, vz, bu, bv, color):
    """Щепка: длинный тонкий осколок вдоль волокон."""
    sl = rng.uniform(0.7, 1.0)
    wig = rng.uniform(-0.12, 0.12)
    fv = [(-0.5 * sl, 0.0), (-0.08 + wig, 0.5), (0.5 * sl, 0.0),
          (-0.08 - wig, -0.5)]
    pixels.append(dict(x=x, y=y, z=z, vx=vx, vy=vy, vz=vz,
                       size=1.0, color=color, rest=False, t=0.0,
                       life=SHARD_LIFE, fade=1.0,
                       kind="sh", ang=rng.uniform(0, 6.28),
                       spin=rng.uniform(-11, 11),
                       verts=None, face=(bu, bv), fverts=fv))
    _trim_pixels(pixels)


def add_fiber(pixels, x, y, z, vx, vy, vz, length, color):
    """Волокно: короткая светлая чёрточка."""
    pixels.append(dict(x=x, y=y, z=z, vx=vx, vy=vy, vz=vz,
                       size=length, color=color, rest=False, t=0.0,
                       life=CRUMB_LIFE, fade=1.0,
                       kind="fib", ang=rng.uniform(0, 6.28),
                       spin=rng.uniform(-11, 11), verts=None))
    _trim_pixels(pixels)


def _cell_face(o, c, bx, by, bz):
    """Лицевая грань ячейки со стороны взрыва: нормаль + базис куска."""
    g = o.get("_chipgrid")
    nx, ny, nz = g["nx"], g["ny"], g["nz"]
    ix, iy, iz, cx, cy, cz, cw, cd, ch = c
    cand = []
    if ix == 0:
        cand.append(((-1, 0, 0), (0.0, cd, 0.0), (0.0, 0.0, ch)))
    if ix == nx - 1:
        cand.append(((1, 0, 0), (0.0, cd, 0.0), (0.0, 0.0, ch)))
    if iy == 0:
        cand.append(((0, -1, 0), (cw, 0.0, 0.0), (0.0, 0.0, ch)))
    if iy == ny - 1:
        cand.append(((0, 1, 0), (cw, 0.0, 0.0), (0.0, 0.0, ch)))
    if iz == nz - 1:
        cand.append((PZ, (cw, 0.0, 0.0), (0.0, cd, 0.0)))
    if not cand:
        return None
    dx, dy, dz = cx - bx, cy - by, cz - bz
    return max(cand,
               key=lambda t: t[0][0] * dx + t[0][1] * dy + t[0][2] * dz)


def add_face_shard(pixels, cx, cy, cz, basis_a, basis_b, face_n, o,
                   vx, vy, vz, seed):
    """Осколок = выбитая ячейка грани: та же форма, размер и цвет."""
    nv = rng.randrange(5, 8)
    angs = sorted(rng.uniform(0, math.pi * 2) for _ in range(nv))
    fv = []
    for a in angs:
        ru = rng.uniform(0.62, 1.08)
        rv = rng.uniform(0.62, 1.08)
        fv.append((math.cos(a) * ru * 0.5, math.sin(a) * rv * 0.5))
    col = _sim_chipping.pixel_color_for(o, 0.0, seed, seed * 7 + 3, fixed_n=face_n)
    pixels.append(dict(x=cx, y=cy, z=cz, vx=vx, vy=vy, vz=vz,
                       size=1.0, color=col, rest=False, t=0.0,
                       life=SHARD_LIFE, fade=1.0,
                       kind="sh", ang=0.0, spin=rng.uniform(-9, 9),
                       verts=None, face=(basis_a, basis_b), fverts=fv))
    _trim_pixels(pixels)


def _wood_group_debris(pixels, o, grp, fn, aux, auy, auz,
                       avx, avy, avz, wu, wv, gx, gy, gz,
                       bx, by, osp, up, power):
    """Дерево: щепки вдоль волокон + волокна + немного крошки."""
    gr = MAT_GRAIN.get(o.get("mat", "concrete"), (0, 0, 1))
    au = abs(aux * gr[0] + auy * gr[1] + auz * gr[2])
    av = abs(avx * gr[0] + avy * gr[1] + avz * gr[2])
    if au >= av:
        ux, uy, uz, Lu = aux, auy, auz, wu
        vx, vy, vz = avx, avy, avz
    else:
        ux, uy, uz, Lu = avx, avy, avz, wv
        vx, vy, vz = aux, auy, auz
    ox, oy, oz = fn
    ddx, ddy = gx - bx, gy - by
    dd = max(0.3, math.hypot(ddx, ddy))
    n_sp = 3 + min(4, len(grp) // 2)
    for i in range(n_sp):
        f = rng.uniform(-0.3, 0.3)
        col = _sim_chipping.pixel_color_for(o, 0.0, int(gx * 91) + i * 17,
                              int(gy * 57 + gz * 31) + i * 29,
                              fixed_n=fn)
        col = tone(col, 1.12)
        L = max(0.55, Lu * rng.uniform(1.0, 1.5))
        Wd = rng.uniform(0.09, 0.16)
        add_splinter(pixels, gx + ox * 0.12 + ux * f,
                     gy + oy * 0.12 + uy * f, gz + oz * 0.12 + uz * f,
                     ox * osp + ddx / dd * osp * 0.6 + rng.uniform(-1, 1),
                     oy * osp + ddy / dd * osp * 0.6 + rng.uniform(-1, 1),
                     oz * osp + up + rng.uniform(-0.8, 0.8),
                     (ux * L, uy * L, uz * L),
                     (vx * Wd, vy * Wd, vz * Wd), col)
    for i in range(10 + len(grp)):
        col = _sim_chipping.pixel_color_for(o, 0.0, rng.randrange(9999),
                              rng.randrange(9999), fixed_n=fn)
        col = tone(col, 1.18)
        a = rng.uniform(0, math.pi * 2)
        sp = osp * rng.uniform(0.5, 1.0)
        add_fiber(pixels, gx + rng.uniform(-0.2, 0.2),
                  gy + rng.uniform(-0.2, 0.2), gz + rng.uniform(-0.2, 0.2),
                  ox * sp + math.cos(a) * 1.5,
                  oy * sp + math.sin(a) * 1.5,
                  up * rng.uniform(0.4, 0.9),
                  rng.uniform(3.0, 5.5), col)


def _cluster_cells(cells):
    """Связные группы ячеек (26-соседство) — будущие крупные куски."""
    leaders = {(c[0], c[1], c[2]): c for c in cells}
    seen, groups = set(), []
    for key in leaders:
        if key in seen:
            continue
        grp, stack = [], [key]
        seen.add(key)
        while stack:
            k = stack.pop()
            grp.append(leaders[k])
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        nb = (k[0] + dx, k[1] + dy, k[2] + dz)
                        if nb in leaders and nb not in seen:
                            seen.add(nb)
                            stack.append(nb)
        groups.append(grp)
    return groups


# Циклические ссылки на модули выше по цепочке: импорт в конце файла,
# имена используются только внутри функций.
from game.sim import chipping as _sim_chipping  # noqa: E402
