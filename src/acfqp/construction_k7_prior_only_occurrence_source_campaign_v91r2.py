"""Producer for the preregistered V91r2 source-only Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_prior_only_occurrence_source_preregistration_v91r2 as pre
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.construction_k7_role_free_relational_template_library_v70 import (
    freeze_role_free_relational_template_library_v70,
    verify_role_free_relational_template_library_v70,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.prior_only_occurrence_source_campaign_core_v91r2 import (
    build_prior_only_occurrence_source_campaign_document_v91r2,
)


CAMPAIGN_ID = (
    "3a3d634361c16438ce9fe74f961a0c57f31f8476e8118869531fe849f68b42a6"
)
EXPECTED_CANONICAL_BYTE_COUNT = 473_436
EXPECTED_CANONICAL_SHA256 = (
    "c85f2c701bd7de569a0539194e8b36f728dae54a9af5949178b2f107b991e85f"
)


class ConstructionK7PriorOnlyOccurrenceSourceCampaignV91R2Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PriorOnlyOccurrenceSourceCampaignV91R2Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PriorOnlyOccurrenceSourceCampaignV91R2:
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
            or pre.domains.extension_content_id_v91r2(
                pre.domains.CONSTRUCTION_K7_PRIOR_ONLY_OCCURRENCE_SOURCE_CAMPAIGN_V91R2_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V91r2 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: PriorOnlyOccurrenceSourceCampaignV91R2 | None = None


def run_prior_only_occurrence_source_campaign_v91r2(
) -> PriorOnlyOccurrenceSourceCampaignV91R2:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64:
        _fail("frozen V91r2 outcome exists; same identity will not be rerun")
    preregistration = (
        pre.verify_prior_only_occurrence_source_preregistration_v91r2(
            pre.freeze_prior_only_occurrence_source_preregistration_v91r2()
        )
    )
    residual = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    ).to_document()
    template = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    ).to_document()
    factor_library = (
        v70.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_prior_only_occurrence_source_campaign_document_v91r2(
        pre.campaign_config_v91r2(),
        preregistration.preregistration_id,
        pre.FAILED_V91R1_ID,
        factor_library,
        residual["compiled_library"],
        template["compiled_template_library"],
        template["offline_template_source_ground_support_labels"],
    )
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V91r2 campaign changed")
    _CACHE = PriorOnlyOccurrenceSourceCampaignV91R2(_ISSUER, raw, identity)
    return _CACHE


def verify_prior_only_occurrence_source_campaign_v91r2(
    value: Any,
) -> PriorOnlyOccurrenceSourceCampaignV91R2:
    if type(value) is not PriorOnlyOccurrenceSourceCampaignV91R2:
        _fail("V91r2 campaign rejects foreign values")
    value.__post_init__()
    expected = run_prior_only_occurrence_source_campaign_v91r2()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V91r2 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "run_prior_only_occurrence_source_campaign_v91r2",
    "verify_prior_only_occurrence_source_campaign_v91r2",
)
