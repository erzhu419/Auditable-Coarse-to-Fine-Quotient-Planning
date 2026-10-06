from fractions import Fraction

from acfqp.science.persistent_consequence_library_v263 import QUERIES
from acfqp.science.persistent_consequence_library_v267 import (
    ALL_QUERIES,
    HELDOUT_QUERIES,
    FIT_PER_OPERATOR,
    AUDIT_PER_OPERATOR,
    SEEDS,
    run_replication,
)


def test_heldout_query_bank_is_fixed_and_disjoint():
    assert set(HELDOUT_QUERIES).isdisjoint(QUERIES)
    assert HELDOUT_QUERIES == {
        "moderate_risk": (Fraction(1), Fraction(2), Fraction(2)),
        "high_goal": (Fraction(1), Fraction(1), Fraction(6)),
        "strict_risk": (Fraction(1), Fraction(6), Fraction(2)),
    }
    assert set(ALL_QUERIES) == set(QUERIES) | set(HELDOUT_QUERIES)


def test_all_arms_share_the_same_fit_prefix_and_audit_suffix():
    result = run_replication()
    expected = [(index + 1) * FIT_PER_OPERATOR * 3 for index in range(4)]
    for record in result["records"]:
        for rows in record["arms"].values():
            assert [row["observations"] for row in rows] == expected
            assert all(row["audit_observations"] == AUDIT_PER_OPERATOR * 3 for row in rows)


def test_both_agreement_arms_record_candidate_checks_and_frozen_reasons():
    result = run_replication()
    allowed = {"initial", "reuse_all_query_actions", "abstain_local_split"}
    for record in result["records"]:
        for arm in ("PRIMARY_AGREEMENT", "ALL_QUERY_AGREEMENT"):
            for row in record["arms"][arm]:
                assignment = row["assignment"]
                assert assignment["reason"] in allowed
                assert assignment["candidate_count_before"] == len(assignment["candidate_checks"])
                assert all(set(check["agreement"]) == set(QUERIES if arm == "PRIMARY_AGREEMENT" else ALL_QUERIES)
                           for check in assignment["candidate_checks"])


def test_summary_has_one_primary_and_heldout_record_per_seed():
    result = run_replication()
    assert result["settings"]["seeds"] == list(SEEDS)
    for arm in ("RESET", "GLOBAL", "PRIMARY_AGREEMENT", "ALL_QUERY_AGREEMENT"):
        summary = result["summary"][arm]
        assert len(summary["primary_policy_correct_counts"]) == len(SEEDS)
        assert len(summary["heldout_policy_correct_counts"]) == len(SEEDS)
        assert len(summary["primary_exact_regrets"]) == len(SEEDS)
        assert len(summary["heldout_exact_regrets"]) == len(SEEDS)
        assert len(summary["primary_set_action_agreement_counts"]) == len(SEEDS)
        assert len(summary["heldout_set_action_agreement_counts"]) == len(SEEDS)
        assert len(summary["combined_set_action_agreement_counts"]) == len(SEEDS)


def test_summary_regrets_match_records_for_both_query_banks():
    result = run_replication()
    for arm in ("RESET", "GLOBAL", "PRIMARY_AGREEMENT", "ALL_QUERY_AGREEMENT"):
        primary = []
        heldout = []
        for record in result["records"]:
            primary.append(sum(Fraction(item["exact_value_regret"])
                               for row in record["arms"][arm]
                               for item in row["primary_metrics"].values()))
            heldout.append(sum(Fraction(item["exact_value_regret"])
                               for row in record["arms"][arm]
                               for item in row["heldout_metrics"].values()))
        assert result["summary"][arm]["primary_exact_regrets"] == [str(value) for value in primary]
        assert result["summary"][arm]["heldout_exact_regrets"] == [str(value) for value in heldout]
