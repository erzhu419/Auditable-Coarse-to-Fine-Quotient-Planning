"""Frozen S0 forced-B confirmation on fresh paired V164 EVAL roots."""
from collections import Counter
from copy import deepcopy
from math import sqrt

from .controlled_predictive_policy_modules_v151 import utility
from .controlled_predictive_program_headroom_v165 import semantic_key

LIVES = (0, 1, 2, 3)
SUFFIXES = tuple(range(16))
MODES = ('H2', 'S0_B')
METRICS = ('utility', 'reward', 'failure', 'success')
CONTRAST = 'S0_B-H2'
BASE = 16700000000


def extract_candidate(candidates, v166_roster):
    """Use the original fold-zero first exact S0/risk1 semantic match."""
    stratum = next((row for row in v166_roster['strata'] if row['stratum_id'] == 'S0' and row['query'] == 'risk1'), None)
    if stratum is None or stratum['source_semantics'] is None:
        raise ValueError('frozen V166 S0 risk1 semantics required')
    cell = next((row for row in candidates if (row['heldout_life'], row['query']) == (0, 'risk1')), None)
    source = next((row for row in cell['candidates'] if semantic_key(row) == semantic_key(stratum['source_semantics'])), None) if cell else None
    if source is None:
        raise ValueError('original fold-zero S0 candidate required')
    return deepcopy(source)


def build_program(candidate):
    """Execute both observed bit leaves as the frozen original B alternative."""
    program = deepcopy(candidate)
    program['true_suffix'] = list(candidate['false_suffix'])
    program['false_suffix'] = list(candidate['false_suffix'])
    return program


def branch_seed(root, suffix):
    return BASE+50000000+root['life']*1000000+root['replica']*1000+root['slot']*100+suffix


def build_roster(roots):
    """Pair the fixed program and H2 on every retained risk1 EVAL root."""
    return [dict(branch_id=f'{root["root_id"]}:{suffix}:{mode}', root_id=root['root_id'],
        life=root['life'], query='risk1', replica=root['replica'], slot=root['slot'],
        suffix=suffix, mode=mode, seed=branch_seed(root, suffix), phase='EVAL',
        heldout_life=root['life'], arm='H2' if mode == 'H2' else 'FEEDBACK')
        for root in roots if root['query'] == 'risk1' for suffix in SUFFIXES for mode in MODES]


def _mean(values):
    values = tuple(values)
    return sum(values)/len(values)


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


def _issue(issues, name):
    if name not in issues:
        issues.append(name)


def _root_roster_issues(roots):
    issues = []
    if len(roots) != 32 or len({root['root_id'] for root in roots}) != 32:
        issues.append('eval_root_roster')
    for life in LIVES:
        pool = [root for root in roots if root['life'] == life]
        if len(pool) != 8 or {(root['replica'], root['slot']) for root in pool} != {(replica, slot) for replica in range(4) for slot in range(2)}:
            _issue(issues, 'eval_root_roster')
    if any(root.get('phase') != 'EVAL_SOURCE' for root in roots):
        _issue(issues, 'eval_root_phase')
    return issues


def _values(row):
    return dict(zip(METRICS, [utility(row['components'], 'risk1'), *row['components']]))


def _diagnostics(roots, index):
    diagnostics = []
    for mode in MODES:
        rows = [index.get((root['root_id'], suffix, mode)) for root in roots for suffix in SUFFIXES]
        present = [row for row in rows if row is not None]
        modules = [row['module'] for row in present]
        diagnostics.append(dict(mode=mode, branches=len(rows), present_branches=len(present),
            complete=len(rows) == 512 and len(present) == 512 and all(row['status'] in ('WON', 'LOST') for row in present),
            mean_prefix_steps=_mean(module['prefix_steps'] for module in modules) if modules else None,
            mean_attempts=_mean(module['attempts'] for module in modules) if modules else None,
            mean_continuation_steps=_mean(row['steps']-row['module']['prefix_steps'] for row in present) if present else None,
            probe_branches=sum(module['predicate'] is not None for module in modules),
            same_step_fallback_branches=sum(module['exit_reason'] == 'illegal' for module in modules),
            continuation_branches=sum(row['steps'] > row['module']['prefix_steps'] for row in present),
            exit_counts=dict(Counter(module['exit_reason'] for module in modules)),
            predicate_counts=dict(Counter('none' if module['predicate'] is None else 'true' if module['predicate'] else 'false' for module in modules))))
    return diagnostics


