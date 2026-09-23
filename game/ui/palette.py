# -*- coding: utf-8 -*-
"""Палитра зданий (клавиша Y) и призрак установки."""

import pygame
from game.world.buildings import (
    EPOCH_NAMES)

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
