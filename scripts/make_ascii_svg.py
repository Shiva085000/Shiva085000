"""Convert source-prepped.png into a self-typing, monochrome ASCII portrait SVG.

Each row is revealed by a left-to-right clip wipe with a small block cursor riding
the edge, staggered top to bottom. It prints once and freezes (SMIL, which GitHub
plays inside <img>). Set STATIC=1 for a frozen frame.

Usage:
    python scripts/make_ascii_svg.py [--src source-prepped.png] [--cols 100] [--out ascii-portrait.svg]
"""

import argparse
import os
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image

RAMP = " .`:-=+*cs#%@"  # bright (sparse) -> dark (dense); leading space clears the background
# Renderers collapse runs of ordinary spaces (xml:space is unreliable), which would
# let textLength smear each row across the full width. NBSP never collapses.
NBSP = "\u00a0"

FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
FS = 10.0
CHAR_W = 6.0  # monospace advance at 10px; textLength enforces it regardless of font
LINE_H = 11.0
PAD = 22.0
DISPLAY_W = 370.0  # README width; window chrome is scaled so it matches the info card's

BG = "#0d1117"
BORDER = "#30363d"
INK = "#d0d3da"
CURSOR = "#C6F432"

STAGGER = 0.055
WIPE = 0.38
START = 0.3


def to_rows(src: str, cols: int, gamma: float) -> list[str]:
    img = Image.open(src).convert("L")
    w, h = img.size
    rows = max(1, round(cols * (h / w) * (CHAR_W / LINE_H)))
    g = np.asarray(img.resize((cols, rows), Image.LANCZOS)).astype(np.float32) / 255.0
    g = np.power(np.clip(g, 0, 1), gamma)
    idx = np.rint((1.0 - g) * (len(RAMP) - 1)).astype(int)
    lines = ["".join(RAMP[i] for i in row) for row in idx]
    # Trim fully blank rows at the top and bottom.
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def build_svg(lines: list[str], cols: int, static: bool) -> str:
    text_w = cols * CHAR_W
    width = text_w + PAD * 2
    k = width / DISPLAY_W  # 1 display px in this SVG's units
    bar_h = 34.0 * k
    height = bar_h + PAD + len(lines) * LINE_H + PAD * 0.8

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'width="{width:.0f}" height="{height:.0f}" role="img" aria-label="ASCII portrait of Gokul Shiva R">',
        f'<rect x="{k / 2:.2f}" y="{k / 2:.2f}" width="{width - k:.1f}" height="{height - k:.1f}" rx="{12 * k:.1f}" '
        f'fill="{BG}" stroke="{BORDER}" stroke-width="{k:.2f}"/>',
        f'<line x1="0" y1="{bar_h:.1f}" x2="{width:.0f}" y2="{bar_h:.1f}" stroke="{BORDER}" stroke-width="{k:.2f}"/>',
    ]
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        out.append(f'<circle cx="{(20 + i * 16) * k:.1f}" cy="{bar_h / 2:.1f}" r="{5 * k:.1f}" fill="{c}" opacity="0.85"/>')
    out.append(
        f'<text x="{width / 2:.0f}" y="{bar_h / 2 + 4 * k:.1f}" text-anchor="middle" font-family="{FONT}" '
        f'font-size="{11 * k:.1f}" fill="#8b949e">~/portrait.txt</text>'
    )

    if not static:
        out.append("<defs>")
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            y = bar_h + PAD + i * LINE_H - FS + 1
            t = START + i * STAGGER
            out.append(
                f'<clipPath id="r{i}"><rect x="{PAD}" y="{y:.1f}" width="0" height="{LINE_H + 1}">'
                f'<animate attributeName="width" from="0" to="{text_w}" begin="{t:.3f}s" dur="{WIPE}s" fill="freeze"/>'
                f"</rect></clipPath>"
            )
        out.append("</defs>")

    out.append(f'<g font-family="{FONT}" font-size="{FS}" fill="{INK}" xml:space="preserve">')
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        y = bar_h + PAD + i * LINE_H
        clip = "" if static else f' clip-path="url(#r{i})"'
        out.append(
            f'<text x="{PAD}" y="{y:.1f}" textLength="{text_w}" lengthAdjust="spacing"{clip}>{escape(line).replace(" ", NBSP)}</text>'
        )
    out.append("</g>")

    if not static:
        # Rows overlap in time, so each gets its own block cursor riding its wipe
        # edge; together they form a diagonal "print head".
        out.append(f'<g fill="{CURSOR}">')
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            y = bar_h + PAD + i * LINE_H - FS + 1.5
            t = START + i * STAGGER
            end_x = PAD + len(line.rstrip()) * CHAR_W
            dur = WIPE * len(line.rstrip()) / len(line)
            out.append(
                f'<rect x="{PAD}" y="{y:.1f}" width="{CHAR_W}" height="{LINE_H - 1}" opacity="0">'
                f'<animate attributeName="x" from="{PAD}" to="{end_x:.1f}" begin="{t:.3f}s" dur="{dur:.3f}s" fill="freeze"/>'
                f'<set attributeName="opacity" to="1" begin="{t:.3f}s"/>'
                f'<set attributeName="opacity" to="0" begin="{t + dur:.3f}s"/>'
                f"</rect>"
            )
        out.append("</g>")

    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="source-prepped.png")
    ap.add_argument("--cols", type=int, default=100)
    ap.add_argument("--gamma", type=float, default=1.3)
    ap.add_argument("--out", default="ascii-portrait.svg")
    args = ap.parse_args()

    lines = to_rows(args.src, args.cols, args.gamma)
    svg = build_svg(lines, args.cols, static=os.environ.get("STATIC") == "1")
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {args.out}: {len(lines)} rows x {args.cols} cols")


if __name__ == "__main__":
    main()
