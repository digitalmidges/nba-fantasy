import json, datetime, re
B='/workspace/barchashim/'
st=json.load(open(B+'data/standings.json'))
dv=json.load(open(B+'data/draft_value.json'))
html=open(B+'data/raw/index.prev.html').read()
now=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
# standings
rows=[]
for t in st['teams']:
    p=t['points_by_stat']
    rows.append('            { seasonRk: %d, team: %s, owner: %s, fgm: %d, fga: %d, ftm: %d, fta: %d, tpm: %d, reb: %d, ast: %d, stl: %d, blk: %d, to: %d, pts: %d, tot: %d, gp: %d }'%(
        t['rank'],json.dumps(t['team']),json.dumps(t.get('owner') or ''),p['FGM'],p['FGA'],p['FTM'],p['FTA'],p['3PM'],p['REB'],p['AST'],p['STL'],p['BLK'],p['TO'],p['PTS'],t['season_points_TOT'],t['GP']))
html=re.sub(r'const currentData = \[\n.*?\n        \]\.map', 'const currentData = [\n'+',\n'.join(rows)+'\n        ].map', html, flags=re.S)
html=re.sub(r'const LAST_REFRESH_ISO = "[^"]*";', 'const LAST_REFRESH_ISO = "%s";'%now, html)
keep=['pick','round','pick_in_round','drafted_by','current_team','player','position','nba_team','status','fpts_tot','fpts_avg','gp_est','prod_rank','value','steal','bust','played']
picks=[{k:p[k] for k in keep} for p in dv['picks']]
teams_order=[p['drafted_by'] for p in dv['picks'] if p['round']==1]
data_js='        const DRAFT = %s;\n        const DRAFT_TEAMS = %s;\n        const BY_ROUND = %s;\n        const TEAM_GRADES = %s;\n        const UNDRAFTED = %s;\n'%(
    json.dumps(picks,separators=(',',':')),json.dumps(teams_order),json.dumps(dv['best_by_round'],separators=(',',':')),
    json.dumps(dv['team_draft_grades'],separators=(',',':')),json.dumps(dv['undrafted_gems'][:10],separators=(',',':')))
css='''        .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.72em; font-weight: 700; letter-spacing: 0.4px; margin-left: 6px; vertical-align: middle; }
        .badge.steal { background: #e6f7ee; color: #127a43; }
        .badge.bust { background: #fdecec; color: #b42318; }
        .badge.dnp { background: #f0f0f0; color: #666; }
        .pos { color: #2a8a55; font-weight: 700; }
        .neg { color: #c0392b; font-weight: 700; }
        .muted { color: #888; font-size: 0.85em; }
        .note { background: #f6f3ff; border-left: 4px solid #764ba2; padding: 10px 14px; border-radius: 6px; color: #444; font-size: 0.88em; margin-bottom: 16px; }
        .board { width: 100%; border-collapse: separate; border-spacing: 4px; }
        .board th { background: none; color: #333; font-size: 0.75em; white-space: normal; text-align: center; padding: 6px 4px; }
        .board thead { background: none; }
        .board td { border: none; border-radius: 6px; padding: 6px 6px; font-size: 0.74em; text-align: center; line-height: 1.25; min-width: 86px; }
        .board td .p { font-weight: 600; color: #222; }
        .board td .v { font-size: 0.92em; }
        .board td.rd { background: none; font-weight: 700; color: #667eea; min-width: 30px; }
        .board tbody tr:hover { background: none; }
        .legend { display: flex; flex-wrap: wrap; gap: 10px; font-size: 0.8em; color: #555; margin-bottom: 12px; }
        .legend span { display: inline-flex; align-items: center; gap: 6px; }
        .legend i { width: 14px; height: 14px; border-radius: 4px; display: inline-block; }
'''
if 'id="bangForBuck"' not in html:
    html=html.replace('        .footer {', css+'        .footer {',1)
sections='''
        <div class="table-section" id="bangForBuck">
            <h2>Best bang for the buck</h2>
            <p class="hint">Who returned the most fantasy points for where they were drafted.</p>
            <div class="note">Value = overall pick # minus production rank. Production rank orders all drafted players who have played by the average of their FPts-total rank and FPts/G rank (1 = best). +40 means a player is producing about 40 spots better than his draft slot. <b>STEAL</b> = round 4 or later and a top-20 producer, or value +40 and up. <b>BUST</b> = rounds 1–3 and value −25 or worse. Early season: most players have only 2–3 games, so expect big swings.</div>
            <div class="controls">
                <div class="control-group">
                    <label for="valueView">Show:</label>
                    <select id="valueView">
                        <option value="steals" selected>Top 15 steals</option>
                        <option value="busts">Biggest early-round busts</option>
                        <option value="all">All drafted players</option>
                    </select>
                </div>
                <div class="control-group">
                    <label for="valueTeam">Team:</label>
                    <select id="valueTeam"><option value="">All teams</option></select>
                </div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Player</th>
                        <th>Drafted by</th>
                        <th class="number">Pick</th>
                        <th class="number">Rd</th>
                        <th class="number">FPts</th>
                        <th class="number">FPts/G</th>
                        <th class="number">Prod RK</th>
                        <th class="number">Value</th>
                    </tr>
                </thead>
                <tbody id="tableValue"></tbody>
            </table>
        </div>

        <div class="table-section" id="stealsByRound">
            <h2>Steals by round</h2>
            <p class="hint">Best and worst return in every round. A low production rank in a late round is the "4th-rounder playing like a 1st-rounder" pick.</p>
            <table>
                <thead>
                    <tr>
                        <th>Rd</th>
                        <th>Best pick</th>
                        <th>Drafted by</th>
                        <th class="number">Pick</th>
                        <th class="number">FPts</th>
                        <th class="number">Prod RK</th>
                        <th>Worst pick</th>
                        <th class="number">FPts</th>
                        <th class="number">Rd avg FPts</th>
                    </tr>
                </thead>
                <tbody id="tableByRound"></tbody>
            </table>
        </div>

        <div class="table-section" id="draftBoard">
            <h2>Draft board</h2>
            <p class="hint">Every pick by round and team, shaded by value. Green = outperforming the draft slot, red = underperforming.</p>
            <div class="legend">
                <span><i style="background:#2a8a55"></i>Value +40 or better</span>
                <span><i style="background:#9fdcb8"></i>+10 to +39</span>
                <span><i style="background:#f1f1f1"></i>−9 to +9</span>
                <span><i style="background:#f6b5ad"></i>−10 to −39</span>
                <span><i style="background:#d9534f"></i>−40 or worse</span>
                <span><i style="background:#fff;border:1px dashed #bbb"></i>No games yet</span>
            </div>
            <table class="board">
                <thead><tr id="boardHead"></tr></thead>
                <tbody id="boardBody"></tbody>
            </table>
        </div>

        <div class="table-section" id="draftGrades">
            <h2>Draft report card</h2>
            <p class="hint">Fantasy points produced so far by each team's 13 draft picks (including players since dropped). Net value adds up every pick's value score.</p>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Team</th>
                        <th class="number">Draft FPts</th>
                        <th class="number">Net value</th>
                        <th class="number">Steals</th>
                        <th class="number">Busts</th>
                        <th>Best value pick</th>
                    </tr>
                </thead>
                <tbody id="tableGrades"></tbody>
            </table>
        </div>

        <div class="table-section" id="undrafted">
            <h2>Best undrafted pickups</h2>
            <p class="hint">Waiver adds who weren't drafted, with where they'd rank among the 100 drafted players who have played (by FPts total).</p>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Player</th>
                        <th>Team</th>
                        <th>Pos</th>
                        <th class="number">FPts</th>
                        <th class="number">FPts/G</th>
                        <th class="number">Would rank</th>
                    </tr>
                </thead>
                <tbody id="tableUndrafted"></tbody>
            </table>
        </div>

        <p class="footer">'''
