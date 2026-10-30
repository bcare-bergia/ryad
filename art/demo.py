#!/usr/bin/env python3
"""ryad demo: a real terminal session, played back as an animated SVG.

Two environments, two profiles, two prompt colors: step into a project, see
that ~/.ssh isn't there, start a GUI app in the background, then step into a
client's project, which doesn't see the first one.

Writes, next to this script:
  demo.cast  the recorded session (asciicast v2: asciinema can play it too)
  demo.svg   for the README:
             <p align="center"><img src="art/demo.svg" alt="a ryad session"></p>

Run: python3 art/demo.py            render demo.svg from demo.cast (no dependencies)
     python3 art/demo.py --record   record demo.cast again, then render. Needs the
                                    ryad image and a desktop session (it starts
                                    VSCodium). It uses its own ryad config
                                    (RYAD_HOME, in a temporary folder) and creates,
                                    then removes, ~/projects/acme, ~/clients/x/api
                                    and the environments "acme" and "api".
"""
import json
import os
import random
import re
import sys
import time
from html import escape

COLS, ROWS = 104, 24         # terminal size
CW, LH = 8, 18               # pixels per character cell
HERE = os.path.dirname(os.path.abspath(__file__))
CAST, SVG = os.path.join(HERE, 'demo.cast'), os.path.join(HERE, 'demo.svg')

# ------------------------------------------------------------------ the session
# Each profile gets its own prompt colors (256-color codes, from the art palette).
PROFILES = {
    'personal': 'user=1;38;5;43 host=1;38;5;43 dir=1;38;5;117',     # teal
    'client-x': 'user=1;38;5;208 host=1;38;5;208 dir=1;38;5;222',   # orange
}
FOLDERS = ['projects/acme', 'clients/x/api']       # under ~, created for the recording
SCENE = [
    ('type', 'cd ~/projects/acme'),
    ('type', 'ryad --profile=personal'),
    ('pause', 1.5),
    ('type', 'ls ~/.ssh'),
    ('type', 'exit'),
    ('type', 'ryad -d -- codium .'),
    ('pause', 1.0),
    ('type', 'cd ~/clients/x/api'),
    ('type', 'ryad --profile=client-x'),
    ('pause', 1.5),
    ('type', 'ls ~/projects'),
    ('type', 'exit'),
    ('pause', 4.0),
]
HOST_PS1 = r'you@laptop:\w$ '      # left plain, so the environments' colors stand out
MAX_GAP = 1.2                # seconds: longer waits (container start…) are cut to this

