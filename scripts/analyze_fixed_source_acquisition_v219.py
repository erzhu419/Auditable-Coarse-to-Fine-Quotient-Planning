"""Independent fixed-source target replay, including actual historical source costs."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import analyze_joint_acquisition_v218 as prior

OUTPUT = ROOT/'reports/fixed_source_acquisition_v219'
ARMS = ('MEAN','SET','LOCAL','ORACLE')
OPERATORS, SUPPORT = prior.OPERATORS, prior.SUPPORT
F = Fraction
empty, world, queries = prior.empty, prior.world, prior.queries
score, query_score, same = prior.score, prior.query_score, prior.same
settled = prior.settled


def base_arm(arm):
    return {'MEAN':'MEMBER','SET':'FULL'}.get(arm,arm)


def make_plan(member, anchors, case, arm, work, identity=None, force_member=False):
    return prior.make_plan(member,anchors,case,base_arm(arm),work,identity,force_member)


def choose(member, anchors, case, arm, plan, spent, work):
    return prior.choose(member,anchors,case,base_arm(arm),plan,spent,work)


def summary(results, work, historical):
    arms = {}
    for arm in ARMS:
        rows = [r for r in results if r['arm'] == arm]
        late = [r for r in rows if r['index'] >= 15]
        points = [p for r in rows for p in r['history']]
        arms[arm] = dict(total_samples=sum(historical[arm])+sum(r['spent'] for r in rows),
            source_samples=sum(historical[arm]),
            target_samples=sum(r['member_spent'] for r in rows),
            source_revisit_samples=0,
            late_samples=sum(r['spent'] for r in late),
            late_certified=sum(r['certified'] for r in late),
            late_transferred=sum(r['transferred'] and r['transfer_correct'] for r in late),
            late_identified=sum(r['identified'] and r['identity_correct'] for r in late),
            wrong_transfers=sum(r['transferred'] and not r['transfer_correct'] for r in rows),
            late_utility=settled.mean(float(r['terminal']['actual_utility']) for r in late),
            late_post_regret=settled.mean(float(v['regret']) for r in late for v in r['query_post'].values()),
            history_violations=sum(p['violation'] for p in points),
            max_failure=max(float(p['actual'][1]) for p in points),
            coverage=settled.mean(p['coverage'] for p in points),
            member_fallbacks=sum(r['fallback'] for r in rows))
    contrasts = {key: [] for key in ('local_minus_mean_samples','set_minus_mean_samples',
        'mean_minus_local_late_utility','mean_minus_set_post_regret','mean_minus_oracle_samples',
        'mean_minus_set_late_utility','mean_minus_set_late_certified')}
    for life in range(12):
        rows = [r for r in results if r['life'] == life]
        costs = {arm: historical[arm][life]+sum(r['spent'] for r in rows if r['arm'] == arm) for arm in ARMS}
        utility = {arm: settled.mean(float(r['terminal']['actual_utility']) for r in rows
                        if r['arm'] == arm and r['index'] >= 15) for arm in ARMS}
        regret = {arm: settled.mean(float(v['regret']) for r in rows if r['arm'] == arm
                        and r['index'] >= 15 for v in r['query_post'].values()) for arm in ARMS}
        contrasts['local_minus_mean_samples'].append(costs['LOCAL']-costs['MEAN'])
        contrasts['set_minus_mean_samples'].append(costs['SET']-costs['MEAN'])
        contrasts['mean_minus_oracle_samples'].append(costs['MEAN']-costs['ORACLE'])
        contrasts['mean_minus_local_late_utility'].append(utility['MEAN']-utility['LOCAL'])
        contrasts['mean_minus_set_late_utility'].append(utility['MEAN']-utility['SET'])
        contrasts['mean_minus_set_late_certified'].append(
            sum(r['certified'] for r in rows if r['arm'] == 'MEAN' and r['index'] >= 15)
            -sum(r['certified'] for r in rows if r['arm'] == 'SET' and r['index'] >= 15))
        contrasts['mean_minus_set_post_regret'].append(regret['MEAN']-regret['SET'])
    rng = random.Random(223900)
    samples = {key: [] for key in contrasts}
    for _ in range(5000):
        indices = [rng.randrange(12) for _ in range(12)]
        for key,rows in contrasts.items():
            samples[key].append(settled.mean(rows[i] for i in indices))
        work['bootstrap_index_draws'] += 12
        work['bootstrap_mean_terms'] += 84
    intervals = {key: dict(mean=settled.mean(rows),
        ci=[sorted(samples[key])[124],sorted(samples[key])[4874]]) for key,rows in contrasts.items()}
    target = arms['MEAN']
    points = [p for r in results if r['arm'] == 'MEAN' for p in r['history']]
    conditions = dict(
        COST=intervals['local_minus_mean_samples']['mean'] >= 64
             and intervals['local_minus_mean_samples']['ci'][0] > 0,
        QUALITY=target['late_certified'] >= 108
                and target['late_certified'] >= arms['LOCAL']['late_certified']
                and target['late_utility'] >= 2
                and intervals['mean_minus_local_late_utility']['ci'][0] >= -.05,
        RISK=all(p['actual'][1] <= F(1,20) and p['risk_upper'] <= F(1,20) for p in points),
        APPLICABILITY=target['late_transferred'] >= 108 and target['late_post_regret'] <= .05,
        TARGET_EFFECT=intervals['set_minus_mean_samples']['ci'][0] > 0
                    and intervals['mean_minus_set_post_regret']['ci'][1] <= .01,
        REFERENCE_QUALITY=target['late_certified'] >= arms['SET']['late_certified']
                    and intervals['mean_minus_set_late_utility']['ci'][0] >= -.05)
    return dict(complete=True,arms=arms,contrasts=contrasts,bootstrap=intervals,conditions=conditions,
        decision='FIXED_SOURCE_ACQUISITION_SUPPORTED' if all(conditions.values()) else 'FIXED_SOURCE_ACQUISITION_NOT_SUPPORTED')


def reconstruct_source(row, case, prefixes, work):
    life,index,arm = row['life'],row['index'],row['arm']
    member = empty()
    plan = prior.make_plan(member,[],case,arm,work)
    flags = dict(plans=same(row['initial_plan'],plan) and same(row['case'],case),
        counts=True,choices=True,queries=same(row['initial_query'],queries(plan)))
    seeds = {op: 223000+(life*27+index)*3+i for i,op in enumerate(OPERATORS)}
    flags['plans'] &= row['seeds'] == seeds
    spent,consumed = 0,Counter()
    for batch in row['batches']:
        choice = prior.choose(member,[],case,arm,plan,spent,work,True,index)
        flags['choices'] &= choice is not None and same(batch['choice'],choice)
        op = choice['operator']
        increments = dict.fromkeys(SUPPORT[op],0)
        for cat in prefixes[life,index,op][consumed[op]:consumed[op]+16]:
            increments[cat] += 1
        flags['counts'] &= batch['operator'] == op and batch['scope'] == 'SOURCE'
        flags['counts'] &= batch['source_index'] == index and batch['draw_start'] == consumed[op]
        flags['counts'] &= batch['increments'] == increments and sum(increments.values()) == 16
        for cat,k in increments.items(): member[op][cat] += k
        consumed[op] += 16; spent += 16
        flags['counts'] &= batch['draw_end'] == consumed[op] and batch['spent'] == spent
        flags['counts'] &= batch['source_spent'] == spent and batch['member_spent'] == 0
        plan = prior.make_plan(member,[],case,arm,work)
        flags['plans'] &= same(batch['plan'],plan)
    flags['choices'] &= prior.choose(member,[],case,arm,plan,spent,work,True,index) is None
    flags['choices'] &= 0 <= spent <= 1152
    certified = plan['utility_lower'] >= 2
    stop = 'anchor_complete' if arm == 'FULL' else 'member_certified' if certified else 'budget'
    flags['choices'] &= row['stop'] == stop and row['fallback'] is False
    flags['plans'] &= row['spent'] == spent and row['source_spent'] == spent and row['member_spent'] == 0
    flags['plans'] &= row['certified'] == certified and row['identified'] is False and row['transferred'] is False
    flags['plans'] &= same(row['member'],member) and same(row['terminal_plan'],plan)
    flags['queries'] &= same(row['terminal_query'],queries(plan))
    return member,spent,flags


def analyze():
    begun = perf_counter()
    work,actual,planning = Counter(),Counter(),Counter()
    checks = []
    def check(name, value): checks.append(dict(name=name,passed=bool(value)))
    def read(name): return json.loads((OUTPUT/name).read_text())
    try:
        worlds = [world(life) for life in range(12)]
        check('fixed_opaque_private_worlds',same(read('cases.json'),
              [dict(life=life,cases=worlds[life][0]) for life in range(12)]))
        source_rows = read('source_evidence.json')
        sources = {(r['life'],r['index'],r['arm']): r for r in source_rows}
        check('only_complete_actual_initial_full_and_local_sources',
            len(source_rows) == len(sources) == 72 and all(
                (life,index,arm) in sources for life in range(12)
                for index in range(3) for arm in ('FULL','LOCAL')))
        maximum = Counter()
        for row in source_rows:
            for op in OPERATORS:
                n = 16*sum(b['operator'] == op for b in row['batches'])
                key = row['life'],row['index'],op
                maximum[key] = max(maximum[key],n)
        source_prefixes = {key: settled.generate_prefix(
            223000+(key[0]*27+key[1])*3+OPERATORS.index(key[2]),n,
            worlds[key[0]][1][key[1]][key[2]],SUPPORT[key[2]],work)
            for key,n in maximum.items()}
        libraries = []
        source_costs = {arm: [0]*12 for arm in ('FULL','LOCAL')}
        for life in range(12):
            anchors = []
            flags = dict(plans=True,counts=True,choices=True,queries=True)
            for index in range(3):
                for arm in ('FULL','LOCAL'):
                    row = sources[life,index,arm]
                    member,spent,verified = reconstruct_source(
                        row,worlds[life][0][index],source_prefixes,work)
                    for key,value in verified.items(): flags[key] &= value
                    source_costs[arm][life] += spent
                    if arm == 'FULL': anchors.append(deepcopy(member))
            libraries.append(dict(life=life,anchors=anchors))
            for key,value in flags.items(): check(f'life_{life}_historical_source_{key}',value)
        historical = {arm: list(source_costs['LOCAL' if arm == 'LOCAL' else 'FULL']) for arm in ARMS}
        check('actual_historical_source_costs',source_costs['FULL'] == [3456]*12
              and sum(source_costs['LOCAL']) == 12640)
        check('frozen_library_from_actual_full_source_prefixes',same(read('libraries.json'),libraries))
        rows = read('records.json')
        lookup = {(r['life'],r['index'],r['arm']): r for r in rows}
        check('complete_unique_fresh_targets',len(rows) == len(lookup) == 1152
              and all((life,index,arm) in lookup for life in range(12)
                      for index in range(3,27) for arm in ARMS))
        paired = True
        for life in range(12):
            for index in range(3,27):
                seeds = {op: 224000+(life*27+index)*3+i for i,op in enumerate(OPERATORS)}
                paired &= all(lookup[life,index,arm]['seeds'] == seeds for arm in ARMS)
        check('four_arm_shared_fresh_target_prefix_seeds',paired)
        maximum = Counter()
        for row in rows:
            for op in OPERATORS:
                n = 16*sum(b['operator'] == op for b in row['batches'])
                key = row['life'],row['index'],op
                maximum[key] = max(maximum[key],n)
        prefixes = {key: settled.generate_prefix(
            224000+(key[0]*27+key[1])*3+OPERATORS.index(key[2]),n,
            worlds[key[0]][1][key[1]][key[2]],SUPPORT[key[2]],work)
            for key,n in maximum.items()}
        results = []
        for life in range(12):
            cases,laws,identities = worlds[life]
            anchors = libraries[life]['anchors']
            decisions_ok = allocation_ok = counts_ok = plans_ok = True
            for index in range(3,27):
                case = cases[index]
                seeds = {op: 224000+(life*27+index)*3+i for i,op in enumerate(OPERATORS)}
                for arm in ARMS:
                    row = lookup[life,index,arm]
                    member = empty()
                    library = [] if arm == 'LOCAL' else anchors
                    identity = identities[index] if arm == 'ORACLE' else None
                    plan = make_plan(member,library,case,arm,work,identity)
                    planning[arm] += 1
                    plans_ok &= same(row['case'],case) and row['seeds'] == seeds
                    plans_ok &= same(row['initial_plan'],plan)
                    pre = queries(plan)
                    decisions_ok &= same(row['initial_query'],pre)
                    points = [score(plan,laws[index],case,0,work)]
                    spent,consumed = 0,Counter()
                    for batch in row['batches']:
                        choice = choose(member,library,case,arm,plan,spent,work)
                        allocation_ok &= choice is not None and same(batch['choice'],choice)
                        op = choice['operator']
                        allocation_ok &= choice['scope'] == 'TARGET' and choice['source_index'] is None
                        increments = dict.fromkeys(SUPPORT[op],0)
                        for cat in prefixes[life,index,op][consumed[op]:consumed[op]+16]:
                            increments[cat] += 1
                        counts_ok &= batch['operator'] == op and batch['scope'] == 'TARGET'
                        counts_ok &= batch['source_index'] is None and batch['draw_start'] == consumed[op]
                        counts_ok &= batch['increments'] == increments and sum(increments.values()) == 16
                        for cat,k in increments.items(): member[op][cat] += k
                        consumed[op] += 16; spent += 16; actual[arm] += 16
                        counts_ok &= batch['draw_end'] == consumed[op] and batch['spent'] == spent
                        counts_ok &= batch['member_spent'] == spent and batch['source_spent'] == 0
                        plan = make_plan(member,library,case,arm,work,identity)
                        planning[arm] += 1
                        plans_ok &= same(batch['plan'],plan)
                        points.append(score(plan,laws[index],case,spent,work))
                    allocation_ok &= choose(member,library,case,arm,plan,spent,work) is None
                    allocation_ok &= 0 <= spent <= 384
                    fallback = arm != 'LOCAL' and len(plan['candidates']) != 1 and not (arm in ('MEAN','SET') and plan['query_ready'])
                    if fallback:
                        plan = make_plan(member,library,case,arm,work,identity,force_member=True)
                        planning[arm] += 1
                        points.append(score(plan,laws[index],case,spent,work))
                    certified = plan['utility_lower'] >= 2
                    identified = arm != 'LOCAL' and len(plan['candidates']) == 1 and certified
                    transferred = arm != 'LOCAL' and certified and plan['mode'] == 'library' and (identified or arm in ('MEAN','SET') and plan['query_ready'])
                    stop = ('member_budget' if fallback else 'query_set' if transferred and not identified else
                            'identified' if identified else 'member_certified' if certified else 'budget')
                    allocation_ok &= row['stop'] == stop and row['fallback'] == fallback
                    plans_ok &= row['spent'] == spent and row['member_spent'] == spent and row['source_spent'] == 0
                    plans_ok &= row['certified'] == certified and row['identified'] == identified
                    plans_ok &= row['transferred'] == transferred and same(row['member'],member)
                    plans_ok &= same(row['terminal_plan'],plan)
                    post = queries(plan)
                    decisions_ok &= same(row['terminal_query'],post)
                    correct = identified and plan['candidates'][0] == identities[index]
                    transfer_correct = transferred and identities[index] in plan['candidates']
                    results.append(dict(life=life,index=index,arm=arm,spent=spent,
                        source_spent=0,member_spent=spent,certified=certified,identified=identified,
                        identity_correct=correct,transferred=transferred,transfer_correct=transfer_correct,
                        fallback=fallback,history=points,terminal=points[-1],
                        query_pre=query_score(pre,laws[index],case),query_post=query_score(post,laws[index],case)))
            for name,flag in [('full_policy_queries',decisions_ok),('finite_choices_stops_and_target_only_budget',allocation_ok),
                              ('actual_paired_fresh_target_prefixes',counts_ok),('fixed_library_and_member_plans',plans_ok)]:
                check(f'life_{life}_{name}',flag)
        check('frozen_history_true_joint_and_own_query_results',same(read('results.json'),results))
        stats = Counter()
        expected = summary(results,stats,historical)
        check('total_lifecycle_statistics_and_frozen_gates',same(read('summary.json'),expected))
        run = read('run.json')
        check('historical_source_fee_is_separate_from_fresh_sampling',same(run['historical_source_costs'],historical))
        check('actual_fresh_target_and_planning_costs',sum(actual.values()) <= 442368 and all(
            run['arm_costs'][arm].get(key,0) == actual[arm]
            for arm in ARMS for key in ('controlled_samples','controlled_resets','environment_random_draws'))
            and all(run['arm_costs'][arm]['planning_calls'] == planning[arm] for arm in ARMS)
            and all(expected['arms'][arm]['source_samples'] == sum(historical[arm])
                    and expected['arms'][arm]['target_samples'] == actual[arm]
                    and expected['arms'][arm]['total_samples'] == sum(historical[arm])+actual[arm]
                    and expected['arms'][arm]['source_revisit_samples'] == 0 for arm in ARMS))
        check('frozen_bootstrap_costs',run['bootstrap_costs'] == dict(stats))
        check('oracle_scoring_after_all_decisions',run['phases'] == [
            'protocol_frozen','all_decisions_frozen','oracle_evaluated','complete'])
        complete = True
    except Exception as error:
        check('reconstruction',False)
        checks[-1]['error'] = f'{type(error).__name__}: {error}'
        complete = False
    output = dict(valid=complete and all(c['passed'] for c in checks),complete=complete,
                  checks=checks,costs=dict(work),seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(valid=output['valid'],complete=complete,checks=len(checks))))
    return output


if __name__ == '__main__':
    raise SystemExit(0 if analyze()['valid'] else 1)
