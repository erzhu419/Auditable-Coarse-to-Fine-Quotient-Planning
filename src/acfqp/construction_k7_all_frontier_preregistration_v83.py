"""Outcome-free preregistration for the V83 all-frontier source Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_bounded_source_preregistration_v82 as previous
from acfqp import construction_k7_domain_registry_extension_v83 as domains
from acfqp.all_frontier_multi_source_campaign_core_v83 import (
    build_all_frontier_multi_source_campaign_document_v83,
)
from acfqp.construction_k7_bounded_source_campaign_v82 import (
    FROZEN_FAILURE_ID as V82_FAILURE_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "ddfed6a"
PREREGISTRATION_ID = "c8b2ec9a0256743fc31674fb90f78baffaea875e9aab86a966467d650b3d79fe"
EXPECTED_CANONICAL_BYTE_COUNT = 7_097
EXPECTED_CANONICAL_SHA256 = "04595ab44a4b5b8cca1c604a567120830c2cf6fe357abb16610870daa86879a2"
V82_FROZEN_FAILURE_ID = V82_FAILURE_ID
SOURCE_FAMILY = "BALANCED_BATCH_REFINEMENT"
SOURCE_POOL_SEEDS = (849_101, 849_102, 849_103, 849_104, 849_105, 849_106)
SOURCE_EPISODE_INDEX = 0
SOURCE_WORKER_COUNT = 2
REQUIRED_SOURCE_MEMBER_COUNT = 6
TEMPLATE_LIBRARY_ARTIFACT_ID = previous.TEMPLATE_LIBRARY_ARTIFACT_ID
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v83.py",
    "src/acfqp/generic_frontier_prequential_acquisition_v53.py",
    "src/acfqp/generic_frontier_prequential_model_compiler_v53.py",
    "src/acfqp/generic_compiler_ready_acquisition_v52.py",
    "src/acfqp/generic_compiler_ready_model_compiler_v52.py",
    "src/acfqp/generic_version_space_retaining_model_compiler_v51.py",
    "src/acfqp/generic_structural_source_partition_v50.py",
    "src/acfqp/generic_canonical_source_pool_v48.py",
    "src/acfqp/all_frontier_multi_source_campaign_core_v83.py",
    "src/acfqp/bounded_multi_source_campaign_core_v82.py",
    "src/acfqp/retained_version_space_source_campaign_core_v81.py",
    "src/acfqp/structurally_routed_source_campaign_core_v80.py",
    "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
    "src/acfqp/generic_source_complete_relational_world_model_v31.py",
    "src/acfqp/construction_k7_bounded_source_campaign_v82.py",
)


class ConstructionK7AllFrontierPreregistrationV83Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AllFrontierPreregistrationV83Error(message)


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


def campaign_config_v83() -> dict[str, Any]:
    config = previous.campaign_config_v82()
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
        "schema": "acfqp.all_frontier_multi_source_preregistration.v83",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v82_failure_id": V82_FROZEN_FAILURE_ID,
            "v82_preregistration_id": previous.PREREGISTRATION_ID,
            "v81_failed_campaign_id": previous.V81_FAILED_CAMPAIGN_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v83_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V83),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_all_frontier_multi_source_campaign_document_v83
            ),
            "frozen_before_any_registered_v83_source_outcome": True,
        },
        "failure_driven_successor_contract": {
            "v82_terminal_frontier_compilation_failure_preserved": True,
            "blind_seed_substitution_or_posthoc_selection_used": False,
            "six_source_identities_fixed_before_all_outcomes": True,
            "every_fixed_source_executed_and_retained": True,
            "every_terminal_frontier_candidate_checked_prequentially": True,
            "every_terminal_frontier_candidate_checked_on_heldout": True,
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
            "source_seeds_disjoint_from_v82": min(SOURCE_POOL_SEEDS) > 849_000,
            "source_episode_index": SOURCE_EPISODE_INDEX,
            "fresh_target_identities_registered": [],
        },
        "construction_contract": {
            "anonymous_layout_signature_partition_retained": True,
            "family_or_outcome_used_for_partition": False,
            "all_six_source_members_retained_exactly_once": True,
            "v53_all_frontier_prequential_acquisition_per_group": True,
            "all_retained_terminal_trees_checked_before_model_compilation": True,
            "residual_successor_consensus_used_before_issuance": False,
            "nonempty_residual_version_space_used_as_readiness_gate": True,
            "every_batch_exact_residual_proposal_jointly_compiled": True,
            "compiled_models_are_proposals_not_safety_authority": True,
        },
        "registered_gate": {
            "required_relation": (
                "SIX_FRESH_SOURCE_MEMBERS_AND_SOURCE_CERTIFICATE_DISCIPLINE_CLEAN_"
                "AND_EVERY_MEMBER_RETAINED_EXACTLY_ONCE_AND_EVERY_STRUCTURAL_"
                "GROUP_ALL_FRONTIER_PREQUENTIAL_AND_HELDOUT_EXACT_AND_COMPILER_"
                "READY_AND_MODEL_COMPILED_WITH_ALL_RESIDUALS_AND_ZERO_TARGETS"
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
            "registered_v83_source_outcome_observed": False,
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
        "fresh_registered_v83_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v83(
            domains.CONSTRUCTION_K7_ALL_FRONTIER_PREREGISTRATION_V83_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AllFrontierPreregistrationV83:
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
            or domains.extension_content_id_v83(
                domains.CONSTRUCTION_K7_ALL_FRONTIER_PREREGISTRATION_V83_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V83 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: AllFrontierPreregistrationV83 | None = None


def freeze_all_frontier_preregistration_v83() -> AllFrontierPreregistrationV83:
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
        _fail("frozen V83 preregistration changed")
    _CACHE = AllFrontierPreregistrationV83(_ISSUER, raw, identity)
    return _CACHE


def verify_all_frontier_preregistration_v83(
    value: Any,
) -> AllFrontierPreregistrationV83:
    if type(value) is not AllFrontierPreregistrationV83:
        _fail("V83 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_all_frontier_preregistration_v83()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V83 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "SOURCE_POOL_SEEDS",
    "campaign_config_v83",
    "freeze_all_frontier_preregistration_v83",
    "verify_all_frontier_preregistration_v83",
)
