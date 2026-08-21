from acfqp import construction_k7_identity_short_circuited_epoch_preregistration_v111 as v111_pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.symmetric_epoch_accounting_campaign_core_v112 import (
    build_symmetric_epoch_accounting_occurrence_v112,
)


def test_v112_historical_changed_graph_failure_passes_symmetric_accounting():
    occurrence = build_symmetric_epoch_accounting_occurrence_v112(
        v111_pre.campaign_config_v111(),
        family="BALANCED_BATCH_REFINEMENT",
        seed=1_023_101,
        episode_indices=(201, 202, 203),
        factor_library=(
            v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    accounting = occurrence["accounting"]
    assert occurrence["registered_gate"]["passed"] is True
    assert accounting["maintenance_events_avoided_against_full_diff"] == -2
    assert accounting[
        "maintenance_events_avoided_against_fully_accounted_full_diff"
    ] == 0
    assert accounting["v110_full_diff_baseline_omitted_identity_checks"] is True
    assert occurrence["algorithm_or_outcome_changed_from_embedded_v111_occurrence"] is False
    assert occurrence["official_scalar_cost"] is None
