"""Fixed mechanism products and matched SOURCE-selected linear consequences."""
from collections import Counter
from copy import deepcopy
from itertools import combinations
from math import sqrt
import random

import numpy as np

from . import controlled_predictive_source_regularization_v183 as ridge
from . import controlled_predictive_rank_layout_consequences_v182 as layout
from . import controlled_predictive_shared_consequences_v179 as shared
from . import controlled_predictive_exact_h3_v177 as exact
from . import controlled_predictive_source_coverage_v185 as coverage
from . import controlled_predictive_consequence_partition_v172 as estimation

SCHEMA = 'acfqp.mechanism_interactions.v188'
ACTIONS, EPSILON, LAMBDAS = estimation.ACTIONS, estimation.EPSILON, ridge.LAMBDAS
FEATURE_NAMES = tuple(shared.FEATURE_NAMES)
BOUNDS = (1, 16, 12, 12, 12, 12)
PRODUCT_PAIRS = tuple((i, j) for i in range(6) for j in range(i, 6) if (i, j) != (0, 0))
NORMALIZERS = tuple(sqrt(BOUNDS[i]*BOUNDS[j]) for i, j in PRODUCT_PAIRS)
MODES = ('LINEAR', 'INTERACT')
MODEL_NAMES = ('INTERACT', 'LINEAR', 'RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE')
SOURCE_GROUPS = 36
REPLICAS, ROOTS_PER_REPLICA, SEED_BASE = 4, 24, 1880200


def _basis(mode):
    if mode not in MODES:
        raise ValueError('fixed LINEAR or INTERACT basis required')
    products = [dict(column=6+k, left=i, right=j, normalizer=NORMALIZERS[k],
                     name=f'{FEATURE_NAMES[i]}*{FEATURE_NAMES[j]}')
                for k, (i, j) in enumerate(PRODUCT_PAIRS)] if mode == 'INTERACT' else []
    return dict(aggregate_names=list(FEATURE_NAMES), aggregate_bounds=list(BOUNDS),
                aggregate_scaling='UNCHANGED', products=products, columns=6+len(products), intercept=False)


def action_features_from_root(root, counts=None, mode='INTERACT'):
    """Read the fixed cached aggregates; compute products without environment calls."""
    columns = _basis(mode)['columns']
    work = Counter()
    if 'interaction_features' in root:
        features = {a: list(row[:columns]) for a, row in root['interaction_features'].items()}
        work.update(mechanism_feature_cache_hits=1, mechanism_cached_feature_reads=columns*len(features))
    else:
        if 'action_features' in root:
            aggregates = root['action_features']
            work['mechanism_aggregate_cache_hits'] += 1
        else:
            aggregates = {a: row['aggregate'] for a, row in root['layout_features'].items()}
            work['mechanism_layout_aggregate_cache_hits'] += 1
        features = {}
        for action, values in aggregates.items():
            vector = list(map(float, values))
            if len(vector) != 6:
                raise ValueError('six frozen mechanism aggregates required')
            work.update(mechanism_base_feature_reads=6, mechanism_aggregate_values_copied=6)
            if mode == 'INTERACT':
                vector += [values[i]*values[j]/normalizer
                           for (i, j), normalizer in zip(PRODUCT_PAIRS, NORMALIZERS)]
                work.update(mechanism_product_feature_multiplications=20,
                            mechanism_product_normalizer_reads=20, mechanism_product_normalizations=20)
            features[action] = vector
        work['mechanism_feature_maps_derived'] += 1
    if counts is not None:
        counts.update(work)
    return features


