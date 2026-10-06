"""Member evidence acquisition with fixed learned partitions and route priors.

Confidence uses real complete-context counts.  Disposable fractional forecasts
choose observations; they neither update experience nor certify a real plan.
The supplied graph, supports and costs are prior knowledge, not learned laws.
Work dictionaries count logical arithmetic, scans, updates and planning calls.
"""
from copy import deepcopy
from fractions import Fraction
from itertools import combinations
from math import ceil, floor, log

from . import continual_route_kernels_v202 as learning
from . import robust_route_planning_v203 as confidence

OPERATORS = learning.OPERATORS
ALPHABETS = learning.ALPHABETS
PURE_POLICIES = confidence.PURE_POLICIES
FIELDS = learning.FEATURE_FIELDS
BATCH = 16
BUDGET = 384
BETA = log(2*728/0.05)
GRID = 2**40
DELTA = Fraction(1, 20)


def _add(work, key, amount=1):
    if work is not None:
        work[key] = work.get(key, 0)+amount


def interval(k, n, work=None):
    """KL interval, allowing rational expected counts only for forecasts."""
    _add(work, "interval_calls")
    if not 0 <= k <= n:
        raise ValueError("categorical marginal count must lie between zero and n")
    if n == 0:
        _add(work, "interval_unobserved")
        _add(work, "interval_fraction_constructions", 2)
        return Fraction(0), Fraction(1)
    x = float(k/n)
    _add(work, "interval_frequency_divisions")
    if k == 0:
        lower = 0.0
        _add(work, "interval_boundary_endpoints")
    else:
        lo, hi = 0.0, x
        for _ in range(64):
            mid = (lo+hi)/2
            if n*confidence._kl(x, mid, work) > BETA:
                lo = mid
            else:
                hi = mid
            _add(work, "interval_bisections")
            _add(work, "interval_scaled_kl_comparisons")
        lower = lo
        _add(work, "interval_searched_endpoints")
    if k == n:
        upper = 1.0
        _add(work, "interval_boundary_endpoints")
    else:
        lo, hi = x, 1.0
        for _ in range(64):
            mid = (lo+hi)/2
            if n*confidence._kl(x, mid, work) > BETA:
                hi = mid
            else:
                lo = mid
            _add(work, "interval_bisections")
            _add(work, "interval_scaled_kl_comparisons")
        upper = hi
        _add(work, "interval_searched_endpoints")
    _add(work, "interval_dyadic_roundings", 2)
    _add(work, "interval_fraction_constructions", 2)
    return Fraction(floor(lower*GRID), GRID), Fraction(ceil(upper*GRID), GRID)


def _box(counts, operator, work):
    n = sum(counts.values())
    _add(work, "envelope_count_summands", len(counts))
    bounds = {category: list(interval(counts[category], n, work))
              for category in ALPHABETS[operator]}
    _add(work, "envelope_operator_records")
    return dict(n=n, counts=counts, bounds=bounds)


def envelopes(model, case, work=None):
    """Simultaneous member bounds, without selected-field count pooling."""
    _add(work, "envelope_calls")
    wanted = tuple(case[field] for field in FIELDS)
    _add(work, "envelope_context_projections")
    result = {}
    for operator in OPERATORS:
        counts = dict.fromkeys(ALPHABETS[operator], 0)
        for record in model["tables"][operator]:
            _add(work, "envelope_context_scans")
            _add(work, "envelope_context_projections")
            if tuple(record["context"][field] for field in FIELDS) == wanted:
                for category in counts:
                    counts[category] += record["counts"][category]
                _add(work, "envelope_count_accumulations", len(counts))
        result[operator] = _box(counts, operator, work)
    return result


def risk_bounds(envelope, work=None):
    """The prior policy grammar gives V203's common worst-risk kernel."""
    return confidence.risk_bounds(envelope, work)


