"""One-shot producer for the preregistered V176 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_certificate_delta_only_invalidation_preregistration_v176 as pre
from acfqp.certificate_delta_only_invalidation_campaign_core_v176 import (
    build_certificate_delta_only_invalidation_campaign_v176,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "UNEXECUTED"
FAILURE_ID = "0" * 64
V175R1_CAMPAIGN_ID = "6552685740a9244d3a9b77c3bfdf78ce065cc98bbc8f2348cf0826c247c72f63"
V175R1_VERIFICATION_ID = "bd5276748e2e136381c2058ff5c9f95c6ca55e4a1faf03cf43adbb48878240c0"


class ConstructionK7CertificateDeltaOnlyInvalidationCampaignV176Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CertificateDeltaOnlyInvalidationCampaignV176Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CertificateDeltaOnlyInvalidationCampaignV176:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_certificate_delta_only_invalidation_campaign_v176(
    classifier_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
) -> CertificateDeltaOnlyInvalidationCampaignV176:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V176 attempt is terminal and will not be rerun")
    registration = pre.freeze_certificate_delta_only_invalidation_preregistration_v176()
    document = build_certificate_delta_only_invalidation_campaign_v176(
        pre.campaign_config_v176(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        classifier_receipt_raw=classifier_raw,
        v175r1_campaign_id=V175R1_CAMPAIGN_ID,
        v175r1_verification_id=V175R1_VERIFICATION_ID,
    )
    if document.get("registered_gate", {}).get("passed") is not True:
        _fail("V176 preregistered scientific gate failed")
    raw = canonical_json_bytes(document)
    if CAMPAIGN_ID != "0" * 64 and not (
        document["campaign_id"] == CAMPAIGN_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V176 frozen campaign changed")
    _CACHE = CertificateDeltaOnlyInvalidationCampaignV176(
        _ISSUER, raw, document["campaign_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_ID",
    "run_certificate_delta_only_invalidation_campaign_v176",
)
