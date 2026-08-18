"""Producer for the preregistered V65 online residual-planning campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_online_residual_planning_preregistration_v65 as pre
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.online_residual_planning_campaign_core_v65 import (
    build_online_residual_planning_campaign_document_v65,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0754c5575634d075a005d809589dc00198ad4b66be5afcee73c15b3317f9eeda"
EXPECTED_CANONICAL_BYTE_COUNT = 2_475_692
EXPECTED_CANONICAL_SHA256 = "629bf0560654d23fb566a8c4d8555cb508d23ddcd09dc98f5f300755c47c8764"
REGISTERED_FAILURE_ID = ""


class ConstructionK7OnlineResidualPlanningCampaignV65Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OnlineResidualPlanningCampaignV65Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OnlineResidualPlanningCampaignV65:
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
            or pre.domains.extension_content_id_v65(
                pre.domains.CONSTRUCTION_K7_ONLINE_RESIDUAL_PLANNING_CAMPAIGN_V65_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V65 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: OnlineResidualPlanningCampaignV65 | None = None


def run_online_residual_planning_campaign_v65() -> OnlineResidualPlanningCampaignV65:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(f"V65 registered failure is frozen: {REGISTERED_FAILURE_ID}")
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_online_residual_planning_preregistration_v65(
        pre.freeze_online_residual_planning_preregistration_v65()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][
        "source_facts"
    ]:
        _fail("V65 preregistered source closure changed before execution")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    if residual_artifact.library_artifact_id != pre.V62_LIBRARY_ID:
        _fail("V65 residual library predecessor changed")
    document = build_online_residual_planning_campaign_document_v65(
        pre.campaign_config_v65(),
        preregistration.preregistration_id,
        pre.V64_CAMPAIGN_ID,
        pre.V64_VERIFICATION_ID,
        pre.previous.previous.previous.FACTOR_LIBRARY,
        residual_artifact.to_document()["compiled_library"],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V65 campaign changed")
    _CACHE = OnlineResidualPlanningCampaignV65(_ISSUER, raw, identity)
    return _CACHE


def verify_online_residual_planning_campaign_v65(
    value: Any,
) -> OnlineResidualPlanningCampaignV65:
    if type(value) is not OnlineResidualPlanningCampaignV65:
        _fail("V65 campaign rejects foreign values")
    value.__post_init__()
    expected = run_online_residual_planning_campaign_v65()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V65 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "run_online_residual_planning_campaign_v65",
    "verify_online_residual_planning_campaign_v65",
)
