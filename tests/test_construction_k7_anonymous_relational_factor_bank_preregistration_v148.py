from pathlib import Path
import hashlib

from acfqp.construction_k7_anonymous_relational_factor_bank_preregistration_v148 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_anonymous_relational_factor_bank_preregistration_v148,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _freeze():
    return freeze_anonymous_relational_factor_bank_preregistration_v148(
        (ROOT / "v145_certificate_local_recovery_union_campaign.json").read_bytes(),
        (ROOT / "v145_certificate_local_recovery_union_verification.json").read_bytes(),
        (ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (ROOT / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
    )


def test_v148_preregisters_fresh_outcome_free_relational_prior_ablation():
    result = _freeze()
    document = result.to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["registered_gate"][
        "only_arm_switch_is_anonymous_relational_prior_codelength"
    ] is True
    assert document["registered_gate"]["producer_free_verification_required"] is True
    assert document["target_worker_count"] == 2
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v148_preregistration_bytes_when_frozen():
    result = _freeze()
    if PREREGISTRATION_ID != "0" * 64:
        assert result.preregistration_id == PREREGISTRATION_ID
        assert len(result.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(result.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
