# Assembly animations (Blender)

Realistic step-by-step build films of the two original sets, rendered with Cycles from the same data the web pages
use. Nothing needs exporting: `blender_anim.py` reads `docs/sets/<set>/data/set.js` (part meshes, colours,
placements, steps, and the slide-in direction `instructions/check.py` found for every piece).

## What you get

- Each step, the new pieces slide in along their checked direction and seat; pieces of one step arrive one after another.
- The camera glides to frame what is built so far (it makes room for pieces still sliding in), then the finished model turns once.
- Studio lighting from the same HDRI the web pages use, glossy clear-coat plastic, a soft key light, and a contact
  shadow on the floor. Frames are transparent PNGs; `make_video.sh` lays them over the page colour of the set
  (light blue for 40725, grey for 10280).
- Tall thin models (stems, branches) get a portrait 1080x1440 frame, the rest 1920x1080 (`--res WxH` to override).

## Run it

You need Blender 4.2 or newer (any recent release works), or the `bpy` module from pip, and ffmpeg.

```bash
# whole film of a set: renders every model, makes one mp4 per model, joins them into render/out/<set>.mp4
render/render_all.sh 40725
render/render_all.sh 10280

# fast look first (480x270, 12 samples)
render/render_all.sh 40725 --preview

# one model, at your own settings
blender -b -P render/blender_anim.py -- --set 10280 --model rose_head --out render/frames/10280/rose_head --samples 96
render/make_video.sh 10280 render/frames/10280/rose_head
```

Options for `blender_anim.py`: `--res`, `--samples` (default 128), `--fps` (30), `--step-seconds` (1.6),
`--turntable-seconds` (5), `--device auto|cpu|gpu`, `--start/--end` (render only some frames, so one clip can be split
across machines), `--preview`, `--list` (print the models of a set).

On a machine with an NVIDIA GPU (also under WSL with the CUDA driver) it picks OptiX or CUDA by itself. Finished clips
are skipped when you run `render_all.sh` again, so an interrupted run resumes where it stopped.

## Models per film

- 40725: `branch_white`, `branch_pink`, `final`
- 10280: `daisy`, `rose_head`, `rose_stem_curved`, `rose_stem_straight`, `roses`, `poppy`, `grass`, `snap_head`,
  `snap_stem_curved`, `snap_stem_straight`, `snapdragons`, `big_leaf`, `lavender`, `aster`, `bouquet`

The sub-builds shown in the callouts of the web pages move in as whole units inside their step; they are not played
separately in the films.

## Known limits

- Pieces are rebuilt from the manuals by hand, so a few joints are not millimetre-exact; `instructions/check.py` lists
  the ones it still flags (the trunk axle fit in 40725, some blossom-on-brick clashes, many of the 10280 sprigs).
- LDraw has no transparency data in the page files, so clear parts (there are none in these two sets) would render opaque.
