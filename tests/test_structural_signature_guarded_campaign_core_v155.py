from pathlib import Path

from acfqp.generic_relation_fanout_routing_adapter_v154 import (
    FAMILY,
    relation_fanout_routing_config_v154,
)
from acfqp.structural_signature_guarded_campaign_core_v155 import (
    build_structural_signature_guarded_occurrence_v155,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v155_development_occurrence_prevents_v154_regression():
    row = build_structural_signature_guarded_occurrence_v155(
        relation_fanout_routing_config_v154(),
        family=FAMILY,
        seed=1_047_503,
        episode_indices=(671, 672),
        bank_raw=(ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(ROOT / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
        guard_receipt_raw=(ROOT / "v155_structural_signature_query_guard_receipt.json").read_bytes(),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["guard_sample_reduction_vs_legacy_prior"] == 0
    assert row["factor_prior_sample_reduction_within_guarded_operator"] == 8
    assert row["registered_gate"]["nonrelational_ood_rejected_before_bank_access"] is True
    assert row["guard_is_planning_or_certificate_authority"] is False
