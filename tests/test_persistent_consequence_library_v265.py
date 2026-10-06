from fractions import Fraction

from acfqp.science.persistent_consequence_library_v265 import (
    FIT_PER_OPERATOR,
    AUDIT_PER_OPERATOR,
    SEEDS,
    run_replication,
)


def test_all_arms_use_the_same_fit_prefix_and_audit_suffix():
    result = run_replication()
    for record in result["records"]:
        for arm, rows in record["arms"].items():
            assert [row["observations"] for row in rows] == [
                (index + 1) * FIT_PER_OPERATOR * 3 for index in range(4)
            ]
            assert all(row["audit_observations"] == AUDIT_PER_OPERATOR * 3 for row in rows)


def test_guarded_arm_records_an_explicit_assignment_state():
    result = run_replication()
    for record in result["records"]:
        for row in record["arms"]["GUARDED_LIBRARY"]:
            assert row["assignment"]["reason"] in {
                "initial", "reuse_confident", "abstain_local_split"
            }
            assert "audit_brier" in row


def test_summary_has_all_frozen_fresh_seeds_and_finite_regrets():
    result = run_replication()
    assert result["settings"]["seeds"] == list(SEEDS)
    assert result["settings"]["fit_per_operator"] == 48
    assert result["settings"]["audit_per_operator"] == 16
    for arm in ("RESET", "GLOBAL", "LEGACY_LIBRARY", "GUARDED_LIBRARY"):
        assert len(result["summary"][arm]["policy_correct_counts"]) == len(SEEDS)
        assert all(Fraction(value) >= 0 for value in result["summary"][arm]["exact_regrets"])
