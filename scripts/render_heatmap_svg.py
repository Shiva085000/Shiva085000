"""Render data/contributions.json as an animated 53-week contribution heatmap SVG.

Boxes slide down into place along a diagonal sweep once on load, then freeze.
The palette is the portfolio's lime instead of GitHub green; level 5 is a
bright top end for the busiest days. Set STATIC=1 for a frozen frame.

Usage:
    python scripts/render_heatmap_svg.py [--out contrib-heatmap.svg]
"""

import argparse
import datetime as dt
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "contributions.json"

PALETTE = ["#161b22", "#2a3a13", "#4a6b17", "#7aa51f", "#c6f432", "#eaff8f"]
# none -> brightest (level 5 marks the top days)

FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
BG = "#0d1117"
BORDER = "#30363d"
TEXT = "#d0d3da"
DIM = "#8b949e"
LIME = "#C6F432"

WIDTH = 860.0
CELL = 11.0
GAP = 3.0
STEP = CELL + GAP
BAR_H = 34.0
LABEL_W = 30.0
TOP = BAR_H + 52.0  # room for the stats headline and month labels


def fmt_day(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return f"{d.strftime('%b')} {d.day}"


def build(data: dict, static: bool) -> str:
    days = data["days"]
    s = data["stats"]

    # Level 5: the busiest days (top 5% of active days, at least the single best day).
    active = sorted((d["count"] for d in days if d["count"] > 0), reverse=True)
    cutoff = active[max(0, int(len(active) * 0.05) - 1)] if active else None

    first = dt.date.fromisoformat(days[0]["date"])
    start_sunday = first - dt.timedelta(days=(first.weekday() + 1) % 7)
    cells = []
    for d in days:
        date = dt.date.fromisoformat(d["date"])
        week = (date - start_sunday).days // 7
        dow = (date.weekday() + 1) % 7  # Sunday = 0
        level = d["level"]
        if cutoff is not None and level == 4 and d["count"] >= cutoff:
            level = 5
        cells.append((week, dow, level, date))

    weeks = max(c[0] for c in cells) + 1
    grid_w = weeks * STEP - GAP
    left = (WIDTH - grid_w - LABEL_W) / 2 + LABEL_W
    height = TOP + 7 * STEP - GAP + 58

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH:.0f} {height:.0f}" width="{WIDTH:.0f}" '
        f'height="{height:.0f}" role="img" aria-label="{s["total"]} GitHub contributions in the last year">',
    ]
    if not static:
        out.append(
            "<style>"
            ".c{opacity:0;animation:drop .55s cubic-bezier(.22,1,.36,1) forwards}"
            "@keyframes drop{from{opacity:0;transform:translateY(-7px)}to{opacity:1;transform:translateY(0)}}"
            ".f{opacity:0;animation:fade .6s ease forwards}"
            "@keyframes fade{to{opacity:1}}"
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
        f'font-size="11" fill="{DIM}">contributions.sh — github.com/{data["user"]}</text>'
    )

    out.append(f'<g font-family="{FONT}">')
    # Headline
    out.append(
        f'<text x="{left - LABEL_W:.1f}" y="{BAR_H + 26}" font-size="14" fill="{TEXT}">'
        f'<tspan fill="{LIME}" font-weight="700">{s["total"]:,}</tspan> contributions in the last year</text>'
    )
    out.append(
        f'<text x="{left + grid_w:.1f}" y="{BAR_H + 26}" font-size="11" fill="{DIM}" text-anchor="end">'
        f'{fmt_day(data["range"]["from"])}, {data["range"]["from"][:4]} → {fmt_day(data["range"]["to"])}, {data["range"]["to"][:4]}</text>'
    )

    # Month labels at the first week that contains the 1st of a month.
    last_label_week = -10
    for week, dow, _, date in cells:
        if date.day == 1 and week - last_label_week >= 3 and week < weeks - 1:
            out.append(
                f'<text x="{left + week * STEP:.1f}" y="{TOP - 8}" font-size="10" fill="{DIM}">{date.strftime("%b")}</text>'
            )
            last_label_week = week
    for dow, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(
            f'<text x="{left - 8:.1f}" y="{TOP + dow * STEP + CELL - 2:.1f}" font-size="9" fill="{DIM}" text-anchor="end">{name}</text>'
        )

    for week, dow, level, _ in cells:
        x = left + week * STEP
        y = TOP + dow * STEP
        stroke = f' stroke="{PALETTE[5]}" stroke-opacity="0.6"' if level == 5 else ""
        anim = "" if static else f' class="c" style="animation-delay:{0.25 + (week + dow) * 0.013:.3f}s"'
        out.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="2.5" fill="{PALETTE[level]}"{stroke}{anim}/>'
        )

    # Footer: stats on the left, legend on the right.
    fy = TOP + 7 * STEP - GAP + 30
    footer_delay = 0.25 + (weeks + 6) * 0.013
    fcls = "" if static else f' class="f" style="animation-delay:{footer_delay:.2f}s"'
    best = s["best_day"]
    stats = [
        ("current streak", f'{s["current_streak"]}d'),
        ("longest streak", f'{s["longest_streak"]}d'),
        ("active days", str(s["active_days"])),
        ("best day", f'{best["count"]} on {fmt_day(best["date"])}' if best["count"] else "—"),
    ]
    out.append(f"<g{fcls}>")
    x = left - LABEL_W
    parts = []
    for k, v in stats:
        parts.append(f'<tspan fill="{DIM}">{k} </tspan><tspan fill="{TEXT}" font-weight="700">{v}</tspan>')
    sep = f'<tspan fill="{BORDER}">  │  </tspan>'
    out.append(f'<text x="{x:.1f}" y="{fy}" font-size="11" xml:space="preserve">{sep.join(parts)}</text>')

    right = left + grid_w
    out.append(f'<text x="{right:.1f}" y="{fy}" font-size="10" fill="{DIM}" text-anchor="end">More</text>')
    lx = right - 34 - (len(PALETTE) * STEP - GAP)
    for i, c in enumerate(PALETTE):
        out.append(f'<rect x="{lx + i * STEP:.1f}" y="{fy - CELL + 1:.1f}" width="{CELL}" height="{CELL}" rx="2.5" fill="{c}"/>')
    out.append(f'<text x="{lx - 8:.1f}" y="{fy}" font-size="10" fill="{DIM}" text-anchor="end">Less</text>')
    out.append("</g>")

    out.append("</g></svg>")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "contrib-heatmap.svg"))
    args = ap.parse_args()
    data = json.loads(DATA.read_text(encoding="utf-8"))
    svg = build(data, static=os.environ.get("STATIC") == "1")
    Path(args.out).write_text(svg, encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
