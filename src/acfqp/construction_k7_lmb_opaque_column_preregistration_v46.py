"""Outcome-free V46 registration for opaque-column world-model synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_LMB_COLUMN_FACTORIZATION_V46_DOMAIN,
    CONSTRUCTION_K7_LMB_FACTORIZED_DISTINCTION_V46_DOMAIN,
    CONSTRUCTION_K7_LMB_FACTORIZED_EPISODE_V46_DOMAIN,
    CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_CAMPAIGN_V46_DOMAIN,
    CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_OBSERVATION_V46_DOMAIN,
    CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_PREREGISTRATION_V46_DOMAIN,
    CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_VERIFICATION_V46_DOMAIN,
    CONSTRUCTION_K7_LMB_OPAQUE_SCHEMA_OOD_REJECTION_V46_DOMAIN,
    CONSTRUCTION_K7_LMB_RELATION_PROGRAM_V46_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "46.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.210"
PROFILE_KEY = "construction_k7_lmb_opaque_column_synthesis_v46"
PREREGISTRATION_ID = "8f5fa0557c5b04073e7c24f1d3f962a673b029d6f18905c5a52600bf5093f46d"
EXPECTED_CANONICAL_BYTE_COUNT = 8_910
EXPECTED_CANONICAL_SHA256 = "b124d259ff035532c937dda557167004071922c9664ef7be1c5180f00233896a"

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
V45_PREREGISTRATION_ID = "396734cb88018922b3ba706fd05aa009d676b9cf3f6228d23b2add3cab1b8eca"
V45_CAMPAIGN_ID = "e1b034e577463ea1f91380bb2b85b97c130af89886ce62638762e65a4dab1413"
V45_VERIFICATION_ID = "3b6eaf9419890e498fce52b86f4a23b00b59e1bb195470718342401f4aab48c0"

SOURCE_SPEC = {"tile_count": 21, "type_count": 7, "capacity": 7, "max_layers": 5}
SOURCE_ACQUISITION_SEEDS = (460101, 460102, 460103, 460104)
SOURCE_CONFIRMATION_SEED = 460201
MAX_SOURCE_ACQUISITION_LABELS = 80
MIN_DYNAMIC_COLUMN_COUNT = 4
TARGET_SPEC = {"tile_count": 24, "type_count": 8, "capacity": 8, "max_layers": 6}
HELDOUT_SEEDS = (461301, 461302, 461303, 461304, 461305, 461306)
RECEDING_HORIZON = 4
MAX_TARGET_LOCAL_LABELS_PER_EPISODE = 48
ARMS = ("DERIVED_FACTORIZED_RELATION", "STRICT_NO_PRIOR_CONTEXT_TABLE")
STATE_EXTRA_COLUMN_COUNT = 3
ACTION_METADATA_FIELD_COUNT = 3
FLAT_COLUMN_ORDER_SALT = 0x46A1
ACTION_VALUE_SALT = 0x46B2
STATUS_ENCODING_SALT = 0x46C3

GENERIC_RELATION_META_GRAMMAR = {
    "types": [
        "ACTION_ID",
        "ATOM",
        "BOOL",
        "COLUMN_INDEX",
        "COLUMN_PARTITION",
        "COLUMN_VECTOR",
        "FIELD_INDEX",
        "FIELD_PARTITION",
        "NAT",
        "RELATION",
        "SCALAR",
    ],
    "atoms": [
        ["PRE_COLUMNS", "COLUMN_VECTOR"],
        ["POST_COLUMNS", "COLUMN_VECTOR"],
        ["ACTION_METADATA", "COLUMN_VECTOR"],
        ["ACTION_ID", "ACTION_ID"],
        ["INSTANCE_SCALARS", "COLUMN_VECTOR"],
    ],
    "constructors": [
        ["CHANGED_COLUMN_SET", ["COLUMN_VECTOR", "COLUMN_VECTOR"], "COLUMN_PARTITION"],
        ["FIELD_VALUE_PARTITION", ["COLUMN_VECTOR", "FIELD_INDEX"], "FIELD_PARTITION"],
        ["PARTITION_TO_CHANGED_COLUMN_RELATION", ["FIELD_PARTITION", "COLUMN_PARTITION"], "RELATION"],
        ["UNCHANGED_OR_CYCLIC_INCREMENT", ["SCALAR", "SCALAR", "NAT"], "BOOL"],
        ["MONOTONE_SINGLE_BIT_INSERTION", ["SCALAR", "SCALAR", "ACTION_ID"], "BOOL"],
        ["CONSTANT_COLUMN", ["SCALAR", "SCALAR"], "BOOL"],
        ["TERMINAL_CHANGE_COLUMN", ["SCALAR", "SCALAR"], "BOOL"],
        ["SUM_PARTITION", ["COLUMN_VECTOR", "COLUMN_PARTITION"], "NAT"],
        ["GREATER_THAN", ["NAT", "NAT"], "BOOL"],
        ["IF_THEN_ELSE", ["BOOL", "ATOM", "ATOM"], "ATOM"],
        ["MDL_SELECT", ["RELATION", "COLUMN_PARTITION"], "RELATION"],
    ],
    "state_column_semantic_names_exposed": False,
    "action_metadata_semantic_names_exposed": False,
    "coordinate_token_atom_present": False,
    "direct_descriptor_to_column_equality_constructor_present": False,
    "predeclared_state_column_roles": [],
    "predeclared_dynamic_column_indices": [],
    "predeclared_action_projection_field": None,
}

MDL_AND_DEPENDENCY_RULE = {
    "relation_score_order": [
        "RESIDUAL_ERROR_COUNT",
        "SEMANTIC_EXCEPTION_COUNT",
        "GROUP_TO_COLUMN_MAPPING_COUNT",
        "SINGLETON_GROUP_COUNT",
        "TYPED_AST_NODE_COUNT",
        "FIELD_INDEX",
    ],
    "score_order": "LEXICOGRAPHIC_ASCENDING",
    "dynamic_column_acceptance": (
        "UNCHANGED_OR_ONE_SHARED_CYCLIC_INCREMENT_AND_CHANGED_AT_LEAST_ONCE"
    ),
    "removed_column_acceptance": "MONOTONE_SINGLE_BIT_INSERTION_PER_ACTION",
    "constant_column_acceptance": "UNCHANGED_IN_ALL_SOURCE_ROWS",
    "terminal_column_acceptance": "CHANGES_ONLY_ON_REGISTERED_TERMINAL_ROWS",
    "support_dependency_roots": "COMPILED_PROGRAM_INPUTS_ONLY",
    "support_normalization": "EXACT_ALGEBRAIC_AND_TERMINAL_NORMAL_FORMS",
    "support_deletion": "EXHAUSTIVE_FINITE_COUNTEREXAMPLE_SEARCH",
    "support_signature_fields_predeclared": [],
    "expected_factorization_predeclared": False,
    "expected_projection_field_predeclared": None,
}

OOD_CONTROL = {
    "control_id": "STANDARD_2048_OPAQUE_BOARD_SCHEMA_V1",
    "domain_family": "STANDARD_2048",
    "flat_state_column_count": 16,
    "action_metadata_field_count": 1,
    "registered_lmb_relation_assumptions_present": False,
    "expected_decision": "OOD_SCHEMA_REJECTED_NO_TRANSFER",
    "prior_or_overlay_access_allowed": False,
    "transition_outcome_access_allowed": False,
    "environment_step_allowed": False,
}

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_PREREGISTRATION_V46_DOMAIN,
    "observation": CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_OBSERVATION_V46_DOMAIN,
    "factorization": CONSTRUCTION_K7_LMB_COLUMN_FACTORIZATION_V46_DOMAIN,
    "program": CONSTRUCTION_K7_LMB_RELATION_PROGRAM_V46_DOMAIN,
    "distinction": CONSTRUCTION_K7_LMB_FACTORIZED_DISTINCTION_V46_DOMAIN,
    "episode": CONSTRUCTION_K7_LMB_FACTORIZED_EPISODE_V46_DOMAIN,
    "ood": CONSTRUCTION_K7_LMB_OPAQUE_SCHEMA_OOD_REJECTION_V46_DOMAIN,
    "campaign": CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_CAMPAIGN_V46_DOMAIN,
    "verification": CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_VERIFICATION_V46_DOMAIN,
}


class ConstructionK7LMBOpaqueColumnPreregistrationV46Error(ValueError):
    """A predecessor, opaque protocol, workload, or claim changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LMBOpaqueColumnPreregistrationV46Error(message)


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.lmb_opaque_column_preregistration.v46",
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
            "v45_preregistration_id": V45_PREREGISTRATION_ID,
            "v45_campaign_id": V45_CAMPAIGN_ID,
            "v45_verification_id": V45_VERIFICATION_ID,
            "all_predecessor_identities_preserved": True,
        },
        "opaque_flat_adapter_protocol": {
            "state_vector_role": "OPAQUE_ORDERED_SCALARS",
            "state_column_count_formula": "TYPE_COUNT_PLUS_THREE",
            "state_extra_column_count": STATE_EXTRA_COLUMN_COUNT,
            "action_metadata_field_count": ACTION_METADATA_FIELD_COUNT,
            "every_action_metadata_field_type": "ATOM",
            "state_column_semantic_names_exposed_to_synthesizer": False,
            "action_metadata_semantic_names_exposed_to_synthesizer": False,
            "coordinate_tokens_present": False,
            "direct_cross_interface_equal_values_present": False,
            "flat_column_order_salt": FLAT_COLUMN_ORDER_SALT,
            "action_value_salt": ACTION_VALUE_SALT,
            "status_encoding_salt": STATUS_ENCODING_SALT,
            "state_column_order_permuted_by_occurrence": True,
            "action_metadata_values_permuted_by_occurrence": True,
            "source_and_target_value_namespaces_disjoint": True,
        },
        "source_acquisition": {
            "instance_specification": SOURCE_SPEC,
            "ordered_seeds": list(SOURCE_ACQUISITION_SEEDS),
            "action_policy": "MIN_LEGAL_ACTION_ID",
            "action_policy_reads_column_roles": False,
            "action_policy_reads_action_metadata": False,
            "action_policy_reads_transition_outcome_before_selection": False,
            "stop_when": {
                "unique_minimum_mdl_factorization_and_projection": True,
                "minimum_changed_dynamic_column_count": MIN_DYNAMIC_COLUMN_COUNT,
                "one_shared_cyclic_cardinality_derived": True,
            },
            "maximum_transition_labels": MAX_SOURCE_ACQUISITION_LABELS,
            "source_generation_witness_access_allowed": False,
            "hidden_solution_sequence_access_allowed": False,
        },
        "source_program_confirmation": {
            "fresh_seed": SOURCE_CONFIRMATION_SEED,
            "policy": "DERIVED_FACTORIZATION_RELATION_AND_PROGRAM_PLAN",
            "kernel_step_during_planning_allowed": False,
            "source_generation_witness_access_allowed": False,
        },
        "generic_relation_meta_grammar": GENERIC_RELATION_META_GRAMMAR,
        "mdl_and_dependency_rule": MDL_AND_DEPENDENCY_RULE,
        "heldout_target": {
            "seeds": list(HELDOUT_SEEDS),
            "instance_specification": TARGET_SPEC,
            "tile_count_changed": True,
            "type_count_changed": True,
            "capacity_changed": True,
            "layer_depth_changed": True,
            "state_column_order_changed": True,
            "action_metadata_values_changed": True,
            "generation_witness_access_allowed": False,
            "target_outcome_observed_before_registration": False,
        },
        "ood_no_transfer_control": OOD_CONTROL,
        "planning_and_recovery_protocol": {
            "arms": list(ARMS),
            "receding_horizon": RECEDING_HORIZON,
            "kernel_step_during_planning_allowed": False,
            "target_relation_mapping_requires_certificate_support": True,
            "first_unverified_action_group_requires_failed_certificate": True,
            "ground_distinction_requires_prior_failed_certificate": True,
            "successful_certificate_forbids_ground_acquisition": True,
            "strict_control_support_key": "EXACT_OPAQUE_STATE_ACTION_CONTEXT",
            "maximum_target_local_labels_per_episode": MAX_TARGET_LOCAL_LABELS_PER_EPISODE,
        },
        "accounting_axes": {
            "source_acquisition_labels": "labels",
            "source_confirmation_labels": "labels",
            "target_local_distinction_labels": "labels",
            "ood_target_labels": "labels",
            "execution_environment_steps": "steps",
            "factorization_relation_program_dependency_derivation": "compute events",
            "source_and_target_abstract_transition_evaluations": "compute events",
            "certificate_evaluations": "compute events",
            "ood_schema_evaluations": "compute events",
            "peak_dynamic_program_cache_entries": "peak entries",
            "labels_steps_and_compute_may_not_be_collapsed": True,
        },
        "required_positive_conditions": [
            "OPAQUE_STATE_COLUMN_ROLES_ARE_MDL_DERIVED",
            "ACTION_FIELD_GROUP_TO_CHANGED_COLUMN_RELATION_IS_MDL_DERIVED",
            "NO_COORDINATE_TOKEN_EQUALITY_JOIN_IS_AVAILABLE",
            "PROGRAM_AND_SUPPORT_ARE_COMPILED_FROM_RAW_DELTAS",
            "FRESH_TARGET_COLUMN_AND_ACTION_NAMESPACES_CHANGE",
            "ALL_HELDOUT_EPISODES_COMPLETE_IN_BOTH_ARMS",
            "EVERY_TARGET_LABEL_FOLLOWS_FAILED_CERTIFICATE",
            "DERIVED_FACTORIZED_ARM_USES_FEWER_LABELS_THAN_STRICT_CONTROL",
            "INCOMPATIBLE_CROSS_DOMAIN_SCHEMA_RECEIVES_NO_PRIOR_OR_OUTCOME",
            "PRODUCER_FREE_VERIFIER_REDERIVES_ALL_POSITIVE_AND_OOD_RESULTS",
        ],
        "outcome_fields_present": False,
        "campaign_executed": False,
        "state_column_roles_predeclared": False,
        "coordinate_token_equality_scaffold_present": False,
        "open_ended_relation_grammar_invention_claimed": False,
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
        "lmb_opaque_column_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LMBOpaqueColumnPreregistrationV46:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V46 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V46 preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "lmb_opaque_column_preregistration_id"
        }
        if (
            document.get("lmb_opaque_column_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V46 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError("V46 preregistration is not an object")
        return value


def freeze_lmb_opaque_column_preregistration_v46() -> LMBOpaqueColumnPreregistrationV46:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["lmb_opaque_column_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V46 preregistration changed")
    return LMBOpaqueColumnPreregistrationV46(_ISSUER, raw, identity)


def verify_lmb_opaque_column_preregistration_v46(
    value: LMBOpaqueColumnPreregistrationV46,
) -> LMBOpaqueColumnPreregistrationV46:
    if type(value) is not LMBOpaqueColumnPreregistrationV46:
        _fail("V46 preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("V46 preregistration semantics changed")
    return value


__all__ = (
    "ACTION_METADATA_FIELD_COUNT",
    "ARMS",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FLAT_COLUMN_ORDER_SALT",
    "FUTURE_DOMAINS",
    "GENERIC_RELATION_META_GRAMMAR",
    "HELDOUT_SEEDS",
    "LMBOpaqueColumnPreregistrationV46",
    "MDL_AND_DEPENDENCY_RULE",
    "OOD_CONTROL",
    "PREREGISTRATION_ID",
    "RECEDING_HORIZON",
    "SOURCE_ACQUISITION_SEEDS",
    "SOURCE_CONFIRMATION_SEED",
    "SOURCE_SPEC",
    "STATE_EXTRA_COLUMN_COUNT",
    "TARGET_SPEC",
    "freeze_lmb_opaque_column_preregistration_v46",
    "verify_lmb_opaque_column_preregistration_v46",
)
