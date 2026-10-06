"""Independent shifted-system certificates and actual R/F/S kernel scores."""
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
from scripts import analyze_controlled_predictive_merge_relations_v190 as relation
from acfqp.science import controlled_predictive_exact_h3_v177 as native_exact

ACTIONS, EPS = relation.ACTIONS, relation.EPS
GAMMAS = (.25, 1., 4.)
LAMBDAS = (.0001, .001, .01, .1, 1.)
COLUMNS = 98
SCHEMA = 'acfqp.nonlinear_relations.v192'
OUTPUT = PROJECT/'reports/controlled_predictive_nonlinear_relations_v192'
CONTROLS = ('RELATION', 'LINEAR', 'INTERACT', 'RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE')
MODEL_NAMES = ('NONLINEAR', *CONTROLS)


def certify_coefficients(H, Y, B, roots, lambda_value, saved_alpha, saved_coefficients, work):
    """Certify the arrays used for scoring with one independent direct solve."""
    matrix = H+roots*lambda_value*np.eye(len(H))
    work.update(independent_shifted_system_solves=1, independent_shifted_system_matrix_cells=matrix.size,
        independent_shifted_system_target_cells=Y.size)
    alpha = np.linalg.solve(matrix, Y)
    coefficients = B.T@alpha
    actual_alpha, actual_coefficients = np.asarray(saved_alpha, dtype=float), np.asarray(saved_coefficients, dtype=float)
    correct_shape = actual_alpha.shape == alpha.shape and actual_coefficients.shape == coefficients.shape
    passed = correct_shape and bool(np.all(np.abs(actual_alpha-alpha) <= 1e-8*(1.+np.abs(alpha)))) and bool(
        np.all(np.abs(actual_coefficients-coefficients) <= 1e-8*(1.+np.abs(coefficients))))
    work.update(independent_predictors_checked=1, independent_predictors_passed=int(passed),
        independent_dual_coefficient_entries_checked=alpha.size,
        independent_center_coefficient_entries_checked=coefficients.size)
    if not passed:
        raise ValueError('saved kernel coefficients fail the frozen direct-system tolerance')
    # All subsequent histories use these certified saved arrays.
    return actual_alpha, actual_coefficients


def observable(root):
    return relation.observable(root)