if 'id="bangForBuck"' not in html:
    html=html.replace('\n        <p class="footer">',sections,1)
html=html.replace('Source: ESPN Fantasy league 683874011 · Times show in your device timezone','Source: ESPN Fantasy league 683874011 · Fantasy points = ESPN points-league scoring · Times show in your device timezone')
html=html.replace('<p class="subtitle">2027 · Points per position</p>','<p class="subtitle">2027 · Points per position · Draft value</p>')
js=r'''
        function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
        function fmtVal(v) { if (v == null) return '<span class="muted">—</span>'; return '<span class="' + (v > 0 ? 'pos' : v < 0 ? 'neg' : '') + '">' + (v > 0 ? '+' : '') + v + '</span>'; }
        function fnum(n, d) { return n == null ? '<span class="muted">—</span>' : (d ? n.toFixed(d) : num(n)); }
        function badges(p) {
            let b = '';
            if (p.steal) b += '<span class="badge steal">STEAL</span>';
            if (p.bust) b += '<span class="badge bust">BUST</span>';
            if (!p.played) b += '<span class="badge dnp">NO GAMES</span>';
            if (p.status === 'dropped') b += '<span class="badge dnp">DROPPED</span>';
            return b;
        }
        function renderValue() {
            const view = document.getElementById('valueView').value;
            const team = document.getElementById('valueTeam').value;
            let list = DRAFT.filter(p => !team || p.drafted_by === team);
            if (view === 'steals') list = list.filter(p => p.played).sort((a, b) => b.value - a.value).slice(0, 15);
            else if (view === 'busts') list = list.filter(p => p.played && p.round <= 4).sort((a, b) => a.value - b.value).slice(0, 10);
            else list = list.sort((a, b) => (b.value == null ? -999 : b.value) - (a.value == null ? -999 : a.value));
            document.getElementById('tableValue').innerHTML = list.map((p, i) =>
                '<tr><td class="rank">' + (i + 1) + '</td>' +
                '<td class="team">' + esc(p.player) + ' <span class="muted">' + esc(p.position) + ' · ' + esc(p.nba_team) + '</span>' + badges(p) + '</td>' +
                '<td>' + esc(p.drafted_by) + '</td>' +
                '<td class="number">' + p.pick + '</td>' +
                '<td class="number">' + p.round + '</td>' +
                '<td class="number">' + fnum(p.fpts_tot) + '</td>' +
                '<td class="number">' + fnum(p.fpts_avg, 1) + '</td>' +
                '<td class="number">' + (p.prod_rank == null ? '<span class="muted">—</span>' : p.prod_rank) + '</td>' +
                '<td class="number tot">' + fmtVal(p.value) + '</td></tr>').join('');
        }
        function renderByRound() {
            document.getElementById('tableByRound').innerHTML = BY_ROUND.map(r =>
                '<tr><td class="rank">' + r.round + '</td>' +
                '<td class="team">' + esc(r.best) + (r.round >= 4 && r.best_rank <= 20 ? '<span class="badge steal">STEAL</span>' : '') + '</td>' +
                '<td>' + esc(r.best_team) + '</td>' +
                '<td class="number">' + r.best_pick + '</td>' +
                '<td class="number">' + num(r.best_fpts) + '</td>' +
                '<td class="number tot">' + r.best_rank + '</td>' +
                '<td>' + esc(r.worst) + ' <span class="muted">#' + r.worst_pick + '</span></td>' +
                '<td class="number">' + num(r.worst_fpts) + '</td>' +
                '<td class="number">' + r.round_avg_fpts.toFixed(1) + '</td></tr>').join('');
        }
        function cellColor(p) {
            if (!p.played) return 'background:#fff;border:1px dashed #bbb';
            const v = p.value;
            if (v >= 40) return 'background:#2a8a55;color:#fff';
            if (v >= 10) return 'background:#9fdcb8';
            if (v > -10) return 'background:#f1f1f1';
            if (v > -40) return 'background:#f6b5ad';
            return 'background:#d9534f;color:#fff';
        }
        function renderBoard() {
            document.getElementById('boardHead').innerHTML = '<th>Rd</th>' + DRAFT_TEAMS.map(t => '<th>' + esc(t) + '</th>').join('');
            let body = '';
            for (let r = 1; r <= 13; r++) {
                body += '<tr><td class="rd">' + r + '</td>' + DRAFT_TEAMS.map(t => {
                    const p = DRAFT.find(x => x.round === r && x.drafted_by === t);
                    if (!p) return '<td></td>';
                    const strong = p.played && p.value >= 40 || p.played && p.value <= -40;
                    return '<td style="' + cellColor(p) + '" title="#' + p.pick + ' ' + esc(p.player) + ' — ' + (p.played ? p.fpts_tot + ' FPts, value ' + (p.value > 0 ? '+' : '') + p.value : 'no games yet') + '">' +
                        '<div class="p"' + (strong ? ' style="color:#fff"' : '') + '>' + esc(p.player) + '</div>' +
                        '<div class="v">#' + p.pick + ' · ' + (p.played ? (p.value > 0 ? '+' : '') + p.value : '—') + '</div></td>';
                }).join('') + '</tr>';
            }
            document.getElementById('boardBody').innerHTML = body;
        }
        function renderGrades() {
            document.getElementById('tableGrades').innerHTML = TEAM_GRADES.map((t, i) =>
                '<tr' + (t.team === MUSHROOM ? ' class="highlight"' : '') + '><td class="rank">' + (i + 1) + '</td>' +
                '<td class="team">' + esc(t.team) + '</td>' +
                '<td class="number tot">' + num(t.draft_fpts) + '</td>' +
                '<td class="number">' + fmtVal(t.value_sum) + '</td>' +
                '<td class="number">' + t.steals + '</td>' +
                '<td class="number">' + t.busts + '</td>' +
                '<td>' + esc(t.best_value_pick) + ' <span class="muted">(' + (t.best_value > 0 ? '+' : '') + t.best_value + ')</span></td></tr>').join('');
        }
        function renderUndrafted() {
            document.getElementById('tableUndrafted').innerHTML = UNDRAFTED.map((u, i) =>
                '<tr><td class="rank">' + (i + 1) + '</td>' +
                '<td class="team">' + esc(u.player) + '</td>' +
                '<td>' + esc(u.fantasy_team) + '</td>' +
                '<td>' + esc(u.position) + '</td>' +
                '<td class="number tot">' + num(u.fpts_tot) + '</td>' +
                '<td class="number">' + u.fpts_avg.toFixed(1) + '</td>' +
                '<td class="number">' + u.would_rank + '</td></tr>').join('');
        }
        (function initTeamFilter() {
            const sel = document.getElementById('valueTeam');
            DRAFT_TEAMS.slice().sort().forEach(t => { const o = document.createElement('option'); o.value = t; o.textContent = t; sel.appendChild(o); });
        })();
        document.getElementById('valueView').addEventListener('change', renderValue);
        document.getElementById('valueTeam').addEventListener('change', renderValue);
'''
if 'const DRAFT = ' not in html:
    html=html.replace('        const MUSHROOM = "Team The Mushroom";\n','        const MUSHROOM = "Team The Mushroom";\n'+data_js,1)
    html=html.replace('        showLastRefresh();\n', js+'\n        showLastRefresh();\n',1)
    html=html.replace('        renderCustom();\n    </script>','        renderCustom();\n        renderValue();\n        renderByRound();\n        renderBoard();\n        renderGrades();\n        renderUndrafted();\n    </script>',1)
