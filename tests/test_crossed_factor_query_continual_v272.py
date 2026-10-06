from fractions import Fraction

from acfqp.science.crossed_factor_continual_v271 import (
    ARMS,
    PHASES,
    SEEDS,
    SOURCE_FIT,
    SOURCE_PAIRS,
    TARGET_AUDIT,
    TARGET_PAIRS,
    TARGET_PREFIXES,
    _contexts,
    _stream_for_phase,
)
from acfqp.science.crossed_factor_query_continual_v272 import (
    B_QUERIES,
    PHASE_QUERIES,
    _queries_for_phase,
    run_replication,
)
from acfqp.science.persistent_consequence_library_v263 import QUERIES


def test_only_b_risk_query_changes_and_aprime_restores_a():
    assert PHASE_QUERIES["A"] == QUERIES
    assert PHASE_QUERIES["A_prime"] == QUERIES
    assert B_QUERIES["reward"] == QUERIES["reward"]
    assert B_QUERIES["goal"] == QUERIES["goal"]
    assert B_QUERIES["risk"] == (Fraction(1), Fraction(1), Fraction(4))
    assert B_QUERIES["risk"] != QUERIES["risk"]


def test_dynamics_are_identical_across_phases():
    context = _contexts(((2, 2),), "query")[0]
    assert _stream_for_phase(context, 272001, "A") != _stream_for_phase(context, 272002, "B")
    # Independent streams differ, but their declared generator law is the same.
    from acfqp.science.crossed_factor_query_continual_v272 import _law_for_phase
    assert _law_for_phase(context, "A") == _law_for_phase(context, "B")
    assert _law_for_phase(context, "A") == _law_for_phase(context, "A_prime")


def test_query_change_is_visible_in_exact_action_for_one_target():
    result = run_replication()
    rows = [row for row in result["records"][0]["arms"]["FROZEN_FACTOR"]
            if row["target"]["id"] == "target_2_2" and row["prefix_per_operator"] == 0]
    a = next(row for row in rows if row["phase"] == "A")
    b = next(row for row in rows if row["phase"] == "B")
    aprime = next(row for row in rows if row["phase"] == "A_prime")
    assert a["query_bank"] == aprime["query_bank"]
    assert a["query_bank"] != b["query_bank"]
    assert a["metrics"]["risk"]["exact_policy"] != b["metrics"]["risk"]["exact_policy"]


def test_selector_is_frozen_and_phase_records_are_complete():
    result = run_replication()
    assert result["settings"]["dynamics_changed"] is False
    assert result["settings"]["phase_order"] == PHASES
    for record in result["records"]:
        assert record["selected"]["source_fit_observations"] == len(SOURCE_PAIRS) * 3 * SOURCE_FIT
        assert record["selected"]["source_audit_observations"] == len(SOURCE_PAIRS) * 3 * 16
        for arm in ARMS:
            assert len(record["arms"][arm]) == len(TARGET_PAIRS) * len(PHASES) * len(TARGET_PREFIXES)
            assert all(row["target_audit_per_operator"] == TARGET_AUDIT
                       for row in record["arms"][arm])


def test_summary_denominators_and_query_bank_keys():
    result = run_replication()
    for arm in ARMS:
        for phase in PHASES:
            assert set(_queries_for_phase(phase)) == {"reward", "risk", "goal"}
            for prefix in TARGET_PREFIXES:
                bucket = result["summary"][arm][phase][str(prefix)]
                assert bucket["denominator_per_seed"] == len(TARGET_PAIRS) * 3
                assert len(bucket["policy_correct_counts"]) == len(SEEDS)
                assert all(Fraction(value) >= 0 for value in bucket["exact_regrets"])


def test_b_query_prefix_records_use_the_frozen_b_bank():
    result = run_replication()
    for arm in ARMS:
        for record in result["records"]:
            rows = [row for row in record["arms"][arm] if row["phase"] == "B"]
            assert all(row["query_bank"]["risk"] == ["1", "1", "4"] for row in rows)
