from pathlib import Path

from acfqp.relation_coverage_acquisition_operator_v153 import acquire_matched_relation_coverage_arms_v153
from acfqp.generic_quaternary_relation_workflow_adapter_v153 import build_quaternary_relation_workflow_adapter_v153, quaternary_relation_workflow_config_v153


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v153_relation_coverage_operator_reduces_absolute_and_prior_samples():
    config = quaternary_relation_workflow_config_v153()
    adapter = build_quaternary_relation_workflow_adapter_v153(1_047_003, config)
    arms = acquire_matched_relation_coverage_arms_v153(
        adapter,
        (ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (ROOT / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
        config,
    )
    prior = arms["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]["document"]
    strict = arms["STRICT_NO_PRIOR"]["document"]
    assert prior["ground_support_labels"] < 156
    assert strict["ground_support_labels"] < 164
    assert prior["ground_support_labels"] < strict["ground_support_labels"]
    assert prior["relational_artifact_expression_selected_count"] > 0
    assert prior["generation_witness_accessed"] is False
    assert prior["observation_derived_relation_coverage_then_path_backtracking"] is True
