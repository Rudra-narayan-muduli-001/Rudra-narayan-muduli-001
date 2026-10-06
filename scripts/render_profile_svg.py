#!/usr/bin/env python3
"""
Render the profile / languages card from data/profile.json (written daily by
fetch_profile.py) as a terminal-window SVG that sits beside stats.svg.

The canvas is the same size as stats.svg (840 x 880) so the two panels line
up when the README shows them side by side at equal widths.

Four stat tiles slide in and their numbers count up to the real value, then a
"most used language" bar list grows in underneath. The count-up is a stack of
pre-rendered frames toggled with SMIL <set>, since GitHub runs SMIL/CSS inside
<img> SVGs but never JS.

    python scripts/render_profile_svg.py [data.json] [output.svg]
"""
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "data", "profile.json")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "profile.svg")

BG = "#0d1117"
BG2 = "#111722"
TILE = "#161b22"
FRAME = "#30363d"
MUTED = "#7d8590"
INK = "#e6edf3"
GREEN = "#39d353"
BAR = "#26a641"

W, H = 840, 880                      # == stats.svg canvas
PAD = 20
TITLEBAR_H = 30
COLS, ROWS = 2, 2
GAP = 16
TILE_W = (W - PAD * 2 - GAP * (COLS - 1)) / COLS
TILE_H = 150
TILES_TOP = TITLEBAR_H + PAD + 4
PANEL_TOP = TILES_TOP + ROWS * TILE_H + (ROWS - 1) * GAP + GAP

# timing (seconds)
TILE_STAGGER = 0.15
SLIDE_DUR = 0.45
COUNT_DUR = 1.2
FRAMES = 16
BAR_START = TILE_STAGGER * COLS * ROWS + 0.4
BAR_STAGGER = 0.08
BAR_DUR = 0.6


data = json.load(open(SRC))

# (label, value, suffix, caption, accent)
tiles = [
    ("total stars", data["stars"], "", "earned across repos", GREEN),
    ("total PRs", data["prs"], "", "authored", INK),
    ("total issues", data["issues"], "", "opened", INK),
    ("public repos", data["public_repos"], "", "and counting", INK),
]


def fmt(v):
    return f"{int(round(v)):,}"


parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
    '<style>'
    f'.t{{opacity:0;animation:in {SLIDE_DUR}s ease-out both}}'
    '@keyframes in{0%{opacity:0;transform:translateY(14px)}100%{opacity:1;transform:translateY(0)}}'
    f'.b{{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:grow {BAR_DUR}s ease-out both}}'
    '@keyframes grow{to{transform:scaleX(1)}}'
    '@media (prefers-reduced-motion: reduce){.t,.b{opacity:1!important;transform:none!important;animation:none!important}}'
    '</style>',
    f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient></defs>',
    f'<rect width="{W}" height="{H}" rx="12" fill="url(#bg)"/>',
    f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="none" stroke="{FRAME}"/>',
    f'<line x1="0" y1="{TITLEBAR_H}" x2="{W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>',
]
for i, dot in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dot}"/>')
parts.append(f'<text x="{W/2}" y="{TITLEBAR_H/2 + 4}" fill="{MUTED}" font-size="12" '
             f'text-anchor="middle">rudra@github: ~$ ./profile.sh</text>')

# ---- stat tiles ----------------------------------------------------------
for i, (label, value, suffix, caption, accent) in enumerate(tiles):
    col, row = i % COLS, i // COLS
    x = PAD + col * (TILE_W + GAP)
    y = TILES_TOP + row * (TILE_H + GAP)
    start = i * TILE_STAGGER
    count_start = start + SLIDE_DUR * 0.6

    parts.append(f'<g class="t" style="animation-delay:{start:.2f}s">')
    parts.append(f'<rect x="{x:.1f}" y="{y}" width="{TILE_W:.1f}" height="{TILE_H}" rx="10" '
                 f'fill="{TILE}" stroke="{FRAME}"/>')
    parts.append(f'<text x="{x+24:.1f}" y="{y+40}" fill="{MUTED}" font-size="22">$ {label}</text>')

    # count-up frames: ease-out so it decelerates into the real number
    num_y = y + 100
    for k in range(1, FRAMES + 1):
        p = k / FRAMES
        v = value * (1 - (1 - p) ** 3)
        t_on = count_start + COUNT_DUR * (k - 1) / FRAMES
        t_off = count_start + COUNT_DUR * k / FRAMES
        anim = f'<set attributeName="opacity" to="1" begin="{t_on:.3f}s"/>'
        if k < FRAMES:
            anim += f'<set attributeName="opacity" to="0" begin="{t_off:.3f}s"/>'
        parts.append(
            f'<text x="{x+24:.1f}" y="{num_y}" opacity="0" font-size="54" font-weight="700" fill="{accent}">'
            f'{fmt(v)}<tspan font-size="24" font-weight="400" fill="{MUTED}">{suffix}</tspan>'
            f'{anim}</text>'
        )
    parts.append(f'<text x="{x+24:.1f}" y="{y+132}" fill="{MUTED}" font-size="20">{caption}</text>')
    parts.append('</g>')

# ---- most used language --------------------------------------------------
langs = data["top_languages"]
panel_x, panel_w = PAD, W - PAD * 2
panel_h = H - PAD - PANEL_TOP
parts.append(f'<g class="t" style="animation-delay:{BAR_START - 0.3:.2f}s">')
parts.append(f'<rect x="{panel_x}" y="{PANEL_TOP}" width="{panel_w}" height="{panel_h}" rx="10" '
             f'fill="{TILE}" stroke="{FRAME}"/>')
parts.append(f'<text x="{panel_x+24}" y="{PANEL_TOP+40}" fill="{MUTED}" font-size="22">$ most used language</text>')
parts.append('</g>')

list_top = PANEL_TOP + 64
list_bot = PANEL_TOP + panel_h - 24
row_h = (list_bot - list_top) / max(len(langs), 1)
bar_x = panel_x + 220
bar_end = panel_x + panel_w - 90
peak = max((m["repos"] for m in langs), default=1) or 1
for i, m in enumerate(langs):
    ry = list_top + i * row_h
    w = max(4, (bar_end - bar_x) * m["repos"] / peak)
    fill = GREEN if m["repos"] == peak else BAR
    delay = BAR_START + i * BAR_STAGGER
    name = html.escape(m["language"])
    parts.append(f'<text x="{panel_x+24}" y="{ry + row_h/2 + 7:.1f}" fill="{INK}" font-size="22">{name}</text>')
    parts.append(f'<rect class="b" x="{bar_x}" y="{ry + 6:.1f}" width="{w:.1f}" height="{row_h - 12:.1f}" '
                 f'rx="4" fill="{fill}" style="animation-delay:{delay:.2f}s"/>')
    parts.append(f'<text class="t" style="animation-delay:{delay + BAR_DUR:.2f}s" x="{bar_end + 12}" '
                 f'y="{ry + row_h/2 + 7:.1f}" fill="{MUTED}" font-size="20">{m["repos"]} repos</text>')

parts.append('</svg>')
svg = "".join(parts)
open(OUT, "w").write(svg)
print(f"wrote {OUT}: {W} x {H}, {len(svg)//1024} KB")
