"""Outcome-free V154 application contract for the frozen V153 operator."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v154 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


V153_OPERATOR_RECEIPT_ID = "07b8dddbaa4915cc7cd98804cee6efefefb287d2a0512120b0dc6623dcd687a9"
V153_OPERATOR_RECEIPT_BYTE_COUNT = 1_578
V153_OPERATOR_RECEIPT_SHA256 = "fd07c8439e639a1fb5a2b323282f50ca7fb3f968035a9c6a539e056c54b92b95"
V153_CAMPAIGN_ID = "47028757be59d7b6617d01411d5e0b580944df931ecb82bcdcea27f98fccee27"
V153_CAMPAIGN_BYTE_COUNT = 7_167_903
V153_CAMPAIGN_SHA256 = "b85a19614111542a7cb1cd150019c7bf6775e15fc2cd4a8f6d2e8ec7c6c4f61d"
V153_VERIFICATION_ID = "edeec1a912c6ff4da374490fd53a1ab8eb84d0d70ef4492f8d00b367f51128ef"
V153_VERIFICATION_BYTE_COUNT = 10_351
V153_VERIFICATION_SHA256 = "ccc9b46543e592d238a79cefbd8f7241631f8771bf297580cd265af291628c18"
APPLICATION_RECEIPT_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
SOURCE_ROOT = Path(__file__).resolve().parents[2]


class RelationCoverageCrossStructureApplicationReceiptV154Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise RelationCoverageCrossStructureApplicationReceiptV154Error(message)


def _verified(raw: bytes, *, identity: str, count: int, digest: str, key: str):
    document = loads_canonical_json(raw)
    if (
        canonical_json_bytes(document) != raw
        or len(raw) != count
        or hashlib.sha256(raw).hexdigest() != digest
        or document.get(key) != identity
    ):
        _fail("V154 frozen predecessor changed")
    return document


def _document(operator_raw: bytes, campaign_raw: bytes, verification_raw: bytes):
    operator = _verified(
        operator_raw,
        identity=V153_OPERATOR_RECEIPT_ID,
        count=V153_OPERATOR_RECEIPT_BYTE_COUNT,
        digest=V153_OPERATOR_RECEIPT_SHA256,
        key="operator_receipt_id",
    )
    campaign = _verified(
        campaign_raw,
        identity=V153_CAMPAIGN_ID,
        count=V153_CAMPAIGN_BYTE_COUNT,
        digest=V153_CAMPAIGN_SHA256,
        key="campaign_id",
    )
    verification = _verified(
        verification_raw,
        identity=V153_VERIFICATION_ID,
        count=V153_VERIFICATION_BYTE_COUNT,
        digest=V153_VERIFICATION_SHA256,
        key="verification_id",
    )
    operator_source = (SOURCE_ROOT / "src/acfqp/relation_coverage_acquisition_operator_v153.py").read_bytes()
    if (
        operator["operator"]["future_target_outcomes_accessed"] is not False
        or campaign["registered_gate"]["aggregate_operator_sample_reduction_vs_legacy_prior"] != 345
        or verification["registered_operator_sample_tax_reduction_independently_verified"] is not True
        or verification["operator_sample_reduction_vs_legacy_prior"] != 345
    ):
        _fail("V154 source operator evidence changed")
    payload = {
        "schema": "acfqp.relation_coverage_cross_structure_application_receipt.v154",
        "v153_operator_receipt_id": V153_OPERATOR_RECEIPT_ID,
        "v153_campaign_id": V153_CAMPAIGN_ID,
        "v153_verification_id": V153_VERIFICATION_ID,
        "v153_verified_operator_sample_reduction": 345,
        "v153_verified_factor_prior_reduction_within_operator": 20,
        "frozen_operator_source_fact": {
            "relative_path": "src/acfqp/relation_coverage_acquisition_operator_v153.py",
            "byte_count": len(operator_source),
            "sha256": hashlib.sha256(operator_source).hexdigest(),
        },
        "registered_application": {
            "target_structure": "FRESH_BRANCHING_FANOUT_DAG_WITH_CROSS_LAYER_EDGES",
            "same_exact_v153_query_operator_required": True,
            "aggregate_operator_reduction_vs_matched_legacy_required": True,
            "per_occurrence_operator_noninferiority_required": True,
            "aggregate_factor_prior_reduction_within_same_operator_required": True,
            "per_occurrence_factor_prior_noninferiority_required": True,
            "v115_memoized_plan_receipt_must_be_consumed_before_v109_execution_receipt": True,
            "nonrelational_anonymous_schema_ood_must_reject_before_bank_access": True,
            "fresh_target_outcomes_accessed": False,
        },
        "operator_remains_query_order_heuristic_not_model_or_certificate_authority": True,
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
        "application_receipt_id": domains.extension_content_id_v154(
            domains.CONSTRUCTION_K7_APPLICATION_RECEIPT_V154_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class RelationCoverageCrossStructureApplicationReceiptV154:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    application_receipt_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_relation_coverage_cross_structure_application_receipt_v154(
    operator_raw: bytes, campaign_raw: bytes, verification_raw: bytes
):
    document = _document(operator_raw, campaign_raw, verification_raw)
    raw = canonical_json_bytes(document)
    if APPLICATION_RECEIPT_ID != "0" * 64 and (
        document["application_receipt_id"] != APPLICATION_RECEIPT_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V154 application receipt changed")
    return RelationCoverageCrossStructureApplicationReceiptV154(
        _ISSUER, raw, document["application_receipt_id"]
    )


__all__ = (
    "APPLICATION_RECEIPT_ID",
    "freeze_relation_coverage_cross_structure_application_receipt_v154",
)
