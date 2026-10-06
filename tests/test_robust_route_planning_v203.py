"""Synthetic counts and policy vectors; no real kernels or new observations."""
from collections import Counter
from fractions import Fraction as F
from math import exp

from acfqp.science import robust_route_planning_v203 as core


def case(weather, operating="low"):
    return dict(id=f"synthetic_{weather}_{operating}", weather=weather,
                operating=operating, retry_cost="17/20")


def test_unknown_and_unobserved_failure_intervals_are_not_zero_risk():
    assert core.interval(0, 0) == (F(0), F(1))
    work = Counter()
    lower, upper = core.interval(0, 256, work)
    endpoint = 1-exp(-core.BETA/256)
    assert lower == 0 and upper > 0
    assert endpoint <= float(upper) <= endpoint+2/core.GRID
    assert core.GRID % upper.denominator == 0
    assert work["interval_bisections"] == 64
    lower, upper = core.interval(256, 256)
    endpoint = exp(-core.BETA/256)
    assert endpoint-2/core.GRID <= float(lower) <= endpoint and upper == 1
    lower, upper = core.interval(64, 256)
    assert lower < F(1, 4) < upper
    assert core.GRID % lower.denominator == core.GRID % upper.denominator == 0


def test_raw_context_envelope_does_not_inherit_selected_leaf_homogeneity():
    normal, wet = case("normal"), case("wet", "high")
    tables = {
        "SHORT_PASS": [dict(context=normal, counts={"DELIVERY": 99, "LOST": 1}),
                       dict(context=wet, counts={"DELIVERY": 50, "LOST": 50})],
        "DETOUR_PASS": [dict(context=normal, counts={"DELIVERY": 99, "LOST": 1, "RECOVERY": 0})],
        "RECOVERY_RETRY": [dict(context=normal, counts={"DELIVERY": 99, "LOST": 1})],
    }
    model = dict(tables=tables, selected_fields={operator: [] for operator in core.OPERATORS})
    raw = core.envelopes(model, wet)
    pooled = core.envelopes(model, wet, pooled=True)
    assert raw["SHORT_PASS"]["n"] == 100 and pooled["SHORT_PASS"]["n"] == 200
    assert raw["SHORT_PASS"]["bounds"]["LOST"][0] <= F(1, 2) <= raw["SHORT_PASS"]["bounds"]["LOST"][1]
    assert pooled["SHORT_PASS"]["bounds"]["LOST"][1] < F(1, 2)
    unknown = core.envelopes(model, case("blocked"))
    assert all(row["n"] == 0 for row in unknown.values())
    assert core.risk_bounds(unknown) == {"WAIT": F(0), "SHORT": F(1), "DETOUR_RETURN": F(1), "DETOUR_RETRY": F(1)}


def test_common_detour_extremum_accounts_for_the_probability_simplex():
    envelope = {
        "SHORT_PASS": dict(bounds={"DELIVERY": [F(1, 2), F(9, 10)], "LOST": [F(1, 10), F(1, 2)]}),
        "DETOUR_PASS": dict(bounds={"DELIVERY": [F(1, 5), F(1, 2)],
                                     "LOST": [F(1, 10), F(3, 5)],
                                     "RECOVERY": [F(1, 10), F(3, 5)]}),
        "RECOVERY_RETRY": dict(bounds={"DELIVERY": [F(1, 5), F(4, 5)], "LOST": [F(1, 5), F(4, 5)]}),
    }
    risks = core.risk_bounds(envelope)
    assert risks == {"WAIT": F(0), "SHORT": F(1, 2), "DETOUR_RETURN": F(3, 5), "DETOUR_RETRY": F(19, 25)}
    # f=.6, r=.2, delivery=.2 is feasible and jointly attains both bounds.
    mixed = F(2, 5)*risks["DETOUR_RETURN"]+F(3, 5)*risks["DETOUR_RETRY"]
    assert mixed == F(87, 125)
    assert mixed == F(3, 5)+F(3, 5)*F(1, 5)*F(4, 5)
    assert F(1, 5)+F(3, 5)*F(3, 5)*F(4, 5) < mixed
    assert risks["DETOUR_RETRY"] < F(3, 5)+F(3, 5)*F(4, 5)


def test_robust_optimization_changes_decision_without_splicing_joint_vector():
    point = {"WAIT": [F(0), F(0), F(0)],
             "SHORT": [F(-1, 10), F(1, 10), F(9, 10)],
             "DETOUR_RETURN": [F(-1, 20), F(1, 100), F(17, 20)],
             "DETOUR_RETRY": [F(-169, 1000), F(23, 200), F(177, 200)]}
    plugin = core.optimize(point, {name: vector[1] for name, vector in point.items()})
    work = Counter()
    robust = core.optimize(point, {"WAIT": F(0), "SHORT": F(1), "DETOUR_RETURN": F(1), "DETOUR_RETRY": F(1)}, work=work)
    assert robust["mix"] == [["SHORT", F(1, 20)], ["WAIT", F(19, 20)]]
    assert robust["mix"] != plugin["mix"]
    assert robust["predicted"] == [F(-1, 200), F(1, 200), F(9, 200)]
    assert robust["risk_upper"] == F(1, 20) and robust["predicted"][1] != robust["risk_upper"]
    assert robust["predicted_utility"] == F(7, 40)
    assert all(row["risk_upper"] <= F(1, 20) for row in robust["candidates"])
    assert work["optimization_pure_feasibility_checks"] == 4 and work["optimization_pair_checks"] == 6
    tied = dict(point, DETOUR_RETURN=list(point["SHORT"]))
    best = core.optimize(tied, {"WAIT": F(0), "SHORT": F(1), "DETOUR_RETURN": F(1), "DETOUR_RETRY": F(1)})
    assert best["mix"][0][0] == "DETOUR_RETURN"
