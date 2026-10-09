"""
Il telone visto da sotto: il pescatore rannicchiato sul pagliolo tra i due banchi, con la tela tirata
sopra la testa. La tela è una simulazione di stoffa vera: cade sui due banchi e sul pescatore
rannicchiato e fa le sue pieghe. Si vede la tela da vicino, i lati che scendono fino al pagliolo e, in
fondo, lo spiraglio sotto il banco di prua.

Due passi di luce:
  ambient  la luce di fuori che filtra dalla tela (lampara, luna, lanterna)
  lamp     la tela retroilluminata in modo uniforme (luce verdeazzurra del giocattolo di Hatch):
           il motore la moltiplica per un bagliore che si muove, cioè Hatch che fruga sopra il telone
"""
from __future__ import annotations

import bpy
import numpy as np

from boat import half_width_at
from common import link, log, set_lightgroup
from nodes import material

EYE_HIDDEN = (0.03, -0.16, 0.17)       # occhi del pescatore rannicchiato sul pagliolo (piano a z −0.09)
LOOK_AT = (0.0, 1.0, 0.33)
SHEET = (1.9, 2.1)                     # telo: larghezza (x) e lunghezza (y), metri
SHEET_Y = 0.27                         # centro del telo lungo la barca
FRAMES = 45


def canvas_material():
    """Tela cerata vecchia: verde oliva a chiazze, cera lucida a tratti, aloni d'acqua, muffa,
    orlo cucito e una cucitura a metà. Niente trama regolare: a distanza farebbe moiré."""
    m = bpy.data.materials.get('TarpWaxed')
    if m:
        return m
    m, g = material('TarpWaxed')
    co = g.texcoord('Object')
    uv = g.texcoord('UV')
    n1 = g.noise(co, scale=2.4, detail=6.0, rough=0.55)
    n2 = g.noise(co, scale=9.0, detail=4.0, rough=0.6)
    col = g.ramp(n1.fac, [(0.30, (0.050, 0.055, 0.032)), (0.55, (0.085, 0.088, 0.052)), (0.80, (0.115, 0.110, 0.068))])
    # aloni d'acqua secca: anelli più scuri
    vor = g.voronoi(co, scale=2.6, out='Distance')
    tide = g.mul(g.smoothstep(0.22, 0.26, vor), g.sub(1.0, g.smoothstep(0.27, 0.31, vor)))
    col = g.mix(g.mul(tide, 0.45), col, (0.03, 0.032, 0.02))
    # puntini di muffa
    mold = g.mul(g.smoothstep(0.70, 0.78, g.noise(co, scale=34.0, detail=2.0).fac), g.smoothstep(0.45, 0.65, n2.fac))
    col = g.mix(g.mul(mold, 0.8), col, (0.012, 0.018, 0.010))
    # orlo cucito lungo i bordi del telo e una cucitura a metà (in uv: seguono la stoffa)
    u, v, _ = g.sep(uv)
    edge = g.mx(g.mx(g.smoothstep(0.988, 0.995, u), g.sub(1.0, g.smoothstep(0.005, 0.012, u))),
                g.mx(g.smoothstep(0.988, 0.995, v), g.sub(1.0, g.smoothstep(0.005, 0.012, v))))
    seam = g.sub(1.0, g.smoothstep(0.0015, 0.004, g.math('ABSOLUTE', g.sub(v, 0.52))))
    hem = g.mx(edge, seam)
    col = g.mix(g.mul(hem, 0.35), col, (0.025, 0.025, 0.015))
    # le pieghe trattengono lo sporco
    ao = g.ao(distance=0.06, samples=8)
    col = g.mix(g.sub(1.0, ao), col, (0.02, 0.02, 0.012))
    rough = g.map_range(n2.fac, 0.3, 0.7, 0.42, 0.72)
    grain = g.noise(co, scale=140.0, detail=2.0, rough=0.5)
    nrm = g.bump(g.add(g.mul(grain.fac, 0.4), g.mul(hem, 0.6)), strength=0.08, distance=0.002)
    surf = g.principled(color=col, rough=rough, coat=0.18, coat_rough=0.35, sheen=0.15, sheen_tint=(0.4, 0.45, 0.3), normal=nrm)
    # poca luce passa attraverso la tela cerata, meno ancora sull'orlo doppio
    trans_col = g.mix(hem, g.vmath('SCALE', col, scale=2.6), (0.02, 0.02, 0.015))
    trans = g.translucent(trans_col, normal=nrm)
    g.output_material(g.mix_shader(0.16, surf, trans))
    return m


def _collider(ob, friction=6.0):
    ob.modifiers.new('Collision', 'COLLISION')
    ob.collision.thickness_outer = 0.02
    ob.collision.cloth_friction = friction


def _ellipsoid(name, loc, radii):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=1.0, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = radii
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.hide_render = True
    return ob


def _ridge(y):
    """Quota del colmo della tela lungo l'asse della barca: sulla testa, poi tesa fino al banco di prua."""
    if y < -0.40:                                   # dietro: scende oltre il banco dove sei seduto
        return 0.42 - (-0.40 - y) * 0.9
    if y < -0.02:                                   # appoggiata sulla testa e sulle spalle
        return 0.34 + 0.03 * np.sin((y + 0.40) / 0.38 * np.pi)
    if y < 0.86:                                    # campata fino al banco di prua
        s = (y + 0.02) / 0.88
        return 0.34 + (0.435 - 0.34) * s - 0.04 * 4 * s * (1 - s)
    if y < 1.10:                                    # sopra il banco di prua
        return 0.435
    return max(-0.05, 0.435 - (y - 1.10) * 1.6)     # oltre il banco ricade verso il pagliolo


