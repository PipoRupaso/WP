"""Showcase renders: doll/open/hit/floor + intacts + rotations + nights + strip.

Deterministic: fixed seeds, settled physics, fixed frame. Run twice -> identical PNGs.
Usage: python3 render_showcase.py
"""
import os
import sys

sys.argv = ["main.py"]
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

import pygame  # noqa: E402

import main as M  # noqa: E402

W, H = 1280 // 3, 720 // 3  # world surface 426x240
BIG = (W * M.PIXEL, H * M.PIXEL)  # 1278x720
FRAME = 100  # fixed anim frame (clouds/stars)


def reset_env(seed):
    M.rng.seed(seed)
    M.wind_rng.seed(20260917)
    M.WIND.update(ang=0.8, str=0.35, t_ang=0.8, t_str=0.35,
                  next=10.0, t=0.0, kick=0.0, wx=1.0, wy=0.6, mag=0.4)
    M.ANIM_T = 0.0
    M.CLOUD_OFF = 0.0
    M.TRAUMA = 0.0
    M._SUP_IDX["ver"] = -2
    M._PICK_IDX["ver"] = -2
    M.CHIMNEY_T.clear()
    M.HOUSE_HIT.clear()
    for lst in (M.FLASHES, M.RINGS, M.SMOKES, M.SPARKS, M.FLYERS):
        lst.clear()
    try:
        M.DENTED.clear()
    except AttributeError:
        pass
    M.reset_ground()


def settle(objects, pixels, n=120, f0=61):
    for i in range(n):
        M.update_wind(1 / 60)
        M.step_physics(objects, pixels, 1 / 60)
        M.update_fx(1 / 60, f0 + i)


def _showcase_filter(objects):
    """Только дома + мелочь/деревья: тестовые блоки-кубы в кадр не лезут."""
    out = []
    for o in objects:
        if o.get("house") is not None:
            out.append(o)
        elif o.get("shape") == "tree":
            out.append(o)
        elif min(o["w"], o["d"]) < 0.9:
            out.append(o)
    return out


def _smoke_r(e, zoom):
    k = e["t"] / e["life"]
    return int((e["r"] * (M.TILE_W / 2) + 26 * k) * zoom / M.PIXEL)


def render(objects, pixels, cam, preset):
    show = _showcase_filter(objects)
    M.set_preset(preset)
    sky = M.make_sky(W, H)
    cam.update_win_size(W, H)
    M.update_sun_screen(cam)
    surf = pygame.Surface((W, H)).convert()
    surf.blit(sky, (0, 0))
    if M.LIGHT["stars"]:
        M.draw_stars(surf, W, H, FRAME)
    M.draw_disc(surf, W, H)
    M.draw_edge_glow(surf, W, H, FRAME)
    M.draw_island_sides(surf, cam)
    M._paint_ground_base(surf, cam)
    M.draw_ground(surf, cam, False, preset)
    sh = pygame.Surface((W, H), pygame.SRCALPHA)
    M.draw_shadows(sh, cam, show)
    m = pygame.Surface((W, H), pygame.SRCALPHA)
    c = [cam.world_to_screen(0, 0, 0),
         cam.world_to_screen(M.GRID_W, 0, 0),
         cam.world_to_screen(M.GRID_W, M.GRID_D, 0),
         cam.world_to_screen(0, M.GRID_D, 0)]
    pygame.draw.polygon(m, (255, 255, 255, 255), c)
    sh.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surf.blit(sh, (0, 0))
    show = _showcase_filter(objects)
    M.draw_objects_and_pixels(surf, cam, show, pixels, preset)
    _saved_smoke, M.SMOKES[:] = M.SMOKES[:], [
        s for s in M.SMOKES if _smoke_r(s, cam.zoom) <= 6]
    M.draw_fx(surf, cam)
    M.SMOKES[:] = _saved_smoke
    M.draw_fir_overlay(surf, cam, show, W, H)
    big = pygame.transform.scale(surf, BIG)
    return big


def frame_cam(fx, fy, fz, zoom, rot=0, vy=0.55):
    cam = M.Camera()
    cam.rot = rot
    cam.zoom = zoom
    cam.x = cam.y = 0.0
    cam.update_win_size(W, H)
    px, py = cam.world_to_screen(fx, fy, fz)
    cam.x = W / 2 - px
    cam.y = H * vy - py
    return cam


def save(big, name, square=False):
    pygame.image.save(big, name)
    print("saved", name, flush=True)
    if square:
        x0 = (big.get_width() - 720) // 2
        sq = big.subsurface((x0, 0, 720, 720)).copy()
        sn = name.replace(".png", "_sq.png")
        pygame.image.save(sq, sn)
        print("saved", sn, flush=True)


