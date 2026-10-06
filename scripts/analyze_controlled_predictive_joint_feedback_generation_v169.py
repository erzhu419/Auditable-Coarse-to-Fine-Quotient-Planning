"""Independent joint-program generation, paired arm selection and trace replay."""
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
from scripts import analyze_controlled_predictive_feedback_program_v162 as feedback
from scripts.analyze_controlled_predictive_fixed_program_v167 import _equal, _mean, _moments, _pool

LIVES = range(4)
ACTIONS = ('DOWN', 'LEFT', 'RIGHT', 'UP')
MODES = ('H2', 'COND', 'TWIN')
METRICS = ('utility', 'reward', 'failure', 'success')
CONTRASTS = {'COND-TWIN': ('COND', 'TWIN'), 'COND-H2': ('COND', 'H2'), 'TWIN-H2': ('TWIN', 'H2')}
PROGRAM_KEYS = ('first_action', 'probe_action', 'true_suffix', 'false_suffix')
BASE = 16900000000


def program_key(program):
    return (program['first_action'], program['probe_action'], *program['true_suffix'], *program['false_suffix'])


def from_key(key):
    return dict(first_action=key[0], probe_action=key[1], true_suffix=list(key[2:5]), false_suffix=list(key[5:8]))


def executable(program, forced=None):
    result = deepcopy(program)
    if forced is not None:
        suffix = result['true_suffix' if forced == 'A' else 'false_suffix']
        result['true_suffix'] = list(suffix)
        result['false_suffix'] = list(suffix)
    result['fixed_suffix'] = list(result['true_suffix'])
    return result


def mutations(parents):
    keys = [program_key(program) for program in parents]
    children = list(keys)
    for parent in keys:
        for position in range(8):
            for action in ACTIONS:
                if action != parent[position]:
                    child = list(parent); child[position] = action; children.append(tuple(child))
    return [dict(candidate_slot=slot, program=from_key(key)) for slot, key in enumerate(children)]


def branch_seed(phase, root, suffix, heldout=None):
    if phase == 'EVAL':
        return BASE+50000000+root['life']*1000000+root['replica']*1000+root['slot']*100+suffix
    return BASE+{'G1': 20000000, 'G2': 30000000, 'FINAL': 40000000}[phase]+heldout*1000000+root['life']*100000+root['replica']*1000+root['slot']*100+suffix


def source_candidates(rows):
    cells = []
    for heldout in LIVES:
        generated = feedback.generation_cell(rows, heldout, 'risk1')
        parents = [{key: deepcopy(candidate[key]) for key in PROGRAM_KEYS} for candidate in generated['candidates']]
        issues = []
        if generated['training_lives'] != [life for life in LIVES if life != heldout]: issues.append('source_history_roster')
        for life in LIVES:
            if life == heldout: continue
            games = [game for game in generated['source_games'] if game['life'] == life]
            if len(games) != 4 or {game['replica'] for game in games} != set(range(4)):
                if 'source_game_roster' not in issues: issues.append('source_game_roster')
        if len(parents) != 2 or len({program_key(parent) for parent in parents}) != 2: issues.append('source_program_pool')
        cells.append({key: generated[key] for key in ('heldout_life', 'query', 'training_lives', 'source_games', 'counts')} |
                     dict(parents=parents, complete=not issues, issues=issues))
    return cells


def generation_cells(sources, phase, previous=None):
    cells = []
    for source in sources:
        parents = source['parents'] if phase == 'G1' else next(
            cell['selected_parents'] for cell in previous if cell['heldout_life'] == source['heldout_life'])
        slots = mutations(parents) if phase != 'FINAL' else [dict(candidate_slot=i, program=deepcopy(p)) for i, p in enumerate(parents)]
        cells.append(dict(heldout_life=source['heldout_life'], query='risk1', phase=phase, parents=parents, slots=slots,
                          complete=source['complete'] and len(parents) == 2 and len({program_key(p) for p in parents}) == 2, issues=list(source['issues'])))
    return cells


def _utility(vector):
    return vector[0]-vector[1]+vector[2]


