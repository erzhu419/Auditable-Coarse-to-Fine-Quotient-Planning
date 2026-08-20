"""Producer for the preregistered V85 projected-disagreement source Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_projected_disagreement_preregistration_v85 as pre
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
from acfqp.projected_disagreement_source_campaign_core_v85 import (
    build_projected_disagreement_source_campaign_document_v85,
)


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
PRE_OUTCOME_FAILURE_ID = "82f3212d9e755c769795d1a908bbb1aac33b18de8f6cbe5a407256cac3e60acb"
PRE_OUTCOME_FAILURE_BYTE_COUNT = 797
PRE_OUTCOME_FAILURE_SHA256 = "e6235deeb980b2f7cc64d2ac5db0fc23064930ad82012fcc84b61aea1098d44d"


class ConstructionK7ProjectedDisagreementCampaignV85Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProjectedDisagreementCampaignV85Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ProjectedDisagreementCampaignV85:
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
            or pre.domains.extension_content_id_v85(
                pre.domains.CONSTRUCTION_K7_PROJECTED_DISAGREEMENT_CAMPAIGN_V85_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V85 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ProjectedDisagreementCampaignV85 | None = None


def _pre_outcome_failure_document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.projected_disagreement_pre_outcome_failure.v85",
        "preregistration_id": pre.PREREGISTRATION_ID,
        "failed_operation": "MATERIALIZE_FROZEN_V70_TEMPLATE_LIBRARY",
        "exception_type": (
            "ConstructionK7SourceCompleteRelationalPreregistrationV69Error"
        ),
        "exception_message": "frozen V69 preregistration changed",
        "fresh_source_member_execution_started": False,
        "fresh_source_outcome_count": 0,
        "campaign_document_created": False,
        "same_identity_rerun_forbidden": True,
        "withdrawn_earlier_preregistration_preserved": True,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "failure_id": pre.domains.extension_content_id_v85(
            pre.domains.CONSTRUCTION_K7_PROJECTED_DISAGREEMENT_CAMPAIGN_V85_DOMAIN,
            payload,
        ),
    }


def frozen_pre_outcome_failure_v85() -> dict[str, Any]:
    document = _pre_outcome_failure_document()
    raw = canonical_json_bytes(document)
    if PRE_OUTCOME_FAILURE_ID != "0" * 64 and (
        document["failure_id"] != PRE_OUTCOME_FAILURE_ID
        or len(raw) != PRE_OUTCOME_FAILURE_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != PRE_OUTCOME_FAILURE_SHA256
    ):
        _fail("frozen V85 pre-outcome failure changed")
    return document


def run_projected_disagreement_campaign_v85() -> ProjectedDisagreementCampaignV85:
    global _CACHE
    if PRE_OUTCOME_FAILURE_ID != "0" * 64:
        failure = frozen_pre_outcome_failure_v85()
        _fail(
            "V85 failed before fresh outcomes and is frozen; same-identity rerun "
            f"forbidden: {failure['failure_id']}"
        )
    if _CACHE is not None:
        return _CACHE
    preregistration = pre.verify_projected_disagreement_preregistration_v85(
        pre.freeze_projected_disagreement_preregistration_v85()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"]["source_facts"]:  # noqa: SLF001
        _fail("V85 preregistered source closure changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    template_artifact = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    )
    if template_artifact.library_artifact_id != pre.TEMPLATE_LIBRARY_ARTIFACT_ID:
        _fail("V85 frozen template library changed")
    template_document = template_artifact.to_document()
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_projected_disagreement_source_campaign_document_v85(
        pre.campaign_config_v85(),
        preregistration.preregistration_id,
        pre.V84_FAILED_CAMPAIGN_ID,
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
        _fail("frozen V85 campaign changed")
    _CACHE = ProjectedDisagreementCampaignV85(_ISSUER, raw, identity)
    return _CACHE


def verify_projected_disagreement_campaign_v85(
    value: Any,
) -> ProjectedDisagreementCampaignV85:
    if type(value) is not ProjectedDisagreementCampaignV85:
        _fail("V85 campaign rejects foreign values")
    value.__post_init__()
    expected = run_projected_disagreement_campaign_v85()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V85 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "PRE_OUTCOME_FAILURE_ID",
    "frozen_pre_outcome_failure_v85",
    "run_projected_disagreement_campaign_v85",
    "verify_projected_disagreement_campaign_v85",
)