open(B+'index.html','w').write(html)
print('ok',now,len(html))

# ---- tabs: Leaderboard / Draft value ----
html=open(B+'index.html').read()
if 'id="panel-leaderboard"' not in html:
    tab_css='''        .tabs { display: flex; gap: 8px; margin: 6px 0 22px; padding: 6px; background: #f3f0fb; border-radius: 999px; width: fit-content; max-width: 100%; overflow-x: auto; }
        .tab { border: none; background: transparent; color: #764ba2; font-weight: 700; font-size: 0.95em; padding: 10px 20px; border-radius: 999px; cursor: pointer; white-space: nowrap; font-family: inherit; }
        .tab:hover { background: rgba(118,75,162,0.1); }
        .tab.active { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; box-shadow: 0 2px 8px rgba(118,75,162,0.3); }
        .tab-panel[hidden] { display: none; }
        @media (max-width: 600px) { .tabs { width: 100%; } .tab { flex: 1; padding: 10px 8px; font-size: 0.9em; } }
'''
    html=html.replace('        .footer {', tab_css+'        .footer {',1)
    bar='''
        <nav class="tabs" role="tablist">
            <button type="button" class="tab active" role="tab" data-tab="leaderboard" aria-selected="true">🏆 Leaderboard</button>
            <button type="button" class="tab" role="tab" data-tab="draft" aria-selected="false">💎 Draft value</button>
        </nav>
        <div class="tab-panel" id="panel-leaderboard" role="tabpanel">
        <p class="formula">'''
    html=html.replace('\n        <p class="formula">',bar,1)
    html=html.replace('\n        <div class="table-section" id="bangForBuck">','\n        </div>\n        <div class="tab-panel" id="panel-draft" role="tabpanel" hidden>\n        <div class="table-section" id="bangForBuck">',1)
    html=html.replace('\n        <p class="footer">','\n        </div>\n\n        <p class="footer">',1)
    tab_js='''
        function showTab(name) {
            if (name !== 'draft') name = 'leaderboard';
            document.querySelectorAll('.tab').forEach(b => { const on = b.dataset.tab === name; b.classList.toggle('active', on); b.setAttribute('aria-selected', on); });
            document.getElementById('panel-leaderboard').hidden = name !== 'leaderboard';
            document.getElementById('panel-draft').hidden = name !== 'draft';
            document.title = 'Barchashim League — ' + (name === 'draft' ? 'Draft value' : 'Leaderboard');
        }
        document.querySelectorAll('.tab').forEach(b => b.addEventListener('click', () => { history.replaceState(null, '', '#' + b.dataset.tab); showTab(b.dataset.tab); }));
        window.addEventListener('hashchange', () => showTab(location.hash.slice(1)));
        showTab(location.hash.slice(1));
    </script>'''
    html=html.replace('\n    </script>',tab_js,1) if html.count('</script>')==1 else html.replace('        renderUndrafted();\n    </script>','        renderUndrafted();'+tab_js,1)
    open(B+'index.html','w').write(html)

# ---- favicon: keep the basketball icon across PPG rebuilds ----
html=open(B+'index.html').read()
changed=False
if 'href="favicon.svg"' not in html:
    icon_links=('    <link rel="icon" href="favicon.svg" type="image/svg+xml">\n'
                '    <link rel="icon" href="favicon.ico" sizes="any">\n'
                '    <link rel="apple-touch-icon" href="apple-touch-icon.png">\n')
    if '    <title>' in html:
        html=html.replace('    <title>', icon_links+'    <title>', 1)
    else:
        html=html.replace('<title>', icon_links+'<title>', 1)
    changed=True
if 'h1 .ball' not in html:
    ball_css='        h1 .ball { display: inline-block; width: 0.82em; height: 0.82em; vertical-align: middle; margin-right: 0.22em; }\n'
    if '        .footer {' in html:
        html=html.replace('        .footer {', ball_css+'        .footer {', 1)
    else:
        html=html.replace('    </style>', ball_css+'    </style>', 1)
    changed=True
if 'class="ball"' not in html:
    html=html.replace('<h1>Barchashim League</h1>', '<h1><img class="ball" src="favicon.svg" alt="" width="46" height="46">Barchashim League</h1>', 1)
    changed=True
if changed:
    open(B+'index.html','w').write(html)

# ---- responsive layout: mobile cards, slim desktop table ----
HEADER = '''    <header class="topbar">
        <div class="brand">
            <img class="ball" src="favicon.svg" alt="" width="40" height="40">
            <div class="brand-text">
                <h1><span class="short">Barchashim</span><span class="long">Barchashim League</span></h1>
                <p class="tagline">Season points ÷ games</p>
            </div>
        </div>
        <div class="stamp">
            <span class="stamp-text"><span class="chip-prefix-short">Updated </span><span class="chip-prefix-long">Updated </span><span id="lastRefreshLabel">—</span></span>
            <button type="button" class="icon-btn" id="refreshBtn" aria-label="Refresh">
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M20 12a8 8 0 1 1-2.3-5.7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M20 4v5h-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
        </div>
    </header>
'''

LEADERBOARD = '''        <div class="section-head">
            <h2>Leaderboard</h2>
            <p class="formula">Avg = season points ÷ games</p>
        </div>
        <div class="mode-pills" id="rankMode" role="tablist">
            <button type="button" class="pill active" data-mode="avg" aria-selected="true">Avg</button>
            <button type="button" class="pill" data-mode="total" aria-selected="false">Total</button>
        </div>
        <div class="cards" id="teamCards"></div>
        <div class="board-wrap">
            <table class="slim">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Team</th>
                        <th>Owner</th>
                        <th class="number">Total</th>
                        <th class="number">Games</th>
                        <th class="number">Avg</th>
                    </tr>
                </thead>
                <tbody id="tableSlim"></tbody>
            </table>
        </div>
        <div class="section-head spaced">
            <h2>Season totals</h2>
            <p class="formula">ESPN order · season points and games</p>
        </div>
        <div class="cards" id="seasonCards"></div>
        <div class="board-wrap">
            <table class="slim">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Team</th>
                        <th>Owner</th>
                        <th class="number">Total</th>
                        <th class="number">Games</th>
                    </tr>
                </thead>
                <tbody id="tableSeason"></tbody>
            </table>
        </div>
'''

