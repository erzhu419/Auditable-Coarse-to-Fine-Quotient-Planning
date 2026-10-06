from fractions import Fraction

from acfqp.science.crossed_factor_transfer_v270 import (
    CANDIDATE_SUBSETS,
    ROAD_WEATHER,
    SEEDS,
    SOURCE_FIT,
    SOURCE_PAIRS,
    TARGET_AUDIT,
    TARGET_PAIRS,
    TARGET_PREFIXES,
    _contexts,
    _law,
    _stream,
    run_replication,
)


def test_source_l_and_target_corners_are_disjoint_and_connected():
    assert set(SOURCE_PAIRS).isdisjoint(TARGET_PAIRS)
    assert SOURCE_PAIRS == ((0, 0), (1, 0), (2, 0), (0, 1), (0, 2))
    assert all(1 <= a <= 2 and 1 <= b <= 2 for a, b in TARGET_PAIRS)


def test_recombined_laws_depend_on_declared_visible_factors_only():
    contexts = _contexts(((0, 1), (0, 2), (1, 1)), "check")
    first, second, third = (_law(context) for context in contexts)
    assert first["SHORT_PASS"] == second["SHORT_PASS"]
    assert first["DETOUR_PASS"] == second["DETOUR_PASS"]
    assert first["RECOVERY_RETRY"] != second["RECOVERY_RETRY"]
    assert first["RECOVERY_RETRY"] == third["RECOVERY_RETRY"]
    assert first["SHORT_PASS"] != third["SHORT_PASS"]
    assert all("weather" not in context.as_dict() for context in contexts)


def test_source_selector_and_target_prefixes_are_frozen_and_audited_separately():
    result = run_replication()
    assert result["settings"]["seeds"] == list(SEEDS)
    assert tuple(tuple(fields) for fields in result["settings"]["candidate_subsets"]) == CANDIDATE_SUBSETS
    for record in result["records"]:
        selected = record["selected"]
        assert selected["source_fit_observations"] == len(SOURCE_PAIRS) * 3 * SOURCE_FIT
        assert selected["source_audit_observations"] == len(SOURCE_PAIRS) * 3 * 16
        for arm in result["summary"]:
            assert len(record["arms"][arm]) == len(TARGET_PAIRS) * len(TARGET_PREFIXES)
            assert all(row["target_audit_per_operator"] == TARGET_AUDIT for row in record["arms"][arm])
            assert all(row["prefix_per_operator"] in TARGET_PREFIXES for row in record["arms"][arm])


def test_full_context_at_zero_prefix_matches_reset_and_summary_has_curves():
    result = run_replication()
    for record in result["records"]:
        reset = {(tuple(row["target"].values()), row["prefix_per_operator"]): row["metrics"]
                 for row in record["arms"]["RESET"] if row["prefix_per_operator"] == 0}
        full = {(tuple(row["target"].values()), row["prefix_per_operator"]): row["metrics"]
                for row in record["arms"]["FULL_CONTEXT"] if row["prefix_per_operator"] == 0}
        assert reset == full
    for arm in result["summary"]:
        assert set(map(int, result["summary"][arm])) == set(TARGET_PREFIXES)
        endpoint = result["summary"][arm]["48"]
        assert len(endpoint["policy_correct_counts"]) == len(SEEDS)
        assert len(endpoint["set_action_agreement_counts"]) == len(SEEDS)
        assert all(Fraction(value) >= 0 for value in endpoint["exact_regrets"])


def test_streams_are_deterministic_for_a_context_seed():
    context = _contexts(((1, 2),), "single")[0]
    assert _stream(context, SEEDS[0]) == _stream(context, SEEDS[0])
