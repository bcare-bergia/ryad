#!/usr/bin/env python3
"""ryad: an isometric riad on an island at sunset, rendered as coloured ASCII.

The riad is modelled in 3D (signed distance fields), ray-marched from a
2:1 dimetric camera like the isometric games of the 80s and 90s, and turned
into text: each character cell is sampled 2x4 times; cells inside one surface
get that surface's texture glyph (zellige, plaster, water, leaves...), cells
on an edge get the ASCII glyph whose shape best matches the edge (/ \\ | _ .).

Writes, next to this script:
  riad.txt  plain ASCII
  riad.ans  24-bit ANSI colour (cat riad.ans in a terminal >= 220 columns)
  riad-render.png  the 3D render the characters are sampled from
                   (one pixel per sample, 440x376; needs Pillow)
  riad.svg  coloured, for the GitHub README:
            <p align="center"><img src="art/riad.svg" alt="ryad"></p>
Run: python3 art/riad.py   (needs numpy; about ten seconds)
"""
import os
import sys
from html import escape

import numpy as np

# ------------------------------------------------------------------ canvas
W, H = 220, 94              # characters
SX, SY = 2, 4               # samples per character
CW = 0.21                   # world units per character column (rows are 2x)
CENTER_ROW = 58             # screen row the world origin projects to
HORIZON = 30                # screen row of the sea horizon
SEA_Z = -3.0

EL = np.arctan(0.5)        # 2:1 dimetric, the classic pixel-art isometric
F = np.array([np.cos(EL) / np.sqrt(2), np.cos(EL) / np.sqrt(2), -np.sin(EL)])
R = np.array([1.0, -1.0, 0.0]) / np.sqrt(2)
U = np.cross(R, F)
SUN = np.array([-0.72, -0.3, 0.62]); SUN /= np.linalg.norm(SUN)

# ------------------------------------------------------------------ materials
(ISLAND, WALL, ROOF, GOLD, LANTERN, WATER, BASIN, BED, LEAF, TRUNK, FROND,
 CYPRESS, WOOD, SAIL) = range(14)
SMOOTH = {LEAF, TRUNK, FROND, CYPRESS, GOLD, WATER, SAIL, LANTERN}

# ------------------------------------------------------------------ sdf kit
def length3(x, y, z):
    return np.sqrt(x * x + y * y + z * z)

def box2(qx, qy):
    return (np.hypot(np.maximum(qx, 0), np.maximum(qy, 0))
            + np.minimum(np.maximum(qx, qy), 0))

def box(x, y, z, cx, cy, cz, hx, hy, hz):
    qx, qy, qz = np.abs(x - cx) - hx, np.abs(y - cy) - hy, np.abs(z - cz) - hz
    return (length3(np.maximum(qx, 0), np.maximum(qy, 0), np.maximum(qz, 0))
            + np.minimum(np.maximum(np.maximum(qx, qy), qz), 0))

