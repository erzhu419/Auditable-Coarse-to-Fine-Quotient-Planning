"""Producer for the preregistered V88 replayable-coordinate Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_replayable_coordinate_preregistration_v88 as pre
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70
from acfqp.construction_k7_action_applicability_model_v87 import load_action_applicability_model_v87
from acfqp.construction_k7_projected_model_artifact_v86 import load_projected_model_artifact_v86
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.replayable_coordinate_target_campaign_core_v88 import build_replayable_coordinate_target_campaign_document_v88


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7ReplayableCoordinateCampaignV88Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReplayableCoordinateCampaignV88Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ReplayableCoordinateCampaignV88:
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
            or pre.domains.extension_content_id_v88(
                pre.domains.CONSTRUCTION_K7_REPLAYABLE_COORDINATE_CAMPAIGN_V88_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V88 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ReplayableCoordinateCampaignV88 | None = None


def run_replayable_coordinate_campaign_v88() -> ReplayableCoordinateCampaignV88:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_replayable_coordinate_preregistration_v88(
        pre.freeze_replayable_coordinate_preregistration_v88()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][  # noqa: SLF001
        "source_facts"
    ]:
        _fail("V88 source closure changed")
    projected = load_projected_model_artifact_v86()
    applicability = load_action_applicability_model_v87()
    factor_library = v70.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    document = build_replayable_coordinate_target_campaign_document_v88(
        pre.campaign_config_v88(),
        preregistration.preregistration_id,
        pre.PROJECTED_MODEL_ARTIFACT_ID,
        pre.APPLICABILITY_MODEL_ARTIFACT_ID,
        projected["projected_disagreement_successor_model"],
        applicability["action_applicability_program"],
        factor_library,
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V88 campaign changed")
    _CACHE = ReplayableCoordinateCampaignV88(_ISSUER, raw, identity)
    return _CACHE


def verify_replayable_coordinate_campaign_v88(
    value: Any,
) -> ReplayableCoordinateCampaignV88:
    if type(value) is not ReplayableCoordinateCampaignV88:
        _fail("V88 campaign rejects foreign values")
    value.__post_init__()
    expected = run_replayable_coordinate_campaign_v88()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V88 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "run_replayable_coordinate_campaign_v88",
    "verify_replayable_coordinate_campaign_v88",
)
