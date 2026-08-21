from pathlib import Path

from acfqp.construction_k7_generic_quotient_compiler_preregistration_v123r1 import (
    MAXIMUM_ACQUISITION_LABELS,
    TARGET_EPISODE_INDICES,
    TARGET_OCCURRENCES,
    freeze_generic_quotient_compiler_preregistration_v123r1,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _inputs():
    sources = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    return (
        sources,
        (ROOT / "v122_generic_factor_planner_campaign.json").read_bytes(),
        (ROOT / "v122_generic_factor_planner_verification.json").read_bytes(),
        (ROOT / "v123_generic_quotient_compiler_failure.json").read_bytes(),
    )


def test_v123r1_preregistration_is_fresh_and_retains_failure():
    value = freeze_generic_quotient_compiler_preregistration_v123r1(*_inputs())
    document = value.to_document()
    assert tuple((row["family"], row["seed"]) for row in document["identity_contract"]["target_occurrences"]) == TARGET_OCCURRENCES
    assert tuple(document["identity_contract"]["target_episode_indices"]) == TARGET_EPISODE_INDICES
    assert document["resource_schedule"]["maximum_acquisition_labels"] == MAXIMUM_ACQUISITION_LABELS
    assert document["frozen_failed_predecessor"]["same_identity_rerun_forbidden"] is True
    assert document["claim_boundary"]["registered_v123r1_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
