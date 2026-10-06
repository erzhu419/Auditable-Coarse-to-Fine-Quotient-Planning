"""Independent conditional mechanisms, chronological counts and own-policy audit.

No V205 producer mathematics is imported. Dirichlet condition selection,
fixed source conditions, pilot allocation, raw confidence boxes and complete
policy scoring are reconstructed. Only actual integer batches update models.
"""
import argparse
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
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science import structured_route_task_v201 as route

OUTPUT = ROOT / 'reports/conditioned_mechanisms_v205'
OPERATORS = ('SHORT_PASS', 'DETOUR_PASS', 'RECOVERY_RETRY')
SUPPORT = {'SHORT_PASS': ('DELIVERY', 'LOST'), 'DETOUR_PASS': ('DELIVERY', 'LOST', 'RECOVERY'),
           'RECOVERY_RETRY': ('DELIVERY', 'LOST')}
FIELDS = ('operating', 'retry_cost', 'weather')
ARMS = ('GUIDED', 'FIXED', 'COLD', 'UNIFORM')
GRID = 2 ** 40
BETA = math.log(2 * 728 / .05)
DELTA = Fraction(1, 20)
ZERO = (Fraction(0),) * 3


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [exact_json(item) for item in value]
    return value


def projection(case, fields=FIELDS):
    return tuple(case[field] for field in fields)


def kl(x, p):
    if x == 0:
        return math.inf if p == 1 else -math.log1p(-p)
    if x == 1:
        return math.inf if p == 0 else -math.log(p)
    if p in (0, 1):
        return math.inf
    return x * math.log(x / p) + (1 - x) * math.log((1 - x) / (1 - p))


def interval(k, n, work):
    work['interval_calls'] += 1
    if not n:
        return Fraction(0), Fraction(1)
    x = float(k / n)
    if k:
        lo, hi = 0., x
        for _ in range(64):
            midpoint = (lo + hi) / 2
            if float(n) * kl(x, midpoint) <= BETA:
                hi = midpoint
            else:
                lo = midpoint
            work['kl_calls'] += 1
        lower = Fraction(math.floor(lo * GRID), GRID)
    else:
        lower = Fraction(0)
    if k < n:
        lo, hi = x, 1.
        for _ in range(64):
            midpoint = (lo + hi) / 2
            if float(n) * kl(x, midpoint) <= BETA:
                lo = midpoint
            else:
                hi = midpoint
            work['kl_calls'] += 1
        upper = Fraction(math.ceil(hi * GRID), GRID)
    else:
        upper = Fraction(1)
    return lower, upper


def member_counts(model, case, operator, fields=FIELDS, work=None):
    work = Counter() if work is None else work
    counts = dict.fromkeys(SUPPORT[operator], 0)
    for record in model['tables'][operator]:
        work['model_context_scans'] += 1
        if projection(record['context'], fields) == projection(case, fields):
            for category in counts:
                counts[category] += record['counts'][category]
                work['model_count_additions'] += 1
    return counts


def laws(model, case, work):
    result = {}
    for operator in OPERATORS:
        counts = member_counts(model, case, operator, model['selected_fields'][operator], work)
        n = sum(counts.values()); size = len(counts)
        result[operator] = {category: Fraction(2 * count + 1, 2 * n + size) for category, count in counts.items()}
    return result


def boxes(counts, work):
    result = {}
    for operator in OPERATORS:
        n = sum(counts[operator].values())
        result[operator] = dict(n=n, counts=dict(counts[operator]),
            bounds={category: interval(count, n, work) for category, count in counts[operator].items()})
    return result


def risk_bounds(envelopes):
    short, detour, retry = (envelopes[operator]['bounds'] for operator in OPERATORS)
    s = min(short['LOST'][1], 1 - short['DELIVERY'][0])
    q = min(retry['LOST'][1], 1 - retry['DELIVERY'][0])
    f = min(detour['LOST'][1], 1 - detour['DELIVERY'][0] - detour['RECOVERY'][0])
    r = min(detour['RECOVERY'][1], 1 - detour['DELIVERY'][0] - f)
    return dict(WAIT=Fraction(0), SHORT=s, DETOUR_RETURN=f, DETOUR_RETRY=f + r * q)


def goal_bounds(envelopes, case):
    short, detour, retry = (envelopes[operator]['bounds'] for operator in OPERATORS)
    short_cost, detour_cost = route.OPERATING[case['operating']]
    d_short = max(short['DELIVERY'][0], 1 - short['LOST'][1])
    t = max(retry['DELIVERY'][0], 1 - retry['LOST'][1])
    d = max(detour['DELIVERY'][0], 1 - detour['LOST'][1] - detour['RECOVERY'][1])
    a = 4 * t - Fraction(case['retry_cost'])
    r = (min(detour['RECOVERY'][1], 1 - d - detour['LOST'][0]) if a < 0 else
         max(detour['RECOVERY'][0], 1 - d - detour['LOST'][1]))
    return dict(WAIT=Fraction(0), SHORT=-short_cost + 4 * d_short,
                DETOUR_RETURN=-detour_cost + 4 * d, DETOUR_RETRY=-detour_cost + 4 * d + a * r)


