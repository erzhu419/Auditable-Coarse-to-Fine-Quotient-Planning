import os

import pytest


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_ACTION_APPLICABILITY_V87") != "1",
    reason="explicit retained V86 target planner regression",
)
def test_v59_conditioned_model_orders_every_abstract_query_without_safety_authority():
    from acfqp import construction_k7_projected_target_preregistration_v86 as pre
    from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70_pre
    from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
    from acfqp.construction_k7_action_applicability_model_v87 import (
        load_action_applicability_model_v87,
    )
    from acfqp.construction_k7_projected_model_artifact_v86 import (
        load_projected_model_artifact_v86,
    )
    from acfqp.generic_applicability_certificate_planner_v59 import (
        run_matched_applicability_ablation_v59,
    )

    config = pre.campaign_config_v86()
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        config["target_family"], 889_101, config
    )
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    partial = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    model = load_projected_model_artifact_v86()[
        "projected_disagreement_successor_model"
    ]
    applicability = load_action_applicability_model_v87()[
        "action_applicability_program"
    ]
    ablation = run_matched_applicability_ablation_v59(
        adapter,
        partial["candidate"],
        partial["rows"],
        model,
        applicability,
        model_source_episode_index=0,
        episode_index=9,
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_target_ground_support_labels=config[
            "maximum_target_ground_support_labels"
        ],
        maximum_abstract_support_branch_evaluations=config[
            "maximum_relational_support_branch_evaluations"
        ],
        abstract_support_feasible_beam_width=config[
            "relational_support_feasible_beam_width"
        ],
    )
    derived = ablation["arms"]["APPLICABILITY_CONDITIONED_WORLD_MODEL"]
    strict = ablation["arms"]["STRICT_NO_REUSABLE_MODEL"]
    assert derived["success"] is True
    assert derived["abstract_plan_success_count"] > 0
    assert derived["abstract_plan_abstention_count"] == 0
    assert (
        derived["abstract_model_ordering_accepted_count"]
        == derived["abstract_plan_success_count"]
    )
    assert derived["inapplicable_action_branch_evaluations_avoided"] > 0
    assert derived["all_ground_queries_followed_failed_certificates"] is True
    assert (
        derived["reusable_abstract_model_or_applicability_used_as_safety_authority"]
        is False
    )
    assert (
        derived["target_certificate_local_ground_support_labels"]
        == strict["target_certificate_local_ground_support_labels"]
    )
