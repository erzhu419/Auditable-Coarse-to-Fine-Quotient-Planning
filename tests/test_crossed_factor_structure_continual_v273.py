from fractions import Fraction

from acfqp.science.crossed_factor_continual_v271 import (
    PHASES,
    SEEDS,
    SOURCE_FIT,
    SOURCE_PAIRS,
    TARGET_PAIRS,
    TARGET_PREFIXES,
    _contexts,
)
from acfqp.science.crossed_factor_structure_continual_v273 import (
    ACTION_MASKS,
    ARMS,
    _exact_vectors_for_phase,
    _law_for_phase,
    _masked_metrics,
    _observed_stream_for_phase,
    _stream_for_phase,
    run_replication,
)


def test_b_changes_only_available_actions():
    context = _contexts(((2, 2),), "structure")[0]
    assert _law_for_phase(context, "A") == _law_for_phase(context, "B")
    assert _law_for_phase(context, "A") == _law_for_phase(context, "A_prime")
    assert ACTION_MASKS["A"] == ACTION_MASKS["A_prime"]
    assert ACTION_MASKS["B"] == frozenset(("RETURN",))


def test_b_does_not_acquire_unavailable_retry_rows():
    context = _contexts(((2, 2),), "structure")[0]
    stream = _stream_for_phase(context, 273001, "B")
    observed = _observed_stream_for_phase(stream, "B")
    assert len(stream["RECOVERY_RETRY"]) == 64
    assert observed["RECOVERY_RETRY"] == []
    assert len(observed["SHORT_PASS"]) == 64
    assert len(observed["DETOUR_PASS"]) == 64


def test_masked_predictions_are_legal_and_legacy_reports_invalid():
    context = _contexts(((2, 2),), "structure")[0]
    exact = _exact_vectors_for_phase(context, "B")
    predicted = dict(exact)
    aware = _masked_metrics(predicted, exact, "B", apply_mask=True)
    legacy = _masked_metrics(predicted, exact, "B", apply_mask=False)
    assert all(not row["invalid_action"] for row in aware.values())
    assert sum(row["invalid_action"] for row in legacy.values()) >= 1
    assert all(row["exact_value_regret"] is None for row in legacy.values() if row["invalid_action"])


def test_source_selector_and_records_are_complete():
    result = run_replication()
    assert result["settings"]["dynamics_changed"] is False
    assert result["settings"]["query_changed"] is False
    for record in result["records"]:
        assert record["selected"]["source_fit_observations"] == len(SOURCE_PAIRS) * 3 * SOURCE_FIT
        for arm in ARMS:
            assert len(record["arms"][arm]) == len(TARGET_PAIRS) * len(PHASES) * len(TARGET_PREFIXES)


def test_b_fit_cost_has_two_observed_operators_and_aprime_restores_three():
    result = run_replication()
    for record in result["records"]:
        b0 = [row for row in record["arms"]["CONTINUAL_FACTOR_AWARE"]
              if row["phase"] == "B" and row["prefix_per_operator"] == 48]
        aprime0 = [row for row in record["arms"]["CONTINUAL_FACTOR_AWARE"]
                   if row["phase"] == "A_prime" and row["prefix_per_operator"] == 48]
        assert all(row["current_fit_observations_used"] == 96 for row in b0)
        assert all(row["current_fit_observations_used"] == 144 for row in aprime0)
        assert all(row["prior_fit_observations_used"] == 240 for row in aprime0)
        assert all(row["observed_operators"] == ["SHORT_PASS", "DETOUR_PASS"] for row in b0)
        assert all(row["observed_audit_observations"] == 32 for row in b0)
        assert all(row["observed_audit_observations"] == 48 for row in aprime0)


def test_summary_reports_invalid_actions_separately():
    result = run_replication()
    for arm in ARMS:
        for phase in PHASES:
            for prefix in TARGET_PREFIXES:
                bucket = result["summary"][arm][phase][str(prefix)]
                assert bucket["denominator_per_seed"] == len(TARGET_PAIRS) * 3
                assert len(bucket["invalid_action_counts"]) == len(SEEDS)
                assert all(Fraction(value) >= 0 for value in bucket["exact_regrets"])
