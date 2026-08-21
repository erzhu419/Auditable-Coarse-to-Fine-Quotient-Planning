"""Producer for the preregistered V140 occurrence-factor-bank campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_occurrence_factor_bank_planning_preregistration_v140 as pre
from acfqp.occurrence_factor_bank_planning_campaign_core_v140 import (
    build_occurrence_factor_bank_planning_campaign_document_v140,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "FROZEN_PREREGISTERED_RESOURCE_CAP_FAILURE"
FAILURE_RECORD_SHA256 = (
    "3123b0babe9b11a732bb565c855cbc852ec16998d0aa36bbc18cbf10f279af02"
)


class ConstructionK7OccurrenceFactorBankPlanningCampaignV140Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OccurrenceFactorBankPlanningCampaignV140Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OccurrenceFactorBankPlanningCampaignV140:
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
            or pre.domains.extension_content_id_v140(
                pre.domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_CAMPAIGN_V140_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V140 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: OccurrenceFactorBankPlanningCampaignV140 | None = None


def run_occurrence_factor_bank_planning_campaign_v140(
    dictionary_raw: bytes, verification_raw: bytes
) -> OccurrenceFactorBankPlanningCampaignV140:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED":
        _fail("frozen V140 attempt failed; same preregistered identity will not be rerun")
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V140 campaign exists; same identity will not be rerun")
    registration = pre.freeze_occurrence_factor_bank_planning_preregistration_v140(
        dictionary_raw, verification_raw
    )
    preregistration = registration.to_document()
    dictionary = preregistration["frozen_v139_factor_bank"]
    verification = preregistration["frozen_v139_independent_verification"]
    document = build_occurrence_factor_bank_planning_campaign_document_v140(
        pre.campaign_config_v140(),
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
        _fail("frozen V140 campaign changed")
    _CACHE = OccurrenceFactorBankPlanningCampaignV140(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_RECORD_SHA256",
    "run_occurrence_factor_bank_planning_campaign_v140",
)
