"""Small conditional action programs fitted only to retained behavior examples."""
from collections import Counter
from copy import deepcopy
from random import Random


SCHEMA = 'acfqp.policy_programs.v140'
ACTIONS = ('DOWN', 'LEFT', 'RIGHT', 'UP')
MAX_DEPTH, MIN_CHILD = 2, 8
PREDICATE_NAMES = (
    'empty_le_2', 'empty_le_4', 'empty_le_8',
    'equal_neighbors_le_0', 'equal_neighbors_le_2', 'equal_neighbors_le_4',
    'max_at_0', 'max_at_3', 'max_at_12', 'max_at_15',
    'max_on_top', 'max_on_bottom', 'max_on_left', 'max_on_right')
NEIGHBORS = tuple((4*r+c, 4*r+c+1) for r in range(4) for c in range(3))+tuple(
    (4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4))
BOUNDARIES = ((0, 1, 2, 3), (12, 13, 14, 15), (0, 4, 8, 12), (3, 7, 11, 15))


def features(board):
    """Return the frozen fourteen predicates; empty cells are never equal tiles."""
    empty = sum(rank == 0 for rank in board)
    equal = sum(board[a] > 0 and board[a] == board[b] for a, b in NEIGHBORS)
    largest = max(board)
    corners = tuple(largest > 0 and board[index] == largest for index in (0, 3, 12, 15))
    edges = tuple(largest > 0 and any(board[index] == largest for index in edge)
        for edge in BOUNDARIES)
    return tuple(empty <= threshold for threshold in (2, 4, 8))+tuple(
        equal <= threshold for threshold in (0, 2, 4))+corners+edges


def rank_actions(board, previous_action, payload):
    """Read a program without fitting, fallback, legality checks or mutation."""
    tree = payload['trees'][ACTIONS.index(previous_action)]
    observed, node = features(board), 0
    while tree[node][0] >= 0:
        node = 2*node+1+int(observed[tree[node][0]])
    return tuple(ACTIONS[index] for index in tree[node][1:])


def fit_programs(examples):
    """Greedy positive mistake-reduction splits with fixed depth and child size."""
    work = Counter(fit_calls=1)
    groups = [[] for _ in ACTIONS]
    for example in examples:
        observed = features(example['board'])
        groups[ACTIONS.index(example['previous_action'])].append(
            (observed, ACTIONS.index(example['action'])))
        work.update(training_examples=1, feature_calls=1, feature_input_cells=16,
            feature_neighbor_pairs=24, feature_predicate_values=14, training_label_encodings=1)

    trees, sample_counts, action_counts, tree_mistakes = [], [], [], []
    for group in groups:
        tree = [[-1, 0, 1, 2, 3] for _ in range(7)]
        samples, histograms = [0]*7, [[0]*4 for _ in range(7)]

        def build(rows, index, depth):
            counts = [0]*4
            for _, action in rows:
                counts[action] += 1
            samples[index], histograms[index] = len(rows), counts
            tree[index][1:] = sorted(range(4), key=lambda action: (-counts[action], action))
            work.update(active_nodes=1, node_sample_visits=len(rows),
                node_histogram_updates=len(rows), action_rankings=1, ranked_action_entries=4)
            mistakes = len(rows)-max(counts)
            if depth == MAX_DEPTH or len(rows) < 2*MIN_CHILD or not mistakes:
                work['active_leaves'] += 1
                return mistakes

            best_gain, best_predicate, best_children = 0, None, None
            for predicate in range(len(PREDICATE_NAMES)):
                children, child_counts = ([], []), ([0]*4, [0]*4)
                for observed, action in rows:
                    branch = int(observed[predicate])
                    children[branch].append((observed, action))
                    child_counts[branch][action] += 1
                work.update(split_candidates=1, split_predicate_reads=len(rows),
                    split_histogram_updates=len(rows))
                if min(map(len, children)) < MIN_CHILD:
                    work['split_candidates_small_child'] += 1
                    continue
                gain = max(child_counts[0])+max(child_counts[1])-max(counts)
                if gain > best_gain:
                    best_gain, best_predicate, best_children = gain, predicate, children
            if best_predicate is None:
                work['active_leaves'] += 1
                return mistakes
            tree[index][0] = best_predicate
            work['chosen_splits'] += 1
            return build(best_children[0], 2*index+1, depth+1)+build(
                best_children[1], 2*index+2, depth+1)

        tree_mistakes.append(build(group, 0, 0))
        trees.append(tree)
        sample_counts.append(samples)
        action_counts.append(histograms)
    work.update(stored_tree_nodes=28, stored_node_integers=140)
    metadata = dict(examples=sum(map(len, groups)), examples_by_previous_action=list(map(len, groups)),
        fit_classification_mistakes=sum(tree_mistakes), tree_fit_mistakes=tree_mistakes,
        node_sample_counts=sample_counts, node_action_counts=action_counts,
        split_nodes=work['chosen_splits'], leaf_nodes=work['active_leaves'], max_depth=MAX_DEPTH,
        min_child=MIN_CHILD, predicate_names=list(PREDICATE_NAMES), randomized=False)
    return dict(schema=SCHEMA, trees=trees, metadata=metadata, work=dict(work))


def randomize_programs(payload, seed):
    """Preserve every predicate and randomize all node rankings uniformly."""
    result, random = deepcopy(payload), Random(seed)
    work = Counter(randomize_calls=1, copied_tree_nodes=28, copied_node_integers=140)
    for tree in result['trees']:
        for node in tree:
            order = list(range(4))
            for index in (3, 2, 1):
                other = random.randrange(index+1)
                order[index], order[other] = order[other], order[index]
                work['random_draws'] += 1
            node[1:] = order
            work['random_action_orders'] += 1
    result['metadata'].update(randomized=True, random_seed=int(seed))
    result['work'] = dict(work)
    return result
