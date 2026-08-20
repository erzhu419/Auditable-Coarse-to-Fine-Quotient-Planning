"""Outcome-free preregistration for the V85 projected-disagreement source Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_contextual_ordinal_preregistration_v84 as previous
from acfqp import construction_k7_domain_registry_extension_v85 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.projected_disagreement_source_campaign_core_v85 import (
    build_projected_disagreement_source_campaign_document_v85,
)


IMPLEMENTATION_COMMIT = "808fb7b"
PREREGISTRATION_ID = "01bbe4a0924535e11fea1a04d0a9205e6f0bfbefa9216a88f8aa2d7b4a2d77fb"
EXPECTED_CANONICAL_BYTE_COUNT = 7_641
EXPECTED_CANONICAL_SHA256 = "007f0e3d57b8dc9c1b57107171cbe28671bfc75f1c8f16e818ca113844f1f261"
V84_FAILED_CAMPAIGN_ID = (
    "1828a9c92459da992f2e691b5a8f935005d4da5981070728f4c5d9a0a4e9db28"
)
SOURCE_FAMILY = "BALANCED_BATCH_REFINEMENT"
SOURCE_POOL_SEEDS = (869_101, 869_102, 869_103, 869_104, 869_105, 869_106)
SOURCE_EPISODE_INDEX = 0
SOURCE_WORKER_COUNT = 2
REQUIRED_SOURCE_MEMBER_COUNT = 6
MINIMUM_COMPILED_MODEL_COUNT = 1
MINIMUM_COMPILED_SOURCE_MEMBER_COUNT = 2
TEMPLATE_LIBRARY_ARTIFACT_ID = previous.TEMPLATE_LIBRARY_ARTIFACT_ID
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v85.py",
    "src/acfqp/generic_projected_disagreement_acquisition_v56.py",
    "src/acfqp/generic_projected_disagreement_model_compiler_v56.py",
    "src/acfqp/generic_projected_disagreement_planner_v56.py",
    "src/acfqp/generic_context_stratified_schedule_v55.py",
    "src/acfqp/generic_contextual_ordinal_residual_v54.py",
    "src/acfqp/generic_contextual_ordinal_frontier_acquisition_v54.py",
    "src/acfqp/generic_contextual_ordinal_model_compiler_v54.py",
    "src/acfqp/projected_disagreement_source_campaign_core_v85.py",
    "src/acfqp/contextual_ordinal_source_campaign_core_v84.py",
    "src/acfqp/generic_frontier_prequential_acquisition_v53.py",
    "src/acfqp/generic_structural_source_partition_v50.py",
    "src/acfqp/generic_canonical_source_pool_v48.py",
    "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
    "src/acfqp/generic_source_complete_relational_world_model_v31.py",
    "src/acfqp/construction_k7_contextual_ordinal_campaign_v84.py",
)


class ConstructionK7ProjectedDisagreementPreregistrationV85Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProjectedDisagreementPreregistrationV85Error(message)


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


def campaign_config_v85() -> dict[str, Any]:
    config = previous.campaign_config_v84()
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
        "schema": "acfqp.projected_disagreement_source_preregistration.v85",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v84_failed_campaign_id": V84_FAILED_CAMPAIGN_ID,
            "v84_preregistration_id": previous.PREREGISTRATION_ID,
            "v83_failed_campaign_id": previous.V83_FAILED_CAMPAIGN_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v85_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V85),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_projected_disagreement_source_campaign_document_v85
            ),
            "frozen_before_any_registered_v85_source_outcome": True,
        },
        "failure_driven_successor_contract": {
            "v84_context_schedule_failure_preserved": True,
            "v84_raw_transitions_used_only_for_offline_schedule_diagnosis": True,
            "projected_disagreement_schedule_is_generic_not_family_named": True,
            "fresh_v85_seeds_disjoint_from_v84": True,
            "blind_seed_substitution_or_posthoc_selection_used": False,
            "all_six_source_identities_fixed_before_outcomes": True,
            "query_selection_uses_only_pre_state_action_and_model_projections": True,
            "unacquired_post_state_or_label_access_for_query_selection": False,
            "all_terminal_and_residual_frontiers_checked_before_compilation": True,
            "confirmation_budget_derived_from_candidate_mdl_and_confidence": True,
            "source_only_gate_before_any_fresh_target": True,
        },
        "identity_contract": {
            "source_family": SOURCE_FAMILY,
            "source_pool_seeds": list(SOURCE_POOL_SEEDS),
            "source_seed_count": len(SOURCE_POOL_SEEDS),
            "source_seeds_unique": len(set(SOURCE_POOL_SEEDS)) == len(SOURCE_POOL_SEEDS),
            "source_seeds_disjoint_from_v84": min(SOURCE_POOL_SEEDS)
            > max(previous.SOURCE_POOL_SEEDS),
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
            "model_projected_candidate_disagreement_drives_query_order": True,
            "every_batch_exact_residual_proposal_jointly_compiled": True,
            "compiled_models_are_proposals_not_safety_authority": True,
        },
        "registered_gate": {
            "required_relation": (
                "SIX_FRESH_SOURCE_MEMBERS_AND_SOURCE_CERTIFICATE_DISCIPLINE_CLEAN_"
                "AND_EVERY_MEMBER_RETAINED_EXACTLY_ONCE_AND_AT_LEAST_ONE_"
                "MULTI_SOURCE_PROJECTED_DISAGREEMENT_MODEL_COMPILED_AND_EVERY_"
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
            "query_selection_projection_compute_separate": True,
            "planning_compute_separate": True,
            "target_axes_zero_in_source_only_slice": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v85_source_outcome_observed": False,
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
        "fresh_registered_v85_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v85(
            domains.CONSTRUCTION_K7_PROJECTED_DISAGREEMENT_PREREGISTRATION_V85_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ProjectedDisagreementPreregistrationV85:
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
            or domains.extension_content_id_v85(
                domains.CONSTRUCTION_K7_PROJECTED_DISAGREEMENT_PREREGISTRATION_V85_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V85 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ProjectedDisagreementPreregistrationV85 | None = None


def freeze_projected_disagreement_preregistration_v85(
) -> ProjectedDisagreementPreregistrationV85:
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
        _fail("frozen V85 preregistration changed")
    _CACHE = ProjectedDisagreementPreregistrationV85(_ISSUER, raw, identity)
    return _CACHE


def verify_projected_disagreement_preregistration_v85(
    value: Any,
) -> ProjectedDisagreementPreregistrationV85:
    if type(value) is not ProjectedDisagreementPreregistrationV85:
        _fail("V85 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_projected_disagreement_preregistration_v85()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V85 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "SOURCE_POOL_SEEDS",
    "campaign_config_v85",
    "freeze_projected_disagreement_preregistration_v85",
    "verify_projected_disagreement_preregistration_v85",
)
