from pathlib import Path

from acfqp.construction_k7_standalone_generic_model_preregistration_v125 import TARGET_EPISODE_INDICES, TARGET_OCCURRENCES, freeze_standalone_generic_model_preregistration_v125


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _inputs():
    sources = {"V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(), "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(), "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes()}
    return sources, (ROOT / "v124_cross_family_generic_compiler_campaign.json").read_bytes(), (ROOT / "v124_cross_family_generic_compiler_verification.json").read_bytes()


def test_v125_preregistration_is_fresh_and_outcome_free():
    document = freeze_standalone_generic_model_preregistration_v125(*_inputs()).to_document()
    assert tuple((row["family"], row["seed"]) for row in document["identity_contract"]["target_occurrences"]) == TARGET_OCCURRENCES
    assert tuple(document["identity_contract"]["target_episode_indices"]) == TARGET_EPISODE_INDICES
    assert document["construction_contract"]["retained_v113_state_carrier_present"] is False
    assert document["claim_boundary"]["registered_v125_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
