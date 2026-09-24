# -*- coding: utf-8 -*-
"""Главный цикл: окно, рендер, ввод, режимы --test/--bench/--sim/--closeup."""

import math
import pygame
from game.core import state as G
from game.core.config import (
    BASE_COLORS, BENCH_MODE, CLOSEUP_MODE, GRID_D, GRID_W, SIM_MODE,
    TEST_MODE, TILE_H, TILE_W, WINDOW_H, WINDOW_W, rng)
from game.core.utils import (
    clamp)
from game.world.world_state import (
    DUST, FLAMES, FLASHES, FLYERS, RINGS, SMOKES, SPARKS, WIND,
    _CRATER_TILES, _STATIC_REQ, bump_world, wind_rng)
from game.core.audio import (
    init_audio)
from game.render.lighting import (
    DAY_LEN, _day_step, set_preset, update_daytime, update_sun_screen)
from game.render.normalmaps import (
    ground_sprite, normal_preview_image)
from game.world.terrain import (
    ground_height_at, reset_ground)
from game.render.camera import (
    Camera, _OFFY_K, _static_canvas_params, home_cam, rotate_camera)
from game.world.scene import (
    make_test_scene)
from game.world.buildings import (
    _tpl_layout, draw_ghost, make_building_library, place_building)
from game.ui.palette import (
    PALETTE, PLACE, draw_palette)
from game.world.queries import (
    stack_height_at, top_object_at)
from game.render.sky import (
    draw_disc, draw_edge_glow, draw_stars, make_sky)
from game.render.island import (
    draw_island_sides)
from game.render.ground import (
    _ordered_tiles, _paint_ground_base, _visible_tile_range, draw_ground,
    draw_wear_layer)
from game.render.objects import (
    _SPRITE_BUDGET)
from game.render.trees import (
    draw_fir_overlay)
from game.render.sprites import (
    _collect_render_items, _draw_render_items,
    draw_objects_and_pixels, prune_object_sprites)
from game.render.shadows import (
    draw_hover, draw_shadows)
from game.sim.picking import (
    pick_blast_point)
from game.sim.destruction import (
    explode)
from game.sim.physics import (
    step_physics)
from game.sim.effects import (
    draw_fx, update_fx, update_wind)
from game.village.core import (
    village_reset)
from game.village.update import (
    update_village)
from game.village.draw import (
    collect_village_items, draw_village_overlay)
from game.ui.hud import (
    HUD, make_icon, save_screenshot)

