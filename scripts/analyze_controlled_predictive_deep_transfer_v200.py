"""Independent SOURCE transition partitions and deep native policy replay.

No V200 learner or runner mathematics is imported.  The settled public swipe
and D4 board transport supply only the declared 2048 physics; target features,
encoding, planning, learned-row construction and audit decisions are separate.
"""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from acfqp.domains.standard_2048 import Swipe2048Action, swipe_board_v1, transform_board_v1, transform_action_v1
from acfqp.domains.g2048 import D4_ELEMENTS

SCHEMA = 'acfqp.deep_controlled_transfer.v200'
OUTPUT = ROOT/'reports/controlled_predictive_deep_transfer_v200'
ACTIONS = ('DOWN', 'LEFT', 'RIGHT', 'UP')
EPSILON = Fraction(1, 10**12)
SPLIT_EPSILON = 1e-9
GOAL_RANK = 6
QUERIES = dict(reward=dict(reward_weight=1, failure_penalty=0, goal_bonus=0),
    goal=dict(reward_weight=1, failure_penalty=0, goal_bonus=4),
    risk=dict(reward_weight=1, failure_penalty=4, goal_bonus=4))
PAIRS = ((0, 5), (1, 6), (0, 6), (0, 10), (1, 7), (4, 10),
    (5, 11), (2, 8), (3, 12), (5, 14), (6, 13), (2, 15))


def board_features(board):
    result = list(board)
    for row in range(4):
        for column in range(3):
            a, b = board[4*row+column], board[4*row+column+1]
            result.append(int(a > 0 and a == b))
    for row in range(3):
        for column in range(4):
            a, b = board[4*row+column], board[4*(row+1)+column]
            result.append(int(a > 0 and a == b))
    result.extend((board.count(0), max(board)))
    return tuple(result)


def select_action(vectors, query):
    coefficients = [Fraction(str(query[key])) for key in ('reward_weight', 'failure_penalty', 'goal_bonus')]
    winner, best = None, None
    for action in sorted(vectors):
        reward, failure, success = vectors[action]
        value = coefficients[0]*reward-coefficients[1]*failure+coefficients[2]*success
        if winner is None or value > best+EPSILON:
            winner, best = action, value
    return winner


def utility(vector, query):
    return (Fraction(str(query['reward_weight']))*vector[0]
        - Fraction(str(query['failure_penalty']))*vector[1]
        + Fraction(str(query['goal_bonus']))*vector[2])


def terminal(status):
    return (Fraction(0), Fraction(status == 'LOST'), Fraction(status == 'WON'))


def traverse(tree, features):
    while 'feature' in tree:
        tree = tree['left'] if features[tree['feature']] <= tree['threshold'] else tree['right']
    return tree['cell']


def encode(model, board, status, legal, horizon):
    if status == 'WON':
        return 0
    if status == 'LOST':
        return 1
    if horizon == 0:
        return 2
    mask = tuple(legal)
    for record in model['trees'][str(horizon)]:
        if tuple(record['mask']) == mask:
            return traverse(record['tree'], board_features(board))
    return None


def fraction_kernel(payload):
    cells = {state: (horizon, status) for state, horizon, status in payload['cells']}
    rows, actions = {}, defaultdict(list)
    for state, action, outcomes in payload['rows']:
        rows[state, action] = [(Fraction(p, q), child, Fraction(r, s)) for p, q, child, r, s in outcomes]
        actions[state].append(action)
    return cells, rows, {state: tuple(sorted(names)) for state, names in actions.items()}


def plan_model(model, query, work=None):
    work = Counter() if work is None else work
    cells, rows, actions = fraction_kernel(model)
    values, policy, qvectors = {}, {}, {}
    work['abstract_dp_calls'] += 1
    for state in sorted(cells, key=lambda sid: (cells[sid][0], sid)):
        _, status = cells[state]
        work['abstract_dp_cells'] += 1
        if status != 'ACTIVE':
            values[state] = terminal(status)
            continue
        qvalues = {}
        for action in actions[state]:
            vector = [Fraction(0), Fraction(0), Fraction(0)]
            work['abstract_dp_action_rows'] += 1
            for probability, child, reward in rows[state, action]:
                continuation = values[child]
                vector[0] += probability*(reward+continuation[0])
                vector[1] += probability*continuation[1]
                vector[2] += probability*continuation[2]
                work['abstract_dp_outcomes'] += 1
            qvalues[action] = tuple(vector)
            qvectors[state, action] = tuple(vector)
        chosen = select_action(qvalues, query)
        policy[state] = chosen
        values[state] = qvalues[chosen]
    return dict(values=values, policy=policy, qvectors=qvectors)


