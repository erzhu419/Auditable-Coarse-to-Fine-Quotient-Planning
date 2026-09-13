from dataclasses import replace

from acfqp.science.controlled_predictive_challenges_v6 import V6Case
from acfqp.science.controlled_predictive_cohort_v6 import (
    V5_REPORT, audit_roster_v6, board_symmetries, v5_report_roots,
)


def _case(name="variant_a", board=tuple(range(16)), variant="a"):
    return V6Case(name=name, group="one_mechanism", family="one_mechanism", variant=variant,
                  board=board, horizon=3, role="MECHANISM_CHALLENGE", mechanism="fixed construction")


def test_rotations_and_reflections_of_exposed_roots_are_not_new_roots():
    """Missing reflection or rotation exposure would overstate new-root evidence."""
    source = tuple(range(16))
    symmetries = board_symmetries(source)
    assert len(set(symmetries.values())) == 8
    assert symmetries["rotate_90"] == (12, 8, 4, 0, 13, 9, 5, 1, 14, 10, 6, 2, 15, 11, 7, 3)
    history = [{"source_report": "historical.json", "source_section": "cases",
                "case_name": "old_root", "board": source}]
    cases = tuple(_case(name=name, board=board, variant=name) for name, board in symmetries.items())
    roster = audit_roster_v6(cases, history)
    assert roster["registered_exposure_counts"] == {"EXPOSED_ROOT_REUSE": 1, "EXPOSED_SYMMETRY_REUSE": 7}
    assert roster["unique_raw_root_board_count"] == 8
    assert roster["unique_root_symmetry_orbit_count"] == 1
    assert roster["unique_new_root_symmetry_orbit_count"] == 0
    assert all(record["historical_symmetry_root_matches"][0]["case_name"] == "old_root"
               for record in roster["cases"][1:])


def test_family_variants_and_repeated_inputs_are_retained_and_grouped():
    """Discarding duplicate variants or treating them as replicates biases the denominator."""
    first = _case()
    duplicate = replace(first, name="duplicate", variant="repeat")
    rotated = replace(first, name="rotated", variant="rotation", board=board_symmetries(first.board)["rotate_90"])
    different = replace(first, name="changed", variant="changed", board=(16, *first.board[1:]))
    roster = audit_roster_v6((first, duplicate, rotated, different), ())
    assert [record["case"]["name"] for record in roster["cases"]] == ["variant_a", "duplicate", "rotated", "changed"]
    assert roster["declared_case_count"] == 4
    assert roster["unique_raw_root_board_count"] == 3
    assert roster["unique_root_symmetry_orbit_count"] == 2
    assert roster["generation_group_count"] == roster["family_group_count"] == 1
    assert not roster["family_groups"][0]["variants_are_independent_replicates"]
    assert roster["cases"][0]["within_roster_raw_root_matches"][0]["case_name"] == "duplicate"
    assert roster["cases"][0]["within_roster_symmetry_root_matches"][0]["case_name"] == "rotated"
    assert roster["all_declared_cases_retained"]
    assert not roster["v6_characterization_and_sample_outcomes_evaluated"]
    assert not roster["original_deferred_24_case_cohort_loaded_or_executed"]


def test_v5_inventory_reads_root_metadata_without_promoting_result_witnesses():
    """A witness counted as a declared root would change the exposure classification."""
    root = {"name": "declared_root", "board": list(range(16))}
    witness = {"name": "witness", "board": [0] * 16}
    extracted = v5_report_roots({"cases": [{"case": root, "worst_regret_witness": witness}],
                               "cohort_roster": {"cases": [witness]}, "deferred": [witness]})
    assert extracted == ({"source_report": V5_REPORT, "source_section": "cases",
                          "case_name": "declared_root", "board": tuple(range(16))},)
