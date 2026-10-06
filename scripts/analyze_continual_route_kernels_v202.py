"""Independent count/evidence audit of chronological conditional route kernels.

New learning and sampling implementations are not imported.  The V201 finite
planner is a settled interface; all conditional sufficient statistics, evidence,
posterior probabilities and complete-policy actual vectors are reconstructed.
"""
import argparse
from collections import Counter, defaultdict
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

OUTPUT = ROOT / 'reports/continual_route_kernels_v202'
FEATURES = ('operating', 'retry_cost', 'weather')
OPERATORS = ('SHORT_PASS', 'DETOUR_PASS', 'RECOVERY_RETRY')
SUPPORT = {'SHORT_PASS': ('DELIVERY', 'LOST'),
           'DETOUR_PASS': ('DELIVERY', 'LOST', 'RECOVERY'),
           'RECOVERY_RETRY': ('DELIVERY', 'LOST')}
ARMS = ('REVISED', 'RESET', 'FROZEN', 'FULL_CONTEXT', 'FIXED_WEATHER')
CHECKPOINTS = ('SOURCE', 'NEW_COST_ZERO', 'NEW_COST128', 'NEW_WEATHER_ZERO',
               'NEW_WEATHER64', 'NEW_WEATHER256', 'FINAL_REUSE')
EPS = 1e-9
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


def subsets():
    return [fields for size in range(4) for fields in combinations(FEATURES, size)]


def context_key(case, fields):
    return tuple(str(case[field]) for field in fields)


def aggregate(records, fields, operator, work=None):
    work = Counter() if work is None else work
    groups = {}
    for record in records:
        if record['operator'] != operator:
            continue
        key = context_key(record['context'], fields)
        if key not in groups:
            groups[key] = {category: 0 for category in SUPPORT[operator]}
        for category in SUPPORT[operator]:
            groups[key][category] += int(record['counts'].get(category, 0))
            work['count_component_additions'] += 1
    return groups


def evidence(groups, operator, work=None):
    """Ordered-data Dirichlet integral; there is no multinomial coefficient."""
    work = Counter() if work is None else work
    size = len(SUPPORT[operator]); total = 0.0
    for key in sorted(groups):
        counts = groups[key]; number = sum(counts.values())
        base = math.lgamma(size * .5) - math.lgamma(number + size * .5)
        terms = [math.lgamma(counts[category] + .5) - math.lgamma(.5)
                 for category in SUPPORT[operator]]
        total += base + sum(terms)
        work['evidence_groups'] += 1
        work['evidence_lgamma_calls'] += 2 + 2 * size
    return total


def rebuild_model(records, arm='REVISED', frozen=None, work=None):
    work = Counter() if work is None else work
    if arm == 'FROZEN' and frozen is not None:
        return frozen
    selected, scores, tables = {}, {}, {}
    for operator in OPERATORS:
        candidates = subsets() if arm in ('REVISED', 'RESET', 'FROZEN') else [
            FEATURES if arm == 'FULL_CONTEXT' else ('weather',)]
        winner, best, rows = None, None, []
        for fields in candidates:
            grouped = aggregate(records, fields, operator, work)
            score = evidence(grouped, operator, work)
            rows.append(dict(fields=list(fields), score=score))
            if (best is None or score > best + EPS or
                    (abs(score - best) <= EPS and (len(fields), fields) < (len(winner), winner))):
                winner, best = fields, score
        grouped = aggregate(records, FEATURES, operator, work)
        selected[operator] = list(winner); scores[operator] = rows
        tables[operator] = [dict(context=next(dict(row['context']) for row in records
                                             if row['operator'] == operator
                                             and context_key(row['context'], FEATURES) == key),
                                counts=grouped[key]) for key in sorted(grouped)]
    work['reconstructed_models'] += 1
    return dict(schema='acfqp.continual_route_kernels.v202.model', arm=arm,
                selected_fields=selected, scores=scores, tables=tables,
                observations_used=sum(sum(row['counts'].values()) for row in records))


