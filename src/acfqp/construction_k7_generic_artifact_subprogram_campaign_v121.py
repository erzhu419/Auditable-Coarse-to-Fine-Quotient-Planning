"""Producer for the preregistered generic artifact-subprogram campaign V121."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_generic_artifact_subprogram_preregistration_v121 as pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.construction_k7_artifact_derived_factor_independent_verifier_v120 import (
    freeze_artifact_derived_factor_verification_v120,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_artifact_subprogram_campaign_core_v121 import (
    build_generic_artifact_subprogram_campaign_document_v121,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7GenericArtifactSubprogramCampaignV121Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7GenericArtifactSubprogramCampaignV121Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class GenericArtifactSubprogramCampaignV121:
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
            or pre.domains.extension_content_id_v121(
                pre.domains.CONSTRUCTION_K7_GENERIC_ARTIFACT_SUBPROGRAM_CAMPAIGN_V121_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V121 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: GenericArtifactSubprogramCampaignV121 | None = None


def run_generic_artifact_subprogram_campaign_v121(
    source_campaign_bytes: Mapping[str, bytes],
    v120_campaign_raw: bytes,
    v120_verification_raw: bytes,
) -> GenericArtifactSubprogramCampaignV121:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V121 campaign exists; same identity will not be rerun")
    source_bytes = dict(source_campaign_bytes)
    try:
        registration = pre.verify_generic_artifact_subprogram_preregistration_v121(
            pre.freeze_generic_artifact_subprogram_preregistration_v121(source_bytes),
            source_bytes,
        )
    except Exception as exc:
        _fail(f"V121 preregistered source evidence changed: {exc}")
    try:
        predecessor = loads_canonical_json(v120_campaign_raw)
        verification = loads_canonical_json(v120_verification_raw)
    except Exception as exc:
        _fail(f"V121 frozen V120 predecessor is unreadable: {exc}")
    if (
        canonical_json_bytes(predecessor) != v120_campaign_raw
        or len(v120_campaign_raw) != pre.V120_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v120_campaign_raw).hexdigest() != pre.V120_CAMPAIGN_SHA256
        or predecessor.get("campaign_id") != pre.V120_CAMPAIGN_ID
        or canonical_json_bytes(verification) != v120_verification_raw
        or len(v120_verification_raw) != pre.V120_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v120_verification_raw).hexdigest()
        != pre.V120_VERIFICATION_SHA256
        or verification.get("verification_id") != pre.V120_VERIFICATION_ID
        or verification.get("registered_gate_independently_verified") is not True
        or freeze_artifact_derived_factor_verification_v120(
            v120_campaign_raw, source_bytes
        )
        != v120_verification_raw
    ):
        _fail("V121 frozen successful V120 evidence changed")
    library = derive_artifact_factor_projection_v120(source_bytes)
    if library != registration.to_document()["artifact_factor_library"]:
        _fail("V121 preregistered factor library reconstruction changed")
    document = build_generic_artifact_subprogram_campaign_document_v121(
        pre.campaign_config_v121(),
        preregistration_id=registration.preregistration_id,
        v120_campaign_id=pre.V120_CAMPAIGN_ID,
        v120_verification_id=pre.V120_VERIFICATION_ID,
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
        _fail("frozen V121 campaign changed")
    _CACHE = GenericArtifactSubprogramCampaignV121(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_generic_artifact_subprogram_campaign_v121")
