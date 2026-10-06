"""No-Monte-Carlo H3 labels for the frozen V174 partition hypothesis.

An explicit exact-data entry point replaces suffix observations with one
enumerated continuation-vector contrast per legal action pair. Design groups
are provenance blocks, not episodes or independent Monte Carlo replicates.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from itertools import combinations

from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4Transform
from . import controlled_predictive_consequence_partition_v172 as estimation
from . import controlled_predictive_utility_partition_v174 as learning
from .controlled_predictive_program_consolidation_v161 import INVERSE, canonical_frame
from .controlled_predictive_consequence_partition_v172 import (
    ACTIONS, EPSILON, MAX_LEAVES, MIN_ACTION_ROOTS, MIN_CHILD_ROOTS, MIN_CHILD_SOURCES,
)

SCHEMA = 'acfqp.exact_h3_learning.v177'
QUERY = 'goal_1_risk_1'
HORIZON = 3
DESIGN_GROUPS = 12
RESTORE_TOLERANCE = 1e-12
MAX_PROBABILITY_DENOMINATOR = 2560


def _utility(vector):
    return vector[0]-vector[1]+vector[2]


def root_from_case(case, ordinal, cohort, counts=None):
    """Observe the current board and immediate rewards without policy labels."""
    board = tuple(case['board'])
    canonical, frame = canonical_frame(board)
    inverse = INVERSE[D4Transform(frame)]
    action_map, rewards = {}, {}
    local = Counter(root_records_read=1, root_tile_reads=16, root_board_transforms=8)
    for action in ACTIONS:
        actual = ground.transform_action_v1(ground.Swipe2048Action(action), inverse).value
        _, score, legal = ground.swipe_board_v1(board, ground.Swipe2048Action(actual))
        local.update(root_action_transports=1, root_ground_swipe_calls=1)
        if legal:
            action_map[action] = actual
            rewards[action] = score/2048.
    legal = [action for action in ACTIONS if action in rewards]
    if not legal:
        raise ValueError('active source/target roots require a legal action')
    fallback, best = legal[0], None
    for action in legal:
        local['fallback_immediate_reward_comparisons'] += 1
        if best is None or rewards[action] > best+EPSILON:
            fallback, best = action, rewards[action]
    if counts is not None:
        counts.update(local)
    return dict(root_id=case['name'], life=0, source_id=f'DESIGN_SOURCE:{ordinal//4:02d}',
        cohort=cohort, ordinal=ordinal, horizon=case['horizon'], board=list(board),
        canonical_board=list(canonical), frame=frame, legal_actions=legal, action_map=action_map,
        immediate_rewards=rewards, fallback_action=fallback, teacher_action=fallback,
        fallback_origin='largest_exact_immediate_reward', work=dict(local))


def _restore_float(value, probability, counts):
    kind = 'probability' if probability else 'reward'
    if probability:
        result = Fraction(value).limit_denominator(MAX_PROBABILITY_DENOMINATOR)
        counts['kernel_probability_recoveries'] += 1
    else:
        result = Fraction(round(float(value)*2048), 2048)
        counts['kernel_reward_recoveries'] += 1
    error = float(abs(Fraction(value)-result))
    counts[kind+'_grid_changed_atoms'] += int(error > 0.)
    counts[kind+'_grid_max_error'] = max(counts[kind+'_grid_max_error'], error)
    if error > RESTORE_TOLERANCE:
        raise ValueError('saved kernel float is outside its native rational grid')
    return result


def _serialize_vector(vector):
    return [[value.numerator, value.denominator] for value in vector]


def exact_action_labels(cells, rows, policy, roots):
    """Enumerate all first actions followed by ONE saved native teacher.

