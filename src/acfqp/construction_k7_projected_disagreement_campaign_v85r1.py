"""Producer for the self-contained V85r1 projected-disagreement source Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_projected_disagreement_preregistration_v85r1 as pre
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70_pre
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.construction_k7_v84_template_library_v85r1 import (
    load_v84_template_library_v85r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.projected_disagreement_source_campaign_core_v85r1 import (
    build_projected_disagreement_source_campaign_document_v85r1,
)


CAMPAIGN_ID = "da749b6ad8996aba86896476fd7293540cca77cd1b4db7145b9bf4fe2759ec70"
EXPECTED_CANONICAL_BYTE_COUNT = 6_400_725
EXPECTED_CANONICAL_SHA256 = "9371c385cdbfa795752c79e57e3a557f278707df5341b52f81cfdc291e440541"


class ConstructionK7ProjectedDisagreementCampaignV85R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProjectedDisagreementCampaignV85R1Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ProjectedDisagreementCampaignV85R1:
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
            or pre.domains.extension_content_id_v85r1(
                pre.domains.CONSTRUCTION_K7_PROJECTED_DISAGREEMENT_CAMPAIGN_V85R1_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V85r1 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ProjectedDisagreementCampaignV85R1 | None = None


def run_projected_disagreement_campaign_v85r1() -> ProjectedDisagreementCampaignV85R1:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_projected_disagreement_preregistration_v85r1(
        pre.freeze_projected_disagreement_preregistration_v85r1()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"]["source_facts"]:  # noqa: SLF001
        _fail("V85r1 preregistered source closure changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    template_document = load_v84_template_library_v85r1()
    if template_document["library_artifact_id"] != pre.TEMPLATE_LIBRARY_ARTIFACT_ID:
        _fail("V85r1 self-contained template library changed")
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_projected_disagreement_source_campaign_document_v85r1(
        pre.campaign_config_v85r1(),
        preregistration.preregistration_id,
        pre.V84_FAILED_CAMPAIGN_ID,
        pre.V85_PRE_OUTCOME_FAILURE_ID,
        pre.TEMPLATE_LIBRARY_ARTIFACT_ID,
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
        _fail("frozen V85r1 campaign changed")
    _CACHE = ProjectedDisagreementCampaignV85R1(_ISSUER, raw, identity)
    return _CACHE


def verify_projected_disagreement_campaign_v85r1(
    value: Any,
) -> ProjectedDisagreementCampaignV85R1:
    if type(value) is not ProjectedDisagreementCampaignV85R1:
        _fail("V85r1 campaign rejects foreign values")
    value.__post_init__()
    expected = run_projected_disagreement_campaign_v85r1()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V85r1 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "run_projected_disagreement_campaign_v85r1",
    "verify_projected_disagreement_campaign_v85r1",
)
