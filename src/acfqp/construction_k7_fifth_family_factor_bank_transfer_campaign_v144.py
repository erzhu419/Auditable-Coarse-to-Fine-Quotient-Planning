"""Producer for the preregistered V144 fifth-family transfer campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_fifth_family_factor_bank_transfer_preregistration_v144 as pre
from acfqp.fifth_family_factor_bank_transfer_campaign_core_v144 import (
    build_fifth_family_factor_bank_transfer_campaign_document_v144,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "FROZEN_PREREGISTERED_INCREMENTAL_RELATIONAL_PROJECTION_FAILURE"
FAILURE_RECORD_SHA256 = (
    "24a77206af172b7b51c9f4836b7e40ee28fbb63ef9e9c1de622dae91eb9e6418"
)


class ConstructionK7FifthFamilyFactorBankTransferCampaignV144Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FifthFamilyFactorBankTransferCampaignV144Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FifthFamilyFactorBankTransferCampaignV144:
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
            or pre.domains.extension_content_id_v144(
                pre.domains.CONSTRUCTION_K7_FIFTH_FAMILY_FACTOR_BANK_TRANSFER_CAMPAIGN_V144_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V144 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: FifthFamilyFactorBankTransferCampaignV144 | None = None


def run_fifth_family_factor_bank_transfer_campaign_v144(
    dictionary_raw: bytes,
    verification_raw: bytes,
) -> FifthFamilyFactorBankTransferCampaignV144:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED":
        _fail("frozen V144 attempt failed; same preregistered identity will not be rerun")
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V144 campaign exists; same identity will not be rerun")
    registration = pre.freeze_fifth_family_factor_bank_transfer_preregistration_v144(
        dictionary_raw, verification_raw
    )
    preregistration = registration.to_document()
    document = build_fifth_family_factor_bank_transfer_campaign_document_v144(
        pre.campaign_config_v144(),
        preregistration_id=registration.preregistration_id,
        dictionary=preregistration["frozen_v141_factor_bank"],
        dictionary_verification=preregistration[
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
        _fail("frozen V144 campaign changed")
    _CACHE = FifthFamilyFactorBankTransferCampaignV144(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_RECORD_SHA256",
    "run_fifth_family_factor_bank_transfer_campaign_v144",
)
