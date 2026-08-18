"""Producer for the preregistered fresh V63r1 total residual campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_total_residual_sample_tax_preregistration_v63r1 as pre
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.total_residual_sample_tax_campaign_core_v63r1 import (
    build_total_residual_sample_tax_campaign_document_v63r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "1e9f4fbdb13e9c7c477ec213fec3d0cda09d4b0af7698d8c7e774ebdbf320db8"
EXPECTED_CANONICAL_BYTE_COUNT = 1_524_901
EXPECTED_CANONICAL_SHA256 = "02d2149b39043e28354dc57e36a03cc3905d8266dbf25015486c0bda0c220e29"
REGISTERED_FAILURE_ID = ""


class ConstructionK7TotalResidualSampleTaxCampaignV63R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TotalResidualSampleTaxCampaignV63R1Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TotalResidualSampleTaxCampaignV63R1:
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
            or pre.domains.extension_content_id_v63r1(
                pre.V63R1_DOMAINS["campaign"], payload
            )
            != self.campaign_id
        ):
            _fail("V63r1 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: TotalResidualSampleTaxCampaignV63R1 | None = None


def run_total_residual_sample_tax_campaign_v63r1() -> TotalResidualSampleTaxCampaignV63R1:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(f"V63r1 registered failure is frozen: {REGISTERED_FAILURE_ID}")
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_total_residual_sample_tax_preregistration_v63r1(
        pre.freeze_total_residual_sample_tax_preregistration_v63r1()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][
        "source_facts"
    ]:
        _fail("V63r1 preregistered source closure changed before execution")
    library = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    if library.library_artifact_id != pre.V62_LIBRARY_ARTIFACT_ID:
        _fail("V63r1 residual library predecessor changed")
    document = build_total_residual_sample_tax_campaign_document_v63r1(
        pre.campaign_config_v63r1(),
        preregistration.preregistration_id,
        pre.FAILED_V63_REGISTERED_FAILURE_ID,
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
        _fail("frozen V63r1 campaign changed")
    _CACHE = TotalResidualSampleTaxCampaignV63R1(_ISSUER, raw, identity)
    return _CACHE


def verify_total_residual_sample_tax_campaign_v63r1(
    value: Any,
) -> TotalResidualSampleTaxCampaignV63R1:
    if type(value) is not TotalResidualSampleTaxCampaignV63R1:
        _fail("V63r1 campaign rejects foreign values")
    value.__post_init__()
    expected = run_total_residual_sample_tax_campaign_v63r1()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V63r1 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "run_total_residual_sample_tax_campaign_v63r1",
    "verify_total_residual_sample_tax_campaign_v63r1",
)
