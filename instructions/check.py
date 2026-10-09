"""Physical checks for the rebuilt models: do parts overlap, does every part touch the build, and can every
step's new parts slide in along their connection without passing through what is already built?

usage: python instructions/check.py 10280|40725 [model ...]     (prints a report)
       from check import annotate; annotate(models)              (adds insertion directions to each step)

Each part becomes a voxel solid with a signed distance field (see Geo). Penetration is measured both ways: how deep
surface samples of one part lie inside the other. LEGO connections are line-to-line in LDraw, so a correct joint has ~0 depth; anything past
PEN_FINAL LDU is a real overlap. While sliding a part in, PEN_PATH allows for clips and hinges that flex.

Insertion: for each new part (or each placed sub-build, which moves as one), the candidate directions are the axes
of its connection features that touch the build (studs, anti-studs, axles, pins, holes, bars), then its own axes,
then the world axes. The first direction whose whole path is clear is used; the viewer slides the part in along it.
"""
import hashlib, json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'pipeline'))
from scipy import ndimage                                                         # noqa: E402
import pack, conn                                                                 # noqa: E402

PEN_FINAL, PEN_PATH, TOUCH = 0.9, 1.6, 0.6
PATH = [0.5, 1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12, 15, 18, 22, 26, 30, 36, 44, 52, 60]
CACHE_FILE = os.path.join(HERE, '.checkcache.json')

# ----------------------------------------------------------------------------------------------- part geometry
RES, PAD = 0.4, 4.0

class Geo:
    """A part as a voxel solid: its surface rasterised at RES LDU, enclosed space filled (so LDraw's internal and
    doubled faces don't matter), and a signed distance field (negative inside, in LDU)."""
    def __init__(self, pid):
        T = pack.geo(pid + '.dat')[0].astype(np.float64); V = T.reshape(-1, 3)
        self.lo, self.hi = V.min(0), V.max(0)
        o = self.lo - PAD; n = np.ceil((self.hi + PAD - o) / RES).astype(int) + 1
        surf = np.zeros(n, bool)
        a = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
        e = np.maximum(np.linalg.norm(T[:, 1] - T[:, 0], axis=1), np.maximum(np.linalg.norm(T[:, 2] - T[:, 1], axis=1), np.linalg.norm(T[:, 0] - T[:, 2], axis=1)))
        k = np.clip(np.ceil(e / (RES * 0.45)).astype(int), 1, 400)          # barycentric grid density per triangle
        for kk in np.unique(k):
            sel = T[k == kk]
            i, j = np.meshgrid(np.arange(kk + 1), np.arange(kk + 1)); m = (i + j) <= kk
            u, v = (i[m] / kk), (j[m] / kk)
            P = sel[:, 0, None] + (sel[:, 1] - sel[:, 0])[:, None] * u[None, :, None] + (sel[:, 2] - sel[:, 0])[:, None] * v[None, :, None]
            q = np.floor((P.reshape(-1, 3) - o) / RES + 0.5).astype(int)
            surf[q[:, 0], q[:, 1], q[:, 2]] = True
        solid = ndimage.binary_fill_holes(surf)
        sd = ndimage.distance_transform_edt(~solid) - ndimage.distance_transform_edt(solid)
        self.sd = (sd * RES).astype(np.float32); self.o = o; self.n = n
        # surface samples for testing against other parts: area weighted, plus vertices, capped
        rng = np.random.default_rng(int(hashlib.md5(pid.encode()).hexdigest()[:8], 16))
        cnt = int(min(3000, max(400, a.sum() / 5)))
        idx = rng.choice(len(T), cnt, p=a / a.sum())
        u, v = rng.random(cnt), rng.random(cnt); f = u + v > 1; u[f], v[f] = 1 - u[f], 1 - v[f]
        S = T[idx, 0] + (T[idx, 1] - T[idx, 0]) * u[:, None] + (T[idx, 2] - T[idx, 0]) * v[:, None]
        Vu = np.unique(np.round(V, 2), axis=0)
        if len(Vu) > 1500: Vu = Vu[rng.choice(len(Vu), 1500, replace=False)]
        self.pts = np.vstack([S, Vu])
        self.feats = [(kd, np.asarray(p, float), np.asarray(ax, float)) for kd, p, ax, ln, sub in conn.summary(pid)]
        # joint lines: axles, pins, bars and studs run through their holes, so volume shared near them is contact
        self.joints = [(p, ax, ln) for (kd, p, ax, ln, sub) in conn.summary(pid) if kd in ('axle', 'pin', 'pinhole', 'bar', 'stud', 'antistud')]

    def field(self, L):
        """Signed distance (LDU) at local points; +PAD+1 outside the grid."""
        q = np.floor((L - self.o) / RES + 0.5).astype(int)
        ok = np.all((q >= 0) & (q < self.n), axis=1); out = np.full(len(L), PAD + 1.0)
        out[ok] = self.sd[q[ok, 0], q[ok, 1], q[ok, 2]]
        return out

