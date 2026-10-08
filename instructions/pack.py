"""Pack LDraw part geometry (faces, edge lines, conditional lines) and built models for the step viewer.

pack(models, out_js): models is a list of Model objects (main build first, then sub-builds). The output defines
window.SET = {geoms: {pid: {...}}, colours: {code: [hex, edgeHex]}, models: {name: {parts, steps}}}.
Positions are quantised to int16 per geometry block and stored base64.
"""
import base64, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'pipeline'))
import ldraw, ldraw_hi                                            # noqa: E402,F401  (hi-res primitives)

_memo = {}
def geo(name):
    """(tris[n,3,3], tri colour[n], edges[m,2,3], cond[k,4,3]) of a part file, colour 16 = inherit, 24 = edge colour."""
    rel = ldraw.locate(name)
    if rel is None: raise FileNotFoundError(name)
    if rel in _memo: return _memo[rel]
    T, TC, E, CL = [], [], [], []
    inv = False
    for line in open(ldraw.fetch(rel), encoding='utf-8', errors='replace'):
        t = line.split()
        if not t: continue
        if t[0] == '3' and len(t) >= 11:
            TC.append(int(t[1])); T.append(np.array(t[2:11], float).reshape(3, 3))
        elif t[0] == '4' and len(t) >= 14:
            q = np.array(t[2:14], float).reshape(4, 3); c = int(t[1]); T += [q[[0, 1, 2]], q[[0, 2, 3]]]; TC += [c, c]
        elif t[0] == '2' and len(t) >= 8:
            E.append(np.array(t[2:8], float).reshape(2, 3))
        elif t[0] == '5' and len(t) >= 14:
            CL.append(np.array(t[2:14], float).reshape(4, 3))
        elif t[0] == '1' and len(t) >= 15:
            c = int(t[1]); x, y, z, a, b, cc, d, e, f, g, h, i = map(float, t[2:14])
            M = np.array([[a, b, cc], [d, e, f], [g, h, i]]); o = np.array([x, y, z])
            try: st, sc, se, scl = geo(' '.join(t[14:]))
            except FileNotFoundError: continue
            if len(st):
                tt = st @ M.T + o
                if np.linalg.det(M) < 0: tt = tt[:, ::-1]
                T.extend(list(tt)); TC.extend([c if k == 16 else k for k in sc])
            if len(se): E.extend(list(se @ M.T + o))
            if len(scl): CL.extend(list(scl @ M.T + o))
    out = (np.array(T, np.float32).reshape(-1, 3, 3), np.array(TC, np.int32), np.array(E, np.float32).reshape(-1, 2, 3),
           np.array(CL, np.float32).reshape(-1, 4, 3))
    _memo[rel] = out; return out

def q16(arr):
    if arr is None or len(arr) == 0: return None
    f = np.asarray(arr, float).reshape(-1, 3); m = float(np.abs(f).max()) or 1.0
    return {'s': round(m, 4), 'b': base64.b64encode(np.round(f / m * 32767).astype(np.int16).tobytes()).decode()}

def colours():
    import re
    out = {}
    for line in open(ldraw.fetch('LDConfig.ldr'), encoding='utf-8', errors='replace'):
        m = re.search(r'!COLOUR\s+(\S+)\s+CODE\s+(\d+)\s+VALUE\s+#([0-9A-Fa-f]{6})\s+EDGE\s+#([0-9A-Fa-f]{6})', line)
        if m: out[int(m.group(2))] = ['#' + m.group(3), '#' + m.group(4), m.group(1)]
    return out

def pack(models, out_js, extra=None):
    pids = sorted({p['pid'] for m in models for p in m.parts})
    ldraw.prefetch([p + '.dat' for p in pids])
    G = {}
    for pid in pids:
        T, C, E, CL = geo(pid + '.dat')
        inh = (C == 16) | (C == 24)
        G[pid] = {'tri': q16(T[inh]), 'fixed': [{'c': int(c), 'tri': q16(T[C == c])} for c in sorted(set(C[~inh].tolist()))],
                  'edge': q16(E), 'cond': q16(CL), 'bb': [np.round(T.reshape(-1, 3).min(0), 1).tolist(), np.round(T.reshape(-1, 3).max(0), 1).tolist()]}
    cols = colours(); used = {p['col'] for m in models for p in m.parts} | {c for g in G.values() for c in [f['c'] for f in g['fixed']]}
    M = {}
    for m in models:
        M[m.name] = {'title': m.title,
                     'parts': [[p['pid'], p['col']] + [round(float(v), 5) for v in p['M'].ravel()] + [round(float(v), 3) for v in p['t']] for p in m.parts],
                     'steps': m.steps}
    data = {'geoms': G, 'colours': {c: cols.get(c, ['#888888', '#333333', 'Unknown']) for c in sorted(used)}, 'models': M}
    if extra: data.update(extra)
    os.makedirs(os.path.dirname(out_js), exist_ok=True)
    open(out_js, 'w').write('window.SET=' + json.dumps(data, separators=(',', ':')) + ';')
    print(out_js, round(os.path.getsize(out_js) / 1e6, 2), 'MB,', len(pids), 'parts,', sum(len(m.parts) for m in models[:1]), 'pieces in main')

ALIAS = {'6538c': '6538b', '4589b': '4589', '98088pb05': '98088'}
def part_names():
    """Part names from the combined checklist (BrickLink names), keyed by the LDraw id the models use."""
    import openpyxl
    wb = openpyxl.load_workbook(os.path.join(os.path.dirname(HERE), 'lego', 'parts_inventory.xlsx'), read_only=True)
    out = {}
    for r in wb['Parts checklist'].iter_rows(min_row=12, values_only=True):
        if r[0] and r[2]: out[ALIAS.get(str(r[0]), str(r[0]))] = r[2]
    out.update({'23443': 'Bar Holder with Handle', '48729b': 'Bar 1L with Clip (Mechanical Claw)', '68211': 'Plant Stem, 3 Short Stems',
                '24855': 'Plant Stem, Bar Holder, Bar and 3 Stems', '89678': 'Technic Pin 1/2', '15470': 'Plate, Round 1x1 with Swirl'})
    return out
