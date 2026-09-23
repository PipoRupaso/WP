# -*- coding: utf-8 -*-
"""Спрайты человечков по позам."""

import pygame
from game.render.lighting import (
    tone)
from game.village.core import (
    VIL_HUM_SPR, _HBOOTS, _HLEGS, _HSKIN)

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
