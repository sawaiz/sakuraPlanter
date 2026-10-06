"""Sakura Planter: place every LEGO part from 10280 + 40725 on the PLA trunk/planter.

World frame: millimetres, Z up, soil-plate top at z=0 (same as pla.py).
Output: placements.json (one row per LEGO part) + usage.json (what was used, what wasn't, why).
"""
import json, math, sys, os
import numpy as np

OUT = sys.argv[1]
A = json.load(open(os.path.join(sys.argv[2], 'anchors.json')))
rng = np.random.default_rng(20261006)

# ------------------------------------------------------------------ inventory (BrickLink, no spares)
INV = """
23443|Black|8;3062|Black|4;68013|Black|2;60478|Black|4;2817|Black|3;10197|Black|2;32054|Black|6;90202|Black|6;
4589|Bright Pink|16;32039|Dark Bluish Gray|4;98088|Dark Green|3;6064|Dark Green|4;3021|Dark Green|3;3034|Dark Green|3;
15573|Dark Green|6;85861|Dark Green|6;4032|Dark Green|2;32803|Dark Green|3;32016|Dark Green|7;26287|Dark Green|65;
67811|Dark Green|7;98100|Dark Pink|16;61252|Dark Purple|20;18674|Dark Purple|1;96874|Dark Turquoise|1;3941|Green|4;
60470b|Green|3;48336|Green|3;24866|Green|2;4032|Green|3;24866|Lavender|55;4519|Light Bluish Gray|5;11476|Light Nougat|24;
3069|Light Nougat|12;98835|Light Nougat|12;93604|Light Nougat|12;4733|Lime|3;3062|Lime|8;3022|Lime|6;6538b|Lime|2;
553|Magenta|16;15469|Magenta|16;32607|Medium Lavender|34;2540|Orange|4;50950|Orange|4;93604|Orange|4;64225|Orange|2;
39262|Pearl Gold|9;32607|Pearl Gold|9;20482|Pearl Gold|4;32062|Red|57;30374|Reddish Brown|12;63965|Reddish Brown|6;
13564|Reddish Brown|4;24855|Reddish Brown|22;33183|Reddish Brown|2;15712|Reddish Brown|4;4589|Sand Green|2;
15362|Sand Green|4;90397|Sand Green|3;75937|Sand Green|7;98284|Sand Green|4;15068|Sand Green|3;50450|Sand Green|10;
15712|Sand Green|32;64225|Sand Green|3;45301|Sand Green|3;2566|Tan|6;99207|Tan|12;87580|Tan|3;47458|Tan|12;
4733|White|3;49668|White|12;24866|White|3;35480|White|48;11090|Yellow|4;67329|Yellow|2;3022|Yellow|1;11476|Yellow|4;
14769|Yellow|6;49668|Yellowish Green|8;
32062|Black|28;39262|Bright Pink|37;24866|Bright Pink|37;15470|Bright Pink|6;89678|Dark Bluish Gray|12;24866|Dark Pink|37;
65578|Dark Red|44;24866|Dark Red|26;4519|Light Bluish Gray|4;32607|Lime|32;48729b|Reddish Brown|12;78258|Reddish Brown|16;
23443|Reddish Brown|12;4733|Reddish Brown|14;4589|Reddish Brown|2;68211|Reddish Brown|12;85861|Reddish Brown|24;
32034|Reddish Brown|12;6538b|Reddish Brown|20;24122|Reddish Brown|4;39262|White|37;15470|White|6
"""
pool = {}
for tok in INV.replace('\n', '').split(';'):
    p, c, n = tok.split('|'); pool[(p, c)] = pool.get((p, c), 0) + int(n)
TOTAL = sum(pool.values())
assert TOTAL == 1194, TOTAL
LDCOL = {'Black': 0, 'Bright Pink': 29, 'Dark Bluish Gray': 72, 'Dark Green': 288, 'Dark Pink': 5, 'Dark Purple': 85,
         'Dark Turquoise': 3, 'Green': 2, 'Lavender': 31, 'Light Bluish Gray': 71, 'Light Nougat': 78, 'Lime': 27,
         'Magenta': 26, 'Medium Lavender': 30, 'Orange': 25, 'Pearl Gold': 297, 'Red': 4, 'Reddish Brown': 70,
         'Sand Green': 378, 'Tan': 19, 'White': 15, 'Yellow': 14, 'Yellowish Green': 326, 'Dark Red': 320}
BL_ID = {'4589': '4589b', '98088': '98088pb05', '6538b': '6538c'}

placed = []
def take(p, c, n=1):
    k = (p, c)
    if pool.get(k, 0) < n:
        raise RuntimeError(f'out of {p} {c}: need {n}, have {pool.get(k, 0)}')
    pool[k] -= n

# ------------------------------------------------------------------ orientation helpers
def unit(v):
    v = np.asarray(v, float); n = np.linalg.norm(v); return v / n if n > 1e-9 else v
def perp(v):
    v = unit(v); a = np.array([0, 0, 1.0]) if abs(v[2]) < 0.9 else np.array([1.0, 0, 0])
    return unit(np.cross(v, a))
def orient(la, wa, lb, wb):
    """Rotation (local LDraw coords -> world mm frame) with la->wa exactly and lb->wb as close as possible."""
    la, wa = unit(la), unit(wa)
    lb = unit(np.asarray(lb, float) - la * (la @ lb)); wb = np.asarray(wb, float) - wa * (wa @ wb)
    if np.linalg.norm(wb) < 1e-6: wb = perp(wa)
    wb = unit(wb)
    L = np.column_stack([la, lb, np.cross(la, lb)]); W = np.column_stack([wa, wb, np.cross(wa, wb)])
    return W @ L.T
def rot_about(axis, ang):
    axis = unit(axis); K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K
UP_L = np.array([0, -1.0, 0])      # LDraw local 'up'
LDU = 0.4                           # mm

def put(p, c, R, at, attach=(0, 0, 0), group='', role=''):
    """Place part p (LDraw id) colour c so that its local point `attach` (LDU) sits at world point `at` (mm)."""
    take(p, c)
    origin = np.asarray(at, float) - R @ (np.asarray(attach, float) * LDU)
    placed.append({'part': p, 'colour': c, 'R': R.round(5).tolist(), 'p': origin.round(3).tolist(), 'group': group, 'role': role})
    return origin

def up_part(p, c, at, u, spin=0.0, attach=(0, 8, 0), xhint=None, **kw):
    """Plates/bricks/flowers: local up (-y) along u, bottom (attach) at `at`."""
    xh = perp(u) if xhint is None else xhint
    R = rot_about(u, spin) @ orient(UP_L, u, [1, 0, 0], xh)
    return put(p, c, R, at, attach, **kw), R

# ------------------------------------------------------------------ anchors from the PLA design
holes = {h['label']: h for h in A['axle_holes']}
pins = {h['label']: h for h in A['pin_holes']}
def mouth(h): return np.array(h['origin']), np.array(h['dir'])   # dir points INTO the PLA
def hx(h): return np.array(h['x'])                                 # direction of one arm of the hole's cross
def axle_R(axis, arm): return orient([1, 0, 0], axis, [0, 1, 0], arm)      # 32062/4519/50450: arms on local y,z
def conn_R(axis, arm): return orient([0, 0, 1], axis, [1, 0, 0], arm)      # 26287/6538b/32034: cross hole arms on local x,y

