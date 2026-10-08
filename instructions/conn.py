"""List the connection primitives inside an LDraw part, with their position and axis in the part's own frame.

usage: python instructions/conn.py 26287 90202 ...
Every LDraw primitive is placed by a 4x4 transform; a stud's axis is its local -Y, an axle or pin hole runs along its
local Y, and a cylinder primitive scaled to radius 4 LDU is a bar (3.18 mm).
"""
import os, sys, re, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pipeline'))
import ldraw

KINDS = [
    (r'^(stud|stud2|stud2a|stud6|stud6a|stud10|stud15|studp\d+|stud-\w+|stud17a|stud2s)\.dat$', 'stud'),
    (r'^(stud3|stud3a|stud4|stud4a|stud4h|stud4o|stud4s|stud12|stud16|stud18a|stud4f\d\w)\.dat$', 'antistud'),
    (r'^(axle|axleend|axlehol\d*|axl\dhol\d*|axlehole|axl\dhole|axlehol8|axl2hol\d)\.dat$', 'axle'),
    (r'^(connhole|connhol\d|beamhole|beamhol\d|peghole|npeghol\w*|connhol\w*)\.dat$', 'pinhole'),
    (r'^(connect\d*|confric\d*|confric|connect)\.dat$', 'pin'),
]
def kind_of(name):
    n = os.path.basename(name.replace('\\', '/')).lower()
    for pat, k in KINDS:
        if re.match(pat, n): return k
    m = re.match(r'^(\d+)-(\d+)(cyli|cylo|cylc|cyls|edge|disc)\.dat$', n)
    if m: return 'cyl'
    return None

def walk(name, M=np.eye(3), o=np.zeros(3), depth=0, out=None):
    out = [] if out is None else out
    rel = ldraw.locate(name)
    if rel is None: return out
    for line in open(ldraw.fetch(rel), encoding='utf-8', errors='replace'):
        t = line.split()
        if not t or t[0] != '1' or len(t) < 15: continue
        x, y, z, a, b, c, d, e, f, g, h, i = map(float, t[2:14]); sub = ' '.join(t[14:])
        Ms = np.array([[a, b, c], [d, e, f], [g, h, i]]); os_ = np.array([x, y, z])
        Mw = M @ Ms; ow = M @ os_ + o
        k = kind_of(sub)
        if k == 'cyl':
            r = np.linalg.norm(Mw[:, 0]); ln = np.linalg.norm(Mw[:, 1]); ax = Mw[:, 1] / (ln or 1)
            if abs(r - 4) < 0.6 and ln > 3: out.append(('bar', ow, ax, ln, sub))
            continue
        if k:
            ax = Mw[:, 1] / (np.linalg.norm(Mw[:, 1]) or 1)
            out.append((k, ow, ax, np.linalg.norm(Mw[:, 1]), sub)); continue
        if depth < 6 and not os.path.basename(sub.replace('\\', '/')).lower().startswith(('4-4', '1-4', '2-4', '3-4', '1-8', '3-8', '5-8', '7-8', '1-16', '3-16', 'rect', 'box', 'tri', 'ring')):
            walk(sub, Mw, ow, depth + 1, out)
    return out

def summary(pid):
    rows = walk(pid + '.dat')
    seen = set(); res = []
    for k, p, ax, ln, sub in rows:
        key = (k, tuple(np.round(p, 1)), tuple(np.round(np.abs(ax), 2)))
        if key in seen: continue
        seen.add(key); res.append((k, np.round(p, 2), np.round(ax, 3), round(ln, 1), sub))
    return res

if __name__ == '__main__':
    for pid in sys.argv[1:]:
        print('==', pid)
        for k, p, ax, ln, sub in summary(pid): print(f'  {k:8s} p={p.tolist()} ax={ax.tolist()} len={ln} {sub}')
