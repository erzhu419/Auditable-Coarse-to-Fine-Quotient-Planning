"""Outcome-free V45 registration for anonymous-descriptor LMB synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_CAMPAIGN_V45_DOMAIN,
    CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_EPISODE_V45_DOMAIN,
    CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_OBSERVATION_V45_DOMAIN,
    CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_PREREGISTRATION_V45_DOMAIN,
    CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_PROGRAM_V45_DOMAIN,
    CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_VERIFICATION_V45_DOMAIN,
    CONSTRUCTION_K7_LMB_DEPENDENCY_DERIVED_DISTINCTION_V45_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "45.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.209"
PROFILE_KEY = "construction_k7_lmb_anonymous_descriptor_synthesis_v45"
PREREGISTRATION_ID = "396734cb88018922b3ba706fd05aa009d676b9cf3f6228d23b2add3cab1b8eca"
EXPECTED_CANONICAL_BYTE_COUNT = 7_245
EXPECTED_CANONICAL_SHA256 = "b7800bb6c7768439e63fac6c3afce9e7988b51e9883e053e348dc7d43a321a3e"

V41_CAMPAIGN_ID = "1a576e0c8b34f52050f77366ec7ac39dab58bddd53ec91180ed9d6c092072732"
V41_VERIFICATION_ID = "a05a6b795a15a8dda596b148efe52b374cc687f125b1c14731466f83aa791396"
V42_CAMPAIGN_ID = "c8adada792b7dacfce816bf1916457329643b61e8915f285472708c6c6bd359b"
V42_VERIFICATION_ID = "af44dabf2f2f7b05767343c2d8306165cfe828ff8180efe7d409e0baa3315da0"
V43_CAMPAIGN_ID = "d435246de035efd4081922b8d6995f1dceb36216bf08cb5766a76ed5dfdbe00d"
V43_VERIFICATION_ID = "d3e7426521c663ccef51a4da6bb30112c37fc7d37f743050d27942b578a76a51"
V44_PREREGISTRATION_ID = "6876b931a99f5d7da01e32df15788197b5acd6d42b625828d3daed1db3243f64"
V44_FAILURE_ID = "f98b1fb28efcb7f5f311f04d6c16bf283cbe521a2cf1f0cb4bc4fe3057d19bcd"
V44R1_PREREGISTRATION_ID = "ab2d00d7fb7ad79ee73b9f1ed74595e582b5790de2d3d45dbcf051901f79236f"
V44R1_CAMPAIGN_ID = "3fdf113eb789fca2ceb033a430cc6491fc2ffc2a7cc0408e2929aeff6b414b35"
V44R1_VERIFICATION_ID = "3c7f833428bcc92f4f3003caea638b1dd81a97a94f7ff1af8b817a8f3e8e3be1"

SOURCE_SPEC = {"tile_count": 18, "type_count": 6, "capacity": 6, "max_layers": 4}
PROJECTION_ACQUISITION_SEEDS = (450101, 450102, 450103, 450104)
SOURCE_CONFIRMATION_SEED = 450201
MAX_PROJECTION_ACQUISITION_LABELS = 60
MIN_DISTINCT_CHANGED_COORDINATE_TOKENS = 3
TARGET_SPEC = {"tile_count": 21, "type_count": 7, "capacity": 7, "max_layers": 5}
HELDOUT_SEEDS = (451301, 451302, 451303, 451304, 451305, 451306)
RECEDING_HORIZON = 4
MAX_TARGET_LOCAL_LABELS_PER_EPISODE = 42
ARMS = ("DERIVED_DEPENDENCY_SIGNATURE", "STRICT_NO_PRIOR_CONTEXT_TABLE")
DESCRIPTOR_FIELD_COUNT = 3
DESCRIPTOR_TOKEN_SALT = 0x45A1
COORDINATE_ORDER_SALT = 0x45B2
OPAQUE_FIELD_SALT = 0x45C3

TYPED_RELATION_GRAMMAR = {
    "types": [
        "ATOM",
        "BOOL",
        "COUNT_VECTOR",
        "DESCRIPTOR_VECTOR",
        "INDEX",
        "NAT",
        "STATUS",
        "TILE_ID",
        "TILE_SET",
        "TOKEN_VECTOR",
    ],
    "atoms": [
        ["PRE_OBSERVED_COUNT_VECTOR", "COUNT_VECTOR"],
        ["POST_OBSERVED_COUNT_VECTOR", "COUNT_VECTOR"],
        ["ACTION_DESCRIPTOR_FIELDS", "DESCRIPTOR_VECTOR"],
        ["COORDINATE_TOKENS", "TOKEN_VECTOR"],
        ["ACTION_ID", "TILE_ID"],
        ["PRE_REMOVED_SET", "TILE_SET"],
        ["POST_REMOVED_SET", "TILE_SET"],
        ["INSTANCE_CAPACITY", "NAT"],
        ["POST_STATUS", "STATUS"],
    ],
    "constructors": [
        ["DESCRIPTOR_FIELD", ["DESCRIPTOR_VECTOR", "INDEX"], "ATOM"],
        ["UNIQUE_EQUALITY_JOIN_INDEX", ["TOKEN_VECTOR", "ATOM"], "INDEX"],
        ["UNIQUE_DIFF_INDEX", ["COUNT_VECTOR", "COUNT_VECTOR"], "INDEX"],
        ["VECTOR_AT", ["COUNT_VECTOR", "INDEX"], "NAT"],
        ["VECTOR_UPDATE", ["COUNT_VECTOR", "INDEX", "NAT"], "COUNT_VECTOR"],
        ["SUM_VECTOR", ["COUNT_VECTOR"], "NAT"],
        ["ADD_ONE", ["NAT"], "NAT"],
        ["SUBTRACT", ["NAT", "NAT"], "NAT"],
        ["MODULO", ["NAT", "NAT"], "NAT"],
        ["SET_INSERT", ["TILE_SET", "TILE_ID"], "TILE_SET"],
        ["GREATER_THAN", ["NAT", "NAT"], "BOOL"],
        ["ALL_REGISTERED_TILES_REMOVED", ["TILE_SET"], "BOOL"],
        ["IF_THEN_ELSE", ["BOOL", "STATUS", "STATUS"], "STATUS"],
    ],
    "descriptor_field_indices_are_the_only_projection_candidates": [0, 1, 2],
    "descriptor_field_semantic_names_exposed": False,
    "named_action_class_atom_present": False,
    "predeclared_projection_field": None,
}

DEPENDENCY_MINIMIZATION = {
    "initial_roots": "INPUTS_TO_JOIN_MODULO_COMPARISON_AND_TERMINAL_BRANCH_NODES",
    "comparison_normalization": "REPLACE_CAPACITY_AND_PRE_LOAD_WITH_CAPACITY_MINUS_PRE_LOAD",
    "terminal_normalization": "REPLACE_UPDATED_SET_WITH_WILL_REMOVE_LAST_TILE",
    "deletion_rule": "REMOVE_FEATURE_EXACTLY_DERIVABLE_FROM_RETAINED_FEATURES",
    "tie_break": "LEXICOGRAPHIC_CANONICAL_TYPED_AST_BYTES",
    "support_signature_fields_predeclared": [],
    "expected_support_signature_predeclared": False,
}

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_PREREGISTRATION_V45_DOMAIN,
    "observation": CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_OBSERVATION_V45_DOMAIN,
    "program": CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_PROGRAM_V45_DOMAIN,
    "distinction": CONSTRUCTION_K7_LMB_DEPENDENCY_DERIVED_DISTINCTION_V45_DOMAIN,
    "episode": CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_EPISODE_V45_DOMAIN,
    "campaign": CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_CAMPAIGN_V45_DOMAIN,
    "verification": CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_VERIFICATION_V45_DOMAIN,
}


class ConstructionK7LMBAnonymousDescriptorPreregistrationV45Error(ValueError):
    """A predecessor, anonymous relation grammar, workload, or claim changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LMBAnonymousDescriptorPreregistrationV45Error(message)


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.lmb_anonymous_descriptor_preregistration.v45",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "v41_campaign_id": V41_CAMPAIGN_ID,
            "v41_verification_id": V41_VERIFICATION_ID,
            "v42_campaign_id": V42_CAMPAIGN_ID,
            "v42_verification_id": V42_VERIFICATION_ID,
            "v43_campaign_id": V43_CAMPAIGN_ID,
            "v43_verification_id": V43_VERIFICATION_ID,
            "v44_preregistration_id": V44_PREREGISTRATION_ID,
            "v44_failure_id": V44_FAILURE_ID,
            "v44r1_preregistration_id": V44R1_PREREGISTRATION_ID,
            "v44r1_campaign_id": V44R1_CAMPAIGN_ID,
            "v44r1_verification_id": V44R1_VERIFICATION_ID,
            "all_predecessor_identities_preserved": True,
        },
        "anonymous_adapter_protocol": {
            "descriptor_field_count": DESCRIPTOR_FIELD_COUNT,
            "every_descriptor_field_type": "ATOM",
            "descriptor_field_names": ["F0", "F1", "F2"],
            "descriptor_field_semantic_names_exposed_to_synthesizer": False,
            "coordinate_tokens_published_in_observed_vector_order": True,
            "descriptor_token_salt": DESCRIPTOR_TOKEN_SALT,
            "coordinate_order_salt": COORDINATE_ORDER_SALT,
            "opaque_field_salt": OPAQUE_FIELD_SALT,
            "descriptor_values_permuted_by_occurrence": True,
            "coordinate_order_permuted_by_occurrence": True,
            "source_and_target_descriptor_value_namespaces_disjoint": True,
        },
        "source_projection_acquisition": {
            "instance_specification": SOURCE_SPEC,
            "ordered_seeds": list(PROJECTION_ACQUISITION_SEEDS),
            "action_policy": "MIN_LEGAL_ACTION_ID",
            "action_policy_reads_descriptor_fields": False,
            "action_policy_reads_transition_outcome_before_selection": False,
            "stop_when": {
                "one_projection_field_satisfies_all_rows": True,
                "minimum_distinct_changed_coordinate_tokens": (
                    MIN_DISTINCT_CHANGED_COORDINATE_TOKENS
                ),
            },
            "maximum_transition_labels": MAX_PROJECTION_ACQUISITION_LABELS,
            "source_generation_witness_access_allowed": False,
            "hidden_solution_sequence_access_allowed": False,
        },
        "source_program_confirmation": {
            "fresh_seed": SOURCE_CONFIRMATION_SEED,
            "policy": "DERIVED_PROJECTION_PLUS_FROZEN_V44R1_PROGRAM_PLAN",
            "kernel_step_during_planning_allowed": False,
            "source_generation_witness_access_allowed": False,
        },
        "typed_relation_grammar": TYPED_RELATION_GRAMMAR,
        "dependency_minimization": DEPENDENCY_MINIMIZATION,
        "heldout_target": {
            "seeds": list(HELDOUT_SEEDS),
            "instance_specification": TARGET_SPEC,
            "tile_count_changed": True,
            "type_count_changed": True,
            "capacity_changed": True,
            "layer_depth_changed": True,
            "descriptor_values_and_coordinate_order_changed": True,
            "generation_witness_access_allowed": False,
            "target_outcome_observed_before_registration": False,
        },
        "planning_and_recovery_protocol": {
            "arms": list(ARMS),
            "receding_horizon": RECEDING_HORIZON,
            "kernel_step_during_planning_allowed": False,
            "derived_support_signature_required": True,
            "hand_written_structural_support_key_present": False,
            "strict_control_support_key": "EXACT_STATE_ACTION_CONTEXT",
            "ground_distinction_requires_prior_failed_certificate": True,
            "successful_certificate_forbids_ground_acquisition": True,
            "maximum_target_local_labels_per_episode": MAX_TARGET_LOCAL_LABELS_PER_EPISODE,
        },
        "accounting_axes": {
            "source_projection_labels": "labels",
            "source_confirmation_labels": "labels",
            "target_local_distinction_labels": "labels",
            "execution_environment_steps": "steps",
            "projection_program_and_dependency_derivation": "compute events",
            "source_and_target_abstract_transition_evaluations": "compute events",
            "certificate_evaluations": "compute events",
            "peak_dynamic_program_cache_entries": "peak entries",
            "labels_steps_and_compute_may_not_be_collapsed": True,
        },
        "required_positive_conditions": [
            "ONE_ANONYMOUS_DESCRIPTOR_FIELD_IS_UNIQUELY_SELECTED_BY_EQUALITY_JOIN",
            "DESCRIPTOR_VALUES_AND_COORDINATE_ORDER_CHANGE_ON_HELDOUT_TARGETS",
            "TRANSITION_PROGRAM_USES_DERIVED_PROJECTION",
            "SUPPORT_SIGNATURE_IS_DEPENDENCY_DERIVED_NOT_PREDECLARED",
            "ALL_HELDOUT_EPISODES_COMPLETE_IN_BOTH_ARMS",
            "EVERY_TARGET_LABEL_FOLLOWS_FAILED_CERTIFICATE",
            "DERIVED_SIGNATURE_ARM_USES_FEWER_LABELS_THAN_STRICT_CONTROL",
            "PRODUCER_FREE_VERIFIER_REDERIVES_PROJECTION_SIGNATURE_AND_PLANS",
        ],
        "outcome_fields_present": False,
        "campaign_executed": False,
        "named_action_class_scaffold_present": False,
        "open_ended_descriptor_or_grammar_invention_claimed": False,
        "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
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
        "lmb_anonymous_descriptor_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LMBAnonymousDescriptorPreregistrationV45:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V45 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V45 preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "lmb_anonymous_descriptor_preregistration_id"
        }
        if (
            document.get("lmb_anonymous_descriptor_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V45 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError("V45 preregistration is not an object")
        return value


def freeze_lmb_anonymous_descriptor_preregistration_v45() -> (
    LMBAnonymousDescriptorPreregistrationV45
):
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["lmb_anonymous_descriptor_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V45 preregistration changed")
    return LMBAnonymousDescriptorPreregistrationV45(_ISSUER, raw, identity)


def verify_lmb_anonymous_descriptor_preregistration_v45(
    value: LMBAnonymousDescriptorPreregistrationV45,
) -> LMBAnonymousDescriptorPreregistrationV45:
    if type(value) is not LMBAnonymousDescriptorPreregistrationV45:
        _fail("V45 preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("V45 preregistration semantics changed")
    return value


__all__ = (
    "ARMS",
    "COORDINATE_ORDER_SALT",
    "DEPENDENCY_MINIMIZATION",
    "DESCRIPTOR_FIELD_COUNT",
    "DESCRIPTOR_TOKEN_SALT",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "HELDOUT_SEEDS",
    "LMBAnonymousDescriptorPreregistrationV45",
    "OPAQUE_FIELD_SALT",
    "PREREGISTRATION_ID",
    "PROJECTION_ACQUISITION_SEEDS",
    "RECEDING_HORIZON",
    "SOURCE_CONFIRMATION_SEED",
    "SOURCE_SPEC",
    "TARGET_SPEC",
    "TYPED_RELATION_GRAMMAR",
    "freeze_lmb_anonymous_descriptor_preregistration_v45",
    "verify_lmb_anonymous_descriptor_preregistration_v45",
)