# ---------------------------------------------------------------------------
# Главный цикл
# ---------------------------------------------------------------------------
def main():
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
    cam.update_win_size(window.get_size()[0] // G.PIXEL,
                        window.get_size()[1] // G.PIXEL)
    home_cam(cam)
    reset_ground()
    objects = make_test_scene()
    pixels = []
    village_reset(objects)
    hud = HUD()
    set_preset(1)
    world = {"w": 0, "h": 0, "surf": None}

    def ensure_world():
        ww = max(160, window.get_size()[0] // G.PIXEL)
        hh = max(120, window.get_size()[1] // G.PIXEL)
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
            tile_cost = 100 if (tile in G.DENTED or tile in G._RIMTILES) else 1
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
            sw = max(2, int(round(TILE_W * cam.zoom / G.PIXEL))) + ov
            sh = max(1, int(round(TILE_H * cam.zoom / G.PIXEL))) + ov
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
            G._SHADOW_ARR = bsh
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
        if G.LIGHT.get("star_a", 0.0) > 0.01:
            draw_stars(surf, w, h, frame)
        draw_disc(surf, w, h)
        # статичный слой: остров + земля + тени. Холст центрирован на острове
        # (панорамирование по острову без перестроя) либо на камере вдали.
        qx, qy = cam.x, cam.y
        key = (w, h, round(cam.zoom, 3), cam.rot, qx, qy,
               li, show_checker, G.STATIC_VER)
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
                    G._SHADOW_ARR = shadow_layer
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
        G._STATIC_OFF = (_offx, _offy)
        G._STATIC_SCALE = _scale
        if (G.VIL is not None and G.VIL.get("wear")) or G.SCORCH:
            draw_wear_layer(surf, cam,
                            G.VIL.get("wear") if G.VIL else None,
                            G.SCORCH)
        _render_zoom = (static_cache.get("zoom", cam.zoom)
                        if _BUILD is not None else cam.zoom)
        _extras = collect_village_items(cam) if G.VIL is not None else ()
        if _render_zoom < 0.6 and not show_checker:
            draw_objects_and_pixels(surf, cam, [], pixels, li, _extras)
        else:
            draw_objects_and_pixels(surf, cam, objects, pixels, li,
                                     _extras)
        draw_edge_glow(surf, w, h, frame)
        draw_fx(surf, cam)
        if mpos:
            hover_tile = draw_hover(surf, cam, objects, mpos, blast_mode,
                                    G.BLAST_POWER)
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
        draw_village_overlay(surf, cam, frame)
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
        G.ANIM_T = 0.0
        G.CLOUD_OFF = 0.0

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
        G.ANIM_T = 0.0
        G.CLOUD_OFF = 0.0

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
                G.VIL["lit"] = True
                G.VIL["phase"] = "settle"
                G.VIL["t"] = 0.0
                _fx, _fy = G.VIL["fire"]
                cam.zoom = 1.05
                cam.x = 0.0
                cam.y = 0.0
                _px, _py = cam.world_to_screen(_fx, _fy, 0.2)
                cam.x = world["w"] / 2 - _px
                cam.y = world["h"] * 0.45 - _py
                print(f"[sim] костёр ({_fx:.1f},{_fy:.1f}), "
                      f"участков {len(G.VIL['plots'])}")
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
                _ws = [h for h in G.VIL["workers"]
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
                _pd = [p for p in G.VIL["plots"] if p["state"] == "done"]
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
                _fx0, _fy0 = G.VIL["fire"]
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
                _fx, _fy = G.VIL["fire"]
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
                _done = sum(1 for p in G.VIL["plots"]
                            if p["state"] == "done")
                _states = {}
                for p in G.VIL["plots"]:
                    _states[p["state"]] = _states.get(p["state"], 0) + 1
                _dead = sum(1 for h in G.VIL["workers"] if h.get("dead"))
                print(f"[sim] ИТОГО t={frame / 30:.0f}s (2x): "
                      f"уровень {G.VIL['lvl']}, готово {_done}/"
                      f"{len(G.VIL['plots'])}, статы {_states}, "
                      f"мёртвых {_dead}, "
                      f"брёвен {G.VIL['res']['logs']}, "
                      f"камней {G.VIL['res']['stones']}, "
                      f"копей {G.VIL['res']['spears']}, "
                      f"объектов {len(objects)}, "
                      f"крови {len(G.VIL['blood'])}")
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
                      f"dented={len(G.DENTED)}")
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
                    G.BLAST_POWER = clamp(G.BLAST_POWER - 0.1, 0.3, 2.5)
                elif ev.key == pygame.K_x:
                    G.BLAST_POWER = clamp(G.BLAST_POWER + 0.1, 0.3, 2.5)
                elif ev.key == pygame.K_t:
                    set_preset((int(G.DAYT * 4) % 4) + 1)
                elif ev.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    set_preset(ev.key - pygame.K_1)
                elif ev.key == pygame.K_0:
                    G.DAY_PAUSE = not G.DAY_PAUSE
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
                        cam, objects, ev.pos[0] // G.PIXEL, ev.pos[1] // G.PIXEL)
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
                    cam.zoom_at(ev.pos[0] // G.PIXEL, ev.pos[1] // G.PIXEL, 1.12)
                elif ev.button == 5:
                    cam.zoom_at(ev.pos[0] // G.PIXEL, ev.pos[1] // G.PIXEL,
                                  1 / 1.12)
            elif ev.type == pygame.MOUSEBUTTONUP:
                if ev.button in (1, 2, 3) and dragging and ev.button == drag_button:
                    dragging = False
                    if not moved:
                        wwx, wwy, wwz, hit = pick_blast_point(
                            cam, objects, ev.pos[0] // G.PIXEL, ev.pos[1] // G.PIXEL)
                        tx, ty = math.floor(wwx), math.floor(wwy)
                        if 0 <= tx < GRID_W and 0 <= ty < GRID_D:
                            if ev.button == 1:
                                if blast_mode:
                                    explode(cam, objects, pixels, wwx, wwy,
                                            G.BLAST_POWER, wwz)
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
                        cam.x += (ev.pos[0] - last_mouse[0]) / G.PIXEL
                        cam.y += (ev.pos[1] - last_mouse[1]) / G.PIXEL
                last_mouse = ev.pos

        keys = pygame.key.get_pressed()
        speed = 700 / cam.zoom * dt / G.PIXEL
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
        sh = G.TRAUMA * G.TRAUMA * 18 / G.PIXEL
        cam.shx = sh * math.sin(frame * 2.3)
        cam.shy = sh * math.cos(frame * 1.7)

        if ensure_world():
            shadow_layer = pygame.Surface((world["w"], world["h"]),
                                          pygame.SRCALPHA)
            static_cache["key"] = None
        mp = pygame.mouse.get_pos()
        render_all(fps, frame, mpos=(mp[0] // G.PIXEL, mp[1] // G.PIXEL))
        pygame.display.flip()

        if save_after_draw:
            save_after_draw = False
            save_screenshot(window)

    pygame.quit()
    return 0
