"""Generate the recessed sakura-branch motif that wraps the six planter faces.

The artwork is drawn on a flat strip (6 faces x FACE_W mm wide, z = height in planter
coordinates) and saved as polygons per paint colour. The FreeCAD macro maps each face's
slice of the strip onto that (tapered) face and cuts it 0.8 mm deep.

Every pocket is at least MIN_W wide and separated from pockets of another colour by a
land of at least LAND mm, so each colour can be flooded with acrylic and wiped back.

usage: python tools/make_motif.py [seed]  ->  cad/motif.json, images/motif.svg
"""
import json, math, os, random, sys
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, box
from shapely.ops import unary_union
from shapely import affinity

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 23
rnd = random.Random(SEED)

FACE_W = 80.0            # usable width of one face on the strip (corner fillet zones excluded)
NF = 6
Z0, Z1 = -76.0, 0.0      # usable height (planter z: floor underside -83, rim band starts at +5)
LAND, MIN_W = 0.9, 1.1   # mm
RES = 10                 # circle resolution (segments per quarter)

def lerp(a, b, t): return a + (b - a) * t

# ------------------------------------------------------------------ main branch
def branch_z(x):
    return -46 + 17 * math.sin(2 * math.pi * x / 240 + 0.4) + 6 * math.sin(2 * math.pi * x / 83 + 1.3) + 0.03 * x

X_START, X_END = 6.0, 470.0
xs = [X_START + (X_END - X_START) * k / 400 for k in range(401)]
pts = [(x, branch_z(x)) for x in xs]
def smooth(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)
pts = [(x, lerp(Z0 + 1.5, z, smooth((x - X_START) / 34) ** 0.7)) for x, z in pts]   # rises out of the bottom edge on face 1

def width_at(t): return lerp(5.2, 1.3, t ** 0.8)

def tapered(path, w0, w1, cap_end=True):
    """Polygon of a polyline whose width tapers from w0 to w1."""
    segs = []
    n = len(path) - 1
    for k in range(n):
        t0, t1 = k / n, (k + 1) / n
        a, b = path[k], path[k + 1]
        r0, r1 = lerp(w0, w1, t0) / 2, lerp(w0, w1, t1) / 2
        segs.append(unary_union([Point(a).buffer(r0, RES), Point(b).buffer(r1, RES)]).convex_hull)
    return unary_union(segs)

bark = [tapered(pts, 5.2, 1.3)]
branch_line = LineString(pts)

def tangent(x):
    h = 0.5
    dz = branch_z(x + h) - branch_z(x - h)
    l = math.hypot(2 * h, dz); return (2 * h / l, dz / l)

# ------------------------------------------------------------------ blossoms, buds, twigs
def blossom(cx, cz, R, rot):
    """Five notched petals around a separate centre pocket. Returns (petals, centre, outline)."""
    rp = R * 0.46
    petals = []
    for k in range(5):
        a = rot + 2 * math.pi * k / 5
        c = (cx + math.cos(a) * R * 0.52, cz + math.sin(a) * R * 0.52)
        p = affinity.rotate(affinity.scale(Point(0, 0).buffer(rp, RES), 1.0, 1.18), math.degrees(a) - 90, origin=(0, 0))
        p = affinity.translate(p, *c)
        tip = (cx + math.cos(a) * (R + 0.2), cz + math.sin(a) * (R + 0.2))
        notch = Polygon([tip, (tip[0] - math.cos(a) * R * 0.22 - math.sin(a) * R * 0.11, tip[1] - math.sin(a) * R * 0.22 + math.cos(a) * R * 0.11),
                         (tip[0] - math.cos(a) * R * 0.22 + math.sin(a) * R * 0.11, tip[1] - math.sin(a) * R * 0.22 - math.cos(a) * R * 0.11)])
        petals.append(p.difference(notch))
    allp = unary_union(petals)
    rc = max(1.3, R * 0.17)
    centre = Point(cx, cz).buffer(rc, RES)
    petal = allp.difference(Point(cx, cz).buffer(rc + LAND, RES))
    return petal, centre, allp.union(centre)

def bud(cx, cz, ang, L=5.6, W=3.6):
    e = affinity.scale(Point(0, 0).buffer(1.0, RES), L / 2, W / 2)
    e = affinity.rotate(e, math.degrees(ang), origin=(0, 0))
    return affinity.translate(e, cx, cz)

