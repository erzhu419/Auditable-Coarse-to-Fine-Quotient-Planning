"""One-shot producer for the preregistered V168 fifth-family campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import (
    construction_k7_fifth_family_total_plan_receipt_set_preregistration_v168 as pre,
)
from acfqp.fifth_family_total_plan_receipt_set_campaign_core_v168 import (
    build_fifth_family_total_plan_receipt_set_campaign_v168,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "447f04fb450a9b76083993593a66ef717431f0b814212927ff2adfa1e27e4dce"
EXPECTED_CANONICAL_BYTE_COUNT = 25_586_483
EXPECTED_CANONICAL_SHA256 = (
    "e0cd4d36fb72bf79519878e1a368aeecf128cd91c4571bf0071d68af2760dfa5"
)
ATTEMPT_TERMINAL_STATE = "FROZEN_SUCCESS"
FAILURE_ID = "0" * 64


class ConstructionK7FifthFamilyTotalPlanReceiptSetCampaignV168Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FifthFamilyTotalPlanReceiptSetCampaignV168Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FifthFamilyTotalPlanReceiptSetCampaignV168:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_fifth_family_total_plan_receipt_set_campaign_v168(
    classifier_receipt_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v167_campaign_raw: bytes,
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V168 target attempt is terminal and will not be rerun")
    registration = pre.freeze_fifth_family_total_plan_receipt_set_preregistration_v168()
    document = build_fifth_family_total_plan_receipt_set_campaign_v168(
        pre.campaign_config_v168(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
        v167_campaign_raw=v167_campaign_raw,
    )
    raw = canonical_json_bytes(document)
    if CAMPAIGN_ID != "0" * 64 and not (
        document["campaign_id"] == CAMPAIGN_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V168 frozen campaign changed")
    _CACHE = FifthFamilyTotalPlanReceiptSetCampaignV168(
        _ISSUER, raw, document["campaign_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_ID",
    "run_fifth_family_total_plan_receipt_set_campaign_v168",
)
