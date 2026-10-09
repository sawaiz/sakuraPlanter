"""LEGO 10280 Flower Bouquet, rebuilt step by step from the official instructions (6532379.pdf).

Each flower is a section in its own frame: head near the origin, stem running down +Y (LDraw: -Y is up).
Run: python instructions/s10280.py  -> docs/sets/10280/data/set.js
"""
import math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from model import Model, frame, axis_frame, align, put, rot, unit, RX, RY, RZ      # noqa: E402

UP = np.array([0, -1.0, 0]); X = np.array([1.0, 0, 0]); Z = np.array([0, 0, 1.0]); Y = np.array([0, 1.0, 0])
DG, SG, RED = 'Dark Green', 'Sand Green', 'Red'
AX_X = axis_frame((0, 1, 0), 'x')            # parts whose length runs along local X (axles, pins), laid along +Y
AX_Z = axis_frame((0, 1, 0), 'z')            # parts whose length runs along local Z (26287, 6538, 32034)

def dirdeg(a, el):
    """Unit direction at azimuth a (degrees, from +X towards +Z) and elevation el (degrees up)."""
    a, el = math.radians(a), math.radians(el)
    return np.array([math.cos(el) * math.cos(a), -math.sin(el), math.cos(el) * math.sin(a)])

# ---------------------------------------------------------------- stems
def connector_chain(m, top, n, axle_on_top=True):
    """n dark green 3L connectors (26287) end to end downwards from y=top, a red 2L axle in each joint and,
    optionally, one sticking up out of the top."""
    for k in range(n):
        if k or axle_on_top: m.add('32062', RED, AX_X, (0, top + 60 * k, 0))
        m.add('26287', DG, AX_Z, (0, top + 30 + 60 * k, 0))
    return top + 60 * n

def chain_sub(n, name='stem_link'):
    s = Model(name, 'Stem link'); s.add('26287', DG, AX_Z, (0, 30, 0)); s.step(); s.add('32062', RED, AX_X, (0, 0, 0)); s.step()
    return s

def long_axle(m, top):
    """A sand green 32L axle (50450) hanging down from y=top."""
    m.add('50450', SG, AX_X, (0, top + 320, 0)); return top + 640

def holder_frame(d, t):
    """23443 turned so its bar-holder end points along d, its handle along the tangent t."""
    return align((0, -1, 0), d, (0, 0, 1), t)

# ---------------------------------------------------------------- bag 1: daisies (2x)
def daisy_head():
    s = Model('daisy_head', 'Daisy head')
    s.add('2566', 'Tan'); s.step()
    arms = [dirdeg(45 + 90 * k, 0) * 14.1 for k in range(4)]
    for k, a in enumerate(arms):
        ang = 45 + 90 * k - 22.5; R = RY(-ang)
        s.add('35480', 'White', R, put((-10, 0, 0), R, a + np.array([0, -12, 0])))
    s.step()
    for k, a in enumerate(arms):
        ang = 45 + 90 * k + 22.5; R = RY(-ang)
        s.add('35480', 'White', R, put((-10, 0, 0), R, a + np.array([0, -20, 0])))
    s.step()
    s.add('14769', 'Yellow', np.eye(3), (0, -28, 0)); s.step()
    return s

def daisy():
    m = Model('daisy', 'Daisies')
    m.add('32054', 'Black', axis_frame((0, -1, 0), 'x'), (0, 12, 0)); m.step(view=dict(az=-30, el=20, min=80))
    m.add('90202', 'Black', np.eye(3), (0, -6, 0)); m.step()
    clips = []
    for k, (a, el) in enumerate([(0, 50), (90, 55), (180, 50), (270, 60)]):
        r = dirdeg(a, 0); t = np.cross(r, UP); d = dirdeg(a, el); c = np.array([0, -6, 0.0]) + r * 22
        M = holder_frame(d, t); m.add('23443', 'Black', M, c); clips.append((M, c, d))
    m.step()
    M, c, d = clips[3]; top = c + M @ np.array([0, -30, 0.0])
    m.add('33183', 'Reddish Brown', align((0, -1, 0), d), top - d * 8); m.step()
    H = daisy_head()
    for M, c, d in clips[:3]:
        top = c + M @ np.array([0, -30, 0.0]); R = align((0, -1, 0), d, (1, 0, 0), np.cross(d, UP) + 0.01)
        m.place(H, R, put((0, 24, 0), R, top))
    m.step(callout=H, mult=3)
    long_axle(m, 24); m.step(view=dict(az=-30, el=15))
    return m, [H]

# ---------------------------------------------------------------- bag 1: roses (3 heads, 2 curved stems, 1 straight)
WHEEL_RING_R, WHEEL_RING_Y = 40.0, -5.0       # 67811: ring centre radius and height in its own frame