def goals_lower(envelope, case, work=None):
    """Exact common lower goal utility over marginal boxes and simplexes.

    The detour delivery coefficient dominates recovery for every nonnegative
    complete-policy mixture.  Recovery's coefficient has the same sign for
    every mixture, so these pure minima have a common attaining kernel.
    """
    short = envelope["SHORT_PASS"]["bounds"]
    detour = envelope["DETOUR_PASS"]["bounds"]
    retry = envelope["RECOVERY_RETRY"]["bounds"]
    short_cost, detour_cost = learning.COST_PRIOR[case["operating"]]
    retry_cost = Fraction(case["retry_cost"])
    sd = max(short["DELIVERY"][0], 1-short["LOST"][1])
    rd = max(retry["DELIVERY"][0], 1-retry["LOST"][1])
    dd = max(detour["DELIVERY"][0], 1-detour["LOST"][1]-detour["RECOVERY"][1])
    a = 4*rd-retry_cost
    if a < 0:
        dr = min(detour["RECOVERY"][1], 1-dd-detour["LOST"][0])
    else:
        dr = max(detour["RECOVERY"][0], 1-dd-detour["LOST"][1])
    base = -detour_cost+4*dd
    _add(work, "goal_bound_calls")
    _add(work, "goal_bound_endpoint_reads", 9)
    _add(work, "goal_bound_cost_reads", 3)
    _add(work, "goal_bound_subtractions", 9)
    _add(work, "goal_bound_extrema", 4)
    _add(work, "goal_bound_products", 4)
    _add(work, "goal_bound_accumulations", 3)
    return {"WAIT": Fraction(0), "SHORT": -short_cost+4*sd,
            "DETOUR_RETURN": base, "DETOUR_RETRY": base+a*dr}


def point_vectors(model, case, work=None):
    """Own complete-policy joint R/F/S from learned means and known costs."""
    short = learning.probabilities(model, case, "SHORT_PASS", work)
    detour = learning.probabilities(model, case, "DETOUR_PASS", work)
    retry = learning.probabilities(model, case, "RECOVERY_RETRY", work)
    short_cost, detour_cost = learning.COST_PRIOR[case["operating"]]
    retry_cost = Fraction(case["retry_cost"])
    recovery = detour["RECOVERY"]
    _add(work, "point_vector_calls")
    _add(work, "point_vector_probability_reads", 7)
    _add(work, "point_vector_cost_reads", 3)
    _add(work, "point_vector_products", 3)
    _add(work, "point_vector_accumulations", 3)
    _add(work, "point_vector_cost_negations", 3)
    return {"WAIT": [Fraction(0), Fraction(0), Fraction(0)],
            "SHORT": [-short_cost, short["LOST"], short["DELIVERY"]],
            "DETOUR_RETURN": [-detour_cost, detour["LOST"], detour["DELIVERY"]],
            "DETOUR_RETRY": [-detour_cost-recovery*retry_cost,
                             detour["LOST"]+recovery*retry["LOST"],
                             detour["DELIVERY"]+recovery*retry["DELIVERY"]]}


def _candidate(mix, pure, risks, goals, work):
    predicted = [Fraction(0), Fraction(0), Fraction(0)]
    risk, goal = Fraction(0), Fraction(0)
    for policy, weight in mix:
        for component in range(3):
            predicted[component] += weight*pure[policy][component]
        risk += weight*risks[policy]
        goal += weight*goals[policy]
        _add(work, "optimization_mixture_products", 5)
        _add(work, "optimization_mixture_accumulations", 5)
    _add(work, "optimization_objective_products")
    _add(work, "optimization_objective_accumulations")
    _add(work, "optimization_candidates")
    return dict(mix=mix, predicted=predicted, predicted_utility=predicted[0]+4*predicted[2],
                risk_upper=risk, utility_lower=goal)


def solve(pure, risks, goals, work=None):
    """Maximize the exact common lower goal utility under delta=1/20."""
    _add(work, "optimization_calls")
    policies = sorted(PURE_POLICIES)
    candidates = []
    for policy in policies:
        _add(work, "optimization_pure_feasibility_checks")
        if risks[policy] <= DELTA:
            candidates.append(_candidate([[policy, Fraction(1)]], pure, risks, goals, work))
    for left, right in combinations(policies, 2):
        a, b = risks[left], risks[right]
        _add(work, "optimization_pair_checks")
        if min(a, b) < DELTA < max(a, b):
            weight = (DELTA-b)/(a-b)
            candidates.append(_candidate([[left, weight], [right, 1-weight]], pure, risks, goals, work))
            _add(work, "optimization_edge_intersections")
            _add(work, "optimization_weight_subtractions", 3)
            _add(work, "optimization_weight_divisions")
    best = None
    for candidate in candidates:
        _add(work, "optimization_candidate_comparisons")
        if (best is None or candidate["utility_lower"] > best["utility_lower"]
                or (candidate["utility_lower"] == best["utility_lower"] and candidate["mix"] < best["mix"])):
            best = candidate
    return best


