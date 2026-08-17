"""Producer for the preregistered V54 joint factor/residual campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_joint_factor_residual_preregistration_v54 as pre
from acfqp.construction_k7_cross_schema_factor_campaign_v51 import (
    EXPECTED_CANONICAL_SHA256 as V51_CAMPAIGN_SHA256,
    run_cross_schema_factor_campaign_v51,
)
from acfqp.joint_factor_residual_campaign_core_v54 import (
    build_joint_factor_residual_campaign_document_v54,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


CAMPAIGN_ID = "0000000000000000000000000000000000000000000000000000000000000000"
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = ""
REGISTERED_FAILURE_ID = "f5dbecac001b91c3a460fe4f7d4559a45bef631640f881c29e6e484f95c8b785"


class ConstructionK7JointFactorResidualCampaignV54Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7JointFactorResidualCampaignV54Error(message)


def _verify_source_closure() -> None:
    expected = pre.freeze_joint_factor_residual_preregistration_v54().to_document()[
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
        _fail("V54 preregistered source closure changed before outcome execution")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class JointFactorResidualCampaignV54:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V54 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V54 campaign canonical bytes changed")
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            document.get("campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload)
            != self.campaign_id
        ):
            _fail("V54 campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: JointFactorResidualCampaignV54 | None = None


def run_joint_factor_residual_campaign_v54() -> JointFactorResidualCampaignV54:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(
            "V54 registered execution failed and is frozen; same-identity rerun is forbidden: "
            + REGISTERED_FAILURE_ID
        )
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_joint_factor_residual_preregistration_v54(
        pre.freeze_joint_factor_residual_preregistration_v54()
    )
    _verify_source_closure()
    predecessor = run_cross_schema_factor_campaign_v51()
    if (
        predecessor.campaign_id != pre.V51_CAMPAIGN_ID
        or hashlib.sha256(predecessor.canonical_bytes).hexdigest()
        != V51_CAMPAIGN_SHA256
    ):
        _fail("V54 frozen V51 predecessor identity changed")
    factor_library = predecessor.to_document()["inherited_factor_library"]
    if factor_library.get("factor_library_id") != pre.V51_FACTOR_LIBRARY_ID:
        _fail("V54 frozen V51 factor library changed")
    document = build_joint_factor_residual_campaign_document_v54(
        pre.campaign_config_v54(),
        preregistration.preregistration_id,
        factor_library,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V54 campaign changed")
    _CACHE = JointFactorResidualCampaignV54(_ISSUER, raw, identity)
    return _CACHE


def verify_joint_factor_residual_campaign_v54(
    value: JointFactorResidualCampaignV54,
) -> JointFactorResidualCampaignV54:
    if type(value) is not JointFactorResidualCampaignV54:
        _fail("V54 campaign rejects foreign values")
    value.__post_init__()
    expected = run_joint_factor_residual_campaign_v54()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V54 campaign does not match frozen producer output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "JointFactorResidualCampaignV54",
    "run_joint_factor_residual_campaign_v54",
    "verify_joint_factor_residual_campaign_v54",
)
