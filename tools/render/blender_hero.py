"""Photoreal render of the finished Sakura Planter (Blender 4.x/5.x Cycles, bpy).

Studio HDR (Poly Haven studio_small_03, CC0) for light, a procedural linen sweep as the backdrop.
Run tools/render/prep_render.py first, then:
  python tools/render/blender_hero.py <out.png> <width> <height> <samples> [hero|close|motif|top]
"""
import sys, json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.join(ROOT, 'pipeline', 'work', 'render')
OUT = os.path.abspath(sys.argv[1]); W, H, SPP = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
VIEW = sys.argv[5] if len(sys.argv) > 5 else 'hero'
S = 0.001
FLOOR_Z = -0.0838

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

HEX = {'Black': '1B2A34', 'Bright Pink': 'F4A7CF', 'Dark Bluish Gray': '5E6366', 'Dark Green': '184632', 'Dark Pink': 'C8509B',
       'Dark Purple': '3F3691', 'Dark Turquoise': '069D9F', 'Green': '237841', 'Lavender': 'CDA4DE', 'Light Bluish Gray': 'A0A5A9',
       'Light Nougat': 'F6D7B3', 'Lime': 'BBE90B', 'Magenta': '923978', 'Medium Lavender': 'AC78BA', 'Orange': 'FE8A18',
       'Pearl Gold': 'AA7F2E', 'Red': 'C91A09', 'Reddish Brown': '582A12', 'Sand Green': 'A0BCAC', 'Tan': 'E4CD9E',
       'White': 'F4F4F4', 'Yellow': 'F2CD37', 'Yellowish Green': 'DFEEA5', 'Dark Red': '720E0F'}
LD2NAME = {0: 'Black', 29: 'Bright Pink', 72: 'Dark Bluish Gray', 288: 'Dark Green', 5: 'Dark Pink', 85: 'Dark Purple', 3: 'Dark Turquoise',
           2: 'Green', 31: 'Lavender', 71: 'Light Bluish Gray', 78: 'Light Nougat', 27: 'Lime', 26: 'Magenta', 30: 'Medium Lavender',
           25: 'Orange', 297: 'Pearl Gold', 4: 'Red', 70: 'Reddish Brown', 378: 'Sand Green', 19: 'Tan', 15: 'White', 14: 'Yellow',
           326: 'Yellowish Green', 320: 'Dark Red'}
def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]
def node_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bs.outputs['BSDF'], out.inputs['Surface'])
    return m, nt, bs

MATS = {}
def abs_mat(colour):
    if colour in MATS: return MATS[colour]
    m, nt, bs = node_mat('ABS ' + colour)
    bs.inputs['Base Color'].default_value = lin(HEX[colour]); bs.inputs['Roughness'].default_value = 0.17
    bs.inputs['IOR'].default_value = 1.54; bs.inputs['Coat Weight'].default_value = 0.15; bs.inputs['Coat Roughness'].default_value = 0.06
    if colour == 'Pearl Gold':
        bs.inputs['Metallic'].default_value = 0.85; bs.inputs['Roughness'].default_value = 0.32; bs.inputs['Coat Weight'].default_value = 0.0
    if colour in ('White', 'Bright Pink', 'Light Nougat', 'Lavender', 'Yellowish Green', 'Tan', 'Lime', 'Yellow', 'Medium Lavender', 'Sand Green'):
        bs.inputs['Subsurface Weight'].default_value = 0.12; bs.inputs['Subsurface Radius'].default_value = (1.0, 0.8, 0.6); bs.inputs['Subsurface Scale'].default_value = 0.0015
    MATS[colour] = m
    return m

