from pathlib import Path
import hashlib

from acfqp.construction_k7_unified_factor_prior_ablation_preregistration_v129 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_unified_factor_prior_ablation_preregistration_v129,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _inputs():
    source = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    return source, (ROOT / "v128_third_family_owned_sequence_campaign.json").read_bytes(), (ROOT / "v128_third_family_owned_sequence_verification.json").read_bytes()


def test_v129_preregistration_freezes_matched_ablation_before_outcomes():
    registration = freeze_unified_factor_prior_ablation_preregistration_v129(*_inputs())
    document = registration.to_document()
    assert document["preregistration_id"] == PREREGISTRATION_ID
    assert document["source_closure"]["frozen_before_any_registered_v129_target_outcome"] is True
    assert document["matched_ablation_contract"]["same_stopping_rule_function"] is True
    assert document["matched_ablation_contract"]["only_arm_switch_is_registered_factor_prior"] is True
    assert document["claim_boundary"]["registered_workload_sample_efficiency_improvement_observed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    if PREREGISTRATION_ID != "0" * 64:
        assert len(registration.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(registration.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
