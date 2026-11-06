# Barchashim League

Points-per-position board (season TOT ÷ GP) and draft-value board, updated by NBA Fantasy Bot.

https://digitalmidges.github.io/nba-fantasy/

The page has five tabs: **Leaderboard** (points per position), **Draft value**, **Draft retro**, **Pace** (games played against the ESPN position caps, versus the NBA calendar), and **Trends** (Avg Pts/Pos at each standings refresh).

Pace is rebuilt with the standings refresh (`scripts/build_index.py` reads `data/standings.json` and, when ESPN cookies are available, per-position games from the league API). The same rebuild appends that scrape to `data/avg_history.json` and embeds it in the Trends chart. Older points stay. Two scrapes inside 30 minutes count as one refresh (the later `scraped_at` is kept). Scrapes 30 minutes or more apart are both kept, including a morning refresh and an after-games refresh on the same day. Avg is `season_points_TOT / GP`, the same ratio as the Leaderboard, not the basketball PTS category.

The shell lives in `data/raw/index.prev.html` so a standings-only rebuild keeps the tabs.

Draft value sections: Best bang for the buck, Steals by round, Draft board, Draft report card, Best undrafted pickups.


## Refreshing Draft value / Draft retro

Draft production numbers come from `data/draft_value.json` (embedded into the page by `scripts/build_index.py`). They do not update from the public site alone.

1. While signed in to ESPN Fantasy as a league member, save the league API payload
   (`view=mRoster&view=mTeam`) to `data/raw/espn_mroster.json`.
2. Rebuild roster + FA flats and `draft_value.json`:
   `python3 scripts/refresh_draft_data.py data/raw/espn_mroster.json`
   The script also pulls public season stats for dropped / free-agent players from
   ESPN `kona_player_info` (no login). Pass `--kona PATH` to reuse a saved dump.
3. Rebuild and publish the page: `python3 scripts/build_index.py` then commit
   `index.html` + `data/draft_value.json`.

The twice-daily standings refresh should save a fresh `espn_mroster.json` and run
steps 2–3 so Draft value / Draft retro stay current with the leaderboard.
