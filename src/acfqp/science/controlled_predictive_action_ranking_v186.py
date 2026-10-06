"""Decision-focused SOURCE ranking with frozen layout features and support."""
from collections import Counter
from copy import deepcopy
from itertools import combinations
import random
from time import perf_counter

import numpy as np
from scipy.optimize import minimize
from scipy.sparse import csr_matrix

from . import controlled_predictive_rank_layout_consequences_v182 as layout
from . import controlled_predictive_shared_consequences_v179 as shared
from . import controlled_predictive_exact_h3_v177 as exact
from . import controlled_predictive_fresh_h3_confirmation_v184 as fresh
from . import controlled_predictive_source_coverage_v185 as coverage
from . import controlled_predictive_consequence_partition_v172 as estimation

SCHEMA = 'acfqp.action_ranking.v186'
ACTIONS, EPSILON = estimation.ACTIONS, estimation.EPSILON
LAMBDA = .1
GRADIENT_TOLERANCE = 1e-7
OPTIMIZER_OPTIONS = dict(maxiter=1000, maxls=50, ftol=1e-15, gtol=1e-10)
MODEL_NAMES = ('RANK', 'RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE')
SEED_BASE = 1860200
REPLICAS, ROOTS_PER_REPLICA = 4, 24
cache_roots = coverage.cache_roots


class RankingExecutionError(RuntimeError):
    def __init__(self, record):
        self.record = record
        super().__init__(record.get('error', 'ranking optimizer did not meet stationarity tolerance'))


