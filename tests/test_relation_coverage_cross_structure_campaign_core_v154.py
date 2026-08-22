from pathlib import Path

from acfqp.generic_relation_fanout_routing_adapter_v154 import (
    FAMILY,
    relation_fanout_routing_config_v154,
)
from acfqp.relation_coverage_cross_structure_application_receipt_v154 import (
    freeze_relation_coverage_cross_structure_application_receipt_v154,
)
from acfqp.relation_coverage_cross_structure_campaign_core_v154 import (
    build_relation_coverage_cross_structure_occurrence_v154,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v154_development_occurrence_reuses_operator_and_rejects_ood():
    application = freeze_relation_coverage_cross_structure_application_receipt_v154(
        (ROOT / "v153_relation_coverage_operator_receipt.json").read_bytes(),
        (ROOT / "v153_relation_coverage_campaign.json").read_bytes(),
        (ROOT / "v153_relation_coverage_verification.json").read_bytes(),
    )
    row = build_relation_coverage_cross_structure_occurrence_v154(
        relation_fanout_routing_config_v154(),
        family=FAMILY,
        seed=1_047_503,
        episode_indices=(651, 652),
        bank_raw=(ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(ROOT / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
        application_receipt_raw=application.canonical_bytes,
    )
    assert row["registered_gate"]["passed"] is True
    assert row["operator_sample_reduction_vs_legacy_prior"] == 5
    assert row["factor_prior_sample_reduction_within_adaptive_operator"] == 3
    assert row["nonrelational_ood_control"]["operator_transfer_rejected_before_bank_access"] is True
    assert row["operator_is_planning_or_certificate_authority"] is False
    assert row["official_scalar_cost"] is None
