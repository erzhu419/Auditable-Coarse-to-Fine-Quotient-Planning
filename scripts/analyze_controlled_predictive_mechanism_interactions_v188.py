"""Independent six-mechanism interactions and matched SOURCE selections."""
import argparse
from collections import Counter
from copy import deepcopy
from itertools import combinations
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter
import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(PROJECT/'src'))
from scripts import analyze_controlled_predictive_position_shared_v187 as previous

coverage, layout, shared, exact, ridge = previous.coverage, previous.layout, previous.shared, previous.exact, previous.ridge
ACTIONS, EPS, LAMBDAS, same = previous.ACTIONS, previous.EPS, previous.LAMBDAS, previous.same
SCHEMA = 'acfqp.mechanism_interactions.v188'
MODES = ('LINEAR', 'INTERACT')
MODEL_NAMES = ('INTERACT', 'LINEAR', 'RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE')
BOUNDS = (1, 16, 12, 12, 12, 12)
PRODUCT_PAIRS = [(i, j) for i in range(6) for j in range(i, 6) if (i, j) != (0, 0)]
OUTPUT = PROJECT/'reports/controlled_predictive_mechanism_interactions_v188'


def interaction_vector(aggregate):
    values = list(map(float, aggregate))
    return values+[values[i]*values[j]/math.sqrt(BOUNDS[i]*BOUNDS[j]) for i, j in PRODUCT_PAIRS]


def basis(mode):
    names = list(shared.FEATURE_NAMES)
    products = [dict(column=6+k, left=i, right=j, normalizer=math.sqrt(BOUNDS[i]*BOUNDS[j]), name=f'{names[i]}*{names[j]}')
                for k, (i, j) in enumerate(PRODUCT_PAIRS)] if mode == 'INTERACT' else []
    return dict(aggregate_names=names, aggregate_bounds=list(BOUNDS), aggregate_scaling='UNCHANGED', products=products, columns=6+len(products), intercept=False)


def action_features_from_root(root, counts=None, mode='INTERACT'):
    columns = basis(mode)['columns']; work = Counter()
    if 'interaction_features' in root:
        features = {action: list(vector[:columns]) for action, vector in root['interaction_features'].items()}
        work.update(mechanism_feature_cache_hits=1, mechanism_cached_feature_reads=columns*len(features))
    else:
        if 'action_features' in root:
            aggregates = root['action_features']; work['mechanism_aggregate_cache_hits'] += 1
        else:
            aggregates = {action: row['aggregate'] for action, row in root['layout_features'].items()}; work['mechanism_layout_aggregate_cache_hits'] += 1
        features = {}
        for action, values in aggregates.items():
            features[action] = interaction_vector(values) if mode == 'INTERACT' else list(map(float, values))
            work.update(mechanism_base_feature_reads=6, mechanism_aggregate_values_copied=6)
            if mode == 'INTERACT':
                work.update(mechanism_product_feature_multiplications=20, mechanism_product_normalizer_reads=20, mechanism_product_normalizations=20)
        work['mechanism_feature_maps_derived'] += 1
    if counts is not None:
        counts.update(work)
    return features


