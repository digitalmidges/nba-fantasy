# Barchashim League

Points-per-position board (season TOT ÷ GP) and draft-value board, updated by NBA Fantasy Bot.

https://digitalmidges.github.io/nba-fantasy/

The page has five tabs: **Leaderboard** (points per position), **Draft value**, **Draft retro**, **Pace** (games played against the ESPN position caps, versus the NBA calendar), and **Trends** (Avg Pts/Pos at each standings refresh).

Pace is rebuilt with the standings refresh (`scripts/build_index.py` reads `data/standings.json` and, when ESPN cookies are available, per-position games from the league API). The same rebuild appends that scrape to `data/avg_history.json` and embeds it in the Trends chart. Older points stay. Two scrapes inside 30 minutes count as one refresh (the later `scraped_at` is kept). Scrapes 30 minutes or more apart are both kept, including a morning refresh and an after-games refresh on the same day. Avg is `season_points_TOT / GP`, the same ratio as the Leaderboard, not the basketball PTS category.

The shell lives in `data/raw/index.prev.html` so a standings-only rebuild keeps the tabs.

Draft value sections: Best bang for the buck, Steals by round, Draft board, Draft report card, Best undrafted pickups.
