"""Producer for the preregistered V58r1 true-bit partial campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_true_bit_partial_preregistration_v58r1 as pre
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.true_bit_partial_three_domain_campaign_core_v58r1 import (
    build_true_bit_partial_three_domain_campaign_document_v58r1,
)


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
REGISTERED_FAILURE_ID = "62786c619f6ea7354929c23e25fbd5ea4c9e24fee9cedb5917c0edb207186cf6"


class ConstructionK7TrueBitPartialCampaignV58R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TrueBitPartialCampaignV58R1Error(message)


def _verify_source_closure() -> None:
    expected = pre.freeze_true_bit_partial_preregistration_v58r1().to_document()[
        "source_closure"
    ]["source_facts"]
    actual = pre._source_facts()
    if actual != expected:
        _fail("V58r1 preregistered source closure changed before execution")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TrueBitPartialCampaignV58R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V58r1 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains.extension_content_id_v58r1(
                pre.SUCCESSOR_DOMAINS["campaign"], payload
            )
            != self.campaign_id
        ):
            _fail("V58r1 campaign bytes or identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: TrueBitPartialCampaignV58R1 | None = None


def run_true_bit_partial_campaign_v58r1() -> TrueBitPartialCampaignV58R1:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(
            "V58r1 registered execution failed and is frozen; rerun forbidden: "
            f"{REGISTERED_FAILURE_ID}"
        )
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_true_bit_partial_preregistration_v58r1(
        pre.freeze_true_bit_partial_preregistration_v58r1()
    )
    _verify_source_closure()
    document = build_true_bit_partial_three_domain_campaign_document_v58r1(
        pre.campaign_config_v58r1(),
        preregistration.preregistration_id,
        pre.previous.FACTOR_LIBRARY,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V58r1 campaign changed")
    _CACHE = TrueBitPartialCampaignV58R1(_ISSUER, raw, identity)
    return _CACHE


def verify_true_bit_partial_campaign_v58r1(
    value: Any,
) -> TrueBitPartialCampaignV58R1:
    if type(value) is not TrueBitPartialCampaignV58R1:
        _fail("V58r1 campaign rejects foreign values")
    value.__post_init__()
    expected = run_true_bit_partial_campaign_v58r1()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V58r1 campaign does not match frozen producer output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "TrueBitPartialCampaignV58R1",
    "run_true_bit_partial_campaign_v58r1",
    "verify_true_bit_partial_campaign_v58r1",
)
