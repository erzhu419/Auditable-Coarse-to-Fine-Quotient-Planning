"""Fixed-root headroom from already paid, semantically matched V164 arms."""
from collections import Counter
from copy import deepcopy
from math import sqrt

from .controlled_predictive_policy_modules_v151 import QUERIES, utility

LIVES = (0, 1, 2, 3)
SUFFIXES = (0, 1, 2, 3)
ROOTS_PER_HISTORY = 4
SPLITS = {'primary': ((0, 1), (2, 3)), 'reverse': ((2, 3), (0, 1))}
MODES = ('H2', 'A', 'B', 'LEARNED', 'GLOBAL', 'ROOT', 'BIT_REFIT', 'GLOBAL_REFIT', 'TEST_ROOT_MEAN_ORACLE')
METRICS = ('utility', 'reward', 'failure', 'success')
CONTRASTS = {
    'ROOT-BIT_REFIT': ('ROOT', 'BIT_REFIT'), 'ROOT-GLOBAL_REFIT': ('ROOT', 'GLOBAL_REFIT'),
    'BIT_REFIT-GLOBAL_REFIT': ('BIT_REFIT', 'GLOBAL_REFIT'),
    'BIT_REFIT-H2': ('BIT_REFIT', 'H2'), 'GLOBAL_REFIT-H2': ('GLOBAL_REFIT', 'H2'),
    'ROOT-LEARNED': ('ROOT', 'LEARNED'), 'ROOT-GLOBAL': ('ROOT', 'GLOBAL'),
    'ROOT-H2': ('ROOT', 'H2'), 'LEARNED-GLOBAL': ('LEARNED', 'GLOBAL'),
    'LEARNED-ROOT': ('LEARNED', 'ROOT'), 'LEARNED-H2': ('LEARNED', 'H2'),
    'GLOBAL-H2': ('GLOBAL', 'H2'), 'A-H2': ('A', 'H2'), 'B-H2': ('B', 'H2'),
    'TEST_ROOT_MEAN_ORACLE-H2': ('TEST_ROOT_MEAN_ORACLE', 'H2'),
    'TEST_ROOT_MEAN_ORACLE-LEARNED': ('TEST_ROOT_MEAN_ORACLE', 'LEARNED'),
    'TEST_ROOT_MEAN_ORACLE-ROOT': ('TEST_ROOT_MEAN_ORACLE', 'ROOT')}
SEMANTIC_FIELDS = ('first_action', 'probe_action', 'true_suffix', 'false_suffix')
OUTCOME_FIELDS = ('score', 'steps', 'status', 'components', 'utility')
NONE_PATH_FIELDS = ('actual_word', 'actual_probe', 'prefix_steps', 'attempts', 'exit_reason', 'exit_step')
MAPPING_CODES = ('AA', 'AB', 'BA', 'BB')


def semantic_key(candidate):
    """A/B mean the original true/false alternatives, independent of local IDs."""
    return (candidate['first_action'], candidate['probe_action'],
            tuple(candidate['true_suffix']), tuple(candidate['false_suffix']))


def _coordinate(row):
    return row['heldout_life'], row['root_id'], row['suffix'], row['mode']


def _issue(issues, name):
    if name not in issues:
        issues.append(name)


