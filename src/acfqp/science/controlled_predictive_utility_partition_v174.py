"""Generate partitions by SOURCE-crossfit actual action utility.

Crossfit scores are candidate-learning objectives, not independent confirmation.
Every compared heldout action must be fully model-supported; no historical H2
action is invented for the inherited roots. Final node fits use all DISCOVERY.
"""
from collections import Counter
from copy import deepcopy

from . import controlled_predictive_consequence_partition_v172 as estimation
from .controlled_predictive_consequence_partition_v172 import (
    ACTIONS, EPSILON, MAX_LEAVES, MIN_ACTION_ROOTS, MIN_CHILD_ROOTS, MIN_CHILD_SOURCES,
)

SCHEMA = 'acfqp.utility_partition.v174'
SOURCES = 12
SUFFIXES = 4


def _prepare(examples, life, counts):
    examples = list(examples)
    sources = sorted({row['source_id'] for row in examples if row['life'] == life})
    if len(sources) != SOURCES:
        raise ValueError('twelve fixed DISCOVERY SOURCE games per history required')
    folds = [sources[0::2], sources[1::2]]
    source_fold = {source: fold for fold, group in enumerate(folds) for source in group}
    counts['source_fold_assignments'] += len(sources)
    prepared = estimation._prepare(examples, life, counts)
    originals = {row['root_id']: row for row in examples if row['life'] == life}
    for item in prepared:
        raw = originals[item['root_id']]
        if len(raw['suffix_trials']) != SUFFIXES or {trial['suffix'] for trial in raw['suffix_trials']} != set(range(SUFFIXES)):
            raise ValueError('four complete fixed DISCOVERY suffixes required')
        item['fold'] = source_fold[item['source_id']]
        item['rewards'] = {action: float(raw['immediate_rewards'][action]) for action in item['legal']}
        counts['utility_immediate_reward_loads'] += len(item['legal'])
        means = {action: [0., 0., 0.] for action in item['legal']}
        for trial in raw['suffix_trials']:
            for action in item['legal']:
                for component in range(3):
                    means[action][component] += float(trial['action_components'][action][component])/SUFFIXES
                    counts['observed_terminal_component_reads'] += 1
        item['observed_means'] = means
        item['training_outcome'] = dict(root_id=item['root_id'], source_id=item['source_id'],
            life=life, fold=item['fold'], canonical_board=list(item['board']), legal_actions=list(item['legal']),
            immediate_rewards=dict(item['rewards']), suffix_trials=deepcopy(raw['suffix_trials']))
        counts['observed_terminal_action_averages'] += len(item['legal'])
    return prepared, folds


def _action(fit, item, counts):
    legal = item['legal']
    action_counts = {action: len(fit['action_root_ids'][action]) for action in legal}
    component_ids = {action: component for component, group in enumerate(fit['connected_components']) for action in group}
    counts.update(crossfit_policy_support_checks=1, crossfit_action_support_lookups=len(legal),
                  crossfit_component_membership_lookups=len(legal))
    connected = len({component_ids[action] for action in legal}) == 1
    supported = connected and all(action_counts[action] >= MIN_ACTION_ROOTS for action in legal)
    support = dict(action_root_counts=action_counts, connected=connected, complete=supported)
    if not supported:
        return dict(canonical_action=None, support=support, predicted_components={})
    selected, best, predicted = legal[0], None, {}
    for action in legal:
        vector = list(fit['coefficients'][action]); vector[0] += item['rewards'][action]
        predicted[action] = vector
        value = vector[0]-vector[1]+vector[2]
        counts.update(crossfit_coefficient_component_reads=3, crossfit_exact_reward_reads=1,
                      crossfit_utility_evaluations=1)
        if best is None or value > best+EPSILON:
            selected, best = action, value
    counts['crossfit_supported_policy_decisions'] += 1
    return dict(canonical_action=selected, support=support, predicted_components=predicted)


def _fit_summary(indices, prepared):
    return dict(roots=len(indices), sources=sorted({prepared[index]['source_id'] for index in indices}))