def prepare_design(examples, mode='INTERACT', life=0):
    metadata = basis(mode); columns = metadata['columns']; counts, feature_counts = Counter(), Counter(); roots, features = [], {}
    for original in examples:
        counts['examples_examined'] += 1
        if original['life'] != life:
            counts['other_life_examples_excluded'] += 1; continue
        root = deepcopy(original); legal = [action for action in ACTIONS if action in root['legal_actions']]
        root['legal_actions'] = legal
        root['immediate_rewards'] = {action: float(root['immediate_rewards'][action]) for action in legal}
        root['action_components'] = {action: list(map(float, root['action_components'][action])) for action in legal}
        features[root['root_id']] = action_features_from_root(root, feature_counts, mode); roots.append(root)
        counts.update(examples_fitted=1, legal_action_reads=len(legal), immediate_reward_reads=len(legal), exact_action_vector_reads=len(legal),
                      label_component_reads=3*len(legal), tail_reward_subtractions=len(legal))
    roots.sort(key=lambda row: row['root_id']); action_roots = {action: set() for action in ACTIONS}
    pair_roots = {f'{a}|{b}': set() for a, b in combinations(ACTIONS, 2)}; labels, records = [], []
    for root in roots:
        legal = root['legal_actions']
        for action in legal:
            action_roots[action].add(root['root_id'])
        pairs = []
        for ia, ib, weight, target in exact.exact_pair_samples(root):
            first, second = ACTIONS[ia], ACTIONS[ib]
            values = [features[root['root_id']][first][k]-features[root['root_id']][second][k] for k in range(columns)]
            sparse = [[column, value] for column, value in enumerate(values) if value != 0.]
            pair = dict(actions=[first, second], weight=weight, design=sparse, components=target); pairs.append(deepcopy(pair))
            records.append(dict(root_id=root['root_id'], source_id=root['source_id'], **pair)); pair_roots[f'{first}|{second}'].add(root['root_id'])
            counts.update(paired_vector_labels=1, paired_component_subtractions=3, mechanism_pair_rows=1, mechanism_design_value_reads=2*columns,
                          mechanism_design_subtractions=columns, mechanism_nonzero_design_entries=len(sparse))
        labels.append(dict(root_id=root['root_id'], source_id=root['source_id'], legal_actions=legal, label_kind='exact_enumerated_vector', pairs=pairs))
    matrix, targets = np.zeros((len(records), columns)), np.zeros((len(records), 3))
    for index, record in enumerate(records):
        scale = math.sqrt(record['weight'])
        for column, value in record['design']:
            matrix[index, column] = scale*value
        targets[index] = [scale*value for value in record['components']]
        counts.update(mechanism_weight_square_roots=1, mechanism_weighted_design_scalings=len(record['design']), mechanism_weighted_target_scalings=3)
    counts.update(mechanism_design_matrix_cells=matrix.size, mechanism_target_matrix_cells=targets.size, ridge_design_preparations=1)
    sources = dict(Counter(root['source_id'] for root in roots)); pair_ids = {pair: sorted(ids) for pair, ids in pair_roots.items()}
    return dict(schema=SCHEMA+'.design', mode=mode, life=life, basis=metadata, feature_names=metadata['aggregate_names']+[row['name'] for row in metadata['products']],
        roots=roots, root_ids=[root['root_id'] for root in roots], source_ids=sorted(sources), source_root_counts=sources,
        action_root_ids={action: sorted(ids) for action, ids in action_roots.items()}, pair_root_ids=pair_ids, connected_components=shared.connected_components(pair_ids),
        fit_labels=labels, pair_records=records, design_format='sparse_columns', shape=list(matrix.shape), X=matrix, Y=targets,
        prepare_counts=dict(counts), feature_counts=dict(feature_counts), work=dict(counts+feature_counts))


def model_from_fit(design, decomposition, fitted, lambda_value, source_folds):
    counts = Counter(design['prepare_counts'])+Counter(decomposition['work'])+Counter(fitted['counts'])
    return dict(schema=SCHEMA+'.model', mode=design['mode'], life=design['life'], query='risk1', native_teacher_query='goal_1_risk_1', horizon=3,
        label_kind='exact_enumerated_vector', feature_names=list(design['feature_names']), basis=deepcopy(design['basis']), design_format='sparse_columns',
        coefficients=fitted['coefficients'], rank=decomposition['rank'], singular_values=decomposition['singular_values'], component_losses=fitted['component_losses'],
        loss=fitted['loss'], root_mean_loss=fitted['root_mean_loss'], penalty=fitted['penalty'], objective=fitted['objective'],
        constants=dict(min_action_roots=4, epsilon=EPS, goal_rank=11, columns=design['basis']['columns'], intercept=False, lambda_value=lambda_value, penalty_normalization='ROOT_MEAN', rcond=None),
        root_ids=list(design['root_ids']), source_ids=list(design['source_ids']), source_folds=deepcopy(source_folds), source_root_counts=deepcopy(design['source_root_counts']),
        action_root_ids=deepcopy(design['action_root_ids']), pair_root_ids=deepcopy(design['pair_root_ids']), connected_components=deepcopy(design['connected_components']),
        fit_labels=deepcopy(design['fit_labels']), fit_residuals=fitted['residuals'], training_outcomes=deepcopy(design['roots']), fit_counts=dict(counts), feature_counts=dict(design['feature_counts']))


