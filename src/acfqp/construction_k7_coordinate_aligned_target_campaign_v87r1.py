"""Producer for the preregistered V87r1 coordinate-aligned target Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_coordinate_aligned_target_preregistration_v87r1 as pre
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70_pre
from acfqp.construction_k7_action_applicability_model_v87 import (
    load_action_applicability_model_v87,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    load_projected_model_artifact_v86,
)
from acfqp.coordinate_aligned_target_campaign_core_v87r1 import (
    build_coordinate_aligned_target_campaign_document_v87r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "33e9d49933e8b2d94169911170732b178095ce55fe52258c6ccfb9d425990739"
EXPECTED_CANONICAL_BYTE_COUNT = 2_439_114
EXPECTED_CANONICAL_SHA256 = "a0c033bd300584b9bda88520d7fdacc410970ee101c70e406387f122efec9937"


class ConstructionK7CoordinateAlignedTargetCampaignV87R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CoordinateAlignedTargetCampaignV87R1Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CoordinateAlignedTargetCampaignV87R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items() if key != "campaign_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains.extension_content_id_v87r1(
                pre.domains.CONSTRUCTION_K7_COORDINATE_ALIGNED_CAMPAIGN_V87R1_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V87r1 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: CoordinateAlignedTargetCampaignV87R1 | None = None


def run_coordinate_aligned_target_campaign_v87r1(
) -> CoordinateAlignedTargetCampaignV87R1:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_coordinate_aligned_target_preregistration_v87r1(
        pre.freeze_coordinate_aligned_target_preregistration_v87r1()
    )
    if pre._frozen_source_facts() != preregistration.to_document()["source_closure"][  # noqa: SLF001
        "source_facts"
    ]:
        _fail("V87r1 preregistered source closure changed")
    projected_artifact = load_projected_model_artifact_v86()
    applicability_artifact = load_action_applicability_model_v87()
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_coordinate_aligned_target_campaign_document_v87r1(
        pre.campaign_config_v87r1(),
        preregistration.preregistration_id,
        pre.PROJECTED_MODEL_ARTIFACT_ID,
        pre.APPLICABILITY_MODEL_ARTIFACT_ID,
        projected_artifact["projected_disagreement_successor_model"],
        applicability_artifact["action_applicability_program"],
        factor_library,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V87r1 campaign changed")
    _CACHE = CoordinateAlignedTargetCampaignV87R1(_ISSUER, raw, identity)
    return _CACHE


def verify_coordinate_aligned_target_campaign_v87r1(
    value: Any,
) -> CoordinateAlignedTargetCampaignV87R1:
    if type(value) is not CoordinateAlignedTargetCampaignV87R1:
        _fail("V87r1 campaign rejects foreign values")
    value.__post_init__()
    expected = run_coordinate_aligned_target_campaign_v87r1()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V87r1 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "run_coordinate_aligned_target_campaign_v87r1",
    "verify_coordinate_aligned_target_campaign_v87r1",
)