def petal_frame(a, phi, inward=False):
    """Petal clipped to a ring at azimuth a: local X along the ring's tangent, its studs facing out, its tip
    (local -Z) pointing up, leaning in by phi degrees (out if phi < 0)."""
    r = dirdeg(a, 0); T = np.cross(UP, r); ph = math.radians(phi)
    n = r * math.cos(ph) + UP * math.sin(ph); tip = UP * math.cos(ph) - r * math.sin(ph)
    M = np.column_stack([T, n if inward else -n, -tip])
    if np.linalg.det(M) < 0: M = np.column_stack([-M[:, 0], M[:, 1], M[:, 2]])
    return M, r

def rose_head():
    m = Model('rose_head', 'Rose head')
    m.add('67811', DG); m.add('4032', 'Green', np.eye(3), (0, -8, 0)); m.step(view=dict(az=-30, el=30, min=80))
    m.add('67811', DG, np.eye(3), (0, -18, 0)); m.step()
    m.add('3941', 'Green', np.eye(3), (0, -42, 0)); m.step()
    # brackets: two on the brick (facing back and front), two on top of those (facing the sides)
    def bracket_pair(rot_deg, y):
        out = []
        for flip in (0, 180):
            R = RY(rot_deg + flip); t = R @ np.array([0, 0, 10.0]) + np.array([0, y, 0])
            out.append((R, t))
        return out
    A = bracket_pair(0, -50); B = bracket_pair(90, -58)
    S4 = Model('rose_bracket', 'Bracket'); S4.add('99207', 'Tan'); S4.step()
    Rs = align((0, -1, 0), (0, 0, -1), (0, 0, 1), (0, -1, 0)); S4.add('47458', 'Tan', Rs, put((0, 16, 0), Rs, (0, -22, -18))); S4.step()
    for R, t in A: m.place(S4, R, t)
    m.step(callout=S4, mult=2)
    for R, t in B: m.place(S4, R, t)
    m.step(callout=S4, mult=2)
    m.add('87580', 'Tan', np.eye(3), (0, -66, 0)); m.step()
    S7 = Model('rose_bud', 'Bud')
    S7.add('4733', 'White'); S7.add('24866', 'White', np.eye(3), (0, -8, 0)); S7.step()
    for k, d in enumerate([X, -X, Z, -Z]):
        R = align((0, -1, 0), d, (0, 0, -1), UP); S7.add('49668', 'White', R, put((0, 8, 0), R, d * 10 + np.array([0, 10, 0])))
    S7.step()
    m.place(S7, np.eye(3), (0, -90, 0)); m.step(callout=S7, mult=1)
    # inner petals: wedge + clip plate + tile, clipped to the upper wheel
    P8 = Model('rose_petal_inner', 'Inner petal')
    P8.add('93604', 'Light Nougat'); P8.add('3069', 'Light Nougat', np.eye(3), (0, -8, 0)); P8.step()
    P8.add('11476', 'Light Nougat', RY(180), (0, 8, -6)); P8.step()
    hinge = np.array([0, 10, 20.0])
    for k in range(4):
        M, r = petal_frame(45 + 90 * k, 4); P = r * (WHEEL_RING_R + 2) + np.array([0, -18 + WHEEL_RING_Y, 0])
        m.place(P8, M, P - M @ hinge)
    m.step(callout=P8, mult=4, view=dict(az=-30, el=35, min=80))
    # outer petals: mudguard + clip plate, clipped to the lower wheel from below
    P9 = Model('rose_petal_outer', 'Outer petal')
    P9.add('98835', 'Light Nougat'); P9.step(); P9.add('11476', 'Light Nougat', RY(180), (0, -8, -6)); P9.step()
    hinge9 = np.array([0, -6, 20.0])
    for k in range(4):
        M, r = petal_frame(90 * k, -20); P = r * (WHEEL_RING_R + 8) + np.array([0, WHEEL_RING_Y + 4, 0])
        m.place(P9, M, P - M @ hinge9)
    m.step(callout=P9, mult=4, rotate=True, view=dict(az=-20, el=-35, min=80))
    m.add('30374', 'Reddish Brown', np.eye(3), (0, 6, 0)); m.step(view=dict(az=-30, el=-20, min=80))
    return m, [S4, S7, P8, P9]

def leaf_on_clip(m, hub_y, side=1, droop=35):
    """98088 leaf clipped to the 90202 hub's clip on the +X (side=1) or -X side, its blade hanging outward."""
    R = RZ(droop * side) if side > 0 else RZ(180 + droop * side)
    m.add('98088', DG, R, np.array([24.0 * side + 4 * side, hub_y, 0]))

