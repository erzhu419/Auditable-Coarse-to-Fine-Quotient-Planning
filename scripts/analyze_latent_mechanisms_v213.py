"""Independent V213 replay; no producer learner, mechanism or task import."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from itertools import combinations
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import analyze_conditioned_mechanisms_v205 as settled

OUTPUT = ROOT / 'reports/latent_mechanisms_v213'
ARMS = ('LATENT', 'LOCAL', 'ORACLE')
OPERATORS, SUPPORT = settled.OPERATORS, settled.SUPPORT
F = Fraction
settled.BETA = math.log(2 * 5544 / .05)


def empty():
    return {op: dict.fromkeys(SUPPORT[op], 0) for op in OPERATORS}


def posterior(counts):
    result = {}
    for op in OPERATORS:
        n = sum(counts[op].values())
        result[op] = {cat: F(2*k+1, 2*n+len(SUPPORT[op]))
                      for cat, k in counts[op].items()}
    return result


def intersections(member, anchors, work, identity=None):
    """Intersect marginal boxes without treating pooled counts as a certificate."""
    raw = settled.boxes(member, work)
    accepted, envelopes = [], {}
    for index, anchor in enumerate(anchors):
        if identity is not None and index != identity:
            continue
        reference = settled.boxes(anchor, work)
        bounds = {}
        ok = True
        for op in OPERATORS:
            bounds[op] = {}
            for cat in SUPPORT[op]:
                a, b = raw[op]['bounds'][cat], reference[op]['bounds'][cat]
                lo, hi = max(a[0], b[0]), min(a[1], b[1])
                bounds[op][cat] = (lo, hi)
                ok &= lo <= hi
        if ok:
            accepted.append(index)
            envelopes[index] = {op: dict(n=raw[op]['n'], counts=dict(member[op]),
                                         bounds=bounds[op]) for op in OPERATORS}
    return raw, accepted, envelopes


def make_plan(member, anchors, case, arm, work, identity=None, force_member=False):
    use = anchors if arm != 'LOCAL' and not force_member else []
    raw, candidates, blocks = intersections(member, use, work,
                                             identity if arm == 'ORACLE' else None)
    if candidates:
        risk_sets = [settled.risk_bounds(block) for block in blocks.values()]
        goal_sets = [settled.goal_bounds(block, case) for block in blocks.values()]
        upper = {p: max(F(0), *(r[p] for r in risk_sets)) for p in risk_sets[0]}
        lower = {p: min(g[p] for g in goal_sets) for p in goal_sets[0]}
        means = [posterior({op: {cat: anchors[i][op][cat]+member[op][cat]
                               for cat in SUPPORT[op]} for op in OPERATORS})
                 for i in candidates]
        probabilities = {op: {cat: sum(p[op][cat] for p in means)/len(means)
                              for cat in SUPPORT[op]} for op in OPERATORS}
        envelope = deepcopy(raw)
        for op in OPERATORS:
            envelope[op]['bounds'] = {cat: (
                min(block[op]['bounds'][cat][0] for block in blocks.values()),
                max(block[op]['bounds'][cat][1] for block in blocks.values()))
                for cat in SUPPORT[op]}
        mode = 'library'
    else:
        envelope = raw
        upper, lower = settled.risk_bounds(raw), settled.goal_bounds(raw, case)
        probabilities, mode = posterior(member), 'member'
    pure = settled.vectors(case, probabilities)
    return dict(settled.optimize(pure, upper, lower, work), envelopes=envelope,
                risks=upper, goals_lower=lower, pure_vectors=pure,
                candidates=candidates, candidate_envelopes=blocks, mode=mode)


def goal_choice(member, case, plan):
    counts = {op: plan['envelopes'][op]['n'] for op in OPERATORS}
    for op in OPERATORS:
        if not counts[op]:
            return dict(operator=op, pilot=True, reason='member_probe', policy=None,
                        policy_scores=None, projection_counts=counts, sensitivity_scores=None)
    values = {name: max(F(0), v[0]+4*v[2])*min(F(1), F(1,20)/v[1])
              for name,v in plan['pure_vectors'].items() if name != 'WAIT'}
    capable = [name for name in values if values[name] >= 2]
    policy = min(capable, key=lambda name: (1+int(name=='DETOUR_RETRY'), -values[name], name)) if capable else min(values, key=lambda name: (-values[name], name))
    sensitivity = None
    if policy == 'SHORT': op = 'SHORT_PASS'
    elif policy == 'DETOUR_RETURN': op = 'DETOUR_PASS'
    else:
        sensitivity = {}
        p = posterior(member)
        for op in ('DETOUR_PASS', 'RECOVERY_RETRY'):
            box = deepcopy(plan['envelopes'])
            box[op]['bounds'] = {cat: (prob, prob) for cat,prob in p[op].items()}
            upper = settled.risk_bounds(box)[policy]
            lower = settled.goal_bounds(box, case)[policy]
            sensitivity[op] = max(F(0), lower*min(F(1),F(1,20)/upper)) if upper else max(F(0),lower)
        op = min(sensitivity, key=lambda name: (-sensitivity[name], OPERATORS.index(name)))
    return dict(operator=op, pilot=False, reason='constrained_target', policy=policy,
                policy_scores=values, projection_counts=counts, sensitivity_scores=sensitivity)


def choose(member, anchors, case, arm, plan, spent, work, source=False):
    if source and arm != 'LOCAL':
        return None if spent == 1152 else dict(operator=OPERATORS[(spent//16)%3], reason='paid_anchor')
    if spent == (1152 if source else 384): return None
    if plan['utility_lower'] >= 2 and (arm == 'LOCAL' or source or len(plan['candidates']) == 1): return None
    if arm == 'LATENT' and len(plan['candidates']) > 1:
        means = {i: posterior(anchors[i]) for i in plan['candidates']}
        scores = {op: min(sum(abs(means[a][op][cat]-means[b][op][cat])
                              for cat in SUPPORT[op])/2
                          for a,b in combinations(plan['candidates'],2)) for op in OPERATORS}
        op = min(OPERATORS, key=lambda name: (-scores[name], OPERATORS.index(name)))
        return dict(operator=op, reason='identify', scores=scores)
    detail = goal_choice(member, case, plan)
    return dict(operator=detail['operator'], reason='certify', detail=detail)


QUERY_WEIGHTS = {'reward': (1,0,0), 'goal': (1,0,4), 'risk': (1,4,4)}


def queries(plan):
    result = {}
    for query,weights in QUERY_WEIGHTS.items():
        def value(name):
            v = plan['pure_vectors'][name]
            return v[0]*weights[0]-v[1]*weights[1]+v[2]*weights[2]
        result[query] = dict(policy=min(plan['pure_vectors'], key=lambda name: (-value(name), name)))
    return result


def world(life):
    labels = list(settled.WEATHER)
    random.Random(214900+life).shuffle(labels)
    targets = list(settled.WEATHER)*8
    random.Random(215000+life).shuffle(targets)
    costs = [(op,retry) for op in ('low','high') for retry in ('17/20','19/20')]*6
    random.Random(215100+life).shuffle(costs)
    cases = [dict(id=f'unit_{i:02d}', operating='high', retry_cost='19/20') for i in range(3)]
    cases += [dict(id=f'unit_{i+3:02d}', operating=op, retry_cost=retry)
              for i,(op,retry) in enumerate(costs)]
    kernels = [settled.true_laws(dict(weather=label)) for label in labels+targets]
    identities = [0,1,2]+[labels.index(label) for label in targets]
    return cases, kernels, identities


def score(plan, law, case, spent, work):
    pure = settled.vectors(case, law)
    actual = settled.joint(plan['mix'], pure, work)
    coverage = all(lo <= law[op][cat] <= hi
                   for op,env in plan['envelopes'].items()
                   for cat,(lo,hi) in env['bounds'].items())
    return dict(spent=spent, actual=actual, actual_utility=actual[0]+4*actual[2],
                risk_upper=plan['risk_upper'], utility_lower=plan['utility_lower'],
                violation=actual[1] > F(1,20), coverage=coverage)


def query_score(decision, law, case):
    pure = settled.vectors(case, law)
    result = {}
    for query,weights in QUERY_WEIGHTS.items():
        def value(v): return v[0]*weights[0]-v[1]*weights[1]+v[2]*weights[2]
        name = decision[query]['policy']
        actual = pure[name]
        result[query] = dict(policy=name, actual=actual, utility=value(actual),
                             regret=max(value(v) for v in pure.values())-value(actual))
    return result


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
            late_identified=sum(r['identified'] and r['identity_correct'] for r in late),
            wrong_identifications=sum(r['identified'] and not r['identity_correct'] for r in rows),
            late_utility=settled.mean(float(r['terminal']['actual_utility']) for r in late),
            late_post_regret=settled.mean(float(v['regret']) for r in late for v in r['query_post'].values()),
            history_violations=sum(p['violation'] for p in points),
            max_failure=max(float(p['actual'][1]) for p in points),
            coverage=settled.mean(p['coverage'] for p in points),
            member_fallbacks=sum(r['fallback'] for r in rows))
    contrasts = {key: [] for key in ('local_minus_latent_samples',
        'latent_minus_local_late_utility', 'latent_minus_oracle_samples')}
    for life in range(12):
        rows = [r for r in results if r['life'] == life]
        costs = {arm: sum(r['spent'] for r in rows if r['arm'] == arm) for arm in ARMS}
        utility = {arm: settled.mean(float(r['terminal']['actual_utility']) for r in rows
                        if r['arm'] == arm and r['index'] >= 15) for arm in ARMS}
        contrasts['local_minus_latent_samples'].append(costs['LOCAL']-costs['LATENT'])
        contrasts['latent_minus_local_late_utility'].append(utility['LATENT']-utility['LOCAL'])
        contrasts['latent_minus_oracle_samples'].append(costs['LATENT']-costs['ORACLE'])
    rng = random.Random(213900)
    samples = {key: [] for key in contrasts}
    for _ in range(5000):
        indices = [rng.randrange(12) for _ in range(12)]
        for key,rows in contrasts.items():
            samples[key].append(settled.mean(rows[i] for i in indices))
        work['bootstrap_index_draws'] += 12
        work['bootstrap_mean_terms'] += 36
    intervals = {key: dict(mean=settled.mean(rows),
        ci=[sorted(samples[key])[124], sorted(samples[key])[4874]])
        for key,rows in contrasts.items()}
    target = arms['LATENT']
    points = [p for r in results if r['arm'] == 'LATENT' for p in r['history']]
    conditions = dict(
        COST=intervals['local_minus_latent_samples']['mean'] >= 64
             and intervals['local_minus_latent_samples']['ci'][0] > 0,
        QUALITY=target['late_certified'] >= 108
                and target['late_certified'] >= arms['LOCAL']['late_certified']
                and target['late_utility'] >= 2
                and intervals['latent_minus_local_late_utility']['ci'][0] >= -.05,
        RISK=all(p['actual'][1] <= F(1,20) and p['risk_upper'] <= F(1,20) for p in points),
        IDENTITY=target['late_identified'] >= 108 and target['late_post_regret'] <= .05)
    return dict(complete=True, arms=arms, contrasts=contrasts, bootstrap=intervals,
        conditions=conditions, decision='LATENT_MECHANISMS_SUPPORTED' if all(conditions.values())
                                      else 'LATENT_MECHANISMS_NOT_SUPPORTED')


def exact(value):
    return json.loads(json.dumps(settled.exact_json(value)))


def same(saved, expected):
    return settled.equal_numbers(saved, exact(expected))


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
        check('complete_unique_lifecycles', len(rows) == len(lookup) == 972
              and all((life,index,arm) in lookup for life in range(12)
                      for index in range(27) for arm in ARMS))
        maximum = Counter()
        for row in rows:
            for op in OPERATORS:
                n = 16*sum(b['operator'] == op for b in row['batches'])
                key = row['life'],row['index'],op
                maximum[key] = max(maximum[key],n)
        prefixes = {key: settled.generate_prefix(
            214000+(key[0]*27+key[1])*3+OPERATORS.index(key[2]), n,
            worlds[key[0]][1][key[1]][key[2]], SUPPORT[key[2]], work)
            for key,n in maximum.items()}
        results = []
        for life in range(12):
            cases, laws, identities = worlds[life]
            anchors = {arm: [] for arm in ARMS}
            decisions_ok = allocation_ok = counts_ok = plans_ok = True
            for index,case in enumerate(cases):
                source = index < 3
                seeds = {op: 214000+(life*27+index)*3+i for i,op in enumerate(OPERATORS)}
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
                    fallback = not source and arm != 'LOCAL' and len(plan['candidates']) != 1
                    if fallback:
                        plan = make_plan(member,library,case,arm,work,identity,force_member=True)
                        planning[arm] += 1
                        points.append(score(plan,laws[index],case,spent,work))
                    certified = plan['utility_lower'] >= 2
                    identified = not source and arm != 'LOCAL' and len(plan['candidates']) == 1 and certified
                    stop = ('anchor_complete' if source and arm != 'LOCAL' else
                            'member_budget' if fallback else 'identified' if identified else
                            'member_certified' if certified else 'budget')
                    allocation_ok &= row['stop'] == stop and row['fallback'] == fallback
                    plans_ok &= row['spent'] == spent and row['certified'] == certified
                    plans_ok &= row['identified'] == identified and same(row['member'],member)
                    plans_ok &= same(row['terminal_plan'],plan)
                    post = queries(plan)
                    decisions_ok &= same(row['terminal_query'],post)
                    correct = identified and plan['candidates'][0] == identities[index]
                    results.append(dict(life=life,index=index,arm=arm,spent=spent,certified=certified,
                        identified=identified,identity_correct=correct,fallback=fallback,
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
        check('paid_calibration_target_and_environment_costs',
            sum(actual.values()) <= 456192 and all(
                run['arm_costs'][arm][key] == actual[arm]
                for arm in ARMS for key in ('controlled_samples','controlled_resets','environment_random_draws'))
            and all(run['arm_costs'][arm]['planning_calls'] == planning[arm] for arm in ARMS)
            and expected['arms']['LATENT']['source_samples'] == expected['arms']['ORACLE']['source_samples'] == 41472)
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
