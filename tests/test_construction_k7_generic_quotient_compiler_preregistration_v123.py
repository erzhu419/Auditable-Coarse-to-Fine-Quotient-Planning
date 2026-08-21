from pathlib import Path

from acfqp.construction_k7_generic_quotient_compiler_preregistration_v123 import (
    TARGET_EPISODE_INDICES,
    TARGET_OCCURRENCES,
    freeze_generic_quotient_compiler_preregistration_v123,
    verify_generic_quotient_compiler_preregistration_v123,
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
    )


def test_v123_preregistration_is_outcome_free_and_fresh():
    value = freeze_generic_quotient_compiler_preregistration_v123(*_inputs())
    verify_generic_quotient_compiler_preregistration_v123(value, *_inputs())
    document = value.to_document()
    assert tuple((row["family"], row["seed"]) for row in document["identity_contract"]["target_occurrences"]) == TARGET_OCCURRENCES
    assert tuple(document["identity_contract"]["target_episode_indices"]) == TARGET_EPISODE_INDICES
    assert document["source_closure"]["frozen_before_any_registered_v123_target_outcome"] is True
    assert document["claim_boundary"]["registered_v123_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