def prepare_ranking(examples, reference_model):
    """Bind complete SOURCE labels to the frozen vocabulary and observed support."""
    work, roots, seen = Counter(), [], set()
    life = reference_model['life']
    vocabulary = deepcopy(reference_model['vocabulary'])
    indexed = layout._index(vocabulary, work)
    for raw in examples:
        work['ranking_examples_examined'] += 1
        if raw['life'] != life:
            work['ranking_other_life_excluded'] += 1
            continue
        root_id = raw['root_id']
        if root_id in seen:
            raise ValueError('duplicate ranking training root')
        seen.add(root_id)
        legal = [action for action in ACTIONS if action in raw['legal_actions']]
        if not legal or len(legal) != len(raw['legal_actions']) or set(raw['action_components']) != set(legal):
            raise ValueError('complete exact vectors for every distinct legal action required')
        if 'layout_features' not in raw:
            raise ValueError('frozen layout feature cache required')
        root = dict(root_id=root_id, source_id=raw['source_id'], legal_actions=legal,
            immediate_rewards={a: float(raw['immediate_rewards'][a]) for a in legal},
            action_components={a: list(map(float, raw['action_components'][a])) for a in legal},
            layout_features=raw['layout_features'])
        if any(len(vector) != 3 for vector in root['action_components'].values()):
            raise ValueError('complete reward/failure/success vectors required')
        roots.append(root)
        work.update(ranking_root_labels_read=1, ranking_legal_action_reads=len(legal),
                    ranking_full_component_reads=3*len(legal), ranking_immediate_reward_reads=len(legal))
    roots.sort(key=lambda row: row['root_id'])
    root_ids = [row['root_id'] for row in roots]
    if not roots or root_ids != sorted(reference_model['root_ids']):
        raise ValueError('ranking roots must match the frozen SOURCE reference exactly')
    rows, root_records, values, row_indices, column_indices = [], [], [], [], []
    for root in roots:
        legal = root['legal_actions']
        encoded = {a: layout._encode(root['layout_features'][a], indexed, work)[0] for a in legal}
        utilities = {a: vector[0]-vector[1]+vector[2] for a, vector in root['action_components'].items()}
        best, best_value = legal[0], utilities[legal[0]]
        for action in legal[1:]:
            if utilities[action] > best_value+EPSILON:
                best, best_value = action, utilities[action]
        ties = [a for a in legal if abs(best_value-utilities[a]) <= EPSILON]
        losers = [a for a in legal if best_value-utilities[a] > EPSILON]
        root_rows = []
        for bad in losers:
            columns = sorted(set(encoded[best]) | set(encoded[bad]))
            sparse = [[column, encoded[best].get(column, 0.)-encoded[bad].get(column, 0.)] for column in columns]
            sparse = [[column, value] for column, value in sparse if value != 0.]
            utility_gap = best_value-utilities[bad]
            reward_gap = root['immediate_rewards'][best]-root['immediate_rewards'][bad]
            record = dict(root_id=root['root_id'], source_id=root['source_id'], best_action=best,
                bad_action=bad, utility_gap=utility_gap, immediate_reward_gap=reward_gap,
                target=utility_gap-reward_gap, weight=1./len(losers), design=sparse)
            index = len(rows)
            rows.append(record); root_rows.append(index)
            for column, value in sparse:
                row_indices.append(index); column_indices.append(column); values.append(value)
            work.update(ranking_loser_pairs=1, ranking_design_value_reads=2*len(columns),
                ranking_design_subtractions=len(columns), ranking_sparse_design_entries=len(sparse),
                ranking_utility_gap_subtractions=1, ranking_reward_gap_subtractions=1,
                ranking_target_subtractions=1)
        root_records.append(dict(root_id=root['root_id'], source_id=root['source_id'], legal_actions=legal,
            action_components=deepcopy(root['action_components']), utilities=utilities,
            immediate_rewards=dict(root['immediate_rewards']), best_action=best,
            tied_actions=ties, loser_actions=losers, rows=root_rows))
        work.update(ranking_utility_evaluations=len(legal), ranking_best_comparisons=max(0, len(legal)-1),
                    ranking_tie_tests=len(legal), ranking_loser_tests=len(legal), ranking_roots_prepared=1)
    dimensions = 6+len(vocabulary)
    matrix = csr_matrix((values, (row_indices, column_indices)), shape=(len(rows), dimensions), dtype=float)
    work.update(ranking_csr_matrices=1, ranking_csr_stored_values=matrix.nnz)
    return dict(schema=SCHEMA+'.design', life=life, vocabulary=vocabulary,
        root_count=len(roots), root_ids=root_ids, root_records=root_records, rows=rows,
        source_ids=sorted({row['source_id'] for row in roots}),
        action_root_ids=deepcopy(reference_model['action_root_ids']),
        pair_root_ids=deepcopy(reference_model['pair_root_ids']),
        connected_components=deepcopy(reference_model['connected_components']),
        shape=list(matrix.shape), D=matrix, targets=np.asarray([r['target'] for r in rows]),
        weights=np.asarray([r['weight'] for r in rows]), lambda_value=LAMBDA, work=dict(work))


def loss_gradient(beta, design):
    """Mean-root positive ranking residual plus fixed quadratic regularization."""
    beta = np.asarray(beta, dtype=float)
    residual = np.maximum(0., design['targets']-design['D'] @ beta)
    weighted = design['weights']*residual
    loss = float(np.dot(weighted, residual)/design['root_count']+LAMBDA*np.dot(beta, beta))
    gradient = -2.*np.asarray(design['D'].T @ weighted).ravel()/design['root_count']+2.*LAMBDA*beta
    return loss, gradient


