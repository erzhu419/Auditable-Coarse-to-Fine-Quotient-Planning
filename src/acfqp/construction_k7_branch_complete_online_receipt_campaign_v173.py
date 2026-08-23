"""One-shot producer for the preregistered V173 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_branch_complete_online_receipt_preregistration_v173 as pre
from acfqp.branch_complete_online_receipt_campaign_core_v173 import (
    build_branch_complete_online_receipt_campaign_v173,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "FROZEN_REGISTERED_GATE_FAILURE"
FAILURE_ID = "ce5ca1449b5956b9b60fd3b0cfa45ce2ea987822f34145cb63ec4e5a87a5626d"


class ConstructionK7BranchCompleteOnlineReceiptCampaignV173Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7BranchCompleteOnlineReceiptCampaignV173Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class BranchCompleteOnlineReceiptCampaignV173:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_branch_complete_online_receipt_campaign_v173(
    classifier_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v172r1_campaign_raw: bytes,
    v172r1_verification_raw: bytes,
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V173 attempt is terminal and will not be rerun")
    registration = pre.freeze_branch_complete_online_receipt_preregistration_v173()
    document = build_branch_complete_online_receipt_campaign_v173(
        pre.campaign_config_v173(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        classifier_receipt_raw=classifier_raw,
        v172r1_campaign_raw=v172r1_campaign_raw,
        v172r1_verification_raw=v172r1_verification_raw,
    )
    if document.get("registered_gate", {}).get("passed") is not True:
        _fail("V173 preregistered scientific gate failed")
    raw = canonical_json_bytes(document)
    if CAMPAIGN_ID != "0" * 64 and not (
        document["campaign_id"] == CAMPAIGN_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V173 frozen campaign changed")
    _CACHE = BranchCompleteOnlineReceiptCampaignV173(
        _ISSUER, raw, document["campaign_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_ID",
    "run_branch_complete_online_receipt_campaign_v173",
)
