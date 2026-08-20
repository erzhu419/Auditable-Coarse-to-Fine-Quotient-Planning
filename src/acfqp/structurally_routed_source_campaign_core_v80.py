"""V80 source Gate with anonymous structural partition before V49 acquisition."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v80 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_joint_successor_version_space_planner_v42 import (
    GenericJointSuccessorVersionSpacePlannerV42Error,
)
from acfqp.generic_source_complete_relational_world_model_v31 import (
    run_source_complete_relational_world_model_episode_v31,
)
from acfqp.generic_structural_source_partition_v50 import (
    partition_canonical_source_evidence_v50,
)
from acfqp.generic_successor_projected_acquisition_v49 import (
    run_relation_covering_successor_projected_acquisition_v49,
)
from acfqp.generic_successor_projected_model_compiler_v49 import (
    GenericSuccessorProjectedModelCompilerV49Error,
    compile_successor_projected_model_v49,
)


class StructurallyRoutedSourceCampaignCoreV80Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise StructurallyRoutedSourceCampaignCoreV80Error(message)


def _member(args: tuple[Any, ...]) -> dict[str, Any]:
    family, seed, factor_library, residual_library, config = args
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        family, seed, config
    )
    partial = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    envelope = run_source_complete_relational_world_model_episode_v31(
        adapter,
        partial["candidate"],
        partial["rows"],
        residual_prior_library=residual_library,
        episode_index=config["source_episode_index"],
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
    evidence = envelope["terminal_program_source_evidence"]
    payload = {
        "schema": "acfqp.structurally_routed_source_member.v80",
        "family": family,
        "source_seed": seed,
        "source_episode_index": config["source_episode_index"],
        "common_partial_acquisition": partial["document"],
        "source_complete_episode": envelope,
        "source_evidence": evidence,
        "action_catalogue": [row.to_document() for row in adapter.catalogue],
        "target_outcome_accessed": False,
        "query_local_overlay_only_safety_authority": True,
    }
    return {
        **payload,
        "member_id": domains.extension_content_id_v80(
            domains.CONSTRUCTION_K7_STRUCTURAL_ROUTE_MEMBER_V80_DOMAIN,
            payload,
        ),
        "partial_candidate": partial["candidate"],
    }


def build_structurally_routed_source_campaign_document_v80(
    config: Mapping[str, Any],
    preregistration_id: str,
    v79_failure_id: str,
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
        _fail("V80 source member count changed")

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
        acquisition = run_relation_covering_successor_projected_acquisition_v49(
            evidence,
            role_free_template_library=template_library,
            successor_prior_library=residual_library,
            maximum_exact_instantiations=config[
                "maximum_terminal_program_candidates_to_try"
            ],
            confidence_denominator=config["prequential_confidence_denominator"],
            successor_confidence_denominator=config[
                "successor_confidence_denominator"
            ],
            maximum_successor_support_states=config[
                "maximum_successor_support_states"
            ],
        )
        learned = acquisition["successor_projected_acquisition"]
        model = None
        reason = None
        status = "GROUP_ACQUISITION_ABSTAINED_NONCERTIFICATE"
        if learned["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED":
            try:
                model = compile_successor_projected_model_v49(
                    candidate_by_member[structural_group["source_member_ids"][0]],
                    evidence,
                    acquisition,
                )
            except (
                GenericSuccessorProjectedModelCompilerV49Error,
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
                "relation_covering_successor_projected_acquisition": acquisition,
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
    passed = (
        len(public_members) == config["required_source_member_count"]
        and source_clean
        and partition["every_source_member_retained_exactly_once"] is True
        and every_group_compiled
    )
    attempts = [
        attempt
        for group in group_results
        for attempt in group["relation_covering_successor_projected_acquisition"][
            "successor_projected_acquisition"
        ]["proposal_attempts"]
    ]
    learned_rows = [
        group["relation_covering_successor_projected_acquisition"][
            "successor_projected_acquisition"
        ]
        for group in group_results
    ]
    payload = {
        "schema": "acfqp.structurally_routed_source_campaign.v80",
        "preregistration_id": preregistration_id,
        "v79_failure_id": v79_failure_id,
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
            "projected_successor_consensus_attempt_count": sum(
                row["learned_successor_guard"].get(
                    "learned_successor_frontier_consensus"
                )
                is True
                for row in attempts
            ),
            "terminal_frontier_evaluated_on_query_prestates": False,
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
            "successor_derivation_compute_events": sum(
                row["successor_model_derivation_compute_events"]
                for row in learned_rows
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
            "fresh_target_outcome_count": 0,
            "passed": passed,
        },
        "v79_failed_predecessor_preserved": True,
        "structural_partition_uses_no_family_or_outcome": True,
        "incompatible_sources_not_forced_into_one_model": True,
        "every_discovered_structural_group_required_to_compile": True,
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
        "campaign_id": domains.extension_content_id_v80(
            domains.CONSTRUCTION_K7_STRUCTURAL_ROUTE_CAMPAIGN_V80_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_structurally_routed_source_campaign_document_v80",)
