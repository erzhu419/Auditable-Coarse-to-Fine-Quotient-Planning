"""Fresh V71 factorial sample-tax campaign over role-free world models."""

from __future__ import annotations

import copy
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v71 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_prequential_role_free_acquisition_v37 import (
    acquire_prequential_role_free_terminal_program_v37,
)
from acfqp.generic_role_free_acquisition_operator_v36 import (
    schedule_role_free_acquisition_queries_v36,
)
from acfqp.generic_role_free_relational_template_v33 import (
    GenericRoleFreeRelationalTemplateV33Error,
    instantiate_role_free_relational_template_v33,
)
from acfqp.generic_source_complete_relational_world_model_v31 import (
    run_source_complete_relational_world_model_episode_v31,
)


class RoleFreePrequentialCampaignCoreV71Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise RoleFreePrequentialCampaignCoreV71Error(message)


def _ordered(
    evidence: Mapping[str, Any], schedule: Mapping[str, Any]
) -> dict[str, Any]:
    result = copy.deepcopy(evidence)
    result["raw_transition_rows"] = schedule["scheduled_raw_transition_rows"]
    return result


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
        colors.append("V71_OOD_DUPLICATE_STATUS_ROLE")
    result["unknown_residual_target_columns"].append(new_canonical)
    result["unknown_residual_target_columns"].sort()
    for row in result["raw_transition_rows"]:
        row["pre_vector"].append(row["pre_vector"][raw_status])
        row["post_vector"].append(row["post_vector"][raw_status])
    return result


