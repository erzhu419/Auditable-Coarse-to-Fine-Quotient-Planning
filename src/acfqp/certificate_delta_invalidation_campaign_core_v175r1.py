"""Corrected fresh-identity successor around the frozen V175 construction."""

from __future__ import annotations

import hashlib

from acfqp import construction_k7_domain_registry_extension_v175r1 as domains
from acfqp import certificate_delta_invalidation_campaign_core_v175 as base
from acfqp.construction_k7_paid_path_prefix_classifier_receipt_freeze_v161 import (
    CLASSIFIER_RECEIPT_ID,
    verify_frozen_paid_path_prefix_classifier_receipt_v161,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PACKET_FAMILY = base.PACKET_FAMILY
RESERVOIR_FAMILY = base.RESERVOIR_FAMILY
V175_FAILURE_ID = "431ac86701677586b6b8a95a75a7b9153941a75f7581703edec1637da8e0e476"
V175_FAILURE_BYTE_COUNT = 1_812
V175_FAILURE_SHA256 = "323f55deb1287dacff7df3759a54be54b5325d0fecf9715189b5f6ae15140dcd"


def certificate_delta_invalidation_campaign_config_v175r1():
    return base.certificate_delta_invalidation_campaign_config_v175()


def _frozen_failure(raw: bytes):
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == V175_FAILURE_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == V175_FAILURE_SHA256
        and document.get("failure_id") == V175_FAILURE_ID
        and document.get("same_preregistration_identity_may_be_rerun") is False
        and document.get("fresh_successor_identity_required") is True
        and document.get("target_outcomes_accessed") is False
    ):
        raise ValueError("V175r1 frozen V175 failure changed")
    return document


def _successor_occurrence(row):
    payload = {
        **{key: value for key, value in row.items() if key not in {"schema", "occurrence_id"}},
        "schema": "acfqp.certificate_delta_invalidation_occurrence.v175r1",
        "frozen_v175_failure_id": V175_FAILURE_ID,
        "corrected_classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v175r1(
            domains.CONSTRUCTION_K7_OCCURRENCE_V175R1_DOMAIN, payload
        ),
    }


def build_certificate_delta_invalidation_campaign_v175r1(
    config,
    *,
    preregistration_id,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
    v174_campaign_raw,
    v174_verification_raw,
    v175_failure_raw,
):
    _frozen_failure(v175_failure_raw)
    classifier = verify_frozen_paid_path_prefix_classifier_receipt_v161(
        classifier_receipt_raw
    )
    if classifier.get("classifier_receipt_id") != CLASSIFIER_RECEIPT_ID:
        raise ValueError("V175r1 classifier receipt identity changed")
    original = base.build_certificate_delta_invalidation_campaign_v175(
        config,
        preregistration_id=preregistration_id,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
        v174_campaign_raw=v174_campaign_raw,
        v174_verification_raw=v174_verification_raw,
    )
    rows = [_successor_occurrence(row) for row in original["target_occurrences"]]
    payload = {
        **{
            key: value
            for key, value in original.items()
            if key
            not in {
                "schema",
                "campaign_id",
                "target_occurrences",
                "target_occurrence_ids",
            }
        },
        "schema": "acfqp.certificate_delta_invalidation_campaign.v175r1",
        "frozen_v175_failure_id": V175_FAILURE_ID,
        "corrected_classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "same_v175_preregistration_identity_reused": False,
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v175r1(
            domains.CONSTRUCTION_K7_CAMPAIGN_V175R1_DOMAIN, payload
        ),
    }


__all__ = (
    "PACKET_FAMILY",
    "RESERVOIR_FAMILY",
    "build_certificate_delta_invalidation_campaign_v175r1",
    "certificate_delta_invalidation_campaign_config_v175r1",
)
