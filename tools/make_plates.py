"""Arrange the printed parts on Prusa CORE One plates and write PrusaSlicer project 3MFs.

Each 3MF carries the full CORE One HF0.4 printer, print and filament settings for that plate
(from the PrusaSlicer bundle, with this project's changes) and per-object settings such as the
fuzzy-skin bark on the trunk and branches, with modifiers that keep every joint smooth.

usage: python tools/make_plates.py [path/to/PrusaResearch.ini]
       -> print/plates/*.3mf, print/stl/*.stl, print/plates.json
"""
import json, math, os, shutil, sys, zipfile
import numpy as np, trimesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nest
from prusa_config import load, resolve

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FC = os.path.join(ROOT, 'cad', 'out'); PR = os.path.join(ROOT, 'print')
BUNDLE = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('PRUSA_BUNDLE', '')
BW, BH = 250.0, 220.0
ANCH = json.load(open(os.path.join(FC, 'anchors.json')))

# ------------------------------------------------------------------ materials and settings
PRINTER = 'Prusa CORE One HF0.4 nozzle'
PRINT = '0.20mm BALANCED @COREONE HF0.4'
MATERIALS = {
    'PLA':       dict(base='Generic PLA @COREONE HF0.4', name='eSUN PLA+ Bone White', colour='#EDE4D3',
                      cfg=dict(temperature=220, first_layer_temperature=225, bed_temperature=60, first_layer_bed_temperature=60,
                               filament_vendor='eSUN', filament_type='PLA')),
    'TPU black': dict(base='Prusament TPU 95A @COREONE', name='TPU 95A Black', colour='#202020',
                      cfg=dict(temperature=230, first_layer_temperature=230, bed_temperature=55, first_layer_bed_temperature=55, filament_type='FLEX')),
    'TPU clear': dict(base='Prusament TPU 95A @COREONE', name='TPU 95A Clear', colour='#D8E8EC',
                      cfg=dict(temperature=235, first_layer_temperature=235, bed_temperature=55, first_layer_bed_temperature=55, filament_type='FLEX')),
}
COMMON = dict(support_material=0, support_material_auto=0, seam_position='aligned', bottom_solid_layers=4)
FUZZY = dict(fuzzy_skin='external', fuzzy_skin_thickness=0.3, fuzzy_skin_point_dist=0.7)

def part(name):
    m = trimesh.load(os.path.join(FC, name + '.stl'))
    m.apply_translation([-(m.bounds[0][0] + m.bounds[1][0]) / 2, -(m.bounds[0][1] + m.bounds[1][1]) / 2, -m.bounds[0][2]])
    return m

def smooth_zones(name, m_raw):
    """Modifier meshes (in the part's own print coordinates, before centring) where fuzzy skin is switched off."""
    zones = []
    if name == 'Trunk':
        for am in ANCH['arms']:
            s = trimesh.creation.icosphere(2, 17.0); s.apply_translation(am['face_c']); zones.append(s)
        s = trimesh.creation.icosphere(2, 9.0); s.apply_translation(ANCH['trunk_top']); zones.append(s)
    if name.startswith('Branch'):
        i = int(name[-1]) - 1; am = ANCH['arms'][i]
        b = trimesh.creation.box([14, 40, 12]); b.apply_translation([5, 0, 4.5]); zones.append(b)       # root end: flat face, key, pin and axle holes
        s = trimesh.creation.icosphere(2, 9.0); s.apply_translation([am['L'], am['rise'], 4.5]); zones.append(s)   # tip cross hole
    return zones

# ------------------------------------------------------------------ plates
def single(name, x=BW / 2, y=BH / 2, ang=0.0): return [(name, ang, x, y)]
def nested(names, bw=236, bh=206, step=10):
    nest.BW, nest.BH = bw, bh
    r, _ = nest.place(names, [math.radians(a) for a in range(0, 360, step)])
    if r is None: raise RuntimeError('nesting failed for ' + ', '.join(names))
    items = []
    for o in r:
        m = part(o['name']); m.apply_transform(rot(o['ang'], 0, 0)); lo = m.bounds[0]
        items.append((o['name'], o['ang'], o['x'] - lo[0], o['y'] - lo[1]))
    b = np.array([placed(n, a, x, y).bounds for n, a, x, y in items])
    off = (np.array([BW, BH]) - (b[:, 1, :2].max(0) - b[:, 0, :2].min(0))) / 2 - b[:, 0, :2].min(0)
    return [(n, a, x + off[0], y + off[1]) for n, a, x, y in items]
def stack(names, gap=7.0):
    ms = [part(n) for n in names]; tot = sum(m.extents[1] for m in ms) + gap * (len(ms) - 1)
    y = (BH - tot) / 2; out = []
    for n, m in zip(names, ms):
        out.append((n, 0.0, BW / 2, y + m.extents[1] / 2)); y += m.extents[1] + gap
    return out
def rot(ang, dx, dy):
    c, s = math.cos(ang), math.sin(ang); M = np.eye(4); M[:2, :2] = [[c, -s], [s, c]]; M[0, 3] = dx; M[1, 3] = dy; return M
