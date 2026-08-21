"""Producer for the preregistered V142r1 occurrence-factor-bank-update campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_occurrence_factor_bank_update_planning_preregistration_v142r1 as pre
from acfqp.occurrence_factor_bank_update_planning_campaign_core_v142r1 import (
    build_occurrence_factor_bank_update_planning_campaign_document_v142r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "bce11c716fe7d8d47e7181cfab8a4aa00204c015794bb62c7e6376278b94b19a"
EXPECTED_CANONICAL_BYTE_COUNT = 7_977_801
EXPECTED_CANONICAL_SHA256 = (
    "c470ec0f47637c5911c95bf13c67ad96d43d40a4cebea24dcf9aa077de622c47"
)
ATTEMPT_TERMINAL_STATE = "UNEXECUTED"
FAILURE_RECORD_SHA256 = "0" * 64


class ConstructionK7OccurrenceFactorBankUpdatePlanningCampaignV142r1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OccurrenceFactorBankUpdatePlanningCampaignV142r1Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OccurrenceFactorBankUpdatePlanningCampaignV142r1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains.extension_content_id_v142r1(
                pre.domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_UPDATE_CAMPAIGN_V142R1_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V142r1 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: OccurrenceFactorBankUpdatePlanningCampaignV142r1 | None = None


def run_occurrence_factor_bank_update_planning_campaign_v142r1(
    dictionary_raw: bytes,
    verification_raw: bytes,
    v140_failure_raw: bytes,
    v142_failure_raw: bytes,
) -> OccurrenceFactorBankUpdatePlanningCampaignV142r1:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED":
        _fail("frozen V142r1 attempt failed; same preregistered identity will not be rerun")
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V142r1 campaign exists; same identity will not be rerun")
    registration = pre.freeze_occurrence_factor_bank_update_planning_preregistration_v142r1(
        dictionary_raw, verification_raw, v140_failure_raw, v142_failure_raw
    )
    preregistration = registration.to_document()
    dictionary = preregistration["frozen_v141_factor_bank"]
    verification = preregistration["frozen_v141_independent_verification"]
    document = build_occurrence_factor_bank_update_planning_campaign_document_v142r1(
        pre.campaign_config_v142r1(),
        preregistration_id=registration.preregistration_id,
        dictionary=dictionary,
        dictionary_verification=verification,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V142r1 campaign changed")
    _CACHE = OccurrenceFactorBankUpdatePlanningCampaignV142r1(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_RECORD_SHA256",
    "run_occurrence_factor_bank_update_planning_campaign_v142r1",
)
