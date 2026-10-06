"""Independent full-context envelopes and complete-policy robust-plan audit.

No V203 producer mathematics is imported.  Raw V202 sufficient counts define
the confidence family; selected fields are used only for the pooled ablation.
Point R/F/S, risk bounds and actual R/F/S remain separate throughout.
"""
import argparse
from collections import Counter
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

OUTPUT = ROOT / 'reports/robust_route_planning_v203'
FIELDS = ('operating', 'retry_cost', 'weather')
OPERATORS = ('SHORT_PASS', 'DETOUR_PASS', 'RECOVERY_RETRY')
SUPPORT = {'SHORT_PASS': ('DELIVERY', 'LOST'), 'DETOUR_PASS': ('DELIVERY', 'LOST', 'RECOVERY'),
           'RECOVERY_RETRY': ('DELIVERY', 'LOST')}
ARMS = ('PLUGIN', 'REVISED_ROBUST', 'FULL_ROBUST', 'POOLED_ABLATION')
GRID = 2 ** 40
BETA = math.log(2 * 84 / .05)
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


def bernoulli_kl(x, p):
    if x == 0:
        return math.inf if p == 1 else -math.log1p(-p)
    if x == 1:
        return math.inf if p == 0 else -math.log(p)
    if p in (0, 1):
        return math.inf
    return x * math.log(x / p) + (1 - x) * math.log((1 - x) / (1 - p))


def interval(k, n, work=None):
    work = Counter() if work is None else work
    work['interval_calls'] += 1
    if not n:
        return Fraction(0), Fraction(1)
    x = k / n
    if k:
        lo, hi = 0., x
        for _ in range(64):
            midpoint = (lo + hi) / 2
            if n * bernoulli_kl(x, midpoint) <= BETA:
                hi = midpoint
            else:
                lo = midpoint
            work['kl_evaluations'] += 1
        lower = Fraction(math.floor(lo * GRID), GRID)
    else:
        lower = Fraction(0)
    if k < n:
        lo, hi = x, 1.
        for _ in range(64):
            midpoint = (lo + hi) / 2
            if n * bernoulli_kl(x, midpoint) <= BETA:
                lo = midpoint
            else:
                hi = midpoint
            work['kl_evaluations'] += 1
        upper = Fraction(math.ceil(hi * GRID), GRID)
    else:
        upper = Fraction(1)
    work['outward_grid_endpoints'] += 2
    return lower, upper


def projection(case, fields=FIELDS):
    return tuple(case[field] for field in fields)


def raw_tables(lifecycle, work=None):
    work = Counter() if work is None else work
    grouped = {operator: {} for operator in OPERATORS}
    for batch in lifecycle['batches']:
        for record in batch['records']:
            operator, key = record['operator'], projection(record['context'])
            table = grouped[operator]
            if key not in table:
                table[key] = dict(context=dict(record['context']), counts=dict.fromkeys(SUPPORT[operator], 0))
            for category in SUPPORT[operator]:
                table[key]['counts'][category] += record['counts'][category]
                work['raw_count_accumulations'] += 1
    return {operator: [records[key] for key in sorted(records)] for operator, records in grouped.items()}


def make_envelopes(tables, case, fields_by_operator=None, work=None):
    work = Counter() if work is None else work
    result = {}
    for operator in OPERATORS:
        fields = FIELDS if fields_by_operator is None else fields_by_operator[operator]
        counts = dict.fromkeys(SUPPORT[operator], 0)
        for record in tables[operator]:
            work['envelope_context_scans'] += 1
            if projection(record['context'], fields) == projection(case, fields):
                for category in SUPPORT[operator]:
                    counts[category] += record['counts'][category]
                    work['envelope_count_accumulations'] += 1
        n = sum(counts.values())
        result[operator] = dict(n=n, counts=counts,
            bounds={category: interval(counts[category], n, work) for category in SUPPORT[operator]})
    return result


