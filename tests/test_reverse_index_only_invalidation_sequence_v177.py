from pathlib import Path

from acfqp.generic_relation_fanout_routing_adapter_v154 import (
    build_relation_fanout_routing_adapter_v154,
    relation_fanout_routing_config_v154,
)
from acfqp.relation_coverage_acquisition_operator_v153 import (
    acquire_matched_relation_coverage_arms_v153,
)
from acfqp.reverse_index_only_invalidation_sequence_v177 import (
    run_reverse_index_only_invalidation_sequence_v177,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v177_invalidation_selection_has_no_live_projection_scan():
    config = relation_fanout_routing_config_v154()
    adapter = build_relation_fanout_routing_adapter_v154(1_077_511, config)
    arms = acquire_matched_relation_coverage_arms_v153(
        adapter,
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (
            FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
        ).read_bytes(),
        config,
    )
    arm = arms["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]
    sequence = run_reverse_index_only_invalidation_sequence_v177(
        adapter,
        arm["candidate"],
        arm["rows"],
        arm["document"]["ground_support_labels"],
        episode_indices=(661, 662),
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    transition = sequence["receipt_driven_model_epoch_transition_receipts"][0]
    assert sequence["production_full_graph_diff_checks"] == 0
    assert sequence["production_live_dependency_projection_scan_count"] == 0
    assert transition["production_live_dependency_projection_scan_count"] == 0
    assert "dependency_projection_ids_by_dependency_receipt_id" not in transition
    assert transition["receipt_reverse_index_drove_invalidation"] is True
    assert transition["reverse_dependency_index_lookups"] >= 0
    assert sequence["receipt_driven_graph_dependency_retention_count"] > 0
    assert sequence["incrementally_revalidated_plan_receipt_count"] > 0
    assert sequence["query_local_exact_overlay_remains_only_safety_authority"] is True
