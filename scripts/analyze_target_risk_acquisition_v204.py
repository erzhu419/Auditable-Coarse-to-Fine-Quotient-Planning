"""Independent adaptive-prefix, real-count and whole-policy acquisition audit.

No V204 producer mathematics is imported.  KL boxes, both common kernels,
forecast selection, updates, prefix observations and lifecycle decisions are
reconstructed.  Only actual integer batches enter the persistent model.
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

OUTPUT = ROOT / 'reports/target_risk_acquisition_v204'
OPERATORS = ('SHORT_PASS', 'DETOUR_PASS', 'RECOVERY_RETRY')
SUPPORT = {'SHORT_PASS': ('DELIVERY', 'LOST'), 'DETOUR_PASS': ('DELIVERY', 'LOST', 'RECOVERY'),
           'RECOVERY_RETRY': ('DELIVERY', 'LOST')}
FIELDS = ('operating', 'retry_cost', 'weather')
ARMS = ('GUIDED', 'UNIFORM', 'NO_SHARE', 'COLD_POLICY')
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


def forecast(model, case, current, work):
    probabilities = laws(model, case, work); scores = {}
    for operator in OPERATORS:
        disposable = {name: dict(row['counts']) for name, row in current['envelopes'].items()}
        for category in SUPPORT[operator]:
            disposable[operator][category] += 16 * probabilities[operator][category]
        envelope = boxes(disposable, work)
        score = optimize(current['pure_vectors'], risk_bounds(envelope), goal_bounds(envelope, case), work)
        scores[operator] = score['utility_lower']
        work['forecast_operator_candidates'] += 1
    selected = min(OPERATORS, key=lambda operator: (-scores[operator], OPERATORS.index(operator)))
    return dict(operator=selected, forecast_scores=scores)


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


def true_laws(case):
    short, detour, failure, recovery, retry = route.WEATHER[case['weather']]
    return {'SHORT_PASS': dict(DELIVERY=short, LOST=1 - short),
            'DETOUR_PASS': dict(DELIVERY=detour, LOST=failure, RECOVERY=recovery),
            'RECOVERY_RETRY': dict(DELIVERY=retry, LOST=1 - retry)}


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


def bootstrap(contrasts, work):
    size = len(next(iter(contrasts.values()))); rng = random.Random(204900)
    draws = {name: [] for name in contrasts}
    for _ in range(5000):
        indices = [rng.randrange(size) for _ in range(size)]
        for name, values in contrasts.items():
            draws[name].append(sum(values[index] for index in indices) / size)
        work['bootstrap_index_draws'] += size
        work['bootstrap_mean_terms'] += size * len(contrasts)
    work['bootstrap_resamples'] += 5000
    result = {}
    for name, values in draws.items():
        ordered = sorted(values); result[name] = dict(mean=mean(contrasts[name]), ci=[ordered[124], ordered[4874]])
    return result


def summarize(targets, old, work):
    arms, retention = {}, {}
    for arm in ARMS:
        rows = [row for row in targets if row['arm'] == arm]
        history = [item for row in rows for item in row['history']]
        first = [row['first_true_utility_ge_2'] for row in rows if row['first_true_utility_ge_2'] is not None]
        arms[arm] = dict(restored=sum(row['terminal']['certified'] for row in rows),
            total_samples=sum(row['terminal']['spent'] for row in rows), mean_samples=mean(row['terminal']['spent'] for row in rows),
            true_utility=mean(row['terminal']['actual_utility'] for row in rows), history_violations=sum(row['violation'] for row in history),
            terminal_violations=sum(row['terminal']['violation'] for row in rows), max_failure=max(row['actual'][1] for row in history),
            max_excess=max(row['excess'] for row in history), wait_mass=mean(row['terminal']['wait_mass'] for row in rows),
            coverage=mean(row['coverage'] for row in history), retrospective_true_restored=len(first),
            mean_first_true_samples=mean(first) if first else None)
        values = {stage: mean(query['regret'] for row in old if row['arm'] == arm and row['stage'] == stage
                              for query in row['queries'].values()) for stage in ('initial', 'final')}
        retention[arm] = dict(initial_regret=values['initial'], final_regret=values['final'], regret_change=values['final'] - values['initial'])
    contrasts = {name: [] for name in ('uniform_minus_guided_samples', 'no_share_minus_guided_samples',
        'guided_minus_uniform_utility', 'guided_minus_no_share_utility', 'cold_policy_minus_guided_samples',
        'guided_minus_cold_policy_utility')}
    for life in range(12):
        costs = {arm: mean(row['terminal']['spent'] for row in targets if row['life'] == life and row['arm'] == arm) for arm in ARMS}
        utilities = {arm: mean(row['terminal']['actual_utility'] for row in targets if row['life'] == life and row['arm'] == arm) for arm in ARMS}
        for arm, key in (('UNIFORM', 'uniform'), ('NO_SHARE', 'no_share'), ('COLD_POLICY', 'cold_policy')):
            contrasts[key + '_minus_guided_samples'].append(costs[arm] - costs['GUIDED'])
            contrasts['guided_minus_' + key + '_utility'].append(utilities['GUIDED'] - utilities[arm])
    intervals = bootstrap(contrasts, work)
    hard = [point for row in targets if row['arm'] == 'GUIDED' for point in row['history']]
    hard.extend(row['hard'] for row in old if row['arm'] == 'GUIDED')
    conditions = dict(RISK=all(Fraction(row['risk_upper']) <= DELTA and not row['violation'] for row in hard),
        RESTORATION=arms['GUIDED']['restored'] >= 36 and arms['GUIDED']['true_utility'] >= 2,
        ALLOCATION=intervals['uniform_minus_guided_samples']['mean'] >= 16 and intervals['uniform_minus_guided_samples']['ci'][0] > 0
            and arms['GUIDED']['restored'] >= arms['UNIFORM']['restored'],
        KNOWLEDGE=all(intervals[key]['mean'] >= 16 and intervals[key]['ci'][0] > 0 for key in
            ('no_share_minus_guided_samples', 'cold_policy_minus_guided_samples'))
            and all(arms['GUIDED']['restored'] >= arms[arm]['restored'] for arm in ('NO_SHARE', 'COLD_POLICY'))
            and retention['GUIDED']['regret_change'] <= .01)
    return dict(schema='acfqp.target_risk_acquisition.v204.summary', complete=True, targets_per_arm=48,
        arms=arms, retention=retention, paired_lifecycle_contrasts=contrasts, bootstrap=intervals, conditions=conditions,
        decision='TARGET_ACQUISITION_SUPPORTED' if all(conditions.values()) else 'TARGET_ACQUISITION_NOT_SUPPORTED',
        cold_start_reference={arm: dict(source_samples=0, target_samples=arms[arm]['total_samples']) for arm in ('NO_SHARE', 'COLD_POLICY')})


def raw_tables(lifecycle, work):
    groups = {operator: {} for operator in OPERATORS}
    for batch in lifecycle['batches']:
        for row in batch['records']:
            operator = row['operator']; key = projection(row['context'])
            if key not in groups[operator]:
                groups[operator][key] = dict(context=dict(row['context']), counts=dict.fromkeys(SUPPORT[operator], 0))
            for category in SUPPORT[operator]:
                groups[operator][key]['counts'][category] += row['counts'][category]
                work['source_count_additions'] += 1
    return {operator: [table[key] for key in sorted(table)] for operator, table in groups.items()}


def old_expected(life, arm, stage, model, case, work):
    return dict(life=life, context_id=case['id'], arm=arm, stage=stage,
                hard=make_plan(model, case, work), queries=query_decisions(model, case, work))


def old_score(decision, case, probabilities, work):
    pure = vectors(case, probabilities); queries = {}
    for query, row in decision['queries'].items():
        actual = pure[row['pure_policy']]; u = route.utility(actual, query, work)
        oracle = max(route.utility(vector, query, work) for vector in pure.values())
        queries[query] = dict(actual_fractions=exact_json(actual), actual=[float(x) for x in actual],
            utility_fraction=str(u), utility=float(u), oracle_utility_fraction=str(oracle), oracle_utility=float(oracle),
            regret_fraction=str(oracle - u), regret=float(oracle - u))
    return dict(life=decision['life'], context_id=case['id'], arm=decision['arm'], stage=decision['stage'],
                hard=score(decision['hard'], probabilities, case, 0, work), queries=queries)


def consumed_prefixes(histories, targets, work):
    maximum = Counter()
    for row in histories:
        consumed = Counter(batch['operator'] for batch in row['batches'])
        if len(row['batches']) > 24:
            raise ValueError('target history exceeds the frozen 24-batch budget')
        for operator in OPERATORS:
            key = row['life'], row['target_index'], operator
            maximum[key] = max(maximum[key], 16 * consumed[operator])
    prefixes = {}
    for (life, target_index, operator), n in maximum.items():
        seed = 204000 + (life * 4 + target_index) * 3 + OPERATORS.index(operator)
        probabilities = true_laws(targets[target_index])[operator]
        prefixes[life, target_index, operator] = generate_prefix(seed, n, probabilities, SUPPORT[operator], work)
    return prefixes


def analyze(directory=OUTPUT):
    begun = perf_counter(); work = Counter(); checks = []; complete = False
    def check(name, flag):
        checks.append(dict(name=name, passed=bool(flag)))
    try:
        def read(relative):
            raw = (directory / relative).read_bytes(); work['input_files_read'] += 1; work['input_bytes_read'] += len(raw)
            return json.loads(raw)
        cases, batches, snapshots, source_run = (read('inputs/' + name) for name in ('cases.json', 'batches.json', 'snapshots.json', 'run.json'))
        histories, old_saved = (read(name)['records'] for name in ('histories.json', 'old_decisions.json'))
        final_models = read('models.json')['lifecycles']
        target_saved, old_results_saved, references_saved = (read(name)['records'] for name in
            ('target_results.json', 'old_results.json', 'reference.json'))
        summary_saved, accounting, run = (read(name) for name in ('summary.json', 'source_accounting.json', 'run.json'))
        source_manifest, input_manifest = read('source_manifest.json'), read('input_manifest.json')
        targets = [case for case in cases if case['weather'] != 'normal' and case['operating'] == 'low']
        old_cases = [case for case in cases if case not in targets]; case_map = {case['id']: case for case in cases}
        check('frozen_cases_and_lifecycles', cases == route.roster() and
              [(row['life'], row['seed']) for row in batches['lifecycles']] == [(i, 202000 + i) for i in range(12)])
        history_map = {(row['life'], row['target_index'], row['arm']): row for row in histories}
        old_map = {(row['life'], row['context_id'], row['arm'], row['stage']): row for row in old_saved}
        target_map = {(row['life'], row['target_index'], row['arm']): row for row in target_saved}
        old_result_map = {(row['life'], row['context_id'], row['arm'], row['stage']): row for row in old_results_saved}
        model_map = {row['life']: row['models'] for row in final_models}
        check('complete_four_arm_decision_rosters', len(history_map) == len(histories) == 192 and len(old_map) == len(old_saved) == 768
            and len(target_map) == len(target_saved) == 192 and len(old_result_map) == len(old_results_saved) == 768
            and len(model_map) == len(final_models) == 12)
        prefixes = consumed_prefixes(histories, targets, work)
        source_models = {row['life']: row['models'] for row in snapshots['checkpoints'] if row['checkpoint'] == 'FINAL_REUSE'}
        expected_histories, expected_old = [], []; real_samples = Counter()
        for lifecycle in batches['lifecycles']:
            life = lifecycle['life']; raw = raw_tables(lifecycle, work); sources = source_models[life]
            check(f'life_{life}_source_real_count_tables', all(sources[arm]['tables'] == raw for arm in ('REVISED', 'FULL_CONTEXT')))
            models = {arm: deepcopy(sources['FULL_CONTEXT' if arm in ('NO_SHARE', 'COLD_POLICY') else 'REVISED']) for arm in ARMS}
            old_ok = True
            for case in old_cases:
                for arm in ARMS:
                    decision = old_expected(life, arm, 'initial', models[arm], case, work)
                    old_ok &= plan_matches(old_map[life, case['id'], arm, 'initial'], decision); expected_old.append(decision)
            allocation_ok = draws_ok = plans_ok = True
            for target_index, case in enumerate(targets):
                seeds = {operator: 204000 + (life * 4 + target_index) * 3 + i for i, operator in enumerate(OPERATORS)}
                for arm in ARMS:
                    saved = history_map[life, target_index, arm]; model = models[arm]
                    current = make_plan(model, case, work); planned = [current]; spent = 0; draws = Counter()
                    plans_ok &= (saved['context_id'] == case['id'] and saved['seeds'] == seeds and plan_matches(saved['initial_plan'], current))
                    for step, batch in enumerate(saved['batches']):
                        choice = (dict(operator=OPERATORS[step % 3], forecast_scores=None) if arm == 'UNIFORM' else
                                  cold_policy(model, case, current, work) if arm == 'COLD_POLICY' else forecast(model, case, current, work))
                        allocation_ok &= (stop_reason(current, spent) is None and batch['operator'] == choice['operator']
                            and batch['forecast_scores'] == exact_json(choice['forecast_scores'])
                            and batch['policy'] == choice.get('policy') and batch['policy_scores'] == exact_json(choice.get('policy_scores')))
                        operator = batch['operator']; start = draws[operator]; end = start + 16; spent += 16
                        counts = dict.fromkeys(SUPPORT[operator], 0)
                        for outcome in prefixes[life, target_index, operator][start:end]:
                            counts[outcome] += 1
                        draws_ok &= (batch['seed'] == seeds[operator] and batch['draw_start'] == start and batch['draw_end'] == end
                            and batch['operator_n'] == end and batch['spent'] == spent and batch['increments'] == counts and sum(counts.values()) == 16)
                        draws[operator] = end; real_samples[arm] += 16
                        update(model, case, operator, batch['increments'], work)
                        current = make_plan(model, case, work); planned.append(current)
                        plans_ok &= plan_matches(batch['plan'], current)
                    reason = stop_reason(current, spent)
                    allocation_ok &= reason is not None and bool(saved['batches'])
                    plans_ok &= plan_matches(saved['terminal'], dict(spent=spent, stop_reason=reason, plan=current))
                    expected_histories.append(dict(life=life, context_id=case['id'], target_index=target_index, arm=arm,
                                                    plans=planned, spent=spent, stop_reason=reason))
            for case in old_cases:
                for arm in ARMS:
                    decision = old_expected(life, arm, 'final', models[arm], case, work)
                    old_ok &= plan_matches(old_map[life, case['id'], arm, 'final'], decision); expected_old.append(decision)
            final_ok = all(all(model_map[life][arm][field] == models[arm][field] for field in
                               ('selected_fields', 'scores', 'tables', 'observations_used')) for arm in ARMS)
            for name, flag in (('forecast_or_cold_or_uniform_stopping', allocation_ok), ('paired_consumed_prefixes', draws_ok),
                               ('real_plans_no_forecast_evidence', plans_ok), ('persistent_fixed_fields_final_models', final_ok),
                               ('initial_final_old_decisions', old_ok)):
                check(f'life_{life}_{name}', flag)
        reference_map = {row['context_id']: row for row in references_saved}; reference_ok = len(reference_map) == len(references_saved) == 12
        laws_map = {}
        for case in cases:
            probabilities = true_laws(case); laws_map[case['id']] = probabilities; pure = vectors(case, probabilities)
            oracle = {query: max(route.utility(vector, query, work) for vector in pure.values()) for query in route.QUERIES}
            reference_ok &= plan_matches(reference_map[case['id']], dict(context_id=case['id'], pure_vectors=pure, oracle_utility=oracle))
        check('true_joint_references', reference_ok)
        target_results, old_results = [], []; evaluation_flags = {life: True for life in range(12)}; implication = True
        for history in expected_histories:
            case = case_map[history['context_id']]; probabilities = laws_map[case['id']]
            scores = [score(plan, probabilities, case, step * 16, work) for step, plan in enumerate(history['plans'])]
            first = next((row['spent'] for row in scores if Fraction(row['actual_utility_fraction']) >= 2), None)
            terminal = dict(scores[-1], certified=history['stop_reason'] == 'certified', stop_reason=history['stop_reason'])
            result = dict(life=history['life'], context_id=case['id'], target_index=history['target_index'], arm=history['arm'],
                          history=scores, terminal=terminal, first_true_utility_ge_2=first)
            evaluation_flags[history['life']] &= equal_numbers(target_map[history['life'], history['target_index'], history['arm']], result)
            target_results.append(result)
        for decision in expected_old:
            case = case_map[decision['context_id']]; result = old_score(decision, case, laws_map[case['id']], work)
            evaluation_flags[decision['life']] &= equal_numbers(old_result_map[decision['life'], case['id'], decision['arm'], decision['stage']], result)
            old_results.append(result)
        for scored in [row for target in target_results for row in target['history']] + [row['hard'] for row in old_results]:
            if scored['coverage']:
                implication &= (Fraction(scored['actual_fractions'][1]) <= Fraction(scored['risk_upper'])
                                and Fraction(scored['actual_utility_fraction']) >= Fraction(scored['utility_lower']))
        for life, flag in evaluation_flags.items():
            check(f'life_{life}_own_joint_history_retention_and_coverage', flag)
        check('covered_kernels_imply_risk_and_goal_bounds', implication)
        check('life_bootstrap_and_four_frozen_conditions', equal_numbers(summary_saved, summarize(target_results, old_results, work)))
        per_life = {str(row['life']): sum(sum(record['counts'].values()) for batch in row['batches'] for record in batch['records'])
                    for row in batches['lifecycles']}
        inherited = {arm: source_run['arm_costs']['FULL_CONTEXT' if arm in ('NO_SHARE', 'COLD_POLICY') else 'REVISED'] for arm in ARMS}
        check('paid_historical_source_accounting', accounting == dict(samples_per_lifecycle=per_life, total_samples=sum(per_life.values()),
                                                                    inherited_arm_costs=inherited, inherited_aggregate_costs=source_run['costs']))
        total = sum(real_samples.values())
        phases = [(row['phase'], row['target_count'], row['old_decision_count'], row['controlled_samples'], row['fit_calls'], row['condition_selections'])
                  for row in run['phase_history']]
        check('all_decisions_before_oracle_and_no_new_fit', phases == [
            ('inputs_frozen', 0, 0, 0, 0, 0), ('all_decisions_frozen', 192, 768, total, 0, 0),
            ('oracle_evaluated', 192, 768, total, 0, 0), ('complete', 192, 768, total, 0, 0)]
            and run['status'] == 'complete' and run['fit_calls'] == run['condition_selections'] == 0
            and len(run['prerequisites']) == 2 and all(row['valid'] and row['complete'] for row in run['prerequisites']))
        stages = ('acquisition', 'update', 'forecast', 'planning', 'retention_planning', 'evaluation')
        sums = {stage: Counter() for stage in stages}
        for arm in ARMS:
            for stage in stages:
                sums[stage].update(run['arm_costs'][arm][stage])
        check('separate_arm_actual_sample_and_work_ledgers', all(dict(counter) == run['costs'][stage] for stage, counter in sums.items())
            and total <= 73728 and all(run['arm_costs'][arm]['acquisition']['controlled_samples'] == real_samples[arm] for arm in ARMS)
            and all(run['costs']['acquisition'][name] == total for name in ('controlled_samples', 'controlled_resets', 'environment_random_draws'))
            and run['costs']['bootstrap'] == {name: work[name] for name in ('bootstrap_index_draws', 'bootstrap_mean_terms', 'bootstrap_resamples')})
        check('retained_source_and_inputs', len(source_manifest) == 11 and [row['name'] for row in input_manifest] ==
              ['cases.json', 'batches.json', 'snapshots.json', 'run.json'])
        complete = True
    except Exception as error:
        check('independent_reconstruction', False); failure = dict(type=type(error).__name__, message=str(error))
    analysis = dict(schema='acfqp.target_risk_acquisition.v204.analysis', complete=complete,
                    valid=complete and all(row['passed'] for row in checks), checks=checks, costs=dict(work),
                    seconds=perf_counter() - begun, new_samples=0, fit_calls=0)
    if not complete:
        analysis['error'] = failure
    (directory / 'analysis.json').write_text(json.dumps(analysis, separators=(',', ':')) + '\n')
    return analysis


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    result = analyze(parser.parse_args().directory)
    print(json.dumps(dict(complete=result['complete'], valid=result['valid'], checks=len(result['checks']))))
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())



