"""Independent fresh-suffix statistics and settled V162 physical replay."""
from collections import Counter
from copy import deepcopy
import argparse
import gzip
import json
import math
from pathlib import Path
import sys
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from scripts import analyze_controlled_predictive_feedback_program_v162 as feedback

LIVES = range(4)
SUFFIXES = range(16)
MODES = ('H2', 'S0_B')
METRICS = ('utility', 'reward', 'failure', 'success')
DEFAULT_DIRECTORY = Path(__file__).resolve().parents[1]/'reports/controlled_predictive_fixed_program_v167'


def seed(root, suffix):
    return 167*100000000+50000000+root['life']*1000000+root['replica']*1000+root['slot']*100+suffix


def _equal(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(key in actual and _equal(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(_equal(a, b) for a, b in zip(actual, expected))
    if isinstance(expected, float):
        return isinstance(actual, (int, float)) and math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10)
    return actual == expected


def _mean(values):
    return math.fsum(values)/len(values)


def _moments(values):
    complete = bool(values) and all(value is not None for value in values)
    mean = _mean(values) if complete else None
    variance = math.fsum((v-mean)**2 for v in values)/(len(values)-1) if complete else None
    return {'n': len(values), 'complete': complete, 'mean': mean, 'sample_variance': variance,
            'mean_variance': None if variance is None else variance/len(values)}


def _pool(values, required):
    complete = len(values) == required and all(v['complete'] for v in values)
    mean = _mean([v['mean'] for v in values]) if complete else None
    variance = math.fsum(v['mean_variance'] for v in values)/required**2 if complete else None
    error = math.sqrt(variance) if complete else None
    return {'complete': complete, 'mean': mean, 'mean_variance': variance,
            'conditional_suffix_se': error, 'conditional_suffix_ci95': None if error is None else [mean-1.96*error, mean+1.96*error]}


def independent_statistics(roots, outcomes):
    """Fixed 16-suffix paired contrasts; a broken pair remains in the cohort."""
    pool = [r for r in roots if r['query'] == 'risk1']
    index = {(r['root_id'], r['suffix'], r['mode']): r for r in outcomes}
    counts = Counter((r['root_id'], r['suffix'], r['mode']) for r in outcomes)
    roster_valid = len(pool) == 32 and len({r['root_id'] for r in pool}) == 32 and all(sum(r['life'] == life for r in pool) == 8 for life in LIVES)
    result = []
    for root in pool:
        errors, pairs = [], []
        if not roster_valid: errors.append('root_roster')
        trials = {mode: {metric: [] for metric in METRICS} for mode in MODES}
        differences = {metric: [] for metric in METRICS}
        for suffix in SUFFIXES:
            rows, pair_errors = {}, []
            for mode in MODES:
                coordinate = root['root_id'], suffix, mode
                row = index.get(coordinate)
                rows[mode] = row
                if counts[coordinate] != 1:
                    pair_errors.append('missing_or_duplicate_outcome')
                if row is not None:
                    if row['seed'] != seed(root, suffix): pair_errors.append('outcome_seed_mismatch')
                    if row['status'] not in ('WON', 'LOST') or row['utility'] is None: pair_errors.append('nonterminal_outcome')
                    if row['components'][1:] != [float(row['status'] == 'LOST'), float(row['status'] == 'WON')] or not math.isclose(row['components'][0], row['score']/2048., abs_tol=1e-10):
                        pair_errors.append('terminal_component_mismatch')
                    elif row['utility'] is not None and not math.isclose(row['utility'], row['components'][0]-row['components'][1]+row['components'][2], abs_tol=1e-10):
                        pair_errors.append('utility_vector_mismatch')
            complete = not pair_errors
            delta, utility_delta = None, None
            if complete:
                delta = [b-a for a, b in zip(rows['H2']['components'], rows['S0_B']['components'])]
                utility_delta = delta[0]-delta[1]+delta[2]
                for mode in MODES:
                    for metric, value in zip(METRICS, [rows[mode]['utility'], *rows[mode]['components']]): trials[mode][metric].append(value)
                for metric, value in zip(METRICS, [utility_delta, *delta]): differences[metric].append(value)
            else:
                for mode in MODES:
                    for metric in METRICS: trials[mode][metric].append(None)
                for metric in METRICS: differences[metric].append(None)
            pairs.append({'suffix': suffix, 'seed': seed(root, suffix), 'complete': complete,
                          'component_delta': delta, 'utility_delta': utility_delta})
            errors.extend(pair_errors)
        mode_stats = {mode: {metric: _moments(values) for metric, values in metrics.items()} for mode, metrics in trials.items()}
        contrast = {metric: _moments(values) for metric, values in differences.items()}
        result.append({'root_id': root['root_id'], 'life': root['life'], 'query': 'risk1', 'replica': root['replica'], 'slot': root['slot'],
                       'complete': not errors, 'pairs': pairs, 'modes': mode_stats, 'contrasts': {'S0_B-H2': contrast}})
    histories = []
    for life in LIVES:
        selected = [r for r in result if r['life'] == life]
        histories.append({'life': life, 'roots': len(selected), 'metrics': {metric: _pool([r['contrasts']['S0_B-H2'][metric] for r in selected], 8) for metric in METRICS}})
    comparison = {'query': 'risk1', 'contrast': 'S0_B-H2', 'roots': len(result),
                  'metrics': {metric: _pool([h['metrics'][metric] for h in histories], 4) for metric in METRICS}, 'per_history': histories}
    comparison['complete'] = roster_valid and all(m['complete'] for m in comparison['metrics'].values())
    return {'complete': comparison['complete'], 'root_count': len(result), 'root_rows': result, 'comparison': comparison}


def check_statistics(roots, outcomes, summary):
    expected = independent_statistics(roots, outcomes)
    actual_roots = {r['root_id']: r for r in summary['root_rows']}
    checks = [{'name': 'fresh_complete_fixed_roster', 'passed': expected['complete']},
              {'name': 'all_32_roots_retained', 'passed': len(summary['root_rows']) == 32 and len(actual_roots) == 32},
              {'name': 'fresh_primary_statistics', 'passed': _equal(summary.get('comparison'), expected['comparison'])}]
    checks.extend({'name': f"fresh_root:{root['root_id']}", 'passed': _equal(actual_roots.get(root['root_id']), root)} for root in expected['root_rows'])
    return checks, expected


def independent_plan(roots):
    return [{'root_id': root['root_id'], 'phase': 'EVAL', 'life': root['life'], 'query': 'risk1',
             'replica': root['replica'], 'slot': root['slot'], 'heldout_life': root['life'],
             'mode': mode, 'arm': 'H2' if mode == 'H2' else 'FEEDBACK', 'suffix': suffix, 'seed': seed(root, suffix)}
            for root in roots for suffix in SUFFIXES for mode in MODES]


def _diagnostics(outcomes):
    result = []
    for mode in MODES:
        rows = [row for row in outcomes if row['mode'] == mode]
        modules = [r['module'] for r in rows]
        result.append({'mode': mode, 'branches': 512, 'present_branches': len(rows),
                       'complete': len(rows) == 512 and all(r['status'] in ('WON', 'LOST') and r['utility'] is not None for r in rows),
                       'mean_prefix_steps': _mean([m['prefix_steps'] for m in modules]),
                       'mean_attempts': _mean([m['attempts'] for m in modules]),
                       'mean_continuation_steps': _mean([r['steps']-r['module']['prefix_steps'] for r in rows]),
                       'probe_branches': sum(m['predicate'] is not None for m in modules),
                       'same_step_fallback_branches': sum(m['exit_reason'] == 'illegal' for m in modules),
                       'continuation_branches': sum(r['steps'] > r['module']['prefix_steps'] for r in rows),
                       'exit_counts': dict(Counter(m['exit_reason'] for m in modules)),
                       'predicate_counts': dict(Counter('none' if m['predicate'] is None else 'true' if m['predicate'] else 'false' for m in modules))})
    return result


def analyze(directory):
    started = perf_counter()
    read = lambda name: json.loads((directory/name).read_text())
    capsule, roots, program, candidate, inputs, run, summary = [read(name) for name in
        ('source_capsule.json', 'eval_roots.json', 'frozen_program.json', 'frozen_candidate.json', 'evaluation_inputs.json', 'run.json', 'summary.json')]
    frozen_inputs = read('frozen_inputs.json')
    checks = []
    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
    expected_semantics = dict(first_action='DOWN', probe_action='RIGHT', true_suffix=['RIGHT', 'DOWN', 'RIGHT'], false_suffix=['DOWN', 'RIGHT', 'DOWN'])
    expected_program = deepcopy(candidate)
    expected_program.update(true_suffix=list(expected_semantics['false_suffix']), false_suffix=list(expected_semantics['false_suffix']))
    source_ref = Path(capsule['source_run_ref'])
    source_directory = (source_ref if source_ref.is_absolute() else PROJECT_ROOT/source_ref).parent
    original_candidates = json.loads((source_directory/'generated_candidates.json').read_text())
    source_candidate = next(c for cell in original_candidates if cell['heldout_life'] == 0 and cell['query'] == 'risk1'
                            for c in cell['candidates'] if _equal(c, expected_semantics))
    original_roots = json.loads((source_directory/'eval_roots.json').read_text())
    nomination_ref = Path(capsule['nomination_roster_ref'])
    nomination = json.loads((nomination_ref if nomination_ref.is_absolute() else PROJECT_ROOT/nomination_ref).read_text())
    nominated = next(s for s in nomination['strata'] if s['stratum_id'] == 'S0' and s['query'] == 'risk1')
    check('fixed_original_S0_candidate', _equal(candidate, dict(candidate_id='P0', **expected_semantics)))
    check('deterministic_original_fold_candidate', candidate == source_candidate and nominated['source_semantics'] == expected_semantics)
    check('fixed_source_EVAL_roots', roots == [r for r in original_roots if r['query'] == 'risk1'])
    check('forced_BB_whole_suffix_program', program == expected_program)
    check('prelaunch_inputs_fixed', inputs['roots'] == roots and inputs['program'] == program)
    check('frozen_execution_settings', frozen_inputs['status'] == 'frozen' and run['settings'] == frozen_inputs['settings'])
    check('run_phase_complete', run['status'] == 'complete' and run['phase_order'] == ['INPUTS_FROZEN', 'EVAL'] and run['new_parameter_updates'] == 0)
    plan, roots_by_id = independent_plan(roots), {root['root_id']: root for root in roots}
    plans = {(p['root_id'], p['suffix'], p['mode']): p for p in plan}
    frozen_plans = {(p['root_id'], p['suffix'], p['mode']): p for p in inputs['branch_roster']}
    check('all_fresh_branch_plans', len(inputs['branch_roster']) == 1024 and len(frozen_plans) == 1024 and
          set(frozen_plans) == set(plans) and all(_equal(frozen_plans[key], expected) for key, expected in plans.items()))
    outcomes, raw_rows, lifecosts, replaychecks = [], [], [], {}
    lifecycle_rows = run['phases']['EVAL']['lifecycles']
    check('four_fresh_lifecycles', len(lifecycle_rows) == 4 and [row['life'] for row in lifecycle_rows] == list(LIVES))
    for lifecycle in lifecycle_rows:
        life, cost = lifecycle['life'], feedback.new_cost()
        source = capsule['snapshots'][life]
        compact = json.loads((directory/lifecycle['outcomes_ref']).read_text())
        compact_index = {(r['root_id'], r['suffix'], r['mode']): r for r in compact}
        observed, totals = [], {q: Counter() for q in ('risk1', 'risk8')}
        for row in feedback.prior.old.read_rows(directory/lifecycle['branch_trace']):
            observed.append((row['root_id'], row['suffix'], row['mode']))
            key = observed[-1]
            frozen = frozen_plans.get(key)
            replay, swipes = feedback.replay_branch(row, max_steps=2000)
            feedback.add_checks(replaychecks, replay)
            replaychecks['frozen_trace_identity'] = replaychecks.get('frozen_trace_identity', True) and frozen is not None and _equal(row, frozen)
            replaychecks['frozen_root_board'] = replaychecks.get('frozen_root_board', True) and row['root_board'] == roots_by_id[row['root_id']]['board']
            replaychecks['frozen_executed_program'] = replaychecks.get('frozen_executed_program', True) and row['module']['program'] == (None if row['mode'] == 'H2' else program)
            fields = {k: row['result'][k] for k in ('score', 'steps', 'status', 'components', 'utility')}
            fields.update(module=row['module'], arm=row['arm'])
            replaychecks['compact_matches_trace'] = replaychecks.get('compact_matches_trace', True) and _equal(compact_index.get(key), {**(frozen or {}), **fields})
            feedback.add_cost(cost, row['result'], 'physical_branches')
            cost['analysis_replay_swipes'] += swipes
            for query in totals: totals[query].update(row['result']['policy_counts_by_query'][query])
            raw_rows.append(row)
        check(f'life_{life}:fixed_branch_cohort', len(observed) == 256 and len(set(observed)) == 256 and
              set(observed) == {key for key, meta in plans.items() if meta['life'] == life})
        check(f'life_{life}:compact_cohort', len(compact) == 256 and len(compact_index) == 256 and set(compact_index) == set(observed))
        check(f'life_{life}:readonly_rule', lifecycle['rule_before'] == lifecycle['rule_after'] == source['rule'])
        feedback.add_checks(replaychecks, feedback.teacher_checks(lifecycle, source, totals))
        for key in ('physical_branches', 'environment_counts', 'policy_counts', 'program_setup_counts', 'statuses'):
            check(f'life_{life}:cost:{key}', _equal(lifecycle[key], dict(cost[key]) if isinstance(cost[key], Counter) else cost[key]))
        outcomes.extend(compact); lifecosts.append(cost)
    checks.extend({'name': 'fresh_replay:'+key, 'passed': value} for key, value in replaychecks.items())
    statistical_checks, independent = check_statistics(roots, outcomes, summary)
    checks.extend(statistical_checks)
    check('program_execution_diagnostics', _equal(summary['program_diagnostics'], _diagnostics(outcomes)))
    costs = feedback.aggregate_costs(lifecosts)
    costs.update(new_parameter_updates=0, inherited_cost_refs=capsule['cost_refs'],
                 inherited_v164_environment_samples=capsule['inherited_v164_environment_samples'],
                 this_stage_test_refs=capsule['this_stage_test_refs'],
                 teacher_accounting=[dict(phase=phase, life=row['life'], query=query, **teacher)
                                     for phase, data in run['phases'].items() for row in data['lifecycles']
                                     for query, teacher in row['teacher_bank'].items()])
    result = {'schema': 'acfqp.fixed_program.v167.analysis', 'valid': all(c['passed'] for c in checks),
              'complete': all(c['passed'] for c in checks), 'primary_complete': independent['complete'],
              'checks': checks, 'passed_checks': sum(c['passed'] for c in checks), 'total_checks': len(checks),
              'comparison': independent['comparison'], 'metrics': independent['comparison']['metrics'], 'costs': costs,
              'inherited_cost_refs': capsule['cost_refs'],
              'seconds': perf_counter()-started}
    (directory/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, default=DEFAULT_DIRECTORY)
    args = parser.parse_args()
    result = analyze(args.directory)
    print(json.dumps({'valid': result['valid'], 'primary_complete': result['primary_complete'],
                      'passed': result['passed_checks'], 'checks': result['total_checks']}))
    raise SystemExit(0 if result['valid'] else 1)


if __name__ == '__main__':
    main()
