"""Synthetic observations only: prefix isolation, partitions, and interface."""
from copy import deepcopy
from fractions import Fraction as F

from acfqp.science import continual_route_kernels_v202 as core
from acfqp.science.structured_route_task_v201 import evaluate_plan


def case(weather="normal", operating="low", retry="17/20"):
    return dict(id=f"synthetic_{weather}_{operating}_{retry}", weather=weather,
                operating=operating, retry_cost=retry)


def observations(context, operator, successors):
    return [dict(context=dict(context), operator=operator, successor=value) for value in successors]


def small_batch():
    context = case()
    return (observations(context, "SHORT_PASS", ["DELIVERY"]*3+["LOST"])
            + observations(context, "DETOUR_PASS", ["DELIVERY"]*2+["LOST", "RECOVERY"])
            + observations(context, "RECOVERY_RETRY", ["DELIVERY"]))


def test_future_prefix_isolation_frozen_source_and_reset_phase():
    source = small_batch()
    future = observations(case("blocked", "high"), "SHORT_PASS", ["LOST"]*12)
    history = [source, future]
    prefix = core.fit(history[:1])
    snapshot = deepcopy(prefix)
    assert prefix["observations_used"] == len(source)
    core.fit(history)
    assert prefix == snapshot
    frozen = core.fit(history[:1], "FROZEN")
    retained = core.fit(history, "FROZEN", frozen=frozen)
    for key in ("tables", "scores", "selected_fields", "observations_used"):
        assert retained[key] == frozen[key]
    assert retained["fit_counts"]["frozen_model_copies"] == 1
    reset = core.fit(history, "RESET")
    assert reset["observations_used"] == len(future)
    empty = core.fit(history+[[]], "RESET")
    assert empty["observations_used"] == 0
    assert core.probabilities(empty, case(), "DETOUR_PASS") == {category: F(1, 3) for category in core.ALPHABETS["DETOUR_PASS"]}


def test_observed_counterexample_selects_weather_over_nuisance_fields():
    batches = []
    for weather, successor in (("normal", "DELIVERY"), ("blocked", "LOST")):
        batch = []
        for operating in ("low", "high"):
            for retry in ("17/20", "19/20"):
                batch += observations(case(weather, operating, retry), "SHORT_PASS", [successor]*8)
        batches.append(batch)
    initial = core.fit(batches[:1])
    assert initial["selected_fields"]["SHORT_PASS"] == []
    revised = core.fit(batches)
    assert revised["selected_fields"]["SHORT_PASS"] == ["weather"]
    assert len(revised["scores"]["SHORT_PASS"]) == 8
    assert core.probabilities(revised, case("normal", "high"), "SHORT_PASS")["DELIVERY"] == F(65, 66)
    assert core.probabilities(revised, case("blocked", "low"), "SHORT_PASS")["DELIVERY"] == F(1, 66)


def test_exact_posterior_normalization_and_unseen_projection_prior():
    full = core.fit([small_batch()], "FULL_CONTEXT")
    assert core.probabilities(full, case(), "SHORT_PASS") == {"DELIVERY": F(7, 10), "LOST": F(3, 10)}
    assert core.probabilities(full, case(), "DETOUR_PASS") == {"DELIVERY": F(5, 11), "LOST": F(3, 11), "RECOVERY": F(3, 11)}
    for operator in core.OPERATORS:
        probabilities = core.probabilities(full, case(), operator)
        assert sum(probabilities.values()) == 1 and all(value > 0 for value in probabilities.values())
    assert core.probabilities(full, case(operating="high"), "SHORT_PASS") == {"DELIVERY": F(1, 2), "LOST": F(1, 2)}
    weather = core.fit([small_batch()], "FIXED_WEATHER")
    assert core.probabilities(weather, case(operating="high"), "SHORT_PASS")["DELIVERY"] == F(7, 10)
    assert core.probabilities(weather, case("wet"), "DETOUR_PASS") == {category: F(1, 3) for category in core.ALPHABETS["DETOUR_PASS"]}


def test_known_cost_interface_and_joint_learned_successor_mapping():
    model = core.fit([small_batch()], "FIXED_WEATHER")
    task = core.predicted_graph(model, case(operating="high", retry="19/20"))
    assert task["SHORT_ENTRY"]["PASS"] == [(F(7, 10), "DELIVERY", F(-3, 25)),
                                          (F(3, 10), "LOST", F(-3, 25))]
    assert task["DETOUR_ENTRY"]["PASS"] == [(F(5, 11), "DELIVERY", F(-7, 100)),
                                           (F(3, 11), "LOST", F(-7, 100)),
                                           (F(3, 11), "RECOVERY", F(-7, 100))]
    assert task["RECOVERY"]["RETRY"] == [(F(3, 4), "DELIVERY", F(-19, 20)),
                                         (F(1, 4), "LOST", F(-19, 20))]
    assert task["DELIVERY"]["FINISH"] == [(F(1), "WON", F(0))]
    actual = evaluate_plan(task, 4, "DETOUR_RETRY")["root"]
    assert actual == (F(-181, 550), F(15, 44), F(29, 44))
