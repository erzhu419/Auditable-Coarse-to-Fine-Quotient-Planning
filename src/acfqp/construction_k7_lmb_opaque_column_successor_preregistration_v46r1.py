"""Outcome-free V46r1 successor after the preserved V46 grammar failure."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_lmb_opaque_column_failure_v46 as failure
from acfqp import construction_k7_lmb_opaque_column_preregistration_v46 as base
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_LMB_COLUMN_FACTORIZATION_V46R1_DOMAIN,
    CONSTRUCTION_K7_LMB_FACTORIZED_DISTINCTION_V46R1_DOMAIN,
    CONSTRUCTION_K7_LMB_FACTORIZED_EPISODE_V46R1_DOMAIN,
    CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_CAMPAIGN_V46R1_DOMAIN,
    CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_OBSERVATION_V46R1_DOMAIN,
    CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_SUCCESSOR_PREREGISTRATION_V46R1_DOMAIN,
    CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_VERIFICATION_V46R1_DOMAIN,
    CONSTRUCTION_K7_LMB_OPAQUE_SCHEMA_OOD_REJECTION_V46R1_DOMAIN,
    CONSTRUCTION_K7_LMB_RELATION_PROGRAM_V46R1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "46.1.0"
PROPOSED_CONTRACT_VERSION = "2.0.211"
PROFILE_KEY = "construction_k7_lmb_opaque_column_successor_v46r1"
PREREGISTRATION_ID = "9135f93555696f38e75897dee45c2b389f0374ac8060e5cc4e5a5928dfc08963"
EXPECTED_CANONICAL_BYTE_COUNT = 10_047
EXPECTED_CANONICAL_SHA256 = "d652a55125b0cc697f9a9a60ec403c246f04b2857b2c14c2f8b841c862fe29ee"

V46_PREREGISTRATION_ID = base.PREREGISTRATION_ID
V46_FAILURE_ID = failure.FAILURE_ID
V46_ATTEMPTED_CAMPAIGN_ID = (
    "7eca22a5292256d98898f4dfaeed48efce058a5becec12ad70b44f35f6c59ce2"
)

SOURCE_SPEC = dict(base.SOURCE_SPEC)
SOURCE_ACQUISITION_SEEDS = (462101, 462102, 462103, 462104)
SOURCE_CONFIRMATION_SEED = 462201
MAX_SOURCE_ACQUISITION_LABELS = 80
MIN_DYNAMIC_COLUMN_COUNT = 4
TARGET_SPEC = dict(base.TARGET_SPEC)
HELDOUT_SEEDS = (463301, 463302, 463303, 463304, 463305, 463306)
RECEDING_HORIZON = base.RECEDING_HORIZON
MAX_TARGET_LOCAL_LABELS_PER_EPISODE = base.MAX_TARGET_LOCAL_LABELS_PER_EPISODE
ARMS = base.ARMS
STATE_EXTRA_COLUMN_COUNT = base.STATE_EXTRA_COLUMN_COUNT
ACTION_METADATA_FIELD_COUNT = base.ACTION_METADATA_FIELD_COUNT
FLAT_COLUMN_ORDER_SALT = 0x46D4
ACTION_VALUE_SALT = 0x46E5
STATUS_ENCODING_SALT = 0x46F6

ADDED_CONSTRUCTORS = (
    "ADD_ONE",
    "ALL_ACTION_IDS_INSERTED",
    "MODULO",
    "RELATION_VECTOR_AT",
    "RELATION_VECTOR_UPDATE",
)

GENERIC_RELATION_META_GRAMMAR = {
    "types": base.GENERIC_RELATION_META_GRAMMAR["types"],
    "atoms": [
        *base.GENERIC_RELATION_META_GRAMMAR["atoms"],
        ["COLUMN_TRANSITION_TRACES", "RELATION"],
        ["PRE_REMOVED_SET", "SCALAR"],
        ["FACTORIZED_CAPACITY_COLUMN", "SCALAR"],
        ["FAILURE", "ATOM"],
        ["SUCCESS", "ATOM"],
        ["ACTIVE", "ATOM"],
    ],
    "constructors": [
        *base.GENERIC_RELATION_META_GRAMMAR["constructors"],
        ["RELATION_VECTOR_AT", ["COLUMN_VECTOR", "RELATION"], "SCALAR"],
        [
            "RELATION_VECTOR_UPDATE",
            ["COLUMN_VECTOR", "RELATION", "SCALAR"],
            "COLUMN_VECTOR",
        ],
        ["ADD_ONE", ["NAT"], "NAT"],
        ["MODULO", ["NAT", "NAT"], "NAT"],
        ["ALL_ACTION_IDS_INSERTED", ["SCALAR"], "BOOL"],
    ],
    "state_column_semantic_names_exposed": False,
    "action_metadata_semantic_names_exposed": False,
    "coordinate_token_atom_present": False,
    "direct_descriptor_to_column_equality_constructor_present": False,
    "predeclared_state_column_roles": [],
    "predeclared_dynamic_column_indices": [],
    "predeclared_action_projection_field": None,
}

MDL_AND_DEPENDENCY_RULE = base.MDL_AND_DEPENDENCY_RULE
OOD_CONTROL = base.OOD_CONTROL

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_SUCCESSOR_PREREGISTRATION_V46R1_DOMAIN,
    "observation": CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_OBSERVATION_V46R1_DOMAIN,
    "factorization": CONSTRUCTION_K7_LMB_COLUMN_FACTORIZATION_V46R1_DOMAIN,
    "program": CONSTRUCTION_K7_LMB_RELATION_PROGRAM_V46R1_DOMAIN,
    "distinction": CONSTRUCTION_K7_LMB_FACTORIZED_DISTINCTION_V46R1_DOMAIN,
    "episode": CONSTRUCTION_K7_LMB_FACTORIZED_EPISODE_V46R1_DOMAIN,
    "ood": CONSTRUCTION_K7_LMB_OPAQUE_SCHEMA_OOD_REJECTION_V46R1_DOMAIN,
    "campaign": CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_CAMPAIGN_V46R1_DOMAIN,
    "verification": CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_VERIFICATION_V46R1_DOMAIN,
}


class ConstructionK7LMBOpaqueColumnSuccessorPreregistrationV46R1Error(ValueError):
    """The failed predecessor, grammar correction, workload, or claim changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LMBOpaqueColumnSuccessorPreregistrationV46R1Error(message)


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.lmb_opaque_column_successor_preregistration.v46r1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "v41_campaign_id": base.V41_CAMPAIGN_ID,
            "v41_verification_id": base.V41_VERIFICATION_ID,
            "v42_campaign_id": base.V42_CAMPAIGN_ID,
            "v42_verification_id": base.V42_VERIFICATION_ID,
            "v43_campaign_id": base.V43_CAMPAIGN_ID,
            "v43_verification_id": base.V43_VERIFICATION_ID,
            "v44_preregistration_id": base.V44_PREREGISTRATION_ID,
            "v44_failure_id": base.V44_FAILURE_ID,
            "v44r1_campaign_id": base.V44R1_CAMPAIGN_ID,
            "v44r1_verification_id": base.V44R1_VERIFICATION_ID,
            "v45_preregistration_id": base.V45_PREREGISTRATION_ID,
            "v45_campaign_id": base.V45_CAMPAIGN_ID,
            "v45_verification_id": base.V45_VERIFICATION_ID,
            "v46_preregistration_id": V46_PREREGISTRATION_ID,
            "v46_attempted_campaign_id": V46_ATTEMPTED_CAMPAIGN_ID,
            "v46_failure_id": V46_FAILURE_ID,
            "v46_failure_preserved_before_successor_registration": True,
            "all_predecessor_identities_preserved": True,
        },
        "grammar_correction": {
            "failure_code": "COMPILED_PROGRAM_USES_UNREGISTERED_RELATION_CONSTRUCTORS",
            "exact_unregistered_constructor_names": list(ADDED_CONSTRUCTORS),
            "all_failed_constructor_names_now_registered": True,
            "no_other_constructor_added": True,
            "same_identity_corrected_rerun_allowed": False,
            "fresh_source_and_target_identities_required": True,
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
            "policy": "DERIVED_FACTORIZATION_RELATION_AND_REGISTERED_PROGRAM_PLAN",
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
            "ALL_COMPILED_CONSTRUCTORS_BELONG_TO_REGISTERED_META_GRAMMAR",
            "OPAQUE_STATE_COLUMN_ROLES_ARE_MDL_DERIVED",
            "ACTION_FIELD_GROUP_TO_CHANGED_COLUMN_RELATION_IS_MDL_DERIVED",
            "NO_COORDINATE_TOKEN_EQUALITY_JOIN_IS_AVAILABLE",
            "PROGRAM_AND_SUPPORT_ARE_COMPILED_FROM_RAW_DELTAS",
            "ALL_FRESH_HELDOUT_EPISODES_COMPLETE_IN_BOTH_ARMS",
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
        "lmb_opaque_column_successor_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LMBOpaqueColumnSuccessorPreregistrationV46R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V46r1 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V46r1 preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "lmb_opaque_column_successor_preregistration_id"
        }
        if (
            document.get("lmb_opaque_column_successor_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V46r1 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError("V46r1 preregistration is not an object")
        return value


def freeze_lmb_opaque_column_successor_preregistration_v46r1() -> (
    LMBOpaqueColumnSuccessorPreregistrationV46R1
):
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["lmb_opaque_column_successor_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V46r1 preregistration changed")
    return LMBOpaqueColumnSuccessorPreregistrationV46R1(_ISSUER, raw, identity)


def verify_lmb_opaque_column_successor_preregistration_v46r1(
    value: LMBOpaqueColumnSuccessorPreregistrationV46R1,
) -> LMBOpaqueColumnSuccessorPreregistrationV46R1:
    if type(value) is not LMBOpaqueColumnSuccessorPreregistrationV46R1:
        _fail("V46r1 preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("V46r1 preregistration semantics changed")
    return value


__all__ = (
    "ACTION_METADATA_FIELD_COUNT",
    "ADDED_CONSTRUCTORS",
    "ARMS",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FLAT_COLUMN_ORDER_SALT",
    "FUTURE_DOMAINS",
    "GENERIC_RELATION_META_GRAMMAR",
    "HELDOUT_SEEDS",
    "LMBOpaqueColumnSuccessorPreregistrationV46R1",
    "MDL_AND_DEPENDENCY_RULE",
    "OOD_CONTROL",
    "PREREGISTRATION_ID",
    "RECEDING_HORIZON",
    "SOURCE_ACQUISITION_SEEDS",
    "SOURCE_CONFIRMATION_SEED",
    "SOURCE_SPEC",
    "STATE_EXTRA_COLUMN_COUNT",
    "TARGET_SPEC",
    "V46_ATTEMPTED_CAMPAIGN_ID",
    "V46_FAILURE_ID",
    "V46_PREREGISTRATION_ID",
    "freeze_lmb_opaque_column_successor_preregistration_v46r1",
    "verify_lmb_opaque_column_successor_preregistration_v46r1",
)
