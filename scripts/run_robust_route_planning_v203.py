"""Frozen-evidence whole-policy risk planning and subsequent true evaluation."""
import argparse
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import robust_route_planning_v203 as core
from acfqp.science import structured_route_task_v201 as route

OUTPUT = ROOT/'reports/robust_route_planning_v203'
INPUT = ROOT/'reports/continual_route_kernels_v202'
RUNTIME = ROOT/'reports/v203_runtime_tmp'
ARMS = ('PLUGIN', 'REVISED_ROBUST', 'FULL_ROBUST', 'POOLED_ABLATION')
INPUT_NAMES = ('cases.json', 'batches.json', 'snapshots.json')
SOURCE_FILES = (
    'src/acfqp/science/robust_route_planning_v203.py',
    'src/acfqp/science/structured_route_task_v201.py',
    'scripts/run_robust_route_planning_v203.py',
    'scripts/analyze_robust_route_planning_v203.py',
    'tests/test_robust_route_planning_v203.py',
    'tests/test_robust_route_analysis_v203.py',
    'specs/ROBUST_ROUTE_PLANNING_V203.md',
    'reports/v203_runtime_tmp/run_checks.py',
    'reports/v203_runtime_tmp/run_stage.py')
DELTA = Fraction(1, 20)


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [exact_json(item) for item in value]
    return value


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(exact_json(value), ensure_ascii=False, separators=(',', ':'))+'\n')


def capture_code(output):
    manifest = []
    for relative in SOURCE_FILES:
        target = output/'source_code'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, target)
        manifest.append(dict(path=relative))
    save(output/'source_manifest.json', manifest)


def capture_inputs(output, work):
    manifest = []
    for name in INPUT_NAMES:
        payload = (INPUT/name).read_bytes()
        (output/'inputs').mkdir(parents=True, exist_ok=True)
        (output/'inputs'/name).write_bytes(payload)
        work['input_files_copied'] += 1; work['input_bytes'] += len(payload)
        manifest.append(dict(name=name, source=str(INPUT/name), bytes=len(payload)))
    save(output/'input_manifest.json', manifest)


def observed_contexts(batches, work):
    observed = {}
    for lifecycle in batches['lifecycles']:
        totals = Counter()
        for batch in lifecycle['batches']:
            for record in batch['records']:
                for count in record['counts'].values():
                    totals[record['context']['id']] += count
                    work['retained_count_accumulations'] += 1
                work['retained_operator_records'] += 1
        observed[lifecycle['life']] = {context for context, number in totals.items() if number > 0}
    return observed


def point_vectors(prediction, work):
    vectors = {name: tuple(Fraction(value) for value in vector)
               for name, vector in prediction['pure_vectors'].items()}
    work['retained_point_vector_components'] += 3*len(vectors)
    return vectors


def plugin_plan(prediction, vectors, work):
    mix = [(name, Fraction(weight)) for name, weight in prediction['hard']['mix']]
    predicted = tuple(sum((weight*vectors[name][component] for name, weight in mix), Fraction(0))
                      for component in range(3))
    work['predicted_mixture_component_products'] += 3*len(mix)
    work['predicted_mixture_component_accumulations'] += 3*len(mix)
    return dict(envelopes=None, risks=None, mix=mix, predicted=predicted,
                predicted_utility=route.utility(predicted, 'goal', work), risk_upper=None, candidates=None)


def make_plan(life, case, observed, arm, models, predictions, work):
    point_arm = 'FULL_CONTEXT' if arm == 'FULL_ROBUST' else 'REVISED'
    prediction = predictions[case['id'], point_arm]
    vectors = point_vectors(prediction, work)
    if arm == 'PLUGIN':
        decision = plugin_plan(prediction, vectors, work)
    else:
        envelope = core.envelopes(models['REVISED'], case, pooled=arm == 'POOLED_ABLATION', work=work)
        risks = core.risk_bounds(envelope, work=work)
        decision = core.optimize(vectors, risks, DELTA, work=work)
        decision.update(envelopes=envelope, risks=risks)
    return dict(life=life, context_id=case['id'], observed=observed, arm=arm,
                pure_vectors=vectors, **decision)


def true_probabilities(case, work):
    short, detour, failure, recovery, retry = route.WEATHER[case['weather']]
    work['true_kernel_reads'] += 1
    return {'SHORT_PASS': {'DELIVERY': short, 'LOST': 1-short},
            'DETOUR_PASS': {'DELIVERY': detour, 'LOST': failure, 'RECOVERY': recovery},
            'RECOVERY_RETRY': {'DELIVERY': retry, 'LOST': 1-retry}}


