#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jana PELAN LANTAI BAWAH gaya persembahan arkitek (berwarna) - A3 landskap, skala 1:50.

    python3 jana_pelan.py            -> ../Pelan_Lantai_Bawah_A3.svg + .html
Kemudian render ke PDF/JPG dengan Chromium (lihat render_pelan.sh).

Koordinat lukisan dalam KAKI (lihat geometri.py); ditukar ke mm kertas di sini.
"""
import math
import os
import random

from geometri import *  # noqa: F401,F403

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, '..'))

S = 304.8 / 50.0               # mm kertas bagi 1 kaki pada 1:50
SHEET_W, SHEET_H = 420.0, 297.0
FRAME = 7.0                    # jidar bingkai
TB_W = 100.0                   # lebar lajur blok tajuk
DRAW_X0, DRAW_X1 = FRAME, SHEET_W - FRAME - TB_W
DRAW_Y0, DRAW_Y1 = FRAME, SHEET_H - FRAME

# kedudukan pelan: pusatkan julat X -4..39 kaki, Y -10..34.8 kaki dalam ruang lukisan
OX = (DRAW_X0 + DRAW_X1) / 2 - 17.5 * S
OY = (DRAW_Y0 + DRAW_Y1) / 2 + 12.4 * S


def mx(x):
    return OX + x * S


def my(y):
    return OY - y * S


def n(v):
    s = f"{v:.3f}".rstrip('0').rstrip('.')
    return s if s not in ('-0', '') else '0'


def attrs(d):
    out = []
    for k, v in d.items():
        if v is None:
            continue
        k = k.rstrip('_').replace('_', '-')
        out.append(f'{k}="{v}"')
    return ' '.join(out)


# ---------------------------------------------------------------- primitif (kaki)
def rect(x0, x1, y0, y1, rx=0, **a):
    xa, xb = sorted((x0, x1))
    ya, yb = sorted((y0, y1))
    r = f' rx="{n(rx * S)}"' if rx else ''
    return (f'<rect x="{n(mx(xa))}" y="{n(my(yb))}" width="{n((xb - xa) * S)}" '
            f'height="{n((yb - ya) * S)}"{r} {attrs(a)}/>')


def circle(cx, cy, r, **a):
    return f'<circle cx="{n(mx(cx))}" cy="{n(my(cy))}" r="{n(r * S)}" {attrs(a)}/>'


def ellipse(cx, cy, rx, ry, **a):
    return (f'<ellipse cx="{n(mx(cx))}" cy="{n(my(cy))}" rx="{n(rx * S)}" '
            f'ry="{n(ry * S)}" {attrs(a)}/>')


def line(x0, y0, x1, y1, **a):
    return (f'<line x1="{n(mx(x0))}" y1="{n(my(y0))}" x2="{n(mx(x1))}" '
            f'y2="{n(my(y1))}" {attrs(a)}/>')


def poly(pts, closed=True, **a):
    p = ' '.join(f'{n(mx(x))},{n(my(y))}' for x, y in pts)
    tag = 'polygon' if closed else 'polyline'
    return f'<{tag} points="{p}" {attrs(a)}/>'


def path(d, **a):
    return f'<path d="{d}" {attrs(a)}/>'


def P(x, y):
    return f'{n(mx(x))},{n(my(y))}'


def text(x, y, s, size=2.0, anchor='middle', weight=400, fill='#222', ls=0,
         halo=True, rot=0, style='', family='Inter'):
    tr = f' transform="rotate({rot} {n(mx(x))} {n(my(y))})"' if rot else ''
    h = (' stroke="#ffffff" stroke-width="0.7" stroke-opacity="0.85" '
         'paint-order="stroke" stroke-linejoin="round"') if halo else ''
    st = f' font-style="{style}"' if style else ''
    return (f'<text x="{n(mx(x))}" y="{n(my(y))}" font-family="{family}" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}"{st}{h}{tr}>{s}</text>')


def ft_in(v):
    """12.125 -> 12'-1½\""""
    inches = round(v * 12 * 2) / 2
    ft = int(inches // 12)
    rem = inches - ft * 12
    whole = int(rem)
    half = '½' if rem - whole else ''
    return f"{ft}'-{whole}{half}\""


# ---------------------------------------------------------------- warna / gaya
INK = '#1d1d1b'
WALL = '#262624'
LINE = '#4a4844'
THIN = 0.12
MED = 0.18


# ============================================================== DEFS
def defs():
    d = []
    # --- jubin porselin 600x600 (ruang tamu / makan / laluan)
    T = 2 * S
    tones = ['#efe9df', '#ece5da', '#f1ece3', '#eae3d7', '#eee8de', '#e9e2d6',
             '#f0eae1', '#ebe4d9', '#ede7dc']
    t = [f'<pattern id="pTile" patternUnits="userSpaceOnUse" x="{n(mx(10.75))}" '
         f'y="{n(my(0.75))}" width="{n(3 * T)}" height="{n(3 * T)}">']
    for i in range(3):
        for j in range(3):
            t.append(f'<rect x="{n(i * T)}" y="{n(j * T)}" width="{n(T)}" height="{n(T)}" '
                     f'fill="{tones[i * 3 + j]}" stroke="#d3cabb" stroke-width="0.14"/>')
    t.append('</pattern>')
    d += t

    # --- jubin 300x300 kelabu (bilik air / stor)
    T1 = S
    tones = ['#dde2e3', '#d9dfe0', '#e0e5e6', '#d6dcdd', '#dce1e2', '#e2e6e7',
             '#d8dedf', '#dee3e4', '#dadfe0']
    t = [f'<pattern id="pBath" patternUnits="userSpaceOnUse" x="{n(mx(10.75))}" '
         f'y="{n(my(21.25))}" width="{n(3 * T1)}" height="{n(3 * T1)}">']
    for i in range(3):
        for j in range(3):
            t.append(f'<rect x="{n(i * T1)}" y="{n(j * T1)}" width="{n(T1)}" height="{n(T1)}" '
                     f'fill="{tones[i * 3 + j]}" stroke="#b9c2c5" stroke-width="0.12"/>')
    t.append('</pattern>')
    d += t

    # --- mozek pancuran
    m = S / 3
    d.append(f'<pattern id="pMosaic" patternUnits="userSpaceOnUse" x="{n(mx(10.75))}" '
             f'y="{n(my(29.25))}" width="{n(2 * m)}" height="{n(2 * m)}">'
             f'<rect width="{n(2 * m)}" height="{n(2 * m)}" fill="#a9bcc4"/>'
             f'<rect x="0.06" y="0.06" width="{n(m - 0.12)}" height="{n(m - 0.12)}" fill="#c3d2d8"/>'
             f'<rect x="{n(m + 0.06)}" y="0.06" width="{n(m - 0.12)}" height="{n(m - 0.12)}" fill="#b8c9d0"/>'
             f'<rect x="0.06" y="{n(m + 0.06)}" width="{n(m - 0.12)}" height="{n(m - 0.12)}" fill="#bccdd3"/>'
             f'<rect x="{n(m + 0.06)}" y="{n(m + 0.06)}" width="{n(m - 0.12)}" height="{n(m - 0.12)}" fill="#c7d5da"/>'
             f'</pattern>')

    # --- jubin dapur 300x300 (hijau-kelabu, susun serong)
    tones = ['#dfe0d6', '#dbddd2', '#e2e3d9', '#d8dacf']
    t = [f'<pattern id="pKitchen" patternUnits="userSpaceOnUse" x="{n(mx(0.5))}" '
         f'y="{n(my(8))}" width="{n(2 * T1)}" height="{n(2 * T1)}" '
         f'patternTransform="rotate(45 {n(mx(0.5))} {n(my(8))})">']
    for i in range(2):
        for j in range(2):
            t.append(f'<rect x="{n(i * T1)}" y="{n(j * T1)}" width="{n(T1)}" height="{n(T1)}" '
                     f'fill="{tones[i * 2 + j]}" stroke="#bfc1b3" stroke-width="0.12"/>')
    t.append('</pattern>')
    d += t

    # --- turapan batu 1'x2' ikatan larian (anjung & laman sisi)
    W, H = 2 * S, S
    tones = ['#d9d1c3', '#d4cbbc', '#ddd5c8', '#d1c8b8', '#d7cfc1', '#dbd3c6']
    t = [f'<pattern id="pPave" patternUnits="userSpaceOnUse" x="{n(mx(0))}" y="{n(my(0))}" '
         f'width="{n(3 * W)}" height="{n(2 * H)}">']
    k = 0
    for row in range(2):
        off = 0 if row == 0 else W / 2
        for i in range(-1, 4):
            t.append(f'<rect x="{n(off + i * W)}" y="{n(row * H)}" width="{n(W)}" height="{n(H)}" '
                     f'fill="{tones[k % len(tones)]}" stroke="#bcb2a1" stroke-width="0.14"/>')
            k += 1
    t.append('</pattern>')
    d += t

    # --- lantai kayu (papan oak, membujur utara-selatan)
    pw = 0.5 * S
    L = 4.0 * S
    offs = [0.0, 0.55, 0.25, 0.8, 0.4, 0.1, 0.68, 0.33]
    cols = ['#c9a073', '#c39867', '#cfa77b', '#bf9161', '#c79d6f', '#cca276', '#c2966a', '#c69b6c']
    cols2 = ['#c59b6d', '#ca9f70', '#c0935f', '#cda57a', '#c49869', '#bf9566', '#c8a074', '#c39a6b']
    t = [f'<pattern id="pWood" patternUnits="userSpaceOnUse" x="{n(mx(20.5))}" y="{n(my(29.25))}" '
         f'width="{n(8 * pw)}" height="{n(L)}">']
    for i in range(8):
        o = offs[i] * L
        x = i * pw
        t.append(f'<rect x="{n(x)}" y="{n(o - L)}" width="{n(pw)}" height="{n(L)}" fill="{cols[i]}" '
                 f'stroke="#9c7650" stroke-width="0.07"/>')
        t.append(f'<rect x="{n(x)}" y="{n(o)}" width="{n(pw)}" height="{n(L)}" fill="{cols2[i]}" '
                 f'stroke="#9c7650" stroke-width="0.07"/>')
    t.append('</pattern>')
    d += t

    # --- anak tangga kayu
    d.append('<linearGradient id="gStair" x1="0" y1="0" x2="0" y2="1">'
             '<stop offset="0" stop-color="#d7b68c"/><stop offset="1" stop-color="#caa577"/></linearGradient>')

    # --- tekstur & bayang
    d.append('''
<filter id="fGrain" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
  <feTurbulence type="fractalNoise" baseFrequency="1.6" numOctaves="2" seed="7" result="n"/>
  <feColorMatrix in="n" type="matrix" values="0.16 0 0 0 0.86  0.16 0 0 0 0.86  0.16 0 0 0 0.86  0 0 0 0 1" result="g"/>
  <feBlend in="SourceGraphic" in2="g" mode="multiply" result="b"/>
  <feComposite in="b" in2="SourceGraphic" operator="in"/>
</filter>
<filter id="fWoodGrain" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
  <feTurbulence type="fractalNoise" baseFrequency="1.3 0.035" numOctaves="3" seed="4" result="n"/>
  <feColorMatrix in="n" type="matrix" values="0.32 0 0 0 0.74  0.32 0 0 0 0.74  0.32 0 0 0 0.74  0 0 0 0 1" result="g"/>
  <feBlend in="SourceGraphic" in2="g" mode="multiply" result="b"/>
  <feComposite in="b" in2="SourceGraphic" operator="in"/>
</filter>
<filter id="fGrass" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
  <feTurbulence type="fractalNoise" baseFrequency="1.1" numOctaves="3" seed="11" result="n1"/>
  <feColorMatrix in="n1" type="matrix" values="0 0 0 0 0.30  0 0 0 0 0.46  0 0 0 0 0.22  2.2 0 0 0 -0.95" result="dark"/>
  <feTurbulence type="fractalNoise" baseFrequency="0.07" numOctaves="2" seed="5" result="n2"/>
  <feColorMatrix in="n2" type="matrix" values="0 0 0 0 0.70  0 0 0 0 0.80  0 0 0 0 0.50  1.4 0 0 0 -0.55" result="light"/>
  <feMerge result="tex"><feMergeNode in="SourceGraphic"/><feMergeNode in="light"/><feMergeNode in="dark"/></feMerge>
  <feComposite in="tex" in2="SourceGraphic" operator="in"/>
</filter>
<filter id="fSoil" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
  <feTurbulence type="fractalNoise" baseFrequency="2.2" numOctaves="2" seed="2" result="n"/>
  <feColorMatrix in="n" type="matrix" values="0 0 0 0 0.30  0 0 0 0 0.22  0 0 0 0 0.15  2 0 0 0 -0.8" result="d"/>
  <feMerge result="t"><feMergeNode in="SourceGraphic"/><feMergeNode in="d"/></feMerge>
  <feComposite in="t" in2="SourceGraphic" operator="in"/>
</filter>
<filter id="fShWall" x="-5%" y="-5%" width="112%" height="112%" color-interpolation-filters="sRGB">
  <feGaussianBlur in="SourceAlpha" stdDeviation="0.75"/>
  <feOffset dx="1.15" dy="1.15" result="o"/>
  <feComponentTransfer in="o" result="s"><feFuncA type="linear" slope="0.42"/></feComponentTransfer>
  <feMerge><feMergeNode in="s"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<filter id="fAO" x="-5%" y="-5%" width="110%" height="110%">
  <feMorphology in="SourceAlpha" operator="dilate" radius="0.35" result="d"/>
  <feGaussianBlur in="d" stdDeviation="0.9"/>
</filter>
<filter id="fShFurn" x="-20%" y="-20%" width="150%" height="150%" color-interpolation-filters="sRGB">
  <feGaussianBlur in="SourceAlpha" stdDeviation="0.38"/>
  <feOffset dx="0.55" dy="0.6" result="o"/>
  <feComponentTransfer in="o" result="s"><feFuncA type="linear" slope="0.30"/></feComponentTransfer>
  <feMerge><feMergeNode in="s"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<filter id="fShPlant" x="-30%" y="-30%" width="170%" height="170%" color-interpolation-filters="sRGB">
  <feGaussianBlur in="SourceAlpha" stdDeviation="0.7"/>
  <feOffset dx="1.3" dy="1.4" result="o"/>
  <feComponentTransfer in="o" result="s"><feFuncA type="linear" slope="0.38"/></feComponentTransfer>
  <feMerge><feMergeNode in="s"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<filter id="fSoft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2"/></filter>
<radialGradient id="gLamp" cx="0.5" cy="0.5" r="0.5">
  <stop offset="0" stop-color="#fff6d8" stop-opacity="0.95"/>
  <stop offset="1" stop-color="#ffe9a8" stop-opacity="0"/>
</radialGradient>
<linearGradient id="gGlass" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="#cfe6f2"/><stop offset="1" stop-color="#9cc6dc"/>
</linearGradient>
''')
    # topeng pudar untuk rumput tapak
    d.append(f'<mask id="mLawn" maskUnits="userSpaceOnUse">'
             f'{rect(-2.4, 37.4, -8.6, 32.4, rx=1.6, fill="#fff", filter="url(#fSoft)")}</mask>')
    return '<defs>' + ''.join(d) + '</defs>'


# ============================================================== TAPAK
def site():
    o = []
    o.append(f'<g mask="url(#mLawn)">'
             f'{rect(-3.5, 38.5, -9.5, 33.5, fill="#9dbb7d", filter="url(#fGrass)")}</g>')
    return ''.join(o)


# ============================================================== LANTAI
def floors():
    o = []
    # anjung + laman sisi (turapan batu)
    o.append(rect(*PORCH[:2], PORCH[2], PORCH[3], fill='url(#pPave)'))
    o.append(rect(0, 10, 0, 8.0, fill='url(#pPave)'))
    # zon dapur & dobi
    o.append(rect(0.5, 10.0, 8.0, 29.5, fill='url(#pKitchen)'))
    o.append(rect(3.0, 7.0, 29.5, 30.0, fill='url(#pKitchen)'))
    # rumah utama
    o.append(rect(10.0, 35.0, 0.0, 30.0, fill='url(#pTile)'))
    o.append(rect(10.75, 16.125, 20.875, 29.25, fill='url(#pBath)'))
    o.append(rect(10.75, 14.625, 16.0, 20.875, fill='url(#pBath)'))
    o.append(rect(10.75, 15.75, 27.125, 29.25, fill='url(#pMosaic)'))
    return '<g filter="url(#fGrain)">' + ''.join(o) + '</g>'


def wood_floor():
    x0, x1, y0, y1 = ROOMS['tidur']
    return (f'<g filter="url(#fWoodGrain)">{rect(x0 - 0.4, x1, y0 - 0.4, y1, fill="url(#pWood)")}</g>')


def planter():
    cx, cy, r = PLANTER_SW
    d = (f'M{P(cx, cy)} L{P(cx + r, cy)} A{n(r * S)},{n(r * S)} 0 0 0 {P(cx, cy + r)} Z')
    o = [path(d, fill='#7b6247', filter='url(#fSoil)')]
    o.append(path(d, fill='none', stroke='#cfc6b6', stroke_width=n(0.3 * S), stroke_linejoin='round'))
    o.append(path(d, fill='none', stroke=LINE, stroke_width=THIN))
    return ''.join(o)


def thresholds():
    o = []
    for (x0, x1, y0, y1, kind, sill, head) in OPENINGS:
        if kind == 'door':
            o.append(rect(x0, x1, y0, y1, fill='#e3ddd0', stroke='#b7ad9c', stroke_width=0.08))
    # bukaan belakang zon dapur
    o.append(rect(3.0, 7.0, 29.5, 30.0, fill='#e3ddd0', stroke='#b7ad9c', stroke_width=0.08))
    # tepi anjung (anak tangga turun ke laman)
    o.append(rect(0, 35, -6.0, -5.55, fill='#c9bfae', stroke=LINE, stroke_width=THIN))
    return ''.join(o)


# ============================================================== DINDING
def wall_segments():
    """Tolak bukaan daripada setiap dinding -> senarai segi empat pepejal."""
    segs = []
    for (x0, x1, y0, y1, kind) in WALLS:
        horiz = (x1 - x0) >= (y1 - y0)
        cuts = []
        for (a0, a1, b0, b1, k, s, h) in OPENINGS:
            if horiz and b0 >= y0 - 1e-6 and b1 <= y1 + 1e-6 and a1 > x0 and a0 < x1:
                cuts.append((a0, a1))
            if not horiz and a0 >= x0 - 1e-6 and a1 <= x1 + 1e-6 and b1 > y0 and b0 < y1:
                cuts.append((b0, b1))
        lo, hi = (x0, x1) if horiz else (y0, y1)
        cur = lo
        for c0, c1 in sorted(cuts) + [(hi, hi)]:
            if c0 > cur:
                segs.append((x0, x1, y0, y1, horiz, cur, c0))
            cur = max(cur, c1)
    for (x0, x1, y0, y1, horiz, s0, s1) in segs:
        yield (s0, s1, y0, y1) if horiz else (x0, x1, s0, s1)


def walls():
    rects = [rect(*r, fill=WALL) for r in wall_segments()]
    ao = '<g opacity="0.30" filter="url(#fAO)">' + ''.join(
        rect(*r, fill='#000') for r in wall_segments()) + '</g>'
    return ao, '<g filter="url(#fShWall)">' + ''.join(rects) + '</g>'


def windows():
    o = []
    for (x0, x1, y0, y1, kind, sill, head) in OPENINGS:
        if kind != 'win':
            continue
        horiz = (x1 - x0) >= (y1 - y0)
        o.append(rect(x0, x1, y0, y1, fill='#f7f9fa'))
        if horiz:
            ym = (y0 + y1) / 2
            o.append(line(x0, y0, x1, y0, stroke=INK, stroke_width=THIN))
            o.append(line(x0, y1, x1, y1, stroke=INK, stroke_width=THIN))
            o.append(rect(x0, x1, ym - 0.06, ym + 0.06, fill='url(#gGlass)', stroke='#3e6a85', stroke_width=0.09))
            npan = max(1, math.ceil((x1 - x0) / 2.6))
            for i in range(1, npan):
                xx = x0 + (x1 - x0) * i / npan
                o.append(line(xx, y0, xx, y1, stroke=INK, stroke_width=0.1))
            o.append(line(x0, y0, x0, y1, stroke=INK, stroke_width=0.16))
            o.append(line(x1, y0, x1, y1, stroke=INK, stroke_width=0.16))
            # ambang luar (sill)
            if y0 < 0.01 or y1 > 29.99:
                ys = y0 - 0.12 if y0 < 0.01 else y1 + 0.12
                o.append(rect(x0 - 0.15, x1 + 0.15, min(ys, y0 if y0 < 0.01 else y1),
                              max(ys, y0 if y0 < 0.01 else y1), fill='#f2f0eb', stroke=INK, stroke_width=0.08))
        else:
            xm = (x0 + x1) / 2
            o.append(line(x0, y0, x0, y1, stroke=INK, stroke_width=THIN))
            o.append(line(x1, y0, x1, y1, stroke=INK, stroke_width=THIN))
            o.append(rect(xm - 0.06, xm + 0.06, y0, y1, fill='url(#gGlass)', stroke='#3e6a85', stroke_width=0.09))
            npan = max(1, math.ceil((y1 - y0) / 2.6))
            for i in range(1, npan):
                yy = y0 + (y1 - y0) * i / npan
                o.append(line(x0, yy, x1, yy, stroke=INK, stroke_width=0.1))
            o.append(line(x0, y0, x1, y0, stroke=INK, stroke_width=0.16))
            o.append(line(x0, y1, x1, y1, stroke=INK, stroke_width=0.16))
            outside_w = x0 < 0.01 or abs(x0 - 10.0) < 0.01
            outside_e = x1 > 34.99
            if outside_w or outside_e:
                xs = x0 - 0.12 if outside_w else x1 + 0.12
                xa, xb = (xs, x0) if outside_w else (x1, xs)
                o.append(rect(xa, xb, y0 - 0.15, y1 + 0.15, fill='#f2f0eb', stroke=INK, stroke_width=0.08))
    return ''.join(o)


def doors():
    o = []
    t = 0.14
    for (hx, hy, r, a_open, a_close) in DOOR_LEAVES:
        ao, ac = math.radians(a_open), math.radians(a_close)
        ex, ey = hx + r * math.cos(ao), hy + r * math.sin(ao)
        cx, cy = hx + r * math.cos(ac), hy + r * math.sin(ac)
        # sapuan daun (warna lembut)
        sweep = 1 if ((a_close - a_open) % 360) < 180 else 0
        sweep_svg = 1 - sweep  # paksi Y diterbalikkan
        o.append(path(f'M{P(hx, hy)} L{P(ex, ey)} A{n(r * S)},{n(r * S)} 0 0 {sweep_svg} {P(cx, cy)} Z',
                      fill='#ffffff', fill_opacity='0.35'))
        o.append(path(f'M{P(ex, ey)} A{n(r * S)},{n(r * S)} 0 0 {sweep_svg} {P(cx, cy)}',
                      fill='none', stroke='#5a5650', stroke_width=0.1, stroke_dasharray='0.9 0.45'))
        # daun pintu
        nx, ny = -math.sin(ao), math.cos(ao)
        side = 1 if ((a_close - a_open) % 360) < 180 else -1
        p1 = (hx, hy)
        p2 = (ex, ey)
        p3 = (ex + nx * t * side, ey + ny * t * side)
        p4 = (hx + nx * t * side, hy + ny * t * side)
        o.append(poly([p1, p2, p3, p4], fill='#b88a5e', stroke=INK, stroke_width=0.12))
    return ''.join(o)


def low_walls():
    o = []
    # dinding separuh pancuran
    o.append(rect(*SHOWER_WALL, fill='#a9a49b', stroke=INK, stroke_width=0.12))
    # sekatan kaca ruang makan / tamu
    x0, x1, y0, y1 = DIVIDER
    xm = (x0 + x1) / 2
    o.append(rect(x0, x1, y0, y1, fill='#f4f6f7', stroke=INK, stroke_width=0.14))
    o.append(rect(xm - 0.05, xm + 0.05, y0, y1, fill='url(#gGlass)', stroke='#3e6a85', stroke_width=0.08))
    for yy in (y0 + (y1 - y0) / 3, y0 + 2 * (y1 - y0) / 3):
        o.append(rect(x0, x1, yy - 0.06, yy + 0.06, fill='#3b3b3b'))
    return ''.join(o)


# ============================================================== TANGGA
def stair():
    x0, x1, y0, y1 = STAIR
    ys = STAIR_LANDING_Y
    xm = STAIR_SPLIT
    o = [rect(x0, x1, y0, y1, fill='url(#gStair)', stroke=INK, stroke_width=0.16)]
    o.append(rect(x0, x1, y0, ys, fill='#cfac80', stroke=INK, stroke_width=0.12))   # pelantar
    step = (y1 - ys) / 7
    for i in range(8):
        yy = ys + i * step
        o.append(line(x0, yy, x1, yy, stroke='#6c4f33', stroke_width=0.12))
    # dinding tengah
    o.append(rect(xm - 0.07, xm + 0.07, ys, y1, fill='#4a4a48'))
    # garis potong (patah)
    bx = [(xm + 0.07, 14.3), (23.95, 14.75), (24.1, 14.45), (24.28, 15.1), (24.43, 14.85), (x1, 15.3)]
    o.append(poly(bx, closed=False, fill='none', stroke=INK, stroke_width=0.14))
    # garis jalan + anak panah
    wx1, wx2 = (x0 + xm) / 2, (xm + x1) / 2
    wy = y0 + (ys - y0) / 2 + 0.1
    o.append(circle(wx1, y1 - 0.35, 0.14, fill=INK))
    o.append(poly([(wx1, y1 - 0.35), (wx1, wy), (wx2, wy), (wx2, y1 - 0.45)], closed=False,
                  fill='none', stroke=INK, stroke_width=0.14))
    o.append(poly([(wx2, y1 - 0.15), (wx2 - 0.22, y1 - 0.62), (wx2 + 0.22, y1 - 0.62)], fill=INK))
    o.append(text(x0 + 0.62, 14.9, 'NAIK', size=1.45, weight=600, rot=-90, fill=INK, ls=0.2))
    return ''.join(o)


# ============================================================== PERABOT
def furn_style(fill='#fbfaf7'):
    return dict(fill=fill, stroke=LINE, stroke_width=MED)


def rug(x0, x1, y0, y1, base, border, inner=None):
    o = [rect(x0, x1, y0, y1, rx=0.15, fill=base, stroke=border, stroke_width=0.12)]
    o.append(rect(x0 + 0.3, x1 - 0.3, y0 + 0.3, y1 - 0.3, rx=0.08, fill='none', stroke=border,
                  stroke_width=0.22, stroke_opacity='0.7'))
    if inner:
        o.append(rect(x0 + 0.55, x1 - 0.55, y0 + 0.55, y1 - 0.55, fill='none', stroke=inner,
                      stroke_width=0.1, stroke_dasharray='0.5 0.35'))
    return ''.join(o)


def bed():
    x0, x1, y0, y1 = BED
    o = [rect(x0, x1, y0, y1, rx=0.12, fill='#a77d55', stroke=INK, stroke_width=MED)]            # rangka
    o.append(rect(x0 - 0.05, x1 + 0.05, y1 - 0.42, y1, rx=0.08, fill='#7c5a3c', stroke=INK, stroke_width=MED))
    o.append(rect(x0 + 0.15, x1 - 0.15, y0 + 0.15, y1 - 0.45, rx=0.18, fill='#fbfaf6', stroke=LINE, stroke_width=0.14))
    # bantal
    pw = (x1 - x0 - 0.6) / 2
    for i in range(2):
        px = x0 + 0.25 + i * (pw + 0.1)
        o.append(rect(px, px + pw, y1 - 1.75, y1 - 0.6, rx=0.3, fill='#ffffff', stroke=LINE, stroke_width=0.14))
        o.append(line(px + 0.3, y1 - 1.18, px + pw - 0.3, y1 - 1.18, stroke='#cfcac1', stroke_width=0.1))
    # selimut + lipatan
    o.append(rect(x0 + 0.1, x1 - 0.1, y0 + 0.1, y1 - 2.15, rx=0.2, fill='#e9e4da', stroke=LINE, stroke_width=0.14))
    o.append(rect(x0 + 0.1, x1 - 0.1, y1 - 2.65, y1 - 2.15, rx=0.1, fill='#f7f4ee', stroke=LINE, stroke_width=0.12))
    # kain hiasan kaki katil
    o.append(rect(x0 + 0.05, x1 - 0.05, y0 + 0.55, y0 + 1.75, rx=0.08, fill='#b06f52', stroke='#6d3f2c', stroke_width=0.12))
    for k in range(1, 4):
        yy = y0 + 0.55 + k * 0.3
        o.append(line(x0 + 0.05, yy, x1 - 0.05, yy, stroke='#8f553d', stroke_width=0.07))
    for k in range(3):
        o.append(path(f'M{P(x0 + 0.6 + k * 1.6, y0 + 2.4)} q{n(0.5 * S)},{n(-0.25 * S)} {n(1.1 * S)},0',
                      fill='none', stroke='#d2ccc0', stroke_width=0.1))
    return ''.join(o)


def wardrobe():
    x0, x1, y0, y1 = WARDROBE
    o = [rect(x0, x1, y0, y1, fill='#efe8dc', stroke=INK, stroke_width=MED)]
    o.append(line(x1 - 0.12, y0, x1 - 0.12, y1, stroke=LINE, stroke_width=0.1))
    o.append(line(x1 - 0.25, y0 + 0.05, x1 - 0.25, (y0 + y1) / 2 + 0.3, stroke=LINE, stroke_width=0.1))
    o.append(line(x1 - 0.25, (y0 + y1) / 2 - 0.3, x1 - 0.25, y1 - 0.05, stroke=LINE, stroke_width=0.1))
    xr = (x0 + x1) / 2 - 0.1
    o.append(line(xr, y0 + 0.2, xr, y1 - 0.2, stroke='#8a8478', stroke_width=0.1, stroke_dasharray='0.4 0.25'))
    for k in range(13):
        yy = y0 + 0.45 + k * (y1 - y0 - 0.9) / 12
        o.append(line(xr - 0.7, yy, xr + 0.7, yy, stroke='#b9b1a3', stroke_width=0.08))
    return ''.join(o)


def bedroom_rest():
    o = []
    x0, x1, y0, y1 = NIGHTSTAND
    o.append(rect(x0, x1, y0, y1, rx=0.06, fill='#a07752', stroke=INK, stroke_width=MED))
    o.append(circle((x0 + x1) / 2, (y0 + y1) / 2, 0.5, fill='url(#gLamp)'))
    o.append(circle((x0 + x1) / 2, (y0 + y1) / 2, 0.32, fill='#f6efdc', stroke=LINE, stroke_width=0.1))
    x0, x1, y0, y1 = DRESSER
    o.append(rect(x0, x1, y0, y1, fill='#efe8dc', stroke=INK, stroke_width=MED))
    o.append(line(x0 + 0.12, y0, x0 + 0.12, y1, stroke=LINE, stroke_width=0.08))
    o.append(rect(x0 + 0.45, x0 + 1.05, y1 - 1.0, y1 - 0.4, rx=0.1, fill='#d9d2c4', stroke=LINE, stroke_width=0.08))
    o.append(circle(x0 + 0.75, y0 + 0.7, 0.25, fill='#7f9a6c', stroke='#4b6340', stroke_width=0.08))
    x0, x1, y0, y1 = DESK
    o.append(rect(x0, x1, y0, y1, fill='#b48a62', stroke=INK, stroke_width=MED))
    o.append(rect(x0 + 1.2, x0 + 2.3, y0 + 0.35, y0 + 1.15, rx=0.05, fill='#cfd2d4', stroke=LINE, stroke_width=0.1))
    o.append(circle(x1 - 0.5, y0 + 0.55, 0.42, fill='url(#gLamp)'))
    o.append(circle(x1 - 0.5, y0 + 0.55, 0.25, fill='#f6efdc', stroke=LINE, stroke_width=0.08))
    cx, cy, r = DESK_CHAIR
    o.append(circle(cx, cy, r, fill='#8a9a84', stroke=INK, stroke_width=MED))
    o.append(path(f'M{P(cx - r * 0.95, cy + 0.15)} A{n(r * S)},{n(r * S)} 0 0 1 {P(cx + r * 0.95, cy + 0.15)}',
                  fill='none', stroke='#5d6d58', stroke_width=n(0.25 * S)))
    o.append(circle(cx, cy - 0.05, r * 0.55, fill='#9eae97', stroke='none'))
    return ''.join(o)


def sofa():
    o = []
    o.append(poly(SOFA_U, fill='#cdc6ba', stroke=INK, stroke_width=MED))
    back = [(23.0, 8.0), (23.0, 0.75), (34.25, 0.75), (34.25, 7.25), (33.6, 7.25),
            (33.6, 1.4), (23.65, 1.4), (23.65, 8.0)]
    o.append(poly(back, fill='#bdb5a8', stroke=LINE, stroke_width=0.14))
    o.append(rect(23.65, 25.5, 7.45, 8.0, rx=0.12, fill='#c3bbae', stroke=LINE, stroke_width=0.14))
    o.append(rect(32.0, 33.6, 6.7, 7.25, rx=0.12, fill='#c3bbae', stroke=LINE, stroke_width=0.14))
    seats = [(23.65, 25.5, 1.4, 3.25), (23.65, 25.5, 3.25, 5.35), (23.65, 25.5, 5.35, 7.45),
             (25.5, 28.75, 1.4, 3.25), (28.75, 32.0, 1.4, 3.25),
             (32.0, 33.6, 1.4, 3.25), (32.0, 33.6, 3.25, 5.0), (32.0, 33.6, 5.0, 6.7)]
    for (a, b, c, d) in seats:
        o.append(rect(a + 0.05, b - 0.05, c + 0.05, d - 0.05, rx=0.18, fill='#ddd7cc', stroke=LINE, stroke_width=0.12))
    # bantal hiasan
    pillows = [(24.25, 2.0, 25, '#c98f5e'), (24.25, 6.6, -15, '#7d8f74'), (33.0, 2.0, -20, '#c98f5e'),
               (28.75, 1.95, 8, '#e8e2d6'), (33.0, 5.9, 12, '#7d8f74')]
    for (px, py, ang, col) in pillows:
        o.append(f'<g transform="rotate({ang} {n(mx(px))} {n(my(py))})">'
                 + rect(px - 0.5, px + 0.5, py - 0.32, py + 0.32, rx=0.15, fill=col, stroke=INK, stroke_width=0.1)
                 + '</g>')
    return ''.join(o)


def living_rest():
    o = []
    x0, x1, y0, y1 = COFFEE_TABLE
    o.append(rect(x0, x1, y0, y1, rx=0.35, fill='#a87b52', stroke=INK, stroke_width=MED))
    o.append(rect(x0 + 0.15, x1 - 0.15, y0 + 0.15, y1 - 0.15, rx=0.25, fill='none', stroke='#8a6240', stroke_width=0.08))
    o.append(rect(x0 + 0.5, x0 + 1.4, y0 + 0.5, y0 + 1.25, fill='#e9e4da', stroke=LINE, stroke_width=0.08))
    o.append(circle(x1 - 0.8, y0 + 1.05, 0.36, fill='#f3f0ea', stroke=LINE, stroke_width=0.08))
    o.append(circle(x1 - 0.8, y0 + 1.05, 0.2, fill='#7f9a6c'))
    x0, x1, y0, y1 = TV_CONSOLE
    o.append(rect(x0, x1, y0, y1, fill='#7d5a3c', stroke=INK, stroke_width=MED))
    for k in (1, 2):
        xx = x0 + (x1 - x0) * k / 3
        o.append(line(xx, y0, xx, y1 - 0.1, stroke='#5e422b', stroke_width=0.08))
    o.append(rect(x0 + 0.5, x1 - 0.5, y1 - 0.35, y1 - 0.12, fill='#1c1c1c'))
    o.append(rect(x0 + 0.25, x0 + 0.85, y0 + 0.3, y0 + 0.9, rx=0.05, fill='#e8e2d6', stroke=LINE, stroke_width=0.06))
    return ''.join(o)


def chair(cx, cy, ang, col='#e9e3d7', back='#8c6a4a'):
    s = 0.68
    g = [rect(cx - s, cx + s, cy - s, cy + s, rx=0.2, fill=col, stroke=INK, stroke_width=0.14)]
    g.append(rect(cx - s, cx - s + 0.28, cy - s + 0.05, cy + s - 0.05, rx=0.1, fill=back, stroke=INK, stroke_width=0.1))
    return f'<g transform="rotate({-ang + 180} {n(mx(cx))} {n(my(cy))})">' + ''.join(g) + '</g>'


def dining():
    o = []
    for (cx, cy, ang) in DINING_CHAIRS:
        o.append(chair(cx, cy, ang))
    x0, x1, y0, y1 = DINING_TABLE
    o.append(rect(x0, x1, y0, y1, rx=0.15, fill='#b98a5e', stroke=INK, stroke_width=MED))
    o.append(rect(x0 + 0.12, x1 - 0.12, y0 + 0.12, y1 - 0.12, rx=0.1, fill='none', stroke='#9a6f48', stroke_width=0.08))
    o.append(rect((x0 + x1) / 2 - 0.45, (x0 + x1) / 2 + 0.45, y0 + 0.4, y1 - 0.4, fill='#e7ddc9', stroke='#a89a82', stroke_width=0.06))
    for (cx, cy, ang) in DINING_CHAIRS:
        a = math.radians(ang)
        px = cx - 1.05 * math.cos(a)
        py = cy - 1.05 * math.sin(a)
        px = min(max(px, x0 + 0.45), x1 - 0.45)
        py = min(max(py, y0 + 0.45), y1 - 0.45)
        o.append(circle(px, py, 0.36, fill='#ffffff', stroke=LINE, stroke_width=0.08))
        o.append(circle(px, py, 0.22, fill='none', stroke='#cfc9bd', stroke_width=0.06))
    o.append(circle((x0 + x1) / 2, (y0 + y1) / 2, 0.3, fill='#7f9a6c', stroke='#4b6340', stroke_width=0.08))
    return ''.join(o)


def hall_cabinet():
    x0, x1, y0, y1 = HALL_CABINET
    o = [rect(x0, x1, y0, y1, fill='#efe8dc', stroke=INK, stroke_width=MED)]
    o.append(line(x1 - 0.1, y0, x1 - 0.1, y1, stroke=LINE, stroke_width=0.08))
    for k in (1, 2):
        yy = y0 + (y1 - y0) * k / 3
        o.append(line(x0, yy, x1, yy, stroke=LINE, stroke_width=0.08))
    return ''.join(o)


def kitchen():
    o = []
    stone = dict(fill='#f1eee8', stroke=INK, stroke_width=MED)
    pts = [(0.5, 29.5), (2.5, 29.5), (2.5, 17.0), (6.0, 17.0), (6.0, 14.75), (0.5, 14.75)]
    o.append(poly(pts, **stone))
    o.append(rect(*COUNTER_S, **stone))
    o.append(rect(*BAR, fill='#b88c60', stroke=INK, stroke_width=MED))
    for k in range(1, 6):
        yy = BAR[2] + (BAR[3] - BAR[2]) * k / 6
        o.append(line(BAR[0], yy, BAR[1], yy, stroke='#9e7650', stroke_width=0.06))
    # garis hidung permukaan kabinet
    o.append(poly([(2.38, 29.5), (2.38, 17.12), (5.88, 17.12), (5.88, 14.87)], closed=False,
                  fill='none', stroke='#9c978d', stroke_width=0.07))
    o.append(line(2.38, 8.0, 2.38, 12.75, stroke='#9c978d', stroke_width=0.07))
    # sinki dua mangkuk
    x0, x1, y0, y1 = KSINK
    o.append(rect(x0, x1, y0, y1, rx=0.1, fill='#d3d8db', stroke=INK, stroke_width=0.12))
    ym = (y0 + y1) / 2
    for (a, b) in ((y0 + 0.15, ym - 0.08), (ym + 0.08, y1 - 0.15)):
        o.append(rect(x0 + 0.15, x1 - 0.15, a, b, rx=0.15, fill='#b8c0c5', stroke=LINE, stroke_width=0.1))
        o.append(circle((x0 + x1) / 2, (a + b) / 2, 0.1, fill='none', stroke=LINE, stroke_width=0.06))
    o.append(rect(x0 + 0.02, x0 + 0.17, ym - 0.1, ym + 0.1, fill='#777'))
    # dapur gas
    x0, x1, y0, y1 = HOB
    o.append(rect(x0, x1, y0, y1, rx=0.08, fill='#2a2a2a', stroke=INK, stroke_width=0.12))
    for yy in (y0 + 0.6, y1 - 0.6):
        o.append(circle((x0 + x1) / 2, yy, 0.38, fill='none', stroke='#8a8a8a', stroke_width=0.12))
        o.append(circle((x0 + x1) / 2, yy, 0.18, fill='none', stroke='#8a8a8a', stroke_width=0.1))
    # meja bujur + bangku
    cx, cy, rx_, ry_ = KTABLE
    for (sx, sy) in KSTOOLS:
        o.append(circle(sx, sy, 0.55, fill='#7d8f74', stroke=INK, stroke_width=0.14))
        o.append(circle(sx, sy, 0.35, fill='none', stroke='#5d6d58', stroke_width=0.08))
    o.append(ellipse(cx, cy, rx_, ry_, fill='#c79f73', stroke=INK, stroke_width=MED))
    o.append(ellipse(cx, cy, rx_ - 0.15, ry_ - 0.15, fill='none', stroke='#a37b52', stroke_width=0.08))
    o.append(circle(cx, cy + 0.2, 0.25, fill='#f3f0ea', stroke=LINE, stroke_width=0.06))
    # mesin basuh & pengering
    for (x0, x1, y0, y1) in (WASHER, DRYER):
        o.append(rect(x0, x1, y0, y1, rx=0.1, fill='#fbfbfb', stroke=INK, stroke_width=MED))
        o.append(rect(x0, x0 + 0.35, y0 + 0.1, y1 - 0.1, fill='#dcdfe1', stroke=LINE, stroke_width=0.08))
        o.append(circle((x0 + x1) / 2 + 0.15, (y0 + y1) / 2, 0.62, fill='none', stroke='#9aa0a4',
                        stroke_width=0.1, stroke_dasharray='0.35 0.2'))
    # sinki utiliti
    x0, x1, y0, y1 = UTILITY_SINK
    o.append(rect(x0, x1, y0, y1, fill='#f1eee8', stroke=INK, stroke_width=MED))
    o.append(rect(x0 + 0.25, x1 - 0.35, y0 + 0.3, y1 - 0.3, rx=0.2, fill='#d3d8db', stroke=LINE, stroke_width=0.1))
    o.append(circle((x0 + x1) / 2 - 0.05, (y0 + y1) / 2, 0.1, fill='none', stroke=LINE, stroke_width=0.06))
    o.append(rect(x1 - 0.3, x1 - 0.12, (y0 + y1) / 2 - 0.1, (y0 + y1) / 2 + 0.1, fill='#777'))
    return ''.join(o)


def bathroom():
    o = []
    x0, x1, y0, y1 = WC
    o.append(rect(x0, x0 + 0.6, y0, y1, rx=0.08, fill='#ffffff', stroke=INK, stroke_width=MED))
    cy = (y0 + y1) / 2
    o.append(ellipse(x0 + 1.32, cy, 0.78, 0.6, fill='#ffffff', stroke=INK, stroke_width=MED))
    o.append(ellipse(x0 + 1.4, cy, 0.55, 0.4, fill='#eef1f2', stroke=LINE, stroke_width=0.1))
    o.append(rect(x0 + 0.55, x0 + 0.75, cy - 0.45, cy + 0.45, fill='#ffffff', stroke=LINE, stroke_width=0.1))
    cx, cy, r = BASIN
    o.append(path(f'M{P(10.75, cy - r)} L{P(cx, cy - r)} A{n(r * S)},{n(r * S)} 0 0 0 {P(cx, cy + r)} '
                  f'L{P(10.75, cy + r)} Z', fill='#ffffff', stroke=INK, stroke_width=MED))
    o.append(ellipse(cx - 0.05, cy, r * 0.6, r * 0.72, fill='#eef1f2', stroke=LINE, stroke_width=0.1))
    o.append(rect(10.8, 11.1, cy - 0.06, cy + 0.06, fill='#888'))
    x, y = SHOWER_HEAD
    o.append(circle(x, y, 0.42, fill='none', stroke='#5a6a72', stroke_width=0.1, stroke_dasharray='0.25 0.18'))
    o.append(rect(x - 0.15, x + 0.15, 29.25 - 0.12, 29.25, fill='#888'))
    x, y = FLOOR_TRAP
    o.append(rect(x - 0.2, x + 0.2, y - 0.2, y + 0.2, fill='#d6dbdd', stroke=INK, stroke_width=0.08))
    for k in (-0.1, 0, 0.1):
        o.append(line(x - 0.15, y + k, x + 0.15, y + k, stroke='#666', stroke_width=0.04))
    return ''.join(o)


# ============================================================== TUMBUHAN
GREENS = ['#4f7d3c', '#5e8f47', '#6d9e52', '#7fae5e', '#46733a', '#88b766']


def leaf(cx, cy, ang, l0, l1, w, col, stroke='#2f5126'):
    a = math.radians(ang)
    ux, uy = math.cos(a), math.sin(a)
    vx, vy = -uy, ux
    bx, by = cx + ux * l0, cy + uy * l0
    tx, ty = cx + ux * l1, cy + uy * l1
    mxp, myp = (bx + tx) / 2, (by + ty) / 2
    c1 = (mxp + vx * w, myp + vy * w)
    c2 = (mxp - vx * w, myp - vy * w)
    d = f'M{P(bx, by)} Q{P(*c1)} {P(tx, ty)} Q{P(*c2)} {P(bx, by)} Z'
    return path(d, fill=col, stroke=stroke, stroke_width=0.05)


def shrub(cx, cy, r, seed):
    rnd = random.Random(seed)
    o = [circle(cx, cy, r * 0.9, fill='#3f6a31')]
    for layer, (k, scale) in enumerate(((18, 1.0), (13, 0.75), (9, 0.5))):
        for i in range(k):
            ang = i * 360 / k + rnd.uniform(-10, 10) + layer * 13
            L = r * scale * rnd.uniform(0.82, 1.0)
            o.append(leaf(cx, cy, ang, r * 0.08, L, L * 0.2, rnd.choice(GREENS)))
    o.append(circle(cx, cy, r * 0.12, fill='#8cbf6a'))
    return ''.join(o)


def palm(cx, cy, r, seed):
    rnd = random.Random(seed)
    o = []
    k = 11
    for i in range(k):
        ang = i * 360 / k + rnd.uniform(-8, 8)
        a = math.radians(ang)
        L = r * rnd.uniform(0.85, 1.0)
        tx, ty = cx + math.cos(a) * L, cy + math.sin(a) * L
        col = rnd.choice(GREENS)
        o.append(leaf(cx, cy, ang, 0.05, L, L * 0.16, col))
        nl = 9
        for j in range(1, nl):
            f_ = j / nl
            px, py = cx + math.cos(a) * L * f_, cy + math.sin(a) * L * f_
            for sgn in (1, -1):
                b = a + sgn * math.radians(55)
                ll = L * 0.24 * (1 - f_ * 0.6)
                o.append(line(px, py, px + math.cos(b) * ll, py + math.sin(b) * ll,
                              stroke=col, stroke_width=0.16, stroke_linecap='round'))
        o.append(line(cx, cy, tx, ty, stroke='#c8d9a8', stroke_width=0.06))
    o.append(circle(cx, cy, r * 0.1, fill='#7a5c3a'))
    return ''.join(o)


def pot(cx, cy, r, seed, pot_r=None, pot_col='#b9774e'):
    pr = pot_r or r * 0.75
    o = [circle(cx, cy, pr, fill=pot_col, stroke=INK, stroke_width=0.12),
         circle(cx, cy, pr * 0.82, fill='#5b4636')]
    o.append(shrub(cx, cy, r, seed))
    return ''.join(o)


def plants():
    o = []
    for i, (x, y, r, kind) in enumerate(PLANTS):
        if kind == 'shrub':
            o.append(shrub(x, y, r, 10 + i))
        elif kind == 'palm':
            o.append(palm(x, y, r, 20 + i))
        elif kind == 'bigpot':
            o.append(pot(x, y, r, 30 + i, pot_r=0.8, pot_col='#9a9a96'))
        else:
            o.append(pot(x, y, r, 40 + i, pot_r=r * 0.8))
    return '<g filter="url(#fShPlant)">' + ''.join(o) + '</g>'


# ============================================================== LABEL
def room_label(x, y, name, en, size_txt, big=True):
    o = [text(x, y, name, size=2.25 if big else 1.75, weight=700, fill='#1f1f1d', ls=0.28)]
    o.append(text(x, y - (0.52 if big else 0.42), en, size=1.25 if big else 1.05, weight=500,
                  fill='#6a665f', ls=0.35))
    if size_txt:
        o.append(text(x, y - (1.1 if big else 0.9), size_txt, size=1.6 if big else 1.3, weight=400, fill='#2e2d2a'))
    return ''.join(o)


def labels():
    o = []
    o.append(room_label(29.9, 11.9, 'RUANG TAMU', 'LIVING', '11\'6" × 16\'6"'))
    o.append(room_label(15.4, 12.6, 'RUANG MAKAN', 'DINING', '13\'1" × 16\'11"'))
    o.append(room_label(27.1, 19.5, 'BILIK TIDUR', 'BEDROOM', '14\'0" × 12\'0"'))
    o.append(room_label(14.55, 26.05, 'BILIK AIR', 'BATH', '5\'0" × 8\'0"', big=False))
    o.append(room_label(12.5, 19.25, 'STOR', 'STORE', '3\'6" × 4\'6"', big=False))
    o.append(room_label(18.125, 28.0, 'ALMARI', 'CLOSET', '4\'0" × 3\'6"', big=False))
    o.append(room_label(18.125, 21.6, 'LALUAN', 'CORRIDOR', '', big=False))
    o.append(room_label(4.75, 23.6, 'DAPUR &amp; DOBI', 'KITCHEN &amp; LAUNDRY', '10\'0" × 30\'0"'))
    o.append(room_label(27.75, -2.6, 'ANJUNG', 'PORCH', '35\'0" × 6\'0"'))
    o.append(text(5.6, 5.1, 'LAMAN', size=1.5, weight=700, fill='#3b3a36', ls=0.3))
    o.append(text(5.6, 4.55, 'GARDEN', size=1.05, weight=500, fill='#6a665f', ls=0.35))
    o.append(text(5.0, 29.15, 'BUKAAN', size=1.0, weight=600, fill='#55524b', ls=0.25))
    o.append(text(19.0, -0.95, 'PINTU UTAMA', size=1.0, weight=600, fill='#55524b', ls=0.25))
    return ''.join(o)


# ============================================================== UKURAN
def tick(x, y):
    a = 0.22
    return line(x - a, y - a, x + a, y + a, stroke=INK, stroke_width=0.28)


def dim_h(xs, y, y_obj, metric=False):
    o = []
    for x in xs:
        o.append(line(x, y_obj + (0.25 if y > y_obj else -0.25), x, y + (0.35 if y > y_obj else -0.35),
                      stroke='#6b6862', stroke_width=0.08))
    o.append(line(xs[0] - 0.4, y, xs[-1] + 0.4, y, stroke='#3a3935', stroke_width=0.1))
    for x in xs:
        o.append(tick(x, y))
    for a, b in zip(xs, xs[1:]):
        lab = ft_in(b - a)
        if metric:
            lab += f'  ({(b - a) * 0.3048:.2f} m)'
        o.append(text((a + b) / 2, y + 0.22, lab, size=1.55, weight=500, fill='#2b2a27', halo=True))
    return ''.join(o)


def dim_v(ys, x, x_obj, metric=False):
    o = []
    for y in ys:
        o.append(line(x_obj + (0.25 if x > x_obj else -0.25), y, x + (0.35 if x > x_obj else -0.35), y,
                      stroke='#6b6862', stroke_width=0.08))
    o.append(line(x, ys[0] - 0.4, x, ys[-1] + 0.4, stroke='#3a3935', stroke_width=0.1))
    for y in ys:
        o.append(tick(x, y))
    for a, b in zip(ys, ys[1:]):
        lab = ft_in(b - a)
        if metric:
            lab += f'  ({(b - a) * 0.3048:.2f} m)'
        o.append(text(x - 0.22, (a + b) / 2, lab, size=1.55, weight=500, fill='#2b2a27', rot=-90))
    return ''.join(o)


def dims():
    o = []
    # utara
    o.append(dim_h([0, 10, 16.125, 20.125, 35], 32.75, 30.0))
    o.append(dim_h([0, 35], 34.0, 30.0, metric=True))
    # selatan
    o.append(dim_h([0, 10, 16.75, 21.25, 35], -8.0, -6.0))
    o.append(dim_h([0, 35], -9.25, -6.0, metric=True))
    # barat
    o.append(dim_v([-6, 0, 8, 30], -2.0, 0.0))
    o.append(dim_v([-6, 30], -3.25, 0.0, metric=True))
    # timur
    o.append(dim_v([-6, 0, 16.75, 30], 37.0, 35.0))
    o.append(dim_v([-6, 30], 38.25, 35.0, metric=True))
    return ''.join(o)


# ============================================================== BLOK TAJUK
def tb_text(x, y, s, size=2.0, weight=400, fill='#222', anchor='start', ls=0, style=''):
    st = f' font-style="{style}"' if style else ''
    return (f'<text x="{n(x)}" y="{n(y)}" font-family="Inter" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" letter-spacing="{ls}"{st}>{s}</text>')


def title_block():
    x0 = SHEET_W - FRAME - TB_W
    x1 = SHEET_W - FRAME
    y0, y1 = FRAME, SHEET_H - FRAME
    cx = (x0 + x1) / 2
    pad = 6
    o = [f'<rect x="{n(x0)}" y="{n(y0)}" width="{n(TB_W)}" height="{n(y1 - y0)}" fill="#f7f5f0"/>',
         f'<line x1="{n(x0)}" y1="{n(y0)}" x2="{n(x0)}" y2="{n(y1)}" stroke="{INK}" stroke-width="0.5"/>']

    def hr(y, w=0.25):
        return f'<line x1="{n(x0)}" y1="{n(y)}" x2="{n(x1)}" y2="{n(y)}" stroke="{INK}" stroke-width="{w}"/>'

    # --- kepala
    y = y0 + 10
    o.append(tb_text(x0 + pad, y, 'LUKISAN PERSEMBAHAN', 2.0, 600, '#8a6a46', ls=0.6))
    o.append(tb_text(x0 + pad, y + 8, 'CADANGAN', 4.2, 300, '#222', ls=0.3))
    o.append(tb_text(x0 + pad, y + 14.5, 'RUMAH KEDIAMAN', 5.4, 700, '#1a1a1a', ls=0.2))
    o.append(tb_text(x0 + pad, y + 20.5, 'Pelan lantai bawah · rumah utama 25\' × 30\'', 2.0, 400, '#555'))
    o.append(tb_text(x0 + pad, y + 24.5, 'dengan dapur sisi & anjung hadapan', 2.0, 400, '#555'))
    o.append(hr(y0 + 41))

    # --- arah utara + skala
    ny = y0 + 60
    nx = x0 + 20
    o.append(f'<circle cx="{n(nx)}" cy="{n(ny)}" r="9" fill="none" stroke="{INK}" stroke-width="0.3"/>')
    o.append(f'<circle cx="{n(nx)}" cy="{n(ny)}" r="7.6" fill="none" stroke="{INK}" stroke-width="0.12"/>')
    o.append(f'<path d="M{n(nx)},{n(ny - 11)} L{n(nx + 3.4)},{n(ny + 5)} L{n(nx)},{n(ny + 2.6)} Z" fill="{INK}"/>')
    o.append(f'<path d="M{n(nx)},{n(ny - 11)} L{n(nx - 3.4)},{n(ny + 5)} L{n(nx)},{n(ny + 2.6)} Z" '
             f'fill="#fff" stroke="{INK}" stroke-width="0.25"/>')
    o.append(tb_text(nx, ny - 12.6, 'U', 3.0, 700, INK, 'middle'))
    o.append(tb_text(nx, ny + 14.2, 'UTARA (ANDAIAN)', 1.4, 500, '#666', 'middle', ls=0.3))
    # bar skala 0-8 kaki dan 0-2 meter
    sx = x0 + 40
    sy = ny - 2
    o.append(tb_text(sx, sy - 8, 'SKALA 1:50', 2.6, 700, INK, ls=0.4))
    o.append(tb_text(sx, sy - 4.5, 'pada kertas A3', 1.6, 400, '#666'))
    for i in range(4):
        col = INK if i % 2 == 0 else '#fff'
        o.append(f'<rect x="{n(sx + i * 2 * S)}" y="{n(sy)}" width="{n(2 * S)}" height="1.4" fill="{col}" '
                 f'stroke="{INK}" stroke-width="0.2"/>')
    for i in range(5):
        o.append(tb_text(sx + i * 2 * S, sy + 4.2, str(i * 2), 1.5, 500, '#333', 'middle'))
    o.append(tb_text(sx + 8 * S + 2.2, sy + 1.3, 'kaki', 1.5, 400, '#333'))
    w = 500 / 304.8 * S
    for i in range(4):
        col = INK if i % 2 == 0 else '#fff'
        o.append(f'<rect x="{n(sx + i * w)}" y="{n(sy + 8)}" width="{n(w)}" height="1.4" fill="{col}" '
                 f'stroke="{INK}" stroke-width="0.2"/>')
    for i in range(5):
        o.append(tb_text(sx + i * w, sy + 12.2, ('0', '0.5', '1', '1.5', '2')[i], 1.5, 500, '#333', 'middle'))
    o.append(tb_text(sx + 4 * w + 2.2, sy + 9.3, 'meter', 1.5, 400, '#333'))
    o.append(hr(y0 + 81))

    # --- petunjuk kemasan
    ly = y0 + 89
    o.append(tb_text(x0 + pad, ly, 'CADANGAN KEMASAN LANTAI', 2.1, 700, INK, ls=0.4))
    items = [
        ('pTile', 'Jubin porselin 600×600', 'Ruang tamu, ruang makan, laluan'),
        ('pWood', 'Lantai kayu / laminat oak', 'Bilik tidur'),
        ('pBath', 'Jubin anti-gelincir 300×300', 'Bilik air, stor'),
        ('pKitchen', 'Jubin seramik 300×300 (serong)', 'Dapur & dobi'),
        ('pPave', 'Turapan batu 300×600', 'Anjung, laman sisi'),
        ('grass', 'Rumput / landskap', 'Kawasan luar'),
    ]
    for i, (pat, a, b) in enumerate(items):
        yy = ly + 5 + i * 8.6
        sw = f'<rect x="{n(x0 + pad)}" y="{n(yy)}" width="11" height="6.4" fill="url(#{pat})" stroke="{INK}" stroke-width="0.2"/>'
        if pat == 'grass':
            sw = (f'<rect x="{n(x0 + pad)}" y="{n(yy)}" width="11" height="6.4" fill="#9dbb7d" filter="url(#fGrass)"/>'
                  f'<rect x="{n(x0 + pad)}" y="{n(yy)}" width="11" height="6.4" fill="none" stroke="{INK}" stroke-width="0.2"/>')
        o.append(sw)
        o.append(tb_text(x0 + pad + 14, yy + 2.8, a, 1.85, 600, '#222'))
        o.append(tb_text(x0 + pad + 14, yy + 5.6, b.replace('&', '&amp;'), 1.6, 400, '#666'))
    o.append(hr(y0 + 147))

    # --- jadual keluasan
    ty = y0 + 155
    o.append(tb_text(x0 + pad, ty, 'JADUAL KELUASAN (KASAR)', 2.1, 700, INK, ls=0.4))
    rows = [('Rumah utama', "25' × 30'", 750), ('Dapur & dobi + laman', "10' × 30'", 300),
            ('Anjung hadapan', "35' × 6'", 210)]
    for i, (a, b, sq) in enumerate(rows):
        yy = ty + 6.5 + i * 5.2
        o.append(tb_text(x0 + pad, yy, a.replace('&', '&amp;'), 1.8, 400, '#222'))
        o.append(tb_text(x0 + 52, yy, b, 1.8, 400, '#555', 'middle'))
        o.append(tb_text(x1 - pad, yy, f'{sq:,} kp  ·  {sq * 0.092903:.1f} m²', 1.8, 400, '#222', 'end'))
    yy = ty + 6.5 + 3 * 5.2 + 0.8
    o.append(f'<line x1="{n(x0 + pad)}" y1="{n(yy - 3.6)}" x2="{n(x1 - pad)}" y2="{n(yy - 3.6)}" stroke="#999" stroke-width="0.15"/>')
    o.append(tb_text(x0 + pad, yy, 'Jumlah', 1.9, 700, '#222'))
    o.append(tb_text(x1 - pad, yy, '1,260 kp  ·  117.1 m²', 1.9, 700, '#222', 'end'))
    o.append(hr(y0 + 186))

    # --- nota
    ny2 = y0 + 194
    o.append(tb_text(x0 + pad, ny2, 'NOTA', 2.1, 700, INK, ls=0.4))
    notes = ['Semua ukuran dalam kaki dan inci.',
             'Saiz bilik ialah ukuran dalaman anggaran',
             'mengikut lakaran asal.',
             'Dinding luar 9", dinding dalam 4½".',
             'Kemasan, perabot & landskap ialah cadangan.',
             'Sahkan semua ukuran di tapak sebelum bina.']
    for i, s in enumerate(notes):
        num = '' if s.startswith('mengikut') else f'{[1, 2, None, 3, 4, 5][i]}.'
        o.append(tb_text(x0 + pad, ny2 + 5.5 + i * 4.2, num, 1.7, 600, '#444'))
        o.append(tb_text(x0 + pad + 4, ny2 + 5.5 + i * 4.2, s, 1.7, 400, '#333'))
    o.append(hr(y0 + 226, 0.4))

    # --- tajuk lukisan
    o.append(f'<rect x="{n(x0)}" y="{n(y0 + 226)}" width="{n(TB_W)}" height="{n(y1 - y0 - 226)}" fill="#22211f"/>')
    o.append(tb_text(x0 + pad, y0 + 236, 'TAJUK LUKISAN', 1.6, 600, '#c9b08a', ls=0.6))
    o.append(tb_text(x0 + pad, y0 + 245, 'PELAN LANTAI BAWAH', 5.6, 800, '#ffffff', ls=0.3))
    o.append(tb_text(x0 + pad, y0 + 250.5, 'GROUND FLOOR PLAN', 2.2, 500, '#bdb8ae', ls=0.6))
    fy = y0 + 259
    o.append(f'<line x1="{n(x0 + pad)}" y1="{n(fy - 3)}" x2="{n(x1 - pad)}" y2="{n(fy - 3)}" stroke="#55524c" stroke-width="0.2"/>')
    cols = [('SKALA', '1:50 @ A3'), ('TARIKH', 'OKT 2026'), ('NO. LUKISAN', 'A-101')]
    cw = (TB_W - 2 * pad) / 3
    for i, (a, b) in enumerate(cols):
        xx = x0 + pad + i * cw
        o.append(tb_text(xx, fy + 1, a, 1.4, 600, '#9d978c', ls=0.5))
        o.append(tb_text(xx, fy + 6.2, b, 2.6, 700, '#ffffff'))
    return ''.join(o)


def sheet_frame():
    return (f'<rect x="{n(FRAME)}" y="{n(FRAME)}" width="{n(SHEET_W - 2 * FRAME)}" '
            f'height="{n(SHEET_H - 2 * FRAME)}" fill="none" stroke="{INK}" stroke-width="0.6"/>'
            f'<rect x="{n(FRAME - 2.2)}" y="{n(FRAME - 2.2)}" width="{n(SHEET_W - 2 * FRAME + 4.4)}" '
            f'height="{n(SHEET_H - 2 * FRAME + 4.4)}" fill="none" stroke="{INK}" stroke-width="0.15"/>')


# ============================================================== HIMPUN
def build():
    ao, wall_g = walls()
    clip = (f'<clipPath id="cDraw"><rect x="{n(DRAW_X0)}" y="{n(DRAW_Y0)}" '
            f'width="{n(DRAW_X1 - DRAW_X0)}" height="{n(DRAW_Y1 - DRAW_Y0)}"/></clipPath>')
    body = [
        f'<rect width="{SHEET_W}" height="{SHEET_H}" fill="#ffffff"/>',
        defs(), clip,
        '<g clip-path="url(#cDraw)">',
        site(),
        floors(), wood_floor(), planter(), thresholds(),
        rug(25.0, 32.5, 3.0, 9.6, '#c9cdb8', '#8f977c', '#a4ab92'),
        rug(23.75, 31.75, 20.6, 25.75, '#d8c7b2', '#a88d70', '#bca78f'),
        stair(),
        '<g filter="url(#fShFurn)">',
        wardrobe(), bedroom_rest(), bed(), sofa(), living_rest(), dining(), hall_cabinet(),
        kitchen(), bathroom(),
        '</g>',
        ao,
        low_walls(),
        wall_g,
        windows(), doors(),
        plants(),
        labels(), dims(),
        '</g>',
        title_block(), sheet_frame(),
    ]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{SHEET_W}mm" height="{SHEET_H}mm" '
           f'viewBox="0 0 {SHEET_W} {SHEET_H}">' + ''.join(body) + '</svg>')
    return svg


if __name__ == '__main__':
    svg = build()
    base = os.path.join(OUT, 'Pelan_Lantai_Bawah_A3')
    with open(base + '.svg', 'w', encoding='utf-8') as fh:
        fh.write(svg)
    html = ('<!doctype html><html><head><meta charset="utf-8"><title>Pelan Lantai Bawah</title>'
            '<style>@page{size:420mm 297mm;margin:0}html,body{margin:0;padding:0;background:#fff}'
            'svg{display:block}</style></head><body>' + svg + '</body></html>')
    with open(os.path.join(HERE, 'pelan.html'), 'w', encoding='utf-8') as fh:
        fh.write(html)
    print('ok', len(svg))
