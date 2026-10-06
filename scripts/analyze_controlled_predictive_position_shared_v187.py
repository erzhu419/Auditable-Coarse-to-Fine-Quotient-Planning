"""Independent occurrence pooling, SOURCE-only ridge selection and consequences."""
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
from scripts import analyze_controlled_predictive_source_regularization_v183 as ridge
from scripts import analyze_controlled_predictive_action_ranking_v186 as previous

coverage, layout, shared, exact = previous.coverage, previous.layout, previous.shared, previous.exact
ACTIONS, EPS, LAMBDAS = exact.ACTIONS, exact.EPS, ridge.LAMBDAS
SCHEMA, REPRESENTATION = 'acfqp.position_shared.v187', 'POSITION_SHARED_OCCURRENCE_SUM'
MODEL_NAMES = ('POOL', 'RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE')
OUTPUT = PROJECT/'reports/controlled_predictive_position_shared_v187'
same = coverage.same


def action_features_from_root(root, counts=None):
    work = Counter()
    if 'pooled_features' in root:
        features = {action: dict(aggregate=list(row['aggregate']), tokens=[list(token) for token in row['tokens']])
                    for action, row in root['pooled_features'].items()}
        work.update(pool_feature_cache_hits=1, pool_cached_aggregate_reads=6*len(features),
                    pool_cached_token_occurrences=40*len(features), pool_cached_token_values=104*len(features))
    else:
        features = {}
        for action, row in root['layout_features'].items():
            tokens = [[token[0], token[2]] if token[0] == 'cell' else [token[0], token[2], token[3]] for token in row['tokens']]
            features[action] = dict(aggregate=list(row['aggregate']), tokens=tokens)
            work.update(pool_aggregate_values_copied=6, pool_token_occurrences_read=40,
                        pool_token_kind_reads=40, pool_rank_values_copied=64, pool_positions_discarded=40)
        work['pool_feature_maps_derived'] += 1
    if counts is not None:
        counts.update(work)
    return features


pooled_features_from_root = action_features_from_root


def encode_action(record, indexed, work):
    encoded = dict(enumerate(map(float, record['aggregate']))); known = unknown = 0
    for token in record['tokens']:
        work['token_lookups'] += 1; column = indexed.get(tuple(token))
        if column is None:
            unknown += 1; work['unknown_token_entries'] += 1
        else:
            known += 1; work['pool_duplicate_occurrences'] += int(column in encoded)
            encoded[column] = encoded.get(column, 0.)+layout.token_weight(token)
            work.update(known_token_entries=1, token_weight_loads=1, pool_occurrence_accumulations=1)
    work.update(encoded_actions=1, aggregate_values_read=6)
    return encoded, dict(known_tokens=known, unknown_tokens=unknown, total_tokens=len(record['tokens']))


