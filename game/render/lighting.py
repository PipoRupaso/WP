# -*- coding: utf-8 -*-
"""Свет и плавная смена суток: пресеты, тона, затенение."""

import math
from game.core import state as G
from game.core.config import (
    PRESETS, TEST_MODE)
from game.core.utils import (
    clamp, hash01)

# ---------------------------------------------------------------------------
# Свет
# ---------------------------------------------------------------------------
GROUND_CACHE = {}
GROUND_BASE = {}
GRAIN_CACHE = {}  # (preset, a, b, r,g,b-idx...) -> цвет зерна


# ---------------------------------------------------------------------------
# Плавное течение суток: DAYT в [0,1) — утро(0) -> день(0.25) -> вечер(0.5)
# -> ночь(0.75) -> утро. Небо/солнце/звёзды меняются непрерывно каждый кадр;
# «запечённый» свет (земля, тени, спрайты) обновляется по DAY_STEPS шагов
# за сутки, чтобы не перестраивать статику каждый кадр.
# ---------------------------------------------------------------------------
DAY_LEN = 240.0    # секунд в одних сутках
DAY_STEPS = 72     # квантование запечённого света за сутки


def _day_step():
    return int(G.DAYT * DAY_STEPS) % DAY_STEPS


def _mixc3(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def apply_daylight():
    """Свет из времени суток: сглаженное плавное межу 4 пресетов."""
    t = G.DAYT * 4.0
    i = int(t) % 4
    f = t - int(t)
    s = f * f * (3 - 2 * f)
    a, b = PRESETS[i], PRESETS[(i + 1) % 4]
    sx = a["sun"][0] + (b["sun"][0] - a["sun"][0]) * s
    sy = a["sun"][1] + (b["sun"][1] - a["sun"][1]) * s
    sz = a["sun"][2] + (b["sun"][2] - a["sun"][2]) * s
    sl = math.sqrt(sx * sx + sy * sy + sz * sz) or 1.0
    G.SUN = (sx / sl, sy / sl, sz / sl)
    _dz = max(0.12, G.SUN[2])
    G.SHADOW_DX = -G.SUN[0] / _dz
    G.SHADOW_DY = -G.SUN[1] / _dz
    sa = a["shadow_alpha"] + (b["shadow_alpha"] - a["shadow_alpha"]) * s
    G.SHADOW_RGBA = (28, 38, 78, int(round(sa)))
    amb = a["amb"] + (b["amb"] - a["amb"]) * s
    dif = a["dif"] + (b["dif"] - a["dif"]) * s
    warm = tuple(a["warm"][k] + (b["warm"][k] - a["warm"][k]) * s
                 for k in range(3))
    cool = tuple(a["cool"][k] + (b["cool"][k] - a["cool"][k]) * s
                 for k in range(3))
    sky = (_mixc3(a["sky"][0], b["sky"][0], s),
           _mixc3(a["sky"][1], b["sky"][1], s))
    fx = a["disc"][1] + (b["disc"][1] - a["disc"][1]) * s
    fy = a["disc"][2] + (b["disc"][2] - a["disc"][2]) * s
    night_w = s if i == 2 else ((1 - s) if i == 3 else 0.0)
    G.LIGHT = dict(name=PRESETS[i]["name"], sun=G.SUN, amb=amb, dif=dif,
                 warm=warm, cool=cool, sky=sky, shadow_alpha=sa,
                 cloud_w=_mixc3(a["cloud_w"], b["cloud_w"], s),
                 cloud_s=_mixc3(a["cloud_s"], b["cloud_s"], s),
                 disc=("sun", fx, fy, _mixc3(a["disc"][3], b["disc"][3], s)),
                 stars=night_w > 0.5, star_a=night_w,
                 smoke=_mixc3(a["smoke"], b["smoke"], s))


def update_daytime(dt):
    """Плавное течение суток: непрерывный свет каждый кадр; True, если
    сменился шаг запечённого света (земля/тени/спрайты пересоберутся)."""
    if G.DAY_PAUSE or TEST_MODE:
        return False
    step0 = _day_step()
    G.DAYT = (G.DAYT + dt / DAY_LEN) % 1.0
    apply_daylight()
    if _day_step() != step0:
        GROUND_CACHE.clear()
        GRAIN_CACHE.clear()
        return True
    return False


def set_preset(i):
    """Прыжок к ключевому моменту суток (T/1-4). Течение продолжается."""
    G.DAYT = (i % len(PRESETS)) / 4.0
    apply_daylight()
    GROUND_CACHE.clear()
    GRAIN_CACHE.clear()
    return int(G.DAYT * DAY_STEPS)


def shade(base, n):
    d = max(0.0, n[0] * G.SUN[0] + n[1] * G.SUN[1] + n[2] * G.SUN[2])
    w, c = G.LIGHT["warm"], G.LIGHT["cool"]
    r = base[0] * (G.LIGHT["amb"] * c[0] + G.LIGHT["dif"] * d * w[0])
    g = base[1] * (G.LIGHT["amb"] * c[1] + G.LIGHT["dif"] * d * w[1])
    b = base[2] * (G.LIGHT["amb"] * c[2] + G.LIGHT["dif"] * d * w[2])
    return (clamp(int(r), 0, 255), clamp(int(g), 0, 255), clamp(int(b), 0, 255))


def tilt_normal(face_n, a, b, c, amount=0.45):
    tx = (hash01(a, b, c) - 0.5) * amount
    ty = (hash01(b, c, a) - 0.5) * amount
    tz = hash01(c, a, b) * 0.12
    nx, ny, nz = face_n[0] + tx, face_n[1] + ty, face_n[2] + tz
    il = 1.0 / math.sqrt(nx * nx + ny * ny + nz * nz)
    return (nx * il, ny * il, nz * il)


def grain_color(preset_idx, base, face_n, a, b):
    """Цвет зерна рельефа с кэшем (нормали наклонены — видно на скользящем свете)."""
    key = (preset_idx, base[0], base[1], base[2],
           round(face_n[0], 3), round(face_n[1], 3), round(face_n[2], 3), a, b)
    c = GRAIN_CACHE.get(key)
    if c is None:
        if len(GRAIN_CACHE) > 4000:
            GRAIN_CACHE.clear()
        c = shade(base, tilt_normal(face_n, a, b, 77, 0.7))
        # лёгкий контраст зерна (спокойный вид как на отдалении)
        avg = (c[0] + c[1] + c[2]) / 3
        lit = shade(base, face_n)
        lavg = (lit[0] + lit[1] + lit[2]) / 3 + 1e-6
        k = clamp(avg / lavg, 0.55, 1.6)
        k = 1.0 + (k - 1.0) * 1.2
        c = tone(lit, k)
        GRAIN_CACHE[key] = c
    return c


def tone(color, f):
    return (clamp(int(color[0] * f), 0, 255),
            clamp(int(color[1] * f), 0, 255),
            clamp(int(color[2] * f), 0, 255))


def update_sun_screen(cam):
    ax, ay = cam.world_to_screen(0, 0, 0)
    bx, by = cam.world_to_screen(G.SUN[0] * 2, G.SUN[1] * 2, 0)
    dx, dy = bx - ax, by - ay
    il = 1.0 / max(1e-6, math.hypot(dx, dy))
    G.SUN_SX, G.SUN_SY = dx * il, dy * il
