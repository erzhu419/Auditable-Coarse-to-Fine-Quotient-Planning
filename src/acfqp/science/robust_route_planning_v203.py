"""Fixed-evidence route risk envelopes and whole-policy robust optimization.

Only counts and frozen predicted policy vectors enter these routines.  Operator
supports and complete-policy grammar are supplied priors; true laws and task
modules are not imported.  Probability intervals are rounded outward, then
simplex risk bounds and mixture arithmetic use exact Fractions.
"""
from fractions import Fraction
from itertools import combinations
from math import ceil, floor, inf, log, log1p

OPERATORS = ("SHORT_PASS", "DETOUR_PASS", "RECOVERY_RETRY")
ALPHABETS = {"SHORT_PASS": ("DELIVERY", "LOST"),
             "DETOUR_PASS": ("DELIVERY", "LOST", "RECOVERY"),
             "RECOVERY_RETRY": ("DELIVERY", "LOST")}
PURE_POLICIES = ("WAIT", "SHORT", "DETOUR_RETURN", "DETOUR_RETRY")
FIELDS = ("operating", "retry_cost", "weather")
BETA = log(2*84/0.05)
GRID = 2**40


def _add(work, key, amount=1):
    if work is not None:
        work[key] = work.get(key, 0)+amount


def _kl(x, p, work):
    _add(work, "interval_kl_evaluations")
    if x == 0:
        if p == 1:
            return inf
        _add(work, "interval_log_calls")
        return -log1p(-p)
    if x == 1:
        if p == 0:
            return inf
        _add(work, "interval_log_calls")
        return -log(p)
    if p in (0, 1):
        return inf
    _add(work, "interval_log_calls", 2)
    return x*log(x/p)+(1-x)*log((1-x)/(1-p))


def interval(k, n, work=None):
    """Binomial KL interval: 64 bisections, outward dyadic endpoint rounding."""
    _add(work, "interval_calls")
    if not 0 <= k <= n:
        raise ValueError("categorical marginal count must lie between zero and n")
    if n == 0:
        _add(work, "interval_unobserved")
        _add(work, "interval_fraction_constructions", 2)
        return Fraction(0), Fraction(1)
    x = k/n
    _add(work, "interval_frequency_divisions")
    if k == 0:
        lower = 0.0
        _add(work, "interval_boundary_endpoints")
    else:
        lo, hi = 0.0, x
        for _ in range(64):
            mid = (lo+hi)/2
            if n*_kl(x, mid, work) > BETA:
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
            if n*_kl(x, mid, work) > BETA:
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


def envelopes(model, case, pooled=False, work=None):
    """Raw complete-context envelopes, or explicitly selected-field pooling."""
    result = {}
    _add(work, "envelope_calls")
    for operator in OPERATORS:
        fields = model["selected_fields"][operator] if pooled else FIELDS
        wanted = tuple(case[field] for field in fields)
        counts = dict.fromkeys(ALPHABETS[operator], 0)
        for record in model["tables"][operator]:
            _add(work, "envelope_context_scans")
            if tuple(record["context"][field] for field in fields) == wanted:
                for category in ALPHABETS[operator]:
                    counts[category] += record["counts"][category]
                _add(work, "envelope_count_accumulations", len(counts))
        n = sum(counts.values())
        bounds = {category: list(interval(counts[category], n, work)) for category in ALPHABETS[operator]}
        result[operator] = dict(n=n, counts=counts, bounds=bounds)
        _add(work, "envelope_operator_records")
    return result


def risk_bounds(envelope, work=None):
    """Exact maxima over marginal boxes intersected with each row's simplex.

    The shared DETOUR extremum maximizes every nonnegative complete-policy
    mixture: its failure coefficient is at least its recovery coefficient.
    """
    short = envelope["SHORT_PASS"]["bounds"]
    detour = envelope["DETOUR_PASS"]["bounds"]
    retry = envelope["RECOVERY_RETRY"]["bounds"]
    s = min(short["LOST"][1], 1-short["DELIVERY"][0])
    q = min(retry["LOST"][1], 1-retry["DELIVERY"][0])
    f = min(detour["LOST"][1], 1-detour["DELIVERY"][0]-detour["RECOVERY"][0])
    r = min(detour["RECOVERY"][1], 1-detour["DELIVERY"][0]-f)
    _add(work, "risk_bound_calls")
    _add(work, "risk_bound_endpoint_reads", 9)
    _add(work, "risk_bound_subtractions", 6)
    _add(work, "risk_bound_minima", 4)
    _add(work, "risk_bound_products")
    _add(work, "risk_bound_accumulations")
    return {"WAIT": Fraction(0), "SHORT": s, "DETOUR_RETURN": f, "DETOUR_RETRY": f+r*q}


def _candidate(mix, vectors, risks, work):
    predicted = [Fraction(0), Fraction(0), Fraction(0)]
    risk = Fraction(0)
    for policy, weight in mix:
        for component in range(3):
            predicted[component] += weight*vectors[policy][component]
        risk += weight*risks[policy]
        _add(work, "optimization_mixture_products", 4)
        _add(work, "optimization_mixture_accumulations", 4)
    _add(work, "optimization_objective_products")
    _add(work, "optimization_objective_accumulations")
    _add(work, "optimization_candidates")
    return dict(mix=mix, predicted=predicted, risk_upper=risk,
                predicted_utility=predicted[0]+4*predicted[2])


def optimize(pure_vectors, risks, delta=Fraction(1, 20), work=None):
    """Maximize the unchanged point goal objective under whole-policy bounds."""
    _add(work, "optimization_calls")
    vectors = {policy: [Fraction(value) for value in pure_vectors[policy]] for policy in sorted(PURE_POLICIES)}
    bounds = {policy: Fraction(risks[policy]) for policy in vectors}
    _add(work, "optimization_input_components", 16)
    candidates = []
    for policy in vectors:
        _add(work, "optimization_pure_feasibility_checks")
        if bounds[policy] <= delta:
            candidates.append(_candidate([[policy, Fraction(1)]], vectors, bounds, work))
    for left, right in combinations(vectors, 2):
        a, b = bounds[left], bounds[right]
        _add(work, "optimization_pair_checks")
        if min(a, b) < delta < max(a, b):
            weight = (delta-b)/(a-b)
            candidates.append(_candidate([[left, weight], [right, 1-weight]], vectors, bounds, work))
            _add(work, "optimization_edge_intersections")
            _add(work, "optimization_weight_subtractions", 3)
            _add(work, "optimization_weight_divisions")
    if not candidates:
        raise ValueError("no feasible complete route policy mixture")
    best = None
    for candidate in candidates:
        _add(work, "optimization_candidate_comparisons")
        if (best is None or candidate["predicted_utility"] > best["predicted_utility"]
                or (candidate["predicted_utility"] == best["predicted_utility"] and candidate["mix"] < best["mix"])):
            best = candidate
    return dict(**best, candidates=candidates)