def scenario(seed, blasts, settle_n=120, remove=None):
    reset_env(seed)
    objects = M.make_test_scene()
    _lib = M.make_building_library()
    for _t in _lib[:5]:  # C1..C5 (Средневековье) на родных якорях
        M.place_building(objects, _t, *_t["anchor"])
    if remove is not None:
        objects[:] = [o for o in objects if not remove(o)]
        M.WORLD_VERSION += 1
    pixels = []
    cam0 = M.Camera()
    for (bx, by, pw, bz) in blasts:
        M.explode(cam0, objects, pixels, bx, by, power=pw, bz=bz)
    settle(objects, pixels, n=settle_n)
    if blasts:
        pixels.clear()  # крошка убрана: видна архитектура, а не хаос
    return objects, pixels


def _cut_c1(o):
    if o.get("house") != 1:
        return False
    if o.get("shape") == "gable":
        return True
    return (o.get("mat") == "plaster"
            and (abs(o["y"] - 10.71) < 0.01 or abs(o["x"] - 42.86) < 0.01))


FOCUS = {
    1: (42.6, 10.5, 0.4),
    2: (38.55, 30.0, 0.5),
    3: (18.95, 8.05, 0.5),
    4: (7.0, 30.75, 0.7),
    5: (25.2, 22.15, 0.9),
}
ZOOM = {1: 8.5, 2: 7.0, 3: 6.2, 4: 5.4, 5: 4.8}


def main():
    M.pygame.init()
    M.pygame.display.set_mode((1280, 720))
    M.set_preset(1)

    # --- showcase blasts (locked aims/seeds) ---
    obs, px = scenario(0, [(42.6, 10.5, 0.5, 0.9)] * 2)
    save(render(obs, px, frame_cam(*FOCUS[1], 11.0), 1), "C1_doll.png", square=True)

    obs, px = scenario(7, [], remove=_cut_c1)
    save(render(obs, px, frame_cam(42.6, 10.5, 0.2, 11.0), 1), "C1_cut.png", square=True)

    obs, px = scenario(6, [(42.42, 10.9, 1.0, 0.2)])
    save(render(obs, px, frame_cam(42.5, 10.7, 0.25, 11.0), 1), "C1_open.png", square=True)

    obs, px = scenario(3, [(38.55, 30.62, 1.2, 0.3)])
    save(render(obs, px, frame_cam(*FOCUS[2], 8.5), 1), "C2_hit.png", square=True)

    obs, px = scenario(2, [(42.6, 10.5, 0.5, 0.9)] * 2 + [(42.6, 10.5, 0.7, 0.15)])
    save(render(obs, px, frame_cam(42.6, 10.5, 0.15, 11.0), 1), "C1_floor.png", square=True)

    # --- intacts ---
    for hid in (1, 2, 3, 4, 5):
        obs, px = scenario(7, [])
        save(render(obs, px, frame_cam(*FOCUS[hid], ZOOM[hid]), 1),
             f"C{hid}_intact.png")

    # --- rotations C1 + C5 ---
    for hid in (1, 5):
        for rot in range(4):
            obs, px = scenario(7, [])
            save(render(obs, px, frame_cam(*FOCUS[hid], ZOOM[hid], rot=rot), 1),
                 f"C{hid}_rot{rot}.png")

    # --- nights ---
    for hid in (1, 5):
        obs, px = scenario(7, [])
        save(render(obs, px, frame_cam(*FOCUS[hid], ZOOM[hid]), 3),
             f"C{hid}_night.png")

    # --- strip C1..C5 ---
    thumbs = []
    for hid in (1, 2, 3, 4, 5):
        img = pygame.image.load(f"C{hid}_intact.png")
        th = 225
        tw = int(img.get_width() * th / img.get_height())
        thumbs.append(pygame.transform.scale(img, (tw, th)))
    tw = thumbs[0].get_width()
    strip = pygame.Surface((tw * 5, 225 + 44))
    strip.fill((16, 18, 24))
    font = pygame.font.Font(None, 36)
    for i, th in enumerate(thumbs):
        strip.blit(th, (i * tw, 0))
        t = font.render(f"C{i + 1}", True, (255, 255, 255))
        strip.blit(t, (i * tw + 12, 225 + 6))
    pygame.image.save(strip, "CLASSES_compare.png")
    print("saved CLASSES_compare.png", flush=True)


if __name__ == "__main__":
    main()
