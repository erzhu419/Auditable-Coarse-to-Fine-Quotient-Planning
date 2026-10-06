from copy import deepcopy
from fractions import Fraction as F

import pytest

from acfqp.science import online_factor_repair_v276 as v276
from acfqp.science.online_support_continual_v275 import OnlineLearner


def source_slice(seed=275402):
    contexts = v276._contexts(v276.SOURCE_PAIRS, "source")
    streams = {
        context.context_id: v276._stream(context, seed + index)
        for index, context in enumerate(contexts)
    }
    return contexts, streams


def uncovered_short_learner():
    contexts, streams = source_slice()
    initial = {
        "SHORT_PASS": ("road_profile", "retry_service"),
        "DETOUR_PASS": (),
        "RECOVERY_RETRY": (),
    }
    learner = OnlineLearner("CONTINUAL_FACTOR_ONLINE", dict(initial), contexts, streams)
    return learner, initial


def test_empty_online_history_preserves_v270_factor_scoring():
    contexts, streams = source_slice()
    original = v276.select_factor_subsets(contexts, streams)
    online = v276.select_online_fields(contexts, streams, [])
    assert online["selected_fields"] == original["selected_fields"]
    assert online["online_events_used"] == 0
    for operator in v276.OPERATORS:
        for before, after in zip(original["scores"][operator], online["scores"][operator]):
            assert tuple(before["fields"]) == tuple(after["fields"])
            assert after["score"] == pytest.approx(before["score"], abs=1e-12)


def test_factor_scoring_does_not_consume_source_audit_suffix():
    contexts, streams = source_slice()
    before = v276.select_online_fields(contexts, streams, [])
    changed = deepcopy(streams)
    for operators in changed.values():
        for outcomes in operators.values():
            outcomes[v276.SOURCE_FIT:] = [
                "LOST" if outcome == "DELIVERY" else "DELIVERY"
                for outcome in outcomes[v276.SOURCE_FIT:]
            ]
    assert v276.select_online_fields(contexts, changed, []) == before


def test_only_committed_operator_events_change_its_factor_score():
    contexts, streams = source_slice()
    target = v276._contexts(((1, 1),), "target")[0]
    before = v276.select_online_fields(contexts, streams, [])
    event = (target, "B", 1, 0, "RECOVERY_RETRY", "DELAYED")
    after = v276.select_online_fields(contexts, streams, [event])
    assert after["online_events_used"] == 1
    assert after["scores"]["SHORT_PASS"] == before["scores"]["SHORT_PASS"]
    assert after["scores"]["DETOUR_PASS"] == before["scores"]["DETOUR_PASS"]
    assert after["scores"]["RECOVERY_RETRY"] != before["scores"]["RECOVERY_RETRY"]


def test_coverage_quota_uses_initial_keys_and_matching_committed_outcomes():
    learner, initial = uncovered_short_learner()
    target, other = v276._contexts(((1, 1), (1, 2)), "target")
    learner.selected = {operator: () for operator in v276.OPERATORS}
    for trial in range(v276.COVERAGE_QUOTA):
        learner.observe(other, "A", 1, trial, "SHORT_PASS", "DELIVERY")
        learner.observe(target, "A", 1, trial, "DETOUR_PASS", "DELIVERY")
    assert v276.coverage_request(learner, initial, target) == "SHORT_PASS"
    for trial in range(v276.COVERAGE_QUOTA - 1):
        learner.observe(target, "A", 1, trial, "SHORT_PASS", "DELIVERY")
    assert v276.coverage_request(learner, initial, target) == "SHORT_PASS"
    learner.observe(target, "A", 1, v276.COVERAGE_QUOTA - 1, "SHORT_PASS", "LOST")
    assert v276.coverage_request(learner, initial, target) is None
    learner.begin_phase("B")
    assert v276.coverage_request(learner, initial, target) is None
    assert v276.coverage_request(learner, initial, other) is None


def test_source_covered_bucket_does_not_pay_online_coverage_quota():
    learner, _ = uncovered_short_learner()
    initial = {operator: () for operator in v276.OPERATORS}
    target = v276._contexts(((1, 1),), "target")[0]
    learner.selected = {operator: ("road_profile", "retry_service") for operator in v276.OPERATORS}
    assert learner.history == []
    assert v276.coverage_request(learner, initial, target) is None


