from pathlib import Path

from acfqp.anonymous_relational_factor_bank_acquisition_v148 import (
    acquire_matched_anonymous_relational_factor_bank_arms_v148,
)
from acfqp.generic_relation_keyed_workflow_adapter_v151 import (
    build_relation_keyed_workflow_adapter_v151,
    relation_keyed_workflow_config_v151,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v151_development_relation_keyed_domain_selects_relational_template():
    config = relation_keyed_workflow_config_v151()
    adapter = build_relation_keyed_workflow_adapter_v151(1_047_001, config)
    arms = acquire_matched_anonymous_relational_factor_bank_arms_v148(
        adapter,
        (ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (ROOT / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
        config,
    )
    prior = arms["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]["document"]
    strict = arms["STRICT_NO_PRIOR"]["document"]
    assert prior["relational_artifact_expression_selected_count"] > 0
    assert prior["ground_support_labels"] < strict["ground_support_labels"]
    assert prior["same_generic_atomic_hypothesis_pool"] is True
    assert strict["same_generic_atomic_hypothesis_pool"] is True