def posterior(model, case, operator, work=None):
    work = Counter() if work is None else work
    fields = tuple(model['selected_fields'][operator])
    counts = {category: 0 for category in SUPPORT[operator]}
    for row in model['tables'][operator]:
        if context_key(row['context'], fields) == context_key(case, fields):
            for category in SUPPORT[operator]:
                counts[category] += row['counts'][category]
    number = sum(counts.values()); size = len(SUPPORT[operator])
    work['posterior_calls'] += 1
    return {category: Fraction(2 * counts.get(category, 0) + 1, 2 * number + size)
            for category in SUPPORT[operator]}


def predicted_graph(model, case, work=None):
    """Declared graph and cost prior, with independently estimated probabilities."""
    work = Counter() if work is None else work
    one, zero = Fraction(1), Fraction(0)
    short_cost, detour_cost = route.OPERATING[case['operating']]
    graph = {state: {} for state in route.STATES}
    graph['START'] = {action: [(one, action + '_ENTRY', zero)]
                      for action in ('DETOUR', 'SHORT', 'WAIT')}
    graph['WAIT_ENTRY'] = {'WAIT': [(one, 'ABORT', zero)]}
    graph['DELIVERY'] = {'FINISH': [(one, 'WON', zero)]}
    for operator, state, action, cost in (
            ('SHORT_PASS', 'SHORT_ENTRY', 'PASS', short_cost),
            ('DETOUR_PASS', 'DETOUR_ENTRY', 'PASS', detour_cost),
            ('RECOVERY_RETRY', 'RECOVERY', 'RETRY', Fraction(case['retry_cost']))):
        probabilities = posterior(model, case, operator, work)
        graph[state][action] = [(probabilities[category], category, -cost)
                                for category in SUPPORT[operator]]
    graph['RECOVERY']['RETURN'] = [(one, 'ABORT', zero)]
    work['predicted_graphs'] += 1
    return graph


def complete_vectors(case, probabilities=None, work=None):
    """Four complete H4 policies; reward, failure and success remain joint."""
    work = Counter() if work is None else work
    if probabilities is None:
        short, detour, failure, recovery, retry = route.WEATHER[case['weather']]
    else:
        short = probabilities['SHORT_PASS']['DELIVERY']
        detour = probabilities['DETOUR_PASS']['DELIVERY']
        failure = probabilities['DETOUR_PASS']['LOST']
        recovery = probabilities['DETOUR_PASS']['RECOVERY']
        retry = probabilities['RECOVERY_RETRY']['DELIVERY']
    short_cost, detour_cost = route.OPERATING[case['operating']]
    work['closed_complete_vectors'] += 4
    return {'WAIT': ZERO, 'SHORT': (-short_cost, 1 - short, short),
            'DETOUR_RETURN': (-detour_cost, failure, detour),
            'DETOUR_RETRY': (-detour_cost - recovery * Fraction(case['retry_cost']),
                            failure + recovery * (1 - retry), detour + recovery * retry)}


def selected_complete_policy(root_action, recovery_action):
    if root_action == 'DETOUR':
        return 'DETOUR_RETRY' if recovery_action == 'RETRY' else 'DETOUR_RETURN'
    return root_action


def utility(vector, query):
    reward, failure, success = route.QUERIES[query]
    return reward * vector[0] - failure * vector[1] + success * vector[2]


def mixture_vector(mix, vectors):
    return tuple(sum((Fraction(row['weight']) * vectors[row['policy']][k]
                      for row in mix), Fraction(0)) for k in range(3))


def constrained_bound(vectors, delta=DELTA):
    """Independent upper frontier in (F, goal utility), not pair enumeration."""
    best_by_failure = {}
    for name, vector in vectors.items():
        point = vector[1], utility(vector, 'goal'), name
        if point[0] not in best_by_failure or point[1] > best_by_failure[point[0]][1]:
            best_by_failure[point[0]] = point
    hull = []
    for point in sorted(best_by_failure.values()):
        while len(hull) > 1:
            a, b = hull[-2:]
            cross = (b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0])
            if cross < 0:
                break
            hull.pop()
        hull.append(point)
    bounds = [point[1] for point in hull if point[0] <= delta]
    for a, b in zip(hull, hull[1:]):
        if a[0] < delta < b[0]:
            fraction = (delta - a[0]) / (b[0] - a[0])
            bounds.append(a[1] + fraction * (b[1] - a[1]))
    return max(bounds)


