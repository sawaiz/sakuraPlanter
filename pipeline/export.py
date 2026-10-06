"""Export the Sakura Planter: LDraw MPD (BrickLink Studio / LeoCAD / LDView) + compact viewer data for docs/.

usage: export.py <model_dir with placements.json> <pla_dir with anchors.json> <out_dir>   (env FCOUT = cad/out)
"""
import json, os, sys, base64, math
import numpy as np, trimesh
import ldraw

M, PLA, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
P = json.load(open(os.path.join(M, 'placements.json')))
anch = json.load(open(os.path.join(PLA, 'anchors.json')))
cols = ldraw.colours(ldraw.fetch('LDConfig.ldr'))
LDCOL = {'Black': 0, 'Bright Pink': 29, 'Dark Bluish Gray': 72, 'Dark Green': 288, 'Dark Pink': 5, 'Dark Purple': 85,
         'Dark Turquoise': 3, 'Green': 2, 'Lavender': 31, 'Light Bluish Gray': 71, 'Light Nougat': 78, 'Lime': 27,
         'Magenta': 26, 'Medium Lavender': 30, 'Orange': 25, 'Pearl Gold': 297, 'Red': 4, 'Reddish Brown': 70,
         'Sand Green': 378, 'Tan': 19, 'White': 15, 'Yellow': 14, 'Yellowish Green': 326, 'Dark Red': 320}
C = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)     # world-mm (Z up) -> LDraw axes (-Y up)
S = 2.5                                                       # mm -> LDU

FC = os.environ.get('FCOUT')
BONE, BLACK, CLEAR = 0x2EDE4D3, 0x2202020, 0x2D8E4E6      # LDraw direct colours (0x2RRGGBB)
import math as _m
_d = anch['dims']; _P = anch['params']
def _mz(x, y, z, R=None):
    M = np.zeros((3, 4)); M[:, :3] = np.eye(3) if R is None else R; M[:, 3] = (x, y, z); return M
PAINT = {'bark': 0x26B3F2A, 'petal': 0x2F2A7C3, 'centre': 0x2B5285A, 'bud': 0x2E0607E}
PLA_PARTS = [('sakura_planter', 'Planter_world.stl', None, BONE, 'Planter'),
             ('sakura_soil_core', 'SoilCore_world.stl', None, BONE, 'Soil core'),
             ('sakura_soil_mat', 'SoilMat_world.stl', None, BLACK, 'Soil mat'),
             ('sakura_trunk', 'Trunk_world.stl', None, BONE, 'Trunk')] + \
            [(f'sakura_branch_{i + 1}', f'Branch{i + 1}.stl', np.array(anch['arms'][i]['world']), BONE, f'Branch {i + 1}') for i in range(5)]
for k in range(6):
    a = _m.radians(60 * k)
    PLA_PARTS.append((f'sakura_foot', 'Foot.stl', _mz(_d['foot_r'] * _m.cos(a), _d['foot_r'] * _m.sin(a), _d['planter_bottom_z'] - (_P['foot_h'] - _P['foot_pocket_h'])), CLEAR, f'Foot {k + 1}'))
for h in anch['pin_holes']:
    if h['label'].startswith('stub-') and h['label'].endswith('-pin'):
        z = np.array(h['dir']); x = np.array(h['x']); y = np.cross(z, x)
        PLA_PARTS.append(('sakura_joint_sleeve', 'JointSleeve.stl', _mz(*h['origin'], R=np.column_stack([x, y, z])), CLEAR, 'Joint sleeve'))
for cat, col in PAINT.items():
    if os.path.exists(os.path.join(FC, f'Paint_{cat}_world.stl')):
        PLA_PARTS.append((f'sakura_paint_{cat}', f'Paint_{cat}_world.stl', None, col, f'Paint {cat}'))
ORDER = ['Structure', 'Stems', 'Ground cover', 'Roses', 'Aster', 'Poppies', 'Lavender', 'Snapdragons', 'Foliage', 'Daisies', 'Canopy']

def fmt(v): return ('%.3f' % v).rstrip('0').rstrip('.') if abs(v) > 1e-9 else '0'

# ---------------------------------------------------------------- MPD
lines = ['0 FILE sakura_planter.ldr', '0 Sakura Planter - LEGO 10280 + 40725 remix with 3D-printed PLA parts',
         '0 Name: sakura_planter.ldr', '0 Author: sakuraPlanter', '0 !LICENSE Redistributable under CCAL version 2.0 : see CAreadme.txt', '']