def vectors(case, probabilities):
    short_cost, detour_cost = route.OPERATING[case['operating']]
    short, detour, retry = (probabilities[operator] for operator in OPERATORS)
    r = detour['RECOVERY']
    return dict(WAIT=ZERO, SHORT=(-short_cost, short['LOST'], short['DELIVERY']),
        DETOUR_RETURN=(-detour_cost, detour['LOST'], detour['DELIVERY']),
        DETOUR_RETRY=(-detour_cost - r * Fraction(case['retry_cost']),
                      detour['LOST'] + r * retry['LOST'], detour['DELIVERY'] + r * retry['DELIVERY']))


def goal(vector):
    return vector[0] + 4 * vector[2]


def joint(mix, pure, work):
    work['mixture_components'] += 3 * len(mix)
    return tuple(sum((Fraction(weight) * pure[name][i] for name, weight in mix), Fraction(0)) for i in range(3))


def optimize(pure, upper, lower, work):
    candidates = []
    def add(mix):
        predicted = joint(mix, pure, work)
        candidates.append(dict(mix=mix, predicted=predicted, predicted_utility=goal(predicted),
            risk_upper=sum((weight * upper[name] for name, weight in mix), Fraction(0)),
            utility_lower=sum((weight * lower[name] for name, weight in mix), Fraction(0))))
    names = sorted(pure)
    for name in names:
        work['optimizer_pure_checks'] += 1
        if upper[name] <= DELTA:
            add([(name, Fraction(1))])
    for left, right in combinations(names, 2):
        work['optimizer_pair_checks'] += 1
        a, b = upper[left], upper[right]
        if min(a, b) < DELTA < max(a, b):
            weight = (DELTA - b) / (a - b)
            add([(left, weight), (right, 1 - weight)])
    return min(candidates, key=lambda row: (-row['utility_lower'], row['mix']))


def make_plan(model, case, work):
    counts = {operator: member_counts(model, case, operator, work=work) for operator in OPERATORS}
    envelope = boxes(counts, work); upper = risk_bounds(envelope); lower = goal_bounds(envelope, case)
    pure = vectors(case, laws(model, case, work))
    return dict(optimize(pure, upper, lower, work), envelopes=envelope, risks=upper, goals_lower=lower, pure_vectors=pure)


def cold_policy(model, case, current, work):
    pure = current['pure_vectors']
    scores = {name: goal(vector) / vector[1] for name, vector in pure.items() if name != 'WAIT'}
    policy = min(scores, key=lambda name: (-scores[name], name))
    occupancy = dict.fromkeys(OPERATORS, Fraction(0))
    if policy == 'SHORT':
        occupancy['SHORT_PASS'] = 1
    else:
        occupancy['DETOUR_PASS'] = 1
        if policy == 'DETOUR_RETRY':
            occupancy['RECOVERY_RETRY'] = laws(model, case, work)['DETOUR_PASS']['RECOVERY']
    operator = min(OPERATORS, key=lambda name: (-occupancy[name], OPERATORS.index(name)))
    return dict(operator=operator, forecast_scores=None, policy=policy, policy_scores=scores)


def update(model, case, operator, increments, work):
    table = model['tables'][operator]
    record = next((row for row in table if projection(row['context']) == projection(case)), None)
    if record is None:
        record = dict(context=dict(case), counts=dict.fromkeys(SUPPORT[operator], 0)); table.append(record)
        table.sort(key=lambda row: projection(row['context']))
    for category in SUPPORT[operator]:
        record['counts'][category] += increments[category]
        work['real_count_updates'] += 1
    model['observations_used'] += sum(increments.values())


def stop_reason(plan, spent):
    if plan['utility_lower'] >= 2:
        return 'certified'
    return 'budget' if spent == 384 else None


def generate_prefix(seed, count, probabilities, alphabet, work):
    rng = random.Random(seed); outcomes = []
    for _ in range(count):
        draw = rng.random(); cumulative = Fraction(0)
        for category in alphabet:
            cumulative += probabilities[category]
            if draw < float(cumulative):
                outcomes.append(category); break
        work['regenerated_consumed_samples'] += 1
    return outcomes


def query_decisions(model, case, work):
    pure = vectors(case, laws(model, case, work)); result = {}
    for query in route.QUERIES:
        recovery = min(('RETURN', 'RETRY'), key=lambda action: (
            -route.utility(pure['DETOUR_' + action], query, work), action))
        options = {'DETOUR': pure['DETOUR_' + recovery], 'SHORT': pure['SHORT'], 'WAIT': pure['WAIT']}
        root = min(options, key=lambda action: (-route.utility(options[action], query, work), action))
        name = 'DETOUR_' + recovery if root == 'DETOUR' else root
        result[query] = dict(root_action=root, recovery_action=recovery, pure_policy=name, predicted=options[root])
    return result


def score(plan, probabilities, case, spent, work):
    pure = vectors(case, probabilities); actual = joint(plan['mix'], pure, work)
    excess = max(Fraction(0), actual[1] - DELTA)
    wait = sum((weight for name, weight in plan['mix'] if name == 'WAIT'), Fraction(0))
    coverage = all(plan['envelopes'][operator]['bounds'][category][0] <= p <=
                   plan['envelopes'][operator]['bounds'][category][1]
                   for operator, entries in probabilities.items() for category, p in entries.items())
    return dict(spent=spent, actual_fractions=exact_json(actual), actual=[float(x) for x in actual],
        actual_utility_fraction=str(goal(actual)), actual_utility=float(goal(actual)),
        risk_upper=str(plan['risk_upper']), utility_lower=str(plan['utility_lower']),
        violation=excess > 0, excess_fraction=str(excess), excess=float(excess), coverage=coverage,
        wait_mass_fraction=str(wait), wait_mass=float(wait))


