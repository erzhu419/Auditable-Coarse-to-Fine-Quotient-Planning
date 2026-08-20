"""Outcome-free preregistration for the V75r5 agreement filter."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v75r5 as domains
from acfqp import construction_k7_structural_rank_preregistration_v75r4 as previous
from acfqp.agreement_filtered_priority_campaign_core_v75r5 import (
    build_agreement_filtered_priority_campaign_document_v75r5,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "8594a23"
AGREEMENT_FILTER_COMMIT = "33be36d"
PREREGISTRATION_ID = "e3cd3b61db376a9e3a3addd0767300c6dda350a98d2853142992c6ba33e47a92"
EXPECTED_CANONICAL_BYTE_COUNT = 5_838
EXPECTED_CANONICAL_SHA256 = "dbbae68fbc3cdb12308ee453ae317669e94106b5d72034ba4581b33704bff663"
V75R4_CAMPAIGN_ID = "cc3ad3f14573acecea2a6001f0f7f706a3fbb585385f7aa873c5bdb0b3dfcb96"
PRESERVED_PREDECESSOR_IDS = (
    previous.V75_FAILURE_ID,
    previous.V75R1_FAILURE_ID,
    previous.V75R2_FAILURE_ID,
    previous.V75R3_CAMPAIGN_ID,
    V75R4_CAMPAIGN_ID,
)
TEMPLATE_LIBRARY_ARTIFACT_ID = previous.TEMPLATE_LIBRARY_ARTIFACT_ID
SOURCE_SEED_BY_FAMILY = dict(previous.SOURCE_SEED_BY_FAMILY)
FRESH_TARGET_SEEDS = {
    "COUPLED_EXCHANGE": (766_201, 766_202),
    "MAINTENANCE_CASCADE": (766_301, 766_302),
}
TARGET_EPISODE_INDEX = 6
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v75r5.py",
    "src/acfqp/agreement_filtered_priority_campaign_core_v75r5.py",
    "src/acfqp/generic_abstract_agreement_query_filter_v47.py",
    "src/acfqp/generic_structural_rank_query_prior_v46.py",
    "src/acfqp/generic_flat_action_adapter_v45.py",
    "src/acfqp/generic_portable_certificate_query_priority_v44.py",
    "src/acfqp/structural_rank_transfer_campaign_core_v75r4.py",
)


class ConstructionK7AgreementFilteredPreregistrationV75R5Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AgreementFilteredPreregistrationV75R5Error(message)


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


def campaign_config_v75r5() -> dict[str, Any]:
    config = previous.campaign_config_v75r4()
    config.update(
        fresh_target_seeds={key: tuple(value) for key, value in FRESH_TARGET_SEEDS.items()},
        target_episode_index=TARGET_EPISODE_INDEX,
    )
    return config


def _document() -> dict[str, Any]:
    target_seeds = tuple(seed for values in FRESH_TARGET_SEEDS.values() for seed in values)
    payload = {
        "schema": "acfqp.agreement_filtered_preregistration.v75r5",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "preserved_predecessor_ids": list(PRESERVED_PREDECESSOR_IDS),
            "agreement_filter_commit": AGREEMENT_FILTER_COMMIT,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v75r5_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75R5),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_agreement_filtered_priority_campaign_document_v75r5
            ),
            "frozen_before_any_registered_v75r5_target_outcome": True,
        },
        "failure_driven_successor_contract": {
            "v75r4_portable_but_harmful_priority_gate_preserved": True,
            "unfiltered_priority_arm_retained": True,
            "agreement_filtered_priority_arm_added": True,
            "model_only_arm_uses_same_v44_engine_with_inert_priority": True,
            "strict_no_model_or_priority_arm_retained": True,
            "filter_uses_only_target_initial_observation_and_abstract_plan": True,
            "target_transition_outcomes_used_to_filter_priority": False,
        },
        "identity_contract": {
            "source_seed_by_family": dict(SOURCE_SEED_BY_FAMILY),
            "fresh_target_seeds": {
                key: list(value) for key, value in FRESH_TARGET_SEEDS.items()
            },
            "fresh_target_seed_count": len(set(target_seeds)),
            "fresh_target_seed_identities_unique": len(target_seeds) == len(set(target_seeds)),
            "fresh_target_seeds_disjoint_from_predecessors": min(target_seeds) > 766_000,
            "source_and_target_seeds_disjoint": not (
                set(SOURCE_SEED_BY_FAMILY.values()) & set(target_seeds)
            ),
            "source_episode_index": 0,
            "priority_source_episode_index": 1,
            "target_episode_index": TARGET_EPISODE_INDEX,
        },
        "construction_contract": {
            "four_matched_target_arms": True,
            "same_target_partial_acquisition_adapter_kernel_seed_episode": True,
            "same_v44_engine_and_stopping_rule_filtered_vs_model_only": True,
            "agreement_filter_enable_iff_source_and_abstract_actions_equal": True,
            "target_outcomes_used_to_refit_source_or_filter": False,
            "every_ground_query_requires_prior_certificate_failure": True,
            "query_local_exact_overlay_only_safety_authority": True,
            "strict_incompatible_schema_rejected_before_ground_query": True,
        },
        "registered_gate": {
            "required_relation": (
                "ZERO_ARM_FAILURES_AND_ALL_OOD_REJECTIONS_AND_CERTIFICATE_CLEAN_AND_"
                "FILTERED_EXACTLY_MATCHES_MODEL_ONLY_PER_TARGET_AND_FILTERED_NOT_WORSE_"
                "THAN_UNFILTERED_AND_FILTERED_AGGREGATE_LABELS_LT_STRICT_AND_AT_LEAST_"
                "ONE_TARGET_REDUCED"
            ),
            "required_source_count": 2,
            "required_fresh_target_occurrence_count": 4,
            "minimum_reduced_target_occurrence_count": 1,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "source_worker_count": 2,
            "target_worker_count": 4,
            "maximum_simultaneous_worker_count": 4,
            "maximum_target_ground_support_labels_per_arm_occurrence": 100_000,
        },
        "accounting_contract": {
            "offline_labels_separate": True,
            "source_labels_separate": True,
            "target_common_partial_labels_separate": True,
            "target_certificate_labels_separate_by_four_arms": True,
            "execution_steps_separate": True,
            "planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v75r5_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "heuristic_operator_sample_tax_control_verified": False,
            "cross_occurrence_model_sample_reduction_verified": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_v75r5_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v75r5(
            domains.CONSTRUCTION_K7_AGREEMENT_FILTERED_PREREGISTRATION_V75R5_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AgreementFilteredPreregistrationV75R5:
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
            or domains.extension_content_id_v75r5(
                domains.CONSTRUCTION_K7_AGREEMENT_FILTERED_PREREGISTRATION_V75R5_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V75r5 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: AgreementFilteredPreregistrationV75R5 | None = None


def freeze_agreement_filtered_preregistration_v75r5() -> AgreementFilteredPreregistrationV75R5:
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
        _fail("frozen V75r5 preregistration changed")
    _CACHE = AgreementFilteredPreregistrationV75R5(_ISSUER, raw, identity)
    return _CACHE


def verify_agreement_filtered_preregistration_v75r5(
    value: Any,
) -> AgreementFilteredPreregistrationV75R5:
    if type(value) is not AgreementFilteredPreregistrationV75R5:
        _fail("V75r5 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_agreement_filtered_preregistration_v75r5()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V75r5 preregistration differs from frozen output")
    return value


__all__ = (
    "FRESH_TARGET_SEEDS",
    "PRESERVED_PREDECESSOR_IDS",
    "PREREGISTRATION_ID",
    "campaign_config_v75r5",
    "freeze_agreement_filtered_preregistration_v75r5",
    "verify_agreement_filtered_preregistration_v75r5",
)