def build_roster(candidates, programs, roots, screening_branch_roster):
    """Freeze the first semantic donor using metadata, never terminal labels."""
    candidate_cells = {(c['heldout_life'], c['query']): c for c in candidates}
    program_cells = {(c['heldout_life'], c['query']): c for c in programs}
    branch_index, duplicate_branches = {}, set()
    for branch in screening_branch_roster:
        key = _coordinate(branch)
        if key in branch_index:
            duplicate_branches.add(key)
        branch_index[key] = branch
    work = Counter(metadata_branches_indexed=len(screening_branch_roster),
                   metadata_roots_examined=len(roots), semantic_candidates_examined=0,
                   metadata_branch_lookups=0)
    cells = []
    for life in LIVES:
        for query in QUERIES:
            issues, source, selected_id, donor = [], None, None, None
            frozen = program_cells.get((life, query))
            selected = None if frozen is None else frozen.get('programs', {}).get('LEARNED')
            global_program = None if frozen is None else frozen.get('programs', {}).get('GLOBAL')
            if selected is None:
                issues.append('selected_program_missing')
            else:
                selected_id = selected['candidate_id']
                source = next((c for c in candidate_cells.get((life, query), {}).get('candidates', [])
                               if c['candidate_id'] == selected_id), None)
            if source is None or not all(field in source for field in SEMANTIC_FIELDS):
                _issue(issues, 'selected_source_semantics_missing')
                source = None
            if selected is not None and (selected.get('mapping') is None or
                    any(selected['mapping'].get(p) not in ('A', 'B') for p in ('true', 'false'))):
                _issue(issues, 'learned_mapping_missing')
            if (global_program is None or global_program.get('candidate_id') != selected_id or
                    global_program.get('mapping') not in (dict(true='A', false='A'), dict(true='B', false='B'))):
                _issue(issues, 'global_mapping_not_constant_same_candidate')
            if source is not None:
                for fold in LIVES:
                    if fold == life:
                        continue
                    for position, candidate in enumerate(candidate_cells.get((fold, query), {}).get('candidates', [])):
                        work['semantic_candidates_examined'] += 1
                        if all(field in candidate for field in SEMANTIC_FIELDS) and semantic_key(candidate) == semantic_key(source):
                            donor = dict(heldout_life=fold, candidate_id=candidate['candidate_id'],
                                         candidate_position=position)
                            break
                    if donor is not None:
                        break
                if donor is None:
                    _issue(issues, 'semantic_donor_missing')
            pool = [root for root in roots if (root['life'], root['query']) == (life, query)]
            if len(pool) != ROOTS_PER_HISTORY or len({root['root_id'] for root in pool}) != ROOTS_PER_HISTORY:
                _issue(issues, 'own_history_root_roster')
            root_rows = []
            for root in pool:
                item = {key: deepcopy(value) for key, value in root.items() if key != 'board'}
                item.update(branches=[], issues=list(issues))
                if donor is not None:
                    for suffix in SUFFIXES:
                        triple = []
                        for mode in ('H2', donor['candidate_id']+'_A', donor['candidate_id']+'_B'):
                            key = donor['heldout_life'], root['root_id'], suffix, mode
                            work['metadata_branch_lookups'] += 1
                            branch = branch_index.get(key)
                            if branch is None:
                                _issue(item['issues'], 'missing_branch_metadata')
                            elif key in duplicate_branches:
                                _issue(item['issues'], 'duplicate_branch_metadata')
                            if branch is not None:
                                triple.append(branch)
                                item['branches'].append(deepcopy(branch))
                        if len(triple) == 3 and len({branch['seed'] for branch in triple}) != 1:
                            _issue(item['issues'], 'paired_seed_metadata_mismatch')
                item['complete'] = not item['issues']
                root_rows.append(item)
            cells.append(dict(target_life=life, query=query, selected_candidate_id=selected_id,
                source_semantics=None if source is None else {key: deepcopy(source[key]) for key in SEMANTIC_FIELDS},
                learned_mapping=None if selected is None else deepcopy(selected.get('mapping')),
                global_mapping=None if global_program is None else deepcopy(global_program.get('mapping')),
                donor=donor, roots=root_rows, issues=issues,
                complete=not issues and all(root['complete'] for root in root_rows)))
    return dict(schema='acfqp.program_headroom.v165.roster', expected_cell_count=8,
        expected_root_count=32, root_count=sum(len(cell['roots']) for cell in cells),
        cells=cells, complete=all(cell['complete'] for cell in cells), logical_work=dict(work))


def _mean(values):
    values = tuple(values)
    return sum(values)/len(values)


def _moments(values):
    values = tuple(values)
    complete = bool(values) and all(value is not None for value in values)
    average = _mean(values) if complete else None
    variance = sum((value-average)**2 for value in values)/(len(values)-1) if complete and len(values)>1 else 0. if complete else None
    return dict(n=len(values), complete=complete, mean=average, sample_variance=variance,
                mean_variance=variance/len(values) if complete else None)


def _pool(stats, expected):
    complete = len(stats) == expected and all(stat['complete'] for stat in stats)
    average = _mean(stat['mean'] for stat in stats) if complete else None
    variance = sum(stat['mean_variance'] for stat in stats)/expected**2 if complete else None
    se = sqrt(variance) if complete else None
    return dict(complete=complete, mean=average, mean_variance=variance,
                conditional_suffix_se=se,
                conditional_suffix_ci95=None if se is None else [average-1.96*se, average+1.96*se])


