from pathlib import Path
import hashlib

from acfqp.construction_k7_cross_domain_relational_bank_preregistration_v149 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_cross_domain_relational_bank_preregistration_v149,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _freeze():
    return freeze_cross_domain_relational_bank_preregistration_v149(
        (ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (ROOT / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
        (ROOT / "v148_anonymous_relational_factor_bank_campaign.json").read_bytes(),
        (
            ROOT / "v148_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
    )


def test_v149_preregisters_fresh_cross_domain_bank_reuse_without_outcomes():
    document = _freeze().to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["registered_gate"][
        "four_source_unseen_structural_families_required"
    ] is True
    assert document["registered_gate"][
        "relational_template_selection_itself_is_not_primary_gate"
    ] is True
    assert document["target_worker_count"] == 2
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v149_preregistration_bytes_when_frozen():
    result = _freeze()
    if PREREGISTRATION_ID != "0" * 64:
        assert result.preregistration_id == PREREGISTRATION_ID
        assert len(result.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(result.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
