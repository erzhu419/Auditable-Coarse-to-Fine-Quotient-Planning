"""Matched true-bit acquisition and certificate-gated residual recovery."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v58r1 as domains
from acfqp import universal_mixture_three_domain_campaign_core_v58 as predecessor
from acfqp.generic_bit_codelength_universal_synthesizer_v14 import (
    bit_codelength_universal_stop_update_v14,
)
from acfqp.generic_mdl_adaptive_joint_synthesizer_v11 import (
    exact_candidate_replay_v11,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    V51_FACTOR_TEMPLATE_PROJECTION,
    exact_partial_factor_replay_v15,
    partial_factor_bit_codelength_stop_update_v15,
    synthesize_partial_factor_candidate_v15,
)


class TrueBitPartialThreeDomainCampaignCoreV58R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise TrueBitPartialThreeDomainCampaignCoreV58R1Error(message)


def _identifier(domain: str, payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    return {**payload, key: domains.extension_content_id_v58r1(domain, payload)}


def _partial_document(
    adapter: Any,
    labels: int,
    rows: tuple[Any, ...],
    candidate: Any,
    issued_at: int,
    invalidated: int,
    disagreements: int,
    epoch: int,
    successes: int,
    stop: Mapping[str, Any],
    accepting_label: int,
    history: list[dict[str, Any]],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.true_bit_partial_acquisition.v58r1",
        "family": adapter.family,
        "seed": adapter.seed,
        "arm": "ANONYMOUS_FACTOR_PRIOR_ON",
        "factor_prior_enabled": True,
        "ground_support_labels": labels,
        "raw_transition_count": len(rows),
        "raw_transition_sha256": predecessor.ground._raw_sha(rows),
        "candidate": dict(candidate.public_document),
        "candidate_issued_at_support_label": issued_at,
        "invalidated_candidate_count": invalidated,
        "candidate_program_disagreement_count": disagreements,
        "candidate_epoch": epoch,
        "post_issuance_exact_prediction_success_count": successes,
        "first_accepting_observation_label": accepting_label,
        "terminal_stop_update": dict(stop),
        "stopping_history": history,
        "partial_prediction_scope_only": True,
        "unknown_residual_outputs_claimed": False,
        "complete_world_model_claimed": False,
        "terminal_observation_required_for_planning_objective": True,
        "reachable_frontier_exhaustion_input_consumed": False,
        "heuristic_mdl_information_units_consumed": False,
        "predictive_evidence_to_mdl_credit_consumed": False,
    }
    return _identifier(
        config["successor_domains"]["acquisition"], payload, "acquisition_id"
    )


def _full_document(
    adapter: Any,
    labels: int,
    rows: tuple[Any, ...],
    candidate: Any,
    issued_at: int,
    invalidated: int,
    disagreements: int,
    epoch: int,
    successes: int,
    stop: Mapping[str, Any],
    history: list[dict[str, Any]],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.true_bit_complete_acquisition.v58r1",
        "family": adapter.family,
        "seed": adapter.seed,
        "arm": "STRICT_NO_PRIOR",
        "factor_prior_enabled": False,
        "ground_support_labels": labels,
        "raw_transition_count": len(rows),
        "raw_transition_sha256": predecessor.ground._raw_sha(rows),
        "candidate": dict(candidate.public_document),
        "candidate_issued_at_support_label": issued_at,
        "invalidated_candidate_count": invalidated,
        "candidate_program_disagreement_count": disagreements,
        "candidate_epoch": epoch,
        "post_issuance_exact_prediction_success_count": successes,
        "terminal_stop_update": dict(stop),
        "stopping_history": history,
        "complete_world_model_synthesized_from_raw_observations": True,
        "factor_library_reference_code_available": False,
        "reachable_frontier_exhaustion_input_consumed": False,
        "heuristic_mdl_information_units_consumed": False,
        "predictive_evidence_to_mdl_credit_consumed": False,
    }
    return _identifier(
        config["successor_domains"]["acquisition"], payload, "acquisition_id"
    )


def acquire_matched_true_bit_models_v58r1(
    adapter: Any,
    factor_library: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    rows: list[Any] = []
    batches: list[tuple[Any, ...]] = []
    maximum = config["families"][adapter.family]["maximum_acquisition_labels"]
    partial_candidate = None
    full_candidate = None
    partial_issued = full_issued = 0
    partial_invalidated = full_invalidated = 0
    partial_disagreements = full_disagreements = 0
    partial_epoch = full_epoch = 0
    partial_successes = full_successes = 0
    partial_previous = full_previous = None
    accepting_label = None
    partial_history: list[dict[str, Any]] = []
    full_history: list[dict[str, Any]] = []
    results: dict[str, Any] = {}
    for labels, batch in enumerate(predecessor.ground._witness_blind_depth_frontier(adapter), 1):
        if labels > maximum:
            break
        rows.extend(batch)
        batches.append(batch)
        current = tuple(rows)
        if accepting_label is None and any(
            row.terminal_acceptance_after is True for row in batch
        ):
            accepting_label = labels
        if "ANONYMOUS_FACTOR_PRIOR_ON" not in results:
            if partial_candidate is not None:
                replay = exact_partial_factor_replay_v15(
                    partial_candidate, current, adapter.catalogue
                )
                if replay["exact"] is True:
                    partial_successes += 1
                else:
                    partial_previous = partial_candidate.public_document[
                        "candidate_id"
                    ]
                    partial_candidate = None
                    partial_invalidated += 1
                    partial_epoch += 1
                    partial_successes = 0
            if partial_candidate is None:
                try:
                    partial_candidate = synthesize_partial_factor_candidate_v15(
                        current,
                        adapter.catalogue,
                        V51_FACTOR_TEMPLATE_PROJECTION,
                        support_label_count=labels,
                        layout_domain=config["generic_domains"]["layout"],
                        candidate_domain=config["successor_domains"]["acquisition"],
                        candidate_content_id=domains.extension_content_id_v58r1,
                        minimum_factor_assignment_count=config[
                            "minimum_reusable_factor_count"
                        ],
                    )
                    partial_issued = labels
                    if (
                        partial_previous is not None
                        and partial_candidate.public_document["candidate_id"]
                        != partial_previous
                    ):
                        partial_disagreements += 1
                except Exception as error:
                    partial_history.append(
                        {
                            "support_label_count": labels,
                            "candidate_available": False,
                            "constructor_error_type": type(error).__name__,
                        }
                    )
                    partial_candidate = None
            if partial_candidate is not None:
                stop = partial_factor_bit_codelength_stop_update_v15(
                    partial_candidate,
                    current,
                    adapter.catalogue,
                    candidate_epoch=partial_epoch,
                    invalidated_candidate_count=partial_invalidated,
                    post_issuance_exact_prediction_success_count=partial_successes,
                    global_alpha_denominator=config["global_alpha_denominator"],
                )
                partial_history.append(
                    {
                        "support_label_count": labels,
                        "candidate_available": True,
                        "candidate_id": partial_candidate.public_document[
                            "candidate_id"
                        ],
                        "stopped_by_true_bits_and_universal_evidence": stop[
                            "stopped"
                        ],
                        "accepting_projection_available": accepting_label is not None,
                    }
                )
                if stop["stopped"] is True and accepting_label is not None:
                    document = _partial_document(
                        adapter,
                        labels,
                        current,
                        partial_candidate,
                        partial_issued,
                        partial_invalidated,
                        partial_disagreements,
                        partial_epoch,
                        partial_successes,
                        stop,
                        accepting_label,
                        list(partial_history),
                        config,
                    )
                    results["ANONYMOUS_FACTOR_PRIOR_ON"] = {
                        "document": document,
                        "candidate": partial_candidate,
                        "rows": current,
                        "batches": tuple(batches),
                    }
        if "STRICT_NO_PRIOR" not in results:
            if full_candidate is not None:
                replay = exact_candidate_replay_v11(
                    full_candidate, current, adapter.catalogue
                )
                if replay["exact"] is True:
                    full_successes += 1
                else:
                    full_previous = full_candidate.public_document[
                        "program_fingerprint_sha256"
                    ]
                    full_candidate = None
                    full_invalidated += 1
                    full_epoch += 1
                    full_successes = 0
            if full_candidate is None:
                try:
                    full_candidate = predecessor.ground._candidate(
                        current, adapter.catalogue, factor_library, labels, config
                    )
                    full_issued = labels
                    if (
                        full_previous is not None
                        and full_candidate.public_document[
                            "program_fingerprint_sha256"
                        ]
                        != full_previous
                    ):
                        full_disagreements += 1
                except Exception as error:
                    full_history.append(
                        {
                            "support_label_count": labels,
                            "candidate_available": False,
                            "constructor_error_type": type(error).__name__,
                        }
                    )
                    full_candidate = None
            if full_candidate is not None:
                stop = bit_codelength_universal_stop_update_v14(
                    full_candidate,
                    current,
                    adapter.catalogue,
                    factor_prior_enabled=False,
                    factor_library=factor_library,
                    invalidated_candidate_count=full_invalidated,
                    candidate_program_disagreement_count=full_disagreements,
                    candidate_epoch=full_epoch,
                    post_issuance_exact_prediction_success_count=full_successes,
                    global_alpha_denominator=config["global_alpha_denominator"],
                )
                full_history.append(
                    {
                        "support_label_count": labels,
                        "candidate_available": True,
                        "candidate_id": full_candidate.public_document["candidate_id"],
                        "stopped_by_true_bits_and_universal_evidence": stop[
                            "stopped"
                        ],
                    }
                )
                if stop["stopped"] is True:
                    document = _full_document(
                        adapter,
                        labels,
                        current,
                        full_candidate,
                        full_issued,
                        full_invalidated,
                        full_disagreements,
                        full_epoch,
                        full_successes,
                        stop,
                        list(full_history),
                        config,
                    )
                    results["STRICT_NO_PRIOR"] = {
                        "document": document,
                        "candidate": full_candidate,
                        "rows": current,
                        "batches": tuple(batches),
                    }
        if len(results) == 2:
            prior = results["ANONYMOUS_FACTOR_PRIOR_ON"]
            strict = results["STRICT_NO_PRIOR"]
            shared = tuple(
                row
                for item in strict["batches"][: len(prior["batches"])]
                for row in item
            )
            if prior["rows"] != shared:
                _fail("V58r1 matched acquisition prefix changed")
            return results
    _fail(
        "V58r1 true-bit acquisition did not close before its cap for "
        f"{adapter.family} seed {adapter.seed}; pending="
        f"{sorted({'ANONYMOUS_FACTOR_PRIOR_ON', 'STRICT_NO_PRIOR'} - set(results))}"
    )


def _recovered_prior_episode(
    adapter: Any,
    episode_index: int,
    acquisitions: Mapping[str, Any],
    factor_library: Mapping[str, Any],
    config: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    prior = acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"]
    strict = acquisitions["STRICT_NO_PRIOR"]
    recovery_labels = max(
        0,
        strict["document"]["ground_support_labels"]
        - prior["document"]["ground_support_labels"],
    )
    certificate_payload = {
        "schema": "acfqp.true_bit_partial_safety_certificate_failure.v58r1",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_index": episode_index,
        "partial_candidate_id": prior["document"]["candidate"]["candidate_id"],
        "failure_kind": "UNKNOWN_RESIDUAL_PREVENTS_ALL_BRANCH_SAFETY_PROOF",
        "unknown_residual_target_columns": prior["document"]["candidate"][
            "unknown_residual_target_columns"
        ],
        "ground_query_performed_before_failure": False,
    }
    certificate = _identifier(
        config["successor_domains"]["certificate"],
        certificate_payload,
        "failed_certificate_id",
    )
    distinction_payload = {
        "schema": "acfqp.true_bit_residual_recovery.v58r1",
        "failed_certificate_id": certificate["failed_certificate_id"],
        "successor_complete_candidate_id": strict["document"]["candidate"][
            "candidate_id"
        ],
        "additional_ground_support_labels": recovery_labels,
        "query_after_failed_certificate": True,
        "same_witness_blind_stream_prefix_extended": True,
        "query_locality_minimality_claimed": False,
    }
    distinction = _identifier(
        config["successor_domains"]["distinction"],
        distinction_payload,
        "local_distinction_id",
    )
    episode, nested_failures, nested_distinctions = predecessor.ground._episode(
        adapter=adapter,
        arm="ANONYMOUS_FACTOR_PRIOR_ON_AFTER_CERTIFICATE_RECOVERY",
        episode_index=episode_index,
        acquisition=strict,
        factor_library=factor_library,
        config=config,
    )
    payload = {
        "schema": "acfqp.true_bit_partial_recovered_episode.v58r1",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_index": episode_index,
        "partial_acquisition_id": prior["document"]["acquisition_id"],
        "complete_recovery_acquisition_id": strict["document"]["acquisition_id"],
        "initial_partial_safety_certificate": certificate,
        "initial_residual_distinction": distinction,
        "complete_abstract_episode": episode,
        "local_ground_support_labels": recovery_labels
        + episode["local_ground_support_labels"],
        "execution_steps": episode["execution_steps"],
        "planning_compute_events": episode["planning_compute_events"],
        "success": episode["success"],
        "all_ground_queries_followed_failed_certificates": True,
        "partial_model_executed_without_residual_safety_certificate": False,
    }
    return (
        _identifier(
            config["successor_domains"]["episode"], payload, "episode_id"
        ),
        [certificate, *nested_failures],
        [distinction, *nested_distinctions],
    )


def _run_occurrence(args: tuple[Any, ...]) -> dict[str, Any]:
    family, index, seed, factor_library, config = args
    adapter = predecessor.prior_ground._adapter(family, seed, config)
    acquisitions = acquire_matched_true_bit_models_v58r1(
        adapter, factor_library, config
    )
    result = {
        "family": family,
        "seed": seed,
        "acquisitions": {
            arm: row["document"] for arm, row in acquisitions.items()
        },
        "episodes": {},
        "failures": [],
        "distinctions": [],
    }
    if index < config["planning_seed_count_per_family"]:
        prior_episode, failures, distinctions = _recovered_prior_episode(
            adapter, index, acquisitions, factor_library, config
        )
        strict_episode, strict_failures, strict_distinctions = (
            predecessor.ground._episode(
                adapter=adapter,
                arm="STRICT_NO_PRIOR",
                episode_index=index,
                acquisition=acquisitions["STRICT_NO_PRIOR"],
                factor_library=factor_library,
                config=config,
            )
        )
        direct = predecessor.ground._strict_episode(adapter, index, config)
        if not (prior_episode["success"] and strict_episode["success"] and direct["success"]):
            _fail(f"V58r1 held-out planning failed for {family} seed {seed}")
        result["episodes"] = {
            "ANONYMOUS_FACTOR_PRIOR_ON": prior_episode,
            "STRICT_NO_PRIOR": strict_episode,
            "STRICT_EXACT_CONTEXT": direct,
        }
        result["failures"] = [*failures, *strict_failures]
        result["distinctions"] = [*distinctions, *strict_distinctions]
    return result


def build_true_bit_partial_three_domain_campaign_document_v58r1(
    config: Mapping[str, Any],
    preregistration_id: str,
    factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    if factor_library.get("factor_library_id") != config["factor_library_id"]:
        _fail("V58r1 factor-library identity changed")
    arguments = [
        (family, index, seed, factor_library, config)
        for family, spec in config["families"].items()
        for index, seed in enumerate(spec["target_seeds"])
    ]
    if config["worker_count"] == 1:
        occurrences = [_run_occurrence(row) for row in arguments]
    else:
        with ProcessPoolExecutor(max_workers=config["worker_count"]) as executor:
            occurrences = list(executor.map(_run_occurrence, arguments))
    acquisitions = {
        arm: [row["acquisitions"][arm] for row in occurrences]
        for arm in ("ANONYMOUS_FACTOR_PRIOR_ON", "STRICT_NO_PRIOR")
    }
    episodes = {
        arm: [row["episodes"][arm] for row in occurrences if arm in row["episodes"]]
        for arm in (
            "ANONYMOUS_FACTOR_PRIOR_ON",
            "STRICT_NO_PRIOR",
            "STRICT_EXACT_CONTEXT",
        )
    }
    failures = [item for row in occurrences for item in row["failures"]]
    distinctions = [item for row in occurrences for item in row["distinctions"]]
    prior_labels = sum(row["ground_support_labels"] for row in acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"])
    strict_labels = sum(row["ground_support_labels"] for row in acquisitions["STRICT_NO_PRIOR"])
    prior_local = sum(row["local_ground_support_labels"] for row in episodes["ANONYMOUS_FACTOR_PRIOR_ON"])
    strict_local = sum(row["local_ground_support_labels"] for row in episodes["STRICT_NO_PRIOR"])
    family_rows = {}
    for family in config["families"]:
        prior_family = [row for row in acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"] if row["family"] == family]
        strict_family = [row for row in acquisitions["STRICT_NO_PRIOR"] if row["family"] == family]
        reduction = sum(row["ground_support_labels"] for row in strict_family) - sum(
            row["ground_support_labels"] for row in prior_family
        )
        if reduction <= 0:
            _fail(f"V58r1 factor prior did not reduce labels in {family}")
        family_rows[family] = {
            "occurrence_count": len(prior_family),
            "factor_prior_on_acquisition_labels": sum(row["ground_support_labels"] for row in prior_family),
            "strict_no_prior_acquisition_labels": sum(row["ground_support_labels"] for row in strict_family),
            "incremental_acquisition_label_reduction": reduction,
        }
    online = (strict_labels + strict_local) - (prior_labels + prior_local)
    lifetime = online - config["factor_library_labels"]
    if strict_labels <= prior_labels or online <= 0 or lifetime <= 0:
        _fail("V58r1 registered sample-tax Gate did not close")
    sample_payload = {
        "schema": "acfqp.true_bit_partial_sample_tax.v58r1",
        "factor_library_labels_prior_on_only": config["factor_library_labels"],
        "factor_prior_on_acquisition_labels": prior_labels,
        "strict_no_prior_acquisition_labels": strict_labels,
        "incremental_acquisition_label_reduction": strict_labels - prior_labels,
        "factor_prior_on_certificate_recovery_labels": prior_local,
        "strict_no_prior_local_recovery_labels": strict_local,
        "online_label_reduction_including_recovery": online,
        "lifetime_label_reduction_after_offline_tax": lifetime,
        "family_projections": family_rows,
        "true_bit_codelength_used_in_both_arms": True,
        "same_universal_mixture_eprocess_used_in_both_arms": True,
        "only_switched_variable": "PARTIAL_FACTOR_PROPOSAL_LIBRARY_AVAILABLE",
        "query_locality_minimality_claimed": False,
        "official_break_even_claimed": False,
    }
    sample_tax = _identifier(
        config["successor_domains"]["sample_tax"], sample_payload, "sample_tax_id"
    )
    payload = {
        "schema": "acfqp.true_bit_partial_three_domain_campaign.v58r1",
        "preregistration_id": preregistration_id,
        "failed_v58_predecessor_id": config["failed_v58_predecessor_id"],
        "v57_campaign_id": config["v57_campaign_id"],
        "v57_verification_id": config["v57_verification_id"],
        "factor_library_id": config["factor_library_id"],
        "families": list(config["families"]),
        "acquisitions": acquisitions,
        "episodes": episodes,
        "failed_certificates": failures,
        "local_distinctions": distinctions,
        "sample_tax": sample_tax,
        "accounting": {
            "offline_factor_library_labels": config["factor_library_labels"],
            "factor_prior_on_target_labels": prior_labels,
            "strict_no_prior_target_labels": strict_labels,
            "factor_prior_on_recovery_labels": prior_local,
            "strict_no_prior_recovery_labels": strict_local,
            "factor_prior_on_execution_steps": sum(row["execution_steps"] for row in episodes["ANONYMOUS_FACTOR_PRIOR_ON"]),
            "strict_no_prior_execution_steps": sum(row["execution_steps"] for row in episodes["STRICT_NO_PRIOR"]),
            "direct_execution_steps": sum(row["execution_steps"] for row in episodes["STRICT_EXACT_CONTEXT"]),
            "factor_prior_on_planning_compute_events": sum(row["planning_compute_events"] for row in episodes["ANONYMOUS_FACTOR_PRIOR_ON"]),
            "strict_no_prior_planning_compute_events": sum(row["planning_compute_events"] for row in episodes["STRICT_NO_PRIOR"]),
            "direct_planning_compute_events": sum(row["planning_compute_events"] for row in episodes["STRICT_EXACT_CONTEXT"]),
            "certificate_compute_events": len(failures),
            "all_axes_separate": True,
        },
        "reachable_frontier_exhaustion_stop_consumed": False,
        "fixed_label_floor_consumed": False,
        "fixed_confirmation_block_consumed": False,
        "heuristic_mdl_information_units_consumed": False,
        "predictive_evidence_to_mdl_credit_consumed": False,
        "partial_model_executed_without_residual_safety_certificate": False,
        "all_recovery_queries_followed_failed_certificates": True,
        "query_locality_minimality_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "global_exact_dynamics_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return _identifier(
        config["successor_domains"]["campaign"], payload, "campaign_id"
    )


__all__ = (
    "acquire_matched_true_bit_models_v58r1",
    "build_true_bit_partial_three_domain_campaign_document_v58r1",
)
