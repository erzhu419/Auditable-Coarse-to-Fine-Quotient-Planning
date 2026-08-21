"""Producer for the preregistered sequence-wide shield V100 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_sequence_wide_agreement_shielded_preregistration_v100 as pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.construction_k7_agreement_shielded_independent_verifier_v99 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V99_VERIFICATION_BYTE_COUNT,
    verify_agreement_shielded_campaign_bytes_v99,
)
from acfqp.construction_k7_post_dependency_source_library_v97 import (
    freeze_post_dependency_source_library_v97,
)
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.sequence_wide_agreement_shielded_campaign_core_v100 import (
    build_sequence_wide_agreement_shielded_campaign_document_v100,
)


CAMPAIGN_ID = "ce5886a86036c5f1163fcd98b5566c5dc5ca981405d433096944dc0d7c293a9a"
EXPECTED_CANONICAL_BYTE_COUNT = 4_250_703
EXPECTED_CANONICAL_SHA256 = "396cd4a9af3b0f25ce2449b341b15ac1bab69a02fe078ceacd93b36441df40d0"


class ConstructionK7SequenceWideAgreementShieldedCampaignV100Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SequenceWideAgreementShieldedCampaignV100Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SequenceWideAgreementShieldedCampaignV100:
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
            or pre.domains.extension_content_id_v100(
                pre.domains.CONSTRUCTION_K7_SEQUENCE_WIDE_AGREEMENT_SHIELDED_CAMPAIGN_V100_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V100 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError
        return value


_CACHE: SequenceWideAgreementShieldedCampaignV100 | None = None


def run_sequence_wide_agreement_shielded_campaign_v100(
    v96_campaign_raw: bytes,
    v96_verification_raw: bytes,
    v99_campaign_raw: bytes,
    v99_verification_raw: bytes,
) -> SequenceWideAgreementShieldedCampaignV100:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V100 campaign exists; same identity will not be rerun")
    preregistration = pre.verify_sequence_wide_agreement_shielded_preregistration_v100(
        pre.freeze_sequence_wide_agreement_shielded_preregistration_v100()
    )
    try:
        verified_v99 = verify_agreement_shielded_campaign_bytes_v99(
            v99_campaign_raw
        )
        verification = loads_canonical_json(v99_verification_raw)
    except Exception as exc:
        _fail(f"V100 frozen V99 failed predecessor is unreadable: {exc}")
    if (
        verified_v99.get("campaign_id") != pre.V99_CAMPAIGN_ID
        or verified_v99.get("registered_v99_gate_passed") is not False
        or type(verification) is not dict
        or canonical_json_bytes(verification) != v99_verification_raw
        or verification.get("verification_id") != pre.V99_VERIFICATION_ID
        or len(v99_verification_raw) != V99_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v99_verification_raw).hexdigest()
        != pre.V99_VERIFICATION_SHA256
    ):
        _fail("V100 frozen V99 failed predecessor evidence changed")
    source = freeze_post_dependency_source_library_v97(
        v96_campaign_raw, v96_verification_raw
    )
    if source.source_library_artifact_id != pre.SOURCE_LIBRARY_ARTIFACT_ID:
        _fail("V100 structural source library changed")
    residual = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    if residual.library_artifact_id != pre.V62_LIBRARY_ID:
        _fail("V100 residual library changed")
    document = build_sequence_wide_agreement_shielded_campaign_document_v100(
        pre.campaign_config_v100(),
        preregistration_id=preregistration.preregistration_id,
        v99_campaign_id=pre.V99_CAMPAIGN_ID,
        v99_verification_id=pre.V99_VERIFICATION_ID,
        source_library_artifact_id=source.source_library_artifact_id,
        factor_library=v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
        residual_library=residual.to_document()["compiled_library"],
        structural_prior_library=source.to_document()["compiled_structure_library"],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V100 campaign changed")
    _CACHE = SequenceWideAgreementShieldedCampaignV100(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_sequence_wide_agreement_shielded_campaign_v100")
