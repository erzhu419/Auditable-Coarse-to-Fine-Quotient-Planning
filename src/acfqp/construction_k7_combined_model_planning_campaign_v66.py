"""Producer for the preregistered V66 combined-model campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_combined_model_planning_preregistration_v66 as pre
from acfqp.combined_model_planning_campaign_core_v66 import (
    build_combined_model_planning_campaign_document_v66,
)
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "b4c8e705ebe76b63c3a67831feedcff948a2b0e09ab928b9aaa03363f3d3a1a8"
EXPECTED_CANONICAL_BYTE_COUNT = 1_880_548
EXPECTED_CANONICAL_SHA256 = "6ab084c3c465a5b410e4d3e5950e9625aaf49e9804dc0e75e08c7a96dc2129d2"
REGISTERED_FAILURE_ID = ""


class ConstructionK7CombinedModelPlanningCampaignV66Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CombinedModelPlanningCampaignV66Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CombinedModelPlanningCampaignV66:
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
            or pre.domains.extension_content_id_v66(
                pre.domains.CONSTRUCTION_K7_COMBINED_MODEL_PLANNING_CAMPAIGN_V66_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V66 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: CombinedModelPlanningCampaignV66 | None = None


def run_combined_model_planning_campaign_v66() -> CombinedModelPlanningCampaignV66:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(f"V66 registered failure is frozen: {REGISTERED_FAILURE_ID}")
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_combined_model_planning_preregistration_v66(
        pre.freeze_combined_model_planning_preregistration_v66()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][
        "source_facts"
    ]:
        _fail("V66 preregistered source closure changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    if residual_artifact.library_artifact_id != pre.V62_LIBRARY_ID:
        _fail("V66 residual library predecessor changed")
    document = build_combined_model_planning_campaign_document_v66(
        pre.campaign_config_v66(),
        preregistration.preregistration_id,
        pre.V65_CAMPAIGN_ID,
        pre.V65_VERIFICATION_ID,
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
        _fail("frozen V66 campaign changed")
    _CACHE = CombinedModelPlanningCampaignV66(_ISSUER, raw, identity)
    return _CACHE


def verify_combined_model_planning_campaign_v66(
    value: Any,
) -> CombinedModelPlanningCampaignV66:
    if type(value) is not CombinedModelPlanningCampaignV66:
        _fail("V66 campaign rejects foreign values")
    value.__post_init__()
    expected = run_combined_model_planning_campaign_v66()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V66 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "run_combined_model_planning_campaign_v66",
    "verify_combined_model_planning_campaign_v66",
)
