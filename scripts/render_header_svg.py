#!/usr/bin/env python3
"""
Render an animated header banner (header.svg) with the name set in the
IBM Plex Mono SemiBold font (OFL, vendored under scripts/fonts/) --
a clean monospace that reads as developer-native.

Glyphs are baked to SVG paths via fontTools, so the banner needs no webfont
at view time and renders identically everywhere. Background waves drift via
SMIL, letters rise in staggered, and a soft glow pulses behind the name --
all runnable inside GitHub's <img> SVGs (SMIL/CSS only, no JS).

    python scripts/render_header_svg.py [output.svg]

Requires (one-time, not needed by the daily workflow): pip install fonttools
"""
import math
import os
import sys

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "IBMPlexMono-SemiBold.ttf")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "header.svg")

TEXT = "Rudra Narayan Muduli"
W, H = 1200, 220
MAX_TEXT_W = 1060          # side margins for the name
CENTER_Y = 152              # optical center of the name (waves hang from the top)

BG1, BG2 = "#1a1b27", "#2a2145"
WAVE1, WAVE2 = "#7a45c7", "#5b34a8"

font = TTFont(FONT)
upm = font["head"].unitsPerEm
cmap = font.getBestCmap()
glyph_set = font.getGlyphSet()
hmtx = font["hmtx"]
try:
    cap_h = font["OS/2"].sCapHeight / upm
except AttributeError:
    cap_h = 0.72

# ---- lay out glyphs in font units, then auto-fit to MAX_TEXT_W ----------------
advances, draws = [], []
for ch in TEXT:
    if ch == " ":
        advances.append(hmtx[cmap[ord(" ")]][0] if ord(" ") in cmap else int(upm * 0.3))
        draws.append(None)
        continue
    name = cmap[ord(ch)]
    pen = SVGPathPen(glyph_set)
    glyph_set[name].draw(pen)
    draws.append(pen.getCommands())
    advances.append(hmtx[name][0])
natural = sum(advances)
SIZE = upm * MAX_TEXT_W / natural
scale = SIZE / upm
baseline = CENTER_Y + (cap_h * SIZE) / 2

print(f"font size {SIZE:.1f}, text width {MAX_TEXT_W}, baseline {baseline:.1f}")

# ---- letters with staggered rise-in ----------------------------------------
positions = []
x = (W - MAX_TEXT_W) / 2
for adv in advances:
    positions.append(x)
    x += adv * scale

letters = []
for i, (ch, d, lx) in enumerate(zip(TEXT, draws, positions)):
    if d is not None:
        letters.append(
            f'<g class="L" style="animation-delay:{0.15 + i * 0.045:.3f}s">'
            f'<path d="{d}" fill="url(#nameGrad)" '
            f'transform="translate({lx:.1f},{baseline:.1f}) scale({scale:.4f},{-scale:.4f})"/>'
            f'</g>'
        )

glow = "".join(
    f'<path d="{d}" fill="#7a45c7" '
    f'transform="translate({lx:.1f},{baseline:.1f}) scale({scale:.4f},{-scale:.4f})"/>'
    for ch, d, lx in zip(TEXT, draws, positions) if d is not None
)


def wave_path(y_base, amp, length, periods):
    pts = []
    steps = periods * 24
    for k in range(steps + 1):
        px = length * k / steps
        py = y_base + amp * math.sin(2 * math.pi * periods * k / steps)
        pts.append(f"{'M' if k == 0 else 'L'}{px:.1f},{py:.1f}")
    # close up to the top edge over a double-wide canvas for seamless looping
    return "".join(pts) + f"L{length:.1f},0L0,0Z"


# double-wide waves hanging from the top; each group slides left by exactly
# one wavelength, looping
SPAN = W * 2
wave1 = wave_path(52, 12, SPAN, 4)
wave2 = wave_path(74, 15, SPAN, 3)

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
    '<style>'
    '.L{opacity:0;animation:rise .55s cubic-bezier(.2,.7,.3,1.2) both}'
    '@keyframes rise{0%{opacity:0;transform:translateY(14px)}100%{opacity:1;transform:translateY(0)}}'
    '@media (prefers-reduced-motion: reduce){.L{opacity:1!important;animation:none!important}}'
    '</style>',
    '<defs>'
    f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="0">'
    f'<stop offset="0" stop-color="{BG1}"/><stop offset=".5" stop-color="{BG2}"/>'
    f'<stop offset="1" stop-color="{BG1}"/></linearGradient>',
    '<linearGradient id="nameGrad" x1="0" y1="0" x2="1" y2="0">'
    '<stop offset="0" stop-color="#e8ecff"/><stop offset=".55" stop-color="#bb9af7"/>'
    '<stop offset="1" stop-color="#7a45c7"/></linearGradient>',
    '<filter id="glow" x="-20%" y="-40%" width="140%" height="180%">'
    '<feGaussianBlur stdDeviation="7" result="b"/>'
    '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
    '</defs>',
    f'<rect width="{W}" height="{H}" rx="10" fill="url(#bg)"/>',
    # drifting waves (back + front)
    f'<g opacity="0.28"><path d="{wave1}" fill="{WAVE1}">'
    '<animateTransform attributeName="transform" type="translate" '
    f'from="0,0" to="-{SPAN // 4},0" dur="9s" repeatCount="indefinite"/></path></g>',
    f'<g opacity="0.35"><path d="{wave2}" fill="{WAVE2}">'
    '<animateTransform attributeName="transform" type="translate" '
    f'from="-{SPAN // 3},0" to="0,0" dur="12s" repeatCount="indefinite"/></path></g>',
    # soft pulsing glow behind the name
    '<g opacity="0.5" filter="url(#glow)">'
    '<animate attributeName="opacity" values="0.35;0.65;0.35" dur="3.2s" repeatCount="indefinite"/>',
    glow,
    '</g>',
    f'<g filter="url(#glow)">{"".join(letters)}</g>',
    '</svg>',
]

svg = "".join(parts)
open(OUT, "w").write(svg)
print(f"wrote {OUT}: {W} x {H}, {len(svg)//1024} KB")
