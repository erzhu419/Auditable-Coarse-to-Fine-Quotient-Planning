from fractions import Fraction, Fraction as F

from acfqp.science.persistent_consequence_library_v263 import (
    QUERIES, WEATHER, _draw_rows, _exact_vectors,
)
from acfqp.science.persistent_consequence_library_v268 import (
    _exact_pair_model,
    _pair_counts,
    _pair_model,
    run_replication,
)
from acfqp.science.persistent_consequence_library_v266 import _run_lifecycle as run_v266_lifecycle
from acfqp.science.persistent_consequence_library_v265 import (
    AUDIT_PER_OPERATOR, FIT_PER_OPERATOR, SEEDS,
)


def _rows(weather: str, seed: int):
    law = WEATHER[weather]
    return _draw_rows({
        "SHORT_PASS": {"DELIVERY": law[0], "LOST": 1 - law[0]},
        "DETOUR_PASS": {"DELIVERY": law[1], "LOST": law[2], "RECOVERY": law[3]},
        "RECOVERY_RETRY": {"DELIVERY": law[4], "LOST": 1 - law[4]},
    }, seed)


def test_fixed_index_pair_counts_conserve_fit_and_audit_rows():
    rows = _rows("normal", SEEDS[0])
    fit = _pair_counts(rows, 0, FIT_PER_OPERATOR)
    audit = _pair_counts(rows, FIT_PER_OPERATOR, FIT_PER_OPERATOR + AUDIT_PER_OPERATOR)
    assert sum(fit.values()) == FIT_PER_OPERATOR
    assert sum(audit.values()) == AUDIT_PER_OPERATOR


def test_pair_posterior_is_normalized_and_matches_exact_route_composition():
    rows = _rows("normal", SEEDS[0])
    short = {name: rows["SHORT_PASS"][:FIT_PER_OPERATOR].count(name) for name in ("DELIVERY", "LOST")}
    pair = _pair_counts(rows, 0, FIT_PER_OPERATOR)
    model = _pair_model(short, pair)
    assert sum(F(value) for value in (pair.values())) == FIT_PER_OPERATOR
    posterior_pair_mass = {
        name: F(2 * value + 1, 2 * FIT_PER_OPERATOR + 4) for name, value in pair.items()
    }
    assert sum(posterior_pair_mass.values()) == 1
    for vector in model.values():
        assert all(isinstance(value, Fraction) for value in vector)
    exact = _exact_pair_model("normal")
    assert exact["DETOUR_RETRY"] == (Fraction(-183, 1000), Fraction(23, 200), Fraction(177, 200))
    for weather in WEATHER:
        assert _exact_pair_model(weather) == _exact_vectors(weather)


def test_locked_composed_keeps_v266_marginal_assignment_decisions():
    result = run_replication()
    for record in result["records"]:
        marginal = record["arms"]["LOCKED_MARGINAL"]
        composed = record["arms"]["LOCKED_COMPOSED"]
        old = run_v266_lifecycle(record["seed"])["arms"]["ACTION_AGREEMENT"]
        for new_marginal, new_composed, old_row in zip(marginal, composed, old):
            for field in ("module_id", "reason", "reused", "candidate_count_before", "module_count_after"):
                assert new_marginal["assignment"][field] == old_row["assignment"][field]
                assert new_composed["assignment"][field] == old_row["assignment"][field]
            assert new_marginal["assignment"]["candidate_checks"] == [
                {key: value for key, value in check.items() if key != "query_action_agreement"}
                for check in old_row["assignment"]["candidate_checks"]
            ]
            assert all(row_count == expected for row_count, expected in (
                (new_composed["pair_fit_count"], FIT_PER_OPERATOR),
                (new_composed["pair_audit_count"], AUDIT_PER_OPERATOR),
            ))


def test_all_arms_share_fit_and_audit_accounting():
    result = run_replication()
    expected = [(index + 1) * FIT_PER_OPERATOR * 3 for index in range(4)]
    for record in result["records"]:
        for rows in record["arms"].values():
            assert [row["observations"] for row in rows] == expected
            assert all(row["audit_observations"] == AUDIT_PER_OPERATOR * 3 for row in rows)


def test_summary_has_one_record_per_seed_and_matches_query_count():
    result = run_replication()
    assert result["settings"]["seeds"] == list(SEEDS)
    for summary in result["summary"].values():
        assert len(summary["policy_correct_counts"]) == len(SEEDS)
        assert len(summary["set_action_agreement_counts"]) == len(SEEDS)
        assert len(summary["exact_regrets"]) == len(SEEDS)
        assert summary["mean_policy_correct"] <= len(QUERIES) * 4
