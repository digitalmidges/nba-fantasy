import json, datetime, pathlib, statistics

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = str(ROOT / 'data') + '/'

# Avg ranks ignore short samples so a 1- or 2-game spike cannot jump the board.
# Floor is 3 games; that is also the current cutoff because most drafted players
# already have well more than that.
AVG_MIN_GP = 3

STEAL_TOP_RANK = 20
STEAL_VALUE = 40
STEAL_MIN_ROUND = 4
BUST_MAX_ROUND = 3
BUST_VALUE = -25


def gp_of(tot, avg):
    if tot is None or avg in (None, 0):
        return None
    return int(round(tot / avg))


def competition_rank(items, keyfn):
    """1-based competition rank; ties share a rank, next rank skips."""
    ordered = sorted(items, key=keyfn)
    last_key = object()
    last_rank = 0
    for i, item in enumerate(ordered, start=1):
        k = keyfn(item)
        if k != last_key:
            last_rank = i
            last_key = k
        item['_rank_tmp'] = last_rank
    return ordered


def mark_steal_bust(round_no, rank, value, qualifies):
    if not qualifies or rank is None or value is None:
        return False, False
    steal = (round_no >= STEAL_MIN_ROUND and rank <= STEAL_TOP_RANK) or value >= STEAL_VALUE
    bust = round_no <= BUST_MAX_ROUND and value <= BUST_VALUE
    return steal, bust


def round_best_worst(played_subset, rank_key, stat_key):
    ranked = [x for x in played_subset if x.get(rank_key) is not None]
    if not ranked:
        return None
    best = min(ranked, key=lambda x: (x[rank_key], -(x.get(stat_key) or 0), x['pick']))
    worst = max(ranked, key=lambda x: (x[rank_key], -(x.get(stat_key) or 0), -x['pick']))
    stats = [x[stat_key] for x in ranked if x.get(stat_key) is not None]
    return dict(
        best=best['player'],
        best_team=best['drafted_by'],
        best_pick=best['pick'],
        best_stat=best[stat_key],
        best_rank=best[rank_key],
        worst=worst['player'],
        worst_pick=worst['pick'],
        worst_stat=worst[stat_key],
        round_avg=round(sum(stats) / len(stats), 1) if stats else None,
    )


def team_grade(rows, played_attr, value_key, steal_key, bust_key, stat_key, use_mean=False):
    teams = {}
    for x in rows:
        t = teams.setdefault(x['drafted_by'], dict(
            team=x['drafted_by'], draft_stat=0, stat_n=0, value_sum=0,
            steals=0, busts=0, dnp=0, short_gp=0, best=None,
        ))
        qualifies = x.get(played_attr)
        if x.get('played') and not qualifies and played_attr == 'qualifies_avg':
            t['short_gp'] += 1
        if not x.get('played'):
            t['dnp'] += 1
            continue
        if not qualifies:
            continue
        stat = x.get(stat_key)
        if stat is not None:
            t['draft_stat'] += stat
            t['stat_n'] += 1
        val = x.get(value_key)
        if val is not None:
            t['value_sum'] += val
            if t['best'] is None or val > t['best'][1]:
                t['best'] = (x['player'], val)
        t['steals'] += bool(x.get(steal_key))
        t['busts'] += bool(x.get(bust_key))
    out = []
    for t in teams.values():
        entry = dict(
            team=t['team'],
            value_sum=t['value_sum'],
            steals=t['steals'],
            busts=t['busts'],
            dnp=t['dnp'],
            short_gp=t['short_gp'],
            n=t['stat_n'],
            best_value_pick=t['best'][0] if t['best'] else None,
            best_value=t['best'][1] if t['best'] else None,
        )
        if use_mean:
            entry['draft_stat'] = round(t['draft_stat'] / t['stat_n'], 2) if t['stat_n'] else None
        else:
            entry['draft_stat'] = t['draft_stat']
        out.append(entry)
    def sort_key(e):
        stat = e['draft_stat']
        return (stat is not None, stat if stat is not None else 0)
    return sorted(out, key=sort_key, reverse=True)


draft = json.load(open(D + 'draft.json'))
ros = json.load(open(D + 'rosters_flat.json'))
fa = json.load(open(D + 'free_agents.json'))
byname = {r['player']: r for r in ros}
faby = {f['player']: f for f in fa}

rows = []
for p in draft['picks']:
    r = byname.get(p['player']); src = 'rostered'
    if r is None:
        r = faby.get(p['player']); src = 'dropped' if r else 'unknown'
    tot = r.get('fpts_tot') if r else None
    avg = r.get('fpts_avg') if r else None
    gp = gp_of(tot, avg)
    rows.append(dict(
        pick=p['pick'], round=p['round'], pick_in_round=p['pick_in_round'],
        drafted_by=p['team'],
        current_team=(r.get('fantasy_team') if src == 'rostered' else 'Waivers/FA') if r else None,
        player=p['player'], position=p['position'], nba_team=p['nba_team'],
        status=src, injury=(r.get('injury') if r else None),
        fpts_tot=tot, fpts_avg=avg, gp_est=gp,
        played=tot is not None, qualifies_avg=bool(gp is not None and gp >= AVG_MIN_GP),
    ))

