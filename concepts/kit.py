"""Shared helpers for the concept mock-ups: the flower/branch library, a Scene of LEGO placements and printed meshes, and simple solids.

World frame: millimetres, Z up, shelf surface at z = 0, viewer looking from -Y.
"""
import json, math, os
import numpy as np, trimesh
from manifold3d import Manifold, Mesh as MM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = os.path.join(ROOT, 'concepts', 'work')
LIB = json.load(open(os.path.join(W, 'library.json')))
rng = np.random.default_rng(3)

def unit(v): v = np.asarray(v, float); return v / np.linalg.norm(v)
def frame(z, spin=0.0, xhint=None):
    z = unit(z); a = np.array(xhint, float) if xhint is not None else (np.array([1.0, 0, 0]) if abs(z[0]) < 0.9 else np.array([0, 1.0, 0]))
    x = unit(a - z * a.dot(z)); y = np.cross(z, x)
    c, s = math.cos(spin), math.sin(spin); x, y = c * x + s * y, -s * x + c * y
    return np.column_stack([x, y, z])
def Rx(a): c, s = math.cos(a), math.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def Ry(a): c, s = math.cos(a), math.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
def Rz(a): c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

class Scene:
    def __init__(self, name, title):
        self.name, self.title = name, title; self.lego = []; self.printed = []; self.notes = {}
    def part(self, pid, colour, R, p, role=''):
        self.lego.append({'part': pid, 'colour': colour, 'R': np.asarray(R).round(6).tolist(), 'p': np.asarray(p, float).round(3).tolist(), 'role': role})
    def unit(self, name, R, origin, skip=()):
        for q in LIB[name]['parts']:
            if any(q['role'].startswith(s) for s in skip): continue
            self.part(q['part'], q['colour'], R @ np.array(q['R']), np.asarray(origin) + R @ np.array(q['p']), q['role'])
    def stem(self, base, top, colour='Dark Green'):
        """LEGO stem: 3L axle connectors end to end (each holds a hidden 2L axle at the joint)."""
        base, top = np.asarray(base, float), np.asarray(top, float); d = top - base; L = np.linalg.norm(d); R = frame(d)
        n = max(1, int(round(L / 24)))
        for k in range(n): self.part('26287', colour, R, base + d * (k + 0.5) / n, 'Stem (3L connector)')
        return top
    def flower(self, name, base, top, spin=0.0, stem=True):
        top = np.asarray(top, float); d = unit(top - np.asarray(base, float))
        if stem: self.stem(base, top)
        self.unit(name, frame(d, spin), top)
    def branch(self, name, root, direction, up, flip=False):
        x = unit(direction); y = unit(np.asarray(up) - x * np.dot(up, x)); z = np.cross(x, y)
        if flip: y, z = -y, -z
        self.unit(name, np.column_stack([x, y, z]), np.asarray(root) - z * 4.5)
    def axle32(self, centre, direction, colour='Sand Green'):
        d = unit(direction); R = frame(d); R = R[:, [2, 0, 1]]          # LDraw 50450 axis is local X
        self.part('50450', colour, R, centre, 'Structure: 32L axle')
    def mesh(self, m, kind, label, grams=None):
        self.printed.append({'kind': kind, 'label': label, 'm': m, 'grams': grams})
    def save(self, desc):
        out = {'name': self.name, 'title': self.title, 'lego': self.lego, 'printed': [], 'desc': desc}
        tot = 0
        for p in self.printed:
            m = p['m']
            g = p['grams'] if p['grams'] is not None else printed_grams(m, p['kind'], 'tone' in p['label'])
            if p['kind'] in ('pla', 'tpu', 'clear'): tot += g
            out['printed'].append({'kind': p['kind'], 'label': p['label'], 'grams': round(g, 1), 'v': m.vertices.round(3).tolist(), 'f': m.faces.tolist()})
        out['printed_grams'] = round(tot); out['lego_count'] = len(self.lego)
        json.dump(out, open(os.path.join(W, self.name + '.json'), 'w'))
        return out

def printed_grams(m, kind, hollow=False):
    """Rough slicer-style estimate: 0.9 mm shell + 15 % infill, PLA 1.24 / TPU 1.21 g/cm3."""
    if kind not in ('pla', 'tpu', 'clear'): return 0.0
    V = abs(m.volume) / 1000; A = m.area / 100; shell = min(V, A * 0.09)
    if hollow: return (shell + (V - shell) * 0.05) * 1.24
    return (shell + (V - shell) * 0.15) * (1.24 if kind == 'pla' else 1.21)

def M(m): return Manifold(MM(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
def T(mf): o = mf.to_mesh(); return trimesh.Trimesh(np.asarray(o.vert_properties)[:, :3], np.asarray(o.tri_verts))
def box(ext, c): b = trimesh.creation.box(ext); b.apply_translation(c); return b
def cyl(r, h, c, axis=(0, 0, 1), sections=48):
    m = trimesh.creation.cylinder(r, h, sections=sections); R = frame(axis); Tm = np.eye(4); Tm[:3, :3] = R; Tm[:3, 3] = c; m.apply_transform(Tm); return m
def stone(size, seed, centre=(0, 0, 0)):
    """Low-poly stone: jittered icosphere, flat bottom, hollow-printed."""
    r = np.random.default_rng(seed); s = trimesh.creation.icosphere(2, 1.0)
    v = s.vertices * (1 + 0.16 * r.standard_normal(len(s.vertices)))[:, None]
    s = trimesh.Trimesh(v * np.array(size) / 2, s.faces); s = s.convex_hull
    s.apply_translation([centre[0], centre[1], size[2] * 0.32])
    cut = M(box([size[0] * 2, size[1] * 2, 200], (centre[0], centre[1], 100)))
    return T(M(s) ^ cut)
def socket_holes(m, pts, depth=12):
    mf = M(m)
    for p, d in pts: mf = mf - M(cyl(2.7, depth * 2, np.asarray(p), d, 16))
    return T(mf)

