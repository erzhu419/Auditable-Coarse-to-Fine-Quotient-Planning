"""Producer for the preregistered V80 structurally routed source Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_structural_route_preregistration_v80 as pre
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
from acfqp.structurally_routed_source_campaign_core_v80 import (
    build_structurally_routed_source_campaign_document_v80,
)


CAMPAIGN_ID = "baba3898eec69852d3275dd61daa2a6823512879bd44df1a031cc50d8106476d"
EXPECTED_CANONICAL_BYTE_COUNT = 1_452_985
EXPECTED_CANONICAL_SHA256 = "e0a142adc327f32d49de6313ab9af001c659e05fe80c25c5ae55348b54935d4c"


class ConstructionK7StructuralRouteCampaignV80Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7StructuralRouteCampaignV80Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class StructuralRouteCampaignV80:
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
            or pre.domains.extension_content_id_v80(
                pre.domains.CONSTRUCTION_K7_STRUCTURAL_ROUTE_CAMPAIGN_V80_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V80 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: StructuralRouteCampaignV80 | None = None


def run_structural_route_campaign_v80() -> StructuralRouteCampaignV80:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_structural_route_preregistration_v80(
        pre.freeze_structural_route_preregistration_v80()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][  # noqa: SLF001
        "source_facts"
    ]:
        _fail("V80 preregistered source closure changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    template_artifact = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    )
    if template_artifact.library_artifact_id != pre.TEMPLATE_LIBRARY_ARTIFACT_ID:
        _fail("V80 frozen template library changed")
    template_document = template_artifact.to_document()
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_structurally_routed_source_campaign_document_v80(
        pre.campaign_config_v80(),
        preregistration.preregistration_id,
        pre.V79_FROZEN_FAILURE_ID,
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
        _fail("frozen V80 campaign changed")
    _CACHE = StructuralRouteCampaignV80(_ISSUER, raw, identity)
    return _CACHE


def verify_structural_route_campaign_v80(
    value: Any,
) -> StructuralRouteCampaignV80:
    if type(value) is not StructuralRouteCampaignV80:
        _fail("V80 campaign rejects foreign values")
    value.__post_init__()
    expected = run_structural_route_campaign_v80()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V80 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "run_structural_route_campaign_v80",
    "verify_structural_route_campaign_v80",
)
