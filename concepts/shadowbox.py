"""Shadow-box concepts: one piece, everything inside a box of LEGO 32L axles, fabric clipped on, and a long vine
with the flowers along it (no stems meeting in a centre).

usage: python concepts/shadowbox.py   -> concepts/work/sb_<variant>.json and concepts/work/sb_summary.json
World frame: millimetres, Z up, shelf at z = 0, viewer at -Y.

The box
  8 sand-green 32L axles: a front and a back square (verticals at x = +-H, horizontals at z = ZC +- H).
  12 dark green 3L connectors: three per corner, front to back.
  8 printed corner nodes: each takes one axle along X, one along Z and the connector chain along Y; the three
     holes stop short of each other, so every node is the same part.
  2 more 32L axles: rails just in front of the back cloth; they carry fabric pieces and hold the vine.
The vine
  dark green 3L connectors joined end to end (hidden 2L axles), with a black TPU knuckle at every bend; each
  knuckle has a side socket that takes a flower head's axle directly.
"""
import collections, json, math, os
import numpy as np, trimesh
from scipy.spatial import cKDTree
from kit import *

H, ZC = 134.0, 146.0                      # axle centre lines; the box sits on its bottom corner nodes at z = 0
YF, YB, NODE = -60.0, 60.0, 24.0          # front and back frame planes (four 3L connectors apart), corner node size
DEPTH_Y = (-36, -12, 12, 36)
RAIL_Y = 52.0
LO = np.array([-130.0, -60.0, ZC - H + 3]); HI = np.array([130.0, 56.0, ZC + H - 3])     # where any part of a flower may go
import sys; sys.path.insert(0, os.path.join(ROOT, 'pipeline')); import ldraw                         # noqa: E402
_BB = {}
def corners(pid):
    """Bounding-box corners of a part in mm, in its own frame (LDraw units x 0.4)."""
    if pid not in _BB:
        V = ldraw.tris(pid + '.dat')[0].reshape(-1, 3) * 0.4; a, b = V.min(0), V.max(0)
        _BB[pid] = np.array([[x, y, z] for x in (a[0], b[0]) for y in (a[1], b[1]) for z in (a[2], b[2])])
    return _BB[pid]
FWD = np.array([0, -1.0, 0])
STOCK = collections.Counter()
for q in json.load(open(os.path.join(ROOT, 'lego', 'placements.json'))): STOCK[(q['part'], q['colour'])] += 1

def lib_pts(name, R, origin, skip=()):
    P = np.array([q['p'] for q in LIB[name]['parts'] if not any(q['role'].startswith(s) for s in skip)])
    return np.asarray(origin) + P @ np.asarray(R).T

def lib_box(name, R, origin, skip=()):
    """Every bounding-box corner of every part of a unit, in world mm."""
    out = []
    for q in LIB[name]['parts']:
        if any(q['role'].startswith(s) for s in skip): continue
        Rw = np.asarray(R) @ np.array(q['R']); out.append(np.asarray(origin) + (np.asarray(R) @ np.array(q['p'])) + corners(q['part']) @ Rw.T)
    return np.vstack(out)

def oob(P): return int(((P < LO) | (P > HI)).any(axis=1).sum())

def seg_cyl(a, b, r, sections=16):
    a, b = np.asarray(a, float), np.asarray(b, float); return cyl(r, np.linalg.norm(b - a), (a + b) / 2, b - a, sections)

def ball(r, c):
    m = trimesh.creation.icosphere(1, r); m.apply_translation(c); return m

def leaf(c, d, n, length=34, width=15):
    """A felt leaf: a thin ellipse in the plane spanned by d (its length) and n x d."""
    m = trimesh.creation.cylinder(1.0, 0.8, sections=24); m.apply_scale([width / 2, length / 2, 1])
    d = unit(d); n = unit(n); x = unit(np.cross(d, n)); R = np.column_stack([x, d, np.cross(x, d)])
    Tm = np.eye(4); Tm[:3, :3] = R; Tm[:3, 3] = np.asarray(c) + d * length / 2; m.apply_transform(Tm); return m