def aabb(x, y, z, x0, x1, y0, y1, z0, z1):
    return box(x, y, z, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2,
               (x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2)

def cyl(x, y, z, cx, cy, r, z0, z1):
    return box2(np.hypot(x - cx, y - cy) - r, np.abs(z - (z0 + z1) / 2) - (z1 - z0) / 2)

def sphere(x, y, z, cx, cy, cz, r):
    return length3(x - cx, y - cy, z - cz) - r

def ellipsoid(x, y, z, cx, cy, cz, rx, ry, rz):
    px, py, pz = (x - cx), (y - cy), (z - cz)
    k0 = length3(px / rx, py / ry, pz / rz)
    k1 = length3(px / rx / rx, py / ry / ry, pz / rz / rz)
    return k0 * (k0 - 1) / np.maximum(k1, 1e-6)

def capsule(x, y, z, a, b, r):
    pax, pay, paz = x - a[0], y - a[1], z - a[2]
    bax, bay, baz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    h = np.clip((pax * bax + pay * bay + paz * baz) / (bax * bax + bay * bay + baz * baz), 0, 1)
    return length3(pax - bax * h, pay - bay * h, paz - baz * h) - r

def pyramid(x, y, z, cx, cy, z0, half, height):
    m = np.maximum(np.abs(x - cx), np.abs(y - cy))
    k = height / half
    slant = (m * k + (z - z0) - height) / np.sqrt(1 + k * k)
    return np.maximum(z0 - z, slant)

def horseshoe(q, z, z0, zc, r, jamb):
    """2D horseshoe arch opening: a circle wider than the jambs below it."""
    circ = np.hypot(q, z - zc) - r
    rect = box2(np.abs(q) - jamb, np.abs(z - (z0 + zc) / 2) - (zc - z0) / 2)
    return np.minimum(circ, rect)

def rep(u, u0, s, n):
    """Repeat a shape n times every s along u, starting at u0."""
    return u - (u0 + np.clip(np.round((u - u0) / s), 0, n - 1) * s)

def hash3(x, y, z):
    v = np.sin(x * 12.9898 + y * 78.233 + z * 37.719) * 43758.5453
    return v - np.floor(v)

# ------------------------------------------------------------------ the riad
C0 = -1.5                   # courtyard centre (x = y = C0)
ARC_U0, ARC_S, ARC_N = -8.5, 4.5, 4
G_ZC, G_R, G_J = 2.9, 1.45, 1.1          # ground arcade: arch centre, radius, jamb
U_Z0, U_ZC, U_R, U_J = 5.5, 6.5, 0.85, 0.62    # upper windows
WING_H = 8.0
FRIEZE = (4.55, 5.0)
TOWER_H = 13.5

def wing(a, b, z):
    """A two-storey wing whose courtyard face is at a = 8 (a across, b along)."""
    d = box(a, b, z, 10, 0, WING_H / 2, 2, 12, WING_H / 2)
    q = rep(b, ARC_U0, ARC_S, ARC_N)
    g = np.maximum(horseshoe(q, z, -1, G_ZC, G_R, G_J), np.abs(a - 8.45) - 1.45)
    u = np.maximum(horseshoe(q, z, U_Z0, U_ZC, U_R, U_J), np.abs(a - 7.9) - 0.45)
    d = np.maximum(d, -np.minimum(g, u))
    # a plain parapet along the courtyard edge of the roof terrace
    return np.minimum(d, box(a, b, z, 8.2, -2.2, WING_H + 0.18, 0.2, 9.8, 0.18))

def lanterns(a, b, z):
    q = rep(b, ARC_U0, ARC_S, ARC_N)
    return np.minimum(box(a, q, z, 9.1, 0, 3.25, 0.22, 0.22, 0.32),
                      capsule(a, q, z, (9.1, 0, 3.5), (9.1, 0, G_ZC + G_R), 0.04))

def merlons(u, v, z, vfix, u0, u1, ztop, s=1.0):
    n = int(round((u1 - u0) / s)) + 1
    q = rep(u, u0, s, n)
    return box(q, v, z, 0, vfix, ztop + 0.35, 0.33, 0.3, 0.35)

def walls(x, y, z):
    d = np.minimum(wing(x, y, z), wing(y, x, z))
    # crenellated parapets on both wings, courtyard side and outer side
    for a, b in ((x, y), (y, x)):
        d = np.minimum(d, merlons(b, a, z, 11.7, -11.7, 7.3, WING_H, 1.3))
        d = np.minimum(d, merlons(a, b, z, -11.7, 8.3, 11.7, WING_H, 1.3))
    # corner tower
    t = box(x, y, z, 10, 10, TOWER_H / 2, 2.4, 2.4, TOWER_H / 2)
    w1 = np.maximum(horseshoe(y - 10, z, 9.4, 10.6, 0.72, 0.54), np.abs(x - 7.6) - 0.35)
    w2 = np.maximum(horseshoe(x - 10, z, 9.4, 10.6, 0.72, 0.54), np.abs(y - 7.6) - 0.35)
    t = np.maximum(t, -np.minimum(w1, w2))
    t = np.minimum(t, merlons(y, x, z, 7.85, 7.85, 12.15, TOWER_H, 1.08))
    t = np.minimum(t, merlons(x, y, z, 7.85, 7.85, 12.15, TOWER_H, 1.08))
    d = np.minimum(d, t)
    # low front walls, cut away so we can look in; a gate in the right one
    fw = np.minimum(aabb(x, y, z, -12, -11, -12, 8, 0, 1.3),
                    aabb(x, y, z, -12, 8, -12, -11, 0, 1.3))
    fw = np.maximum(fw, -aabb(x, y, z, 1.0, 4.0, -13, -10, -1, 3))
    fw = np.minimum(fw, merlons(y, x, z, -11.5, -10.5, 7.5, 1.3, 1.5))
    fw = np.minimum(fw, merlons(x, y, z, -11.5, -10.5, -0.5, 1.3, 1.5))
    fw = np.minimum(fw, merlons(x, y, z, -11.5, 5.5, 7.5, 1.3, 1.5))
    d = np.minimum(d, fw)
    # gate posts and corner turret
    for gx in (0.7, 4.3):
        d = np.minimum(d, aabb(x, y, z, gx - 0.4, gx + 0.4, -12.2, -10.8, 0, 2.4))
    d = np.minimum(d, cyl(x, y, z, -11.5, -11.5, 1.0, 0, 2.6))
    return d

def roofs(x, y, z):
    d = pyramid(x, y, z, 10, 10, TOWER_H, 2.2, 2.8)
    dome = np.maximum(sphere(x, y, z, -11.5, -11.5, 2.6, 0.95), 2.6 - z)
    return np.minimum(d, dome)

def gold(x, y, z):
    top = TOWER_H + 2.8
    d = capsule(x, y, z, (10, 10, top - 0.4), (10, 10, top + 1.6), 0.06)
    for zz, r in ((top + 0.35, 0.27), (top + 0.85, 0.22), (top + 1.25, 0.15)):
        d = np.minimum(d, sphere(x, y, z, 10, 10, zz, r))
    d = np.minimum(d, sphere(x, y, z, -11.5, -11.5, 3.75, 0.18))
    for gx in (0.7, 4.3):
        d = np.minimum(d, sphere(x, y, z, gx, -11.5, 2.65, 0.25))
    return d

def island(x, y, z):
    half = 14.6 + np.maximum(-z, 0) * 0.3
    r = 3.2
    qx, qy = np.abs(x) - half + r, np.abs(y) - half + r
    d2 = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r
    d2 = d2 + 0.12 * np.sin(x * 1.3 + z * 2.1) * np.sin(y * 1.1 - z * 1.7) * np.clip(-z, 0, 1)
    d = np.maximum(d2 * 0.8, np.maximum(z, -(z + 6)))
    # water channels cut into the courtyard floor
    ch = np.minimum(aabb(x, y, z, C0 - 0.6, C0 + 0.6, -11, 8, -0.35, 1),
                    aabb(x, y, z, -11, 8, C0 - 0.6, C0 + 0.6, -0.35, 1))
    d = np.maximum(d, -ch)
    # steps down the cliff from the gate to the jetty
    for k in range(6):
        d = np.minimum(d, aabb(x, y, z, 1.4, 3.6, -15.0 - 0.6 * (k + 1), -14.0, -3.4, -0.5 * (k + 1)))
    return d

def water(x, y, z):
    d = np.minimum(aabb(x, y, z, C0 - 0.6, C0 + 0.6, -11, 8, -0.4, -0.12),
                   aabb(x, y, z, -11, 8, C0 - 0.6, C0 + 0.6, -0.4, -0.12))
    d = np.minimum(d, cyl(x, y, z, C0, C0, 2.45, 0, 0.5))
    d = np.minimum(d, cyl(x, y, z, C0, C0, 0.8, 1.6, 1.75))
    d = np.minimum(d, capsule(x, y, z, (C0, C0, 1.7), (C0, C0, 2.45), 0.1))
    return d

def basin(x, y, z):
    d = cyl(x, y, z, C0, C0, 2.8, 0, 0.7)
    d = np.maximum(d, -cyl(x, y, z, C0, C0, 2.45, 0.45, 2))
    d = np.minimum(d, cyl(x, y, z, C0, C0, 0.3, 0, 1.6))
    bowl = np.maximum(cyl(x, y, z, C0, C0, 0.95, 1.5, 1.82), -cyl(x, y, z, C0, C0, 0.8, 1.7, 3))
    return np.minimum(d, bowl)

BEDS = [(C0 + 1.5, 6.2), (-9.4, C0 - 1.5)]
def beds(x, y, z):
    d = None
    for x0, x1 in BEDS:
        for y0, y1 in BEDS:
            b = aabb(x, y, z, x0, x1, y0, y1, 0, 0.32)
            d = b if d is None else np.minimum(d, b)
    return np.maximum(d, -cyl(x, y, z, C0, C0, 3.5, -1, 1))

POTS = [(7.0, u) for u in (-6.25, -1.75, 2.75)] + [(u, 7.0) for u in (-6.25, -1.75, 2.75)]
ORANGES = [(2.9, 2.9), (-6.2, 2.6), (2.6, -6.2), (-6.0, -6.0)]
CYPRESSES = [(-13.4, 2.0, 2.4), (-13.4, 5.5, 2.0), (2.0, -13.4, 2.4), (5.5, -13.4, 2.0)]

def palm(base, height, lean, n, seed, length=3.2):
    """Trunk and frond capsules for one palm."""
    rng = np.random.default_rng(seed)
    bx, by, bz = base
    lx, ly = lean
    pts = [(bx + lx * np.sin(t * np.pi / 2) * t, by + ly * np.sin(t * np.pi / 2) * t, bz + height * t)
           for t in np.linspace(0, 1, 5)]
    trunk = [(pts[i], pts[i + 1], 0.26 - 0.03 * i) for i in range(4)]
    top = pts[-1]
    fronds = []
    for i in range(n):
        a = 2 * np.pi * i / n + rng.uniform(-0.25, 0.25)
        L = length * rng.uniform(0.85, 1.1)
        rise = rng.uniform(0.3, 0.8)
        prev = top
        for s in np.linspace(0.25, 1, 4):
            p = (top[0] + np.cos(a) * L * s, top[1] + np.sin(a) * L * s,
                 top[2] + rise * s - 2.2 * s * s)
            fronds.append((prev, p, 0.16 * (1.15 - s * 0.6)))
            prev = p
    nuts = [(top[0] + 0.3 * np.cos(a), top[1] + 0.3 * np.sin(a), top[2] - 0.35)
            for a in (0.4, 2.5, 4.4)]
    return trunk, fronds, nuts, top

PALMS = [palm((-13.4, 11.0, 0), 9.0, (-0.8, 0.5), 11, 1),
         palm((11.0, -13.4, 0), 8.4, (0.6, -0.9), 10, 2),
         palm((-13.3, -7.5, 0), 7.0, (-1.2, 0.2), 10, 3),
         palm((-7.0, -13.3, 0), 8.2, (0.2, -1.0), 10, 4),
         palm((12.6, -12.4, 0), 6.5, (0.8, -0.8), 9, 5)]

def palms(x, y, z):
    tr = fr = None
    for trunk, fronds, nuts, top in PALMS:
        for a, b, r in trunk:
            d = capsule(x, y, z, a, b, r)
            tr = d if tr is None else np.minimum(tr, d)
        bound = sphere(x, y, z, top[0], top[1], top[2] - 0.8, 4.2)
        near = bound < 0.5
        f = bound.copy()
        if near.any():
            sx, sy, sz = x[near], y[near], z[near]
            fd = np.full(sx.shape, 1e9)
            for a, b, r in fronds:
                fd = np.minimum(fd, capsule(sx, sy, sz, a, b, r))
            for n in nuts:
                fd = np.minimum(fd, sphere(sx, sy, sz, *n, 0.17))
            f[near] = fd
        fr = f if fr is None else np.minimum(fr, f)
    return tr, fr

def trees(x, y, z):
    leaf = trunk = cyp = None
    for tx, ty in ORANGES:
        l = sphere(x, y, z, tx, ty, 2.35, 1.35) + 0.12 * np.sin(x * 3.1) * np.sin(y * 2.9) * np.sin(z * 3.3)
        t = cyl(x, y, z, tx, ty, 0.16, 0.3, 1.4)
        leaf = l if leaf is None else np.minimum(leaf, l)
        trunk = t if trunk is None else np.minimum(trunk, t)
    for px, py in POTS:
        trunk = np.minimum(trunk, cyl(x, y, z, px, py, 0.32, 0, 0.55))
        leaf = np.minimum(leaf, sphere(x, y, z, px, py, 1.05, 0.5))
    for cx, cy, h in CYPRESSES:
        c = ellipsoid(x, y, z, cx, cy, h + 0.5, 0.7, 0.7, h)
        cyp = c if cyp is None else np.minimum(cyp, c)
        trunk = np.minimum(trunk, cyl(x, y, z, cx, cy, 0.12, 0, 0.8))
    return leaf, trunk, cyp

def tri2(px, py, a, b, c):
    """2D signed distance to a triangle (Inigo Quilez)."""
    def seg(p0, p1):
        ex, ey = p1[0] - p0[0], p1[1] - p0[1]
        wx, wy = px - p0[0], py - p0[1]
        h = np.clip((wx * ex + wy * ey) / (ex * ex + ey * ey), 0, 1)
        dx, dy = wx - ex * h, wy - ey * h
        return dx * dx + dy * dy, ex * wy - ey * wx
    d0, s0 = seg(a, b); d1, s1 = seg(b, c); d2, s2 = seg(c, a)
    d = np.minimum(np.minimum(d0, d1), d2)
    inside = ((s0 > 0) & (s1 > 0) & (s2 > 0)) | ((s0 < 0) & (s1 < 0) & (s2 < 0))
    return np.where(inside, -1, 1) * np.sqrt(d)

BOAT = (7.6, -18.6)
def boat(x, y, z):
    bx, by = BOAT
    hull = np.maximum(ellipsoid(x, y, z, bx, by, SEA_Z + 0.35, 3.0, 0.95, 0.75), z - (SEA_Z + 0.45))
    hull = np.maximum(hull, -ellipsoid(x, y, z, bx, by, SEA_Z + 0.5, 2.7, 0.75, 0.55))
    dock = aabb(x, y, z, 0.8, 4.2, -20.2, -16.5, SEA_Z - 0.4, SEA_Z + 0.35)
    for px in (0.8, 4.2):
        for py in (-20.0, -17.4):
            dock = np.minimum(dock, cyl(x, y, z, px, py, 0.16, SEA_Z - 1, SEA_Z + 0.75))
    wood = np.minimum(hull, dock)
    mast = capsule(x, y, z, (bx - 0.3, by, SEA_Z + 0.3), (bx - 0.6, by, SEA_Z + 5.4), 0.08)
    sail = np.maximum(tri2(x, z, (bx - 2.6, SEA_Z + 1.4), (bx + 2.9, SEA_Z + 1.9), (bx - 1.6, SEA_Z + 6.6)),
                      np.abs(y - by - 0.15) - 0.05)
    return wood, mast, sail

def scene(x, y, z, with_mat=False):
    tr, fr = palms(x, y, z)
    leaf, trunk, cyp = trees(x, y, z)
    wood, mast, sail = boat(x, y, z)
    parts = [
        island(x, y, z), walls(x, y, z), roofs(x, y, z), gold(x, y, z),
        np.minimum(lanterns(x, y, z), lanterns(y, x, z)),
        water(x, y, z), basin(x, y, z), beds(x, y, z), leaf,
        np.minimum(np.minimum(trunk, tr), mast), fr, cyp, wood, sail,
    ]
    d = np.stack(parts)
    if with_mat:
        return d.min(0), d.argmin(0)
    return d.min(0)

# ------------------------------------------------------------------ marching
def march(ox, oy, oz, dx, dy, dz, tmin, tmax, steps=220, eps=0.004):
    n = ox.size
    t = tmin.copy()
    hit = np.zeros(n, bool)
    live = np.nonzero(t < tmax)[0]
    for _ in range(steps):
        if live.size == 0:
            break
        tl = t[live]
        d = scene(ox[live] + dx * tl if np.isscalar(dx) else ox[live] + dx[live] * tl,
                  oy[live] + dy * tl if np.isscalar(dy) else oy[live] + dy[live] * tl,
                  oz[live] + dz * tl if np.isscalar(dz) else oz[live] + dz[live] * tl)
        h = d < eps * (1 + tl * 0.02)
        hit[live[h]] = True
        t[live] = tl + np.maximum(d, eps) * 0.9
        keep = ~h & (t[live] < tmax[live])
        live = live[keep]
    return hit, t

def normals(px, py, pz):
    e = 0.01
    nx = scene(px + e, py, pz) - scene(px - e, py, pz)
    ny = scene(px, py + e, pz) - scene(px, py - e, pz)
    nz = scene(px, py, pz + e) - scene(px, py, pz - e)
    l = np.maximum(length3(nx, ny, nz), 1e-9)
    return nx / l, ny / l, nz / l

# ------------------------------------------------------------------ palette
def rgb(h):
    return np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)])

