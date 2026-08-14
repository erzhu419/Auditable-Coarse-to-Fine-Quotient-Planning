"""Outcome-free registration of the second-domain reusable-model campaign.

V41 closed one complete standard 2048 episode while keeping learned-model
labels separate from planning compute.  V42 freezes a different domain before
any target execution: Layered Matching Buffer.  A finite, domain-neutral
rewrite/capacity grammar may be proposed from offline structural observations;
the same held-out instances are then assigned to a structural-meta-prior arm
and a strict context-table arm.  Both arms must plan receding-horizon paths in
their learned model.  Target ground rows are authorized only by a failed
certificate and remain a separate acquisition axis.

This registration contains seeds and protocol, never target outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_LMB_LOCAL_GROUND_DISTINCTION_V42_DOMAIN,
    CONSTRUCTION_K7_LMB_RECEDING_EPISODE_V42_DOMAIN,
    CONSTRUCTION_K7_LMB_REUSABLE_PRIMITIVE_PROPOSAL_V42_DOMAIN,
    CONSTRUCTION_K7_LMB_REUSABLE_WORLD_MODEL_CAMPAIGN_V42_DOMAIN,
    CONSTRUCTION_K7_LMB_REUSABLE_WORLD_MODEL_PREREGISTRATION_V42_DOMAIN,
    CONSTRUCTION_K7_LMB_REUSABLE_WORLD_MODEL_VERIFICATION_V42_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "42.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.205"
PROFILE_KEY = "construction_k7_lmb_reusable_world_model_v42"

# Frozen only after the outcome-free bytes have been committed.
PREREGISTRATION_ID = (
    "2c0415db488d7abafe8317a0377f619b331326f3aa15c1a97dde791fa636f02b"
)
EXPECTED_CANONICAL_BYTE_COUNT = 4_776
EXPECTED_CANONICAL_SHA256 = (
    "efd8745c4104b728b8ecaeae97257f93acbc143b13479af562ce7697c7bdba25"
)

V41_PREREGISTRATION_ID = (
    "4298e79e9f8aee401901efb2d534e55954d7cd43932da891f51f7daeb52f6dd7"
)
V41_CAMPAIGN_ID = (
    "1a576e0c8b34f52050f77366ec7ac39dab58bddd53ec91180ed9d6c092072732"
)
V41_VERIFICATION_ID = (
    "a05a6b795a15a8dda596b148efe52b374cc687f125b1c14731466f83aa791396"
)

SOURCE_OBSERVATION_SEEDS = (420001, 420002, 420003, 420004)
HELDOUT_EPISODE_SEEDS = (421101, 421102, 421103, 421104, 421105, 421106)
TILE_COUNT = 12
TYPE_COUNT = 4
BUFFER_CAPACITY = 5
MAX_LAYERS = 3
RECEDING_HORIZON = 4
MAX_LOCAL_DISTINCTION_ROWS_PER_EPISODE = 24

GENERIC_SOURCE_RELATIONS = (
    "AVAILABLE_OPERATION_SET",
    "CAPACITY_LIMIT",
    "DEPENDENCY_RELATION",
    "OPERATION_CLASS",
    "RESOURCE_COUNT_VECTOR",
)
GENERIC_META_OPERATORS = (
    "CARDINALITY",
    "COUNT_AVAILABLE_BY_CLASS",
    "EQUALS",
    "SELECT_CLASS_COUNT",
    "SUBTRACT",
    "SUM_VECTOR",
)
REGISTERED_SHARED_PRIMITIVES = (
    "capacity_slack",
    "future_repair_supply",
    "post_operation_load",
    "resource_load",
    "rewrite_on_next",
    "selected_class_count",
)
ACQUISITION_ARMS = (
    "STRUCTURAL_META_PRIOR",
    "STRICT_NO_PRIOR_CONTEXT_TABLE",
)

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_LMB_REUSABLE_WORLD_MODEL_PREREGISTRATION_V42_DOMAIN,
    "primitive_proposal": CONSTRUCTION_K7_LMB_REUSABLE_PRIMITIVE_PROPOSAL_V42_DOMAIN,
    "local_ground_distinction": CONSTRUCTION_K7_LMB_LOCAL_GROUND_DISTINCTION_V42_DOMAIN,
    "episode": CONSTRUCTION_K7_LMB_RECEDING_EPISODE_V42_DOMAIN,
    "campaign": CONSTRUCTION_K7_LMB_REUSABLE_WORLD_MODEL_CAMPAIGN_V42_DOMAIN,
    "verification": CONSTRUCTION_K7_LMB_REUSABLE_WORLD_MODEL_VERIFICATION_V42_DOMAIN,
}


class ConstructionK7LMBReusableWorldModelPreregistrationV42Error(ValueError):
    """The V41 predecessor, LMB workload, grammar, or claim locks changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LMBReusableWorldModelPreregistrationV42Error(message)


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.lmb_reusable_world_model_preregistration.v42",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessor": {
            "v41_preregistration_id": V41_PREREGISTRATION_ID,
            "v41_complete_episode_campaign_id": V41_CAMPAIGN_ID,
            "v41_producer_free_verification_id": V41_VERIFICATION_ID,
            "v41_identities_preserved_without_rewrite": True,
        },
        "outcome_free_workload": {
            "domain": "LAYERED_MATCHING_BUFFER",
            "source_observation_seeds": list(SOURCE_OBSERVATION_SEEDS),
            "heldout_episode_seeds": list(HELDOUT_EPISODE_SEEDS),
            "tile_count": TILE_COUNT,
            "type_count": TYPE_COUNT,
            "buffer_capacity": BUFFER_CAPACITY,
            "max_layers": MAX_LAYERS,
            "generation_witness_available_to_planner": False,
            "target_kernel_transition_observed_before_registration": False,
            "target_outcome_or_policy_present": False,
        },
        "observation_derived_program_space": {
            "source_relations": list(GENERIC_SOURCE_RELATIONS),
            "meta_operators": list(GENERIC_META_OPERATORS),
            "registered_shared_primitive_compatibility_names": list(
                REGISTERED_SHARED_PRIMITIVES
            ),
            "domain_name_or_reward_query_is_program_input": False,
            "finite_human_registered_operator_grammar": True,
            "open_ended_operator_invention_claimed": False,
            "proposal_acceptance_requires_source_observation_consistency": True,
        },
        "matched_acquisition_protocol": {
            "arms": list(ACQUISITION_ARMS),
            "same_heldout_instances_and_episode_order": True,
            "structural_meta_prior_uses_shared_primitive_support_keys": True,
            "strict_no_prior_uses_exact_state_action_context_keys": True,
            "prior_is_proposal_order_not_acceptance_authority": True,
            "target_row_may_be_acquired_only_after_certificate_failure": True,
            "local_distinction_rows_are_immutable_episode_overlays": True,
            "maximum_local_distinction_rows_per_episode": (
                MAX_LOCAL_DISTINCTION_ROWS_PER_EPISODE
            ),
            "sample_labels_and_planning_compute_are_separate_axes": True,
        },
        "planning_and_certificate_protocol": {
            "receding_horizon": RECEDING_HORIZON,
            "abstract_model_replanned_after_each_executed_operation": True,
            "terminal_feasibility_proof_uses_model_only_dynamic_programming": True,
            "generation_witness_or_target_solution_sequence_forbidden": True,
            "kernel_step_during_planning_forbidden": True,
            "certificate_frozen_before_each_target_execution": True,
            "failed_certificate_precedes_every_local_ground_distinction": True,
            "successful_certificate_forbids_local_ground_acquisition": True,
        },
        "accounting_axes": {
            "offline_source_transition_labels": "additive labels",
            "target_local_distinction_labels": "additive labels",
            "execution_environment_steps": "additive steps",
            "abstract_transition_evaluations": "additive compute events",
            "certificate_evaluations": "additive compute events",
            "dynamic_programming_cache_entries": "peak entries",
            "labels_must_not_be_summed_with_compute_events": True,
            "execution_steps_must_not_be_relabelled_as_model_labels": True,
        },
        "required_controls": [
            "MATCHED_STRUCTURAL_META_PRIOR_VERSUS_STRICT_NO_PRIOR",
            "COLD_EXACT_GROUND_EPISODE_REPLAY",
            "CERTIFICATE_SUCCESS_GROUND_QUERY_ATTACK_REJECTED",
            "TARGET_GENERATION_WITNESS_ACCESS_REJECTED",
            "SAMPLE_AND_COMPUTE_AXIS_COLLAPSE_REJECTED",
            "PRIMITIVE_OR_PROPOSAL_IDENTITY_TAMPER_REJECTED",
        ],
        "required_positive_conditions": [
            "ONE_SOURCE_OBSERVATION_DERIVED_SHARED_PRIMITIVE_PROPOSAL",
            "BOTH_ARMS_COMPLETE_ALL_PREREGISTERED_HELDOUT_EPISODES",
            "ALL_TARGET_LABELS_HAVE_PRIOR_FAILED_CERTIFICATE_IDENTITIES",
            "ALL_PLANS_REPLAY_WITHOUT_KERNEL_STEP_DURING_PLANNING",
            "ALL_EPISODES_COLD_REPLAY_TO_THE_SAME_TERMINAL_STATUS",
            "STRUCTURAL_META_PRIOR_USES_FEWER_TARGET_LABELS_THAN_NO_PRIOR",
        ],
        "outcome_fields_present": False,
        "target_campaign_executed": False,
        "cross_domain_general_sample_efficiency_claimed": False,
        "broad_iid_claimed": False,
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
        "lmb_reusable_world_model_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LMBReusableWorldModelPreregistrationV42:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("LMB preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("LMB preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "lmb_reusable_world_model_preregistration_id"
        }
        if (
            document.get("lmb_reusable_world_model_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("LMB preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError("LMB preregistration is not an object")
        return document


def freeze_lmb_reusable_world_model_preregistration_v42(
) -> LMBReusableWorldModelPreregistrationV42:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["lmb_reusable_world_model_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen LMB preregistration changed")
    return LMBReusableWorldModelPreregistrationV42(_ISSUER, raw, identity)


def verify_lmb_reusable_world_model_preregistration_v42(
    value: LMBReusableWorldModelPreregistrationV42,
) -> LMBReusableWorldModelPreregistrationV42:
    if type(value) is not LMBReusableWorldModelPreregistrationV42:
        _fail("LMB preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("LMB preregistration semantics changed")
    return value


__all__ = (
    "ACQUISITION_ARMS",
    "BUFFER_CAPACITY",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "HELDOUT_EPISODE_SEEDS",
    "LMBReusableWorldModelPreregistrationV42",
    "MAX_LAYERS",
    "PREREGISTRATION_ID",
    "RECEDING_HORIZON",
    "REGISTERED_SHARED_PRIMITIVES",
    "SOURCE_OBSERVATION_SEEDS",
    "TILE_COUNT",
    "TYPE_COUNT",
    "freeze_lmb_reusable_world_model_preregistration_v42",
    "verify_lmb_reusable_world_model_preregistration_v42",
)
