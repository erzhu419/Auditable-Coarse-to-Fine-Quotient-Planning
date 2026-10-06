"""Four bounded witnesses using synthetic observations or declared task laws."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from itertools import product

from acfqp.science import conditioned_mechanisms_v205 as core
from acfqp.science import mechanism_switch_task_v205 as task
from acfqp.science import structured_route_task_v201 as mechanics


def case(weather, operating="low", retry_cost="17/20"):
    return dict(id=f"synthetic_{weather}_{operating}_{retry_cost}", weather=weather,
                operating=operating, retry_cost=retry_cost)


def synthetic_history():
    counts = {
        "normal": {"SHORT_PASS": {"DELIVERY": 80, "LOST": 20},
                   "DETOUR_PASS": {"DELIVERY": 90, "LOST": 1, "RECOVERY": 9},
                   "RECOVERY_RETRY": {"DELIVERY": 30, "LOST": 70}},
        "wet": {"SHORT_PASS": {"DELIVERY": 99, "LOST": 1},
                "DETOUR_PASS": {"DELIVERY": 65, "LOST": 25, "RECOVERY": 10},
                "RECOVERY_RETRY": {"DELIVERY": 90, "LOST": 10}},
        "blocked": {"SHORT_PASS": {"DELIVERY": 30, "LOST": 70},
                    "DETOUR_PASS": {"DELIVERY": 90, "LOST": 1, "RECOVERY": 9},
                    "RECOVERY_RETRY": {"DELIVERY": 30, "LOST": 70}},
    }
    source, revision = [], []
    contexts = ([case("normal", operating, retry) for operating, retry in product(("low", "high"), ("17/20", "19/20"))]
                + [case(weather, "high", retry) for weather, retry in product(("wet", "blocked"), ("17/20", "19/20"))])
    for context in contexts:
        events = source if context["weather"] == "normal" else revision
        for operator in core.OPERATORS:
            for category, n in counts[context["weather"]][operator].items():
                events.extend(dict(context=context, operator=operator, successor=category) for _ in range(n))
    return source, revision


def test_observed_conditions_route_acquisition_and_local_pilots_disappear():
    source, revision = synthetic_history()
    before = core.fit([source], "REVISED")
    learned = core.fit([source, revision], "REVISED")
    for operator in core.OPERATORS[:2]:
        assert before["selected_fields"][operator] == []
        assert learned["selected_fields"][operator] == ["weather"]
    for weather, expected in (("wet", "SHORT_PASS"), ("blocked", "DETOUR_PASS")):
        target = case(weather)
        choice = core.choose(learned, target, core.make_plan(learned, target))
        assert choice["operator"] == expected and not choice["pilot"]
        assert all(n == 200 for n in choice["projection_counts"].values())
    local = core.fit([source, revision], "FULL_CONTEXT")
    target = case("wet")
    first = core.choose(local, target, core.make_plan(local, target))
    assert first["operator"] == "SHORT_PASS" and first["pilot"]
    assert first["policy"] is None and first["projection_counts"] == {"SHORT_PASS": 0, "DETOUR_PASS": 0}
    core.update(local, target, "SHORT_PASS", {"DELIVERY": 16, "LOST": 0})
    second = core.choose(local, target, core.make_plan(local, target))
    assert second["operator"] == "DETOUR_PASS" and second["pilot"]
    assert second["projection_counts"] == {"SHORT_PASS": 16, "DETOUR_PASS": 0}
    core.update(local, target, "DETOUR_PASS", {"DELIVERY": 16, "LOST": 0, "RECOVERY": 0})
    third = core.choose(local, target, core.make_plan(local, target))
    assert not third["pilot"] and third["policy"] is not None
    assert third["projection_counts"] == {"SHORT_PASS": 16, "DETOUR_PASS": 16}


def test_fixed_conditions_use_all_prefix_counts_then_real_target_updates():
    source, revision = synthetic_history()
    initial = core.fit([source], "REVISED")
    full = core.fit([source, revision], "FULL_CONTEXT")
    initial_before, full_before = deepcopy(initial), deepcopy(full)
    work = Counter()
    fixed = core.fixed_model(initial, full, work)
    assert fixed["arm"] == "FIXED" and fixed["selected_fields"] == initial["selected_fields"]
    assert fixed["tables"] == full["tables"] and fixed["observations_used"] == 2400
    assert initial == initial_before and full == full_before
    assert work["fixed_model_calls"] == 1 and work["score_candidates"] == 3
    assert all(len(scores) == 1 for scores in fixed["scores"].values())
    target = case("wet")
    old = core.probabilities(initial, target, "SHORT_PASS")
    prefix = core.probabilities(fixed, target, "SHORT_PASS")
    assert prefix != old  # Conditions freeze; posterior parameters do not.
    fields, scores = deepcopy(fixed["selected_fields"]), deepcopy(fixed["scores"])
    core.update(fixed, target, "SHORT_PASS", {"DELIVERY": 16, "LOST": 0})
    assert fixed["observations_used"] == 2416
    assert fixed["selected_fields"] == fields and fixed["scores"] == scores
    assert core.probabilities(fixed, target, "SHORT_PASS")["DELIVERY"] > prefix["DELIVERY"]
    assert core.make_plan(fixed, target)["envelopes"]["SHORT_PASS"]["n"] == 16
    assert initial == initial_before and full == full_before


def test_query_vectors_follow_their_own_reached_recovery_choice():
    source, revision = synthetic_history()
    learned = core.fit([source, revision], "REVISED")
    target = case("blocked")
    decisions = core.query_decisions(learned, target)
    goal, risk = decisions["goal"], decisions["risk"]
    assert goal["policy"]["START", 4] == risk["policy"]["START", 4] == "DETOUR"
    assert goal["policy"]["RECOVERY", 2] == "RETRY"
    assert risk["policy"]["RECOVERY", 2] == "RETURN"
    detour = core.probabilities(learned, target, "DETOUR_PASS")
    retry = core.probabilities(learned, target, "RECOVERY_RETRY")
    assert goal["values"]["RECOVERY", 2] == (-F(17, 20), retry["LOST"], retry["DELIVERY"])
    assert risk["values"]["START", 4] == (-F(1, 20), detour["LOST"], detour["DELIVERY"])
    assert goal["values"]["START", 4][1] > risk["values"]["START", 4][1]
    assert goal["values"]["START", 4][2] > risk["values"]["START", 4][2]
    graph = core.predicted_graph(learned, target)
    for query, decision in decisions.items():
        own = mechanics.evaluate_plan(graph, 4, decision["policy"])
        assert own["root"] == decision["values"]["START", 4]
        if query in ("goal", "risk"):
            assert ("RECOVERY", 2) in own["policy"]
    assert decisions["reward"]["policy"]["START", 4] == "WAIT"


def test_declared_task_requires_context_switch_and_own_continuation():
    cases = task.roster()
    assert len(cases) == 12 and cases[0]["id"] == "v205_normal_low_r17_20"
    assert cases[-1]["id"] == "v205_blocked_high_r19_20"
    qualified = task.qualify()
    assert qualified["qualified"] and all(qualified["conditions"].values())
    assert qualified["constant_comparison"]["contexts"] == 4
    assert qualified["constant_comparison"]["gap"] == F(2318, 1725)
    records = {row["context_id"]: row for row in qualified["records"]}
    wet = records["v205_wet_low_r17_20"]
    assert wet["hard_optimum"]["mix"] == [("SHORT", F(1))]
    assert wet["hard_optimum"]["vector"] == [-F(1, 10), F(1, 100), F(99, 100)]
    blocked = records["v205_blocked_low_r17_20"]
    assert dict(blocked["hard_optimum"]["mix"]) == {"DETOUR_RETURN": F(37, 57), "DETOUR_RETRY": F(20, 57)}
    assert blocked["hard_optimum"]["vector"][1] == F(1, 20)
    assert blocked["queries"]["goal"]["recovery_reached"] and blocked["queries"]["risk"]["recovery_reached"]
    assert blocked["queries"]["goal"]["recovery_action"] == "RETRY"
    assert blocked["queries"]["risk"]["recovery_action"] == "RETURN"
    assert all(row["queries"][query]["gap"] >= 2 for row in qualified["records"] for query in ("goal", "risk"))