P = {k: rgb(v) for k, v in dict(
    rose='#d27a52', plaster='#efcf9c', terrace='#e8b98a', sand='#e6c58e', rock='#a8664a',
    rock2='#9c5d43', rock3='#b0704f', cobalt='#2f5fd0', turq='#2bb8b0', emerald='#1f9a6a',
    white='#f5ecd8', black='#2a2238', gold='#f2c14e', red='#c23b2b', wood='#7a4424',
    glow='#ffb347', water='#3cc6c8', grass='#4f8a34', leaf='#3f8a3a', orange='#ff8c1a',
    cypress='#24603f', frond='#5aa040', trunk='#8a5a3a', roof='#1e8f6a', marble='#f2e8dc',
    sail='#f6e7c8', shadow='#5a3a56', pink='#e85a8a').items()}

def pick(cond_colors, default):
    """Vectorised select over (cond, rgb) pairs."""
    out = np.broadcast_to(default, cond_colors[0][0].shape + (3,)).copy() if cond_colors else None
    for cond, col in cond_colors:
        out[cond] = col
    return out

def texture(m, x, y, z, nx, ny, nz):
    """Surface colour and glyph per sample. Returns base rgb (N,3), ink rgb (N,3), glyph (N,) str."""
    n = x.size
    base = np.zeros((n, 3)); ink = np.zeros((n, 3)); gly = np.full(n, ' ', dtype='<U1')
    hsh = hash3(np.floor(x * 3), np.floor(y * 3), np.floor(z * 3))
    top = nz > 0.6

    def setm(mask, b, i, g):
        base[mask] = b; ink[mask] = i; gly[mask] = g

    # --- island: zellige courtyard, sand terrace, rock strata on the cliffs
    isl = m == ISLAND
    court = isl & top & (x > -11) & (x < 8) & (y > -11) & (y < 8)
    terr = isl & top & ~court
    rock = isl & ~top
    tx, ty = np.floor(x), np.floor(y)
    fx, fy = x - tx, y - ty
    grout = np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy)) < 0.1
    chk = ((tx + ty) % 2 == 0)
    centre = np.hypot(fx - 0.5, fy - 0.5) < 0.28
    setm(court & chk, P['cobalt'], P['white'], ':')
    setm(court & ~chk, P['white'], P['emerald'], '+')
    setm(court & centre & chk, P['cobalt'], P['gold'], '*')
    setm(court & centre & ~chk, P['white'], P['cobalt'], 'o')
    setm(court & grout, P['white'] * 0.85, P['white'], '.')
    setm(terr, P['sand'], P['sand'] * 0.7, '.')
    setm(terr & (hsh < 0.25), P['sand'], P['sand'] * 0.65, ':')
    setm(terr & (hsh > 0.93), P['sand'], P['grass'], ',')
    band = np.floor(z * 1.7 + 0.5 * np.sin(x * 0.6 + y * 0.4)).astype(int) % 3
    for k, (c, g) in enumerate(((P['rock'], '%'), (P['rock2'], '#'), (P['rock3'], ':'))):
        setm(rock & (band == k), c, c * 0.62, g)
    setm(rock & (hsh < 0.18), P['rock'], P['rock3'] * 1.15, '.')

    # --- walls: rose ochre outside; plaster, zellige and cedar on the courtyard faces
    wl = m == WALL
    in_a = (x > 7.5) & (y < 7.6)                 # right wing, courtyard face
    in_b = (y > 7.5) & (x < 7.6)                 # back wing
    face = wl & ((in_a & (nx < -0.5)) | (in_b & (ny < -0.5)))
    u = np.where(in_a, y, x)
    depth = np.where(in_a, x, y)
    q = rep(u, ARC_U0, ARC_S, ARC_N)
    gd = horseshoe(q, z, -1, G_ZC, G_R, G_J)
    ud = horseshoe(q, z, U_Z0, U_ZC, U_R, U_J)
    inside = wl & (in_a | in_b) & (depth > 8.1) & (depth < 10.0) & ((gd < 0.03) | (ud < 0.03)) & (z < WING_H)
    out = wl & ~face & ~inside
    setm(out, P['rose'], P['rose'] * 0.7, ' ')
    setm(out & ~top & (((z * 2.4) % 1) < 0.2), P['rose'], P['rose'] * 0.7, '_')
    setm(out & ~top & (hsh < 0.05), P['rose'], P['rose'] * 0.7, '.')
    setm(out & top, P['terrace'], P['terrace'] * 0.75, '=')
    ou = np.where(np.abs(nx) > np.abs(ny), y, x)
    win = out & ~top & (((ou + 0.5) % 3.0) < 0.7) & (z > 5.6) & (z < 6.8) & (np.maximum(x, y) < 12.5)
    setm(win, P['wood'], P['glow'], '#')
    fc = face | inside
    setm(fc, P['plaster'], P['plaster'] * 0.75, ' ')
    setm(fc & (hsh < 0.04), P['plaster'], P['plaster'] * 0.75, '.')
    setm(inside & (depth > 8.6), P['shadow'], P['shadow'] * 1.5, ' ')
    setm(inside & (depth > 9.7) & (hsh < 0.3), P['shadow'], P['glow'] * 0.6, '.')
    dado = fc & (z < 1.1)
    dd = (np.floor(u * 2.2) + np.floor(z * 2.2)) % 2 == 0
    dcol = np.floor(u * 1.1) % 3
    for k, c in enumerate((P['cobalt'], P['emerald'], P['black'])):
        setm(dado & dd & (dcol == k), P['white'], c, '/')
        setm(dado & ~dd & (dcol == k), c, P['white'], '\\')
    frz = face & (z > FRIEZE[0]) & (z < FRIEZE[1])
    fk = np.floor(u * 1.6) % 4
    for k, (b, i, g) in enumerate(((P['cobalt'], P['gold'], '*'), (P['white'], P['emerald'], 'o'),
                                   (P['emerald'], P['white'], '+'), (P['white'], P['cobalt'], 'o'))):
        setm(frz & (fk == k), b, i, g)
    corn = face & (z > WING_H - 0.45) & (z < WING_H)
    setm(corn, P['wood'], P['gold'], '=')
    # arch voussoirs: alternating red and ivory around each horseshoe
    vous = face & (gd > 0) & (gd < 0.42) & (z > G_ZC - 0.5)
    ang = np.floor((np.arctan2(z - G_ZC, q) + 1) * 3.2) % 2 == 0
    setm(vous & ang, P['red'], P['white'], '=')
    setm(vous & ~ang, P['white'], P['red'], '=')
    uvous = face & (ud > 0) & (ud < 0.28) & (z > U_ZC - 0.3)
    setm(uvous, P['cobalt'], P['turq'], '-')
    # mashrabiya screens in the upper windows, lit from inside
    mash = wl & (depth > 8.25) & (depth < 8.5) & (z > U_Z0 - 0.1) & (z < WING_H) & (ud < 0.01)
    lat = (np.floor(q * 5) + np.floor(z * 5)) % 2 == 0
    setm(mash & lat, P['wood'], P['glow'], '#')
    setm(mash & ~lat, P['glow'] * 0.9, P['wood'], '+')
    # tower windows glow
    tw = wl & (x > 7.5) & (y > 7.5) & (z > 9.3) & (z < 11.4) & ((x > 7.8) & (y > 7.8)) & (np.minimum(x, y) < 8.0)
    setm(tw, P['glow'], P['gold'], '#')
    setm(wl & (x > 7.6) & (y > 7.6) & (z > 12.2) & (z < 12.75) & ~top & (np.minimum(x, y) < 7.7), P['cobalt'], P['white'], 'x')

    setm(m == ROOF, P['roof'], P['roof'] * 1.5, '^')
    setm((m == ROOF) & (((z * 3) % 1) < 0.3), P['roof'] * 0.75, P['turq'], '_')
    setm(m == GOLD, P['gold'], P['white'], 'o')
    setm(m == LANTERN, P['glow'], P['white'], '*')
    wv = np.sin(x * 2.7 + y * 1.9) + np.sin(np.hypot(x - C0, y - C0) * 5)
    setm(m == WATER, P['water'], P['white'], '~')
    setm((m == WATER) & (wv < 0), P['water'], P['turq'] * 0.7, '-')
    setm(m == BASIN, P['marble'], P['cobalt'], ':')
    setm((m == BASIN) & ~top & (z > 0.15) & (z < 0.55), P['cobalt'], P['white'], '<')
    setm((m == BASIN) & ~top & (z > 0.15) & (z < 0.55) & (hsh > 0.5), P['cobalt'], P['white'], '>')
    bd = m == BED
    setm(bd, P['grass'], P['grass'] * 1.5, ',')
    setm(bd & (hsh > 0.5), P['grass'], P['grass'] * 1.6, "'")
    setm(bd & (hsh > 0.85), P['grass'], P['pink'], '*')
    setm(bd & (hsh > 0.93), P['grass'], P['gold'], '*')
    setm(bd & ~top, P['cypress'], P['grass'], '#')
    lf = m == LEAF
    setm(lf, P['leaf'], P['leaf'] * 1.5, '&')
    setm(lf & (hsh > 0.55), P['leaf'], P['leaf'] * 1.6, '%')
    setm(lf & (hsh > 0.86), P['leaf'], P['orange'], 'o')
    setm(m == TRUNK, P['trunk'], P['trunk'] * 0.6, '|')
    setm((m == TRUNK) & (((z * 3) % 1) < 0.35), P['trunk'], P['trunk'] * 1.4, '=')
    setm(m == FROND, P['frond'], P['frond'] * 1.5, '~')
    setm(m == CYPRESS, P['cypress'], P['cypress'] * 1.8, '%')
    setm((m == CYPRESS) & (hsh > 0.6), P['cypress'], P['cypress'] * 1.6, '(')
    setm(m == WOOD, P['wood'], P['wood'] * 1.5, '=')
    setm(m == SAIL, P['sail'], P['sail'] * 0.8, ' ')
    setm((m == SAIL) & (((z * 2) % 1) < 0.15), P['sail'], P['sail'] * 0.75, '-')
    return base, ink, gly