def _row_valid(row, root, suffix, phase, heldout):
    return row is not None and row['phase'] == phase and row['life'] == root['life'] and row['query'] == 'risk1' and row['heldout_life'] == heldout and row['seed'] == branch_seed(phase, root, suffix, heldout) and row['status'] in ('WON', 'LOST') and row['utility'] is not None and _equal(row['components'], [row['score']/2048., float(row['status'] == 'LOST'), float(row['status'] == 'WON')]) and _equal(row['utility'], _utility(row['components']))


def paired_predicate_valid(a, b):
    if a is None or b is None: return False
    predicate = a['module']['predicate']
    if predicate is not b['module']['predicate'] or predicate not in (True, False, None): return False
    if predicate is None:
        return all(a[key] == b[key] for key in ('score', 'steps', 'status', 'components', 'utility')) and all(
            a['module'][key] == b['module'][key] for key in ('actual_word', 'prefix_steps', 'attempts', 'exit_reason', 'exit_step'))
    return True


def select_parents(cells, roots, outcomes):
    """Select conditional utility reconstructed from both paid suffix arms."""
    coordinates = lambda row: (row['heldout_life'], row['root_id'], row['suffix'], row['mode'])
    indexed = {coordinates(row): row for row in outcomes}
    counts = Counter(coordinates(row) for row in outcomes)
    result = []
    for cell in cells:
        heldout, phase = cell['heldout_life'], cell['phase']
        histories = [life for life in LIVES if life != heldout]
        pool = [root for root in roots if root['life'] != heldout and root['query'] == 'risk1']
        suffixes = range(4 if phase == 'FINAL' else 1)
        cohort = len(pool) == 12 and len({r['root_id'] for r in pool}) == 12 and all(
            {(r['replica'], r['slot']) for r in pool if r['life'] == life} == {(replica, slot) for replica in range(2) for slot in range(2)} for life in histories)
        scores = []
        for slot in cell['slots']:
            complete, root_vectors, predicates = cohort, [], Counter()
            for root in pool:
                vectors = {arm: [] for arm in ('COND', 'A', 'B', 'H2')}
                for suffix in suffixes:
                    keys = [(heldout, root['root_id'], suffix, mode) for mode in ('H2', f"P{slot['candidate_slot']}_A", f"P{slot['candidate_slot']}_B")]
                    h2, a, b = [indexed.get(key) for key in keys]
                    valid = all(counts[key] == 1 and _row_valid(row, root, suffix, phase, heldout) for key, row in zip(keys, (h2, a, b)))
                    valid = valid and paired_predicate_valid(a, b)
                    if valid:
                        valid = a['module']['program'] == executable(slot['program'], 'A') and b['module']['program'] == executable(slot['program'], 'B')
                        valid = valid and all(row['route'] == arm and row['candidate_slot'] == slot['candidate_slot'] and row['arm'] == 'FEEDBACK' for arm, row in (('A', a), ('B', b)))
                        valid = valid and h2['route'] == 'H2' and h2['candidate_slot'] is None and h2['arm'] == 'H2'
                    if not valid:
                        complete = False; continue
                    predicate = a['module']['predicate']; predicates['true' if predicate is True else 'false' if predicate is False else 'unobserved'] += 1
                    selected = a if predicate is True or predicate is None else b
                    for arm, row in (('COND', selected), ('A', a), ('B', b), ('H2', h2)): vectors[arm].append(row['components'])
                if len(vectors['COND']) == len(suffixes):
                    root_vectors.append((root['life'], {arm: [_mean([v[k] for v in values]) for k in range(3)] for arm, values in vectors.items()}))
            per_history = []
            if complete:
                for life in histories:
                    values = [vectors for root_life, vectors in root_vectors if root_life == life]
                    means = {arm: [_mean([v[arm][k] for v in values]) for k in range(3)] for arm in ('COND', 'A', 'B', 'H2')}
                    delta = [a-b for a, b in zip(means['COND'], means['H2'])]
                    per_history.append(dict(life=life, roots=4, component_mean=means['COND'], utility=_utility(means['COND']),
                                            component_delta_vs_H2=delta, gain=_utility(delta),
                                            unconditional_A=dict(life=life, roots=4, component_mean=means['A'], utility=_utility(means['A'])),
                                            unconditional_B=dict(life=life, roots=4, component_mean=means['B'], utility=_utility(means['B']))))
                vector = [_mean([row['component_mean'][k] for row in per_history]) for k in range(3)]
                delta = [_mean([row['component_delta_vs_H2'][k] for row in per_history]) for k in range(3)]
                unconditional = {arm: [_mean([row['unconditional_'+arm]['component_mean'][k] for row in per_history]) for k in range(3)] for arm in ('A', 'B')}
            else: vector, delta, unconditional = None, None, {'A': None, 'B': None}
            scores.append(dict(candidate_slot=slot['candidate_slot'], program=deepcopy(slot['program']), complete=complete,
                               train_component_mean=vector, train_utility=None if vector is None else _utility(vector),
                               train_component_delta_vs_H2=delta, train_gain=None if delta is None else _utility(delta),
                               unconditional={arm: dict(component_mean=values, utility=None if values is None else _utility(values),
                                                        per_history=[row['unconditional_'+arm] for row in per_history]) for arm, values in unconditional.items()},
                               predicate_counts=dict(predicates), per_history=per_history))
        complete = cell['complete'] and bool(scores) and all(score['complete'] for score in scores)
        selected = []
        if complete:
            for score in sorted(scores, key=lambda row: (-row['train_utility'], program_key(row['program']), row['candidate_slot'])):
                if program_key(score['program']) not in {program_key(row['program']) for row in selected}: selected.append(score)
                if len(selected) == (1 if phase == 'FINAL' else 2): break
        selected_twin = None
        if phase == 'FINAL' and selected:
            selected_twin = min(('A', 'B'), key=lambda arm: (-selected[0]['unconditional'][arm]['utility'], arm))
        result.append({**{key: value for key, value in cell.items() if key != 'issues'}, 'slot_scores': scores, 'selected_parents': [row['program'] for row in selected],
                       'selected_slots': [row['candidate_slot'] for row in selected],
                       'complete': complete, 'selection_basis': 'conditional_terminal_utility'})
        if phase == 'FINAL': result[-1]['selected_twin'] = selected_twin
    return result


