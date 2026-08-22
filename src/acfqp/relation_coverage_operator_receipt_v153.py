"""Outcome-free extraction of the V153 acquisition operator from frozen use."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v153 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


V151_CAMPAIGN_ID = "da305e55c00ff69b3aa240f2536a511eec6d6c3ee07f1418f80281f9ffa64cb0"
V151_CAMPAIGN_BYTE_COUNT = 25_536_677
V151_CAMPAIGN_SHA256 = "df3c508a7aa9fb8b0fecebb07530b21288818ebf993cf2e1f8b4407e79568a68"
V151_VERIFICATION_ID = "a57a8075fa7edd59bbefa9555a9457403374ca9c69600f6f305efab6442efd35"
V151_VERIFICATION_BYTE_COUNT = 12_585
V151_VERIFICATION_SHA256 = "6d1597be009be60ab50381146267367cd35c57811845d10a1c9270cdf395c813"
V152_CAMPAIGN_ID = "043437af4d99d554275eaf1f13a5691b1f46a332081b5a1cbe3b75f0e0586783"
V152_CAMPAIGN_BYTE_COUNT = 30_756_918
V152_CAMPAIGN_SHA256 = "d77f1be15500ac909f81a0b782443a659970b625f534e3c3f0acd460c936091a"
V152_VERIFICATION_ID = "ff34a70a970a33766372a33ec5b490062deaf03d592fa3aaff488f07a5747a63"
V152_VERIFICATION_BYTE_COUNT = 12_987
V152_VERIFICATION_SHA256 = "7dbd36f30a60bc24dd353f1efc013923e16fa804c7dd2ce4a146d1057ce668c5"
OPERATOR_RECEIPT_ID = "07b8dddbaa4915cc7cd98804cee6efefefb287d2a0512120b0dc6623dcd687a9"
EXPECTED_CANONICAL_BYTE_COUNT = 1_578
EXPECTED_CANONICAL_SHA256 = "fd07c8439e639a1fb5a2b323282f50ca7fb3f968035a9c6a539e056c54b92b95"


class RelationCoverageOperatorReceiptV153Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise RelationCoverageOperatorReceiptV153Error(message)


def _verified(raw: bytes, *, identity: str, count: int, digest: str, key: str):
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw or len(raw) != count or hashlib.sha256(raw).hexdigest() != digest or document.get(key) != identity:
        _fail("V153 frozen predecessor changed")
    return document


def _document(v151_campaign_raw: bytes, v151_verification_raw: bytes, v152_campaign_raw: bytes, v152_verification_raw: bytes):
    v151_campaign = _verified(v151_campaign_raw, identity=V151_CAMPAIGN_ID, count=V151_CAMPAIGN_BYTE_COUNT, digest=V151_CAMPAIGN_SHA256, key="campaign_id")
    v151_verification = _verified(v151_verification_raw, identity=V151_VERIFICATION_ID, count=V151_VERIFICATION_BYTE_COUNT, digest=V151_VERIFICATION_SHA256, key="verification_id")
    v152_campaign = _verified(v152_campaign_raw, identity=V152_CAMPAIGN_ID, count=V152_CAMPAIGN_BYTE_COUNT, digest=V152_CAMPAIGN_SHA256, key="campaign_id")
    v152_verification = _verified(v152_verification_raw, identity=V152_VERIFICATION_ID, count=V152_VERIFICATION_BYTE_COUNT, digest=V152_VERIFICATION_SHA256, key="verification_id")
    if (
        v151_campaign["registered_gate"]["relational_artifact_selected_in_prior_everywhere"] is not True
        or v151_verification["registered_relation_keyed_sample_efficiency_improvement_independently_verified"] is not True
        or v152_campaign["registered_gate"]["changed_relation_cardinality_transfer_everywhere"] is not True
        or v152_verification["registered_changed_cardinality_sample_efficiency_improvement_independently_verified"] is not True
        or len(v151_campaign["target_occurrences"]) != 6
        or len(v152_campaign["target_occurrences"]) != 6
    ):
        _fail("V153 source selection evidence changed")
    payload = {
        "schema": "acfqp.relation_coverage_operator_receipt.v153",
        "source_campaign_ids": [V151_CAMPAIGN_ID, V152_CAMPAIGN_ID],
        "source_verification_ids": [V151_VERIFICATION_ID, V152_VERIFICATION_ID],
        "source_verified_occurrence_count": 12,
        "source_relation_key_cardinalities": [2, 3],
        "relational_artifact_selected_in_every_source_prior_arm": True,
        "source_aggregate_acquisition_labels_avoided": 96,
        "operator": {
            "initial_query_rule": "EXHAUST_ANONYMOUS_ACTIONS_AT_ONE_OBSERVED_STATE",
            "descriptor_selection_rule": "MINIMUM_FIELD_WITH_EXACT_FULL_CATALOGUE_REPEATED_SUPPORT_AND_ONE_TO_ONE_POSITIVE_DELTA_RELATION",
            "state_coordinate_selection_rule": "MAXIMUM_OBSERVED_DELTA_RANGE_THEN_MINIMUM_COLUMN",
            "continuation_rule": "MAXIMUM_PREVIOUSLY_OBSERVED_RELATION_DELTA",
            "fallback_rule": "WITNESS_BLIND_PATH_BACKTRACKING_WITH_EXACT_QUERY_DEDUPLICATION",
            "generation_witness_accessed": False,
            "semantic_names_used": False,
            "future_target_outcomes_accessed": False,
        },
        "operator_extracted_before_v153_outcomes": True,
        "operator_is_query_order_heuristic_not_model_or_certificate_authority": True,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {**payload, "operator_receipt_id": domains.extension_content_id_v153(domains.CONSTRUCTION_K7_OPERATOR_RECEIPT_V153_DOMAIN, payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class RelationCoverageOperatorReceiptV153:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    operator_receipt_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_relation_coverage_operator_receipt_v153(v151_campaign_raw: bytes, v151_verification_raw: bytes, v152_campaign_raw: bytes, v152_verification_raw: bytes):
    document = _document(v151_campaign_raw, v151_verification_raw, v152_campaign_raw, v152_verification_raw)
    raw = canonical_json_bytes(document)
    identity = document["operator_receipt_id"]
    if OPERATOR_RECEIPT_ID != "0" * 64 and (identity != OPERATOR_RECEIPT_ID or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256):
        _fail("V153 frozen operator receipt changed")
    return RelationCoverageOperatorReceiptV153(_ISSUER, raw, identity)


__all__ = ("OPERATOR_RECEIPT_ID", "freeze_relation_coverage_operator_receipt_v153")
