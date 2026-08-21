"""Producer for the preregistered V130 normalized code-prior campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_normalized_mixture_factor_prior_preregistration_v130 as pre
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.normalized_mixture_factor_prior_campaign_core_v130 import (
    build_normalized_mixture_factor_prior_campaign_document_v130,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "96447e0821d622b044daaffa8f9e0c8b0e1814a799b9b40f438ce5b4b8d55cbe"
EXPECTED_CANONICAL_BYTE_COUNT = 11_815_506
EXPECTED_CANONICAL_SHA256 = "9c179b4c9b54fa885d85c58608879c8b39649dd5cc8881e2d5a1cd6cfc90a433"


class ConstructionK7NormalizedMixtureFactorPriorCampaignV130Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7NormalizedMixtureFactorPriorCampaignV130Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class NormalizedMixtureFactorPriorCampaignV130:
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
            or pre.domains.extension_content_id_v130(
                pre.domains.CONSTRUCTION_K7_NORMALIZED_MIXTURE_FACTOR_CAMPAIGN_V130_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V130 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: NormalizedMixtureFactorPriorCampaignV130 | None = None


def run_normalized_mixture_factor_prior_campaign_v130(
    source_campaign_bytes: Mapping[str, bytes],
    v129r1_campaign_raw: bytes,
    v129r1_verification_raw: bytes,
) -> NormalizedMixtureFactorPriorCampaignV130:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V130 campaign exists; same identity will not be rerun")
    source = dict(source_campaign_bytes)
    registration = pre.freeze_normalized_mixture_factor_prior_preregistration_v130(
        source, v129r1_campaign_raw, v129r1_verification_raw
    )
    library = derive_artifact_factor_projection_v120(source)
    if library != registration.to_document()["artifact_factor_library"]:
        _fail("V130 preregistered artifact library changed")
    document = build_normalized_mixture_factor_prior_campaign_document_v130(
        pre.campaign_config_v130(),
        preregistration_id=registration.preregistration_id,
        v129r1_campaign_id=pre.V129R1_CAMPAIGN_ID,
        v129r1_verification_id=pre.V129R1_VERIFICATION_ID,
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
        _fail("frozen V130 campaign changed")
    _CACHE = NormalizedMixtureFactorPriorCampaignV130(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_normalized_mixture_factor_prior_campaign_v130")
