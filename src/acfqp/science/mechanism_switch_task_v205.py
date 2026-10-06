"""Declared V205 route task with a context-dependent risk-critical gate.

This module owns the simulator/oracle laws.  Learning and acquisition import
only the reusable prior mechanics and never import this task module.
"""
from fractions import Fraction
from itertools import product

from . import structured_route_task_v201 as mechanics
from .continual_route_kernels_v202 import ALPHABETS, OPERATORS

QUERIES = mechanics.QUERIES
PURE_POLICIES = mechanics.PURE_POLICIES
OPERATING = mechanics.OPERATING
RETRY_COSTS = mechanics.RETRY_COSTS
WEATHER = {
    "normal": (Fraction(9, 10), Fraction(17, 20), Fraction(1, 100), Fraction(7, 50), Fraction(1, 4)),
    "wet": (Fraction(99, 100), Fraction(7, 10), Fraction(3, 25), Fraction(9, 50), Fraction(9, 10)),
    "blocked": (Fraction(13, 20), Fraction(4, 5), Fraction(1, 100), Fraction(19, 100), Fraction(2, 5)),
}


def _add(work, key, amount=1):
    if work is not None:
        work[key] = work.get(key, 0)+amount


def roster(work=None):
    """Twelve contexts in weather/operating/retry-cost Cartesian order."""
    result = []
    for weather, operating, retry_cost in product(WEATHER, OPERATING, RETRY_COSTS):
        result.append(dict(id=f"v205_{weather}_{operating}_r{retry_cost.replace('/', '_')}",
                           weather=weather, operating=operating, retry_cost=retry_cost))
        _add(work, "roster_context_constructions")
    return result


def laws(case, work=None):
    """Simulator-only categorical laws in the supplied operator/support order."""
    short, delivery, failure, recovery, retry = WEATHER[case["weather"]]
    _add(work, "true_law_calls")
    _add(work, "true_law_probability_subtractions", 2)
    return {"SHORT_PASS": dict(DELIVERY=short, LOST=1-short),
            "DETOUR_PASS": dict(DELIVERY=delivery, LOST=failure, RECOVERY=recovery),
            "RECOVERY_RETRY": dict(DELIVERY=retry, LOST=1-retry)}


def rows(case, work=None):
    """The unchanged nine-state delayed-success route graph with V205 laws."""
    probabilities = laws(case, work)
    short_cost, detour_cost = OPERATING[case["operating"]]
    retry_cost = Fraction(case["retry_cost"])
    one, zero = Fraction(1), Fraction(0)
    graph = {
        "START": {"DETOUR": [(one, "DETOUR_ENTRY", zero)],
                  "SHORT": [(one, "SHORT_ENTRY", zero)],
                  "WAIT": [(one, "WAIT_ENTRY", zero)]},
        "SHORT_ENTRY": {"PASS": [(probabilities["SHORT_PASS"][category], category, -short_cost)
                                  for category in ALPHABETS["SHORT_PASS"]]},
        "DETOUR_ENTRY": {"PASS": [(probabilities["DETOUR_PASS"][category], category, -detour_cost)
                                   for category in ALPHABETS["DETOUR_PASS"]]},
        "WAIT_ENTRY": {"WAIT": [(one, "ABORT", zero)]},
        "DELIVERY": {"FINISH": [(one, "WON", zero)]},
        "RECOVERY": {"RETURN": [(one, "ABORT", zero)],
                     "RETRY": [(probabilities["RECOVERY_RETRY"][category], category, -retry_cost)
                               for category in ALPHABETS["RECOVERY_RETRY"]]},
        "WON": {}, "LOST": {}, "ABORT": {},
    }
    _add(work, "graph_context_calls")
    _add(work, "graph_state_constructions", 9)
    _add(work, "graph_action_row_constructions", 9)
    _add(work, "graph_outcome_constructions", 13)
    _add(work, "graph_cost_negations", 7)
    _add(work, "graph_retry_fraction_constructions")
    return graph


def qualify(work=None):
    """Declared-task witnesses, separate from learning or acquired evidence.

    Constant-root comparisons permit WAIT and any continuation inside the
    chosen SHORT/DETOUR family, giving the constant-route control its best
    constrained policy in every case.  Mean gaps use the four low-cost
    new-weather targets uniformly, before any observations are collected.
    """
    records = []
    conditions = dict(ROOT_SWITCH=True, CONTINUATION=True, DEPTH=True)
    totals = dict(optimal=Fraction(0), SHORT=Fraction(0), DETOUR=Fraction(0))
    for case in roster(work):
        graph = rows(case, work)
        pure = mechanics.pure_values(graph, counts=work)
        hard = mechanics.hard_constraint(pure, counts=work)
        queries = {}
        for query in QUERIES:
            full = mechanics.plan(graph, 4, query, work)
            replay = mechanics.evaluate_plan(graph, 4, full["policy"], work)
            short = mechanics.evaluate_controller(graph, 4, query, lookahead=2, counts=work)
            full_utility = mechanics.utility(replay["root"], query, work)
            short_utility = mechanics.utility(short["root"], query, work)
            queries[query] = dict(vector=list(replay["root"]), utility=full_utility,
                                  root_action=full["policy"]["START", 4],
                                  recovery_action=full["policy"]["RECOVERY", 2],
                                  recovery_reached=("RECOVERY", 2) in replay["policy"],
                                  receding_h2_vector=list(short["root"]),
                                  receding_h2_utility=short_utility, gap=full_utility-short_utility)
            if query in ("goal", "risk"):
                conditions["DEPTH"] &= full_utility-short_utility >= 2
        if case["weather"] == "wet":
            conditions["ROOT_SWITCH"] &= hard["mix"] == [("SHORT", Fraction(1))]
        if case["weather"] == "blocked":
            conditions["ROOT_SWITCH"] &= all(policy.startswith("DETOUR_") for policy, _ in hard["mix"])
            conditions["CONTINUATION"] &= (queries["goal"]["root_action"] == "DETOUR"
                                            and queries["risk"]["root_action"] == "DETOUR"
                                            and queries["goal"]["recovery_reached"]
                                            and queries["risk"]["recovery_reached"]
                                            and queries["goal"]["recovery_action"] == "RETRY"
                                            and queries["risk"]["recovery_action"] == "RETURN")
        constants = {}
        for family, names in (("SHORT", ("WAIT", "SHORT")),
                              ("DETOUR", ("WAIT", "DETOUR_RETURN", "DETOUR_RETRY"))):
            constant = mechanics.hard_constraint({name: pure[name] for name in names}, counts=work)
            constants[family] = dict(mix=constant["mix"], vector=list(constant["vector"]), utility=constant["utility"])
        if case["weather"] in ("wet", "blocked") and case["operating"] == "low":
            totals["optimal"] += hard["utility"]
            for family in constants:
                totals[family] += constants[family]["utility"]
            _add(work, "qualification_utility_accumulations", 3)
        records.append(dict(context_id=case["id"], queries=queries,
                            pure_vectors=pure, hard_optimum=dict(mix=hard["mix"], vector=list(hard["vector"]), utility=hard["utility"]),
                            constant_families=constants))
    means = {name: total/4 for name, total in totals.items()}
    constant_gap = means["optimal"]-max(means["SHORT"], means["DETOUR"])
    conditions["CONSTANT_GAP"] = constant_gap >= Fraction(1, 2)
    _add(work, "qualification_calls")
    _add(work, "qualification_mean_divisions", 3)
    return dict(qualified=all(conditions.values()), conditions=conditions, records=records,
                constant_comparison=dict(means=means, gap=constant_gap, contexts=4))