EMISSIVE = {LANTERN: 1.0, GOLD: 0.25, SAIL: 0.35}

# ------------------------------------------------------------------ sky & sea (screen space)
def lerp(a, b, t):
    return a + (b - a) * np.clip(t, 0, 1)[..., None]

SKY = [rgb(c) for c in ('#140c33', '#2b1650', '#5a2463', '#9a3a6c', '#d65a5a', '#f28a4a', '#ffbe63')]
SUN_COL, SUN_R = 34, 8.0        # sun centre column, radius in rows
MOON = (196, 7, 3.4)

def sky_cell(r, c):
    """Background colour and glyph for one cell above the horizon."""
    t = r / HORIZON
    k = min(int(t * (len(SKY) - 1) * 1.0 + 0.0), len(SKY) - 2)
    # stepped bands, like a palette-limited sky
    col = SKY[min(int(t ** 0.8 * len(SKY)), len(SKY) - 1)].copy()
    g, ink = ' ', None
    h = hash3(np.array(r * 1.0), np.array(c * 1.0), np.array(3.0))
    if t < 0.55 and h > 0.965:
        g, ink = ('.' if h < 0.99 else '*'), rgb('#fff1c8')
    if t < 0.4 and h > 0.995:
        g, ink = '+', rgb('#ffffff')
    # sun: a setting disc with the retro stripes
    dr, dc = (r - HORIZON) / SUN_R, (c - SUN_COL) / (2 * SUN_R)
    if dr * dr + dc * dc < 1:
        stripe = (r > HORIZON - 4) and (r % 2 == 1)
        col = lerp(rgb('#ffe27a'), rgb('#ff6a3d'), np.array((r - (HORIZON - SUN_R)) / SUN_R))
        if stripe:
            col = SKY[-2]
        g, ink = ' ', None
    elif dr * dr + dc * dc < 1.6:
        col = lerp(col, rgb('#ffd27a'), np.array(0.35))
    # crescent moon
    mc, mr, mrad = MOON
    d1 = ((r - mr) / mrad) ** 2 + ((c - mc) / (2 * mrad)) ** 2
    d2 = ((r - mr + 0.8) / mrad) ** 2 + ((c - mc - 2.8) / (2 * mrad)) ** 2
    if d1 < 1 and d2 > 1:
        col, g, ink = rgb('#fff3d6'), ' ', None
    # long thin clouds lit from below
    cl = np.sin(c * 0.07 + r * 1.3) + np.sin(c * 0.023 - r * 0.6)
    if HORIZON - 9 < r < HORIZON - 2 and cl > 1.35:
        col = lerp(col, rgb('#ff9f7a'), np.array(0.5))
        g, ink = '~', rgb('#ffd0a0')
    # distant islands of the caliph on the horizon
    hgt = island_profile(c)
    if HORIZON - r <= hgt and r <= HORIZON:
        col = rgb('#4a2457')
        g, ink = (' ', None)
        if HORIZON - r > hgt - 1:
            g, ink = '_' if hgt < 1.5 else '^', rgb('#7a3a70')
    # seagulls
    if (r, c) in BIRDS:
        g, ink = 'v', rgb('#2a1630')
    return col, g, ink

