"""Outcome-free preregistration for the fail-closed V77 successor."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v77 as domains
from acfqp import construction_k7_three_family_preregistration_v76 as previous
from acfqp.fail_closed_three_family_campaign_core_v77 import (
    build_fail_closed_three_family_campaign_document_v77,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "cf54208"
PREREGISTRATION_ID = "a99637a7fc854950b458be2ae7f9a81764ce45d3c478d2171730969e52301409"
EXPECTED_CANONICAL_BYTE_COUNT = 5_493
EXPECTED_CANONICAL_SHA256 = "946c7736d4f3049a4077152a73563497e2bfedb423f7ba77cdcf2f965dd2bfce"
V76_FAILURE_ID = "87d538791718b5cb95a1e97e944a3fe066d4061f4e8bfd10a7cf85aba97c4fa7"
V75R5_CAMPAIGN_ID = previous.V75R5_CAMPAIGN_ID
V75R5_VERIFICATION_ID = previous.V75R5_VERIFICATION_ID
TEMPLATE_LIBRARY_ARTIFACT_ID = previous.TEMPLATE_LIBRARY_ARTIFACT_ID
SOURCE_SEED_BY_FAMILY = {
    **previous.SOURCE_SEED_BY_FAMILY,
    "BALANCED_BATCH_REFINEMENT": 751_101,
}
FRESH_TARGET_SEEDS = {
    "BALANCED_BATCH_REFINEMENT": (768_101, 768_102),
    "COUPLED_EXCHANGE": (768_201, 768_202),
    "MAINTENANCE_CASCADE": (768_301, 768_302),
}
TARGET_EPISODE_INDEX = 8
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v77.py",
    "src/acfqp/fail_closed_three_family_campaign_core_v77.py",
    "src/acfqp/construction_k7_three_family_failure_v76.py",
    "src/acfqp/generic_abstract_agreement_query_filter_v47.py",
    "src/acfqp/generic_structural_rank_query_prior_v46.py",
    "src/acfqp/generic_flat_action_adapter_v45.py",
    "src/acfqp/three_family_cross_occurrence_campaign_core_v76.py",
)


class ConstructionK7ThreeFamilyPreregistrationV77Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ThreeFamilyPreregistrationV77Error(message)


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


def campaign_config_v77() -> dict[str, Any]:
    config = previous.campaign_config_v76()
    config.update(
        source_seed_by_family=dict(SOURCE_SEED_BY_FAMILY),
        fresh_target_seeds={key: tuple(value) for key, value in FRESH_TARGET_SEEDS.items()},
        target_episode_index=TARGET_EPISODE_INDEX,
    )
    return config


def _document() -> dict[str, Any]:
    targets = tuple(seed for values in FRESH_TARGET_SEEDS.values() for seed in values)
    payload = {
        "schema": "acfqp.three_family_preregistration.v77",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v76_failure_id": V76_FAILURE_ID,
            "v75r5_campaign_id": V75R5_CAMPAIGN_ID,
            "v75r5_verification_id": V75R5_VERIFICATION_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v77_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V77),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_fail_closed_three_family_campaign_document_v77
            ),
            "frozen_before_any_registered_v77_target_outcome": True,
        },
        "failure_driven_successor_contract": {
            "v76_source_abstention_failure_preserved": True,
            "balanced_source_seed_changed_to_fresh_predecessor_occurrence": True,
            "source_abstention_is_typed_and_never_dereferenced": True,
            "target_execution_only_for_usable_source_families": True,
            "all_six_target_identities_are_fresh": True,
        },
        "identity_contract": {
            "source_seed_by_family": dict(SOURCE_SEED_BY_FAMILY),
            "fresh_target_seeds": {
                key: list(value) for key, value in FRESH_TARGET_SEEDS.items()
            },
            "fresh_target_seed_count": len(set(targets)),
            "fresh_target_seeds_unique": len(targets) == len(set(targets)),
            "fresh_target_seeds_disjoint_from_predecessors": min(targets) > 768_000,
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
                "FAILURES_AND_FILTERED_MATCHES_MODEL_ONLY_AND_ALL_OOD_REJECTIONS_AND_"
                "CERTIFICATE_CLEAN_AND_FILTERED_LABELS_LE_STRICT_AND_ONE_REDUCED"
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
            "target_certificate_labels_separate_by_arm": True,
            "execution_steps_separate": True,
            "planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v77_target_outcome_observed": False,
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
        "fresh_registered_v77_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v77(
            domains.CONSTRUCTION_K7_THREE_FAMILY_PREREGISTRATION_V77_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ThreeFamilyPreregistrationV77:
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
            or domains.extension_content_id_v77(
                domains.CONSTRUCTION_K7_THREE_FAMILY_PREREGISTRATION_V77_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V77 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ThreeFamilyPreregistrationV77 | None = None


def freeze_three_family_preregistration_v77() -> ThreeFamilyPreregistrationV77:
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
        _fail("frozen V77 preregistration changed")
    _CACHE = ThreeFamilyPreregistrationV77(_ISSUER, raw, identity)
    return _CACHE


def verify_three_family_preregistration_v77(value: Any) -> ThreeFamilyPreregistrationV77:
    if type(value) is not ThreeFamilyPreregistrationV77:
        _fail("V77 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_three_family_preregistration_v77()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V77 preregistration differs from frozen output")
    return value


__all__ = (
    "FRESH_TARGET_SEEDS",
    "PREREGISTRATION_ID",
    "SOURCE_SEED_BY_FAMILY",
    "campaign_config_v77",
    "freeze_three_family_preregistration_v77",
    "verify_three_family_preregistration_v77",
)