def choose_action(payload, root, counts=None):
    legal = [action for action in ACTIONS if action in root['legal_actions']]; columns = basis(payload['mode'])['columns']
    feature_work = Counter(); features = action_features_from_root(root, feature_work, payload['mode'])
    work = Counter(mechanism_decisions=1, mechanism_legal_action_reads=len(legal))
    action_counts = {action: len(payload['action_root_ids'][action]) for action in legal}
    pair_counts = {f'{a}|{b}': len(payload['pair_root_ids'][f'{a}|{b}']) for a, b in combinations(legal, 2)}
    connected = payload['connected_components']; component = {action: index for index, group in enumerate(connected) for action in group}
    work.update(mechanism_action_support_lookups=len(legal), mechanism_pair_support_lookups=len(pair_counts), mechanism_component_membership_lookups=len(legal))
    if len(legal) == 1:
        selected, fallback, reason = legal[0], False, 'single_legal_action'
    elif any(value < 4 for value in action_counts.values()):
        selected, fallback, reason = root['fallback_action'], True, 'insufficient_action_support'
    elif len({component[action] for action in legal}) != 1:
        selected, fallback, reason = root['fallback_action'], True, 'disconnected_required_actions'
    else:
        selected, fallback, reason = None, False, 'selected'
    predicted = {}
    for action in legal:
        vector = [sum(features[action][i]*payload['coefficients'][i][k] for i in range(columns)) for k in range(3)]
        vector[0] += root['immediate_rewards'][action]; predicted[action] = vector
        work.update(mechanism_prediction_feature_reads=3*columns, mechanism_prediction_coefficient_reads=3*columns,
                    mechanism_prediction_component_evaluations=3, mechanism_immediate_reward_reads=1, mechanism_reward_additions=1)
    pairs = {f'{a}|{b}': [predicted[a][k]-predicted[b][k] for k in range(3)] for a, b in combinations(legal, 2) if component[a] == component[b]}
    if pairs:
        work['mechanism_predicted_pair_subtractions'] += 3*len(pairs)
    if selected is None:
        best = None
        for action in legal:
            value = exact.utility(predicted[action]); work['mechanism_utility_evaluations'] += 1
            if best is None or value > best+EPS:
                selected, best = action, value
    result = dict(canonical_action=selected, actual_action=root['action_map'][selected], fallback=fallback, leaf=0, reason=reason,
        predicted_components=predicted, predicted_pairs=pairs,
        support=dict(action_root_counts=action_counts, pair_root_counts=pair_counts, connected_components=deepcopy(connected), required_actions=legal, complete=not fallback),
        work=dict(work), feature_work=dict(feature_work))
    if counts is not None:
        counts.update(work); counts.update(feature_work)
    return result


def observable(root):
    result = {key: root[key] for key in ('root_id', 'source_id', 'life', 'canonical_board', 'legal_actions', 'immediate_rewards', 'fallback_action', 'action_map')}
    for key in ('layout_features', 'action_features', 'interaction_features'):
        if key in root:
            result[key] = root[key]
    return result


def score_heldout(model, roots):
    counts, groups, choices = Counter(), {}, []
    for root in sorted(roots, key=lambda row: row['root_id']):
        decision = choose_action(model, observable(root), counts); vector = list(map(float, root['action_components'][decision['canonical_action']]))
        groups.setdefault(root['source_id'], []).append(vector)
        choices.append(dict(root_id=root['root_id'], source_id=root['source_id'], decision=decision, components=vector, utility=exact.utility(vector)))
        counts.update(heldout_action_vector_reads=1, heldout_component_reads=3, heldout_utility_evaluations=1)
    records = []
    for source, vectors in sorted(groups.items()):
        mean = [sum(vector[k] for vector in vectors)/len(vectors) for k in range(3)]
        records.append(dict(source_id=source, roots=len(vectors), components=mean, utility=exact.utility(mean)))
        counts.update(heldout_group_component_means=3, heldout_group_utility_evaluations=1)
    return records, choices, dict(counts)


