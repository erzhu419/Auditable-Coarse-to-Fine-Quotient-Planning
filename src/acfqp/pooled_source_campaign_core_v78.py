"""Source-only V78 Gate for canonical cross-occurrence evidence pooling."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v78 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_canonical_source_pool_v48 import (
    pool_canonical_source_evidence_v48,
)
from acfqp.generic_joint_successor_version_space_planner_v42 import (
    GenericJointSuccessorVersionSpacePlannerV42Error,
    compile_joint_successor_version_space_model_v42,
)
from acfqp.generic_learned_successor_support_acquisition_v41 import (
    run_relation_covering_learned_successor_acquisition_v41,
)
from acfqp.generic_source_complete_relational_world_model_v31 import (
    run_source_complete_relational_world_model_episode_v31,
)


class PooledSourceCampaignCoreV78Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise PooledSourceCampaignCoreV78Error(message)


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
        "schema": "acfqp.canonical_pooled_source_member.v78",
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
    member_id = domains.extension_content_id_v78(
        domains.CONSTRUCTION_K7_POOLED_SOURCE_MEMBER_V78_DOMAIN, payload
    )
    return {
        **payload,
        "member_id": member_id,
        "partial_candidate": partial["candidate"],
    }


def build_pooled_source_campaign_document_v78(
    config: Mapping[str, Any],
    preregistration_id: str,
    v77_campaign_id: str,
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
        _fail("V78 source member count changed")

    pool_input = [
        {
            "member_id": row["member_id"],
            "source_evidence": row["source_evidence"],
            "action_catalogue": row["action_catalogue"],
        }
        for row in members
    ]
    pooled = pool_canonical_source_evidence_v48(pool_input)
    acquisition = run_relation_covering_learned_successor_acquisition_v41(
        pooled,
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
    learned = acquisition["learned_successor_acquisition"]
    model = None
    model_reason = None
    status = "POOLED_SOURCE_ACQUISITION_ABSTAINED_NONCERTIFICATE"
    if learned["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED":
        try:
            model = compile_joint_successor_version_space_model_v42(
                members[0]["partial_candidate"], pooled, acquisition
            )
        except GenericJointSuccessorVersionSpacePlannerV42Error as error:
            status = "POOLED_SOURCE_MODEL_COMPILATION_ABSTAINED_NONCERTIFICATE"
            model_reason = str(error)
        else:
            status = "POOLED_SOURCE_MODEL_COMPILED_NO_TARGET_EXECUTION"

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
    passed = (
        len(public_members) == config["required_source_member_count"]
        and source_clean
        and model is not None
        and learned["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
    )
    stopped = learned["stopped_physical_ground_support_labels"]
    payload = {
        "schema": "acfqp.canonical_pooled_source_campaign.v78",
        "preregistration_id": preregistration_id,
        "v77_failed_campaign_id": v77_campaign_id,
        "source_members": public_members,
        "canonical_source_pool": pooled,
        "relation_covering_acquisition": acquisition,
        "reusable_joint_successor_version_space_model": model,
        "pooled_source_status": status,
        "pooled_source_model_compilation_reason": model_reason,
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
            "pooled_acquisition_query_groups_consumed": (
                stopped
                if type(stopped) is int
                else learned["full_query_stream_ground_support_labels"]
            ),
            "pooled_acquisition_query_groups_are_not_physical_label_count": True,
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
            "pool_projection_rows": pooled["pooled_raw_transition_row_count"],
            "successor_derivation_compute_events": learned[
                "successor_model_derivation_compute_events"
            ],
            "target_labels": 0,
            "target_execution_steps": 0,
            "target_planning_compute": 0,
            "all_axes_separate": True,
        },
        "registered_gate": {
            "required_source_member_count": config["required_source_member_count"],
            "actual_source_member_count": len(public_members),
            "source_certificate_discipline_clean": source_clean,
            "pooled_proposal_heldout_validated": learned["status"]
            == "PROPOSAL_ISSUED_HELDOUT_VALIDATED",
            "pooled_model_compiled": model is not None,
            "fresh_target_outcome_count": 0,
            "passed": passed,
        },
        "individual_v76_v77_balanced_abstentions_preserved": True,
        "source_member_outcomes_used_for_pooling": True,
        "fresh_target_outcomes_used_to_fit_or_select_pool": False,
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
        "campaign_id": domains.extension_content_id_v78(
            domains.CONSTRUCTION_K7_POOLED_SOURCE_CAMPAIGN_V78_DOMAIN, payload
        ),
    }


__all__ = ("build_pooled_source_campaign_document_v78",)
