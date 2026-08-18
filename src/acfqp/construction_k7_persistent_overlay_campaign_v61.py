"""Producer for the preregistered V61 persistent-overlay campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_persistent_overlay_preregistration_v61 as pre
from acfqp.persistent_overlay_campaign_core_v61 import (
    build_persistent_overlay_campaign_document_v61,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "8f0adc8821a7a5c1de892cdec14af67102c3d6fb8351611210e9493812d1f6ab"
EXPECTED_CANONICAL_BYTE_COUNT = 9_318_414
EXPECTED_CANONICAL_SHA256 = "4f7a087c511d3b3e38c8e7a8931a3a157e931115b84c9ee451941acfeda08e27"
REGISTERED_FAILURE_ID = ""


class ConstructionK7PersistentOverlayCampaignV61Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PersistentOverlayCampaignV61Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PersistentOverlayCampaignV61:
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
            or pre.domains.extension_content_id_v61(pre.V61_DOMAINS["campaign"], payload)
            != self.campaign_id
        ):
            _fail("V61 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: PersistentOverlayCampaignV61 | None = None


def run_persistent_overlay_campaign_v61() -> PersistentOverlayCampaignV61:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(f"V61 registered failure is frozen: {REGISTERED_FAILURE_ID}")
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_persistent_overlay_preregistration_v61(
        pre.freeze_persistent_overlay_preregistration_v61()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"]["source_facts"]:
        _fail("V61 preregistered source closure changed before execution")
    document = build_persistent_overlay_campaign_document_v61(
        pre.campaign_config_v61(),
        preregistration.preregistration_id,
        pre.previous.previous.previous.previous.FACTOR_LIBRARY,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V61 campaign changed")
    _CACHE = PersistentOverlayCampaignV61(_ISSUER, raw, identity)
    return _CACHE


def verify_persistent_overlay_campaign_v61(
    value: Any,
) -> PersistentOverlayCampaignV61:
    if type(value) is not PersistentOverlayCampaignV61:
        _fail("V61 campaign rejects foreign values")
    value.__post_init__()
    expected = run_persistent_overlay_campaign_v61()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V61 campaign does not match frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "run_persistent_overlay_campaign_v61",
    "verify_persistent_overlay_campaign_v61",
)
