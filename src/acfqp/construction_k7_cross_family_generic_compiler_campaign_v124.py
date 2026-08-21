"""Producer for the preregistered V124 cross-family campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_cross_family_generic_compiler_preregistration_v124 as pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96
from acfqp.cross_family_generic_compiler_campaign_core_v124 import build_cross_family_generic_compiler_campaign_document_v124
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "d2da5c1f3271b362a584156fa7febe4d0cf2e715e14d9d4d453eeef471aa1d26"
EXPECTED_CANONICAL_BYTE_COUNT = 1_830_635
EXPECTED_CANONICAL_SHA256 = "b1a1f7e40747275077ce32e3147a48bef2235de23bc3b983e86b79d36a32eb49"


class ConstructionK7CrossFamilyGenericCompilerCampaignV124Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CrossFamilyGenericCompilerCampaignV124Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CrossFamilyGenericCompilerCampaignV124:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if self._issuer is not _ISSUER or canonical_json_bytes(document) != self.canonical_bytes or document.get("campaign_id") != self.campaign_id or pre.domains.extension_content_id_v124(pre.domains.CONSTRUCTION_K7_CROSS_FAMILY_GENERIC_COMPILER_CAMPAIGN_V124_DOMAIN, payload) != self.campaign_id:
            _fail("V124 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: CrossFamilyGenericCompilerCampaignV124 | None = None


def run_cross_family_generic_compiler_campaign_v124(
    source_campaign_bytes: Mapping[str, bytes],
    v123r1_campaign_raw: bytes,
    v123r1_verification_raw: bytes,
) -> CrossFamilyGenericCompilerCampaignV124:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V124 campaign exists; same identity will not be rerun")
    source = dict(source_campaign_bytes)
    registration = pre.freeze_cross_family_generic_compiler_preregistration_v124(source, v123r1_campaign_raw, v123r1_verification_raw)
    library = derive_artifact_factor_projection_v120(source)
    if library != registration.to_document()["artifact_factor_library"]:
        _fail("V124 preregistered artifact library changed")
    document = build_cross_family_generic_compiler_campaign_document_v124(
        pre.campaign_config_v124(),
        preregistration_id=registration.preregistration_id,
        v123r1_campaign_id=pre.V123R1_CAMPAIGN_ID,
        v123r1_verification_id=pre.V123R1_VERIFICATION_ID,
        artifact_factor_library=library,
        source_campaign_bytes=source,
        strict_complete_factor_library=v96.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (identity != CAMPAIGN_ID or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256):
        _fail("frozen V124 campaign changed")
    _CACHE = CrossFamilyGenericCompilerCampaignV124(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_cross_family_generic_compiler_campaign_v124")
