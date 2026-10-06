"""Declared finite route mechanics, joint planning, and achievable risk mixes.

This is an oracle task specification, not a learner or sampled experience.
At H4, each DP/replay has at most 45 state/remaining keys.  Hard-constrained
planning considers four pure policies and their six two-policy edges.
"""
from collections import Counter
from fractions import Fraction
from itertools import combinations, product

STATES = ("START", "SHORT_ENTRY", "DETOUR_ENTRY", "WAIT_ENTRY", "DELIVERY",
          "RECOVERY", "WON", "LOST", "ABORT")
PURE_POLICIES = ("WAIT", "SHORT", "DETOUR_RETURN", "DETOUR_RETRY")
QUERIES = {"reward": (1, 0, 0), "goal": (1, 0, 4), "risk": (1, 4, 4)}
WEATHER = {
    "normal": (Fraction(9, 10), Fraction(17, 20), Fraction(1, 100), Fraction(7, 50), Fraction(1, 4)),
    "wet": (Fraction(17, 20), Fraction(39, 50), Fraction(1, 50), Fraction(1, 5), Fraction(3, 10)),
    "blocked": (Fraction(13, 20), Fraction(41, 50), Fraction(1, 100), Fraction(17, 100), Fraction(2, 5)),
}
OPERATING = {"low": (Fraction(1, 10), Fraction(1, 20)),
             "high": (Fraction(3, 25), Fraction(7, 100))}
RETRY_COSTS = ("17/20", "19/20")
ZERO = Fraction(0)
ONE = Fraction(1)
TERMINAL_VALUES = {"WON": (ZERO, ZERO, ONE), "LOST": (ZERO, ONE, ZERO),
                   "ABORT": (ZERO, ZERO, ZERO)}


def _add(counts, name, amount=1):
    if counts is not None:
        counts[name] = counts.get(name, 0) + amount


def _work(counts):
    return Counter() if counts is None else counts


def roster(counts=None):
    """The declared Cartesian contexts, in weather/operating/retry order."""
    cases = []
    for weather, operating, retry_cost in product(WEATHER, OPERATING, RETRY_COSTS):
        cases.append(dict(id=f"v201_{weather}_{operating}_r{retry_cost.replace('/', '_')}",
                          weather=weather, operating=operating, retry_cost=retry_cost))
        _add(counts, "roster_context_constructions")
    return cases


def rows(case, counts=None):
    """Return nine state dictionaries with nine rows and thirteen outcomes.

    An outcome is ``(probability, next_state, immediate_reward)`` with exact
    Fraction components.  DELIVERY is active: FINISH must still reach WON.
    """
    short_s, detour_s, detour_f, recovery, retry_s = WEATHER[case["weather"]]
    short_cost, detour_cost = OPERATING[case["operating"]]
    retry_cost = Fraction(case["retry_cost"])
    if str(retry_cost) not in RETRY_COSTS:
        raise ValueError("V201 retry cost must be 17/20 or 19/20")
    graph = {
        "START": {"DETOUR": [(ONE, "DETOUR_ENTRY", ZERO)],
                  "SHORT": [(ONE, "SHORT_ENTRY", ZERO)],
                  "WAIT": [(ONE, "WAIT_ENTRY", ZERO)]},
        "SHORT_ENTRY": {"PASS": [(short_s, "DELIVERY", -short_cost),
                                 (ONE-short_s, "LOST", -short_cost)]},
        "DETOUR_ENTRY": {"PASS": [(detour_s, "DELIVERY", -detour_cost),
                                  (detour_f, "LOST", -detour_cost),
                                  (recovery, "RECOVERY", -detour_cost)]},
        "WAIT_ENTRY": {"WAIT": [(ONE, "ABORT", ZERO)]},
        "DELIVERY": {"FINISH": [(ONE, "WON", ZERO)]},
        "RECOVERY": {"RETURN": [(ONE, "ABORT", ZERO)],
                     "RETRY": [(retry_s, "DELIVERY", -retry_cost),
                               (ONE-retry_s, "LOST", -retry_cost)]},
        "WON": {}, "LOST": {}, "ABORT": {},
    }
    _add(counts, "graph_context_calls")
    _add(counts, "graph_state_constructions", 9)
    _add(counts, "graph_action_row_constructions", 9)
    _add(counts, "graph_outcome_constructions", 13)
    _add(counts, "graph_probability_subtractions", 2)
    _add(counts, "graph_cost_negations", 7)
    _add(counts, "graph_retry_fraction_constructions")
    return graph


