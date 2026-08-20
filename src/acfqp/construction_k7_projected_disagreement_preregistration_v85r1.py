"""Outcome-free preregistration for the self-contained V85r1 source Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v85r1 as domains
from acfqp import construction_k7_projected_disagreement_preregistration_v85 as previous
from acfqp.construction_k7_v84_template_library_v85r1 import LIBRARY_ARTIFACT_ID
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.projected_disagreement_source_campaign_core_v85r1 import (
    build_projected_disagreement_source_campaign_document_v85r1,
)


IMPLEMENTATION_COMMIT = "129527f"
PREREGISTRATION_ID = "f93a236934e32cb03bc8e6303410dd4e420525de70d48b9a4075d1e917c12b86"
EXPECTED_CANONICAL_BYTE_COUNT = 6_133
EXPECTED_CANONICAL_SHA256 = "271b66b4dd8076d06299c86d47024910d0ce805336d03abc9d49707404a33066"
V84_FAILED_CAMPAIGN_ID = previous.V84_FAILED_CAMPAIGN_ID
V85_PRE_OUTCOME_FAILURE_ID = (
    "82f3212d9e755c769795d1a908bbb1aac33b18de8f6cbe5a407256cac3e60acb"
)
TEMPLATE_LIBRARY_ARTIFACT_ID = LIBRARY_ARTIFACT_ID
SOURCE_FAMILY = "BALANCED_BATCH_REFINEMENT"
SOURCE_POOL_SEEDS = (879_101, 879_102, 879_103, 879_104, 879_105, 879_106)
SOURCE_WORKER_COUNT = 2
REQUIRED_SOURCE_MEMBER_COUNT = 6
MINIMUM_COMPILED_MODEL_COUNT = 1
MINIMUM_COMPILED_SOURCE_MEMBER_COUNT = 2
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "artifacts/world_model/v85r1_v84_balanced_template_library.json",
    "src/acfqp/construction_k7_domain_registry_extension_v85r1.py",
    "src/acfqp/construction_k7_v84_template_library_v85r1.py",
    "src/acfqp/projected_disagreement_source_campaign_core_v85r1.py",
    "src/acfqp/construction_k7_projected_disagreement_campaign_v85r1.py",
    "src/acfqp/projected_disagreement_source_campaign_core_v85.py",
    "src/acfqp/generic_projected_disagreement_acquisition_v56.py",
    "src/acfqp/generic_projected_disagreement_model_compiler_v56.py",
    "src/acfqp/generic_projected_disagreement_planner_v56.py",
    "src/acfqp/generic_context_stratified_schedule_v55.py",
    "src/acfqp/generic_contextual_ordinal_residual_v54.py",
    "src/acfqp/generic_structural_source_partition_v50.py",
)
FROZEN_SOURCE_FACTS = (
    ("artifacts/world_model/v85r1_v84_balanced_template_library.json", 49262, "433e4fe332da6629532e6b84a46e9cfafee2c2378de414cc2c6af3d881133706"),
    ("src/acfqp/construction_k7_domain_registry_extension_v85r1.py", 1584, "df15f1e7255f81384cba882f10b9b13250fba90c2c5a61ab2f62cd4667de8c78"),
    ("src/acfqp/construction_k7_v84_template_library_v85r1.py", 3024, "efd6fd0653731ab959d64d140bb56c184311c0b566231cfd3510593527e11625"),
    ("src/acfqp/projected_disagreement_source_campaign_core_v85r1.py", 2469, "36e7c8ff7df5b91f9458446f398ea71a4f7c66479910a97db3fb834b957168ee"),
    ("src/acfqp/construction_k7_projected_disagreement_campaign_v85r1.py", 4790, "e64a7679bdcfc3ab985aa9a6f67b31b8bca2be84bc2239d163f6d573c3f2004a"),
    ("src/acfqp/projected_disagreement_source_campaign_core_v85.py", 14055, "11570b3f941900edd22fd53730778134ac5470c364f8016654084a110d54d290"),
    ("src/acfqp/generic_projected_disagreement_acquisition_v56.py", 21335, "641737c6f5b200ec86b1051f62c8e83e6f9014218fe294a213cad1b27c541c3b"),
    ("src/acfqp/generic_projected_disagreement_model_compiler_v56.py", 12065, "e92b87e65151bcaaf9aa7ab30a4421760f46f4cc15015e66d6d5e6931c8e2364"),
    ("src/acfqp/generic_projected_disagreement_planner_v56.py", 1893, "7029052eb45ead4666fd6d1536831711a2836ace9b8608a678dd170545fd20e3"),
    ("src/acfqp/generic_context_stratified_schedule_v55.py", 4498, "a95c93e2566672ba1470f5c7f26c0f3538e7868098b183ebddfd1e7aff588df1"),
    ("src/acfqp/generic_contextual_ordinal_residual_v54.py", 15495, "0f4f9b42cdfe991481cd17d1a0c7239d287d97fca4d57a9ae2d284f857e9b81d"),
    ("src/acfqp/generic_structural_source_partition_v50.py", 6913, "50bfd1d146ff509a862037079f8a1bfb646924826d81b40efc290f360dbf9c01"),
)


class ConstructionK7ProjectedDisagreementPreregistrationV85R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProjectedDisagreementPreregistrationV85R1Error(message)


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


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def _callable_fact(value: Any) -> dict[str, Any]:
    return {
        "module": value.__module__,
        "qualname": value.__qualname__,
        "code_sha256": hashlib.sha256(marshal.dumps(value.__code__)).hexdigest(),
    }


def campaign_config_v85r1() -> dict[str, Any]:
    config = previous.campaign_config_v85()
    config.update(
        source_pool_seeds=SOURCE_POOL_SEEDS,
        source_worker_count=SOURCE_WORKER_COUNT,
        required_source_member_count=REQUIRED_SOURCE_MEMBER_COUNT,
        minimum_compiled_model_count=MINIMUM_COMPILED_MODEL_COUNT,
        minimum_compiled_source_member_count=MINIMUM_COMPILED_SOURCE_MEMBER_COUNT,
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.projected_disagreement_source_preregistration.v85r1",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v84_failed_campaign_id": V84_FAILED_CAMPAIGN_ID,
            "v85_preregistration_id": previous.PREREGISTRATION_ID,
            "v85_pre_outcome_failure_id": V85_PRE_OUTCOME_FAILURE_ID,
            "self_contained_template_library_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v85r1_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V85R1),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_projected_disagreement_source_campaign_document_v85r1
            ),
            "frozen_before_any_registered_v85r1_source_outcome": True,
        },
        "failure_driven_successor_contract": {
            "v85_pre_outcome_failure_preserved": True,
            "v85_fresh_seed_outcome_count_was_zero": True,
            "historical_v70_producer_dereference_forbidden": True,
            "self_contained_template_bytes_bound_before_outcomes": True,
            "fresh_v85r1_seeds_disjoint_from_v85": True,
            "blind_seed_substitution_or_posthoc_selection_used": False,
            "query_selection_uses_only_pre_state_action_and_model_projections": True,
            "unacquired_post_state_or_label_access_for_query_selection": False,
            "source_only_gate_before_any_fresh_target": True,
        },
        "identity_contract": {
            "source_family": SOURCE_FAMILY,
            "source_pool_seeds": list(SOURCE_POOL_SEEDS),
            "source_seed_count": len(SOURCE_POOL_SEEDS),
            "source_seeds_unique": len(set(SOURCE_POOL_SEEDS)) == len(SOURCE_POOL_SEEDS),
            "source_seeds_disjoint_from_v85": min(SOURCE_POOL_SEEDS)
            > max(previous.SOURCE_POOL_SEEDS),
            "fresh_target_identities_registered": [],
        },
        "registered_gate": {
            "required_relation": (
                "SIX_FRESH_SOURCE_MEMBERS_AND_SOURCE_CERTIFICATE_DISCIPLINE_CLEAN_"
                "AND_EVERY_MEMBER_RETAINED_EXACTLY_ONCE_AND_AT_LEAST_ONE_"
                "PROJECTED_DISAGREEMENT_MODEL_COMPILED_OVER_AT_LEAST_TWO_MEMBERS_"
                "AND_ZERO_TARGET_OUTCOMES"
            ),
            "required_source_member_count": REQUIRED_SOURCE_MEMBER_COUNT,
            "minimum_compiled_model_count": MINIMUM_COMPILED_MODEL_COUNT,
            "minimum_compiled_source_member_count": MINIMUM_COMPILED_SOURCE_MEMBER_COUNT,
            "target_execution_forbidden_in_this_slice": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "source_worker_count": SOURCE_WORKER_COUNT,
            "maximum_simultaneous_worker_count": SOURCE_WORKER_COUNT,
            "source_member_count": REQUIRED_SOURCE_MEMBER_COUNT,
            "maximum_terminal_program_candidates_to_try_per_group": 32,
        },
        "accounting_contract": {
            "offline_template_labels_separate": True,
            "offline_residual_labels_separate": True,
            "source_partial_labels_separate": True,
            "source_certificate_labels_separate": True,
            "group_query_counts_not_mislabeled_as_physical_samples": True,
            "execution_steps_separate": True,
            "derivation_query_selection_and_planning_compute_separate": True,
            "target_axes_zero_in_source_only_slice": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v85r1_source_outcome_observed": False,
            "fresh_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "robust_target_plan_verified": False,
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
        "fresh_registered_v85r1_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v85r1(
            domains.CONSTRUCTION_K7_PROJECTED_DISAGREEMENT_PREREGISTRATION_V85R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ProjectedDisagreementPreregistrationV85R1:
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
            or domains.extension_content_id_v85r1(
                domains.CONSTRUCTION_K7_PROJECTED_DISAGREEMENT_PREREGISTRATION_V85R1_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V85r1 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ProjectedDisagreementPreregistrationV85R1 | None = None


def freeze_projected_disagreement_preregistration_v85r1(
) -> ProjectedDisagreementPreregistrationV85R1:
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
        _fail("frozen V85r1 preregistration changed")
    _CACHE = ProjectedDisagreementPreregistrationV85R1(_ISSUER, raw, identity)
    return _CACHE


def verify_projected_disagreement_preregistration_v85r1(
    value: Any,
) -> ProjectedDisagreementPreregistrationV85R1:
    if type(value) is not ProjectedDisagreementPreregistrationV85R1:
        _fail("V85r1 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_projected_disagreement_preregistration_v85r1()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V85r1 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "SOURCE_POOL_SEEDS",
    "campaign_config_v85r1",
    "freeze_projected_disagreement_preregistration_v85r1",
    "verify_projected_disagreement_preregistration_v85r1",
)