def expected_roster(roots, cells, phase):
    result = []
    by_cell = {cell['heldout_life']: cell for cell in cells}
    for root in roots:
        folds = [root['life']] if phase == 'EVAL' else [life for life in LIVES if life != root['life']]
        for heldout in folds:
            cell = by_cell[heldout]
            for suffix in range(16 if phase == 'EVAL' else 4 if phase == 'FINAL' else 1):
                alternatives = [('H2', 'H2', 'H2', None, None)]
                if phase == 'EVAL':
                    program = cell['selected_parents'][0]
                    alternatives.extend((route, route, 'FEEDBACK', None, executable(program, None if route == 'COND' else cell['selected_twin'])) for route in ('COND', 'TWIN'))
                else:
                    alternatives.extend((arm, f"P{slot['candidate_slot']}_{arm}", 'FEEDBACK', slot['candidate_slot'], executable(slot['program'], arm)) for slot in cell['slots'] for arm in ('A', 'B'))
                for route, mode, arm, candidate_slot, program in alternatives:
                    result.append(dict(branch_id=f"{phase}:{root['root_id']}:fold{heldout}:{suffix}:{mode}", root_id=root['root_id'],
                                       phase=phase, life=root['life'], query='risk1', replica=root['replica'], slot=root['slot'],
                                       heldout_life=heldout, route=route, mode=mode, arm=arm, candidate_slot=candidate_slot,
                                       suffix=suffix, seed=branch_seed(phase, root, suffix, heldout), program=program))
    return result


