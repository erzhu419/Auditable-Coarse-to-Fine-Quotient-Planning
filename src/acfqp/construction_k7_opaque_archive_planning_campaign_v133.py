"""Producer for the preregistered V133 opaque-dictionary planning campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_opaque_archive_planning_preregistration_v133 as pre
from acfqp.opaque_archive_planning_campaign_core_v133 import (
    build_opaque_archive_planning_campaign_document_v133,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "010f13f7cb3981524baec4cedcf245d707ded136d440d8b29a6bd848de566874"
EXPECTED_CANONICAL_BYTE_COUNT = 17_890_540
EXPECTED_CANONICAL_SHA256 = "98e805ab53095f089e1dca3453c8ce2d8ddcd3a690d87395aac9e21e6b3c3d5e"


class ConstructionK7OpaqueArchivePlanningCampaignV133Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OpaqueArchivePlanningCampaignV133Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpaqueArchivePlanningCampaignV133:
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
            or pre.domains.extension_content_id_v133(
                pre.domains.CONSTRUCTION_K7_OPAQUE_ARCHIVE_PLANNING_CAMPAIGN_V133_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V133 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: OpaqueArchivePlanningCampaignV133 | None = None


def run_opaque_archive_planning_campaign_v133(
    dictionary_raw: bytes, verification_raw: bytes
) -> OpaqueArchivePlanningCampaignV133:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V133 campaign exists; same identity will not be rerun")
    registration = pre.freeze_opaque_archive_planning_preregistration_v133(
        dictionary_raw, verification_raw
    )
    preregistration = registration.to_document()
    dictionary = preregistration["frozen_v132_dictionary"]
    verification = preregistration["frozen_v132_independent_verification"]
    document = build_opaque_archive_planning_campaign_document_v133(
        pre.campaign_config_v133(),
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
        _fail("frozen V133 campaign changed")
    _CACHE = OpaqueArchivePlanningCampaignV133(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_opaque_archive_planning_campaign_v133")
