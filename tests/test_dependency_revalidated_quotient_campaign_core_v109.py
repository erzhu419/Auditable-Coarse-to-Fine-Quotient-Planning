from acfqp import construction_k7_catalogue_closed_legality_quotient_preregistration_v107 as v107_pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.dependency_revalidated_quotient_campaign_core_v109 import (
    build_dependency_revalidated_quotient_occurrence_v109,
)
from acfqp.generic_quotient_plan_dependency_receipt_v109 import (
    revalidate_quotient_plan_dependency_v109,
)


def test_v109_historical_balanced_occurrence_reuses_only_unchanged_bfs_dependencies():
    occurrence = build_dependency_revalidated_quotient_occurrence_v109(
        v107_pre.campaign_config_v107(),
        family="BALANCED_BATCH_REFINEMENT",
        seed=1_020_101,
        episode_indices=(171, 172, 173),
        factor_library=(
            v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    gate = occurrence["registered_gate"]
    accounting = occurrence["accounting"]
    sequence = occurrence["persistent_dependency_revalidated_quotient_sequence"]
    assert gate["revalidated_and_no_cache_action_sequences_exactly_match"] is True
    assert gate[
        "revalidated_and_no_cache_base_execution_receipts_exactly_match"
    ] is True
    assert gate["revalidated_and_no_cache_target_labels_exactly_match"] is True
    assert gate["actual_new_planning_compute_strictly_below_no_cache"] is True
    assert sequence["dependency_revalidated_cache_hit_count"] > 0
    assert accounting["dependency_validation_checks"] > 0
    assert accounting["scalar_cost_aggregation_performed"] is False
    assert occurrence["official_scalar_cost"] is None

    hit = next(
        wrapper["abstract_plan"]
        for episode in sequence["episodes"]
        for wrapper in episode["abstract_plan_receipts"]
        if wrapper["abstract_plan"]["schema"]
        == "acfqp.generic_dependency_revalidated_quotient_heuristic_plan.v109"
    )
    model = next(
        row
        for row in sequence["quotient_models_before_each_episode"]
        if row["quotient_graph_id"] == hit["quotient_graph_id"]
    )
    changed = {**model, "projected_edge_rows": list(model["projected_edge_rows"])}
    dependency_state = hit["quotient_plan_dependency_receipt"][
        "ordered_bfs_dependency_rows"
    ][0]["projected_state"]
    changed["projected_edge_rows"] = [
        row
        for row in changed["projected_edge_rows"]
        if row["projected_pre"] != dependency_state
    ]
    rules = tuple(
        hit["quotient_plan_dependency_receipt"]["terminal_projection_rule"]
    )
    assert (
        revalidate_quotient_plan_dependency_v109(
            hit["quotient_plan_dependency_receipt"],
            current_model=changed,
            current_terminal_projection_rule=rules,
        )
        is None
    )