def summarize(roots, outcomes):
    """Score only the independent fresh forced-B/H2 paired outcomes."""
    roots = [root for root in roots if root['query'] == 'risk1']
    roster_issues = _root_roster_issues(roots)
    expected = {(row['root_id'], row['suffix'], row['mode']): row for row in build_roster(roots)}
    index, duplicates, unexpected = {}, set(), 0
    for row in outcomes:
        key = row['root_id'], row['suffix'], row['mode']
        if key in index:
            duplicates.add(key)
        index[key] = row
        unexpected += int(key not in expected)
    root_rows = []
    for root in roots:
        issues, pairs, mode_values, deltas = list(roster_issues), [], {mode: [] for mode in MODES}, []
        if unexpected:
            _issue(issues, 'unexpected_outcome')
        for suffix in SUFFIXES:
            pair_issues, rows = [], {}
            for mode in MODES:
                key = root['root_id'], suffix, mode
                row, plan = index.get(key), expected[key]
                rows[mode] = row
                if row is None:
                    _issue(pair_issues, 'missing_outcome')
                    continue
                if key in duplicates:
                    _issue(pair_issues, 'duplicate_outcome')
                if row['seed'] != plan['seed']:
                    _issue(pair_issues, 'paired_seed_mismatch')
                if any(row.get(field) != plan[field] for field in ('branch_id', 'life', 'query', 'replica', 'slot', 'phase', 'heldout_life', 'arm')):
                    _issue(pair_issues, 'outcome_metadata_mismatch')
                if row['status'] not in ('WON', 'LOST') or row['utility'] is None:
                    _issue(pair_issues, 'nonterminal_outcome')
                else:
                    if row['components'][0] != row['score']/2048. or row['components'][1:] != [float(row['status'] == 'LOST'), float(row['status'] == 'WON')]:
                        _issue(pair_issues, 'terminal_component_mismatch')
                    if row['utility'] != utility(row['components'], 'risk1'):
                        _issue(pair_issues, 'recorded_utility_mismatch')
            complete = not pair_issues and not roster_issues and not unexpected
            values = {mode: _values(rows[mode]) if complete else {metric: None for metric in METRICS} for mode in MODES}
            delta = [rows['S0_B']['components'][k]-rows['H2']['components'][k] for k in range(3)] if complete else None
            utility_delta = utility(delta, 'risk1') if complete else None
            deltas.append(dict(zip(METRICS, [utility_delta, *(delta if delta is not None else [None]*3)])))
            for mode in MODES:
                mode_values[mode].append(values[mode])
            pairs.append(dict(suffix=suffix, seed=branch_seed(root, suffix), complete=complete, issues=pair_issues,
                outcomes=deepcopy(rows), component_delta=delta, utility_delta=utility_delta))
            for issue in pair_issues:
                _issue(issues, issue)
        modes = {mode: {metric: _moments(row[metric] for row in mode_values[mode]) for metric in METRICS} for mode in MODES}
        contrasts = {CONTRAST: {metric: _moments(row[metric] for row in deltas) for metric in METRICS}}
        root_rows.append(dict(**{key: root[key] for key in ('root_id', 'life', 'query', 'replica', 'slot')},
            complete=not issues, issues=issues, pairs=pairs, modes=modes, contrasts=contrasts))
    histories = []
    for life in LIVES:
        selected = [row for row in root_rows if row['life'] == life]
        histories.append(dict(life=life, roots=len(selected),
            metrics={metric: _pool([row['contrasts'][CONTRAST][metric] for row in selected], 8) for metric in METRICS}))
    metrics = {metric: _pool([history['metrics'][metric] for history in histories], 4) for metric in METRICS}
    comparison = dict(query='risk1', contrast=CONTRAST, roots=len(roots),
        complete=all(metric['complete'] for metric in metrics.values()), metrics=metrics, per_history=histories)
    return dict(schema='acfqp.fixed_program.v167.summary', query='risk1', contrast=CONTRAST,
        complete=comparison['complete'], root_count=len(roots), comparison=comparison, root_rows=root_rows,
        program_diagnostics=_diagnostics(roots, index),
        logical_work=dict(outcome_rows_supplied=len(outcomes), paired_suffixes_examined=len(roots)*16,
                          component_difference_vectors=sum(pair['complete'] for row in root_rows for pair in row['pairs'])),
        uncertainty='Normal paired-suffix CI conditional on 32 fixed risk1 EVAL roots and four histories; 16 suffixes/root, equal eight roots/history and four histories.')
