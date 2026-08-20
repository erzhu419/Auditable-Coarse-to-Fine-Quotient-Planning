"""Fresh-target Gate for a frozen V85r1 projected-disagreement world model."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v86 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_projected_disagreement_certificate_planner_v57 import (
    GenericProjectedDisagreementCertificatePlannerV57Error,
    run_matched_projected_disagreement_ablation_v57,
)
from acfqp.generic_projected_disagreement_planner_v56 import (
    plan_projected_disagreement_model_v56,
)


class ProjectedDisagreementTargetCampaignCoreV86Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ProjectedDisagreementTargetCampaignCoreV86Error(message)


def _compatible(model: Mapping[str, Any], candidate: PartialFactorCandidateV15) -> bool:
    target = candidate.public_document
    source_layout = model.get("source_layout")
    target_layout = target.get("layout")
    return (
        type(source_layout) is dict
        and type(target_layout) is dict
        and target.get("state_width") == model.get("state_width")
        and target.get("action_field_width") == model.get("action_field_width")
        and target.get("unknown_residual_target_columns")
        == model.get("unknown_residual_target_columns")
        and target.get("compiled_factor_assignments")
        == model.get("known_partial_factor_assignments")
        and target_layout.get("state_structural_colors")
        == source_layout.get("state_structural_colors")
        and target_layout.get("action_structural_colors")
        == source_layout.get("action_structural_colors")
    )


def _ood_control(
    model: Mapping[str, Any],
    candidate: PartialFactorCandidateV15,
    adapter: Any,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    foreign_document = copy.deepcopy(candidate.public_document)
    foreign_document["state_width"] += 1
    foreign_document["unknown_residual_target_columns"] = sorted(
        [
            *foreign_document["unknown_residual_target_columns"],
            foreign_document["state_width"] - 1,
        ]
    )
    foreign_document["layout"]["state_canonical_to_raw"].append(
        foreign_document["state_width"] - 1
    )
    foreign_document["layout"]["state_structural_colors"].append(
        "V86_STRICT_INCOMPATIBLE_EXTRA_COORDINATE"
    )
    foreign = PartialFactorCandidateV15(
        foreign_document,
        candidate.layout,
        candidate.assignments,
        candidate.issuance_rows,
    )
    try:
        plan_projected_disagreement_model_v56(
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
    except Exception as error:
        if not error.__class__.__module__.startswith("acfqp.generic_"):
            raise
        return {
            "status": "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_ABSTRACT_SEARCH",
            "reason": str(error),
            "ground_transition_accessed": False,
        }
    _fail("V86 incompatible schema received a model plan")


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    seed, model, factor_library, config = args
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        config["target_family"], seed, config
    )
    partial = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    candidate = partial["candidate"]
    compatible = _compatible(model, candidate)
    ablation = None
    ood = None
    status = "TARGET_STRUCTURALLY_INCOMPATIBLE_NO_TRANSFER_NO_EPISODE"
    reason = None
    if compatible:
        try:
            ablation = run_matched_projected_disagreement_ablation_v57(
                adapter,
                candidate,
                partial["rows"],
                model,
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
        except GenericProjectedDisagreementCertificatePlannerV57Error as error:
            status = "TARGET_MATCHED_EPISODE_FAILED_NONCERTIFICATE"
            reason = str(error)
        else:
            status = "TARGET_MATCHED_EPISODES_COMPLETED"
            ood = _ood_control(model, candidate, adapter, config)
    payload = {
        "schema": "acfqp.projected_disagreement_target_occurrence.v86",
        "family": adapter.family,
        "target_seed": seed,
        "target_episode_index": config["target_episode_index"],
        "source_model_id": model["projected_disagreement_successor_model_id"],
        "target_common_partial_acquisition": partial["document"],
        "target_common_partial_ground_support_labels": partial["document"][
            "ground_support_labels"
        ],
        "target_structurally_compatible": compatible,
        "matched_ablation": ablation,
        "incompatible_schema_ood_control": ood,
        "status": status,
        "failure_reason": reason,
        "model_frozen_before_target_occurrence": True,
        "target_outcomes_used_to_select_or_refit_model": False,
        "certificate_failure_only_local_ground_distinctions": (
            ablation is None
            or ablation["all_ground_queries_followed_failed_certificates"] is True
        ),
        "query_local_exact_overlay_only_safety_authority": True,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v86(
            domains.CONSTRUCTION_K7_PROJECTED_TARGET_OCCURRENCE_V86_DOMAIN,
            payload,
        ),
    }


def build_projected_disagreement_target_campaign_document_v86(
    config: Mapping[str, Any],
    preregistration_id: str,
    model_artifact_id: str,
    v85r1_campaign_id: str,
    v85r1_verification_id: str,
    model: Mapping[str, Any],
    factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    args = [
        (seed, model, factor_library, config)
        for seed in config["target_seeds"]
    ]
    with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
        occurrences = list(executor.map(_target, args))
    if len(occurrences) != config["required_target_occurrence_count"]:
        _fail("V86 target occurrence count changed")
    compatible = [row for row in occurrences if row["target_structurally_compatible"]]
    completed = [
        row for row in compatible if row["status"] == "TARGET_MATCHED_EPISODES_COMPLETED"
    ]
    ablations = [row["matched_ablation"] for row in completed]
    certificate_clean = all(
        ablation["all_ground_queries_followed_failed_certificates"] is True
        and ablation["query_local_exact_overlay_exclusively_used_for_safety"] is True
        for ablation in ablations
    )
    derived_episodes = [
        ablation["arms"]["PROJECTED_DISAGREEMENT_WORLD_MODEL"]
        for ablation in ablations
    ]
    strict_episodes = [
        ablation["arms"]["STRICT_NO_REUSABLE_MODEL"] for ablation in ablations
    ]
    abstract_used = bool(derived_episodes) and all(
        episode["abstract_plan_success_count"] > 0
        and episode["abstract_model_ordering_accepted_count"] > 0
        for episode in derived_episodes
    )
    ood_clean = bool(completed) and all(
        row["incompatible_schema_ood_control"]["status"]
        == "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_ABSTRACT_SEARCH"
        and row["incompatible_schema_ood_control"]["ground_transition_accessed"]
        is False
        for row in completed
    )
    passed = (
        len(occurrences) == config["required_target_occurrence_count"]
        and len(completed) >= config["minimum_compatible_completed_target_count"]
        and len(completed) == len(compatible)
        and certificate_clean
        and abstract_used
        and ood_clean
    )
    derived_labels = sum(
        episode["target_certificate_local_ground_support_labels"]
        for episode in derived_episodes
    )
    strict_labels = sum(
        episode["target_certificate_local_ground_support_labels"]
        for episode in strict_episodes
    )
    payload = {
        "schema": "acfqp.projected_disagreement_target_campaign.v86",
        "preregistration_id": preregistration_id,
        "model_artifact_id": model_artifact_id,
        "v85r1_campaign_id": v85r1_campaign_id,
        "v85r1_verification_id": v85r1_verification_id,
        "source_model_id": model["projected_disagreement_successor_model_id"],
        "target_occurrences": occurrences,
        "registered_gate": {
            "required_target_occurrence_count": config[
                "required_target_occurrence_count"
            ],
            "actual_target_occurrence_count": len(occurrences),
            "minimum_compatible_completed_target_count": config[
                "minimum_compatible_completed_target_count"
            ],
            "actual_structurally_compatible_target_count": len(compatible),
            "actual_completed_matched_target_count": len(completed),
            "every_compatible_target_completed": len(completed) == len(compatible),
            "certificate_failure_only_ground_discipline_clean": certificate_clean,
            "abstract_world_model_ordering_used_on_every_completed_target": abstract_used,
            "strict_incompatible_schema_no_transfer_verified": ood_clean,
            "passed": passed,
        },
        "sample_tax_measurement": {
            "derived_target_certificate_local_labels": derived_labels,
            "strict_target_certificate_local_labels": strict_labels,
            "derived_minus_strict_target_labels": derived_labels - strict_labels,
            "actual_target_sample_reduction_observed": derived_labels < strict_labels,
            "reduction_required_for_this_transfer_gate": False,
        },
        "accounting": {
            "offline_v85r1_template_source_labels": 515,
            "offline_residual_library_labels": 204,
            "offline_v85r1_source_common_partial_labels": 170,
            "offline_v85r1_source_certificate_local_labels": 318,
            "offline_v85r1_group_query_counts_not_physical_labels": 266,
            "target_common_partial_labels": sum(
                row["target_common_partial_ground_support_labels"]
                for row in occurrences
            ),
            "derived_target_certificate_local_labels": derived_labels,
            "strict_target_certificate_local_labels": strict_labels,
            "derived_target_execution_steps": sum(
                episode["execution_steps"] for episode in derived_episodes
            ),
            "strict_target_execution_steps": sum(
                episode["execution_steps"] for episode in strict_episodes
            ),
            "derived_abstract_planning_compute_events": sum(
                episode["abstract_planning_compute_events"]
                for episode in derived_episodes
            ),
            "strict_abstract_planning_compute_events": sum(
                episode["abstract_planning_compute_events"]
                for episode in strict_episodes
            ),
            "all_axes_separate": True,
        },
        "model_frozen_before_all_target_outcomes": True,
        "target_outcomes_used_to_refit_source_model": False,
        "multi_step_planning_primarily_in_abstract_model_claimed": False,
        "certificate_failure_only_local_ground_recovery_observed": certificate_clean,
        "query_local_exact_overlay_only_safety_authority": True,
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
        "campaign_id": domains.extension_content_id_v86(
            domains.CONSTRUCTION_K7_PROJECTED_TARGET_CAMPAIGN_V86_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_projected_disagreement_target_campaign_document_v86",)
