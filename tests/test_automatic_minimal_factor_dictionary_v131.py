from pathlib import Path

from acfqp.automatic_minimal_factor_dictionary_v131 import (
    derive_automatic_minimal_factor_dictionary_v131,
    verify_automatic_minimal_factor_dictionary_v131,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _source():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def test_v131_selects_minimum_dictionary_and_reconstructs_each_source_holdout():
    source = _source()
    library = derive_artifact_factor_projection_v120(source)
    document = derive_automatic_minimal_factor_dictionary_v131(library, source)
    verified = verify_automatic_minimal_factor_dictionary_v131(
        document, library, source
    )
    assert document["source_template_pool_count"] == 3
    assert document["selected_template_count"] == 2
    assert document["subset_search"]["candidate_subset_count"] == 8
    assert all(
        reconstruction["eligible_without_held_out_source"]
        for row in document["leave_one_source_campaign_reconstruction"]
        for reconstruction in row["leave_one_source_reconstructions"]
    )
    assert document["target_outcomes_accessed"] is False
    assert document["fixed_template_cardinality_supplied"] is False
    assert verified["minimum_two_part_prefix_code_verified"] is True