def reference(case, work):
    graph = route.rows(case, work)
    pure = route.pure_values(graph, 4, work)
    hard = route.hard_constraint(pure, DELTA, work)
    return dict(context_id=case['id'], pure_vectors=pure,
        oracle=dict(mix=hard['mix'], vector=hard['vector'], utility=hard['utility'])), true_probabilities(case, work)


def evaluate(plan, reference, probabilities, work):
    pure, mix = reference['pure_vectors'], plan['mix']
    actual = tuple(sum((weight*pure[name][component] for name, weight in mix), Fraction(0))
                   for component in range(3))
    work['actual_mixture_component_products'] += 3*len(mix)
    work['actual_mixture_component_accumulations'] += 3*len(mix)
    utility = route.utility(actual, 'goal', work)
    excess = max(Fraction(0), actual[1]-DELTA)
    wait = sum((weight for name, weight in mix if name == 'WAIT'), Fraction(0))
    coverage = None
    if plan['envelopes'] is not None:
        comparisons = []
        for operator, envelope in plan['envelopes'].items():
            for category, (lower, upper) in envelope['bounds'].items():
                comparisons.append(lower <= probabilities[operator][category] <= upper)
                work['envelope_coverage_marginals'] += 1
        coverage = all(comparisons)
    work['true_risk_comparisons'] += 1
    work['wait_mass_terms'] += len(mix)
    return dict(life=plan['life'], context_id=plan['context_id'], observed=plan['observed'], arm=plan['arm'],
        actual_fractions=actual, actual=[float(value) for value in actual], actual_utility_fraction=utility,
        actual_utility=float(utility), violation=excess > 0, excess_fraction=excess, excess=float(excess),
        wait_mass_fraction=wait, wait_mass=float(wait), oracle_utility_fraction=reference['oracle']['utility'],
        oracle_utility=float(reference['oracle']['utility']), coverage=coverage)


def mean(values):
    values = list(values)
    return sum(values)/len(values)


def group_metrics(records):
    utility = mean(row['actual_utility'] for row in records)
    oracle = mean(row['oracle_utility'] for row in records)
    return dict(count=len(records), violations=sum(row['violation'] for row in records),
        max_failure=max(row['actual'][1] for row in records), max_excess=max(row['excess'] for row in records),
        utility=utility, oracle_utility=oracle, oracle_ratio=utility/oracle,
        wait_mass=mean(row['wait_mass'] for row in records),
        coverage=None if records[0]['coverage'] is None else mean(row['coverage'] for row in records))


def bootstrap(contrasts, work):
    rng = random.Random(203900); samples = {name: [] for name in contrasts}
    for _ in range(5000):
        indices = [rng.randrange(12) for _ in range(12)]
        work['bootstrap_index_draws'] += 12
        for name, values in contrasts.items():
            samples[name].append(sum(values[index] for index in indices)/12)
            work['bootstrap_mean_terms'] += 12
    result = {}
    for name, values in contrasts.items():
        ordered = sorted(samples[name])
        result[name] = dict(mean=mean(values), ci=[ordered[124], ordered[4874]])
    work['bootstrap_resamples'] += 5000
    return result


