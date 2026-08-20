"""Outcome-free preregistration for the V80 structurally routed source Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v80 as domains
from acfqp import construction_k7_successor_projected_preregistration_v79 as previous
from acfqp.construction_k7_successor_projected_campaign_v79 import (
    FROZEN_FAILURE_ID as V79_FAILURE_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.structurally_routed_source_campaign_core_v80 import (
    build_structurally_routed_source_campaign_document_v80,
)


IMPLEMENTATION_COMMIT = "237b2d1"
PREREGISTRATION_ID = "9ab8c65267b42ccdd6e50b7513cf201dbd14de4ecf5a77bc53f20dfc78f5668d"
EXPECTED_CANONICAL_BYTE_COUNT = 6_236
EXPECTED_CANONICAL_SHA256 = "d8604fb5070a13f4ca136b9d3e9d3a2a41bc44995b5cd50d9193cb7b9684f083"
V79_FROZEN_FAILURE_ID = V79_FAILURE_ID
SOURCE_FAMILY = "BALANCED_BATCH_REFINEMENT"
SOURCE_POOL_SEEDS = (809_101, 809_102)
SOURCE_EPISODE_INDEX = 0
SOURCE_WORKER_COUNT = 2
REQUIRED_SOURCE_MEMBER_COUNT = 2
TEMPLATE_LIBRARY_ARTIFACT_ID = previous.TEMPLATE_LIBRARY_ARTIFACT_ID
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v80.py",
    "src/acfqp/generic_structural_source_partition_v50.py",
    "src/acfqp/generic_canonical_source_pool_v48.py",
    "src/acfqp/generic_successor_projected_acquisition_v49.py",
    "src/acfqp/generic_successor_projected_model_compiler_v49.py",
    "src/acfqp/structurally_routed_source_campaign_core_v80.py",
    "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
    "src/acfqp/generic_relation_covering_schedule_v39.py",
    "src/acfqp/generic_prequential_role_free_acquisition_v37.py",
    "src/acfqp/generic_source_complete_relational_world_model_v31.py",
    "src/acfqp/construction_k7_successor_projected_campaign_v79.py",
)


class ConstructionK7StructuralRoutePreregistrationV80Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7StructuralRoutePreregistrationV80Error(message)


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


def campaign_config_v80() -> dict[str, Any]:
    config = previous.campaign_config_v79()
    config.update(
        source_family=SOURCE_FAMILY,
        source_pool_seeds=SOURCE_POOL_SEEDS,
        source_episode_index=SOURCE_EPISODE_INDEX,
        source_worker_count=SOURCE_WORKER_COUNT,
        required_source_member_count=REQUIRED_SOURCE_MEMBER_COUNT,
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.structurally_routed_source_preregistration.v80",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v79_failure_id": V79_FROZEN_FAILURE_ID,
            "v79_preregistration_id": previous.PREREGISTRATION_ID,
            "v78_failed_campaign_id": previous.V78_FAILED_CAMPAIGN_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v80_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V80),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_structurally_routed_source_campaign_document_v80
            ),
            "frozen_before_any_registered_v80_source_outcome": True,
        },
        "failure_driven_successor_contract": {
            "v79_structural_incompatibility_preserved": True,
            "blind_seed_substitution_used_as_fix": False,
            "anonymous_layout_signature_partition_added": True,
            "v48_pooling_only_inside_compatible_groups": True,
            "singleton_source_groups_retained_without_discard": True,
            "every_discovered_group_required_to_compile": True,
            "source_only_gate_before_any_fresh_target": True,
        },
        "identity_contract": {
            "source_family": SOURCE_FAMILY,
            "source_pool_seeds": list(SOURCE_POOL_SEEDS),
            "source_seed_count": len(SOURCE_POOL_SEEDS),
            "source_seeds_unique": len(set(SOURCE_POOL_SEEDS))
            == len(SOURCE_POOL_SEEDS),
            "source_seeds_disjoint_from_v79": min(SOURCE_POOL_SEEDS) > 809_000,
            "source_episode_index": SOURCE_EPISODE_INDEX,
            "fresh_target_identities_registered": [],
        },
        "construction_contract": {
            "partition_uses_only_discovered_layout_and_schema_signature": True,
            "family_name_used_by_partition_or_pooling": False,
            "terminal_or_target_outcome_used_by_partition": False,
            "all_source_members_retained_exactly_once": True,
            "incompatible_sources_forced_into_one_model": False,
            "v49_successor_projected_acquisition_per_group": True,
            "query_prestates_not_used_as_terminal_frontier_vote_inputs": True,
            "same_v42_joint_successor_model_format_and_verifier": True,
            "heldout_validation_required_before_each_model_compilation": True,
            "group_models_are_proposals_not_safety_authority": True,
        },
        "registered_gate": {
            "required_relation": (
                "TWO_FRESH_SOURCE_MEMBERS_AND_SOURCE_CERTIFICATE_DISCIPLINE_CLEAN_"
                "AND_EVERY_MEMBER_RETAINED_EXACTLY_ONCE_AND_EVERY_DISCOVERED_"
                "STRUCTURAL_GROUP_HELDOUT_VALIDATED_AND_MODEL_COMPILED_AND_ZERO_"
                "FRESH_TARGET_OUTCOMES"
            ),
            "required_source_member_count": REQUIRED_SOURCE_MEMBER_COUNT,
            "target_execution_forbidden_in_this_slice": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "source_worker_count": SOURCE_WORKER_COUNT,
            "maximum_simultaneous_worker_count": SOURCE_WORKER_COUNT,
            "maximum_terminal_program_candidates_to_try_per_group": 32,
            "maximum_successor_support_states_per_group": 4_096,
            "maximum_relational_support_branch_evaluations_per_plan": 1_000_000,
        },
        "accounting_contract": {
            "offline_labels_separate": True,
            "source_partial_labels_separate": True,
            "source_certificate_labels_separate": True,
            "group_query_counts_not_mislabeled_as_physical_samples": True,
            "execution_steps_separate": True,
            "derivation_and_planning_compute_separate": True,
            "target_axes_zero_in_source_only_slice": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v80_source_outcome_observed": False,
            "fresh_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "cross_group_model_composition_verified": False,
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
        "fresh_registered_v80_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v80(
            domains.CONSTRUCTION_K7_STRUCTURAL_ROUTE_PREREGISTRATION_V80_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class StructuralRoutePreregistrationV80:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value
            for key, value in document.items()
            if key != "preregistration_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v80(
                domains.CONSTRUCTION_K7_STRUCTURAL_ROUTE_PREREGISTRATION_V80_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V80 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: StructuralRoutePreregistrationV80 | None = None


def freeze_structural_route_preregistration_v80(
) -> StructuralRoutePreregistrationV80:
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
        _fail("frozen V80 preregistration changed")
    _CACHE = StructuralRoutePreregistrationV80(_ISSUER, raw, identity)
    return _CACHE


def verify_structural_route_preregistration_v80(
    value: Any,
) -> StructuralRoutePreregistrationV80:
    if type(value) is not StructuralRoutePreregistrationV80:
        _fail("V80 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_structural_route_preregistration_v80()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V80 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "SOURCE_FAMILY",
    "SOURCE_POOL_SEEDS",
    "campaign_config_v80",
    "freeze_structural_route_preregistration_v80",
    "verify_structural_route_preregistration_v80",
)
