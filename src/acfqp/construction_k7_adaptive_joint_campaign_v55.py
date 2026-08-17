"""Producer for the preregistered V55 adaptive joint campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_adaptive_joint_preregistration_v55 as pre
from acfqp.adaptive_joint_factor_residual_campaign_core_v55 import (
    build_adaptive_joint_factor_residual_campaign_document_v55,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "ea85860f499ac631a7f3e6b306974be2a2d7c9de88cde3cf492380ebd59ec589"
EXPECTED_CANONICAL_BYTE_COUNT = 2_027_913
EXPECTED_CANONICAL_SHA256 = "38363f222d1b4047e4ce6f2fd5e6c4aea595709b473e9aed44d90fd54245128a"
REGISTERED_FAILURE_ID = ""


class ConstructionK7AdaptiveJointCampaignV55Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AdaptiveJointCampaignV55Error(message)


def _verify_source_closure() -> None:
    expected = pre.freeze_adaptive_joint_preregistration_v55().to_document()[
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
        _fail("V55 preregistered source closure changed before execution")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AdaptiveJointCampaignV55:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V55 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items() if key != "campaign_id"
        }
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains_v55.extension_content_id_v55(
                pre.FUTURE_DOMAINS["campaign"], payload
            )
            != self.campaign_id
        ):
            _fail("V55 campaign bytes or identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: AdaptiveJointCampaignV55 | None = None


def run_adaptive_joint_campaign_v55() -> AdaptiveJointCampaignV55:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(
            "V55 registered execution failed; same-identity rerun is forbidden: "
            + REGISTERED_FAILURE_ID
        )
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_adaptive_joint_preregistration_v55(
        pre.freeze_adaptive_joint_preregistration_v55()
    )
    _verify_source_closure()
    document = build_adaptive_joint_factor_residual_campaign_document_v55(
        pre.campaign_config_v55(),
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
        _fail("frozen V55 campaign changed")
    _CACHE = AdaptiveJointCampaignV55(_ISSUER, raw, identity)
    return _CACHE


def verify_adaptive_joint_campaign_v55(value: Any) -> AdaptiveJointCampaignV55:
    if type(value) is not AdaptiveJointCampaignV55:
        _fail("V55 campaign rejects foreign values")
    value.__post_init__()
    expected = run_adaptive_joint_campaign_v55()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V55 campaign does not match frozen bytes")
    return value


__all__ = (
    "AdaptiveJointCampaignV55",
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "run_adaptive_joint_campaign_v55",
    "verify_adaptive_joint_campaign_v55",
)
