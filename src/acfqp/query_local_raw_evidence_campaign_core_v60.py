"""V60 raw-evidence campaign with certificate-guided local residual overlays."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v59 as domains_v59
from acfqp import construction_k7_domain_registry_extension_v60 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as predecessor
from acfqp.generic_certificate_guided_partial_planner_v16 import (
    run_certificate_guided_partial_episode_v16,
)
from acfqp.phase3e_ids import canonical_json_bytes


class QueryLocalRawEvidenceCampaignCoreV60Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise QueryLocalRawEvidenceCampaignCoreV60Error(message)


def _identifier(domain: str, payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    return {**payload, key: domains.extension_content_id_v60(domain, payload)}


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


def _raw_batches(batches: tuple[tuple[Any, ...], ...]) -> list[list[dict[str, Any]]]:
    return [[row.to_document() for row in batch] for batch in batches]


def acquire_query_local_raw_evidence_v60(
    adapter: Any,
    factor_library: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    acquisitions = predecessor.acquire_matched_true_bit_models_v59(
        adapter, factor_library, _legacy_config(config)
    )
    longest = max(acquisitions.values(), key=lambda row: len(row["batches"]))
    raw_payload = {
        "schema": "acfqp.query_local_matched_raw_evidence.v60",
        "family": adapter.family,
        "seed": adapter.seed,
        "raw_transition_batches": _raw_batches(longest["batches"]),
        "maximum_observed_label_count": len(longest["batches"]),
        "symmetric_common_prefix_reconstructible_from_bytes": True,
        "generation_witness_present": False,
    }
    raw_evidence = _identifier(
        config["v60_domains"]["raw_evidence"], raw_payload, "raw_evidence_id"
    )
    wrapped = {}
    for arm, acquisition in acquisitions.items():
        batches = _raw_batches(acquisition["batches"])
        flat = [row for batch in batches for row in batch]
        if hashlib.sha256(canonical_json_bytes(flat)).hexdigest() != acquisition[
            "document"
        ]["raw_transition_sha256"]:
            _fail("V60 raw acquisition hash did not join predecessor evidence")
        payload = {
            "schema": "acfqp.query_local_raw_acquisition.v60",
            "family": adapter.family,
            "seed": adapter.seed,
            "arm": arm,
            "predecessor_acquisition": acquisition["document"],
            "raw_evidence_id": raw_evidence["raw_evidence_id"],
            "raw_transition_batches": batches,
            "ground_support_labels": len(batches),
            "raw_transition_count": len(flat),
            "raw_transition_sha256": hashlib.sha256(
                canonical_json_bytes(flat)
            ).hexdigest(),
            "compiled_program": (
                None
                if arm == "ANONYMOUS_FACTOR_PRIOR_ON"
                else acquisition["candidate"].program
            ),
            "compiled_layout": acquisition["candidate"].layout.to_document(),
            "producer_free_raw_prefix_replay_enabled": True,
            "reachable_frontier_exhaustion_input_consumed": False,
        }
        wrapped[arm] = {
            **acquisition,
            "document": _identifier(
                config["v60_domains"]["acquisition"], payload, "acquisition_id"
            ),
        }
    common = min(len(row["batches"]) for row in acquisitions.values())
    prefixes = [
        _raw_batches(row["batches"][:common]) for row in acquisitions.values()
    ]
    if prefixes[0] != prefixes[1]:
        _fail("V60 independently materialized common prefixes changed")
    return {"acquisitions": wrapped, "raw_evidence": raw_evidence}


def _guided_episode(
    adapter: Any,
    index: int,
    acquisition: Mapping[str, Any],
    config: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    raw = run_certificate_guided_partial_episode_v16(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        episode_index=index,
        maximum_abstract_depth=config["maximum_partial_abstract_depth"],
        maximum_execution_steps=config["maximum_partial_execution_steps"],
    )
    certificates = []
    distinctions = []
    for failure, distinction in zip(
        raw["failed_certificates"], raw["local_distinctions"], strict=True
    ):
        certificate_payload = {
            "schema": "acfqp.query_local_failed_certificate.v60",
            "family": adapter.family,
            "seed": adapter.seed,
            "episode_index": index,
            "partial_candidate_id": raw["partial_candidate_id"],
            "failure": failure,
        }
        certificate = _identifier(
            config["v60_domains"]["certificate"],
            certificate_payload,
            "failed_certificate_id",
        )
        distinction_payload = {
            "schema": "acfqp.query_local_ground_distinction.v60",
            "failed_certificate_id": certificate["failed_certificate_id"],
            "distinction": distinction,
        }
        certificates.append(certificate)
        distinctions.append(
            _identifier(
                config["v60_domains"]["distinction"],
                distinction_payload,
                "local_distinction_id",
            )
        )
    payload = {
        **{key: value for key, value in raw.items() if key not in {"failed_certificates", "local_distinctions"}},
        "schema": "acfqp.query_local_certificate_guided_episode.v60",
        "acquisition_id": acquisition["document"]["acquisition_id"],
        "failed_certificates": certificates,
        "local_distinctions": distinctions,
    }
    return (
        _identifier(config["v60_domains"]["episode"], payload, "episode_id"),
        certificates,
        distinctions,
    )


def _run_occurrence(args: tuple[Any, ...]) -> dict[str, Any]:
    family, index, seed, factor_library, config = args
    adapter = predecessor.predecessor.predecessor.prior_ground._adapter(
        family, seed, config
    )
    acquired = acquire_query_local_raw_evidence_v60(adapter, factor_library, config)
    acquisitions = acquired["acquisitions"]
    result = {
        "family": family,
        "seed": seed,
        "raw_evidence": acquired["raw_evidence"],
        "acquisitions": {
            arm: row["document"] for arm, row in acquisitions.items()
        },
        "episodes": {},
        "failures": [],
        "distinctions": [],
    }
    if index < config["planning_seed_count_per_family"]:
        prior_episode, failures, distinctions = _guided_episode(
            adapter, index, acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"], config
        )
        strict_episode, strict_failures, strict_distinctions = (
            predecessor.predecessor.predecessor.ground._episode(
                adapter=adapter,
                arm="STRICT_NO_PRIOR",
                episode_index=index,
                acquisition=acquisitions["STRICT_NO_PRIOR"],
                factor_library=factor_library,
                config=config,
            )
        )
        direct = predecessor.predecessor.predecessor.ground._strict_episode(
            adapter, index, config
        )
        if not (prior_episode["success"] and strict_episode["success"] and direct["success"]):
            _fail(f"V60 planning failed for {family} seed {seed}")
        result["episodes"] = {
            "ANONYMOUS_FACTOR_PRIOR_ON": prior_episode,
            "STRICT_NO_PRIOR": strict_episode,
            "STRICT_EXACT_CONTEXT": direct,
        }
        result["failures"] = [*failures, *strict_failures]
        result["distinctions"] = [*distinctions, *strict_distinctions]
    return result


def build_query_local_raw_evidence_campaign_document_v60(
    config: Mapping[str, Any],
    preregistration_id: str,
    factor_library: Mapping[str, Any],
) -> dict[str, Any]:
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
        for arm in ("ANONYMOUS_FACTOR_PRIOR_ON", "STRICT_NO_PRIOR", "STRICT_EXACT_CONTEXT")
    }
    prior_labels = sum(row["ground_support_labels"] for row in acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"])
    strict_labels = sum(row["ground_support_labels"] for row in acquisitions["STRICT_NO_PRIOR"])
    prior_local = sum(row["local_ground_support_labels"] for row in episodes["ANONYMOUS_FACTOR_PRIOR_ON"])
    strict_local = sum(row["local_ground_support_labels"] for row in episodes["STRICT_NO_PRIOR"])
    family_rows = {}
    for family in config["families"]:
        left = sum(row["ground_support_labels"] for row in acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"] if row["family"] == family)
        right = sum(row["ground_support_labels"] for row in acquisitions["STRICT_NO_PRIOR"] if row["family"] == family)
        if right <= left:
            _fail(f"V60 factor prior did not reduce acquisition labels in {family}")
        family_rows[family] = {
            "occurrence_count": 12,
            "factor_prior_on_acquisition_labels": left,
            "strict_no_prior_acquisition_labels": right,
            "incremental_acquisition_label_reduction": right - left,
        }
    online = strict_labels + strict_local - prior_labels - prior_local
    lifetime = online - config["factor_library_labels"]
    if online <= 0 or lifetime <= 0:
        _fail("V60 sample-tax Gate did not close")
    sample_payload = {
        "schema": "acfqp.query_local_sample_tax.v60",
        "factor_library_labels_prior_on_only": config["factor_library_labels"],
        "factor_prior_on_acquisition_labels": prior_labels,
        "strict_no_prior_acquisition_labels": strict_labels,
        "incremental_acquisition_label_reduction": strict_labels - prior_labels,
        "factor_prior_on_query_local_labels": prior_local,
        "strict_no_prior_local_recovery_labels": strict_local,
        "online_label_reduction_including_local_queries": online,
        "lifetime_label_reduction_after_offline_tax": lifetime,
        "family_projections": family_rows,
        "stream_prefix_residual_recovery_consumed": False,
        "only_switched_variable": "PARTIAL_FACTOR_PROPOSAL_LIBRARY_AVAILABLE",
        "official_break_even_claimed": False,
    }
    sample = _identifier(config["v60_domains"]["sample_tax"], sample_payload, "sample_tax_id")
    failures = [item for row in occurrences for item in row["failures"]]
    distinctions = [item for row in occurrences for item in row["distinctions"]]
    payload = {
        "schema": "acfqp.query_local_raw_evidence_campaign.v60",
        "preregistration_id": preregistration_id,
        "v59_campaign_id": config["v59_campaign_id"],
        "v59_verification_id": config["v59_verification_id"],
        "raw_evidence": [row["raw_evidence"] for row in occurrences],
        "acquisitions": acquisitions,
        "episodes": episodes,
        "failed_certificates": failures,
        "local_distinctions": distinctions,
        "sample_tax": sample,
        "accounting": {
            "offline_factor_library_labels": config["factor_library_labels"],
            "factor_prior_on_target_labels": prior_labels,
            "strict_no_prior_target_labels": strict_labels,
            "factor_prior_on_query_local_labels": prior_local,
            "strict_no_prior_local_labels": strict_local,
            "factor_prior_on_execution_steps": sum(row["execution_steps"] for row in episodes["ANONYMOUS_FACTOR_PRIOR_ON"]),
            "strict_no_prior_execution_steps": sum(row["execution_steps"] for row in episodes["STRICT_NO_PRIOR"]),
            "direct_execution_steps": sum(row["execution_steps"] for row in episodes["STRICT_EXACT_CONTEXT"]),
            "factor_prior_on_planning_compute_events": sum(row["abstract_planning_compute_events"] for row in episodes["ANONYMOUS_FACTOR_PRIOR_ON"]),
            "strict_no_prior_planning_compute_events": sum(row["planning_compute_events"] for row in episodes["STRICT_NO_PRIOR"]),
            "direct_planning_compute_events": sum(row["planning_compute_events"] for row in episodes["STRICT_EXACT_CONTEXT"]),
            "certificate_compute_events": len(failures),
            "all_axes_separate": True,
        },
        "raw_transition_bytes_embedded_for_producer_free_replay": True,
        "symmetric_common_prefix_reconstructible_from_bytes": True,
        "stream_prefix_residual_recovery_consumed": False,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_used": True,
        "complete_residual_world_model_synthesized": False,
        "reachable_frontier_exhaustion_stop_consumed": False,
        "heuristic_mdl_information_units_consumed": False,
        "predictive_evidence_to_mdl_credit_consumed": False,
        "arbitrary_domain_transfer_claimed": False,
        "global_exact_dynamics_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return _identifier(config["v60_domains"]["campaign"], payload, "campaign_id")


__all__ = (
    "acquire_query_local_raw_evidence_v60",
    "build_query_local_raw_evidence_campaign_document_v60",
)
