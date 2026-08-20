"""Fresh cross-episode V73 campaign for reusable abstract world models.

For each fresh identity, episode 0 builds the unchanged certificate-local V31
source and the held-out-validated V41 proposal.  If that source can compile a
complete conservative V42 version space, episode 1 runs a matched V43 target
ablation.  Both target arms use the same exact certificate engine; only the
availability of the already-frozen abstract model differs.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v73 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_joint_successor_version_space_planner_v42 import (
    GenericJointSuccessorVersionSpacePlannerV42Error,
    compile_joint_successor_version_space_model_v42,
    plan_joint_successor_version_space_v42,
)
from acfqp.generic_learned_successor_support_acquisition_v41 import (
    run_relation_covering_learned_successor_acquisition_v41,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_reusable_version_space_certificate_planner_v43 import (
    GenericReusableVersionSpaceCertificatePlannerV43Error,
    run_reusable_version_space_certificate_episode_v43,
)
from acfqp.generic_source_complete_relational_world_model_v31 import (
    run_source_complete_relational_world_model_episode_v31,
)


class ReusableVersionSpaceCampaignCoreV73Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ReusableVersionSpaceCampaignCoreV73Error(message)


def _source_acquisition(
    evidence: Mapping[str, Any],
    terminal_library: Mapping[str, Any],
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


def _ood_control(
    model: Mapping[str, Any],
    candidate: PartialFactorCandidateV15,
    adapter: Any,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    foreign_document = copy.deepcopy(candidate.public_document)
    foreign_document["state_width"] += 1
    foreign_document["unknown_residual_target_columns"] = [
        *foreign_document["unknown_residual_target_columns"],
        foreign_document["state_width"] - 1,
    ]
    foreign_document["unknown_residual_target_columns"].sort()
    foreign_document["layout"]["state_canonical_to_raw"].append(
        foreign_document["state_width"] - 1
    )
    foreign_document["layout"]["state_structural_colors"].append(
        "V73_INCOMPATIBLE_EXTRA_COORDINATE"
    )
    foreign = PartialFactorCandidateV15(
        foreign_document,
        candidate.layout,
        candidate.assignments,
        candidate.issuance_rows,
    )
    try:
        plan_joint_successor_version_space_v42(
            model,
            foreign,
            adapter.catalogue,
            (*adapter.encode(adapter.initial()), 0),
            maximum_depth=config["maximum_abstract_depth"],
            maximum_support_branch_evaluations=config[
                "maximum_relational_support_branch_evaluations"
            ],
            support_feasible_beam_width=config[
                "relational_support_feasible_beam_width"
            ],
        )
    except GenericJointSuccessorVersionSpacePlannerV42Error as error:
        return {
            "status": "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_ABSTRACT_SEARCH",
            "reason": str(error),
            "ground_transition_accessed": False,
        }
    _fail("V73 incompatible target schema received a reusable model plan")


def _run_target_arm(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    rows: tuple[Any, ...],
    model: Mapping[str, Any] | None,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        result = run_reusable_version_space_certificate_episode_v43(
            adapter,
            candidate,
            rows,
            reusable_model=model,
            model_source_episode_index=config["source_episode_index"],
            episode_index=config["target_episode_index"],
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
    except GenericReusableVersionSpaceCertificatePlannerV43Error as error:
        return {
            "schema": "acfqp.generic_reusable_version_space_certificate_failure.v43",
            "status": "TARGET_CERTIFICATE_EPISODE_FAILED_NONCERTIFICATE",
            "reason": str(error),
            "reusable_model_present": model is not None,
            "official_execution_allowed": False,
        }
    return result


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
    source_episode = envelope["predecessor_v30_episode"]
    retained = envelope["terminal_program_source_evidence"]
    source = {
        "layout": retained["layout"],
        "unknown_residual_target_columns": retained[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": retained["raw_transition_rows"],
    }
    acquisition = _source_acquisition(
        source, template_library, residual_library, config
    )
    learned = acquisition["learned_successor_acquisition"]
    model = None
    model_status = "SOURCE_ACQUISITION_ABSTAINED_NO_TARGET_EXECUTION"
    compile_reason = None
    if learned["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED":
        try:
            model = compile_joint_successor_version_space_model_v42(
                partial["candidate"], source, acquisition
            )
        except GenericJointSuccessorVersionSpacePlannerV42Error as error:
            model_status = "SOURCE_MODEL_COMPILATION_ABSTAINED_NONCERTIFICATE"
            compile_reason = str(error)
        else:
            model_status = "REUSABLE_MODEL_COMPILED_TARGET_EXECUTION_ATTEMPTED"
    if model is None:
        target_arms = None
        ood = {
            "status": "NOT_RUN_SOURCE_MODEL_UNAVAILABLE",
            "ground_transition_accessed": False,
        }
    else:
        target_arms = {
            "REUSABLE_JOINT_VERSION_SPACE_MODEL": _run_target_arm(
                adapter, partial["candidate"], partial["rows"], model, config
            ),
            "STRICT_NO_REUSABLE_MODEL": _run_target_arm(
                adapter, partial["candidate"], partial["rows"], None, config
            ),
        }
        ood = _ood_control(model, partial["candidate"], adapter, config)
    if (
        envelope["all_v28_source_rows_retained"] is not True
        or source_episode["success"] is not True
        or source_episode["all_ground_queries_followed_failed_certificates"]
        is not True
        or source_episode[
            "query_local_exact_overlay_exclusively_used_for_safety"
        ]
        is not True
    ):
        _fail("V73 source-generation safety boundary changed")
    payload = {
        "schema": "acfqp.reusable_version_space_occurrence.v73",
        "family": family,
        "seed": seed,
        "source_episode_index": config["source_episode_index"],
        "target_episode_index": config["target_episode_index"],
        "common_partial_acquisition_id": partial["document"]["acquisition_id"],
        "common_partial_ground_support_labels": partial["document"][
            "ground_support_labels"
        ],
        "source_complete_episode": envelope,
        "retained_source_evidence": source,
        "source_relation_covering_acquisition": acquisition,
        "source_model_status": model_status,
        "source_model_compilation_reason": compile_reason,
        "reusable_joint_successor_version_space_model": model,
        "target_ablation_arms": target_arms,
        "incompatible_schema_ood_control": ood,
        "source_model_frozen_before_target_episode_execution": model is not None,
        "same_target_adapter_kernel_seed_episode_in_both_arms": model is not None,
        "same_exact_query_local_certificate_engine_in_both_arms": model is not None,
        "only_reusable_model_availability_differs_between_target_arms": model is not None,
        "target_outcomes_used_to_refit_reusable_model": False,
        "query_local_overlay_only_safety_authority": True,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v73(
            domains.CONSTRUCTION_K7_REUSABLE_VERSION_SPACE_OCCURRENCE_V73_DOMAIN,
            payload,
        ),
    }


def build_reusable_version_space_campaign_document_v73(
    config: Mapping[str, Any],
    preregistration_id: str,
    v72r1_campaign_id: str,
    v72r1_verification_id: str,
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
        _fail("V73 occurrence inventory changed")
    compiled = [
        row for row in occurrences
        if row["reusable_joint_successor_version_space_model"] is not None
    ]
    source_failed = sum(
        row["source_relation_covering_acquisition"]["learned_successor_acquisition"][
            "status"
        ]
        == "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE"
        for row in occurrences
    )
    comparable = []
    target_failures = 0
    for row in compiled:
        arms = row["target_ablation_arms"]
        if all(arm.get("success") is True for arm in arms.values()):
            comparable.append(row)
        else:
            target_failures += 1
    derived_labels = sum(
        row["target_ablation_arms"]["REUSABLE_JOINT_VERSION_SPACE_MODEL"][
            "target_certificate_local_ground_support_labels"
        ]
        for row in comparable
    )
    strict_labels = sum(
        row["target_ablation_arms"]["STRICT_NO_REUSABLE_MODEL"][
            "target_certificate_local_ground_support_labels"
        ]
        for row in comparable
    )
    reduction_count = sum(
        row["target_ablation_arms"]["REUSABLE_JOINT_VERSION_SPACE_MODEL"][
            "target_certificate_local_ground_support_labels"
        ]
        < row["target_ablation_arms"]["STRICT_NO_REUSABLE_MODEL"][
            "target_certificate_local_ground_support_labels"
        ]
        for row in comparable
    )
    ood_rejections = sum(
        row["incompatible_schema_ood_control"]["status"]
        == "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_ABSTRACT_SEARCH"
        for row in compiled
    )
    certificate_clean = all(
        arm["all_ground_queries_followed_failed_certificates"] is True
        and arm["query_local_exact_overlay_exclusively_used_for_safety"] is True
        and arm["reusable_abstract_model_used_as_safety_authority"] is False
        for row in comparable
        for arm in row["target_ablation_arms"].values()
    )
    aggregate_reduction = bool(comparable) and derived_labels < strict_labels
    gate_passed = (
        source_failed == 0
        and len(compiled) >= config["minimum_compiled_occurrence_count"]
        and len(comparable) == len(compiled)
        and target_failures == 0
        and ood_rejections == len(compiled)
        and certificate_clean
        and aggregate_reduction
        and reduction_count >= config["minimum_reduced_occurrence_count"]
    )
    source_episodes = [
        row["source_complete_episode"]["predecessor_v30_episode"]
        for row in occurrences
    ]
    accounting = {
        "offline_template_source_labels": offline_template_source_labels,
        "offline_residual_library_labels": config["offline_library_labels"],
        "source_common_partial_labels": sum(
            row["common_partial_ground_support_labels"] for row in occurrences
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
        "source_acquisition_consumed_labels": sum(
            (
                row["source_relation_covering_acquisition"][
                    "learned_successor_acquisition"
                ]["stopped_physical_ground_support_labels"]
                or row["source_relation_covering_acquisition"][
                    "learned_successor_acquisition"
                ]["full_query_stream_ground_support_labels"]
            )
            for row in occurrences
        ),
        "target_derived_certificate_local_labels": derived_labels,
        "target_strict_certificate_local_labels": strict_labels,
        "target_derived_execution_steps": sum(
            row["target_ablation_arms"]["REUSABLE_JOINT_VERSION_SPACE_MODEL"][
                "execution_steps"
            ]
            for row in comparable
        ),
        "target_strict_execution_steps": sum(
            row["target_ablation_arms"]["STRICT_NO_REUSABLE_MODEL"][
                "execution_steps"
            ]
            for row in comparable
        ),
        "target_derived_abstract_planning_compute_events": sum(
            row["target_ablation_arms"]["REUSABLE_JOINT_VERSION_SPACE_MODEL"][
                "abstract_planning_compute_events"
            ]
            for row in comparable
        ),
        "target_strict_abstract_planning_compute_events": 0,
        "all_axes_separate": True,
        "source_labels_not_subtracted_from_target_label_comparison": True,
    }
    sample_tax = {
        "compiled_occurrence_count": len(compiled),
        "matched_successful_target_occurrence_count": len(comparable),
        "target_occurrence_with_strict_reduction_count": reduction_count,
        "derived_target_certificate_local_labels": derived_labels,
        "strict_target_certificate_local_labels": strict_labels,
        "derived_minus_strict_target_labels": derived_labels - strict_labels,
        "fresh_actual_target_sample_reduction_observed": aggregate_reduction,
        "source_acquisition_cost_amortization_evaluated": False,
        "economics_claimed": False,
    }
    payload = {
        "schema": "acfqp.reusable_version_space_campaign.v73",
        "preregistration_id": preregistration_id,
        "v72r1_campaign_id": v72r1_campaign_id,
        "v72r1_verification_id": v72r1_verification_id,
        "template_library_artifact_id": template_library_artifact_id,
        "occurrences": occurrences,
        "accounting": accounting,
        "sample_tax_comparison": sample_tax,
        "registered_gate": {
            "source_heldout_failed_noncertificate_count": source_failed,
            "compiled_occurrence_count": len(compiled),
            "required_minimum_compiled_occurrence_count": config[
                "minimum_compiled_occurrence_count"
            ],
            "matched_successful_target_occurrence_count": len(comparable),
            "target_failure_count": target_failures,
            "incompatible_schema_ood_rejection_count": ood_rejections,
            "required_incompatible_schema_ood_rejection_count": len(compiled),
            "certificate_discipline_clean": certificate_clean,
            "aggregate_actual_target_label_reduction_required": True,
            "aggregate_actual_target_label_reduction_observed": aggregate_reduction,
            "minimum_reduced_occurrence_count": config[
                "minimum_reduced_occurrence_count"
            ],
            "actual_reduced_occurrence_count": reduction_count,
            "passed": gate_passed,
        },
        "same_exact_target_certificate_engine_in_both_arms": True,
        "only_reusable_model_availability_differs_between_target_arms": True,
        "source_model_frozen_before_every_target_episode": True,
        "target_outcomes_used_to_refit_reusable_models": False,
        "all_ground_queries_followed_failed_certificates": certificate_clean,
        "query_local_exact_overlay_exclusively_used_for_safety": certificate_clean,
        "producer_free_verification_present": False,
        "online_adaptive_model_refit_integrated": False,
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
        "campaign_id": domains.extension_content_id_v73(
            domains.CONSTRUCTION_K7_REUSABLE_VERSION_SPACE_CAMPAIGN_V73_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "ReusableVersionSpaceCampaignCoreV73Error",
    "build_reusable_version_space_campaign_document_v73",
)