BIRDS = {(12, 140), (11, 143), (14, 150), (13, 154), (10, 162)}

def island_profile(c):
    h = 0.0
    for cc, w, hh in ((168, 14, 2.2), (204, 9, 1.4), (74, 7, 1.2)):
        x = (c - cc) / w
        if abs(x) < 1:
            h = max(h, hh * (1 - x * x))
    # domes and minarets on the far islands
    for cc, hh in ((165, 3.2), (171, 4.6), (174, 3.0), (204, 2.6)):
        if c == cc:
            h = max(h, hh)
    for cc, w, hh in ((168, 2, 3.4),):
        if abs(c - cc) <= w:
            h = max(h, hh - 0.25 * abs(c - cc) ** 2)
    return h

def sea_cell(r, c, wx, wy):
    """Sea colour and glyph for a cell below the horizon (wx, wy: world point)."""
    t = np.clip((r - HORIZON) / 30, 0, 1)
    col = lerp(rgb('#c86a6a'), rgb('#1b3a6a'), np.array(t ** 0.6))
    col = lerp(col, rgb('#0f2148'), np.array(np.clip((r - HORIZON - 26) / 30, 0, 1)))
    g, ink = ' ', None
    wave = np.sin(wx * 0.9 + wy * 0.35) + 0.6 * np.sin(wx * 0.31 - wy * 1.1)
    if wave > 1.0:
        g, ink = '~', col * 1.6 + 0.08
    elif wave < -1.2:
        g, ink = '-', col * 1.4 + 0.05
    # glitter path under the sun
    w = 3 + (r - HORIZON) * 0.9
    if abs(c - SUN_COL) < w and hash3(np.array(r * 1.0), np.array(c * 1.0), np.array(9.0)) > 0.55:
        g, ink = ('=' if r < HORIZON + 6 else '-'), rgb('#ffd27a') * (1 - t * 0.5)
    # foam where the sea meets the cliffs
    half = 14.6 + 0.3 * 3.0
    if max(abs(wx), abs(wy)) < half + 1.2 and max(abs(wx), abs(wy)) > half - 3.5:
        g, ink = '~', rgb('#e8f4f0')
    if r == HORIZON:
        col = rgb('#ffcf80')
        g, ink = '_', rgb('#ffe7a8')
    return col, g, ink

