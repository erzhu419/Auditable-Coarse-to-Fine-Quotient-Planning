"""Producer-free verification of the frozen V63r1 matched campaign."""

from __future__ import annotations

import hashlib
import math
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v63r1 as domains
from acfqp.generic_total_adaptive_residual_acquisition_v20 import (
    acquire_total_adaptive_residual_factor_v20,
    replay_total_adaptive_residual_factor_v20,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


VERIFICATION_ID = "9dcfc9aa1e363d13ea6f32f0208048657acd4428e6c65d48a3c434b45e531b2c"
EXPECTED_CANONICAL_BYTE_COUNT = 689
EXPECTED_CANONICAL_SHA256 = "2b0ea9fb8253f2bc1ba21396cdac6174509cc8d960e18166c6dac312fe1b2f17"
_PREREGISTRATION_ID = "ff8004b4bf2535c9efade94410aa037bdf35949bfb9d91b62a8dfe82bccec8d5"
_FAILED_V63_ID = "716b0fba8968318c284a0840e2f109c861f819d5c52a177fdd41efee88c2fae0"
_V62_LIBRARY_ARTIFACT_ID = "26e5e031eb6b57e73253bc85bc3d0c372f6444248ad0c4e3343a01f43353b3d0"
_V62_RESIDUAL_LIBRARY = {
    "residual_factor_library_id": "216eec4bfa84daf406f38a55caac6e775d0658ef007a21d70d9cd95d93a23e4e",
    "compiled_subprograms": [
        {
            "normalized_expression": [
                "R03",
                ["R03", ["R00"], ["R01"]],
                ["R02"],
            ]
        },
        {
            "normalized_expression": [
                "R04",
                ["R00"],
                ["R03", ["R03", ["R00"], ["R01"]], ["R02"]],
            ]
        },
    ],
}


class ConstructionK7TotalResidualSampleTaxIndependentVerifierV63R1Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TotalResidualSampleTaxIndependentVerifierV63R1Error(
        message
    )


def _content_id(domain: str, document: dict[str, Any], key: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    if domains.extension_content_id_v63r1(domain, payload) != document.get(key):
        _fail(f"V63r1 {key} changed")


def _verify_raw_pool(row: dict[str, Any]) -> dict[str, Any]:
    _content_id(
        domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_RAW_QUERY_POOL_V63R1_DOMAIN,
        row,
        "raw_query_pool_id",
    )
    failures = row.get("failed_certificates")
    distinctions = row.get("local_distinctions")
    raw_rows = row.get("raw_transition_rows")
    batches = row.get("raw_partial_acquisition_batches")
    if not all(type(value) is list for value in (failures, distinctions, raw_rows, batches)):
        _fail("V63r1 raw evidence lists changed")
    if len(failures) != len(distinctions):
        _fail("V63r1 certificate/distinction pairing changed")
    flattened = []
    residual_queries = 0
    for index, (failure, distinction) in enumerate(
        zip(failures, distinctions, strict=True)
    ):
        if (
            failure.get("failure_index") != index
            or failure.get("ground_query_performed_before_failure") is not False
            or distinction.get("failure_index") != index
            or distinction.get("ground_support_labels") != 1
            or distinction.get("query_after_failed_certificate") is not True
        ):
            _fail("V63r1 certificate-before-query ordering changed")
        if distinction.get("distinction_kind") == "QUERY_LOCAL_EXACT_RESIDUAL_SUPPORT":
            residual_queries += 1
            rows = distinction.get("raw_transition_rows")
            if type(rows) is not list or not rows:
                _fail("V63r1 residual distinction rows changed")
            flattened.extend(rows)
    if (
        flattened != raw_rows
        or row.get("residual_query_pool_label_count") != residual_queries
        or row.get("full_safety_local_ground_support_labels") != len(distinctions)
        or row.get("partial_acquisition", {}).get("ground_support_labels") != len(batches)
        or len(row.get("action_keys", [])) != row.get("execution_steps")
        or len(row.get("outcome_tape_sha256", [])) != row.get("execution_steps")
        or row.get("all_ground_queries_followed_failed_certificates") is not True
        or row.get("full_episode_success") is not True
    ):
        _fail("V63r1 raw query-pool accounting changed")
    return {
        "layout": row["layout"],
        "unknown_residual_target_columns": row[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": raw_rows,
    }


def _verify_occurrence(row: dict[str, Any]) -> tuple[int, int, int, int, int]:
    family = row.get("family")
    seed = row.get("seed")
    pool = row.get("raw_query_pool")
    acquisitions = row.get("acquisitions")
    safety = row.get("safety_episode")
    if type(family) is not str or type(seed) is not int or not all(
        type(value) is dict for value in (pool, acquisitions, safety)
    ):
        _fail("V63r1 occurrence shape changed")
    if pool.get("family") != family or pool.get("seed") != seed:
        _fail("V63r1 occurrence/raw-pool identity changed")
    evidence = _verify_raw_pool(pool)
    reconstructed = {}
    for arm, library in (
        ("RESIDUAL_FACTOR_PRIOR_ON", _V62_RESIDUAL_LIBRARY),
        ("STRICT_NO_RESIDUAL_FACTOR_PRIOR", None),
    ):
        wrapped = acquisitions.get(arm)
        if type(wrapped) is not dict:
            _fail("V63r1 matched arm inventory changed")
        _content_id(
            domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_ACQUISITION_V63R1_DOMAIN,
            wrapped,
            "acquisition_id",
        )
        if (
            wrapped.get("family") != family
            or wrapped.get("seed") != seed
            or wrapped.get("arm") != arm
            or wrapped.get("raw_query_pool_id") != pool["raw_query_pool_id"]
        ):
            _fail("V63r1 acquisition joins changed")
        expected = acquire_total_adaptive_residual_factor_v20(
            evidence, prior_library=library, confidence_denominator=64
        )
        if wrapped.get("total_adaptive_acquisition") != expected:
            _fail("V63r1 adaptive acquisition differs from reconstruction")
        replay = replay_total_adaptive_residual_factor_v20(expected, evidence)
        if wrapped.get("full_query_pool_replay") != replay:
            _fail("V63r1 query-pool replay changed")
        reconstructed[arm] = expected
    _content_id(
        domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_SAFETY_EPISODE_V63R1_DOMAIN,
        safety,
        "safety_episode_id",
    )
    prior = reconstructed["RESIDUAL_FACTOR_PRIOR_ON"]
    strict = reconstructed["STRICT_NO_RESIDUAL_FACTOR_PRIOR"]
    expected_safety = {
        "schema": "acfqp.total_residual_sample_tax_safety_episode.v63r1",
        "family": family,
        "seed": seed,
        "raw_query_pool_id": pool["raw_query_pool_id"],
        "prior_acquisition_id": acquisitions["RESIDUAL_FACTOR_PRIOR_ON"][
            "acquisition_id"
        ],
        "strict_acquisition_id": acquisitions[
            "STRICT_NO_RESIDUAL_FACTOR_PRIOR"
        ]["acquisition_id"],
        "prior_status": prior["status"],
        "strict_status": strict["status"],
        "action_keys": pool["action_keys"],
        "outcome_tape_sha256": pool["outcome_tape_sha256"],
        "execution_steps": pool["execution_steps"],
        "full_safety_local_ground_support_labels": pool[
            "full_safety_local_ground_support_labels"
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
    expected_safety["safety_episode_id"] = domains.extension_content_id_v63r1(
        domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_SAFETY_EPISODE_V63R1_DOMAIN,
        expected_safety,
    )
    if safety != expected_safety:
        _fail("V63r1 safety episode changed")
    return (
        prior["ground_support_labels"],
        strict["ground_support_labels"],
        pool["partial_acquisition"]["ground_support_labels"],
        pool["full_safety_local_ground_support_labels"],
        pool["abstract_planning_compute_events"],
    )


def reconstruct_total_residual_occurrences_v63r1(
    occurrences: list[dict[str, Any]],
) -> dict[str, Any]:
    if type(occurrences) is not list or not occurrences:
        _fail("V63r1 reconstruct occurrence inventory changed")
    if len({(row.get("family"), row.get("seed")) for row in occurrences}) != len(
        occurrences
    ):
        _fail("V63r1 reconstruct occurrence identity duplicated")
    checked = [_verify_occurrence(row) for row in occurrences]
    family_rows = {}
    for family in sorted({row["family"] for row in occurrences}):
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
    return {
        "occurrence_count": len(occurrences),
        "prior_labels": sum(row[0] for row in checked),
        "strict_labels": sum(row[1] for row in checked),
        "common_partial_acquisition_labels": sum(row[2] for row in checked),
        "full_safety_local_labels": sum(row[3] for row in checked),
        "abstract_planning_compute_events": sum(row[4] for row in checked),
        "execution_steps": sum(
            row["safety_episode"]["execution_steps"] for row in occurrences
        ),
        "prior_proposal_count": sum(
            row["safety_episode"]["prior_status"] == "STATISTICAL_PROPOSAL_ISSUED"
            for row in occurrences
        ),
        "strict_proposal_count": sum(
            row["safety_episode"]["strict_status"] == "STATISTICAL_PROPOSAL_ISSUED"
            for row in occurrences
        ),
        "family_projections": family_rows,
    }


def verify_total_residual_sample_tax_campaign_bytes_v63r1(raw: bytes) -> bytes:
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V63r1 campaign bytes are not canonical")
    _content_id(
        domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_CAMPAIGN_V63R1_DOMAIN,
        document,
        "campaign_id",
    )
    if (
        document.get("preregistration_id") != _PREREGISTRATION_ID
        or document.get("failed_v63_registered_failure_id") != _FAILED_V63_ID
        or document.get("v62_library_artifact_id") != _V62_LIBRARY_ARTIFACT_ID
    ):
        _fail("V63r1 predecessor identities changed")
    occurrences = document.get("occurrences")
    if type(occurrences) is not list or len(occurrences) != 12:
        _fail("V63r1 occurrence inventory changed")
    if len({(row.get("family"), row.get("seed")) for row in occurrences}) != 12:
        _fail("V63r1 occurrence identity duplicated")
    checked = [_verify_occurrence(row) for row in occurrences]
    prior_labels = sum(row[0] for row in checked)
    strict_labels = sum(row[1] for row in checked)
    reduction = strict_labels - prior_labels
    if reduction <= 0:
        _fail("V63r1 aggregate label reduction changed")
    family_rows = {}
    for family in sorted({row["family"] for row in occurrences}):
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
    offline = 204
    summary_payload = {
        "schema": "acfqp.total_residual_factor_sample_tax_summary.v63r1",
        "offline_development_labels": offline,
        "target_occurrence_count": len(occurrences),
        "prior_target_residual_acquisition_labels": prior_labels,
        "strict_target_residual_acquisition_labels": strict_labels,
        "target_residual_label_reduction": reduction,
        "observed_prior_lifetime_labels_including_offline": offline + prior_labels,
        "observed_strict_lifetime_labels": strict_labels,
        "offline_tax_amortized_within_registered_occurrences": offline + prior_labels
        <= strict_labels,
        "diagnostic_projected_break_even_occurrence_count": math.ceil(
            offline * len(occurrences) / reduction
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
    expected_summary = {
        **summary_payload,
        "sample_tax_id": domains.extension_content_id_v63r1(
            domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_SUMMARY_V63R1_DOMAIN,
            summary_payload,
        ),
    }
    if document.get("sample_tax") != expected_summary:
        _fail("V63r1 sample-tax summary changed")
    expected_accounting = {
        "offline_development_labels": offline,
        "common_partial_acquisition_target_labels": sum(row[2] for row in checked),
        "prior_residual_acquisition_target_labels": prior_labels,
        "strict_residual_acquisition_target_labels": strict_labels,
        "full_safety_local_ground_support_labels": sum(row[3] for row in checked),
        "execution_steps": sum(
            row["safety_episode"]["execution_steps"] for row in occurrences
        ),
        "abstract_planning_compute_events": sum(row[4] for row in checked),
        "all_axes_separate": True,
    }
    if document.get("accounting") != expected_accounting:
        _fail("V63r1 accounting changed")
    expected_locks = {
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
    if any(document.get(key) != value for key, value in expected_locks.items()):
        _fail("V63r1 claim locks changed")
    verification_payload = {
        "schema": "acfqp.total_residual_sample_tax_verification.v63r1",
        "campaign_id": document["campaign_id"],
        "occurrence_count": len(occurrences),
        "prior_target_residual_labels": prior_labels,
        "strict_target_residual_labels": strict_labels,
        "target_residual_label_reduction": reduction,
        "offline_development_labels": offline,
        "diagnostic_projected_break_even_occurrence_count": math.ceil(
            offline * len(occurrences) / reduction
        ),
        "producer_imported": False,
        "campaign_core_imported": False,
        "adaptive_acquisitions_reconstructed": True,
        "certificate_before_query_ledger_replayed": True,
        "official_execution_allowed": False,
        "status": "PRODUCER_FREE_TOTAL_RESIDUAL_SAMPLE_TAX_VERIFIED",
    }
    verification = {
        **verification_payload,
        "verification_id": domains.extension_content_id_v63r1(
            domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_VERIFICATION_V63R1_DOMAIN,
            verification_payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V63r1 verification changed")
    return result


__all__ = (
    "reconstruct_total_residual_occurrences_v63r1",
    "verify_total_residual_sample_tax_campaign_bytes_v63r1",
)
