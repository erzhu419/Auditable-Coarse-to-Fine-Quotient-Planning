"""One-shot V173r1 cross-family branch-complete producer."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_cross_family_branch_complete_preregistration_v173r1 as pre
from acfqp.cross_family_branch_complete_online_receipt_core_v173r1 import (
    build_cross_family_branch_complete_campaign_v173r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "418dc59c44243cb96e275539f564b1cd651664c9af19538d75f675093b8f2840"
EXPECTED_CANONICAL_BYTE_COUNT = 37_582_314
EXPECTED_CANONICAL_SHA256 = "ab871f3c8ecb6a19a8876458bb7c7e68737e7493489b89723191587d8219be46"
ATTEMPT_TERMINAL_STATE = "FROZEN_SUCCESS"
FAILURE_ID = "0" * 64


class ConstructionK7CrossFamilyBranchCompleteCampaignV173R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CrossFamilyBranchCompleteCampaignV173R1Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CrossFamilyBranchCompleteCampaignV173R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_cross_family_branch_complete_campaign_v173r1(
    classifier_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
    v172r1_campaign_raw: bytes,
    v172r1_verification_raw: bytes,
    v173_failure_raw: bytes,
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V173r1 attempt is terminal and will not be rerun")
    registration = pre.freeze_cross_family_branch_complete_preregistration_v173r1()
    document = build_cross_family_branch_complete_campaign_v173r1(
        pre.campaign_config_v173r1(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        classifier_receipt_raw=classifier_raw,
        v172r1_campaign_raw=v172r1_campaign_raw,
        v172r1_verification_raw=v172r1_verification_raw,
        v173_failure_raw=v173_failure_raw,
    )
    if document.get("registered_gate", {}).get("passed") is not True:
        _fail("V173r1 preregistered scientific gate failed")
    raw = canonical_json_bytes(document)
    if CAMPAIGN_ID != "0" * 64 and not (
        document["campaign_id"] == CAMPAIGN_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V173r1 frozen campaign changed")
    _CACHE = CrossFamilyBranchCompleteCampaignV173R1(
        _ISSUER, raw, document["campaign_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_ID",
    "run_cross_family_branch_complete_campaign_v173r1",
)
