# Concepts: shelf pieces that use LEGO for the structure

Drafts that came after the planter, built to use less printed material. Generated files go in `work/`, which is not committed. The renders are in `renders/`.

| Script | What it does |
|---|---|
| `library.py` | Splits `lego/placements.json` into reusable flower heads and cherry branches. Writes `work/library.json`. |
| `kit.py` | Shared helpers: a Scene of LEGO placements and printed meshes, and simple solids. |
| `compose.py` | The first six drafts: scroll, stone, trellis and three paired versions. |
| `shadowbox.py` | The shadow box. Moon, Climbing vine and Cascade have a fabric back. Garden wall has a flat-printed back wall and fabric sides. |
| `pack.py` | Packs each composed scene for `render.html`. |
| `render.html` | Three.js renderer using the docs HDR and procedural linen. Example: `render.html?c=sb_dense&az=30`. |

Run order: `python concepts/library.py`, then `python concepts/compose.py` and `python concepts/shadowbox.py`, then `python concepts/pack.py`. To view a scene, serve the repository root and open `concepts/render.html?c=<name>`.

The flower heads are placeholders taken from the planter model.
