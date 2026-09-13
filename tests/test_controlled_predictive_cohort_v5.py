from dataclasses import replace

from acfqp.science.controlled_predictive_cohort_v5 import (
    HISTORICAL_REPORTS, audit_roster_v5, declared_cases_v5, historical_report_roots,
)


def test_extracts_all_actual_report_formats_without_counting_witness_or_deferred_boards():
    """Missing either discovery round or sampling section would mislabel exposure."""
    base = declared_cases_v5()[0]
    root = {"name": base.name, "board": list(base.board)}
    witness = {"name": "not_a_root", "board": [0] * 16}
    formats = (
        {"public_development_boards_rank_encoding": {root["name"]: root["board"]}},
        {"records": [root], "round2": {"records": [root]}, "deferred": [witness]},
        {"cases": [{"case": root, "worst_regret_witness": witness}]},
        {"cases": [{"case": root, "worst_regret_witness": witness}]},
        {"original_exposed_diagnosis": {"cases": [{"case": root}]},
         "nested_sampling_curve": {"cases": [{"case": root}]}},
    )
    extracted = [historical_report_roots(name, payload) for name, payload in zip(HISTORICAL_REPORTS, formats)]
    assert list(map(len, extracted)) == [1, 2, 1, 1, 2]
    assert all(item["case_name"] == base.name and item["board"] == base.board
               for group in extracted for item in group)
    assert {item["source_section"] for item in extracted[-1]} == {
        "original_exposed_diagnosis.cases", "nested_sampling_curve.cases"}


def test_reused_and_duplicate_candidates_are_labeled_without_replacing_declared_units():
    """New seeds can produce old or duplicated roots; dropping them biases the cohort."""
    declared = declared_cases_v5()
    assert len(declared) == 14
    assert [case.seed for case in declared[2:6]] == [838101, 838201, 838301, 838401]
    assert all(case.horizon == 3 for case in declared)
    original = declared[2]
    duplicate = replace(original, name="second_generation_unit", seed=999999)
    history = [{"source_report": HISTORICAL_REPORTS[0], "source_section": "roots",
                "case_name": "old_root", "board": original.board}]
    roster = audit_roster_v5((original, duplicate, declared[3]), history)
    assert roster["declared_case_count"] == 3
    assert roster["unique_root_board_count"] == 2
    assert roster["new_seed_cases_reusing_exposed_roots"] == 2
    assert roster["unique_new_roots_absent_from_historical_root_inventory"] == 1
    assert [record["case"]["name"] for record in roster["cases"]] == [original.name, duplicate.name, declared[3].name]
    assert [record["case"]["split"] for record in roster["cases"]] == [
        "EXPOSED_ROOT_REUSE", "EXPOSED_ROOT_REUSE", "NEW_ROOT_DEVELOPMENT_V5"]
    assert roster["cases"][0]["within_roster_other_case_names"] == [duplicate.name]
    assert roster["cases"][0]["historical_root_matches"][0]["case_name"] == "old_root"
    assert roster["all_declared_cases_retained"]
    assert not roster["v5_query_and_sample_outcomes_evaluated"]
