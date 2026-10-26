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
    rows.append('            { seasonRk: %d, team: %s, fgm: %d, fga: %d, ftm: %d, fta: %d, tpm: %d, reb: %d, ast: %d, stl: %d, blk: %d, to: %d, pts: %d, tot: %d, gp: %d }'%(
        t['rank'],json.dumps(t['team']),p['FGM'],p['FGA'],p['FTM'],p['FTA'],p['3PM'],p['REB'],p['AST'],p['STL'],p['BLK'],p['TO'],p['PTS'],t['season_points_TOT'],t['GP']))
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
