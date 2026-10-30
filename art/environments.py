#!/usr/bin/env python3
"""ryad environments: what each environment sees, drawn as coloured ASCII.

Same look as riad.svg (8x16 character cells, the sunset palette): one image,
one container per project, and the riad wall between the containers and your
home. Only two mounts pass the wall: the project folder and the profile home.

Writes, next to this script:
  environments.svg  for the README:
                    <p align="center"><img src="art/environments.svg" alt="ryad environments"></p>
Run: python3 art/environments.py          (no dependencies)
     python3 art/environments.py --txt    print the character grid instead
"""
import os
import random
import sys
from html import escape

W, H = 158, 39              # characters
CW, LH = 8, 16              # pixels per character cell

# ------------------------------------------------------------------ palette
# from riad.py
GOLD, GLOW, PLASTER, SAND = '#f2c14e', '#ffb347', '#efcf9c', '#e6c58e'
ROSE, ROCK = '#d27a52', '#a8664a'
MUTED, NO = '#a79fb8', '#ff7a6a'
PROFILE = {'personal': '#2bb8b0', 'client_x': '#ff8c1a', 'client_y': '#e85a8a'}
PANEL, SLOT = '#2b1650', '#331d5c'
SKY = [(0, '#140c33'), (24, '#24134a'), (35, '#4a2060')]

def rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]

def hexc(c):
    return '#%02x%02x%02x' % tuple(int(round(v)) for v in c)

def mix(a, b, t):
    a, b = rgb(a), rgb(b)
    return hexc([x + (y - x) * t for x, y in zip(a, b)])

def sky(r):
    for (r0, c0), (r1, c1) in zip(SKY, SKY[1:]):
        if r <= r1:
            return mix(c0, c1, (r - r0) / (r1 - r0))
    return SKY[-1][1]

# ------------------------------------------------------------------ grid kit
G = [[' '] * W for _ in range(H)]
FG = [[None] * W for _ in range(H)]
BG = [[None] * W for _ in range(H)]
BOLD = [[False] * W for _ in range(H)]

def put(r, c, s, fg, bg=None, bold=False):
    for i, ch in enumerate(s):
        if 0 <= c + i < W:
            G[r][c + i], FG[r][c + i], BOLD[r][c + i] = ch, fg, bold
            if bg:
                BG[r][c + i] = bg

def fill(r0, c0, r1, c1, bg):
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            BG[r][c] = bg

