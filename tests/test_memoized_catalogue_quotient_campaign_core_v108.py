from acfqp import construction_k7_catalogue_closed_legality_quotient_preregistration_v107 as v107_pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.memoized_catalogue_quotient_campaign_core_v108 import (
    build_memoized_catalogue_quotient_occurrence_v108,
)


def test_v108_development_memoization_reduces_compute_without_changing_actions_or_labels():
    config = v107_pre.campaign_config_v107()
    occurrence = build_memoized_catalogue_quotient_occurrence_v108(
        config,
        family="MAINTENANCE_CASCADE",
        seed=1_019_104,
        episode_indices=(161, 162, 163),
        factor_library=(
            v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    gate = occurrence["registered_gate"]
    accounting = occurrence["accounting"]
    assert gate["memoized_and_no_cache_action_sequences_exactly_match"] is True
    assert gate["memoized_and_no_cache_per_action_receipts_exactly_match"] is True
    assert gate["memoized_and_no_cache_target_labels_exactly_match"] is True
    assert gate["memoized_actual_planning_compute_strictly_below_no_cache"] is True
    assert accounting["planning_compute_events_avoided"] > 0
    assert accounting["scalar_cost_aggregation_performed"] is False
    assert occurrence["official_scalar_cost"] is None