def risks(envelopes, work=None):
    work = Counter() if work is None else work
    short, detour, retry = (envelopes[operator]['bounds'] for operator in OPERATORS)
    s = min(short['LOST'][1], 1 - short['DELIVERY'][0])
    q = min(retry['LOST'][1], 1 - retry['DELIVERY'][0])
    f = min(detour['LOST'][1], 1 - detour['DELIVERY'][0] - detour['RECOVERY'][0])
    r = min(detour['RECOVERY'][1], 1 - detour['DELIVERY'][0] - f)
    work['common_worst_kernel_constructions'] += 1
    return dict(WAIT=Fraction(0), SHORT=s, DETOUR_RETURN=f, DETOUR_RETRY=f + r * q)


def point_vectors(model, case, work=None):
    work = Counter() if work is None else work
    laws = {}
    for operator in OPERATORS:
        fields = model['selected_fields'][operator]; counts = dict.fromkeys(SUPPORT[operator], 0)
        for row in model['tables'][operator]:
            if projection(row['context'], fields) == projection(case, fields):
                for category in SUPPORT[operator]:
                    counts[category] += row['counts'][category]
                    work['point_count_accumulations'] += 1
        n = sum(counts.values()); size = len(counts)
        laws[operator] = {category: Fraction(2 * count + 1, 2 * n + size) for category, count in counts.items()}
    return vectors_from_laws(case, laws)


def vectors_from_laws(case, laws):
    short_cost, detour_cost = route.OPERATING[case['operating']]
    short, detour, retry = (laws[operator] for operator in OPERATORS)
    mass = detour['RECOVERY']; retry_cost = Fraction(case['retry_cost'])
    return dict(WAIT=ZERO, SHORT=(-short_cost, short['LOST'], short['DELIVERY']),
        DETOUR_RETURN=(-detour_cost, detour['LOST'], detour['DELIVERY']),
        DETOUR_RETRY=(-detour_cost - mass * retry_cost,
                      detour['LOST'] + mass * retry['LOST'], detour['DELIVERY'] + mass * retry['DELIVERY']))


def goal(vector):
    return vector[0] + 4 * vector[2]


def joint(mix, pure, work=None):
    work = Counter() if work is None else work
    work['mixture_component_products'] += 3 * len(mix)
    return tuple(sum((Fraction(weight) * pure[name][component] for name, weight in mix), Fraction(0))
                 for component in range(3))


def optimize(pure, upper, work=None):
    """Exact feasible-vertex/crossing-edge LP with original point objective."""
    work = Counter() if work is None else work
    names = sorted(pure); candidates = []
    def candidate(mix):
        predicted = joint(mix, pure, work)
        bound = sum((weight * upper[name] for name, weight in mix), Fraction(0))
        return dict(mix=mix, predicted=predicted, predicted_utility=goal(predicted), risk_upper=bound)
    for name in names:
        work['pure_feasibility_checks'] += 1
        if upper[name] <= DELTA:
            candidates.append(candidate([(name, Fraction(1))]))
    for left, right in combinations(names, 2):
        work['crossing_pair_checks'] += 1
        a, b = upper[left], upper[right]
        if min(a, b) < DELTA < max(a, b):
            weight = (DELTA - b) / (a - b)
            candidates.append(candidate([(left, weight), (right, 1 - weight)]))
    best = min(candidates, key=lambda row: (-row['predicted_utility'], row['mix']))
    return dict(best, candidates=candidates)


def true_laws(case):
    short, detour, failure, recovery, retry = route.WEATHER[case['weather']]
    return {'SHORT_PASS': dict(DELIVERY=short, LOST=1 - short),
            'DETOUR_PASS': dict(DELIVERY=detour, LOST=failure, RECOVERY=recovery),
            'RECOVERY_RETRY': dict(DELIVERY=retry, LOST=1 - retry)}


def covered(envelopes, laws):
    return all(envelopes[operator]['bounds'][category][0] <= probability <=
               envelopes[operator]['bounds'][category][1]
               for operator, probabilities in laws.items() for category, probability in probabilities.items())


