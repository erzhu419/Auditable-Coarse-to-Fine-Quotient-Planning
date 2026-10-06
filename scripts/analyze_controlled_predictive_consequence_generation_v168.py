"""Independent word generation, terminal selection and new-trace replay."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from scripts import analyze_controlled_predictive_program_consolidation_v161 as prior
from scripts.analyze_controlled_predictive_fixed_program_v167 import _equal, _mean, _moments, _pool

LIVES = range(4)
ACTIONS = ('DOWN', 'LEFT', 'RIGHT', 'UP')
ROUTES = ('FREQ', 'CONS')
MODES = ('H2', 'FREQ', 'CONS')
METRICS = ('utility', 'reward', 'failure', 'success')
CONTRASTS = {'CONS-FREQ': ('CONS', 'FREQ'), 'CONS-H2': ('CONS', 'H2'), 'FREQ-H2': ('FREQ', 'H2')}
BASE = 16800000000


def branch_seed(phase, root, suffix, heldout=None):
    if phase == 'EVAL':
        return BASE+50000000+root['life']*1000000+root['replica']*1000+root['slot']*100+suffix
    return BASE+{'G1': 20000000, 'G2': 30000000, 'FINAL': 40000000}[phase]+heldout*1000000+root['life']*100000+root['replica']*1000+root['slot']*100+suffix


def mutations(parents):
    words = [list(word) for word in parents]
    for parent in parents:
        for position in range(4):
            for action in ACTIONS:
                if action != parent[position]:
                    word = list(parent); word[position] = action; words.append(word)
    return [{'candidate_slot': slot, 'word': word} for slot, word in enumerate(words)]


def canonical_counts(boards, row):
    counts = Counter()
    for start in range(len(row['actions'])-3):
        _, transform = prior.frame(boards[start])
        word = tuple(prior.ground.transform_action_v1(prior.ground.Swipe2048Action(action), transform).value
                     for action in row['actions'][start:start+4])
        counts[word] += 1
    return counts


def frequency_cells(source_results):
    cells = []
    for heldout in LIVES:
        selected = [r for r in source_results if r['life'] != heldout]
        counts = sum((r['word_counts'] for r in selected), Counter())
        games = [game for r in selected for game in r['source_games']]
        frequencies = [{'word': list(word), 'frequency': count} for word, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]
        windows = sum(max(game['steps']-3, 0) for game in games)
        cells.append({'heldout_life': heldout, 'training_lives': [life for life in LIVES if life != heldout],
                      'source_frequencies': frequencies, 'source_games': games, 'complete': len(frequencies) >= 2,
                      'counts': dict(source_rows_examined=16, source_games=len(games), source_state_reconstructions=sum(game['steps'] for game in games),
                                     fragment_windows=windows, board_transforms=8*windows, action_transports=4*windows, unique_words=len(counts))})
    return cells


def generation_cells(frequencies, phase, previous=None):
    cells = []
    for frequency in frequencies:
        for route in ROUTES:
            parents = [row['word'] for row in frequency['source_frequencies'][:2]] if phase == 'G1' else next(
                c['selected_parents'] for c in previous if c['heldout_life'] == frequency['heldout_life'] and c['route'] == route)
            slots = mutations(parents) if phase != 'FINAL' else [{'candidate_slot': index, 'word': word} for index, word in enumerate(parents)]
            cells.append({'heldout_life': frequency['heldout_life'], 'route': route, 'phase': phase,
                          'source_frequencies': frequency['source_frequencies'], 'parents': parents,
                          'slots': slots, 'complete': len(parents) == 2 and len({tuple(w) for w in parents}) == 2})
    return cells


def _utility(vector):
    return vector[0]-vector[1]+vector[2]


def _row_valid(row, root, suffix, phase, heldout):
    return row is not None and row['seed'] == branch_seed(phase, root, suffix, heldout) and row['status'] in ('WON', 'LOST') and row['utility'] is not None and _equal(row['components'], [row['score']/2048., float(row['status'] == 'LOST'), float(row['status'] == 'WON')]) and _equal(row['utility'], _utility(row['components']))


def select_parents(cells, roots, outcomes):
    coordinates = lambda r: (r['heldout_life'], r['root_id'], r['suffix'], r['mode'])
    indexed = {coordinates(r): r for r in outcomes}
    counts = Counter(coordinates(r) for r in outcomes)
    result = []
    for cell in cells:
        heldout, phase, route = cell['heldout_life'], cell['phase'], cell['route']
        source_lives = [life for life in LIVES if life != heldout]
        pool = [r for r in roots if r['life'] != heldout]
        suffixes = range(4 if phase == 'FINAL' else 2)
        frequency = {tuple(row['word']): row['frequency'] for row in cell['source_frequencies']}
        scores = []
        cohort = len(pool) == 12 and all(sum(r['life'] == life for r in pool) == 4 for life in source_lives)
        for slot in cell['slots']:
            root_vectors, complete = [], cohort
            for root in pool:
                vectors, deltas = [], []
                for suffix in suffixes:
                    key = heldout, root['root_id'], suffix, f"{route}_W{slot['candidate_slot']}"
                    hkey = heldout, root['root_id'], suffix, 'H2'
                    row, baseline = indexed.get(key), indexed.get(hkey)
                    if counts[key] != 1 or counts[hkey] != 1 or not _row_valid(row, root, suffix, phase, heldout) or not _row_valid(baseline, root, suffix, phase, heldout):
                        complete = False; continue
                    vectors.append(row['components']); deltas.append([a-b for a, b in zip(row['components'], baseline['components'])])
                if len(vectors) == len(suffixes):
                    root_vectors.append((root['life'], [_mean([v[k] for v in vectors]) for k in range(3)], [_mean([v[k] for v in deltas]) for k in range(3)]))
            histories = []
            if complete:
                for life in source_lives:
                    values = [(vector, delta) for root_life, vector, delta in root_vectors if root_life == life]
                    vector = [_mean([v[k] for v, _ in values]) for k in range(3)]
                    delta = [_mean([d[k] for _, d in values]) for k in range(3)]
                    histories.append({'life': life, 'roots': 4, 'component_mean': vector, 'utility': _utility(vector), 'component_delta_vs_H2': delta, 'gain': _utility(delta)})
                vector = [_mean([h['component_mean'][k] for h in histories]) for k in range(3)]
                delta = [_mean([h['component_delta_vs_H2'][k] for h in histories]) for k in range(3)]
            else: vector, delta = None, None
            scores.append({'candidate_slot': slot['candidate_slot'], 'word': slot['word'], 'frequency': frequency.get(tuple(slot['word']), 0),
                           'complete': complete, 'train_component_mean': vector, 'train_utility': None if vector is None else _utility(vector),
                           'train_component_delta_vs_H2': delta, 'train_gain': None if delta is None else _utility(delta), 'per_history': histories})
        complete = cell['complete'] and bool(scores) and all(s['complete'] for s in scores)
        basis = 'terminal_utility' if route == 'CONS' or phase == 'FINAL' else 'source_frequency'
        ordered = sorted(scores, key=lambda score: (-(score['train_utility'] if basis == 'terminal_utility' else score['frequency']), tuple(score['word']), score['candidate_slot'])) if complete else []
        chosen = []
        for score in ordered:
            if score['word'] not in [s['word'] for s in chosen]: chosen.append(score)
            if len(chosen) == (1 if phase == 'FINAL' else 2): break
        result.append({**cell, 'slot_scores': scores, 'selected_parents': [s['word'] for s in chosen],
                       'selected_slots': [s['candidate_slot'] for s in chosen], 'complete': complete, 'selection_basis': basis})
    return result


def expected_roster(roots, cells, phase):
    result = []
    by_cell = {(c['heldout_life'], c['route']): c for c in cells}
    for root in roots:
        folds = [root['life']] if phase == 'EVAL' else [life for life in LIVES if life != root['life']]
        for heldout in folds:
            for suffix in range(16 if phase == 'EVAL' else 4 if phase == 'FINAL' else 2):
                alternatives = [('H2', 'H2', None, None)]
                for route in ROUTES:
                    cell = by_cell[heldout, route]
                    alternatives.extend((route, route if phase == 'EVAL' else f"{route}_W{slot['candidate_slot']}",
                                         None if phase == 'EVAL' else slot['candidate_slot'], slot['word'])
                                        for slot in ([{'candidate_slot': 0, 'word': cell['selected_parents'][0]}] if phase == 'EVAL' else cell['slots']))
                for route, mode, candidate_slot, word in alternatives:
                    result.append({'branch_id': f"{phase}:{root['root_id']}:fold{heldout}:{suffix}:{mode}", 'root_id': root['root_id'],
                                   'phase': phase, 'life': root['life'], 'query': 'risk1', 'replica': root['replica'], 'slot': root['slot'],
                                   'heldout_life': heldout, 'route': route, 'mode': mode, 'candidate_slot': candidate_slot,
                                   'suffix': suffix, 'seed': branch_seed(phase, root, suffix, heldout), 'program': word})
    return result


def eval_summary(roots, outcomes):
    index = {(r['root_id'], r['suffix'], r['mode']): r for r in outcomes}
    counts = Counter((r['root_id'], r['suffix'], r['mode']) for r in outcomes)
    root_rows = []
    cohort = len(roots) == 32 and len({r['root_id'] for r in roots}) == 32 and all(sum(r['life'] == life for r in roots) == 8 for life in LIVES)
    for root in roots:
        pairs, values, complete = [], {m: {k: [] for k in METRICS} for m in MODES}, cohort
        differences = {c: {k: [] for k in METRICS} for c in CONTRASTS}
        for suffix in range(16):
            rows = {mode: index.get((root['root_id'], suffix, mode)) for mode in MODES}
            valid = all(counts[root['root_id'], suffix, mode] == 1 and _row_valid(row, root, suffix, 'EVAL', root['life']) for mode, row in rows.items())
            deltas = {label: [a-b for a, b in zip(rows[left]['components'], rows[right]['components'])] if valid else None for label, (left, right) in CONTRASTS.items()}
            pairs.append({'suffix': suffix, 'seed': branch_seed('EVAL', root, suffix), 'complete': valid, 'component_deltas': deltas})
            if not valid: complete = False
            for mode, row in rows.items():
                for key, value in zip(METRICS, [_utility(row['components']), *row['components']] if valid else [None]*4): values[mode][key].append(value)
            for label, delta in deltas.items():
                for key, value in zip(METRICS, [_utility(delta), *delta] if valid else [None]*4): differences[label][key].append(value)
        root_rows.append({'root_id': root['root_id'], 'life': root['life'], 'query': 'risk1', 'replica': root['replica'], 'slot': root['slot'],
                          'complete': complete, 'pairs': pairs, 'modes': {mode: {k: _moments(v) for k, v in data.items()} for mode, data in values.items()},
                          'contrasts': {label: {k: _moments(v) for k, v in data.items()} for label, data in differences.items()}})
    comparisons = []
    for contrast in CONTRASTS:
        histories = []
        for life in LIVES:
            selected = [r for r in root_rows if r['life'] == life]
            histories.append({'life': life, 'roots': len(selected), 'metrics': {k: _pool([r['contrasts'][contrast][k] for r in selected], 8) for k in METRICS}})
        metrics = {k: _pool([h['metrics'][k] for h in histories], 4) for k in METRICS}
        comparisons.append({'query': 'risk1', 'contrast': contrast, 'roots': len(root_rows), 'complete': cohort and all(v['complete'] for v in metrics.values()),
                            'metrics': metrics, 'per_history': histories})
    return {'root_rows': root_rows, 'comparisons': comparisons, 'complete': all(c['complete'] for c in comparisons)}


def replay_lifecycle(task):
    """One life and phase streamed in a worker; only new records are replayed."""
    directory, phase, lifecycle, source, plans, roots = task
    directory = Path(directory)
    life, cost, checks = lifecycle['life'], prior.new_cost(), {}
    source_phase = phase in ('TRAIN_SOURCE', 'EVAL_SOURCE')
    plans = {p['branch_id']: p for p in plans}
    roots = {r['root_id']: r for r in roots}
    totals, observed, expected_roots, word_counts, games = {q: Counter() for q in ('risk1', 'risk8')}, [], [], Counter(), []
    compact = [] if source_phase else json.loads((directory/lifecycle['outcomes_ref']).read_text())
    compact_index = {r['branch_id']: r for r in compact}
    route_costs = {route: prior.new_cost() for route in (('SOURCE',) if source_phase else ('H2', 'FREQ', 'CONS'))}
    trace = lifecycle['source_trace'] if source_phase else lifecycle['branch_trace']
    for row in prior.prior.old.read_rows(directory/trace):
        if source_phase:
            local, swipes, boards = prior.prior.replay_game(row, {})
            observed.append(row['replica'])
            correct_seed = BASE+{'TRAIN_SOURCE': 10000000, 'EVAL_SOURCE': 90000000}[phase]+life*1000000+row['replica']
            local['source_seed'] = row['seed'] == correct_seed
            local['source_identity'] = row['life'] == life and row['phase'] == phase and row['query'] == 'risk1'
            prior.prior.add_policy_work(totals, row['result']['policy_counts'])
            expected_roots.extend(prior.expected_roots(boards, row))
            if phase == 'TRAIN_SOURCE': word_counts.update(canonical_counts(boards, row))
            games.append({k: row[k] for k in ('life', 'query', 'replica', 'seed')} | {k: row['result'][k] for k in ('steps', 'status')})
            prior.add_cost(cost, row['result'], 'physical_games')
            route, physical_key = 'SOURCE', 'physical_games'
        else:
            local, swipes = prior.replay_branch(row, max_steps=2000)
            observed.append(row['branch_id'])
            plan = plans.get(row['branch_id'])
            expected_fields = {k: value for k, value in (plan or {}).items() if k != 'program'}
            local['frozen_branch_identity'] = plan is not None and _equal(row, expected_fields)
            local['frozen_root_board'] = row['root_board'] == roots[row['root_id']]['board']
            local['frozen_word'] = plan is not None and row['module']['program'] == plan['program']
            expected_fields.update({k: row['result'][k] for k in ('score', 'steps', 'status', 'components', 'utility')}, module=row['module'])
            local['compact_matches_trace'] = _equal(compact_index.get(row['branch_id']), expected_fields)
            for query in totals: totals[query].update(row['result']['policy_counts_by_query'][query])
            prior.add_cost(cost, row['result'], 'physical_branches')
            route, physical_key = row['route'], 'physical_branches'
        prior.add_checks(checks, local)
        cost['analysis_replay_swipes'] += swipes
        prior.add_cost(route_costs[route], row['result'], physical_key)
        route_costs[route]['analysis_replay_swipes'] += swipes
    prior.add_checks(checks, prior.teacher_checks(lifecycle, source, totals))
    if not source_phase: checks['readonly_rule'] = lifecycle['rule_before'] == lifecycle['rule_after'] == source['rule']
    if source_phase:
        checks['four_source_games'] = sorted(observed) == list(range(4))
        checks['selected_source_roots'] = lifecycle['roots'] == expected_roots
    else:
        checks['frozen_physical_cohort'] = len(observed) == len(plans) and len(set(observed)) == len(plans) and set(observed) == set(plans)
        checks['compact_physical_cohort'] = len(compact) == len(plans) and len(compact_index) == len(plans) and set(compact_index) == set(plans)
    for key in (('physical_games',) if source_phase else ('physical_branches', 'program_setup_counts'))+('environment_counts', 'policy_counts', 'statuses'):
        checks['cost:'+key] = _equal(lifecycle[key], dict(cost[key]) if isinstance(cost[key], Counter) else cost[key])
    return {'phase': phase, 'life': life, 'checks': checks, 'costs': cost, 'route_costs': route_costs,
            'roots': expected_roots, 'word_counts': word_counts, 'source_games': games}


def analyze(directory):
    started = perf_counter()
    read = lambda name: json.loads((directory/name).read_text())
    run, capsule, frozen = [read(name) for name in ('run.json', 'source_capsule.json', 'frozen_inputs.json')]
    checks, phase_results, expected_train_roots, expected_eval_roots = [], {}, [], []
    frequencies, selections, selection_history = None, None, {}
    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
    check('execution_settings_frozen', frozen['status'] == 'frozen' and frozen['settings'] == run['settings'])
    full_order = ['INPUTS_FROZEN', 'TRAIN_SOURCE', 'G1', 'G1_SELECTED', 'G2', 'G2_SELECTED', 'FINAL', 'PROGRAMS_FROZEN', 'EVAL_SOURCE', 'EVAL']
    check('declared_phase_sequence', run['phase_order'] == full_order[:len(run['phase_order'])])
    with ProcessPoolExecutor(max_workers=4) as pool:
        for phase in ('TRAIN_SOURCE', 'G1', 'G2', 'FINAL', 'EVAL_SOURCE', 'EVAL'):
            if phase not in run['phases']: continue
            source_phase = phase in ('TRAIN_SOURCE', 'EVAL_SOURCE')
            if source_phase:
                plans, roots = [], []
            else:
                inputs = read(f'inputs_{phase.lower()}.json')
                if phase == 'EVAL':
                    cells = selections
                    roots = expected_eval_roots
                    check('frozen_final_programs', _equal(read('frozen_programs.json'), cells))
                else:
                    cells = generation_cells(frequencies, phase, selections)
                    roots = expected_train_roots
                    check(f'{phase}:candidate_cells', _equal(inputs['cells'], cells))
                plans = expected_roster(roots, cells, phase)
                check(f'{phase}:frozen_roster', inputs['roots'] == roots and inputs['branch_roster'] == plans)
            lifecycles = run['phases'][phase]['lifecycles']
            check(f'{phase}:four_lifecycles', len(lifecycles) == 4 and [r['life'] for r in lifecycles] == list(LIVES))
            tasks = [(str(directory), phase, lifecycle, capsule['snapshots'][lifecycle['life']],
                      [p for p in plans if p['life'] == lifecycle['life']], [r for r in roots if r['life'] == lifecycle['life']])
                     for lifecycle in lifecycles]
            results = list(pool.map(replay_lifecycle, tasks))
            phase_results[phase] = results
            for result in results:
                for name, valid in result['checks'].items(): check(f"{phase}:life{result['life']}:{name}", valid)
            if phase == 'TRAIN_SOURCE':
                expected_train_roots = [r for result in results for r in result['roots']]
                frequencies = frequency_cells(results)
                check('frozen_source_frequencies', _equal(read('source_frequencies.json'), frequencies))
            elif phase == 'EVAL_SOURCE':
                expected_eval_roots = [r for result in results for r in result['roots']]
            elif phase in ('G1', 'G2', 'FINAL'):
                outcomes = [row for lifecycle in lifecycles for row in json.loads((directory/lifecycle['outcomes_ref']).read_text())]
                selections = select_parents(cells, roots, outcomes)
                saved_selection = read(f'selections_{phase.lower()}.json')
                selection_history[phase] = saved_selection
                check(f'{phase}:independent_selection', _equal(saved_selection, selections))
            print(json.dumps({'audited_phase': phase, 'lifecycles': len(results)}), flush=True)
    complete_training = selections is not None and all(c['complete'] for c in selections) and selections[0]['phase'] == 'FINAL'
    check('training_failure_stops_future_phases', ('EVAL' not in run['phases']) if not complete_training else True)
    expected = None
    if 'EVAL' in phase_results:
        outcomes = [row for lifecycle in run['phases']['EVAL']['lifecycles'] for row in json.loads((directory/lifecycle['outcomes_ref']).read_text())]
        expected = eval_summary(expected_eval_roots, outcomes)
        summary = read('summary.json')
        check('independent_eval_statistics', _equal(summary, expected))
    all_results = [row for rows in phase_results.values() for row in rows]
    costs = prior.aggregate_costs([row['costs'] for row in all_results])
    costs.update(new_parameter_updates=0, physical_phase_costs={phase: prior.aggregate_costs([r['costs'] for r in rows]) for phase, rows in phase_results.items()},
                 teacher_accounting=[dict(phase=phase, life=row['life'], query=query, **teacher)
                                     for phase, data in run['phases'].items() for row in data['lifecycles']
                                     for query, teacher in row['teacher_bank'].items()],
                 this_stage_test_refs=capsule['this_stage_test_refs'], inherited_cost_refs=capsule['cost_refs'])
    costs['route_costs'] = {route: prior.aggregate_costs([r['route_costs'][route] for r in all_results if route in r['route_costs']])
                            for route in ('SOURCE', 'H2', 'FREQ', 'CONS')}
    costs['generation_counts'] = dict(sum((Counter(c['counts']) for c in (frequencies or [])), Counter()))
    costs['selection_logical_work'] = {phase: dict(sum((Counter(c['logical_work']) for c in cells), Counter())) for phase, cells in selection_history.items()}
    costs['generation_seconds'] = run['generation_seconds']
    costs['selection_seconds'] = run['selection_seconds']
    costs['inherited_v167_environment_samples'] = capsule['inherited_v167_environment_samples']
    check('physical_transition_cap', costs['new_environment_samples'] <= 25408000)
    if run['status'] == 'complete':
        check('complete_physical_roster', costs['physical_games'] == 32 and costs['physical_branches'] == 12672)
        check('completed_phase_sequence', run['phase_order'] == full_order)
    check('declared_run_status', run['status'] == ('complete' if 'EVAL' in phase_results else 'incomplete_training'))
    valid = all(c['passed'] for c in checks)
    result = {'schema': 'acfqp.consequence_generation.v168.analysis', 'valid': valid, 'complete': valid,
              'primary_complete': expected is not None and expected['complete'], 'training_complete': complete_training,
              'checks': checks, 'passed_checks': sum(c['passed'] for c in checks), 'total_checks': len(checks),
              'comparisons': [] if expected is None else expected['comparisons'], 'costs': costs,
              'inherited_cost_refs': capsule['cost_refs'], 'seconds': perf_counter()-started}
    (directory/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, default=PROJECT/'reports/controlled_predictive_consequence_generation_v168')
    args = parser.parse_args()
    result = analyze(args.directory)
    print(json.dumps({'valid': result['valid'], 'primary_complete': result['primary_complete'], 'passed': result['passed_checks'], 'checks': result['total_checks']}))
    raise SystemExit(0 if result['valid'] else 1)


if __name__ == '__main__':
    main()
