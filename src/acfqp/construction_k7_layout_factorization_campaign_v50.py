"""Producer for the preregistered V50 layout-factorization campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_layout_factorization_preregistration_v50 as pre
from acfqp.layout_factorized_campaign_core_v50 import (
    build_layout_factorized_campaign_document_v50,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = "50.0.0"
CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
REGISTERED_FAILURE_ID = "603e1e69ed5e4093675435ffda6aa1de82118d93b44232a9cfc0454a00424581"


class ConstructionK7LayoutFactorizationCampaignV50Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LayoutFactorizationCampaignV50Error(message)


def _verify_source_closure() -> None:
    preregistration = pre.freeze_layout_factorization_preregistration_v50().to_document()
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
        _fail("V50 preregistered source closure changed before outcome execution")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LayoutFactorizationCampaignV50:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V50 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V50 campaign canonical bytes changed")
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            document.get("campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("V50 campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: LayoutFactorizationCampaignV50 | None = None


def run_layout_factorization_campaign_v50() -> LayoutFactorizationCampaignV50:
    global _CACHE
    if REGISTERED_FAILURE_ID != "":
        _fail(
            "V50 registered execution failed and is frozen; same-identity rerun is forbidden: "
            + REGISTERED_FAILURE_ID
        )
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_layout_factorization_preregistration_v50(
        pre.freeze_layout_factorization_preregistration_v50()
    )
    _verify_source_closure()
    document = build_layout_factorized_campaign_document_v50(
        pre.campaign_config_v50(), preregistration.preregistration_id
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V50 campaign changed")
    _CACHE = LayoutFactorizationCampaignV50(_ISSUER, raw, identity)
    return _CACHE


def verify_layout_factorization_campaign_v50(
    value: LayoutFactorizationCampaignV50,
) -> LayoutFactorizationCampaignV50:
    if type(value) is not LayoutFactorizationCampaignV50:
        _fail("V50 campaign rejects foreign values")
    value.__post_init__()
    expected = run_layout_factorization_campaign_v50()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V50 campaign does not match the frozen producer output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "LayoutFactorizationCampaignV50",
    "run_layout_factorization_campaign_v50",
    "verify_layout_factorization_campaign_v50",
)