def fdm_mat(name, hexc, rough, axis=(0, 0, 1), layer=0.2, bump=0.3, fuzzy=0.0):
    """FDM print: layer lines perpendicular to the print axis (object coords, mm), optional fuzzy-skin bark."""
    m, nt, bs = node_mat(name)
    bs.inputs['Base Color'].default_value = lin(hexc); bs.inputs['Roughness'].default_value = rough
    tc = nt.nodes.new('ShaderNodeTexCoord')
    dot = nt.nodes.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'; dot.inputs[1].default_value = axis
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 2 * math.pi / layer
    sin = nt.nodes.new('ShaderNodeMath'); sin.operation = 'SINE'
    bmp = nt.nodes.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = bump; bmp.inputs['Distance'].default_value = 0.03
    nt.links.new(tc.outputs['Object'], dot.inputs[0]); nt.links.new(dot.outputs['Value'], mul.inputs[0]); nt.links.new(mul.outputs[0], sin.inputs[0])
    h = sin.outputs[0]
    if fuzzy:
        nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.6; nz.inputs['Detail'].default_value = 3.0
        mix = nt.nodes.new('ShaderNodeMath'); mix.operation = 'MULTIPLY_ADD'; mix.inputs[1].default_value = fuzzy
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector']); nt.links.new(nz.outputs['Fac'], mix.inputs[0]); nt.links.new(h, mix.inputs[2])
        h = mix.outputs[0]; bmp.inputs['Strength'].default_value = 0.55
    nt.links.new(h, bmp.inputs['Height']); nt.links.new(bmp.outputs['Normal'], bs.inputs['Normal'])
    return m, bs

FDM = {}
def printed_mat(kind, axis):
    key = (kind, tuple(round(a, 3) for a in axis))
    if key in FDM: return FDM[key]
    if kind in ('bone', 'bark'):
        m, bs = fdm_mat(kind, 'E6DBC6', 0.45, axis, fuzzy=6.0 if kind == 'bark' else 0.0)
        bs.inputs['Subsurface Weight'].default_value = 0.08; bs.inputs['Subsurface Radius'].default_value = (1.0, 0.85, 0.7); bs.inputs['Subsurface Scale'].default_value = 0.002
    elif kind == 'tpu_black':
        m, bs = fdm_mat(kind, '1A1A1B', 0.62, axis, bump=0.2)
    elif kind == 'tpu_clear':
        m, bs = fdm_mat(kind, 'E6F0F2', 0.3, axis, bump=0.45)
        bs.inputs['Transmission Weight'].default_value = 0.92; bs.inputs['IOR'].default_value = 1.5
    else:                                     # acrylic paint in the motif pockets
        col = {'paint_bark': '5E3523', 'paint_petal': 'EFA2BE', 'paint_centre': 'A3204F', 'paint_bud': 'D9577F'}[kind]
        m, nt, bs = node_mat(kind); bs.inputs['Base Color'].default_value = lin(col); bs.inputs['Roughness'].default_value = 0.5
    FDM[key] = m
    return m

# ------------------------------------------------------------------ LEGO
D = np.load(os.path.join(WORK, 'parts_hi.npz'))
P = json.load(open(os.path.join(ROOT, 'lego', 'placements.json')))
mesh_cache = {}
def part_mesh(pid):
    if pid in mesh_cache: return mesh_cache[pid]
    V = D[pid + '_v'] * S; C = D[pid + '_c']
    bm = bmesh.new(); vs = [bm.verts.new(v) for v in V]
    fixed = sorted(set(int(c) for c in C if c not in (16, 24)))
    for k in range(len(C)):
        try:
            f = bm.faces.new((vs[3 * k], vs[3 * k + 1], vs[3 * k + 2])); c = int(C[k]); f.material_index = 0 if c in (16, 24) else 1 + fixed.index(c)
        except ValueError: pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.00001); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(pid); bm.to_mesh(me); bm.free(); me.shade_smooth()
    try: me.set_sharp_from_angle(angle=math.radians(32))
    except Exception: pass
    me.materials.append(None)
    for c in fixed: me.materials.append(abs_mat(LD2NAME.get(c, 'Black')))
    mesh_cache[pid] = me
    return me
lego = bpy.data.collections.new('LEGO'); scene.collection.children.link(lego)
for i, p in enumerate(P):
    ob = bpy.data.objects.new(f"{p['part']}_{i}", part_mesh(p['part']))
    R = np.array(p['R']); t = np.array(p['p']) * S
    ob.matrix_world = Matrix(((R[0, 0], R[0, 1], R[0, 2], t[0]), (R[1, 0], R[1, 1], R[1, 2], t[1]), (R[2, 0], R[2, 1], R[2, 2], t[2]), (0, 0, 0, 1)))
    ob.material_slots[0].link = 'OBJECT'; ob.material_slots[0].material = abs_mat(p['colour'])
    lego.objects.link(ob)

