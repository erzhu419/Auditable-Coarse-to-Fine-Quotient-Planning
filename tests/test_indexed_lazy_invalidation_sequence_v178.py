from pathlib import Path

from acfqp.generic_relation_fanout_routing_adapter_v154 import (
    build_relation_fanout_routing_adapter_v154,
    relation_fanout_routing_config_v154,
)
from acfqp.indexed_lazy_invalidation_sequence_v178 import (
    run_indexed_lazy_invalidation_sequence_v178,
)
from acfqp.relation_coverage_acquisition_operator_v153 import (
    acquire_matched_relation_coverage_arms_v153,
)


FREEZE = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v178_uses_indexed_receipts_and_lazy_retained_authorization():
    config = relation_fanout_routing_config_v154()
    adapter = build_relation_fanout_routing_adapter_v154(1_078_511, config)
    arms = acquire_matched_relation_coverage_arms_v153(
        adapter,
        (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (FREEZE / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
        config,
    )
    arm = arms["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]
    sequence = run_indexed_lazy_invalidation_sequence_v178(
        adapter,
        arm["candidate"],
        arm["rows"],
        arm["document"]["ground_support_labels"],
        episode_indices=(671, 672, 673),
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    assert sequence["production_full_graph_diff_checks"] == 0
    assert sequence["production_live_dependency_projection_scan_count"] == 0
    assert sequence["production_prior_receipt_event_scan_count"] == 0
    assert sequence["retained_authorization_metadata_update_count"] == 0
    assert sequence["lazy_authorization_metadata_update_count"] > 0
    assert sequence["lazy_authorization_issuance_join_count"] == sequence[
        "lazy_authorization_receipt_count"
    ]
    assert sequence["incrementally_revalidated_plan_receipt_count"] > 0
    for transition in sequence["receipt_driven_model_epoch_transition_receipts"]:
        assert transition["production_prior_receipt_event_scan_count"] == 0
        assert transition["retained_authorization_metadata_updates"] == 0
        assert transition["retained_authorization_deferred_until_actual_cache_hit"] is True
    assert sequence["query_local_exact_overlay_remains_only_safety_authority"] is True
