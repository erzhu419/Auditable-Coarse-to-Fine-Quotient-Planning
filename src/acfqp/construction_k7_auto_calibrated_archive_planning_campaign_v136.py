"""Producer for the preregistered V136 auto-calibrated archive planning campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_auto_calibrated_archive_planning_preregistration_v136 as pre
from acfqp.auto_calibrated_archive_planning_campaign_core_v136 import (
    build_auto_calibrated_archive_planning_campaign_document_v136,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7AutoCalibratedArchivePlanningCampaignV136Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AutoCalibratedArchivePlanningCampaignV136Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AutoCalibratedArchivePlanningCampaignV136:
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
            or pre.domains.extension_content_id_v136(
                pre.domains.CONSTRUCTION_K7_AUTO_CALIBRATED_ARCHIVE_CAMPAIGN_V136_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V136 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: AutoCalibratedArchivePlanningCampaignV136 | None = None


def run_auto_calibrated_archive_planning_campaign_v136(
    dictionary_raw: bytes, verification_raw: bytes
) -> AutoCalibratedArchivePlanningCampaignV136:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V136 campaign exists; same identity will not be rerun")
    registration = pre.freeze_auto_calibrated_archive_planning_preregistration_v136(
        dictionary_raw, verification_raw
    )
    preregistration = registration.to_document()
    dictionary = preregistration["frozen_v135_dictionary"]
    verification = preregistration["frozen_v135_independent_verification"]
    document = build_auto_calibrated_archive_planning_campaign_document_v136(
        pre.campaign_config_v136(),
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
        _fail("frozen V136 campaign changed")
    _CACHE = AutoCalibratedArchivePlanningCampaignV136(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_auto_calibrated_archive_planning_campaign_v136")
