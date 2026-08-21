"""Producer for preregistered opportunity-independent V121r1."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_generic_subprogram_preregistration_v121r1 as pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_subprogram_opportunity_independent_campaign_core_v121r1 import (
    build_opportunity_independent_campaign_document_v121r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7GenericSubprogramCampaignV121R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7GenericSubprogramCampaignV121R1Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class GenericSubprogramCampaignV121R1:
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
            or pre.domains.extension_content_id_v121r1(
                pre.domains.CONSTRUCTION_K7_GENERIC_SUBPROGRAM_CAMPAIGN_V121R1_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V121r1 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: GenericSubprogramCampaignV121R1 | None = None


def run_generic_subprogram_campaign_v121r1(
    source_campaign_bytes: Mapping[str, bytes], failed_v121_raw: bytes
) -> GenericSubprogramCampaignV121R1:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V121r1 campaign exists; same identity will not be rerun")
    source_bytes = dict(source_campaign_bytes)
    try:
        registration = pre.verify_generic_subprogram_preregistration_v121r1(
            pre.freeze_generic_subprogram_preregistration_v121r1(
                source_bytes, failed_v121_raw
            ),
            source_bytes,
            failed_v121_raw,
        )
    except Exception as exc:
        _fail(f"V121r1 preregistered evidence changed: {exc}")
    if (
        len(failed_v121_raw) != pre.FAILED_V121_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(failed_v121_raw).hexdigest()
        != pre.FAILED_V121_CAMPAIGN_SHA256
    ):
        _fail("V121r1 failed predecessor bytes changed")
    library = derive_artifact_factor_projection_v120(source_bytes)
    if library != registration.to_document()["artifact_factor_library"]:
        _fail("V121r1 preregistered factor library changed")
    document = build_opportunity_independent_campaign_document_v121r1(
        pre.campaign_config_v121r1(),
        preregistration_id=registration.preregistration_id,
        failed_v121_campaign_id=pre.FAILED_V121_CAMPAIGN_ID,
        artifact_factor_library=library,
        source_campaign_bytes=source_bytes,
        strict_complete_factor_library=(
            v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V121r1 campaign changed")
    _CACHE = GenericSubprogramCampaignV121R1(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_generic_subprogram_campaign_v121r1")
