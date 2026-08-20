"""Producer for the preregistered V69 source-complete campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_source_complete_relational_preregistration_v69 as pre
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.source_complete_relational_campaign_core_v69 import (
    build_source_complete_relational_campaign_document_v69,
)


CAMPAIGN_ID = "3a7655580b14f00a6833599f676c7b03719ae59cb5c48d2677545b47e38ad7a8"
EXPECTED_CANONICAL_BYTE_COUNT = 2_328_789
EXPECTED_CANONICAL_SHA256 = "e69aa4207ecc1acec1dc0c00c0361063a4917bd501be7df339e8fb43356eda17"
REGISTERED_FAILURE_ID = ""


class ConstructionK7SourceCompleteRelationalCampaignV69Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SourceCompleteRelationalCampaignV69Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SourceCompleteRelationalCampaignV69:
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
            or pre.domains.extension_content_id_v69(
                pre.domains.CONSTRUCTION_K7_SOURCE_COMPLETE_RELATIONAL_CAMPAIGN_V69_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V69 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: SourceCompleteRelationalCampaignV69 | None = None


def run_source_complete_relational_campaign_v69() -> SourceCompleteRelationalCampaignV69:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(f"V69 registered failure is frozen: {REGISTERED_FAILURE_ID}")
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_source_complete_relational_preregistration_v69(
        pre.freeze_source_complete_relational_preregistration_v69()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][
        "source_facts"
    ]:
        _fail("V69 preregistered source closure changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    if residual_artifact.library_artifact_id != pre.V62_LIBRARY_ID:
        _fail("V69 residual library predecessor changed")
    document = build_source_complete_relational_campaign_document_v69(
        pre.campaign_config_v69(),
        preregistration.preregistration_id,
        pre.V68_CAMPAIGN_ID,
        pre.V68_VERIFICATION_ID,
        pre.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
        residual_artifact.to_document()["compiled_library"],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V69 campaign changed")
    _CACHE = SourceCompleteRelationalCampaignV69(_ISSUER, raw, identity)
    return _CACHE


def verify_source_complete_relational_campaign_v69(
    value: Any,
) -> SourceCompleteRelationalCampaignV69:
    if type(value) is not SourceCompleteRelationalCampaignV69:
        _fail("V69 campaign rejects foreign values")
    value.__post_init__()
    expected = run_source_complete_relational_campaign_v69()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V69 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "run_source_complete_relational_campaign_v69",
    "verify_source_complete_relational_campaign_v69",
)
