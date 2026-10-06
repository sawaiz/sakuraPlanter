"""Resolve interpenetrating decorative parts and re-attach floating ones.

Moves only decorative parts (petals, blossoms, leaves, buds...). Structural parts (axles, connectors,
pins, stems, twigs, anything plugged into the printed parts) never move.
Usage: relax.py <placements.json> <pla_dir> <voxel_templates.pkl> <out_placements.json>
"""
import json, sys, os, math, pickle, time
import numpy as np, trimesh, cv2
from scipy import ndimage
from manifold3d import Manifold, Mesh as MMesh

PL, PLA, TPL, OUTP = sys.argv[1:5]
P = json.load(open(PL)); A = json.load(open(os.path.join(PLA, 'anchors.json')))
T = pickle.load(open(TPL, 'rb'))
FINE, COARSE = 0.4, 0.8
def keys(pts, pitch):
    q = np.floor(pts / pitch).astype(np.int64) + 4096
    return (q[:, 0] << 26) | (q[:, 1] << 13) | q[:, 2]
def unkey(k, pitch):
    x = (k >> 26) - 4096; y = ((k >> 13) & 8191) - 4096; z = (k & 8191) - 4096
    return (np.stack([x, y, z], 1) + 0.5) * pitch
def slice_fill(m, pitch, surface=False):
    mf = Manifold(MMesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
    lo, hi = m.bounds
    lo = np.floor(lo / pitch) * pitch                 # align cells to the global voxel grid
    nx, ny = int(math.ceil((hi[0] - lo[0]) / pitch)) + 2, int(math.ceil((hi[1] - lo[1]) / pitch)) + 2
    zs = np.arange(lo[2] + pitch / 2, hi[2], pitch); occ = np.zeros((len(zs), ny, nx), bool)
    for k, z in enumerate(zs):
        polys = mf.slice(float(z)).to_polygons()
        if not polys: continue
        img = np.zeros((ny, nx), np.uint8)
        cv2.fillPoly(img, [np.round(((np.asarray(pg) - lo[:2]) / pitch - 0.5) * 16).astype(np.int32) for pg in polys], 1, cv2.LINE_8, 4)
        occ[k] = img.astype(bool)
    if surface: occ = occ & ~ndimage.binary_erosion(occ)
    else: occ = ndimage.binary_erosion(occ)
    kk, jj, ii = np.nonzero(occ)
    return np.stack([lo[0] + (ii + 0.5) * pitch, lo[1] + (jj + 0.5) * pitch, zs[kk]], 1)

FIXED_ROLES_PREFIX = ('Hidden', 'Branch joint', 'Daisy stem', 'Flower stem', 'Stem bend', 'Head axle', 'Through-axle',
                      'Twig root', 'Spur anchor', 'Twig', 'Spur node', 'Stalk adapter', 'Spike adapter', 'Spike core',
                      'Lavender stalk', 'Side stalk', 'Pin joining', 'Rose centre', 'Head base', 'Petal clip hub',
                      'Daisy centre', 'Blossom spray', 'Blossom whorl', 'Lavender bunch', 'Stamen / flower stalk')
def movable(p): return (not p['role'].startswith(FIXED_ROLES_PREFIX)) or p['group'] == 'Aster' and 'core' in p['role']
N = len(P)
mov = np.array([movable(p) for p in P])
disp = np.zeros((N, 3))
def part_keys(i, pitch, kind):
    p = P[i]; R = np.array(p['R']); t = np.array(p['p']) + disp[i]
    pts = T[p['part']]['solid' if kind == 'solid' else 'surf']
    return np.unique(keys(pts @ R.T + t, pitch))
# fixed obstacles: printed parts
pla_solid, pla_surf = [], []
names = ['sakura_planter.stl', 'sakura_soil_plate.stl', 'sakura_trunk.stl'] + [f'sakura_branch_{i + 1}.stl' for i in range(5)]
for j, f in enumerate(names):
    m = trimesh.load(os.path.join(PLA, f))
    if j >= 3:
        W = np.array(A['arms'][j - 3]['world']); M4 = np.eye(4); M4[:3, :] = W; m.apply_transform(M4)
    pla_solid.append(np.unique(keys(slice_fill(m, FINE), FINE)))
    pla_surf.append(np.unique(keys(slice_fill(m, COARSE, True), COARSE)))
PLA_ID = -1
solid = [part_keys(i, FINE, 'solid') for i in range(N)]
surf = [part_keys(i, COARSE, 'surf') for i in range(N)]
cent0 = np.array([unkey(s, FINE).mean(0) if len(s) else np.array(P[i]['p']) for i, s in enumerate(solid)])

def overlaps():
    K = np.concatenate(solid + pla_solid)
    I = np.concatenate([np.full(len(s), i) for i, s in enumerate(solid)] + [np.full(len(s), N + j) for j, s in enumerate(pla_solid)])
    o = np.argsort(K, kind='stable'); K, I = K[o], I[o]
    st = np.nonzero(np.r_[True, K[1:] != K[:-1]])[0]; en = np.r_[st[1:], len(K)]
    multi = np.nonzero(en - st > 1)[0]
    pair = {}
    for s_ in multi:
        ids = np.unique(I[st[s_]:en[s_]])
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                k = (int(ids[a]), int(ids[b])); pair.setdefault(k, []).append(K[st[s_]])
    return pair

t0 = time.time()
STEP, MAXD = 0.6, 18.0
history = []
for it in range(90):
    pair = overlaps()
    bad = {k: v for k, v in pair.items() if len(v) * FINE ** 3 >= 1.5}
    nclash = sum(1 for v in bad.values() if len(v) * FINE ** 3 >= 4.0)
    history.append((it, len(bad), nclash))
    if it % 5 == 0: print('iter', it, 'tight+clash', len(bad), 'clash', nclash, round(time.time() - t0, 1), 's', flush=True)
    if not bad: break
    moved = set(); push = np.zeros((N, 3)); cnt = np.zeros(N)
    for (a, b), ks in bad.items():
        oc = unkey(np.array(ks), FINE).mean(0)
        cands = [x for x in (a, b) if x < N and mov[x] and np.linalg.norm(disp[x]) < MAXD]
        if not cands: continue
        # move the smaller (or later-built) part
        x = min(cands, key=lambda i: (len(solid[i]), -i)) if len(cands) == 2 else cands[0]
        other = b if x == a else a
        cx = unkey(solid[x], FINE).mean(0) if len(solid[x]) else cent0[x]
        d = cx - oc
        if np.linalg.norm(d) < 0.3:
            oc2 = unkey(solid[other], FINE).mean(0) if other < N and len(solid[other]) else oc
            d = cx - oc2
        if np.linalg.norm(d) < 1e-6: d = np.random.default_rng(it).normal(size=3)
        push[x] += d / np.linalg.norm(d); cnt[x] += 1
    for x in np.nonzero(cnt)[0]:
        v = push[x]; n = np.linalg.norm(v)
        if n < 1e-6: v = np.random.default_rng(x + it).normal(size=3); n = np.linalg.norm(v)
        disp[x] += v / n * STEP
        solid[x] = part_keys(x, FINE, 'solid'); surf[x] = part_keys(x, COARSE, 'surf')
pair = overlaps()
remaining = {k: round(len(v) * FINE ** 3, 1) for k, v in pair.items() if len(v) * FINE ** 3 >= 1.5}

# ---------------------------------------------------------------- re-attach floating parts (contact = within ~1 coarse cell)
offs = np.array([(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)], np.int64)
off_k = (offs[:, 0] << 26) + (offs[:, 1] << 13) + offs[:, 2]
def neighbours():
    KC = np.concatenate(surf + pla_surf)
    IC = np.concatenate([np.full(len(s), i) for i, s in enumerate(surf)] + [np.full(len(s), N + j) for j, s in enumerate(pla_surf)])
    o = np.argsort(KC); return KC[o], IC[o]
def contacts_of(i, KCs, ICs):
    dk = np.unique((surf[i][:, None] + off_k[None, :]).ravel())
    pos = np.searchsorted(KCs, dk); ok_ = pos < len(KCs); pos, dk = pos[ok_], dk[ok_]
    pos = pos[KCs[pos] == dk]                 # only cells that really are occupied by another part
    out = set()
    for p0 in pos:
        j = p0
        while j < len(KCs) and KCs[j] == KCs[p0]:
            if ICs[j] != i: out.add(int(ICs[j]))
            j += 1
    return out
def graph():
    KCs, ICs = neighbours()
    adj = {i: contacts_of(i, KCs, ICs) for i in range(N)}
    return adj
def reachable(adj):
    root = set(range(N, N + 8)); seen = set(); stack = []
    for i in range(N):
        if adj[i] & root: seen.add(i); stack.append(i)
    while stack:
        n = stack.pop()
        for m in adj[n]:
            if m < N and m not in seen: seen.add(m); stack.append(m)
    return seen
adj = graph(); ok = reachable(adj)
floating0 = [i for i in range(N) if i not in ok]
print('floating before attach', len(floating0), flush=True)
cent = np.array([unkey(s, FINE).mean(0) if len(s) else np.array(P[i]['p']) + disp[i] for i, s in enumerate(solid)])
for rnd in range(3):
    fl = [i for i in range(N) if i not in ok]
    if not fl: break
    anchors_ = np.array(sorted(ok))
    for i in fl:
        # nearest supported part by voxel centroid
        d = np.linalg.norm(cent[anchors_] - cent[i], axis=1); tgt = anchors_[np.argmin(d)]
        tp = unkey(solid[tgt], FINE); dv = tp - cent[i]
        near = tp[np.argmin(np.linalg.norm(dv, axis=1))]
        v = near - cent[i]; dist = np.linalg.norm(v); v = v / max(dist, 1e-6)
        for k in range(int(dist / 0.4) + 2):
            disp[i] += v * 0.4
            surf[i] = part_keys(i, COARSE, 'surf'); solid[i] = part_keys(i, FINE, 'solid')
            ov = len(np.intersect1d(solid[i], solid[tgt])) * FINE ** 3
            if ov >= 1.0:
                disp[i] -= v * 0.4; surf[i] = part_keys(i, COARSE, 'surf'); solid[i] = part_keys(i, FINE, 'solid'); break
            KCs, ICs = np.sort(surf[tgt]), np.full(len(surf[tgt]), tgt)
            dk = np.unique((surf[i][:, None] + off_k[None, :]).ravel())
            if np.isin(dk, surf[tgt]).any(): break
        cent[i] = unkey(solid[i], FINE).mean(0) if len(solid[i]) else cent[i]
    adj = graph(); ok = reachable(adj)
floating = [i for i in range(N) if i not in ok]
pair = overlaps()
remaining = {k: round(len(v) * FINE ** 3, 1) for k, v in pair.items() if len(v) * FINE ** 3 >= 1.5}
for i in range(N):
    P[i]['p'] = (np.array(P[i]['p']) + disp[i]).round(3).tolist()
    P[i]['moved_mm'] = round(float(np.linalg.norm(disp[i])), 2)
json.dump(P, open(OUTP, 'w'))
mv = np.linalg.norm(disp, axis=1)
print(json.dumps({'iterations': len(history), 'start': history[0], 'end_tight_or_clash': len(remaining),
                  'end_clash': sum(1 for v in remaining.values() if v >= 4.0), 'floating_before': len(floating0), 'floating_after': len(floating),
                  'parts_moved': int((mv > 0.01).sum()), 'median_move_mm': round(float(np.median(mv[mv > 0.01])) if (mv > 0.01).any() else 0, 2),
                  'max_move_mm': round(float(mv.max()), 2)}))