def true_probabilities(case, operator):
    short, detour, failure, recovery, retry = route.WEATHER[case['weather']]
    return {'SHORT_PASS': (short, 1 - short),
            'DETOUR_PASS': (detour, failure, recovery),
            'RECOVERY_RETRY': (retry, 1 - retry)}[operator]


def sample_batches(seed, work=None):
    """One independent regeneration of the fixed chronological random stream."""
    work = Counter() if work is None else work
    rng = random.Random(seed); cases = route.roster()
    source = [case for case in cases if case['weather'] == 'normal' and case['operating'] == 'low']
    high = [case for case in cases if case['weather'] == 'normal' and case['operating'] == 'high']
    novel = [case for case in cases if case['weather'] != 'normal' and case['operating'] == 'high']
    batches = []
    draw_index = 0
    for name, contexts, number in (('SOURCE', source, 256), ('NEW_COST128', high, 128),
                                    ('NEW_WEATHER64', novel, 64), ('NEW_WEATHER256', novel, 192)):
        records = []
        for case in contexts:
            for operator in OPERATORS:
                counts = {category: 0 for category in SUPPORT[operator]}
                probabilities = true_probabilities(case, operator)
                begin = draw_index
                for _ in range(number):
                    draw = rng.random(); cumulative = Fraction(0)
                    for category, probability in zip(SUPPORT[operator], probabilities):
                        cumulative += probability
                        if draw < float(cumulative):
                            counts[category] += 1; break
                    work['regenerated_samples'] += 1
                    draw_index += 1
                records.append(dict(context=case, operator=operator, counts=counts,
                                    n=number, phase=name, draw_start=begin, draw_end=draw_index))
        batches.append(dict(name=name, records=records))
    return batches


def probe_contexts(checkpoint):
    cases = route.roster()
    if checkpoint == 'SOURCE':
        return [case for case in cases if case['weather'] == 'normal' and case['operating'] == 'low']
    if checkpoint.startswith('NEW_COST'):
        return [case for case in cases if case['weather'] == 'normal' and case['operating'] == 'high']
    if checkpoint.startswith('NEW_WEATHER'):
        return [case for case in cases if case['weather'] != 'normal' and case['operating'] == 'high']
    return [case for case in cases if case['weather'] == 'normal' or case['operating'] == 'low']


def reconstruct_choice(model, case, work=None):
    work = Counter() if work is None else work
    probabilities = {operator: posterior(model, case, operator, work) for operator in OPERATORS}
    estimated, actual = complete_vectors(case, probabilities, work), complete_vectors(case, work=work)
    graph = predicted_graph(model, case, work)
    tv = {operator: sum((abs(probabilities[operator][category] - probability)
                         for category, probability in zip(SUPPORT[operator], true_probabilities(case, operator))),
                        Fraction(0)) / 2 for operator in OPERATORS}
    queries = {}
    for query in route.QUERIES:
        plan = route.plan(graph, 4, query, work)
        root, recovery = plan['policy']['START', 4], plan['policy']['RECOVERY', 2]
        name = selected_complete_policy(root, recovery)
        detour_name = min(('DETOUR_RETURN', 'DETOUR_RETRY'),
                          key=lambda name: (-utility(actual[name], query), name))
        oracle_options = {'DETOUR': actual[detour_name], 'SHORT': actual['SHORT'], 'WAIT': actual['WAIT']}
        oracle_root = min(oracle_options, key=lambda action: (-utility(oracle_options[action], query), action))
        oracle_vector = oracle_options[oracle_root]; oracle = utility(oracle_vector, query)
        queries[query] = dict(root_action=root, recovery_action=recovery,
                             predicted_vector=estimated[name], actual_vector=actual[name],
                             predicted_utility=utility(estimated[name], query),
                             actual_utility=utility(actual[name], query),
                             regret=oracle - utility(actual[name], query), oracle_vector=oracle_vector,
                             oracle_utility=oracle, policy=plan['policy'])
    return dict(context=case, probabilities=probabilities, kernel_tv=tv, queries=queries,
                estimated_pure=estimated, actual_pure=actual, graph=graph)