def _select(a, b, mapping):
    predicate = a['module']['predicate']
    return a if predicate is None or mapping['true' if predicate else 'false'] == 'A' else b


def _values(row, query):
    return dict(zip(METRICS, (utility(row['components'], query), *row['components'])))


def _choice(triples, suffixes, query, work):
    values = {}
    for arm in ('A', 'B'):
        vectors = [triples[suffix][arm]['components'] for suffix in suffixes]
        vector = [_mean(row[k] for row in vectors) for k in range(3)]
        values[arm] = dict(components=vector, utility=utility(vector, query))
        work['arm_mean_vectors'] += 1
    return ('A' if values['A']['utility'] >= values['B']['utility'] else 'B'), values


def _validated_roots(roster, flat_outcome_rows, work):
    index, duplicate_rows = {}, set()
    for row in flat_outcome_rows:
        key = _coordinate(row)
        if key in index:
            duplicate_rows.add(key)
        index[key] = row
    result = []
    for cell in roster['cells']:
        for root in cell['roots']:
            issues, triples = list(root['issues']), {}
            plans = {(row['suffix'], row['mode']): row for row in root['branches']}
            if cell['donor'] is not None:
                donor = cell['donor']
                for suffix in SUFFIXES:
                    work['outcome_triples_examined'] += 1
                    rows = {}
                    for arm, mode in (('H2', 'H2'), ('A', donor['candidate_id']+'_A'), ('B', donor['candidate_id']+'_B')):
                        key = donor['heldout_life'], root['root_id'], suffix, mode
                        row, plan = index.get(key), plans.get((suffix, mode))
                        if row is None:
                            _issue(issues, 'missing_outcome')
                        elif key in duplicate_rows:
                            _issue(issues, 'duplicate_outcome')
                        if row is not None:
                            rows[arm] = row
                            if plan is None or row['seed'] != plan['seed']:
                                _issue(issues, 'outcome_seed_mismatch')
                            if row['status'] not in ('WON', 'LOST') or row['utility'] is None:
                                _issue(issues, 'nonterminal_outcome')
                            elif row['utility'] != utility(row['components'], root['query']):
                                _issue(issues, 'recorded_utility_mismatch')
                    if len(rows) != 3:
                        continue
                    a, b = rows['A'], rows['B']
                    predicate = a['module']['predicate']
                    if predicate != b['module']['predicate']:
                        _issue(issues, 'predicate_mismatch')
                    if predicate is None and any(a[key] != b[key] for key in OUTCOME_FIELDS):
                        _issue(issues, 'none_outcome_mismatch')
                    if predicate is None and any(a['module'][key] != b['module'][key] for key in NONE_PATH_FIELDS):
                        _issue(issues, 'none_path_mismatch')
                    triples[suffix] = rows
            result.append(dict(cell=cell, root=root, triples=triples, issues=issues,
                               complete=not issues and len(triples) == 4))
    return result