# =================================================================== 1. STRUCTURE
# 4 sand-green 32L axles: planter floor -> through soil plate -> up the trunk core (hidden anchors)
# each long axle stands in a dark-green 3L connector that sits on a printed cross peg on the planter floor
# (the connector's lower end takes the peg, its upper end takes the bottom 8 mm of the axle)
for lab in [f'floor-trunk-{i}' for i in range(4)] + [f'floor-daisy-{k}' for k in range(6)]:
    o, d = mouth(holes[lab]); up = -d
    put('26287', 'Dark Green', conn_R(up, hx(holes[lab])), o + up * 12, group='Structure', role='Hidden socket for a 32L axle (on a printed floor peg)')
for i in range(4):
    o, d = mouth(holes[f'floor-trunk-{i}']); up = -d
    bottom = o + up * 16.0
    put('50450', 'Sand Green', axle_R(up, hx(holes[f'floor-trunk-{i}'])), bottom + up * 128.0, group='Structure', role='Hidden anchor: planter floor to trunk core')
# arm joints: 3L friction pin + black 2L axle per arm; one more pin locks the trunk boss
for i in range(5):
    o, d = mouth(pins[f'stub-{i}-pin'])
    # 3L pin with stop bush: the bush end (local -x, 8 mm) sits in a snug pocket in the trunk stub,
    # the 2L pin end goes into the branch
    R = orient([-1, 0, 0], d, [0, 1, 0], perp(d))
    put('32054', 'Black', R, o - d * 4.0, group='Structure', role='Branch joint pin (trunk to branch)')
    o, d = mouth(holes[f'stub-{i}-axle'])
    R = axle_R(d, hx(holes[f'stub-{i}-axle']))
    put('32062', 'Black', R, o, group='Structure', role='Branch joint anti-twist axle')
# sixth 3L pin: through the trunk-top hole as the crown twig's root
# (placed in the canopy section)

# =================================================================== 2. DAISIES on the 32L axles (their original 10280 stems)
daisies = []
for k, da in enumerate(A['daisy_axes']):
    o, d = mouth(holes[f'floor-daisy-{k}'])
    axis = -d
    bottom = o + axis * 16.0
    R = axle_R(axis, hx(holes[f'floor-daisy-{k}']))
    put('50450', 'Sand Green', R, bottom + axis * 128.0, group='Daisies', role='Daisy stem (original 10280 role)')
    top = bottom + axis * 256.0
    daisies.append((top, axis, da['az']))     # head is coaxial: the axle end sits in the head's pin hole
for k, (top, u, az) in enumerate(daisies):
    g = 'Daisies'
    for j in range(2):                       # tan brackets as sepals under the head
        rad = unit(rot_about(u, j * math.pi + 0.8) @ perp(u))
        R = orient([0, 0, -1], unit(rad + u * 0.3), UP_L, u)
        put('99207', 'Tan', R, top - u * 3 + rad * 7, attach=(0, 8, 0), group=g, role='Sepal (bracket)')
    if k < 4:
        up_part('98284', 'Sand Green', top, u, group=g, role='Green calyx')
    else:
        up_part('87580', 'Tan', top, u, group=g, role='Head base')
    if k == 0:
        up_part('87580', 'Tan', top + u * 3.2, u, group=g, role='Head base')
    up_part('2566', 'Tan', top + u * 5, u, attach=(0, 40, 0), group=g, role='Daisy centre (original 10280 role)')
    up_part('14769', 'Yellow', top + u * 21, u, attach=(0, 8, 0), group=g, role='Yellow disc')
    for j in range(8):
        a = j * math.pi / 4 + (k * 0.2)
        rad = unit(rot_about(u, a) @ perp(u))
        tilt = unit(rad * 0.97 + u * 0.24)
        p = top + u * 15 + rad * 14
        R = orient([1, 0, 0], tilt, UP_L, unit(u - tilt * (tilt @ u)))
        put('35480', 'White', R, p, attach=(0, 8, 0), group=g, role='Petal (original 10280 role)')
    for j in range(2):
        a = j * math.pi + 0.4
        rad = unit(rot_about(u, a) @ perp(u))
        R = orient([0, 0, -1], rad, UP_L, u)
        put('49668', 'White', R, top + u * 12 + rad * 8, attach=(0, 8, 0), group=g, role='Petal infill')
    for j in range(2):
        a = j * math.pi + 1.2
        rad = unit(rot_about(u, a) @ perp(u))
        R = orient([0, 0, 1], -rad, UP_L, u)
        put('47458', 'Tan', R, top + u * 2 + rad * 7, attach=(0, 8, 0), group=g, role='Underside of head')
    if k < 3:
        side = unit(rot_about(u, 2.2) @ perp(u))
        up_part('4733', 'White', top - u * 40 + side * 6, side, attach=(0, 24, 0), group=g, role='Side bud base')
        up_part('24866', 'White', top - u * 40 + side * 16, side, group=g, role='Side bud')
    if k < 2:
        side = unit(rot_about(u, -2.0) @ perp(u))
        up_part('24866', 'Green', top - u * 70 + side * 5, side, group=g, role='Green bud on stem')

# =================================================================== 3. FLOWER STEMS from the soil plate
stems = sorted([h for h in A['axle_holes'] if h['label'].startswith('soil-stem-')], key=lambda h: int(h['label'].split('-')[-1]))
stem_xy = [np.array(h['origin']) for h in stems]
# assign flower types to stem holes: inner ring (r=40) = taller spikes + bushes, outer ring (r=70) = roses, poppies...
inner = [i for i, p in enumerate(stem_xy) if np.hypot(p[0], p[1]) < 55]
outer = [i for i, p in enumerate(stem_xy) if np.hypot(p[0], p[1]) >= 55]
plan = {}
inner_types = ['bush', 'lavender', 'snapdragon', 'bush', 'lavender', 'bush', 'snapdragon', 'lavender', 'bush']
outer_types = ['bush', 'foliage', 'poppy', 'rose', 'aster', 'poppy', 'rose', 'foliage', 'rose', 'lavender']   # bush under the lowest branch
for i, t in zip(inner, inner_types): plan[i] = t
for i, t in zip(outer, outer_types): plan[i] = t
need = {'rose': 3, 'poppy': 2, 'aster': 1, 'lavender': 3, 'snapdragon': 2, 'bush': 4, 'foliage': 2}
have = {}
for t in plan.values(): have[t] = have.get(t, 0) + 1
# rebalance to exactly the needed counts
extra = [i for i, t in plan.items() if have[t] > need.get(t, 0)]
for i in list(plan):
    t = plan[i]
    if have[t] > need[t]:
        for t2 in need:
            if have.get(t2, 0) < need[t2]:
                have[t] -= 1; have[t2] = have.get(t2, 0) + 1; plan[i] = t2; break