def _cross(u, y):
    """Quanto la tela resta alta allontanandosi dall'asse (1 sul colmo, 0 sul pagliolo)."""
    w0 = 0.24 + 0.04 * np.sin(y * 3.1)
    w1 = 0.70 + 0.04 * np.sin(y * 2.3 + 1.0)
    t = np.clip((u - w0) / (w1 - w0), 0.0, 1.0)
    return 1.0 - t * t * (3 - 2 * t)


def simulate_drape(res=0.02, frames=FRAMES):
    """La forma a tenda (sulla testa, tesa fino al banco di prua, i lati che scendono al pagliolo)
    rilassata da una simulazione di stoffa: la tela resta fissata sul colmo e sui banchi, si allarga un
    poco e fa grinze e afflosciamenti veri tra un appoggio e l'altro."""
    sc = bpy.context.scene
    floor = -0.085
    xs = np.arange(-0.95, 0.95 + 1e-6, res)
    ys = np.arange(-0.80, 1.45 + 1e-6, res)
    nx = len(xs)
    rr = np.random.default_rng(11)
    verts, uvs, pin = [], [], []
    for y in ys:
        ridge = _ridge(float(y))
        for x in xs:
            c = float(_cross(abs(float(x)), float(y)))
            z = max(floor, floor + (ridge - floor) * c + float(rr.normal(0.0, 0.002)))
            # dentro lo scafo: in basso la barca è stretta
            xm = max(0.05, half_width_at(float(y), z + 0.02) - 0.03)
            xx = float(np.clip(float(x) * (1 + 0.05 * (1 - c)), -xm, xm))
            verts.append((xx, float(y), z))
            uvs.append(((x + 0.95) / 1.9, (y + 0.80) / 2.25))
            # fissata sul colmo, sui banchi e dove tocca il pagliolo; libera sui fianchi
            on_ridge = abs(x) < 0.07 and -0.45 < y < 0.95
            on_bench = (0.86 < y < 1.10 or -0.66 < y < -0.40) and abs(x) < 0.55
            on_floor = c < 0.02
            pin.append(1.0 if on_ridge else 0.6 if on_bench else 0.5 if on_floor else 0.0)
    faces = []
    for j in range(len(ys) - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    me = bpy.data.meshes.new('TarpSim')
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            uv.data[li].uv = uvs[vi]
    sheet = bpy.data.objects.new('TarpSim', me)
    sc.collection.objects.link(sheet)
    vg = sheet.vertex_groups.new(name='Pin')
    for i, w in enumerate(pin):
        if w > 0:
            vg.add([i], w, 'REPLACE')
    cloth = sheet.modifiers.new('Cloth', 'CLOTH')
    st = cloth.settings
    st.quality = 12
    st.mass = 0.15
    st.tension_stiffness = 40.0
    st.compression_stiffness = 6.0      # si accartoccia facilmente: fa grinze
    st.shear_stiffness = 15.0
    st.bending_stiffness = 2.5
    st.air_damping = 5.0
    st.vertex_group_mass = 'Pin'
    st.pin_stiffness = 2.0
    st.shrink_min = -0.09               # la tela è un po' più grande della forma: l'eccesso fa pieghe
    st.effector_weights.gravity = 0.6
    cs = cloth.collision_settings
    cs.use_collision = True
    cs.distance_min = 0.008
    cs.collision_quality = 5
    cs.use_self_collision = False
    cloth.point_cache.frame_start = 1
    cloth.point_cache.frame_end = frames
    cols = [bpy.data.objects[n] for n in ('ThwartSeat', 'ThwartFwd', 'Hull') if n in bpy.data.objects]
    cols += [o for o in bpy.data.objects if o.name.startswith('Floor') and o.type == 'MESH']
    for o in cols:
        _collider(o)
    bpy.context.view_layer.update()
    sc.frame_set(1)
    for f in range(1, frames + 1):
        sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = sheet.evaluated_get(dg)
    me2 = bpy.data.meshes.new_from_object(ev)
    drape = bpy.data.objects.new('TarpDrape', me2)
    link(drape, 'boat')
    drape.matrix_world = sheet.matrix_world.copy()
    for p in me2.polygons:
        p.use_smooth = True
    sub = drape.modifiers.new('S', 'SUBSURF')
    sub.levels = 1
    sub.render_levels = 1
    so = drape.modifiers.new('T', 'SOLIDIFY')
    so.thickness = 0.0025
    drape.data.materials.append(canvas_material())
    set_lightgroup(drape, 'ambient')
    bpy.data.objects.remove(sheet, do_unlink=True)
    for o in cols:
        m = o.modifiers.get('Collision')
        if m:
            o.modifiers.remove(m)
    sc.frame_set(1)
    mw = drape.matrix_world
    zs = np.array([(mw @ v.co).z for v in me2.vertices])
    log('telone simulato:', len(me2.vertices), 'vertici, quota nel mondo', round(float(zs.min()), 3), '…', round(float(zs.max()), 3))
    return drape


def toy_backlight():
    """Luce uniforme sopra il telone (gruppo 'lamp'): il motore la trasforma nel bagliore che fruga."""
    ld = bpy.data.lights.new('ToyBacklight', 'AREA')
    ld.shape = 'RECTANGLE'
    ld.size = 2.2
    ld.size_y = 2.6
    ld.energy = 60.0
    ld.color = (0.30, 1.0, 0.82)
    ob = bpy.data.objects.new('ToyBacklight', ld)
    ob.location = (0.0, 0.35, 1.05)
    link(ob, 'boat')
    ob.lightgroup = 'lamp'
    return ob
