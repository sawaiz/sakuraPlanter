"""Place every LEGO piece on the printed parts, relax overlaps, check the build, export the model.

Run after the FreeCAD macro has written cad/out/:
    python pipeline/run_pipeline.py
Outputs: lego/placements.json, lego/steps.json, lego/verify_report.json, lego/sakura_planter.mpd,
         docs/data/viewer_data.js   (work files in pipeline/work/, LDraw parts cached in pipeline/.ldcache/)
"""
import json, os, shutil, subprocess, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
FC = os.path.join(ROOT, 'cad', 'out'); W = os.path.join(HERE, 'work')
PLA, MODEL = os.path.join(W, 'pla'), os.path.join(W, 'model')
PY = sys.executable

def run(*args):
    t = time.time(); print('>', ' '.join(os.path.relpath(a, ROOT) if os.path.isabs(a) else a for a in args), flush=True)
    r = subprocess.run([PY, *args], cwd=HERE, capture_output=True, text=True)
    if r.returncode: print(r.stdout[-3000:], r.stderr[-3000:]); raise SystemExit(r.returncode)
    print('  ', (r.stdout.strip().splitlines() or [''])[-1][:160], f'({time.time() - t:.0f} s)', flush=True)

def accumulate(prev, new, out):
    a = json.load(open(prev)); b = json.load(open(new))
    for x, y in zip(a, b):
        y['moved_mm'] = round(float(np.linalg.norm(np.array(y['p']) - np.array(x['p'])) + x.get('moved_mm', 0)), 2)
    json.dump(b, open(out, 'w'))

def main():
    os.makedirs(PLA, exist_ok=True); os.makedirs(MODEL, exist_ok=True)
    for src, dst in [('Planter_world.stl', 'sakura_planter.stl'), ('SoilPlate_world.stl', 'sakura_soil_plate.stl'),
                     ('Trunk_world.stl', 'sakura_trunk.stl'), ('anchors.json', 'anchors.json')] + \
                    [(f'Branch{i}.stl', f'sakura_branch_{i}.stl') for i in range(1, 6)]:
        shutil.copy(os.path.join(FC, src), os.path.join(PLA, dst))
    m = lambda f: os.path.join(MODEL, f)
    run('build.py', MODEL, PLA)
    run('steps_map.py', m('placements.json'), os.path.join(ROOT, 'lego', 'parts_inventory.xlsx'), m('steps.json'))
    run('verify.py', m('placements.json'), m('steps.json'), PLA, m('verify_start.json'))      # also caches voxel templates
    cur = m('placements.json')
    for k in (1, 2, 3):
        run('relax.py', cur, PLA, m('voxel_templates_eroded.pkl'), m(f'relaxed{k}.json'))
        accumulate(cur, m(f'relaxed{k}.json'), m(f'placements_r{k}.json')); cur = m(f'placements_r{k}.json')
    run('verify.py', cur, m('steps.json'), PLA, m('verify.json'))
    os.makedirs(os.path.join(W, 'final'), exist_ok=True)
    shutil.copy(cur, os.path.join(W, 'final', 'placements.json'))
    env = dict(os.environ, FCOUT=FC)
    r = subprocess.run([PY, 'export.py', os.path.join(W, 'final'), PLA, os.path.join(W, 'export')], cwd=HERE, env=env, capture_output=True, text=True)
    if r.returncode: print(r.stderr[-3000:]); raise SystemExit(1)
    print('  ', r.stdout.strip().splitlines()[-1])
    lego, data = os.path.join(ROOT, 'lego'), os.path.join(ROOT, 'docs', 'data')
    os.makedirs(data, exist_ok=True)
    shutil.copy(cur, os.path.join(lego, 'placements.json'))
    shutil.copy(m('steps.json'), os.path.join(lego, 'steps.json'))
    shutil.copy(m('verify.json'), os.path.join(lego, 'verify_report.json'))
    shutil.copy(os.path.join(W, 'export', 'sakura_planter.mpd'), os.path.join(lego, 'sakura_planter.mpd'))
    shutil.copy(os.path.join(W, 'export', 'viewer_data.js'), os.path.join(data, 'viewer_data.js'))
    v = json.load(open(m('verify.json')))
    print(f"done: {v['parts']} pieces, {v['n_clash']} overlaps >= 4 mm3, {v['n_tight']} near-touches, {len(v['floating'])} floating")

if __name__ == '__main__':
    main()