def _candidate(prepared, indices, node_id, cell, threshold, folds, source_counts, counts):
    counts['utility_candidates_evaluated'] += 1
    sides = {index: 'left' if prepared[index]['board'][cell] <= threshold else 'right' for index in indices}
    counts['utility_split_feature_threshold_tests'] += len(indices)
    partitions = [{side: [index for index in indices if prepared[index]['fold'] == fold and sides[index] == side]
                   for side in ('left', 'right')} for fold in range(2)]
    record = dict(candidate_id=f'{node_id}:{cell}:{threshold}', node_id=node_id, cell=cell, threshold=threshold,
                  comparable=False, score=None, selected=False, reason=None, directions=[])
    for fold in range(2):
        side_stats = {side: _fit_summary(partitions[fold][side], prepared) for side in ('left', 'right')}
        record['directions'].append(dict(fit_fold=fold, heldout_fold=1-fold, fit_children=side_stats,
                                         root_decisions=[], source_effects=[], mean_components=None, score=None))
    if any(stats['roots'] < MIN_CHILD_ROOTS for direction in record['directions'] for stats in direction['fit_children'].values()):
        record['reason'] = 'insufficient_fit_child_roots'
        return record
    if any(len(stats['sources']) < MIN_CHILD_SOURCES for direction in record['directions'] for stats in direction['fit_children'].values()):
        record['reason'] = 'insufficient_fit_child_sources'
        return record
    counts['utility_structurally_eligible_candidates'] += 1
    complete = True
    for fold, direction in enumerate(record['directions']):
        fit_indices = sorted(partitions[fold]['left']+partitions[fold]['right'])
        parent_fit = estimation._fit_leaf(prepared, fit_indices, counts)
        children = {side: estimation._fit_leaf(prepared, partitions[fold][side], counts) for side in ('left', 'right')}
        counts.update(crossfit_parent_leaf_fits=1, crossfit_child_leaf_fits=2)
        direction['parent_coefficients'] = deepcopy(parent_fit['coefficients'])
        direction['child_coefficients'] = {side: deepcopy(fit['coefficients']) for side, fit in children.items()}
        for index in indices:
            item = prepared[index]
            if item['fold'] == fold:
                continue
            side = sides[index]
            parent, child = _action(parent_fit, item, counts), _action(children[side], item, counts)
            supported = parent['support']['complete'] and child['support']['complete']
            complete &= supported
            direction['root_decisions'].append(dict(root_id=item['root_id'], source_id=item['source_id'], side=side,
                                                    parent=parent, child=child, complete=supported))
    if not complete:
        record['reason'] = 'unsupported_heldout_policy'
        return record
    counts['utility_comparable_candidates'] += 1
    by_root = {prepared[index]['root_id']: prepared[index] for index in indices}
    for direction in record['directions']:
        sums = {source: [0., 0., 0.] for source in folds[direction['heldout_fold']]}
        region_roots = Counter()
        for decision in direction['root_decisions']:
            item = by_root[decision['root_id']]
            parent = item['observed_means'][decision['parent']['canonical_action']]
            child = item['observed_means'][decision['child']['canonical_action']]
            difference = [child[component]-parent[component] for component in range(3)]
            decision.update(observed_parent_components=list(parent), observed_child_components=list(child),
                            actual_difference_components=difference)
            for component in range(3):
                sums[item['source_id']][component] += difference[component]
            region_roots[item['source_id']] += 1
            counts.update(crossfit_observed_terminal_component_reads=6,
                          crossfit_actual_component_subtractions=3, crossfit_source_component_accumulations=3)
        for source, sums_vector in sorted(sums.items()):
            vector = [value/source_counts[source] for value in sums_vector]
            direction['source_effects'].append(dict(source_id=source, roots=source_counts[source],
                in_region_roots=region_roots[source], components=vector, utility=vector[0]-vector[1]+vector[2]))
            counts.update(crossfit_source_component_normalizations=3, crossfit_source_utility_evaluations=1)
        vector = [sum(effect['components'][component] for effect in direction['source_effects'])/len(direction['source_effects'])
                  for component in range(3)]
        direction.update(mean_components=vector, score=vector[0]-vector[1]+vector[2])
        counts['crossfit_direction_scores'] += 1
    score = sum(direction['score'] for direction in record['directions'])/2
    record.update(comparable=True, score=score, reason='positive_utility' if score > EPSILON else 'utility_not_positive')
    return record


