"""Fresh multi-source Gate for generic contextual-ordinal residual synthesis."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping, NoReturn

from acfqp import all_frontier_multi_source_campaign_core_v83 as v83
from acfqp import construction_k7_domain_registry_extension_v84 as domains
from acfqp.generic_contextual_ordinal_frontier_acquisition_v54 import (
    run_relation_covering_contextual_ordinal_acquisition_v54,
)
from acfqp.generic_contextual_ordinal_model_compiler_v54 import (
    GenericContextualOrdinalModelCompilerV54Error,
    compile_contextual_ordinal_model_v54,
)
from acfqp.generic_contextual_ordinal_residual_v54 import (
    GenericContextualOrdinalResidualV54Error,
    attach_contextual_action_supports_v54,
)
from acfqp.generic_structural_source_partition_v50 import (
    partition_canonical_source_evidence_v50,
)


class ContextualOrdinalSourceCampaignCoreV84Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ContextualOrdinalSourceCampaignCoreV84Error(message)


def _member(args: tuple[Any, ...]) -> dict[str, Any]:
    inherited = v83._member(args)  # noqa: SLF001
    candidate = inherited.pop("partial_candidate")
    inherited.pop("member_id")
    inherited["schema"] = "acfqp.contextual_ordinal_source_member.v84"
    member_id = domains.extension_content_id_v84(
        domains.CONSTRUCTION_K7_CONTEXTUAL_ORDINAL_MEMBER_V84_DOMAIN,
        inherited,
    )
    return {**inherited, "member_id": member_id, "partial_candidate": candidate}


def build_contextual_ordinal_source_campaign_document_v84(
    config: Mapping[str, Any],
    preregistration_id: str,
    v83_failed_campaign_id: str,
    factor_library: Mapping[str, Any],
    residual_library: Mapping[str, Any],
    template_library: Mapping[str, Any],
    offline_template_source_labels: int,
) -> dict[str, Any]:
    args = [
        (
            config["source_family"],
            seed,
            factor_library,
            residual_library,
            config,
        )
        for seed in config["source_pool_seeds"]
    ]
    with ProcessPoolExecutor(max_workers=config["source_worker_count"]) as executor:
        members = list(executor.map(_member, args))
    if len(members) != config["required_source_member_count"]:
        _fail("V84 source member count changed")
    partition = partition_canonical_source_evidence_v50(
        [
            {
                "member_id": row["member_id"],
                "source_evidence": row["source_evidence"],
                "action_catalogue": row["action_catalogue"],
            }
            for row in members
        ]
    )
    member_by_id = {row["member_id"]: row for row in members}
    candidate_by_member = {
        row["member_id"]: row["partial_candidate"] for row in members
    }
    group_results = []
    for structural_group in partition["structural_groups"]:
        evidence = attach_contextual_action_supports_v54(
            structural_group, member_by_id
        )
        acquisition = run_relation_covering_contextual_ordinal_acquisition_v54(
            evidence,
            role_free_template_library=template_library,
            maximum_exact_instantiations=config[
                "maximum_terminal_program_candidates_to_try"
            ],
            confidence_denominator=config["prequential_confidence_denominator"],
        )
        learned = acquisition["contextual_ordinal_frontier_acquisition"]
        model = None
        reason = None
        status = "GROUP_ACQUISITION_ABSTAINED_NONCERTIFICATE"
        eligible = learned["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
        if eligible:
            try:
                model = compile_contextual_ordinal_model_v54(
                    candidate_by_member[structural_group["source_member_ids"][0]],
                    evidence,
                    acquisition,
                )
            except (
                GenericContextualOrdinalModelCompilerV54Error,
                GenericContextualOrdinalResidualV54Error,
            ) as error:
                status = "GROUP_MODEL_COMPILATION_ABSTAINED_NONCERTIFICATE"
                reason = str(error)
            else:
                status = "GROUP_CONTEXTUAL_MODEL_COMPILED_NO_TARGET_EXECUTION"
        group_results.append(
            {
                "structural_signature_id": structural_group[
                    "structural_signature_id"
                ],
                "source_member_ids": structural_group["source_member_ids"],
                "source_member_count": structural_group["source_member_count"],
                "contextual_action_support_projection_id": evidence[
                    "contextual_action_support_projection_id"
                ],
                "relation_covering_contextual_ordinal_acquisition": acquisition,
                "contextual_ordinal_successor_model": model,
                "group_compilation_eligible": eligible,
                "status": status,
                "model_compilation_reason": reason,
            }
        )
    public_members = [
        {key: value for key, value in row.items() if key != "partial_candidate"}
        for row in members
    ]
    source_episodes = [
        row["source_complete_episode"]["predecessor_v30_episode"]
        for row in public_members
    ]
    source_clean = all(
        episode["success"] is True
        and episode["all_ground_queries_followed_failed_certificates"] is True
        and episode["query_local_exact_overlay_exclusively_used_for_safety"] is True
        for episode in source_episodes
    )
    eligible_groups = [row for row in group_results if row["group_compilation_eligible"]]
    models = [
        row["contextual_ordinal_successor_model"]
        for row in group_results
        if row["contextual_ordinal_successor_model"] is not None
    ]
    every_eligible_compiled = bool(eligible_groups) and all(
        row["contextual_ordinal_successor_model"] is not None
        for row in eligible_groups
    )
    compiled_member_count = sum(
        row["source_member_count"]
        for row in group_results
        if row["contextual_ordinal_successor_model"] is not None
    )
    every_model_contextual = bool(models) and all(
        model["contextual_ordinal_action_support_operator_present"] is True
        for model in models
    )
    every_model_retains_all = bool(models) and all(
        model["every_batch_exact_residual_expression_retained"] is True
        for model in models
    )
    passed = (
        len(public_members) == config["required_source_member_count"]
        and source_clean
        and partition["every_source_member_retained_exactly_once"] is True
        and len(models) >= config["minimum_compiled_model_count"]
        and compiled_member_count >= config["minimum_compiled_source_member_count"]
        and every_eligible_compiled
        and every_model_contextual
        and every_model_retains_all
    )
    learned_rows = [
        group["relation_covering_contextual_ordinal_acquisition"][
            "contextual_ordinal_frontier_acquisition"
        ]
        for group in group_results
    ]
    attempts = [
        attempt for learned in learned_rows for attempt in learned["proposal_attempts"]
    ]
    payload = {
        "schema": "acfqp.contextual_ordinal_source_campaign.v84",
        "preregistration_id": preregistration_id,
        "v83_failed_campaign_id": v83_failed_campaign_id,
        "source_members": public_members,
        "structural_source_partition": partition,
        "structural_group_results": group_results,
        "acquisition_diagnostics": {
            "proposal_attempt_count": len(attempts),
            "semantic_class_coverage_attempt_count": sum(
                row["semantic_class_coverage_complete"] is True for row in attempts
            ),
            "contextual_ordinal_ready_attempt_count": sum(
                row["compiler_readiness"]["contextual_ordinal_candidate_present"]
                is True
                for row in attempts
            ),
            "acquisition_eligible_attempt_count": sum(
                row["training_calibrated_after_all_acquisition_guards"] is True
                for row in attempts
            ),
            "retired_joint_frontier_proposal_count": sum(
                learned["retired_failed_proposal_count"] for learned in learned_rows
            ),
            "all_terminal_and_residual_candidates_checked_prequentially": True,
            "all_terminal_and_residual_candidates_checked_on_heldout": True,
            "confirmation_budget_derived_from_candidate_mdl_and_confidence": True,
        },
        "retained_model_diagnostics": {
            "compiled_model_count": len(models),
            "compiled_source_member_count": compiled_member_count,
            "retained_terminal_frontier_candidate_count": sum(
                model["mdl_minimal_terminal_candidate_count"] for model in models
            ),
            "retained_residual_expression_count": sum(
                row["batch_exact_candidate_count"]
                for model in models
                for row in model["residual_version_spaces"]
            ),
            "contextual_ordinal_model_count": sum(
                model["contextual_ordinal_action_support_operator_present"] is True
                for model in models
            ),
            "multiple_residual_proposals_jointly_compiled_in_any_model": any(
                model["multiple_residual_proposals_jointly_compiled"] is True
                for model in models
            ),
        },
        "accounting": {
            "offline_template_source_labels": offline_template_source_labels,
            "offline_residual_library_labels": config["offline_library_labels"],
            "source_common_partial_labels": sum(
                row["common_partial_acquisition"]["ground_support_labels"]
                for row in public_members
            ),
            "source_certificate_local_labels": sum(
                row["local_ground_support_labels"] for row in source_episodes
            ),
            "group_acquisition_query_groups_consumed": sum(
                row["stopped_physical_ground_support_labels"]
                if type(row["stopped_physical_ground_support_labels"]) is int
                else row["full_query_stream_ground_support_labels"]
                for row in learned_rows
            ),
            "group_acquisition_query_groups_are_not_physical_label_count": True,
            "source_execution_steps": sum(row["execution_steps"] for row in source_episodes),
            "source_partial_planning_compute_events": sum(
                row["partial_planning_compute_events"] for row in source_episodes
            ),
            "source_relational_planning_compute_events": sum(
                row["relational_abstract_support_branch_evaluations"]
                for row in source_episodes
            ),
            "terminal_candidate_derivation_compute_events": sum(
                row["terminal_candidate_derivation_compute_events"]
                for row in learned_rows
            ),
            "contextual_version_space_readiness_compute_events": sum(
                row["compiler_readiness_compute_events"] for row in learned_rows
            ),
            "joint_version_space_selection_compute_events": sum(
                model["version_space_selection_compute_events"] for model in models
            ),
            "target_labels": 0,
            "target_execution_steps": 0,
            "target_planning_compute": 0,
            "all_axes_separate": True,
        },
        "registered_gate": {
            "required_source_member_count": config["required_source_member_count"],
            "actual_source_member_count": len(public_members),
            "minimum_compiled_model_count": config["minimum_compiled_model_count"],
            "actual_compiled_model_count": len(models),
            "minimum_compiled_source_member_count": config[
                "minimum_compiled_source_member_count"
            ],
            "actual_compiled_source_member_count": compiled_member_count,
            "source_certificate_discipline_clean": source_clean,
            "every_source_member_retained_exactly_once": partition[
                "every_source_member_retained_exactly_once"
            ],
            "every_compilation_eligible_group_compiled": every_eligible_compiled,
            "every_compiled_model_uses_contextual_ordinal_operator": every_model_contextual,
            "every_compiled_model_retains_all_batch_exact_residuals": every_model_retains_all,
            "fresh_target_outcome_count": 0,
            "passed": passed,
        },
        "v83_failed_predecessor_preserved": True,
        "all_preregistered_source_seeds_executed_without_selection": True,
        "contextual_action_supports_derived_from_catalogue_without_outcomes": True,
        "all_terminal_and_residual_candidates_validated_before_compilation": True,
        "residual_uncertainty_retained_for_robust_planning": True,
        "target_execution_performed": False,
        "producer_free_verification_present": False,
        "complete_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v84(
            domains.CONSTRUCTION_K7_CONTEXTUAL_ORDINAL_CAMPAIGN_V84_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_contextual_ordinal_source_campaign_document_v84",)