def rose_stem_curved():
    m = Model('rose_stem_curved', 'Rose stem, curved')
    m.add('26287', DG, AX_Z, (0, 30, 0)); m.add('4519', 'Light Bluish Gray', AX_X, (0, 0, 0)); m.step(view=dict(az=-30, el=20, min=80))
    m.add('90202', 'Black', np.eye(3), (0, -10, 0)); m.step()
    # 32016 on the axle top: straight leg down, bent leg up and toward +X
    B = np.column_stack([[0, 0, 1.0], [-1.0, 0, 0], [0, -1.0, 0]])          # local x -> +Z (pin hole), local y -> -X, local z -> up
    if np.linalg.det(B) < 0: B = np.column_stack([[0, 0, -1.0], [-1.0, 0, 0], [0, -1.0, 0]])
    j1 = np.array([0, -50, 0.0]); bend = B @ unit((0, -0.383, 0.924))
    m.add('32062', RED, align((1, 0, 0), bend), j1 + bend * 30); m.add('32016', DG, B, j1); m.step()
    R2 = rot(Z, 22.5) @ B
    j2 = j1 + bend * 60
    m.add('32016', DG, R2, j2); m.step()
    for J, M in ((j1, B), (j2, R2)):
        pin = M @ X
        Mp = frame(up=pin, x=(0, 1, 0)); m.add('85861', DG, Mp, put((0, 8, 0), Mp, J + pin * 10))
    m.step()
    for J, M in ((j1, B), (j2, R2)):
        pin = M @ X; s = 1
        m.add('13564', 'Reddish Brown', align((-1, 0, 0), pin, (0, -1, 0), UP + X), J + pin * 22)
    m.step()
    S7 = chain_sub(8); S7.name = 'stem_link'
    for k in range(8): m.place(S7, np.eye(3), (0, 60 + 60 * k, 0))
    m.step(callout=S7, mult=8, view=dict(az=-30, el=10))
    leaf_on_clip(m, -10, 1); m.step()
    top = j2 + (R2 @ unit((0, -0.383, 0.924))) * 30
    return m, [S7], (top, R2 @ unit((0, -0.383, 0.924)))

def rose_stem_straight():
    m = Model('rose_stem_straight', 'Rose stem, straight')
    m.add('26287', DG, AX_Z, (0, 30, 0)); m.add('4519', 'Light Bluish Gray', AX_X, (0, 0, 0)); m.step(view=dict(az=-30, el=20, min=80))
    m.add('90202', 'Black', np.eye(3), (0, -10, 0)); m.step()
    m.add('26287', DG, AX_Z, (0, -50, 0)); m.add('32062', RED, AX_X, (0, -80, 0)); m.step()
    m.add('26287', DG, AX_Z, (0, -110, 0)); m.step()
    S = chain_sub(8)
    for k in range(8): m.place(S, np.eye(3), (0, 60 + 60 * k, 0))
    m.step(callout=S, mult=8, view=dict(az=-30, el=10))
    leaf_on_clip(m, -10, 1); m.step()
    return m, [S], (np.array([0, -140, 0.0]), UP)

def roses(head, curved, c_top, straight, s_top):
    """Page 35: the three heads go onto the three stems."""
    m = Model('roses', 'Roses')
    xs = [-150, 0, 150]
    stems = [(curved, c_top, RY(180), xs[0]), (straight, s_top, np.eye(3), xs[1]), (curved, c_top, np.eye(3), xs[2])]
    heads = []
    for st, (top, d), R, x in stems:
        m.place(st, R, (x, 0, 0)); heads.append((R @ top + np.array([x, 0, 0]), R @ d))
    m.step(view=dict(az=-15, el=10))
    for p, d in heads:
        M = align((0, -1, 0), d, (1, 0, 0), (1, 0, 0)); m.place(head, M, p - M @ np.array([0, 70, 0]))
    m.step(view=dict(az=-15, el=10))
    return m

# ---------------------------------------------------------------- shared: a stem grip of 3L connectors under a 32L axle
def grip_stem(m, top, n_conn, sub_name):
    """Pages 46/66/80: n dark green connectors joined by red axles, then a 32L axle pushed into the top one.
    Built as its own callout; returns the sub-build (local frame: axle top at y=0)."""
    s = Model(sub_name, 'Stem')
    y0 = 640 - 30                                   # connectors hang off the axle's lower end
    s.add('26287', DG, AX_Z, (0, y0 + 30, 0)); s.step(view=dict(az=-30, el=15, min=90))
    for k in range(1, n_conn):
        s.add('32062', RED, AX_X, (0, y0 + 60 * k, 0)); s.add('26287', DG, AX_Z, (0, y0 + 30 + 60 * k, 0))
    s.step()
    s.add('50450', SG, AX_X, (0, 320, 0)); s.step(view=dict(az=-30, el=10))
    return s

