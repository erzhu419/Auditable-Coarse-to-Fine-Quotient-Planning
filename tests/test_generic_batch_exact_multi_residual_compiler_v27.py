import os

import pytest

from acfqp.generic_batch_exact_multi_residual_compiler_v27 import (
    GenericBatchExactMultiResidualCompilerV27Error,
    compile_batch_exact_multi_residual_support_v27,
)


def test_v27_rejects_foreign_predecessor():
    with pytest.raises(GenericBatchExactMultiResidualCompilerV27Error):
        compile_batch_exact_multi_residual_support_v27({}, {}, prior_library=None)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_MULTI_RESIDUAL") != "1",
    reason="explicit V27 stochastic batch-support development",
)
def test_v27_rejects_prior_favored_support_that_is_not_batch_exact():
    from acfqp import construction_k7_combined_model_planning_preregistration_v66 as pre
    from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as campaign
    from acfqp.construction_k7_residual_factor_library_v62 import (
        freeze_residual_factor_library_v62,
    )
    from acfqp.generic_certificate_guided_partial_planner_v16 import (
        run_certificate_guided_partial_episode_v16,
    )
    from acfqp.generic_multi_residual_acquisition_v24 import (
        acquire_multi_residual_factors_v24,
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
    evidence = {
        "layout": candidate["layout"],
        "unknown_residual_target_columns": candidate[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": episode["raw_local_transition_rows"],
    }
    library = freeze_residual_factor_library_v62().to_document()["compiled_library"]
    acquisition = acquire_multi_residual_factors_v24(
        evidence, prior_library=library
    )
    original_by_target = {
        row["target_column"]: row["total_acquisition"]["candidate"]
        for row in acquisition["target_results"]
    }
    assert any(
        row["predictive_support_excess"] > 0
        for row in original_by_target.values()
        if row is not None
    )
    result = compile_batch_exact_multi_residual_support_v27(
        acquisition, evidence, prior_library=library
    )
    assert result["joint_batch_exact_candidate_count"] == 1
    assert result["all_targets_batch_exact_on_complete_frozen_query_pool"] is False
    assert any(
        row["original_selected_candidate_retained"] is False
        for row in result["target_refinements"]
    )
    assert result["future_unseen_support_authority_present"] is False
    assert result["complete_residual_world_model_synthesized"] is False