def select_regularization(examples, mode, life, audit_work, saved_selection=None, saved_model=None):
    sources = sorted({row['source_id'] for row in examples if row['life'] == life})
    if len(sources) != 36:
        raise ValueError('Thirty-six fixed SOURCE groups required')
    source_folds = [sources[::2], sources[1::2]]; costs = Counter(source_fold_assignments=36, regularization_candidates=6)
    designs, heldouts, saved_folds, metadata = [], [], [], []
    for fold, heldout in enumerate(source_folds):
        train_sources = [source for source in sources if source not in heldout]
        design = prepare_design([row for row in examples if row['life'] == life and row['source_id'] in train_sources], mode, life)
        designs.append(design); costs.update(design['work']); heldouts.append([row for row in examples if row['life'] == life and row['source_id'] in heldout])
        saved_folds.append(dict(fold=fold, train_sources=train_sources, heldout_sources=list(heldout), design={key: value for key, value in design.items() if key not in ('X', 'Y')}))
    candidates, selected, best = [], LAMBDAS[0], None
    for candidate_index, lambda_value in enumerate(LAMBDAS):
        fold_results, groups = [], []
        for fold in range(2):
            saved = None if saved_selection is None else saved_selection['candidates'][candidate_index]['fold_results'][fold]['coefficients']
            fitted, rank, singular = previous.fit_design(designs[fold], lambda_value, audit_work, saved); costs.update(fitted['counts'])
            if lambda_value == 0:
                meta = ridge.decomposition_metadata(designs[fold], rank, singular); metadata.append(meta); costs.update(meta['work']); saved_folds[fold]['decomposition'] = meta
            model = model_from_fit(designs[fold], metadata[fold], fitted, lambda_value, source_folds)
            records, choices, prediction_counts = score_heldout(model, heldouts[fold]); costs.update(prediction_counts); groups.extend(records)
            fold_results.append(dict(fold=fold, coefficients=fitted['coefficients'], component_losses=fitted['component_losses'], loss=fitted['loss'],
                root_mean_loss=fitted['root_mean_loss'], penalty=fitted['penalty'], objective=fitted['objective'], group_records=records,
                choices=choices, prediction_counts=prediction_counts, coefficient_counts=fitted['counts']))
        groups.sort(key=lambda row: row['source_id']); utility = sum(row['utility'] for row in groups)/len(sources)
        costs.update(regularization_group_mean_reads=36, regularization_score_comparisons=1)
        candidates.append(dict(lambda_value=lambda_value, utility=utility, group_records=groups, fold_results=fold_results))
        if best is None or utility > best+EPS:
            selected, best = lambda_value, utility
    full = prepare_design(examples, mode, life); costs.update(full['work'])
    saved = None if saved_model is None else saved_model['coefficients']
    fitted, rank, singular = previous.fit_design(full, selected, audit_work, saved); costs.update(fitted['counts'])
    if selected > 0:
        singular = np.linalg.svd(full['X'], compute_uv=False); cutoff = np.finfo(float).eps*max(full['X'].shape)*(singular[0] if len(singular) else 0.)
        rank = int(sum(singular > cutoff)); audit_work.update(final_singular_values_only_decompositions=1, final_singular_values_matrix_cells=full['X'].size)
    meta = ridge.decomposition_metadata(full, rank, singular); costs.update(meta['work']); costs['new_predictors_fitted'] = costs['ridge_predictors_fitted']
    selection = dict(schema=SCHEMA+'.selection', mode=mode, life=life, basis=basis(mode), lambdas=list(LAMBDAS), source_folds=source_folds,
        folds=saved_folds, candidates=candidates, selected_lambda=selected, selected_utility=best, costs=dict(costs))
    return selection, model_from_fit(full, meta, fitted, selected, source_folds)


def fit_models(examples, life=0, saved_selections=None, saved_models=None):
    cached, cache_counts = [], Counter()
    for original in examples:
        if original['life'] != life:
            continue
        root = deepcopy(original); root['interaction_features'] = action_features_from_root(root, cache_counts); cached.append(root)
    models, selections, costs, audit_work = {}, {}, Counter(cache_counts), Counter()
    for mode in MODES:
        saved_selection = None if saved_selections is None else saved_selections[mode]
        saved_model = None if saved_models is None else saved_models[mode]
        selections[mode], models[mode] = select_regularization(cached, mode, life, audit_work, saved_selection, saved_model)
        costs.update(selections[mode]['costs'])
    return dict(models=models, selections=selections, costs=dict(costs), cache_counts=dict(cache_counts)), dict(audit_work)


def cache_roots(roots):
    work = Counter(coverage.cache_roots(roots))
    for root in roots:
        root['interaction_features'] = action_features_from_root(root, work)
    return dict(work)


