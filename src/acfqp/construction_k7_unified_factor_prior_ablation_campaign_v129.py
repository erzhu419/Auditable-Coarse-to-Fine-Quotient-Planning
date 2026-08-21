"""Producer for the preregistered V129 matched sample-tax ablation."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Mapping, NoReturn

from acfqp import construction_k7_unified_factor_prior_ablation_preregistration_v129 as pre
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.unified_factor_prior_ablation_campaign_core_v129 import build_unified_factor_prior_ablation_campaign_document_v129


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7UnifiedFactorPriorAblationCampaignV129Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7UnifiedFactorPriorAblationCampaignV129Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class UnifiedFactorPriorAblationCampaignV129:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self):
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains.extension_content_id_v129(
                pre.domains.CONSTRUCTION_K7_UNIFIED_FACTOR_PRIOR_ABLATION_CAMPAIGN_V129_DOMAIN,
                payload,
            ) != self.campaign_id
        ):
            _fail("V129 campaign bytes or issuer changed")

    def to_document(self):
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def run_unified_factor_prior_ablation_campaign_v129(
    source_campaign_bytes: Mapping[str, bytes],
    v128_campaign_raw: bytes,
    v128_verification_raw: bytes,
):
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V129 campaign exists; same identity will not be rerun")
    source = dict(source_campaign_bytes)
    registration = pre.freeze_unified_factor_prior_ablation_preregistration_v129(
        source, v128_campaign_raw, v128_verification_raw
    )
    library = derive_artifact_factor_projection_v120(source)
    if library != registration.to_document()["artifact_factor_library"]:
        _fail("V129 preregistered artifact library changed")
    document = build_unified_factor_prior_ablation_campaign_document_v129(
        pre.campaign_config_v129(),
        preregistration_id=registration.preregistration_id,
        v128_campaign_id=pre.V128_CAMPAIGN_ID,
        v128_verification_id=pre.V128_VERIFICATION_ID,
        artifact_factor_library=library,
        source_campaign_bytes=source,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V129 campaign changed")
    _CACHE = UnifiedFactorPriorAblationCampaignV129(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_unified_factor_prior_ablation_campaign_v129")
