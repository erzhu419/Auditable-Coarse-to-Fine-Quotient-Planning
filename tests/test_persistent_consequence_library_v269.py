from fractions import Fraction

from acfqp.science.persistent_consequence_library_v263 import QUERIES
from acfqp.science.persistent_consequence_library_v266 import _run_lifecycle as run_v266_lifecycle
from acfqp.science.persistent_consequence_library_v269 import (
    KAPPA,
    _empty_counts,
    _shrink_model,
    run_replication,
)
from acfqp.science.persistent_consequence_library_v265 import (
    AUDIT_PER_OPERATOR, FIT_PER_OPERATOR, SEEDS,
)


def test_shrink_formula_is_normalized_and_empty_baseline_is_reset():
    local = _empty_counts()
    for row in local.values():
        first = next(iter(row))
        row[first] = FIT_PER_OPERATOR
    empty = _empty_counts()
    shrunk = _shrink_model(local, empty)
    for operator, values in shrunk.items():
        assert sum(values.values()) == 1
        assert all(isinstance(value, Fraction) for value in values.values())
    from acfqp.science.persistent_consequence_library_v263 import posterior
    assert shrunk == posterior(local)


def test_assignment_and_module_ids_match_independent_v266_replay():
    result = run_replication()
    for record in result["records"]:
        old = run_v266_lifecycle(record["seed"])["arms"]["ACTION_AGREEMENT"]
        for arm in ("LOCKED_MARGINAL", "FACTORIZED_MODULE"):
            for new, old_row in zip(record["arms"][arm], old):
                for field in ("module_id", "reason", "reused", "candidate_count_before", "module_count_after"):
                    assert new["assignment"][field] == old_row["assignment"][field]


def test_all_arms_share_prefix_accounting_and_record_baseline_source():
    result = run_replication()
    expected = [(index + 1) * FIT_PER_OPERATOR * 3 for index in range(4)]
    for record in result["records"]:
        for arm, rows in record["arms"].items():
            assert [row["observations"] for row in rows] == expected
            assert all(row["audit_observations"] == AUDIT_PER_OPERATOR * 3 for row in rows)
            assert {row["base_source"] for row in rows} == {
                {"RESET": "none", "LOCKED_MARGINAL": "module_history_committed",
                 "GLOBAL_SHRINK": "global_history", "FACTORIZED_MODULE": "module_history"}[arm]
            }
            if arm in ("GLOBAL_SHRINK", "FACTORIZED_MODULE"):
                assert all(row["kappa"] in {"0", str(KAPPA)} for row in rows)


def test_summary_has_one_record_per_seed_and_query_count():
    result = run_replication()
    assert result["settings"]["kappa"] == str(KAPPA)
    for summary in result["summary"].values():
        assert len(summary["policy_correct_counts"]) == len(SEEDS)
        assert len(summary["set_action_agreement_counts"]) == len(SEEDS)
        assert len(summary["exact_regrets"]) == len(SEEDS)
        assert summary["mean_policy_correct"] <= len(QUERIES) * 4
