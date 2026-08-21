"""Producer for the preregistered generic quotient compiler campaign V123."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_generic_quotient_compiler_preregistration_v123 as pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_quotient_compiler_campaign_core_v123 import (
    build_generic_quotient_compiler_campaign_document_v123,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
ATTEMPT_TERMINAL_STATE = "FROZEN_PREREGISTERED_RESOURCE_CAP_FAILURE"
FAILURE_RECORD_SHA256 = "84f32d6ed71ac0b4496d457662d5f750dacb9e77e37a51a17d6db6b6939b778e"


class ConstructionK7GenericQuotientCompilerCampaignV123Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7GenericQuotientCompilerCampaignV123Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class GenericQuotientCompilerCampaignV123:
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
            or pre.domains.extension_content_id_v123(
                pre.domains.CONSTRUCTION_K7_GENERIC_QUOTIENT_COMPILER_CAMPAIGN_V123_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V123 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: GenericQuotientCompilerCampaignV123 | None = None


def run_generic_quotient_compiler_campaign_v123(
    source_campaign_bytes: Mapping[str, bytes],
    v122_campaign_raw: bytes,
    v122_verification_raw: bytes,
) -> GenericQuotientCompilerCampaignV123:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if ATTEMPT_TERMINAL_STATE != "UNEXECUTED":
        _fail("frozen V123 attempt failed; same preregistered identity will not be rerun")
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V123 campaign exists; same identity will not be rerun")
    source_bytes = dict(source_campaign_bytes)
    try:
        registration = pre.verify_generic_quotient_compiler_preregistration_v123(
            pre.freeze_generic_quotient_compiler_preregistration_v123(
                source_bytes, v122_campaign_raw, v122_verification_raw
            ),
            source_bytes,
            v122_campaign_raw,
            v122_verification_raw,
        )
    except Exception as exc:
        _fail(f"V123 preregistered source evidence changed: {exc}")
    library = derive_artifact_factor_projection_v120(source_bytes)
    if library != registration.to_document()["artifact_factor_library"]:
        _fail("V123 preregistered factor library reconstruction changed")
    document = build_generic_quotient_compiler_campaign_document_v123(
        pre.campaign_config_v123(),
        preregistration_id=registration.preregistration_id,
        v122_campaign_id=pre.V122_CAMPAIGN_ID,
        v122_verification_id=pre.V122_VERIFICATION_ID,
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
        _fail("frozen V123 campaign changed")
    _CACHE = GenericQuotientCompilerCampaignV123(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_generic_quotient_compiler_campaign_v123")