class Box(Scene):
    def __init__(self, name, title):
        super().__init__(name, title); self.flower_pts = []; self.log = []; self.knots = []

    # ---------------------------------------------------------------- frame
    def frame_box(self, back, rails):
        for y in (YF, YB):
            for sx in (-1, 1): self.axle32((sx * H, y, ZC), (0, 0, 1))
            for sz in (-1, 1): self.axle32((0, y, ZC + sz * H), (1, 0, 0))
        for sx in (-1, 1):
            for sz in (-1, 1):
                for y in DEPTH_Y: self.part('26287', 'Dark Green', frame((0, 1, 0)), (sx * H, y, ZC + sz * H), 'Structure: depth connector')
                for y in (YF, YB):
                    self.mesh(box([NODE] * 3, (sx * H, y, ZC + sz * H)), 'pla', 'Corner node')
        for z in rails:
            self.axle32((0, RAIL_Y, z), (1, 0, 0))
            for sx in (-1, 1): self.mesh(box([12, 16, 12], (sx * (H - 3), (RAIL_Y + YB) / 2, z)), 'pla', 'Rail clip (snaps on the back upright)')
        self.mesh(box([34, 8, 22], (0, YB + 7, ZC + H - 4)), 'pla', 'Hanger clip with keyhole (snaps on the top back axle)')
        self.mesh(box([2 * H + 14, 1.0, 2 * H + 14], (0, YB + 4, ZC)), 'fabric:' + back, 'Back cloth (wraps the back frame)')
        for sz in (-1, 1):
            for x in (-80, 0, 80):
                if sz > 0 and x == 0: continue
                self.mesh(box([14, 6, 9], (x, YB + 1, ZC + sz * H)), 'clear', 'Fabric clip (clear TPU)')
        for sx in (-1, 1):
            for z in (ZC - 70, ZC + 70): self.mesh(box([9, 6, 14], (sx * H, YB + 1, z)), 'clear', 'Fabric clip (clear TPU)')

    def fabric_on_rail(self, m, colour, label):
        self.mesh(m, 'fabric:' + colour, label)

    # ---------------------------------------------------------------- vine
    def vine(self, ctrl, step=37):
        """Catmull-Rom through ctrl (x, y, z), cut into straight runs of 3L connectors with a TPU knuckle at each bend."""
        C = np.array(ctrl, float); C = np.vstack([C[0] * 2 - C[1], C, C[-1] * 2 - C[-2]])
        pts = []
        for i in range(1, len(C) - 2):
            p0, p1, p2, p3 = C[i - 1:i + 3]
            for t in np.linspace(0, 1, 60, endpoint=False):
                pts.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
        pts.append(C[-2]); pts = np.array(pts)
        s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
        n = max(2, int(round(s[-1] / step)))
        V = np.array([np.interp(np.linspace(0, s[-1], n + 1), s, pts[:, k]) for k in range(3)]).T
        bends = []
        for i in range(len(V) - 1):
            a, b = V[i], V[i + 1]; d = b - a; L = np.linalg.norm(d); d = d / L; R = frame(d)
            k = max(1, int(round((L - 10) / 24)))
            for j in range(k): self.part('26287', 'Dark Green', R, a + d * (5 + (L - 10) * (j + 0.5) / k), 'Vine (3L connector)')
        for i, v in enumerate(V):
            self.mesh(ball(6.5, v), 'tpu', 'Vine knuckle (black TPU)')
            if 0 < i < len(V) - 1:
                bends.append(math.degrees(math.acos(np.clip(unit(V[i] - V[i - 1]).dot(unit(V[i + 1] - V[i])), -1, 1))))
        for v in (V[0], V[-1]): self.mesh(box([12, 12, 12], v), 'pla', 'Vine end clip')
        T = np.array([unit(V[min(i + 1, len(V) - 1)] - V[max(i - 1, 0)]) for i in range(len(V))])
        self.knots.append((V, T)); self.vine_pts = np.vstack([q['p'] for q in self.lego if q['role'].startswith('Vine')])
        self.bends = getattr(self, 'bends', []) + bends
        return V, T

    def standoffs(self, V, rails, per_rail=2):
        for zr in rails:
            idx = sorted(range(1, len(V) - 1), key=lambda i: abs(V[i][2] - zr))
            chosen = []
            for i in idx:
                if abs(V[i][2] - zr) > 45: break
                if all(abs(V[i][0] - V[j][0]) > 70 for j in chosen): chosen.append(i)
                if len(chosen) == per_rail: break
            for i in chosen:
                a = V[i]; b = np.array([a[0], RAIL_Y, zr])
                self.mesh(seg_cyl(a + [0, 5, 0], b, 2.6), 'pla', 'Vine standoff (clips on the rail)')

    # ---------------------------------------------------------------- flowers
    def _score(self, P, d, want, tree, near, avoid=9.0, Bx=None):
        o = oob(Bx if Bx is not None else P); col = 0
        if tree is not None:
            dd, _ = tree.query(P, distance_upper_bound=avoid); col = int(np.isfinite(dd).sum())
        vd, _ = self.vtree.query(P, distance_upper_bound=avoid)
        col += int((np.isfinite(vd) & (np.linalg.norm(P - near, axis=1) > 22)).sum())
        return 1000 * o + 5 * col + 10 * (1 - d.dot(want)), o, col

    def head(self, name, knot, want=None, side=1, tilt=65, skip=(), loose=False):
        V, T = self.knots[-1]; knot = min(knot, len(V) - 2); v, t = V[knot], T[knot]
        nrm = unit(np.cross(t, [0, 1.0, 0])) * side
        if want is None: want = unit(nrm * math.cos(math.radians(tilt)) + FWD * math.sin(math.radians(tilt)))
        want = unit(want)
        tree = cKDTree(np.vstack(self.flower_pts)) if self.flower_pts else None
        self.vtree = cKDTree(self.vine_pts)
        best = None
        for a in range(0, 360, 15):
            for tl in (0, 15, 30, 45, 60, 75, 88):
                d = np.array([math.cos(math.radians(a)) * math.cos(math.radians(tl)), -math.sin(math.radians(tl)), math.sin(math.radians(a)) * math.cos(math.radians(tl))])
                if d.dot(want) < (-1.1 if loose else 0.2): continue
                for spin in np.linspace(0, 2 * math.pi, 6, endpoint=False):
                    R = frame(d, spin); o = v + d * 7; P = lib_pts(name, R, o, skip)
                    sc = self._score(P, d, want, tree, v, Bx=lib_box(name, R, o, skip))
                    if best is None or sc[0] < best[0][0]: best = (sc, R, o, P)
        if best[0][1] and not loose: return self.head(name, knot, want, side, tilt, skip, loose=True)
        (sc, o_, col), R, o, P = best
        self.unit(name, R, o, skip); self.flower_pts.append(P)
        self.log.append(f'{name:15s} knot {knot:2d} out {o_} close {col}')
        self.mesh(seg_cyl(v, o, 2.2), 'tpu', 'Knuckle side socket')

    def bough(self, name, root, angles, flip=False):
        """A cherry branch on its LEGO 2L-connector core, canopy toward the viewer; try directions in the XZ plane."""
        tree = cKDTree(np.vstack(self.flower_pts)) if self.flower_pts else None
        self.vtree = cKDTree(self.vine_pts) if hasattr(self, 'vine_pts') else cKDTree([[1e6, 1e6, 1e6]])
        best = None; root = np.asarray(root, float)
        for a in angles:
            for tl in (0, 10, 20):
                x = np.array([math.cos(math.radians(a)) * math.cos(math.radians(tl)), -math.sin(math.radians(tl)), math.sin(math.radians(a)) * math.cos(math.radians(tl))])
                for f in (False, True):
                    y = unit(FWD - x * FWD.dot(x)); z = np.cross(x, y)
                    if f: z = -z; y = np.cross(z, x)                     # mirror the spread, keep the canopy forward
                    R = np.column_stack([x, y, z])
                    if np.linalg.det(R) < 0: continue
                    o = root - z * 4.5; P = lib_pts(name, R, o)
                    sc = self._score(P, x, x, tree, root, 6.0, Bx=lib_box(name, R, o))
                    if best is None or sc[0] < best[0][0]: best = (sc, R, o, P, a, f)
        (sc, o_, col), R, o, P, a, f = best
        self.unit(name, R, o); self.flower_pts.append(P)
        self.log.append(f'{name:15s} bough at {a} deg  out {o_} close {col}')

    def felt_leaves(self, V, T, idx, colour):
        for k, i in enumerate(idx):
            i = min(max(i, 1), len(V) - 2)
            nrm = unit(np.cross(T[i], [0, 1.0, 0])) * (1 if k % 2 else -1)
            d = unit(nrm + T[i] * 0.6 + FWD * 0.25)
            m = leaf(V[i] + d * 4, d, FWD * 0.8 + nrm * 0.2)
            if oob(m.vertices) == 0: self.mesh(m, 'fabric:' + colour, 'Felt leaf (clips on the knuckle)')

    def report(self, desc):
        use = collections.Counter((q['part'], q['colour']) for q in self.lego)
        short = {f'{p} {c}': f'{n}/{STOCK[(p, c)]}' for (p, c), n in use.items() if n > STOCK[(p, c)]}
        out_n = sum(oob(np.array(q['p']) + corners(q['part']) @ (np.array(q['R']).T)) > 0 for q in self.lego if not q['role'].startswith('Structure'))
        out = self.save(desc)
        out['check'] = {'over_stock': short, 'parts_outside_box': out_n, 'vine_connectors': sum(1 for q in self.lego if q['role'].startswith('Vine')),
                        'knuckles': sum(1 for p in self.printed if p['label'].startswith('Vine knuckle')), 'max_bend_deg': round(max(self.bends), 1) if self.bends else 0,
                        'axles_32L': use[('50450', 'Sand Green')], 'brown_2L_connectors': use[('6538b', 'Reddish Brown')]}
        print(self.name, out['printed_grams'], 'g printed,', out['lego_count'], 'LEGO;', out['check']); print('   ' + '\n   '.join(self.log))
        return out

