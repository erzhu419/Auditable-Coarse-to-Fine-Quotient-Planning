"""Producer for the preregistered V155 guarded sample-tax campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_structural_signature_guarded_preregistration_v155 as pre
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.structural_signature_guarded_campaign_core_v155 import build_structural_signature_guarded_campaign_document_v155


CAMPAIGN_ID = "8e624c5e4fc054956e9c624d8612c016f91daf46a6d9991e07074b60ca2c4780"
EXPECTED_CANONICAL_BYTE_COUNT = 8_411_353
EXPECTED_CANONICAL_SHA256 = "2a0fba2417762da1c3e52357e4da484d93e798c4214d28366e9fef7c9e4ee08d"
ATTEMPT_TERMINAL_STATE = "FROZEN_SUCCESS"
FAILURE_RECORD_SHA256: str | None = None


class ConstructionK7StructuralSignatureGuardedCampaignV155Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7StructuralSignatureGuardedCampaignV155Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class StructuralSignatureGuardedCampaignV155:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_structural_signature_guarded_campaign_v155(guard_receipt_raw: bytes, bank_raw: bytes, bank_verification_raw: bytes):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED" or CAMPAIGN_ID != "0" * 64:
        _fail("frozen V155 attempt is terminal; its identity will not be rerun")
    registration = pre.freeze_structural_signature_guarded_preregistration_v155(guard_receipt_raw)
    document = build_structural_signature_guarded_campaign_document_v155(
        pre.campaign_config_v155(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        guard_receipt_raw=guard_receipt_raw,
    )
    raw = canonical_json_bytes(document)
    _CACHE = StructuralSignatureGuardedCampaignV155(_ISSUER, raw, document["campaign_id"])
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_RECORD_SHA256",
    "run_structural_signature_guarded_campaign_v155",
)
