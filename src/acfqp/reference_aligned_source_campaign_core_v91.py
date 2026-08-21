"""V91 source-only synthesis after stochastic partial-layout alignment."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping, NoReturn

from acfqp import bounded_multi_source_campaign_core_v82 as v82
from acfqp import construction_k7_domain_registry_extension_v91 as domains
from acfqp.generic_compiler_ready_acquisition_v52 import (
    run_relation_covering_compiler_ready_acquisition_v52,
)
from acfqp.generic_compiler_ready_model_compiler_v52 import (
    GenericCompilerReadyModelCompilerV52Error,
    compile_compiler_ready_model_v52,
)
from acfqp.generic_joint_successor_version_space_planner_v42 import (
    GenericJointSuccessorVersionSpacePlannerV42Error,
)
from acfqp.generic_reference_aligned_source_pool_v65 import (
    pool_reference_aligned_source_evidence_v65,
)


class ReferenceAlignedSourceCampaignCoreV91Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ReferenceAlignedSourceCampaignCoreV91Error(message)


def _member(args: tuple[Any, ...]) -> dict[str, Any]:
    inherited = v82._member(args)  # noqa: SLF001
    candidate = inherited.pop("partial_candidate")
    inherited.pop("member_id")
    inherited["schema"] = "acfqp.reference_aligned_source_member.v91"
    payload = inherited
    return {
        **payload,
        "member_id": domains.extension_content_id_v91(
            domains.CONSTRUCTION_K7_REFERENCE_ALIGNED_MEMBER_V91_DOMAIN,
            payload,
        ),
        "partial_candidate": candidate,
    }


def build_reference_aligned_source_campaign_document_v91(
    config: Mapping[str, Any],
    preregistration_id: str,
    v90_verification_id: str,
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
        _fail("V91 source member count changed")

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
    acquisition = run_relation_covering_compiler_ready_acquisition_v52(
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
    status = "REFERENCE_ALIGNED_ACQUISITION_ABSTAINED_NONCERTIFICATE"
    if learned["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED":
        reference = next(
            row
            for row in members
            if row["member_id"] == aligned_pool["reference_member_id"]
        )
        try:
            model = compile_compiler_ready_model_v52(
                reference["partial_candidate"], evidence, acquisition
            )
        except (
            GenericCompilerReadyModelCompilerV52Error,
            GenericJointSuccessorVersionSpacePlannerV42Error,
        ) as error:
            status = "REFERENCE_ALIGNED_MODEL_COMPILATION_ABSTAINED_NONCERTIFICATE"
            compilation_reason = str(error)
        else:
            status = "REFERENCE_ALIGNED_MODEL_COMPILED_NO_TARGET_EXECUTION"

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
        and aligned_pool["every_original_source_evidence_replayed_before_alignment"]
        is True
        and aligned_pool["every_source_member_retained_exactly_once"] is True
    )
    compiled = model is not None
    retained = compiled and model[
        "every_batch_exact_residual_expression_retained"
    ] is True
    multiple = compiled and model[
        "multiple_residual_proposals_jointly_compiled"
    ] is True
    passed = (
        len(public_members) == config["required_source_member_count"]
        and source_clean
        and all_aligned
        and learned["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
        and compiled
        and retained
        and multiple
    )
    payload = {
        "schema": "acfqp.reference_aligned_source_campaign.v91",
        "preregistration_id": preregistration_id,
        "v90_verification_id": v90_verification_id,
        "source_members": public_members,
        "reference_aligned_source_pool": aligned_pool,
        "relation_covering_compiler_ready_acquisition": acquisition,
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
            "alignment_relation_evaluations": sum(
                row["graph_edit_score"]
                for row in aligned_pool["source_alignment_receipts"]
            ),
            "pooled_source_transition_rows": evidence[
                "pooled_raw_transition_row_count"
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
                0 if model is None else model["version_space_selection_compute_events"]
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
            "finite_observation_color_mismatch_overcome_by_raw_reference_alignment": (
                any(
                    row["graph_edit_score"] > 0
                    for row in aligned_pool["source_alignment_receipts"]
                )
            ),
            "compiler_ready_heldout_validated": learned["status"]
            == "PROPOSAL_ISSUED_HELDOUT_VALIDATED",
            "joint_successor_model_compiled": compiled,
            "every_batch_exact_residual_expression_retained": retained,
            "multiple_residual_proposals_jointly_compiled": multiple,
            "fresh_target_outcome_count": 0,
            "passed": passed,
        },
        "all_preregistered_source_seeds_executed_without_selection": True,
        "source_terminal_acceptance_observations_available_to_alignment": True,
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
        "campaign_id": domains.extension_content_id_v91(
            domains.CONSTRUCTION_K7_REFERENCE_ALIGNED_CAMPAIGN_V91_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_reference_aligned_source_campaign_document_v91",)
