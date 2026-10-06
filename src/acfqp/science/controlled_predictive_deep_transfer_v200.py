"""Bounded learned conditions from stationary controlled one-step SOURCE rows.

Trees use 42 fixed board features, rather than board identities.  Every horizon
fits all controlled ACTIVE SOURCE states; neither returns nor target rows enter
the labels.  Native rational rows retain the uniformly averaged immediate
reward on every pushed successor outcome.

``action_values`` and ``choose_action`` expose the same exact Bellman and
selection law used by ``plan_model`` for runner witnesses.  Optional counters
are mutable mappings of logical operation names to integer amounts.
"""
from collections import Counter, defaultdict
from fractions import Fraction
from math import fsum

HORIZONS = (1, 2, 3, 4)
ACTIONS = ("DOWN", "LEFT", "RIGHT", "UP")
MAX_LEAVES = 32
MAX_DEPTH = 6
MIN_CHILD = 4
GAIN_EPS = 1e-9
UTILITY_EPS = Fraction(1, 10**12)
TERMINALS = {"WON": 0, "LOST": 1, "CUTOFF": 2}


def _add(counts, key, amount=1):
    if counts is not None:
        counts[key] = counts.get(key, 0) + amount


def board_features(board, counts=None):
    """Ranks, horizontal equality, vertical equality, empties, maximum rank.

    Equalities are positive-tile equalities.  Horizontal pairs are ordered by
    row then left column; vertical pairs by top row then column.
    """
    if len(board) != 16:
        raise ValueError("a V200 board has 16 ranks")
    ranks = tuple(board)
    horizontal = tuple(int(ranks[4*r+c] > 0 and ranks[4*r+c] == ranks[4*r+c+1])
                       for r in range(4) for c in range(3))
    vertical = tuple(int(ranks[4*r+c] > 0 and ranks[4*r+c] == ranks[4*(r+1)+c])
                     for r in range(3) for c in range(4))
    _add(counts, "feature_calls")
    _add(counts, "feature_tile_reads", 16)
    _add(counts, "feature_equality_checks", 24)
    _add(counts, "feature_scalar_reductions", 32)
    return ranks + horizontal + vertical + (ranks.count(0), max(ranks))


def _route(tree, features, counts):
    while "cell" not in tree:
        _add(counts, "encoding_predicates")
        tree = tree["left" if features[tree["feature"]] <= tree["threshold"] else "right"]
    return tree["cell"]


def _encode_features(payload, features, h, status, legal, counts):
    _add(counts, "encoding_calls")
    if status in TERMINALS:
        return TERMINALS[status]
    if status != "ACTIVE":
        raise ValueError("unknown V200 state status")
    if h == 0:
        return 2
    if h not in HORIZONS:
        raise ValueError("V200 horizon must be 0 through 4")
    mask = tuple(legal)
    for root in payload["trees"][str(h)]:
        _add(counts, "encoding_mask_comparisons")
        if tuple(root["mask"]) == mask:
            return _route(root["tree"], features, counts)
    return None


def encode(payload, board, h, status, legal, counts=None):
    """Route a board; an unseen ACTIVE legal mask returns ``None``.

    Terminal events are global cells.  An ACTIVE board at horizon zero is the
    CUTOFF cell, so terminal and cutoff encoding do not evaluate board features.
    """
    features = board_features(board, counts) if status == "ACTIVE" and h else ()
    return _encode_features(payload, features, h, status, legal, counts)


def _prefer(gain, key, best):
    return (best is None or gain > best[0] + GAIN_EPS
            or (abs(gain-best[0]) <= GAIN_EPS and key < best[1]))


