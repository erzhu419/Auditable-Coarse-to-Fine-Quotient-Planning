"""Producer for the preregistered V68 relational world-model campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_relational_world_model_preregistration_v68 as pre
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.relational_world_model_campaign_core_v68 import (
    build_relational_world_model_campaign_document_v68,
)


CAMPAIGN_ID = "607e55ff4f745dee3f1ddf8fd8cccb76ffc1bf4f25f6df143a9b61a08c50a944"
EXPECTED_CANONICAL_BYTE_COUNT = 1_194_499
EXPECTED_CANONICAL_SHA256 = "dd91b0cac6467ac240019979eed7c4b5772a343132ad1e398ed171c8ebcada03"
REGISTERED_FAILURE_ID = ""


class ConstructionK7RelationalWorldModelCampaignV68Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RelationalWorldModelCampaignV68Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class RelationalWorldModelCampaignV68:
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
            or pre.domains.extension_content_id_v68(
                pre.domains.CONSTRUCTION_K7_RELATIONAL_WORLD_MODEL_CAMPAIGN_V68_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V68 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: RelationalWorldModelCampaignV68 | None = None


def run_relational_world_model_campaign_v68() -> RelationalWorldModelCampaignV68:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(f"V68 registered failure is frozen: {REGISTERED_FAILURE_ID}")
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_relational_world_model_preregistration_v68(
        pre.freeze_relational_world_model_preregistration_v68()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][
        "source_facts"
    ]:
        _fail("V68 preregistered source closure changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    if residual_artifact.library_artifact_id != pre.V62_LIBRARY_ID:
        _fail("V68 residual library predecessor changed")
    document = build_relational_world_model_campaign_document_v68(
        pre.campaign_config_v68(),
        preregistration.preregistration_id,
        pre.V67_CAMPAIGN_ID,
        pre.V67_VERIFICATION_ID,
        pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
        residual_artifact.to_document()["compiled_library"],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V68 campaign changed")
    _CACHE = RelationalWorldModelCampaignV68(_ISSUER, raw, identity)
    return _CACHE


def verify_relational_world_model_campaign_v68(
    value: Any,
) -> RelationalWorldModelCampaignV68:
    if type(value) is not RelationalWorldModelCampaignV68:
        _fail("V68 campaign rejects foreign values")
    value.__post_init__()
    expected = run_relational_world_model_campaign_v68()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V68 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "run_relational_world_model_campaign_v68",
    "verify_relational_world_model_campaign_v68",
)
