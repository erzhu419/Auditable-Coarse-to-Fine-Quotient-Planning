"""Frozen chronological sampling, kernel revision, and own-policy route probes."""
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
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science import continual_route_kernels_v202 as learner
from acfqp.science import structured_route_task_v201 as route

OUTPUT = ROOT / 'reports/continual_route_kernels_v202'
RUNTIME = ROOT / 'reports/v202_runtime_tmp'
ARMS = ('REVISED', 'FULL_CONTEXT', 'FIXED_WEATHER', 'FROZEN', 'RESET')
CHECKPOINTS = ('SOURCE', 'NEW_COST_ZERO', 'NEW_COST128', 'NEW_WEATHER_ZERO',
               'NEW_WEATHER64', 'NEW_WEATHER256', 'FINAL_REUSE')
SOURCE_FILES = (
    'src/acfqp/science/continual_route_kernels_v202.py',
    'src/acfqp/science/structured_route_task_v201.py',
    'scripts/run_continual_route_kernels_v202.py',
    'scripts/analyze_continual_route_kernels_v202.py',
    'tests/test_continual_route_kernels_v202.py',
    'tests/test_continual_route_analysis_v202.py',
    'specs/CONTINUAL_ROUTE_KERNELS_V202.md',
    'reports/v202_runtime_tmp/run_checks.py',
    'reports/v202_runtime_tmp/run_stage.py')
DELTA = Fraction(1, 20)


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(item) for item in value]
    return value


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(exact_json(value), ensure_ascii=False, separators=(',', ':')) + '\n')


def capture_code(output):
    manifest = []
    for relative in SOURCE_FILES:
        target = output / 'source_code' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
        manifest.append(dict(path=relative))
    save(output / 'source_manifest.json', manifest)


def contexts(cases, checkpoint):
    if checkpoint == 'SOURCE':
        return [case for case in cases if case['weather'] == 'normal' and case['operating'] == 'low']
    if checkpoint.startswith('NEW_COST'):
        return [case for case in cases if case['weather'] == 'normal' and case['operating'] == 'high']
    if checkpoint.startswith('NEW_WEATHER'):
        return [case for case in cases if case['weather'] != 'normal' and case['operating'] == 'high']
    return [case for case in cases if case['weather'] == 'normal' or case['operating'] == 'low']


def environment_probabilities(case, operator, work):
    short, detour, failure, recovery, retry = route.WEATHER[case['weather']]
    work['environment_kernel_reads'] += 1
    return {'SHORT_PASS': (short, 1-short), 'DETOUR_PASS': (detour, failure, recovery),
            'RECOVERY_RETRY': (retry, 1-retry)}[operator]


def acquire(rng, cases, checkpoint, number, draw_index, batch, work):
    """Every controlled reset consumes exactly one draw; only events reach fit."""
    events = []
    for case in cases:
        for operator in learner.OPERATORS:
            alphabet = learner.ALPHABETS[operator]
            probabilities = environment_probabilities(case, operator, work)
            record = dict(context=case, operator=operator, counts=dict.fromkeys(alphabet, 0),
                          n=0, phase=checkpoint, draw_start=draw_index, draw_end=draw_index)
            batch['records'].append(record)
            for _ in range(number):
                draw = rng.random(); cumulative = Fraction(0)
                work['controlled_resets'] += 1; work['environment_random_draws'] += 1
                work['controlled_samples'] += 1; draw_index += 1
                for category, probability in zip(alphabet, probabilities):
                    cumulative += probability
                    work['sampling_threshold_accumulations'] += 1
                    work['sampling_threshold_comparisons'] += 1
                    if draw < float(cumulative):
                        record['counts'][category] += 1
                        events.append(dict(context=case, operator=operator, successor=category))
                        work['observed_successor_records'] += 1
                        break
                record['n'] += 1; record['draw_end'] = draw_index
    return events, draw_index


def pure_name(root_action, recovery_action):
    if root_action == 'DETOUR':
        return 'DETOUR_RETRY' if recovery_action == 'RETRY' else 'DETOUR_RETURN'
    return root_action


