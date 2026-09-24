# -*- coding: utf-8 -*-
"""Изометрическая камера и быстрая проекция для горячих циклов."""

from game.core import state as G
from game.core.config import (
    GRID_D, GRID_W, HOME_ZOOM, ISLAND_T, TILE_H, TILE_W, TILE_Z, WINDOW_H,
    WINDOW_W)
from game.core.utils import (
    clamp)
from game.render.lighting import (
    GROUND_CACHE)
from game.world.terrain import (
    ground_height_at)

# ---------------------------------------------------------------------------
# Камера
# ---------------------------------------------------------------------------
# off_y зависит только от win_h — константу не пересчитываем на каждый вызов
_OFFY_K = (((GRID_W + GRID_D) * (TILE_H / 2)) / 2
           + ISLAND_T * TILE_Z / 2) / G.PIXEL
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
        ze = self.zoom / G.PIXEL  # мир — в пикселях малого буфера
        px = sx * ze + self.win_w / 2 + self.x + self.shx
        py = sy * ze + self.off_y + self.y + self.shy
        return px, py

    def world_to_screen(self, x, y, z=0.0):
        xr, yr = self.rotate_point(x, y)
        return self.iso_project(xr, yr, z)

    def screen_to_world(self, px, py, z=0.0):
        ze = self.zoom / G.PIXEL
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
        sx = (px - self.win_w / 2 - self.x) / (old / G.PIXEL)
        sy = (py - self.off_y - self.y) / (old / G.PIXEL)
        self.zoom = new
        self.x = px - self.win_w / 2 - sx * (new / G.PIXEL)
        self.y = py - self.off_y - sy * (new / G.PIXEL)


# ---------------------------------------------------------------------------
# Быстрая проекция для горячих циклов: один раз на кадр собираем контекст,
# дальше — чистая арифметика без вызовов методов (world_to_screen делает
# 3 вызова + свойство off_y на точку).
# ---------------------------------------------------------------------------
def _proj_ctx(cam):
    return (cam.rot, GRID_W, GRID_D, cam.zoom / G.PIXEL,
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


def _static_canvas_params(cam, w, h):
    """Размер и центр холста статики.

    Вблизи острова холст центрирован на ЦЕНТРЕ ОСТРОВА и покрывает весь
    остров: панорамирование по острову — простым сдвигом блита, без
    перестроя (плавный FPS). Если камера ушла с острова — холст
    центрируется на камере (там пусто, перестрои дешёвые)."""
    ze = cam.zoom / G.PIXEL
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
