"""Render a realistic step-by-step assembly animation of one of the rebuilt sets with Blender (Cycles).

It reads the same data the web pages use (docs/sets/<set>/data/set.js): every part's mesh, colour and placement,
the steps, and the slide-in direction instrumentation/check.py worked out for each piece. Each step the new pieces
slide in along their direction and seat, the camera glides to frame what is built, and the finished model gets a
turntable at the end. Frames are PNGs with transparent backgrounds (a soft contact shadow stays in the alpha), so
render/make_video.sh can lay them over the set's page colour.

Run with Blender (4.2 or newer), or with the `bpy` module from pip:

    blender -b -P render/blender_anim.py -- --set 40725 --model branch_white --out render/frames/40725/branch_white
    python3 render/blender_anim.py --set 10280 --model daisy --out render/frames/10280/daisy --preview

Options: --res 1920x1080  --samples 128  --fps 30  --step-seconds 1.6  --turntable-seconds 5  --device auto|cpu|gpu
         --start N --end N  (render only these frames, to split a clip across machines)  --preview (480x270, 12 samples)
"""
import argparse, base64, json, math, os, sys
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
LDU = 0.0004                                     # metres per LDraw unit (0.4 mm)
HDRI = os.path.join(ROOT, 'docs', 'assets', 'studio_small_03_1k.hdr')
BG = {'cherry': '#D6EAF8', 'bouquet': '#898F95'}
METAL = {297, 334, 383}

def args():
    ap = argparse.ArgumentParser(); a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap.add_argument('--set', required=True); ap.add_argument('--model', default=''); ap.add_argument('--out', default='')
    ap.add_argument('--res', default='auto', help='WxH, or auto: 1920x1080, or 1080x1440 for tall thin models'); ap.add_argument('--samples', type=int, default=128); ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--step-seconds', type=float, default=1.6); ap.add_argument('--turntable-seconds', type=float, default=5.0)
    ap.add_argument('--device', default='auto'); ap.add_argument('--start', type=int, default=0); ap.add_argument('--end', type=int, default=-1)
    ap.add_argument('--preview', action='store_true'); ap.add_argument('--list', action='store_true', help='print the models and exit')
    return ap.parse_args(a)

# ---------------------------------------------------------------- data
def load_set(name):
    s = open(os.path.join(ROOT, 'docs', 'sets', name, 'data', 'set.js')).read()
    return json.loads(s[s.index('=') + 1:].rstrip().rstrip(';'))

def q16(o):
    if not o: return np.zeros((0, 3, 3))
    return (np.frombuffer(base64.b64decode(o['b']), dtype='<i2').astype(np.float64) / 32767 * o['s']).reshape(-1, 3, 3)

