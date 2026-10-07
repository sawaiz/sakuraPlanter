"""Compose the first six concept mock-ups (scroll, stone, trellis and pairs).

usage: python concepts/compose.py   -> concepts/work/<concept>.json and concepts/work/summary.json
"""
import json, math, os
import numpy as np
from kit import *

SUMMARY = []

# =========================================================== A. Scroll (combined)
def scroll_frame(S, cx, width, height, roller='lego', cloth=('#E8E0CF', '#3E4B44'), label=''):
    """Kakejiku on a shelf stand: rollers, cloth, two feet; LEGO 32L axles as rollers and rear spine when width allows."""
    zb, zt = 24.0, 24.0 + height
    half = width / 2
    if roller == 'lego':
        S.axle32((cx, 0, zb), (1, 0, 0)); S.axle32((cx, 0, zt), (1, 0, 0))
        for sx in (-1, 1):                                  # rear spine: a 32L axle up each side, behind the cloth
            S.axle32((cx + sx * (half - 30), 9, zb + 128), (0, 0, 1))
    else:
        for z in (zb, zt): S.mesh(cyl(3.2, width + 6, (cx, 0, z), (1, 0, 0), 24), 'pla', f'{label} roller')
    for z in (zb, zt):                                      # roller end knobs (jiku-saki)
        for sx in (-1, 1):
            S.mesh(cyl(6.5, 12, (cx + sx * (half + 9), 0, z), (1, 0, 0)), 'pla', f'{label} roller knob')
    S.mesh(box([width - 8, 0.8, height - 6], (cx, -3.2, (zb + zt) / 2)), 'cloth_border', 'Mounting cloth (fabric or paper, not printed)')
    S.mesh(box([width - 40, 0.6, height * 0.66], (cx, -3.8, zb + height * 0.55)), 'cloth', 'Picture panel (washi or linen)')
    S.mesh(box([width * 0.9, 0.4, 5], (cx, -4.2, zb + height * 0.93)), 'cloth_border', 'Ichimonji strip')
    for sx in (-1, 1):                                      # feet: cradle the bottom roller and the spine
        f = M(box([22, 70, 20], (cx + sx * (half - 30), 6, 10))) - M(cyl(3.0, 30, (cx + sx * (half - 30), 0, zb), (1, 0, 0), 24))
        S.mesh(T(f), 'pla', f'{label} foot')
    for sx in (-1, 1):                                      # top clips: spine to top roller, with the keyhole for hanging
        S.mesh(box([12, 16, 14], (cx + sx * (half - 30), 4, zt - 2)), 'pla', f'{label} top clip (keyhole)')
    return zb, zt

S = Scene('a_scroll', 'Scroll')
zb, zt = scroll_frame(S, 0, 256, 280)
S.branch('branch_1', (70, -16, 150), (-0.93, 0, 0.36), (0.36, 0, 0.93))
S.branch('branch_3', (70, -22, 210), (-0.70, 0, 0.71), (0.71, 0, 0.70))
dish = M(box([110, 46, 12], (-55, -52, 6))) - M(box([102, 38, 12], (-55, -52, 10)))
S.mesh(T(dish), 'pla', 'Suiban dish with pin holder')
S.mesh(box([60, 24, 6], (-55, -52, 5)), 'tpu', 'Pin holder (kenzan), black TPU')
for name, dx, h, tilt, spin in [('roses_1', -70, 70, -0.25, 0.3), ('daisies_1', -40, 105, 0.3, 1.0), ('daisies_2', -85, 90, -0.45, 2.0), ('lavender_1', -55, 120, 0.05, 0), ('poppies_1', -30, 60, 0.5, 0.5)]:
    base = np.array([dx, -52, 10]); top = base + np.array([tilt * h, -8, h])
    S.flower(name, base, top, spin)
SUMMARY.append(S.save({'layout': 'combined', 'size': '26 × 12 cm footprint, about 42 cm tall',
    'lego': 'Two 32L axles are the rollers and two more stand behind the cloth as the spine; the cherry branches are rebuilt on LEGO 2L connectors and pinned to the spine; a few bouquet flowers sit in front.',
    'print': 'Four roller knobs, two feet, two top clips (one has the keyhole), a shallow dish and a small TPU pin holder.',
    'other': 'The cloth: a 25 × 28 cm piece of linen or washi paper, plus a contrasting border strip.'}))