def _best_split(members, features, targets, mask, path, depth, counts):
    _add(counts, "fit_leaf_evaluations")
    if depth >= MAX_DEPTH or len(members) < 2*MIN_CHILD:
        return None
    size, dimensions = len(members), len(targets[members[0]])
    totals = [0.0]*dimensions
    for state in sorted(members):
        for component, value in enumerate(targets[state]):
            totals[component] += value
        _add(counts, "fit_total_component_updates", dimensions)
    best = None
    for feature in range(42):
        ordered = sorted(members, key=lambda state: (features[state][feature], state))
        _add(counts, "fit_feature_sorts")
        _add(counts, "fit_feature_values", size)
        prefix = [0.0]*dimensions
        for index, state in enumerate(ordered[:-1]):
            for component, value in enumerate(targets[state]):
                prefix[component] += value
            _add(counts, "fit_prefix_component_updates", dimensions)
            left_size, right_size = index+1, size-index-1
            threshold = features[state][feature]
            if (left_size < MIN_CHILD or right_size < MIN_CHILD
                    or threshold == features[ordered[index+1]][feature]):
                continue
            # This is the float64 decrease in total within-leaf SSE.  Totals
            # use SOURCE ID order; prefixes use (feature value, SOURCE ID).
            gain = left_size*right_size/size * fsum(
                (prefix[c]/left_size-(totals[c]-prefix[c])/right_size)**2
                for c in range(dimensions))
            _add(counts, "fit_split_candidates")
            _add(counts, "fit_sse_components", dimensions)
            key = (mask, path, feature, threshold)
            if gain > GAIN_EPS and _prefer(gain, key, best):
                best = (gain, key, feature, threshold,
                        ordered[:left_size], ordered[left_size:])
    return best


def _fit_trees(groups, features, targets, mode, next_cell, h, counts):
    roots, leaves = [], {}
    _add(counts, "fit_tree_layers")
    for mask, members in sorted(groups.items()):
        tree = {"members": sorted(members)}
        roots.append({"mask": list(mask), "tree": tree})
        key = (mask, ())
        candidate = (_best_split(members, features, targets, mask, (), 0, counts)
                     if mode == "LEARNED" else None)
        leaves[key] = (tree, candidate)
    if len(leaves) > MAX_LEAVES:
        raise ValueError("observed legal masks exceed the V200 leaf bound")
    while mode == "LEARNED" and len(leaves) < MAX_LEAVES:
        selected = None
        for key in sorted(leaves):
            candidate = leaves[key][1]
            _add(counts, "fit_leaf_candidate_comparisons")
            if candidate is not None and _prefer(candidate[0], candidate[1], selected):
                selected = candidate
        if selected is None:
            break
        _, (mask, path, _, _), feature, threshold, left, right = selected
        tree, _ = leaves.pop((mask, path))
        left_tree, right_tree = {"members": sorted(left)}, {"members": sorted(right)}
        tree.clear()
        tree.update(feature=feature, threshold=threshold, left=left_tree, right=right_tree)
        for bit, child, members in ((0, left_tree, left), (1, right_tree, right)):
            child_path = path+(bit,)
            leaves[mask, child_path] = (
                child, _best_split(members, features, targets, mask, child_path, len(child_path), counts))
        _add(counts, "fit_splits")
    cells, member_cells = [], {}
    for (mask, path), (tree, _) in sorted(leaves.items()):
        tree["cell"] = next_cell
        cells.append([next_cell, h, "ACTIVE"])
        for state in tree["members"]:
            member_cells[state] = next_cell
        next_cell += 1
    _add(counts, "fit_final_leaves", len(leaves))
    return roots, cells, member_cells, next_cell