played = [x for x in rows if x['played']]
avg_pool = [x for x in played if x['qualifies_avg']]

# --- Total ranks among anyone who has played ---
for x in competition_rank(played, keyfn=lambda x: (-(x['fpts_tot'] or 0), -(x['fpts_avg'] or 0), x['pick'])):
    x['rank_tot'] = x.pop('_rank_tmp')
    x['fpts_rank'] = x['rank_tot']  # backward compatible alias
    x['value_tot'] = x['pick'] - x['rank_tot']
    x['steal_tot'], x['bust_tot'] = mark_steal_bust(x['round'], x['rank_tot'], x['value_tot'], True)

# --- Avg ranks among players who meet the min-GP rule ---
for x in rows:
    if x not in avg_pool:
        x['rank_avg'] = None
        x['value_avg'] = None
        x['steal_avg'] = False
        x['bust_avg'] = False
        x['avg_rank'] = None
for x in competition_rank(avg_pool, keyfn=lambda x: (-(x['fpts_avg'] or 0), -(x['fpts_tot'] or 0), x['pick'])):
    x['rank_avg'] = x.pop('_rank_tmp')
    x['avg_rank'] = x['rank_avg']
    x['value_avg'] = x['pick'] - x['rank_avg']
    x['steal_avg'], x['bust_avg'] = mark_steal_bust(x['round'], x['rank_avg'], x['value_avg'], True)

# Legacy blended production rank, kept so an older page shell still renders.
for x in competition_rank(played, keyfn=lambda x: (
    -((x['rank_tot'] + (x['rank_avg'] if x['rank_avg'] is not None else x['rank_tot'])) / 2),
    -(x['fpts_tot'] or 0),
    x['pick'],
)):
    x['prod_rank'] = x.pop('_rank_tmp')
for x in rows:
    if x['played']:
        x['value'] = x['pick'] - x['prod_rank']
        x['steal'] = (x['round'] >= 4 and x['prod_rank'] <= 20) or x['value'] >= 40
        x['bust'] = x['round'] <= 3 and x['value'] <= -25
    else:
        x['fpts_rank'] = None
        x['prod_rank'] = None
        x['avg_rank'] = None
        x['rank_tot'] = None
        x['value_tot'] = None
        x['steal_tot'] = False
        x['bust_tot'] = False
        x['value'] = None
        x['steal'] = False
        x['bust'] = False

def steals_list(pool, value_key):
    return sorted([x for x in pool if x.get(value_key) is not None], key=lambda x: -x[value_key])

def busts_list(pool, value_key):
    return sorted([x for x in pool if x.get(value_key) is not None and x['round'] <= 4], key=lambda x: x[value_key])

best_by_round = []
for rd in range(1, 14):
    rr = [x for x in played if x['round'] == rd]
    tot_bw = round_best_worst(rr, 'rank_tot', 'fpts_tot') or {}
    avg_bw = round_best_worst([x for x in rr if x['qualifies_avg']], 'rank_avg', 'fpts_avg') or {}
    row = dict(round=rd)
    # Backward-compatible total fields (previous page JS reads these).
    if tot_bw:
        row.update(
            best=tot_bw['best'], best_team=tot_bw['best_team'], best_pick=tot_bw['best_pick'],
            best_fpts=tot_bw['best_stat'], best_rank=tot_bw['best_rank'],
            worst=tot_bw['worst'], worst_pick=tot_bw['worst_pick'], worst_fpts=tot_bw['worst_stat'],
            round_avg_fpts=tot_bw['round_avg'],
        )
    if avg_bw:
        row.update(
            best_avg=avg_bw['best'], best_team_avg=avg_bw['best_team'], best_pick_avg=avg_bw['best_pick'],
            best_fpts_avg=avg_bw['best_stat'], best_rank_avg=avg_bw['best_rank'],
            worst_avg=avg_bw['worst'], worst_pick_avg=avg_bw['worst_pick'], worst_fpts_avg=avg_bw['worst_stat'],
            round_avg_avg=avg_bw['round_avg'],
        )
    best_by_round.append(row)

grades_tot = team_grade(rows, 'played', 'value_tot', 'steal_tot', 'bust_tot', 'fpts_tot', use_mean=False)
grades_avg = team_grade(rows, 'qualifies_avg', 'value_avg', 'steal_avg', 'bust_avg', 'fpts_avg', use_mean=True)