def clip_ring(r=31.0, y=2.0, n=8, a0=0.0):
    """Clip spots round a 75937 bar frame (or a 67811 ring): (point, tangent, radial)."""
    out = []
    for k in range(n):
        a = a0 + 360 * k / n; rd = dirdeg(a, 0); out.append((rd * r + np.array([0, y, 0]), np.cross(UP, rd), rd))
    return out

def clip_on(m, sub, spot, hinge, up_deg=35, spin=0.0, out=False):
    """Clip a small sub-build (clip hinge at `hinge` in its frame, clip axis local X, face local -Y) onto a bar,
    facing outward and tipped up by up_deg. out=True: the clip is on the sub-build's top, so its body (local +Y)
    hangs outward from the bar instead."""
    p, t, rd = spot; face = unit(rd * math.cos(math.radians(up_deg)) + UP * math.sin(math.radians(up_deg)))
    if out: face = -face
    M = align((0, -1, 0), face, (1, 0, 0), t); M = rot(face, spin) @ M
    return m.place(sub, M, p - M @ hinge)

# ---------------------------------------------------------------- bag 2: California poppy
def poppy():
    m = Model('poppy', 'California poppy')
    m.add('3941', 'Green'); m.step(view=dict(az=-30, el=30, min=70))
    for z in (-10, 10): m.add('67329', 'Yellow', np.eye(3), (0, -40, z))
    m.add('3022', 'Yellow', np.eye(3), (0, -48, 0)); m.step()
    for x in (-10, 10):
        for z in (-10, 10): m.add('20482', 'Pearl Gold', np.eye(3), (x, -56, z))
    m.step()
    def side_petal(back):
        s = Model('poppy_petal_back' if back else 'poppy_petal', 'Petal')
        s.add('11476', 'Yellow'); s.step()
        if back: s.add('64225', 'Orange', np.eye(3), (0, -24, -10))
        else:
            for x in (-10, 10): s.add('50950', 'Orange', np.eye(3), (x, -24, -6))
        s.step(); return s
    P4, P5 = side_petal(False), side_petal(True)
    for P, sides in ((P4, (X, -X)), (P5, (Z, -Z))):
        for d in sides:
            M = align((0, -1, 0), d, (0, 0, -1), UP); m.place(P, M, d * 24 + np.array([0, -26, 0]) - M @ np.array([0, 8, 0]))
        m.step(callout=P, mult=2)
    for x in (-10, 10):
        for z in (-10, 10): m.add('11090', 'Yellow', RY(45 if x * z > 0 else -45), (x, -78, z))
    m.step()
    P7 = Model('poppy_petal_top', 'Large petal')
    P7.add('93604', 'Orange'); P7.step(); P7.add('2540', 'Orange', np.eye(3), (0, 8, 4)); P7.step()
    for k in range(4):
        rd = dirdeg(45 + 90 * k, 0); M = petal_frame(45 + 90 * k, -66, inward=True)[0]
        m.place(P7, M, rd * 34 + np.array([0, -70, 0]) - M @ np.array([0, 10, 18]))
    m.step(callout=P7, mult=4, view=dict(az=-30, el=40, min=80))
    Bp = np.column_stack([[0, 0, 1.0], [1.0, 0, 0], [0, 1.0, 0]])          # 32016 with its straight leg up into the flower
    j = np.array([0, 54, 0.0])
    m.add('32062', RED, AX_X, (0, 24, 0)); m.add('32016', DG, Bp, j); m.step(view=dict(az=-30, el=20))
    S = Model('poppy_stem', 'Stem'); S.add('26287', DG, AX_Z, (0, 610, 0)); S.step(); S.add('50450', SG, AX_X, (0, 320, 0)); S.step()
    dn = Bp @ unit((0, -0.383, 0.924))                                        # the bent leg, pointing down and out
    M = align((0, 1, 0), dn); m.place(S, M, j + dn * 10)
    m.step(callout=S, mult=1, view=dict(az=-30, el=10))
    return m, [P4, P5, P7, S]

# ---------------------------------------------------------------- bag 2: grass (2x)
def grass():
    m = Model('grass', 'Grass')
    m.add('4032', DG, np.eye(3), (0, 0, 0)); m.add('6064', DG, np.eye(3), (0, -8, 0)); m.step(view=dict(az=-30, el=20, min=80))
    m.add('63965', 'Reddish Brown', np.eye(3), (0, -10, 0)); m.step()
    m.add('3062', 'Black', np.eye(3), (0, -72, 0)); m.add('3062', 'Black', np.eye(3), (0, -96, 0)); m.step()
    m.add('6064', DG, np.eye(3), (0, -100, 0)); m.step()
    S = grip_stem(m, 0, 4, 'grass_stem'); m.place(S, np.eye(3), (0, 8, 0)); m.step(callout=S, mult=1, view=dict(az=-30, el=10))
    return m, [S]

