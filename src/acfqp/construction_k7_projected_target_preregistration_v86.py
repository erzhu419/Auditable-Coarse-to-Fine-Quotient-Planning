"""Outcome-free preregistration for V86 fresh-target model transfer."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v86 as domains
from acfqp import construction_k7_projected_disagreement_preregistration_v85r1 as previous
from acfqp.construction_k7_projected_model_artifact_v86 import MODEL_ARTIFACT_ID
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.projected_disagreement_target_campaign_core_v86 import (
    build_projected_disagreement_target_campaign_document_v86,
)


IMPLEMENTATION_COMMIT = "4ff303e"
PREREGISTRATION_ID = "aa34820576e1f935782ec6d3be5151be4cda750e33e7b523eccd209c7dc4bb78"
EXPECTED_CANONICAL_BYTE_COUNT = 5_386
EXPECTED_CANONICAL_SHA256 = "9080c98178ddf40b61d8dcc0290a1ee17815d6c7654f555a32d1c2fdac4a4139"
V85R1_CAMPAIGN_ID = "da749b6ad8996aba86896476fd7293540cca77cd1b4db7145b9bf4fe2759ec70"
V85R1_VERIFICATION_ID = "391038636f3b1744112f1a4a08b9d4acb5d32f8d19c27af603e69431cd40ad0f"
TARGET_FAMILY = "BALANCED_BATCH_REFINEMENT"
TARGET_SEEDS = (889_101, 889_102, 889_103, 889_104, 889_105, 889_106)
SOURCE_EPISODE_INDEX = 0
TARGET_EPISODE_INDEX = 7
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 6
MINIMUM_COMPATIBLE_COMPLETED_TARGET_COUNT = 2
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "artifacts/world_model/v86_projected_disagreement_model.json",
    "src/acfqp/construction_k7_domain_registry_extension_v86.py",
    "src/acfqp/construction_k7_projected_model_artifact_v86.py",
    "src/acfqp/generic_projected_disagreement_certificate_planner_v57.py",
    "src/acfqp/generic_projected_disagreement_planner_v56.py",
    "src/acfqp/generic_projected_disagreement_model_compiler_v56.py",
    "src/acfqp/projected_disagreement_target_campaign_core_v86.py",
    "src/acfqp/construction_k7_projected_target_campaign_v86.py",
)


class ConstructionK7ProjectedTargetPreregistrationV86Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProjectedTargetPreregistrationV86Error(message)


def _source_facts() -> list[dict[str, Any]]:
    result = []
    for relative in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        result.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return result


def _callable_fact(value: Any) -> dict[str, Any]:
    return {
        "module": value.__module__,
        "qualname": value.__qualname__,
        "code_sha256": hashlib.sha256(marshal.dumps(value.__code__)).hexdigest(),
    }


def campaign_config_v86() -> dict[str, Any]:
    config = previous.campaign_config_v85r1()
    config.update(
        target_family=TARGET_FAMILY,
        target_seeds=TARGET_SEEDS,
        target_episode_index=TARGET_EPISODE_INDEX,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
        minimum_compatible_completed_target_count=(
            MINIMUM_COMPATIBLE_COMPLETED_TARGET_COUNT
        ),
        maximum_target_ground_support_labels=100_000,
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.projected_disagreement_target_preregistration.v86",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v85r1_campaign_id": V85R1_CAMPAIGN_ID,
            "v85r1_verification_id": V85R1_VERIFICATION_ID,
            "model_artifact_id": MODEL_ARTIFACT_ID,
            "v85_pre_outcome_failure_id": previous.V85_PRE_OUTCOME_FAILURE_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v86_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V86),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_projected_disagreement_target_campaign_document_v86
            ),
            "frozen_before_any_registered_v86_target_outcome": True,
        },
        "identity_contract": {
            "target_family": TARGET_FAMILY,
            "target_seeds": list(TARGET_SEEDS),
            "target_seed_count": len(TARGET_SEEDS),
            "target_seeds_unique": len(set(TARGET_SEEDS)) == len(TARGET_SEEDS),
            "target_seeds_disjoint_from_all_v85r1_sources": min(TARGET_SEEDS)
            > max(previous.SOURCE_POOL_SEEDS),
            "target_episode_index": TARGET_EPISODE_INDEX,
            "source_episode_index": SOURCE_EPISODE_INDEX,
            "source_and_target_episode_indices_disjoint": TARGET_EPISODE_INDEX
            != SOURCE_EPISODE_INDEX,
        },
        "construction_contract": {
            "source_model_frozen_before_targets": True,
            "target_outcomes_cannot_select_or_refit_model": True,
            "same_exact_certificate_engine_in_both_arms": True,
            "only_world_model_availability_differs_between_arms": True,
            "abstract_planning_uses_no_ground_transition": True,
            "every_ground_query_must_follow_failed_certificate": True,
            "query_local_exact_overlay_only_safety_authority": True,
            "incompatible_schema_must_reject_before_abstract_search": True,
            "sample_reduction_measured_but_not_required_for_gate": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "minimum_compatible_completed_target_count": (
                MINIMUM_COMPATIBLE_COMPLETED_TARGET_COUNT
            ),
            "every_compatible_target_must_complete_both_arms": True,
            "abstract_world_model_ordering_must_be_used": True,
            "certificate_failure_only_ground_discipline_required": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "target_sample_reduction_required": False,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "maximum_target_ground_support_labels_per_arm": 100_000,
            "maximum_relational_support_branch_evaluations_per_plan": 1_000_000,
        },
        "accounting_contract": {
            "offline_source_labels_separate": True,
            "target_common_partial_labels_separate": True,
            "derived_and_strict_certificate_labels_separate": True,
            "execution_steps_separate": True,
            "abstract_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v86_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "multi_step_planning_primarily_in_abstract_model_claimed": False,
            "sample_tax_reduction_verified": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_v86_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v86(
            domains.CONSTRUCTION_K7_PROJECTED_TARGET_PREREGISTRATION_V86_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ProjectedTargetPreregistrationV86:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items() if key != "preregistration_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v86(
                domains.CONSTRUCTION_K7_PROJECTED_TARGET_PREREGISTRATION_V86_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V86 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ProjectedTargetPreregistrationV86 | None = None


def freeze_projected_target_preregistration_v86(
) -> ProjectedTargetPreregistrationV86:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V86 preregistration changed")
    _CACHE = ProjectedTargetPreregistrationV86(_ISSUER, raw, identity)
    return _CACHE


def verify_projected_target_preregistration_v86(
    value: Any,
) -> ProjectedTargetPreregistrationV86:
    if type(value) is not ProjectedTargetPreregistrationV86:
        _fail("V86 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_projected_target_preregistration_v86()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V86 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "TARGET_SEEDS",
    "campaign_config_v86",
    "freeze_projected_target_preregistration_v86",
    "verify_projected_target_preregistration_v86",
)
