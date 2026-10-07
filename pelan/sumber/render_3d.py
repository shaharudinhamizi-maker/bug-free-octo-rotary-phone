# -*- coding: utf-8 -*-
"""
Render 3D rumah dua tingkat (Blender Cycles, modul bpy) daripada geometri.py.

Guna:
  python render_3d.py [--view luar|pelan|udara|all] [--quick] [--samples N]
                      [--width W] [--out DIR] [--blend FILE]

  luar  -> Render_3D_Luar.jpg   (paras mata, 3/4 hadapan kanan)
  pelan -> Render_3D_Pelan.jpg  (pelan 3D 'dollhouse' tingkat bawah)
  udara -> Render_3D_Udara.jpg  (pandangan udara 3/4 hadapan kiri)

Unit dalam geometri.py ialah kaki; semua dibina dalam kaki lalu ditukar ke
meter (x 0.3048) semasa mesh dicipta.
"""
import sys
import os
import math
import random
import argparse
import time

import bpy
import bmesh
import addon_utils
from mathutils import Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import geometri as G  # noqa: E402

F = 0.3048                      # kaki -> meter
Z_WALL = 10.5                   # atas dinding putih = aras lantai loteng
Z_CEIL = 10.0                   # siling tingkat bawah / atas dinding dalam
H_ATTIC = Z_WALL                # tangga naik ke loteng
ROOF_EAVE_Z = 11.0              # bumbung pelana pada muka luar dinding barat/timur
RIDGE_X = 22.5                  # perabung utara-selatan (~23.5')
MAIN_SIDE_OV, MAIN_RAKE_OV = 0.3, 0.9
VER_Z_WALL, VER_DROP = 10.5, 2.0   # bumbung veranda: 10.5' di dinding -> 8.5' di tepi luar
Z_LAWN, Z_GRAVEL = -1.5, -1.25
CUT = 8.0                       # aras potongan pelan 3D
CAP = 0.06                      # tebal 'poche' di atas dinding terpotong
POSTS = [(0.2, -5.8), (40.8, -5.8), (0.2, 12.0), (0.2, 29.75), (40.8, 12.0), (40.8, 29.75)]


# ===========================================================================
# Pembina mesh (koordinat dalam kaki)
# ===========================================================================
def newell(pts):
    n = Vector((0, 0, 0))
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]
        n.x += (p[1] - q[1]) * (p[2] + q[2])
        n.y += (p[2] - q[2]) * (p[0] + q[0])
        n.z += (p[0] - q[0]) * (p[1] + q[1])
    return n


class MB:
    """Kumpul verteks/muka untuk satu objek; bina() cipta objek Blender."""

    def __init__(self, name, coll, bevel=0.0):
        self.name, self.coll, self.bevel = name, coll, bevel
        self.v, self.f, self.fm, self.fs, self.fuv, self.mats = [], [], [], [], [], []

    def _mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def add(self, verts, faces, mats, smooth=False, uvs=None):
        i0 = len(self.v)
        self.v.extend([tuple(p) for p in verts])
        for k, fc in enumerate(faces):
            m = mats[k] if isinstance(mats, (list, tuple)) else mats
            sm = smooth[k] if isinstance(smooth, (list, tuple)) else smooth
            self.f.append(tuple(i0 + i for i in fc))
            self.fm.append(self._mi(m))
            self.fs.append(bool(sm))
            self.fuv.append(uvs[k] if uvs else None)

    def face(self, pts, m, uv=None, smooth=False):
        self.add(pts, [tuple(range(len(pts)))], m, smooth, [uv] if uv else None)

    def prism(self, pts, e, m, mtop=None, mbot=None, smooth_sides=False):
        """Poligon satah 'pts' (3D) diunjur sepanjang vektor e."""
        pts = [Vector(p) for p in pts]
        e = Vector(e)
        if newell(pts).dot(e) > 0:
            pts = pts[::-1]
        n = len(pts)
        verts = pts + [p + e for p in pts]
        faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        mats = [mbot or m, mtop or m]
        sm = [False, False]
        for i in range(n):
            j = (i + 1) % n
            faces.append((j, i, n + i, n + j))
            mats.append(m)
            sm.append(smooth_sides)
        self.add(verts, faces, mats, sm)

    def box(self, x0, x1, y0, y1, z0, z1, m, mtop=None, mbot=None):
        if x1 - x0 < 1e-6 or y1 - y0 < 1e-6 or z1 - z0 < 1e-6:
            return
        self.prism([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
                   (0, 0, z1 - z0), m, mtop, mbot)

    def box_slope(self, x0, x1, y0, y1, z0, ztop, m, mtop=None):
        """Kotak dengan bahagian atas condong: ztop(x, y)."""
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, ztop(x0, y0)), (x1, y0, ztop(x1, y0)),
             (x1, y1, ztop(x1, y1)), (x0, y1, ztop(x0, y1))]
        faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        self.add(v, faces, [m, mtop or m, m, m, m, m])

    def cyl(self, cx, cy, rx, z0, z1, m, ry=None, seg=32, mtop=None, r1=None):
        ry = ry if ry is not None else rx
        r1 = r1 if r1 is not None else 1.0     # nisbah jejari atas (tirus)
        n = seg
        bot = [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n), z0) for i in range(n)]
        top = [(cx + r1 * rx * math.cos(2 * math.pi * i / n), cy + r1 * ry * math.sin(2 * math.pi * i / n), z1) for i in range(n)]
        verts = bot + top
        faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
        mats = [m, mtop or m]
        sm = [False, False]
        for i in range(n):
            j = (i + 1) % n
            faces.append((i, j, n + j, n + i))
            mats.append(m)
            sm.append(True)
        self.add(verts, faces, mats, sm)

    def beam(self, p0, p1, w, h, m, up=(0, 0, 1)):
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        s = d.cross(Vector(up))
        if s.length < 1e-6:
            s = d.cross(Vector((1, 0, 0)))
        s.normalize()
        u = s.cross(d).normalized()
        pts = [p0 + s * a * w / 2 + u * b * h / 2 for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        self.prism(pts, d, m)

    def tube(self, pts, radii, m, seg=10, cap=True):
        pts = [Vector(p) for p in pts]
        rings = []
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            ref = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 1, 0))
            a = t.cross(ref).normalized()
            b = t.cross(a).normalized()
            rings.append([p + (a * math.cos(2 * math.pi * k / seg) + b * math.sin(2 * math.pi * k / seg)) * radii[i]
                          for k in range(seg)])
        verts = [v for r in rings for v in r]
        faces, sm = [], []
        for i in range(len(rings) - 1):
            for k in range(seg):
                kk = (k + 1) % seg
                faces.append((i * seg + k, i * seg + kk, (i + 1) * seg + kk, (i + 1) * seg + k))
                sm.append(True)
        if cap:
            faces.append(tuple(range(seg - 1, -1, -1)))
            faces.append(tuple(range((len(rings) - 1) * seg, len(rings) * seg)))
            sm += [False, False]
        self.add(verts, faces, m, sm)

    def blob(self, c, r, m, sub=2, squash=0.85, rough=0.18, seed=0, smooth=True):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
        off = Vector((seed * 7.31, seed * 3.17, seed * 5.71))
        verts = []
        for v in bm.verts:
            p = v.co.copy()
            d = 1.0 + rough * noise.noise(p * 1.7 + off)
            verts.append((c[0] + p.x * r * d, c[1] + p.y * r * d, c[2] + p.z * r * d * squash))
        faces = [tuple(v.index for v in f.verts) for f in bm.faces]
        bm.free()
        self.add(verts, faces, m, smooth)

    def build(self):
        if not self.f:
            return None
        me = bpy.data.meshes.new(self.name)
        me.from_pydata([(x * F, y * F, z * F) for x, y, z in self.v], [], self.f)
        for m in self.mats:
            me.materials.append(m)
        me.polygons.foreach_set('material_index', self.fm)
        me.polygons.foreach_set('use_smooth', self.fs)
        if any(u is not None for u in self.fuv):
            uvl = me.uv_layers.new(name='UVMap')
            flat = [0.0] * (2 * len(me.loops))
            for poly, uv in zip(me.polygons, self.fuv):
                if uv is None:
                    continue
                for k, li in enumerate(poly.loop_indices):
                    flat[2 * li] = uv[k][0]
                    flat[2 * li + 1] = uv[k][1]
            uvl.data.foreach_set('uv', flat)
        me.validate()
        me.update()
        ob = bpy.data.objects.new(self.name, me)
        self.coll.objects.link(ob)
        if self.bevel > 0:
            md = ob.modifiers.new('bevel', 'BEVEL')
            md.width = self.bevel * F
            md.segments = 2
            md.limit_method = 'ANGLE'
            md.harden_normals = False
        return ob


BUILDERS = []


def mb(name, coll, bevel=0.0):
    b = MB(name, coll, bevel)
    BUILDERS.append(b)
    return b


# ===========================================================================
# Bahan (material)
# ===========================================================================
def _in(node, key):
    for s in node.inputs:
        if s.identifier == key:
            return s
    return node.inputs[key]


def _out(node, key):
    for s in node.outputs:
        if s.identifier == key:
            return s
    return node.outputs[key]


class NT:
    def __init__(self, name):
        self.mat = bpy.data.materials.new(name)
        if self.mat.node_tree is None:
            self.mat.use_nodes = True
        self.t = self.mat.node_tree
        for n in list(self.t.nodes):
            self.t.nodes.remove(n)
        self.out = self.t.nodes.new('ShaderNodeOutputMaterial')
        self._coord = None

    def n(self, typ, **kw):
        node = self.t.nodes.new(typ)
        for k, v in kw.items():
            if hasattr(node, k) and not isinstance(v, bpy.types.NodeSocket) and k not in ('inputs',):
                try:
                    setattr(node, k, v)
                    continue
                except (TypeError, AttributeError):
                    pass
            self.set(node, k.replace('_', ' ') if k not in [s.identifier for s in node.inputs] else k, v)
        return node

    def set(self, node, key, val):
        s = _in(node, key)
        if isinstance(val, bpy.types.NodeSocket):
            self.t.links.new(val, s)
        else:
            if s.type == 'RGBA' and len(val) == 3:
                val = (*val, 1.0)
            s.default_value = val

    def link(self, a, b):
        self.t.links.new(a, b)

    def obj(self):
        if self._coord is None:
            self._coord = self.t.nodes.new('ShaderNodeTexCoord')
        return self._coord.outputs['Object']

    def uv(self):
        if self._coord is None:
            self._coord = self.t.nodes.new('ShaderNodeTexCoord')
        return self._coord.outputs['UV']

    def mix(self, a, b, fac, blend='MIX'):
        m = self.t.nodes.new('ShaderNodeMix')
        m.data_type = 'RGBA'
        m.blend_type = blend
        self.set(m, 'Factor_Float', fac)
        self.set(m, 'A_Color', a)
        self.set(m, 'B_Color', b)
        return _out(m, 'Result_Color')

    def math(self, op, a, b=0.0):
        m = self.t.nodes.new('ShaderNodeMath')
        m.operation = op
        for i, v in enumerate((a, b)):
            if isinstance(v, bpy.types.NodeSocket):
                self.link(v, m.inputs[i])
            else:
                m.inputs[i].default_value = v
        return m.outputs[0]

    def xyz(self, vec):
        s = self.t.nodes.new('ShaderNodeSeparateXYZ')
        self.link(vec, s.inputs[0])
        return s.outputs

    def comb(self, x, y, z=0.0):
        c = self.t.nodes.new('ShaderNodeCombineXYZ')
        for i, v in enumerate((x, y, z)):
            if isinstance(v, bpy.types.NodeSocket):
                self.link(v, c.inputs[i])
            else:
                c.inputs[i].default_value = v
        return c.outputs[0]

    def noise(self, vec, scale, detail=2.0, rough=0.5):
        n = self.t.nodes.new('ShaderNodeTexNoise')
        self.link(vec, n.inputs['Vector'])
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        return n.outputs['Fac']

    def bump(self, height, strength, dist, normal=None, invert=False):
        b = self.t.nodes.new('ShaderNodeBump')
        b.invert = invert
        self.link(height, b.inputs['Height'])
        b.inputs['Strength'].default_value = strength
        b.inputs['Distance'].default_value = dist
        if normal is not None:
            self.link(normal, b.inputs['Normal'])
        return b.outputs['Normal']

    def principled(self, base, rough=0.5, metal=0.0, normal=None, spec=0.5, **kw):
        b = self.t.nodes.new('ShaderNodeBsdfPrincipled')
        self.set(b, 'Base Color', base)
        self.set(b, 'Roughness', rough)
        self.set(b, 'Metallic', metal)
        self.set(b, 'Specular IOR Level', spec)
        if normal is not None:
            self.link(normal, b.inputs['Normal'])
        for k, v in kw.items():
            self.set(b, k.replace('_', ' '), v)
        return b.outputs[0]

    def done(self, shader, viewport=(0.5, 0.5, 0.5)):
        self.link(shader, self.out.inputs['Surface'])
        self.mat.diffuse_color = (*viewport[:3], 1.0)
        return self.mat


def scl(c, k):
    return tuple(min(1.0, max(0.0, x * k)) for x in c)


def mat_plain(name, col, rough=0.6, metal=0.0, var=0.0, vscale=3.0, bump=0.0, bscale=40.0, spec=0.5, **kw):
    t = NT(name)
    base = col
    if var > 0:
        base = t.mix(scl(col, 1 - var), scl(col, 1 + var), t.noise(t.obj(), vscale, 3.0))
    nrm = t.bump(t.noise(t.obj(), bscale, 4.0), bump, 0.002) if bump > 0 else None
    return t.done(t.principled(base, rough, metal, nrm, spec, **kw), col)


