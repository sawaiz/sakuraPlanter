"""LEGO 40725 Cherry Blossoms, rebuilt step by step from the official instructions (6554062.pdf).

Two branches with the same 19 steps: white blossoms first (manual pages 4-25), pink second (pages 27-49).
LDraw units, -Y up. Run: python instructions/s40725.py  -> docs/sets/40725/data/set.js
"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from model import Model, frame, axis_frame, align, put, rot, unit, RY      # noqa: E402

UP = np.array([0, -1.0, 0]); DOWN = -UP
X = np.array([1.0, 0, 0]); Z = np.array([0, 0, 1.0])
VERT_Z = axis_frame((0, 1, 0), 'z')          # 32034 / 6538b / 24122: their local Z along the trunk
VERT_X = axis_frame((0, 1, 0), 'x')          # 4519 / 32062: their local X along the trunk
BR = 'Reddish Brown'

class Sockets:
    """Free places a blossom can go: (name, surface point, outward direction)."""
    def __init__(self): self.s = {}
    def add(self, name, p, d): self.s[name] = (np.asarray(p, float), unit(d))
    def take(self, name): return self.s.pop(name)

# ---------------------------------------------------------------- small pieces of the build
def segment(m, y, side_hi, side_lo, socks=None, tag=''):
    """Steps 1-2 geometry: two 32034 stacked on a 3L axle, a 3L axle sticking out of the top.
    Returns hole centres of the two 32034 (upper, lower)."""
    lo = np.array([0, y, 0.0]); hi = np.array([0, y - 60, 0.0])
    return lo, hi

def side_pin(m, hole, side):
    """89678 half pin in a 32034's pin hole, pointing out along `side`."""
    side = unit(side)
    M = np.column_stack([side, [0, 1.0, 0], np.cross(side, [0, 1.0, 0])])
    return m.add('89678', 'Dark Bluish Gray', M, hole + side * 10)

def side_plate(m, hole, side):
    M = frame(up=side, x=(0, 1, 0)); return m.add('85861', BR, M, put((0, 8, 0), M, hole + side * 10))

def side_claw(m, hole, side):
    """48729b on the plate's open stud, clip axis front-to-back. Returns the claw's clip centre and frame."""
    M = frame(up=side, x=(0, 1, 0)); t = hole + side * 35
    m.add('48729b', BR, M, t); return t, M

def holder_in_claw(m, claw_t, claw_M, tilt=0.0):
    """23443 with its handle in the claw, body pointing outward (optionally hinged up by `tilt` degrees)."""
    side = claw_M @ np.array([0, -1.0, 0]); M = frame(up=side, x=(0, 1, 0))
    if tilt: M = rot(Z * np.sign(-side[0] or 1), tilt) @ M
    return M, claw_t

def red_bar_on_side_stud(m, brick_M, brick_t, k, colour='Dark Red', ref=None):
    """65578 with its angled bar in side stud k (0:+x 1:-x 2:+z 3:-z) of a 4733."""
    d = [(1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)][k]
    out = brick_M @ np.array(d, float); stud = brick_M @ (np.array(d, float) * 10 + np.array([0, 10, 0])) + brick_t
    tip = stud - out * 4
    up_ref = brick_M @ np.array([0, -1.0, 0]) if ref is None else ref
    M = align((-0.707, 0.707, 0), -out, (0, -1, 0), up_ref + out * 0.6)
    i = m.add('65578', colour, M, put((-10, 19.7, 0), M, tip))
    return i, M

def plate_top(m, i):
    """Surface point and outward direction of a 1x1 round part's top stud (65578 / 85861 / 24866)."""
    M, t = m.T(i); return t, M @ np.array([0, -1.0, 0])

def brick_top(m, i):
    M, t = m.T(i); return t, M @ np.array([0, -1.0, 0])

def brick_side(m, i, k):
    M, t = m.T(i); d = np.array([(1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)][k], float)
    return M @ (d * 10 + np.array([0, 10, 0])) + t, M @ d

