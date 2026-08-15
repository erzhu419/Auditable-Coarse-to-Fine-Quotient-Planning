"""Outcome-free V47r1 successor after the frozen target-register failure."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp.construction_k7_generic_bytecode_failure_v47 import FAILURE_ID
from acfqp.construction_k7_generic_bytecode_preregistration_v47 import (
    PREREGISTRATION_ID as FAILED_PREREGISTRATION_ID,
)
from acfqp.generic_bytecode_world_model_v2 import (
    GENERIC_TYPES,
    generic_opcode_documents_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_GENERIC_BYTECODE_PREREGISTRATION_V47R1_DOMAIN,
    CONSTRUCTION_K7_GENERIC_BYTECODE_PROGRAM_V47R1_DOMAIN,
    CONSTRUCTION_K7_GENERIC_CROSS_DOMAIN_CAMPAIGN_V47R1_DOMAIN,
    CONSTRUCTION_K7_GENERIC_CROSS_DOMAIN_VERIFICATION_V47R1_DOMAIN,
    CONSTRUCTION_K7_GENERIC_LOCAL_DISTINCTION_V47R1_DOMAIN,
    CONSTRUCTION_K7_GENERIC_RAW_OBSERVATION_V47R1_DOMAIN,
    CONSTRUCTION_K7_GENERIC_RECEDING_EPISODE_V47R1_DOMAIN,
    CONSTRUCTION_K7_GENERIC_SAMPLE_TAX_V47R1_DOMAIN,
    CONSTRUCTION_K7_GENERIC_STOCHASTIC_PARTIAL_V47R1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "47.1.0"
PROPOSED_CONTRACT_VERSION = "2.0.213"
PROFILE_KEY = "construction_k7_generic_bytecode_cross_domain_v47r1"
PREREGISTRATION_ID = "2ad2e7a2409ed1d025b9659973115e8489266bb196db049a6340ba1f22e32ae8"
EXPECTED_CANONICAL_BYTE_COUNT = 6108
EXPECTED_CANONICAL_SHA256 = "22f78058a5f698954eee2893e34b5698eac4bda9e0fedb8ae8592812f42db1b7"

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/generic_bytecode_world_model_v1.py",
    "src/acfqp/generic_bytecode_world_model_v2.py",
    "src/acfqp/domains/matching_buffer.py",
    "src/acfqp/domains/stochastic_routing.py",
)

LMB_SOURCE_SPEC = {"tile_count": 24, "type_count": 8, "capacity": 8, "max_layers": 6}
LMB_SOURCE_SEEDS = (474101, 474102, 474103, 474104)
LMB_TARGET_SPEC = {"tile_count": 27, "type_count": 9, "capacity": 9, "max_layers": 7}
LMB_TARGET_SEEDS = (475301, 475302, 475303, 475304, 475305, 475306)
LMB_MAX_SOURCE_LABELS = 256

ROUTING_SOURCE_SPEC = {"node_count": 9, "capacity": 12}
ROUTING_SOURCE_SEEDS = (476101, 476102, 476103, 476104)
ROUTING_SOURCE_EPISODES_PER_SEED = 8
ROUTING_TARGET_SPEC = {"node_count": 11, "capacity": 15}
ROUTING_TARGET_SEEDS = (477301, 477302, 477303, 477304, 477305, 477306, 477307, 477308)
ROUTING_MAX_SOURCE_LABELS = 256

ARMS = ("STRUCTURAL_META_PRIOR", "STRICT_EXACT_CONTEXT")
RECEDING_HORIZON = 4
FLAT_LAYOUT_SALT = 0x471A
ACTION_FIELD_SALT = 0x471B
TOKEN_SALT = 0x471C

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_GENERIC_BYTECODE_PREREGISTRATION_V47R1_DOMAIN,
    "observation": CONSTRUCTION_K7_GENERIC_RAW_OBSERVATION_V47R1_DOMAIN,
    "program": CONSTRUCTION_K7_GENERIC_BYTECODE_PROGRAM_V47R1_DOMAIN,
    "distinction": CONSTRUCTION_K7_GENERIC_LOCAL_DISTINCTION_V47R1_DOMAIN,
    "episode": CONSTRUCTION_K7_GENERIC_RECEDING_EPISODE_V47R1_DOMAIN,
    "stochastic": CONSTRUCTION_K7_GENERIC_STOCHASTIC_PARTIAL_V47R1_DOMAIN,
    "sample_tax": CONSTRUCTION_K7_GENERIC_SAMPLE_TAX_V47R1_DOMAIN,
    "campaign": CONSTRUCTION_K7_GENERIC_CROSS_DOMAIN_CAMPAIGN_V47R1_DOMAIN,
    "verification": CONSTRUCTION_K7_GENERIC_CROSS_DOMAIN_VERIFICATION_V47R1_DOMAIN,
}


class ConstructionK7GenericBytecodeSuccessorPreregistrationV47R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7GenericBytecodeSuccessorPreregistrationV47R1Error(message)


def _source_facts() -> list[dict[str, Any]]:
    result = []
    for relative in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        result.append({"relative_path": relative, "byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    return result


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.generic_bytecode_successor_preregistration.v47r1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_failed_predecessor": {
            "failed_preregistration_id": FAILED_PREREGISTRATION_ID,
            "failure_id": FAILURE_ID,
            "failed_identity_reused": False,
            "all_failed_evidence_preserved": True,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "frozen_before_fresh_v47r1_outcomes": True,
        },
        "raw_interface": {
            "state": "OPAQUE_ORDERED_INTEGER_VECTOR",
            "action": "OPAQUE_KEY_PLUS_ANONYMOUS_INTEGER_FIELDS",
            "observation": ["PRE_VECTOR", "LEGAL_KEYS_BEFORE", "ACTION_KEY_AND_FIELDS", "POST_VECTOR", "LEGAL_KEYS_AFTER", "OPTIONAL_TAPE_SHA256"],
            "domain_name_available_to_synthesizer": False,
            "state_column_role_available_to_synthesizer": False,
            "action_field_role_available_to_synthesizer": False,
            "adapter_provided_abstract_state_present": False,
        },
        "generic_engine": {
            "types": list(GENERIC_TYPES),
            "opcodes": generic_opcode_documents_v1(),
            "templates": ["T00", "T01"],
            "selection": "MIN_EXACT_RESIDUAL_THEN_TYPED_MDL_THEN_OPCODE",
            "domain_named_primitive_count": 0,
            "lmb_named_primitive_count": 0,
            "complete_target_state_register_binding_required": True,
            "public_anonymous_vm_executor_required": True,
            "support_signature": "EXACT_COMPILED_REGISTER_DELETION",
            "semantic_support_names_predeclared": [],
        },
        "fresh_workloads": {
            "lmb": {
                "source_spec": LMB_SOURCE_SPEC,
                "source_seeds": list(LMB_SOURCE_SEEDS),
                "target_spec": LMB_TARGET_SPEC,
                "target_seeds": list(LMB_TARGET_SEEDS),
                "maximum_source_labels": LMB_MAX_SOURCE_LABELS,
                "source_policy": "WITNESS_BLIND_ANONYMOUS_FIELD_COVERAGE",
            },
            "stochastic_partial": {
                "source_spec": ROUTING_SOURCE_SPEC,
                "source_seeds": list(ROUTING_SOURCE_SEEDS),
                "source_episodes_per_seed": ROUTING_SOURCE_EPISODES_PER_SEED,
                "target_spec": ROUTING_TARGET_SPEC,
                "target_seeds": list(ROUTING_TARGET_SEEDS),
                "maximum_source_labels": ROUTING_MAX_SOURCE_LABELS,
                "source_policy": "WITNESS_BLIND_LEAST_OBSERVED_ANONYMOUS_FIELD_TUPLE",
                "exact_probability_authority_claimed": False,
                "partial_model": "OBSERVED_SUPPORT_EMPIRICAL_RATIONAL_PLUS_UNIT_INTERVAL",
            },
            "all_seed_identities_fresh_after_v47_failure": True,
        },
        "protocol": {
            "arms": list(ARMS),
            "receding_horizon": RECEDING_HORIZON,
            "planner_consumes_compiled_world_model_only": True,
            "kernel_transition_during_planning_forbidden_for_meta_arm": True,
            "local_ground_label_only_after_certificate_failure": True,
            "strict_control": "GROUND_QUERY_EACH_NEW_EXACT_STATE_ACTION_CONTEXT",
            "strict_ood_schema": "OPAQUE_CONTINUOUS_REAL_VECTOR",
            "strict_ood_prior_access": False,
            "strict_ood_outcome_access": False,
        },
        "accounting": {
            "offline_source_labels": "SEPARATE_AXIS",
            "target_local_labels": "SEPARATE_AXIS",
            "execution_steps": "SEPARATE_AXIS",
            "synthesis_compute": "SEPARATE_AXIS",
            "planning_compute": "SEPARATE_AXIS",
            "certificate_compute": "SEPARATE_AXIS",
            "peak_cache": "SEPARATE_AXIS",
            "positive_sample_tax_condition": "SOURCE_PLUS_META_TARGET_LABELS_LT_STRICT_TARGET_LABELS",
            "diagnostic_break_even_only": True,
        },
        "required_positive_conditions": [
            "TWO_DISTINCT_PROGRAMS_SYNTHESIZED_BY_ONE_GENERIC_ENGINE",
            "PLANNER_USES_COMPILED_VM_NOT_TYPED_ADAPTER_ABSTRACTION",
            "PARTIAL_DYNAMICS_RETAIN_SUPPORT_WITHOUT_EXACT_PROBABILITY_AUTHORITY",
            "STRICT_OOD_NO_TRANSFER_NO_OUTCOME",
            "ALL_LOCAL_LABELS_FOLLOW_FAILED_CERTIFICATES",
            "REGISTERED_META_LABEL_TOTAL_BEATS_STRICT_CONTROL",
            "PRODUCER_FREE_RECONSTRUCTION_PASSES",
        ],
        "outcome_fields_present": False,
        "fresh_outcome_execution_performed": False,
        "campaign_artifact_issued": False,
        "sample_tax_result_issued": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {**payload, "generic_bytecode_successor_preregistration_id": content_id(FUTURE_DOMAINS["preregistration"], payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class GenericBytecodeSuccessorPreregistrationV47R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V47r1 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V47r1 preregistration bytes changed")
        payload = {key: value for key, value in document.items() if key != "generic_bytecode_successor_preregistration_id"}
        if document.get("generic_bytecode_successor_preregistration_id") != self.preregistration_id or content_id(FUTURE_DOMAINS["preregistration"], payload) != self.preregistration_id:
            _fail("V47r1 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError
        return value


def freeze_generic_bytecode_successor_preregistration_v47r1() -> GenericBytecodeSuccessorPreregistrationV47R1:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["generic_bytecode_successor_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (identity != PREREGISTRATION_ID or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256):
        _fail("frozen V47r1 preregistration changed")
    return GenericBytecodeSuccessorPreregistrationV47R1(_ISSUER, raw, identity)


def verify_generic_bytecode_successor_preregistration_v47r1(value: GenericBytecodeSuccessorPreregistrationV47R1) -> GenericBytecodeSuccessorPreregistrationV47R1:
    if type(value) is not GenericBytecodeSuccessorPreregistrationV47R1:
        _fail("V47r1 preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("V47r1 preregistration semantics changed")
    return value


__all__ = (
    "ACTION_FIELD_SALT", "ARMS", "BOUND_SOURCE_PATHS", "EXPECTED_CANONICAL_BYTE_COUNT", "EXPECTED_CANONICAL_SHA256", "FLAT_LAYOUT_SALT", "FUTURE_DOMAINS", "LMB_MAX_SOURCE_LABELS", "LMB_SOURCE_SEEDS", "LMB_SOURCE_SPEC", "LMB_TARGET_SEEDS", "LMB_TARGET_SPEC", "PREREGISTRATION_ID", "RECEDING_HORIZON", "ROUTING_MAX_SOURCE_LABELS", "ROUTING_SOURCE_EPISODES_PER_SEED", "ROUTING_SOURCE_SEEDS", "ROUTING_SOURCE_SPEC", "ROUTING_TARGET_SEEDS", "ROUTING_TARGET_SPEC", "SOURCE_ROOT", "TOKEN_SALT", "freeze_generic_bytecode_successor_preregistration_v47r1", "verify_generic_bytecode_successor_preregistration_v47r1",
)
