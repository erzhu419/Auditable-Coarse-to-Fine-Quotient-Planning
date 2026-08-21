from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96
from acfqp import construction_k7_quotient_utilization_preregistration_v105 as v105
from acfqp.legality_conditioned_quotient_campaign_core_v106 import (
    build_legality_conditioned_quotient_occurrence_v106,
)


def test_v106_development_occurrence_conditions_quotient_on_certified_legality():
    occurrence = build_legality_conditioned_quotient_occurrence_v106(
        v105.campaign_config_v105(),
        family="MAINTENANCE_CASCADE",
        seed=1_017_103,
        episode_indices=(141, 142, 143),
        factor_library=(
            v96.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    utilization = occurrence["legality_conditioned_quotient_utilization"]
    sequence = occurrence[
        "persistent_legality_conditioned_quotient_sequence"
    ]
    assert occurrence["registered_gate"]["passed"] is True
    assert utilization["quotient_proposal_admitted_execution_count"] == 12
    assert utilization[
        "chosen_action_matches_admitted_quotient_proposal_count"
    ] == 11
    assert utilization["execution_step_count"] == 12
    assert utilization["certificate_local_legality_plan_count"] == 2
    assert sequence[
        "certified_legality_reused_as_abstract_boundary_not_recharged"
    ] is True
    assert sequence["every_new_ground_query_followed_a_failed_certificate"] is True
    assert occurrence["accounting"]["quotient_lifetime_target_labels"] == 36
    assert occurrence["accounting"]["cold_direct_lifetime_target_labels"] == 63
    assert occurrence["complete_ground_world_model_synthesized"] is False
    assert occurrence["official_scalar_cost"] is None
    assert occurrence["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
