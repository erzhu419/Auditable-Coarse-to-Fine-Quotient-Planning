"""Producer for the preregistered V160 progressive raw-prefix campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_progressive_raw_prefix_preregistration_v160 as pre
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.progressive_raw_prefix_campaign_core_v160 import (
    build_progressive_raw_prefix_campaign_v160,
)


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "UNEXECUTED"
FAILURE_RECORD_SHA256: str | None = None


class ConstructionK7ProgressiveRawPrefixCampaignV160Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProgressiveRawPrefixCampaignV160Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ProgressiveRawPrefixCampaignV160:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_progressive_raw_prefix_campaign_v160(
    classifier_receipt_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V160 target attempt is terminal and will not be rerun")
    registration = pre.freeze_progressive_raw_prefix_preregistration_v160(
        classifier_receipt_raw
    )
    document = build_progressive_raw_prefix_campaign_v160(
        pre.campaign_config_v160(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
    )
    raw = canonical_json_bytes(document)
    _CACHE = ProgressiveRawPrefixCampaignV160(
        _ISSUER, raw, document["campaign_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_RECORD_SHA256",
    "run_progressive_raw_prefix_campaign_v160",
)