def fit_ranking(examples, reference_model):
    """Fit once from zero; unresolved stationarity stops before fresh labels."""
    started = perf_counter()
    design = prepare_ranking(examples, reference_model)
    saved_design = {key: value for key, value in design.items() if key not in ('D', 'targets', 'weights')}
    costs, history = Counter(design['work']), []
    dimensions = design['shape'][1]
    def evaluate(beta):
        loss, gradient = loss_gradient(beta, design)
        costs.update(ranking_loss_gradient_calls=1, ranking_forward_sparse_values=design['D'].nnz,
            ranking_gradient_sparse_values=design['D'].nnz, ranking_hinge_residual_values=len(design['rows']),
            ranking_loss_weight_reads=len(design['rows']), ranking_regularizer_coefficient_values=dimensions,
            ranking_gradient_values=dimensions, ranking_gradient_inf_values=dimensions)
        history.append(dict(evaluation=len(history)+1, objective=loss,
                            gradient_inf=float(np.max(np.abs(gradient))) if len(gradient) else 0.))
        return loss, gradient
    costs['ranking_optimizer_attempts'] += 1
    tick = perf_counter()
    try:
        result = minimize(evaluate, np.zeros(dimensions), method='L-BFGS-B', jac=True,
                          options=dict(OPTIMIZER_OPTIONS))
    except Exception as error:
        raise RankingExecutionError(dict(error=str(error), design=saved_design,
            history=history, costs=dict(costs), seconds=perf_counter()-started)) from error
    optimizer_seconds = perf_counter()-tick
    costs['ranking_optimizer_returns'] += 1
    objective, gradient = evaluate(result.x)
    gradient_inf = float(np.max(np.abs(gradient))) if len(gradient) else 0.
    objective_gap_bound = float(np.dot(gradient, gradient)/(4.*LAMBDA))
    costs.update(ranking_gap_bound_gradient_squares=dimensions, ranking_final_stationarity_checks=1)
    fit = dict(design=saved_design, history=history, objective=objective,
        gradient=gradient.tolist(), gradient_inf=gradient_inf, objective_gap_upper_bound=objective_gap_bound,
        accepted=gradient_inf <= GRADIENT_TOLERANCE,
        optimizer=dict(method='L-BFGS-B', options=dict(OPTIMIZER_OPTIONS), initialization='ZERO',
            success=bool(result.success), status=int(result.status), message=str(result.message),
            iterations=int(result.nit), function_evaluations=int(result.nfev), gradient_evaluations=int(result.njev)),
        costs=dict(costs), times=dict(optimizer=optimizer_seconds, total=perf_counter()-started))
    if not fit['accepted']:
        raise RankingExecutionError(dict(fit, error='ranking gradient tolerance was not achieved'))
    model = dict(schema=SCHEMA+'.model', mode='RANK', life=design['life'], query='risk1',
        native_teacher_query=exact.QUERY, horizon=3, coefficients=result.x.tolist(),
        vocabulary=deepcopy(design['vocabulary']), root_ids=list(design['root_ids']), source_ids=list(design['source_ids']),
        action_root_ids=deepcopy(design['action_root_ids']), pair_root_ids=deepcopy(design['pair_root_ids']),
        connected_components=deepcopy(design['connected_components']),
        constants=dict(lambda_value=LAMBDA, min_action_roots=estimation.MIN_ACTION_ROOTS,
            epsilon=EPSILON, gradient_tolerance=GRADIENT_TOLERANCE, aggregate_columns=6,
            columns=dimensions, token_weights=dict(layout.TOKEN_WEIGHTS), intercept=False),
        fit_counts=dict(costs))
    return dict(model=model, fit=fit)


