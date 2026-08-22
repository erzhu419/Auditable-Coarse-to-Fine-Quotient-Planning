"""Producer for the preregistered V157 plan-mode margin campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_plan_mode_margin_preregistration_v157 as pre
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.plan_mode_margin_campaign_core_v157 import build_plan_mode_margin_campaign_document_v157


CAMPAIGN_ID = "51810176bf2ab9d4e51f11cf8a4f73b04bfb76bef116b8ebfce9d08f3fe1ed79"
EXPECTED_CANONICAL_BYTE_COUNT = 13_671_890
EXPECTED_CANONICAL_SHA256 = "8674649d85d991d8625d43104cd4a5e07fa75ccd4ffb88236e767cba11ea5284"
ATTEMPT_TERMINAL_STATE = "FROZEN_SUCCESS"
FAILURE_RECORD_SHA256: str | None = None


class ConstructionK7PlanModeMarginCampaignV157Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PlanModeMarginCampaignV157Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PlanModeMarginCampaignV157:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_plan_mode_margin_campaign_v157(guard_receipt_raw: bytes, correction_receipt_raw: bytes, bank_raw: bytes, bank_verification_raw: bytes):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V157 attempt is terminal; its identity will not be rerun")
    registration = pre.freeze_plan_mode_margin_preregistration_v157(guard_receipt_raw, correction_receipt_raw)
    document = build_plan_mode_margin_campaign_document_v157(
        pre.campaign_config_v157(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        guard_receipt_raw=guard_receipt_raw,
        correction_receipt_raw=correction_receipt_raw,
    )
    raw = canonical_json_bytes(document)
    _CACHE = PlanModeMarginCampaignV157(_ISSUER, raw, document["campaign_id"])
    return _CACHE


__all__ = ("ATTEMPT_TERMINAL_STATE", "CAMPAIGN_ID", "FAILURE_RECORD_SHA256", "run_plan_mode_margin_campaign_v157")
