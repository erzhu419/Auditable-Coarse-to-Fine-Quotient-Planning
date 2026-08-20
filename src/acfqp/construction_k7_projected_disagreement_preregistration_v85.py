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
WITHDRAWN_INCOMPLETE_SOURCE_CLOSURE_PREREGISTRATION_ID = (
    "01bbe4a0924535e11fea1a04d0a9205e6f0bfbefa9216a88f8aa2d7b4a2d77fb"
)
PREREGISTRATION_ID = "87ba0a081d8b007bcd267323269407febcd95ee3019c679f543022baf8c40138"
EXPECTED_CANONICAL_BYTE_COUNT = 8_083
EXPECTED_CANONICAL_SHA256 = "8cae7b6438ea7a78f5646593366f9db299c8076b6620089509ab8a90725c331d"
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
    "src/acfqp/construction_k7_projected_disagreement_campaign_v85.py",
    "src/acfqp/contextual_ordinal_source_campaign_core_v84.py",
    "src/acfqp/generic_frontier_prequential_acquisition_v53.py",
    "src/acfqp/generic_structural_source_partition_v50.py",
    "src/acfqp/generic_canonical_source_pool_v48.py",
    "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
    "src/acfqp/generic_source_complete_relational_world_model_v31.py",
    "src/acfqp/construction_k7_contextual_ordinal_campaign_v84.py",
)
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v85.py", 1543, "5d61d16e4d931ab79c34a03004b6a537257b7bb61d1a2bb88333e9d9cc76f051"),
    ("src/acfqp/generic_projected_disagreement_acquisition_v56.py", 21335, "641737c6f5b200ec86b1051f62c8e83e6f9014218fe294a213cad1b27c541c3b"),
    ("src/acfqp/generic_projected_disagreement_model_compiler_v56.py", 12065, "e92b87e65151bcaaf9aa7ab30a4421760f46f4cc15015e66d6d5e6931c8e2364"),
    ("src/acfqp/generic_projected_disagreement_planner_v56.py", 1893, "7029052eb45ead4666fd6d1536831711a2836ace9b8608a678dd170545fd20e3"),
    ("src/acfqp/generic_context_stratified_schedule_v55.py", 4498, "a95c93e2566672ba1470f5c7f26c0f3538e7868098b183ebddfd1e7aff588df1"),
    ("src/acfqp/generic_contextual_ordinal_residual_v54.py", 15495, "0f4f9b42cdfe991481cd17d1a0c7239d287d97fca4d57a9ae2d284f857e9b81d"),
    ("src/acfqp/generic_contextual_ordinal_frontier_acquisition_v54.py", 17154, "1153bd95c7f698aa1be4d0779723ac50e89719ad379eaf55d25f0359ae985dc5"),
    ("src/acfqp/generic_contextual_ordinal_model_compiler_v54.py", 16005, "446558176449420620f0a32cb1a4e763906b3b24df622cc63b5bfe54c4b1704a"),
    ("src/acfqp/projected_disagreement_source_campaign_core_v85.py", 14055, "11570b3f941900edd22fd53730778134ac5470c364f8016654084a110d54d290"),
    ("src/acfqp/construction_k7_projected_disagreement_campaign_v85.py", 4861, "e8f2102822673cf684f6591183a2ce003ad18b1deba0b3d69a7a16fefa74869b"),
    ("src/acfqp/contextual_ordinal_source_campaign_core_v84.py", 13852, "5adb462d5133dedd34a2153f8ec25fa33cc546f99eca2c40d0427d8d71d68975"),
    ("src/acfqp/generic_frontier_prequential_acquisition_v53.py", 15431, "eb3d63f1cda91a28f2ac91820d20001dc704b606b67736422a6f56c95011e094"),
    ("src/acfqp/generic_structural_source_partition_v50.py", 6913, "50bfd1d146ff509a862037079f8a1bfb646924826d81b40efc290f360dbf9c01"),
    ("src/acfqp/generic_canonical_source_pool_v48.py", 10924, "d066f256e5b0e9b8cf512999fc86d8b699752df452681310473eda2cb4d2a835"),
    ("src/acfqp/generic_joint_successor_version_space_planner_v42.py", 36033, "d4b99c0f96688fc4d4dc4fae01a1d6896d254f166881ad5611c1e755c8bc1005"),
    ("src/acfqp/generic_source_complete_relational_world_model_v31.py", 5009, "efb982d243604a038dd9a173f84a8ccf8e26a87f9183e9393f23465ba5177bf0"),
    ("src/acfqp/construction_k7_contextual_ordinal_campaign_v84.py", 4901, "5080efbe67726bdbe7c86909c71254267b6d02ba09a3ac7f6094972bd6487e3c"),
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
            "withdrawn_incomplete_source_closure_preregistration_id": (
                WITHDRAWN_INCOMPLETE_SOURCE_CLOSURE_PREREGISTRATION_ID
            ),
            "v84_failed_campaign_id": V84_FAILED_CAMPAIGN_ID,
            "v84_preregistration_id": previous.PREREGISTRATION_ID,
            "v83_failed_campaign_id": previous.V83_FAILED_CAMPAIGN_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v85_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V85),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_projected_disagreement_source_campaign_document_v85
            ),
            "frozen_before_any_registered_v85_source_outcome": True,
        },
        "failure_driven_successor_contract": {
            "earlier_outcome_free_v85_preregistration_with_unbound_producer_preserved": True,
            "no_outcome_executed_under_withdrawn_preregistration": True,
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