def eval_summary(roots, outcomes):
    index = {(row['root_id'], row['suffix'], row['mode']): row for row in outcomes}
    counts = Counter((row['root_id'], row['suffix'], row['mode']) for row in outcomes)
    root_rows = []
    cohort = len(roots) == 32 and len({root['root_id'] for root in roots}) == 32 and all(sum(root['life'] == life for root in roots) == 8 for life in LIVES)
    for root in roots:
        pairs, values, complete = [], {mode: {key: [] for key in METRICS} for mode in MODES}, cohort
        differences = {label: {key: [] for key in METRICS} for label in CONTRASTS}
        for suffix in range(16):
            rows = {mode: index.get((root['root_id'], suffix, mode)) for mode in MODES}
            valid = all(counts[root['root_id'], suffix, mode] == 1 and _row_valid(row, root, suffix, 'EVAL', root['life']) for mode, row in rows.items())
            valid = valid and paired_predicate_valid(rows['COND'], rows['TWIN'])
            if valid:
                conditional, twin = rows['COND']['module']['program'], rows['TWIN']['module']['program']
                valid = conditional['first_action'] == twin['first_action'] and conditional['probe_action'] == twin['probe_action'] and twin['true_suffix'] == twin['false_suffix'] and twin['true_suffix'] in (conditional['true_suffix'], conditional['false_suffix'])
            deltas = {label: [a-b for a, b in zip(rows[left]['components'], rows[right]['components'])] if valid else None for label, (left, right) in CONTRASTS.items()}
            pairs.append(dict(suffix=suffix, seed=branch_seed('EVAL', root, suffix), complete=valid, component_deltas=deltas))
            if not valid: complete = False
            for mode, row in rows.items():
                for key, value in zip(METRICS, [_utility(row['components']), *row['components']] if valid else [None]*4): values[mode][key].append(value)
            for label, delta in deltas.items():
                for key, value in zip(METRICS, [_utility(delta), *delta] if valid else [None]*4): differences[label][key].append(value)
        root_rows.append(dict(root_id=root['root_id'], life=root['life'], query='risk1', replica=root['replica'], slot=root['slot'], complete=complete,
                              pairs=pairs, modes={mode: {key: _moments(v) for key, v in data.items()} for mode, data in values.items()},
                              contrasts={label: {key: _moments(v) for key, v in data.items()} for label, data in differences.items()}))
    comparisons = []
    for contrast in CONTRASTS:
        histories = []
        for life in LIVES:
            selected = [row for row in root_rows if row['life'] == life]
            histories.append(dict(life=life, roots=len(selected), metrics={key: _pool([row['contrasts'][contrast][key] for row in selected], 8) for key in METRICS}))
        metrics = {key: _pool([history['metrics'][key] for history in histories], 4) for key in METRICS}
        comparisons.append(dict(query='risk1', contrast=contrast, roots=len(root_rows), complete=cohort and all(value['complete'] for value in metrics.values()), metrics=metrics, per_history=histories))
    diagnostics = []
    for mode in MODES:
        present = [index[root['root_id'], suffix, mode] for root in roots for suffix in range(16) if (root['root_id'], suffix, mode) in index]
        diagnostics.append(dict(mode=mode, branches=len(roots)*16, present_branches=len(present),
                                mean_prefix_steps=_mean([row['module']['prefix_steps'] for row in present]) if present else None,
                                mean_attempts=_mean([row['module']['attempts'] for row in present]) if present else None,
                                exit_counts=dict(Counter(row['module']['exit_reason'] for row in present)),
                                predicate_counts=dict(Counter('true' if row['module']['predicate'] is True else 'false' if row['module']['predicate'] is False else 'unobserved' for row in present))))
    observed, divergence, both = 0, 0, 0
    for root in root_rows:
        seen = set()
        for pair in root['pairs']:
            if not pair['complete']: continue
            conditional = index[root['root_id'], pair['suffix'], 'COND']['module']
            twin = index[root['root_id'], pair['suffix'], 'TWIN']['module']
            if conditional['predicate'] is not None:
                seen.add(conditional['predicate']); observed += 1
                divergence += conditional['actual_word'][1:] != twin['actual_word'][1:]
        both += seen == {True, False}
    return dict(root_rows=root_rows, comparisons=comparisons, program_diagnostics=diagnostics,
                feedback_diagnostics=dict(predicate_observed_branches=observed, suffixes_differ_from_twin=divergence, roots_with_both_predicates=both),
                complete=all(row['complete'] for row in comparisons))