def _leaf_candidate(indices, features, targets, depth, work):
    """Independent prefix means; the final squared-coordinate sum uses fsum."""
    work['fit_leaf_evaluations'] += 1
    if depth >= 6 or len(indices) < 8:
        return None
    ordered_ids = sorted(indices)
    total = np.zeros(targets.shape[1], dtype=np.float64)
    for index in ordered_ids:
        total += targets[index]
        work['fit_total_component_updates'] += targets.shape[1]
    best = None
    for feature in range(42):
        order = sorted(ordered_ids, key=lambda index: (features[index][feature], index))
        work['fit_feature_sorts'] += 1
        work['fit_feature_values'] += len(indices)
        prefix = np.zeros_like(total)
        for position, index in enumerate(order[:-1], 1):
            prefix += targets[index]
            work['fit_prefix_component_updates'] += targets.shape[1]
            if position < 4 or len(order)-position < 4:
                continue
            threshold = features[index][feature]
            if threshold == features[order[position]][feature]:
                continue
            left_mean = prefix/position
            right_mean = (total-prefix)/(len(order)-position)
            difference = left_mean-right_mean
            gain = position*(len(order)-position)/len(order)*math.fsum(float(value)**2 for value in difference)
            work['fit_split_candidates'] += 1
            work['fit_sse_components'] += targets.shape[1]
            if gain <= SPLIT_EPSILON:
                continue
            key = feature, int(threshold)
            if best is None or gain > best['gain']+SPLIT_EPSILON or (
                    abs(gain-best['gain']) <= SPLIT_EPSILON and key < best['key']):
                best = dict(gain=gain, key=key, feature=feature, threshold=int(threshold),
                    left=order[:position], right=order[position:])
    return best


def _source_encode(model, state, horizon, features, counts):
    counts['encoding_calls'] += 1
    if state['status'] == 'WON':
        return 0
    if state['status'] == 'LOST':
        return 1
    if horizon == 0:
        return 2
    mask = tuple(state['legal'])
    for root in model['trees'][str(horizon)]:
        counts['encoding_mask_comparisons'] += 1
        if tuple(root['mask']) != mask:
            continue
        tree = root['tree']
        while 'feature' in tree:
            counts['encoding_predicates'] += 1
            tree = tree['left'] if features[tree['feature']] <= tree['threshold'] else tree['right']
        return tree['cell']
    return None


def rebuild_model(source, learned=True, work=None):
    """Fit only expected immediate reward and previous-layer cell transitions."""
    work = Counter() if work is None else work
    states = source['states']
    controlled = sorted(source['controlled'])
    members = [sid for sid in controlled if states[sid]['status'] == 'ACTIVE']
    rows, rewards = {}, {}
    counts = Counter(fit_calls=1, source_controlled_state_reads=len(controlled))
    for sid, action, outcomes in source['rows']:
        rows[sid, action] = [(Fraction(p, q), child, Fraction(r, s)) for p, q, child, r, s in outcomes]
        rewards[sid, action] = sum((p*r for p, _, r in rows[sid, action]), Fraction(0))
        counts['source_rows_read'] += 1
        counts['source_outcomes_read'] += len(outcomes)
        counts['source_reward_products'] += len(outcomes)
    needed = set(members)
    for sid in members:
        for action in states[sid]['legal']:
            needed.update(child for _, child, _ in rows[sid, action] if states[child]['status'] == 'ACTIVE')
    features = {sid: board_features(tuple(states[sid]['board'])) for sid in sorted(needed)}
    counts.update(feature_calls=len(needed), feature_tile_reads=16*len(needed),
        feature_equality_checks=24*len(needed), feature_scalar_reductions=32*len(needed))
    model = dict(schema='acfqp.deep_transfer.v200.model', mode='LEARNED' if learned else 'COARSE',
        cells=[[0, 0, 'WON'], [1, 0, 'LOST'], [2, 0, 'CUTOFF']], rows=[], trees={})
    next_id = 3
    for horizon in range(1, 5):
        layer = Counter(fit_tree_layers=1)
        previous = [0, 1, 2]+[sid for sid, layer, status in model['cells'] if layer == horizon-1 and status == 'ACTIVE']
        previous_column = {cell: index for index, cell in enumerate(previous)}
        groups = defaultdict(list)
        # Masks have different action counts, hence different target dimensions.
        layer_trees, layer_leaves = {}, {}
        per_mask_targets = {}
        for sid in members:
            groups[tuple(states[sid]['legal'])].append(sid)
        for mask, ids in sorted(groups.items()):
            targets = np.zeros((len(states), len(ACTIONS)*(len(previous)+1)), dtype=np.float64)
            for sid in ids:
                for action_index, action in enumerate(ACTIONS):
                    layer['label_components'] += len(previous)+1
                    if action not in mask:
                        layer['label_zero_components'] += len(previous)+1
                        continue
                    law = defaultdict(Fraction)
                    for p, child, _ in rows[sid, action]:
                        successor = states[child]
                        destination = _source_encode(model, successor, horizon-1, features.get(child, ()), layer)
                        if destination is None:
                            raise ValueError('SOURCE successor has an unseen legal mask')
                        law[destination] += p
                        layer['label_probability_pushes'] += 1
                    offset = action_index*(len(previous)+1)
                    targets[sid, offset] = float(rewards[sid, action])
                    for cell, p in law.items():
                        targets[sid, offset+1+previous_column[cell]] = float(p)
                    layer['label_action_rows'] += 1
            per_mask_targets[mask] = targets
            layer_trees[mask] = dict(indices=sorted(ids))
            candidate = _leaf_candidate(ids, features, targets, 0, layer) if learned else None
            layer_leaves[mask, ()] = layer_trees[mask], 0, candidate
        if learned:
            while len(layer_leaves) < 32:
                best = None
                for (mask, path), (node, depth, candidate) in sorted(layer_leaves.items()):
                    layer['fit_leaf_candidate_comparisons'] += 1
                    if candidate is None:
                        continue
                    candidate = dict(candidate, global_key=(mask, path, candidate['feature'], candidate['threshold']), node=node, depth=depth)
                    if best is None or candidate['gain'] > best['gain']+SPLIT_EPSILON or (
                            abs(candidate['gain']-best['gain']) <= SPLIT_EPSILON and candidate['global_key'] < best['global_key']):
                        best = candidate
                if best is None:
                    break
                mask, path, feature, threshold = best['global_key']
                node = best['node']
                node.clear()
                node.update(feature=feature, threshold=threshold,
                    left=dict(indices=sorted(best['left'])), right=dict(indices=sorted(best['right'])))
                del layer_leaves[mask, path]
                for bit in (0, 1):
                    child = node['left' if bit == 0 else 'right']
                    child_depth = best['depth']+1
                    candidate = _leaf_candidate(child['indices'], features, per_mask_targets[mask], child_depth, layer)
                    layer_leaves[mask, path+(bit,)] = child, child_depth, candidate
                layer['fit_splits'] += 1
        for (mask, path), (node, _, _) in sorted(layer_leaves.items()):
            ids = node.pop('indices')
            node.update(cell=next_id, members=ids)
            model['cells'].append([next_id, horizon, 'ACTIVE'])
            next_id += 1
        model['trees'][str(horizon)] = [dict(mask=list(mask), tree=tree) for mask, tree in sorted(layer_trees.items())]
        for mask, path in sorted(layer_leaves):
            node = layer_leaves[mask, path][0]
            ids = node['members']
            for action in mask:
                reward = Fraction(0)
                law = defaultdict(Fraction)
                for sid in ids:
                    reward += rewards[sid, action]/len(ids)
                    layer['compiler_member_rows'] += 1
                    layer['compiler_reward_accumulations'] += 1
                    for p, child, _ in rows[sid, action]:
                        successor = states[child]
                        destination = _source_encode(model, successor, horizon-1, features.get(child, ()), layer)
                        law[destination] += p/len(ids)
                        layer['compiler_probability_pushes'] += 1
                model['rows'].append([node['cell'], action, [[p.numerator, p.denominator,
                    destination, reward.numerator, reward.denominator] for destination, p in sorted(law.items())]])
                layer['compiler_rows'] += 1
                layer['compiler_outcomes'] += len(law)
        layer['fit_final_leaves'] += len(layer_leaves)
        counts.update(layer)
        counts.update({f'h{horizon}_{key}': value for key, value in layer.items()})
        counts[f'h{horizon}_fit_states'] = len(members)
        counts[f'h{horizon}_start_leaves'] = len(groups)
    model['fit_counts'] = dict(counts)
    work.update(counts)
    return model


