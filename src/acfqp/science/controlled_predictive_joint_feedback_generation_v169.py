"""Paid joint generation of one observable condition and two action suffixes."""
from collections import Counter
from copy import deepcopy

from .controlled_predictive_feedback_program_v162 import generate_candidates
from .controlled_predictive_policy_modules_v151 import utility
from .controlled_predictive_consequence_generation_v168 import (
    _issue, _mean, _vector_mean, _terminal_issues, _moments, _pool)

LIVES = (0, 1, 2, 3)
ACTIONS = ('DOWN', 'LEFT', 'RIGHT', 'UP')
BASE = 16900000000
PHASE_SUFFIXES = dict(G1=1, G2=1, FINAL=4)
MODES = ('H2', 'COND', 'TWIN')
METRICS = ('utility', 'reward', 'failure', 'success')
CONTRASTS = {'COND-TWIN': ('COND', 'TWIN'), 'COND-H2': ('COND', 'H2'),
             'TWIN-H2': ('TWIN', 'H2')}
PROGRAM_FIELDS = ('first_action', 'probe_action', 'true_suffix', 'false_suffix')


def program_key(program):
    return (program['first_action'], program['probe_action'],
            *program['true_suffix'], *program['false_suffix'])


def _program(genes):
    return dict(first_action=genes[0], probe_action=genes[1],
                true_suffix=list(genes[2:5]), false_suffix=list(genes[5:8]))


def source_candidates(source_rows, rules_by_life, heldout):
    """Seed from two observed eligible groups without accessing held-out rules."""
    original = generate_candidates(source_rows, rules_by_life, heldout, 'risk1', limit=2)
    parents = [{key: deepcopy(candidate[key]) for key in PROGRAM_FIELDS}
               for candidate in original['candidates']]
    issues = []
    if original['training_lives'] != [life for life in LIVES if life != heldout]:
        _issue(issues, 'source_history_roster')
    for life in LIVES:
        if life == heldout:
            continue
        games = [row for row in original['source_games'] if row['life'] == life]
        if len(games) != 4 or {row['replica'] for row in games} != set(range(4)):
            _issue(issues, 'source_game_roster')
    if len(parents) != 2 or len({program_key(program) for program in parents}) != 2:
        _issue(issues, 'source_program_pool')
    return dict(heldout_life=heldout, query='risk1',
                training_lives=deepcopy(original['training_lives']), parents=parents,
                source_games=deepcopy(original['source_games']),
                counts=deepcopy(original['counts']), complete=not issues, issues=issues)


def mutate(parents):
    """Retain both parents and all 48 substitutions as physical slots."""
    keys = [program_key(parent) for parent in parents]
    if len(keys) != 2 or len(set(keys)) != 2 or any(len(key) != 8 or any(gene not in ACTIONS for gene in key) for key in keys):
        raise ValueError('two distinct eight-gene programs required')
    genes = [list(key) for key in keys]
    for parent in keys:
        for position in range(8):
            for action in ACTIONS:
                if action != parent[position]:
                    child = list(parent)
                    child[position] = action
                    genes.append(child)
    return [dict(candidate_slot=slot, program=_program(key)) for slot, key in enumerate(genes)]


def executable(program, forced=None):
    """Use identical predicate work for conditional and forced suffix arms."""
    if forced not in (None, 'A', 'B'):
        raise ValueError('forced suffix must be A or B')
    result = {key: deepcopy(program[key]) for key in PROGRAM_FIELDS}
    if forced is not None:
        selected = deepcopy(program['true_suffix' if forced == 'A' else 'false_suffix'])
        result.update(true_suffix=deepcopy(selected), false_suffix=deepcopy(selected))
    result['fixed_suffix'] = deepcopy(result['true_suffix'])
    return result