def replay_lifecycle(task):
    directory, phase, lifecycle, source, plans, roots = task
    directory = Path(directory)
    life, cost, checks = lifecycle['life'], prior.new_cost(), {}
    source_phase = phase in ('TRAIN_SOURCE', 'EVAL_SOURCE')
    plans = {plan['branch_id']: plan for plan in plans}; roots = {root['root_id']: root for root in roots}
    totals, observed, expected_roots, source_rows = {query: Counter() for query in ('risk1', 'risk8')}, [], [], []
    compact = [] if source_phase else json.loads((directory/lifecycle['outcomes_ref']).read_text())
    compact_index = {row['branch_id']: row for row in compact}
    route_costs = {route: prior.new_cost() for route in (('SOURCE',) if source_phase else ('H2', 'COND', 'TWIN') if phase == 'EVAL' else ('H2', 'A', 'B'))}
    trace = lifecycle['source_trace'] if source_phase else lifecycle['branch_trace']
    paired_first = {}
    for row in prior.prior.old.read_rows(directory/trace):
        if source_phase:
            local, swipes, boards = prior.prior.replay_game(row, {})
            observed.append(row['replica'])
            local['source_seed'] = row['seed'] == BASE+{'TRAIN_SOURCE': 10000000, 'EVAL_SOURCE': 90000000}[phase]+life*1000000+row['replica']
            local['source_identity'] = row['life'] == life and row['phase'] == phase and row['query'] == 'risk1'
            prior.prior.add_policy_work(totals, row['result']['policy_counts'])
            expected_roots.extend(prior.expected_roots(boards, row))
            if phase == 'TRAIN_SOURCE': source_rows.append(row)
            prior.add_cost(cost, row['result'], 'physical_games')
            route, physical_key = 'SOURCE', 'physical_games'
        else:
            local, swipes = feedback.replay_branch(row, max_steps=2000)
            observed.append(row['branch_id']); plan = plans.get(row['branch_id'])
            expected_fields = {key: value for key, value in (plan or {}).items() if key != 'program'}
            local['frozen_branch_identity'] = plan is not None and _equal(row, expected_fields)
            local['frozen_root_board'] = row['root_board'] == roots[row['root_id']]['board']
            local['frozen_program'] = plan is not None and row['module']['program'] == plan['program']
            expected_fields.update({key: row['result'][key] for key in ('score', 'steps', 'status', 'components', 'utility')}, module=row['module'])
            local['compact_matches_trace'] = _equal(compact_index.get(row['branch_id']), expected_fields)
            if row['route'] != 'H2':
                key = row['root_id'], row['heldout_life'], row['suffix'], row['candidate_slot']
                paired_first.setdefault(key, {})[row['route']] = (row['actions'][0], row['scores'][0], row['choices'][0]['afterstate'], row['spawned_cells'][0], row['spawned_ranks'][0], row['module']['predicate'])
            for query in totals: totals[query].update(row['result']['policy_counts_by_query'][query])
            prior.add_cost(cost, row['result'], 'physical_branches'); route, physical_key = row['route'], 'physical_branches'
        prior.add_checks(checks, local); cost['analysis_replay_swipes'] += swipes
        prior.add_cost(route_costs[route], row['result'], physical_key); route_costs[route]['analysis_replay_swipes'] += swipes
    prior.add_checks(checks, prior.teacher_checks(lifecycle, source, totals))
    if source_phase:
        checks['four_source_games'] = sorted(observed) == list(range(4))
        checks['selected_source_roots'] = lifecycle['roots'] == expected_roots
    else:
        checks['readonly_rule'] = lifecycle['rule_before'] == lifecycle['rule_after'] == source['rule']
        checks['frozen_physical_cohort'] = len(observed) == len(plans) and len(set(observed)) == len(plans) and set(observed) == set(plans)
        checks['compact_physical_cohort'] = len(compact) == len(plans) and len(compact_index) == len(plans) and set(compact_index) == set(plans)
        routes = {'COND', 'TWIN'} if phase == 'EVAL' else {'A', 'B'}
        checks['shared_first_prefix_and_predicate'] = all(set(pair) == routes and len(set(json.dumps(value, sort_keys=True) for value in pair.values())) == 1 for pair in paired_first.values())
    for key in (('physical_games',) if source_phase else ('physical_branches', 'program_setup_counts'))+('environment_counts', 'policy_counts', 'statuses'):
        checks['cost:'+key] = _equal(lifecycle[key], dict(cost[key]) if isinstance(cost[key], Counter) else cost[key])
    return dict(phase=phase, life=life, checks=checks, costs=cost, route_costs=route_costs, roots=expected_roots, source_rows=source_rows)