def paired_bootstrap(contrasts, work=None):
    """A shared lifecycle-index draw for all contrasts, rather than case draws."""
    work = Counter() if work is None else work
    size = len(next(iter(contrasts.values()))); rng = random.Random(202900)
    draws = {name: [] for name in contrasts}
    for _ in range(5000):
        indices = [rng.randrange(size) for _ in range(size)]
        for name, values in contrasts.items():
            draws[name].append(sum(values[index] for index in indices) / size)
        work['bootstrap_index_draws'] += size
        work['bootstrap_mean_terms'] += size * len(contrasts)
    result = {}
    for name, values in contrasts.items():
        ordered = sorted(draws[name])
        result[name] = dict(mean=sum(values) / size, ci=[ordered[124], ordered[4874]])
    work['bootstrap_resamples'] += 5000
    return result


def mean(values):
    values = list(values)
    return sum(values) / len(values)


def life_metric(records, name):
    if name == 'tv':
        return mean(mean(float(value) for value in row['kernel_tv'].values()) for row in records)
    if name in ('utility', 'regret'):
        field = 'actual_utility' if name == 'utility' else 'regret'
        return mean(mean(float(query[field]) for query in row['queries'].values()) for row in records)
    component = ('R', 'F', 'S').index(name)
    return mean(mean(abs(float(query['predicted_vector'][component] - query['actual_vector'][component]))
                     for query in row['queries'].values()) for row in records)


def independent_summary(lives, work=None):
    """All thresholds use paired learner lifecycles and the frozen probe sets."""
    work = Counter() if work is None else work
    contrasts = {name: [] for name in ('zero_tv', 'revision_tv', 'transfer_full', 'transfer_frozen')}
    final = {arm: [] for arm in ARMS}; final_unacquired = {arm: [] for arm in ARMS}
    retained, short_weather = [], 0
    for life in lives:
        records = life['evaluations']
        for arm in ARMS:
            full = records['NEW_WEATHER256'][arm] + records['FINAL_REUSE'][arm]
            unacquired = [row for row in records['FINAL_REUSE'][arm] if row['context']['weather'] != 'normal']
            final[arm].append({metric: life_metric(full, metric) for metric in ('tv', 'utility', 'regret', 'R', 'F', 'S')})
            final_unacquired[arm].append({metric: life_metric(unacquired, metric) for metric in ('tv', 'utility')})
        contrasts['zero_tv'].append(life_metric(records['NEW_COST_ZERO']['FULL_CONTEXT'], 'tv') -
                                    life_metric(records['NEW_COST_ZERO']['REVISED'], 'tv'))
        contrasts['revision_tv'].append(final_unacquired['FROZEN'][-1]['tv'] - final_unacquired['REVISED'][-1]['tv'])
        contrasts['transfer_full'].append(final_unacquired['REVISED'][-1]['utility'] - final_unacquired['FULL_CONTEXT'][-1]['utility'])
        contrasts['transfer_frozen'].append(final_unacquired['REVISED'][-1]['utility'] - final_unacquired['FROZEN'][-1]['utility'])
        old = [row for row in records['FINAL_REUSE']['REVISED']
               if row['context']['weather'] == 'normal' and row['context']['operating'] == 'low']
        retained.append(life_metric(old, 'regret') - life_metric(records['SOURCE']['REVISED'], 'regret'))
        short_weather += life['models']['NEW_WEATHER256']['REVISED']['selected_fields']['SHORT_PASS'] == ['weather']
    bootstrap = paired_bootstrap(contrasts, work)
    final_means = {arm: {metric: mean(row[metric] for row in values)
                         for metric in ('tv', 'utility', 'regret', 'R', 'F', 'S')} for arm, values in final.items()}
    revised = final_means['REVISED']; fixed_gap = revised['regret'] - final_means['FIXED_WEATHER']['regret']
    retention = mean(retained)
    conditions = dict(
        ZERO_SAMPLE_REUSE=bootstrap['zero_tv']['mean'] > .05 and bootstrap['zero_tv']['ci'][0] > 0,
        CONDITION_REVISION=bootstrap['revision_tv']['mean'] > .02 and bootstrap['revision_tv']['ci'][0] > 0 and short_weather >= 10,
        POLICY_TRANSFER=all(bootstrap[key]['mean'] > threshold and bootstrap[key]['ci'][0] > 0
                            for key, threshold in (('transfer_full', .05), ('transfer_frozen', .01))),
        QUALITY_RETENTION=revised['tv'] <= .05 and revised['regret'] <= .05
            and all(revised[metric] <= .05 for metric in ('R', 'F', 'S')) and fixed_gap <= .01 and retention <= .01)
    checkpoint_means, hard_risk = {}, {}
    for checkpoint in CHECKPOINTS:
        checkpoint_means[checkpoint] = {}; hard_risk[checkpoint] = {}
        for arm in ARMS:
            grouped = [life['evaluations'][checkpoint][arm] for life in lives]
            checkpoint_means[checkpoint][arm] = {metric: mean(life_metric(rows, metric) for rows in grouped)
                                                for metric in ('tv', 'utility', 'regret', 'R', 'F', 'S')}
            violations = [float(row['hard_violation']) for rows in grouped for row in rows]
            hard_risk[checkpoint][arm] = dict(evaluations=len(violations),
                violations=sum(value > 0 for value in violations), mean_violation=mean(violations),
                max_violation=max(violations))
    return dict(bootstrap=bootstrap, final_means=final_means, weather_selected=short_weather,
                retention_change=retention, fixed_regret_gap=fixed_gap, conditions=conditions,
                checkpoint_means=checkpoint_means, hard_risk=hard_risk,
                paired_lifecycle_contrasts=contrasts,
                decision='CONDITIONAL_LEARNING_SUPPORTED' if all(conditions.values()) else 'CONDITIONAL_LEARNING_NOT_SUPPORTED')


