from pathlib import Path
import hashlib

from acfqp.construction_k7_fair_unified_factor_prior_ablation_preregistration_v129r1 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    FAILED_V129_PREREGISTRATION_ID,
    PREREGISTRATION_ID,
    freeze_fair_unified_factor_prior_ablation_preregistration_v129r1,
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
        (ROOT / "v128_third_family_owned_sequence_campaign.json").read_bytes(),
        (ROOT / "v128_third_family_owned_sequence_verification.json").read_bytes(),
        (ROOT / "v129_unified_factor_prior_ablation_failure.json").read_bytes(),
    )


def test_v129r1_preregistration_freezes_fair_successor_before_outcomes():
    registration = freeze_fair_unified_factor_prior_ablation_preregistration_v129r1(
        *_inputs()
    )
    document = registration.to_document()
    assert document["preregistration_id"] == PREREGISTRATION_ID
    assert document["retained_failed_predecessor"][
        "v129_preregistration_id"
    ] == FAILED_V129_PREREGISTRATION_ID
    assert document["retained_failed_predecessor"]["failed_identity_reused_by_v129r1"] is False
    assert document["matched_ablation_contract"][
        "same_fair_witness_blind_path_first_backtracking_policy"
    ] is True
    assert document["matched_ablation_contract"]["generation_witness_accessed"] is False
    assert document["resource_schedule"]["maximum_acquisition_labels_per_arm"] == 320
    assert document["claim_boundary"][
        "registered_workload_sample_efficiency_improvement_observed"
    ] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    if PREREGISTRATION_ID != "0" * 64:
        assert len(registration.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(registration.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