assert all(have.get(t, 0) == need[t] for t in need), have
HEIGHT = {'rose': 3, 'poppy': 3, 'aster': 2, 'lavender': 3, 'snapdragon': 2, 'bush': 1, 'foliage': 2}  # connector count target

# distribute the 65 dark-green 3L connectors: start from targets, then add to the tallest stems
order = sorted([i for i in plan if plan[i] in ('rose', 'poppy', 'aster', 'foliage')], key=lambda i: -HEIGHT[plan[i]])   # extra height only on the outer ring, clear of the branches
nconn = {i: HEIGHT[plan[i]] for i in plan}
left = pool[('26287', 'Dark Green')] - sum(nconn.values())
j = 0
while left > 0:
    i = order[j % len(order)]
    if plan[i] not in ('bush',):
        nconn[i] += 1; left -= 1
    j += 1
while left < 0:
    i = order[j % len(order)]
    if nconn[i] > 1: nconn[i] -= 1; left += 1
    j += 1
bend = sorted([i for i in plan if plan[i] in ('rose', 'poppy', 'aster', 'foliage')], key=lambda i: plan[i] == 'foliage')[:7]   # 32016 angled connectors
# keep every stem top at least 22 mm from the printed branches: shorten offenders, give the connector to a clear stem
import trimesh as _tm
_arm_pts = []
for _j, _am in enumerate(A['arms']):
    _m = _tm.load(os.path.join(sys.argv[2], f'sakura_branch_{_j + 1}.stl')); _W = np.array(_am['world'])
    _arm_pts.append(_m.vertices @ _W[:, :3].T + _W[:, 3])
_arm_pts = np.concatenate(_arm_pts)
def _top(i):
    o = np.array(stems[i]['origin']); up = -np.array(stems[i]['dir']); out = unit(np.array([o[0], o[1], 0.0]))
    p = o + up * 24 * nconn[i]
    if i in bend: p = p + up * 12 + unit(up + out * 0.41) * 12
    return p + unit(up + out * 0.3) * 30          # rough head extent
def _clear(i): return np.min(np.linalg.norm(_arm_pts - _top(i), axis=1))
for _ in range(40):
    bad_i = [i for i in plan if _clear(i) < 40 and nconn[i] > 1]
    if not bad_i: break
    i = bad_i[0]; nconn[i] -= 1
    for j in sorted(plan, key=lambda j: -_clear(j)):
        if j != i and plan[j] != 'bush':
            nconn[j] += 1
            if _clear(j) >= 40: break
            nconn[j] -= 1
    else:
        nconn[i] += 1; break
axle_queue = ['Red'] * 57 + ['Black'] * 28
def next_axle():
    return axle_queue.pop(0)
heads = {}; stem_len = {}
for i in plan:
    h = stems[i]; o, d = mouth(h); up = -d
    out = unit(np.array([o[0], o[1], 0.0]))
    g = 'Stems'
    # first connector slides onto the printed axle peg on the soil plate (peg arms along world X/Y)
    p = o.copy(); t = up.copy(); armref = hx(h)      # peg arm points radially (= out)
    for k in range(nconn[i]):
        if k > 0:
            R = axle_R(t, armref)
            put('32062', next_axle(), R, p, group=g, role='Hidden joint axle')
        R = conn_R(t, armref)
        put('26287', 'Dark Green', R, p + t * 12, group=g, role='Flower stem (original 10280 role)')
        p = p + t * 24
        # (connectors joined by axles are coaxial: the stem stays straight until the angled connector)
    if i in bend:
        put('32062', next_axle(), axle_R(t, armref), p, group=g, role='Hidden joint axle')
        t2 = unit(rot_about(np.cross(t, out), -math.radians(22.5)) @ t)
        # straight end (local -z) down onto the axle, angled end up and bending outward (local -y)
        R = orient([0, 0, 1], t, [0, -1, 0], out)
        put('32016', 'Dark Green', R, p + t * 12, group=g, role='Stem bend (22.5 deg)')
        p = p + t * 12 + t2 * 12; t = t2
    heads[i] = (p, t, out); stem_len[i] = float(np.linalg.norm(p - o))

# --------------------------------------------------------------- 3a. ROSES (light nougat) x3
roses = [i for i in plan if plan[i] == 'rose']
for n, i in enumerate(roses):
    p, t, out = heads[i]; g = 'Roses'
    R = orient([1, 0, 0], t, [0, 1, 0], out)
    put('32062', next_axle(), R, p, group=g, role='Head axle')
    up_part('67811', 'Dark Green', p + t * 2, t, attach=(0, 16, 0), group=g, role='Rose centre (original 10280 role)')
    up_part('67811', 'Dark Green', p + t * 12, t, spin=0.4, attach=(0, 16, 0), group=g, role='Rose centre (original 10280 role)')
    for k in range(2):
        up_part('90202', 'Black', p + t * (23.2 + 8 * k), t, spin=k * 0.78, attach=(0, 10, 0), group=g, role='Petal clip hub')
    c = p + t * 26
    for k in range(4):
        a = k * math.pi / 2
        rad = unit(rot_about(t, a) @ perp(t))
        R = orient([0, 0, -1], unit(rad * 0.75 + t * 0.66), UP_L, unit(t - rad * 0.5))
        put('98835', 'Light Nougat', R, c + rad * 16 - t * 2, attach=(0, 12, -20), group=g, role='Outer petal')
        rad2 = unit(rot_about(t, a + math.pi / 4) @ perp(t))
        R = orient([0, 0, -1], unit(rad2 * 0.45 + t * 0.9), UP_L, unit(t - rad2 * 0.8))
        put('93604', 'Light Nougat', R, c + rad2 * 10 + t * 8, attach=(0, 0, -20), group=g, role='Middle petal')
        R = orient([0, 0, -1], unit(rad * 0.2 + t), UP_L, unit(-rad))
        put('3069', 'Light Nougat', R, c + rad * 3.5 + t * 20, attach=(0, 4, 0), group=g, role='Inner bud')
    for k in range(8):
        a = k * math.pi / 4 + 0.2
        rad = unit(rot_about(t, a) @ perp(t))
        R = orient([0, 0, -1], unit(rad * 0.3 + t), UP_L, unit(-rad))
        put('11476', 'Light Nougat', R, c + rad * 7 + t * 14, attach=(0, 4, 0), group=g, role='Inner petal')
    # pteranodon wing as the rose's leaf, near the base of the head
    leaf_dir = unit(out + np.array([0, 0, 0.25]))
    R = orient([1, 0, 0], leaf_dir, UP_L, [0, 0, 1])
    put('98088', 'Dark Green', R, p - t * 30 + leaf_dir * 4, attach=(0, 0, 0), group=g, role='Rose leaf (original 10280 role)')

# --------------------------------------------------------------- 3b. ASTER x1 (medium lavender dome)
i = [i for i in plan if plan[i] == 'aster'][0]
p, t, out = heads[i]; g = 'Aster'
R = orient([1, 0, 0], t, [0, 1, 0], out)
put('32062', next_axle(), R, p, group=g, role='Head axle')
up_part('67811', 'Dark Green', p + t * 2, t, attach=(0, 16, 0), group=g, role='Head base')
for k in range(2):
    R = orient([0, -1, 0], t, [1, 0, 0], perp(t))
    put('10197', 'Black', R, p + t * (10 + 6 * k), group=g, role='Core hub')
    up_part('68013', 'Black', p + t * (12 + 4 * k), t, spin=k * math.pi, attach=(0, 24, 0), group=g, role='Core')
