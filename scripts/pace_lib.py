"""Games-played pace for Barchashim League.

ESPN caps each starter slot separately (verified 2026-10-31):
PG, SG, SF, PF, C, G, F at 82 games, and Util at 245 for the three Util spots.
There is no extra league-wide cap. 82*7 + 245 = 819.

Per-position games used live on the fantasy API as
schedule[].teams[].cumulativeScore.statBySlot for a Total Season Points league
(not an H2H league). Stat id 42 is games played. The public standings scrape only
has the team total, so the page falls back to that total versus 819 when the
league API does not return slot counters.

Calendar pace uses NBA regular-season days that actually have games, from the
ESPN on-days calendar for season 2027: 2026-10-20 through 2027-04-11, skipping
dark dates (including the All-Star break). A day counts as complete when it is
on or before the standings snapshot date.
"""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import date, datetime, timedelta

LEAGUE_ID = 683874011
SEASON = 2027
GP_STAT_ID = 42
SEASON_START = date(2026, 10, 20)
SEASON_END = date(2027, 4, 11)  # inclusive last regular-season game day
# Dark dates inside the regular-season window (ESPN on-days, fetched 2026-10-31).
BAKED_OFF_DAYS = {
    date(2026, 11, 3),
    date(2026, 11, 26),
    date(2026, 12, 6),
    date(2026, 12, 7),
    date(2026, 12, 9),
    date(2026, 12, 10),
    date(2026, 12, 24),
    date(2027, 2, 19),
    date(2027, 2, 20),
    date(2027, 2, 21),
    date(2027, 2, 22),
    date(2027, 2, 23),
    date(2027, 2, 24),
    date(2027, 4, 10),
}
# Year-end projection / cap. Over the cap means the burn rate hits the maximum
# before the season ends. Well under means games would be left unused.
BURN_RATIO = 1.08
UNDER_RATIO = 0.85

POSITIONS = [
    {"slot": 0, "id": "PG", "name": "Point Guard", "max": 82},
    {"slot": 1, "id": "SG", "name": "Shooting Guard", "max": 82},
    {"slot": 2, "id": "SF", "name": "Small Forward", "max": 82},
    {"slot": 3, "id": "PF", "name": "Power Forward", "max": 82},
    {"slot": 4, "id": "C", "name": "Center", "max": 82},
    {"slot": 5, "id": "G", "name": "Guard", "max": 82},
    {"slot": 6, "id": "F", "name": "Forward", "max": 82},
    {"slot": 11, "id": "UTIL", "name": "Util", "max": 245},
]
H2H_SCORING = {"H2H_POINTS", "H2H_CATEGORY", "H2H_MOST_CATEGORIES"}
TOTAL_NOTE = (
    "Per-position games used are not in this refresh. The ESPN roster is private, so each bar "
    "is the team's total games played (the same number as the Leaderboard) against 819, the sum "
    "of the eight caps. Slot-by-slot bars replace this total when a refresh can read the league."
)
SHORT_STATUS = {
    "burning": "Burning fast",
    "under": "Leaving games",
    "onpace": "On pace",
}


def total_cap(positions=None):
    return sum(p["max"] for p in (positions or POSITIONS))


def pretty_date(d):
    return d.strftime("%b %-d, %Y")


def snapshot_date(scraped_at):
    if not scraped_at:
        return date.today()
    return datetime.fromisoformat(scraped_at).date()


def baked_game_days():
    days = []
    d = SEASON_START
    while d <= SEASON_END:
        if d not in BAKED_OFF_DAYS:
            days.append(d)
        d += timedelta(days=1)
    return days


