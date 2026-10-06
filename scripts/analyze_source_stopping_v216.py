"""Independent paid-source stopping replay from settled V213 audit math."""
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
from scripts import analyze_latent_mechanisms_v213 as independent

OUTPUT = ROOT/'reports/source_stopping_v216'
ARMS = ('EARLY','FULL','LOCAL','ORACLE')
OPERATORS, SUPPORT = independent.OPERATORS, independent.SUPPORT
F = Fraction


def base_arm(arm):
    return 'LATENT' if arm in ('EARLY','FULL') else arm


def make_plan(member, anchors, case, arm, work, identity=None, force_member=False):
    plan = independent.make_plan(member,anchors,case,base_arm(arm),work,identity,force_member)
    value = proxy(member,anchors,case,plan)
    plan['query_proxy'] = value
    plan['query_ready'] = plan['mode'] == 'library' and value is not None and plan['utility_lower'] >= 2 and value <= F(1,20)
    return plan


def proxy(member, anchors, case, plan):
    """Whole-query mean regret, evaluated separately under each candidate mean."""
    decision = independent.queries(plan)
    values = []
    for index in plan['candidates']:
        counts = {op: {cat: member[op][cat]+anchors[index][op][cat]
                       for cat in SUPPORT[op]} for op in OPERATORS}
        pure = independent.settled.vectors(case,independent.posterior(counts))
        losses = []
        for query,weights in independent.QUERY_WEIGHTS.items():
            def utility(v): return v[0]*weights[0]-v[1]*weights[1]+v[2]*weights[2]
            selected = decision[query]['policy']
            losses.append(max(utility(v) for v in pure.values())-utility(pure[selected]))
        values.append(sum(losses)/3)
    return max(values) if values else None


def sufficient(member, anchors, case, plan):
    return plan['query_ready']


def choose(member, anchors, case, arm, plan, spent, work, source=False):
    if source and arm in ('EARLY','FULL','ORACLE'):
        if spent == 1152: return None
        counts = {op: sum(member[op].values()) for op in OPERATORS}
        if arm in ('EARLY','ORACLE') and min(counts.values()) >= 32 and plan['utility_lower'] >= 2:
            return None
        op = min(OPERATORS, key=lambda name: (counts[name],OPERATORS.index(name)))
        if counts[op] < 32:
            return dict(operator=op,reason='calibration_pilot',counts=counts)
        if plan['utility_lower'] < 2:
            detail = independent.goal_choice(member,case,plan)
            return dict(operator=detail['operator'],reason='calibration_certificate',detail=detail)
        return dict(operator=op,reason='calibration_balance',counts=counts)
    if arm in ('EARLY','FULL') and not source and sufficient(member,anchors,case,plan): return None
    return independent.choose(member,anchors,case,base_arm(arm),plan,spent,work,source)


empty, world, queries = independent.empty, independent.world, independent.queries
score, query_score, same = independent.score, independent.query_score, independent.same
settled = independent.settled


