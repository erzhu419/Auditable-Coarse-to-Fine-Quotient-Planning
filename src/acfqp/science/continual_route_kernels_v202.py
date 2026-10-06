"""Chronological categorical kernel learning under explicit route priors.

The learner receives individual observed successors, never true probabilities.
The graph, operator supports, terminal semantics, and costs are supplied prior
knowledge.  Eight finite field-subset partitions are the candidate language.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction
from itertools import combinations
from math import lgamma

FEATURE_FIELDS = ("operating", "retry_cost", "weather")
OPERATORS = ("SHORT_PASS", "DETOUR_PASS", "RECOVERY_RETRY")
ALPHABETS = {"SHORT_PASS": ("DELIVERY", "LOST"),
             "DETOUR_PASS": ("DELIVERY", "LOST", "RECOVERY"),
             "RECOVERY_RETRY": ("DELIVERY", "LOST")}
ARMS = ("RESET", "FROZEN", "FULL_CONTEXT", "FIXED_WEATHER", "REVISED")
SUBSETS = tuple(subset for size in range(4) for subset in combinations(FEATURE_FIELDS, size))
SCORE_EPS = 1e-9
COST_PRIOR = {"low": (Fraction(1, 10), Fraction(1, 20)),
              "high": (Fraction(3, 25), Fraction(7, 100))}


def _add(counts, key, amount=1):
    if counts is not None:
        counts[key] = counts.get(key, 0)+amount


def _projection(context, fields):
    return tuple(context[field] for field in fields)


def _table(history, counts):
    grouped = {operator: {} for operator in OPERATORS}
    observations = 0
    for batch in history:
        _add(counts, "fit_batches_read")
        for event in batch:
            context, operator, successor = event["context"], event["operator"], event["successor"]
            if successor not in ALPHABETS[operator]:
                raise ValueError("observed successor is outside the operator's supplied support")
            key = _projection(context, FEATURE_FIELDS)
            table = grouped[operator]
            if key not in table:
                table[key] = dict(context=dict(context), counts={category: 0 for category in ALPHABETS[operator]})
                _add(counts, "fit_context_records")
            table[key]["counts"][successor] += 1
            observations += 1
            _add(counts, "fit_observations_read")
            _add(counts, "fit_categorical_increments")
    return {operator: [table[key] for key in sorted(table)] for operator, table in grouped.items()}, observations


def _score(table, operator, fields, counts):
    groups = defaultdict(Counter)
    alphabet = ALPHABETS[operator]
    for record in table:
        group = groups[_projection(record["context"], fields)]
        for category in alphabet:
            group[category] += record["counts"][category]
        _add(counts, "score_context_projections")
        _add(counts, "score_count_accumulations", len(alphabet))
    score = 0.0
    k = len(alphabet)
    for key in sorted(groups):
        group = groups[key]
        total = sum(group.values())
        base = lgamma(k*0.5)-lgamma(total+k*0.5)
        terms = [lgamma(group[category]+0.5)-lgamma(0.5) for category in alphabet]
        score += base+sum(terms)
        _add(counts, "score_groups")
        _add(counts, "score_lgamma_calls", 2+2*k)
        _add(counts, "score_category_terms", k)
    _add(counts, "score_candidates")
    return score


def fit(batch_history, arm="REVISED", frozen=None, counts=None):
    """Fit the available prefix, latest batch, or an immutable SOURCE model.

    Events have ``context``, ``operator``, and observed ``successor`` fields.
    RESET receives an empty last batch at a zero-acquisition phase boundary.
    FROZEN initially selects like REVISED; subsequent calls supply ``frozen``
    and copy its SOURCE tables without examining batch_history.
    """
    if arm not in ARMS:
        raise ValueError("unknown V202 learner arm")
    work = Counter() if counts is None else counts
    _add(work, "fit_calls")
    if arm == "FROZEN" and frozen is not None:
        model = deepcopy(frozen)
        model["arm"] = "FROZEN"
        _add(work, "frozen_model_copies")
        model["fit_counts"] = dict(work)
        return model
    history = batch_history[-1:] if arm == "RESET" else batch_history
    tables, observations = _table(history, work)
    selected, scores = {}, {}
    for operator in OPERATORS:
        candidates = ((FEATURE_FIELDS,) if arm == "FULL_CONTEXT" else
                      (("weather",),) if arm == "FIXED_WEATHER" else SUBSETS)
        best, records = None, []
        for fields in candidates:
            score = _score(tables[operator], operator, fields, work)
            records.append(dict(fields=list(fields), score=score))
            _add(work, "score_comparisons")
            key = (len(fields), fields)
            if (best is None or score > best[0]+SCORE_EPS
                    or (abs(score-best[0]) <= SCORE_EPS and key < best[1])):
                best = (score, key, fields)
        selected[operator], scores[operator] = list(best[2]), records
    return dict(schema="acfqp.continual_route_kernels.v202.model", arm=arm,
                selected_fields=selected, scores=scores, tables=tables,
                observations_used=observations, fit_counts=dict(work))


def probabilities(model, case, operator, counts=None):
    """Posterior probabilities; a never-observed projection has uniform prior."""
    alphabet, fields = ALPHABETS[operator], model["selected_fields"][operator]
    wanted = _projection(case, fields)
    category_counts = dict.fromkeys(alphabet, 0)
    _add(counts, "posterior_calls")
    for record in model["tables"][operator]:
        _add(counts, "posterior_context_scans")
        if _projection(record["context"], fields) == wanted:
            for category in alphabet:
                category_counts[category] += record["counts"][category]
            _add(counts, "posterior_count_accumulations", len(alphabet))
    total = sum(category_counts.values())
    denominator = 2*total+len(alphabet)
    result = {category: Fraction(2*category_counts[category]+1, denominator) for category in alphabet}
    _add(counts, "posterior_fraction_constructions", len(alphabet))
    return result


def predicted_graph(model, case, counts=None):
    """Instantiate the supplied V201 graph with learned gate probabilities.

    This routine does not import the task's true weather kernels, rows, or
    roster.  Costs and the delayed DELIVERY/FINISH interface are known priors.
    """
    short = probabilities(model, case, "SHORT_PASS", counts)
    detour = probabilities(model, case, "DETOUR_PASS", counts)
    retry = probabilities(model, case, "RECOVERY_RETRY", counts)
    short_cost, detour_cost = COST_PRIOR[case["operating"]]
    retry_cost = Fraction(case["retry_cost"])
    one, zero = Fraction(1), Fraction(0)
    graph = {
        "START": {"DETOUR": [(one, "DETOUR_ENTRY", zero)],
                  "SHORT": [(one, "SHORT_ENTRY", zero)],
                  "WAIT": [(one, "WAIT_ENTRY", zero)]},
        "SHORT_ENTRY": {"PASS": [(short[category], category, -short_cost) for category in ALPHABETS["SHORT_PASS"]]},
        "DETOUR_ENTRY": {"PASS": [(detour[category], category, -detour_cost) for category in ALPHABETS["DETOUR_PASS"]]},
        "RECOVERY": {"RETURN": [(one, "ABORT", zero)],
                     "RETRY": [(retry[category], category, -retry_cost) for category in ALPHABETS["RECOVERY_RETRY"]]},
        "WAIT_ENTRY": {"WAIT": [(one, "ABORT", zero)]},
        "DELIVERY": {"FINISH": [(one, "WON", zero)]},
        "WON": {}, "LOST": {}, "ABORT": {},
    }
    _add(counts, "predicted_graph_calls")
    _add(counts, "predicted_graph_states", 9)
    _add(counts, "predicted_graph_action_rows", 9)
    _add(counts, "predicted_graph_outcomes", 13)
    _add(counts, "predicted_graph_cost_negations", 7)
    _add(counts, "predicted_graph_fraction_constructions", 3)
    return graph