def predict(model, case, work):
    probabilities = {operator: learner.probabilities(model, case, operator, work)
                     for operator in learner.OPERATORS}
    graph = learner.predicted_graph(model, case, work)
    queries = {}
    for query in route.QUERIES:
        plan = route.plan(graph, 4, query, work)
        root_action = plan['policy']['START', 4]
        recovery_action = plan['policy']['RECOVERY', 2]
        vector = plan['values']['START', 4]
        queries[query] = dict(root_action=root_action, recovery_action=recovery_action,
                             pure_policy=pure_name(root_action, recovery_action),
                             predicted=[float(item) for item in vector], predicted_fractions=vector)
    pure = route.pure_values(graph, 4, work)
    hard = route.hard_constraint(pure, DELTA, work)
    return dict(context_id=case['id'], arm=model['arm'], operator_probabilities=probabilities,
                graph=graph, queries=queries, pure_vectors=pure,
                hard=dict(mix=hard['mix'], predicted=[float(item) for item in hard['vector']],
                          predicted_fractions=hard['vector'], predicted_utility=float(hard['utility']),
                          predicted_utility_fraction=hard['utility']))


def true_reference(case, work):
    graph = route.rows(case, work)
    probabilities = {operator: environment_probabilities(case, operator, work)
                     for operator in learner.OPERATORS}
    oracle = {query: route.plan(graph, 4, query, work) for query in route.QUERIES}
    pure = route.pure_values(graph, 4, work)
    return graph, probabilities, oracle, pure


def score(prediction, reference, life, seed, checkpoint, work):
    graph, true_probabilities, oracle, true_pure = reference
    tv, tv_fractions = {}, {}
    for operator in learner.OPERATORS:
        value = sum((abs(prediction['operator_probabilities'][operator][category]-probability)
                     for category, probability in zip(learner.ALPHABETS[operator], true_probabilities[operator])), Fraction(0))/2
        tv[operator], tv_fractions[operator] = float(value), value
        work['kernel_tv_component_differences'] += len(learner.ALPHABETS[operator])
        work['kernel_tv_sums'] += 1
    queries = {}
    for query, decision in prediction['queries'].items():
        actual = route.evaluate_plan(graph, 4, decision['pure_policy'], work)['root']
        oracle_vector = oracle[query]['values']['START', 4]
        utility = route.utility(actual, query, work)
        oracle_utility = route.utility(oracle_vector, query, work)
        error = [abs(float(predicted-true)) for predicted, true in zip(decision['predicted_fractions'], actual)]
        work['prediction_error_components'] += 3; work['regret_subtractions'] += 1
        queries[query] = dict(actual=[float(item) for item in actual], actual_fractions=actual,
            utility=float(utility), utility_fraction=utility, oracle=[float(item) for item in oracle_vector],
            oracle_fractions=oracle_vector, oracle_utility=float(oracle_utility),
            oracle_utility_fraction=oracle_utility, regret=float(oracle_utility-utility),
            regret_fraction=oracle_utility-utility, abs_prediction_error=error)
    actual_mix = tuple(sum((weight*true_pure[name][component] for name, weight in prediction['hard']['mix']),
                           Fraction(0)) for component in range(3))
    work['actual_mixture_component_products'] += 3*len(prediction['hard']['mix'])
    work['actual_mixture_component_accumulations'] += 3*len(prediction['hard']['mix'])
    violation = max(Fraction(0), actual_mix[1]-DELTA)
    actual_utility = route.utility(actual_mix, 'goal', work)
    return dict(life=life, seed=seed, checkpoint=checkpoint, context_id=prediction['context_id'],
        arm=prediction['arm'], kernel_tv=tv, kernel_tv_fractions=tv_fractions, queries=queries,
        hard=dict(actual=[float(item) for item in actual_mix], actual_fractions=actual_mix,
                  actual_utility=float(actual_utility), actual_utility_fraction=actual_utility,
                  violation=violation > 0, violation_magnitude=float(violation), violation_fraction=violation))


def mean(values):
    values = list(values)
    return sum(values)/len(values)


def metrics(records):
    return dict(tv=mean(mean(row['kernel_tv'].values()) for row in records),
        utility=mean(mean(query['utility'] for query in row['queries'].values()) for row in records),
        regret=mean(mean(query['regret'] for query in row['queries'].values()) for row in records),
        **{name: mean(mean(query['abs_prediction_error'][index] for query in row['queries'].values())
                      for row in records) for index, name in enumerate(('R', 'F', 'S'))})


def paired_bootstrap(contrasts, work):
    rng = random.Random(202900); samples = {name: [] for name in contrasts}
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


