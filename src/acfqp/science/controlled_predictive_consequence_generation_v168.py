"""Two fixed generations of paid whole-word consequence selection."""
from collections import Counter
from copy import deepcopy
from math import sqrt

from .controlled_predictive_policy_modules_v151 import utility
from .controlled_predictive_program_consolidation_v161 import generate_candidates

LIVES = (0, 1, 2, 3)
ACTIONS = ('DOWN', 'LEFT', 'RIGHT', 'UP')
PHASE_SUFFIXES = dict(G1=2, G2=2, FINAL=4)
BASE = 16800000000
MODES = ('H2', 'FREQ', 'CONS')
METRICS = ('utility', 'reward', 'failure', 'success')
CONTRASTS = {'CONS-FREQ': ('CONS', 'FREQ'), 'CONS-H2': ('CONS', 'H2'), 'FREQ-H2': ('FREQ', 'H2')}


def source_frequencies(source_rows, heldout):
    """Keep all 4**4 canonical source words and the existing D4 work counts."""
    original = generate_candidates(source_rows, heldout, 'risk1', limit=256)
    frequencies = [dict(word=deepcopy(row['word']), frequency=row['occurrences']) for row in original['candidates']]
    issues = []
    if original['training_lives'] != [life for life in LIVES if life != heldout]:
        issues.append('source_history_roster')
    for life in LIVES:
        if life == heldout:
            continue
        games = [row for row in original['source_games'] if row['life'] == life]
        if len(games) != 4 or {row['replica'] for row in games} != set(range(4)):
            if 'source_game_roster' not in issues:
                issues.append('source_game_roster')
    if len(frequencies) < 2:
        issues.append('source_word_pool')
    return dict(heldout_life=heldout, query='risk1', source_frequencies=frequencies,
        training_lives=deepcopy(original['training_lives']), counts=deepcopy(original['counts']),
        source_games=deepcopy(original['source_games']), complete=not issues, issues=issues)


def seed_parents(cell):
    if not cell['complete']:
        return []
    return [deepcopy(row['word']) for row in sorted(cell['source_frequencies'], key=lambda row: (-row['frequency'], tuple(row['word'])))[:2]]


def mutate(parents):
    """Keep two parent slots and all 24 substitutions, including duplicates."""
    if len(parents) != 2 or len({tuple(word) for word in parents}) != 2 or any(len(word) != 4 or any(action not in ACTIONS for action in word) for word in parents):
        raise ValueError('two distinct four-action parents required')
    words = [list(word) for word in parents]
    for parent in parents:
        for position in range(4):
            for action in ACTIONS:
                if action == parent[position]:
                    continue
                child = list(parent)
                child[position] = action
                words.append(child)
    return [dict(candidate_slot=slot, word=word) for slot, word in enumerate(words)]


def branch_seed(phase, root, suffix, heldout_life=None):
    if phase == 'EVAL':
        return BASE+50000000+root['life']*1000000+root['replica']*1000+root['slot']*100+suffix
    return BASE+dict(G1=20000000, G2=30000000, FINAL=40000000)[phase]+heldout_life*1000000+root['life']*100000+root['replica']*1000+root['slot']*100+suffix


def _issue(issues, name):
    if name not in issues:
        issues.append(name)


def _mean(values):
    values = tuple(values)
    return sum(values)/len(values)


def _vector_mean(vectors):
    vectors = tuple(vectors)
    return [_mean(vector[k] for vector in vectors) for k in range(3)]


def _terminal_issues(row, seed):
    if row is None:
        return ['missing_outcome']
    issues = []
    if row['seed'] != seed:
        issues.append('paired_seed_mismatch')
    if row['status'] not in ('WON', 'LOST') or row['utility'] is None:
        issues.append('nonterminal_outcome')
    else:
        if row['components'][0] != row['score']/2048. or row['components'][1:] != [float(row['status'] == 'LOST'), float(row['status'] == 'WON')]:
            issues.append('terminal_component_mismatch')
        if row['utility'] != utility(row['components'], 'risk1'):
            issues.append('recorded_utility_mismatch')
    return issues


