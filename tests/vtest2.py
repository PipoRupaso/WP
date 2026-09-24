# -*- coding: utf-8 -*-
"""Проверка: взрыв по человеку (обрывки+кровь сразу) и ремонт дома.
Запуск: python3 tests/vtest2.py"""
import os
import sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from game import api as M  # noqa: E402
from game.core import state as G  # noqa: E402
M.reset_ground()
M.set_preset(1)


class _Cam:
    zoom = 1.0

    def world_to_screen(self, x, y, z):
        return (0, 0)


CAM = _Cam()

print("=== T5: взрыв по человеку — обрывки и кровь СРАЗУ ===")
objs = []
M.village_reset(objs)
v = G.VIL
v["objects"] = objs
fx, fy = v["fire"]
v["lit"] = True
v["phase"] = "settle"
v["t"] = 0.0
# одного рабочего ставим прямо в центр взрыва
h0 = v["workers"][0]
h0["x"], h0["y"] = fx + 0.3, fy + 0.3
h0["tx"], h0["ty"] = h0["x"], h0["y"]
blood0 = len(v["blood"])
nobj0 = len(objs)
# взрыв с близкого расстояния (power 1.2 -> fall ~0.9 -> dead_mark)
M.explode(CAM, objs, [], fx + 0.05, fy + 0.05, power=1.2, bz=0.3)
parts = [o for o in objs if o.get("body_part")]
dead_now = h0.get("dead")
blood_now = len(v["blood"])
print("мёртв сразу:", dead_now, "| обрывков:", len(parts),
      "| крови+:", blood_now - blood0,
      "| objs+:", len(objs) - nobj0)
assert dead_now, "человек должен умереть сразу"
assert len(parts) >= 5, "обрывки должны лететь от взрыва"
assert blood_now > blood0, "кровь при взрыве"

print()
print("=== T6: ремонт возвращает дом в прежний вид ===")
objs2 = []
M.village_reset(objs2)
v2 = G.VIL
v2["objects"] = objs2
fx2, fy2 = v2["fire"]
v2["lit"] = True
v2["phase"] = "settle"
v2["t"] = 0.0
for h in v2["workers"]:
    h["stone"] = True
    h["x"] = h["tx"] = fx2 + 1.0
    h["y"] = h["ty"] = fy2 + 1.0

def finish_all(vv):
    for p in vv["plots"]:
        while p["stage"] < len(p["stages"]):
            M._plot_spawn_stage(vv, p)

finish_all(v2)
p1 = v2["plots"][1]  # шалаш из шкур
assert p1["state"] == "done"
# взрыв по дому: часть деталей получает сколы/уничтожается
pc = p1["stages"][3]["pieces"][0]
M.explode(CAM, objs2, [],
             p1["x"] + pc["x"] + pc["w"] / 2,
             p1["y"] + pc["y"] + pc["d"] / 2, power=0.9, bz=0.3)
over_before = sum(o.get("over", 0) for o in objs2
                  if o.get("vid") == p1["idx"])
print("стат после взрыва:", p1["state"],
      "| сколов до ремонта:", over_before)
# даём деревне поработать 120 с
for f in range(120 * 60):
    M.update_village(1 / 60.0, objs2)
over_after = sum(o.get("over", 0) for o in objs2
                 if o.get("vid") == p1["idx"])
chips_after = sum(len(o.get("chips") or ()) for o in objs2
                  if o.get("vid") == p1["idx"])
n_parts = len(p1["stages"][3]["objs"])
present = sum(1 for o in p1["stages"][3]["objs"] if o is not None)
print("стат через 120с:", p1["state"],
      "| сколов после:", over_after, "| чипов:", chips_after,
      "| деталей ст.3:", present, "/", n_parts)
assert p1["state"] == "done", "дом должен восстановиться"
assert over_after == 0 and chips_after == 0, "сколы должны исчезнуть"
assert present == n_parts, "все детали на месте"
print()
print("T5+T6 OK")
