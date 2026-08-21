"""V91r2 source Gate without the irrelevant strict complete-model arm."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v91r2 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as v59
from acfqp.generic_joint_successor_version_space_planner_v42 import (
    GenericJointSuccessorVersionSpacePlannerV42Error,
)
from acfqp.generic_occurrence_balanced_compiler_ready_acquisition_v66 import (
    run_occurrence_balanced_compiler_ready_acquisition_v66,
)
from acfqp.generic_occurrence_balanced_model_compiler_v66 import (
    GenericOccurrenceBalancedModelCompilerV66Error,
    compile_occurrence_balanced_model_v66,
)
from acfqp.generic_prior_only_partial_acquisition_v67 import (
    acquire_prior_only_partial_candidate_v67,
)
from acfqp.generic_reference_aligned_source_pool_v65 import (
    pool_reference_aligned_source_evidence_v65,
)
from acfqp.generic_source_complete_relational_world_model_v31 import (
    run_source_complete_relational_world_model_episode_v31,
)


class PriorOnlyOccurrenceSourceCampaignCoreV91R2Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise PriorOnlyOccurrenceSourceCampaignCoreV91R2Error(message)


def _member(args: tuple[Any, ...]) -> dict[str, Any]:
    family, seed, _factor_library, residual_library, config = args
    adapter = v59.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        family, seed, config
    )
    partial = acquire_prior_only_partial_candidate_v67(
        adapter,
        maximum_ground_support_labels=config[
            "source_partial_acquisition_maximum_ground_labels"
        ],
        global_alpha_denominator=config["global_alpha_denominator"],
        minimum_factor_assignment_count=config["minimum_reusable_factor_count"],
        layout_domain=config["generic_domains"]["layout"],
        acquisition_domain=(
            domains.CONSTRUCTION_K7_PRIOR_ONLY_OCCURRENCE_SOURCE_PARTIAL_ACQUISITION_V91R2_DOMAIN
        ),
        content_id=domains.extension_content_id_v91r2,
    )
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
    payload = {
        "schema": "acfqp.prior_only_occurrence_source_member.v91r2",
        "family": family,
        "source_seed": seed,
        "source_episode_index": config["source_episode_index"],
        "common_partial_acquisition": partial["document"],
        "source_complete_episode": envelope,
        "source_evidence": envelope["terminal_program_source_evidence"],
        "action_catalogue": [row.to_document() for row in adapter.catalogue],
        "strict_no_prior_arm_executed_for_source_member": False,
        "sample_tax_comparison_claimed_for_source_member": False,
        "target_outcome_accessed": False,
        "query_local_overlay_only_safety_authority": True,
    }
    return {
        **payload,
        "member_id": domains.extension_content_id_v91r2(
            domains.CONSTRUCTION_K7_PRIOR_ONLY_OCCURRENCE_SOURCE_MEMBER_V91R2_DOMAIN,
            payload,
        ),
        "partial_candidate": partial["candidate"],
    }


def build_prior_only_occurrence_source_campaign_document_v91r2(
    config: Mapping[str, Any],
    preregistration_id: str,
    failed_v91r1_id: str,
    factor_library: Mapping[str, Any],
    residual_library: Mapping[str, Any],
    template_library: Mapping[str, Any],
    offline_template_source_labels: int,
) -> dict[str, Any]:
    arguments = [
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
        members = list(executor.map(_member, arguments))
    if len(members) != config["required_source_member_count"]:
        _fail("V91r2 source member count changed")
    if any(
        row["common_partial_acquisition"]["strict_no_prior_arm_executed"]
        is not False
        or row["strict_no_prior_arm_executed_for_source_member"] is not False
        for row in members
    ):
        _fail("V91r2 source member reintroduced the irrelevant strict arm")

    aligned_pool = pool_reference_aligned_source_evidence_v65(
        [
            {
                "member_id": row["member_id"],
                "common_partial_acquisition": row["common_partial_acquisition"],
                "source_evidence": row["source_evidence"],
                "action_catalogue": row["action_catalogue"],
            }
            for row in members
        ],
        layout_domain=config["generic_domains"]["layout"],
    )
    evidence = aligned_pool["canonical_source_pool"]
    acquisition = run_occurrence_balanced_compiler_ready_acquisition_v66(
        evidence,
        role_free_template_library=template_library,
        maximum_exact_instantiations=config[
            "maximum_terminal_program_candidates_to_try"
        ],
        confidence_denominator=config["prequential_confidence_denominator"],
    )
    learned = acquisition["compiler_ready_acquisition"]
    model = None
    compilation_reason = None
    status = "PRIOR_ONLY_OCCURRENCE_ACQUISITION_ABSTAINED_NONCERTIFICATE"
    if learned["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED":
        reference = next(
            row
            for row in members
            if row["member_id"] == aligned_pool["reference_member_id"]
        )
        try:
            model = compile_occurrence_balanced_model_v66(
                reference["partial_candidate"], evidence, acquisition
            )
        except (
            GenericOccurrenceBalancedModelCompilerV66Error,
            GenericJointSuccessorVersionSpacePlannerV42Error,
        ) as error:
            status = "PRIOR_ONLY_OCCURRENCE_COMPILATION_ABSTAINED_NONCERTIFICATE"
            compilation_reason = str(error)
        else:
            status = "PRIOR_ONLY_OCCURRENCE_MODEL_COMPILED_NO_TARGET_EXECUTION"

    public_members = [
        {key: value for key, value in row.items() if key != "partial_candidate"}
        for row in members
    ]
    source_episodes = [
        row["source_complete_episode"]["predecessor_v30_episode"]
        for row in public_members
    ]
    source_clean = bool(source_episodes) and all(
        row["success"] is True
        and row["all_ground_queries_followed_failed_certificates"] is True
        and row["query_local_exact_overlay_exclusively_used_for_safety"] is True
        for row in source_episodes
    )
    all_aligned = (
        aligned_pool["source_member_count"] == len(public_members)
        and aligned_pool[
            "every_original_source_evidence_replayed_before_alignment"
        ]
        is True
        and aligned_pool["every_source_member_retained_exactly_once"] is True
    )
    schedule = acquisition["query_schedule"]
    compiled = model is not None
    retained = compiled and model[
        "every_batch_exact_residual_expression_retained"
    ] is True
    multiple = compiled and model[
        "multiple_residual_proposals_jointly_compiled"
    ] is True
    strict_removed = all(
        row["strict_no_prior_arm_executed_for_source_member"] is False
        for row in public_members
    )
    passed = (
        len(public_members) == config["required_source_member_count"]
        and source_clean
        and all_aligned
        and strict_removed
        and schedule["occurrence_signature_bucket_count"] >= 2
        and learned["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
        and compiled
        and retained
        and multiple
    )
    payload = {
        "schema": "acfqp.prior_only_occurrence_source_campaign.v91r2",
        "preregistration_id": preregistration_id,
        "failed_v91r1_id": failed_v91r1_id,
        "source_members": public_members,
        "reference_aligned_source_pool": aligned_pool,
        "occurrence_balanced_compiler_ready_acquisition": acquisition,
        "reusable_joint_successor_version_space_model": model,
        "status": status,
        "model_compilation_reason": compilation_reason,
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
            "alignment_graph_edit_score": sum(
                row["graph_edit_score"]
                for row in aligned_pool["source_alignment_receipts"]
            ),
            "pooled_source_transition_rows": evidence[
                "pooled_raw_transition_row_count"
            ],
            "occurrence_balance_query_groups": schedule["query_count"],
            "occurrence_balance_bucket_count": schedule[
                "occurrence_signature_bucket_count"
            ],
            "group_acquisition_query_groups_consumed": (
                learned["stopped_physical_ground_support_labels"]
                if type(learned["stopped_physical_ground_support_labels"]) is int
                else learned["full_query_stream_ground_support_labels"]
            ),
            "group_acquisition_query_groups_are_not_physical_label_count": True,
            "terminal_candidate_derivation_compute_events": learned[
                "terminal_candidate_derivation_compute_events"
            ],
            "compiler_readiness_compute_events": learned[
                "compiler_readiness_compute_events"
            ],
            "joint_version_space_selection_compute_events": (
                0
                if model is None
                else model["version_space_selection_compute_events"]
            ),
            "target_labels": 0,
            "target_execution_steps": 0,
            "target_planning_compute": 0,
            "all_sample_execution_derivation_and_planning_axes_separate": True,
        },
        "registered_gate": {
            "required_source_member_count": config["required_source_member_count"],
            "actual_source_member_count": len(public_members),
            "source_certificate_discipline_clean": source_clean,
            "every_source_member_replayed_aligned_and_retained": all_aligned,
            "irrelevant_strict_no_prior_source_arm_removed": strict_removed,
            "occurrence_balanced_query_schedule_present": schedule[
                "occurrence_signature_bucket_count"
            ]
            >= 2,
            "compiler_ready_heldout_validated": learned["status"]
            == "PROPOSAL_ISSUED_HELDOUT_VALIDATED",
            "failed_candidate_retirement_count": learned[
                "retired_failed_proposal_count"
            ],
            "joint_successor_model_compiled": compiled,
            "every_batch_exact_residual_expression_retained": retained,
            "multiple_residual_proposals_jointly_compiled": multiple,
            "fresh_target_outcome_count": 0,
            "passed": passed,
        },
        "v91r1_failure_preserved_without_reinterpretation": True,
        "all_preregistered_source_seeds_executed_without_selection": True,
        "strict_no_prior_arm_not_run_or_charged": True,
        "sample_tax_comparison_claimed_in_this_slice": False,
        "target_outcomes_used_for_alignment_or_model_compilation": False,
        "query_local_exact_overlay_only_safety_authority": True,
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
        "campaign_id": domains.extension_content_id_v91r2(
            domains.CONSTRUCTION_K7_PRIOR_ONLY_OCCURRENCE_SOURCE_CAMPAIGN_V91R2_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_prior_only_occurrence_source_campaign_document_v91r2",)