def utility(vector, query, counts=None):
    """Exact utility of one achievable joint R/F/S vector."""
    reward, failure, goal = QUERIES[query]
    _add(counts, "utility_calls")
    _add(counts, "utility_component_reads", 3)
    return reward*vector[0]-failure*vector[1]+goal*vector[2]


def _choose(vectors, query, counts):
    chosen, best = None, None
    for action in sorted(vectors):
        value = utility(vectors[action], query, counts)
        _add(counts, "action_comparisons")
        if best is None or value > best:
            chosen, best = action, value
    return chosen


def _horizon(h):
    if not isinstance(h, int) or not 0 <= h <= 4:
        raise ValueError("V201 remaining horizon must be 0 through 4")


def _boundary(state, remaining):
    if state in TERMINAL_VALUES:
        return TERMINAL_VALUES[state]
    return (ZERO, ZERO, ZERO) if remaining == 0 else None


def _vector(outcomes, continuation, counts, prefix):
    result = [ZERO, ZERO, ZERO]
    for probability, successor, reward in outcomes:
        tail = continuation(successor)
        result[0] += probability*(reward+tail[0])
        result[1] += probability*tail[1]
        result[2] += probability*tail[2]
        _add(counts, f"{prefix}_outcome_evaluations")
        _add(counts, f"{prefix}_component_products", 3)
        _add(counts, f"{prefix}_component_accumulations", 3)
        _add(counts, f"{prefix}_immediate_reward_additions")
    return tuple(result)


def plan(graph, h, query, counts=None):
    """Joint Bellman DP; exact ties retain the first sorted action.

    Values and action_vectors contain every (state, remaining) pair.  Terminal
    and horizon-zero action-vector dictionaries are empty.  Policy contains
    only ACTIVE pairs with positive remaining horizon.
    """
    _horizon(h)
    work = _work(counts)
    _add(work, "plan_calls")
    values, policy, action_vectors = {}, {}, {}
    for remaining in range(h+1):
        for state in sorted(graph):
            key = (state, remaining)
            boundary = _boundary(state, remaining)
            if boundary is not None:
                values[key], action_vectors[key] = boundary, {}
            else:
                candidates = {}
                for action, outcomes in sorted(graph[state].items()):
                    candidates[action] = _vector(
                        outcomes, lambda successor: values[successor, remaining-1], work, "dp")
                    _add(work, "dp_action_rows")
                chosen = _choose(candidates, query, work)
                values[key], policy[key] = candidates[chosen], chosen
                action_vectors[key] = candidates
            _add(work, "dp_value_keys")
    return dict(values=values, policy=policy, action_vectors=action_vectors, counts=dict(work))


def _policy_action(graph, state, remaining, policy, counts):
    _add(counts, "replay_policy_requests")
    if callable(policy):
        return policy(state, remaining)
    if isinstance(policy, str):
        if policy not in PURE_POLICIES:
            raise ValueError("unknown V201 pure policy")
        if state == "START":
            return policy if policy in ("WAIT", "SHORT") else "DETOUR"
        if state == "RECOVERY":
            return "RETRY" if policy == "DETOUR_RETRY" else "RETURN"
        return next(iter(graph[state]))
    return policy[state, remaining]


