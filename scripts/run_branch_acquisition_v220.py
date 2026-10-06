"""Integrate candidate-conditioned observation branches under fixed paid sources."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import branch_acquisition_v220 as core
from acfqp.science import latent_route_task_v213 as task
from scripts import run_conditioned_mechanisms_v205 as saved

OUTPUT = ROOT/'reports/branch_acquisition_v220'
SOURCE_EVIDENCE = ROOT/'reports/fixed_source_acquisition_v219/source_evidence.json'
ARMS = ('BRANCH', 'MEAN', 'SET', 'LOCAL', 'ORACLE')
SOURCE_FILES = ('src/acfqp/science/structured_route_task_v201.py', 'src/acfqp/science/continual_route_kernels_v202.py', 'src/acfqp/science/robust_route_planning_v203.py', 'src/acfqp/science/target_risk_acquisition_v204.py', 'src/acfqp/science/conditioned_mechanisms_v205.py', 'src/acfqp/science/mechanism_switch_task_v205.py', 'src/acfqp/science/online_lifecycle_v206.py', 'src/acfqp/science/constrained_acquisition_v208.py', 'src/acfqp/science/contracted_risk_reuse_v209.py', 'src/acfqp/science/strategic_maintenance_v210.py', 'src/acfqp/science/latent_mechanisms_v213.py', 'src/acfqp/science/query_sufficient_v214.py', 'src/acfqp/science/query_calibration_v215.py', 'src/acfqp/science/source_stopping_v216.py', 'src/acfqp/science/joint_acquisition_v218.py', 'src/acfqp/science/fixed_source_acquisition_v219.py', 'src/acfqp/science/latent_route_task_v213.py', 'scripts/run_conditioned_mechanisms_v205.py', 'scripts/analyze_conditioned_mechanisms_v205.py', 'scripts/analyze_latent_mechanisms_v213.py', 'scripts/analyze_joint_acquisition_v218.py', 'scripts/analyze_fixed_source_acquisition_v219.py', 'src/acfqp/science/branch_acquisition_v220.py', 'scripts/run_branch_acquisition_v220.py', 'scripts/analyze_branch_acquisition_v220.py', 'tests/test_branch_acquisition_v220.py', 'specs/BRANCH_ACQUISITION_V220.md', 'reports/v220_runtime_tmp/run_stage.py')
save, mean = saved.save, saved.mean


def score(plan, law, case, spent):
    pure = core.vectors(case, law)
    actual = [sum(weight*pure[name][i] for name,weight in plan['mix']) for i in range(3)]
    coverage = all(lo <= law[op][cat] <= hi for op,env in plan['envelopes'].items()
                   for cat,(lo,hi) in env['bounds'].items())
    return dict(spent=spent, actual=actual, actual_utility=actual[0]+4*actual[2],
                risk_upper=plan['risk_upper'], utility_lower=plan['utility_lower'],
                violation=actual[1] > F(1,20), coverage=coverage)


def query_score(decision, law, case):
    pure = core.vectors(case, law); result = {}
    for query,w in {'reward':(1,0,0), 'goal':(1,0,4), 'risk':(1,4,4)}.items():
        utility = lambda v: v[0]*w[0]-v[1]*w[1]+v[2]*w[2]
        actual = pure[decision[query]['policy']]
        result[query] = dict(policy=decision[query]['policy'], actual=actual,
            utility=utility(actual), regret=max(utility(v) for v in pure.values())-utility(actual))
    return result


def summarize(results, historical, work):
    arms = {}
    for arm in ARMS:
        rows = [r for r in results if r['arm'] == arm]; late = [r for r in rows if r['index'] >= 15]
        points = [p for r in rows for p in r['history']]
        source_cost = sum(historical[arm]); target_cost = sum(r['spent'] for r in rows)
        arms[arm] = dict(total_samples=source_cost+target_cost, source_samples=source_cost,
            target_samples=target_cost, source_revisit_samples=0, late_samples=sum(r['spent'] for r in late),
            late_certified=sum(r['certified'] for r in late),
            late_transferred=sum(r['transferred'] and r['transfer_correct'] for r in late),
            late_identified=sum(r['identified'] and r['identity_correct'] for r in late),
            wrong_transfers=sum(r['transferred'] and not r['transfer_correct'] for r in rows),
            late_utility=mean(float(r['terminal']['actual_utility']) for r in late),
            late_post_regret=mean(float(v['regret']) for r in late for v in r['query_post'].values()),
            history_violations=sum(p['violation'] for p in points), max_failure=max(float(p['actual'][1]) for p in points),
            coverage=mean(p['coverage'] for p in points), member_fallbacks=sum(r['fallback'] for r in rows))
    contrasts = {key: [] for key in ('local_minus_branch_samples', 'set_minus_branch_samples',
        'branch_minus_local_late_utility', 'branch_minus_set_post_regret', 'branch_minus_oracle_samples',
        'branch_minus_set_late_utility', 'branch_minus_set_late_certified',
        'mean_minus_branch_samples', 'branch_minus_mean_post_regret',
        'branch_minus_mean_late_utility', 'branch_minus_mean_late_certified')}
    for life in range(12):
        rows = [r for r in results if r['life'] == life]
        totals = {arm: historical[arm][life]+sum(r['spent'] for r in rows if r['arm'] == arm) for arm in ARMS}
        utility = {arm: mean(float(r['terminal']['actual_utility']) for r in rows if r['arm'] == arm and r['index'] >= 15) for arm in ARMS}
        regret = {arm: mean(float(v['regret']) for r in rows if r['arm'] == arm and r['index'] >= 15 for v in r['query_post'].values()) for arm in ARMS}
        contrasts['local_minus_branch_samples'].append(totals['LOCAL']-totals['BRANCH'])
        contrasts['set_minus_branch_samples'].append(totals['SET']-totals['BRANCH'])
        contrasts['branch_minus_oracle_samples'].append(totals['BRANCH']-totals['ORACLE'])
        contrasts['branch_minus_local_late_utility'].append(utility['BRANCH']-utility['LOCAL'])
        contrasts['branch_minus_set_late_utility'].append(utility['BRANCH']-utility['SET'])
        contrasts['branch_minus_set_post_regret'].append(regret['BRANCH']-regret['SET'])
        contrasts['branch_minus_set_late_certified'].append(sum(r['certified'] for r in rows if r['arm']=='BRANCH' and r['index']>=15)
            -sum(r['certified'] for r in rows if r['arm']=='SET' and r['index']>=15))
        contrasts['mean_minus_branch_samples'].append(totals['MEAN']-totals['BRANCH'])
        contrasts['branch_minus_mean_post_regret'].append(regret['BRANCH']-regret['MEAN'])
        contrasts['branch_minus_mean_late_utility'].append(utility['BRANCH']-utility['MEAN'])
        contrasts['branch_minus_mean_late_certified'].append(sum(r['certified'] for r in rows if r['arm']=='BRANCH' and r['index']>=15)
            -sum(r['certified'] for r in rows if r['arm']=='MEAN' and r['index']>=15))
    rng = random.Random(224900); samples = {key: [] for key in contrasts}
    for _ in range(5000):
        indices = [rng.randrange(12) for _ in range(12)]; work['bootstrap_index_draws'] += 12
        for key,rows in contrasts.items():
            samples[key].append(mean(rows[i] for i in indices)); work['bootstrap_mean_terms'] += 12
    intervals = {key: dict(mean=mean(rows), ci=[sorted(samples[key])[124],sorted(samples[key])[4874]]) for key,rows in contrasts.items()}
    a = arms['BRANCH']; points = [p for r in results if r['arm']=='BRANCH' for p in r['history']]
    conditions = dict(COST=intervals['local_minus_branch_samples']['mean'] >= 64 and intervals['local_minus_branch_samples']['ci'][0] > 0,
        QUALITY=a['late_certified'] >= 108 and a['late_certified'] >= arms['LOCAL']['late_certified'] and a['late_utility'] >= 2
            and intervals['branch_minus_local_late_utility']['ci'][0] >= -.05,
        RISK=all(p['actual'][1] <= F(1,20) and p['risk_upper'] <= F(1,20) for p in points),
        APPLICABILITY=a['late_transferred'] >= 108 and a['late_post_regret'] <= .05,
        TARGET_EFFECT=intervals['set_minus_branch_samples']['ci'][0] > 0 and intervals['branch_minus_set_post_regret']['ci'][1] <= .01,
        REFERENCE_QUALITY=a['late_certified'] >= arms['SET']['late_certified'] and intervals['branch_minus_set_late_utility']['ci'][0] >= -.05,
        MEAN_EFFECT=intervals['mean_minus_branch_samples']['ci'][0] > 0
            and intervals['branch_minus_mean_post_regret']['ci'][1] <= .01
            and a['late_certified'] >= arms['MEAN']['late_certified']
            and intervals['branch_minus_mean_late_utility']['ci'][0] >= -.05)
    return dict(complete=True, arms=arms, contrasts=contrasts, bootstrap=intervals, conditions=conditions,
        decision='BRANCH_ACQUISITION_SUPPORTED' if all(conditions.values()) else 'BRANCH_ACQUISITION_NOT_SUPPORTED')


def run():
    begun = perf_counter(); OUTPUT.mkdir(parents=True, exist_ok=False)
    for name in SOURCE_FILES:
        path = OUTPUT/'source_code'/name; path.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT/name, path)
    save(OUTPUT/'source_manifest.json', [dict(path=name) for name in SOURCE_FILES])
    shutil.copyfile(SOURCE_EVIDENCE, OUTPUT/'source_evidence.json')
    source_rows = json.loads((OUTPUT/'source_evidence.json').read_text())
    lookup = {(r['life'],r['index'],r['arm']): r for r in source_rows}
    historical = {arm: [sum(lookup[life,i,'LOCAL' if arm=='LOCAL' else 'FULL']['spent'] for i in range(3))
                        for life in range(12)] for arm in ARMS}
    libraries = [dict(life=life, anchors=[deepcopy(lookup[life,i,'FULL']['member']) for i in range(3)]) for life in range(12)]
    save(OUTPUT/'libraries.json', libraries)
    work = {arm: Counter() for arm in ARMS}; records = []; cases_saved = []
    arm_seconds = dict.fromkeys(ARMS,0.0)
    for life in range(12):
        cases,laws,identities = task.world(life); cases_saved.append(dict(life=life,cases=cases))
        cache = core.prepare(libraries[life]['anchors'],work['BRANCH'])
        for index,case in enumerate(cases[3:], start=3):
            seeds = {op: 225000+(life*27+index)*3+i for i,op in enumerate(core.OPERATORS)}
            for arm in ARMS:
                arm_begun = perf_counter()
                member = core.empty(); rng = {op: random.Random(seed) for op,seed in seeds.items()}
                library = libraries[life]['anchors'] if arm!='LOCAL' else []
                identity = identities[index] if arm=='ORACLE' else None
                plan = core.make_plan(member,library,case,arm,work[arm],identity)
                row = dict(life=life,index=index,case=case,arm=arm,seeds=seeds,
                           initial_plan=plan,initial_query=core.queries(plan),batches=[])
                spent = 0
                while True:
                    choice = core.choose(member,library,case,arm,plan,spent,work[arm],cache)
                    if choice is None: break
                    op = choice['operator']; start = sum(member[op].values())
                    increments = dict.fromkeys(core.ALPHABETS[op],0); progress = dict(draw_end=start,n=start)
                    saved.draw(rng[op],laws[index],op,increments,16,work[arm],progress)
                    for cat,k in increments.items(): member[op][cat] += k
                    spent += 16; plan = core.make_plan(member,library,case,arm,work[arm],identity)
                    row['batches'].append(dict(choice=choice,scope='TARGET',source_index=None,
                        operator=op,draw_start=start,increments=increments,draw_end=progress['draw_end'],
                        spent=spent,member_spent=spent,source_spent=0,plan=plan))
                fallback = arm!='LOCAL' and len(plan['candidates'])!=1 and not (arm in ('BRANCH','MEAN','SET') and plan['query_ready'])
                if fallback: plan = core.make_plan(member,library,case,arm,work[arm],identity,force_member=True)
                certified = plan['utility_lower'] >= 2
                identified = arm!='LOCAL' and len(plan['candidates'])==1 and certified
                transferred = arm!='LOCAL' and certified and plan['mode']=='library' and (identified or arm in ('BRANCH','MEAN','SET') and plan['query_ready'])
                stop = 'member_budget' if fallback else 'query_set' if transferred and not identified else 'identified' if identified else 'member_certified' if certified else 'budget'
                row.update(spent=spent,member_spent=spent,source_spent=0,terminal_plan=plan,
                    terminal_query=core.queries(plan),member=deepcopy(member),certified=certified,
                    identified=identified,transferred=transferred,fallback=fallback,stop=stop)
                records.append(row)
                arm_seconds[arm] += perf_counter()-arm_begun
        save(OUTPUT/'records.json',records); save(OUTPUT/'cases.json',cases_saved)
        print(json.dumps(dict(life=life,seconds=perf_counter()-begun,fresh_target_samples={arm:w['controlled_samples'] for arm,w in work.items()})),flush=True)
    save(OUTPUT/'run.json',dict(phases=['protocol_frozen','all_decisions_frozen'],arm_costs=work,arm_seconds=arm_seconds,historical_source_costs=historical))
    results = []
    for row in records:
        case = row['case']; _,laws,identities = task.world(row['life']); law = laws[row['index']]
        points = [score(row['initial_plan'],law,case,0)] + [score(b['plan'],law,case,b['spent']) for b in row['batches']]
        if row['fallback']: points.append(score(row['terminal_plan'],law,case,row['spent']))
        results.append(dict(life=row['life'],index=row['index'],arm=row['arm'],spent=row['spent'],source_spent=0,member_spent=row['spent'],
            certified=row['certified'],identified=row['identified'],identity_correct=row['identified'] and row['terminal_plan']['candidates'][0]==identities[row['index']],
            transferred=row['transferred'],transfer_correct=row['transferred'] and identities[row['index']] in row['terminal_plan']['candidates'],
            fallback=row['fallback'],history=points,terminal=points[-1],
            query_pre=query_score(row['initial_query'],law,case),query_post=query_score(row['terminal_query'],law,case)))
    stats = Counter(); summary = summarize(results,historical,stats)
    save(OUTPUT/'results.json',results); save(OUTPUT/'summary.json',summary)
    save(OUTPUT/'run.json',dict(phases=['protocol_frozen','all_decisions_frozen','oracle_evaluated','complete'],
        arm_costs=work,arm_seconds=arm_seconds,historical_source_costs=historical,bootstrap_costs=stats,seconds=perf_counter()-begun))
    print(json.dumps(summary),flush=True)


if __name__ == '__main__':
    run()
