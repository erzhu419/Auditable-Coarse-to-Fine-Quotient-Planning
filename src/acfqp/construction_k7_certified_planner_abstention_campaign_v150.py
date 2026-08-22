"""Producer for the preregistered V150 certified-abstention campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_certified_planner_abstention_preregistration_v150 as pre
from acfqp.cross_domain_relational_factor_bank_campaign_core_v150 import (
    build_cross_domain_relational_factor_bank_campaign_document_v150,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "UNEXECUTED"
FAILURE_RECORD_SHA256: str | None = None


class ConstructionK7CertifiedPlannerAbstentionCampaignV150Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CertifiedPlannerAbstentionCampaignV150Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CertifiedPlannerAbstentionCampaignV150:
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
            or pre.domains.extension_content_id_v150(
                pre.domains.CONSTRUCTION_K7_CAMPAIGN_V150_DOMAIN, payload
            )
            != self.campaign_id
        ):
            _fail("V150 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: CertifiedPlannerAbstentionCampaignV150 | None = None


def run_certified_planner_abstention_campaign_v150(
    v149_preregistration_raw: bytes,
    v149_failure_raw: bytes,
) -> CertifiedPlannerAbstentionCampaignV150:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED":
        _fail("frozen V150 attempt is terminal; its identity will not be rerun")
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V150 campaign exists; its identity will not be rerun")
    registration = pre.freeze_certified_planner_abstention_preregistration_v150(
        v149_preregistration_raw, v149_failure_raw
    )
    registration_document = registration.to_document()
    source = registration_document["frozen_v149_preregistration"]
    bank_raw = canonical_json_bytes(source["frozen_v146_factor_bank"])
    verification_raw = canonical_json_bytes(
        source["frozen_v146_independent_verification"]
    )
    document = build_cross_domain_relational_factor_bank_campaign_document_v150(
        pre.campaign_config_v150(),
        preregistration_id=registration.preregistration_id,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    _CACHE = CertifiedPlannerAbstentionCampaignV150(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "ATTEMPT_TERMINAL_STATE",
    "CAMPAIGN_ID",
    "FAILURE_RECORD_SHA256",
    "run_certified_planner_abstention_campaign_v150",
)