SUM = []
SIZE = f'{(2 * H + NODE) / 10:.0f} × {(2 * H + NODE) / 10:.0f} cm, {(YB - YF + NODE) / 10:.0f} cm deep'

# ======================================================================= 1. Moon and bough
def along(S, V, plan):
    """plan: (name, fraction along the vine, side, tilt or want-vector)."""
    for name, f, side, how in plan:
        k = int(round(f * (len(V) - 2))) if f < 1 else len(V) - 2
        k = max(1, k)
        sk = ('Rose leaf',)
        if isinstance(how, (int, float)): S.head(name, k, side=side, tilt=how, skip=sk)
        else: S.head(name, k, want=np.array(how, float), skip=sk)

S = Box('sb_moon', 'Moon and bough')
S.frame_box('#2E3650', rails=(ZC - 40, ZC + 60))
S.fabric_on_rail(cyl(66, 1.0, (52, RAIL_Y - 3, ZC + 52), (0, 1, 0), 96), '#EDE3CB', 'Fabric moon (stiffened disc, clips on the upper rail)')
V, Tn = S.vine([(124, 40, 30), (104, 36, 70), (56, 34, 92), (0, 32, 80), (-50, 34, 56), (-96, 36, 74), (-108, 38, 128), (-92, 40, 172)])
S.standoffs(V, (ZC - 40,))
S.bough('branch_1', (-120, 40, 236), range(-40, 15, 5))
along(S, V, [('roses_1', .1, 1, 60), ('daisies_4', .25, -1, 70), ('poppies_1', .4, 1, 70), ('aster_1', .55, -1, 70),
             ('daisies_1', .7, 1, 70), ('lavender_1', .85, 1, 15), ('daisies_3', 1, -1, 70)])