# Merge into one object per team so the page can switch metrics without a second const.
grades_avg_by = {t['team']: t for t in grades_avg}
# Preserve previous sort (total) as the default array order; the page re-sorts in the browser.
team_draft_grades = []
for t in grades_tot:
    a = grades_avg_by[t['team']]
    team_draft_grades.append(dict(
        team=t['team'],
        draft_fpts=t['draft_stat'],
        value_sum=t['value_sum'],
        steals=t['steals'],
        busts=t['busts'],
        dnp=t['dnp'],
        best_value_pick=t['best_value_pick'],
        best_value=t['best_value'],
        draft_avg=a['draft_stat'],
        value_sum_avg=a['value_sum'],
        steals_avg=a['steals'],
        busts_avg=a['busts'],
        short_gp=a['short_gp'],
        qualified_avg=a['n'],
        best_value_pick_avg=a['best_value_pick'],
        best_value_avg=a['best_value'],
    ))

undrafted = sorted(
    [r for r in ros if r['draft_pick'] is None and r['fpts_tot'] is not None],
    key=lambda r: (-r['fpts_tot'], -(r['fpts_avg'] or 0)),
)
und = []
for r in undrafted:
    gp = gp_of(r['fpts_tot'], r['fpts_avg'])
    qualifies = bool(gp is not None and gp >= AVG_MIN_GP)
    would_tot = 1 + sum(1 for x in played if (x['fpts_tot'] or 0) > r['fpts_tot'])
    would_avg = None
    if qualifies:
        would_avg = 1 + sum(1 for x in avg_pool if (x['fpts_avg'] or 0) > (r['fpts_avg'] or 0))
    und.append(dict(
        player=r['player'], fantasy_team=r['fantasy_team'], position=r['eligible'],
        fpts_tot=r['fpts_tot'], fpts_avg=r['fpts_avg'], gp_est=gp,
        qualifies_avg=qualifies,
        would_rank=would_tot,          # backward compatible (total)
        would_rank_tot=would_tot,
        would_rank_avg=would_avg,
    ))

method = (
    "Two standalone metrics. Total: production rank is season fantasy points among drafted "
    "players who have played; value = overall pick # minus that rank. Avg: production rank is "
    "fantasy points per game among drafted players with at least %d games (GP is season points "
    "÷ points-per-game, rounded); value uses that rank. Positive value = outperforming the draft "
    "slot. STEAL = round 4 or later and a top-20 producer on that metric, or value +40 and up. "
    "BUST = rounds 1–3 and value −25 or worse. Players with no games are excluded from both ranks. "
    "Players under the Avg game floor are excluded from Avg ranks only. A legacy prod_rank that "
    "averages the two ranks is still emitted for older page shells."
) % AVG_MIN_GP

out = dict(
    generated_at=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
    avg_min_gp=AVG_MIN_GP,
    method=method,
    picks=rows,
    steals=steals_list(played, 'value')[:15],
    steals_tot=steals_list(played, 'value_tot')[:15],
    steals_avg=steals_list(avg_pool, 'value_avg')[:15],
    busts=busts_list(played, 'value')[:8],
    busts_tot=busts_list(played, 'value_tot')[:8],
    busts_avg=busts_list(avg_pool, 'value_avg')[:8],
    best_by_round=best_by_round,
    team_draft_grades=team_draft_grades,
    undrafted_gems=und,
    dnp=[x for x in rows if not x['played']],
)

json.dump(out, open(D + 'draft_value.json', 'w'), indent=1)

print('played', len(played), 'avg_qualified', len(avg_pool), 'avg_min_gp', AVG_MIN_GP)
print('--steals tot')
for x in out['steals_tot'][:12]:
    print(x['value_tot'], x['rank_tot'], x['pick'], x['round'], x['player'], x['fpts_tot'], x['fpts_avg'], x['gp_est'])
print('--steals avg')
for x in out['steals_avg'][:12]:
    print(x['value_avg'], x['rank_avg'], x['pick'], x['round'], x['player'], x['fpts_tot'], x['fpts_avg'], x['gp_est'])
print('--busts tot')
for x in out['busts_tot'][:8]:
    print(x['value_tot'], x['rank_tot'], x['pick'], x['player'], x['fpts_tot'], x['gp_est'])
print('--busts avg')
for x in out['busts_avg'][:8]:
    print(x['value_avg'], x['rank_avg'], x['pick'], x['player'], x['fpts_avg'], x['gp_est'])
print('--teams tot', [(t['team'], t['draft_fpts'], t['value_sum']) for t in team_draft_grades])
print('--teams avg', [(t['team'], t['draft_avg'], t['value_sum_avg']) for t in sorted(team_draft_grades, key=lambda t: -(t['draft_avg'] or 0))])
print('--und tot', [(u['player'], u['fpts_tot'], u['would_rank_tot']) for u in und[:8]])
avg_und = sorted([u for u in und if u['qualifies_avg']], key=lambda u: (-(u['fpts_avg'] or 0), -(u['fpts_tot'] or 0)))
print('--und avg', [(u['player'], u['fpts_avg'], u['would_rank_avg'], u['gp_est']) for u in avg_und[:8]])
print('generated_at', out['generated_at'])