for k in range(4):
    up_part('3062', 'Black', p + t * (14 + 6 * k), t, attach=(0, 24, 0), group=g, role='Core spacer')
c = p + t * 22
R0 = 21.0
for k in range(34):                      # Fibonacci hemisphere
    z = 1 - (k + 0.5) / 34 * 0.92
    rr = math.sqrt(max(0, 1 - z * z)); a = k * 2.39996
    n_ = unit(rot_about(t, a) @ perp(t) * rr + t * z)
    up_part('32607', 'Medium Lavender', c + n_ * R0, n_, spin=a, group=g, role='Aster petals (original 10280 role)')
for k in range(20):
    z = 0.15 - (k % 2) * 0.12; a = k * 2 * math.pi / 20
    n_ = unit(rot_about(t, a) @ perp(t) * 0.98 + t * z)
    R = orient([0, 0, -1], n_, UP_L, t)
    put('61252', 'Dark Purple', R, c + n_ * (R0 - 5), attach=(0, 4, 0), group=g, role='Petal clips (original 10280 role)')
up_part('18674', 'Dark Purple', c + t * (R0 + 1), t, group=g, role='Centre tile')

# --------------------------------------------------------------- 3c. POPPIES x2 (orange, yellow centre, black stamens)
for n, i in enumerate([i for i in plan if plan[i] == 'poppy']):
    p, t, out = heads[i]; g = 'Poppies'
    R = orient([1, 0, 0], t, [0, 1, 0], out)
    put('32062', next_axle(), R, p, group=g, role='Head axle')
    up_part('2817', 'Black', p + t * 2, t, group=g, role='Head base plate')
    if n == 0: up_part('2817', 'Black', p + t * 5.2, t, spin=0.78, group=g, role='Head base plate')
    if n == 0: up_part('3022', 'Yellow', p + t * 8.4, t, group=g, role='Centre plate')
    up_part('67329', 'Yellow', p + t * 9, t, attach=(0, 40, -2), group=g, role='Seed head (original 10280 role)')
    for k in range(2):
        rad = unit(rot_about(t, k * math.pi) @ perp(t))
        R = orient([0, 0, -1], unit(rad + t * 0.9), UP_L, unit(t - rad))
        put('93604', 'Orange', R, p + t * 6 + rad * 12, attach=(0, 0, -20), group=g, role='Petal (original 10280 role)')
        rad2 = unit(rot_about(t, k * math.pi + math.pi / 2) @ perp(t))
        R = orient([0, 0, -1], unit(rad2 + t * 1.1), UP_L, unit(t - rad2))
        put('50950', 'Orange', R, p + t * 4 + rad2 * 10, attach=(0, 12, 0), group=g, role='Petal')
        R = orient([0, 0, -1], rad2, UP_L, t)
        put('2540', 'Orange', R, p + t * 1 + rad2 * 6, attach=(0, 4, 0), group=g, role='Petal mount')
        R = orient([0, 0, -1], rad, UP_L, t)
        put('60478', 'Black', R, p + t * 3 + rad * 5, attach=(0, 4, 0), group=g, role='Petal mount')
        up_part('11090', 'Yellow', p + t * 22 + rad * 4, unit(t + rad * 0.5), attach=(0, 30, 0), group=g, role='Stamen')
        R = orient([0, 0, -1], rad2, UP_L, t)
        put('11476', 'Yellow', R, p + t * 14 + rad2 * 6, attach=(0, 4, 0), group=g, role='Centre detail')
    rad = unit(rot_about(t, math.pi / 4) @ perp(t))
    R = orient([0, 0, -1], unit(rad * 1.2 + t), UP_L, unit(t - rad))
    put('64225', 'Orange', R, p + t * 10 + rad * 12, attach=(0, 12, -10), group=g, role='Back petal (original 10280 role)')
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        rad = unit(rot_about(t, a) @ perp(t))
        up_part('23443', 'Black', p + t * 18 + rad * 4, unit(t + rad * 0.6), attach=(0, 6, 0), group=g, role='Dark stamens')

# --------------------------------------------------------------- 3d. LAVENDER x3 (10280's lavender: three-stem bunches)
lav_parts = {'24855': 18, '24866': 55, '39262': 9, '32607': 9, '20482': 4, '30374': 12, '63965': 6, '15712': 4}
for n, i in enumerate([i for i in plan if plan[i] == 'lavender']):
    p, t, out = heads[i]; g = 'Lavender'
    R = orient([1, 0, 0], t, [0, 1, 0], out)
    put('32062', next_axle(), R, p, group=g, role='Head axle')
    up_part('6538b', 'Reddish Brown', p, t, attach=(0, 0, 0), group=g, role='Stalk adapter') if False else None
    # main stalk: two 6L bars end to end
    q = p + t * 8.0                    # stalk starts above the head axle
    for k in range(2):
        R = orient(UP_L, t, [1, 0, 0], perp(t))
        put('63965', 'Reddish Brown', R, q, attach=(0, 18, 0), group=g, role='Lavender stalk')
        q = q + t * 48
    if n < 4:
        up_part('20482', 'Pearl Gold', p + t * 47, t, attach=(0, 8, 0), group=g, role='Stalk joint')
    if n == 0:
        up_part('20482', 'Pearl Gold', p + t * 95, t, attach=(0, 8, 0), group=g, role='Stalk tip')
    # 4 side stalks (4L bars) + 6 bunches of three
    for k in range(4):
        inward = -unit(np.array([p[0], p[1], 0.0]))          # spread the side stalks over the outward half, away from the trunk
        phi = math.radians(90 + k * 60)
        d = np.array([inward[0] * math.cos(phi) - inward[1] * math.sin(phi), inward[0] * math.sin(phi) + inward[1] * math.cos(phi), 0.0])
        rad = unit(d - t * np.dot(d, t))
        sd = unit(t * 0.75 + rad * 0.65)
        base = p + t * (30 + k * 15) + rad * 4.5
        R = orient(UP_L, sd, [1, 0, 0], perp(sd))
        put('30374', 'Reddish Brown', R, base, attach=(0, 80, 0), group=g, role='Side stalk')
        if k < 4 and pool[('15712', 'Reddish Brown')] > 0 and n < 2 and k < 2:
            R = orient([0, 0, -1], rad, UP_L, t)
            put('15712', 'Reddish Brown', R, base, attach=(0, 4, 0), group=g, role='Side stalk clip')
    for k in range(6):
        a = k * 2.1 + n
        rad = unit(rot_about(t, a) @ perp(t))
        bt = unit(t * 0.9 + rad * 0.45)
        base = p + t * (40 + k * 9) + rad * 6
        R = rot_about(bt, a) @ orient(UP_L, bt, [1, 0, 0], perp(bt))
        put('24855', 'Reddish Brown', R, base, attach=(0, 20, 0), group=g, role='Lavender bunch (original 10280 role)')
        tips = [np.array([-24.3, -26.0, -14.3]), np.array([22.6, -21.3, -12.0]), np.array([0.0, -15.7, 22.0])]
        org = placed[-1]['p']
        for tp in tips:
            wp = np.array(org) + R @ (tp * LDU)
            up_part('24866', 'Lavender', wp, unit(bt + R @ unit(tp) * 0.3), group=g, role='Lavender florets (original 10280 role)')
        if k < 3 and pool[('39262', 'Pearl Gold')] > 0:
            up_part('39262', 'Pearl Gold', base - bt * 4, bt, attach=(0, 8, 0), group=g, role='Gold calyx')
            up_part('32607', 'Pearl Gold', base - bt * 9, unit(rad + t * 0.3), spin=a, group=g, role='Gold leaf')
    if n == 0:
        up_part('24866', 'Lavender', p + t * 97, t, group=g, role='Top floret')
