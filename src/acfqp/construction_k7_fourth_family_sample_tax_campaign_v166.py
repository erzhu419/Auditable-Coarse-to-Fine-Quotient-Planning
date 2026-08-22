"""Producer for the preregistered V166 fourth-family transfer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_fourth_family_sample_tax_preregistration_v166 as pre
from acfqp.fourth_family_sample_tax_transfer_campaign_core_v166 import (
    build_fourth_family_sample_tax_campaign_v166,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "FROZEN_FAILURE"
FAILURE_ID = "2d299454ac4aaa7d0517875f568b90a782d79c1c4aa6881b5d0e18ab48d15911"


class ConstructionK7FourthFamilySampleTaxCampaignV166Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FourthFamilySampleTaxCampaignV166Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FourthFamilySampleTaxCampaignV166:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_fourth_family_sample_tax_campaign_v166(
    classifier_receipt_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V166 target attempt is terminal and will not be rerun")
    registration = pre.freeze_fourth_family_sample_tax_preregistration_v166()
    document = build_fourth_family_sample_tax_campaign_v166(
        pre.campaign_config_v166(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
    )
    raw = canonical_json_bytes(document)
    _CACHE = FourthFamilySampleTaxCampaignV166(
        _ISSUER, raw, document["campaign_id"]
    )
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_ID",
    "run_fourth_family_sample_tax_campaign_v166",
)