def prepare_design(examples, mode='INTERACT', life=0):
    basis = _basis(mode)
    columns = basis['columns']
    counts, feature_counts = Counter(), Counter()
    roots, features, seen = [], {}, set()
    for raw in examples:
        counts['examples_examined'] += 1
        if raw['life'] != life:
            counts['other_life_examples_excluded'] += 1
            continue
        root_id = raw['root_id']
        if root_id in seen:
            raise ValueError('duplicate exact training root')
        seen.add(root_id)
        legal = [a for a in ACTIONS if a in raw['legal_actions']]
        if not legal or len(legal) != len(raw['legal_actions']) or set(raw['action_components']) != set(legal):
            raise ValueError('one complete vector for every distinct legal action required')
        root = deepcopy(raw)
        root['legal_actions'] = legal
        root['immediate_rewards'] = {a: float(raw['immediate_rewards'][a]) for a in legal}
        root['action_components'] = {a: list(map(float, raw['action_components'][a])) for a in legal}
        if any(len(vector) != 3 for vector in root['action_components'].values()):
            raise ValueError('complete reward/failure/success vectors required')
        features[root_id] = action_features_from_root(root, feature_counts, mode)
        roots.append(root)
        counts.update(examples_fitted=1, legal_action_reads=len(legal), immediate_reward_reads=len(legal),
            exact_action_vector_reads=len(legal), label_component_reads=3*len(legal), tail_reward_subtractions=len(legal))
    roots.sort(key=lambda row: row['root_id'])
    if not roots:
        raise ValueError('same-teacher exact training roots required')
    action_roots = {a: set() for a in ACTIONS}
    pair_roots = {estimation._pair_key(a, b): set() for a, b in combinations(ACTIONS, 2)}
    labels, records = [], []
    for root in roots:
        legal = root['legal_actions']
        tails = {a: [root['action_components'][a][0]-root['immediate_rewards'][a],
                     *root['action_components'][a][1:]] for a in legal}
        for action in legal:
            action_roots[action].add(root['root_id'])
        pairs = list(combinations(legal, 2))
        weight = 1./len(pairs) if pairs else 0.
        label = dict(root_id=root['root_id'], source_id=root['source_id'], legal_actions=legal,
                     label_kind='exact_enumerated_vector', pairs=[])
        for first, second in pairs:
            values = [features[root['root_id']][first][i]-features[root['root_id']][second][i] for i in range(columns)]
            sparse = [[i, value] for i, value in enumerate(values) if value != 0.]
            target = [tails[first][i]-tails[second][i] for i in range(3)]
            pair = dict(actions=[first, second], weight=weight, design=sparse, components=target)
            label['pairs'].append(deepcopy(pair))
            records.append(dict(root_id=root['root_id'], source_id=root['source_id'], **pair))
            pair_roots[estimation._pair_key(first, second)].add(root['root_id'])
            counts.update(paired_vector_labels=1, paired_component_subtractions=3, mechanism_pair_rows=1,
                mechanism_design_value_reads=2*columns, mechanism_design_subtractions=columns,
                mechanism_nonzero_design_entries=len(sparse))
        labels.append(label)
    matrix, targets = np.zeros((len(records), columns)), np.zeros((len(records), 3))
    for index, record in enumerate(records):
        scale = sqrt(record['weight'])
        for column, value in record['design']:
            matrix[index, column] = value*scale
        targets[index] = [value*scale for value in record['components']]
        counts.update(mechanism_weight_square_roots=1, mechanism_weighted_design_scalings=len(record['design']),
                      mechanism_weighted_target_scalings=3)
    counts.update(mechanism_design_matrix_cells=matrix.size, mechanism_target_matrix_cells=targets.size,
                  ridge_design_preparations=1)
    action_ids = {a: sorted(ids) for a, ids in action_roots.items()}
    pair_ids = {pair: sorted(ids) for pair, ids in pair_roots.items()}
    source_counts = dict(Counter(row['source_id'] for row in roots))
    return dict(schema=SCHEMA+'.design', mode=mode, life=life, basis=basis,
        feature_names=list(FEATURE_NAMES)+[row['name'] for row in basis['products']],
        roots=roots, root_ids=[row['root_id'] for row in roots], source_ids=sorted(source_counts), source_root_counts=source_counts,
        action_root_ids=action_ids, pair_root_ids=pair_ids, connected_components=estimation._components(pair_ids),
        fit_labels=labels, pair_records=records, design_format='sparse_columns', shape=list(matrix.shape), X=matrix, Y=targets,
        prepare_counts=dict(counts), feature_counts=dict(feature_counts), work=dict(counts+feature_counts))