# =========================================================== B. Stone and branch (combined)
S = Scene('b_stone', 'Stone and branch')
st = stone((150, 105, 70), 11)
holes = [((-10, 5, 40), (0.15, 0.1, 1)), ((12, -4, 38), (-0.2, 0.1, 1)), ((-40, -18, 22), (0, 0, 1)), ((40, -20, 22), (0, 0, 1)), ((-25, -30, 18), (0, 0, 1)), ((30, 10, 30), (0, 0, 1))]
S.mesh(socket_holes(st, holes), 'pla', 'Stone (hollow, 2 walls, 10 % infill)')
S.branch('branch_1', (-6, 2, 44), (-0.45, 0.1, 0.89), (-0.89, 0, -0.45), flip=True)
S.branch('branch_3', (10, -2, 44), (0.55, 0.05, 0.83), (0.83, 0, -0.55))
S.branch('branch_4', (0, 6, 46), (-0.05, 0.25, 0.97), (1, 0, 0.05))
for name, b, top, spin in [('daisies_1', (-40, -18, 22), (-58, -30, 95), 0.4), ('daisies_3', (40, -20, 22), (66, -32, 80), 1.7), ('lavender_2', (-25, -30, 18), (-34, -45, 120), 0),
                           ('ground cover_1', (30, 10, 30), (34, 6, 40), 0), ('roses_2', (40, -20, 22), (20, -46, 62), 0.6)]:
    S.flower(name, b, top, spin)
S.lego = [q for q in S.lego if not q['role'].startswith('Rose leaf')]
SUMMARY.append(S.save({'layout': 'combined', 'size': '15 × 11 cm footprint, about 40 cm tall',
    'lego': 'Three cherry branches rebuilt on LEGO 2L connectors rise out of the stone like a small bonsai; daisies, lavender and a rose grow at its foot on LEGO stems.',
    'print': 'One hollow low-poly stone with Technic sockets. Paint it, or leave it bone-white like marble.',
    'other': 'Nothing else.'}))

# =========================================================== C. Trellis frame (combined)
def trellis(S, cx, w, h, rails, label=''):
    """A frame of LEGO 32L axles held by printed corner blocks; horizontal rails carry the flowers."""
    zb = 22.0; zt = zb + h
    S.axle32((cx - w / 2, 0, zb + h / 2), (0, 0, 1)); S.axle32((cx + w / 2, 0, zb + h / 2), (0, 0, 1))
    for z in [zb, zt] + list(rails):
        if w >= 250: S.axle32((cx, 0, z), (1, 0, 0))
        else: S.mesh(cyl(3.0, w, (cx, 0, z), (1, 0, 0), 24), 'pla', f'{label} printed rail')
    for z in (zb, zt):
        for sx in (-1, 1): S.mesh(box([13, 13, 13], (cx + sx * w / 2, 0, z)), 'pla', f'{label} corner block')
    for sx in (-1, 1):
        S.mesh(box([14, 64, 10], (cx + sx * w / 2, 8, 5)), 'pla', f'{label} foot')
    for z in rails:
        for sx in (-0.25, 0.25): S.mesh(box([8, 10, 9], (cx + sx * w, -5, z)), 'pla', f'{label} rail clip')
    return zb, zt

S = Scene('c_trellis', 'Trellis frame')
zb, zt = trellis(S, 0, 256, 256, (100, 180))
S.branch('branch_2', (-110, -14, 180), (0.94, 0, 0.34), (-0.34, 0, 0.94))
S.branch('branch_4', (110, -14, 230), (-0.90, 0, 0.44), (0.44, 0, 0.90))
fan = [('roses_1', -0.35, 150, 0.2), ('roses_3', 0.32, 140, 1.2), ('poppies_1', -0.12, 175, 0.6), ('poppies_2', 0.55, 120, 2.0), ('daisies_2', -0.6, 135, 0.1),
       ('daisies_4', 0.15, 190, 0.8), ('lavender_1', -0.05, 215, 0), ('lavender_3', 0.38, 200, 0), ('foliage_1', -0.75, 110, 0.3), ('aster_1', 0.0, 130, 0.0)]
for name, ang, L, spin in fan:                              # a flat, hand-tied bouquet fanning up from the bottom rail
    base = np.array([0, -14, 40]); d = np.array([math.sin(ang), -0.08, math.cos(ang)])
    S.flower(name, base, base + d * L, spin)
S.mesh(box([26, 6, 14], (0, -16, 52)), 'pla', 'Bouquet tie (ribbon clip)')
SUMMARY.append(S.save({'layout': 'combined', 'size': '27 × 7 cm footprint, about 42 cm tall',
    'lego': 'Six 32L axles make the frame and two rails; the bouquet is tied flat and fans upward from the bottom rail, with two cherry branches crossing the top.',
    'print': 'Four corner blocks, two feet, rail clips and a bouquet tie: very little plastic.',
    'other': 'Optional: a card or linen panel behind.'}))

