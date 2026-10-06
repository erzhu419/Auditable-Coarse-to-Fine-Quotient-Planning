from fractions import Fraction

from acfqp.science.persistent_consequence_library_v266 import (
    FIT_PER_OPERATOR,
    SEEDS,
    run_replication,
)


def test_v266_has_one_regret_record_per_frozen_seed():
    result = run_replication()
    for arm in ("RESET", "GLOBAL", "V265_GUARDED", "ACTION_AGREEMENT"):
        assert len(result["summary"][arm]["exact_regrets"]) == len(SEEDS)


def test_v266_keeps_all_arms_on_the_shared_fit_prefix():
    result = run_replication()
    for record in result["records"]:
        expected = [(index + 1) * FIT_PER_OPERATOR * 3 for index in range(4)]
        for rows in record["arms"].values():
            assert [row["observations"] for row in rows] == expected
            assert all(row["audit_observations"] == 16 * 3 for row in rows)


def test_action_agreement_has_only_frozen_assignment_reasons():
    result = run_replication()
    allowed = {"initial", "reuse_all_query_actions", "abstain_local_split"}
    for record in result["records"]:
        for row in record["arms"]["ACTION_AGREEMENT"]:
            assert row["assignment"]["reason"] in allowed
            assert "query_action_agreement" in row["assignment"]
            assert "candidate_checks" in row["assignment"]
            assert row["assignment"]["candidate_count_before"] == len(row["assignment"]["candidate_checks"])


def test_summary_regrets_match_each_seed_records():
    result = run_replication()
    for arm in ("RESET", "GLOBAL", "V265_GUARDED", "ACTION_AGREEMENT"):
        expected = []
        for record in result["records"]:
            expected.append(sum(Fraction(item["exact_value_regret"])
                                for row in record["arms"][arm]
                                for item in row["metrics"].values()))
        assert result["summary"][arm]["exact_regrets"] == [str(value) for value in expected]
