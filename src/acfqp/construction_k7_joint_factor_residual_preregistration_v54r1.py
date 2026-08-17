"""Fresh outcome-free successor to the frozen failed V54 predecessor."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp.construction_k7_joint_factor_residual_preregistration_v54 import (
    FUTURE_DOMAINS,
    TERMINAL_TOKENS,
    V51_CAMPAIGN_ID,
    V51_CAMPAIGN_SHA256,
    V51_EVIDENCE_COMMIT,
    V51_FACTOR_LIBRARY_ID,
    V51_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = "54r1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.225"
PROFILE_KEY = "construction_k7_joint_factor_residual_discovery_v54r1"
PREREGISTRATION_ID = "43065d8851a792f5bbcf8ccc9dbdf027843ce22e547c1dc6bf0cb18f4621647a"
EXPECTED_CANONICAL_BYTE_COUNT = 6_829
EXPECTED_CANONICAL_SHA256 = "91277b868b58cf4af0e5724e92a68701d89915e520f47657060f89095d10526d"
IMPLEMENTATION_COMMIT = "533da48"
V54_FAILURE_COMMIT = "b2e6635"
V54_PREREGISTRATION_ID = "e729ba8af747af549abc8454b6cd5b5466551ec25b76bbab854e17cf50815c01"
V54_FAILURE_ID = "f5dbecac001b91c3a460fe4f7d4559a45bef631640f881c29e6e484f95c8b785"
FACTOR_LIBRARY_LABELS = 370

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/generic_atomic_expression_world_model_v4.py",
    "src/acfqp/generic_layout_factorized_world_model_v5.py",
    "src/acfqp/generic_layout_factorized_world_model_v6.py",
    "src/acfqp/generic_cross_schema_factor_library_v7.py",
    "src/acfqp/generic_joint_factor_residual_world_model_v9.py",
    "src/acfqp/domains/stochastic_batch_refinement.py",
    "src/acfqp/domains/stochastic_balanced_batch_refinement.py",
    "src/acfqp/joint_factor_residual_campaign_core_v54r1.py",
    "src/acfqp/construction_k7_cross_schema_factor_campaign_v51.py",
    "src/acfqp/construction_k7_joint_factor_residual_failure_v54.py",
)

SOURCE_SEEDS = (542_101, 542_102, 542_103)
TARGET_SEEDS = tuple(range(542_201, 542_209))
DEVELOPMENT_SEEDS = tuple(range(559_101, 559_365))
SOURCE_STAGE_COUNT = 6
SOURCE_UNIT_BASE = 3
TARGET_STAGE_COUNT = 7
TARGET_UNIT_BASE = 4
MAXIMUM_SOURCE_LABELS_PER_OCCURRENCE = 128
MAXIMUM_TARGET_LAYOUT_LABELS = 128
MAXIMUM_RELATION_OUTPUT_CANDIDATE = 64
MINIMUM_REUSABLE_FACTOR_COUNT = 3


class ConstructionK7JointFactorResidualPreregistrationV54R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7JointFactorResidualPreregistrationV54R1Error(message)


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


def campaign_config_v54r1() -> dict[str, Any]:
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
        "maximum_relation_output_candidate": MAXIMUM_RELATION_OUTPUT_CANDIDATE,
        "minimum_reusable_factor_count": MINIMUM_REUSABLE_FACTOR_COUNT,
        "v51_factor_library_id": V51_FACTOR_LIBRARY_ID,
        "factor_library_labels": FACTOR_LIBRARY_LABELS,
        "v54_failure_id": V54_FAILURE_ID,
    }


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.joint_factor_residual_preregistration.v54r1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "implementation_commit": IMPLEMENTATION_COMMIT,
            "v54_failure_commit": V54_FAILURE_COMMIT,
            "v54_preregistration_id": V54_PREREGISTRATION_ID,
            "v54_registered_failure_id": V54_FAILURE_ID,
            "v54_same_identity_rerun_forbidden": True,
            "v51_evidence_commit": V51_EVIDENCE_COMMIT,
            "v51_campaign_id": V51_CAMPAIGN_ID,
            "v51_campaign_sha256": V51_CAMPAIGN_SHA256,
            "v51_verification_id": V51_VERIFICATION_ID,
            "v51_factor_library_id": V51_FACTOR_LIBRARY_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "domain_tags": dict(FUTURE_DOMAINS),
            "frozen_before_any_v54r1_registered_outcome": True,
            "development_seed_identities_disjoint_from_registered_identities": set(
                DEVELOPMENT_SEEDS
            ).isdisjoint(set(SOURCE_SEEDS) | set(TARGET_SEEDS)),
        },
        "repair_contract": {
            "failed_v54_cause": "NONUNIQUE_OR_UNSTABLE_HELD_OUT_LAYOUT_WITHIN_64_LABELS",
            "fresh_family_token": "OPAQUE_BALANCED_STOCHASTIC_BATCH_REFINEMENT",
            "opaque_state_width": 6,
            "opaque_action_field_width": 5,
            "balanced_goal_paths_remove_accidental_constant_column_symmetry": True,
            "witness_blind_full_frontier_layout_policy": True,
            "maximum_target_layout_labels": MAXIMUM_TARGET_LAYOUT_LABELS,
            "development_unique_layout_matches": 64,
            "development_maximum_layout_labels": 76,
            "registered_outcome_not_used_to_select_repair": True,
        },
        "joint_discovery_contract": {
            "only_prior_input": "ANONYMOUS_CROSS_SCHEMA_SIGNATURE_LIBRARY",
            "v51_target_program_consumed": False,
            "shared_residual_scaffold_consumed": False,
            "predeclared_reusable_factor_slots_consumed": False,
            "full_target_program_synthesized_from_raw_observations_first": True,
            "factorable_residual_classification_derived_from_dependencies": True,
            "minimum_reusable_factor_count": MINIMUM_REUSABLE_FACTOR_COUNT,
            "at_least_one_novel_factor_required": True,
            "at_least_one_schema_bound_residual_required": True,
        },
        "registered_inventory": {
            "source_seeds": list(SOURCE_SEEDS),
            "target_seeds": list(TARGET_SEEDS),
            "source_stage_count": SOURCE_STAGE_COUNT,
            "target_stage_count": TARGET_STAGE_COUNT,
            "independent_state_and_action_permutations": True,
            "generation_witness_available_to_constructor": False,
            "semantic_bridge_available_to_constructor": False,
        },
        "planning_recovery_and_ood": {
            "matched_receding_abstract_and_direct_plans_required": True,
            "local_ground_distinction_before_certificate_failure_forbidden": True,
            "strict_bitmask_ood_full_reconstruction_and_no_transfer_required": True,
            "ood_outcome_execution_forbidden": True,
        },
        "accounting_contract": {
            "historical_factor_library_labels": FACTOR_LIBRARY_LABELS,
            "source_target_local_execution_derivation_planning_and_certificate_axes_separate": True,
            "factor_prior_sample_savings_reestimated_in_v54r1": False,
        },
        "claim_boundary": {
            "fresh_successor_preregistered": True,
            "registered_outcome_observed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "future_content_domains": dict(FUTURE_DOMAINS),
        "fresh_v54r1_registered_outcome_execution_performed": False,
    }
    return {**payload, "preregistration_id": content_id(FUTURE_DOMAINS["preregistration"], payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class JointFactorResidualPreregistrationV54R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V54r1 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload) != self.preregistration_id
        ):
            _fail("V54r1 preregistration bytes or identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError
        return value


_CACHE: JointFactorResidualPreregistrationV54R1 | None = None


def freeze_joint_factor_residual_preregistration_v54r1() -> JointFactorResidualPreregistrationV54R1:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V54r1 preregistration changed")
    if _CACHE is None:
        _CACHE = JointFactorResidualPreregistrationV54R1(_ISSUER, raw, identity)
    return _CACHE


def verify_joint_factor_residual_preregistration_v54r1(value):
    if type(value) is not JointFactorResidualPreregistrationV54R1:
        _fail("V54r1 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_joint_factor_residual_preregistration_v54r1()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V54r1 preregistration does not match frozen bytes")
    return value


__all__ = (
    "FUTURE_DOMAINS",
    "JointFactorResidualPreregistrationV54R1",
    "campaign_config_v54r1",
    "freeze_joint_factor_residual_preregistration_v54r1",
    "verify_joint_factor_residual_preregistration_v54r1",
)
