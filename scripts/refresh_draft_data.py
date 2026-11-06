#!/usr/bin/env python3
"""Rebuild rosters_flat.json, free_agents.json, and draft_value.json from ESPN.

Workflow (daily / on demand)
----------------------------
1. While signed in to ESPN fantasy as a league member, open the league and save
   the mRoster API payload to data/raw/espn_mroster.json. Easiest from DevTools
   on a request like:
     .../apis/v3/games/fba/seasons/2027/segments/0/leagues/683874011?view=mRoster&view=mTeam
   Or paste the JSON the signed-in browser already fetched.
2. Run:
     python3 scripts/refresh_draft_data.py data/raw/espn_mroster.json
   Optional: --kona PATH to reuse a saved public player dump instead of fetching.
3. Then rebuild the site (from the publish clone):
     python3 scripts/build_index.py

The public kona_player_info endpoint (no auth) supplies season stats for
drafted players who were dropped and the free-agent pool. Rostered players
prefer ESPN's season appliedTotal from the mRoster file.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SEASON = 2027
SEASON_STAT_ID = f"00{SEASON}"  # "002027"

# ESPN default fantasy points (verified vs Wembanyama early-season line).
# Prefer appliedTotal from the league mRoster when present.
SCORE_WEIGHTS = {
    "0": 1,   # PTS
    "17": 1,  # 3PM
    "13": 2,  # FGM
    "14": -1, # FGA
    "15": 1,  # FTM
    "16": -1, # FTA
    "6": 1,   # REB
    "3": 2,   # AST
    "2": 4,   # STL
    "1": 4,   # BLK
    "9": -2,  # TO
}

PRO_TEAMS = {
    0: "FA",
    1: "ATL", 2: "BOS", 3: "NO", 4: "CHI", 5: "CLE", 6: "DAL", 7: "DEN",
    8: "DET", 9: "GS", 10: "HOU", 11: "IND", 12: "LAC", 13: "LAL", 14: "MIA",
    15: "MIL", 16: "MIN", 17: "BKN", 18: "NY", 19: "ORL", 20: "PHI", 21: "PHX",
    22: "POR", 23: "SAC", 24: "SA", 25: "OKC", 26: "UTAH", 27: "WSH", 28: "TOR",
    29: "MEM", 30: "CHA",
}

SLOT_POS = {0: "PG", 1: "SG", 2: "SF", 3: "PF", 4: "C"}
DEFAULT_POS = {1: "PG", 2: "SG", 3: "SF", 4: "PF", 5: "C"}

KONA_URL = (
    "https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/"
    f"{SEASON}/segments/0/leaguedefaults/1?view=kona_player_info"
)
KONA_FILTER = json.dumps(
    {"players": {"limit": 400, "sortPercOwned": {"sortPriority": 1, "sortAsc": False}}}
)

STAT_AVG_KEYS = {
    "MIN": "40",
    "FGM": "13",
    "FGA": "14",
    "FTM": "15",
    "FTA": "16",
    "3PM": "17",
    "REB": "6",
    "AST": "3",
    "STL": "2",
    "BLK": "1",
    "TO": "9",
    "PTS": "0",
}


def r1(x):
    if x is None:
        return None
    return round(float(x) + 0.0, 1)


def injury_code(status):
    if not status or status in ("ACTIVE", "NORMAL"):
        return None
    if status == "OUT":
        return "O"
    if status == "DAY_TO_DAY":
        return "DTD"
    return status


def eligible_str(player):
    slots = []
    seen = set()
    for s in player.get("eligibleSlots") or []:
        name = SLOT_POS.get(s)
        if name and name not in seen:
            seen.add(name)
            slots.append(name)
    default = DEFAULT_POS.get(player.get("defaultPositionId"))
    if default and default in slots:
        slots = [default] + [p for p in slots if p != default]
    elif default and not slots:
        slots = [default]
    return ", ".join(slots)


def season_split(player):
    for s in player.get("stats") or []:
        if s.get("id") == SEASON_STAT_ID:
            return s
    for s in player.get("stats") or []:
        if (
            s.get("statSourceId") == 0
            and s.get("statSplitTypeId") == 0
            and str(s.get("externalId")) == str(SEASON)
        ):
            return s
    return None


def formula_fpts(stats):
    if not stats:
        return None
    total = 0.0
    any_stat = False
    for k, w in SCORE_WEIGHTS.items():
        if k in stats and stats[k] is not None:
            total += w * float(stats[k])
            any_stat = True
    return total if any_stat else None


def gp_from_split(split):
    if not split:
        return None
    stats = split.get("stats") or {}
    for key in ("42", "41"):
        v = stats.get(key)
        if v:
            return int(round(float(v)))
    applied = split.get("appliedTotal")
    avg = split.get("appliedAverage")
    if applied and avg:
        return max(1, int(round(float(applied) / float(avg))))
    return None


def box_averages(split):
    out = {k: None for k in STAT_AVG_KEYS}
    if not split:
        return out
    avg = split.get("averageStats") or {}
    totals = split.get("stats") or {}
    gp = gp_from_split(split)
    for name, key in STAT_AVG_KEYS.items():
        if key in avg and avg[key] is not None:
            out[name] = r1(avg[key])
        elif gp and key in totals and totals[key] is not None:
            out[name] = r1(float(totals[key]) / gp)
        # ESPN sometimes puts per-game values in the totals map under 28/29/...;
        # MIN also appears as 40 in both maps.
    return out


def fpts_from_split(split, prefer_applied=True):
    if not split:
        return None, None
    applied = split.get("appliedTotal")
    applied_avg = split.get("appliedAverage")
    stats = split.get("stats") or {}
    calc = formula_fpts(stats)
    gp = gp_from_split(split)

    if prefer_applied and applied is not None:
        tot = r1(applied)
        if applied_avg is not None:
            avg = r1(applied_avg)
        elif gp:
            avg = r1(float(applied) / gp)
        else:
            avg = None
        # Sanity: large drift from formula is logged by caller if needed.
        return tot, avg

    if calc is None:
        return None, None
    tot = r1(calc)
    avg = r1(calc / gp) if gp else None
    return tot, avg


def ownership(player):
    own = player.get("ownership") or {}
    pct = own.get("percentOwned")
    chg = own.get("percentChange")
    return (r1(pct) if pct is not None else None, r1(chg) if chg is not None else None)


def fetch_kona(path: Path | None):
    if path and path.exists():
        return json.loads(path.read_text())
    req = urllib.request.Request(
        KONA_URL,
        headers={
            "x-fantasy-filter": KONA_FILTER,
            "User-Agent": "Mozilla/5.0 barchashim-draft-refresh",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    out = DATA / "raw" / "espn_kona_players.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data))
    return data


def index_kona(kona):
    by_name = {}
    by_id = {}
    for entry in kona.get("players") or []:
        pl = entry.get("player") or {}
        name = pl.get("fullName")
        if name:
            by_name[name] = (entry, pl)
        if pl.get("id") is not None:
            by_id[pl["id"]] = (entry, pl)
    return by_name, by_id


def player_row_from_espn(player, *, fantasy_team, draft_pick, draft_round, drafted_by, prefer_applied):
    split = season_split(player)
    box = box_averages(split)
    fpts_tot, fpts_avg = fpts_from_split(split, prefer_applied=prefer_applied)
    pct_rostered, pct_change = ownership(player)
    return {
        "player": player.get("fullName"),
        "nba_team": PRO_TEAMS.get(player.get("proTeamId"), "FA"),
        "eligible": eligible_str(player),
        "fantasy_team": fantasy_team,
        "draft_pick": draft_pick,
        "draft_round": draft_round,
        "drafted_by": drafted_by,
        **box,
        "pct_rostered": pct_rostered,
        "pct_change": pct_change,
        "fpts_tot": fpts_tot,
        "fpts_avg": fpts_avg,
        "injury": injury_code(player.get("injuryStatus")),
    }


def fa_row_from_espn(player, rank):
    split = season_split(player)
    box = box_averages(split)
    # Public leaguedefaults feed has no appliedTotal — use formula.
    fpts_tot, fpts_avg = fpts_from_split(split, prefer_applied=False)
    pct_rostered, pct_change = ownership(player)
    return {
        "rank_by_pct_rostered": rank,
        "player": player.get("fullName"),
        "injury": injury_code(player.get("injuryStatus")),
        "nba_team": PRO_TEAMS.get(player.get("proTeamId"), "FA"),
        "position": eligible_str(player),
        "status": "FA",
        **box,
        "pct_rostered": pct_rostered,
        "pct_change": pct_change,
        "fpts_tot": fpts_tot,
        "fpts_avg": fpts_avg,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mroster", type=Path, help="Path to espn_mroster.json (view=mRoster&view=mTeam)")
    ap.add_argument("--kona", type=Path, default=None, help="Optional saved kona_player_info JSON")
    ap.add_argument("--skip-draft-value", action="store_true", help="Only rebuild roster/FA files")
    args = ap.parse_args()

    draft = json.loads((DATA / "draft.json").read_text())
    dmap = {p["player"]: p for p in draft["picks"]}
    mroster = json.loads(args.mroster.read_text())
    kona = fetch_kona(args.kona)
    kona_by_name, _ = index_kona(kona)

    # Team names on mRoster already match draft.json (e.g. Team The Mushroom).
    team_names = {t["id"]: t["name"] for t in mroster.get("teams") or []}

    ros = []
    rostered_names = set()
    for t in mroster.get("teams") or []:
        fantasy_team = t.get("name") or team_names.get(t["id"])
        for e in (t.get("roster") or {}).get("entries") or []:
            ppe = e.get("playerPoolEntry") or {}
            pl = ppe.get("player") or {}
            name = pl.get("fullName")
            if not name:
                continue
            rostered_names.add(name)
            d = dmap.get(name)
            row = player_row_from_espn(
                pl,
                fantasy_team=fantasy_team,
                draft_pick=d["pick"] if d else None,
                draft_round=d["round"] if d else None,
                drafted_by=d["team"] if d else None,
                prefer_applied=True,
            )
            # Keep schema of rosters_flat (no injury key historically); draft_value uses .get
            # Include injury only when set so FA-style lookups still work via .get
            row.pop("injury", None)  # rosters_flat schema has no injury field
            ros.append(row)

    # Free agents: not currently rostered, ranked by % owned. Always include
    # every dropped drafted player even if ownership is low / outside top 400.
    fa_candidates = []
    for name, (entry, pl) in kona_by_name.items():
        if name in rostered_names:
            continue
        fa_candidates.append(pl)

    # Ensure dropped draftees are present even if missing from the 400 cap.
    for name in dmap:
        if name not in rostered_names and name not in {p.get("fullName") for p in fa_candidates}:
            # Should be rare; try kona again by scanning (already covered).
            pass

    fa_candidates.sort(
        key=lambda pl: -((pl.get("ownership") or {}).get("percentOwned") or 0)
    )

    # Keep a pool similar to the old FA page (~70+) but large enough for drops.
    fa = []
    seen = set()
    for pl in fa_candidates:
        name = pl.get("fullName")
        if not name or name in seen:
            continue
        seen.add(name)
        fa.append(fa_row_from_espn(pl, len(fa) + 1))
        if len(fa) >= 120:
            break

    # Force-include any dropped draftee not already in FA list.
    for name, d in dmap.items():
        if name in rostered_names or name in seen:
            continue
        pl = (kona_by_name.get(name) or (None, None))[1]
        if not pl:
            print(f"warning: dropped draftee {name!r} missing from kona feed", file=sys.stderr)
            continue
        fa.append(fa_row_from_espn(pl, len(fa) + 1))
        seen.add(name)

    # Drop injury:null-less consistency for FA — keep injury key always (old schema).
    for row in fa:
        if "injury" not in row:
            row["injury"] = None

    (DATA / "rosters_flat.json").write_text(json.dumps(ros, indent=1) + "\n")
    by_team = {}
    for r in ros:
        by_team.setdefault(r["fantasy_team"], []).append(
            {k: v for k, v in r.items() if k != "injury" or v is not None}
        )
    # Strip injury from nested rosters.json to match prior schema
    clean_by_team = {
        team: [{k: v for k, v in p.items() if k != "injury"} for p in players]
        for team, players in by_team.items()
    }
    (DATA / "rosters.json").write_text(json.dumps(clean_by_team, indent=1) + "\n")
    (DATA / "free_agents.json").write_text(json.dumps(fa, indent=1) + "\n")

    dropped = sorted(set(dmap) - rostered_names)
    print(f"rosters {len(ros)} across {len(clean_by_team)} teams; FA {len(fa)}; dropped draftees {len(dropped)}")
    if dropped:
        print("dropped:", ", ".join(dropped))

    if not args.skip_draft_value:
        dv_script = ROOT / "scripts" / "draft_value.py"
        subprocess.check_call([sys.executable, str(dv_script)], cwd=str(ROOT))


if __name__ == "__main__":
    main()
