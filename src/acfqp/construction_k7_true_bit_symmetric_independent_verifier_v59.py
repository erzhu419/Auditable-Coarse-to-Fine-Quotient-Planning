"""Producer-free identity and accounting verifier for frozen V59 bytes."""

from __future__ import annotations

import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v59 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "60ecb969f8b2b6cd7aa000d7306c213ab194293fc76a01190c73bae22e8b8d18"
CAMPAIGN_BYTE_COUNT = 881_518
CAMPAIGN_SHA256 = "50117e4665dc29819e19e38ebf17a8fbaceb2ba9c466afc4bd377ed74f83e99a"
PREREGISTRATION_ID = "99554f27032332e126e39294adcc36a601231a91d13fc5123f98fcb1557f7ff2"
VERIFICATION_ID = "b9b783080837cf9ac2641bf73036363bfe5813f8be1893b114c8fe7ec0f95a8f"
EXPECTED_VERIFICATION_BYTE_COUNT = 1_068
EXPECTED_VERIFICATION_SHA256 = "df0a035cec3b3a8790feaf1e20c6aed234b254cd403e7ac6b37d3081d16bb57e"


class ConstructionK7TrueBitSymmetricIndependentVerifierV59Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TrueBitSymmetricIndependentVerifierV59Error(message)


