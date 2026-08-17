"""Outcome-free V50r1 registration after the frozen V50 dependency failure."""

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
from acfqp.generic_layout_factorized_world_model_v5 import (
    LAYOUT_REFINEMENT_MAX_ROUNDS_V5,
    LAYOUT_RELATION_META_GRAMMAR_V5,
    META_PRIOR_ALIGNMENT_MAX_CANDIDATES_V5,
)
from acfqp.generic_layout_factorized_world_model_v6 import (
    SAFE_TERMINAL_TREE_BEAM_WIDTH_V6,
    SAFE_TERMINAL_TREE_MAX_DEPTH_V6,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_CAMPAIGN_V50R1_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_DEPENDENCY_SUPPORT_V50R1_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_FAILED_CERTIFICATE_V50R1_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_LAYOUT_V50R1_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_LOCAL_DISTINCTION_V50R1_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_OOD_REJECTION_V50R1_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_PREREGISTRATION_V50R1_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_PROGRAM_V50R1_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_RAW_OBSERVATION_V50R1_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_RECEDING_EPISODE_V50R1_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_SAMPLE_TAX_V50R1_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_VERIFICATION_V50R1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "50.1.0"
PROPOSED_CONTRACT_VERSION = "2.0.220"
PROFILE_KEY = "construction_k7_automatic_layout_factorization_v50r1"
PREREGISTRATION_ID = "b2fece3d681121fb3c0b72af92f7dc9466a643e143e53d0e80574b5acfb73fcf"
EXPECTED_CANONICAL_BYTE_COUNT = 7_789
EXPECTED_CANONICAL_SHA256 = "ae09ef2dd41d8929020d4ab2ebbb5c3e83d6354b1b9eef0f7829720880f86a9a"

V50_PREREGISTRATION_COMMIT = "5dd443f"
V50_FAILURE_COMMIT = "e65e74b"
V50_SUCCESSOR_IMPLEMENTATION_COMMIT = "b09903f"
V50_PREREGISTRATION_ID = (
    "6f3199a6d0bad3abc11cb68e0b60183d97871a60702f66cb4d5d877a150b2782"
)
V50_FAILURE_ID = (
    "603e1e69ed5e4093675435ffda6aa1de82118d93b44232a9cfc0454a00424581"
)
V50_FAILED_PRODUCER_SHA256 = (
    "2d1a8f947bd3ba185f7270c3928266f46d8cdff368a2a4eeadc981f4e04cf346"
)

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/generic_atomic_expression_world_model_v4.py",
    "src/acfqp/generic_layout_factorized_world_model_v5.py",
    "src/acfqp/generic_layout_factorized_world_model_v6.py",
    "src/acfqp/layout_factorized_campaign_core_v50.py",
    "src/acfqp/layout_factorized_campaign_core_v50r1.py",
    "src/acfqp/domains/stochastic_modular_routing.py",
    "src/acfqp/domains/stochastic_inventory_assembly.py",
)

TERMINAL_TOKENS = {"A": 9_001, "F": 9_007, "S": 9_011}
MODE_TOKENS = (8_001, 8_009, 8_021, 8_039)
CLASS_TOKENS = (8_101, 8_111, 8_117)
MODULAR_SOURCE_SPEC = {
    "node_count": 6,
    "modulus": 7,
    "capacity": 20,
    "step_limit": 7,
    "mode_deltas": (1, 2, 3),
}
MODULAR_SOURCE_SEEDS = (502_101, 502_102, 502_103)
MODULAR_TARGET_SPEC = {
    "node_count": 7,
    "modulus": 11,
    "capacity": 24,
    "step_limit": 8,
    "mode_deltas": (1, 2, 4, 5),
}
MODULAR_TARGET_SEEDS = tuple(range(502_301, 502_309))
INVENTORY_SOURCE_STAGE_COUNT = 6
INVENTORY_SOURCE_SEEDS = (502_201, 502_202, 502_203)
INVENTORY_TARGET_STAGE_COUNT = 7
INVENTORY_TARGET_SEEDS = tuple(range(502_401, 502_409))
MAXIMUM_SOURCE_LABELS_PER_OCCURRENCE = 512
MAXIMUM_TARGET_LAYOUT_LABELS = 16

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_PREREGISTRATION_V50R1_DOMAIN,
    "observation": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_RAW_OBSERVATION_V50R1_DOMAIN,
    "layout": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_LAYOUT_V50R1_DOMAIN,
    "program": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_PROGRAM_V50R1_DOMAIN,
    "support": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_DEPENDENCY_SUPPORT_V50R1_DOMAIN,
    "failed_certificate": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_FAILED_CERTIFICATE_V50R1_DOMAIN,
    "distinction": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_LOCAL_DISTINCTION_V50R1_DOMAIN,
    "episode": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_RECEDING_EPISODE_V50R1_DOMAIN,
    "sample_tax": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_SAMPLE_TAX_V50R1_DOMAIN,
    "ood": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_OOD_REJECTION_V50R1_DOMAIN,
    "campaign": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_CAMPAIGN_V50R1_DOMAIN,
    "verification": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_VERIFICATION_V50R1_DOMAIN,
}


