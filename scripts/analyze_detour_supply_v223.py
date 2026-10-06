"""Independent paid-detour and cumulative-confidence lifecycle reconstruction."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import json
from math import log
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import analyze_assignment_union_v222 as union_math
from scripts import analyze_fixed_source_acquisition_v219 as source_audit

OUTPUT = ROOT/'reports/detour_supply_v223'
ARMS = ('FIXED_SET', 'UNION_SET', 'FIXED_DETOUR', 'UNION_DETOUR')
OPERATORS, SUPPORT = union_math.OPERATORS, union_math.SUPPORT
RAW_BETA = log(2*17640/.025)
POOL_BETA = log(2*27216/.025)
independent = union_math.prior
settled = independent.settled
empty, world, queries = independent.empty, independent.world, independent.queries
same, score, query_score = independent.same, independent.score, independent.query_score
intersect, feasible = union_math.intersect, union_math.feasible


def boxes(counts):
    return union_math.boxes(counts, RAW_BETA)


def raw_problem(anchors, members):
    source = [union_math.project_simplex(boxes(a)) for a in anchors]
    raw = [union_math.project_simplex(boxes(m)) for m in members]
    return dict(source_boxes=source, member_boxes=raw,
                masks=[[i for i, anchor in enumerate(source)
                        if intersect(anchor, member) is not None] for member in raw])


def projection(problem, anchors, members, masks):
    bounds, maximum = deepcopy(problem['source_boxes']), 0
    for i, anchor in enumerate(anchors):
        mandatory = [j for j, mask in enumerate(masks) if mask == [i]]
        optional = [j for j, mask in enumerate(masks) if i in mask and len(mask) > 1]
        for j in mandatory:
            if bounds[i] is not None:
                bounds[i] = intersect(bounds[i], problem['member_boxes'][j])
        if bounds[i] is None:
            return [], maximum
        for op in OPERATORS:
            n = sum(anchor[op].values())+sum(sum(members[j][op].values()) for j in mandatory)
            for cat in SUPPORT[op]:
                k = anchor[op][cat]+sum(members[j][op][cat] for j in mandatory)
                choices = [(sum(members[j][op].values()), members[j][op][cat]) for j in optional]
                states = union_math.subset_extrema(n, k, choices)
                maximum = max(maximum, len(states))
                lo = min(union_math.interval(a, total, POOL_BETA)[0]
                         for total, (a, b) in states.items())
                hi = max(union_math.interval(b, total, POOL_BETA)[1]
                         for total, (a, b) in states.items())
                old = bounds[i][op]['bounds'][cat]
                bounds[i][op]['bounds'][cat] = [max(old[0], lo), min(old[1], hi)]
        if not feasible(bounds[i]):
            return [], maximum
        bounds[i] = union_math.project_simplex(bounds[i])
    return bounds, maximum


def outer_union(problem, anchors, members):
    masks = deepcopy(problem['masks'])
    iterations, maximum = 0, 0
    while True:
        iterations += 1
        if any(not mask for mask in masks):
            return dict(bounds=[], masks=[[] for _ in members], no_feasible=True,
                        iterations=iterations, max_dp_states=maximum)
        bounds, count = projection(problem, anchors, members, masks)
        maximum = max(maximum, count)
        if not bounds:
            return dict(bounds=[], masks=[[] for _ in members], no_feasible=True,
                        iterations=iterations, max_dp_states=maximum)
        following = [[i for i in mask if intersect(bounds[i], problem['member_boxes'][j]) is not None]
                     for j, mask in enumerate(masks)]
        if following == masks:
            for block in bounds:
                for op in OPERATORS:
                    block[op]['kind'] = 'outer_assignment_union'
            return dict(bounds=bounds, masks=masks, no_feasible=False,
                        iterations=iterations, max_dp_states=maximum)
        masks = following


def prepare(anchors):
    return dict(members=[], bounds=raw_problem(anchors, [])['source_boxes'], masks=[],
                no_feasible=False, iterations=0, max_dp_states=0)


def make_plan(member, anchors, case, state, work, force_member=False):
    raw = boxes(member)
    candidates, blocks = [], {}
    for i, reference in enumerate([] if force_member else state['bounds']):
        block = intersect(raw, reference)
        if feasible(block):
            candidates.append(i)
            blocks[i] = block
    if candidates:
        risks = [settled.risk_bounds(block) for block in blocks.values()]
        goals = [settled.goal_bounds(block, case) for block in blocks.values()]
        upper = {policy: max(r[policy] for r in risks) for policy in risks[0]}
        lower = {policy: min(g[policy] for g in goals) for policy in goals[0]}
        means = [independent.posterior({op: {
            cat: member[op][cat]+anchors[i][op][cat] for cat in SUPPORT[op]}
            for op in OPERATORS}) for i in candidates]
        probabilities = {op: {cat: sum(p[op][cat] for p in means)/len(means)
                              for cat in SUPPORT[op]} for op in OPERATORS}
        envelope = deepcopy(raw)
        for op in OPERATORS:
            for cat in SUPPORT[op]:
                envelope[op]['bounds'][cat] = [min(b[op]['bounds'][cat][0] for b in blocks.values()),
                                               max(b[op]['bounds'][cat][1] for b in blocks.values())]
        mode = 'library'
    else:
        envelope, mode = raw, 'member'
        upper, lower = settled.risk_bounds(raw), settled.goal_bounds(raw, case)
        probabilities = independent.posterior(member)
    pure = settled.vectors(case, probabilities)
    result = dict(settled.optimize(pure, upper, lower, work), envelopes=envelope,
                  risks=upper, goals_lower=lower, pure_vectors=pure,
                  candidates=candidates, candidate_envelopes=blocks, mode=mode)
    chosen, regrets = queries(result), []
    for i in candidates:
        combined = {op: {cat: member[op][cat]+anchors[i][op][cat] for cat in SUPPORT[op]}
                    for op in OPERATORS}
        individual = settled.vectors(case, independent.posterior(combined))
        losses = []
        for name, weights in independent.QUERY_WEIGHTS.items():
            def value(v):
                return v[0]*weights[0]-v[1]*weights[1]+v[2]*weights[2]
            losses.append(max(value(v) for v in individual.values())-
                          value(individual[chosen[name]['policy']]))
        regrets.append(sum(losses)/3)
    proxy = max(regrets) if regrets else None
    result['query_proxy'] = proxy
    result['query_ready'] = mode == 'library' and result['utility_lower'] >= 2 and proxy is not None and proxy <= F(1,20)
    return result


def choose(member, anchors, case, arm, plan, spent, work):
    if spent == 384:
        return None
    if spent == 0 and arm in ('FIXED_DETOUR', 'UNION_DETOUR'):
        return dict(operator='DETOUR_PASS', reason='paid_detour_pilot',
                    scope='TARGET', source_index=None)
    if plan['query_ready']:
        return None
    choice = independent.choose(member, anchors, case, 'LATENT', plan, spent, work)
    return None if choice is None else dict(choice, scope='TARGET', source_index=None)


def advance(state, member, anchors, arm):
    if arm in ('FIXED_SET', 'FIXED_DETOUR'):
        return None
    state['members'].append(deepcopy(member))
    result = outer_union(raw_problem(anchors, state['members']), anchors, state['members'])
    state.update(result)
    return result


def summary(results, frozen, work, historical):
    arms = {}
    for arm in ARMS:
        rows = [row for row in results if row['arm'] == arm]
        late = [row for row in rows if row['index'] >= 15]
        points = [point for row in rows for point in row['history']]
        target = sum(row['spent'] for row in rows)
        observed = [row for row in frozen if row['arm'] == arm]
        arms[arm] = dict(total_samples=sum(historical[arm])+target,
            source_samples=sum(historical[arm]), target_samples=target, source_revisit_samples=0,
            late_samples=sum(row['spent'] for row in late), late_certified=sum(row['certified'] for row in late),
            late_transferred=sum(row['transferred'] and row['transfer_correct'] for row in late),
            late_identified=sum(row['identified'] and row['identity_correct'] for row in late),
            wrong_transfers=sum(row['transferred'] and not row['transfer_correct'] for row in rows),
            late_utility=settled.mean(float(row['terminal']['actual_utility']) for row in late),
            late_post_regret=settled.mean(float(q['regret']) for row in late for q in row['query_post'].values()),
            history_violations=sum(point['violation'] for point in points),
            max_failure=max(float(point['actual'][1]) for point in points),
            coverage=settled.mean(point['coverage'] for point in points),
            member_fallbacks=sum(row['fallback'] for row in rows),
            pilot_samples=sum(row['pilot_samples'] for row in rows),
            retained_targets=len(rows) if arm.startswith('UNION') else 0,
            retained_target_samples=target if arm.startswith('UNION') else 0,
            target_operator_samples={op: sum(sum(row['member'][op].values()) for row in observed)
                                     for op in OPERATORS},
            library_coverage=settled.mean(row['library_coverage'] for row in rows),
            library_lost_masks=sum(not row['library_true_masks'] for row in rows),
            no_feasible=sum(row['library_no_feasible'] for row in rows))
    keys = (
        'fixed_detour_minus_union_detour_samples', 'fixed_set_minus_union_set_samples',
        'fixed_set_minus_fixed_detour_samples', 'union_set_minus_union_detour_samples',
        'learning_gain_difference', 'fixed_set_minus_union_detour_samples',
        'union_detour_minus_fixed_detour_utility', 'union_detour_minus_fixed_set_utility',
        'union_detour_minus_fixed_detour_regret', 'union_detour_minus_fixed_set_regret',
        'union_set_minus_fixed_set_utility', 'union_set_minus_fixed_set_regret',
        'union_detour_minus_fixed_detour_late_certified', 'union_detour_minus_fixed_set_late_certified')
    contrasts = {key: [] for key in keys}
    for life in range(12):
        rows = [row for row in results if row['life'] == life]
        total = {arm: historical[arm][life]+sum(row['spent'] for row in rows if row['arm'] == arm) for arm in ARMS}
        late = {arm: [row for row in rows if row['arm'] == arm and row['index'] >= 15] for arm in ARMS}
        utility = {arm: settled.mean(float(row['terminal']['actual_utility']) for row in late[arm]) for arm in ARMS}
        regret = {arm: settled.mean(float(q['regret']) for row in late[arm] for q in row['query_post'].values()) for arm in ARMS}
        cert = {arm: sum(row['certified'] for row in late[arm]) for arm in ARMS}
        fixed_set, union_set = total['FIXED_SET'], total['UNION_SET']
        fixed_detour, union_detour = total['FIXED_DETOUR'], total['UNION_DETOUR']
        values = {
            'fixed_detour_minus_union_detour_samples': fixed_detour-union_detour,
            'fixed_set_minus_union_set_samples': fixed_set-union_set,
            'fixed_set_minus_fixed_detour_samples': fixed_set-fixed_detour,
            'union_set_minus_union_detour_samples': union_set-union_detour,
            'learning_gain_difference': (fixed_detour-union_detour)-(fixed_set-union_set),
            'fixed_set_minus_union_detour_samples': fixed_set-union_detour,
            'union_detour_minus_fixed_detour_utility': utility['UNION_DETOUR']-utility['FIXED_DETOUR'],
            'union_detour_minus_fixed_set_utility': utility['UNION_DETOUR']-utility['FIXED_SET'],
            'union_detour_minus_fixed_detour_regret': regret['UNION_DETOUR']-regret['FIXED_DETOUR'],
            'union_detour_minus_fixed_set_regret': regret['UNION_DETOUR']-regret['FIXED_SET'],
            'union_set_minus_fixed_set_utility': utility['UNION_SET']-utility['FIXED_SET'],
            'union_set_minus_fixed_set_regret': regret['UNION_SET']-regret['FIXED_SET'],
            'union_detour_minus_fixed_detour_late_certified': cert['UNION_DETOUR']-cert['FIXED_DETOUR'],
            'union_detour_minus_fixed_set_late_certified': cert['UNION_DETOUR']-cert['FIXED_SET']}
        for key in keys:
            contrasts[key].append(values[key])
    randomizer = random.Random(227900)
    samples = {key: [] for key in keys}
    for _ in range(5000):
        indices = [randomizer.randrange(12) for _ in range(12)]
        work['bootstrap_index_draws'] += 12
        for key in keys:
            samples[key].append(settled.mean(contrasts[key][i] for i in indices))
            work['bootstrap_mean_terms'] += 12
    intervals = {key: dict(mean=settled.mean(rows),
                           ci=[sorted(samples[key])[124], sorted(samples[key])[4874]])
                 for key, rows in contrasts.items()}
    tested = arms['UNION_DETOUR']
    points = [point for row in results for point in row['history']]
    conditions = dict(
        RISK=all(point['actual'][1] <= F(1,20) and point['risk_upper'] <= F(1,20) for point in points)
             and all(arm['wrong_transfers'] == 0 and arm['library_coverage'] == 1
                     and arm['library_lost_masks'] == 0 and arm['no_feasible'] == 0 for arm in arms.values()),
        QUALITY=tested['late_certified'] >= 108
                and tested['late_certified'] >= arms['FIXED_DETOUR']['late_certified']
                and tested['late_certified'] >= arms['FIXED_SET']['late_certified']
                and tested['late_utility'] >= 2
                and intervals['union_detour_minus_fixed_detour_utility']['ci'][0] >= -.05
                and intervals['union_detour_minus_fixed_set_utility']['ci'][0] >= -.05,
        APPLICABILITY=tested['late_transferred'] >= 108 and tested['late_post_regret'] <= .05,
        LEARNING_EFFECT=intervals['fixed_detour_minus_union_detour_samples']['mean'] >= 64
                and intervals['fixed_detour_minus_union_detour_samples']['ci'][0] > 0
                and intervals['union_detour_minus_fixed_detour_regret']['ci'][1] <= .01,
        NET_EFFECT=intervals['fixed_set_minus_union_detour_samples']['mean'] >= 64
                and intervals['fixed_set_minus_union_detour_samples']['ci'][0] > 0
                and intervals['union_detour_minus_fixed_set_regret']['ci'][1] <= .01)
    return dict(complete=True, arms=arms, contrasts=contrasts, bootstrap=intervals, conditions=conditions,
                confidence=dict(scope='all_four_arms_per_lifecycle', raw_family=17640, pool_family=27216,
                                raw_delta=.025, pool_delta=.025),
                decision='DETOUR_SUPPLY_LEARNING_SUPPORTED' if all(conditions.values())
                         else 'DETOUR_SUPPLY_LEARNING_NOT_SUPPORTED')


def analyze():
    started = perf_counter()
    work, actual, planning = Counter(), Counter(), Counter()
    union_calls, retained_samples, pilots = Counter(), Counter(), Counter()
    checks = []
    def check(name, value):
        checks.append(dict(name=name, passed=bool(value)))
    def read(name):
        return json.loads((OUTPUT/name).read_text())
    try:
        worlds = [world(life) for life in range(12)]
        check('fixed_public_cases_and_private_worlds', same(read('cases.json'),
              [dict(life=life, cases=worlds[life][0]) for life in range(12)]))
        original = json.loads((ROOT/'reports/fixed_source_acquisition_v219/source_evidence.json').read_text())
        sources = {(row['life'], row['index']): row for row in original if row['arm'] == 'FULL'}
        check('original_full_initial_sources', len(sources) == 36 and all(
            (life, index) in sources for life in range(12) for index in range(3)))
        source_prefixes = {}
        for (life, index), row in sources.items():
            for j, op in enumerate(OPERATORS):
                n = 16*sum(batch['operator'] == op for batch in row['batches'])
                source_prefixes[life, index, op] = settled.generate_prefix(
                    223000+(life*27+index)*3+j, n, worlds[life][1][index][op], SUPPORT[op], work)
        libraries, historical = [], {arm: [] for arm in ARMS}
        for life in range(12):
            anchors, source_samples = [], 0
            source_flags = dict(plans=True, counts=True, choices=True, queries=True)
            for index in range(3):
                member, spent, verified = source_audit.reconstruct_source(
                    sources[life, index], worlds[life][0][index], source_prefixes, work)
                anchors.append(deepcopy(member))
                source_samples += spent
                for key, value in verified.items():
                    source_flags[key] &= value
            libraries.append(dict(life=life, anchors=anchors))
            for arm in ARMS:
                historical[arm].append(source_samples)
            for key, value in source_flags.items():
                check(f'life_{life}_original_paid_source_{key}', value)
        check('actual_historical_source_fees', all(costs == [3456]*12 for costs in historical.values()))
        check('small_frozen_source_evidence_matches_original_prefixes', same(read('source_evidence.json'), libraries))
        check('original_v221_source_evidence_unchanged', same(
            json.loads((ROOT/'reports/persistent_evidence_v221/libraries.json').read_text()), libraries))
        rows = read('records.json')
        lookup = {(r['life'], r['index'], r['arm']): r for r in rows}
        check('complete_unique_four_arm_fresh_targets', len(rows) == len(lookup) == 1152 and all(
            (life, index, arm) in lookup for life in range(12) for index in range(3,27) for arm in ARMS))
        paired, maximum = True, Counter()
        for row in rows:
            life, index = row['life'], row['index']
            seeds = {op: 228000+(life*27+index)*3+j for j, op in enumerate(OPERATORS)}
            paired &= row['seeds'] == seeds
            for op in OPERATORS:
                n = 16*sum(batch['operator'] == op for batch in row['batches'])
                maximum[life, index, op] = max(maximum[life, index, op], n)
        check('four_arm_shared_fresh_target_prefixes', paired)
        prefixes = {key: settled.generate_prefix(
            228000+(key[0]*27+key[1])*3+OPERATORS.index(key[2]), n,
            worlds[key[0]][1][key[1]][key[2]], SUPPORT[key[2]], work)
            for key, n in maximum.items()}
        frozen = []
        for life in range(12):
            cases = worlds[life][0]
            anchors = libraries[life]['anchors']
            states = {arm: prepare(anchors) for arm in ARMS}
            flags = dict(plans=True, choices=True, counts=True, queries=True, state=True)
            for index in range(3,27):
                case = cases[index]
                for arm in ARMS:
                    row, state = lookup[life, index, arm], states[arm]
                    before = deepcopy(state)
                    flags['state'] &= same(row['library_before'], before)
                    member, spent, consumed = empty(), 0, Counter()
                    plan = make_plan(member, anchors, case, state, work)
                    planning[arm] += 1
                    flags['plans'] &= same(row['case'], case) and same(row['initial_plan'], plan)
                    pre = queries(plan)
                    flags['queries'] &= same(row['initial_query'], pre)
                    history = [(0, plan)]
                    for batch in row['batches']:
                        choice = choose(member, anchors, case, arm, plan, spent, work)
                        flags['choices'] &= choice is not None and same(batch['choice'], choice)
                        op = choice['operator']
                        increments = dict.fromkeys(SUPPORT[op], 0)
                        for cat in prefixes[life, index, op][consumed[op]:consumed[op]+16]:
                            increments[cat] += 1
                        flags['counts'] &= batch['operator'] == op and batch['scope'] == 'TARGET'
                        flags['counts'] &= batch['source_index'] is None and batch['draw_start'] == consumed[op]
                        flags['counts'] &= batch['increments'] == increments and sum(increments.values()) == 16
                        for cat, value in increments.items():
                            member[op][cat] += value
                        consumed[op] += 16
                        spent += 16
                        actual[arm] += 16
                        pilots[arm] += 16*int(choice['reason'] == 'paid_detour_pilot')
                        flags['counts'] &= batch['draw_end'] == consumed[op] and batch['spent'] == spent
                        flags['counts'] &= batch['member_spent'] == spent and batch['source_spent'] == 0
                        plan = make_plan(member, anchors, case, state, work)
                        planning[arm] += 1
                        flags['plans'] &= same(batch['plan'], plan)
                        history.append((spent, plan))
                    flags['choices'] &= choose(member, anchors, case, arm, plan, spent, work) is None
                    flags['choices'] &= 0 <= spent <= 384
                    fallback = len(plan['candidates']) != 1 and not plan['query_ready']
                    if fallback:
                        plan = make_plan(member, anchors, case, state, work, force_member=True)
                        planning[arm] += 1
                        history.append((spent, plan))
                    certified = plan['utility_lower'] >= 2
                    identified = len(plan['candidates']) == 1 and certified
                    transferred = certified and plan['mode'] == 'library' and (identified or plan['query_ready'])
                    stop = ('member_budget' if fallback else 'query_set' if transferred and not identified else
                            'identified' if identified else 'member_certified' if certified else 'budget')
                    flags['choices'] &= row['stop'] == stop and row['fallback'] == fallback
                    flags['plans'] &= row['spent'] == spent and row['member_spent'] == spent and row['source_spent'] == 0
                    flags['plans'] &= row['certified'] == certified and row['identified'] == identified
                    flags['plans'] &= row['transferred'] == transferred and same(row['member'], member)
                    flags['plans'] &= same(row['terminal_plan'], plan)
                    post = queries(plan)
                    flags['queries'] &= same(row['terminal_query'], post)
                    flags['state'] &= state == before
                    event = advance(state, member, anchors, arm)
                    flags['state'] &= same(row['advance'], event) and same(row['library_after'], state)
                    if arm.startswith('UNION'):
                        union_calls[arm] += 1
                        retained_samples[arm] += spent
                        flags['state'] &= len(state['members']) == index-2
                    else:
                        flags['state'] &= state == before and event is None
                    frozen.append(dict(life=life, index=index, arm=arm, spent=spent,
                        certified=certified, identified=identified, transferred=transferred,
                        fallback=fallback, plan=plan, history=history, pre=pre, post=post,
                        after=deepcopy(state), member=deepcopy(member)))
            for name, flag in flags.items():
                check(f'life_{life}_independent_{name}', flag)
        # Identity and kernels score only already-reconstructed decisions and libraries.
        results = []
        for row in frozen:
            life, index, arm = row['life'], row['index'], row['arm']
            cases, laws, identities = worlds[life]
            plan, state = row['plan'], row['after']
            history = [score(p, laws[index], cases[index], spent, work) for spent, p in row['history']]
            library_coverage = union_math.coverage(state['bounds'], laws)
            true_masks = all(identities[3+j] in mask for j, mask in enumerate(state['masks']))
            results.append(dict(life=life, index=index, arm=arm, spent=row['spent'],
                source_spent=0, member_spent=row['spent'], certified=row['certified'],
                identified=row['identified'], identity_correct=row['identified'] and plan['candidates'][0] == identities[index],
                transferred=row['transferred'], transfer_correct=row['transferred'] and identities[index] in plan['candidates'],
                fallback=row['fallback'], history=history, terminal=history[-1],
                query_pre=query_score(row['pre'], laws[index], cases[index]),
                query_post=query_score(row['post'], laws[index], cases[index]),
                library_coverage=library_coverage, library_true_masks=true_masks,
                library_no_feasible=state['no_feasible'], pilot_samples=16 if arm.endswith('DETOUR') else 0))
        check('delayed_true_history_queries_and_library_coverage', same(read('results.json'), results))
        stats = Counter()
        expected = summary(results, frozen, stats, historical)
        check('paired_factorial_statistics_and_frozen_gates', same(read('summary.json'), expected))
        run = read('run.json')
        check('historical_source_fee_separate_from_fresh_sampling', same(run['historical_source_costs'], historical))
        check('actual_sample_reset_draw_and_planning_costs', sum(actual.values()) <= 442368 and all(
            run['arm_costs'][arm].get(key, 0) == actual[arm] for arm in ARMS
            for key in ('controlled_samples', 'controlled_resets', 'environment_random_draws'))
            and all(run['arm_costs'][arm]['planning_calls'] == planning[arm] for arm in ARMS))
        check('paid_detour_pilots_and_complete_union_retention', all(
            pilots[arm] == (4608 if arm.endswith('DETOUR') else 0)
            and run['arm_costs'][arm].get('union_retained_targets',0) == union_calls[arm]
            and run['arm_costs'][arm].get('union_retained_samples',0) == retained_samples[arm]
            and run['arm_costs'][arm].get('detour_supply_preparations',0) == 12
            for arm in ARMS))
        check('actual_factorial_bootstrap_costs', run['bootstrap_costs'] == dict(stats))
        check('oracle_scoring_after_all_decisions', run['phases'] == [
            'protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete'])
        complete = True
    except Exception as error:
        check('reconstruction', False)
        checks[-1]['error'] = f'{type(error).__name__}: {error}'
        complete = False
    output = dict(valid=complete and all(c['passed'] for c in checks), complete=complete,
                  checks=checks, costs=dict(work), seconds=perf_counter()-started)
    (OUTPUT/'analysis.json').write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps(dict(valid=output['valid'], complete=complete, checks=len(checks))))
    return output


if __name__ == '__main__':
    raise SystemExit(0 if analyze()['valid'] else 1)