def score_mix(mix, pure, oracle_utility, envelopes, laws, work=None):
    actual = joint(mix, pure, work); failure = actual[1]; excess = max(Fraction(0), failure - DELTA)
    wait_mass = sum((Fraction(weight) for name, weight in mix if name == 'WAIT'), Fraction(0))
    return dict(actual_fractions=exact_json(actual), actual=[float(x) for x in actual],
        actual_utility_fraction=str(goal(actual)), actual_utility=float(goal(actual)),
        violation=failure > DELTA, excess_fraction=str(excess), excess=float(excess),
        wait_mass_fraction=str(wait_mass), wait_mass=float(wait_mass), oracle_utility_fraction=str(oracle_utility),
        oracle_utility=float(oracle_utility), coverage=None if envelopes is None else covered(envelopes, laws))


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


def group_metrics(rows):
    utility = mean(row['actual_utility'] for row in rows)
    oracle = mean(row['oracle_utility'] for row in rows)
    return dict(count=len(rows), violations=sum(row['violation'] for row in rows),
        max_failure=max(row['actual'][1] for row in rows), max_excess=max(row['excess'] for row in rows),
        utility=utility, oracle_utility=oracle, oracle_ratio=utility / oracle,
        wait_mass=mean(row['wait_mass'] for row in rows),
        coverage=None if rows[0]['coverage'] is None else mean(row['coverage'] for row in rows))


def bootstrap(contrasts, work=None):
    work = Counter() if work is None else work
    size = len(next(iter(contrasts.values()))); rng = random.Random(203900)
    samples = {name: [] for name in contrasts}
    for _ in range(5000):
        indices = [rng.randrange(size) for _ in range(size)]
        for name, values in contrasts.items():
            samples[name].append(sum(values[index] for index in indices) / size)
        work['bootstrap_index_draws'] += size
        work['bootstrap_mean_terms'] += size * len(contrasts)
    work['bootstrap_resamples'] += 5000
    result = {}
    for name, values in samples.items():
        ordered = sorted(values)
        result[name] = dict(mean=mean(contrasts[name]), ci=[ordered[124], ordered[4874]])
    return result


def summarize(plans, records, work=None):
    work = Counter() if work is None else work
    groups = {}
    for group in ('all', 'observed', 'unobserved'):
        groups[group] = {arm: group_metrics([row for row in records if row['arm'] == arm
            and (group == 'all' or row['observed'] == (group == 'observed'))]) for arm in ARMS}
    contrasts = {name: [] for name in ('supported_minus_half_oracle', 'observed_minus_full',
                                      'unobserved_minus_full', 'unobserved_minus_half_oracle')}
    for life in range(12):
        cells = {(observed, arm): group_metrics([row for row in records
                    if row['life'] == life and row['observed'] == observed and row['arm'] == arm])
                 for observed in (True, False) for arm in ('REVISED_ROBUST', 'FULL_ROBUST')}
        known, unknown = cells[True, 'REVISED_ROBUST'], cells[False, 'REVISED_ROBUST']
        contrasts['supported_minus_half_oracle'].append(known['utility'] - .5 * known['oracle_utility'])
        contrasts['observed_minus_full'].append(known['utility'] - cells[True, 'FULL_ROBUST']['utility'])
        contrasts['unobserved_minus_full'].append(unknown['utility'] - cells[False, 'FULL_ROBUST']['utility'])
        contrasts['unobserved_minus_half_oracle'].append(unknown['utility'] - .5 * unknown['oracle_utility'])
    intervals = bootstrap(contrasts, work)
    revised = [row for row in plans if row['arm'] == 'REVISED_ROBUST']
    outcomes = [row for row in records if row['arm'] == 'REVISED_ROBUST']
    conditions = dict(RISK=all(row['risk_upper'] <= DELTA for row in revised)
        and not any(row['violation'] for row in outcomes), SUPPORTED_UTILITY=
        intervals['supported_minus_half_oracle']['mean'] > 0 and intervals['supported_minus_half_oracle']['ci'][0] > 0)
    unknown = [row for row in outcomes if not row['observed']]
    return dict(schema='acfqp.robust_route_planning.v203.summary', complete=True, groups=groups,
        paired_lifecycle_contrasts=contrasts, bootstrap=intervals, conditions=conditions,
        decision='RISK_PLANNING_SUPPORTED' if all(conditions.values()) else 'RISK_PLANNING_NOT_SUPPORTED',
        unknown_information_boundary=dict(contexts=len(unknown), action_mass_cap=.05, utility_cap=.2,
            max_action_mass=max(float(1 - Fraction(row['wait_mass_fraction'])) for row in unknown),
            max_true_utility=max(row['actual_utility'] for row in unknown)))


