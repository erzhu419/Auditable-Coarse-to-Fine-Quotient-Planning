from pathlib import Path

from acfqp.certificate_delta_only_invalidation_sequence_v176 import (
    run_certificate_delta_only_invalidation_sequence_v176,
)
from acfqp.generic_relation_fanout_routing_adapter_v154 import (
    build_relation_fanout_routing_adapter_v154,
    relation_fanout_routing_config_v154,
)
from acfqp.relation_coverage_acquisition_operator_v153 import (
    acquire_matched_relation_coverage_arms_v153,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v176_production_path_has_no_full_graph_diff_control():
    config = relation_fanout_routing_config_v154()
    adapter = build_relation_fanout_routing_adapter_v154(1_057_511, config)
    arms = acquire_matched_relation_coverage_arms_v153(
        adapter,
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        config,
    )
    arm = arms["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]
    sequence = run_certificate_delta_only_invalidation_sequence_v176(
        adapter,
        arm["candidate"],
        arm["rows"],
        arm["document"]["ground_support_labels"],
        episode_indices=(657, 658),
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    transition = sequence["receipt_driven_model_epoch_transition_receipts"][0]
    assert sequence["certificate_local_model_delta_receipt_count"] == 2
    assert sequence["delta_transition_join_count"] == 1
    assert sequence["production_full_graph_diff_checks"] == 0
    assert transition["production_full_graph_diff_checks"] == 0
    assert "matched_full_graph_diff_checks" not in transition
    assert "matched_full_graph_diff_changed_states" not in transition
    assert transition["producer_free_full_graph_diff_control_required"] is True
    assert sequence["receipt_driven_graph_dependency_retention_count"] > 0
    assert sequence["incrementally_revalidated_plan_receipt_count"] > 0
    assert sequence["query_local_exact_overlay_remains_only_safety_authority"] is True
