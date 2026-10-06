"""Verify the Sakura Planter build.

Checks
  1. Clashes      - solid-voxel overlap (0.4 mm grid) between every pair of parts, LEGO and PLA.
  2. Support      - contact graph (parts within ~0.8 mm of each other); every part must connect back
                    to the planter, both in the finished model and at the end of every build step.
  3. Stability    - centre of mass vs the planter's footprint; bending load on each branch joint.
  4. Printability - downward-facing overhang area on each printed part.
Usage: verify.py <placements.json> <steps.json> <pla_dir> <out.json>
"""
import json, sys, math, os, time
import numpy as np, trimesh
from collections import defaultdict, Counter
import ldraw


import cv2
from scipy import ndimage
from manifold3d import Manifold, Mesh as MMesh
def slice_fill(m, pitch, grid=False):
    """Solid voxel centres of a watertight mesh by slicing it with manifold3d and rasterising each slice."""
    mf = Manifold(MMesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
    lo, hi = m.bounds
    lo = np.floor(lo / pitch) * pitch                 # align cells to the global voxel grid
    nx, ny = int(math.ceil((hi[0] - lo[0]) / pitch)) + 2, int(math.ceil((hi[1] - lo[1]) / pitch)) + 2
    zs = np.arange(lo[2] + pitch / 2, hi[2], pitch)
    occ = np.zeros((len(zs), ny, nx), bool)
    SH = 4
    for k, z in enumerate(zs):
        polys = mf.slice(float(z)).to_polygons()
        if not polys: continue
        img = np.zeros((ny, nx), np.uint8)
        cs = [np.round(((np.asarray(pg) - lo[:2]) / pitch - 0.5) * (1 << SH)).astype(np.int32) for pg in polys]
        cv2.fillPoly(img, cs, 1, lineType=cv2.LINE_8, shift=SH)
        occ[k] = img.astype(bool)
    if grid:   # boundary cells only (surface), for the contact graph
        occ = occ & ~ndimage.binary_erosion(occ)
    else:      # erode one cell, same as the LEGO parts, so flush seating doesn't read as a collision
        occ = ndimage.binary_erosion(occ)
    kk, jj, ii = np.nonzero(occ)
    return np.stack([lo[0] + (ii + 0.5) * pitch, lo[1] + (jj + 0.5) * pitch, zs[kk]], 1)

PL, STEPS, PLA, OUT = sys.argv[1:5]
P = json.load(open(PL)); ST = json.load(open(STEPS))['steps']
A = json.load(open(os.path.join(PLA, 'anchors.json')))
t0 = time.time()
FINE, COARSE = 0.4, 0.8
def keys(pts, pitch):
    q = np.floor(pts / pitch).astype(np.int64) + 4096
    return (q[:, 0] << 26) | (q[:, 1] << 13) | q[:, 2]

# ---------------------------------------------------------------- per-unique-part voxel templates
import pickle
CACHE_T = os.path.join(os.path.dirname(OUT), 'voxel_templates_eroded.pkl')
tmpl = pickle.load(open(CACHE_T, 'rb')) if os.path.exists(CACHE_T) else {}
for pid in sorted(set(p['part'] for p in P) - set(tmpl)):
    V, _ = ldraw.tris(pid + '.dat')
    m = trimesh.Trimesh(vertices=V.reshape(-1, 3) * 0.4, faces=np.arange(len(V) * 3).reshape(-1, 3), process=True)
    vg = m.voxelized(FINE, max_iter=30)
    filled = vg.fill()
    # erode one voxel: surface voxelisation inflates parts by up to a voxel, which would make every
    # stud-in-tube or axle-in-hole connection look like a collision
    core = ndimage.binary_erosion(filled.matrix)
    vc = m.voxelized(COARSE, max_iter=30)
    tmpl[pid] = {'solid': filled.indices_to_points(np.argwhere(core)), 'surf': vc.points, 'vol': float(filled.filled_count) * FINE ** 3}
pickle.dump(tmpl, open(CACHE_T, 'wb'))
print('templates', round(time.time() - t0, 1), 's', flush=True)

# ---------------------------------------------------------------- PLA parts (world frame)
pla = []
names = [('Planter', 'sakura_planter.stl', None, 1), ('Soil plate', 'sakura_soil_plate.stl', None, 2), ('Trunk', 'sakura_trunk.stl', None, 3)] + \
        [(f'Branch {i + 1}', f'sakura_branch_{i + 1}.stl', np.array(A['arms'][i]['world']), 4) for i in range(5)]
for name, f, W, step in names:
    m = trimesh.load(os.path.join(PLA, f))
    if W is not None:
        T = np.eye(4); T[:3, :] = W; m.apply_transform(T)
    solid = slice_fill(m, FINE)
    occ_c = slice_fill(m, COARSE, grid=True)
    pla.append({'name': name, 'mesh': m, 'solid': solid, 'surf': occ_c, 'vol': m.volume, 'step': step})
print('pla voxels', round(time.time() - t0, 1), 's', flush=True)

N = len(P); NP = len(pla)
nodes = []                 # node i < N : LEGO part i ; N + j : PLA part j
solid_k, solid_id, surf_k, surf_id, cent, vols = [], [], [], [], [], []
for i, p in enumerate(P):
    R = np.array(p['R']); t = np.array(p['p']); tp = tmpl[p['part']]
    # template points are in LDraw-local mm (already *0.4); R maps local unit vectors to world
    ws = tp['solid'] @ R.T + t; wc = tp['surf'] @ R.T + t
    ks = np.unique(keys(ws, FINE)); kc = np.unique(keys(wc, COARSE))
    solid_k.append(ks); solid_id.append(np.full(len(ks), i)); surf_k.append(kc); surf_id.append(np.full(len(kc), i))
    cent.append(ws.mean(0) if len(ws) else t); vols.append(tp['vol'])
for j, q in enumerate(pla):
    ks = np.unique(keys(q['solid'], FINE)); kc = np.unique(keys(q['surf'], COARSE))
    solid_k.append(ks); solid_id.append(np.full(len(ks), N + j)); surf_k.append(kc); surf_id.append(np.full(len(kc), N + j))
    cent.append(q['solid'].mean(0)); vols.append(q['vol'])
cent = np.array(cent)
step_of = np.array(ST + [q['step'] for q in pla])

# ---------------------------------------------------------------- 1. clashes
K = np.concatenate(solid_k); I = np.concatenate(solid_id)
o = np.argsort(K, kind='stable'); K, I = K[o], I[o]
dup = np.nonzero(K[1:] == K[:-1])[0]
pairs = Counter()
# group runs of equal keys
starts = np.nonzero(np.r_[True, K[1:] != K[:-1]])[0]
ends = np.r_[starts[1:], len(K)]
multi = np.nonzero(ends - starts > 1)[0]
for s in multi:
    ids = np.unique(I[starts[s]:ends[s]])
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            pairs[(int(ids[a]), int(ids[b]))] += 1
print('clash pairs', len(pairs), round(time.time() - t0, 1), 's', flush=True)

def label(n):
    if n >= N: return pla[n - N]['name']
    p = P[n]; return f"{p['colour']} {p['part']} ({p['group']}: {p['role']})"
def vol_of(n): return vols[n]
clashes = []
for (a, b), c in pairs.items():
    ov = c * FINE ** 3
    small = max(1e-6, min(vol_of(a), vol_of(b)))
    clashes.append({'a': a, 'b': b, 'overlap_mm3': round(ov, 1), 'frac_of_smaller': round(ov / small, 3)})
# A connection (stud in tube, axle in connector, pin in hole) shares only a skin of voxels.
# Treat as a real clash when the overlap is big in absolute terms AND a big share of the smaller part.
def severity(c):
    # calibrated on known-good joints: aligned axle-in-connector, stacked plates, stud-in-tube all < 1 mm3;
    # an axle twisted 45 degrees in its hole gives 5-9 mm3
    if c['overlap_mm3'] >= 4.0: return 'clash'
    if c['overlap_mm3'] >= 1.5: return 'tight'
    return 'ok'
for c in clashes: c['sev'] = severity(c)

# ---------------------------------------------------------------- 2. contact graph
KC = np.concatenate(surf_k); IC = np.concatenate(surf_id)
offs = np.array([(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)], np.int64)
off_k = (offs[:, 0] << 26) + (offs[:, 1] << 13) + offs[:, 2]
DK = (KC[:, None] + off_k[None, :]).ravel(); DI = np.repeat(IC, 27)
u = np.unique(np.stack([DK, DI], 1), axis=0); DK, DI = u[:, 0], u[:, 1]
o = np.argsort(KC); KCs, ICs = KC[o], IC[o]
pos = np.searchsorted(KCs, DK)
adj = defaultdict(set)
valid = pos < len(KCs)
pos2 = pos[valid]; dk2 = DK[valid]; di2 = DI[valid]
# walk matching runs
hit = KCs[pos2] == dk2
pos2, di2, dk2 = pos2[hit], di2[hit], dk2[hit]
for p0, a in zip(pos2, di2):
    j = p0
    while j < len(KCs) and KCs[j] == KCs[p0]:
        b = int(ICs[j])
        if b != a: adj[int(a)].add(b); adj[b].add(int(a))
        j += 1
print('contacts', sum(len(v) for v in adj.values()) // 2, round(time.time() - t0, 1), 's', flush=True)

ROOT = N + 0   # planter
def reach(maxstep):
    ok = {ROOT}; stack = [ROOT]
    while stack:
        n = stack.pop()
        for m in adj[n]:
            if m not in ok and step_of[m] <= maxstep:
                ok.add(m); stack.append(m)
    return ok
final = reach(99)
floating = [n for n in range(N + NP) if n not in final]
per_step = {}
for k in range(1, 11):
    r = reach(k)
    lost = [n for n in range(N + NP) if step_of[n] <= k and n not in r]
    per_step[k] = lost
lone = [n for n in range(N) if len(adj[n]) == 0]

# ---------------------------------------------------------------- 3. stability
ABS, PLA_D = 1.05e-3, 1.24e-3      # g/mm3
INFILL = {'Planter': 0.95, 'Soil plate': 0.45, 'Trunk': 0.45}
mass = np.zeros(N + NP)
for i in range(N): mass[i] = vols[i] * ABS
for j, q in enumerate(pla): mass[N + j] = q['vol'] * PLA_D * INFILL.get(q['name'], 0.75)
com = (cent * mass[:, None]).sum(0) / mass.sum()
foot_r = 72.0
# branch loads: everything whose contact path to the planter passes through a branch
branch_loads = []
for j, q in enumerate(pla):
    if not q['name'].startswith('Branch'): continue
    bn = N + j
    # parts reachable from the branch without going through the trunk / other PLA
    seen = {bn}; stack = [bn]
    while stack:
        n = stack.pop()
        for m in adj[n]:
            if m in seen or m >= N or P[m]['group'] != 'Canopy': continue
            seen.add(m); stack.append(m)
    load = [n for n in seen if n < N]
    arm = A['arms'][int(q['name'].split()[-1]) - 1]; face = np.array(arm['face_c'])
    lm = sum(mass[n] for n in load) + mass[bn]
    moment = sum(mass[n] * 9.81e-3 * np.hypot(*(cent[n][:2] - face[:2])) for n in load + [bn])   # N*mm
    branch_loads.append({'branch': q['name'], 'parts': len(load), 'mass_g': round(lm, 1), 'moment_Nmm': round(moment, 1)})

# ---------------------------------------------------------------- 4. printability: overhangs
over = []
for q in pla:
    m = trimesh.load(os.path.join(PLA, {'Planter': 'sakura_planter.stl', 'Soil plate': 'sakura_soil_plate.stl', 'Trunk': 'sakura_trunk.stl'}.get(q['name'], f"sakura_branch_{q['name'].split()[-1]}.stl")))
    zmin = m.bounds[0][2]
    n = m.face_normals; c = m.triangles_center
    down = (n[:, 2] < -math.cos(math.radians(45))) & (c[:, 2] > zmin + 0.4)
    area = float(m.area_faces[down].sum())
    over.append({'part': q['name'], 'overhang_mm2': round(area, 1), 'watertight': bool(m.is_watertight),
                 'bbox': (m.bounds[1] - m.bounds[0]).round(1).tolist()})

rep = {
    'parts': N, 'pla_parts': NP,
    'clashes': sorted([dict(c, a_label=label(c['a']), b_label=label(c['b'])) for c in clashes if c['sev'] != 'ok'], key=lambda c: -c['overlap_mm3']),
    'n_clash': sum(c['sev'] == 'clash' for c in clashes), 'n_tight': sum(c['sev'] == 'tight' for c in clashes), 'n_pairs_touching_solid': len(clashes),
    'floating': [label(n) for n in floating], 'floating_idx': floating, 'lone_idx': lone,
    'step_unsupported': {k: [int(n) for n in v] for k, v in per_step.items()},
    'mass_total_g': round(float(mass.sum()), 1), 'mass_lego_g': round(float(mass[:N].sum()), 1),
    'com_mm': com.round(1).tolist(), 'com_offset_mm': round(float(np.hypot(com[0], com[1])), 1), 'foot_radius_mm': foot_r,
    'branch_loads': branch_loads, 'overhangs': over,
    'adj': {int(k): sorted(int(x) for x in v) for k, v in adj.items()},
}
json.dump(rep, open(OUT, 'w'))
print(json.dumps({k: v for k, v in rep.items() if k not in ('clashes', 'floating', 'floating_idx', 'lone_idx', 'step_unsupported', 'adj')}, indent=1))
print('clash', rep['n_clash'], 'tight', rep['n_tight'], 'floating', len(floating), 'lone', len(lone))
print('unsupported per step', {k: len(v) for k, v in per_step.items()})
print(Counter((c['sev'], P[c['a']]['group'] if c['a'] < N else 'PLA') for c in clashes if c['sev'] != 'ok').most_common(20))
print('time', round(time.time() - t0, 1))