def equal_numbers(saved, expected):
    if isinstance(expected, dict):
        return all(key in saved and equal_numbers(saved[key], value) for key, value in expected.items())
    if isinstance(expected, (tuple, list)):
        return len(saved) == len(expected) and all(equal_numbers(a, b) for a, b in zip(saved, expected))
    if isinstance(expected, float):
        return abs(saved - expected) <= 1e-12 * (1 + abs(expected))
    return saved == expected


def plan_matches(saved, expected):
    return all(saved[key] == exact_json(value) for key, value in expected.items())


def mean(values):
    values = list(values)
    return sum(values) / len(values)


WEATHER = {
    'normal': tuple(map(Fraction, ('9/10', '17/20', '1/100', '7/50', '1/4'))),
    'wet': tuple(map(Fraction, ('99/100', '7/10', '3/25', '9/50', '9/10'))),
    'blocked': tuple(map(Fraction, ('13/20', '4/5', '1/100', '19/100', '2/5'))),
}
SUBSETS = tuple(fields for size in range(4) for fields in combinations(FIELDS, size))
SCORE_EPS = 1e-9


def roster():
    return [dict(id=f"v205_{weather}_{operating}_r{retry.replace('/', '_')}",
                 weather=weather, operating=operating, retry_cost=retry)
            for weather in WEATHER for operating in ('low', 'high') for retry in ('17/20', '19/20')]


def true_laws(case):
    s, d, f, r, t = WEATHER[case['weather']]
    return {'SHORT_PASS': dict(DELIVERY=s, LOST=1-s),
            'DETOUR_PASS': dict(DELIVERY=d, LOST=f, RECOVERY=r),
            'RECOVERY_RETRY': dict(DELIVERY=t, LOST=1-t)}


def field_score(table, operator, fields, work):
    groups = {}
    for row in table:
        key = projection(row['context'], fields)
        group = groups.setdefault(key, dict.fromkeys(SUPPORT[operator], 0))
        for category in group:
            group[category] += row['counts'][category]
            work['field_score_count_additions'] += 1
    k = len(SUPPORT[operator]); result = 0.
    for key in sorted(groups):
        counts = groups[key]; n = sum(counts.values())
        base = math.lgamma(k*.5) - math.lgamma(n+k*.5)
        terms = [math.lgamma(counts[category]+.5) - math.lgamma(.5) for category in SUPPORT[operator]]
        result += base + sum(terms)
        work['field_score_lgamma_calls'] += 2+2*k
    work['field_score_candidates'] += 1
    return result


def fit_tables(tables, arm, work, fixed_fields=None):
    """Select conditions from source counts, or score one frozen subset."""
    selected, scores = {}, {}
    for operator in OPERATORS:
        candidates = ((tuple(fixed_fields[operator]),) if fixed_fields is not None else
                      (FIELDS,) if arm == 'FULL_CONTEXT' else SUBSETS)
        best = None; records = []
        for fields in candidates:
            value = field_score(tables[operator], operator, fields, work)
            records.append(dict(fields=list(fields), score=value))
            key = (len(fields), fields)
            if best is None or value > best[0]+SCORE_EPS or (abs(value-best[0]) <= SCORE_EPS and key < best[1]):
                best = value, key, fields
        selected[operator] = list(best[2]); scores[operator] = records
    work['reconstructed_model_fits'] += 1
    return dict(schema='acfqp.continual_route_kernels.v202.model', arm=arm,
                selected_fields=selected, scores=scores, tables=deepcopy(tables),
                observations_used=sum(sum(row['counts'].values()) for table in tables.values() for row in table))


def source_history(life, cases, work):
    """Regenerate each source draw once, using the continuous lifecycle RNG."""
    rng = random.Random(205000+life); batches = []; offset = 0
    for name, chosen in (('SOURCE', [case for case in cases if case['weather'] == 'normal']),
                         ('REVISION', [case for case in cases if case['weather'] != 'normal' and case['operating'] == 'high'])):
        records = []
        for case in chosen:
            probabilities = true_laws(case)
            for operator in OPERATORS:
                counts = dict.fromkeys(SUPPORT[operator], 0)
                for _ in range(128):
                    value = rng.random(); cumulative = Fraction(0)
                    for category in SUPPORT[operator]:
                        cumulative += probabilities[operator][category]
                        if value < float(cumulative):
                            counts[category] += 1; break
                    work['regenerated_source_samples'] += 1
                records.append(dict(context=dict(case), operator=operator, counts=counts, n=128,
                                    phase=name, draw_start=offset, draw_end=offset+128))
                offset += 128
        batches.append(dict(name=name, records=records))
    return dict(life=life, seed=205000+life, batches=batches)