def srgb_to_linear(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def hex_rgb(h): h = h.lstrip('#'); return [srgb_to_linear(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)]

# ---------------------------------------------------------------- scene
def setup_render(a, theme):
    sc = bpy.context.scene; w, h = (480, 270) if a.preview or a.res == 'auto' else map(int, a.res.lower().split('x'))
    sc.render.engine = 'CYCLES'; sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.render.fps = a.fps; sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    cy = sc.cycles; cy.samples = 12 if a.preview else a.samples; cy.use_denoising = True; cy.max_bounces = 8; cy.diffuse_bounces = 3
    cy.glossy_bounces = 5; cy.transmission_bounces = 2; cy.sample_clamp_indirect = 10.0
    for n in ('Khronos PBR Neutral', 'AgX', 'Filmic', 'Standard'):          # the first one this Blender has; PBR Neutral keeps plastic colours true
        try: sc.view_settings.view_transform = n; break
        except TypeError: continue
    sc.view_settings.look = 'None'; sc.view_settings.exposure = -0.3
    # compute device: use whatever GPU is there unless told otherwise
    dev = 'CPU'
    if a.device != 'cpu':
        try:
            pref = bpy.context.preferences.addons['cycles'].preferences
            for kind in ('OPTIX', 'CUDA', 'HIP', 'METAL', 'ONEAPI'):
                try:
                    pref.compute_device_type = kind; pref.get_devices()
                    gpus = [d for d in pref.devices if d.type != 'CPU']
                    if gpus:
                        for d in pref.devices: d.use = d.type != 'CPU'
                        sc.cycles.device = 'GPU'; dev = f'{kind} ({", ".join(d.name for d in gpus)})'; break
                except Exception: continue
        except Exception: pass
    print('render device:', dev)
    return sc

def setup_world(sc):
    w = bpy.data.worlds.new('studio'); sc.world = w; w.use_nodes = True; nt = w.node_tree; nt.nodes.clear()
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(HDRI)
    mapn = nt.nodes.new('ShaderNodeMapping'); coord = nt.nodes.new('ShaderNodeTexCoord'); mapn.inputs['Rotation'].default_value[2] = math.radians(35)
    bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = 0.32; out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(coord.outputs['Generated'], mapn.inputs['Vector']); nt.links.new(mapn.outputs['Vector'], env.inputs['Vector'])
    nt.links.new(env.outputs['Color'], bg.inputs['Color']); nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    # a soft key light for crisp contact shadows on top of the studio lighting
    k = bpy.data.lights.new('key', 'AREA'); k.energy = 8; k.size = 0.25; ko = bpy.data.objects.new('key', k)
    ko.location = (-0.25, -0.3, 0.9); bpy.context.collection.objects.link(ko)
    tr = ko.constraints.new('TRACK_TO'); tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
    t = bpy.data.objects.new('aim', None); bpy.context.collection.objects.link(t); tr.target = t
    return t

def make_ground():
    bpy.ops.mesh.primitive_plane_add(size=6.0); g = bpy.context.active_object; g.name = 'ground'
    g.is_shadow_catcher = True; return g

def make_camera(sc):
    cam = bpy.data.cameras.new('cam'); cam.lens = 85; cam.sensor_width = 36; cam.clip_start = 0.01; cam.clip_end = 20
    co = bpy.data.objects.new('cam', cam); bpy.context.collection.objects.link(co); sc.camera = co; return co

_mats = {}
def material(code, S):
    if code in _mats: return _mats[code]
    hexc = S['colours'].get(str(code), ['#888888'])[0]; m = bpy.data.materials.new(f'c{code}'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = hex_rgb(hexc) + [1]
    if code in METAL: b.inputs['Metallic'].default_value = 1.0; b.inputs['Roughness'].default_value = 0.22
    else:
        b.inputs['Roughness'].default_value = 0.30
        for n, v in (('Coat Weight', 0.45), ('Coat Roughness', 0.08), ('Specular IOR Level', 0.55)):
            if n in b.inputs: b.inputs[n].default_value = v
    _mats[code] = m; return m

_meshes = {}
def part_mesh(pid, S):
    """One Blender mesh per part id: slot 0 takes the part's own colour, further slots hold faces with fixed colours."""
    if pid in _meshes: return _meshes[pid]
    g = S['geoms'][pid]; groups = [(None, q16(g.get('tri')))] + [(f['c'], q16(f['tri'])) for f in g.get('fixed', [])]
    bm = bmesh.new(); mats = []
    for gi, (code, T) in enumerate(groups):
        if code is not None: mats.append(code)
        for t in T:
            v = [bm.verts.new((p[0] * LDU, p[2] * LDU, -p[1] * LDU)) for p in t]
            try: f = bm.faces.new(v)
            except ValueError: continue
            f.material_index = gi
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=LDU * 0.02)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(pid); bm.to_mesh(me); bm.free()
    me.materials.append(None)
    for code in mats: me.materials.append(material(code, S))
    for p in me.polygons: p.use_smooth = True
    try: me.shade_smooth()
    except Exception: pass
    _meshes[pid] = me; return me

def make_instances(model, S, coll):
    """A Blender object per part, placed in its final position. Returns the list (same order as model['parts'])."""
    objs = []
    for pid, col, *m in model['parts']:
        o = bpy.data.objects.new(pid, part_mesh(pid, S)); coll.objects.link(o)
        o.material_slots[0].link = 'OBJECT'; o.material_slots[0].material = material(col, S)
        M = np.array(m[:9]).reshape(3, 3); t = np.array(m[9:12])
        # LDraw (x, y, z) -> Blender (x, z, -y): a proper rotation, so handedness is kept
        C = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)
        R = C @ M @ C.T; tt = C @ t * LDU
        o.matrix_world = Matrix([[*R[0], tt[0]], [*R[1], tt[1]], [*R[2], tt[2]], [0, 0, 0, 1]])
        o.hide_render = True; objs.append(o)
    return objs