class Native:
    """One board-row cache per case, reused by all horizons/queries/controllers."""
    def __init__(self, work=None, bounds=None):
        self.work = Counter() if work is None else work
        self.boards = {}
        self.moves = {}
        self.rows = {}
        self.oracle_cache = {}
        self.replay_cache = {}
        self.transforms = {}
        self.bounds = bounds or dict(boards=100000, rows=24000, outcomes=200000)

    def classify(self, board):
        board = tuple(board)
        if board in self.boards:
            return self.boards[board]
        if len(self.boards) >= self.bounds['boards']:
            raise RuntimeError('independent native observed-board bound reached')
        self.work['native_board_classifications'] += 1
        if max(board) >= GOAL_RANK:
            result = 'WON', ()
        else:
            moves = []
            for action in ACTIONS:
                moved, score, changed = swipe_board_v1(board, Swipe2048Action(action))
                self.work['native_swipe_calls'] += 1
                if changed:
                    moves.append(action)
                    self.moves[board, action] = moved, score
            result = ('ACTIVE', tuple(moves)) if moves else ('LOST', ())
        self.boards[board] = result
        return result

    def _spawn(self, moved, score):
        empty = [index for index, value in enumerate(moved) if value == 0]
        outcomes = []
        for index in empty:
            for rank, probability in ((1, Fraction(9, 10)), (2, Fraction(1, 10))):
                if self.work['native_spawn_outcomes'] >= self.bounds['outcomes']:
                    raise RuntimeError('independent native support-outcome bound reached')
                child = list(moved)
                child[index] = rank
                outcomes.append((probability/len(empty), tuple(child), Fraction(score, 2048)))
                self.work['native_spawn_outcomes'] += 1
        return tuple(outcomes)

    def outcomes(self, board, action):
        self.classify(board)
        key = tuple(board), action
        if key not in self.rows:
            if len(self.rows) >= self.bounds['rows']:
                raise RuntimeError('independent native support-row bound reached')
            moved, score = self.moves[key]
            self.rows[key] = self._spawn(moved, score)
            self.work['native_support_rows'] += 1
        return self.rows[key]

    def oracle(self, board, horizon, query_name):
        board = tuple(board)
        key = board, horizon, query_name
        if key in self.oracle_cache:
            return self.oracle_cache[key]
        status, legal = self.classify(board)
        self.work['oracle_states'] += 1
        if status != 'ACTIVE' or horizon == 0:
            result = dict(vector=terminal(status), action=None, qvectors={})
        else:
            qvalues = {}
            for action in legal:
                vector = [Fraction(0), Fraction(0), Fraction(0)]
                self.work['oracle_action_rows'] += 1
                for p, child, reward in self.outcomes(board, action):
                    future = self.oracle(child, horizon-1, query_name)['vector']
                    vector[0] += p*(reward+future[0])
                    vector[1] += p*future[1]
                    vector[2] += p*future[2]
                    self.work['oracle_outcomes'] += 1
                qvalues[action] = tuple(vector)
            chosen = select_action(qvalues, QUERIES[query_name])
            result = dict(vector=qvalues[chosen], action=chosen, qvectors=qvalues)
        self.oracle_cache[key] = result
        return result


