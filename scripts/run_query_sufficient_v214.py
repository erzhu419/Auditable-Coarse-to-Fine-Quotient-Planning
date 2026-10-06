"""Paid finite-library identity learning, with all evaluation after decisions freeze."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from acfqp.science import query_sufficient_v214 as core
from acfqp.science import latent_route_task_v213 as task
from scripts import run_conditioned_mechanisms_v205 as saved
OUTPUT=ROOT/'reports/query_sufficient_v214'
ARMS=('SET','STRICT','LOCAL','ORACLE')
SOURCE_FILES=(
 'src/acfqp/science/structured_route_task_v201.py',
 'src/acfqp/science/continual_route_kernels_v202.py',
 'src/acfqp/science/robust_route_planning_v203.py',
 'src/acfqp/science/target_risk_acquisition_v204.py',
 'src/acfqp/science/conditioned_mechanisms_v205.py',
 'src/acfqp/science/mechanism_switch_task_v205.py',
 'src/acfqp/science/online_lifecycle_v206.py',
 'src/acfqp/science/constrained_acquisition_v208.py',
 'src/acfqp/science/contracted_risk_reuse_v209.py',
 'src/acfqp/science/strategic_maintenance_v210.py',
 'src/acfqp/science/latent_mechanisms_v213.py',
 'src/acfqp/science/query_sufficient_v214.py',
 'src/acfqp/science/latent_route_task_v213.py',
 'scripts/run_conditioned_mechanisms_v205.py',
 'scripts/analyze_conditioned_mechanisms_v205.py',
 'scripts/run_query_sufficient_v214.py',
 'scripts/analyze_latent_mechanisms_v213.py',
 'scripts/analyze_query_sufficient_v214.py',
 'tests/test_query_sufficient_v214.py',
 'specs/QUERY_SUFFICIENT_V214.md',
 'reports/v214_runtime_tmp/run_stage.py')
save=saved.save
mean=saved.mean

def score(plan,law,case,spent):
    pure=core.vectors(case,law)
    actual=[sum(weight*pure[name][i] for name,weight in plan['mix']) for i in range(3)]
    coverage=all(lo<=law[op][cat]<=hi for op,env in plan['envelopes'].items() for cat,(lo,hi) in env['bounds'].items())
    return dict(spent=spent,actual=actual,actual_utility=actual[0]+4*actual[2],
                risk_upper=plan['risk_upper'],utility_lower=plan['utility_lower'],
                violation=actual[1]>F(1,20),coverage=coverage)

def query_score(decision,law,case):
    pure=core.vectors(case,law);weights={'reward':(1,0,0),'goal':(1,0,4),'risk':(1,4,4)};result={}
    for q,w in weights.items():
        utility=lambda v:v[0]*w[0]-v[1]*w[1]+v[2]*w[2]
        actual=pure[decision[q]['policy']]
        best=max(utility(v) for v in pure.values())
        result[q]=dict(policy=decision[q]['policy'],actual=actual,utility=utility(actual),regret=best-utility(actual))
    return result

def summarize(results,work):
    arms={}
    for arm in ARMS:
        rows=[r for r in results if r['arm']==arm];late=[r for r in rows if r['index']>=15]
        points=[p for r in rows for p in r['history']]
        arms[arm]=dict(total_samples=sum(r['spent'] for r in rows),source_samples=sum(r['spent'] for r in rows if r['index']<3),
            target_samples=sum(r['spent'] for r in rows if r['index']>=3),late_samples=sum(r['spent'] for r in late),
            late_certified=sum(r['certified'] for r in late),
            late_transferred=sum(r['transferred'] and r['transfer_correct'] for r in late),
            late_identified=sum(r['identified'] and r['identity_correct'] for r in late),
            wrong_transfers=sum(r['transferred'] and not r['transfer_correct'] for r in rows),
            late_utility=mean(float(r['terminal']['actual_utility']) for r in late),
            late_post_regret=mean(float(v['regret']) for r in late for v in r['query_post'].values()),
            history_violations=sum(p['violation'] for p in points),max_failure=max(float(p['actual'][1]) for p in points),
            coverage=mean(p['coverage'] for p in points),member_fallbacks=sum(r['fallback'] for r in rows))
    contrasts={key:[] for key in ('local_minus_set_samples','strict_minus_set_samples',
        'set_minus_local_late_utility','set_minus_strict_post_regret','set_minus_oracle_samples')}
    for life in range(12):
        rows=[r for r in results if r['life']==life];totals={arm:sum(r['spent'] for r in rows if r['arm']==arm) for arm in ARMS}
        utility={arm:mean(float(r['terminal']['actual_utility']) for r in rows if r['arm']==arm and r['index']>=15) for arm in ARMS}
        regret={arm:mean(float(v['regret']) for r in rows if r['arm']==arm and r['index']>=15 for v in r['query_post'].values()) for arm in ARMS}
        contrasts['local_minus_set_samples'].append(totals['LOCAL']-totals['SET'])
        contrasts['strict_minus_set_samples'].append(totals['STRICT']-totals['SET'])
        contrasts['set_minus_oracle_samples'].append(totals['SET']-totals['ORACLE'])
        contrasts['set_minus_local_late_utility'].append(utility['SET']-utility['LOCAL'])
        contrasts['set_minus_strict_post_regret'].append(regret['SET']-regret['STRICT'])
    rng=random.Random(215900);samples={key:[] for key in contrasts}
    for _ in range(5000):
        indices=[rng.randrange(12) for _ in range(12)];work['bootstrap_index_draws']+=12
        for key,rows in contrasts.items():samples[key].append(mean(rows[i] for i in indices));work['bootstrap_mean_terms']+=12
    intervals={key:dict(mean=mean(rows),ci=[sorted(samples[key])[124],sorted(samples[key])[4874]]) for key,rows in contrasts.items()}
    a=arms['SET'];risk_points=[p for r in results if r['arm']=='SET' for p in r['history']]
    conditions=dict(COST=intervals['local_minus_set_samples']['mean']>=64 and intervals['local_minus_set_samples']['ci'][0]>0,
        QUALITY=a['late_certified']>=108 and a['late_certified']>=arms['LOCAL']['late_certified'] and a['late_utility']>=2
                and intervals['set_minus_local_late_utility']['ci'][0]>=-.05,
        RISK=all(p['actual'][1]<=F(1,20) and p['risk_upper']<=F(1,20) for p in risk_points),
        APPLICABILITY=a['late_transferred']>=108 and a['late_post_regret']<=.05,
        STOP_EFFECT=intervals['strict_minus_set_samples']['ci'][0]>0 and intervals['set_minus_strict_post_regret']['ci'][1]<=.01)
    return dict(complete=True,arms=arms,contrasts=contrasts,bootstrap=intervals,conditions=conditions,
                decision='QUERY_SUFFICIENT_SUPPORTED' if all(conditions.values()) else 'QUERY_SUFFICIENT_NOT_SUPPORTED')

def run():
    begun=perf_counter();OUTPUT.mkdir(parents=True,exist_ok=False)
    for name in SOURCE_FILES:
        path=OUTPUT/'source_code'/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,path)
    save(OUTPUT/'source_manifest.json',[dict(path=name) for name in SOURCE_FILES])
    work={arm:Counter() for arm in ARMS};records=[];cases_saved=[]
    for life in range(12):
        cases,laws,identities=task.world(life);cases_saved.append(dict(life=life,cases=cases))
        anchors={arm:[] for arm in ARMS}
        for index,case in enumerate(cases):
            source=index<3;seeds={op:216000+(life*27+index)*3+i for i,op in enumerate(core.OPERATORS)}
            for arm in ARMS:
                member=core.empty();rng={op:random.Random(seed) for op,seed in seeds.items()}
                library=anchors[arm] if not source and arm!='LOCAL' else []
                identity=identities[index] if arm=='ORACLE' else None
                plan=core.make_plan(member,library,case,arm,work[arm],identity)
                row=dict(life=life,index=index,case=case,arm=arm,seeds=seeds,initial_plan=plan,
                         initial_query=core.queries(plan),batches=[])
                spent=0;consumed=Counter()
                while True:
                    choice=core.choose(member,library,case,arm,plan,spent,work[arm],source)
                    if choice is None:break
                    op=choice['operator'];increments=dict.fromkeys(core.ALPHABETS[op],0)
                    progress=dict(draw_end=consumed[op],operator_n=consumed[op],spent=spent)
                    saved.draw(rng[op],laws[index],op,increments,16,work[arm],progress)
                    for cat,k in increments.items():member[op][cat]+=k
                    spent=progress['spent'];consumed[op]=progress['operator_n']
                    plan=core.make_plan(member,library,case,arm,work[arm],identity)
                    row['batches'].append(dict(choice=choice,operator=op,draw_start=consumed[op]-16,
                        increments=increments,draw_end=consumed[op],spent=spent,plan=plan))
                fallback=not source and arm!='LOCAL' and len(plan['candidates'])!=1 and not (arm=='SET' and plan['query_ready'])
                if fallback:plan=core.make_plan(member,library,case,arm,work[arm],identity,force_member=True)
                certified=plan['utility_lower']>=2
                identified=not source and arm!='LOCAL' and len(plan['candidates'])==1 and certified
                transferred=not source and arm!='LOCAL' and certified and plan['mode']=='library' and (identified or arm=='SET' and plan['query_ready'])
                stop='anchor_complete' if source and arm!='LOCAL' else 'member_budget' if fallback else 'query_set' if transferred and not identified else 'identified' if identified else 'member_certified' if certified else 'budget'
                row.update(spent=spent,terminal_plan=plan,terminal_query=core.queries(plan),member=member,
                           certified=certified,identified=identified,transferred=transferred,fallback=fallback,stop=stop)
                records.append(row)
                if source:anchors[arm].append(deepcopy(member))
        save(OUTPUT/'records.json',records);save(OUTPUT/'cases.json',cases_saved)
        print(json.dumps(dict(life=life,samples=sum(w['controlled_samples'] for w in work.values()))),flush=True)
    save(OUTPUT/'run.json',dict(phases=['protocol_frozen','all_decisions_frozen'],arm_costs=work))
    results=[]
    for row in records:
        case=row['case'];_,laws,identities=task.world(row['life']);law=laws[row['index']]
        history=[score(row['initial_plan'],law,case,0)]
        history += [score(b['plan'],law,case,b['spent']) for b in row['batches']]
        if row['fallback']:history.append(score(row['terminal_plan'],law,case,row['spent']))
        transfer_correct=row['transferred'] and identities[row['index']] in row['terminal_plan']['candidates']
        correct=row['identified'] and row['terminal_plan']['candidates'][0]==identities[row['index']]
        results.append(dict(life=row['life'],index=row['index'],arm=row['arm'],spent=row['spent'],certified=row['certified'],
            identified=row['identified'],identity_correct=correct,transferred=row['transferred'],transfer_correct=transfer_correct,fallback=row['fallback'],history=history,terminal=history[-1],
            query_pre=query_score(row['initial_query'],law,case),query_post=query_score(row['terminal_query'],law,case)))
    stats=Counter();summary=summarize(results,stats)
    save(OUTPUT/'results.json',results);save(OUTPUT/'summary.json',summary)
    save(OUTPUT/'run.json',dict(phases=['protocol_frozen','all_decisions_frozen','oracle_evaluated','complete'],
        arm_costs=work,bootstrap_costs=stats,seconds=perf_counter()-begun))
    print(json.dumps(summary),flush=True)
if __name__=='__main__':run()
