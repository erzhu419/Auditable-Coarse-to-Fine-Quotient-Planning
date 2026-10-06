"""Learn spatial partitions from same-teacher paired terminal contrasts.

Leaf coefficients identify relative continuation vectors, not probabilities or
absolute values. Exact immediate swipe reward remains a decision parameter.
"""
from collections import Counter
from copy import deepcopy
from itertools import combinations

import numpy as np

from .controlled_predictive_causal_quotient_v171 import state_key

ACTIONS = ('DOWN', 'LEFT', 'RIGHT', 'UP')
MIN_CHILD_ROOTS = 8
MIN_CHILD_SOURCES = 2
MAX_LEAVES = 16
MIN_ACTION_ROOTS = 4
MODES = ('PART_EARLY', 'PART_LATE', 'COARSE_LATE', 'ONE_LATE')
EPSILON = 1e-12
SCHEMA = 'acfqp.consequence_partition.v172'


def _pair_key(first, second):
    return f'{first}|{second}'


def _components(pair_root_ids):
    adjacency = {action: set() for action in ACTIONS}
    for key, roots in pair_root_ids.items():
        if roots:
            first, second = key.split('|')
            adjacency[first].add(second)
            adjacency[second].add(first)
    components, remaining = [], set(ACTIONS)
    for action in ACTIONS:
        if action not in remaining:
            continue
        connected, pending = set(), [action]
        while pending:
            current = pending.pop()
            if current in connected:
                continue
            connected.add(current)
            pending.extend(adjacency[current]-connected)
        remaining -= connected
        components.append([item for item in ACTIONS if item in connected])
    return components


def _prepare(examples, life, counts):
    prepared, seen = [], set()
    for example in examples:
        counts['examples_examined'] += 1
        if example['life'] != life:
            counts['other_life_examples_excluded'] += 1
            continue
        root_id = example['root_id']
        if root_id in seen:
            raise ValueError('duplicate training root')
        seen.add(root_id)
        board = list(example['canonical_board'])
        if len(board) != 16:
            raise ValueError('canonical root must have sixteen tile ranks')
        legal = [action for action in ACTIONS if action in example['legal_actions']]
        if not legal or len(legal) != len(example['legal_actions']):
            raise ValueError('distinct canonical legal actions required')
        rewards = {action: float(example['immediate_rewards'][action]) for action in legal}
        trials = sorted(example['suffix_trials'], key=lambda item: item['suffix'])
        if not trials or len({item['suffix'] for item in trials}) != len(trials):
            raise ValueError('distinct observed suffix trials required')
        counts.update(examples_fitted=1, root_feature_tile_reads=16,
                      legal_action_reads=len(legal), immediate_reward_reads=len(legal))
        pairs = list(combinations(legal, 2))
        weight = 1./(len(trials)*len(pairs)) if pairs else 0.
        observations, labels = [], []
        for trial in trials:
            if set(trial['action_components']) != set(legal):
                raise ValueError('every suffix must cover exactly the root legal actions')
            counts['suffix_trials_read'] += 1
            tails = {}
            for action in legal:
                vector = [float(value) for value in trial['action_components'][action]]
                if len(vector) != 3:
                    raise ValueError('complete reward/failure/success vector required')
                vector[0] -= rewards[action]
                tails[action] = vector
                counts.update(label_component_reads=3, tail_reward_subtractions=1)
            pair_labels = []
            for first, second in pairs:
                target = [tails[first][component]-tails[second][component] for component in range(3)]
                observations.append((first, second, weight, target))
                pair_labels.append(dict(actions=[first, second], weight=weight, components=target))
                counts.update(paired_vector_labels=1, paired_component_subtractions=3)
            labels.append(dict(suffix=trial['suffix'], seed=trial['seed'], pairs=pair_labels))
        prepared.append(dict(root_id=root_id, source_id=example['source_id'], board=board,
                             legal=legal, observations=observations,
                             fit_label=dict(root_id=root_id, source_id=example['source_id'],
                                            legal_actions=legal, suffixes=labels)))
    if not prepared:
        raise ValueError('same-history training roots required')
    return sorted(prepared, key=lambda item: item['root_id'])


def solve_centered_laplacian(laplacian, rhs, components):
    """Fix every connected gauge explicitly despite floating row-sum error."""
    constraints = np.asarray([[float(action in component) for action in ACTIONS]
                              for component in components])
    matrix = np.vstack((laplacian, constraints))
    targets = np.vstack((rhs, np.zeros((len(components), 3))))
    return np.linalg.lstsq(matrix, targets, rcond=None)[0]


