"""Producer for the preregistered V87 applicability-conditioned target Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_applicability_target_preregistration_v87 as pre
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70_pre
from acfqp.applicability_target_campaign_core_v87 import (
    build_applicability_target_campaign_document_v87,
)
from acfqp.construction_k7_action_applicability_model_v87 import (
    load_action_applicability_model_v87,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    load_projected_model_artifact_v86,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "e5432505db2bf911324d3d719986493bfa81aa131439ee31367da9329cc2b0d8"
EXPECTED_CANONICAL_BYTE_COUNT = 85_215
EXPECTED_CANONICAL_SHA256 = "233d01e1429fa1742ca9cfae9aaac29e26310840ee2354166df967888088cb95"


class ConstructionK7ApplicabilityTargetCampaignV87Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ApplicabilityTargetCampaignV87Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ApplicabilityTargetCampaignV87:
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
            or pre.domains.extension_content_id_v87(
                pre.domains.CONSTRUCTION_K7_APPLICABILITY_TARGET_CAMPAIGN_V87_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V87 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ApplicabilityTargetCampaignV87 | None = None


def run_applicability_target_campaign_v87() -> ApplicabilityTargetCampaignV87:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_applicability_target_preregistration_v87(
        pre.freeze_applicability_target_preregistration_v87()
    )
    if pre._frozen_source_facts() != preregistration.to_document()["source_closure"][  # noqa: SLF001
        "source_facts"
    ]:
        _fail("V87 preregistered source closure changed")
    projected_artifact = load_projected_model_artifact_v86()
    applicability_artifact = load_action_applicability_model_v87()
    if (
        projected_artifact["model_artifact_id"] != pre.PROJECTED_MODEL_ARTIFACT_ID
        or applicability_artifact["model_artifact_id"]
        != pre.APPLICABILITY_MODEL_ARTIFACT_ID
    ):
        _fail("V87 frozen model artifact changed")
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_applicability_target_campaign_document_v87(
        pre.campaign_config_v87(),
        preregistration.preregistration_id,
        pre.PROJECTED_MODEL_ARTIFACT_ID,
        pre.APPLICABILITY_MODEL_ARTIFACT_ID,
        pre.V86_CAMPAIGN_ID,
        pre.V86_VERIFICATION_ID,
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
        _fail("frozen V87 campaign changed")
    _CACHE = ApplicabilityTargetCampaignV87(_ISSUER, raw, identity)
    return _CACHE


def verify_applicability_target_campaign_v87(
    value: Any,
) -> ApplicabilityTargetCampaignV87:
    if type(value) is not ApplicabilityTargetCampaignV87:
        _fail("V87 campaign rejects foreign values")
    value.__post_init__()
    expected = run_applicability_target_campaign_v87()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V87 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "run_applicability_target_campaign_v87",
    "verify_applicability_target_campaign_v87",
)
