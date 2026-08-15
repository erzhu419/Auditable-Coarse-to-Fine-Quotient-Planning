"""Outcome-free V47 generic-bytecode, stochastic-transfer, and sample-tax Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp.generic_bytecode_world_model_v1 import (
    GENERIC_OPCODES,
    GENERIC_TYPES,
    generic_opcode_documents_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_GENERIC_BYTECODE_PREREGISTRATION_V47_DOMAIN,
    CONSTRUCTION_K7_GENERIC_BYTECODE_PROGRAM_V47_DOMAIN,
    CONSTRUCTION_K7_GENERIC_CROSS_DOMAIN_CAMPAIGN_V47_DOMAIN,
    CONSTRUCTION_K7_GENERIC_CROSS_DOMAIN_VERIFICATION_V47_DOMAIN,
    CONSTRUCTION_K7_GENERIC_LOCAL_DISTINCTION_V47_DOMAIN,
    CONSTRUCTION_K7_GENERIC_RAW_OBSERVATION_V47_DOMAIN,
    CONSTRUCTION_K7_GENERIC_RECEDING_EPISODE_V47_DOMAIN,
    CONSTRUCTION_K7_GENERIC_SAMPLE_TAX_V47_DOMAIN,
    CONSTRUCTION_K7_GENERIC_STOCHASTIC_PARTIAL_V47_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "47.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.212"
PROFILE_KEY = "construction_k7_generic_bytecode_cross_domain_v47"
PREREGISTRATION_ID = "feeaa6e1337181e2d4489a9fddaf1bec912984d05cd02727e2c930d084cee177"
EXPECTED_CANONICAL_BYTE_COUNT = 8204
EXPECTED_CANONICAL_SHA256 = "f05b8d4737d06377c598fe7b346eadf5799f9ff8ce4de7d8454037bc4b362f83"

V41_CAMPAIGN_ID = "1a576e0c8b34f52050f77366ec7ac39dab58bddd53ec91180ed9d6c092072732"
V41_VERIFICATION_ID = "a05a6b795a15a8dda596b148efe52b374cc687f125b1c14731466f83aa791396"
V46_FAILURE_ID = "b3303de4717ccc7232527cc83204279294d8756ccb965951bd27820abafa6a6b"
V46R1_CAMPAIGN_ID = "6d7d2c65ff6ce2146896179b89e9a9fea7a755d3a31c6f883e8371c1baffaa5c"
V46R1_VERIFICATION_ID = "dd1560746c3e7fb6b78897d82e89f02b4983a56593b93940019ffd4f04915944"

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/generic_bytecode_world_model_v1.py",
    "src/acfqp/domains/matching_buffer.py",
    "src/acfqp/domains/stochastic_routing.py",
)

LMB_SOURCE_SPEC = {
    "tile_count": 24,
    "type_count": 8,
    "capacity": 8,
    "max_layers": 6,
}
LMB_SOURCE_SEEDS = (470101, 470102, 470103, 470104)
LMB_TARGET_SPEC = {
    "tile_count": 27,
    "type_count": 9,
    "capacity": 9,
    "max_layers": 7,
}
LMB_TARGET_SEEDS = (471301, 471302, 471303, 471304, 471305, 471306)
LMB_MAX_SOURCE_LABELS = 192

ROUTING_SOURCE_SPEC = {"node_count": 9, "capacity": 12}
ROUTING_SOURCE_SEEDS = (472101, 472102, 472103, 472104)
ROUTING_SOURCE_EPISODES_PER_SEED = 8
ROUTING_TARGET_SPEC = {"node_count": 11, "capacity": 15}
ROUTING_TARGET_SEEDS = (
    473301,
    473302,
    473303,
    473304,
    473305,
    473306,
    473307,
    473308,
)
ROUTING_MAX_SOURCE_LABELS = 256

ARMS = ("STRUCTURAL_META_PRIOR", "STRICT_EXACT_CONTEXT")
RECEDING_HORIZON = 4
MAX_TARGET_LOCAL_LABELS_PER_EPISODE = 64
FLAT_LAYOUT_SALT = 0x47A1
ACTION_FIELD_SALT = 0x47B2
TOKEN_SALT = 0x47C3

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_GENERIC_BYTECODE_PREREGISTRATION_V47_DOMAIN,
    "observation": CONSTRUCTION_K7_GENERIC_RAW_OBSERVATION_V47_DOMAIN,
    "program": CONSTRUCTION_K7_GENERIC_BYTECODE_PROGRAM_V47_DOMAIN,
    "distinction": CONSTRUCTION_K7_GENERIC_LOCAL_DISTINCTION_V47_DOMAIN,
    "episode": CONSTRUCTION_K7_GENERIC_RECEDING_EPISODE_V47_DOMAIN,
    "stochastic": CONSTRUCTION_K7_GENERIC_STOCHASTIC_PARTIAL_V47_DOMAIN,
    "sample_tax": CONSTRUCTION_K7_GENERIC_SAMPLE_TAX_V47_DOMAIN,
    "campaign": CONSTRUCTION_K7_GENERIC_CROSS_DOMAIN_CAMPAIGN_V47_DOMAIN,
    "verification": CONSTRUCTION_K7_GENERIC_CROSS_DOMAIN_VERIFICATION_V47_DOMAIN,
}


class ConstructionK7GenericBytecodePreregistrationV47Error(ValueError):
    """The generic grammar, fresh workloads, controls, or claim locks changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7GenericBytecodePreregistrationV47Error(message)


