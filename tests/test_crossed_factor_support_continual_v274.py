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
from acfqp.science.crossed_factor_support_continual_v274 import (
    ARMS,
    B_DELAYED_PROBABILITY,
    NEW_SUCCESSOR,
    OLD_SUPPORT,
    _consequence_vector_dynamic,
    _exact_vectors_for_phase,
    _law_for_phase,
    _stream_for_phase,
    run_replication,
)


def test_b_expands_only_retry_support_and_law_sums_to_one():
    context = _contexts(((2, 2),), "support")[0]
    a = _law_for_phase(context, "A")
    b = _law_for_phase(context, "B")
    aprime = _law_for_phase(context, "A_prime")
    assert a == aprime
    assert set(b["RECOVERY_RETRY"]) == {"DELIVERY", "LOST", NEW_SUCCESSOR}
    assert set(a["RECOVERY_RETRY"]) == set(OLD_SUPPORT["RECOVERY_RETRY"])
    assert sum(b["RECOVERY_RETRY"].values()) == 1
    assert b["RECOVERY_RETRY"][NEW_SUCCESSOR] == B_DELAYED_PROBABILITY


def test_dynamic_stream_can_observe_new_successor_and_is_deterministic():
    context = _contexts(((2, 2),), "support")[0]
    first = _stream_for_phase(context, 274001, "B")
    second = _stream_for_phase(context, 274001, "B")
    assert first == second
    assert NEW_SUCCESSOR in first["RECOVERY_RETRY"]
    assert len(first["RECOVERY_RETRY"]) == 64


def test_delayed_semantics_are_predeclared_and_change_exact_vector():
    context = _contexts(((2, 2),), "support")[0]
    assert _exact_vectors_for_phase(context, "A") == _exact_vectors_for_phase(context, "A_prime")
    assert _exact_vectors_for_phase(context, "A") != _exact_vectors_for_phase(context, "B")
    assert _consequence_vector_dynamic({"operating": "low", "retry_cost": "19/20"},
                                       _law_for_phase(context, "B"))["DETOUR_RETRY"]


def test_source_selector_and_records_are_complete():
    result = run_replication()
    for record in result["records"]:
        assert record["selected"]["source_fit_observations"] == len(SOURCE_PAIRS) * 3 * SOURCE_FIT
        for arm in ARMS:
            assert len(record["arms"][arm]) == len(TARGET_PAIRS) * len(PHASES) * len(TARGET_PREFIXES)


def test_expanding_arm_discovers_support_without_future_prefix_leak():
    result = run_replication()
    rows = [row for row in result["records"][0]["arms"]["CONTINUAL_FACTOR_EXPANDING"]
            if row["target"]["id"] == "target_2_2" and row["phase"] == "B"]
    assert any(row["unknown_outcome_count"] > 0 for row in rows)
    first_unknown = min(row["prefix_per_operator"] for row in rows if row["unknown_outcome_count"] > 0)
    assert first_unknown in TARGET_PREFIXES[1:]
    zero = next(row for row in rows if row["prefix_per_operator"] == 0)
    assert NEW_SUCCESSOR not in zero["support_seen"]["RECOVERY_RETRY"]
    assert zero["new_successor_discovered"] is False


def test_reset_does_not_use_source_or_prior_audit_rows():
    result = run_replication()
    row = next(row for row in result["records"][0]["arms"]["RESET_DYNAMIC"]
               if row["phase"] == "A" and row["prefix_per_operator"] == 0)
    assert row["source_fit_observations_used"] == 0
    assert row["prior_fit_observations_used"] == 0
    assert row["current_fit_observations_used"] == 0

    # The model at B prefix zero is unchanged if only the completed A audit
    # suffix is altered; only A[:48] may be committed to the continual arm.
    continual = next(row for row in result["records"][0]["arms"]["CONTINUAL_FACTOR_EXPANDING"]
                     if row["phase"] == "B" and row["prefix_per_operator"] == 0)
    assert continual["new_successor_discovered"] is False


def test_summary_separates_abstain_and_coercion_counts():
    result = run_replication()
    for arm in ARMS:
        for phase in PHASES:
            for prefix in TARGET_PREFIXES:
                bucket = result["summary"][arm][phase][str(prefix)]
                assert bucket["denominator_per_seed"] == len(TARGET_PAIRS) * 3
                assert len(bucket["abstain_counts"]) == len(SEEDS)
                assert len(bucket["support_discovery_counts"]) == len(SEEDS)
                assert len(bucket["support_recall_counts"]) == len(SEEDS)
                assert all(Fraction(value) >= 0 for value in bucket["exact_regrets"])


def test_legacy_coercion_counts_include_committed_b_history():
    result = run_replication()
    rows = [row for row in result["records"][0]["arms"]["LEGACY_COERCE"]
            if row["phase"] == "A_prime" and row["prefix_per_operator"] == 0]
    assert any(row["coerced_unknown_count"] > 0 for row in rows)