# ---------------------------------------------------------------- animation
C = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)
def ease(t): t = min(1, max(0, t)); return 1 - (1 - t) ** 3

def plan(model, a):
    """Per step: units (part idx lists with a slide-in direction), start frame and the frame it is complete."""
    fps = a.fps; per = int(round(a.step_seconds * fps)); steps = []; f0 = int(0.5 * fps)
    for si, st in enumerate(model['steps']):
        units = []
        ins = {k: u for u in st.get('ins', []) for k in u['p']}; seen = set()
        for k in st['new']:
            if k in seen: continue
            u = ins.get(k); idx = list(u['p']) if u else [k]; seen.update(idx)
            d = np.array(u['d'], float) if u and u.get('k') not in ('blocked', 'first') else np.array([0, -1.0, 0])
            units.append((idx, C @ d / np.linalg.norm(d)))
        steps.append({'units': units, 'f0': f0, 'f1': f0 + per}); f0 += per
    return steps, f0

def frame_state(model, objs, steps, f, slide):
    """Show the parts of finished steps, and slide in the ones being fitted at frame f."""
    for o in objs: o.hide_render = True
    vis = []
    for st in steps:
        if f < st['f0']: break
        for ui, (idx, d) in enumerate(st['units']):
            t0 = st['f0'] + 0.35 * (st['f1'] - st['f0']) * ui / max(1, len(st['units']));     # pieces of one step arrive one after another
            if f < t0: continue                                                                # not arrived yet
            k = ease((f - t0) / (0.75 * (st['f1'] - st['f0']))) if f < st['f1'] else 1.0
            off = d * slide * (1 - k) * LDU
            for i in idx:
                o = objs[i]; o.hide_render = False; vis.append(i)
                o.location = Vector(o['rest']) + Vector(off)
    return vis

def bounds(objs, vis):
    """World-space box of the given parts in their finished positions."""
    P = np.array([c for i in vis for c in objs[i]['corners']]); return P.min(0), P.max(0)

