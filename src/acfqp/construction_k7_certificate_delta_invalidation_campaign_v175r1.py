"""One-shot producer for the fresh corrected V175r1 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_certificate_delta_invalidation_preregistration_v175r1 as pre
from acfqp.certificate_delta_invalidation_campaign_core_v175r1 import (
    build_certificate_delta_invalidation_campaign_v175r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "6552685740a9244d3a9b77c3bfdf78ce065cc98bbc8f2348cf0826c247c72f63"
EXPECTED_CANONICAL_BYTE_COUNT = 59_473_200
EXPECTED_CANONICAL_SHA256 = "31f4846627ed9750401b13a906dbc91b3242506c43e7df61fc3a14b7e4b2edf2"
ATTEMPT_TERMINAL_STATE = "FROZEN_SUCCESS"
FAILURE_ID = "0" * 64


class ConstructionK7CertificateDeltaInvalidationCampaignV175R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CertificateDeltaInvalidationCampaignV175R1Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CertificateDeltaInvalidationCampaignV175R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_certificate_delta_invalidation_campaign_v175r1(
    classifier_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v174_campaign_raw: bytes,
    v174_verification_raw: bytes,
    v175_failure_raw: bytes,
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V175r1 attempt is terminal and will not be rerun")
    registration = pre.freeze_certificate_delta_invalidation_preregistration_v175r1()
    document = build_certificate_delta_invalidation_campaign_v175r1(
        pre.campaign_config_v175r1(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        classifier_receipt_raw=classifier_raw,
        v174_campaign_raw=v174_campaign_raw,
        v174_verification_raw=v174_verification_raw,
        v175_failure_raw=v175_failure_raw,
    )
    if document.get("registered_gate", {}).get("passed") is not True:
        _fail("V175r1 preregistered scientific gate failed")
    raw = canonical_json_bytes(document)
    if CAMPAIGN_ID != "0" * 64 and not (
        document["campaign_id"] == CAMPAIGN_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V175r1 frozen campaign changed")
    _CACHE = CertificateDeltaInvalidationCampaignV175R1(
        _ISSUER, raw, document["campaign_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_ID",
    "run_certificate_delta_invalidation_campaign_v175r1",
)