# ---------------------------------------------------------------- blossoms and buds (callout sub-builds)
def blossom(kind, crown, centre, base=None):
    """kind 'dr' (dark red flower base), 'lime' (leaves base) or 'bare' (crown straight on). Local frame: the
    blossom's bottom surface at y = +8 below the origin of its lowest piece."""
    s = Model(f'blossom_{kind}_{crown.split()[0].lower()}', 'Blossom')
    y = 0.0
    if kind == 'dr': s.add('24866', 'Dark Red', np.eye(3), (0, y, 0)); y -= 8
    elif kind == 'lime': s.add('32607', 'Lime', RY(30), (0, y, 0)); y -= 8
    s.step()
    if kind == 'bare':
        s.add('24866', centre, np.eye(3), (0, -8, 0)); s.step()
        s.add('39262', crown, np.eye(3), (0, 0, 0)); s.step()
    else:
        s.add('39262', crown, np.eye(3), (0, y, 0)); s.add('24866', centre, np.eye(3), (0, y - 8, 0)); s.step()
    return s

def bud(swirl):
    s = Model(f'bud_{swirl.split()[0].lower()}', 'Bud')
    s.add('24866', 'Dark Red'); s.step(); s.add('15470', swirl, np.eye(3), (0, 0, 0)); s.step()
    return s

def place_on(m, sub, surface, out, spin=0.0, depth=8.0, base_y=8.0):
    """Put a 1x1 sub-build (bottom surface at local y=base_y) onto a stud/bar whose top is `surface`, facing `out`."""
    M = rot(out, spin) @ frame(up=out, x=None)
    return m.place(sub, M, put((0, base_y, 0), M, surface))