def prepare_design(examples, life=0):
    counts, feature_counts, encoder_counts = Counter(), Counter(), Counter(); roots, features = [], {}
    for original in examples:
        counts['examples_examined'] += 1
        if original['life'] != life:
            counts['other_life_examples_excluded'] += 1; continue
        root = deepcopy(original); legal = [action for action in ACTIONS if action in root['legal_actions']]
        root['legal_actions'] = legal
        root['immediate_rewards'] = {action: float(root['immediate_rewards'][action]) for action in legal}
        root['action_components'] = {action: list(map(float, root['action_components'][action])) for action in legal}
        root['pooled_features'] = action_features_from_root(root, feature_counts)
        features[root['root_id']] = root['pooled_features']; roots.append(root)
        counts.update(examples_fitted=1, root_feature_tile_reads=16, legal_action_reads=len(legal), immediate_reward_reads=len(legal),
                      exact_action_vector_reads=len(legal), label_component_reads=3*len(legal), tail_reward_subtractions=len(legal))
    roots.sort(key=lambda row: row['root_id'])
    vocabulary = [list(token) for token in sorted({tuple(token) for root in roots for action in root['legal_actions'] for token in features[root['root_id']][action]['tokens']})]
    counts.update(source_vocabulary_tokens=len(vocabulary), vocabulary_token_records_read=sum(40*len(root['legal_actions']) for root in roots))
    indexed = layout.vocabulary_index(vocabulary, encoder_counts)
    action_roots = {action: set() for action in ACTIONS}; pair_roots = {f'{a}|{b}': set() for a, b in combinations(ACTIONS, 2)}
    labels, records = [], []
    for root in roots:
        legal = root['legal_actions']; encoded = {action: encode_action(features[root['root_id']][action], indexed, encoder_counts)[0] for action in legal}
        for action in legal:
            action_roots[action].add(root['root_id'])
        pairs = []
        for ia, ib, weight, target in exact.exact_pair_samples(root):
            first, second = ACTIONS[ia], ACTIONS[ib]; columns = sorted(set(encoded[first]) | set(encoded[second]))
            sparse = [[column, encoded[first].get(column, 0.)-encoded[second].get(column, 0.)] for column in columns]
            sparse = [[column, value] for column, value in sparse if value != 0.]
            pair = dict(actions=[first, second], weight=weight, design=sparse, components=target); pairs.append(deepcopy(pair))
            records.append(dict(root_id=root['root_id'], source_id=root['source_id'], **pair)); pair_roots[f'{first}|{second}'].add(root['root_id'])
            counts.update(paired_vector_labels=1, paired_component_subtractions=3, layout_pair_rows=1, layout_design_value_lookups=2*len(columns),
                          layout_design_subtractions=len(columns), layout_nonzero_design_entries=len(sparse))
        labels.append(dict(root_id=root['root_id'], source_id=root['source_id'], legal_actions=legal, label_kind='exact_enumerated_vector', pairs=pairs))
    matrix, targets = np.zeros((len(records), 6+len(vocabulary))), np.zeros((len(records), 3))
    for index, record in enumerate(records):
        scale = math.sqrt(record['weight'])
        for column, value in record['design']:
            matrix[index, column] = scale*value
        targets[index] = [scale*value for value in record['components']]
        counts.update(layout_weight_square_roots=1, layout_weighted_design_scalings=len(record['design']), layout_weighted_target_scalings=3)
    counts.update(layout_design_matrix_cells=matrix.size, layout_target_matrix_cells=targets.size, ridge_design_preparations=1)
    sources = dict(Counter(root['source_id'] for root in roots)); pair_ids = {pair: sorted(ids) for pair, ids in pair_roots.items()}
    return dict(schema=SCHEMA+'.design', representation=REPRESENTATION, life=life, vocabulary=vocabulary, roots=roots,
        root_ids=[root['root_id'] for root in roots], source_ids=sorted(sources), source_root_counts=sources,
        action_root_ids={action: sorted(ids) for action, ids in action_roots.items()}, pair_root_ids=pair_ids,
        connected_components=shared.connected_components(pair_ids), fit_labels=labels, pair_records=records, design_format='sparse_columns',
        shape=list(matrix.shape), X=matrix, Y=targets, prepare_counts=dict(counts), feature_counts=dict(feature_counts), encoder_counts=dict(encoder_counts),
        work=dict(counts+feature_counts+encoder_counts))


def ridge_coefficients(matrix, targets, roots, lambda_value, work):
    if lambda_value == 0:
        coefficients, _, rank, singular = np.linalg.lstsq(matrix, targets, rcond=None)
        work.update(zero_minimum_norm_lstsq_solves=1, least_squares_design_cells=matrix.size, least_squares_target_cells=targets.size)
        return coefficients, int(rank), singular
    normal = matrix.T@matrix+roots*lambda_value*np.eye(matrix.shape[1]); rhs = matrix.T@targets
    coefficients = np.linalg.solve(normal, rhs)
    work.update(positive_column_normal_solves=1, column_normal_matrix_cells=normal.size, column_normal_rhs_cells=rhs.size, ridge_coefficients_cells=coefficients.size)
    return coefficients, None, None


