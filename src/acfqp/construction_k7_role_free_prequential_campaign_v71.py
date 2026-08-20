"""Producer for the preregistered V71 prequential sample-tax campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_role_free_prequential_preregistration_v71 as pre
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70_pre
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.construction_k7_role_free_relational_template_library_v70 import (
    freeze_role_free_relational_template_library_v70,
    verify_role_free_relational_template_library_v70,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.role_free_prequential_campaign_core_v71 import (
    build_role_free_prequential_campaign_document_v71,
)


CAMPAIGN_ID = "a8a9ebead0bcfeb1587be1a6b21ddb11189ec74e26d871ab5ada0ec279261e17"
EXPECTED_CANONICAL_BYTE_COUNT = 3_531_014
EXPECTED_CANONICAL_SHA256 = "4d8f6afa609e38aaad4f714abd550dcc9fbebe0dcadcc5611e92cc81e9f6e51d"
REGISTERED_FAILURE_ID = ""


class ConstructionK7RoleFreePrequentialCampaignV71Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RoleFreePrequentialCampaignV71Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class RoleFreePrequentialCampaignV71:
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
            or pre.domains.extension_content_id_v71(
                pre.domains.CONSTRUCTION_K7_ROLE_FREE_PREQUENTIAL_CAMPAIGN_V71_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V71 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: RoleFreePrequentialCampaignV71 | None = None


def run_role_free_prequential_campaign_v71() -> RoleFreePrequentialCampaignV71:
    global _CACHE
    if REGISTERED_FAILURE_ID:
        _fail(f"V71 registered failure is frozen: {REGISTERED_FAILURE_ID}")
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_role_free_prequential_preregistration_v71(
        pre.freeze_role_free_prequential_preregistration_v71()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][
        "source_facts"
    ]:
        _fail("V71 preregistered source closure changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    template_artifact = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    )
    if (
        residual_artifact.library_artifact_id != pre.V62_LIBRARY_ID
        or template_artifact.library_artifact_id
        != pre.TEMPLATE_LIBRARY_ARTIFACT_ID
    ):
        _fail("V71 frozen library predecessor changed")
    template_document = template_artifact.to_document()
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_role_free_prequential_campaign_document_v71(
        pre.campaign_config_v71(),
        preregistration.preregistration_id,
        pre.V70_CAMPAIGN_ID,
        pre.V70_VERIFICATION_ID,
        template_artifact.library_artifact_id,
        factor_library,
        residual_artifact.to_document()["compiled_library"],
        template_document["compiled_template_library"],
        template_document["offline_template_source_ground_support_labels"],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V71 campaign changed")
    _CACHE = RoleFreePrequentialCampaignV71(_ISSUER, raw, identity)
    return _CACHE


def verify_role_free_prequential_campaign_v71(
    value: Any,
) -> RoleFreePrequentialCampaignV71:
    if type(value) is not RoleFreePrequentialCampaignV71:
        _fail("V71 campaign rejects foreign values")
    value.__post_init__()
    expected = run_role_free_prequential_campaign_v71()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V71 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "run_role_free_prequential_campaign_v71",
    "verify_role_free_prequential_campaign_v71",
)