def branch_seed(phase, root, suffix, heldout_life=None):
    if phase == 'EVAL':
        return BASE+50000000+root['life']*1000000+root['replica']*1000+root['slot']*100+suffix
    return BASE+dict(G1=20000000, G2=30000000, FINAL=40000000)[phase]+heldout_life*1000000+root['life']*100000+root['replica']*1000+root['slot']*100+suffix


def _metadata_issues(row, root, phase, heldout, mode, slot, route, arm):
    if row is None:
        return []
    expected = dict(phase=phase, heldout_life=heldout, root_id=root['root_id'],
                    life=root['life'], query='risk1', replica=root['replica'],
                    slot=root['slot'], mode=mode, route=route,
                    candidate_slot=slot, arm=arm)
    return [] if all(row.get(key) == value for key, value in expected.items()) else ['outcome_metadata_mismatch']


def _predicate_issues(left, right):
    if left is None or right is None:
        return []
    a, b = left['module']['predicate'], right['module']['predicate']
    issues = []
    if a not in (None, True, False) or b not in (None, True, False) or a is not b:
        _issue(issues, 'paired_predicate_mismatch')
    if a is None and any(left[key] != right[key] for key in ('score', 'steps', 'status', 'components', 'utility')):
        _issue(issues, 'unobserved_predicate_outcome_mismatch')
    return issues


def _aggregate_roots(root_vectors, roots, histories):
    per_history = []
    for life in histories:
        vectors = [vector for root_life, vector in root_vectors if root_life == life]
        vector = _vector_mean(vectors)
        per_history.append(dict(life=life, roots=len(vectors), component_mean=vector,
                                utility=utility(vector, 'risk1')))
    return _vector_mean(row['component_mean'] for row in per_history), per_history