def tables_from_batches(batches, work):
    tables = {operator: {} for operator in OPERATORS}
    for batch in batches:
        for row in batch['records']:
            operator = row['operator']; key = projection(row['context'])
            record = tables[operator].setdefault(key, dict(context=dict(row['context']),
                                                           counts=dict.fromkeys(SUPPORT[operator], 0)))
            for category in SUPPORT[operator]:
                record['counts'][category] += row['counts'][category]
                work['source_table_count_additions'] += 1
    return {operator: [table[key] for key in sorted(table)] for operator, table in tables.items()}


def choose(model, case, current, work):
    observed = {operator: sum(member_counts(model, case, operator, model['selected_fields'][operator], work).values())
                for operator in OPERATORS[:2]}
    for operator in OPERATORS[:2]:
        if observed[operator] == 0:
            return dict(operator=operator, pilot=True, policy=None, policy_scores=None, projection_counts=observed)
    return dict(cold_policy(model, case, current, work), pilot=False, projection_counts=observed)


def true_optimum(pure, work):
    result = optimize(pure, {name: vector[1] for name, vector in pure.items()},
                      {name: goal(vector) for name, vector in pure.items()}, work)
    return dict(mix=result['mix'], vector=list(result['predicted']), utility=result['predicted_utility'])


def qualify(cases, work):
    """Analytic declaration only; H2 selects WAIT before either gate is paid."""
    records = []; flags = dict(ROOT_SWITCH=True, CONTINUATION=True, DEPTH=True)
    totals = dict(optimal=Fraction(0), SHORT=Fraction(0), DETOUR=Fraction(0))
    for case in cases:
        pure = vectors(case, true_laws(case)); optimum = true_optimum(pure, work); queries = {}
        for query in route.QUERIES:
            recovery = min(('RETURN', 'RETRY'), key=lambda action: (-route.utility(pure['DETOUR_'+action], query, work), action))
            options = dict(DETOUR=pure['DETOUR_'+recovery], SHORT=pure['SHORT'], WAIT=pure['WAIT'])
            root = min(options, key=lambda action: (-route.utility(options[action], query, work), action))
            value = route.utility(options[root], query, work)
            queries[query] = dict(vector=list(options[root]), utility=value, root_action=root,
                recovery_action=recovery, recovery_reached=root == 'DETOUR',
                receding_h2_vector=list(ZERO), receding_h2_utility=Fraction(0), gap=value)
            if query in ('goal', 'risk'):
                flags['DEPTH'] &= value >= 2
        if case['weather'] == 'wet':
            flags['ROOT_SWITCH'] &= optimum['mix'] == [('SHORT', Fraction(1))]
        if case['weather'] == 'blocked':
            flags['ROOT_SWITCH'] &= all(name.startswith('DETOUR_') for name, _ in optimum['mix'])
            flags['CONTINUATION'] &= all(queries[q]['root_action'] == 'DETOUR' and queries[q]['recovery_reached']
                                          for q in ('goal', 'risk'))
            flags['CONTINUATION'] &= queries['goal']['recovery_action'] == 'RETRY' and queries['risk']['recovery_action'] == 'RETURN'
        constants = {name: true_optimum({policy: pure[policy] for policy in policies}, work)
            for name, policies in (('SHORT', ('WAIT', 'SHORT')), ('DETOUR', ('WAIT', 'DETOUR_RETURN', 'DETOUR_RETRY')))}
        if case['weather'] != 'normal' and case['operating'] == 'low':
            totals['optimal'] += optimum['utility']
            for family in constants:
                totals[family] += constants[family]['utility']
        records.append(dict(context_id=case['id'], queries=queries, pure_vectors=pure,
                            hard_optimum=optimum, constant_families=constants))
    means = {name: value/4 for name, value in totals.items()}; gap = means['optimal']-max(means['SHORT'], means['DETOUR'])
    flags['CONSTANT_GAP'] = gap >= Fraction(1, 2)
    return dict(qualified=all(flags.values()), conditions=flags, records=records,
                constant_comparison=dict(means=means, gap=gap, contexts=4))


def bootstrap(contrasts, work):
    rng = random.Random(205900); resamples = {name: [] for name in contrasts}
    for _ in range(5000):
        indices = [rng.randrange(12) for _ in range(12)]
        for name, values in contrasts.items():
            resamples[name].append(sum(values[index] for index in indices)/12)
        work['bootstrap_index_draws'] += 12
        work['bootstrap_mean_terms'] += 12*len(contrasts)
    work['bootstrap_resamples'] += 5000
    return {name: dict(mean=mean(contrasts[name]), ci=[sorted(values)[124], sorted(values)[4874]])
            for name, values in resamples.items()}


