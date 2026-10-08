# Step-by-step rebuilds of the original sets

These scripts rebuild LEGO 10280 Flower Bouquet and 40725 Cherry Blossoms in LDraw, following their official instructions step by step. The output feeds the manual-style pages in [`../docs/sets/`](../docs/sets/).

| File | What it does |
|---|---|
| `model.py` | A small modelling kit. A `Model` holds parts and steps; a step can carry a callout (a sub-build with a "2x" count) and page details such as a rotate icon or a manual page number. Units are LDU, and -Y is up. |
| `s40725.py` | 40725, both branches (white, then pink), 19 steps each, plus the two branches together. |
| `s10280.py` | 10280, one section per flower in manual order (daisies, roses, poppy, grass, snapdragons, lavender, leaves, aster), plus the finished bouquet. |
| `pack.py` | Packs part geometry (faces, edge lines, silhouette lines) and the models into `docs/sets/<set>/data/set.js`. Part names come from `lego/parts_inventory.xlsx`. |
| `conn.py`, `thumbs.py` | Modelling aids: list a part's studs, holes and bars, and draw a part with its axes. |

Run `python instructions/s40725.py` and `python instructions/s10280.py`. Parts download on demand from the LDraw library mirror, the same way as in `pipeline/`.

The piece positions were worked out from the manual pictures. They are close, but not an official model.
