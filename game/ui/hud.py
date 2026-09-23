# -*- coding: utf-8 -*-
"""Иконка окна, HUD (FPS), скриншоты."""

import datetime
import pygame

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
