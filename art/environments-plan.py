#!/usr/bin/env python3
"""ryad environments as a riad seen from above, in coloured ASCII.

Same tools, separate rooms: each environment is a room around one courtyard.
The fountain in the middle is the image, so every room opens onto the same
tools; each room's zellige floor is its profile, and its project folder is
the only other thing brought in. Everything else stays outside the walls.
Same look as riad.svg and environments.svg (8x16 cells, the sunset palette).

Writes, next to this script:
  environments-plan.svg  for the README:
                         <p align="center"><img src="art/environments-plan.svg" alt="ryad environments"></p>
Run: python3 art/environments-plan.py          (no dependencies)
     python3 art/environments-plan.py --txt    print the character grid instead
"""
import os
import random
import sys
from html import escape

W, H = 152, 46              # characters
CW, LH = 8, 16              # pixels per character cell

# ------------------------------------------------------------------ palette
# from riad.py
GOLD, PLASTER, SAND, WOOD, SAIL = '#f2c14e', '#efcf9c', '#e6c58e', '#7a4424', '#f6e7c8'
ROSE, ROCK = '#d27a52', '#a8664a'
MUTED, NO, WARN = '#a79fb8', '#ff7a6a', '#ffb347'
PROFILE = {'personal': '#2bb8b0', 'client_x': '#ff8c1a', 'client_y': '#e85a8a'}
PANEL = '#1f1147'
ISLAND, GARDEN, PATH, WATER = '#6e4a36', '#1d3a2a', '#3b2a44', '#1f5f7a'

def rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]

def hexc(c):
    return '#%02x%02x%02x' % tuple(int(round(v)) for v in c)

def mix(a, b, t):
    a, b = rgb(a), rgb(b)
    return hexc([x + (y - x) * t for x, y in zip(a, b)])

def sea(r):
    return mix('#1b3a6a', '#0f2148', r / (H - 1))

# ------------------------------------------------------------------ grid kit
G = [[' '] * W for _ in range(H)]
FG = [[None] * W for _ in range(H)]
BG = [[None] * W for _ in range(H)]
BOLD = [[False] * W for _ in range(H)]
USED = [[False] * W for _ in range(H)]   # written by a label or a shape: keep decoration off

def put(r, c, s, fg, bg=None, bold=False):
    for i, ch in enumerate(s):
        if 0 <= c + i < W:
            G[r][c + i], FG[r][c + i], BOLD[r][c + i] = ch, fg, bold
            USED[r][c + i] = True
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

# ------------------------------------------------------------------ the riad
# outer wall rows 5..43, cols 5..104; inside, rows 6..42 and cols 7..102
TOP, BOT, LEFT, RIGHT = 5, 43, 5, 104
PATH_C = (52, 57)           # the north-south path
PATH_R = (23, 25)           # the east-west path
ROOMS = [  # name, workspace, profile, interior rows, interior cols, wall cells, door cells
    ('blog', '~/perso/blog', 'personal', (6, 17), (7, 42), [(18, 7, 18, 44), (6, 43, 18, 44)], (18, 37, 18, 40)),
    ('x-api', '~/client_x/api', 'client_x', (6, 17), (67, 102), [(18, 65, 18, 102), (6, 65, 18, 66)], (18, 69, 18, 72)),
    ('y-robot', '~/client_y/robot', 'client_y', (31, 42), (7, 42), [(30, 7, 30, 44), (30, 43, 42, 44)], (30, 37, 30, 40)),
    ('x-site', '~/client_x/site', 'client_x', (31, 42), (67, 102), [(30, 65, 30, 102), (30, 65, 42, 66)], (30, 69, 30, 72)),
]

def header():
    put(1, 4, 'ryad, seen from above', GOLD, bold=True)
    put(2, 4, 'Same tools, separate rooms: every room opens onto one courtyard, '
              'and each keeps its own folder and its own keys.', MUTED)

def island():
    rnd = random.Random(5)
    fill(TOP - 1, LEFT - 3, BOT + 1, RIGHT + 3, ISLAND)
    for r in range(TOP - 1, BOT + 2):           # a ragged shore
        for c in (LEFT - 4, RIGHT + 4):
            if rnd.random() < 0.5:
                BG[r][c] = ISLAND
    for r in range(TOP - 1, BOT + 2):
        for c in range(LEFT - 4, RIGHT + 5):
            inside = TOP <= r <= BOT and LEFT <= c <= RIGHT
            if BG[r][c] == ISLAND and not inside and rnd.random() < 0.08:
                G[r][c], FG[r][c] = rnd.choice('.,'), mix(ISLAND, SAND, 0.35)