# ---------------------------------------------------------------- bag 2: snapdragons (2 heads, 2 stems)
def frame_spots(y, r=31):
    return [(p + np.array([0, y, 0]), t, rd) for p, t, rd in clip_ring(r, 2, 8, 22.5)]

def snap_head():
    m = Model('snap_head', 'Snapdragon head')
    m.add('85861', DG, np.eye(3), (0, 8, 0)); m.add('75937', SG); m.add('3062', 'Lime', np.eye(3), (0, -24, 0)); m.step(view=dict(az=-30, el=25, min=80))
    m.add('63965', 'Reddish Brown', np.eye(3), (0, 16, 0)); m.step()
    m.add('75937', SG, np.eye(3), (0, -32, 0)); m.step()
    m.add('3062', 'Lime', np.eye(3), (0, -56, 0)); m.step()
    m.add('75937', SG, np.eye(3), (0, -64, 0)); m.step()
    m.add('6538b', 'Lime', AX_Z, (0, -88, 0)); m.step()
    def tier(name):
        s = Model(name, 'Florets')
        s.add('98284', SG); s.add('3062', 'Lime', np.eye(3), (0, -24, 0)); s.step()
        for x, z in ((0, -30), (-30, 0), (0, 30), (30, 0)): s.add('4589', 'Bright Pink', np.eye(3), (x, -40, z))
        s.step(); return s
    T7, T8 = tier('snap_tier'), tier('snap_tier')
    m.place(T7, RY(45), (0, -100, 0)); m.step(callout=T7, mult=1)
    m.place(T8, np.eye(3), (0, -132, 0)); m.step(callout=T7, mult=1)
    B9 = Model('snap_bud', 'Bud')
    B9.add('4733', 'Lime'); B9.add('4589', SG, np.eye(3), (0, -24, 0)); B9.step()
    for d in (X, -X, Z, -Z):
        R = align((0, -1, 0), d, (0, 0, -1), UP); B9.add('49668', 'Yellowish Green', R, put((0, 8, 0), R, d * 10 + np.array([0, 10, 0])))
    B9.step()
    m.place(B9, np.eye(3), (0, -180, 0)); m.step(callout=B9, mult=1)
    F10 = Model('snap_floret', 'Floret'); F10.add('98100', 'Dark Pink'); F10.step(); F10.add('15712', SG, np.eye(3), (0, -12, 0)); F10.step()
    F12 = Model('snap_bell', 'Bell'); F12.add('15469', 'Magenta', np.eye(3), (0, 0, 0)); F12.step(); F12.add('553', 'Magenta', np.eye(3), (0, -4, 0)); F12.add('15712', SG, np.eye(3), (0, -16, 0)); F12.step()
    hinge10, hinge12 = np.array([0, -18, 0.0]), np.array([0, -22, 0.0])
    spots_hi, spots_mid, spots_lo = frame_spots(-64, 36), frame_spots(-32, 36), frame_spots(0, 36)
    for k in range(4): clip_on(m, F10, spots_hi[2 * k], hinge10, up_deg=25, out=True)
    m.step(callout=F10, mult=4)
    for k in range(4): clip_on(m, F10, spots_mid[2 * k + 1], hinge10, up_deg=10, out=True)
    m.step(callout=F10, mult=4)
    for k in range(4): clip_on(m, F12, spots_mid[2 * k], hinge12, up_deg=-10, out=True)
    m.step(callout=F12, mult=4)
    for k in range(4): clip_on(m, F12, spots_lo[2 * k + 1], hinge12, up_deg=-30, out=True)
    m.step(callout=F12, mult=4, view=dict(az=-30, el=15))
    return m, [T7, B9, F10, F12]

def leaf_pair(m, J, side):
    """32039 connectors with the long claw leaves (15362) on the stem."""
    S = Model('snap_leaf', 'Leaf'); S.add('32039', 'Dark Bluish Gray'); S.step()
    S.add('15362', SG, align((0, -1, 0), (1, 0, 0)), (-10, 0, -20)); S.step()
    return S