def _plane_vec(t, plane):
    """Vektor 2D untuk corak: 'xy' lantai, 'v' muka tegak (x+y, z), 'vt' tegak (z, x+y)."""
    if plane == 'xy':
        return t.obj()
    o = t.xyz(t.obj())
    s = t.math('ADD', o[0], o[1])
    if plane == 'v':
        return t.comb(s, o[2])
    return t.comb(o[2], s)


def mat_tile(name, col, mortar, w, h, rough, var=0.07, offset=0.0, plane='xy', gap=0.003,
             bump=0.4, grain=0.0, grain_scale=(1.5, 40.0), vscale=0.6, spec=0.5):
    t = NT(name)
    vec = _plane_vec(t, plane)
    br = t.n('ShaderNodeTexBrick', offset=offset, offset_frequency=2, squash=1.0, squash_frequency=2)
    t.link(vec, br.inputs['Vector'])
    t.set(br, 'Color1', scl(col, 1 - var))
    t.set(br, 'Color2', scl(col, 1 + var))
    t.set(br, 'Mortar', mortar)
    t.set(br, 'Scale', 1.0)
    t.set(br, 'Mortar Size', gap)
    t.set(br, 'Mortar Smooth', 0.2)
    t.set(br, 'Bias', 0.0)
    t.set(br, 'Brick Width', w)
    t.set(br, 'Row Height', h)
    col_out = br.outputs['Color']
    # variasi halus besar
    col_out = t.mix(col_out, scl(col, 0.9), t.math('MULTIPLY', t.noise(t.obj(), vscale, 3.0), 0.35), 'MULTIPLY') \
        if vscale else col_out
    if grain > 0:
        o = t.xyz(vec)
        gv = t.comb(t.math('MULTIPLY', o[0], grain_scale[0]), t.math('MULTIPLY', o[1], grain_scale[1]), o[2])
        g = t.noise(gv, 4.0, 6.0, 0.6)
        col_out = t.mix(col_out, t.mix((0.55, 0.45, 0.35), (1.0, 1.0, 1.0), g), grain, 'MULTIPLY')
    nrm = t.bump(br.outputs['Fac'], bump, 0.002, invert=True) if bump > 0 else None
    return t.done(t.principled(col_out, rough, 0.0, nrm, spec), col)


def mat_roof(name, col):
    """Genting konkrit: UV (u sepanjang cucur, v naik cerun) dalam meter."""
    t = NT(name)
    uv = t.uv()
    br = t.n('ShaderNodeTexBrick', offset=0.5, offset_frequency=2, squash=1.0, squash_frequency=2)
    t.link(uv, br.inputs['Vector'])
    t.set(br, 'Color1', scl(col, 0.8))
    t.set(br, 'Color2', scl(col, 1.25))
    t.set(br, 'Mortar', scl(col, 0.4))
    t.set(br, 'Scale', 1.0)
    t.set(br, 'Mortar Size', 0.004)
    t.set(br, 'Mortar Smooth', 0.3)
    t.set(br, 'Bias', 0.0)
    t.set(br, 'Brick Width', 0.42)
    t.set(br, 'Row Height', 0.32)
    o = t.xyz(uv)
    # tangga tindihan genting (gigi gergaji) + profil gelombang melintang
    saw = t.math('FRACT', t.math('DIVIDE', o[1], 0.32))
    wave = t.math('SINE', t.math('MULTIPLY', o[0], 2 * math.pi / 0.21))
    h = t.math('ADD', t.math('MULTIPLY', t.math('SUBTRACT', 1.0, saw), 0.7), t.math('MULTIPLY', wave, 0.25))
    h = t.math('SUBTRACT', h, t.math('MULTIPLY', br.outputs['Fac'], 0.6))
    nrm = t.bump(h, 0.55, 0.012)
    dirt = t.noise(t.obj(), 0.8, 4.0)
    base = t.mix(br.outputs['Color'], scl(col, 1.3), t.math('MULTIPLY', dirt, 0.5))
    rough = t.math('ADD', 0.45, t.math('MULTIPLY', dirt, 0.25))
    return t.done(t.principled(base, rough, 0.0, nrm, 0.5), col)


def mat_lawn(name):
    t = NT(name)
    o = t.obj()
    n1 = t.noise(o, 0.35, 4.0, 0.6)
    n2 = t.noise(o, 3.0, 6.0, 0.6)
    vor = t.n('ShaderNodeTexVoronoi')
    t.link(o, vor.inputs['Vector'])
    vor.inputs['Scale'].default_value = 260.0
    c = t.mix((0.035, 0.11, 0.018), (0.09, 0.19, 0.035), n1)
    c = t.mix(c, (0.13, 0.17, 0.05), t.math('MULTIPLY', t.math('GREATER_THAN', n2, 0.58), 0.6))
    c = t.mix(c, (0.6, 0.75, 0.5), t.math('MULTIPLY', vor.outputs['Distance'], 0.35), 'MULTIPLY')
    nrm = t.bump(vor.outputs['Distance'], 0.6, 0.004)
    return t.done(t.principled(c, 0.85, 0.0, nrm, 0.3), (0.06, 0.16, 0.03))


def mat_leaf(name, c1, c2, trans=0.25):
    t = NT(name)
    o = t.obj()
    vor = t.n('ShaderNodeTexVoronoi')
    t.link(o, vor.inputs['Vector'])
    vor.inputs['Scale'].default_value = 14.0
    c = t.mix(c1, c2, t.noise(o, 1.2, 3.0))
    c = t.mix(c, scl(c2, 1.4), t.math('MULTIPLY', vor.outputs['Distance'], 0.5))
    nrm = t.bump(vor.outputs['Distance'], 0.9, 0.03)
    p = t.principled(c, 0.55, 0.0, nrm, 0.4)
    tr = t.n('ShaderNodeBsdfTranslucent')
    t.set(tr, 'Color', scl(c2, 1.3))
    t.link(nrm, tr.inputs['Normal'])
    ms = t.n('ShaderNodeMixShader')
    ms.inputs[0].default_value = trans
    t.link(p, ms.inputs[1])
    t.link(tr.outputs[0], ms.inputs[2])
    return t.done(ms.outputs[0], c1)


def mat_glass(name, tint=(0.80, 0.90, 0.93)):
    t = NT(name)
    g = t.n('ShaderNodeBsdfGlass')
    t.set(g, 'Color', tint)
    t.set(g, 'Roughness', 0.0)
    t.set(g, 'IOR', 1.5)
    tr = t.n('ShaderNodeBsdfTransparent')
    t.set(tr, 'Color', tint)
    lp = t.n('ShaderNodeLightPath')
    fac = t.math('MAXIMUM', lp.outputs['Is Shadow Ray'], lp.outputs['Is Diffuse Ray'])
    ms = t.n('ShaderNodeMixShader')
    t.link(fac, ms.inputs[0])
    t.link(g.outputs[0], ms.inputs[1])
    t.link(tr.outputs[0], ms.inputs[2])
    return t.done(ms.outputs[0], (0.6, 0.75, 0.8))


def mat_curtain(name, col=(0.92, 0.90, 0.86)):
    t = NT(name)
    o = t.xyz(t.obj())
    folds = t.math('SINE', t.math('MULTIPLY', t.math('ADD', o[0], o[1]), 40.0))
    nrm = t.bump(folds, 0.6, 0.01)
    d = t.principled(col, 0.9, 0.0, nrm, 0.2)
    tr = t.n('ShaderNodeBsdfTranslucent')
    t.set(tr, 'Color', col)
    ms = t.n('ShaderNodeMixShader')
    ms.inputs[0].default_value = 0.45
    t.link(d, ms.inputs[1])
    t.link(tr.outputs[0], ms.inputs[2])
    return t.done(ms.outputs[0], col)


def mat_gravel(name):
    t = NT(name)
    o = t.obj()
    vor = t.n('ShaderNodeTexVoronoi')
    t.link(o, vor.inputs['Vector'])
    vor.inputs['Scale'].default_value = 90.0
    c = t.mix((0.05, 0.05, 0.05), (0.20, 0.19, 0.18), vor.outputs['Color'])
    c = t.mix(c, (0.6, 0.6, 0.6), t.math('MULTIPLY', t.noise(o, 1.0, 3.0), 0.5), 'MULTIPLY')
    nrm = t.bump(vor.outputs['Distance'], 1.0, 0.01, invert=True)
    return t.done(t.principled(c, 0.8, 0.0, nrm, 0.4), (0.12, 0.12, 0.12))


def mat_metal_sheet(name, col):
    """Kepingan zink bercat: atas merah berkilat, bawah kelabu zink."""
    t = NT(name)
    g = t.n('ShaderNodeNewGeometry')
    base = t.mix(scl(col, 0.9), scl(col, 1.12), t.noise(t.obj(), 1.5, 3.0))
    base = t.mix(base, (0.42, 0.42, 0.40), g.outputs['Backfacing'])
    nrm = t.bump(t.noise(t.obj(), 25.0, 3.0), 0.05, 0.002)
    return t.done(t.principled(base, 0.36, 0.25, nrm, 0.5), col)


def mat_emit(name, col, strength):
    t = NT(name)
    e = t.n('ShaderNodeEmission')
    t.set(e, 'Color', col)
    t.set(e, 'Strength', strength)
    return t.done(e.outputs[0], col)