V68 stores [probability,target,reward] floats. V69 stores their native five
rational coordinates. Internal arithmetic is Fraction in either supported
format; terminal CUTOFF contributes neither failure nor success.
"""
    counts = Counter()
    states = {int(state): (int(layer), status) for state, layer, status in cells}
    counts['kernel_cells_read'] += len(cells)
    native_policy = {int(state): action for state, action in policy.items()}
    transitions, actions = {}, {}
    for state, action, outcomes in rows:
        state = int(state)
        converted = []
        for outcome in outcomes:
            if len(outcome) == 3:
                probability, target, reward = outcome
                probability = _restore_float(probability, True, counts)
                reward = _restore_float(reward, False, counts)
            else:
                p_num, p_den, target, r_num, r_den = outcome
                probability, reward = Fraction(p_num, p_den), Fraction(r_num, r_den)
                counts['kernel_rational_outcomes_loaded'] += 1
            target = int(target)
            if states[target][0] != states[state][0]-1:
                raise ValueError('exact continuation must descend one horizon layer')
            converted.append((probability, target, reward))
            counts.update(kernel_outcomes_read=1, horizon_edge_checks=1)
        if not converted or sum(row[0] for row in converted) != 1:
            raise ValueError('restored exact action probability must sum to one')
        if (state, action) in transitions:
            raise ValueError('duplicate exact kernel action row')
        transitions[state, action] = converted
        actions.setdefault(state, []).append(action)
        counts.update(kernel_rows_read=1, probability_mass_checks=1)

    tails = {}

    def action_vector(state, action, prefix):
        vector = [Fraction(0), Fraction(0), Fraction(0)]
        for probability, target, reward in transitions[state, action]:
            child = tails[target]
            vector[0] += probability*(reward+child[0])
            vector[1] += probability*child[1]
            vector[2] += probability*child[2]
            counts[prefix+'_outcomes_evaluated'] += 1
            counts[prefix+'_component_accumulations'] += 3
        counts[prefix+'_action_rows_evaluated'] += 1
        return vector

    for state, (layer, status) in sorted(states.items(), key=lambda item: (item[1][0], item[0])):
        if status != 'ACTIVE':
            tails[state] = [Fraction(0), Fraction(status == 'LOST'), Fraction(status == 'WON')]
            counts['terminal_vector_initializations'] += 1
        else:
            action = native_policy[state]
            counts['teacher_policy_reads'] += 1
            tails[state] = action_vector(state, action, 'teacher')
            counts['teacher_states_evaluated'] += 1
    labels = []
    tolerance = Fraction(1, 10**12)
    for root_index, state in enumerate(roots):
        state = int(state)
        layer, status = states[state]
        legal = [action for action in ACTIONS if action in actions.get(state, ())]
        vectors, rewards, oracle, best = {}, {}, None, None
        for action in legal:
            row_rewards = {outcome[2] for outcome in transitions[state, action]}
            if len(row_rewards) != 1:
                raise ValueError('a concrete first swipe must have deterministic reward')
            rewards[action] = float(next(iter(row_rewards)))
            vectors[action] = action_vector(state, action, 'root')
            value = _utility(vectors[action])
            counts['oracle_utility_evaluations'] += 1
            if best is None or value > best+tolerance:
                oracle, best = action, value
        labels.append(dict(root_index=root_index, root_cell=state, horizon=layer, status=status,
            legal_actions=legal, immediate_rewards=rewards,
            action_components={action: list(map(float, vector)) for action, vector in vectors.items()},
            action_component_fractions={action: _serialize_vector(vector) for action, vector in vectors.items()},
            continuation_components=list(map(float, tails[state])),
            oracle_action=oracle, oracle_components=list(map(float, vectors[oracle] if oracle else tails[state])),
            teacher_action=native_policy.get(state)))
        counts['root_labels_emitted'] += 1
    return dict(labels=labels, counts=dict(counts))


def evaluate_payload(payload, plansquery, root_indices=None):
    roots = payload['roots'] if root_indices is None else [payload['roots'][index] for index in root_indices]
    result = exact_action_labels(payload['cells'], payload['rows'], plansquery['policy'], roots)
    if root_indices is not None:
        for label, index in zip(result['labels'], root_indices):
            label['root_index'] = index
    return result


def _prepare_exact(examples, life, counts):
    examples = list(examples)
    sources = sorted({row['source_id'] for row in examples if row['life'] == life})
    if len(sources) != DESIGN_GROUPS:
        raise ValueError('twelve fixed provenance design groups required')
    folds = [sources[0::2], sources[1::2]]
    source_fold = {source: fold for fold, group in enumerate(folds) for source in group}
    counts['source_fold_assignments'] += len(sources)
    prepared, seen = [], set()
    for raw in examples:
        counts['examples_examined'] += 1
        if raw['life'] != life:
            counts['other_life_examples_excluded'] += 1
            continue
        root_id = raw['root_id']
        if root_id in seen:
            raise ValueError('duplicate exact training root')
        seen.add(root_id)
        board = list(raw['canonical_board'])
        if len(board) != 16:
            raise ValueError('canonical root must have sixteen tile ranks')
        legal = [action for action in ACTIONS if action in raw['legal_actions']]
        if not legal or len(legal) != len(raw['legal_actions']) or set(raw['action_components']) != set(legal):
            raise ValueError('one exact full vector for every distinct legal action required')
        rewards = {action: float(raw['immediate_rewards'][action]) for action in legal}
        full = {action: [float(value) for value in raw['action_components'][action]] for action in legal}
        if any(len(vector) != 3 for vector in full.values()):
            raise ValueError('complete exact reward/failure/success vectors required')
        tails = {action: [full[action][0]-rewards[action], *full[action][1:]] for action in legal}
        pairs = list(combinations(legal, 2))
        weight = 1./len(pairs) if pairs else 0.
        observations, pair_labels = [], []
        for first, second in pairs:
            target = [tails[first][i]-tails[second][i] for i in range(3)]
            observations.append((first, second, weight, target))
            pair_labels.append(dict(actions=[first, second], weight=weight, components=target))
            counts.update(paired_vector_labels=1, paired_component_subtractions=3)
        fit_label = dict(root_id=root_id, source_id=raw['source_id'], legal_actions=legal,
                         label_kind='exact_enumerated_vector', pairs=pair_labels)
        outcome = dict(root_id=root_id, source_id=raw['source_id'], life=life,
            fold=source_fold[raw['source_id']], canonical_board=board, legal_actions=legal,
            immediate_rewards=rewards, action_components=deepcopy(full),
            provenance=deepcopy(raw.get('provenance', {})))
        prepared.append(dict(root_id=root_id, source_id=raw['source_id'], board=board, legal=legal,
            observations=observations, fit_label=fit_label, fold=outcome['fold'], rewards=rewards,
            observed_means=full, training_outcome=outcome))
        counts.update(examples_fitted=1, root_feature_tile_reads=16, legal_action_reads=len(legal),
            immediate_reward_reads=len(legal), exact_action_vector_reads=len(legal),
            label_component_reads=3*len(legal), tail_reward_subtractions=len(legal),
            utility_immediate_reward_loads=len(legal), observed_terminal_action_averages=len(legal))
    if not prepared:
        raise ValueError('same-history exact training roots required')
    return sorted(prepared, key=lambda item: item['root_id']), folds


def _payload(prepared, folds, nodes, groups, leaves, fits, records, fit_counts, search_counts, node_counts, life, mode):
    sources = dict(Counter(item['source_id'] for item in prepared))
    return dict(schema=SCHEMA, life=life, query='risk1', native_teacher_query=QUERY, horizon=HORIZON,
        mode=mode, label_kind='exact_enumerated_vector',
        constants=dict(min_child_roots=MIN_CHILD_ROOTS, min_child_sources=MIN_CHILD_SOURCES,
            min_action_roots=MIN_ACTION_ROOTS, max_leaves=MAX_LEAVES, epsilon=EPSILON,
            discovery_design_groups=DESIGN_GROUPS),
        root_ids=[item['root_id'] for item in prepared], source_ids=sorted(sources), source_folds=folds,
        source_root_counts=sources, nodes=nodes, groups=groups, leaves=leaves, node_fits=fits,
        fit_labels=[deepcopy(item['fit_label']) for item in prepared],
        training_outcomes=[deepcopy(item['training_outcome']) for item in prepared],
        candidate_records=records, fit_counts=dict(fit_counts), utility_search_counts=dict(search_counts),
        node_fit_counts=dict(node_counts))


def fit_exact_partition(examples, life=0):
    """Run the unchanged V174 SOURCE-crossfit search on exact pair labels."""
    fit_counts, search_counts, node_counts = Counter(), Counter(), Counter()
    prepared, folds = _prepare_exact(examples, life, fit_counts)
    source_counts = dict(Counter(item['source_id'] for item in prepared))
    nodes = [dict(node_id=0, kind='leaf', leaf_id=0)]
    active = {0: list(range(len(prepared)))}
    node_indices, records = {0: list(active[0])}, []
    candidates = {0: learning._search_node(prepared, active[0], 0, folds, source_counts, search_counts, records)}
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
        left = [i for i in active[node_id] if prepared[i]['board'][best['cell']] <= best['threshold']]
        right = [i for i in active[node_id] if prepared[i]['board'][best['cell']] > best['threshold']]
        nodes[node_id] = dict(node_id=node_id, kind='split', cell=best['cell'], threshold=best['threshold'],
                             left=left_id, right=right_id, utility_gain=best['score'])
        del active[node_id], candidates[node_id]
        for child_id, indices in ((left_id, left), (right_id, right)):
            nodes.append(dict(node_id=child_id, kind='leaf', leaf_id=child_id))
            active[child_id], node_indices[child_id] = indices, indices
        search_counts['utility_splits_applied'] += 1
        if len(active) < MAX_LEAVES:
            for child_id in (left_id, right_id):
                candidates[child_id] = learning._search_node(prepared, active[child_id], child_id, folds,
                                                           source_counts, search_counts, records)
    fits = {}
    for node in nodes:
        node_id = node['node_id']
        fits[str(node_id)] = dict(leaf_id=node_id, **estimation._fit_leaf(prepared, node_indices[node_id], node_counts))
        node_counts['full_discovery_node_fits'] += 1
    leaves = [deepcopy(fits[str(node_id)]) for node_id in sorted(active)]
    return _payload(prepared, folds, nodes, {}, leaves, fits, records, fit_counts, search_counts,
                    node_counts, life, 'PART_UNPRUNED')


def fit_exact_one(examples, life=0):
    counts, node_counts = Counter(), Counter()
    prepared, folds = _prepare_exact(examples, life, counts)
    leaf = dict(leaf_id=0, **estimation._fit_leaf(prepared, list(range(len(prepared))), node_counts))
    node_counts['full_discovery_node_fits'] += 1
    return _payload(prepared, folds, [], {'ALL': 0}, [leaf], {'0': deepcopy(leaf)}, [],
                    counts, Counter(), node_counts, life, 'ONE_LATE')


def choose_action(payload, root, counts=None):
    """V172 deployment with the same observable-only fallback for both models."""
    observed_root = dict(root, teacher_action=root['fallback_action'])
    decision = estimation.choose_action(payload, observed_root, counts)
    if 'action_map' in root:
        decision['actual_action'] = root['action_map'][decision['canonical_action']]
    return decision
