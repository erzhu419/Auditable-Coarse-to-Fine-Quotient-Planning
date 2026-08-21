"""Producer for the preregistered V92 target campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_version_space_target_preregistration_v92 as pre
from acfqp.construction_k7_prior_only_occurrence_source_campaign_v91r2 import (
    CAMPAIGN_ID as V91R2_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V91R2_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V91R2_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_source_model_acceptance_v91r3 import (
    ACCEPTANCE_ID as V91R3_ACCEPTANCE_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V91R3_ACCEPTANCE_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V91R3_ACCEPTANCE_SHA256,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.version_space_target_campaign_core_v92 import (
    build_version_space_target_campaign_document_v92,
)


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7VersionSpaceTargetCampaignV92Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7VersionSpaceTargetCampaignV92Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class VersionSpaceTargetCampaignV92:
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
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains.extension_content_id_v92(
                pre.domains.CONSTRUCTION_K7_VERSION_SPACE_TARGET_CAMPAIGN_V92_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V92 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: VersionSpaceTargetCampaignV92 | None = None


def run_version_space_target_campaign_v92(
    source_campaign_raw: bytes,
    source_acceptance_raw: bytes,
) -> VersionSpaceTargetCampaignV92:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V92 campaign exists; same identity will not be rerun")
    if (
        type(source_campaign_raw) is not bytes
        or len(source_campaign_raw) != V91R2_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(source_campaign_raw).hexdigest()
        != V91R2_CAMPAIGN_SHA256
        or type(source_acceptance_raw) is not bytes
        or len(source_acceptance_raw) != V91R3_ACCEPTANCE_BYTE_COUNT
        or hashlib.sha256(source_acceptance_raw).hexdigest()
        != V91R3_ACCEPTANCE_SHA256
    ):
        _fail("V92 frozen predecessor bytes changed")
    source = loads_canonical_json(source_campaign_raw)
    acceptance = loads_canonical_json(source_acceptance_raw)
    if (
        source.get("campaign_id") != V91R2_CAMPAIGN_ID
        or acceptance.get("acceptance_id") != V91R3_ACCEPTANCE_ID
        or acceptance.get("v91r2_campaign_id") != source["campaign_id"]
    ):
        _fail("V92 predecessor identity join changed")
    preregistration = pre.verify_version_space_target_preregistration_v92(
        pre.freeze_version_space_target_preregistration_v92()
    )
    document = build_version_space_target_campaign_document_v92(
        pre.campaign_config_v92(),
        preregistration_id=preregistration.preregistration_id,
        source_acceptance_id=acceptance["acceptance_id"],
        source_acceptance_verification_id=pre.V91R3_VERIFICATION_ID,
        source_campaign_id=source["campaign_id"],
        source_campaign_verification_id=pre.V91R2_VERIFICATION_ID,
        source_accounting=source["accounting"],
        model=acceptance["accepted_joint_successor_version_space_model"],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V92 campaign changed")
    _CACHE = VersionSpaceTargetCampaignV92(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_version_space_target_campaign_v92")