petals, centres, buds, occupied = [], [], [], []
def free(shape, pad=LAND):
    if shape.is_empty: return True
    g = shape.buffer(pad, 4)
    if g.bounds[1] < Z0 or g.bounds[3] > Z1: return False
    # keep every motif element inside one face (corner fillets lie between faces)
    f0 = math.floor(g.bounds[0] / FACE_W); f1 = math.floor(g.bounds[2] / FACE_W)
    if f0 != f1 or f0 < 0 or f1 >= NF: return False
    return all(not g.intersects(o) for o in occupied)

def add_blossom(cx, cz, R, rot):
    p, c, outline = blossom(cx, cz, R, rot)
    if not free(outline) or outline.buffer(LAND).intersects(bark_union()): return False
    petals.append(p); centres.append(c); occupied.append(outline); outlines.append(outline); return True

def bark_union(): return unary_union(bark)

# twigs every ~34 mm, alternating up and down; each ends in a cluster of blossoms and buds
outlines = []
x = 30.0; up = True
while x < X_END - 16:
    t = (x - X_START) / (X_END - X_START)
    bx, bz = branch_z(x) if False else x, branch_z(x)
    tx, tz = tangent(x)
    sgn = 1 if up else -1
    ang = math.atan2(tz, tx) + sgn * math.radians(rnd.uniform(35, 60))
    L = rnd.uniform(15, 24) * lerp(1.0, 0.8, t)
    ok = False
    for tries in range(12):
        R = rnd.uniform(7.0, 9.0) * lerp(1.0, 0.85, t)
        end = (bx + math.cos(ang) * L, bz + math.sin(ang) * L)
        c = (end[0] + math.cos(ang) * R * 0.6, end[1] + math.sin(ang) * R * 0.6)
        p, cc, outline = blossom(c[0], c[1], R, rnd.uniform(0, 2 * math.pi))
        twig = tapered([(bx, bz), c], lerp(2.8, 1.5, t), 1.3)
        twig_out = twig.difference(Point(bx, bz).buffer(width_at(t) + 1.0, RES)).difference(outline.buffer(LAND, 4))
        if free(outline) and free(twig_out, 0.3):
            bark.append(twig); petals.append(p); centres.append(cc); occupied.append(outline); outlines.append(outline)
            occupied.append(twig_out)
            ok = True
            # companions: a second, smaller blossom or a bud beside the first
            for extra in range(2):
                a2 = ang + sgn * math.radians(rnd.choice((-1, 1)) * rnd.uniform(55, 95))
                if rnd.random() < 0.55:
                    R2 = R * rnd.uniform(0.62, 0.8)
                    c2 = (c[0] + math.cos(a2) * (R + R2 + 0.6), c[1] + math.sin(a2) * (R + R2 + 0.6))
                    p2, cc2, o2 = blossom(c2[0], c2[1], R2, rnd.uniform(0, 6.3))
                    if free(o2):
                        petals.append(p2); centres.append(cc2); occupied.append(o2); outlines.append(o2)
                else:
                    m = (bx + math.cos(ang) * L * 0.6, bz + math.sin(ang) * L * 0.6)
                    a3 = ang - sgn * math.radians(rnd.uniform(40, 65))
                    e2 = (m[0] + math.cos(a3) * 7.5, m[1] + math.sin(a3) * 7.5)
                    bc = (e2[0] + math.cos(a3) * 1.6, e2[1] + math.sin(a3) * 1.6)
                    b_ = bud(bc[0], bc[1], a3)
                    spur = tapered([m, bc], 1.35, 1.2)
                    spur_out = spur.difference(twig.buffer(0.6)).difference(b_.buffer(LAND, 4))
                    if free(b_) and free(spur_out, 0.2):
                        bark.append(spur); buds.append(b_); occupied.append(b_); occupied.append(spur_out); outlines.append(b_)
                    break
            break
        ang -= sgn * math.radians(7); L *= 0.93
    x += rnd.uniform(26, 36) if ok else 5
    up = not up if ok else up

