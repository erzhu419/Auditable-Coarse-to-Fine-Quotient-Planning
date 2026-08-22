"""Outcome-free max-margin guard derived from frozen V153--V155 evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v156 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


V153_CAMPAIGN_ID = "47028757be59d7b6617d01411d5e0b580944df931ecb82bcdcea27f98fccee27"
V153_CAMPAIGN_BYTE_COUNT = 7_167_903
V153_CAMPAIGN_SHA256 = "b85a19614111542a7cb1cd150019c7bf6775e15fc2cd4a8f6d2e8ec7c6c4f61d"
V154_CAMPAIGN_ID = "b6ecf976d4261f8753f9653d9b0aaa3c2c75c618ecae21d3602ae0a81f9b71f1"
V154_CAMPAIGN_BYTE_COUNT = 4_129_436
V154_CAMPAIGN_SHA256 = "9d4147d843f0f6c59c2e8efad6d917e25bbecd6563359ab785ed08c6915b3ef7"
V154_FAILURE_BYTE_COUNT = 3_309
V154_FAILURE_SHA256 = "7bb3f3cfb23ed848b6e5bd4e15ebe3a067fcdcfb2aa34cc6e903109dbd384894"
V155_CAMPAIGN_ID = "8e624c5e4fc054956e9c624d8612c016f91daf46a6d9991e07074b60ca2c4780"
V155_CAMPAIGN_BYTE_COUNT = 8_411_353
V155_CAMPAIGN_SHA256 = "2a0fba2417762da1c3e52357e4da484d93e798c4214d28366e9fef7c9e4ee08d"
V155_VERIFICATION_ID = "59ff42b2cfea1e433702d8a9cae3b4cdd69b7dd715c5512dcbe40194f72940c3"
V155_VERIFICATION_BYTE_COUNT = 10_833
V155_VERIFICATION_SHA256 = "f1d4e41fa8e7f7ddd2b833fa643cb426afcdf21dcbaaadf33d12dd0e3a58d239"
POSITIVE_SOURCE_SCORES = (3, 3)
FAILED_SOURCE_SCORES = (1,)
DECISION_BOUNDARY = 2
GUARD_RECEIPT_ID = "ce0cb66a507748cd7b6a69cd0de7a45efe1cc23c9616582fbc81ec3c27e1ab49"
EXPECTED_CANONICAL_BYTE_COUNT = 1_729
EXPECTED_CANONICAL_SHA256 = "2bf639742179fce7b0685ba95e2133064cbce7a35d4e0f06ac7b5ead34054776"


class StructuralMarginQueryGuardReceiptV156Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise StructuralMarginQueryGuardReceiptV156Error(message)


def _verified(raw: bytes, *, count: int, digest: str, key: str | None, identity: str | None):
    document = loads_canonical_json(raw)
    if (
        canonical_json_bytes(document) != raw
        or len(raw) != count
        or hashlib.sha256(raw).hexdigest() != digest
        or (key is not None and document.get(key) != identity)
    ):
        _fail("V156 frozen predecessor changed")
    return document


def _document(v153_campaign_raw: bytes, v154_campaign_raw: bytes, v154_failure_raw: bytes, v155_campaign_raw: bytes, v155_verification_raw: bytes):
    v153 = _verified(v153_campaign_raw, count=V153_CAMPAIGN_BYTE_COUNT, digest=V153_CAMPAIGN_SHA256, key="campaign_id", identity=V153_CAMPAIGN_ID)
    v154 = _verified(v154_campaign_raw, count=V154_CAMPAIGN_BYTE_COUNT, digest=V154_CAMPAIGN_SHA256, key="campaign_id", identity=V154_CAMPAIGN_ID)
    failure = _verified(v154_failure_raw, count=V154_FAILURE_BYTE_COUNT, digest=V154_FAILURE_SHA256, key=None, identity=None)
    v155 = _verified(v155_campaign_raw, count=V155_CAMPAIGN_BYTE_COUNT, digest=V155_CAMPAIGN_SHA256, key="campaign_id", identity=V155_CAMPAIGN_ID)
    verification = _verified(v155_verification_raw, count=V155_VERIFICATION_BYTE_COUNT, digest=V155_VERIFICATION_SHA256, key="verification_id", identity=V155_VERIFICATION_ID)
    if not (
        v153["registered_gate"]["aggregate_operator_sample_reduction_vs_legacy_prior"] == 345
        and v154["registered_gate"]["aggregate_operator_sample_reduction_vs_legacy_prior"] == -8
        and failure["same_identity_rerun_forbidden"] is True
        and v155["registered_gate"]["aggregate_guard_sample_reduction_vs_legacy_prior"] == 0
        and verification["registered_structural_guard_prevented_regression_independently_verified"] is True
    ):
        _fail("V156 source labels changed")
    payload = {
        "schema": "acfqp.structural_margin_query_guard_receipt.v156",
        "positive_source_campaign_id": V153_CAMPAIGN_ID,
        "failed_source_campaign_id": V154_CAMPAIGN_ID,
        "failed_source_record_sha256": V154_FAILURE_SHA256,
        "guarded_source_campaign_id": V155_CAMPAIGN_ID,
        "guarded_source_verification_id": V155_VERIFICATION_ID,
        "anonymous_score_rule": "COUNT_SORTED_SUPPORT_PAIRS_WITH_INITIAL_SUPPORT_ONE_AND_CATALOGUE_SUPPORT_AT_LEAST_THREE",
        "positive_source_scores": list(POSITIVE_SOURCE_SCORES),
        "failed_source_scores": list(FAILED_SOURCE_SCORES),
        "maximum_failed_score": max(FAILED_SOURCE_SCORES),
        "minimum_positive_score": min(POSITIVE_SOURCE_SCORES),
        "max_margin_decision_boundary": DECISION_BOUNDARY,
        "selection_rule": {
            "score_strictly_above_boundary": "V153_RELATION_COVERAGE_THEN_DEDUPLICATED_PATH_BACKTRACKING",
            "score_at_or_below_boundary": "WITNESS_BLIND_PATH_FIRST_BACKTRACKING",
            "boundary_and_unknown_scores_default_to_safe_fallback": True,
            "exact_signature_registry_consulted": False,
            "signature_uses_action_metadata_and_initial_legality_only": True,
            "ground_successor_outcomes_accessed_by_guard": False,
            "semantic_names_used": False,
        },
        "guard_frozen_before_v156_target_outcomes": True,
        "guard_is_query_order_meta_prior_not_model_or_certificate_authority": True,
        "v154_failed_identity_preserved": True,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {**payload, "guard_receipt_id": domains.extension_content_id_v156(domains.CONSTRUCTION_K7_GUARD_RECEIPT_V156_DOMAIN, payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class StructuralMarginQueryGuardReceiptV156:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    guard_receipt_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_structural_margin_query_guard_receipt_v156(v153_campaign_raw: bytes, v154_campaign_raw: bytes, v154_failure_raw: bytes, v155_campaign_raw: bytes, v155_verification_raw: bytes):
    document = _document(v153_campaign_raw, v154_campaign_raw, v154_failure_raw, v155_campaign_raw, v155_verification_raw)
    raw = canonical_json_bytes(document)
    if GUARD_RECEIPT_ID != "0" * 64 and (
        document["guard_receipt_id"] != GUARD_RECEIPT_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V156 guard receipt changed")
    return StructuralMarginQueryGuardReceiptV156(_ISSUER, raw, document["guard_receipt_id"])


__all__ = (
    "DECISION_BOUNDARY",
    "GUARD_RECEIPT_ID",
    "freeze_structural_margin_query_guard_receipt_v156",
)
