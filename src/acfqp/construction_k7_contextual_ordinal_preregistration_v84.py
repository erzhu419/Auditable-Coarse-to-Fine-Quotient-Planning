"""Outcome-free preregistration for the V84 contextual-ordinal source Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_all_frontier_preregistration_v83 as previous
from acfqp import construction_k7_domain_registry_extension_v84 as domains
from acfqp.contextual_ordinal_source_campaign_core_v84 import (
    build_contextual_ordinal_source_campaign_document_v84,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "659306b"
PREREGISTRATION_ID = "f5e94a31203d5c607d44e9edb94e4224cecd34d7e48e62b868c950379b5ebec0"
EXPECTED_CANONICAL_BYTE_COUNT = 7_189
EXPECTED_CANONICAL_SHA256 = "020b1bee419731906369c7b8996d2a62271a0155b586a360ef55d35df6713cfb"
V83_FAILED_CAMPAIGN_ID = (
    "9befdfcfd6b5a6673cd9e6a9f88837865f9c535febbc8cf57eadbbaae18e7bb4"
)
SOURCE_FAMILY = "BALANCED_BATCH_REFINEMENT"
SOURCE_POOL_SEEDS = (859_101, 859_102, 859_103, 859_104, 859_105, 859_106)
SOURCE_EPISODE_INDEX = 0
SOURCE_WORKER_COUNT = 2
REQUIRED_SOURCE_MEMBER_COUNT = 6
MINIMUM_COMPILED_MODEL_COUNT = 1
MINIMUM_COMPILED_SOURCE_MEMBER_COUNT = 2
TEMPLATE_LIBRARY_ARTIFACT_ID = previous.TEMPLATE_LIBRARY_ARTIFACT_ID
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v84.py",
    "src/acfqp/generic_contextual_ordinal_residual_v54.py",
    "src/acfqp/generic_contextual_ordinal_frontier_acquisition_v54.py",
    "src/acfqp/generic_contextual_ordinal_model_compiler_v54.py",
    "src/acfqp/generic_contextual_ordinal_planner_v54.py",
    "src/acfqp/contextual_ordinal_source_campaign_core_v84.py",
    "src/acfqp/generic_frontier_prequential_acquisition_v53.py",
    "src/acfqp/generic_structural_source_partition_v50.py",
    "src/acfqp/generic_canonical_source_pool_v48.py",
    "src/acfqp/all_frontier_multi_source_campaign_core_v83.py",
    "src/acfqp/bounded_multi_source_campaign_core_v82.py",
    "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
    "src/acfqp/generic_source_complete_relational_world_model_v31.py",
    "src/acfqp/construction_k7_all_frontier_campaign_v83.py",
)


class ConstructionK7ContextualOrdinalPreregistrationV84Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ContextualOrdinalPreregistrationV84Error(message)


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


def campaign_config_v84() -> dict[str, Any]:
    config = previous.campaign_config_v83()
    config.update(
        source_family=SOURCE_FAMILY,
        source_pool_seeds=SOURCE_POOL_SEEDS,
        source_episode_index=SOURCE_EPISODE_INDEX,
        source_worker_count=SOURCE_WORKER_COUNT,
        required_source_member_count=REQUIRED_SOURCE_MEMBER_COUNT,
        minimum_compiled_model_count=MINIMUM_COMPILED_MODEL_COUNT,
        minimum_compiled_source_member_count=MINIMUM_COMPILED_SOURCE_MEMBER_COUNT,
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.contextual_ordinal_source_preregistration.v84",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v83_failed_campaign_id": V83_FAILED_CAMPAIGN_ID,
            "v83_preregistration_id": previous.PREREGISTRATION_ID,
            "v82_failure_id": previous.V82_FROZEN_FAILURE_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v84_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V84),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_contextual_ordinal_source_campaign_document_v84
            ),
            "frozen_before_any_registered_v84_source_outcome": True,
        },
        "failure_driven_successor_contract": {
            "v83_zero_residual_frontier_failure_preserved": True,
            "v83_raw_transitions_used_only_for_offline_grammar_diagnosis": True,
            "contextual_ordinal_operator_is_generic_not_family_named": True,
            "fresh_v84_seeds_disjoint_from_v83": True,
            "blind_seed_substitution_or_posthoc_selection_used": False,
            "all_six_source_identities_fixed_before_outcomes": True,
            "all_terminal_and_residual_frontier_candidates_checked_prequentially": True,
            "all_terminal_and_residual_frontier_candidates_checked_on_heldout": True,
            "confirmation_budget_derived_from_candidate_mdl_and_confidence": True,
            "source_only_gate_before_any_fresh_target": True,
        },
        "identity_contract": {
            "source_family": SOURCE_FAMILY,
            "source_pool_seeds": list(SOURCE_POOL_SEEDS),
            "source_seed_count": len(SOURCE_POOL_SEEDS),
            "source_seeds_unique": len(set(SOURCE_POOL_SEEDS)) == len(SOURCE_POOL_SEEDS),
            "source_seeds_disjoint_from_v83": min(SOURCE_POOL_SEEDS) > max(previous.SOURCE_POOL_SEEDS),
            "source_episode_index": SOURCE_EPISODE_INDEX,
            "fresh_target_identities_registered": [],
        },
        "construction_contract": {
            "anonymous_layout_signature_partition_retained": True,
            "family_or_outcome_used_for_partition": False,
            "all_six_source_members_retained_exactly_once": True,
            "context_action_supports_derived_from_catalogues_not_outcomes": True,
            "context_local_action_field_ordinal_operator_registered": True,
            "raw_integer_token_identity_transferred_between_occurrences": False,
            "terminal_and_residual_frontiers_prequentially_frozen": True,
            "residual_successor_consensus_used_before_issuance": False,
            "every_batch_exact_residual_proposal_jointly_compiled": True,
            "compiled_models_are_proposals_not_safety_authority": True,
        },
        "registered_gate": {
            "required_relation": (
                "SIX_FRESH_SOURCE_MEMBERS_AND_SOURCE_CERTIFICATE_DISCIPLINE_CLEAN_"
                "AND_EVERY_MEMBER_RETAINED_EXACTLY_ONCE_AND_AT_LEAST_ONE_"
                "MULTI_SOURCE_CONTEXTUAL_ORDINAL_MODEL_COMPILED_AND_EVERY_"
                "ELIGIBLE_GROUP_COMPILED_WITH_ALL_FRONTIERS_AND_ZERO_TARGETS"
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
            "maximum_relational_support_branch_evaluations_per_plan": 1_000_000,
        },
        "accounting_contract": {
            "offline_labels_separate": True,
            "source_partial_labels_separate": True,
            "source_certificate_labels_separate": True,
            "group_query_counts_not_mislabeled_as_physical_samples": True,
            "execution_steps_separate": True,
            "terminal_derivation_compute_separate": True,
            "contextual_version_space_compute_separate": True,
            "planning_compute_separate": True,
            "target_axes_zero_in_source_only_slice": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v84_source_outcome_observed": False,
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
        "fresh_registered_v84_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v84(
            domains.CONSTRUCTION_K7_CONTEXTUAL_ORDINAL_PREREGISTRATION_V84_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ContextualOrdinalPreregistrationV84:
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
            or domains.extension_content_id_v84(
                domains.CONSTRUCTION_K7_CONTEXTUAL_ORDINAL_PREREGISTRATION_V84_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V84 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ContextualOrdinalPreregistrationV84 | None = None


def freeze_contextual_ordinal_preregistration_v84() -> ContextualOrdinalPreregistrationV84:
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
        _fail("frozen V84 preregistration changed")
    _CACHE = ContextualOrdinalPreregistrationV84(_ISSUER, raw, identity)
    return _CACHE


def verify_contextual_ordinal_preregistration_v84(
    value: Any,
) -> ContextualOrdinalPreregistrationV84:
    if type(value) is not ContextualOrdinalPreregistrationV84:
        _fail("V84 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_contextual_ordinal_preregistration_v84()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V84 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "SOURCE_POOL_SEEDS",
    "campaign_config_v84",
    "freeze_contextual_ordinal_preregistration_v84",
    "verify_contextual_ordinal_preregistration_v84",
)