def _arm(
    ordered_evidence: Mapping[str, Any],
    *,
    library: Mapping[str, Any] | None,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    return acquire_prequential_role_free_terminal_program_v37(
        ordered_evidence,
        role_free_template_library=library,
        maximum_exact_instantiations=config[
            "maximum_terminal_program_candidates_to_try"
        ],
        confidence_denominator=config["prequential_confidence_denominator"],
    )


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
    prior_schedule = schedule_role_free_acquisition_queries_v36(
        target_source, role_free_template_library=template_library
    )
    strict_schedule = schedule_role_free_acquisition_queries_v36(
        target_source, role_free_template_library=None
    )
    prior_ordered = _ordered(target_source, prior_schedule)
    strict_ordered = _ordered(target_source, strict_schedule)
    arms = {
        "JOINT_SCHEDULE_AND_PROGRAM_PRIOR": _arm(
            prior_ordered, library=template_library, config=config
        ),
        "SCHEDULE_PRIOR_ONLY": _arm(
            prior_ordered, library=None, config=config
        ),
        "PROGRAM_PRIOR_ONLY": _arm(
            strict_ordered, library=template_library, config=config
        ),
        "STRICT_NO_PRIOR": _arm(strict_ordered, library=None, config=config),
    }
    if (
        arms["JOINT_SCHEDULE_AND_PROGRAM_PRIOR"][
            "witness_blind_query_order_sha256"
        ]
        != arms["SCHEDULE_PRIOR_ONLY"]["witness_blind_query_order_sha256"]
        or arms["PROGRAM_PRIOR_ONLY"]["witness_blind_query_order_sha256"]
        != arms["STRICT_NO_PRIOR"]["witness_blind_query_order_sha256"]
        or prior_schedule["terminal_acceptance_label_accessed"] is not False
        or strict_schedule["terminal_acceptance_label_accessed"] is not False
    ):
        _fail("V71 factorial schedule or outcome-blind boundary changed")

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
            _fail("V71 OOD schema received a role-free program")
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
        _fail("V71 source-generation safety boundary changed")
    payload = {
        "schema": "acfqp.role_free_prequential_occurrence.v71",
        "family": family,
        "seed": seed,
        "common_partial_acquisition_id": partial["document"]["acquisition_id"],
        "common_partial_ground_support_labels": partial["document"][
            "ground_support_labels"
        ],
        "target_source_complete_episode": envelope,
        "retained_target_source": target_source,
        "prior_query_schedule": prior_schedule,
        "strict_query_schedule": strict_schedule,
        "factorial_acquisition_arms": arms,
        "retained_incompatible_schema_ood_source": ood_source,
        "incompatible_schema_ood_control": ood_result,
        "same_target_query_pool_in_all_four_arms": True,
        "same_v37_stop_engine_in_all_four_arms": True,
        "factorial_switches": ["OUTCOME_BLIND_SCHEDULER", "PROGRAM_CODE_PRIOR"],
        "retrospective_counterfactual_acquisition_only": True,
        "query_local_overlay_only_safety_authority": True,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v71(
            domains.CONSTRUCTION_K7_ROLE_FREE_PREQUENTIAL_OCCURRENCE_V71_DOMAIN,
            payload,
        ),
    }


def _consumed(acquisition: Mapping[str, Any]) -> int:
    stopped = acquisition.get("stopped_physical_ground_support_labels")
    full = acquisition.get("full_query_stream_ground_support_labels")
    if stopped is not None:
        if type(stopped) is not int:
            _fail("V71 stop label changed")
        return stopped
    if type(full) is not int:
        _fail("V71 full label count changed")
    return full


def _heldout(acquisition: Mapping[str, Any]) -> int:
    value = acquisition.get("heldout_ground_query_count")
    if type(value) is not int:
        _fail("V71 held-out label count changed")
    return value


def _constructor_compute(acquisition: Mapping[str, Any]) -> int:
    total = 0
    for row in acquisition.get("proposal_attempts", []):
        value = row.get("candidate_constructor_compute", 0)
        if type(value) is not int:
            _fail("V71 constructor compute changed")
        total += value
    return total


def build_role_free_prequential_campaign_document_v71(
    config: Mapping[str, Any],
    preregistration_id: str,
    v70_campaign_id: str,
    v70_verification_id: str,
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
        _fail("V71 occurrence inventory changed")

    names = (
        "JOINT_SCHEDULE_AND_PROGRAM_PRIOR",
        "SCHEDULE_PRIOR_ONLY",
        "PROGRAM_PRIOR_ONLY",
        "STRICT_NO_PRIOR",
    )
    summaries = {}
    for name in names:
        arms = [row["factorial_acquisition_arms"][name] for row in occurrences]
        summaries[name] = {
            "heldout_validated_occurrence_count": sum(
                row["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
                for row in arms
            ),
            "heldout_failed_noncertificate_occurrence_count": sum(
                row["status"] == "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE"
                for row in arms
            ),
            "abstained_occurrence_count": sum(row["status"].startswith("ABSTAINED") for row in arms),
            "counterfactual_acquisition_consumed_labels": sum(
                _consumed(row) for row in arms
            ),
            "post_stop_heldout_audit_labels": sum(_heldout(row) for row in arms),
            "proposal_constructor_compute_events": sum(
                _constructor_compute(row) for row in arms
            ),
            "retired_failed_proposal_count": sum(
                row["retired_failed_proposal_count"] for row in arms
            ),
        }
    jointly_comparable = [
        row
        for row in occurrences
        if row["factorial_acquisition_arms"]["JOINT_SCHEDULE_AND_PROGRAM_PRIOR"][
            "status"
        ]
        == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
        and row["factorial_acquisition_arms"]["STRICT_NO_PRIOR"]["status"]
        == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
    ]
    joint_labels = sum(
        _consumed(
            row["factorial_acquisition_arms"][
                "JOINT_SCHEDULE_AND_PROGRAM_PRIOR"
            ]
        )
        for row in jointly_comparable
    )
    strict_labels = sum(
        _consumed(row["factorial_acquisition_arms"]["STRICT_NO_PRIOR"])
        for row in jointly_comparable
    )
    ood_rejections = sum(
        row["incompatible_schema_ood_control"]["status"]
        == "INCOMPATIBLE_SCHEMA_REJECTED"
        for row in occurrences
    )
    outcome_blind = all(
        row["prior_query_schedule"]["outcome_witness_used_for_scheduling"]
        is not True
        if "outcome_witness_used_for_scheduling" in row["prior_query_schedule"]
        else row["prior_query_schedule"]["terminal_acceptance_label_accessed"] is False
        for row in occurrences
    ) and all(
        row["prior_query_schedule"]["terminal_acceptance_label_accessed"] is False
        and row["strict_query_schedule"]["terminal_acceptance_label_accessed"] is False
        for row in occurrences
    )
    gate_passed = (
        summaries["JOINT_SCHEDULE_AND_PROGRAM_PRIOR"][
            "heldout_validated_occurrence_count"
        ]
        > 0
        and summaries["STRICT_NO_PRIOR"]["heldout_validated_occurrence_count"]
        > 0
        and ood_rejections == len(occurrences)
        and outcome_blind
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
            row["relational_abstract_support_branch_evaluations"]
            for row in episodes
        ),
        "prior_schedule_score_evaluations": sum(
            row["prior_query_schedule"]["outcome_blind_score_evaluation_count"]
            for row in occurrences
        ),
        "strict_schedule_score_evaluations": sum(
            row["strict_query_schedule"]["outcome_blind_score_evaluation_count"]
            for row in occurrences
        ),
        "factorial_arm_accounting": summaries,
        "all_axes_separate": True,
        "counterfactual_acquisition_labels_not_subtracted_from_actual_source_generation": True,
    }
    sample_tax = {
        "jointly_heldout_validated_occurrence_count": len(jointly_comparable),
        "joint_prior_consumed_labels_on_comparable_occurrences": joint_labels,
        "strict_consumed_labels_on_comparable_occurrences": strict_labels,
        "joint_prior_minus_strict_labels": joint_labels - strict_labels,
        "fresh_joint_prior_label_reduction_observed": (
            bool(jointly_comparable) and joint_labels < strict_labels
        ),
        "factorial_attribution_available": True,
        "online_actual_sample_reduction_claimed": False,
        "economics_claimed": False,
    }
    payload = {
        "schema": "acfqp.role_free_prequential_campaign.v71",
        "preregistration_id": preregistration_id,
        "v70_campaign_id": v70_campaign_id,
        "v70_verification_id": v70_verification_id,
        "template_library_artifact_id": template_library_artifact_id,
        "occurrences": occurrences,
        "accounting": accounting,
        "sample_tax_comparison": sample_tax,
        "registered_prequential_gate": {
            "joint_prior_heldout_validated_occurrence_count": summaries[
                "JOINT_SCHEDULE_AND_PROGRAM_PRIOR"
            ]["heldout_validated_occurrence_count"],
            "strict_heldout_validated_occurrence_count": summaries[
                "STRICT_NO_PRIOR"
            ]["heldout_validated_occurrence_count"],
            "incompatible_schema_ood_rejection_count": ood_rejections,
            "required_ood_rejection_count": len(occurrences),
            "all_schedules_outcome_blind": outcome_blind,
            "sample_reduction_required": False,
            "passed": gate_passed,
        },
        "same_target_query_pool_in_all_four_arms": True,
        "same_v37_stop_engine_in_all_four_arms": True,
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
    document = {
        **payload,
        "campaign_id": domains.extension_content_id_v71(
            domains.CONSTRUCTION_K7_ROLE_FREE_PREQUENTIAL_CAMPAIGN_V71_DOMAIN,
            payload,
        ),
    }
    if not gate_passed:
        _fail(
            "V71 registered Gate failed: "
            f"joint={summaries['JOINT_SCHEDULE_AND_PROGRAM_PRIOR']['heldout_validated_occurrence_count']} "
            f"strict={summaries['STRICT_NO_PRIOR']['heldout_validated_occurrence_count']} "
            f"ood={ood_rejections} failed_campaign_id={document['campaign_id']}"
        )
    return document


__all__ = (
    "RoleFreePrequentialCampaignCoreV71Error",
    "build_role_free_prequential_campaign_document_v71",
)
