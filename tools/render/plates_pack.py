"""Pack the plate layouts (print/plates.json + print/stl) for plates.html.  -> pipeline/work/render/plates_data.js"""
import json, math, os, base64
import numpy as np, trimesh
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COL = {'PLA': '#E2D5BC', 'TPU black': '#1C1C1C', 'TPU clear': '#CFE0E6'}
out = []
for P in json.load(open(os.path.join(ROOT, 'print', 'plates.json'))):
    ms = []
    for n, a, x, y in P['items']:
        m = trimesh.load(os.path.join(ROOT, 'print', 'stl', n + '.stl'))
        m.apply_translation([-(m.bounds[0][0] + m.bounds[1][0]) / 2, -(m.bounds[0][1] + m.bounds[1][1]) / 2, -m.bounds[0][2]])
        c, s = math.cos(a), math.sin(a); M = np.eye(4); M[:2, :2] = [[c, -s], [s, c]]; M[0, 3] = x; M[1, 3] = y
        m.apply_transform(M); ms.append(m)
    m = trimesh.util.concatenate(ms); tri = m.vertices[m.faces].reshape(-1, 3).astype(np.float32)
    out.append({'id': P['id'], 'mat': P['mat'], 'col': COL[P['mat']], 'h': float(m.bounds[1][2]), 'b': base64.b64encode(tri.tobytes()).decode()})
os.makedirs(os.path.join(ROOT, 'pipeline', 'work', 'render'), exist_ok=True)
open(os.path.join(ROOT, 'pipeline', 'work', 'render', 'plates_data.js'), 'w').write('window.PLATES=' + json.dumps(out) + ';')
print(len(out), 'plates packed')