def make_materials():
    M = {}
    M['render'] = mat_plain('render_putih', (0.80, 0.79, 0.76), 0.88, var=0.025, vscale=2.0, bump=0.15, bscale=60)
    M['paint'] = mat_plain('cat_dalam', (0.80, 0.78, 0.74), 0.9, var=0.015)
    M['cap'] = mat_plain('poche', (0.10, 0.10, 0.11), 0.8)
    M['stone_v'] = mat_tile('batu_dinding', (0.30, 0.30, 0.29), (0.16, 0.16, 0.16), 0.6, 0.3, 0.7, plane='v', var=0.12)
    M['stone_h'] = mat_tile('batu_anjung', (0.42, 0.41, 0.39), (0.25, 0.25, 0.24), 0.6, 0.6, 0.6, var=0.08)
    M['porcelain'] = mat_tile('porselin', (0.80, 0.78, 0.74), (0.62, 0.60, 0.57), 0.6, 0.6, 0.22, var=0.03, spec=0.6)
    M['oak'] = mat_tile('papan_oak', (0.50, 0.33, 0.18), (0.18, 0.12, 0.07), 1.2, 0.15, 0.4, var=0.12,
                        offset=0.5, gap=0.0015, grain=0.5, bump=0.3)
    M['tile_grey'] = mat_tile('jubin_kelabu', (0.46, 0.46, 0.45), (0.3, 0.3, 0.3), 0.3, 0.3, 0.35, var=0.04)
    M['tile_wall'] = mat_tile('jubin_dinding', (0.78, 0.78, 0.76), (0.6, 0.6, 0.6), 0.3, 0.6, 0.15, plane='vt',
                              var=0.02, offset=0.5)
    M['paver'] = mat_plain('turap', (0.55, 0.53, 0.49), 0.75, var=0.08, vscale=2.0, bump=0.3, bscale=30)
    M['lawn'] = mat_lawn('rumput')
    M['soil'] = mat_plain('tanah', (0.10, 0.07, 0.045), 0.95, var=0.2, bump=0.6, bscale=20)
    M['roof'] = mat_roof('genting', (0.07, 0.075, 0.08))
    M['roof_cap'] = mat_plain('genting_perabung', (0.06, 0.063, 0.068), 0.5)
    M['fascia'] = mat_plain('papan_cucur', (0.86, 0.86, 0.85), 0.5)
    M['soffit'] = mat_plain('siling', (0.82, 0.82, 0.80), 0.85)
    M['alu'] = mat_plain('aluminium', (0.045, 0.047, 0.05), 0.38, metal=0.7)
    M['glass'] = mat_glass('kaca')
    M['clad'] = mat_tile('kayu_dinding', (0.46, 0.25, 0.11), (0.06, 0.035, 0.02), 2.4, 0.11, 0.55, var=0.15,
                         plane='vt', offset=0.5, gap=0.006, grain=0.35, grain_scale=(1.5, 30.0), bump=0.8)
    M['door_main'] = mat_tile('pintu_utama', (0.13, 0.065, 0.03), (0.04, 0.02, 0.01), 3.0, 0.16, 0.45,
                              var=0.1, plane='vt', gap=0.004, grain=0.4, bump=0.6)
    M['door_int'] = mat_tile('pintu_dalam', (0.62, 0.48, 0.33), (0.5, 0.4, 0.3), 3.0, 1.0, 0.45, var=0.04,
                             plane='vt', gap=0.0, grain=0.35, bump=0.0)
    M['steel'] = mat_plain('keluli', (0.75, 0.75, 0.74), 0.25, metal=1.0)
    M['sofa'] = mat_plain('fabrik_sofa', (0.60, 0.56, 0.50), 0.95, var=0.03, bump=0.3, bscale=300,
                          **{'Sheen Weight': 0.4})
    M['cush1'] = mat_plain('kusyen_bata', (0.55, 0.24, 0.13), 0.95, **{'Sheen Weight': 0.4})
    M['cush2'] = mat_plain('kusyen_hijau', (0.30, 0.40, 0.31), 0.95, **{'Sheen Weight': 0.4})
    M['cush3'] = mat_plain('kusyen_kuning', (0.70, 0.52, 0.18), 0.95, **{'Sheen Weight': 0.4})
    M['wood'] = mat_tile('kayu_perabot', (0.38, 0.22, 0.11), (0.3, 0.18, 0.1), 2.0, 0.6, 0.4, var=0.03,
                         gap=0.0, grain=0.45, bump=0.0, vscale=0)
    M['wood_light'] = mat_tile('kayu_cerah', (0.62, 0.46, 0.30), (0.5, 0.4, 0.3), 2.0, 0.6, 0.45, var=0.03,
                               gap=0.0, grain=0.35, bump=0.0, vscale=0)
    M['black'] = mat_plain('hitam', (0.025, 0.025, 0.027), 0.5)
    M['screen'] = mat_plain('skrin', (0.005, 0.005, 0.006), 0.08)
    M['ceramic'] = mat_plain('seramik', (0.88, 0.88, 0.87), 0.12, **{'Coat Weight': 0.3})
    M['cabinet'] = mat_plain('kabinet', (0.30, 0.36, 0.32), 0.55)
    M['quartz'] = mat_plain('kuarza', (0.86, 0.85, 0.83), 0.2, var=0.03, vscale=8)
    M['linen'] = mat_plain('cadar', (0.90, 0.89, 0.86), 0.9, bump=0.2, bscale=80, **{'Sheen Weight': 0.3})
    M['duvet'] = mat_plain('selimut', (0.40, 0.48, 0.55), 0.95, bump=0.3, bscale=50, **{'Sheen Weight': 0.4})
    M['rug'] = mat_plain('permaidani', (0.62, 0.57, 0.49), 1.0, var=0.06, vscale=6, bump=0.5, bscale=200)
    M['rug2'] = mat_plain('permaidani2', (0.33, 0.37, 0.42), 1.0, var=0.05, vscale=6, bump=0.5, bscale=200)
    M['leaf'] = mat_leaf('daun', (0.035, 0.12, 0.02), (0.09, 0.24, 0.04))
    M['leaf2'] = mat_leaf('daun_gelap', (0.025, 0.08, 0.02), (0.06, 0.16, 0.035))
    M['leaf3'] = mat_leaf('daun_cerah', (0.07, 0.18, 0.03), (0.16, 0.30, 0.05))
    M['trunk'] = mat_plain('batang', (0.13, 0.10, 0.075), 0.9, var=0.2, vscale=10, bump=0.8, bscale=25)
    M['palm_trunk'] = mat_plain('batang_palma', (0.32, 0.29, 0.24), 0.9, var=0.15, vscale=8, bump=0.6, bscale=12)
    M['pot_terra'] = mat_plain('pasu_tanah', (0.45, 0.22, 0.12), 0.8, var=0.05)
    M['pot_dark'] = mat_plain('pasu_gelap', (0.09, 0.09, 0.09), 0.6, var=0.05)
    M['curtain'] = mat_curtain('langsir')
    M['mirror'] = mat_plain('cermin', (0.9, 0.9, 0.9), 0.02, metal=1.0)
    M['brass'] = mat_plain('loyang', (0.75, 0.55, 0.28), 0.3, metal=1.0)
    M['shade'] = mat_emit('lampu', (1.0, 0.82, 0.6), 3.0)
    M['appliance'] = mat_plain('perkakas', (0.90, 0.90, 0.90), 0.3)
    M['book'] = mat_plain('buku', (0.5, 0.35, 0.3), 0.8, var=0.4, vscale=30)
    # --- reka bentuk pengguna: bumbung zink merah, kayu merah-perang ---
    M['metal'] = mat_metal_sheet('zink_merah', (0.30, 0.042, 0.036))
    M['frame'] = mat_tile('kayu_bingkai', (0.10, 0.026, 0.015), (0.08, 0.02, 0.01), 2.0, 0.6, 0.45, var=0.05,
                          plane='vt', gap=0.0, grain=0.3, bump=0.0, vscale=0)
    M['boards'] = mat_tile('papan_gable', (0.19, 0.072, 0.03), (0.035, 0.015, 0.008), 3.0, 0.17, 0.6,
                           var=0.14, plane='v', offset=0.5, gap=0.008, grain=0.35, grain_scale=(1.0, 30.0),
                           bump=0.9)
    M['post'] = mat_tile('kayu_tiang', (0.15, 0.065, 0.028), (0.1, 0.05, 0.02), 3.0, 0.5, 0.55, var=0.06,
                         plane='vt', gap=0.0, grain=0.4, bump=0.0, vscale=0)
    M['slat'] = mat_tile('bilah_kayu', (0.40, 0.21, 0.08), (0.3, 0.15, 0.06), 3.0, 0.5, 0.5, var=0.1,
                         plane='vt', gap=0.0, grain=0.35, bump=0.0, vscale=0)
    M['terracotta'] = mat_tile('jubin_terakota', (0.50, 0.17, 0.065), (0.33, 0.28, 0.22), 0.3, 0.3, 0.55,
                               var=0.14, gap=0.004, bump=0.5)
    M['brick'] = mat_tile('bata_merah', (0.30, 0.075, 0.042), (0.42, 0.40, 0.37), 0.215, 0.075, 0.85,
                          var=0.25, plane='v', offset=0.5, gap=0.01, bump=1.0)
    M['gravel'] = mat_gravel('kerikil')
    M['lamp_glass'] = mat_emit('kaca_tanglung', (1.0, 0.78, 0.5), 4.0)
    M['yellow'] = mat_plain('pasu_kuning', (0.72, 0.46, 0.02), 0.12, var=0.05, vscale=4,
                            **{'Coat Weight': 0.6})
    return M


# ===========================================================================
# Utiliti dinding & bukaan
# ===========================================================================
def _subtract(intervals, holes):
    out = list(intervals)
    for h0, h1 in holes:
        nxt = []
        for a, b in out:
            if h1 <= a or h0 >= b:
                nxt.append((a, b))
                continue
            if h0 > a:
                nxt.append((a, h0))
            if h1 < b:
                nxt.append((h1, b))
        out = nxt
    return [(a, b) for a, b in out if b - a > 1e-4]


def openings_in(rect, ops, eps=0.01):
    x0, x1, y0, y1 = rect[:4]
    return [o for o in ops if o[0] >= x0 - eps and o[1] <= x1 + eps and o[2] >= y0 - eps and o[3] <= y1 + eps]


def build_wall(b, rect, ops, z0, z1, m, ztop=None, cap_mat=None, mtop=None):
    """Dinding sebagai segmen kotak; bukaan dipotong pada julat z masing-masing."""
    x0, x1, y0, y1 = rect[:4]
    horiz = (x1 - x0) >= (y1 - y0)
    a0, a1 = (x0, x1) if horiz else (y0, y1)
    cuts = [((o[0], o[1]) if horiz else (o[2], o[3])) + (o[5], o[6]) for o in ops]
    pts = sorted(set([a0, a1] + [max(a0, min(a1, c[0])) for c in cuts] + [max(a0, min(a1, c[1])) for c in cuts]))
    zc = z1 - CAP if cap_mat else z1
    for s, e in zip(pts[:-1], pts[1:]):
        if e - s < 1e-4:
            continue
        mid = (s + e) / 2
        holes = [(c[2], c[3]) for c in cuts if c[0] <= mid <= c[1]]
        for za, zb in _subtract([(z0, zc)], holes):
            bx = (s, e, y0, y1) if horiz else (x0, x1, s, e)
            if ztop is not None and abs(zb - zc) < 1e-6:
                b.box_slope(bx[0], bx[1], bx[2], bx[3], za, ztop, m)
            else:
                b.box(*bx, za, zb, m, mtop=mtop)
    if cap_mat:
        b.box(x0, x1, y0, y1, zc, z1, cap_mat)


def outward(o):
    """Arah luar bukaan pada dinding luar: (paksi, tanda)."""
    x0, x1, y0, y1 = o[:4]
    if (x1 - x0) >= (y1 - y0):
        return 'y', (-1 if (y0 + y1) / 2 < 15 else 1)
    return 'x', (-1 if (x0 + x1) / 2 < 17.5 else 1)


def _B(b, horiz, a0, a1, d0, d1, z0, z1, m):
    if horiz:
        b.box(a0, a1, d0, d1, z0, z1, m)
    else:
        b.box(d0, d1, a0, a1, z0, z1, m)


def build_window(bf, bg, o, M, panes=None, transom=None):
    """Tingkap bingkai kayu merah-perang, kaca jernih, dekat muka luar dinding."""
    x0, x1, y0, y1, _, s, h = o
    horiz = (x1 - x0) >= (y1 - y0)
    a0, a1 = (x0, x1) if horiz else (y0, y1)
    w0, w1 = (y0, y1) if horiz else (x0, x1)
    ax, sg = outward(o)
    fd, fw = 0.3, 0.2
    if sg < 0:
        d0 = w0 + 0.06
        d1 = d0 + fd
    else:
        d1 = w1 - 0.06
        d0 = d1 - fd
    c = (d0 + d1) / 2
    tm = M['frame']
    _B(bf, horiz, a0, a1, d0, d1, s, s + fw, tm)
    _B(bf, horiz, a0, a1, d0, d1, h - fw, h, tm)
    _B(bf, horiz, a0, a0 + fw, d0, d1, s + fw, h - fw, tm)
    _B(bf, horiz, a1 - fw, a1, d0, d1, s + fw, h - fw, tm)
    n = panes or max(1, int(round((a1 - a0) / 1.6)))
    for i in range(1, n):
        a = a0 + i * (a1 - a0) / n
        _B(bf, horiz, a - 0.06, a + 0.06, d0 + 0.04, d1 - 0.04, s + fw, h - fw, tm)
    if transom:
        zt = s + transom * (h - s)
        _B(bf, horiz, a0 + fw, a1 - fw, d0 + 0.05, d1 - 0.05, zt - 0.06, zt + 0.06, tm)
    _B(bg, horiz, a0 + fw * 0.5, a1 - fw * 0.5, c - 0.015, c + 0.015, s + fw * 0.5, h - fw * 0.5, M['glass'])
    # ambang luar kayu
    if sg < 0:
        _B(bf, horiz, a0 - 0.1, a1 + 0.1, w0 - 0.15, d0, s - 0.1, s + 0.03, tm)
    else:
        _B(bf, horiz, a0 - 0.1, a1 + 0.1, d1, w1 + 0.15, s - 0.1, s + 0.03, tm)


def leaves_for(o):
    x0, x1, y0, y1 = o[:4]
    res = []
    for hx, hy, r, _, cd in G.DOOR_LEAVES:
        if x0 - 0.01 <= hx <= x1 + 0.01 and y0 - 0.01 <= hy <= y1 + 0.01:
            ex, ey = hx + r * math.cos(math.radians(cd)), hy + r * math.sin(math.radians(cd))
            res.append((hx, hy, ex, ey))
    return res


def build_door(bf, bl, bg, o, M, main=False):
    x0, x1, y0, y1, _, s, h = o
    horiz = (x1 - x0) >= (y1 - y0)
    a0, a1 = (x0, x1) if horiz else (y0, y1)
    w0, w1 = (y0, y1) if horiz else (x0, x1)
    c = (w0 + w1) / 2
    fw = 0.18
    fm = M['frame']
    _B(bf, horiz, a0, a0 + fw, w0 - 0.03, w1 + 0.03, 0, h - fw, fm)
    _B(bf, horiz, a1 - fw, a1, w0 - 0.03, w1 + 0.03, 0, h - fw, fm)
    _B(bf, horiz, a0, a1, w0 - 0.03, w1 + 0.03, h - fw, h, fm)
    lt = 0.16 if main else 0.13
    lc = 0.25 if main else c
    ht = h - fw - 0.01
    for hx, hy, ex, ey in leaves_for(o):
        p0, p1 = (hx, ex) if horiz else (hy, ey)
        la, lb = max(min(p0, p1), a0 + fw), min(max(p0, p1), a1 - fw)
        hinge_lo = p0 < p1
        if abs(p1 - p0) < (a1 - a0) - 0.5:      # daun berkembar: celah kecil di tengah
            if hinge_lo:
                lb -= 0.01
            else:
                la += 0.01
        d0, d1 = lc - lt / 2, lc + lt / 2
        if main:
            # pintu kayu berpanel kaca (atas) + panel bawah
            st = 0.33
            lm = M['frame']
            _B(bl, horiz, la, la + st, d0, d1, 0.03, ht, lm)
            _B(bl, horiz, lb - st, lb, d0, d1, 0.03, ht, lm)
            _B(bl, horiz, la + st, lb - st, d0, d1, 0.03, 0.75, lm)
            _B(bl, horiz, la + st, lb - st, d0, d1, 2.9, 3.25, lm)
            _B(bl, horiz, la + st, lb - st, d0, d1, ht - 0.35, ht, lm)
            _B(bl, horiz, la + st, lb - st, lc - 0.04, lc + 0.04, 0.75, 2.9, M['door_int'])
            _B(bg, horiz, la + st, lb - st, lc - 0.015, lc + 0.015, 3.25, ht - 0.35, M['glass'])
            zm = (3.25 + ht - 0.35) / 2
            _B(bl, horiz, la + st, lb - st, d0 + 0.03, d1 - 0.03, zm - 0.04, zm + 0.04, lm)
            if lb - la > 2:
                am = (la + lb) / 2
                _B(bl, horiz, am - 0.04, am + 0.04, d0 + 0.035, d1 - 0.035, 3.25, ht - 0.35, lm)
                fe = lb - 0.5 if hinge_lo else la + 0.4
                _B(bl, horiz, fe, fe + 0.08, d0 - 0.2, d0 - 0.12, 2.6, 4.6, M['brass'])
                _B(bl, horiz, fe, fe + 0.08, d0 - 0.12, d0, 2.7, 2.78, M['brass'])
                _B(bl, horiz, fe, fe + 0.08, d0 - 0.12, d0, 4.42, 4.5, M['brass'])
        else:
            _B(bl, horiz, la, lb, d0, d1, 0.03, ht, M['door_int'])
            free = lb - 0.35 if hinge_lo else la + 0.15
            for sg in (-1, 1):
                dd = lc + sg * (lt / 2 + 0.06)
                _B(bl, horiz, free, free + 0.2, dd - 0.03, dd + 0.03, 3.3, 3.37, M['brass'])


