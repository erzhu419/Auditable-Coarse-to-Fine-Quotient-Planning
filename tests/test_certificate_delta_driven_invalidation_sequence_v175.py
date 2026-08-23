from pathlib import Path

from acfqp.certificate_delta_driven_invalidation_sequence_v175 import (
    run_certificate_delta_driven_invalidation_sequence_v175,
)
from acfqp.generic_relation_fanout_routing_adapter_v154 import (
    build_relation_fanout_routing_adapter_v154,
    relation_fanout_routing_config_v154,
)
from acfqp.relation_coverage_acquisition_operator_v153 import (
    acquire_matched_relation_coverage_arms_v153,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v175_certificate_delta_drives_frontier_before_full_diff_control():
    config = relation_fanout_routing_config_v154()
    adapter = build_relation_fanout_routing_adapter_v154(1_047_511, config)
    arms = acquire_matched_relation_coverage_arms_v153(
        adapter,
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        config,
    )
    arm = arms["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]
    sequence = run_certificate_delta_driven_invalidation_sequence_v175(
        adapter,
        arm["candidate"],
        arm["rows"],
        arm["document"]["ground_support_labels"],
        episode_indices=(653, 654),
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    assert sequence["certificate_local_model_delta_receipt_count"] == 2
    assert sequence["delta_transition_join_count"] == 1
    delta = sequence["certificate_local_model_delta_receipts"][0]
    transition = sequence["receipt_driven_model_epoch_transition_receipts"][0]
    join = sequence["delta_transition_joins"][0]
    assert delta["certificate_delta_receipt_id"] == transition[
        "certificate_delta_receipt_id"
    ]
    assert join["certificate_delta_receipt_id"] == delta[
        "certificate_delta_receipt_id"
    ]
    assert transition["delta_derived_changed_projected_state_count"] == delta[
        "changed_projected_state_count"
    ]
    assert transition["matched_full_graph_diff_changed_states"] == delta[
        "changed_projected_states"
    ]
    assert sequence[
        "serialized_full_graph_rows_scanned_for_invalidation_decision"
    ] == 0
    assert sequence["matched_full_graph_diff_control_checks"] > 0
    assert sequence[
        "full_graph_diff_checks_avoided_on_invalidation_decision_path"
    ] == sequence["matched_full_graph_diff_control_checks"]
    assert sequence["receipt_driven_graph_dependency_retention_count"] > 0
    assert sequence["incrementally_revalidated_plan_receipt_count"] > 0
    assert sequence["receipt_dependency_lifecycle_changes_selected_action_order"] is False
    assert sequence["query_local_exact_overlay_remains_only_safety_authority"] is True

