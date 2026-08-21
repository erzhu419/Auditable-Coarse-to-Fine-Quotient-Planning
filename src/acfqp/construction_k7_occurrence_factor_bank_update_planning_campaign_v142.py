"""Producer for the preregistered V142 occurrence-factor-bank-update campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_occurrence_factor_bank_update_planning_preregistration_v142 as pre
from acfqp.occurrence_factor_bank_update_planning_campaign_core_v142 import (
    build_occurrence_factor_bank_update_planning_campaign_document_v142,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "UNEXECUTED"
FAILURE_RECORD_SHA256 = "0" * 64


class ConstructionK7OccurrenceFactorBankUpdatePlanningCampaignV142Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OccurrenceFactorBankUpdatePlanningCampaignV142Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OccurrenceFactorBankUpdatePlanningCampaignV142:
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
            or pre.domains.extension_content_id_v142(
                pre.domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_UPDATE_CAMPAIGN_V142_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V142 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: OccurrenceFactorBankUpdatePlanningCampaignV142 | None = None


def run_occurrence_factor_bank_update_planning_campaign_v142(
    dictionary_raw: bytes, verification_raw: bytes, v140_failure_raw: bytes
) -> OccurrenceFactorBankUpdatePlanningCampaignV142:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED":
        _fail("frozen V142 attempt failed; same preregistered identity will not be rerun")
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V142 campaign exists; same identity will not be rerun")
    registration = pre.freeze_occurrence_factor_bank_update_planning_preregistration_v142(
        dictionary_raw, verification_raw, v140_failure_raw
    )
    preregistration = registration.to_document()
    dictionary = preregistration["frozen_v141_factor_bank"]
    verification = preregistration["frozen_v141_independent_verification"]
    document = build_occurrence_factor_bank_update_planning_campaign_document_v142(
        pre.campaign_config_v142(),
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
        _fail("frozen V142 campaign changed")
    _CACHE = OccurrenceFactorBankUpdatePlanningCampaignV142(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_RECORD_SHA256",
    "run_occurrence_factor_bank_update_planning_campaign_v142",
)