def snap_stem(curved):
    m = Model('snap_stem_curved' if curved else 'snap_stem_straight', 'Snapdragon stem, ' + ('curved' if curved else 'straight'))
    m.add('26287', DG, AX_Z, (0, 30, 0)); m.add('4519', 'Light Bluish Gray', AX_X, (0, 0, 0)); m.step(view=dict(az=-30, el=20, min=80))
    m.add('32039', 'Dark Bluish Gray', AX_Z, (0, -10, 0)); m.step()
    L = Model('snap_leaf', 'Leaf'); L.add('32039', 'Dark Bluish Gray'); L.step()
    L.add('15362', SG, align((0, -1, 0), (-1, 0.0, 0.0), (0, 0, 1), (0, 0, 1)), (-28, 0, -20)); L.step()
    if curved:
        B = np.column_stack([[0, 0, 1.0], [-1.0, 0, 0], [0, -1.0, 0]]); j1 = np.array([0, -50, 0.0]); bend = B @ unit((0, -0.383, 0.924))
        m.add('32062', RED, align((1, 0, 0), bend), j1 + bend * 30); m.add('32016', DG, B, j1); m.step()
        for k, a in enumerate((20, -60)):
            M = rot(UP, a) @ np.column_stack([[0, 1.0, 0], [0, 0, 1.0], [1.0, 0, 0]]) if False else RY(a); m.place(L, M, (0, 10 + 2 * k, 0))
        m.step(callout=L, mult=2)
        R2 = rot(Z, 22.5) @ B; j2 = j1 + bend * 60; m.add('32016', DG, R2, j2); m.step()
        for J, M in ((j1, B), (j2, R2)):
            pin = M @ X; Mp = frame(up=pin, x=(0, 1, 0)); m.add('24866', 'Green', Mp, put((0, 8, 0), Mp, J + pin * 10))
        m.step()
        top = (j2 + (R2 @ unit((0, -0.383, 0.924))) * 30, R2 @ unit((0, -0.383, 0.924)))
    else:
        m.add('32062', RED, AX_X, (0, -40, 0)); m.add('26287', DG, AX_Z, (0, -50, 0)); m.step()
        m.add('26287', DG, AX_Z, (0, -110, 0)); m.add('32062', RED, AX_X, (0, -80, 0)); m.step()
        for k, a in enumerate((30, -50)): m.place(L, RY(a), (0, -10 + 0 * k, 0))
        m.step(callout=L, mult=2)
        top = (np.array([0, -140, 0.0]), UP)
    S = chain_sub(8)
    for k in range(8): m.place(S, np.eye(3), (0, 60 + 60 * k, 0))
    m.step(callout=S, mult=8, view=dict(az=-30, el=10))
    return m, [L, S], top

def snapdragons(head, curved, c_top, straight, s_top):
    m = Model('snapdragons', 'Snapdragons')
    stems = [(curved, c_top, np.eye(3), -110), (straight, s_top, np.eye(3), 110)]
    heads = []
    for st, (top, d), R, x in stems:
        m.place(st, R, (x, 0, 0)); heads.append((R @ top + np.array([x, 0, 0]), R @ d))
    m.step(view=dict(az=-15, el=10))
    for p, d in heads:
        M = align((0, -1, 0), d, (1, 0, 0), (1, 0, 0)); m.place(head, M, p - M @ np.array([0, 30, 0]))
    m.step(view=dict(az=-15, el=10))
    return m

# ---------------------------------------------------------------- bag 3: large leaves (3x)
def big_leaf():
    m = Model('big_leaf', 'Large leaf')
    R0 = np.eye(3)
    m.add('32803', DG, R0, (0, 0, 0)); m.add('60470b', 'Green', R0, (0, -8, 0)); m.step(view=dict(az=-40, el=35, min=80))
    m.add('3021', DG, R0, (0, -16, -30)); m.step()
    m.add('3034', DG, RY(90), (0, -24, -100)); m.add('3022', 'Lime', R0, (0, -32, -60)); m.add('3022', 'Lime', R0, (0, -32, -120)); m.step()
    m.add('15068', SG, R0, (0, -24, -20)); m.step()
    m.add('45301', SG, R0, (0, -40, -60)); m.step(view=dict(az=-40, el=35))
    for z in (-110, -150): m.add('15573', DG, R0, (0, 16, z))
    m.add('90397', SG, RX(180), (0, 28, -200)); m.step(rotate=True, view=dict(az=-40, el=-35))
    S7 = Model('leaf_mount', 'Mount')
    S7.add('32039', 'Dark Bluish Gray', AX_X); S7.add('32054', 'Black', align((1, 0, 0), (0, 0, 1)), (0, 0, 30)); S7.step()
    S7.add('48336', 'Green', np.eye(3), (0, -18, 0)); S7.step(); S7.add('64225', SG, np.eye(3), (0, -26, 0)); S7.step()
    m.place(S7, RX(180), (0, 16, 30)); m.step(callout=S7, mult=1, rotate=True)
    m.add('50450', SG, align((1, 0, 0), (0, 0, 1)), (0, 16, 350)); m.step(view=dict(az=-60, el=15))
    return m, [S7]

