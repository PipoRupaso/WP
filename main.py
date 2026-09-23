# -*- coding: utf-8 -*-
"""
Пиксельный изометрический прототип в духе Project Zomboid.
Этап 5: фигуры стоят неподвижно, взрывы выбивают рваные пиксельные сколы.

- Фигуры неподвижны: взрыв выбивает связный рваный скол (форма зависит
  от удара) + осколки-щепки любой формы + крошку; на объекте — плоское
  тёмное устье со светлой кромкой. Сила взрыва: Z/X. Клик по блоку
  бьёт по блоку (3D-выбор точки удара).
- Графика понижена: мир рисуется в 1/3 разрешения и растягивается —
  честный крупный пиксель везде (C: x2/x3/x4); тексели 0.28, чанки 4x4.
- Карта 40x40 (в 4 раза больше), воронки ступенчатые с текстурой земли
  и рваными кусками вокруг.

Управление — как в этапе 3 (ЛКМ взрыв/стройка на B, свет на T/1-4...).
Тест:  python main.py --test
"""

import sys
import os
import math
import random
import datetime

TEST_MODE = "--test" in sys.argv
BENCH_MODE = "--bench" in sys.argv
SIM_MODE = "--sim" in sys.argv
CLOSEUP_MODE = "--closeup" in sys.argv
if SIM_MODE or TEST_MODE or CLOSEUP_MODE:
    os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
import numpy as np

rng = random.Random()

# ---------------------------------------------------------------------------
# Настройки
# ---------------------------------------------------------------------------
WINDOW_W, WINDOW_H = 1280, 720
GRID_W, GRID_D = 160, 160
HOME_ZOOM = 0.45     # стартовый зум: весь остров в кадре

TILE_W = 64
TILE_H = 32
TILE_Z = 32
ISLAND_T = 3.0
MIN_H = -0.70        # воронки стали мельче
GRAVITY = 24.0
VOX = 0.5            # базовый размер вокселя
CHIP_VOX = 0.25      # сетка сколов на фигурах
PIXEL_CAP = 1200     # максимум пикселей-осколков
CRUMB_LIFE = 8.0      # сколько крошка лежит на земле
SHARD_LIFE = 12.0     # сколько лежат крупные осколки

FPS = 60
PIXEL = 3            # понижение графики: мир рисуется в 1/PIXEL (клавиша C)
BLAST_POWER = 1.0    # сила взрыва (клавиши Z/X: 0.3 - 2.5)


def SP(px):
    return max(1, int(round(px / PIXEL)))

GRASS = (88, 150, 74)
GRASS_CHECK = (81, 141, 68)
GRASS_DARK = (62, 108, 52)
GRASS_LIGHT = (114, 176, 94)
DIRT_COLOR = (150, 116, 78)
DIRT_DEEP = (128, 96, 64)
ROCK_DEEP = (104, 94, 100)
STONE_GRAY = (96, 98, 108)

HIGHLIGHT = (255, 255, 255)
PANEL_BG = (12, 14, 20, 170)

BASE_COLORS = {
    "red": (236, 96, 84),
    "blue": (98, 148, 236),
    "yellow": (244, 204, 94),
    "green": (110, 194, 104),
    "purple": (172, 134, 224),
    "orange": (244, 154, 72),
    "cyan": (104, 204, 214),
    "gray": (170, 174, 186),
    "white": (232, 234, 242),
    "pink": (238, 144, 193),
    "wood_dark": (133, 90, 50),
    "wood_light": (214, 176, 128),
    "leaf1": (70, 138, 60),
    "leaf2": (92, 162, 66),
    "fir1": (48, 112, 60),
    "fir2": (60, 130, 70),
    "plaster": (233, 222, 198),
    "tile_red": (172, 84, 58),
    "tile_blue": (93, 139, 209),
    "tile_green": (86, 158, 112),
    "tile_purple": (146, 112, 190),
    "tile_gold": (206, 166, 80),
    "leather": (128, 84, 50),
    "straw": (202, 172, 96),
    "wattle": (172, 141, 94),
    "adobe": (216, 178, 120),
    "brick": (160, 82, 56),
    "panel": (186, 193, 190),
    "concrete_g": (148, 150, 148),
    "charcoal": (62, 58, 56),
    "plank_light": (196, 158, 110),
    "plank_dark": (108, 72, 44),
    "dirt": (150, 116, 78),
    "turf": (96, 158, 70),
    "bone": (228, 220, 198),
}
_BASE_ORDER = list(BASE_COLORS)  # стабильный порядок цветов для сида текстур
STONE_MATS = {"gray"}
MAT_ERODE = {"concrete": 1.0, "wood_dark": 0.6, "wood_light": 1.3,
            "plank_dark": 1.1, "plank_light": 1.4,
            "plaster": 1.1, "tile": 1.35, "cloth": 0.5, "stone": 0.55,
            "straw": 2.4, "wattle": 1.6, "leather": 0.9,
            "adobe": 1.1, "brick": 0.38, "panel": 0.62}
MAT_GRAIN = {"concrete": None, "wood_dark": (0, 0, 1),
             "wood_light": (0, 0, 1), "plank_dark": (1, 0, 0),
             "plank_light": (1, 0, 0), "plaster": None, "tile": None,
             "cloth": None, "stone": None}
WOOD_MATS = {"wood_dark", "wood_light", "plank_dark", "plank_light"}
BURN_MATS = WOOD_MATS | {"straw", "wattle", "leather"}   # загорается
_BURN_RATE = {"straw": 0.16, "wattle": 0.10, "leather": 0.12, "cloth": 0.14}
PLANK_MATS = {"plank_dark", "plank_light"}

PRESETS = [
    dict(name="Утро", sun=(0.82, 0.30, 0.40), amb=0.50, dif=0.62,
         warm=(1.10, 0.98, 0.84), cool=(0.88, 0.93, 1.06),
         sky=((148, 188, 238), (246, 222, 198)), shadow_alpha=130,
         cloud_w=(255, 242, 232), cloud_s=(218, 202, 202),
         disc=("sun", 0.85, 0.20, (255, 238, 205)), stars=False,
         smoke=(225, 215, 210)),
    dict(name="День", sun=(0.45, 0.15, 0.88), amb=0.55, dif=0.52,
         warm=(1.06, 1.00, 0.92), cool=(0.90, 0.94, 1.04),
         sky=((98, 172, 235), (188, 228, 250)), shadow_alpha=100,
         cloud_w=(250, 252, 255), cloud_s=(208, 224, 242),
         disc=("sun", 0.84, 0.11, (255, 253, 240)), stars=False,
         smoke=(210, 212, 218)),
    dict(name="Вечер", sun=(-0.78, 0.34, 0.30), amb=0.48, dif=0.64,
         warm=(1.12, 0.88, 0.66), cool=(0.86, 0.88, 1.08),
         sky=((112, 100, 175), (252, 170, 118)), shadow_alpha=145,
         cloud_w=(255, 214, 190), cloud_s=(198, 150, 170),
         disc=("sun", 0.15, 0.24, (255, 200, 140)), stars=False,
         smoke=(225, 180, 170)),
    dict(name="Ночь", sun=(-0.30, 0.50, 0.62), amb=0.30, dif=0.36,
         warm=(0.85, 0.92, 1.10), cool=(0.70, 0.78, 1.00),
         sky=((18, 30, 66), (58, 82, 128)), shadow_alpha=55,
         cloud_w=(90, 110, 160), cloud_s=(50, 64, 110),
         disc=("moon", 0.20, 0.15, (235, 242, 255)), stars=True,
         smoke=(70, 80, 110)),
]

