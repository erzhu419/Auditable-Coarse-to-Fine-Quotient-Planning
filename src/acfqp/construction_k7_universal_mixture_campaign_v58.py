"""Producer for the preregistered V58 universal-mixture campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_universal_mixture_preregistration_v58 as pre
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.universal_mixture_three_domain_campaign_core_v58 import (
    build_universal_mixture_three_domain_campaign_document_v58,
)


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
REGISTERED_FAILURE_ID = (
    "f90df0f0035140179b33e0b3a9d438dd232faf458b4efbd0be6d9f6a785d6ac2"
)


class ConstructionK7UniversalMixtureCampaignV58Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7UniversalMixtureCampaignV58Error(message)


def _verify_source_closure() -> None:
    expected = pre.freeze_universal_mixture_preregistration_v58().to_document()[
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
        _fail("V58 preregistered source closure changed before execution")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class UniversalMixtureCampaignV58:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V58 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains_v58.extension_content_id_v58(
                pre.SUCCESSOR_DOMAINS["campaign"], payload
            )
            != self.campaign_id
        ):
            _fail("V58 campaign bytes or identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: UniversalMixtureCampaignV58 | None = None


def run_universal_mixture_campaign_v58() -> UniversalMixtureCampaignV58:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(
            "V58 registered execution failed and is frozen; rerun forbidden: "
            f"{REGISTERED_FAILURE_ID}"
        )
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_universal_mixture_preregistration_v58(
        pre.freeze_universal_mixture_preregistration_v58()
    )
    _verify_source_closure()
    document = build_universal_mixture_three_domain_campaign_document_v58(
        pre.campaign_config_v58(),
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
        _fail("frozen V58 campaign changed")
    _CACHE = UniversalMixtureCampaignV58(_ISSUER, raw, identity)
    return _CACHE


def verify_universal_mixture_campaign_v58(
    value: Any,
) -> UniversalMixtureCampaignV58:
    if type(value) is not UniversalMixtureCampaignV58:
        _fail("V58 campaign rejects foreign values")
    value.__post_init__()
    expected = run_universal_mixture_campaign_v58()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V58 campaign does not match the frozen producer output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "UniversalMixtureCampaignV58",
    "run_universal_mixture_campaign_v58",
    "verify_universal_mixture_campaign_v58",
)
