"""Fresh V70 matched role-free transfer versus exact-context planning."""

from __future__ import annotations

import copy
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v70 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_relational_residual_abstract_planner_v29 import (
    GenericRelationalResidualAbstractPlannerV29Error,
    plan_relational_residual_abstract_frontier_v29,
)
from acfqp.generic_role_free_relational_template_v33 import (
    GenericRoleFreeRelationalTemplateV33Error,
    instantiate_role_free_relational_template_v33,
)
from acfqp.generic_role_free_relational_world_model_planner_v34 import (
    GenericRoleFreeRelationalWorldModelPlannerV34Error,
    plan_role_free_relational_world_model_v34,
)
from acfqp.generic_source_complete_relational_world_model_v31 import (
    run_source_complete_relational_world_model_episode_v31,
)


class RoleFreeRelationalTransferCampaignCoreV70Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise RoleFreeRelationalTransferCampaignCoreV70Error(message)


def _ood_evidence(
    evidence: Mapping[str, Any], status_target: int
) -> dict[str, Any]:
    result = copy.deepcopy(evidence)
    layout = result["layout"]
    order = layout["state_canonical_to_raw"]
    raw_status = order[status_target]
    new_raw = len(order)
    new_canonical = len(order)
    order.append(new_raw)
    colors = layout.get("state_structural_colors")
    if type(colors) is list:
        colors.append("V70_OOD_DUPLICATE_STATUS_ROLE")
    result["unknown_residual_target_columns"].append(new_canonical)
    result["unknown_residual_target_columns"].sort()
    for row in result["raw_transition_rows"]:
        row["pre_vector"].append(row["pre_vector"][raw_status])
        row["post_vector"].append(row["post_vector"][raw_status])
    return result