def equal_numbers(saved, expected):
    if isinstance(expected, dict):
        return all(key in saved and equal_numbers(saved[key], value) for key, value in expected.items())
    if isinstance(expected, (tuple, list)):
        return len(saved) == len(expected) and all(equal_numbers(a, b) for a, b in zip(saved, expected))
    if isinstance(expected, float):
        return abs(saved - expected) <= 1e-12 * (1 + abs(expected))
    return saved == expected


def model_matches(saved, expected):
    return (all(saved[key] == expected[key] for key in ('schema', 'arm', 'selected_fields', 'tables', 'observations_used'))
            and all(len(saved['scores'][op]) == len(expected['scores'][op])
                and all(left['fields'] == right['fields'] and abs(left['score'] - right['score']) <= EPS
                        for left, right in zip(saved['scores'][op], expected['scores'][op])) for op in OPERATORS))


def query_result_matches(saved, expected):
    exact = dict(actual_fractions=exact_json(expected['actual_vector']),
                 utility_fraction=str(expected['actual_utility']),
                 oracle_fractions=exact_json(expected['oracle_vector']),
                 oracle_utility_fraction=str(expected['oracle_utility']), regret_fraction=str(expected['regret']))
    numeric = dict(actual=[float(x) for x in expected['actual_vector']], utility=float(expected['actual_utility']),
                   oracle=[float(x) for x in expected['oracle_vector']], oracle_utility=float(expected['oracle_utility']),
                   regret=float(expected['regret']), abs_prediction_error=[
                       abs(float(a - b)) for a, b in zip(expected['predicted_vector'], expected['actual_vector'])])
    return all(saved[key] == value for key, value in exact.items()) and equal_numbers(saved, numeric)