def own_policy_replay(native, root, horizon, query_name, mode, model=None, plan=None):
    """Receding frozen-model control; abstract estimates never replace outcomes."""
    memo = native.replay_cache
    def visit(board, remaining):
        key = tuple(board), remaining, query_name, mode
        if key in memo:
            return memo[key]
        status, legal = native.classify(board)
        native.work['policy_replay_states'] += 1
        if status != 'ACTIVE' or remaining == 0:
            result = dict(vector=terminal(status), fallback_visits=Fraction(0), fallback_probability=Fraction(0), action=None)
        else:
            fallback = False
            if mode == 'NATIVE_H2':
                chosen = native.oracle(board, min(2, remaining), query_name)['action']
            else:
                depth = min(1, remaining) if mode == 'LEARNED_D1' else remaining
                cell = encode(model, tuple(board), status, legal, depth)
                fallback = cell is None
                chosen = legal[0] if fallback else plan['policy'][cell]
            totals = [Fraction(0), Fraction(0), Fraction(0)]
            fallback_visits = Fraction(int(fallback))
            fallback_probability = Fraction(int(fallback))
            native.work['policy_replay_action_rows'] += 1
            for p, child, reward in native.outcomes(board, chosen):
                future = visit(child, remaining-1)
                totals[0] += p*(reward+future['vector'][0])
                totals[1] += p*future['vector'][1]
                totals[2] += p*future['vector'][2]
                fallback_visits += p*future['fallback_visits']
                if not fallback:
                    fallback_probability += p*future['fallback_probability']
                native.work['policy_replay_outcomes'] += 1
            result = dict(vector=tuple(totals), fallback_visits=fallback_visits,
                fallback_probability=fallback_probability, action=chosen)
        memo[key] = result
        return result
    return visit(tuple(root), horizon)


def source_truth(source, work=None):
    """Read each controlled SOURCE row once against known public native physics."""
    work = Counter() if work is None else work
    native = Native(work, dict(boards=50000, rows=20000, outcomes=250000))
    states = source['states']
    stored = {(sid, action): outcomes for sid, action, outcomes in source['rows']}
    checks = []
    for sid, state in enumerate(states):
        status, legal = native.classify(tuple(state['board']))
        checks.append(dict(name=f'source_state:{sid}', passed=status == state['status'] and list(legal) == state['legal']))
    expected_keys = {(sid, action) for sid in source['controlled'] for action in states[sid]['legal']}
    checks.append(dict(name='source_only_controlled_rows', passed=set(stored) == expected_keys and len(stored) == len(source['rows'])))
    for sid in sorted(source['controlled']):
        state = states[sid]
        board = tuple(state['board'])
        status, legal = native.classify(board)
        for action in legal:
            expected = native.outcomes(board, action)
            actual = [(Fraction(p, q), tuple(states[child]['board']), Fraction(r, s))
                for p, q, child, r, s in stored[sid, action]]
            work['source_native_row_checks'] += 1
            work['source_native_outcome_checks'] += len(actual)
            checks.append(dict(name=f'source_row:{sid}:{action}', passed=tuple(actual) == expected))
    successor_masks = set()
    masks = {tuple(states[sid]['legal']) for sid in source['controlled']}
    for sid, action, outcomes in source['rows']:
        for _, _, child, _, _ in outcomes:
            state = states[child]
            if state['status'] == 'ACTIVE':
                successor_masks.add(tuple(state['legal']))
    checks.append(dict(name='source_successor_mask_closure', passed=successor_masks <= masks))
    return checks


def fixed_roster():
    result = {}
    for split, count, seed_base in (('SOURCE', 32, 200100), ('TARGET', 24, 200200)):
        records = []
        for index in range(count):
            seed = seed_base+index
            rng = random.Random(seed)
            board = [rng.randint(1, 4) for _ in range(16)]
            first, second = PAIRS[index % len(PAIRS)]
            board[first] = board[second] = 5
            if index % 2:
                board[rng.choice([cell for cell in range(16) if cell not in (first, second)])] = 0
            records.append(dict(root_id=f'v200_{split.lower()}_{index:02d}', seed=seed, board=board))
        result[split] = records
    return result


