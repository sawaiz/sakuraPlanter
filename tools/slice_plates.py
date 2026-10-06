"""Slice every plate headlessly with the PrusaSlicer CLI and record print time and filament.

The plates' own embedded settings are used; only the printer's custom G-code templates are swapped
for minimal ones (older CLI builds can't parse the CORE One templates), so times exclude the
~3 min start sequence (homing, bed levelling, purge).
usage: python tools/slice_plates.py [prusa-slicer]     -> adds 'estimate' to print/plates.json
       ONLY=01,05 python tools/slice_plates.py              (re-slice some plates)
"""
import json, os, re, subprocess, sys, tempfile, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PS = sys.argv[1] if len(sys.argv) > 1 else 'prusa-slicer'
OVR = {'start_gcode': 'G28', 'end_gcode': 'M84', 'before_layer_gcode': 'G92 E0', 'layer_gcode': '', 'toolchange_gcode': '',
       'between_objects_gcode': '', 'color_change_gcode': 'M600', 'pause_print_gcode': 'M601', 'template_custom_gcode': '',
       'start_filament_gcode': '"; start filament"', 'end_filament_gcode': '"; end filament"', 'binary_gcode': '0'}

def embedded_config(path):
    with zipfile.ZipFile(path) as z:
        txt = z.read('Metadata/Slic3r_PE.config').decode()
    cfg = {}
    for line in txt.splitlines():
        m = re.match(r'^; (\w+) = (.*)$', line)
        if m: cfg[m.group(1)] = m.group(2)
    return cfg

def parse_time(s):
    t = 0
    for v, u in re.findall(r'(\d+)([dhms])', s): t += int(v) * {'d': 86400, 'h': 3600, 'm': 60, 's': 1}[u]
    return t

VERSION = ''
def main():
    global VERSION
    VERSION = subprocess.run([PS, '--help'], capture_output=True, text=True).stdout.splitlines()[0].split(' based')[0].replace('+UNKNOWN', '')
    plates = json.load(open(os.path.join(ROOT, 'print', 'plates.json')))
    tmp = tempfile.mkdtemp()
    only = [x for x in os.environ.get('ONLY', '').split(',') if x]
    for P in plates:
        if only and P['id'] not in only: continue
        src = os.path.join(ROOT, 'print', P['file'])
        cfg = embedded_config(src); cfg.update(OVR)
        ini = os.path.join(tmp, P['id'] + '.ini')
        open(ini, 'w').write(''.join(f'{k} = {v}\n' for k, v in cfg.items()))
        out = os.path.join(tmp, P['id'] + '.gcode')
        r = subprocess.run([PS, '--export-gcode', '--load', ini, '-o', out, src], capture_output=True, text=True, timeout=3600)
        if not os.path.exists(out):
            print(P['id'], 'FAILED', r.stdout[-800:], r.stderr[-800:]); continue
        g = open(out, errors='replace').read()
        tm = re.search(r'estimated printing time \(normal mode\) = (.*)', g).group(1).strip()
        grams = float(re.search(r'total filament used \[g\] = ([\d.]+)', g).group(1))
        metres = float(re.search(r'filament used \[mm\] = ([\d.]+)', g).group(1)) / 1000
        P['estimate'] = {'time': tm, 'seconds': parse_time(tm), 'grams': round(grams, 1), 'metres': round(metres, 2),
                         'layers': g.count(';LAYER_CHANGE'), 'slicer': VERSION}
        print(P['id'], P['title'], tm, f'{grams:.1f} g')
    json.dump(plates, open(os.path.join(ROOT, 'print', 'plates.json'), 'w'), indent=1)

if __name__ == '__main__':
    main()
