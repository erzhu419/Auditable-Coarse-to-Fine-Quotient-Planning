"""Producer for the preregistered fresh V63 residual sample-tax campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_residual_sample_tax_preregistration_v63 as pre
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.residual_factor_sample_tax_campaign_core_v63 import (
    build_residual_factor_sample_tax_campaign_document_v63,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
REGISTERED_FAILURE_ID = "716b0fba8968318c284a0840e2f109c861f819d5c52a177fdd41efee88c2fae0"


def registered_failure_document_v63() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.residual_sample_tax_registered_failure.v63",
        "preregistration_id": pre.PREREGISTRATION_ID,
        "failure_phase": "ADAPTIVE_RESIDUAL_ACQUISITION",
        "error_type": "GenericAdaptiveResidualFactorAcquisitionV19Error",
        "error_message": "V19 adaptive residual acquisition did not stop on available evidence",
        "worker_occurrence_identity_returned": False,
        "partial_campaign_artifact_present": False,
        "same_identity_rerun_allowed": False,
    }
    identity = pre.domains.extension_content_id_v63(
        pre.V63_DOMAINS["campaign"], payload
    )
    if identity != REGISTERED_FAILURE_ID:
        _fail("V63 registered failure identity changed")
    return {**payload, "registered_failure_id": identity}


class ConstructionK7ResidualSampleTaxCampaignV63Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ResidualSampleTaxCampaignV63Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ResidualSampleTaxCampaignV63:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains.extension_content_id_v63(
                pre.V63_DOMAINS["campaign"], payload
            )
            != self.campaign_id
        ):
            _fail("V63 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ResidualSampleTaxCampaignV63 | None = None


def run_residual_sample_tax_campaign_v63() -> ResidualSampleTaxCampaignV63:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(f"V63 registered failure is frozen: {REGISTERED_FAILURE_ID}")
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_residual_sample_tax_preregistration_v63(
        pre.freeze_residual_sample_tax_preregistration_v63()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][
        "source_facts"
    ]:
        _fail("V63 preregistered source closure changed before execution")
    library = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    if library.library_artifact_id != pre.V62_LIBRARY_ARTIFACT_ID:
        _fail("V63 frozen residual library predecessor changed")
    document = build_residual_factor_sample_tax_campaign_document_v63(
        pre.campaign_config_v63(),
        preregistration.preregistration_id,
        pre.previous.previous.previous.FACTOR_LIBRARY,
        library.to_document(),
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V63 campaign changed")
    _CACHE = ResidualSampleTaxCampaignV63(_ISSUER, raw, identity)
    return _CACHE


def verify_residual_sample_tax_campaign_v63(
    value: Any,
) -> ResidualSampleTaxCampaignV63:
    if type(value) is not ResidualSampleTaxCampaignV63:
        _fail("V63 campaign rejects foreign values")
    value.__post_init__()
    expected = run_residual_sample_tax_campaign_v63()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V63 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "REGISTERED_FAILURE_ID",
    "registered_failure_document_v63",
    "run_residual_sample_tax_campaign_v63",
    "verify_residual_sample_tax_campaign_v63",
)
