"""V61 matched persistent-overlay versus cold-restart campaign core."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v59 as domains_v59
from acfqp import construction_k7_domain_registry_extension_v61 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as acquisition
from acfqp.generic_certificate_guided_partial_planner_v16 import (
    run_certificate_guided_partial_episode_v16,
)
from acfqp.generic_persistent_certificate_overlay_planner_v17 import (
    run_persistent_certificate_overlay_episodes_v17,
)
from acfqp.phase3e_ids import canonical_json_bytes


class PersistentOverlayCampaignCoreV61Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise PersistentOverlayCampaignCoreV61Error(message)


def _identifier(domain: str, payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    return {**payload, key: domains.extension_content_id_v61(domain, payload)}


def _raw_batches(batches: tuple[tuple[Any, ...], ...]) -> list[list[dict[str, Any]]]:
    return [[row.to_document() for row in batch] for batch in batches]


def _legacy_config(config: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(config)
    result["successor_domains"] = {
        "preregistration": domains_v59.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_PREREGISTRATION_V59_DOMAIN,
        "acquisition": domains_v59.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_ACQUISITION_V59_DOMAIN,
        "certificate": domains_v59.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_CERTIFICATE_V59_DOMAIN,
        "distinction": domains_v59.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_DISTINCTION_V59_DOMAIN,
        "episode": domains_v59.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_EPISODE_V59_DOMAIN,
        "sample_tax": domains_v59.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_SAMPLE_TAX_V59_DOMAIN,
        "campaign": domains_v59.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_CAMPAIGN_V59_DOMAIN,
        "verification": domains_v59.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_VERIFICATION_V59_DOMAIN,
    }
    return result


def _acquire(adapter: Any, factor_library: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    rows = acquisition.acquire_matched_true_bit_models_v59(
        adapter, factor_library, _legacy_config(config)
    )
    longest = max(rows.values(), key=lambda value: len(value["batches"]))
    raw_payload = {
        "schema": "acfqp.persistent_overlay_raw_evidence.v61",
        "family": adapter.family,
        "seed": adapter.seed,
        "raw_transition_batches": _raw_batches(longest["batches"]),
        "maximum_observed_label_count": len(longest["batches"]),
        "generation_witness_present": False,
    }
    evidence = _identifier(
        config["v61_domains"]["raw_evidence"], raw_payload, "raw_evidence_id"
    )
    wrapped = {}
    for arm, row in rows.items():
        batches = _raw_batches(row["batches"])
        flat = [item for batch in batches for item in batch]
        payload = {
            "schema": "acfqp.persistent_overlay_raw_acquisition.v61",
            "family": adapter.family,
            "seed": adapter.seed,
            "arm": arm,
            "predecessor_acquisition": row["document"],
            "raw_evidence_id": evidence["raw_evidence_id"],
            "raw_transition_batches": batches,
            "ground_support_labels": len(batches),
            "raw_transition_count": len(flat),
            "raw_transition_sha256": hashlib.sha256(
                canonical_json_bytes(flat)
            ).hexdigest(),
            "reachable_frontier_exhaustion_input_consumed": False,
        }
        wrapped[arm] = {**row, "document": _identifier(config["v61_domains"]["acquisition"], payload, "acquisition_id")}
    common = min(len(row["batches"]) for row in rows.values())
    if _raw_batches(rows["ANONYMOUS_FACTOR_PRIOR_ON"]["batches"][:common]) != _raw_batches(rows["STRICT_NO_PRIOR"]["batches"][:common]):
        _fail("V61 matched acquisition prefix changed")
    return {"raw_evidence": evidence, "acquisitions": wrapped}


def _wrap_episode_evidence(
    raw_episode: Mapping[str, Any],
    *,
    family: str,
    seed: int,
    mode: str,
    acquisition_id: str,
    config: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    raw_failures = raw_episode[
        "new_failed_certificates" if mode == "PERSISTENT_OVERLAY" else "failed_certificates"
    ]
    raw_distinctions = raw_episode[
        "new_local_distinctions" if mode == "PERSISTENT_OVERLAY" else "local_distinctions"
    ]
    certificates = []
    distinctions = []
    for failure, distinction in zip(raw_failures, raw_distinctions, strict=True):
        certificate_payload = {
            "schema": "acfqp.persistent_overlay_failed_certificate.v61",
            "family": family,
            "seed": seed,
            "mode": mode,
            "episode_index": raw_episode["episode_index"],
            "partial_candidate_id": raw_episode["partial_candidate_id"],
            "failure": failure,
        }
        certificate = _identifier(
            config["v61_domains"]["certificate"],
            certificate_payload,
            "failed_certificate_id",
        )
        distinction_payload = {
            "schema": "acfqp.persistent_overlay_local_distinction.v61",
            "failed_certificate_id": certificate["failed_certificate_id"],
            "distinction": distinction,
        }
        certificates.append(certificate)
        distinctions.append(
            _identifier(
                config["v61_domains"]["distinction"],
                distinction_payload,
                "local_distinction_id",
            )
        )
    omitted = {
        "new_failed_certificates",
        "new_local_distinctions",
        "failed_certificates",
        "local_distinctions",
    }
    payload = {
        **{key: value for key, value in raw_episode.items() if key not in omitted},
        "schema": "acfqp.persistent_overlay_episode.v61",
        "mode": mode,
        "acquisition_id": acquisition_id,
        "failed_certificates": certificates,
        "local_distinctions": distinctions,
    }
    return (
        _identifier(config["v61_domains"]["episode"], payload, "episode_id"),
        certificates,
        distinctions,
    )


def _run_occurrence(args: tuple[Any, ...]) -> dict[str, Any]:
    family, seed, factor_library, config = args
    adapter = acquisition.predecessor.predecessor.prior_ground._adapter(
        family, seed, config
    )
    acquired = _acquire(adapter, factor_library, config)
    prior = acquired["acquisitions"]["ANONYMOUS_FACTOR_PRIOR_ON"]
    indices = tuple(config["episode_indices"])
    persistent = run_persistent_certificate_overlay_episodes_v17(
        adapter,
        prior["candidate"],
        prior["rows"],
        episode_indices=indices,
        maximum_abstract_depth=config["maximum_partial_abstract_depth"],
        maximum_execution_steps=config["maximum_partial_execution_steps"],
    )
    persistent_episodes = []
    persistent_certificates = []
    persistent_distinctions = []
    for raw_episode in persistent["episodes"]:
        episode, certificates, distinctions = _wrap_episode_evidence(
            raw_episode,
            family=family,
            seed=seed,
            mode="PERSISTENT_OVERLAY",
            acquisition_id=prior["document"]["acquisition_id"],
            config=config,
        )
        persistent_episodes.append(episode)
        persistent_certificates.extend(certificates)
        persistent_distinctions.extend(distinctions)
    cold_episodes = []
    cold_certificates = []
    cold_distinctions = []
    for episode_index in indices:
        cold = run_certificate_guided_partial_episode_v16(
            adapter,
            prior["candidate"],
            prior["rows"],
            episode_index=episode_index,
            maximum_abstract_depth=config["maximum_partial_abstract_depth"],
            maximum_execution_steps=config["maximum_partial_execution_steps"],
        )
        episode, certificates, distinctions = _wrap_episode_evidence(
            cold,
            family=family,
            seed=seed,
            mode="COLD_RESTART",
            acquisition_id=prior["document"]["acquisition_id"],
            config=config,
        )
        cold_episodes.append(episode)
        cold_certificates.extend(certificates)
        cold_distinctions.extend(distinctions)
    persistent_labels = sum(row["new_local_ground_support_labels"] for row in persistent_episodes)
    cold_labels = sum(row["local_ground_support_labels"] for row in cold_episodes)
    if (
        not all(row["success"] for row in [*persistent_episodes, *cold_episodes])
        or persistent_labels <= 0
        or cold_labels <= persistent_labels
        or any(row["new_local_ground_support_labels"] != 0 for row in persistent_episodes[1:])
        or [row["action_keys"] for row in persistent_episodes]
        != [row["action_keys"] for row in cold_episodes]
        or [row["outcome_tape_sha256"] for row in persistent_episodes]
        != [row["outcome_tape_sha256"] for row in cold_episodes]
    ):
        _fail(f"V61 matched persistent overlay Gate failed for {family} {seed}")
    run_payload = {
        "schema": "acfqp.persistent_overlay_matched_run.v61",
        "family": family,
        "seed": seed,
        "partial_acquisition_id": prior["document"]["acquisition_id"],
        "persistent_overlay_id": persistent["persistent_overlay_id"],
        "persistent_episodes": persistent_episodes,
        "cold_restart_episodes": cold_episodes,
        "persistent_failed_certificates": persistent_certificates,
        "persistent_local_distinctions": persistent_distinctions,
        "cold_failed_certificates": cold_certificates,
        "cold_local_distinctions": cold_distinctions,
        "persistent_overlay_raw_transition_rows": persistent["overlay_raw_transition_rows"],
        "persistent_local_ground_support_labels": persistent_labels,
        "cold_restart_local_ground_support_labels": cold_labels,
        "amortized_query_label_reduction": cold_labels - persistent_labels,
        "later_episode_ground_query_count": persistent["later_episode_ground_query_count"],
        "matched_action_and_outcome_tapes": True,
        "only_switched_variable": "OCCURRENCE_LOCAL_PROOF_OVERLAY_PERSISTENCE",
        "occurrence_identity_bound": True,
        "cross_occurrence_ground_fact_reuse_allowed": False,
        "complete_residual_world_model_synthesized": False,
        "success": True,
    }
    return {
        "family": family,
        "seed": seed,
        "raw_evidence": acquired["raw_evidence"],
        "acquisitions": {arm: row["document"] for arm, row in acquired["acquisitions"].items()},
        "run": _identifier(config["v61_domains"]["run"], run_payload, "run_id"),
    }


def build_persistent_overlay_campaign_document_v61(
    config: Mapping[str, Any],
    preregistration_id: str,
    factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    arguments = [
        (family, seed, factor_library, config)
        for family, spec in config["families"].items()
        for seed in spec["target_seeds"]
    ]
    if config["worker_count"] == 1:
        occurrences = [_run_occurrence(row) for row in arguments]
    else:
        with ProcessPoolExecutor(max_workers=config["worker_count"]) as executor:
            occurrences = list(executor.map(_run_occurrence, arguments))
    persistent_labels = sum(row["run"]["persistent_local_ground_support_labels"] for row in occurrences)
    cold_labels = sum(row["run"]["cold_restart_local_ground_support_labels"] for row in occurrences)
    family_rows = {}
    for family in config["families"]:
        selected = [row["run"] for row in occurrences if row["family"] == family]
        persistent = sum(row["persistent_local_ground_support_labels"] for row in selected)
        cold = sum(row["cold_restart_local_ground_support_labels"] for row in selected)
        if cold <= persistent:
            _fail(f"V61 persistent overlay did not reduce labels in {family}")
        family_rows[family] = {
            "occurrence_count": len(selected),
            "episode_count": len(selected) * len(config["episode_indices"]),
            "persistent_overlay_local_labels": persistent,
            "cold_restart_local_labels": cold,
            "amortized_query_label_reduction": cold - persistent,
        }
    sample_payload = {
        "schema": "acfqp.persistent_overlay_sample_tax.v61",
        "persistent_overlay_local_labels": persistent_labels,
        "cold_restart_local_labels": cold_labels,
        "amortized_query_label_reduction": cold_labels - persistent_labels,
        "family_projections": family_rows,
        "same_partial_model_same_episodes_same_outcome_tapes": True,
        "only_switched_variable": "OCCURRENCE_LOCAL_PROOF_OVERLAY_PERSISTENCE",
        "official_break_even_claimed": False,
    }
    sample = _identifier(config["v61_domains"]["sample_tax"], sample_payload, "sample_tax_id")
    payload = {
        "schema": "acfqp.persistent_overlay_campaign.v61",
        "preregistration_id": preregistration_id,
        "v60_campaign_id": config["v60_campaign_id"],
        "v60_verification_id": config["v60_verification_id"],
        "occurrences": occurrences,
        "sample_tax": sample,
        "accounting": {
            "acquisition_target_labels": sum(
                row["ground_support_labels"]
                for occurrence in occurrences
                for row in occurrence["acquisitions"].values()
            ),
            "persistent_overlay_local_labels": persistent_labels,
            "cold_restart_local_labels": cold_labels,
            "persistent_execution_steps": sum(
                episode["execution_steps"]
                for occurrence in occurrences
                for episode in occurrence["run"]["persistent_episodes"]
            ),
            "cold_restart_execution_steps": sum(
                episode["execution_steps"]
                for occurrence in occurrences
                for episode in occurrence["run"]["cold_restart_episodes"]
            ),
            "persistent_planning_compute_events": sum(
                episode["new_abstract_planning_compute_events"]
                for occurrence in occurrences
                for episode in occurrence["run"]["persistent_episodes"]
            ),
            "cold_restart_planning_compute_events": sum(
                episode["abstract_planning_compute_events"]
                for occurrence in occurrences
                for episode in occurrence["run"]["cold_restart_episodes"]
            ),
            "all_axes_separate": True,
        },
        "raw_transition_bytes_embedded_for_producer_free_replay": True,
        "all_ground_queries_followed_failed_certificates": True,
        "occurrence_bound_persistent_overlay_used": True,
        "cross_occurrence_ground_fact_reuse_allowed": False,
        "complete_residual_world_model_synthesized": False,
        "reachable_frontier_exhaustion_stop_consumed": False,
        "arbitrary_domain_transfer_claimed": False,
        "global_exact_dynamics_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return _identifier(config["v61_domains"]["campaign"], payload, "campaign_id")


__all__ = ("build_persistent_overlay_campaign_document_v61",)