def source_framing(source, cases):
    """Rebuild acquisition IDs/controlled order from retained truth-checked rows.

    This verifies SOURCE provenance without making another native support call.
    Extra TARGET observations or controlled rows cannot enter a source payload.
    """
    states = source['states']
    rows = {(sid, action): outcomes for sid, action, outcomes in source['rows']}
    observed, lookup, row_order = [], {}, []
    def intern(board):
        board = tuple(board)
        if board not in lookup:
            lookup[board] = len(observed)
            observed.append(board)
        return lookup[board]
    root_ids = [intern(case['board']) for case in cases]
    controlled, frontier = set(), sorted(set(root_ids))
    def expand(sid):
        following = set()
        for action in states[sid]['legal']:
            row_order.append((sid, action))
            for _, _, child, _, _ in rows[sid, action]:
                if intern(states[child]['board']) != child:
                    raise ValueError('retained SOURCE successor ID breaks acquisition order')
                following.add(child)
        return following
    for _ in range(2):
        following = set()
        for sid in frontier:
            if states[sid]['status'] == 'ACTIVE' and sid not in controlled:
                controlled.add(sid)
                following.update(expand(sid))
        frontier = sorted(following)
    augmentations = 0
    while True:
        masks = {tuple(states[sid]['legal']) for sid in controlled}
        missing = next((sid for sid in range(len(observed)) if states[sid]['status'] == 'ACTIVE'
            and tuple(states[sid]['legal']) not in masks), None)
        if missing is None:
            break
        controlled.add(missing)
        expand(missing)
        augmentations += 1
    return (root_ids == source['root_ids'] and observed == [tuple(state['board']) for state in states]
        and sorted(controlled) == source['controlled'] and augmentations == source['mask_augmentations']
        and row_order == [(sid, action) for sid, action, _ in source['rows']])


def deep_native_support(native, roots):
    """D4 unions exclude horizon1, whose distinctions cannot prove deep reuse."""
    visited, raw_states, raw_pairs = set(), set(), set()
    canonical_states, canonical_pairs = set(), set()
    layers = defaultdict(lambda: dict(raw_states=set(), raw_pairs=set(), canonical_states=set(), canonical_pairs=set()))
    def visit(board, horizon):
        key = tuple(board), horizon
        if key in visited:
            return
        visited.add(key)
        status, legal = native.classify(board)
        if status != 'ACTIVE' or horizon <= 1:
            return
        if horizon >= 2:
            if tuple(board) not in native.transforms:
                native.transforms[tuple(board)] = [transform_board_v1(tuple(board), transform) for transform in D4_ELEMENTS]
                native.work['native_benchmark_board_transforms'] += len(D4_ELEMENTS)
            images = native.transforms[tuple(board)]
            representative = min(images)
            raw_states.add((horizon, tuple(board)))
            canonical_states.add((horizon, representative))
            layers[horizon]['raw_states'].add(tuple(board))
            layers[horizon]['canonical_states'].add(representative)
            for action in legal:
                transported = [transform_action_v1(Swipe2048Action(action), transform).value for transform in D4_ELEMENTS]
                native.work['native_benchmark_action_transports'] += len(transported)
                pair = min(zip(images, transported))
                raw_pairs.add((horizon, tuple(board), action))
                canonical_pairs.add((horizon, pair[0], pair[1]))
                layers[horizon]['raw_pairs'].add((tuple(board), action))
                layers[horizon]['canonical_pairs'].add(pair)
        for action in legal:
            native.work['native_benchmark_graph_row_visits'] += 1
            for _, child, _ in native.outcomes(board, action):
                visit(child, horizon-1)
    for board, horizon in roots:
        visit(tuple(board), horizon)
    return dict(raw_states=raw_states, raw_pairs=raw_pairs, canonical_states=canonical_states,
        canonical_pairs=canonical_pairs, layers=layers)


def benchmark_counts(keys, horizon):
    return dict(layers={str(h): dict(active_states=sum(key[0] == h for key in keys['raw_states']),
        action_rows=sum(key[0] == h for key in keys['raw_pairs'])) for h in range(2, horizon+1)},
        D4_states=len(keys['canonical_states']), D4_rows=len(keys['canonical_pairs']))


def packed(vector, query, action=None):
    return dict(components=[float(value) for value in vector], component_fractions=[str(value) for value in vector],
        utility=float(utility(vector, query)), action=action)


def step_diagnostic(native, board, horizon, model):
    status, legal = native.classify(board)
    if status != 'ACTIVE':
        return None
    root_cell = encode(model, tuple(board), status, legal, horizon)
    if root_cell is None:
        return None
    _, learned_rows, _ = fraction_kernel(model)
    result = {}
    for action in legal:
        actual_reward = Fraction(0)
        actual_law = defaultdict(Fraction)
        for probability, child, reward in native.outcomes(board, action):
            child_status, child_legal = native.classify(child)
            destination = encode(model, child, child_status, child_legal, horizon-1)
            actual_law[-1 if destination is None else destination] += probability
            actual_reward += probability*reward
            native.work['step_diagnostic_outcomes'] += 1
        predicted_law = {child: probability for probability, child, _ in learned_rows[root_cell, action]}
        predicted_reward = sum((p*r for p, _, r in learned_rows[root_cell, action]), Fraction(0))
        coordinates = set(actual_law)|set(predicted_law)
        tv = sum((abs(actual_law.get(child, Fraction(0))-predicted_law.get(child, Fraction(0))) for child in sorted(coordinates)), Fraction(0))/2
        result[action] = dict(reward_error=float(abs(actual_reward-predicted_reward)), successor_tv=float(tv),
            unknown_successor_mass=float(actual_law.get(-1, Fraction(0))))
    return result