def _run_occurrence(args: tuple[Any, ...]) -> dict[str, Any]:
    family, seed, factor_library, residual_library, template_library, config = args
    adapter = base.predecessor.predecessor.prior_ground._adapter(family, seed, config)
    partial = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    envelope = run_source_complete_relational_world_model_episode_v31(
        adapter,
        partial["candidate"],
        partial["rows"],
        residual_prior_library=residual_library,
        episode_index=0,
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        confidence_denominator=config["residual_confidence_denominator"],
        maximum_terminal_program_candidates_to_try=config[
            "maximum_terminal_program_candidates_to_try"
        ],
        maximum_relational_support_branch_evaluations=config[
            "maximum_relational_support_branch_evaluations"
        ],
        relational_support_feasible_beam_width=config[
            "relational_support_feasible_beam_width"
        ],
    )
    episode = envelope["predecessor_v30_episode"]
    retained = envelope["terminal_program_source_evidence"]
    target_source = {
        "layout": retained["layout"],
        "unknown_residual_target_columns": retained[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": retained["raw_transition_rows"],
    }
    common = {
        "candidate": partial["candidate"],
        "observed_rows": partial["rows"],
        "catalogue": adapter.catalogue,
        "initial_raw_state": adapter.encode(adapter.initial()),
        "batch_exact": episode["final_batch_exact_residual_support"],
    }
    try:
        transferred = plan_role_free_relational_world_model_v34(
            common["candidate"],
            common["observed_rows"],
            common["catalogue"],
            common["initial_raw_state"],
            common["batch_exact"],
            template_library,
            target_source,
            maximum_depth=config["maximum_abstract_depth"],
            maximum_terminal_program_candidates_to_try=config[
                "maximum_terminal_program_candidates_to_try"
            ],
            maximum_support_branch_evaluations=config[
                "maximum_relational_support_branch_evaluations"
            ],
            support_feasible_beam_width=config[
                "relational_support_feasible_beam_width"
            ],
        )
        transfer_result = {
            "status": "ROLE_FREE_TRANSFER_PLAN_FOUND",
            "plan": transferred,
        }
    except (
        GenericRoleFreeRelationalWorldModelPlannerV34Error,
        GenericRoleFreeRelationalTemplateV33Error,
        GenericRelationalResidualAbstractPlannerV29Error,
    ) as error:
        transfer_result = {
            "status": "ROLE_FREE_TRANSFER_ABSTAINED",
            "failure": str(error),
        }
    try:
        strict = plan_relational_residual_abstract_frontier_v29(
            common["candidate"],
            common["observed_rows"],
            common["catalogue"],
            common["initial_raw_state"],
            common["batch_exact"],
            episode["final_relational_terminal_program"],
            maximum_depth=config["maximum_abstract_depth"],
            maximum_terminal_program_candidates_to_try=config[
                "maximum_terminal_program_candidates_to_try"
            ],
            maximum_support_branch_evaluations=config[
                "maximum_relational_support_branch_evaluations"
            ],
            support_feasible_beam_width=config[
                "relational_support_feasible_beam_width"
            ],
        )
        strict_result = {
            "status": "EXACT_CONTEXT_PLAN_FOUND",
            "plan": strict,
        }
    except GenericRelationalResidualAbstractPlannerV29Error as error:
        strict_result = {
            "status": "EXACT_CONTEXT_PLAN_ABSTAINED",
            "failure": str(error),
        }
    ood_source = _ood_evidence(
        target_source, episode["final_relational_terminal_program"]["status_target_column"]
    )
    try:
        ood = instantiate_role_free_relational_template_v33(
            template_library,
            ood_source,
            maximum_exact_instantiations=config[
                "maximum_terminal_program_candidates_to_try"
            ],
        )
    except GenericRoleFreeRelationalTemplateV33Error as error:
        ood_result = {
            "status": "INCOMPATIBLE_SCHEMA_REJECTED",
            "reason": str(error),
        }
    else:
        if ood["exact_target_instantiation_count"] != 0:
            _fail("V70 incompatible schema incorrectly received a template")
        ood_result = {
            "status": "INCOMPATIBLE_SCHEMA_REJECTED",
            "instantiation_id": ood["instantiation_id"],
        }
    if (
        envelope["all_v28_source_rows_retained"] is not True
        or episode["success"] is not True
        or episode["all_ground_queries_followed_failed_certificates"] is not True
        or episode["query_local_exact_overlay_exclusively_used_for_safety"] is not True
    ):
        _fail("V70 target evidence safety boundary changed")
    payload = {
        "schema": "acfqp.role_free_relational_transfer_occurrence.v70",
        "family": family,
        "seed": seed,
        "common_partial_acquisition_id": partial["document"]["acquisition_id"],
        "common_partial_ground_support_labels": partial["document"][
            "ground_support_labels"
        ],
        "target_source_complete_episode": envelope,
        "transferred_role_free_arm": transfer_result,
        "strict_exact_context_arm": strict_result,
        "incompatible_schema_ood_control": ood_result,
        "same_target_rows_residual_support_and_planner_caps_between_arms": True,
        "only_switched_variable": "TERMINAL_PROGRAM_SOURCE_ROLE_FREE_LIBRARY_VS_TARGET_EXACT_CONTEXT",
        "query_local_overlay_only_safety_authority": True,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v70(
            domains.CONSTRUCTION_K7_ROLE_FREE_RELATIONAL_OCCURRENCE_V70_DOMAIN,
            payload,
        ),
    }


def build_role_free_relational_transfer_campaign_document_v70(
    config: Mapping[str, Any],
    preregistration_id: str,
    v69_campaign_id: str,
    v69_verification_id: str,
    template_library_artifact_id: str,
    factor_library: Mapping[str, Any],
    residual_library: Mapping[str, Any],
    template_library: Mapping[str, Any],
    offline_template_source_labels: int,
) -> dict[str, Any]:
    arguments = [
        (family, seed, factor_library, residual_library, template_library, config)
        for family, seeds in config["target_seeds"].items()
        for seed in seeds
    ]
    if config["worker_count"] == 1:
        occurrences = [_run_occurrence(row) for row in arguments]
    else:
        with ProcessPoolExecutor(max_workers=config["worker_count"]) as executor:
            occurrences = list(executor.map(_run_occurrence, arguments))
    if len(occurrences) != config["target_occurrence_count"]:
        _fail("V70 occurrence inventory changed")
    transfer_success = sum(
        row["transferred_role_free_arm"]["status"]
        == "ROLE_FREE_TRANSFER_PLAN_FOUND"
        for row in occurrences
    )
    strict_success = sum(
        row["strict_exact_context_arm"]["status"] == "EXACT_CONTEXT_PLAN_FOUND"
        for row in occurrences
    )
    ood_rejections = sum(
        row["incompatible_schema_ood_control"]["status"]
        == "INCOMPATIBLE_SCHEMA_REJECTED"
        for row in occurrences
    )
    gate_passed = transfer_success > 0 and ood_rejections == len(occurrences)
    family_projections = {}
    for family in config["target_seeds"]:
        selected = [row for row in occurrences if row["family"] == family]
        family_projections[family] = {
            "occurrence_count": len(selected),
            "transferred_plan_success_count": sum(
                row["transferred_role_free_arm"]["status"]
                == "ROLE_FREE_TRANSFER_PLAN_FOUND"
                for row in selected
            ),
            "strict_plan_success_count": sum(
                row["strict_exact_context_arm"]["status"]
                == "EXACT_CONTEXT_PLAN_FOUND"
                for row in selected
            ),
            "target_certificate_local_labels": sum(
                row["target_source_complete_episode"]["predecessor_v30_episode"][
                    "local_ground_support_labels"
                ]
                for row in selected
            ),
        }
    episodes = [
        row["target_source_complete_episode"]["predecessor_v30_episode"]
        for row in occurrences
    ]
    transfer_plans = [
        row["transferred_role_free_arm"].get("plan") for row in occurrences
    ]
    strict_plans = [row["strict_exact_context_arm"].get("plan") for row in occurrences]
    accounting = {
        "offline_template_source_labels": offline_template_source_labels,
        "offline_residual_library_labels": config["offline_library_labels"],
        "target_common_partial_acquisition_labels": sum(
            row["common_partial_ground_support_labels"] for row in occurrences
        ),
        "target_certificate_local_labels": sum(
            row["local_ground_support_labels"] for row in episodes
        ),
        "target_execution_steps": sum(row["execution_steps"] for row in episodes),
        "target_online_partial_planning_compute_events": sum(
            row["partial_planning_compute_events"] for row in episodes
        ),
        "target_online_relational_planning_compute_events": sum(
            row["relational_abstract_support_branch_evaluations"] for row in episodes
        ),
        "transfer_template_binding_evaluations": sum(
            0
            if plan is None
            else plan["target_instantiation"]["binding_evaluation_count"]
            for plan in transfer_plans
        ),
        "transfer_abstract_support_branch_evaluations": sum(
            0 if plan is None else plan["abstract_plan"]["abstract_support_branch_evaluations"]
            for plan in transfer_plans
        ),
        "strict_abstract_support_branch_evaluations": sum(
            0 if plan is None else plan["abstract_support_branch_evaluations"]
            for plan in strict_plans
        ),
        "all_axes_separate": True,
    }
    payload = {
        "schema": "acfqp.role_free_relational_transfer_campaign.v70",
        "preregistration_id": preregistration_id,
        "v69_campaign_id": v69_campaign_id,
        "v69_verification_id": v69_verification_id,
        "template_library_artifact_id": template_library_artifact_id,
        "occurrences": occurrences,
        "accounting": accounting,
        "family_projections": family_projections,
        "registered_role_free_transfer_gate": {
            "transferred_plan_success_count": transfer_success,
            "strict_plan_success_count": strict_success,
            "incompatible_schema_ood_rejection_count": ood_rejections,
            "required_ood_rejection_count": len(occurrences),
            "required_relation": "TRANSFER_PLAN_GT_ZERO_AND_ALL_INCOMPATIBLE_SCHEMA_OOD_REJECTED",
            "passed": gate_passed,
            "transfer_outperform_strict_required": False,
            "target_label_reduction_required": False,
        },
        "cross_occurrence_role_free_templates_reused": True,
        "target_observation_exactness_required_before_planning": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "transferred_abstract_plan_used_as_safety_authority": False,
        "producer_free_verification_present": False,
        "online_transfer_planner_integrated": False,
        "complete_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **payload,
        "campaign_id": domains.extension_content_id_v70(
            domains.CONSTRUCTION_K7_ROLE_FREE_RELATIONAL_CAMPAIGN_V70_DOMAIN,
            payload,
        ),
    }
    if not gate_passed:
        _fail(
            "V70 registered Gate failed: "
            f"transfer={transfer_success} ood={ood_rejections} "
            f"failed_campaign_id={document['campaign_id']}"
        )
    return document


__all__ = (
    "RoleFreeRelationalTransferCampaignCoreV70Error",
    "build_role_free_relational_transfer_campaign_document_v70",
)
