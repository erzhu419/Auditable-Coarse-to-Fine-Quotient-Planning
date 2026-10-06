"""Position-shared rank occurrences with frozen full-consequence learning."""
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

SCHEMA = 'acfqp.position_shared.v187'
REPRESENTATION = 'POSITION_SHARED_OCCURRENCE_SUM'
ACTIONS, EPSILON, LAMBDAS = estimation.ACTIONS, estimation.EPSILON, ridge.LAMBDAS
SOURCE_GROUPS = 36
MODEL_NAMES = ('POOL', 'RIDGE', 'LAYOUT', 'SHARED', 'OLD_SHARED', 'ONE')
SEED_BASE = 1870200
REPLICAS, ROOTS_PER_REPLICA = 4, 24


def action_features_from_root(root, counts=None):
    work = Counter()
    if 'pooled_features' in root:
        features = {a: dict(aggregate=list(row['aggregate']), tokens=[list(t) for t in row['tokens']])
                    for a, row in root['pooled_features'].items()}
        work.update(pool_feature_cache_hits=1, pool_cached_aggregate_reads=6*len(features),
                    pool_cached_token_occurrences=40*len(features), pool_cached_token_values=104*len(features))
    else:
        if 'layout_features' not in root:
            raise ValueError('frozen layout cache required for position sharing')
        features = {}
        for action, row in root['layout_features'].items():
            features[action] = dict(aggregate=list(row['aggregate']), tokens=[[t[0], *t[2:]] for t in row['tokens']])
            work.update(pool_aggregate_values_copied=6, pool_token_occurrences_read=40,
                        pool_token_kind_reads=40, pool_rank_values_copied=64, pool_positions_discarded=40)
        work['pool_feature_maps_derived'] += 1
    if counts is not None:
        counts.update(work)
    return features


def _index(vocabulary, work):
    work['vocabulary_entries_indexed'] += len(vocabulary)
    return {tuple(token): index+6 for index, token in enumerate(vocabulary)}


def _encode(record, vocabulary, work):
    entries = {index: float(value) for index, value in enumerate(record['aggregate'])}
    known, unknown = 0, 0
    for token in record['tokens']:
        work['token_lookups'] += 1
        column = vocabulary.get(tuple(token))
        if column is None:
            unknown += 1; work['unknown_token_entries'] += 1
        else:
            known += 1
            work['pool_duplicate_occurrences'] += int(column in entries)
            entries[column] = entries.get(column, 0.)+layout.TOKEN_WEIGHTS[token[0]]
            work.update(known_token_entries=1, token_weight_loads=1, pool_occurrence_accumulations=1)
    work.update(encoded_actions=1, aggregate_values_read=6)
    return entries, dict(known_tokens=known, unknown_tokens=unknown, total_tokens=len(record['tokens']))