LAYOUT_CSS = '''        /* responsive board: cards under 700px, slim table above */
        body { background: #f4f1fb; padding: 0; color: #241c3a; }
        .container { max-width: 980px; margin: 0 auto; padding: 16px 16px 40px; }
        .topbar {
            display: flex; align-items: center; justify-content: space-between; gap: 12px;
            padding: 16px 18px; color: #fff;
            background: linear-gradient(100deg, #693fc4 0%, #7a4fd0 100%);
        }
        .topbar .brand { display: flex; align-items: center; gap: 12px; min-width: 0; }
        .topbar .ball { width: 40px; height: 40px; display: block; flex: none; }
        .topbar h1 {
            text-align: left; color: #fff; margin: 0; text-shadow: none;
            font-size: 1.35rem; font-weight: 800; letter-spacing: -0.02em; line-height: 1.1;
        }
        .topbar .tagline { margin: 3px 0 0; color: rgba(255,255,255,0.82); font-size: 0.78rem; font-weight: 500; }
        .chip {
            display: inline-flex; align-items: center; gap: 8px; flex: none;
            max-width: 58%; color: #fff; background: transparent; cursor: pointer; font: inherit;
            font-size: 0.75rem; font-weight: 650; line-height: 1.2; text-align: left;
            border: 1px solid rgba(255,255,255,0.38); border-radius: 999px; padding: 6px 12px 6px 10px;
        }
        .chip:disabled { opacity: 0.7; cursor: wait; }
        .chip-icon, .chip-refresh { flex: none; }
        .chip-refresh, .when-short { display: none; }
        .formula { text-align: left; color: #7c7694; font-weight: 500; font-size: 0.82rem; margin: 2px 0 12px; }
        .footer { color: #8d87a3; }
        .cards { display: none; }
        .board-wrap {
            display: block; background: #fff; border-radius: 18px;
            box-shadow: 0 10px 28px rgba(70,40,120,0.08); overflow: hidden;
        }
        .card {
            display: flex; align-items: center; gap: 12px; background: #fff;
            border-radius: 16px; padding: 16px 16px; 
            box-shadow: 0 8px 22px rgba(70,40,120,0.07);
        }
        .card.highlight { box-shadow: inset 0 0 0 2px #d9ccf7, 0 8px 22px rgba(70,40,120,0.07); }
        .card .rk { flex: none; width: 52px; font-weight: 800; font-size: 1.45rem; color: #2c2644; letter-spacing: -0.03em; }
        .card .rk.gold { color: #e2a30b; }
        .card .who { min-width: 0; flex: 1; }
        .card .name { font-weight: 800; font-size: 1.05rem; color: #1c1730; line-height: 1.2; }
        .card .owner { margin-top: 3px; color: #8b86a0; font-size: 0.88rem; }
        .card .stat { text-align: right; flex: none; }
        .card .lbl { font-size: 0.68rem; letter-spacing: 0.08em; font-weight: 800; color: #8b86a0; }
        .card .avg { font-size: 1.65rem; font-weight: 800; color: #6236d4; line-height: 1.05; font-variant-numeric: tabular-nums; }
        .card .games { margin-top: 2px; color: #8b86a0; font-size: 0.82rem; }
        table.slim thead { background: transparent; color: #8b86a0; }
        table.slim th { color: #8b86a0; font-weight: 600; font-size: 0.78rem; padding: 16px 18px 10px; }
        table.slim td { padding: 14px 18px; border-bottom: 1px solid #f0eef5; font-size: 0.95rem; }
        table.slim .rank { color: #3a3158; }
        table.slim td.avg { color: #6236d4; font-weight: 800; font-size: 1.05rem; }
        table.slim .team { white-space: normal; }
        .tabs { display: flex; gap: 10px; margin: 4px 0 14px; padding: 0; background: transparent; width: 100%; border-radius: 0; }
        .tab {
            flex: 1; border: none; background: #fff; color: #6d6786; font-weight: 750; font-size: 0.98rem;
            padding: 12px 10px; border-radius: 14px; cursor: pointer; font-family: inherit;
            box-shadow: 0 2px 8px rgba(70,40,120,0.06);
        }
        .tab.active {
            background: linear-gradient(180deg, #7b5ae0 0%, #6841c9 100%);
            color: #fff; box-shadow: 0 6px 16px rgba(104,65,201,0.28);
        }
        @media (max-width: 700px) {
            .cards { display: flex; flex-direction: column; gap: 12px; }
            .board-wrap { display: none; }
            .topbar .long, .chip-prefix-long, .when-long { display: none; }
            .when-short { display: inline; }
            .topbar .tagline { white-space: nowrap; }
            .topbar { padding: 14px 16px; }
            .table-section { padding: 16px; overflow-x: visible; }
            #panel-draft table { display: none; }
            #panel-draft .m-only { display: flex; }
            body { overflow-x: hidden; }
        }
        @media (min-width: 701px) {
            .topbar { padding: 18px 28px; }
            .topbar h1 { font-size: 1.7rem; }
            .topbar .short, .chip-prefix-short, .chip-icon { display: none; }
            .chip-refresh { display: block; }
            .chip { border: none; max-width: none; font-size: 0.95rem; font-weight: 600; padding: 0; gap: 14px; }
            .tabs {
                width: fit-content; gap: 0; padding: 4px; margin: 0 0 16px;
                background: rgba(255,255,255,0.72); border-radius: 14px;
            }
            .tab { flex: none; background: transparent; color: #6d6786; box-shadow: none; border-radius: 10px; padding: 8px 18px; }
            .tab.active { background: #fff; color: #2c2548; box-shadow: 0 1px 4px rgba(40,20,80,0.08); }
            #panel-draft .table-section { overflow-x: auto; }
        }

'''

RENDER_FN = '''        function renderStandings() {
            const sorted = [...currentData].sort((a, b) => b.avgPts - a.avgPts || a.seasonRk - b.seasonRk);
            const cards = document.getElementById('teamCards');
            const slim = document.getElementById('tableSlim');
            if (!cards || !slim) return;
            cards.innerHTML = sorted.map((t, i) => {
                const n = i + 1;
                const hl = t.team === MUSHROOM ? ' highlight' : '';
                const gold = n === 1 ? ' gold' : '';
                return '<article class="card' + hl + '">' +
                    '<div class="rk' + gold + '">#' + n + '</div>' +
                    '<div class="who"><div class="name">' + esc(t.team) + '</div>' +
                    '<div class="owner">' + esc(t.owner || '') + '</div></div>' +
                    '<div class="stat"><div class="lbl">AVG</div><div class="avg">' + fmtAvg(t.avgPts) + '</div>' +
                    '<div class="games">' + t.gp + ' games</div></div></article>';
            }).join('');
            slim.innerHTML = sorted.map((t, i) => {
                const hl = t.team === MUSHROOM ? ' class="highlight"' : '';
                return '<tr' + hl + '><td class="rank">' + (i + 1) + '</td>' +
                    '<td class="team">' + esc(t.team) + '</td>' +
                    '<td class="owner">' + esc(t.owner || '') + '</td>' +
                    '<td class="number">' + num(t.tot) + '</td>' +
                    '<td class="number">' + t.gp + '</td>' +
                    '<td class="number avg">' + fmtAvg(t.avgPts) + '</td></tr>';
            }).join('');
        }
'''