def record():
    import fcntl, pty, select, shutil, struct, subprocess, tempfile, termios
    home = os.path.expanduser('~')
    made = []
    for f in FOLDERS:
        top = os.path.join(home, f.split('/')[0])
        if os.path.exists(top) and top not in made:
            sys.exit(f'{top} exists: the recording creates and removes it, so it must not')
        made.append(top)
    rhome = tempfile.mkdtemp(prefix='ryad-demo-')
    env = dict(os.environ, RYAD_HOME=rhome, PS1=HOST_PS1, TERM='xterm-256color', LANG='C.UTF-8',
               LC_ALL='C.UTF-8', HISTFILE='/dev/null', PROMPT_COMMAND='')
    run = lambda *a: subprocess.run(['ryad', *a], env=env, check=True, stdout=subprocess.DEVNULL)
    for f in FOLDERS:
        os.makedirs(os.path.join(home, f))
    for p, colors in PROFILES.items():
        run('profiles', 'create', p)
        with open(os.path.join(rhome, 'profiles', p, 'profile.conf'), 'a') as fh:
            fh.write(f'PROMPT_COLORS="{colors}"\n')
    events, t0 = [], time.monotonic()
    pid, fd = pty.fork()
    if pid == 0:
        fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack('HHHH', ROWS, COLS, 0, 0))
        os.chdir(home)
        os.execvpe('bash', ['bash', '--norc', '--noprofile', '-i'], env)
    tail = ''

    def pump(seconds):
        """Read output for this long; return the time of the last output."""
        nonlocal tail
        end, last = time.monotonic() + seconds, None
        while (left := end - time.monotonic()) > 0:
            r, _, _ = select.select([fd], [], [], left)
            if not r:
                break
            try:
                data = os.read(fd, 65536)
            except OSError:
                break
            now = time.monotonic()
            events.append([now - t0, data])
            tail = (tail + data.decode('utf-8', 'replace'))[-400:]
            last = now
        return last

    def wait_prompt(timeout=300):
        """Until the output ends with a prompt ('$ ') and stays quiet a moment."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            pump(0.4)
            if re.sub(r'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07]*\x07', '', tail).endswith('$ '):
                if pump(0.6) is None:
                    return
        raise SystemExit('no prompt: ' + repr(tail[-200:]))

    rnd = random.Random(7)
    try:
        wait_prompt()
        pump(0.8)
        for kind, arg in SCENE:
            if kind == 'pause':
                pump(arg)
                continue
            for ch in arg:
                os.write(fd, ch.encode())
                pump(rnd.uniform(0.045, 0.12))
            pump(0.35)
            os.write(fd, b'\r')
            wait_prompt()
            pump(0.7)
    finally:
        try:
            os.write(fd, b'exit\r')
        except OSError:
            pass
        for name in ('acme', 'api'):
            subprocess.run(['ryad', 'rm', '--force', name], env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for top in made:
            shutil.rmtree(top, ignore_errors=True)
        # the containers wrote some of it under their own user ids
        subprocess.run(['podman', 'unshare', 'rm', '-rf', rhome])

    # Merge the bytes into text events, cut the long waits, hide who recorded it.
    user = os.environ.get('USER', '')
    subst = [(rhome, '~/.config/ryad'), (home, '/home/you')]
    out, t, prev, buf = [], 0.0, None, b''
    for when, data in events:
        if prev is not None:
            t += min(when - prev, MAX_GAP)
        prev = when
        buf += data
        try:
            text = buf.decode('utf-8')
        except UnicodeDecodeError:
            continue                     # a character split between two reads
        buf = b''
        for a, b in subst:
            text = text.replace(a, b)
        if user:                         # in the prompt, between color codes
            text = text.replace(user, 'you')
        out.append([round(t, 3), 'o', text])
    joined = ''.join(e[2] for e in out)
    for a in [a for a, _ in subst] + ([user] if user else []):
        assert a not in joined, f'{a!r} left in the recording'
    with open(CAST, 'w') as f:
        f.write(json.dumps({'version': 2, 'width': COLS, 'height': ROWS,
                            'env': {'TERM': 'xterm-256color', 'SHELL': '/bin/bash'}}) + '\n')
        for e in out:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')

# ------------------------------------------------------------------ terminal emulator
# Just enough of a VT100/xterm for a shell session: text, colors, cursor moves, erases.
# palette, from riad.py where it can
BG_COLOR, FG_COLOR = '#1a0f3c', '#efe6d8'
ANSI = ['#4a3a6e', '#ff7a6a', '#8fd694', '#f2c14e', '#7aa2ff', '#e85a8a', '#2bb8b0', '#efe6d8',
        '#a79fb8', '#ff9d8f', '#b4ecb4', '#ffd97a', '#a8c4ff', '#ff8cb4', '#6fe0d8', '#ffffff']

def color256(n):
    if n < 16:
        return ANSI[n]
    if n < 232:
        n -= 16
        lv = [0, 95, 135, 175, 215, 255]
        return '#%02x%02x%02x' % (lv[n // 36], lv[n // 6 % 6], lv[n % 6])
    v = 8 + (n - 232) * 10
    return '#%02x%02x%02x' % (v, v, v)

class Term:
    def __init__(self, cols, rows):
        self.cols, self.rows = cols, rows
        self.blank = (' ', None, None, False)
        self.grid = [[self.blank] * cols for _ in range(rows)]
        self.r = self.c = 0
        self.wrap = False
        self.fg, self.bg, self.bold, self.rev = None, None, False, False
        self.cursor = True
        self.pending = ''

    def scroll(self):
        self.grid.pop(0)
        self.grid.append([self.blank] * self.cols)

    def newline(self):
        if self.r == self.rows - 1:
            self.scroll()
        else:
            self.r += 1

    def put(self, ch):
        if self.wrap:
            self.c, self.wrap = 0, False
            self.newline()
        fg, bg = (self.bg or BG_COLOR, self.fg or FG_COLOR) if self.rev else (self.fg, self.bg)
        self.grid[self.r][self.c] = (ch, fg, bg, self.bold)
        if self.c == self.cols - 1:
            self.wrap = True
        else:
            self.c += 1

    def sgr(self, ps):
        ps = ps or [0]
        i = 0
        while i < len(ps):
            p = ps[i]
            if p == 0:
                self.fg, self.bg, self.bold, self.rev = None, None, False, False
            elif p == 1:
                self.bold = True
            elif p == 22:
                self.bold = False
            elif p == 7:
                self.rev = True
            elif p == 27:
                self.rev = False
            elif 30 <= p <= 37:
                self.fg = ANSI[p - 30]
            elif 90 <= p <= 97:
                self.fg = ANSI[p - 82]
            elif p == 39:
                self.fg = None
            elif 40 <= p <= 47:
                self.bg = ANSI[p - 40]
            elif 100 <= p <= 107:
                self.bg = ANSI[p - 92]
            elif p == 49:
                self.bg = None
            elif p in (38, 48) and i + 1 < len(ps):
                if ps[i + 1] == 5 and i + 2 < len(ps):
                    col, i = color256(ps[i + 2]), i + 2
                elif ps[i + 1] == 2 and i + 4 < len(ps):
                    col, i = '#%02x%02x%02x' % tuple(ps[i + 2:i + 5]), i + 4
                else:
                    col = None
                if p == 38:
                    self.fg = col
                else:
                    self.bg = col
            i += 1

    def erase(self, r, c0, c1):
        for c in range(c0, c1):
            self.grid[r][c] = (' ', None, self.bg, False)

    def csi(self, priv, ps, final):
        n = (ps[0] if ps and ps[0] else 1)
        if priv == '?':
            if final in 'hl' and 25 in ps:
                self.cursor = final == 'h'
            return
        if final == 'm':
            self.sgr(ps)
            return
        self.wrap = False
        if final == 'A':
            self.r = max(0, self.r - n)
        elif final == 'B':
            self.r = min(self.rows - 1, self.r + n)
        elif final == 'C':
            self.c = min(self.cols - 1, self.c + n)
        elif final == 'D':
            self.c = max(0, self.c - n)
        elif final == 'G':
            self.c = min(self.cols - 1, n - 1)
        elif final in 'Hf':
            self.r = min(self.rows - 1, (ps[0] if ps and ps[0] else 1) - 1)
            self.c = min(self.cols - 1, (ps[1] if len(ps) > 1 and ps[1] else 1) - 1)
        elif final == 'K':
            m = ps[0] if ps else 0
            self.erase(self.r, *{0: (self.c, self.cols), 1: (0, self.c + 1)}.get(m, (0, self.cols)))
        elif final == 'J':
            m = ps[0] if ps else 0
            rows = {0: range(self.r + 1, self.rows), 1: range(0, self.r)}.get(m, range(self.rows))
            if m == 0:
                self.erase(self.r, self.c, self.cols)
            elif m == 1:
                self.erase(self.r, 0, self.c + 1)
            for r in rows:
                self.erase(r, 0, self.cols)
        elif final == 'P':
            row = self.grid[self.r]
            del row[self.c:self.c + n]
            row.extend([self.blank] * (self.cols - len(row)))
        elif final == '@':
            row = self.grid[self.r]
            row[self.c:self.c] = [self.blank] * n
            del row[self.cols:]
        elif final == 'X':
            self.erase(self.r, self.c, min(self.cols, self.c + n))

    def feed(self, text):
        s, i = self.pending + text, 0
        self.pending = ''
        while i < len(s):
            ch = s[i]
            if ch == '\x1b':
                if i + 1 >= len(s):
                    self.pending = s[i:]
                    return
                nxt = s[i + 1]
                if nxt == '[':
                    m = re.compile(r'\[([?>=]?)([0-9;:]*)([ -/]*)([@-~])').match(s, i + 1)
                    if not m:
                        self.pending = s[i:]
                        return
                    ps = [int(x) if x else 0 for x in re.split('[;:]', m.group(2))] if m.group(2) else []
                    if not m.group(3):
                        self.csi(m.group(1), ps, m.group(4))
                    i = m.end()
                    continue
                if nxt == ']':           # OSC: window title and the like
                    m = re.compile(r'\][^\x07\x1b]*(\x07|\x1b\\)').match(s, i + 1)
                    if not m:
                        self.pending = s[i:]
                        return
                    i = m.end()
                    continue
                i += 3 if nxt in '()#%' else 2   # charset selection, keypad modes…
                continue
            if ch == '\r':
                self.c, self.wrap = 0, False
            elif ch == '\n':
                self.wrap = False
                self.newline()
            elif ch == '\b':
                self.c, self.wrap = max(0, self.c - 1), False
            elif ch == '\t':
                self.c = min(self.cols - 1, (self.c // 8 + 1) * 8)
            elif ch >= ' ' and ch != '\x7f':
                self.put(ch)
            i += 1

    def snapshot(self):
        return tuple(tuple(row) for row in self.grid), ((self.r, self.c) if self.cursor else None)

# ------------------------------------------------------------------ rendering
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace"
PAD, BAR = 20, 34            # window padding, title bar height
FRAME_BG, BAR_BG = '#2b1650', '#331d5c'
DOTS = ['#ff7a6a', '#f2c14e', '#2bb8b0']

def row_svg(row):
    """One terminal row as <rect>s for backgrounds and a <text> of colored runs."""
    rects, spans, c = [], [], 0
    while c < COLS:
        bg = row[c][2]
        e = c
        while e + 1 < COLS and row[e + 1][2] == bg:
            e += 1
        if bg:
            rects.append(f'<rect x="{c * CW}" width="{(e - c + 1) * CW}" height="{LH}" fill="{bg}"/>')
        c = e + 1
    c = 0
    while c < COLS:
        if row[c][0] == ' ':
            c += 1
            continue
        key = (row[c][1], row[c][3], row[c][0].isascii())
        e = c
        while e + 1 < COLS and (row[e + 1][0] == ' ' or (row[e + 1][1], row[e + 1][3], row[e + 1][0].isascii()) == key):
            e += 1
        while row[e][0] == ' ':
            e -= 1
        text = ''.join(x[0] for x in row[c:e + 1])
        attrs = f' x="{c * CW}"' + (f' fill="{key[0]}"' if key[0] else '') + (' font-weight="bold"' if key[1] else '')
        if not key[2]:
            attrs += f' textLength="{len(text) * CW}" lengthAdjust="spacingAndGlyphs"'
        spans.append(f'<tspan{attrs}>{escape(text)}</tspan>')
        c = e + 1
    out = ''.join(rects)
    if spans:
        out += f'<text y="13">{"".join(spans)}</text>'
    return out

def render():
    with open(CAST) as f:
        lines = f.read().splitlines()
    head = json.loads(lines[0])
    assert (head['width'], head['height']) == (COLS, ROWS), 'demo.cast was recorded at another size'
    term = Term(COLS, ROWS)
    frames = []                          # (time, screen, cursor)
    for line in lines[1:]:
        t, kind, data = json.loads(line)
        if kind != 'o':
            continue
        term.feed(data)
        snap = term.snapshot()
        if frames and frames[-1][1:] == snap:
            continue
        if frames and t - frames[-1][0] < 0.02:
            frames[-1] = (frames[-1][0], *snap)      # same instant: keep the last state
        else:
            frames.append((t, *snap))
    total = frames[-1][0] + 4.0

    sw, sh = COLS * CW, ROWS * LH
    w, h = sw + 2 * PAD, sh + BAR + 2 * PAD - 6
    rows, ids = {}, []
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
         f'xml:space="preserve" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="A ryad session: '
         'stepping into two projects, each with its own profile and prompt colors, and starting '
         'VSCodium in the background">']
    defs = []
    body = []
    for k, (t, screen, cur) in enumerate(frames):
        uses = []
        for r, row in enumerate(screen):
            if all(cell == (' ', None, None, False) for cell in row):
                continue
            if row not in rows:
                rows[row] = len(rows)
                defs.append(f'<g id="r{rows[row]}">{row_svg(row)}</g>')
            uses.append(f'<use xlink:href="#r{rows[row]}" y="{r * LH}"/>')
        if cur:
            uses.append(f'<rect x="{cur[1] * CW}" y="{cur[0] * LH + 2}" width="{CW}" height="{LH - 3}" '
                        f'fill="{FG_COLOR}" opacity=".75"/>')
        body.append(f'<g transform="translate(0 {k * sh})">{"".join(uses)}</g>')
    keys = ''.join(f'{100 * t / total:.3f}%{{transform:translateY({-k * sh}px)}}'
                   for k, (t, _, _) in enumerate(frames))
    s.append(f'<style>@keyframes play{{{keys}}}'
             f'.play{{animation:play {total:.2f}s steps(1,end) infinite}}text{{white-space:pre}}</style>')
    s.append(f'<defs>{"".join(defs)}</defs>')
    s.append(f'<rect width="{w}" height="{h}" rx="12" fill="{FRAME_BG}"/>'
             f'<rect width="{w}" height="{BAR}" rx="12" fill="{BAR_BG}"/>'
             f'<rect y="{BAR - 12}" width="{w}" height="12" fill="{BAR_BG}"/>')
    s += [f'<circle cx="{PAD + 6 + 20 * i}" cy="{BAR // 2}" r="6" fill="{c}"/>' for i, c in enumerate(DOTS)]
    s.append(f'<text x="{w // 2}" y="{BAR // 2 + 5}" text-anchor="middle" font-family="{FONT}" '
             f'font-size="13" fill="#a79fb8">ryad</text>')
    s.append(f'<clipPath id="screen"><rect width="{sw}" height="{sh}"/></clipPath>'
             f'<g transform="translate({PAD} {BAR + PAD - 6})" clip-path="url(#screen)">'
             f'<rect width="{sw}" height="{sh}" fill="{BG_COLOR}"/>'
             f'<g class="play" font-family="{FONT}" font-size="13.3" fill="{FG_COLOR}">'
             f'{"".join(body)}</g></g>')
    s.append('</svg>')
    with open(SVG, 'w') as f:
        f.write('\n'.join(s) + '\n')
    print(f'{SVG}: {len(frames)} frames, {total:.0f} s, {os.path.getsize(SVG) // 1024} KB')

if __name__ == '__main__':
    if '--record' in sys.argv:
        record()
    render()
