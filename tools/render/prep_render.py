"""Prepare inputs for blender_hero.py: hi-res LEGO meshes (npz) and world-frame printed parts.
usage: python tools/render/prep_render.py   -> pipeline/work/render/
"""
import json, math, os, sys
import numpy as np, trimesh
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import ldraw_hi, ldraw                                         # noqa: E402  (hi-res primitives)
FC = os.path.join(ROOT, 'cad', 'out'); OUT = os.path.join(ROOT, 'pipeline', 'work', 'render'); os.makedirs(os.path.join(OUT, 'stl'), exist_ok=True)
P = json.load(open(os.path.join(ROOT, 'lego', 'placements.json')))
ids = sorted(set(p['part'] for p in P)); ldraw.prefetch([i + '.dat' for i in ids])
arrs = {}
for pid in ids:
    V, C = ldraw.tris(pid + '.dat'); arrs[pid + '_v'] = (V.reshape(-1, 3) * 0.4).astype(np.float32); arrs[pid + '_c'] = C.astype(np.int32)
np.savez_compressed(os.path.join(OUT, 'parts_hi.npz'), **arrs)
A = json.load(open(os.path.join(FC, 'anchors.json'))); d = A['dims']; prm = A['params']
def mz(x, y, z, R=None):
    M = np.zeros((3, 4)); M[:, :3] = np.eye(3) if R is None else R; M[:, 3] = (x, y, z); return M
spec = [('Planter_world.stl', None, 'bone', 'planter', (0, 0, 1)), ('SoilCore_world.stl', None, 'bone', 'soilcore', (0, 0, 1)),
        ('SoilMat_world.stl', None, 'tpu_black', 'soilmat', (0, 0, 1)), ('Trunk_world.stl', None, 'bark', 'trunk', (0, 0, 1))]
for i, am in enumerate(A['arms']):
    W = np.array(am['world']); spec.append((f'Branch{i + 1}.stl', W, 'bark', f'branch{i + 1}', tuple(W[:, 2])))
for k in range(6):
    a = math.radians(60 * k)
    spec.append(('Foot.stl', mz(d['foot_r'] * math.cos(a), d['foot_r'] * math.sin(a), d['planter_bottom_z'] - (prm['foot_h'] - prm['foot_pocket_h'])), 'tpu_clear', f'foot{k + 1}', (0, 0, 1)))
k = 0
for h in A['pin_holes']:
    if h['label'].startswith('stub-') and h['label'].endswith('-pin'):
        z = np.array(h['dir']); x = np.array(h['x']); k += 1
        spec.append(('JointSleeve.stl', mz(*h['origin'], R=np.column_stack([x, np.cross(z, x), z])), 'tpu_clear', f'sleeve{k}', tuple(z)))
for cat in ('bark', 'petal', 'centre', 'bud'):
    spec.append((f'Paint_{cat}_world.stl', None, 'paint_' + cat, 'paint_' + cat, (0, 0, 1)))
out = []
for f, M, mat, name, axis in spec:
    m = trimesh.load(os.path.join(FC, f))
    if M is not None: m.vertices = (M[:, :3] @ m.vertices.T).T + M[:, 3]
    p = os.path.join(OUT, 'stl', name + '.stl'); m.export(p)
    out.append({'file': p, 'mat': mat, 'name': name, 'axis': [float(a) for a in axis]})
json.dump(out, open(os.path.join(OUT, 'parts.json'), 'w'), indent=1)
print(len(ids), 'LEGO part types,', len(out), 'printed meshes ->', OUT)