def placed(n, a, x, y):
    m = part(n); m.apply_transform(rot(a, x, y)); return m

small = [('Foot', 0.0, 125 - 62.5 + 25 * i, 95.0) for i in range(6)] + [('JointSleeve', 0.0, 125 - 50 + 25 * i, 125.0) for i in range(5)]
PLATES = [
    dict(id='01', slug='fit-kit-pla', title='Fit-test kit, PLA (FT1-FT5)', mat='PLA', items=stack(['FT1_FloorPegs', 'FT2_VerticalHoles', 'FT3_BranchRoot', 'FT4_StubFace', 'FT5_FootPockets']),
         cfg=dict(perimeters=3, fill_density='25%', fill_pattern='gyroid', top_solid_layers=5)),
    dict(id='02', slug='fit-kit-tpu-black', title='Fit-test kit, black TPU (FT6)', mat='TPU black', items=single('FT6_SoilMat'),
         cfg=dict(perimeters=3, fill_density='100%', fill_pattern='rectilinear', top_solid_layers=5)),
    dict(id='03', slug='fit-kit-tpu-clear', title='Fit-test kit, clear TPU (FT7)', mat='TPU clear', items=single('FT7_Sleeves'),
         cfg=dict(perimeters=3, fill_density='100%', fill_pattern='rectilinear', top_solid_layers=5)),
    dict(id='04', slug='planter', title='Planter', mat='PLA', items=single('Planter'),
         cfg=dict(perimeters=3, fill_density='15%', fill_pattern='gyroid', top_solid_layers=5)),
    dict(id='05', slug='trunk', title='Trunk', mat='PLA', items=single('Trunk'), fuzzy=True,
         cfg=dict(perimeters=4, fill_density='25%', fill_pattern='gyroid', top_solid_layers=5, brim_width=5, brim_type='outer_only')),
    dict(id='06', slug='branches', title='Branches 1-5', mat='PLA', items=nested(['Branch1', 'Branch2', 'Branch3', 'Branch4', 'Branch5']), fuzzy=True,
         cfg=dict(perimeters=4, fill_density='25%', fill_pattern='gyroid', top_solid_layers=5)),
    dict(id='07', slug='soil-core', title='Soil core', mat='PLA', items=single('SoilCore'),
         cfg=dict(perimeters=2, fill_density='15%', fill_pattern='gyroid', top_solid_layers=4)),
    dict(id='08', slug='soil-mat', title='Soil mat', mat='TPU black', items=single('SoilMat'),
         cfg=dict(perimeters=3, fill_density='100%', fill_pattern='rectilinear', top_solid_layers=4)),
    dict(id='09', slug='feet-and-sleeves', title='Feet x6 and joint sleeves x5', mat='TPU clear', items=small,
         cfg=dict(perimeters=3, fill_density='100%', fill_pattern='rectilinear', top_solid_layers=5)),
]

# ------------------------------------------------------------------ 3MF writer (PrusaSlicer project flavour)
def config_text(P, secs):
    mat = MATERIALS[P['mat']]
    cfg = {}
    cfg.update(resolve(secs, 'printer', PRINTER)); cfg.update(resolve(secs, 'print', PRINT)); cfg.update(resolve(secs, 'filament', mat['base']))
    for k in ('compatible_printers_condition', 'compatible_prints_condition', 'renamed_from', 'alias', 'inherits'): cfg.pop(k, None)
    cfg.update({k: str(v) for k, v in COMMON.items()}); cfg.update({k: str(v) for k, v in P['cfg'].items()}); cfg.update({k: str(v) for k, v in mat['cfg'].items()})
    cfg.update(printer_settings_id=PRINTER, print_settings_id=PRINT, filament_settings_id=f'"{mat["name"]}"',
               inherits_group=f'"{PRINT}";"{mat["base"]}";"{PRINTER}"', filament_colour=f'"{mat["colour"]}"', extruder_colour='""')
    return cfg

