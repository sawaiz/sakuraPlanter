# Sakura Planter: project briefing

Read this first. It covers what the repo is, how the pieces fit, the history of the work, and what is still open.

## What this repo is
1. **Sakura Planter**: a 3D-printable planter and display kit. FreeCAD design in `cad/`, CORE One print plates in `print/`, fit-test kit, a 3D assembly page in `docs/`, shadow-box concept drafts in `concepts/`, LEGO part data in `lego/`, LDraw pipeline in `pipeline/`.
2. **Original-set manuals**: step-by-step 3D instruction pages for LEGO **10280 Flower Bouquet** and **40725 Cherry Blossoms**, styled after the printed manuals. Rebuilt by hand in LDraw. Pages in `docs/sets/<set>/`.
3. **Collision checker** (`instructions/check.py`): checks every placement and gives each step a slide-in direction.
4. **Assembly films** (`render/`): Blender Cycles animations built from the same data.

## Layout and how to rebuild
- `instructions/model.py` is the modelling kit (units LDU, -Y up; `Model.add/place/step`, groups, sub-builds).
- `instructions/s40725.py`, `s10280.py`: `build()` returns the models (and sub-builds). Running the file annotates every step with slide-in directions, then packs.
- `instructions/pack.py` writes `docs/sets/<set>/data/set.js` (int16 base64 geometry + steps + `ins`).
- `instructions/conn.py` lists studs, axles, pins and bars of a part. `thumbs.py` draws parts with axes.
- Rebuild: `python3 instructions/s40725.py` and `python3 instructions/s10280.py` (LDraw parts download on demand).
- Check: `python3 instructions/check.py 40725|10280 [model...]`. Cache `instructions/.checkcache.json` is gitignored.
- Pages: `docs/sets/lib/{viewer.js,scene.js,manual.css}`, three.js r170. Themes: `cherry` (40725, light blue) and `bouquet` (10280, grey). Serve with `python3 -m http.server 8766` from the repo root and open `/docs/sets/<set>/`.
- Films: see `render/README.md`. `render/render_all.sh 40725` / `10280` (`--preview` first). Needs Blender 4.2+ or pip `bpy`, ffmpeg, numpy. WSL with an NVIDIA driver uses OptiX/CUDA by itself.

### Checker details
- Voxel solid per part (RES 0.4, PAD 4, hole filling, signed distance field) plus surface sample points.
- Penetration ignores joint zones: axle/pin/pinhole radius 7.5, bar 5.5, stud/antistud 5.0, joint segment runs from the feature point along its axis for the connector length, plus 6.
- Thresholds: final fit 0.9, path 1.6, touch 0.6.
- `candidates()` tries engaged feature axes, part axes, world axes; `path_clear()` scans offsets. Result per step: `step['ins'] = [{p, d, k}]`, `k` in first / feature / part / world / blocked. The viewer skips `blocked` and `first`.

### Renderer details
- Reads `docs/sets/<set>/data/set.js` directly. Transparent PNG frames, laid over the set's page colour by `make_video.sh`.
- Studio HDRI at strength 0.32, exposure -0.3, 8 W key light scaled with distance, shadow-catcher floor. Tall thin models render 1080x1440, others 1920x1080.
- Models per film: 40725 `branch_white`, `branch_pink`, `final`. 10280 `daisy`, `rose_head`, `rose_stem_curved`, `rose_stem_straight`, `roses`, `poppy`, `grass`, `snap_head`, `snap_stem_curved`, `snap_stem_straight`, `snapdragons`, `big_leaf`, `lavender`, `aster`, `bouquet`.

## History (what was asked and done)
1. Sakura Planter repo: docs, CAD, plates, fit-test kit, 3D assembly page (`41e9c56`).
2. Find both original manuals and build step-by-step website subpages in the manual art style. Decisions: download the PDFs, full 3D at every step, link to official art only, extras = highlight new parts, click-a-part callout, 1:1 size check, progress + resume (`1cd24c1`).
3. Manual-style insertion arrows, flower heads, phone layout, studio lighting and reflections (`6fbdc5c`).
4. "Make sure the parts go in on a path that makes sense with no collisions" led to the physical checker (`56930ea`, `c8ae65a`), then slide-in paths wired into the viewer and bars seated in holders (`dd4eba5`).
5. Blender assembly films for both sets, viewer framing and rose fixes (`1b8de72`).
6. The user's render server (`sawaiz@10.50.0.211`, a Windows machine "CHIMERA" with WSL and an SSH server) could not be reached from the Claude cloud session or its device shell (sandbox, no LAN route, no key). Plan: run Claude Code on CHIMERA's WSL, or on the Mac, and render there.

## Open work (in priority order)
1. **Render the films**: `render/render_all.sh 40725 --preview`, check, then full 40725 and 10280. Outputs in `render/out/` (gitignored).
2. **40725 trunk section**: the axle/connector fit is wrong against manual pp. 4-6 (position/rotation scans did not fix it; it needs a redesign of the connector stack).
3. **Remaining overlaps** from `check.py`: blossoms on bricks (~1 mm), bar holders, and many 10280 ones (roses ~320, lavender ~223, aster ~137 flagged points).
4. **Blocked insertion paths**: reduce the count of steps with `k == 'blocked'`.
5. Re-run check.py, rebuild both sets, walk the pages in a browser (desktop and phone width), then commit and push.

## Gotchas
- Never `pkill -f` with a pattern that matches your own shell.
- A sub-build screenshot that looks empty is usually capture timing, not a bug.
- Open3D ray occupancy gives false positives on LDraw internal faces. Keep the voxel SDF approach.
- Piece positions come from manual pictures by hand; they are close but not an official model.
- Do not edit `docs/sets/*/data/set.js` by hand; regenerate it.
- Commit trailer: end commit messages with the attribution lines the session asks for.