# ===========================================================================
# Pembinaan bangunan
# ===========================================================================
# ---------------------------------------------------------------------------
# Bumbung: fungsi aras permukaan (kaki)
# ---------------------------------------------------------------------------
def roof_top(x, y=0.0):
    """Bumbung pelana utama 45 darjah, perabung U-S pada X=RIDGE_X."""
    return ROOF_EAVE_Z + (RIDGE_X - 10.0) - abs(x - RIDGE_X)


def ver_front(x, y):
    return VER_Z_WALL + y * (VER_DROP / 6.5)


def ver_west(x, y):
    return VER_Z_WALL + (x - 10.0) * (VER_DROP / 10.5)


def ver_east(x, y):
    return VER_Z_WALL - (x - 35.0) * (VER_DROP / 6.5)


def ver_top(x, y):
    """Aras atas bumbung veranda (cucur pinggul: minimum satah)."""
    zs = []
    if y <= 0:
        zs.append(ver_front(x, y))
    if x <= 10:
        zs.append(ver_west(x, y))
    if x >= 35:
        zs.append(ver_east(x, y))
    return min(zs) if zs else VER_Z_WALL


def clip_half(poly, ud, c, sign):
    """Kekalkan bahagian poligon (xy) dengan sign*(u - c) >= 0, u = p.ud."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp = sign * (p[0] * ud[0] + p[1] * ud[1] - c)
        fq = sign * (q[0] * ud[0] + q[1] * ud[1] - c)
        if fp >= 0:
            out.append(p)
        if (fp >= 0) != (fq >= 0):
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def ribbed(b, region, plane, ud, m, P=0.75, h=0.1):
    """Kepingan logam trapezoid: rusuk menurun cerun, dijarakkan sepanjang ud."""
    us = [p[0] * ud[0] + p[1] * ud[1] for p in region]
    umin, umax = min(us), max(us)
    prof = []
    k = math.floor(umin / P)
    while k * P < umax:
        for du, hh in ((0.0, 0.0), (0.47, 0.0), (0.55, h), (0.67, h)):
            prof.append((k * P + du, hh))
        k += 1
    prof.append((k * P, 0.0))
    for (ua, ha), (ub, hb) in zip(prof[:-1], prof[1:]):
        poly = clip_half(region, ud, ua, 1)
        poly = clip_half(poly, ud, ub, -1) if len(poly) >= 3 else []
        if len(poly) < 3:
            continue
        verts = []
        for x, y in poly:
            t = (x * ud[0] + y * ud[1] - ua) / (ub - ua)
            verts.append((x, y, plane(x, y) + ha + (hb - ha) * t))
        b.face(verts, m)


def win_sill(o):
    """Ambang tingkap ikut model pengguna (~2.5')."""
    return 2.5 if (o[4] == 'win' and abs(o[5] - G.SILL) < 1e-6) else o[5]


def ground_openings():
    res = []
    for o in G.OPENINGS:
        if o[1] <= 0.51:          # tingkap dinding barat dapur -> kini skrin kayu
            continue
        res.append((o[0], o[1], o[2], o[3], o[4], win_sill(o), o[6]))
    return res


def build_ground(C, M):
    g = mb('tanah_rumput', C['common'])
    g.face([(-400, -400, Z_LAWN), (420, -400, Z_LAWN), (420, 420, Z_LAWN), (-400, 420, Z_LAWN)], M['lawn'])
    b = mb('tapak', C['common'])
    sv = M['stone_v']
    b.box(10, 35, 0, 30, Z_LAWN, -0.05, sv)               # tapak rumah
    b.box(0, 10, -6, 30, Z_LAWN, -0.05, sv)               # pelantar dapur & dobi
    gr = mb('kerikil', C['common'])
    gr.box(10, 41, -6, 0, Z_LAWN - 0.1, Z_GRAVEL, M['gravel'])       # jalur anjung hadapan
    gr.box(35, 41, 0, 30.5, Z_LAWN - 0.1, Z_GRAVEL, M['gravel'])     # jalur sisi timur
    gr.box(16.6, 21.4, -1.6, 0.0, Z_GRAVEL, -0.6, M['stone_v'], mtop=M['stone_h'])   # anak tangga pintu
    f = mb('lantai', C['common'])
    f.box(10, 35, 0, 30, -0.05, 0.0, M['porcelain'])
    f.box(0, 10, -6, 30, -0.05, 0.0, M['terracotta'])
    for key, mat in (('tidur', 'oak'), ('almari', 'oak'), ('air', 'tile_grey'), ('stor', 'tile_grey')):
        x0, x1, y0, y1 = G.ROOMS[key]
        f.box(x0, x1, y0, y1, 0.0, 0.02, M[mat])
    # laluan batu pijak ke selatan
    p = mb('laluan', C['common'], bevel=0.04)
    y = -6.3
    while y > -24:
        p.box(16.5, 21.5, y - 2.0, y, Z_LAWN - 0.1, Z_LAWN + 0.08, M['paver'])
        y -= 2.4
    # batas tanaman suku bulatan (barat daya) di atas pelantar
    cx, cy, r = G.PLANTER_SW
    pl = mb('batas_sw', C['common'], bevel=0.03)
    n, rw = 14, 0.35
    for i in range(n):
        a, bb = math.pi / 2 * i / n, math.pi / 2 * (i + 1) / n
        pts = [(cx + (r - rw) * math.cos(a), cy + (r - rw) * math.sin(a), 0.0),
               (cx + r * math.cos(a), cy + r * math.sin(a), 0.0),
               (cx + r * math.cos(bb), cy + r * math.sin(bb), 0.0),
               (cx + (r - rw) * math.cos(bb), cy + (r - rw) * math.sin(bb), 0.0)]
        pl.prism(pts, (0, 0, 1.1), M['brick'])
    soil = [(cx, cy, 0.0)] + [(cx + (r - rw) * math.cos(math.pi / 2 * i / 24),
                               cy + (r - rw) * math.sin(math.pi / 2 * i / 24), 0.0) for i in range(25)]
    pl.prism(soil, (0, 0, 0.9), M['brick'], mtop=M['soil'])


def trimmed_walls():
    """Pendekkan dinding yang bertindih di sudut (elak muka sesatah bertindih)."""
    done, out = [], []
    for x0, x1, y0, y1, k in G.WALLS:
        horiz = (x1 - x0) >= (y1 - y0)
        for p in done:
            ox0, ox1 = max(x0, p[0]), min(x1, p[1])
            oy0, oy1 = max(y0, p[2]), min(y1, p[3])
            if ox1 - ox0 > 1e-6 and oy1 - oy0 > 1e-6:
                if horiz:
                    if ox0 <= x0 + 1e-6:
                        x0 = ox1
                    elif ox1 >= x1 - 1e-6:
                        x1 = ox0
                else:
                    if oy0 <= y0 + 1e-6:
                        y0 = oy1
                    elif oy1 >= y1 - 1e-6:
                        y1 = oy0
        done.append((x0, x1, y0, y1))
        out.append((x0, x1, y0, y1, k))
    return out


def build_walls(C, M, cut):
    tag = 'cut' if cut else 'full'
    coll = C[tag]
    we = mb('dinding_luar_' + tag, coll)
    wi = mb('dinding_dalam_' + tag, coll)
    ws = mb('dinding_dapur_' + tag, coll)
    capm = M['cap'] if cut else None
    ops = ground_openings()
    for w in trimmed_walls():
        x0, x1, y0, y1, kind = w
        wo = openings_in(w, ops)
        if kind == 'ext':
            side = (y1 - y0) > (x1 - x0)
            if cut:
                build_wall(we, w, wo, 0.0, CUT, M['render'], cap_mat=capm)
            elif side:     # dinding barat/timur naik hingga bawah bumbung
                build_wall(we, w, wo, 0.0, 30.0, M['render'], ztop=lambda x, y: roof_top(x) - 0.45)
            else:
                build_wall(we, w, wo, 0.0, Z_WALL, M['render'])
        elif kind == 'int':
            build_wall(wi, w, wo, 0.0, CUT if cut else Z_CEIL, M['paint'], cap_mat=capm)
        else:
            if x1 <= 0.51:
                build_screen(ws, w, M, cut)
            elif cut:
                build_wall(ws, w, wo, 0.0, CUT, M['brick'], cap_mat=capm)
            else:
                build_wall(ws, w, wo, 0.0, 30.0, M['brick'], ztop=lambda x, y: ver_west(x, y) - 0.06)
    # jubin dinding bilik air (dalam)
    t = mb('jubin_bilik_air_' + tag, coll)
    th = 0.03
    bx0, bx1, by0, by1 = G.ROOMS['air']
    zt = min(7.5, CUT - CAP)
    for rect in ((bx0, bx0 + th, by0 + th, by1 - th), (bx1 - th, bx1, by0 + th, by1 - th),
                 (bx0, bx1, by1 - th, by1), (bx0, bx1, by0, by0 + th)):
        tops = []
        for o in ops:
            if o[0] <= rect[1] + 0.4 and o[1] >= rect[0] - 0.4 and o[2] <= rect[3] + 0.4 and o[3] >= rect[2] - 0.4:
                tops.append((max(o[0], rect[0]), min(o[1], rect[1]), max(o[2], rect[2]), min(o[3], rect[3]),
                             o[4], o[5], o[6]))
        build_wall(t, rect, [o for o in tops if o[1] > o[0] and o[3] > o[2]], 0.0, zt, M['tile_wall'])


def build_screen(b, w, M, cut):
    """Skrin bilah kayu menegak (dinding barat zon dapur)."""
    x0, x1, y0, y1 = w[:4]
    xc = (x0 + x1) / 2
    top = CUT if cut else 8.05
    tm = M['post']
    b.box(xc - 0.18, xc + 0.18, y0, y1, 0.0, 0.3, tm)
    b.box(xc - 0.15, xc + 0.15, y0, y1, 3.3, 3.5, tm)
    b.box(xc - 0.18, xc + 0.18, y0, y1, top - 0.25, top, tm)
    y = y0 + 0.15
    while y < y1 - 0.2:
        b.box(xc - 0.09, xc + 0.09, y, y + 0.22, 0.3, top - 0.25, M['slat'])
        y += 0.55


def build_openings(C, M):
    fr = mb('bingkai_tingkap', C['common'])
    gl = mb('kaca', C['common'])
    df = mb('bingkai_pintu', C['common'])
    dl = mb('daun_pintu', C['common'])
    for o in ground_openings():
        if o[4] == 'win':
            build_window(fr, gl, o, M)
        else:
            build_door(df, dl, gl, o, M, main=(o[0] == 16.75 and o[2] == 0.0))
    # lampu tanglung dinding di kiri kanan pintu utama
    ln = mb('tanglung', C['common'], bevel=0.01)
    for x in (15.85, 22.15):
        lantern(ln, x, 0.0, 5.6, M)


def lantern(b, x, y, z, M):
    bk = M['black']
    b.box(x - 0.12, x + 0.12, y - 0.06, y, z + 0.4, z + 1.3, bk)                 # plat dinding
    b.beam((x, y - 0.05, z + 1.15), (x, y - 0.55, z + 1.15), 0.06, 0.06, bk)     # lengan
    cy = y - 0.62
    b.box(x - 0.24, x + 0.24, cy - 0.24, cy + 0.24, z - 0.05, z + 0.05, bk)
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box(x + sx * 0.2 - 0.03, x + sx * 0.2 + 0.03, cy + sy * 0.2 - 0.03, cy + sy * 0.2 + 0.03,
                  z + 0.05, z + 0.85, bk)
    b.box(x - 0.17, x + 0.17, cy - 0.17, cy + 0.17, z + 0.05, z + 0.85, M['lamp_glass'])
    b.cyl(x, cy, 0.34, z + 0.85, z + 1.15, bk, seg=4, r1=0.25)
    b.cyl(x, cy, 0.06, z + 1.15, z + 1.3, bk, seg=8)


def gable_part(b, xa, xb, y0, y1, za, top, m):
    pts = [(xa, za), (xb, za), (xb, top(xb))]
    if xa < RIDGE_X < xb:
        pts.append((RIDGE_X, top(RIDGE_X)))
    pts.append((xa, top(xa)))
    b.prism([(px, y0, pz) for px, pz in pts], (0, y1 - y0, 0), m)


def build_roofs(C, M):
    """Pelana 45 darjah + veranda balut tiga sisi (semua dalam koleksi 'full')."""
    coll = C['full']
    # siling / lantai loteng
    sl = mb('siling', coll)
    sx0, sx1, sy0, sy1 = G.STAIR
    hole = (sx0 + 3.0, sx1, sy0 + 2.5, sy1 + 0.4)
    cx0, cx1, cy0, cy1 = 10.75, 34.25, 0.75, 29.25
    sl.box(cx0, cx1, cy0, hole[2], Z_CEIL, Z_WALL, M['soffit'], mtop=M['wood'])
    sl.box(cx0, cx1, hole[3], cy1, Z_CEIL, Z_WALL, M['soffit'], mtop=M['wood'])
    sl.box(cx0, hole[0], hole[2], hole[3], Z_CEIL, Z_WALL, M['soffit'], mtop=M['wood'])
    sl.box(hole[1], cx1, hole[2], hole[3], Z_CEIL, Z_WALL, M['soffit'], mtop=M['wood'])
    # dinding gable papan kayu (hadapan & belakang) dengan tingkap kecil
    gb = mb('gable', coll)
    gtop = (lambda x: roof_top(x) - 0.04)
    wx0, wx1 = RIDGE_X - 1.25, RIDGE_X + 1.25
    wz0, wz1 = 14.75, 17.25
    gf = mb('tingkap_gable', coll)
    gg = mb('kaca_gable', coll)
    for y0, y1 in ((0.0, 0.75), (29.25, 30.0)):
        gable_part(gb, 10.0, wx0, y0, y1, Z_WALL, gtop, M['boards'])
        gable_part(gb, wx1, 35.0, y0, y1, Z_WALL, gtop, M['boards'])
        gb.box(wx0, wx1, y0, y1, Z_WALL, wz0, M['boards'])
        gable_part(gb, wx0, wx1, y0, y1, wz1, gtop, M['boards'])
        build_window(gf, gg, (wx0, wx1, y0, y1, 'win', wz0, wz1), M, panes=2, transom=0.5)
    # bumbung pelana: kepingan beralur
    r = mb('bumbung_utama', coll)
    ex0, ex1 = 10.0 - MAIN_SIDE_OV, 35.0 + MAIN_SIDE_OV
    ry0, ry1 = -MAIN_RAKE_OV, 30.0 + MAIN_RAKE_OV
    ribbed(r, [(ex0, ry0), (RIDGE_X, ry0), (RIDGE_X, ry1), (ex0, ry1)], roof_top, (0, 1), M['metal'])
    ribbed(r, [(RIDGE_X, ry0), (ex1, ry0), (ex1, ry1), (RIDGE_X, ry1)], roof_top, (0, 1), M['metal'])
    zr = roof_top(RIDGE_X)
    # perabung (kepingan V terbalik)
    cap = [(-0.75, -0.75 + 0.14), (0.0, 0.22), (0.75, -0.75 + 0.14), (0.75, -0.75 + 0.1), (0.0, 0.17),
           (-0.75, -0.75 + 0.1)]
    r.prism([(RIDGE_X + dx, ry0 - 0.05, zr + dz) for dx, dz in cap], (0, ry1 - ry0 + 0.1, 0), M['metal'])
    # papan layang (barge) & fasia cucur, gelegar (purlin)
    tb = mb('kayu_bumbung', coll)
    bd = 0.95                                            # dalam papan layang
    for yb in (ry0 + 0.07, ry1 - 0.07):
        zo = 0.09 - bd / 2 * math.sqrt(2)
        tb.beam((ex0, yb, roof_top(ex0) + zo), (RIDGE_X, yb, zr + zo), 0.14, bd, M['post'])
        tb.beam((RIDGE_X, yb, zr + zo), (ex1, yb, roof_top(ex1) + zo), 0.13, bd, M['post'])
        # papan sofit di bawah unjuran cucur layang
        yy0, yy1 = (ry0 + 0.14, 0.0) if yb < 15 else (30.0, ry1 - 0.14)
        for xa, xb in ((ex0, RIDGE_X), (RIDGE_X, ex1)):
            pa = (xa, roof_top(xa) - bd * math.sqrt(2) + 0.12)
            pb = (xb, roof_top(xb) - bd * math.sqrt(2) + 0.12)
            tb.prism([(pa[0], yy0, pa[1]), (pb[0], yy0, pb[1]), (pb[0], yy0, pb[1] + 0.06),
                      (pa[0], yy0, pa[1] + 0.06)], (0, yy1 - yy0, 0), M['soffit'])
    for xf in (ex0 + 0.06, ex1 - 0.06):
        tb.box(xf - 0.06, xf + 0.06, ry0 + 0.12, ry1 - 0.12, roof_top(xf) - 0.5, roof_top(xf) - 0.04, M['post'])
    for k in range(5):
        for side in (-1, 1):
            xc = RIDGE_X + side * (1.2 + k * 2.5)
            xl = xc + side * 0.1
            tb.box(xc - 0.1, xc + 0.1, ry0 + 0.12, ry1 - 0.12, roof_top(xl) - 0.34, roof_top(xl) - 0.03, M['post'])
    tb.box(RIDGE_X - 0.12, RIDGE_X + 0.12, ry0 + 0.12, ry1 - 0.12, zr - 0.6, zr - 0.05, M['post'])
    build_veranda(C, M)


def build_veranda(C, M):
    coll = C['full']
    vr = mb('bumbung_veranda', coll)
    A, B_ = (-0.5, -6.5), (41.5, -6.5)
    ym = 30.5
    ribbed(vr, [A, B_, (35.0, 0.0), (10.0, 0.0)], ver_front, (1, 0), M['metal'])
    ribbed(vr, [A, (10.0, 0.0), (10.0, ym), (-0.5, ym)], ver_west, (0, 1), M['metal'])
    ribbed(vr, [(35.0, 0.0), B_, (41.5, ym), (35.0, ym)], ver_east, (0, 1), M['metal'])
    # bubung pinggul & kilat dinding
    hz = 0.13
    vr.beam((10.0, 0.0, VER_Z_WALL + hz), (A[0], A[1], ver_front(*A) + hz), 0.7, 0.05, M['metal'])
    vr.beam((35.0, 0.0, VER_Z_WALL + hz), (B_[0], B_[1], ver_front(*B_) + hz), 0.7, 0.05, M['metal'])
    vr.box(10.0, 35.0, -0.4, 0.0, VER_Z_WALL + 0.06, VER_Z_WALL + 0.16, M['metal'])
    vr.box(10.0 - 0.4, 10.0, 0.0, ym, VER_Z_WALL + 0.06, VER_Z_WALL + 0.16, M['metal'])
    vr.box(35.0, 35.4, 0.0, ym, VER_Z_WALL + 0.06, VER_Z_WALL + 0.16, M['metal'])
    # kasau (rafter) kayu di bawah kepingan
    tb = mb('kasau_veranda', coll)
    rw, rd = 0.17, 0.42
    off = 0.03 + rd / 2 + 0.02

    def rafter(p0, p1, w=rw, d=rd):
        z0 = ver_top(*p0) - off
        z1 = ver_top(*p1) - off
        tb.beam((p0[0], p0[1], z0), (p1[0], p1[1], z1), w, d, M['post'])

    x = 12.0
    while x < 34.0:
        rafter((x, -0.02), (x, -6.4))
        x += 2.5
    for x in (2.5, 5.0, 7.5):
        rafter((x, (6.5 / 10.5) * (x - 10.0) - 0.15), (x, -6.4))
    for x in (37.5, 40.0):
        rafter((x, -(x - 35.0) - 0.15), (x, -6.4))
    y = 1.5
    while y < 30.5:
        rafter((9.98, y), (-0.4, y))
        rafter((35.02, y), (41.4, y))
        y += 2.5
    for y in (-2.5, -5.0):
        rafter((10.0 + y * (10.5 / 6.5) - 0.15, y), (-0.4, y))
        rafter((35.0 - y + 0.15, y), (41.4, y))
    rafter((10.0, 0.0), (A[0] + 0.1, A[1] + 0.1), 0.22, 0.5)
    rafter((35.0, 0.0), (B_[0] - 0.1, B_[1] + 0.1), 0.22, 0.5)
    # rasuk tepi (tiada tiang tengah di hadapan)
    bd = 0.6
    zf = ver_front(0, POSTS[0][1]) - off - rd / 2 - 0.02
    zw = ver_west(POSTS[0][0], 0) - off - rd / 2 - 0.02
    tb.box(-0.35, 41.35, POSTS[0][1] - 0.18, POSTS[0][1] + 0.18, zf - bd, zf, M['post'])
    tb.box(POSTS[0][0] - 0.18, POSTS[0][0] + 0.18, -6.3, 30.35, zw - bd, zw, M['post'])
    tb.box(POSTS[1][0] - 0.18, POSTS[1][0] + 0.18, -6.3, 30.35, zf - bd, zf, M['post'])
    # tiang kayu bulat
    pc = mb('tiang', C['common'], bevel=0.0)
    for px, py in POSTS:
        z0 = 0.0 if px < 10 else Z_GRAVEL
        pc.cyl(px, py, 0.25, z0, zw - bd + 0.05, M['post'], seg=16)
        pc.cyl(px, py, 0.32, z0, z0 + 0.25, M['stone_v'], seg=16)


def build_stair(C, M, cut):
    tag = 'cut' if cut else 'full'
    coll = C[tag]
    st = mb('tangga_' + tag, coll, bevel=0.015)
    sx0, sx1, sy0, sy1 = G.STAIR
    sp = G.STAIR_SPLIT
    ly = G.STAIR_LANDING_Y
    nr = 8
    zl = H_ATTIC / 2
    rh = zl / nr
    td = (sy1 - ly) / (nr - 1)
    zmax = CUT if cut else 99

    def step(xa, xb, ya, yb, ztop):
        z = min(ztop, zmax)
        if ztop > zmax + 1e-6:
            st.box(xa, xb, ya, yb, 0.0, z - CAP, M['paint'])
            st.box(xa, xb, ya, yb, z - CAP, z, M['cap'])
        else:
            st.box(xa, xb, ya, yb, 0.0, z - 0.08, M['paint'])
            st.box(xa - 0.01, xb + 0.01, ya - 0.04, yb + 0.04, z - 0.08, z, M['wood'])

    for i in range(1, nr):                       # sayap barat: naik ke selatan
        step(sx0, sp - 0.125, sy1 - i * td, sy1 - (i - 1) * td, i * rh)
    st.box(sx0, sx1, sy0, ly, 0.0, zl - 0.08, M['paint'])      # pelantar
    st.box(sx0, sx1, sy0, ly, zl - 0.08, zl, M['wood'])
    for k in range(1, nr):                       # sayap timur: naik ke utara
        step(sp + 0.125, sx1, ly + (k - 1) * td, ly + k * td, zl + k * rh)
    wz = CUT if cut else Z_CEIL
    build_wall(st, (sp - 0.125, sp + 0.125, ly, sy1), [], 0.0, wz, M['paint'], cap_mat=M['cap'] if cut else None)
    gl = mb('balustrad_' + tag, coll)
    rail = 3.0

    def panel(pa, pb, axis, const):
        poly = [(pa[0], pa[1]), (pb[0], pb[1]), (pb[0], pb[1] + rail), (pa[0], pa[1] + rail)]
        poly = clip_z(poly, zmax)
        if len(poly) < 3:
            return
        th = 0.04
        if axis == 'y':
            gl.prism([(const - th / 2, s_, z_) for s_, z_ in poly], (th, 0, 0), M['glass'])
        else:
            gl.prism([(s_, const - th / 2, z_) for s_, z_ in poly], (0, th, 0), M['glass'])
        seg = clip_seg((pa[0], pa[1] + rail + 0.08), (pb[0], pb[1] + rail + 0.08), zmax)
        if seg:
            q0, q1 = seg
            if axis == 'y':
                gl.beam((const, q0[0], q0[1]), (const, q1[0], q1[1]), 0.18, 0.12, M['wood'])
            else:
                gl.beam((q0[0], const, q0[1]), (q1[0], const, q1[1]), 0.18, 0.12, M['wood'])

    panel((sy1, rh * 0.5), (ly, zl), 'y', sx0 + 0.05)
    panel((ly, zl), (sy1, H_ATTIC), 'y', sx1 - 0.05)
    panel((sx0, zl), (sx1, zl), 'x', sy0 + 0.05)
    panel((sy0, zl), (ly, zl), 'y', sx0 + 0.05)
    panel((sy0, zl), (ly, zl), 'y', sx1 - 0.05)


def clip_z(poly, zmax):
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        pin, qin = p[1] <= zmax, q[1] <= zmax
        if pin:
            out.append(p)
        if pin != qin:
            t = (zmax - p[1]) / (q[1] - p[1])
            out.append((p[0] + t * (q[0] - p[0]), zmax))
    return out


def clip_seg(p, q, zmax):
    if p[1] > zmax and q[1] > zmax:
        return None
    if p[1] <= zmax and q[1] <= zmax:
        return p, q
    t = (zmax - p[1]) / (q[1] - p[1])
    r = (p[0] + t * (q[0] - p[0]), zmax)
    return (p, r) if p[1] <= zmax else (r, q)


def build_divider(C, M, cut):
    tag = 'cut' if cut else 'full'
    d = mb('sekatan_kaca_' + tag, C[tag])
    x0, x1, y0, y1 = G.DIVIDER
    zt = CUT if cut else Z_CEIL
    c = (x0 + x1) / 2
    al = M['alu']
    d.box(x0 + 0.05, x1 - 0.05, y0, y1, 0.0, 0.35, al)
    d.box(x0 + 0.1, x1 - 0.1, y0, y1, zt - 0.2, zt, al)
    n = 3
    for i in range(n + 1):
        y = y0 + i * (y1 - y0) / n
        d.box(x0 + 0.1, x1 - 0.1, max(y0, y - 0.08), min(y1, y + 0.08), 0.35, zt - 0.2, al)
    d.box(c - 0.02, c + 0.02, y0, y1, 0.35, zt - 0.2, M['glass'])
    d.box(x0 + 0.1, x1 - 0.1, y0, y1, 3.4, 3.5, al)


# ===========================================================================
# Perabot
# ===========================================================================
def build_furniture(C, M):
    co = C['common']
    # --- ruang tamu: sofa U ---
    s = mb('sofa', co, bevel=0.12)
    base = [(23.65, 1.4), (33.6, 1.4), (33.6, 6.75), (32.0, 6.75), (32.0, 3.25), (25.5, 3.25), (25.5, 7.5),
            (23.65, 7.5)]
    s.prism([(x, y, 0.25) for x, y in base], (0, 0, 0.9), M['sofa'])
    seat = [(23.68, 1.43), (33.57, 1.43), (33.57, 6.72), (32.03, 6.72), (32.03, 3.22), (25.47, 3.22),
            (25.47, 7.47), (23.68, 7.47)]
    s.prism([(x, y, 1.15) for x, y in seat], (0, 0, 0.33), M['sofa'])
    s.box(23.0, 34.25, 0.75, 1.4, 0.25, 2.62, M['sofa'])
    s.box(23.0, 23.65, 1.4, 8.0, 0.25, 2.62, M['sofa'])
    s.box(33.6, 34.25, 1.4, 7.25, 0.25, 2.62, M['sofa'])
    s.box(23.65, 25.5, 7.5, 8.0, 0.25, 2.0, M['sofa'])
    s.box(32.0, 33.6, 6.75, 7.25, 0.25, 2.0, M['sofa'])
    legs = mb('kaki_sofa', co)
    for x, y in ((23.2, 0.95), (34.0, 0.95), (23.2, 7.8), (25.3, 7.8), (32.2, 7.05), (34.0, 7.05), (25.3, 3.1),
                 (32.2, 3.1)):
        legs.box(x - 0.08, x + 0.08, y - 0.08, y + 0.08, 0, 0.25, M['black'])
    cu = mb('kusyen', co, bevel=0.15)
    for x0, y0, mat in ((24.4, 1.45, 'cush1'), (27.5, 1.45, 'cush2'), (31.6, 1.45, 'cush3'), (33.0, 2.2, 'cush1'),
                        (23.7, 5.3, 'cush2')):
        if y0 < 2:
            cu.box(x0, x0 + 1.4, y0, y0 + 0.4, 1.5, 2.75, M[mat])
        elif x0 > 30:
            cu.box(x0, x0 + 0.4, y0, y0 + 1.4, 1.5, 2.75, M[mat])
        else:
            cu.box(x0, x0 + 0.4, y0, y0 + 1.4, 1.5, 2.75, M[mat])
    # permaidani & meja kopi
    rg = mb('permaidani', co)
    rg.box(25.6, 31.9, 3.3, 9.3, 0.0, 0.04, M['rug'])
    x0, x1, y0, y1 = G.COFFEE_TABLE
    ct = mb('meja_kopi', co, bevel=0.03)
    ct.box(x0, x1, y0, y1, 1.15, 1.32, M['wood'])
    ct.box(x0 + 0.3, x1 - 0.3, y0 + 0.3, y1 - 0.3, 0.04, 1.15, M['black'])
    ct.cyl(28.0, 5.4, 0.3, 1.32, 1.5, M['ceramic'], seg=20)
    # konsol TV + TV
    x0, x1, y0, y1 = G.TV_CONSOLE
    tv = mb('konsol_tv', co, bevel=0.03)
    tv.box(x0, x1, y0 + 0.2, y1, 0.4, 1.55, M['wood'])
    tv.box(x0 + 0.3, x1 - 0.3, y0 + 0.4, y1 - 0.1, 0.0, 0.4, M['black'])
    tvs = mb('tv', co, bevel=0.01)
    tvs.box(27.4, 31.6, 16.45, 16.62, 2.6, 5.0, M['black'])
    tvs.box(27.45, 31.55, 16.43, 16.45, 2.65, 4.95, M['screen'])
    # lampu lantai sudut ruang tamu
    lp = mb('lampu_lantai', co)
    lp.cyl(25.2, 9.0, 0.35, 0.0, 0.08, M['black'], seg=20)
    lp.cyl(25.2, 9.0, 0.04, 0.08, 4.8, M['black'], seg=8)
    lp.cyl(25.2, 9.0, 0.55, 4.6, 5.6, M['shade'], seg=24, r1=0.75)

    # --- ruang makan ---
    x0, x1, y0, y1 = G.DINING_TABLE
    dt = mb('meja_makan', co, bevel=0.03)
    dt.box(x0, x1, y0, y1, 2.3, 2.46, M['wood'])
    for lx, ly in ((x0 + 0.25, y0 + 0.25), (x1 - 0.4, y0 + 0.25), (x0 + 0.25, y1 - 0.4), (x1 - 0.4, y1 - 0.4)):
        dt.box(lx, lx + 0.15, ly, ly + 0.15, 0, 2.3, M['wood'])
    ch = mb('kerusi_makan', co, bevel=0.04)
    for cx, cy, ang in G.DINING_CHAIRS:
        chair(ch, cx, cy, ang, M)
    # lampu loket atas meja makan
    pend = mb('lampu_loket', C['full'])
    pend.cyl(14.0, 4.75, 0.02, 6.4, Z_CEIL, M['black'], seg=6)
    pend.cyl(14.0, 4.75, 0.8, 5.8, 6.4, M['shade'], seg=32, r1=0.3)
    # kabinet laluan
    x0, x1, y0, y1 = G.HALL_CABINET
    hc = mb('kabinet_laluan', co, bevel=0.02)
    hc.box(x0, x1 - 0.05, y0 + 0.1, y1 - 0.1, 0.3, 3.0, M['wood_light'])
    hc.box(x0 + 0.1, x1 - 0.2, y0 + 0.3, y1 - 0.3, 0.0, 0.3, M['black'])
    hc.cyl(15.3, 17.4, 0.25, 3.0, 3.9, M['ceramic'], seg=16, r1=0.6)

    # --- bilik tidur ---
    x0, x1, y0, y1 = G.BED
    bd = mb('katil', co, bevel=0.06)
    bd.box(x0, x1, y0, y1 - 0.35, 0.25, 0.95, M['wood'])
    bd.box(x0 - 0.3, x1 + 0.3, y1 - 0.35, y1, 0.0, 3.6, M['wood'])
    bd.box(x0 + 0.1, x1 - 0.1, y0 + 0.1, y1 - 0.45, 0.95, 1.64, M['linen'])
    bd.box(x0 - 0.04, x1 + 0.04, y0 - 0.04, y0 + 4.3, 0.85, 1.74, M['duvet'])
    pw = mb('bantal', co, bevel=0.18)
    pw.box(x0 + 0.4, x0 + 2.6, y1 - 1.9, y1 - 0.55, 1.64, 2.15, M['linen'])
    pw.box(x1 - 2.6, x1 - 0.4, y1 - 1.9, y1 - 0.55, 1.64, 2.15, M['linen'])
    pw.box(x0 + 1.6, x1 - 1.6, y1 - 2.3, y1 - 1.7, 1.64, 2.3, M['cush3'])
    rg.box(24.0, 31.5, 19.5, 24.5, 0.02, 0.06, M['rug2'])
    x0, x1, y0, y1 = G.WARDROBE
    wd = mb('almari_baju', co, bevel=0.02)
    wd.box(x0, x1, y0, y1, 0.0, 6.9, M['wood_light'])
    for yy in (y0 + (y1 - y0) / 3, y0 + 2 * (y1 - y0) / 3):
        wd.box(x1, x1 + 0.01, yy - 0.01, yy + 0.01, 0.2, 6.8, M['black'])
    for yy in (y0 + (y1 - y0) / 3 - 0.2, y0 + 2 * (y1 - y0) / 3 + 0.1):
        wd.box(x1, x1 + 0.06, yy, yy + 0.1, 3.0, 4.2, M['steel'])
    x0, x1, y0, y1 = G.NIGHTSTAND
    ns = mb('meja_sisi', co, bevel=0.03)
    ns.box(x0, x1, y0, y1, 0.2, 1.8, M['wood_light'])
    ns.cyl((x0 + x1) / 2, (y0 + y1) / 2, 0.25, 1.8, 2.9, M['brass'], seg=16, r1=0.3)
    ns.cyl((x0 + x1) / 2, (y0 + y1) / 2, 0.5, 2.6, 3.3, M['shade'], seg=24, r1=0.8)
    x0, x1, y0, y1 = G.DRESSER
    dr = mb('almari_solek', co, bevel=0.03)
    dr.box(x0 + 0.2, x1, y0, y1, 0.3, 2.6, M['wood_light'])
    dr.box(x1 - 0.06, x1 - 0.02, y0 + 0.4, y1 - 0.4, 3.2, 6.0, M['mirror'])
    x0, x1, y0, y1 = G.DESK
    dk = mb('meja_tulis', co, bevel=0.02)
    dk.box(x0, x1, y0 + 0.1, y1, 2.3, 2.46, M['wood_light'])
    dk.box(x0 + 0.05, x0 + 0.2, y0 + 0.1, y1, 0, 2.3, M['wood_light'])
    dk.box(x1 - 0.2, x1 - 0.05, y0 + 0.1, y1, 0, 2.3, M['wood_light'])
    dk.box(31.6, 32.9, 17.4, 18.3, 2.46, 2.5, M['black'])
    dk.cyl(33.7, 17.6, 0.2, 2.46, 3.6, M['black'], seg=12, r1=0.2)
    cx, cy, r = G.DESK_CHAIR
    dc = mb('kerusi_meja', co, bevel=0.05)
    dc.cyl(cx, cy, r * 0.8, 0.0, 0.1, M['black'], seg=20)
    dc.cyl(cx, cy, 0.08, 0.1, 1.4, M['steel'], seg=10)
    dc.cyl(cx, cy, r * 0.95, 1.4, 1.65, M['cush2'], seg=28)
    dc.box(cx - 0.7, cx + 0.7, cy + 0.45, cy + 0.65, 1.8, 3.3, M['cush2'])

    # --- bilik air ---
    x0, x1, y0, y1 = G.WC
    wc = mb('tandas', co, bevel=0.05)
    wc.box(x0, x0 + 0.65, y0 + 0.1, y1 - 0.1, 0.0, 2.7, M['ceramic'])
    wc.cyl(x0 + 1.3, (y0 + y1) / 2, 0.85, 0.0, 1.35, M['ceramic'], ry=0.6, seg=28, r1=1.0)
    wc.cyl(x0 + 1.3, (y0 + y1) / 2, 0.8, 1.35, 1.42, M['ceramic'], ry=0.58, seg=28)
    bx, by, br = G.BASIN
    bs = mb('sinki_bilik_air', co, bevel=0.03)
    bs.box(10.75, bx + 0.85, by - 0.95, by + 0.95, 1.0, 2.6, M['wood'])
    bs.cyl(bx, by, br * 0.85, 2.6, 3.0, M['ceramic'], seg=28, mtop=M['ceramic'])
    bs.cyl(bx, by, br * 0.65, 2.92, 3.01, M['steel'], seg=24)
    bs.box(10.78, 10.83, by - 0.9, by + 0.9, 3.6, 6.2, M['mirror'])
    bs.beam((10.8, by, 3.25), (bx - 0.3, by, 3.25), 0.07, 0.07, M['steel'])
    x0, x1, y0, y1 = G.SHOWER_WALL
    sw = mb('dinding_pancuran', co)
    sw.box(x0, x1, y0, y1, 0.0, 3.5, M['tile_wall'])
    sw.box(x0, x1, (y0 + y1) / 2 - 0.02, (y0 + y1) / 2 + 0.02, 3.5, 6.5, M['glass'])
    hx, hy = G.SHOWER_HEAD
    sw.cyl(hx, 29.15, 0.03, 4.0, 6.6, M['steel'], seg=8)
    sw.beam((hx, 29.2, 6.6), (hx, hy, 6.6), 0.06, 0.06, M['steel'])
    sw.cyl(hx, hy, 0.35, 6.45, 6.55, M['steel'], seg=20)
    fx, fy = G.FLOOR_TRAP
    sw.box(fx - 0.2, fx + 0.2, fy - 0.2, fy + 0.2, 0.02, 0.03, M['steel'])
    # --- stor: rak ---
    rk = mb('rak_stor', co)
    sx0, sx1, sy0, sy1 = G.ROOMS['stor']
    for z in (0.3, 2.0, 3.7, 5.4):
        rk.box(sx0 + 0.05, sx0 + 1.4, sy0 + 0.6, sy1 - 0.1, z, z + 0.08, M['wood_light'])
    for yy in (sy0 + 0.6, sy1 - 0.15):
        rk.box(sx0 + 0.05, sx0 + 1.4, yy, yy + 0.05, 0.0, 5.6, M['black'])
    for i in range(6):
        rk.box(sx0 + 0.2, sx0 + 1.2, sy0 + 0.9 + i * 0.6, sy0 + 1.3 + i * 0.6, 2.08, 2.6 + 0.1 * (i % 3),
               M['book'])
    # --- almari bilik (walk-in) ---
    ax0, ax1, ay0, ay1 = G.ROOMS['almari']
    wk = mb('rak_almari', co, bevel=0.02)
    wk.box(ax0 + 0.05, ax1 - 0.05, ay1 - 1.8, ay1, 0.0, 6.9, M['wood_light'])
    wk.box(ax0, ax0 + 1.6, ay0 + 0.6, ay1 - 1.8, 0.0, 3.0, M['wood_light'])

    build_kitchen(C, M)


def chair(b, cx, cy, ang, M):
    a = math.radians(ang)
    dx, dy = math.cos(a), math.sin(a)          # arah sandaran
    hw = 0.75
    b.box(cx - hw, cx + hw, cy - hw, cy + hw, 1.4, 1.55, M['wood'])
    for sx in (-1, 1):
        for sy in (-1, 1):
            px, py = cx + sx * (hw - 0.12), cy + sy * (hw - 0.12)
            b.box(px - 0.06, px + 0.06, py - 0.06, py + 0.06, 0.0, 1.4, M['wood'])
    bx, by = cx + dx * (hw - 0.08), cy + dy * (hw - 0.08)
    if abs(dx) > 0.5:
        b.box(bx - 0.08, bx + 0.08, cy - hw, cy + hw, 1.55, 2.9, M['wood'])
    else:
        b.box(cx - hw, cx + hw, by - 0.08, by + 0.08, 1.55, 2.9, M['wood'])
    b.box(cx - hw + 0.08, cx + hw - 0.08, cy - hw + 0.08, cy + hw - 0.08, 1.55, 1.68, M['cush2'])


def build_kitchen(C, M):
    co = C['common']
    k = mb('dapur', co, bevel=0.015)
    ctop = 2.95

    def counter(x0, x1, y0, y1, tx0, tx1, ty0, ty1):
        k.box(x0 + 0.1, x1 - 0.1, y0 + 0.1, y1 - 0.1, 0.0, 0.3, M['black'])
        k.box(x0, x1, y0, y1, 0.3, ctop - 0.12, M['cabinet'])
        k.box(tx0, tx1, ty0, ty1, ctop - 0.12, ctop, M['quartz'])

    x0, x1, y0, y1 = G.COUNTER_N
    counter(x0, x1, y0, y1 - 0.05, x0 - 0.05, x1 + 0.05, y0 - 0.03, y1 - 0.05)
    x0, x1, y0, y1 = G.COUNTER_S
    counter(x0, x1, y0 + 0.05, y1, x0 - 0.05, x1 + 0.05, y0, y1 - 0.02)
    x0, x1, y0, y1 = G.COUNTER_PEN
    counter(x0 + 0.05, x1, y0, y1, x1 - 3.45 + 0.07, x1 + 0.05, y0 - 0.03, y1 + 0.05)
    # meja bar kayu
    x0, x1, y0, y1 = G.BAR
    k.box(x0, x1 - 0.5, y0 + 0.3, y1 - 0.3, 0.0, ctop - 0.12, M['cabinet'])
    k.box(x0, x1, y0, y1, ctop - 0.12, ctop + 0.05, M['wood'])
    # pintu kabinet (garis)
    for y in range(15, 29, 2):
        k.box(2.5, 2.52, y, y + 0.02, 0.35, ctop - 0.2, M['black'])
    x0, x1, y0, y1 = G.KSINK
    k.box(x0, x1, y0, y1, ctop + 0.001, ctop + 0.012, M['steel'])
    k.box(x0 + 0.12, (x0 + x1) / 2 - 0.06, y0 + 0.12, y1 - 0.12, ctop + 0.012, ctop + 0.016, M['black'])
    k.box((x0 + x1) / 2 + 0.06, x1 - 0.12, y0 + 0.12, y1 - 0.12, ctop + 0.012, ctop + 0.016, M['black'])
    k.cyl(0.85, (y0 + y1) / 2, 0.06, ctop, ctop + 1.1, M['steel'], seg=10)
    k.beam((0.85, (y0 + y1) / 2, ctop + 1.1), (1.5, (y0 + y1) / 2, ctop + 1.1), 0.08, 0.08, M['steel'])
    x0, x1, y0, y1 = G.HOB
    k.box(x0, x1, y0, y1, ctop, ctop + 0.03, M['screen'])
    for yy in (y0 + 0.55, y1 - 0.55):
        k.cyl((x0 + x1) / 2, yy, 0.28, ctop + 0.03, ctop + 0.08, M['black'], seg=16)
    # meja bujur + bangku
    cx, cy, rx, ry = G.KTABLE
    t = mb('meja_dapur', co, bevel=0.02)
    t.cyl(cx, cy, rx, 2.33, 2.46, M['wood'], ry=ry, seg=40)
    t.cyl(cx, cy, 0.12, 0.05, 2.33, M['black'], seg=10)
    t.cyl(cx, cy, 0.6, 0.0, 0.05, M['black'], ry=0.8, seg=24)
    for sx, sy in G.KSTOOLS:
        t.cyl(sx, sy, 0.55, 1.45, 1.58, M['wood'], seg=24)
        t.cyl(sx, sy, 0.45, 0.0, 1.45, M['black'], seg=16, r1=0.6)
    # dobi
    ap = mb('mesin_basuh', co, bevel=0.05)
    for (x0, x1, y0, y1) in (G.WASHER, G.DRYER):
        ap.box(x0 + 0.05, x1 - 0.05, y0 + 0.05, y1 - 0.05, 0.0, 2.8, M['appliance'])
        cyy = (y0 + y1) / 2
        door = mb('pintu_mesin', co)
        door.prism([(x0 + 0.04, cyy + 0.65 * math.cos(2 * math.pi * i / 24),
                     1.35 + 0.65 * math.sin(2 * math.pi * i / 24)) for i in range(24)], (-0.03, 0, 0), M['screen'])
        ap.box(x0 + 0.04, x0 + 0.06, y0 + 0.2, y1 - 0.2, 2.35, 2.65, M['black'])
    x0, x1, y0, y1 = G.UTILITY_SINK
    us = mb('sinki_dobi', co, bevel=0.02)
    us.box(x0 + 0.05, x1 - 0.05, y0 + 0.05, y1 - 0.05, 0.0, 2.8, M['appliance'])
    us.box(x0 + 0.3, x1 - 0.3, y0 + 0.4, y1 - 0.4, 2.8, 2.82, M['steel'])
    us.cyl(x1 - 0.2, (y0 + y1) / 2, 0.05, 2.8, 3.9, M['steel'], seg=8)


# ===========================================================================
# Landskap
# ===========================================================================
def shrub(b, x, y, r, z0, rng, mat):
    for i in range(rng.randint(2, 3)):
        a = rng.uniform(0, 2 * math.pi)
        d = rng.uniform(0, 0.35) * r
        rr = r * rng.uniform(0.6, 0.8)
        c = (x + d * math.cos(a), y + d * math.sin(a), z0 + rr * 0.7)
        canopy(b, c, rr, rr * 0.8, mat, mat, random.Random(rng.randint(0, 9999)), int(18 + 10 * rr), rr * 0.28)


def palm(b, bl, x, y, h, rng, M):
    lean = Vector((rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6), 0))
    pts = [Vector((x, y, Z_LAWN)) + lean * (i / 8) ** 2 + Vector((0, 0, h * i / 8)) for i in range(9)]
    b.tube(pts, [0.45 - 0.2 * i / 8 for i in range(9)], M['palm_trunk'], seg=12)
    top = pts[-1]
    b.blob(top + Vector((0, 0, 0.2)), 0.5, M['palm_trunk'], sub=1, squash=1.4)
    nf = 11
    for i in range(nf):
        az = 2 * math.pi * i / nf + rng.uniform(-0.15, 0.15)
        el = rng.uniform(0.2, 0.9)
        L = rng.uniform(6.5, 8.5)
        d = Vector((math.cos(az), math.sin(az), 0))
        side = Vector((-d.y, d.x, 0))
        seg = 10
        rows = []
        for k in range(seg + 1):
            t = k / seg
            p = top + d * (L * t) + Vector((0, 0, L * (el * t - 1.1 * t * t)))
            w = 1.1 * math.sin(math.pi * min(1.0, t * 1.15)) * (1 - 0.3 * t) + 0.05
            rows.append((p + side * w - Vector((0, 0, 0.25 * w)), p + Vector((0, 0, 0.08)),
                         p - side * w - Vector((0, 0, 0.25 * w))))
        verts = [v for r in rows for v in r]
        faces = []
        for k in range(seg):
            a0 = 3 * k
            faces.append((a0, a0 + 1, a0 + 4, a0 + 3))
            faces.append((a0 + 1, a0 + 2, a0 + 5, a0 + 4))
        bl.add(verts, faces, M['leaf3'], True)