def _model(design, decomposition, fitted, lambda_value, source_folds):
    counts = Counter(design['prepare_counts'])+Counter(decomposition['metadata']['work'])+Counter(fitted['counts'])
    return dict(schema=SCHEMA+'.model', mode=design['mode'], life=design['life'], query='risk1',
        native_teacher_query=exact.QUERY, horizon=exact.HORIZON, label_kind='exact_enumerated_vector',
        feature_names=list(design['feature_names']), basis=deepcopy(design['basis']), design_format='sparse_columns',
        coefficients=fitted['coefficients'], rank=decomposition['metadata']['rank'],
        singular_values=decomposition['metadata']['singular_values'], component_losses=fitted['component_losses'],
        loss=fitted['loss'], root_mean_loss=fitted['root_mean_loss'], penalty=fitted['penalty'], objective=fitted['objective'],
        constants=dict(min_action_roots=estimation.MIN_ACTION_ROOTS, epsilon=EPSILON, goal_rank=11,
            columns=design['basis']['columns'], intercept=False, lambda_value=lambda_value,
            penalty_normalization='ROOT_MEAN', rcond=None),
        root_ids=list(design['root_ids']), source_ids=list(design['source_ids']), source_folds=deepcopy(source_folds),
        source_root_counts=deepcopy(design['source_root_counts']), action_root_ids=deepcopy(design['action_root_ids']),
        pair_root_ids=deepcopy(design['pair_root_ids']), connected_components=deepcopy(design['connected_components']),
        fit_labels=deepcopy(design['fit_labels']), fit_residuals=fitted['residuals'], training_outcomes=deepcopy(design['roots']),
        fit_counts=dict(counts), feature_counts=dict(design['feature_counts']))


def choose_action(payload, root, counts=None):
    if payload['life'] != root['life']:
        raise ValueError('model and root require the same frozen teacher')
    legal = [a for a in ACTIONS if a in root['legal_actions']]
    if not legal or len(legal) != len(root['legal_actions']) or root['fallback_action'] not in legal:
        raise ValueError('distinct legal actions and observable-only fallback required')
    columns = _basis(payload['mode'])['columns']
    feature_work, work = Counter(), Counter(mechanism_decisions=1, mechanism_legal_action_reads=len(legal))
    features = action_features_from_root(root, feature_work, payload['mode'])
    action_counts = {a: len(payload['action_root_ids'][a]) for a in legal}
    pair_counts = {estimation._pair_key(a, b): len(payload['pair_root_ids'][estimation._pair_key(a, b)])
                   for a, b in combinations(legal, 2)}
    connected = deepcopy(payload['connected_components'])
    component_id = {a: i for i, group in enumerate(connected) for a in group}
    work.update(mechanism_action_support_lookups=len(legal), mechanism_pair_support_lookups=len(pair_counts),
                mechanism_component_membership_lookups=len(legal))
    if len(legal) == 1:
        selected, fallback, reason = legal[0], False, 'single_legal_action'
    elif any(action_counts[a] < estimation.MIN_ACTION_ROOTS for a in legal):
        selected, fallback, reason = root['fallback_action'], True, 'insufficient_action_support'
    elif len({component_id[a] for a in legal}) != 1:
        selected, fallback, reason = root['fallback_action'], True, 'disconnected_required_actions'
    else:
        selected, fallback, reason = None, False, 'selected'
    predicted = {}
    for action in legal:
        vector = [sum(features[action][i]*payload['coefficients'][i][component] for i in range(columns))
                  for component in range(3)]
        vector[0] += root['immediate_rewards'][action]
        predicted[action] = vector
        work.update(mechanism_prediction_feature_reads=3*columns, mechanism_prediction_coefficient_reads=3*columns,
                    mechanism_prediction_component_evaluations=3, mechanism_immediate_reward_reads=1, mechanism_reward_additions=1)
    pairs = {}
    for first, second in combinations(legal, 2):
        if component_id[first] == component_id[second]:
            pairs[estimation._pair_key(first, second)] = [predicted[first][i]-predicted[second][i] for i in range(3)]
            work['mechanism_predicted_pair_subtractions'] += 3
    if selected is None:
        selected, best = legal[0], None
        for action in legal:
            vector = predicted[action]
            value = vector[0]-vector[1]+vector[2]
            work['mechanism_utility_evaluations'] += 1
            if best is None or value > best+EPSILON:
                selected, best = action, value
    result = dict(canonical_action=selected, actual_action=root['action_map'][selected], fallback=fallback, leaf=0,
        reason=reason, predicted_components=predicted, predicted_pairs=pairs,
        support=dict(action_root_counts=action_counts, pair_root_counts=pair_counts, connected_components=connected,
            required_actions=legal, complete=not fallback), work=dict(work), feature_work=dict(feature_work))
    if counts is not None:
        counts.update(work); counts.update(feature_work)
    return result


