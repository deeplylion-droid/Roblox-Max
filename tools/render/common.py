"""
Utilità condivise della pipeline di render di SPLASHLAND IS CLOSED! (Blender 5.2 come modulo Python).

Convenzioni di scena (metri):
  - livello del mare z = 0, prua verso +Y, dritta (destra) verso +X;
  - l'occhio del giocatore è in EYE; lo sguardo "avanti" è +Y;
  - panorama equirettangolare: x cresce girando a destra, il centro dell'immagine è +Y,
    riga 0 = latitudine LAT_MAX (verificato con tools/render/calib.py).

Ogni render scrive un EXR multilayer con i passi:
  ambient, lamp, lantern → light group (lineari, denoisati separatamente con OIDN)
  alpha, mist, index → dati (canali 'alpha.V', 'mist.V', 'index.V')
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass

import bpy
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE = os.path.join(ROOT, 'tools', 'render', 'cache')
OUT_IMG = os.path.join(ROOT, 'public', 'assets', 'img')

EYE = (0.0, -0.55, 1.25)          # occhio del pescatore seduto sul banco
LAT_MIN, LAT_MAX = -58.0, 36.0    # gradi coperti dal panorama in verticale
PANO_W_FINAL = 8192

LIGHTGROUPS = ('ambient', 'lamp', 'lantern')

# indici oggetto per le maschere (pass IndexOB)
IDX_WATER = 1
IDX_SKY = 2


def pano_size(width: int) -> tuple[int, int]:
    h = round(width * (LAT_MAX - LAT_MIN) / 360.0)
    return width, h


# ───────────────────────── scena ─────────────────────────

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = False          # denoise per passo nel compositor
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 6
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.sample_clamp_indirect = 6.0
    sc.render.threads_mode = 'AUTO'
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.film_transparent = False
    # il modulo bpy non ha contesto GPU: compositor e denoiser su CPU
    sc.render.compositor_device = 'CPU'
    sc.render.compositor_denoise_device = 'CPU'
    sc.render.compositor_precision = 'FULL'
    vl = sc.view_layers[0]
    for name in LIGHTGROUPS:
        vl.lightgroups.add(name=name)
    vl.cycles.denoising_store_passes = True
    vl.use_pass_mist = True
    vl.use_pass_object_index = True
    return sc


def collection(name: str):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def link(obj, col_name: str):
    col = collection(col_name)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def set_lightgroup(obj, group: str):
    obj.lightgroup = group


def set_visibility(obj, camera=True, shadow=True, diffuse=True, glossy=True, transmission=True, scatter=True):
    obj.visible_camera = camera
    obj.visible_shadow = shadow
    obj.visible_diffuse = diffuse
    obj.visible_glossy = glossy
    obj.visible_transmission = transmission
    obj.visible_volume_scatter = scatter


def mesh_from_arrays(name: str, verts, faces, smooth=True, col='misc'):
    me = bpy.data.meshes.new(name)
    verts = np.asarray(verts, dtype=float)
    me.from_pydata(verts, [], faces)
    me.validate(clean_customdata=False)
    me.update()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    collection(col).objects.link(ob)
    return ob


def set_custom_normals(ob, normals):
    me = ob.data
    me.normals_split_custom_set_from_vertices([tuple(map(float, n)) for n in normals])


# ───────────────────────── materiali ─────────────────────────

class NodeBuilder:
    """Piccolo aiuto per costruire node tree di materiali in modo leggibile."""

    def __init__(self, mat):
        self.mat = mat
        self.nt = mat.node_tree
        self.x = 0

    def node(self, kind: str, **inputs):
        n = self.nt.nodes.new(kind)
        n.location = (self.x, 0)
        self.x -= 220
        for k, v in inputs.items():
            if k.startswith('_'):
                setattr(n, k[1:], v)
                continue
            self.set_input(n, k, v)
        return n

    def set_input(self, n, key, v):
        sock = n.inputs[key] if not isinstance(key, int) else n.inputs[key]
        if isinstance(v, bpy.types.NodeSocket):
            self.nt.links.new(v, sock)
        else:
            sock.default_value = v

    def link(self, a, b):
        self.nt.links.new(a, b)


def new_material(name: str):
    m = bpy.data.materials.get(name)
    if m:
        return m, None
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, NodeBuilder(m)


def principled(name: str, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, coat=0.0, coat_rough=0.05,
               sss=0.0, sss_radius=(1.0, 0.4, 0.2), sss_scale=0.05, emission=None, emission_strength=0.0,
               spec=0.5, alpha=1.0, transmission=0.0, ior=1.45):
    m, b = new_material(name)
    if b is None:
        return m
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    p.inputs['Coat Weight'].default_value = coat
    p.inputs['Coat Roughness'].default_value = coat_rough
    p.inputs['Subsurface Weight'].default_value = sss
    p.inputs['Subsurface Radius'].default_value = sss_radius
    p.inputs['Subsurface Scale'].default_value = sss_scale
    p.inputs['Specular IOR Level'].default_value = spec
    p.inputs['Alpha'].default_value = alpha
    p.inputs['Transmission Weight'].default_value = transmission
    p.inputs['IOR'].default_value = ior
    if emission is not None:
        p.inputs['Emission Color'].default_value = (*emission, 1)
        p.inputs['Emission Strength'].default_value = emission_strength
    return m


def emission_material(name: str, color, strength):
    m, b = new_material(name)
    if b is None:
        return m
    nt = m.node_tree
    nt.nodes.clear()
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (*color, 1)
    e.inputs['Strength'].default_value = strength
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(e.outputs[0], out.inputs['Surface'])
    return m


def assign(ob, mat):
    if ob.data.materials:
        ob.data.materials[0] = mat
    else:
        ob.data.materials.append(mat)
    return ob


# ───────────────────────── camere ─────────────────────────

def panorama_camera(location=EYE, name='PanoCam'):
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = 'PANO'
    cam_data.panorama_type = 'EQUIRECTANGULAR'
    cam_data.latitude_min = math.radians(LAT_MIN)
    cam_data.latitude_max = math.radians(LAT_MAX)
    cam_data.longitude_min = -math.pi
    cam_data.longitude_max = math.pi
    cam_data.clip_start = 0.05
    cam_data.clip_end = 20000
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = location
    cam.rotation_euler = (math.radians(90), 0, 0)   # guarda +Y, alto +Z
    bpy.context.scene.camera = cam
    return cam


def perspective_camera(location, target, lens=24.0, name='Cam', sensor=36.0, roll=0.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_data.sensor_width = sensor
    cam_data.clip_start = 0.02
    cam_data.clip_end = 20000
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = location
    look_at(cam, target, roll)
    bpy.context.scene.camera = cam
    return cam


def look_at(ob, target, roll=0.0):
    from mathutils import Vector
    d = Vector(target) - Vector(ob.location)
    q = d.to_track_quat('-Z', 'Y')
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = q
    if roll:
        from mathutils import Quaternion
        ob.rotation_quaternion = q @ Quaternion((0, 0, 1), roll)


def dir_to_pano_uv(d):
    """Direzione relativa all'occhio (x destra, y avanti, z alto) → uv del panorama (0..1, v dall'alto)."""
    x, y, z = d
    lon = math.atan2(x, y)
    lat = math.atan2(z, math.hypot(x, y))
    u = 0.5 + lon / (2 * math.pi)
    v = (math.radians(LAT_MAX) - lat) / math.radians(LAT_MAX - LAT_MIN)
    return u, v


def world_to_pano_px(p, width):
    w, h = pano_size(width)
    d = (p[0] - EYE[0], p[1] - EYE[1], p[2] - EYE[2])
    u, v = dir_to_pano_uv(d)
    return u * w, v * h


# ───────────────────────── render e passi ─────────────────────────

@dataclass
class Quality:
    name: str
    samples: int
    pano_width: int
    persp_scale: float  # moltiplicatore della risoluzione per le camere prospettiche


QUALITY = {
    'draft': Quality('draft', 24, 2048, 0.5),
    'preview': Quality('preview', 64, 4096, 0.75),
    'final': Quality('final', 160, PANO_W_FINAL, 1.0),
}


def setup_compositor(exr_path: str, groups=LIGHTGROUPS, data_passes=('Alpha', 'Mist', 'Object Index'), denoise=True):
    """Collega RenderLayers → (Denoise) → File Output EXR multilayer."""
    sc = bpy.context.scene
    sc.render.use_compositing = True
    ng = bpy.data.node_groups.new('LamparaComp', 'CompositorNodeTree')
    sc.compositing_node_group = ng
    rl = ng.nodes.new('CompositorNodeRLayers')
    rl.location = (-600, 0)
    out = ng.nodes.new('CompositorNodeOutputFile')
    out.location = (400, 0)
    out.format.file_format = 'OPEN_EXR_MULTILAYER'
    out.format.color_depth = '16'
    out.format.exr_codec = 'ZIP'
    out.directory = os.path.dirname(exr_path)
    out.file_name = os.path.basename(exr_path).replace('.exr', '')
    names = {o.name for o in rl.outputs}
    y = 0
    for g in groups:
        src_name = f'Combined_{g}'
        if src_name not in names:
            raise RuntimeError(f'pass {src_name} mancante; output disponibili: {sorted(names)}')
        out.file_output_items.new('RGBA', g)
        src = rl.outputs[src_name]
        if denoise:
            dn = ng.nodes.new('CompositorNodeDenoise')
            dn.location = (0, y)
            ng.links.new(src, dn.inputs['Image'])
            ng.links.new(rl.outputs['Denoising Albedo'], dn.inputs['Albedo'])
            ng.links.new(rl.outputs['Denoising Normal'], dn.inputs['Normal'])
            dn.inputs['HDR'].default_value = True
            ng.links.new(dn.outputs['Image'], out.inputs[g])
        else:
            ng.links.new(src, out.inputs[g])
        y -= 300
    for p in data_passes:
        if p not in names:
            continue
        key = {'Object Index': 'index'}.get(p, p.lower())
        out.file_output_items.new('FLOAT', key)
        ng.links.new(rl.outputs[p], out.inputs[key])
    return out


def render(exr_path: str, samples: int, resolution, region=None, groups=LIGHTGROUPS, transparent=False,
           data_passes=('Alpha', 'Mist', 'Object Index'), denoise=True):
    """Esegue il render; region = (x0, y0, x1, y1) in pixel (origine in alto a sinistra)."""
    sc = bpy.context.scene
    sc.cycles.samples = samples
    sc.render.resolution_x, sc.render.resolution_y = resolution
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    if region:
        x0, y0, x1, y1 = region
        W, H = resolution
        sc.render.use_border = True
        sc.render.use_crop_to_border = True
        sc.render.border_min_x = x0 / W
        sc.render.border_max_x = x1 / W
        # Blender misura il bordo dal basso
        sc.render.border_min_y = 1 - y1 / H
        sc.render.border_max_y = 1 - y0 / H
    else:
        sc.render.use_border = False
    os.makedirs(os.path.dirname(exr_path), exist_ok=True)
    setup_compositor(exr_path, groups, data_passes, denoise)
    # il file output aggiunge il numero di frame: lo rimuoviamo dopo
    sc.frame_set(1)
    bpy.ops.render.render(write_still=False)
    base = exr_path.replace('.exr', '')
    for cand in (base + '0001.exr', base + '.exr'):
        if os.path.exists(cand) and cand != exr_path:
            os.replace(cand, exr_path)
    if not os.path.exists(exr_path):
        found = [f for f in os.listdir(os.path.dirname(exr_path))]
        raise RuntimeError(f'EXR non trovato: {exr_path} (presenti: {found})')
    return exr_path


def log(*a):
    print('[render]', *a, flush=True)
    sys.stdout.flush()