def _fit_leaf(prepared, indices, counts):
    counts.update(leaf_fits=1, leaf_fit_root_visits=len(indices))
    laplacian, rhs = np.zeros((4, 4)), np.zeros((4, 3))
    action_roots = {action: set() for action in ACTIONS}
    pair_roots = {_pair_key(first, second): set() for first, second in combinations(ACTIONS, 2)}
    observations, total_weight = [], 0.
    for index in indices:
        item = prepared[index]
        for action in item['legal']:
            action_roots[action].add(item['root_id'])
        for first, second, weight, target in item['observations']:
            ia, ib = ACTIONS.index(first), ACTIONS.index(second)
            laplacian[ia, ia] += weight
            laplacian[ib, ib] += weight
            laplacian[ia, ib] -= weight
            laplacian[ib, ia] -= weight
            for component in range(3):
                rhs[ia, component] += weight*target[component]
                rhs[ib, component] -= weight*target[component]
            observations.append((ia, ib, weight, target))
            total_weight += weight
            pair_roots[_pair_key(first, second)].add(item['root_id'])
            counts.update(leaf_pair_observations=1, laplacian_scalar_accumulations=4,
                          rhs_component_accumulations=6)
    pairs = {key: sorted(roots) for key, roots in pair_roots.items()}
    connected = _components(pairs)
    # Real 1/24 weights lift the floating null eigenvalue above default rcond.
    # Explicit component constraints preserve the intended relative coordinates.
    if observations:
        coefficients = solve_centered_laplacian(laplacian, rhs, connected)
        counts.update(laplacian_solves=1, laplacian_matrix_cells=16, laplacian_rhs_cells=12)
        counts.update(zero_sum_constraint_rows=len(connected), zero_sum_constraint_cells=4*len(connected),
                      centered_solver_matrix_cells=4*(4+len(connected)),
                      centered_solver_rhs_cells=3*(4+len(connected)))
    else:
        coefficients = np.zeros((4, 3))
    loss = 0.
    for ia, ib, weight, target in observations:
        for component in range(3):
            residual = coefficients[ia, component]-coefficients[ib, component]-target[component]
            loss += weight*residual*residual
            counts['loss_component_residuals'] += 1
    return dict(root_ids=sorted(prepared[index]['root_id'] for index in indices),
                source_ids=sorted({prepared[index]['source_id'] for index in indices}),
                coefficients={action: list(map(float, coefficients[index])) for index, action in enumerate(ACTIONS)},
                action_root_ids={action: sorted(roots) for action, roots in action_roots.items()},
                pair_root_ids=pairs, connected_components=connected,
                loss=float(loss), pair_observations=len(observations), total_pair_weight=float(total_weight))


def _best_split(prepared, node_id, indices, leaf, counts):
    best = None
    if len(indices) < 2*MIN_CHILD_ROOTS:
        return None
    counts['split_nodes_evaluated'] += 1
    for cell in range(16):
        for threshold in range(10):
            counts['split_predicates_evaluated'] += 1
            left, right = [], []
            for index in indices:
                (left if prepared[index]['board'][cell] <= threshold else right).append(index)
                counts['split_feature_threshold_tests'] += 1
            if min(len(left), len(right)) < MIN_CHILD_ROOTS:
                continue
            if min(len({prepared[index]['source_id'] for index in left}),
                   len({prepared[index]['source_id'] for index in right})) < MIN_CHILD_SOURCES:
                continue
            counts['supported_split_candidates'] += 1
            left_fit, right_fit = _fit_leaf(prepared, left, counts), _fit_leaf(prepared, right, counts)
            gain = leaf['loss']-left_fit['loss']-right_fit['loss']
            counts['split_gain_comparisons'] += 1
            if gain > EPSILON and (best is None or gain > best['gain']+EPSILON):
                best = dict(node_id=node_id, cell=cell, threshold=threshold, gain=float(gain),
                            left=left, right=right, left_fit=left_fit, right_fit=right_fit)
    return best


def _tree(prepared, counts):
    indices = list(range(len(prepared)))
    initial = _fit_leaf(prepared, indices, counts)
    nodes = [dict(node_id=0, kind='leaf', leaf_id=0)]
    active = {0: (indices, initial)}
    candidates = {0: _best_split(prepared, 0, indices, initial, counts)}
    while len(active) < MAX_LEAVES:
        best = None
        for node_id in sorted(candidates):
            candidate = candidates[node_id]
            if candidate is None:
                continue
            counts['global_split_gain_comparisons'] += 1
            if best is None or candidate['gain'] > best['gain']+EPSILON:
                best = candidate
        if best is None:
            break
        node_id, left_id, right_id = best['node_id'], len(nodes), len(nodes)+1
        nodes[node_id] = dict(node_id=node_id, kind='split', cell=best['cell'],
                              threshold=best['threshold'], left=left_id, right=right_id, gain=best['gain'])
        del active[node_id], candidates[node_id]
        for label, child_id in (('left', left_id), ('right', right_id)):
            child_indices, child_fit = best[label], best[f'{label}_fit']
            nodes.append(dict(node_id=child_id, kind='leaf', leaf_id=child_id))
            active[child_id] = (child_indices, child_fit)
            candidates[child_id] = _best_split(prepared, child_id, child_indices, child_fit, counts)
        counts['splits_applied'] += 1
    leaves = [dict(leaf_id=node_id, **leaf) for node_id, (_, leaf) in sorted(active.items())]
    return nodes, {}, leaves


