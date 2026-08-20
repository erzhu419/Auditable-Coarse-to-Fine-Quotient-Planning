"""Fresh V72 campaign for conservative learned successor support.

Both arms receive the same outcome-blind relation-covering query order, the
same finite successor expression grammar, the same version-space guard, and
the same prequential stopping rule.  The only switch is the frozen role-free
terminal-program prior.  Source generation remains the unchanged certified
V31 path; this campaign is retrospective acquisition evidence, not online
authority.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v72 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_learned_successor_support_acquisition_v41 import (
    run_relation_covering_learned_successor_acquisition_v41,
)
from acfqp.generic_role_free_relational_template_v33 import (
    GenericRoleFreeRelationalTemplateV33Error,
    instantiate_role_free_relational_template_v33,
)
from acfqp.generic_source_complete_relational_world_model_v31 import (
    run_source_complete_relational_world_model_episode_v31,
)


class SuccessorVersionSpaceCampaignCoreV72Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise SuccessorVersionSpaceCampaignCoreV72Error(message)


def _ood_evidence(
    evidence: Mapping[str, Any], status_target: int
) -> dict[str, Any]:
    result = copy.deepcopy(evidence)
    layout = result["layout"]
    order = layout["state_canonical_to_raw"]
    raw_status = order[status_target]
    order.append(len(order))
    colors = layout.get("state_structural_colors")
    if type(colors) is list:
        colors.append("V72_OOD_DUPLICATE_STATUS_ROLE")
    result["unknown_residual_target_columns"].append(len(order) - 1)
    result["unknown_residual_target_columns"].sort()
    for row in result["raw_transition_rows"]:
        row["pre_vector"].append(row["pre_vector"][raw_status])
        row["post_vector"].append(row["post_vector"][raw_status])
    return result


def _acquisition(
    evidence: Mapping[str, Any],
    *,
    terminal_library: Mapping[str, Any] | None,
    successor_library: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    return run_relation_covering_learned_successor_acquisition_v41(
        evidence,
        role_free_template_library=terminal_library,
        successor_prior_library=successor_library,
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


def _run_occurrence(args: tuple[Any, ...]) -> dict[str, Any]:
    family, seed, factor_library, residual_library, template_library, config = args
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
    prior = _acquisition(
        target_source,
        terminal_library=template_library,
        successor_library=residual_library,
        config=config,
    )
    strict = _acquisition(
        target_source,
        terminal_library=None,
        successor_library=residual_library,
        config=config,
    )
    prior_schedule = prior["query_schedule"]
    strict_schedule = strict["query_schedule"]
    if (
        prior_schedule != strict_schedule
        or prior_schedule.get("terminal_acceptance_label_accessed") is not False
        or prior.get("outcome_witness_used_for_scheduling_or_unacquired_guard")
        is not False
        or strict.get("outcome_witness_used_for_scheduling_or_unacquired_guard")
        is not False
    ):
        _fail("V72 matched outcome-blind schedule changed")
    exact_program = episode["final_relational_terminal_program"]
    ood_source = _ood_evidence(
        target_source, exact_program["status_target_column"]
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
            _fail("V72 OOD schema received a transferred program")
        ood_result = {
            "status": "INCOMPATIBLE_SCHEMA_REJECTED",
            "instantiation_id": ood["instantiation_id"],
        }
    if (
        envelope["all_v28_source_rows_retained"] is not True
        or episode["success"] is not True
        or episode["all_ground_queries_followed_failed_certificates"] is not True
        or episode["query_local_exact_overlay_exclusively_used_for_safety"]
        is not True
    ):
        _fail("V72 source-generation safety boundary changed")
    payload = {
        "schema": "acfqp.successor_version_space_occurrence.v72",
        "family": family,
        "seed": seed,
        "common_partial_acquisition_id": partial["document"]["acquisition_id"],
        "common_partial_ground_support_labels": partial["document"][
            "ground_support_labels"
        ],
        "target_source_complete_episode": envelope,
        "retained_target_source": target_source,
        "shared_outcome_blind_query_schedule": prior_schedule,
        "acquisition_arms": {
            "ROLE_FREE_FACTOR_PRIOR_ON": prior["learned_successor_acquisition"],
            "STRICT_NO_ROLE_FREE_FACTOR_PRIOR": strict[
                "learned_successor_acquisition"
            ],
        },
        "retained_incompatible_schema_ood_source": ood_source,
        "incompatible_schema_ood_control": ood_result,
        "same_target_query_pool_in_both_arms": True,
        "same_query_schedule_in_both_arms": True,
        "same_v41_version_space_and_stop_engine_in_both_arms": True,
        "only_terminal_program_prior_switched": True,
        "retrospective_counterfactual_acquisition_only": True,
        "query_local_overlay_only_safety_authority": True,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v72(
            domains.CONSTRUCTION_K7_SUCCESSOR_VERSION_SPACE_OCCURRENCE_V72_DOMAIN,
            payload,
        ),
    }


def _consumed(acquisition: Mapping[str, Any]) -> int:
    value = acquisition.get("stopped_physical_ground_support_labels")
    if value is None:
        value = acquisition.get("full_query_stream_ground_support_labels")
    if type(value) is not int:
        _fail("V72 consumed-label accounting changed")
    return value


def _terminal_compute(acquisition: Mapping[str, Any]) -> int:
    total = 0
    for row in acquisition.get("proposal_attempts", []):
        value = row.get("candidate_constructor_compute", 0)
        if type(value) is not int:
            _fail("V72 terminal constructor compute changed")
        total += value
    return total


def build_successor_version_space_campaign_document_v72(
    config: Mapping[str, Any],
    preregistration_id: str,
    v71_campaign_id: str,
    v71_verification_id: str,
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
        _fail("V72 occurrence inventory changed")
    arm_names = (
        "ROLE_FREE_FACTOR_PRIOR_ON",
        "STRICT_NO_ROLE_FREE_FACTOR_PRIOR",
    )
    summaries = {}
    for name in arm_names:
        rows = [row["acquisition_arms"][name] for row in occurrences]
        summaries[name] = {
            "heldout_validated_occurrence_count": sum(
                row["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
                for row in rows
            ),
            "heldout_failed_noncertificate_occurrence_count": sum(
                row["status"]
                == "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE"
                for row in rows
            ),
            "abstained_occurrence_count": sum(
                row["status"].startswith("ABSTAINED") for row in rows
            ),
            "counterfactual_acquisition_consumed_labels": sum(
                _consumed(row) for row in rows
            ),
            "post_stop_heldout_audit_labels": sum(
                row["heldout_ground_query_count"] for row in rows
            ),
            "terminal_constructor_compute_events": sum(
                _terminal_compute(row) for row in rows
            ),
            "successor_model_derivation_compute_events": sum(
                row["successor_model_derivation_compute_events"] for row in rows
            ),
            "retired_failed_proposal_count": sum(
                row["retired_failed_proposal_count"] for row in rows
            ),
        }
    comparable = [
        row
        for row in occurrences
        if all(
            row["acquisition_arms"][name]["status"]
            == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
            for name in arm_names
        )
    ]
    prior_labels = sum(
        _consumed(row["acquisition_arms"][arm_names[0]]) for row in comparable
    )
    strict_labels = sum(
        _consumed(row["acquisition_arms"][arm_names[1]]) for row in comparable
    )
    ood_rejections = sum(
        row["incompatible_schema_ood_control"]["status"]
        == "INCOMPATIBLE_SCHEMA_REJECTED"
        for row in occurrences
    )
    zero_failed = all(
        summaries[name]["heldout_failed_noncertificate_occurrence_count"] == 0
        for name in arm_names
    )
    gate_passed = (
        zero_failed
        and all(
            summaries[name]["heldout_validated_occurrence_count"] > 0
            for name in arm_names
        )
        and bool(comparable)
        and ood_rejections == len(occurrences)
        and all(
            row["shared_outcome_blind_query_schedule"][
                "terminal_acceptance_label_accessed"
            ]
            is False
            for row in occurrences
        )
    )
    episodes = [
        row["target_source_complete_episode"]["predecessor_v30_episode"]
        for row in occurrences
    ]
    accounting = {
        "offline_template_source_labels": offline_template_source_labels,
        "offline_residual_library_labels": config["offline_library_labels"],
        "underlying_target_common_partial_labels": sum(
            row["common_partial_ground_support_labels"] for row in occurrences
        ),
        "underlying_target_certificate_local_labels": sum(
            row["local_ground_support_labels"] for row in episodes
        ),
        "underlying_target_execution_steps": sum(
            row["execution_steps"] for row in episodes
        ),
        "underlying_target_partial_planning_compute_events": sum(
            row["partial_planning_compute_events"] for row in episodes
        ),
        "underlying_target_relational_planning_compute_events": sum(
            row["relational_abstract_support_branch_evaluations"] for row in episodes
        ),
        "shared_schedule_score_evaluations": sum(
            row["shared_outcome_blind_query_schedule"][
                "outcome_blind_score_evaluation_count"
            ]
            for row in occurrences
        ),
        "arm_accounting": summaries,
        "all_axes_separate": True,
        "counterfactual_acquisition_labels_not_subtracted_from_actual_source_generation": True,
    }
    sample_tax = {
        "jointly_heldout_validated_occurrence_count": len(comparable),
        "prior_consumed_labels_on_comparable_occurrences": prior_labels,
        "strict_consumed_labels_on_comparable_occurrences": strict_labels,
        "prior_minus_strict_labels": prior_labels - strict_labels,
        "fresh_prior_label_reduction_observed": bool(comparable)
        and prior_labels < strict_labels,
        "sample_reduction_required_by_registered_gate": False,
        "online_actual_sample_reduction_claimed": False,
        "economics_claimed": False,
    }
    payload = {
        "schema": "acfqp.successor_version_space_campaign.v72",
        "preregistration_id": preregistration_id,
        "v71_campaign_id": v71_campaign_id,
        "v71_verification_id": v71_verification_id,
        "template_library_artifact_id": template_library_artifact_id,
        "occurrences": occurrences,
        "accounting": accounting,
        "sample_tax_comparison": sample_tax,
        "registered_gate": {
            "zero_heldout_failed_proposals_in_both_arms": zero_failed,
            "prior_heldout_validated_occurrence_count": summaries[arm_names[0]][
                "heldout_validated_occurrence_count"
            ],
            "strict_heldout_validated_occurrence_count": summaries[arm_names[1]][
                "heldout_validated_occurrence_count"
            ],
            "jointly_comparable_occurrence_count": len(comparable),
            "incompatible_schema_ood_rejection_count": ood_rejections,
            "required_ood_rejection_count": len(occurrences),
            "sample_reduction_required": False,
            "passed": gate_passed,
        },
        "same_target_query_pool_in_both_arms": True,
        "same_query_schedule_in_both_arms": True,
        "same_v41_version_space_and_stop_engine_in_both_arms": True,
        "heldout_rows_accessed_before_stop": False,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "producer_free_verification_present": False,
        "online_adaptive_acquisition_integrated": False,
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
        "campaign_id": domains.extension_content_id_v72(
            domains.CONSTRUCTION_K7_SUCCESSOR_VERSION_SPACE_CAMPAIGN_V72_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "SuccessorVersionSpaceCampaignCoreV72Error",
    "build_successor_version_space_campaign_document_v72",
)