def main():
    a = args(); S = load_set(a.set)
    if a.list: print(', '.join(k for k, v in S['models'].items() if v['steps'])); return
    model = S['models'][a.model]; theme = 'cherry' if a.set == '40725' else 'bouquet'
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = setup_render(a, theme); aim = setup_world(sc); make_ground(); cam = make_camera(sc)
    coll = bpy.context.collection; objs = make_instances(model, S, coll)
    bpy.context.view_layer.update()
    for o in objs: o['rest'] = tuple(o.location); o['corners'] = [tuple(o.matrix_world @ Vector(c)) for c in o.bound_box]
    steps, f_end = plan(model, a); tt = int(a.turntable_seconds * a.fps); total = f_end + int(0.4 * a.fps) + tt
    # ground sits under the whole finished model
    allv = list(range(len(objs))); lo, hi = bounds(objs, allv); bpy.data.objects['ground'].location = (0, 0, lo[2] - 0.0004)
    if a.res == 'auto':                                           # tall thin pieces (stems, branches) get a portrait frame
        w, h = (1080, 1440) if (hi[2] - lo[2]) > 2.0 * max(hi[0] - lo[0], hi[1] - lo[1]) else (1920, 1080)
        if a.preview: w, h = round(w / 2.25), round(h / 2.25)
        sc.render.resolution_x, sc.render.resolution_y = w, h
    diag = float(np.linalg.norm(hi - lo)); slide = max(40.0, min(140.0, diag / LDU * 0.18))
    fov = 2 * math.atan(36 / (2 * 85)); az0, el = math.radians(-35), math.radians(18)
    # camera targets per step: frame everything built so far (what the manual's pages do), smoothed between steps
    keys = []
    for st in steps:
        vis = [i for s2 in steps[:steps.index(st) + 1] for idx, _ in s2['units'] for i in idx]
        l, h = bounds(objs, vis); c = (l + h) / 2
        keys.append((c, np.array([max((h[0] - l[0]) / 2, (h[1] - l[1]) / 2, 0.03), max((h[2] - l[2]) / 2, 0.03)])))   # half width round the vertical axis, half height
    c_final, r_final = keys[-1] if keys else ((lo + hi) / 2, np.array([diag / 3, diag / 3]))
    os.makedirs(a.out, exist_ok=True)
    f1 = a.end if a.end >= 0 else total - 1
    print(f'{a.set}/{a.model}: {len(steps)} steps, {total} frames @ {a.fps} fps ({total / a.fps:.1f}s)')
    for f in range(a.start, f1 + 1):
        vis = frame_state(model, objs, steps, f, slide)
        # which step are we in: blend the framing between consecutive steps
        si = max([i for i, st in enumerate(steps) if f >= st['f0']] or [0]); st = steps[si]
        k = ease((f - st['f0']) / max(1, 0.8 * (st['f1'] - st['f0']))); prev = keys[si - 1] if si > 0 else keys[0]; cur = keys[si]
        c = np.array(prev[0]) * (1 - k) + np.array(cur[0]) * k; r = prev[1] * (1 - k) + cur[1] * k
        r = r + slide * LDU * 0.45 * (1 - ease((f - st['f0']) / max(1, 0.75 * (st['f1'] - st['f0']))))      # room for pieces still sliding in
        if f >= f_end:                                            # finished: settle on the whole model and turn around it
            u = min(1, (f - f_end) / max(1, tt + 0.4 * a.fps)); c, r = np.array(c_final), r_final; az = az0 + 2 * math.pi * ease(u) * (1 if tt else 0)
        else: az = az0 + math.radians(40) * (f / max(1, f_end))
        asp = sc.render.resolution_x / sc.render.resolution_y
        vfov = 2 * math.atan(math.tan(fov / 2) / asp) if asp >= 1 else fov       # Blender fits the sensor to the wider side
        hfov = fov if asp >= 1 else 2 * math.atan(math.tan(fov / 2) * asp)
        if asp < 1: vfov = fov
        hw, hh = r; dist = (max(hh / math.tan(vfov / 2), hw / math.tan(hfov / 2)) + hw) * 1.12
        pos = Vector(c) + Vector((math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el))) * dist
        cam.location = pos; aim.location = Vector(c)
        d = Vector(c) - pos; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        sc_k = max(max(r) / 0.08, 0.5); bpy.data.objects['key'].location = Vector(c) + Vector((-0.25, -0.3, 0.9)) * sc_k
        bpy.data.lights['key'].energy = 8 * sc_k ** 2; bpy.data.lights['key'].size = 0.25 * sc_k      # same light however far it sits
        sc.render.filepath = os.path.join(a.out, f'frame_{f:05d}.png'); bpy.ops.render.render(write_still=True)
        if f % 10 == 0 or f == f1: print('frame', f, '/', total - 1, flush=True)

if __name__ == '__main__': main()
