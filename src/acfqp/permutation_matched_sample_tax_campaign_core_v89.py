"""V89 matched sample-tax campaign under outcome-blind action identifiers."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v89 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.coordinate_aligned_target_campaign_core_v87r1 import (
    _ood_control,
    _same_structural_schema_family,
)
from acfqp.generic_action_key_permutation_adapter_v62 import (
    permute_adapter_action_keys_v62,
)
from acfqp.generic_coordinate_aligned_certificate_planner_v60 import (
    run_coordinate_aligned_applicability_ablation_v60,
)
from acfqp.phase3e_ids import canonical_json_bytes


class PermutationMatchedSampleTaxCampaignCoreV89Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise PermutationMatchedSampleTaxCampaignCoreV89Error(message)


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    seed, model, applicability, factor_library, config = args
    original = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        config["target_family"], seed, config
    )
    adapter, permutation = permute_adapter_action_keys_v62(original)
    partial = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    candidate = partial["candidate"]
    rows = partial["rows"]
    raw_rows = [row.to_document() for row in rows]
    raw_catalogue = [row.to_document() for row in adapter.catalogue]
    if (
        canonical_json_bytes(raw_rows)
        != canonical_json_bytes([row.to_document() for row in rows])
        or partial["document"]["raw_transition_count"] != len(raw_rows)
        or permutation["permuted_catalogue_sha256"]
        != hashlib.sha256(canonical_json_bytes(raw_catalogue)).hexdigest()
    ):
        _fail("V89 raw pre-episode witness freeze changed")
    eligible = _same_structural_schema_family(model, applicability, candidate)
    ablation = None
    ood = None
    status = "TARGET_STRUCTURAL_SCHEMA_INCOMPATIBLE_NO_EPISODE"
    reason = None
    if eligible:
        try:
            ablation = run_coordinate_aligned_applicability_ablation_v60(
                adapter,
                candidate,
                rows,
                model,
                applicability,
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
        except Exception as error:
            if not error.__class__.__module__.startswith("acfqp.generic_"):
                raise
            status = "TARGET_ALIGNMENT_OR_EPISODE_FAILED_NONCERTIFICATE"
            reason = str(error)
        else:
            status = "TARGET_PERMUTATION_MATCHED_EPISODES_COMPLETED"
            ood = _ood_control(
                model, applicability, candidate, rows, adapter.catalogue
            )
    alignment = None if ablation is None else ablation["coordinate_alignment"]
    payload = {
        "schema": "acfqp.permutation_matched_sample_tax_occurrence.v89",
        "family": adapter.family,
        "target_seed": seed,
        "target_episode_index": config["target_episode_index"],
        "source_model_id": model["projected_disagreement_successor_model_id"],
        "action_applicability_program_id": applicability[
            "action_applicability_program_id"
        ],
        "v88_campaign_id": config["v88_campaign_id"],
        "v88_verification_id": config["v88_verification_id"],
        "outcome_blind_action_key_permutation": permutation,
        "target_common_partial_acquisition": partial["document"],
        "target_common_partial_ground_support_labels": partial["document"][
            "ground_support_labels"
        ],
        "target_common_partial_raw_transition_rows": raw_rows,
        "target_common_partial_action_catalogue": raw_catalogue,
        "raw_alignment_inputs_and_permutation_frozen_before_target_episode": (
            ablation is not None
        ),
        "target_structural_schema_family_eligible": eligible,
        "coordinate_alignment_id": (
            None if alignment is None else alignment["coordinate_alignment_id"]
        ),
        "coordinate_alignment": alignment,
        "matched_ablation": ablation,
        "incompatible_schema_ood_control": ood,
        "status": status,
        "failure_reason": reason,
        "target_episode_outcomes_used_to_select_permutation_alignment_or_refit_models": False,
        "certificate_failure_only_local_ground_distinctions": (
            ablation is None
            or ablation["all_ground_queries_followed_failed_certificates"] is True
        ),
        "query_local_exact_overlay_only_safety_authority": True,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v89(
            domains.CONSTRUCTION_K7_PERMUTATION_MATCHED_OCCURRENCE_V89_DOMAIN,
            payload,
        ),
    }


def build_permutation_matched_sample_tax_campaign_document_v89(
    config: Mapping[str, Any],
    preregistration_id: str,
    projected_model_artifact_id: str,
    applicability_model_artifact_id: str,
    model: Mapping[str, Any],
    applicability: Mapping[str, Any],
    factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    arguments = [
        (seed, model, applicability, factor_library, config)
        for seed in config["target_seeds"]
    ]
    with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
        occurrences = list(executor.map(_target, arguments))
    eligible = [row for row in occurrences if row["target_structural_schema_family_eligible"]]
    completed = [
        row
        for row in eligible
        if row["status"] == "TARGET_PERMUTATION_MATCHED_EPISODES_COMPLETED"
    ]
    ablations = [row["matched_ablation"] for row in completed]
    alignments = [row["coordinate_alignment"] for row in completed]
    derived = [row["arms"]["APPLICABILITY_CONDITIONED_WORLD_MODEL"] for row in ablations]
    strict = [row["arms"]["STRICT_NO_REUSABLE_MODEL"] for row in ablations]
    paired = list(zip(derived, strict, strict=True))
    raw_embedded = bool(completed) and all(
        row["raw_alignment_inputs_and_permutation_frozen_before_target_episode"] is True
        and len(row["target_common_partial_raw_transition_rows"])
        == row["target_common_partial_acquisition"]["raw_transition_count"]
        and row["coordinate_alignment"]["target_raw_transition_sha256"]
        == row["target_common_partial_acquisition"]["raw_transition_sha256"]
        for row in completed
    )
    permutation_clean = bool(completed) and all(
        row["outcome_blind_action_key_permutation"][
            "transition_outcomes_accessed_to_select_permutation"
        ]
        is False
        and row["outcome_blind_action_key_permutation"][
            "anonymous_descriptor_fields_preserved_exactly"
        ]
        is True
        and sorted(row["outcome_blind_action_key_permutation"]["old_to_new"])
        == list(range(row["outcome_blind_action_key_permutation"]["action_count"]))
        for row in completed
    )
    unique_alignments = bool(alignments) and all(
        row["exact_full_model_projection_count"] == 1 for row in alignments
    )
    certificate_clean = bool(ablations) and all(
        row["all_ground_queries_followed_failed_certificates"] is True
        and row["query_local_exact_overlay_exclusively_used_for_safety"] is True
        for row in ablations
    )
    abstract_clean = bool(derived) and all(
        row["execution_steps"] > 1
        and row["abstract_plan_success_count"] > 0
        and row["abstract_plan_abstention_count"] == 0
        and row["abstract_model_ordering_accepted_count"]
        == row["abstract_plan_success_count"]
        for row in derived
    )
    execution_matched = bool(paired) and all(
        left["action_keys"] == right["action_keys"]
        and left["outcome_tape_sha256"] == right["outcome_tape_sha256"]
        and left["execution_steps"] == right["execution_steps"]
        for left, right in paired
    )
    ood_clean = bool(completed) and all(
        row["incompatible_schema_ood_control"]["status"]
        == "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_ALIGNMENT_OR_SEARCH"
        and row["incompatible_schema_ood_control"][
            "ground_transition_accessed_beyond_registered_partial_prefix"
        ]
        is False
        for row in completed
    )
    derived_labels = sum(row["target_certificate_local_ground_support_labels"] for row in derived)
    strict_labels = sum(row["target_certificate_local_ground_support_labels"] for row in strict)
    reduced_count = sum(
        left["target_certificate_local_ground_support_labels"]
        < right["target_certificate_local_ground_support_labels"]
        for left, right in paired
    )
    no_regressions = bool(paired) and all(
        left["target_certificate_local_ground_support_labels"]
        <= right["target_certificate_local_ground_support_labels"]
        for left, right in paired
    )
    sample_reduced = (
        derived_labels < strict_labels
        and reduced_count >= config["minimum_reduced_target_occurrence_count_v89"]
        and no_regressions
    )
    passed = (
        len(occurrences) == config["required_target_occurrence_count"]
        and len(completed) >= config["minimum_completed_target_count_v89"]
        and len(completed) == len(eligible)
        and raw_embedded
        and permutation_clean
        and unique_alignments
        and certificate_clean
        and abstract_clean
        and execution_matched
        and ood_clean
        and sample_reduced
    )
    payload = {
        "schema": "acfqp.permutation_matched_sample_tax_campaign.v89",
        "preregistration_id": preregistration_id,
        "v87_failed_campaign_id": config["v87_failed_campaign_id"],
        "v87r1_campaign_id": config["v87r1_campaign_id"],
        "v87r1_verification_id": config["v87r1_verification_id"],
        "v88_campaign_id": config["v88_campaign_id"],
        "v88_verification_id": config["v88_verification_id"],
        "projected_model_artifact_id": projected_model_artifact_id,
        "applicability_model_artifact_id": applicability_model_artifact_id,
        "source_model_id": model["projected_disagreement_successor_model_id"],
        "action_applicability_program_id": applicability[
            "action_applicability_program_id"
        ],
        "target_occurrences": occurrences,
        "registered_gate": {
            "required_target_occurrence_count": config["required_target_occurrence_count"],
            "actual_target_occurrence_count": len(occurrences),
            "minimum_completed_target_count": config["minimum_completed_target_count_v89"],
            "actual_completed_target_count": len(completed),
            "every_eligible_target_completed": len(completed) == len(eligible),
            "raw_alignment_inputs_embedded": raw_embedded,
            "outcome_blind_action_key_permutations_clean": permutation_clean,
            "unique_alignment_on_every_completed_target": unique_alignments,
            "certificate_failure_only_ground_discipline_clean": certificate_clean,
            "abstract_model_ordering_clean": abstract_clean,
            "matched_ground_execution_identical": execution_matched,
            "strict_incompatible_schema_no_transfer_verified": ood_clean,
            "minimum_reduced_target_occurrence_count": config[
                "minimum_reduced_target_occurrence_count_v89"
            ],
            "actual_reduced_target_occurrence_count": reduced_count,
            "no_target_label_regressions": no_regressions,
            "aggregate_target_sample_reduction_observed": derived_labels < strict_labels,
            "passed": passed,
        },
        "sample_tax_measurement": {
            "derived_target_certificate_local_labels": derived_labels,
            "strict_target_certificate_local_labels": strict_labels,
            "derived_minus_strict_target_labels": derived_labels - strict_labels,
            "target_labels_avoided": strict_labels - derived_labels,
            "reduced_target_occurrence_count": reduced_count,
            "actual_target_sample_reduction_observed": derived_labels < strict_labels,
            "reduction_required_for_this_gate": True,
            "same_synthesizer_stopping_rule_and_exact_certificate_engine": True,
            "only_reusable_model_availability_differs_between_episode_arms": True,
        },
        "accounting": {
            "offline_v85r1_template_source_labels": 515,
            "offline_residual_library_labels": 204,
            "offline_v85r1_source_common_partial_labels": 170,
            "offline_v85r1_source_certificate_local_labels": 318,
            "target_common_partial_labels": sum(
                row["target_common_partial_ground_support_labels"] for row in occurrences
            ),
            "derived_target_certificate_local_labels": derived_labels,
            "strict_target_certificate_local_labels": strict_labels,
            "derived_target_execution_steps": sum(row["execution_steps"] for row in derived),
            "strict_target_execution_steps": sum(row["execution_steps"] for row in strict),
            "derived_abstract_planning_compute_events": sum(
                row["abstract_planning_compute_events"] for row in derived
            ),
            "strict_abstract_planning_compute_events": sum(
                row["abstract_planning_compute_events"] for row in strict
            ),
            "derived_queried_state_action_count": sum(
                row["queried_state_action_count"] for row in derived
            ),
            "strict_queried_state_action_count": sum(
                row["queried_state_action_count"] for row in strict
            ),
            "all_axes_separate": True,
        },
        "predecessor_identities_preserved": True,
        "target_episode_outcomes_used_to_select_permutation_alignment_or_refit_models": False,
        "multi_step_abstract_ordering_primary_observed": passed,
        "certificate_failure_only_local_ground_recovery_observed": certificate_clean,
        "query_local_exact_overlay_only_safety_authority": True,
        "sample_tax_reduction_verified": sample_reduced,
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
        "campaign_id": domains.extension_content_id_v89(
            domains.CONSTRUCTION_K7_PERMUTATION_MATCHED_CAMPAIGN_V89_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_permutation_matched_sample_tax_campaign_document_v89",)