def prepare_design(examples, life=0):
    counts, feature_counts, encoder_counts = Counter(), Counter(), Counter()
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
            raise ValueError('one full vector for each distinct legal action required')
        if len(raw['canonical_board']) != 16:
            raise ValueError('sixteen-cell canonical board required')
        root = deepcopy(raw)
        root['legal_actions'] = legal
        root['immediate_rewards'] = {a: float(raw['immediate_rewards'][a]) for a in legal}
        root['action_components'] = {a: list(map(float, raw['action_components'][a])) for a in legal}
        if any(len(vector) != 3 for vector in root['action_components'].values()):
            raise ValueError('complete reward/failure/success vectors required')
        root['pooled_features'] = action_features_from_root(root, feature_counts)
        features[root_id] = root['pooled_features']
        roots.append(root)
        counts.update(examples_fitted=1, root_feature_tile_reads=16, legal_action_reads=len(legal),
            immediate_reward_reads=len(legal), exact_action_vector_reads=len(legal),
            label_component_reads=3*len(legal), tail_reward_subtractions=len(legal))
    roots.sort(key=lambda row: row['root_id'])
    if not roots:
        raise ValueError('same-history exact roots required')
    vocabulary = [list(token) for token in sorted({tuple(t) for row in roots for a in row['legal_actions']
                                                  for t in features[row['root_id']][a]['tokens']})]
    counts.update(source_vocabulary_tokens=len(vocabulary),
                  vocabulary_token_records_read=sum(40*len(row['legal_actions']) for row in roots))
    indexed = _index(vocabulary, encoder_counts)
    action_roots = {a: set() for a in ACTIONS}
    pair_roots = {estimation._pair_key(a, b): set() for a, b in combinations(ACTIONS, 2)}
    labels, records = [], []
    for root in roots:
        legal = root['legal_actions']
        encoded = {a: _encode(features[root['root_id']][a], indexed, encoder_counts)[0] for a in legal}
        tails = {a: [root['action_components'][a][0]-root['immediate_rewards'][a],
                     *root['action_components'][a][1:]] for a in legal}
        for action in legal:
            action_roots[action].add(root['root_id'])
        pairs = list(combinations(legal, 2))
        weight = 1./len(pairs) if pairs else 0.
        label = dict(root_id=root['root_id'], source_id=root['source_id'], legal_actions=legal,
                     label_kind='exact_enumerated_vector', pairs=[])
        for first, second in pairs:
            columns = sorted(set(encoded[first]) | set(encoded[second]))
            sparse = [[column, encoded[first].get(column, 0.)-encoded[second].get(column, 0.)] for column in columns]
            sparse = [[column, value] for column, value in sparse if value != 0.]
            target = [tails[first][i]-tails[second][i] for i in range(3)]
            pair = dict(actions=[first, second], weight=weight, design=sparse, components=target)
            label['pairs'].append(deepcopy(pair))
            records.append(dict(root_id=root['root_id'], source_id=root['source_id'], **pair))
            pair_roots[estimation._pair_key(first, second)].add(root['root_id'])
            counts.update(paired_vector_labels=1, paired_component_subtractions=3, layout_pair_rows=1,
                layout_design_value_lookups=2*len(columns), layout_design_subtractions=len(columns),
                layout_nonzero_design_entries=len(sparse))
        labels.append(label)
    matrix, targets = np.zeros((len(records), 6+len(vocabulary))), np.zeros((len(records), 3))
    for index, record in enumerate(records):
        scale = sqrt(record['weight'])
        for column, value in record['design']:
            matrix[index, column] = value*scale
        targets[index] = [value*scale for value in record['components']]
        counts.update(layout_weight_square_roots=1, layout_weighted_design_scalings=len(record['design']),
                      layout_weighted_target_scalings=3)
    counts.update(layout_design_matrix_cells=matrix.size, layout_target_matrix_cells=targets.size, ridge_design_preparations=1)
    action_ids = {a: sorted(ids) for a, ids in action_roots.items()}
    pair_ids = {pair: sorted(ids) for pair, ids in pair_roots.items()}
    source_counts = dict(Counter(row['source_id'] for row in roots))
    return dict(schema=SCHEMA+'.design', representation=REPRESENTATION, life=life, vocabulary=vocabulary,
        roots=roots, root_ids=[row['root_id'] for row in roots], source_ids=sorted(source_counts), source_root_counts=source_counts,
        action_root_ids=action_ids, pair_root_ids=pair_ids, connected_components=estimation._components(pair_ids),
        fit_labels=labels, pair_records=records, design_format='sparse_columns', shape=list(matrix.shape), X=matrix, Y=targets,
        prepare_counts=dict(counts), feature_counts=dict(feature_counts), encoder_counts=dict(encoder_counts),
        work=dict(counts+feature_counts+encoder_counts))


def choose_action(payload, root, counts=None):
    if payload['life'] != root['life']:
        raise ValueError('pooled model and root require the same teacher')
    legal = [a for a in ACTIONS if a in root['legal_actions']]
    if not legal or len(legal) != len(root['legal_actions']) or root['fallback_action'] not in legal:
        raise ValueError('distinct legal actions and observable-only fallback required')
    feature_work, work = Counter(), Counter(pool_decisions=1, pool_legal_action_reads=len(legal))
    features = action_features_from_root(root, feature_work)
    indexed = _index(payload['vocabulary'], work)
    action_counts = {a: len(payload['action_root_ids'][a]) for a in legal}
    pair_counts = {estimation._pair_key(a, b): len(payload['pair_root_ids'][estimation._pair_key(a, b)])
                   for a, b in combinations(legal, 2)}
    connected = deepcopy(payload['connected_components'])
    component_id = {a: i for i, group in enumerate(connected) for a in group}
    work.update(pool_action_support_lookups=len(legal), pool_pair_support_lookups=len(pair_counts),
                pool_component_membership_lookups=len(legal))
    if len(legal) == 1:
        selected, fallback, reason = legal[0], False, 'single_legal_action'
    elif any(action_counts[a] < estimation.MIN_ACTION_ROOTS for a in legal):
        selected, fallback, reason = root['fallback_action'], True, 'insufficient_action_support'
    elif len({component_id[a] for a in legal}) != 1:
        selected, fallback, reason = root['fallback_action'], True, 'disconnected_required_actions'
    else:
        selected, fallback, reason = None, False, 'selected'
    predicted, coverage_values = {}, {}
    for action in legal:
        encoded, coverage_values[action] = _encode(features[action], indexed, work)
        vector = [sum(value*payload['coefficients'][column][i] for column, value in encoded.items()) for i in range(3)]
        vector[0] += root['immediate_rewards'][action]
        predicted[action] = vector
        work.update(pool_prediction_coefficient_reads=3*len(encoded), pool_prediction_value_reads=3*len(encoded),
                    pool_prediction_component_evaluations=3, pool_immediate_reward_reads=1, pool_reward_additions=1)
    pairs = {}
    for first, second in combinations(legal, 2):
        if component_id[first] == component_id[second]:
            pairs[estimation._pair_key(first, second)] = [predicted[first][i]-predicted[second][i] for i in range(3)]
            work['pool_predicted_pair_subtractions'] += 3
    if selected is None:
        selected, best = legal[0], None
        for action in legal:
            value = predicted[action][0]-predicted[action][1]+predicted[action][2]
            work['pool_utility_evaluations'] += 1
            if best is None or value > best+EPSILON:
                selected, best = action, value
    result = dict(canonical_action=selected, actual_action=root['action_map'][selected], fallback=fallback, leaf=0,
        reason=reason, predicted_components=predicted, predicted_pairs=pairs, coverage=coverage_values,
        support=dict(action_root_counts=action_counts, pair_root_counts=pair_counts, connected_components=connected,
            required_actions=legal, complete=not fallback), work=dict(work), feature_work=dict(feature_work))
    if counts is not None:
        counts.update(work); counts.update(feature_work)
    return result