def walls():
    for c in range(LEFT, RIGHT + 1):            # crenellations, seen from above
        for r in (TOP, BOT):
            BG[r][c] = ROSE if (c // 2) % 2 else mix(ROSE, ROCK, 0.7)
    for r in range(TOP, BOT + 1):
        for c in (LEFT, LEFT + 1, RIGHT - 1, RIGHT):
            BG[r][c] = ROSE if r % 2 else mix(ROSE, ROCK, 0.7)
    for c in range(PATH_C[0], PATH_C[1] + 1):   # the gate
        put(BOT, c, '▒', mix(WOOD, '#000000', 0.2), WOOD)
    center(BOT + 1, 40, 30, ' $ ryad <name>  steps in ', PLASTER, bold=True)

def courtyard():
    fill(TOP + 1, LEFT + 2, BOT - 1, RIGHT - 2, GARDEN)
    for r in range(TOP + 1, BOT):
        for c in range(PATH_C[0], PATH_C[1] + 1):
            put(r, c, '·' if (r + c) % 2 else ' ', mix(PATH, PLASTER, 0.25), PATH)
    for r in range(PATH_R[0], PATH_R[1] + 1):
        for c in range(LEFT + 2, RIGHT - 1):
            put(r, c, '·' if (r + c) % 2 else ' ', mix(PATH, PLASTER, 0.25), PATH)
    # the fountain: the image every room shares
    box(21, 45, 7, 20, 'round', PLASTER, WATER)
    put(22, 46, ' ' * 18, None); put(23, 46, ' ' * 18, None)
    put(24, 46, ' ' * 18, None); put(25, 46, ' ' * 18, None); put(26, 46, ' ' * 18, None)
    for r in range(22, 27):
        for c in range(46, 64):
            if (r * 3 + c) % 5 == 0:
                put(r, c, '~', '#7fe0e0')
    center(23, 46, 18, 'ryad image', GOLD, bold=True)
    center(25, 46, 18, '$ ryad build', PLASTER)
    for c in range(46, 64):                     # keep the labels on clear water
        for r in (23, 25):
            if G[r][c] == '~':
                G[r][c] = ' '
    # the same tools along the paths, in every direction
    center(23, 7, 38, ' pi · claude · claude-desktop ', PLASTER)
    center(24, 7, 38, ' antigravity · codium · emacs ', PLASTER)
    center(25, 7, 38, ' rstudio · firefox · git ', PLASTER)
    center(23, 65, 38, ' python · node · R ', PLASTER)
    center(24, 65, 38, ' + anything else that runs ', MUTED)
    center(25, 65, 38, ' on Debian or Ubuntu ', MUTED)
    put(20, 9, 'the courtyard is the image', GOLD, bold=True)
    put(28, 101 - len('every room opens onto it'), 'every room opens onto it', MUTED)

def room(name, ws, prof, rows, cols, wall_cells, door):
    col = PROFILE[prof]
    r0, r1 = rows
    c0, c1 = cols
    for wr0, wc0, wr1, wc1 in wall_cells:
        fill(wr0, wc0, wr1, wc1, ROSE)
    dr0, dc0, dr1, dc1 = door
    fill(dr0, dc0, dr1, dc1, GARDEN)
    # zellige floor: a tiled border in the profile's colour around a plain floor
    tile = mix(col, PANEL, 0.7)
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            edge = r in (r0, r1) or c in (c0, c0 + 1, c1 - 1, c1)
            put(r, c, ('▄' if (r + c) % 2 else '▀') if edge else ' ', col, tile if edge else mix(col, PANEL, 0.88))
    x = c0 + 4
    put(r0 + 2, x, 'environment ', MUTED)
    put(r0 + 2, x + 12, name, PLASTER, bold=True)
    put(r0 + 4, x, 'project', MUTED)
    put(r0 + 4, x + 10, ws, SAND, bold=True)
    put(r0 + 5, x + 10, 'rw · same path', MUTED)
    put(r0 + 7, x, 'home', MUTED)
    put(r0 + 7, x + 10, 'profile ', MUTED)
    put(r0 + 7, x + 18, prof, col, bold=True)
    put(r0 + 8, x + 10, 'rw · /home/you', MUTED)

def legend():
    x, w = 110, 40
    box(4, x, 17, w, 'single', mix(PLASTER, PANEL, 0.4), PANEL)
    put(4, x + 2, ' zellige floor = profile ', GOLD, bold=True)
    used = {'personal': 'blog', 'client_x': 'x-api and x-site', 'client_y': 'y-robot'}
    r = 6
    for name, col in PROFILE.items():
        put(r, x + 2, '▄▀▄▀', col, mix(col, PANEL, 0.7))
        put(r, x + 7, name, col, bold=True)
        put(r, x + 8 + len(name), f'· {used[name]}', MUTED)
        put(r + 1, x + 2, f'~/.config/ryad/profiles/{name}', PLASTER)
        r += 3
    put(15, x + 2, 'each holds the logins, API keys and', MUTED)
    put(16, x + 2, 'history of one context; rooms on the', MUTED)
    put(17, x + 2, 'same profile share them', MUTED)

    box(22, x, 8, w, 'single', mix(NO, PANEL, 0.4), PANEL)
    put(22, x + 2, ' outside the walls ', NO, bold=True)
    for i, item in enumerate(('~/.ssh', '~/Documents', 'other projects', 'host keyring & D-Bus')):
        put(24 + i, x + 3, 'x', NO, bold=True)
        put(24 + i, x + 5, item, PLASTER)
    put(28, x + 3, 'never brought into any room', MUTED)

    box(31, x, 5, w, 'single', mix(WARN, PANEL, 0.4), PANEL)
    put(31, x + 2, ' not walled off ', WARN, bold=True)
    put(32, x + 3, '!', WARN, bold=True); put(32, x + 5, 'your display (Wayland / X11)', PLASTER)
    put(33, x + 3, '!', WARN, bold=True); put(33, x + 5, 'network', PLASTER)

def boat():
    x, r = 124, 38
    for i, (line, fg) in enumerate(((r'   |\ ', SAIL), (r'   | \ ', SAIL), (r'   |__\ ', SAIL),
                                    (r'\_______/', WOOD))):
        for j, ch in enumerate(line):
            if ch != ' ':
                put(r + i, x + j, ch, fg, bold=True)

def garden():
    rnd = random.Random(9)
    for r in range(TOP + 1, BOT):
        for c in range(LEFT + 2, RIGHT - 1):
            near = any(USED[r][k] for k in range(max(c - 2, 0), min(c + 3, W)))
            if BG[r][c] == GARDEN and not near and rnd.random() < 0.05:
                g, fg = rnd.choice((('o', '#ff8c1a'), ('*', '#5aa040'), ('@', '#3f8a3a'), ('@', '#3f8a3a')))
                put(r, c, g, fg)

def waves():
    rnd = random.Random(2)
    for r in range(H):
        for c in range(W):
            if BG[r][c] is None and not USED[r][c] and rnd.random() < 0.05 and not (r in (1, 2) and c < 140):
                put(r, c, rnd.choice('~~-'), mix(sea(r), '#7fb0d0', 0.45))

def compose():
    header(); island(); walls(); courtyard()
    for spec in ROOMS:
        room(*spec)
    legend(); boat(); garden(); waves()

# ------------------------------------------------------------------ output
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace"

def write(here):
    w, h = W * CW, H * LH
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
         'role="img" aria-label="ryad environments as a riad seen from above: four rooms, one per environment, '
         'open onto a courtyard whose fountain is the shared image; each room has its own project folder and a '
         'zellige floor coloured by its profile, and the rest of your home stays outside the walls">',
         f'<clipPath id="c"><rect width="{w}" height="{h}" rx="16"/></clipPath><g clip-path="url(#c)">',
         '<g shape-rendering="crispEdges">']
    for r in range(H):
        c = 0
        while c < W:
            col = BG[r][c] or sea(r); e = c
            while e + 1 < W and (BG[r][e + 1] or sea(r)) == col:
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
    with open(os.path.join(here, 'environments-plan.svg'), 'w') as f:
        f.write('\n'.join(s) + '\n')

if __name__ == '__main__':
    compose()
    if '--txt' in sys.argv:
        print('\n'.join(''.join(row).rstrip() for row in G))
    else:
        write(os.path.dirname(os.path.abspath(__file__)))
