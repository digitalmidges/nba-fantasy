"""Pace math and ESPN slot parsing. Run: python3 scripts/test_pace.py"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from pace_lib import (  # noqa: E402
    BAKED_OFF_DAYS,
    SEASON_END,
    SEASON_START,
    baked_game_days,
    build_pace,
    slots_from_league,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_calendar():
    days = baked_game_days()
    assert len(days) == 160, len(days)
    assert days[0] == SEASON_START
    assert days[-1] == SEASON_END
    assert len(BAKED_OFF_DAYS) == 14
    from datetime import date
    assert date(2026, 10, 31) in days
    assert date(2027, 2, 20) not in days
    assert date(2027, 4, 10) not in days


def test_standings_order_and_flags():
    standings = json.load(open(ROOT / "data" / "standings.json"))
    pace = build_pace(standings, game_days=baked_game_days(), progress_source="test")
    assert pace["breakdown"] == "total"
    assert pace["total_cap"] == 819
    assert pace["progress"]["as_of"] == "2026-10-30"
    assert pace["progress"]["game_days_complete"] == 11
    assert pace["progress"]["game_days_total"] == 160
    names = [t["team"] for t in pace["teams"]]
    assert names[0] == "Naim Merlon"
    assert names[1] == "The Pigs orsurf"
    # Same games ahead: alphabetical, and not pinned to Team The Mushroom.
    assert names.index("DanKen") < names.index("Team The Mushroom")
    assert pace["teams"][0]["flag"] == "burning"
    assert pace["teams"][0]["gp"] == 67
    assert pace["teams"][0]["projected"] == 975
    assert pace["teams"][-1]["team"] == "Omer's Team"
    assert pace["teams"][-1]["flag"] == "onpace"
    assert all(t["slots"][0]["id"] == "ALL" for t in pace["teams"])
    assert "819" in pace["note"]
    assert not any(t["team"] == "Team The Mushroom" and t["rank"] == 1 for t in pace["teams"])


def test_position_parse_and_caps():
    limits = {}
    stat = {}
    for slot, cap, used in (
        (0, 82, 9),
        (1, 82, 8),
        (2, 82, 7),
        (3, 82, 6),
        (4, 82, 10),
        (5, 82, 4),
        (6, 82, 5),
        (11, 245, 18),
    ):
        limits[str(slot)] = {"statId": 42, "limitValue": cap}
        stat[str(slot)] = {"statId": 42, "value": used, "limitExceeded": False}
    payload = {
        "settings": {
            "scoringSettings": {"scoringType": "TOTAL_SEASON_POINTS"},
            "rosterSettings": {"lineupSlotStatLimits": limits},
        },
        "teams": [{"id": 1, "name": "Naim Merlon", "owners": []}],
        "schedule": [
            {
                "matchupPeriodId": 1,
                "teams": [{"teamId": 1, "cumulativeScore": {"statBySlot": stat}}],
            }
        ],
    }
    slots, parsed_limits, scoring = slots_from_league(payload)
    assert scoring == "TOTAL_SEASON_POINTS"
    assert parsed_limits[11] == 245
    assert slots["naim merlon"][0] == 9
    standings = {
        "scraped_at": "2026-10-30T23:54:08-05:00",
        "season": 2027,
        "teams": [{"team": "Naim Merlon", "owner": "Meir Naim", "GP": 67}],
    }
    # One team only, so the "all teams have slots" check passes.
    pace = build_pace(standings, slots_by_team=slots, limits=parsed_limits, game_days=baked_game_days())
    assert pace["breakdown"] == "position"
    team = pace["teams"][0]
    assert [s["id"] for s in team["slots"]] == ["PG", "SG", "SF", "PF", "C", "G", "F", "UTIL"]
    assert team["slots"][0]["used"] == 9 and team["slots"][0]["max"] == 82
    assert team["slots"][-1]["used"] == 18 and team["slots"][-1]["max"] == 245
    assert team["gp"] == 9 + 8 + 7 + 6 + 10 + 4 + 5 + 18
    assert team["owner"] == "Meir Naim"
    # A partial slot map must not pretend every team has position data.
    full = json.load(open(ROOT / "data" / "standings.json"))
    fallback = build_pace(full, slots_by_team=slots, limits=parsed_limits, game_days=baked_game_days())
    assert fallback["breakdown"] == "total"


def test_ignores_non_gp_stat():
    entry = {"statId": 0, "value": 99}
    from pace_lib import parse_stat_value
    assert parse_stat_value(entry) is None
    assert parse_stat_value({"statId": 42, "value": 3}) == 3


if __name__ == "__main__":
    test_calendar()
    test_standings_order_and_flags()
    test_position_parse_and_caps()
    test_ignores_non_gp_stat()
    print("ok")