def fit_partition(examples, life, mode):
    """Fit one frozen history's joint-legal paired continuation contrasts."""
    if mode not in MODES:
        raise ValueError('unknown consequence partition mode')
    counts = Counter()
    prepared = _prepare(examples, life, counts)
    if mode.startswith('PART_'):
        nodes, groups, leaves = _tree(prepared, counts)
    else:
        grouped = {}
        for index, item in enumerate(prepared):
            key = 'ALL' if mode == 'ONE_LATE' else state_key(item['board'], counts)
            grouped.setdefault(key, []).append(index)
        groups, leaves, nodes = {}, [], []
        for leaf_id, (key, indices) in enumerate(sorted(grouped.items())):
            groups[key] = leaf_id
            leaves.append(dict(leaf_id=leaf_id, **_fit_leaf(prepared, indices, counts)))
    counts['final_leaves'] = len(leaves)
    return dict(schema=SCHEMA, life=life, query='risk1', mode=mode,
                constants=dict(min_child_roots=MIN_CHILD_ROOTS, max_leaves=MAX_LEAVES,
                               min_child_sources=MIN_CHILD_SOURCES,
                               min_action_roots=MIN_ACTION_ROOTS, epsilon=EPSILON),
                root_ids=[item['root_id'] for item in prepared],
                source_ids=sorted({item['source_id'] for item in prepared}),
                nodes=nodes, groups=groups, leaves=leaves,
                fit_labels=[deepcopy(item['fit_label']) for item in prepared], fit_counts=dict(counts))


def _route(payload, board, work):
    if payload['mode'].startswith('PART_'):
        node_id = 0
        while True:
            node = payload['nodes'][node_id]
            work['partition_node_lookups'] += 1
            if node['kind'] == 'leaf':
                return node['leaf_id']
            work['partition_feature_threshold_tests'] += 1
            node_id = node['left'] if board[node['cell']] <= node['threshold'] else node['right']
    key = 'ALL' if payload['mode'] == 'ONE_LATE' else state_key(board, work)
    work['partition_group_lookups'] += 1
    return payload['groups'].get(key)


def choose_action(payload, root, counts=None):
    """Choose a current legal action from contrasts plus exact immediate reward."""
    if root['life'] != payload['life']:
        raise ValueError('partition and root must use the same frozen teacher history')
    legal = [action for action in ACTIONS if action in root['legal_actions']]
    if not legal or len(legal) != len(root['legal_actions']) or root['teacher_action'] not in legal:
        raise ValueError('legal canonical actions and their supplied teacher action required')
    work = Counter(partition_decisions=1, partition_legal_action_reads=len(legal))
    leaf_id = _route(payload, root['canonical_board'], work)
    leaf = None
    for item in payload['leaves']:
        work['partition_leaf_records_examined'] += 1
        if item['leaf_id'] == leaf_id:
            leaf = item
            break
    action_counts = {action: len(leaf['action_root_ids'][action]) if leaf else 0 for action in legal}
    pair_counts = {_pair_key(first, second): len(leaf['pair_root_ids'][_pair_key(first, second)]) if leaf else 0
                   for first, second in combinations(legal, 2)}
    connected = deepcopy(leaf['connected_components']) if leaf else [[action] for action in ACTIONS]
    component_id = {action: index for index, component in enumerate(connected) for action in component}
    work.update(partition_action_support_lookups=len(legal), partition_pair_support_lookups=len(pair_counts))
    reason = 'selected'
    if len(legal) == 1:
        selected, fallback, reason = legal[0], False, 'single_legal_action'
    elif leaf is None:
        selected, fallback, reason = root['teacher_action'], True, 'missing_partition_leaf'
    elif any(action_counts[action] < MIN_ACTION_ROOTS for action in legal):
        selected, fallback, reason = root['teacher_action'], True, 'insufficient_action_support'
    elif len({component_id[action] for action in legal}) != 1:
        selected, fallback, reason = root['teacher_action'], True, 'disconnected_required_actions'
    else:
        selected, fallback = None, False
    predicted = {}
    if leaf is not None:
        for action in legal:
            if action_counts[action]:
                vector = list(leaf['coefficients'][action])
                vector[0] += root['immediate_rewards'][action]
                predicted[action] = vector
                work.update(partition_coefficient_component_reads=3,
                            partition_immediate_reward_reads=1, partition_reward_additions=1)
    pairs = {}
    for first, second in combinations(legal, 2):
        if first in predicted and second in predicted and component_id[first] == component_id[second]:
            pairs[_pair_key(first, second)] = [predicted[first][i]-predicted[second][i] for i in range(3)]
            work['partition_predicted_pair_component_subtractions'] += 3
    if selected is None:
        selected, best = legal[0], None
        for action in legal:
            vector = predicted[action]
            value = vector[0]-vector[1]+vector[2]
            work['partition_utility_evaluations'] += 1
            if best is None or value > best+EPSILON:
                selected, best = action, value
    support = dict(action_root_counts=action_counts, pair_root_counts=pair_counts,
                   connected_components=connected, required_actions=legal, complete=not fallback)
    if counts is not None:
        counts.update(work)
    return dict(canonical_action=selected, fallback=fallback, leaf=leaf_id, reason=reason,
                predicted_components=predicted, predicted_pairs=pairs, support=support, work=dict(work))