def cohort_cases():
    cases = []
    for replica in range(4):
        for index in range(24):
            seed = 1920200+24*replica+index; rng = random.Random(seed)
            board = [rng.randint(1, 10) for _ in range(16)]
            edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]
            edges += [(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
            first, second = edges[index]; rank = 1+index%10
            board[first] = board[second] = rank
            for position in rng.sample([p for p in range(16) if p not in (first, second)], index%3):
                board[position] = 0
            cases.append(dict(name=f'v192_target_r{replica:02d}_{index:02d}', split='TARGET', seed=seed,
                replica=replica, stratum=index, board=board, horizon=3, vacancies=index%3))
    return cases


def observe_roots(cases):
    # The settled V184 observer emits FRESH metadata, not a SOURCE split.
    return relation.observe_roots(cases)


def distance(first, second):
    return sum((first[index]-second[index])**2 for index in range(COLUMNS))


def prepare_design(examples, life=0):
    counts, roots = Counter(), []
    for original in examples:
        counts['examples_examined'] += 1
        if original['life'] != life:
            counts['other_life_examples_excluded'] += 1; continue
        root = deepcopy(original); legal = [action for action in ACTIONS if action in root['legal_actions']]
        root['legal_actions'] = legal
        root['immediate_rewards'] = {action: float(root['immediate_rewards'][action]) for action in legal}
        root['action_components'] = {action: list(map(float, root['action_components'][action])) for action in legal}
        roots.append(root)
        counts.update(examples_fitted=1, legal_action_reads=len(legal), immediate_reward_reads=len(legal),
            exact_action_vector_reads=len(legal), label_component_reads=3*len(legal), tail_reward_subtractions=len(legal))
    roots.sort(key=lambda row: row['root_id']); centers, labels, records = [], [], []
    action_roots = {action: set() for action in ACTIONS}
    pair_roots = {f'{a}|{b}': set() for a, b in combinations(ACTIONS, 2)}
    for root in roots:
        legal = root['legal_actions']; center_ids = {}
        counts.update(nonlinear_feature_cache_reads=1, nonlinear_feature_value_reads=COLUMNS*len(legal))
        for action in legal:
            center_ids[action] = len(centers)
            centers.append(dict(root_id=root['root_id'], source_id=root['source_id'], action=action,
                features=list(map(float, root['relation_features'][action]))))
            action_roots[action].add(root['root_id'])
        tails = {a: [root['action_components'][a][0]-root['immediate_rewards'][a],
            *root['action_components'][a][1:]] for a in legal}
        pairs = list(combinations(legal, 2)); weight = 1./len(pairs) if pairs else 0.
        label = dict(root_id=root['root_id'], source_id=root['source_id'], legal_actions=legal,
            label_kind='exact_enumerated_vector', pairs=[])
        for a, b in pairs:
            pair = dict(actions=[a, b], center_indices=[center_ids[a], center_ids[b]], weight=weight,
                scale=math.sqrt(weight), components=[tails[a][i]-tails[b][i] for i in range(3)])
            label['pairs'].append(deepcopy(pair)); records.append(dict(root_id=root['root_id'], source_id=root['source_id'], **pair))
            pair_roots[f'{a}|{b}'].add(root['root_id'])
            counts.update(paired_vector_labels=1, paired_component_subtractions=3,
                nonlinear_pair_rows=1, nonlinear_weight_square_roots=1)
        labels.append(label)
    X = np.asarray([center['features'] for center in centers], dtype=float)
    Y = np.asarray([[value*row['scale'] for value in row['components']] for row in records], dtype=float).reshape(-1, 3)
    D = np.zeros((len(centers), len(centers))); nonzero = []
    for first, second in combinations(range(len(centers)), 2):
        value = distance(centers[first]['features'], centers[second]['features']); D[first, second] = D[second, first] = value
        if value > 0.:
            nonzero.append(value)
    if not nonzero:
        raise ValueError('training centers require a nonzero median distance')
    median = float(np.median(nonzero)); pairs = len(centers)*(len(centers)-1)//2
    counts.update(nonlinear_design_preparations=1, nonlinear_centers=len(centers),
        nonlinear_center_matrix_cells=X.size, nonlinear_target_matrix_cells=Y.size,
        nonlinear_weighted_target_scalings=Y.size, nonlinear_distance_pairs=pairs,
        nonlinear_distance_coordinate_subtractions=COLUMNS*pairs, nonlinear_distance_coordinate_squares=COLUMNS*pairs,
        nonlinear_distance_component_sums=COLUMNS*pairs, nonlinear_distance_matrix_cells=D.size,
        nonlinear_nonzero_distance_tests=pairs, nonlinear_median_distance_values=len(nonzero), nonlinear_median_computations=1)
    sources = dict(Counter(root['source_id'] for root in roots)); pair_ids = {key: sorted(value) for key, value in pair_roots.items()}
    return dict(schema=SCHEMA+'.design', mode='NONLINEAR', life=life, basis=relation.basis_metadata(),
        feature_names=list(relation.FEATURE_NAMES), roots=roots, root_ids=[root['root_id'] for root in roots],
        source_ids=sorted(sources), source_root_counts=sources,
        action_root_ids={action: sorted(value) for action, value in action_roots.items()}, pair_root_ids=pair_ids,
        connected_components=relation.shared.connected_components(pair_ids), fit_labels=labels, pair_records=records,
        centers=centers, center_shape=list(X.shape), shape=[len(records), len(centers)],
        design_format='weighted_center_differences', median_squared_distance=median,
        X=X, Y=Y, D=D, prepare_counts=dict(counts), feature_counts={}, work=dict(counts))


def retained_design(design):
    return {key: value for key, value in design.items() if key not in ('X', 'Y', 'D')}


def kernel_and_gram(design, gamma):
    m = len(design['centers']); K = np.ones((m, m))
    for first, second in combinations(range(m), 2):
        value = math.exp(-gamma*design['D'][first, second]/design['median_squared_distance'])
        K[first, second] = K[second, first] = value
    first = np.asarray([row['center_indices'][0] for row in design['pair_records']], dtype=int)
    second = np.asarray([row['center_indices'][1] for row in design['pair_records']], dtype=int)
    scales = np.asarray([row['scale'] for row in design['pair_records']], dtype=float)
    H = K[first[:, None], first[None, :]]-K[first[:, None], second[None, :]]
    H -= K[second[:, None], first[None, :]]; H += K[second[:, None], second[None, :]]
    H *= scales[:, None]*scales[None, :]; H = (H+H.T)/2.
    B = np.zeros((len(first), m))
    for index in range(len(first)):
        B[index, first[index]] = scales[index]; B[index, second[index]] = -scales[index]
    pairs = m*(m-1)//2
    work = dict(nonlinear_kernel_matrices=1, nonlinear_kernel_exponentials=pairs, nonlinear_kernel_distance_reads=pairs,
        nonlinear_kernel_scalings=2*pairs, nonlinear_kernel_matrix_cells=K.size, nonlinear_gram_matrices=1,
        nonlinear_gram_kernel_reads=4*H.size, nonlinear_gram_signed_sums=3*H.size,
        nonlinear_gram_scale_products=H.size, nonlinear_gram_weight_scalings=H.size,
        nonlinear_gram_symmetrizations=1, nonlinear_gram_symmetrization_cells=H.size)
    return K, H, B, work


def decomposition_metadata(design, gamma, H, kernel_work, saved):
    values = np.asarray(saved['eigenvalues'], dtype=float)
    cutoff = np.finfo(float).eps*max(H.shape)*max(abs(float(value)) for value in values)
    work = Counter(kernel_work)
    work.update(nonlinear_eigh_attempts=1, nonlinear_eigh_decompositions=1, nonlinear_eigh_matrix_cells=H.size,
        nonlinear_eigh_vector_cells=H.size, nonlinear_eigh_values=len(values),
        nonlinear_target_projection_cells=design['Y'].size, nonlinear_target_projection_products=3*H.size,
        nonlinear_eigenvalue_rank_tests=len(values))
    # Spectral metadata is retained; the coefficient certificate uses no eigensolve.
    return dict(gamma=gamma, median_squared_distance=design['median_squared_distance'], shape=list(H.shape),
        eigenvalues=values.tolist(), cutoff=float(cutoff), rank=int(np.sum(values > cutoff)),
        minimum_eigenvalue=float(values[0]), work=dict(work))


def fit_certificate(design, H, B, lambda_value, saved, audit_work):
    alpha, coefficients = certify_coefficients(H, design['Y'], B, len(design['roots']), lambda_value,
        saved['dual_coefficients'], saved['coefficients'], audit_work)
    prediction = H@alpha; residual = prediction-design['Y']; component_losses = np.sum(residual*residual, axis=0)
    energy = float(np.sum(alpha*prediction)); penalty = lambda_value*energy
    residuals = [dict(**row, predicted_components=(prediction[index]/row['scale']).tolist(),
        residual_components=(residual[index]/row['scale']).tolist(),
        weighted_component_losses=(residual[index]*residual[index]).tolist(),
        weighted_loss=float(np.sum(residual[index]*residual[index]))) for index, row in enumerate(design['pair_records'])]
    p, m = len(design['pair_records']), len(design['centers'])
    counts = dict(nonlinear_filter_attempts=1, nonlinear_coefficient_filters=1, nonlinear_predictors_fitted=1, new_predictors_fitted=1,
        nonlinear_eigenvalue_shifts=p, nonlinear_projected_component_divisions=3*p,
        nonlinear_dual_reconstruction_products=3*p*p, nonlinear_dual_coefficient_cells=alpha.size,
        nonlinear_center_coefficient_cells=3*m, nonlinear_center_coefficient_scalings=3*p,
        nonlinear_center_coefficient_accumulations=6*p, nonlinear_fit_prediction_products=3*p*p,
        nonlinear_fit_residual_subtractions=3*p, nonlinear_fit_residual_squares=3*p,
        nonlinear_rkhs_energy_products=3*p, nonlinear_penalty_scalings=1, nonlinear_residual_export_divisions=6*p)
    loss = float(np.sum(component_losses))
    return dict(coefficients=coefficients.tolist(), dual_coefficients=alpha.tolist(), component_losses=component_losses.tolist(),
        loss=loss, root_mean_loss=loss/len(design['roots']), rkhs_energy=energy, penalty=penalty,
        objective=loss/len(design['roots'])+penalty, residuals=residuals, counts=counts)


def model_from_fit(design, metadata, fitted, lambda_value, source_folds):
    counts = Counter(design['work'])+Counter(metadata['work'])+Counter(fitted['counts'])
    return dict(schema=SCHEMA+'.model', mode='NONLINEAR', life=design['life'], query='risk1',
        native_teacher_query=native_exact.QUERY, horizon=native_exact.HORIZON, label_kind='exact_enumerated_vector',
        feature_names=list(relation.FEATURE_NAMES), basis=relation.basis_metadata(), design_format=design['design_format'],
        centers=deepcopy(design['centers']), coefficients=fitted['coefficients'], dual_coefficients=fitted['dual_coefficients'],
        gamma=metadata['gamma'], median_squared_distance=design['median_squared_distance'],
        eigenvalues=metadata['eigenvalues'], rank=metadata['rank'], eigenvalue_cutoff=metadata['cutoff'],
        minimum_eigenvalue=metadata['minimum_eigenvalue'], component_losses=fitted['component_losses'], loss=fitted['loss'],
        root_mean_loss=fitted['root_mean_loss'], rkhs_energy=fitted['rkhs_energy'], penalty=fitted['penalty'], objective=fitted['objective'],
        constants=dict(min_action_roots=4, epsilon=EPS, columns=COLUMNS, intercept=False, gamma=metadata['gamma'],
            lambda_value=lambda_value, bandwidth_normalization='TRAIN_CENTER_NONZERO_DISTANCE_MEDIAN',
            penalty_normalization='ROOT_MEAN', norm='RBF_RKHS'), root_ids=list(design['root_ids']), source_ids=list(design['source_ids']),
        source_root_counts=deepcopy(design['source_root_counts']), source_folds=deepcopy(source_folds),
        action_root_ids=deepcopy(design['action_root_ids']), pair_root_ids=deepcopy(design['pair_root_ids']),
        connected_components=deepcopy(design['connected_components']), fit_labels=deepcopy(design['fit_labels']),
        fit_residuals=fitted['residuals'], training_outcomes=deepcopy(design['roots']), fit_counts=dict(counts), feature_counts={})


def choose_action(payload, root, counts=None):
    legal = [action for action in ACTIONS if action in root['legal_actions']]
    features = {action: list(map(float, root['relation_features'][action])) for action in legal}
    work = Counter(nonlinear_decisions=1, nonlinear_legal_action_reads=len(legal),
        nonlinear_feature_cache_reads=1, nonlinear_feature_value_reads=COLUMNS*len(legal))
    action_counts = {action: len(payload['action_root_ids'][action]) for action in legal}
    pair_counts = {f'{a}|{b}': len(payload['pair_root_ids'][f'{a}|{b}']) for a, b in combinations(legal, 2)}
    connected = deepcopy(payload['connected_components']); components = {a: i for i, group in enumerate(connected) for a in group}
    work.update(nonlinear_action_support_lookups=len(legal), nonlinear_pair_support_lookups=len(pair_counts),
        nonlinear_component_membership_lookups=len(legal))
    if len(legal) == 1:
        selected, fallback, reason = legal[0], False, 'single_legal_action'
    elif any(value < 4 for value in action_counts.values()):
        selected, fallback, reason = root['fallback_action'], True, 'insufficient_action_support'
    elif len({components[action] for action in legal}) != 1:
        selected, fallback, reason = root['fallback_action'], True, 'disconnected_required_actions'
    else:
        selected, fallback, reason = None, False, 'selected'
    predicted = {}
    for action in legal:
        kernels = [math.exp(-payload['gamma']*distance(features[action], center['features'])/payload['median_squared_distance'])
            for center in payload['centers']]
        vector = [sum(kernels[index]*payload['coefficients'][index][k] for index in range(len(kernels))) for k in range(3)]
        vector[0] += root['immediate_rewards'][action]; predicted[action] = vector; n = len(kernels)
        work.update(nonlinear_prediction_distance_pairs=n, nonlinear_prediction_feature_reads=2*COLUMNS*n,
            nonlinear_prediction_distance_subtractions=COLUMNS*n, nonlinear_prediction_distance_squares=COLUMNS*n,
            nonlinear_prediction_distance_sums=COLUMNS*n, nonlinear_prediction_kernel_exponentials=n,
            nonlinear_prediction_kernel_scalings=2*n, nonlinear_prediction_products=3*n,
            nonlinear_prediction_coefficient_reads=3*n, nonlinear_prediction_component_evaluations=3,
            nonlinear_immediate_reward_reads=1, nonlinear_reward_additions=1)
    pairs = {}
    for a, b in combinations(legal, 2):
        if components[a] == components[b]:
            pairs[f'{a}|{b}'] = [predicted[a][k]-predicted[b][k] for k in range(3)]
            work['nonlinear_predicted_pair_subtractions'] += 3
    if selected is None:
        best = None
        for action in legal:
            value = relation.exact.utility(predicted[action]); work['nonlinear_utility_evaluations'] += 1
            if best is None or value > best+EPS:
                selected, best = action, value
    result = dict(canonical_action=selected, actual_action=root['action_map'][selected], fallback=fallback, leaf=0, reason=reason,
        predicted_components=predicted, predicted_pairs=pairs, support=dict(action_root_counts=action_counts,
            pair_root_counts=pair_counts, connected_components=connected, required_actions=legal, complete=not fallback),
        work=dict(work), feature_work={})
    if counts is not None:
        counts.update(work)
    return result


def score_heldout(model, roots):
    counts, groups, choices = Counter(), {}, []
    for root in sorted(roots, key=lambda row: row['root_id']):
        decision = choose_action(model, observable(root), counts)
        vector = list(map(float, root['action_components'][decision['canonical_action']])); value = relation.exact.utility(vector)
        groups.setdefault(root['source_id'], []).append(vector)
        choices.append(dict(root_id=root['root_id'], source_id=root['source_id'], decision=decision, components=vector, utility=value))
        counts.update(heldout_action_vector_reads=1, heldout_component_reads=3, heldout_utility_evaluations=1)
    records = []
    for source in sorted(groups):
        mean = [sum(vector[k] for vector in groups[source])/len(groups[source]) for k in range(3)]
        records.append(dict(source_id=source, roots=len(groups[source]), components=mean, utility=relation.exact.utility(mean)))
        counts.update(heldout_group_component_means=3, heldout_group_utility_evaluations=1)
    return records, choices, dict(counts)


def fit_model(examples, saved_selection, saved_model, life=0):
    sources = sorted({root['source_id'] for root in examples if root['life'] == life}); folds = [sources[::2], sources[1::2]]
    costs = Counter(source_fold_assignments=len(sources), nonlinear_candidates=len(GAMMAS)*len(LAMBDAS)); audit_work = Counter()
    designs, heldouts, fold_records = [], [], []
    for fold, heldout_sources in enumerate(folds):
        train_sources = [source for source in sources if source not in heldout_sources]
        design = prepare_design([root for root in examples if root['life'] == life and root['source_id'] in train_sources], life)
        costs.update(design['work']); designs.append(design)
        heldouts.append([root for root in examples if root['life'] == life and root['source_id'] in heldout_sources])
        fold_records.append(dict(fold=fold, train_sources=train_sources, heldout_sources=heldout_sources,
            design=retained_design(design), decompositions=[]))
    candidates, selected_gamma, selected_lambda, best = [], GAMMAS[0], LAMBDAS[0], None
    for gamma_index, gamma in enumerate(GAMMAS):
        grams, incidence, metadata = [], [], []
        for fold, design in enumerate(designs):
            _, H, B, kernel_work = kernel_and_gram(design, gamma)
            meta = decomposition_metadata(design, gamma, H, kernel_work,
                saved_selection['folds'][fold]['decompositions'][gamma_index])
            grams.append(H); incidence.append(B); metadata.append(meta)
            costs.update(meta['work']); fold_records[fold]['decompositions'].append(meta)
        for lambda_index, lambda_value in enumerate(LAMBDAS):
            results, groups = [], []
            saved_candidate = saved_selection['candidates'][gamma_index*len(LAMBDAS)+lambda_index]
            for fold, design in enumerate(designs):
                fitted = fit_certificate(design, grams[fold], incidence[fold], lambda_value,
                    saved_candidate['fold_results'][fold], audit_work); costs.update(fitted['counts'])
                model = model_from_fit(design, metadata[fold], fitted, lambda_value, folds)
                records, choices, prediction_counts = score_heldout(model, heldouts[fold]); costs.update(prediction_counts); groups.extend(records)
                results.append(dict(fold=fold, coefficients=fitted['coefficients'], dual_coefficients=fitted['dual_coefficients'],
                    component_losses=fitted['component_losses'], loss=fitted['loss'], root_mean_loss=fitted['root_mean_loss'],
                    rkhs_energy=fitted['rkhs_energy'], penalty=fitted['penalty'], objective=fitted['objective'],
                    group_records=records, choices=choices, prediction_counts=prediction_counts, coefficient_counts=fitted['counts']))
            groups.sort(key=lambda row: row['source_id']); value = sum(row['utility'] for row in groups)/len(sources)
            candidates.append(dict(gamma=gamma, lambda_value=lambda_value, utility=value, group_records=groups, fold_results=results))
            costs.update(nonlinear_group_mean_reads=len(sources), nonlinear_score_comparisons=1)
            if best is None or value > best+EPS:
                selected_gamma, selected_lambda, best = gamma, lambda_value, value
    final = prepare_design(examples, life); costs.update(final['work'])
    _, H, B, kernel_work = kernel_and_gram(final, selected_gamma)
    meta = decomposition_metadata(final, selected_gamma, H, kernel_work, saved_model); costs.update(meta['work'])
    fitted = fit_certificate(final, H, B, selected_lambda, saved_model, audit_work); costs.update(fitted['counts'])
    model = model_from_fit(final, meta, fitted, selected_lambda, folds); costs['new_predictors_fitted'] = costs['nonlinear_predictors_fitted']
    selection = dict(schema=SCHEMA+'.selection', mode='NONLINEAR', life=life, basis=relation.basis_metadata(), gammas=list(GAMMAS),
        lambdas=list(LAMBDAS), source_folds=folds, folds=fold_records, candidates=candidates,
        selected_gamma=selected_gamma, selected_lambda=selected_lambda, selected_utility=best, costs=dict(costs))
    return dict(model=model, selection=selection, costs=dict(costs), cache_counts={}), dict(audit_work)


def source_diagnostics(roots, model):
    records, work = [], Counter()
    for root in sorted(roots, key=lambda row: row['root_id']):
        decision = choose_action(model, observable(root), work); legal = [a for a in ACTIONS if a in root['legal_actions']]
        vectors = root['action_components']; values = {a: relation.exact.utility(vectors[a]) for a in legal}
        maximum = max(values.values()); oracle = next(a for a in legal if values[a] >= maximum-EPS)
        action = decision['canonical_action']; regret = maximum-values[action]
        records.append(dict(root_id=root['root_id'], source_id=root['source_id'], decision=decision,
            action=action, components=list(vectors[action]), utility=values[action], oracle_action=oracle,
            oracle_components=list(vectors[oracle]), oracle_utility=maximum, regret=regret, positive_regret=regret > EPS))
        work.update(source_observable_root_preparations=1, source_complete_component_reads=3*len(legal),
            source_action_utility_evaluations=len(legal), source_selected_component_reads=3,
            source_oracle_component_reads=3, source_regret_subtractions=1,
            source_oracle_action_comparisons=legal.index(oracle)+1, source_diagnostic_root_records=1)
    n = len(records)
    metrics = dict(roots=n, components=[math.fsum(row['components'][k] for row in records)/n for k in range(3)],
        utility=math.fsum(row['utility'] for row in records)/n,
        oracle_components=[math.fsum(row['oracle_components'][k] for row in records)/n for k in range(3)],
        oracle_utility=math.fsum(row['oracle_utility'] for row in records)/n,
        regret_mean=math.fsum(row['regret'] for row in records)/n, positive_regret_roots=sum(row['positive_regret'] for row in records),
        fallback_roots=sum(row['decision']['fallback'] for row in records))
    work.update(source_summary_component_reads=6*n, source_summary_scalar_reads=3*n, source_summary_flag_reads=2*n)
    return dict(root_records=records, metrics=metrics, work=dict(work))


def freeze_choices(roots, models):
    choices, work = {name: [] for name in (*MODEL_NAMES, 'FALLBACK')}, Counter()
    for root in roots:
        observed = observable(root)
        for name in MODEL_NAMES:
            chooser = choose_action if name == 'NONLINEAR' else relation.choose_action if name == 'RELATION' else (
                relation.dense.choose_action if name in ('LINEAR', 'INTERACT') else relation.shared.choose_action if name in
                ('SHARED', 'OLD_SHARED') else relation.exact.choose_action if name == 'ONE' else relation.layout.choose_action)
            decision = chooser(models[name], observed); work.update(decision['work']); work.update(decision.get('feature_work', {}))
            work['frozen_model_choices'] += 1
            choices[name].append(dict(root_id=root['root_id'], mode=name, canonical_action=decision['canonical_action'],
                actual_action=decision['actual_action'], fallback=decision['fallback'], decision=decision))
        action = root['fallback_action']; work['frozen_fallback_choices'] += 1
        choices['FALLBACK'].append(dict(root_id=root['root_id'], mode='FALLBACK', canonical_action=action,
            actual_action=root['action_map'][action], fallback=False, decision=dict(reason='observable_immediate_reward',
                work=dict(frozen_fallback_choices=1))))
    return choices, dict(work)


def summarize(roots, labels, choices, selection, model, source):
    labels_by_id = {row['root_id']: row['action_components'] for row in labels}
    choices_by_id = {name: {row['root_id']: row for row in records} for name, records in choices.items()}
    names = (*MODEL_NAMES, 'FALLBACK', 'ORACLE'); records = []
    for root in roots['TARGET']:
        vectors = labels_by_id[root['root_id']]; oracle = root['legal_actions'][0]
        for action in root['legal_actions'][1:]:
            if relation.exact.utility(vectors[action]) > relation.exact.utility(vectors[oracle])+EPS:
                oracle = action
        outcomes = {}
        for name in names:
            choice = None if name == 'ORACLE' else choices_by_id[name][root['root_id']]
            action = oracle if choice is None else choice['canonical_action']; vector = list(vectors[action])
            outcomes[name] = dict(action=action, components=vector, utility=relation.exact.utility(vector),
                regret=relation.exact.utility(vectors[oracle])-relation.exact.utility(vector), fallback=False if choice is None else choice['fallback'])
        records.append(dict(root_id=root['root_id'], replica=root['replica'], stratum=root['stratum'], models=outcomes))
    def means(rows):
        result = {}
        for name in names:
            vector = relation.exact.mean_vectors([row['models'][name]['components'] for row in rows])
            result[name] = dict(components=vector, utility=relation.exact.utility(vector),
                positive_regret_roots=sum(row['models'][name]['regret'] > EPS for row in rows),
                fallback_roots=sum(row['models'][name]['fallback'] for row in rows))
        return result
    def contrasts(rows):
        selected = [dict(root_id=row['root_id'], models={'NONLINEAR': row['models']['NONLINEAR']}) for row in rows]
        return {'NONLINEAR_MINUS_'+name: relation.coverage.coverage_effect(selected,
            [dict(root_id=row['root_id'], models={'NONLINEAR': row['models'][name]}) for row in rows], 'NONLINEAR') for name in CONTROLS}
    models, effects = means(records), contrasts(records)
    replicas = [dict(replica=replica, roots=len(rows), models=means(rows), comparisons=contrasts(rows))
        for replica in sorted({row['replica'] for row in records})
        for rows in [[row for row in records if row['replica'] == replica]]]
    headroom = models['ORACLE']['utility']-models['ONE']['utility']
    return dict(schema=SCHEMA+'.summary', complete=True, roots=len(records),
        SOURCE=dict(roots=len(roots['SOURCE']), design_groups=len({row['source_id'] for row in roots['SOURCE']}),
            selected_gamma=selection['selected_gamma'], selected_lambda=selection['selected_lambda'],
            source_heldout_utility=selection['selected_utility'], feature_columns=COLUMNS, source_rank=model['rank'],
            median_squared_distance=model['median_squared_distance'], source_root_mean_loss=model['root_mean_loss'], actual=source['metrics'],
            source_selection=[dict(gamma=row['gamma'], lambda_value=row['lambda_value'], utility=row['utility']) for row in selection['candidates']]),
        models=models, comparisons=effects, replicas=replicas, root_records=records,
        oracle_minus_one=headroom, oracle_minus_nonlinear=models['ORACLE']['utility']-models['NONLINEAR']['utility'],
        headroom_closed_fraction=effects['NONLINEAR_MINUS_ONE']['utility']/headroom if headroom > EPS else None,
        whole_cohort_positive_vs_linear_relation_old_shared=all(effects['NONLINEAR_MINUS_'+name]['utility'] > EPS for name in ('LINEAR', 'RELATION', 'OLD_SHARED')),
        all_replicas_positive_vs_linear_relation_old_shared=all(row['comparisons']['NONLINEAR_MINUS_'+name]['utility'] > EPS
            for row in replicas for name in ('LINEAR', 'RELATION', 'OLD_SHARED')),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=31)


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, io, binding_work = [], Counter(), Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); io.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    names = ('v191_stage_checks.json', 'v191_run.json', 'v191_roots.json', 'relation_model.json',
        'expanded_models.json', 'baseline_models.json', 'learned_rule.json', 'dense_models.json')
    check('eight_frozen_SOURCE_and_control_inputs', [(row['saved_ref'], row['phase']) for row in inputs] ==
        [(f'inputs/inherited/{name}', 'protocol_frozen') for name in names])
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        io.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        check('retained_input:'+row['saved_ref'], saved == original and len(saved) == row['bytes'])
    stage, inherited_run = read('inputs/inherited/v191_stage_checks.json'), read('inputs/inherited/v191_run.json')
    check('settled_V191_complete', stage['valid'] and inherited_run['status'] == 'complete')
    source = read('inputs/inherited/v191_roots.json')['SOURCE']
    check('unchanged_SOURCE143_36_groups_existing_relation_cache', len(source) == 143 and len({row['source_id'] for row in source}) == 36 and
        all(len(root['relation_features'][a]) == COLUMNS for root in source for a in root['legal_actions']))
    saved_selection, saved_model = read('selection.json'), read('model.json')
    fitted, solver_work = fit_model(source, saved_selection, saved_model)
    selection, model, counts = fitted['selection'], fitted['model'], fitted['costs']
    check('31_direct_shifted_system_certificates_before_saved_array_EPS_scoring',
        solver_work['independent_shifted_system_solves'] == solver_work['independent_predictors_checked'] ==
        solver_work['independent_predictors_passed'] == 31)
    check('SOURCE_only_train_median_two_folds_15_candidates_and_actual_utility_selection', relation.same(saved_selection, selection))
    check('certified_saved_dual_center_arrays_full_loss_penalty_and_metadata', relation.same(saved_model, model))
    check('three_designs_seven_eigh_31_filters_and_paid_learning',
        counts['nonlinear_design_preparations'] == 3 and counts['nonlinear_eigh_decompositions'] == 7 and
        counts['nonlinear_predictors_fitted'] == counts['new_predictors_fitted'] == 31 and
        run['costs']['learning']['counts'] == counts)
    diagnostic = source_diagnostics(source, model)
    check('actual_frozen_SOURCE_RFS_choices_and_regrets', relation.same(read('source_diagnostics.json'), diagnostic))
    check('paid_actual_SOURCE_evaluation', run['costs']['source_evaluation']['counts'] == diagnostic['work'])
    cases = cohort_cases(); target, observation_work = observe_roots(cases)
    feature_work = relation.coverage.cache_roots(target); relation_work = relation.cache_roots(target)
    roots = dict(SOURCE=source, TARGET=target)
    check('96_fresh_seeded_H3_cases_no_replacement', read('target_cases.json') == cases)
    check('unchanged_SOURCE_and_FRESH_observable_geometry_relation_caches', relation.same(read('roots.json'), roots))
    observed = run['costs']['observations']
    check('once_fresh_observation_geometry_and_relation_costs', observed['counts'] == observation_work and
        observed['feature_counts'] == feature_work and observed['relation_counts'] == relation_work)
    expanded = read('inputs/inherited/expanded_models.json'); old = read('inputs/inherited/baseline_models.json')
    dense = read('inputs/inherited/dense_models.json'); old_relation = read('inputs/inherited/relation_model.json')
    models = dict(expanded, **dense, NONLINEAR=model, RELATION=old_relation, OLD_SHARED=old['SHARED'], ONE=old['ONE'])
    choices, choice_counts = freeze_choices(target, models)
    check('SOURCE_selected_kernel_and_all_control_choices_before_labels', relation.same(read('choices.json'), choices))
    check('paid_full_RFS_frozen_decisions', run['costs']['choices']['counts'] == choice_counts)
    native, label_costs = read('native_labels.json'), read('label_costs.json'); ids = [root['root_id'] for root in target]
    check('complete_native_label_and_cost_rosters', [row['root_id'] for row in native] == ids and
        [row['root_id'] for row in label_costs] == ids)
    labels, label_work = [], Counter()
    for root, raw, cost_row in zip(target, native, label_costs, strict=True):
        teacher = read(f"teacher_policy/{root['root_id']}.json")
        check('settled_native_fraction_teacher_binding:'+root['root_id'], relation.coverage.native_binding(root, raw, teacher))
        binding_work.update(new_label_roots_bound=1, teacher_root_records_inspected=len(teacher),
            exact_component_coordinates_bound=3*len(root['legal_actions']))
        provenance = dict(kind='new_exact_V69_FULL', teacher_query='goal_1_risk_1', teacher_policy_ref='teacher_policy/'+root['root_id']+'.json')
        labels.append(relation.exact.canonical_labels(root, raw, provenance))
        costs = cost_row['costs']; construction, compilation, export = costs['construction'], costs['compilation'], costs['teacher_export']; n = len(teacher)
        accounting = construction['concrete_states'] <= 200000 and construction['concrete_active_states'] == construction['active_states'] == n
        accounting = accounting and compilation['model_payload_calls'] == compilation['model_reload_calls'] == 1
        accounting = accounting and compilation['payload_cells'] == construction['registered_states'] == costs['label_evaluation']['kernel_cells_read']
        accounting = accounting and compilation['payload_rows'] == costs['label_evaluation']['kernel_rows_read'] and compilation['payload_outcomes'] == costs['label_evaluation']['kernel_outcomes_read']
        accounting = accounting and costs['label_evaluation']['root_labels_emitted'] == 1
        expected_export = dict(teacher_encoding_records_read=construction['concrete_states'], teacher_policy_records=n,
            teacher_policy_action_reads=n, teacher_policy_tile_reads=16*n)
        check('settled_acquisition_caps_and_export_costs:'+root['root_id'], accounting and export == expected_export)
        for kind in ('construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation'):
            label_work.update({kind+'.'+key: value for key, value in costs[kind].items() if type(value) is int})
    check('all_new_canonical_RFS_vectors_and_fraction_metadata', relation.same(read('labels.json'), labels))
    summary = summarize(roots, labels, choices, selection, model, diagnostic)
    check('actual_RFS_controls_regret_replicas_and_gain_concentration', relation.same(read('summary.json'), summary))
    phases = ('protocol_frozen', 'source_selection', 'models_frozen', 'target_roots', 'target_choices_frozen', 'target_labels', 'complete')
    check('SOURCE_selection_and_frozen_all_choices_before_target_labels',
        [(row['phase'], row['input_reads']) for row in run['phase_history']] == [(phase, 0 if i == 0 else 8) for i, phase in enumerate(phases)])
    check('all_paid_input_and_label_counts', run['costs']['input_counts'] == dict(json_read_operations=8,
        input_bytes_read=sum(row['bytes'] for row in inputs), input_bytes_retained=sum(row['bytes'] for row in inputs)) and
        run['costs']['labels']['counts'] == dict(label_work))
    accounting = all(run[key] == 96 for key in ('new_boards_generated', 'new_reference_kernel_attempts',
        'new_reference_kernels', 'new_teacher_plans', 'new_exact_label_roots', 'completed_roots'))
    accounting = accounting and run['new_learning_attempts'] == 1 and run['new_predictors_fitted'] == 31 and run['resource_cap_per_board'] == 200000
    accounting = accounting and all(run[key] == 0 for key in ('new_environment_samples', 'new_source_games', 'new_native_weight_updates'))
    check('one_SOURCE_selection_31_predictors_96_labels_no_sampling', accounting)
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and summary['complete']
    return dict(schema=SCHEMA+'.analysis', valid=valid, complete=complete, primary_complete=complete, checks=checks,
        passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=summary,
        costs=dict(independent_eigen_solves=0, independent_svd_solves=0, spectral_metadata='retained_decomposition_metadata',
            new_environment_samples=0, physical_branches_replayed=0, new_kernels_reintegrated=0, old_models_refitted=0,
            independent_input_counts=dict(io), independent_coefficient_solver_counts=solver_work, reconstructed_learning_counts=counts,
            independent_SOURCE_cache_derivations=0, independent_source_evaluation_counts=diagnostic['work'],
            independent_observation_counts=observation_work, independent_feature_counts=feature_work,
            independent_relation_counts=relation_work, independent_choice_counts=choice_counts,
            independent_new_label_binding_counts=dict(binding_work), reconstructed_acquisition_counts=dict(label_work),
            original_run_costs=run['costs'], inherited_cost_refs=run['inherited_cost_refs'], test_refs=run['test_refs'], seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    args = parser.parse_args(); result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'])))


if __name__ == '__main__':
    main()