# =========================================================== D. Two stones (pair)
S = Scene('d_two_stones', 'Two stones')
st1 = stone((105, 85, 80), 5, (-95, 0)); st2 = stone((135, 85, 45), 8, (95, 0))
S.mesh(socket_holes(st1, [((-95, 0, 52), (0, 0, 1))]), 'pla', 'Tall stone')
S.mesh(socket_holes(st2, [((70, -10, 30), (0, 0, 1)), ((110, -12, 30), (0, 0, 1))]), 'pla', 'Low stone')
S.branch('branch_1', (-98, 0, 56), (-0.25, 0.05, 0.97), (-0.97, 0, -0.25), flip=True)
S.branch('branch_3', (-92, 0, 56), (0.45, 0.05, 0.89), (0.89, 0, -0.45))
for name, b, top, spin in [('roses_1', (70, -10, 30), (60, -20, 110), 0.3), ('daisies_2', (110, -12, 30), (128, -22, 125), 1.0), ('lavender_1', (90, 0, 32), (92, -4, 160), 0),
                           ('poppies_2', (100, -18, 30), (112, -40, 85), 0.6), ('daisies_5', (78, 8, 32), (66, 12, 140), 2.0)]:
    S.flower(name, b, top, spin)
SUMMARY.append(S.save({'layout': 'pair', 'size': '33 × 9 cm together; cherry about 40 cm tall, bouquet about 18 cm',
    'lego': 'A tall stone carries the cherry branches; a low stone carries a small meadow of bouquet flowers on LEGO stems.',
    'print': 'Two hollow stones.', 'other': 'Nothing else.'}))

# =========================================================== E. Trellis diptych (pair)
S = Scene('e_diptych', 'Trellis diptych')
trellis(S, -72, 128, 256, (120,), 'Left')
trellis(S, 72, 128, 256, (120,), 'Right')
S.branch('branch_2', (-128, -14, 120), (0.55, 0, 0.84), (-0.84, 0, 0.55))
S.branch('branch_5', (-16, -14, 200), (-0.50, 0, 0.87), (0.87, 0, 0.50))
for name, ang, L, spin in [('roses_2', -0.25, 120, 0.4), ('daisies_3', 0.3, 150, 1.0), ('lavender_2', 0.0, 200, 0), ('poppies_1', -0.5, 100, 0.6), ('foliage_2', 0.55, 110, 0.2)]:
    base = np.array([72, -14, 40]); d = np.array([math.sin(ang), -0.08, math.cos(ang)])
    S.flower(name, base, base + d * L, spin)
SUMMARY.append(S.save({'layout': 'pair', 'size': '29 × 7 cm together, about 40 cm tall',
    'lego': 'Two narrow frames stand side by side: LEGO 32L axles for the uprights, the cherry branch in the left, a tied bouquet in the right.',
    'print': 'Short printed rails (the sets have no 16L axles), corner blocks, feet and clips.', 'other': 'Optional backing card.'}))

# =========================================================== F. Twin scrolls (pair)
S = Scene('f_twin_scrolls', 'Twin scrolls')
scroll_frame(S, -78, 140, 300, roller='print', label='Left')
scroll_frame(S, 78, 140, 300, roller='print', label='Right')
S.branch('branch_3', (-40, -16, 120), (-0.45, 0, 0.89), (0.89, 0, 0.45))
S.branch('branch_4', (-60, -20, 200), (0.5, 0, 0.86), (-0.86, 0, 0.5), flip=True)
for name, b, top, spin in [('lavender_1', (70, -14, 60), (64, -18, 260), 0), ('roses_1', (80, -14, 60), (92, -22, 150), 0.2), ('daisies_1', (85, -14, 60), (110, -20, 210), 0.9), ('foliage_1', (75, -14, 60), (52, -20, 130), 0.4)]:
    S.flower(name, b, top, spin)
SUMMARY.append(S.save({'layout': 'pair', 'size': '33 × 7 cm together, about 34 cm tall',
    'lego': 'Two narrow scrolls: cherry branches on the left, a tall nageire-style stem arrangement on the right, held to each scroll by LEGO pins.',
    'print': 'Printed rollers (the 32L axles are too wide for a narrow scroll), knobs, feet and clips.', 'other': 'Two 12 × 30 cm pieces of cloth or washi.'}))

json.dump([{k: v for k, v in s.items() if k not in ('lego', 'printed')} for s in SUMMARY], open(os.path.join(W, 'summary.json'), 'w'), indent=1)
for s in SUMMARY: print(s['name'], s['title'], 'LEGO', s['lego_count'], 'printed g', s['printed_grams'])