S.felt_leaves(V, Tn, [2, 4, 7, 9], '#4B6A55')
SUM.append(S.report({'size': SIZE,
    'idea': 'A cherry bough reaches in from the top-left corner across a fabric moon; below it a vine climbs from the bottom-right corner and swings round to meet it, flowering all the way.',
    'fabric': 'Indigo back cloth; a cream moon disc clipped to the upper rail; felt leaves on the vine.'}))

# ======================================================================= 2. Climbing vine with mist bands
S = Box('sb_climb', 'Climbing vine')
rails = (ZC - 52, ZC + 48)
S.frame_box('#E4DBC8', rails=rails)
for z, col in zip(rails, ('#9DB09F', '#D9B3A9')):
    S.fabric_on_rail(box([2 * H - 8, 1.0, 44], (0, RAIL_Y - 4, z)), col, 'Fabric mist band (kasumi), clipped over the rail')
V, Tn = S.vine([(-124, 40, 30), (-60, 36, 56), (20, 34, 62), (88, 36, 90), (104, 36, 138), (44, 34, 172), (-46, 34, 180), (-100, 36, 214), (-76, 38, 256)])
S.standoffs(V, rails)
S.bough('branch_3', (120, 40, 252), range(160, 250, 5))
along(S, V, [('roses_1', .08, 1, 60), ('daisies_1', .2, -1, 70), ('poppies_1', .32, 1, 70), ('aster_1', .44, -1, 70),
             ('lavender_1', .56, 1, 15), ('daisies_2', .67, -1, 70), ('poppies_2', .78, 1, 70), ('lavender_2', .89, -1, 15), ('daisies_3', 1, 1, 70)])