def _content(document: dict[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v59(domain, payload):
        _fail(f"V59 {key} content identity changed")


def verify_true_bit_symmetric_campaign_bytes_v59(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V59 frozen campaign byte envelope changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V59 campaign is not canonical JSON")
    if document.get("campaign_id") != CAMPAIGN_ID:
        _fail("V59 campaign identity changed")
    _content(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_CAMPAIGN_V59_DOMAIN,
    )
    if document.get("preregistration_id") != PREREGISTRATION_ID:
        _fail("V59 preregistration join changed")
    acquisitions = document.get("acquisitions")
    if type(acquisitions) is not dict or set(acquisitions) != {
        "ANONYMOUS_FACTOR_PRIOR_ON",
        "STRICT_NO_PRIOR",
    }:
        _fail("V59 acquisition arm inventory changed")
    prior = acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"]
    strict = acquisitions["STRICT_NO_PRIOR"]
    if type(prior) is not list or type(strict) is not list or len(prior) != 36 or len(strict) != 36:
        _fail("V59 acquisition occurrence cardinality changed")
    expected_pairs = [
        (family, seed)
        for family, start in (
            ("BALANCED_BATCH_REFINEMENT", 587_101),
            ("COUPLED_EXCHANGE", 588_101),
            ("MAINTENANCE_CASCADE", 589_101),
        )
        for seed in range(start, start + 12)
    ]
    if [(row.get("family"), row.get("seed")) for row in prior] != expected_pairs:
        _fail("V59 prior occurrence identities changed")
    if [(row.get("family"), row.get("seed")) for row in strict] != expected_pairs:
        _fail("V59 strict occurrence identities changed")
    for arm, rows in acquisitions.items():
        for row in rows:
            _content(
                row,
                "acquisition_id",
                domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_ACQUISITION_V59_DOMAIN,
            )
            if (
                row.get("arm") != arm
                or row.get("symmetric_minimum_common_prefix_post_audit") is not True
                or row.get("reachable_frontier_exhaustion_input_consumed") is not False
                or row.get("heuristic_mdl_information_units_consumed") is not False
                or row.get("predictive_evidence_to_mdl_credit_consumed") is not False
                or row.get("terminal_stop_update", {}).get("stopped") is not True
                or len(row.get("stopping_history", []))
                != row.get("ground_support_labels")
            ):
                _fail("V59 acquisition stopping contract changed")
    sample = document.get("sample_tax")
    if type(sample) is not dict:
        _fail("V59 sample-tax document is absent")
    _content(
        sample,
        "sample_tax_id",
        domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_SAMPLE_TAX_V59_DOMAIN,
    )
    prior_labels = sum(row["ground_support_labels"] for row in prior)
    strict_labels = sum(row["ground_support_labels"] for row in strict)
    episodes = document.get("episodes")
    if type(episodes) is not dict or any(
        len(episodes.get(arm, [])) != 3
        for arm in (
            "ANONYMOUS_FACTOR_PRIOR_ON",
            "STRICT_NO_PRIOR",
            "STRICT_EXACT_CONTEXT",
        )
    ):
        _fail("V59 episode inventory changed")
    if not all(row.get("success") is True for rows in episodes.values() for row in rows):
        _fail("V59 episode success claim changed")
    prior_local = sum(
        row["local_ground_support_labels"]
        for row in episodes["ANONYMOUS_FACTOR_PRIOR_ON"]
    )
    strict_local = sum(
        row["local_ground_support_labels"] for row in episodes["STRICT_NO_PRIOR"]
    )
    online = strict_labels + strict_local - prior_labels - prior_local
    lifetime = online - sample["factor_library_labels_prior_on_only"]
    expected_sample = {
        "factor_prior_on_acquisition_labels": prior_labels,
        "strict_no_prior_acquisition_labels": strict_labels,
        "incremental_acquisition_label_reduction": strict_labels - prior_labels,
        "factor_prior_on_certificate_recovery_labels": prior_local,
        "strict_no_prior_local_recovery_labels": strict_local,
        "online_label_reduction_including_recovery": online,
        "lifetime_label_reduction_after_offline_tax": lifetime,
    }
    if any(sample.get(key) != value for key, value in expected_sample.items()):
        _fail("V59 sample-tax arithmetic changed")
    for family, projection in sample.get("family_projections", {}).items():
        prior_family = sum(row["ground_support_labels"] for row in prior if row["family"] == family)
        strict_family = sum(row["ground_support_labels"] for row in strict if row["family"] == family)
        if projection != {
            "occurrence_count": 12,
            "factor_prior_on_acquisition_labels": prior_family,
            "strict_no_prior_acquisition_labels": strict_family,
            "incremental_acquisition_label_reduction": strict_family - prior_family,
        } or strict_family <= prior_family:
            _fail("V59 family sample-tax projection changed")
    if online <= 0 or lifetime <= 0:
        _fail("V59 positive sample-tax Gate changed")
    failures = document.get("failed_certificates")
    distinctions = document.get("local_distinctions")
    if type(failures) is not list or type(distinctions) is not list or len(failures) != len(distinctions):
        _fail("V59 certificate/distinction cardinality changed")
    if any(row.get("ground_query_performed_before_failure") is not False for row in failures):
        _fail("V59 ground query preceded a certificate failure")
    if any(row.get("query_after_failed_certificate") is not True for row in distinctions):
        _fail("V59 distinction ordering changed")
    locks = {
        "symmetric_minimum_common_prefix_post_audit": True,
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
    if any(document.get(key) != value for key, value in locks.items()):
        _fail("V59 claim lock changed")
    payload = {
        "schema": "acfqp.true_bit_symmetric_independent_verification.v59",
        "campaign_id": CAMPAIGN_ID,
        "campaign_byte_count": len(raw),
        "campaign_sha256": hashlib.sha256(raw).hexdigest(),
        "acquisition_occurrence_count": 36,
        "episode_count": 9,
        "failed_certificate_count": len(failures),
        "local_distinction_count": len(distinctions),
        "recomputed_sample_tax": expected_sample,
        "all_content_ids_and_internal_accounting_verified": True,
        "producer_or_campaign_core_imported": False,
        "raw_transition_semantic_reexecution_present": False,
        "full_scientific_semantic_replay_claimed": False,
        "outcome": "PRODUCER_FREE_IDENTITY_AND_INTERNAL_ACCOUNTING_VERIFIED",
    }
    result = {
        **payload,
        "verification_id": domains.extension_content_id_v59(
            domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_VERIFICATION_V59_DOMAIN,
            payload,
        ),
    }
    verification_raw = canonical_json_bytes(result)
    if VERIFICATION_ID != "0" * 64 and (
        result["verification_id"] != VERIFICATION_ID
        or len(verification_raw) != EXPECTED_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(verification_raw).hexdigest() != EXPECTED_VERIFICATION_SHA256
    ):
        _fail("frozen V59 verification changed")
    return result


__all__ = ("verify_true_bit_symmetric_campaign_bytes_v59",)
