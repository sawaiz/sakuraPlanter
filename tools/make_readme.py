"""Write README.md from the project data, so the numbers and lists in it stay in step with the files.

Sources: docs/data/guide.js (step text), lego/steps.json (parts lists), print/plates.json (plates and slicer
estimates), lego/verify_report.json (fit checks), cad/out/anchors.json (parameters).
usage: python tools/make_readme.py
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def jsvar(path): t = open(os.path.join(ROOT, path)).read(); return json.loads(t[t.index('=') + 1:].rstrip().rstrip(';'))
GUIDE = jsvar('docs/data/guide.js')['steps']
LISTS = json.load(open(os.path.join(ROOT, 'lego', 'steps.json')))['lists']
PLATES = json.load(open(os.path.join(ROOT, 'print', 'plates.json')))
V = json.load(open(os.path.join(ROOT, 'lego', 'verify_report.json')))
PRM = json.load(open(os.path.join(ROOT, 'cad', 'out', 'anchors.json')))['params']
PAGES = 'https://sawaiz.github.io/sakuraPlanter/'

def hm(sec):
    h, m = divmod(round(sec / 60), 60); return f'{h} h {m:02d} min' if h else f'{m} min'
tot_s = sum(p['estimate']['seconds'] for p in PLATES)
model_s = sum(p['estimate']['seconds'] for p in PLATES if not p['id'] in ('01', '02', '03'))
grams = {}
for p in PLATES: grams[p['mat']] = grams.get(p['mat'], 0) + p['estimate']['grams']
pla, tpub, tpuc = grams.get('PLA', 0), grams.get('TPU black', 0), grams.get('TPU clear', 0)
lego_n = V['parts']
clash = [c for c in V['clashes'] if c['sev'] == 'clash']
printed_clash = [c for c in clash if c['a'] >= lego_n or c['b'] >= lego_n]
unsup = {k: len(v) for k, v in V['step_unsupported'].items() if v}
bl = V['branch_loads']

def plates_table():
    rows = ['| Plate | Parts | Material | Time | Filament | Settings that differ from the preset |', '|---|---|---|---|---|---|']
    for p in PLATES:
        s = p.get('settings', {})
        bits = [f"{s.get('perimeters')} perimeters", f"{s.get('fill_density')} {s.get('fill_pattern')}"]
        if s.get('brim_width'): bits.append(f"{s['brim_width']} mm brim")
        if p.get('fuzzy'): bits.append('fuzzy skin (joints kept smooth)')
        e = p['estimate']
        rows.append(f"| [{p['id']}](print/{p['file']}) | {p['title']} | {p['material']} | {hm(e['seconds'])} | {e['grams']:.0f} g | {', '.join(bits)} |")
    return '\n'.join(rows)

def plate_gallery():
    cells = [f'<td align="center"><img src="images/plates/plate_{p["id"]}.jpg" width="260" alt="Plate {p["id"]}: {p["title"]}"><br><sub>{p["id"]}: {p["title"]}</sub></td>' for p in PLATES]
    rows = [''.join(cells[i:i + 3]) for i in range(0, len(cells), 3)]
    return '<table>\n' + '\n'.join(f'<tr>{r}</tr>' for r in rows) + '\n</table>'

def parts_list(k):
    L = LISTS.get(str(k), [])
    if not L: return ''
    n = sum(p['n'] for p in L)
    rows = '\n'.join(f"| {p['n']} | {p['colour']} | {p['name']} | `{p['part']}` |" for p in L)
    return f"\n<details><summary>LEGO pieces for this step ({n})</summary>\n\n| Qty | Colour | Part | ID |\n|---:|---|---|---|\n{rows}\n\n</details>\n"

def steps_md():
    out = []
    for s in GUIDE:
        head = f"### {s['label']}: {s['title']}" if not s['label'].startswith('Step') else f"### {s['label']}. {s['title']}"
        body = '\n\n'.join(s['body'])
        tips = ''.join(f'\n- {t}' for t in s.get('tips', []))
        img = f'<img src="images/steps/{s["id"]}.jpg" width="560" alt="{s["label"]}: {s["title"]}">'
        out.append(f"{head}\n\n{img}\n\n{body}\n{tips}\n{parts_list(s['lego']) if s.get('lego') else ''}")
    return '\n'.join(out)

FITS = [('FT1 Floor pegs', 'PLA', 'cross pegs standing on a plate, like the planter floor', '`peg_w`, `peg_t`', 'a dark green 3L connector pushes on and stays on upside down'),
        ('FT2 Vertical holes, row 1', 'PLA', 'cross holes', '`axle_w`, `axle_t`', 'a LEGO axle slides in with light friction and does not fall out'),
        ('FT2 Vertical holes, row 2', 'PLA', 'round pin holes', '`pin_d`', 'a black friction pin pushes in firmly and turns stiffly'),
        ('FT2 Vertical holes, row 3', 'PLA', 'small round holes (not used by the current parts; there for remixes)', '`bar_d`', 'a 3.18 mm LEGO bar pushes in and holds'),
        ('FT3 Branch root, front', 'PLA', 'pin holes printed sideways, like the branch roots', '`hpin_d`', 'a 3L pin\'s 2L end pushes in firmly'),
        ('FT3 Branch root, back', 'PLA', 'cross holes printed sideways', '`haxle_w`, `haxle_t`', 'a 2L axle pushes in with light friction'),
        ('FT4 Stub face', 'PLA', 'sleeve pockets and cross holes on a 45° face, like the trunk stubs', '`sleeve_pocket_d` (pockets), `axle_w`, `axle_t` (holes)', 'a clear sleeve presses in with your thumb and stays; an axle slides in'),
        ('FT5 Foot pockets', 'PLA', 'pockets on the underside, like the planter', '`foot_pocket_d`', 'a clear foot presses in and stays'),
        ('FT6 Soil mat', 'black TPU', 'stem pegs and axle pass-throughs at mat thickness', '`tpu_peg_w`, `tpu_peg_t` (pegs), `tpu_axle_w`, `tpu_axle_t` (holes)', 'a 3L connector pushes on and has to be pulled off; a 32L axle slides through and stays where you leave it'),
        ('FT7 Sleeves', 'clear TPU', 'seven sleeves on a numbered web, plus two feet', '`sleeve_id`', 'the stop bush of a 3L pin pushes in and the pin can\'t wobble')]
def fits_md():
    rows = ['| Piece | Material | What it copies | Parameter(s) | A good fit |', '|---|---|---|---|---|']
    rows += [f'| {a} | {b} | {c} | {d} | {e} |' for a, b, c, d, e in FITS]
    return '\n'.join(rows)

PARAM_ROWS = [('peg_w × peg_t', 'Floor cross peg (PLA)', 'into a 3L connector'), ('axle_w × axle_t', 'Cross hole, vertical or angled (trunk channels, stubs, twig holes)', 'LEGO axle 4.8 × 1.8'),
              ('pin_d', 'Pin hole, vertical (branch spur holes)', 'Technic pin 4.8'), ('hpin_d', 'Pin hole, horizontal (branch roots)', 'Technic pin 4.8'),
              ('haxle_w × haxle_t', 'Cross hole, horizontal (branch roots and tips)', 'LEGO axle'), ('bar_d', 'Bar hole (PLA; fit test only, for remixes)', 'LEGO bar 3.18'),
              ('tpu_peg_w × tpu_peg_t', 'Stem peg (black TPU)', 'into a 3L connector'), ('tpu_axle_w × tpu_axle_t', 'Axle pass-through (black TPU)', '32L axle'),
              ('foot_d / foot_pocket_d', 'Foot in its pocket', 'clear TPU into PLA'), ('sleeve_od / sleeve_pocket_d', 'Sleeve in the stub', 'clear TPU into PLA'),
              ('sleeve_id', 'Sleeve on the pin bush', 'stop bush ≈ 7.2'), ('key_d / key_hole_d', 'Branch key', 'PLA pin in PLA hole'), ('soil_gap', 'Soil plate to planter wall', 'clearance')]
def pval(expr):
    return ' × '.join(' / '.join(str(PRM[k.strip()]) for k in part.split('/')) for part in expr.split('×'))
def params_md():
    rows = ['| Parameter | Joint | Mates with | Value (mm) |', '|---|---|---|---:|']
    rows += [f'| `{a}` | {b} | {c} | {pval(a)} |' for a, b, c in PARAM_ROWS]
    return '\n'.join(rows)

clash_groups = {}
for c in clash:
    g = c['a_label'].split('(')[1].split(':')[0]; clash_groups[g] = clash_groups.get(g, 0) + 1
def role(label):
    m = re.match(r'(.+?) (\w+) \((\w[\w ]*): (.+?)(?: \(original.*)?\)$', label)
    return f'{m.group(1).lower()} {m.group(4).lower()} ({m.group(2)})' if m else label
top_groups = ', '.join(f'{g.lower()} {n}' for g, n in sorted(clash_groups.items(), key=lambda kv: -kv[1])[:4])

T = open(os.path.join(ROOT, 'tools', 'README.template.md')).read()
ctx = {
    'PAGES': PAGES, 'LEGO_N': f'{lego_n:,}', 'TOT_H': f'{tot_s / 3600:.0f}', 'MODEL_H': f'{model_s / 3600:.0f}', 'PLA_G': f'{pla:.0f}', 'TPUB_G': f'{tpub:.0f}', 'TPUC_G': f'{tpuc:.0f}',
    'PLATES_TABLE': plates_table(), 'PLATE_GALLERY': plate_gallery(), 'STEPS': steps_md(), 'FITS': fits_md(), 'PARAMS': params_md(),
    'N_CLASH': str(V['n_clash']), 'N_TIGHT': str(V['n_tight']), 'TOP_GROUPS': top_groups, 'COM': f"{V['com_offset_mm']:.1f}",
    'BL_MIN': f"{min(b['mass_g'] for b in bl):.0f}", 'BL_MAX': f"{max(b['mass_g'] for b in bl):.0f}", 'MOM': f"{max(b['moment_Nmm'] for b in bl):.0f}",
    'LEGO_G': f"{V['mass_lego_g']:.0f}", 'MOTIF_DEPTH': str(PRM['motif_depth']),
    'PRINTED_CLASH': '; '.join(f"{role(c['a_label'])} against {c['b_label'].lower()} ({c['overlap_mm3']:.0f} mm³)" for c in printed_clash),
    'SLICER': PLATES[0]['estimate'].get('slicer', 'PrusaSlicer'),
}
for k, v in ctx.items(): T = T.replace('{{' + k + '}}', v)
left = re.findall(r'\{\{\w+\}\}', T)
assert not left, left
open(os.path.join(ROOT, 'README.md'), 'w').write(T)
print('README.md written,', len(T) // 1000, 'kB')
