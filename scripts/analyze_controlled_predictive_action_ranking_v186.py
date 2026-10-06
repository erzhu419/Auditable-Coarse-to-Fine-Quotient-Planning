"""Independent SOURCE ranking design, nonnegative dual certificate and effects."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from itertools import combinations
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter
import numpy as np
from scipy.optimize import nnls
from scipy.sparse import csr_matrix

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(PROJECT/'src'))
from scripts import analyze_controlled_predictive_source_coverage_v185 as coverage

layout, shared, exact = coverage.layout, coverage.shared, coverage.exact
ACTIONS, EPS = exact.ACTIONS, exact.EPS
LAMBDA, GRADIENT_TOLERANCE = .1, 1e-7
OPTIMIZER_OPTIONS = dict(maxiter=1000, maxls=50, ftol=1e-15, gtol=1e-10)
MODEL_NAMES = ('RANK', 'RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE')
OUTPUT = PROJECT/'reports/controlled_predictive_action_ranking_v186'


def same(actual, expected):
    return coverage.same(actual, expected)


def prepare_ranking(examples, reference):
    work, roots = Counter(), []; indexed = layout.vocabulary_index(reference['vocabulary'], work)
    for original in examples:
        work['ranking_examples_examined'] += 1
        if original['life'] != reference['life']:
            work['ranking_other_life_excluded'] += 1; continue
        legal = [action for action in ACTIONS if action in original['legal_actions']]
        roots.append(dict(root_id=original['root_id'], source_id=original['source_id'], legal_actions=legal,
            immediate_rewards={action: float(original['immediate_rewards'][action]) for action in legal},
            action_components={action: list(map(float, original['action_components'][action])) for action in legal}, layout_features=original['layout_features']))
        work.update(ranking_root_labels_read=1, ranking_legal_action_reads=len(legal), ranking_full_component_reads=3*len(legal), ranking_immediate_reward_reads=len(legal))
    roots.sort(key=lambda row: row['root_id'])
    if len({row['root_id'] for row in roots}) != len(roots) or [row['root_id'] for row in roots] != sorted(reference['root_ids']):
        raise ValueError('Ranking SOURCE identities must match the fixed reference')
    records, rows, values, row_indices, column_indices = [], [], [], [], []
    for root in roots:
        legal = root['legal_actions']; encoded = {action: layout.encode_action(root['layout_features'][action], indexed, work)[0] for action in legal}
        utilities = {action: exact.utility(root['action_components'][action]) for action in legal}
        best = legal[0]
        for action in legal[1:]:
            if utilities[action] > utilities[best]+EPS:
                best = action
        ties = [action for action in legal if abs(utilities[best]-utilities[action]) <= EPS]
        losers = [action for action in legal if utilities[best]-utilities[action] > EPS]; root_rows = []
        for bad in losers:
            columns = sorted(set(encoded[best]) | set(encoded[bad]))
            sparse = [[column, encoded[best].get(column, 0.)-encoded[bad].get(column, 0.)] for column in columns]
            sparse = [[column, value] for column, value in sparse if value != 0.]
            utility_gap = utilities[best]-utilities[bad]; reward_gap = root['immediate_rewards'][best]-root['immediate_rewards'][bad]
            index = len(rows); root_rows.append(index)
            rows.append(dict(root_id=root['root_id'], source_id=root['source_id'], best_action=best, bad_action=bad,
                utility_gap=utility_gap, immediate_reward_gap=reward_gap, target=utility_gap-reward_gap, weight=1./len(losers), design=sparse))
            for column, value in sparse:
                row_indices.append(index); column_indices.append(column); values.append(value)
            work.update(ranking_loser_pairs=1, ranking_design_value_reads=2*len(columns), ranking_design_subtractions=len(columns),
                ranking_sparse_design_entries=len(sparse), ranking_utility_gap_subtractions=1, ranking_reward_gap_subtractions=1, ranking_target_subtractions=1)
        records.append(dict(root_id=root['root_id'], source_id=root['source_id'], legal_actions=legal,
            action_components=deepcopy(root['action_components']), utilities=utilities, immediate_rewards=dict(root['immediate_rewards']),
            best_action=best, tied_actions=ties, loser_actions=losers, rows=root_rows))
        work.update(ranking_utility_evaluations=len(legal), ranking_best_comparisons=max(0, len(legal)-1), ranking_tie_tests=len(legal), ranking_loser_tests=len(legal), ranking_roots_prepared=1)
    matrix = csr_matrix((values, (row_indices, column_indices)), shape=(len(rows), 6+len(reference['vocabulary'])), dtype=float)
    work.update(ranking_csr_matrices=1, ranking_csr_stored_values=matrix.nnz)
    return dict(schema='acfqp.action_ranking.v186.design', life=reference['life'], vocabulary=deepcopy(reference['vocabulary']),
        root_count=len(roots), root_ids=[row['root_id'] for row in roots], root_records=records, rows=rows,
        source_ids=sorted({row['source_id'] for row in roots}), action_root_ids=deepcopy(reference['action_root_ids']),
        pair_root_ids=deepcopy(reference['pair_root_ids']), connected_components=deepcopy(reference['connected_components']),
        shape=list(matrix.shape), D=matrix, targets=np.asarray([row['target'] for row in rows]), weights=np.asarray([row['weight'] for row in rows]),
        lambda_value=LAMBDA, work=dict(work))


def loss_gradient(beta, design, work=None):
    beta = np.asarray(beta, dtype=float); residual = design['targets']-design['D'].dot(beta)
    hinge = np.maximum(residual, 0.); weighted = design['weights']*hinge
    objective = float(np.dot(weighted, hinge)/design['root_count']+LAMBDA*np.dot(beta, beta))
    gradient = 2*LAMBDA*beta-2*np.asarray(design['D'].T.dot(weighted)).ravel()/design['root_count']
    if work is not None:
        work.update(independent_loss_gradient_calls=1, independent_sparse_value_products=2*design['D'].nnz,
            independent_hinge_values=len(hinge), independent_gradient_values=len(beta))
    return objective, gradient


def dual_certificate(design, beta):
    """Solve only the nonnegative dual, independently of the primal optimizer."""
    started = perf_counter(); work = Counter(); n = design['root_count']; m = len(design['rows'])
    gram = (design['D']@design['D'].T).toarray()
    hessian = gram/(2*LAMBDA)+np.diag(n/(2*design['weights']))
    work.update(dual_row_gram_matrices=1, dual_row_gram_cells=m*m, dual_hessian_diagonal_entries=m)
    factor = np.linalg.cholesky(hessian); transformed = np.linalg.solve(factor, design['targets'])
    work.update(dual_cholesky_decompositions=1, dual_cholesky_cells=m*m, dual_triangular_solves=1, dual_rhs_values=m, dual_nnls_attempts=1)
    tick = perf_counter(); alpha, residual_norm = nnls(factor.T, transformed, maxiter=10000)
    nnls_seconds = perf_counter()-tick; work.update(dual_nnls_returns=1, dual_nnls_matrix_cells=m*m, dual_nnls_target_values=m)
    beta_dual = np.asarray(design['D'].T.dot(alpha)).ravel()/(2*LAMBDA)
    objective, gradient = loss_gradient(beta, design, work); stationarity = float(np.max(np.abs(gradient)))
    dual_primal_objective, dual_gradient = loss_gradient(beta_dual, design, work)
    lower = float(np.dot(design['targets'], alpha)-n/4*np.sum(alpha*alpha/design['weights'])-LAMBDA*np.dot(beta_dual, beta_dual))
    gap = objective-lower; kkt = hessian@alpha-design['targets']
    violation = np.where(alpha > 0, np.abs(kkt), np.maximum(-kkt, 0.)); kkt_inf = float(np.max(violation))
    coefficient_l2 = float(np.linalg.norm(np.asarray(beta)-beta_dual))
    gap_distance_bound = math.sqrt(max(gap, 0.)/LAMBDA)
    gradient_distance_bound = (float(np.linalg.norm(gradient))+float(np.linalg.norm(dual_gradient)))/(2*LAMBDA)
    bound = max(gap_distance_bound, gradient_distance_bound)+1e-8
    work.update(dual_nonnegative_multiplier_checks=m, dual_kkt_values=m, dual_coefficient_values=len(beta_dual),
        dual_gradient_norm_values=2*len(beta_dual), dual_coefficient_distance_values=len(beta_dual), dual_gap_evaluations=1)
    return dict(schema='acfqp.action_ranking.v186.dual_certificate', alpha=alpha.tolist(), beta_dual=beta_dual.tolist(),
        primal_objective=objective, dual_lower_bound=lower, primal_dual_gap=gap, primal_gradient=gradient.tolist(),
        primal_gradient_inf=stationarity, dual_beta_primal_objective=dual_primal_objective, dual_beta_gradient=dual_gradient.tolist(),
        gap_coefficient_distance_bound=gap_distance_bound, gradient_coefficient_distance_bound=gradient_distance_bound,
        kkt_residual=kkt.tolist(), dual_kkt_inf=kkt_inf,
        coefficient_l2_difference=coefficient_l2, coefficient_l2_bound=bound, nnls_residual_norm=float(residual_norm),
        accepted=bool(np.all(alpha >= 0) and stationarity <= GRADIENT_TOLERANCE and -1e-10 <= gap <= 1e-9 and kkt_inf <= 1e-7 and coefficient_l2 <= bound),
        costs=dict(work), times=dict(nnls=nnls_seconds, total=perf_counter()-started))


def choose_action(payload, root, counts=None):
    legal = [action for action in ACTIONS if action in root['legal_actions']]
    feature_work, work = Counter(), Counter(ranking_decisions=1, ranking_legal_action_reads=len(legal))
    features = layout.action_features_from_root(root, feature_work); indexed = layout.vocabulary_index(payload['vocabulary'], work)
    action_counts = {action: len(payload['action_root_ids'][action]) for action in legal}
    pair_counts = {f'{a}|{b}': len(payload['pair_root_ids'][f'{a}|{b}']) for a, b in combinations(legal, 2)}
    connected = deepcopy(payload['connected_components']); component = {action: index for index, group in enumerate(connected) for action in group}
    work.update(ranking_action_support_lookups=len(legal), ranking_pair_support_lookups=len(pair_counts), ranking_component_membership_lookups=len(legal))
    if len(legal) == 1:
        selected, fallback, reason = legal[0], False, 'single_legal_action'
    elif any(value < 4 for value in action_counts.values()):
        selected, fallback, reason = root['fallback_action'], True, 'insufficient_action_support'
    elif len({component[action] for action in legal}) != 1:
        selected, fallback, reason = root['fallback_action'], True, 'disconnected_required_actions'
    else:
        selected, fallback, reason = None, False, 'selected'
    predicted, coverage_rows = {}, {}
    for action in legal:
        encoded, coverage_rows[action] = layout.encode_action(features[action], indexed, work)
        predicted[action] = root['immediate_rewards'][action]+sum(value*payload['coefficients'][column] for column, value in encoded.items())
        work.update(ranking_prediction_coefficient_reads=len(encoded), ranking_prediction_value_reads=len(encoded), ranking_immediate_reward_reads=1, ranking_reward_additions=1)
    pairs = {f'{a}|{b}': predicted[a]-predicted[b] for a, b in combinations(legal, 2) if component[a] == component[b]}
    if pairs:
        work['ranking_predicted_pair_subtractions'] += len(pairs)
    if selected is None:
        best = None
        for action in legal:
            work['ranking_utility_comparisons'] += 1
            if best is None or predicted[action] > best+EPS:
                selected, best = action, predicted[action]
    result = dict(canonical_action=selected, actual_action=root['action_map'][selected], fallback=fallback, reason=reason,
        predicted_utilities=predicted, predicted_pair_utilities=pairs, coverage=coverage_rows,
        support=dict(action_root_counts=action_counts, pair_root_counts=pair_counts, connected_components=connected, required_actions=legal, complete=not fallback),
        work=dict(work), feature_work=dict(feature_work))
    if counts is not None:
        counts.update(work); counts.update(feature_work)
    return result


def cohort_cases():
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]+[(4*r+c, 4*r+c+4) for r in range(3) for c in range(4)]
    cases = []
    for replica in range(4):
        for index, (first, second) in enumerate(edges):
            seed = 1860200+24*replica+index; rng = random.Random(seed); board = [rng.randint(1, 10) for _ in range(16)]
            board[first] = board[second] = 1+index % 10
            for cell in rng.sample([cell for cell in range(16) if cell not in (first, second)], index % 3):
                board[cell] = 0
            cases.append(dict(split='TARGET', replica=replica, stratum=index, name=f'v186_target_r{replica:02d}_{index:02d}', horizon=3, seed=seed, board=board, vacancies=index % 3))
    return cases


def freeze_choices(roots, models):
    choices, work = {name: [] for name in (*MODEL_NAMES, 'FALLBACK')}, Counter()
    keys = ('root_id', 'source_id', 'life', 'canonical_board', 'legal_actions', 'immediate_rewards', 'fallback_action', 'action_map', 'layout_features', 'action_features')
    for root in roots:
        observed = {key: root[key] for key in keys}
        for name in MODEL_NAMES:
            chooser = choose_action if name == 'RANK' else shared.choose_action if name in ('SHARED', 'OLD_SHARED') else exact.choose_action if name == 'ONE' else layout.choose_action
            decision = chooser(models[name], observed); work.update(decision['work']); work.update(decision.get('feature_work', {})); work['ranking_frozen_model_choices'] += 1
            choices[name].append(dict(root_id=root['root_id'], mode=name, canonical_action=decision['canonical_action'], actual_action=decision['actual_action'], fallback=decision['fallback'], decision=decision))
        action = root['fallback_action']; work['ranking_frozen_fallback_choices'] += 1
        choices['FALLBACK'].append(dict(root_id=root['root_id'], mode='FALLBACK', canonical_action=action, actual_action=root['action_map'][action], fallback=False,
            decision=dict(reason='observable_immediate_reward', work=dict(ranking_frozen_fallback_choices=1))))
    return choices, dict(work)


def summarize(roots, labels, choices, fit):
    labels = {row['root_id']: row for row in labels}; chosen = {name: {row['root_id']: row for row in rows} for name, rows in choices.items()}
    modes = (*MODEL_NAMES, 'FALLBACK', 'ORACLE'); controls = ('RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE'); records = []
    for root in roots['TARGET']:
        vectors = labels[root['root_id']]['action_components']; oracle = root['legal_actions'][0]
        for action in root['legal_actions'][1:]:
            if exact.utility(vectors[action]) > exact.utility(vectors[oracle])+EPS:
                oracle = action
        models = {}
        for name in modes:
            decision = None if name == 'ORACLE' else chosen[name][root['root_id']]
            action = oracle if decision is None else decision['canonical_action']; vector = vectors[action]
            models[name] = dict(action=action, components=vector, utility=exact.utility(vector), regret=exact.utility(vectors[oracle])-exact.utility(vector), fallback=False if decision is None else decision['fallback'])
        records.append(dict(root_id=root['root_id'], replica=root['replica'], stratum=root['stratum'], models=models))

    def means(rows):
        result = {}
        for name in modes:
            mean = exact.mean_vectors([row['models'][name]['components'] for row in rows])
            result[name] = dict(components=mean, utility=exact.utility(mean), positive_regret_roots=sum(row['models'][name]['regret'] > EPS for row in rows), fallback_roots=sum(row['models'][name]['fallback'] for row in rows))
        return result

    def contrasts(rows):
        first = [dict(root_id=row['root_id'], models={'RANK': row['models']['RANK']}) for row in rows]
        return {'RANK_MINUS_'+name: coverage.coverage_effect(first,
            [dict(root_id=row['root_id'], models={'RANK': row['models'][name]}) for row in rows], 'RANK') for name in controls}

    metrics, effects = means(records), contrasts(records)
    replicas = [dict(replica=replica, roots=len(rows), models=means(rows), comparisons=contrasts(rows))
        for replica in sorted({row['replica'] for row in records}) for rows in [[row for row in records if row['replica'] == replica]]]
    entries = [entry for row in choices['RANK'] for entry in row['decision']['coverage'].values()]
    headroom = metrics['ORACLE']['utility']-metrics['ONE']['utility']
    return dict(schema='acfqp.action_ranking.v186.summary', complete=True, roots=len(records),
        SOURCE=dict(roots=len(roots['SOURCE']), design_groups=len({row['source_id'] for row in roots['SOURCE']}), lambda_value=LAMBDA,
            ranking_pairs=len(fit['design']['rows']), objective=fit['objective'], gradient_inf=fit['gradient_inf'], objective_gap_upper_bound=fit['objective_gap_upper_bound']),
        models=metrics, comparisons=effects, replicas=replicas, root_records=records, oracle_minus_one=headroom,
        oracle_minus_rank=metrics['ORACLE']['utility']-metrics['RANK']['utility'], headroom_closed_fraction=effects['RANK_MINUS_ONE']['utility']/headroom if headroom > EPS else None,
        feature_coverage={key: sum(entry[key] for entry in entries) for key in ('total_tokens', 'known_tokens', 'unknown_tokens')},
        whole_cohort_positive_vs_ridge_and_old_shared=all(effects['RANK_MINUS_'+name]['utility'] > EPS for name in ('RIDGE', 'OLD_SHARED')),
        all_replicas_positive_vs_ridge_and_old_shared=all(row['comparisons']['RANK_MINUS_'+name]['utility'] > EPS for row in replicas for name in ('RIDGE', 'OLD_SHARED')),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=1)


def recorded_fit_costs(design, fit):
    calls, dimensions, rows, nonzero = len(fit['history']), design['shape'][1], len(design['rows']), design['D'].nnz
    work = Counter(design['work'])
    work.update(ranking_optimizer_attempts=1, ranking_optimizer_returns=1, ranking_gap_bound_gradient_squares=dimensions, ranking_final_stationarity_checks=1,
        ranking_loss_gradient_calls=calls, ranking_forward_sparse_values=calls*nonzero, ranking_gradient_sparse_values=calls*nonzero,
        ranking_hinge_residual_values=calls*rows, ranking_loss_weight_reads=calls*rows, ranking_regularizer_coefficient_values=calls*dimensions,
        ranking_gradient_values=calls*dimensions, ranking_gradient_inf_values=calls*dimensions)
    return dict(work)


def expected_model(design, beta, costs):
    return dict(schema='acfqp.action_ranking.v186.model', mode='RANK', life=design['life'], query='risk1', native_teacher_query='goal_1_risk_1', horizon=3,
        coefficients=list(beta), vocabulary=deepcopy(design['vocabulary']), root_ids=list(design['root_ids']), source_ids=list(design['source_ids']),
        action_root_ids=deepcopy(design['action_root_ids']), pair_root_ids=deepcopy(design['pair_root_ids']), connected_components=deepcopy(design['connected_components']),
        constants=dict(lambda_value=LAMBDA, min_action_roots=4, epsilon=EPS, gradient_tolerance=GRADIENT_TOLERANCE, aggregate_columns=6,
            columns=design['shape'][1], token_weights=dict(cell=.25, horizontal=1/math.sqrt(12), vertical=1/math.sqrt(12)), intercept=False), fit_counts=costs)


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, io, objective_work, binding_work = [], Counter(), Counter(), Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); io.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    names = ('stage_checks.json', 'v185_run.json', 'source_labels.json', 'expanded_models.json', 'baseline_models.json', 'learned_rule.json')
    expected_inputs = [(f'inputs/inherited/{name}', 'protocol_frozen') for name in names]
    check('six_protocol_frozen_SOURCE_model_and_rule_inputs', [(row['saved_ref'], row['phase']) for row in inputs] == expected_inputs)
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        io.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        check('retained_input:'+row['saved_ref'], saved == original and len(saved) == row['bytes'])
    stage, inherited_run = read('inputs/inherited/stage_checks.json'), read('inputs/inherited/v185_run.json')
    check('settled_V185_stage_and_run', stage['valid'] and inherited_run['status'] == 'complete')
    source = read('inputs/inherited/source_labels.json'); controls = read('inputs/inherited/expanded_models.json'); old_controls = read('inputs/inherited/baseline_models.json')
    fixed_source = len(source) == 143 and len({row['source_id'] for row in source}) == 36 and controls['RIDGE']['constants']['lambda_value'] == LAMBDA
    check('fixed_SOURCE143_36_groups_strength_vocabulary_and_support', fixed_source and read('source_labels.json') == source)
    design = prepare_ranking(source, controls['RIDGE']); saved_fit, saved_models = read('fit.json'), read('models.json')
    saved_design = {key: value for key, value in design.items() if key not in ('D', 'targets', 'weights')}
    check('independent_full_vector_best_ties_strict_losers_root_weight_and_sparse_design', same(saved_fit['design'], saved_design))
    beta = saved_models['RANK']['coefficients']; certificate = dual_certificate(design, beta)
    check('independent_nonnegative_dual_optimality_KKT_gap_and_coefficient_bound', certificate['accepted'])
    final_objective, gradient = certificate['primal_objective'], np.asarray(certificate['primal_gradient']); gradient_inf = certificate['primal_gradient_inf']
    bound = float(np.dot(gradient, gradient)/(4*LAMBDA))
    expected_final = dict(objective=final_objective, gradient=gradient.tolist(), gradient_inf=gradient_inf, objective_gap_upper_bound=bound, accepted=gradient_inf <= GRADIENT_TOLERANCE)
    check('recomputed_primal_stationarity_and_strong_convex_objective_bound', exact._equal(saved_fit, expected_final) and saved_fit['accepted'])
    optimizer = saved_fit['optimizer']; history = saved_fit['history']
    optimizer_binding = optimizer['method'] == 'L-BFGS-B' and optimizer['options'] == OPTIMIZER_OPTIONS and optimizer['initialization'] == 'ZERO'
    history_binding = len(history) == optimizer['function_evaluations']+1 and [row['evaluation'] for row in history] == list(range(1, len(history)+1))
    initial_objective, initial_gradient = loss_gradient(np.zeros(design['shape'][1]), design, objective_work)
    endpoints_binding = same(history[0], dict(evaluation=1, objective=initial_objective, gradient_inf=float(np.max(np.abs(initial_gradient)))))
    endpoints_binding = endpoints_binding and same(history[-1], dict(evaluation=len(history), objective=final_objective, gradient_inf=gradient_inf))
    check('one_zero_initialized_frozen_optimizer_and_retained_objective_calls', optimizer_binding and history_binding and endpoints_binding)
    learning_costs = recorded_fit_costs(design, saved_fit)
    check('single_primal_optimizer_and_all_recorded_gradient_costs', saved_fit['costs'] == learning_costs and run['costs']['learning']['counts'] == learning_costs)
    model = expected_model(design, beta, learning_costs)
    check('one_scalar_ranking_model_with_fixed_vocabulary_and_support', same(saved_models, dict(RANK=model)))
    cases = cohort_cases(); target, observation_work = coverage.observe_roots(cases); feature_work = coverage.cache_roots(target)
    check('96_fresh_seeded_targets_without_replacement', read('target_cases.json') == cases)
    roots = dict(SOURCE=source, TARGET=target)
    check('source_labels_and_target_observable_caches', same(read('roots.json'), roots))
    check('new_target_observation_and_cache_costs', run['costs']['observations']['counts'] == observation_work and run['costs']['observations']['feature_counts'] == feature_work)
    models = dict(controls, RANK=model, OLD_SHARED=old_controls['SHARED'], ONE=old_controls['ONE'])
    choices, choice_work = freeze_choices(target, models)
    check('dual_certified_primal_scores_EPS_support_fallback_and_all_controls', same(read('choices.json'), choices))
    check('scalar_scores_without_predicted_RFS_and_all_prediction_costs', all('predicted_components' not in row['decision'] for row in choices['RANK']) and run['costs']['choices']['counts'] == choice_work)
    native, label_costs = read('native_labels.json'), read('label_costs.json'); ids = [root['root_id'] for root in target]
    check('complete_native_label_and_paid_cost_rosters', [row['root_id'] for row in native] == ids and [row['root_id'] for row in label_costs] == ids)
    labels, label_work = [], Counter()
    for root, raw, cost_row in zip(target, native, label_costs, strict=True):
        teacher = read(f"teacher_policy/{root['root_id']}.json")
        check('unchanged_native_fraction_teacher_and_canonical_binding:'+root['root_id'], coverage.native_binding(root, raw, teacher))
        binding_work.update(new_label_roots_bound=1, teacher_root_records_inspected=len(teacher), exact_component_coordinates_bound=3*len(root['legal_actions']))
        labels.append(exact.canonical_labels(root, raw, dict(kind='new_exact_V69_FULL', teacher_query='goal_1_risk_1', teacher_policy_ref='teacher_policy/'+root['root_id']+'.json')))
        costs = cost_row['costs']; construction, compilation, export = costs['construction'], costs['compilation'], costs['teacher_export']; n = len(teacher)
        accounting = construction['concrete_states'] <= 200000 and construction['concrete_active_states'] == construction['active_states'] == n
        accounting = accounting and compilation['model_payload_calls'] == compilation['model_reload_calls'] == 1
        accounting = accounting and compilation['payload_cells'] == construction['registered_states'] == costs['label_evaluation']['kernel_cells_read']
        accounting = accounting and compilation['payload_rows'] == costs['label_evaluation']['kernel_rows_read'] and compilation['payload_outcomes'] == costs['label_evaluation']['kernel_outcomes_read']
        accounting = accounting and costs['label_evaluation']['root_labels_emitted'] == 1 and export == dict(teacher_encoding_records_read=construction['concrete_states'], teacher_policy_records=n, teacher_policy_action_reads=n, teacher_policy_tile_reads=16*n)
        check('unchanged_acquisition_caps_and_paid_export_counts:'+root['root_id'], accounting)
        for kind in ('construction', 'planning', 'label_evaluation', 'teacher_export', 'compilation'):
            label_work.update({kind+'.'+key: value for key, value in costs[kind].items() if type(value) is int})
    check('bound_complete_canonical_target_vectors_and_fractions', same(read('labels.json'), labels))
    summary = summarize(roots, labels, choices, saved_fit)
    check('independent_actual_RFS_regret_controls_replica_and_gain_concentration', same(read('summary.json'), summary))
    phases = ['protocol_frozen', 'source_fit', 'models_frozen', 'target_roots', 'target_choices_frozen', 'target_labels', 'complete']
    check('fixed_source_fit_all_models_and_choices_before_target_labels', [(row['phase'], row['input_reads']) for row in run['phase_history']] == [(phase, 0 if i == 0 else 6) for i, phase in enumerate(phases)])
    input_counts = dict(json_read_operations=6, input_bytes_read=sum(row['bytes'] for row in inputs), input_bytes_retained=sum(row['bytes'] for row in inputs))
    check('all_paid_input_and_acquisition_counts', run['costs']['input_counts'] == input_counts and run['costs']['labels']['counts'] == dict(label_work))
    accounting = all(run[key] == 96 for key in ('new_boards_generated', 'new_reference_kernel_attempts', 'new_reference_kernels', 'new_teacher_plans', 'new_exact_label_roots', 'completed_roots'))
    accounting = accounting and run['new_predictor_fit_attempts'] == run['new_predictors_fitted'] == 1 and run['resource_cap_per_board'] == 200000
    accounting = accounting and all(run[key] == 0 for key in ('new_environment_samples', 'new_source_games', 'new_native_weight_updates'))
    check('one_frozen_loss_fit_96_new_labels_and_no_environment_sampling', accounting)
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and summary['complete']
    return dict(schema='acfqp.action_ranking.v186.analysis', valid=valid, complete=complete, primary_complete=complete, checks=checks,
        passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), dual_certificate=certificate, summary=summary,
        costs=dict(new_environment_samples=0, physical_branches_replayed=0, old_kernels_reevaluated=0, new_kernels_reintegrated=0, old_models_refitted=0,
            independent_input_counts=dict(io), independent_ranking_prepare_counts=design['work'], independent_dual_counts=certificate['costs'],
            independent_dual_times=certificate['times'], independent_objective_counts=dict(objective_work), independent_primal_refits=0,
            independent_observation_counts=observation_work, independent_feature_counts=feature_work, independent_choice_counts=choice_work,
            independent_new_label_binding_counts=dict(binding_work), reconstructed_learning_counts=learning_costs, reconstructed_acquisition_counts=dict(label_work),
            original_run_costs=run['costs'], inherited_cost_refs=run['inherited_cost_refs'], test_refs=run['test_refs'], seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    args = parser.parse_args(); result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'], new_environment_samples=0)))


if __name__ == '__main__':
    main()