# use any leftover lavender-group parts at the third spike's tip
while pool[('15712', 'Reddish Brown')] > 0:
    p, t, out = heads[[i for i in plan if plan[i] == 'lavender'][2]]
    R = orient([0, 0, -1], out, UP_L, t)
    put('15712', 'Reddish Brown', R, p + t * (20 + 6 * pool[('15712', 'Reddish Brown')]), attach=(0, 4, 0), group='Lavender', role='Side stalk clip')
while pool[('20482', 'Pearl Gold')] > 0:
    p, t, out = heads[[i for i in plan if plan[i] == 'lavender'][1 + pool[('20482', 'Pearl Gold')] % 2]]
    up_part('20482', 'Pearl Gold', p + t * 95, t, attach=(0, 8, 0), group='Lavender', role='Stalk tip')

# --------------------------------------------------------------- 3e. SNAPDRAGONS x2 (pink spikes)
snaps = [i for i in plan if plan[i] == 'snapdragon']
for n, i in enumerate(snaps):
    p, t, out = heads[i]; g = 'Snapdragons'
    R = orient([1, 0, 0], t, [0, 1, 0], out)
    put('32062', next_axle(), R, p, group=g, role='Head axle')
    R = conn_R(t, out)
    put('6538b', 'Lime', R, p + t * 8, group=g, role='Spike adapter')
    # a solid core column: 2 green round bricks, then whorl plates separated by lime round bricks, lime tip
    z = 16.0
    for k in range(2):
        up_part('3941', 'Green', p + t * z, t, attach=(0, 24, 0), group=g, role='Spike core'); z += 9.6
    nf = 4 if n == 0 else 3
    for k in range(nf):
        lvl = p + t * z
        up_part('75937', 'Sand Green', lvl, t, spin=k * 0.4, group=g, role='Blossom whorl (original 10280 role)'); z += 3.2
        for m in range(4):
            if pool[('553', 'Magenta')] == 0: break
            a = m * math.pi / 2 + k * 0.6
            rad = unit(rot_about(t, a) @ perp(t))
            bd = unit(rad + t * 0.5)
            up_part('15469', 'Magenta', lvl + rad * 9 + t * 2, bd, spin=a, group=g, role='Blossom lip')
            up_part('553', 'Magenta', lvl + rad * 11 + t * 5, bd, attach=(0, 24, 0), group=g, role='Blossom (original 10280 role)')
            up_part('98100', 'Dark Pink', lvl + rad * 6 + t * 7, unit(rad * 0.4 + t), attach=(0, 24, 0), group=g, role='Blossom throat')
            up_part('4589', 'Bright Pink', lvl + rad * 7 + t * 12, unit(rad * 0.6 + t), attach=(0, 24, 0), group=g, role='Bud')
        if k < nf - 1:
            up_part('3062', 'Lime', p + t * z, t, attach=(0, 24, 0), group=g, role='Spike core'); z += 9.6
    ntip = 2 if n == 0 else 1
    for k in range(ntip):
        up_part('3062', 'Lime', p + t * z, t, attach=(0, 24, 0), group=g, role='Green tip buds'); z += 9.6
    for k in range(4):
        rad = unit(rot_about(t, k * math.pi / 2) @ perp(t))
        R = orient([0, 0, -1], unit(rad + t * 0.6), UP_L, t)
        put('49668', 'Yellowish Green', R, p + t * (z - 6.0 - 3.0 * (k % 2)) + rad * 4.2, attach=(0, 4, 0), group=g, role='Tip sepals')
    up_part('4589', 'Sand Green', p + t * z, t, attach=(0, 24, 0), group=g, role='Spike tip')
# leftover snapdragon pieces go on the second spike's lower whorl
i = snaps[1]; p, t, out = heads[i]
while pool[('553', 'Magenta')] > 0:
    m = pool[('553', 'Magenta')]
    a = m * 1.3; rad = unit(rot_about(t, a) @ perp(t)); bd = unit(rad + t * 0.4); lvl = p + t * (30 + 4 * m)
    up_part('15469', 'Magenta', lvl + rad * 9, bd, spin=a, group='Snapdragons', role='Blossom lip')
    up_part('553', 'Magenta', lvl + rad * 11 + t * 3, bd, attach=(0, 24, 0), group='Snapdragons', role='Blossom (original 10280 role)')
    up_part('98100', 'Dark Pink', lvl + rad * 6 + t * 5, unit(rad * 0.4 + t), attach=(0, 24, 0), group='Snapdragons', role='Blossom throat')
    up_part('4589', 'Bright Pink', lvl + rad * 7 + t * 10, unit(rad * 0.6 + t), attach=(0, 24, 0), group='Snapdragons', role='Bud')
# green leaf whorls at the base of both spikes (uses 10280's green plates and clips)
leafy = [('60470b', 'Green', 3), ('48336', 'Green', 3), ('4032', 'Green', 3), ('4032', 'Dark Green', 2),
         ('15573', 'Dark Green', 6), ('85861', 'Dark Green', 6), ('4733', 'Lime', 3), ('3022', 'Lime', 6), ('3062', 'Black', 0)]