def fit_design(design, lambda_value, audit_work, saved_coefficients=None):
    coefficients, rank, singular = ridge_coefficients(design['X'], design['Y'], len(design['roots']), lambda_value, audit_work)
    if saved_coefficients is not None:
        audit_work.update(independent_coefficient_arrays_checked=1,
                          independent_coefficient_arrays_passed=int(same(saved_coefficients, coefficients.tolist())),
                          independent_coefficient_values_compared=coefficients.size)
        coefficients = np.asarray(saved_coefficients, dtype=float)
    width = min(design['X'].shape); counts = Counter(ridge_coefficient_filters=1, ridge_predictors_fitted=1,
        ridge_singular_filter_values=width, ridge_projected_component_scalings=3*width, ridge_coefficient_cells=coefficients.size)
    losses, residuals = [0., 0., 0.], []
    for row in design['pair_records']:
        prediction = [float(sum(value*coefficients[column, k] for column, value in row['design'])) for k in range(3)]
        residual = [prediction[k]-row['components'][k] for k in range(3)]; weighted = [row['weight']*value*value for value in residual]
        losses = [losses[k]+weighted[k] for k in range(3)]
        residuals.append(dict(deepcopy(row), predicted_components=prediction, residual_components=residual, weighted_component_losses=weighted, weighted_loss=sum(weighted)))
        counts.update(ridge_fit_prediction_coefficient_reads=3*len(row['design']), ridge_fit_residual_component_subtractions=3, ridge_fit_weighted_component_losses=3)
    penalty = float(lambda_value*np.sum(coefficients*coefficients)); counts['ridge_penalty_coefficient_squares'] += coefficients.size
    return dict(coefficients=coefficients.tolist(), component_losses=losses, loss=sum(losses), root_mean_loss=sum(losses)/len(design['roots']),
                penalty=penalty, objective=sum(losses)/len(design['roots'])+penalty, residuals=residuals, counts=dict(counts)), rank, singular


def model_from_fit(design, decomposition, fitted, lambda_value, source_folds):
    model = ridge.model_from_fit(design, decomposition, fitted, lambda_value, source_folds)
    model.update(schema=SCHEMA+'.model', mode='POOL', representation=REPRESENTATION)
    return model


def choose_action(payload, root, counts=None):
    legal = [action for action in ACTIONS if action in root['legal_actions']]
    feature_work = Counter(); features = action_features_from_root(root, feature_work)
    work = Counter(pool_decisions=1, pool_legal_action_reads=len(legal)); indexed = layout.vocabulary_index(payload['vocabulary'], work)
    action_counts = {action: len(payload['action_root_ids'][action]) for action in legal}
    pair_counts = {f'{a}|{b}': len(payload['pair_root_ids'][f'{a}|{b}']) for a, b in combinations(legal, 2)}
    connected = payload['connected_components']; component = {action: index for index, group in enumerate(connected) for action in group}
    work.update(pool_action_support_lookups=len(legal), pool_pair_support_lookups=len(pair_counts), pool_component_membership_lookups=len(legal))
    if len(legal) == 1:
        selected, fallback, reason = legal[0], False, 'single_legal_action'
    elif any(value < 4 for value in action_counts.values()):
        selected, fallback, reason = root['fallback_action'], True, 'insufficient_action_support'
    elif len({component[action] for action in legal}) != 1:
        selected, fallback, reason = root['fallback_action'], True, 'disconnected_required_actions'
    else:
        selected, fallback, reason = None, False, 'selected'
    predicted, action_coverage = {}, {}
    for action in legal:
        entries, action_coverage[action] = encode_action(features[action], indexed, work)
        vector = [sum(value*payload['coefficients'][column][k] for column, value in entries.items()) for k in range(3)]
        vector[0] += root['immediate_rewards'][action]; predicted[action] = vector
        work.update(pool_prediction_coefficient_reads=3*len(entries), pool_prediction_value_reads=3*len(entries), pool_prediction_component_evaluations=3,
                    pool_immediate_reward_reads=1, pool_reward_additions=1)
    pairs = {f'{a}|{b}': [predicted[a][k]-predicted[b][k] for k in range(3)] for a, b in combinations(legal, 2) if component[a] == component[b]}
    if pairs:
        work['pool_predicted_pair_subtractions'] += 3*len(pairs)
    if selected is None:
        best = None
        for action in legal:
            value = exact.utility(predicted[action]); work['pool_utility_evaluations'] += 1
            if best is None or value > best+EPS:
                selected, best = action, value
    result = dict(canonical_action=selected, actual_action=root['action_map'][selected], fallback=fallback, leaf=0, reason=reason,
        predicted_components=predicted, predicted_pairs=pairs,
        support=dict(action_root_counts=action_counts, pair_root_counts=pair_counts, connected_components=deepcopy(connected), required_actions=legal, complete=not fallback),
        coverage=action_coverage, work=dict(work), feature_work=dict(feature_work))
    if counts is not None:
        counts.update(work); counts.update(feature_work)
    return result