_G = {}
def G(pid):
    if pid not in _G: _G[pid] = Geo(pid)
    return _G[pid]

def local(P, part): return (P - part['t']) @ np.linalg.inv(part['M']).T

def inside_depth(P, part):
    """Depth (LDU) of world points P inside a placed part; 0 where outside."""
    return np.maximum(0.0, -G(part['pid']).field(local(P, part)))

def world_pts(part, off=np.zeros(3)):
    g = G(part['pid']); return g.pts @ part['M'].T + part['t'] + off

def world_box(part, off=np.zeros(3)):
    g = G(part['pid']); c = np.array([[x, y, z] for x in (g.lo[0], g.hi[0]) for y in (g.lo[1], g.hi[1]) for z in (g.lo[2], g.hi[2])])
    W = c @ part['M'].T + part['t'] + off; return W.min(0), W.max(0)

def boxes_meet(a, b, pad=1.0): return np.all(a[0] - pad < b[1]) and np.all(b[0] - pad < a[1])

JOINT_R = 4.5

def in_joint(P, part):
    """Which world points lie in a joint of `part`: within JOINT_R of its axle/pin/bar line, near its length."""
    m = np.zeros(len(P), bool)
    for c, ax, ln in G(part['pid']).joints:
        w = part['M'] @ c + part['t']; a = part['M'] @ ax; a = a / (np.linalg.norm(a) or 1)
        d = P - w; t = d @ a; perp = np.linalg.norm(d - np.outer(t, a), axis=1)
        lo, hi = (-6.0, ln + 6.0) if ln > 1.5 else (-JOINT_R, JOINT_R)     # the joint runs from its start point along ax
        m |= (perp < JOINT_R) & (t > lo) & (t < hi)
    return m

def penetration(A, B, offA=np.zeros(3)):
    """Max depth and number of points deeper than PEN_FINAL that are not in a joint, either way round, with A moved by offA."""
    PA = world_pts(A, offA); PB = world_pts(B)
    da = inside_depth(PA, B); db = inside_depth(PB, dict(A, t=A['t'] + offA))
    da = np.where(in_joint(PA, B), 0.0, da); db = np.where(in_joint(PB, dict(A, t=A['t'] + offA)), 0.0, db)
    return max(da.max(initial=0), db.max(initial=0)), int((da > PEN_FINAL).sum() + (db > PEN_FINAL).sum())

def gap(A, B):
    """Closest distance between the surfaces of two placed parts (sampled)."""
    return float(G(B['pid']).field(local(world_pts(A), B)).min())

# ----------------------------------------------------------------------------------------------- static checks
def static_report(m, label=None):
    """Overlapping pairs and loose parts in a finished model."""
    P = m.parts; boxes = [world_box(p) for p in P]; out = []
    touch = {i: set() for i in range(len(P))}
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            if not boxes_meet(boxes[i], boxes[j]): continue
            dep, n = penetration(P[i], P[j])
            if dep > PEN_FINAL and n >= 3: out.append(('overlap', i, j, round(dep, 1), n))
            if gap(P[i], P[j]) < TOUCH or gap(P[j], P[i]) < TOUCH or dep > 0: touch[i].add(j); touch[j].add(i)
    for i in range(len(P)):
        if not touch[i] and len(P) > 1: out.append(('loose', i))
    # connected pieces
    seen, comps = set(), []
    for i in range(len(P)):
        if i in seen: continue
        st, c = [i], []
        while st:
            k = st.pop()
            if k in seen: continue
            seen.add(k); c.append(k); st += list(touch[k])
        comps.append(c)
    if len(comps) > 1: out.append(('pieces', [sorted(c)[:6] + (['...'] if len(c) > 6 else []) for c in comps]))
    return out, touch

# ----------------------------------------------------------------------------------------------- insertion paths
def candidates(unit, statics, parts):
    """Directions to try for a unit (list of part dicts): engaged feature axes first, then part axes, world axes."""
    eng = []
    for p in unit:
        g = G(p['pid'])
        for k, fp, fa in g.feats:
            if k not in ('stud', 'antistud', 'axle', 'pin', 'pinhole', 'bar'): continue
            w = p['M'] @ fp + p['t']; a = p['M'] @ fa
            for s in statics:
                q = parts[s]
                if G(q['pid']).field(local(w[None], q))[0] < 3.5:
                    eng.append(a / np.linalg.norm(a)); break
    dirs = []
    def add(d, tag):
        d = np.asarray(d, float); d = d / np.linalg.norm(d)
        for e, _ in dirs:
            if e @ d > 0.995: return
        dirs.append((d, tag))
    # most common engaged axis first
    groups = []
    for a in eng:
        for g_ in groups:
            if abs(g_[0] @ a) > 0.98: g_[1] += 1; break
        else: groups.append([a, 1])
    groups.sort(key=lambda g_: -g_[1])
    centre = np.mean(np.vstack([world_pts(p) for p in unit]), axis=0)
    sc = np.mean([parts[s]['t'] for s in statics], axis=0) if statics else centre
    for a, n in groups:
        sgn = 1 if a @ (centre - sc) >= 0 else -1
        add(a * sgn, 'feature'); add(-a * sgn, 'feature')
    for p in unit:
        for c in (1, 0, 2):
            ax = p['M'][:, c]; add(-ax, 'part'); add(ax, 'part')
    for d in ((0, -1, 0), (0, 1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)): add(d, 'world')
    return dirs, len(groups) > 0

