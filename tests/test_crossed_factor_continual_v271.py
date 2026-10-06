from copy import deepcopy
from fractions import Fraction

from acfqp.science.crossed_factor_continual_v271 import (
    ARMS,
    B_RETRY_DELIVERY,
    PHASES,
    SEEDS,
    SOURCE_FIT,
    SOURCE_PAIRS,
    TARGET_AUDIT,
    TARGET_FIT,
    TARGET_PAIRS,
    TARGET_PREFIXES,
    _contexts,
    _exact_vectors_for_phase,
    _law_for_phase,
    _model_for_arm,
    _stream_for_phase,
    _stream_seed,
    run_replication,
)
from acfqp.science.crossed_factor_transfer_v270 import select_factor_subsets


def test_phase_changes_only_retry_law_and_a_prime_restores_a():
    contexts = _contexts(TARGET_PAIRS, "check")
    for context in contexts:
        a = _law_for_phase(context, "A")
        b = _law_for_phase(context, "B")
        a_prime = _law_for_phase(context, "A_prime")
        assert a_prime == a
        assert b["SHORT_PASS"] == a["SHORT_PASS"]
        assert b["DETOUR_PASS"] == a["DETOUR_PASS"]
        assert b["RECOVERY_RETRY"] == {
            "DELIVERY": B_RETRY_DELIVERY,
            "LOST": 1 - B_RETRY_DELIVERY,
        }


def test_phase_marker_is_not_in_visible_context():
    context = _contexts(((1, 2),), "check")[0]
    assert set(context.as_dict()) == {"id", "road_profile", "retry_service"}


def test_streams_are_unique_and_deterministic_per_phase():
    context = _contexts(((1, 2),), "single")[0]
    streams = [_stream_for_phase(context, 271001 + index, phase)
               for index, phase in enumerate(PHASES)]
    assert streams == [_stream_for_phase(context, 271001 + index, phase)
                       for index, phase in enumerate(PHASES)]
    assert len({tuple(rows["RECOVERY_RETRY"]) for rows in streams}) == len(PHASES)


def test_source_selector_is_frozen_and_audit_cost_is_separate():
    result = run_replication()
    assert result["settings"]["phase_order"] == PHASES
    for record in result["records"]:
        assert record["selected"]["source_fit_observations"] == len(SOURCE_PAIRS) * 3 * SOURCE_FIT
        assert record["selected"]["source_audit_observations"] == len(SOURCE_PAIRS) * 3 * 16
        assert set(record["arms"]) == set(ARMS)
        assert record["phase_order"] == list(PHASES)
        for arm in ARMS:
            assert len(record["arms"][arm]) == len(TARGET_PAIRS) * len(PHASES) * len(TARGET_PREFIXES)
            assert {row["phase"] for row in record["arms"][arm]} == set(PHASES)
            assert all(row["target_audit_per_operator"] == TARGET_AUDIT
                       for row in record["arms"][arm])


def test_frozen_factor_does_not_change_with_prefix_and_continual_commits_only_fit_rows():
    result = run_replication()
    for record in result["records"]:
        for target in TARGET_PAIRS:
            target_id = f"target_{target[0]}_{target[1]}"
            rows = [row for row in record["arms"]["FROZEN_FACTOR"]
                    if row["target"]["id"] == target_id and row["phase"] == "B"]
            assert len({str(row["metrics"]) for row in rows}) == 1
        continual = [row for row in record["arms"]["CONTINUAL_FACTOR"]
                     if row["phase"] == "B" and row["prefix_per_operator"] == 0]
        assert all(row["prior_fit_observations_used"] == TARGET_FIT * 3 for row in continual)
        a_prime = [row for row in record["arms"]["CONTINUAL_FACTOR"]
                   if row["phase"] == "A_prime" and row["prefix_per_operator"] == 0]
        assert all(row["prior_fit_observations_used"] == 2 * TARGET_FIT * 3 for row in a_prime)


def test_audit_suffix_cannot_change_continual_model():
    source_contexts = _contexts(SOURCE_PAIRS, "source")
    target = _contexts((TARGET_PAIRS[0],), "target")[0]
    source_streams = {context.context_id: _stream_for_phase(context, 271100 + index, "A")
                      for index, context in enumerate(source_contexts)}
    selected = select_factor_subsets(source_contexts, source_streams)["selected_fields"]
    current = _stream_for_phase(target, 271200, "A")
    model = _model_for_arm("CONTINUAL_FACTOR", target, source_contexts, source_streams,
                           selected, [], current, 48)
    committed = _model_for_arm("CONTINUAL_FACTOR", target, source_contexts, source_streams,
                               selected, [("A", current)], current, 0)
    assert model == committed
    changed_source = deepcopy(source_streams)
    changed_current = deepcopy(current)
    for rows in [*changed_source.values(), changed_current]:
        for operator in rows:
            rows[operator][48:] = ["LOST"] * 16
    assert selected == select_factor_subsets(source_contexts, changed_source)["selected_fields"]
    changed_model = _model_for_arm("CONTINUAL_FACTOR", target, source_contexts, changed_source,
                                  selected, [("A", changed_current)], changed_current, 0)
    assert model == changed_model


def test_future_fit_rows_do_not_enter_current_prefix():
    source_contexts = _contexts(SOURCE_PAIRS, "source")
    target = _contexts((TARGET_PAIRS[0],), "target")[0]
    source_streams = {context.context_id: _stream_for_phase(context, 271100 + index, "A")
                      for index, context in enumerate(source_contexts)}
    selected = select_factor_subsets(source_contexts, source_streams)["selected_fields"]
    current = _stream_for_phase(target, 271200, "B")
    changed = deepcopy(current)
    for operator in changed:
        changed[operator][4:] = ["LOST"] * 60
    for arm in ARMS:
        assert _model_for_arm(arm, target, source_contexts, source_streams, selected, [], current, 4) == _model_for_arm(
            arm, target, source_contexts, source_streams, selected, [], changed, 4)


def test_target_stream_seed_map_has_no_cross_phase_or_seed_collision():
    seeds = [_stream_seed(seed, target_index, phase_index)
             for seed in SEEDS for target_index in range(len(TARGET_PAIRS))
             for phase_index in range(len(PHASES))]
    assert len(seeds) == len(set(seeds))


def test_summary_denominator_and_finite_regrets():
    result = run_replication()
    assert result["settings"]["seeds"] == list(SEEDS)
    for arm in ARMS:
        for phase in PHASES:
            assert set(map(int, result["summary"][arm][phase])) == set(TARGET_PREFIXES)
            for prefix in TARGET_PREFIXES:
                bucket = result["summary"][arm][phase][str(prefix)]
                assert bucket["denominator_per_seed"] == len(TARGET_PAIRS) * 3
                assert len(bucket["policy_correct_counts"]) == len(SEEDS)
                assert all(Fraction(value) >= 0 for value in bucket["exact_regrets"])


def test_phase_exact_vectors_differ_in_retry_and_restore():
    target = _contexts(((2, 2),), "target")[0]
    assert _exact_vectors_for_phase(target, "A") == _exact_vectors_for_phase(target, "A_prime")
    assert _exact_vectors_for_phase(target, "A") != _exact_vectors_for_phase(target, "B")
