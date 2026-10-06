"""Synthetic member evidence only; no task laws or acquisition experiments."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from itertools import combinations, product

import pytest

from acfqp.science import continual_route_kernels_v202 as learning
from acfqp.science import robust_route_planning_v203 as previous
from acfqp.science import target_risk_acquisition_v204 as core


def case(weather="wet", operating="low"):
    return dict(id=f"synthetic_{weather}_{operating}", weather=weather,
                operating=operating, retry_cost="17/20")


def model(fields=("weather",)):
    old = case(operating="high")
    return dict(selected_fields={operator: list(fields) for operator in core.OPERATORS},
                scores={operator: [dict(fields=list(fields), score=-1.0)] for operator in core.OPERATORS},
                tables={
                    "SHORT_PASS": [dict(context=old, counts={"DELIVERY": 50, "LOST": 50})],
                    "DETOUR_PASS": [dict(context=old, counts={"DELIVERY": 98, "LOST": 1, "RECOVERY": 1})],
                    "RECOVERY_RETRY": [dict(context=old, counts={"DELIVERY": 50, "LOST": 50})]},
                observations_used=300)


def polygon_vertices(bounds):
    """Independent enumeration: two active box faces plus the simplex plane."""
    names = tuple(bounds)
    vertices = set()
    for faces in combinations(range(3), 2):
        free = next(index for index in range(3) if index not in faces)
        for endpoints in product((0, 1), repeat=2):
            point = [F(0)]*3
            for index, endpoint in zip(faces, endpoints):
                point[index] = bounds[names[index]][endpoint]
            point[free] = 1-sum(point)
            if all(bounds[name][0] <= value <= bounds[name][1] for name, value in zip(names, point)):
                vertices.add(tuple(point))
    return [dict(zip(names, vertex)) for vertex in vertices]


def test_goal_minima_share_a_vertex_for_both_retry_signs_and_mixtures():
    envelope = {
        "SHORT_PASS": dict(bounds={"DELIVERY": [F(1, 2), F(9, 10)], "LOST": [F(1, 10), F(1, 2)]}),
        "DETOUR_PASS": dict(bounds={"DELIVERY": [F(1, 5), F(1, 2)],
                                     "LOST": [F(1, 10), F(3, 5)],
                                     "RECOVERY": [F(1, 10), F(3, 5)]}),
        "RECOVERY_RETRY": dict(bounds={"DELIVERY": [F(1, 10), F(9, 10)], "LOST": [F(1, 10), F(9, 10)]})}
    for retry_lower, expected, mixed in ((F(1, 10), F(12, 25), F(147, 250)),
                                         (F(1, 2), F(49, 50), F(111, 125))):
        envelope["RECOVERY_RETRY"]["bounds"] = {
            "DELIVERY": [retry_lower, F(9, 10)], "LOST": [F(1, 10), 1-retry_lower]}
        goals = core.goals_lower(envelope, case())
        assert goals["SHORT"] == F(19, 10) and goals["DETOUR_RETURN"] == F(3, 4)
        assert goals["DETOUR_RETRY"] == expected
        pure_return, pure_retry, mixture = [], [], []
        for vertex in polygon_vertices(envelope["DETOUR_PASS"]["bounds"]):
            for retry_success in (retry_lower, F(9, 10)):
                direct = -F(1, 20)+4*vertex["DELIVERY"]
                recovered = direct+vertex["RECOVERY"]*(4*retry_success-F(17, 20))
                pure_return.append(direct)
                pure_retry.append(recovered)
                mixture.append(F(2, 5)*direct+F(3, 5)*recovered)
        assert min(pure_return) == goals["DETOUR_RETURN"]
        assert min(pure_retry) == goals["DETOUR_RETRY"]
        assert min(mixture) == mixed == F(2, 5)*goals["DETOUR_RETURN"]+F(3, 5)*goals["DETOUR_RETRY"]


def test_disposable_forecast_fixed_fields_and_prior_only_policy_control():
    learned, target = model(), case()
    current = core.make_plan(learned, target)
    before, plan_before = deepcopy(learned), deepcopy(current)
    work = Counter()
    choice = core.forecast(learned, target, current, work)
    assert choice["operator"] == "DETOUR_PASS"
    assert set(choice["forecast_scores"]) == set(core.OPERATORS)
    assert learned == before and current == plan_before
    assert work["forecast_candidates"] == 3 and work["forecast_envelope_copies"] == 3
    virtual = {category: core.BATCH*probability for category, probability in
               learning.probabilities(learned, target, "DETOUR_PASS").items()}
    with pytest.raises(ValueError, match="integer observations"):
        core.update(learned, target, "DETOUR_PASS", virtual)
    assert learned == before
    core.update(learned, target, "DETOUR_PASS", {"DELIVERY": 16, "LOST": 0, "RECOVERY": 0})
    assert learned["observations_used"] == 316
    assert learned["selected_fields"] == before["selected_fields"] and learned["scores"] == before["scores"]
    assert learning.probabilities(learned, target, "DETOUR_PASS")["DELIVERY"] == F(229, 235)
    assert core.envelopes(learned, target)["DETOUR_PASS"]["counts"] == {"DELIVERY": 16, "LOST": 0, "RECOVERY": 0}
    cold = model(core.FIELDS)
    cold_before = deepcopy(cold)
    control = core.cold_policy(cold, target, core.make_plan(cold, target))
    assert control["forecast_scores"] is None and control["policy"] == "DETOUR_RETURN"
    assert control["operator"] == "DETOUR_PASS" and cold == cold_before
    assert control["policy_scores"]["DETOUR_RETURN"] == F(77, 20)
    assert control["policy_scores"]["SHORT"] == F(19, 5)


def test_adaptive_look_intervals_use_raw_members_and_accept_virtual_counts():
    assert core.interval(0, 0) == (F(0), F(1))
    work = Counter()
    lower, upper = core.interval(F(4, 3), 16, work)
    assert lower < F(1, 12) < upper
    assert core.GRID % lower.denominator == core.GRID % upper.denominator == 0
    assert work["interval_bisections"] == 128
    assert core.interval(0, 16)[1] > previous.interval(0, 16)[1]
    learned, target = model(), case()
    unknown = core.envelopes(learned, target)
    assert all(row["n"] == 0 for row in unknown.values())
    assert all(pair == [F(0), F(1)] for row in unknown.values() for pair in row["bounds"].values())
    assert core.risk_bounds(unknown) == {"WAIT": F(0), "SHORT": F(1), "DETOUR_RETURN": F(1), "DETOUR_RETRY": F(1)}
    assert learning.probabilities(learned, target, "DETOUR_PASS")["DELIVERY"] > F(9, 10)
    core.update(learned, target, "SHORT_PASS", {"DELIVERY": 16, "LOST": 0})
    observed = core.envelopes(learned, target)["SHORT_PASS"]
    assert observed["n"] == 16 and all(type(count) is int for count in observed["counts"].values())
    assert observed["bounds"]["LOST"][1] > 0
    assert learned["tables"]["SHORT_PASS"][0]["context"]["operating"] == "high"


def test_certificate_budget_censoring_and_whole_policy_plan_arithmetic():
    target = case()
    assert core.BATCH == 16 and core.BUDGET == 384
    unknown = core.make_plan(model(), target)
    assert unknown["utility_lower"] == 0 and unknown["mix"] == [["WAIT", F(1)]]
    supported = model()
    for batch_index in range(core.BUDGET//core.BATCH):
        increments = ({"DELIVERY": 16, "LOST": 0, "RECOVERY": 0} if batch_index < 20
                      else {"DELIVERY": 14, "LOST": 1, "RECOVERY": 1})
        core.update(supported, target, "DETOUR_PASS", increments)
    certified = core.make_plan(supported, target)
    assert certified["envelopes"]["DETOUR_PASS"]["n"] == core.BUDGET
    assert certified["utility_lower"] >= 2 and certified["risk_upper"] <= F(1, 20)
    assert certified["predicted"][1] < certified["risk_upper"]
    assert certified["predicted_utility"] >= certified["utility_lower"]
    expected = [sum(weight*certified["pure_vectors"][policy][index] for policy, weight in certified["mix"])
                for index in range(3)]
    assert certified["predicted"] == expected
    censored = model()
    for _ in range(core.BUDGET//core.BATCH):
        core.update(censored, target, "SHORT_PASS", {"DELIVERY": 8, "LOST": 8})
    stopped = core.make_plan(censored, target)
    assert sum(row["n"] for row in stopped["envelopes"].values()) == core.BUDGET
    assert stopped["utility_lower"] < 2
    # A point-favored SHORT cannot replace the lower-objective optimum.
    point = {"WAIT": [F(0), F(0), F(0)], "SHORT": [F(0), F(1, 10), F(3, 4)],
             "DETOUR_RETURN": [F(0), F(1, 10), F(1, 4)], "DETOUR_RETRY": [F(0), F(1, 10), F(1, 4)]}
    solved = core.solve(point, {policy: vector[1] for policy, vector in point.items()},
                        {"WAIT": F(0), "SHORT": F(1), "DETOUR_RETURN": F(2), "DETOUR_RETRY": F(0)})
    assert solved["mix"] == [["DETOUR_RETURN", F(1, 2)], ["WAIT", F(1, 2)]]
    assert solved["utility_lower"] == 1 and solved["predicted_utility"] == F(1, 2)
