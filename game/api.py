# -*- coding: utf-8 -*-
"""Единый фасад: все функции/константы игры в одном пространстве имён.

Удобно для тестов и инструментов (раньше они делали `import main`):

    from game import api as M
    from game.core import state as G   # изменяемое состояние: G.DAYT, G.VIL...

Изменяемое состояние (DAYT, VIL, ANIM_T, PIXEL, ...) хранится только в
game.core.state — читать и писать его нужно через G.<ИМЯ>.
"""
import importlib as _il

from game.core import state as G  # noqa: F401

_MODULES = [
    "core.config",
    "core.utils",
    "world.world_state",
    "core.audio",
    "render.lighting",
    "render.normalmaps",
    "world.terrain",
    "render.camera",
    "world.scene",
    "world.buildings",
    "ui.palette",
    "world.queries",
    "render.sky",
    "render.island",
    "render.ground",
    "render.primitives",
    "render.materials",
    "render.objects",
    "render.trees",
    "render.sprites",
    "render.shadows",
    "sim.pixels",
    "sim.chipping",
    "sim.picking",
    "sim.destruction",
    "sim.fire",
    "sim.physics",
    "sim.effects",
    "village.core",
    "village.planner",
    "village.worker",
    "village.construction",
    "village.tribe",
    "village.update",
    "village.people_draw",
    "village.draw",
    "ui.hud",
    "app",
]

for _m in _MODULES:
    _mod = _il.import_module("game." + _m)
    for _k, _v in vars(_mod).items():
        if not _k.startswith("__") and _k != "G":
            globals()[_k] = _v
del _m, _mod, _k, _v