def score_heldout(model, roots):
    counts, groups, choices = Counter(), {}, []
    keys = ('root_id', 'source_id', 'life', 'canonical_board', 'legal_actions', 'immediate_rewards', 'fallback_action', 'action_map', 'layout_features')
    for root in sorted(roots, key=lambda row: row['root_id']):
        observable = {key: root[key] for key in keys}
        if 'pooled_features' in root:
            observable['pooled_features'] = root['pooled_features']
        decision = choose_action(model, observable, counts); vector = list(map(float, root['action_components'][decision['canonical_action']]))
        groups.setdefault(root['source_id'], []).append(vector)
        choices.append(dict(root_id=root['root_id'], source_id=root['source_id'], decision=decision, components=vector, utility=exact.utility(vector)))
        counts.update(heldout_action_vector_reads=1, heldout_component_reads=3, heldout_utility_evaluations=1)
    records = []
    for source, vectors in sorted(groups.items()):
        mean = [sum(vector[k] for vector in vectors)/len(vectors) for k in range(3)]
        records.append(dict(source_id=source, roots=len(vectors), components=mean, utility=exact.utility(mean)))
        counts.update(heldout_group_component_means=3, heldout_group_utility_evaluations=1)
    return records, choices, dict(counts)


def select_regularization(examples, life=0, saved_selection=None, saved_model=None):
    examples = list(examples); sources = sorted({row['source_id'] for row in examples if row['life'] == life})
    if len(sources) != 36:
        raise ValueError('Thirty-six fixed SOURCE groups required')
    source_folds = [sources[::2], sources[1::2]]; costs = Counter(source_fold_assignments=36, regularization_candidates=6)
    audit_work, designs, heldouts, saved_folds, metadata = Counter(), [], [], [], []
    for fold, heldout in enumerate(source_folds):
        train_sources = [source for source in sources if source not in heldout]
        design = prepare_design([row for row in examples if row['life'] == life and row['source_id'] in train_sources], life)
        designs.append(design); costs.update(design['work']); heldouts.append([row for row in examples if row['life'] == life and row['source_id'] in heldout])
        saved_folds.append(dict(fold=fold, train_sources=train_sources, heldout_sources=list(heldout), design={key: value for key, value in design.items() if key not in ('X', 'Y')}))
    candidates, selected, best = [], LAMBDAS[0], None
    for candidate_index, lambda_value in enumerate(LAMBDAS):
        fold_results, groups = [], []
        for fold in range(2):
            saved = None if saved_selection is None else saved_selection['candidates'][candidate_index]['fold_results'][fold]['coefficients']
            fitted, rank, singular = fit_design(designs[fold], lambda_value, audit_work, saved); costs.update(fitted['counts'])
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
    full = prepare_design(examples, life); costs.update(full['work'])
    saved = None if saved_model is None else saved_model['coefficients']
    fitted, rank, singular = fit_design(full, selected, audit_work, saved); costs.update(fitted['counts'])
    if selected > 0:
        singular = np.linalg.svd(full['X'], compute_uv=False); cutoff = np.finfo(float).eps*max(full['X'].shape)*(singular[0] if len(singular) else 0.)
        rank = int(sum(singular > cutoff)); audit_work.update(final_singular_values_only_decompositions=1, final_singular_values_matrix_cells=full['X'].size)
    meta = ridge.decomposition_metadata(full, rank, singular); costs.update(meta['work']); costs['new_predictors_fitted'] = costs['ridge_predictors_fitted']
    return dict(schema=SCHEMA+'.selection', representation=REPRESENTATION, life=life, lambdas=list(LAMBDAS), source_folds=source_folds,
        folds=saved_folds, candidates=candidates, selected_lambda=selected, selected_utility=best,
        model=model_from_fit(full, meta, fitted, selected, source_folds), costs=dict(costs)), dict(audit_work)


