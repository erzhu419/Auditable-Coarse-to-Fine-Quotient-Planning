from pathlib import Path

from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.robust_automatic_factor_dictionary_v131r2 import (
    derive_robust_automatic_factor_dictionary_v131r2,
    verify_robust_automatic_factor_dictionary_v131r2,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _source():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def test_v131r2_selects_every_leave_one_source_positive_gain_template():
    source = _source()
    library = derive_artifact_factor_projection_v120(source)
    document = derive_robust_automatic_factor_dictionary_v131r2(library, source)
    verified = verify_robust_automatic_factor_dictionary_v131r2(
        document, library, source
    )
    assert document["source_template_pool_count"] == 3
    assert document["selected_template_count"] == 3
    assert document["minimum_selected_template_leave_one_source_gain_bits"] == 7
    assert document["failed_v131r1_target_outcome_used_for_selection"] is False
    assert all(
        item["eligible_without_held_out_source"]
        for row in document["leave_one_source_campaign_reconstruction"]
        for item in row["leave_one_source_reconstructions"]
    )
    assert verified["positive_singleton_prefix_gain_every_holdout_verified"] is True
