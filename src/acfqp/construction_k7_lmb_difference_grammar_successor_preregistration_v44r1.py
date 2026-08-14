"""Outcome-free V44r1 successor after the preserved V44 coverage failure."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_lmb_difference_grammar_preregistration_v44 as v44
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_CAMPAIGN_V44R1_DOMAIN,
    CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_DISTINCTION_V44R1_DOMAIN,
    CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_EPISODE_V44R1_DOMAIN,
    CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_VERIFICATION_V44R1_DOMAIN,
    CONSTRUCTION_K7_LMB_DERIVED_TRANSITION_PROGRAM_V44R1_DOMAIN,
    CONSTRUCTION_K7_LMB_DIFFERENCE_GRAMMAR_SUCCESSOR_PREREGISTRATION_V44R1_DOMAIN,
    CONSTRUCTION_K7_LMB_MODEL_DERIVED_SOURCE_OBSERVATION_V44R1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "44.1.0"
PROPOSED_CONTRACT_VERSION = "2.0.208"
PROFILE_KEY = "construction_k7_lmb_raw_difference_synthesis_successor_v44r1"
PREREGISTRATION_ID = "ab2d00d7fb7ad79ee73b9f1ed74595e582b5790de2d3d45dbcf051901f79236f"
EXPECTED_CANONICAL_BYTE_COUNT = 5_801
EXPECTED_CANONICAL_SHA256 = "f47b7adfb74c53b4fca8cd8829c79368c713698b976970eb9393e5f6196099cc"

V41_CAMPAIGN_ID = v44.V41_CAMPAIGN_ID
V41_VERIFICATION_ID = v44.V41_VERIFICATION_ID
V42_CAMPAIGN_ID = v44.V42_CAMPAIGN_ID
V42_VERIFICATION_ID = v44.V42_VERIFICATION_ID
V43_PREREGISTRATION_ID = v44.V43_PREREGISTRATION_ID
V43_CAMPAIGN_ID = v44.V43_CAMPAIGN_ID
V43_VERIFICATION_ID = v44.V43_VERIFICATION_ID
V44_PREREGISTRATION_ID = v44.PREREGISTRATION_ID
V44_FAILURE_ID = "f98b1fb28efcb7f5f311f04d6c16bf283cbe521a2cf1f0cb4bc4fe3057d19bcd"
V44_FAILURE_BYTE_COUNT = 35_869
V44_FAILURE_SHA256 = "cda363571b6639b5bbe5895719da72bf7aa46fb54ab31433b9fe3a96e98a09b6"

SOURCE_SPEC = dict(v44.SOURCE_SPEC)
SOURCE_CONFIRMATION_SEED = 440301
INHERITED_OFFLINE_SOURCE_LABEL_COUNT = 42
MAX_ADDITIONAL_SOURCE_LABELS = SOURCE_SPEC["tile_count"]
TARGET_SPEC = dict(v44.TARGET_SPEC)
HELDOUT_SEEDS = (441301, 441302, 441303, 441304, 441305, 441306)
ARMS = v44.ARMS
RECEDING_HORIZON = v44.RECEDING_HORIZON
MAX_TARGET_LOCAL_LABELS_PER_EPISODE = v44.MAX_TARGET_LOCAL_LABELS_PER_EPISODE
TYPED_GRAMMAR = v44.TYPED_GRAMMAR

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_LMB_DIFFERENCE_GRAMMAR_SUCCESSOR_PREREGISTRATION_V44R1_DOMAIN,
    "source_observation": CONSTRUCTION_K7_LMB_MODEL_DERIVED_SOURCE_OBSERVATION_V44R1_DOMAIN,
    "program": CONSTRUCTION_K7_LMB_DERIVED_TRANSITION_PROGRAM_V44R1_DOMAIN,
    "distinction": CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_DISTINCTION_V44R1_DOMAIN,
    "episode": CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_EPISODE_V44R1_DOMAIN,
    "campaign": CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_CAMPAIGN_V44R1_DOMAIN,
    "verification": CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_VERIFICATION_V44R1_DOMAIN,
}


class ConstructionK7LMBDifferenceGrammarSuccessorPreregistrationV44R1Error(ValueError):
    """The failed predecessor, confirmation protocol, workload, or claims changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LMBDifferenceGrammarSuccessorPreregistrationV44R1Error(message)


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.lmb_difference_grammar_successor_preregistration.v44r1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "v41_campaign_id": V41_CAMPAIGN_ID,
            "v41_verification_id": V41_VERIFICATION_ID,
            "v42_campaign_id": V42_CAMPAIGN_ID,
            "v42_verification_id": V42_VERIFICATION_ID,
            "v43_preregistration_id": V43_PREREGISTRATION_ID,
            "v43_campaign_id": V43_CAMPAIGN_ID,
            "v43_verification_id": V43_VERIFICATION_ID,
            "v44_preregistration_id": V44_PREREGISTRATION_ID,
            "v44_failure_id": V44_FAILURE_ID,
            "v44_failure_byte_count": V44_FAILURE_BYTE_COUNT,
            "v44_failure_sha256": V44_FAILURE_SHA256,
            "failed_predecessor_preserved_without_relabeling": True,
        },
        "source_successor_protocol": {
            "instance_specification": SOURCE_SPEC,
            "inherited_offline_source_transition_labels": INHERITED_OFFLINE_SOURCE_LABEL_COUNT,
            "fresh_confirmation_seed": SOURCE_CONFIRMATION_SEED,
            "maximum_additional_source_labels": MAX_ADDITIONAL_SOURCE_LABELS,
            "partial_program_inputs": [
                "V44_RAW_STATE_ACTION_SUCCESSOR_DIFFERENCES",
                "PUBLIC_LEGAL_ACTION_SET",
                "PUBLIC_ACTION_CLASS",
                "PUBLIC_INSTANCE_CAPACITY",
            ],
            "confirmation_policy": (
                "DERIVE_PARTIAL_PROGRAM_THEN_MODEL_PLAN_FULL_REMOVAL"
            ),
            "full_removal_is_planning_goal_not_assumed_terminal_status": True,
            "terminal_success_rule_requires_fresh_observation": True,
            "kernel_step_during_source_planning_allowed": False,
            "source_generation_witness_access_allowed": False,
            "hidden_solution_sequence_access_allowed": False,
            "reuse_failed_v44_seed_under_new_identity": False,
        },
        "typed_expression_grammar": TYPED_GRAMMAR,
        "numeric_program_grid_present": False,
        "heldout_target": {
            "seeds": list(HELDOUT_SEEDS),
            "instance_specification": TARGET_SPEC,
            "different_from_source": {
                "tile_count": True,
                "type_count": True,
                "capacity": True,
                "layer_depth": True,
            },
            "generation_witness_access_allowed": False,
            "target_outcome_observed_before_registration": False,
        },
        "planning_and_recovery_protocol": {
            "arms": list(ARMS),
            "receding_horizon": RECEDING_HORIZON,
            "kernel_step_during_planning_allowed": False,
            "structural_support_key": [
                "SELECTED_COMPONENT_COUNT",
                "CAPACITY_SLACK",
                "AT_CAPACITY",
            ],
            "strict_control_support_key": "EXACT_STATE_ACTION_CONTEXT",
            "ground_distinction_requires_prior_failed_certificate": True,
            "successful_certificate_forbids_ground_acquisition": True,
            "maximum_target_local_labels_per_episode": MAX_TARGET_LOCAL_LABELS_PER_EPISODE,
        },
        "accounting_axes": {
            "inherited_offline_source_labels": "labels",
            "additional_source_confirmation_labels": "labels",
            "target_local_distinction_labels": "labels",
            "execution_environment_steps": "steps",
            "source_and_target_abstract_transition_evaluations": "compute events",
            "certificate_evaluations": "compute events",
            "grammar_derivation_events": "compute events",
            "peak_dynamic_program_cache_entries": "peak entries",
            "labels_steps_and_compute_may_not_be_collapsed": True,
        },
        "required_positive_conditions": [
            "FAILED_V44_PREDECESSOR_REMAINS_FROZEN",
            "FRESH_SOURCE_CONFIRMATION_OBSERVES_SUCCESS_ON_FULL_REMOVAL",
            "RAW_DIFFERENCES_COMPILE_ONE_EXACT_TYPED_PROGRAM_WITHOUT_NUMERIC_GRID",
            "ALL_HELDOUT_EPISODES_COMPLETE_IN_BOTH_ARMS",
            "EVERY_TARGET_LABEL_FOLLOWS_FAILED_CERTIFICATE",
            "STRUCTURAL_ARM_USES_FEWER_TARGET_LABELS_THAN_STRICT_CONTROL",
            "PRODUCER_FREE_VERIFIER_REDERIVES_PROGRAM_AND_PLANS",
        ],
        "outcome_fields_present": False,
        "campaign_executed": False,
        "open_ended_grammar_invention_claimed": False,
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
        "lmb_difference_grammar_successor_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LMBDifferenceGrammarSuccessorPreregistrationV44R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V44r1 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V44r1 preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "lmb_difference_grammar_successor_preregistration_id"
        }
        if (
            document.get("lmb_difference_grammar_successor_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V44r1 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError("V44r1 preregistration is not an object")
        return value


def freeze_lmb_difference_grammar_successor_preregistration_v44r1() -> (
    LMBDifferenceGrammarSuccessorPreregistrationV44R1
):
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["lmb_difference_grammar_successor_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V44r1 preregistration changed")
    return LMBDifferenceGrammarSuccessorPreregistrationV44R1(_ISSUER, raw, identity)


def verify_lmb_difference_grammar_successor_preregistration_v44r1(
    value: LMBDifferenceGrammarSuccessorPreregistrationV44R1,
) -> LMBDifferenceGrammarSuccessorPreregistrationV44R1:
    if type(value) is not LMBDifferenceGrammarSuccessorPreregistrationV44R1:
        _fail("V44r1 preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("V44r1 preregistration semantics changed")
    return value


__all__ = (
    "ARMS",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "HELDOUT_SEEDS",
    "LMBDifferenceGrammarSuccessorPreregistrationV44R1",
    "PREREGISTRATION_ID",
    "RECEDING_HORIZON",
    "SOURCE_CONFIRMATION_SEED",
    "SOURCE_SPEC",
    "TARGET_SPEC",
    "TYPED_GRAMMAR",
    "V44_FAILURE_ID",
    "freeze_lmb_difference_grammar_successor_preregistration_v44r1",
    "verify_lmb_difference_grammar_successor_preregistration_v44r1",
)
