"""Pack composed concepts for concepts/render.html (three.js, Y-up).  -> concepts/work/<name>.js"""
import json, os, sys, base64
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import ldraw_hi, ldraw                                     # noqa: E402
W = os.path.join(ROOT, 'concepts', 'work')
cols = ldraw.colours(ldraw.fetch('LDConfig.ldr'))
LDCOL = {'Black': 0, 'Bright Pink': 29, 'Dark Bluish Gray': 72, 'Dark Green': 288, 'Dark Pink': 5, 'Dark Purple': 85, 'Dark Turquoise': 3, 'Green': 2,
         'Lavender': 31, 'Light Bluish Gray': 71, 'Light Nougat': 78, 'Lime': 27, 'Magenta': 26, 'Medium Lavender': 30, 'Orange': 25, 'Pearl Gold': 297,
         'Red': 4, 'Reddish Brown': 70, 'Sand Green': 378, 'Tan': 19, 'White': 15, 'Yellow': 14, 'Yellowish Green': 326, 'Dark Red': 320}
T = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)
def hexcol(code): return '#%06X' % (code & 0xFFFFFF) if code >= 0x2000000 else (cols[code][1] if code in cols else '#888888')
def pack(arr):
    if len(arr) == 0: return None
    flat = np.asarray(arr, float).reshape(-1, 3); m = float(np.abs(flat).max()) or 1.0
    return {'s': m, 'b': base64.b64encode(np.round(flat / m * 32767).astype(np.int16).tobytes()).decode()}
geo = {}
for f in sorted(os.listdir(W)):
    if not f.endswith('.json') or f == 'library.json' or f.endswith('summary.json'): continue
    S = json.load(open(os.path.join(W, f)))
    ids = sorted(set(p['part'] for p in S['lego'])); ldraw.prefetch([i + '.dat' for i in ids])
    G = {}
    for pid in ids:
        if pid not in geo:
            V, C = ldraw.tris(pid + '.dat')
            geo[pid] = {'inh': pack(V[(C == 16) | (C == 24)]), 'fixed': [{'c': hexcol(int(c)), 'g': pack(V[C == c])} for c in set(C.tolist()) if c not in (16, 24) and (C == c).any()]}
        G[pid] = geo[pid]
    inst = []
    for p in S['lego']:
        R = T @ np.array(p['R']) * 0.4; t = T @ np.array(p['p'])
        inst.append([p['part'], hexcol(LDCOL[p['colour']])] + [round(float(x), 5) for x in R.ravel()] + [round(float(x), 2) for x in t])
    pr = []
    for q in S['printed']:
        v = (T @ np.array(q['v']).T).T; f_ = np.array(q['f'])
        pr.append({'kind': q['kind'], 'label': q['label'], **pack(v[f_])})
    open(os.path.join(W, S['name'] + '.js'), 'w').write('window.CONCEPT=' + json.dumps({'title': S['title'], 'geoms': G, 'inst': inst, 'printed': pr}) + ';')
    print(S['name'], len(inst), 'pieces', len(pr), 'printed meshes')