def expected_plan(life, case, observed, arm, models, tables, point, retained, work=None):
    work = Counter() if work is None else work
    pure = point['FULL_CONTEXT' if arm == 'FULL_ROBUST' else 'REVISED']
    if arm == 'PLUGIN':
        mix = [(name, Fraction(weight)) for name, weight in retained['hard']['mix']]
        predicted = joint(mix, pure, work)
        decision = dict(envelopes=None, risks=None, mix=mix, predicted=predicted,
                        predicted_utility=goal(predicted), risk_upper=None, candidates=None)
    else:
        fields = models['REVISED']['selected_fields'] if arm == 'POOLED_ABLATION' else None
        envelope = make_envelopes(tables, case, fields, work)
        upper = risks(envelope, work)
        decision = dict(optimize(pure, upper, work), envelopes=envelope, risks=upper)
    return dict(life=life, context_id=case['id'], observed=observed, arm=arm, pure_vectors=pure, **decision)


def analyze(directory=OUTPUT):
    begun = perf_counter(); work = Counter(); checks = []; complete = False
    def check(name, passed):
        checks.append(dict(name=name, passed=bool(passed)))
    try:
        def read(relative):
            payload = (directory / relative).read_bytes()
            work['input_files_read'] += 1; work['input_bytes_read'] += len(payload)
            return json.loads(payload)
        cases, batches, snapshots = (read('inputs/' + name) for name in ('cases.json', 'batches.json', 'snapshots.json'))
        saved_plans, saved_results, saved_reference = (read(name)['records'] for name in
                                                     ('plans.json', 'results.json', 'reference.json'))
        saved_summary, run = read('summary.json'), read('run.json')
        manifest, input_manifest = read('source_manifest.json'), read('input_manifest.json')
        check('fixed_cases_and_lifecycles', cases == route.roster()
              and [(row['life'], row['seed']) for row in batches['lifecycles']] == [(i, 202000 + i) for i in range(12)])
        snapshot_map = {(row['life'], row['checkpoint']): row for row in snapshots['checkpoints']}
        plan_map = {(row['life'], row['context_id'], row['arm']): row for row in saved_plans}
        result_map = {(row['life'], row['context_id'], row['arm']): row for row in saved_results}
        reference_map = {row['context_id']: row for row in saved_reference}
        check('all_frozen_record_rosters', len(plan_map) == len(saved_plans) == 576
              and len(result_map) == len(saved_results) == 576 and len(reference_map) == len(saved_reference) == 12)
        plans = []; plan_flags = {}
        for lifecycle in batches['lifecycles']:
            life = lifecycle['life']; tables = raw_tables(lifecycle, work)
            models = snapshot_map[life, 'FINAL_REUSE']['models']
            check(f'life_{life}_raw_final_model_tables', all(models[arm]['tables'] == tables
                  for arm in ('REVISED', 'FULL_CONTEXT')))
            retained = {(row['context_id'], row['arm']): row for checkpoint in ('NEW_WEATHER256', 'FINAL_REUSE')
                        for row in snapshot_map[life, checkpoint]['predictions']}
            source_ok = plan_ok = True
            for case in cases:
                point = {arm: point_vectors(models[arm], case, work) for arm in ('REVISED', 'FULL_CONTEXT')}
                source_ok &= all(retained[case['id'], arm]['pure_vectors'] == exact_json(point[arm])
                                 for arm in point)
                observed = any(projection(row['context']) == projection(case) and sum(row['counts'].values()) > 0
                               for row in tables['SHORT_PASS'])
                for arm in ARMS:
                    expected = expected_plan(life, case, observed, arm, models, tables, point,
                                             retained[case['id'], 'REVISED'], work)
                    plan_ok &= plan_matches(plan_map[life, case['id'], arm], expected)
                    plans.append(expected)
            check(f'life_{life}_unchanged_point_predictions', source_ok)
            check(f'life_{life}_intervals_common_kernel_exact_optimum', plan_ok)
            plan_flags[life] = True
        # Only after reconstructing all plans do private true laws enter scoring.
        references, laws_map = {}, {}
        reference_ok = True
        for case in cases:
            laws = true_laws(case); pure = vectors_from_laws(case, laws)
            hard = optimize(pure, {name: vector[1] for name, vector in pure.items()}, work)
            reference = dict(context_id=case['id'], pure_vectors=pure,
                             oracle=dict(mix=hard['mix'], vector=hard['predicted'], utility=hard['predicted_utility']))
            reference_ok &= plan_matches(reference_map[case['id']], reference)
            references[case['id']], laws_map[case['id']] = reference, laws
            work['true_reference_contexts'] += 1
        check('true_joint_reference_and_hard_oracle', reference_ok)
        results = []; bound_implication = unknown_boundary = True
        for plan in plans:
            reference = references[plan['context_id']]; laws = laws_map[plan['context_id']]
            scored = score_mix(plan['mix'], reference['pure_vectors'], reference['oracle']['utility'], plan['envelopes'], laws, work)
            expected = dict(life=plan['life'], context_id=plan['context_id'], observed=plan['observed'], arm=plan['arm'], **scored)
            key = plan['life'], plan['context_id'], plan['arm']
            plan_flags[plan['life']] &= equal_numbers(result_map[key], expected)
            if plan['envelopes'] is not None and scored['coverage']:
                bound_implication &= Fraction(scored['actual_fractions'][1]) <= plan['risk_upper']
            if plan['arm'] in ('REVISED_ROBUST', 'FULL_ROBUST') and not plan['observed']:
                unknown_boundary &= (all(value == 1 for name, value in plan['risks'].items() if name != 'WAIT')
                    and 1 - Fraction(scored['wait_mass_fraction']) <= DELTA
                    and Fraction(scored['actual_utility_fraction']) <= Fraction(1, 5) and scored['coverage'])
            results.append(expected)
        for life, flag in plan_flags.items():
            check(f'life_{life}_own_joint_results_and_coverage', flag)
        check('covered_kernel_implies_whole_mix_risk_bound', bound_implication)
        check('unknown_simplex_information_boundary', unknown_boundary)
        expected_summary = summarize(plans, results, work)
        check('groups_shared_lifecycle_bootstrap_and_two_conditions', equal_numbers(saved_summary, expected_summary))
        phases = [(row['phase'], row['plan_count'], row['result_count'], row['samples'], row['fit_calls'])
                  for row in run['phase_history']]
        check('all_decisions_frozen_before_private_oracle', phases == [
            ('inputs_frozen', 0, 0, 0, 0), ('all_plans_frozen', 576, 0, 0, 0),
            ('oracle_evaluated', 576, 576, 0, 0), ('complete', 576, 576, 0, 0)]
            and run['status'] == 'complete' and run['fit_calls'] == run['samples'] == run['controlled_resets'] == 0
            and run['prerequisite']['valid'] and run['prerequisite']['complete'])
        sums = {stage: Counter() for stage in ('planning', 'evaluation')}
        for arm in ARMS:
            for stage in sums:
                sums[stage].update(run['arm_costs'][arm][stage])
        check('separate_arm_paid_work', all(dict(counts) == run['costs'][stage] for stage, counts in sums.items())
              and run['costs']['bootstrap'] == {name: work[name] for name in
                  ('bootstrap_index_draws', 'bootstrap_mean_terms', 'bootstrap_resamples')})
        check('retained_source_and_input_manifests', len(manifest) == 9 and len(input_manifest) == 3
              and [row['name'] for row in input_manifest] == ['cases.json', 'batches.json', 'snapshots.json'])
        complete = True
    except Exception as error:
        check('independent_reconstruction', False)
        failure = dict(type=type(error).__name__, message=str(error))
    analysis = dict(schema='acfqp.robust_route_planning.v203.analysis', complete=complete,
                    valid=complete and all(row['passed'] for row in checks), checks=checks, costs=dict(work),
                    seconds=perf_counter() - begun, samples=0, fit_calls=0)
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