def canopy(bl, c, rx, rz, mat, core_mat, rng, n, cr, sub=1):
    """Kanopi: teras gelap + banyak gugusan daun kecil di permukaan."""
    bl.blob(c, rx * 0.8, core_mat, sub=2, squash=rz / rx, rough=0.25, seed=rng.randint(0, 999))
    for i in range(n):
        while True:
            v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
            if 0.2 < v.length <= 1:
                break
        v.normalize()
        if v.z < -0.5 and rng.random() < 0.6:
            continue
        t = rng.uniform(0.72, 1.0)
        p = Vector((c[0] + v.x * rx * t, c[1] + v.y * rx * t, c[2] + v.z * rz * t))
        bl.blob(p, cr * rng.uniform(0.7, 1.3), mat, sub=sub, squash=0.8, rough=0.45, seed=rng.randint(0, 999),
                smooth=True)


def tree(b, bl, x, y, h, r, rng, mat_leaf, M, z0=Z_LAWN, sub=2, far=False):
    hc = h - r * 0.75
    pts = [Vector((x + rng.uniform(-0.25, 0.25) * i / 4 * r * 0.1, y + rng.uniform(-0.25, 0.25) * i / 4 * r * 0.1,
                   z0 + hc * 0.8 * i / 4)) for i in range(5)]
    b.tube(pts, [max(0.15, r * 0.075) * (1 - 0.3 * i / 4) for i in range(5)], M['trunk'], seg=10)
    top = pts[-1]
    if not far:
        for k in range(4):
            az = rng.uniform(0, 2 * math.pi)
            e = top + Vector((math.cos(az) * r * 0.5, math.sin(az) * r * 0.5, r * 0.45))
            b.tube([top - Vector((0, 0, hc * 0.12)), e], [max(0.1, r * 0.045), max(0.05, r * 0.02)], M['trunk'],
                   seg=8)
    nlobes = 1 if far else rng.randint(3, 5)
    for k in range(nlobes):
        if nlobes == 1:
            c, rr = Vector((x, y, z0 + hc)), r
        else:
            az = 2 * math.pi * k / nlobes + rng.uniform(-0.4, 0.4)
            c = Vector((x + math.cos(az) * r * 0.42, y + math.sin(az) * r * 0.42, z0 + hc + rng.uniform(-0.1, 0.25) * r))
            rr = r * rng.uniform(0.55, 0.7)
        n = 45 if far else int(70 * (rr / 5.0) ** 1.6) + 30
        canopy(bl, c, rr, rr * 0.72, mat_leaf, M['leaf2'], rng, n, rr * (0.3 if far else 0.17), sub=1 if far else 2)


