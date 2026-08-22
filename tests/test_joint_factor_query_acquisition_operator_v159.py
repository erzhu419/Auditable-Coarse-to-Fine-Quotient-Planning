from pathlib import Path

from acfqp.anonymous_relational_factor_bank_acquisition_v148 import (
    acquire_matched_anonymous_relational_factor_bank_arms_v148,
)
from acfqp.generic_modular_routing_adapter_v128 import (
    build_modular_routing_adapter_v128,
    modular_routing_config_v128,
)
from acfqp.joint_factor_query_acquisition_operator_v159 import (
    acquire_matched_joint_factor_query_arms_v159,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v159_factorization_label_repairs_v158_modular_false_positive():
    config = modular_routing_config_v128()
    adapter = build_modular_routing_adapter_v128(1_048_992, config)
    bank = (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes()
    verification = (
        FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
    ).read_bytes()
    receipt = (FREEZE / "v159_joint_factor_query_classifier_receipt.json").read_bytes()
    arms = acquire_matched_joint_factor_query_arms_v159(
        adapter, bank, verification, receipt, config
    )
    legacy = acquire_matched_anonymous_relational_factor_bank_arms_v148(
        adapter, bank, verification, config
    )
    for name in arms:
        document = arms[name]["document"]
        source = legacy[name]["document"]
        assert document["query_policy_decision"] == "PATH_FIRST_SAFE_FALLBACK"
        assert document["v158_metadata_classifier_counterfactual_decision"] == "RELATION_COVERAGE"
        assert document["source_v148_acquisition_id"] == source["acquisition_id"]
        assert document["ground_support_labels"] == source["ground_support_labels"]
        assert document["raw_transition_sha256"] == source["raw_transition_sha256"]
        assert document["target_factorization_probe_labels_added_by_classifier"] == 0
