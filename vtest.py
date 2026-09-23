# -*- coding: utf-8 -*-
"""Проверка механик Task D: уровни L0-L2, рубка/брёвна, склады,
копьё, ночь (факелы/сон), коллизии. Запуск: python3 vtest.py"""
import os
import math

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((8, 8))

import main  # noqa: E402

PASS = []
FAIL = []


def check(name, ok, extra=""):
    (PASS if ok else FAIL).append(name)
    print(("PASS  " if ok else "FAIL  ") + name + ("  " + extra if extra
                                                   else ""), flush=True)


def force_done(v, hid, pos):
    p = main._vil_new_plot(v, hid, pos)
    if p is None:
        return None
    while p["stage"] < len(p["stages"]):
        main._plot_spawn_stage(v, p)
    return p


def finish_all(v):
    for p in v["plots"]:
        while p["stage"] < len(p["stages"]):
            main._plot_spawn_stage(v, p)


def run(v, objs, sec):
    for _ in range(int(sec * 60)):
        main.update_village(1 / 60.0, objs)


print("=== T1: уровень 1 — камень есть, кровати всем -> рубка, брёвна ===")
objs = main.make_test_scene()
main.reset_ground()
main.village_reset(objs)
v = main.VIL
v["objects"] = objs
fx, fy = v["fire"]
v["lit"] = True
v["phase"] = "settle"
v["t"] = 0.0
for h in v["workers"]:
    h["stone"] = True
    h["x"] = h["tx"] = fx + 1.0
    h["y"] = h["ty"] = fy + 1.0
    h["z"] = h["z0"] = main._vil_gz(h["x"], h["y"])
# кровати: все пять жилищ готовы (12 кровей >= 10)
finish_all(v)
force_done(v, 11, (fx + 4.5, fy + 3.0))
force_done(v, 67, (fx - 4.5, fy + 3.5))
force_done(v, 68, (fx + 4.0, fy - 4.5))
max_logs = 0
# ночь (t=84-173s) — все спят; доживаем до рассвета и дальше
for _s in range(30):
    run(v, objs, 10.0)
    max_logs = max(max_logs, v["res"]["logs"])
check("T1 lvl>=1", v["lvl"] >= 1, "lvl=%d" % v["lvl"])
stumps = sum(1 for t in main.VIL_TREES if t["o"].get("dead") == "stump")
check("T1 деревья срублены (пенёк -> 2 бревна)",
      stumps >= 2, "пеньков=%d" % stumps)
check("T1 брёвна в игре (на складе или в постройке)",
      max_logs >= 1, "max_res.logs=%d" % max_logs)
check("T1 мастерская (12) запланирована",
      any(p["tpl"]["hid"] == 12 for p in v["plots"]))

print("=== T2: уровень 2 — мастерская готова + брёвна -> особые, ===")
print("     склад камней, копьё ===")
# честный запас: реальные брёвна на складе
_lp = v["logpile"]
for _k in range(40):
    v["logs"].append(dict(
        x=_lp[0] + (_k % 6) * 0.3 - 0.9,
        y=_lp[1] + (_k // 6) * 0.22 - 0.5,
        z=0.0, owner=None, placed=True, ang=0.5))
v["res"]["logs"] = sum(1 for l in v["logs"] if l["placed"])
p12 = next((p for p in v["plots"] if p["tpl"]["hid"] == 12), None)
if p12 is not None:
    while p12["stage"] < len(p12["stages"]):
        main._plot_spawn_stage(v, p12)
run(v, objs, 180.0)
check("T2 lvl==2", v["lvl"] == 2, "lvl=%d" % v["lvl"])
h72 = [p["tpl"]["hid"] for p in v["plots"] if p["tpl"]["hid"] in (72, 67, 68)]
check("T2 дома ур.3-5 запланированы",
      len(h72) >= 1, "hid=%s" % h72)
check("T2 склад камней пополняется",
      len(v["stones_placed"]) >= 2,
      "камней=%d res=%d" % (len(v["stones_placed"]), v["res"]["stones"]))
p72 = next((p for p in v["plots"] if p["tpl"]["hid"] == 72), None)
run(v, objs, 420.0 if p72 is not None and p72["state"] != "done" else 5.0)
spears = sum(1 for o in objs if o.get("vid") == -2)
check("T2 дом 72 (3 чел.) построен", p72 is not None and p72["state"] == "done",
      "" if p72 is None else p72["state"])
check("T2 копьё (камень+жерди) в мастерской",
      v["res"]["spears"] >= 1 and spears >= 2,
      "spears=%d objs=%d" % (v["res"]["spears"], spears))

print("=== T3: ночь ===")
print("   L2: факелы не отменяют отдых — все спят ===")
main.DAYT = 0.70
main.apply_daylight()
run(v, objs, 30.0)
alive = [h for h in v["workers"] if not h.get("dead")]
sleeping = sum(1 for h in alive if h.get("act") == "sleep"
               or h["state"] == "sit")
working = sum(1 for h in alive if h["state"] in ("work", "clean",
                                                 "chop", "drop_log"))
check("T3a ночью все спят (L2, даже с факелами)",
      sleeping >= len(alive) - 1 and working == 0,
      "sleep=%d work=%d all=%d" % (sleeping, working, len(alive)))
print("   L0: сон в хижине, вне дома никого ===")
objs2 = main.make_test_scene()
main.reset_ground()
main.village_reset(objs2)
v2 = main.VIL
v2["objects"] = objs2
fx2, fy2 = v2["fire"]
v2["lit"] = True
v2["phase"] = "settle"
v2["t"] = 0.0
finish_all(v2)  # готовая хижина для ночёвки
main.DAYT = 0.72
main.apply_daylight()
run(v2, objs2, 45.0)
alive2 = [h for h in v2["workers"] if not h.get("dead")]
sleep2 = sum(1 for h in alive2 if h.get("act") == "sleep"
             or (h["state"] == "sit" and h.get("act") in ("sleep", "sit")))
working2 = sum(1 for h in alive2 if h["state"] in ("work", "clean",
                                                   "chop", "drop_log"))
check("T3b ночью почти все в хижине/у огня",
      sleep2 >= len(alive2) - 2 and working2 == 0,
      "sleep=%d work=%d all=%d" % (sleep2, working2, len(alive2)))

print("=== T4: коллизии — люди не проходят сквозь костёр ===")
v3 = main.VIL
main._vil_solids(v3)
h3 = dict(main._vil_make_human(99, fx2 + 1.6, fy2))
h3["state"] = "walk"
h3["act"] = "task"
h3["tx"], h3["ty"] = fx2 - 1.6, fy2
h3["stuck_t"] = 0.0
mind = 9.0
arrived = False
for _ in range(30 * 60):
    main._vil_worker_step(v3, h3, 1 / 60.0)
    mind = min(mind, math.hypot(h3["x"] - fx2, h3["y"] - fy2))
    if h3["state"] != "walk" and h3["state"] != "run":
        arrived = True
        break
check("T4 не прошёл сквозь костёр", mind > 0.55, "min_d=%.2f" % mind)
check("T4 дошёл (обойдя)", arrived,
      "pos=(%.1f,%.1f) state=%s" % (h3["x"], h3["y"], h3["state"]))

print()
print("ИТОГО: PASS %d, FAIL %d" % (len(PASS), len(FAIL)))
if FAIL:
    print("Провалы:", FAIL)
    raise SystemExit(1)
print("ALL OK")
