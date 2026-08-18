import os

import pytest

from acfqp.generic_partial_residual_abstract_planner_v22 import (
    GenericPartialResidualAbstractPlannerV22Error,
)


def test_v22_rejects_non_actionable_residual_candidate_before_search():
    from acfqp.generic_partial_residual_abstract_planner_v22 import (
        plan_partial_residual_abstract_program_v22,
    )

    with pytest.raises(GenericPartialResidualAbstractPlannerV22Error):
        plan_partial_residual_abstract_program_v22(
            object(), (), (), (), {"target_column": 0}, maximum_depth=1
        )


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_PARTIAL_RESIDUAL_PLANNER") != "1",
    reason="explicit two-family V22 combined abstract planning development",
)
def test_v22_real_combined_model_searches_without_ground_transition_access():
    from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as pre
    from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as campaign
    from acfqp.construction_k7_residual_factor_library_v62 import (
        freeze_residual_factor_library_v62,
    )
    from acfqp.generic_atomic_expression_world_model_v4 import (
        FlatRawActionV4,
        FlatRawTransitionV4,
    )
    from acfqp.generic_certificate_guided_partial_planner_v16 import (
        run_certificate_guided_partial_episode_v16,
    )
    from acfqp.generic_total_adaptive_residual_acquisition_v20 import (
        acquire_total_adaptive_residual_factor_v20,
    )
    from acfqp.generic_partial_residual_abstract_planner_v22 import (
        plan_partial_residual_abstract_program_v22,
    )

    config = pre.campaign_config_v59()
    factor_library = pre.previous.previous.FACTOR_LIBRARY
    residual_library = freeze_residual_factor_library_v62().to_document()[
        "compiled_library"
    ]

    def restore(document):
        action = document["selected_action"]
        return FlatRawTransitionV4(
            document["occurrence"],
            document["transition_index"],
            tuple(document["pre_vector"]),
            tuple(document["legal_action_keys_before"]),
            FlatRawActionV4(
                action["action_key"], tuple(action["anonymous_fields"])
            ),
            tuple(document["post_vector"]),
            tuple(document["legal_action_keys_after"]),
            document["terminal_acceptance_after"],
            document["outcome_tape_sha256"],
        )

    for family, seed in (
        ("COUPLED_EXCHANGE", 590_942),
        ("MAINTENANCE_CASCADE", 590_943),
    ):
        adapter = campaign.predecessor.predecessor.prior_ground._adapter(
            family, seed, config
        )
        partial = campaign.acquire_matched_true_bit_models_v59(
            adapter, factor_library, config
        )["ANONYMOUS_FACTOR_PRIOR_ON"]
        episode = run_certificate_guided_partial_episode_v16(
            adapter,
            partial["candidate"],
            partial["rows"],
            episode_index=0,
            maximum_abstract_depth=12,
            maximum_execution_steps=96,
        )
        local_rows = tuple(restore(row) for row in episode["raw_local_transition_rows"])
        candidate_document = partial["candidate"].public_document
        acquisition = acquire_total_adaptive_residual_factor_v20(
            {
                "layout": candidate_document["layout"],
                "unknown_residual_target_columns": candidate_document[
                    "unknown_residual_target_columns"
                ],
                "raw_transition_rows": [row.to_document() for row in local_rows],
            },
            prior_library=residual_library,
            confidence_denominator=64,
        )
        assert acquisition["status"] == "STATISTICAL_PROPOSAL_ISSUED"
        plan = plan_partial_residual_abstract_program_v22(
            partial["candidate"],
            partial["rows"],
            adapter.catalogue,
            adapter.encode(adapter.initial()),
            acquisition["candidate"],
            maximum_depth=12,
        )
        assert plan["support_feasible_receding_plan_found"] is True
        assert plan["ground_transition_accessed_during_abstract_search"] is False
        assert plan["abstract_plan_used_as_safety_authority"] is False
        assert plan["abstract_support_branch_evaluations"] > 0
