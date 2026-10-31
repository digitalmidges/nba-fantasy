# Barchashim League

Points-per-position board (season TOT ÷ GP) and draft-value board, updated by NBA Fantasy Bot.

https://digitalmidges.github.io/nba-fantasy/

The page has four tabs: **Leaderboard** (points per position), **Draft value**, **Draft retro**, and **Pace** (games played against the ESPN position caps, versus the NBA calendar).

Pace is rebuilt with the standings refresh (`scripts/build_index.py` reads `data/standings.json` and, when ESPN cookies are available, per-position games from the league API). The shell lives in `data/raw/index.prev.html` so a standings-only rebuild keeps the tab.

Draft value sections: Best bang for the buck, Steals by round, Draft board, Draft report card, Best undrafted pickups.