def _source_facts() -> list[dict[str, Any]]:
    facts = []
    for relative in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        facts.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return facts


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.generic_bytecode_preregistration.v47",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "v41_campaign_id": V41_CAMPAIGN_ID,
            "v41_verification_id": V41_VERIFICATION_ID,
            "v46_failure_id": V46_FAILURE_ID,
            "v46r1_campaign_id": V46R1_CAMPAIGN_ID,
            "v46r1_verification_id": V46R1_VERIFICATION_ID,
            "all_predecessor_identities_preserved": True,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "source_frozen_before_v47_outcomes": True,
        },
        "raw_interface": {
            "state": "OPAQUE_ORDERED_INTEGER_VECTOR",
            "action": "OPAQUE_KEY_PLUS_ANONYMOUS_INTEGER_FIELDS",
            "observation": [
                "PRE_VECTOR",
                "LEGAL_ACTION_KEYS_BEFORE",
                "SELECTED_ACTION_KEY_AND_FIELDS",
                "POST_VECTOR",
                "LEGAL_ACTION_KEYS_AFTER",
                "OPTIONAL_OUTCOME_TAPE_SHA256",
            ],
            "domain_name_available_to_synthesizer": False,
            "state_column_role_available_to_synthesizer": False,
            "action_field_role_available_to_synthesizer": False,
            "adapter_provided_abstract_state_present": False,
            "kernel_transition_allowed_during_planning": False,
        },
        "finite_generic_meta_grammar": {
            "types": list(GENERIC_TYPES),
            "opcodes": generic_opcode_documents_v1(),
            "domain_named_primitive_count": 0,
            "lmb_named_primitive_count": 0,
            "registered_template_opcodes": ["T00", "T01"],
            "maximum_ast_depth": 5,
            "maximum_instruction_count": 16,
            "open_ended_program_invention_claimed": False,
        },
        "selection_rule": {
            "primary": "EXACT_RAW_TRANSITION_RESIDUAL_COUNT",
            "secondary": "TYPED_AST_MDL_SIZE",
            "tertiary": "TEMPLATE_OPCODE",
            "required_unique_minimum": True,
            "dependency_support_rule": (
                "DELETE_EACH_COMPILED_INPUT_REGISTER_AND_REQUIRE_COUNTEREXAMPLE"
            ),
            "semantic_support_names_predeclared": [],
        },
        "lmb_workload": {
            "source_specification": LMB_SOURCE_SPEC,
            "source_seeds": list(LMB_SOURCE_SEEDS),
            "source_policy": (
                "WITNESS_BLIND_MIN_LEGAL_THEN_UNSEEN_ACTION_FIELD_COVERAGE"
            ),
            "maximum_source_transition_labels": LMB_MAX_SOURCE_LABELS,
            "target_specification": LMB_TARGET_SPEC,
            "target_seeds": list(LMB_TARGET_SEEDS),
            "state_column_order_per_occurrence_permuted": True,
            "action_field_order_per_occurrence_permuted": True,
            "action_and_state_token_namespaces_per_occurrence_disjoint": True,
            "generation_witness_access_allowed": False,
        },
        "stochastic_partial_workload": {
            "source_specification": ROUTING_SOURCE_SPEC,
            "source_seeds": list(ROUTING_SOURCE_SEEDS),
            "source_episodes_per_seed": ROUTING_SOURCE_EPISODES_PER_SEED,
            "source_policy": "WITNESS_BLIND_LEAST_OBSERVED_ANONYMOUS_CLASS",
            "maximum_source_transition_labels": ROUTING_MAX_SOURCE_LABELS,
            "target_specification": ROUTING_TARGET_SPEC,
            "target_seeds": list(ROUTING_TARGET_SEEDS),
            "probability_source_rule_available_to_synthesizer": False,
            "required_partial_model": (
                "OBSERVED_FINITE_SUPPORT_WITH_EMPIRICAL_RATIONAL_AND_UNIT_INTERVAL"
            ),
            "exact_probability_authority_claimed": False,
            "planner_rule": "ROBUST_WORST_SUPPORT_RECEDING_PLAN",
        },
        "planning_and_certificate_protocol": {
            "arms": list(ARMS),
            "receding_horizon": RECEDING_HORIZON,
            "planner_consumes_compiled_bytecode_only": True,
            "adapter_provided_abstract_state_forbidden": True,
            "kernel_transition_during_planning_forbidden": True,
            "local_ground_distinction_requires_failed_certificate": True,
            "successful_certificate_forbids_local_ground_label": True,
            "successful_execution_observation_not_retained_as_acquisition_label": True,
            "strict_control_key": "EXACT_OPAQUE_STATE_ACTION_CONTEXT",
            "maximum_target_local_labels_per_episode": (
                MAX_TARGET_LOCAL_LABELS_PER_EPISODE
            ),
        },
        "sample_tax_protocol": {
            "matched_arms": list(ARMS),
            "source_labels_charged_to_meta_prior_arm": True,
            "offline_source_labels": "SEPARATE_AXIS",
            "target_local_labels": "SEPARATE_AXIS",
            "execution_steps": "SEPARATE_AXIS",
            "synthesis_compute": "SEPARATE_AXIS",
            "planning_compute": "SEPARATE_AXIS",
            "certificate_compute": "SEPARATE_AXIS",
            "diagnostic_label_break_even_may_be_reported": True,
            "official_N_break_even_must_remain_null": True,
            "positive_registered_result_requires_total_meta_labels_below_control": True,
            "broad_cross_domain_sample_efficiency_claimed": False,
        },
        "strict_ood_control": {
            "schema_id": "OPAQUE_REAL_VECTOR_CONTINUOUS_CONTROL_V1",
            "state_scalar_type": "REAL",
            "action_field_scalar_type": "REAL",
            "registered_integer_grammar_compatible": False,
            "prior_access_allowed": False,
            "transition_outcome_access_allowed": False,
            "environment_step_allowed": False,
            "expected_decision": "OOD_SCHEMA_REJECTED_NO_TRANSFER",
        },
        "accounting_axes": {
            "lmb_source_labels": "labels",
            "stochastic_source_labels": "labels",
            "lmb_target_local_labels": "labels",
            "stochastic_target_local_labels": "labels",
            "execution_environment_steps": "steps",
            "synthesis_compute_events": "compute events",
            "planning_compute_events": "compute events",
            "certificate_compute_events": "compute events",
            "ood_schema_compute_events": "compute events",
            "peak_program_cache_entries": "peak entries",
            "labels_steps_compute_and_peak_may_not_be_collapsed": True,
        },
        "required_positive_conditions": [
            "ONE_GENERIC_SYNTHESIZER_SELECTS_DISTINCT_PROGRAMS_IN_TWO_DOMAINS",
            "NO_LMB_NAMED_PRIMITIVE_APPEARS_IN_COMPILED_BYTECODE",
            "LMB_PLANNER_CONSUMES_ONLY_COMPILED_VM_STATE_AND_ACTION_CATALOGUE",
            "STOCHASTIC_PROGRAM_RETAINS_PARTIAL_NOT_EXACT_PROBABILITY_DYNAMICS",
            "ALL_LOCAL_GROUND_LABELS_FOLLOW_FAILED_CERTIFICATES",
            "META_PRIOR_TOTAL_LABELS_BEAT_STRICT_CONTROL_ON_REGISTERED_CAMPAIGN",
            "STRICT_INCOMPATIBLE_SCHEMA_RECEIVES_NO_TRANSFER_AND_NO_OUTCOME",
            "PRODUCER_FREE_VERIFIER_RECONSTRUCTS_PROGRAMS_PLANS_AND_ACCOUNTING",
        ],
        "outcome_fields_present": False,
        "raw_transition_archive_materialized": False,
        "program_selection_executed": False,
        "target_planning_or_execution_performed": False,
        "sample_tax_result_observed": False,
        "broad_world_model_synthesis_claimed": False,
        "exact_stochastic_probability_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "generic_bytecode_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class GenericBytecodePreregistrationV47:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V47 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V47 preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "generic_bytecode_preregistration_id"
        }
        if (
            document.get("generic_bytecode_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V47 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError("V47 preregistration is not an object")
        return value


def freeze_generic_bytecode_preregistration_v47() -> GenericBytecodePreregistrationV47:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["generic_bytecode_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V47 preregistration changed")
    return GenericBytecodePreregistrationV47(_ISSUER, raw, identity)


def verify_generic_bytecode_preregistration_v47(
    value: GenericBytecodePreregistrationV47,
) -> GenericBytecodePreregistrationV47:
    if type(value) is not GenericBytecodePreregistrationV47:
        _fail("V47 preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("V47 preregistration semantics changed")
    return value


__all__ = (
    "ACTION_FIELD_SALT",
    "ARMS",
    "BOUND_SOURCE_PATHS",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FLAT_LAYOUT_SALT",
    "FUTURE_DOMAINS",
    "GenericBytecodePreregistrationV47",
    "LMB_MAX_SOURCE_LABELS",
    "LMB_SOURCE_SEEDS",
    "LMB_SOURCE_SPEC",
    "LMB_TARGET_SEEDS",
    "LMB_TARGET_SPEC",
    "MAX_TARGET_LOCAL_LABELS_PER_EPISODE",
    "PREREGISTRATION_ID",
    "PROFILE_KEY",
    "RECEDING_HORIZON",
    "ROUTING_MAX_SOURCE_LABELS",
    "ROUTING_SOURCE_EPISODES_PER_SEED",
    "ROUTING_SOURCE_SEEDS",
    "ROUTING_SOURCE_SPEC",
    "ROUTING_TARGET_SEEDS",
    "ROUTING_TARGET_SPEC",
    "SCHEMA_VERSION",
    "SOURCE_ROOT",
    "TOKEN_SALT",
    "freeze_generic_bytecode_preregistration_v47",
    "verify_generic_bytecode_preregistration_v47",
)
