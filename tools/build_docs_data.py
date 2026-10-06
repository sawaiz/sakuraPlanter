"""Write docs/data/steps.js (per-piece step numbers + per-step parts lists with colours),
docs/data/plates.js (plate summary) for the companion page, and lego/parts_usage.csv (what each piece does).
usage: python tools/build_docs_data.py
"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEX = {'Black': '#1B2A34', 'Bright Pink': '#E4ADC8', 'Dark Bluish Gray': '#6C6E68', 'Dark Green': '#184632', 'Dark Pink': '#C870A0',
       'Dark Purple': '#3F3691', 'Dark Turquoise': '#008F9B', 'Green': '#237841', 'Lavender': '#E1D5ED', 'Light Bluish Gray': '#A0A5A9',
       'Light Nougat': '#F6D7B3', 'Lime': '#BBE90B', 'Magenta': '#923978', 'Medium Lavender': '#AC78BA', 'Orange': '#FE8A18',
       'Pearl Gold': '#AA7F2E', 'Red': '#C91A09', 'Reddish Brown': '#582A12', 'Sand Green': '#A0BCAC', 'Tan': '#E4CD9E',
       'White': '#F4F4F4', 'Yellow': '#F2CD37', 'Yellowish Green': '#DFEEA5', 'Dark Red': '#720E0F'}
st = json.load(open(os.path.join(ROOT, 'lego', 'steps.json')))
for k, lst in st['lists'].items():
    for p in lst: p['hex'] = HEX.get(p['colour'], '#888888')
open(os.path.join(ROOT, 'docs', 'data', 'steps.js'), 'w').write('window.STEPS=' + json.dumps(st, separators=(',', ':')) + ';')
pl = json.load(open(os.path.join(ROOT, 'print', 'plates.json')))
slim = [{k: p[k] for k in ('id', 'file', 'title', 'material', 'parts', 'estimate') if k in p} for p in pl]
open(os.path.join(ROOT, 'docs', 'data', 'plates.js'), 'w').write('window.PLATES=' + json.dumps(slim, separators=(',', ':')) + ';')
import csv, collections
P = json.load(open(os.path.join(ROOT, 'lego', 'placements.json')))
names = {(p['part'], p['colour']): p['name'] for lst in st['lists'].values() for p in lst}
step_of = st['steps']
agg = collections.OrderedDict()
for i, p in enumerate(P):
    k = (p['part'], p['colour'], p['group'], p['role'])
    a = agg.setdefault(k, {'n': 0, 'steps': set()}); a['n'] += 1; a['steps'].add(step_of[i])
with open(os.path.join(ROOT, 'lego', 'parts_usage.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['part', 'colour', 'name', 'quantity', 'group', 'role', 'assembly steps'])
    for (part, col, grp, role), a in sorted(agg.items(), key=lambda kv: (min(kv[1]['steps']), kv[0][2], kv[0][0])):
        w.writerow([part, col, names.get((part, col), ''), a['n'], grp, role, ' '.join(str(s) for s in sorted(a['steps']))])
print('steps.js, plates.js and parts_usage.csv written')
