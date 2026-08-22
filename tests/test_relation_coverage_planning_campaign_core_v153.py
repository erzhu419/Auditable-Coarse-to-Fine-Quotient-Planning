from pathlib import Path

from acfqp.generic_quaternary_relation_workflow_adapter_v153 import FAMILY, quaternary_relation_workflow_config_v153
from acfqp.relation_coverage_planning_campaign_core_v153 import build_relation_coverage_planning_occurrence_v153


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v153_development_occurrence_plans_after_low_tax_acquisition():
    row = build_relation_coverage_planning_occurrence_v153(
        quaternary_relation_workflow_config_v153(),
        family=FAMILY,
        seed=1_047_003,
        episode_indices=(631, 632),
        bank_raw=(ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        verification_raw=(ROOT / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
        operator_receipt_raw=(ROOT / "v153_relation_coverage_operator_receipt.json").read_bytes(),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["anonymous_relational_factor_prior_acquisition"]["ground_support_labels"] == 13
    assert row["strict_no_prior_acquisition"]["ground_support_labels"] == 18
    assert row["legacy_path_first_prior_acquisition_summary"]["ground_support_labels"] == 156
    assert row["operator_sample_reduction_vs_legacy_prior"] == 143
    assert row["factor_prior_sample_reduction_within_adaptive_operator"] == 5
    assert row["operator_is_planning_or_certificate_authority"] is False
    assert row["official_scalar_cost"] is None