def freeze_choices(roots, models):
    choices, work = {name: [] for name in (*MODEL_NAMES, 'FALLBACK')}, Counter()
    for root in roots:
        observed = observable(root)
        for name in MODEL_NAMES:
            chooser = choose_action if name in MODES else shared.choose_action if name in ('SHARED', 'OLD_SHARED') else exact.choose_action if name == 'ONE' else layout.choose_action
            decision = chooser(models[name], observed); work.update(decision['work']); work.update(decision.get('feature_work', {})); work['mechanism_frozen_model_choices'] += 1
            choices[name].append(dict(root_id=root['root_id'], mode=name, canonical_action=decision['canonical_action'], actual_action=decision['actual_action'], fallback=decision['fallback'], decision=decision))
        action = root['fallback_action']; work['mechanism_frozen_fallback_choices'] += 1
        choices['FALLBACK'].append(dict(root_id=root['root_id'], mode='FALLBACK', canonical_action=action, actual_action=root['action_map'][action], fallback=False,
            decision=dict(reason='observable_immediate_reward', work=dict(mechanism_frozen_fallback_choices=1))))
    return choices, dict(work)


def cohort_cases():
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]+[(4*r+c, 4*r+c+4) for r in range(3) for c in range(4)]
    cases = []
    for replica in range(4):
        for index, (first, second) in enumerate(edges):
            seed = 1880200+24*replica+index; rng = random.Random(seed); board = [rng.randint(1, 10) for _ in range(16)]
            board[first] = board[second] = 1+index % 10
            for cell in rng.sample([cell for cell in range(16) if cell not in (first, second)], index % 3):
                board[cell] = 0
            cases.append(dict(split='TARGET', replica=replica, stratum=index, name=f'v188_target_r{replica:02d}_{index:02d}', horizon=3, seed=seed, board=board, vacancies=index % 3))
    return cases