def summarize(targets, zero, old, sources, qualification, work):
    arms, zero_metrics, retention = {}, {}, {}
    for arm in ARMS:
        rows = [row for row in targets if row['arm'] == arm]; history = [point for row in rows for point in row['history']]
        total = sum(row['terminal']['spent'] for row in rows)
        arms[arm] = dict(restored=sum(row['terminal']['certified'] for row in rows), total_samples=total,
            mean_samples=mean(row['terminal']['spent'] for row in rows), true_utility=mean(row['terminal']['actual_utility'] for row in rows),
            history_violations=sum(point['violation'] for point in history), terminal_violations=sum(row['terminal']['violation'] for row in rows),
            max_failure=max(point['actual'][1] for point in history), max_excess=max(point['excess'] for point in history),
            wait_mass=mean(row['terminal']['wait_mass'] for row in rows), coverage=mean(point['coverage'] for point in history),
            pilot_fraction=sum(row['pilot_batches'] for row in rows)/sum(row['total_batches'] for row in rows),
            first_operator_counts={operator: sum(row['first_operator'] == operator for row in rows) for operator in OPERATORS},
            source_samples=36864, source_plus_target_samples=36864+total)
        queries = [query for row in zero if row['arm'] == arm for query in row['queries'].values()]
        zero_metrics[arm] = dict(utility=mean(row['utility'] for row in queries), regret=mean(row['regret'] for row in queries),
                                **{name: mean(row['abs_prediction_error'][i] for row in queries) for i, name in enumerate(('R', 'F', 'S'))})
        before = mean(query['regret'] for row in old if row['arm'] == arm and row['stage'] == 'SOURCE' for query in row['queries'].values())
        after = mean(query['regret'] for row in old if row['arm'] == arm and row['stage'] == 'FINAL' for query in row['queries'].values())
        retention[arm] = dict(SOURCE_regret=before, FINAL_regret=after, regret_change=after-before)
    revision = dict(SOURCE_no_weather=all('weather' not in row['SOURCE']['REVISED']['selected_fields'][operator]
                                         for row in sources for operator in OPERATORS[:2]),
                    SHORT_weather_lifecycles=sum(row['REVISION']['REVISED']['selected_fields']['SHORT_PASS'] == ['weather'] for row in sources),
                    DETOUR_weather_lifecycles=sum(row['REVISION']['REVISED']['selected_fields']['DETOUR_PASS'] == ['weather'] for row in sources),
                    GUIDED_first_critical_operator=sum(row['first_operator'] == ('SHORT_PASS' if 'wet' in row['context_id'] else 'DETOUR_PASS')
                                                       for row in targets if row['arm'] == 'GUIDED'))
    contrasts = {name: [] for name in ('cold_minus_guided_samples', 'uniform_minus_guided_samples',
        'fixed_minus_guided_samples', 'guided_minus_cold_utility', 'zero_guided_minus_cold_utility', 'zero_guided_minus_fixed_utility')}
    for life in range(12):
        cost = {arm: mean(row['terminal']['spent'] for row in targets if row['arm'] == arm and row['life'] == life) for arm in ARMS}
        terminal = {arm: mean(row['terminal']['actual_utility'] for row in targets if row['arm'] == arm and row['life'] == life) for arm in ARMS}
        initial = {arm: mean(query['utility'] for row in zero if row['arm'] == arm and row['life'] == life for query in row['queries'].values()) for arm in ARMS}
        for arm in ('COLD', 'UNIFORM', 'FIXED'):
            contrasts[arm.lower()+'_minus_guided_samples'].append(cost[arm]-cost['GUIDED'])
        contrasts['guided_minus_cold_utility'].append(terminal['GUIDED']-terminal['COLD'])
        for arm in ('COLD', 'FIXED'):
            contrasts['zero_guided_minus_'+arm.lower()+'_utility'].append(initial['GUIDED']-initial[arm])
    intervals = bootstrap(contrasts, work)
    hard = [point for row in targets if row['arm'] == 'GUIDED' for point in row['history']]
    conditions = dict(TASK=qualification['qualified'],
        CONDITION=revision['SOURCE_no_weather'] and revision['SHORT_weather_lifecycles'] >= 10
            and revision['DETOUR_weather_lifecycles'] >= 10 and revision['GUIDED_first_critical_operator'] >= 44,
        TRANSFER=zero_metrics['GUIDED']['regret'] <= .05 and all(intervals[key]['mean'] >= .1 and intervals[key]['ci'][0] > 0
            for key in ('zero_guided_minus_cold_utility', 'zero_guided_minus_fixed_utility')),
        ACQUISITION=intervals['cold_minus_guided_samples']['mean'] >= 16 and intervals['cold_minus_guided_samples']['ci'][0] > 0
            and arms['GUIDED']['restored'] >= 36 and arms['GUIDED']['restored'] >= arms['COLD']['restored'] and arms['GUIDED']['true_utility'] >= 2,
        RISK_RETENTION=all(Fraction(point['risk_upper']) <= DELTA and not point['violation'] for point in hard)
            and retention['GUIDED']['regret_change'] <= .01)
    return dict(schema='acfqp.conditioned_mechanisms.v205.summary', complete=True, arms=arms, zero_metrics=zero_metrics,
        retention=retention, condition_revision=revision, paired_lifecycle_contrasts=contrasts, bootstrap=intervals,
        conditions=conditions, decision='CONDITIONED_MECHANISMS_SUPPORTED' if all(conditions.values()) else 'CONDITIONED_MECHANISMS_NOT_SUPPORTED',
        cold_start_reference=dict(arm='COLD', source_samples=0, target_samples=arms['COLD']['total_samples']))


def decision(model, life, arm, case, work, stage=None):
    row = dict(life=life, context_id=case['id'], arm=arm, queries=query_decisions(model, case, work))
    if stage is not None:
        row['stage'] = stage
    return row


