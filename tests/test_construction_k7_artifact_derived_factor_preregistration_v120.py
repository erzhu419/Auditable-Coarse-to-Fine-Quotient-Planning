from pathlib import Path

from acfqp import construction_k7_artifact_derived_factor_preregistration_v120 as pre


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _sources():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def test_v120_preregistration_is_fresh_outcome_free_and_claim_locked():
    value = pre.freeze_artifact_derived_factor_preregistration_v120(_sources())
    document = value.to_document()
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert document["identity_contract"]["target_seeds_not_previously_exposed"] is True
    assert document["source_closure"][
        "frozen_before_any_registered_v120_target_outcome"
    ] is True
    assert document["construction_contract"]["hand_written_factor_template_count"] == 0
    assert document["artifact_factor_library"]["hand_written_factor_template_count"] == 0
    boundary = document["claim_boundary"]
    assert boundary["registered_v120_target_outcome_observed"] is False
    assert boundary["arbitrary_unseen_domain_transfer_claimed"] is False
    assert boundary["official_scalar_cost"] is None
    assert boundary["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v120_source_closure_and_resource_schedule_are_exact():
    document = pre.freeze_artifact_derived_factor_preregistration_v120(
        _sources()
    ).to_document()
    assert document["source_closure"]["source_facts"] == pre._frozen_source_facts()
    assert document["artifact_factor_library_id"] == pre.EXPECTED_FACTOR_LIBRARY_ID
    assert document["resource_schedule"]["target_worker_count"] == 2
    assert document["resource_schedule"]["maximum_acquisition_labels"] == 320