def _refit_cells(roster, validated, train, work):
    """Fit a shared bit map on the same four-root selection half as ROOT."""
    result = []
    for cell in roster['cells']:
        pool = [item for item in validated if item['cell'] is cell]
        complete = cell['complete'] and len(pool) == 4 and all(item['complete'] for item in pool)
        evidence, scores, allowed = {}, [], []
        if complete:
            for name, predicate in (('true', True), ('false', False)):
                support, root_vectors = 0, []
                for item in pool:
                    vectors = []
                    for suffix in train:
                        a, b = item['triples'][suffix]['A'], item['triples'][suffix]['B']
                        if a['module']['predicate'] is predicate:
                            support += 1
                            vectors.append([x-y for x, y in zip(a['components'], b['components'], strict=True)])
                        else:
                            vectors.append([0., 0., 0.])
                    root_vectors.append([_mean(vector[k] for vector in vectors) for k in range(3)])
                vector = [_mean(row[k] for row in root_vectors) for k in range(3)] if support else None
                prior = cell['learned_mapping'][name]
                evidence[name] = dict(support=support, prior_assignment=prior,
                    component_delta_A_minus_B=vector,
                    utility_delta_A_minus_B=None if vector is None else utility(vector, cell['query']),
                    provenance='terminal_estimated' if support else 'frozen_learned_prior',
                    allowed_assignments=['A', 'B'] if support else [prior])
            allowed = [code for code in MAPPING_CODES if code[0] in evidence['true']['allowed_assignments']
                       and code[1] in evidence['false']['allowed_assignments']]
            for code in MAPPING_CODES:
                mapping = dict(true=code[0], false=code[1])
                root_vectors, root_deltas = [], []
                for item in pool:
                    vectors, deltas = [], []
                    for suffix in train:
                        triple = item['triples'][suffix]
                        selected = _select(triple['A'], triple['B'], mapping)
                        vectors.append(selected['components'])
                        deltas.append([x-y for x, y in zip(selected['components'], triple['H2']['components'], strict=True)])
                        work['refit_mapping_vector_selections'] += 1
                    root_vectors.append([_mean(vector[k] for vector in vectors) for k in range(3)])
                    root_deltas.append([_mean(vector[k] for vector in deltas) for k in range(3)])
                vector = [_mean(row[k] for row in root_vectors) for k in range(3)]
                delta = [_mean(row[k] for row in root_deltas) for k in range(3)]
                scores.append(dict(mapping_code=code, mapping=mapping, component_mean=vector,
                    selection_utility=utility(vector, cell['query']), component_delta_vs_H2=delta,
                    selection_gain_vs_H2=utility(delta, cell['query'])))
            bit = min((row for row in scores if row['mapping_code'] in allowed),
                      key=lambda row: (-row['selection_utility'], MAPPING_CODES.index(row['mapping_code'])))
            global_fit = min((row for row in scores if row['mapping_code'] in ('AA', 'BB')),
                             key=lambda row: (-row['selection_utility'], MAPPING_CODES.index(row['mapping_code'])))
        else:
            bit, global_fit = None, None
        result.append(dict(target_life=cell['target_life'], heldout_life=cell['target_life'], query=cell['query'],
            complete=complete, selection_suffixes=list(train), roots=len(pool), leaf_evidence=evidence,
            allowed_mapping_codes=allowed, mapping_scores=scores,
            bit_refit_mapping=None if bit is None else bit['mapping'],
            bit_refit_mapping_code=None if bit is None else bit['mapping_code'],
            global_refit_mapping=None if global_fit is None else global_fit['mapping'],
            global_refit_mapping_code=None if global_fit is None else global_fit['mapping_code']))
        work['refit_cell_fits'] += int(complete)
    return result


def _summaries(root_rows, kind, names):
    result = []
    for query in QUERIES:
        pool = [row for row in root_rows if row['query'] == query]
        for name in names:
            histories = []
            for life in LIVES:
                selected = [row for row in pool if row['life'] == life]
                metrics = {key: _pool([row[kind][name][key] for row in selected], ROOTS_PER_HISTORY)
                           for key in METRICS}
                histories.append(dict(life=life, roots=len(selected), metrics=metrics))
            metrics = {key: _pool([history['metrics'][key] for history in histories], 4) for key in METRICS}
            point_only = 'TEST_ROOT_MEAN_ORACLE' in name
            if point_only:
                for summary in [metrics]+[history['metrics'] for history in histories]:
                    for stats in summary.values():
                        stats.update(mean_variance=None, conditional_suffix_se=None, conditional_suffix_ci95=None)
            result.append(dict(query=query, **{('contrast' if kind == 'contrasts' else 'mode'): name},
                roots=len(pool), complete=all(metric['complete'] for metric in metrics.values()),
                point_only=point_only, metrics=metrics, per_history=histories))
    return result