def _observable(root):
    keys = ('root_id', 'source_id', 'life', 'canonical_board', 'legal_actions', 'immediate_rewards', 'fallback_action', 'action_map')
    result = {key: root[key] for key in keys}
    for key in ('layout_features', 'action_features', 'interaction_features'):
        if key in root:
            result[key] = root[key]
    return result


def _heldout(model, roots):
    counts, groups, choices = Counter(), {}, []
    for root in sorted(roots, key=lambda row: row['root_id']):
        decision = choose_action(model, _observable(root), counts)
        vector = list(map(float, root['action_components'][decision['canonical_action']]))
        utility = vector[0]-vector[1]+vector[2]
        groups.setdefault(root['source_id'], []).append(vector)
        choices.append(dict(root_id=root['root_id'], source_id=root['source_id'], decision=decision, components=vector, utility=utility))
        counts.update(heldout_action_vector_reads=1, heldout_component_reads=3, heldout_utility_evaluations=1)
    records = []
    for source in sorted(groups):
        mean = [sum(vector[i] for vector in groups[source])/len(groups[source]) for i in range(3)]
        records.append(dict(source_id=source, roots=len(groups[source]), components=mean, utility=mean[0]-mean[1]+mean[2]))
        counts.update(heldout_group_component_means=3, heldout_group_utility_evaluations=1)
    return records, choices, dict(counts)


def _select(examples, mode, life):
    sources = sorted({row['source_id'] for row in examples if row['life'] == life})
    if len(sources) != SOURCE_GROUPS:
        raise ValueError('thirty-six fixed SOURCE groups required')
    source_folds = [sources[::2], sources[1::2]]
    costs = Counter(source_fold_assignments=len(sources), regularization_candidates=len(LAMBDAS))
    designs, decompositions, heldouts, folds = [], [], [], []
    for fold, heldout_sources in enumerate(source_folds):
        train_sources = [s for s in sources if s not in heldout_sources]
        design = prepare_design([r for r in examples if r['life'] == life and r['source_id'] in train_sources], mode, life)
        costs.update(design['work'])
        decomposition = ridge._decompose(design, costs)
        designs.append(design); decompositions.append(decomposition)
        heldouts.append([r for r in examples if r['life'] == life and r['source_id'] in heldout_sources])
        folds.append(dict(fold=fold, train_sources=train_sources, heldout_sources=list(heldout_sources),
            design={key: value for key, value in design.items() if key not in ('X', 'Y')},
            decomposition=deepcopy(decomposition['metadata'])))
    candidates, selected, best = [], LAMBDAS[0], None
    for lambda_value in LAMBDAS:
        results, groups = [], []
        for fold in range(2):
            fitted = ridge._filter(designs[fold], decompositions[fold], lambda_value)
            costs.update(fitted['counts'])
            model = _model(designs[fold], decompositions[fold], fitted, lambda_value, source_folds)
            group_records, choices, prediction_counts = _heldout(model, heldouts[fold])
            costs.update(prediction_counts); groups.extend(group_records)
            results.append(dict(fold=fold, coefficients=fitted['coefficients'], component_losses=fitted['component_losses'],
                loss=fitted['loss'], root_mean_loss=fitted['root_mean_loss'], penalty=fitted['penalty'], objective=fitted['objective'],
                group_records=group_records, choices=choices, prediction_counts=prediction_counts, coefficient_counts=fitted['counts']))
        groups.sort(key=lambda row: row['source_id'])
        utility = sum(row['utility'] for row in groups)/len(sources)
        candidates.append(dict(lambda_value=lambda_value, utility=utility, group_records=groups, fold_results=results))
        costs.update(regularization_group_mean_reads=len(sources), regularization_score_comparisons=1)
        if best is None or utility > best+EPSILON:
            selected, best = lambda_value, utility
    final_design = prepare_design(examples, mode, life)
    costs.update(final_design['work'])
    decomposition = ridge._decompose(final_design, costs)
    fitted = ridge._filter(final_design, decomposition, selected)
    costs.update(fitted['counts'])
    model = _model(final_design, decomposition, fitted, selected, source_folds)
    costs['new_predictors_fitted'] = costs['ridge_predictors_fitted']
    return dict(schema=SCHEMA+'.selection', mode=mode, life=life, basis=_basis(mode), lambdas=list(LAMBDAS),
        source_folds=source_folds, folds=folds, candidates=candidates, selected_lambda=selected,
        selected_utility=best, costs=dict(costs)), model