# ------------------------------------------------------------------ glyph shapes
# 2x4 coverage templates (row-major, top to bottom) for edge cells
TEMPL = [
    ('_', [0, 0, 0, 0, 0, 0, 1, 1]), ('.', [0, 0, 0, 0, 0, 0, 1, 0]), ('.', [0, 0, 0, 0, 0, 0, 0, 1]),
    ('-', [0, 0, 1, 1, 0, 0, 0, 0]), ('-', [0, 0, 0, 0, 1, 1, 0, 0]), 
    ("'", [0, 1, 0, 0, 0, 0, 0, 0]), ('`', [1, 0, 0, 0, 0, 0, 0, 0]), ('-', [1, 1, 0, 0, 0, 0, 0, 0]),
    ('/', [0, 1, 0, 1, 1, 0, 1, 0]), ('/', [0, 0, 0, 1, 1, 0, 0, 0]), ('/', [0, 1, 1, 0, 0, 0, 0, 0]),
    ('/', [0, 0, 0, 0, 0, 1, 1, 0]),
    ('\\', [1, 0, 1, 0, 0, 1, 0, 1]), ('\\', [0, 0, 1, 0, 0, 1, 0, 0]), ('\\', [1, 0, 0, 1, 0, 0, 0, 0]),
    ('\\', [0, 0, 0, 0, 1, 0, 0, 1]),
    ('|', [1, 0, 1, 0, 1, 0, 1, 0]), ('|', [0, 1, 0, 1, 0, 1, 0, 1]), ('|', [0, 0, 1, 0, 1, 0, 0, 0]),
    ('|', [0, 0, 0, 1, 0, 1, 0, 0]),
    (',', [0, 0, 0, 0, 0, 1, 1, 1]), (',', [0, 0, 0, 0, 1, 0, 1, 1]),
]
TG = np.array([g for g, _ in TEMPL]); TM = np.array([m for _, m in TEMPL], float)

