"""Producer for the preregistered V52 factor-prior acquisition ablation."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_factor_prior_ablation_preregistration_v52 as pre
from acfqp.factor_prior_acquisition_ablation_core_v52 import (
    build_factor_prior_acquisition_ablation_document_v52,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


CAMPAIGN_ID = "8952b649ce5fb3fb9a5ce3de6e324d52ac42cad334c1a257e88bd2aca18f1898"
EXPECTED_CANONICAL_BYTE_COUNT = 88_222
EXPECTED_CANONICAL_SHA256 = "fb8e2d80d2acabff1005caf160b67af8f309a087a4262477f253b5ce26e5dfb9"
REGISTERED_FAILURE_ID = ""


class ConstructionK7FactorPriorAblationCampaignV52Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FactorPriorAblationCampaignV52Error(message)


def _verify_source_closure() -> None:
    expected = pre.freeze_factor_prior_ablation_preregistration_v52().to_document()[
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
        _fail("V52 preregistered source closure changed before outcome execution")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FactorPriorAblationCampaignV52:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V52 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V52 campaign canonical bytes changed")
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            document.get("campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("V52 campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: FactorPriorAblationCampaignV52 | None = None


def run_factor_prior_ablation_campaign_v52() -> FactorPriorAblationCampaignV52:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(
            "V52 registered execution failed and is frozen; same-identity rerun is forbidden: "
            + REGISTERED_FAILURE_ID
        )
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_factor_prior_ablation_preregistration_v52(
        pre.freeze_factor_prior_ablation_preregistration_v52()
    )
    _verify_source_closure()
    document = build_factor_prior_acquisition_ablation_document_v52(
        pre.campaign_config_v52(), preregistration.preregistration_id
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V52 campaign changed")
    _CACHE = FactorPriorAblationCampaignV52(_ISSUER, raw, identity)
    return _CACHE


def verify_factor_prior_ablation_campaign_v52(
    value: FactorPriorAblationCampaignV52,
) -> FactorPriorAblationCampaignV52:
    if type(value) is not FactorPriorAblationCampaignV52:
        _fail("V52 campaign rejects foreign values")
    value.__post_init__()
    expected = run_factor_prior_ablation_campaign_v52()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V52 campaign does not match frozen producer output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FactorPriorAblationCampaignV52",
    "run_factor_prior_ablation_campaign_v52",
    "verify_factor_prior_ablation_campaign_v52",
)