def summarize(results, snapshots, cases, work):
    case_map = {case['id']: case for case in cases}
    indexed = {(life, checkpoint, arm): [] for life in range(12) for checkpoint in CHECKPOINTS for arm in ARMS}
    for row in results:
        indexed[row['life'], row['checkpoint'], row['arm']].append(row)
    final, unacquired = {arm: [] for arm in ARMS}, {arm: [] for arm in ARMS}
    contrasts = {name: [] for name in ('zero_tv', 'revision_tv', 'transfer_full', 'transfer_frozen')}
    retained = []; weather_selected = 0
    snapshot_map = {(row['life'], row['checkpoint']): row for row in snapshots}
    for life in range(12):
        for arm in ARMS:
            final[arm].append(metrics(indexed[life, 'NEW_WEATHER256', arm]+indexed[life, 'FINAL_REUSE', arm]))
            heldout = [row for row in indexed[life, 'FINAL_REUSE', arm]
                       if case_map[row['context_id']]['weather'] != 'normal']
            unacquired[arm].append(metrics(heldout))
        contrasts['zero_tv'].append(metrics(indexed[life, 'NEW_COST_ZERO', 'FULL_CONTEXT'])['tv']-
                                    metrics(indexed[life, 'NEW_COST_ZERO', 'REVISED'])['tv'])
        contrasts['revision_tv'].append(unacquired['FROZEN'][-1]['tv']-unacquired['REVISED'][-1]['tv'])
        contrasts['transfer_full'].append(unacquired['REVISED'][-1]['utility']-unacquired['FULL_CONTEXT'][-1]['utility'])
        contrasts['transfer_frozen'].append(unacquired['REVISED'][-1]['utility']-unacquired['FROZEN'][-1]['utility'])
        old = [row for row in indexed[life, 'FINAL_REUSE', 'REVISED']
               if case_map[row['context_id']]['weather'] == 'normal' and case_map[row['context_id']]['operating'] == 'low']
        retained.append(metrics(old)['regret']-metrics(indexed[life, 'SOURCE', 'REVISED'])['regret'])
        weather_selected += snapshot_map[life, 'NEW_WEATHER256']['models']['REVISED']['selected_fields']['SHORT_PASS'] == ['weather']
    bootstrap = paired_bootstrap(contrasts, work)
    final_means = {arm: {metric: mean(row[metric] for row in rows) for metric in ('tv', 'utility', 'regret', 'R', 'F', 'S')}
                   for arm, rows in final.items()}
    revised = final_means['REVISED']
    fixed_gap = revised['regret']-final_means['FIXED_WEATHER']['regret']; retention = mean(retained)
    conditions = dict(
        ZERO_SAMPLE_REUSE=bootstrap['zero_tv']['mean'] > .05 and bootstrap['zero_tv']['ci'][0] > 0,
        CONDITION_REVISION=bootstrap['revision_tv']['mean'] > .02 and bootstrap['revision_tv']['ci'][0] > 0 and weather_selected >= 10,
        POLICY_TRANSFER=all(bootstrap[name]['mean'] > threshold and bootstrap[name]['ci'][0] > 0
                            for name, threshold in (('transfer_full', .05), ('transfer_frozen', .01))),
        QUALITY_RETENTION=revised['tv'] <= .05 and revised['regret'] <= .05
            and all(revised[name] <= .05 for name in ('R', 'F', 'S')) and fixed_gap <= .01 and retention <= .01)
    checkpoint_means, hard_risk = {}, {}
    for checkpoint in CHECKPOINTS:
        checkpoint_means[checkpoint], hard_risk[checkpoint] = {}, {}
        for arm in ARMS:
            life_values = [metrics(indexed[life, checkpoint, arm]) for life in range(12)]
            checkpoint_means[checkpoint][arm] = {metric: mean(row[metric] for row in life_values)
                                                for metric in ('tv', 'utility', 'regret', 'R', 'F', 'S')}
            rows = [row for life in range(12) for row in indexed[life, checkpoint, arm]]
            hard_risk[checkpoint][arm] = dict(evaluations=len(rows), violations=sum(row['hard']['violation'] for row in rows),
                mean_violation=mean(row['hard']['violation_magnitude'] for row in rows),
                max_violation=max(row['hard']['violation_magnitude'] for row in rows))
    return dict(schema='acfqp.continual_route_kernels.v202.summary', complete=True, lifecycles=12,
        controlled_draws=64512, bootstrap=bootstrap, final_means=final_means, weather_selected=weather_selected,
        retention_change=retention, fixed_regret_gap=fixed_gap, conditions=conditions,
        decision='CONDITIONAL_LEARNING_SUPPORTED' if all(conditions.values()) else 'CONDITIONAL_LEARNING_NOT_SUPPORTED',
        checkpoint_means=checkpoint_means, hard_risk=hard_risk, paired_lifecycle_contrasts=contrasts)


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    work = {name: Counter() for name in ('roster', 'acquisition', 'learning', 'prediction', 'oracle', 'evaluation', 'bootstrap')}
    arm_costs = {arm: {stage: Counter() for stage in ('learning', 'prediction', 'evaluation')} for arm in ARMS}
    record = dict(schema='acfqp.continual_route_kernels.v202.run', status='preparing', phase_history=[], costs=work,
        arm_costs=arm_costs,
        teacher_loads=0, random_samples_used_as_oracle_labels=0, parameter_solves=0,
        runtime=dict(python=sys.version.split()[0], executable=sys.executable),
        test_refs=[str(RUNTIME/'test_checks.json')])
    lifecycles, snapshots, results = [], [], []
    current = None

    def arm_operation(arm, stage, operation):
        local = Counter()
        try:
            return operation(local)
        finally:
            work[stage].update(local)
            arm_costs[arm][stage].update(local)

    def phase(name, **details):
        record['status'] = name
        record['phase_history'].append(dict(phase=name, seconds_since_start=perf_counter()-begun,
            controlled_samples=work['acquisition']['controlled_samples'], **details))
        save(output/'run.json', record)

    try:
        capture_code(output); phase('protocol_frozen')
        cases = route.roster(work['roster']); save(output/'cases.json', cases); phase('roster_frozen')
        for life in range(12):
            seed = 202000+life; rng = random.Random(seed); draw_index = 0
            lifecycle = dict(life=life, seed=seed, batches=[]); lifecycles.append(lifecycle)
            history, models = [], {}
            for checkpoint in CHECKPOINTS:
                current = dict(life=life, checkpoint=checkpoint)
                scope = contexts(cases, checkpoint)
                number = {'SOURCE': 256, 'NEW_COST128': 128, 'NEW_WEATHER64': 64, 'NEW_WEATHER256': 192}.get(checkpoint)
                if number is not None:
                    batch = dict(name=checkpoint, records=[]); lifecycle['batches'].append(batch)
                    events, draw_index = acquire(rng, scope, checkpoint, number, draw_index, batch, work['acquisition'])
                    history.append(events); save(output/'batches.json', dict(lifecycles=lifecycles))
                    phase('acquired', life=life, checkpoint=checkpoint)
                    for arm in ARMS:
                        if arm != 'FROZEN' or checkpoint == 'SOURCE':
                            models[arm] = arm_operation(arm, 'learning',
                                lambda local: learner.fit(history, arm, counts=local))
                elif checkpoint.endswith('_ZERO'):
                    models['RESET'] = arm_operation('RESET', 'learning',
                        lambda local: learner.fit([[]], 'RESET', counts=local))
                predictions = [arm_operation(arm, 'prediction',
                    lambda local: predict(models[arm], case, local)) for case in scope for arm in ARMS]
                snapshot = dict(life=life, seed=seed, checkpoint=checkpoint,
                    context_ids=[case['id'] for case in scope], models=dict(models), predictions=predictions)
                snapshots.append(snapshot)
                save(output/'snapshots.json', dict(checkpoints=snapshots))
                phase('checkpoint_frozen', life=life, checkpoint=checkpoint)
                references = {case['id']: true_reference(case, work['oracle']) for case in scope}
                for prediction in predictions:
                    results.append(arm_operation(prediction['arm'], 'evaluation',
                        lambda local: score(prediction, references[prediction['context_id']], life, seed,
                                            checkpoint, local)))
                save(output/'results.json', dict(records=results)); phase('checkpoint_evaluated', life=life, checkpoint=checkpoint)
                print(json.dumps(dict(life=life, checkpoint=checkpoint, draws=draw_index,
                    contexts=len(scope), selected=models['REVISED']['selected_fields']), separators=(',', ':')), flush=True)
            current = None
        summary = summarize(results, snapshots, cases, work['bootstrap'])
        save(output/'summary.json', summary); record['seconds'] = perf_counter()-begun; phase('complete')
        print(json.dumps(dict(conditions=summary['conditions'], decision=summary['decision']), separators=(',', ':')), flush=True)
        return record
    except Exception as error:
        record.update(status='failed', seconds=perf_counter()-begun,
                      failure=dict(type=type(error).__name__, message=str(error), current=current))
        save(output/'batches.json', dict(lifecycles=lifecycles))
        save(output/'snapshots.json', dict(checkpoints=snapshots)); save(output/'results.json', dict(records=results))
        save(output/'run.json', record)
        raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
