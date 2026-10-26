import json, datetime
D='/workspace/barchashim/data/'
draft=json.load(open(D+'draft.json'))
ros=json.load(open(D+'rosters_flat.json'))
fa=json.load(open(D+'free_agents.json'))
byname={r['player']:r for r in ros}
faby={f['player']:f for f in fa}
rows=[]
for p in draft['picks']:
    r=byname.get(p['player']); src='rostered'
    if r is None:
        r=faby.get(p['player']); src='dropped' if r else 'unknown'
    gp=None
    tot=r.get('fpts_tot') if r else None; avg=r.get('fpts_avg') if r else None
    if tot is not None and avg: gp=round(tot/avg)
    rows.append(dict(pick=p['pick'],round=p['round'],pick_in_round=p['pick_in_round'],drafted_by=p['team'],
        current_team=(r.get('fantasy_team') if src=='rostered' else ('Waivers/FA')) if r else None,
        player=p['player'],position=p['position'],nba_team=p['nba_team'],status=src,
        injury=(r.get('injury') if r else None),
        fpts_tot=tot,fpts_avg=avg,gp_est=gp,played=tot is not None))
played=[x for x in rows if x['played']]
# competition-rank by fpts_tot among drafted players who played; DNP get rank = len(played)+1.. (not scored)
s=sorted(played,key=lambda x:(-x['fpts_tot'],-(x['fpts_avg'] or 0)))
for i,x in enumerate(s):
    x['fpts_rank']=i+1
s2=sorted(played,key=lambda x:-(x['fpts_avg'] or 0))
for i,x in enumerate(s2): x['avg_rank']=i+1
s3=sorted(played,key=lambda x:((x['fpts_rank']+x['avg_rank'])/2,-x['fpts_tot']))
for i,x in enumerate(s3): x['prod_rank']=i+1
for x in rows:
    if x['played']:
        x['value']=x['pick']-x['prod_rank']
        x['steal']= (x['round']>=4 and x['prod_rank']<=20) or x['value']>=40
        x['bust']= x['round']<=3 and x['value']<=-25
    else:
        x['fpts_rank']=None;x['prod_rank']=None;x['avg_rank']=None;x['value']=None;x['steal']=False;x['bust']=False
steals=sorted([x for x in played],key=lambda x:-x['value'])
busts=sorted([x for x in played if x['round']<=4],key=lambda x:x['value'])
best_by_round=[]
for rd in range(1,14):
    rr=[x for x in played if x['round']==rd]
    b=min(rr,key=lambda x:x['prod_rank'])
    w=max(rr,key=lambda x:x['prod_rank'])
    best_by_round.append(dict(round=rd,best=b['player'],best_team=b['drafted_by'],best_pick=b['pick'],best_fpts=b['fpts_tot'],best_rank=b['prod_rank'],
        worst=w['player'],worst_pick=w['pick'],worst_fpts=w['fpts_tot'],round_avg_fpts=round(sum(x['fpts_tot'] for x in rr)/len(rr),1)))
teams={}
for x in rows:
    t=teams.setdefault(x['drafted_by'],dict(team=x['drafted_by'],draft_fpts=0,value_sum=0,steals=0,busts=0,dnp=0,best=None))
    if x['played']:
        t['draft_fpts']+=x['fpts_tot']; t['value_sum']+=x['value']; t['steals']+=x['steal']; t['busts']+=x['bust']
        if t['best'] is None or x['value']>t['best'][1]: t['best']=(x['player'],x['value'])
    else: t['dnp']+=1
tg=sorted(teams.values(),key=lambda t:-t['draft_fpts'])
for t in tg: t['best_value_pick']=t['best'][0]; t['best_value']=t['best'][1]; del t['best']
undrafted=sorted([r for r in ros if r['draft_pick'] is None and r['fpts_tot'] is not None],key=lambda r:-r['fpts_tot'])
und=[dict(player=r['player'],fantasy_team=r['fantasy_team'],position=r['eligible'],fpts_tot=r['fpts_tot'],fpts_avg=r['fpts_avg']) for r in undrafted]
# where they'd rank among drafted
for u in und: u['would_rank']=1+sum(1 for x in played if x['fpts_tot']>u['fpts_tot'])
out=dict(generated_at=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
  method="Production rank = order of the average of FPts-total rank and FPts/G rank among drafted players who have played. Value = overall pick # minus production rank among the drafted players who have played (1 = most fantasy points). Positive = outperforming draft slot. STEAL = round>=4 and top-20 FPts, or value>=40. BUST = rounds 1-3 and value<=-25. Players with no games yet are excluded from ranks.",
  picks=rows,steals=steals[:15],busts=busts[:8],best_by_round=best_by_round,team_draft_grades=tg,undrafted_gems=und,
  dnp=[x for x in rows if not x['played']])
json.dump(out,open(D+'draft_value.json','w'),indent=1)
print('played',len(played))
for x in steals[:20]: print(x['value'],x['prod_rank'],x['pick'],x['round'],x['player'],x['drafted_by'],x['current_team'],x['fpts_tot'],x['fpts_avg'],x['fpts_rank'],x['steal'])
print('--busts')
for x in busts[:10]: print(x['value'],x['prod_rank'],x['pick'],x['player'],x['fpts_tot'],x['fpts_rank'],x['gp_est'])
print('--rounds');[print(b) for b in best_by_round]
print('--teams');[print(t) for t in tg]
print('--und');[print(u) for u in und[:10]]
print('--dnp',[ (x['player'],x['pick'],x['status']) for x in out['dnp']])
print('steal count',sum(x['steal'] for x in rows))