# ------------------------------------------------------------------ printed parts
pc = bpy.data.collections.new('Printed'); scene.collection.children.link(pc)
for sp in json.load(open(os.path.join(WORK, 'parts.json'))):
    bpy.ops.wm.stl_import(filepath=sp['file'])
    ob = bpy.context.selected_objects[0]; ob.name = sp['name']
    for c in ob.users_collection: c.objects.unlink(ob)
    pc.objects.link(ob)
    ob.data.materials.clear(); ob.data.materials.append(printed_mat(sp['mat'], sp['axis']))
    ob.data.shade_smooth()
    try: ob.data.set_sharp_from_angle(angle=math.radians(40))
    except Exception: pass
    vmax = max(abs(c) for v in ob.data.vertices for c in v.co); u = S if vmax > 2 else 1.0
    ob.matrix_world = Matrix(((u, 0, 0, 0), (0, u, 0, 0), (0, 0, u, 0), (0, 0, 0, 1)))

# ------------------------------------------------------------------ linen sweep
VIEWS = {'hero': ((0.72, -1.0, 0.40), (0.0, 0.0, 0.15), 50.0, 5.6),
         'close': ((0.21, -0.29, 0.25), (0.01, 0.0, 0.20), 85.0, 3.2),
         'motif': ((0.17, -0.40, 0.02), (0.035, -0.082, -0.035), 70.0, 11.0),
         'top': ((0.16, -0.22, 0.62), (0.0, 0.0, 0.05), 50.0, 6.0)}
loc, tgt, lens, fstop = VIEWS[VIEW]
az = math.atan2(loc[0] - tgt[0], -(loc[1] - tgt[1]))       # camera azimuth around Z, 0 = looking from -Y
def sweep():
    prof, R = [], 0.65
    zs = [1.9 - 0.05 * k for k in range(48)]
    prof += [(z, 0.0) for z in zs if z > -0.45]
    prof += [(-0.45 - math.sin(k / 24 * math.pi / 2) * R, R - math.cos(k / 24 * math.pi / 2) * R) for k in range(25)]
    prof += [(-0.45 - R, R + 0.1 * k) for k in range(1, 25)]
    bm = bmesh.new(); xs = [-3.0 + 0.5 * i for i in range(13)]; rows = []
    for z, y in prof: rows.append([bm.verts.new((x, -z, y)) for x in xs])            # local: floor toward -Y (camera side), wall at +Y
    for a, b in zip(rows[:-1], rows[1:]):
        for i in range(len(xs) - 1): bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
    me = bpy.data.meshes.new('Sweep'); bm.to_mesh(me); bm.free(); me.shade_smooth()
    ob = bpy.data.objects.new('Sweep', me); scene.collection.objects.link(ob)
    ob.location = (0, 0, FLOOR_Z); ob.rotation_euler = (0, 0, az)
    m, nt, bs = node_mat('Linen')
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep.inputs['Vector'])
    # cloth coordinates: x across, and the distance along the floor/cove/wall (y and z both feed the other thread direction)
    alongs = nt.nodes.new('ShaderNodeMath'); alongs.operation = 'ADD'; nt.links.new(sep.outputs['Y'], alongs.inputs[0]); nt.links.new(sep.outputs['Z'], alongs.inputs[1])
    def threads(src, seed):
        noise = nt.nodes.new('ShaderNodeTexNoise'); noise.noise_dimensions = '4D'; noise.inputs['Scale'].default_value = 9.0
        try: noise.inputs['W'].default_value = seed
        except KeyError: noise.inputs[1].default_value = seed
        nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
        mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 2 * math.pi / 0.0016
        wob = nt.nodes.new('ShaderNodeMath'); wob.operation = 'MULTIPLY_ADD'; wob.inputs[1].default_value = 1.4
        nt.links.new(src, mul.inputs[0]); nt.links.new(noise.outputs['Fac'], wob.inputs[0]); nt.links.new(mul.outputs[0], wob.inputs[2])
        s = nt.nodes.new('ShaderNodeMath'); s.operation = 'SINE'; nt.links.new(wob.outputs[0], s.inputs[0])
        a = nt.nodes.new('ShaderNodeMath'); a.operation = 'ABSOLUTE'; nt.links.new(s.outputs[0], a.inputs[0])
        return a.outputs[0], noise.outputs['Fac']
    tx, nx = threads(sep.outputs['X'], 1.3); ty, ny = threads(alongs.outputs[0], 7.1)
    mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'; nt.links.new(tx, mx.inputs[0]); nt.links.new(ty, mx.inputs[1])
    slub = nt.nodes.new('ShaderNodeTexNoise'); slub.inputs['Scale'].default_value = 60.0; slub.inputs['Detail'].default_value = 4.0
    nt.links.new(tc.outputs['Object'], slub.inputs['Vector'])
    shade = nt.nodes.new('ShaderNodeMath'); shade.operation = 'MULTIPLY_ADD'; shade.inputs[1].default_value = 0.25; shade.inputs[2].default_value = 0.0
    nt.links.new(mx.outputs[0], shade.inputs[0])
    col = nt.nodes.new('ShaderNodeMath'); col.operation = 'MULTIPLY_ADD'; col.inputs[1].default_value = 0.35
    nt.links.new(slub.outputs['Fac'], col.inputs[0]); nt.links.new(shade.outputs[0], col.inputs[2])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.1; ramp.color_ramp.elements[0].color = lin('8E826E')
    ramp.color_ramp.elements[1].position = 0.6; ramp.color_ramp.elements[1].color = lin('C7BAA2')
    nt.links.new(col.outputs[0], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], bs.inputs['Base Color'])
    bmp = nt.nodes.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = 0.6; bmp.inputs['Distance'].default_value = 0.0004
    nt.links.new(mx.outputs[0], bmp.inputs['Height']); nt.links.new(bmp.outputs['Normal'], bs.inputs['Normal'])
    bs.inputs['Roughness'].default_value = 0.85; bs.inputs['Sheen Weight'].default_value = 0.35; bs.inputs['Sheen Roughness'].default_value = 0.6
    me.materials.append(m)