# ---------------------------------------------------------------- the branch
def branch(colour_name):
    white = colour_name == 'white'
    crown = 'White' if white else 'Bright Pink'; centre = 'Bright Pink' if white else 'Dark Pink'
    swirl = 'White' if white else 'Bright Pink'
    m = Model(f'branch_{colour_name}', f'{"White" if white else "Pink"} branch')
    subs = []
    SO = Sockets()

    # steps 1-2: trunk tip, two 32034 on 3L axles
    A, B = np.array([0, 0, 0.0]), np.array([0, -60, 0.0])
    m.add('32034', BR, VERT_Z, A); m.add('4519', 'Light Bluish Gray', VERT_X, (0, -30, 0)); m.step(view=dict(az=-25, el=15))
    m.add('32034', BR, VERT_Z, B); m.add('4519', 'Light Bluish Gray', VERT_X, (0, -90, 0)); m.step()
    # steps 3-5: half pins, round plates, claws (upper one left, lower one right)
    sides = [(B, -X), (A, X)]
    for h, s_ in sides: side_pin(m, h, s_)
    m.step()
    for h, s_ in sides: side_plate(m, h, s_)
    m.step()
    claws = [side_claw(m, h, s_) for h, s_ in sides]
    m.step()

    # step 6 (2x): the same trunk section with a hub on top
    S6 = Model('trunk_section', 'Trunk section')
    S6.add('32034', BR, VERT_Z, A); S6.add('4519', 'Light Bluish Gray', VERT_X, (0, -30, 0)); S6.step()
    S6.add('32034', BR, VERT_Z, B); S6.add('4519', 'Light Bluish Gray', VERT_X, (0, -90, 0)); S6.step()
    for h, s_ in sides: side_pin(S6, h, s_)
    S6.step()
    for h, s_ in sides: side_plate(S6, h, s_)
    S6.step()
    for h, s_ in sides: side_claw(S6, h, s_)
    S6.step()
    S6.add('24122', BR, VERT_Z, (0, -100, 0)); S6.step()
    subs.append(S6)
    sec_t = [np.array([0, 140, 0.0]), np.array([0, 280, 0.0])]
    for t in sec_t: m.place(S6, np.eye(3), t)
    m.step(callout=S6, mult=2)
    claws += [(c + t, M) for t in sec_t for c, M in [side_claw(Model('_'), h, s_) for h, s_ in sides]]
    hubs = [np.array([0, -100, 0.0]) + t for t in sec_t]

    # step 7: 23443 holders in the top two claws
    tops = []
    for (ct, cM), tilt in zip(claws[:2], (35, 35)):
        M, t = holder_in_claw(m, ct, cM, tilt); tops.append((M, t)); m.add('23443', BR, M, t)
    m.step()

    # steps 8-9: holders with a 4733 and dark red angled bars, into the middle and lower claws
    def holder_cluster(nbars, name):
        S = Model(name, 'Side twig')
        S.add('23443', BR); S.step()
        S.add('78258', BR, np.eye(3), (0, -30, 0)); S.step()
        b = S.add('4733', BR, np.eye(3), (0, -54, 0)); S.step()
        for k in ([0, 1] if nbars == 2 else [0, 1, 2, 3]): red_bar_on_side_stud(S, np.eye(3), np.array([0, -54, 0.0]), k)
        S.step(); return S
    S8 = holder_cluster(2, 'side_twig_2'); S9 = holder_cluster(4, 'side_twig_4'); subs += [S8, S9]
    clusters = []
    for S, cl in ((S8, claws[2:4]), (S9, claws[4:6])):
        for ct, cM in cl:
            M, t = holder_in_claw(m, ct, cM); idx = m.place(S, M, t); clusters.append((S, idx))
        m.step(callout=S, mult=2)

    # step 10 (seen from the back): four angled twigs on the two hubs
    S10 = Model('hub_twig', 'Hub twig')
    S10.add('65578', 'Dark Red'); S10.step()
    S10.add('85861', BR, np.eye(3), (0, -8, 0)); S10.step()
    S10.add('78258', BR, np.eye(3), (0, -28, 0)); S10.step()
    subs.append(S10)
    twigs = []
    for hub in hubs:
        for side in (-X, X):
            M = align((-0.707, 0.707, 0), -side, (0, -1, 0), UP + side * 0.3)
            t = put((-10, 19.7, 0), M, hub + side * 14); idx = m.place(S10, M, t); twigs.append((M, t, idx))
    m.step(callout=S10, mult=4, rotate=True, view=dict(az=160, el=15))

    # step 11: 85861 + 4733 + two red bars on the lower twigs' tips
    S11 = Model('twig_tip', 'Twig tip')
    S11.add('85861', BR); S11.step()
    b11 = S11.add('4733', BR, np.eye(3), (0, -32, 0)); S11.step()
    for k in (0, 1): red_bar_on_side_stud(S11, np.eye(3), np.array([0, -32, 0.0]), k)
    S11.step(); subs.append(S11)
    s11 = []
    for M, t, idx in twigs[2:]:
        tip = M @ np.array([0, -48, 0.0]) + t; up = M @ np.array([0, -1.0, 0])
        MM = frame(up=up, x=M @ X); s11.append(m.place(S11, MM, put((0, 8, 0), MM, tip + up * 4)))
    m.step(callout=S11, mult=2, view=dict(az=-20, el=15))

    # step 12: a cone, a 4733 and two red bars on the top axle
    S12 = Model('crown_top', 'Top')
    S12.add('4589', BR); S12.step()
    S12.add('4733', BR, np.eye(3), (0, -28, 0)); S12.step()
    for k in (0, 1): red_bar_on_side_stud(S12, np.eye(3), np.array([0, -28, 0.0]), k)
    S12.step(); subs.append(S12)
    s12 = m.place(S12, np.eye(3), (0, -114, 0))
    m.step(callout=S12, mult=1)

    # step 13: the long trunk, 10x (32062 into 6538)
    S13 = Model('trunk_link', 'Trunk link')
    S13.add('6538b', BR, VERT_Z, (0, 20, 0)); S13.step(); S13.add('32062', 'Black', VERT_X, (0, 0, 0)); S13.step()
    subs.append(S13)
    y0 = 310.0
    for k in range(10): m.place(S13, np.eye(3), (0, y0 + 40 * k, 0))
    m.step(callout=S13, mult=10, view=dict(az=-25, el=10, zoom=0.9))

    # sockets for blossoms --------------------------------------------------------------
    P = m.parts
    def idx_of(idxs, pid): return [i for i in idxs if P[i]['pid'] == pid]
    SO.add('top', *brick_top(m, idx_of(s12, '4733')[0]))
    for i, r in enumerate(idx_of(s12, '65578')): SO.add(f'top_red{i}', *plate_top(m, r))
    for j, idx in enumerate(s11):
        SO.add(f's11_top{j}', *brick_top(m, idx_of(idx, '4733')[0]))
        for i, r in enumerate(idx_of(idx, '65578')): SO.add(f's11_red{j}{i}', *plate_top(m, r))
        for k in (2, 3): SO.add(f's11_side{j}{k}', *brick_side(m, idx_of(idx, '4733')[0], k))
    for j, (M, t, idx) in enumerate(twigs[:2]):
        SO.add(f'twig_tip{j}', M @ np.array([0, -48, 0.0]) + t, M @ np.array([0, -1.0, 0]))
    for j, (M, t, idx) in enumerate(twigs):
        SO.add(f'twig_red{j}', *plate_top(m, idx_of(idx, '65578')[0]))
    for j, (S, idx) in enumerate(clusters):
        br = idx_of(idx, '4733')[0]; SO.add(f'cl_top{j}', *brick_top(m, br))
        for i, r in enumerate(idx_of(idx, '65578')): SO.add(f'cl_red{j}{i}', *plate_top(m, r))
        if S is S8:
            for k in (2, 3): SO.add(f'cl_side{j}{k}', *brick_side(m, br, k))

    bl_dr, bl_lime, bl_bare = blossom('dr', crown, centre), blossom('lime', crown, centre), blossom('bare', crown, centre)
    subs += [bl_dr, bl_lime, bl_bare]
    def bloom(sub, names, spin0=0):
        for k, n in enumerate(names):
            p, d = SO.take(n); place_on(m, sub, p, d, spin=spin0 + 47 * k)

    # steps 14-18: 37 blossoms
    bloom(bl_dr, ['top', 's11_top0', 's11_top1']); m.step(callout=bl_dr, mult=3, view=dict(az=-20, el=15))
    bloom(bl_lime, ['twig_tip0', 'twig_tip1', 'cl_top0', 'cl_top1', 'cl_top2', 'cl_top3']); m.step(callout=bl_lime, mult=6)
    bloom(bl_dr, ['s11_red00', 's11_red01', 's11_red10', 's11_red11']); m.step(callout=bl_dr, mult=4, rotate=True, view=dict(az=150, el=15))
    bloom(bl_lime, ['top_red0', 'top_red1'] + [f'cl_red{j}{i}' for j in (2, 3) for i in range(4)]); m.step(callout=bl_lime, mult=10, view=dict(az=-20, el=15))
    rest = [n for n in SO.s.keys()]
    bloom(bl_bare, rest[:14]); m.step(callout=bl_bare, mult=14, rotate=True, view=dict(az=150, el=15))

    # step 19 (2x): a V twig with a small Y twig and three buds, into the two top holders
    S19 = Model('bud_twig', 'Bud twig')
    S19.add('24855', BR); S19.step()
    S19.add('68211', BR, np.eye(3), (0, -6, 0)); S19.step()
    bd = bud(swirl); subs.append(bd)
    tips = [(np.array([-23.6, -26.5, -13.3]), np.array([-23.6, -26.5, -13.3])), (np.array([21.8, -22, -12.0]), np.array([21.8, -22, -12.0])),
            (np.array([5.8, -31.5, -8.0]), np.array([5.8, -25.5, -8.0]))]
    for p, d in tips: place_on(S19, bd, p, d, depth=6)
    S19.step(callout=bd, mult=3); subs.append(S19)
    for M, t in tops:
        m.place(S19, M, M @ np.array([0, -38, 0.0]) + t)
    m.step(callout=S19, mult=2, view=dict(az=-20, el=15))
    pages = [4, 4, 5, 5, 6, 7, 10, 11, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24]
    for st, pg in zip(m.steps, pages): st['meta']['pdf'] = pg + (0 if white else 23)
    return m, subs

def build():
    w, sw = branch('white'); p, sp = branch('pink')
    # final: both branches together as in the box picture (page 50)
    fin = Model('final', 'Cherry Blossoms')
    fin.place(w, rot((0, 0, 1), 8), (60, 0, 0)); fin.place(p, rot((0, 0, 1), -10), (-70, -60, 0)); fin.step()
    seen = {}; subs = []
    for s in sw + sp:
        if s.name not in seen: seen[s.name] = 1; subs.append(s)
    return [w, p, fin], subs

if __name__ == '__main__':
    from pack import pack, part_names
    models, subs = build()
    out = os.path.join(os.path.dirname(HERE), 'docs', 'sets', '40725', 'data', 'set.js')
    pack(models + subs, out, extra={'set': '40725', 'names': part_names()})
    for mm in models[:2]: print(mm.name, len(mm.parts), 'pieces', len(mm.steps), 'steps')
