from acfqp import construction_k7_epoch_indexed_quotient_preregistration_v110 as v110_pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.identity_short_circuited_epoch_campaign_core_v111 import (
    build_identity_short_circuited_epoch_occurrence_v111,
)


def test_v111_historical_v110_failure_is_repaired_without_execution_change():
    occurrence = build_identity_short_circuited_epoch_occurrence_v111(
        v110_pre.campaign_config_v110(),
        family="MAINTENANCE_CASCADE",
        seed=1_022_103,
        episode_indices=(191, 192, 193),
        factor_library=(
            v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    gate = occurrence["registered_gate"]
    accounting = occurrence["accounting"]
    assert gate["identity_short_full_diff_per_hit_and_no_cache_execution_equal"] is True
    assert gate[
        "identity_short_dependency_maintenance_strictly_below_per_hit_validation"
    ] is True
    assert accounting["identity_short_circuit_count"] > 0
    assert accounting["identity_short_dependency_maintenance_events"] < 344
    assert accounting["full_diff_dependency_maintenance_events"] == 346
    assert accounting["scalar_cost_aggregation_performed"] is False
    assert occurrence["official_scalar_cost"] is None