def pot_plant(b, bl, x, y, r, z0, kind, rng, M):
    if kind in ('pot', 'yellow'):
        if kind == 'pot':
            b.cyl(x, y, r * 0.75, z0, z0 + r * 2.4, M['pot_dark'], seg=24, r1=1.33)
            b.cyl(x, y, r * 0.92, z0 + r * 2.2, z0 + r * 2.3, M['soil'], seg=24)
            zt, nl, lmin, lmax = z0 + r * 2.3, 9, 2.2, 3.4
        else:     # pasu seramik kuning berkilat (bujur)
            prof = [(0.55, 0.0), (0.85, 0.25), (1.0, 0.7), (0.95, 1.2), (0.78, 1.55), (0.8, 1.7)]
            b.tube([(x, y, z0 + pz * r * 1.4) for _, pz in prof], [pr * r for pr, _ in prof], M['yellow'], seg=28)
            zt = z0 + 1.7 * r * 1.4 - 0.1
            b.cyl(x, y, 0.78 * r, zt - 0.02, zt, M['soil'], seg=24)
            nl, lmin, lmax = 0, 0, 0
            # pokok tinggi (dracaena): batang + jambak daun
            for k in range(3):
                az = 2 * math.pi * k / 3 + 0.4
                base = Vector((x + 0.15 * math.cos(az), y + 0.15 * math.sin(az), zt))
                tip = base + Vector((0.6 * math.cos(az), 0.6 * math.sin(az), 3.2 + 0.9 * k))
                b.tube([base, tip], [0.07, 0.05], M['trunk'], seg=6)
                for j in range(12):
                    a2 = rng.uniform(0, 2 * math.pi)
                    el = rng.uniform(-0.2, 0.9)
                    L = rng.uniform(1.2, 1.9)
                    d = Vector((math.cos(a2) * math.cos(el), math.sin(a2) * math.cos(el), math.sin(el)))
                    side = Vector((-math.sin(a2), math.cos(a2), 0)) * 0.13
                    p0 = tip + Vector((0, 0, rng.uniform(-0.6, 0.1)))
                    mid = p0 + d * L * 0.5
                    end = p0 + d * L + Vector((0, 0, -0.25 * L * (1 - el)))
                    bl.add([p0 - side * 0.4, p0 + side * 0.4, mid + side, end, mid - side], [(0, 1, 2, 3, 4)],
                           M['leaf'], True)
        for i in range(nl):
            az = 2 * math.pi * i / nl + rng.uniform(-0.2, 0.2)
            rr = rng.uniform(0.0, 0.45) * r
            base = Vector((x + rr * math.cos(az), y + rr * math.sin(az), zt))
            L = rng.uniform(lmin, lmax)
            tip = base + Vector((math.cos(az) * 0.45, math.sin(az) * 0.45, L))
            side = Vector((-math.sin(az + 1.2), math.cos(az + 1.2), 0)) * 0.22
            mid = base.lerp(tip, 0.45)
            bl.add([base - side, base + side, mid + side * 1.1, tip, mid - side * 1.1], [(0, 1, 2, 3, 4)],
                   M['leaf'], True)
    else:      # bigpot: pasu besar + pokok kecil
        b.cyl(x, y, r * 0.8, z0, z0 + 2.0, M['pot_terra'], seg=32, r1=1.25)
        b.cyl(x, y, r * 0.95, z0 + 1.9, z0 + 1.95, M['soil'], seg=32)
        tree(b, bl, x, y, 6.5, 2.0, rng, M['leaf'], M, z0=z0 + 1.9)