def ensure_responsive_layout(html):
    if 'id="teamCards"' in html:
        return html
    if '    </style>' not in html:
        raise SystemExit('style close missing')
    html = html.replace('    </style>', LAYOUT_CSS + '    </style>', 1)
    if '<header class="topbar">' not in html:
        pat = r'[ \t]*<h1\b.*?</h1>\s*<p class="subtitle">.*?</p>\s*<div class="toolbar">[\s\S]*?id="refreshBtn"[\s\S]*?</div>\n'
        html, n = re.subn(pat, '\n', html, count=1, flags=re.S)
        if n != 1:
            raise SystemExit('header block not found')
        needle = '<body>\n    <div class="container">'
        if needle not in html:
            raise SystemExit('body container not found')
        html = html.replace(needle, '<body>\n' + HEADER + '\n    <div class="container">', 1)
    panel = r'(<div class="tab-panel" id="panel-leaderboard"[^>]*>)(.*?)(\s*<div class="tab-panel" id="panel-draft")'
    html, n = re.subn(panel, r'\1\n' + LEADERBOARD + r'\n        </div>\n\3', html, count=1, flags=re.S)
    if n != 1:
        raise SystemExit('leaderboard panel not found')
    html = html.replace('>🏆 Leaderboard<', '>Leaderboard<')
    html = html.replace('>💎 Draft value<', '>Draft value<')
    html = html.replace("            this.textContent = 'Refreshing…';\n", '')
    html = html.replace("        document.getElementById('sortColumn').addEventListener('change', renderCustom);\n", '')
    html = html.replace("        document.getElementById('sortOrder').addEventListener('change', renderCustom);\n", '')
    old_calls = '        renderEspn();\n        renderEff();\n        renderCustom();\n'
    if old_calls not in html:
        raise SystemExit('standings render calls missing')
    html = html.replace(old_calls, '        renderStandings();\n', 1)
    if 'function renderStandings(' not in html:
        call = '        showLastRefresh();\n'
        if call not in html:
            raise SystemExit('showLastRefresh call missing')
        html = html.replace(call, RENDER_FN + '\n' + call, 1)
    old_fn = '''        function showLastRefresh() {
            const el = document.getElementById('lastRefreshLabel');
            try {
                el.textContent = new Date(LAST_REFRESH_ISO).toLocaleString(undefined, {
                    dateStyle: 'medium',
                    timeStyle: 'short'
                });
            } catch (e) {
                el.textContent = LAST_REFRESH_ISO;
            }
        }'''
    new_fn = '''        function showLastRefresh() {
            const el = document.getElementById('lastRefreshLabel');
            try {
                const d = new Date(LAST_REFRESH_ISO);
                const long = d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
                const short = d.toLocaleString(undefined, { month: 'short', day: 'numeric' });
                el.innerHTML = '<span class="when-long">' + long + '</span><span class="when-short">' + short + '</span>';
            } catch (e) {
                el.textContent = LAST_REFRESH_ISO;
            }
        }'''
    if old_fn in html:
        html = html.replace(old_fn, new_fn, 1)
    return html
def ensure_draft_mobile(html):
    if '.m-only {' not in html and '    </style>' in html:
        html = html.replace('    </style>', '''        .m-only { display: none; flex-direction: column; gap: 10px; }
        .pick-card, .round-card { background: #fff; border-radius: 14px; padding: 14px; box-shadow: 0 6px 16px rgba(70,40,120,0.06); }
        .pick-card { display: flex; gap: 10px; align-items: flex-start; }
        .pick-card .rk { flex: none; width: 36px; font-weight: 800; font-size: 1.15rem; color: #2c2644; }
        .pick-card .rk.bad { color: #c0392b; }
        .pick-card .mid { flex: 1; min-width: 0; }
        .pick-card .name { font-weight: 800; color: #1c1730; line-height: 1.25; }
        .pick-card .meta { margin-top: 3px; color: #8b86a0; font-size: 0.84rem; line-height: 1.35; }
        .pick-card .val { flex: none; font-weight: 800; font-size: 1.35rem; text-align: right; font-variant-numeric: tabular-nums; }
        .pick-card .val.neg { color: #c0392b; }
        .pick-card .val.pos { color: #127a43; }
        .round-card .rh { font-weight: 800; color: #6236d4; margin-bottom: 4px; }
        .pick-line { display: flex; gap: 8px; align-items: flex-start; padding: 7px 0; border-top: 1px solid #f2eef8; font-size: 0.88rem; line-height: 1.35; }
        .pick-line i { width: 12px; height: 12px; border-radius: 3px; flex: none; margin-top: 4px; }
    </style>''', 1)
    if 'id="worstDrafts"' not in html and 'id="stealsByRound"' in html:
        html = html.replace('<div class="table-section" id="stealsByRound">', '''<div class="table-section" id="worstDrafts">
            <h2>Worst drafts</h2>
            <p class="hint">Biggest misses among picks that have played, worst value first. Value = pick number minus production rank.</p>
            <div class="m-only" id="worstCards"></div>
            <table class="slim">
                <thead><tr><th>#</th><th>Player</th><th>Drafted by</th><th class="number">Pick</th><th class="number">Rd</th><th class="number">FPts</th><th class="number">FPts/G</th><th class="number">Prod RK</th><th class="number">Value</th></tr></thead>
                <tbody id="tableWorst"></tbody>
            </table>
        </div>

        <div class="table-section" id="stealsByRound">''', 1)
    if 'id="valueCards"' not in html:
        html = re.sub(r'\n([ \t]*)<table>(\s*<thead>\s*<tr>\s*<th>#</th>\s*<th>Player</th>\s*<th>Drafted by</th>)',
                      r'\n\1<div class="m-only" id="valueCards"></div>\n\1<table>\2', html, count=1)
    if 'id="roundCards"' not in html:
        html = re.sub(r'\n([ \t]*)<table>(\s*<thead>\s*<tr>\s*<th>Rd</th>)',
                      r'\n\1<div class="m-only" id="roundCards"></div>\n\1<table>\2', html, count=1)
    if 'id="boardRounds"' not in html:
        html = html.replace('<table class="board">', '<div class="m-only" id="boardRounds"></div>\n            <table class="board">', 1)
    if 'id="gradeCards"' not in html:
        html = re.sub(r'\n([ \t]*)<table>(\s*<thead>\s*<tr>\s*<th>#</th>\s*<th>Team</th>\s*<th class="number">Draft FPts</th>)',
                      r'\n\1<div class="m-only" id="gradeCards"></div>\n\1<table>\2', html, count=1)
    if 'id="undraftedCards"' not in html:
        html = re.sub(r'\n([ \t]*)<table>(\s*<thead>\s*<tr>\s*<th>#</th>\s*<th>Player</th>\s*<th>Team</th>)',
                      r'\n\1<div class="m-only" id="undraftedCards"></div>\n\1<table>\2', html, count=1)
    if 'function renderWorst(' not in html and 'function renderValue(' in html:
        extra = '''
        function renderWorst() {
            const list = DRAFT.filter(p => p.played && p.value != null).sort((a, b) => a.value - b.value || a.pick - b.pick).slice(0, 12);
            const cards = document.getElementById('worstCards');
            const body = document.getElementById('tableWorst');
            const row = (p, i) => '<article class="pick-card"><div class="rk bad">#' + (i + 1) + '</div><div class="mid"><div class="name">' + esc(p.player) + '</div><div class="meta">' + esc(p.drafted_by) + ' · Pick ' + p.pick + ' · Rd ' + p.round + '</div><div class="meta">' + fnum(p.fpts_tot) + ' FPts · ' + fnum(p.fpts_avg, 1) + '/G · Prod ' + (p.prod_rank == null ? '—' : p.prod_rank) + '</div></div><div class="val neg">' + (p.value > 0 ? '+' : '') + p.value + '</div></article>';
            if (cards) cards.innerHTML = list.map(row).join('');
            if (body) body.innerHTML = list.map((p, i) => '<tr><td class="rank">' + (i + 1) + '</td><td>' + esc(p.player) + '</td><td>' + esc(p.drafted_by) + '</td><td class="number">' + p.pick + '</td><td class="number">' + p.round + '</td><td class="number">' + fnum(p.fpts_tot) + '</td><td class="number">' + fnum(p.fpts_avg, 1) + '</td><td class="number">' + (p.prod_rank == null ? '—' : p.prod_rank) + '</td><td class="number">' + fmtVal(p.value) + '</td></tr>').join('');
        }
        function renderValue() {
            const view = document.getElementById('valueView').value;
            const team = document.getElementById('valueTeam').value;
            let list = DRAFT.filter(p => !team || p.drafted_by === team);
            if (view === 'steals') list = list.filter(p => p.played).sort((a, b) => b.value - a.value).slice(0, 15);
            else if (view === 'busts') list = list.filter(p => p.played && p.round <= 4).sort((a, b) => a.value - b.value).slice(0, 10);
            else list = list.sort((a, b) => (b.value == null ? -999 : b.value) - (a.value == null ? -999 : a.value));
            const cards = document.getElementById('valueCards');
            if (cards) cards.innerHTML = list.map((p, i) => '<article class="pick-card"><div class="rk">#' + (i + 1) + '</div><div class="mid"><div class="name">' + esc(p.player) + '</div><div class="meta">' + esc(p.drafted_by) + ' · Pick ' + p.pick + ' · Rd ' + p.round + '</div></div><div class="val ' + (p.value < 0 ? 'neg' : 'pos') + '">' + (p.value > 0 ? '+' : '') + p.value + '</div></article>').join('');
            const body = document.getElementById('tableValue');
            if (body) body.innerHTML = list.map((p, i) => '<tr><td>' + (i + 1) + '</td><td>' + esc(p.player) + '</td><td>' + esc(p.drafted_by) + '</td><td class="number">' + p.pick + '</td><td class="number">' + p.round + '</td><td class="number">' + fnum(p.fpts_tot) + '</td><td class="number">' + fnum(p.fpts_avg, 1) + '</td><td class="number">' + (p.prod_rank == null ? '—' : p.prod_rank) + '</td><td class="number">' + fmtVal(p.value) + '</td></tr>').join('');
        }
        function renderByRound() {
            const cards = document.getElementById('roundCards');
            if (cards) cards.innerHTML = BY_ROUND.map(r => '<article class="round-card"><div class="rh">Round ' + r.round + '</div><div class="pick-line"><span><b>Best</b> ' + esc(r.best) + ' · ' + esc(r.best_team) + ' · pick ' + r.best_pick + ' · ' + r.best_fpts + ' FPts</span></div><div class="pick-line"><span><b>Worst</b> ' + esc(r.worst) + ' · pick ' + r.worst_pick + ' · ' + r.worst_fpts + ' FPts</span></div></article>').join('');
            const body = document.getElementById('tableByRound');
            if (body) body.innerHTML = BY_ROUND.map(r => '<tr><td>' + r.round + '</td><td>' + esc(r.best) + '</td><td>' + esc(r.best_team) + '</td><td>' + r.best_pick + '</td><td>' + r.best_fpts + '</td><td>' + r.best_rank + '</td><td>' + esc(r.worst) + '</td><td>' + r.worst_fpts + '</td><td>' + r.round_avg_fpts.toFixed(1) + '</td></tr>').join('');
        }
        function renderBoard() {
            const rounds = document.getElementById('boardRounds');
            if (!rounds) return;
            let html = '';
            for (let r = 1; r <= 13; r++) {
                html += '<article class="round-card"><div class="rh">Round ' + r + '</div>' + DRAFT_TEAMS.map(t => {
                    const p = DRAFT.find(x => x.round === r && x.drafted_by === t);
                    if (!p) return '';
                    const v = p.played ? ((p.value > 0 ? '+' : '') + p.value) : '—';
                    return '<div class="pick-line"><span><b>' + esc(p.player) + '</b> · ' + esc(t) + ' · #' + p.pick + ' · ' + v + '</span></div>';
                }).join('') + '</article>';
            }
            rounds.innerHTML = html;
            const head = document.getElementById('boardHead');
            const body = document.getElementById('boardBody');
            if (head) head.innerHTML = '<th>Rd</th>' + DRAFT_TEAMS.map(t => '<th>' + esc(t) + '</th>').join('');
            if (body) {
                let rows = '';
                for (let r = 1; r <= 13; r++) rows += '<tr><td>' + r + '</td>' + DRAFT_TEAMS.map(t => { const p = DRAFT.find(x => x.round === r && x.drafted_by === t); return '<td>' + (p ? esc(p.player) : '') + '</td>'; }).join('') + '</tr>';
                body.innerHTML = rows;
            }
        }
'''
        html = html.replace('\n    </script>', extra + '\n    </script>', 1)
        if 'renderWorst();' not in html:
            html = html.replace('renderUndrafted();\n', 'renderUndrafted();\n        renderWorst();\n', 1)
    return html

