from pathlib import Path
import hashlib

from acfqp.construction_k7_safe_paid_path_sample_tax_preregistration_v163 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_safe_paid_path_sample_tax_preregistration_v163,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v163_preregistration_is_outcome_free_and_exact():
    frozen = freeze_safe_paid_path_sample_tax_preregistration_v163(
        (FREEZE / "v161_paid_path_prefix_classifier_receipt.json").read_bytes()
    )
    document = frozen.to_document()
    assert frozen.preregistration_id == PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["registered_gate"][
        "query_policy_noninferior_everywhere_required"
    ] is True
    assert document["registered_gate"][
        "factor_prior_strict_aggregate_sample_reduction_required"
    ] is True
    assert document["frozen_v162_failure"]["document"][
        "failed_result_not_reclassified_as_success"
    ] is True
