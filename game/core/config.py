# -*- coding: utf-8 -*-
"""Настройки: режимы запуска, размеры, цвета, материалы, пресеты света."""

import os
import random
import sys

TEST_MODE = "--test" in sys.argv
BENCH_MODE = "--bench" in sys.argv
SIM_MODE = "--sim" in sys.argv
CLOSEUP_MODE = "--closeup" in sys.argv
if SIM_MODE or TEST_MODE or CLOSEUP_MODE:
    os.environ["SDL_VIDEODRIVER"] = "dummy"


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


def SP(px):
    return max(1, int(round(px / G.PIXEL)))

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


# состояние импортируется в конце: state.py сам берёт GRID_W/GRID_D отсюда
from game.core import state as G  # noqa: E402