# ---------------------------------------------------------------- bag 3: lavender
def lavender():
    m = Model('lavender', 'Lavender')
    m.add('32054', 'Black', axis_frame((0, -1, 0), 'x'), (0, 10, 0)); m.add('90202', 'Black', np.eye(3), (0, -6, 0)); m.step(view=dict(az=-30, el=30, min=80))
    S2 = Model('lav_holder', 'Holder'); S2.add('60478', 'Black'); S2.add('15712', 'Reddish Brown', np.eye(3), (-10, -8, 0)); S2.step()
    for k in range(4):
        rd = dirdeg(90 * k, 0); M = align((1, 0, 0), rd * 0.6 + UP * 0.8, (0, -1, 0), -rd)
        m.place(S2, M, rd * 26 + np.array([0, -6, 0]) - M @ np.array([30, 2, 0]))
    m.step(callout=S2, mult=4)
    Sp = Model('lav_spike', 'Spike')
    Sp.add('32607', 'Pearl Gold'); Sp.add('39262', 'Pearl Gold', np.eye(3), (0, -8, 0)); Sp.step()
    Sp.add('24855', 'Reddish Brown', np.eye(3), (0, -36, 0)); Sp.add('24855', 'Reddish Brown', RY(90), (0, -70, 0)); Sp.step()
    tips = [np.array([-23.6, -26.5, -13.3]), np.array([21.8, -22, -12.0]), np.array([0, -16.7, 21.1])]
    for base, R in ((np.array([0, -36, 0.0]), np.eye(3)), (np.array([0, -70, 0.0]), RY(90))):
        for tp in tips:
            p = base + R @ tp; d = unit(R @ tp * np.array([1, 0.3, 1]) + UP * 20)
            M = frame(up=d); Sp.add('24866', 'Lavender', M, put((0, 8, 0), M, p))
    Sp.step()
    Sp.add('30374', 'Reddish Brown', np.eye(3), (0, 0, 0)); Sp.step()
    spots = [(0, 0), (22, 0), (-22, 0), (0, 22), (0, -22), (16, 16), (-16, -16), (16, -16), (-16, 16)]
    for k, (x, z) in enumerate(spots):
        lean = unit(np.array([x * 0.012, -1, z * 0.012])); M = align((0, -1, 0), lean, (1, 0, 0), (1, 0, 0)) @ RY(40 * k)
        m.place(Sp, M, np.array([x, -40 - (k % 3) * 18, z]))
    m.step(callout=Sp, mult=9, view=dict(az=-30, el=15, min=90))
    S = grip_stem(m, 0, 4, 'lav_stem'); m.place(S, np.eye(3), (0, 30, 0)); m.step(callout=S, mult=1, view=dict(az=-30, el=10))
    return m, [S2, Sp, S]

# ---------------------------------------------------------------- bag 3: aster
def aster():
    m = Model('aster', 'Aster')
    m.add('67811', DG); m.step(view=dict(az=-30, el=35, min=70))
    for z in (-10, 10): m.add('68013', 'Black', RY(0 if z < 0 else 180), (0, -24, z))
    m.step()
    m.add('75937', SG, np.eye(3), (0, -32, 0)); m.add('18674', 'Dark Purple', np.eye(3), (0, -40, 0)); m.step()
    m.add('4733', 'Lime', np.eye(3), (0, -64, 0)); m.add('24866', 'Lavender', np.eye(3), (0, -72, 0)); m.step()
    for d in (X, -X, Z, -Z):
        R = frame(up=d, x=UP); m.add('32607', 'Medium Lavender', R, put((0, 8, 0), R, d * 10 + np.array([0, -54, 0])))
    m.step()
    F = Model('aster_petal', 'Petal'); F.add('61252', 'Dark Purple'); F.step(); F.add('32607', 'Medium Lavender', np.eye(3), (0, -8, 0)); F.step()
    hinge = np.array([0, 2, -20.0])
    for k in range(4): clip_on(m, F, frame_spots(-32)[2 * k], hinge, up_deg=55)
    m.step(callout=F, mult=4)
    for k in range(4): clip_on(m, F, frame_spots(-32)[2 * k + 1], hinge, up_deg=40)
    m.step(callout=F, mult=4)
    ring = clip_ring(WHEEL_RING_R + 2, WHEEL_RING_Y, 12, 15)
    for k in range(6): clip_on(m, F, ring[2 * k], hinge, up_deg=5)
    m.step(callout=F, mult=6, rotate=True, view=dict(az=-30, el=-40, min=80))
    for k in range(6): clip_on(m, F, ring[2 * k + 1], hinge, up_deg=-15)
    m.step(callout=F, mult=6, view=dict(az=-30, el=25, min=80))
    S = grip_stem(m, 0, 3, 'aster_stem'); m.place(S, np.eye(3), (0, 16, 0)); m.step(callout=S, mult=1, view=dict(az=-30, el=10))
    return m, [F, S]

SECTIONS = []   # (model, title, bag, mult, pdf page, view)

