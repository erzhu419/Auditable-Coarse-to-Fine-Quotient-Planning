"""Producer for the preregistered generic factor planner campaign V122."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_generic_factor_planner_preregistration_v122 as pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.construction_k7_generic_subprogram_independent_verifier_v121r1 import (
    freeze_generic_subprogram_verification_v121r1,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_factor_planner_campaign_core_v122 import (
    build_generic_factor_planner_campaign_document_v122,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "a958bef4dfdc141f010e7ee7a93e27f84a9db36c5f630a3ebc656937733a6421"
EXPECTED_CANONICAL_BYTE_COUNT = 4_139_139
EXPECTED_CANONICAL_SHA256 = "1a71026284a5fe00a252bfa4a146315aaf4c229ea3dff5a954da8157a2042d0f"


class ConstructionK7GenericFactorPlannerCampaignV122Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7GenericFactorPlannerCampaignV122Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class GenericFactorPlannerCampaignV122:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("campaign_id") != self.campaign_id
            or pre.domains.extension_content_id_v122(
                pre.domains.CONSTRUCTION_K7_GENERIC_FACTOR_PLANNER_CAMPAIGN_V122_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V122 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: GenericFactorPlannerCampaignV122 | None = None


def run_generic_factor_planner_campaign_v122(
    source_campaign_bytes: Mapping[str, bytes],
    v121r1_campaign_raw: bytes,
    v121r1_verification_raw: bytes,
) -> GenericFactorPlannerCampaignV122:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V122 campaign exists; same identity will not be rerun")
    source_bytes = dict(source_campaign_bytes)
    try:
        registration = pre.verify_generic_factor_planner_preregistration_v122(
            pre.freeze_generic_factor_planner_preregistration_v122(
                source_bytes, v121r1_campaign_raw, v121r1_verification_raw
            ),
            source_bytes,
            v121r1_campaign_raw,
            v121r1_verification_raw,
        )
    except Exception as exc:
        _fail(f"V122 preregistered source evidence changed: {exc}")
    failed_v121_raw = (
        pre.SOURCE_ROOT
        / ".tmp/exact-freeze/v121_generic_artifact_subprogram_campaign.json"
    ).read_bytes()
    if (
        freeze_generic_subprogram_verification_v121r1(
            v121r1_campaign_raw, failed_v121_raw, source_bytes
        )
        != v121r1_verification_raw
    ):
        _fail("V122 frozen V121r1 independent verification changed")
    library = derive_artifact_factor_projection_v120(source_bytes)
    if library != registration.to_document()["artifact_factor_library"]:
        _fail("V122 preregistered factor library reconstruction changed")
    document = build_generic_factor_planner_campaign_document_v122(
        pre.campaign_config_v122(),
        preregistration_id=registration.preregistration_id,
        v121r1_campaign_id=pre.V121R1_CAMPAIGN_ID,
        v121r1_verification_id=pre.V121R1_VERIFICATION_ID,
        artifact_factor_library=library,
        source_campaign_bytes=source_bytes,
        strict_complete_factor_library=(
            v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V122 campaign changed")
    _CACHE = GenericFactorPlannerCampaignV122(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("CAMPAIGN_ID", "run_generic_factor_planner_campaign_v122")
