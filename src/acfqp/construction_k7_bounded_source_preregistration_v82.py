"""Outcome-free preregistration for the V82 bounded multi-source Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v82 as domains
from acfqp import construction_k7_retained_space_preregistration_v81 as previous
from acfqp.construction_k7_retained_space_campaign_v81 import (
    CAMPAIGN_ID as V81_CAMPAIGN_ID,
)
from acfqp.bounded_multi_source_campaign_core_v82 import (
    build_bounded_multi_source_campaign_document_v82,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "ad70b6e"
PREREGISTRATION_ID = "8998c7f33a9025afc77dc4e1cb681f7cd0b5f7d7fee8519538362376678d87be"
EXPECTED_CANONICAL_BYTE_COUNT = 6_904
EXPECTED_CANONICAL_SHA256 = "ea8572664ae2ff9a0a0d15b3586ab4fc4e5c6cfa965ee904f973b18efb9a3e21"
V81_FAILED_CAMPAIGN_ID = V81_CAMPAIGN_ID
SOURCE_FAMILY = "BALANCED_BATCH_REFINEMENT"
SOURCE_POOL_SEEDS = (839_101, 839_102, 839_103, 839_104, 839_105, 839_106)
SOURCE_EPISODE_INDEX = 0
SOURCE_WORKER_COUNT = 2
REQUIRED_SOURCE_MEMBER_COUNT = 6
TEMPLATE_LIBRARY_ARTIFACT_ID = previous.TEMPLATE_LIBRARY_ARTIFACT_ID
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v82.py",
    "src/acfqp/generic_compiler_ready_acquisition_v52.py",
    "src/acfqp/generic_compiler_ready_model_compiler_v52.py",
    "src/acfqp/generic_version_space_retaining_model_compiler_v51.py",
    "src/acfqp/generic_structural_source_partition_v50.py",
    "src/acfqp/generic_canonical_source_pool_v48.py",
    "src/acfqp/bounded_multi_source_campaign_core_v82.py",
    "src/acfqp/retained_version_space_source_campaign_core_v81.py",
    "src/acfqp/structurally_routed_source_campaign_core_v80.py",
    "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
    "src/acfqp/generic_relation_covering_schedule_v39.py",
    "src/acfqp/generic_prequential_role_free_acquisition_v37.py",
    "src/acfqp/generic_source_complete_relational_world_model_v31.py",
    "src/acfqp/construction_k7_retained_space_campaign_v81.py",
)


class ConstructionK7BoundedSourcePreregistrationV82Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7BoundedSourcePreregistrationV82Error(message)


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


def campaign_config_v82() -> dict[str, Any]:
    config = previous.campaign_config_v81()
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
        "schema": "acfqp.bounded_multi_source_preregistration.v82",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v81_failed_campaign_id": V81_FAILED_CAMPAIGN_ID,
            "v81_preregistration_id": previous.PREREGISTRATION_ID,
            "v80_failed_campaign_id": previous.V80_FAILED_CAMPAIGN_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v82_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V82),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_bounded_multi_source_campaign_document_v82
            ),
            "frozen_before_any_registered_v82_source_outcome": True,
        },
        "failure_driven_successor_contract": {
            "v81_acquisition_success_but_compiler_not_ready_preserved": True,
            "v81_second_singleton_semantic_coverage_abstention_preserved": True,
            "blind_seed_substitution_or_posthoc_selection_used": False,
            "six_source_identities_fixed_before_all_outcomes": True,
            "every_fixed_source_executed_and_retained": True,
            "structural_groups_formed_only_after_all_source_outcomes": True,
            "nonempty_residual_version_space_required_before_stop": True,
            "residual_successor_consensus_still_not_required": True,
            "source_only_gate_before_any_fresh_target": True,
        },
        "identity_contract": {
            "source_family": SOURCE_FAMILY,
            "source_pool_seeds": list(SOURCE_POOL_SEEDS),
            "source_seed_count": len(SOURCE_POOL_SEEDS),
            "source_seeds_unique": len(set(SOURCE_POOL_SEEDS))
            == len(SOURCE_POOL_SEEDS),
            "source_seeds_disjoint_from_v81": min(SOURCE_POOL_SEEDS) > 839_000,
            "source_episode_index": SOURCE_EPISODE_INDEX,
            "fresh_target_identities_registered": [],
        },
        "construction_contract": {
            "anonymous_layout_signature_partition_retained": True,
            "family_or_outcome_used_for_partition": False,
            "all_six_source_members_retained_exactly_once": True,
            "v52_compiler_ready_acquisition_per_group": True,
            "residual_successor_consensus_used_before_issuance": False,
            "nonempty_residual_version_space_used_as_readiness_gate": True,
            "observed_successor_mdl_prequential_and_heldout_guards_required": True,
            "every_batch_exact_residual_proposal_jointly_compiled": True,
            "compiled_models_are_proposals_not_safety_authority": True,
        },
        "registered_gate": {
            "required_relation": (
                "SIX_FRESH_SOURCE_MEMBERS_AND_SOURCE_CERTIFICATE_DISCIPLINE_CLEAN_"
                "AND_EVERY_MEMBER_RETAINED_EXACTLY_ONCE_AND_EVERY_DISCOVERED_"
                "STRUCTURAL_GROUP_COMPILER_READY_HELDOUT_VALIDATED_AND_MODEL_"
                "COMPILED_WITH_ALL_BATCH_EXACT_RESIDUALS_AND_ZERO_TARGET_OUTCOMES"
            ),
            "required_source_member_count": REQUIRED_SOURCE_MEMBER_COUNT,
            "target_execution_forbidden_in_this_slice": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "source_worker_count": SOURCE_WORKER_COUNT,
            "maximum_simultaneous_worker_count": SOURCE_WORKER_COUNT,
            "source_member_count": REQUIRED_SOURCE_MEMBER_COUNT,
            "maximum_terminal_program_candidates_to_try_per_group": 32,
            "maximum_relational_support_branch_evaluations_per_plan": 1_000_000,
        },
        "accounting_contract": {
            "offline_labels_separate": True,
            "source_partial_labels_separate": True,
            "source_certificate_labels_separate": True,
            "group_query_counts_not_mislabeled_as_physical_samples": True,
            "execution_steps_separate": True,
            "terminal_readiness_and_version_space_derivation_compute_separate": True,
            "planning_compute_separate": True,
            "target_axes_zero_in_source_only_slice": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v82_source_outcome_observed": False,
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
        "fresh_registered_v82_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v82(
            domains.CONSTRUCTION_K7_BOUNDED_SOURCE_PREREGISTRATION_V82_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class BoundedSourcePreregistrationV82:
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
            or domains.extension_content_id_v82(
                domains.CONSTRUCTION_K7_BOUNDED_SOURCE_PREREGISTRATION_V82_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V82 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: BoundedSourcePreregistrationV82 | None = None


def freeze_bounded_source_preregistration_v82() -> BoundedSourcePreregistrationV82:
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
        _fail("frozen V82 preregistration changed")
    _CACHE = BoundedSourcePreregistrationV82(_ISSUER, raw, identity)
    return _CACHE


def verify_bounded_source_preregistration_v82(
    value: Any,
) -> BoundedSourcePreregistrationV82:
    if type(value) is not BoundedSourcePreregistrationV82:
        _fail("V82 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_bounded_source_preregistration_v82()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V82 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "SOURCE_POOL_SEEDS",
    "campaign_config_v82",
    "freeze_bounded_source_preregistration_v82",
    "verify_bounded_source_preregistration_v82",
)