S.felt_leaves(V, Tn, [2, 5, 8, 11, 14], '#55704F')
SUM.append(S.report({'size': SIZE,
    'idea': 'One long vine climbs from the bottom-left corner in an S to the top, with roses, poppies, daisies and lavender along it; a cherry bough leans in from the top-right corner.',
    'fabric': 'Linen back cloth; two mist bands (sage and blush) folded over the rails; felt leaves clip onto the knuckles.'}))

# ======================================================================= 3. Cascade
S = Box('sb_cascade', 'Cascade')
rails = (ZC + 100, ZC - 20)
S.frame_box('#E6DDCB', rails=rails)
S.fabric_on_rail(box([H - 4, 1.0, 2 * H - 40], (-H / 2, RAIL_Y - 3, ZC + 10)), '#3F4C46', 'Noren panel, left (hangs from the upper rail)')
S.fabric_on_rail(box([H - 4, 1.0, 2 * H - 40], (H / 2, RAIL_Y - 3, ZC + 10)), '#B9C3B4', 'Noren panel, right (hangs from the upper rail)')
V, Tn = S.vine([(-124, 40, 256), (-100, 36, 196), (-58, 34, 128), (0, 32, 104), (58, 34, 128), (100, 36, 196), (124, 40, 256)])
S.standoffs(V, rails)
along(S, V, [('daisies_3', .12, 1, (0.4, -1, 0.2)), ('lavender_1', .24, 1, (-0.1, -0.4, -1)), ('daisies_1', .36, 1, (-0.4, -1, -0.3)),
             ('snapdragons_1', .5, 1, (0, -0.5, -1)), ('poppies_1', .62, 1, (0.4, -1, -0.3)), ('lavender_3', .74, 1, (0.1, -0.4, -1)),
             ('daisies_2', .86, 1, (-0.4, -1, 0.2)), ('aster_1', .97, 1, (0.2, -1, -0.4))])