lines.append('0 // Step 1: printed parts (PLA bone: planter, soil core, trunk, 5 branches; TPU black: soil mat; TPU clear: 6 feet, 5 sleeves; acrylic paint in the motif)')
for name, f, Mw, col, _ in PLA_PARTS:
    if Mw is None:
        R, t = np.eye(3), np.zeros(3)
    else:
        R, t = Mw[:, :3], Mw[:, 3]
    Rl = C @ R @ C.T; pl = S * C @ t
    lines.append('1 %d %s %s %s.dat' % (col, ' '.join(fmt(v) for v in pl), ' '.join(fmt(v) for v in Rl.ravel()), name))
lines.append('0 STEP')
for g in ORDER:
    lines.append(f'0 // {g}')
    for p in [p for p in P if p['group'] == g]:
        R = np.array(p['R']); t = np.array(p['p'])
        Rl = C @ R; pl = S * C @ t                  # R maps LDraw-local (LDU) -> world mm axes
        lines.append('1 %d %s %s %s.dat' % (LDCOL[p['colour']], ' '.join(fmt(v) for v in pl), ' '.join(fmt(v) for v in Rl.ravel()), p['part']))
    lines.append('0 STEP')
lines.append('0 NOFILE')
for name, f, Mw, col, title in PLA_PARTS:
    m = trimesh.load(os.path.join(FC, f))
    if any(l == f'0 FILE {name}.dat' for l in lines): continue
    lines += ['', f'0 FILE {name}.dat', f'0 {title} (3D-printed part, not a LEGO part)', f'0 Name: {name}.dat',
              '0 Author: sakuraPlanter', '0 !LDRAW_ORG Unofficial_Part', '0 BFC CERTIFY CCW']
    V = (S * (C @ m.vertices.T)).T
    for tri in m.faces:
        a, b, c = V[tri]
        lines.append('3 16 ' + ' '.join(fmt(x) for x in np.concatenate([a, b, c])))
    lines.append('0 NOFILE')
open(os.path.join(OUT, 'sakura_planter.mpd'), 'w').write('\n'.join(lines) + '\n')

# ---------------------------------------------------------------- viewer data (Y-up, mm)
T = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)      # world-mm Z-up -> three.js Y-up
def hexcol(code):
    if code >= 0x2000000: return '#%06X' % (code & 0xFFFFFF)
    return cols[code][1] if code in cols else '#888888'
geoms, insts = {}, []
group_ids = {g: i for i, g in enumerate(ORDER + ['PLA'])}
for p in P:
    pid = p['part']
    if pid not in geoms:
        V, Cc = ldraw.tris(pid + '.dat')
        geoms[pid] = (V, Cc)
uniq = {}
for pid, (V, Cc) in geoms.items():
    # split into inherited-colour triangles and fixed-colour ones (rare)
    inh = V[(Cc == 16) | (Cc == 24)]
    fixed = {int(c): V[Cc == c] for c in set(Cc.tolist()) if c not in (16, 24)}
    uniq[pid] = (inh, fixed)
def pack(tris_ldu):
    """int16-quantised triangle soup in LDU with per-part scale."""
    if len(tris_ldu) == 0: return None
    flat = tris_ldu.reshape(-1, 3)
    m = float(np.abs(flat).max()) or 1.0
    q = np.round(flat / m * 32767).astype(np.int16)
    return {'s': m, 'n': len(flat), 'b': base64.b64encode(q.tobytes()).decode()}
G = {}
for pid, (inh, fixed) in uniq.items():
    G[pid] = {'inh': pack(inh), 'fixed': [{'c': hexcol(c), 'g': pack(v)} for c, v in fixed.items() if len(v)]}
for p in P:
    R = T @ np.array(p['R']) * 0.4; t = T @ np.array(p['p'])
    insts.append([p['part'], hexcol(LDCOL[p['colour']]), group_ids[p['group']]] + [round(float(x), 4) for x in R.ravel()] + [round(float(x), 2) for x in t])
pla = []
for name, f, Mw, col, title in PLA_PARTS:
    m = trimesh.load(os.path.join(FC, f))
    v = m.vertices.copy()
    if Mw is not None: v = (Mw[:, :3] @ v.T).T + Mw[:, 3]
    v = (T @ v.T).T
    tri = v[m.faces].reshape(-1, 3)
    mx = float(np.abs(tri).max())
    q = np.round(tri / mx * 32767).astype(np.int16)
    pla.append({'name': title, 'c': hexcol(col), 's': mx, 'n': len(tri), 'b': base64.b64encode(q.tobytes()).decode(), 'clear': col == CLEAR})
data = {'geoms': G, 'inst': insts, 'pla': pla, 'groups': ORDER + ['PLA']}
s = json.dumps(data, separators=(',', ':'))
open(os.path.join(OUT, 'viewer_data.js'), 'w').write('window.SAKURA=' + s + ';')
print('mpd lines', len(lines), 'viewer data MB', round(len(s) / 1e6, 2), 'unique parts', len(G))