def choose_parents(cells, roots, outcomes, phase):
    """Rank all paid slots and keep distinct words under the frozen route rule."""
    suffixes = PHASE_SUFFIXES[phase]
    index, duplicates = {}, set()
    for row in outcomes:
        if row['phase'] != phase:
            continue
        key = row['heldout_life'], row['root_id'], row['suffix'], row['mode']
        if key in index:
            duplicates.add(key)
        index[key] = row
    result = []
    for cell in cells:
        heldout, route = cell['heldout_life'], cell['route']
        histories = [life for life in LIVES if life != heldout]
        pool = [root for root in roots if root['life'] in histories and root['query'] == 'risk1']
        issues = list(cell['issues'])
        if not cell['complete']:
            _issue(issues, 'candidate_cell_incomplete')
        if cell['phase'] != phase:
            _issue(issues, 'candidate_phase_mismatch')
        expected_slots = 2 if phase == 'FINAL' else 26
        if len(cell['slots']) != expected_slots or [row['candidate_slot'] for row in cell['slots']] != list(range(expected_slots)):
            _issue(issues, 'candidate_slot_roster')
        for life in histories:
            selected = [root for root in pool if root['life'] == life]
            if len(selected) != 4 or len({root['root_id'] for root in selected}) != 4 or {(root['replica'], root['slot']) for root in selected} != {(replica, slot) for replica in range(2) for slot in range(2)}:
                _issue(issues, 'training_root_roster')
        frequency_index = {tuple(row['word']): row['frequency'] for row in cell['source_frequencies']}
        work = Counter(paired_terminal_trials_examined=0, terminal_vector_differences=0, frequency_lookups=0)
        scores = []
        for candidate in cell['slots']:
            candidate_slot, word = candidate['candidate_slot'], candidate['word']
            candidate_issues, root_vectors, root_deltas = list(issues), [], []
            for root in pool:
                vectors, deltas = [], []
                for suffix in range(suffixes):
                    work['paired_terminal_trials_examined'] += 1
                    seed = branch_seed(phase, root, suffix, heldout)
                    keys = [(heldout, root['root_id'], suffix, mode) for mode in ('H2', f'{route}_W{candidate_slot}')]
                    rows = [index.get(key) for key in keys]
                    trial_issues = []
                    for key, row in zip(keys, rows, strict=True):
                        for issue in _terminal_issues(row, seed):
                            _issue(trial_issues, issue)
                        if key in duplicates:
                            _issue(trial_issues, 'duplicate_outcome')
                        if row is not None and (row['query'] != 'risk1' or row['life'] != root['life'] or row['candidate_slot'] != (None if row['mode'] == 'H2' else candidate_slot) or row['route'] != ('H2' if row['mode'] == 'H2' else route)):
                            _issue(trial_issues, 'outcome_metadata_mismatch')
                    for issue in trial_issues:
                        _issue(candidate_issues, issue)
                    if trial_issues:
                        continue
                    h2, selected = rows
                    vectors.append(selected['components'])
                    deltas.append([x-y for x, y in zip(selected['components'], h2['components'], strict=True)])
                    work['terminal_vector_differences'] += 1
                if len(vectors) == suffixes:
                    root_vectors.append((root['life'], _vector_mean(vectors)))
                    root_deltas.append((root['life'], _vector_mean(deltas)))
            complete = not candidate_issues
            per_history = []
            if complete:
                for life in histories:
                    vectors = [vector for root_life, vector in root_vectors if root_life == life]
                    deltas = [vector for root_life, vector in root_deltas if root_life == life]
                    vector, delta = _vector_mean(vectors), _vector_mean(deltas)
                    per_history.append(dict(life=life, roots=len(vectors), component_mean=vector,
                        utility=utility(vector, 'risk1'), component_delta_vs_H2=delta, gain=utility(delta, 'risk1')))
                vector = _vector_mean(row['component_mean'] for row in per_history)
                delta = _vector_mean(row['component_delta_vs_H2'] for row in per_history)
            else:
                vector, delta = None, None
            work['frequency_lookups'] += 1
            scores.append(dict(candidate_slot=candidate_slot, word=deepcopy(word), frequency=frequency_index.get(tuple(word), 0),
                complete=complete, issues=candidate_issues, train_component_mean=vector,
                train_utility=None if vector is None else utility(vector, 'risk1'),
                train_component_delta_vs_H2=delta, train_gain=None if delta is None else utility(delta, 'risk1'),
                per_history=per_history))
        complete = not issues and bool(scores) and all(row['complete'] for row in scores)
        terminal = phase == 'FINAL' or route == 'CONS'
        basis = 'terminal_utility' if terminal else 'source_frequency'
        chosen, seen = [], set()
        if complete:
            ordered = sorted(scores, key=lambda row: (-(row['train_utility'] if terminal else row['frequency']), tuple(row['word']), row['candidate_slot']))
            for score in ordered:
                word = tuple(score['word'])
                if word in seen:
                    continue
                chosen.append(score)
                seen.add(word)
                if len(chosen) == (1 if phase == 'FINAL' else 2):
                    break
            if len(chosen) != (1 if phase == 'FINAL' else 2):
                complete = False
                _issue(issues, 'distinct_parent_pool')
                chosen = []
        if not complete:
            _issue(issues, 'incomplete_terminal_cohort')
        selected = deepcopy(cell)
        selected.update(complete=complete, issues=issues, slot_scores=scores, selection_basis=basis,
            selected_parents=[deepcopy(row['word']) for row in chosen], selected_slots=[row['candidate_slot'] for row in chosen],
            logical_work=dict(work))
        result.append(selected)
    return result


