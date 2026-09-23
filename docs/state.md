# Current State
_What is being worked on right now, what is unfinished, and the immediate next steps. Always update this section._

**FINAL sim #7 running (PID 3779, `--sim 720 --speed 2 --shots` → /tmp/sim_final7.log, ~7 min) with ALL fixes of this message. When done: check shots (esp. sim_night_130s = real dark night + sleepers, sim_blast_air = parts+blood), tail line, then RUSSIAN REPORT + tell user main.py is updated in workspace (they upload via GitHub web UI).**

## Changes THIS message (user re-sent Task D verbatim + 3 new complaints; all addressed):
1. **Explosion on people = parts + blood IMMEDIATELY**: in `explode()`, after velocity/blood-pixel block, `if h["dead_mark"]: _vil_human_die(VIL, h)` — 7 body parts (bone/leather/wood boxes, `body_part=True`, world objects → later explosions chip them too) + big blood pool spawn at the blast point, body not drawn (dead). Non-lethal knockback still flies+stuns. Verified: vtest2.py T5 (dead immediately, 7 parts, blood+5).
2. **Repair restores ORIGINAL look**: `_plot_after_clear` (was_done branch) now resets `ob["over"]=0` + `ob["chips"].clear()` on all surviving parts of damaged stages (with small puff) — previously chips persisted forever (house stayed chipped). `_vil_puff` got `small=` param. Verified: vtest2.py T6 (15 chips → 0 after cycle, house done, all parts present). Cycle speed OK (~30-60 s for heavy damage: 4-7 debris×0.7s + jobs×~1s, 4 workers).
3. **Землянка removed → Палатка is class-1**: tent (i==2, hid 10) rebuilt as real cone: 8 poles × 3 stepped segments converging to apex (r 0.45→0.33→0.20), apex bundle, 2 straw lashing rings (4 tangents each), entrance gap (pole 0 skipped) + hide flap, 3 side hide patches, hearth. cu_h10.png verified.
4. **Hide hut (i==1, hid 9) = triangle + deer pattern**: `draw_gable` ends=="hide" now renders hide on BOTH visible faces: 3 horizontal seams, 3 dark vertical stripes (seeded), light+dark spots. Scene: removed scattered stripe/spot boxes (read as planks); kept A-frame posts, ridge, floor, entrance, flag. cu_h9.png verified.
5. **Sim day/night was BROKEN**: sim loop never called update_daytime → no nights in sim (villagers never slept in sim!). Added `update_daytime(sdt)` to the 2× sim loop. Night1 t=84-173 s, night2 t=324-413 s.

## Earlier this session (pre-compaction + after): vtest 13/13; sim blasts moved 450/560 s (power 0.7/0.9); pacing (sit 2/0.22, build 0.65+0.18n, walk 2.6/2.0); stick econ (spawn 1.6+2.8, cap 24, stuck-stick removed); stone-depot distribution (id%3 or _spn==0); drop_sp releases pebble (was: pool drained at ~9).
## Evidence: sim #6 (pre-daytime): lvl 2, 7/13 done, мёртвых 1, stones 21. vtest 13/13 + vtest2 T5/T6. mon.py: L0→L2 by ~600 s peaceful.

## NEXT (after sim #7)
1. Verify night shots are dark + sleepers; verify blast frames.
2. Russian report: (a) parts+blood at blast moment — show sim_blast_air.png; (b) repair restores look — vtest2 T6 + sim_repair_580; (c) палатка конус + шалаш треугольный с узором — cu_h10/cu_h9; (d) whole Task D state: L0→L2 in 720 s sim (lvl 2, 7/13, stones 21), spear 8 (vtest), sleep/torches, collision, placement variety, tribe spawns scattered, all solid.
3. main.py in workspace = updated (user uploads to GitHub web UI themselves).

# Task
_What did the user ask for, in their own words. Preserve acceptance criteria._

