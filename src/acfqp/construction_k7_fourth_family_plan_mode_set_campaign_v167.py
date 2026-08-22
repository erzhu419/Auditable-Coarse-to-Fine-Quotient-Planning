"""One-shot producer for the preregistered V167 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import (
    construction_k7_fourth_family_plan_mode_set_preregistration_v167 as pre,
)
from acfqp.fourth_family_plan_mode_set_campaign_core_v167 import (
    build_fourth_family_plan_mode_set_campaign_v167,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "UNEXECUTED"
FAILURE_ID = "0" * 64


class ConstructionK7FourthFamilyPlanModeSetCampaignV167Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FourthFamilyPlanModeSetCampaignV167Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FourthFamilyPlanModeSetCampaignV167:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_fourth_family_plan_mode_set_campaign_v167(
    classifier_receipt_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V167 target attempt is terminal and will not be rerun")
    registration = pre.freeze_fourth_family_plan_mode_set_preregistration_v167()
    document = build_fourth_family_plan_mode_set_campaign_v167(
        pre.campaign_config_v167(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
    )
    raw = canonical_json_bytes(document)
    if CAMPAIGN_ID != "0" * 64 and not (
        document["campaign_id"] == CAMPAIGN_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V167 frozen campaign changed")
    _CACHE = FourthFamilyPlanModeSetCampaignV167(
        _ISSUER, raw, document["campaign_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_ID",
    "run_fourth_family_plan_mode_set_campaign_v167",
)
