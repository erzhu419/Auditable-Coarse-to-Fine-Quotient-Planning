import os

import pytest


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_ONLINE_RESIDUAL_PLANNER") != "1",
    reason="explicit three-family online residual planning development",
)
def test_v21_real_online_guidance_preserves_certificate_local_safety():
    from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as pre
    from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as campaign
    from acfqp.construction_k7_residual_factor_library_v62 import (
        freeze_residual_factor_library_v62,
    )
    from acfqp.generic_online_residual_guided_planner_v21 import (
        run_online_residual_guided_episode_v21,
    )

    config = pre.campaign_config_v59()
    factor_library = pre.previous.previous.FACTOR_LIBRARY
    residual_library = freeze_residual_factor_library_v62().to_document()[
        "compiled_library"
    ]
    totals = {"prior": 0, "strict": 0}
    activations = 0
    by_family = {}
    for family, seed in (
        ("BALANCED_BATCH_REFINEMENT", 590_941),
        ("COUPLED_EXCHANGE", 590_942),
        ("MAINTENANCE_CASCADE", 590_943),
    ):
        adapter = campaign.predecessor.predecessor.prior_ground._adapter(
            family, seed, config
        )
        partial = campaign.acquire_matched_true_bit_models_v59(
            adapter, factor_library, config
        )["ANONYMOUS_FACTOR_PRIOR_ON"]
        prior = run_online_residual_guided_episode_v21(
            adapter,
            partial["candidate"],
            partial["rows"],
            residual_prior_library=residual_library,
            episode_index=0,
            maximum_abstract_depth=12,
            maximum_execution_steps=96,
        )
        strict = run_online_residual_guided_episode_v21(
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
            assert row["residual_proposal_used_as_safety_authority"] is False
        by_family[family] = (
            prior["local_ground_support_labels"],
            strict["local_ground_support_labels"],
        )
        totals["prior"] += prior["local_ground_support_labels"]
        totals["strict"] += strict["local_ground_support_labels"]
        activations += len(prior["residual_proposal_activations"])
    assert activations > 0
    assert by_family == {
        "BALANCED_BATCH_REFINEMENT": (50, 50),
        "COUPLED_EXCHANGE": (27, 28),
        "MAINTENANCE_CASCADE": (21, 23),
    }
    assert totals == {"prior": 98, "strict": 101}