def ensure_controls(html):
    if 'id="rankMode"' not in html and 'id="teamCards"' in html and '<p class="formula">Avg = season points ÷ games</p>' in html:
        html = html.replace('<p class="formula">Avg = season points ÷ games</p>\n        <div class="cards" id="teamCards"></div>',
                            LEADERBOARD.split('<div class="cards" id="teamCards"></div>')[0] + '<div class="cards" id="teamCards"></div>', 1)
        old_tail = '''                <tbody id="tableSlim"></tbody>
            </table>
        </div>

        </div>'''
        new_tail = '''                <tbody id="tableSlim"></tbody>
            </table>
        </div>
''' + LEADERBOARD.split('<tbody id="tableSlim"></tbody>')[1]
        # LEADERBOARD tail includes season board but not the panel close. Keep panel close.
        if 'id="tableSeason"' not in html and 'id="tableSlim"' in html:
            season = '''
        <div class="section-head spaced">
            <h2>Season totals</h2>
            <p class="formula">ESPN order · season points and games</p>
        </div>
        <div class="cards" id="seasonCards"></div>
        <div class="board-wrap">
            <table class="slim">
                <thead><tr><th>Rank</th><th>Team</th><th>Owner</th><th class="number">Total</th><th class="number">Games</th></tr></thead>
                <tbody id="tableSeason"></tbody>
            </table>
        </div>
'''
            needle = '                <tbody id="tableSlim"></tbody>\n            </table>\n        </div>\n'
            if needle in html:
                html = html.replace(needle, needle + season, 1)
    if 'class="icon-btn"' not in html and '<button type="button" class="chip" id="refreshBtn"' in html:
        i = html.find('<button type="button" class="chip" id="refreshBtn"')
        j = html.find('</button>', i)
        stamp = HEADER[HEADER.find('<div class="stamp">'):HEADER.find('    </header>')].strip()
        html = html[:i] + stamp + html[j+len('</button>'):]
    if '.mode-pills' not in html and '    </style>' in html:
        html = html.replace('    </style>', '''        .stamp { display: flex; align-items: center; gap: 8px; color: #fff; font-size: 0.75rem; font-weight: 650; }
        .icon-btn { width: 34px; height: 34px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.5); background: transparent; color: #fff; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; padding: 0; }
        .section-head h2 { margin: 0 0 2px; font-size: 1.45rem; color: #1c1730; }
        .section-head.spaced { margin-top: 28px; }
        .mode-pills, .view-pills { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 14px; }
        .pill { border: none; background: #fff; color: #5c5678; font-weight: 700; border-radius: 999px; padding: 8px 12px; cursor: pointer; font-family: inherit; }
        .pill.active { background: #6841c9; color: #fff; }
        .card .subtot { color: #a39eb6; font-size: 0.75rem; }
        table.slim td.hot { color: #6236d4; font-weight: 800; }
        table.slim td.muted-num { color: #9a94ad; font-weight: 500; }
        #panel-draft .table-section[hidden] { display: none !important; }
    </style>''', 1)
    if 'id="draftPills"' not in html and 'id="panel-draft"' in html:
        pills = '''        <div class="view-pills" id="draftPills" role="tablist">
            <button type="button" class="pill" data-view="worst">Worst drafts</button>
            <button type="button" class="pill active" data-view="steals" aria-selected="true">Top 15 steals</button>
            <button type="button" class="pill" data-view="busts">Biggest busts</button>
            <button type="button" class="pill" data-view="all">All drafted</button>
            <button type="button" class="pill" data-view="rounds">Steals by round</button>
            <button type="button" class="pill" data-view="board">Draft board</button>
            <button type="button" class="pill" data-view="grades">Team grades</button>
            <button type="button" class="pill" data-view="undrafted">Undrafted</button>
        </div>
'''
        html = html.replace('<div class="tab-panel" id="panel-draft" role="tabpanel" hidden>\n',
                            '<div class="tab-panel" id="panel-draft" role="tabpanel" hidden>\n' + pills, 1)
        start = html.find('id="panel-draft"')
        end = html.find('<p class="footer">')
        if start != -1 and end != -1:
            mid = html[start:end]
            mid = re.sub(r'\s*<div class="note">.*?</div>', '', mid, flags=re.S)
            mid = re.sub(r'\s*<p class="hint">.*?</p>', '', mid)
            mid = re.sub(r'\s*<div class="controls">[\s\S]*?\n            <div class="m-only" id="valueCards">', '\n            <div class="m-only" id="valueCards">', mid, count=1)
            mid = mid.replace('<h2>Best bang for the buck</h2>', '<h2 id="valueTitle">Top 15 steals</h2>')
            for sid in ['worstDrafts', 'stealsByRound', 'draftBoard', 'draftGrades', 'undrafted']:
                mid = mid.replace('<div class="table-section" id="%s">' % sid, '<div class="table-section" id="%s" hidden>' % sid)
            html = html[:start] + mid + html[end:]
        html = html.replace("        document.getElementById('valueView').addEventListener('change', renderValue);\n", '')
        html = html.replace("        document.getElementById('valueTeam').addEventListener('change', renderValue);\n", '')
        html = re.sub(r'\n        \(function initTeamFilter\(\) \{.*?\}\)\(\);\n', '\n', html, flags=re.S)
    if 'function showDraftView(' not in html and 'function renderValue(' in html:
        html = html.replace('\n    </script>', '''
        var rankMode = 'avg';
        var draftListMode = 'steals';
        function renderStandings() {
            const mode = rankMode === 'total' ? 'total' : 'avg';
            const sorted = [...currentData].sort((a, b) => mode === 'total' ? (b.tot - a.tot || a.seasonRk - b.seasonRk) : (b.avgPts - a.avgPts || a.seasonRk - b.seasonRk));
            const cards = document.getElementById('teamCards');
            const slim = document.getElementById('tableSlim');
            if (cards) cards.innerHTML = sorted.map((t, i) => '<article class="card"><div class="rk' + (i === 0 ? ' gold' : '') + '">#' + (i + 1) + '</div><div class="who"><div class="name">' + esc(t.team) + '</div><div class="owner">' + esc(t.owner || '') + '</div></div><div class="stat"><div class="lbl">' + (mode === 'total' ? 'TOTAL' : 'AVG') + '</div><div class="avg">' + (mode === 'total' ? num(t.tot) : fmtAvg(t.avgPts)) + '</div><div class="games">' + t.gp + ' games</div>' + (mode === 'avg' ? '<div class="subtot">' + num(t.tot) + ' total</div>' : '') + '</div></article>').join('');
            if (slim) slim.innerHTML = sorted.map((t, i) => '<tr><td class="rank">' + (i + 1) + '</td><td class="team">' + esc(t.team) + '</td><td>' + esc(t.owner || '') + '</td><td class="number' + (mode === 'total' ? ' hot' : ' muted-num') + '">' + num(t.tot) + '</td><td class="number">' + t.gp + '</td><td class="number' + (mode === 'avg' ? ' hot' : ' muted-num') + '">' + fmtAvg(t.avgPts) + '</td></tr>').join('');
            const espn = [...currentData].sort((a, b) => a.seasonRk - b.seasonRk);
            const sc = document.getElementById('seasonCards');
            const st = document.getElementById('tableSeason');
            if (sc) sc.innerHTML = espn.map(t => '<article class="card"><div class="rk">#' + t.seasonRk + '</div><div class="who"><div class="name">' + esc(t.team) + '</div><div class="owner">' + esc(t.owner || '') + '</div></div><div class="stat"><div class="lbl">TOTAL</div><div class="avg">' + num(t.tot) + '</div><div class="games">' + t.gp + ' games</div></div></article>').join('');
            if (st) st.innerHTML = espn.map(t => '<tr><td class="rank">' + t.seasonRk + '</td><td class="team">' + esc(t.team) + '</td><td>' + esc(t.owner || '') + '</td><td class="number hot">' + num(t.tot) + '</td><td class="number">' + t.gp + '</td></tr>').join('');
        }
        function showDraftView(name) {
            const map = { worst: 'worstDrafts', steals: 'bangForBuck', busts: 'bangForBuck', all: 'bangForBuck', rounds: 'stealsByRound', board: 'draftBoard', grades: 'draftGrades', undrafted: 'undrafted' };
            const id = map[name] || 'bangForBuck';
            document.querySelectorAll('#draftPills .pill').forEach(p => p.classList.toggle('active', p.dataset.view === name));
            document.querySelectorAll('#panel-draft .table-section').forEach(s => { s.hidden = s.id !== id; });
            if (id === 'bangForBuck') { draftListMode = (name === 'busts' || name === 'all') ? name : 'steals'; if (typeof renderValue === 'function') renderValue(); }
        }
        function renderValue() {
            const view = draftListMode;
            let list = DRAFT.slice();
            if (view === 'steals') list = list.filter(p => p.played).sort((a, b) => b.value - a.value).slice(0, 15);
            else if (view === 'busts') list = list.filter(p => p.played && p.round <= 4).sort((a, b) => a.value - b.value).slice(0, 10);
            else list = list.filter(p => p.value != null).sort((a, b) => b.value - a.value);
            const cards = document.getElementById('valueCards');
            const body = document.getElementById('tableValue');
            if (cards) cards.innerHTML = list.map((p, i) => '<article class="pick-card"><div class="rk">#' + (i + 1) + '</div><div class="mid"><div class="name">' + esc(p.player) + '</div><div class="meta">' + esc(p.drafted_by) + ' · Pick ' + p.pick + ' · Rd ' + p.round + '</div></div><div class="val">' + (p.value > 0 ? '+' : '') + p.value + '</div></article>').join('');
            if (body) body.innerHTML = list.map((p, i) => '<tr><td>' + (i + 1) + '</td><td>' + esc(p.player) + '</td><td>' + esc(p.drafted_by) + '</td><td class="number">' + p.pick + '</td><td class="number">' + p.round + '</td><td class="number">' + fnum(p.fpts_tot) + '</td><td class="number">' + fnum(p.fpts_avg, 1) + '</td><td class="number">' + (p.prod_rank == null ? '—' : p.prod_rank) + '</td><td class="number">' + fmtVal(p.value) + '</td></tr>').join('');
            const title = document.getElementById('valueTitle');
            if (title) title.textContent = view === 'busts' ? 'Biggest busts' : view === 'all' ? 'All drafted' : 'Top 15 steals';
        }
        document.getElementById('rankMode') && document.getElementById('rankMode').addEventListener('click', function (e) {
            const btn = e.target.closest('[data-mode]'); if (!btn) return;
            rankMode = btn.dataset.mode === 'total' ? 'total' : 'avg';
            this.querySelectorAll('.pill').forEach(p => p.classList.toggle('active', p === btn));
            renderStandings();
        });
        document.getElementById('draftPills') && document.getElementById('draftPills').addEventListener('click', function (e) {
            const btn = e.target.closest('[data-view]'); if (!btn) return; showDraftView(btn.dataset.view);
        });
        showDraftView('steals');
    </script>''', 1)
    return html

