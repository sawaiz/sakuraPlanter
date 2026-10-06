import json, sys
from collections import Counter
P = json.load(open(sys.argv[1])); names_xlsx = sys.argv[2]; out = sys.argv[3]
HW = {'Through-axle carrying two twigs','Twig','Twig root axle (into PLA)','Hidden twig joint axle','Spur anchor (half pin)','Spur node','Knot','Blossom node','Curling twig tip','Twig tip'}
def step(p):
    g, r = p['group'], p['role']
    if r.startswith(('Hidden anchor', 'Daisy stem', 'Hidden socket')): return 1
    if g == 'Structure' and r.startswith('Branch joint'): return 4
    if g == 'Stems': return 5
    if g in ('Ground cover', 'Roses', 'Aster'): return 6
    if g in ('Poppies', 'Lavender', 'Snapdragons', 'Foliage'): return 7
    if g == 'Daisies': return 8
    if g == 'Canopy': return 9 if r in HW else 10
    raise ValueError((g, r))
steps = [step(p) for p in P]
import openpyxl
ws = openpyxl.load_workbook(names_xlsx)['Parts checklist']
names = {(str(r[0]), r[1]): r[2] for r in ws.iter_rows(min_row=12, values_only=True) if r[0] and r[2]}
BL = {'4589': '4589b', '98088': '98088pb05', '6538b': '6538c'}
lists = {}
for p, s_ in zip(P, steps):
    lists.setdefault(s_, Counter())[(BL.get(p['part'], p['part']), p['colour'])] += 1
json.dump({'steps': steps, 'lists': {str(k): [{'part': a, 'colour': b, 'name': names.get((a, b), '?'), 'n': n} for (a, b), n in c.most_common()] for k, c in lists.items()}}, open(out, 'w'))
print(sorted(Counter(steps).items()))
