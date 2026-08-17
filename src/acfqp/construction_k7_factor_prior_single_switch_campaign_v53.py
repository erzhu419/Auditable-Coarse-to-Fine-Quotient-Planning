"""Producer for the preregistered V53 factor-prior single-switch campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_factor_prior_single_switch_preregistration_v53 as pre
from acfqp.factor_prior_single_switch_core_v53 import (
    build_factor_prior_single_switch_document_v53,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


CAMPAIGN_ID = "f99f19fb95af81fe25a8a3229bd0dbc35187e1e3cf9a9f97b824dbc31993d169"
EXPECTED_CANONICAL_BYTE_COUNT = 33_058_905
EXPECTED_CANONICAL_SHA256 = "6a435b190a2f5fefb4ede21b3483f90dfa199c93c555a6c6faf30aa3f5990234"
REGISTERED_FAILURE_ID = ""


class ConstructionK7FactorPriorSingleSwitchCampaignV53Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FactorPriorSingleSwitchCampaignV53Error(message)


def _verify_source_closure() -> None:
    expected = pre.freeze_factor_prior_single_switch_preregistration_v53().to_document()[
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
        _fail("V53 preregistered source closure changed before outcome execution")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FactorPriorSingleSwitchCampaignV53:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V53 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V53 campaign canonical bytes changed")
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            document.get("campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("V53 campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: FactorPriorSingleSwitchCampaignV53 | None = None


def run_factor_prior_single_switch_campaign_v53() -> FactorPriorSingleSwitchCampaignV53:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(
            "V53 registered execution failed and is frozen; same-identity rerun is forbidden: "
            + REGISTERED_FAILURE_ID
        )
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_factor_prior_single_switch_preregistration_v53(
        pre.freeze_factor_prior_single_switch_preregistration_v53()
    )
    _verify_source_closure()
    document = build_factor_prior_single_switch_document_v53(
        pre.campaign_config_v53(), preregistration.preregistration_id
    )
    if len(document["acquisitions"]["FACTOR_SIGNATURE_PRIOR_ON"]) != len(
        pre.TARGET_SEEDS
    ) or len(document["acquisitions"]["FACTOR_SIGNATURE_PRIOR_OFF"]) != len(
        pre.TARGET_SEEDS
    ):
        _fail("V53 registered acquisition occurrence count changed")
    if len(document["episodes"]["FACTOR_SIGNATURE_PRIOR_ON"]) != pre.PLANNING_VALIDATION_SEED_COUNT:
        _fail("V53 planning validation count changed")
    sample_tax = document["sample_tax"]
    if (
        sample_tax["lifetime_label_reduction"] <= 0
        or sample_tax["diagnostic_break_even_occurrence_count"] is None
        or sample_tax["diagnostic_break_even_occurrence_count"] > len(pre.TARGET_SEEDS)
    ):
        _fail("V53 historical factor-prior sample tax did not amortize within horizon")
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V53 campaign changed")
    _CACHE = FactorPriorSingleSwitchCampaignV53(_ISSUER, raw, identity)
    return _CACHE


def verify_factor_prior_single_switch_campaign_v53(
    value: FactorPriorSingleSwitchCampaignV53,
) -> FactorPriorSingleSwitchCampaignV53:
    if type(value) is not FactorPriorSingleSwitchCampaignV53:
        _fail("V53 campaign rejects foreign values")
    value.__post_init__()
    expected = run_factor_prior_single_switch_campaign_v53()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V53 campaign does not match frozen producer output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FactorPriorSingleSwitchCampaignV53",
    "run_factor_prior_single_switch_campaign_v53",
    "verify_factor_prior_single_switch_campaign_v53",
)