PX, NX = (1, 0, 0), (-1, 0, 0)
PY, NY = (0, 1, 0), (0, -1, 0)
PZ = (0, 0, 1)
RIGHT_N = [PX, NY, NX, PY]
LEFT_N = [PY, PX, NY, NX]


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------
def hash01(a, b, c=0):
    h = (int(a * 73856093) ^ int(b * 19349663) ^ int(c * 83492791)) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    h = (h ^ (h >> 16)) & 0xFFFFFFFF
    return (h % 10000) / 10000.0


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp_pt(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def quad_pt(q, u, t):
    top = lerp_pt(q[0], q[1], u)
    bot = lerp_pt(q[3], q[2], u)
    return lerp_pt(top, bot, t)


def convex_hull(points):
    pts = sorted(set((round(x, 2), round(y, 2)) for x, y in points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def unrot_vec(a, b, rot):
    if rot == 0:
        return (a, b)
    if rot == 1:
        return (b, -a)
    if rot == 2:
        return (-a, -b)
    return (-b, a)


# ---------------------------------------------------------------------------
# Свет
# ---------------------------------------------------------------------------
LIGHT = {}
SUN = (0.45, 0.15, 0.88)
SHADOW_DX, SHADOW_DY = -0.5, -0.17
SHADOW_RGBA = (28, 38, 78, 100)
SUN_SX, SUN_SY = 1.0, 0.3
GROUND_CACHE = {}
GROUND_BASE = {}
GRAIN_CACHE = {}  # (preset, a, b, r,g,b-idx...) -> цвет зерна


# ---------------------------------------------------------------------------
# Плавное течение суток: DAYT в [0,1) — утро(0) -> день(0.25) -> вечер(0.5)
# -> ночь(0.75) -> утро. Небо/солнце/звёзды меняются непрерывно каждый кадр;
# «запечённый» свет (земля, тени, спрайты) обновляется по DAY_STEPS шагов
# за сутки, чтобы не перестраивать статику каждый кадр.
# ---------------------------------------------------------------------------
DAYT = 0.25        # текущее время суток (старт — день)
DAY_LEN = 240.0    # секунд в одних сутках
DAY_PAUSE = False  # пауза цикла (клавиша 0)
DAY_STEPS = 72     # квантование запечённого света за сутки


def _day_step():
    return int(DAYT * DAY_STEPS) % DAY_STEPS


def _mixc3(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def apply_daylight():
    """Свет из времени суток: сглаженное плавное межу 4 пресетов."""
    global LIGHT, SUN, SHADOW_DX, SHADOW_DY, SHADOW_RGBA
    t = DAYT * 4.0
    i = int(t) % 4
    f = t - int(t)
    s = f * f * (3 - 2 * f)
    a, b = PRESETS[i], PRESETS[(i + 1) % 4]
    sx = a["sun"][0] + (b["sun"][0] - a["sun"][0]) * s
    sy = a["sun"][1] + (b["sun"][1] - a["sun"][1]) * s
    sz = a["sun"][2] + (b["sun"][2] - a["sun"][2]) * s
    sl = math.sqrt(sx * sx + sy * sy + sz * sz) or 1.0
    SUN = (sx / sl, sy / sl, sz / sl)
    _dz = max(0.12, SUN[2])
    SHADOW_DX = -SUN[0] / _dz
    SHADOW_DY = -SUN[1] / _dz
    sa = a["shadow_alpha"] + (b["shadow_alpha"] - a["shadow_alpha"]) * s
    SHADOW_RGBA = (28, 38, 78, int(round(sa)))
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
    LIGHT = dict(name=PRESETS[i]["name"], sun=SUN, amb=amb, dif=dif,
                 warm=warm, cool=cool, sky=sky, shadow_alpha=sa,
                 cloud_w=_mixc3(a["cloud_w"], b["cloud_w"], s),
                 cloud_s=_mixc3(a["cloud_s"], b["cloud_s"], s),
                 disc=("sun", fx, fy, _mixc3(a["disc"][3], b["disc"][3], s)),
                 stars=night_w > 0.5, star_a=night_w,
                 smoke=_mixc3(a["smoke"], b["smoke"], s))


def update_daytime(dt):
    """Плавное течение суток: непрерывный свет каждый кадр; True, если
    сменился шаг запечённого света (земля/тени/спрайты пересоберутся)."""
    global DAYT
    if DAY_PAUSE or TEST_MODE:
        return False
    step0 = _day_step()
    DAYT = (DAYT + dt / DAY_LEN) % 1.0
    apply_daylight()
    if _day_step() != step0:
        GROUND_CACHE.clear()
        GRAIN_CACHE.clear()
        return True
    return False


def set_preset(i):
    """Прыжок к ключевому моменту суток (T/1-4). Течение продолжается."""
    global DAYT
    DAYT = (i % len(PRESETS)) / 4.0
    apply_daylight()
    GROUND_CACHE.clear()
    GRAIN_CACHE.clear()
    return int(DAYT * DAY_STEPS)


def shade(base, n):
    d = max(0.0, n[0] * SUN[0] + n[1] * SUN[1] + n[2] * SUN[2])
    w, c = LIGHT["warm"], LIGHT["cool"]
    r = base[0] * (LIGHT["amb"] * c[0] + LIGHT["dif"] * d * w[0])
    g = base[1] * (LIGHT["amb"] * c[1] + LIGHT["dif"] * d * w[1])
    b = base[2] * (LIGHT["amb"] * c[2] + LIGHT["dif"] * d * w[2])
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
    global SUN_SX, SUN_SY
    ax, ay = cam.world_to_screen(0, 0, 0)
    bx, by = cam.world_to_screen(SUN[0] * 2, SUN[1] * 2, 0)
    dx, dy = bx - ax, by - ay
    il = 1.0 / max(1e-6, math.hypot(dx, dy))
    SUN_SX, SUN_SY = dx * il, dy * il


# ---------------------------------------------------------------------------
# Карты нормалей земли (numpy) — как в этапе 3
# ---------------------------------------------------------------------------
def _value_noise(w, h, cx, cy, seed):
    r = np.random.RandomState(seed)
    g = r.rand(cy + 1, cx + 1)
    xs = np.linspace(0, cx, w)
    ys = np.linspace(0, cy, h)
    x0 = np.floor(xs).astype(np.int32)
    y0 = np.floor(ys).astype(np.int32)
    x1 = np.clip(x0 + 1, 0, cx)
    y1 = np.clip(y0 + 1, 0, cy)
    x0 = np.clip(x0, 0, cx)
    y0 = np.clip(y0, 0, cy)
    fx = (xs - np.floor(xs))
    fy = (ys - np.floor(ys))
    sx = fx * fx * (3 - 2 * fx)
    sy = fy * fy * (3 - 2 * fy)
    g00 = g[y0[:, None], x0[None, :]]
    g10 = g[y0[:, None], x1[None, :]]
    g01 = g[y1[:, None], x0[None, :]]
    g11 = g[y1[:, None], x1[None, :]]
    top = g00 * (1 - sx)[None, :] + g10 * sx[None, :]
    bot = g01 * (1 - sx)[None, :] + g11 * sx[None, :]
    return top * (1 - sy)[:, None] + bot * sy[:, None]


def _fbm(w, h, seed, base_cells=4):
    return (_value_noise(w, h, base_cells, base_cells // 2 + 1, seed) * 0.55
            + _value_noise(w, h, base_cells * 3, base_cells * 2, seed + 101) * 0.30
            + _value_noise(w, h, base_cells * 7, base_cells * 5, seed + 202) * 0.15)


def _height_to_normal(h, strength):
    gy, gx = np.gradient(h)
    nx = -gx * strength
    ny = -gy * strength
    nz = np.ones_like(h)
    il = 1.0 / np.sqrt(nx * nx + ny * ny + 1.0)
    return nx * il, ny * il, il


def _diamond_mask(w, h):
    yy, xx = np.mgrid[0:h, 0:w]
    return ((np.abs(xx - (w - 1) / 2) / (w / 2)
             + np.abs(yy - (h - 1) / 2) / (h / 2)) <= 1.0)


def build_ground_base(mat, var):
    key = (mat, var)
    if key in GROUND_BASE:
        return GROUND_BASE[key]
    w, h = TILE_W, TILE_H
    seed = 1000 + var * 77 + (0 if mat == "grass" else 5000)
    mask = _diamond_mask(w, h)
    grain = np.random.RandomState(seed + 7).rand(h, w)
    if mat == "grass":
        base = np.array(GRASS, dtype=np.float32)
        patch = _fbm(w, h, seed, 4)
        height = (_fbm(w, h, seed + 21, 5) * 0.7 + grain * 0.18
                  + _value_noise(w, h, 24, 12, seed + 33) * 0.15)
        albedo = base[None, None, :] * (0.90 + 0.16 * patch[:, :, None])
        albedo *= (0.95 + 0.07 * grain[:, :, None])
        pits = np.random.RandomState(seed + 9).rand(h, w)
        albedo[pits < 0.025] *= 0.78
        albedo[pits > 0.975] *= 1.12
        nu, nv, nw = _height_to_normal(height, 1.7)
    else:
        base = np.array(DIRT_COLOR, dtype=np.float32)
        patch = _fbm(w, h, seed, 3)
        height = (_fbm(w, h, seed + 21, 4) * 0.75 + grain * 0.15)
        clumps = np.random.RandomState(seed + 11).rand(h, w)
        height -= (clumps < 0.06) * 0.55
        height += (clumps > 0.94) * 0.35
        albedo = base[None, None, :] * (0.88 + 0.20 * patch[:, :, None])
        albedo *= (0.94 + 0.07 * grain[:, :, None])
        albedo[clumps < 0.06] *= 0.72
        albedo[clumps > 0.94] *= 1.18
        nu, nv, nw = _height_to_normal(height, 2.5)
    data = dict(albedo=albedo.astype(np.float32), nu=nu, nv=nv, nw=nw, mask=mask)
    GROUND_BASE[key] = data
    return data


def ground_sprite(mat, var, sw, sh, preset_idx, rot, hlev=2):
    key = (mat, var, sw, sh, preset_idx, rot, hlev)
    hit = GROUND_CACHE.get(key)
    if hit is not None:
        return hit[0]
    if len(GROUND_CACHE) > 140:
        GROUND_CACHE.clear()
    d = build_ground_base(mat, var)
    tx = unrot_vec(0.7071, -0.7071, rot)
    ty = unrot_vec(0.7071, 0.7071, rot)
    sU = tx[0] * SUN[0] + tx[1] * SUN[1]
    sV = ty[0] * SUN[0] + ty[1] * SUN[1]
    sZ = SUN[2]
    dot = np.clip(d["nu"] * sU + d["nv"] * sV + d["nw"] * sZ, 0.0, 1.0)
    w_, c_ = np.array(LIGHT["warm"]), np.array(LIGHT["cool"])
    lit = d["albedo"] * (LIGHT["amb"] * c_ + LIGHT["dif"] * dot[:, :, None] * w_)
    lit = np.clip(lit, 0, 255).astype(np.uint8)
    # крупный пиксель: усреднение блоками 4x4 (маска остаётся чёткой)
    lb = lit.reshape(TILE_H // 4, 4, TILE_W // 4, 4, 3).mean(axis=(1, 3))
    lit = lb.repeat(4, axis=0).repeat(4, axis=1).astype(np.uint8)
    if hlev != 2:
        lit = np.clip(lit * (0.78 + 0.11 * hlev), 0, 255).astype(np.uint8)
    alpha = (d["mask"] * 255).astype(np.uint8)
    rgba = np.dstack([lit, alpha])
    buf = rgba.tobytes()
    surf = pygame.image.frombuffer(buf, (TILE_W, TILE_H), "RGBA")
    if (sw, sh) != (TILE_W, TILE_H):
        surf = pygame.transform.scale(surf, (sw, sh))
    GROUND_CACHE[key] = (surf, buf)
    return surf


def build_stone_maps(size=96):
    s = size
    rows, bh = 4, s // 4
    height = np.full((s, s), 0.25, np.float32)
    tint = np.full((s, s), 0.55, np.float32)
    r = np.random.RandomState(42)
    for row in range(rows):
        y0, y1 = row * bh, (row + 1) * bh
        off = (s // 8) if row % 2 else 0
        for x0 in range(-s // 4, s + s // 4, s // 4):
            xa, xb = max(0, x0 + off + 2), min(s, x0 + off + s // 4 - 2)
            ya, yb = y0 + 2, y1 - 2
            if xa >= xb or ya >= yb:
                continue
            height[ya:yb, xa:xb] = 1.0
            tint[ya:yb, xa:xb] = 0.92 + 0.14 * r.rand()
            for k in range(3):
                f = 0.55 + 0.15 * k
                height[ya + k, xa:xb] = min(1.0, f + 0.3)
                height[yb - 1 - k, xa:xb] = f
                height[ya:yb, xa + k] = np.minimum(height[ya:yb, xa + k], f + 0.25)
                height[ya:yb, xb - 1 - k] = np.minimum(height[ya:yb, xb - 1 - k], f + 0.1)
    nu, nv, nw = _height_to_normal(height, 2.0)
    base = np.array(BASE_COLORS["gray"], np.float32)
    albedo = base[None, None, :] * tint[:, :, None]
    return albedo, nu, nv, nw, height


def build_tile_maps(size=96):
    s = size
    rows, rh = 4, s // 4
    height = np.zeros((s, s), np.float32)
    tint = np.full((s, s), 0.90, np.float32)
    r = np.random.RandomState(7)
    tw = s // 6
    for row in range(rows):
        y0 = row * rh
        yy = np.arange(rh) / rh
        prof = np.sin(yy * math.pi) ** 0.7
        xx = np.arange(s) / tw * math.pi + row * 0.7
        arc = np.abs(np.sin(xx)) ** 0.8
        height[y0:y0 + rh, :] = prof[:, None] * 0.55 + arc[None, :] * 0.45
        tint[y0:y0 + rh, :] *= 0.94 + 0.10 * r.rand(rh, s)
        tint[y0 + rh - 2:y0 + rh, :] *= 0.68  # тень нахлёста
        height[y0 + rh - 2:y0 + rh, :] *= 0.4
    tint *= 0.92 + 0.08 * r.rand(s, s)
    nu, nv, nw = _height_to_normal(height, 2.0)
    base = np.array(BASE_COLORS["tile_blue"], np.float32)
    albedo = base[None, None, :] * tint[:, :, None]
    return albedo, nu, nv, nw, height


def build_wood_maps(size=96):
    s = size
    r = np.random.RandomState(11)
    xx = np.arange(s)
    warp = np.sin(xx * 0.25) * 2.0 + np.sin(xx * 0.09 + 2.0) * 3.0
    height = np.zeros((s, s), np.float32)
    for i in range(s):
        height[:, i] = (0.55 + 0.25 * np.sin(i * 0.55 + warp[i] * 0.25)
                        + 0.10 * np.sin(i * 1.7 + 1.0))
    cy, cx = s * 0.38, s * 0.62  # сучок
    yy, xxg = np.mgrid[0:s, 0:s]
    dd = np.sqrt(((xxg - cx) / 9) ** 2 + ((yy - cy) / 6) ** 2)
    height += np.clip(1.2 - dd, 0, 1) * 0.5
    for k in range(1, 4):  # швы досок
        y0 = k * s // 4
        height[y0 - 1:y0 + 1, :] *= 0.35
    tint = 0.86 + 0.16 * (height - height.min()) / max(1e-6, height.max()
                                                       - height.min())
    for k in range(1, 4):
        tint[k * s // 4 - 1:k * s // 4 + 1, :] *= 0.7
    nu, nv, nw = _height_to_normal(height, 1.6)
    base = np.array(BASE_COLORS["wood_light"], np.float32)
    albedo = base[None, None, :] * tint[:, :, None]
    return albedo, nu, nv, nw, height


def build_plaster_maps(size=96):
    s = size
    r = np.random.RandomState(23)
    height = r.rand(s, s).astype(np.float32) * 0.25
    for _ in range(14):
        cx, cy = r.rand() * s, r.rand() * s
        rad = 6 + r.rand() * 16
        yy, xx = np.mgrid[0:s, 0:s]
        height += (np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / rad ** 2)
                   * (0.3 + r.rand() * 0.5))
    height += r.rand(s, s).astype(np.float32) * 0.25
    nu, nv, nw = _height_to_normal(height, 1.2)
    base = np.array(BASE_COLORS["plaster"], np.float32)
    tint = 0.94 + 0.06 * (height - height.min()) / max(1e-6, height.max()
                                                       - height.min())
    albedo = base[None, None, :] * tint[:, :, None]
    return albedo, nu, nv, nw, height


_NMAP_CACHE = {}
_FACE_TAN = {(1, 0, 0): ((0, 1, 0), (0, 0, 1)),
             (-1, 0, 0): ((0, 1, 0), (0, 0, 1)),
             (0, 1, 0): ((1, 0, 0), (0, 0, 1)),
             (0, -1, 0): ((1, 0, 0), (0, 0, 1)),
             (0, 0, 1): ((1, 0, 0), (0, 1, 0))}


def _nmap_for_mat(mat):
    if mat == "tile":
        return build_tile_maps
    if mat in WOOD_MATS:
        return build_wood_maps
    if mat in ("plaster", "cloth"):
        return build_plaster_maps
    return build_stone_maps


def nshade(base, mat, ix, iy, face_n, strength=0.55):
    """Оттенок: нормаль грани возмущена картой нормалей материала."""
    mk = ("tile" if mat == "tile" else
          ("wood" if mat in WOOD_MATS else
           ("plaster" if mat in ("plaster", "cloth") else "stone")))
    e = _NMAP_CACHE.get(mk)
    if e is None:
        a, nu, nv, nw, h = _nmap_for_mat(mat)()
        e = _NMAP_CACHE[mk] = (nu, nv, nw)
    nu, nv, nw = e
    s = nu.shape[0]
    u = float(nu[iy % s, ix % s])
    v = float(nv[iy % s, ix % s])
    w = float(nw[iy % s, ix % s])
    t, b = _FACE_TAN.get(tuple(face_n), ((1, 0, 0), (0, 1, 0)))
    nx = face_n[0] * w + strength * (t[0] * u + b[0] * v)
    ny = face_n[1] * w + strength * (t[1] * u + b[1] * v)
    nz = face_n[2] * w + strength * (t[2] * u + b[2] * v)
    il = 1.0 / max(1e-6, math.sqrt(nx * nx + ny * ny + nz * nz))
    return shade(base, (nx * il, ny * il, nz * il))


def normal_preview_image(kind):
    if kind == "stone":
        albedo, nu, nv, nw, height = build_stone_maps()
        panel = (192, 192)
    elif kind == "tile":
        albedo, nu, nv, nw, height = build_tile_maps()
        panel = (192, 192)
    elif kind == "wood":
        albedo, nu, nv, nw, height = build_wood_maps()
        panel = (192, 192)
    elif kind == "plaster":
        albedo, nu, nv, nw, height = build_plaster_maps()
        panel = (192, 192)
    else:
        d = build_ground_base(kind, 0)
        albedo, nu, nv, nw = d["albedo"], d["nu"], d["nv"], d["nw"]
        height = None
        panel = (192, 96)
    font = pygame.font.Font(None, 24)

    def to_surf(arr):
        a = np.clip(arr, 0, 255).astype(np.uint8)
        return pygame.image.frombuffer(a.tobytes(), (a.shape[1], a.shape[0]),
                                       "RGB" if a.shape[2] == 3 else "RGBA")

    alb = to_surf(albedo)
    nrm = to_surf((np.dstack([nu, nv, nw]) * 0.5 + 0.5) * 255.0)
    if height is None:
        hgt = to_surf(np.dstack([albedo[:, :, 1]] * 3))
    else:
        hgt = to_surf(np.dstack([(height / height.max() * 255)] * 3))
    pw, ph = panel
    img = pygame.Surface((pw * 3 + 40, ph + 60))
    img.fill((24, 26, 34))
    for i, (s, cap) in enumerate([(alb, "albedo"), (nrm, "normal map"),
                                  (hgt, "height" if kind == "stone" else "green")]):
        img.blit(pygame.transform.scale(s, (pw, ph)), (10 + i * (pw + 10), 34))
        img.blit(font.render(cap, True, (220, 220, 230)), (10 + i * (pw + 10), 8))
    names = {"grass": "trava", "dirt": "zemlya", "stone": "kamen",
             "tile": "cherepitsa", "wood": "doski",
             "plaster": "shtukaturka"}
    img.blit(font.render(names[kind], True, (240, 200, 90)), (10, ph + 38))
    return img


# ---------------------------------------------------------------------------
# Камера
# ---------------------------------------------------------------------------
# off_y зависит только от win_h — константу не пересчитываем на каждый вызов
_OFFY_K = (((GRID_W + GRID_D) * (TILE_H / 2)) / 2
           + ISLAND_T * TILE_Z / 2) / PIXEL
_HW, _HH, _TZ = TILE_W / 2, TILE_H / 2, TILE_Z


class Camera:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.zoom = HOME_ZOOM
        self.rot = 0
        self.win_w = WINDOW_W
        self.win_h = WINDOW_H
        self.shx = 0.0
        self.shy = 0.0

    def update_win_size(self, w, h):
        self.win_w, self.win_h = w, h

    @property
    def off_y(self):
        return self.win_h / 2 - _OFFY_K

    def rotate_point(self, x, y):
        W, D = GRID_W, GRID_D
        if self.rot == 0:
            return x, y
        if self.rot == 1:
            return D - y, x
        if self.rot == 2:
            return W - x, D - y
        return y, W - x

    def unrotate_point(self, xr, yr):
        W, D = GRID_W, GRID_D
        if self.rot == 0:
            return xr, yr
        if self.rot == 1:
            return yr, D - xr
        if self.rot == 2:
            return W - xr, D - yr
        return W - yr, xr

    def rotated_footprint(self, x, y, w, d):
        corners = [(x, y), (x + w, y), (x + w, y + d), (x, y + d)]
        rc = [self.rotate_point(cx, cy) for cx, cy in corners]
        xs = [p[0] for p in rc]
        ys = [p[1] for p in rc]
        rx0, ry0 = min(xs), min(ys)
        return rx0, ry0, max(xs) - rx0, max(ys) - ry0

    def iso_project(self, xr, yr, z=0.0):
        sx = (xr - yr) * (TILE_W / 2)
        sy = (xr + yr) * (TILE_H / 2) - z * TILE_Z
        ze = self.zoom / PIXEL  # мир — в пикселях малого буфера
        px = sx * ze + self.win_w / 2 + self.x + self.shx
        py = sy * ze + self.off_y + self.y + self.shy
        return px, py

    def world_to_screen(self, x, y, z=0.0):
        xr, yr = self.rotate_point(x, y)
        return self.iso_project(xr, yr, z)

    def screen_to_world(self, px, py, z=0.0):
        ze = self.zoom / PIXEL
        sx = (px - self.win_w / 2 - self.x - self.shx) / ze
        sy = (py - self.off_y - self.y - self.shy) / ze + z * TILE_Z
        xr = (sx / (TILE_W / 2) + sy / (TILE_H / 2)) / 2
        yr = (sy / (TILE_H / 2) - sx / (TILE_W / 2)) / 2
        return self.unrotate_point(xr, yr)

    def zoom_at(self, px, py, factor):
        old = self.zoom
        new = clamp(old * factor, 0.25, 1.2)
        if abs(new - old) < 1e-6:
            return
        sx = (px - self.win_w / 2 - self.x) / (old / PIXEL)
        sy = (py - self.off_y - self.y) / (old / PIXEL)
        self.zoom = new
        self.x = px - self.win_w / 2 - sx * (new / PIXEL)
        self.y = py - self.off_y - sy * (new / PIXEL)


# ---------------------------------------------------------------------------
# Быстрая проекция для горячих циклов: один раз на кадр собираем контекст,
# дальше — чистая арифметика без вызовов методов (world_to_screen делает
# 3 вызова + свойство off_y на точку).
# ---------------------------------------------------------------------------
def _proj_ctx(cam):
    return (cam.rot, GRID_W, GRID_D, cam.zoom / PIXEL,
            cam.win_w * 0.5 + cam.x + cam.shx,
            cam.off_y + cam.y + cam.shy)


def _proj_pt(ctx, x, y, z):
    rot, W, D, ze, cx, cy = ctx
    if rot == 0:
        xr, yr = x, y
    elif rot == 1:
        xr, yr = D - y, x
    elif rot == 2:
        xr, yr = W - x, D - y
    else:
        xr, yr = y, W - x
    return ((xr - yr) * _HW * ze + cx,
            (xr + yr) * _HH * ze - z * _TZ * ze + cy)


def _box_bbox(ctx, x, y, z, w, d, h):
    """Экранный AABB бокса по 8 углам. Проектция линейна, поворот — кратно
    90°, поэтому крайние (xr-yr) и (xr+yr) находятся аналитически."""
    rot, W, D, ze, cx, cy = ctx
    if rot == 0:
        mns, mxs = x - (y + d), x + w - y
        mnu, mxu = x + y, x + w + y + d
    elif rot == 1:
        mns, mxs = D - y - d - x - w, D - y - x
        mnu, mxu = D - y - d + x, D - y + x + w
    elif rot == 2:
        mns, mxs = W - x - w - D + y, W - x - D + y + d
        mnu, mxu = W - x - w + D - y - d, W - x + D - y
    else:
        mns, mxs = y - W + x, y + d - W + x + w
        mnu, mxu = y + W - x - w, y + d + W - x
    return (mns * _HW * ze + cx,
            mnu * _HH * ze - (z + h) * _TZ * ze + cy,
            mxs * _HW * ze + cx,
            mxu * _HH * ze - z * _TZ * ze + cy)


_STATIC_BUF = 384     # буфер: фоновая пересборка успевает до края
_STATIC_MAXC = 3072   # запас для панорамирования без пересборки
_STATIC_OFF = (0, 0)  # текущий оффсет блита холста (для _fir_shadowed)
_STATIC_SCALE = 1.0   # preview-масштаб старого холста во время zoom


def _static_canvas_params(cam, w, h):
    """Размер и центр холста статики.

    Вблизи острова холст центрирован на ЦЕНТРЕ ОСТРОВА и покрывает весь
    остров: панорамирование по острову — простым сдвигом блита, без
    перестроя (плавный FPS). Если камера ушла с острова — холст
    центрируется на камере (там пусто, перестрои дешёвые)."""
    ze = cam.zoom / PIXEL
    W, D = GRID_W, GRID_D
    cx0, cy0 = cam.rotate_point(W * 0.5, D * 0.5)
    icx = (cx0 - cy0) * _HW * ze
    icy = (cx0 + cy0) * _HH * ze
    xs, ys = [], []
    for ax, ay in ((0, 0), (W, 0), (W, D), (0, D)):
        rx, ry = cam.rotate_point(ax, ay)
        xs.append((rx - ry) * _HW * ze)
        ys.append((rx + ry) * _HH * ze)
    bw = max(xs) - min(xs)
    bh = max(ys) - min(ys)
    ox = -icx
    oy = _OFFY_K - icy
    bigw = min(w + bw + 2 * _STATIC_BUF, _STATIC_MAXC)
    bigh = min(h + bh + 2 * _STATIC_BUF, _STATIC_MAXC)
    # камера за пределами холста-острова? -> центрируемся на камере
    if (abs(cam.x - ox) > bigw / 2 - w / 2 - 320
            or abs(cam.y - oy) > bigh / 2 - h / 2 - 320):
        # Вне острова центр привязан к крупной сетке. Иначе при
        # панорамировании желаемая геометрия менялась каждый кадр и
        # фоновая сборка не успевала закончиться.
        ox = round(cam.x / 512.0) * 512.0
        oy = round(cam.y / 512.0) * 512.0
        bigw = w + 2 * 512
        bigh = h + 2 * 512
    bigw = max(int(bigw), w + 96)
    bigh = max(int(bigh), h + 96)
    return bigw, bigh, ox, oy


def home_cam(cam, ww=None, hh=None):
    """Дом: сцена (20,20) в центре кадра."""
    cam.zoom = HOME_ZOOM
    if ww is None:
        ww, hh = cam.win_w, cam.win_h
    cam.x = cam.y = 0.0
    px, py = cam.world_to_screen(20.0, 20.0, 0.5)
    cam.x = ww / 2 - px
    cam.y = hh * 0.52 - py


def rotate_camera(cam, d):
    """Q/E: вращается КАМЕРА вокруг центра экрана — мировой пункт под
    центром кадра остаётся на месте, мир не «крутится вокруг карты»."""
    px, py = cam.win_w / 2.0, cam.win_h / 2.0
    wx, wy = cam.screen_to_world(px, py, 0.0)
    gz = 0.0
    for _ in range(4):  # точка на поверхности под центром
        g = ground_height_at(wx, wy)
        if g is None:
            break
        gz = g
        wx, wy = cam.screen_to_world(px, py, g)
    sx0, sy0 = cam.iso_project(*cam.rotate_point(wx, wy), gz)
    cam.rot = (cam.rot + d) % 4
    sx1, sy1 = cam.iso_project(*cam.rotate_point(wx, wy), gz)
    cam.x += sx0 - sx1
    cam.y += sy0 - sy1
    GROUND_CACHE.clear()


# ---------------------------------------------------------------------------
# Поле высот
# ---------------------------------------------------------------------------
GH = [[0.0] * (GRID_W + 1) for _ in range(GRID_D + 1)]
DENTED = set()
_RIMTILES = set()  # вал выброса вокруг воронок
_FARMAP = dict(key=None, colors=None, X=None, Y=None, H=None, buf=None,
               dkey=None, painted=set(), rpainted=set())


def _vnoise(x, y, seed):
    xi, yi = math.floor(x), math.floor(y)
    xf, yf = x - xi, y - yi
    u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)
    a = hash01(xi, yi, seed)
    b = hash01(xi + 1, yi, seed)
    c = hash01(xi, yi + 1, seed)
    d = hash01(xi + 1, yi + 1, seed)
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v


BASE_H = None


def _base_h():
    """Природный рельеф: холмы вдали, ровно у построек и дороги."""
    global BASE_H
    if BASE_H is None:
        H = [[0.0] * (GRID_W + 1) for _ in range(GRID_D + 1)]
        for y in range(GRID_D + 1):
            Hy = H[y]
            for x in range(GRID_W + 1):
                n = (_vnoise(x * 0.045, y * 0.045, 101) * 0.65
                     + _vnoise(x * 0.11, y * 0.11, 202) * 0.35)
                h = (n - 0.42) * 3.4
                fx = clamp((x - 44) / 10.0, 0.0, 1.0)
                fy = clamp((y - 44) / 10.0, 0.0, 1.0)
                f = max(fx, fy)
                f = f * f * (3 - 2 * f)
                e = min(x, y, GRID_W - x, GRID_D - y, 6) / 6.0
                Hy[x] = clamp(round(h * f * e / 0.15) * 0.15, -1.0, 2.2)
        BASE_H = H
    return BASE_H


def _base_plate_h(x, y, fx, fy):
    B = _base_h()
    gx, gy = x + fx, y + fy
    x0 = int(min(gx, GRID_W - 1e-6))
    y0 = int(min(gy, GRID_D - 1e-6))
    u, v = gx - x0, gy - y0
    return (B[y0][x0] * (1 - u) * (1 - v) + B[y0][x0 + 1] * u * (1 - v)
            + B[y0 + 1][x0] * (1 - u) * v + B[y0 + 1][x0 + 1] * u * v)


def reset_ground():
    global GH, DENTED, _RIMTILES
    _base_h()
    GH = [row[:] for row in BASE_H]
    DENTED = set()
    _RIMTILES = set()
    _FARMAP["dkey"] = None


def ground_height_at(x, y):
    if not (0 <= x <= GRID_W and 0 <= y <= GRID_D):
        return None
    x0, y0 = int(min(x, GRID_W - 1e-6)), int(min(y, GRID_D - 1e-6))
    fx, fy = x - x0, y - y0
    return (GH[y0][x0] * (1 - fx) * (1 - fy) + GH[y0][x0 + 1] * fx * (1 - fy)
            + GH[y0 + 1][x0] * (1 - fx) * fy + GH[y0 + 1][x0 + 1] * fx * fy)


def height_normal_at(x, y):
    h00, h10 = GH[y][x], GH[y][x + 1]
    h01, h11 = GH[y + 1][x], GH[y + 1][x + 1]
    dhdx = ((h10 + h11) - (h00 + h01)) * 0.5
    dhdy = ((h01 + h11) - (h00 + h10)) * 0.5
    il = 1.0 / math.sqrt(dhdx * dhdx + dhdy * dhdy + 1.0)
    return (-dhdx * il, -dhdy * il, il)


def recompute_dented():
    global DENTED
    DENTED = set()
    for y in range(GRID_D):
        for x in range(GRID_W):
            hs = (GH[y][x], GH[y][x + 1], GH[y + 1][x], GH[y + 1][x + 1])
            if max(abs(v) for v in hs) > 0.015:
                DENTED.add((x, y))


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
            _sup0 = support_height_obj(_solids0, o)
            if o["z"] - _sup0 > 0.055:
                o["z"] = _sup0
            o["park_v"] = WORLD_VERSION
    return s



# ---------------------------------------------------------------------------
# Библиотека зданий по эпохам + установка в мир (панель по Y)
# ---------------------------------------------------------------------------
EPOCH_NAMES = ["Каменный век", "Раннее дерево", "Рубленые избы",
               "Средневековье", "Саман", "Замки", "Бетон и стекло", "Сегодня"]
CLASS_NAMES = [
    ["Навес с кострищем", "Шалаш из шкур", "Палатка из жердей",
     "Двускатный шалаш", "Мастерская на жердях", "Шалаш-вышка",
     "База охотников", "Охотничья будка", "Склад камней", "Склад брёвен",
     "Шалаш-двойной"],
    ["Круглая хижина", "Длинный дом", "Хижина на сваях", "Хижина вождя",
     "Хижина-галерея"],
    ["Рубленая изба", "Изба с крыльцом", "Изба с дровенником",
     "Изба L-образная", "Изба с частоколом"],
    ["Коттедж C1", "Двухэтажный C2", "Изба-терем C3", "Терем C4",
     "Большой терем C5", "Фахверк-лавка", "Таверна"],
    ["Саман-куб", "Саман 2-ярусный", "Саман L-дом", "Купол-улей",
     "Пуэбло 3-ярусный", "Саман с аркой", "Общинный длинный",
     "Саман с лестницей", "Башенка-саман", "Храм-ступени"],
    ["Донжон с аркой", "Замок-двор", "Часовня", "Королевский донжон",
     "Сторожевая башня", "Воротная башня", "Замок-усадьба", "Бастион"],
    ["Куб-студия", "Двухэтажный с балконом", "L-дом модерн",
     "Дуплекс нижний", "Дуплекс студия", "Дом с эркером", "Лофт 3эт.",
     "Дом с гаражом", "Вилла с террасой", "Офисный куб", "Пентхаус-вилла"],
    ["Коттедж витражный", "Коттедж витражный-2", "Таунхаус 3эт.",
     "Таунхаус 4эт.", "Панелька 5эт.", "Панелька 9эт.", "Кирпичный дом",
     "Магазин-витрина", "Особняк с колоннами", "Дом с мансардой",
     "Свечка-новостройка", "Панелька с балконами", "Дуплекс-таун",
     "Дачный домик", "Особняк с гаражом"],
]
# класс жильцов по замыслу (0 = худший, 4 = лучший); порядок в палитре
HOUSE_ORDER = {
    8: 5, 9: 1, 10: 0, 11: 2, 12: 6, 67: 3, 68: 4,
    69: 7, 70: 8, 71: 9, 72: 10,                          # каменный век
    13: 0, 14: 2, 15: 1, 16: 3, 17: 4,                     # раннее дерево
    18: 0, 19: 1, 20: 2, 21: 3, 22: 4,                     # рубленые избы
    1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6,              # средневековье
    28: 0, 27: 1, 29: 2, 23: 3, 26: 4, 24: 5, 25: 6, 30: 7,  # замки
    42: 0, 44: 1, 45: 2, 43: 3, 46: 4, 47: 5, 50: 6,
    49: 7, 51: 8, 41: 9, 48: 10,                            # бетон и стекло
    66: 0, 63: 1, 56: 2, 57: 3, 62: 4,
    52: 5, 53: 6, 54: 7, 55: 8, 58: 9, 59: 10, 60: 11,
    61: 12, 64: 13, 65: 14,                                 # сегодня
}
# вместимость (чел.) у жилых классов
HOUSE_CAP = {
    10: 1, 9: 2, 11: 2, 67: 4, 68: 5, 72: 3,
    13: 1, 15: 2, 14: 3, 16: 4, 17: 5,
    18: 1, 19: 2, 20: 3, 21: 4, 22: 5,
    1: 1, 2: 3, 3: 4, 4: 5, 5: 6,
    28: 2, 27: 3, 29: 4, 23: 5, 26: 6,
    42: 2, 44: 2, 45: 2, 43: 3, 46: 3, 47: 3, 50: 5,
    49: 6, 51: 8,
    66: 3, 63: 4, 56: 6, 57: 8, 62: 10,
}
LIB_TPL = None
NEXT_HOUSE = [41]  # пул id для устанавливаемых домов


_EPOCH_RANGES = [(1, 7, 3), (8, 12, 0), (13, 17, 1), (18, 22, 2),
                 (23, 30, 5), (31, 40, 4), (41, 51, 6), (52, 66, 7),
                 (67, 72, 0)]
_EPOCH_START = {3: 1, 0: 8, 1: 13, 2: 18, 4: 23, 5: 31, 6: 41, 7: 52}


def _epoch_of_id(h):
    for a_, b_, e_ in _EPOCH_RANGES:
        if a_ <= h <= b_:
            return e_
    return 7


def make_building_library():
    """40 шаблонов: epoch, cls, name, anchor, pieces (относительные коорд.)."""
    global LIB_TPL
    if LIB_TPL is not None:
        return LIB_TPL
    objs = make_test_scene(keep_buildings=True)
    by_house = {}
    for o in objs:
        if o.get("house"):
            by_house.setdefault(o["house"], []).append(o)
    lib = []
    for hid in sorted(by_house):
        ep = _epoch_of_id(hid)
        if ep == 4:  # эпоха самана удалена из каталога
            continue
        pieces = by_house[hid]
        ox = min(p["x"] for p in pieces)
        oy = min(p["y"] for p in pieces)
        oz = min(p["z"] for p in pieces)
        cls = HOUSE_ORDER.get(hid, 90 + hid)
        rel = []
        for p in pieces:
            q = {k: v for k, v in p.items()
                 if k not in ("house", "_chipgrid", "sup", "supt", "park_v",
                              "tmb", "fx_t", "sp_t", "ig", "burn", "dust_t",
                              "chips", "over")}
            q = dict(q)
            q["x"] = round(p["x"] - ox, 4)
            q["y"] = round(p["y"] - oy, 4)
            q["z"] = round(p["z"] - oz, 4)
            q["vx"] = q["vy"] = q["vz"] = 0.0
            rel.append(q)
        if hid in (67, 68):  # дома ур.4/5: моделька чуть больше
            _SC = 1.18
            for q in rel:
                for _kk in ("x", "y", "w", "d"):
                    q[_kk] = round(q[_kk] * _SC, 4)
                for _kk in ("z", "h"):
                    q[_kk] = round(q[_kk] * 1.08, 4)
        _idx = hid - _EPOCH_START[ep]
        nm = (CLASS_NAMES[ep][_idx]
              if _idx < len(CLASS_NAMES[ep]) else "Дом %d" % (hid))
        _cap = HOUSE_CAP.get(hid)
        if _cap:
            nm = "%s \u00b7 %d чел." % (nm, _cap)
        lib.append(dict(epoch=ep, cls=cls, hid=hid, name=nm,
                        anchor=(ox, oy), z0=oz, _raw=(ox, oy, oz),
                        pieces=rel, cap=_cap or 0))
    LIB_TPL = lib
    return lib


def _tpl_layout(tpl, rot):
    """Раскладка кусков шаблона с поворотом rot (90гр шаги), по якорю-мину."""
    raw = []
    for p in tpl["pieces"]:
        x, y, w, d = p["x"], p["y"], p["w"], p["d"]
        pts = [(x, y), (x + w, y), (x + w, y + d), (x, y + d)]
        for _ in range(rot % 4):
            pts = [(b_, -a_) for (a_, b_) in pts]
        xa = min(c[0] for c in pts)
        ya = min(c[1] for c in pts)
        xb = max(c[0] for c in pts)
        yb = max(c[1] for c in pts)
        raw.append([xa, ya, xb - xa, yb - ya, p])
    bx0 = min(r[0] for r in raw)
    by0 = min(r[1] for r in raw)
    return [(r[0] - bx0, r[1] - by0, r[2], r[3], r[4]) for r in raw]


def _tpl_ground_z(layout):
    """Якорь детали к рельефу: минимум по углам объединённого прямоугольника."""
    ux1 = max(r[0] + r[2] for r in layout)
    uy1 = max(r[1] + r[3] for r in layout)
    best = 1e9
    for ux in (0.0, ux1):
        for uy in (0.0, uy1):
            g = ground_height_at(ux, uy)
            if g is not None and g < best:
                best = g
    if best > 1e8:
        best = 0.0
    return math.floor(best / 0.05) * 0.05 - 0.045


def place_building(objects, tpl, X, Y, rot=0):
    """Установить дом из шаблона в точку X,Y (метка = левый нижний угол)."""
    layout = _tpl_layout(tpl, rot)
    if not layout:
        return None
    zb = _tpl_ground_z(layout)
    hid = NEXT_HOUSE[0]
    NEXT_HOUSE[0] += 1
    for xa, ya, w, d, p in layout:
        q = dict(p)
        q["x"], q["y"] = xa + X, ya + Y
        q["w"], q["d"] = w, d
        q["z"] = p["z"] + zb
        q["house"] = hid
        if rot % 4 and q.get("detail") and q["detail"].get("n"):
            nx, ny, _nz = q["detail"]["n"]
            for _ in range(rot % 4):
                nx, ny = ny, -nx
            q["detail"] = dict(q["detail"])
            q["detail"]["n"] = (nx, ny, 0)
        if q.get("vent"):
            q["vent"] = hid
            VENTS[hid] = q
        objects.append(q)
    bump_world()
    return hid


def draw_ghost(window, cam, tpl, rot, wx, wy):
    """Зелёный 3D-контур макета, ползущий за мышью."""
    layout = _tpl_layout(tpl, rot)
    if not layout:
        return
    # сдвинуть так, чтобы прицел был центром объединённого прямоугольника
    ux0 = min(r[0] for r in layout)
    uy0 = min(r[1] for r in layout)
    ux1 = max(r[0] + r[2] for r in layout)
    uy1 = max(r[1] + r[3] for r in layout)
    cx, cy = (ux0 + ux1) / 2, (uy0 + uy1) / 2
    values = []
    for ux in (ux0, ux1, cx):
        for uy in (uy0, uy1, cy):
            g = ground_height_at(wx + ux - cx, wy + uy - cy)
            if g is not None:
                values.append(g)
    zb = (math.floor(min(values) / 0.05) * 0.05 - 0.045) if values else 0.0
    surf = pygame.Surface((cam.win_w, cam.win_h), pygame.SRCALPHA)
    lim = [(0, 0), (ux1, 0), (ux1, uy1), (0, uy1)]
    q = [cam.world_to_screen(wx + a - cx, wy + b - cy, zb) for a, b in lim]
    pygame.draw.polygon(surf, (110, 255, 140, 46), q)
    pygame.draw.polygon(surf, (110, 255, 140, 190), q, 1)
    for xa, ya, w, d, p in layout:
        X, Y = wx + xa - cx, wy + ya - cy
        z, h = p["z"] + zb, p["h"]
        pts = [(X, Y), (X + w, Y), (X + w, Y + d), (X, Y + d)]
        top = [cam.world_to_screen(a, b, z + h) for a, b in pts]
        bot = [cam.world_to_screen(a, b, z) for a, b in pts]
        pygame.draw.polygon(surf, (110, 255, 140, 42), top)
        for j in range(4):
            j2 = (j + 1) % 4
            pygame.draw.line(surf, (130, 255, 150, 120), top[j], top[j2], 1)
            pygame.draw.line(surf, (130, 255, 150, 90), bot[j], top[j], 1)
    window.blit(surf, (0, 0))



# ---------------------------------------------------------------------------
# Палитра зданий (кнопка Y) + режим установки
# ---------------------------------------------------------------------------
PALETTE = {"open": False, "rects": []}
PLACE = {"tpl": None, "rot": 0}


def draw_palette(window, hud, lib, mouse):
    """Панель выбора здания: 8 эпох (4 колонки x 2 ряда), списки классов."""
    w, h = window.get_size()
    groups = {}
    for t in lib:
        groups.setdefault(t["epoch"], []).append(t)
    ncls = [len(groups.get(e, [])) for e in range(8)]
    cell_w, title_h, item_h, pad = 250, 22, 17, 8
    cols = 4
    bh_top = title_h + max(ncls[:4]) * item_h + pad
    bh_bot = title_h + max(ncls[4:]) * item_h + pad
    pw = cols * cell_w + (cols + 1) * pad
    ph = bh_top + bh_bot + 3 * pad + 24
    ox, oy = max(6, (w - pw) // 2), max(6, (h - ph) // 2)
    bg = pygame.Surface((pw, ph), pygame.SRCALPHA)
    bg.fill((12, 14, 20, 238))
    window.blit(bg, (ox, oy))
    hud.text(window, "Выбери здание — эпохи слева направо",
             (ox + pad, oy + ph - 26), (170, 176, 190), hud.font_small)
    rects = []
    for ep in range(8):
        gx = ox + pad + (ep % cols) * (cell_w + pad)
        gy = oy + pad + (bh_top if ep >= cols else 0) + ((ep // cols) * pad)
        hud.text(window, EPOCH_NAMES[ep], (gx + 2, gy), (255, 236, 170),
                 hud.font_small)
        yy = gy + title_h
        for t in sorted(groups.get(ep, []), key=lambda q: q["cls"]):
            r = pygame.Rect(gx, yy, cell_w - 8, item_h - 3)
            hov = r.collidepoint(mouse)
            pygame.draw.rect(window,
                             (52, 66, 52) if hov else (24, 28, 34), r, 0, 3)
            pygame.draw.rect(window,
                             (110, 255, 140) if hov else (70, 76, 88), r, 1, 3)
            hud.text(window, t["name"], (gx + 7, yy + 2),
                     (200, 255, 210) if hov else (210, 214, 222),
                     hud.font_small)
            rects.append((r, t))
            yy += item_h
    return rects

def stack_height_at(objects, tx, ty):
    top = 0.0
    gh = ground_height_at(tx + 0.5, ty + 0.5)
    if gh is not None:
        top = gh
    for o in objects:
        if o["x"] <= tx < o["x"] + o["w"] and o["y"] <= ty < o["y"] + o["d"]:
            top = max(top, o["z"] + o["h"])
    return top


def top_object_at(objects, tx, ty):
    best, best_top = None, -1e9
    for o in objects:
        if o["x"] <= tx < o["x"] + o["w"] and o["y"] <= ty < o["y"] + o["d"]:
            if o["z"] + o["h"] >= best_top:
                best, best_top = o, o["z"] + o["h"]
    return best


def support_height_obj(objects, o):
    cx, cy = o["x"] + o["w"] / 2, o["y"] + o["d"] / 2
    sup = ground_height_at(cx, cy)
    if sup is None:
        sup = -1e9
    g = _support_index(objects)
    x0, x1 = o["x"], o["x"] + o["w"]
    y0, y1 = o["y"], o["y"] + o["d"]
    zlim = o["z"] + 0.06
    for ix in range(math.floor(x0), math.floor(x1 - 1e-6) + 1):
        for iy in range(math.floor(y0), math.floor(y1 - 1e-6) + 1):
            lst = g.get((ix, iy))
            if not lst:
                continue
            for top2, ox0, ox1, oy0, oy1, o2 in lst:
                if o2 is o or top2 > zlim or top2 <= sup:
                    continue
                if x0 < ox1 and ox0 < x1 and y0 < oy1 and oy0 < y1:
                    sup = top2
    return sup


def _support_index(objects):
    """Клетка 1x1 -> [(верх, x0, x1, y0, y1)] по убыванию верха.
    Кэш на пару списков (список не-ёлков и полный список): раньше индекс
    пересобирался на каждом физ-кадре, потому что solids создавался заново."""
    e = _SUP_IDX.get(id(objects))
    if e is not None and e[0] == WORLD_VERSION and e[1] is objects:
        return e[2]
    grid = {}
    for o in objects:
        if o.get("shape") == "tree":
            continue
        top = o["z"] + o["h"]
        x0, x1, y0, y1 = o["x"], o["x"] + o["w"], o["y"], o["y"] + o["d"]
        for ix in range(math.floor(x0), math.floor(x1 - 1e-6) + 1):
            for iy in range(math.floor(y0), math.floor(y1 - 1e-6) + 1):
                grid.setdefault((ix, iy), []).append((top, x0, x1, y0,
                                                     y1, o))
    for lst in grid.values():
        # key без dict: при равных геометриях не сравнивать сами объекты
        lst.sort(key=lambda t: (t[0], t[1], t[3]), reverse=True)
    if len(_SUP_IDX) > 4:
        _SUP_IDX.clear()
    _SUP_IDX[id(objects)] = (WORLD_VERSION, objects, grid)
    return grid


_SOLIDS_C = {"key": None, "lst": None}
_TREES_C = {"key": None, "lst": None}


def _solids_of(objects):
    """Не-ёлки: список со стабильной идентичностью (кэш _support_index
    привязан к id списка), пересборка только при смене мира/состава."""
    key = (id(objects), WORLD_VERSION, len(objects))
    if _SOLIDS_C["key"] != key:
        _SOLIDS_C["lst"] = [o for o in objects if o.get("shape") != "tree"]
        _SOLIDS_C["key"] = key
    return _SOLIDS_C["lst"]


def _trees_of(objects):
    """Ёлки с стабильной идентичностью списка для разнесённого апдейта."""
    key = (id(objects), WORLD_VERSION, len(objects))
    if _TREES_C["key"] != key:
        _TREES_C["lst"] = [o for o in objects if o.get("shape") == "tree"]
        _TREES_C["key"] = key
    return _TREES_C["lst"]


def support_height_point(objects, x, y, z):
    gh = ground_height_at(x, y)
    sup = gh if gh is not None else -1e9
    lst = _support_index(objects).get((math.floor(x), math.floor(y)))
    if lst:
        zlim = z + 0.06
        for top, x0, x1, y0, y1, _o in lst:
            if top > zlim:
                continue
            if x0 <= x < x1 and y0 <= y < y1:
                sup = top  # список по убыванию — первый годный и есть ответ
                break
    return sup


# ---------------------------------------------------------------------------
# Небо, звёзды, солнце/луна, облака
# ---------------------------------------------------------------------------
_SKY_CACHE = {"key": None, "surf": None}


def make_sky(w, h):
    """Вертикальный градиент меняется только при переходе цвета на
    следующее целое значение. Между такими изменениями не создаём Surface
    и не рисуем сотни линий каждый кадр.
    """
    top, bot = LIGHT["sky"]
    key = (w, h, top, bot)
    if _SKY_CACHE["key"] == key:
        return _SKY_CACHE["surf"]
    sky = pygame.Surface((w, h))
    for yy in range(h):
        f = yy / max(1, h - 1)
        c = tuple(int(top[i] + (bot[i] - top[i]) * f) for i in range(3))
        pygame.draw.line(sky, c, (0, yy), (w, yy))
    _SKY_CACHE["key"], _SKY_CACHE["surf"] = key, sky
    return sky


_STARS = None


def _stars_table():
    """Позиции/яркость/размер звёзд детерминированы — считаем один раз."""
    global _STARS
    if _STARS is None:
        _STARS = [(hash01(i, 7, 1), hash01(i, 13, 2), i * 1.7,
                   hash01(i, 29, 3),
                   2 if hash01(i, 5, 4) > 0.85 else 1) for i in range(170)]
    return _STARS


def draw_stars(window, w, h, frame):
    fade = LIGHT.get("star_a", 1.0)
    if fade <= 0.02:
        return  # звёзды плавно проявляются только к ночи
    for hx, hy, ph, hb, sz in _stars_table():
        x = hx * w
        y = hy * h * 0.7
        tw = 0.55 + 0.45 * math.sin(frame * 0.05 + ph)
        b = int((140 + 110 * tw * hb) * fade)
        if b < 10:
            continue
        pygame.draw.rect(window, (b, b, min(255, b + 20)),
                         (int(x), int(y), sz, sz))


def draw_disc(window, w, h):
    # солнце и луна плавно «сменяют» друг друга (кросс-фейд в сумерках)
    kind, fx, fy, col = LIGHT["disc"]
    night_w = LIGHT.get("star_a", 0.0)
    sun_w = clamp(1.0 - 2.0 * night_w, 0.0, 1.0)
    moon_w = clamp(2.0 * night_w - 1.0, 0.0, 1.0)
    if sun_w <= 0.02 and moon_w <= 0.02:
        return
    sx, sy = int(w * fx), int(h * fy)
    R = SP(110)
    glow = pygame.Surface((R * 2, R * 2), pygame.SRCALPHA)
    if sun_w > 0.02:
        for rr, aa in ((SP(105), 26), (SP(70), 42), (SP(45), 66)):
            pygame.draw.circle(glow, col + (int(aa * sun_w),), (R, R), rr)
        pygame.draw.circle(glow, col + (int(255 * sun_w),), (R, R), SP(24))
    if moon_w > 0.02:
        mcol = (235, 242, 255)
        for rr, aa in ((SP(105), 18), (SP(70), 30), (SP(45), 50)):
            pygame.draw.circle(glow, mcol + (int(aa * moon_w),), (R, R), rr)
        pygame.draw.circle(glow, mcol + (int(255 * moon_w),), (R, R), SP(20))
        for mx, my, mr in [(-SP(6), -SP(4), SP(5)), (SP(7), SP(5), SP(4)),
                           (-SP(2), SP(9), SP(3))]:
            pygame.draw.circle(glow, (205, 215, 235, int(200 * moon_w)),
                               (R + mx, R + my), mr)
    window.blit(glow, (sx - R, sy - R))
    if sun_w > 0.5:
        pygame.draw.circle(window, tone(col, 0.92), (sx, sy), SP(24), 1)


FAR_CLOUDS = []
NEAR_CLOUDS = []

_EDGE_CACHE = {}
_EDGE_FORM = [(0.07, 0.12, 90), (0.24, 0.05, 120), (0.46, 0.10, 80),
              (0.68, 0.055, 110), (0.88, 0.13, 95), (0.5, 0.34, 70),
              (0.16, 0.31, 62)]


def _glow_surf(r, col):
    s = pygame.Surface((r * 8, r * 8), pygame.SRCALPHA)
    c = r * 4
    for i in range(5):
        rr = max(2, int(r * (0.9 + 0.62 * i)))
        aa = int(200 / (i + 0.85))
        pygame.draw.circle(s, col + (aa,), (c, c), rr)
    return s


def draw_edge_glow(window, w, h, frame):
    """Мягкие анимированные засветы облаков у краёв неба (без облаков-объектов)."""
    key = (w, h, LIGHT["cloud_w"], LIGHT["cloud_s"])
    slots = _EDGE_CACHE.get(key)
    if slots is None:
        if len(_EDGE_CACHE) > 6:
            _EDGE_CACHE.clear()
        slots = []
        for i, (fx, fy, r) in enumerate(_EDGE_FORM):
            mix = hash01(i, 3, 91)
            # приближаем к чистому свету, чтобы пятно читалось на небе
            col = tuple(min(255, int(LIGHT["cloud_w"][c] * 0.72
                                     + 245 * 0.28 + 18 * mix))
                        for c in range(3))
            slots.append((_glow_surf(int(SP(r)), col), fx, fy, r,
                          hash01(i, 7, 92)))
        _EDGE_CACHE[key] = slots
    t = ANIM_T
    for spr, fx, fy, r, ph in slots:
        drift = t * (3.0 + r * 0.06) + CLOUD_OFF * (0.10 + ph * 0.25)
        span = w + r * 8
        px = (fx * span + drift * (1 if ph > 0.4 else -1)) % span - r * 4
        py = fy * h + math.sin(t * 0.30 + ph * 9.0) * r * 0.12
        spr.set_alpha(int(250 * (0.78 + 0.22 * math.sin(t * 0.42 + ph * 7.1))))
        window.blit(spr, (int(px - r * 4), int(py - r * 4)))


# ---------------------------------------------------------------------------
# Остров
# ---------------------------------------------------------------------------
def speckle(window, cam, x, y, color):
    ix, iy = int(x), int(y)
    if _SPRITE_MODE:
        ww, hh = window.get_size()
        if 0 <= ix < ww and 0 <= iy < hh:
            window.set_at((ix, iy), color)
    elif 0 <= ix < cam.win_w and 0 <= iy < cam.win_h:
        window.set_at((ix, iy), color)


def draw_pebble(window, cam, x, y, base):
    light = tone(base, 1.45)
    dark = tone(base, 0.62)
    mid = tone(base, 1.05)
    ix, iy = int(x), int(y)
    n = SP(2)
    for ox in range(n):
        for oy in range(n):
            s = (ox - 0.5) * SUN_SX + (oy - 0.5) * SUN_SY
            c = light if s > 0.15 else (dark if s < -0.15 else mid)
            speckle(window, cam, ix + ox, iy + oy, c)


def draw_island_sides(window, cam):
    W, D = GRID_W, GRID_D
    sides = [
        dict(a=(W, 0), b=(W, D), n=RIGHT_N[cam.rot], seed=11, wl=D),
        dict(a=(0, D), b=(W, D), n=LEFT_N[cam.rot], seed=77, wl=W),
    ]
    zf = min(cam.zoom, 1.6)
    for side in sides:
        n = side["n"]
        A = cam.iso_project(*side["a"], 0)
        B = cam.iso_project(*side["b"], 0)
        A2 = cam.iso_project(*side["a"], -ISLAND_T)
        B2 = cam.iso_project(*side["b"], -ISLAND_T)
        quad = [A, B, B2, A2]

        dirt = shade(DIRT_DEEP, n)
        rock = shade(ROCK_DEEP, n)

        bands = [(0.00, 0.30, tone(dirt, 1.04)),
                 (0.30, 0.58, tone(dirt, 0.96)),
                 (0.58, 0.80, tone(dirt, 1.00)),
                 (0.80, 1.00, rock)]
        for t0, t1, col in bands:
            pygame.draw.polygon(window, col,
                                [quad_pt(quad, 0, t0), quad_pt(quad, 1, t0),
                                 quad_pt(quad, 1, t1), quad_pt(quad, 0, t1)])

        edge_len = math.hypot(B[0] - A[0], B[1] - A[1])
        for t_edge in (0.30, 0.58, 0.80):
            steps = max(8, int(edge_len / (9 / PIXEL)))
            for i in range(steps + 1 if cam.zoom >= 99 else 0):
                u = i / steps
                wob = math.sin(u * 22 + side["seed"]) * SP(2) * zf
                px, py = quad_pt(quad, u, t_edge)
                speckle(window, cam, px, py + wob, tone(dirt, 0.72))

        nx = max(10, int(side["wl"] / 0.55))
        ny = max(4, int(ISLAND_T / 0.55))
        for gy in range(ny + 1 if cam.zoom >= 99 else 0):
            for gx in range(nx + 1):
                u, t = gx / nx, gy / ny
                px, py = quad_pt(quad, u, t)
                r = hash01(gx + side["seed"] * 131, gy, 7)
                raw = ROCK_DEEP if t > 0.80 else DIRT_DEEP
                stone_p = 0.16 if t > 0.80 else 0.06
                if r < stone_p:
                    draw_pebble(window, cam, px, py, shade(raw, n))
                else:
                    nn = tilt_normal(n, gx + side["seed"], gy, 21, 0.6)
                    f = 0.72 if r < 0.55 else 1.18
                    speckle(window, cam, px, py, tone(shade(raw, nn), f))

        lip = shade(GRASS, n)
        teeth = max(16, int(side["wl"] / 0.5))
        for i in range(teeth):
            t0 = i / teeth
            left = lerp_pt(A, B, t0)
            right = lerp_pt(A, B, min(1.0, t0 + 0.9 / teeth))
            mid = ((left[0] + right[0]) / 2, (left[1] + right[1]) / 2)
            depth = SP(4 + 7 * hash01(i, side["seed"], 3)) * zf
            pygame.draw.polygon(window, lip, [left, right, (mid[0], mid[1] + depth)])

        bottom_n = max(8, int(side["wl"] / 1.5))
        for i in range(bottom_n):
            t0 = (i + 0.5) / bottom_n
            c = lerp_pt(A2, B2, t0)
            hw = edge_len / bottom_n * 0.28
            depth = SP(8 + 14 * hash01(i, side["seed"], 5)) * zf
            pygame.draw.polygon(window, tone(rock, 0.8),
                                [(c[0] - hw, c[1]), (c[0] + hw, c[1]),
                                 (c[0], c[1] + depth)])


# ---------------------------------------------------------------------------
# Земля
# ---------------------------------------------------------------------------
FLOWER_COLORS = [(240, 240, 245), (240, 200, 120), (235, 150, 180)]
CHECKER_CACHE = {}


def checker_sprite(sw, sh):
    key = (sw, sh)
    s = CHECKER_CACHE.get(key)
    if s is None:
        if len(CHECKER_CACHE) > 30:
            CHECKER_CACHE.clear()
        s = pygame.Surface((sw, sh), pygame.SRCALPHA)
        w2, h2 = sw / 2, sh / 2
        pygame.draw.polygon(s, (10, 20, 10, 26),
                            [(w2, 1), (sw - 1, h2), (w2, sh - 1), (1, h2)])
        CHECKER_CACHE[key] = s
    return s


def draw_tile_details(window, cam, x, y, pts, is_dirt):
    cx = (pts[0][0] + pts[2][0]) / 2
    cy = (pts[0][1] + pts[2][1]) / 2

    def inside(k, spread=0.7):
        corner = pts[k % 4]
        f = 0.12 + spread * hash01(x, y, k)
        return (cx + (corner[0] - cx) * f, cy + (corner[1] - cy) * f)

    if is_dirt:
        dt = shade(DIRT_COLOR, PZ)
        for k in range(6):
            px, py = inside(k)
            r = hash01(x, y, k + 50)
            if r < 0.18:
                draw_pebble(window, cam, px, py, dt)
            elif r < 0.6:
                speckle(window, cam, px, py, tone(dt, 0.7))
    else:
        g_dark = shade(GRASS_DARK, PZ)
        g_light = shade(GRASS_LIGHT, PZ)
        for k in range(6):
            px, py = inside(k + 100, 0.7)
            lean = (hash01(x, y, k + 120) - 0.5) * 2
            hgt = SP(2 + int(hash01(x, y, k + 130) * 2))
            x0, y0 = int(px), int(py)
            if 0 <= x0 < cam.win_w and 1 <= y0 < cam.win_h:
                pygame.draw.line(window, g_dark, (x0, y0),
                                 (int(x0 + lean), y0 - hgt), 1)
                speckle(window, cam, x0 + lean, y0 - hgt, g_light)
        if hash01(x, y, 200) < 0.05:
            px, py = inside(7, 0.5)
            fx, fy = int(px), int(py)
            pygame.draw.line(window, g_dark, (fx, fy), (fx, fy - SP(3)), 1)
            pet = FLOWER_COLORS[int(hash01(x, y, 201) * 3) % 3]
            n = SP(2)
            for ox in range(n):
                for oy in range(n):
                    speckle(window, cam, fx + ox - 1, fy - 5 + oy, pet)
        if hash01(x, y, 210) < 0.07:
            px, py = inside(9, 0.6)
            draw_pebble(window, cam, px, py, shade(STONE_GRAY, PZ))


def _plate_h(x, y, fx, fy):
    h = ground_height_at(x + fx, y + fy)
    if h is None:
        return 0.0
    return round(h / 0.15) * 0.15  # ступени: воронка полностью пиксельная


def draw_dent_overlay(window, cam, x, y):
    SUB = 4
    n = height_normal_at(x, y)
    for sy in range(SUB):
        for sx in range(SUB):
            fx0, fy0 = sx / SUB, sy / SUB
            h = _plate_h(x, y, fx0 + 0.5 / SUB, fy0 + 0.5 / SUB)
            bh = _base_plate_h(x, y, fx0 + 0.5 / SUB, fy0 + 0.5 / SUB)
            depth = clamp((bh - h) / 0.30, 0.0, 1.0)
            patch = 0.85 + 0.30 * hash01(x * 4 + sx, y * 4 + sy, 77)
            g = tone(shade(GRASS, n), patch)
            dd = tuple(int(DIRT_COLOR[i] + (DIRT_DEEP[i] - DIRT_COLOR[i]) * depth ** 0.7) for i in range(3))
            e = tone(shade(dd, n), patch)
            base = tuple(int(g[i] + (e[i] - g[i]) * depth) for i in range(3))
            sc = clamp((depth - 0.55) / 0.45, 0.0, 1.0)
            base = tone(base, 1.0 - 0.45 * sc)  # пригар в центре
            c = [cam.world_to_screen(x + fx0, y + fy0, h),
                 cam.world_to_screen(x + fx0 + 1 / SUB, y + fy0, h),
                 cam.world_to_screen(x + fx0 + 1 / SUB, y + fy0 + 1 / SUB, h),
                 cam.world_to_screen(x + fx0, y + fy0 + 1 / SUB, h)]
            pygame.draw.polygon(window, base, c)
            # рваная крошка земли на пластине
            cx = sum(p[0] for p in c) / 4
            cy = sum(p[1] for p in c) / 4
            for k in range(3):
                corner = c[k % 4]
                f = 0.15 + 0.6 * hash01(x * 4 + sx, y * 4 + sy, k)
                px = cx + (corner[0] - cx) * f
                py = cy + (corner[1] - cy) * f
                r = hash01(x + sx, y + sy, k + 300)
                if r < 0.40:
                    draw_pebble(window, cam, px, py, shade(DIRT_DEEP, n))
                else:
                    nn = tilt_normal(n, x * 4 + sx, y * 4 + sy, k, 0.7)
                    speckle(window, cam, px, py,
                            tone(shade(DIRT_DEEP, nn), 0.75 if r < 0.6 else 1.2))


def _draw_rim_overlay(window, cam, x, y):
    """Вал выброса: приподнятые пластины + светлая крошка."""
    SUB = 4
    n = height_normal_at(x, y)
    for sy in range(SUB):
        for sx in range(SUB):
            fx0, fy0 = sx / SUB, sy / SUB
            h = _plate_h(x, y, fx0 + 0.5 / SUB, fy0 + 0.5 / SUB)
            patch = 0.90 + 0.25 * hash01(x * 4 + sx, y * 4 + sy, 78)
            g = tone(shade(GRASS, n), patch)
            e = tone(shade(DIRT_COLOR, n), patch * 1.05)
            col = tuple(int(g[i] + (e[i] - g[i]) * 0.45) for i in range(3))
            c = [cam.world_to_screen(x + fx0, y + fy0, h),
                 cam.world_to_screen(x + fx0 + 1 / SUB, y + fy0, h),
                 cam.world_to_screen(x + fx0 + 1 / SUB, y + fy0 + 1 / SUB, h),
                 cam.world_to_screen(x + fx0, y + fy0 + 1 / SUB, h)]
            pygame.draw.polygon(window, col, c)
            cx = sum(p[0] for p in c) / 4
            cy = sum(p[1] for p in c) / 4
            for k in range(2):
                corner = c[(k * 2 + 1) % 4]
                f = 0.2 + 0.55 * hash01(x * 4 + sx, y * 4 + sy, k + 50)
                px = cx + (corner[0] - cx) * f
                py = cy + (corner[1] - cy) * f
                nn = tilt_normal(n, x * 4 + sx, y * 4 + sy, k + 9, 0.7)
                speckle(window, cam, px, py,
                        tone(shade(DIRT_COLOR, nn), 1.15))


def _tile_order_key(x, y, rot):
    if rot == 0:
        return x + y
    if rot == 1:
        return x - y
    if rot == 2:
        return -(x + y)
    return y - x


def _ordered_tiles(x0, x1, y0, y1, rot):
    """Клетки bbox сразу в порядке живописи (диагонали, без сортировки)."""
    if rot == 0:
        for s in range(x0 + y0, x1 + y1 + 1):
            for x in range(max(x0, s - y1), min(x1, s - y0) + 1):
                yield (x, s - x)
    elif rot == 1:
        for dd in range(x0 - y1, x1 - y0 + 1):
            for x in range(max(x0, y0 + dd), min(x1, y1 + dd) + 1):
                yield (x, x - dd)
    elif rot == 2:
        for s in range(x1 + y1, x0 + y0 - 1, -1):
            for x in range(max(x0, s - y1), min(x1, s - y0) + 1):
                yield (x, s - x)
    else:
        for dd in range(y0 - x1, y1 - x0 + 1):
            for x in range(max(x0, y0 - dd), min(x1, y1 - dd) + 1):
                yield (x, x + dd)


def _visible_tile_range(cam, rect=None):
    """Какие клетки в кадре (инверсия аффинной решётки)."""
    if rect is None:
        corners = ((0, 0), (cam.win_w, 0), (0, cam.win_h),
                   (cam.win_w, cam.win_h))
    else:
        corners = ((rect[0], rect[1]), (rect[0] + rect[2], rect[1]),
                   (rect[0], rect[1] + rect[3]),
                   (rect[0] + rect[2], rect[1] + rect[3]))
    ox, oy = cam.world_to_screen(0, 0, 0)
    ax, ay = cam.world_to_screen(1, 0, 0)
    bx, by = cam.world_to_screen(0, 1, 0)
    dxx, dxy = ax - ox, ay - oy
    dyx, dyy = bx - ox, by - oy
    det = dxx * dyy - dyx * dxy
    if abs(det) < 1e-9:
        return 0, GRID_W - 1, 0, GRID_D - 1
    xs, ys = [], []
    for qx, qy in corners:
        rx, ry = qx - ox, qy - oy
        xs.append((rx * dyy - ry * dyx) / det)
        ys.append((ry * dxx - rx * dxy) / det)
    return (max(0, int(min(xs)) - 8), min(GRID_W - 1, int(max(xs)) + 8),
            max(0, int(min(ys)) - 8), min(GRID_D - 1, int(max(ys)) + 8))


def _farmap_build(preset_idx):
    N = GRID_W * GRID_D
    X = np.empty(N, np.float32)
    Y = np.empty(N, np.float32)
    H = np.empty(N, np.float32)
    k = 0
    for y in range(GRID_D):
        r0, r1 = BASE_H[y], BASE_H[y + 1]
        for x in range(GRID_W):
            X[k] = x + 0.5
            Y[k] = y + 0.5
            H[k] = (r0[x] + r0[x + 1] + r1[x] + r1[x + 1]) * 0.25
            k += 1
    Hg = H.reshape(GRID_D, GRID_W)
    gx = np.zeros_like(Hg)
    gy = np.zeros_like(Hg)
    gx[:, 1:-1] = (Hg[:, 2:] - Hg[:, :-2]) * 0.5
    gy[1:-1, :] = (Hg[2:, :] - Hg[:-2, :]) * 0.5
    il = 1.0 / np.sqrt(gx * gx + gy * gy + 1.0)
    dot = (-gx * il) * SUN[0] + (-gy * il) * SUN[1] + il * SUN[2]
    hlev = np.clip(np.round((dot - 0.88) * 9 + 2), 0, 4)
    tint = (0.78 + 0.11 * hlev).reshape(N)
    grass = np.array(tone(shade(GRASS, PZ), 1.0), np.float32)
    dirt = np.array(tone(shade(DIRT_COLOR, PZ), 1.0), np.float32)
    colors = np.empty((N, 3), np.uint8)
    colors[:] = np.clip(grass * tint[:, None], 0, 255)
    _FARMAP["X"], _FARMAP["Y"], _FARMAP["H"] = X, Y, H
    _FARMAP["colors"], _FARMAP["key"] = colors, preset_idx
    _FARMAP["painted"] = set()
    _FARMAP["rpainted"] = set()
    _FARMAP["dkey"] = None


def _draw_ground_far(window, cam, preset_idx):
    """Фар-план: все клетки — векторными точками 2x2 (точно по проекции)."""
    if _FARMAP["key"] != preset_idx or _FARMAP["colors"] is None:
        _farmap_build(preset_idx)
    dkey = (len(DENTED), len(_RIMTILES))
    if _FARMAP["dkey"] != dkey:
        colors = _FARMAP["colors"]
        dd = tuple(int(v) for v in tone(shade(DIRT_DEEP, PZ), 0.62))
        de = tuple(int(v) for v in tone(shade(DIRT_COLOR, PZ), 1.08))
        for x, y in DENTED:
            if (x, y) not in _FARMAP["painted"]:
                colors[y * GRID_W + x] = dd
                _FARMAP["painted"].add((x, y))
        for x, y in _RIMTILES:
            if (x, y) not in _FARMAP["rpainted"]:
                if (x, y) not in DENTED:
                    colors[y * GRID_W + x] = de
                _FARMAP["rpainted"].add((x, y))
        _FARMAP["dkey"] = dkey
    X, Y, H = _FARMAP["X"], _FARMAP["Y"], _FARMAP["H"]
    colors = _FARMAP["colors"]
    ox, oy = cam.world_to_screen(0, 0, 0)
    ax, ay = cam.world_to_screen(1, 0, 0)
    bx, by = cam.world_to_screen(0, 1, 0)
    dxx, dxy = ax - ox, ay - oy
    dyx, dyy = bx - ox, by - oy
    ze = cam.zoom / PIXEL
    w, h = cam.win_w, cam.win_h
    px = (ox + X * dxx + Y * dyx).astype(np.int32)
    py = (oy + X * dxy + Y * dyy - H * TILE_Z * ze).astype(np.int32)
    if cam.rot == 0:
        kk = X + Y
    elif cam.rot == 1:
        kk = X - Y
    elif cam.rot == 2:
        kk = -(X + Y)
    else:
        kk = Y - X
    order = np.argsort(kk, kind="stable")
    # фон = небо пресета (градиент + звёзды), не чёрный
    top, bot = LIGHT["sky"]
    _t = np.linspace(0.0, 1.0, max(1, h), dtype=np.float32)[:, None, None]
    img = (np.array(top, np.float32)[None, None, :] * (1.0 - _t)
           + np.array(bot, np.float32)[None, None, :] * _t)
    img = np.repeat(img, max(1, w), axis=1).astype(np.uint8)
    if LIGHT["stars"]:
        for _i in range(150):
            _sx = int(hash01(_i, 7, 1) * max(1, w - 1))
            _sy = int(hash01(_i, 13, 2) * h * 0.60)
            _b = int(150 + 100 * hash01(_i, 29, 3))
            img[_sy, _sx] = (_b, _b, min(255, _b + 20))
    # блоб клетки масштабируется под питч: сплошной ковёр без полос
    _blob = max(2, min(12, int(max(abs(dxx), abs(dyx), abs(dxy),
                                   abs(dyy)) * 1.9) + 1))
    ok = (px >= 0) & (px < w - _blob) & (py >= 0) & (py < h - _blob)
    idx = order[ok[order]]
    _py, _px = py[idx], px[idx]
    _col = colors[idx]
    for _a in range(_blob):
        for _b in range(_blob):
            img[_py + _a, _px + _b] = _col
    buf = img.tobytes()
    window.blit(pygame.image.frombuffer(buf, (w, h), "RGB"), (0, 0))
    _FARMAP["buf"] = buf



def _paint_ground_base(window, cam):
    c0 = cam.world_to_screen(0, 0, 0)
    c1 = cam.world_to_screen(GRID_W, 0, 0)
    c2 = cam.world_to_screen(GRID_W, GRID_D, 0)
    c3 = cam.world_to_screen(0, GRID_D, 0)
    pygame.draw.polygon(window, tone(shade(GRASS, PZ), 0.92),
                        [c0, c1, c2, c3])


def draw_ground(window, cam, show_checker, preset_idx, only=None):
    # вдали: растровый фар-план вместо тысяч спрайтов
    if cam.zoom < 0.35 and not show_checker:
        _draw_ground_far(window, cam, preset_idx)
        return
    # only: инкремент — красить только эти клетки (порядок тот же)
    # аффинная решётка: 3 проекции на кадр вместо тысяч вызовов
    ox, oy = cam.world_to_screen(0, 0, 0)
    ax, ay = cam.world_to_screen(1, 0, 0)
    bx, by = cam.world_to_screen(0, 1, 0)
    dxx, dxy = ax - ox, ay - oy
    dyx, dyy = bx - ox, by - oy
    ze = cam.zoom / PIXEL
    ov = 2 + int(cam.zoom * 3)  # нахлёст прячет уступы холмов
    sw = max(2, int(round(TILE_W * cam.zoom / PIXEL))) + ov
    sh = max(1, int(round(TILE_H * cam.zoom / PIXEL))) + ov
    chk = checker_sprite(sw, sh) if show_checker else None
    if only is not None:
        tiles = sorted(only, key=lambda t: (_tile_order_key(t[0], t[1],
                                                            cam.rot),
                                            t[0], t[1]))
    else:
        x0, x1, y0, y1 = _visible_tile_range(cam)
        tiles = _ordered_tiles(x0, x1, y0, y1, cam.rot)
    sun0, sun1, sun2 = SUN
    for x, y in tiles:
        px = ox + x * dxx + y * dyx
        py = oy + x * dxy + y * dyy
        gh00, gh10 = GH[y][x], GH[y][x + 1]
        gh01, gh11 = GH[y + 1][x], GH[y + 1][x + 1]
        havg = (gh00 + gh10 + gh01 + gh11) * 0.25
        if havg:
            py -= havg * TILE_Z * ze
        cx = px + (dxx + dyx) * 0.5
        cy = py + (dxy + dyy) * 0.5
        if cx < -sw or cx > cam.win_w + sw or cy < -sh or cy > cam.win_h + sh:
            continue
        dhdx = (gh10 + gh11 - gh00 - gh01) * 0.5
        dhdy = (gh01 + gh11 - gh00 - gh10) * 0.5
        if dhdx or dhdy:
            il = 1.0 / math.sqrt(dhdx * dhdx + dhdy * dhdy + 1.0)
            dot = (-dhdx * il) * sun0 + (-dhdy * il) * sun1 + il * sun2
            hlev = clamp(int(round((dot - 0.88) * 9 + 2)), 0, 4)
        else:
            hlev = 2
        is_dirt = False
        spr = ground_sprite("grass", int(hash01(x, y, 5) * 4) % 4,
                            sw, sh, preset_idx, cam.rot, hlev)
        _sx, _sy = math.floor(cx - sw / 2), math.floor(cy - sh / 2)
        window.blit(spr, (_sx, _sy))
        if chk is not None and (x + y) % 2 == 0:
            window.blit(chk, (_sx, _sy))
        if cam.zoom >= 99:
            draw_tile_details(window, cam, x, y, pts, is_dirt)
        if (x, y) in DENTED:
            draw_dent_overlay(window, cam, x, y)
        elif (x, y) in _RIMTILES:
            _draw_rim_overlay(window, cam, x, y)


# ---------------------------------------------------------------------------
# Фигуры (+ зерно нормалей на гранях)
# ---------------------------------------------------------------------------
def box_corner_points(cam, x, y, z, w, d, h):
    rx0, ry0, wr, dr = cam.rotated_footprint(x, y, w, d)
    rx1, ry1 = rx0 + wr, ry0 + dr
    p1 = cam.iso_project(rx0, ry0, z + h)
    p2 = cam.iso_project(rx1, ry0, z + h)
    p3 = cam.iso_project(rx1, ry1, z + h)
    p4 = cam.iso_project(rx0, ry1, z + h)
    p2b = cam.iso_project(rx1, ry0, z)
    p3b = cam.iso_project(rx1, ry1, z)
    p4b = cam.iso_project(rx0, ry1, z)
    return p1, p2, p3, p4, p2b, p3b, p4b


def face_texels(window, cam, quad, face_n, base_raw, seed, preset_idx,
                world_w, world_h):
    """Крупные пиксели-тексели на грани (сетка в мировых единицах)."""
    return  # выкл: вид как издали на любом зуме
    minx = min(p[0] for p in quad)
    maxx = max(p[0] for p in quad)
    miny = min(p[1] for p in quad)
    maxy = max(p[1] for p in quad)
    if not _SPRITE_MODE and (maxx < 0 or minx > cam.win_w
                             or maxy < 0 or miny > cam.win_h):
        return
    TW = 0.28
    cols = max(1, int(round(world_w / TW)))
    rows = max(1, int(round(world_h / TW)))
    if cols * rows > 120:
        k = math.sqrt(cols * rows / 120)
        cols = max(1, int(cols / k))
        rows = max(1, int(rows / k))
    wpx = math.hypot(quad[1][0] - quad[0][0], quad[1][1] - quad[0][1])
    hpx = math.hypot(quad[3][0] - quad[0][0], quad[3][1] - quad[0][1])
    if wpx / cols < 4 / PIXEL or hpx / rows < 4 / PIXEL:
        return  # далеко: грань гладкая (быстро)
    for r in range(rows):
        t0, t1 = r / rows, (r + 1) / rows
        for c in range(cols):
            u0, u1 = c / cols, (c + 1) / cols
            col = grain_color(preset_idx, base_raw, face_n,
                              seed + c * 7, r * 13)
            pygame.draw.polygon(window, col,
                                [quad_pt(quad, u0, t0), quad_pt(quad, u1, t0),
                                 quad_pt(quad, u1, t1), quad_pt(quad, u0, t1)])


def draw_flat_side(window, quad, base_raw, face_n, seed, preset_idx, cam,
                   world_w, world_h):
    pygame.draw.polygon(window, shade(base_raw, face_n), quad)
    face_texels(window, cam, quad, face_n, base_raw, seed, preset_idx,
                world_w, world_h)


# ---------------------------------------------------------------------------
# Текстуры стен и крыш по материалам (стабильные, без «снега» между кадрами)
# ---------------------------------------------------------------------------
_PANEL_MATS = {"panel", "panel_dark", "concrete", "concrete_g"}
_EARTH_MATS = {"adobe", "dirt", "earth"}
_FIBRE_MATS = {"wattle", "straw", "cloth", "leather", "hide"}
_BRICK_MATS = {"brick", "brick_red"}
_TILES_MATS = {"tile", "tile_red", "tile_blue", "tile_gray", "tile_dark"}


def _quad_mottle(window, quad, lit, seed, n, t_lo, t_hi, f_lo, f_hi,
                 u_lo, u_hi, wu, wt, size_jitter=False):
    for k in range(n):
        u0 = u_lo + hash01(seed, k * 13, 7) * (u_hi - u_lo - wu)
        t0 = t_lo + hash01(seed, k * 17, 29) * (t_hi - t_lo - wt)
        ww = wu * (0.7 + 0.6 * hash01(seed, k * 7, 11)) if size_jitter else wu
        tt = wt * (0.7 + 0.6 * hash01(seed, k * 23, 41)) if size_jitter else wt
        f = f_lo + (f_hi - f_lo) * hash01(seed, k * 31, 53)
        pygame.draw.polygon(window, tone(lit, f),
                            [quad_pt(quad, u0, t0), quad_pt(quad, u0 + ww, t0),
                             quad_pt(quad, u0 + ww, t0 + tt),
                             quad_pt(quad, u0, t0 + tt)])


def draw_wall_face(window, quad, mat, base_raw, face_n, seed, preset_idx,
                   cam, world_w, world_h, face_id=1):
    """Грань стены с текстурой материала. quad: [верх-0, верх-1, низ-1, низ-0]."""
    fw = math.hypot(quad[1][0] - quad[0][0], quad[1][1] - quad[0][1])
    lit = shade(base_raw, face_n)
    f_t = 0.95 + 0.10 * hash01(seed, face_id * 7, 3)  # собственный тон стены
    pygame.draw.polygon(window, tone(lit, f_t), quad)
    if fw < 11:
        return
    m = mat or "concrete"
    if m in WOOD_MATS:
        rows = max(2, min(16, int(round(world_h / 0.30))))
        for r in range(rows):
            t0, t1 = r / rows, (r + 1) / rows
            f = f_t * (0.89 + 0.20 * hash01(seed, r * 13, 1))
            pygame.draw.polygon(window, tone(lit, f),
                                [quad_pt(quad, 0, t0), quad_pt(quad, 1, t0),
                                 quad_pt(quad, 1, t1), quad_pt(quad, 0, t1)])
            pygame.draw.line(window, tone(lit, f_t * 0.62),
                             quad_pt(quad, 0, t1 - 0.012),
                             quad_pt(quad, 1, t1 - 0.012), 1)
            pygame.draw.line(window, tone(lit, f * 1.10),
                             quad_pt(quad, 0, t0 + 0.014),
                             quad_pt(quad, 1, t0 + 0.014), 1)
        if fw >= 26:  # сучки
            for k in range(3):
                kk = int(hash01(seed, 91, k * 7) * rows)
                u = 0.12 + 0.76 * hash01(seed, 97, k * 13)
                t = (kk + 0.45) / rows
                px, py = quad_pt(quad, u, t)
                pygame.draw.ellipse(window, tone(lit, f_t * 0.58),
                                    (px - 1, py - 1, 2, 2))
    elif m in _PANEL_MATS:
        ncols = max(2, min(8, int(round(world_w / 1.1))))
        for c in range(ncols):
            u0, u1 = c / ncols, (c + 1) / ncols
            f = f_t * (0.91 + 0.14 * hash01(seed, c * 29, 5))
            pygame.draw.polygon(window, tone(lit, f),
                                [quad_pt(quad, u0, 0), quad_pt(quad, u1, 0),
                                 quad_pt(quad, u1, 1), quad_pt(quad, u0, 1)])
            if u1 < 1.0:
                pygame.draw.line(window, tone(lit, f_t * 0.70),
                                 quad_pt(quad, u1, 0.02),
                                 quad_pt(quad, u1, 0.98), 1)
        pygame.draw.line(window, tone(lit, f_t * 0.72),
                         quad_pt(quad, 0.02, 0.5), quad_pt(quad, 0.98, 0.5), 1)
        if fw >= 30:
            _quad_mottle(window, quad, lit, seed + 733, 8, 0.07, 0.85,
                         0.90, 1.10, 0.05, 0.92, 0.13, 0.11)
    elif m in _EARTH_MATS:
        rows = max(2, min(12, int(round(world_h / 0.34))))
        for r in range(rows):
            t0, t1 = r / rows, (r + 1) / rows
            f = f_t * (0.89 + 0.20 * hash01(seed, r * 13, 1))
            pygame.draw.polygon(window, tone(lit, f),
                                [quad_pt(quad, 0, t0), quad_pt(quad, 1, t0),
                                 quad_pt(quad, 1, t1), quad_pt(quad, 0, t1)])
            pygame.draw.line(window, tone(lit, f_t * 0.64),
                             quad_pt(quad, 0, t1 - 0.01),
                             quad_pt(quad, 1, t1 - 0.01), 1)
        if fw >= 20:  # вертикальные швы со смещением
            ncol = max(3, min(9, int(round(world_w / 0.55))))
            for r in range(rows):
                t0, t1 = r / rows, (r + 1) / rows
                off = 0.5 if r % 2 else 0.0
                for c in range(ncol + 1):
                    u = (c + off) / ncol
                    if u <= 0.02 or u >= 0.98:
                        continue
                    pygame.draw.line(window, tone(lit, f_t * 0.72),
                                     quad_pt(quad, u, t0 + 0.05),
                                     quad_pt(quad, u, t1 - 0.05), 1)
    elif m in _FIBRE_MATS:
        rows = max(3, min(18, int(round(world_h / 0.16))))
        for r in range(rows):
            t0, t1 = r / rows, (r + 1) / rows
            f = f_t * (0.93 + 0.14 * hash01(seed, r * 11, 2))
            pygame.draw.polygon(window, tone(lit, f),
                                [quad_pt(quad, 0, t0), quad_pt(quad, 1, t0),
                                 quad_pt(quad, 1, t1), quad_pt(quad, 0, t1)])
        if fw >= 18:  # прутья/нити: штрихи со смещением
            nd = max(4, min(14, int(round(world_w / 0.22))))
            for r in range(rows):
                t0, t1 = r / rows, (r + 1) / rows
                off = 0.5 if r % 2 else 0.0
                f = f_t * (0.84 + 0.22 * hash01(seed, r * 19, 4))
                for k in range(nd):
                    u0 = (k + off) / nd
                    u1 = u0 + 0.42 / nd
                    if u1 <= 0.02 or u0 >= 0.98:
                        continue
                    pygame.draw.line(window, tone(lit, f),
                                     quad_pt(quad, clamp(u0, 0, 1), t0 + 0.04),
                                     quad_pt(quad, clamp(u1, 0, 1), t1 - 0.04), 1)
    elif m in _BRICK_MATS:
        rows = max(2, min(14, int(round(world_h / 0.24))))
        ncol = max(3, min(12, int(round(world_w / 0.5))))
        for r in range(rows):
            t0, t1 = r / rows, (r + 1) / rows
            off = 0.5 if r % 2 else 0.0
            for c in range(ncol + 1):
                u0 = (c + off) / ncol
                u1 = (c + 1 + off) / ncol
                u0c, u1c = clamp(u0, 0, 1), clamp(u1, 0, 1)
                if u1c <= 0.01 or u0c >= 0.99:
                    continue
                f = f_t * (0.92 + 0.16 * hash01(seed, r * 31 + c, 6))
                pygame.draw.polygon(window, tone(lit, f),
                                    [quad_pt(quad, u0c, t0 + 0.02),
                                     quad_pt(quad, u1c, t0 + 0.02),
                                     quad_pt(quad, u1c, t1 - 0.02),
                                     quad_pt(quad, u0c, t1 - 0.02)])
    elif m in _TILES_MATS:
        rows = max(3, min(8, int(round(world_h / 0.34))))
        for r in range(rows):
            t0, t1 = r / rows, (r + 1) / rows
            f = f_t * (0.94 + 0.12 * hash01(seed, r * 11, 3))
            pygame.draw.polygon(window, tone(lit, f),
                                [quad_pt(quad, 0, t0), quad_pt(quad, 1, t0),
                                 quad_pt(quad, 1, t1), quad_pt(quad, 0, t1)])
            pygame.draw.line(window, tone(lit, f_t * 0.62),
                             quad_pt(quad, 0.02, t1 - 0.015),
                             quad_pt(quad, 0.98, t1 - 0.015), 1)
            pygame.draw.line(window, tone(lit, f * 1.12),
                             quad_pt(quad, 0.02, t0 + 0.02),
                             quad_pt(quad, 0.98, t0 + 0.02), 1)
    else:  # штукатурка / краска / прочее: разводы + трещины
        _quad_mottle(window, quad, lit, seed + 91, 10, 0.05, 0.84,
                     0.89, 1.11, 0.04, 0.88, 0.17, 0.15, size_jitter=True)
        if fw >= 40:
            for k in range(2):
                u = 0.15 + 0.7 * hash01(seed, k * 43, 17)
                pts = []
                uu, tt = u, 0.1 + 0.3 * hash01(seed, k * 57, 23)
                for s in range(3):
                    pts.append(quad_pt(quad,
                                       clamp(uu + (hash01(seed, k * 71, s) - 0.5) * 0.12, 0.03, 0.97),
                                       tt))
                    tt += 0.16 + 0.1 * hash01(seed, k * 83, s + 5)
                pygame.draw.lines(window, tone(lit, f_t * 0.72), False, pts, 1)
    # зерно штукатурки крупным планом (стабильное, кэшированное)
    if m in ("plaster", "white", "concrete", "concrete_g", "panel") and fw >= 30:
        rows = max(2, min(5, int(round(world_h / 0.5))))
        cols = max(2, min(6, int(round(world_w / 0.5))))
        for r in range(rows):
            t0, t1 = r / rows, (r + 1) / rows
            for c in range(cols):
                u0, u1 = c / cols, (c + 1) / cols
                g = grain_color(preset_idx, base_raw, face_n,
                                seed + c * 7 + face_id * 101, r * 13)
                pygame.draw.polygon(window, g,
                                    [quad_pt(quad, u0, t0), quad_pt(quad, u1, t0),
                                     quad_pt(quad, u1, t1), quad_pt(quad, u0, t1)])


def draw_top_face(window, cam, quad, mat, base_raw, seed, w, d):
    """Верхняя грань бокса: устойчивый тон + рисунок материала."""
    lit = shade(base_raw, PZ)
    f_t = 0.97 + 0.08 * hash01(seed, 5, 9)
    pygame.draw.polygon(window, tone(lit, f_t), quad)
    fw = max(math.hypot(quad[1][0] - quad[0][0], quad[1][1] - quad[0][1]),
             math.hypot(quad[3][0] - quad[0][0], quad[3][1] - quad[0][1]))
    if fw < 20:
        return
    m = mat or "concrete"
    if m in _TILES_MATS or (m == "tile"):
        rows = 4
        for r in range(1, rows):
            t = r / rows
            pygame.draw.line(window, tone(lit, f_t * 0.72),
                             quad_pt(quad, 0.03, t), quad_pt(quad, 0.97, t), 1)
            pygame.draw.line(window, tone(lit, f_t * 1.10),
                             quad_pt(quad, 0.03, t + 0.02),
                             quad_pt(quad, 0.97, t + 0.02), 1)
    elif m in _FIBRE_MATS:
        nd = max(6, min(16, int(round(max(w, d) / 0.3))))
        for k in range(nd):
            u = (k + 0.5) / nd
            tt = 0.08 + 0.8 * hash01(seed, k * 13, 7)
            f = f_t * (0.9 + 0.2 * hash01(seed, k * 7, 3))
            pygame.draw.line(window, tone(lit, f),
                             quad_pt(quad, u, tt),
                             quad_pt(quad, u + 0.05, tt + 0.1), 1)
    elif m in ("turf", "dirt", "grass") or base_raw == BASE_COLORS.get("turf"):
        for k in range(14):
            u = hash01(seed, k * 13, 11)
            t = hash01(seed, k * 17, 13)
            f = f_t * (0.88 + 0.24 * hash01(seed, k * 23, 29))
            pygame.draw.ellipse(window, tone(lit, f),
                                (quad_pt(quad, u, t)[0] - 1,
                                 quad_pt(quad, u, t)[1] - 1, 2, 2))
    elif m in WOOD_MATS:
        rows = max(2, min(6, int(round(min(w, d) / 0.35))))
        for r in range(1, rows):
            t = r / rows
            pygame.draw.line(window, tone(lit, f_t * 0.70),
                             quad_pt(quad, 0.05, t), quad_pt(quad, 0.95, t), 1)
    elif m in _PANEL_MATS:
        for t in (0.33, 0.66):
            pygame.draw.line(window, tone(lit, f_t * 0.78),
                             quad_pt(quad, 0.08, t), quad_pt(quad, 0.92, t), 1)
    else:
        _quad_mottle(window, quad, lit, seed + 41, 6, 0.08, 0.78,
                     0.94, 1.06, 0.06, 0.84, 0.14, 0.12, size_jitter=True)


def draw_stone_face(window, quad, base_raw, face_n, seed, h_px, zoom):
    top_len = math.hypot(quad[1][0] - quad[0][0], quad[1][1] - quad[0][1])
    rows = max(1, int(round(h_px / (TILE_Z * zoom / PIXEL) / 0.5)))
    world_len = top_len / (math.hypot(TILE_W / 2, TILE_H / 2) * (zoom / PIXEL))
    cols = max(1, int(round(world_len / 0.6)))
    lit = shade(base_raw, face_n)
    mortar = tone(lit, 0.52)
    pygame.draw.polygon(window, mortar, quad)
    elev_f = clamp(SUN[2] * 1.6, 0.25, 1.0)
    for r in range(rows):
        t0, t1 = r / rows, (r + 1) / rows
        tc = (t0 + t1) / 2
        band_f = 1.0 if tc < 0.58 else (0.94 if tc < 0.84 else 0.85)
        off = 0.5 if r % 2 else 0.0
        for c in range(-1, cols + 1):
            u0 = (c + off) / cols
            u1 = (c + 1 + off) / cols
            if u1 < 0 or u0 > 1:
                continue
            u0c, u1c = clamp(u0, 0, 1), clamp(u1, 0, 1)
            bn = tilt_normal(face_n, seed + r * 131, c * 17 + 3, 5, 0.5)
            tint = (0.90 + 0.18 * hash01(seed, r * 31 + c, 5)) * band_f
            cell = tone(shade(base_raw, bn), tint)
            pts = [quad_pt(quad, u0c, t0), quad_pt(quad, u1c, t0),
                   quad_pt(quad, u1c, t1), quad_pt(quad, u0c, t1)]
            pygame.draw.polygon(window, cell, pts)
            pygame.draw.line(window, tone(cell, 1 + 0.20 * elev_f),
                             pts[0], pts[1], 1)
            pygame.draw.line(window, tone(cell, 1 - 0.26 * elev_f),
                             pts[3], pts[2], 1)
    mw = 1 if zoom < 1.2 else 2
    for r in range(1, rows):
        t = r / rows
        pygame.draw.line(window, mortar, quad_pt(quad, 0, t), quad_pt(quad, 1, t), mw)
    for r in range(rows):
        t0, t1 = r / rows, (r + 1) / rows
        off = 0.5 if r % 2 else 0.0
        for c in range(cols + 1):
            u = (c + off) / cols
            if 0 < u < 1:
                pygame.draw.line(window, mortar,
                                 quad_pt(quad, u, t0), quad_pt(quad, u, t1), mw)


def draw_stone_top(window, diamond, base_raw, cam, seed):
    q = diamond
    lit = shade(base_raw, PZ)
    mortar = tone(lit, 0.55)
    pygame.draw.polygon(window, mortar, q)
    for r in range(2):
        for c in range(2):
            bn = tilt_normal(PZ, seed + r, c, 9, 0.4)
            tint = 0.92 + 0.14 * hash01(seed, r * 2 + c, 9)
            pygame.draw.polygon(window, tone(shade(base_raw, bn), tint),
                                [quad_pt(q, c / 2, r / 2), quad_pt(q, (c + 1) / 2, r / 2),
                                 quad_pt(q, (c + 1) / 2, (r + 1) / 2),
                                 quad_pt(q, c / 2, (r + 1) / 2)])
    pygame.draw.line(window, mortar, quad_pt(q, 0.5, 0), quad_pt(q, 0.5, 1), 1)
    pygame.draw.line(window, mortar, quad_pt(q, 0, 0.5), quad_pt(q, 1, 0.5), 1)
    cx = (q[0][0] + q[2][0]) / 2
    cy = (q[0][1] + q[2][1]) / 2
    for k in range(8):
        corner = q[k % 4]
        f = 0.15 + 0.6 * hash01(seed, k, 13)
        nn = tilt_normal(PZ, seed, k, 14, 0.5)
        speckle(window, cam, cx + (corner[0] - cx) * f,
                cy + (corner[1] - cy) * f,
                tone(shade(base_raw, nn), 0.8 if k % 2 else 1.15))


def draw_box_faces(window, cam, x, y, z, w, d, h, base, seed, stone, preset_idx, mat=None):
    p1, p2, p3, p4, p2b, p3b, p4b = box_corner_points(cam, x, y, z, w, d, h)
    h_px = h * TILE_Z * cam.zoom / PIXEL
    if stone:
        draw_stone_face(window, [p2, p3, p3b, p2b], base, RIGHT_N[cam.rot],
                        seed * 3 + 1, h_px, cam.zoom)
        draw_stone_face(window, [p4, p3, p3b, p4b], base, LEFT_N[cam.rot],
                        seed * 3 + 2, h_px, cam.zoom)
        draw_stone_top(window, [p1, p2, p3, p4], base, cam, seed * 3 + 3)
    else:
        rw = d if cam.rot % 2 == 0 else w
        lw = w if cam.rot % 2 == 0 else d
        draw_wall_face(window, [p2, p3, p3b, p2b], mat, base, RIGHT_N[cam.rot],
                       seed * 5 + 1, preset_idx, cam, rw, h, face_id=1)
        draw_wall_face(window, [p4, p3, p3b, p4b], mat, base, LEFT_N[cam.rot],
                       seed * 5 + 2, preset_idx, cam, lw, h, face_id=2)
        draw_top_face(window, cam, [p1, p2, p3, p4], mat, base, seed * 5 + 3,
                      w, d)


def draw_pyramid(window, cam, x, y, z, w, d, h, base, seed, stone, preset_idx,
                 mat=None):
    levels = 3
    for i in range(levels):
        # пропорциональный спад: и маленькие шалаши читаются как пирамида
        f = 1.0 - i * 0.36
        ww = max(0.14, w * f)
        dd = max(0.14, d * f)
        xi = x + (w - ww) / 2
        yi = y + (d - dd) / 2
        draw_box_faces(window, cam, xi, yi, z + h * i / levels, ww, dd,
                       h / levels, tone(base, 1.0 + i * 0.05),
                       seed + i * 977, stone, preset_idx, mat)


def draw_timber_face(window, q, base, n, wide, beams_only=False):
    """Фахверк: штукатурка + тёмные балки (стойки, обвязки, раскос)."""
    if not beams_only:
        pygame.draw.polygon(window, shade(base, n), q)
    fw = math.hypot(q[1][0] - q[0][0], q[1][1] - q[0][1])
    bl = nshade(BASE_COLORS["wood_dark"], "wood_dark",
                int(q[0][0] * 2.3), int(q[0][1] * 3.1), n, 0.5)
    if fw >= 48 and not beams_only:  # рельеф штукатурки из карты нормалей
        si = int(q[0][0] * 2.1 + q[0][1] * 3.7)
        flat = shade(base, n)
        for k, (uu0, uu1, tt0, tt1) in enumerate(
                ((0.08, 0.42, 0.15, 0.55), (0.55, 0.92, 0.45, 0.85))):
            pn = nshade(base, "plaster", si + k * 31, k * 17 + 3, n, 0.9)
            mix = tuple((pn[i] + flat[i]) // 2 for i in range(3))
            pygame.draw.polygon(window, mix,
                                [quad_pt(q, uu0, tt0), quad_pt(q, uu1, tt0),
                                 quad_pt(q, uu1, tt1), quad_pt(q, uu0, tt1)])
    if fw >= 30 and not beams_only:  # плетёнка: контрастная матовая стена
        flat = shade(base, n)
        si = int(q[0][0] * 2.1 + q[0][1] * 3.7)
        pygame.draw.polygon(window, tone(flat, 0.80),
                            [quad_pt(q, 0.10, 0.12), quad_pt(q, 0.90, 0.12),
                             quad_pt(q, 0.90, 0.88), quad_pt(q, 0.10, 0.88)])
        nlat = max(5, min(13, int(round(fw / 4.5))))
        for r in range(nlat):
            tt = 0.14 + 0.72 * (r + 0.5) / nlat
            f = 0.66 + 0.22 * hash01(si + r * 13, r * 7, 5)
            pygame.draw.line(window, tone(flat, f),
                             quad_pt(q, 0.10, tt), quad_pt(q, 0.90, tt), 1)
            tt2 = min(0.86, tt + 0.5 * 0.72 / nlat)
            pygame.draw.line(window, tone(flat, 1.02),
                             quad_pt(q, 0.10, tt2), quad_pt(q, 0.90, tt2), 1)
        nv = max(7, min(19, int(round(fw / 3.8))))
        for c in range(nv):
            uu = 0.12 + 0.76 * (c + 0.5) / nv
            f = 0.62 + 0.20 * hash01(si + c * 17, c * 11, 9)
            pygame.draw.line(window, tone(flat, f),
                             quad_pt(q, uu, 0.14), quad_pt(q, uu, 0.86), 1)
    if fw < 24:  # кроха (субпиксели x3): чистая штукатурка
        return
    if fw < 48:  # микро: чёткий контур 1px вместо заливок
        pygame.draw.line(window, bl, quad_pt(q, 0, 0), quad_pt(q, 0, 1), 1)
        pygame.draw.line(window, bl, quad_pt(q, 1, 0), quad_pt(q, 1, 1), 1)
        pygame.draw.line(window, bl, quad_pt(q, 0, 0.06), quad_pt(q, 1, 0.06),
                         1)
        pygame.draw.line(window, bl, quad_pt(q, 0, 0.94), quad_pt(q, 1, 0.94),
                         1)
        return
    bu = 0.07 if wide else 0.10
    for u0, u1 in ((0.0, bu), (1 - bu, 1.0)):
        pygame.draw.polygon(window, bl, [quad_pt(q, u0, 0), quad_pt(q, u1, 0),
                                        quad_pt(q, u1, 1), quad_pt(q, u0, 1)])
    for t0, t1 in ((0.0, 0.10), (0.90, 1.0)):
        pygame.draw.polygon(window, bl, [quad_pt(q, 0, t0), quad_pt(q, 1, t0),
                                        quad_pt(q, 1, t1), quad_pt(q, 0, t1)])
    elev_f = clamp(SUN[2] * 1.6, 0.25, 1.0)  # свет сверху, тень снизу балок
    pygame.draw.line(window, tone(bl, 1 + 0.18 * elev_f),
                     quad_pt(q, 0, 0.0), quad_pt(q, 1, 0.0), 1)
    pygame.draw.line(window, tone(bl, 1 - 0.22 * elev_f),
                     quad_pt(q, 0, 1.0), quad_pt(q, 1, 1.0), 1)
    if wide:
        for u0, u1 in ((0.31, 0.38), (0.62, 0.69)):
            pygame.draw.polygon(window, tone(bl, 0.95),
                                [quad_pt(q, u0, 0.1), quad_pt(q, u1, 0.1),
                                 quad_pt(q, u1, 0.9), quad_pt(q, u0, 0.9)])
        pygame.draw.line(window, tone(bl, 0.9),
                         quad_pt(q, 0.10, 0.88), quad_pt(q, 0.30, 0.12), 2)


def draw_tile_face(window, q, base, n):
    """Черепица: ряды с тенью и разбежкой вертикальных швов."""
    pygame.draw.polygon(window, shade(base, n), q)
    fw = math.hypot(q[1][0] - q[0][0], q[1][1] - q[0][1])
    if fw < 12:
        return
    lit = shade(base, n)
    facing = max(0.0, n[0] * SUN[0] + n[1] * SUN[1] + n[2] * SUN[2])
    sh_t = 0.60 - 0.16 * (1 - facing)  # тень глубже на теневой стороне
    rows, nt = 3, 6
    for r in range(rows):
        t0, t1 = r / rows, (r + 1) / rows
        rj = 0.96 + 0.08 * hash01(int(q[0][0] * 3.3) + r * 11,
                                      r * 7 + 1, 91)
        pygame.draw.line(window, tone(lit, sh_t * rj),
                         quad_pt(q, 0.02, t1 - 0.02),
                         quad_pt(q, 0.98, t1 - 0.02), 1)
        pygame.draw.line(window, tone(lit, (1.14 + 0.12 * facing) * rj),
                         quad_pt(q, 0.02, t0 + 0.03),
                         quad_pt(q, 0.98, t0 + 0.03), 1)
        off = 0.5 / nt if r % 2 else 0.0
        for k in range(nt + 1):
            u = (k + off) / nt
            if u <= 0.02 or u >= 0.98:
                continue
            pygame.draw.line(window, tone(lit, 0.72),
                             quad_pt(q, u, t0 + 0.06),
                             quad_pt(q, u, t1 - 0.04), 1)


def draw_gable(window, cam, x, y, z, w, d, h, base, seed, preset_idx,
               ends="timber"):
    """Щипцовая крыша: 3 уступа, скаты — черепица, торцы — фахверк/камень."""
    plaster = BASE_COLORS["plaster"]
    LV = 2 if h < 0.7 else 3
    step = (d / 2 - 0.2) / (LV - 1)
    h_px = (h / LV) * TILE_Z * cam.zoom / PIXEL
    top = None
    for i in range(LV):
        dd = d - 2 * i * step
        lvl = tone(base, 1.0 + i * 0.07)
        p1, p2, p3, p4, p2b, p3b, p4b = box_corner_points(
            cam, x, y + i * step, z + h * i / LV, w, dd, h / LV)
        def _hide_face(q, s2):
            # шкура: швы поперёк, жирные тёмные полосы (олений рисунок),
            # светлые пятна — узор крупный, читается на любом зуме
            pygame.draw.polygon(window, shade(lvl, n), q)
            for t in (0.26, 0.52, 0.78):
                pygame.draw.line(window, tone(lvl, 0.70),
                                 quad_pt(q, 0.05, t),
                                 quad_pt(q, 0.95, t), 1)
            lw = max(2, int(h_px * 0.2))
            for u0 in (0.16, 0.40, 0.62, 0.86):
                u = u0 + (hash01(s2, 11, 7) - 0.5) * 0.05
                pygame.draw.line(window, tone(lvl, 0.44),
                                 quad_pt(q, u, 0.08),
                                 quad_pt(q, u, 0.93), lw)
            r = max(2, int(h_px * 0.14))
            for u, t in ((0.28, 0.34), (0.52, 0.60), (0.78, 0.28),
                         (0.66, 0.78), (0.36, 0.72)):
                c = quad_pt(q, u, t)
                pygame.draw.circle(window, tone(lvl, 1.5),
                                   (int(c[0]), int(c[1])), r)
            for u, t in ((0.5, 0.4), (0.2, 0.55), (0.9, 0.6),
                         (0.45, 0.2)):
                c = quad_pt(q, u, t)
                pygame.draw.circle(window, tone(lvl, 1.3),
                                   (int(c[0]), int(c[1])),
                                   max(1, r // 2))

        for n, q in ((RIGHT_N[cam.rot], [p2, p3, p3b, p2b]),
                     (LEFT_N[cam.rot], [p4, p3, p3b, p4b])):
            if ends == "hide":
                _hide_face(q, seed + i * 131)
            elif n[0] != 0:
                if ends == "stone":
                    draw_stone_face(window, q, BASE_COLORS["gray"], n,
                                    seed + i * 977, h_px, cam.zoom)
                else:
                    draw_timber_face(window, q, tone(plaster, 0.92), n,
                                     True)
            else:
                draw_tile_face(window, q, lvl, n)
        pygame.draw.polygon(window, shade(lvl, PZ), [p1, p2, p3, p4])
        if ends == "hide":
            # шкуры на скатах: шов вдоль конька + светлые пятна —
            # каждый уступ выглядит как отдельная шкура
            bq = [p1, p2, p3, p4]
            for t in (0.3, 0.7):
                pygame.draw.line(window, tone(lvl, 0.66),
                                 quad_pt(bq, 0.06, t),
                                 quad_pt(bq, 0.94, t),
                                 1 if h_px < 8 else 2)
            for u, t in ((0.2, 0.5), (0.55, 0.38), (0.8, 0.62)):
                c = quad_pt(bq, u, t)
                pygame.draw.circle(window, tone(lvl, 1.45),
                                   (int(c[0]), int(c[1])),
                                   max(1, int(h_px * 0.1)))
        top = [p1, p2, p3, p4]
    if top is not None:  # конёк: светлый брус вдоль верха
        fw = math.hypot(top[1][0] - top[0][0], top[1][1] - top[0][1])
        if fw >= 6:
            pygame.draw.line(window, tone(shade(base, PZ), 1.35),
                             quad_pt(top, 0.04, 0.5),
                             quad_pt(top, 0.96, 0.5),
                             2 if fw >= 14 else 1)


def _draw_timber_eroded(window, cam, o):
    """Балки побитой стены: только по целым ячейкам, с разрывами."""
    g = o.get("_chipgrid")
    if g is None:
        return
    chips = o.get("chips", ())
    nx, ny, nz = g["nx"], g["ny"], g["nz"]
    cw, cd, ch = g["cw"], g["cd"], g["ch"]
    VR, VL = RIGHT_N[cam.rot], LEFT_N[cam.rot]

    def proj(x, y, z):
        xr, yr = cam.rotate_point(x, y)
        return cam.iso_project(xr, yr, z)

    for n in (VR, VL):
        beam = shade(BASE_COLORS["wood_dark"], n)
        if n[0] != 0:
            along, nn = "y", ny
            plane = o["x"] + o["w"] if n[0] == 1 else o["x"]
            fixed = nx - 1 if n[0] == 1 else 0
            wide = o["d"] > 1.1
        else:
            along, nn = "x", nx
            plane = o["y"] + o["d"] if n[1] == 1 else o["y"]
            fixed = ny - 1 if n[1] == 1 else 0
            wide = o["w"] > 1.1
        bu = 0.07 if wide else 0.10
        for j in range(nn):
            for k in range(nz):
                key = (fixed, j, k) if along == "y" else (j, fixed, k)
                if key in chips:
                    continue
                u, v = (j + 0.5) / nn, (k + 0.5) / nz
                is_beam = (u < bu or u > 1 - bu or v < 0.10 or v > 0.90)
                if wide and not is_beam:
                    is_beam = ((0.31 <= u <= 0.38 or 0.62 <= u <= 0.69)
                               and 0.10 <= v <= 0.90)
                if wide and not is_beam and 0.06 <= u <= 0.34:
                    vd = 0.12 + (0.88 - 0.12) * (u - 0.10) / 0.20
                    is_beam = abs(v - vd) < 0.07
                if not is_beam:
                    continue
                if along == "y":
                    y0, y1 = o["y"] + j * cd, o["y"] + (j + 1) * cd
                    z0, z1 = o["z"] + k * ch, o["z"] + (k + 1) * ch
                    q = [proj(plane, y0, z1), proj(plane, y1, z1),
                         proj(plane, y1, z0), proj(plane, y0, z0)]
                else:
                    x0, x1 = o["x"] + j * cw, o["x"] + (j + 1) * cw
                    z0, z1 = o["z"] + k * ch, o["z"] + (k + 1) * ch
                    q = [proj(x0, plane, z1), proj(x1, plane, z1),
                         proj(x1, plane, z0), proj(x0, plane, z0)]
                pygame.draw.polygon(window, beam, q)


def _draw_timber_dressing(window, cam, o, eroded):
    """Балки поверх стены; на битой — уцелевший каркас поверх дыр."""
    base = BASE_COLORS[o["color"]]
    p1, p2, p3, p4, p2b, p3b, p4b = box_corner_points(cam, o["x"], o["y"],
                                                     o["z"], o["w"], o["d"],
                                                     o["h"])
    rw = o["d"] if cam.rot % 2 == 0 else o["w"]
    lw = o["w"] if cam.rot % 2 == 0 else o["d"]
    draw_timber_face(window, [p2, p3, p3b, p2b], base, RIGHT_N[cam.rot],
                     rw > 1.1, eroded)
    draw_timber_face(window, [p4, p3, p3b, p4b], base, LEFT_N[cam.rot],
                     lw > 1.1, eroded)


def _glow_quad(window, q, color, alpha):
    xs = [p[0] for p in q]
    ys = [p[1] for p in q]
    x0, y0 = int(min(xs)) - 2, int(min(ys)) - 2
    w, h = int(max(xs)) - x0 + 4, int(max(ys)) - y0 + 4
    if w <= 0 or h <= 0:
        return
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, color + (alpha // 3,), s.get_rect())
    inner = s.get_rect().inflate(-4, -4)
    if inner.width > 0 and inner.height > 0:
        pygame.draw.rect(s, color + (alpha,), inner)
    window.blit(s, (x0, y0))


def _draw_face_detail(window, cam, o):
    """Дверь/окно/топка на грани: по ячейкам, сквозь сколы не рисуем."""
    d = o.get("detail")
    if not d:
        return
    n = d["n"]
    VR, VL = RIGHT_N[cam.rot], LEFT_N[cam.rot]
    if n not in (VR, VL):
        return
    g = o.get("_chipgrid") or object_chip_grid(o)
    chips = o.get("chips", ())
    nx, ny, nz = g["nx"], g["ny"], g["nz"]
    cw, cd, ch = g["cw"], g["cd"], g["ch"]
    kind = d["kind"]
    _rect = d.get("rect")
    if _rect is not None:
        u0, u1, v0, v1 = _rect
    elif kind == "door":
        u0, u1, v0, v1 = 0.20, 0.80, 0.0, 0.65
    elif kind == "window":
        u0, u1, v0, v1 = 0.15, 0.85, 0.38, 0.82
    elif kind == "band":
        u0, u1, v0, v1 = 0.04, 0.96, 0.14, 0.90
    elif kind == "panel":
        u0, u1, v0, v1 = 0.04, 0.97, 0.08, 0.97
    else:
        u0, u1, v0, v1 = 0.25, 0.75, 0.20, 0.60
    beam = shade(BASE_COLORS["wood_dark"], n)
    night = clamp((0.6 - LIGHT["amb"]) / 0.35, 0.0, 1.0)
    _hl = o.get("house")
    _lit = _hl is None or _hl not in LIGHTS_OFF
    _fire = _hl is not None and _hl in HOUSE_BURNING
    glass = (255, int(196 + 30 * night), int(120 + 40 * night))
    if not _lit:
        glass = (54, 60, 66)
    firec = (255, int(140 + 40 * night), int(50 + 30 * night))
    if n[0] != 0:
        along = "y"
        nn = ny
        plane = o["x"] + o["w"] if n[0] == 1 else o["x"]
        fixed = nx - 1 if n[0] == 1 else 0
    else:
        along = "x"
        nn = nx
        plane = o["y"] + o["d"] if n[1] == 1 else o["y"]
        fixed = ny - 1 if n[1] == 1 else 0
    du, dv = 1.0 / nn, 1.0 / nz
    vm = (v0 + v1) / 2
    shut = d.get("shut", False) and kind == "window"

    def proj(x, y, z):
        xr, yr = cam.rotate_point(x, y)
        return cam.iso_project(xr, yr, z)

    for j in range(nn):
        for k in range(nz):
            u, v = (j + 0.5) * du, (k + 0.5) * dv
            in_rect = (u0 <= u <= u1 and v0 <= v <= v1)
            is_shut = (shut and v0 <= v <= v1
                       and ((u < u0 and u >= u0 - 1.6 * du)
                            or (u > u1 and u <= u1 + 1.6 * du)))
            if not (in_rect or is_shut):
                continue
            key = (fixed, j, k) if along == "y" else (j, fixed, k)
            if key in chips:
                continue
            if along == "y":
                y0, y1 = o["y"] + j * cd, o["y"] + (j + 1) * cd
                z0, z1 = o["z"] + k * ch, o["z"] + (k + 1) * ch
                q = [proj(plane, y0, z1), proj(plane, y1, z1),
                     proj(plane, y1, z0), proj(plane, y0, z0)]
            else:
                x0, x1 = o["x"] + j * cw, o["x"] + (j + 1) * cw
                z0, z1 = o["z"] + k * ch, o["z"] + (k + 1) * ch
                q = [proj(x0, plane, z1), proj(x1, plane, z1),
                     proj(x1, plane, z0), proj(x0, plane, z0)]
            if is_shut:  # ставни: тёмные доски с пазом
                pygame.draw.polygon(window, beam, q)
                pygame.draw.line(window, tone(beam, 0.55),
                                 quad_pt(q, 0.5, 0.05),
                                 quad_pt(q, 0.5, 0.95), 1)
                continue
            _u_edge = kind != "firebox" and (u - du / 2 <= u0
                                                  or u + du / 2 >= u1)
            if d.get("frame", True) and (_u_edge or v - dv / 2 <= v0
                                         or v + dv / 2 >= v1):
                pygame.draw.polygon(window, beam, q)
                continue
            if kind == "door":
                pygame.draw.polygon(window, tone(beam, 0.55), q)
                for s in (0.36, 0.52, 0.68):
                    if j * du < s <= (j + 1) * du:
                        t = (s - j * du) / du
                        pygame.draw.line(window, tone(beam, 0.35),
                                         quad_pt(q, t, 0), quad_pt(q, t, 1), 1)
                if (j * du < 0.62 <= (j + 1) * du
                        and k * dv < 0.42 <= (k + 1) * dv):
                    kx, ky = quad_pt(q, (0.62 - j * du) / du,
                                     1 - (0.42 - k * dv) / dv)
                    pygame.draw.rect(window, (255, 220, 150),
                                     (int(kx), int(ky), 1, 1))
            elif kind in ("band", "panel"):  # стекло-лента / решётка панельки
                is_glass = (kind == "band"
                            or ((j % 3) in (1, 2) and (k % 3) == 1))
                if not is_glass:
                    continue
                lit_w = (night > 0.3 and _lit
                         and hash01(j * 7 + 3, k * 13 + (_hl or 0), 5)
                         < 0.55 + 0.2 * night)
                if lit_w:
                    pygame.draw.polygon(window, glass, q)
                    if night > 0.45:
                        _glow_quad(window, q, (255, 190, 110),
                                   int(70 * night))
                else:
                    col_w = (46, 56, 70) if night < 0.3 else (40, 48, 60)
                    pygame.draw.polygon(window, col_w, q)
                if _fire:
                    _glow_quad(window, q, (255, 145, 40),
                               int(120 + 60 * night))
            elif kind == "window":
                pygame.draw.polygon(window, glass, q)
                if night > 0.45 and _lit:  # ореол света ночью
                    _glow_quad(window, q, (255, 190, 110),
                               int(90 * night))
                if _fire:  # за окном бушует пожар
                    _glow_quad(window, q, (255, 145, 40),
                               int(120 + 60 * night))
                if j * du < 0.5 <= (j + 1) * du:
                    t = (0.5 - j * du) / du
                    pygame.draw.line(window, beam, quad_pt(q, t, 0),
                                     quad_pt(q, t, 1), 1)
                if k * dv < vm <= (k + 1) * dv:
                    t = 1 - (vm - k * dv) / dv
                    pygame.draw.line(window, beam, quad_pt(q, 0, t),
                                     quad_pt(q, 1, t), 1)
            else:
                pygame.draw.polygon(window, firec, q)
                if night > 0.45:
                    _glow_quad(window, q, (255, 150, 70),
                               int(90 * night))


def _rot_normal(nx, ny, rot):
    if rot == 0:
        return nx, ny
    if rot == 1:
        return -ny, nx
    if rot == 2:
        return -nx, -ny
    return ny, -nx


def draw_cylinder(window, cam, x, y, z, w, d, h, base, seed, preset_idx):
    cx, cy = cam.world_to_screen(x + w / 2, y + d / 2, z + h)
    rw = (w + d) / 2
    rx = (TILE_W / 2) * (rw / 2) * cam.zoom / PIXEL
    ry = (TILE_H / 2) * (rw / 2) * cam.zoom / PIXEL
    h_px = h * TILE_Z * cam.zoom / PIXEL
    n = 8
    top_pts, bot_pts = [], []
    for i in range(n):
        a = math.pi * 2 * i / n
        px = cx + rx * math.cos(a)
        py = cy + ry * math.sin(a)
        top_pts.append((px, py))
        bot_pts.append((px, py + h_px))

    for i in range(n):
        j = (i + 1) % n
        ai = math.pi * 2 * i / n
        aj = math.pi * 2 * j / n
        mid = (ai + aj) / 2
        if (math.sin(ai) + math.sin(aj)) / 2 > -0.05:
            wx, wy = _rot_normal(math.cos(mid), math.sin(mid), cam.rot)
            dd = max(0.0, wx * SUN[0] + wy * SUN[1])
            f = LIGHT["amb"] + LIGHT["dif"] * dd
            col = (clamp(int(base[0] * f), 0, 255),
                   clamp(int(base[1] * f), 0, 255),
                   clamp(int(base[2] * f), 0, 255))
            quad = [top_pts[i], top_pts[j], bot_pts[j], bot_pts[i]]
            pygame.draw.polygon(window, col, quad)
            face_texels(window, cam, quad, (wx, wy, 0.0), base,
                        seed + i * 31, preset_idx, math.pi * rw / 8, h)
    pygame.draw.polygon(window, shade(base, PZ), top_pts)
    tq = [top_pts[6], top_pts[0], top_pts[2], top_pts[4]]
    face_texels(window, cam, tq, PZ, base, seed + 777, preset_idx, rw, rw)


def draw_pixel(window, cam, p, ctx=None):
    if ctx is None:
        ctx = _proj_ctx(cam)
    px, py = _proj_pt(ctx, p["x"], p["y"], p["z"])
    zc = max(cam.zoom, 0.75)
    if p.get("kind") == "fib":
        ln = p["size"] * zc / PIXEL * p.get("fade", 1.0)
        ca, sa = math.cos(p["ang"]), math.sin(p["ang"])
        x1, y1 = px - ca * ln / 2, py - sa * ln / 2
        x2, y2 = px + ca * ln / 2, py + sa * ln / 2
        if -4 <= x1 < cam.win_w + 4 or -4 <= x2 < cam.win_w + 4:
            pygame.draw.line(window, p["color"], (x1, y1), (x2, y2), 1)
        return
    if p.get("kind") == "sh":
        fade = p.get("fade", 1.0)
        if p.get("face") is not None:
            (ax, ay, az), (bx, by, bz) = p["face"]
            ex = _proj_pt(ctx, p["x"] + ax, p["y"] + ay, p["z"] + az)
            ez = _proj_pt(ctx, p["x"] + bx, p["y"] + by, p["z"] + bz)
            ex = (ex[0] - px, ex[1] - py)
            ez = (ez[0] - px, ez[1] - py)
            ca, sa = math.cos(p["ang"]), math.sin(p["ang"])
            pts = []
            for su, sv in p["fverts"]:
                uu, vv = su * fade, sv * fade
                wx = ex[0] * uu + ez[0] * vv
                wy = ex[1] * uu + ez[1] * vv
                pts.append((px + wx * ca - wy * sa,
                            py + wx * sa + wy * ca))
            if any(-8 <= q[0] < cam.win_w + 8
                   and -8 <= q[1] < cam.win_h + 8 for q in pts):
                pygame.draw.polygon(window, p["color"], pts)
                if fade > 0.85:
                    pygame.draw.line(window, tone(p["color"], 1.35),
                                     pts[0], pts[1], 1)
            return
        sc = zc / PIXEL * fade
        ca, sa = math.cos(p["ang"]), math.sin(p["ang"])
        pts = [(px + (vx * ca - vy * sa) * sc,
                py + (vx * sa + vy * ca) * sc) for vx, vy in p["verts"]]
        if any(-8 <= q[0] < cam.win_w + 8 and -8 <= q[1] < cam.win_h + 8
               for q in pts):
            pygame.draw.polygon(window, p["color"], pts)
            if fade > 0.85 and len(pts) >= 2:
                pygame.draw.line(window, tone(p["color"], 1.35),
                                 pts[0], pts[1], 1)
        return
    s = max(1, int(round(p["size"] * zc / PIXEL * p.get("fade", 1.0))))
    ix, iy = int(px - s / 2), int(py - s / 2)
    if -4 <= ix < cam.win_w + 4 and -4 <= iy < cam.win_h + 4:
        pygame.draw.rect(window, p["color"], (ix, iy, s, s))
        if s >= 4:  # крупные куски: свет сверху, тень снизу
            r, g, b = p["color"]
            pygame.draw.rect(window, (min(255, r + 45), min(255, g + 45),
                                         min(255, b + 45)), (ix, iy, s, 1))
            pygame.draw.rect(window, (r * 3 // 5, g * 3 // 5, b * 3 // 5),
                             (ix, iy + s - 1, s, 1))


def _pit_edge(pts, C, dx, dy):
    """Ребро квада, наиболее развёрнутое к направлению (dx, dy)."""
    best, be = -1e9, (pts[0], pts[1])
    for i in range(4):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % 4]
        ex, ey = x2 - x1, y2 - y1
        L = math.hypot(ex, ey) or 1.0
        nx, ny = -ey / L, ex / L
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if (mx - C[0]) * nx + (my - C[1]) * ny < 0:
            nx, ny = -nx, -ny
        sc = nx * dx + ny * dy
        if sc > best:
            best, be = sc, ((x1, y1), (x2, y2))
    return be


def _draw_pit(window, q, base_lit, v, seed):
    """Выбоина-впадина: рваные края, устье, дно и стенки по свету."""
    C = (sum(p[0] for p in q) / 4, sum(p[1] for p in q) / 4)
    e0 = max(2.0, math.hypot(q[1][0] - q[0][0], q[1][1] - q[0][1]))
    e1 = max(2.0, math.hypot(q[3][0] - q[0][0], q[3][1] - q[0][1]))
    jq = []
    for k, (x, y) in enumerate(q):
        fr = 0.80 + 0.40 * hash01(seed, k * 2 + 1, 31)
        jx = (hash01(seed, k * 2 + 2, 47) - 0.5) * e0 * 0.22
        jy = (hash01(seed, k * 2 + 3, 53) - 0.5) * e1 * 0.22
        jq.append((C[0] + (x - C[0]) * fr + jx,
                   C[1] + (y - C[1]) * fr + jy))
    q = jq
    if hash01(seed, 7, 77) < 0.25:
        halo = [(C[0] + (x - C[0]) * 1.15, C[1] + (y - C[1]) * 1.15)
                for x, y in q]
        pygame.draw.polygon(window, tone(base_lit, 0.55), halo)
        in1 = [(C[0] + (x - C[0]) * 0.80, C[1] + (y - C[1]) * 0.80)
               for x, y in q]
        pygame.draw.polygon(window, tone(base_lit, 0.45), in1)
        return
    hs = 1.12 + 0.14 * hash01(seed, 9, 91)
    halo = [(C[0] + (x - C[0]) * hs, C[1] + (y - C[1]) * hs)
            for x, y in q]
    pygame.draw.polygon(window, tone(base_lit, 0.55), halo)
    ms = 0.76 + 0.12 * hash01(seed, 10, 92)
    in1 = [(C[0] + (x - C[0]) * ms, C[1] + (y - C[1]) * ms)
           for x, y in q]
    pygame.draw.polygon(window, tone(base_lit, v), in1)
    sunx, suny = SUN_SX, SUN_SY
    cell = max(2.0, math.hypot(q[1][0] - q[0][0], q[1][1] - q[0][1]))
    sh = min(3.0, cell * 0.15)
    Cb = (C[0] + sunx * sh, C[1] + suny * sh)
    bs = 0.44 + 0.16 * hash01(seed, 11, 93)
    bot = [(Cb[0] + (x - Cb[0]) * bs, Cb[1] + (y - Cb[1]) * bs)
           for x, y in q]
    pygame.draw.polygon(window, tone(base_lit, 0.07), bot)
    (ax, ay), (bx, by) = _pit_edge(q, C, -sunx, -suny)
    pygame.draw.polygon(window, tone(base_lit, 1.30),
                        [(ax, ay), (bx, by),
                         (C[0] + (bx - C[0]) * 0.5,
                          C[1] + (by - C[1]) * 0.5),
                         (C[0] + (ax - C[0]) * 0.5,
                          C[1] + (ay - C[1]) * 0.5)])
    (cx_, cy_), (dx_, dy_) = _pit_edge(q, C, sunx, suny)
    pygame.draw.polygon(window, tone(base_lit, 0.38),
                        [(cx_, cy_), (dx_, dy_),
                         (C[0] + (dx_ - C[0]) * 0.5,
                          C[1] + (dy_ - C[1]) * 0.5),
                         (C[0] + (cx_ - C[0]) * 0.5,
                          C[1] + (cy_ - C[1]) * 0.5)])
    pygame.draw.line(window, tone(base_lit, 1.45), (ax, ay), (bx, by), 1)


def draw_chip_notches(window, cam, o):
    """Выбоины как ВПАДИНЫ: устье с глубиной, дно и стенки на свету."""
    chips = o.get("chips")
    g = o.get("_chipgrid")
    if not chips or g is None:
        return
    base = BASE_COLORS[o["color"]]
    VR, VL = RIGHT_N[cam.rot], LEFT_N[cam.rot]
    nx, ny, nz = g["nx"], g["ny"], g["nz"]
    cw, cd, ch = g["cw"], g["cd"], g["ch"]
    # соль от координат: id() прыгал между прогонами, рендер терял повторяемость
    osalt = abs(int(o["x"] * 431 + o["y"] * 1021 + o["z"] * 67
                  + o["w"] * 131 + o["h"] * 53)) % 10007

    def proj(x, y, z):
        xr, yr = cam.rotate_point(x, y)
        return cam.iso_project(xr, yr, z)

    for key in chips:
        c = g["idx"].get(key)
        if c is None:
            continue
        ix, iy, iz = key
        cx, cy, cz = c[3], c[4], c[5]
        v = 0.18 + 0.06 * hash01(ix * 3 + 1, iy * 5 + iz, 9)
        if iz == nz - 1:  # верхняя грань
            x0, x1 = cx - cw / 2, cx + cw / 2
            y0, y1 = cy - cd / 2, cy + cd / 2
            z = o["z"] + o["h"]
            q = [proj(x0, y0, z), proj(x1, y0, z),
                 proj(x1, y1, z), proj(x0, y1, z)]
            _draw_pit(window, q, shade(base, PZ), v,
                      osalt * 100003 + ix * 131 + iy * 17 + iz * 13 + 1)
        sides = [((1, 0, 0), ix == nx - 1, o["x"] + o["w"], True),
                 ((-1, 0, 0), ix == 0, o["x"], True),
                 ((0, 1, 0), iy == ny - 1, o["y"] + o["d"], False),
                 ((0, -1, 0), iy == 0, o["y"], False)]
        for n, on_face, plane, along_y in sides:
            if not on_face or n not in (VR, VL):
                continue
            z0, z1 = cz - ch / 2, cz + ch / 2
            if along_y:
                y0, y1 = cy - cd / 2, cy + cd / 2
                q = [proj(plane, y0, z1), proj(plane, y1, z1),
                     proj(plane, y1, z0), proj(plane, y0, z0)]
            else:
                x0, x1 = cx - cw / 2, cx + cw / 2
                q = [proj(x0, plane, z1), proj(x1, plane, z1),
                     proj(x1, plane, z0), proj(x0, plane, z0)]
            salt = 2 if n[0] == 1 else (3 if n[0] == -1 else (5 if n[1] == 1 else 7))
            _draw_pit(window, q, shade(base, n), v,
                      osalt * 100003 + ix * 131 + iy * 17 + iz * 13 + salt)


_SPRITE_MODE = False  # True: рисуем объект на свой спрайт
OBJ_SPRITES = {}      # id(o) -> готовый спрайт объекта
# Бюджет пере-рендера спрайтов за кадр: смена запечённого света (течение
# суток) не вызывает единый тяжёлый кадр — устаревшие спрайты обновляются
# по чуть-чуть в течение ~полсекунды (старый и новый свет незаметно смешиваются).
_SPRITE_BUDGET = [48]


def _wood_cell_color(base, n, seed, inner, mat="wood_dark"):
    v = 0.90 + 0.20 * hash01(seed, 5, 6)
    if inner:
        v *= 0.78
        v *= 0.94 + 0.12 * hash01(seed, 12, 13)
    return tone(nshade(base, mat, seed, 9, n, 0.7), v)


def _wood_cell_detail(window, q, n, seed, inner, mat, z0, z1, o):
    gr = MAT_GRAIN.get(mat)
    end = gr is not None and (n == gr or (n[0] == -gr[0]
                                        and n[1] == -gr[1]
                                        and n[2] == -gr[2]))
    base = BASE_COLORS[o["color"]]
    lit = shade(base, n)
    if end:
        for k in range(3):
            u = 0.2 + 0.6 * hash01(seed, k, 21)
            t = 0.2 + 0.6 * hash01(seed, k, 22)
            x, y = quad_pt(q, u, t)
            pygame.draw.rect(window, tone(lit, 0.62),
                             (int(x), int(y), 1, 1))
    else:
        t = 0.25 + 0.5 * hash01(seed, 3, 23)
        wob = (hash01(seed, 4, 24) - 0.5) * 0.1
        if mat in PLANK_MATS:
            a, b = quad_pt(q, 0.06, t), quad_pt(q, 0.94, t + wob)
        else:
            a, b = quad_pt(q, t, 0.06), quad_pt(q, t + wob, 0.94)
        pygame.draw.line(window, tone(lit, 0.70), a, b, 1)
    if inner:
        for k in range(2):
            t = 0.2 + 0.6 * hash01(seed, k, 25)
            wob = (hash01(seed, k, 26) - 0.5) * 0.2
            pygame.draw.line(window, tone(lit, 1.25),
                             quad_pt(q, 0.1, t), quad_pt(q, 0.9, t + wob), 1)
    if mat in PLANK_MATS and n[2] == 0:
        for k in (1, 2, 3):
            zb = o["z"] + o["h"] * k / 4
            if z0 < zb < z1:
                t = (z1 - zb) / (z1 - z0)
                pygame.draw.line(window, tone(lit, 0.40),
                                 quad_pt(q, 0, t), quad_pt(q, 1, t), 1)


def _wood_face_finish(window, q, base, n, gr, mat, o):
    lit = shade(base, n)
    end = gr is not None and (n == gr or (n[0] == -gr[0]
                                        and n[1] == -gr[1]
                                        and n[2] == -gr[2]))
    if mat in PLANK_MATS and n[2] == 0:
        for b in range(4):
            t0, t1 = b / 4, (b + 1) / 4
            bq = [quad_pt(q, 0, t0), quad_pt(q, 1, t0),
                  quad_pt(q, 1, t1), quad_pt(q, 0, t1)]
            pygame.draw.polygon(window, tone(lit, 0.93 + 0.07 * (b % 2)), bq)
            mid = (t0 + t1) / 2
            wob = (hash01(b, 3, 77) - 0.5) * 0.05
            pygame.draw.line(window, tone(lit, 0.72),
                             quad_pt(q, 0.02, mid),
                             quad_pt(q, 0.98, mid + wob), 1)
        for k in (1, 2, 3):
            t = k / 4
            pygame.draw.line(window, tone(lit, 0.42),
                             quad_pt(q, 0, t), quad_pt(q, 1, t), 1)
        return
    if end:
        cx, cy = quad_pt(q, 0.5, 0.5)
        r = max(2.0, math.hypot(q[1][0] - q[0][0],
                                q[1][1] - q[0][1]) * 0.16)
        prev = None
        for a in range(11):
            ang = a / 10 * math.pi * 2
            pt = (cx + math.cos(ang) * r, cy + math.sin(ang) * r * 0.5)
            if prev is not None:
                pygame.draw.line(window, tone(lit, 0.65), prev, pt, 1)
            prev = pt
        for k in range(8):
            u = 0.15 + 0.7 * hash01(k, 5, 81)
            t = 0.15 + 0.7 * hash01(k, 6, 82)
            x, y = quad_pt(q, u, t)
            pygame.draw.rect(window, tone(lit, 0.60),
                             (int(x), int(y), 1, 1))
        return
    for i in range(7):
        t = (i + 0.5) / 7
        wob = (hash01(i, 9, 83) - 0.5) * 0.06
        tonev = 0.70 + 0.15 * hash01(i, 10, 84)
        pygame.draw.line(window, tone(lit, tonev),
                         quad_pt(q, t, 0.03), quad_pt(q, t + wob, 0.97), 1)
    kx, ky = quad_pt(q, 0.3 + 0.4 * hash01(3, 1, 85),
                     0.3 + 0.4 * hash01(3, 2, 86))
    pygame.draw.rect(window, tone(lit, 0.50),
                     (int(kx), int(ky), 2, 2))


def _draw_wood_dressing(window, cam, o, base):
    mat = o.get("mat", "concrete")
    gr = MAT_GRAIN.get(mat)
    p1, p2, p3, p4, p2b, p3b, p4b = box_corner_points(cam, o["x"], o["y"],
                                                     o["z"], o["w"], o["d"], o["h"])
    faces = [(RIGHT_N[cam.rot], [p2, p3, p3b, p2b]),
             (LEFT_N[cam.rot], [p4, p3, p3b, p4b]),
             (PZ, [p1, p2, p3, p4])]
    for n, q in faces:
        _wood_face_finish(window, q, base, n, gr, mat, o)


def _obj_idx(o):
    """Стабильный сид объекта (такой же, как в _render_object_sprite)."""
    try:
        _ci = _BASE_ORDER.index(o["color"])
    except ValueError:
        _ci = 0
    return int(o["x"] * 12.7 + o["y"] * 57.3 + o["z"] * 101.1 + o["w"] * 3.1
              + o["d"] * 7.7 + o["h"] * 13.9 + _ci * 37.3) % 100000


def _rock_poly(o):
    """Рваные контуры валуна (низ и верх) — одна формула для рендера
    и для тени, чтобы тень всегда совпадала с силуэтом."""
    x, y, z, w, d, h = o["x"], o["y"], o["z"], o["w"], o["d"], o["h"]
    cx = x + w / 2
    cy = y + d / 2
    idx = _obj_idx(o)
    nv = 5 + idx % 3
    foot = []
    for i in range(nv):
        a = math.pi * 2 * i / nv + (hash01(i, idx, 31) - 0.5) * 0.9
        rx = (w / 2) * (0.72 + 0.28 * hash01(i, idx, 32))
        ry = (d / 2) * (0.72 + 0.28 * hash01(i, idx, 33))
        foot.append((cx + math.cos(a) * rx, cy + math.sin(a) * ry))
    tx = cx + (hash01(idx, 1, 33) - 0.5) * w * 0.25
    ty = cy + (hash01(idx, 2, 33) - 0.5) * d * 0.25
    tz = z + h * (0.85 + 0.3 * hash01(idx, 3, 33))
    top = [(tx + (fx - cx) * 0.45, ty + (fy - cy) * 0.45)
           for fx, fy in foot]
    return foot, top, tz


def draw_rock(window, cam, o, base, idx):
    """Валун: рваный многогранник с вкраплениями; форма — из сида idx."""
    x, y, z, w, d, h = o["x"], o["y"], o["z"], o["w"], o["d"], o["h"]
    foot, top, tz = _rock_poly(o)
    nv = len(foot)
    pf = [cam.world_to_screen(fx, fy, z) for fx, fy in foot]
    pt = [cam.world_to_screen(txx, tyy, tz) for txx, tyy in top]
    for i in range(nv):
        i2 = (i + 1) % nv
        a = math.pi * 2 * (i + 0.5) / nv
        wx, wy = _rot_normal(math.cos(a), math.sin(a), cam.rot)
        lit = shade(base, (wx, wy, 0.15))
        quad = [pf[i], pf[i2], pt[i2], pt[i]]
        pygame.draw.polygon(window, lit, quad)
        if hash01(i, idx, 34) < 0.7:
            mx = int((quad[0][0] + quad[2][0]) / 2)
            my = int((quad[0][1] + quad[2][1]) / 2)
            pygame.draw.rect(window, tone(lit, 0.8 + 0.4 * hash01(i, idx, 35)),
                             (mx - SP(1), my - SP(1), SP(2), SP(2)))
    pygame.draw.polygon(window, shade(base, PZ), pt)
    draw_chip_notches(window, cam, o)


def _draw_eroded_box(window, cam, o, base, preset_idx):
    """Блок с дырой в месте удара: целые воксели, полые — выбиты."""
    g = o["_chipgrid"]
    chips = o.get("chips", ())
    idx = g["idx"]
    VR, VL = RIGHT_N[cam.rot], LEFT_N[cam.rot]
    stone = o["color"] in STONE_MATS
    vis = (PZ, VR, VL)
    mat = o.get("mat", "concrete")
    _gb = o.get("shape") == "gable"
    _gbp = BASE_COLORS["gray"] if o.get("ends") == "stone" else BASE_COLORS[
        "plaster"]
    _gbe = o.get("ends") == "stone"
    nx = g["nx"]

    def proj(x, y, z):
        xr, yr = cam.rotate_point(x, y)
        return cam.iso_project(xr, yr, z)

    def solid(key):
        return key in idx and key not in chips

    cells = []
    for c in g["cells"]:
        key = (c[0], c[1], c[2])
        if key in chips:
            continue
        xr, yr = cam.rotate_point(c[3], c[4])
        cells.append((xr + yr, -c[5], c))
    cells.sort(key=lambda t: (t[0], t[1]))
    for _, _, c in cells:
        ix, iy, iz, cx, cy, cz, cw, cd, ch = c
        x0, x1 = cx - cw / 2, cx + cw / 2
        y0, y1 = cy - cd / 2, cy + cd / 2
        z0, z1 = cz - ch / 2, cz + ch / 2
        faces = [
            (PZ, (ix, iy, iz + 1),
             [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]),
            ((1, 0, 0), (ix + 1, iy, iz),
             [(x1, y0, z1), (x1, y1, z1), (x1, y1, z0), (x1, y0, z0)]),
            ((-1, 0, 0), (ix - 1, iy, iz),
             [(x0, y1, z1), (x0, y0, z1), (x0, y0, z0), (x0, y1, z0)]),
            ((0, 1, 0), (ix, iy + 1, iz),
             [(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)]),
            ((0, -1, 0), (ix, iy - 1, iz),
             [(x1, y0, z1), (x0, y0, z1), (x0, y0, z0), (x1, y0, z0)]),
        ]
        for n, nb, corners in faces:
            if n not in vis:
                continue
            if solid(nb):
                continue
            q = [proj(*pt) for pt in corners]
            inner = nb in chips
            seed = ix * 131 + iy * 17 + iz * 13 + n[0] * 3 + n[1] * 5
            _end = _gb and (ix == 0 or ix == nx - 1)
            bbase = _gbp if _end else base
            if stone or (_end and _gbe):
                if hash01(seed, 6, 7) < 0.30:
                    col = tone(shade(bbase, n), 0.52)
                else:
                    v = 0.90 + 0.18 * hash01(seed, 7, 8)
                    if inner:
                        v *= 0.48
                    col = tone(nshade(bbase, mat, seed, 3, n, 0.7), v)
            elif mat in WOOD_MATS:
                col = _wood_cell_color(bbase, n, seed, inner, mat)
                if mat in PLANK_MATS:
                    band = int((cz - o["z"]) / o["h"] * 4)
                    col = tone(col, 0.94 + 0.06 * (band % 2))
            else:
                v = 0.88 + 0.24 * hash01(seed, 5, 6)
                if inner:
                    v *= 0.48
                col = tone(nshade(bbase, mat, seed, 3, n, 0.7), v)
            pygame.draw.polygon(window, col, q)
            if mat in WOOD_MATS:
                _wood_cell_detail(window, q, n, seed, inner, mat,
                                  z0, z1, o)


_SHADOW_ARR = None  # Surface теней; без дорогой полной numpy-копии


def _occ_rects(cam, objects):
    """Спрайты фигур: прямоугольники + ключ живописи (раз на кадр)."""
    rects = []
    for o2 in objects:
        if o2.get("shape") == "tree":
            continue
        e = OBJ_SPRITES.get(id(o2))
        if e is None:
            continue
        ratio = cam.zoom / max(1e-6, e.get("zoom", cam.zoom))
        dx = e["minx"] * ratio + cam.win_w / 2 + cam.x + cam.shx
        dy = e["miny"] * ratio + cam.win_h / 2 + cam.y + cam.shy
        sw2 = e["surf"].get_width() * ratio
        sh2 = e["surf"].get_height() * ratio
        qx0, qy0, qwr, qdr = cam.rotated_footprint(o2["x"], o2["y"],
                                                   o2["w"], o2["d"])
        rects.append((dx + 3, dy + 3, dx + sw2 - 3, dy + sh2 - 3,
                      qx0 + qwr + qy0 + qdr))
    return rects


def _fir_occluded2(lx, ly, tkey, rects):
    for x0, y0, x1, y1, k in rects:
        if x0 <= lx < x1 and y0 <= ly < y1 and k > tkey + 0.01:
            return True
    return False


def _fir_shadowed(cam, lx, ly):
    """Ёлка в тени постройки? Точечная проба готового слоя теней."""
    shadow = _SHADOW_ARR
    if shadow is None:
        return False
    offx, offy = _STATIC_OFF
    scale = _STATIC_SCALE
    ix = int((lx - offx) / scale)
    iy = int((ly - offy) / scale)
    sw, sh = shadow.get_size()
    if 0 <= ix < sw and 0 <= iy < sh:
        return shadow.get_at((ix, iy)).a > 40
    return False



def _mixc(a, b, k):
    return (int(a[0] + (b[0] - a[0]) * k),
            int(a[1] + (b[1] - a[1]) * k),
            int(a[2] + (b[2] - a[2]) * k))


def _fir_tones(o, fade, shadowed=False):
    base = BASE_COLORS[o["color"]]
    main = tone(shade(base, PZ), 1.0)
    side = tone(shade(base, NY), 0.82)
    lite = tone(shade(base, PZ), 1.22)
    dark = tone(shade(base, NY), 0.55)
    trunk_c = tone(shade(BASE_COLORS["wood_dark"], NY), 1.0)
    if fade < 1.0:
        gcol = tone(shade(GRASS, PZ), 0.9)
        k = 1.0 - fade
        main = _mixc(main, gcol, k)
        side = _mixc(side, gcol, k)
        lite = _mixc(lite, gcol, k)
        dark = _mixc(dark, gcol, k)
        trunk_c = _mixc(trunk_c, gcol, k)
    if shadowed:
        main = tone(main, 0.55)
        side = tone(side, 0.55)
        lite = tone(lite, 0.55)
        dark = tone(dark, 0.55)
        trunk_c = tone(trunk_c, 0.55)
    return main, side, lite, dark, trunk_c


def _draw_stump(window, o, sx, sy, S, shadowed=False):
    """Пенёк: короткий ствол с рваным светлым срезом."""
    trunk_c = tone(shade(BASE_COLORS["wood_dark"], NY), 1.0)
    lite = tone(shade(BASE_COLORS["wood_light"], PZ), 1.0)
    dark = tone(shade(BASE_COLORS["wood_dark"], NY), 0.55)
    if shadowed:
        trunk_c = tone(trunk_c, 0.55)
        lite = tone(lite, 0.55)
        dark = tone(dark, 0.55)
    if o.get("char"):
        trunk_c, lite, dark = (56, 47, 40), (74, 62, 52), (24, 21, 19)
    h = 2 + (int(o["x"] * 7 + o["y"] * 13) % 2)
    wdt = 2 if S >= 10 else 1
    bx = int(round(sx))
    by = int(round(sy))
    pygame.draw.ellipse(window, tone(shade(GRASS, PZ), 0.55),
                        (bx - 2, by - 1, 5, 2))
    pygame.draw.rect(window, trunk_c, (bx - wdt // 2, by - h, wdt, h))
    pygame.draw.rect(window, lite, (bx - wdt // 2, by - h, wdt, 1))
    pygame.draw.rect(window, dark, (bx - wdt // 2, by - 1, wdt, 1))



def _fir_row(r, Hc, T, maxW):
    """Ряд хвои: (ширина, вид) — 0 макушка, 1 ступень, 2 обычная."""
    if r == 0:
        return 1, 0
    tier = min(T - 1, int(r * T / Hc))
    prow = (r * T / Hc) - tier
    wfrac = (tier + 0.30 + 0.70 * prow) / T
    w = max(1, int(round(maxW * (0.16 + 0.84 * wfrac))))
    prev_tier = min(T - 1, int((r - 1) * T / Hc))
    if tier != prev_tier and tier > 0:
        return max(1, w - max(1, maxW // 6)), 1
    return w, 2


_FIR_SPR = {}
_FIR_WM = [1, 2, 3, 4, 3, 4, 5, 6, 5, 6, 7, 8, 9, 11, 13]  # ширины рядов хвои
_FIR_ZE = [0.0]  # текущий ze для hop-смещения


def _fir_sprite(cname, S, lean_ix=0.0, fade=1.0, shadowed=False, roots=False):
    """Кэшированная ёлка master 15x18: крупные пиксели при любом зуме."""
    fq = int(fade * 10 + 0.5)
    # грубый ключ света (1/8 суток): тон ёлок стабилен и не прыгает
    lkey = int(DAYT * 8) % 8
    key = (cname, int(round(S)), int(lean_ix * 2), fq, shadowed, roots, lkey)
    spr = _FIR_SPR.get(key)
    if spr is not None:
        return spr
    if len(_FIR_SPR) > 16384:
        _FIR_SPR.clear()
    o = dict(color=cname)
    main_, side, lite, dark, trunk_c = _fir_tones(o, fq / 10.0, shadowed)
    MW, MH = 15, 18
    m = pygame.Surface((MW, MH), pygame.SRCALPHA)
    for r, w in enumerate(_FIR_WM):
        sh = int(round(lean_ix * ((MH - 1 - r) / (MH - 1)) ** 1.5))
        x0 = (MW - w) // 2 + sh
        for j in range(w):
            if j == 0:
                c = lite
            elif j == w - 1:
                c = dark
            elif r % 5 == 4 or r == 14:
                c = side
            else:
                c = main_
            if 0 <= x0 + j < MW:
                m.set_at((x0 + j, r), c)
    for r in (15, 16, 17):  # ствол
        for j in (6, 7, 8):
            m.set_at((j, r), trunk_c)
    if roots:
        root_c = tone(shade(DIRT_COLOR, PZ), 0.9)
        if fq < 10:
            root_c = _mixc(root_c, tone(shade(GRASS, PZ), 0.9),
                           1.0 - fq / 10.0)
        for j in (4, 5, 9, 10):
            m.set_at((j, 17), root_c)
    th = max(4, int(round(S)))
    tw = max(3, int(round(th * MW / MH)))
    spr = pygame.transform.scale(m, (tw, th))
    _FIR_SPR[key] = spr
    return spr


def _render_fir_sprite(f, S, shadowed):
    """Ёлка-флаер в том же пиксель-стиле + корни для кувырка."""
    return _fir_sprite(f["color"], S, 0.0, f["fade"], shadowed, roots=True)


def _draw_flyer(window, cam, f, sx, sy, S):
    """Вырванная с корнем ёлка в полёте: тень на земле + кувырок."""
    ze = _FIR_ZE[0]
    gz = ground_height_at(f["x"], f["y"]) or 0.0
    sh_c = tone(shade(GRASS, PZ), 0.5)
    gx, gy = _proj_pt(_proj_ctx(cam), f["x"] + 0.5, f["y"] + 0.5, gz)
    hgt = max(0.0, f["z"] - gz)
    shr = max(3, int(S * 0.45 * (1.0 - 0.05 * hgt)))
    pygame.draw.ellipse(window, sh_c,
                        (int(gx - shr / 2), int(gy - shr / 6), shr,
                         max(2, shr // 4)))
    spr = _render_fir_sprite(f, S, _fir_shadowed(cam, sx, sy))
    spin = f.get("spin", 0.0)
    if abs(spin) > 0.01:
        spr = pygame.transform.rotozoom(spr, -math.degrees(spin), 1.0)
    if f.get("fade", 1.0) < 1.0:
        spr = spr.copy()
        spr.set_alpha(int(255 * f["fade"]))
    window.blit(spr, (int(sx - spr.get_width() / 2),
                      int(sy - spr.get_height() / 2)))



def _draw_mini_fir(window, o, sx, sy, S, wdx, wdy, mag01,
                   blox=0.0, bloy=0.0, fade=1.0, shadowed=False,
                   hop=0.0):
    """Ёлка из крупных пикселей: силуэт одинаков на любом зуме."""
    sh_c = tone(shade(GRASS, PZ), 0.55)
    bx = int(round(sx))
    base_y = int(round(sy))
    ze_ = (TILE_Z and _FIR_ZE[0]) or 0.0
    hop_k = max(0.0, min(1.4, hop))
    shw = max(4, int(S * 0.5 * (1.0 - 0.14 * hop_k)))  # тень под ёлкой
    pygame.draw.ellipse(window, sh_c,
                        (bx - shw // 2 + 1, base_y - 1,
                         shw, max(2, S // 7)))
    shake = o.get("shake", 0.0)
    if shake > 0.001:  # тяжёлая дрожь после удара (медленная, широкая)
        _wph = ANIM_T * 1.7 + o["phase"]
        _wA = shake * S * 0.15
        lean_x = (blox + wdx * _wA * math.sin(_wph)
                  + (-wdy) * 0.35 * _wA * math.sin(_wph * 1.31 + 1.0))
    else:
        lean_x = blox
    tw = max(3, int(round(S * 15 / 18)))
    # мягкое наклонение: вдали деревья почти прямые и стабильные,
    # сильный наклон — только вблизи при сильном ветре
    lean_ix = max(-4, min(4, int(round(lean_x * 4.5 / max(3.0, tw)))))
    spr = _fir_sprite(o["color"], S, lean_ix, fade, shadowed)
    hoppx = int(hop_k * TILE_Z * ze_)
    window.blit(spr, (bx - spr.get_width() // 2,
                      base_y - spr.get_height() + 2 - hoppx))


def _draw_fir_at(window, cam, o, preset_idx, ctx):
    """Одна ёлка в общей сортировке мира: люди и дома за ней
    рисуются раньше — объёмная иерархия работает корректно."""
    ze = ctx[3]
    sx, sy = _proj_pt(ctx, o["x"] + 0.5, o["y"] + 0.5, o["z"])
    S = max(12, int(round(1.65 * o.get("sz", 1.0) * TILE_Z * ze)))
    if (sx < -3 * S or sy < -S or sx > cam.win_w + 3 * S
            or sy > cam.win_h + S):
        return  # за кадром — culling
    shadowed = _fir_shadowed(cam, sx, sy)
    if o.get("dead"):
        if o["dead"] == "stump":
            _draw_stump(window, o, sx, sy, S, shadowed)
        return
    wrx, wry = cam.rotate_point(WIND.get("wx", 0.0), WIND.get("wy", 0.0))
    lx = (wrx - wry) * (TILE_W / 2) * ze
    ly = (wrx + wry) * (TILE_H / 2) * ze
    wl = math.hypot(lx, ly)
    wdx = lx / wl if wl > 1e-6 else 0.0
    wdy = ly / wl if wl > 1e-6 else 1.0
    mag01 = clamp(wl / 18.0, 0.0, 1.0)
    _FIR_ZE[0] = ze
    ox, oy = cam.rotate_point(o.get("lx", 0.0) + o.get("_spx", 0.0),
                              o.get("ly", 0.0) + o.get("_spy", 0.0))
    blox = (ox - oy) * (TILE_W / 2) * ze  # экранный сдвиг верхушки
    _draw_mini_fir(window, o, sx, sy, S, wdx, wdy, mag01,
                   blox=blox, fade=1.0, shadowed=shadowed,
                   hop=o.get("hop", 0.0))


def draw_fir_overlay(window, cam, objects, w, h):
    """Вырванные с корнем ёлки в полёте — поверх мира (они в воздухе)."""
    ctx = _proj_ctx(cam)
    ze = ctx[3]
    for f in FLYERS:
        sx, sy = _proj_pt(ctx, f["x"] + 0.5, f["y"] + 0.5, f["z"])
        S = max(12, int(round(1.65 * f.get("sz", 1.0) * TILE_Z * ze)))
        if (sx < -3 * S or sy < -3 * S or sx > cam.win_w + 3 * S
                or sy > cam.win_h + 3 * S):
            continue
        _draw_flyer(window, cam, f, sx, sy, S)


_PATH_CACHE = {"key": None, "surf": None}


def _draw_village_paths(window, cam, wear):
    """Вытоптанные тропинки: пятна грунта там, где чаще всего ходили."""
    if not wear:
        return
    key = ((cam.win_w, cam.win_h), round(cam.zoom, 3), cam.rot,
           round(cam.x + cam.shx, 1), round(cam.y + cam.shy, 1),
           0 if VIL is None else VIL.get("wear_ver", 0))
    if _PATH_CACHE["key"] == key:
        window.blit(_PATH_CACHE["surf"], (0, 0))
        return
    ctx = _proj_ctx(cam)
    lay = pygame.Surface((cam.win_w, cam.win_h), pygame.SRCALPHA)
    cr, cg, cb = 148, 120, 79
    drawn = 0
    for (tx, ty), wv in wear.items():
        if wv < 1.1 or drawn > 600:
            continue
        pts = []
        ok = True
        for dx, dy in ((0, 0), (1, 0), (1, 1), (0, 1)):
            gz = ground_height_at(tx + dx + 0.5, ty + dy + 0.5)
            if gz is None:
                ok = False
                break
            pts.append(_proj_pt(ctx, tx + dx + 0.5, ty + dy + 0.5, gz))
        if not ok:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if (max(xs) < 0 or min(xs) > cam.win_w
                or max(ys) < 0 or min(ys) > cam.win_h):
            continue
        a = int(min(170, (wv - 1.0) * 22 + 24))
        c0 = (pts[0][0] + pts[2][0]) / 2
        c1 = (pts[0][1] + pts[2][1]) / 2

        def _sq(t):
            return [(c0 + (p[0] - c0) * t, c1 + (p[1] - c1) * t)
                    for p in pts]
        pygame.draw.polygon(lay, (cr, cg, cb, max(30, a - 60)), _sq(0.94))
        pygame.draw.polygon(lay, (cr - 18, cg - 18, cb - 18, a), _sq(0.62))
        drawn += 1
    if drawn:
        _PATH_CACHE["key"], _PATH_CACHE["surf"] = key, lay
        window.blit(lay, (0, 0))


def _render_object_sprite(cam, o, preset_idx):
    global _SPRITE_MODE
    base = BASE_COLORS[o["color"]]
    if o.get("burn"):
        base = _mixc(base, (40, 34, 30),
                     0.75 * min(1.0, o["burn"] * 1.15))  # обугливание
    stone = o["color"] in STONE_MATS
    try:
        _ci = _BASE_ORDER.index(o["color"])
    except ValueError:
        _ci = 0
    # стабильный сид текстур (id() прыгал от запуска к запуску)
    idx = int(o["x"] * 12.7 + o["y"] * 57.3 + o["z"] * 101.1 + o["w"] * 3.1
              + o["d"] * 7.7 + o["h"] * 13.9 + _ci * 37.3) % 100000
    sx, sy, ssx, ssy = cam.x, cam.y, cam.shx, cam.shy
    win_w, win_h = cam.win_w, cam.win_h
    cam.x = cam.y = cam.shx = cam.shy = 0.0
    # Храним оффсет спрайта от начала проекции, а не от центра
    # текущего Surface. Так один спрайт годится и для холста, и для экрана.
    cam.update_win_size(0, 0)
    x, y, z, w, d, h = o["x"], o["y"], o["z"], o["w"], o["d"], o["h"]
    pts = [cam.world_to_screen(px, py, pz)
           for px in (x, x + w) for py in (y, y + d)
           for pz in (z, z + h)]
    pad = 4
    minx = int(min(p[0] for p in pts)) - pad
    miny = int(min(p[1] for p in pts)) - pad
    maxx = int(max(p[0] for p in pts)) + pad + 1
    maxy = int(max(p[1] for p in pts)) + pad + 1
    cam.x, cam.y = -minx, -miny
    surf = pygame.Surface((max(1, maxx - minx), max(1, maxy - miny)),
                          pygame.SRCALPHA)
    _SPRITE_MODE = True
    try:
        if o["shape"] == "box" and o.get("chips"):
            _draw_eroded_box(surf, cam, o, base, preset_idx)
        elif o["shape"] == "box":
            draw_box_faces(surf, cam, x, y, z, w, d, h, base, idx,
                           stone, preset_idx, o.get("mat", "concrete"))
            if o.get("mat", "concrete") in WOOD_MATS:
                _draw_wood_dressing(surf, cam, o, base)
        elif o["shape"] == "gable" and o.get("chips"):
            _draw_eroded_box(surf, cam, o, base, preset_idx)
        elif o["shape"] == "gable":
            draw_gable(surf, cam, x, y, z, w, d, h, base, idx,
                       preset_idx, o.get("ends", "timber"))
        elif o["shape"] == "pyramid":
            draw_pyramid(surf, cam, x, y, z, w, d, h, base, idx,
                         stone, preset_idx)
        elif o["shape"] == "cylinder":
            draw_cylinder(surf, cam, x, y, z, w, d, h, base, idx,
                          preset_idx)
        elif o["shape"] == "rock":
            draw_rock(surf, cam, o, base, idx)
        if o.get("frame") and o["shape"] == "box":
            if o.get("chips"):
                _draw_timber_eroded(surf, cam, o)
            else:
                _draw_timber_dressing(surf, cam, o, False)
        if o.get("detail") and o["shape"] in ("box", "gable"):
            _draw_face_detail(surf, cam, o)
        if not (o["shape"] in ("box", "gable") and o.get("chips")):
            draw_chip_notches(surf, cam, o)
    finally:
        _SPRITE_MODE = False
        cam.x, cam.y, cam.shx, cam.shy = sx, sy, ssx, ssy
        cam.update_win_size(win_w, win_h)
    return surf, minx, miny


def _blit_object(window, cam, o, preset_idx, ctx=None):
    x, y, z, w, d, h = o["x"], o["y"], o["z"], o["w"], o["d"], o["h"]
    if ctx is None:
        ctx = _proj_ctx(cam)
    x0, y0, x1, y1 = _box_bbox(ctx, x, y, z, w, d, h)
    if (x1 < -6 or x0 > cam.win_w + 6
            or y1 < -6 or y0 > cam.win_h + 6):
        return  # мимо камеры — даже не рендерим
    # ключ БЕЗ версии мира: взрыв перерисует только задетые спрайты
    # Zoom не инвалидирует дорогую векторную отрисовку: готовый
    # пиксельный спрайт масштабируется дешёвым nearest-neighbour.
    key = (preset_idx, cam.rot, o.get("over", 0),
           len(o.get("chips") or ()), round(o["x"], 3),
           round(o["y"], 3), round(o["z"], 3), round(o["w"], 3),
           round(o["d"], 3), round(o["h"], 3), o.get("color"),
           o.get("shape"), o.get("mat", "concrete"))
    e = OBJ_SPRITES.get(id(o))
    if e is None:
        surf, minx, miny = _render_object_sprite(cam, o, preset_idx)
        e = dict(key=key, surf=surf, minx=minx, miny=miny,
                 zoom=cam.zoom, scaled=None)
        OBJ_SPRITES[id(o)] = e
    elif e["key"] != key and _SPRITE_BUDGET[0] > 0:
        # устарел (сменился свет/повреждение): обновляем в рамках бюджета
        _SPRITE_BUDGET[0] -= 1
        surf, minx, miny = _render_object_sprite(cam, o, preset_idx)
        e = dict(key=key, surf=surf, minx=minx, miny=miny,
                 zoom=cam.zoom, scaled=None)
        OBJ_SPRITES[id(o)] = e
    ratio = cam.zoom / max(1e-6, e.get("zoom", cam.zoom))
    spr = e["surf"]
    if abs(ratio - 1.0) > 1e-5:
        scale_key = round(cam.zoom, 3)
        scaled = e.get("scaled")
        if scaled is None or scaled[0] != scale_key:
            sw0, sh0 = spr.get_size()
            spr = pygame.transform.scale(
                spr, (max(1, int(round(sw0 * ratio))),
                      max(1, int(round(sh0 * ratio)))))
            e["scaled"] = (scale_key, spr)
        else:
            spr = scaled[1]
    dx = e["minx"] * ratio + cam.win_w / 2 + cam.x + cam.shx
    dy = e["miny"] * ratio + cam.win_h / 2 + cam.y + cam.shy
    sw, sh = spr.get_size()
    if dx + sw < 0 or dy + sh < 0 or dx > cam.win_w or dy > cam.win_h:
        return
    window.blit(spr, (int(dx), int(dy)))


def prune_object_sprites(objects):
    alive = {id(o) for o in objects}
    for k in [k for k in OBJ_SPRITES if k not in alive]:
        del OBJ_SPRITES[k]


def _collect_render_items(cam, objects, pixels):
    """Отсечь и отсортировать видимые элементы один раз.

    Отдельная функция нужна фоновой сборке: она рисует уже правильно
    отсортированный список маленькими порциями в разных кадрах.
    """
    ctx = _proj_ctx(cam)
    rot = ctx[0]
    _w0, _h0 = cam.win_w, cam.win_h
    items = []
    for o in objects:
        x, y, z, w, d = o["x"], o["y"], o["z"], o["w"], o["d"]
        _pxc, _pyc = _proj_pt(ctx, x + w / 2, y + d / 2, z)
        if (_pxc < -90 or _pxc > _w0 + 90 or _pyc < -220
                or _pyc > _h0 + 90):
            continue  # мимо камеры — без сортировки и рендера
        # ключ сортировки — в мировых координатах; footprint при поворотах
        # кратно 90° считается напрямую (без rotate_point по 4 углам)
        # ёлка — по дальнему углу своей плитки (человек за ёлкой
        # рисуется раньше и правильно скрывается)
        _sm = False if o.get("shape") == "tree" else o.get("sort_min")
        if rot == 0:
            _k = x + y if _sm else x + w + y + d
        elif rot == 1:
            _k = ctx[2] - y - d + x if _sm else ctx[2] - y + x + w
        elif rot == 2:
            _k = (ctx[1] - x - w) + (ctx[2] - y - d) if _sm \
                else (ctx[1] - x) + (ctx[2] - y)
        else:
            _k = y + ctx[1] - x - w if _sm else y + d + ctx[1] - x
        items.append((_k, z, 0, o))
    for p in pixels:
        rx, ry = cam.rotate_point(p["x"], p["y"])
        items.append((rx + ry, p["z"], 1, p))
    items.sort(key=lambda t: (t[0], t[1], t[2]))
    return items


def _draw_render_items(window, cam, items, preset_idx):
    ctx = _proj_ctx(cam)
    for _, _, kind, payload in items:
        if kind == 0:
            if payload.get("shape") == "tree":
                _draw_fir_at(window, cam, payload, preset_idx, ctx)
            else:
                _blit_object(window, cam, payload, preset_idx, ctx)
        else:
            draw_pixel(window, cam, payload, ctx)


def draw_objects_and_pixels(window, cam, objects, pixels, preset_idx):
    prune_object_sprites(objects)
    _draw_render_items(window, cam,
                       _collect_render_items(cam, objects, pixels), preset_idx)


# ---------------------------------------------------------------------------
# Тени
# ---------------------------------------------------------------------------
def object_corners_world(o):
    if o["shape"] == "cylinder":
        cx, cy = o["x"] + o["w"] / 2, o["y"] + o["d"] / 2
        pts = []
        for i in range(8):
            a = math.pi * 2 * i / 8
            pts.append((cx + (o["w"] / 2) * math.cos(a),
                        cy + (o["d"] / 2) * math.sin(a)))
        return pts
    x, y, w, d = o["x"], o["y"], o["w"], o["d"]
    return [(x, y), (x + w, y), (x + w, y + d), (x, y + d)]


def draw_shadows(layer, cam, objects):
    # Быстрый путь: инлайн-проекция _proj_pt (без вызовов методов камеры)
    ctx = _proj_ctx(cam)
    _w0, _h0 = cam.win_w, cam.win_h
    sdX, sdY = SHADOW_DX, SHADOW_DY
    rgba = SHADOW_RGBA

    def _pt(wx, wy):
        # тень лежит НА рельефе, а не на плоскости z=0
        gz = ground_height_at(wx, wy)
        if gz is None:
            gz = 0.0
        return _proj_pt(ctx, wx, wy, gz)

    for o in objects:
        shape = o.get("shape")
        if shape == "tree":
            _pxc, _pyc = _proj_pt(ctx, o["x"] + 0.5, o["y"] + 0.5, o["z"])
        else:
            _pxc, _pyc = _proj_pt(ctx, o["x"] + o["w"] * 0.5,
                                  o["y"] + o["d"] * 0.5, o["z"])
        if (_pxc < -140 or _pxc > _w0 + 140 or _pyc < -140
                or _pyc > _h0 + 140):
            continue
        pts = []
        if shape == "tree":
            # вытянутая тень: диск у основания + верх кроны вдоль солнца
            cx, cy = o["x"] + 0.5, o["y"] + 0.5
            sz = o.get("sz", 1.0)
            # верх кроны ≈ 1.65*sz (такой же, как высота спрайта ёлки)
            zb, zt = o["z"], o["z"] + (0.25 if o.get("dead") else 1.65 * sz)
            r = 0.30 * sz
            rr = r
            for i in range(6):
                a = math.pi * 2 * i / 6
                wx = cx + math.cos(a) * rr
                wy = cy + math.sin(a) * rr
                pts.append(_pt(wx + sdX * zb, wy + sdY * zb))
            for i in range(6):
                a = math.pi * 2 * i / 6 + 0.5
                wx = cx + math.cos(a) * rr * 0.55
                wy = cy + math.sin(a) * rr * 0.55
                pts.append(_pt(wx + sdX * (zb + zt) * 0.5,
                               wy + sdY * (zb + zt) * 0.5))
            for i in range(4):
                a = math.pi * 2 * i / 4 + 0.4
                wx = cx + math.cos(a) * r * 0.45
                wy = cy + math.sin(a) * r * 0.45
                pts.append(_pt(wx + sdX * zt, wy + sdY * zt))
        elif shape == "rock":
            # тень точно по рваному силуэту (тот же контур, что и в рендере)
            foot, top, tz = _rock_poly(o)
            z = o["z"]
            for wx, wy in foot:
                pts.append(_pt(wx + sdX * z, wy + sdY * z))
            for wx, wy in top:
                pts.append(_pt(wx + sdX * tz, wy + sdY * tz))
        else:
            z0, z1 = o["z"], o["z"] + o["h"]
            for wx, wy in object_corners_world(o):
                pts.append(_pt(wx + sdX * z0, wy + sdY * z0))
                pts.append(_pt(wx + sdX * z1, wy + sdY * z1))
        hull = convex_hull(pts)
        if len(hull) >= 3:
            pygame.draw.polygon(layer, rgba, hull)
            if shape in ("tree", "rock"):
                pygame.draw.polygon(layer, rgba, hull)


def draw_hover(window, cam, objects, mpos, blast_mode, power):
    wx, wy = cam.screen_to_world(mpos[0], mpos[1], 0)
    for _ in range(3):
        _gz = ground_height_at(wx, wy)
        if _gz is None:
            break
        wx, wy = cam.screen_to_world(mpos[0], mpos[1], _gz)
    tx, ty = math.floor(wx), math.floor(wy)
    if not (0 <= tx < GRID_W and 0 <= ty < GRID_D):
        return None
    gz0 = ground_height_at(tx + 0.5, ty + 0.5) or 0.0
    p1 = cam.world_to_screen(tx, ty, gz0)
    p2 = cam.world_to_screen(tx + 1, ty, gz0)
    p3 = cam.world_to_screen(tx + 1, ty + 1, gz0)
    p4 = cam.world_to_screen(tx, ty + 1, gz0)
    col = (255, 120, 90) if blast_mode else HIGHLIGHT
    pygame.draw.polygon(window, col, [p1, p2, p3, p4], 1)
    if not blast_mode:
        z = stack_height_at(objects, tx, ty)
        rx0, ry0, wr, dr = cam.rotated_footprint(tx, ty, 1, 1)
        rx1, ry1 = rx0 + wr, ry0 + dr
        c1 = cam.iso_project(rx0, ry0, z + 1)
        c2 = cam.iso_project(rx1, ry0, z + 1)
        c3 = cam.iso_project(rx1, ry1, z + 1)
        c4 = cam.iso_project(rx0, ry1, z + 1)
        c3b = cam.iso_project(rx1, ry1, z)
        pygame.draw.polygon(window, HIGHLIGHT, [c1, c2, c3, c4], 1)
        pygame.draw.line(window, HIGHLIGHT, c3, c3b, 1)
    else:
        cx = (p1[0] + p3[0]) / 2
        cy = (p1[1] + p3[1]) / 2
        r = (1.5 * power + 0.4) * (TILE_W / 2) * cam.zoom / PIXEL
        pygame.draw.ellipse(window, col, (cx - r, cy - r / 2, r * 2, r), 1)
    return (tx, ty)


# ---------------------------------------------------------------------------
# Воксельные разрушения (Teardown в 2D) + пиксели + физика
# ---------------------------------------------------------------------------
FLASHES, RINGS, SMOKES, SPARKS, FLAMES, DUST = [], [], [], [], [], []
HOUSE_HIT = {i: False for i in range(1, 41)}  # дом под атакой: дым гаснет
LIGHTS_OFF = set()         # дом разрушен на 30%+ — свет в его окнах гаснет
HOUSE_BURNING = set()      # в доме что-то горит (окна светятся огнём)
HOUSE_TOTAL, HOUSE_DMG = {}, {}   # урон дома в вокселях
LIGHTS_OFF_FRACTION = 0.30
VENTS = {}  # дом -> объект-труба
CHIMNEY_T = {i: 0.0 for i in range(1, 41)}
fx_rng = random.Random(9182)  # свой ГСЧ дымка, боевой rng не трогаем
TRAUMA = 0.0
BOOM_SOUND = None
# --- ветер: направление/сила плывут к целям, цели меняются порывами ---
WIND = dict(ang=0.8, str=0.35, t_ang=0.8, t_str=0.35, next=10.0, t=0.0,
            kick=0.0, wx=1.0, wy=0.6, mag=0.4)
ANIM_T = 0.0      # часы анимации (качание деревьев)
CLOUD_OFF = 0.0   # накопленный снос облаков ветром
wind_rng = random.Random(20260917)
_PHYS_TICK = 0    # счётчик шагов физики (кэш опоры мусора)
_FIRE_ACC = 0.0   # пожару достаточно 30 логических шагов/с
_PHYS_AUDIT = {"version": -1, "cursor": 0}
STATIC_VER = 0    # версия статики: стройка/снос/сброс (взрыв — инкремент)
_CRATER_TILES = set()  # клетки воронок для инкрементной перекраски
_STATIC_REQ = dict(full=False)  # обрушение требует полный перестрой
_SUP_IDX = {}  # id(списка) -> (WORLD_VERSION, список, grid)
FLYERS = []  # вырванные ёлки в полёте  # индекс опоры
WORLD_VERSION = 0  # растёт при любом изменении мира (взрыв/стройка/сброс)


def bump_world():
    global WORLD_VERSION, STATIC_VER
    WORLD_VERSION += 1
    STATIC_VER += 1


_TREECNT = {"key": None, "n": 0}


def tree_count(objects):
    """Счётчик ёлок для HUD: пересчёт только при смене состава мира
    (взрыв/стройка/сброс/удаление фигуры меняют len и/или версию)."""
    key = (id(objects), WORLD_VERSION, len(objects))
    if _TREECNT["key"] != key:
        _TREECNT["n"] = sum(1 for o in objects if o.get("shape") == "tree")
        _TREECNT["key"] = key
    return _TREECNT["n"]


def init_audio():
    global BOOM_SOUND
    try:
        pygame.mixer.pre_init(22050, -16, 2, 512)
    except Exception:
        pass
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        sr, dur = 22050, 0.7
        n = int(sr * dur)
        t = np.arange(n) / sr
        noise = np.random.RandomState(3).randn(n)
        thump = np.sin(2 * np.pi * 48 * t) * np.exp(-3.5 * t)
        crack = np.random.RandomState(4).randn(n) * np.exp(-22 * t) * 0.7
        s = noise * np.exp(-5.5 * t) * 0.55 + thump * 0.75 + crack
        s = s / max(1e-6, np.abs(s).max()) * 0.9
        stereo = np.stack([s, s], axis=1)
        BOOM_SOUND = pygame.sndarray.make_sound((stereo * 32767).astype(np.int16))
        BOOM_SOUND.set_volume(0.5)
    except Exception as e:
        print(f"[звук] выключен ({e})")
        BOOM_SOUND = None




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
    col = pixel_color_for(o, 0.0, seed, seed * 7 + 3, fixed_n=face_n)
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
        col = pixel_color_for(o, 0.0, int(gx * 91) + i * 17,
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
        col = pixel_color_for(o, 0.0, rng.randrange(9999),
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
            GH[ty][tx] = max(MIN_H, GH[ty][tx] - 0.2)
            DENTED.add((tx, ty))
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
        _house_damage_add(objects, o["house"], len(o["chips"]) - _n0)
    chip_blob(pixels, o, chosen, bx, by, bz, power, R)
    _lim = 0.55 if o.get("house") else 0.65
    if len(o["chips"]) > _lim * len(g["cells"]):
        if o.get("house"):
            _house_damage_add(objects, o["house"],
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


_PICK_IDX = dict(ver=-2, objs=None, grid={})


def _pick_index(objects):
    if _PICK_IDX["ver"] != WORLD_VERSION or _PICK_IDX["objs"] is not objects:
        grid = {}
        for o in objects:
            x0 = math.floor(o["x"])
            x1 = math.floor(o["x"] + o["w"] - 1e-6)
            y0 = math.floor(o["y"])
            y1 = math.floor(o["y"] + o["d"] - 1e-6)
            for ix in range(x0, x1 + 1):
                for iy in range(y0, y1 + 1):
                    grid.setdefault((ix, iy), []).append(o)
        _PICK_IDX["ver"], _PICK_IDX["objs"], _PICK_IDX["grid"] = (
            WORLD_VERSION, objects, grid)
    return _PICK_IDX["grid"]


def pick_blast_point(cam, objects, sx, sy):
    """3D-выбор точки: луч сверху вниз — блок раньше земли за ним."""
    grid = _pick_index(objects)
    z = 12.0
    while z >= 0:
        wx, wy = cam.screen_to_world(sx, sy, z)
        for o in grid.get((math.floor(wx), math.floor(wy)), ()):
            if (o["x"] - 0.03 <= wx < o["x"] + o["w"] + 0.03
                    and o["y"] - 0.03 <= wy < o["y"] + o["d"] + 0.03
                    and o["z"] - 0.03 <= z <= o["z"] + o["h"] + 0.03):
                return (wx, wy, z, o)
        z -= 0.1
    wx, wy = cam.screen_to_world(sx, sy, 0.0)
    for _ in range(3):
        _gz = ground_height_at(wx, wy)
        if _gz is None:
            break
        wx, wy = cam.screen_to_world(sx, sy, _gz)
    return (wx, wy, 0.0, None)


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
                GH[y][x] += lip * 0.5
                GH[y][x + 1] += lip * 0.5
                GH[y + 1][x] += lip * 0.5
                GH[y + 1][x + 1] += lip * 0.5
                _RIMTILES.add((x, y))
            dig = max(BASE_H[y][x] - GH[y][x],
                      BASE_H[y][x + 1] - GH[y][x + 1],
                      BASE_H[y + 1][x] - GH[y + 1][x],
                      BASE_H[y + 1][x + 1] - GH[y + 1][x + 1])
            if dig > 0.03:
                DENTED.add((x, y))
                _RIMTILES.discard((x, y))


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


def _burn_fx_spawn(o):
    """Пламя и тёмный дым с поверхности горящего объекта."""
    k = fx_rng
    if o.get("shape") == "tree":
        x = o["x"] + 0.5 + k.uniform(-0.2, 0.2)
        y = o["y"] + 0.5 + k.uniform(-0.2, 0.2)
        z = o["z"] + k.uniform(0.2, 0.85)
    else:
        x = o["x"] + k.random() * o["w"]
        y = o["y"] + k.random() * o["d"]
        z = o["z"] + o["h"] * k.uniform(0.25, 1.0)
    sm = max(0.13, min(0.3, o.get("h", 0.35) * 0.26))
    if len(FLAMES) < 110:
        FLAMES.append(dict(x=x, y=y, z=z, t=0.0,
                           life=0.30 + k.random() * 0.22,
                           s=sm * k.uniform(0.7, 1.5),
                           ph=k.random() * 6.283))
    if len(SMOKES) < 120 and k.random() < 0.75:
        SMOKES.append(dict(x=x, y=y, z=z + 0.18, t=0.0,
                           life=2.4 + k.random() * 1.0,
                           r=0.24 + k.random() * 0.16,
                           c=(58, 53, 50), a=150, rise=1.6))


def _fire_neighbor(objects, o):
    """Ближайший горючий сосед в 1.15 клетки — туда перекинется огонь."""
    ox = o["x"] + o.get("w", 1) / 2
    oy = o["y"] + o.get("d", 1) / 2
    best, bd = None, 1.15
    for n in objects:
        if n is o or n.get("burn") or n.get("dead"):
            continue
        if n.get("shape") != "tree" and n.get("mat") not in BURN_MATS:
            continue
        nx = clamp(ox, n["x"], n["x"] + n.get("w", 1))
        ny = clamp(oy, n["y"], n["y"] + n.get("d", 1))
        d = math.hypot(nx - ox, ny - oy)
        if d < bd:
            bd, best = d, n
    return best


def _burn_out(objects, pixels, o):
    """Сгорело дотла: зола, угар и исчезновение объекта."""
    o.pop("burn", None)
    o.pop("fx_t", None)
    o.pop("sp_t", None)
    if o.get("shape") == "tree":
        o["dead"] = "stump"   # обгоревший пенёк остаётся
        o["char"] = True
        return
    g = object_chip_grid(o)
    cells = g["cells"]
    for c in rng.sample(cells, min(len(cells), 24)):
        add_pixel(pixels, c[3], c[4], c[5] + 0.02,
                  rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4),
                  rng.uniform(0.4, 1.4), 3, (40, 36, 32))
    if len(SMOKES) < 120:
        SMOKES.append(dict(x=o["x"] + o["w"] / 2, y=o["y"] + o["d"] / 2,
                           z=o["z"] + 0.3, t=0.0, life=1.8, r=0.4,
                           c=(52, 47, 44), a=150, rise=1.5))
    hid = o.get("house")
    if hid:
        _house_damage_add(objects, hid, len(cells))
    if o in objects:
        objects.remove(o)
    bump_world()  # опоры для висящих сверху блоков пересчитаются


def _fire_tick(objects, pixels, dt):
    """Таймеры поджига, прогресс горения, распространение пожара."""
    burning = HOUSE_BURNING
    burning.clear()
    for o in list(objects):
        ig = o.get("ig")
        if ig is not None:
            if ig <= dt:
                o.pop("ig", None)
                o["burn"] = 1e-4
                o["fx_t"] = o["sp_t"] = 0.0
                if o.get("house"):
                    HOUSE_HIT[o["house"]] = True  # пожар: дымка из трубы нет
            else:
                o["ig"] = ig - dt
                continue
        if o.get("burn") is None:
            continue
        if o.get("house"):
            burning.add(o["house"])
        o["burn"] += dt * (0.10 if o.get("shape") == "tree"
                             else _BURN_RATE.get(o.get("mat"), 0.055))
        o["fx_t"] = o.get("fx_t", 0.0) + dt
        while o["fx_t"] >= 0.075:
            o["fx_t"] -= 0.075
            _burn_fx_spawn(o)
        o["sp_t"] = o.get("sp_t", 0.0) + dt
        if o["sp_t"] > 0.55 and o["burn"] > 0.3:
            o["sp_t"] = 0.0
            if rng.random() < 0.6:
                n = _fire_neighbor(objects, o)
                if n is not None and n.get("ig") is None:
                    n["ig"] = rng.uniform(0.6, 1.4)
        if o["burn"] >= 1.0:
            _burn_out(objects, pixels, o)


def explode(cam, objects, pixels, wx, wy, power=1.0, bz=0.3):
    global TRAUMA, STATIC_VER
    # Сколы меняют картинку, но не геометрию опор. Раньше каждый
    # взрыв зря инвалидировал физический индекс всех ~1900 объектов.
    STATIC_VER += 1
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
                GH[cy][cx] = max(MIN_H, GH[cy][cx] - depth * (1 - d / R))
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
    if VIL is not None:
        for h in VIL["workers"]:
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
                        VIL["blood"].append(dict(
                            x=h["x"] + math.cos(_a) * _rr,
                            y=h["y"] + math.sin(_a) * _rr,
                            r=0.05 + rng.random() * 0.07 * fall, t=0.0,
                            big=False))
                    # смертельный удар: человек разрушается СРАЗУ —
                    # обрывки летят от центра взрыва вместе с кровью
                    if h["dead_mark"]:
                        _vil_human_die(VIL, h)
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
    TRAUMA = min(1.0, TRAUMA + 0.55 * power)
    WIND["kick"] = min(1.5, WIND["kick"] + 0.45 * power)  # порыв
    if BOOM_SOUND is not None:
        try:
            BOOM_SOUND.play()
        except Exception:
            pass


def step_physics(objects, pixels, dt):
    global _PHYS_TICK, _FIRE_ACC
    _PHYS_TICK += 1
    alive_ids = {id(o) for o in objects} if VENTS else ()
    for h, vent in VENTS.items():  # дымок из целых труб
        if HOUSE_HIT.get(h):
            continue
        if id(vent) not in alive_ids:
            continue
        CHIMNEY_T[h] = CHIMNEY_T.get(h, 0.0) + dt
        if CHIMNEY_T[h] >= 0.25 and len(SMOKES) < 100:
            CHIMNEY_T[h] = 0.0
            SMOKES.append(dict(
                x=vent["x"] + vent["w"] / 2 + fx_rng.uniform(-0.03, 0.03),
                y=vent["y"] + vent["d"] / 2 + fx_rng.uniform(-0.03, 0.03),
                z=vent["z"] + vent["h"] + 0.05, t=0.0,
                life=2.2 + fx_rng.random() * 0.8,
                r=0.18 + fx_rng.random() * 0.12))
    _FIRE_ACC += dt
    if _FIRE_ACC >= 1.0 / 30.0:
        _fire_tick(objects, pixels, _FIRE_ACC)
        _FIRE_ACC = 0.0
    wx, wy = WIND["wx"], WIND["wy"]
    crowded = len(pixels) > 800
    solids = _solids_of(objects)
    # Опоры неподвижных тел могут измениться только после bump_world().
    # После этого проверяем их по 128 за кадр, а не весь мир за один кадр.
    if solids:
        _n = len(solids)
        if _PHYS_AUDIT["version"] != WORLD_VERSION:
            _PHYS_AUDIT["version"] = WORLD_VERSION
            _PHYS_AUDIT["cursor"] = 0
        _end = min(_n, _PHYS_AUDIT["cursor"] + 128)
        for _i in range(_PHYS_AUDIT["cursor"], _end):
            _o = solids[_i]
            _pv = _o.get("park_v")
            if _pv is None or _pv == WORLD_VERSION:
                continue
            if _o.get("burn") or \
                    _o["z"] - support_height_obj(solids, _o) > 0.055:
                _o["park_v"] = None
            else:
                _o["park_v"] = WORLD_VERSION
        _PHYS_AUDIT["cursor"] = _end
    # Деревьев больше всего. Каждое обновляется в 1/4 кадров, но с
    # увеличенным dt: физика сохраняет скорость, а CPU не обходит весь лес.
    dt4 = dt * 4.0
    for o in _trees_of(objects):
        if (_PHYS_TICK + int(o.get("phase", 0.0) * 1000)) % 4:
            continue
        if o.get("shake", 0.0) > 0.0:
            o["shake"] = max(0.0, o["shake"] - dt4 * 0.9)
        if o.get("hop", 0.0) > 0.0 or o.get("hopv", 0.0) != 0.0:
            _hv = o.get("hopv", 0.0) - 13.0 * dt4
            _h = o.get("hop", 0.0) + _hv * dt4
            if _h < 0.0:
                _h = 0.0
                _hv = -_hv * 0.28 if _hv < -0.6 else 0.0
            o["hop"], o["hopv"] = _h, _hv
        if not o.get("dead"):
            o["lvx"] += (-20.0 * o["lx"] - 3.8 * o["lvx"]) * dt4
            o["lvy"] += (-20.0 * o["ly"] - 3.8 * o["lvy"]) * dt4
            o["lx"] = clamp(o["lx"] + o["lvx"] * dt4, -1.3, 1.3)
            o["ly"] = clamp(o["ly"] + o["lvy"] * dt4, -1.3, 1.3)
            _k1 = 1.0 - math.exp(-dt4 / o.get("sw_tau", 2.5))
            o["_swx"] = o.get("_swx", 0.0) + (wx - o.get("_swx", 0.0)) * _k1
            o["_swy"] = o.get("_swy", 0.0) + (wy - o.get("_swy", 0.0)) * _k1
            _svx = o.get("_svx", 0.0) + ((o["_swx"] * 0.14
                                          - o.get("_spx", 0.0)) * 3.0
                                         - o.get("_svx", 0.0) * 1.1) * dt4
            _svy = o.get("_svy", 0.0) + ((o["_swy"] * 0.14
                                          - o.get("_spy", 0.0)) * 3.0
                                         - o.get("_svy", 0.0) * 1.1) * dt4
            o["_svx"], o["_svy"] = _svx, _svy
            o["_spx"] = o.get("_spx", 0.0) + _svx * dt4
            o["_spy"] = o.get("_spy", 0.0) + _svy * dt4
    for o in solids:
        if o.get("park_v") is not None:
            continue  # упакован; надзор выше распакует при потере опоры
        sup = support_height_obj(solids, o)
        airborne = o["z"] > sup + 0.002 or abs(o["vz"]) > 1e-6
        if airborne:
            if not o.get("tmb"):  # обрушившийся кусок валится под углом
                o["tmb"] = True
                o["vx"] += rng.uniform(-0.35, 0.35)
                o["vy"] += rng.uniform(-0.35, 0.35)
            _SUP_IDX.clear()  # летящий блок: индекс протух
            o["vz"] -= GRAVITY * dt
            o["z"] += o["vz"] * dt
            o["vx"] *= max(0.0, 1 - 0.15 * dt)
            o["vy"] *= max(0.0, 1 - 0.15 * dt)
            if o["z"] <= sup:
                o["z"] = sup
                if o["vz"] < -5:
                    _landing_dust(o, sup)
                o["vz"] = -o["vz"] * 0.25 if o["vz"] < -3 else 0.0
                o["vx"] *= 0.6
                o["vy"] *= 0.6
        else:
            o["vx"] *= max(0.0, 1 - 6 * dt)
            o["vy"] *= max(0.0, 1 - 6 * dt)
            if abs(o["vx"]) < 0.05:
                o["vx"] = 0.0
            if abs(o["vy"]) < 0.05:
                o["vy"] = 0.0
            o["park_v"] = WORLD_VERSION  # упакован до смены мира
        o["x"] += o["vx"] * dt
        o["y"] += o["vy"] * dt
    for p in pixels:
        if p["rest"]:
            p["t"] += dt * (3.0 if crowded else 1.0)
            left = p.get("life", 9.0) - p["t"]
            p["fade"] = clamp(left / 1.2, 0.0, 1.0)
            continue
        if p.get("kind") in ("sh", "fib"):
            p["ang"] += p["spin"] * dt
        last_sup = p.get("sup")
        if (last_sup is None or _PHYS_TICK - p.get("supt", -99) >= 2
                or p["z"] - last_sup < 1.0):
            last_sup = support_height_point(objects, p["x"], p["y"], p["z"])
            p["sup"], p["supt"] = last_sup, _PHYS_TICK
        sup = last_sup
        p["vz"] -= GRAVITY * dt
        # ветер: лёгкая мелочь плывёт по ветру, тяжёлая почти нет
        wk = 0.55 if p.get("kind") == "fib" else (
            0.22 if p.get("kind") == "px" and p["size"] <= 3 else 0.06)
        p["vx"] += (wx - p["vx"]) * min(1.0, wk * dt)
        p["vy"] += (wy - p["vy"]) * min(1.0, wk * dt)
        drag = max(0.0, 1 - 0.7 * dt)  # воздушные: лёгкое сопротивление
        p["vx"] *= drag
        p["vy"] *= drag
        p["x"] += p["vx"] * dt
        p["y"] += p["vy"] * dt
        p["z"] += p["vz"] * dt
        if p["size"] >= 5 and p["vz"] < -4.0 and not p["rest"]:
            p["dust_t"] = p.get("dust_t", 0.0) + dt
            if p["dust_t"] >= 0.09 and len(DUST) < 240:
                p["dust_t"] = 0.0
                DUST.append(dict(x=p["x"], y=p["y"], z=p["z"], t=0.0,
                                 life=0.35, r=0.12, c=(125, 114, 96), a=55))
        if p["z"] <= sup:
            p["z"] = sup
            if (p["size"] >= 4 and len(DUST) < 240
                    and fx_rng.random() < 0.4):
                DUST.append(dict(x=p["x"], y=p["y"], z=sup + 0.08, t=0.0,
                                 life=0.45, r=0.14 + p["size"] * 0.03,
                                 c=(118, 106, 88), a=70))
            if abs(p["vz"]) > 1.2:
                p["vz"] = -p["vz"] * 0.35
                p["vx"] *= 0.6
                p["vy"] *= 0.6
            else:
                p["vz"] = 0.0
                p["vx"] *= max(0.0, 1 - 5 * dt)
                p["vy"] *= max(0.0, 1 - 5 * dt)
                if math.hypot(p["vx"], p["vy"]) < 0.4:
                    p["vx"] = p["vy"] = 0.0
                    p["spin"] = 0.0
                    p["rest"] = True
    pixels[:] = [p for p in pixels
                 if p["z"] > -6 and p.get("fade", 1.0) > 0.0]
    for f in FLYERS:
        if f["rest"]:
            f["t"] += dt
            f["fade"] = clamp(min(1.0, (7.5 - f["t"]) / 1.5), 0.0, 1.0)
            if f.get("et", 1.0) < 0.25:
                f["et"] = min(0.25, f["et"] + dt)
                k = f["et"] / 0.25
                k = k * k * (3 - 2 * k)
                f["spin"] = f["a0"] + (f["a1"] - f["a0"]) * k
            continue
        f["vz"] -= GRAVITY * 0.55 * dt
        dr = max(0.0, 1 - 0.4 * dt)
        f["vx"] *= dr
        f["vy"] *= dr
        f["vx"] += (wx - f["vx"]) * min(1.0, 0.8 * dt)
        f["vy"] += (wy - f["vy"]) * min(1.0, 0.8 * dt)
        f["x"] += f["vx"] * dt
        f["y"] += f["vy"] * dt
        f["z"] += f["vz"] * dt
        f["phase"] += f["spin_v"] * dt
        f["spin"] += f["spin_v"] * dt
        if f["z"] < -6:
            f["rest"], f["t"] = True, 99.0
            continue
        sup = support_height_point(objects, f["x"], f["y"], f["z"])
        if f["z"] <= sup:
            f["z"] = sup
            if f["vz"] < -3.0:
                f["vz"] = -f["vz"] * 0.25
                f["vx"] *= 0.5
                f["vy"] *= 0.5
            else:
                f["rest"] = True
                f["t"] = 0.0
                f["a0"] = f["spin"]
                f["a1"] = (round((f["spin"] - math.pi / 2) / math.pi)
                           * math.pi + math.pi / 2)
                f["et"] = 0.0
                sp = math.hypot(f["vx"], f["vy"])
                if sp > 0.5:
                    f["dx"], f["dy"] = f["vx"] / sp, f["vy"] / sp
                f["vx"] = f["vy"] = f["vz"] = 0.0
    FLYERS[:] = [f for f in FLYERS
                 if not f["rest"] or f.get("fade", 1.0) > 0.0]


def update_wind(dt):
    """Ветер: порывы сильнее/слабее + смена направления. Детерминирован."""
    global ANIM_T, CLOUD_OFF
    ANIM_T += dt
    W = WIND
    W["t"] += dt
    if W["t"] >= W["next"]:
        W["t"] = 0.0
        W["next"] = wind_rng.uniform(9.0, 22.0)
        r = wind_rng.random()
        if r < 0.20:  # штиль
            W["t_str"] = wind_rng.uniform(0.03, 0.15)
        elif r < 0.75:  # обычный
            W["t_str"] = wind_rng.uniform(0.25, 0.65)
        else:  # порыв
            W["t_str"] = wind_rng.uniform(0.9, 1.5)
        W["t_ang"] += wind_rng.uniform(-1.2, 1.2)
        if wind_rng.random() < 0.15:
            W["t_ang"] += wind_rng.uniform(-2.0, 2.0)
    k = 1.0 - math.exp(-dt * 0.7)
    W["str"] += (W["t_str"] - W["str"]) * k
    da = (W["t_ang"] - W["ang"] + math.pi) % (2 * math.pi) - math.pi
    W["ang"] += da * k
    W["kick"] *= math.exp(-dt * 1.4)
    fl = (1.0 + 0.22 * math.sin(ANIM_T * 2.3)
          + 0.13 * math.sin(ANIM_T * 5.1 + 1.0))
    mag = max(0.0, (W["str"] + W["kick"]) * fl)
    W["wx"] = math.cos(W["ang"]) * mag * 2.4  # сила 1.0 ~= 2.4 кл/с
    W["wy"] = math.sin(W["ang"]) * mag * 2.4
    W["mag"] = mag
    CLOUD_OFF += (W["wx"] - W["wy"]) * dt * 9.0


def update_fx(dt, frame):
    global TRAUMA
    TRAUMA = max(0.0, TRAUMA - 1.8 * dt)
    for lst in (FLASHES, RINGS, SMOKES, SPARKS, FLAMES, DUST):
        for e in lst:
            e["t"] += dt
    for s in SMOKES:
        s["z"] += s.get("rise", 1.1) * dt
        s["x"] += (0.30 + WIND["wx"]) * dt
        s["y"] += WIND["wy"] * dt
    for s in DUST:
        s["z"] += 0.35 * dt
        s["x"] += (0.10 + WIND["wx"] * 0.35) * dt
        s["y"] += WIND["wy"] * 0.35 * dt
    for f in FLAMES:
        f["z"] += 0.25 * dt
    for s in SPARKS:
        s["vz"] -= GRAVITY * dt
        s["vx"] += WIND["wx"] * 0.4 * dt
        s["vy"] += WIND["wy"] * 0.4 * dt
        s["x"] += s["vx"] * dt
        s["y"] += s["vy"] * dt
        s["z"] += s["vz"] * dt
    for lst in (FLASHES, RINGS, SMOKES, SPARKS, FLAMES, DUST):
        lst[:] = [e for e in lst if e["t"] < e["life"]]


def draw_fx(window, cam):
    night = clamp((0.6 - LIGHT["amb"]) / 0.35, 0.0, 1.0)
    _c0 = cam.world_to_screen(20, 20, 1)
    _c1 = cam.world_to_screen(20 + WIND["wx"], 20 + WIND["wy"], 1)
    fwx, fwy = _c1[0] - _c0[0], _c1[1] - _c0[1]
    _l = math.hypot(fwx, fwy)
    if _l > 1e-6:
        fwx, fwy = fwx / _l, fwy / _l
    else:
        fwx, fwy = 0.7, 0.7
    _gust = min(1.4, WIND["mag"] + WIND.get("kick", 0.0) * 0.8)

    def _fireball(px, py, R, k, ph):
        # огненный шар: белый центр -> жёлто-оранжевый -> тёмные головни
        a = clamp(1 - k, 0.0, 1.0)
        if k < 0.25:
            col = (255, 252, 235)
        elif k < 0.55:
            col = (255, 204, 92)
        elif k < 0.8:
            col = (238, 118, 32)
        else:
            col = (86, 54, 40)
        grow = 1 - (1 - min(1.0, k * 1.6)) ** 2
        rr = max(2.0, R * (0.25 + 0.75 * grow))
        sz = int(rr * 2.6) + 6
        if sz < 6:
            return
        s = pygame.Surface((sz, sz), pygame.SRCALPHA)
        cc = sz // 2
        al = int(210 * a)
        for i in range(7):  # рваные лепестки по периметру
            ang = ph + i * (math.pi * 2 / 7)
            j = hash01(i * 7 + 3, int(ph * 60.0) + i, 5)
            rad = rr * (0.62 + 0.38 * j)
            ox, oy = math.cos(ang) * rr * 0.42, math.sin(ang) * rr * 0.42
            pygame.draw.circle(s, col + (al,), (int(cc + ox), int(cc + oy)),
                               max(1, int(rad)))
        pygame.draw.circle(s, col + (int(230 * a),), (cc, cc), int(rr))
        if k < 0.35:
            ic = (255, 255, 246)
        elif k < 0.6:
            ic = (255, 236, 180)
        else:
            ic = (252, 168, 74)
        pygame.draw.circle(s, ic + (int(240 * a),), (cc, cc),
                           max(1, int(rr * max(0.1, 0.55 - 0.3 * k))))
        window.blit(s, (int(px) - cc, int(py) - cc))

    for e in RINGS:
        k = e["t"] / e["life"]
        r = (20 + 340 * k) * e["power"] * cam.zoom / PIXEL
        a = int(170 * (1 - k))
        s = pygame.Surface((int(r * 2 + 4), int(r + 4)), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (255, 240, 220, a), s.get_rect(), SP(3))
        k2 = clamp(k * 1.3 - 0.12, 0.0, 1.0)  # вторая волна внутри
        r2 = (8 + 200 * k2) * e["power"] * cam.zoom / PIXEL
        a2 = int(120 * (1 - k2))
        pygame.draw.ellipse(s, (255, 250, 235, a2),
                            (int(r - r2) + 2, int(r / 2 - r2 / 2) + 2,
                             int(r2 * 2), int(r2)), SP(2))
        window.blit(s, (e["x"] - r - 2, e["y"] - r / 2 - 2))
    for e in DUST:  # лёгкая пыльца обломков
        k = e["t"] / e["life"]
        px, py = cam.world_to_screen(e["x"], e["y"], e["z"])
        r = int((e["r"] * (TILE_W / 2) + 10 * k) * cam.zoom / PIXEL)
        a = int(e["a"] * (1 - k))
        if r > 0:
            s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(s, e["c"] + (a,), (r + 1, r + 1), r)
            window.blit(s, (px - r - 1, py - r - 1))
    for e in SMOKES:  # пышный клуб дыма из четырёх под-кругов
        k = e["t"] / e["life"]
        px, py = cam.world_to_screen(e["x"], e["y"], e["z"])
        r = int((e["r"] * (TILE_W / 2) + 26 * k) * cam.zoom / PIXEL)
        a = int(e.get("a", 120) * (1 - k))
        if r > 1:
            col = e.get("c", LIGHT["smoke"])
            s = pygame.Surface((r * 4, int(r * 3.2)), pygame.SRCALPHA)
            cx0, cy0 = r * 2, r * 2
            for i, (dxx, dyy, sc) in enumerate(
                    ((-0.62, 0.10, 0.72), (0.58, 0.06, 0.78),
                     (0.0, -0.5, 0.85), (0.12, 0.28, 0.90))):
                j = hash01(i * 31 + 7, int(e["x"] * 37 + e["y"] * 91), 3)
                rr = r * sc * (0.85 + 0.3 * j)
                pygame.draw.circle(s, col + (a,),
                                   (int(cx0 + dxx * r), int(cy0 + dyy * r)),
                                   max(1, int(rr)))
            window.blit(s, (px - cx0, int(py - cy0)))
    for e in FLASHES:  # огненный шар + ночная вспышка на земле
        k = e["t"] / e["life"]
        R = (30 + 46 * e["power"]) * cam.zoom / PIXEL
        if night > 0.2:
            gr = int(R * 4.2)
            if gr > 3:
                s = pygame.Surface((gr * 2, gr), pygame.SRCALPHA)
                pygame.draw.ellipse(s, (255, 170, 70,
                                        int(70 * night * (1 - k))),
                                    s.get_rect())
                window.blit(s, (e["x"] - gr, e["y"] - gr / 2))
        _fireball(e["x"], e["y"], R, k, e.get("ph", 0.0))
    # огонь: четыре тлеющих яруса с трепетом, угли, ночной отсвет
    _LCRS = ((166, 44, 10, 150, 1.30, 0.30),
             (255, 96, 18, 190, 1.00, 0.55),
             (255, 166, 42, 220, 0.66, 0.80),
             (255, 236, 122, 235, 0.38, 1.05))
    for e in FLAMES:
        k = e["t"] / e["life"]
        px, py = cam.world_to_screen(e["x"], e["y"], e["z"])
        flick = (1 + 0.16 * math.sin(e["t"] * 43 + e["ph"])
                 + 0.07 * math.sin(e["t"] * 97 + e["ph"] * 2.3))
        flick *= 1 + 0.25 * WIND.get("kick", 0.0)  # порыв раздувает языки
        _fv = 0.78 + 0.55 * hash01(int(e["ph"] * 997) % 1000, 41, 9)
        r0 = e["s"] * _fv * (TILE_W / 2) * (0.75 + 0.5 * (1 - k)) * flick
        r = max(2.0, r0 * cam.zoom / PIXEL)
        _tv = 1.55 + 0.85 * hash01(int(e["ph"] * 881) % 1000, 43, 8)
        tall = r * (_tv + 0.30 * math.sin(e["t"] * 29 + e["ph"] * 1.7))
        tall *= 1 + 0.22 * WIND.get("kick", 0.0)
        _wl = fwx * (0.42 + 0.55 * _gust)
        lean = (_wl + 0.28 * math.sin(e["t"] * 21 + e["ph"])) * r
        if night > 0.25:  # пожар освещает землю в такт мерцанию языков
            gr = int(r * (1.4 + night) * flick)
            if gr > 2:
                s = pygame.Surface((gr * 2 + 2, gr + 4), pygame.SRCALPHA)
                pygame.draw.ellipse(s, (255, 140, 50,
                                        int(46 * night * flick)),
                                    s.get_rect())
                window.blit(s, (px - gr - 1, py - gr // 2))
        fade = (1 - k) * (0.4 + 0.6 * min(1.0, e["t"] / 0.08))
        for cr, cg, cb, ca, cs, yoff in _LCRS:
            rr = r * cs
            wide = 0.62 if cs > 0.5 else 0.55
            tip_y = py - tall * yoff + fwy * _gust * r * (yoff / _LCRS[-1][5]) * 0.5
            cx_i = px + lean * (yoff / _LCRS[-1][5])
            pts = [(cx_i, tip_y + rr * 0.9),
                   (cx_i - rr * wide, tip_y),
                   (cx_i + lean * 0.4, tip_y - rr * 1.15),
                   (cx_i + rr * wide, tip_y)]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            x0, y0 = min(xs) - 2, min(ys) - 2
            s = pygame.Surface((int(max(xs) - x0) + 4,
                                int(max(ys) - y0) + 4), pygame.SRCALPHA)
            pygame.draw.polygon(s, (cr, cg, cb, int(ca * fade)),
                                [(int(p[0] - x0) + 2, int(p[1] - y0) + 2)
                                 for p in pts])
            window.blit(s, (int(x0), int(y0)))
        if r > 4:  # ветряные угольки, танцующие над языками
            for i in range(2):
                t01 = (e["t"] * (2.2 + i * 0.7) + e["ph"] + i * 0.5) % 1.0
                ex = px + math.sin(t01 * 9 + e["ph"] * (3 + i)) * r * 0.45
                ey = py - tall * 0.6 - t01 * tall * 1.1
                ea = int(150 * (1 - t01) * flick * fade)
                if ea > 12:
                    pygame.draw.circle(window,
                                       (255, 170 + int(60 * (1 - t01)), 70),
                                       (int(ex), int(ey)), max(1, SP(2)))
    for e in SPARKS:  # искра: жёлтое сердце, оранжевый хвост, тёплый ореол
        px, py = cam.world_to_screen(e["x"], e["y"], e["z"])
        ox, oy = cam.world_to_screen(e["x"] - e["vx"] * 0.05,
                                     e["y"] - e["vy"] * 0.05,
                                     e["z"] - e["vz"] * 0.05)
        k = 1 - e["t"] / e["life"]
        pygame.draw.line(window, (255, int(140 + 80 * k), int(50 + 80 * k)),
                         (ox, oy), (px, py), SP(2) + 1)
        pygame.draw.line(window, (255, int(210 + 45 * k), 160),
                         (int(px - (px - ox) * 0.5),
                          int(py - (py - oy) * 0.5)), (px, py), SP(1))
        hr = max(1, int(2 * k + 1))
        s = pygame.Surface((hr * 4, hr * 4), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 220, 140, int(70 * k)),
                           (hr * 2, hr * 2), hr * 2)
        pygame.draw.circle(s, (255, 250, 230, int(220 * k)),
                           (hr * 2, hr * 2), hr)
        window.blit(s, (int(px) - hr * 2, int(py) - hr * 2))



# ---------------------------------------------------------------------------
# Люди: первое поселение — вожак, костёр, хижины. «С этого всё начнётся».
# ---------------------------------------------------------------------------
VIL = None          # состояние поселения
VIL_T = 0.0         # время поселения (для мерцания огня)
VIL_TREES = []      # ёлки рядом с поселением (доноры жердей)
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
        ntrees = sum(1 for t in VIL_TREES
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
    global VIL, VIL_T, VIL_TREES
    VIL_TREES = [dict(x=o["x"] + 0.5, y=o["y"] + 0.5, o=o)
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
                          cls=t["cls"], stages=_plot_plan(t), stage=0,
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
    VIL = v
    VIL_T = 0.0
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
    trees = [t for t in VIL_TREES if not t["o"].get("dead")]
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
                           stages=_plot_plan(t), stage=0,
                           st_time=0.0, state="wait", debris=[], jobs=[],
                           broken_from=0, was_done=False, relocs=0))
    v["_plots_by_hid"][hid] = v["_plots_by_hid"].get(hid, 0) + 1
    return v["plots"][-1]


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
    for t in VIL_TREES:
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
    for t in VIL_TREES:
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
    night = DAYT >= 0.60 and DAYT < 0.97
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
            an = _vil_pick_prey(v, hum)
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
        p = _vil_next_plot(v, hum)
        if p is not None:
            _vil_assign_plot(v, p, hum)
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
            an = _vil_pick_prey(v, hum)
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
            if sitting < 2 and hash01(VIL_T, hum["id"], 5) < 0.22:
                _vil_send_sit(hum)
                return
        # слоняться возле поселения
        fx, fy = v["fire"]
        ang = hash01(VIL_T, hum["id"], 9) * 6.283
        rr = 0.8 + hash01(VIL_T, hum["id"], 11) * 2.6
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
    fx, fy = VIL["fire"]
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
                _vil_release_prey(v, hum)
                hum["state"] = "idle"
                hum["st"] = 0.3
                hum["act"] = "task"
                return
            o_ = an_["o"]
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
                    _vil_release_prey(v, hum)
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
        o = next((t["o"] for t in VIL_TREES
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
            _vil_puff(v, lx, ly, _vil_gz(lx, ly) + 1.1)
            _vil_puff(v, lx, ly, _vil_gz(lx, ly) + 0.6)
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
            _vil_work_done(v, hum)
    elif hum["state"] in ("attack", "aim"):
        hum["st"] -= dt
        if hum["st"] <= 0:
            an_ = next((a for a in v["animals"]
                        if id(a) == hum.get("prey")), None)
            if an_ is not None and \
                    math.hypot(an_["o"]["x"] - hum["x"],
                               an_["o"]["y"] - hum["y"]) <= 4.0:
                an_["o"]["hunt_by"] = None
                _vil_kill_prey(v, hum, an_)
            _vil_release_prey(v, hum)
            hum["state"] = "idle"
            hum["st"] = 0.4
            hum["act"] = "task"
    elif hum["state"] == "light":
        hum["st"] -= dt
        if hum["st"] <= 0:
            v["lit"] = True
            _vil_phase_hut(v)
    elif hum["state"] == "sit":
        hum["st"] -= dt
        if hum["st"] <= 0:
            hum["sit_ang"] = 0.0
            _vil_pick_task(v, hum)
    else:  # idle
        hum["st"] -= dt
        if hum["st"] <= 0:
            _vil_pick_task(v, hum)


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
        _vil_release_prey(v, h)
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
    _vil_release_prey(v, hum)
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
def _vil_leader_step(v, hum, dt):
    fx, fy = v["fire"]
    ph = v["phase"]
    if ph == "council":
        t = v["t"]
        if t < 2.6:
            # встать в круг
            i = hum["id"]
            ang = i * 6.283 / 10 + 0.31
            hum["tx"] = fx + math.cos(ang) * 1.7
            hum["ty"] = fy + math.sin(ang) * 1.7
            hum["state"] = "walk"
            hum["act"] = "council"
        elif t < 3.6:
            # шагнуть в центр
            hum["tx"], hum["ty"] = fx, fy
            hum["state"] = "walk"
            hum["act"] = "leader_walk"
        else:
            hum["state"] = "idle"
    elif ph in ("fire_stones", "fire_sticks", "fire_light"):
        if hum["state"] in ("work", "place", "light"):
            hum["st"] -= dt
            if hum["st"] <= 0:
                _vil_leader_done(v, hum)
            return
        if hum.get("carried_log"):
            # везёт жердь к огню — не перегенерировать цель
            hum["tx"], hum["ty"] = fx, fy
            hum["act"] = "log"
            hum["state"] = "walk"
            return
        # следующая цель
        if ph == "fire_stones":
            i = v["stones"]
            ang = i * 6.283 / 6 + 0.26
            hum["tx"] = fx + math.cos(ang) * 0.30
            hum["ty"] = fy + math.sin(ang) * 0.30
            hum["act"] = "stone"
        elif ph == "fire_sticks":
            if v["pile_n"] > 0:
                hum["tx"], hum["ty"] = v["pile"]
                hum["act"] = "log_get"
            else:
                hum["tx"], hum["ty"] = fx, fy
                hum["act"] = "log"
        else:  # fire_light
            hum["tx"], hum["ty"] = fx + 0.12, fy + 0.12
            hum["act"] = "light"
        hum["state"] = "walk"


def _vil_leader_done(v, hum):
    ph = v["phase"]
    if ph == "fire_stones":
        v["stones"] += 1
        if v["stones"] >= 6:
            v["phase"] = "fire_sticks"
            v["t"] = 0.0
    elif ph == "fire_sticks":
        if hum.get("carried_log"):
            hum["carried_log"] = False
            v["fire_logs"] += 1
            if v["fire_logs"] >= 4:
                v["phase"] = "fire_light"
                v["t"] = 0.0
        else:
            v["pile_n"] -= 1  # подобрал жердь с кучи
        hum["state"] = "idle"
        hum["st"] = 0.3
    elif ph == "fire_light":
        v["lit"] = True
        _vil_phase_hut(v)
    hum["state"] = "idle"
    hum["st"] = 0.5


def _vil_make_spear(v):
    """Копьё (камень + жерди) в мастерской, пока хватает ресурсов."""
    if v["lvl"] < 2 or v["res"]["spears"] >= 10:
        return
    p12 = next((p for p in v["plots"] if p["tpl"]["hid"] == 12
                and p["state"] == "done"), None)
    if p12 is None or v["res"]["stones"] < 2 or v["pile_n"] < 2:
        return
    v["res"]["stones"] -= 2
    for _ in range(2):
        if v["stones_placed"]:
            v["stones_placed"].pop(0)
    v["pile_n"] -= 2
    v["res"]["spears"] += 1
    bx, by = p12["x"] + 0.62, p12["y"] + 0.20
    z0 = _vil_gz(bx, by)
    v["objects"].append(dict(
        x=bx, y=by, z=z0 + 0.02, w=0.05, d=0.03, h=0.66,
        color="wood_light", shape="box", mat="wood_light",
        vx=0.0, vy=0.0, vz=0.0, erode=1.2, vox=0.04, sort_min=True,
        vid=-2))
    v["objects"].append(dict(
        x=bx - 0.012, y=by - 0.008, z=z0 + 0.62, w=0.07, d=0.05, h=0.10,
        color="gray", shape="box", mat="stone",
        vx=0.0, vy=0.0, vz=0.0, erode=0.6, vox=0.035, sort_min=True,
        vid=-2))


def _vil_spawn_animal(v, kind, px, py):
    """Зверь: зайец (добыча палкой/камнем) или олень (только копьё)."""
    gz = _vil_gz(px, py)
    v["_an_n"] = v.get("_an_n", 0) + 1
    aid = v["_an_n"]
    if kind == "rabbit":
        specs = ((0.0, 0.0, 0.0, 0.16, 0.11, 0.09, "bone", "bone"),
                 (0.14, 0.015, 0.02, 0.09, 0.08, 0.07, "bone", "bone"))
        base = 2.1
    else:
        specs = ((0.0, 0.0, 0.05, 0.42, 0.18, 0.26, "wood_light",
                  "wood_light"),
                 (0.36, 0.02, 0.16, 0.14, 0.10, 0.12, "wood_light",
                  "wood_light"),
                 (0.39, 0.03, 0.26, 0.045, 0.045, 0.09, "bone", "bone"),
                 (0.44, 0.03, 0.26, 0.045, 0.045, 0.09, "bone", "bone"))
        base = 3.4
    boxes = []
    for dx, dy, zz, w_, d_, h_, cc, mm in specs:
        b = dict(x=px + dx, y=py + dy, z=gz + zz, w=w_, d=d_, h=h_,
                 color=cc, shape="box", mat=mm,
                 vx=0.0, vy=0.0, vz=0.0, erode=0.8, vox=0.05,
                 sort_min=True, animal=kind, aid=aid, zoff=zz)
        v["objects"].append(b)
        boxes.append(b)
    v["animals"].append(dict(o=boxes[0], boxes=boxes, kind=kind,
                             home=(px, py), tx=px, ty=py, t=1.0,
                             base=base, spd=base * 0.5))


def _vil_pick_prey(v, hum):
    """Ближайшая добыча: олень — только если копья на всех охотников."""
    if v["lvl"] < 1 or not v["animals"]:
        return None
    n_sp_use = sum(1 for h in v["workers"] if h is not hum
                   and h.get("spear"))
    best, bd = None, 16.0
    for an in v["animals"]:
        o = an["o"]
        if o.get("hunt_by") is not None:
            continue
        if an["kind"] == "deer" and \
                v["res"]["spears"] <= n_sp_use:
            continue  # на оленя — только с копьём
        d = math.hypot(o["x"] - hum["x"], o["y"] - hum["y"])
        if d < bd:
            bd, best = d, an
    return best


def _vil_kill_prey(v, hum, an):
    o = an["o"]
    for b in an["boxes"]:
        try:
            v["objects"].remove(b)
        except ValueError:
            pass
    try:
        v["animals"].remove(an)
    except ValueError:
        pass
    v["food"] = min(80.0, v.get("food", 0.0) + (3.0 if an["kind"] == "deer"
                                                else 1.0))
    v["blood"].append(dict(x=o["x"] + 0.1, y=o["y"] + 0.1, r=0.16,
                           t=0.0, big=False))
    # тушка на земле (протухнет)
    v["objects"].append(dict(
        x=o["x"], y=o["y"], z=_vil_gz(o["x"], o["y"]),
        w=0.16, d=0.10, h=0.05,
        color="bone", shape="box", mat="bone",
        vx=0.0, vy=0.0, vz=0.0, erode=0.6, vox=0.05, sort_min=True,
        carcass=45.0))


def _vil_release_prey(v, hum):
    for an in v["animals"]:
        if an["o"].get("hunt_by") == hum["id"]:
            an["o"]["hunt_by"] = None
    hum["spear"] = False
    hum["prey"] = None


def update_village(dt, objects=None):
    """Обновление поселения: фазы, люди, жерди, костёр, город."""
    global VIL_T
    v = VIL
    if v is None:
        return
    if objects is not None:
        v["objects"] = objects
    VIL_T += dt
    v["t"] += dt
    # --- падение жердей с деревьев ---
    active = sum(1 for s in v["sticks"] if not s.get("old"))
    if v["t"] >= v["next_drop"] and len(v["sticks"]) < 24:
        v["next_drop"] = v["t"] + 1.6 + hash01(VIL_T * 0.7, 1, 2) * 2.8
        fx_, fy_ = v["fire"]
        # жерди: часть падает с веток, часть «находится» на земле
        # у самого костра (короткий круг до кучи)
        for k in range(2 if hash01(VIL_T, 13, 14) < 0.4 else 1):
            if hash01(VIL_T, 15 + k, 16 + k) < 0.5:
                sx = fx_ + (hash01(VIL_T, 5 + k, 6 + k) - 0.5) * 10.0
                sy = fy_ + (hash01(VIL_T, 7 + k, 8 + k) - 0.5) * 10.0
                gz = _vil_gz(sx, sy)
                v["sticks"].append(dict(
                    x=sx, y=sy, z=gz, vz=0.0,
                    falling=False, t=0.0,
                    owner=None, ang=hash01(VIL_T, 11 + k, 12 + k)
                    * 6.283))
                continue
            trees = [t for t in VIL_TREES
                     if not t["o"].get("dead")
                     and math.hypot(t["x"] - fx_, t["y"] - fy_) < 13]
            if not trees:
                continue
            t = trees[int(hash01(VIL_T, 3 + k, 4 + k)
                          * len(trees)) % len(trees)]
            sx = t["x"] + (hash01(VIL_T, 5 + k, 6 + k) - 0.5) * 1.1
            sy = t["y"] + (hash01(VIL_T, 7 + k, 8 + k) - 0.5) * 1.1
            if 1 < sx < GRID_W - 1 and 1 < sy < GRID_D - 1:
                gz = _vil_gz(sx, sy)
                v["sticks"].append(dict(
                    x=sx, y=sy, z=gz + 1.7 + k * 0.25, vz=0.0,
                    falling=True, t=0.0,
                    owner=None, ang=hash01(VIL_T, 11 + k, 12 + k)
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
    _oid = set(id(b) for b in v["objects"])
    for an in list(v["animals"]):
        if id(an["o"]) not in _oid:  # зверя разрушили — выбрасываем
            v["animals"].remove(an)
            continue
        o = an["o"]
        an["t"] -= dt
        hx = hy = None
        hbid = o.get("hunt_by")
        if hbid is not None:
            hh = next((h for h in v["workers"] if h["id"] == hbid), None)
            if hh is None or hh.get("dead"):
                o["hunt_by"] = None
            else:
                hx, hy = hh["x"], hh["y"]
        fleeing = (hx is not None and
                   math.hypot(hx - o["x"], hy - o["y"]) < 7.0)
        if an["t"] <= 0 or fleeing:
            an["t"] = 2.0 + rng.uniform(0, 3.0)
            if fleeing:
                dx = o["x"] - hx
                dy = o["y"] - hy
                l = max(0.3, math.hypot(dx, dy))
                an["tx"] = clamp(o["x"] + dx / l * 5.0, 2, GRID_W - 2)
                an["ty"] = clamp(o["y"] + dy / l * 5.0, 2, GRID_D - 2)
                an["spd"] = an["base"] * (1.35 if an["kind"] == "deer"
                                          else 1.3)
            else:
                an["tx"] = clamp(an["home"][0] + rng.uniform(-4, 4),
                                 2, GRID_W - 2)
                an["ty"] = clamp(an["home"][1] + rng.uniform(-4, 4),
                                 2, GRID_D - 2)
                an["spd"] = an["base"] * 0.5
        dx = an["tx"] - o["x"]
        dy = an["ty"] - o["y"]
        l = math.hypot(dx, dy)
        if l > 0.1:
            k = min(1.0, an["spd"] * dt / l)
            gz = _vil_gz(o["x"] + dx * k, o["y"] + dy * k)
            for b in an["boxes"]:
                b["x"] += dx * k
                b["y"] += dy * k
                b["z"] = gz + b["zoff"]
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
            key = (int(hum["x"]), int(hum["y"]))
            if 0 <= key[0] < GRID_W and 0 <= key[1] < GRID_D:
                v["wear"][key] = min(6.0, v["wear"].get(key, 0.0) + 0.4)
        if len(v["wear"]) > 350:
            for k2 in list(v["wear"]):
                v["wear"][k2] *= 0.97
                if v["wear"][k2] < 0.3:
                    del v["wear"][k2]
    # лес восстанавливается: из пня вырастает новая ёлка
    for tr in VIL_TREES:
        o = tr["o"]
        if o.get("dead") == "stump" \
                and v["t"] - o.get("stump_t", 0.0) > 240.0:
            o["dead"] = None
            o["vx"] = o["vy"] = o["vz"] = 0.0
            _vil_puff(v, o["x"] + 0.5, o["y"] + 0.5,
                      _vil_gz(o["x"], o["y"]) + 0.6, small=True)
    # --- люди ---
    _night = DAYT >= 0.60 and DAYT < 0.97
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
        v["defeat"] = VIL_T
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


# ---------------------------------------------------------------------------
# Спрайты человечков: master 8x14, пиксели рисуются по позам
# ---------------------------------------------------------------------------
def _hum_master(pose, hum):
    # Человечек 10x16: мелкий, но детализированный (волосы, глаза,
    # тени на тунике, пояс, ботинки) — в игре рисуется примерно в 2 раза
    # меньше прежнего.
    W, H = 10, 16
    m = pygame.Surface((W, H), pygame.SRCALPHA)
    skin, hair, tun = _HSKIN, hum["hair"], hum["tunic"]
    tun_d = tone(tun, 0.72)
    tun_l = tone(tun, 1.18)
    legs, boots = _HLEGS, _HBOOTS
    eye = (44, 34, 32)

    def head(x0, y0):
        # волосы с челкой, лицо, глаза
        for j in range(x0, x0 + 4):
            m.set_at((j, y0), hair)
        for j in range(x0 + 1, x0 + 3):
            m.set_at((j, y0 + 1), skin)
        m.set_at((x0, y0 + 1), hair)
        m.set_at((x0 + 3, y0 + 1), hair)
        m.set_at((x0 + 1, y0 + 1), (50, 40, 36) if j % 2 else skin)
        for j in range(x0 + 1, x0 + 3):
            m.set_at((j, y0 + 2), skin)
        m.set_at((x0 + 1, y0 + 2), eye)
        m.set_at((x0 + 2, y0 + 2), eye)

    if pose == "dead":
        # труп: лежит на боку, голова справа
        for i in (0, 1, 2):
            for j in range(2, 8):
                m.set_at((j, i), tone(tun, 0.55))
        for i in (0, 1):
            for j in range(8, 10):
                m.set_at((j, i), legs)
        m.set_at((9, 0), boots)
        m.set_at((9, 1), boots)
        for j in range(0, 3):
            for i in range(0, 3):
                m.set_at((j, i), skin)
        for j in range(0, 3):
            m.set_at((j, 0), hair)
            m.set_at((j, 2), hair)
        m.set_at((1, 1), eye)
        return m

    yo = 0
    if pose in ("sit", "clean", "stun"):
        yo = 1
    # голова (чуть по центру)
    head(3, yo)
    # шея
    m.set_at((3, 3 + yo), skin)
    m.set_at((4, 3 + yo), skin)
    # плечи и туника с тенями и бликом
    for i in range(4, 10 + yo):
        for j in range(2, 8):
            c = tun
            if i < 6 + yo:
                c = tun_l
            if i > 7 + yo:
                c = tun_d
            m.set_at((j, i), c)
        m.set_at((1, i), tun_d if i > 5 + yo else tun)
        m.set_at((8, i), tun_d)
    # пояс
    for j in range(2, 8):
        m.set_at((j, 9 + yo), (92, 70, 42))
    m.set_at((4, 9 + yo), (150, 128, 70))  # пряжка
    if pose == "sit":
        # ноги сложены вперёд
        for j in range(1, 8):
            m.set_at((j, 11), legs)
            m.set_at((j, 12), boots)
        for i in (10, 11):
            for j in range(2, 8):
                m.set_at((j, i + 0), tun_d)
        # руки по коленям
        m.set_at((1, 8), skin)
        m.set_at((8, 8), skin)
        return m
    if pose == "carry":
        # руки вперёд + жердь в руках
        for i in (5, 6):
            for j in range(1, 9):
                m.set_at((j, i), skin)
        for k in range(8):
            j = 1 + k
            i = 4 + k // 2
            if i < 16:
                m.set_at((j, i), (122, 84, 48))
        return m
    if pose == "air":
        # отлёты: руки вверх, ноги врозь
        for i in range(3, 6 + yo):
            m.set_at((1, i), skin)
            m.set_at((8, i), skin)
        for i in range(10, 15):
            m.set_at((2, i), legs)
            m.set_at((3, i), legs)
            m.set_at((6, i), legs)
            m.set_at((7, i), legs)
        m.set_at((2, 14), boots)
        m.set_at((7, 14), boots)
        return m
    if pose == "clean":
        # присел, собирает обломки: руки вперёд-вниз
        for i in range(9, 12):
            for j in range(2, 8):
                m.set_at((j, i + 1), legs if i > 9 else tun_d)
        for j in (1, 2, 7, 8):
            m.set_at((j, 11), legs)
        for j in (1, 8):
            m.set_at((j, 12), boots)
        for i in (9, 10):
            m.set_at((1, i + 1), skin)
            m.set_at((8, i + 1), skin)
        return m
    if pose in ("work_a",):
        # правая рука вверх с молотком
        for i in range(4, 7):
            m.set_at((8, i), skin)
        m.set_at((8, 3), (120, 124, 130))
        m.set_at((8, 2), (90, 92, 98))
        m.set_at((7, 2), (90, 92, 98))
        for i in (6, 7):
            m.set_at((1, i), skin)
    elif pose in ("work_b", "repair"):
        # рука вниз, корпус чуть присел
        for i in range(7, 10):
            m.set_at((8, i), skin)
        for i in (6, 7):
            m.set_at((1, i), skin)
    elif pose == "light":
        # рука вперёд, искра добавляется при рендере
        for i in (6, 7):
            for j in range(8, 10):
                m.set_at((j, i), skin)
        m.set_at((1, 7), skin)
    elif pose in ("walk_a", "walk_b", "run_a", "run_b"):
        run = pose.startswith("run")
        step = 2 if run else 1
        if pose in ("walk_a", "run_a"):
            l0, r0 = 10, 11 + step
        else:
            l0, r0 = 11 + step, 10
        for i in range(9, 15):
            for j in range(2, 4):
                if i >= l0:
                    m.set_at((j, i), legs)
            for j in range(5, 7):
                if i >= r0:
                    m.set_at((j, i), legs)
        m.set_at((2, 14), boots)
        m.set_at((3, 14), boots)
        m.set_at((5, 14), boots)
        m.set_at((6, 14), boots)
        # махи руками
        if pose in ("walk_a", "run_a"):
            m.set_at((1, 6), skin)
            m.set_at((8, 7), skin)
            m.set_at((1, 7), skin)
        else:
            m.set_at((1, 7), skin)
            m.set_at((8, 6), skin)
            m.set_at((8, 7), skin)
    else:
        # stand / place
        for i in range(10, 15):
            for j in range(2, 4):
                m.set_at((j, i), legs)
            for j in range(5, 7):
                m.set_at((j, i), legs)
        for j in (2, 3, 5, 6):
            m.set_at((j, 14), boots)
        for i in (5, 6, 7, 8):
            m.set_at((1, i), tun_d)
            m.set_at((8, i), tun_d)
        for j in (1, 8):
            m.set_at((j, 9), skin)
        if pose == "place":
            m.set_at((1, 8), skin)
            m.set_at((8, 8), skin)
        if pose == "stun":
            for j in (0, 9):
                m.set_at((j, 6), skin)
    return m


def _hum_sprite(pose, hum, S, flip):
    key = (pose, hum["hair"], hum["tunic"], S, flip)
    spr = VIL_HUM_SPR.get(key)
    if spr is None:
        m = _hum_master(pose, hum)
        tw = max(3, int(round(S * 10 / 16)))
        spr = pygame.transform.scale(m, (tw, S))
        if flip:
            spr = pygame.transform.flip(spr, True, False)
        if len(VIL_HUM_SPR) > 4096:
            VIL_HUM_SPR.clear()
        VIL_HUM_SPR[key] = spr
    return spr


def _hum_pose(hum, moving, spd):
    st = hum["state"]
    if hum.get("dead"):
        return "dead"
    if st == "air":
        return "air"
    if st == "clean":
        return "clean"
    if st == "stun":
        return "stun"
    if st == "sit":
        return "sit"
    if st == "pick" or st == "place":
        return "place"
    if st == "light":
        return "light"
    if st == "drop":
        return "place"
    if st in ("work",):
        return "work_a" if int(hum["ph"] * 2) % 2 == 0 else "work_b"
    if moving:
        fr = int(hum["ph"]) % 2
        if spd > 1.9:
            return "run_a" if fr == 0 else "run_b"
        return "walk_a" if fr == 0 else "walk_b"
    if hum["carry"]:
        return "carry"
    return "stand"


def _draw_hut_a(window, cam, hx, hy, z0, prog, ctx):
    """Двускатный шалаш, конёк вдоль X. Этапы: 4 стойки, стены, крыша."""
    W, D = 1.5, 1.1

    def pt(x, y, z):
        return cam.world_to_screen(hx + x, hy + y, z0 + z)

    wood_d = BASE_COLORS["wood_dark"]
    wood_l = BASE_COLORS["plank_light"]
    straw = BASE_COLORS["straw"]
    # 0: утоптанная поляна (появляется с началом стройки)
    if prog > 0:
        pygame.draw.polygon(window, tone(shade(GRASS, PZ), 0.90),
                            [pt(0, 0, 0), pt(W, 0, 0), pt(W, D, 0), pt(0, D, 0)])
    # 1-4: стойки
    for i, (px, py) in enumerate(((0.05, 0.05), (W - 0.05, 0.05),
                                  (W - 0.05, D - 0.05), (0.05, D - 0.05))):
        if prog <= i:
            continue
        h = 0.5
        pygame.draw.polygon(window, shade(wood_d, (1, 0, 0)),
                            [pt(px + 0.03, py, 0), pt(px + 0.03, py + 0.06, 0),
                             pt(px + 0.03, py + 0.06, h),
                             pt(px + 0.03, py, h)])
        pygame.draw.polygon(window, shade(wood_d, (0, 1, 0)),
                            [pt(px, py + 0.06, 0), pt(px + 0.06, py + 0.06, 0),
                             pt(px + 0.06, py + 0.06, h),
                             pt(px, py + 0.06, h)])
    # 5-6: задняя стена (доски)
    if prog > 4:
        wall_t = 1.0 if prog > 5 else 0.55
        q = [pt(0, D - 0.02, 0), pt(W, D - 0.02, 0),
             pt(W, D - 0.02, 0.5 * wall_t), pt(0, D - 0.02, 0.5 * wall_t)]
        pygame.draw.polygon(window, shade(wood_l, (0, 1, 0)), q)
        for k in range(1, 4):
            t = 0.5 * wall_t * k / 4
            pygame.draw.line(window, tone(shade(wood_d, (0, 1, 0)), 0.6),
                             pt(0, D - 0.02, t), pt(W, D - 0.02, t), 1)
    # 7-8: передняя стена с проёмом
    if prog > 6:
        for xa, xb in ((0.0, 0.95), (1.15, W)):
            q = [pt(xa, 0.02, 0), pt(xb, 0.02, 0),
                 pt(xb, 0.02, 0.48), pt(xa, 0.02, 0.48)]
            pygame.draw.polygon(window, shade(wood_l, (0, -1, 0)), q)
            for k in range(1, 4):
                t = 0.48 * k / 4
                pygame.draw.line(window, tone(shade(wood_d, (0, -1, 0)), 0.6),
                                 pt(xa, 0.02, t), pt(xb, 0.02, t), 1)
        pygame.draw.polygon(window, tone(shade(wood_d, (0, 1, 0)), 0.35),
                            [pt(0.95, 0.02, 0), pt(1.15, 0.02, 0),
                             pt(1.15, 0.02, 0.48), pt(0.95, 0.02, 0.48)])
    # 9: крыша-щипец
    if prog > 8:
        r = 0.14
        zf, zt = 0.52, 0.86
        front = [pt(-r, -r, zf), pt(W + r, -r, zf),
                 pt(W + r, D / 2, zt), pt(-r, D / 2, zt)]
        back = [pt(-r, D + r, zf), pt(W + r, D + r, zf),
                pt(W + r, D / 2, zt), pt(-r, D / 2, zt)]
        pygame.draw.polygon(window, shade(straw, (0, 0.62, 0.79)), back)
        pygame.draw.polygon(window, shade(straw, (0, -0.62, 0.79)), front)
        for s, q in ((-1, front), (1, back)):
            pygame.draw.line(window, tone(shade(straw, (0, 0, 1)), 0.55),
                             q[0], q[1], 2)
        # торцы-фронтоны (плетёнка)
        for xe in (-r, W + r):
            pygame.draw.polygon(window, tone(shade(straw, (1, 0, 0)), 0.82),
                                [pt(xe, 0, 0.5), pt(xe, D, 0.5),
                                 pt(xe, D / 2, zt)])
        pygame.draw.line(window, tone(shade(straw, (0, 0, 1)), 1.2),
                         pt(-r, D / 2, zt), pt(W + r, D / 2, zt), 2)


def _draw_hut_c(window, cam, hx, hy, z0, prog, ctx):
    # Круглая хижина: колья, стена-цилиндр, конус соломы
    R, HC = 0.65, 0.46

    def pt(x, y, z):
        return cam.world_to_screen(hx + x, hy + y, z0 + z)

    wood_d = BASE_COLORS["wood_dark"]
    wood_l = BASE_COLORS["plank_light"]
    straw = BASE_COLORS["straw"]
    if prog > 0:  # утоптанная поляна
        c0 = pt(R, R, 0)
        rx = abs(pt(R * 2, R, 0)[0] - c0[0]) + 2
        ry = abs(pt(R, R * 2, 0)[1] - c0[1]) + 2
        pygame.draw.ellipse(window, tone(shade(GRASS, PZ), 0.90),
                            (c0[0] - rx, c0[1] - ry * 0.35, rx * 2,
                             ry * 0.7))
    # 1-4: колья-стойки в квадрантах
    for i, (px, py) in enumerate(((R * 0.7, R * 0.7), (R * 1.3, R * 0.7),
                                  (R * 1.3, R * 1.3), (R * 0.7, R * 1.3))):
        if prog <= i:
            continue
        pygame.draw.polygon(window, shade(wood_d, (1, 0, 0)),
                            [pt(px + 0.03, py, 0), pt(px + 0.03, py + 0.06, 0),
                             pt(px + 0.03, py + 0.06, HC),
                             pt(px + 0.03, py, HC)])
        pygame.draw.polygon(window, shade(wood_d, (0, 1, 0)),
                            [pt(px, py + 0.06, 0), pt(px + 0.06, py + 0.06, 0),
                             pt(px + 0.06, py + 0.06, HC),
                             pt(px, py + 0.06, HC)])
    # 5-6: стена-цилиндр (задняя дуга темнее, передняя светлее)
    if prog > 4:
        n = 12
        wfull = 1.0 if prog > 5 else 0.5
        for back in (True, False):
            bot, top = [], []
            for k in range(n + 1):
                a = math.pi * k / n + (math.pi if back else 0.0)
                bot.append(pt(R + R * math.cos(a), R + R * math.sin(a), 0))
                top.append(pt(R + R * math.cos(a), R + R * math.sin(a),
                              HC * wfull))
            col = (tone(shade(wood_l, (0, 1, 0)), 0.72) if back
                   else shade(wood_l, (0, -1, 0)))
            pygame.draw.polygon(window, col, bot + top[::-1])
        if prog > 5:  # швы досок
            for k3 in range(1, 3):
                zt = HC * k3 / 3
                for k2 in range(0, n + 1, 2):
                    a1 = math.pi * k2 / n
                    a2 = math.pi * (k2 + 1) / n
                    pygame.draw.line(window,
                                     tone(shade(wood_d, (0, -1, 0)), 0.65),
                                     pt(R + R * math.cos(a1),
                                        R + R * math.sin(a1), zt),
                                     pt(R + R * math.cos(a2),
                                        R + R * math.sin(a2), zt), 1)
    # 7-8: конус соломы
    if prog > 6:
        ht = HC + 0.42 * (1.0 if prog > 7 else 0.55)
        n = 12
        for back in (True, False):
            poly = []
            for k in range(n + 1):
                a = math.pi * k / n + (math.pi if back else 0.0)
                poly.append(pt(R + R * math.cos(a),
                               R + R * math.sin(a), HC))
            apex = pt(R, R, ht)
            poly.append(apex)
            poly.append(apex)
            pygame.draw.polygon(window,
                                tone(shade(straw, (0, 1, 0)), 0.78)
                                if back else shade(straw, (0, -1, 0)),
                                poly)
    # 9: дверь + дымарь
    if prog > 8:
        pygame.draw.polygon(window, tone(shade(wood_d, (0, -1, 0)), 0.4),
                            [pt(R - 0.14, R + 0.62, 0),
                             pt(R + 0.14, R + 0.62, 0),
                             pt(R + 0.14, R + 0.62, 0.34),
                             pt(R - 0.14, R + 0.62, 0.34)])
        p1 = pt(R, R, HC + 0.42)
        p2 = pt(R + 0.05, R + 0.05, HC + 0.62)
        pygame.draw.line(window, tone(shade(wood_d, (0, 1, 0)), 1.1),
                         p1, p2, 2)


def _draw_hut_b(window, cam, hx, hy, z0, prog):
    """Навес на стойках: односкатная крыша."""
    W, D = 1.4, 1.0
    wood_d = BASE_COLORS["wood_dark"]
    wood_l = BASE_COLORS["plank_light"]
    straw = BASE_COLORS["straw"]

    def pt(x, y, z):
        return cam.world_to_screen(hx + x, hy + y, z0 + z)

    if prog > 0:
        pygame.draw.polygon(window, tone(shade(GRASS, PZ), 0.90),
                            [pt(0, 0, 0), pt(W, 0, 0), pt(W, D, 0), pt(0, D, 0)])
    posts = ((0.05, D - 0.05, 0.62), (W - 0.05, D - 0.05, 0.62),
             (0.05, 0.05, 0.34), (W - 0.05, 0.05, 0.34))
    for i, (px, py, h) in enumerate(posts):
        if prog <= i:
            continue
        pygame.draw.polygon(window, shade(wood_d, (1, 0, 0)),
                            [pt(px + 0.03, py, 0), pt(px + 0.03, py + 0.06, 0),
                             pt(px + 0.03, py + 0.06, h),
                             pt(px + 0.03, py, h)])
        pygame.draw.polygon(window, shade(wood_d, (0, 1, 0)),
                            [pt(px, py + 0.06, 0), pt(px + 0.06, py + 0.06, 0),
                             pt(px + 0.06, py + 0.06, h),
                             pt(px, py + 0.06, h)])
    if prog > 4:
        q = [pt(0, D - 0.02, 0), pt(W, D - 0.02, 0),
             pt(W, D - 0.02, 0.6), pt(0, D - 0.02, 0.6)]
        pygame.draw.polygon(window, shade(wood_l, (0, 1, 0)), q)
        for k in range(1, 4):
            t = 0.6 * k / 4
            pygame.draw.line(window, tone(shade(wood_d, (0, 1, 0)), 0.6),
                             pt(0, D - 0.02, t), pt(W, D - 0.02, t), 1)
    if prog > 5:
        zf, zt = 0.32, 0.66
        front = [pt(-0.12, -0.12, zf), pt(W + 0.12, -0.12, zf),
                 pt(W + 0.12, D + 0.06, zt), pt(-0.12, D + 0.06, zt)]
        pygame.draw.polygon(window, shade(straw, (0, -0.55, 0.83)), front)
        pygame.draw.line(window, tone(shade(straw, (0, 0, 1)), 0.5),
                         front[0], front[1], 2)
        for xe in (-0.12, W + 0.12):
            pygame.draw.polygon(window, tone(shade(straw, (1, 0, 0)), 0.8),
                                [pt(xe, 0, zf), pt(xe, D, 0.62),
                                 pt(xe, D, 0.0)])
    if prog > 7:
        for xe in (0.35, 0.7, 1.05):
            pygame.draw.line(window, tone(shade(straw, (0, -0.55, 0.83)), 0.75),
                             pt(xe, -0.12, 0.32),
                             pt(xe, D + 0.06, 0.66), 1)


def _vil_draw_fire(window, cam, ctx):
    v = VIL
    fx, fy = v["fire"]
    z0 = _vil_gz(fx, fy)
    ze = ctx[3]
    # подкладка-земля
    r0 = (0.34 * (TILE_W / 2) * ze)
    c0 = cam.world_to_screen(fx, fy, z0)
    pygame.draw.ellipse(window, tone(shade(DIRT_COLOR, PZ), 0.80),
                        (c0[0] - r0, c0[1] - r0 / 2, r0 * 2, r0))
    # кольцо камней
    for i in range(6):
        if v["stones"] < 1 and v["fire_logs"] < 1 and not v["lit"]:
            return
        ang = i * 6.283 / 6 + 0.26
        if v["stones"] > 0 and i >= v["stones"] and not v["lit"]:
            continue
        sx, sy = fx + math.cos(ang) * 0.30, fy + math.sin(ang) * 0.30
        p = cam.world_to_screen(sx, sy, z0)
        rs = max(2, int(0.11 * (TILE_W / 2) * ze))
        pygame.draw.ellipse(window, shade(BASE_COLORS["gray"], (0, 1, 0.3)),
                            (p[0] - rs, p[1] - rs / 2, rs * 2, rs))
        pygame.draw.ellipse(window, shade(BASE_COLORS["gray"], (0, 0, 1)),
                            (p[0] - rs * 0.6, p[1] - rs * 0.75, rs * 1.2,
                             rs * 0.6))
    nightv = clamp((0.6 - LIGHT["amb"]) / 0.35, 0.0, 1.0)
    if nightv > 0.2 and v["lit"]:
        r = max(24, int(TILE_W / 2 * ze * 3.2))
        gl = _radial_glow(("fire", r), r, (255, 150, 50), 46)
        window.blit(gl, (int(c0[0] - r), int(c0[1] - r * 0.7)))
    wood = BASE_COLORS["wood_dark"]
    if v["fire_logs"] < 1 and v["stones"] < 6:
        for i in range(3):
            a = i * 2.1 + 0.4
            x1 = fx + math.cos(a) * 0.26
            y1 = fy + math.sin(a) * 0.26
            x2 = fx + math.cos(a + 1.1) * 0.20
            y2 = fy + math.sin(a + 1.1) * 0.20
            p1 = cam.world_to_screen(x1, y1, z0 + 0.015)
            p2 = cam.world_to_screen(x2, y2, z0 + 0.015)
            pygame.draw.line(window,
                             tone(shade(BASE_COLORS["wood_light"], PZ), 0.85),
                             p1, p2, max(1, SP(1)))
    # жерди-шалашик
    for i in range(max(0, min(4, v["fire_logs"]))):
        ang = i * 1.7 + 0.5
        x1 = fx + math.cos(ang) * 0.22
        y1 = fy + math.sin(ang) * 0.22
        x2 = fx + math.cos(ang + 2.4) * 0.20
        y2 = fy + math.sin(ang + 2.4) * 0.20
        p1 = cam.world_to_screen(x1, y1, z0 + 0.02)
        p2 = cam.world_to_screen(x2, y2, z0 + 0.02)
        pt = cam.world_to_screen((x1 + x2) * 0.5 + 0.02,
                                 (y1 + y2) * 0.5 - 0.02, z0 + 0.34)
        pygame.draw.line(window, tone(shade(wood, (0, 1, 0)), 0.9),
                         p1, pt, max(1, SP(2)))
        pygame.draw.line(window, tone(shade(wood, (1, 0, 0)), 0.8),
                         p2, pt, max(1, SP(2)))
    if not v["lit"]:
        return
    # пламя: четыре яруса, мерцание плавное (синусы, не случайный снег)
    flick = (1 + 0.14 * math.sin(VIL_T * 7.3) + 0.09 * math.sin(VIL_T * 17.7))
    _LCRS = ((166, 44, 10, 150, 1.30, 0.30),
             (255, 96, 18, 190, 1.00, 0.55),
             (255, 166, 42, 220, 0.66, 0.80),
             (255, 236, 122, 235, 0.38, 1.05))
    night = clamp((0.6 - LIGHT["amb"]) / 0.35, 0.0, 1.0)
    R = 0.16 * (TILE_W / 2) * ze * flick
    tall = R * 2.4
    for cr, cg, cb, ca, cs, yoff in _LCRS:
        rr = R * cs
        cx_ = c0[0] + 0.14 * R * math.sin(VIL_T * 3.1 + yoff * 5)
        tip_y = c0[1] - tall * yoff
        pts = [(cx_, tip_y + rr * 0.9), (cx_ - rr * 0.62, tip_y),
               (cx_ + rr * 0.62, tip_y)]
        pygame.draw.polygon(window, (cr, cg, cb), pts)
    if R > 3:
        pygame.draw.circle(window, (255, 250, 235),
                           (int(c0[0]), int(c0[1] - tall * 0.18)),
                           max(1, int(R * 0.3)))
    if night > 0.2:  # отсвет на земле
        gr = int(R * (2.2 + 2.4 * night) * flick)
        if gr > 3:
            s = pygame.Surface((gr * 2 + 2, gr + 4), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (255, 150, 50, int(60 * night * flick)),
                                s.get_rect())
            window.blit(s, (int(c0[0]) - gr - 1, int(c0[1]) - gr // 2))


_GLOW_C = {}


def _radial_glow(key, radius, color, alpha):
    surf = _GLOW_C.get(key)
    if surf is None:
        r = max(4, int(radius))
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for rr in range(r, 0, -2):
            a = int(alpha * (1.0 - rr / r) ** 1.6)
            pygame.draw.circle(surf, (color[0], color[1], color[2], a),
                               (r, r), rr)
        _GLOW_C[key] = surf
    return surf


def draw_village(window, cam, frame):
    """Поселение: жерди, костёр, хижины, люди (по глубине)."""
    v = VIL
    if v is None:
        return
    ctx = _proj_ctx(cam)
    ze = ctx[3]
    items = []
    for s in v["sticks"]:
        sx, sy = cam.world_to_screen(s["x"], s["y"], s["z"])
        if sx < -40 or sy < -40 or sx > cam.win_w + 40 or sy > cam.win_h + 40:
            continue
        items.append((s["x"] + s["y"], 0, ("stick", s, sx, sy)))
    for lg in v["logs"]:
        if not lg.get("placed") or lg.get("owner") is not None:
            continue
        sx, sy = cam.world_to_screen(lg["x"], lg["y"], lg["z"])
        if sx < -40 or sy < -40 or sx > cam.win_w + 40 \
                or sy > cam.win_h + 40:
            continue
        items.append((lg["x"] + lg["y"], 0, ("log", lg, sx, sy)))
    for sp in v.get("stones_placed", ()):
        sx, sy = cam.world_to_screen(sp["x"], sp["y"],
                                     _vil_gz(sp["x"], sp["y"]))
        if sx < -40 or sy < -40 or sx > cam.win_w + 40 \
                or sy > cam.win_h + 40:
            continue
        items.append((sp["x"] + sp["y"], 0, ("stonep", sp, sx, sy)))
    for s2 in v.get("pebbles", ()):
        if s2["owner"] is not None:
            continue
        sx, sy = cam.world_to_screen(s2["x"], s2["y"], s2["z"])
        if sx < -40 or sy < -40 or sx > cam.win_w + 40 \
                or sy > cam.win_h + 40:
            continue
        items.append((s2["x"] + s2["y"], 0, ("pebble", s2, sx, sy)))
    fx, fy = v["fire"]
    items.append((fx + fy, 0, ("fire", None, None, None)))
    # кровь: рисуем под всеми предметами
    for b in v["blood"]:
        bx, by = b["x"], b["y"]
        sx, sy = cam.world_to_screen(bx, by, _vil_gz(bx, by))
        if sx < -40 or sy < -40 or sx > cam.win_w + 40 or sy > cam.win_h + 40:
            continue
        gr = min(1.0, b["t"] * 2.0)
        fade = max(0.3, 1.0 - max(0.0, b["t"] - 45.0) / 45.0)
        rr = max(2, int(b["r"] * 30.0 * ze * (0.45 + 0.55 * gr)))
        col = (int(118 * fade), int(16 * fade), int(15 * fade))
        pygame.draw.ellipse(window, col,
                            (sx - rr, sy - rr // 3, rr * 2,
                             rr * 2 // 3 + 1))
        if b["big"]:
            for k in range(5):
                a2 = hash01(k, int(bx * 13), int(by * 13)) * 6.283
                d2 = rr * (0.8 + hash01(k, 7, 1) * 0.5)
                pygame.draw.ellipse(window, col,
                                    (sx + math.cos(a2) * d2 - rr // 4,
                                     sy + math.sin(a2) * d2 / 3 - rr // 8,
                                     rr // 2, rr // 4 + 1))
    for hum in v["workers"]:
        sx, sy = cam.world_to_screen(hum["x"], hum["y"], hum["z"])
        if sx < -60 or sy < -60 or sx > cam.win_w + 60 or sy > cam.win_h + 60:
            continue
        items.append((hum["x"] + hum["y"], 1, ("hum", hum, sx, sy)))
    items.sort(key=lambda t: t[0])
    night = clamp((0.6 - LIGHT["amb"]) / 0.35, 0.0, 1.0)
    for _, _, (kind, payload, sx, sy) in items:
        if kind == "stick":
            s = payload
            ze2 = ctx[3]
            dxw = math.cos(s["ang"]) * 0.22
            dyw = math.sin(s["ang"]) * 0.16
            p1 = cam.world_to_screen(s["x"], s["y"], s["z"] + 0.02)
            p2 = cam.world_to_screen(s["x"] + dxw, s["y"] + dyw, s["z"] + 0.05)
            if s["falling"]:
                shx, shy = cam.world_to_screen(s["x"], s["y"],
                                               _vil_gz(s["x"], s["y"]))
                pygame.draw.ellipse(window, tone(shade(GRASS, PZ), 0.5),
                                    (shx - 3, shy - 1, 6, 3))
            pygame.draw.line(window, tone(shade(BASE_COLORS["wood_dark"],
                                                PZ), 0.95),
                             p1, p2, max(1, SP(2) if ze2 > 0.5 else 1))
        elif kind == "log":
            lg = payload
            dxw = math.cos(lg.get("ang", 0.0)) * 0.26
            dyw = math.sin(lg.get("ang", 0.0)) * 0.18
            p1 = cam.world_to_screen(lg["x"] - dxw / 2,
                                     lg["y"] - dyw / 2, lg["z"] + 0.05)
            p2 = cam.world_to_screen(lg["x"] + dxw / 2,
                                     lg["y"] + dyw / 2, lg["z"] + 0.05)
            pygame.draw.line(window,
                             tone(shade(BASE_COLORS["wood_light"], PZ), 0.85),
                             p1, p2, max(2, SP(3) if ze > 0.5 else 2))
            pygame.draw.line(window,
                             tone(shade(BASE_COLORS["wood_dark"], PZ), 0.8),
                             (p1[0], p1[1] + 1), (p2[0], p2[1] + 1),
                             max(1, SP(1)))
        elif kind in ("stonep", "pebble"):
            sp = payload
            rr = max(2, int((0.09 if kind == "stonep" else 0.06)
                            * (TILE_W / 2) * ze))
            cc = shade(BASE_COLORS["gray"], (0, 1, 0.3))
            pygame.draw.ellipse(window, cc,
                                (sx - rr, sy - rr // 2, rr * 2, rr))
        elif kind == "fire":
            _vil_draw_fire(window, cam, ctx)
        else:
            hum = payload
            moving = hum["state"] in ("walk", "run")
            if moving:
                hum["ph"] += (9.0 if hum["carry"] or
                              math.hypot(hum["tx"] - hum["x"],
                                         hum["ty"] - hum["y"]) > 6
                              else 6.0) * (1 / 60.0)
            else:
                hum["ph"] += 1.6 / 60.0
            S = max(6, int(round(TILE_Z * ze * 0.55)))  # мелкие, детализированные
            spd = 2.3 if (hum["carry"] or
                          math.hypot(hum["tx"] - hum["x"],
                                     hum["ty"] - hum["y"]) > 6) else 1.5
            pose = _hum_pose(hum, moving, spd)
            spr = _hum_sprite(pose, hum, S, hum["flip"])
            if pose == "dead":
                window.blit(spr, (int(sx - spr.get_width() / 2),
                                  int(sy - spr.get_height() / 2)))
            else:
                shw = max(4, int(S * 0.4))
                pygame.draw.ellipse(window, tone(shade(GRASS, PZ), 0.55),
                                    (sx - shw // 2, sy - shw // 6, shw,
                                     max(2, shw // 3)))
                window.blit(spr, (int(sx - spr.get_width() / 2),
                                  int(sy - spr.get_height())))
            if pose == "light" and hum["state"] == "light":
                # искра у кончиков пальцев
                k = 0.5 + 0.5 * math.sin(VIL_T * 21)
                pygame.draw.circle(window, (255, 220 + int(35 * k), 120),
                                   (int(sx + spr.get_width() * 0.28),
                                    int(sy - spr.get_height() * 0.55)),
                                   max(1, S // 9))
            if hum.get("carry_log"):
                p1 = cam.world_to_screen(hum["x"] - 0.06, hum["y"] - 0.04,
                                        hum["z"] + 0.30)
                p2 = cam.world_to_screen(hum["x"] + 0.13, hum["y"] + 0.07,
                                        hum["z"] + 0.26)
                pygame.draw.line(window,
                                 tone(shade(BASE_COLORS["wood_light"], PZ),
                                      0.9), p1, p2, max(2, S // 6))
            if hum.get("carry_sp"):
                pygame.draw.circle(
                    window, shade(BASE_COLORS["gray"], (0, 1, 0.3)),
                    (int(sx + S * 0.16), int(sy - S * 0.35)),
                    max(1, S // 9))
            nightv = clamp((0.6 - LIGHT["amb"]) / 0.35, 0.0, 1.0)
            if hum.get("torch") and nightv > 0.25:
                fx2 = int(sx + S * 0.17)
                fy2 = int(sy - spr.get_height() * 0.52)
                pygame.draw.circle(window, (255, 190, 80), (fx2, fy2),
                                   max(1, S // 10))
                pygame.draw.circle(window, (255, 130, 45), (fx2, fy2 + 1),
                                   max(1, S // 14))
                gl = _radial_glow(("torch", S), S * 2, (255, 150, 50), 30)
                window.blit(gl, (fx2 - gl.get_width() // 2,
                                 fy2 - gl.get_height() // 2))
    if v["defeat"] is not None:
        f_big = pygame.font.Font(None, 54)
        f_sm = pygame.font.Font(None, 24)
        t1 = f_big.render("ПОРАЖЕНИЕ", True, (214, 58, 46))
        t2 = f_sm.render("Племя вымерло — R: новое поселение",
                         True, (240, 240, 244))
        window.blit(t1, (cam.win_w / 2 - t1.get_width() / 2,
                         cam.win_h * 0.28))
        window.blit(t2, (cam.win_w / 2 - t2.get_width() / 2,
                         cam.win_h * 0.28 + 46))


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------
def make_icon():
    icon = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.polygon(icon, (240, 200, 90), [(8, 1), (14, 4), (8, 7), (2, 4)])
    pygame.draw.polygon(icon, (120, 40, 38), [(2, 4), (8, 7), (8, 14), (2, 11)])
    pygame.draw.polygon(icon, (168, 58, 50), [(8, 7), (14, 4), (14, 11), (8, 14)])
    return icon


class HUD:
    def __init__(self):
        self.font_big = pygame.font.Font(None, 38)
        self.font = pygame.font.Font(None, 26)
        self.font_small = pygame.font.Font(None, 23)
        self._tcache = {}
        self._panel = None
        self._panel_key = None
        self._helpbg = None
        self._helpbg_key = None
        self._windbg = None
        self._windbg_key = None
        self._fps_key = None
        self._fps_surf = None

    def text(self, window, s, pos, color=(235, 235, 240), font=None):
        f = font or self.font
        key = (s, color, id(f))
        surf = self._tcache.get(key)
        if surf is None:
            if len(self._tcache) > 250:
                self._tcache.clear()
            surf = f.render(s, True, color)
            self._tcache[key] = surf
        window.blit(surf, pos)
        return surf.get_height()

    def draw(self, window, cam, objects, pixels, fps, hover_tile, show_help,
             preset_idx, blast_mode):
        # Только маленький аккуратный FPS в левом верхнем углу — без подсказок.
        fps_i = int(round(fps))
        if self._fps_key != fps_i:
            t = self.font_small.render(f"FPS {fps_i}", True, (214, 222, 235))
            panel = pygame.Surface((t.get_width() + 10, t.get_height() + 6),
                                   pygame.SRCALPHA)
            panel.fill((10, 12, 18, 140))
            panel.blit(t, (5, 3))
            self._fps_key, self._fps_surf = fps_i, panel
        window.blit(self._fps_surf, (8, 6))


def save_screenshot(window, name=None):
    if name is None:
        name = "screenshot_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
    pygame.image.save(window, name)
    print(f"[скриншот] сохранён в {name}")
    return name


# ---------------------------------------------------------------------------
# Главный цикл
# ---------------------------------------------------------------------------
def main():
    global BLAST_POWER, PIXEL, ANIM_T, CLOUD_OFF, DAY_PAUSE
    pygame.init()
    pygame.display.set_caption("Пиксельный прототип — изометрия (этап 9)")
    pygame.display.set_icon(make_icon())
    init_audio()

    def make_window(w=None, h=None):
        """Безрамочный полный экран (размер рабочего стола), с откатами."""
        if TEST_MODE:
            return pygame.display.set_mode((WINDOW_W, WINDOW_H))
        if w is None or h is None:
            info = pygame.display.Info()
            w, h = info.current_w or WINDOW_W, info.current_h or WINDOW_H
        try:
            return pygame.display.set_mode((w, h),
                                           pygame.FULLSCREEN | pygame.NOFRAME)
        except pygame.error:
            pass
        try:
            return pygame.display.set_mode((w, h), pygame.FULLSCREEN)
        except pygame.error:
            return pygame.display.set_mode((w, h), pygame.RESIZABLE)

    window = make_window()

    clock = pygame.time.Clock()
    cam = Camera()
    cam.update_win_size(window.get_size()[0] // PIXEL,
                        window.get_size()[1] // PIXEL)
    home_cam(cam)
    reset_ground()
    objects = make_test_scene()
    pixels = []
    village_reset(objects)
    hud = HUD()
    set_preset(1)
    world = {"w": 0, "h": 0, "surf": None}

    def ensure_world():
        ww = max(160, window.get_size()[0] // PIXEL)
        hh = max(120, window.get_size()[1] // PIXEL)
        if world["surf"] is None or (ww, hh) != (world["w"], world["h"]):
            world["w"], world["h"] = ww, hh
            world["surf"] = pygame.Surface((ww, hh)).convert()
            return True
        return False

    ensure_world()
    shadow_layer = pygame.Surface((world["w"], world["h"]), pygame.SRCALPHA)

    show_checker = False
    show_help = True
    save_after_draw = False
    blast_mode = True

    dragging = False
    drag_button = None
    down_pos = (0, 0)
    moved = False
    last_mouse = (0, 0)
    island_mask = {"key": None, "surf": None}
    static_cache = {"key": None, "surf": None}
    zoom_track = {"value": cam.zoom, "stable": 99}
    _BUILD = None  # поэтапная сборка холста (смена шага света)

    def mask_shadow_layer():
        key = ((cam.win_w, cam.win_h), round(cam.zoom, 3), cam.rot,
               round(cam.x, 1), round(cam.y, 1))
        if island_mask["key"] != key:
            w0, h0 = cam.win_w, cam.win_h
            m = pygame.Surface((w0, h0), pygame.SRCALPHA)
            c = [cam.world_to_screen(0, 0, 0), cam.world_to_screen(GRID_W, 0, 0),
                 cam.world_to_screen(GRID_W, GRID_D, 0),
                 cam.world_to_screen(0, GRID_D, 0)]
            pygame.draw.polygon(m, (255, 255, 255, 255), c)
            island_mask["key"], island_mask["surf"] = key, m
        shadow_layer.blit(island_mask["surf"], (0, 0),
                          special_flags=pygame.BLEND_RGBA_MULT)

    def _build_begin(bigw, bigh, cox, coy, checker):
        """Старт поэтапной сборки нового холста (показывается, когда готов)."""
        _sx, _sy, _shx, _shy = cam.x, cam.y, cam.shx, cam.shy
        cam.x, cam.y = cox, coy
        cam.shx = cam.shy = 0.0
        cam.update_win_size(bigw, bigh)
        x0, x1, y0, y1 = _visible_tile_range(cam)
        tiles = list(_ordered_tiles(x0, x1, y0, y1, cam.rot))
        # Крупные этапы давали 40–95 мс на одном кадре. Делим
        # работу на мелкие задачи; старый готовый холст виден до конца.
        # A crater tile is roughly 100x more expensive than an ordinary tile
        # (16 little plates plus debris).  Count work, not merely tiles, so a
        # whole crater never lands in one or two unlucky frames.
        ground_jobs, ground_chunk, ground_cost = [], [], 0
        for tile in tiles:
            tile_cost = 100 if (tile in DENTED or tile in _RIMTILES) else 1
            if ground_chunk and ground_cost + tile_cost > 300:
                ground_jobs.append(ground_chunk)
                ground_chunk, ground_cost = [], 0
            ground_chunk.append(tile)
            ground_cost += tile_cost
        if ground_chunk:
            ground_jobs.append(ground_chunk)
        # SDL/Windows reserves large surfaces cheaply, but commits their pages
        # on the first write.  Touching the whole 15-25 MB canvas from the
        # first ground chunk used to turn that otherwise small job into a
        # 35-55 ms frame.  Commit both canvases in narrow strips instead.
        touch_h = max(1, (bigh + 23) // 24)
        touch_jobs = [("static_touch", (y, min(touch_h, bigh - y)))
                      for y in range(0, bigh, touch_h)]
        jobs = [("static_init", None)] + touch_jobs + [("base", None)]
        if cam.zoom >= 0.35:
            # A cold light/zoom cache needs up to 20 NumPy-generated ground
            # sprites.  Generating them lazily in the first two tile chunks
            # caused a pair of 35-50 ms frames after an explosion.
            jobs += [("ground_prewarm", (var, hlev))
                     for var in range(4) for hlev in range(5)]
        jobs += [("ground", chunk) for chunk in ground_jobs]
        jobs.append(("shadow_init", None))
        jobs += [("shadow_touch", (y, min(touch_h, bigh - y)))
                 for y in range(0, bigh, touch_h)]
        shadow_n = max(1, (len(objects) + 15) // 16)
        jobs += [("shadow", objects[i:i + shadow_n])
                 for i in range(0, len(objects), shadow_n)]
        jobs.append(("shadow_mask", None))
        jobs.append(("shadow_composite", None))
        if cam.zoom < 0.6 and not checker:
            # Sorting/culling all objects is itself sizeable.  Make planning
            # a build job too, instead of doing it on the click/zoom frame.
            jobs.append(("objects_plan", None))
        elif not checker:
            jobs.append(("trees_plan", None))
        cam.update_win_size(world["w"], world["h"])
        cam.x, cam.y = _sx, _sy
        cam.shx, cam.shy = _shx, _shy
        return {"st": None, "sh": None,
                "scratch": pygame.Surface((1, 1), pygame.SRCALPHA),
                "i": 0, "jobs": jobs,
                "params": (bigw, bigh, cox, coy, checker),
                "guard": 0}

    def _build_step(li, newkey):
        nonlocal shadow_layer, _BUILD
        global _SHADOW_ARR
        B = _BUILD
        bigw, bigh, bo, by, checker = B["params"]
        bst, bsh = B["st"], B["sh"]
        _sx, _sy, _shx, _shy = cam.x, cam.y, cam.shx, cam.shy
        cam.x, cam.y = bo, by
        cam.shx = cam.shy = 0.0
        cam.update_win_size(bigw, bigh)
        kind, payload = B["jobs"][B["i"]]
        if kind == "static_init":
            bst = pygame.Surface((bigw, bigh), pygame.SRCALPHA)
            B["st"] = bst
        elif kind == "static_touch":
            y, hh = payload
            bst.fill((0, 0, 0, 0), (0, y, bigw, hh))
        elif kind == "base":
            draw_island_sides(bst, cam)
            _paint_ground_base(bst, cam)
        elif kind == "ground_prewarm":
            var, hlev = payload
            ov = 2 + int(cam.zoom * 3)
            sw = max(2, int(round(TILE_W * cam.zoom / PIXEL))) + ov
            sh = max(1, int(round(TILE_H * cam.zoom / PIXEL))) + ov
            ground_sprite("grass", var, sw, sh, li, cam.rot, hlev)
        elif kind == "ground":
            draw_ground(bst, cam, checker, li, only=payload)
        elif kind == "shadow_init":
            bsh = pygame.Surface((bigw, bigh), pygame.SRCALPHA)
            B["sh"] = bsh
        elif kind == "shadow_touch":
            y, hh = payload
            bsh.fill((0, 0, 0, 0), (0, y, bigw, hh))
        elif kind == "shadow":
            draw_shadows(bsh, cam, payload)
        elif kind == "shadow_mask":
            _mkey = ((bigw, bigh), round(cam.zoom, 3), cam.rot,
                     round(bo, 1), round(by, 1))
            if island_mask["key"] != _mkey:
                m = pygame.Surface((bigw, bigh), pygame.SRCALPHA)
                c = [cam.world_to_screen(0, 0, 0),
                     cam.world_to_screen(GRID_W, 0, 0),
                     cam.world_to_screen(GRID_W, GRID_D, 0),
                     cam.world_to_screen(0, GRID_D, 0)]
                pygame.draw.polygon(m, (255, 255, 255, 255), c)
                island_mask["key"], island_mask["surf"] = _mkey, m
            bsh.blit(island_mask["surf"], (0, 0),
                     special_flags=pygame.BLEND_RGBA_MULT)
        elif kind == "shadow_composite":
            bst.blit(bsh, (0, 0))
        elif kind == "objects":
            _draw_render_items(bst, cam, payload, li)
        elif kind == "objects_plan":
            prune_object_sprites(objects)
            render_items = _collect_render_items(cam, objects, [])
            B["jobs"][B["i"] + 1:B["i"] + 1] = [
                ("objects", render_items[i:i + 8])
                for i in range(0, len(render_items), 8)]
        elif kind == "trees_plan":
            render_items = _collect_render_items(cam, objects, [])
            tree_items = [it for it in render_items
                          if it[2] == 0 and it[3].get("shape") == "tree"]
            B["jobs"][B["i"] + 1:B["i"] + 1] = [
                ("prewarm_trees", tree_items[i:i + 4])
                for i in range(0, len(tree_items), 4)]
        elif kind == "prewarm_trees":
            _draw_render_items(B["scratch"], cam, payload, li)
        cam.update_win_size(world["w"], world["h"])
        cam.x, cam.y = _sx, _sy
        cam.shx, cam.shy = _shx, _shy
        B["i"] += 1
        B["guard"] += 1
        if B["i"] >= len(B["jobs"]):
            static_cache["key"] = newkey
            static_cache["surf"] = bst
            static_cache["big"] = (bigw, bigh)
            static_cache["ox"], static_cache["oy"] = bo, by
            static_cache["sh"] = (0, 0)
            static_cache["zoom"] = cam.zoom
            shadow_layer = bsh
            _SHADOW_ARR = bsh
            _STATIC_REQ["full"] = False
            _CRATER_TILES.clear()
            _BUILD = None
        elif B["guard"] > len(B["jobs"]) + 8:
            _BUILD = None  # страховка: сброс, полный перестрой дальше

    def _blit_static_preview(dst, st, w, h):
        """Пока холст нового zoom собирается, показать старый в точной
        аффинной проекции. Масштабируется только видимый crop, а не
        многомегабайтный холст целиком.
        """
        cbw, cbh = static_cache["big"]
        ox, oy = static_cache["ox"], static_cache["oy"]
        sh0, sh1 = static_cache.get("sh", (0, 0))
        old_zoom = static_cache.get("zoom", cam.zoom)
        ratio = cam.zoom / max(1e-6, old_zoom)
        full_x = (w / 2 + cam.x + cam.shx
                  - ratio * (cbw / 2 + ox + sh0))
        full_y = (h / 2 - _OFFY_K + cam.y + cam.shy
                  - ratio * (cbh / 2 - _OFFY_K + oy + sh1))
        if abs(ratio - 1.0) < 1e-5:
            dst.blit(st, (round(full_x), round(full_y)))
            return full_x, full_y, 1.0
        sx0 = max(0, int(math.floor(-full_x / ratio)) - 1)
        sy0 = max(0, int(math.floor(-full_y / ratio)) - 1)
        sx1 = min(cbw, int(math.ceil((w - full_x) / ratio)) + 1)
        sy1 = min(cbh, int(math.ceil((h - full_y) / ratio)) + 1)
        if sx1 > sx0 and sy1 > sy0:
            rect = pygame.Rect(sx0, sy0, sx1 - sx0, sy1 - sy0)
            crop = st.subsurface(rect)
            dw = max(1, int(round(rect.w * ratio)))
            dh = max(1, int(round(rect.h * ratio)))
            scaled = pygame.transform.scale(crop, (dw, dh))
            dst.blit(scaled, (round(full_x + sx0 * ratio),
                              round(full_y + sy0 * ratio)))
        return full_x, full_y, ratio

    def render_all(fps, frame, mpos=None, hud_hover=None):
        global _SHADOW_ARR, _STATIC_OFF, _STATIC_SCALE
        nonlocal shadow_layer, _BUILD
        w, h = world["w"], world["h"]
        surf = world["surf"]
        cam.update_win_size(w, h)
        if abs(cam.zoom - zoom_track["value"]) > 1e-6:
            zoom_track["value"] = cam.zoom
            zoom_track["stable"] = 0
        else:
            zoom_track["stable"] += 1
        update_sun_screen(cam)
        li = _day_step()  # шаг запечённого света для кэшей
        surf.blit(make_sky(w, h), (0, 0))
        if LIGHT.get("star_a", 0.0) > 0.01:
            draw_stars(surf, w, h, frame)
        draw_disc(surf, w, h)
        # статичный слой: остров + земля + тени. Холст центрирован на острове
        # (панорамирование по острову без перестроя) либо на камере вдали.
        qx, qy = cam.x, cam.y
        key = (w, h, round(cam.zoom, 3), cam.rot, qx, qy,
               li, show_checker, STATIC_VER)
        _bigw, _bigh, _cox, _coy = _static_canvas_params(cam, w, h)
        st = static_cache["surf"]
        _ok2 = static_cache["key"]
        _same_core = (_ok2 is not None and _ok2[:4] == key[:4]
                      and _ok2[6:] == key[6:])
        _geom_same = (st is not None and st.get_size() == (_bigw, _bigh)
                      and static_cache.get("ox") == _cox
                      and static_cache.get("oy") == _coy)
        _stbig = static_cache.get("big")
        _covers_canvas = (_stbig is not None
                          and abs(qx - static_cache["ox"])
                          <= _stbig[0] / 2 - w / 2
                          and abs(qy - static_cache["oy"])
                          <= _stbig[1] / 2 - h / 2)
        _in_canvas = _same_core and _covers_canvas
        _incr = None
        if (not _STATIC_REQ["full"] and _same_core and _in_canvas
                and st is not None and st.get_size() == (_bigw, _bigh)
                and _CRATER_TILES):
            _tiles = set()
            _far = cam.zoom < 0.35 and not show_checker
            for _tx, _ty in _CRATER_TILES:
                for _ix in range(_tx - 1, _tx + 2):
                    for _iy in range(_ty - 1, _ty + 2):
                        if 0 <= _ix < GRID_W and 0 <= _iy < GRID_D:
                            _tiles.add((_ix, _iy))
            if _far or show_checker or any(_x == _y for _x, _y in _tiles):
                _STATIC_REQ["full"] = True
            else:
                _incr = _tiles
        # смена шага света (только li): холст собирается поэтапно,
        # старый показывается до готовности — без провисаний FPS
        if _BUILD is not None:
            _bp = _BUILD["params"]
            _b_in = (abs(qx - _bp[2]) <= _bp[0] / 2 - w / 2
                     and abs(qy - _bp[3]) <= _bp[1] / 2 - h / 2)
            _abort = (_bp[0] != _bigw or _bp[1] != _bigh
                      or _bp[2] != _cox or _bp[3] != _coy
                      or _bp[4] != show_checker
                      or _STATIC_REQ["full"] or not _b_in)
            if _abort:
                _BUILD = None  # геометрия/мир изменились — прерываем
            else:
                _build_step(li, key)
        if _BUILD is None:
            # свежее состояние кэша (сборка могла завершиться в этом кадре)
            st = static_cache["surf"]
            _ok2 = static_cache["key"]
            _same_core = (_ok2 is not None and _ok2[:4] == key[:4]
                          and _ok2[6:] == key[6:])
            _geom_same = (st is not None
                          and st.get_size() == (_bigw, _bigh)
                          and static_cache.get("ox") == _cox
                          and static_cache.get("oy") == _coy)
            _stbig = static_cache.get("big")
            _covers_canvas = (_stbig is not None
                              and abs(qx - static_cache["ox"])
                              <= _stbig[0] / 2 - w / 2
                              and abs(qy - static_cache["oy"])
                              <= _stbig[1] / 2 - h / 2)
            _in_canvas = _same_core and _covers_canvas
            if (_STATIC_REQ["full"] or st is None
                    or st.get_size() != (_bigw, _bigh)
                    or not _same_core or not _in_canvas):
                _view_compatible = (_ok2 is not None
                                    and _ok2[0:2] == key[0:2]
                                    and _ok2[3] == key[3])
                _zoom_changed = (_ok2 is not None and _ok2[2] != key[2])
                _can_stage = (st is not None and _view_compatible
                              and (_covers_canvas or _zoom_changed)
                              and _bigw > w + 256 and _bigh > h + 256
                              and not show_checker and not TEST_MODE)
                if (_zoom_changed and _view_compatible
                        and zoom_track["stable"] < 3):
                    # Колесо ещё крутится: показываем масштабированный
                    # preview и не выделяем десятки МБ под заведомо устаревающую сборку.
                    st = static_cache["surf"]
                elif _can_stage:
                    _BUILD = _build_begin(_bigw, _bigh, _cox, _coy,
                                          show_checker)
                    # Запрос, из-за которого стартовала эта сборка,
                    # поглощён. Новое изменение мира снова поднимет флаг
                    # и безопасно прервёт устаревшую сборку.
                    _STATIC_REQ["full"] = False
                    st = static_cache["surf"]
                else:
                    st = pygame.Surface((_bigw, _bigh), pygame.SRCALPHA)
                    if shadow_layer.get_size() != (_bigw, _bigh):
                        shadow_layer = pygame.Surface((_bigw, _bigh),
                                                       pygame.SRCALPHA)
                    _sx, _sy = cam.x, cam.y
                    cam.x, cam.y = _cox, _coy
                    cam.update_win_size(_bigw, _bigh)
                    draw_island_sides(st, cam)
                    _paint_ground_base(st, cam)
                    draw_ground(st, cam, show_checker, li)
                    shadow_layer.fill((0, 0, 0, 0))
                    draw_shadows(shadow_layer, cam, objects)
                    mask_shadow_layer()
                    st.blit(shadow_layer, (0, 0))
                    if cam.zoom < 0.6 and not show_checker:
                        draw_objects_and_pixels(st, cam, objects, [], li)
                    cam.update_win_size(w, h)
                    cam.x, cam.y = _sx, _sy
                    _SHADOW_ARR = shadow_layer
                    static_cache["key"], static_cache["surf"] = key, st
                    static_cache["big"] = (_bigw, _bigh)
                    static_cache["ox"], static_cache["oy"] = _cox, _coy
                    static_cache["sh"] = (round(cam.shx), round(cam.shy))
                    static_cache["zoom"] = cam.zoom
                    _STATIC_REQ["full"] = False
                    _CRATER_TILES.clear()
        elif _incr is not None and _BUILD is None:
            _ox, _oy = static_cache["ox"], static_cache["oy"]
            _cb = static_cache["big"]
            _sx, _sy = cam.x, cam.y
            cam.x, cam.y = _ox, _oy
            cam.update_win_size(_cb[0], _cb[1])
            draw_ground(st, cam, show_checker, li, only=_incr)
            cam.x, cam.y = _sx, _sy
            cam.update_win_size(w, h)
            _CRATER_TILES.clear()
        _offx, _offy, _scale = _blit_static_preview(surf, st, w, h)
        _STATIC_OFF = (_offx, _offy)
        _STATIC_SCALE = _scale
        if VIL is not None and VIL.get("wear"):
            _draw_village_paths(surf, cam, VIL["wear"])
        _render_zoom = (static_cache.get("zoom", cam.zoom)
                        if _BUILD is not None else cam.zoom)
        if _render_zoom < 0.6 and not show_checker:
            draw_objects_and_pixels(surf, cam, [], pixels, li)
        else:
            draw_objects_and_pixels(surf, cam, objects, pixels, li)
        draw_edge_glow(surf, w, h, frame)
        draw_fx(surf, cam)
        if mpos:
            hover_tile = draw_hover(surf, cam, objects, mpos, blast_mode,
                                    BLAST_POWER)
        else:
            hover_tile = hud_hover
        if PLACE["tpl"] is not None and mpos is not None:
            _wx, _wy = cam.screen_to_world(mpos[0], mpos[1], 0)
            for _ in range(3):
                _gz = ground_height_at(_wx, _wy)
                if _gz is None:
                    break
                _wx, _wy = cam.screen_to_world(mpos[0], mpos[1], _gz)
            draw_ghost(surf, cam, PLACE["tpl"], PLACE["rot"], _wx, _wy)
        draw_fir_overlay(surf, cam, objects, w, h)
        draw_village(surf, cam, frame)
        # scale() умеет писать сразу в display Surface: без
        # полноэкранной временной копии и ещё одного blit.
        pygame.transform.scale(surf, window.get_size(), window)
        hud.draw(window, cam, objects, pixels, fps, hover_tile, show_help,
                 li, blast_mode)
        if PALETTE["open"]:
            PALETTE["rects"] = draw_palette(
                window, hud, make_building_library(), pygame.mouse.get_pos())
        return hover_tile

    running = True
    frame = 0
    village_acc = 0.0

    if BENCH_MODE:
        # замер стоимости реального рендера: сценарии A/B/C/E
        rng.seed(7)
        wind_rng.seed(20260917)
        WIND.update(ang=0.8, str=0.35, t_ang=0.8, t_str=0.35,
                    next=10.0, t=0.0, kick=0.0, wx=1.0, wy=0.6, mag=0.4)
        ANIM_T = 0.0
        CLOUD_OFF = 0.0

        def _bench_render(i):
            render_all(60, i)
            pygame.display.flip()

        def _bench(name, n, prep=None, step=None):
            import time as _t
            if prep is not None:
                prep()
            for _ in range(30):  # прогрев
                _bench_render(_)
            t0 = _t.perf_counter()
            worst = 0.0
            for i in range(n):
                if step is not None:
                    step(i)
                _bb = (None if _BUILD is None else
                       (_BUILD["i"], _BUILD["jobs"][_BUILD["i"]][0]))
                ft = _t.perf_counter()
                _bench_render(i)
                _dtf = (_t.perf_counter() - ft) * 1000.0
                if _dtf > 25.0:
                    _bi = _BUILD["i"] if _BUILD else None
                    print(f"  [slow] {name} frame {i}: {_dtf:.1f} ms "
                          f"build={_bb}->{_bi}")
                worst = max(worst, _dtf)
            avg = (_t.perf_counter() - t0) * 1000.0 / n
            print(f"BENCH {name:20s} avg {avg:7.2f} ms/frame "
                  f"({1000 / avg:6.1f} fps)  worst {worst:7.2f} ms")
            return avg, worst

        def _prep_a():
            home_cam(cam)

        def _prep_b():
            home_cam(cam)
            cam.zoom = 1.2
            home_cam(cam)

        def _prep_c():
            home_cam(cam)
            cam.x -= 400.0  # старт с края, длинный пролёт через остров
            cam.y -= 160.0

        def _step_c(i):
            cam.x += 2.5
            cam.y += 1.2

        def _prep_e():
            home_cam(cam)
            set_preset(0)

        def _prep_zoom():
            home_cam(cam)

        def _step_zoom(i):
            # 360 кадров непрерывного wheel/pinch + пауза, за
            # которую фоновый холст должен начать достраиваться.
            if i < 360:
                target = 0.62 + 0.32 * math.sin(i * 0.055)
                cam.zoom_at(cam.win_w / 2, cam.win_h / 2,
                            target / cam.zoom)

        _bench("A far static", 300, prep=_prep_a)
        _bench("B mid static", 300, prep=_prep_b)
        _bench("C panning island", 500, prep=_prep_c, step=_step_c)
        _bench("D continuous zoom", 600, prep=_prep_zoom, step=_step_zoom)
        _bench("E day/night", 1200, prep=_prep_e,
               step=lambda i: update_daytime(
                   (DAY_LEN / 72.0) / 200.0 * 1.05))
        print(f"BENCH objects={len(objects)} window={window.get_size()}")
        running = False


    if TEST_MODE:
        rng.seed(7)
        wind_rng.seed(20260917)
        WIND.update(ang=0.8, str=0.35, t_ang=0.8, t_str=0.35,
                    next=10.0, t=0.0, kick=0.0, wx=1.0, wy=0.6,
                    mag=0.4)
        ANIM_T = 0.0
        CLOUD_OFF = 0.0

    while running:
        dt = 1 / 60 if TEST_MODE else min(clock.tick(0) / 1000.0, 0.05)
        frame += 1
        fps = clock.get_fps()

        # ---------------- крупный план моделей ----------------
        if CLOSEUP_MODE:
            if frame == 1:
                _CU_FULL = make_test_scene(keep_buildings=True)
                objects = list(_CU_FULL)
                pixels.clear()
                reset_ground()
            cids = [8, 9, 10, 12, 67, 72]
            cid = cids[(frame - 2) // 2] if frame <= 13 else None
            if frame in (2, 4, 6, 8, 10, 12):
                objects = [o for o in _CU_FULL
                           if o.get("house") is None
                           or o.get("house") == cid]
                bump_world()
                _pts = [o for o in objects if o.get("house") == cid]
                if _pts:
                    _cx = sum(o["x"] + o["w"] / 2 for o in _pts) / len(_pts)
                    _cy = sum(o["y"] + o["d"] / 2 for o in _pts) / len(_pts)
                    cam.zoom = 4.5
                    cam.x = 0.0
                    cam.y = 0.0
                    _px, _py = cam.world_to_screen(_cx, _cy, 0.3)
                    cam.x = world["w"] / 2 - _px
                    cam.y = world["h"] * 0.45 - _py
            render_all(60, frame)
            pygame.display.flip()
            if frame in (3, 5, 7, 9, 11, 13):
                save_screenshot(window, "cu_h%d.png" % cids[(frame - 3) // 2])
            if frame == 13:
                running = False
            continue
        # ---------------- симуляция деревни ----------------
        if SIM_MODE:
            sdt = 1 / 60.0
            cam.update_win_size(world["w"], world["h"])
            if frame == 1:
                rng.seed(7)
                wind_rng.seed(20260917)
                WIND.update(ang=0.8, str=0.35, t_ang=0.8, t_str=0.35,
                            next=10.0, t=0.0, kick=0.0, wx=1.0, wy=0.6,
                            mag=0.4)
                objects = make_test_scene()
                pixels.clear()
                reset_ground()
                village_reset(objects)
                VIL["lit"] = True
                VIL["phase"] = "settle"
                VIL["t"] = 0.0
                _fx, _fy = VIL["fire"]
                cam.zoom = 1.05
                cam.x = 0.0
                cam.y = 0.0
                _px, _py = cam.world_to_screen(_fx, _fy, 0.2)
                cam.x = world["w"] / 2 - _px
                cam.y = world["h"] * 0.45 - _py
                print(f"[sim] костёр ({_fx:.1f},{_fy:.1f}), "
                      f"участков {len(VIL['plots'])}")
            # 2x: симуляция идёт в два раза быстрее реального времени
            for _ in range(2):
                update_wind(sdt)
                step_physics(objects, pixels, sdt)
                update_fx(sdt, frame)
                update_daytime(sdt)  # плавное течение суток (ночи в симе)
                update_village(sdt, objects)
            render_all(60, frame)
            pygame.display.flip()
            # кадры в 2x: игровые секунды = frame / 30
            if frame == 2100:
                save_screenshot(window, "sim_build_70s.png")
            if frame == 3900:
                save_screenshot(window, "sim_night_130s.png")
            if frame == 4800:
                save_screenshot(window, "sim_build_160s.png")
            if frame == 13500:
                # взрыв рядом со строителями (t=450s, после L1)
                _ws = [h for h in VIL["workers"]
                       if not h.get("dead") and h["state"] in ("work",
                                                               "walk",
                                                               "run")]
                if _ws:
                    _w = min(_ws, key=lambda h: h["st"])
                    explode(cam, objects, pixels, _w["x"], _w["y"],
                            power=0.7, bz=0.3)
                    print("[sim] взрыв у рабочих")
            if frame == 13535:
                save_screenshot(window, "sim_blast_air.png")
            if frame == 13650:
                save_screenshot(window, "sim_blood_clear.png")
            if frame == 16800:
                # взрыв по готовому дому — починка (t=560s)
                _pd = [p for p in VIL["plots"] if p["state"] == "done"]
                if _pd:
                    _p = _pd[0]
                    _stg = _p["stages"][min(2, len(_p["stages"]) - 1)]
                    _pc = _stg["pieces"][0]
                    explode(cam, objects, pixels,
                            _p["x"] + _pc["x"] + _pc["w"] / 2,
                            _p["y"] + _pc["y"] + _pc["d"] / 2,
                            power=0.9, bz=0.3)
                    print(f"[sim] взрыв по дому '{_p['name']}'")
            if frame == 17400:
                save_screenshot(window, "sim_repair_580s.png")
            if frame == 7500:
                # общий план поселения: костёр в центре
                _fx0, _fy0 = VIL["fire"]
                cam.zoom = 2.2
                cam.x = 0.0
                cam.y = 0.0
                _px, _py = cam.world_to_screen(_fx0, _fy0, 0.2)
                cam.x = world["w"] / 2 - _px
                cam.y = world["h"] * 0.45 - _py
            if frame == 7530:
                save_screenshot(window, "sim_closeup_250s.png")
                pygame.image.save(world["surf"], "sim_raw_250s.png")
            if frame == 7560:
                _fx, _fy = VIL["fire"]
                cam.zoom = 1.05
                cam.x = 0.0
                cam.y = 0.0
                _px, _py = cam.world_to_screen(_fx, _fy, 0.2)
                cam.x = world["w"] / 2 - _px
                cam.y = world["h"] * 0.45 - _py
            if frame == 15000:
                save_screenshot(window, "sim_l1_500s.png")
            if frame == 12000:
                save_screenshot(window, "sim_night2_400s.png")
            if frame == 14400:
                save_screenshot(window, "sim_final_480s.png")
            if frame == 18000:
                save_screenshot(window, "sim_final_600s.png")
            if frame == 21600:
                save_screenshot(window, "sim_final_720s.png")
                _done = sum(1 for p in VIL["plots"]
                            if p["state"] == "done")
                _states = {}
                for p in VIL["plots"]:
                    _states[p["state"]] = _states.get(p["state"], 0) + 1
                _dead = sum(1 for h in VIL["workers"] if h.get("dead"))
                print(f"[sim] ИТОГО t={frame / 30:.0f}s (2x): "
                      f"уровень {VIL['lvl']}, готово {_done}/"
                      f"{len(VIL['plots'])}, статы {_states}, "
                      f"мёртвых {_dead}, "
                      f"брёвен {VIL['res']['logs']}, "
                      f"камней {VIL['res']['stones']}, "
                      f"копей {VIL['res']['spears']}, "
                      f"объектов {len(objects)}, "
                      f"крови {len(VIL['blood'])}")
                running = False
            continue
        # ---------------- тестовый прогон ----------------
        if TEST_MODE:
            cam.update_win_size(world["w"], world["h"])
            home_cam(cam)
            td = {10: (0, "light_morning.png"), 20: (1, "light_day.png"),
                  30: (2, "light_evening.png"), 40: (3, "light_night.png")}
            if frame in td:
                set_preset(td[frame][0])
                render_all(60, frame, hud_hover=(2, 2))
                pygame.display.flip()
                save_screenshot(window, td[frame][1])
            if frame == 50:
                shots = ["light_morning.png", "light_day.png",
                         "light_evening.png", "light_night.png"]
                caps = ["Утро", "День", "Вечер", "Ночь"]
                coll = pygame.Surface((1280, 720))
                font = pygame.font.Font(None, 44)
                for i, (fn, cap) in enumerate(zip(shots, caps)):
                    img = pygame.image.load(fn)
                    img = pygame.transform.scale(img, (640, 360))
                    coll.blit(img, ((i % 2) * 640, (i // 2) * 360))
                    t = font.render(cap, True, (255, 255, 255))
                    bg = pygame.Surface((t.get_width() + 16, t.get_height() + 8),
                                        pygame.SRCALPHA)
                    bg.fill((10, 12, 18, 160))
                    bx, by = (i % 2) * 640 + 12, (i // 2) * 360 + 360 - 96
                    coll.blit(bg, (bx, by))
                    coll.blit(t, (bx + 8, by + 4))
                pygame.image.save(coll, "light_compare.png")
                print("[скриншот] сохранён в light_compare.png")
                for kind, fn in [("grass", "normal_grass.png"),
                                 ("dirt", "normal_dirt.png"),
                                 ("stone", "normal_stone.png"),
                                 ("tile", "normal_tile.png"),
                                 ("wood", "normal_wood.png"),
                                 ("plaster", "normal_plaster.png")]:
                    pygame.image.save(normal_preview_image(kind), fn)
                    print(f"[карта нормалей] сохранена в {fn}")
            if frame == 55:
                set_preset(1)
                cam.rot = 1
                render_all(60, frame, hud_hover=(2, 2))
                pygame.display.flip()
                save_screenshot(window, "test_rot1.png")
                cam.rot = 0
            if frame == 60:
                objects = make_test_scene()
                pixels.clear()
                FLYERS.clear()
                FLAMES.clear()
                DUST.clear()
                reset_ground()
                _lt = make_building_library()
                place_building(objects, _lt[2], *_lt[2]["anchor"])
                explode(cam, objects, pixels, 18.9, 7.95, power=1.2)
            if 60 < frame <= 82:
                update_wind(1 / 60)
                step_physics(objects, pixels, 1 / 60)
                update_fx(1 / 60, frame)
            if frame == 82:
                cam.zoom = 4.2  # средний план: изба + кратер
                cam.x, cam.y = 0, 0
                _px, _py = cam.world_to_screen(18.9, 7.95, 0.4)
                cam.x, cam.y = world["w"] / 2 - _px, world["h"] / 2 - _py
                render_all(60, frame, hud_hover=(18, 7))
                pygame.display.flip()
                save_screenshot(window, "test_boom.png")
                print(f"TEST OK: objects={len(objects)} pixels={len(pixels)} "
                      f"dented={len(DENTED)}")
            if frame == 86:
                # слегка подорванный объект: слабый взрыв у края зелёного блока
                objects = make_test_scene()
                pixels.clear()
                reset_ground()
                FLASHES.clear()
                RINGS.clear()
                SMOKES.clear()
                SPARKS.clear()
                FLAMES.clear()
                DUST.clear()
                FLYERS.clear()
                _lt = make_building_library()
                place_building(objects, _lt[3], *_lt[3]["anchor"])
                explode(cam, objects, pixels, 7.45, 30.75, power=0.75)
            if 86 < frame <= 140:
                update_wind(1 / 60)
                step_physics(objects, pixels, 1 / 60)
                update_fx(1 / 60, frame)
            if frame == 140:
                cam.zoom = 5.0  # крупный план повреждения
                cam.x, cam.y = 0, 0
                _px, _py = cam.world_to_screen(7.45, 30.8, 0.9)
                cam.x, cam.y = (world["w"] / 2 - _px,
                                world["h"] * 330 / 720 - _py)
                render_all(60, frame, hud_hover=(8, 12))
                pygame.display.flip()
                save_screenshot(window, "test_damaged.png")
                print(f"TEST OK: damaged shot objects={len(objects)} "
                      f"pixels={len(pixels)}")
            if frame == 142:
                # проверка панорамирования: сдвиг камеры == сдвиг картинки
                objects = make_test_scene()
                pixels.clear()
                reset_ground()
                cam.rot = 0
                home_cam(cam)
                render_all(60, frame)
                pygame.display.flip()
                pygame.image.save(world["surf"], "pan_a_small.png")
                pygame.image.save(window, "pan_a.png")
                cam.x += 80.0
                cam.y += 40.0
                render_all(60, frame + 1)
                pygame.display.flip()
                pygame.image.save(world["surf"], "pan_b_small.png")
                pygame.image.save(window, "pan_b.png")
                print("PAN CHECK: pan_a/pan_b сохранены")
                running = False
                continue

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.VIDEORESIZE:
                # сохраняем безрамочный полноэкранный режим при смене размера
                window = make_window(ev.w, ev.h)
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    # ESC всегда закрывает игру (отмена размещения — ПКМ)
                    running = False
                elif ev.key == pygame.K_y:
                    PALETTE["open"] = not PALETTE["open"]
                    if PALETTE["open"]:
                        PLACE["tpl"] = None
                elif ev.key == pygame.K_g:
                    show_checker = not show_checker
                elif ev.key == pygame.K_h:
                    show_help = not show_help
                elif ev.key == pygame.K_b:
                    blast_mode = not blast_mode
                elif ev.key == pygame.K_z:
                    BLAST_POWER = clamp(BLAST_POWER - 0.1, 0.3, 2.5)
                elif ev.key == pygame.K_x:
                    BLAST_POWER = clamp(BLAST_POWER + 0.1, 0.3, 2.5)
                elif ev.key == pygame.K_t:
                    set_preset((int(DAYT * 4) % 4) + 1)
                elif ev.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    set_preset(ev.key - pygame.K_1)
                elif ev.key == pygame.K_0:
                    DAY_PAUSE = not DAY_PAUSE
                elif ev.key == pygame.K_r:
                    if PLACE["tpl"] is not None:
                        PLACE["rot"] = (PLACE["rot"] + 1) % 4
                        continue
                    objects = make_test_scene()
                    pixels.clear()
                    FLYERS.clear()
                    reset_ground()
                    bump_world()
                    FLASHES.clear()
                    RINGS.clear()
                    SMOKES.clear()
                    SPARKS.clear()
                    FLAMES.clear()
                    DUST.clear()
                    village_reset(objects)
                elif ev.key == pygame.K_q:
                    rotate_camera(cam, -1)
                elif ev.key == pygame.K_e:
                    rotate_camera(cam, +1)
                elif ev.key in (pygame.K_p, pygame.K_F12):
                    save_after_draw = True
                elif ev.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1 and PALETTE["open"]:
                    hit = None
                    for r, t in PALETTE["rects"]:
                        if r.collidepoint(ev.pos):
                            hit = t
                            break
                    PALETTE["open"] = False
                    if hit is not None:
                        PLACE["tpl"] = hit
                        PLACE["rot"] = 0
                    continue
                if PLACE["tpl"] is not None and ev.button in (1, 3):
                    if ev.button == 3:
                        PLACE["tpl"] = None
                        continue
                    _wx, _wy, _wz, _h = pick_blast_point(
                        cam, objects, ev.pos[0] // PIXEL, ev.pos[1] // PIXEL)
                    _lay = _tpl_layout(PLACE["tpl"], PLACE["rot"])
                    _ux0 = min(r[0] for r in _lay)
                    _uy0 = min(r[1] for r in _lay)
                    _ux1 = max(r[0] + r[2] for r in _lay)
                    _uy1 = max(r[1] + r[3] for r in _lay)
                    place_building(objects, PLACE["tpl"],
                                   _wx - (_ux0 + _ux1) / 2,
                                   _wy - (_uy0 + _uy1) / 2,
                                   PLACE["rot"])
                    PLACE["tpl"] = None
                    continue
                if ev.button in (1, 2, 3):
                    dragging = True
                    drag_button = ev.button
                    down_pos = ev.pos
                    moved = False
                elif ev.button == 4:
                    cam.zoom_at(ev.pos[0] // PIXEL, ev.pos[1] // PIXEL, 1.12)
                elif ev.button == 5:
                    cam.zoom_at(ev.pos[0] // PIXEL, ev.pos[1] // PIXEL,
                                  1 / 1.12)
            elif ev.type == pygame.MOUSEBUTTONUP:
                if ev.button in (1, 2, 3) and dragging and ev.button == drag_button:
                    dragging = False
                    if not moved:
                        wwx, wwy, wwz, hit = pick_blast_point(
                            cam, objects, ev.pos[0] // PIXEL, ev.pos[1] // PIXEL)
                        tx, ty = math.floor(wwx), math.floor(wwy)
                        if 0 <= tx < GRID_W and 0 <= ty < GRID_D:
                            if ev.button == 1:
                                if blast_mode:
                                    explode(cam, objects, pixels, wwx, wwy,
                                            BLAST_POWER, wwz)
                                else:
                                    if hit is not None:
                                        tx, ty = int(hit["x"]), int(hit["y"])
                                        z = hit["z"] + hit["h"]
                                    else:
                                        z = stack_height_at(objects, tx, ty)
                                    color = rng.choice(list(BASE_COLORS.keys()))
                                    objects.append(dict(x=tx, y=ty, z=z, w=1, d=1,
                                                        h=1, color=color,
                                                        shape="box", vx=0.0,
                                                        vy=0.0, vz=0.0))
                                    bump_world()
                            elif ev.button == 3:
                                top = (hit if hit is not None
                                       else top_object_at(objects, tx, ty))
                                if top:
                                    objects.remove(top)
                                    bump_world()
            elif ev.type == pygame.MOUSEMOTION:
                if dragging and drag_button in (1, 2):
                    if abs(ev.pos[0] - down_pos[0]) + abs(ev.pos[1] - down_pos[1]) > 6:
                        moved = True
                    if moved:
                        cam.x += (ev.pos[0] - last_mouse[0]) / PIXEL
                        cam.y += (ev.pos[1] - last_mouse[1]) / PIXEL
                last_mouse = ev.pos

        keys = pygame.key.get_pressed()
        speed = 700 / cam.zoom * dt / PIXEL
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            cam.x += speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            cam.x -= speed
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            cam.y += speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            cam.y -= speed

        if not TEST_MODE:
            update_wind(dt)
            step_physics(objects, pixels, dt)
            update_fx(dt, frame)
            update_daytime(dt)  # плавное течение суток
            # AI/экономика не требуют сотен апдейтов в секунду.
            # Анимация по-прежнему рисуется каждый кадр.
            village_acc += dt
            if village_acc >= 1.0 / 30.0:
                update_village(village_acc, objects)
                village_acc = 0.0
            _SPRITE_BUDGET[0] = 4  # не более 4 дорогих спрайтов за кадр
        sh = TRAUMA * TRAUMA * 18 / PIXEL
        cam.shx = sh * math.sin(frame * 2.3)
        cam.shy = sh * math.cos(frame * 1.7)

        if ensure_world():
            shadow_layer = pygame.Surface((world["w"], world["h"]),
                                          pygame.SRCALPHA)
            static_cache["key"] = None
        mp = pygame.mouse.get_pos()
        render_all(fps, frame, mpos=(mp[0] // PIXEL, mp[1] // PIXEL))
        pygame.display.flip()

        if save_after_draw:
            save_after_draw = False
            save_screenshot(window)

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
