from acfqp import construction_k7_legality_conditioned_quotient_preregistration_v106 as v106_pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.catalogue_closed_legality_conditioned_quotient_campaign_core_v107 import (
    build_catalogue_closed_legality_quotient_occurrence_v107,
)


def test_v107_development_catalogue_closes_v106_fallback_and_keeps_axes_separate():
    config = v106_pre.campaign_config_v106()
    occurrence = build_catalogue_closed_legality_quotient_occurrence_v107(
        config,
        family="MAINTENANCE_CASCADE",
        seed=1_018_103,
        episode_indices=(151, 152, 153),
        factor_library=(
            v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    receipt = occurrence["complete_anonymous_action_catalogue_receipt"]
    assert receipt["catalogue_complete_at_target_adapter_boundary"] is True
    assert receipt["catalogue_enumerated_before_target_episode_outcomes"] is True
    assert occurrence["registered_gate"][
        "every_abstract_plan_action_bound_to_catalogue_descriptor"
    ] is True
    assert occurrence["registered_gate"]["passed"] is True
    assert occurrence["accounting"]["scalar_cost_aggregation_performed"] is False
    assert occurrence["official_scalar_cost"] is None
