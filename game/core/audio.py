# -*- coding: utf-8 -*-
"""Инициализация звука (синтезированный звук взрыва)."""

import numpy as np
import pygame
from game.core import state as G

def init_audio():
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
        G.BOOM_SOUND = pygame.sndarray.make_sound((stereo * 32767).astype(np.int16))
        G.BOOM_SOUND.set_volume(0.5)
    except Exception as e:
        print(f"[звук] выключен ({e})")
        G.BOOM_SOUND = None
