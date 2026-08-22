"""One-shot producer for the preregistered V171 sixth-family campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import (
    construction_k7_sixth_family_complete_plan_receipt_preregistration_v171 as pre,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.sixth_family_complete_plan_receipt_campaign_core_v171 import (
    build_sixth_family_complete_plan_receipt_campaign_v171,
)


CAMPAIGN_ID = "ca284948d3d8886025fb13a84cffbab9bb535c242d292a2a68dd194bef4ed463"
EXPECTED_CANONICAL_BYTE_COUNT = 14_712_225
EXPECTED_CANONICAL_SHA256 = (
    "95b2fb332a5813d83a50b4ba192cc5720e054c009e8af4b3e9ce8c93cf99f76a"
)
ATTEMPT_TERMINAL_STATE = "FROZEN_SUCCESS"
FAILURE_ID = "0" * 64


class ConstructionK7SixthFamilyCompletePlanReceiptCampaignV171Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SixthFamilyCompletePlanReceiptCampaignV171Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SixthFamilyCompletePlanReceiptCampaignV171:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_sixth_family_complete_plan_receipt_campaign_v171(
    classifier_receipt_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v168_campaign_raw: bytes,
    v170_audit_raw: bytes,
    v170_verification_raw: bytes,
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V171 target attempt is terminal and will not be rerun")
    registration = pre.freeze_sixth_family_complete_plan_receipt_preregistration_v171()
    document = build_sixth_family_complete_plan_receipt_campaign_v171(
        pre.campaign_config_v171(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
        v168_campaign_raw=v168_campaign_raw,
        v170_audit_raw=v170_audit_raw,
        v170_verification_raw=v170_verification_raw,
    )
    if document.get("registered_gate", {}).get("passed") is not True:
        _fail("V171 preregistered scientific gate failed")
    raw = canonical_json_bytes(document)
    if CAMPAIGN_ID != "0" * 64 and not (
        document["campaign_id"] == CAMPAIGN_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V171 frozen campaign changed")
    _CACHE = SixthFamilyCompletePlanReceiptCampaignV171(
        _ISSUER, raw, document["campaign_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_ID",
    "run_sixth_family_complete_plan_receipt_campaign_v171",
)