def certify_choice(prediction, result, expected):
    prediction_ok = (prediction['operator_probabilities'] == exact_json(expected['probabilities'])
        and prediction['graph'] == exact_json(expected['graph'])
        and prediction['pure_vectors'] == exact_json(expected['estimated_pure']))
    result_ok = (result['kernel_tv_fractions'] == exact_json(expected['kernel_tv'])
                 and equal_numbers(result['kernel_tv'], {key: float(value) for key, value in expected['kernel_tv'].items()}))
    for query, row in expected['queries'].items():
        saved = prediction['queries'][query]
        prediction_ok &= (saved['root_action'] == row['root_action'] and saved['recovery_action'] == row['recovery_action']
            and saved['pure_policy'] == selected_complete_policy(row['root_action'], row['recovery_action'])
            and saved['predicted_fractions'] == exact_json(row['predicted_vector'])
            and equal_numbers(saved['predicted'], [float(value) for value in row['predicted_vector']]))
        result_ok &= query_result_matches(result['queries'][query], row)
    mixture = [dict(policy=name, weight=weight) for name, weight in prediction['hard']['mix']]
    predicted = mixture_vector(mixture, expected['estimated_pure']); actual = mixture_vector(mixture, expected['actual_pure'])
    violation = max(Fraction(0), actual[1] - DELTA)
    hard_ok = (bool(mixture) and all(Fraction(row['weight']) > 0 for row in mixture)
        and sum((Fraction(row['weight']) for row in mixture), Fraction(0)) == 1 and predicted[1] <= DELTA
        and utility(predicted, 'goal') == constrained_bound(expected['estimated_pure'])
        and prediction['hard']['predicted_fractions'] == exact_json(predicted)
        and prediction['hard']['predicted_utility_fraction'] == str(utility(predicted, 'goal'))
        and equal_numbers(prediction['hard'], dict(predicted=[float(x) for x in predicted], predicted_utility=float(utility(predicted, 'goal'))))
        and result['hard']['actual_fractions'] == exact_json(actual)
        and result['hard']['actual_utility_fraction'] == str(utility(actual, 'goal'))
        and result['hard']['violation'] == (violation > 0) and result['hard']['violation_fraction'] == str(violation)
        and equal_numbers(result['hard'], dict(actual=[float(x) for x in actual], actual_utility=float(utility(actual, 'goal')),
                                              violation_magnitude=float(violation))))
    expected['hard_violation'] = violation
    return bool(prediction_ok), bool(result_ok), bool(hard_ok)


