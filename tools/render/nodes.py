"""
Mini-DSL per costruire node tree di shader (materiali e mondo) in Blender 5.2.

Ogni funzione accetta socket o costanti e restituisce il socket di uscita, così i grafi
si scrivono come espressioni:  g.mix(g.noise(co, 4).fac, col_a, col_b)
"""
from __future__ import annotations

import bpy

Socket = bpy.types.NodeSocket


def _enabled(sockets, name):
    for s in sockets:
        if s.name == name and s.enabled:
            return s
    for s in sockets:
        if s.identifier == name:
            return s
    raise KeyError(f'socket {name!r} non trovato tra {[x.name for x in sockets if x.enabled]}')


class Noise:
    def __init__(self, node):
        self.node = node
        self.fac = node.outputs['Factor']
        self.color = node.outputs['Color']


class Graph:
    def __init__(self, node_tree, clear=True):
        self.nt = node_tree
        if clear:
            self.nt.nodes.clear()
        self._x = 0

    # ── basi ──
    def node(self, kind: str, **props):
        n = self.nt.nodes.new(kind)
        n.location = (self._x, 0)
        self._x -= 200
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def inp(self, node, name):
        return _enabled(node.inputs, name)

    def out(self, node, name=None):
        if name is None:
            for s in node.outputs:
                if s.enabled:
                    return s
        return _enabled(node.outputs, name)

    def set(self, node, name, value):
        sock = self.inp(node, name) if isinstance(name, str) else node.inputs[name]
        if isinstance(value, Socket):
            self.nt.links.new(value, sock)
        elif value is not None:
            if sock.type == 'RGBA' and isinstance(value, (tuple, list)) and len(value) == 3:
                value = (*value, 1.0)
            if sock.type == 'VECTOR' and isinstance(value, (int, float)):
                value = (value, value, value)
            sock.default_value = value
        return node

    def link(self, a: Socket, b: Socket):
        self.nt.links.new(a, b)

    # ── coordinate ──
    def texcoord(self, which='Object'):
        return self.out(self.node('ShaderNodeTexCoord'), which)

    def attr(self, name, out='Fac', kind='GEOMETRY'):
        n = self.node('ShaderNodeAttribute', attribute_name=name, attribute_type=kind)
        return self.out(n, out)

    def geometry(self, which):
        return self.out(self.node('ShaderNodeNewGeometry'), which)

    def layer_weight(self, blend=0.5, which='Facing', normal=None):
        n = self.node('ShaderNodeLayerWeight')
        self.set(n, 'Blend', blend)
        if normal is not None:
            self.set(n, 'Normal', normal)
        return self.out(n, which)

    def fresnel(self, ior=1.45):
        n = self.node('ShaderNodeFresnel')
        self.set(n, 'IOR', ior)
        return self.out(n, 'Fac')

    def ao(self, distance=0.3, samples=16, only_local=True):
        n = self.node('ShaderNodeAmbientOcclusion', samples=samples, only_local=only_local)
        self.set(n, 'Distance', distance)
        return self.out(n, 'AO')

    # ── matematica ──
    def math(self, op, a, b=None, c=None, clamp=False):
        n = self.node('ShaderNodeMath', operation=op, use_clamp=clamp)
        self.set(n, 0, a)
        if b is not None:
            self.set(n, 1, b)
        if c is not None:
            self.set(n, 2, c)
        return n.outputs[0]

    def add(self, a, b): return self.math('ADD', a, b)
    def sub(self, a, b): return self.math('SUBTRACT', a, b)
    def mul(self, a, b, clamp=False): return self.math('MULTIPLY', a, b, clamp=clamp)
    def div(self, a, b): return self.math('DIVIDE', a, b)
    def pow(self, a, b): return self.math('POWER', a, b)
    def mn(self, a, b): return self.math('MINIMUM', a, b)
    def mx(self, a, b): return self.math('MAXIMUM', a, b)
    def clamp01(self, a): return self.math('MULTIPLY', a, 1.0, clamp=True)

    def smoothstep(self, e0, e1, x):
        n = self.node('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP', clamp=True)
        self.set(n, 'Value', x)
        self.set(n, 'From Min', e0)
        self.set(n, 'From Max', e1)
        self.set(n, 'To Min', 0.0)
        self.set(n, 'To Max', 1.0)
        return self.out(n, 'Result')

    def map_range(self, x, a0, a1, b0, b1, clamp=True):
        n = self.node('ShaderNodeMapRange', clamp=clamp)
        self.set(n, 'Value', x)
        self.set(n, 'From Min', a0)
        self.set(n, 'From Max', a1)
        self.set(n, 'To Min', b0)
        self.set(n, 'To Max', b1)
        return self.out(n, 'Result')

    def vmath(self, op, a, b=None, scale=None):
        n = self.node('ShaderNodeVectorMath', operation=op)
        self.set(n, 0, a)
        if b is not None:
            self.set(n, 1, b)
        if scale is not None:
            self.set(n, 'Scale', scale)
        return self.out(n, 'Value' if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else 'Vector')

    def sep(self, v):
        n = self.node('ShaderNodeSeparateXYZ')
        self.set(n, 'Vector', v)
        return n.outputs['X'], n.outputs['Y'], n.outputs['Z']

    def comb(self, x, y, z):
        n = self.node('ShaderNodeCombineXYZ')
        self.set(n, 'X', x)
        self.set(n, 'Y', y)
        self.set(n, 'Z', z)
        return n.outputs[0]

    def mapping(self, v, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
        n = self.node('ShaderNodeMapping')
        self.set(n, 'Vector', v)
        self.set(n, 'Location', loc)
        self.set(n, 'Rotation', rot)
        self.set(n, 'Scale', scale)
        return n.outputs[0]

    # ── colore ──
    def mix(self, fac, a, b, blend='MIX', clamp=True):
        n = self.node('ShaderNodeMix', data_type='RGBA', blend_type=blend, clamp_result=clamp)
        self.set(n, 'Factor', fac)
        self.set(n, 'A', a)
        self.set(n, 'B', b)
        return self.out(n, 'Result')

    def mixf(self, fac, a, b):
        n = self.node('ShaderNodeMix', data_type='FLOAT')
        self.set(n, 'Factor', fac)
        self.set(n, 'A', a)
        self.set(n, 'B', b)
        return self.out(n, 'Result')

    def ramp(self, fac, stops, interp='LINEAR'):
        """stops: lista di (pos, (r,g,b)) oppure (pos, (r,g,b,a))."""
        n = self.node('ShaderNodeValToRGB')
        cr = n.color_ramp
        cr.interpolation = interp
        els = cr.elements
        while len(els) > 1:
            els.remove(els[-1])
        for i, (pos, col) in enumerate(stops):
            e = els[0] if i == 0 else els.new(pos)
            e.position = pos
            e.color = (*col, 1.0) if len(col) == 3 else col
        self.set(n, 'Fac', fac)
        return n.outputs['Color']

    def hsv(self, color, h=0.5, s=1.0, v=1.0):
        n = self.node('ShaderNodeHueSaturation')
        self.set(n, 'Color', color)
        self.set(n, 'Hue', h)
        self.set(n, 'Saturation', s)
        self.set(n, 'Value', v)
        return n.outputs['Color']

    def bw(self, color):
        n = self.node('ShaderNodeRGBToBW')
        self.set(n, 'Color', color)
        return n.outputs[0]

    # ── texture ──
    def noise(self, vec, scale=5.0, detail=4.0, rough=0.5, distortion=0.0, dims='3D', w=0.0, lacunarity=2.0):
        n = self.node('ShaderNodeTexNoise', noise_dimensions=dims)
        self.set(n, 'Vector', vec)
        self.set(n, 'Scale', scale)
        self.set(n, 'Detail', detail)
        self.set(n, 'Roughness', rough)
        self.set(n, 'Lacunarity', lacunarity)
        self.set(n, 'Distortion', distortion)
        if dims in ('4D', '1D'):
            self.set(n, 'W', w)
        return Noise(n)

    def voronoi(self, vec, scale=5.0, feature='F1', distance='EUCLIDEAN', randomness=1.0, out='Distance', dims='3D'):
        n = self.node('ShaderNodeTexVoronoi', feature=feature, distance=distance, voronoi_dimensions=dims)
        self.set(n, 'Vector', vec)
        self.set(n, 'Scale', scale)
        self.set(n, 'Randomness', randomness)
        return self.out(n, out)

    def wave(self, vec, scale=5.0, distortion=0.0, detail=2.0, detail_scale=1.0, kind='BANDS', axis='X', profile='SIN', phase=0.0):
        n = self.node('ShaderNodeTexWave', wave_type=kind, bands_direction=axis, rings_direction=axis, wave_profile=profile)
        self.set(n, 'Vector', vec)
        self.set(n, 'Scale', scale)
        self.set(n, 'Distortion', distortion)
        self.set(n, 'Detail', detail)
        self.set(n, 'Detail Scale', detail_scale)
        self.set(n, 'Phase Offset', phase)
        return n.outputs['Color'], n.outputs['Fac']

    def gradient(self, vec, kind='LINEAR'):
        n = self.node('ShaderNodeTexGradient', gradient_type=kind)
        self.set(n, 'Vector', vec)
        return n.outputs['Fac']

    def image(self, path, vec=None, interp='Linear', extension='REPEAT', colorspace='sRGB'):
        img = bpy.data.images.load(path, check_existing=True)
        img.colorspace_settings.name = colorspace
        n = self.node('ShaderNodeTexImage', interpolation=interp, extension=extension)
        n.image = img
        if vec is not None:
            self.set(n, 'Vector', vec)
        return n.outputs['Color'], n.outputs['Alpha']

    # ── shading ──
    def bump(self, height, strength=0.2, distance=0.01, normal=None, invert=False):
        n = self.node('ShaderNodeBump', invert=invert)
        self.set(n, 'Height', height)
        self.set(n, 'Strength', strength)
        self.set(n, 'Distance', distance)
        if normal is not None:
            self.set(n, 'Normal', normal)
        return n.outputs['Normal']

    def principled(self, **kw):
        n = self.node('ShaderNodeBsdfPrincipled')
        names = {
            'color': 'Base Color', 'metal': 'Metallic', 'rough': 'Roughness', 'ior': 'IOR', 'alpha': 'Alpha',
            'normal': 'Normal', 'sss': 'Subsurface Weight', 'sss_radius': 'Subsurface Radius',
            'sss_scale': 'Subsurface Scale', 'spec': 'Specular IOR Level', 'spec_tint': 'Specular Tint',
            'transmission': 'Transmission Weight', 'coat': 'Coat Weight', 'coat_rough': 'Coat Roughness',
            'coat_normal': 'Coat Normal', 'coat_tint': 'Coat Tint', 'sheen': 'Sheen Weight', 'sheen_tint': 'Sheen Tint',
            'sheen_rough': 'Sheen Roughness', 'emission': 'Emission Color', 'emission_strength': 'Emission Strength',
            'aniso': 'Anisotropic', 'thin_film': 'Thin Film Thickness',
        }
        for k, v in kw.items():
            self.set(n, names[k], v)
        return n.outputs[0]

    def emission(self, color, strength=1.0):
        n = self.node('ShaderNodeEmission')
        self.set(n, 'Color', color)
        self.set(n, 'Strength', strength)
        return n.outputs[0]

    def transparent(self, color=(1, 1, 1)):
        n = self.node('ShaderNodeBsdfTransparent')
        self.set(n, 'Color', color)
        return n.outputs[0]

    def translucent(self, color, normal=None):
        n = self.node('ShaderNodeBsdfTranslucent')
        self.set(n, 'Color', color)
        if normal is not None:
            self.set(n, 'Normal', normal)
        return n.outputs[0]

    def diffuse(self, color, rough=0.5, normal=None):
        n = self.node('ShaderNodeBsdfDiffuse')
        self.set(n, 'Color', color)
        self.set(n, 'Roughness', rough)
        if normal is not None:
            self.set(n, 'Normal', normal)
        return n.outputs[0]

    def holdout(self):
        return self.node('ShaderNodeHoldout').outputs[0]

    def mix_shader(self, fac, a, b):
        n = self.node('ShaderNodeMixShader')
        self.set(n, 0, fac)
        self.link(a, n.inputs[1])
        self.link(b, n.inputs[2])
        return n.outputs[0]

    def add_shader(self, a, b):
        n = self.node('ShaderNodeAddShader')
        self.link(a, n.inputs[0])
        self.link(b, n.inputs[1])
        return n.outputs[0]

    def background(self, color, strength=1.0):
        n = self.node('ShaderNodeBackground')
        self.set(n, 'Color', color)
        self.set(n, 'Strength', strength)
        return n.outputs[0]

    def output_material(self, surface, displacement=None, volume=None):
        n = self.node('ShaderNodeOutputMaterial')
        self.link(surface, n.inputs['Surface'])
        if displacement is not None:
            self.link(displacement, n.inputs['Displacement'])
        if volume is not None:
            self.link(volume, n.inputs['Volume'])
        return n

    def output_world(self, surface):
        n = self.node('ShaderNodeOutputWorld')
        self.link(surface, n.inputs['Surface'])
        return n


def material(name: str) -> tuple[bpy.types.Material, Graph]:
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, Graph(m.node_tree)


def world(name: str) -> tuple[bpy.types.World, Graph]:
    w = bpy.data.worlds.new(name)
    w.use_nodes = True
    bpy.context.scene.world = w
    return w, Graph(w.node_tree)