def on_stem(name, stem, top, head, drop):
    """A finished flower for the bouquet: a stem with its head pushed on."""
    m = Model(name, name); m.place(stem); p, d = top
    M = align((0, -1, 0), d, (1, 0, 0), (1, 0, 0)); m.place(head, M, p - M @ np.array([0, drop, 0])); m.step()
    return m

def bouquet(parts):
    """The finished bouquet (box picture): every stem gathered low down and fanned out."""
    m = Model('bouquet', 'Flower Bouquet')
    B = np.array([0, 640, 0.0])
    for name, (mod, lean, spin, dy, *rest) in parts.items():
        pre = rest[0] if rest else np.eye(3); piv = rest[1] if len(rest) > 1 else B
        M = RY(spin) @ RZ(lean * 1.5) @ pre; m.place(mod, M, B + np.array([0, dy, 0]) - M @ piv)
    m.step(view=dict(az=-10, el=8))
    return m

def build():
    """Every model of the set: main builds first, then their sub-builds."""
    d = daisy(); rh = rose_head(); rc = rose_stem_curved(); rs = rose_stem_straight()
    ro = roses(rh[0], rc[0], rc[2], rs[0], rs[2])
    po = poppy(); gr = grass(); sh = snap_head(); scs = snap_stem(True); sss = snap_stem(False)
    sn = snapdragons(sh[0], scs[0], scs[2], sss[0], sss[2])
    lf = big_leaf(); lv = lavender(); ast = aster()
    rose_c = on_stem('rose_on_curved', rc[0], rc[2], rh[0], 70); rose_s = on_stem('rose_on_straight', rs[0], rs[2], rh[0], 70)
    snap_c = on_stem('snap_on_curved', scs[0], scs[2], sh[0], 30); snap_s = on_stem('snap_on_straight', sss[0], sss[2], sh[0], 30)
    LP = np.array([0, 16, 650.0])
    fin = bouquet({'rose1': (rose_c, -6, 200, -120), 'rose2': (rose_s, 3, 0, -150), 'rose3': (rose_c, 8, 20, -110),
                   'daisy1': (d[0], -16, 30, -40), 'daisy2': (d[0], 15, 160, -30), 'poppy': (po[0], 12, 70, -60, RZ(-22.5), np.array([0, 54, 0.0]) + np.array([-0.383, 0.924, 0]) * 650),
                   'grass1': (gr[0], -22, 120, 20), 'grass2': (gr[0], 21, -60, 20), 'snap1': (snap_c, -9, 150, -90), 'snap2': (snap_s, 6, -40, -100),
                   'leaf1': (lf[0], -26, 80, 30, RX(-90), LP), 'leaf2': (lf[0], 27, 250, 30, RX(-90), LP), 'leaf3': (lf[0], 2, 170, 0, RX(-90), LP),
                   'lav': (lv[0], -10, -100, -80), 'aster': (ast[0], 10, 140, -70)})
    built = [d, rh, rc[:2], rs[:2], (ro, []), po, gr, sh, scs[:2], sss[:2], (sn, []), lf, lv, ast, (fin, [])]
    PAGES = {'daisy': [15, 15, 16, 16, 17, 18], 'rose_head': [19, 20, 20, 21, 21, 22, 22, 23, 24, 25],
             'rose_stem_curved': [26, 27, 27, 27, 28, 28, 29, 30], 'rose_stem_straight': [31, 31, 32, 32, 33, 34], 'roses': [35, 35],
             'poppy': [37, 37, 38, 38, 39, 39, 40, 40, 41], 'grass': [43, 44, 44, 45, 46],
             'snap_head': [48, 49, 49, 49, 50, 50, 51, 51, 52, 52, 53, 53, 54], 'snap_stem_curved': [55, 55, 56, 56, 57, 57, 58],
             'snap_stem_straight': [59, 59, 60, 60, 61, 61], 'snapdragons': [62, 62], 'lavender': [64, 64, 65, 66],
             'big_leaf': [68, 68, 69, 69, 70, 71, 72, 73], 'aster': [74, 75, 75, 75, 76, 77, 77, 78, 79, 80]}
    for m, _ in built:
        for st, pg in zip(m.steps, PAGES.get(m.name, [])): st['meta']['pdf'] = pg
    models, subs, seen = [], [], set()
    for m, ss in built:
        models.append(m)
        for s in ss:
            if s.name not in seen: seen.add(s.name); subs.append(s)
    return models, subs

if __name__ == '__main__':
    from pack import pack, part_names
    models, subs = build()
    out = os.path.join(os.path.dirname(HERE), 'docs', 'sets', '10280', 'data', 'set.js')
    pack(models + subs, out, extra={'set': '10280', 'names': part_names()})
    for m in models: print(m.name, len(m.parts), 'pieces', len(m.steps), 'steps')
