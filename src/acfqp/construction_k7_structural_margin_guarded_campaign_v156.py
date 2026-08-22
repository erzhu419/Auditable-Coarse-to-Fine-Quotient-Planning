"""Producer for the preregistered V156 structural-margin campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_structural_margin_guarded_preregistration_v156 as pre
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.structural_margin_guarded_campaign_core_v156 import build_structural_margin_guarded_campaign_document_v156


CAMPAIGN_ID = "eddffbb380f9ea6e084515f622b81bce993b4e5b209bac2375417b1946dc6eb3"
EXPECTED_CANONICAL_BYTE_COUNT = 14_015_131
EXPECTED_CANONICAL_SHA256 = "15758409c83b82f2720529b5e0e80917077472bbe6664e5e2204704e3684788e"
ATTEMPT_TERMINAL_STATE = "FROZEN_PREREGISTERED_GATE_FAILURE"
FAILURE_RECORD_BYTE_COUNT = 5_207
FAILURE_RECORD_SHA256 = "5bd68c477d98231ddbc4bcd7361ad18f2ba1a89fc12b6ced7796da617791e881"


class ConstructionK7StructuralMarginGuardedCampaignV156Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7StructuralMarginGuardedCampaignV156Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class StructuralMarginGuardedCampaignV156:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_structural_margin_guarded_campaign_v156(guard_receipt_raw: bytes, bank_raw: bytes, bank_verification_raw: bytes):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V156 attempt is terminal; its identity will not be rerun")
    registration = pre.freeze_structural_margin_guarded_preregistration_v156(guard_receipt_raw)
    document = build_structural_margin_guarded_campaign_document_v156(
        pre.campaign_config_v156(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        guard_receipt_raw=guard_receipt_raw,
    )
    raw = canonical_json_bytes(document)
    _CACHE = StructuralMarginGuardedCampaignV156(_ISSUER, raw, document["campaign_id"])
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_RECORD_SHA256",
    "run_structural_margin_guarded_campaign_v156",
)
