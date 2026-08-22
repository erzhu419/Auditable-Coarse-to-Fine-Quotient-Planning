from pathlib import Path

from acfqp.generic_quaternary_relation_workflow_adapter_v153 import (
    build_quaternary_relation_workflow_adapter_v153,
    quaternary_relation_workflow_config_v153,
)
from acfqp.generic_relation_fanout_routing_adapter_v154 import (
    build_relation_fanout_routing_adapter_v154,
    relation_fanout_routing_config_v154,
)
from acfqp.structural_signature_guarded_acquisition_operator_v155 import (
    acquire_matched_structural_signature_guarded_arms_v155,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _inputs():
    return (
        (ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (ROOT / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
        (ROOT / "v155_structural_signature_query_guard_receipt.json").read_bytes(),
    )


def test_v155_guard_uses_relation_policy_only_for_positive_signature():
    bank, verification, guard = _inputs()
    config = quaternary_relation_workflow_config_v153()
    config["_v155_guard_receipt_hex"] = guard.hex()
    arms = acquire_matched_structural_signature_guarded_arms_v155(
        build_quaternary_relation_workflow_adapter_v153(1_047_003, config),
        bank,
        verification,
        config,
    )
    assert {arm["document"]["guard_decision"] for arm in arms.values()} == {"RELATION_COVERAGE"}


def test_v155_guard_falls_back_exactly_on_failed_signature():
    bank, verification, guard = _inputs()
    config = relation_fanout_routing_config_v154()
    config["_v155_guard_receipt_hex"] = guard.hex()
    arms = acquire_matched_structural_signature_guarded_arms_v155(
        build_relation_fanout_routing_adapter_v154(1_047_503, config),
        bank,
        verification,
        config,
    )
    prior = arms["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]["document"]
    assert prior["guard_decision"] == "PATH_FIRST_SAFE_FALLBACK"
    assert prior["failed_signature_match"] is True
    assert prior["ground_support_labels"] == 17
