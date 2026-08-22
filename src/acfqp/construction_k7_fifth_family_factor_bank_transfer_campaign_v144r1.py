"""Producer for the preregistered V144R1 relational-overlay campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_fifth_family_factor_bank_transfer_preregistration_v144r1 as pre
from acfqp.fifth_family_factor_bank_transfer_campaign_core_v144r1 import (
    build_fifth_family_factor_bank_transfer_campaign_document_v144r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "UNEXECUTED"
FAILURE_RECORD_SHA256: str | None = None


class ConstructionK7FifthFamilyFactorBankTransferCampaignV144R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FifthFamilyFactorBankTransferCampaignV144R1Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FifthFamilyFactorBankTransferCampaignV144R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items() if key != "campaign_id"
        }
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains.extension_content_id_v144r1(
                pre.domains.CONSTRUCTION_K7_FIFTH_FAMILY_FACTOR_BANK_TRANSFER_CAMPAIGN_V144R1_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V144R1 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: FifthFamilyFactorBankTransferCampaignV144R1 | None = None


def run_fifth_family_factor_bank_transfer_campaign_v144r1(
    v144_preregistration_raw: bytes,
    v144_failure_raw: bytes,
) -> FifthFamilyFactorBankTransferCampaignV144R1:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED":
        _fail("frozen V144R1 attempt is terminal; its identity will not be rerun")
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V144R1 campaign exists; its identity will not be rerun")
    registration = pre.freeze_fifth_family_factor_bank_transfer_preregistration_v144r1(
        v144_preregistration_raw, v144_failure_raw
    )
    preregistration = registration.to_document()
    predecessor = preregistration["frozen_v144_preregistration"]
    document = build_fifth_family_factor_bank_transfer_campaign_document_v144r1(
        pre.campaign_config_v144r1(),
        preregistration_id=registration.preregistration_id,
        dictionary=predecessor["frozen_v141_factor_bank"],
        dictionary_verification=predecessor[
            "frozen_v141_independent_verification"
        ],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V144R1 campaign changed")
    _CACHE = FifthFamilyFactorBankTransferCampaignV144R1(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_RECORD_SHA256",
    "run_fifth_family_factor_bank_transfer_campaign_v144r1",
)
