from fractions import Fraction

from acfqp.science.online_support_continual_v275 import (
    ARMS,
    EPISODES_PER_PHASE,
    PHASES,
    SEEDS,
    TRIALS_PER_EPISODE,
    _contexts,
    _execute_policy,
    _sample_outcome,
    _source_counts,
    select_factor_subsets,
    run_replication,
)
from acfqp.science.crossed_factor_support_continual_v274 import NEW_SUCCESSOR
from acfqp.science.crossed_factor_continual_v271 import SOURCE_PAIRS
from acfqp.science.crossed_factor_transfer_v270 import _stream


def test_counter_sampling_is_deterministic_and_only_route_policy_adds_retry():
    context = _contexts(((2, 2),), "online")[0]
    assert _sample_outcome(context, "B", SEEDS[0], 1, 0, 0, "RECOVERY_RETRY") == _sample_outcome(
        context, "B", SEEDS[0], 1, 0, 0, "RECOVERY_RETRY"
    )
    assert _execute_policy(context, "B", SEEDS[0], 1, 0, "WAIT") == []
    return_events = _execute_policy(context, "B", SEEDS[0], 1, 0, "DETOUR_RETURN")
    assert all(event["operator"] != "RECOVERY_RETRY" for event in return_events)
    short_events = _execute_policy(context, "B", SEEDS[0], 1, 0, "SHORT")
    assert [event["operator"] for event in short_events] == ["SHORT_PASS"]
    for seed in range(10):
        retry_events = _execute_policy(context, "B", seed, 1, 0, "DETOUR_RETRY")
        assert all(event["operator"] in {"DETOUR_PASS", "RECOVERY_RETRY"} for event in retry_events)
        if retry_events[0]["outcome"] == "RECOVERY":
            assert retry_events[-1]["operator"] == "RECOVERY_RETRY"
        else:
            assert len(retry_events) == 1


def test_source_audit_suffix_is_not_consumed_by_source_model():
    source_contexts = _contexts(SOURCE_PAIRS, "source")
    target = _contexts(((1, 1),), "target")[0]
    streams = {context.context_id: _stream(context, 100 + index) for index, context in enumerate(source_contexts)}
    selected = select_factor_subsets(source_contexts, streams)["selected_fields"]
    before = _source_counts(target, source_contexts, streams, selected)
    changed = {context_id: {operator: list(values) for operator, values in rows.items()} for context_id, rows in streams.items()}
    for rows in changed.values():
        for operator, values in rows.items():
            values[48:] = ["DELIVERY" if value != "DELIVERY" else "LOST" for value in values[48:]]
    after = _source_counts(target, source_contexts, changed, selected)
    assert before == after


def test_run_has_one_cross_context_lifecycle_and_separate_source_cost():
    result = run_replication()
    assert result["settings"]["phase_order"] == PHASES
    assert result["settings"]["episodes_per_phase"] == EPISODES_PER_PHASE
    assert result["settings"]["trials_per_episode"] == TRIALS_PER_EPISODE
    for record in result["records"]:
        for arm in ARMS:
            rows = record["arms"][arm]
            assert len(rows) == len(PHASES) * EPISODES_PER_PHASE * TRIALS_PER_EPISODE
            expected_source = 0 if arm == "PHASE_RESET_ONLINE" else 720
            assert all(row["source_fit_observations_available"] == expected_source for row in rows)
            assert all(row["source_audit_observations_available"] == (0 if arm == "PHASE_RESET_ONLINE" else 240) for row in rows)


def test_history_changes_only_after_events_and_phase_reset_is_local():
    result = run_replication()
    for record in result["records"]:
        reset_rows = record["arms"]["PHASE_RESET_ONLINE"]
        a_first = next(row for row in reset_rows if row["phase"] == "A" and row["episode"] == 1 and row["trial"] == 0)
        b_first = next(row for row in reset_rows if row["phase"] == "B" and row["episode"] == 1 and row["trial"] == 0)
        a_prime_first = next(row for row in reset_rows if row["phase"] == "A_prime" and row["episode"] == 1 and row["trial"] == 0)
        assert a_first["history_before"] == 0
        assert b_first["history_before"] == 0
        assert a_prime_first["history_before"] == 0
        assert any(row["history_before"] > 0 for row in reset_rows if row["phase"] == "A" and row["episode"] > 1)
        for row in reset_rows:
            assert row["history_after"] - row["history_before"] == row["executed_event_count"]
            assert row["committed_history_after"] - row["committed_history_before"] == row["executed_event_count"]


def test_continual_lifecycle_keeps_history_across_contexts_and_frozen_has_none():
    result = run_replication()
    for record in result["records"]:
        continual = record["arms"]["CONTINUAL_FACTOR_ONLINE"]
        assert continual[-1]["model_visible_history"] > 0
        assert any(row["context"]["id"] != continual[0]["context"]["id"] for row in continual)
        frozen = record["arms"]["FROZEN_FACTOR_ONLINE"]
        assert all(row["history_before"] == 0 and row["history_after"] == 0 for row in frozen)
        assert any(row["committed_history_after"] > 0 for row in frozen)


def test_only_executed_support_can_be_observed():
    result = run_replication()
    for record in result["records"]:
        for arm in ARMS:
            rows = record["arms"][arm]
            for row in rows:
                events = row["executed_events"]
                if row["new_support_observed"]:
                    assert any(event["outcome"] == NEW_SUCCESSOR for event in events)
                if row["predicted_policy"] == "WAIT":
                    assert events == []
                if row["predicted_policy"] == "DETOUR_RETURN":
                    assert all(event["operator"] != "RECOVERY_RETRY" for event in events)
                for event in events:
                    assert event["operator"] in {"SHORT_PASS", "DETOUR_PASS", "RECOVERY_RETRY"}


def test_summary_denominators_and_finite_regret():
    result = run_replication()
    for arm in ARMS:
        for phase in PHASES:
            for episode in range(1, EPISODES_PER_PHASE + 1):
                bucket = result["summary"][arm][phase][str(episode)]
                assert bucket["denominator"] == len(SEEDS) * TRIALS_PER_EPISODE
                assert Fraction(bucket["mean_exact_regret"]) >= 0
