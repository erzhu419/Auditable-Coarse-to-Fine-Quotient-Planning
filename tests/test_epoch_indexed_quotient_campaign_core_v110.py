from acfqp import construction_k7_dependency_revalidated_quotient_preregistration_v109 as v109_pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.epoch_indexed_quotient_campaign_core_v110 import (
    build_epoch_indexed_quotient_occurrence_v110,
)


def test_v110_historical_occurrence_reduces_dependency_maintenance_without_changing_execution():
    occurrence = build_epoch_indexed_quotient_occurrence_v110(
        v109_pre.campaign_config_v109(),
        family="BALANCED_BATCH_REFINEMENT",
        seed=1_021_101,
        episode_indices=(181, 182, 183),
        factor_library=(
            v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    gate = occurrence["registered_gate"]
    accounting = occurrence["accounting"]
    assert gate[
        "indexed_per_hit_and_no_cache_actions_base_receipts_labels_and_steps_equal"
    ] is True
    assert gate[
        "epoch_indexed_dependency_maintenance_strictly_below_per_hit_validation"
    ] is True
    assert gate["per_hit_dependency_rescan_count_is_zero"] is True
    assert accounting["dependency_maintenance_events_avoided"] > 0
    assert accounting["scalar_cost_aggregation_performed"] is False
    assert occurrence["official_scalar_cost"] is None