def evaluate_plan(graph, h, policy, counts=None, *, start="START"):
    """Replay a full policy from a fresh prefix, counting only future costs.

    ``policy`` is a plan's tuple-keyed policy dictionary, one of the four pure
    policy names, or a (state, remaining)->action callable.  Returned policy
    includes the nonterminal pairs actually reached by this replay.
    """
    _horizon(h)
    work = _work(counts)
    _add(work, "replay_calls")
    values, actions = {}, {}

    def visit(state, remaining):
        _add(work, "replay_value_requests")
        key = (state, remaining)
        if key in values:
            _add(work, "replay_memo_hits")
            return values[key]
        boundary = _boundary(state, remaining)
        if boundary is not None:
            result = boundary
        else:
            action = _policy_action(graph, state, remaining, policy, work)
            actions[key] = action
            result = _vector(graph[state][action], lambda successor: visit(successor, remaining-1), work, "replay")
            _add(work, "replay_action_rows")
        values[key] = result
        _add(work, "replay_value_keys")
        return result

    root = visit(start, h)
    return dict(root=root, values=values, policy=actions, counts=dict(work))


def evaluate_controller(graph, h, query, lookahead=None, counts=None):
    """Replay full planning or a receding controller at min(depth, remaining)."""
    _horizon(h)
    depth = h if lookahead is None else lookahead
    _horizon(depth)
    if h and depth == 0:
        raise ValueError("an active V201 controller needs positive lookahead")
    work = _work(counts)
    _add(work, "controller_calls")
    table = plan(graph, min(depth, h), query, work)

    def action(state, remaining):
        _add(work, "controller_policy_lookups")
        return table["policy"][state, min(depth, remaining)]

    return evaluate_plan(graph, h, action, work)


def pure_values(graph, h=4, counts=None):
    """All four complete executable policy vectors at START."""
    _horizon(h)
    work = _work(counts)
    _add(work, "pure_policy_sets")
    result = {}
    for name in PURE_POLICIES:
        result[name] = evaluate_plan(graph, h, name, work)["root"]
        _add(work, "pure_policy_evaluations")
    return result


def hard_constraint(pure_vectors, delta=Fraction(1, 20), counts=None):
    """Maximize R+4S over feasible pure vertices and crossing-edge mixtures.

    A mixture chooses an entire pure policy at START.  Its constituent vectors
    are retained, so the returned R/F/S is achievable by one randomized policy.
    This implements a risk constraint, rather than a failure penalty.
    """
    work = _work(counts)
    _add(work, "hard_constraint_calls")
    delta = Fraction(delta)
    vectors = {name: tuple(Fraction(value) for value in vector)
               for name, vector in sorted(pure_vectors.items())}
    candidates = []
    for name, vector in vectors.items():
        _add(work, "hard_pure_feasibility_checks")
        if vector[1] <= delta:
            candidates.append(dict(mix=[(name, ONE)], vector=vector, utility=utility(vector, "goal", work)))
            _add(work, "hard_feasible_pure_candidates")
    for left, right in combinations(vectors, 2):
        a, b = vectors[left], vectors[right]
        _add(work, "hard_pair_checks")
        if not min(a[1], b[1]) < delta < max(a[1], b[1]):
            continue
        weight = (delta-b[1])/(a[1]-b[1])
        vector = tuple(weight*a[c]+(ONE-weight)*b[c] for c in range(3))
        candidates.append(dict(mix=[(left, weight), (right, ONE-weight)], vector=vector,
                               utility=utility(vector, "goal", work)))
        _add(work, "hard_edge_intersections")
        _add(work, "hard_mixture_component_products", 6)
        _add(work, "hard_mixture_component_accumulations", 3)
    if not candidates:
        raise ValueError("no feasible V201 policy mixture")
    best = None
    for candidate in candidates:
        _add(work, "hard_candidate_comparisons")
        if (best is None or candidate["utility"] > best["utility"]
                or (candidate["utility"] == best["utility"] and candidate["mix"] < best["mix"])):
            best = candidate
    return dict(vector=best["vector"], utility=best["utility"], mix=best["mix"],
                pure_vectors=vectors, candidates=candidates, delta=delta, counts=dict(work))