def _search_node(prepared, indices, node_id, folds, source_counts, counts, records):
    counts['utility_search_nodes_evaluated'] += 1
    if any(sum(prepared[index]['fold'] == fold for index in indices) < 2*MIN_CHILD_ROOTS for fold in range(2)):
        counts['utility_nodes_without_two_fit_children'] += 1
        return None
    best = None
    for cell in range(16):
        for threshold in range(10):
            record = _candidate(prepared, indices, node_id, cell, threshold, folds, source_counts, counts)
            records.append(record)
            if record['score'] is None or record['score'] <= EPSILON:
                continue
            counts['utility_positive_candidate_comparisons'] += 1
            if best is None or record['score'] > best['score']+EPSILON:
                best = record
    return best


def propose_partition(examples, life):
    """Learn a utility-ranked tree, then freeze all-node full-DISCOVERY fits."""
    fit_counts, search_counts, node_counts = Counter(), Counter(), Counter()
    prepared, folds = _prepare(examples, life, fit_counts)
    source_counts = dict(Counter(item['source_id'] for item in prepared))
    nodes = [dict(node_id=0, kind='leaf', leaf_id=0)]
    active = {0: list(range(len(prepared)))}
    node_indices = {0: list(active[0])}
    records = []
    candidates = {0: _search_node(prepared, active[0], 0, folds, source_counts, search_counts, records)}
    while len(active) < MAX_LEAVES:
        best = None
        for node_id in sorted(candidates):
            candidate = candidates[node_id]
            if candidate is None:
                continue
            search_counts['utility_global_candidate_comparisons'] += 1
            if best is None or candidate['score'] > best['score']+EPSILON:
                best = candidate
        if best is None:
            break
        node_id, left_id, right_id = best['node_id'], len(nodes), len(nodes)+1
        best['selected'] = True
        left = [index for index in active[node_id] if prepared[index]['board'][best['cell']] <= best['threshold']]
        right = [index for index in active[node_id] if prepared[index]['board'][best['cell']] > best['threshold']]
        nodes[node_id] = dict(node_id=node_id, kind='split', cell=best['cell'], threshold=best['threshold'],
                              left=left_id, right=right_id, utility_gain=best['score'])
        del active[node_id], candidates[node_id]
        for child_id, indices in ((left_id, left), (right_id, right)):
            nodes.append(dict(node_id=child_id, kind='leaf', leaf_id=child_id))
            active[child_id], node_indices[child_id] = indices, indices
        search_counts['utility_splits_applied'] += 1
        if len(active) < MAX_LEAVES:
            for child_id in (left_id, right_id):
                candidates[child_id] = _search_node(prepared, active[child_id], child_id, folds,
                                                    source_counts, search_counts, records)
    fits = {}
    for node in nodes:
        node_id = node['node_id']
        fits[str(node_id)] = dict(leaf_id=node_id, **estimation._fit_leaf(prepared, node_indices[node_id], node_counts))
        node_counts['full_discovery_node_fits'] += 1
    leaves = [deepcopy(fits[str(node_id)]) for node_id in sorted(active)]
    return dict(schema=SCHEMA, life=life, query='risk1', mode='PART_UNPRUNED',
        constants=dict(min_child_roots=MIN_CHILD_ROOTS, min_child_sources=MIN_CHILD_SOURCES,
                       min_action_roots=MIN_ACTION_ROOTS, max_leaves=MAX_LEAVES, epsilon=EPSILON,
                       discovery_sources=SOURCES, suffixes=SUFFIXES),
        root_ids=[item['root_id'] for item in prepared], source_ids=sorted(source_counts), source_folds=folds,
        source_root_counts=source_counts, nodes=nodes, groups={}, leaves=leaves, node_fits=fits,
        fit_labels=[deepcopy(item['fit_label']) for item in prepared],
        training_outcomes=[deepcopy(item['training_outcome']) for item in prepared],
        candidate_records=records, fit_counts=dict(fit_counts), utility_search_counts=dict(search_counts),
        node_fit_counts=dict(node_counts))