def summarize(roots, labels, choices, selection, models):
    indexed_labels = {row['root_id']: row for row in labels}; indexed_choices = {name: {row['root_id']: row for row in rows} for name, rows in choices.items()}
    modes = (*MODEL_NAMES, 'FALLBACK', 'ORACLE'); controls = ('LINEAR', 'RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE'); records = []
    for root in roots['TARGET']:
        vectors = indexed_labels[root['root_id']]['action_components']; oracle = root['legal_actions'][0]
        for action in root['legal_actions'][1:]:
            if exact.utility(vectors[action]) > exact.utility(vectors[oracle])+EPS:
                oracle = action
        outcomes = {}
        for name in modes:
            decision = None if name == 'ORACLE' else indexed_choices[name][root['root_id']]
            action = oracle if decision is None else decision['canonical_action']; vector = vectors[action]
            outcomes[name] = dict(action=action, components=vector, utility=exact.utility(vector), regret=exact.utility(vectors[oracle])-exact.utility(vector),
                                  fallback=False if decision is None else decision['fallback'])
        records.append(dict(root_id=root['root_id'], replica=root['replica'], stratum=root['stratum'], models=outcomes))

    def means(rows):
        result = {}
        for name in modes:
            mean = exact.mean_vectors([row['models'][name]['components'] for row in rows])
            result[name] = dict(components=mean, utility=exact.utility(mean), positive_regret_roots=sum(row['models'][name]['regret'] > EPS for row in rows),
                                fallback_roots=sum(row['models'][name]['fallback'] for row in rows))
        return result

    def contrasts(rows):
        first = [dict(root_id=row['root_id'], models={'INTERACT': row['models']['INTERACT']}) for row in rows]
        return {'INTERACT_MINUS_'+name: coverage.coverage_effect(first,
            [dict(root_id=row['root_id'], models={'INTERACT': row['models'][name]}) for row in rows], 'INTERACT') for name in controls}

    metrics, effects = means(records), contrasts(records)
    replicas = [dict(replica=replica, roots=len(rows), models=means(rows), comparisons=contrasts(rows))
        for replica in sorted({row['replica'] for row in records}) for rows in [[row for row in records if row['replica'] == replica]]]
    headroom = metrics['ORACLE']['utility']-metrics['ONE']['utility']
    learners = {name: dict(selected_lambda=selection[name]['selected_lambda'], source_heldout_utility=selection[name]['selected_utility'],
        source_selection=[dict(lambda_value=row['lambda_value'], utility=row['utility']) for row in selection[name]['candidates']],
        columns=models[name]['constants']['columns'], source_rank=models[name]['rank'], source_root_mean_loss=models[name]['root_mean_loss']) for name in MODES}
    return dict(schema=SCHEMA+'.summary', complete=True, roots=len(records),
        SOURCE=dict(roots=len(roots['SOURCE']), design_groups=len({row['source_id'] for row in roots['SOURCE']}), learners=learners),
        models=metrics, comparisons=effects, replicas=replicas, root_records=records, oracle_minus_one=headroom,
        oracle_minus_interact=metrics['ORACLE']['utility']-metrics['INTERACT']['utility'],
        headroom_closed_fraction=effects['INTERACT_MINUS_ONE']['utility']/headroom if headroom > EPS else None,
        whole_cohort_positive_vs_linear_ridge_old_shared=all(effects['INTERACT_MINUS_'+name]['utility'] > EPS for name in ('LINEAR', 'RIDGE', 'OLD_SHARED')),
        all_replicas_positive_vs_linear_ridge_old_shared=all(row['comparisons']['INTERACT_MINUS_'+name]['utility'] > EPS for row in replicas for name in ('LINEAR', 'RIDGE', 'OLD_SHARED')),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=26)


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, io, binding_work = [], Counter(), Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); io.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    names = ('stage_checks.json', 'v187_run.json', 'source_labels.json', 'expanded_models.json', 'baseline_models.json', 'learned_rule.json')
    expected_inputs = [(f'inputs/inherited/{name}', 'protocol_frozen') for name in names]
    check('six_frozen_SOURCE_and_control_inputs', [(row['saved_ref'], row['phase']) for row in inputs] == expected_inputs)
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        io.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        check('retained_input:'+row['saved_ref'], saved == original and len(saved) == row['bytes'])
    stage, inherited_run = read('inputs/inherited/stage_checks.json'), read('inputs/inherited/v187_run.json')
    check('settled_V187_complete', stage['valid'] and inherited_run['status'] == 'complete')
    source = read('inputs/inherited/source_labels.json'); controls, old_controls = read('inputs/inherited/expanded_models.json'), read('inputs/inherited/baseline_models.json')
    fixed_source = len(source) == 143 and len({row['source_id'] for row in source}) == 36
    check('unchanged_SOURCE143_and_36_groups', fixed_source and read('source_labels.json') == source and controls['RIDGE']['constants']['lambda_value'] == .1)
    saved_selection, saved_models = read('selection.json'), read('models.json')
    fitted, solver_work = fit_models(source, saved_selections=saved_selection, saved_models=saved_models)
    selection = dict(fitted['selections'], costs=fitted['costs']); new_models = fitted['models']
    certificates = solver_work['independent_coefficient_arrays_checked'] == solver_work['independent_coefficient_arrays_passed'] == 26
    check('26_independent_coefficients_before_actual_EPS_scoring', certificates)
    check('matched_LINEARSOURCE_and_INTERACTSOURCE_group_selection', same(saved_selection, selection))
    check('two_new_fixed_mechanism_models', same(saved_models, new_models))
    counts = fitted['costs']
    budget = counts['ridge_design_preparations'] == counts['ridge_svd_decompositions'] == 6 and counts['ridge_predictors_fitted'] == counts['new_predictors_fitted'] == 26
    check('once_SOURCE_cache_six_decompositions_26_filters_and_costs', budget and run['costs']['learning']['counts'] == counts)
    cases = cohort_cases(); target, observation_work = coverage.observe_roots(cases); feature_work = cache_roots(target)
    check('96_fresh_seeded_targets_without_replacement', read('target_cases.json') == cases)
    roots = dict(SOURCE=source, TARGET=target)
    check('unchanged_SOURCE_and_observable_target_interaction_caches', same(read('roots.json'), roots))
    feature_costs = run['costs']['observations']['counts'] == observation_work and run['costs']['observations']['feature_counts'] == feature_work
    check('one_target_geometry_cache_and_mechanism_construction_costs', feature_costs)
    models = dict(controls, **new_models, OLD_SHARED=old_controls['SHARED'], ONE=old_controls['ONE']); choices, choice_work = freeze_choices(target, models)
    check('both_SOURCE_selected_models_and_frozen_control_choices', same(read('choices.json'), choices))
    check('all_mechanism_full_vector_support_and_choice_costs', run['costs']['choices']['counts'] == choice_work)
    native, label_costs = read('native_labels.json'), read('label_costs.json'); ids = [root['root_id'] for root in target]
    check('complete_native_label_and_cost_rosters', [row['root_id'] for row in native] == ids and [row['root_id'] for row in label_costs] == ids)
    labels, label_work = [], Counter()
    for root, raw, cost_row in zip(target, native, label_costs, strict=True):
        teacher = read(f"teacher_policy/{root['root_id']}.json")
        check('settled_native_fraction_teacher_binding:'+root['root_id'], coverage.native_binding(root, raw, teacher))
        binding_work.update(new_label_roots_bound=1, teacher_root_records_inspected=len(teacher), exact_component_coordinates_bound=3*len(root['legal_actions']))
        provenance = dict(kind='new_exact_V69_FULL', teacher_query='goal_1_risk_1', teacher_policy_ref='teacher_policy/'+root['root_id']+'.json')
        labels.append(exact.canonical_labels(root, raw, provenance))
        costs = cost_row['costs']; construction, compilation, export = costs['construction'], costs['compilation'], costs['teacher_export']; n = len(teacher)
        accounting = construction['concrete_states'] <= 200000 and construction['concrete_active_states'] == construction['active_states'] == n
        accounting = accounting and compilation['model_payload_calls'] == compilation['model_reload_calls'] == 1
        accounting = accounting and compilation['payload_cells'] == construction['registered_states'] == costs['label_evaluation']['kernel_cells_read']
        accounting = accounting and compilation['payload_rows'] == costs['label_evaluation']['kernel_rows_read'] and compilation['payload_outcomes'] == costs['label_evaluation']['kernel_outcomes_read']
        accounting = accounting and costs['label_evaluation']['root_labels_emitted'] == 1
        expected_export = dict(teacher_encoding_records_read=construction['concrete_states'], teacher_policy_records=n, teacher_policy_action_reads=n, teacher_policy_tile_reads=16*n)
        check('settled_acquisition_caps_and_export_costs:'+root['root_id'], accounting and export == expected_export)
        for kind in ('construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation'):
            label_work.update({kind+'.'+key: value for key, value in costs[kind].items() if type(value) is int})
    check('all_canonical_target_vectors_and_fractions_bound', same(read('labels.json'), labels))
    summary = summarize(roots, labels, choices, selection, new_models)
    check('actual_RFS_controls_regret_replicas_and_gain_concentration', same(read('summary.json'), summary))
    phases = ['protocol_frozen', 'source_selection', 'models_frozen', 'target_roots', 'target_choices_frozen', 'target_labels', 'complete']
    expected_phases = [(phase, 0 if i == 0 else 6) for i, phase in enumerate(phases)]
    check('both_SOURCE_selections_and_all_choices_before_target_labels', [(row['phase'], row['input_reads']) for row in run['phase_history']] == expected_phases)
    input_counts = dict(json_read_operations=6, input_bytes_read=sum(row['bytes'] for row in inputs), input_bytes_retained=sum(row['bytes'] for row in inputs))
    check('all_paid_input_and_label_counts', run['costs']['input_counts'] == input_counts and run['costs']['labels']['counts'] == dict(label_work))
    accounting = all(run[key] == 96 for key in ('new_boards_generated', 'new_reference_kernel_attempts', 'new_reference_kernels', 'new_teacher_plans', 'new_exact_label_roots', 'completed_roots'))
    accounting = accounting and run['new_learning_attempts'] == 1 and run['new_predictors_fitted'] == 26 and run['resource_cap_per_board'] == 200000
    accounting = accounting and all(run[key] == 0 for key in ('new_environment_samples', 'new_source_games', 'new_native_weight_updates'))
    check('matched_two_arm_selection_26_predictors_96_labels_no_sampling', accounting)
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and summary['complete']
    return dict(schema=SCHEMA+'.analysis', valid=valid, complete=complete, primary_complete=complete, checks=checks,
        passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=summary,
        costs=dict(new_environment_samples=0, physical_branches_replayed=0, old_kernels_reevaluated=0, new_kernels_reintegrated=0, old_models_refitted=0,
            independent_input_counts=dict(io), independent_coefficient_solver_counts=solver_work, reconstructed_learning_counts=counts,
            independent_SOURCE_cache_counts=fitted['cache_counts'], independent_observation_counts=observation_work, independent_feature_counts=feature_work,
            independent_choice_counts=choice_work, independent_new_label_binding_counts=dict(binding_work), reconstructed_acquisition_counts=dict(label_work),
            original_run_costs=run['costs'], inherited_cost_refs=run['inherited_cost_refs'], test_refs=run['test_refs'], seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    args = parser.parse_args(); result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'], new_environment_samples=0)))


if __name__ == '__main__':
    main()
