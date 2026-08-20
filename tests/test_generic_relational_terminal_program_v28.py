import os

import pytest

from acfqp.generic_relational_terminal_program_v28 import (
    GenericRelationalTerminalProgramV28Error,
    synthesize_relational_terminal_program_v28,
)


def test_v28_rejects_empty_terminal_evidence():
    with pytest.raises(GenericRelationalTerminalProgramV28Error):
        synthesize_relational_terminal_program_v28({})


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_MULTI_RESIDUAL") != "1",
    reason="explicit V28 anonymous relational terminal-program development",
)
def test_v28_discovers_status_coordinate_tokens_and_relational_tree_from_raw_rows():
    from acfqp import construction_k7_combined_model_planning_preregistration_v66 as pre
    from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as campaign
    from acfqp.generic_certificate_guided_partial_planner_v16 import (
        run_certificate_guided_partial_episode_v16,
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
    candidate = partial["candidate"].public_document
    program = synthesize_relational_terminal_program_v28(
        {
            "layout": candidate["layout"],
            "unknown_residual_target_columns": candidate[
                "unknown_residual_target_columns"
            ],
            "raw_transition_rows": episode["raw_local_transition_rows"],
        }
    )
    assert program["status_target_column"] in candidate[
        "unknown_residual_target_columns"
    ]
    assert program["exact_on_complete_frozen_query_pool"] is True
    assert program["state_column_roles_preregistered"] is False
    assert program["status_token_values_preregistered"] is False
    assert program["future_unseen_terminal_authority_present"] is False