def summarize(plans, results, work):
    groups = {group: {} for group in ('all', 'observed', 'unobserved')}
    for group in groups:
        for arm in ARMS:
            rows = [row for row in results if row['arm'] == arm
                    and (group == 'all' or row['observed'] == (group == 'observed'))]
            groups[group][arm] = group_metrics(rows)
    contrasts = {name: [] for name in ('supported_minus_half_oracle', 'observed_minus_full',
                                      'unobserved_minus_full', 'unobserved_minus_half_oracle')}
    for life in range(12):
        metrics = {}
        for observed in (True, False):
            for arm in ('REVISED_ROBUST', 'FULL_ROBUST'):
                metrics[observed, arm] = group_metrics([row for row in results
                    if row['life'] == life and row['arm'] == arm and row['observed'] == observed])
        known, unknown = metrics[True, 'REVISED_ROBUST'], metrics[False, 'REVISED_ROBUST']
        contrasts['supported_minus_half_oracle'].append(known['utility']-.5*known['oracle_utility'])
        contrasts['observed_minus_full'].append(known['utility']-metrics[True, 'FULL_ROBUST']['utility'])
        contrasts['unobserved_minus_full'].append(unknown['utility']-metrics[False, 'FULL_ROBUST']['utility'])
        contrasts['unobserved_minus_half_oracle'].append(unknown['utility']-.5*unknown['oracle_utility'])
    intervals = bootstrap(contrasts, work)
    conditions = dict(RISK=all(row['risk_upper'] <= DELTA for row in plans if row['arm'] == 'REVISED_ROBUST')
        and not any(row['violation'] for row in results if row['arm'] == 'REVISED_ROBUST'),
        SUPPORTED_UTILITY=intervals['supported_minus_half_oracle']['mean'] > 0
            and intervals['supported_minus_half_oracle']['ci'][0] > 0)
    unknown = [row for row in results if row['arm'] == 'REVISED_ROBUST' and not row['observed']]
    return dict(schema='acfqp.robust_route_planning.v203.summary', complete=True, groups=groups,
        paired_lifecycle_contrasts=contrasts, bootstrap=intervals, conditions=conditions,
        decision='RISK_PLANNING_SUPPORTED' if all(conditions.values()) else 'RISK_PLANNING_NOT_SUPPORTED',
        unknown_information_boundary=dict(contexts=len(unknown), action_mass_cap=.05, utility_cap=.2,
            max_action_mass=max(float(1-row['wait_mass_fraction']) for row in unknown),
            max_true_utility=max(row['actual_utility'] for row in unknown)))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    costs = {stage: Counter() for stage in ('io', 'shared_counts', 'planning', 'oracle', 'evaluation', 'bootstrap')}
    arm_costs = {arm: {stage: Counter() for stage in ('planning', 'evaluation')} for arm in ARMS}
    run_record = dict(schema='acfqp.robust_route_planning.v203.run', status='preparing', phase_history=[],
        costs=costs, arm_costs=arm_costs, fit_calls=0, samples=0, controlled_resets=0,
        test_refs=[str(RUNTIME/'test_checks.json')], runtime=dict(python=sys.version.split()[0], executable=sys.executable))
    plans, results, references = [], [], []
    current = None

    def phase(name):
        run_record['status'] = name
        run_record['phase_history'].append(dict(phase=name, seconds_since_start=perf_counter()-begun,
            plan_count=len(plans), result_count=len(results), samples=0, fit_calls=0))
        save(output/'run.json', run_record)

    def arm_operation(arm, stage, operation):
        local = Counter()
        try:
            return operation(local)
        finally:
            costs[stage].update(local); arm_costs[arm][stage].update(local)

    try:
        capture_code(output); capture_inputs(output, costs['io']); phase('inputs_frozen')
        prior = json.loads((INPUT/'analysis.json').read_text())
        if not prior['valid'] or not prior['complete']:
            raise ValueError('V202 independent audit must be complete and valid')
        run_record['prerequisite'] = dict(path=str(INPUT/'analysis.json'), valid=True, complete=True)
        loaded = {name: json.loads((output/'inputs'/name).read_bytes()) for name in INPUT_NAMES}
        cases, batches, snapshots = loaded['cases.json'], loaded['batches.json'], loaded['snapshots.json']
        observed = observed_contexts(batches, costs['shared_counts'])
        snapshot_map = {(row['life'], row['checkpoint']): row for row in snapshots['checkpoints']}
        for life in range(12):
            models = snapshot_map[life, 'FINAL_REUSE']['models']
            predictions = {(row['context_id'], row['arm']): row
                           for row in snapshot_map[life, 'NEW_WEATHER256']['predictions']}
            predictions.update({(row['context_id'], row['arm']): row
                                for row in snapshot_map[life, 'FINAL_REUSE']['predictions']})
            for case in cases:
                for arm in ARMS:
                    current = dict(life=life, context_id=case['id'], arm=arm)
                    plans.append(arm_operation(arm, 'planning',
                        lambda local: make_plan(life, case, case['id'] in observed[life], arm, models, predictions, local)))
        save(output/'plans.json', dict(records=plans)); phase('all_plans_frozen')
        reference_map, probability_map = {}, {}
        for case in cases:
            saved, probabilities = reference(case, costs['oracle'])
            references.append(saved); reference_map[case['id']], probability_map[case['id']] = saved, probabilities
        save(output/'reference.json', dict(records=references))
        for plan in plans:
            current = dict(life=plan['life'], context_id=plan['context_id'], arm=plan['arm'])
            results.append(arm_operation(plan['arm'], 'evaluation', lambda local:
                evaluate(plan, reference_map[plan['context_id']], probability_map[plan['context_id']], local)))
        save(output/'results.json', dict(records=results)); phase('oracle_evaluated')
        summary = summarize(plans, results, costs['bootstrap']); save(output/'summary.json', summary)
        run_record['seconds'] = perf_counter()-begun; current = None; phase('complete')
        print(json.dumps(dict(conditions=summary['conditions'], decision=summary['decision'],
            observed=summary['groups']['observed']['REVISED_ROBUST'],
            unobserved=summary['groups']['unobserved']['REVISED_ROBUST']), separators=(',', ':')), flush=True)
        return run_record
    except Exception as error:
        run_record.update(status='failed', seconds=perf_counter()-begun,
            failure=dict(type=type(error).__name__, message=str(error), current=current))
        save(output/'plans.json', dict(records=plans)); save(output/'results.json', dict(records=results))
        save(output/'reference.json', dict(records=references)); save(output/'run.json', run_record)
        raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