def choose_parents(cells, roots, outcomes, phase):
    """Compose paid terminal A/B continuations; rank conditional full vectors."""
    suffixes = PHASE_SUFFIXES[phase]
    index, duplicates = {}, set()
    for row in outcomes:
        if row['phase'] != phase:
            continue
        key = row['heldout_life'], row['root_id'], row['suffix'], row['mode']
        if key in index:
            duplicates.add(key)
        index[key] = row
    selected_cells = []
    for cell in cells:
        heldout = cell['heldout_life']
        histories = [life for life in LIVES if life != heldout]
        pool = [root for root in roots if root['life'] in histories and root['query'] == 'risk1']
        issues = list(cell['issues'])
        if not cell['complete']:
            _issue(issues, 'candidate_cell_incomplete')
        if cell['phase'] != phase or cell['query'] != 'risk1':
            _issue(issues, 'candidate_phase_mismatch')
        count = 2 if phase == 'FINAL' else 50
        if len(cell['slots']) != count or [row['candidate_slot'] for row in cell['slots']] != list(range(count)):
            _issue(issues, 'candidate_slot_roster')
        for life in histories:
            roster = [root for root in pool if root['life'] == life]
            if len(roster) != 4 or len({root['root_id'] for root in roster}) != 4 or {(root['replica'], root['slot']) for root in roster} != {(replica, slot) for replica in range(2) for slot in range(2)} or any(root['phase'] != 'TRAIN_SOURCE' for root in roster):
                _issue(issues, 'training_root_roster')
        expected = {(heldout, root['root_id'], suffix, mode)
                    for root in pool for suffix in range(suffixes)
                    for mode in ['H2']+[f'P{slot["candidate_slot"]}_{arm}' for slot in cell['slots'] for arm in ('A', 'B')]}
        if any(key[0] == heldout and key not in expected for key in index):
            _issue(issues, 'unexpected_outcome')
        work = Counter(paired_terminal_trials_examined=0, terminal_vector_differences=0,
                       conditional_vectors_composed=0)
        scores = []
        for candidate in cell['slots']:
            slot, program = candidate['candidate_slot'], candidate['program']
            candidate_issues = list(issues)
            root_vectors = {mode: [] for mode in ('COND', 'A', 'B', 'H2')}
            predicates = Counter()
            for root in pool:
                vectors = {mode: [] for mode in root_vectors}
                for suffix in range(suffixes):
                    work['paired_terminal_trials_examined'] += 1
                    seed = branch_seed(phase, root, suffix, heldout)
                    modes = dict(H2='H2', A=f'P{slot}_A', B=f'P{slot}_B')
                    rows = {arm: index.get((heldout, root['root_id'], suffix, mode)) for arm, mode in modes.items()}
                    trial_issues = []
                    for arm, row in rows.items():
                        for issue in _terminal_issues(row, seed):
                            _issue(trial_issues, issue)
                        key = (heldout, root['root_id'], suffix, modes[arm])
                        if key in duplicates:
                            _issue(trial_issues, 'duplicate_outcome')
                        for issue in _metadata_issues(row, root, phase, heldout, modes[arm],
                                None if arm == 'H2' else slot, arm, 'H2' if arm == 'H2' else 'FEEDBACK'):
                            _issue(trial_issues, issue)
                        if row is not None and (row['module']['arm'] != ('H2' if arm == 'H2' else 'FEEDBACK') or
                                row['module']['program'] != (None if arm == 'H2' else executable(program, arm))):
                            _issue(trial_issues, 'executable_program_mismatch')
                    for issue in _predicate_issues(rows['A'], rows['B']):
                        _issue(trial_issues, issue)
                    for issue in trial_issues:
                        _issue(candidate_issues, issue)
                    if trial_issues:
                        continue
                    predicate = rows['A']['module']['predicate']
                    predicates['true' if predicate is True else 'false' if predicate is False else 'unobserved'] += 1
                    picked = rows['B'] if predicate is False else rows['A']
                    for arm in ('A', 'B', 'H2'):
                        vectors[arm].append(rows[arm]['components'])
                    vectors['COND'].append(picked['components'])
                    work['conditional_vectors_composed'] += 1
                    work['terminal_vector_differences'] += 3
                if len(vectors['COND']) == suffixes:
                    for mode in root_vectors:
                        root_vectors[mode].append((root['life'], _vector_mean(vectors[mode])))
            complete = not candidate_issues
            aggregated = {mode: _aggregate_roots(root_vectors[mode], pool, histories) for mode in root_vectors} if complete else {}
            per_history = []
            if complete:
                for index_history, life in enumerate(histories):
                    vector = aggregated['COND'][1][index_history]['component_mean']
                    baseline = aggregated['H2'][1][index_history]['component_mean']
                    delta = [a-b for a, b in zip(vector, baseline, strict=True)]
                    per_history.append(dict(life=life, roots=4, component_mean=vector,
                        utility=utility(vector, 'risk1'), component_delta_vs_H2=delta, gain=utility(delta, 'risk1'),
                        unconditional_A=aggregated['A'][1][index_history],
                        unconditional_B=aggregated['B'][1][index_history]))
                vector = aggregated['COND'][0]
                delta = [a-b for a, b in zip(vector, aggregated['H2'][0], strict=True)]
            else:
                vector, delta = None, None
            unconditional = {arm: dict(component_mean=None if not complete else aggregated[arm][0],
                    utility=None if not complete else utility(aggregated[arm][0], 'risk1'),
                    per_history=[] if not complete else aggregated[arm][1]) for arm in ('A', 'B')}
            scores.append(dict(candidate_slot=slot, program=deepcopy(program), complete=complete,
                issues=candidate_issues, train_component_mean=vector,
                train_utility=None if vector is None else utility(vector, 'risk1'),
                train_component_delta_vs_H2=delta, train_gain=None if delta is None else utility(delta, 'risk1'),
                unconditional=unconditional, predicate_counts=dict(predicates), per_history=per_history))
        complete = not issues and bool(scores) and all(row['complete'] for row in scores)
        chosen, seen = [], set()
        if complete:
            for score in sorted(scores, key=lambda row: (-row['train_utility'], program_key(row['program']), row['candidate_slot'])):
                key = program_key(score['program'])
                if key in seen:
                    continue
                chosen.append(score)
                seen.add(key)
                if len(chosen) == (1 if phase == 'FINAL' else 2):
                    break
            if len(chosen) != (1 if phase == 'FINAL' else 2):
                complete = False
                _issue(issues, 'distinct_parent_pool')
                chosen = []
        if not complete:
            _issue(issues, 'incomplete_terminal_cohort')
        selected = deepcopy(cell)
        selected.update(complete=complete, issues=issues, slot_scores=scores,
            selection_basis='conditional_terminal_utility', logical_work=dict(work),
            selected_parents=[deepcopy(row['program']) for row in chosen],
            selected_slots=[row['candidate_slot'] for row in chosen])
        if phase == 'FINAL':
            selected['selected_twin'] = None if not chosen else ('A' if chosen[0]['unconditional']['A']['utility'] >= chosen[0]['unconditional']['B']['utility'] else 'B')
        selected_cells.append(selected)
    return selected_cells


