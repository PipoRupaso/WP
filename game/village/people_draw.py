# -*- coding: utf-8 -*-
"""Спрайты человечков: мастер 20x32, позы и оружие в руках.

Пиксель арта людей и зверей одного размера (32 строки = рост человека),
поэтому в фигуре помещаются лицо, пальцы, пояс, складки туники и
оружие: копьё, дубинка, камень, факел, жердь. На экране фигура того же
«крупного пикселя», что и раньше, но пикселей в ней вчетверо больше.
"""

import pygame

from game.render.lighting import (
    tone)
from game.village.core import (
    VIL_HUM_SPR, _HBOOTS, _HLEGS, _HSKIN)

W, H = 20, 32
_EYE = (44, 34, 32)
_BROW = (70, 52, 40)
_BELT = (92, 70, 42)
_BUCKLE = (150, 128, 70)
_WOOD = (122, 84, 48)
_WOOD_D = (96, 64, 36)
_STEEL = (120, 124, 130)
_STEEL_D = (90, 92, 98)
_FLAME = (255, 176, 60)
_FLAME_C = (255, 236, 122)


def _hum_master(pose, hum):
    m = pygame.Surface((W, H), pygame.SRCALPHA)
    skin, hair, tun = _HSKIN, hum["hair"], hum["tunic"]
    tun_d = tone(tun, 0.72)
    tun_l = tone(tun, 1.18)
    legs, boots = _HLEGS, _HBOOTS
    legs_d = tone(legs, 0.8)

    def px(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            m.set_at((x, y), c)

    def rect(x0, y0, x1, y1, c):
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                px(xx, yy, c)

    def vline(x, y0, y1, c):
        for yy in range(y0, y1 + 1):
            px(x, yy, c)

    def head(hx, hy):
        # голова 6x6: волосы с челкой и бликом, лицо, глаза
        rect(hx, hy, hx + 5, hy, hair)
        px(hx + 1, hy, tone(hair, 1.3))
        px(hx + 4, hy, tone(hair, 1.3))
        rect(hx, hy + 1, hx + 5, hy + 4, skin)
        px(hx, hy + 1, hair)
        px(hx + 5, hy + 1, hair)
        px(hx, hy + 2, hair)
        px(hx + 5, hy + 2, hair)
        px(hx + 1, hy + 1, _BROW)
        px(hx + 4, hy + 1, _BROW)
        px(hx + 1, hy + 2, _EYE)
        px(hx + 4, hy + 2, _EYE)
        px(hx + 2, hy + 3, tone(skin, 0.84))
        px(hx + 3, hy + 3, tone(skin, 0.84))
        px(hx + 2, hy + 4, tone(skin, 0.74))
        # шея
        rect(hx + 2, hy + 5, hx + 3, hy + 5, skin)

    def torso(ty, arm_l=None, arm_r=None):
        """Туника rows ty..ty+8 (плечи 8宽), руки по бокам."""
        for i in range(ty, ty + 9):
            for j in range(6, 14):
                c = tun
                if i < ty + 2:
                    c = tun_l
                if i > ty + 5:
                    c = tun_d
                px(j, i, c)
        vline(5, ty, ty + 6, tun_d)
        vline(14, ty, ty + 6, tun_d)
        # складки
        px(9, ty + 4, tun_d)
        px(11, ty + 5, tun_d)
        # пояс с пряжкой
        rect(6, ty + 8, 13, ty + 8, _BELT)
        px(9, ty + 8, _BUCKLE)
        px(10, ty + 8, _BUCKLE)

    def arm(x, y0, y1, c=None):
        c = c or skin
        vline(x, y0, y1, c)

    def legs_stand(ly):
        for i in range(ly, ly + 11):
            c = legs if i < ly + 8 else legs_d
            rect(7, i, 8, i, c)
            rect(11, i, 12, i, c)
        rect(7, ly + 11, 8, ly + 12, boots)
        rect(11, ly + 11, 12, ly + 12, boots)
        rect(6, ly + 13, 9, ly + 13, tone(boots, 0.7))
        rect(11, ly + 13, 14, ly + 13, tone(boots, 0.7))

    def leg_swing(x0, ly, sw1, sw2, lift):
        """Нога: бедро со сдвигом sw1, голень sw2, ботинок со сдвигом sw2."""
        y1 = ly + 6
        y2 = ly + 11 - lift
        for i in range(ly, y1 + 1):
            rect(x0 + sw1, i, x0 + 1 + sw1, i, legs)
        for i in range(y1 + 1, y2 + 1):
            rect(x0 + sw2, i, x0 + 1 + sw2, i, legs_d)
        rect(x0 + sw2, y2 + 1, x0 + 1 + sw2, min(y2 + 2, H - 1), boots)
        if y2 + 3 < H:
            rect(x0 + sw2 - 1, y2 + 3, x0 + 2 + sw2, y2 + 3,
                 tone(boots, 0.7))

    def spear(sx, sy, horiz=False):
        if horiz:
            rect(2, sy, 15, sy, _WOOD)
            px(16, sy, _STEEL)
            px(17, sy, _STEEL)
            px(18, sy, _STEEL_D)
        else:
            vline(sx, sy, sy + 14, _WOOD)
            px(sx, sy - 1, _STEEL)
            px(sx, sy - 2, _STEEL)
            px(sx - 1, sy - 1, _STEEL_D)
            px(sx + 1, sy - 1, _STEEL_D)

    def torch(sx, sy):
        vline(sx, sy, sy + 5, _WOOD_D)
        px(sx, sy - 1, _FLAME)
        px(sx - 1, sy - 1, _FLAME)
        px(sx, sy - 2, _FLAME_C)

    def club(sx, sy, up=True):
        if up:
            vline(sx, sy, sy + 5, _WOOD)
            rect(sx - 1, sy - 2, sx + 1, sy - 1, _STEEL_D)
            px(sx, sy - 3, _STEEL)
        else:
            for k in range(5):
                px(sx + k // 2, sy + k, _WOOD)
            rect(sx + 2, sy + 4, sx + 4, sy + 6, _STEEL_D)

    flags = hum
    has_spear = flags.get("spear")
    has_torch = flags.get("torch_on")
    carry_log = flags.get("carry_log")
    carry_sp = flags.get("carry_sp")
    has_stone = flags.get("stone")
    carry_stick = flags.get("carry")

    if pose == "dead":
        rect(4, 14, 13, 19, tone(tun, 0.6))
        rect(4, 14, 13, 15, tone(tun, 0.45))
        rect(14, 15, 18, 18, legs)
        rect(18, 15, 19, 16, boots)
        rect(0, 13, 4, 18, skin)
        rect(0, 13, 4, 14, hair)
        px(2, 16, _EYE)
        px(1, 17, _EYE)
        return m

    yo = 1 if pose in ("sit", "clean", "stun") else 0
    head(7, yo)
    ty = 7 + yo
    if pose == "sit":
        torso(ty)
        # ноги сложены
        rect(6, ty + 9, 13, ty + 11, legs)
        rect(5, ty + 12, 14, ty + 13, boots)
        rect(6, ty + 6, 7, ty + 8, skin)
        rect(12, ty + 6, 13, ty + 8, skin)
        return m
    if pose in ("walk_a", "walk_b", "run_a", "run_b"):
        run = pose.startswith("run")
        a = 1 if pose.endswith("a") else -1
        s1, s2 = (1, 2) if run else (1, 1)
        l1, l2 = (0, 2) if run else (0, 1)
        torso(ty)
        leg_swing(7, ty + 9, a * s1, a * s2, a * l1 if a > 0 else 0)
        leg_swing(11, ty + 9, -a * s1, -a * s2, 0 if a > 0 else l2)
        # встречные махи рук
        arm(5, ty + 1, ty + 3, tun_d)
        arm(14, ty + 1, ty + 3, tun_d)
        arm(5, ty + 4, ty + 5 - a, skin)
        arm(14, ty + 4, ty + 5 + a, skin)
        if has_spear:
            spear(15, ty - 2)
        elif has_torch:
            torch(15, ty + 2)
        return m
    if pose in ("work_a", "work_b"):
        torso(ty)
        legs_stand(ty + 9)
        if pose == "work_a":
            arm(14, ty - 3, ty + 2)
            px(14, ty - 4, skin)
            club(14, ty - 4, up=True)
            arm(5, ty + 2, ty + 6)
        else:
            arm(14, ty + 3, ty + 8)
            club(15, ty + 6, up=False)
            arm(5, ty + 2, ty + 6)
        return m
    if pose == "carry":
        torso(ty)
        legs_stand(ty + 9)
        rect(5, ty + 3, 14, ty + 4, skin)  # руки вперёд
        if carry_log or carry_stick:
            rect(2, ty + 1, 17, ty + 3, _WOOD)
            px(2, ty + 2, _WOOD_D)
            px(17, ty + 2, _WOOD_D)
            px(3, ty + 1, tone(_WOOD, 1.2))
            px(16, ty + 1, tone(_WOOD, 1.2))
        else:
            rect(6, ty + 1, 13, ty + 3, _WOOD)
        return m
    if pose == "air":
        torso(ty)
        arm(4, ty - 2, ty + 3)
        arm(15, ty - 2, ty + 3)
        leg_swing(7, ty + 9, -2, -3, 1)
        leg_swing(11, ty + 9, 2, 3, 1)
        return m
    if pose == "clean":
        torso(ty + 1)
        rect(7, ty + 10, 8, ty + 13, legs)
        rect(11, ty + 10, 12, ty + 13, legs)
        rect(7, ty + 13, 8, ty + 14, boots)
        rect(11, ty + 13, 12, ty + 14, boots)
        rect(13, ty + 6, 15, ty + 9, skin)   # руки к земле
        px(5, ty + 6, skin)
        return m
    if pose == "light":
        torso(ty)
        legs_stand(ty + 9)
        rect(13, ty + 3, 16, ty + 4, skin)
        torch(16, ty + 1)
        arm(5, ty + 1, ty + 6)
        return m
    if pose == "aim":
        torso(ty)
        legs_stand(ty + 9)
        rect(4, ty + 3, 7, ty + 4, skin)    # замах назад
        rect(12, ty + 3, 14, ty + 4, skin)  # рука вперёд
        spear(0, ty + 3, horiz=True)
        return m
    if pose == "attack":
        torso(ty)
        legs_stand(ty + 9)
        rect(13, ty + 2, 16, ty + 4, skin)
        club(16, ty + 3, up=False)
        arm(5, ty + 1, ty + 6)
        return m
    if pose == "stun":
        torso(ty)
        legs_stand(ty + 9)
        rect(2, ty + 2, 5, ty + 3, skin)
        rect(14, ty + 2, 17, ty + 3, skin)
        return m
    # stand / place
    torso(ty)
    legs_stand(ty + 9)
    arm(5, ty + 1, ty + 3, tun_d)
    arm(14, ty + 1, ty + 3, tun_d)
    arm(5, ty + 4, ty + 6, skin)
    arm(14, ty + 4, ty + 6, skin)
    px(5, ty + 7, skin)
    px(14, ty + 7, skin)
    if pose == "place":
        rect(13, ty + 5, 15, ty + 7, skin)
    if has_spear:
        spear(15, ty - 1)
    elif has_torch:
        torch(15, ty + 3)
    elif carry_sp:
        rect(13, ty + 6, 15, ty + 8, (128, 128, 132))
        px(14, ty + 6, (168, 168, 172))
    elif has_stone:
        rect(13, ty + 6, 15, ty + 8, (128, 128, 132))
    elif carry_log:
        rect(2, ty + 4, 17, ty + 6, _WOOD)
        px(2, ty + 5, _WOOD_D)
        px(17, ty + 5, _WOOD_D)
    return m


def _hum_sprite(pose, hum, S, flip):
    key = ("hum", pose, hum["hair"], hum["tunic"], S, flip,
           bool(hum.get("spear")), bool(hum.get("torch_on")),
           bool(hum.get("carry_log")), bool(hum.get("carry_sp")),
           bool(hum.get("stone")), bool(hum.get("carry")))
    spr = VIL_HUM_SPR.get(key)
    if spr is None:
        m = _hum_master(pose, hum)
        tw = max(4, int(round(S * W / H)))
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
    if st == "aim":
        return "aim"
    if st == "attack":
        return "attack"
    if st in ("work", "chop"):
        return "work_a" if int(hum["ph"] * 2) % 2 == 0 else "work_b"
    if moving:
        fr = int(hum["ph"]) % 2
        if spd > 1.9:
            return "run_a" if fr == 0 else "run_b"
        return "walk_a" if fr == 0 else "walk_b"
    if hum["carry"]:
        return "carry"
    return "stand"
