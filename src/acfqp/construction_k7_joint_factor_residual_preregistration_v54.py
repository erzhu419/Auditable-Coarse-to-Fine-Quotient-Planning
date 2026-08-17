"""Outcome-free V54 registration for joint factor/residual discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_CAMPAIGN_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_EPISODE_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_FAILED_CERTIFICATE_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LOCAL_DISTINCTION_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_OOD_REJECTION_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PREREGISTRATION_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_RAW_OBSERVATION_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_VERIFICATION_V54_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "54.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.224"
PROFILE_KEY = "construction_k7_joint_factor_residual_discovery_v54"
PREREGISTRATION_ID = "e729ba8af747af549abc8454b6cd5b5466551ec25b76bbab854e17cf50815c01"
EXPECTED_CANONICAL_BYTE_COUNT = 6_145
EXPECTED_CANONICAL_SHA256 = "440a8d002599f3ae09c6b1ba5e20d32b04097f81a0d926b64860cd316c78b903"

IMPLEMENTATION_COMMITS = ("a0fdf89", "787139a")
V51_EVIDENCE_COMMIT = "154815d"
V51_CAMPAIGN_ID = "44a63b782201b3e53a32de1bc071d66fb06526903f96a037d2c55c8f3068e144"
V51_CAMPAIGN_SHA256 = "124bb3d89ee55b7f942161934c8f7c80236826b5b715473a7c81fa626bc52433"
V51_VERIFICATION_ID = "8d0e1044fe8db610375f35cd0956387b1ce6dca21d786cc62ae9bf1c69c66b3f"
V51_FACTOR_LIBRARY_ID = "46aa60cc33ca61238612342ed9fe73e91cfa7bfb639b4a8f0afa29c491428162"
FACTOR_LIBRARY_LABELS = 370

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/phase3e_ids.py",
    "src/acfqp/generic_atomic_expression_world_model_v4.py",
    "src/acfqp/generic_layout_factorized_world_model_v5.py",
    "src/acfqp/generic_layout_factorized_world_model_v6.py",
    "src/acfqp/generic_cross_schema_factor_library_v7.py",
    "src/acfqp/generic_joint_factor_residual_world_model_v9.py",
    "src/acfqp/domains/stochastic_batch_refinement.py",
    "src/acfqp/joint_factor_residual_campaign_core_v54.py",
    "src/acfqp/construction_k7_cross_schema_factor_campaign_v51.py",
)

TERMINAL_TOKENS = {"A": 9_001, "F": 9_007, "S": 9_011}
SOURCE_STAGE_COUNT = 6
SOURCE_UNIT_BASE = 3
SOURCE_SEEDS = (541_101, 541_102, 541_103)
TARGET_STAGE_COUNT = 7
TARGET_UNIT_BASE = 4
TARGET_SEEDS = tuple(range(541_201, 541_209))
DEVELOPMENT_SEEDS = (
    549_101,
    549_102,
    549_103,
    549_201,
    549_202,
    549_203,
    549_204,
)
MAXIMUM_SOURCE_LABELS_PER_OCCURRENCE = 128
MAXIMUM_TARGET_LAYOUT_LABELS = 64
LAYOUT_CONFIRMATION_COUNT = 2
MAXIMUM_RELATION_OUTPUT_CANDIDATE = 64
MINIMUM_REUSABLE_FACTOR_COUNT = 3

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PREREGISTRATION_V54_DOMAIN,
    "observation": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_RAW_OBSERVATION_V54_DOMAIN,
    "layout": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    "program": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    "support": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
    "joint_model": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
    "failed_certificate": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_FAILED_CERTIFICATE_V54_DOMAIN,
    "distinction": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LOCAL_DISTINCTION_V54_DOMAIN,
    "episode": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_EPISODE_V54_DOMAIN,
    "ood": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_OOD_REJECTION_V54_DOMAIN,
    "campaign": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_CAMPAIGN_V54_DOMAIN,
    "verification": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_VERIFICATION_V54_DOMAIN,
}


class ConstructionK7JointFactorResidualPreregistrationV54Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7JointFactorResidualPreregistrationV54Error(message)


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


def campaign_config_v54() -> dict[str, Any]:
    return {
        "domains": dict(FUTURE_DOMAINS),
        "terminal_tokens": dict(TERMINAL_TOKENS),
        "source_stage_count": SOURCE_STAGE_COUNT,
        "source_unit_base": SOURCE_UNIT_BASE,
        "source_seeds": SOURCE_SEEDS,
        "maximum_source_labels_per_occurrence": MAXIMUM_SOURCE_LABELS_PER_OCCURRENCE,
        "target_stage_count": TARGET_STAGE_COUNT,
        "target_unit_base": TARGET_UNIT_BASE,
        "target_seeds": TARGET_SEEDS,
        "maximum_target_layout_labels": MAXIMUM_TARGET_LAYOUT_LABELS,
        "layout_confirmation_count": LAYOUT_CONFIRMATION_COUNT,
        "maximum_relation_output_candidate": MAXIMUM_RELATION_OUTPUT_CANDIDATE,
        "minimum_reusable_factor_count": MINIMUM_REUSABLE_FACTOR_COUNT,
        "v51_factor_library_id": V51_FACTOR_LIBRARY_ID,
        "factor_library_labels": FACTOR_LIBRARY_LABELS,
    }


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.joint_factor_residual_preregistration.v54",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "implementation_commits": list(IMPLEMENTATION_COMMITS),
            "v51_evidence_commit": V51_EVIDENCE_COMMIT,
            "v51_campaign_id": V51_CAMPAIGN_ID,
            "v51_campaign_sha256": V51_CAMPAIGN_SHA256,
            "v51_verification_id": V51_VERIFICATION_ID,
            "v51_factor_library_id": V51_FACTOR_LIBRARY_ID,
            "v51_target_program_available_to_v54": False,
            "v51_reused_factor_slot_inventory_available_to_v54": False,
            "all_predecessor_identities_preserved": True,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "frozen_before_any_v54_registered_outcome": True,
            "development_seed_identities_disjoint_from_registered_identities": set(
                DEVELOPMENT_SEEDS
            ).isdisjoint(set(SOURCE_SEEDS) | set(TARGET_SEEDS)),
        },
        "joint_discovery_contract": {
            "constructor_inputs": [
                "RAW_STATE_ACTION_SUCCESSOR_OBSERVATIONS",
                "ANONYMOUS_ACTION_CATALOGUES",
                "ANONYMOUS_CROSS_SCHEMA_SIGNATURE_LIBRARY",
            ],
            "forbidden_constructor_inputs": [
                "V51_TARGET_PROGRAM",
                "V51_SHARED_RESIDUAL_SCAFFOLD",
                "V51_REUSED_FACTOR_SUBPROGRAM_SLOTS",
                "CALLER_SELECTED_TARGET_COLUMNS",
            ],
            "full_target_program_synthesized_before_signature_matching": True,
            "all_output_assignments_compete_in_same_atomic_expression_grammar": True,
            "factorable_residual_classification_derived_from_compiled_dependencies": True,
            "reusable_classification_requires_exact_anonymous_signature_match": True,
        },
        "fresh_target": {
            "family_token": "OPAQUE_STOCHASTIC_BATCH_REFINEMENT",
            "source_seeds": list(SOURCE_SEEDS),
            "target_seeds": list(TARGET_SEEDS),
            "source_stage_count": SOURCE_STAGE_COUNT,
            "target_stage_count": TARGET_STAGE_COUNT,
            "independent_state_and_action_permutations": True,
            "generation_witness_available_to_constructor": False,
            "semantic_bridge_available_to_constructor": False,
            "minimum_reusable_factor_count": MINIMUM_REUSABLE_FACTOR_COUNT,
            "at_least_one_schema_bound_residual_required": True,
        },
        "planning_and_recovery": {
            "receding_abstract_planning_required": True,
            "matched_direct_ground_plan_required": True,
            "local_ground_query_before_certificate_failure_forbidden": True,
            "at_least_one_failed_certificate_and_local_distinction_required": True,
            "maximum_relation_output_candidate": MAXIMUM_RELATION_OUTPUT_CANDIDATE,
        },
        "strict_ood": {
            "family_token": "OPAQUE_BITMASK_ACCUMULATOR",
            "same_full_synthesizer_required": True,
            "complete_program_reconstruction_required": True,
            "minimum_signature_threshold_not_met_required": True,
            "prior_transfer_forbidden": True,
            "outcome_execution_forbidden": True,
        },
        "accounting_contract": {
            "historical_factor_library_labels": FACTOR_LIBRARY_LABELS,
            "source_labels_target_labels_execution_steps_derivation_planning_and_certificate_compute_separate": True,
            "v54_factor_prior_sample_savings_reestimation_required": False,
        },
        "required_positive_conditions": [
            "FULL_TARGET_PROGRAM_SYNTHESIZED_FROM_FRESH_RAW_TRANSITIONS",
            "FACTORABLE_AND_RESIDUAL_ASSIGNMENTS_JOINTLY_DISCOVERED",
            "NO_TARGET_SCAFFOLD_OR_FACTOR_SLOT_LIST_CONSUMED",
            "HELD_OUT_ABSTRACT_AND_DIRECT_PLANS_MATCH_AND_SUCCEED",
            "EVERY_LOCAL_GROUND_DISTINCTION_FOLLOWS_CERTIFICATE_FAILURE",
            "INCOMPATIBLE_OOD_PROGRAM_IS_RECONSTRUCTED_AND_TRANSFER_IS_REJECTED",
            "PRODUCER_FREE_RECONSTRUCTION_MATCHES_FROZEN_EVIDENCE",
        ],
        "claim_boundary": {
            "joint_discovery_preregistered": True,
            "registered_outcome_observed": False,
            "factor_prior_sample_savings_reestimated": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "future_content_domains": dict(FUTURE_DOMAINS),
        "fresh_v54_registered_outcome_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": content_id(FUTURE_DOMAINS["preregistration"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class JointFactorResidualPreregistrationV54:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V54 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V54 preregistration canonical bytes changed")
        payload = {
            key: value for key, value in document.items() if key != "preregistration_id"
        }
        if (
            document.get("preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V54 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: JointFactorResidualPreregistrationV54 | None = None


def freeze_joint_factor_residual_preregistration_v54() -> JointFactorResidualPreregistrationV54:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V54 preregistration changed")
    if _CACHE is None:
        _CACHE = JointFactorResidualPreregistrationV54(_ISSUER, raw, identity)
    return _CACHE


def verify_joint_factor_residual_preregistration_v54(
    value: JointFactorResidualPreregistrationV54,
) -> JointFactorResidualPreregistrationV54:
    if type(value) is not JointFactorResidualPreregistrationV54:
        _fail("V54 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_joint_factor_residual_preregistration_v54()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V54 preregistration does not match frozen bytes")
    return value


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "JointFactorResidualPreregistrationV54",
    "PREREGISTRATION_ID",
    "campaign_config_v54",
    "freeze_joint_factor_residual_preregistration_v54",
    "verify_joint_factor_residual_preregistration_v54",
)