def _evaluate_split(roster, validated, train, test, work):
    refits = _refit_cells(roster, validated, train, work)
    refit_index = {(cell['target_life'], cell['query']): cell for cell in refits}
    root_rows = []
    for item in validated:
        cell, root, triples = item['cell'], item['root'], item['triples']
        refit = refit_index[root['life'], root['query']]
        complete = item['complete'] and refit['complete']
        issues = list(item['issues'])
        if not refit['complete']:
            _issue(issues, 'refit_cell_incomplete')
        selected_arm, train_means, oracle_arm, test_means = None, {}, None, {}
        trials = []
        if complete:
            selected_arm, train_means = _choice(triples, train, root['query'], work)
            oracle_arm, test_means = _choice(triples, test, root['query'], work)
            work['root_choice_fits'] += 1
            work['test_mean_oracle_choices'] += 1
            for suffix in test:
                triple = triples[suffix]
                selected = dict(H2=triple['H2'], A=triple['A'], B=triple['B'],
                    LEARNED=_select(triple['A'], triple['B'], cell['learned_mapping']),
                    GLOBAL=_select(triple['A'], triple['B'], cell['global_mapping']),
                    BIT_REFIT=_select(triple['A'], triple['B'], refit['bit_refit_mapping']),
                    GLOBAL_REFIT=_select(triple['A'], triple['B'], refit['global_refit_mapping']),
                    ROOT=triple[selected_arm], TEST_ROOT_MEAN_ORACLE=triple[oracle_arm])
                values = {mode: _values(row, root['query']) for mode, row in selected.items()}
                work['logical_vector_selections'] += len(selected)
                trials.append(dict(suffix=suffix, seed=triple['H2']['seed'], predicate=triple['A']['module']['predicate'],
                    modes={mode: dict(branch_id=row['branch_id'], components=deepcopy(row['components']),
                        raw_utility=row['utility'], **values[mode]) for mode, row in selected.items()},
                    contrasts={name: {key: values[left][key]-values[right][key] for key in METRICS}
                               for name, (left, right) in CONTRASTS.items()}))
        modes = {mode: {key: _moments(trial['modes'][mode][key] for trial in trials)
                       if complete else _moments([None]*len(test)) for key in METRICS} for mode in MODES}
        contrasts = {name: {key: _moments(trial['contrasts'][name][key] for trial in trials)
                           if complete else _moments([None]*len(test)) for key in METRICS} for name in CONTRASTS}
        root_rows.append(dict(root_id=root['root_id'], life=root['life'], query=root['query'],
            complete=complete, issues=issues, donor=deepcopy(cell['donor']),
            selected_arm=selected_arm, train_arm_means=train_means, test_arm_means=test_means,
            test_mean_oracle_arm=oracle_arm, test_trials=trials, modes=modes, contrasts=contrasts))
    choices = []
    for query in QUERIES:
        histories = []
        for life in LIVES:
            selected = [row for row in root_rows if (row['life'], row['query']) == (life, query)]
            histories.append(dict(life=life, roots=len(selected),
                counts={arm: sum(row['selected_arm'] == arm for row in selected) for arm in ('A', 'B')},
                unknown=sum(row['selected_arm'] is None for row in selected)))
        choices.append(dict(query=query, per_history=histories,
            counts={arm: sum(history['counts'][arm] for history in histories) for arm in ('A', 'B')},
            unknown=sum(history['unknown'] for history in histories)))
    comparisons = _summaries(root_rows, 'contrasts', CONTRASTS)
    modes = _summaries(root_rows, 'modes', MODES)
    return dict(selection_suffixes=list(train), scoring_suffixes=list(test),
        train_suffixes=list(train), test_suffixes=list(test), cells=refits, root_rows=root_rows,
        comparisons=comparisons, modes=modes, root_choices=choices,
        complete=all(row['complete'] for row in comparisons))


def evaluate(roster, flat_outcome_rows):
    """Fit fixed A/B on TRAIN, then score whole paired TEST outcome vectors."""
    work = Counter(outcome_rows_supplied=len(flat_outcome_rows), outcome_triples_examined=0,
        arm_mean_vectors=0, root_choice_fits=0, test_mean_oracle_choices=0, logical_vector_selections=0,
        refit_mapping_vector_selections=0, refit_cell_fits=0)
    validated = _validated_roots(roster, flat_outcome_rows, work)
    splits = {name: _evaluate_split(roster, validated, train, test, work) for name, (train, test) in SPLITS.items()}
    return dict(schema='acfqp.program_headroom.v165.evaluation', roster=deepcopy(roster),
        complete=roster['complete'] and all(split['complete'] for split in splits.values()), splits=splits,
        root_count=len(validated), complete_root_count=sum(row['complete'] for row in validated),
        logical_work=dict(work), new_environment_samples=0, new_model_samples=0,
        native_planner_calls=0, real_training_updates=0,
        uncertainty='Normal paired-suffix intervals conditional on 32 fixed own-history TRAIN roots and fitted per-root choices; two TEST suffixes/root, equal four roots/history and four histories.',
        oracle_scope='TEST root-mean max(A,B) is an optimistic finite-sample diagnostic; it is not an adoption rule.')
