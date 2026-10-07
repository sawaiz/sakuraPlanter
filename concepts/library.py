"""Split the current LEGO model into reusable units: flower heads (with their own frame) and cherry branches.

Each unit is a list of parts in a local frame: head units have their stem axis along +Z with the stem
top at the origin; branch units keep the printed-branch frame (x along the branch, z through its thickness)
and get a LEGO-built core in place of the printed branch.  -> concepts/work/library.json
"""
import json, math, os, collections
import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = json.load(open(os.path.join(ROOT, 'lego', 'placements.json')))
A = json.load(open(os.path.join(ROOT, 'cad', 'out', 'anchors.json')))
os.makedirs(os.path.join(ROOT, 'concepts', 'work'), exist_ok=True)

def frame_from_axis(t):
    t = t / np.linalg.norm(t); a = np.array([1.0, 0, 0]) if abs(t[0]) < 0.9 else np.array([0, 1.0, 0])
    x = a - t * a.dot(t); x /= np.linalg.norm(x); y = np.cross(t, x); return np.column_stack([x, y, t])   # local -> world
def to_local(idx, origin, R):
    out = []
    for i in idx:
        p = P[i]; Rw = np.array(p['R']); pw = np.array(p['p'])
        out.append({'part': p['part'], 'colour': p['colour'], 'R': (R.T @ Rw).round(6).tolist(), 'p': (R.T @ (pw - origin)).round(3).tolist(), 'role': p['role']})
    return out

units = {}
SKIP_ROLES = ('Hidden', 'Flower stem', 'Stem bend', 'Head axle', 'Daisy stem')
for g in ['Roses', 'Aster', 'Poppies', 'Lavender', 'Snapdragons', 'Daisies', 'Foliage', 'Ground cover']:
    idx = [i for i, p in enumerate(P) if p['group'] == g]
    X = np.array([P[i]['p'] for i in idx])
    axles = [i for i in idx if P[i]['role'].startswith('Head axle')]
    cl = collections.defaultdict(list)
    if g == 'Snapdragons': axles = axles[:1]
    if len(axles) > 1:                                     # one unit per head axle: each part joins the nearest axle line
        for i in idx:
            pw = np.array(P[i]['p']); best = None
            for a in axles:
                o = np.array(P[a]['p']); t = np.array(P[a]['R'])[:, 0]; s_ = np.clip((pw - o).dot(t), -20, 140)
                d = np.linalg.norm(pw - (o + t * s_))
                if best is None or d < best[0]: best = (d, a)
            cl[best[1]].append(i)
    elif len(axles) == 1 and g == 'Snapdragons':
        cl[axles[0]] = list(idx)
    else:
        lab = fcluster(linkage(X, 'single'), 18, 'distance') if len(idx) > 1 else [1]
        for i, l in zip(idx, lab): cl[l].append(i)
    k = 0
    for l, members in sorted(cl.items(), key=lambda kv: -len(kv[1])):
        if len(members) < 4: continue
        ax = [i for i in members if P[i]['role'].startswith('Head axle')]
        if ax:
            Ra = np.array(P[ax[0]]['R']); t = Ra[:, 0]; origin = np.array(P[ax[0]]['p'])
        else:                                              # no head axle (daisies sit on 32L axles): use the cluster's main axis
            Y = np.array([P[i]['p'] for i in members]); origin = Y[np.argmin(Y[:, 2])]; t = Y.mean(0) - origin
            if np.linalg.norm(t) < 1e-6: t = np.array([0, 0, 1.0])
        R = frame_from_axis(t)
        parts = [q for q in to_local(members, origin, R) if not q['role'].startswith(SKIP_ROLES)]
        k += 1; units[f'{g.lower()}_{k}'] = {'kind': 'head', 'group': g, 'parts': parts}
# cherry branches: canopy parts nearest each printed branch, in that branch's frame, plus a LEGO core
can = [i for i, p in enumerate(P) if p['group'] == 'Canopy']
Ws = [np.array(am['world']) for am in A['arms']]
def local_of(W, pw): return W[:, :3].T @ (pw - W[:, 3])
assign = collections.defaultdict(list)
for i in can:
    pw = np.array(P[i]['p']); best = None
    for j, (W, am) in enumerate(zip(Ws, A['arms'])):
        q = local_of(W, pw); L = am['L']; x = min(max(q[0], 0), L)
        cy = am['rise'] * (0.9 * x / L - 0.55 * (x / L) ** 2 + 0.65 * (x / L) ** 3)
        d = math.hypot(q[0] - x, q[1] - cy)
        if best is None or d < best[0]: best = (d, j)
    if best[0] < 40: assign[best[1]].append(i)              # twigs further out belonged to the trunk top
for j, am in enumerate(A['arms']):
    W = Ws[j]; R = W[:, :3]; origin = W[:, 3]
    L, rise = am['L'], am['rise']
    core = []
    n = int(L // 16)
    for k in range(n):                                     # brown 2L axle connectors end to end along the centre line
        x0 = 8 + 16 * k; t = x0 / L
        y = rise * (0.9 * t - 0.55 * t ** 2 + 0.65 * t ** 3); dy = rise * (0.9 - 1.1 * t + 1.95 * t * t) / L
        a = math.atan2(dy, 1.0); c, s = math.cos(a), math.sin(a)
        # LDraw 6538 axis is local Y; map it onto the branch direction (cos a, sin a, 0)
        Rl = np.column_stack([[0, 0, 1.0], [s, -c, 0], [c, s, 0]])          # LDraw 6538 axis (local Z) along the branch
        core.append({'part': '6538b', 'colour': 'Reddish Brown', 'R': Rl.round(6).tolist(), 'p': [round(x0, 3), round(y, 3), 4.5], 'role': 'Branch core (LEGO)'})
    units[f'branch_{j + 1}'] = {'kind': 'branch', 'L': L, 'rise': rise, 'parts': core + to_local(assign[j], origin, R)}
json.dump(units, open(os.path.join(ROOT, 'concepts', 'work', 'library.json'), 'w'))
print({k: len(v['parts']) for k, v in units.items()})
