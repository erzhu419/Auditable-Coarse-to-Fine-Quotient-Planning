from pathlib import Path

from acfqp.generic_relation_fanout_routing_adapter_v154 import (
    build_relation_fanout_routing_adapter_v154,
    relation_fanout_routing_config_v154,
)
from acfqp.online_typed_plan_receipt_sequence_v172 import (
    TAXONOMY,
    run_online_typed_plan_receipt_sequence_v172,
)
from acfqp.relation_coverage_acquisition_operator_v153 import (
    acquire_matched_relation_coverage_arms_v153,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v172_issues_complete_typed_receipts_before_orderer_return():
    config = relation_fanout_routing_config_v154()
    adapter = build_relation_fanout_routing_adapter_v154(1_047_503, config)
    arms = acquire_matched_relation_coverage_arms_v153(
        adapter,
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        config,
    )
    arm = arms["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]
    sequence = run_online_typed_plan_receipt_sequence_v172(
        adapter,
        arm["candidate"],
        arm["rows"],
        arm["document"]["ground_support_labels"],
        episode_indices=(651, 652),
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    assert sequence["online_plan_issuance_receipt_count"] == sum(
        len(episode["abstract_plan_receipts"])
        for episode in sequence["episodes"]
    )
    assert sequence["online_execution_join_receipt_count"] == sequence[
        "execution_step_count"
    ]
    assert set(sequence["online_typed_plan_source_histogram"]) == set(
        TAXONOMY.values()
    )
    assert sequence[
        "every_abstract_plan_receipt_issued_before_orderer_return"
    ] is True
    assert sequence["every_executed_action_joins_prior_online_receipt"] is True
    assert sequence["delegate_plan_byte_identity_preserved"] is True
    assert sequence["online_receipt_changes_planning_or_execution"] is False
    assert sequence["online_receipt_is_model_or_safety_authority"] is False
    assert sequence[
        "query_local_exact_overlay_remains_only_safety_authority"
    ] is True


def test_v172_each_execution_join_references_an_online_issuance():
    config = relation_fanout_routing_config_v154()
    adapter = build_relation_fanout_routing_adapter_v154(1_047_503, config)
    arms = acquire_matched_relation_coverage_arms_v153(
        adapter,
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        config,
    )
    arm = arms["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]
    sequence = run_online_typed_plan_receipt_sequence_v172(
        adapter,
        arm["candidate"],
        arm["rows"],
        arm["document"]["ground_support_labels"],
        episode_indices=(651, 652),
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    issuance_ids = {
        receipt["online_plan_issuance_receipt_id"]
        for receipt in sequence["online_plan_issuance_receipts"]
    }
    assert issuance_ids
    assert all(
        join["online_plan_issuance_receipt_id"] in issuance_ids
        and join["receipt_was_issued_before_plan_return"] is True
        and join["receipt_changes_plan_or_action_order"] is False
        for join in sequence["online_execution_join_receipts"]
    )
