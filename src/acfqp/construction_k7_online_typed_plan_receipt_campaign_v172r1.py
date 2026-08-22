"""One-shot producer for the fresh V172r1 successor campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_online_typed_plan_receipt_preregistration_v172r1 as pre
from acfqp.online_typed_plan_receipt_campaign_core_v172 import (
    build_online_typed_plan_receipt_campaign_v172,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "c904d48bd590a287c4a1085ffecf41920ddde5cbba7a958e3906232afdd4128b"
EXPECTED_CANONICAL_BYTE_COUNT = 14_761_292
EXPECTED_CANONICAL_SHA256 = "2988188d53f74266839e107fb2e6a378cf3d2b8dfbe5f29fae3076b36556fb99"
ATTEMPT_TERMINAL_STATE = "FROZEN_SUCCESS"
FAILURE_ID = "0" * 64


class ConstructionK7OnlineTypedPlanReceiptCampaignV172R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OnlineTypedPlanReceiptCampaignV172R1Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OnlineTypedPlanReceiptCampaignV172R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_online_typed_plan_receipt_campaign_v172r1(
    classifier_receipt_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v171_campaign_raw: bytes,
    v171_verification_raw: bytes,
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V172r1 target attempt is terminal and will not be rerun")
    registration = pre.freeze_online_typed_plan_receipt_preregistration_v172r1()
    document = build_online_typed_plan_receipt_campaign_v172(
        pre.campaign_config_v172r1(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
        v171_campaign_raw=v171_campaign_raw,
        v171_verification_raw=v171_verification_raw,
    )
    if document.get("registered_gate", {}).get("passed") is not True:
        _fail("V172r1 preregistered scientific gate failed")
    raw = canonical_json_bytes(document)
    if CAMPAIGN_ID != "0" * 64 and not (
        document["campaign_id"] == CAMPAIGN_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V172r1 frozen campaign changed")
    _CACHE = OnlineTypedPlanReceiptCampaignV172R1(
        _ISSUER, raw, document["campaign_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_ID",
    "run_online_typed_plan_receipt_campaign_v172r1",
)
