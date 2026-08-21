from pathlib import Path
import hashlib

from acfqp.construction_k7_automatic_factor_dictionary_preregistration_v131r1 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_automatic_factor_dictionary_preregistration_v131r1,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _inputs():
    source = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    return (
        source,
        (ROOT / "v130_normalized_mixture_factor_prior_campaign.json").read_bytes(),
        (ROOT / "v130_normalized_mixture_factor_prior_verification.json").read_bytes(),
        (ROOT / "v131_automatic_factor_dictionary_preregistration.json").read_bytes(),
    )


def test_v131r1_preregistration_freezes_automatic_dictionary_before_targets():
    registration = freeze_automatic_factor_dictionary_preregistration_v131r1(
        *_inputs()
    )
    document = registration.to_document()
    assert document["preregistration_id"] != "0" * 64
    if PREREGISTRATION_ID != "0" * 64:
        assert document["preregistration_id"] == PREREGISTRATION_ID
    assert document["automatic_dictionary_calibration"][
        "prior_odds_derived_from_prefix_codelength_difference"
    ] is True
    assert document["automatic_factor_dictionary"]["selected_template_count"] == 2
    assert document["frozen_pre_outcome_withdrawn_predecessor"][
        "registered_target_outcome_executed"
    ] is False
    assert document["automatic_factor_dictionary"][
        "fixed_template_cardinality_supplied"
    ] is False
    assert document["matched_ablation_contract"][
        "fixed_two_to_library_cardinality_prior_multiplier_present"
    ] is False
    assert document["resource_schedule"]["maximum_acquisition_labels_per_arm"] == 320
    assert document["claim_boundary"][
        "registered_workload_sample_efficiency_improvement_observed"
    ] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    if PREREGISTRATION_ID != "0" * 64:
        assert len(registration.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(registration.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
