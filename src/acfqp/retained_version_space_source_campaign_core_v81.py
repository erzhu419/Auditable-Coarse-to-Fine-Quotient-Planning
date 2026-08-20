"""V81 source Gate: structural routing plus joint version-space retention."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v81 as domains
from acfqp import structurally_routed_source_campaign_core_v80 as v80
from acfqp.generic_joint_successor_version_space_planner_v42 import (
    GenericJointSuccessorVersionSpacePlannerV42Error,
)
from acfqp.generic_structural_source_partition_v50 import (
    partition_canonical_source_evidence_v50,
)
from acfqp.generic_version_space_retaining_acquisition_v51 import (
    run_relation_covering_version_space_retaining_acquisition_v51,
)
from acfqp.generic_version_space_retaining_model_compiler_v51 import (
    GenericVersionSpaceRetainingModelCompilerV51Error,
    compile_version_space_retaining_model_v51,
)


class RetainedVersionSpaceSourceCampaignCoreV81Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise RetainedVersionSpaceSourceCampaignCoreV81Error(message)


def _member(args: tuple[Any, ...]) -> dict[str, Any]:
    inherited = v80._member(args)  # noqa: SLF001
    candidate = inherited.pop("partial_candidate")
    inherited.pop("member_id")
    inherited["schema"] = "acfqp.retained_version_space_source_member.v81"
    member_id = domains.extension_content_id_v81(
        domains.CONSTRUCTION_K7_RETAINED_SPACE_MEMBER_V81_DOMAIN,
        inherited,
    )
    return {**inherited, "member_id": member_id, "partial_candidate": candidate}


def build_retained_version_space_source_campaign_document_v81(
    config: Mapping[str, Any],
    preregistration_id: str,
    v80_failed_campaign_id: str,
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
        _fail("V81 source member count changed")

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
    candidate_by_member = {row["member_id"]: row["partial_candidate"] for row in members}
    group_results = []
    for structural_group in partition["structural_groups"]:
        evidence = structural_group["source_evidence"]
        acquisition = run_relation_covering_version_space_retaining_acquisition_v51(
            evidence,
            role_free_template_library=template_library,
            maximum_exact_instantiations=config[
                "maximum_terminal_program_candidates_to_try"
            ],
            confidence_denominator=config["prequential_confidence_denominator"],
        )
        learned = acquisition["version_space_retaining_acquisition"]
        model = None
        reason = None
        status = "GROUP_ACQUISITION_ABSTAINED_NONCERTIFICATE"
        if learned["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED":
            try:
                model = compile_version_space_retaining_model_v51(
                    candidate_by_member[structural_group["source_member_ids"][0]],
                    evidence,
                    acquisition,
                )
            except (
                GenericVersionSpaceRetainingModelCompilerV51Error,
                GenericJointSuccessorVersionSpacePlannerV42Error,
            ) as error:
                status = "GROUP_MODEL_COMPILATION_ABSTAINED_NONCERTIFICATE"
                reason = str(error)
            else:
                status = "GROUP_MODEL_COMPILED_NO_TARGET_EXECUTION"
        group_results.append(
            {
                "structural_signature_id": structural_group[
                    "structural_signature_id"
                ],
                "source_member_ids": structural_group["source_member_ids"],
                "source_member_count": structural_group["source_member_count"],
                "relation_covering_version_space_retaining_acquisition": acquisition,
                "reusable_joint_successor_version_space_model": model,
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
    every_group_compiled = all(
        row["reusable_joint_successor_version_space_model"] is not None
        for row in group_results
    )
    every_model_retains_all = every_group_compiled and all(
        row["reusable_joint_successor_version_space_model"][
            "every_batch_exact_residual_expression_retained"
        ]
        is True
        for row in group_results
    )
    passed = (
        len(public_members) == config["required_source_member_count"]
        and source_clean
        and partition["every_source_member_retained_exactly_once"] is True
        and every_group_compiled
        and every_model_retains_all
    )
    attempts = [
        attempt
        for group in group_results
        for attempt in group["relation_covering_version_space_retaining_acquisition"][
            "version_space_retaining_acquisition"
        ]["proposal_attempts"]
    ]
    learned_rows = [
        group["relation_covering_version_space_retaining_acquisition"][
            "version_space_retaining_acquisition"
        ]
        for group in group_results
    ]
    models = [
        group["reusable_joint_successor_version_space_model"]
        for group in group_results
        if group["reusable_joint_successor_version_space_model"] is not None
    ]
    payload = {
        "schema": "acfqp.retained_version_space_source_campaign.v81",
        "preregistration_id": preregistration_id,
        "v80_failed_campaign_id": v80_failed_campaign_id,
        "source_members": public_members,
        "structural_source_partition": partition,
        "structural_group_results": group_results,
        "acquisition_diagnostics": {
            "proposal_attempt_count": len(attempts),
            "semantic_class_coverage_attempt_count": sum(
                row["semantic_class_coverage_complete"] is True for row in attempts
            ),
            "observed_successor_training_calibrated_attempt_count": sum(
                row.get("training_calibrated") is True for row in attempts
            ),
            "acquisition_eligible_attempt_count": sum(
                row["training_calibrated_after_all_acquisition_guards"] is True
                for row in attempts
            ),
            "residual_successor_consensus_used_as_acquisition_gate": False,
        },
        "retained_model_diagnostics": {
            "compiled_model_count": len(models),
            "residual_coordinate_count": sum(
                len(model["residual_version_spaces"]) for model in models
            ),
            "retained_residual_expression_count": sum(
                row["batch_exact_candidate_count"]
                for model in models
                for row in model["residual_version_spaces"]
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
            "source_execution_steps": sum(
                row["execution_steps"] for row in source_episodes
            ),
            "source_partial_planning_compute_events": sum(
                row["partial_planning_compute_events"] for row in source_episodes
            ),
            "source_relational_planning_compute_events": sum(
                row["relational_abstract_support_branch_evaluations"]
                for row in source_episodes
            ),
            "partition_projection_rows": sum(
                len(group["source_evidence"]["raw_transition_rows"])
                for group in partition["structural_groups"]
            ),
            "terminal_candidate_derivation_compute_events": sum(
                row["terminal_candidate_derivation_compute_events"]
                for row in learned_rows
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
            "source_certificate_discipline_clean": source_clean,
            "every_source_member_retained_exactly_once": partition[
                "every_source_member_retained_exactly_once"
            ],
            "structural_group_count": partition["structural_group_count"],
            "every_structural_group_model_compiled": every_group_compiled,
            "every_compiled_model_retains_all_batch_exact_residuals": (
                every_model_retains_all
            ),
            "fresh_target_outcome_count": 0,
            "passed": passed,
        },
        "v80_failed_predecessor_preserved": True,
        "residual_successor_consensus_not_used_as_acquisition_gate": True,
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
        "campaign_id": domains.extension_content_id_v81(
            domains.CONSTRUCTION_K7_RETAINED_SPACE_CAMPAIGN_V81_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_retained_version_space_source_campaign_document_v81",)
