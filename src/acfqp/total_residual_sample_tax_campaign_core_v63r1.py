"""V63r1 total matched residual-factor sample-tax campaign core."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import math
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v63r1 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as acquisition
from acfqp.generic_certificate_guided_partial_planner_v16 import (
    run_certificate_guided_partial_episode_v16,
)
from acfqp.generic_total_adaptive_residual_acquisition_v20 import (
    acquire_total_adaptive_residual_factor_v20,
    replay_total_adaptive_residual_factor_v20,
)


class TotalResidualSampleTaxCampaignCoreV63R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise TotalResidualSampleTaxCampaignCoreV63R1Error(message)


def _identifier(domain: str, payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    return {**payload, key: domains.extension_content_id_v63r1(domain, payload)}


def _raw_batches(batches: tuple[tuple[Any, ...], ...]) -> list[list[dict[str, Any]]]:
    return [[row.to_document() for row in batch] for batch in batches]


def _run_occurrence(arguments: tuple[Any, ...]) -> dict[str, Any]:
    family, seed, factor_library, residual_library, config = arguments
    adapter = acquisition.predecessor.predecessor.prior_ground._adapter(
        family, seed, config
    )
    partial = acquisition.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    episode = run_certificate_guided_partial_episode_v16(
        adapter,
        partial["candidate"],
        partial["rows"],
        episode_index=0,
        maximum_abstract_depth=config["maximum_partial_abstract_depth"],
        maximum_execution_steps=config["maximum_partial_execution_steps"],
    )
    candidate = partial["candidate"].public_document
    raw_payload = {
        "schema": "acfqp.total_residual_sample_tax_raw_query_pool.v63r1",
        "family": family,
        "seed": seed,
        "partial_candidate_id": candidate["candidate_id"],
        "layout": candidate["layout"],
        "unknown_residual_target_columns": candidate[
            "unknown_residual_target_columns"
        ],
        "partial_acquisition": partial["document"],
        "raw_partial_acquisition_batches": _raw_batches(partial["batches"]),
        "failed_certificates": episode["failed_certificates"],
        "local_distinctions": episode["local_distinctions"],
        "raw_transition_rows": episode["raw_local_transition_rows"],
        "action_keys": episode["action_keys"],
        "outcome_tape_sha256": episode["outcome_tape_sha256"],
        "execution_steps": episode["execution_steps"],
        "full_safety_local_ground_support_labels": episode[
            "local_ground_support_labels"
        ],
        "residual_query_pool_label_count": episode["queried_state_action_count"],
        "abstract_planning_compute_events": episode[
            "abstract_planning_compute_events"
        ],
        "all_ground_queries_followed_failed_certificates": episode[
            "all_ground_queries_followed_failed_certificates"
        ],
        "full_episode_success": episode["success"],
        "query_pool_contexts_materialized_for_matched_offline_label_selection": True,
    }
    raw_pool = _identifier(
        config["v63r1_domains"]["raw_query_pool"], raw_payload, "raw_query_pool_id"
    )
    evidence = {
        "layout": candidate["layout"],
        "unknown_residual_target_columns": candidate[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": episode["raw_local_transition_rows"],
    }
    acquisitions = {}
    for name, library in (
        ("RESIDUAL_FACTOR_PRIOR_ON", residual_library),
        ("STRICT_NO_RESIDUAL_FACTOR_PRIOR", None),
    ):
        total = acquire_total_adaptive_residual_factor_v20(
            evidence,
            prior_library=library,
            confidence_denominator=config["residual_confidence_denominator"],
        )
        replay = replay_total_adaptive_residual_factor_v20(total, evidence)
        payload = {
            "schema": "acfqp.total_residual_sample_tax_acquisition.v63r1",
            "family": family,
            "seed": seed,
            "arm": name,
            "raw_query_pool_id": raw_pool["raw_query_pool_id"],
            "total_adaptive_acquisition": total,
            "full_query_pool_replay": replay,
        }
        acquisitions[name] = _identifier(
            config["v63r1_domains"]["acquisition"], payload, "acquisition_id"
        )
    prior = acquisitions["RESIDUAL_FACTOR_PRIOR_ON"]["total_adaptive_acquisition"]
    strict = acquisitions["STRICT_NO_RESIDUAL_FACTOR_PRIOR"][
        "total_adaptive_acquisition"
    ]
    if (
        not episode["success"]
        or prior["same_generic_synthesizer_and_stop_rule"] is not True
        or strict["same_generic_synthesizer_and_stop_rule"] is not True
        or prior["query_pool_exhaustion_used_as_positive_stop"] is not False
        or strict["query_pool_exhaustion_used_as_positive_stop"] is not False
    ):
        _fail(f"V63r1 total acquisition Gate failed for {family} seed {seed}")
    safety_payload = {
        "schema": "acfqp.total_residual_sample_tax_safety_episode.v63r1",
        "family": family,
        "seed": seed,
        "raw_query_pool_id": raw_pool["raw_query_pool_id"],
        "prior_acquisition_id": acquisitions["RESIDUAL_FACTOR_PRIOR_ON"][
            "acquisition_id"
        ],
        "strict_acquisition_id": acquisitions[
            "STRICT_NO_RESIDUAL_FACTOR_PRIOR"
        ]["acquisition_id"],
        "prior_status": prior["status"],
        "strict_status": strict["status"],
        "action_keys": episode["action_keys"],
        "outcome_tape_sha256": episode["outcome_tape_sha256"],
        "execution_steps": episode["execution_steps"],
        "full_safety_local_ground_support_labels": episode[
            "local_ground_support_labels"
        ],
        "prior_residual_acquisition_labels": prior["ground_support_labels"],
        "strict_residual_acquisition_labels": strict["ground_support_labels"],
        "residual_label_reduction": strict["ground_support_labels"]
        - prior["ground_support_labels"],
        "statistical_proposal_or_typed_abstention_retained": True,
        "all_ground_queries_followed_failed_certificates": True,
        "safety_uses_only_exact_query_local_overlay": True,
        "residual_factor_proposal_used_as_safety_authority": False,
        "success": True,
    }
    return {
        "family": family,
        "seed": seed,
        "raw_query_pool": raw_pool,
        "acquisitions": acquisitions,
        "safety_episode": _identifier(
            config["v63r1_domains"]["safety_episode"],
            safety_payload,
            "safety_episode_id",
        ),
    }


def build_total_residual_sample_tax_campaign_document_v63r1(
    config: Mapping[str, Any],
    preregistration_id: str,
    failed_v63_id: str,
    factor_library: Mapping[str, Any],
    residual_library_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    residual_library = residual_library_artifact["compiled_library"]
    arguments = [
        (family, seed, factor_library, residual_library, config)
        for family, specification in config["families"].items()
        for seed in specification["target_seeds"]
    ]
    if config["worker_count"] == 1:
        occurrences = [_run_occurrence(row) for row in arguments]
    else:
        with ProcessPoolExecutor(max_workers=config["worker_count"]) as executor:
            occurrences = list(executor.map(_run_occurrence, arguments))
    prior_labels = sum(
        row["safety_episode"]["prior_residual_acquisition_labels"]
        for row in occurrences
    )
    strict_labels = sum(
        row["safety_episode"]["strict_residual_acquisition_labels"]
        for row in occurrences
    )
    reduction = strict_labels - prior_labels
    if reduction <= 0:
        _fail("V63r1 aggregate residual-factor label reduction Gate failed")
    family_rows = {}
    for family in config["families"]:
        selected = [row for row in occurrences if row["family"] == family]
        family_prior = sum(
            row["safety_episode"]["prior_residual_acquisition_labels"]
            for row in selected
        )
        family_strict = sum(
            row["safety_episode"]["strict_residual_acquisition_labels"]
            for row in selected
        )
        family_rows[family] = {
            "occurrence_count": len(selected),
            "prior_residual_acquisition_labels": family_prior,
            "strict_residual_acquisition_labels": family_strict,
            "residual_label_reduction": family_strict - family_prior,
            "prior_proposal_count": sum(
                row["safety_episode"]["prior_status"]
                == "STATISTICAL_PROPOSAL_ISSUED"
                for row in selected
            ),
            "strict_proposal_count": sum(
                row["safety_episode"]["strict_status"]
                == "STATISTICAL_PROPOSAL_ISSUED"
                for row in selected
            ),
            "all_occurrences_retained": True,
        }
    offline_labels = residual_library_artifact["accounting"]["offline_total_labels"]
    occurrence_count = len(occurrences)
    summary_payload = {
        "schema": "acfqp.total_residual_factor_sample_tax_summary.v63r1",
        "offline_development_labels": offline_labels,
        "target_occurrence_count": occurrence_count,
        "prior_target_residual_acquisition_labels": prior_labels,
        "strict_target_residual_acquisition_labels": strict_labels,
        "target_residual_label_reduction": reduction,
        "observed_prior_lifetime_labels_including_offline": offline_labels + prior_labels,
        "observed_strict_lifetime_labels": strict_labels,
        "offline_tax_amortized_within_registered_occurrences": offline_labels + prior_labels
        <= strict_labels,
        "diagnostic_projected_break_even_occurrence_count": math.ceil(
            offline_labels * occurrence_count / reduction
        ),
        "diagnostic_projection_is_not_official_economics": True,
        "prior_proposal_count": sum(
            row["safety_episode"]["prior_status"] == "STATISTICAL_PROPOSAL_ISSUED"
            for row in occurrences
        ),
        "strict_proposal_count": sum(
            row["safety_episode"]["strict_status"] == "STATISTICAL_PROPOSAL_ISSUED"
            for row in occurrences
        ),
        "family_projections": family_rows,
        "only_switched_variable": "FROZEN_RESIDUAL_FACTOR_EXPRESSION_PRIOR_CODE_LENGTH",
        "same_synthesizer_stop_confidence_and_totalization_rule": True,
        "official_break_even_claimed": False,
    }
    summary = _identifier(
        config["v63r1_domains"]["summary"], summary_payload, "sample_tax_id"
    )
    payload = {
        "schema": "acfqp.total_residual_sample_tax_campaign.v63r1",
        "preregistration_id": preregistration_id,
        "failed_v63_registered_failure_id": failed_v63_id,
        "v62_library_artifact_id": residual_library_artifact[
            "library_artifact_id"
        ],
        "occurrences": occurrences,
        "sample_tax": summary,
        "accounting": {
            "offline_development_labels": offline_labels,
            "common_partial_acquisition_target_labels": sum(
                row["raw_query_pool"]["partial_acquisition"]["ground_support_labels"]
                for row in occurrences
            ),
            "prior_residual_acquisition_target_labels": prior_labels,
            "strict_residual_acquisition_target_labels": strict_labels,
            "full_safety_local_ground_support_labels": sum(
                row["safety_episode"]["full_safety_local_ground_support_labels"]
                for row in occurrences
            ),
            "execution_steps": sum(
                row["safety_episode"]["execution_steps"] for row in occurrences
            ),
            "abstract_planning_compute_events": sum(
                row["raw_query_pool"]["abstract_planning_compute_events"]
                for row in occurrences
            ),
            "all_axes_separate": True,
        },
        "all_registered_occurrences_retained_including_abstentions": True,
        "fresh_held_out_outcome_execution_performed": True,
        "producer_free_verification_present": False,
        "all_ground_queries_followed_failed_certificates": True,
        "statistical_residual_proposal_used_as_safety_authority": False,
        "complete_residual_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return _identifier(
        config["v63r1_domains"]["campaign"], payload, "campaign_id"
    )


__all__ = ("build_total_residual_sample_tax_campaign_document_v63r1",)