def analyze(directory=OUTPUT):
    begun = perf_counter(); work = Counter(); checks = []; complete = False
    def check(name, passed):
        checks.append(dict(name=name, passed=bool(passed)))
    try:
        def read(name):
            payload = json.loads((directory / name).read_text())
            work['input_files_read'] += 1
            return payload
        cases, batches, snapshots, results = (read(name) for name in
            ('cases.json', 'batches.json', 'snapshots.json', 'results.json'))
        summary, run, manifest = (read(name) for name in ('summary.json', 'run.json', 'source_manifest.json'))
        check('fixed_context_roster', cases == route.roster())
        check('twelve_lifecycles', [(row['life'], row['seed']) for row in batches['lifecycles']]
              == [(life, 202000 + life) for life in range(12)])
        snapshot_index = {(row['life'], row['checkpoint']): row for row in snapshots['checkpoints']}
        result_index = {(row['life'], row['checkpoint'], row['context_id'], row['arm']): row for row in results['records']}
        check('retained_record_rosters', len(snapshot_index) == len(snapshots['checkpoints']) == 84
              and len(result_index) == len(results['records']) == 1560)
        lives = []
        for saved_life in batches['lifecycles']:
            life, seed = saved_life['life'], saved_life['seed']
            regenerated = sample_batches(seed, work)
            check(f'life_{life}_draws', saved_life['batches'] == regenerated)
            prefix, current, frozen, position = [], {}, None, 0
            model_ok = prediction_ok = result_ok = hard_ok = True
            reconstructed = dict(models={}, evaluations={})
            for checkpoint in CHECKPOINTS:
                if checkpoint in ('SOURCE', 'NEW_COST128', 'NEW_WEATHER64', 'NEW_WEATHER256'):
                    records = saved_life['batches'][position]['records']; position += 1; prefix.extend(records)
                    current = {arm: rebuild_model(records if arm == 'RESET' else prefix, arm,
                               frozen=frozen if arm == 'FROZEN' else None, work=work) for arm in ARMS}
                    if checkpoint == 'SOURCE':
                        frozen = current['FROZEN']
                elif checkpoint.endswith('_ZERO'):
                    current = dict(current); current['RESET'] = rebuild_model([], 'RESET', work=work)
                snapshot = snapshot_index[life, checkpoint]
                probes = probe_contexts(checkpoint)
                model_ok &= (snapshot['seed'] == seed and snapshot['context_ids'] == [case['id'] for case in probes]
                             and set(snapshot['models']) == set(ARMS)
                             and all(model_matches(snapshot['models'][arm], current[arm]) for arm in ARMS))
                reconstructed['models'][checkpoint] = dict(current)
                reconstructed['evaluations'][checkpoint] = {arm: [] for arm in ARMS}
                prediction_index = {(row['context_id'], row['arm']): row for row in snapshot['predictions']}
                prediction_ok &= len(prediction_index) == len(snapshot['predictions']) == len(probes) * len(ARMS)
                for case in probes:
                    for arm in ARMS:
                        expected = reconstruct_choice(current[arm], case, work)
                        flags = certify_choice(prediction_index[case['id'], arm],
                            result_index[life, checkpoint, case['id'], arm], expected)
                        prediction_ok &= flags[0]; result_ok &= flags[1]; hard_ok &= flags[2]
                        reconstructed['evaluations'][checkpoint][arm].append(expected)
            for name, flag in (('prefix_models', model_ok), ('point_plans', prediction_ok),
                               ('own_joint_results', result_ok), ('hard_diagnostics', hard_ok)):
                check(f'life_{life}_{name}', flag)
            lives.append(reconstructed)
        expected_summary = independent_summary(lives, work)
        check('summary_and_shared_lifecycle_bootstrap', equal_numbers(summary, expected_summary))
        check('completed_summary', summary['complete'] and summary['lifecycles'] == 12
              and summary['controlled_draws'] == 64512)
        check('source_manifest', len(manifest) == 9 and all((directory / 'source_code' / row['path']).is_file()
                                                        for row in manifest))
        check('complete_run', run['status'] == 'complete')
        phases = [('protocol_frozen', None, None, 0), ('roster_frozen', None, None, 0)]
        for life in range(12):
            draw_count = life * 5376
            for checkpoint in CHECKPOINTS:
                acquired = dict(SOURCE=1536, NEW_COST128=768, NEW_WEATHER64=768, NEW_WEATHER256=2304).get(checkpoint, 0)
                if acquired:
                    draw_count += acquired; phases.append(('acquired', life, checkpoint, draw_count))
                phases.extend([(phase, life, checkpoint, draw_count)
                               for phase in ('checkpoint_frozen', 'checkpoint_evaluated')])
        phases.append(('complete', None, None, 64512))
        check('freeze_before_scoring_chronology', [(row['phase'], row.get('life'), row.get('checkpoint'), row['controlled_samples'])
                                                 for row in run['phase_history']] == phases)
        costs = run['costs']
        check('controlled_acquisition_and_learning_ledger', set(costs) ==
              {'roster', 'acquisition', 'learning', 'prediction', 'oracle', 'evaluation', 'bootstrap'}
              and all(costs['acquisition'][name] == 64512 for name in
                      ('controlled_samples', 'controlled_resets', 'environment_random_draws', 'observed_successor_records'))
              and costs['learning']['fit_calls'] == 228 and costs['prediction']['predicted_graph_calls'] == 1560
              and costs['bootstrap'] == {name: work[name] for name in
                  ('bootstrap_index_draws', 'bootstrap_mean_terms', 'bootstrap_resamples')}
              and run['teacher_loads'] == run['random_samples_used_as_oracle_labels'] == run['parameter_solves'] == 0)
        complete = True
    except Exception as error:
        check('independent_reconstruction', False)
        failure = dict(type=type(error).__name__, message=str(error))
    analysis = dict(schema='acfqp.continual_route_kernels.v202.analysis', complete=complete,
                    valid=complete and all(row['passed'] for row in checks), checks=checks,
                    costs=dict(work), seconds=perf_counter() - begun)
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

