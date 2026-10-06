"""Chronological mechanism learning, paired acquisition, and frozen evaluation."""
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
from acfqp.science import conditioned_mechanisms_v205 as core
from acfqp.science import mechanism_switch_task_v205 as task
from acfqp.science import structured_route_task_v201 as route

OUTPUT = ROOT/'reports/conditioned_mechanisms_v205'
RUNTIME = ROOT/'reports/v205_runtime_tmp'
ARMS = ('GUIDED', 'FIXED', 'COLD', 'UNIFORM')
SOURCE_FILES = (
    'src/acfqp/science/structured_route_task_v201.py',
    'src/acfqp/science/continual_route_kernels_v202.py',
    'src/acfqp/science/robust_route_planning_v203.py',
    'src/acfqp/science/target_risk_acquisition_v204.py',
    'src/acfqp/science/mechanism_switch_task_v205.py',
    'src/acfqp/science/conditioned_mechanisms_v205.py',
    'scripts/run_conditioned_mechanisms_v205.py',
    'scripts/analyze_conditioned_mechanisms_v205.py',
    'tests/test_conditioned_mechanisms_v205.py',
    'tests/test_conditioned_mechanism_analysis_v205.py',
    'specs/CONDITIONED_MECHANISMS_V205.md',
    'reports/v205_runtime_tmp/run_checks.py',
    'reports/v205_runtime_tmp/run_stage.py')
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


def capture(output):
    manifest = []
    for relative in SOURCE_FILES:
        destination = output/'source_code'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, destination); manifest.append(dict(path=relative))
    save(output/'source_manifest.json', manifest)


def query_decision(life, case, arm, model, work, stage=None):
    decisions = core.query_decisions(model, case, work)
    queries = {}
    for query, plan in decisions.items():
        root, recovery = plan['policy']['START', 4], plan['policy']['RECOVERY', 2]
        pure = ('DETOUR_RETRY' if recovery == 'RETRY' else 'DETOUR_RETURN') if root == 'DETOUR' else root
        queries[query] = dict(root_action=root, recovery_action=recovery, pure_policy=pure,
                             predicted=plan['values']['START', 4])
    record = dict(life=life, context_id=case['id'], arm=arm, queries=queries)
    if stage is not None:
        record['stage'] = stage
    return record


def draw(rng, laws, operator, increments, number, work, progress):
    for _ in range(number):
        value = rng.random(); cumulative = Fraction(0)
        work['controlled_samples'] += 1; work['controlled_resets'] += 1; work['environment_random_draws'] += 1
        for category in core.ALPHABETS[operator]:
            cumulative += laws[operator][category]
            work['sampling_threshold_accumulations'] += 1; work['sampling_threshold_comparisons'] += 1
            if value < float(cumulative):
                increments[category] += 1
                break
        progress['draw_end'] += 1
        if 'n' in progress:
            progress['n'] += 1
        else:
            progress['operator_n'] += 1; progress['spent'] += 1


def source_batch(rng, cases, name, index, batch, work):
    events = []
    for case in cases:
        laws = task.laws(case, work)
        for operator in core.OPERATORS:
            record = dict(context=case, operator=operator, counts=dict.fromkeys(core.ALPHABETS[operator], 0),
                          n=0, phase=name, draw_start=index, draw_end=index)
            batch['records'].append(record)
            # Observed events alone enter the statistical learner.
            for _ in range(128):
                before = dict(record['counts'])
                draw(rng, laws, operator, record['counts'], 1, work, record)
                successor = next(category for category in core.ALPHABETS[operator]
                                 if record['counts'][category] > before[category])
                events.append(dict(context=case, operator=operator, successor=successor))
                work['source_observed_events'] += 1
            index = record['draw_end']
    return events, index


def target_batch(rng, case, operator, batch, work):
    draw(rng, task.laws(case, work), operator, batch['increments'], core.BATCH, work, batch)


