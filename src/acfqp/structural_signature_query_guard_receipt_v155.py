"""Outcome-free query-policy guard derived from V153 success and V154 failure."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v155 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


V153_CAMPAIGN_ID = "47028757be59d7b6617d01411d5e0b580944df931ecb82bcdcea27f98fccee27"
V153_CAMPAIGN_BYTE_COUNT = 7_167_903
V153_CAMPAIGN_SHA256 = "b85a19614111542a7cb1cd150019c7bf6775e15fc2cd4a8f6d2e8ec7c6c4f61d"
V153_VERIFICATION_ID = "edeec1a912c6ff4da374490fd53a1ab8eb84d0d70ef4492f8d00b367f51128ef"
V153_VERIFICATION_BYTE_COUNT = 10_351
V153_VERIFICATION_SHA256 = "ccc9b46543e592d238a79cefbd8f7241631f8771bf297580cd265af291628c18"
V154_CAMPAIGN_ID = "b6ecf976d4261f8753f9653d9b0aaa3c2c75c618ecae21d3602ae0a81f9b71f1"
V154_CAMPAIGN_BYTE_COUNT = 4_129_436
V154_CAMPAIGN_SHA256 = "9d4147d843f0f6c59c2e8efad6d917e25bbecd6563359ab785ed08c6915b3ef7"
V154_FAILURE_BYTE_COUNT = 3_309
V154_FAILURE_SHA256 = "7bb3f3cfb23ed848b6e5bd4e15ebe3a067fcdcfb2aa34cc6e903109dbd384894"
POSITIVE_SIGNATURES = (
    ((1, 4), (1, 4), (1, 4), (2, 3), (4, 4), (4, 16)),
    ((1, 4), (1, 4), (1, 4), (3, 3), (4, 4), (4, 16)),
)
FALLBACK_SIGNATURES = (
    ((1, 4), (2, 2), (2, 2), (2, 4), (4, 4), (4, 16)),
)
GUARD_RECEIPT_ID = "61394b986763ef65e12cd21a15940fe01c61bbca3e403c669c39cf8a8ebb6871"
EXPECTED_CANONICAL_BYTE_COUNT = 1_746
EXPECTED_CANONICAL_SHA256 = "15a0ef806ccb819c4123d6d9d85a3ed33707ffcfdbf1d344b283a6decea6c0e2"


class StructuralSignatureQueryGuardReceiptV155Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise StructuralSignatureQueryGuardReceiptV155Error(message)


def _verified(raw: bytes, *, identity: str | None, count: int, digest: str, key: str | None):
    document = loads_canonical_json(raw)
    if (
        canonical_json_bytes(document) != raw
        or len(raw) != count
        or hashlib.sha256(raw).hexdigest() != digest
        or (key is not None and document.get(key) != identity)
    ):
        _fail("V155 frozen predecessor changed")
    return document


def _document(v153_campaign_raw: bytes, v153_verification_raw: bytes, v154_campaign_raw: bytes, v154_failure_raw: bytes):
    v153_campaign = _verified(v153_campaign_raw, identity=V153_CAMPAIGN_ID, count=V153_CAMPAIGN_BYTE_COUNT, digest=V153_CAMPAIGN_SHA256, key="campaign_id")
    v153_verification = _verified(v153_verification_raw, identity=V153_VERIFICATION_ID, count=V153_VERIFICATION_BYTE_COUNT, digest=V153_VERIFICATION_SHA256, key="verification_id")
    v154_campaign = _verified(v154_campaign_raw, identity=V154_CAMPAIGN_ID, count=V154_CAMPAIGN_BYTE_COUNT, digest=V154_CAMPAIGN_SHA256, key="campaign_id")
    v154_failure = _verified(v154_failure_raw, identity=None, count=V154_FAILURE_BYTE_COUNT, digest=V154_FAILURE_SHA256, key=None)
    if (
        v153_campaign["registered_gate"]["aggregate_operator_sample_reduction_vs_legacy_prior"] != 345
        or v153_verification["registered_operator_sample_tax_reduction_independently_verified"] is not True
        or v154_campaign["registered_gate"]["aggregate_operator_sample_reduction_vs_legacy_prior"] != -8
        or v154_failure["same_identity_rerun_forbidden"] is not True
        or v154_failure["campaign_id"] != V154_CAMPAIGN_ID
    ):
        _fail("V155 positive or failed source evidence changed")
    payload = {
        "schema": "acfqp.structural_signature_query_guard_receipt.v155",
        "positive_source_campaign_id": V153_CAMPAIGN_ID,
        "positive_source_verification_id": V153_VERIFICATION_ID,
        "failed_source_campaign_id": V154_CAMPAIGN_ID,
        "failed_source_record_sha256": V154_FAILURE_SHA256,
        "positive_source_operator_sample_reduction": 345,
        "failed_source_operator_sample_reduction": -8,
        "signature_schema": "SORTED_PER_ANONYMOUS_FIELD_PAIR_OF_INITIAL_LEGAL_SUPPORT_CARDINALITY_AND_FULL_CATALOGUE_SUPPORT_CARDINALITY",
        "positive_relation_coverage_signatures": [[list(pair) for pair in signature] for signature in POSITIVE_SIGNATURES],
        "path_first_fallback_signatures": [[list(pair) for pair in signature] for signature in FALLBACK_SIGNATURES],
        "selection_rule": {
            "exact_positive_signature": "V153_RELATION_COVERAGE_THEN_DEDUPLICATED_PATH_BACKTRACKING",
            "exact_failed_or_unknown_signature": "WITNESS_BLIND_PATH_FIRST_BACKTRACKING",
            "signature_uses_action_metadata_and_initial_legality_only": True,
            "ground_successor_outcomes_accessed_by_guard": False,
            "semantic_names_used": False,
            "unknown_signature_defaults_to_safe_fallback": True,
        },
        "guard_frozen_before_v155_target_outcomes": True,
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
    return {
        **payload,
        "guard_receipt_id": domains.extension_content_id_v155(
            domains.CONSTRUCTION_K7_GUARD_RECEIPT_V155_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class StructuralSignatureQueryGuardReceiptV155:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    guard_receipt_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_structural_signature_query_guard_receipt_v155(
    v153_campaign_raw: bytes,
    v153_verification_raw: bytes,
    v154_campaign_raw: bytes,
    v154_failure_raw: bytes,
):
    document = _document(v153_campaign_raw, v153_verification_raw, v154_campaign_raw, v154_failure_raw)
    raw = canonical_json_bytes(document)
    if GUARD_RECEIPT_ID != "0" * 64 and (
        document["guard_receipt_id"] != GUARD_RECEIPT_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V155 guard receipt changed")
    return StructuralSignatureQueryGuardReceiptV155(_ISSUER, raw, document["guard_receipt_id"])


__all__ = (
    "FALLBACK_SIGNATURES",
    "GUARD_RECEIPT_ID",
    "POSITIVE_SIGNATURES",
    "freeze_structural_signature_query_guard_receipt_v155",
)
