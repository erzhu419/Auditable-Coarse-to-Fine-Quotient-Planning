"""Producer for the preregistered V91r1 occurrence-balanced source Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_occurrence_balanced_source_preregistration_v91r1 as pre
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.construction_k7_role_free_relational_template_library_v70 import (
    freeze_role_free_relational_template_library_v70,
    verify_role_free_relational_template_library_v70,
)
from acfqp.occurrence_balanced_source_campaign_core_v91r1 import (
    build_occurrence_balanced_source_campaign_document_v91r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
FROZEN_FAILURE_ID = (
    "6c076b761b7b2b9e68a0ac49a7f7b8ae1accb43e2b140486b1c268eb23b179c6"
)


class ConstructionK7OccurrenceBalancedSourceCampaignV91R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OccurrenceBalancedSourceCampaignV91R1Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OccurrenceBalancedSourceCampaignV91R1:
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
            or pre.domains.extension_content_id_v91r1(
                pre.domains.CONSTRUCTION_K7_OCCURRENCE_BALANCED_SOURCE_CAMPAIGN_V91R1_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V91r1 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: OccurrenceBalancedSourceCampaignV91R1 | None = None


def run_occurrence_balanced_source_campaign_v91r1(
) -> OccurrenceBalancedSourceCampaignV91R1:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if CAMPAIGN_ID != "0" * 64 or FROZEN_FAILURE_ID != "0" * 64:
        _fail("frozen V91r1 outcome exists; same identity will not be rerun")
    preregistration = (
        pre.verify_occurrence_balanced_source_preregistration_v91r1(
            pre.freeze_occurrence_balanced_source_preregistration_v91r1()
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
    document = build_occurrence_balanced_source_campaign_document_v91r1(
        pre.campaign_config_v91r1(),
        preregistration.preregistration_id,
        pre.FAILED_V91_CAMPAIGN_ID,
        pre.FAILED_V91_VERIFICATION_ID,
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
        _fail("frozen V91r1 campaign changed")
    _CACHE = OccurrenceBalancedSourceCampaignV91R1(_ISSUER, raw, identity)
    return _CACHE


def verify_occurrence_balanced_source_campaign_v91r1(
    value: Any,
) -> OccurrenceBalancedSourceCampaignV91R1:
    if type(value) is not OccurrenceBalancedSourceCampaignV91R1:
        _fail("V91r1 campaign rejects foreign values")
    value.__post_init__()
    expected = run_occurrence_balanced_source_campaign_v91r1()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V91r1 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "FROZEN_FAILURE_ID",
    "run_occurrence_balanced_source_campaign_v91r1",
    "verify_occurrence_balanced_source_campaign_v91r1",
)