def build_landscape(C, M):
    rng = random.Random(7)
    co = C['common']
    b = mb('batang_pasu', co)
    bl = mb('daun', co)
    for x, y, r, kind in G.PLANTS:
        if kind == 'shrub':
            z0 = 0.9 if (x < 4.5 and y < 4.5) else Z_LAWN
            shrub(bl, x, y, r, z0, rng, M['leaf2'])
        elif kind == 'palm':
            palm(b, bl, x, y, 15.0, rng, M)
        elif kind == 'pot':
            pot_plant(b, bl, x, y, r, 0.0 if y > 0 else Z_GRAVEL, kind, rng, M)
        elif kind == 'bigpot':
            pot_plant(b, bl, x, y, r, 0.0, kind, rng, M)
    # pasu kuning berkilat di sudut hadapan-kiri rumah (model pengguna)
    pot_plant(b, bl, 11.0, -1.0, 0.75, Z_GRAVEL, 'yellow', rng, M)
    # pokok sekitar tapak (sisi & belakang sahaja; hadapan dibiarkan lapang)
    ctx = mb('batang_pokok', C['ctx'])
    cl = mb('daun_pokok', C['ctx'])
    for x, y, h, r, m in ((-24, 20, 24, 10, 'leaf'), (-20, 46, 28, 11, 'leaf2'), (10, 56, 32, 12, 'leaf'),
                          (38, 60, 26, 11, 'leaf2'), (62, 34, 24, 10, 'leaf'), (66, 10, 18, 7, 'leaf3'),
                          (-30, -2, 16, 6.5, 'leaf3')):
        tree(ctx, cl, x, y, h, r, rng, M[m], M)
    for x in range(-44, 84, 4):
        shrub(cl, x + rng.uniform(-1, 1), 72 + rng.uniform(-1, 1), 2.8, Z_LAWN, rng, M['leaf2'])
    for i in range(110):
        a = rng.uniform(-0.3 * math.pi, 1.3 * math.pi)
        d = rng.uniform(150, 240)
        x, y = 20 + d * math.cos(a), 12 + d * math.sin(a)
        tree(ctx, cl, x, y, rng.uniform(28, 46), rng.uniform(11, 17), rng,
             M[rng.choice(['leaf', 'leaf2', 'leaf3'])], M, far=True)
    for y in (6, 16, 26):
        shrub(cl, 43.5, y, 1.3, Z_LAWN, rng, M['leaf2'])
    for y in (34, 37):
        shrub(cl, 3.0, y, 1.3, Z_LAWN, rng, M['leaf2'])


