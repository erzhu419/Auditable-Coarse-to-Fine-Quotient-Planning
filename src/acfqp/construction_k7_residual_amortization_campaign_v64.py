"""Producer for the preregistered V64 residual-prior amortization campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_residual_amortization_preregistration_v64 as pre
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.residual_prior_amortization_campaign_core_v64 import (
    build_residual_prior_amortization_campaign_document_v64,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "b995c21c6e9b6f558d61cac084f9f8dd03eb694ffc0d026ace224e0abb175647"
EXPECTED_CANONICAL_BYTE_COUNT = 8_545_006
EXPECTED_CANONICAL_SHA256 = "deb8260b7deb57a168309579e79b23942775f667523f025d44ea7f91b8c4e195"
REGISTERED_FAILURE_ID = ""


class ConstructionK7ResidualAmortizationCampaignV64Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ResidualAmortizationCampaignV64Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ResidualAmortizationCampaignV64:
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
            or pre.domains.extension_content_id_v64(
                pre.V64_DOMAINS["campaign"], payload
            )
            != self.campaign_id
        ):
            _fail("V64 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ResidualAmortizationCampaignV64 | None = None


def run_residual_amortization_campaign_v64() -> ResidualAmortizationCampaignV64:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(f"V64 registered failure is frozen: {REGISTERED_FAILURE_ID}")
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_residual_amortization_preregistration_v64(
        pre.freeze_residual_amortization_preregistration_v64()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][
        "source_facts"
    ]:
        _fail("V64 preregistered source closure changed before execution")
    library = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    if library.library_artifact_id != pre.V62_LIBRARY_ID:
        _fail("V64 residual library predecessor changed")
    document = build_residual_prior_amortization_campaign_document_v64(
        pre.campaign_config_v64(),
        preregistration.preregistration_id,
        pre.FAILED_V63_ID,
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
        _fail("frozen V64 campaign changed")
    _CACHE = ResidualAmortizationCampaignV64(_ISSUER, raw, identity)
    return _CACHE


def verify_residual_amortization_campaign_v64(
    value: Any,
) -> ResidualAmortizationCampaignV64:
    if type(value) is not ResidualAmortizationCampaignV64:
        _fail("V64 campaign rejects foreign values")
    value.__post_init__()
    expected = run_residual_amortization_campaign_v64()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V64 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "run_residual_amortization_campaign_v64",
    "verify_residual_amortization_campaign_v64",
)