def fit_models(examples, life=0):
    cached, cache_counts = [], Counter()
    for raw in examples:
        if raw['life'] != life:
            continue
        root = deepcopy(raw)
        root['interaction_features'] = action_features_from_root(root, cache_counts)
        cached.append(root)
    models, selections, costs = {}, {}, Counter(cache_counts)
    for mode in MODES:
        try:
            selection, models[mode] = _select(cached, mode, life)
        except ridge.RegularizationExecutionError as error:
            paid = costs+Counter(error.record['costs'])
            raise ridge.RegularizationExecutionError(f'{mode}:{error.record["operation"]}', paid, error) from error
        selections[mode] = selection
        costs.update(selection['costs'])
    return dict(models=models, selections=selections, costs=dict(costs), cache_counts=dict(cache_counts))


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
            cases.append(dict(split='TARGET', replica=replica, stratum=index, horizon=3, seed=seed,
                name=f'v188_target_r{replica:02d}_{index:02d}', board=board, vacancies=index % 3))
    return cases


def observe_roots(cases):
    return coverage.observe_roots(cases)


def cache_roots(roots):
    work = Counter(coverage.cache_roots(roots))
    for root in roots:
        root['interaction_features'] = action_features_from_root(root, work)
    return dict(work)


def freeze_choices(roots, models):
    choices, work = {mode: [] for mode in (*MODEL_NAMES, 'FALLBACK')}, Counter()
    for root in roots:
        observable = _observable(root)
        for mode in MODEL_NAMES:
            chooser = (choose_action if mode in MODES else shared.choose_action if mode in ('SHARED', 'OLD_SHARED')
                       else exact.choose_action if mode == 'ONE' else layout.choose_action)
            decision = chooser(models[mode], observable)
            work.update(decision['work']); work.update(decision.get('feature_work', {}))
            work['mechanism_frozen_model_choices'] += 1
            choices[mode].append(dict(root_id=root['root_id'], mode=mode, canonical_action=decision['canonical_action'],
                actual_action=decision['actual_action'], fallback=decision['fallback'], decision=decision))
        action = root['fallback_action']
        work['mechanism_frozen_fallback_choices'] += 1
        choices['FALLBACK'].append(dict(root_id=root['root_id'], mode='FALLBACK', canonical_action=action,
            actual_action=root['action_map'][action], fallback=False,
            decision=dict(reason='observable_immediate_reward', work=dict(mechanism_frozen_fallback_choices=1))))
    return choices, dict(work)