def analyze(directory):
    started = perf_counter(); read = lambda name: json.loads((directory/name).read_text())
    run, capsule, frozen = [read(name) for name in ('run.json', 'source_capsule.json', 'frozen_inputs.json')]
    checks, phase_results, train_roots, eval_roots = [], {}, [], []
    sources, selections, selection_history = None, None, {}
    def check(name, condition): checks.append(dict(name=name, passed=bool(condition)))
    check('execution_settings_frozen', frozen['status'] == 'frozen' and frozen['settings'] == run['settings'])
    check('frozen_physical_budget', _equal(run['settings'], dict(lifecycles=list(LIVES), queries=['risk1'], source_replicas=4,
        source_games=32, train_roots=16, eval_roots=32, word_length=4, generations=2, beam=2, candidate_slots=50,
        generation_suffixes=1, final_suffixes=4, eval_suffixes=16, generation_branches=9696, final_branches=960,
        evaluation_branches=1536, physical_branches=12192, maximum_environment_transitions=24448000,
        max_steps=2000, p_four=.1, workers=4, version_base=BASE, new_parameter_updates=0)))
    source_roster = [dict(phase=phase, life=life, query='risk1', replica=replica,
                         seed=BASE+{'TRAIN_SOURCE':10000000, 'EVAL_SOURCE':90000000}[phase]+life*1000000+replica)
                     for phase in ('TRAIN_SOURCE', 'EVAL_SOURCE') for life in LIVES for replica in range(4)]
    check('frozen_source_roster', frozen['source_roster'] == source_roster)
    inherited = json.loads(Path(capsule['source_analysis_ref']).read_text())
    inherited_capsule = json.loads((Path(capsule['source_analysis_ref']).parent/'source_capsule.json').read_text())
    check('inherited_audited_capsule', inherited['valid'] and inherited['primary_complete'] and capsule['snapshots'] == inherited_capsule['snapshots'] and capsule['inherited_v168_environment_samples'] == inherited['costs']['new_environment_samples'])
    full_order = ['INPUTS_FROZEN', 'TRAIN_SOURCE', 'G1', 'G1_SELECTED', 'G2', 'G2_SELECTED', 'FINAL', 'PROGRAMS_FROZEN', 'EVAL_SOURCE', 'EVAL']
    check('declared_phase_sequence', run['phase_order'] == full_order[:len(run['phase_order'])])
    with ProcessPoolExecutor(max_workers=4) as pool:
        for phase in ('TRAIN_SOURCE', 'G1', 'G2', 'FINAL', 'EVAL_SOURCE', 'EVAL'):
            if phase not in run['phases']: continue
            source_phase = phase in ('TRAIN_SOURCE', 'EVAL_SOURCE')
            if source_phase: plans, roots = [], []
            else:
                inputs = read(f'inputs_{phase.lower()}.json')
                if phase == 'EVAL':
                    cells, roots = selections, eval_roots
                    check('frozen_final_programs', _equal(read('frozen_programs.json'), cells))
                    check('EVAL:frozen_candidate_cells', _equal(inputs['cells'], cells))
                else:
                    cells, roots = generation_cells(sources, phase, selections), train_roots
                    check(f'{phase}:candidate_cells', _equal(inputs['cells'], cells))
                plans = expected_roster(roots, cells, phase)
                check(f'{phase}:frozen_roster', inputs['roots'] == roots and inputs['branch_roster'] == plans)
            lifecycles = run['phases'][phase]['lifecycles']
            check(f'{phase}:four_lifecycles', len(lifecycles) == 4 and [row['life'] for row in lifecycles] == list(LIVES))
            tasks = [(str(directory), phase, lifecycle, capsule['snapshots'][lifecycle['life']], [plan for plan in plans if plan['life'] == lifecycle['life']], [root for root in roots if root['life'] == lifecycle['life']]) for lifecycle in lifecycles]
            results = list(pool.map(replay_lifecycle, tasks)); phase_results[phase] = results
            for result in results:
                for name, valid in result['checks'].items(): check(f"{phase}:life{result['life']}:{name}", valid)
            if phase == 'TRAIN_SOURCE':
                train_roots = [root for result in results for root in result['roots']]
                sources = source_candidates([row for result in results for row in result['source_rows']])
                check('frozen_source_candidates', _equal(read('source_candidates.json'), sources))
            elif phase == 'EVAL_SOURCE': eval_roots = [root for result in results for root in result['roots']]
            elif phase in ('G1', 'G2', 'FINAL'):
                outcomes = [row for lifecycle in lifecycles for row in read(lifecycle['outcomes_ref'])]
                selections = select_parents(cells, roots, outcomes)
                selection_history[phase] = read(f'selections_{phase.lower()}.json')
                check(f'{phase}:independent_selection', _equal(selection_history[phase], selections))
            print(json.dumps(dict(audited_phase=phase, lifecycles=len(results))), flush=True)
    complete_training = selections is not None and all(cell['complete'] for cell in selections) and selections[0]['phase'] == 'FINAL'
    check('training_failure_stops_future_phases', ('EVAL' not in run['phases']) if not complete_training else True)
    if not complete_training:
        check('incomplete_final_not_frozen', 'PROGRAMS_FROZEN' not in run['phase_order'] and not (directory/'frozen_programs.json').exists())
    expected = None
    if 'EVAL' in phase_results:
        outcomes = [row for lifecycle in run['phases']['EVAL']['lifecycles'] for row in read(lifecycle['outcomes_ref'])]
        expected = eval_summary(eval_roots, outcomes)
        check('independent_eval_statistics', _equal(read('summary.json'), expected))
    all_results = [row for rows in phase_results.values() for row in rows]
    costs = prior.aggregate_costs([row['costs'] for row in all_results])
    costs.update(new_parameter_updates=0, physical_phase_costs={phase: prior.aggregate_costs([row['costs'] for row in rows]) for phase, rows in phase_results.items()},
                 teacher_accounting=[dict(phase=phase, life=row['life'], query=query, **teacher) for phase, data in run['phases'].items() for row in data['lifecycles'] for query, teacher in row['teacher_bank'].items()],
                 this_stage_test_refs=capsule['this_stage_test_refs'], inherited_cost_refs=capsule['cost_refs'])
    costs['route_costs'] = {route: prior.aggregate_costs([row['route_costs'][route] for row in all_results if route in row['route_costs']]) for route in ('SOURCE', 'H2', 'A', 'B', 'COND', 'TWIN')}
    costs['generation_counts'] = dict(sum((Counter(cell['counts']) for cell in (sources or [])), Counter()))
    costs['selection_logical_work'] = {phase: dict(sum((Counter(cell['logical_work']) for cell in cells), Counter())) for phase, cells in selection_history.items()}
    costs['generation_seconds'] = run['generation_seconds']; costs['selection_seconds'] = run.get('selection_seconds', {})
    costs['inherited_v168_environment_samples'] = capsule['inherited_v168_environment_samples']
    check('physical_transition_cap', costs['new_environment_samples'] <= 24448000)
    if run['status'] == 'complete':
        check('complete_physical_roster', costs['physical_games'] == 32 and costs['physical_branches'] == 12192)
        check('completed_phase_sequence', run['phase_order'] == full_order)
    check('declared_run_status', run['status'] == ('complete' if 'EVAL' in phase_results else 'incomplete_training'))
    valid = all(check['passed'] for check in checks)
    result = dict(schema='acfqp.joint_feedback_generation.v169.analysis', valid=valid, complete=valid,
                  primary_complete=expected is not None and expected['complete'], training_complete=complete_training,
                  checks=checks, passed_checks=sum(check['passed'] for check in checks), total_checks=len(checks),
                  comparisons=[] if expected is None else expected['comparisons'], costs=costs,
                  inherited_cost_refs=capsule['cost_refs'], seconds=perf_counter()-started)
    (directory/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, default=PROJECT/'reports/controlled_predictive_joint_feedback_generation_v169')
    result = analyze(parser.parse_args().directory)
    print(json.dumps(dict(valid=result['valid'], primary_complete=result['primary_complete'], passed=result['passed_checks'], checks=result['total_checks'])))
    raise SystemExit(0 if result['valid'] else 1)


if __name__ == '__main__': main()
