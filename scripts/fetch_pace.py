"""Pull per-position games used from ESPN, then write data/pace.json.

The Barchashim league API is private. Without espn_s2 and SWID (or ESPN_COOKIE)
the request returns 401 and the file falls back to standings GP versus the
819-game sum of the position caps. Daily standings refreshes still move that
total, because build_index.py rebuilds pace from data/standings.json.

Cookie env, when the bot has a logged-in session:
  ESPN_S2, SWID
  or ESPN_COOKIE as a full Cookie header value
"""

from __future__ import annotations

import json
import os
import pathlib
import urllib.error
import urllib.request

from pace_lib import LEAGUE_ID, SEASON, build_pace, fetch_game_days, slots_from_league

ROOT = pathlib.Path(__file__).resolve().parent.parent
STANDINGS = ROOT / "data" / "standings.json"
OUT = ROOT / "data" / "pace.json"
API = (
    "https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/%d/segments/0/leagues/%d"
    % (SEASON, LEAGUE_ID)
)
VIEW_SETS = (
    ("mSettings", "mTeam", "mRoster", "mMatchupScore", "mSchedule", "mStatus"),
    ("mSettings", "mTeam", "mMatchup"),
    ("mSettings", "mTeam", "mSchedule"),
)


def cookie_header():
    raw = os.environ.get("ESPN_COOKIE")
    if raw:
        return raw
    s2 = os.environ.get("ESPN_S2")
    swid = os.environ.get("SWID")
    if s2 and swid:
        return "espn_s2=%s; SWID=%s" % (s2, swid)
    return None


def fetch_league(timeout=25):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "x-fantasy-platform": "kona",
        "Referer": "https://fantasy.espn.com/basketball/league?leagueId=%d" % LEAGUE_ID,
    }
    cookie = cookie_header()
    if cookie:
        headers["Cookie"] = cookie
    last_error = "ESPN league API was not reached"
    for views in VIEW_SETS:
        url = API + "?" + "&".join("view=%s" % v for v in views)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.load(resp)
        except urllib.error.HTTPError as err:
            detail = ""
            try:
                body = json.loads(err.read().decode("utf-8", "replace"))
                detail = (body.get("messages") or [""])[0]
            except Exception:
                detail = str(err)
            last_error = "ESPN league API HTTP %s (%s)" % (err.code, detail or err.reason)
            if err.code in (401, 403):
                return None, last_error
            continue
        except Exception as err:
            last_error = "ESPN league API request failed (%s)" % err.__class__.__name__
            continue
        if isinstance(payload, dict) and payload.get("messages"):
            last_error = payload["messages"][0]
            continue
        return payload, ""
    return None, last_error


def load_standings():
    return json.load(open(STANDINGS))


def build_from_standings(standings=None, network_calendar=True):
    standings = standings if standings is not None else load_standings()
    slots, limits, note = None, None, None
    payload, error = fetch_league()
    if payload:
        slots, limits, scoring = slots_from_league(payload)
        if slots:
            note = "Per-position games are the ones ESPN has counted in each capped slot"
            if scoring:
                note += " (%s)" % scoring.replace("_", " ").title()
            note += "."
        else:
            note = (
                "ESPN returned the league, but no per-position games-played counters were on the schedule. "
                + "Each bar is the team's total games played against 819, the sum of the position caps."
            )
            slots, limits = None, None
    else:
        print("espn pace unavailable:", error)
        note = None
    if network_calendar:
        days, source = fetch_game_days()
    else:
        days, source = None, None
    pace = build_pace(
        standings,
        slots_by_team=slots,
        limits=limits,
        breakdown_note=note,
        game_days=days,
        progress_source=source,
    )
    return pace


def main():
    pace = build_from_standings()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(pace, open(OUT, "w"), indent=1)
    print(
        "pace",
        pace["breakdown"],
        "teams",
        len(pace["teams"]),
        "as_of",
        pace["progress"]["as_of"],
        "days",
        "%d/%d" % (pace["progress"]["game_days_complete"], pace["progress"]["game_days_total"]),
    )
    return pace


if __name__ == "__main__":
    main()