# ------------------------------------------------------------------ render
def render():
    Ws, Hs = W * SX, H * SY
    cx = ((np.arange(Ws) + 0.5) / SX - W / 2) * CW
    cy = -((np.arange(Hs) + 0.5) / SY - CENTER_ROW) * 2 * CW
    X, Y = np.meshgrid(cx, cy)
    X, Y = X.ravel(), Y.ravel()
    ox = X * R[0] + Y * U[0] - 120 * F[0]
    oy = X * R[1] + Y * U[1] - 120 * F[1]
    oz = X * R[2] + Y * U[2] - 120 * F[2]
    # clip rays to the scene's bounding box and stop them at the sea
    lo, hi = np.array([-24, -24, -7.0]), np.array([24, 24, 19.5])
    t0 = np.zeros_like(ox); t1 = np.full_like(ox, 1e9)
    for o, d, a, b in ((ox, F[0], lo[0], hi[0]), (oy, F[1], lo[1], hi[1]), (oz, F[2], lo[2], hi[2])):
        ta, tb = (a - o) / d, (b - o) / d
        t0 = np.maximum(t0, np.minimum(ta, tb)); t1 = np.minimum(t1, np.maximum(ta, tb))
    t_sea = (SEA_Z - oz) / F[2]
    t1 = np.minimum(t1, t_sea)
    hit, t = march(ox, oy, oz, F[0], F[1], F[2], t0, t1)
    hi_ = np.nonzero(hit)[0]
    px, py, pz = ox[hi_] + F[0] * t[hi_], oy[hi_] + F[1] * t[hi_], oz[hi_] + F[2] * t[hi_]
    _, mat = scene(px, py, pz, with_mat=True)
    nx, ny, nz = normals(px, py, pz)
    # shadows from the low sun
    so = 0.05
    sh, _ = march(px + nx * so, py + ny * so, pz + nz * so, SUN[0], SUN[1], SUN[2],
                  np.zeros_like(px), np.full_like(px, 45.0), steps=120, eps=0.01)
    diff = np.clip(nx * SUN[0] + ny * SUN[1] + nz * SUN[2], 0, 1) * (~sh)
    diff = np.floor(diff * 4 + 0.5) / 4                      # cel steps
    amb = np.array([0.46, 0.40, 0.58]) * (0.75 + 0.25 * nz)[:, None]
    light = amb + np.array([1.12, 0.84, 0.58]) * diff[:, None]
    base, ink, gly = texture(mat, px, py, pz, nx, ny, nz)
    em = np.zeros(mat.size)
    for k, v in EMISSIVE.items():
        em[mat == k] = v
    glow_cells = np.all(np.isclose(base, P['glow']), axis=1) | np.all(np.isclose(base, P['glow'] * 0.9), axis=1)
    em[glow_cells] = np.maximum(em[glow_cells], 0.8)
    lit_b = base * (light * (1 - em[:, None]) + em[:, None])
    lit_i = ink * (light * (1 - em[:, None]) + em[:, None])
    # face ids for edge finding: material and, for flat materials, the face
    code = np.where(nz > 0.6, 4, np.where(nz < -0.6, 5,
           np.where(np.abs(nx) > np.abs(ny), np.where(nx > 0, 0, 1), np.where(ny > 0, 2, 3))))
    smooth = np.isin(mat, list(SMOOTH))
    code = np.where(smooth, 6, code)
    code = np.where((mat == ISLAND) & (nz < 0.6), 6, code)
    fid = mat * 8 + code

    N = ox.size
    ID = np.full(N, -1); ID[hi_] = fid
    BASE = np.zeros((N, 3)); BASE[hi_] = lit_b
    INK = np.zeros((N, 3)); INK[hi_] = lit_i
    GLY = np.full(N, ' ', dtype='<U1'); GLY[hi_] = gly
    DEPTH = np.full(N, 1e9); DEPTH[hi_] = t[hi_]
    # background: the world point where each ray meets the sea, for wave texture
    sx_ = ox + F[0] * t_sea; sy_ = oy + F[1] * t_sea
    return (ID.reshape(Hs, Ws), BASE.reshape(Hs, Ws, 3), INK.reshape(Hs, Ws, 3),
            GLY.reshape(Hs, Ws), sx_.reshape(Hs, Ws), sy_.reshape(Hs, Ws))

