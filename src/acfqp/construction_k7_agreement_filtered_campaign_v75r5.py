"""Producer for the preregistered V75r5 agreement-filtered campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_agreement_filtered_preregistration_v75r5 as pre
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70_pre
from acfqp.agreement_filtered_priority_campaign_core_v75r5 import (
    build_agreement_filtered_priority_campaign_document_v75r5,
)
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.construction_k7_role_free_relational_template_library_v70 import (
    freeze_role_free_relational_template_library_v70,
    verify_role_free_relational_template_library_v70,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7AgreementFilteredCampaignV75R5Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AgreementFilteredCampaignV75R5Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AgreementFilteredCampaignV75R5:
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
            or pre.domains.extension_content_id_v75r5(
                pre.domains.CONSTRUCTION_K7_AGREEMENT_FILTERED_CAMPAIGN_V75R5_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V75r5 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: AgreementFilteredCampaignV75R5 | None = None


def run_agreement_filtered_campaign_v75r5() -> AgreementFilteredCampaignV75R5:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_agreement_filtered_preregistration_v75r5(
        pre.freeze_agreement_filtered_preregistration_v75r5()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][  # noqa: SLF001
        "source_facts"
    ]:
        _fail("V75r5 preregistered source closure changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    template_artifact = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    )
    if template_artifact.library_artifact_id != pre.TEMPLATE_LIBRARY_ARTIFACT_ID:
        _fail("V75r5 frozen terminal-template library changed")
    template_document = template_artifact.to_document()
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_agreement_filtered_priority_campaign_document_v75r5(
        pre.campaign_config_v75r5(),
        preregistration.preregistration_id,
        pre.PRESERVED_PREDECESSOR_IDS,
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
        _fail("frozen V75r5 campaign changed")
    _CACHE = AgreementFilteredCampaignV75R5(_ISSUER, raw, identity)
    return _CACHE


def verify_agreement_filtered_campaign_v75r5(
    value: Any,
) -> AgreementFilteredCampaignV75R5:
    if type(value) is not AgreementFilteredCampaignV75R5:
        _fail("V75r5 campaign rejects foreign values")
    value.__post_init__()
    expected = run_agreement_filtered_campaign_v75r5()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V75r5 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "run_agreement_filtered_campaign_v75r5",
    "verify_agreement_filtered_campaign_v75r5",
)
