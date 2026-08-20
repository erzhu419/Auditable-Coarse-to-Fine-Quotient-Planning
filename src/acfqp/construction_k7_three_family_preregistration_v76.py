"""Outcome-free preregistration for the V76 three-family campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v76 as domains
from acfqp import construction_k7_agreement_filtered_preregistration_v75r5 as previous
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.three_family_cross_occurrence_campaign_core_v76 import (
    build_three_family_cross_occurrence_campaign_document_v76,
)


IMPLEMENTATION_COMMIT = "f18149e"
PREREGISTRATION_ID = "30169836395c025b2c86223f7c0a0716677a1076a333c2a4f475ffcf9fffde2b"
EXPECTED_CANONICAL_BYTE_COUNT = 5_508
EXPECTED_CANONICAL_SHA256 = "958551cd1048d18bb399f1df3cdb6719e4a1bce573be327362d38537107e5872"
V75R5_CAMPAIGN_ID = "09f60884721e863b864b539ff95e9e82a5de60de2755995fbf49cd1905b1ed5a"
V75R5_VERIFICATION_ID = "510ce0d66d0f228cc9202dd86098fbf391c02aa60ac75882b39dca76044422e6"
TEMPLATE_LIBRARY_ARTIFACT_ID = previous.TEMPLATE_LIBRARY_ARTIFACT_ID
SOURCE_SEED_BY_FAMILY = {
    "BALANCED_BATCH_REFINEMENT": 751_102,
    "COUPLED_EXCHANGE": 752_102,
    "MAINTENANCE_CASCADE": 753_101,
}
FRESH_TARGET_SEEDS = {
    "BALANCED_BATCH_REFINEMENT": (767_101, 767_102),
    "COUPLED_EXCHANGE": (767_201, 767_202),
    "MAINTENANCE_CASCADE": (767_301, 767_302),
}
TARGET_EPISODE_INDEX = 7
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v76.py",
    "src/acfqp/three_family_cross_occurrence_campaign_core_v76.py",
    "src/acfqp/generic_abstract_agreement_query_filter_v47.py",
    "src/acfqp/generic_structural_rank_query_prior_v46.py",
    "src/acfqp/generic_flat_action_adapter_v45.py",
    "src/acfqp/generic_portable_certificate_query_priority_v44.py",
    "src/acfqp/agreement_filtered_priority_campaign_core_v75r5.py",
)


class ConstructionK7ThreeFamilyPreregistrationV76Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ThreeFamilyPreregistrationV76Error(message)


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


def campaign_config_v76() -> dict[str, Any]:
    config = previous.campaign_config_v75r5()
    config.update(
        source_seed_by_family=dict(SOURCE_SEED_BY_FAMILY),
        fresh_target_seeds={key: tuple(value) for key, value in FRESH_TARGET_SEEDS.items()},
        target_episode_index=TARGET_EPISODE_INDEX,
        source_worker_count=3,
        target_worker_count=6,
        fresh_target_occurrence_count=6,
        required_usable_source_count=3,
    )
    return config


def _document() -> dict[str, Any]:
    targets = tuple(seed for values in FRESH_TARGET_SEEDS.values() for seed in values)
    payload = {
        "schema": "acfqp.three_family_preregistration.v76",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v75r5_campaign_id": V75R5_CAMPAIGN_ID,
            "v75r5_verification_id": V75R5_VERIFICATION_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v76_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V76),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_three_family_cross_occurrence_campaign_document_v76
            ),
            "frozen_before_any_registered_v76_target_outcome": True,
        },
        "extension_contract": {
            "v75r5_two_family_evidence_preserved": True,
            "balanced_batch_refinement_added_as_third_family": True,
            "one_source_model_per_family": True,
            "two_fresh_target_seeds_per_family": True,
            "cross_family_model_transfer_claimed": False,
            "same_generic_synthesizer_planner_certificate_pipeline": True,
        },
        "identity_contract": {
            "source_seed_by_family": dict(SOURCE_SEED_BY_FAMILY),
            "fresh_target_seeds": {
                key: list(value) for key, value in FRESH_TARGET_SEEDS.items()
            },
            "fresh_target_seed_count": len(set(targets)),
            "fresh_target_seed_identities_unique": len(targets) == len(set(targets)),
            "fresh_target_seeds_disjoint_from_predecessors": min(targets) > 767_000,
            "source_and_target_seeds_disjoint": not (
                set(SOURCE_SEED_BY_FAMILY.values()) & set(targets)
            ),
            "source_episode_index": 0,
            "priority_source_episode_index": 1,
            "target_episode_index": TARGET_EPISODE_INDEX,
        },
        "construction_contract": {
            "three_matched_target_arms": True,
            "same_target_partial_acquisition_adapter_kernel_seed_episode": True,
            "same_v44_engine_filtered_vs_model_only": True,
            "target_transition_outcomes_used_to_filter_priority": False,
            "target_outcomes_used_to_refit_source_artifacts": False,
            "every_ground_query_requires_prior_certificate_failure": True,
            "query_local_exact_overlay_only_safety_authority": True,
            "strict_incompatible_schema_rejected_before_ground_query": True,
        },
        "registered_gate": {
            "required_relation": (
                "THREE_USABLE_SOURCE_FAMILIES_AND_SIX_FRESH_TARGETS_AND_ZERO_ARM_"
                "FAILURES_AND_FILTERED_MATCHES_MODEL_ONLY_PER_TARGET_AND_ALL_OOD_"
                "REJECTIONS_AND_CERTIFICATE_CLEAN_AND_FILTERED_AGGREGATE_LABELS_LE_"
                "STRICT_AND_AT_LEAST_ONE_TARGET_REDUCED"
            ),
            "required_source_family_count": 3,
            "required_fresh_target_occurrence_count": 6,
            "minimum_reduced_target_occurrence_count": 1,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "source_worker_count": 3,
            "target_worker_count": 6,
            "maximum_simultaneous_worker_count": 6,
            "maximum_target_ground_support_labels_per_arm_occurrence": 100_000,
        },
        "accounting_contract": {
            "offline_labels_separate": True,
            "source_labels_separate": True,
            "target_common_partial_labels_separate": True,
            "target_certificate_labels_separate_by_arm_and_family": True,
            "execution_steps_separate": True,
            "planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v76_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "three_family_cross_occurrence_noninferiority_verified": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "cross_family_model_transfer_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_v76_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v76(
            domains.CONSTRUCTION_K7_THREE_FAMILY_PREREGISTRATION_V76_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ThreeFamilyPreregistrationV76:
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
            or domains.extension_content_id_v76(
                domains.CONSTRUCTION_K7_THREE_FAMILY_PREREGISTRATION_V76_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V76 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ThreeFamilyPreregistrationV76 | None = None


def freeze_three_family_preregistration_v76() -> ThreeFamilyPreregistrationV76:
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
        _fail("frozen V76 preregistration changed")
    _CACHE = ThreeFamilyPreregistrationV76(_ISSUER, raw, identity)
    return _CACHE


def verify_three_family_preregistration_v76(value: Any) -> ThreeFamilyPreregistrationV76:
    if type(value) is not ThreeFamilyPreregistrationV76:
        _fail("V76 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_three_family_preregistration_v76()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V76 preregistration differs from frozen output")
    return value


__all__ = (
    "FRESH_TARGET_SEEDS",
    "PREREGISTRATION_ID",
    "SOURCE_SEED_BY_FAMILY",
    "campaign_config_v76",
    "freeze_three_family_preregistration_v76",
    "verify_three_family_preregistration_v76",
)
