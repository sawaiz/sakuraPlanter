"""A small modelling kit for rebuilding the official LEGO builds step by step in LDraw units.

Coordinates are LDraw's: LDU, -Y is up. A part is placed with a 3x3 matrix M (columns = where its local x, y, z
axes go) and a position t, so world = M @ local + t.

A Model is one build in its own frame: the parts it adds and the steps that add them. A step can carry a callout
(a sub-build Model placed one or more times in that step) and the page furniture the manual shows (a rotate icon,
a 1:1 check, a note). Sub-builds keep their own steps, so the viewer can play them inside the callout.
"""
import json, math
import numpy as np

COL = {'Black': 0, 'Blue': 1, 'Green': 2, 'Dark Turquoise': 3, 'Red': 4, 'Dark Pink': 5, 'Brown': 6, 'Light Gray': 7,
       'Yellow': 14, 'White': 15, 'Tan': 19, 'Orange': 25, 'Magenta': 26, 'Lime': 27, 'Bright Pink': 29,
       'Medium Lavender': 30, 'Lavender': 31, 'Reddish Brown': 70, 'Light Bluish Gray': 71, 'Dark Bluish Gray': 72,
       'Dark Purple': 85, 'Light Nougat': 78, 'Dark Green': 288, 'Pearl Gold': 297, 'Dark Red': 320,
       'Yellowish Green': 326, 'Sand Green': 378, 'Medium Nougat': 84, 'Bright Green': 10}

def unit(v): v = np.asarray(v, float); return v / np.linalg.norm(v)

def frame(up, x=None):
    """Matrix that turns a part so its local -Y (its 'up', where studs point) points along `up`, and its local +X
    points as near to `x` as possible."""
    u = unit(up); y = -u
    if x is None: x = (1, 0, 0) if abs(u[0]) < 0.9 else (0, 0, 1)
    x = np.asarray(x, float); x = unit(x - y * x.dot(y)); z = np.cross(x, y)
    return np.column_stack([x, y, z])

def axis_frame(axis, local='z', x=None):
    """Matrix that lays a part's local `local` axis ('x', 'y' or 'z') along world `axis`."""
    a = unit(axis); i = 'xyz'.index(local)
    if x is None: x = (1, 0, 0) if abs(a[0]) < 0.9 else (0, 0, 1)
    p = unit(np.asarray(x, float) - a * np.dot(x, a)); q = np.cross(a, p)
    cols = [None] * 3; cols[i] = a; cols[(i + 1) % 3] = p; cols[(i + 2) % 3] = q
    return np.column_stack(cols)

def rot(axis, deg):
    a = unit(axis); c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + s * K + (1 - c) * K @ K

def basis(a, r):
    a = unit(a); r = np.asarray(r, float); r = r - a * r.dot(a)
    if np.linalg.norm(r) < 1e-6: r = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 0, 1.0]); r = r - a * r.dot(a)
    r = unit(r); return np.column_stack([a, r, np.cross(a, r)])

def align(local_dir, world_dir, local_ref=None, world_ref=None, spin=0.0):
    """Rotation taking local_dir onto world_dir, turned about it so local_ref points as near world_ref as it can
    (then by `spin` degrees more)."""
    if local_ref is None: local_ref = (0, 1, 0) if abs(unit(local_dir)[1]) < 0.9 else (1, 0, 0)
    if world_ref is None: world_ref = (0, 1, 0) if abs(unit(world_dir)[1]) < 0.9 else (1, 0, 0)
    M = basis(world_dir, world_ref) @ basis(local_dir, local_ref).T
    return rot(world_dir, spin) @ M

def put(local_point, M, world_point):
    """Position so that local_point (in the part's frame, rotated by M) lands on world_point."""
    return np.asarray(world_point, float) - M @ np.asarray(local_point, float)

RX = lambda d: rot((1, 0, 0), d)
RY = lambda d: rot((0, 1, 0), d)
RZ = lambda d: rot((0, 0, 1), d)

class Model:
    def __init__(self, name, title=None):
        self.name, self.title = name, title or name
        self.parts = []          # {'pid','col','M','t','step'}
        self.steps = []          # {'new': [part idx], 'callout': {...} or None, 'meta': {...}}
        self.pending = []
        self.groups = []
        self.callout = None

    def add(self, pid, col, M=np.eye(3), t=(0, 0, 0)):
        c = COL[col] if isinstance(col, str) else col
        self.parts.append({'pid': pid, 'col': c, 'M': np.asarray(M, float), 't': np.asarray(t, float)})
        self.pending.append(len(self.parts) - 1)
        return len(self.parts) - 1

    def place(self, sub, M=np.eye(3), t=(0, 0, 0)):
        """Add every part of a finished sub-build, transformed; returns the new part indices."""
        M = np.asarray(M, float); t = np.asarray(t, float); out = []
        for p in sub.parts:
            out.append(self.add(p['pid'], p['col'], M @ p['M'], M @ p['t'] + t))
        self.groups.append(out)
        return out

    def step(self, callout=None, mult=None, **meta):
        """Close a step. callout: a sub-build Model shown in the step's callout box (with mult, e.g. 2 for '2x')."""
        s = {'new': self.pending, 'meta': meta}
        if callout is not None: s['callout'] = {'model': callout.name, 'mult': mult or 1}
        if callout is not None and self.groups: s['groups'] = [g for g in self.groups if g and g[0] in set(self.pending)]
        self.steps.append(s); self.pending = []; self.groups = []
        return len(self.steps)

    def T(self, i):
        p = self.parts[i]; return p['M'], p['t']

    def world(self, i, local):
        M, t = self.T(i); return M @ np.asarray(local, float) + t

    def mpd(self, subs=()):
        """LDraw text of this model (flattened parts, STEP lines)."""
        L = [f'0 FILE {self.name}.ldr', f'0 {self.title}', f'0 Name: {self.name}.ldr', '0 Author: sakuraPlanter rebuild', '']
        for s in self.steps:
            for i in s['new']:
                p = self.parts[i]; M = p['M']; t = p['t']
                L.append('1 %d %s %s %s.dat' % (p['col'], ' '.join(f'{v:.4g}' for v in t), ' '.join(f'{v:.6g}' for v in M.ravel()), p['pid']))
            L.append('0 STEP')
        return '\n'.join(L) + '\n'