def decision_score(saved, case, probabilities, work):
    pure = vectors(case, probabilities); queries = {}
    for query, chosen in saved['queries'].items():
        actual = pure[chosen['pure_policy']]; predicted = chosen['predicted']
        utility = route.utility(actual, query, work)
        oracle = max(route.utility(vector, query, work) for vector in pure.values())
        queries[query] = dict(actual_fractions=exact_json(actual), actual=[float(x) for x in actual],
            utility_fraction=str(utility), utility=float(utility), oracle_utility_fraction=str(oracle), oracle_utility=float(oracle),
            regret_fraction=str(oracle-utility), regret=float(oracle-utility),
            abs_prediction_error=[float(abs(a-b)) for a, b in zip(actual, predicted)])
    row = dict(life=saved['life'], context_id=case['id'], arm=saved['arm'], queries=queries)
    if 'stage' in saved:
        row['stage'] = saved['stage']
    return row


def consumed_prefixes(histories, targets, work):
    maximum = Counter()
    for row in histories:
        if len(row['batches']) > 24:
            raise ValueError('target history exceeds frozen 24-batch budget')
        consumed = Counter(batch['operator'] for batch in row['batches'])
        for operator in OPERATORS:
            key = row['life'], row['target_index'], operator
            maximum[key] = max(maximum[key], 16*consumed[operator])
    result = {}
    for (life, index, operator), n in maximum.items():
        seed = 206000+(life*4+index)*3+OPERATORS.index(operator)
        result[life, index, operator] = generate_prefix(seed, n, true_laws(targets[index])[operator], SUPPORT[operator], work)
    return result


def model_matches(saved, expected):
    return equal_numbers(saved, {key: expected[key] for key in
        ('schema', 'arm', 'selected_fields', 'scores', 'tables', 'observations_used')})