def true_reference(case, work):
    graph = task.rows(case, work); pure = route.pure_values(graph, 4, work)
    oracle = {query: max(route.utility(vector, query, work) for vector in pure.values()) for query in route.QUERIES}
    return dict(context_id=case['id'], pure_vectors=pure, oracle_utility=oracle), task.laws(case, work)


def score_hard(plan, reference, laws, spent, work):
    vector = tuple(sum((weight*reference['pure_vectors'][name][component] for name, weight in plan['mix']), Fraction(0))
                   for component in range(3))
    work['actual_mixture_component_products'] += 3*len(plan['mix'])
    work['actual_mixture_component_accumulations'] += 3*len(plan['mix'])
    utility = route.utility(vector, 'goal', work); excess = max(Fraction(0), vector[1]-DELTA)
    wait = sum((weight for name, weight in plan['mix'] if name == 'WAIT'), Fraction(0))
    within = []
    for operator, envelope in plan['envelopes'].items():
        for category, (lower, upper) in envelope['bounds'].items():
            within.append(lower <= laws[operator][category] <= upper); work['coverage_marginals'] += 1
    return dict(spent=spent, actual_fractions=vector, actual=[float(value) for value in vector],
        actual_utility_fraction=utility, actual_utility=float(utility), risk_upper=plan['risk_upper'],
        utility_lower=plan['utility_lower'], violation=excess > 0, excess_fraction=excess, excess=float(excess),
        coverage=all(within), wait_mass_fraction=wait, wait_mass=float(wait))


def score_target(record, reference, laws, work):
    history = [score_hard(record['initial_plan'], reference, laws, 0, work)]
    history.extend(score_hard(batch['plan'], reference, laws, batch['spent'], work) for batch in record['batches'])
    terminal = dict(history[-1], certified=record['terminal']['stop_reason'] == 'certified',
                    stop_reason=record['terminal']['stop_reason'])
    first = next((row['spent'] for row in history if row['actual_utility_fraction'] >= 2), None)
    return dict(life=record['life'], context_id=record['context_id'], target_index=record['target_index'], arm=record['arm'],
        history=history, terminal=terminal, first_true_utility_ge_2=first,
        first_operator=record['batches'][0]['operator'], pilot_batches=sum(batch['pilot'] for batch in record['batches']),
        total_batches=len(record['batches']))


def score_queries(record, reference, work):
    queries = {}
    for query, decision in record['queries'].items():
        vector = reference['pure_vectors'][decision['pure_policy']]
        utility = route.utility(vector, query, work); oracle = reference['oracle_utility'][query]
        error = [abs(float(predicted-actual)) for predicted, actual in zip(decision['predicted'], vector)]
        work['prediction_error_components'] += 3; work['regret_subtractions'] += 1
        queries[query] = dict(actual_fractions=vector, actual=[float(value) for value in vector],
            utility_fraction=utility, utility=float(utility), oracle_utility_fraction=oracle,
            oracle_utility=float(oracle), regret_fraction=oracle-utility, regret=float(oracle-utility), abs_prediction_error=error)
    scored = dict(life=record['life'], context_id=record['context_id'], arm=record['arm'], queries=queries)
    if 'stage' in record:
        scored['stage'] = record['stage']
    return scored


def mean(values):
    values = list(values)
    return sum(values)/len(values)


def query_metrics(rows):
    return dict(utility=mean(query['utility'] for row in rows for query in row['queries'].values()),
        regret=mean(query['regret'] for row in rows for query in row['queries'].values()),
        **{name: mean(query['abs_prediction_error'][component] for row in rows for query in row['queries'].values())
           for component, name in enumerate(('R', 'F', 'S'))})


def bootstrap(contrasts, work):
    rng = random.Random(205900); samples = {name: [] for name in contrasts}
    for _ in range(5000):
        indices = [rng.randrange(12) for _ in range(12)]; work['bootstrap_index_draws'] += 12
        for name, values in contrasts.items():
            samples[name].append(sum(values[index] for index in indices)/12); work['bootstrap_mean_terms'] += 12
    result = {}
    for name, values in contrasts.items():
        ordered = sorted(samples[name]); result[name] = dict(mean=mean(values), ci=[ordered[124], ordered[4874]])
    work['bootstrap_resamples'] += 5000
    return result


