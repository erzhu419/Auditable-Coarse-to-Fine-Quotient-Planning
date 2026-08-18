"""Producer for the preregistered V59 symmetric-prefix campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as pre
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.true_bit_symmetric_three_domain_campaign_core_v59 import (
    build_true_bit_symmetric_three_domain_campaign_document_v59,
)


CAMPAIGN_ID = "60ecb969f8b2b6cd7aa000d7306c213ab194293fc76a01190c73bae22e8b8d18"
EXPECTED_CANONICAL_BYTE_COUNT = 881_518
EXPECTED_CANONICAL_SHA256 = "50117e4665dc29819e19e38ebf17a8fbaceb2ba9c466afc4bd377ed74f83e99a"
REGISTERED_FAILURE_ID = ""


class ConstructionK7TrueBitSymmetricCampaignV59Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TrueBitSymmetricCampaignV59Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TrueBitSymmetricCampaignV59:
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
            or pre.domains.extension_content_id_v59(pre.SUCCESSOR_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("V59 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: TrueBitSymmetricCampaignV59 | None = None


def run_true_bit_symmetric_campaign_v59() -> TrueBitSymmetricCampaignV59:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(f"V59 registered failure is frozen: {REGISTERED_FAILURE_ID}")
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_true_bit_symmetric_preregistration_v59(
        pre.freeze_true_bit_symmetric_preregistration_v59()
    )
    expected = preregistration.to_document()["source_closure"]["source_facts"]
    if pre._source_facts() != expected:
        _fail("V59 preregistered source closure changed before execution")
    document = build_true_bit_symmetric_three_domain_campaign_document_v59(
        pre.campaign_config_v59(),
        preregistration.preregistration_id,
        pre.previous.previous.FACTOR_LIBRARY,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V59 campaign changed")
    _CACHE = TrueBitSymmetricCampaignV59(_ISSUER, raw, identity)
    return _CACHE


def verify_true_bit_symmetric_campaign_v59(value: Any) -> TrueBitSymmetricCampaignV59:
    if type(value) is not TrueBitSymmetricCampaignV59:
        _fail("V59 campaign rejects foreign values")
    value.__post_init__()
    expected = run_true_bit_symmetric_campaign_v59()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V59 campaign does not match frozen producer output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "run_true_bit_symmetric_campaign_v59",
    "verify_true_bit_symmetric_campaign_v59",
)
