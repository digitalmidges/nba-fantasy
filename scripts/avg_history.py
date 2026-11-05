"""Avg Pts/Pos history for the Trends tab.

Avg Pts/Pos is season_points_TOT / GP, the same ratio as the Leaderboard.
The basketball PTS category is not used.

Dedupe
------
Each standings scrape is one point, stamped with scraped_at (not the filename).
Points are sorted oldest first.

Scrapes at least 30 minutes apart are both kept. That includes two refreshes on
the same calendar day when they are actually different samples (a morning
refresh and an after-games refresh, or a later scrape once more games are in).

Scrapes inside a 30-minute window are one refresh being written twice. The
later scraped_at replaces the earlier point. The window is anchored on the
earlier scrape, so a chain of updates does not collapse the whole history:
a point 32 minutes after the window opened is a new point even if it is only
a few minutes after the replacement.

A rebuild appends the current standings snapshot and merges it with this rule.
Older points are never dropped.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

WINDOW = timedelta(minutes=30)

DEDUPE_NOTE = (
    "One point per standings scrape, stamped with scraped_at. "
    "Scrapes at least 30 minutes apart are both kept, including two on the same calendar day. "
    "Scrapes inside 30 minutes of the earlier one are the same refresh: the later scraped_at replaces it. "
    "A rebuild appends the current standings snapshot and does not drop older points. "
    "avg is season_points_TOT / GP (not the basketball PTS category)."
)


def _stamp(at):
    return datetime.fromisoformat(at)


def point_from_standings(doc):
    at = doc.get("scraped_at")
    if not at:
        raise ValueError("standings snapshot has no scraped_at")
    _stamp(at)
    teams = []
    for team in doc.get("teams") or []:
        tot = team.get("season_points_TOT")
        gp = team.get("GP")
        if tot is None or not gp:
            continue
        tot = int(tot)
        gp = int(gp)
        teams.append({
            "team": team["team"],
            "avg": round(tot / gp, 4),
            "tot": tot,
            "gp": gp,
        })
    teams.sort(key=lambda row: row["team"].casefold())
    return {"at": at, "teams": teams}


def merge_points(points):
    """Sort by scraped_at and collapse scrapes inside the same 30-minute window."""
    ordered = sorted((p for p in points if p.get("at")), key=lambda p: _stamp(p["at"]))
    kept = []
    for point in ordered:
        stamp = _stamp(point["at"])
        if kept and stamp - kept[-1][0] < WINDOW:
            if stamp >= _stamp(kept[-1][1]["at"]):
                kept[-1] = (kept[-1][0], point)
            continue
        kept.append((stamp, point))
    return [point for _, point in kept]


def load_history(path):
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    return list(data.get("points") or [])


def history_document(points):
    return {
        "metric": "avg_pts_pos",
        "formula": "season_points_TOT / GP",
        "dedupe": DEDUPE_NOTE,
        "points": points,
    }


def save_history(path, points):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history_document(points), indent=1) + "\n")
    return history_document(points)


def append_standings(path, standings):
    """Merge one standings scrape into the history file. Does not wipe older points."""
    points = load_history(path)
    points.append(point_from_standings(standings))
    merged = merge_points(points)
    return save_history(path, merged)
