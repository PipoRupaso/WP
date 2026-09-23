# -*- coding: utf-8 -*-
"""Построение тестовой сцены: деревня, площадь, сад, крепость, дома по эпохам."""

import math
from game.core import state as G
from game.core.config import (
    GRID_D, GRID_W)
from game.core.utils import (
    hash01)
from game.world.world_state import (
    CHIMNEY_T, HOUSE_BURNING, HOUSE_DMG, HOUSE_HIT, HOUSE_TOTAL, LIGHTS_OFF,
    VENTS)
from game.world.terrain import (
    _base_h, _vnoise, ground_height_at)

# ---------------------------------------------------------------------------
# Сцена
# ---------------------------------------------------------------------------
def make_test_scene(keep_buildings=False):
    s = []
    for h in HOUSE_HIT:
        HOUSE_HIT[h] = False
        CHIMNEY_T[h] = 0.0
    VENTS.clear()
    LIGHTS_OFF.clear()
    HOUSE_BURNING.clear()
    HOUSE_TOTAL.clear()
    HOUSE_DMG.clear()

    # на карте — только дома: фигуры-фантики убраны
    # домик: фундамент, стены сегментами, крыша-щипец, мебель внутри
    def hbox(x, y, z, w, d, h, color, shape="box", mat="concrete", **kw):
        s.append(dict(x=x, y=y, z=z, w=w, d=d, h=h, color=color,
                      shape=shape, mat=mat, vx=0.0, vy=0.0, vz=0.0,
                      house=1, **kw))

    hbox(42.25, 10.2, 0, 0.7, 0.6, 0.07, "gray", erode=0.35, vox=0.09,
         sort_min=True)
    hbox(42.33, 10.28, 0.07, 0.54, 0.44, 0.03, "wood_light",
         mat="plank_light", inside=True, erode=1.2, vox=0.09,
         sort_min=True)
    hbox(42.33, 10.71, 0.07, 0.18, 0.09, 0.34, "plaster", mat="plaster",
         frame=True, erode=0.25, vox=0.075,
         detail=dict(n=(0, 1, 0), kind="window", frame=False,
                     rect=(0.05, 0.95, 0.15, 0.6)))
    hbox(42.51, 10.71, 0.07, 0.18, 0.09, 0.34, "plaster", mat="plaster",
         frame=True, erode=0.25, vox=0.075,
         detail=dict(n=(0, 1, 0), kind="door", frame=False,
                     rect=(0.05, 0.95, 0.0, 0.7)))
    hbox(42.69, 10.71, 0.07, 0.18, 0.09, 0.34, "plaster", mat="plaster",
         frame=True, erode=0.25, vox=0.075,
         detail=dict(n=(0, 1, 0), kind="window", frame=False,
                     rect=(0.05, 0.95, 0.15, 0.6)))
    hbox(42.33, 10.2, 0.07, 0.27, 0.09, 0.34, "plaster", mat="plaster",
         frame=True, erode=0.25, vox=0.075,
         detail=dict(n=(0, -1, 0), kind="window", frame=False,
                     rect=(0.05, 0.95, 0.15, 0.6)))
    hbox(42.6, 10.2, 0.07, 0.27, 0.09, 0.34, "plaster", mat="plaster",
         frame=True, erode=0.25, vox=0.075,
         detail=dict(n=(0, -1, 0), kind="window", frame=False,
                     rect=(0.05, 0.95, 0.15, 0.6)))
    hbox(42.25, 10.29, 0.07, 0.09, 0.42, 0.34, "plaster", mat="plaster",
         frame=True, erode=0.25, vox=0.075,
         detail=dict(n=(-1, 0, 0), kind="window", frame=False, shut=True,
                     rect=(0.22, 0.78, 0.15, 0.6)))
    hbox(42.86, 10.29, 0.07, 0.09, 0.42, 0.34, "plaster", mat="plaster",
         frame=True, erode=0.25, vox=0.075,
         detail=dict(n=(1, 0, 0), kind="window", frame=False, shut=True,
                     rect=(0.22, 0.78, 0.15, 0.6)))
    hbox(42.175, 10.125, 0.41, 0.85, 0.75, 0.3, "tile_red",
         shape="gable", mat="tile", erode=1.2, vox=0.15, ends="timber")
    hbox(42.645, 10.325, 0.27, 0.12, 0.12, 0.5, "gray", mat="stone",
         erode=0.5, vox=0.06, vent=1)
    hbox(42.55, 10.8, 0, 0.13, 0.1, 0.035, "gray", erode=0.35, vox=0.05)
    hbox(42.35, 10.3, 0.1, 0.26, 0.17, 0.09, "wood_dark", mat="wood_dark",
         inside=True, erode=0.3, vox=0.075)
    hbox(42.365, 10.31, 0.19, 0.23, 0.15, 0.045, "white", mat="cloth",
         inside=True, erode=0.3, vox=0.075)
    hbox(42.365, 10.31, 0.235, 0.11, 0.15, 0.025, "red", mat="cloth",
         inside=True, erode=0.3, vox=0.075)
    hbox(42.62, 10.3, 0.1, 0.17, 0.17, 0.17, "gray", mat="stone",
         inside=True, erode=0.5, vox=0.075,
         detail=dict(n=(0, 1, 0), kind="firebox", frame=False,
                     rect=(0.0, 1.0, 0.15, 0.7)))
    hbox(42.38, 10.5, 0.185, 0.2, 0.14, 0.025, "wood_light",
         mat="wood_light", inside=True, erode=0.3, vox=0.075)
    hbox(42.455, 10.545, 0.118, 0.05, 0.05, 0.067, "wood_dark",
         mat="wood_dark", inside=True, erode=0.3, vox=0.075)
    hbox(42.36, 10.48, 0.1, 0.24, 0.17, 0.018, "red", mat="cloth",
         inside=True, erode=0.3, vox=0.075)
    # двор: бочка, ящик, колпак трубы (разрушаемые, вне дома)
    s.append(dict(x=43.06, y=10.5, z=0, w=0.12, d=0.12, h=0.15,
                  color="wood_dark", shape="cylinder", mat="wood_dark",
                  vx=0.0, vy=0.0, vz=0.0, vox=0.05, erode=0.4))
    s.append(dict(x=42.76, y=10.87, z=0, w=0.12, d=0.12, h=0.12,
                  color="wood_light", shape="box", mat="wood_dark",
                  vx=0.0, vy=0.0, vz=0.0, vox=0.05, erode=0.6))
    s.append(dict(x=42.635, y=10.315, z=0.77, w=0.14, d=0.14, h=0.04,
                  color="gray", shape="box", mat="stone",
                  vx=0.0, vy=0.0, vz=0.0, vox=0.05, erode=0.3))
    # второй дом: двухэтажный, красная крыша (house=2)
    def hbox2(x, y, z, w, d, h, color, shape="box", mat="concrete", **kw):
        s.append(dict(x=x, y=y, z=z, w=w, d=d, h=h, color=color,
                      shape=shape, mat=mat, vx=0.0, vy=0.0, vz=0.0,
                      house=2, **kw))

    hbox2(37.95, 29.45, 0, 1.2, 1.0, 0.07, "gray", erode=0.35, vox=0.1,
          sort_min=True)
    hbox2(38.03, 29.53, 0.07, 1.04, 0.84, 0.03, "wood_light",
          mat="plank_light", inside=True, erode=1.2, vox=0.1,
          sort_min=True)
    # первый этаж
    hbox2(38.0, 30.31, 0.07, 0.37, 0.09, 0.26, "plaster", mat="plaster",
          frame=True, erode=0.25, vox=0.075,
          detail=dict(n=(0, 1, 0), kind="window", frame=False,
                      rect=(0.20, 0.80, 0.15, 0.6)))
    hbox2(38.37, 30.31, 0.07, 0.36, 0.09, 0.26, "plaster", mat="plaster",
          frame=True, erode=0.25, vox=0.075,
          detail=dict(n=(0, 1, 0), kind="door", frame=False,
                      rect=(0.05, 0.95, 0.0, 0.7)))
    hbox2(38.73, 30.31, 0.07, 0.37, 0.09, 0.26, "plaster", mat="plaster",
          frame=True, erode=0.25, vox=0.075,
          detail=dict(n=(0, 1, 0), kind="window", frame=False,
                      rect=(0.20, 0.80, 0.15, 0.6)))
    hbox2(38.0, 29.5, 0.07, 0.55, 0.09, 0.26, "plaster", mat="plaster",
          frame=True, erode=0.25, vox=0.075,
          detail=dict(n=(0, -1, 0), kind="window", frame=False,
                      rect=(0.20, 0.80, 0.15, 0.6)))
    hbox2(38.55, 29.5, 0.07, 0.55, 0.09, 0.26, "plaster", mat="plaster",
          frame=True, erode=0.25, vox=0.075,
          detail=dict(n=(0, -1, 0), kind="window", frame=False,
                      rect=(0.20, 0.80, 0.15, 0.6)))
    hbox2(38.0, 29.59, 0.07, 0.09, 0.72, 0.26, "plaster", mat="plaster",
          frame=True, erode=0.25, vox=0.075,
          detail=dict(n=(-1, 0, 0), kind="window", frame=False, shut=True,
                      rect=(0.3, 0.7, 0.15, 0.6)))
    hbox2(39.01, 29.59, 0.07, 0.09, 0.36, 0.26, "plaster", mat="plaster",
          frame=True, erode=0.25, vox=0.075)
    hbox2(39.01, 29.95, 0.07, 0.09, 0.36, 0.26, "plaster", mat="plaster",
          frame=True, erode=0.25, vox=0.075,
          detail=dict(n=(1, 0, 0), kind="window", frame=False, shut=True,
                      rect=(0.22, 0.78, 0.15, 0.6)))
    # перекрытие между этажами
    hbox2(38.03, 29.53, 0.33, 1.04, 0.84, 0.03, "wood_light",
          mat="plank_light", inside=True, erode=1.2, vox=0.1,
          sort_min=True)
    # второй этаж: окна со ставнями
    hbox2(38.0, 30.31, 0.33, 0.37, 0.09, 0.24, "plaster", mat="plaster",
          frame=True, erode=0.25, vox=0.075,
          detail=dict(n=(0, 1, 0), kind="window", frame=False, shut=True,
                      rect=(0.22, 0.78, 0.15, 0.6)))
    hbox2(38.37, 30.31, 0.33, 0.36, 0.09, 0.24, "plaster", mat="plaster",
          frame=True, erode=0.25, vox=0.075,
          detail=dict(n=(0, 1, 0), kind="window", frame=False, shut=True,
                      rect=(0.22, 0.78, 0.15, 0.6)))
    hbox2(38.73, 30.31, 0.33, 0.37, 0.09, 0.24, "plaster", mat="plaster",
          frame=True, erode=0.25, vox=0.075,
          detail=dict(n=(0, 1, 0), kind="window", frame=False, shut=True,
                      rect=(0.22, 0.78, 0.15, 0.6)))
    hbox2(38.0, 29.5, 0.33, 0.55, 0.09, 0.24, "plaster", mat="plaster",
          frame=True, erode=0.25, vox=0.075,
          detail=dict(n=(0, -1, 0), kind="window", frame=False,
                      rect=(0.20, 0.80, 0.15, 0.6)))
    hbox2(38.55, 29.5, 0.33, 0.55, 0.09, 0.24, "plaster", mat="plaster",
          frame=True, erode=0.25, vox=0.075,
          detail=dict(n=(0, -1, 0), kind="window", frame=False,
                      rect=(0.20, 0.80, 0.15, 0.6)))
    hbox2(38.0, 29.59, 0.33, 0.09, 0.72, 0.24, "plaster", mat="plaster",
          frame=True, erode=0.25, vox=0.075,
          detail=dict(n=(-1, 0, 0), kind="window", frame=False, shut=True,
                      rect=(0.3, 0.7, 0.15, 0.6)))
    hbox2(39.01, 29.59, 0.33, 0.09, 0.36, 0.24, "plaster", mat="plaster",
          frame=True, erode=0.25, vox=0.075)
    hbox2(39.01, 29.95, 0.33, 0.09, 0.36, 0.24, "plaster", mat="plaster",
          frame=True, erode=0.25, vox=0.075,
          detail=dict(n=(1, 0, 0), kind="window", frame=False, shut=True,
                      rect=(0.22, 0.78, 0.15, 0.6)))
    # крыша, труба, крыльцо
    hbox2(37.925, 29.425, 0.57, 1.25, 1.05, 0.34, "tile_red",
          shape="gable", mat="tile", erode=1.2, vox=0.15, ends="timber")
    hbox2(38.5, 29.7, 0.53, 0.13, 0.13, 0.45, "gray", mat="stone",
          erode=0.5, vox=0.06, vent=2)
    hbox2(38.47, 30.4, 0, 0.16, 0.12, 0.035, "gray", erode=0.35, vox=0.05)
    # мебель первого этажа
    hbox2(38.1, 29.6, 0.1, 0.26, 0.17, 0.09, "wood_dark", mat="wood_dark",
          inside=True, erode=0.3, vox=0.075)
    hbox2(38.115, 29.61, 0.19, 0.23, 0.15, 0.045, "white", mat="cloth",
          inside=True, erode=0.3, vox=0.075)
    hbox2(38.75, 29.6, 0.1, 0.17, 0.17, 0.17, "gray", mat="stone",
          inside=True, erode=0.5, vox=0.075,
          detail=dict(n=(0, 1, 0), kind="firebox", frame=False,
                      rect=(0.0, 1.0, 0.15, 0.7)))
    hbox2(38.3, 29.9, 0.185, 0.2, 0.14, 0.025, "wood_light",
          mat="wood_light", inside=True, erode=0.3, vox=0.075)
    hbox2(38.375, 29.945, 0.118, 0.05, 0.05, 0.067, "wood_dark",
          mat="wood_dark", inside=True, erode=0.3, vox=0.075)
    hbox2(38.28, 29.88, 0.1, 0.24, 0.17, 0.018, "red", mat="cloth",
          inside=True, erode=0.3, vox=0.075)
    # мебель второго этажа
    hbox2(38.5, 29.7, 0.36, 0.17, 0.17, 0.17, "gray", mat="stone",
          inside=True, erode=0.5, vox=0.075,
          detail=dict(n=(0, 1, 0), kind="firebox", frame=False,
                      rect=(0.0, 1.0, 0.15, 0.7)))
    hbox2(38.68, 29.85, 0.36, 0.26, 0.17, 0.09, "wood_dark",
          mat="wood_dark", inside=True, erode=0.3, vox=0.075)
    hbox2(38.2, 29.7, 0.36, 0.24, 0.17, 0.018, "red", mat="cloth",
          inside=True, erode=0.3, vox=0.075)
    hbox2(38.15, 30.1, 0.36, 0.2, 0.12, 0.12, "wood_light",
          mat="wood_light", inside=True, erode=0.3, vox=0.075)
    # двор второго дома: бочка, ящик, колпак трубы
    s.append(dict(x=39.35, y=29.9, z=0, w=0.12, d=0.12, h=0.15,
                  color="wood_dark", shape="cylinder", mat="wood_dark",
                  vx=0.0, vy=0.0, vz=0.0, vox=0.05, erode=0.4))
    s.append(dict(x=38.2, y=30.55, z=0, w=0.12, d=0.12, h=0.12,
                  color="wood_light", shape="box", mat="wood_dark",
                  vx=0.0, vy=0.0, vz=0.0, vox=0.05, erode=0.6))
    s.append(dict(x=38.49, y=29.69, z=0.98, w=0.15, d=0.15, h=0.04,
                  color="gray", shape="box", mat="stone",
                  vx=0.0, vy=0.0, vz=0.0, vox=0.05, erode=0.3))
    # --- классы 3-5: древнерусские терема ---------------------------------
    # Каменный подклет, бревенчатые этажи, крутые щипцы с фронтонами,
    # сени-сеньки, сараи. Двери/окна-наличники — по всем четырём сторонам.
    WC = "wood_dark"
    WL = "wood_light"

    def segs_wall(hb, X, Y, Z, ln, h, along_x, n_out, col, mat, er,
                  kinds, th=0.09):
        # стена из равных сегментов: "w" сплошная, "o" окно, "d" дверь
        nseg = len(kinds)
        sl = ln / nseg
        for i, kd in enumerate(kinds):
            a = i * sl
            if along_x:
                x, y, w, d = X + a, Y, sl, th
            else:
                x, y, w, d = X, Y + a, th, sl
            kw = dict(erode=er, vox=0.075, sort_min=True)
            if kd == "o":
                u0 = max(0.14, 0.5 - 0.22 / sl)
                kw["detail"] = dict(n=n_out, kind="window", frame=False,
                                    shut=(n_out[0] != 0),
                                    rect=(u0, 1 - u0, 0.16, 0.62))
            elif kd == "d":
                u0 = max(0.10, 0.5 - 0.20 / sl)
                kw["detail"] = dict(n=n_out, kind="door", frame=False,
                                    rect=(u0 * 0.8, 1 - u0 * 0.8, 0.0, 0.66))
            hb(x, y, Z, w, d, h, col, mat=mat, **kw)

    def storey(hb, X, Y, Z, W, D, h, col, mat, er, f="", b="", l="",
               r="", th=0.09):
        # фасад смотрит на +y; боковые стены идут на всю глубину
        if l:
            segs_wall(hb, X, Y, Z, D, h, False, (-1, 0, 0), col, mat, er,
                      l, th)
        if r:
            segs_wall(hb, X + W - th, Y, Z, D, h, False, (1, 0, 0), col,
                      mat, er, r, th)
        if b:
            segs_wall(hb, X + th, Y, Z, W - 2 * th, h, True, (0, -1, 0),
                      col, mat, er, b, th)
        if f:
            segs_wall(hb, X + th, Y + D - th, Z, W - 2 * th, h, True,
                      (0, 1, 0), col, mat, er, f, th)

    def fnd(hb, X, Y, W, D):
        hb(X, Y, 0, W, D, 0.07, "gray", erode=0.45, vox=0.1, sort_min=True)

    def slab_floor(hb, X, Y, Z, W, D):
        hb(X + 0.03, Y + 0.03, Z, W - 0.06, D - 0.06, 0.03, "wood_light",
           mat="plank_light", inside=True, erode=1.35, vox=0.09,
           sort_min=True)

    def gable_roof(hb, X, Y, Z, W, D, h, ends="timber"):
        hb(X, Y, Z, W, D, h, "tile_red", shape="gable", mat="tile",
           erode=1.0, vox=0.15, ends=ends)

    def chimney(hb, X, Y, Z, hgt, vent=None):
        kw = {"vent": vent} if vent else {}
        hb(X - 0.06, Y - 0.06, Z, 0.12, 0.12, hgt, "gray", mat="stone",
           erode=0.5, vox=0.06, **kw)
        hb(X - 0.07, Y - 0.07, Z + hgt, 0.14, 0.14, 0.04, "gray",
           mat="stone", erode=0.3, vox=0.05)

    def porch(hb, X, Yf, Wp, roof_z):
        # крыльцо: ступени, четыре тумбы-столбика, навес красной плитой
        hb(X + 0.01, Yf + 0.10, 0.0, Wp - 0.02, 0.10, 0.035, "gray",
           mat="stone", erode=0.35, vox=0.05, sort_min=True)
        hb(X + 0.03, Yf + 0.02, 0.035, Wp - 0.06, 0.08, 0.035, "gray",
           mat="stone", erode=0.35, vox=0.05, sort_min=True)
        for xx in (X + 0.04, X + Wp - 0.09):
            hb(xx, Yf + 0.12, 0.07, 0.05, 0.05, roof_z - 0.07, WC,
               mat="wood_dark", erode=0.8, vox=0.05)
        hb(X - 0.02, Yf - 0.04, roof_z, Wp + 0.04, 0.26, 0.035, "tile_red",
           mat="tile", erode=1.0, vox=0.09)

    def stove(hb, X, Y, Z, n=(0, 1, 0)):
        hb(X, Y, Z, 0.17, 0.17, 0.17, "gray", mat="stone", inside=True,
           erode=0.4, vox=0.075,
           detail=dict(n=n, kind="firebox", frame=False,
                       rect=(0.0, 1.0, 0.15, 0.7)))

    def bed(hb, X, Y, Z):
        hb(X, Y, Z, 0.26, 0.15, 0.09, WC, mat="wood_dark", inside=True,
           erode=0.3, vox=0.075)
        hb(X + 0.015, Y + 0.01, Z + 0.09, 0.23, 0.13, 0.045, "white",
           mat="cloth", inside=True, erode=0.3, vox=0.075)
        hb(X + 0.02, Y + 0.02, Z + 0.135, 0.09, 0.11, 0.025, "red",
           mat="cloth", inside=True, erode=0.3, vox=0.075)

    def table(hb, X, Y, Z):
        hb(X, Y, Z + 0.085, 0.2, 0.14, 0.025, WL, mat="wood_light",
           inside=True, erode=0.3, vox=0.075)
        hb(X + 0.075, Y + 0.045, Z, 0.05, 0.05, 0.085, WC,
           mat="wood_dark", inside=True, erode=0.3, vox=0.075)

    def rug(hb, X, Y, Z):
        hb(X, Y, Z, 0.24, 0.17, 0.018, "red", mat="cloth", inside=True,
           erode=0.3, vox=0.075, sort_min=True)

    def yard_props(c=()):  # бочка и ящик у стены
        s.append(dict(x=20.22, y=8.30, z=0, w=0.12, d=0.12, h=0.15,
                      color="wood_dark", shape="cylinder", mat="wood_dark",
                      vx=0.0, vy=0.0, vz=0.0, vox=0.05, erode=0.4))

    # ============ КЛАСС 3 — ИЗБА (house=3) ============
    def hbox3(x, y, z, w, d, h, color, shape="box", mat="concrete", **kw):
        s.append(dict(x=x, y=y, z=z, w=w, d=d, h=h, color=color,
                      shape=shape, mat=mat, vx=0.0, vy=0.0, vz=0.0,
                      house=3, **kw))

    fnd(hbox3, 18.28, 7.42, 1.72, 1.30)
    X, Y, W, D = 18.35, 7.55, 1.10, 0.80
    slab_floor(hbox3, X, Y, 0.07, W, D)
    slab_floor(hbox3, X, Y, 0.43, W, D)
    storey(hbox3, X, Y, 0.07, W, D, 0.36, WC, "wood_dark", 0.9,
           f="owdwo", b="owowo", l="owo", r="owo")
    storey(hbox3, X, Y, 0.43, W, D, 0.33, WC, "wood_dark", 0.9,
           f="owowo", b="owowo", l="owo", r="owo")
    gable_roof(hbox3, X - 0.085, Y - 0.10, 0.76, W + 0.17, D + 0.20, 0.36)
    chimney(hbox3, 19.15, 7.95, 0.07, 1.20, vent=3)
    porch(hbox3, 18.72, 8.26, 0.44, 0.37)
    # сени-пристройка в виде сарая у правой стены
    Sx, Sy = 19.50, 7.62
    storey(hbox3, Sx, Sy, 0.07, 0.45, 0.60, 0.30, WL, "wood_light", 1.0,
           f="dw", b="w", l="w", r="wo")
    gable_roof(hbox3, Sx - 0.03, Sy - 0.05, 0.37, 0.51, 0.70, 0.24)
    # внутренность: печь, койка, стол, лежанка-полатэ
    stove(hbox3, 18.42, 7.93, 0.10)
    bed(hbox3, 19.10, 7.62, 0.10)
    table(hbox3, 18.60, 7.62, 0.10)
    rug(hbox3, 18.78, 8.00, 0.10)
    yard_props()

    # ============ КЛАСС 4 — ТЕРЕМ (house=4) ============
    def hbox4(x, y, z, w, d, h, color, shape="box", mat="concrete", **kw):
        s.append(dict(x=x, y=y, z=z, w=w, d=d, h=h, color=color,
                      shape=shape, mat=mat, vx=0.0, vy=0.0, vz=0.0,
                      house=4, **kw))

    fnd(hbox4, 6.15, 30.15, 2.0, 1.6)
    X, Y, W, D = 6.35, 30.30, 1.34, 1.02
    slab_floor(hbox4, X, Y, 0.07, W, D)
    slab_floor(hbox4, X, Y, 0.47, W, D)
    slab_floor(hbox4, X, Y, 0.81, W, D)
    # подклет — камень
    storey(hbox4, X, Y, 0.07, W, D, 0.40, "gray", "stone", 0.65,
           f="odo", b="owo", l="owo", r="owo")
    # два бревенчатых этажа
    storey(hbox4, X, Y, 0.47, W, D, 0.34, WC, "wood_dark", 0.9,
           f="owowo", b="owowo", l="owo", r="owo")
    storey(hbox4, X, Y, 0.81, W, D, 0.33, WC, "wood_dark", 0.9,
           f="owowo", b="owowo", l="owo", r="owo")
    gable_roof(hbox4, 6.26, 30.19, 1.14, 1.52, 1.24, 0.46)
    chimney(hbox4, 7.45, 30.60, 0.07, 1.64, vent=4)
    # слуховое окно на переднем скате
    hbox4(6.92, 31.15, 1.14, 0.26, 0.16, 0.37, WC, mat="wood_dark",
          erode=0.9, vox=0.075,
          detail=dict(n=(0, 1, 0), kind="window", frame=False,
                      rect=(0.18, 0.82, 0.10, 0.86)))
    hbox4(6.90, 31.13, 1.51, 0.30, 0.20, 0.035, "tile_red", mat="tile",
          erode=1.0, vox=0.09)
    # сени-сеньки: входная башенка с шатровой крышей
    Ts, Tsd = 6.57, 0.50
    Yt = 31.32
    slab_floor(hbox4, Ts, Yt, 0.07, Tsd, Tsd)
    storey(hbox4, Ts, Yt, 0.07, Tsd, Tsd, 0.36, WC, "wood_dark", 0.9,
           f="wo", l="wd", r="o")
    storey(hbox4, Ts, Yt, 0.43, Tsd, Tsd, 0.36, WC, "wood_dark", 0.9,
           f="o", l="o", r="o")
    slab_floor(hbox4, Ts, Yt, 0.43, Tsd, Tsd)
    hbox4(Ts - 0.02, Yt - 0.02, 0.79, Tsd + 0.04, Tsd + 0.04, 0.34,
          "tile_red", shape="pyramid", mat="tile", erode=1.0, vox=0.15)
    hbox4(6.62, 31.36, 0.0, 0.16, 0.16, 0.04, "gray", mat="stone",
          erode=0.35, vox=0.05, sort_min=True)
    # внутренность
    stove(hbox4, 6.46, 30.42, 0.10)
    bed(hbox4, 7.32, 30.42, 0.10)
    table(hbox4, 6.52, 30.98, 0.10)
    rug(hbox4, 6.92, 30.60, 0.10)
    hbox4(7.40, 31.02, 0.10, 0.16, 0.14, 0.10, WL, mat="wood_light",
          inside=True, erode=0.3, vox=0.05)
    bed(hbox4, 6.46, 30.42, 0.50)

    # ============ КЛАСС 5 — БОЛЬШОЙ ТЕРЕМ (house=5) ============
    def hbox5(x, y, z, w, d, h, color, shape="box", mat="concrete", **kw):
        s.append(dict(x=x, y=y, z=z, w=w, d=d, h=h, color=color,
                      shape=shape, mat=mat, vx=0.0, vy=0.0, vz=0.0,
                      house=5, **kw))

    fnd(hbox5, 23.85, 21.55, 2.55, 2.05)
    # башня слева
    XT, YT, ST = 23.98, 21.85, 0.58
    slab_floor(hbox5, XT, YT, 0.07, ST, ST)
    slab_floor(hbox5, XT, YT, 0.45, ST, ST)
    slab_floor(hbox5, XT, YT, 0.81, ST, ST)
    storey(hbox5, XT, YT, 0.07, ST, ST, 0.38, "gray", "stone", 0.65,
           f="o", b="o", l="o", r="o")
    storey(hbox5, XT, YT, 0.45, ST, ST, 0.36, WC, "wood_dark", 0.9,
           f="o", b="o", l="o", r="o")
    storey(hbox5, XT, YT, 0.81, ST, ST, 0.34, WC, "wood_dark", 0.9,
           f="o", b="o", l="o", r="o")
    hbox5(XT - 0.03, YT - 0.03, 1.15, ST + 0.06, ST + 0.06, 0.50,
          "tile_red", shape="pyramid", mat="tile", erode=1.0, vox=0.15)
    # главный корпус: подклет, сруб в три этажа с уступами, высокий щипец
    X, Y, W, D = 24.62, 21.85, 1.15, 0.95
    slab_floor(hbox5, X, Y, 0.07, W, D)
    storey(hbox5, X, Y, 0.07, W, D, 0.40, "gray", "stone", 0.65,
           f="odo", b="owo", l="owo", r="owo")
    slab_floor(hbox5, X, Y, 0.47, W, D)
    storey(hbox5, X, Y, 0.47, W, D, 0.34, WC, "wood_dark", 0.9,
           f="owowo", b="owowo", l="owo", r="owo")
    X2, W2 = 24.67, 1.05
    slab_floor(hbox5, X2, Y, 0.81, W2, D)
    storey(hbox5, X2, Y, 0.81, W2, D, 0.33, WC, "wood_dark", 0.9,
           f="owowo", b="owowo", l="owo", r="owo")
    X3, W3 = 24.72, 0.95
    slab_floor(hbox5, X3, Y, 1.14, W3, D)
    storey(hbox5, X3, Y, 1.14, W3, D, 0.30, WC, "wood_dark", 0.9,
           f="owo", b="owo", l="wo", r="wo")
    gable_roof(hbox5, 24.53, 21.76, 1.44, 1.33, 1.18, 0.52)
    chimney(hbox5, 25.30, 22.15, 0.07, 1.93, vent=5)
    # слуховое окно
    hbox5(24.90, 22.58, 1.44, 0.28, 0.18, 0.36, WC, mat="wood_dark",
          erode=0.9, vox=0.075,
          detail=dict(n=(0, 1, 0), kind="window", frame=False,
                      rect=(0.18, 0.82, 0.10, 0.86)))
    hbox5(24.87, 22.55, 1.80, 0.34, 0.24, 0.035, "tile_red", mat="tile",
          erode=1.0, vox=0.09)
    # крыло справа
    XW, YW, WW, DW = 25.83, 21.90, 0.62, 0.72
    slab_floor(hbox5, XW, YW, 0.07, WW, DW)
    slab_floor(hbox5, XW, YW, 0.41, WW, DW)
    storey(hbox5, XW, YW, 0.07, WW, DW, 0.34, WL, "wood_light", 1.0,
           f="ow", b="ow", l="wo", r="wo")
    storey(hbox5, XW, YW, 0.44, WW, DW, 0.32, WL, "wood_light", 1.0,
           f="ow", b="ow", l="wo", r="wo")
    gable_roof(hbox5, XW - 0.05, YW - 0.05, 0.76, WW + 0.10,
               DW + 0.10, 0.30)
    # крыльцо главного корпуса
    porch(hbox5, 24.91, 22.71, 0.50, 0.45)
    # внутренность
    stove(hbox5, 25.50, 21.94, 0.10, n=(0, 1, 0))
    bed(hbox5, 24.72, 21.94, 0.10)
    table(hbox5, 25.05, 22.42, 0.10)
    rug(hbox5, 24.95, 22.10, 0.10)
    hbox5(25.48, 22.52, 0.10, 0.16, 0.14, 0.10, WL, mat="wood_light",
          inside=True, erode=0.3, vox=0.05)
    bed(hbox5, 24.72, 21.94, 0.50)
    table(hbox5, 25.05, 22.42, 0.84)
    hbox5(XT + 0.16, YT + 0.16, 0.10, 0.16, 0.14, 0.10, WL,
          mat="wood_light", inside=True, erode=0.3, vox=0.05)
    # двор: бочка и ящик
    s.append(dict(x=26.62, y=22.60, z=0, w=0.12, d=0.12, h=0.15,
                  color="wood_dark", shape="cylinder", mat="wood_dark",
                  vx=0.0, vy=0.0, vz=0.0, vox=0.05, erode=0.4))
    s.append(dict(x=26.55, y=21.85, z=0, w=0.12, d=0.12, h=0.12,
                  color="wood_light", shape="box", mat="wood_dark",
                  vx=0.0, vy=0.0, vz=0.0, vox=0.05, erode=0.6))
    # ============ ЭПОХИ: от каменного века до наших дней ============
    # 7 районов по 5 классов (E3 = текущий средневековый посёлок выше).
    NID = [5]

    def nid():
        NID[0] += 1
        return NID[0]

    def _gz(x, y):
        best = 1e9
        for dx in (-1.2, -0.4, 0.4, 1.2):
            for dy in (-1.2, -0.4, 0.4, 1.2):
                g = ground_height_at(x + 0.5 + dx, y + 0.5 + dy)
                if g is not None and g < best:
                    best = g
        if best > 1e8:
            best = 0.0
        return max(-0.2, min(0.4, math.floor(best / 0.05) * 0.05 - 0.045))

    def hbx_(hid, zb=0.0):
        def _f(x, y, z, w, d, h, color, shape="box", mat="concrete", **kw):
            if kw.pop("zb_abs", False):
                zb_ = 0.0
            else:
                zb_ = zb
            s.append(dict(x=x, y=y, z=z + zb_, w=w, d=d, h=h, color=color,
                          shape=shape, mat=mat, vx=0.0, vy=0.0, vz=0.0,
                          house=hid, **kw))
        return _f

    DISTRICTS = [(58, 66), (96, 52), (140, 72), (122, 112),
                 (74, 110), (100, 84), (126, 138)]

    def spot(di, i):
        cx, cy = DISTRICTS[di]
        ang = 2.4 * i + hash01(cx, cy, 11) * 6.283
        rr = 1.7 + (i % 3) * 1.9
        x = cx + math.cos(ang) * rr + (hash01(i, cx, 7) - 0.5) * 2.2
        y = cy + math.sin(ang) * rr + (hash01(i, cy, 8) - 0.5) * 2.2
        if abs(x - y) < 3.5:
            x += 4.2
        return x, y

    # ============ НОВЫЕ ДОМА СРЕДНЕВЕКОВЬЯ: фахверк-лавка, таверна =========
    # (ids 6, 7 — после C1..C5)
    for i, (gx, gy) in enumerate([(46.0, 44.0), (49.5, 44.0)]):
        hid = nid()
        hb = hbx_(hid, _gz(gx, gy))
        x, y = gx, gy
        if i == 0:  # ФАХВЕРК-ЛАВКА
            fw, fd = 1.15, 0.95
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            slab_floor(hb, x, y, 0.07, fw, fd)
            slab_floor(hb, x, y, 0.42, fw, fd)
            # каменный первый этаж, узкое окно-витрина + дверь
            storey(hb, x, y, 0.07, fw, fd, 0.35, "gray", "stone", 0.6,
                   f="wdow", b="owwo", l="w", r="w", th=0.1)
            # нависающий фахверковый верх: шире, тёмные балки-кресты
            X2, Y2 = x - 0.06, y - 0.05
            fw2, fd2 = fw + 0.12, fd + 0.10
            storey(hb, X2, Y2, 0.42, fw2, fd2, 0.33, "plaster", "plaster",
                   0.35, f="woow", b="woww", l="ow", r="wo", th=0.09)
            for bx_ in (X2 + 0.12, X2 + fw2 - 0.20):  # балки фронта
                hb(bx_, Y2 + fd2 - 0.075, 0.42, 0.08, 0.03, 0.33, "wood_dark",
                   mat="wood_dark", erode=0.7, vox=0.05, sort_min=True)
            gable_roof(hb, X2 - 0.06, Y2 - 0.07, 0.75, fw2 + 0.12,
                       fd2 + 0.16, 0.40)
            chimney(hb, x + 0.22, y + 0.45, 0.07, 1.24, vent=hid)
            table(hb, x + 0.2, y + 0.2, 0.10)
            rug(hb, x + 0.7, y + 0.5, 0.10)
        else:  # ТАВЕРНА
            fw, fd = 1.5, 0.85
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            slab_floor(hb, x, y, 0.07, fw, fd)
            slab_floor(hb, x, y, 0.44, fw, fd)
            storey(hb, x, y, 0.07, fw, fd, 0.37, WC, "wood_dark", 0.9,
                   f="owDow".replace("D", "d") + "w", b="owowo", l="owo",
                   r="owo")
            storey(hb, x, y, 0.44, fw, fd, 0.33, "plaster", "plaster", 0.35,
                   f="wowow", b="owowo", l="owo", r="owo")
            gable_roof(hb, x - 0.09, y - 0.11, 0.77, fw + 0.18, fd + 0.24,
                       0.46)
            chimney(hb, x + fw - 0.35, y + 0.42, 0.07, 1.34, vent=hid)
            # вывеска на кронштейне у входа
            hb(x + 0.44, y + fd + 0.02, 0.62, 0.04, 0.18, 0.04, "wood_dark",
               mat="wood_dark", erode=0.8, vox=0.04)
            hb(x + 0.40, y + fd + 0.16, 0.52, 0.16, 0.04, 0.10, "wood_light",
               mat="plank_light", erode=0.8, vox=0.04)
            table(hb, x + 0.2, y + 0.2, 0.10)
            table(hb, x + 0.8, y + 0.5, 0.10)
            stove(hb, x + 0.15, y + 0.6, 0.075)

    # ============ E0 КАМЕННЫЙ ВЕК (ids 8-12) ============
    for i in range(5):
        x, y = spot(0, i)
        hid = nid()
        hb = hbx_(hid, _gz(x, y))
        if i == 0:  # КУХНЯ: каменный очаг, подвешенный котел, полка
            for dx, dy in ((0, 0), (0.95, 0), (0.05, 0.85), (0.95, 0.85)):
                hb(x + dx, y + dy, 0, 0.07, 0.07, 0.44, "wood_dark",
                   mat="wood_dark", erode=1.0, vox=0.05)
            hb(x - 0.06, y - 0.10, 0.44, 1.12, 1.05, 0.09, "straw",
               shape="pyramid", mat="straw", erode=2.4, vox=0.09)
            # каменный очаг с тёмным жерлом
            hb(x + 0.08, y + 0.48, 0, 0.34, 0.30, 0.26, "gray",
               mat="stone", erode=0.5, vox=0.06)
            hb(x + 0.16, y + 0.56, 0.12, 0.18, 0.14, 0.10, "charcoal",
               mat="stone", erode=0.6, vox=0.04, sort_min=True)
            # стойка-крюк и подвешенный котел
            hb(x + 0.42, y + 0.44, 0.26, 0.05, 0.05, 0.16, "wood_dark",
               mat="wood_dark", erode=0.9, vox=0.04, sort_min=True)
            hb(x + 0.39, y + 0.42, 0.34, 0.11, 0.11, 0.08, "charcoal",
               mat="stone", erode=0.6, vox=0.04, sort_min=True)
            # полка с кувшинами
            hb(x + 0.62, y + 0.10, 0, 0.26, 0.14, 0.05, "wood_dark",
               mat="wood_dark", erode=0.9, vox=0.04)
            hb(x + 0.64, y + 0.12, 0.05, 0.07, 0.07, 0.10, "bone",
               mat="bone", erode=0.7, vox=0.04, sort_min=True)
            hb(x + 0.76, y + 0.12, 0.05, 0.07, 0.07, 0.12, "plank_dark",
               mat="leather", erode=0.9, vox=0.04, sort_min=True)
        elif i == 1:  # ШАЛАШ ИЗ ШКУР: треугольная А-рама, шкуры с
            # тёмными полосами и светлыми пятнами (олений узор —
            # рисуется в draw_gable, ends="hide")
            for dx, dy in ((0.06, 0.06), (0.89, 0.06), (0.06, 0.89),
                           (0.89, 0.89)):
                hb(x + dx, y + dy, 0, 0.07, 0.07, 0.12, "wood_dark",
                   mat="wood_dark", erode=1.0, vox=0.04, sort_min=True)
            # А-рама спереди: две стойки-дуги + поперечина
            hb(x + 0.08, y + 0.40, 0, 0.05, 0.05, 0.38, "wood_light",
               mat="wood_light", erode=1.2, vox=0.035, sort_min=True)
            hb(x + 0.17, y + 0.31, 0.36, 0.05, 0.05, 0.34, "wood_light",
               mat="wood_light", erode=1.2, vox=0.035, sort_min=True)
            hb(x + 0.28, y + 0.33, 0.42, 0.44, 0.04, 0.04, "wood_dark",
               mat="wood_dark", erode=1.0, vox=0.035, sort_min=True)
            # пол-основание из шкур
            hb(x - 0.02, y - 0.02, 0.02, 1.04, 1.00, 0.08, "leather",
               mat="leather", erode=0.9, vox=0.07, sort_min=True)
            # крутой шатёр: два ската из шкур (треугольник в профиль)
            hb(x, y, 0.08, 1.00, 0.95, 0.92, "leather", shape="gable",
               mat="leather", ends="hide", erode=0.9, vox=0.08)
            # коньковый брус
            hb(x - 0.05, y + 0.455, 1.00, 1.10, 0.06, 0.05, "wood_dark",
               mat="wood_dark", erode=1.0, vox=0.035, sort_min=True)
            # вход на переднем скате: тёмная щель + створки
            hb(x + 0.36, y + 0.87, 0.08, 0.26, 0.07, 0.34, "charcoal",
               mat="leather", erode=0.9, vox=0.04, sort_min=True)
            hb(x + 0.31, y + 0.875, 0.08, 0.05, 0.06, 0.30, "plank_dark",
               mat="leather", erode=0.9, vox=0.04)
            hb(x + 0.64, y + 0.875, 0.08, 0.05, 0.06, 0.30, "plank_dark",
               mat="leather", erode=0.9, vox=0.04)
            hb(x + 0.28, y + 0.83, 0.44, 0.44, 0.07, 0.14, "plank_light",
               mat="leather", erode=0.9, vox=0.04, sort_min=True)
            # флаг на макушке
            hb(x + 0.455, y + 0.455, 1.02, 0.035, 0.035, 0.30,
               "wood_light", mat="wood_light", erode=1.2, vox=0.04)
            hb(x + 0.462, y + 0.462, 1.24, 0.09, 0.02, 0.07, "red",
               mat="cloth", erode=1.0, vox=0.03, sort_min=True)
        elif i == 2:  # ДВУСКАТНЫЙ ШАЛАШ (жилище ур.1, 1 чел.): плетёные
            # прутья двух скатов, жерди-рёбра, вход со шкурной занавесью
            hb(x, y, 0.06, 0.95, 0.72, 0.50, "plank_light",
               shape="gable", mat="wattle", erode=1.4, vox=0.09)
            # жерди-рёбра на обоих скатах
            for sgn in (0, 1):
                for zz, yy in ((0.20, 0.63), (0.36, 0.52)):
                    yoff = yy if sgn == 0 else 0.72 - yy
                    hb(x + 0.17, y + yoff - 0.02, zz, 0.60, 0.05, 0.04,
                       "wood_dark", mat="wood_dark", erode=0.9, vox=0.04,
                       sort_min=True)
            # коньковый брус
            hb(x - 0.04, y + 0.335, 0.62, 1.03, 0.06, 0.05, "wood_dark",
               mat="wood_dark", erode=1.0, vox=0.035, sort_min=True)
            # угловые колышки
            for dx, dy in ((0.02, 0.02), (0.86, 0.02), (0.02, 0.62),
                           (0.86, 0.62)):
                hb(x + dx, y + dy, 0, 0.07, 0.07, 0.14, "wood_dark",
                   mat="wood_dark", erode=1.0, vox=0.04, sort_min=True)
            # вход: тёмная щель + шкурная занавесь
            hb(x + 0.33, y + 0.62, 0.06, 0.28, 0.06, 0.34, "charcoal",
               mat="leather", erode=0.9, vox=0.04, sort_min=True)
            hb(x + 0.29, y + 0.63, 0.06, 0.05, 0.06, 0.30, "plank_dark",
               mat="leather", erode=0.9, vox=0.04)
            hb(x + 0.62, y + 0.63, 0.06, 0.05, 0.06, 0.30, "plank_dark",
               mat="leather", erode=0.9, vox=0.04)
            # маленький флаг на коньке
            hb(x + 0.47, y + 0.335, 0.64, 0.03, 0.03, 0.20, "wood_light",
               mat="wood_light", erode=1.2, vox=0.03, sort_min=True)
            hb(x + 0.475, y + 0.34, 0.80, 0.09, 0.015, 0.06, "red",
               mat="cloth", erode=1.0, vox=0.03, sort_min=True)
        elif i == 3:  # ДВУСКАТНЫЙ ШАЛАШ (углубление-вход + шторы из шкур)
            hb(x - 0.04, y - 0.04, 0, 0.85, 0.68, 0.44, "straw",
               shape="gable", mat="straw", erode=2.4, vox=0.11, ends="timber")
            hb(x + 0.24, y + 0.60, 0.0, 0.30, 0.035, 0.30, "charcoal",
               mat="straw", erode=1.6, vox=0.04, sort_min=True)  # тёмный вход
            hb(x + 0.20, y + 0.60, 0.0, 0.045, 0.05, 0.26, "leather",
               mat="leather", erode=0.9, vox=0.04)  # занавесь слева
            hb(x + 0.535, y + 0.60, 0.0, 0.045, 0.05, 0.26, "leather",
               mat="leather", erode=0.9, vox=0.04)  # занавесь справа
            for dx in (0.0, 0.77):
                hb(x + dx, y + 0.3, 0, 0.07, 0.07, 0.28, "wood_light",
                   mat="wood_light", erode=1.2, vox=0.04)
        else:  # МАСТЕРСКАЯ: доски крыши внахлёст + рабочий камень
            for dx, dy in ((0, 0), (0.95, 0), (0, 0.72), (0.95, 0.72)):
                hb(x + dx, y + dy, 0, 0.07, 0.07, 0.46, "wood_light",
                   mat="wood_light", erode=1.2, vox=0.05)
            for k in range(5):  # доски с перехлёстом: лесенка тонов
                hb(x - 0.07, y - 0.07 + 0.185 * k, 0.46 + 0.012 * k, 1.16,
                   0.20, 0.035, "plank_light" if k % 2 else "plank_dark",
                   mat="plank_light", erode=1.2, vox=0.07, sort_min=True)
            hb(x + 0.42, y + 0.22, 0, 0.24, 0.18, 0.13, "gray", shape="rock",
               mat="stone", erode=0.4, vox=0.05)
            hb(x + 0.46, y + 0.24, 0.13, 0.14, 0.07, 0.05, "wood_dark",
               mat="wood_dark", erode=0.8, vox=0.04)  # заготовка на камне

    # ============ E1 РАННЕЕ ДЕРЕВО (ids 13-17): все разные ============
    for i in range(5):
        x, y = spot(1, i)
        hid = nid()
        hb = hbx_(hid, _gz(x, y))
        if i == 0:  # круглая хижина: каменное кольцо, стены, конус с поясом
            hb(x - 0.04, y - 0.04, 0, 0.88, 0.88, 0.06, "gray",
               shape="cylinder", mat="stone", erode=0.5, vox=0.06)
            hb(x, y, 0.04, 0.80, 0.80, 0.30, "wattle", shape="cylinder",
               mat="wattle", erode=1.4, vox=0.08,
               detail=dict(n=(0, 1, 0), kind="door", frame=False,
                           rect=(0.30, 0.58, 0.0, 0.72)))
            # конус из соломы: 3 нахлёстных яруса
            hb(x - 0.07, y - 0.07, 0.32, 0.94, 0.94, 0.20, "straw",
               shape="pyramid", mat="straw", erode=2.4, vox=0.10)
            hb(x + 0.07, y + 0.07, 0.48, 0.68, 0.68, 0.18, "plank_light",
               shape="pyramid", mat="straw", erode=2.4, vox=0.07)
            hb(x + 0.18, y + 0.18, 0.62, 0.48, 0.48, 0.16, "straw",
               shape="pyramid", mat="straw", erode=2.4, vox=0.06)
            # колья-рёбра по ободу конуса (видны из-под краёв)
            for a in range(7):
                ca = 6.283 * a / 7 + 0.35
                bx_ = x + 0.40 + math.cos(ca) * 0.40
                by_ = y + 0.40 + math.sin(ca) * 0.40
                hb(bx_ - 0.025, by_ - 0.025, 0.20, 0.05, 0.05, 0.18,
                   "wood_dark", mat="wood_dark", erode=1.0, vox=0.035,
                   sort_min=True)
            # оконце с бревенчатым框ом
            hb(x + 0.18, y + 0.05, 0.10, 0.18, 0.06, 0.10, "wood_dark",
               mat="wood_dark", erode=0.9, vox=0.04, sort_min=True)
            hb(x + 0.21, y + 0.07, 0.115, 0.12, 0.03, 0.07, "charcoal",
               mat="wattle", erode=1.4, vox=0.04, sort_min=True)
            # дымовая труба-шест + дымарь-шкурка
            hb(x + 0.385, y + 0.385, 0.72, 0.04, 0.04, 0.22, "wood_light",
               mat="wood_light", erode=1.2, vox=0.04)
            hb(x + 0.392, y + 0.392, 0.88, 0.09, 0.02, 0.07, "plank_dark",
               mat="cloth", erode=1.0, vox=0.03, sort_min=True)
            # порог-мех у двери
            hb(x + 0.26, y + 0.74, 0.045, 0.28, 0.10, 0.02, "plank_light",
               mat="leather", erode=0.9, vox=0.03, sort_min=True)
            # камень-огниво у стены
            hb(x - 0.10, y + 0.62, 0, 0.10, 0.09, 0.06, "gray",
               shape="rock", mat="stone", erode=0.5, vox=0.04)
        elif i == 1:  # длинный дом с двумя дверями
            fw, fd = 1.5, 0.62
            slab_floor(hb, x, y, 0.05, fw, fd)
            storey(hb, x, y, 0.05, fw, fd, 0.27, "wattle", "wattle", 1.5,
                   f="dwowd", b="wwwww", l="w", r="o", th=0.09)
            hb(x - 0.05, y - 0.06, 0.32, fw + 0.1, fd + 0.13, 0.30, "straw",
               shape="gable", mat="straw", erode=2.4, vox=0.11,
               ends="timber")
        elif i == 2:  # хижина на высоких сваях с лесенкой
            fw, fd = 0.72, 0.62
            for dx, dy in ((0.03, 0.03), (fw - 0.09, 0.03), (0.03, fd - 0.09),
                           (fw - 0.09, fd - 0.09), (fw / 2 - 0.03, 0.03),
                           (fw / 2 - 0.03, fd - 0.09)):
                hb(x + dx, y + dy, 0, 0.06, 0.06, 0.26, "wood_dark",
                   mat="wood_dark", erode=0.9, vox=0.05)
            hb(x - 0.03, y - 0.03, 0.26, fw + 0.06, fd + 0.06, 0.035,
               "wood_dark", mat="plank_dark", erode=1.1, vox=0.07,
               sort_min=True)
            for k in range(4):  # лесенка к настилу
                hb(x + fw / 2 - 0.10, y + fd + 0.03 + 0.09 * k,
                   0.26 - 0.065 * (k + 1), 0.20, 0.09, 0.03, "wood_dark",
                   mat="plank_dark", erode=1.1, vox=0.05, sort_min=True)
            storey(hb, x, y, 0.295, fw, fd, 0.26, "wattle", "wattle", 1.5,
                   f="dw", b="w", l="w", r="o", th=0.08)
            hb(x - 0.06, y - 0.05, 0.555, fw + 0.12, fd + 0.11, 0.28, "straw",
               shape="gable", mat="straw", erode=2.4, vox=0.11,
               ends="timber")
        elif i == 3:  # ХИЖИНА ВОЖДЯ: круглая каменная, большой конус, флаг
            # каменный цоколь-кольцо
            hb(x - 0.06, y - 0.06, 0, 1.02, 1.02, 0.16, "gray",
               shape="cylinder", mat="stone", erode=0.5, vox=0.07)
            # стены из толстых брёвен (кольцо)
            hb(x, y, 0.14, 0.90, 0.90, 0.30, "wood_dark",
               shape="cylinder", mat="wood_dark", erode=0.75, vox=0.08,
               detail=dict(n=(0, 1, 0), kind="door", frame=False,
                           rect=(0.30, 0.58, 0.0, 0.78)))
            # высокий конус: 4 яруса, 2-й — красная лента вождя
            hb(x - 0.10, y - 0.10, 0.40, 1.10, 1.10, 0.24, "straw",
               shape="pyramid", mat="straw", erode=2.4, vox=0.10)
            hb(x + 0.05, y + 0.05, 0.58, 0.80, 0.80, 0.22, "red",
               shape="pyramid", mat="cloth", erode=1.0, vox=0.06)
            hb(x + 0.17, y + 0.17, 0.76, 0.56, 0.56, 0.20, "plank_light",
               shape="pyramid", mat="straw", erode=2.4, vox=0.06)
            hb(x + 0.26, y + 0.26, 0.92, 0.40, 0.40, 0.18, "straw",
               shape="pyramid", mat="straw", erode=2.4, vox=0.05)
            # колья-рёбра торчат из-под конуса
            for a in range(8):
                ca = 6.283 * a / 8
                bx_ = x + 0.45 + math.cos(ca) * 0.45
                by_ = y + 0.45 + math.sin(ca) * 0.45
                hb(bx_ - 0.025, by_ - 0.025, 0.28, 0.05, 0.05, 0.20,
                   "wood_dark", mat="wood_dark", erode=1.0, vox=0.035,
                   sort_min=True)
            # флаг-шест с полотнищем
            hb(x + 0.435, y + 0.435, 1.06, 0.04, 0.04, 0.28,
               "wood_light", mat="wood_light", erode=1.2, vox=0.04)
            hb(x + 0.442, y + 0.442, 1.28, 0.16, 0.02, 0.09, "red",
               mat="cloth", erode=1.0, vox=0.03, sort_min=True)
            # каменные ступени ко входу
            for k in range(3):
                hb(x + 0.32, y + 0.92 + 0.075 * k, 0.04 - 0.014 * k,
                   0.26, 0.09, 0.035, "gray", mat="stone", erode=0.5,
                   vox=0.05, sort_min=True)
            # очаг-камень у стены
            hb(x - 0.12, y + 0.58, 0, 0.12, 0.10, 0.07, "gray",
               shape="rock", mat="stone", erode=0.5, vox=0.05)
            hb(x - 0.09, y + 0.60, 0.07, 0.06, 0.05, 0.02, "charcoal",
               mat="stone", erode=0.6, vox=0.03, sort_min=True)
        else:  # ХИЖИНА-ГАЛЕРЕЯ: длинная, каменный низ, дерево, галерея
            fw, fd = 1.55, 0.80
            hb(x - 0.05, y - 0.05, 0, fw + 0.10, fd + 0.10, 0.06, "gray",
               mat="stone", erode=0.5, vox=0.07)
            # первый этаж — камень, второй — дерево/плетёнка
            storey(hb, x, y, 0.05, fw, fd, 0.24, "gray", "stone", 0.55,
                   f="dow", b="o", l="o", r="o", th=0.09)
            storey(hb, x, y, 0.29, fw, fd, 0.24, "wattle", "wattle", 1.4,
                   f="wow", b="w", l="o", r="o", th=0.09)
            # широкая соломенная крыша-щипец
            hb(x - 0.09, y - 0.09, 0.53, fw + 0.18, fd + 0.18, 0.30,
               "straw", shape="gable", mat="straw", erode=2.4, vox=0.11,
               ends="timber")
            # галерея спереди: столбики + настил + навес
            for dx in (0.02, 0.52, 1.02, 1.52):
                hb(x + dx, y + fd + 0.14, 0, 0.055, 0.055, 0.42,
                   "wood_dark", mat="wood_dark", erode=0.9, vox=0.04)
            hb(x - 0.04, y + fd - 0.02, 0.42, fw + 0.08, 0.30, 0.035,
               "wood_dark", mat="plank_dark", erode=1.1, vox=0.06,
               sort_min=True)
            hb(x - 0.08, y + fd + 0.02, 0.455, fw + 0.16, 0.40, 0.03,
               "straw", mat="straw", erode=2.4, vox=0.06, sort_min=True)
            # лесенка на галерею
            for k in range(4):
                hb(x + fw / 2 - 0.10, y + fd + 0.30 + 0.075 * k,
                   0.42 - 0.105 * (k + 1), 0.20, 0.08, 0.03, "wood_dark",
                   mat="plank_dark", erode=1.1, vox=0.05, sort_min=True)
            # трубы с двух концов + камни у подножия
            hb(x + 0.18, y + 0.28, 0.05, 0.09, 0.09, 0.56, "gray",
               mat="stone", erode=0.5, vox=0.06, vent=hid)
            hb(x + fw - 0.30, y + 0.2, 0.05, 0.09, 0.09, 0.52, "gray",
               mat="stone", erode=0.5, vox=0.06, vent=hid)
            hb(x - 0.16, y - 0.12, 0, 0.11, 0.10, 0.07, "gray",
               shape="rock", mat="stone", erode=0.5, vox=0.05)

    # ============ E2 РУБЛЕНЫЕ ИЗБЫ (ids 18-22) ============
    for i in range(5):
        x, y = spot(2, i)
        hid = nid()
        hb = hbx_(hid, _gz(x, y))
        if i == 0:  # классическая рубленая изба
            fw, fd = 0.9, 0.72
            hb(x + 0.02, y + 0.02, 0, fw - 0.04, fd - 0.04, 0.07, "wood_dark",
               mat="wood_dark", erode=0.6, vox=0.1, sort_min=True)
            storey(hb, x, y, 0.07, fw, fd, 0.34, "wood_dark", "wood_dark",
                   0.9, f="dw", b="ow", l="ow", r="w", th=0.1)
            hb(x - 0.06, y - 0.06, 0.41, fw + 0.12, fd + 0.12, 0.34,
               "wood_dark", shape="gable", mat="wood_dark", erode=0.75,
               vox=0.12, ends="timber")
            chimney(hb, x + fw * 0.25, y + fd * 0.5, 0.07, 0.80, vent=hid)
            stove(hb, x + 0.1, y + 0.1, 0.075)
        elif i == 1:  # ИЗБА С КРЫЛЬЦОМ И ЛЕСЕНКОЙ (переделана)
            fw, fd = 0.9, 0.74
            hb(x + 0.02, y + 0.02, 0, fw - 0.04, fd - 0.04, 0.12, "wood_dark",
               mat="wood_dark", erode=0.6, vox=0.1, sort_min=True)
            storey(hb, x, y, 0.12, fw, fd, 0.34, "wood_dark", "wood_dark",
                   0.9, f="dwo", b="w", l="ow", r="o", th=0.1)
            hb(x - 0.06, y - 0.06, 0.46, fw + 0.12, fd + 0.12, 0.34,
               "wood_dark", shape="gable", mat="wood_dark", erode=0.75,
               vox=0.12, ends="timber")
            # крыльцо на столбиках + лестница из четырёх ступеней
            hb(x + 0.10, y + fd + 0.03, 0.10, 0.34, 0.16, 0.025, "wood_dark",
               mat="plank_dark", erode=0.8, vox=0.05, sort_min=True)
            for dx in (0.12, 0.40):
                hb(x + dx, y + fd + 0.14, 0, 0.04, 0.04, 0.10, "wood_dark",
                   mat="wood_dark", erode=0.9, vox=0.04)
            for k in range(4):
                hb(x + 0.14, y + fd + 0.20 + 0.075 * k, 0.075 - 0.025 * k,
                   0.26, 0.075, 0.025, "wood_dark", mat="plank_dark",
                   erode=0.8, vox=0.04, sort_min=True)
            hb(x + 0.06, y + fd - 0.01, 0.32, 0.44, 0.20, 0.06, "wood_dark",
               shape="gable", mat="wood_dark", erode=0.75, vox=0.08)
            chimney(hb, x + fw * 0.7, y + fd * 0.5, 0.07, 0.86, vent=hid)
            stove(hb, x + 0.1, y + 0.1, 0.125)
        elif i == 2:  # изба с навесом-дровенником
            fw, fd = 0.95, 0.72
            hb(x + 0.02, y + 0.02, 0, fw - 0.04, fd - 0.04, 0.07, "wood_dark",
               mat="wood_dark", erode=0.6, vox=0.1, sort_min=True)
            storey(hb, x, y, 0.07, fw, fd, 0.34, "wood_dark", "wood_dark",
                   0.9, f="wdo", b="ow", l="ow", r="w", th=0.1)
            hb(x - 0.06, y - 0.06, 0.41, fw + 0.12, fd + 0.12, 0.30,
               "wood_dark", shape="gable", mat="wood_dark", erode=0.75,
               vox=0.12, ends="timber")
            storey(hb, x + fw + 0.06, y + 0.1, 0.07, 0.4, 0.4, 0.26,
                   "wood_light", "wood_light", 1.0, f="", b="w", l="",
                   r="w", th=0.07)
            hb(x + fw + 0.02, y + 0.06, 0.33, 0.5, 0.5, 0.2, "wood_dark",
               shape="gable", mat="wood_dark", erode=0.75, vox=0.1)
            for k in range(3):  # поленница под навесом
                hb(x + fw + 0.14 + 0.10 * k, y + 0.20, 0.07, 0.07, 0.30,
                   0.07, "wood_dark", shape="cylinder", mat="wood_dark",
                   erode=0.9, vox=0.04)
            chimney(hb, x + fw * 0.25, y + fd * 0.5, 0.07, 0.80, vent=hid)
            stove(hb, x + 0.1, y + 0.1, 0.075)
        elif i == 3:  # ИЗБА L-ОБРАЗНАЯ (переделана: два крыла углом)
            fw, fd = 1.05, 0.72
            hb(x + 0.02, y + 0.02, 0, fw - 0.04, fd - 0.04, 0.07, "wood_dark",
               mat="wood_dark", erode=0.6, vox=0.1, sort_min=True)
            storey(hb, x, y, 0.07, fw, fd, 0.34, "wood_dark", "wood_dark",
                   0.9, f="wdw", b="w", l="o", r="w", th=0.1)
            hb(x - 0.06, y - 0.06, 0.41, fw + 0.12, fd + 0.12, 0.34,
               "wood_dark", shape="gable", mat="wood_dark", erode=0.75,
               vox=0.12, ends="timber")
            # заднее крыло из правого торца (образует L)
            X2, Y2 = x + fw - 0.34, y - 0.52
            w2, d2 = 0.62, 0.58
            hb(X2 + 0.02, Y2 + 0.02, 0, w2 - 0.04, d2 - 0.04, 0.07,
               "wood_dark", mat="wood_dark", erode=0.6, vox=0.1,
               sort_min=True)
            storey(hb, X2, Y2, 0.07, w2, d2, 0.30, "wood_dark", "wood_dark",
                   0.9, f="", b="ow", l="w", r="o", th=0.1)
            hb(X2 - 0.06, Y2 - 0.06, 0.37, w2 + 0.12, d2 + 0.12, 0.28,
               "wood_dark", shape="gable", mat="wood_dark", erode=0.75,
               vox=0.12, ends="timber")
            chimney(hb, x + 0.30, y + 0.36, 0.07, 0.86, vent=hid)
            stove(hb, x + 0.12, y + 0.1, 0.075)
        else:  # ИЗБА С ЧАСТОКОЛОМ: крупный сруб в укреплённом дворе
            fw, fd = 1.15, 0.90
            hb(x + 0.02, y + 0.02, 0, fw - 0.04, fd - 0.04, 0.07, "wood_dark",
               mat="wood_dark", erode=0.6, vox=0.1, sort_min=True)
            storey(hb, x, y, 0.07, fw, fd, 0.36, "wood_dark", "wood_dark",
                   0.9, f="dwoo", b="wo", l="ow", r="ow", th=0.1)
            hb(x - 0.07, y - 0.07, 0.43, fw + 0.14, fd + 0.14, 0.34,
               "wood_dark", shape="gable", mat="wood_dark", erode=0.75,
               vox=0.12, ends="timber")
            # крыльцо с лесенкой
            hb(x + fw / 2 - 0.16, y + fd + 0.02, 0.07, 0.32, 0.18, 0.035,
               "wood_dark", mat="plank_dark", erode=1.1, vox=0.05,
               sort_min=True)
            for k in range(3):
                hb(x + fw / 2 - 0.14, y + fd + 0.20 + 0.075 * k,
                   0.07 - 0.024 * (k + 1), 0.28, 0.08, 0.03, "wood_dark",
                   mat="plank_dark", erode=1.1, vox=0.05, sort_min=True)
            # частокол по трём сторонам двора (двойной ряд в углах)
            for k in range(13):  # фронтальный ряд
                if k in (6,):
                    continue  # ворота
                hb(x - 0.42 + 0.16 * k, y + fd + 0.42, 0, 0.055, 0.055,
                   0.28 - 0.02 * (k % 2), "wood_dark", mat="wood_dark",
                   erode=0.9, vox=0.04)
            for k in range(11):  # левый ряд
                hb(x - 0.42, y - 0.30 + 0.16 * k, 0, 0.055, 0.055,
                   0.26 - 0.02 * (k % 2), "wood_dark", mat="wood_dark",
                   erode=0.9, vox=0.04)
            for k in range(11):  # правый ряд
                hb(x + fw + 0.42 - 0.055, y - 0.30 + 0.16 * k, 0, 0.055,
                   0.055, 0.26 - 0.02 * (k % 2), "wood_dark",
                   mat="wood_dark", erode=0.9, vox=0.04)
            # ворота: две створки + перемычка
            hb(x - 0.42 + 0.16 * 5, y + fd + 0.405, 0.19, 0.17, 0.05, 0.04,
               "wood_dark", mat="wood_dark", erode=0.9, vox=0.04)
            hb(x - 0.50 + 0.16 * 6, y + fd + 0.40, 0, 0.05, 0.05, 0.22,
               "wood_dark", mat="wood_dark", erode=0.9, vox=0.04)
            # бойницы в переднем ряду частокола
            hb(x - 0.42 + 0.16 * 2, y + fd + 0.415, 0.13, 0.06, 0.06, 0.04,
               "charcoal", mat="wood_dark", erode=0.9, vox=0.03,
               sort_min=True)
            hb(x - 0.42 + 0.16 * 10, y + fd + 0.415, 0.13, 0.06, 0.06, 0.04,
               "charcoal", mat="wood_dark", erode=0.9, vox=0.03,
               sort_min=True)
            chimney(hb, x + fw * 0.6, y + fd * 0.5, 0.07, 0.88, vent=hid)
            stove(hb, x + 0.12, y + 0.12, 0.075)
            bed(hb, x + 0.75, y + 0.2, 0.10)

    # ============ E4 ЗАМКИ (ids 23-30): все разные ============
    for i in range(8):
        x, y = spot(3, i)
        hid = nid()
        hb = hbx_(hid, _gz(x, y))
        if i == 0:  # ДОНЖОН С АРКОЙ (крупный): башня, тёмный проезд, зубцы
            _hb0 = hb
            SS = 1.35
            def hb(x, y, z, w, d, h, color, shape="box", mat="concrete",
                   **kw):
                cx_, cy_ = x + w / 2, y + d / 2
                w2, d2, h2 = w * SS, d * SS, h * SS
                _hb0(cx_ - w2 / 2, cy_ - d2 / 2, z * SS, w2, d2, h2, color,
                     shape=shape, mat=mat, **kw)
            fw = fd = 0.95
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            z0 = 0.07
            for fl in range(3):
                storey(hb, x, y, z0, fw, fd, 0.34, "gray", "stone", 0.62,
                       f=("w" if fl == 0 else "o"), b="o" if fl else "w",
                       l="o" if fl else "w", r="w", th=0.11)
                z0 += 0.34
            # арочный проезд: два пилона + перемычка + тёмный провал
            hb(x + 0.28, y + fd - 0.02, 0.07, 0.12, 0.12, 0.26, "gray",
               mat="stone", erode=0.55, vox=0.06)
            hb(x + 0.56, y + fd - 0.02, 0.07, 0.12, 0.12, 0.26, "gray",
               mat="stone", erode=0.55, vox=0.06)
            hb(x + 0.40, y + fd - 0.005, 0.07, 0.16, 0.05, 0.22, "charcoal",
               mat="stone", erode=0.55, vox=0.04, sort_min=True)
            hb(x + 0.28, y + fd - 0.02, 0.33, 0.40, 0.12, 0.09, "gray",
               mat="stone", erode=0.55, vox=0.06)
            for k in range(6):  # зубцы по периметру
                ang = 6.283 * k / 6
                hb(x + fw / 2 + math.cos(ang) * fw / 2 - 0.05,
                   y + fd / 2 + math.sin(ang) * fd / 2 - 0.05, z0, 0.10,
                   0.10, 0.07, "gray", mat="stone", erode=0.55, vox=0.05)
            hb(x + 0.06, y + 0.06, z0, fw - 0.12, fd - 0.12, 0.30, "brick",
               shape="pyramid", mat="brick", erode=0.5, vox=0.14)
            bed(hb, x + 0.15, y + 0.15, 0.41)
        elif i == 1:  # ЗАМОК-ДВОР: П-стена + круглая башня + домик внутри
            fnd(hb, x - 0.04, y - 0.04, 1.7, 1.2)
            # стены-куртины П-образом
            hb(x, y, 0.07, 0.12, 1.1, 0.34, "gray", mat="stone", erode=0.62,
               vox=0.1)
            hb(x, y, 0.07, 1.55, 0.12, 0.34, "gray", mat="stone", erode=0.62,
               vox=0.1)
            hb(x + 1.55, y, 0.07, 0.12, 1.1, 0.34, "gray", mat="stone",
               erode=0.62, vox=0.1)
            for cx_, cy_ in ((x + 1.49, y + 1.04), (x - 0.02, y + 1.04)):
                hb(cx_, cy_, 0.07, 0.20, 0.20, 0.48, "gray", shape="rock",
                   mat="stone", erode=0.55, vox=0.08)
            # круглая угловая башня с конусом
            hb(x + 1.45, y - 0.12, 0.07, 0.42, 0.42, 0.78, "gray",
               shape="cylinder", mat="stone", erode=0.62, vox=0.12,
               detail=dict(n=(1, 0, 0), kind="window", frame=False,
                           rect=(0.3, 0.7, 0.55, 0.75)))
            hb(x + 1.40, y - 0.17, 0.85, 0.52, 0.52, 0.26, "brick",
               shape="pyramid", mat="brick", erode=0.5, vox=0.14)
            # домик внутри двора
            storey(hb, x + 0.35, y + 0.35, 0.07, 0.7, 0.5, 0.26, "wattle",
                   "wattle", 1.3, f="dw", b="w", l="w", r="o", th=0.09)
            hb(x + 0.30, y + 0.30, 0.33, 0.8, 0.6, 0.24, "straw",
               shape="gable", mat="straw", erode=2.2, vox=0.10,
               ends="timber")
        elif i == 2:  # ЧАСОВНЯ: высокий щипец, роза-окно, колокольчик
            fw, fd = 0.8, 1.0
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            storey(hb, x, y, 0.07, fw, fd, 0.46, "gray", "stone", 0.62,
                   f="d", b="o", l="o", r="o", th=0.10)
            hb(x - 0.06, y - 0.06, 0.53, fw + 0.12, fd + 0.12, 0.52,
               "brick", shape="gable", mat="brick", erode=0.5, vox=0.14,
               ends="timber")
            # роза: маленькое круглое окно на фронтоне
            hb(x + fw / 2 - 0.055, y + fd - 0.04, 0.62, 0.11, 0.035, 0.11,
               "charcoal", shape="rock", mat="stone", erode=0.4, vox=0.04,
               sort_min=True)
            # колокольня-арочка на коньке
            hb(x + fw / 2 - 0.11, y + 0.30, 1.05, 0.05, 0.10, 0.16, "gray",
               mat="stone", erode=0.55, vox=0.04)
            hb(x + fw / 2 + 0.06, y + 0.30, 1.05, 0.05, 0.10, 0.16, "gray",
               mat="stone", erode=0.55, vox=0.04)
            hb(x + fw / 2 - 0.11, y + 0.28, 1.21, 0.22, 0.14, 0.04, "gray",
               mat="stone", erode=0.55, vox=0.04)
            hb(x + fw / 2 - 0.01, y + 0.325, 1.08, 0.07, 0.07, 0.09,
               "concrete_g", shape="cylinder", mat="concrete", erode=0.5,
               vox=0.04)
            stove(hb, x + 0.12, y + 0.7, 0.075)
        elif i == 3:  # КОРОЛЕВСКИЙ ДОНЖОН: флаг-башня 4 яруса
            fw, fd = 1.25, 1.05
            fnd(hb, x - 0.05, y - 0.05, fw + 0.1, fd + 0.1)
            z0 = 0.07
            for fl in range(4):
                storey(hb, x, y, z0, fw, fd, 0.33, "gray", "stone", 0.62,
                       f=("odo" if fl == 0 else "owo"),
                       b="owo" if fl else "w", l="o" if fl else "w",
                       r="o" if fl % 2 else "w", th=0.11)
                z0 += 0.33
            for fx0, fy0 in ((x - 0.07, y - 0.07), (x + fw - 0.05, y - 0.07),
                             (x - 0.07, y + fd - 0.05),
                             (x + fw - 0.05, y + fd - 0.05)):
                hb(fx0, fy0, _gz(fx0 + 0.05, fy0 + 0.05) - 0.02, 0.12, 0.12,
                   z0 - 0.07, "gray", mat="stone", erode=0.55, vox=0.08,
                   zb_abs=True)
            for k in range(8):  # зубцы по периметру
                t_ = k / 7
                if k < 4:
                    hb(x + 0.06 + (fw - 0.16) * (k % 4) / 3, y - 0.02, z0,
                       0.09, 0.08, 0.06, "gray", mat="stone", erode=0.55,
                       vox=0.05)
                else:
                    hb(x + 0.06 + (fw - 0.16) * (k % 4) / 3, y + fd - 0.06,
                       z0, 0.09, 0.08, 0.06, "gray", mat="stone", erode=0.55,
                       vox=0.05)
            hb(x + 0.10, y + 0.10, z0, fw - 0.20, fd - 0.20, 0.26, "brick",
               shape="pyramid", mat="brick", erode=0.5, vox=0.15)
            hb(x + fw / 2 - 0.015, y + fd / 2 - 0.015, z0 + 0.26, 0.03, 0.03,
               0.14, "white", mat="stone", erode=0.4, vox=0.04)
            hb(x + fw / 2 - 0.055, y + fd / 2 - 0.015, z0 + 0.34, 0.11, 0.03,
               0.03, "white", mat="stone", erode=0.4, vox=0.04)
            chimney(hb, x + fw * 0.75, y + fd * 0.25, 0.07, z0 + 0.1,
                    vent=hid)
            bed(hb, x + 0.15, y + 0.15, 0.07)
            table(hb, x + 0.7, y + 0.15, 0.07)
        elif i == 4:  # КРУГЛАЯ СТОРОЖЕВАЯ БАШНЯ (крупная, с бойницами)
            _hb0 = hb
            SS = 1.40
            def hb(x, y, z, w, d, h, color, shape="box", mat="concrete",
                   **kw):
                cx_, cy_ = x + w / 2, y + d / 2
                w2, d2, h2 = w * SS, d * SS, h * SS
                _hb0(cx_ - w2 / 2, cy_ - d2 / 2, z * SS, w2, d2, h2, color,
                     shape=shape, mat=mat, **kw)
            fnd(hb, x - 0.04, y - 0.04, 0.95, 0.95)
            z0 = 0.07
            for fl in range(3):
                hb(x, y, z0, 0.85, 0.85, 0.32, "gray", shape="cylinder",
                   mat="stone", erode=0.62, vox=0.12,
                   detail=dict(n=(0, 1, 0), kind="window", frame=False,
                               rect=(0.35, 0.65, 0.35, 0.60)))
                z0 += 0.32
            for k in range(6):  # зубцы по кругу
                ang = 6.283 * k / 6 + 0.26
                hb(x + 0.425 + math.cos(ang) * 0.40, y + 0.425
                   + math.sin(ang) * 0.40, z0, 0.09, 0.09, 0.06, "gray",
                   mat="stone", erode=0.55, vox=0.05)
            hb(x + 0.07, y + 0.07, z0, 0.71, 0.71, 0.30, "brick",
               shape="pyramid", mat="brick", erode=0.5, vox=0.14)
            hb(x + 0.35, y + 0.80, 0.07, 0.15, 0.04, 0.20, "charcoal",
               mat="stone", erode=0.55, vox=0.04, sort_min=True)  # дверь
        elif i == 5:  # ВОРОТНАЯ БАШНЯ: две башенки + арка-проезд
            fnd(hb, x - 0.04, y - 0.04, 1.15, 0.6)
            for bx_ in (x, x + 0.75):
                z0 = 0.07
                for fl in range(3):
                    storey(hb, bx_, y, z0, 0.4, 0.5, 0.30, "gray", "stone",
                           0.62, f="o", b="w", l="w", r="w", th=0.09)
                    z0 += 0.30
                hb(bx_ - 0.03, y - 0.03, z0, 0.46, 0.56, 0.22, "brick",
                   shape="pyramid", mat="brick", erode=0.5, vox=0.12)
            # перемычка + тёмный проезд под ней
            hb(x + 0.40, y + 0.08, 0.55, 0.35, 0.36, 0.14, "gray",
               mat="stone", erode=0.62, vox=0.10)
            hb(x + 0.47, y + 0.18, 0.07, 0.21, 0.20, 0.48, "charcoal",
               mat="stone", erode=0.55, vox=0.05, sort_min=True)
            hb(x + 0.40, y + 0.10, 0.48, 0.35, 0.32, 0.07, "gray",
               mat="stone", erode=0.62, vox=0.08)
            for k in range(3):
                hb(x + 0.42 + 0.12 * k, y + 0.12, 0.55 + 0.14, 0.08, 0.1,
                   0.05, "gray", mat="stone", erode=0.55, vox=0.04)
        elif i == 6:  # ЗАМОК-УСАДЬБА (крупная): жилое крыло + башенка
            _hb0 = hb
            SS = 1.45
            def hb(x, y, z, w, d, h, color, shape="box", mat="concrete",
                   **kw):
                cx_, cy_ = x + w / 2, y + d / 2
                w2, d2, h2 = w * SS, d * SS, h * SS
                _hb0(cx_ - w2 / 2, cy_ - d2 / 2, z * SS, w2, d2, h2, color,
                     shape=shape, mat=mat, **kw)

            fw, fd = 1.15, 0.8
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            z0 = 0.07
            for fl in range(2):
                storey(hb, x, y, z0, fw, fd, 0.32, "gray", "stone", 0.62,
                       f="odo" if fl == 0 else "owo", b="wow", l="w", r="o",
                       th=0.1)
                z0 += 0.32
            hb(x - 0.06, y - 0.06, z0, fw + 0.12, fd + 0.12, 0.30, "brick",
               shape="gable", mat="brick", erode=0.5, vox=0.14,
               ends="timber")
            hb(x + fw - 0.30, y - 0.22, 0.07, 0.40, 0.40, 0.62, "gray",
               shape="cylinder", mat="stone", erode=0.62, vox=0.12,
               detail=dict(n=(1, 0, 0), kind="window", frame=False,
                           rect=(0.3, 0.7, 0.6, 0.8)))
            hb(x + fw - 0.34, y - 0.26, 0.69, 0.48, 0.48, 0.22, "brick",
               shape="pyramid", mat="brick", erode=0.5, vox=0.12)
            chimney(hb, x + 0.25, y + 0.4, 0.07, z0 + 0.1, vent=hid)
            bed(hb, x + 0.14, y + 0.14, 0.07)
        else:  # БАСТИОН: низкий широкий блок + жаровня-площадка
            fw, fd = 1.5, 1.1
            hb(x - 0.05, y - 0.05, 0, fw + 0.1, fd + 0.1, 0.07, "gray",
               mat="stone", erode=0.5, vox=0.1, sort_min=True)
            hb(x, y, 0.07, fw, fd, 0.30, "gray", mat="stone", erode=0.62,
               vox=0.12, detail=dict(n=(0, 1, 0), kind="door", frame=False,
                                     rect=(0.40, 0.60, 0.0, 0.66)))
            hb(x + 0.18, y + 0.18, 0.37, fw - 0.36, fd - 0.36, 0.16, "gray",
               mat="stone", erode=0.62, vox=0.11, sort_min=True)
            for k in range(6):  # парапет-зубцы по фронту
                hb(x + 0.12 + (fw - 0.34) * k / 5, y + fd - 0.14, 0.37, 0.10,
                   0.10, 0.06, "gray", mat="stone", erode=0.55, vox=0.05)
            # сигнальная жаровня: чаша + угли
            hb(x + fw / 2 - 0.12, y + fd / 2 - 0.12, 0.53, 0.24, 0.24, 0.07,
               "gray", shape="cylinder", mat="stone", erode=0.5, vox=0.06)
            hb(x + fw / 2 - 0.07, y + fd / 2 - 0.07, 0.60, 0.14, 0.14, 0.05,
               "charcoal", shape="rock", mat="stone", erode=0.5, vox=0.05)

    # ============ E5 САМАН (ids 31-40): полная переработка, крыши у всех ====
    def _adobe_roof(hb_, x_, y_, zt_, w_, d_):
        # плоская крыша: плита + парапеты + вылезающие балки-виги
        hb_(x_ + 0.02, y_ + 0.02, zt_, w_ - 0.04, d_ - 0.04, 0.045, "adobe",
            mat="adobe", erode=1.05, vox=0.09, sort_min=True)
        hb_(x_, y_, zt_ + 0.045, w_, 0.05, 0.06, "adobe", mat="adobe",
            erode=1.05, vox=0.06)
        hb_(x_, y_ + d_ - 0.05, zt_ + 0.045, w_, 0.05, 0.06, "adobe",
            mat="adobe", erode=1.05, vox=0.06)
        hb_(x_, y_, zt_ + 0.045, 0.05, d_, 0.06, "adobe", mat="adobe",
            erode=1.05, vox=0.06)
        hb_(x_ + w_ - 0.05, y_, zt_ + 0.045, 0.05, d_, 0.06, "adobe",
            mat="adobe", erode=1.05, vox=0.06)
        for k in range(3):
            hb_(x_ + 0.22 + (w_ - 0.44) * k / 2, y_ - 0.03, zt_ - 0.055,
                0.055, d_ + 0.06, 0.05, "wood_dark", mat="wood_dark",
                erode=0.8, vox=0.04)

    for i in range(10):
        x, y = spot(4, i)
        hid = nid()
        hb = hbx_(hid, _gz(x, y))
        if i == 0:  # саман-куб
            fw = fd = 0.9
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            storey(hb, x, y, 0.07, fw, fd, 0.34, "adobe", "adobe", 1.05,
                   f="odo", b="owo", l="w", r="w", th=0.11)
            _adobe_roof(hb, x, y, 0.41, fw, fd)
            bed(hb, x + 0.15, y + 0.14, 0.10)
        elif i == 1:  # двухъярусный + лесенка на крышу
            fw, fd = 1.0, 0.85
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            storey(hb, x, y, 0.07, fw, fd, 0.34, "adobe", "adobe", 1.05,
                   f="odo", b="owo", l="w", r="w", th=0.11)
            _adobe_roof(hb, x, y, 0.41, fw, fd)
            storey(hb, x + 0.16, y + 0.12, 0.46, fw - 0.32, fd - 0.24, 0.28,
                   "adobe", "adobe", 1.05, f="o", b="w", l="w", r="w",
                   th=0.09)
            _adobe_roof(hb, x + 0.16, y + 0.12, 0.74, fw - 0.32, fd - 0.24)
            for k in range(3):  # ступени сбоку на крышу 2 яруса
                hb(x - 0.14, y + 0.20 + 0.14 * k, 0.07 + 0.09 * k, 0.14,
                   0.16, 0.09, "adobe", mat="adobe", erode=1.05, vox=0.07,
                   sort_min=True)
        elif i == 2:  # L-дом: крыла разной высоты
            fnd(hb, x - 0.04, y - 0.04, 1.5, 0.9)
            storey(hb, x, y, 0.07, 1.0, 0.75, 0.36, "adobe", "adobe", 1.05,
                   f="odow", b="wow", l="w", r="w", th=0.11)
            _adobe_roof(hb, x, y, 0.43, 1.0, 0.75)
            storey(hb, x + 1.0, y + 0.05, 0.07, 0.44, 0.7, 0.28, "adobe",
                   "adobe", 1.05, f="do", b="w", l="", r="w", th=0.09)
            _adobe_roof(hb, x + 1.0, y + 0.05, 0.35, 0.44, 0.7)
            bed(hb, x + 0.15, y + 0.14, 0.10)
        elif i == 3:  # КУПОЛ-УЛЕЙ: круглый дом + соломенный конус
            hb(x, y, 0, 0.85, 0.85, 0.34, "adobe", shape="cylinder",
               mat="adobe", erode=1.05, vox=0.1,
               detail=dict(n=(0, 1, 0), kind="door", frame=False,
                           rect=(0.32, 0.68, 0.0, 0.72)))
            hb(x - 0.05, y - 0.05, 0.34, 0.95, 0.95, 0.36, "straw",
               shape="pyramid", mat="straw", erode=2.2, vox=0.11)
            hb(x + 0.06, y + 0.40, 0.12, 0.10, 0.05, 0.09, "charcoal",
               mat="adobe", erode=1.05, vox=0.04, sort_min=True)  # оконце
        elif i == 4:  # ПУЭБЛО трёхъярусный
            fw, fd = 1.15, 0.9
            fnd(hb, x - 0.05, y - 0.05, fw + 0.1, fd + 0.1)
            storey(hb, x, y, 0.07, fw, fd, 0.32, "adobe", "adobe", 1.05,
                   f="odo", b="wow", l="w", r="w", th=0.11)
            _adobe_roof(hb, x, y, 0.39, fw, fd)
            storey(hb, x + 0.20, y + 0.14, 0.44, fw - 0.40, fd - 0.28, 0.26,
                   "adobe", "adobe", 1.05, f="oo", b="w", l="w", r="w",
                   th=0.09)
            _adobe_roof(hb, x + 0.20, y + 0.14, 0.70, fw - 0.40, fd - 0.28)
            storey(hb, x + 0.40, y + 0.26, 0.75, fw - 0.80, fd - 0.52, 0.22,
                   "adobe", "adobe", 1.05, f="o", b="w", l="", r="", th=0.07)
            _adobe_roof(hb, x + 0.40, y + 0.26, 0.97, fw - 0.80, fd - 0.52)
            for k in range(3):
                hb(x - 0.15, y + 0.28 + 0.16 * k, 0.07 + 0.085 * k, 0.15,
                   0.18, 0.085, "adobe", mat="adobe", erode=1.05, vox=0.07,
                   sort_min=True)
            bed(hb, x + 0.16, y + 0.16, 0.10)
        elif i == 5:  # с АРКОЙ входа: глубокий портал
            fw = fd = 0.95
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            storey(hb, x, y, 0.07, fw, fd, 0.34, "adobe", "adobe", 1.05,
                   f="oww", b="owwo", l="w", r="o", th=0.11)
            _adobe_roof(hb, x, y, 0.41, fw, fd)
            hb(x + 0.28, y + fd - 0.02, 0.07, 0.10, 0.12, 0.24, "adobe",
               mat="adobe", erode=1.05, vox=0.07)
            hb(x + 0.57, y + fd - 0.02, 0.07, 0.10, 0.12, 0.24, "adobe",
               mat="adobe", erode=1.05, vox=0.07)
            hb(x + 0.28, y + fd - 0.02, 0.31, 0.39, 0.12, 0.08, "adobe",
               mat="adobe", erode=1.05, vox=0.07)
            hb(x + 0.38, y + fd - 0.02, 0.07, 0.19, 0.06, 0.24, "charcoal",
               mat="adobe", erode=1.05, vox=0.05, sort_min=True)  # проём
            rug(hb, x + 0.2, y + 0.3, 0.10)
        elif i == 6:  # ДЛИННЫЙ ОБЩИННЫЙ ДОМ: 3 двери под одной крышей
            fw, fd = 2.1, 0.75
            fnd(hb, x - 0.05, y - 0.05, fw + 0.1, fd + 0.1)
            storey(hb, x, y, 0.07, fw, fd, 0.32, "adobe", "adobe", 1.05,
                   f="ododod".replace("dd", "d"), b="wowowow", l="w", r="w",
                   th=0.11)
            _adobe_roof(hb, x, y, 0.39, fw, fd)
            rug(hb, x + 0.3, y + 0.3, 0.10)
            rug(hb, x + 1.2, y + 0.3, 0.10)
        elif i == 7:  # с НАРУЖНОЙ ЛЕСТНИЦЕЙ на крышу
            fw = fd = 0.9
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            storey(hb, x, y, 0.07, fw, fd, 0.34, "adobe", "adobe", 1.05,
                   f="odo", b="wow", l="w", r="w", th=0.11)
            _adobe_roof(hb, x, y, 0.41, fw, fd)
            for k in range(4):  # лестница-марш по фасаду
                hb(x + 0.10 + 0.19 * k, y + fd + 0.02 - (0.0 if k < 2 else 0.0),
                   0.07 + 0.085 * k, 0.20, 0.14, 0.09, "adobe", mat="adobe",
                   erode=1.05, vox=0.07, sort_min=True)
            rug(hb, x + 0.2, y + 0.4, 0.10)
        elif i == 8:  # БАШЕНКА: узкая высокая + бойницы + соломенный колпак
            hb(x, y, 0, 0.7, 0.7, 0.07, "adobe", mat="adobe", erode=1.05,
               vox=0.09, sort_min=True)
            z0 = 0.07
            for fl in range(3):
                storey(hb, x, y, z0, 0.66, 0.66, 0.28, "adobe", "adobe",
                       1.05, f="o" if fl else "", b="w" if fl else "",
                       l="", r="", th=0.09)
                z0 += 0.28
            hb(x - 0.04, y - 0.04, z0, 0.74, 0.74, 0.30, "straw",
               shape="pyramid", mat="straw", erode=2.2, vox=0.11)
            hb(x + 0.24, y + 0.62, 0.07, 0.18, 0.04, 0.20, "charcoal",
               mat="adobe", erode=1.05, vox=0.04, sort_min=True)  # дверь
        else:  # ХРАМ-СТУПЕНИ: три платформы + келья наверху
            for k in range(3):
                sk = 1.5 - 0.4 * k
                off = 0.20 * k
                hb(x + off, y + off, 0.07 + 0.14 * k, sk, sk, 0.14, "adobe",
                   mat="adobe", erode=1.05, vox=0.12, sort_min=(k == 0))
            hb(x + 0.53, y + 0.53, 0.49, 0.44, 0.44, 0.26, "adobe",
               mat="adobe", erode=1.05, vox=0.08,
               detail=dict(n=(0, 1, 0), kind="door", frame=False,
                           rect=(0.25, 0.75, 0.0, 0.7)))
            _adobe_roof(hb, x + 0.53, y + 0.53, 0.75, 0.44, 0.44)
        if i in (0, 1, 4, 6):  # печки у жилых
            stove(hb, x + 0.12, y + 0.12, 0.075)

    # ============ E6 БЕТОН И СТЕКЛО (ids 41-51): полная переработка ========
    # у всех окна с обеих сторон (свет ночью) + чёткие фасады
    for i in range(11):
        x, y = spot(5, i)
        hid = nid()
        hb = hbx_(hid, _gz(x, y))
        CG, PN = "concrete_g", "panel"
        if i == 0:  # куб-студия: панорамы с двух сторон
            fw, fd = 1.15, 0.9
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            slab_floor(hb, x, y, 0.07, fw, fd)
            storey(hb, x, y, 0.07, fw, fd, 0.36, CG, "concrete", 0.62,
                   f="dooo", b="ooo", l="o", r="o", th=0.09)
            hb(x - 0.07, y - 0.07, 0.43, fw + 0.14, fd + 0.14, 0.045, CG,
               mat="concrete", erode=0.62, vox=0.09)
            hb(x + 0.09, y - 0.14, 0.0, 0.20, 0.07, 0.035, CG,
               mat="concrete", erode=0.62, vox=0.06, sort_min=True)
            hb(x + 0.09, y - 0.22, 0.0, 0.24, 0.08, 0.03, CG,
               mat="concrete", erode=0.62, vox=0.06, sort_min=True)
            bed(hb, x + 0.16, y + 0.3, 0.07)
        elif i == 1:  # двухэтажный с балконом
            fw, fd = 1.1, 0.85
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            slab_floor(hb, x, y, 0.07, fw, fd)
            slab_floor(hb, x, y, 0.43, fw, fd)
            storey(hb, x, y, 0.07, fw, fd, 0.36, CG, "concrete", 0.62,
                   f="doo", b="ooo", l="o", r="o", th=0.09)
            storey(hb, x, y, 0.43, fw, fd, 0.33, PN, "panel", 0.62,
                   f="ooo", b="ooo", l="o", r="o", th=0.09)
            # балкон-плита по фронту + ограждение
            hb(x + 0.08, y + fd, 0.43, fw - 0.16, 0.15, 0.03, CG,
               mat="concrete", erode=0.6, vox=0.07)
            for k in range(4):
                hb(x + 0.10 + (fw - 0.28) * k / 3, y + fd + 0.12, 0.46, 0.03,
                   0.03, 0.12, PN, mat="panel", erode=0.6, vox=0.04)
            hb(x + 0.08, y + fd + 0.10, 0.58, fw - 0.16, 0.05, 0.03, PN,
               mat="panel", erode=0.6, vox=0.05)
            hb(x - 0.06, y - 0.06, 0.76, fw + 0.12, fd + 0.12, 0.045, CG,
               mat="concrete", erode=0.62, vox=0.09)
            bed(hb, x + 0.16, y + 0.28, 0.46)
        elif i == 2:  # L-дом модерн
            fnd(hb, x - 0.04, y - 0.04, 1.55, 0.95)
            slab_floor(hb, x, y, 0.07, 1.05, 0.85)
            slab_floor(hb, x, y, 0.42, 1.05, 0.85)
            storey(hb, x, y, 0.07, 1.05, 0.85, 0.35, CG, "concrete", 0.62,
                   f="dooo", b="oooo", l="o", r="w", th=0.09)
            storey(hb, x, y, 0.42, 1.05, 0.85, 0.33, CG, "concrete", 0.62,
                   f="ooo", b="ooo", l="o", r="w", th=0.09)
            storey(hb, x + 1.05, y + 0.10, 0.07, 0.42, 0.70, 0.35, PN,
                   "panel", 0.62, f="do", b="w", l="", r="o", th=0.09)
            hb(x - 0.06, y - 0.06, 0.75, 1.17, 0.97, 0.045, CG,
               mat="concrete", erode=0.62, vox=0.09)
            hb(x + 0.99, y + 0.04, 0.42, 0.54, 0.82, 0.045, CG,
               mat="concrete", erode=0.62, vox=0.09)
            bed(hb, x + 0.15, y + 0.25, 0.07)
        elif i == 3:  # дуплекс нижний: два входа, ленточные окна сзади
            fw, fd = 1.5, 0.8
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            slab_floor(hb, x, y, 0.07, fw, fd)
            storey(hb, x, y, 0.07, fw, fd, 0.34, PN, "panel", 0.62,
                   f="dowod", b="oooooo", l="o", r="o", th=0.09)
            hb(x - 0.06, y - 0.06, 0.41, fw + 0.12, fd + 0.12, 0.05, CG,
               mat="concrete", erode=0.62, vox=0.09)
            bed(hb, x + 0.14, y + 0.2, 0.07)
            bed(hb, x + 1.0, y + 0.2, 0.07)
        elif i == 4:  # дуплекс со студией наверху (витраж торца)
            fw, fd = 1.05, 0.8
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            slab_floor(hb, x, y, 0.07, fw, fd)
            slab_floor(hb, x, y, 0.42, fw, fd)
            storey(hb, x, y, 0.07, fw, fd, 0.35, PN, "panel", 0.62,
                   f="doo", b="ooo", l="w", r="o", th=0.09)
            storey(hb, x, y, 0.42, fw, fd, 0.32, CG, "concrete", 0.62,
                   f="ooo", b="ooo", l="o", r="o", th=0.09)
            # витраж правого торца верхнего яруса
            hb(x + fw - 0.09, y + 0.09, 0.42, 0.09, fd - 0.18, 0.32, PN,
               mat="panel", erode=0.62, vox=0.09,
               detail=dict(n=(1, 0, 0), kind="band", frame=False))
            hb(x - 0.06, y - 0.06, 0.74, fw + 0.12, fd + 0.12, 0.045, CG,
               mat="concrete", erode=0.62, vox=0.09)
            bed(hb, x + 0.15, y + 0.25, 0.07)
        elif i == 5:  # дом с ЭРКЕРОМ (выступ с окнами по 3 сторонам)
            fw, fd = 1.15, 0.85
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            slab_floor(hb, x, y, 0.07, fw, fd)
            slab_floor(hb, x, y, 0.42, fw, fd)
            storey(hb, x, y, 0.07, fw, fd, 0.35, CG, "concrete", 0.62,
                   f="odo", b="ooow", l="o", r="o", th=0.09)
            storey(hb, x, y, 0.42, fw, fd, 0.33, CG, "concrete", 0.62,
                   f="owo", b="ooo", l="o", r="o", th=0.09)
            # эркер-выступ на фасаде
            storey(hb, x + 0.40, y + fd - 0.02, 0.07, 0.34, 0.20, 0.35, PN,
                   "panel", 0.62, f="o", b="", l="o", r="o", th=0.06)
            hb(x + 0.38, y + fd + 0.14, 0.42, 0.38, 0.06, 0.04, CG,
               mat="concrete", erode=0.62, vox=0.06)
            hb(x - 0.06, y - 0.06, 0.75, fw + 0.12, fd + 0.12, 0.045, CG,
               mat="concrete", erode=0.62, vox=0.09)
            bed(hb, x + 0.16, y + 0.22, 0.07)
        elif i == 6:  # ЛОФТ 3 эт.: узкий высокий с сеткой окон
            fw, fd = 0.85, 0.8
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            slab_floor(hb, x, y, 0.07, fw, fd)
            z0 = 0.07
            for fl in range(3):
                slab_floor(hb, x, y, z0 + 0.30, fw, fd)
                storey(hb, x, y, z0, fw, fd, 0.30, PN, "panel", 0.62,
                       f="do" if fl == 0 else "oo", b="oo", l="o", r="o",
                       th=0.08)
                z0 += 0.30
            hb(x - 0.05, y - 0.05, z0, fw + 0.10, fd + 0.10, 0.045, CG,
               mat="concrete", erode=0.62, vox=0.09)
            # мини-терраса крыши с парапетом
            hb(x, y, z0 + 0.045, fw, 0.04, 0.06, PN, mat="panel", erode=0.6,
               vox=0.05)
            hb(x, y + fd - 0.04, z0 + 0.045, fw, 0.04, 0.06, PN, mat="panel",
               erode=0.6, vox=0.05)
            bed(hb, x + 0.12, y + 0.2, 0.07)
        elif i == 7:  # дом с ГАРАЖОМ
            fw, fd = 1.1, 0.85
            fnd(hb, x - 0.04, y - 0.04, fw + 0.7, fd + 0.08)
            slab_floor(hb, x, y, 0.07, fw, fd)
            slab_floor(hb, x, y, 0.42, fw, fd)
            storey(hb, x, y, 0.07, fw, fd, 0.35, CG, "concrete", 0.62,
                   f="doow", b="ooo", l="o", r="w", th=0.09)
            storey(hb, x, y, 0.42, fw, fd, 0.33, PN, "panel", 0.62,
                   f="ooow", b="ooo", l="o", r="w", th=0.09)
            # гараж-крыло с воротами
            storey(hb, x + fw, y + 0.06, 0.07, 0.55, fd - 0.12, 0.30, CG,
                   "concrete", 0.62, f="", b="w", l="", r="o", th=0.08)
            hb(x + fw + 0.10, y + fd - 0.14, 0.07, 0.30, 0.08, 0.24, PN,
               mat="panel", erode=0.62, vox=0.10,
               detail=dict(n=(0, 1, 0), kind="door", frame=False,
                           rect=(0.05, 0.95, 0.0, 0.85)))
            hb(x - 0.06, y - 0.06, 0.75, fw + 0.12, fd + 0.12, 0.045, CG,
               mat="concrete", erode=0.62, vox=0.09)
            hb(x + fw - 0.03, y, 0.37, 0.64, fd - 0.06, 0.045, CG,
               mat="concrete", erode=0.62, vox=0.09)
            bed(hb, x + 0.16, y + 0.24, 0.45)
        elif i == 8:  # ВИЛЛА с ТЕРРАСОЙ (крупная): столбики-навес спереди
            _hb0 = hb
            SS = 1.28
            def hb(x, y, z, w, d, h, color, shape="box", mat="concrete",
                   **kw):
                cx_, cy_ = x + w / 2, y + d / 2
                w2, d2, h2 = w * SS, d * SS, h * SS
                _hb0(cx_ - w2 / 2, cy_ - d2 / 2, z * SS, w2, d2, h2, color,
                     shape=shape, mat=mat, **kw)

            fw, fd = 1.3, 0.9
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            slab_floor(hb, x, y, 0.07, fw, fd)
            storey(hb, x, y, 0.07, fw, fd, 0.36, CG, "concrete", 0.62,
                   f="doooo", b="oooo", l="o", r="o", th=0.09)
            hb(x - 0.06, y - 0.06, 0.43, fw + 0.12, fd + 0.28, 0.045, CG,
               mat="concrete", erode=0.62, vox=0.09)
            for dx in (0.10, fw - 0.16):  # столбики навеса
                hb(x + dx, y + fd + 0.16, 0.07, 0.06, 0.06, 0.36, CG,
                   mat="concrete", erode=0.62, vox=0.06)
            bed(hb, x + 0.2, y + 0.3, 0.07)
            table(hb, x + 0.8, y + 0.3, 0.07)
        elif i == 9:  # ОФИСНЫЙ КУБ 3 эт.: регулярная сетка окон
            fw = fd = 1.1
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            z0 = 0.07
            for fl in range(3):
                slab_floor(hb, x, y, z0, fw, fd)
                storey(hb, x, y, z0, fw, fd, 0.30, PN, "panel", 0.62,
                       f="dooo" if fl == 0 else "oooo", b="oooo", l="ooo",
                       r="ooo", th=0.08)
                z0 += 0.30
            hb(x + 0.3, y - 0.14, 0.07, 0.04, 0.04, 0.23, CG, mat="concrete",
               erode=0.62, vox=0.05)
            hb(x + 0.6, y - 0.14, 0.07, 0.04, 0.04, 0.23, CG, mat="concrete",
               erode=0.62, vox=0.05)
            hb(x + 0.28, y - 0.17, 0.30, 0.38, 0.11, 0.025, CG, mat="concrete",
               erode=0.62, vox=0.08)
            hb(x - 0.06, y - 0.06, z0, fw + 0.12, fd + 0.12, 0.05, CG,
               mat="concrete", erode=0.62, vox=0.09)
        else:  # ПЕНТХАУС-ВИЛЛА: 3 яруса, панорамы, бассейн на крыше
            fw, fd = 1.45, 1.10
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            slab_floor(hb, x, y, 0.07, fw, fd)
            slab_floor(hb, x, y, 0.40, fw, fd)
            storey(hb, x, y, 0.07, fw, fd, 0.33, PN, "panel", 0.62,
                   f="ddow", b="ooo", l="ooo", r="ooo", th=0.08)
            slab_floor(hb, x, y, 0.73, fw, fd)
            storey(hb, x, y, 0.40, fw, fd, 0.33, "white", "panel", 0.7,
                   f="owoo", b="ooo", l="ooo", r="ooo", th=0.08)
            X3 = x + 0.18
            fw3 = fw - 0.36
            slab_floor(hb, X3, y + 0.14, 1.06, fw3, fd - 0.28)
            storey(hb, X3, y + 0.14, 0.73, fw3, fd - 0.28, 0.33, PN,
                   "panel", 0.62, f="ow", b="ow", l="oo", r="oo", th=0.08)
            hb(x - 0.08, y - 0.08, 1.42, fw + 0.16, fd + 0.16, 0.05, CG,
               mat="concrete", erode=0.62, vox=0.09)
            hb(x + 0.22, y + 0.28, 1.44, 0.66, 0.5, 0.03, "cyan",
               mat="panel", erode=0.5, vox=0.05, sort_min=True)  # бассейн
            # балкон 2 яруса: настил + парапет
            hb(x - 0.12, y + fd - 0.34, 0.73, 0.32, 0.6, 0.03, CG,
               mat="concrete", erode=0.62, vox=0.07, sort_min=True)
            hb(x - 0.135, y + fd - 0.355, 0.76, 0.35, 0.63, 0.15, "white",
               mat="panel", erode=0.5, vox=0.05, sort_min=True)
            # крыльцо-настил
            hb(x + 0.32, y + fd + 0.02, 0.07, 0.85, 0.26, 0.03, CG,
               mat="concrete", erode=0.62, vox=0.07, sort_min=True)
            bed(hb, x + 0.25, y + 0.3, 0.10)

    # ============ E7 СЕГОДНЯ (ids 52-66) ============
    for i in range(15):
        x, y = spot(6, i)
        hid = nid()
        hb = hbx_(hid, _gz(x, y))
        CG, PN = "concrete_g", "panel"
        if i <= 1:  # современный коттедж с витражным углом (был)
            fw, fd = 1.15 + 0.1 * i, 0.9
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            hb(x, y + fd - 0.09, 0.07, fw, 0.09, 0.4, PN, mat="panel",
               erode=0.62, vox=0.09,
               detail=dict(n=(0, 1, 0), kind="band", frame=False))
            hb(x + fw - 0.09, y, 0.07, 0.09, fd, 0.4, PN, mat="panel",
               erode=0.62, vox=0.09,
               detail=dict(n=(1, 0, 0), kind="band", frame=False))
            hb(x, y, 0.07, 0.09, fd, 0.4, PN, mat="panel", erode=0.62,
               vox=0.09, detail=dict(n=(-1, 0, 0), kind="band", frame=False))
            hb(x + 0.09, y, 0.07, fw - 0.18, 0.09, 0.4, PN, mat="panel",
               erode=0.62, vox=0.09,
               detail=dict(n=(0, -1, 0), kind="door", frame=False,
                           rect=(0.35, 0.65, 0.0, 0.6)))
            hb(x - 0.08, y - 0.08, 0.47, fw + 0.16, fd + 0.2, 0.05, CG,
               mat="concrete", erode=0.62, vox=0.09)
            bed(hb, x + 0.2, y + 0.3, 0.07)
            table(hb, x + fw - 0.35, y + 0.3, 0.07)
        elif i == 2:  # таунхаус 3 эт. (был)
            fw, fd = 0.95, 0.72
            floors = 3
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            z0 = 0.07
            for fl in range(floors):
                slab_floor(hb, x, y, z0, fw, fd)
                storey(hb, x, y, z0, fw, fd, 0.34, PN, "panel", 0.62,
                       f="dow" if fl == 0 else "owo", b="woo", l="w", r="w")
                z0 += 0.34
            hb(x - 0.06, y - 0.06, z0, fw + 0.12, fd + 0.12, 0.05, CG,
               mat="concrete", erode=0.62, vox=0.09)
        elif i == 3:  # таунхаус 4 эт. (был)
            fw, fd = 0.95, 0.72
            floors = 4
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            z0 = 0.07
            for fl in range(floors):
                slab_floor(hb, x, y, z0, fw, fd)
                storey(hb, x, y, z0, fw, fd, 0.34, PN, "panel", 0.62,
                       f="dow" if fl == 0 else "owo", b="woo", l="w", r="w")
                z0 += 0.34
            hb(x - 0.06, y - 0.06, z0, fw + 0.12, fd + 0.12, 0.05, CG,
               mat="concrete", erode=0.62, vox=0.09)
        elif i == 4:  # панелька 5 эт. с балконами (была)
            fw, fd = 1.6, 0.72
            floors = 5
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            z0 = 0.07
            rest = floors
            fh = 0.34
            while rest > 0:
                take = min(2, rest) if rest > 1 else 1
                hs = fh * take
                hb(x, y + fd - 0.09, z0, fw, 0.09, hs, PN, mat="panel",
                   erode=0.62, vox=0.12,
                   detail=dict(n=(0, 1, 0), kind="panel", frame=False))
                hb(x, y, z0, fw, 0.09, hs, PN, mat="panel", erode=0.62,
                   vox=0.12,
                   detail=dict(n=(0, -1, 0), kind="panel", frame=False))
                hb(x, y + 0.09, z0, 0.09, fd - 0.18, hs, PN, mat="panel",
                   erode=0.62, vox=0.12)
                hb(x + fw - 0.09, y + 0.09, z0, 0.09, fd - 0.18, hs, PN,
                   mat="panel", erode=0.62, vox=0.12)
                if z0 == 0.07:
                    hb(x + 0.3, y - 0.005, z0, 0.16, 0.1, hs, PN,
                       mat="panel", erode=0.62, vox=0.12,
                       detail=dict(n=(0, -1, 0), kind="door", frame=False,
                                   rect=(0.25, 0.75, 0.0, 0.62)))
                z0 += hs
                rest -= take
            hb(x - 0.06, y - 0.06, z0, fw + 0.12, fd + 0.12, 0.05, CG,
               mat="concrete", erode=0.62, vox=0.09)
            for k in range(5):  # балконы на третьем этаже
                bx = x + 0.5 + (fw - 1.0) * k / 4
                hb(bx, y + fd - 0.1, 0.07 + 2 * fh, 0.22, 0.14, 0.025, CG,
                   mat="concrete", erode=0.6, vox=0.08)
                hb(bx, y + fd + 0.015, 0.07 + 2 * fh + 0.025, 0.22, 0.03,
                   0.09, PN, mat="panel", erode=0.6, vox=0.08)
            hb(x + 0.28, y - 0.15, 0.07, 0.04, 0.04, 0.25, CG,
               mat="concrete", erode=0.62, vox=0.05)
            hb(x + 0.46, y - 0.15, 0.07, 0.04, 0.04, 0.25, CG,
               mat="concrete", erode=0.62, vox=0.05)
            hb(x + 0.26, y - 0.18, 0.32, 0.24, 0.14, 0.03, CG,
               mat="concrete", erode=0.62, vox=0.08)
            hb(x + 0.3, y - 0.3, 0.0, 0.16, 0.12, 0.035, "gray",
               mat="stone", erode=0.45, vox=0.05, sort_min=True)
        elif i == 5:  # ПАНЕЛЬКА 9 ЭТ. (новая): узкая высокая секция
            fw, fd = 0.95, 0.72
            fh = 0.30
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            z0 = 0.07
            rest = 9
            while rest > 0:
                take = min(2, rest) if rest > 1 else 1
                hs = fh * take
                hb(x, y + fd - 0.09, z0, fw, 0.09, hs, PN, mat="panel",
                   erode=0.62, vox=0.12,
                   detail=dict(n=(0, 1, 0), kind="panel", frame=False))
                hb(x, y, z0, fw, 0.09, hs, PN, mat="panel", erode=0.62,
                   vox=0.12,
                   detail=dict(n=(0, -1, 0), kind="panel", frame=False))
                hb(x, y + 0.09, z0, 0.09, fd - 0.18, hs, PN, mat="panel",
                   erode=0.62, vox=0.12)
                hb(x + fw - 0.09, y + 0.09, z0, 0.09, fd - 0.18, hs, PN,
                   mat="panel", erode=0.62, vox=0.12)
                if z0 == 0.07:
                    hb(x + 0.3, y - 0.005, z0, 0.16, 0.1, hs, PN,
                       mat="panel", erode=0.62, vox=0.12,
                       detail=dict(n=(0, -1, 0), kind="door", frame=False,
                                   rect=(0.25, 0.75, 0.0, 0.62)))
                z0 += hs
                rest -= take
            hb(x - 0.06, y - 0.06, z0, fw + 0.12, fd + 0.12, 0.05, CG,
               mat="concrete", erode=0.62, vox=0.09)
            for fl in (1, 3, 5, 7):  # балконы через этаж
                bx = x + 0.30
                hb(bx, y + fd - 0.1, 0.07 + fl * fh, 0.24, 0.14, 0.025, CG,
                   mat="concrete", erode=0.6, vox=0.08)
                hb(bx, y + fd + 0.015, 0.07 + fl * fh + 0.025, 0.24, 0.03,
                   0.09, PN, mat="panel", erode=0.6, vox=0.08)
        elif i == 6:  # КИРПИЧНЫЙ ДОМ: кирпич, белые окна, серая черепица
            fw, fd = 1.2, 0.9
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            slab_floor(hb, x, y, 0.07, fw, fd)
            slab_floor(hb, x, y, 0.44, fw, fd)
            storey(hb, x, y, 0.07, fw, fd, 0.37, "brick", "brick", 0.55,
                   f="odoo", b="owo", l="owo", r="owo", th=0.1)
            storey(hb, x, y, 0.44, fw, fd, 0.33, "brick", "brick", 0.55,
                   f="owoo", b="owo", l="owo", r="owo", th=0.1)
            hb(x - 0.07, y - 0.08, 0.77, fw + 0.14, fd + 0.18, 0.38, CG,
               shape="gable", mat="concrete", erode=0.62, vox=0.14,
               ends="timber")
            chimney(hb, x + fw * 0.7, y + fd * 0.45, 0.07, 1.3, vent=hid)
            bed(hb, x + 0.16, y + 0.2, 0.10)
            stove(hb, x + 0.16, y + 0.6, 0.075)
        elif i == 7:  # МАГАЗИН-ВИТРИНА: низкий широкий + вывеска
            fw, fd = 1.9, 0.85
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            slab_floor(hb, x, y, 0.07, fw, fd)
            # сплошная витрина по фронту (светится ночью)
            hb(x + 0.5, y + fd - 0.09, 0.07, fw - 0.6, 0.09, 0.30, PN,
               mat="panel", erode=0.62, vox=0.09,
               detail=dict(n=(0, 1, 0), kind="window", frame=False,
                           rect=(0.03, 0.97, 0.12, 0.90)))
            hb(x, y + fd - 0.09, 0.07, 0.5, 0.09, 0.30, PN, mat="panel",
               erode=0.62, vox=0.09,
               detail=dict(n=(0, 1, 0), kind="door", frame=False,
                           rect=(0.35, 0.65, 0.0, 0.85)))
            hb(x, y, 0.07, 0.09, fd, 0.30, PN, mat="panel", erode=0.62,
               vox=0.09)
            hb(x + fw - 0.09, y, 0.07, 0.09, fd, 0.30, PN, mat="panel",
               erode=0.62, vox=0.09)
            hb(x, y, 0.07, fw, 0.09, 0.30, PN, mat="panel", erode=0.62,
               vox=0.09, detail=dict(n=(0, -1, 0), kind="band", frame=False))
            # вывеска-полоса поверх витрины
            hb(x - 0.04, y + fd - 0.02, 0.37, fw - 0.1, 0.05, 0.10, "brick",
               mat="brick", erode=0.55, vox=0.06)
            hb(x - 0.06, y - 0.06, 0.37, fw + 0.12, fd - 0.05, 0.05, CG,
               mat="concrete", erode=0.62, vox=0.09, sort_min=True)
            table(hb, x + 0.3, y + 0.3, 0.07)
            table(hb, x + 1.2, y + 0.3, 0.07)
        elif i == 8:  # ОСОБНЯК С КОЛОННАМИ: портик и фронтон
            fw, fd = 1.4, 0.95
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            slab_floor(hb, x, y, 0.07, fw, fd)
            slab_floor(hb, x, y, 0.44, fw, fd)
            storey(hb, x, y, 0.07, fw, fd, 0.37, "plaster", "plaster", 0.35,
                   f="wodoow", b="oooo", l="oo", r="oo", th=0.1)
            storey(hb, x, y, 0.44, fw, fd, 0.33, "plaster", "plaster", 0.35,
                   f="ooooo", b="oooo", l="oo", r="oo", th=0.1)
            # колонны портика
            for k in range(4):
                hb(x + 0.22 + k * 0.30, y + fd + 0.02, 0.07, 0.07, 0.07,
                   0.37, "white", mat="plaster", erode=0.35, vox=0.06)
            hb(x + 0.14, y + fd - 0.02, 0.44, 1.12, 0.14, 0.26, "white",
               shape="gable", mat="plaster", erode=0.35, vox=0.08)
            hb(x - 0.07, y - 0.07, 0.77, fw + 0.14, fd + 0.16, 0.34,
               "concrete_g", shape="gable", mat="concrete", erode=0.62,
               vox=0.14, ends="timber")
            chimney(hb, x + fw * 0.8, y + fd * 0.35, 0.07, 1.25, vent=hid)
            bed(hb, x + 0.2, y + 0.2, 0.47)
            rug(hb, x + 0.8, y + 0.5, 0.10)
        elif i == 9:  # ДОМ С МАНСАРДОЙ: слуховые окна на скатах
            fw, fd = 1.15, 0.9
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            slab_floor(hb, x, y, 0.07, fw, fd)
            storey(hb, x, y, 0.07, fw, fd, 0.36, "brick", "brick", 0.55,
                   f="odow", b="owo", l="owo", r="owo", th=0.1)
            hb(x - 0.08, y - 0.09, 0.43, fw + 0.16, fd + 0.20, 0.44,
               "concrete_g", shape="gable", mat="concrete", erode=0.62,
               vox=0.15, ends="timber")
            # мансардные слуховые окна
            for dx in (0.30, 0.75):
                hb(x + dx, y + fd - 0.02, 0.43, 0.24, 0.14, 0.30, "brick",
                   mat="brick", erode=0.55, vox=0.07,
                   detail=dict(n=(0, 1, 0), kind="window", frame=False,
                               rect=(0.15, 0.85, 0.15, 0.80)))
                hb(x + dx - 0.02, y + fd - 0.04, 0.73, 0.28, 0.18, 0.04,
                   "concrete_g", mat="concrete", erode=0.62, vox=0.08)
            chimney(hb, x + fw * 0.25, y + fd * 0.5, 0.07, 1.3, vent=hid)
            bed(hb, x + 0.16, y + 0.2, 0.10)
        elif i == 10:  # НОВОСТРОЙКА-СВЕЧКА: башня с цветными этажами
            fw = fd = 0.85
            fh = 0.30
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            z0 = 0.07
            for fl in range(8):
                col = PN if fl % 3 != 1 else "brick"
                storey(hb, x, y, z0, fw, fd, fh, col,
                       "panel" if col == PN else "brick", 0.62,
                       f="do" if fl == 0 else "oo", b="oo", l="oo", r="oo",
                       th=0.08)
                z0 += fh
            hb(x - 0.05, y - 0.05, z0, fw + 0.10, fd + 0.10, 0.05, CG,
               mat="concrete", erode=0.62, vox=0.09)
        elif i == 11:  # ПАНЕЛЬКА С БАЛКОНАМИ ЧЕРЕЗ ОДИН: 6 эт.
            fw, fd = 1.5, 0.72
            fh = 0.32
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            z0 = 0.07
            rest = 6
            while rest > 0:
                take = min(2, rest) if rest > 1 else 1
                hs = fh * take
                hb(x, y + fd - 0.09, z0, fw, 0.09, hs, PN, mat="panel",
                   erode=0.62, vox=0.12,
                   detail=dict(n=(0, 1, 0), kind="panel", frame=False))
                hb(x, y, z0, fw, 0.09, hs, PN, mat="panel", erode=0.62,
                   vox=0.12,
                   detail=dict(n=(0, -1, 0), kind="panel", frame=False))
                hb(x, y + 0.09, z0, 0.09, fd - 0.18, hs, PN, mat="panel",
                   erode=0.62, vox=0.12)
                hb(x + fw - 0.09, y + 0.09, z0, 0.09, fd - 0.18, hs, PN,
                   mat="panel", erode=0.62, vox=0.12)
                if z0 == 0.07:
                    hb(x + 0.3, y - 0.005, z0, 0.16, 0.1, hs, PN,
                       mat="panel", erode=0.62, vox=0.12,
                       detail=dict(n=(0, -1, 0), kind="door", frame=False,
                                   rect=(0.25, 0.75, 0.0, 0.62)))
                z0 += hs
                rest -= take
            hb(x - 0.06, y - 0.06, z0, fw + 0.12, fd + 0.12, 0.05, CG,
               mat="concrete", erode=0.62, vox=0.09)
            for fl in (1, 3, 5):
                for k in (0, 2, 4):
                    bx = x + 0.3 + (fw - 0.7) * k / 4
                    hb(bx, y + fd - 0.1, 0.07 + fl * fh, 0.22, 0.14, 0.025,
                       CG, mat="concrete", erode=0.6, vox=0.08)
                    hb(bx, y + fd + 0.015, 0.07 + fl * fh + 0.025, 0.22,
                       0.03, 0.09, PN, mat="panel", erode=0.6, vox=0.08)
        elif i == 12:  # ДУПЛЕКС-ТАУН: два дома в одном доме
            fd = 0.72
            fnd(hb, x - 0.04, y - 0.04, 1.95, fd + 0.08)
            slab_floor(hb, x, y, 0.07, 1.9, fd)
            slab_floor(hb, x, y, 0.42, 1.9, fd)
            for wi in range(2):
                wx_ = x + 0.95 * wi
                storey(hb, wx_, y, 0.07, 0.93, fd, 0.35, PN, "panel", 0.62,
                       f="odw", b="woo", l="w", r="w", th=0.09)
                storey(hb, wx_, y, 0.42, 0.93, fd, 0.32, PN, "panel", 0.62,
                       f="wow", b="wow", l="w", r="w", th=0.09)
            hb(x - 0.06, y - 0.06, 0.74, 2.02, fd + 0.14, 0.30, "brick",
               shape="gable", mat="brick", erode=0.55, vox=0.14,
               ends="timber")
            bed(hb, x + 0.14, y + 0.24, 0.07)
            bed(hb, x + 1.1, y + 0.24, 0.07)
        elif i == 13:  # ДАЧНЫЙ ДОМИК: маленький с верандой
            fw, fd = 0.95, 0.75
            fnd(hb, x - 0.04, y - 0.04, fw + 0.08, fd + 0.08)
            slab_floor(hb, x, y, 0.07, fw, fd)
            storey(hb, x, y, 0.07, fw, fd, 0.30, "wood_dark", "wood_dark",
                   0.85, f="dw", b="owo", l="ow", r="w", th=0.09)
            # веранда на столбиках
            for dx in (0.02, 0.46, 0.88):
                hb(x + dx, y + fd + 0.16, 0, 0.045, 0.045, 0.30,
                   "wood_dark", mat="wood_dark", erode=0.85, vox=0.04)
            hb(x - 0.06, y + fd - 0.02, 0.30, fw + 0.12, 0.26, 0.05,
               "wood_dark", mat="plank_dark", erode=0.85, vox=0.07)
            hb(x + 0.01, y + fd + 0.02, 0.07, 0.44, 0.14, 0.03, "plank_dark",
               mat="plank_dark", erode=0.85, vox=0.06, sort_min=True)
            hb(x - 0.07, y - 0.07, 0.37, fw + 0.14, fd + 0.14, 0.32,
               "tile_red", shape="gable", mat="tile", erode=1.0, vox=0.13,
               ends="timber")
            hb(x + fw * 0.7, y + fd * 0.4, 0.37, 0.07, 0.07, 0.55, CG,
               shape="cylinder", mat="concrete", erode=0.5, vox=0.06,
               vent=hid)
            stove(hb, x + 0.1, y + 0.1, 0.075)
        else:  # ОСОБНЯК С ГАРАЖОМ: 2 эт. + крыло-гараж с воротами
            fw, fd = 1.15, 0.9
            fnd(hb, x - 0.04, y - 0.04, fw + 0.75, fd + 0.08)
            slab_floor(hb, x, y, 0.07, fw, fd)
            slab_floor(hb, x, y, 0.43, fw, fd)
            storey(hb, x, y, 0.07, fw, fd, 0.36, "brick", "brick", 0.55,
                   f="odow", b="owo", l="owo", r="w", th=0.1)
            storey(hb, x, y, 0.43, fw, fd, 0.32, "brick", "brick", 0.55,
                   f="owow", b="owo", l="owo", r="w", th=0.1)
            hb(x - 0.06, y - 0.07, 0.75, fw + 0.12, fd + 0.15, 0.32,
               "concrete_g", shape="gable", mat="concrete", erode=0.62,
               vox=0.14, ends="timber")
            storey(hb, x + fw + 0.04, y + 0.12, 0.07, 0.6, fd - 0.24, 0.30,
                   PN, "panel", 0.62, f="", b="w", l="", r="o", th=0.08)
            hb(x + fw + 0.16, y + fd - 0.02, 0.07, 0.30, 0.08, 0.24, CG,
               mat="concrete", erode=0.62, vox=0.10,
               detail=dict(n=(0, 1, 0), kind="door", frame=False,
                           rect=(0.05, 0.95, 0.0, 0.85)))
            hb(x + fw - 0.01, y + 0.06, 0.37, 0.7, fd - 0.12, 0.045, CG,
               mat="concrete", erode=0.62, vox=0.09)
            bed(hb, x + 0.16, y + 0.4, 0.46)
            rug(hb, x + 0.6, y + 0.25, 0.10)

    # печь-купол во дворе глиняного района
    s.append(dict(x=DISTRICTS[4][0] + 5.2, y=DISTRICTS[4][1] + 4.6, z=0,
                  w=0.24, d=0.24, h=0.2, color="adobe", shape="cylinder",
                  mat="adobe", vx=0.0, vy=0.0, vz=0.0, vox=0.06, erode=1.1))

    # ============ НОВЫЕ ЖИЛИЩА КАМЕННОГО ВЕКА (ids 67-68) ============
    for i in range(2):
        x, y = spot(0, 5 + i)
        hid = nid()
        hb = hbx_(hid, _gz(x, y))
        if i == 0:  # ШАЛАШ-ВЫШКА: сруб на столбах, соломенная крыша
            fw, fd = 1.0, 0.85
            for dx, dy in ((0.04, 0.04), (fw - 0.10, 0.04),
                           (0.04, fd - 0.10), (fw - 0.10, fd - 0.10),
                           (fw / 2 - 0.03, 0.04), (fw / 2 - 0.03, fd - 0.10),
                           (0.04, fd / 2 - 0.03), (fw - 0.10, fd / 2 - 0.03)):
                hb(x + dx, y + dy, 0, 0.07, 0.07, 0.42, "wood_dark",
                   mat="wood_dark", erode=0.9, vox=0.05)
            # настил-пол
            hb(x - 0.02, y - 0.02, 0.42, fw + 0.04, fd + 0.04, 0.04,
               "wood_dark", mat="plank_dark", erode=1.1, vox=0.07,
               sort_min=True)
            # стены из брёвен (сруб-короб)
            hb(x, y, 0.46, fw, fd, 0.34, "wood_dark", mat="wood_dark",
               erode=0.75, vox=0.09,
               detail=dict(n=(0, 1, 0), kind="door", frame=False,
                           rect=(0.35, 0.62, 0.0, 0.75)))
            # крыша-щипец солома
            hb(x - 0.09, y - 0.08, 0.80, fw + 0.18, fd + 0.16, 0.34,
               "straw", shape="gable", mat="straw", erode=2.4, vox=0.11,
               ends="timber")
            # лесенка-лесовина к настилу
            for k in range(5):
                hb(x + fw / 2 - 0.11, y + fd + 0.04 + 0.10 * k,
                   0.42 - 0.084 * (k + 1), 0.22, 0.09, 0.03, "wood_light",
                   mat="wood_light", erode=1.2, vox=0.05, sort_min=True)
            # костяные украшения на столбах, шест-флаг
            hb(x + 0.075, y + 0.075, 0.30, 0.09, 0.04, 0.05, "bone",
               mat="bone", erode=1.0, vox=0.03, sort_min=True)
            hb(x + fw - 0.16, y + 0.075, 0.30, 0.09, 0.04, 0.05, "bone",
               mat="bone", erode=1.0, vox=0.03, sort_min=True)
            hb(x + 0.10, y + 0.10, 1.14, 0.04, 0.04, 0.18, "wood_light",
               mat="wood_light", erode=1.2, vox=0.04)
            hb(x + 0.107, y + 0.107, 1.24, 0.11, 0.02, 0.08, "red",
               mat="cloth", erode=1.0, vox=0.03, sort_min=True)
            # ящики с добычей у основания
            hb(x - 0.22, y + fd - 0.1, 0, 0.16, 0.14, 0.12, "wood_light",
               mat="plank_light", erode=1.2, vox=0.05)
            hb(x - 0.10, y + fd + 0.16, 0, 0.13, 0.12, 0.10, "wood_dark",
               mat="plank_dark", erode=1.2, vox=0.05)
        else:  # БАЗА ОХОТНИКОВ: два сруба + частокол-двор + сушильня
            fw, fd = 1.25, 0.80
            # основной сруб
            hb(x + 0.02, y + 0.02, 0, fw - 0.04, fd - 0.04, 0.06, "wood_dark",
               mat="wood_dark", erode=0.6, vox=0.1, sort_min=True)
            storey(hb, x, y, 0.06, fw, fd, 0.34, "wood_dark", "wood_dark",
                   0.9, f="dwo", b="w", l="o", r="o", th=0.1)
            hb(x - 0.06, y - 0.06, 0.40, fw + 0.12, fd + 0.12, 0.30,
               "straw", shape="gable", mat="straw", erode=2.4, vox=0.11,
               ends="timber")
            # малый сруб-кладовая сбоку
            X2, Y2 = x + fw + 0.06, y + 0.10
            w2, d2 = 0.55, 0.55
            storey(hb, X2, Y2, 0.06, w2, d2, 0.28, "wattle", "wattle",
                   1.4, f="", b="d", l="w", r="w", th=0.09)
            hb(X2 - 0.05, Y2 - 0.05, 0.34, w2 + 0.10, d2 + 0.10, 0.24,
               "straw", shape="gable", mat="straw", erode=2.4, vox=0.10,
               ends="timber")
            # частокол-двор: две стены + ворота
            for k in range(12):
                if k in (5, 6):
                    continue
                hb(x - 0.30 + 0.17 * k, y + fd + 0.34, 0, 0.05, 0.05,
                   0.24 - 0.02 * (k % 2), "wood_dark", mat="wood_dark",
                   erode=0.9, vox=0.04)
            for k in range(8):
                hb(x - 0.30, y - 0.24 + 0.17 * k, 0, 0.05, 0.05,
                   0.24 - 0.02 * (k % 2), "wood_dark", mat="wood_dark",
                   erode=0.9, vox=0.04)
            hb(x - 0.30 + 0.17 * 5, y + fd + 0.325, 0.16, 0.20, 0.06, 0.035,
               "wood_dark", mat="wood_dark", erode=0.9, vox=0.04)
            # сушильня-стойка с шкурами внутри двора
            for dx, dy in ((0.10, 0.90), (0.62, 0.90)):
                hb(x + dx, y + dy, 0, 0.04, 0.04, 0.34, "wood_light",
                   mat="wood_light", erode=1.2, vox=0.035, sort_min=True)
            hb(x + 0.06, y + 0.87, 0.30, 0.62, 0.035, 0.03, "wood_light",
               mat="wood_light", erode=1.2, vox=0.03, sort_min=True)
            for k in range(4):
                hb(x + 0.12 + 0.13 * k, y + 0.86, 0.18, 0.11, 0.02,
                   0.16, "plank_light" if k % 2 else "plank_dark",
                   mat="leather", erode=0.9, vox=0.035, sort_min=True)
            # стрелы в кобуре у стойки двора
            hb(x - 0.24, y + fd + 0.24, 0, 0.05, 0.05, 0.16, "wood_dark",
               mat="wood_dark", erode=0.9, vox=0.035, sort_min=True)
            for k in range(3):
                hb(x - 0.235 + 0.012 * k, y + fd + 0.245, 0.14, 0.014,
                   0.014, 0.22, "wood_light", mat="wood_light", erode=1.2,
                   vox=0.025, sort_min=True)
            chimney(hb, x + fw * 0.55, y + fd * 0.45, 0.06, 0.78, vent=hid)
            bed(hb, x + 0.16, y + 0.16, 0.09)

    # ============ НОВЫЕ ОБЪЕКТЫ КАМЕННОГО ВЕКА (ids 69-72) ============
    for i in range(4):
        x, y = spot(0, 7 + i)
        hid = nid()
        hb = hbx_(hid, _gz(x, y))
        if i == 0:  # ОХОТНИЧЬЯ БУДКА: двор-частокол, мишень, стойки
            # частокол-двор: U-образный, ворота спереди
            for k in range(14):
                if k in (6, 7):
                    continue
                hb(x - 0.42 + 0.17 * k, y + 1.06, 0, 0.05, 0.05,
                   0.30 - 0.03 * (k % 2), "wood_dark", mat="wood_dark",
                   erode=0.9, vox=0.04)
            for k in range(9):
                hb(x - 0.42, y - 0.30 + 0.17 * k, 0, 0.05, 0.05,
                   0.30 - 0.03 * (k % 2), "wood_dark", mat="wood_dark",
                   erode=0.9, vox=0.04)
            hb(x + 0.65, y + 1.04, 0.20, 0.22, 0.06, 0.04, "wood_dark",
               mat="wood_dark", erode=0.9, vox=0.04)  # верх ворот
            # тренировочный шест с мишенью
            hb(x + 0.30, y + 0.52, 0, 0.10, 0.10, 0.62, "wood_dark",
               mat="wood_dark", erode=0.9, vox=0.05)
            hb(x + 0.28, y + 0.50, 0.62, 0.14, 0.14, 0.14, "bone",
               shape="cylinder", mat="bone", erode=1.0, vox=0.04,
               sort_min=True)
            hb(x + 0.31, y + 0.53, 0.58, 0.08, 0.08, 0.04, "red",
               mat="cloth", erode=1.0, vox=0.03, sort_min=True)
            # шкуры-мишени на перекладине
            hb(x + 0.78, y + 0.52, 0, 0.06, 0.06, 0.42, "wood_light",
               mat="wood_light", erode=1.2, vox=0.04, sort_min=True)
            hb(x + 1.06, y + 0.52, 0, 0.06, 0.06, 0.42, "wood_light",
               mat="wood_light", erode=1.2, vox=0.04, sort_min=True)
            hb(x + 0.76, y + 0.52, 0.40, 0.34, 0.05, 0.04, "wood_light",
               mat="wood_light", erode=1.2, vox=0.04, sort_min=True)
            hb(x + 0.80, y + 0.50, 0.30, 0.12, 0.02, 0.20, "plank_light",
               mat="leather", erode=0.9, vox=0.035, sort_min=True)
            hb(x + 0.95, y + 0.50, 0.28, 0.12, 0.02, 0.22, "plank_dark",
               mat="leather", erode=0.9, vox=0.035, sort_min=True)
            # стойка с копьями: паз в земле + 5 копий (жердь + наконечник)
            hb(x - 0.24, y + 0.92, -0.02, 0.62, 0.10, 0.05, "dirt",
               mat="stone", erode=0.6, vox=0.04, sort_min=True)
            for k in range(5):
                sx_ = x - 0.18 + 0.13 * k
                hb(sx_, y + 0.94, 0, 0.035, 0.035, 0.55 + 0.03 * (k % 3),
                   "wood_light", mat="wood_light", erode=1.2, vox=0.03,
                   sort_min=True)
                hb(sx_, y + 0.94, 0.55 + 0.03 * (k % 3), 0.05, 0.05,
                   0.12, "bone", mat="bone", erode=1.0, vox=0.025,
                   sort_min=True)
            # навес-склад оружия: три жерди + крыша
            for dx, dy in ((1.06, 0.10), (1.06, 0.46), (1.40, 0.28)):
                hb(x + dx, y + dy, 0, 0.05, 0.05, 0.40, "wood_dark",
                   mat="wood_dark", erode=0.9, vox=0.04, sort_min=True)
            hb(x + 1.02, y + 0.06, 0.36, 0.44, 0.44, 0.16, "straw",
               shape="pyramid", mat="straw", erode=2.4, vox=0.06,
               sort_min=True)
            # топор на подставке из камня
            hb(x + 0.10, y + 0.90, 0, 0.16, 0.14, 0.12, "gray",
               shape="rock", mat="stone", erode=0.5, vox=0.04,
               sort_min=True)
            hb(x + 0.13, y + 0.92, 0.12, 0.035, 0.035, 0.30, "wood_light",
               mat="wood_light", erode=1.2, vox=0.03, sort_min=True)
            hb(x + 0.08, y + 0.915, 0.36, 0.14, 0.05, 0.10, "gray",
               mat="stone", erode=0.5, vox=0.035, sort_min=True)
        elif i == 1:  # СКЛАД КАМНЕЙ: каменный загон-подкова + куча
            for k in range(5):  # задняя стенка
                hb(x - 0.06 + 0.24 * k, y - 0.06, 0, 0.22, 0.10,
                   0.16 - 0.02 * (k % 2), "gray", mat="stone", erode=0.5,
                   vox=0.05)
            for k in range(4):  # левая стенка
                hb(x - 0.06, y + 0.18 + 0.24 * k, 0, 0.10, 0.22,
                   0.16 - 0.02 * (k % 2), "gray", mat="stone", erode=0.5,
                   vox=0.05)
            for k in range(3):  # правая стенка (с проходом)
                hb(x + 0.74, y + 0.18 + 0.24 * k, 0, 0.10, 0.22,
                   0.16 - 0.02 * (k % 2), "gray", mat="stone", erode=0.5,
                   vox=0.05)
            # валун-отмечатель угла
            hb(x + 0.30, y + 0.34, 0, 0.24, 0.24, 0.16, "gray",
               shape="rock", mat="stone", erode=0.5, vox=0.05,
               sort_min=True)
            # базовая куча камней (остальные рисует деревня по факту)
            for dx, dy, dd in ((0.30, 0.24, 0.12), (0.44, 0.30, 0.14),
                               (0.52, 0.42, 0.10), (0.36, 0.52, 0.12),
                               (0.24, 0.40, 0.10)):
                hb(x + dx, y + dy, 0, dd, dd, 0.10 + dd * 0.4, "gray",
                   shape="rock", mat="stone", erode=0.5, vox=0.04,
                   sort_min=True)
        elif i == 2:  # СКЛАД БРЁВЕН: четырёхстолбный стеллаж
            for dx, dy in ((0.04, 0.04), (1.36, 0.04), (0.04, 0.86),
                           (1.36, 0.86)):
                hb(x + dx, y + dy, 0, 0.08, 0.08, 0.46, "wood_dark",
                   mat="wood_dark", erode=0.9, vox=0.05)
            hb(x - 0.02, y + 0.04, 0.46, 1.44, 0.08, 0.06, "wood_dark",
               mat="wood_dark", erode=0.9, vox=0.05, sort_min=True)
            hb(x - 0.02, y + 0.86, 0.46, 1.44, 0.08, 0.06, "wood_dark",
               mat="wood_dark", erode=0.9, vox=0.05, sort_min=True)
            # стартовое бревно на полоке и одно на земле
            hb(x + 0.14, y + 0.38, 0.50, 1.16, 0.14, 0.14, "wood_light",
               mat="wood_light", erode=1.1, vox=0.07, sort_min=True)
            hb(x + 0.16, y + 0.56, 0.02, 1.10, 0.14, 0.14, "wood_light",
               mat="wood_light", erode=1.1, vox=0.07, sort_min=True)
        else:  # ДОМ ДЛЯ ТРОИХ (ур.3): бревна на каменном фундаменте
            # каменный фундамент: углы и передняя грань
            for dx, dy in ((0.0, 0.0), (0.70, 0.0), (0.0, 0.70),
                           (0.70, 0.70)):
                hb(x + dx, y + dy, 0, 0.16, 0.16, 0.10, "gray",
                   mat="stone", erode=0.5, vox=0.05, sort_min=True)
            for k in range(3):
                hb(x + 0.22 + 0.17 * k, y - 0.01, 0, 0.16, 0.09, 0.08,
                   "gray", mat="stone", erode=0.5, vox=0.05, sort_min=True)
            # бревенчатые стойки
            for dx, dy in ((0.02, 0.02), (0.86, 0.02), (0.02, 0.76),
                           (0.86, 0.76)):
                hb(x + dx, y + dy, 0.10, 0.10, 0.10, 0.46, "wood_dark",
                   mat="wood_dark", erode=1.0, vox=0.05)
            # крыша-двускатник из плетёных прутьев
            hb(x, y + 0.02, 0.10, 1.00, 0.82, 0.52, "plank_light",
               shape="gable", mat="wattle", erode=1.4, vox=0.09)
            hb(x - 0.05, y + 0.42, 0.70, 1.10, 0.06, 0.05, "wood_dark",
               mat="wood_dark", erode=1.0, vox=0.035, sort_min=True)
            # шкурный пол + три ложа
            hb(x + 0.10, y + 0.12, 0.10, 0.80, 0.62, 0.04, "leather",
               mat="leather", erode=0.9, vox=0.06, sort_min=True)
            for k in range(3):
                hb(x + 0.16 + 0.22 * k, y + 0.18, 0.14, 0.18, 0.44, 0.07,
                   "plank_dark", mat="leather", erode=0.9, vox=0.05,
                   sort_min=True)
            # дверь: тёмная щель + шкурные створки
            hb(x + 0.40, y + 0.74, 0.10, 0.20, 0.05, 0.30, "charcoal",
               mat="leather", erode=0.9, vox=0.04, sort_min=True)
            hb(x + 0.355, y + 0.745, 0.10, 0.05, 0.05, 0.28, "plank_light",
               mat="leather", erode=0.9, vox=0.04)
            hb(x + 0.60, y + 0.745, 0.10, 0.05, 0.05, 0.28, "plank_light",
               mat="leather", erode=0.9, vox=0.04)
            # каменный очаг у двери + флаг
            hb(x + 0.14, y + 0.66, 0.10, 0.16, 0.12, 0.06, "gray",
               mat="stone", erode=0.5, vox=0.04, sort_min=True)
            hb(x + 0.49, y + 0.42, 0.72, 0.03, 0.03, 0.24, "wood_light",
               mat="wood_light", erode=1.2, vox=0.03, sort_min=True)
            hb(x + 0.495, y + 0.425, 0.92, 0.10, 0.015, 0.07, "red",
               mat="cloth", erode=1.0, vox=0.03, sort_min=True)
    # --- валуны разных форм по острову ---------------------------------------
    def rock(x, y, i):
        _gs = [g for g in (ground_height_at(x + 0.03, y + 0.03),
                           ground_height_at(x + 0.37, y + 0.03),
                           ground_height_at(x + 0.03, y + 0.37),
                           ground_height_at(x + 0.37, y + 0.37))
               if g is not None]
        gz = min(_gs) if _gs else 0.0
        _rc = hash01(i, 11, 76)        # широкий класс: булыжники и глыбы
        _rc = _rc * _rc if hash01(i, 13, 75) > 0.70 else _rc * 0.55
        w = 0.07 + 0.85 * _rc * (0.7 + 0.6 * hash01(i, 3, 77))
        d = 0.06 + 0.75 * _rc * (0.7 + 0.6 * hash01(i, 5, 78))
        h = 0.06 + 0.80 * _rc * (0.7 + 0.6 * hash01(i, 7, 79))
        gz -= 0.02
        s.append(dict(x=x, y=y, z=gz, w=w, d=d, h=h, color="gray",
                      shape="rock", mat="stone", vx=0.0, vy=0.0, vz=0.0,
                      vox=0.06, erode=0.35))

    def _in_town(x):
        return x < 46

    placed = 0
    for i in range(560):
        rx = hash01(i, 991, 501) * (GRID_W - 4) + 1
        ry = hash01(i, 992, 502) * (GRID_D - 4) + 1
        if rx < 46 and ry < 46:
            continue
        if abs(rx - ry) < 3:
            continue
        skip = False
        for dx, dy in DISTRICTS:
            if abs(rx - dx) < 13 and abs(ry - dy) < 13:
                skip = True
                break
        if skip:
            continue
        rock(rx, ry, i)
        placed += 1
        if placed >= 230:
            break
    # деревья по краям острова (не на дороге и не в постройках)
    def tree(x, y, i, z=0.0):
        s.append(dict(x=x, y=y, z=z, w=1.0, d=1.0, h=0.9,
                      color="fir1" if i % 2 == 0 else "fir2",
                      shape="tree", mat="wood_dark", vx=0.0, vy=0.0,
                      vz=0.0, th=0.4, cr=0.35, phase=i * 2.39,
                      shake=0.0, sz=(0.8, 0.9, 1.0)[i % 3],
                      sw_tau=2.0 + 1.6 * hash01(i, 7, 7),
                      lx=0.0, ly=0.0, lvx=0.0, lvy=0.0))

    for i, (tx, ty) in enumerate([(2, 6), (6, 2), (33, 3), (37, 6),
                                  (3, 33), (6, 37), (33, 37), (37, 33),
                                  (20, 3), (3, 20), (36, 20), (20, 36),
                                  (14, 32), (26, 12), (12, 2), (16, 5),
                                  (25, 2), (29, 3), (2, 12), (2, 24),
                                  (8, 20), (13, 18), (15, 28), (19, 30),
                                  (23, 26), (26, 30), (36, 14), (30, 17),
                                  (25, 20), (10, 34), (16, 37), (26, 36),
                                  (37, 26)]):
        tree(tx, ty, i)
    # лесные массивы: плотные пятна по шуму, вне сёл, районов и дороги
    B = _base_h()
    cands = []
    for cy in range(0, GRID_D, 2):
        for cx in range(0, GRID_W, 2):
            if cx < 46 and cy < 46:
                continue
            if abs((cx + 1) - (cy + 1)) < 3:
                continue
            bad = False
            for dx, dy in DISTRICTS:
                if abs(cx - dx) < 14 and abs(cy - dy) < 14:
                    bad = True
                    break
            if bad:
                continue
            m = (_vnoise(cx * 0.06 + 31, cy * 0.06 + 7, 303) * 0.6
                 + _vnoise(cx * 0.15, cy * 0.15, 404) * 0.4)
            if m < 0.48:
                continue
            cands.append((hash01(cx, cy, 505), cx, cy))
    cands.sort()
    for _, cx, cy in cands[:1600]:
        ix = cx + int(hash01(cx, cy, 501) * 2)
        iy = cy + int(hash01(cx, cy, 502) * 2)
        if abs(ix - iy) < 2:
            continue
        gz = (B[iy][ix] + B[iy][ix + 1] + B[iy + 1][ix]
              + B[iy + 1][ix + 1]) * 0.25
        tree(ix, iy, len(s), round(gz / 0.15) * 0.15)
    if not keep_buildings:
        s = [o for o in s if o.get("house") is None]
    for o in s:
        if o.get("vent"):
            VENTS[o["vent"]] = o
    # стартовая усадка: блоки, зародившиеся над опорой, прижать сразу —
    # в кадре незапущенной игры ничего не повисает в воздухе
    _solids0 = [o for o in s if o.get("shape") != "tree"]
    for _ in range(3):
        for o in _solids0:
            if o.get("burn"):
                continue
            _sup0 = _world_queries.support_height_obj(_solids0, o)
            if o["z"] - _sup0 > 0.055:
                o["z"] = _sup0
            o["park_v"] = G.WORLD_VERSION
    return s


# Циклические ссылки на модули выше по цепочке: импорт в конце файла,
# имена используются только внутри функций.
from game.world import queries as _world_queries  # noqa: E402
