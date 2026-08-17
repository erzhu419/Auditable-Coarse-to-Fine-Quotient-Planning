"""Outcome-free V49 registration for generic atomic program composition."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    ATOMIC_COMPOSITION_BEAM_WIDTH_V4,
    ATOMIC_COMPOSITION_MAX_DEPTH_V4,
    GENERIC_ATOMIC_TYPES_V4,
    TERMINAL_TREE_BEAM_WIDTH_V4,
    TERMINAL_TREE_MAX_DEPTH_V4,
    generic_atomic_opcode_documents_v4,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_ADAPTIVE_ACQUISITION_V49_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_CAMPAIGN_V49_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_DEPENDENCY_SUPPORT_V49_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_FAILED_CERTIFICATE_V49_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_LOCAL_DISTINCTION_V49_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_OOD_REJECTION_V49_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_PARTIAL_DYNAMICS_V49_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_PREREGISTRATION_V49_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_PROGRAM_V49_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_RAW_OBSERVATION_V49_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_RECEDING_EPISODE_V49_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_SAMPLE_TAX_V49_DOMAIN,
    CONSTRUCTION_K7_ATOMIC_COMPOSITION_VERIFICATION_V49_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "49.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.215"
PROFILE_KEY = "construction_k7_generic_atomic_composition_v49"
PREREGISTRATION_ID = "40c05b0379d5b76f8c2f31db6409951a9b8afc823287bafd740c2b6e16059370"
EXPECTED_CANONICAL_BYTE_COUNT = 7_332
EXPECTED_CANONICAL_SHA256 = "0d34d3640f1bfe965f4cc29189ab07b364f49e34a9c70a84d9245c767984e97f"

V48_PREREGISTRATION_COMMIT = "74f7ee3e7473a96c89745b5264a72fdd81692888"
V48_EVIDENCE_COMMIT = "91ec69e4f4703955981472371f127500b1a35130"
V48_PREREGISTRATION_ID = "55f7a36ccb04361d377570cc6d3681b444be37705a0bbb5ae2b68fb41a88b79e"
V48_CAMPAIGN_ID = "f8fff551812e7dce6d66bcbe68f5dfa8b1c6be66496f1383f9f6982bb2252a3f"
V48_VERIFICATION_ID = "6d5a680b770dd3eac4cef3a6f925a864b0ec9b4f08c8163a381dd1e12ed3eb6c"

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/generic_atomic_expression_world_model_v4.py",
    "src/acfqp/domains/stochastic_modular_routing.py",
)

SOURCE_SPEC = {
    "node_count": 6,
    "modulus": 7,
    "capacity": 20,
    "step_limit": 7,
    "mode_deltas": (1, 2, 3),
}
SOURCE_SEEDS = (491101, 491102, 491103)
TARGET_SPEC = {
    "node_count": 7,
    "modulus": 11,
    "capacity": 24,
    "step_limit": 8,
    "mode_deltas": (1, 2, 4, 5),
}
TARGET_SEEDS = tuple(range(491301, 491313))
SHARED_MODE_TOKENS = (8_001, 8_009, 8_021, 8_039)
SHARED_CLASS_TOKENS = (8_101, 8_111, 8_117)
SHARED_TERMINAL_TOKENS = {"A": 9_001, "F": 9_007, "S": 9_011}
STATE_LAYOUT_ORDER = (6, 0, 4, 2, 8, 1, 5, 3, 7)
ACTION_FIELD_ORDER = (4, 0, 5, 2, 1, 3)
MAX_SOURCE_LABELS_PER_OCCURRENCE = 512
RECEDING_HORIZON = 4
ARMS = ("COMPOSED_STRUCTURAL_PRIOR", "STRICT_EXACT_CONTEXT")

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_ATOMIC_COMPOSITION_PREREGISTRATION_V49_DOMAIN,
    "observation": CONSTRUCTION_K7_ATOMIC_COMPOSITION_RAW_OBSERVATION_V49_DOMAIN,
    "program": CONSTRUCTION_K7_ATOMIC_COMPOSITION_PROGRAM_V49_DOMAIN,
    "support": CONSTRUCTION_K7_ATOMIC_COMPOSITION_DEPENDENCY_SUPPORT_V49_DOMAIN,
    "failed_certificate": CONSTRUCTION_K7_ATOMIC_COMPOSITION_FAILED_CERTIFICATE_V49_DOMAIN,
    "distinction": CONSTRUCTION_K7_ATOMIC_COMPOSITION_LOCAL_DISTINCTION_V49_DOMAIN,
    "episode": CONSTRUCTION_K7_ATOMIC_COMPOSITION_RECEDING_EPISODE_V49_DOMAIN,
    "partial": CONSTRUCTION_K7_ATOMIC_COMPOSITION_PARTIAL_DYNAMICS_V49_DOMAIN,
    "acquisition": CONSTRUCTION_K7_ATOMIC_COMPOSITION_ADAPTIVE_ACQUISITION_V49_DOMAIN,
    "sample_tax": CONSTRUCTION_K7_ATOMIC_COMPOSITION_SAMPLE_TAX_V49_DOMAIN,
    "ood": CONSTRUCTION_K7_ATOMIC_COMPOSITION_OOD_REJECTION_V49_DOMAIN,
    "campaign": CONSTRUCTION_K7_ATOMIC_COMPOSITION_CAMPAIGN_V49_DOMAIN,
    "verification": CONSTRUCTION_K7_ATOMIC_COMPOSITION_VERIFICATION_V49_DOMAIN,
}


class ConstructionK7AtomicCompositionPreregistrationV49Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AtomicCompositionPreregistrationV49Error(message)


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


def _normalized_spec(value: dict[str, Any]) -> dict[str, Any]:
    return {
        **value,
        "mode_deltas": list(value["mode_deltas"]),
    }


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.atomic_composition_preregistration.v49",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessor": {
            "v48_preregistration_commit": V48_PREREGISTRATION_COMMIT,
            "v48_evidence_commit": V48_EVIDENCE_COMMIT,
            "v48_preregistration_id": V48_PREREGISTRATION_ID,
            "v48_campaign_id": V48_CAMPAIGN_ID,
            "v48_verification_id": V48_VERIFICATION_ID,
            "all_v48_identities_preserved": True,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "frozen_before_any_v49_source_or_target_outcome": True,
        },
        "raw_interface": {
            "state": "OPAQUE_FIXED_WIDTH_INTEGER_VECTOR",
            "action": "OPAQUE_KEY_PLUS_ANONYMOUS_INTEGER_FIELDS",
            "observation": [
                "PRE_VECTOR",
                "LEGAL_KEYS_BEFORE",
                "ACTION_KEY_AND_FIELDS",
                "POST_VECTOR",
                "LEGAL_KEYS_AFTER",
                "TERMINAL_ACCEPTANCE_BIT",
                "OPTIONAL_OUTCOME_TAPE_SHA256",
            ],
            "state_layout_order": list(STATE_LAYOUT_ORDER),
            "action_field_order": list(ACTION_FIELD_ORDER),
            "layout_positions_shared_and_preregistered": True,
            "domain_name_available_to_synthesizer": False,
            "semantic_state_or_action_names_available_to_synthesizer": False,
            "adapter_provided_abstract_state_present": False,
        },
        "generic_atomic_search": {
            "types": list(GENERIC_ATOMIC_TYPES_V4),
            "opcodes": generic_atomic_opcode_documents_v4(),
            "whole_program_template_count": 0,
            "specialized_discovery_pattern_count": 0,
            "candidate_generation": "TYPED_BOTTOM_UP_ATOMIC_COMPOSITION",
            "maximum_composition_depth": ATOMIC_COMPOSITION_MAX_DEPTH_V4,
            "residual_mdl_beam_width": ATOMIC_COMPOSITION_BEAM_WIDTH_V4,
            "terminal_tree_maximum_depth": TERMINAL_TREE_MAX_DEPTH_V4,
            "terminal_tree_impurity_beam_width": TERMINAL_TREE_BEAM_WIDTH_V4,
            "selection": "MIN_EXACT_RESIDUAL_THEN_COMPOSITION_DEPTH_THEN_AST_MDL_THEN_CONTENT_HASH",
            "identifier_memorization_filter": "REJECT_ONE_VALUE_PER_ACTION_RELATION_KEYS",
            "support_derivation": "EXACT_COMPILED_LEAF_SINGLE_DELETION_ON_ALL_RAW_TRANSITIONS",
            "predeclared_semantic_support_names": [],
        },
        "fresh_workload": {
            "anonymous_family": "D03",
            "source_spec": _normalized_spec(SOURCE_SPEC),
            "source_seeds": list(SOURCE_SEEDS),
            "target_spec": _normalized_spec(TARGET_SPEC),
            "target_seeds": list(TARGET_SEEDS),
            "target_requires_last_unseen_mode": True,
            "shared_anonymous_mode_tokens": list(SHARED_MODE_TOKENS),
            "shared_anonymous_class_tokens": list(SHARED_CLASS_TOKENS),
            "shared_anonymous_terminal_tokens": SHARED_TERMINAL_TOKENS,
            "held_out_mode_token": SHARED_MODE_TOKENS[-1],
            "held_out_mode_absent_from_all_source_outcomes": True,
            "source_policy": "WITNESS_BLIND_EXHAUSTIVE_REACHABLE_FRONTIER_ALL_LEGAL_ACTION_SUPPORTS",
            "maximum_source_labels_per_occurrence": MAX_SOURCE_LABELS_PER_OCCURRENCE,
            "all_source_and_target_seed_identities_fresh_after_v48": True,
            "generation_witness_available_to_acquisition_or_synthesis": False,
        },
        "protocol": {
            "arms": list(ARMS),
            "receding_horizon": RECEDING_HORIZON,
            "planner_consumes_compiled_world_model_only": True,
            "kernel_transition_during_structural_planning_forbidden": True,
            "finite_support_is_authoritative_for_robust_planning": True,
            "support_probability_authority_claimed": False,
            "local_ground_label_only_after_failed_certificate": True,
            "held_out_relation_requires_failed_certificate_before_query": True,
            "immutable_overlay_reused_across_later_occurrences": True,
            "strict_control": "GROUND_SUPPORT_QUERY_EACH_NEW_EXACT_STATE_ACTION_CONTEXT_DURING_PLANNING",
            "strict_ood_schema": "OPAQUE_CONTINUOUS_REAL_VECTOR_WITH_INCOMPATIBLE_WIDTH",
            "strict_ood_prior_and_outcome_access": False,
        },
        "accounting": {
            "offline_source_support_labels": "SEPARATE_AXIS",
            "target_local_support_labels": "SEPARATE_AXIS",
            "execution_steps": "SEPARATE_AXIS",
            "atomic_derivation_compute": "SEPARATE_AXIS",
            "planning_compute": "SEPARATE_AXIS",
            "certificate_compute": "SEPARATE_AXIS",
            "peak_cache": "SEPARATE_AXIS",
            "positive_sample_tax_condition": "SOURCE_PLUS_LOCAL_SUPPORT_LABELS_LT_STRICT_TARGET_SUPPORT_LABELS",
            "diagnostic_break_even_only": True,
        },
        "required_positive_conditions": [
            "ZERO_WHOLE_PROGRAM_TEMPLATES_AND_ZERO_SPECIALIZED_DISCOVERY_PATTERNS",
            "MODULAR_RELATION_AND_STOCHASTIC_SUPPORT_COMPOSED_FROM_GENERIC_ATOMS",
            "EVERY_SOURCE_RAW_SUCCESSOR_REPLAYED_BY_COMPILED_PROGRAM",
            "DEPENDENCY_SUPPORT_DERIVED_BY_EXACT_SINGLE_LEAF_DELETION",
            "PLANNER_CONSUMES_COMPILED_WORLD_MODEL_ONLY",
            "FAILED_CERTIFICATE_PRECEDES_EVERY_LOCAL_GROUND_LABEL",
            "HELD_OUT_RELATION_LEARNED_ONCE_AND_OVERLAY_REUSED",
            "ALL_FRESH_TARGET_EPISODES_SUCCEED_UNDER_ROBUST_RECEDING_PLANNING",
            "MATCHED_TOTAL_REGISTERED_LABEL_AXIS_BEATS_STRICT_CONTROL",
            "STRICT_OOD_NO_TRANSFER_NO_OUTCOME",
            "PRODUCER_FREE_RECONSTRUCTION_PASSES",
        ],
        "claim_boundary": {
            "fresh_fourth_combination_domain_present": True,
            "fourth_unrelated_domain_authority_claimed": False,
            "higher_order_finite_support_planning_present_if_campaign_passes": False,
            "open_ended_layout_discovery_claimed": False,
            "broad_world_model_synthesis_claimed": False,
            "broad_cross_domain_sample_efficiency_claimed": False,
        },
        "outcome_fields_present": False,
        "fresh_v49_outcome_execution_performed": False,
        "campaign_artifact_issued": False,
        "sample_tax_result_issued": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "atomic_composition_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AtomicCompositionPreregistrationV49:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V49 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V49 preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "atomic_composition_preregistration_id"
        }
        if (
            document.get("atomic_composition_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V49 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def freeze_atomic_composition_preregistration_v49() -> AtomicCompositionPreregistrationV49:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["atomic_composition_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V49 preregistration changed")
    return AtomicCompositionPreregistrationV49(_ISSUER, raw, identity)


def verify_atomic_composition_preregistration_v49(
    value: AtomicCompositionPreregistrationV49,
) -> AtomicCompositionPreregistrationV49:
    if type(value) is not AtomicCompositionPreregistrationV49:
        _fail("V49 preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("V49 preregistration semantics changed")
    return value


__all__ = (
    "ACTION_FIELD_ORDER",
    "ARMS",
    "AtomicCompositionPreregistrationV49",
    "BOUND_SOURCE_PATHS",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "MAX_SOURCE_LABELS_PER_OCCURRENCE",
    "PREREGISTRATION_ID",
    "RECEDING_HORIZON",
    "SHARED_CLASS_TOKENS",
    "SHARED_MODE_TOKENS",
    "SHARED_TERMINAL_TOKENS",
    "SOURCE_ROOT",
    "SOURCE_SEEDS",
    "SOURCE_SPEC",
    "STATE_LAYOUT_ORDER",
    "TARGET_SEEDS",
    "TARGET_SPEC",
    "freeze_atomic_composition_preregistration_v49",
    "verify_atomic_composition_preregistration_v49",
)
