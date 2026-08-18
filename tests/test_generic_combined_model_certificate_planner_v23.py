import os

import pytest


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_COMBINED_CERTIFICATE_PLANNER") != "1",
    reason="explicit V23 matched combined-model development",
)
def test_v23_real_combined_model_remains_certificate_local():
    from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as pre
    from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as campaign
    from acfqp.construction_k7_residual_factor_library_v62 import (
        freeze_residual_factor_library_v62,
    )
    from acfqp.generic_combined_model_certificate_planner_v23 import (
        run_combined_model_certificate_episode_v23,
    )

    config = pre.campaign_config_v59()
    factor_library = pre.previous.previous.FACTOR_LIBRARY
    residual_library = freeze_residual_factor_library_v62().to_document()[
        "compiled_library"
    ]
    totals = {"prior": 0, "strict": 0}
    combined_successes = 0
    by_family = {}
    for family, seed in (
        ("BALANCED_BATCH_REFINEMENT", 590_951),
        ("COUPLED_EXCHANGE", 590_952),
        ("MAINTENANCE_CASCADE", 590_953),
    ):
        adapter = campaign.predecessor.predecessor.prior_ground._adapter(
            family, seed, config
        )
        partial = campaign.acquire_matched_true_bit_models_v59(
            adapter, factor_library, config
        )["ANONYMOUS_FACTOR_PRIOR_ON"]
        prior = run_combined_model_certificate_episode_v23(
            adapter,
            partial["candidate"],
            partial["rows"],
            residual_prior_library=residual_library,
            episode_index=0,
            maximum_abstract_depth=12,
            maximum_execution_steps=96,
        )
        strict = run_combined_model_certificate_episode_v23(
            adapter,
            partial["candidate"],
            partial["rows"],
            residual_prior_library=None,
            episode_index=0,
            maximum_abstract_depth=12,
            maximum_execution_steps=96,
        )
        for row in (prior, strict):
            assert row["success"] is True
            assert row["all_ground_queries_followed_failed_certificates"] is True
            assert row["combined_abstract_plan_used_as_safety_authority"] is False
        by_family[family] = {
            "labels": (
                prior["local_ground_support_labels"],
                strict["local_ground_support_labels"],
            ),
            "combined_successes": (
                prior["combined_abstract_plan_success_count"],
                strict["combined_abstract_plan_success_count"],
            ),
        }
        totals["prior"] += prior["local_ground_support_labels"]
        totals["strict"] += strict["local_ground_support_labels"]
        combined_successes += prior["combined_abstract_plan_success_count"]
    assert combined_successes > 0
    assert by_family == {
        "BALANCED_BATCH_REFINEMENT": {
            "labels": (55, 55),
            "combined_successes": (0, 0),
        },
        "COUPLED_EXCHANGE": {
            "labels": (22, 22),
            "combined_successes": (0, 0),
        },
        "MAINTENANCE_CASCADE": {
            "labels": (15, 15),
            "combined_successes": (1, 0),
        },
    }
    assert totals == {"prior": 92, "strict": 92}