def choose_action(payload, root, counts=None):
    """Rank scalar utilities without inventing reward/failure/success predictions."""
    if payload['life'] != root['life']:
        raise ValueError('ranking model and root require the same teacher')
    legal = [a for a in ACTIONS if a in root['legal_actions']]
    if not legal or len(legal) != len(root['legal_actions']) or root['fallback_action'] not in legal:
        raise ValueError('distinct legal actions and observable-only fallback required')
    if 'layout_features' not in root:
        raise ValueError('frozen current layout cache required')
    feature_work, work = Counter(), Counter(ranking_decisions=1, ranking_legal_action_reads=len(legal))
    features = layout.action_features_from_root(root, feature_work)
    indexed = layout._index(payload['vocabulary'], work)
    action_counts = {a: len(payload['action_root_ids'][a]) for a in legal}
    pair_counts = {estimation._pair_key(a, b): len(payload['pair_root_ids'][estimation._pair_key(a, b)])
                   for a, b in combinations(legal, 2)}
    connected = deepcopy(payload['connected_components'])
    component_id = {a: i for i, group in enumerate(connected) for a in group}
    work.update(ranking_action_support_lookups=len(legal), ranking_pair_support_lookups=len(pair_counts),
                ranking_component_membership_lookups=len(legal))
    if len(legal) == 1:
        selected, fallback, reason = legal[0], False, 'single_legal_action'
    elif any(action_counts[a] < estimation.MIN_ACTION_ROOTS for a in legal):
        selected, fallback, reason = root['fallback_action'], True, 'insufficient_action_support'
    elif len({component_id[a] for a in legal}) != 1:
        selected, fallback, reason = root['fallback_action'], True, 'disconnected_required_actions'
    else:
        selected, fallback, reason = None, False, 'selected'
    predicted, coverage = {}, {}
    for action in legal:
        encoded, coverage[action] = layout._encode(features[action], indexed, work)
        predicted[action] = root['immediate_rewards'][action]+sum(value*payload['coefficients'][column]
                                                                for column, value in encoded.items())
        work.update(ranking_prediction_coefficient_reads=len(encoded), ranking_prediction_value_reads=len(encoded),
                    ranking_immediate_reward_reads=1, ranking_reward_additions=1)
    pairs = {}
    for first, second in combinations(legal, 2):
        if component_id[first] == component_id[second]:
            pairs[estimation._pair_key(first, second)] = predicted[first]-predicted[second]
            work['ranking_predicted_pair_subtractions'] += 1
    if selected is None:
        selected, best = legal[0], None
        for action in legal:
            work['ranking_utility_comparisons'] += 1
            if best is None or predicted[action] > best+EPSILON:
                selected, best = action, predicted[action]
    result = dict(canonical_action=selected, actual_action=root['action_map'][selected], fallback=fallback,
        reason=reason, predicted_utilities=predicted, predicted_pair_utilities=pairs, coverage=coverage,
        support=dict(action_root_counts=action_counts, pair_root_counts=pair_counts, connected_components=connected,
            required_actions=legal, complete=not fallback), work=dict(work), feature_work=dict(feature_work))
    if counts is not None:
        counts.update(work); counts.update(feature_work)
    return result


def cohort_cases():
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    cases = []
    for replica in range(REPLICAS):
        for index in range(ROOTS_PER_REPLICA):
            seed = SEED_BASE+24*replica+index
            rng = random.Random(seed)
            board = [rng.randint(1, 10) for _ in range(16)]
            first, second = edges[index]
            board[first] = board[second] = 1+index % 10
            for cell in rng.sample([i for i in range(16) if i not in (first, second)], index % 3):
                board[cell] = 0
            cases.append(dict(split='TARGET', replica=replica, stratum=index,
                name=f'v186_target_r{replica:02d}_{index:02d}', horizon=3, seed=seed,
                board=board, vacancies=index % 3))
    return cases


def observe_roots(cases):
    roots, work = fresh.observe_roots(cases)
    for root in roots:
        root['cohort'] = root['split'] = 'TARGET'
    return roots, work


def freeze_choices(roots, models):
    choices = {mode: [] for mode in (*MODEL_NAMES, 'FALLBACK')}
    work = Counter()
    for root in roots:
        observable = {key: root[key] for key in ('root_id', 'source_id', 'life', 'canonical_board',
            'legal_actions', 'immediate_rewards', 'fallback_action', 'action_map', 'layout_features', 'action_features')}
        for mode in MODEL_NAMES:
            chooser = (choose_action if mode == 'RANK' else shared.choose_action if mode in ('SHARED', 'OLD_SHARED')
                       else exact.choose_action if mode == 'ONE' else layout.choose_action)
            decision = chooser(models[mode], observable)
            work.update(decision['work']); work.update(decision.get('feature_work', {}))
            work['ranking_frozen_model_choices'] += 1
            choices[mode].append(dict(root_id=root['root_id'], mode=mode, canonical_action=decision['canonical_action'],
                actual_action=decision['actual_action'], fallback=decision['fallback'], decision=decision))
        action = root['fallback_action']
        work['ranking_frozen_fallback_choices'] += 1
        choices['FALLBACK'].append(dict(root_id=root['root_id'], mode='FALLBACK', canonical_action=action,
            actual_action=root['action_map'][action], fallback=False,
            decision=dict(reason='observable_immediate_reward', work=dict(ranking_frozen_fallback_choices=1))))
    return choices, dict(work)