S.felt_leaves(V, Tn, [2, 4, 7, 9, 11], '#4D6A4C')
SUM.append(S.report({'size': SIZE,
    'idea': 'The vine hangs from the two top corners in a long swag, like wisteria: lavender and snapdragons hang from it, roses and daisies face out from the low point.',
    'fabric': 'A two-panel split curtain (noren) hangs from the upper rail in front of a linen back; felt leaves on the knuckles.'}))


# ======================================================================= 4. Dense garden wall: flat-printed back wall, fabric sides
PANEL_Y = 53.6                              # front face of the printed back wall
class Walled(Box):
    def frame_walled(self, sides='#3E4A45'):
        for y in (YF, YB):
            for sx in (-1, 1): self.axle32((sx * H, y, ZC), (0, 0, 1))
            for sz in (-1, 1): self.axle32((0, y, ZC + sz * H), (1, 0, 0))
        for sx in (-1, 1):
            for sz in (-1, 1):
                for y in DEPTH_Y: self.part('26287', 'Dark Green', frame((0, 1, 0)), (sx * H, y, ZC + sz * H), 'Structure: depth connector')
                for y in (YF, YB): self.mesh(box([NODE] * 3, (sx * H, y, ZC + sz * H)), 'pla', 'Corner node')
        self.mesh(box([34, 8, 22], (0, YB + 7, ZC + H - 4)), 'pla', 'Hanger clip with keyhole (snaps on the top back axle)')
        L = YB - YF - 2 * 4
        for sx in (-1, 1):                                                       # fabric side panels, clipped to front and back uprights
            self.mesh(box([1.0, L, 2 * H - 8], (sx * (H + 4), 0, ZC)), 'fabric:' + sides, 'Fabric side panel')
            for y in (YF, YB):
                for z in (ZC - 80, ZC, ZC + 80): self.mesh(box([7, 9, 14], (sx * (H + 3), y + (5 if y < 0 else -5), z)), 'clear', 'Fabric clip (clear TPU)')
        for sz in (-1, 1):                                                       # top and bottom cloth
            self.mesh(box([2 * H - 8, L, 1.0], (0, 0, ZC + sz * (H + 4))), 'fabric:' + sides, 'Fabric top / bottom panel')
            for y in (YF, YB):
                for x in (-80, 0, 80): self.mesh(box([14, 9, 7], (x, y + (5 if y < 0 else -5), ZC + sz * (H + 3))), 'clear', 'Fabric clip (clear TPU)')

    def back_wall(self, motif):
        """Four flat-printed tiles (each 134 x 134, fits the CORE One bed) that snap over the back frame; 1.2 mm wall plus ribs on the back,
        with a shallow relief motif to paint and posts that hold the vine."""
        t = 1.2; half = H - 1
        for sx in (-1, 1):
            for sz in (-1, 1):
                c = (sx * half / 2, PANEL_Y + t / 2, ZC + sz * half / 2)
                self.mesh(box([half - 0.8, t, half - 0.8], c), 'pla', 'Back wall tile (printed flat)')
        for m, col, label in motif: self.mesh(m, 'paint:' + col, label)

    def posts(self, V, idx):
        for i in idx:
            a = V[i]; b = np.array([a[0], PANEL_Y, a[2]])
            self.mesh(seg_cyl(a + [0, 6, 0], b, 3.2), 'pla', 'Vine post (printed on the wall tile)')

def relief_disc(cx, cz, r, depth=0.8):
    return cyl(r, depth, (cx, PANEL_Y - depth / 2, cz), (0, 1, 0), 96)
