"""Producer for the preregistered V50r1 layout-factorization campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_layout_factorization_preregistration_v50r1 as pre
from acfqp.layout_factorized_campaign_core_v50r1 import (
    build_layout_factorized_campaign_document_v50r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = "50.1.0"
CAMPAIGN_ID = "24460ce540a835aba601cdba6865ae74f65c95e6eb8f060c00bddd9b0d4f7622"
EXPECTED_CANONICAL_BYTE_COUNT = 361_145
EXPECTED_CANONICAL_SHA256 = "f962a4a0e2feac85841e12153f3538108d3a165c8e6c482c9e44a7ac4ab176f1"
REGISTERED_FAILURE_ID = ""


class ConstructionK7LayoutFactorizationCampaignV50R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LayoutFactorizationCampaignV50R1Error(message)


def _verify_source_closure() -> None:
    preregistration = pre.freeze_layout_factorization_preregistration_v50r1().to_document()
    expected = preregistration["source_closure"]["source_facts"]
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
        _fail("V50r1 preregistered source closure changed before outcome execution")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LayoutFactorizationCampaignV50R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V50r1 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V50r1 campaign canonical bytes changed")
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            document.get("campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("V50r1 campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: LayoutFactorizationCampaignV50R1 | None = None


def run_layout_factorization_campaign_v50r1() -> LayoutFactorizationCampaignV50R1:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(
            "V50r1 registered execution failed and is frozen; same-identity rerun is forbidden: "
            + REGISTERED_FAILURE_ID
        )
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_layout_factorization_preregistration_v50r1(
        pre.freeze_layout_factorization_preregistration_v50r1()
    )
    _verify_source_closure()
    document = build_layout_factorized_campaign_document_v50r1(
        pre.campaign_config_v50r1(), preregistration.preregistration_id
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V50r1 campaign changed")
    _CACHE = LayoutFactorizationCampaignV50R1(_ISSUER, raw, identity)
    return _CACHE


def verify_layout_factorization_campaign_v50r1(
    value: LayoutFactorizationCampaignV50R1,
) -> LayoutFactorizationCampaignV50R1:
    if type(value) is not LayoutFactorizationCampaignV50R1:
        _fail("V50r1 campaign rejects foreign values")
    value.__post_init__()
    expected = run_layout_factorization_campaign_v50r1()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V50r1 campaign does not match the frozen producer output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "LayoutFactorizationCampaignV50R1",
    "run_layout_factorization_campaign_v50r1",
    "verify_layout_factorization_campaign_v50r1",
)
