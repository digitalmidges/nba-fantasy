"""Avg Pts/Pos history merge. Run: python3 scripts/test_avg_history.py"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from avg_history import append_standings, merge_points, point_from_standings  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def snap(at, rows):
    return {
        "scraped_at": at,
        "teams": [
            {"team": name, "season_points_TOT": tot, "GP": gp, "points_by_stat": {"PTS": 999}}
            for name, tot, gp in rows
        ],
    }


def test_avg_is_tot_over_gp_not_pts_category():
    point = point_from_standings(snap("2026-11-04T23:03:36-06:00", [("Naim Merlon", 3450, 94)]))
    assert point["teams"][0]["avg"] == round(3450 / 94, 4)
    assert point["teams"][0]["tot"] == 3450
    assert point["teams"][0]["gp"] == 94
    assert "pts" not in point["teams"][0]


def test_keeps_samples_30_minutes_apart_and_prefers_later_inside_window():
    early = point_from_standings(snap("2026-11-04T22:53:52-06:00", [("ER", 3083, 92)]))
    later = point_from_standings(snap("2026-11-04T23:03:36-06:00", [("ER", 3081, 92)]))
    morning = point_from_standings(snap("2026-11-03T22:47:31-06:00", [("ER", 2790, 82)]))
    merged = merge_points([later, early, morning])
    assert [p["at"] for p in merged] == [
        "2026-11-03T22:47:31-06:00",
        "2026-11-04T23:03:36-06:00",
    ]
    assert merged[-1]["teams"][0]["tot"] == 3081


def test_same_day_refreshes_an_hour_apart_both_stay():
    night_a = point_from_standings(snap("2026-10-29T23:08:29-05:00", [("DanKen", 1810, 52)]))
    night_b = point_from_standings(snap("2026-10-29T23:51:35-05:00", [("DanKen", 1810, 52)]))
    merged = merge_points([night_b, night_a])
    assert len(merged) == 2


def test_window_does_not_slide_forward():
    # 22:00 opens the window. 22:20 replaces it. 22:35 is 35 minutes after the
    # opener, so it is a new point even though it is 15 minutes after 22:20.
    points = [
        point_from_standings(snap("2026-11-01T22:00:00-06:00", [("ER", 1, 1)])),
        point_from_standings(snap("2026-11-01T22:20:00-06:00", [("ER", 2, 1)])),
        point_from_standings(snap("2026-11-01T22:35:00-06:00", [("ER", 3, 1)])),
    ]
    merged = merge_points(points)
    assert [p["at"] for p in merged] == [
        "2026-11-01T22:20:00-06:00",
        "2026-11-01T22:35:00-06:00",
    ]
    assert [p["teams"][0]["tot"] for p in merged] == [2, 3]


def test_append_keeps_older_points(tmp_path=None):
    path = ROOT / "data" / "_avg_history_test.json"
    if path.exists():
        path.unlink()
    try:
        first = append_standings(path, snap("2026-10-29T11:53:22-05:00", [("ER", 1853, 53), ("DanKen", 1717, 50)]))
        second = append_standings(path, snap("2026-11-04T23:03:36-06:00", [("DanKen", 3069, 90), ("ER", 3081, 92)]))
        again = append_standings(path, snap("2026-11-04T23:03:36-06:00", [("DanKen", 3069, 90), ("ER", 3081, 92)]))
        assert [p["at"] for p in second["points"]] == [
            "2026-10-29T11:53:22-05:00",
            "2026-11-04T23:03:36-06:00",
        ]
        assert again["points"] == second["points"]
        assert first["points"][0]["teams"][0]["team"] == "DanKen"
        assert len(again["points"]) == 2
        saved = json.loads(path.read_text())
        assert saved["formula"] == "season_points_TOT / GP"
        assert "30 minutes" in saved["dedupe"]
    finally:
        if path.exists():
            path.unlink()


def test_committed_history_keeps_the_seed():
    doc = json.loads((ROOT / "data" / "avg_history.json").read_text())
    points = doc["points"]
    assert doc["formula"] == "season_points_TOT / GP"
    assert "basketball PTS" in doc["dedupe"] or "not the basketball PTS" in doc["dedupe"]
    stamps = [p["at"] for p in points]
    assert stamps == sorted(stamps, key=lambda s: s)
    assert stamps[0].startswith("2026-10-29T11:53:22")
    assert "2026-11-04T23:03:36-06:00" in stamps
    # Same-night samples 43 minutes apart stay. Sub-30-minute double writes do not.
    assert "2026-10-29T23:08:29-05:00" in stamps
    assert "2026-10-29T23:51:35-05:00" in stamps
    assert "2026-11-02T22:48:04-06:00" not in stamps
    assert "2026-11-04T22:53:52-06:00" not in stamps
    for point in points:
        assert len(point["teams"]) == 8
        for team in point["teams"]:
            assert team["avg"] == round(team["tot"] / team["gp"], 4)


if __name__ == "__main__":
    test_avg_is_tot_over_gp_not_pts_category()
    test_keeps_samples_30_minutes_apart_and_prefers_later_inside_window()
    test_same_day_refreshes_an_hour_apart_both_stay()
    test_window_does_not_slide_forward()
    test_append_keeps_older_points()
    test_committed_history_keeps_the_seed()
    print("ok")
