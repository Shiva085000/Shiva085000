"""Hand-authored neofetch-style info card SVG.

Lines fade and slide in on a short stagger so the panel looks like it prints next
to the portrait. Its height is matched to the portrait's displayed height (the
README shows the portrait at 370px and this card at 490px wide).
Set STATIC=1 for a frozen frame.

Usage:
    python scripts/make_info_card.py [--portrait ascii-portrait.svg] [--out info-card.svg]
"""

import argparse
import os
import re
import textwrap
from xml.sax.saxutils import escape

WIDTH = 490.0
PORTRAIT_DISPLAY_W = 370.0

FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
BG = "#0d1117"
BORDER = "#30363d"
KEY = "#C6F432"
VAL = "#d0d3da"
DIM = "#8b949e"
ACCENT = "#7C5CFF"

USER = "gokul"
HOST = "github"

# key, value. Values wrap onto continuation lines aligned under the value column.
ROWS = [
    ("Name", "Gokul Shiva R"),
    ("Role", "Software Engineer · Data & AI"),
    ("Now", "Applied AI Engineer Intern @ UpTroop"),
    ("Prev", "Automation & AI @ Tube Products of India"),
    ("", "Software Dev @ Brainwaves NeuroRehab"),
    ("Edu", "B.Tech AI @ SRM IST '27 · CGPA 8.61"),
    ("Langs", "Python · Java · SQL · C++ · TypeScript"),
    ("ML / AI", "PyTorch · CatBoost · RAG · LangGraph"),
    ("Infra", "FastAPI · Docker · Kubernetes · Azure"),
    ("Data", "PostgreSQL · MongoDB · TimescaleDB"),
    ("Projects", "Trust Flow · Gridlock (R² 0.87)"),
    ("", "CampaignMind · RiskSense AI (paper)"),
    ("Freelance", "johannahealthcare.in"),
    ("", "houseofstaffoffshoretalent.com"),
    ("Certs", "MongoDB Assoc. Dev · NVIDIA GenAI · NPTEL Java"),
    ("Contact", "gokulshiva085@gmail.com"),
]

SWATCHES = ["#1f2328", "#ff6b5c", "#C6F432", "#f5c542", "#7C5CFF", "#d16ff7", "#22D3EE", "#e6edf3"]

PAD = 22.0
BAR_H = 34.0
KEY_COLS = 11


def portrait_height(path: str) -> float | None:
    try:
        with open(path, encoding="utf-8") as f:
            head = f.read(400)
    except OSError:
        return None
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', head)
    if not m:
        return None
    w, h = float(m.group(1)), float(m.group(2))
    # Height this card needs (in its own 490-wide units) to line up with the portrait.
    return PORTRAIT_DISPLAY_W * h / w * (WIDTH / 490.0)


def layout(fs: float) -> tuple[list[tuple[str, str]], float]:
    char_w = fs * 0.6
    max_chars = int((WIDTH - PAD * 2) / char_w)
    val_chars = max_chars - KEY_COLS
    lines: list[tuple[str, str]] = []
    for key, val in ROWS:
        chunks = textwrap.wrap(val, val_chars, break_on_hyphens=False) or [""]
        for j, chunk in enumerate(chunks):
            lines.append((key if j == 0 else "", chunk))
    line_h = fs * 1.45
    # bar + gap + title + rule + rows + gap + swatches + bottom pad
    needed = BAR_H + PAD + line_h * 2 + len(lines) * line_h + 14 + 16 + PAD
    return lines, needed


def build(target_h: float | None, static: bool) -> str:
    fs = 13.0
    lines, needed = layout(fs)
    while target_h and needed > target_h and fs > 10.5:
        fs -= 0.25
        lines, needed = layout(fs)
    height = max(needed, target_h or 0)
    line_h = fs * 1.45
    char_w = fs * 0.6
    key_x = PAD
    val_x = PAD + KEY_COLS * char_w

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH:.0f} {height:.0f}" '
        f'width="{WIDTH:.0f}" height="{height:.0f}" role="img" aria-label="neofetch-style card: Gokul Shiva R, Software Engineer, Data and AI">',
    ]
    if not static:
        out.append(
            "<style>"
            ".l{opacity:0;animation:in .5s cubic-bezier(.22,1,.36,1) forwards}"
            "@keyframes in{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:translateX(0)}}"
            "</style>"
        )
    out += [
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1:.0f}" height="{height - 1:.0f}" rx="12" fill="{BG}" stroke="{BORDER}"/>',
        f'<line x1="0" y1="{BAR_H}" x2="{WIDTH:.0f}" y2="{BAR_H}" stroke="{BORDER}"/>',
    ]
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        out.append(f'<circle cx="{20 + i * 16}" cy="{BAR_H / 2}" r="5" fill="{c}" opacity="0.85"/>')
    out.append(
        f'<text x="{WIDTH / 2:.0f}" y="{BAR_H / 2 + 4}" text-anchor="middle" font-family="{FONT}" '
        f'font-size="11" fill="{DIM}">{USER}@{HOST}: ~ $ neofetch</text>'
    )

    out.append(f'<g font-family="{FONT}" font-size="{fs:.2f}">')
    y = BAR_H + PAD + fs
    n = 0

    def line(content: str) -> None:
        nonlocal n
        if static:
            out.append(f"<g>{content}</g>")
        else:
            out.append(f'<g class="l" style="animation-delay:{0.35 + n * 0.11:.2f}s">{content}</g>')
        n += 1

    title = f"{USER}@{HOST}"
    line(
        f'<text x="{key_x}" y="{y:.1f}" font-weight="700"><tspan fill="{KEY}">{USER}</tspan>'
        f'<tspan fill="{DIM}">@</tspan><tspan fill="{KEY}">{HOST}</tspan></text>'
    )
    y += line_h
    line(f'<text x="{key_x}" y="{y:.1f}" fill="{DIM}">{"-" * len(title)}</text>')
    y += line_h

    for key, val in lines:
        parts = []
        if key:
            parts.append(f'<text x="{key_x}" y="{y:.1f}" fill="{KEY}" font-weight="700">{escape(key)}</text>')
        parts.append(f'<text x="{val_x:.1f}" y="{y:.1f}" fill="{VAL}">{escape(val)}</text>')
        line("".join(parts))
        y += line_h

    y += 10
    sw = 22.0
    blocks = "".join(
        f'<rect x="{key_x + i * (sw + 4):.1f}" y="{y - fs + 2:.1f}" width="{sw}" height="14" rx="3" fill="{c}"/>'
        for i, c in enumerate(SWATCHES)
    )
    line(blocks)
    out.append("</g>")

    # Blinking prompt cursor after the last line — the one thing that keeps moving.
    cy = y + 6
    if not static:
        out.append(
            f'<rect x="{key_x + len(SWATCHES) * (sw + 4) + 6:.1f}" y="{cy - 14:.1f}" width="8" height="14" fill="{ACCENT}">'
            f'<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.5;0.5;1;1" dur="1.1s" '
            f'begin="{0.35 + n * 0.11:.2f}s" repeatCount="indefinite"/></rect>'
        )
    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--portrait", default="ascii-portrait.svg")
    ap.add_argument("--out", default="info-card.svg")
    args = ap.parse_args()

    svg = build(portrait_height(args.portrait), static=os.environ.get("STATIC") == "1")
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
