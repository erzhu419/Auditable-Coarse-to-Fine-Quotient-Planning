"""Independent replay of paid prefixes and field revisions, using settled V205 math."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path
import sys
from time import perf_counter
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import analyze_conditioned_mechanisms_v205 as independent

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'reports/constrained_acquisition_v208'
ARMS = ('REVISED', 'LOCAL', 'GLOBAL')
# V206 replaces the finite observation family, not the KL endpoint algorithm.
independent.BETA = math.log(2*2016/.05)
F = Fraction

def choose(model, case, current, work):
    counts={op:current['envelopes'][op]['n'] for op in independent.OPERATORS}
    for op in independent.OPERATORS:
        if counts[op]==0:
            return dict(operator=op,pilot=True,reason='member_probe',policy=None,policy_scores=None,
                        projection_counts=counts,sensitivity_scores=None)
    values={}
    for name,vector in current['pure_vectors'].items():
        if name!='WAIT':
            values[name]=max(F(0),vector[0]+4*vector[2])*min(F(1),F(1,20)/vector[1])
    candidates=[name for name in values if values[name]>=2]
    if candidates:
        target=sorted(candidates,key=lambda name:(1+int(name=='DETOUR_RETRY'),-values[name],name))[0]
    else:
        target=sorted(values,key=lambda name:(-values[name],name))[0]
    sensitivity=None
    if target=='SHORT':operator='SHORT_PASS'
    elif target=='DETOUR_RETURN':operator='DETOUR_PASS'
    else:
        sensitivity={}
        probabilities=independent.laws(model,case,work)
        for op in ('DETOUR_PASS','RECOVERY_RETRY'):
            envelope=deepcopy(current['envelopes'])
            envelope[op]['bounds']={cat:(value,value) for cat,value in probabilities[op].items()}
            risk=independent.risk_bounds(envelope)[target];goal=independent.goal_bounds(envelope,case)[target]
            sensitivity[op]=max(F(0),goal*min(F(1),F(1,20)/risk)) if risk else max(F(0),goal)
        operator=sorted(sensitivity,key=lambda op:(-sensitivity[op],independent.OPERATORS.index(op)))[0]
    return dict(operator=operator,pilot=False,reason='constrained_target',policy=target,
                policy_scores=values,projection_counts=counts,sensitivity_scores=sensitivity)

def fitted(model, arm, work):
    mode = 'REVISED' if arm == 'REVISED' else 'FULL_CONTEXT' if arm == 'LOCAL' else 'FIXED'
    fields = {op: [] for op in independent.OPERATORS} if arm == 'GLOBAL' else None
    return independent.fit_tables(model['tables'], mode, work, fields)

def summary(results, queries, old, models, work):
    arms = {}; retention = {}; late_regret = {}
    for arm in ARMS:
        rows = [r for r in results if r['arm'] == arm]; late = [r for r in rows if r['task_index'] >= 8]
        points = [p for r in rows for p in r['history']]
        arms[arm] = dict(total_samples=sum(r['spent'] for r in rows),
            early_samples=sum(r['spent'] for r in rows if r['task_index'] < 8),
            late_samples=sum(r['spent'] for r in late), all_restored=sum(r['certified'] for r in rows),
            late_restored=sum(r['certified'] for r in late), late_utility=independent.mean(r['terminal']['actual_utility'] for r in late),
            history_violations=sum(p['violation'] for p in points), max_failure=max(p['actual'][1] for p in points),
            coverage=independent.mean(p['coverage'] for p in points), pilot_batches=sum(r['pilot_batches'] for r in rows))
        initial = independent.mean(q['regret'] for r in queries if r['arm'] == arm and r['task_index'] < 4
                                   and r['stage'] == 'POST' for q in r['queries'].values())
        final = independent.mean(q['regret'] for r in old if r['arm'] == arm for q in r['queries'].values())
        retention[arm] = dict(initial_regret=initial, final_regret=final, change=final-initial)
        late_regret[arm] = independent.mean(q['regret'] for r in queries if r['arm'] == arm and r['task_index'] >= 8
                                          and r['stage'] == 'PRE' for q in r['queries'].values())
    contrasts = {k: [] for k in ('local_minus_revised_samples','global_minus_revised_samples','revised_minus_local_late_utility')}
    for life in range(12):
        totals = {arm: sum(r['spent'] for r in results if r['life'] == life and r['arm'] == arm) for arm in ARMS}
        contrasts['local_minus_revised_samples'].append(totals['LOCAL']-totals['REVISED'])
        contrasts['global_minus_revised_samples'].append(totals['GLOBAL']-totals['REVISED'])
        utility = {arm: independent.mean(r['terminal']['actual_utility'] for r in results
                   if r['life'] == life and r['arm'] == arm and r['task_index'] >= 8) for arm in ARMS}
        contrasts['revised_minus_local_late_utility'].append(utility['REVISED']-utility['LOCAL'])
    import random
    rng = random.Random(208900); samples = {k: [] for k in contrasts}
    for _ in range(5000):
        indices = [rng.randrange(12) for _ in range(12)]
        for key in contrasts:
            samples[key].append(sum(contrasts[key][i] for i in indices)/12)
        work['bootstrap_index_draws'] += 12; work['bootstrap_mean_terms'] += 36
    intervals = {k: dict(mean=independent.mean(v), ci=[sorted(samples[k])[124],sorted(samples[k])[4874]])
                 for k,v in contrasts.items()}
    fields = {op: sum(r['models']['REVISED']['selected_fields'][op] == ['weather'] for r in models)
              for op in independent.OPERATORS[:2]}
    points = [p for r in results if r['arm'] == 'REVISED' for p in r['history']]
    conditions = dict(
        COST=intervals['local_minus_revised_samples']['mean'] >= 64 and intervals['local_minus_revised_samples']['ci'][0] > 0,
        QUALITY=arms['REVISED']['late_restored'] >= 36 and arms['REVISED']['late_restored'] >= arms['LOCAL']['late_restored']
            and arms['REVISED']['late_utility'] >= 2 and intervals['revised_minus_local_late_utility']['ci'][0] >= -.05,
        RISK_RETENTION=all(F(p['risk_upper']) <= F(1,20) and not p['violation'] for p in points) and retention['REVISED']['change'] <= .01,
        LEARNING=all(n >= 10 for n in fields.values()) and late_regret['REVISED'] <= .05)
    return dict(complete=True, arms=arms, retention=retention, late_pre_query_regret=late_regret,
        final_weather_lifecycles=fields, contrasts=contrasts, bootstrap=intervals, conditions=conditions,
        decision='CONSTRAINED_ACQUISITION_SUPPORTED' if all(conditions.values()) else 'CONSTRAINED_ACQUISITION_NOT_SUPPORTED')

def analyze():
    begun = perf_counter(); work = Counter(); checks = []
    def check(name, value):
        checks.append(dict(name=name, passed=bool(value)))
    def read(name):
        return json.loads((OUTPUT/name).read_text())
    try:
        cases, histories = read('cases.json'), read('histories.json')
        qsaved, osaved, msaved = read('queries.json'), read('old_decisions.json'), read('models.json')
        roster = independent.roster()
        sequence = ([c for c in roster if c['weather'] == 'normal']+
                    [c for c in roster if c['weather'] != 'normal' and c['operating'] == 'high']+
                    [c for c in roster if c['weather'] != 'normal' and c['operating'] == 'low'])
        check('fixed_twelve_task_sequence', cases == sequence)
        hmap = {(r['life'],r['task_index'],r['arm']):r for r in histories}
        qmap = {(r['life'],r['task_index'],r['arm'],r['stage']):r for r in qsaved}
        omap = {(r['life'],r['context_id'],r['arm']):r for r in osaved}
        mmap = {r['life']:r['models'] for r in msaved}
        check('complete_rosters', len(hmap)==len(histories)==432 and len(qmap)==len(qsaved)==864
              and len(omap)==len(osaved)==144 and len(mmap)==len(msaved)==12)
        maximum = Counter()
        for r in histories:
            counts = Counter(b['operator'] for b in r['batches'])
            for op in independent.OPERATORS:
                key=r['life'],r['task_index'],op
                maximum[key]=max(maximum[key],counts[op]*16)
        prefixes = {key:independent.generate_prefix(209000+(key[0]*12+key[1])*3+independent.OPERATORS.index(key[2]),
                    n,independent.true_laws(cases[key[1]])[key[2]],independent.SUPPORT[key[2]],work) for key,n in maximum.items()}
        results, queries, old = [], [], []; actual = Counter(); fits=Counter()
        for life in range(12):
            models={arm:fitted(dict(tables={op:[] for op in independent.OPERATORS}),arm,work) for arm in ARMS}
            for arm in ARMS: fits[arm]+=1
            decisions_ok = allocation_ok = counts_ok = plans_ok = True
            for index,case in enumerate(cases):
                laws=independent.true_laws(case)
                for arm in ARMS:
                    model=models[arm]; row=hmap[life,index,arm]
                    seeds={op:209000+(life*12+index)*3+i for i,op in enumerate(independent.OPERATORS)}
                    plans_ok &= row['context_id']==case['id'] and row['seeds']==seeds and row['initial_fields']==model['selected_fields']
                    pre=independent.decision(model,life,arm,case,work,'PRE');pre['task_index']=index
                    decisions_ok &= independent.plan_matches(qmap[life,index,arm,'PRE'],pre)
                    pre_result=independent.decision_score(pre,case,laws,work);pre_result['task_index']=index;queries.append(pre_result)
                    plan=independent.make_plan(model,case,work)
                    plans_ok &= independent.plan_matches(row['initial_plan'],plan)
                    points=[independent.score(plan,laws,case,0,work)]
                    spent=0; consumed=Counter(); pilots=0
                    for batch in row['batches']:
                        choice=choose(model,case,plan,work)
                        allocation_ok &= independent.stop_reason(plan,spent) is None
                        allocation_ok &= all(batch['choice'][k]==independent.exact_json(v) for k,v in choice.items())
                        op=choice['operator'];counts=dict.fromkeys(independent.SUPPORT[op],0)
                        for cat in prefixes[life,index,op][consumed[op]:consumed[op]+16]: counts[cat]+=1
                        counts_ok &= batch['operator']==op and batch['draw_start']==consumed[op] and batch['increments']==counts
                        consumed[op]+=16;spent+=16;actual[arm]+=16;pilots+=choice['pilot']
                        counts_ok &= batch['draw_end']==consumed[op] and batch['operator_n']==consumed[op] and batch['spent']==spent
                        independent.update(model,case,op,counts,work);model=fitted(model,arm,work);fits[arm]+=1
                        plan=independent.make_plan(model,case,work)
                        plans_ok &= batch['selected_fields']==model['selected_fields'] and independent.plan_matches(batch['plan'],plan)
                        points.append(independent.score(plan,laws,case,spent,work))
                    models[arm]=model
                    certified=plan['utility_lower']>=2
                    allocation_ok &= independent.stop_reason(plan,spent) is not None and 16<=spent<=384
                    plans_ok &= row['spent']==spent and row['certified']==certified and independent.plan_matches(row['terminal_plan'],plan)
                    results.append(dict(life=life,task_index=index,arm=arm,spent=spent,certified=certified,
                        history=points,terminal=points[-1],pilot_batches=pilots))
                    post=independent.decision(model,life,arm,case,work,'POST');post['task_index']=index
                    decisions_ok &= independent.plan_matches(qmap[life,index,arm,'POST'],post)
                    post_result=independent.decision_score(post,case,laws,work);post_result['task_index']=index;queries.append(post_result)
            for case in cases[:4]:
                for arm in ARMS:
                    row=independent.decision(models[arm],life,arm,case,work,'FINAL')
                    decisions_ok &= independent.plan_matches(omap[life,case['id'],arm],row)
                    old.append(independent.decision_score(row,case,independent.true_laws(case),work))
            for arm in ARMS:
                plans_ok &= all(mmap[life][arm][k]==independent.exact_json(models[arm][k])
                                for k in ('tables','selected_fields','scores','observations_used'))
            for name,flag in [('policies_before_after',decisions_ok),('common_choice_and_stop',allocation_ok),
                              ('actual_prefixes',counts_ok),('online_fields_and_raw_plans',plans_ok)]:
                check(f'life_{life}_{name}',flag)
        check('true_joint_results',independent.equal_numbers(read('results.json'),results))
        check('true_own_queries',independent.equal_numbers(read('query_results.json'),queries))
        check('old_policy_retention',independent.equal_numbers(read('old_results.json'),old))
        expected=summary(results,queries,old,msaved,work)
        check('paired_statistics_and_frozen_conditions',independent.equal_numbers(read('summary.json'),expected))
        run=read('run.json')
        check('all_costs_paid_and_no_pretraining',run['source_samples']==0 and sum(actual.values())<=165888
              and all(run['arm_costs'][arm]['controlled_samples']==actual[arm]
                      and run['arm_costs'][arm]['online_fit_calls']==fits[arm] for arm in ARMS))
        check('oracle_after_decisions',run['phases']==['protocol_frozen','all_decisions_frozen','oracle_evaluated','complete'])
        complete=True
    except Exception as error:
        check('reconstruction',False);checks[-1]['error']=f'{type(error).__name__}: {error}';complete=False
    output=dict(valid=complete and all(c['passed'] for c in checks),complete=complete,checks=checks,
                costs=dict(work),seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(valid=output['valid'],complete=complete,checks=len(checks))))
    return output

if __name__=='__main__':
    raise SystemExit(0 if analyze()['valid'] else 1)
