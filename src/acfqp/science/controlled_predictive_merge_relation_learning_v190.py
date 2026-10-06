"""SOURCE-selected complete R/F/S learning from fixed merge relations."""
from collections import Counter
from copy import deepcopy
from itertools import combinations
from math import sqrt

import numpy as np

from . import controlled_predictive_merge_relations_v190 as relation
from . import controlled_predictive_source_regularization_v183 as ridge
from . import controlled_predictive_mechanism_interactions_v188 as previous
from . import controlled_predictive_consequence_partition_v172 as estimation

SCHEMA = 'acfqp.merge_relation_learning.v190'
ACTIONS, EPSILON, LAMBDAS = estimation.ACTIONS, estimation.EPSILON, ridge.LAMBDAS
SOURCE_ROOTS, SOURCE_GROUPS, COLUMNS = 143, 36, 98


def _basis():
    return relation.basis_metadata()


def prepare_design(examples, life=0):
    basis = _basis()
    columns = COLUMNS
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
        features[root_id] = relation.action_features_from_root(root, feature_counts)
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
            counts.update(paired_vector_labels=1, paired_component_subtractions=3, relation_pair_rows=1,
                relation_design_value_reads=2*columns, relation_design_subtractions=columns,
                relation_nonzero_design_entries=len(sparse))
        labels.append(label)
    matrix, targets = np.zeros((len(records), columns)), np.zeros((len(records), 3))
    for index, record in enumerate(records):
        scale = sqrt(record['weight'])
        for column, value in record['design']:
            matrix[index, column] = value*scale
        targets[index] = [value*scale for value in record['components']]
        counts.update(relation_weight_square_roots=1, relation_weighted_design_scalings=len(record['design']),
                      relation_weighted_target_scalings=3)
    counts.update(relation_design_matrix_cells=matrix.size, relation_target_matrix_cells=targets.size,
                  ridge_design_preparations=1)
    action_ids = {a: sorted(ids) for a, ids in action_roots.items()}
    pair_ids = {pair: sorted(ids) for pair, ids in pair_roots.items()}
    source_counts = dict(Counter(row['source_id'] for row in roots))
    return dict(schema=SCHEMA+'.design', mode='RELATION', life=life, basis=basis,
        feature_names=list(relation.FEATURE_NAMES),
        roots=roots, root_ids=[row['root_id'] for row in roots], source_ids=sorted(source_counts), source_root_counts=source_counts,
        action_root_ids=action_ids, pair_root_ids=pair_ids, connected_components=estimation._components(pair_ids),
        fit_labels=labels, pair_records=records, design_format='sparse_columns', shape=list(matrix.shape), X=matrix, Y=targets,
        prepare_counts=dict(counts), feature_counts=dict(feature_counts), work=dict(counts+feature_counts))


def _model(design, decomposition, fitted, lambda_value, source_folds):
    # The retained V188 metadata constructor is independent of its 6/26 encoder.
    payload = previous._model(design, decomposition, fitted, lambda_value, source_folds)
    payload['schema'] = SCHEMA+'.model'
    return payload


def choose_action(payload, root, counts=None):
    if payload['life'] != root['life']:
        raise ValueError('model and root require the same frozen teacher')
    legal = [a for a in ACTIONS if a in root['legal_actions']]
    if not legal or len(legal) != len(root['legal_actions']) or root['fallback_action'] not in legal:
        raise ValueError('distinct legal actions and observable-only fallback required')
    columns = COLUMNS
    feature_work, work = Counter(), Counter(relation_decisions=1, relation_legal_action_reads=len(legal))
    features = relation.action_features_from_root(root, feature_work)
    action_counts = {a: len(payload['action_root_ids'][a]) for a in legal}
    pair_counts = {estimation._pair_key(a, b): len(payload['pair_root_ids'][estimation._pair_key(a, b)])
                   for a, b in combinations(legal, 2)}
    connected = deepcopy(payload['connected_components'])
    component_id = {a: i for i, group in enumerate(connected) for a in group}
    work.update(relation_action_support_lookups=len(legal), relation_pair_support_lookups=len(pair_counts),
                relation_component_membership_lookups=len(legal))
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
        work.update(relation_prediction_feature_reads=3*columns, relation_prediction_coefficient_reads=3*columns,
                    relation_prediction_component_evaluations=3, relation_immediate_reward_reads=1, relation_reward_additions=1)
    pairs = {}
    for first, second in combinations(legal, 2):
        if component_id[first] == component_id[second]:
            pairs[estimation._pair_key(first, second)] = [predicted[first][i]-predicted[second][i] for i in range(3)]
            work['relation_predicted_pair_subtractions'] += 3
    if selected is None:
        selected, best = legal[0], None
        for action in legal:
            vector = predicted[action]
            value = vector[0]-vector[1]+vector[2]
            work['relation_utility_evaluations'] += 1
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
    for key in ('layout_features', 'action_features', 'relation_features'):
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


def _select(examples, life):
    sources = sorted({row['source_id'] for row in examples if row['life'] == life})
    if len(sources) != SOURCE_GROUPS:
        raise ValueError('thirty-six fixed SOURCE groups required')
    source_folds = [sources[::2], sources[1::2]]
    costs = Counter(source_fold_assignments=len(sources), regularization_candidates=len(LAMBDAS))
    designs, decompositions, heldouts, folds = [], [], [], []
    for fold, heldout_sources in enumerate(source_folds):
        train_sources = [s for s in sources if s not in heldout_sources]
        design = prepare_design([r for r in examples if r['life'] == life and r['source_id'] in train_sources], life)
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
    final_design = prepare_design(examples, life)
    costs.update(final_design['work'])
    decomposition = ridge._decompose(final_design, costs)
    fitted = ridge._filter(final_design, decomposition, selected)
    costs.update(fitted['counts'])
    model = _model(final_design, decomposition, fitted, selected, source_folds)
    costs['new_predictors_fitted'] = costs['ridge_predictors_fitted']
    return dict(schema=SCHEMA+'.selection', mode='RELATION', life=life, basis=_basis(), lambdas=list(LAMBDAS),
        source_folds=source_folds, folds=folds, candidates=candidates, selected_lambda=selected,
        selected_utility=best, costs=dict(costs)), model


def fit_model(examples, life=0):
    """Cache SOURCE once, then fit the fixed two folds and selected full model."""
    cached, cache_counts = [], Counter()
    for raw in examples:
        if raw['life'] != life:
            continue
        root = deepcopy(raw)
        root['relation_features'] = relation.action_features_from_root(root, cache_counts)
        cached.append(root)
    if len(cached) != SOURCE_ROOTS:
        raise ValueError('143 fixed SOURCE roots required')
    try:
        selection, model = _select(cached, life)
    except ridge.RegularizationExecutionError as error:
        paid = cache_counts+Counter(error.record['costs'])
        raise ridge.RegularizationExecutionError(f'RELATION:{error.record["operation"]}', paid, error) from error
    costs = cache_counts+Counter(selection['costs'])
    return dict(model=model, selection=selection, costs=dict(costs), cache_counts=dict(cache_counts))