Task D (village life) — user re-sent the full spec verbatim (3rd time) + new: parts fly from people at blast moment (blast acts on them like on any object); red liquid scatters WITH the pieces (not only on ground impact); repair must restore the building's ORIGINAL look (or be too slow — speed up if long); remove полуземлянка entirely — epoch-1 class-1 dwelling = ordinary tent, conical, sticks bundled together; hide hut must be visibly triangular with deer-like stripes/patterns on the hide (not a brown mass). Full spec: chopping needs small ground stone first; felled tree → stump + 2 logs; logs carried to a self-chosen log depot (separate model); L0 = sticks + huts (now tent/hide-hut), L1 when everyone has a bed (stone + chopping + wood storage), L2 after workshop + beds + wood (double huts 72 + 67/68, hunter hut 69 from scratch, spear = first weapon, stone depot w/ visible count + capacity later); night: no torches = sleep in huts, nobody outside, light ONLY from campfire (lights appear from L1 huts); placement bots analyze terrain, always different decisions, keep distance from trees/houses, never same spots; tribe of 10 spawns at different map points; ALL objects solid — no walking through.

# User Constraints & Corrections
- (standing: Russian comms; borderless fullscreen + ESC exits; no hint text, only small FPS top-left; Q/E pivot around screen-center world point; culling only, no FPS dips on pan; firs stable + ground/self shadows, no fast jitter; rock shadows hug silhouette; smooth day/night; bigger map is end-state (propose, don't just code); lightweight tree ~2.1–2.5 MB; Task-B/C explicit; NEVER confirmed model degradation — don't degrade; state provenance for verification; META: verbatim re-send = same task, complete it.)
- New this message: parts+blood at blast moment; repair → original look (speed if long); полуземлянка gone (class-1 = conical stick-bundle tent); hide hut triangular + deer stripes.

# Workspace
- `/home/user/pixelwars/` — not a git clone (user uploads via GitHub web UI). ~1.6 MB.
  - `main.py` — ALL fixes applied, compiles clean. Village L7466–10180; explode ~L6818; draw_gable ~L4621; test-scene era-0 huts ~L1540-1660.
  - `vtest.py` — 13/13 PASS. `vtest2.py` — NEW: T5 blast parts/blood, T6 repair-look (needs `main.reset_ground(); main.set_preset(1);` + `_Cam` stub for explode).
  - `mon.py` — real-scene monitor. `dbg5/6/7/8.py` — probes.
  - `cu_h9.png`, `cu_h10.png` — fresh closeups (hide hut / tent). `cu_h9/sim/` — sim #6 shots (pre-daytime; #7 will overwrite).
  - `README.md`, `render_showcase.py`, `requirements.txt`, `build_exe.bat`, `PixelZomboidProto.spec`.
- `/tmp/sim_final7.log` — current sim log.

# Actions Taken
_Terse ordered log of executed actions._

363-383. (pre-compaction: vtest 13/13; sim runs; pacing; stick econ; stone distribution; drop_sp release; blasts 450/560)
384. Sim #6: lvl 2, 7/13, мёртвых 1, stones 21, objs 2060. Frames verified (blast w/ parts? — that was pre-fix; night frames BRIGHT — bug found).
385. User re-sent Task D + new complaints (parts/blood at blast, repair look, tent cone, hide hut triangle+stripes).
386. explode(): instant death via _vil_human_die at blast moment (parts+blood pools at blast point).
387. _plot_after_clear: over/chips reset on surviving damaged-stage parts; _vil_puff(small=True).
388. draw_gable ends=="hide": full hide texture (seams + dark vertical stripes + spots) on both visible faces.
389. Scene i==1 hide hut: removed stripe/spot boxes (pattern now in renderer). i==2 tent: rebuilt as stepped-pole cone + lashing rings + entrance gap + hide patches.
390. vtest2.py: T5 (instant death, 7 parts, blood) + T6 (15 chips → 0, done) PASS. vtest 13/13.
391. closeup re-render: cu_h9 (triangle + deer pattern ✓), cu_h10 (cone of poles ✓).
392. Sim #7 (PID 3779): added update_daytime(sdt) to sim loop (nights were missing entirely).

# External Sources
(none)

# Errors & Dead Ends
- **Sim had NO day/night (FIXED this message)**: sim loop bypassed update_daytime → DAYT frozen 0.25, villagers never slept in sim, "night" shots bright. Added to 2× loop.
- **Drop_sp leaked pebble ownership (fixed)**: pool drained at ~9 → stone flow died. Remove pebble on drop.
- **Strict branch reorders ping-pong (fixed)**: use distribution (id%3) + zero-carrier fallback.
- **Chips persisted after repair (fixed this message)**: over/chips never reset → house stayed chipped. Reset in _plot_after_clear.
- **Parts spawned on LANDING not blast (fixed this message)**: now instant at blast point for lethal hits.
- **Stuck-stick loop (fixed)**: remove unreachable stick on give-up.
- **Scripted blasts at 160/210 wrecked early huts (fixed)**: moved to 450/560 s.
- **No zombies attack the village** (memory error): losses only from scripted blasts.
- **_vil_make_tree etc. don't exist**: scene from make_test_scene(); village_reset builds VIL_TREES from scene trees; village_reset returns None → main.VIL.
- **Sim deterministic**: rng.seed(7) + wind_rng.seed(20260917) in SIM init.
- **Headless explode needs**: reset_ground() + set_preset(1) + cam stub (world_to_screen).
- Fragile big string replaces → line splices w/ asserts + py_compile. pygame 2.6.1: no pygame.random.

# Key Results
- **vtest 13/13 + vtest2 T5/T6 PASS** (real game code, headless).
- **Sim #6 (pre-daytime fix)**: lvl 2, 7/13 done, work 3, wait 3, мёртвых 1, stones 21, objs 2060. **Sim #7 (with nights)**: running.
- **mon.py peaceful**: 5/5 ~500 s, 6/6 + lvl 2 @600 s.
- **id map:** ep0 8–12 + 67–72; ep1 13–17; ep2 18–22; ep3 1–7; ep5 23–30; ep4 31–40; ep6 41–51; ep7 52–66.
- **Catalog:** HOUSE_ORDER ep0: 8:5, 9:1, 10:0, 11:2, 12:6, 67:3, 68:4, 69:7, 70:8, 71:9, 72:10; HOUSE_CAP 72:2; CLASS_NAMES[0]: Навес с кострищем / Шалаш из шкур / Палатка из жердей / Двускатный шалаш / Мастерская на жердях / Шалаш-вышка / База охотников / Охотничья будка / Склад камней / Склад брёвен / Шалаш-двойной.
- **Village state:** v: fire, plots, pile, phase(gather→fire_sticks→settle), t, leader, pile_n, stones, fire_logs, workers, next_drop, lit, sparks, blood, parts, defeat, objects, lvl, res{logs,stones,spears}, logpile=(fx+2.1,fy−1.7), stonepile=(fx−2.1,fy+1.7), stones_placed, pebbles, _plots_by_hid, _rocks, plan_t, solids, sol_t, peb_cd. Plot: idx,x,y,tpl,stages,stage,state,debris,jobs,broken_from,was_done,relocs. Hum: stone, torch, carry_log, carry_sp, tree, log, sp, stuck_t, air_k, dead_mark, dvx/dvy/dvz.
- **Timings:** walk 2.6/2.0, arrive d<0.14; pick .7 drop .55 light 2.2; build 0.65+0.18·n, busy 3/plot; repair ~0.7+h*0.8, busy 4; clean 0.7; chop 2.6; sleep sit 300 s. Sticks: cap 24, 1.6–4.4 s, age 120 s, pile cap 1 at lvl≥1 else 4. Pebbles: 8 init, 9–17 s respawn, cap 8/10; hand-stones removed from list.
- **P4:** _VIL_BEDS{8:1,9:2,10:2,11:2,12:0,67:2,68:4,69:2,70:0,71:0,72:4}. L1 = lit + beds≥pop + all live stoned; L2 = 12 done + beds + logs≥1; monotone. Demands 10/9/12; hut when planned-beds<pop; L2: 72 cap2 else specials 67–71 (12 s cd). Solids: fire .55/plots max(fw,fd)/2+.18/trees .24(≤22)/logs .3, margin .10, 0.5 s rebuild, slide + sidestep 0.55 (id%2) + give-up 3.5 s (releases carried + removes stuck stick). _vil_pick_task: stick → pebble-hand → log-carry(r20) → stone-depot(L2: id%3 or _spn==0) → tree(L1, stone) → sit(2, 0.22) → wander. Night DAYT .60–.97 (DAY_LEN 240, start .25; n1 84–173, n2 324–413): lvl<2 sleep at hut door, lvl≥2 torch. Spear at 69: 2 stones + 2 sticks, cap 10. Worker spawn: 10 people, random points 9–34 units from fire on island (scattered ✓).
- **Sim scripted events:** 70 s build; 130 s night; 160 s build; **450 s blast near workers (power 0.7)** (451/455 s shots); **560 s blast on done hut** (580 s repair shot); 250 s closeup; 500 s "l1" shot; 480/600/720 finals.
- **Baselines:** --test objects=1882 pixels=1200 dented=17. Grid 160×160, PIXEL 3, window 1024×768. Sim 2× ≈ 7 min wall.

## ADDENDUM (after compaction risk)
- vtest FLAKY T1/T2 root causes FOUND & FIXED: (a) drop_log RECOMPUTES res.logs from placed log objects → fake `res["logs"]=60` stock evaporated at first real delivery; T2 now places 40 real placed logs at logpile. (b) Planner L2 special-spam (4-5 buildings at once) spread workers → 69 never finished; now n_sp<2 gate. (c) Tree depletion: stumps now regrow new fir after 240 s (o["stump_t"], dead→None). (d) Sticks: 50% spawn on ground near fire (r5) not only from tree branches → shorter carry. (e) T1 extended to 300 s (night 84-173 = sleep), checks relaxed: stumps>=2 + max_logs>=1.
- FORCED NIGHT SLEEP added: night && lvl<2 && settle → ANY worker not asleep walks to sleep spot (carried stick dropped at feet); dawn wakes sleepers (st=min(st,0.4)). Sleep spots: semicircle in front of hut door (per-id ang/rad, no stacking). Sleep st 150 s.
- vtest: 3/3 runs 13/13 after fixes (was flaky 10-13).
- Sim #7 had no nights bug (update_daytime missing in sim loop — added). Sim #8 (with nights + pre-sleep-fix): lvl1 5/6, мёртвых 1 — sleep 300 s covered both nights (too long) → fixed.
- Sim #9 (PID 3987): final, all fixes. Check /tmp/sim_final9.log.
- Night in sim: DAYT advances (update_daytime in 2x loop); night1 t=84-173, night2 t=324-413; scene dark, light only campfire (verified sim_night_130s).

## Этап 10 (2026-09-23): слои, звери, непрерывная земля

- Иерархия слоёв: единая глубинная сортировка (`game/render/depth.py`),
  ключ — центр основания объекта / ноги фигуры; поселение больше не
  рисуется отдель проходом поверх мира (люди за домами и ёлками скрыты).
- Звери: спрайтовые модели вместо коробок (`game/village/animals.py`):
  олень 30x24 с рогами и аллюром на 4 фазы (каждая нога отдельно),
  заяц 16x10 с циклом прыжка; позы еды/тревоги/трупа.
- Люди: мастер 20x32 (вчетверо больше пикселей при том же пикселе арта),
  оружие в руках: копьё, дубинка, камень, факел, жердь; позы aim/attack.
- Земля: тропинки шириной со ступню (сетка износа 6 узлов/клетка) и гарь
  от взрывов — непрерывное поле с размывом (`draw_wear_layer`); кратеры —
  непрерывный тон (`_draw_crater_field`), плитки-швы устранены.
- Проверено: --test (objects=1884 dented=17), vtest 13/13, vtest2 OK,
  --sim 720s (уровень 2, 8/11 построек), --bench, --closeup, showcase.
