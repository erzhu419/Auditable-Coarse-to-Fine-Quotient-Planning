"""Producer for the preregistered V56r1 exact-frontier campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_mdl_adaptive_preregistration_v56r1 as pre
from acfqp.adaptive_mdl_cross_domain_campaign_core_v56r1 import (
    build_adaptive_mdl_cross_domain_campaign_document_v56r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0f5032377cd52b021133fe03a4ab4a34613a230bd3ae25efa43e02ca911521a8"
EXPECTED_CANONICAL_BYTE_COUNT = 16_064_927
EXPECTED_CANONICAL_SHA256 = "67188187a8fcda709fdcd287d653c3140a7dcf40618b4588faae355ff761f3e5"
REGISTERED_FAILURE_ID = ""


class ConstructionK7MDLAdaptiveCampaignV56R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7MDLAdaptiveCampaignV56R1Error(message)


def _verify_source_closure() -> None:
    expected = pre.freeze_mdl_adaptive_preregistration_v56r1().to_document()[
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
        _fail("V56r1 preregistered source closure changed before execution")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class MDLAdaptiveCampaignV56R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V56r1 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains_v56r1.extension_content_id_v56r1(
                pre.SUCCESSOR_DOMAINS["campaign"], payload
            )
            != self.campaign_id
        ):
            _fail("V56r1 campaign bytes or identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: MDLAdaptiveCampaignV56R1 | None = None


def run_mdl_adaptive_campaign_v56r1() -> MDLAdaptiveCampaignV56R1:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(
            "V56r1 registered execution failed and is frozen; rerun forbidden: "
            f"{REGISTERED_FAILURE_ID}"
        )
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_mdl_adaptive_preregistration_v56r1(
        pre.freeze_mdl_adaptive_preregistration_v56r1()
    )
    _verify_source_closure()
    document = build_adaptive_mdl_cross_domain_campaign_document_v56r1(
        pre.campaign_config_v56r1(),
        preregistration.preregistration_id,
        pre.FACTOR_LIBRARY,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V56r1 campaign changed")
    _CACHE = MDLAdaptiveCampaignV56R1(_ISSUER, raw, identity)
    return _CACHE


def verify_mdl_adaptive_campaign_v56r1(value: Any) -> MDLAdaptiveCampaignV56R1:
    if type(value) is not MDLAdaptiveCampaignV56R1:
        _fail("V56r1 campaign rejects foreign values")
    value.__post_init__()
    expected = run_mdl_adaptive_campaign_v56r1()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V56r1 campaign does not match the frozen producer output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "MDLAdaptiveCampaignV56R1",
    "run_mdl_adaptive_campaign_v56r1",
    "verify_mdl_adaptive_campaign_v56r1",
)