k = 0
for part, col, n in leafy:
    for _ in range(n):
        i = snaps[k % 2]; p, t, out = heads[i]
        a = k * 1.9; rad = unit(rot_about(t, a) @ perp(t)); h = -0.45 * stem_len[i] + (k // 2) * 4.0
        if part in ('4032', '3022', '85861'):
            up_part(part, col, p + t * h + rad * 9, unit(rad + t * 0.5), spin=a, group='Snapdragons', role='Leaf whorl')
        elif part == '4733':
            up_part(part, col, p + t * h + rad * 6, rad, attach=(0, 24, 0), group='Snapdragons', role='Leaf node')
        else:
            R = orient([0, 0, -1], unit(rad + t * 0.3), UP_L, t)
            put(part, col, R, p + t * h + rad * 8, attach=(0, 4, 0), group='Snapdragons', role='Leaf / clip')
        k += 1

# --------------------------------------------------------------- 3f. PRICKLY BUSHES x4 (low, round the trunk)
for n, i in enumerate([i for i in plan if plan[i] == 'bush']):
    p, t, out = heads[i]; g = 'Ground cover'
    R = orient([1, 0, 0], t, [0, 1, 0], out)
    put('32062', next_axle(), R, p, group=g, role='Head axle')
    R = orient([0, 0, 1], t, [1, 0, 0], out)
    put('32039', 'Dark Bluish Gray', R, p + t * 6, group=g, role='Bush mount')
    base = p + t * 12
    up_part('3021', 'Dark Green', base, t, spin=n * 0.7, group=g, role='Bush base') if n < 3 else \
        up_part('32803', 'Dark Green', base, t, spin=n * 0.7, attach=(0, 16, 10), group=g, role='Bush base')
    up_part('6064', 'Dark Green', base + t * 3.2, t, spin=n, attach=(0, 0, 0), group=g, role='Bush (original 10280 role)')
# ground-cover leaves on the soil: 2x8 plates and inverted curved slopes fanning out from the bushes
for k in range(3):
    a = math.radians([35, 140, 295][k]); rad = np.array([math.cos(a), math.sin(a), 0])   # in the gaps between both stem rings
    R = orient([1, 0, 0], rad, UP_L, [0, 0, 1])
    put('3034', 'Dark Green', R, rad * 58, attach=(0, 8, 0), group='Ground cover', role='Ground-cover leaf')
for k in range(2):
    a = math.radians(100 + k * 140); rad = np.array([math.cos(a), math.sin(a), 0])
    up_part('32803', 'Dark Green', rad * 48 + np.array([0, 0, 2.0]), np.array([0, 0, 1.0]), xhint=rad, attach=(0, 16, 10), group='Ground cover', role='Ground-cover leaf')

# --------------------------------------------------------------- 3g. FOLIAGE x2 (big sand-green leaves)
fol = [i for i in plan if plan[i] == 'foliage']
sg = [('45301', 2, 1), ('90397', 2, 1), ('15362', 2, 2), ('15068', 2, 1), ('64225', 1, 2)]
for n, i in enumerate(fol):
    p, t, out = heads[i]; g = 'Foliage'
    R = orient([1, 0, 0], t, [0, 1, 0], out)
    put('32062', next_axle(), R, p, group=g, role='Head axle')
    j = 0
    for part, n0, n1 in sg:
        for _ in range(n0 if n == 0 else n1):
            a = (j - 1.5) * 0.55 + n * 0.3; j += 1
            side = unit(rot_about(t, a) @ out)
            ld = unit(side * 0.9 + t * 0.55)
            if part == '45301':
                R = orient([0, 0, -1], ld, UP_L, unit(t - ld * (ld @ t)))
                put(part, 'Sand Green', R, p + ld * 6, attach=(0, 8, 30), group=g, role='Large leaf (wedge 16x4)')
            elif part == '90397':
                R = orient([0, 0, -1], ld, UP_L, unit(t - ld * (ld @ t)))
                put(part, 'Sand Green', R, p + ld * 10 + t * 8, attach=(0, 4, 45), group=g, role='Leaf (original 10280 role)')
            elif part == '15362':
                R = orient([0, 0, -1], ld, [0, -1, 0], t)
                put(part, 'Sand Green', R, p + ld * 4 + t * 4, attach=(0, 0, 10), group=g, role='Curled leaf')
            else:
                R = orient([0, 0, -1], ld, UP_L, unit(t - ld * (ld @ t)))
                put(part, 'Sand Green', R, p + ld * 12 + t * (14 + 4 * j), attach=(0, 8, 0), group=g, role='Leaf')
    # 16 leaflet clips along each foliage stem and the leaves' midribs
    for k in range(16):
        a = k * 2.4; rad = unit(rot_about(t, a) @ out)
        h = -18 - k * 3.5
        R = orient([0, 0, -1], unit(rad + t * 0.35), UP_L, t)
        put('15712', 'Sand Green', R, p + t * h + rad * 6, attach=(0, 4, 0), group=g, role='Leaflet')

# =================================================================== 4. CANOPY (40725 cherry blossom parts + spare 10280 browns)
canopy_g = 'Canopy'
roots = []   # (point, direction) where a twig starts
for h in A['axle_holes']:
    lab = h['label']
    if lab.startswith('arm-') and '-axle-' in lab and lab.endswith('-a'):
        o, d = mouth(h)
        mid = o + d * (h['depth'] / 2)
        R = axle_R(d, hx(h))
        put('4519', 'Light Bluish Gray', R, mid, group='Canopy', role='Through-axle carrying two twigs')
        other = holes[lab[:-1] + 'b']
        roots.append((o, -d, 'side', hx(h)))
        roots.append((np.array(other['origin']), -np.array(other['dir']), 'side', hx(h)))
for h in A['axle_holes']:
    if h['label'].endswith('-tip') and h['label'].startswith('arm-'):
        o, d = mouth(h); roots.append((o, -d, 'tip', hx(h)))
o, d = mouth(holes['trunk-top']); roots.append((o, -d, 'top', hx(holes['trunk-top'])))
# spurs: half pins in the arms' pin holes (one per hole, alternate faces)
spurs = []
sp_holes = sorted([h for h in A['pin_holes'] if h['label'].startswith('arm-')], key=lambda h: h['label'])
for k in range(0, len(sp_holes), 2):
    h = sp_holes[k + (k // 2) % 2]
    o, d = mouth(h)
    R = orient([-1, 0, 0], d, [0, 1, 0], perp(d))
    put('89678', 'Dark Bluish Gray', R, o, group=canopy_g, role='Spur anchor (half pin)')     # flange outside, pin 8 mm in
    spurs.append((o - d * 3.5, -d))
assert len(spurs) == 12, len(spurs)
# the 6th 3L pin crowns the trunk-top twig
o, d = mouth(holes['trunk-top'])
up_part('32054', 'Black', o + np.array([0, 0, 5.0]), np.array([0, 0, 1.0]), attach=(0, 0, 0), group='Structure', role='Crown twig pin') if False else None

def blossom(q, u, kind, group=canopy_g):
    """Blossom heads. Returns nothing; consumes parts. Keeps one small flower in reserve per crown left."""
    if kind == 'flower' and flowers_left() <= crowns_left():
        kind = 'crown' if crowns_left() else ('bud' if pool[('15470', 'White')] + pool[('15470', 'Bright Pink')] else 'leaf')
    if kind == 'crown' and crowns_left() == 0:
        kind = 'flower' if flowers_left() else 'leaf'
    if kind == 'bud' and pool[('15470', 'White')] + pool[('15470', 'Bright Pink')] == 0:
        kind = 'leaf'
    if kind == 'leaf' and pool[('32607', 'Lime')] == 0:
        return
    if kind == 'crown':
        col = 'White' if pool[('39262', 'White')] >= pool[('39262', 'Bright Pink')] else 'Bright Pink'
        up_part('39262', col, q, u, spin=rng.uniform(0, 6.28), attach=(0, 8, 0), group=group, role='Blossom petals (crown)')
        centre = max([('24866', 'Dark Red'), ('24866', 'Dark Pink'), ('24866', 'Bright Pink')], key=lambda k: pool[k])
        if pool[centre]:
            up_part('24866', centre[1], q + u * 3.6, u, spin=rng.uniform(0, 6.28), group=group, role='Blossom centre')
    elif kind == 'flower':
        centre = max([('24866', 'Bright Pink'), ('24866', 'Dark Pink'), ('24866', 'Dark Red')], key=lambda k: pool[k])
        up_part('24866', centre[1], q, u, spin=rng.uniform(0, 6.28), group=group, role='Small blossom')
    elif kind == 'bud':
        col = 'White' if pool[('15470', 'White')] >= pool[('15470', 'Bright Pink')] else 'Bright Pink'
        up_part('15470', col, q, u, attach=(0, 0, 0), group=group, role='Bud (swirl)')
    elif kind == 'leaf':
        up_part('32607', 'Lime', q, u, spin=rng.uniform(0, 6.28), group=group, role='Young leaf')

def crowns_left(): return pool[('39262', 'White')] + pool[('39262', 'Bright Pink')]
def flowers_left(): return pool[('24866', 'Bright Pink')] + pool[('24866', 'Dark Pink')] + pool[('24866', 'Dark Red')]

# spurs: 1x1 brick with 4 side studs, crowns on top + sides
for k, (q, u) in enumerate(spurs):
    up_part('4733', 'Reddish Brown', q, u, spin=k, attach=(0, 24, 0), group=canopy_g, role='Spur node')
    top = q + u * 11.2
    blossom(top, unit(u + np.array([0, 0, 0.4])), 'crown')
    for s in range(3):
        side = unit(rot_about(u, s * 2.1 + k) @ perp(u))
        blossom(q + u * 4.8 + side * 5.6, unit(side + np.array([0, 0, 0.5])), 'crown')

# twigs
twig_parts = []
for p, c in [('6538b', 'Reddish Brown'), ('32034', 'Reddish Brown'), ('23443', 'Reddish Brown'), ('48729b', 'Reddish Brown'),
             ('78258', 'Reddish Brown'), ('24122', 'Reddish Brown'), ('13564', 'Reddish Brown'), ('33183', 'Reddish Brown'),
             ('4589', 'Reddish Brown'), ('85861', 'Reddish Brown'), ('4733', 'Reddish Brown'), ('68211', 'Reddish Brown'),
             ('24855', 'Reddish Brown'), ('65578', 'Dark Red'), ('32054', 'Black')]:
    twig_parts.append((p, c))
LEN = {'6538b': 16, '32034': 24, '23443': 14.4, '48729b': 15.2, '78258': 16, '24122': 8}
AX = {'6538b': [0, 0, 1], '32034': [0, 0, 1], '23443': [0, -1, 0], '48729b': [0, -1, 0], '78258': [0, -1, 0], '24122': [0, 0, 1]}
nt = len(roots)
# deal chain parts round-robin so every twig gets a share
chains = [[] for _ in range(nt)]
first = [('6538b' if r[2] == 'side' else '32034') for r in roots]
for i, f in enumerate(first): chains[i].append(f)
deal = []
for part in ['6538b', '32034', '24122', '23443', '48729b', '78258']:
    n = pool[(part, 'Reddish Brown')] - sum(1 for f in first if f == part)
    deal += [part] * n
hubs = [x for x in deal if x == '24122']; deal = [x for x in deal if x != '24122']
rng.shuffle(deal)
for k, part in enumerate(deal): chains[k % nt].append(part)
hub_chains = [i for i in range(nt) if roots[i][2] == 'side'][:len(hubs)]      # at most one hub per twig
for i in hub_chains: chains[i].append('24122')
# axle-type parts (joined by hidden 2L axles) come first and stay straight; bar-type parts follow and may bend
AXIAL = ('6538b', '32034', '24122')
# the hub (24122) closes the axle run: one axle passes through it, and its bar holders start the bar run
chains = [[c[0]] + sorted(c[1:], key=lambda x: (0 if x in ('6538b', '32034') else 1 if x == '24122' else 2)) for c in chains]
ends = ['68211'] * 12 + ['24855'] * 4 + ['13564'] * 4 + ['33183'] * 2 + ['4589'] * 2
rng.shuffle(ends)
while len(ends) < nt: ends.append(None)
knots = pool[('85861', 'Reddish Brown')]
mid_nodes = pool[('4733', 'Reddish Brown')]
axles_black = lambda: pool[('32062', 'Red')] + pool[('32062', 'Black')]
stamen_left = lambda: pool[('65578', 'Dark Red')]
tip_heads = []
for ti, (o, d, kind, harm) in enumerate(roots):
    away = unit(np.array([o[0], o[1], 0.0]) + 1e-6)
    t_bend = unit(d * 0.55 + away * 0.45 + np.array([0, 0, 0.35]) + rng.normal(0, 0.12, 3))
    if kind == 'top': t_bend = unit(np.array([0, 0, 1.0]) + rng.normal(0, 0.1, 3))
    t = d.copy()                      # the first part is coaxial with the hole
    prev_axial = False; t_prev = t.copy(); harm_prev = harm; harm_t = harm
    q = o.copy()
    if kind == 'side':
        q = o + d * 0.2              # through-axle sticks out ~7.5 mm; the connector slides over it
    for ci, part in enumerate(chains[ti]):
        if part in AXIAL and ci > 0 and prev_axial and axles_black() > 0:
            t = t_prev; harm_t = harm_prev                    # axle joints are straight
            col = 'Black' if pool[('32062', 'Black')] > 0 else 'Red'
            R = orient([1, 0, 0], t, [0, 1, 0], harm_t if prev_axial else perp(t))
            put('32062', col, R, q, group=canopy_g, role='Hidden twig joint axle')
        if kind != 'side' and ci == 0:
            col = 'Black' if pool[('32062', 'Black')] > 0 else 'Red'
            put('32062', col, axle_R(t, harm), q, group=canopy_g, role='Twig root axle (into PLA)')
        L = LEN[part]
        harm_t = harm if ci == 0 else (harm_t if (prev_axial and part in ('6538b', '32034', '24122')) else perp(t))
        R = orient(AX[part], t, [1, 0, 0], harm_t)
        prev_axial = part in ('6538b', '32034', '24122'); t_prev = t.copy(); harm_prev = harm_t
        mid = q + t * (L / 2)
        put(part, 'Reddish Brown', R, mid, attach=(0, -12 if part == '23443' else (12 if part == '48729b' else 0), 0) if AX[part][1] else (0, 0, 0),
            group=canopy_g, role='Twig')
        q = q + t * L
        nxt = chains[ti][ci + 1] if ci + 1 < len(chains[ti]) else None
        if nxt in AXIAL and part in AXIAL: pass                 # stay coaxial through axle joints
        else: t = t_bend if ci == 0 or (prev_axial and nxt not in AXIAL and t_bend is not None and np.allclose(t, d)) else unit(t + rng.normal(0, 0.18, 3) + np.array([0, 0, 0.05]))
        # knots with buds / leaves along the twig
        if knots > 0 and ci % 2 == 1:
            side = unit(np.cross(t, rng.normal(0, 1, 3)))
            up_part('85861', 'Reddish Brown', q - t * L / 2 + side * 3, side, group=canopy_g, role='Knot')
            knots -= 1
            kind2 = 'bud' if pool[('15470', 'White')] + pool[('15470', 'Bright Pink')] > 0 else 'leaf'
            blossom(q - t * L / 2 + side * 6.2, side, kind2)
        if mid_nodes > 0 and pool[('4733', 'Reddish Brown')] > 0 and ci == 2:
            side = unit(np.cross(t, [0, 0, 1]) + np.array([0, 0, 0.3]))
            up_part('4733', 'Reddish Brown', q + side * 4, side, attach=(0, 24, 0), group=canopy_g, role='Blossom node')
            mid_nodes -= 1
            blossom(q + side * 15, unit(side + np.array([0, 0, 0.5])), 'crown' if crowns_left() else 'flower')
            blossom(q + side * 8 + np.array([0, 0, 5.6]), np.array([0, 0, 1.0]), 'crown' if crowns_left() else 'flower')
    e = ends[ti] if ti < len(ends) else None
    if e in ('68211', '24855'):
        R = rot_about(t, rng.uniform(0, 6.28)) @ orient(UP_L, t, [1, 0, 0], perp(t))
        org = put(e, 'Reddish Brown', R, q, attach=(0, 4 if e == '68211' else 20, 0), group=canopy_g, role='Blossom spray (original 40725 role)' if e == '68211' else 'Blossom spray')
        tips = ([np.array([5.0, -25.0, -8.5]), np.array([4.7, -19.8, 9.9]), np.array([-10.5, -17.7, 0.0])] if e == '68211'
                else [np.array([-24.3, -26.0, -14.3]), np.array([22.6, -21.3, -12.0]), np.array([0.0, -15.7, 22.0])])
        for tp in tips:
            wp = org + R @ (tp * LDU)
            tip_heads.append((wp, unit(t + R @ unit(tp) * 0.6)))
    elif e == '13564':
        R = orient([-1, 0, 0], t, [0, 1, 0], perp(t))
        put(e, 'Reddish Brown', R, q, attach=(8, 0, 0), group=canopy_g, role='Curling twig tip')
    elif e == '33183':
        R = orient(UP_L, t, [1, 0, 0], perp(t))
        org = put(e, 'Reddish Brown', R, q, group=canopy_g, role='Twig tip')
        tip_heads.append((org + t * 16.5, t))
    elif e == '4589':
        up_part('4589', 'Reddish Brown', q, t, attach=(0, 24, 0), group=canopy_g, role='Twig tip')
# heads on spray tips: stamen (65578) + crown / small flower; bare tips get a flower
rng.shuffle(tip_heads)
for q, u in tip_heads:
    if stamen_left() > 0:
        R = rot_about(u, rng.uniform(0, 6.28)) @ orient(UP_L, u, [1, 0, 0], perp(u))
        put('65578', 'Dark Red', R, q, attach=(0, 22.5, 0), group=canopy_g, role='Stamen / flower stalk (original 40725 role)')
        q = q + u * 10.6
    blossom(q, u, 'crown' if crowns_left() and (rng.uniform() < 0.55 or not flowers_left() > crowns_left()) else 'flower')
# remaining stamens hang from the crown blossoms on spurs/nodes, carrying the remaining heads
extra_sites = [pl for pl in placed if pl['part'] == '39262' and pl['group'] == canopy_g]
rng.shuffle(extra_sites)
si = 0
while stamen_left() > 0 or crowns_left() > 0 or flowers_left() > 0 or pool[('32607', 'Lime')] > 0 or pool[('15470', 'White')] + pool[('15470', 'Bright Pink')] > 0:
    site = extra_sites[si % len(extra_sites)]; si += 1
    R0 = np.array(site['R']); org = np.array(site['p']); u0 = R0 @ UP_L
    side = unit(R0 @ np.array([1.0, 0, 0]) * math.cos(si) + R0 @ np.array([0, 0, 1.0]) * math.sin(si))
    q = org + R0 @ (np.array([0, 0, 0]) * LDU) + side * 7 + u0 * 1
    u = unit(side + u0 * 0.6)
    if stamen_left() > 0:
        R = rot_about(u, si) @ orient(UP_L, u, [1, 0, 0], perp(u))
        put('65578', 'Dark Red', R, q, attach=(0, 22.5, 0), group=canopy_g, role='Stamen / flower stalk (original 40725 role)')
        q = q + u * 10.6
    if crowns_left(): blossom(q, u, 'crown')
    elif flowers_left(): blossom(q, u, 'flower')
    elif pool[('15470', 'White')] + pool[('15470', 'Bright Pink')] > 0: blossom(q, u, 'bud')
    elif pool[('32607', 'Lime')] > 0: blossom(q, u, 'leaf')
# remaining twig hardware: knots and nodes
while pool[('85861', 'Reddish Brown')] > 0 or pool[('4733', 'Reddish Brown')] > 0:
    tw = [pl for pl in placed if pl['group'] == canopy_g and pl['role'] == 'Twig']
    pl = tw[int(rng.integers(len(tw)))]
    org = np.array(pl['p']); side = unit(rng.normal(0, 1, 3) + np.array([0, 0, 0.6]))
    if pool[('85861', 'Reddish Brown')] > 0:
        up_part('85861', 'Reddish Brown', org + side * 3, side, group=canopy_g, role='Knot')
    else:
        up_part('4733', 'Reddish Brown', org + side * 4, side, attach=(0, 24, 0), group=canopy_g, role='Node')

# =================================================================== 5. LEFTOVERS
# any 2L axles not needed as hidden joints: push them into the spare stem / twig joints as doubled axles
while pool[('32062', 'Red')] + pool[('32062', 'Black')] > 0:
    col = 'Red' if pool[('32062', 'Red')] > 0 else 'Black'
    st = [pl for pl in placed if pl['part'] == '26287']
    pl = st[int(rng.integers(len(st)))]
    R = np.array(pl['R']); org = np.array(pl['p']); ax = R @ np.array([0, 0, 1.0])
    put('32062', col, orient([1, 0, 0], ax, [0, 1, 0], perp(ax)), org, group='Stems', role='Spare axle stored inside a stem connector')
# the 6th 3L pin joins the first poppy's two black 2x2 pin-hole base plates
i = [i for i in plan if plan[i] == 'poppy'][0]; p, t, out = heads[i]
R = orient([1, 0, 0], t, [0, 1, 0], out)
put('32054', 'Black', R, p + t * 4.0, group='Poppies', role='Pin joining the base plates')
unused = {f'{k[0]}|{k[1]}': v for k, v in pool.items() if v}
reasons = {'96874|Dark Turquoise': 'Brick separator: a tool for prying bricks apart, not a model part. Keep it with your tools.'}
used = len(placed)
json.dump(placed, open(os.path.join(OUT, 'placements.json'), 'w'))
json.dump({'total': TOTAL, 'used': used, 'unused': unused, 'reasons': reasons, 'bl_ids': BL_ID,
           'plan': {str(k): v for k, v in plan.items()}}, open(os.path.join(OUT, 'usage.json'), 'w'), indent=1)
print('placed', used, 'of', TOTAL, 'unused', unused)
from collections import Counter
print(Counter(p['group'] for p in placed))
