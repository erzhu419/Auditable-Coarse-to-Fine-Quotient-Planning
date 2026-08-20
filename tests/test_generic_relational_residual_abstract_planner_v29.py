import os

import pytest

from acfqp.generic_relational_residual_abstract_planner_v29 import (
    GenericRelationalResidualAbstractPlannerV29Error,
    plan_relational_residual_abstract_frontier_v29,
    plan_relational_residual_abstract_program_v29,
)


def test_v29_rejects_foreign_programs_before_search():
    with pytest.raises(GenericRelationalResidualAbstractPlannerV29Error):
        plan_relational_residual_abstract_program_v29(
            object(), (), (), (), {}, {}, maximum_depth=1
        )


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_MULTI_RESIDUAL") != "1",
    reason="explicit V29 relational residual abstract planning development",
)
def test_v29_replaces_status_overapproximation_with_relational_successor_program():
    from acfqp import construction_k7_combined_model_planning_preregistration_v66 as pre
    from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as campaign
    from acfqp.construction_k7_residual_factor_library_v62 import (
        freeze_residual_factor_library_v62,
    )
    from acfqp.generic_batch_exact_multi_residual_compiler_v27 import (
        compile_batch_exact_multi_residual_support_v27,
    )
    from acfqp.generic_certificate_guided_partial_planner_v16 import (
        run_certificate_guided_partial_episode_v16,
    )
    from acfqp.generic_multi_residual_acquisition_v24 import (
        acquire_multi_residual_factors_v24,
    )
    from acfqp.generic_relational_terminal_program_v28 import (
        synthesize_relational_terminal_program_v28,
    )

    config = pre.campaign_config_v66()
    adapter = campaign.predecessor.predecessor.prior_ground._adapter(
        "MAINTENANCE_CASCADE", 690_974, config
    )
    partial = campaign.acquire_matched_true_bit_models_v59(
        adapter, pre.previous.previous.previous.FACTOR_LIBRARY, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    episode = run_certificate_guided_partial_episode_v16(
        adapter,
        partial["candidate"],
        partial["rows"],
        episode_index=0,
        maximum_abstract_depth=12,
        maximum_execution_steps=96,
    )
    document = partial["candidate"].public_document
    evidence = {
        "layout": document["layout"],
        "unknown_residual_target_columns": document[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": episode["raw_local_transition_rows"],
    }
    library = freeze_residual_factor_library_v62().to_document()["compiled_library"]
    acquisition = acquire_multi_residual_factors_v24(
        evidence, prior_library=library
    )
    exact = compile_batch_exact_multi_residual_support_v27(
        acquisition, evidence, prior_library=library
    )
    terminal_evidence = {
        **evidence,
        "raw_transition_rows": [
            *(row.to_document() for row in partial["rows"]),
            *episode["raw_local_transition_rows"],
        ],
    }

    terminal = synthesize_relational_terminal_program_v28(terminal_evidence)
    plan = plan_relational_residual_abstract_frontier_v29(
        partial["candidate"],
        partial["rows"],
        adapter.catalogue,
        adapter.encode(adapter.initial()),
        exact,
        terminal,
        maximum_depth=12,
        maximum_terminal_program_candidates_to_try=32,
    )
    assert plan["all_observed_state_coordinates_represented"] is True
    assert plan["remaining_unknown_target_columns"] == []
    assert plan["status_successor_derived_from_anonymous_relational_program"] is True
    assert plan["terminal_relation_and_transition_program_jointly_selected"] is True
    assert plan["joint_selection_used_ground_transition_or_certificate_authority"] is False
    assert plan["terminal_candidate_attempt_count"] > 1
    assert len(plan["rejected_terminal_candidate_attempts"]) + 1 == plan[
        "terminal_candidate_attempt_count"
    ]
    assert plan["ground_transition_accessed_during_abstract_search"] is False
    assert plan["abstract_plan_used_as_safety_authority"] is False
    assert plan["complete_world_model_claimed"] is False
