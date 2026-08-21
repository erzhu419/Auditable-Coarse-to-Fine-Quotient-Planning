"""Producer for the preregistered fair V129r1 sample-tax campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import (
    construction_k7_fair_unified_factor_prior_ablation_preregistration_v129r1 as pre,
)
from acfqp.fair_unified_factor_prior_ablation_campaign_core_v129r1 import (
    build_fair_unified_factor_prior_ablation_campaign_document_v129r1,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "f99bb57dd7d6210c8ee55193a603c8e7195690457df4de9a952fa59c71cda447"
EXPECTED_CANONICAL_BYTE_COUNT = 13_247_464
EXPECTED_CANONICAL_SHA256 = "2196206b7533f885b301ae5f8f68c58222dc34a2ad80691d3079d5214dcfe24c"


class ConstructionK7FairUnifiedFactorPriorAblationCampaignV129R1Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FairUnifiedFactorPriorAblationCampaignV129R1Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FairUnifiedFactorPriorAblationCampaignV129R1:
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
            or pre.domains.extension_content_id_v129r1(
                pre.domains.CONSTRUCTION_K7_FAIR_UNIFIED_FACTOR_PRIOR_ABLATION_CAMPAIGN_V129R1_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V129r1 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: FairUnifiedFactorPriorAblationCampaignV129R1 | None = None


def run_fair_unified_factor_prior_ablation_campaign_v129r1(
    source_campaign_bytes: Mapping[str, bytes],
    v128_campaign_raw: bytes,
    v128_verification_raw: bytes,
    failed_v129_raw: bytes,
) -> FairUnifiedFactorPriorAblationCampaignV129R1:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V129r1 campaign exists; same identity will not be rerun")
    source = dict(source_campaign_bytes)
    registration = (
        pre.freeze_fair_unified_factor_prior_ablation_preregistration_v129r1(
            source,
            v128_campaign_raw,
            v128_verification_raw,
            failed_v129_raw,
        )
    )
    library = derive_artifact_factor_projection_v120(source)
    if library != registration.to_document()["artifact_factor_library"]:
        _fail("V129r1 preregistered artifact library changed")
    document = build_fair_unified_factor_prior_ablation_campaign_document_v129r1(
        pre.campaign_config_v129r1(),
        preregistration_id=registration.preregistration_id,
        v128_campaign_id=pre.V128_CAMPAIGN_ID,
        v128_verification_id=pre.V128_VERIFICATION_ID,
        failed_v129_preregistration_id=pre.FAILED_V129_PREREGISTRATION_ID,
        failed_v129_artifact_sha256=pre.FAILED_V129_SHA256,
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
        _fail("frozen V129r1 campaign changed")
    _CACHE = FairUnifiedFactorPriorAblationCampaignV129R1(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "CAMPAIGN_ID",
    "run_fair_unified_factor_prior_ablation_campaign_v129r1",
)
