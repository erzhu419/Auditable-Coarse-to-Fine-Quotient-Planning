"""Outcome-free V43 registration for witness-blind LMB synthesis.

V42 used a private source construction sequence to schedule its offline rows.
V43 removes that scaffold.  A frozen exploration policy chooses each source
operation only from the current public state, legal operations, and the
remaining finite candidate programs.  Neither source nor target generation
witnesses may be read.  The selected program is then tested on larger, deeper
held-out structures in matched structural-support and exact-context arms.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_LMB_CROSS_CARDINALITY_EPISODE_V43_DOMAIN,
    CONSTRUCTION_K7_LMB_WITNESS_BLIND_CAMPAIGN_V43_DOMAIN,
    CONSTRUCTION_K7_LMB_WITNESS_BLIND_DISTINCTION_V43_DOMAIN,
    CONSTRUCTION_K7_LMB_WITNESS_BLIND_PREREGISTRATION_V43_DOMAIN,
    CONSTRUCTION_K7_LMB_WITNESS_BLIND_PROPOSAL_V43_DOMAIN,
    CONSTRUCTION_K7_LMB_WITNESS_BLIND_VERIFICATION_V43_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "43.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.206"
PROFILE_KEY = "construction_k7_lmb_witness_blind_cross_cardinality_v43"
PREREGISTRATION_ID = (
    "c42ed28cc36eb00b88081b47fd0873783e85b3d8ff06cdc4bf07d6be692ed9fa"
)
EXPECTED_CANONICAL_BYTE_COUNT = 4_238
EXPECTED_CANONICAL_SHA256 = (
    "2376f2decc01b42e85e6040c178351f3de5ae933b3a30bbdda43b74635cbd774"
)

V41_CAMPAIGN_ID = "1a576e0c8b34f52050f77366ec7ac39dab58bddd53ec91180ed9d6c092072732"
V41_VERIFICATION_ID = "a05a6b795a15a8dda596b148efe52b374cc687f125b1c14731466f83aa791396"
V42_PREREGISTRATION_ID = "2c0415db488d7abafe8317a0377f619b331326f3aa15c1a97dde791fa636f02b"
V42_CAMPAIGN_ID = "c8adada792b7dacfce816bf1916457329643b61e8915f285472708c6c6bd359b"
V42_VERIFICATION_ID = "af44dabf2f2f7b05767343c2d8306165cfe828ff8180efe7d409e0baa3315da0"

SOURCE_SEEDS = (430001, 430002, 430003, 430004)
HELDOUT_SEEDS = (431101, 431102, 431103, 431104, 431105, 431106)
SOURCE_SPEC = {"tile_count": 12, "type_count": 4, "capacity": 5, "max_layers": 3}
TARGET_SPEC = {"tile_count": 15, "type_count": 5, "capacity": 5, "max_layers": 4}
RECEDING_HORIZON = 4
MAX_SOURCE_LABELS = 24
MAX_TARGET_LOCAL_LABELS_PER_EPISODE = 30
ARMS = ("STRUCTURAL_META_PRIOR", "STRICT_NO_PRIOR_CONTEXT_TABLE")
CANDIDATES = tuple(
    (trigger, offset) for trigger in (0, 1, 2) for offset in (-1, 0, 1)
)
EXPLORATION_SCORE = (
    "MAX_PREDICTION_PARTITION",
    "MIN_MAX_PARTITION",
    "MAX_RESOURCE_LOAD",
    "MAX_SELECTED_CLASS_COUNT",
    "MIN_TILE_ID",
)
SHARED_PRIMITIVES = (
    "capacity_slack",
    "future_repair_supply",
    "post_operation_load",
    "resource_load",
    "rewrite_on_next",
    "selected_class_count",
)

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_LMB_WITNESS_BLIND_PREREGISTRATION_V43_DOMAIN,
    "proposal": CONSTRUCTION_K7_LMB_WITNESS_BLIND_PROPOSAL_V43_DOMAIN,
    "distinction": CONSTRUCTION_K7_LMB_WITNESS_BLIND_DISTINCTION_V43_DOMAIN,
    "episode": CONSTRUCTION_K7_LMB_CROSS_CARDINALITY_EPISODE_V43_DOMAIN,
    "campaign": CONSTRUCTION_K7_LMB_WITNESS_BLIND_CAMPAIGN_V43_DOMAIN,
    "verification": CONSTRUCTION_K7_LMB_WITNESS_BLIND_VERIFICATION_V43_DOMAIN,
}


class ConstructionK7LMBWitnessBlindPreregistrationV43Error(ValueError):
    """A predecessor, exploration, held-out workload, or claim lock changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LMBWitnessBlindPreregistrationV43Error(message)


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.lmb_witness_blind_preregistration.v43",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "v41_campaign_id": V41_CAMPAIGN_ID,
            "v41_verification_id": V41_VERIFICATION_ID,
            "v42_preregistration_id": V42_PREREGISTRATION_ID,
            "v42_campaign_id": V42_CAMPAIGN_ID,
            "v42_verification_id": V42_VERIFICATION_ID,
            "predecessor_identities_preserved": True,
        },
        "source_exploration": {
            "seeds": list(SOURCE_SEEDS),
            "instance_specification": SOURCE_SPEC,
            "candidate_programs": [list(row) for row in CANDIDATES],
            "exploration_score_lexicographic": list(EXPLORATION_SCORE),
            "maximum_source_transition_labels": MAX_SOURCE_LABELS,
            "reset_on_terminal_if_version_space_not_singleton": True,
            "source_generation_witness_access_allowed": False,
            "source_hidden_solution_sequence_access_allowed": False,
            "action_selection_uses_only_public_state_legal_actions_and_candidates": True,
        },
        "cross_cardinality_target": {
            "seeds": list(HELDOUT_SEEDS),
            "instance_specification": TARGET_SPEC,
            "source_to_target_tile_count_changed": True,
            "source_to_target_type_count_changed": True,
            "source_to_target_layer_depth_changed": True,
            "heldout_generation_witness_access_allowed": False,
            "target_transition_observed_before_registration": False,
            "target_outcome_or_policy_present": False,
        },
        "world_model_protocol": {
            "shared_primitive_compatibility_names": list(SHARED_PRIMITIVES),
            "selected_candidate_requires_unique_observation_consistency": True,
            "receding_horizon": RECEDING_HORIZON,
            "model_only_terminal_feasibility_dynamic_program": True,
            "kernel_step_during_planning_allowed": False,
            "arms": list(ARMS),
            "same_heldout_instances_and_action_proposal_in_both_arms": True,
            "structural_arm_support_key": [
                "selected_class_count",
                "resource_load",
                "at_capacity",
            ],
            "strict_control_support_key": "EXACT_STATE_ACTION_CONTEXT",
            "ground_distinction_requires_prior_failed_certificate": True,
            "successful_certificate_forbids_ground_acquisition": True,
            "maximum_target_local_labels_per_episode": MAX_TARGET_LOCAL_LABELS_PER_EPISODE,
        },
        "accounting_axes": {
            "offline_source_transition_labels": "labels",
            "target_local_distinction_labels": "labels",
            "execution_environment_steps": "steps",
            "abstract_transition_evaluations": "compute events",
            "certificate_evaluations": "compute events",
            "peak_dynamic_program_cache_entries": "peak entries",
            "labels_steps_and_compute_may_not_be_collapsed": True,
        },
        "required_positive_conditions": [
            "WITNESS_BLIND_SOURCE_POLICY_IDENTIFIES_ONE_PROGRAM",
            "TARGET_CARDINALITY_AND_LAYER_DEPTH_DIFFER_FROM_SOURCE",
            "BOTH_ARMS_COMPLETE_ALL_HELDOUT_EPISODES",
            "EVERY_TARGET_LABEL_HAS_PRIOR_FAILED_CERTIFICATE",
            "STRUCTURAL_ARM_USES_FEWER_TARGET_LABELS_THAN_STRICT_CONTROL",
            "PRODUCER_FREE_REPLAY_REBUILDS_SOURCE_POLICY_AND_TARGET_PLANS",
        ],
        "outcome_fields_present": False,
        "campaign_executed": False,
        "open_ended_operator_invention_claimed": False,
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
        "lmb_witness_blind_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LMBWitnessBlindPreregistrationV43:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V43 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V43 preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "lmb_witness_blind_preregistration_id"
        }
        if (
            document.get("lmb_witness_blind_preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V43 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError("V43 preregistration is not an object")
        return value


def freeze_lmb_witness_blind_preregistration_v43() -> LMBWitnessBlindPreregistrationV43:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["lmb_witness_blind_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V43 preregistration changed")
    return LMBWitnessBlindPreregistrationV43(_ISSUER, raw, identity)


def verify_lmb_witness_blind_preregistration_v43(
    value: LMBWitnessBlindPreregistrationV43,
) -> LMBWitnessBlindPreregistrationV43:
    if type(value) is not LMBWitnessBlindPreregistrationV43:
        _fail("V43 preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("V43 preregistration semantics changed")
    return value


__all__ = (
    "ARMS",
    "CANDIDATES",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "HELDOUT_SEEDS",
    "LMBWitnessBlindPreregistrationV43",
    "PREREGISTRATION_ID",
    "RECEDING_HORIZON",
    "SOURCE_SEEDS",
    "SOURCE_SPEC",
    "TARGET_SPEC",
    "freeze_lmb_witness_blind_preregistration_v43",
    "verify_lmb_witness_blind_preregistration_v43",
)
