"""Outcome-free V44 registration for raw-difference LMB program synthesis.

V43 removed source-generation-witness scheduling but selected among nine
predeclared numeric programs.  V44 registers only a small typed expression
language and a public-state exploration policy.  Rewrite cardinality,
capacity boundary, operated component, and terminal semantics must be solved
from raw state-action-successor differences after this registration freezes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_CAMPAIGN_V44_DOMAIN,
    CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_DISTINCTION_V44_DOMAIN,
    CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_EPISODE_V44_DOMAIN,
    CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_VERIFICATION_V44_DOMAIN,
    CONSTRUCTION_K7_LMB_DERIVED_TRANSITION_PROGRAM_V44_DOMAIN,
    CONSTRUCTION_K7_LMB_DIFFERENCE_GRAMMAR_PREREGISTRATION_V44_DOMAIN,
    CONSTRUCTION_K7_LMB_RAW_TRANSITION_OBSERVATION_V44_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "44.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.207"
PROFILE_KEY = "construction_k7_lmb_raw_difference_synthesis_v44"
PREREGISTRATION_ID = "6876b931a99f5d7da01e32df15788197b5acd6d42b625828d3daed1db3243f64"
EXPECTED_CANONICAL_BYTE_COUNT = 5_910
EXPECTED_CANONICAL_SHA256 = "62633cb5dbe84f7e0e6acc88189f4a9f67cdac9fb9fe8c35debe2fad1c094109"

V41_CAMPAIGN_ID = "1a576e0c8b34f52050f77366ec7ac39dab58bddd53ec91180ed9d6c092072732"
V41_VERIFICATION_ID = "a05a6b795a15a8dda596b148efe52b374cc687f125b1c14731466f83aa791396"
V42_CAMPAIGN_ID = "c8adada792b7dacfce816bf1916457329643b61e8915f285472708c6c6bd359b"
V42_VERIFICATION_ID = "af44dabf2f2f7b05767343c2d8306165cfe828ff8180efe7d409e0baa3315da0"
V43_PREREGISTRATION_ID = "c42ed28cc36eb00b88081b47fd0873783e85b3d8ff06cdc4bf07d6be692ed9fa"
V43_CAMPAIGN_ID = "d435246de035efd4081922b8d6995f1dceb36216bf08cb5766a76ed5dfdbe00d"
V43_VERIFICATION_ID = "d3e7426521c663ccef51a4da6bb30112c37fc7d37f743050d27942b578a76a51"

SOURCE_SPEC = {"tile_count": 15, "type_count": 5, "capacity": 5, "max_layers": 3}
SOURCE_SCHEDULE = (
    {
        "mode": "REWRITE_AND_SUCCESS_COVERAGE",
        "ordered_seeds": [440101, 440102, 440103, 440104],
        "score_lexicographic": [
            "MAX_SELECTED_COMPONENT_COUNT",
            "MIN_SELECTED_COUNT_VISIT_COUNT",
            "MAX_RESOURCE_LOAD",
            "MIN_TILE_ID",
        ],
        "stop_after": [
            "INCREMENT_DIFFERENCE_OBSERVED",
            "REWRITE_DIFFERENCE_OBSERVED",
            "SUCCESS_ON_FULL_REMOVAL_OBSERVED",
        ],
    },
    {
        "mode": "CAPACITY_BOUNDARY_STRESS",
        "ordered_seeds": [440201, 440202],
        "score_lexicographic": [
            "MIN_SELECTED_COMPONENT_COUNT",
            "MIN_SELECTED_COUNT_VISIT_COUNT",
            "MAX_RESOURCE_LOAD",
            "MIN_TILE_ID",
        ],
        "stop_after": [
            "ACTIVE_AT_CAPACITY_OBSERVED",
            "FAILURE_ONE_ABOVE_CAPACITY_OBSERVED",
        ],
    },
)
MAX_SOURCE_TRANSITION_LABELS = 72

TARGET_SPEC = {"tile_count": 18, "type_count": 6, "capacity": 6, "max_layers": 4}
HELDOUT_SEEDS = (441201, 441202, 441203, 441204, 441205, 441206)
ARMS = ("STRUCTURAL_META_PRIOR", "STRICT_NO_PRIOR_CONTEXT_TABLE")
RECEDING_HORIZON = 4
MAX_TARGET_LOCAL_LABELS_PER_EPISODE = 36

TYPED_GRAMMAR = {
    "types": ["BOOL", "COUNT_VECTOR", "INDEX", "NAT", "STATUS", "TILE_ID", "TILE_SET"],
    "atoms": [
        ["PRE_BUFFER", "COUNT_VECTOR"],
        ["POST_BUFFER", "COUNT_VECTOR"],
        ["ACTION_PUBLIC_CLASS", "INDEX"],
        ["ACTION_TILE", "TILE_ID"],
        ["PRE_REMOVED_SET", "TILE_SET"],
        ["POST_REMOVED_SET", "TILE_SET"],
        ["INSTANCE_CAPACITY", "NAT"],
        ["POST_STATUS", "STATUS"],
    ],
    "constructors": [
        ["UNIQUE_DIFF_INDEX", ["COUNT_VECTOR", "COUNT_VECTOR"], "INDEX"],
        ["VECTOR_AT", ["COUNT_VECTOR", "INDEX"], "NAT"],
        ["VECTOR_UPDATE", ["COUNT_VECTOR", "INDEX", "NAT"], "COUNT_VECTOR"],
        ["SUM_VECTOR", ["COUNT_VECTOR"], "NAT"],
        ["ADD_ONE", ["NAT"], "NAT"],
        ["MODULO", ["NAT", "NAT"], "NAT"],
        ["SET_INSERT", ["TILE_SET", "TILE_ID"], "TILE_SET"],
        ["GREATER_THAN", ["NAT", "NAT"], "BOOL"],
        ["ALL_REGISTERED_TILES_REMOVED", ["TILE_SET"], "BOOL"],
        ["IF_THEN_ELSE", ["BOOL", "STATUS", "STATUS"], "STATUS"],
    ],
    "numeric_literals_must_be_derived_from_observed_integer_equalities": True,
    "preenumerated_rewrite_thresholds": [],
    "preenumerated_capacity_offsets": [],
    "candidate_program_registry_present": False,
}

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_LMB_DIFFERENCE_GRAMMAR_PREREGISTRATION_V44_DOMAIN,
    "raw_observation": CONSTRUCTION_K7_LMB_RAW_TRANSITION_OBSERVATION_V44_DOMAIN,
    "program": CONSTRUCTION_K7_LMB_DERIVED_TRANSITION_PROGRAM_V44_DOMAIN,
    "distinction": CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_DISTINCTION_V44_DOMAIN,
    "episode": CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_EPISODE_V44_DOMAIN,
    "campaign": CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_CAMPAIGN_V44_DOMAIN,
    "verification": CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_VERIFICATION_V44_DOMAIN,
}


class ConstructionK7LMBDifferenceGrammarPreregistrationV44Error(ValueError):
    """A predecessor, grammar, workload, accounting axis, or claim lock changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LMBDifferenceGrammarPreregistrationV44Error(message)


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.lmb_difference_grammar_preregistration.v44",
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
            "predecessor_identities_preserved": True,
        },
        "source_acquisition": {
            "instance_specification": SOURCE_SPEC,
            "ordered_mode_schedule": list(SOURCE_SCHEDULE),
            "maximum_transition_labels": MAX_SOURCE_TRANSITION_LABELS,
            "policy_inputs": [
                "PUBLIC_STATE",
                "PUBLIC_ACTION_CLASS",
                "LEGAL_ACTION_SET",
                "SELECTED_COUNT_VISIT_COUNTS",
            ],
            "source_generation_witness_access_allowed": False,
            "hidden_solution_sequence_access_allowed": False,
            "candidate_predictions_used_for_action_selection": False,
            "outcome_used_before_action_selection": False,
        },
        "typed_expression_grammar": TYPED_GRAMMAR,
        "required_derivations_from_raw_differences": [
            "OPERATED_COMPONENT_EQUALS_ACTION_PUBLIC_CLASS",
            "REMOVED_SET_INSERTS_ACTION_TILE",
            "REWRITE_CARDINALITY_FROM_WRAP_DIFFERENCE",
            "INCREMENT_MODULO_REWRITE_CARDINALITY",
            "FAILURE_IFF_POST_LOAD_GREATER_THAN_INSTANCE_CAPACITY",
            "SUCCESS_IFF_FULL_REMOVAL_AND_NOT_FAILURE",
            "ACTIVE_OTHERWISE",
        ],
        "heldout_target": {
            "seeds": list(HELDOUT_SEEDS),
            "instance_specification": TARGET_SPEC,
            "tile_count_changed": True,
            "type_count_changed": True,
            "capacity_changed": True,
            "layer_depth_changed": True,
            "generation_witness_access_allowed": False,
            "target_outcome_observed_before_registration": False,
        },
        "planning_and_recovery_protocol": {
            "arms": list(ARMS),
            "receding_horizon": RECEDING_HORIZON,
            "model_only_terminal_feasibility_dynamic_program": True,
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
            "offline_source_transition_labels": "labels",
            "target_local_distinction_labels": "labels",
            "execution_environment_steps": "steps",
            "abstract_transition_evaluations": "compute events",
            "certificate_evaluations": "compute events",
            "grammar_derivation_events": "compute events",
            "peak_dynamic_program_cache_entries": "peak entries",
            "labels_steps_and_compute_may_not_be_collapsed": True,
        },
        "required_positive_conditions": [
            "RAW_DIFFERENCES_COMPILE_ONE_EXACT_TYPED_PROGRAM",
            "NO_PREDECLARED_NUMERIC_PROGRAM_GRID",
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
        "lmb_difference_grammar_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LMBDifferenceGrammarPreregistrationV44:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V44 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V44 preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "lmb_difference_grammar_preregistration_id"
        }
        if (
            document.get("lmb_difference_grammar_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V44 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError("V44 preregistration is not an object")
        return value


def freeze_lmb_difference_grammar_preregistration_v44() -> (
    LMBDifferenceGrammarPreregistrationV44
):
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["lmb_difference_grammar_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V44 preregistration changed")
    return LMBDifferenceGrammarPreregistrationV44(_ISSUER, raw, identity)


def verify_lmb_difference_grammar_preregistration_v44(
    value: LMBDifferenceGrammarPreregistrationV44,
) -> LMBDifferenceGrammarPreregistrationV44:
    if type(value) is not LMBDifferenceGrammarPreregistrationV44:
        _fail("V44 preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("V44 preregistration semantics changed")
    return value


__all__ = (
    "ARMS",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "HELDOUT_SEEDS",
    "LMBDifferenceGrammarPreregistrationV44",
    "PREREGISTRATION_ID",
    "RECEDING_HORIZON",
    "SOURCE_SCHEDULE",
    "SOURCE_SPEC",
    "TARGET_SPEC",
    "TYPED_GRAMMAR",
    "freeze_lmb_difference_grammar_preregistration_v44",
    "verify_lmb_difference_grammar_preregistration_v44",
)
