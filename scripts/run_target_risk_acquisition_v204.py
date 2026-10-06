"""Fixed-field knowledge, paired requested samples, and robust stopping."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import target_risk_acquisition_v204 as core
from acfqp.science import continual_route_kernels_v202 as kernels
from acfqp.science import structured_route_task_v201 as route

OUTPUT = ROOT/'reports/target_risk_acquisition_v204'
INPUT = ROOT/'reports/continual_route_kernels_v202'
RUNTIME = ROOT/'reports/v204_runtime_tmp'
ARMS = ('GUIDED', 'UNIFORM', 'NO_SHARE', 'COLD_POLICY')
INPUT_NAMES = ('cases.json', 'batches.json', 'snapshots.json', 'run.json')
SOURCE_FILES = (
    'src/acfqp/science/structured_route_task_v201.py',
    'src/acfqp/science/continual_route_kernels_v202.py',
    'src/acfqp/science/robust_route_planning_v203.py',
    'src/acfqp/science/target_risk_acquisition_v204.py',
    'scripts/run_target_risk_acquisition_v204.py',
    'scripts/analyze_target_risk_acquisition_v204.py',
    'tests/test_target_risk_acquisition_v204.py',
    'tests/test_target_risk_analysis_v204.py',
    'specs/TARGET_RISK_ACQUISITION_V204.md',
    'reports/v204_runtime_tmp/run_checks.py',
    'reports/v204_runtime_tmp/run_stage.py')
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
    path.write_text(json.dumps(exact_json(value), ensure_ascii=False, separators=(',', ':'))+'\n')


def capture(output, work):
    sources = []
    for relative in SOURCE_FILES:
        target = output/'source_code'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, target); sources.append(dict(path=relative))
    save(output/'source_manifest.json', sources)
    inputs = []
    (output/'inputs').mkdir(parents=True, exist_ok=True)
    for name in INPUT_NAMES:
        payload = (INPUT/name).read_bytes(); (output/'inputs'/name).write_bytes(payload)
        inputs.append(dict(name=name, source=str(INPUT/name), bytes=len(payload)))
        work['input_files_copied'] += 1; work['input_bytes'] += len(payload)
    save(output/'input_manifest.json', inputs)


def source_accounting(batches, source_run):
    samples = {str(row['life']): sum(sum(record['counts'].values()) for batch in row['batches']
                                    for record in batch['records']) for row in batches['lifecycles']}
    return dict(samples_per_lifecycle=samples, total_samples=sum(samples.values()),
        inherited_arm_costs={arm: source_run['arm_costs']['FULL_CONTEXT' if arm in ('NO_SHARE', 'COLD_POLICY') else 'REVISED']
                             for arm in ARMS}, inherited_aggregate_costs=source_run['costs'])


def old_decision(life, case, arm, stage, model, work):
    hard = core.make_plan(model, case, work)
    graph = kernels.predicted_graph(model, case, work)
    queries = {}
    for query in route.QUERIES:
        plan = route.plan(graph, 4, query, work)
        root_action, recovery_action = plan['policy']['START', 4], plan['policy']['RECOVERY', 2]
        pure = ('DETOUR_RETRY' if recovery_action == 'RETRY' else 'DETOUR_RETURN') if root_action == 'DETOUR' else root_action
        queries[query] = dict(root_action=root_action, recovery_action=recovery_action,
                             pure_policy=pure, predicted=plan['values']['START', 4])
    return dict(life=life, context_id=case['id'], arm=arm, stage=stage, hard=hard, queries=queries)


def environment_probabilities(case, operator, work):
    short, detour, failure, recovery, retry = route.WEATHER[case['weather']]
    work['environment_kernel_reads'] += 1
    return {'SHORT_PASS': (short, 1-short), 'DETOUR_PASS': (detour, failure, recovery),
            'RECOVERY_RETRY': (retry, 1-retry)}[operator]


def sample(rng, case, operator, batch, work):
    alphabet = kernels.ALPHABETS[operator]
    probabilities = environment_probabilities(case, operator, work)
    for _ in range(core.BATCH):
        draw = rng.random(); cumulative = Fraction(0)
        work['controlled_samples'] += 1; work['controlled_resets'] += 1
        work['environment_random_draws'] += 1
        for category, probability in zip(alphabet, probabilities):
            cumulative += probability
            work['sampling_threshold_accumulations'] += 1; work['sampling_threshold_comparisons'] += 1
            if draw < float(cumulative):
                batch['increments'][category] += 1
                break
        batch['draw_end'] += 1; batch['operator_n'] += 1; batch['spent'] += 1


def true_reference(case, work):
    graph = route.rows(case, work); pure = route.pure_values(graph, 4, work)
    probabilities = {operator: dict(zip(kernels.ALPHABETS[operator], environment_probabilities(case, operator, work)))
                     for operator in kernels.OPERATORS}
    oracle = {query: max(route.utility(vector, query, work) for vector in pure.values()) for query in route.QUERIES}
    return dict(context_id=case['id'], pure_vectors=pure, oracle_utility=oracle), probabilities


def score_hard(plan, reference, probabilities, spent, work):
    vector = tuple(sum((weight*reference['pure_vectors'][name][component] for name, weight in plan['mix']), Fraction(0))
                   for component in range(3))
    work['actual_mixture_component_products'] += 3*len(plan['mix'])
    work['actual_mixture_component_accumulations'] += 3*len(plan['mix'])
    utility = route.utility(vector, 'goal', work); excess = max(Fraction(0), vector[1]-DELTA)
    wait = sum((weight for name, weight in plan['mix'] if name == 'WAIT'), Fraction(0))
    within = []
    for operator, envelope in plan['envelopes'].items():
        for category, (lower, upper) in envelope['bounds'].items():
            within.append(lower <= probabilities[operator][category] <= upper)
            work['envelope_coverage_marginals'] += 1
    return dict(spent=spent, actual_fractions=vector, actual=[float(value) for value in vector],
        actual_utility_fraction=utility, actual_utility=float(utility), risk_upper=plan['risk_upper'],
        utility_lower=plan['utility_lower'], violation=excess > 0, excess_fraction=excess, excess=float(excess),
        coverage=all(within), wait_mass_fraction=wait, wait_mass=float(wait))


def score_target(record, reference, probabilities, work):
    history = [score_hard(record['initial_plan'], reference, probabilities, 0, work)]
    history.extend(score_hard(batch['plan'], reference, probabilities, batch['spent'], work) for batch in record['batches'])
    terminal = dict(history[-1], certified=record['terminal']['stop_reason'] == 'certified',
                    stop_reason=record['terminal']['stop_reason'])
    first = next((row['spent'] for row in history if row['actual_utility_fraction'] >= 2), None)
    return dict(life=record['life'], context_id=record['context_id'], target_index=record['target_index'], arm=record['arm'],
                history=history, terminal=terminal, first_true_utility_ge_2=first)


def score_old(record, reference, probabilities, work):
    queries = {}
    for query, decision in record['queries'].items():
        vector = reference['pure_vectors'][decision['pure_policy']]
        utility = route.utility(vector, query, work); oracle = reference['oracle_utility'][query]
        work['actual_pure_vector_components'] += 3; work['regret_subtractions'] += 1
        queries[query] = dict(actual_fractions=vector, actual=[float(value) for value in vector],
            utility_fraction=utility, utility=float(utility), oracle_utility_fraction=oracle,
            oracle_utility=float(oracle), regret_fraction=oracle-utility, regret=float(oracle-utility))
    return dict(life=record['life'], context_id=record['context_id'], arm=record['arm'], stage=record['stage'],
        hard=score_hard(record['hard'], reference, probabilities, 0, work), queries=queries)


def mean(values):
    values = list(values)
    return sum(values)/len(values)


def bootstrap(contrasts, work):
    rng = random.Random(204900); samples = {name: [] for name in contrasts}
    for _ in range(5000):
        indices = [rng.randrange(12) for _ in range(12)]; work['bootstrap_index_draws'] += 12
        for name, values in contrasts.items():
            samples[name].append(sum(values[index] for index in indices)/12)
            work['bootstrap_mean_terms'] += 12
    result = {}
    for name, values in contrasts.items():
        ordered = sorted(samples[name]); result[name] = dict(mean=mean(values), ci=[ordered[124], ordered[4874]])
    work['bootstrap_resamples'] += 5000
    return result


def summarize(targets, old, work):
    arms, retention = {}, {}
    for arm in ARMS:
        rows = [row for row in targets if row['arm'] == arm]
        history = [item for row in rows for item in row['history']]
        first = [row['first_true_utility_ge_2'] for row in rows if row['first_true_utility_ge_2'] is not None]
        arms[arm] = dict(restored=sum(row['terminal']['certified'] for row in rows),
            total_samples=sum(row['terminal']['spent'] for row in rows), mean_samples=mean(row['terminal']['spent'] for row in rows),
            true_utility=mean(row['terminal']['actual_utility'] for row in rows),
            history_violations=sum(row['violation'] for row in history),
            terminal_violations=sum(row['terminal']['violation'] for row in rows),
            max_failure=max(row['actual'][1] for row in history), max_excess=max(row['excess'] for row in history),
            wait_mass=mean(row['terminal']['wait_mass'] for row in rows), coverage=mean(row['coverage'] for row in history),
            retrospective_true_restored=len(first), mean_first_true_samples=mean(first) if first else None)
        initial = mean(query['regret'] for row in old if row['arm'] == arm and row['stage'] == 'initial' for query in row['queries'].values())
        final = mean(query['regret'] for row in old if row['arm'] == arm and row['stage'] == 'final' for query in row['queries'].values())
        retention[arm] = dict(initial_regret=initial, final_regret=final, regret_change=final-initial)
    contrasts = {name: [] for name in ('uniform_minus_guided_samples', 'no_share_minus_guided_samples',
                                      'guided_minus_uniform_utility', 'guided_minus_no_share_utility',
                                      'cold_policy_minus_guided_samples', 'guided_minus_cold_policy_utility')}
    for life in range(12):
        means = {arm: dict(samples=mean(row['terminal']['spent'] for row in targets if row['life'] == life and row['arm'] == arm),
                           utility=mean(row['terminal']['actual_utility'] for row in targets if row['life'] == life and row['arm'] == arm))
                 for arm in ARMS}
        contrasts['uniform_minus_guided_samples'].append(means['UNIFORM']['samples']-means['GUIDED']['samples'])
        contrasts['no_share_minus_guided_samples'].append(means['NO_SHARE']['samples']-means['GUIDED']['samples'])
        contrasts['guided_minus_uniform_utility'].append(means['GUIDED']['utility']-means['UNIFORM']['utility'])
        contrasts['guided_minus_no_share_utility'].append(means['GUIDED']['utility']-means['NO_SHARE']['utility'])
        contrasts['cold_policy_minus_guided_samples'].append(means['COLD_POLICY']['samples']-means['GUIDED']['samples'])
        contrasts['guided_minus_cold_policy_utility'].append(means['GUIDED']['utility']-means['COLD_POLICY']['utility'])
    intervals = bootstrap(contrasts, work)
    guided_hard = [point for row in targets if row['arm'] == 'GUIDED' for point in row['history']]
    guided_hard.extend(row['hard'] for row in old if row['arm'] == 'GUIDED')
    conditions = dict(RISK=all(row['risk_upper'] <= DELTA and not row['violation'] for row in guided_hard),
        RESTORATION=arms['GUIDED']['restored'] >= 36 and arms['GUIDED']['true_utility'] >= 2,
        ALLOCATION=intervals['uniform_minus_guided_samples']['mean'] >= 16
            and intervals['uniform_minus_guided_samples']['ci'][0] > 0 and arms['GUIDED']['restored'] >= arms['UNIFORM']['restored'],
        KNOWLEDGE=all(intervals[name]['mean'] >= 16 and intervals[name]['ci'][0] > 0
                      for name in ('no_share_minus_guided_samples', 'cold_policy_minus_guided_samples'))
            and all(arms['GUIDED']['restored'] >= arms[arm]['restored'] for arm in ('NO_SHARE', 'COLD_POLICY'))
            and retention['GUIDED']['regret_change'] <= .01)
    return dict(schema='acfqp.target_risk_acquisition.v204.summary', complete=True, targets_per_arm=48,
        arms=arms, retention=retention, paired_lifecycle_contrasts=contrasts, bootstrap=intervals, conditions=conditions,
        decision='TARGET_ACQUISITION_SUPPORTED' if all(conditions.values()) else 'TARGET_ACQUISITION_NOT_SUPPORTED',
        cold_start_reference={arm: dict(source_samples=0, target_samples=arms[arm]['total_samples'])
                              for arm in ('NO_SHARE', 'COLD_POLICY')})


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    stages = ('acquisition', 'update', 'forecast', 'planning', 'retention_planning', 'evaluation')
    costs = {stage: Counter() for stage in (*stages, 'io', 'oracle', 'bootstrap')}
    arm_costs = {arm: {stage: Counter() for stage in stages} for arm in ARMS}
    record = dict(schema='acfqp.target_risk_acquisition.v204.run', status='preparing', phase_history=[], costs=costs,
        arm_costs=arm_costs, fit_calls=0, condition_selections=0, test_refs=[str(RUNTIME/'test_checks.json')],
        runtime=dict(python=sys.version.split()[0], executable=sys.executable))
    histories, old_decisions, final_models, target_results, old_results, references = [], [], [], [], [], []
    current = None

    def phase(name):
        record['status'] = name
        record['phase_history'].append(dict(phase=name, seconds_since_start=perf_counter()-begun,
            target_count=len(histories), old_decision_count=len(old_decisions),
            controlled_samples=costs['acquisition']['controlled_samples'], fit_calls=0, condition_selections=0))
        save(output/'run.json', record)

    def paid(arm, stage, operation):
        local = Counter()
        try:
            return operation(local)
        finally:
            costs[stage].update(local); arm_costs[arm][stage].update(local)

    def save_decisions():
        save(output/'histories.json', dict(records=histories))
        save(output/'old_decisions.json', dict(records=old_decisions))
        save(output/'models.json', dict(lifecycles=final_models))

    try:
        capture(output, costs['io']); phase('inputs_frozen')
        prerequisites = []
        for directory in (INPUT, ROOT/'reports/robust_route_planning_v203'):
            prior = json.loads((directory/'analysis.json').read_text())
            if not prior['valid'] or not prior['complete']:
                raise ValueError('V202 and V203 independent audits must be complete and valid')
            prerequisites.append(dict(path=str(directory/'analysis.json'), valid=True, complete=True))
        record['prerequisites'] = prerequisites
        data = {name: json.loads((output/'inputs'/name).read_bytes()) for name in INPUT_NAMES}
        cases = data['cases.json']; save(output/'source_accounting.json', source_accounting(data['batches.json'], data['run.json']))
        targets = [case for case in cases if case['weather'] != 'normal' and case['operating'] == 'low']
        old_cases = [case for case in cases if case not in targets]
        sources = {row['life']: row['models'] for row in data['snapshots.json']['checkpoints'] if row['checkpoint'] == 'FINAL_REUSE'}
        for life in range(12):
            models = {arm: deepcopy(sources[life]['FULL_CONTEXT' if arm in ('NO_SHARE', 'COLD_POLICY') else 'REVISED']) for arm in ARMS}
            for case in old_cases:
                for arm in ARMS:
                    old_decisions.append(paid(arm, 'retention_planning',
                        lambda work: old_decision(life, case, arm, 'initial', models[arm], work)))
            for target_index, case in enumerate(targets):
                seeds = {op: 204000+(life*4+target_index)*3+index for index, op in enumerate(kernels.OPERATORS)}
                for arm in ARMS:
                    current = dict(life=life, context_id=case['id'], arm=arm)
                    streams = {op: random.Random(seed) for op, seed in seeds.items()}; op_draws = Counter()
                    costs['acquisition']['rng_streams_created'] += 3; arm_costs[arm]['acquisition']['rng_streams_created'] += 3
                    plan = paid(arm, 'planning', lambda work: core.make_plan(models[arm], case, work))
                    history = dict(life=life, context_id=case['id'], target_index=target_index, arm=arm,
                                   seeds=seeds, initial_plan=plan, batches=[])
                    histories.append(history); spent = 0
                    for step in range(core.BUDGET//core.BATCH):
                        if arm == 'UNIFORM':
                            forecast = None
                        elif arm == 'COLD_POLICY':
                            forecast = paid(arm, 'forecast', lambda work: core.cold_policy(models[arm], case, plan, work))
                        else:
                            forecast = paid(arm, 'forecast', lambda work: core.forecast(models[arm], case, plan, work))
                        operator = kernels.OPERATORS[step % 3] if arm == 'UNIFORM' else forecast['operator']
                        batch = dict(operator=operator, seed=seeds[operator], draw_start=op_draws[operator],
                            draw_end=op_draws[operator], increments=dict.fromkeys(kernels.ALPHABETS[operator], 0),
                            operator_n=op_draws[operator], spent=spent,
                            forecast_scores=None if forecast is None else forecast['forecast_scores'],
                            policy=forecast['policy'] if arm == 'COLD_POLICY' else None,
                            policy_scores=forecast['policy_scores'] if arm == 'COLD_POLICY' else None)
                        history['batches'].append(batch)
                        paid(arm, 'acquisition', lambda work: sample(streams[operator], case, operator, batch, work))
                        spent = batch['spent']; op_draws[operator] = batch['operator_n']
                        paid(arm, 'update', lambda work: core.update(models[arm], case, operator, batch['increments'], work))
                        plan = paid(arm, 'planning', lambda work: core.make_plan(models[arm], case, work))
                        batch['plan'] = plan
                        if plan['utility_lower'] >= 2:
                            break
                    history['terminal'] = dict(spent=spent, stop_reason='certified' if plan['utility_lower'] >= 2 else 'budget', plan=plan)
                    save(output/'histories.json', dict(records=histories))
            for case in old_cases:
                for arm in ARMS:
                    old_decisions.append(paid(arm, 'retention_planning',
                        lambda work: old_decision(life, case, arm, 'final', models[arm], work)))
            final_models.append(dict(life=life, models=models)); save_decisions()
            print(json.dumps(dict(life=life, targets=4, cumulative_samples=costs['acquisition']['controlled_samples']), separators=(',', ':')), flush=True)
        save_decisions(); phase('all_decisions_frozen')
        reference_map, probability_map = {}, {}
        for case in cases:
            saved, probabilities = true_reference(case, costs['oracle'])
            references.append(saved); reference_map[case['id']], probability_map[case['id']] = saved, probabilities
        save(output/'reference.json', dict(records=references))
        for history in histories:
            current = dict(life=history['life'], context_id=history['context_id'], arm=history['arm'])
            target_results.append(paid(history['arm'], 'evaluation', lambda work:
                score_target(history, reference_map[history['context_id']], probability_map[history['context_id']], work)))
        for decision in old_decisions:
            current = dict(life=decision['life'], context_id=decision['context_id'], arm=decision['arm'], stage=decision['stage'])
            old_results.append(paid(decision['arm'], 'evaluation', lambda work:
                score_old(decision, reference_map[decision['context_id']], probability_map[decision['context_id']], work)))
        save(output/'target_results.json', dict(records=target_results)); save(output/'old_results.json', dict(records=old_results))
        phase('oracle_evaluated'); summary = summarize(target_results, old_results, costs['bootstrap'])
        save(output/'summary.json', summary); record['seconds'] = perf_counter()-begun; current = None; phase('complete')
        print(json.dumps(dict(conditions=summary['conditions'], decision=summary['decision'], arms=summary['arms']), separators=(',', ':')), flush=True)
        return record
    except Exception as error:
        record.update(status='failed', seconds=perf_counter()-begun,
                      failure=dict(type=type(error).__name__, message=str(error), current=current))
        save_decisions(); save(output/'target_results.json', dict(records=target_results))
        save(output/'old_results.json', dict(records=old_results)); save(output/'reference.json', dict(records=references))
        save(output/'run.json', record)
        raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
