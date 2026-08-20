"""Producer for the preregistered V82 bounded multi-source Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_bounded_source_preregistration_v82 as pre
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70_pre
from acfqp.bounded_multi_source_campaign_core_v82 import (
    build_bounded_multi_source_campaign_document_v82,
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
FROZEN_FAILURE_ID = "9fa9260a647c5b975f4b441d2666c06c66dccc335d52794f7df4733d84490e6c"
EXPECTED_FAILURE_CANONICAL_BYTE_COUNT = 1_287
EXPECTED_FAILURE_CANONICAL_SHA256 = "0b2af555695d17c64ee8c5258b67884aa97c9dd501d333e54f187526ac7b0b79"


class ConstructionK7BoundedSourceCampaignV82Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7BoundedSourceCampaignV82Error(message)


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class BoundedSourceCampaignV82:
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
            or pre.domains.extension_content_id_v82(
                pre.domains.CONSTRUCTION_K7_BOUNDED_SOURCE_CAMPAIGN_V82_DOMAIN,
                payload,
            )
            != self.campaign_id
        ):
            _fail("V82 campaign bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


@dataclass(frozen=True, slots=True)
class BoundedSourceFailureV82:
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
            or pre.domains.extension_content_id_v82(
                pre.domains.CONSTRUCTION_K7_BOUNDED_SOURCE_CAMPAIGN_V82_DOMAIN,
                payload,
            )
            != self.failure_id
        ):
            _fail("V82 failure bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: BoundedSourceCampaignV82 | None = None
_FAILURE_CACHE: BoundedSourceFailureV82 | None = None


def _failure_document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.bounded_multi_source_failure.v82",
        "preregistration_id": pre.PREREGISTRATION_ID,
        "v81_failed_campaign_id": pre.V81_FAILED_CAMPAIGN_ID,
        "source_family": pre.SOURCE_FAMILY,
        "source_pool_seeds": list(pre.SOURCE_POOL_SEEDS),
        "failure_phase": "TERMINAL_FRONTIER_COMPILATION_EXACTNESS_CHECK",
        "exception_module": (
            "acfqp.generic_version_space_retaining_model_compiler_v51"
        ),
        "exception_type": "GenericVersionSpaceRetainingModelCompilerV51Error",
        "exception_message": (
            "V51 terminal frontier is not exact on acquired successors"
        ),
        "all_preregistered_source_member_processes_completed": True,
        "structural_partition_completed": True,
        "at_least_one_group_model_compilation_attempted": True,
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
        "failure_id": pre.domains.extension_content_id_v82(
            pre.domains.CONSTRUCTION_K7_BOUNDED_SOURCE_CAMPAIGN_V82_DOMAIN,
            payload,
        ),
    }


def freeze_bounded_source_failure_v82() -> BoundedSourceFailureV82:
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
        _fail("frozen V82 failure changed")
    _FAILURE_CACHE = BoundedSourceFailureV82(_ISSUER, raw, identity)
    return _FAILURE_CACHE


def run_bounded_source_campaign_v82() -> BoundedSourceCampaignV82:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if FROZEN_FAILURE_ID != "0" * 64:
        _fail("frozen V82 execution failed; same identity will not be rerun")
    preregistration = pre.verify_bounded_source_preregistration_v82(
        pre.freeze_bounded_source_preregistration_v82()
    )
    if pre._source_facts() != preregistration.to_document()["source_closure"][  # noqa: SLF001
        "source_facts"
    ]:
        _fail("V82 preregistered source closure changed")
    residual_artifact = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    )
    template_artifact = verify_role_free_relational_template_library_v70(
        freeze_role_free_relational_template_library_v70()
    )
    if template_artifact.library_artifact_id != pre.TEMPLATE_LIBRARY_ARTIFACT_ID:
        _fail("V82 frozen template library changed")
    template_document = template_artifact.to_document()
    factor_library = (
        v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    document = build_bounded_multi_source_campaign_document_v82(
        pre.campaign_config_v82(),
        preregistration.preregistration_id,
        pre.V81_FAILED_CAMPAIGN_ID,
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
        _fail("frozen V82 campaign changed")
    _CACHE = BoundedSourceCampaignV82(_ISSUER, raw, identity)
    return _CACHE


def verify_bounded_source_campaign_v82(value: Any) -> BoundedSourceCampaignV82:
    if type(value) is not BoundedSourceCampaignV82:
        _fail("V82 campaign rejects foreign values")
    value.__post_init__()
    expected = run_bounded_source_campaign_v82()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V82 campaign differs from frozen output")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "FROZEN_FAILURE_ID",
    "freeze_bounded_source_failure_v82",
    "run_bounded_source_campaign_v82",
    "verify_bounded_source_campaign_v82",
)
