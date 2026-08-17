"""Outcome-free registration for V51 cross-schema factor composition."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    ATOMIC_COMPOSITION_BEAM_WIDTH_V4,
    ATOMIC_COMPOSITION_MAX_DEPTH_V4,
    generic_atomic_opcode_documents_v4,
)
from acfqp.generic_cross_schema_factor_library_v7 import TRANSFERABLE_OPCODES_V7
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_BOUNDARY_V51_DOMAIN,
    CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_CAMPAIGN_V51_DOMAIN,
    CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_EPISODE_V51_DOMAIN,
    CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_FAILED_CERTIFICATE_V51_DOMAIN,
    CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_LIBRARY_V51_DOMAIN,
    CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_LOCAL_DISTINCTION_V51_DOMAIN,
    CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_OOD_REJECTION_V51_DOMAIN,
    CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_PREREGISTRATION_V51_DOMAIN,
    CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_PROGRAM_V51_DOMAIN,
    CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_RAW_OBSERVATION_V51_DOMAIN,
    CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_SAMPLE_TAX_V51_DOMAIN,
    CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_SUPPORT_V51_DOMAIN,
    CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_VERIFICATION_V51_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "51.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.221"
PROFILE_KEY = "construction_k7_cross_schema_factor_composition_v51"
PREREGISTRATION_ID = "1ee1ef5535993826557e35736e4e7c55b5b0e24050f330180409db3502eee8ed"
EXPECTED_CANONICAL_BYTE_COUNT = 6_879
EXPECTED_CANONICAL_SHA256 = "f225c2a3fa2ac138994ad676d6c20216a549cc08eea3f5f60f387baf6ef1a1f4"

IMPLEMENTATION_COMMIT = "37e77d7"
V50R1_EVIDENCE_COMMIT = "18a3d8e"
V50R1_CAMPAIGN_ID = (
    "24460ce540a835aba601cdba6865ae74f65c95e6eb8f060c00bddd9b0d4f7622"
)
V50R1_CAMPAIGN_SHA256 = (
    "f962a4a0e2feac85841e12153f3538108d3a165c8e6c482c9e44a7ac4ab176f1"
)
V50R1_VERIFICATION_ID = (
    "5998e44d2d1de657b9efee97e717d9301e0af046bac26967a68c8e38f4c2eedb"
)

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/generic_atomic_expression_world_model_v4.py",
    "src/acfqp/generic_layout_factorized_world_model_v5.py",
    "src/acfqp/generic_layout_factorized_world_model_v6.py",
    "src/acfqp/generic_cross_schema_factor_library_v7.py",
    "src/acfqp/domains/stochastic_coupled_exchange.py",
    "src/acfqp/cross_schema_factor_campaign_core_v51.py",
    "src/acfqp/construction_k7_layout_factorization_campaign_v50r1.py",
)

TERMINAL_TOKENS = {"A": 9_001, "F": 9_007, "S": 9_011}
SOURCE_STAGE_COUNT = 6
SOURCE_PRIMARY_BASE = 2
SOURCE_SEEDS = (511_101, 511_102, 511_103)
TARGET_STAGE_COUNT = 7
TARGET_PRIMARY_BASE = 5
TARGET_SEEDS = tuple(range(511_301, 511_309))
MAXIMUM_SOURCE_LABELS_PER_OCCURRENCE = 512
MAXIMUM_TARGET_LAYOUT_LABELS = 32
MAXIMUM_RELATION_OUTPUT_CANDIDATE = 32
MINIMUM_REUSED_FACTOR_COUNT = 3

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_PREREGISTRATION_V51_DOMAIN,
    "observation": CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_RAW_OBSERVATION_V51_DOMAIN,
    "factor_boundary": CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_BOUNDARY_V51_DOMAIN,
    "factor_library": CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_LIBRARY_V51_DOMAIN,
    "program": CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_PROGRAM_V51_DOMAIN,
    "support": CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_SUPPORT_V51_DOMAIN,
    "failed_certificate": CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_FAILED_CERTIFICATE_V51_DOMAIN,
    "distinction": CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_LOCAL_DISTINCTION_V51_DOMAIN,
    "episode": CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_EPISODE_V51_DOMAIN,
    "sample_tax": CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_SAMPLE_TAX_V51_DOMAIN,
    "ood": CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_OOD_REJECTION_V51_DOMAIN,
    "campaign": CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_CAMPAIGN_V51_DOMAIN,
    "verification": CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_VERIFICATION_V51_DOMAIN,
}


class ConstructionK7CrossSchemaFactorPreregistrationV51Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CrossSchemaFactorPreregistrationV51Error(message)


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


def campaign_config_v51() -> dict[str, Any]:
    return {
        "domains": dict(FUTURE_DOMAINS),
        "terminal_tokens": dict(TERMINAL_TOKENS),
        "source_stage_count": SOURCE_STAGE_COUNT,
        "source_primary_base": SOURCE_PRIMARY_BASE,
        "source_seeds": SOURCE_SEEDS,
        "target_stage_count": TARGET_STAGE_COUNT,
        "target_primary_base": TARGET_PRIMARY_BASE,
        "target_seeds": TARGET_SEEDS,
        "maximum_source_labels_per_occurrence": MAXIMUM_SOURCE_LABELS_PER_OCCURRENCE,
        "maximum_target_layout_labels": MAXIMUM_TARGET_LAYOUT_LABELS,
        "maximum_relation_output_candidate": MAXIMUM_RELATION_OUTPUT_CANDIDATE,
        "minimum_reused_factor_count": MINIMUM_REUSED_FACTOR_COUNT,
    }


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.cross_schema_factor_preregistration.v51",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessor": {
            "implementation_commit": IMPLEMENTATION_COMMIT,
            "v50r1_evidence_commit": V50R1_EVIDENCE_COMMIT,
            "v50r1_campaign_id": V50R1_CAMPAIGN_ID,
            "v50r1_campaign_sha256": V50R1_CAMPAIGN_SHA256,
            "v50r1_verification_id": V50R1_VERIFICATION_ID,
            "all_v50r1_identities_preserved": True,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "frozen_before_any_v51_registered_outcome": True,
            "development_seed_identities_disjoint_from_registered_identities": True,
        },
        "factor_boundary_discovery": {
            "rule": "CONNECTED_COMPONENTS_OF_ANONYMOUS_STATE_AND_NEXT_OUTPUT_DEPENDENCIES",
            "expression_normalization": "ALPHA_RENAME_ANONYMOUS_STATE_ACTION_NEXT_CONSTANT_AND_RELATION_REFERENCES",
            "semantic_names_available": False,
            "predeclared_factor_roles": [],
        },
        "cross_schema_library": {
            "source_schema_pairs": [[7, 5], [9, 6]],
            "transferable_opcodes": sorted(TRANSFERABLE_OPCODES_V7),
            "minimum_distinct_source_schema_pairs_per_subprogram": 2,
            "minimum_reused_factor_count": MINIMUM_REUSED_FACTOR_COUNT,
            "caller_selected_factor_roles": [],
        },
        "target_domain": {
            "raw_state_width": 10,
            "raw_action_field_width": 6,
            "source_stage_count": SOURCE_STAGE_COUNT,
            "source_primary_base": SOURCE_PRIMARY_BASE,
            "source_seeds": list(SOURCE_SEEDS),
            "target_stage_count": TARGET_STAGE_COUNT,
            "target_primary_base": TARGET_PRIMARY_BASE,
            "target_seeds": list(TARGET_SEEDS),
            "higher_order_primary_update": "STATE_PLUS_TWO_ANONYMOUS_ACTION_INCREMENTS",
            "partial_stochastic_support": "TWO_POINT_RISK_SUCCESSOR_SUPPORT",
            "generation_witness_available_to_constructor": False,
        },
        "program_construction": {
            "opcodes": generic_atomic_opcode_documents_v4(),
            "maximum_composition_depth": ATOMIC_COMPOSITION_MAX_DEPTH_V4,
            "fallback_beam_width": ATOMIC_COMPOSITION_BEAM_WIDTH_V4,
            "source_signature_unification_then_exact_target_raw_residual": True,
            "full_fallback_used_for_novel_factor_discovery_and_audit": True,
            "fallback_compute_counted_separately_from_sample_labels": True,
            "factor_prior_sample_savings_claimed_without_ablation": False,
        },
        "acquisition_and_recovery": {
            "source_policy": "WITNESS_BLIND_EXHAUSTIVE_REACHABLE_FRONTIER_ALL_LEGAL_SUPPORTS",
            "target_layout_policy": "WITNESS_BLIND_BFS_UNTIL_STABLE_MINIMUM_RELATION_GRAPH_MATCH",
            "maximum_source_labels_per_occurrence": MAXIMUM_SOURCE_LABELS_PER_OCCURRENCE,
            "maximum_target_layout_labels_per_occurrence": MAXIMUM_TARGET_LAYOUT_LABELS,
            "maximum_relation_output_candidate": MAXIMUM_RELATION_OUTPUT_CANDIDATE,
            "local_ground_distinction_only_after_failed_certificate": True,
            "immutable_overlay_reused_across_held_out_occurrences": True,
        },
        "matched_controls": {
            "arms": [
                "CROSS_SCHEMA_FACTOR_COMPOSED_ABSTRACT",
                "STRICT_EXACT_CONTEXT",
            ],
            "same_initial_state_seed_and_outcome_tape": True,
            "strict_arm_receives_no_factor_prior": True,
            "historical_labels_new_source_labels_target_labels_execution_steps_factor_fallback_planning_and_certificate_compute_separate": True,
        },
        "ood_control": {
            "candidate_schema_pair": [4, 3],
            "candidate_only_factor": "INT_BIT_OR_STATE_ACTION",
            "minimum_required_reused_factor_count": MINIMUM_REUSED_FACTOR_COUNT,
            "prior_transfer_before_compatibility_check": False,
            "outcome_execution_before_compatibility_check": False,
        },
        "required_positive_conditions": [
            "ANONYMOUS_FACTOR_BOUNDARIES_DERIVED_WITHOUT_PREDECLARED_ROLES",
            "SUBPROGRAM_SIGNATURES_OBSERVED_IN_TWO_DIFFERENT_SOURCE_SCHEMAS",
            "AT_LEAST_THREE_FACTORS_COMPOSED_IN_FRESH_10_BY_6_TARGET_SCHEMA",
            "HIGHER_ORDER_AND_PARTIAL_STOCHASTIC_PROGRAM_EXACT",
            "ALL_MATCHED_HELD_OUT_EPISODES_SUCCEED",
            "EVERY_LOCAL_GROUND_DISTINCTION_FOLLOWS_A_FAILED_CERTIFICATE",
            "STRICT_INCOMPATIBLE_FACTOR_SIGNATURE_OOD_REJECTED_WITHOUT_OUTCOME",
            "CUMULATIVE_STRUCTURAL_LABELS_LESS_THAN_CUMULATIVE_STRICT_LABELS",
        ],
        "claim_boundary": {
            "finite_integer_expression_grammar": True,
            "bounded_full_fallback_audit": True,
            "unbounded_cross_schema_transfer_claimed": False,
            "factor_prior_sample_savings_claimed_without_ablation": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "future_content_domains": dict(FUTURE_DOMAINS),
        "fresh_v51_registered_outcome_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": content_id(FUTURE_DOMAINS["preregistration"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CrossSchemaFactorPreregistrationV51:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V51 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V51 preregistration canonical bytes changed")
        payload = {
            key: value for key, value in document.items() if key != "preregistration_id"
        }
        if (
            document.get("preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V51 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def freeze_cross_schema_factor_preregistration_v51() -> CrossSchemaFactorPreregistrationV51:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V51 preregistration changed")
    return CrossSchemaFactorPreregistrationV51(_ISSUER, raw, identity)


def verify_cross_schema_factor_preregistration_v51(
    value: CrossSchemaFactorPreregistrationV51,
) -> CrossSchemaFactorPreregistrationV51:
    if type(value) is not CrossSchemaFactorPreregistrationV51:
        _fail("V51 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_cross_schema_factor_preregistration_v51()
    if value.canonical_bytes != expected.canonical_bytes:
        _fail("V51 preregistration semantics changed")
    return value


__all__ = (
    "BOUND_SOURCE_PATHS",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "PREREGISTRATION_ID",
    "CrossSchemaFactorPreregistrationV51",
    "campaign_config_v51",
    "freeze_cross_schema_factor_preregistration_v51",
    "verify_cross_schema_factor_preregistration_v51",
)
