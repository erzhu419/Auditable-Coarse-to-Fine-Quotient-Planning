"""Independent complete observation-branch integration under retained actual sources."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from itertools import product
from math import fsum
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import analyze_fixed_source_acquisition_v219 as prior

OUTPUT = ROOT/'reports/branch_acquisition_v220'
ARMS = ('BRANCH','MEAN','SET','LOCAL','ORACLE')
OPERATORS, SUPPORT = prior.OPERATORS, prior.SUPPORT
F = Fraction
empty, world, queries = prior.empty, prior.world, prior.queries
score, query_score, same = prior.score, prior.query_score, prior.same
settled = prior.settled
independent = prior.prior.independent
reconstruct_source = prior.reconstruct_source


def make_plan(member, anchors, case, arm, work, identity=None, force_member=False):
    return prior.make_plan(member,anchors,case,'MEAN' if arm == 'BRANCH' else arm,
                           work,identity,force_member)


def record_forecast(work, counted):
    if work is not None: work.update({'forecast_'+key: value for key,value in counted.items()})


def cached_boxes(counts, cache, counted):
    boxes = {}
    for op in OPERATORS:
        row = counts[op]
        n = sum(row.values())
        bounds = {}
        for cat in SUPPORT[op]:
            key = row[cat],n
            if key in cache['intervals']:
                counted['interval_cache_hits'] += 1
            else:
                cache['intervals'][key] = settled.interval(row[cat],n,counted)
            bounds[cat] = cache['intervals'][key]
        boxes[op] = dict(n=n,counts=dict(row),bounds=bounds)
    return boxes


def prepare(anchors, work):
    cache = dict(source_boxes=[],intervals={})
    counted = Counter()
    cache['source_boxes'] = [cached_boxes(anchor,cache,counted) for anchor in anchors]
    counted['source_box_records'] += len(anchors)
    record_forecast(work,counted)
    return cache


def forecast_plan(member, anchors, case, work, cache):
    counted = Counter()
    raw = cached_boxes(member,cache,counted)
    candidates,blocks = [],{}
    for index,source in enumerate(cache['source_boxes']):
        bounds = {op: {cat: (
            max(raw[op]['bounds'][cat][0],source[op]['bounds'][cat][0]),
            min(raw[op]['bounds'][cat][1],source[op]['bounds'][cat][1]))
            for cat in SUPPORT[op]} for op in OPERATORS}
        if all(lo <= hi for row in bounds.values() for lo,hi in row.values()):
            candidates.append(index)
            blocks[index] = {op: dict(n=raw[op]['n'],counts=dict(member[op]),bounds=bounds[op])
                             for op in OPERATORS}
    if candidates:
        risks = [settled.risk_bounds(block) for block in blocks.values()]
        goals = [settled.goal_bounds(block,case) for block in blocks.values()]
        upper = {policy: max(F(0),*(row[policy] for row in risks)) for policy in risks[0]}
        lower = {policy: min(row[policy] for row in goals) for policy in goals[0]}
        means = [independent.posterior({op: {cat: member[op][cat]+anchors[index][op][cat]
                  for cat in SUPPORT[op]} for op in OPERATORS}) for index in candidates]
        probabilities = {op: {cat: sum(p[op][cat] for p in means)/len(means)
                         for cat in SUPPORT[op]} for op in OPERATORS}
        envelope = deepcopy(raw)
        for op in OPERATORS:
            envelope[op]['bounds'] = {cat: (
                min(block[op]['bounds'][cat][0] for block in blocks.values()),
                max(block[op]['bounds'][cat][1] for block in blocks.values())) for cat in SUPPORT[op]}
        mode = 'library'
    else:
        envelope,mode = raw,'member'
        upper,lower = settled.risk_bounds(raw),settled.goal_bounds(raw,case)
        probabilities = independent.posterior(member)
    pure = settled.vectors(case,probabilities)
    plan = dict(settled.optimize(pure,upper,lower,counted),envelopes=envelope,
        risks=upper,goals_lower=lower,pure_vectors=pure,candidates=candidates,
        candidate_envelopes=blocks,mode=mode)
    plan['query_proxy'] = prior.prior.proxy(member,anchors,case,plan)
    plan['query_ready'] = mode == 'library' and plan['utility_lower'] >= 2 and plan['query_proxy'] is not None and plan['query_proxy'] <= F(1,20)
    counted['planning_calls'] += 1
    record_forecast(work,counted)
    return plan


def beta_batch(first, remaining, size):
    """Beta-binomial recurrence with both alpha parameters expressed in halves."""
    mass = F(1)
    for index in range(size): mass *= F(remaining+2*index,first+remaining+2*index)
    probabilities = [mass]
    for successes in range(size):
        mass *= F(size-successes,successes+1)*F(first+2*successes,remaining+2*(size-successes-1))
        probabilities.append(mass)
    return probabilities


def dm_distribution(row, op, work=None):
    """Factor the multinomial law into exact conditional beta-binomial laws."""
    alpha = [2*row[cat]+1 for cat in SUPPORT[op]]
    first = beta_batch(alpha[0],sum(alpha[1:]),16)
    if len(alpha) == 2:
        result = [((a,16-a),mass) for a,mass in enumerate(first)]
    else:
        result = []
        for a,first_mass in enumerate(first):
            conditional = beta_batch(alpha[1],alpha[2],16-a)
            result += [((a,b,16-a-b),first_mass*mass) for b,mass in enumerate(conditional)]
    record_forecast(work,dict(dm_components=1,dm_probability_constructions=len(result)))
    return result


def predictive_distribution(member, anchors, plan, op, work=None):
    rows = [{cat: member[op][cat]+anchors[index][op][cat] for cat in SUPPORT[op]}
            for index in plan['candidates']] if plan['candidates'] else [member[op]]
    laws = [dm_distribution(row,op,work) for row in rows]
    return [(dict(zip(SUPPORT[op],counts)),sum(law[index][1] for law in laws)/len(laws))
            for index,(counts,_) in enumerate(laws[0])]


def regret_bound(case, work=None):
    values = []
    for categories in product(*(SUPPORT[op] for op in OPERATORS)):
        probabilities = {op: {cat: F(cat == chosen) for cat in SUPPORT[op]}
                         for op,chosen in zip(OPERATORS,categories)}
        pure = settled.vectors(case,probabilities)
        ranges = []
        for weights in independent.QUERY_WEIGHTS.values():
            utilities = [v[0]*weights[0]-v[1]*weights[1]+v[2]*weights[2] for v in pure.values()]
            ranges.append(max(utilities)-min(utilities))
        values.append(sum(ranges)/3)
    record_forecast(work,dict(query_bound_vertices=12,query_bound_policy_values=144))
    return max(values)


def forecast_loss(plan, unavailable_bound):
    proxy = unavailable_bound if plan['query_proxy'] is None else plan['query_proxy']
    return max(F(0),F(2)-plan['utility_lower'])+max(F(0),proxy-F(1,20))


def choose(member, anchors, case, arm, plan, spent, work, cache):
    if arm != 'BRANCH': return prior.choose(member,anchors,case,arm,plan,spent,work)
    if spent == 384 or plan['query_ready']: return None
    counts = {op: sum(member[op].values()) for op in OPERATORS}
    for op in OPERATORS:
        if not counts[op]:
            return dict(scope='TARGET',source_index=None,operator=op,reason='target_pilot',counts=counts)
    bound,scores = regret_bound(case,work),{}
    for op in OPERATORS:
        losses,ready,unavailable = [],[],[]
        distribution = predictive_distribution(member,anchors,plan,op,work)
        mass = F(0)
        for increments,probability in distribution:
            branch = {name: dict(row) for name,row in member.items()}
            for cat,amount in increments.items(): branch[op][cat] += amount
            predicted = forecast_plan(branch,anchors,case,work,cache)
            mass += probability
            weight = float(probability)
            losses.append(weight*float(forecast_loss(predicted,bound)))
            ready.append(weight*predicted['query_ready'])
            unavailable.append(weight*(predicted['query_proxy'] is None))
        scores[op] = dict(expected_loss=fsum(losses),ready_probability=fsum(ready),
            unavailable_probability=fsum(unavailable),probability_mass=mass,branches=len(distribution))
    selected = min(OPERATORS,key=lambda op: (scores[op]['expected_loss'],counts[op],OPERATORS.index(op)))
    return dict(scope='TARGET',source_index=None,operator=selected,reason='branch_integral',scores=scores)


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
    contrasts = {key: [] for key in ('local_minus_branch_samples','set_minus_branch_samples',
        'branch_minus_local_late_utility','branch_minus_set_post_regret','branch_minus_oracle_samples',
        'branch_minus_set_late_utility','branch_minus_set_late_certified',
        'mean_minus_branch_samples','branch_minus_mean_post_regret',
        'branch_minus_mean_late_utility','branch_minus_mean_late_certified')}
    for life in range(12):
        rows = [r for r in results if r['life'] == life]
        costs = {arm: historical[arm][life]+sum(r['spent'] for r in rows if r['arm'] == arm) for arm in ARMS}
        utility = {arm: settled.mean(float(r['terminal']['actual_utility']) for r in rows
                        if r['arm'] == arm and r['index'] >= 15) for arm in ARMS}
        regret = {arm: settled.mean(float(v['regret']) for r in rows if r['arm'] == arm
                        and r['index'] >= 15 for v in r['query_post'].values()) for arm in ARMS}
        contrasts['local_minus_branch_samples'].append(costs['LOCAL']-costs['BRANCH'])
        contrasts['set_minus_branch_samples'].append(costs['SET']-costs['BRANCH'])
        contrasts['branch_minus_oracle_samples'].append(costs['BRANCH']-costs['ORACLE'])
        contrasts['branch_minus_local_late_utility'].append(utility['BRANCH']-utility['LOCAL'])
        contrasts['branch_minus_set_late_utility'].append(utility['BRANCH']-utility['SET'])
        contrasts['branch_minus_set_late_certified'].append(
            sum(r['certified'] for r in rows if r['arm'] == 'BRANCH' and r['index'] >= 15)
            -sum(r['certified'] for r in rows if r['arm'] == 'SET' and r['index'] >= 15))
        contrasts['branch_minus_set_post_regret'].append(regret['BRANCH']-regret['SET'])
        contrasts['mean_minus_branch_samples'].append(costs['MEAN']-costs['BRANCH'])
        contrasts['branch_minus_mean_post_regret'].append(regret['BRANCH']-regret['MEAN'])
        contrasts['branch_minus_mean_late_utility'].append(utility['BRANCH']-utility['MEAN'])
        contrasts['branch_minus_mean_late_certified'].append(
            sum(r['certified'] for r in rows if r['arm'] == 'BRANCH' and r['index'] >= 15)
            -sum(r['certified'] for r in rows if r['arm'] == 'MEAN' and r['index'] >= 15))
    rng = random.Random(224900)
    samples = {key: [] for key in contrasts}
    for _ in range(5000):
        indices = [rng.randrange(12) for _ in range(12)]
        for key,rows in contrasts.items():
            samples[key].append(settled.mean(rows[i] for i in indices))
        work['bootstrap_index_draws'] += 12
        work['bootstrap_mean_terms'] += 132
    intervals = {key: dict(mean=settled.mean(rows),
        ci=[sorted(samples[key])[124],sorted(samples[key])[4874]]) for key,rows in contrasts.items()}
    target = arms['BRANCH']
    points = [p for r in results if r['arm'] == 'BRANCH' for p in r['history']]
    conditions = dict(
        COST=intervals['local_minus_branch_samples']['mean'] >= 64
             and intervals['local_minus_branch_samples']['ci'][0] > 0,
        QUALITY=target['late_certified'] >= 108
                and target['late_certified'] >= arms['LOCAL']['late_certified']
                and target['late_utility'] >= 2
                and intervals['branch_minus_local_late_utility']['ci'][0] >= -.05,
        RISK=all(p['actual'][1] <= F(1,20) and p['risk_upper'] <= F(1,20) for p in points),
        APPLICABILITY=target['late_transferred'] >= 108 and target['late_post_regret'] <= .05,
        TARGET_EFFECT=intervals['set_minus_branch_samples']['ci'][0] > 0
                    and intervals['branch_minus_set_post_regret']['ci'][1] <= .01,
        REFERENCE_QUALITY=target['late_certified'] >= arms['SET']['late_certified']
                    and intervals['branch_minus_set_late_utility']['ci'][0] >= -.05,
        MEAN_EFFECT=intervals['mean_minus_branch_samples']['ci'][0] > 0
                    and intervals['branch_minus_mean_post_regret']['ci'][1] <= .01
                    and target['late_certified'] >= arms['MEAN']['late_certified']
                    and intervals['branch_minus_mean_late_utility']['ci'][0] >= -.05)
    return dict(complete=True,arms=arms,contrasts=contrasts,bootstrap=intervals,conditions=conditions,
        decision='BRANCH_ACQUISITION_SUPPORTED' if all(conditions.values()) else 'BRANCH_ACQUISITION_NOT_SUPPORTED')


def analyze():
    begun = perf_counter()
    work,actual,planning = Counter(),Counter(),Counter()
    integrated_choices = 0
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
        check('complete_unique_fresh_targets',len(rows) == len(lookup) == 1440
              and all((life,index,arm) in lookup for life in range(12)
                      for index in range(3,27) for arm in ARMS))
        paired = True
        for life in range(12):
            for index in range(3,27):
                seeds = {op: 225000+(life*27+index)*3+i for i,op in enumerate(OPERATORS)}
                paired &= all(lookup[life,index,arm]['seeds'] == seeds for arm in ARMS)
        check('five_arm_shared_fresh_target_prefix_seeds',paired)
        maximum = Counter()
        for row in rows:
            for op in OPERATORS:
                n = 16*sum(b['operator'] == op for b in row['batches'])
                key = row['life'],row['index'],op
                maximum[key] = max(maximum[key],n)
        prefixes = {key: settled.generate_prefix(
            225000+(key[0]*27+key[1])*3+OPERATORS.index(key[2]),n,
            worlds[key[0]][1][key[1]][key[2]],SUPPORT[key[2]],work)
            for key,n in maximum.items()}
        results = []
        for life in range(12):
            cases,laws,identities = worlds[life]
            anchors = libraries[life]['anchors']
            cache = prepare(anchors,work)
            decisions_ok = allocation_ok = counts_ok = plans_ok = True
            for index in range(3,27):
                case = cases[index]
                seeds = {op: 225000+(life*27+index)*3+i for i,op in enumerate(OPERATORS)}
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
                        choice = choose(member,library,case,arm,plan,spent,work,cache)
                        allocation_ok &= choice is not None and same(batch['choice'],choice)
                        op = choice['operator']
                        if arm == 'BRANCH' and choice['reason'] == 'branch_integral': integrated_choices += 1
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
                    allocation_ok &= choose(member,library,case,arm,plan,spent,work,cache) is None
                    allocation_ok &= 0 <= spent <= 384
                    fallback = arm != 'LOCAL' and len(plan['candidates']) != 1 and not (arm in ('BRANCH','MEAN','SET') and plan['query_ready'])
                    if fallback:
                        plan = make_plan(member,library,case,arm,work,identity,force_member=True)
                        planning[arm] += 1
                        points.append(score(plan,laws[index],case,spent,work))
                    certified = plan['utility_lower'] >= 2
                    identified = arm != 'LOCAL' and len(plan['candidates']) == 1 and certified
                    transferred = arm != 'LOCAL' and certified and plan['mode'] == 'library' and (identified or arm in ('BRANCH','MEAN','SET') and plan['query_ready'])
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
        check('actual_fresh_target_and_planning_costs',sum(actual.values()) <= 552960 and all(
            run['arm_costs'][arm].get(key,0) == actual[arm]
            for arm in ARMS for key in ('controlled_samples','controlled_resets','environment_random_draws'))
            and all(run['arm_costs'][arm]['planning_calls'] == planning[arm] for arm in ARMS)
            and run['arm_costs']['BRANCH'].get('forecast_planning_calls',0) == 187*integrated_choices
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