def _heldout(model, roots):
    counts, groups, choices = Counter(), {}, []
    for root in sorted(roots, key=lambda row: row['root_id']):
        observable = {key: root[key] for key in ('root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
            'immediate_rewards', 'fallback_action', 'action_map', 'layout_features')}
        if 'pooled_features' in root:
            observable['pooled_features'] = root['pooled_features']
        decision = choose_action(model, observable, counts)
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


def select_regularization(examples, life=0):
    examples = list(examples)
    sources = sorted({row['source_id'] for row in examples if row['life'] == life})
    if len(sources) != SOURCE_GROUPS:
        raise ValueError('thirty-six fixed SOURCE groups required')
    source_folds = [sources[::2], sources[1::2]]
    costs = Counter(source_fold_assignments=len(sources), regularization_candidates=len(LAMBDAS))
    designs, decompositions, heldouts, folds = [], [], [], []
    for fold, heldout_sources in enumerate(source_folds):
        train_sources = [s for s in sources if s not in heldout_sources]
        training = [r for r in examples if r['life'] == life and r['source_id'] in train_sources]
        heldout = [r for r in examples if r['life'] == life and r['source_id'] in heldout_sources]
        design = prepare_design(training, life)
        costs.update(design['work'])
        decomposition = ridge._decompose(design, costs)
        designs.append(design); decompositions.append(decomposition); heldouts.append(heldout)
        folds.append(dict(fold=fold, train_sources=train_sources, heldout_sources=list(heldout_sources),
            design={key: value for key, value in design.items() if key not in ('X', 'Y')},
            decomposition=deepcopy(decomposition['metadata'])))
    candidates, selected, best = [], LAMBDAS[0], None
    for lambda_value in LAMBDAS:
        results, groups = [], []
        for fold in range(2):
            fitted = ridge._filter(designs[fold], decompositions[fold], lambda_value)
            costs.update(fitted['counts'])
            model = ridge._model(designs[fold], decompositions[fold], fitted, lambda_value, source_folds)
            model.update(schema=SCHEMA+'.model', mode='POOL', representation=REPRESENTATION)
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
    final_decomposition = ridge._decompose(final_design, costs)
    fitted = ridge._filter(final_design, final_decomposition, selected)
    costs.update(fitted['counts'])
    model = ridge._model(final_design, final_decomposition, fitted, selected, source_folds)
    model.update(schema=SCHEMA+'.model', mode='POOL', representation=REPRESENTATION)
    costs['new_predictors_fitted'] = costs['ridge_predictors_fitted']
    return dict(schema=SCHEMA+'.selection', representation=REPRESENTATION, life=life, lambdas=list(LAMBDAS),
        source_folds=source_folds, folds=folds, candidates=candidates, selected_lambda=selected,
        selected_utility=best, model=model, costs=dict(costs))


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
                name=f'v187_target_r{replica:02d}_{index:02d}', board=board, vacancies=index % 3))
    return cases


def observe_roots(cases):
    return coverage.observe_roots(cases)


def cache_roots(roots):
    work = Counter(coverage.cache_roots(roots))
    for root in roots:
        root['pooled_features'] = action_features_from_root(root, work)
    return dict(work)


def freeze_choices(roots, models):
    choices = {mode: [] for mode in (*MODEL_NAMES, 'FALLBACK')}
    work = Counter()
    for root in roots:
        observable = {key: root[key] for key in ('root_id', 'source_id', 'life', 'canonical_board', 'legal_actions',
            'immediate_rewards', 'fallback_action', 'action_map', 'layout_features', 'action_features', 'pooled_features')}
        for mode in MODEL_NAMES:
            chooser = (choose_action if mode == 'POOL' else shared.choose_action if mode in ('SHARED', 'OLD_SHARED')
                       else exact.choose_action if mode == 'ONE' else layout.choose_action)
            decision = chooser(models[mode], observable)
            work.update(decision['work']); work.update(decision.get('feature_work', {}))
            work['pool_frozen_model_choices'] += 1
            choices[mode].append(dict(root_id=root['root_id'], mode=mode, canonical_action=decision['canonical_action'],
                actual_action=decision['actual_action'], fallback=decision['fallback'], decision=decision))
        action = root['fallback_action']
        work['pool_frozen_fallback_choices'] += 1
        choices['FALLBACK'].append(dict(root_id=root['root_id'], mode='FALLBACK', canonical_action=action,
            actual_action=root['action_map'][action], fallback=False,
            decision=dict(reason='observable_immediate_reward', work=dict(pool_frozen_fallback_choices=1))))
    return choices, dict(work)
