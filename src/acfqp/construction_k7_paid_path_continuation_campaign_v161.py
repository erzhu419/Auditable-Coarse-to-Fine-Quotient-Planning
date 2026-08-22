"""Producer for the preregistered V161 exact-fallback campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_paid_path_continuation_preregistration_v161 as pre
from acfqp.paid_path_continuation_campaign_core_v161 import (
    build_paid_path_continuation_campaign_v161,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
FAILED_PREREGISTRATION_ID = "84bfbf8e9be7de54d0ac95516e5adf18cd5cf7ea08ddb8c22881795c234ee13e"
ATTEMPT_TERMINAL_STATE = "FROZEN_FAILURE_BEFORE_CAMPAIGN_DOCUMENT"
FAILURE_RECORD_BYTE_COUNT = 301
FAILURE_RECORD_SHA256 = "2a6658caac00c9c4257311e6a1bcc9667afadc13339d36aff4d84d6ea7293cab"


class ConstructionK7PaidPathContinuationCampaignV161Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PaidPathContinuationCampaignV161Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PaidPathContinuationCampaignV161:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_paid_path_continuation_campaign_v161(
    classifier_receipt_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V161 target attempt is terminal and will not be rerun")
    registration = pre.freeze_paid_path_continuation_preregistration_v161(
        classifier_receipt_raw
    )
    document = build_paid_path_continuation_campaign_v161(
        pre.campaign_config_v161(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
    )
    raw = canonical_json_bytes(document)
    _CACHE = PaidPathContinuationCampaignV161(
        _ISSUER, raw, document["campaign_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_RECORD_SHA256",
    "run_paid_path_continuation_campaign_v161",
)