def analyze(directory=OUTPUT):
    begun = perf_counter(); work = Counter(); checks = []; complete = False
    def check(name, flag):
        checks.append(dict(name=name, passed=bool(flag)))
    try:
        def read(name):
            raw = (directory/name).read_bytes()
            work['input_files_read'] += 1; work['input_bytes_read'] += len(raw)
            return json.loads(raw)
        cases, qualification_saved, run = (read(name) for name in ('cases.json', 'qualification.json', 'run.json'))
        expected_qualification = qualify(roster(), work)
        check('fixed_task_roster_and_analytic_qualification', cases == roster() and equal_numbers(qualification_saved, exact_json(expected_qualification)))
        source_manifest = read('source_manifest.json')
        check('frozen_source_roster', len(source_manifest) == 13)
        if not expected_qualification['qualified']:
            summary = read('summary.json')
            check('unqualified_task_stops_before_samples_or_fits', run['costs']['source_acquisition'].get('controlled_samples', 0) == 0
                  and run['costs']['target_acquisition'].get('controlled_samples', 0) == 0 and not run['source_fits'] and summary['conditions']['TASK'] is False
                  and summary['decision'] == 'CONDITIONED_MECHANISMS_NOT_SUPPORTED')
            complete = True
        else:
            source_batches = read('source_batches.json')['lifecycles']; source_models = read('source_models.json')['lifecycles']
            histories = read('histories.json')['records']; models_saved = read('models.json')['lifecycles']
            zero_saved, old_saved = (read(name)['records'] for name in ('zero_decisions.json', 'old_decisions.json'))
            targets_saved, zero_results_saved, old_results_saved = (read(name)['records'] for name in
                ('target_results.json', 'zero_results.json', 'old_results.json'))
            references_saved = read('reference.json')['records']; summary_saved = read('summary.json'); accounting = read('source_accounting.json')
            targets = [case for case in cases if case['weather'] != 'normal' and case['operating'] == 'low']
            normal = [case for case in cases if case['weather'] == 'normal']; case_map = {case['id']: case for case in cases}
            source_map = {row['life']: row for row in source_models}; batch_map = {row['life']: row for row in source_batches}
            final_map = {row['life']: row['models'] for row in models_saved}
            history_map = {(row['life'], row['target_index'], row['arm']): row for row in histories}
            target_map = {(row['life'], row['target_index'], row['arm']): row for row in targets_saved}
            zero_map = {(row['life'], row['context_id'], row['arm']): row for row in zero_saved}
            zero_result_map = {(row['life'], row['context_id'], row['arm']): row for row in zero_results_saved}
            old_map = {(row['life'], row['context_id'], row['arm'], row['stage']): row for row in old_saved}
            old_result_map = {(row['life'], row['context_id'], row['arm'], row['stage']): row for row in old_results_saved}
            check('complete_chronological_four_arm_rosters', len(source_map) == len(source_models) == len(batch_map) == len(source_batches) == 12
                and len(final_map) == len(models_saved) == 12 and len(history_map) == len(histories) == len(target_map) == len(targets_saved) == 192
                and len(zero_map) == len(zero_saved) == len(zero_result_map) == len(zero_results_saved) == 192
                and len(old_map) == len(old_saved) == len(old_result_map) == len(old_results_saved) == 384)
            prefixes = consumed_prefixes(histories, targets, work)
            expected_histories, expected_zero, expected_old, expected_sources = [], [], [], []
            actual_samples = Counter(); pilot_choices = Counter()
            for life in range(12):
                regenerated = source_history(life, cases, work)
                check(f'life_{life}_continuous_source_and_revision_observations', batch_map[life] == regenerated)
                source_tables = tables_from_batches(regenerated['batches'][:1], work)
                full_tables = tables_from_batches(regenerated['batches'], work)
                source = {arm: fit_tables(source_tables, arm, work) for arm in ('REVISED', 'FULL_CONTEXT')}
                revision = {arm: fit_tables(full_tables, arm, work) for arm in ('REVISED', 'FULL_CONTEXT')}
                revision['FIXED'] = fit_tables(full_tables, 'FIXED', work, source['REVISED']['selected_fields'])
                expected_sources.append(dict(life=life, SOURCE=source, REVISION=revision))
                check(f'life_{life}_five_source_only_condition_models',
                    all(model_matches(source_map[life][phase][arm], model) for phase, group in (('SOURCE', source), ('REVISION', revision))
                        for arm, model in group.items()))
                models = {arm: deepcopy(revision['FIXED' if arm == 'FIXED' else 'FULL_CONTEXT' if arm == 'COLD' else 'REVISED']) for arm in ARMS}
                zero_ok = old_ok = True
                for arm in ARMS:
                    initial = source['FULL_CONTEXT' if arm == 'COLD' else 'REVISED']
                    for case in normal:
                        row = decision(initial, life, arm, case, work, 'SOURCE')
                        old_ok &= plan_matches(old_map[life, case['id'], arm, 'SOURCE'], row); expected_old.append(row)
                    for case in targets:
                        row = decision(models[arm], life, arm, case, work)
                        zero_ok &= plan_matches(zero_map[life, case['id'], arm], row); expected_zero.append(row)
                allocation_ok = observations_ok = plans_ok = True
                for target_index, case in enumerate(targets):
                    seeds = {operator: 206000+(life*4+target_index)*3+i for i, operator in enumerate(OPERATORS)}
                    for arm in ARMS:
                        saved = history_map[life, target_index, arm]; model = models[arm]
                        current = make_plan(model, case, work); planned = [current]; spent = 0; consumed = Counter(); pilots = 0
                        plans_ok &= saved['context_id'] == case['id'] and saved['seeds'] == seeds and plan_matches(saved['initial_plan'], current)
                        for step, batch in enumerate(saved['batches']):
                            selected = (dict(operator=OPERATORS[step % 3], pilot=False, projection_counts=None, policy=None, policy_scores=None)
                                        if arm == 'UNIFORM' else choose(model, case, current, work))
                            allocation_ok &= stop_reason(current, spent) is None and all(
                                batch[key] == exact_json(selected[key]) for key in ('operator', 'pilot', 'projection_counts', 'policy', 'policy_scores'))
                            operator = batch['operator']; start = consumed[operator]; end = start+16; spent += 16
                            increments = dict.fromkeys(SUPPORT[operator], 0)
                            for category in prefixes[life, target_index, operator][start:end]:
                                increments[category] += 1
                            observations_ok &= batch['seed'] == seeds[operator] and batch['draw_start'] == start and batch['draw_end'] == end
                            observations_ok &= batch['operator_n'] == end and batch['spent'] == spent and batch['increments'] == increments
                            consumed[operator] = end; actual_samples[arm] += 16; pilots += selected['pilot']; pilot_choices[arm] += selected['pilot']
                            update(model, case, operator, increments, work)
                            current = make_plan(model, case, work); planned.append(current); plans_ok &= plan_matches(batch['plan'], current)
                        reason = stop_reason(current, spent)
                        allocation_ok &= reason is not None and bool(saved['batches'])
                        plans_ok &= plan_matches(saved['terminal'], dict(spent=spent, stop_reason=reason, plan=current))
                        expected_histories.append(dict(life=life, context_id=case['id'], target_index=target_index, arm=arm, plans=planned,
                            spent=spent, stop_reason=reason, first_operator=saved['batches'][0]['operator'],
                            pilot_batches=pilots, total_batches=len(saved['batches'])))
                for arm in ARMS:
                    for case in normal:
                        row = decision(models[arm], life, arm, case, work, 'FINAL')
                        old_ok &= plan_matches(old_map[life, case['id'], arm, 'FINAL'], row); expected_old.append(row)
                final_ok = all(model_matches(final_map[life][arm], models[arm]) for arm in ARMS)
                for name, flag in (('zero_before_target_and_old_source_final_policies', zero_ok and old_ok),
                                   ('common_projection_pilot_ratio_and_stopping', allocation_ok), ('paired_consumed_target_observations', observations_ok),
                                   ('raw_member_plans_and_fixed_condition_integer_updates', plans_ok and final_ok)):
                    check(f'life_{life}_{name}', flag)
            reference_map = {row['context_id']: row for row in references_saved}; reference_ok = len(reference_map) == len(references_saved) == 12
            for case in cases:
                pure = vectors(case, true_laws(case)); oracle = {q: max(route.utility(v, q, work) for v in pure.values()) for q in route.QUERIES}
                reference_ok &= plan_matches(reference_map[case['id']], dict(context_id=case['id'], pure_vectors=pure, oracle_utility=oracle))
            check('true_joint_policy_references', reference_ok)
            target_results, zero_results, old_results = [], [], []
            evaluation_flags = {life: True for life in range(12)}; implication = True
            for history in expected_histories:
                case = case_map[history['context_id']]; probabilities = true_laws(case)
                scores = [score(plan, probabilities, case, i*16, work) for i, plan in enumerate(history['plans'])]
                first = next((point['spent'] for point in scores if Fraction(point['actual_utility_fraction']) >= 2), None)
                terminal = dict(scores[-1], certified=history['stop_reason'] == 'certified', stop_reason=history['stop_reason'])
                result = {key: history[key] for key in ('life', 'context_id', 'target_index', 'arm', 'first_operator', 'pilot_batches', 'total_batches')}
                result.update(history=scores, terminal=terminal, first_true_utility_ge_2=first)
                evaluation_flags[history['life']] &= equal_numbers(target_map[history['life'], history['target_index'], history['arm']], result)
                target_results.append(result)
                for plan, point in zip(history['plans'], scores):
                    if point['coverage']:
                        implication &= Fraction(point['actual_fractions'][1]) <= plan['risk_upper'] and Fraction(point['actual_utility_fraction']) >= plan['utility_lower']
            for decisions, saved_map, output in ((expected_zero, zero_result_map, zero_results), (expected_old, old_result_map, old_results)):
                for row in decisions:
                    case = case_map[row['context_id']]; result = decision_score(row, case, true_laws(case), work)
                    key = (row['life'], case['id'], row['arm']) + ((row['stage'],) if 'stage' in row else ())
                    evaluation_flags[row['life']] &= equal_numbers(saved_map[key], result); output.append(result)
            for life, flag in evaluation_flags.items():
                check(f'life_{life}_own_policy_joint_target_transfer_and_retention', flag)
            check('covered_raw_members_imply_true_risk_and_goal_bounds', implication)
            expected_summary = summarize(target_results, zero_results, old_results, expected_sources, expected_qualification, work)
            check('lifecycle_bootstrap_and_five_frozen_conditions', equal_numbers(summary_saved, expected_summary))
            total_target = sum(actual_samples.values())
            source_costs = run['costs']['source_acquisition']; target_costs = run['costs']['target_acquisition']; fits = run['costs']['source_learning']
            expected_fits = [(life, phase, mode) for life in range(12) for phase, modes in
                             (('SOURCE', ('REVISED', 'FULL_CONTEXT')), ('REVISION', ('REVISED', 'FULL_CONTEXT', 'FIXED'))) for mode in modes]
            check('actual_acquisition_and_source_fit_costs', work['regenerated_source_samples'] == 36864
                  and work['reconstructed_model_fits'] == 60 and total_target <= 73728
                  and all(source_costs[key] == 36864 and target_costs[key] == total_target
                          for key in ('controlled_samples', 'controlled_resets', 'environment_random_draws'))
                  and fits['fit_calls'] == 48 and fits['fixed_model_calls'] == 12
                  and [(item['life'], item['phase'], item['mode']) for item in run['source_fits']] == expected_fits
                  and run['target_fit_calls'] == run['target_condition_selections'] == 0
                  and all(run['arm_costs'][arm]['target_acquisition']['controlled_samples'] == actual_samples[arm] for arm in ARMS))
            check('paid_source_and_per_arm_accounting', accounting == dict(samples_per_lifecycle={str(i): 3072 for i in range(12)},
                  total_samples=36864, model_fits=60, actual_fit_costs=run['source_fits'])
                  and all(Counter(run['costs'][stage]) == sum((Counter(run['arm_costs'][arm][stage]) for arm in ARMS), Counter())
                          for stage in ('choice', 'target_acquisition', 'update', 'planning', 'query_planning', 'evaluation')))
            phases = [('protocol_frozen', 0, 0, 0, 0, 0), ('task_qualified', 0, 0, 0, 0, 0)]
            for life in range(12):
                previous = sum(row['spent'] for row in expected_histories if row['life'] < life)
                phases.extend((('source_models_frozen', life*3072+1536, previous, life*16, life*16, life*32+16),
                               ('revision_models_frozen', (life+1)*3072, previous, life*16, (life+1)*16, life*32+16)))
            phases.extend((name, 36864, total_target, 192, 192, 384) for name in ('all_decisions_frozen', 'oracle_evaluated', 'complete'))
            check('plans_and_zero_probes_frozen_before_performance_oracle', run['status'] == 'complete' and
                  [(row['phase'], row['source_samples'], row['target_samples'], row['target_count'], row['zero_count'], row['old_count'])
                   for row in run['phase_history']] == phases)
            complete = True
    except Exception as error:
        checks.append(dict(name='independent_reconstruction_exception', passed=False, error=f'{type(error).__name__}: {error}'))
    analysis = dict(schema='acfqp.conditioned_mechanisms.v205.analysis', complete=complete,
                    valid=complete and all(row['passed'] for row in checks), checks=checks, costs=dict(work), seconds=perf_counter()-begun)
    (directory/'analysis.json').write_text(json.dumps(analysis, indent=2, sort_keys=True)+'\n')
    return analysis


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    result = analyze(parser.parse_args().directory)
    print(json.dumps(dict(complete=result['complete'], valid=result['valid'], checks=len(result['checks']))))
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