def _source_rows(source, counts):
    states = source["states"]
    controlled = sorted(source["controlled"])
    if len(controlled) != len(set(controlled)):
        raise ValueError("controlled SOURCE IDs must be unique")
    members = [state for state in controlled if states[state]["status"] == "ACTIVE"]
    _add(counts, "source_controlled_state_reads", len(controlled))
    groups = defaultdict(list)
    for state in members:
        mask = tuple(states[state]["legal"])
        if not mask or mask != tuple(sorted(set(mask))):
            raise ValueError("controlled ACTIVE SOURCE legal actions must be sorted and nonempty")
        groups[mask].append(state)
    rows, rewards = {}, {}
    for state, action, outcomes in source["rows"]:
        _add(counts, "source_rows_read")
        key = (state, action)
        if key in rows:
            raise ValueError("duplicate controlled SOURCE state-action row")
        row, reward, mass = [], Fraction(0), Fraction(0)
        for pn, pd, successor, rn, rd in outcomes:
            probability, immediate = Fraction(pn, pd), Fraction(rn, rd)
            if probability <= 0:
                raise ValueError("controlled SOURCE outcomes need positive probability")
            following = states[successor]
            if following["status"] == "ACTIVE" and tuple(following["legal"]) not in groups:
                raise ValueError("SOURCE successor legal mask has no controlled state")
            row.append((probability, successor))
            reward += probability*immediate
            mass += probability
            _add(counts, "source_outcomes_read")
            _add(counts, "source_reward_products")
        if mass != 1:
            raise ValueError("controlled SOURCE row probability must sum to one")
        rows[key], rewards[key] = row, reward
    for mask, group in groups.items():
        for state in group:
            for action in mask:
                if (state, action) not in rows:
                    raise ValueError("missing controlled SOURCE legal action row")
    return states, members, groups, rows, rewards


def _successor_cell(payload, states, features, successor, previous_h, counts):
    state = states[successor]
    cell = _encode_features(payload, features.get(successor, ()), previous_h,
                            state["status"], state["legal"], counts)
    if cell is None:
        raise ValueError("SOURCE successor legal mask has no controlled state")
    return cell


def fit_model(source, mode="LEARNED"):
    """Learn h=1..4 cells and exact uniform SOURCE-member transition rows."""
    if mode not in ("LEARNED", "COARSE"):
        raise ValueError("V200 mode must be LEARNED or COARSE")
    counts = Counter(fit_calls=1)
    states, members, groups, rows, rewards = _source_rows(source, counts)
    needed = set(members)
    for state in members:
        for action in states[state]["legal"]:
            needed.update(successor for _, successor in rows[state, action]
                          if states[successor]["status"] == "ACTIVE")
    features = {state: board_features(states[state]["board"], counts) for state in sorted(needed)}
    payload = dict(schema="acfqp.deep_transfer.v200.model", mode=mode, trees={},
                   cells=[[0, 0, "WON"], [1, 0, "LOST"], [2, 0, "CUTOFF"]], rows=[])
    next_cell = 3
    for h in HORIZONS:
        layer_counts = Counter()
        previous_cells = [0, 1, 2]+[cell for cell, layer, _ in payload["cells"] if layer == h-1 and layer > 0]
        targets = {}
        for state in members:
            target = []
            for action in ACTIONS:
                if action not in states[state]["legal"]:
                    target.extend([0.0]*(1+len(previous_cells)))
                    _add(layer_counts, "label_zero_components", 1+len(previous_cells))
                    _add(layer_counts, "label_components", 1+len(previous_cells))
                    continue
                pushed = defaultdict(Fraction)
                for probability, successor in rows[state, action]:
                    cell = _successor_cell(payload, states, features, successor, h-1, layer_counts)
                    pushed[cell] += probability
                    _add(layer_counts, "label_probability_pushes")
                target.append(float(rewards[state, action]))
                target.extend(float(pushed[cell]) for cell in previous_cells)
                _add(layer_counts, "label_action_rows")
                _add(layer_counts, "label_components", 1+len(previous_cells))
            targets[state] = tuple(target)
        roots, cells, member_cells, next_cell = _fit_trees(
            groups, features, targets, mode, next_cell, h, layer_counts)
        payload["trees"][str(h)] = roots
        payload["cells"].extend(cells)
        by_cell = defaultdict(list)
        for state, cell in member_cells.items():
            by_cell[cell].append(state)
        for cell, group in sorted(by_cell.items()):
            mask = states[group[0]]["legal"]
            divisor = len(group)
            for action in mask:
                pushed, reward = defaultdict(Fraction), Fraction(0)
                for state in sorted(group):
                    reward += rewards[state, action]/divisor
                    _add(layer_counts, "compiler_member_rows")
                    _add(layer_counts, "compiler_reward_accumulations")
                    for probability, successor in rows[state, action]:
                        destination = _successor_cell(payload, states, features, successor, h-1, layer_counts)
                        pushed[destination] += probability/divisor
                        _add(layer_counts, "compiler_probability_pushes")
                outcomes = [[p.numerator, p.denominator, destination, reward.numerator, reward.denominator]
                            for destination, p in sorted(pushed.items())]
                payload["rows"].append([cell, action, outcomes])
                _add(layer_counts, "compiler_rows")
                _add(layer_counts, "compiler_outcomes", len(outcomes))
        counts.update(layer_counts)
        counts.update({f"h{h}_{key}": value for key, value in layer_counts.items()})
        counts[f"h{h}_fit_states"] = len(members)
        counts[f"h{h}_start_leaves"] = len(groups)
    payload["fit_counts"] = dict(counts)
    return payload


