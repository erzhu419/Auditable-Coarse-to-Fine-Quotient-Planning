"""Matched residual-factor prior/no-prior campaign core for V63."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import hashlib
import math
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v63 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as acquisition
from acfqp.generic_adaptive_residual_factor_acquisition_v19 import (
    acquire_adaptive_residual_factor_v19,
    replay_adaptive_residual_factor_v19,
)
from acfqp.generic_certificate_guided_partial_planner_v16 import (
    run_certificate_guided_partial_episode_v16,
)
from acfqp.phase3e_ids import canonical_json_bytes


class ResidualFactorSampleTaxCampaignCoreV63Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ResidualFactorSampleTaxCampaignCoreV63Error(message)


def _identifier(domain: str, payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    return {**payload, key: domains.extension_content_id_v63(domain, payload)}


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
        "schema": "acfqp.residual_sample_tax_raw_query_pool.v63",
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
        config["v63_domains"]["raw_query_pool"], raw_payload, "raw_query_pool_id"
    )
    evidence = {
        "layout": candidate["layout"],
        "unknown_residual_target_columns": candidate[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": episode["raw_local_transition_rows"],
    }
    prior = acquire_adaptive_residual_factor_v19(
        evidence,
        prior_library=residual_library,
        confidence_denominator=config["residual_confidence_denominator"],
    )
    strict = acquire_adaptive_residual_factor_v19(
        evidence,
        prior_library=None,
        confidence_denominator=config["residual_confidence_denominator"],
    )
    prior_replay = replay_adaptive_residual_factor_v19(prior, evidence)
    strict_replay = replay_adaptive_residual_factor_v19(strict, evidence)
    wrapped = {}
    for name, row, replay in (
        ("RESIDUAL_FACTOR_PRIOR_ON", prior, prior_replay),
        ("STRICT_NO_RESIDUAL_FACTOR_PRIOR", strict, strict_replay),
    ):
        payload = {
            "schema": "acfqp.residual_sample_tax_acquisition.v63",
            "family": family,
            "seed": seed,
            "arm": name,
            "raw_query_pool_id": raw_pool["raw_query_pool_id"],
            "adaptive_acquisition": row,
            "full_query_pool_replay": replay,
        }
        wrapped[name] = _identifier(
            config["v63_domains"]["acquisition"], payload, "acquisition_id"
        )
    prior_labels = prior["ground_support_labels"]
    strict_labels = strict["ground_support_labels"]
    if (
        not episode["success"]
        or prior["same_generic_synthesizer_and_stop_rule"] is not True
        or strict["same_generic_synthesizer_and_stop_rule"] is not True
        or prior["reachable_frontier_exhaustion_consumed"] is not False
        or strict["reachable_frontier_exhaustion_consumed"] is not False
    ):
        _fail(f"V63 matched residual-factor Gate failed for {family} seed {seed}")
    safety_payload = {
        "schema": "acfqp.residual_sample_tax_safety_episode.v63",
        "family": family,
        "seed": seed,
        "raw_query_pool_id": raw_pool["raw_query_pool_id"],
        "prior_acquisition_id": wrapped["RESIDUAL_FACTOR_PRIOR_ON"]["acquisition_id"],
        "strict_acquisition_id": wrapped["STRICT_NO_RESIDUAL_FACTOR_PRIOR"]["acquisition_id"],
        "action_keys": episode["action_keys"],
        "outcome_tape_sha256": episode["outcome_tape_sha256"],
        "execution_steps": episode["execution_steps"],
        "full_safety_local_ground_support_labels": episode[
            "local_ground_support_labels"
        ],
        "prior_residual_acquisition_labels": prior_labels,
        "strict_residual_acquisition_labels": strict_labels,
        "residual_label_reduction": strict_labels - prior_labels,
        "prior_failed_full_pool_query_batches": prior_replay[
            "failed_query_batch_count"
        ],
        "strict_failed_full_pool_query_batches": strict_replay[
            "failed_query_batch_count"
        ],
        "statistical_proposal_tail_errors_do_not_bypass_certificate": True,
        "all_ground_queries_followed_failed_certificates": True,
        "safety_uses_only_exact_query_local_overlay": True,
        "residual_factor_proposal_used_as_safety_authority": False,
        "success": True,
    }
    return {
        "family": family,
        "seed": seed,
        "raw_query_pool": raw_pool,
        "acquisitions": wrapped,
        "safety_episode": _identifier(
            config["v63_domains"]["safety_episode"],
            safety_payload,
            "safety_episode_id",
        ),
    }


def build_residual_factor_sample_tax_campaign_document_v63(
    config: Mapping[str, Any],
    preregistration_id: str,
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
        _fail("V63 aggregate residual-factor label reduction Gate failed")
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
        if family_strict <= family_prior:
            _fail(f"V63 family label reduction Gate failed for {family}")
        family_rows[family] = {
            "occurrence_count": len(selected),
            "prior_residual_acquisition_labels": family_prior,
            "strict_residual_acquisition_labels": family_strict,
            "residual_label_reduction": family_strict - family_prior,
            "prior_failed_full_pool_query_batches": sum(
                row["safety_episode"]["prior_failed_full_pool_query_batches"]
                for row in selected
            ),
            "strict_failed_full_pool_query_batches": sum(
                row["safety_episode"]["strict_failed_full_pool_query_batches"]
                for row in selected
            ),
        }
    offline_labels = residual_library_artifact["accounting"]["offline_total_labels"]
    occurrence_count = len(occurrences)
    projected_break_even = math.ceil(offline_labels * occurrence_count / reduction)
    summary_payload = {
        "schema": "acfqp.residual_factor_sample_tax_summary.v63",
        "offline_development_labels": offline_labels,
        "target_occurrence_count": occurrence_count,
        "prior_target_residual_acquisition_labels": prior_labels,
        "strict_target_residual_acquisition_labels": strict_labels,
        "target_residual_label_reduction": reduction,
        "observed_prior_lifetime_labels_including_offline": offline_labels + prior_labels,
        "observed_strict_lifetime_labels": strict_labels,
        "offline_tax_amortized_within_registered_occurrences": offline_labels + prior_labels
        <= strict_labels,
        "diagnostic_projected_break_even_occurrence_count": projected_break_even,
        "diagnostic_projection_is_not_official_economics": True,
        "family_projections": family_rows,
        "only_switched_variable": "FROZEN_RESIDUAL_FACTOR_EXPRESSION_PRIOR",
        "same_synthesizer_stop_and_confidence_rule": True,
        "official_break_even_claimed": False,
    }
    summary = _identifier(
        config["v63_domains"]["summary"], summary_payload, "sample_tax_id"
    )
    payload = {
        "schema": "acfqp.residual_factor_sample_tax_campaign.v63",
        "preregistration_id": preregistration_id,
        "v62_library_artifact_id": residual_library_artifact[
            "library_artifact_id"
        ],
        "occurrences": occurrences,
        "sample_tax": summary,
        "accounting": {
            "offline_development_labels": offline_labels,
            "common_partial_acquisition_target_labels": sum(
                row["raw_query_pool"]["partial_acquisition"][
                    "ground_support_labels"
                ]
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
            "residual_candidate_binding_evaluation_count_prior": sum(
                row["acquisitions"]["RESIDUAL_FACTOR_PRIOR_ON"][
                    "adaptive_acquisition"
                ]["candidate_binding_evaluation_count"]
                for row in occurrences
            ),
            "residual_candidate_binding_evaluation_count_strict": sum(
                row["acquisitions"]["STRICT_NO_RESIDUAL_FACTOR_PRIOR"][
                    "adaptive_acquisition"
                ]["candidate_binding_evaluation_count"]
                for row in occurrences
            ),
            "all_axes_separate": True,
        },
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
        config["v63_domains"]["campaign"], payload, "campaign_id"
    )


__all__ = ("build_residual_factor_sample_tax_campaign_document_v63",)