def path_clear(unit, statics, parts, d, sboxes):
    worst = 0.0
    for s in PATH:
        off = d * s; hit = False
        ub = [world_box(p, off) for p in unit]
        for si in statics:
            q = parts[si]
            for p, b in zip(unit, ub):
                if not boxes_meet(b, sboxes[si], 0.5): continue
                dep, n = penetration(p, q, off)
                if dep > PEN_PATH and n >= 2: return False, s, si
        # far enough: nothing near any more
        if not any(boxes_meet(b, sboxes[si], 2) for b in ub for si in statics): return True, s, None
    return True, PATH[-1], None

def unit_key(unit, statics, parts):
    h = hashlib.md5()
    for p in unit + [None] + [parts[s] for s in statics]:
        if p is None: h.update(b'|'); continue
        h.update(p['pid'].encode()); h.update(np.round(p['M'], 3).tobytes()); h.update(np.round(p['t'], 2).tobytes())
    return h.hexdigest()

def insertion(m, cache, log):
    """Choose a clear insertion direction for every unit of every step of model m; returns per-step lists."""
    P = m.parts; sboxes = [world_box(p) for p in P]; done = []; res = []
    for si, st in enumerate(m.steps):
        groups = [list(g) for g in st.get('groups', [])]; ingroup = {i for g in groups for i in g}
        units = groups + [[i] for i in st['new'] if i not in ingroup]
        units.sort(key=lambda u: min(u))
        out = []
        for u in units:
            parts_u = [P[i] for i in u]
            # statics: earlier steps and units already in; only those near the unit
            ubox = (np.min([sboxes[i][0] for i in u], 0), np.max([sboxes[i][1] for i in u], 0))
            reach = (ubox[0] - 70, ubox[1] + 70)
            statics = [i for i in done if boxes_meet(sboxes[i], reach)]
            if not statics: out.append({'p': u, 'd': [0, -1, 0], 'k': 'first'}); done += u; continue
            key = unit_key(parts_u, statics, P)
            if key in cache: r = cache[key]
            else:
                dirs, has_feat = candidates(parts_u, statics, P); r = None; why = []
                for d, tag in dirs:
                    ok, s, hit = path_clear(parts_u, statics, P, d, sboxes)
                    if ok: r = {'d': [round(float(v), 4) for v in d], 'k': tag, 'clear': s}; break
                    why.append((tag, [round(float(v), 2) for v in d], s, P[hit]['pid'] if hit is not None else None))
                if r is None: r = {'d': [0, -1, 0], 'k': 'blocked', 'why': why[:4]}
                cache[key] = r
            out.append(dict(r, p=u))
            if r['k'] in ('blocked', 'world', 'part'):
                log.append((m.name, si + 1, [P[i]['pid'] for i in u][:4], r['k'], r.get('why', r['d'])))
            done += u
        res.append(out)
    return res

def load_cache():
    try: return json.load(open(CACHE_FILE))
    except Exception: return {}

def annotate(models, skip=('bouquet', 'final'), verbose=True):
    """Add s['ins'] = [{p: [part idx], d: [x,y,z], k: how found}] to every step of every model."""
    cache = load_cache(); log = []
    for m in models:
        if m.name in skip: continue
        for st, ins in zip(m.steps, insertion(m, cache, log)): st['ins'] = [{'p': i['p'], 'd': i['d'], 'k': i['k']} for i in ins]
    json.dump(cache, open(CACHE_FILE, 'w'))
    if verbose:
        for row in log: print('  path:', *row)
    return log

if __name__ == '__main__':
    which = sys.argv[1]; only = set(sys.argv[2:])
    mod = __import__('s' + which)
    models, subs = mod.build()
    for m in models + subs:
        if only and m.name not in only: continue
        if m.name in ('bouquet', 'final') and not only: continue
        rep, _ = static_report(m)
        for r in rep:
            if r[0] == 'overlap': print(f'{m.name}: overlap {m.parts[r[1]]["pid"]}#{r[1]} x {m.parts[r[2]]["pid"]}#{r[2]} depth {r[3]} ({r[4]} pts)')
            elif r[0] == 'loose': print(f'{m.name}: loose {m.parts[r[1]]["pid"]}#{r[1]}')
            else: print(f'{m.name}: {len(r[1])} separate pieces {r[1]}')
        sys.stdout.flush()
    annotate([m for m in models + subs if not only or m.name in only])
