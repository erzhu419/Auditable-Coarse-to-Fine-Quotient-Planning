"""Producer for the preregistered V51 cross-schema factor campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_cross_schema_factor_preregistration_v51 as pre
from acfqp.cross_schema_factor_campaign_core_v51 import (
    build_cross_schema_factor_campaign_document_v51,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


CAMPAIGN_ID = "44a63b782201b3e53a32de1bc071d66fb06526903f96a037d2c55c8f3068e144"
EXPECTED_CANONICAL_BYTE_COUNT = 254_723
EXPECTED_CANONICAL_SHA256 = "124bb3d89ee55b7f942161934c8f7c80236826b5b715473a7c81fa626bc52433"
REGISTERED_FAILURE_ID = ""


class ConstructionK7CrossSchemaFactorCampaignV51Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CrossSchemaFactorCampaignV51Error(message)


def _verify_source_closure() -> None:
    expected = pre.freeze_cross_schema_factor_preregistration_v51().to_document()[
        "source_closure"
    ]["source_facts"]
    actual = []
    for relative in pre.BOUND_SOURCE_PATHS:
        raw = (pre.SOURCE_ROOT / relative).read_bytes()
        actual.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    if actual != expected:
        _fail("V51 preregistered source closure changed before outcome execution")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CrossSchemaFactorCampaignV51:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V51 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V51 campaign canonical bytes changed")
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            document.get("campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("V51 campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: CrossSchemaFactorCampaignV51 | None = None


def run_cross_schema_factor_campaign_v51() -> CrossSchemaFactorCampaignV51:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(
            "V51 registered execution failed and is frozen; same-identity rerun is forbidden: "
            + REGISTERED_FAILURE_ID
        )
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_cross_schema_factor_preregistration_v51(
        pre.freeze_cross_schema_factor_preregistration_v51()
    )
    _verify_source_closure()
    document = build_cross_schema_factor_campaign_document_v51(
        pre.campaign_config_v51(), preregistration.preregistration_id
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V51 campaign changed")
    _CACHE = CrossSchemaFactorCampaignV51(_ISSUER, raw, identity)
    return _CACHE


def verify_cross_schema_factor_campaign_v51(
    value: CrossSchemaFactorCampaignV51,
) -> CrossSchemaFactorCampaignV51:
    if type(value) is not CrossSchemaFactorCampaignV51:
        _fail("V51 campaign rejects foreign values")
    value.__post_init__()
    expected = run_cross_schema_factor_campaign_v51()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V51 campaign does not match the frozen producer output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "CrossSchemaFactorCampaignV51",
    "run_cross_schema_factor_campaign_v51",
    "verify_cross_schema_factor_campaign_v51",
)
