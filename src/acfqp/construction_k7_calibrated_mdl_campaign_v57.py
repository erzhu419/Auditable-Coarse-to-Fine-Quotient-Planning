"""Producer for the preregistered V57 calibrated three-domain campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_calibrated_mdl_preregistration_v57 as pre
from acfqp.calibrated_mdl_three_domain_campaign_core_v57 import (
    build_calibrated_mdl_three_domain_campaign_document_v57,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "744e764a35cb7ba4955852fa62c30978b7aac35d0761b7054cb64298be1fd92b"
EXPECTED_CANONICAL_BYTE_COUNT = 25_640_858
EXPECTED_CANONICAL_SHA256 = "3fc9f09eac87e1ea2180a1b6a5523694aed5c1dc41438a7484e6a9dc9f925588"
REGISTERED_FAILURE_ID = ""


class ConstructionK7CalibratedMDLCampaignV57Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CalibratedMDLCampaignV57Error(message)


def _verify_source_closure() -> None:
    expected = pre.freeze_calibrated_mdl_preregistration_v57().to_document()[
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
        _fail("V57 preregistered source closure changed before execution")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CalibratedMDLCampaignV57:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V57 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains_v57.extension_content_id_v57(
                pre.SUCCESSOR_DOMAINS["campaign"], payload
            )
            != self.campaign_id
        ):
            _fail("V57 campaign bytes or identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: CalibratedMDLCampaignV57 | None = None


def run_calibrated_mdl_campaign_v57() -> CalibratedMDLCampaignV57:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(
            "V57 registered execution failed and is frozen; rerun forbidden: "
            f"{REGISTERED_FAILURE_ID}"
        )
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_calibrated_mdl_preregistration_v57(
        pre.freeze_calibrated_mdl_preregistration_v57()
    )
    _verify_source_closure()
    document = build_calibrated_mdl_three_domain_campaign_document_v57(
        pre.campaign_config_v57(),
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
        _fail("frozen V57 campaign changed")
    _CACHE = CalibratedMDLCampaignV57(_ISSUER, raw, identity)
    return _CACHE


def verify_calibrated_mdl_campaign_v57(value: Any) -> CalibratedMDLCampaignV57:
    if type(value) is not CalibratedMDLCampaignV57:
        _fail("V57 campaign rejects foreign values")
    value.__post_init__()
    expected = run_calibrated_mdl_campaign_v57()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V57 campaign does not match the frozen producer output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "CalibratedMDLCampaignV57",
    "run_calibrated_mdl_campaign_v57",
    "verify_calibrated_mdl_campaign_v57",
)
