from pathlib import Path
import hashlib

from acfqp.construction_k7_normalized_mixture_factor_prior_preregistration_v130 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_normalized_mixture_factor_prior_preregistration_v130,
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
        (ROOT / "v129r1_fair_unified_factor_prior_ablation_campaign.json").read_bytes(),
        (ROOT / "v129r1_fair_unified_factor_prior_ablation_verification.json").read_bytes(),
    )


def test_v130_preregistration_freezes_normalized_code_prior_before_targets():
    registration = freeze_normalized_mixture_factor_prior_preregistration_v130(
        *_inputs()
    )
    document = registration.to_document()
    assert document["preregistration_id"] == PREREGISTRATION_ID
    assert document["normalized_mixture_calibration"][
        "prior_odds_derived_from_prefix_codelength_difference"
    ] is True
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
