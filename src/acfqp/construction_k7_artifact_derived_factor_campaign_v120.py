"""Producer for the preregistered artifact-derived factor campaign V120."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_artifact_derived_factor_preregistration_v120 as pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.artifact_derived_factor_campaign_core_v120 import (
    build_artifact_derived_factor_campaign_document_v120,
)
from acfqp.construction_k7_source_unseen_residual_independent_verifier_v119 import (
    freeze_source_unseen_residual_verification_v119,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7ArtifactDerivedFactorCampaignV120Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ArtifactDerivedFactorCampaignV120Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ArtifactDerivedFactorCampaignV120:
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
            or pre.domains.extension_content_id_v120(
                pre.domains.CONSTRUCTION_K7_ARTIFACT_DERIVED_FACTOR_CAMPAIGN_V120_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V120 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: ArtifactDerivedFactorCampaignV120 | None = None


def run_artifact_derived_factor_campaign_v120(
    source_campaign_bytes: Mapping[str, bytes],
    v119_verification_raw: bytes,
) -> ArtifactDerivedFactorCampaignV120:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V120 campaign exists; same identity will not be rerun")
    source_bytes = dict(source_campaign_bytes)
    try:
        registration = pre.verify_artifact_derived_factor_preregistration_v120(
            pre.freeze_artifact_derived_factor_preregistration_v120(source_bytes),
            source_bytes,
        )
    except Exception as exc:
        _fail(f"V120 preregistered source evidence changed: {exc}")
    v119_raw = source_bytes.get("V119")
    try:
        verification = loads_canonical_json(v119_verification_raw)
    except Exception as exc:
        _fail(f"V120 frozen V119 verification is unreadable: {exc}")
    if (
        type(v119_raw) is not bytes
        or len(v119_raw) != pre.V119_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v119_raw).hexdigest() != pre.V119_CAMPAIGN_SHA256
        or canonical_json_bytes(verification) != v119_verification_raw
        or len(v119_verification_raw) != pre.V119_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v119_verification_raw).hexdigest()
        != pre.V119_VERIFICATION_SHA256
        or verification.get("verification_id") != pre.V119_VERIFICATION_ID
        or verification.get("registered_gate_independently_verified") is not True
        or freeze_source_unseen_residual_verification_v119(v119_raw)
        != v119_verification_raw
    ):
        _fail("V120 frozen successful V119 predecessor changed")
    library = derive_artifact_factor_projection_v120(source_bytes)
    if library != registration.to_document()["artifact_factor_library"]:
        _fail("V120 preregistered factor library reconstruction changed")
    document = build_artifact_derived_factor_campaign_document_v120(
        pre.campaign_config_v120(),
        preregistration_id=registration.preregistration_id,
        v119_campaign_id=pre.V119_CAMPAIGN_ID,
        v119_verification_id=pre.V119_VERIFICATION_ID,
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
        _fail("frozen V120 campaign changed")
    _CACHE = ArtifactDerivedFactorCampaignV120(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_artifact_derived_factor_campaign_v120")
