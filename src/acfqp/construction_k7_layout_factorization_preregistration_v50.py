"""Outcome-free V50 registration for automatic layout/factor discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    ATOMIC_COMPOSITION_BEAM_WIDTH_V4,
    ATOMIC_COMPOSITION_MAX_DEPTH_V4,
    TERMINAL_TREE_BEAM_WIDTH_V4,
    TERMINAL_TREE_MAX_DEPTH_V4,
    generic_atomic_opcode_documents_v4,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    LAYOUT_REFINEMENT_MAX_ROUNDS_V5,
    LAYOUT_RELATION_META_GRAMMAR_V5,
    META_PRIOR_ALIGNMENT_MAX_CANDIDATES_V5,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_CAMPAIGN_V50_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_DEPENDENCY_SUPPORT_V50_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_FAILED_CERTIFICATE_V50_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_LAYOUT_V50_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_LOCAL_DISTINCTION_V50_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_OOD_REJECTION_V50_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_PREREGISTRATION_V50_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_PROGRAM_V50_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_RAW_OBSERVATION_V50_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_RECEDING_EPISODE_V50_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_SAMPLE_TAX_V50_DOMAIN,
    CONSTRUCTION_K7_LAYOUT_FACTORIZATION_VERIFICATION_V50_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "50.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.219"
PROFILE_KEY = "construction_k7_automatic_layout_factorization_v50"
PREREGISTRATION_ID = "6f3199a6d0bad3abc11cb68e0b60183d97871a60702f66cb4d5d877a150b2782"
EXPECTED_CANONICAL_BYTE_COUNT = 6_961
EXPECTED_CANONICAL_SHA256 = "32af6d3db784d1bb770fd391d254fe4a6efe1bc0faba37b17daeae9e15c78964"

V49R3_PREREGISTRATION_COMMIT = "60f508a"
V49R3_EVIDENCE_COMMIT = "cb17368"
V49R3_PREREGISTRATION_ID = (
    "90198055b383f88f46d44887951601628473c5b32e68b30f5386237b540b92d3"
)
V49R3_CAMPAIGN_ID = (
    "50c7786f7ab89872e4e95ce9a94a8691352cc4899a82554518d6fed07ec18fa3"
)
V49R3_VERIFICATION_ID = (
    "7ae6d7309b493fa3f669eab9869d801eb72e2615df4f06cb8cde4a81064f1be5"
)

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/generic_atomic_expression_world_model_v4.py",
    "src/acfqp/generic_layout_factorized_world_model_v5.py",
    "src/acfqp/layout_factorized_campaign_core_v50.py",
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
MODULAR_SOURCE_SEEDS = (501_101, 501_102, 501_103)
MODULAR_TARGET_SPEC = {
    "node_count": 7,
    "modulus": 11,
    "capacity": 24,
    "step_limit": 8,
    "mode_deltas": (1, 2, 4, 5),
}
MODULAR_TARGET_SEEDS = tuple(range(501_301, 501_309))
INVENTORY_SOURCE_STAGE_COUNT = 6
INVENTORY_SOURCE_SEEDS = (501_201, 501_202, 501_203)
INVENTORY_TARGET_STAGE_COUNT = 7
INVENTORY_TARGET_SEEDS = tuple(range(501_401, 501_409))
MAXIMUM_SOURCE_LABELS_PER_OCCURRENCE = 512
MAXIMUM_TARGET_LAYOUT_LABELS = 16

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_PREREGISTRATION_V50_DOMAIN,
    "observation": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_RAW_OBSERVATION_V50_DOMAIN,
    "layout": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_LAYOUT_V50_DOMAIN,
    "program": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_PROGRAM_V50_DOMAIN,
    "support": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_DEPENDENCY_SUPPORT_V50_DOMAIN,
    "failed_certificate": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_FAILED_CERTIFICATE_V50_DOMAIN,
    "distinction": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_LOCAL_DISTINCTION_V50_DOMAIN,
    "episode": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_RECEDING_EPISODE_V50_DOMAIN,
    "sample_tax": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_SAMPLE_TAX_V50_DOMAIN,
    "ood": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_OOD_REJECTION_V50_DOMAIN,
    "campaign": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_CAMPAIGN_V50_DOMAIN,
    "verification": CONSTRUCTION_K7_LAYOUT_FACTORIZATION_VERIFICATION_V50_DOMAIN,
}


class ConstructionK7LayoutFactorizationPreregistrationV50Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LayoutFactorizationPreregistrationV50Error(message)


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


def campaign_config_v50() -> dict[str, Any]:
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
        "schema": "acfqp.layout_factorization_preregistration.v50",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessor": {
            "v49r3_preregistration_commit": V49R3_PREREGISTRATION_COMMIT,
            "v49r3_evidence_commit": V49R3_EVIDENCE_COMMIT,
            "v49r3_preregistration_id": V49R3_PREREGISTRATION_ID,
            "v49r3_campaign_id": V49R3_CAMPAIGN_ID,
            "v49r3_verification_id": V49R3_VERIFICATION_ID,
            "all_v49r3_identities_preserved": True,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "frozen_before_any_v50_registered_source_or_target_outcome": True,
            "development_seed_identities_disjoint_from_registered_identities": True,
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
            "terminal_tree_maximum_depth": TERMINAL_TREE_MAX_DEPTH_V4,
            "terminal_tree_impurity_beam_width": TERMINAL_TREE_BEAM_WIDTH_V4,
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
            "all_registered_seed_identities_fresh_after_v49r3": True,
            "matched_target_occurrence_count": len(MODULAR_TARGET_SEEDS)
            + len(INVENTORY_TARGET_SEEDS),
        },
        "acquisition_and_recovery_protocol": {
            "source_policy": "WITNESS_BLIND_EXHAUSTIVE_REACHABLE_FRONTIER_ALL_LEGAL_SUPPORTS",
            "target_layout_policy": "WITNESS_BLIND_BFS_UNTIL_STABLE_STRUCTURAL_META_PRIOR_ALIGNMENT",
            "maximum_source_labels_per_occurrence": MAXIMUM_SOURCE_LABELS_PER_OCCURRENCE,
            "maximum_target_layout_labels_per_occurrence": MAXIMUM_TARGET_LAYOUT_LABELS,
            "numeric_relation_values_from_layout_calibration_reused": False,
            "local_ground_distinction_allowed_only_after_failed_compiled_certificate": True,
            "immutable_overlay_reuse_required": True,
        },
        "matched_controls": {
            "arms": ["DERIVED_LAYOUT_STRUCTURAL_PRIOR", "STRICT_EXACT_CONTEXT"],
            "same_kernel_seed_and_outcome_tape": True,
            "same_initial_state_and_success_contract": True,
            "strict_arm_receives_no_source_prior": True,
            "source_labels_target_layout_labels_local_labels_execution_steps_layout_derivation_atomic_synthesis_planning_and_certificate_compute_separate": True,
        },
        "required_positive_conditions": [
            "UNIQUE_LAYOUT_RECOVERED_UNDER_INDEPENDENT_SOURCE_AND_TARGET_PERMUTATIONS",
            "SAME_GENERIC_ATOMIC_SYNTHESIZER_EXACT_IN_BOTH_STOCHASTIC_DOMAINS",
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
        "fresh_v50_registered_outcome_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": content_id(FUTURE_DOMAINS["preregistration"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LayoutFactorizationPreregistrationV50:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V50 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V50 preregistration canonical bytes changed")
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if (
            document.get("preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V50 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def freeze_layout_factorization_preregistration_v50() -> LayoutFactorizationPreregistrationV50:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V50 preregistration changed")
    return LayoutFactorizationPreregistrationV50(_ISSUER, raw, identity)


def verify_layout_factorization_preregistration_v50(
    value: LayoutFactorizationPreregistrationV50,
) -> LayoutFactorizationPreregistrationV50:
    if type(value) is not LayoutFactorizationPreregistrationV50:
        _fail("V50 preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("V50 preregistration semantics changed")
    return value


__all__ = (
    "BOUND_SOURCE_PATHS",
    "CLASS_TOKENS",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "INVENTORY_SOURCE_SEEDS",
    "INVENTORY_SOURCE_STAGE_COUNT",
    "INVENTORY_TARGET_SEEDS",
    "INVENTORY_TARGET_STAGE_COUNT",
    "LayoutFactorizationPreregistrationV50",
    "MAXIMUM_SOURCE_LABELS_PER_OCCURRENCE",
    "MAXIMUM_TARGET_LAYOUT_LABELS",
    "MODE_TOKENS",
    "MODULAR_SOURCE_SEEDS",
    "MODULAR_SOURCE_SPEC",
    "MODULAR_TARGET_SEEDS",
    "MODULAR_TARGET_SPEC",
    "PREREGISTRATION_ID",
    "SOURCE_ROOT",
    "TERMINAL_TOKENS",
    "campaign_config_v50",
    "freeze_layout_factorization_preregistration_v50",
    "verify_layout_factorization_preregistration_v50",
)
