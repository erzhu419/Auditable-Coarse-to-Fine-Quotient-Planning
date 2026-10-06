"""Independent decisions, new suffix draws and fee audit of V230 continuations."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import importlib.util
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import scoped_repair_v229_math as math
from scripts.analyze_scoped_lifecycle_v229 import world

INPUT, OUTPUT = ROOT/'reports/scoped_lifecycle_v229', ROOT/'reports/gap_continuation_v230'
FAILURES = ((0, 58), (1, 58), (2, 42), (2, 44), (4, 44), (4, 58))
METHODS = ('OLD_V229', 'CANDIDATE_MULTI')


def restore_box(box):
    return {op: dict(bounds={cat: list(map(F, pair)) for cat, pair in row['bounds'].items()})
            for op, row in box.items()}


def restore_state(row, source):
    saved = row['library_before']
    return dict(a=dict(bounds=[restore_box(box) for box in saved['a']['bounds']]),
                a_anchors=deepcopy(source['a']),
                b=None if saved['b'] is None else {name: dict(bounds=[restore_box(box)
                    for box in bank['bounds']]) for name, bank in saved['b'].items()},
                b_points=deepcopy(saved['b_points']))


def feasible_point(box):
    result = {}
    for op in math.OPERATORS:
        lower = {cat: F(box[op]['bounds'][cat][0]) for cat in math.SUPPORT[op]}
        width = {cat: F(box[op]['bounds'][cat][1])-lower[cat] for cat in math.SUPPORT[op]}
        total = sum(width.values())
        result[op] = {cat: lower[cat]+(1-sum(lower.values()))*width[cat]/total
                      if total else lower[cat] for cat in math.SUPPORT[op]}
    return result


def plan(member, case, state, work):
    result = math.make_plan(member, case, state, work)
    kernels = {}
    for key in result['candidates']:
        index = result['candidate_labels'][key]['index']
        if index not in kernels:
            kernels[index] = feasible_point(result['candidate_envelopes'][key])
    result['candidate_posteriors'] = kernels or {'member': result['posterior']}
    return result


def ready(result):
    return (result['utility_lower'] >= 2 or result['goal_impossible']) and result['query_ready']


def deficit(result):
    goal = F(0) if result['goal_impossible'] else max(F(0), 2-result['utility_lower'])
    return goal+max(F(0), max(row['regret_upper']
                            for row in result['query_certificates'].values())-F(1, 20))


def candidate_choice(member, case, state, result, spent, work):
    """Reproduce the frozen heuristic without importing the acquisition code."""
    if spent >= 384 or ready(result):
        return None
    horizons = sorted({min(16, 384-spent), min(64, 384-spent), 384-spent})
    kernels = list(result['candidate_posteriors'].values())
    types_before = len({row['index'] for row in result['candidate_labels'].values()})
    before = deficit(result)
    cache, diagnostics, best = {}, {}, {}
    for op in math.OPERATORS:
        diagnostics[op] = []
        for horizon in horizons:
            gain, eliminated, successful = F(0), F(0), 0
            for kernel in kernels:
                hypothetical = deepcopy(member)
                expected = {cat: horizon*kernel[op][cat] for cat in math.SUPPORT[op]}
                addition = {cat: int(value) for cat, value in expected.items()}
                ordered = sorted(math.SUPPORT[op], key=lambda cat: (
                    -(expected[cat]-addition[cat]), math.SUPPORT[op].index(cat)))
                for cat in ordered[:horizon-sum(addition.values())]:
                    addition[cat] += 1
                for cat, count in addition.items():
                    hypothetical[op][cat] += count
                key = tuple(hypothetical[row][cat] for row in math.OPERATORS for cat in math.SUPPORT[row])
                if key not in cache:
                    cache[key] = math.make_plan(hypothetical, case, state, work)
                predicted = cache[key]
                gain += before-deficit(predicted)
                if predicted['mode'] == 'library':
                    eliminated += types_before-len({row['index'] for row in predicted['candidate_labels'].values()})
                successful += ready(predicted)
            batches = F(horizon, 16)
            diagnostics[op].append(dict(horizon=horizon, mean_gain=gain/len(kernels),
                gain_per_batch=gain/len(kernels)/batches,
                mean_eliminated_types=eliminated/len(kernels),
                elimination_per_batch=eliminated/len(kernels)/batches,
                ready_scenarios=successful, scenarios=len(kernels)))
        best[op] = max(diagnostics[op], key=lambda row: (
            max(F(0), row['gain_per_batch']), max(F(0), row['elimination_per_batch']), -row['horizon']))
    selected = min(math.OPERATORS, key=lambda op: (
        -max(F(0), best[op]['gain_per_batch']), -max(F(0), best[op]['elimination_per_batch']),
        sum(member[op].values()), math.OPERATORS.index(op)))
    return dict(operator=selected, reason='candidate_multibatch_certificate_gap',
                scores={op: max(F(0), best[op]['gain_per_batch']) for op in math.OPERATORS},
                selected_horizon=best[selected]['horizon'], horizons=horizons,
                candidate_scenarios=len(kernels), forecasts=diagnostics)


def run():
    begun = perf_counter()
    # This exact pure-function cache was checked in V229; no sampler is called.
    spec = importlib.util.spec_from_file_location('retained_v229_math_cache',
        ROOT/'reports/v229_runtime_tmp/replay_with_cache.py')
    cache = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cache)
    math.certificates, math.goal_upper = cache.certificates, cache.goal_upper
    read = lambda path: json.loads(path.read_text())
    records = read(OUTPUT/'records.json')
    assessed = {(row['life'], row['index'], row['method']): row for row in read(OUTPUT/'results.json')}
    sources = {row['life']: row for row in read(INPUT/'source_evidence.json')}
    histories = {life: [row for line in (INPUT/f'records_life_{life:02d}.jsonl').read_text().splitlines()
                 if (row := json.loads(line))['arm'] == 'REPAIR_CS'] for life, _ in FAILURES}
    checks, expected, per_record = Counter(), Counter(), []

    def check(name, condition):
        expected[name] += 1
        checks[name] += bool(condition)

    check('complete_selection', len(records) == 12 and {(row['life'], row['index'], row['method'])
        for row in records} == {(life, index, method) for life, index in FAILURES for method in METHODS})
    for row in records:
        life, index, method = row['life'], row['index'], row['method']
        cases, laws, _, _ = world(life)
        original = next(old for old in histories[life] if old['index'] == index)
        state, member = restore_state(original, sources[life]), math.empty()
        for batch in original['batches']:
            if batch['spent'] > 256:
                break
            for cat, count in batch['increments'].items():
                member[batch['operator']][cat] += count
        prefix = deepcopy(member)
        state_before = deepcopy(state)
        seeds = {op: 260000+(life*78+index)*3+j for j, op in enumerate(math.OPERATORS)}
        generators = {op: random.Random(seed) for op, seed in seeds.items()}
        offsets = dict.fromkeys(math.OPERATORS, 0)
        work, spent = Counter(), 256
        check('unchanged_case', row['case'] == cases[index] == original['case'])
        check('actual_256_prefix', row['prefix_member'] == member and sum(sum(r.values()) for r in member.values()) == 256)
        check('fresh_paired_seeds', row['seeds'] == seeds)
        check('frozen_library_input', math.same(row['library_before'], state))
        current = plan(member, cases[index], state, work)
        check('initial_plan', math.same(row['initial_plan'], current))
        actual_points = [math.score(current, laws[index], cases[index], spent, work)]
        query_points = [math.query_score(current['queries'], laws[index], cases[index])]
        for batch in row['batches']:
            check('stop_not_ignored', not ready(current) and spent < 384)
            choice = (math.choose(member, cases[index], state, current, spent, work)
                      if method == 'OLD_V229' else candidate_choice(member, cases[index], state, current, spent, work))
            check('exact_acquisition_choice', math.same(batch['choice'], choice))
            op = choice['operator']
            increments = dict.fromkeys(math.SUPPORT[op], 0)
            for _ in range(16):
                value, cumulative = generators[op].random(), F(0)
                for cat in math.SUPPORT[op]:
                    cumulative += laws[index][op][cat]
                    if value < float(cumulative):
                        increments[cat] += 1
                        break
            check('fresh_draws', batch['increments'] == increments)
            check('draw_offsets', batch['operator'] == op and batch['seed'] == seeds[op]
                  and batch['draw_start'] == offsets[op] and batch['draw_end'] == offsets[op]+16)
            offsets[op] += 16
            for cat, count in increments.items():
                member[op][cat] += count
            spent += 16
            current = plan(member, cases[index], state, work)
            check('actual_batch_plan', batch['spent'] == spent and math.same(batch['plan'], current))
            point = math.score(current, laws[index], cases[index], spent, work)
            queries = math.query_score(current['queries'], laws[index], cases[index])
            check('true_query_bound', all(queries[q]['regret'] <= current['query_certificates'][q]['regret_upper'] for q in math.WEIGHTS))
            check('true_risk_bound', point['actual'][1] <= current['risk_upper'] <= F(1, 20))
            actual_points.append(point)
            query_points.append(queries)
        check('correct_terminal_stop', spent == 384 or ready(current))
        check('terminal_plan', math.same(row['terminal_plan'], current))
        check('terminal_actual_counts', row['member'] == member and row['spent'] == spent)
        check('suffix_budget', row['suffix_operator_samples'] == offsets and sum(offsets.values()) == spent-256 <= 128)
        check('prefix_counts', row['prefix_operator_samples'] == {op: sum(prefix[op].values()) for op in math.OPERATORS})
        check('no_library_commit', state == state_before and row['library_frozen'] and row['commits'] == 0
              and math.same(row['library_after'], state_before))
        check('true_completion', row['completed'] == ready(current) and row['query_certified'] == current['query_ready']
              and row['execution_certified'] == (current['utility_lower'] >= 2)
              and row['goal_impossible'] == current['goal_impossible'])
        reference = dict(source_paid_samples=4608,
                         history_paid_samples=sum(old['spent'] for old in histories[life] if old['index'] < index),
                         historical_targets=sum(old['index'] < index for old in histories[life]),
                         prefix_paid_samples=256, additional_paid_samples=spent-256)
        reference['total_reference_paid_samples'] = sum(reference[key] for key in (
            'source_paid_samples', 'history_paid_samples', 'prefix_paid_samples', 'additional_paid_samples'))
        check('paid_reference_fees', row['fees'] == reference)
        check('actual_environment_work', all(row['work'].get(key, 0) == spent-256 for key in (
            'controlled_samples', 'controlled_resets', 'environment_random_draws')))
        check('forecast_not_committed', all(row['work'].get(key, 0) == 0 for key in (
            'scoped_retained_targets', 'scoped_retained_samples', 'scoped_point_committed_targets')))
        results = assessed[life, index, method]
        check('all_actual_history_scored', len(results['history']) == len(actual_points))
        for saved, point, queries in zip(results['history'], actual_points, query_points):
            check('oracle_after_decision_replay', all(math.same(saved[key], point[key]) for key in point)
                  and math.same(saved['queries'], queries))
        per_record.append(dict(life=life, index=index, method=method, spent=spent,
                               additional_paid_samples=spent-256, completed=ready(current)))
        print(f'audit continuation {life}:{index} {method} new={spent-256}', flush=True)
    summary, run_info = read(OUTPUT/'summary.json'), read(OUTPUT/'run.json')
    samples = sum(row['additional_paid_samples'] for row in per_record)
    check('actual_total_budget', summary['new_environment_observations'] == samples <= 1536)
    check('qualification_scope', summary['qualification_only'] and not summary['scientific_gate_changed'])
    check('oracle_only_after_decisions', run_info['phases'] == [
        'protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete'])
    result = dict(valid=all(checks[key] == count for key, count in expected.items()),
                  records=len(records), checks=dict(checks), expected=dict(expected),
                  new_environment_observations=samples, per_record=per_record, seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('checks', 'expected', 'per_record')}), flush=True)
    return result


if __name__ == '__main__':
    run()