def cohort_cases():
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]+[(4*r+c, 4*r+c+4) for r in range(3) for c in range(4)]
    cases = []
    for replica in range(4):
        for index, (first, second) in enumerate(edges):
            seed = 1870200+24*replica+index; rng = random.Random(seed); board = [rng.randint(1, 10) for _ in range(16)]
            board[first] = board[second] = 1+index % 10
            for cell in rng.sample([cell for cell in range(16) if cell not in (first, second)], index % 3):
                board[cell] = 0
            cases.append(dict(split='TARGET', replica=replica, stratum=index, name=f'v187_target_r{replica:02d}_{index:02d}', horizon=3, seed=seed, board=board, vacancies=index % 3))
    return cases


def cache_roots(roots):
    work = Counter(coverage.cache_roots(roots))
    for root in roots:
        root['pooled_features'] = action_features_from_root(root, work)
    return dict(work)


def freeze_choices(roots, models):
    choices, work = {name: [] for name in (*MODEL_NAMES, 'FALLBACK')}, Counter()
    keys = ('root_id', 'source_id', 'life', 'canonical_board', 'legal_actions', 'immediate_rewards', 'fallback_action', 'action_map', 'layout_features', 'action_features', 'pooled_features')
    for root in roots:
        observed = {key: root[key] for key in keys}
        for name in MODEL_NAMES:
            chooser = choose_action if name == 'POOL' else shared.choose_action if name in ('SHARED', 'OLD_SHARED') else exact.choose_action if name == 'ONE' else layout.choose_action
            decision = chooser(models[name], observed); work.update(decision['work']); work.update(decision.get('feature_work', {})); work['pool_frozen_model_choices'] += 1
            choices[name].append(dict(root_id=root['root_id'], mode=name, canonical_action=decision['canonical_action'], actual_action=decision['actual_action'], fallback=decision['fallback'], decision=decision))
        action = root['fallback_action']; work['pool_frozen_fallback_choices'] += 1
        choices['FALLBACK'].append(dict(root_id=root['root_id'], mode='FALLBACK', canonical_action=action, actual_action=root['action_map'][action], fallback=False,
            decision=dict(reason='observable_immediate_reward', work=dict(pool_frozen_fallback_choices=1))))
    return choices, dict(work)