def reconstruct_target(case, models, plans, work=None):
    work = Counter() if work is None else work
    native = Native(work)
    board = tuple(case['board'])
    evaluations = []
    for horizon in (3, 4):
        for name, query in QUERIES.items():
            oracle = native.oracle(board, horizon, name)
            arms = {}
            status, legal = native.classify(board)
            for mode in ('COARSE', 'LEARNED', 'LEARNED_D1', 'NATIVE_H2'):
                model_name = 'COARSE' if mode == 'COARSE' else 'LEARNED'
                replayed = own_policy_replay(native, board, horizon, name, mode,
                    models[model_name], plans[model_name][name])
                if mode == 'NATIVE_H2':
                    short = native.oracle(board, min(2, horizon), name)
                    prediction = packed(short['vector'], query, short['action'])
                else:
                    depth = 1 if mode == 'LEARNED_D1' else horizon
                    cell = encode(models[model_name], board, status, legal, depth)
                    plan = plans[model_name][name]
                    prediction = None if cell is None else packed(plan['values'][cell], query, plan['policy'].get(cell))
                arms[mode] = dict(predicted=prediction, actual=packed(replayed['vector'], query, replayed['action']),
                    root_action=replayed['action'], regret=float(utility(oracle['vector'], query)-utility(replayed['vector'], query)),
                    fallback_probability=float(replayed['fallback_probability']), fallback_probability_fraction=str(replayed['fallback_probability']),
                    expected_fallback_visits=float(replayed['fallback_visits']), expected_fallback_visits_fraction=str(replayed['fallback_visits']))
            reference = packed(oracle['vector'], query, oracle['action'])
            reference.update(action_vectors={action: [float(value) for value in vector] for action, vector in oracle['qvectors'].items()},
                action_vector_fractions={action: [str(value) for value in vector] for action, vector in oracle['qvectors'].items()})
            evaluations.append(dict(horizon=horizon, query=name, oracle=reference, arms=arms))
    keys, deep = {}, {}
    for horizon in (3, 4):
        keys[str(horizon)] = deep_native_support(native, [(board, horizon)])
        deep[str(horizon)] = benchmark_counts(keys[str(horizon)], horizon)
    steps = {str(h): step_diagnostic(native, board, h, models['LEARNED']) for h in (3, 4)}
    statuses = Counter(status for status, _ in native.boards.values())
    record = dict(**case, evaluations=evaluations, native_deep=deep,
        native_status_counts={status: statuses[status] for status in ('ACTIVE', 'WON', 'LOST')}, step_diagnostics=steps)
    return record, keys


def decision_summary(records, models, benchmark):
    """Independent four-condition arithmetic from all fixed roots and queries."""
    def average(values):
        values = list(values)
        return math.fsum(values)/len(values)
    def preference_change(old, new, old_query, new_query):
        old_action, new_action = old['action'], new['action']
        if old_action == new_action:
            return False
        previous = {action: tuple(Fraction(x) for x in vector) for action, vector in old['action_vector_fractions'].items()}
        current = {action: tuple(Fraction(x) for x in vector) for action, vector in new['action_vector_fractions'].items()}
        alternatives = [utility(vector, QUERIES[old_query]) for action, vector in previous.items() if action != old_action]
        return bool(alternatives and utility(previous[old_action], QUERIES[old_query])-max(alternatives) > Fraction(1, 10**10)
            and utility(current[new_action], QUERIES[new_query])-utility(current[old_action], QUERIES[new_query]) > Fraction(1, 100))
    changed, risk_changed = [], []
    for record in records:
        oracle = {row['query']: row['oracle'] for row in record['evaluations'] if row['horizon'] == 4}
        if any(preference_change(oracle['reward'], oracle[name], 'reward', name) for name in ('goal', 'risk')):
            changed.append(record['root_id'])
        if preference_change(oracle['goal'], oracle['risk'], 'goal', 'risk'):
            risk_changed.append(record['root_id'])
    statuses = benchmark['terminal_support_counts']
    informative = len(changed) >= 4 and bool(risk_changed) and statuses['WON'] > 0 and statuses['LOST'] > 0
    horizons = {}
    for horizon in (3, 4):
        rows = [row for record in records for row in record['evaluations'] if row['horizon'] == horizon]
        differences = {mode: average(row['arms']['LEARNED']['actual']['utility']-row['arms'][mode]['actual']['utility'] for row in rows)
            for mode in ('COARSE', 'LEARNED_D1', 'NATIVE_H2')}
        regret = average(row['arms']['LEARNED']['regret'] for row in rows)
        complete_predictions = all(row['arms']['LEARNED']['predicted'] is not None for row in rows)
        errors = [average(abs(row['arms']['LEARNED']['predicted']['components'][k]-row['arms']['LEARNED']['actual']['components'][k])
            for row in rows) for k in range(3)] if complete_predictions else None
        fallback = max(row['arms']['LEARNED']['expected_fallback_visits'] for row in rows)
        cells = {cell for cell, layer, status in models['LEARNED']['cells'] if status == 'ACTIVE' and 2 <= layer <= horizon}
        nrows = sum(cell in cells for cell, _, _ in models['LEARNED']['rows'])
        baseline = benchmark[str(horizon)]
        cell_reduction = 1-len(cells)/baseline['D4_states'] if baseline['D4_states'] else 0.
        row_reduction = 1-nrows/baseline['D4_rows'] if baseline['D4_rows'] else 0.
        horizons[str(horizon)] = dict(root_query_records=len(rows), learned_mean_regret=regret,
            learned_max_regret=max(row['arms']['LEARNED']['regret'] for row in rows),
            learned_mean_absolute_prediction_errors=errors, predictions_complete=complete_predictions,
            learned_max_expected_fallback_visits=fallback, learned_minus=differences,
            deployed_deep_active_cells=len(cells), deployed_deep_action_rows=nrows,
            d4_deep_active_cells=baseline['D4_states'], d4_deep_action_rows=baseline['D4_rows'],
            deep_cell_reduction=cell_reduction, deep_row_reduction=row_reduction,
            deep_reuse_pass=cell_reduction >= .2 and row_reduction >= .2,
            quality_pass=complete_predictions and regret <= .05 and max(errors) <= .05
                and differences['NATIVE_H2'] >= -.01 and fallback <= 1e-12,
            added_depth_pass=differences['COARSE'] >= .01 and differences['LEARNED_D1'] >= .01,
            per_query={name: dict(learned_mean_regret=average(row['arms']['LEARNED']['regret'] for row in rows if row['query'] == name),
                learned_minus={mode: average(row['arms']['LEARNED']['actual']['utility']-row['arms'][mode]['actual']['utility']
                    for row in rows if row['query'] == name) for mode in ('COARSE', 'LEARNED_D1', 'NATIVE_H2')}) for name in QUERIES})
    conditions = dict(TASK=informative, DEEP_REUSE=all(row['deep_reuse_pass'] for row in horizons.values()),
        QUALITY=all(row['quality_pass'] for row in horizons.values()), ADDED_DEPTH=all(row['added_depth_pass'] for row in horizons.values()))
    complete = len(records) == 24 and all(row['root_query_records'] == 72 for row in horizons.values())
    advance = complete and all(conditions.values())
    decision = ('RESUME_BOUNDED_LIFECYCLE' if advance else 'CLOSE_PARTITION_HYPOTHESIS' if informative and complete
        else 'TASK_NOT_INFORMATIVE' if complete else 'INCOMPLETE')
    return dict(schema='acfqp.deep_transfer.v200.summary', complete=complete,
        task=dict(reward_preference_changed_cases=changed, goal_to_risk_changed_cases=risk_changed,
            terminal_support_counts=statuses, informative=informative), per_horizon=horizons,
        conditions=conditions, advance=advance, decision=decision)


