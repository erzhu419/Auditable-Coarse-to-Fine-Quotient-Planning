"""Synthesize a minimal anonymous query-policy classifier from frozen evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v158 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


V157_CAMPAIGN_ID = "51810176bf2ab9d4e51f11cf8a4f73b04bfb76bef116b8ebfce9d08f3fe1ed79"
V157_CAMPAIGN_BYTE_COUNT = 13_671_890
V157_CAMPAIGN_SHA256 = "8674649d85d991d8625d43104cd4a5e07fa75ccd4ffb88236e767cba11ea5284"
V157_VERIFICATION_ID = "61332d6b56b476d960915b182eff944c0a5e67a6dcf8b4782d798b0e46a6d59d"
V157_VERIFICATION_BYTE_COUNT = 17_545
V157_VERIFICATION_SHA256 = "fae743f81b19b45e85c5a96a1ffcf2bcbeee405e8a4651aa937169c635bcb9d4"
SOURCE_POSITIVE_SIGNATURES = (
    ((1, 4), (1, 4), (1, 4), (2, 3), (4, 4), (4, 16)),
    ((1, 4), (1, 4), (1, 4), (3, 3), (4, 4), (4, 16)),
)
SOURCE_FAILED_SIGNATURES = (((1, 4), (2, 2), (2, 2), (2, 4), (4, 4), (4, 16)),)
CLASSIFIER_RECEIPT_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class AnonymousQueryClassifierReceiptV158Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise AnonymousQueryClassifierReceiptV158Error(message)


def evaluate_classifier_expression_v158(expression, signature):
    index = 0 if expression["predicate_field"] == "INITIAL_SUPPORT" else 1
    if expression["predicate_comparator"] == "EQUAL":
        count = sum(pair[index] == expression["predicate_value"] for pair in signature)
    else:
        count = sum(pair[index] >= expression["predicate_value"] for pair in signature)
    return count > expression["count_threshold"], count


def synthesize_anonymous_query_classifier_v158():
    labelled = tuple((signature, True) for signature in SOURCE_POSITIVE_SIGNATURES) + tuple((signature, False) for signature in SOURCE_FAILED_SIGNATURES)
    candidates = []
    evaluated = 0
    for field_rank, field in enumerate(("INITIAL_SUPPORT", "CATALOGUE_SUPPORT")):
        for comparator_rank, comparator in enumerate(("EQUAL", "AT_LEAST")):
            for value in range(1, 17):
                for threshold in range(0, 7):
                    expression = {
                        "kind": "COUNT_PREDICATE_GREATER_THAN",
                        "predicate_field": field,
                        "predicate_comparator": comparator,
                        "predicate_value": value,
                        "count_threshold": threshold,
                    }
                    evaluated += 1
                    if all(evaluate_classifier_expression_v158(expression, signature)[0] is label for signature, label in labelled):
                        mdl = (1, comparator_rank, value.bit_length(), threshold.bit_length(), field_rank, value, threshold)
                        candidates.append((mdl, expression))
    if not candidates:
        _fail("V158 classifier grammar did not separate frozen evidence")
    mdl, expression = min(candidates, key=lambda row: (row[0], canonical_json_bytes(row[1])))
    return expression, list(mdl), evaluated, len(candidates)


def _document(v157_campaign_raw: bytes, v157_verification_raw: bytes):
    campaign = loads_canonical_json(v157_campaign_raw)
    verification = loads_canonical_json(v157_verification_raw)
    if not (
        canonical_json_bytes(campaign) == v157_campaign_raw and len(v157_campaign_raw) == V157_CAMPAIGN_BYTE_COUNT and hashlib.sha256(v157_campaign_raw).hexdigest() == V157_CAMPAIGN_SHA256 and campaign.get("campaign_id") == V157_CAMPAIGN_ID
        and canonical_json_bytes(verification) == v157_verification_raw and len(v157_verification_raw) == V157_VERIFICATION_BYTE_COUNT and hashlib.sha256(v157_verification_raw).hexdigest() == V157_VERIFICATION_SHA256 and verification.get("verification_id") == V157_VERIFICATION_ID
        and verification.get("registered_plan_mode_corrected_margin_evidence_independently_verified") is True
    ):
        _fail("V158 frozen source evidence changed")
    expression, mdl, evaluated, separating = synthesize_anonymous_query_classifier_v158()
    if expression != {"kind": "COUNT_PREDICATE_GREATER_THAN", "predicate_field": "INITIAL_SUPPORT", "predicate_comparator": "EQUAL", "predicate_value": 1, "count_threshold": 1}:
        _fail("V158 minimal classifier expression changed")
    payload = {
        "schema": "acfqp.anonymous_query_classifier_receipt.v158",
        "source_v157_campaign_id": V157_CAMPAIGN_ID,
        "source_v157_verification_id": V157_VERIFICATION_ID,
        "finite_typed_classifier_grammar": {
            "aggregate": "COUNT_PREDICATE_GREATER_THAN",
            "predicate_fields": ["INITIAL_SUPPORT", "CATALOGUE_SUPPORT"],
            "predicate_comparators": ["EQUAL", "AT_LEAST"],
            "predicate_values": {"minimum": 1, "maximum": 16},
            "count_thresholds": {"minimum": 0, "maximum": 6},
        },
        "source_positive_signatures": [[list(pair) for pair in signature] for signature in SOURCE_POSITIVE_SIGNATURES],
        "source_failed_signatures": [[list(pair) for pair in signature] for signature in SOURCE_FAILED_SIGNATURES],
        "selected_expression": expression,
        "selected_expression_mdl_key": mdl,
        "candidate_expression_count_evaluated": evaluated,
        "separating_expression_count": separating,
        "exact_mdl_then_canonical_tie_break": True,
        "source_labels_derived_only_from_frozen_predecessor_campaigns": True,
        "fresh_v158_target_outcomes_accessed": False,
        "exact_signature_registry_consulted_at_application": False,
        "classifier_is_query_order_meta_prior_not_model_or_certificate_authority": True,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {**payload, "classifier_receipt_id": domains.extension_content_id_v158(domains.CONSTRUCTION_K7_CLASSIFIER_RECEIPT_V158_DOMAIN, payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AnonymousQueryClassifierReceiptV158:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    classifier_receipt_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_anonymous_query_classifier_receipt_v158(v157_campaign_raw: bytes, v157_verification_raw: bytes):
    document = _document(v157_campaign_raw, v157_verification_raw)
    raw = canonical_json_bytes(document)
    if CLASSIFIER_RECEIPT_ID != "0" * 64 and (document["classifier_receipt_id"] != CLASSIFIER_RECEIPT_ID or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256):
        _fail("V158 classifier receipt changed")
    return AnonymousQueryClassifierReceiptV158(_ISSUER, raw, document["classifier_receipt_id"])


__all__ = ("CLASSIFIER_RECEIPT_ID", "evaluate_classifier_expression_v158", "freeze_anonymous_query_classifier_receipt_v158", "synthesize_anonymous_query_classifier_v158")
