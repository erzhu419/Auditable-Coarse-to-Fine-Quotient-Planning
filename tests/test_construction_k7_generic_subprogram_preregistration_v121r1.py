from pathlib import Path

from acfqp import construction_k7_generic_subprogram_preregistration_v121r1 as pre


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _sources():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def _failed():
    return (ROOT / "v121_generic_artifact_subprogram_campaign.json").read_bytes()


def test_v121r1_preregistration_preserves_failure_and_freezes_correction():
    document = pre.freeze_generic_subprogram_preregistration_v121r1(
        _sources(), _failed()
    ).to_document()
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert document["frozen_failed_predecessor"]["registered_gate_passed"] is False
    assert document["frozen_failed_predecessor"][
        "failed_predecessor_identity_and_bytes_retained"
    ] is True
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["correction_contract"][
        "same_epoch_cache_hit_count_may_be_zero"
    ] is True
    boundary = document["claim_boundary"]
    assert boundary["registered_v121r1_target_outcome_observed"] is False
    assert boundary["generic_planner_execution_adapter_verified"] is False
    assert boundary["official_scalar_cost"] is None


def test_v121r1_source_closure_and_resource_schedule_are_exact():
    document = pre.freeze_generic_subprogram_preregistration_v121r1(
        _sources(), _failed()
    ).to_document()
    assert document["source_closure"]["source_facts"] == pre._frozen_source_facts()
    assert document["resource_schedule"]["target_worker_count"] == 2
    assert document["resource_schedule"]["maximum_acquisition_labels"] == 320
