"""Producer for the preregistered V79 successor-projected source Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_successor_projected_preregistration_v79 as pre
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
from acfqp.successor_projected_pooled_source_campaign_core_v79 import (
    build_successor_projected_pooled_source_campaign_document_v79,
)


CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64
FROZEN_FAILURE_ID = "8f506014e933c2cf83dff2e33a1f1bef11d49617074d7d978f16964bd9d19a88"
EXPECTED_FAILURE_CANONICAL_BYTE_COUNT = 1_139
EXPECTED_FAILURE_CANONICAL_SHA256 = "dcc71d7144013ebc5675ed2de2c8730184380fb25486ea46709f264620ed4e98"


class ConstructionK7SuccessorProjectedCampaignV79Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SuccessorProjectedCampaignV79Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SuccessorProjectedCampaignV79:
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
            or pre.domains.extension_content_id_v79(
                pre.domains.CONSTRUCTION_K7_SUCCESSOR_PROJECTED_CAMPAIGN_V79_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V79 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


@dataclass(frozen=True, slots=True)
class SuccessorProjectedFailureV79:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    failure_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items() if key != "failure_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("failure_id") != self.failure_id
            or pre.domains.extension_content_id_v79(
                pre.domains.CONSTRUCTION_K7_SUCCESSOR_PROJECTED_CAMPAIGN_V79_DOMAIN,
                payload,
            )
            != self.failure_id
        ):
            _fail("V79 failure bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: SuccessorProjectedCampaignV79 | None = None
_FAILURE_CACHE: SuccessorProjectedFailureV79 | None = None


def _failure_document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.successor_projected_pooled_source_failure.v79",
        "preregistration_id": pre.PREREGISTRATION_ID,
        "v78_failed_campaign_id": pre.V78_FAILED_CAMPAIGN_ID,
        "source_family": pre.SOURCE_FAMILY,
        "source_pool_seeds": list(pre.SOURCE_POOL_SEEDS),
        "failure_phase": "CANONICAL_SOURCE_POOL_COMPATIBILITY_CHECK",
        "exception_module": "acfqp.generic_canonical_source_pool_v48",
        "exception_type": "GenericCanonicalSourcePoolV48Error",
        "exception_message": "V48 source members are not structurally compatible",
        "source_member_processes_completed_before_pool_attempt": True,
        "campaign_document_emitted": False,
        "campaign_id": None,
        "fresh_target_outcome_count": 0,
        "target_execution_performed": False,
        "same_identity_rerun_forbidden": True,
        "resource_schedule_violated": False,
        "typed_noncertificate": True,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "failure_id": pre.domains.extension_content_id_v79(
            pre.domains.CONSTRUCTION_K7_SUCCESSOR_PROJECTED_CAMPAIGN_V79_DOMAIN,
            payload,
        ),
    }


def freeze_successor_projected_failure_v79() -> SuccessorProjectedFailureV79:
    global _FAILURE_CACHE
    if _FAILURE_CACHE is not None:
        return _FAILURE_CACHE
    document = _failure_document()
    raw = canonical_json_bytes(document)
    identity = document["failure_id"]
    if FROZEN_FAILURE_ID != "0" * 64 and (
        identity != FROZEN_FAILURE_ID
        or len(raw) != EXPECTED_FAILURE_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_FAILURE_CANONICAL_SHA256
    ):
        _fail("frozen V79 failure changed")
    _FAILURE_CACHE = SuccessorProjectedFailureV79(_ISSUER, raw, identity)
    return _FAILURE_CACHE


def run_successor_projected_campaign_v79() -> SuccessorProjectedCampaignV79:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if FROZEN_FAILURE_ID != "0" * 64:
        _fail("frozen V79 execution failed; same identity will not be rerun")
    preregistration = pre.verify_successor_projected_preregistration_v79(
        pre.freeze_successor_projected_preregistration_v79()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][  # noqa: SLF001
        "source_facts"
    ]:
        _fail("V79 preregistered source closure changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    template_artifact = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    )
    if template_artifact.library_artifact_id != pre.TEMPLATE_LIBRARY_ARTIFACT_ID:
        _fail("V79 frozen template library changed")
    template_document = template_artifact.to_document()
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_successor_projected_pooled_source_campaign_document_v79(
        pre.campaign_config_v79(),
        preregistration.preregistration_id,
        pre.V78_FAILED_CAMPAIGN_ID,
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
        _fail("frozen V79 campaign changed")
    _CACHE = SuccessorProjectedCampaignV79(_ISSUER, raw, identity)
    return _CACHE


def verify_successor_projected_campaign_v79(
    value: Any,
) -> SuccessorProjectedCampaignV79:
    if type(value) is not SuccessorProjectedCampaignV79:
        _fail("V79 campaign rejects foreign values")
    value.__post_init__()
    expected = run_successor_projected_campaign_v79()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V79 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "FROZEN_FAILURE_ID",
    "freeze_successor_projected_failure_v79",
    "run_successor_projected_campaign_v79",
    "verify_successor_projected_campaign_v79",
)