def write_3mf(P, path, secs):
    objs = []
    for k, (n, a, x, y) in enumerate(P['items']):
        m = trimesh.load(os.path.join(FC, n + '.stl'))
        c = np.array([-(m.bounds[0][0] + m.bounds[1][0]) / 2, -(m.bounds[0][1] + m.bounds[1][1]) / 2, -m.bounds[0][2]])
        vols = [('part', m)]
        if P.get('fuzzy'):
            vols += [('mod', z) for z in smooth_zones(n, m)]
        objs.append((n, a, x, y, c, vols))
    X = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:slic3rpe="http://schemas.slic3r.org/3mf/2017/06">',
         '<metadata name="slic3rpe:Version3mf">1</metadata>', f'<metadata name="Title">Sakura Planter - {P["title"]}</metadata>', '<resources>']
    C = ['<?xml version="1.0" encoding="UTF-8"?>', '<config>']
    for oid, (n, a, x, y, c, vols) in enumerate(objs, 1):
        X.append(f'<object id="{oid}" type="model"><mesh><vertices>')
        tris, first, off = [], 0, 0; vinfo = []
        for kind, m in vols:
            v = m.vertices + c
            X.extend(f'<vertex x="{p[0]:.4f}" y="{p[1]:.4f}" z="{p[2]:.4f}"/>' for p in v)
            tris.append(m.faces + off); vinfo.append((kind, first, first + len(m.faces) - 1)); first += len(m.faces); off += len(v)
        X.append('</vertices><triangles>')
        X.extend(f'<triangle v1="{t[0]}" v2="{t[1]}" v3="{t[2]}"/>' for t in np.vstack(tris))
        X.append('</triangles></mesh></object>')
        label = n if len(objs) == 1 else f'{n} {oid}'
        C.append(f'<object id="{oid}" instances_count="1"><metadata type="object" key="name" value="{label}"/>')
        if P.get('fuzzy'):
            C.extend(f'<metadata type="object" key="{k}" value="{v}"/>' for k, v in FUZZY.items())
        for j, (kind, f0, f1) in enumerate(vinfo):
            C.append(f'<volume firstid="{f0}" lastid="{f1}">')
            if kind == 'part':
                C.append(f'<metadata type="volume" key="name" value="{n}"/><metadata type="volume" key="volume_type" value="ModelPart"/>')
            else:
                C.append(f'<metadata type="volume" key="name" value="smooth joint {j}"/><metadata type="volume" key="volume_type" value="ParameterModifier"/>'
                         '<metadata type="volume" key="modifier" value="1"/><metadata type="volume" key="fuzzy_skin" value="none"/>')
            C.append('<metadata type="volume" key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>')
            C.append('<mesh edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/></volume>')
        C.append('</object>')
    X.append('</resources><build>')
    for oid, (n, a, x, y, c, vols) in enumerate(objs, 1):
        cs, sn = math.cos(a), math.sin(a)
        X.append(f'<item objectid="{oid}" transform="{cs:.6f} {sn:.6f} 0 {-sn:.6f} {cs:.6f} 0 0 0 1 {x:.4f} {y:.4f} 0" printable="1"/>')
    X.append('</build></model>'); C.append('</config>')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
                   '<Default Extension="png" ContentType="image/png"/></Types>')
        z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model', '\n'.join(X))
        z.writestr('Metadata/Slic3r_PE_model.config', '\n'.join(C))
        if secs:
            cfg = config_text(P, secs)
            z.writestr('Metadata/Slic3r_PE.config', '; generated by sakuraPlanter tools/make_plates.py\n' + ''.join(f'; {k} = {cfg[k]}\n' for k in sorted(cfg)))

def main():
    secs = load(BUNDLE) if BUNDLE and os.path.exists(BUNDLE) else None
    if secs is None: print('no PrusaSlicer bundle given: 3MFs carry geometry and per-object settings only')
    os.makedirs(os.path.join(PR, 'plates'), exist_ok=True); os.makedirs(os.path.join(PR, 'stl'), exist_ok=True)
    for f in os.listdir(os.path.join(PR, 'plates')):
        if f.endswith('.3mf'): os.remove(os.path.join(PR, 'plates', f))
    summary = []
    for P in PLATES:
        ms = [placed(n, a, x, y) for n, a, x, y in P['items']]
        b = trimesh.util.concatenate(ms).bounds
        assert b[0][0] >= 0 and b[0][1] >= 0 and b[1][0] <= BW and b[1][1] <= BH and b[1][2] <= 270, (P['title'], b)
        fn = f"{P['id']}_{P['slug']}.3mf"
        write_3mf(P, os.path.join(PR, 'plates', fn), secs)
        summary.append(dict(id=P['id'], file='plates/' + fn, title=P['title'], material=MATERIALS[P['mat']]['name'], mat=P['mat'],
                            parts=[n for n, *_ in P['items']], fuzzy=bool(P.get('fuzzy')), settings=P['cfg'],
                            items=[[n, round(a, 5), round(x, 3), round(y, 3)] for n, a, x, y in P['items']],
                            bbox=np.round(b, 1).tolist(), volume_cm3=round(sum(m.volume for m in ms) / 1000, 2)))
        print(fn, np.round(b[:, :2], 1).tolist(), 'h', round(b[1][2], 1))
    for n in ['Planter', 'SoilCore', 'SoilMat', 'Trunk', 'Branch1', 'Branch2', 'Branch3', 'Branch4', 'Branch5', 'Foot', 'JointSleeve',
              'FT1_FloorPegs', 'FT2_VerticalHoles', 'FT3_BranchRoot', 'FT4_StubFace', 'FT5_FootPockets', 'FT6_SoilMat', 'FT7_Sleeves']:
        shutil.copy(os.path.join(FC, n + '.stl'), os.path.join(PR, 'stl', n + '.stl'))
    old = {}
    if os.path.exists(os.path.join(PR, 'plates.json')):
        old = {p['id']: p for p in json.load(open(os.path.join(PR, 'plates.json')))}
    for s in summary:                     # keep slicer estimates from an earlier tools/slice_plates.py run
        if s['id'] in old and 'estimate' in old[s['id']]: s['estimate'] = old[s['id']]['estimate']
    json.dump(summary, open(os.path.join(PR, 'plates.json'), 'w'), indent=1)

if __name__ == '__main__':
    main()