def fetch_game_days(timeout=15):
    """NBA regular-season dates that have games. Falls back to the baked list."""
    url = (
        "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/"
        "calendar/ondays?season=%d" % SEASON
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.load(resp)
        raw = payload.get("eventDate", {}).get("dates") or []
        days = []
        for stamp in raw:
            d = datetime.fromisoformat(stamp.replace("Z", "+00:00")).date()
            if SEASON_START <= d <= SEASON_END:
                days.append(d)
        days = sorted(set(days))
        if 140 <= len(days) <= 180 and days[0] == SEASON_START:
            return days, "ESPN NBA regular-season on-days, season %d" % SEASON
    except Exception:
        pass
    return baked_game_days(), "ESPN NBA regular-season on-days, season %d (saved calendar)" % SEASON


def season_progress(as_of, game_days=None, source=None):
    days = list(game_days) if game_days is not None else baked_game_days()
    if not days:
        fraction = 0.0
        done = 0
    elif as_of >= days[-1]:
        done = len(days)
        fraction = 1.0
    else:
        done = sum(1 for d in days if d <= as_of)
        fraction = done / len(days)
    pct = round(fraction * 100, 1)
    sentence = (
        "As of %s, %d of %d NBA game days are done (%s%% of the regular season, %s through %s). "
        "Dark dates, including the All-Star break, are not counted. "
        "The year-end number assumes this burn rate holds, so it will swing early in the season."
        % (pretty_date(as_of), done, len(days), pct, pretty_date(SEASON_START), pretty_date(SEASON_END))
    )
    return {
        "start": SEASON_START.isoformat(),
        "end": SEASON_END.isoformat(),
        "as_of": as_of.isoformat(),
        "game_days_total": len(days),
        "game_days_complete": done,
        "fraction": fraction,
        "source": source or "ESPN NBA regular-season on-days, season %d (saved calendar)" % SEASON,
        "sentence": sentence,
    }


def pace_flag(used, cap, fraction):
    if not cap or fraction <= 0:
        return "onpace"
    projected = used / fraction
    ratio = projected / cap
    if ratio >= BURN_RATIO:
        return "burning"
    if ratio <= UNDER_RATIO:
        return "under"
    return "onpace"


def describe(flag, ahead):
    if flag == "burning":
        return "Ahead of pace · burning fast, may run dry"
    if flag == "under":
        return "Behind pace · underusing slots, leaving games on the table"
    if ahead >= 1:
        return "On pace · slightly ahead of the calendar"
    if ahead <= -1:
        return "On pace · slightly behind the calendar"
    return "On pace"


def _round1(n):
    return round(n, 1)


def slot_row(slot_id, name, used, cap, fraction):
    used_n = float(used or 0)
    cap_n = float(cap or 0)
    expected = cap_n * fraction
    ahead = used_n - expected
    projected = round(used_n / fraction) if fraction > 0 else None
    flag = pace_flag(used_n, cap_n, fraction)
    remaining = cap_n - used_n
    pct = round(100.0 * used_n / cap_n, 1) if cap_n else 0.0
    return {
        "id": slot_id,
        "name": name,
        "used": int(round(used_n)),
        "max": int(round(cap_n)),
        "remaining": int(round(remaining)),
        "pct": pct,
        "expected": _round1(expected),
        "ahead": _round1(ahead),
        "projected": projected,
        "flag": flag,
        "status": describe(flag, ahead),
        "short": SHORT_STATUS[flag],
    }


def positions_with_caps(limits):
    rows = []
    for p in POSITIONS:
        cap = p["max"]
        if limits and p["slot"] in limits:
            cap = limits[p["slot"]]
        rows.append({"slot": p["slot"], "id": p["id"], "name": p["name"], "max": int(round(cap))})
    return rows


def _norm(name):
    return re.sub(r"\s+", " ", (name or "").strip()).casefold()


def team_view(name, owner, used, cap, fraction, slots, gp_standings):
    row_slots = slots or []
    flag = pace_flag(used, cap, fraction)
    expected = cap * fraction
    ahead = used - expected
    return {
        "team": name,
        "owner": owner or "",
        "gp": int(round(used)),
        "gp_standings": None if gp_standings is None else int(gp_standings),
        "cap": int(round(cap)),
        "remaining": int(round(cap - used)),
        "pct": round(100.0 * used / cap, 1) if cap else 0.0,
        "expected": _round1(expected),
        "ahead": _round1(ahead),
        "projected": round(used / fraction) if fraction > 0 else None,
        "flag": flag,
        "status": describe(flag, ahead),
        "short": SHORT_STATUS[flag],
        "slots": row_slots,
    }


def build_pace(standings, slots_by_team=None, limits=None, breakdown_note=None, game_days=None, progress_source=None):
    """Build the Pace payload.

    slots_by_team maps a normalized team name to {slot_id: games_used}.
    limits maps slot id to the cap. Missing limits use the verified defaults.
    """
    as_of = snapshot_date(standings.get("scraped_at"))
    progress = season_progress(as_of, game_days=game_days, source=progress_source)
    fraction = progress["fraction"]
    caps = positions_with_caps(limits)
    cap_sum = sum(p["max"] for p in caps)
    by_norm = slots_by_team or {}
    teams_in = standings.get("teams") or []
    use_slots = bool(by_norm) and all(_norm(t.get("team")) in by_norm for t in teams_in)
    rows = []
    for t in teams_in:
        name = t.get("team") or ""
        owner = t.get("owner") or ""
        gp = int(t.get("GP") or 0)
        if use_slots:
            raw = by_norm[_norm(name)]
            slot_rows = []
            for p in caps:
                used = raw.get(p["slot"], 0) or 0
                slot_rows.append(slot_row(p["id"], p["name"], used, p["max"], fraction))
            used_total = sum(s["used"] for s in slot_rows)
            rows.append(team_view(name, owner, used_total, cap_sum, fraction, slot_rows, gp))
        else:
            only = [slot_row("ALL", "All capped slots", gp, cap_sum, fraction)]
            rows.append(team_view(name, owner, gp, cap_sum, fraction, only, gp))
    rows.sort(key=lambda r: (-r["ahead"], r["team"].casefold()))
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
    if use_slots:
        note = breakdown_note or ""
        mismatched = [
            r["team"] for r in rows
            if r["gp_standings"] is not None and abs(r["gp"] - r["gp_standings"]) > 2
        ]
        if mismatched:
            extra = (
                "Slot totals differ from standings GP for %s. The bars use games ESPN counted in each capped slot."
                % ", ".join(mismatched)
            )
            note = (note + " " + extra).strip()
        breakdown = "position"
    else:
        note = breakdown_note or TOTAL_NOTE
        breakdown = "total"
    return {
        "league_id": LEAGUE_ID,
        "season": standings.get("season") or SEASON,
        "breakdown": breakdown,
        "sort": "Furthest ahead of the NBA calendar first (games used minus the share of the cap the calendar says should be spent by now). Ties break by team name.",
        "thresholds": {
            "burning_projected_over_cap": BURN_RATIO,
            "under_projected_under_cap": UNDER_RATIO,
        },
        "progress": progress,
        "caps": [{"id": p["id"], "name": p["name"], "max": p["max"]} for p in caps],
        "total_cap": cap_sum,
        "note": note,
        "teams": rows,
    }


def parse_limit_value(value, stat_id=GP_STAT_ID):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if not isinstance(value, dict):
        return None
    if "limitValue" in value or "maximum" in value or "max" in value:
        sid = value.get("statId", stat_id)
        try:
            if int(sid) != stat_id:
                return None
        except (TypeError, ValueError):
            return None
        raw = value.get("limitValue", value.get("maximum", value.get("max")))
        return None if raw is None else float(raw)
    for key, inner in value.items():
        try:
            if int(key) != stat_id:
                continue
        except (TypeError, ValueError):
            continue
        return parse_limit_value(inner, stat_id)
    return None


def limits_from_settings(settings):
    raw = ((settings or {}).get("rosterSettings") or {}).get("lineupSlotStatLimits") or {}
    out = {}
    if not isinstance(raw, dict):
        return out
    for key, value in raw.items():
        try:
            slot = int(key)
        except (TypeError, ValueError):
            continue
        cap = parse_limit_value(value)
        if cap is not None and cap > 0:
            out[slot] = cap
    return out


def parse_stat_value(entry, stat_id=GP_STAT_ID):
    if entry is None or isinstance(entry, bool):
        return None
    if isinstance(entry, (int, float)):
        return float(entry)
    if isinstance(entry, list):
        for item in entry:
            found = parse_stat_value(item, stat_id)
            if found is not None:
                return found
        return None
    if isinstance(entry, dict):
        if "value" in entry:
            sid = entry.get("statId")
            if sid is not None:
                try:
                    if int(sid) != stat_id:
                        return None
                except (TypeError, ValueError):
                    return None
            return float(entry["value"])
        for key in (str(stat_id), "score"):
            if key in entry and isinstance(entry[key], (int, float)) and not isinstance(entry[key], bool):
                return float(entry[key])
    return None


def _team_label(team):
    name = (team.get("name") or "").strip()
    if name:
        return name
    return ("%s %s" % (team.get("location") or "", team.get("nickname") or "")).strip()


def _slot_map_from_team_entry(entry):
    raw = ((entry or {}).get("cumulativeScore") or {}).get("statBySlot") or {}
    if not isinstance(raw, dict) or not raw:
        return {}
    out = {}
    for key, value in raw.items():
        try:
            slot = int(key)
        except (TypeError, ValueError):
            continue
        parsed = parse_stat_value(value)
        if parsed is None:
            continue
        out[slot] = parsed
    return out


def slots_from_league(payload):
    """Return (slots_by_norm_name, limits, scoring_type) from an ESPN league payload.

    For Total Season Points, ESPN keeps season slot usage on the schedule entry's
    teams[].cumulativeScore.statBySlot (the client reads schedule[0] when the
    league is not H2H). H2H leagues store the same object on the current matchup.
    """
    if not isinstance(payload, dict) or payload.get("messages"):
        return {}, {}, ""
    settings = payload.get("settings") or {}
    scoring = ((settings.get("scoringSettings") or {}).get("scoringType") or "")
    is_h2h = scoring in H2H_SCORING
    limits = limits_from_settings(settings)
    schedule = payload.get("schedule") or []
    by_id = {}

    def consider(entry):
        if not entry or entry.get("teamId") is None:
            return
        found = _slot_map_from_team_entry(entry)
        if not found:
            return
        tid = entry["teamId"]
        total = sum(found.values())
        prev = by_id.get(tid)
        if prev is None or total > prev[0]:
            by_id[tid] = (total, found)

    if not is_h2h and schedule:
        for entry in schedule[0].get("teams") or []:
            consider(entry)
    if not by_id:
        for match in schedule:
            for entry in match.get("teams") or []:
                consider(entry)
            for side in ("home", "away"):
                consider(match.get(side))
    if not by_id:
        for team in payload.get("teams") or []:
            consider({"teamId": team.get("id"), "cumulativeScore": team.get("cumulativeScore")})

    names = {}
    for team in payload.get("teams") or []:
        label = _team_label(team)
        found = by_id.get(team.get("id"))
        if label and found:
            names[_norm(label)] = found[1]
    return names, limits, scoring
