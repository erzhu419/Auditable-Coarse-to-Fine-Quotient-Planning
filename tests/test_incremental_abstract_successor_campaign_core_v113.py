from acfqp import construction_k7_identity_short_circuited_epoch_preregistration_v111 as v111_pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.incremental_abstract_successor_campaign_core_v113 import (
    build_incremental_abstract_successor_occurrence_v113,
)


def test_v113_historical_occurrence_incrementally_compiles_exact_successors():
    occurrence = build_incremental_abstract_successor_occurrence_v113(
        v111_pre.campaign_config_v111(),
        family="MAINTENANCE_CASCADE",
        seed=1_023_103,
        episode_indices=(201, 202, 203),
        factor_library=(
            v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    gate = occurrence["registered_gate"]
    accounting = occurrence["accounting"]
    assert gate["passed"] is True
    assert gate[
        "incremental_and_full_rebuild_actions_plans_receipts_labels_steps_equal"
    ] is True
    assert accounting["incremental_model_update_compilation_events"] < accounting[
        "matched_full_rebuild_update_compilation_events"
    ]
    assert accounting["model_compilation_events_avoided_against_full_rebuild"] > 0
    assert occurrence["compiled_model_used_as_safety_authority"] is False
    assert occurrence["official_scalar_cost"] is None