def summarize(qualification, source_models, targets, zero, old, cases, source_samples, work):
    arms, zero_metrics, retention = {}, {}, {}
    for arm in ARMS:
        rows = [row for row in targets if row['arm'] == arm]; histories = [point for row in rows for point in row['history']]
        total = sum(row['terminal']['spent'] for row in rows)
        arms[arm] = dict(restored=sum(row['terminal']['certified'] for row in rows), total_samples=total,
            mean_samples=mean(row['terminal']['spent'] for row in rows), true_utility=mean(row['terminal']['actual_utility'] for row in rows),
            history_violations=sum(point['violation'] for point in histories), terminal_violations=sum(row['terminal']['violation'] for row in rows),
            max_failure=max(point['actual'][1] for point in histories), max_excess=max(point['excess'] for point in histories),
            wait_mass=mean(row['terminal']['wait_mass'] for row in rows), coverage=mean(point['coverage'] for point in histories),
            pilot_fraction=sum(row['pilot_batches'] for row in rows)/sum(row['total_batches'] for row in rows),
            first_operator_counts={operator: sum(row['first_operator'] == operator for row in rows) for operator in core.OPERATORS},
            source_samples=source_samples, source_plus_target_samples=source_samples+total)
        zero_metrics[arm] = query_metrics([row for row in zero if row['arm'] == arm])
        before = query_metrics([row for row in old if row['arm'] == arm and row['stage'] == 'SOURCE'])['regret']
        after = query_metrics([row for row in old if row['arm'] == arm and row['stage'] == 'FINAL'])['regret']
        retention[arm] = dict(SOURCE_regret=before, FINAL_regret=after, regret_change=after-before)
    source_no_weather = all('weather' not in row['SOURCE']['REVISED']['selected_fields'][operator]
                            for row in source_models for operator in core.OPERATORS[:2])
    short = sum(row['REVISION']['REVISED']['selected_fields']['SHORT_PASS'] == ['weather'] for row in source_models)
    detour = sum(row['REVISION']['REVISED']['selected_fields']['DETOUR_PASS'] == ['weather'] for row in source_models)
    weather = {case['id']: case['weather'] for case in cases}
    first = sum(row['first_operator'] == ('SHORT_PASS' if weather[row['context_id']] == 'wet' else 'DETOUR_PASS')
                for row in targets if row['arm'] == 'GUIDED')
    contrasts = {name: [] for name in ('cold_minus_guided_samples', 'uniform_minus_guided_samples', 'fixed_minus_guided_samples',
                                      'guided_minus_cold_utility', 'zero_guided_minus_cold_utility', 'zero_guided_minus_fixed_utility')}
    for life in range(12):
        terminal = {arm: dict(samples=mean(row['terminal']['spent'] for row in targets if row['life'] == life and row['arm'] == arm),
                             utility=mean(row['terminal']['actual_utility'] for row in targets if row['life'] == life and row['arm'] == arm)) for arm in ARMS}
        qzero = {arm: query_metrics([row for row in zero if row['life'] == life and row['arm'] == arm]) for arm in ARMS}
        for arm, endpoint in (('COLD', 'cold_minus_guided_samples'), ('UNIFORM', 'uniform_minus_guided_samples'), ('FIXED', 'fixed_minus_guided_samples')):
            contrasts[endpoint].append(terminal[arm]['samples']-terminal['GUIDED']['samples'])
        contrasts['guided_minus_cold_utility'].append(terminal['GUIDED']['utility']-terminal['COLD']['utility'])
        contrasts['zero_guided_minus_cold_utility'].append(qzero['GUIDED']['utility']-qzero['COLD']['utility'])
        contrasts['zero_guided_minus_fixed_utility'].append(qzero['GUIDED']['utility']-qzero['FIXED']['utility'])
    intervals = bootstrap(contrasts, work)
    conditions = dict(TASK=qualification['qualified'], CONDITION=source_no_weather and short >= 10 and detour >= 10 and first >= 44,
        TRANSFER=zero_metrics['GUIDED']['regret'] <= .05 and all(intervals[name]['mean'] >= .1 and intervals[name]['ci'][0] > 0
            for name in ('zero_guided_minus_cold_utility', 'zero_guided_minus_fixed_utility')),
        ACQUISITION=intervals['cold_minus_guided_samples']['mean'] >= 16 and intervals['cold_minus_guided_samples']['ci'][0] > 0
            and arms['GUIDED']['restored'] >= 36 and arms['GUIDED']['restored'] >= arms['COLD']['restored'] and arms['GUIDED']['true_utility'] >= 2,
        RISK_RETENTION=all(point['risk_upper'] <= DELTA and not point['violation'] for row in targets if row['arm'] == 'GUIDED' for point in row['history'])
            and retention['GUIDED']['regret_change'] <= .01)
    return dict(schema='acfqp.conditioned_mechanisms.v205.summary', complete=True, arms=arms, zero_metrics=zero_metrics, retention=retention,
        condition_revision=dict(SOURCE_no_weather=source_no_weather, SHORT_weather_lifecycles=short,
                                DETOUR_weather_lifecycles=detour, GUIDED_first_critical_operator=first),
        paired_lifecycle_contrasts=contrasts, bootstrap=intervals, conditions=conditions,
        decision='CONDITIONED_MECHANISMS_SUPPORTED' if all(conditions.values()) else 'CONDITIONED_MECHANISMS_NOT_SUPPORTED',
        cold_start_reference=dict(arm='COLD', source_samples=0, target_samples=arms['COLD']['total_samples']))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    arm_stages = ('choice', 'target_acquisition', 'update', 'planning', 'query_planning', 'evaluation')
    costs = {stage: Counter() for stage in (*arm_stages, 'qualification', 'roster', 'source_acquisition', 'source_learning', 'oracle', 'bootstrap')}
    arm_costs = {arm: {stage: Counter() for stage in arm_stages} for arm in ARMS}
    record = dict(schema='acfqp.conditioned_mechanisms.v205.run', status='preparing', phase_history=[], costs=costs, arm_costs=arm_costs,
        source_fits=[], target_fit_calls=0, target_condition_selections=0, test_refs=[str(RUNTIME/'test_checks.json')],
        runtime=dict(python=sys.version.split()[0], executable=sys.executable))
    batches, source_models, final_models, histories, zero_decisions, old_decisions = [], [], [], [], [], []
    target_results, zero_results, old_results, references = [], [], [], []
    current = None

    def phase(name, **details):
        record['status'] = name
        record['phase_history'].append(dict(phase=name, seconds_since_start=perf_counter()-begun,
            source_samples=costs['source_acquisition']['controlled_samples'], target_samples=costs['target_acquisition']['controlled_samples'],
            target_count=len(histories), zero_count=len(zero_decisions), old_count=len(old_decisions), **details))
        save(output/'run.json', record)

    def paid(arm, stage, operation):
        local = Counter()
        try:
            return operation(local)
        finally:
            costs[stage].update(local); arm_costs[arm][stage].update(local)

    def fit_source(life, phase_name, mode, operation):
        local = Counter(); item = dict(life=life, phase=phase_name, mode=mode, costs=local)
        record['source_fits'].append(item)
        try:
            return operation(local)
        finally:
            costs['source_learning'].update(local)

    def save_decisions():
        save(output/'source_batches.json', dict(lifecycles=batches)); save(output/'source_models.json', dict(lifecycles=source_models))
        save(output/'models.json', dict(lifecycles=final_models)); save(output/'histories.json', dict(records=histories))
        save(output/'zero_decisions.json', dict(records=zero_decisions)); save(output/'old_decisions.json', dict(records=old_decisions))

    try:
        capture(output); phase('protocol_frozen')
        cases = task.roster(costs['roster']); save(output/'cases.json', cases)
        qualification = task.qualify(costs['qualification']); save(output/'qualification.json', qualification); phase('task_qualified')
        if not qualification['qualified']:
            summary = dict(schema='acfqp.conditioned_mechanisms.v205.summary', complete=True, stopped_before_sampling=True,
                conditions=dict(TASK=False, CONDITION=None, TRANSFER=None, ACQUISITION=None, RISK_RETENTION=None),
                decision='CONDITIONED_MECHANISMS_NOT_SUPPORTED')
            save_decisions(); save(output/'summary.json', summary); record['seconds'] = perf_counter()-begun; phase('complete')
            print(json.dumps(summary, separators=(',', ':')), flush=True); return record
        normal = [case for case in cases if case['weather'] == 'normal']
        revision_cases = [case for case in cases if case['weather'] != 'normal' and case['operating'] == 'high']
        targets = [case for case in cases if case['weather'] != 'normal' and case['operating'] == 'low']
        for life in range(12):
            current = dict(life=life, phase='SOURCE'); rng = random.Random(205000+life); index = 0; history = []
            lifecycle = dict(life=life, seed=205000+life, batches=[]); batches.append(lifecycle)
            source = dict(life=life); source_models.append(source)
            batch = dict(name='SOURCE', records=[]); lifecycle['batches'].append(batch)
            events, index = source_batch(rng, normal, 'SOURCE', index, batch, costs['source_acquisition']); history.append(events)
            source['SOURCE'] = {mode: fit_source(life, 'SOURCE', mode, lambda work: core.fit(history, mode, counts=work))
                                for mode in ('REVISED', 'FULL_CONTEXT')}
            for case in normal:
                for arm in ARMS:
                    model = source['SOURCE']['FULL_CONTEXT' if arm == 'COLD' else 'REVISED']
                    old_decisions.append(paid(arm, 'query_planning', lambda work: query_decision(life, case, arm, model, work, 'SOURCE')))
            phase('source_models_frozen', life=life)
            current = dict(life=life, phase='REVISION'); batch = dict(name='REVISION', records=[]); lifecycle['batches'].append(batch)
            events, index = source_batch(rng, revision_cases, 'REVISION', index, batch, costs['source_acquisition']); history.append(events)
            source['REVISION'] = {mode: fit_source(life, 'REVISION', mode, lambda work: core.fit(history, mode, counts=work))
                                  for mode in ('REVISED', 'FULL_CONTEXT')}
            source['REVISION']['FIXED'] = fit_source(life, 'REVISION', 'FIXED',
                lambda work: core.fixed_model(source['SOURCE']['REVISED'], source['REVISION']['FULL_CONTEXT'], work))
            models = {arm: deepcopy(source['REVISION']['FULL_CONTEXT' if arm == 'COLD' else 'FIXED' if arm == 'FIXED' else 'REVISED']) for arm in ARMS}
            # All four zero-target probes precede every target draw in this life.
            for case in targets:
                for arm in ARMS:
                    zero_decisions.append(paid(arm, 'query_planning', lambda work: query_decision(life, case, arm, models[arm], work)))
            save_decisions(); phase('revision_models_frozen', life=life)
            for target_index, case in enumerate(targets):
                seeds = {op: 206000+(life*4+target_index)*3+op_index for op_index, op in enumerate(core.OPERATORS)}
                for arm in ARMS:
                    current = dict(life=life, phase='TARGET', context_id=case['id'], arm=arm)
                    streams = {op: random.Random(seed) for op, seed in seeds.items()}; consumed = Counter(); spent = 0
                    plan = paid(arm, 'planning', lambda work: core.make_plan(models[arm], case, work))
                    acquisition = dict(life=life, context_id=case['id'], target_index=target_index, arm=arm, seeds=seeds, initial_plan=plan, batches=[])
                    histories.append(acquisition)
                    for step in range(core.BUDGET//core.BATCH):
                        choice = (dict(operator=core.OPERATORS[step % 3], pilot=False, projection_counts=None, policy=None, policy_scores=None)
                                  if arm == 'UNIFORM' else paid(arm, 'choice', lambda work: core.choose(models[arm], case, plan, work)))
                        operator = choice['operator']
                        batch = dict(operator=operator, seed=seeds[operator], draw_start=consumed[operator], draw_end=consumed[operator],
                            operator_n=consumed[operator], spent=spent, increments=dict.fromkeys(core.ALPHABETS[operator], 0),
                            pilot=choice['pilot'], projection_counts=choice['projection_counts'], policy=choice['policy'], policy_scores=choice['policy_scores'])
                        acquisition['batches'].append(batch)
                        paid(arm, 'target_acquisition', lambda work: target_batch(streams[operator], case, operator, batch, work))
                        spent = batch['spent']; consumed[operator] = batch['operator_n']
                        paid(arm, 'update', lambda work: core.update(models[arm], case, operator, batch['increments'], work))
                        plan = paid(arm, 'planning', lambda work: core.make_plan(models[arm], case, work)); batch['plan'] = plan
                        if plan['utility_lower'] >= 2:
                            break
                    acquisition['terminal'] = dict(spent=spent, stop_reason='certified' if plan['utility_lower'] >= 2 else 'budget', plan=plan)
            for case in normal:
                for arm in ARMS:
                    old_decisions.append(paid(arm, 'query_planning', lambda work: query_decision(life, case, arm, models[arm], work, 'FINAL')))
            final_models.append(dict(life=life, models=models)); save_decisions()
            print(json.dumps(dict(life=life, source_samples=3072, cumulative_target_samples=costs['target_acquisition']['controlled_samples']), separators=(',', ':')), flush=True)
        save_decisions(); phase('all_decisions_frozen')
        reference_map, laws_map = {}, {}
        for case in cases:
            saved, laws = true_reference(case, costs['oracle']); references.append(saved)
            reference_map[case['id']], laws_map[case['id']] = saved, laws
        save(output/'reference.json', dict(records=references))
        for acquisition in histories:
            target_results.append(paid(acquisition['arm'], 'evaluation', lambda work:
                score_target(acquisition, reference_map[acquisition['context_id']], laws_map[acquisition['context_id']], work)))
        for decisions, results in ((zero_decisions, zero_results), (old_decisions, old_results)):
            for decision in decisions:
                results.append(paid(decision['arm'], 'evaluation', lambda work: score_queries(decision, reference_map[decision['context_id']], work)))
        save(output/'target_results.json', dict(records=target_results)); save(output/'zero_results.json', dict(records=zero_results))
        save(output/'old_results.json', dict(records=old_results)); phase('oracle_evaluated')
        source_samples = costs['source_acquisition']['controlled_samples']
        save(output/'source_accounting.json', dict(samples_per_lifecycle={str(row['life']): sum(record['n'] for batch in row['batches'] for record in batch['records'])
            for row in batches}, total_samples=source_samples, model_fits=len(record['source_fits']), actual_fit_costs=record['source_fits']))
        summary = summarize(qualification, source_models, target_results, zero_results, old_results, cases, source_samples, costs['bootstrap'])
        save(output/'summary.json', summary); record['seconds'] = perf_counter()-begun; current = None; phase('complete')
        print(json.dumps(dict(conditions=summary['conditions'], decision=summary['decision'], arms=summary['arms']), separators=(',', ':')), flush=True)
        return record
    except Exception as error:
        record.update(status='failed', seconds=perf_counter()-begun, failure=dict(type=type(error).__name__, message=str(error), current=current))
        save_decisions(); save(output/'target_results.json', dict(records=target_results)); save(output/'zero_results.json', dict(records=zero_results))
        save(output/'old_results.json', dict(records=old_results)); save(output/'reference.json', dict(records=references)); save(output/'run.json', record)
        raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
