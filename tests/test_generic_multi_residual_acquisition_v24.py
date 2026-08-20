import os

import pytest

from acfqp.generic_multi_residual_acquisition_v24 import (
    GenericMultiResidualAcquisitionV24Error,
    acquire_multi_residual_factors_v24,
)


def test_v24_rejects_empty_shared_query_pool():
    with pytest.raises(GenericMultiResidualAcquisitionV24Error):
        acquire_multi_residual_factors_v24(
            {
                "layout": {},
                "unknown_residual_target_columns": [0],
                "raw_transition_rows": [],
            },
            prior_library=None,
        )


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_MULTI_RESIDUAL") != "1",
    reason="explicit V24 shared-pool multi-target development",
)
def test_v24_real_shared_pool_totalizes_each_unknown_target_without_double_tax():
    from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as pre
    from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as campaign
    from acfqp.construction_k7_residual_factor_library_v62 import (
        freeze_residual_factor_library_v62,
    )
    from acfqp.generic_certificate_guided_partial_planner_v16 import (
        run_certificate_guided_partial_episode_v16,
    )
    from acfqp.generic_multi_residual_acquisition_v24 import (
        acquire_multi_residual_factors_v24,
        replay_multi_residual_factors_v24,
    )

    config = pre.campaign_config_v59()
    adapter = campaign.predecessor.predecessor.prior_ground._adapter(
        "COUPLED_EXCHANGE", 590_962, config
    )
    partial = campaign.acquire_matched_true_bit_models_v59(
        adapter, pre.previous.previous.FACTOR_LIBRARY, config
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
    library = freeze_residual_factor_library_v62().to_document()[
        "compiled_library"
    ]
    acquisition = acquire_multi_residual_factors_v24(
        evidence, prior_library=library
    )
    replay = replay_multi_residual_factors_v24(
        acquisition, evidence, prior_library=library
    )
    assert replay["all_target_totalizers_reconstructed"] is True
    assert acquisition["shared_physical_ground_support_labels"] == episode[
        "queried_state_action_count"
    ]
    assert acquisition[
        "per_target_label_consumption_summed_as_physical_samples"
    ] is False
    assert acquisition["complete_residual_world_model_synthesized"] is False
    assert acquisition[
        "positive_excess_supports_may_only_overapproximate_successors"
    ] is True
    assert acquisition["compilable_candidate_count"] >= acquisition[
        "actionable_candidate_count"
    ]
    assert len(acquisition["target_results"]) == len(
        candidate["unknown_residual_target_columns"]
    )
