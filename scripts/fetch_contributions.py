"""Scrape the public contribution calendar (no token) into data/contributions.json.

GitHub serves the calendar as an HTML fragment at /users/<user>/contributions —
the same one the profile page uses. Each day is a <td data-date data-level>,
and its count lives in a matching <tool-tip for="<td id>">.

Usage:
    python scripts/fetch_contributions.py            # GH_USER env overrides the username
"""

import datetime as dt
import json
import os
import re
from collections import OrderedDict
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USER = os.environ.get("GH_USER", "Shiva085000")
URL = f"https://github.com/users/{USER}/contributions"
OUT = Path(__file__).resolve().parent.parent / "data" / "contributions.json"

COUNT_RE = re.compile(r"^([\d,]+) contributions?\b")


def fetch_days() -> list[dict]:
    resp = requests.get(URL, headers={"User-Agent": "profile-art-bot (+github.com/%s)" % USER}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    tips = {t["for"]: t.get_text(" ", strip=True) for t in soup.select("tool-tip[for]")}
    days = []
    for td in soup.select("td.ContributionCalendar-day[data-date]"):
        m = COUNT_RE.match(tips.get(td.get("id", ""), ""))
        days.append(
            {
                "date": td["data-date"],
                "count": int(m.group(1).replace(",", "")) if m else 0,
                "level": int(td.get("data-level", 0)),
            }
        )
    if not days:
        raise SystemExit(f"No calendar days found at {URL}; GitHub's markup may have changed.")
    days.sort(key=lambda d: d["date"])
    return days


def streaks(days: list[dict]) -> tuple[int, int]:
    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)
    # Current streak may end today or yesterday (today isn't over yet).
    current = 0
    tail = days[:-1] if days and days[-1]["count"] == 0 else days
    for d in reversed(tail):
        if d["count"] == 0:
            break
        current += 1
    return current, longest


def main() -> None:
    days = fetch_days()
    current, longest = streaks(days)
    best = max(days, key=lambda d: (d["count"], d["date"]))
    months: "OrderedDict[str, int]" = OrderedDict()
    for d in days:
        months[d["date"][:7]] = months.get(d["date"][:7], 0) + d["count"]

    data = {
        "user": USER,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "range": {"from": days[0]["date"], "to": days[-1]["date"]},
        "stats": {
            "total": sum(d["count"] for d in days),
            "active_days": sum(1 for d in days if d["count"] > 0),
            "current_streak": current,
            "longest_streak": longest,
            "best_day": {"date": best["date"], "count": best["count"]},
            "monthly": months,
        },
        "days": days,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1), encoding="utf-8")
    s = data["stats"]
    print(f"{USER}: {s['total']} contributions, {s['active_days']} active days, streak {current}/{longest}")


if __name__ == "__main__":
    main()