def ensure_retro(html):
    # Draft retro reads the baked DRAFT + UNDRAFTED snapshot. Live ESPN player stats are not scraped here.
    if 'data-tab="retro"' not in html:
        html = html.replace(
            '<button type="button" class="tab" role="tab" data-tab="draft" aria-selected="false">Draft value</button>',
            '<button type="button" class="tab" role="tab" data-tab="draft" aria-selected="false">Draft value</button>\n            <button type="button" class="tab" role="tab" data-tab="retro" aria-selected="false">Draft retro</button>',
            1)
    if 'id="panel-retro"' not in html and '<p class="footer">' in html:
        html = html.replace('<p class="footer">', '''<div class="tab-panel" id="panel-retro" role="tabpanel" hidden>
        <div class="draft-refresh"><span>Draft stats <span class="draftRefreshLabel">—</span></span>
            <button type="button" class="icon-btn draft-refresh-btn" aria-label="Refresh draft stats" title="Refresh draft stats">↻</button></div>
        <div class="view-pills" id="retroTeams" role="tablist"></div>
        <div class="section-head"><h2 id="retroTeamName">Team The Mushroom</h2><p class="formula" id="retroSummary">—</p></div>
        <div class="retro-list" id="retroCards"></div>
        </div>
        <p class="footer">''', 1)
    if 'DRAFT_REFRESH_ISO' not in html:
        html = html.replace('const LAST_REFRESH_ISO = "', 'const DRAFT_REFRESH_ISO = "";\n        // Filled from draft_value.json generated_at when the rebuild embeds picks.\n        const LAST_REFRESH_ISO = "', 1)
    if 'function renderRetro(' not in html and 'function showTab(' in html:
        html = html.replace('function showTab(name) {', '''function renderRetro() {
            const teams = [MUSHROOM].concat((typeof DRAFT_TEAMS === 'undefined' ? [] : DRAFT_TEAMS).filter(t => t !== MUSHROOM));
            const picker = document.getElementById('retroTeams');
            if (!picker || typeof DRAFT === 'undefined') return;
            let retroTeam = (picker.querySelector('.pill.active') || {}).dataset ? picker.querySelector('.pill.active').dataset.team : MUSHROOM;
            if (!retroTeam) retroTeam = MUSHROOM;
            picker.innerHTML = teams.map(t => '<button type="button" class="pill' + (t === retroTeam ? ' active' : '') + '" data-team="' + esc(t) + '">' + esc(t) + '</button>').join('');
            const picks = DRAFT.filter(p => p.drafted_by === retroTeam).sort((a, b) => a.pick - b.pick);
            let hits = 0, biggest = null;
            const poolOf = (n) => DRAFT.filter(p => p.pick >= n).concat((typeof UNDRAFTED === 'undefined' ? [] : UNDRAFTED).map(u => ({ player: u.player, fpts_tot: u.fpts_tot, fpts_avg: u.fpts_avg, prod_rank: null, would_rank: u.would_rank, played: u.fpts_tot != null, drafted_by: null })));
            const rankOf = (p) => p.prod_rank != null ? p.prod_rank : (p.would_rank != null ? p.would_rank : null);
            const better = (a, b) => { if (a.played && !b.played) return true; if (b.played && !a.played) return false; const ar = rankOf(a), br = rankOf(b); if (ar != null && br != null && ar !== br) return ar < br; return (a.fpts_avg || -1) > (b.fpts_avg || -1); };
            document.getElementById('retroCards').innerHTML = picks.map(p => {
                const pool = poolOf(p.pick);
                const best = pool.reduce((b, x) => b && !better(x, b) ? b : x, null);
                const hit = best && best.player === p.player;
                if (hit) hits++; else if (!biggest || (rankOf(p) || 999) - (rankOf(best) || 0) > biggest.gap) biggest = { gap: (rankOf(p) || 999) - (rankOf(best) || 0), pick: p.pick, took: p.player, best: best.player };
                return '<article class="retro-card ' + (hit ? 'hit' : 'miss') + '"><div class="retro-kicker">Round ' + p.round + ' · Pick ' + p.pick + '</div><div class="retro-name">You took ' + esc(p.player) + '</div><div class="retro-meta">' + (best ? ('Best available: ' + esc(best.player) + (best.drafted_by ? (' · drafted by ' + esc(best.drafted_by)) : ' · Undrafted')) : '') + '</div><div class="' + (hit ? 'tag-hit' : 'tag-miss') + '">' + (hit ? 'Took the best available' : 'Left value on the board') + '</div></article>';
            }).join('');
            const sum = document.getElementById('retroSummary');
            if (sum) sum.textContent = hits + ' of ' + picks.length + ' picks were the best available.' + (biggest ? (' Biggest miss: pick ' + biggest.pick + ', you took ' + biggest.took + ', best available was ' + biggest.best + '.') : '');
            const name = document.getElementById('retroTeamName');
            if (name) name.textContent = retroTeam;
        }
        document.getElementById('retroTeams') && document.getElementById('retroTeams').addEventListener('click', function (e) {
            const btn = e.target.closest('[data-team]'); if (!btn) return;
            this.querySelectorAll('.pill').forEach(p => p.classList.toggle('active', p === btn));
            renderRetro();
        });
        function showTab(name) {''', 1)
        html = html.replace("if (name !== 'draft') name = 'leaderboard';", "if (name !== 'draft' && name !== 'retro') name = 'leaderboard';", 1)
        if "getElementById('panel-retro')" not in html:
            html = html.replace("document.getElementById('panel-draft').hidden = name !== 'draft';",
                                "document.getElementById('panel-draft').hidden = name !== 'draft';\n            const retro = document.getElementById('panel-retro'); if (retro) retro.hidden = name !== 'retro';", 1)
        if 'renderRetro();' not in html.split('function renderRetro')[-1]:
            html = html.replace('showTab(location.hash.slice(1));', 'renderRetro();\n        showTab(location.hash.slice(1));', 1)
    return html

html=open(B+'index.html').read()
_layout=ensure_retro(ensure_controls(ensure_draft_mobile(ensure_responsive_layout(html))))
if _layout!=html:
    open(B+'index.html','w').write(_layout)