def relief_band(z, h, x0, x1, depth=0.8, wave=6, seed=0):
    """A kasumi mist band: a rounded strip with wavy ends, raised 0.8 mm."""
    r = np.random.default_rng(seed); xs = np.linspace(x0, x1, 40)
    top = z + h / 2 + wave * np.sin(xs / 37 + seed); bot = z - h / 2 + wave * np.sin(xs / 41 + seed + 1)
    poly = [(x, zz) for x, zz in zip(xs, top)] + [(x, zz) for x, zz in zip(xs[::-1], bot[::-1])]
    from shapely.geometry import Polygon
    m = trimesh.creation.extrude_polygon(Polygon(poly).buffer(4).buffer(-4), depth)        # in XY, extruded along Z
    Tm = np.array([[1, 0, 0, 0], [0, 0, -1, PANEL_Y], [0, 1, 0, 0], [0, 0, 0, 1]], float)   # XY plane -> XZ plane at the wall face
    m.apply_transform(Tm); return m

S = Walled('sb_dense', 'Garden wall')
S.frame_walled('#46564D')
motif = [(relief_disc(58, ZC + 62, 62), '#D8BF86', 'Relief moon, painted gold'),
         (relief_band(ZC - 36, 26, -128, 40, seed=1), '#E2C3C4', 'Relief mist band, painted blush'),
         (relief_band(ZC + 18, 18, -40, 128, seed=2), '#C9D3C3', 'Relief mist band, painted sage')]
S.back_wall(motif)
LO[1], HI[1] = -60.0, PANEL_Y - 1.5
V, Tn = S.vine([(-128, 30, 30), (-70, 24, 64), (10, 20, 70), (84, 22, 104), (104, 24, 152), (44, 22, 186), (-46, 22, 190), (-100, 24, 222), (-80, 28, 262)])
S.posts(V, [3, 7, 11, 15])
VA = V
V2, T2 = S.vine([(128, 30, 26), (70, 24, 34), (0, 22, 30), (-60, 24, 36)])
S.posts(V2, [2])
S.knots = [(VA, Tn)]
S.vine_pts = np.vstack([q['p'] for q in S.lego if q['role'].startswith('Vine')])
S.bough('branch_1', (128, 30, 250), range(165, 240, 5))
along(S, VA, [('roses_1', .05, 1, 60), ('daisies_1', .1, -1, 70), ('poppies_1', .16, 1, 70), ('foliage_1', .2, -1, 25), ('aster_1', .26, 1, 70),
              ('daisies_2', .32, -1, 70), ('lavender_1', .37, 1, 15), ('roses_2', .43, -1, 60), ('daisies_4', .49, 1, 70), ('poppies_2', .55, -1, 70),
              ('lavender_2', .6, 1, 15), ('daisies_5', .66, -1, 70), ('roses_3', .72, 1, 60), ('foliage_2', .77, -1, 25), ('daisies_6', .83, 1, 70),
              ('lavender_3', .9, -1, 15), ('daisies_3', 1, 1, 70)])
S.knots = [(V2, T2)]
along(S, V2, [('ground cover_1', .2, 1, (0, -0.4, 1)), ('ground cover_2', .45, 1, (0.2, -0.4, 1)), ('ground cover_3', .7, 1, (-0.2, -0.4, 1)), ('ground cover_4', .95, 1, (0, -0.5, 1))])
S.felt_leaves(VA, Tn, [2, 6, 9, 13, 17], '#55704F')
SUM.append(S.report({'size': SIZE,
    'idea': 'A dense garden wall: one long vine climbs in an S carrying every bouquet flower, a short ground vine runs along the bottom with the ground cover, and the cherry bough leans in from the top-right corner.',
    'fabric': 'Fabric on the two sides, top and bottom, clipped to the frame; the printed back wall carries a raised moon and two mist bands to paint.'}))

json.dump([{k: v for k, v in s.items() if k not in ('lego', 'printed')} for s in SUM], open(os.path.join(W, 'sb_summary.json'), 'w'), indent=1)
