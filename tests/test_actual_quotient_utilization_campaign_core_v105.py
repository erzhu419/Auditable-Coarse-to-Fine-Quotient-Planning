from acfqp import construction_k7_hierarchical_utilization_preregistration_v104 as pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96
from acfqp.actual_quotient_utilization_campaign_core_v105 import (
    build_actual_quotient_utilization_occurrence_v105,
    derive_actual_quotient_utilization_v105,
)


def test_v105_actual_quotient_ordering_is_engine_input_and_reduces_labels():
    config = pre.campaign_config_v104()
    occurrence = build_actual_quotient_utilization_occurrence_v105(
        config,
        family="BALANCED_BATCH_REFINEMENT",
        seed=1_016_101,
        episode_indices=(131, 132, 133),
        factor_library=(
            v96.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    utilization = derive_actual_quotient_utilization_v105(
        occurrence["persistent_quotient_sequence"]
    )
    assert utilization["execution_step_count"] == 22
    assert utilization["quotient_proposal_admitted_execution_count"] == 16
    assert utilization["chosen_action_matches_admitted_quotient_proposal_count"] == 16
    assert utilization["ordering_is_engine_input_not_posthoc_policy_match"] is True
    assert occurrence["registered_gate"]["passed"] is True
    assert occurrence["accounting"]["quotient_lifetime_target_labels"] == 71
    assert occurrence["accounting"]["cold_direct_lifetime_target_labels"] == 183
    assert occurrence["complete_ground_world_model_synthesized"] is False