def final_selection(cells, roots, outcomes):
    return choose_parents(cells, roots, outcomes, 'FINAL')


def _moments(values):
    values = tuple(values)
    complete = bool(values) and all(value is not None for value in values)
    average = _mean(values) if complete else None
    variance = sum((value-average)**2 for value in values)/(len(values)-1) if complete else None
    return dict(n=len(values), complete=complete, mean=average, sample_variance=variance,
                mean_variance=variance/len(values) if complete else None)


def _pool(rows, expected):
    complete = len(rows) == expected and all(row['complete'] for row in rows)
    average = _mean(row['mean'] for row in rows) if complete else None
    variance = sum(row['mean_variance'] for row in rows)/expected**2 if complete else None
    se = sqrt(variance) if complete else None
    return dict(complete=complete, mean=average, mean_variance=variance, conditional_suffix_se=se,
                conditional_suffix_ci95=None if se is None else [average-1.96*se, average+1.96*se])


def summarize_eval(roots, outcomes):
    """Pair all three fresh EVAL modes; retain every cutoff and fixed root."""
    roots = [root for root in roots if root['query'] == 'risk1']
    roster_issues = []
    if len(roots) != 32 or len({root['root_id'] for root in roots}) != 32 or any(root.get('phase') != 'EVAL_SOURCE' for root in roots):
        roster_issues.append('eval_root_roster')
    for life in LIVES:
        selected = [root for root in roots if root['life'] == life]
        if len(selected) != 8 or {(root['replica'], root['slot']) for root in selected} != {(replica, slot) for replica in range(4) for slot in range(2)}:
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
                if row is not None and (row['life'] != root['life'] or row['query'] != 'risk1' or row['phase'] != 'EVAL' or row['heldout_life'] != root['life']):
                    _issue(pair_issues, 'outcome_metadata_mismatch')
            complete = not pair_issues
            for mode, row in rows.items():
                values[mode].append(dict(zip(METRICS, [utility(row['components'], 'risk1'), *row['components']]))
                                    if complete else {metric: None for metric in METRICS})
            component_deltas = {}
            for name, (left, right) in CONTRASTS.items():
                delta = [x-y for x, y in zip(rows[left]['components'], rows[right]['components'], strict=True)] if complete else None
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
        metrics = {metric: _pool([history['metrics'][metric] for history in histories], 4) for metric in METRICS}
        comparisons.append(dict(query='risk1', contrast=contrast, roots=len(roots),
            complete=all(metric['complete'] for metric in metrics.values()), metrics=metrics, per_history=histories))
    diagnostics = []
    for mode in MODES:
        present = [index[root['root_id'], suffix, mode] for root in roots for suffix in range(16)
                   if (root['root_id'], suffix, mode) in index]
        diagnostics.append(dict(mode=mode, branches=len(roots)*16, present_branches=len(present),
            mean_prefix_steps=_mean(row['module']['prefix_steps'] for row in present) if present else None,
            mean_attempts=_mean(row['module']['attempts'] for row in present) if present else None,
            exit_counts=dict(Counter(row['module']['exit_reason'] for row in present))))
    return dict(schema='acfqp.consequence_generation.v168.summary', complete=all(row['complete'] for row in comparisons),
        root_rows=root_rows, comparisons=comparisons, program_diagnostics=diagnostics,
        logical_work=dict(outcome_rows_supplied=len(outcomes), paired_suffixes_examined=len(roots)*16,
                          contrast_component_vectors=sum(pair['complete'] for root in root_rows for pair in root['pairs'])*3),
        uncertainty='Normal paired-suffix CI conditional on 32 fixed fresh risk1 EVAL roots, four histories and frozen words; equal16 suffixes/root, eight roots/history and four histories.')