def center(r, c, w, s, fg, bold=False):
    put(r, c + (w - len(s)) // 2, s, fg, bold=bold)

BOXES = {'single': '┌┐└┘─│', 'round': '╭╮╰╯─│', 'double': '╔╗╚╝═║'}

def box(r, c, h, w, style, fg, bg=None):
    tl, tr, bl, br, hz, vt = BOXES[style]
    if bg:
        fill(r + 1, c + 1, r + h - 2, c + w - 2, bg)
    put(r, c, tl + hz * (w - 2) + tr, fg)
    put(r + h - 1, c, bl + hz * (w - 2) + br, fg)
    for i in range(1, h - 1):
        put(r + i, c, vt, fg)
        put(r + i, c + w - 1, vt, fg)

def vline(c, r0, r1, fg):
    for r in range(r0, r1 + 1):
        put(r, c, '│', fg)

# ------------------------------------------------------------------ scene
COLS = [2, 41, 80, 119]     # environment columns, 37 wide
ENVS = [('blog', '~/perso/blog', 'personal'),
        ('x-api', '~/client_x/api', 'client_x'),
        ('x-site', '~/client_x/site', 'client_x'),
        ('y-robot', '~/client_y/robot', 'client_y')]
WALL = 21

def header():
    put(1, 2, 'ryad environments', GOLD, bold=True)
    put(2, 2, 'One image, one Podman container per project. '
              'Each container sees only two folders from your home: its project and one profile.', MUTED)
    put(1, W - 6, ')', '#fff1c8', bold=True)

def image():
    box(4, 2, 5, W - 4, 'double', GOLD, PANEL)
    put(4, 4, ' ryad image ', GOLD, bold=True)
    put(5, 5, 'one image, built once', MUTED)
    put(6, 5, '$ ryad build', PLASTER, bold=True)
    put(4, 30, '╤', GOLD); vline(30, 5, 7, GOLD); put(8, 30, '╧', GOLD)
    put(5, 33, 'AGENTS', MUTED, bold=True)
    put(5, 41, 'pi · claude · claude-desktop · antigravity', PLASTER)
    put(6, 33, 'TOOLS', MUTED, bold=True)
    put(6, 41, 'codium · emacs · rstudio · firefox · git · python · node · R', PLASTER)
    put(7, 41, '+ anything else that runs on Debian or Ubuntu', MUTED)
    for c in COLS:
        put(8, c + 18, '╤', GOLD)
        put(9, c + 18, '│', GLOW)
        put(10, c + 18, 'v', GLOW, bold=True)

def environment(c, name, prof):
    col = PROFILE[prof]
    box(11, c, 9, 37, 'round', PLASTER, '#1f1147')
    put(11, c + 2, f' {name} ', PLASTER, bold=True)
    put(11, c + 24, ' container ', MUTED)
    put(11, c + 18, '┴', GLOW)
    # project folder slot
    box(13, c + 2, 5, 16, 'single', SAND, SLOT)
    center(14, c + 3, 14, 'project folder', PLASTER, bold=True)
    center(15, c + 3, 14, 'rw · same path', MUTED)
    put(16, c + 4, '· ' * 6, mix(SAND, SLOT, 0.55))
    # home slot, tiled in the profile's colour
    box(13, c + 19, 5, 16, 'single', col, SLOT)
    center(14, c + 20, 14, 'home', PLASTER, bold=True)
    center(15, c + 20, 14, 'rw · /home/you', MUTED)
    put(16, c + 20, '▄▀' * 7, col, mix(col, SLOT, 0.7))
    # the two mounts, coming up from the host
    for x, fg, end in ((c + 10, SAND, 24), (c + 27, col, 28)):
        put(17, x, '┬', fg)
        put(18, x, '^', fg, bold=True)
        put(19, x, '┼', fg)
        vline(x, 20, end - 1, fg)

def wall():
    gates = {c + d for c in COLS for d in (10, 27)}
    for c in range(1, W - 1):
        if c in gates:      # the mount line already runs through; open a doorway
            BG[WALL + 1][c] = '#140c33'
            continue
        if c % 4 < 2:
            put(WALL, c, '▄', ROSE)
        put(WALL + 1, c, '_' if c % 6 else '|', mix(ROSE, ROCK, 0.8), ROSE)
    put(WALL + 2, 2, 'HOST', MUTED, bold=True)

def workspaces():
    for c, (_, ws, _) in zip(COLS, ENVS):
        box(24, c, 3, 20, 'single', SAND, SLOT)
        put(24, c + 10, '┴', SAND)
        center(25, c + 1, 18, ws, SAND)

def profiles():
    spans = [('personal', 2, 37, ''), ('client_x', 41, 76, 'shared by x-api and x-site'),
             ('client_y', 119, 37, '')]
    for name, c, w, note in spans:
        col = PROFILE[name]
        box(28, c, 5, w, 'double', col, mix(col, '#1a0f3d', 0.85))
        for x in (c + 27, c + 66) if name == 'client_x' else (c + 27,):
            put(28, x, '╧', col)
        put(29, c + 2, 'profile ', MUTED)
        put(29, c + 10, name, col, bold=True)
        if note:
            put(29, c + w - 2 - len(note), note, MUTED)
        put(30, c + 2, f'~/.config/ryad/profiles/{name}', PLASTER)
        put(31, c + 2, 'logins · API keys · shell history', MUTED)

def outside():
    put(34, 2, 'outside the walls:', NO, bold=True)
    c = 22
    for item in ('~/.ssh', '~/Documents', 'other projects', 'host keyring & D-Bus'):
        put(34, c, 'x', NO, bold=True)
        put(34, c + 2, item, mix(PLASTER, NO, 0.35))
        c += len(item) + 5
    put(34, 100, 'not isolated:', GLOW, bold=True)
    put(34, 115, 'your display (Wayland / X11) · network', PLASTER)

def sea():
    rnd = random.Random(3)
    rows = [('#7a3366', '~', '#ffd0a0', 0.25), ('#3a2f66', '-', '#c86a8a', 0.35),
            ('#1b3a6a', '~', '#7fb0d0', 0.3)]
    for i, (bg, g, fg, p) in enumerate(rows):
        r = H - len(rows) + i
        fill(r, 0, r, W - 1, bg)
        for c in range(W):
            if rnd.random() < p:
                put(r, c, g, fg)

def stars():
    rnd = random.Random(11)
    for r in (0, 1, 2, 3):
        for c in range(W):
            if G[r][c] == ' ' and rnd.random() < 0.03 and not (r in (1, 2) and c < 130):
                put(r, c, rnd.choice('..+*'), '#fff1c8' if rnd.random() < 0.6 else '#ffffff')

def compose():
    header(); image()
    for c, (name, _, prof) in zip(COLS, ENVS):
        environment(c, name, prof)
    wall(); workspaces(); profiles(); outside(); sea(); stars()

# ------------------------------------------------------------------ output
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace"

def write(here):
    w, h = W * CW, H * LH
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
         'role="img" aria-label="ryad environments: one image shared by four containers; each container '
         'mounts only its project folder and one profile home through the riad wall, and the rest of '
         'your home stays outside">',
         f'<clipPath id="c"><rect width="{w}" height="{h}" rx="16"/></clipPath><g clip-path="url(#c)">',
         '<g shape-rendering="crispEdges">']
    for r in range(H):
        c = 0
        while c < W:
            col = BG[r][c] or sky(r); e = c
            while e + 1 < W and (BG[r][e + 1] or sky(r)) == col:
                e += 1
            s.append(f'<rect x="{c * CW}" y="{r * LH}" width="{(e - c + 1) * CW}" height="{LH}" fill="{col}"/>')
            c = e + 1
    s.append(f'</g><g font-family="{FONT}" font-size="13.3" xml:space="preserve">')
    for r in range(H):
        # runs of one colour and weight; non-ASCII glyphs (box drawing, blocks) get their
        # own runs stretched to the cell grid, so fallback fonts can't shift the columns
        spans, c = [], 0
        while c < W:
            if G[r][c] == ' ':
                c += 1; continue
            key = (FG[r][c], BOLD[r][c], G[r][c].isascii()); e = c
            while e + 1 < W and (G[r][e + 1] == ' ' or (FG[r][e + 1], BOLD[r][e + 1], G[r][e + 1].isascii()) == key):
                e += 1
            while G[r][e] == ' ':
                e -= 1
            text = ''.join(G[r][c:e + 1])
            attrs = f' x="{c * CW}" fill="{key[0]}"' + (' font-weight="bold"' if key[1] else '')
            if not key[2]:
                attrs += f' textLength="{len(text) * CW}" lengthAdjust="spacingAndGlyphs"'
            spans.append(f'<tspan{attrs}>{escape(text)}</tspan>')
            c = e + 1
        if spans:
            s.append(f'<text y="{r * LH + 12}">{"".join(spans)}</text>')
    s.append('</g></g></svg>')
    with open(os.path.join(here, 'environments.svg'), 'w') as f:
        f.write('\n'.join(s) + '\n')

if __name__ == '__main__':
    compose()
    if '--txt' in sys.argv:
        print('\n'.join(''.join(row).rstrip() for row in G))
    else:
        write(os.path.dirname(os.path.abspath(__file__)))