def test_coverage_retry_waits_for_actual_recovery_outcome():
    learner, initial = uncovered_short_learner()
    initial["SHORT_PASS"] = ()
    initial["RECOVERY_RETRY"] = ("road_profile", "retry_service")
    target = v276._contexts(((1, 1),), "target")[0]
    assert v276.coverage_request(learner, initial, target) == "RECOVERY_RETRY"
    for trial in range(v276.COVERAGE_QUOTA):
        learner.observe(target, "A", 1, trial, "DETOUR_PASS", "DELIVERY")
    assert v276.coverage_request(learner, initial, target) == "RECOVERY_RETRY"
    for trial in range(v276.COVERAGE_QUOTA):
        learner.observe(target, "A", 2, trial, "RECOVERY_RETRY", "LOST")
    assert v276.coverage_request(learner, initial, target) is None


def test_only_legal_reached_route_operators_draw_outcomes(monkeypatch):
    context = v276._contexts(((2, 2),), "target")[0]
    law = {
        "SHORT_PASS": {"DELIVERY": F(1)},
        "DETOUR_PASS": {"RECOVERY": F(1)},
        "RECOVERY_RETRY": {"DELAYED": F(1)},
    }
    monkeypatch.setattr(v276, "_law_for_phase", lambda _context, _phase: law)
    run = lambda policy: v276.execute_policy(context, "B", 276402, 1, 0, policy)
    assert run("WAIT") == []
    assert [event["operator"] for event in run("SHORT")] == ["SHORT_PASS"]
    assert [event["operator"] for event in run("DETOUR_RETURN")] == ["DETOUR_PASS"]
    retry = run("DETOUR_RETRY")
    assert [(event["operator"], event["outcome"]) for event in retry] == [
        ("DETOUR_PASS", "RECOVERY"), ("RECOVERY_RETRY", "DELAYED")
    ]
    law["DETOUR_PASS"] = {"DELIVERY": F(1)}
    assert [event["operator"] for event in run("DETOUR_RETRY")] == ["DETOUR_PASS"]


def test_sampling_keys_are_distinct_for_frozen_reached_opportunities():
    targets = v276._contexts(v276.TARGET_PAIRS, "target")
    keys = []
    for seed in v276.SEEDS:
        for phase in v276.PHASES:
            for episode in range(1, v276.EPISODES_PER_PHASE + 1):
                for trial in range(v276.TRIALS_PER_EPISODE):
                    context = targets[trial % len(targets)]
                    for visit, operator in ((0, "SHORT_PASS"), (0, "DETOUR_PASS"), (1, "RECOVERY_RETRY")):
                        keys.append(v276.sampling_key(seed, context, phase, episode, trial, visit, operator))
    assert len(keys) == len(set(keys))


def test_lifecycle_primary_regret_charges_the_forced_route(monkeypatch):
    # A one-opportunity fixture tests accounting without running the frozen cohort.
    monkeypatch.setattr(v276, "PHASES", ("A",))
    monkeypatch.setattr(v276, "EPISODES_PER_PHASE", 1)
    monkeypatch.setattr(v276, "TRIALS_PER_EPISODE", 1)
    monkeypatch.setattr(v276, "TARGET_PAIRS", ((2, 2),))
    monkeypatch.setattr(v276, "execute_policy", lambda *_args: [
        {"operator": "SHORT_PASS" if _args[-1] == "SHORT" else "DETOUR_PASS", "outcome": "LOST", "visit": 0}
    ])
    oracle_vectors = {
        "WAIT": (F(0), F(0), F(0)),
        "SHORT": (F(0), F(0), F(0)),
        "DETOUR_RETURN": (F(0), F(0), F(0)),
        "DETOUR_RETRY": (F(0), F(0), F(1)),
    }
    monkeypatch.setattr(v276, "_exact_vectors", lambda *_args: oracle_vectors)
    result = v276.run_lifecycle(275402, 276402)
    for arm in ("COVERED_FIXED", "COVERED_REVISED"):
        row = result["arms"][arm][0]
        assert row["recommended_policy"] == "DETOUR_RETRY"
        assert row["executed_policy"] == "SHORT"
        assert row["coverage_request"] == "SHORT_PASS"
        assert row["recommendation_regret"] == "0"
        assert row["executed_regret"] == "4"
        assert result["totals"][arm]["executed_regret"] == "4"
        assert row["history_after"] - row["history_before"] == len(row["events"])