def _coefficient(value):
    return value if isinstance(value, Fraction) else Fraction(str(value))


def utility(vector, coefficients, counts=None):
    """Exact R - failure penalty + goal bonus utility for one joint vector."""
    _add(counts, "utility_calls")
    _add(counts, "utility_component_reads", 3)
    return (_coefficient(coefficients["reward_weight"])*vector[0]
            - _coefficient(coefficients["failure_penalty"])*vector[1]
            + _coefficient(coefficients["goal_bonus"])*vector[2])


def choose_action(values, coefficients, counts=None):
    """Sorted actions keep the first winner unless utility improves >1e-12."""
    chosen, best = None, None
    for action in sorted(values):
        value = utility(values[action], coefficients, counts)
        _add(counts, "utility_action_comparisons")
        if best is None or value-best > UTILITY_EPS:
            chosen, best = action, value
    return chosen


def _compiled_rows(payload, counts):
    _add(counts, "planning_compile_calls")
    rows = defaultdict(dict)
    for cell, action, outcomes in payload["rows"]:
        rows[cell][action] = [(Fraction(pn, pd), successor, Fraction(rn, rd))
                              for pn, pd, successor, rn, rd in outcomes]
        _add(counts, "planning_row_reads")
        _add(counts, "planning_outcome_reads", len(outcomes))
    return rows


def _action_values(rows, values, cell, counts):
    result = {}
    for action, outcomes in sorted(rows.get(cell, {}).items()):
        vector = [Fraction(0), Fraction(0), Fraction(0)]
        for probability, successor, reward in outcomes:
            continuation = values[successor]
            vector[0] += probability*(reward+continuation[0])
            vector[1] += probability*continuation[1]
            vector[2] += probability*continuation[2]
            _add(counts, "planning_successor_vectors")
            _add(counts, "planning_component_accumulations", 3)
        result[action] = vector
        _add(counts, "planning_action_values")
    return result


def action_values(payload, plan, cell, counts=None):
    """Recompute cell action vectors using this query's own lower-layer plan."""
    return _action_values(_compiled_rows(payload, counts), plan["values"], cell, counts)


def plan_model(payload, queries, counts=None):
    """Exact acyclic Bellman planning; R/F/S always share one chosen policy."""
    rows = _compiled_rows(payload, counts)
    plans = {}
    for query, coefficients in sorted(queries.items()):
        _add(counts, "planning_query_calls")
        values = {0: [Fraction(0), Fraction(0), Fraction(1)],
                  1: [Fraction(0), Fraction(1), Fraction(0)],
                  2: [Fraction(0), Fraction(0), Fraction(0)]}
        policy = {}
        _add(counts, "planning_cell_values", 3)
        for cell, h, status in sorted(payload["cells"], key=lambda item: (item[1], item[0])):
            if status != "ACTIVE":
                continue
            candidates = _action_values(rows, values, cell, counts)
            chosen = choose_action(candidates, coefficients, counts)
            if chosen is None:
                raise ValueError("ACTIVE learned cell has no controlled action row")
            values[cell], policy[cell] = candidates[chosen], chosen
            _add(counts, "planning_cell_values")
        plans[query] = dict(values=values, policy=policy)
    return plans
