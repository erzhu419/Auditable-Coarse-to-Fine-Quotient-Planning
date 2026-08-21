from pathlib import Path

from acfqp import construction_k7_generic_artifact_subprogram_preregistration_v121 as pre


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _sources():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def test_v121_preregistration_is_outcome_free_and_claim_locked():
    document = pre.freeze_generic_artifact_subprogram_preregistration_v121(
        _sources()
    ).to_document()
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["source_closure"][
        "frozen_before_any_registered_v121_target_outcome"
    ] is True
    assert document["construction_contract"][
        "hand_written_normalized_expression_shape_cases"
    ] == 0
    assert document["development_evidence_retained_before_registration"][
        "unfavourable_results_retained"
    ] is True
    boundary = document["claim_boundary"]
    assert boundary["registered_v121_target_outcome_observed"] is False
    assert boundary["legacy_shape_specific_planner_execution_adapter_present"] is True
    assert boundary["generic_planner_execution_adapter_verified"] is False
    assert boundary["official_scalar_cost"] is None
    assert boundary["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v121_source_closure_and_resource_schedule_are_exact():
    document = pre.freeze_generic_artifact_subprogram_preregistration_v121(
        _sources()
    ).to_document()
    assert document["source_closure"]["source_facts"] == pre._frozen_source_facts()
    assert document["artifact_factor_library_id"] == pre.EXPECTED_FACTOR_LIBRARY_ID
    assert document["resource_schedule"]["target_worker_count"] == 2
    assert document["resource_schedule"]["maximum_acquisition_labels"] == 320