def planning_counts(model):
    nrows = len(model['rows'])
    outcomes = sum(len(row) for _, _, row in model['rows'])
    return dict(planning_compile_calls=1, planning_row_reads=nrows, planning_outcome_reads=outcomes,
        planning_query_calls=3, planning_cell_values=3*len(model['cells']), planning_successor_vectors=3*outcomes,
        planning_component_accumulations=9*outcomes, planning_action_values=3*nrows,
        utility_calls=3*nrows, utility_component_reads=9*nrows, utility_action_comparisons=3*nrows)


def source_acquisition_counts(source):
    nrows = len(source['rows'])
    outcomes = sum(len(row) for _, _, row in source['rows'])
    statuses = Counter(state['status'] for state in source['states'])
    result = dict(observation_requests=32+outcomes, observation_memo_hits=32+outcomes-len(source['states']),
        board_maximum_scans=len(source['states']), native_swipe_calls=4*(len(source['states'])-statuses['WON']),
        observed_boards=len(source['states']), support_row_requests=nrows, support_row_attempts=nrows,
        post_swipe_empty_scans=nrows, reward_normalizations=nrows, support_outcomes=outcomes,
        spawn_board_constructions=outcomes, probability_fraction_constructions=outcomes, support_rows=nrows)
    result.update({'status_'+status: count for status, count in statuses.items()})
    if source['mask_augmentations']:
        result['source_mask_augmentations'] = source['mask_augmentations']
    return {name: value for name, value in result.items() if value}


def model_counts(model):
    def size(node):
        if 'cell' in node:
            return 1, 1
        left, right = size(node['left']), size(node['right'])
        return 1+left[0]+right[0], left[1]+right[1]
    layers = {}
    cell_h = {cell: h for cell, h, _ in model['cells']}
    for h in range(1, 5):
        tree_sizes = [size(record['tree']) for record in model['trees'][str(h)]]
        rows = [row for row in model['rows'] if cell_h[row[0]] == h]
        layers[str(h)] = dict(active_cells=sum(layer == h and status == 'ACTIVE' for _, layer, status in model['cells']),
            action_rows=len(rows), outcomes=sum(len(row[2]) for row in rows), tree_nodes=sum(x for x, _ in tree_sizes),
            tree_leaves=sum(y for _, y in tree_sizes))
    return dict(layers=layers, serialized_bytes=len((json.dumps(model, ensure_ascii=False, separators=(',', ':'))+'\n').encode()),
        feature_columns=42, terminal_cells=3)


def matches(actual, expected):
    if isinstance(expected, float):
        return isinstance(actual, (float, int)) and math.isfinite(actual) and abs(actual-expected) <= 1e-10*(1+abs(expected))
    if isinstance(expected, dict):
        return isinstance(actual, dict) and set(actual) == set(expected) and all(matches(actual[key], value) for key, value in expected.items())
    if isinstance(expected, (list, tuple)):
        return isinstance(actual, (list, tuple)) and len(actual) == len(expected) and all(matches(a, b) for a, b in zip(actual, expected))
    return actual == expected