def compose():
    ID, BASE, INK, GLY, SXW, SYW = render()
    Hs, Ws = ID.shape
    # background cells, one per character
    bg_col = np.zeros((H, W, 3)); bg_ink = np.zeros((H, W, 3)); bg_g = np.full((H, W), ' ', dtype='<U1')
    for r in range(H):
        for c in range(W):
            if r <= HORIZON:
                col, g, ink = sky_cell(r, c)
            else:
                col, g, ink = sea_cell(r, c, SXW[r * SY + 2, c * SX + 1], SYW[r * SY + 2, c * SX + 1])
            bg_col[r, c] = col; bg_g[r, c] = g
            bg_ink[r, c] = ink if ink is not None else col
    bgid = np.where(np.arange(H)[:, None] <= HORIZON, -1, -2)
    # fold background into the sample grids
    rr = np.repeat(np.arange(H), SY); cc = np.repeat(np.arange(W), SX)
    isbg = ID < 0
    ID = np.where(isbg, bgid[rr][:, [0]].repeat(Ws, 1), ID)
    BASE = np.where(isbg[..., None], bg_col[rr][:, cc], BASE)

    ids = ID.reshape(H, SY, W, SX).transpose(0, 2, 1, 3).reshape(H, W, SY * SX)
    bas = BASE.reshape(H, SY, W, SX, 3).transpose(0, 2, 1, 3, 4).reshape(H, W, SY * SX, 3)
    ink = INK.reshape(H, SY, W, SX, 3).transpose(0, 2, 1, 3, 4).reshape(H, W, SY * SX, 3)
    gly = GLY.reshape(H, SY, W, SX).transpose(0, 2, 1, 3).reshape(H, W, SY * SX)

    eq = ids[:, :, :, None] == ids[:, :, None, :]
    counts = eq.sum(3)
    pref = np.array([2, 3, 4, 5, 0, 1, 6, 7])
    score = counts * 10 + (8 - np.argsort(pref))[None, None, :] * 0
    order = np.argsort(-(counts[:, :, pref] * 10 - np.arange(8)[None, None, :]), axis=2)
    rep_i = pref[order[:, :, 0]]
    maj_id = np.take_along_axis(ids, rep_i[..., None], 2)[..., 0]
    maj = ids == maj_id[..., None]
    nmaj = maj.sum(2)

    out_g = np.full((H, W), ' ', dtype='<U1')
    out_fg = np.zeros((H, W, 3)); out_bg = np.zeros((H, W, 3))
    out_bg = (bas * maj[..., None]).sum(2) / nmaj[..., None]
    rep_g = np.take_along_axis(gly, rep_i[..., None], 2)[..., 0]
    rep_ink = np.take_along_axis(ink, rep_i[..., None, None].repeat(3, 3), 2)[:, :, 0]
    obj = maj_id >= 0
    out_g = np.where(obj, rep_g, bg_g)
    out_fg = np.where(obj[..., None], rep_ink, bg_ink)
    # edge cells: the minority shape drawn as a glyph over the majority colour
    mixed = nmaj <= SY * SX - 2
    minor = (~maj).astype(float)
    sim = (minor[:, :, None, :] == TM[None, None]).sum(3) - 0.01 * np.arange(len(TEMPL))[None, None]
    eg = TG[sim.argmax(2)]
    mcol = (bas * (~maj)[..., None]).sum(2) / np.maximum(8 - nmaj, 1)[..., None]
    out_g = np.where(mixed, eg, out_g)
    out_fg = np.where(mixed[..., None], mcol * 1.08, out_fg)
    out_bg = out_bg * 0.9
    return out_g, np.clip(out_fg, 0, 1), np.clip(out_bg, 0, 1), np.clip(BASE, 0, 1)

# ------------------------------------------------------------------ output
def quant(c):
    return tuple(int(round(v * 255 / 17) * 17) for v in c)

def write(out_g, fg, bg, here):
    lines = [''.join(r) for r in out_g]
    with open(os.path.join(here, 'riad.txt'), 'w') as f:
        f.write('\n'.join(l.rstrip() for l in lines) + '\n')
    with open(os.path.join(here, 'riad.ans'), 'w') as f:
        for r in range(H):
            cur = None; buf = []
            for c in range(W):
                k = (quant(fg[r, c]), quant(bg[r, c]))
                if k != cur:
                    buf.append('\x1b[38;2;%d;%d;%d;48;2;%d;%d;%dm' % (k[0] + k[1])); cur = k
                buf.append(out_g[r, c])
            f.write(''.join(buf) + '\x1b[0m\n')
    cw, lh = 8, 16
    w, h = W * cw, H * lh
    hexc = lambda c: '#%02x%02x%02x' % quant(c)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
         f'role="img" aria-label="ryad: an isometric riad on an island at sunset, in ASCII">',
         f'<clipPath id="c"><rect width="{w}" height="{h}" rx="16"/></clipPath><g clip-path="url(#c)">',
         '<g shape-rendering="crispEdges">']
    for r in range(H):
        c = 0
        while c < W:
            col = hexc(bg[r, c]); e = c
            while e + 1 < W and hexc(bg[r, e + 1]) == col:
                e += 1
            s.append(f'<rect x="{c * cw}" y="{r * lh}" width="{(e - c + 1) * cw}" height="{lh}" fill="{col}"/>')
            c = e + 1
    s.append('</g><g font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,\'DejaVu Sans Mono\',monospace" '
             'font-size="13.3" xml:space="preserve">')
    for r in range(H):
        spans = []; cur = None; run = ''
        for c in range(W):
            g = out_g[r, c]
            col = hexc(fg[r, c]) if g != ' ' else cur
            if col != cur and run:
                spans.append((cur, run)); run = ''
            cur = col or cur
            run += g
        spans.append((cur, run))
        body = ''.join(f'<tspan fill="{col}">{escape(t)}</tspan>' if col else escape(t) for col, t in spans)
        s.append(f'<text x="0" y="{r * lh + 12}" textLength="{W * cw}" lengthAdjust="spacingAndGlyphs">{body}</text>')
    s.append('</g></g></svg>')
    with open(os.path.join(here, 'riad.svg'), 'w') as f:
        f.write('\n'.join(s) + '\n')

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    g, fg, bg, render_px = compose()
    write(g, fg, bg, here)
    try:
        from PIL import Image
    except ImportError:
        print('Pillow not installed: skipping riad-render.png', file=sys.stderr)
    else:
        Image.fromarray((render_px * 255).round().astype(np.uint8)).save(os.path.join(here, 'riad-render.png'))
