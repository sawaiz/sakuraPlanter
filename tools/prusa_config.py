"""Flatten PrusaSlicer bundle presets (printer + print + filament) into one .ini, with overrides.

Used to slice the plates headlessly for time / filament estimates and to check the 3MF files load.
usage: prusa_config.py <PrusaResearch.ini> <out.ini> printer=NAME print=NAME filament=NAME [key=value ...]
"""
import re, sys

def load(path):
    txt = open(path, encoding='utf-8').read() + '\n['
    secs = {}
    for m in re.finditer(r'^\[([^\]\n]+)\]\n(.*?)(?=^\[)', txt, re.S | re.M):
        d = {}
        for line in m.group(2).splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k, v = line.split('=', 1); d[k.strip()] = v.strip()
        secs[m.group(1)] = d
    return secs

def resolve(secs, kind, name, depth=0):
    d = secs.get(f'{kind}:{name}')
    if d is None: raise KeyError(f'{kind}:{name}')
    out = {}
    for par in [p.strip().strip('"') for p in d.get('inherits', '').split(';') if p.strip()]:
        out.update(resolve(secs, kind, par, depth + 1))
    out.update({k: v for k, v in d.items() if k != 'inherits'})
    return out

def main():
    src, dst = sys.argv[1], sys.argv[2]
    args = dict(a.split('=', 1) for a in sys.argv[3:])
    secs = load(src)
    cfg = {}
    for kind in ('printer', 'print', 'filament'):
        cfg.update(resolve(secs, kind, args.pop(kind)))
    cfg.update(args)
    for k in ('compatible_printers_condition', 'compatible_prints_condition', 'renamed_from', 'alias', 'inherits'):
        cfg.pop(k, None)
    with open(dst, 'w') as f:
        for k in sorted(cfg): f.write(f'{k} = {cfg[k]}\n')
    print(dst, len(cfg), 'keys')

if __name__ == '__main__':
    main()
