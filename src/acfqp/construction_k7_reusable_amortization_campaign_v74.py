"""Producer for the preregistered V74 reusable-model amortization campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_reusable_amortization_preregistration_v74 as pre
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
from acfqp.reusable_amortization_campaign_core_v74 import (
    build_reusable_amortization_campaign_document_v74,
)


CAMPAIGN_ID = "a60009b54923558baca3dd26af35c298b6618a86c3c4ec64639d7efa4c7a76f4"
EXPECTED_CANONICAL_BYTE_COUNT = 16_861_847
EXPECTED_CANONICAL_SHA256 = "c71d4cd434e40a2f4e8a6d19a5442e11b35a13c0026a2d93eae7ba02a94c7669"


class ConstructionK7ReusableAmortizationCampaignV74Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReusableAmortizationCampaignV74Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ReusableAmortizationCampaignV74:
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
            or pre.domains.extension_content_id_v74(
                pre.domains.CONSTRUCTION_K7_REUSABLE_AMORTIZATION_CAMPAIGN_V74_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V74 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ReusableAmortizationCampaignV74 | None = None


def run_reusable_amortization_campaign_v74() -> ReusableAmortizationCampaignV74:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_reusable_amortization_preregistration_v74(
        pre.freeze_reusable_amortization_preregistration_v74()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][  # noqa: SLF001
        "source_facts"
    ]:
        _fail("V74 preregistered source closure changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    template_artifact = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    )
    if template_artifact.library_artifact_id != pre.TEMPLATE_LIBRARY_ARTIFACT_ID:
        _fail("V74 frozen terminal-template library changed")
    template_document = template_artifact.to_document()
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_reusable_amortization_campaign_document_v74(
        pre.campaign_config_v74(),
        preregistration.preregistration_id,
        pre.V73_CAMPAIGN_ID,
        pre.V73_VERIFICATION_ID,
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
        _fail("frozen V74 campaign changed")
    _CACHE = ReusableAmortizationCampaignV74(_ISSUER, raw, identity)
    return _CACHE


def verify_reusable_amortization_campaign_v74(
    value: Any,
) -> ReusableAmortizationCampaignV74:
    if type(value) is not ReusableAmortizationCampaignV74:
        _fail("V74 campaign rejects foreign values")
    value.__post_init__()
    expected = run_reusable_amortization_campaign_v74()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V74 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "run_reusable_amortization_campaign_v74",
    "verify_reusable_amortization_campaign_v74",
)