def summarize_eval(roots, outcomes):
    """Use all fixed fresh roots and pair conditional, frozen twin, and H2."""
    roots = [root for root in roots if root['query'] == 'risk1']
    roster_issues = []
    if len(roots) != 32 or len({root['root_id'] for root in roots}) != 32 or any(root['phase'] != 'EVAL_SOURCE' for root in roots):
        _issue(roster_issues, 'eval_root_roster')
    for life in LIVES:
        roster = [root for root in roots if root['life'] == life]
        if len(roster) != 8 or {(root['replica'], root['slot']) for root in roster} != {(replica, slot) for replica in range(4) for slot in range(2)}:
            _issue(roster_issues, 'eval_root_roster')
    index, duplicates = {}, set()
    for row in outcomes:
        key = row['root_id'], row['suffix'], row['mode']
        if key in index:
            duplicates.add(key)
        index[key] = row
    expected = {(root['root_id'], suffix, mode) for root in roots for suffix in range(16) for mode in MODES}
    if set(index)-expected:
        _issue(roster_issues, 'unexpected_outcome')
    root_rows = []
    for root in roots:
        issues, pairs = list(roster_issues), []
        values = {mode: [] for mode in MODES}
        differences = {name: [] for name in CONTRASTS}
        for suffix in range(16):
            pair_issues = list(roster_issues)
            seed = branch_seed('EVAL', root, suffix)
            rows = {mode: index.get((root['root_id'], suffix, mode)) for mode in MODES}
            for mode, row in rows.items():
                for issue in _terminal_issues(row, seed):
                    _issue(pair_issues, issue)
                if (root['root_id'], suffix, mode) in duplicates:
                    _issue(pair_issues, 'duplicate_outcome')
                for issue in _metadata_issues(row, root, 'EVAL', root['life'], mode, None, mode,
                                              'H2' if mode == 'H2' else 'FEEDBACK'):
                    _issue(pair_issues, issue)
                if row is not None and row['module']['arm'] != ('H2' if mode == 'H2' else 'FEEDBACK'):
                    _issue(pair_issues, 'outcome_metadata_mismatch')
            for issue in _predicate_issues(rows['COND'], rows['TWIN']):
                _issue(pair_issues, issue)
            if rows['COND'] is not None and rows['TWIN'] is not None:
                conditional, twin = rows['COND']['module']['program'], rows['TWIN']['module']['program']
                if conditional['first_action'] != twin['first_action'] or conditional['probe_action'] != twin['probe_action'] or twin['true_suffix'] != twin['false_suffix'] or twin['true_suffix'] not in (conditional['true_suffix'], conditional['false_suffix']):
                    _issue(pair_issues, 'frozen_twin_program_mismatch')
            complete = not pair_issues
            for mode, row in rows.items():
                values[mode].append(dict(zip(METRICS, [utility(row['components'], 'risk1'), *row['components']]))
                                    if complete else {metric: None for metric in METRICS})
            component_deltas = {}
            for name, (left, right) in CONTRASTS.items():
                delta = [a-b for a, b in zip(rows[left]['components'], rows[right]['components'], strict=True)] if complete else None
                component_deltas[name] = delta
                differences[name].append(dict(zip(METRICS, [utility(delta, 'risk1'), *delta]))
                                         if complete else {metric: None for metric in METRICS})
            pairs.append(dict(suffix=suffix, seed=seed, complete=complete, issues=pair_issues,
                outcomes=deepcopy(rows), component_deltas=component_deltas))
            for issue in pair_issues:
                _issue(issues, issue)
        root_rows.append(dict(**{key: root[key] for key in ('root_id', 'life', 'query', 'replica', 'slot')},
            complete=not issues, issues=issues, pairs=pairs,
            modes={mode: {metric: _moments(row[metric] for row in values[mode]) for metric in METRICS} for mode in MODES},
            contrasts={name: {metric: _moments(row[metric] for row in differences[name]) for metric in METRICS} for name in CONTRASTS}))
    comparisons = []
    for contrast in CONTRASTS:
        histories = []
        for life in LIVES:
            selected = [row for row in root_rows if row['life'] == life]
            histories.append(dict(life=life, roots=len(selected), metrics={metric: _pool([row['contrasts'][contrast][metric] for row in selected], 8) for metric in METRICS}))
        metrics = {metric: _pool([row['metrics'][metric] for row in histories], 4) for metric in METRICS}
        comparisons.append(dict(query='risk1', contrast=contrast, roots=len(roots),
            complete=all(metric['complete'] for metric in metrics.values()), metrics=metrics, per_history=histories))
    diagnostics = []
    for mode in MODES:
        present = [index[root['root_id'], suffix, mode] for root in roots for suffix in range(16)
                   if (root['root_id'], suffix, mode) in index]
        predicates = Counter('true' if row['module']['predicate'] is True else 'false' if row['module']['predicate'] is False else 'unobserved' for row in present)
        diagnostics.append(dict(mode=mode, branches=len(roots)*16, present_branches=len(present),
            mean_prefix_steps=_mean(row['module']['prefix_steps'] for row in present) if present else None,
            mean_attempts=_mean(row['module']['attempts'] for row in present) if present else None,
            predicate_counts=dict(predicates), exit_counts=dict(Counter(row['module']['exit_reason'] for row in present))))
    observed, changed, both_roots = 0, 0, 0
    for root in root_rows:
        seen = set()
        for pair in root['pairs']:
            if not pair['complete']:
                continue
            conditional, twin = pair['outcomes']['COND']['module'], pair['outcomes']['TWIN']['module']
            if conditional['predicate'] is not None:
                seen.add(conditional['predicate'])
                observed += 1
                changed += conditional['actual_word'][1:] != twin['actual_word'][1:]
        both_roots += seen == {True, False}
    return dict(schema='acfqp.joint_feedback_generation.v169.summary',
        complete=bool(root_rows) and all(row['complete'] for row in root_rows) and all(row['complete'] for row in comparisons),
        root_rows=root_rows, comparisons=comparisons, program_diagnostics=diagnostics,
        feedback_diagnostics=dict(predicate_observed_branches=observed, suffixes_differ_from_twin=changed,
                                  roots_with_both_predicates=both_roots),
        logical_work=dict(outcome_rows_supplied=len(outcomes), paired_suffixes_examined=len(roots)*16,
                          contrast_component_vectors=sum(pair['complete'] for root in root_rows for pair in root['pairs'])*3),
        uncertainty='Normal paired-suffix CI conditional on 32 fixed fresh risk1 EVAL roots, four histories and frozen feedback programs; equal16 suffixes/root, eight roots/history and four histories.')
