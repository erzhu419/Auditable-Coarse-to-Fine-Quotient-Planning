"""Outcome-free preregistration for the V75r3 fail-closed campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v75r3 as domains
from acfqp import construction_k7_normalized_priority_preregistration_v75r2 as previous
from acfqp.fail_closed_normalized_priority_campaign_core_v75r3 import (
    build_fail_closed_normalized_priority_campaign_document_v75r3,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "645f2a8"
PREREGISTRATION_ID = "0ee7f7594a4e7b8d85ac222b8abd3293af248a205cd70a97e4cf425959a135ad"
EXPECTED_CANONICAL_BYTE_COUNT = 5_794
EXPECTED_CANONICAL_SHA256 = "d3464498727a9be22d33b3b099f820b77f0bf634323c8fad6fd8eb901c7d3224"
V75_FAILURE_ID = previous.V75_FAILURE_ID
V75R1_FAILURE_ID = previous.V75R1_FAILURE_ID
V75R2_PREREGISTRATION_ID = previous.PREREGISTRATION_ID
V75R2_FAILURE_ID = "1cd0c27a096001dd98a89d8e169642cb1e75fb716f39ff649dec1997858d9b48"
TEMPLATE_LIBRARY_ARTIFACT_ID = previous.TEMPLATE_LIBRARY_ARTIFACT_ID
SOURCE_SEED_BY_FAMILY = dict(previous.SOURCE_SEED_BY_FAMILY)
FRESH_TARGET_SEEDS = {
    "COUPLED_EXCHANGE": (764_201, 764_202),
    "MAINTENANCE_CASCADE": (764_301, 764_302),
}
TARGET_EPISODE_INDEX = 4
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v75r3.py",
    "src/acfqp/fail_closed_normalized_priority_campaign_core_v75r3.py",
    "src/acfqp/normalized_portable_priority_campaign_core_v75r2.py",
    "src/acfqp/generic_flat_action_adapter_v45.py",
    "src/acfqp/generic_portable_certificate_query_priority_v44.py",
    "src/acfqp/construction_k7_normalized_priority_failure_v75r2.py",
    "src/acfqp/construction_k7_portable_priority_failure_v75r1.py",
    "src/acfqp/construction_k7_cross_occurrence_reuse_failure_v75.py",
)


class ConstructionK7FailClosedPriorityPreregistrationV75R3Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FailClosedPriorityPreregistrationV75R3Error(message)


def _source_facts() -> list[dict[str, Any]]:
    facts = []
    for relative in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        facts.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return facts


def _callable_fact(value: Any) -> dict[str, Any]:
    return {
        "module": value.__module__,
        "qualname": value.__qualname__,
        "code_sha256": hashlib.sha256(marshal.dumps(value.__code__)).hexdigest(),
    }


def campaign_config_v75r3() -> dict[str, Any]:
    config = previous.campaign_config_v75r2()
    config.update(
        fresh_target_seeds={key: tuple(value) for key, value in FRESH_TARGET_SEEDS.items()},
        target_episode_index=TARGET_EPISODE_INDEX,
    )
    return config


def _document() -> dict[str, Any]:
    target_seeds = tuple(seed for values in FRESH_TARGET_SEEDS.values() for seed in values)
    payload = {
        "schema": "acfqp.fail_closed_priority_preregistration.v75r3",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v75_failure_id": V75_FAILURE_ID,
            "v75r1_failure_id": V75R1_FAILURE_ID,
            "v75r2_preregistration_id": V75R2_PREREGISTRATION_ID,
            "v75r2_failure_id": V75R2_FAILURE_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v75r3_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75R3),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_fail_closed_normalized_priority_campaign_document_v75r3
            ),
            "frozen_before_any_registered_v75r3_target_outcome": True,
        },
        "failure_driven_successor_contract": {
            "v75r2_aggregation_failure_preserved": True,
            "failed_arm_records_retained_before_any_success_only_field_access": True,
            "no_v75r2_target_identity_reused": True,
            "same_scientific_reduction_gate_retained": True,
        },
        "identity_contract": {
            "source_seed_by_family": dict(SOURCE_SEED_BY_FAMILY),
            "fresh_target_seeds": {
                key: list(value) for key, value in FRESH_TARGET_SEEDS.items()
            },
            "fresh_target_seed_count": len(set(target_seeds)),
            "fresh_target_seed_identities_unique": len(target_seeds) == len(set(target_seeds)),
            "fresh_target_seeds_disjoint_from_predecessors": min(target_seeds) > 764_000,
            "source_and_target_seeds_disjoint": not (
                set(SOURCE_SEED_BY_FAMILY.values()) & set(target_seeds)
            ),
            "source_episode_index": previous.SOURCE_EPISODE_INDEX,
            "priority_source_episode_index": previous.PRIORITY_SOURCE_EPISODE_INDEX,
            "target_episode_index": TARGET_EPISODE_INDEX,
        },
        "construction_contract": {
            "source_artifacts_frozen_before_fresh_targets": True,
            "target_arm_failures_are_typed_noncertificates": True,
            "target_arm_failures_are_retained_before_aggregation": True,
            "success_only_fields_read_only_for_successful_arms": True,
            "domain_actions_used_only_for_kernel_calls": True,
            "flat_raw_actions_used_for_generic_receipts_and_planning": True,
            "same_target_adapter_kernel_seed_episode_in_both_arms": True,
            "target_outcomes_used_to_refit_source_artifacts": False,
            "every_ground_query_requires_prior_certificate_failure": True,
            "query_local_exact_overlay_only_safety_authority": True,
            "strict_incompatible_schema_rejected_before_ground_query": True,
        },
        "registered_gate": {
            "required_relation": (
                "TWO_USABLE_SOURCES_AND_FOUR_FRESH_TARGETS_AND_ZERO_TYPED_ARM_FAILURES_"
                "AND_PRIORITY_USED_ON_ALL_TARGETS_AND_ALL_OOD_REJECTIONS_AND_CERTIFICATE_"
                "DISCIPLINE_CLEAN_AND_AGGREGATE_DERIVED_LABELS_LT_STRICT_AND_AT_LEAST_"
                "ONE_TARGET_REDUCED"
            ),
            "required_usable_source_count": previous.REQUIRED_USABLE_SOURCE_COUNT,
            "required_fresh_target_occurrence_count": previous.FRESH_TARGET_OCCURRENCE_COUNT,
            "minimum_reduced_target_occurrence_count": (
                previous.MINIMUM_REDUCED_TARGET_OCCURRENCE_COUNT
            ),
            "zero_typed_target_arm_failures_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "source_worker_count": previous.SOURCE_WORKER_COUNT,
            "target_worker_count": previous.TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": previous.TARGET_WORKER_COUNT,
            "maximum_target_ground_support_labels_per_arm_occurrence": (
                previous.MAXIMUM_TARGET_GROUND_SUPPORT_LABELS
            ),
        },
        "accounting_contract": {
            "offline_and_source_labels_separate": True,
            "priority_source_labels_separate": True,
            "target_common_partial_labels_separate": True,
            "target_certificate_local_labels_separate_by_arm": True,
            "execution_steps_separate": True,
            "planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v75r3_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "normalized_priority_cross_occurrence_reduction_verified": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_v75r3_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v75r3(
            domains.CONSTRUCTION_K7_FAIL_CLOSED_PRIORITY_PREREGISTRATION_V75R3_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FailClosedPriorityPreregistrationV75R3:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v75r3(
                domains.CONSTRUCTION_K7_FAIL_CLOSED_PRIORITY_PREREGISTRATION_V75R3_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V75r3 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: FailClosedPriorityPreregistrationV75R3 | None = None


def freeze_fail_closed_priority_preregistration_v75r3() -> FailClosedPriorityPreregistrationV75R3:
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
        _fail("frozen V75r3 preregistration changed")
    _CACHE = FailClosedPriorityPreregistrationV75R3(_ISSUER, raw, identity)
    return _CACHE


def verify_fail_closed_priority_preregistration_v75r3(
    value: Any,
) -> FailClosedPriorityPreregistrationV75R3:
    if type(value) is not FailClosedPriorityPreregistrationV75R3:
        _fail("V75r3 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_fail_closed_priority_preregistration_v75r3()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V75r3 preregistration differs from frozen output")
    return value


__all__ = (
    "FRESH_TARGET_SEEDS",
    "PREREGISTRATION_ID",
    "SOURCE_SEED_BY_FAMILY",
    "campaign_config_v75r3",
    "freeze_fail_closed_priority_preregistration_v75r3",
    "verify_fail_closed_priority_preregistration_v75r3",
)
