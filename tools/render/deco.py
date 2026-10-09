"""
Mattoni art déco / noir per gli edifici del paese (riferimento: Grim Fandango, Rubacava).

  stepped_tower  torre a gradoni con lesene verticali
  sunburst       raggiera (ventaglio di raggi)
  neon_text      scritta in Limelight (o Monoton) con materiale al neon
  deco_paint     vernice "dipinta": tinta piatta, bordi scuriti, poca grana
"""
from __future__ import annotations

import math
import os

import bpy
import numpy as np

from common import collection, link, set_lightgroup
from geo import rbox, tube
from nodes import material

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
COL = 'env'


def font(name='Limelight-Regular'):
    f = bpy.data.fonts.get(name)
    if f is None:
        f = bpy.data.fonts.load(os.path.join(FONT_DIR, name + '.ttf'))
        f.name = name
    return f


def deco_paint(name, color, edge=0.35, rough=0.6, grime=0.25, emission=None, emission_strength=0.0):
    """Tinta quasi piatta con gli spigoli scuriti (AO) e una leggera sporcizia verticale."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    _, _, z = g.sep(co)
    ao = g.ao(0.6, 8)
    col = g.mix(g.mul(g.sub(1.0, ao), edge), color, (color[0] * 0.25, color[1] * 0.25, color[2] * 0.3))
    streak = g.noise(g.mapping(co, scale=(3.0, 3.0, 0.25)), scale=1.0, detail=3.0).fac
    col = g.mix(g.mul(g.smoothstep(0.55, 0.8, streak), grime), col, (0.05, 0.05, 0.06))
    kw = dict(color=col, rough=rough)
    if emission is not None:
        kw.update(emission=emission, emission_strength=emission_strength)
    g.output_material(g.principled(**kw))
    return m


def neon_material(name, color, strength):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    g.output_material(g.emission(color, strength))
    return m


def place_obj(ob, loc, rot_z):
    ob.location = loc
    ob.rotation_euler = (0, 0, rot_z)
    return ob


def stepped_tower(name, loc, rot_z, base, height, steps=3, shrink=0.72, mat=None, fins=4, fin_mat=None):
    """Torre a gradoni: 'steps' blocchi sovrapposti che si restringono, con lesene sulla facciata."""
    obs = []
    x, y, z = loc
    w, d = base
    hh = height / (steps + 0.6)
    zc = z
    for k in range(steps):
        h = hh * (1.6 if k == 0 else 1.0)
        b = rbox(f'{name}Step{k}', (w, d, h), (0, 0, 0), bevel=min(w, d) * 0.03, col=COL)
        b.location = (x, y, zc + h / 2)
        b.rotation_euler = (0, 0, rot_z)
        if mat:
            b.data.materials.append(mat)
        obs.append(b)
        # lesene verticali sulla facciata rivolta verso −Y locale
        for i in range(fins):
            off = (i - (fins - 1) / 2) * w / (fins + 0.5)
            f = rbox(f'{name}Fin{k}{i}', (w * 0.06, d * 0.08, h * 0.92), (0, 0, 0), bevel=0.0, col=COL)
            lx, ly = off, -d / 2 - d * 0.04
            f.location = (x + lx * math.cos(rot_z) - ly * math.sin(rot_z), y + lx * math.sin(rot_z) + ly * math.cos(rot_z), zc + h / 2)
            f.rotation_euler = (0, 0, rot_z)
            if fin_mat or mat:
                f.data.materials.append(fin_mat or mat)
            obs.append(f)
        zc += h
        w *= shrink
        d *= shrink
    return obs, zc


def sunburst(name, center, rot_z, radius, rays=13, spread=180.0, width=0.06, mat=None):
    """Raggiera a ventaglio nel piano verticale (rivolta verso −Y locale)."""
    obs = []
    cx, cy, cz = center
    for i in range(rays):
        a = math.radians(-spread / 2 + spread * i / (rays - 1)) + math.pi / 2
        r0, r1 = radius * 0.15, radius * (1.0 if i % 2 == 0 else 0.82)
        p0 = (math.cos(a) * r0, 0.0, math.sin(a) * r0)
        p1 = (math.cos(a) * r1, 0.0, math.sin(a) * r1)

        def tw(p):
            lx, ly, lz = p
            return (cx + lx * math.cos(rot_z) - ly * math.sin(rot_z), cy + lx * math.sin(rot_z) + ly * math.cos(rot_z), cz + lz)
        t = tube(f'{name}Ray{i}', [tw(p0), tw(p1)], radius * width * 0.5, n=6, col=COL)
        if mat:
            t.data.materials.append(mat)
        obs.append(t)
    return obs


def neon_text(name, body, size, loc, rot_z, mat, font_name='Limelight-Regular', extrude=0.15, vertical=False, spacing=1.0):
    """Scritta che guarda verso −Y locale (leggibile da chi sta davanti)."""
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body if not vertical else '\n'.join(body)
    cu.font = font(font_name)
    cu.size = size
    cu.extrude = extrude
    cu.bevel_depth = size * 0.015
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.space_character = spacing
    if vertical:
        cu.space_line = 0.85
    ob = bpy.data.objects.new(name, cu)
    collection(COL).objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (math.radians(90), 0, rot_z)
    ob.data.materials.append(mat)
    set_lightgroup(ob, 'ambient')
    return ob