# ===========================================================================
# Pencahayaan, kamera, render
# ===========================================================================
SUN_AZ = 222.0          # azimut kompas matahari (dari utara ikut jam) -> barat daya / hadapan-kiri


def setup_world(sc, sun_el, strength=1.0, sun_energy=4.0, clouds=True):
    w = bpy.data.worlds.new('langit')
    sc.world = w
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    N, L = nt.nodes, nt.links

    def mth(op, a, b=0.0):
        m = N.new('ShaderNodeMath')
        m.operation = op
        for i, v in enumerate((a, b)):
            if isinstance(v, bpy.types.NodeSocket):
                L.new(v, m.inputs[i])
            else:
                m.inputs[i].default_value = v
        return m.outputs[0]

    sky = N.new('ShaderNodeTexSky')
    sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_disc = False
    sky.sun_elevation = math.radians(sun_el)
    sky.sun_rotation = math.radians(SUN_AZ)
    sky.altitude = 50.0
    sky.air_density = 1.0
    sky.aerosol_density = 0.35
    sky.air_density = 1.15
    col = sky.outputs[0]
    if clouds:
        # awan prosedural: unjuran arah pandang ke satah awan
        tc = N.new('ShaderNodeTexCoord')
        sp = N.new('ShaderNodeSeparateXYZ')
        L.new(tc.outputs['Generated'], sp.inputs[0])
        zc = mth('MAXIMUM', sp.outputs[2], 0.03)
        cx = mth('DIVIDE', sp.outputs[0], zc)
        cy = mth('DIVIDE', sp.outputs[1], zc)
        cb = N.new('ShaderNodeCombineXYZ')
        L.new(cx, cb.inputs[0])
        L.new(mth('MULTIPLY', cy, 1.6), cb.inputs[1])
        nz = N.new('ShaderNodeTexNoise')
        L.new(cb.outputs[0], nz.inputs['Vector'])
        nz.inputs['Scale'].default_value = 1.1
        nz.inputs['Detail'].default_value = 8.0
        nz.inputs['Roughness'].default_value = 0.6
        mr = N.new('ShaderNodeMapRange')
        mr.interpolation_type = 'SMOOTHSTEP'
        L.new(nz.outputs['Fac'], mr.inputs['Value'])
        mr.inputs['From Min'].default_value = 0.53
        mr.inputs['From Max'].default_value = 0.72
        hz = N.new('ShaderNodeMapRange')
        hz.interpolation_type = 'SMOOTHSTEP'
        L.new(sp.outputs[2], hz.inputs['Value'])
        hz.inputs['From Min'].default_value = 0.03
        hz.inputs['From Max'].default_value = 0.3
        mask = mth('MULTIPLY', mr.outputs['Result'], hz.outputs['Result'])
        mask = mth('MULTIPLY', mask, 0.92)
        bw = N.new('ShaderNodeRGBToBW')
        L.new(col, bw.inputs[0])
        shade = mth('ADD', 0.75, mth('MULTIPLY', nz.outputs['Fac'], 0.9))
        cval = mth('MULTIPLY', mth('MULTIPLY', bw.outputs[0], 2.3), shade)
        cc = N.new('ShaderNodeCombineColor')
        L.new(cval, cc.inputs[0])
        L.new(cval, cc.inputs[1])
        L.new(mth('MULTIPLY', cval, 1.03), cc.inputs[2])
        mx = N.new('ShaderNodeMix')
        mx.data_type = 'RGBA'
        L.new(mask, _in(mx, 'Factor_Float'))
        L.new(col, _in(mx, 'A_Color'))
        L.new(cc.outputs[0], _in(mx, 'B_Color'))
        col = _out(mx, 'Result_Color')
    bg = N.new('ShaderNodeBackground')
    L.new(col, bg.inputs[0])
    # langit kelihatan sedikit lebih gelap daripada cahaya yang diberi (kesan penapis polar)
    lp = N.new('ShaderNodeLightPath')
    k = mth('ADD', strength, mth('MULTIPLY', lp.outputs['Is Camera Ray'], -0.4 * strength))
    L.new(k, bg.inputs['Strength'])
    out = N.new('ShaderNodeOutputWorld')
    L.new(bg.outputs[0], out.inputs[0])
    ld = bpy.data.lights.new('matahari', 'SUN')
    ld.energy = sun_energy
    ld.angle = math.radians(1.5)
    ld.color = (1.0, 0.95, 0.88)
    ob = bpy.data.objects.new('matahari', ld)
    sc.collection.objects.link(ob)
    az, el = math.radians(SUN_AZ), math.radians(sun_el)
    d = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    ob.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return ob


def add_area(coll, name, x, y, z, size, power, color=(1.0, 0.85, 0.68)):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.shape = 'SQUARE'
    ld.size = size * F
    ld.energy = power
    ld.color = color
    ob = bpy.data.objects.new(name, ld)
    ob.location = (x * F, y * F, z * F)
    ob.visible_camera = False
    coll.objects.link(ob)
    return ob


def build_lights(C):
    for nm, x, y in (('l_tamu', 28.5, 9.0), ('l_makan', 16.5, 8.0), ('l_tidur', 27.0, 23.0),
                     ('l_laluan', 18.0, 21.0), ('l_air', 13.0, 25.0), ('l_dapur', 4.5, 19.0)):
        z = 7.9 if nm == 'l_dapur' else Z_CEIL - 0.1
        add_area(C['full'], nm, x, y, z, 2.0, 45.0)


def camera(sc, name, loc, target=None, lens=30.0, shift=(0.0, 0.0), level=False):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = 36.0
    cd.shift_x, cd.shift_y = shift
    cd.clip_start = 0.1
    cd.clip_end = 2000.0
    ob = bpy.data.objects.new(name, cd)
    sc.collection.objects.link(ob)
    loc = Vector(loc) * F
    ob.location = loc
    tgt = Vector(target) * F
    d = tgt - loc
    if level:
        ob.rotation_euler = (math.radians(90), 0.0, math.atan2(-d.x, d.y))
    else:
        ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.camera = ob
    return ob


VIEWS = {
    'luar': dict(file='Render_3D_Luar.jpg', sun_el=46.0),
    'pelan': dict(file='Render_3D_Pelan.jpg', sun_el=64.0),
    'udara': dict(file='Render_3D_Udara.jpg', sun_el=46.0),
}
SKY_STRENGTH, SUN_ENERGY = 0.45, 4.2


def build_scene():
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras,
                 bpy.data.worlds, bpy.data.images):
        for blk in list(coll):
            coll.remove(blk)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    BUILDERS.clear()
    sc = bpy.context.scene
    C = {}
    for k in ('common', 'full', 'cut', 'ctx'):
        c = bpy.data.collections.new(k)
        sc.collection.children.link(c)
        C[k] = c
    M = make_materials()
    build_ground(C, M)
    build_walls(C, M, cut=False)
    build_walls(C, M, cut=True)
    build_openings(C, M)
    build_roofs(C, M)
    build_stair(C, M, cut=False)
    build_stair(C, M, cut=True)
    build_divider(C, M, cut=False)
    build_divider(C, M, cut=True)
    build_furniture(C, M)
    build_landscape(C, M)
    build_lights(C)
    for b in BUILDERS:
        b.build()
    return sc, C


def setup_render(sc, width, samples, quick):
    sc.render.engine = 'CYCLES'
    cy = sc.cycles
    cy.device = 'CPU'
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.03 if quick else 0.015
    cy.use_denoising = True
    cy.denoiser = 'OPENIMAGEDENOISE'
    cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    cy.denoising_prefilter = 'ACCURATE'
    cy.max_bounces = 8
    cy.diffuse_bounces = 3
    cy.glossy_bounces = 3
    cy.transmission_bounces = 8
    cy.transparent_max_bounces = 16
    cy.sample_clamp_indirect = 6.0
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.use_light_tree = True
    sc.render.resolution_x = width
    sc.render.resolution_y = int(round(width * 2 / 3))
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 92


def apply_view(sc, C, view):
    v = VIEWS[view]
    pelan = view == 'pelan'
    C['full'].hide_render = pelan
    C['cut'].hide_render = not pelan
    for ob in list(sc.collection.objects):
        if ob.type in ('CAMERA', 'LIGHT'):
            bpy.data.objects.remove(ob)
    if pelan:
        setup_world(sc, v['sun_el'], strength=SKY_STRENGTH, sun_energy=SUN_ENERGY)
        sc.view_settings.exposure = 0.0
        tgt = (20.5, 11.0, 0.0)
        el, dist = math.radians(58), 72.0
        loc = (tgt[0], tgt[1] - dist * math.cos(el), tgt[2] + dist * math.sin(el))
        camera(sc, 'kamera', loc, tgt, lens=40.0)
    elif view == 'luar':
        setup_world(sc, v['sun_el'], strength=SKY_STRENGTH, sun_energy=SUN_ENERGY)
        sc.view_settings.exposure = 0.0
        eye = 9.0              # paras mata dinaikkan (~3.2 m dari rumput) seperti imej pengguna
        camera(sc, 'kamera', (-4.0, -40.0, eye), (22.5, 0.0, eye), lens=24.0, shift=(0.0, 0.02), level=True)
    else:
        setup_world(sc, v['sun_el'], strength=SKY_STRENGTH, sun_energy=SUN_ENERGY)
        sc.view_settings.exposure = 0.0
        camera(sc, 'kamera', (-30.0, -50.0, 50.0), (20.0, 12.0, 4.0), lens=34.0)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--view', default='all', choices=['luar', 'pelan', 'udara', 'all'])
    ap.add_argument('--quick', action='store_true', help='pratonton cepat (resolusi & sampel rendah)')
    ap.add_argument('--samples', type=int, default=None)
    ap.add_argument('--width', type=int, default=None)
    ap.add_argument('--out', default=os.path.dirname(HERE))
    ap.add_argument('--suffix', default='')
    ap.add_argument('--blend', default=None, help='simpan fail .blend (nyahpepijat)')
    a = ap.parse_args(argv)
    addon_utils.enable('cycles', default_set=True)
    t0 = time.time()
    sc, C = build_scene()
    print('scene built in %.1fs, objects=%d' % (time.time() - t0, len(bpy.data.objects)))
    width = a.width or (900 if a.quick else 2000)
    samples = a.samples or (24 if a.quick else 64)
    setup_render(sc, width, samples, a.quick)
    views = ['luar', 'pelan', 'udara'] if a.view == 'all' else [a.view]
    for v in views:
        apply_view(sc, C, v)
        name = VIEWS[v]['file']
        if a.suffix:
            name = name.replace('.jpg', a.suffix + '.jpg')
        sc.render.filepath = os.path.join(a.out, name)
        if a.blend:
            bpy.ops.wm.save_as_mainfile(filepath=a.blend)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print('RENDER %s %.1fs -> %s' % (v, time.time() - t, sc.render.filepath))


if __name__ == '__main__':
    main()