def summary(results, work):
    arms = {}
    for arm in ARMS:
        rows = [r for r in results if r['arm'] == arm]
        late = [r for r in rows if r['index'] >= 15]
        points = [p for r in rows for p in r['history']]
        arms[arm] = dict(total_samples=sum(r['spent'] for r in rows),
            source_samples=sum(r['spent'] for r in rows if r['index'] < 3),
            target_samples=sum(r['spent'] for r in rows if r['index'] >= 3),
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
    contrasts = {key: [] for key in ('local_minus_early_samples','full_minus_early_samples',
        'early_minus_local_late_utility','early_minus_full_post_regret','early_minus_oracle_samples')}
    for life in range(12):
        rows = [r for r in results if r['life'] == life]
        costs = {arm: sum(r['spent'] for r in rows if r['arm'] == arm) for arm in ARMS}
        utility = {arm: settled.mean(float(r['terminal']['actual_utility']) for r in rows
                        if r['arm'] == arm and r['index'] >= 15) for arm in ARMS}
        regret = {arm: settled.mean(float(v['regret']) for r in rows if r['arm'] == arm
                        and r['index'] >= 15 for v in r['query_post'].values()) for arm in ARMS}
        contrasts['local_minus_early_samples'].append(costs['LOCAL']-costs['EARLY'])
        contrasts['full_minus_early_samples'].append(costs['FULL']-costs['EARLY'])
        contrasts['early_minus_oracle_samples'].append(costs['EARLY']-costs['ORACLE'])
        contrasts['early_minus_local_late_utility'].append(utility['EARLY']-utility['LOCAL'])
        contrasts['early_minus_full_post_regret'].append(regret['EARLY']-regret['FULL'])
    rng = random.Random(219900)
    samples = {key: [] for key in contrasts}
    for _ in range(5000):
        indices = [rng.randrange(12) for _ in range(12)]
        for key,rows in contrasts.items():
            samples[key].append(settled.mean(rows[i] for i in indices))
        work['bootstrap_index_draws'] += 12
        work['bootstrap_mean_terms'] += 60
    intervals = {key: dict(mean=settled.mean(rows),
        ci=[sorted(samples[key])[124],sorted(samples[key])[4874]]) for key,rows in contrasts.items()}
    target = arms['EARLY']
    points = [p for r in results if r['arm'] == 'EARLY' for p in r['history']]
    conditions = dict(
        COST=intervals['local_minus_early_samples']['mean'] >= 64
             and intervals['local_minus_early_samples']['ci'][0] > 0,
        QUALITY=target['late_certified'] >= 108
                and target['late_certified'] >= arms['LOCAL']['late_certified']
                and target['late_utility'] >= 2
                and intervals['early_minus_local_late_utility']['ci'][0] >= -.05,
        RISK=all(p['actual'][1] <= F(1,20) and p['risk_upper'] <= F(1,20) for p in points),
        APPLICABILITY=target['late_transferred'] >= 108 and target['late_post_regret'] <= .05,
        SOURCE_STOP_EFFECT=intervals['full_minus_early_samples']['ci'][0] > 0
                    and intervals['early_minus_full_post_regret']['ci'][1] <= .01)
    return dict(complete=True,arms=arms,contrasts=contrasts,bootstrap=intervals,conditions=conditions,
        decision='SOURCE_STOPPING_SUPPORTED' if all(conditions.values()) else 'SOURCE_STOPPING_NOT_SUPPORTED')


def analyze():
    begun = perf_counter()
    work, actual, planning = Counter(), Counter(), Counter()
    checks = []
    def check(name, value): checks.append(dict(name=name, passed=bool(value)))
    def read(name): return json.loads((OUTPUT/name).read_text())
    try:
        rows = read('records.json')
        cases_saved = read('cases.json')
        worlds = [world(life) for life in range(12)]
        check('fixed_opaque_private_worlds', same(cases_saved,
              [dict(life=life, cases=worlds[life][0]) for life in range(12)]))
        lookup = {(r['life'],r['index'],r['arm']): r for r in rows}
        check('complete_unique_lifecycles', len(rows) == len(lookup) == 1296
              and all((life,index,arm) in lookup for life in range(12)
                      for index in range(27) for arm in ARMS))
        paired = True
        for life in range(12):
            for index in range(27):
                seeds = {op: 220000+(life*27+index)*3+i for i,op in enumerate(OPERATORS)}
                paired &= all(lookup[life,index,arm]['seeds'] == seeds for arm in ARMS)
        check('four_arm_shared_potential_prefix_seeds',paired)
        source_rows = [r for r in rows if r['index'] < 3 and r['arm'] != 'LOCAL']
        check('source_empty_starts_and_minimum_pilot',all(
            r['initial_plan']['mode'] == 'member' and not r['initial_plan']['candidates']
            and all(r['initial_plan']['envelopes'][op]['n'] == 0 for op in OPERATORS)
            and all(sum(r['member'][op].values()) >= 32 for op in OPERATORS)
            for r in source_rows))
        check('full_source_pays_unchanged_budget',all(
            r['spent'] == 1152 and len(r['batches']) == 72
            for r in source_rows if r['arm'] == 'FULL'))
        source_prefix_ok = source_oracle_ok = True
        for life in range(12):
            for index in range(3):
                early, full, oracle = (lookup[life,index,arm] for arm in ('EARLY','FULL','ORACLE'))
                full_prefix = full['batches'][:len(early['batches'])]
                prefix_counts = empty()
                for batch in full_prefix:
                    for cat,k in batch['increments'].items():
                        prefix_counts[batch['operator']][cat] += k
                source_prefix_ok &= early['initial_plan'] == full['initial_plan']
                source_prefix_ok &= early['batches'] == full_prefix
                source_prefix_ok &= early['member'] == prefix_counts
                source_prefix_ok &= early['spent'] == 16*len(full_prefix) <= full['spent']
                source_oracle_ok &= all(early[key] == oracle[key] for key in (
                    'initial_plan','initial_query','batches','member','spent','terminal_plan',
                    'terminal_query','certified','identified','transferred','fallback','stop'))
        check('early_source_exact_full_acquisition_and_count_prefixes',source_prefix_ok)
        check('early_and_oracle_source_acquisition_identical',source_oracle_ok)
        maximum = Counter()
        for row in rows:
            for op in OPERATORS:
                n = 16*sum(b['operator'] == op for b in row['batches'])
                key = row['life'],row['index'],op
                maximum[key] = max(maximum[key],n)
        prefixes = {key: settled.generate_prefix(
            220000+(key[0]*27+key[1])*3+OPERATORS.index(key[2]), n,
            worlds[key[0]][1][key[1]][key[2]], SUPPORT[key[2]], work)
            for key,n in maximum.items()}
        results = []
        for life in range(12):
            cases, laws, identities = worlds[life]
            anchors = {arm: [] for arm in ARMS}
            decisions_ok = allocation_ok = counts_ok = plans_ok = True
            for index,case in enumerate(cases):
                source = index < 3
                seeds = {op: 220000+(life*27+index)*3+i for i,op in enumerate(OPERATORS)}
                for arm in ARMS:
                    row = lookup[life,index,arm]
                    member = empty()
                    library = anchors[arm] if not source and arm != 'LOCAL' else []
                    identity = identities[index] if arm == 'ORACLE' else None
                    plan = make_plan(member, library, case, arm, work, identity)
                    planning[arm] += 1
                    plans_ok &= same(row['case'],case) and row['seeds'] == seeds
                    plans_ok &= same(row['initial_plan'],plan)
                    pre = queries(plan)
                    decisions_ok &= same(row['initial_query'],pre)
                    points = [score(plan,laws[index],case,0,work)]
                    spent, consumed = 0, Counter()
                    for batch in row['batches']:
                        choice = choose(member,library,case,arm,plan,spent,work,source)
                        allocation_ok &= choice is not None and same(batch['choice'],choice)
                        op = choice['operator']
                        increments = dict.fromkeys(SUPPORT[op],0)
                        for cat in prefixes[life,index,op][consumed[op]:consumed[op]+16]:
                            increments[cat] += 1
                        counts_ok &= batch['operator'] == op and batch['draw_start'] == consumed[op]
                        counts_ok &= batch['increments'] == increments and sum(increments.values()) == 16
                        for cat,k in increments.items(): member[op][cat] += k
                        consumed[op] += 16; spent += 16; actual[arm] += 16
                        counts_ok &= batch['draw_end'] == consumed[op] and batch['spent'] == spent
                        plan = make_plan(member,library,case,arm,work,identity)
                        planning[arm] += 1
                        plans_ok &= same(batch['plan'],plan)
                        points.append(score(plan,laws[index],case,spent,work))
                    allocation_ok &= choose(member,library,case,arm,plan,spent,work,source) is None
                    allocation_ok &= 0 <= spent <= (1152 if source else 384)
                    fallback = not source and arm != 'LOCAL' and len(plan['candidates']) != 1 and not (arm in ('EARLY','FULL') and plan['query_ready'])
                    if fallback:
                        plan = make_plan(member,library,case,arm,work,identity,force_member=True)
                        planning[arm] += 1
                        points.append(score(plan,laws[index],case,spent,work))
                    certified = plan['utility_lower'] >= 2
                    identified = not source and arm != 'LOCAL' and len(plan['candidates']) == 1 and certified
                    transferred = not source and arm != 'LOCAL' and certified and plan['mode'] == 'library' and (identified or arm in ('EARLY','FULL') and plan['query_ready'])
                    if source and arm != 'LOCAL':
                        stop = ('anchor_complete' if arm == 'FULL' else
                                'source_budget' if spent == 1152 else 'source_certified')
                    else:
                        stop = ('member_budget' if fallback else 'query_set' if transferred and not identified else
                                'identified' if identified else 'member_certified' if certified else 'budget')
                    allocation_ok &= row['stop'] == stop and row['fallback'] == fallback
                    plans_ok &= row['spent'] == spent and row['certified'] == certified
                    plans_ok &= row['identified'] == identified and row['transferred'] == transferred and same(row['member'],member)
                    plans_ok &= same(row['terminal_plan'],plan)
                    post = queries(plan)
                    decisions_ok &= same(row['terminal_query'],post)
                    correct = identified and plan['candidates'][0] == identities[index]
                    transfer_correct = transferred and identities[index] in plan['candidates']
                    results.append(dict(life=life,index=index,arm=arm,spent=spent,certified=certified,
                        identified=identified,identity_correct=correct,transferred=transferred,transfer_correct=transfer_correct,fallback=fallback,
                        history=points,terminal=points[-1],
                        query_pre=query_score(pre,laws[index],case),
                        query_post=query_score(post,laws[index],case)))
                    if source: anchors[arm].append(deepcopy(member))
            for name,flag in [('full_policy_queries',decisions_ok), ('choices_stops_and_fallbacks',allocation_ok),
                              ('actual_paired_prefixes',counts_ok), ('candidates_and_intersection_plans',plans_ok)]:
                check(f'life_{life}_{name}',flag)
        check('true_joint_and_own_query_results', same(read('results.json'),results))
        stats = Counter()
        expected = summary(results,stats)
        check('paired_statistics_and_frozen_gates', same(read('summary.json'),expected))
        run = read('run.json')
        check('paid_source_target_and_environment_costs',
            sum(actual.values()) <= 608256 and all(
                run['arm_costs'][arm][key] == actual[arm]
                for arm in ARMS for key in ('controlled_samples','controlled_resets','environment_random_draws'))
            and all(run['arm_costs'][arm]['planning_calls'] == planning[arm] for arm in ARMS)
            and expected['arms']['FULL']['source_samples'] == 41472)
        check('frozen_bootstrap_costs', run['bootstrap_costs'] == dict(stats))
        check('oracle_scoring_after_all_decisions', run['phases'] == [
            'protocol_frozen','all_decisions_frozen','oracle_evaluated','complete'])
        complete = True
    except Exception as error:
        check('reconstruction',False)
        checks[-1]['error'] = f'{type(error).__name__}: {error}'
        complete = False
    output = dict(valid=complete and all(c['passed'] for c in checks), complete=complete,
                  checks=checks,costs=dict(work),seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(valid=output['valid'],complete=complete,checks=len(checks))))
    return output


if __name__ == '__main__':
    raise SystemExit(0 if analyze()['valid'] else 1)
