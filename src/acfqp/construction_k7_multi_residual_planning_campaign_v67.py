"""Producer for the preregistered V67 joint residual planning campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_multi_residual_planning_preregistration_v67 as pre
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.multi_residual_planning_campaign_core_v67 import (
    build_multi_residual_planning_campaign_document_v67,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "4726d258497299bba1dbaf37339ed5f497e3af7e1e114c602d5b4efe9614708b"
EXPECTED_CANONICAL_BYTE_COUNT = 1_891_744
EXPECTED_CANONICAL_SHA256 = "baf3f69dbacb15547a2a6e42250f5b5eac933edb74c013eb6ef9d8b6e710d897"
REGISTERED_FAILURE_ID = ""


class ConstructionK7MultiResidualPlanningCampaignV67Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7MultiResidualPlanningCampaignV67Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class MultiResidualPlanningCampaignV67:
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
            or pre.domains.extension_content_id_v67(
                pre.domains.CONSTRUCTION_K7_MULTI_RESIDUAL_PLANNING_CAMPAIGN_V67_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V67 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: MultiResidualPlanningCampaignV67 | None = None


def run_multi_residual_planning_campaign_v67() -> MultiResidualPlanningCampaignV67:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(f"V67 registered failure is frozen: {REGISTERED_FAILURE_ID}")
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_multi_residual_planning_preregistration_v67(
        pre.freeze_multi_residual_planning_preregistration_v67()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][
        "source_facts"
    ]:
        _fail("V67 preregistered source closure changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    if residual_artifact.library_artifact_id != pre.V62_LIBRARY_ID:
        _fail("V67 residual library predecessor changed")
    document = build_multi_residual_planning_campaign_document_v67(
        pre.campaign_config_v67(),
        preregistration.preregistration_id,
        pre.V66_CAMPAIGN_ID,
        pre.V66_VERIFICATION_ID,
        pre.previous.previous.previous.previous.FACTOR_LIBRARY,
        residual_artifact.to_document()["compiled_library"],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V67 campaign changed")
    _CACHE = MultiResidualPlanningCampaignV67(_ISSUER, raw, identity)
    return _CACHE


def verify_multi_residual_planning_campaign_v67(
    value: Any,
) -> MultiResidualPlanningCampaignV67:
    if type(value) is not MultiResidualPlanningCampaignV67:
        _fail("V67 campaign rejects foreign values")
    value.__post_init__()
    expected = run_multi_residual_planning_campaign_v67()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V67 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "run_multi_residual_planning_campaign_v67",
    "verify_multi_residual_planning_campaign_v67",
)