sweep()

# ------------------------------------------------------------------ light: HDR world + a soft key for shaped shadows
world = bpy.data.worlds.new('World'); scene.world = world; world.use_nodes = True
wn = world.node_tree; bg = wn.nodes['Background']
env = wn.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(os.path.join(ROOT, 'docs', 'assets', 'studio_small_03_1k.hdr'))
mp = wn.nodes.new('ShaderNodeMapping'); tco = wn.nodes.new('ShaderNodeTexCoord'); mp.inputs['Rotation'].default_value = (0, 0, az + math.radians(40))
wn.links.new(tco.outputs['Generated'], mp.inputs['Vector']); wn.links.new(mp.outputs['Vector'], env.inputs['Vector']); wn.links.new(env.outputs['Color'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = 0.42
def area(name, loc, target, size, power, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'RECTANGLE'; ld.size = size[0]; ld.size_y = size[1]; ld.energy = power; ld.color = color
    ob = bpy.data.objects.new(name, ld); scene.collection.objects.link(ob); ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return ob
ca, sa = math.cos(az), math.sin(az)
def rot(x, y, z): return (x * ca - y * sa, x * sa + y * ca, z)
area('Key', rot(-0.55, -0.55, 0.6), (0, 0, 0.12), (0.6, 0.45), 15, (1.0, 0.96, 0.9))
area('Rim', rot(0.35, 0.45, 0.6), (0, 0, 0.18), (0.35, 0.35), 7, (1.0, 0.95, 0.92))

# ------------------------------------------------------------------ camera and render
cd = bpy.data.cameras.new('Cam'); cam = bpy.data.objects.new('Cam', cd); scene.collection.objects.link(cam); scene.camera = cam
cam.location = loc; cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
cd.lens = lens; cd.sensor_width = 36; cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop; cd.dof.focus_distance = (Vector(tgt) - Vector(loc)).length
scene.render.engine = 'CYCLES'; cy = scene.cycles
cy.device = 'CPU'; cy.samples = SPP; cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.015; cy.use_denoising = True
try: cy.denoiser = 'OPENIMAGEDENOISE'
except Exception: pass
cy.max_bounces = 8; cy.transparent_max_bounces = 4; cy.caustics_reflective = False; cy.caustics_refractive = False
scene.render.resolution_x = W; scene.render.resolution_y = H; scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'; scene.render.image_settings.color_depth = '8'
try: scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
scene.view_settings.exposure = -0.2
scene.render.filepath = OUT
print('rendering', VIEW, W, 'x', H, SPP, 'spp', flush=True)
bpy.ops.render.render(write_still=True)
print('done', OUT)