class ConstructionK7LayoutFactorizationPreregistrationV50R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LayoutFactorizationPreregistrationV50R1Error(message)


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


def _spec_document(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: list(item) if type(item) is tuple else item
        for key, item in value.items()
    }


def campaign_config_v50r1() -> dict[str, Any]:
    return {
        "domains": dict(FUTURE_DOMAINS),
        "terminal_tokens": dict(TERMINAL_TOKENS),
        "mode_tokens": MODE_TOKENS,
        "class_tokens": CLASS_TOKENS,
        "modular_source_spec": dict(MODULAR_SOURCE_SPEC),
        "modular_source_seeds": MODULAR_SOURCE_SEEDS,
        "modular_target_spec": dict(MODULAR_TARGET_SPEC),
        "modular_target_seeds": MODULAR_TARGET_SEEDS,
        "inventory_source_stage_count": INVENTORY_SOURCE_STAGE_COUNT,
        "inventory_source_seeds": INVENTORY_SOURCE_SEEDS,
        "inventory_target_stage_count": INVENTORY_TARGET_STAGE_COUNT,
        "inventory_target_seeds": INVENTORY_TARGET_SEEDS,
        "maximum_source_labels_per_occurrence": MAXIMUM_SOURCE_LABELS_PER_OCCURRENCE,
        "maximum_target_layout_labels": MAXIMUM_TARGET_LAYOUT_LABELS,
    }


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.layout_factorization_preregistration.v50r1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_failed_predecessor": {
            "v50_preregistration_commit": V50_PREREGISTRATION_COMMIT,
            "v50_failure_commit": V50_FAILURE_COMMIT,
            "v50_successor_implementation_commit": V50_SUCCESSOR_IMPLEMENTATION_COMMIT,
            "v50_preregistration_id": V50_PREREGISTRATION_ID,
            "v50_failure_id": V50_FAILURE_ID,
            "v50_failed_producer_sha256": V50_FAILED_PRODUCER_SHA256,
            "same_v50_identity_rerun_forbidden": True,
            "failed_predecessor_preserved_without_mutation": True,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "frozen_before_any_v50r1_registered_source_or_target_outcome": True,
            "development_seed_identities_disjoint_from_registered_identities": True,
        },
        "single_dependency_correction": {
            "predecessor_orchestration_code_reused_without_mutation": True,
            "private_copied_global_namespace_used": True,
            "rebound_dependency_count": 1,
            "rebound_from": "synthesize_layout_factorized_world_model_v5",
            "rebound_to": "synthesize_layout_factorized_world_model_v6",
            "caller_supplied_callback_present": False,
            "terminal_next_status_column_candidates_excluded": True,
            "terminal_self_next_dependency_count": 0,
            "safe_terminal_max_depth": SAFE_TERMINAL_TREE_MAX_DEPTH_V6,
            "safe_terminal_beam_width": SAFE_TERMINAL_TREE_BEAM_WIDTH_V6,
        },
        "raw_interface": {
            "state": "OPAQUE_FLAT_INTEGER_COLUMNS_WITH_PER_OCCURRENCE_PERMUTATION",
            "action": "OPAQUE_KEY_PLUS_ANONYMOUS_PERMUTED_INTEGER_FIELDS",
            "layout_positions_preregistered": False,
            "semantic_state_or_action_names_available_to_synthesizer": False,
            "adapter_provided_abstract_state_present": False,
        },
        "layout_factorization": {
            "relation_meta_grammar": list(LAYOUT_RELATION_META_GRAMMAR_V5),
            "reference_selection": "FIRST_SOURCE_ANONYMOUS_RELATION_GRAPH",
            "source_alignment": "MINIMUM_EXACT_TYPED_RELATION_GRAPH_EDIT",
            "target_alignment": "SOURCE_DERIVED_STRUCTURAL_META_PRIOR_WITH_WITNESS_BLIND_RAW_SUPPORTS",
            "target_stop_rule": "TWO_CONSECUTIVE_IDENTICAL_UNIQUE_MINIMUM_ALIGNMENTS",
            "maximum_refinement_rounds": LAYOUT_REFINEMENT_MAX_ROUNDS_V5,
            "maximum_meta_prior_candidate_alignments": META_PRIOR_ALIGNMENT_MAX_CANDIDATES_V5,
            "predeclared_layout_or_factor_roles": [],
            "specialized_layout_discovery_pattern_count": 0,
        },
        "atomic_program_synthesis": {
            "opcodes": generic_atomic_opcode_documents_v4(),
            "maximum_composition_depth": ATOMIC_COMPOSITION_MAX_DEPTH_V4,
            "residual_mdl_beam_width": ATOMIC_COMPOSITION_BEAM_WIDTH_V4,
            "terminal_next_status_column_candidates_excluded": True,
            "whole_program_template_count": 0,
            "specialized_discovery_pattern_count": 0,
        },
        "fresh_workload": {
            "modular_source_spec": _spec_document(MODULAR_SOURCE_SPEC),
            "modular_source_seeds": list(MODULAR_SOURCE_SEEDS),
            "modular_target_spec": _spec_document(MODULAR_TARGET_SPEC),
            "modular_target_seeds": list(MODULAR_TARGET_SEEDS),
            "inventory_source_stage_count": INVENTORY_SOURCE_STAGE_COUNT,
            "inventory_source_seeds": list(INVENTORY_SOURCE_SEEDS),
            "inventory_target_stage_count": INVENTORY_TARGET_STAGE_COUNT,
            "inventory_target_seeds": list(INVENTORY_TARGET_SEEDS),
            "all_registered_seed_identities_fresh_after_v50_failure": True,
            "matched_target_occurrence_count": len(MODULAR_TARGET_SEEDS)
            + len(INVENTORY_TARGET_SEEDS),
        },
        "acquisition_and_recovery_protocol": {
            "source_policy": "WITNESS_BLIND_EXHAUSTIVE_REACHABLE_FRONTIER_ALL_LEGAL_SUPPORTS",
            "target_layout_policy": "WITNESS_BLIND_BFS_UNTIL_STABLE_STRUCTURAL_META_PRIOR_ALIGNMENT",
            "maximum_source_labels_per_occurrence": MAXIMUM_SOURCE_LABELS_PER_OCCURRENCE,
            "maximum_target_layout_labels_per_occurrence": MAXIMUM_TARGET_LAYOUT_LABELS,
            "local_ground_distinction_allowed_only_after_failed_compiled_certificate": True,
            "immutable_overlay_reuse_required": True,
        },
        "matched_controls": {
            "arms": ["DERIVED_LAYOUT_STRUCTURAL_PRIOR", "STRICT_EXACT_CONTEXT"],
            "same_kernel_seed_and_outcome_tape": True,
            "same_initial_state_and_success_contract": True,
            "strict_arm_receives_no_source_prior": True,
            "all_sample_and_compute_axes_separate": True,
        },
        "required_positive_conditions": [
            "UNIQUE_LAYOUT_RECOVERED_UNDER_INDEPENDENT_SOURCE_AND_TARGET_PERMUTATIONS",
            "SAME_GENERIC_ATOMIC_SYNTHESIZER_EXACT_IN_BOTH_STOCHASTIC_DOMAINS",
            "SAFE_TERMINAL_DEPENDENCIES_EXACT_IN_BOTH_DOMAINS",
            "ALL_MATCHED_STRUCTURAL_AND_STRICT_EPISODES_SUCCEED",
            "EVERY_LOCAL_GROUND_DISTINCTION_FOLLOWS_A_FAILED_CERTIFICATE",
            "STRICT_CROSS_DOMAIN_OOD_REJECTED_BEFORE_PRIOR_TRANSFER_OR_OUTCOME",
            "OFFLINE_PLUS_STRUCTURAL_TARGET_LABELS_STRICTLY_LESS_THAN_STRICT_TARGET_LABELS",
        ],
        "claim_boundary": {
            "finite_integer_relation_meta_grammar": True,
            "bounded_source_derived_structural_meta_prior": True,
            "arbitrary_tensor_or_open_world_perception_claimed": False,
            "unbounded_domain_general_world_model_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "future_content_domains": dict(FUTURE_DOMAINS),
        "fresh_v50r1_registered_outcome_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": content_id(FUTURE_DOMAINS["preregistration"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LayoutFactorizationPreregistrationV50R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V50r1 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V50r1 preregistration canonical bytes changed")
        payload = {
            key: value for key, value in document.items() if key != "preregistration_id"
        }
        if (
            document.get("preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V50r1 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def freeze_layout_factorization_preregistration_v50r1(
) -> LayoutFactorizationPreregistrationV50R1:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V50r1 preregistration changed")
    return LayoutFactorizationPreregistrationV50R1(_ISSUER, raw, identity)


def verify_layout_factorization_preregistration_v50r1(
    value: LayoutFactorizationPreregistrationV50R1,
) -> LayoutFactorizationPreregistrationV50R1:
    if type(value) is not LayoutFactorizationPreregistrationV50R1:
        _fail("V50r1 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_layout_factorization_preregistration_v50r1()
    if value.canonical_bytes != expected.canonical_bytes:
        _fail("V50r1 preregistration semantics changed")
    return value


__all__ = (
    "BOUND_SOURCE_PATHS",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "LayoutFactorizationPreregistrationV50R1",
    "PREREGISTRATION_ID",
    "campaign_config_v50r1",
    "freeze_layout_factorization_preregistration_v50r1",
    "verify_layout_factorization_preregistration_v50r1",
)