# a few blossoms sitting right on the branch, between the twigs
for k in range(60):
    if len(petals) > 46: break
    x = rnd.uniform(15, X_END - 15); t = (x - X_START) / (X_END - X_START)
    bz = branch_z(x); w = width_at(t)
    R = rnd.uniform(5.6, 7.4)
    side = rnd.choice((-1, 1))
    tx, tz = tangent(x); nx, nz = -tz * side, tx * side
    d = w / 2 + R + LAND + 0.3
    add_blossom(x + nx * d, bz + nz * d, R, rnd.uniform(0, 6.3))

# ------------------------------------------------------------------ clip into faces, check, save
def faces_of(geom, pad):
    out = []
    for f in range(NF):
        clip = box(f * FACE_W, Z0, (f + 1) * FACE_W, Z1).buffer(-pad, join_style=2)
        g = geom.intersection(clip)
        for poly in (g.geoms if hasattr(g, 'geoms') else [g]):
            if poly.is_empty or poly.geom_type != 'Polygon' or poly.area < 1.5: continue
            if poly.buffer(-MIN_W / 2 + 0.05).is_empty: continue       # too thin to print or paint
            out.append((f, poly))
    return out

groups = {'bark': unary_union(bark).difference(unary_union(outlines).buffer(LAND, 4)), 'petal': unary_union(petals), 'centre': unary_union(centres), 'bud': unary_union(buds)}
# lands between colours
groups['petal'] = groups['petal'].difference(groups['bark'].buffer(LAND))
groups['bud'] = groups['bud'].difference(groups['bark'].buffer(LAND))
data = {'face_w': FACE_W, 'z0': Z0, 'z1': Z1, 'depth': 0.8, 'land': LAND, 'seed': SEED, 'polys': []}
for cat, g in groups.items():
    for f, poly in faces_of(g, 0.0 if cat != 'bark' else 0.0):
        poly = poly.simplify(0.04)
        data['polys'].append({'cat': cat, 'face': f, 'outer': [[round(a - f * FACE_W, 3), round(b, 3)] for a, b in poly.exterior.coords[:-1]],
                              'holes': [[[round(a - f * FACE_W, 3), round(b, 3)] for a, b in r.coords[:-1]] for r in poly.interiors]})
# check: lands between different colours
cats = list(groups)
for i in range(len(cats)):
    for j in range(i + 1, len(cats)):
        d = groups[cats[i]].distance(groups[cats[j]]) if not groups[cats[i]].is_empty and not groups[cats[j]].is_empty else 99
        assert d >= LAND - 0.05, (cats[i], cats[j], d)
json.dump(data, open(os.path.join(ROOT, 'cad', 'motif.json'), 'w'))

# SVG preview (strip unrolled; grey = corner fillet zones)
COL = {'bark': '#6b3f2a', 'petal': '#f2a7c3', 'centre': '#b5285a', 'bud': '#e0607e'}
S = 3.0; gap = 18.0
W = NF * (FACE_W + gap) * S; H = (Z1 - Z0 + 8) * S
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}">',
       f'<rect width="{W:.0f}" height="{H:.0f}" fill="#efe7d8"/>']
for f in range(NF):
    ox = (f * (FACE_W + gap) + gap / 2) * S
    svg.append(f'<rect x="{ox - gap / 2 * S:.1f}" y="0" width="{gap / 2 * S:.1f}" height="{H:.0f}" fill="#e2d8c4"/>')
    svg.append(f'<rect x="{ox + FACE_W * S:.1f}" y="0" width="{gap / 2 * S:.1f}" height="{H:.0f}" fill="#e2d8c4"/>')
for p in data['polys']:
    ox = (p['face'] * (FACE_W + gap) + gap / 2) * S
    def path(ring): return 'M' + ' L'.join(f'{ox + a * S:.1f},{(Z1 + 4 - b) * S:.1f}' for a, b in ring) + ' Z'
    d = path(p['outer']) + ''.join(' ' + path(h) for h in p['holes'])
    svg.append(f'<path d="{d}" fill="{COL[p["cat"]]}" fill-rule="evenodd"/>')
svg.append('</svg>')
open(os.path.join(ROOT, 'images', 'motif.svg'), 'w').write('\n'.join(svg))
n = {c: sum(1 for p in data['polys'] if p['cat'] == c) for c in COL}
print('blossoms', len(petals), 'buds', len(buds), 'pockets', n)