def make_plan(model, case, work=None):
    """Return a whole-policy plan plus all count-derived planning inputs."""
    _add(work, "planning_calls")
    envelope = envelopes(model, case, work)
    risks, goals = risk_bounds(envelope, work), goals_lower(envelope, case, work)
    pure = point_vectors(model, case, work)
    return dict(**solve(pure, risks, goals, work), envelopes=envelope,
                risks=risks, goals_lower=goals, pure_vectors=pure)


def forecast(model, case, current, work=None):
    """Select the best disposable mean-count one-batch information forecast.

    Point vectors stay fixed during this prospective confidence comparison.
    Only scores survive; fractional counts never enter the learner's tables.
    """
    _add(work, "forecast_calls")
    scores = {}
    for operator in OPERATORS:
        prospective = deepcopy(current["envelopes"])
        _add(work, "forecast_envelope_copies")
        _add(work, "forecast_copied_categories", sum(len(alphabet) for alphabet in ALPHABETS.values()))
        posterior = learning.probabilities(model, case, operator, work)
        counts = prospective[operator]["counts"]
        for category in ALPHABETS[operator]:
            counts[category] += BATCH*posterior[category]
        _add(work, "forecast_count_products", len(counts))
        _add(work, "forecast_count_accumulations", len(counts))
        prospective[operator] = _box(counts, operator, work)
        risks, goals = risk_bounds(prospective, work), goals_lower(prospective, case, work)
        scores[operator] = solve(current["pure_vectors"], risks, goals, work)["utility_lower"]
        _add(work, "forecast_candidates")
    chosen = OPERATORS[0]
    for operator in OPERATORS[1:]:
        _add(work, "forecast_score_comparisons")
        if scores[operator] > scores[chosen]:
            chosen = operator
    return dict(operator=chosen, forecast_scores=scores)


def cold_policy(model, case, current, work=None):
    """Known-grammar control using local point goal/risk and policy occupancy."""
    _add(work, "cold_policy_calls")
    pure = current["pure_vectors"]
    scores = {}
    chosen = None
    for policy in sorted(name for name in PURE_POLICIES if name != "WAIT"):
        vector = pure[policy]
        scores[policy] = (vector[0]+4*vector[2])/vector[1]
        _add(work, "cold_policy_products")
        _add(work, "cold_policy_accumulations")
        _add(work, "cold_policy_divisions")
        _add(work, "cold_policy_score_comparisons")
        if chosen is None or scores[policy] > scores[chosen]:
            chosen = policy
    occupancy = dict.fromkeys(OPERATORS, Fraction(0))
    if chosen == "SHORT":
        occupancy["SHORT_PASS"] = Fraction(1)
    else:
        occupancy["DETOUR_PASS"] = Fraction(1)
        if chosen == "DETOUR_RETRY":
            occupancy["RECOVERY_RETRY"] = 1-pure["DETOUR_RETURN"][1]-pure["DETOUR_RETURN"][2]
            _add(work, "cold_policy_occupancy_subtractions", 2)
    operator = OPERATORS[0]
    for candidate in OPERATORS[1:]:
        _add(work, "cold_policy_occupancy_comparisons")
        if occupancy[candidate] > occupancy[operator]:
            operator = candidate
    return dict(operator=operator, forecast_scores=None, policy=chosen, policy_scores=scores)


def update(model, case, operator, increments, work=None):
    """Apply one actual integer batch, retaining selected conditions and scores."""
    _add(work, "update_calls")
    alphabet = ALPHABETS[operator]
    batch = {category: increments.get(category, 0) for category in alphabet}
    if any(type(value) is not int or value < 0 for value in batch.values()) or sum(batch.values()) != BATCH:
        raise ValueError("real acquisition updates require sixteen integer observations")
    _add(work, "update_batch_categories", len(batch))
    wanted = tuple(case[field] for field in FIELDS)
    _add(work, "update_context_projections")
    record = None
    for row in model["tables"][operator]:
        _add(work, "update_context_scans")
        _add(work, "update_context_projections")
        if tuple(row["context"][field] for field in FIELDS) == wanted:
            record = row
            break
    if record is None:
        record = dict(context=dict(case), counts=dict.fromkeys(alphabet, 0))
        model["tables"][operator].append(record)
        _add(work, "update_context_records")
    for category in alphabet:
        record["counts"][category] += batch[category]
    _add(work, "update_categorical_accumulations", len(alphabet))
    model["tables"][operator].sort(key=lambda row: tuple(row["context"][field] for field in FIELDS))
    _add(work, "update_sort_key_projections", len(model["tables"][operator]))
    _add(work, "update_table_sorts")
    model["observations_used"] += BATCH
    _add(work, "update_observations", BATCH)