def summarize(roots, labels, choices, selection, model):
    renamed_choices = {('RANK' if name == 'POOL' else name): rows for name, rows in choices.items()}
    old = previous.summarize(roots, labels, renamed_choices, dict(design=dict(rows=[]), objective=0., gradient_inf=0., objective_gap_upper_bound=0.))
    old.update(schema=SCHEMA+'.summary', new_predictors_fitted=13)
    old['SOURCE'] = dict(roots=len(roots['SOURCE']), design_groups=len({row['source_id'] for row in roots['SOURCE']}),
        selected_lambda=selection['selected_lambda'], source_heldout_utility=selection['selected_utility'],
        source_selection=[dict(lambda_value=row['lambda_value'], utility=row['utility']) for row in selection['candidates']],
        vocabulary_tokens=len(model['vocabulary']), columns=model['constants']['columns'], source_rank=model['rank'], source_root_mean_loss=model['root_mean_loss'])
    old['oracle_minus_pool'] = old.pop('oracle_minus_rank')
    for group in [old, *old['replicas']]:
        group['models']['POOL'] = group['models'].pop('RANK')
        group['comparisons'] = {name.replace('RANK_MINUS_', 'POOL_MINUS_'): row for name, row in group['comparisons'].items()}
    for record in old['root_records']:
        record['models']['POOL'] = record['models'].pop('RANK')
    return old


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, io, binding_work = [], Counter(), Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); io.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    names = ('stage_checks.json', 'v186_run.json', 'source_labels.json', 'expanded_models.json', 'baseline_models.json', 'learned_rule.json')
    check('six_frozen_SOURCE_and_control_inputs', [(row['saved_ref'], row['phase']) for row in inputs] == [(f'inputs/inherited/{name}', 'protocol_frozen') for name in names])
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        io.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        check('retained_input:'+row['saved_ref'], saved == original and len(saved) == row['bytes'])
    stage, inherited_run = read('inputs/inherited/stage_checks.json'), read('inputs/inherited/v186_run.json')
    check('settled_V186_complete', stage['valid'] and inherited_run['status'] == 'complete')
    source = read('inputs/inherited/source_labels.json'); controls, old_controls = read('inputs/inherited/expanded_models.json'), read('inputs/inherited/baseline_models.json')
    source_identity = len(source) == 143 and len({row['source_id'] for row in source}) == 36
    check('unchanged_SOURCE143_and_36_groups', source_identity and read('source_labels.json') == source and controls['RIDGE']['constants']['lambda_value'] == .1)
    saved_selection, saved_models = read('selection.json'), read('models.json')
    selection, solver_work = select_regularization(source, saved_selection=saved_selection, saved_model=saved_models['POOL']); model = selection.pop('model')
    certified = solver_work['independent_coefficient_arrays_checked'] == solver_work['independent_coefficient_arrays_passed'] == 13
    check('13_independent_coefficient_certificates_before_actual_EPS_scoring', certified)
    check('independent_occurrence_sum_folds_support_objective_and_group_utility_selection', same(saved_selection, selection))
    check('one_new_position_shared_model', same(saved_models, dict(POOL=model)))
    counts = selection['costs']
    budget = counts['ridge_design_preparations'] == counts['ridge_svd_decompositions'] == 3 and counts['ridge_predictors_fitted'] == counts['new_predictors_fitted'] == 13
    check('three_production_decompositions_thirteen_filters_and_paid_learning', budget and run['costs']['learning']['counts'] == counts)
    cases = cohort_cases(); target, observation_work = coverage.observe_roots(cases); feature_work = cache_roots(target)
    check('96_fresh_seeded_targets_without_replacement', read('target_cases.json') == cases)
    roots = dict(SOURCE=source, TARGET=target)
    check('unchanged_SOURCE_and_observable_target_pooled_caches', same(read('roots.json'), roots))
    check('one_target_geometry_cache_and_no_source_swipes', run['costs']['observations']['counts'] == observation_work and run['costs']['observations']['feature_counts'] == feature_work)
    models = dict(controls, POOL=model, OLD_SHARED=old_controls['SHARED'], ONE=old_controls['ONE']); choices, choice_work = freeze_choices(target, models)
    check('SOURCE_selected_POOL_and_frozen_control_choices', same(read('choices.json'), choices))
    check('all_occurrence_encoding_support_and_choice_costs', run['costs']['choices']['counts'] == choice_work)
    native, label_costs = read('native_labels.json'), read('label_costs.json'); ids = [root['root_id'] for root in target]
    check('complete_new_native_label_and_cost_rosters', [row['root_id'] for row in native] == ids and [row['root_id'] for row in label_costs] == ids)
    labels, label_work = [], Counter()
    for root, raw, cost_row in zip(target, native, label_costs, strict=True):
        teacher = read(f"teacher_policy/{root['root_id']}.json")
        check('settled_native_fraction_teacher_binding:'+root['root_id'], coverage.native_binding(root, raw, teacher))
        binding_work.update(new_label_roots_bound=1, teacher_root_records_inspected=len(teacher), exact_component_coordinates_bound=3*len(root['legal_actions']))
        labels.append(exact.canonical_labels(root, raw, dict(kind='new_exact_V69_FULL', teacher_query='goal_1_risk_1', teacher_policy_ref='teacher_policy/'+root['root_id']+'.json')))
        costs = cost_row['costs']; construction, compilation, export = costs['construction'], costs['compilation'], costs['teacher_export']; n = len(teacher)
        accounting = construction['concrete_states'] <= 200000 and construction['concrete_active_states'] == construction['active_states'] == n
        accounting = accounting and compilation['model_payload_calls'] == compilation['model_reload_calls'] == 1
        accounting = accounting and compilation['payload_cells'] == construction['registered_states'] == costs['label_evaluation']['kernel_cells_read']
        accounting = accounting and compilation['payload_rows'] == costs['label_evaluation']['kernel_rows_read'] and compilation['payload_outcomes'] == costs['label_evaluation']['kernel_outcomes_read']
        accounting = accounting and costs['label_evaluation']['root_labels_emitted'] == 1
        accounting = accounting and export == dict(teacher_encoding_records_read=construction['concrete_states'], teacher_policy_records=n, teacher_policy_action_reads=n, teacher_policy_tile_reads=16*n)
        check('settled_acquisition_caps_and_export_costs:'+root['root_id'], accounting)
        for kind in ('construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation'):
            label_work.update({kind+'.'+key: value for key, value in costs[kind].items() if type(value) is int})
    check('all_canonical_full_vectors_and_fractions_bound', same(read('labels.json'), labels))
    summary = summarize(roots, labels, choices, selection, model)
    check('actual_RFS_regret_replicas_concentration_and_source_CV_summary', same(read('summary.json'), summary))
    phases = ['protocol_frozen', 'source_selection', 'models_frozen', 'target_roots', 'target_choices_frozen', 'target_labels', 'complete']
    check('SOURCE_CV_then_all_choices_before_target_labels', [(row['phase'], row['input_reads']) for row in run['phase_history']] == [(phase, 0 if i == 0 else 6) for i, phase in enumerate(phases)])
    input_counts = dict(json_read_operations=6, input_bytes_read=sum(row['bytes'] for row in inputs), input_bytes_retained=sum(row['bytes'] for row in inputs))
    check('all_paid_input_and_label_counts', run['costs']['input_counts'] == input_counts and run['costs']['labels']['counts'] == dict(label_work))
    accounting = all(run[key] == 96 for key in ('new_boards_generated', 'new_reference_kernel_attempts', 'new_reference_kernels', 'new_teacher_plans', 'new_exact_label_roots', 'completed_roots'))
    accounting = accounting and run['new_learning_attempts'] == 1 and run['new_predictors_fitted'] == 13 and run['resource_cap_per_board'] == 200000
    accounting = accounting and all(run[key] == 0 for key in ('new_environment_samples', 'new_source_games', 'new_native_weight_updates'))
    check('one_SOURCE_selection_13_predictors_96_labels_and_no_sampling', accounting)
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and summary['complete']
    return dict(schema=SCHEMA+'.analysis', valid=valid, complete=complete, primary_complete=complete, checks=checks,
        passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=summary,
        costs=dict(new_environment_samples=0, physical_branches_replayed=0, old_kernels_reevaluated=0, new_kernels_reintegrated=0, old_models_refitted=0,
            independent_input_counts=dict(io), independent_coefficient_solver_counts=solver_work, reconstructed_learning_counts=counts,
            independent_observation_counts=observation_work, independent_feature_counts=feature_work, independent_choice_counts=choice_work,
            independent_new_label_binding_counts=dict(binding_work), reconstructed_acquisition_counts=dict(label_work),
            original_run_costs=run['costs'], inherited_cost_refs=run['inherited_cost_refs'], test_refs=run['test_refs'], seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    args = parser.parse_args(); result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'], new_environment_samples=0)))


if __name__ == '__main__':
    main()