def analyze(directory=OUTPUT):
    directory = Path(directory)
    begun = perf_counter()
    work, checks = Counter(), []
    def read(name):
        raw = (directory/name).read_bytes()
        work['retained_files_read'] += 1
        work['retained_bytes_read'] += len(raw)
        return json.loads(raw)
    def check(name, passed):
        checks.append(dict(name=name, passed=bool(passed)))
    result = dict(schema='acfqp.deep_transfer.v200.analysis', complete=False, valid=False, checks=checks)
    try:
        run = read('run.json')
        cases, source = read('cases.json'), read('source.json')
        models = {name: read('models/'+name+'.json') for name in ('COARSE', 'LEARNED')}
        saved_plans, saved_model_counts = read('plans.json'), read('model_counts.json')
        target, benchmark, summary = read('target_results.json')['records'], read('benchmark.json'), read('summary.json')
        check('complete_main', run['status'] == 'complete' and run['completed_targets'] == 24)
        check('fixed_roster', cases == fixed_roster())
        check('no_inherited_teacher_inputs', read('input_manifest.json') == [])
        phases = run['phase_history']
        check('frozen_phase_order', [phase['phase'] for phase in phases] == [
            'protocol_frozen', 'source_acquired', 'models_frozen', 'target_complete', 'complete'])
        check('no_target_queries_before_freeze', all(phase['target_support_rows'] == phase['target_support_outcomes'] == 0 for phase in phases[:3]))
        check('no_random_samples_teacher_loads_native_updates', all(run[name] == 0 for name in (
            'new_random_samples', 'new_teacher_loads', 'new_native_weight_updates')))
        truth = source_truth(source, work)
        check('source_native_states', all(row['passed'] for row in truth if row['name'].startswith('source_state:')))
        check('source_native_rows', all(row['passed'] for row in truth if row['name'].startswith('source_row:')))
        check('source_controlled_rows_only', next(row['passed'] for row in truth if row['name'] == 'source_only_controlled_rows'))
        check('source_mask_closure', next(row['passed'] for row in truth if row['name'] == 'source_successor_mask_closure'))
        check('source_acquisition_provenance', source_framing(source, cases['SOURCE']))
        check('source_acquisition_counts', run['costs']['source_acquisition']['counts'] == source_acquisition_counts(source))
        plans = {}
        for mode in models:
            rebuilt = rebuild_model(source, mode == 'LEARNED', work)
            check('source_model:'+mode, models[mode] == rebuilt)
            check('learning_counts:'+mode, run['costs']['learning_'+mode]['counts'] == rebuilt['fit_counts'])
            check('model_counts:'+mode, saved_model_counts[mode] == model_counts(models[mode]))
            plans[mode] = {name: plan_model(models[mode], query, work) for name, query in sorted(QUERIES.items())}
            expected = {name: dict(values={str(cell): [str(value) for value in vector] for cell, vector in plan['values'].items()},
                policy={str(cell): action for cell, action in plan['policy'].items()}) for name, plan in plans[mode].items()}
            check('abstract_plans:'+mode, saved_plans[mode] == expected)
            check('abstract_planning_counts:'+mode, run['costs']['abstract_dp_'+mode]['counts'] == planning_counts(models[mode]))
        unions = {str(h): {name: set() for name in ('raw_states', 'raw_pairs', 'canonical_states', 'canonical_pairs')} for h in (3, 4)}
        statuses, reconstructed = Counter(), []
        check('target_fixed_order', [row['root_id'] for row in target] == [row['root_id'] for row in cases['TARGET']])
        for case, saved in zip(cases['TARGET'], target):
            case_work = Counter()
            rebuilt, keys = reconstruct_target(case, models, plans, case_work)
            reconstructed.append(rebuilt)
            check('target_native_policy:'+case['root_id'], matches({key: saved[key] for key in rebuilt}, rebuilt))
            check('target_native_work:'+case['root_id'], saved['costs']['native']['observed_boards'] == case_work['native_board_classifications']
                and saved['costs']['native']['native_swipe_calls'] == case_work['native_swipe_calls']
                and saved['costs']['native']['support_rows'] == case_work['native_support_rows']
                and saved['costs']['native']['support_outcomes'] == case_work['native_spawn_outcomes'])
            for h in (3, 4):
                for name in unions[str(h)]:
                    unions[str(h)][name].update(keys[str(h)][name])
            statuses.update(rebuilt['native_status_counts'])
            work.update(case_work)
        expected_benchmark = {str(h): benchmark_counts(unions[str(h)], h) for h in (3, 4)}
        expected_benchmark['terminal_support_counts'] = {status: statuses[status] for status in ('WON', 'LOST', 'ACTIVE')}
        check('native_deep_union', benchmark == expected_benchmark)
        expected_summary = decision_summary(reconstructed, models, expected_benchmark)
        check('independent_four_conditions', matches(summary, expected_summary))
        check('target_acquisition_totals', run['target_support_rows'] == sum(row['costs']['native']['support_rows'] for row in target)
            and run['target_support_outcomes'] == sum(row['costs']['native']['support_outcomes'] for row in target))
        result.update(complete=True, valid=all(row['passed'] for row in checks), independently_reconstructed_targets=len(reconstructed),
            conditions=expected_summary['conditions'], advance=expected_summary['advance'])
    except Exception as error:
        result['failure'] = dict(type=type(error).__name__, message=str(error))
    result.update(costs=dict(work), seconds=perf_counter()-begun)
    (directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, default=OUTPUT)
    result = analyze(parser.parse_args().directory)
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], checks=len(result['checks']))), flush=True)
    raise SystemExit(0 if result['valid'] and result['complete'] else 1)


if __name__ == '__main__':
    main()
