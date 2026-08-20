"""Producer for the preregistered V86 fresh-target transfer Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_projected_target_preregistration_v86 as pre
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70_pre
from acfqp.construction_k7_projected_model_artifact_v86 import (
    load_projected_model_artifact_v86,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.projected_disagreement_target_campaign_core_v86 import (
    build_projected_disagreement_target_campaign_document_v86,
)


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7ProjectedTargetCampaignV86Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProjectedTargetCampaignV86Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ProjectedTargetCampaignV86:
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
            or pre.domains.extension_content_id_v86(
                pre.domains.CONSTRUCTION_K7_PROJECTED_TARGET_CAMPAIGN_V86_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V86 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ProjectedTargetCampaignV86 | None = None


def run_projected_target_campaign_v86() -> ProjectedTargetCampaignV86:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_projected_target_preregistration_v86(
        pre.freeze_projected_target_preregistration_v86()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"]["source_facts"]:  # noqa: SLF001
        _fail("V86 preregistered source closure changed")
    model_artifact = load_projected_model_artifact_v86()
    if model_artifact["model_artifact_id"] != pre.MODEL_ARTIFACT_ID:
        _fail("V86 source model artifact changed")
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_projected_disagreement_target_campaign_document_v86(
        pre.campaign_config_v86(),
        preregistration.preregistration_id,
        pre.MODEL_ARTIFACT_ID,
        pre.V85R1_CAMPAIGN_ID,
        pre.V85R1_VERIFICATION_ID,
        model_artifact["projected_disagreement_successor_model"],
        factor_library,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V86 campaign changed")
    _CACHE = ProjectedTargetCampaignV86(_ISSUER, raw, identity)
    return _CACHE


def verify_projected_target_campaign_v86(value: Any) -> ProjectedTargetCampaignV86:
    if type(value) is not ProjectedTargetCampaignV86:
        _fail("V86 campaign rejects foreign values")
    value.__post_init__()
    expected = run_projected_target_campaign_v86()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V86 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "run_projected_target_campaign_v86",
    "verify_projected_target_campaign_v86",
)
