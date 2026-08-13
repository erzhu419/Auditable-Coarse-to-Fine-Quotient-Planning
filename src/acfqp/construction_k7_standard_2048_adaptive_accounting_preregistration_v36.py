"""Outcome-free native-accounting registration for the V35 adaptive campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_CAMPAIGN_V36_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_COUNTER_BUNDLE_V36_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_MEASUREMENT_V36_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_PREREGISTRATION_V36_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_VERIFICATION_V36_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "36.1.0"
PROPOSED_CONTRACT_VERSION = "2.0.196"
PROFILE_KEY = "construction_k7_standard_2048_adaptive_expression_actual_accounting_v36r1"
PREREGISTRATION_ID = "b74c33f607b3a6523a1ec341a0bd059f94edc251bab35f003233e63488815dde"
EXPECTED_CANONICAL_BYTE_COUNT = 215_334
EXPECTED_CANONICAL_SHA256 = "0dd9fd2ffec819ba39529f6ec2a627b5bca19937d5e4b01be98d42200cb997dd"
SUPERSEDED_V36_PREREGISTRATION_ID = (
    "b6d209f4a0e285653349a66293c21597b39dcd1f74c95fbd69d9e3e439accb65"
)
V34R1_PREREGISTRATION_ID = (
    "4546af82f1f4e6429c83148b0f37f9a3995b80e9a0bb4abc2971ada13b115920"
)
V35_PREREGISTRATION_ID = (
    "d2705f1b310b2f88f41799376a69f55b3355b53a54a2a103ba11e5dbf00491a9"
)
MAXIMUM_WORKER_PROCESSES = 2
MAXIMUM_TASKS_PER_WORKER_PROCESS = 1
MAXIMUM_EPISODES = 4
MAXIMUM_DECISIONS_PER_EPISODE = 128
MAXIMUM_TARGET_PROBABILITY_LABELS = 12
MAXIMUM_COLD_CHECKPOINTS = 12
WORKER_WORKING_BYTES_PEAK_UPPER = 24 * 1024 * 1024 * 1024
PARENT_WORKING_BYTES_PEAK_UPPER = 4 * 1024 * 1024 * 1024
MAXIMUM_ACCOUNTING_OUTPUT_BYTES = 2 * 1024 * 1024 * 1024

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_PREREGISTRATION_V36_DOMAIN,
    "measurement": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_MEASUREMENT_V36_DOMAIN,
    "counter_bundle": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_COUNTER_BUNDLE_V36_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_CAMPAIGN_V36_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_VERIFICATION_V36_DOMAIN,
}

MODEL_OPERATIONAL_PATHS = (
    "model.active_query_partition_evaluations",
    "model.candidate_label_consistency_checks",
    "model.exact_program_proof_rows_evaluated",
    "model.expression_candidates_materialized",
    "model.structural_context_rows_frozen",
    "model.structural_expression_value_evaluations",
    "model.target_probability_labels_acquired",
    "model.world_model_freezes",
)
PLANNING_OPERATIONAL_PATHS = (
    "common.abstract_bellman_backups",
    "common.abstract_support_outcome_evaluations",
    "common.abstract_subproof_cache_lookups",
    "common.abstract_subproof_cache_hits",
    "common.abstract_subproof_cache_misses",
    "target.execution_ground_steps",
    "target.execution_outcome_rows",
    "target.transition_observations",
)
EVALUATION_PATHS = (
    "evaluation.active_query_partition_evaluations",
    "evaluation.candidate_label_consistency_checks",
    "evaluation.exact_actions_evaluated",
    "evaluation.exact_bellman_backups",
    "evaluation.exact_ground_steps",
    "evaluation.exact_outcome_rows",
    "evaluation.exact_program_proof_rows_evaluated",
    "evaluation.exact_states_expanded",
    "evaluation.exact_subproof_cache_hits",
    "evaluation.exact_subproof_cache_lookups",
    "evaluation.exact_subproof_cache_misses",
    "evaluation.expression_candidates_materialized",
    "evaluation.structural_context_rows_frozen",
    "evaluation.structural_expression_value_evaluations",
    "evaluation.target_probability_labels_acquired",
    "evaluation.world_model_freezes",
)
SHARED_RESOURCE_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)


class ConstructionK7Standard2048AdaptiveAccountingPreregistrationV36Error(
    ValueError
):
    """The adaptive-accounting protocol, predecessor, or claim lock changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AdaptiveAccountingPreregistrationV36Error(
        message
    )


def _stage_plan() -> list[dict[str, Any]]:
    return [
        {
            "stage": "CERTIFICATE_FAILURE_FRONTIER_FREEZE",
            "lane": "OPERATIONAL",
            "cardinality": 1,
            "counter_paths": ["model.structural_context_rows_frozen"],
            "target_probability_access_allowed": False,
        },
        {
            "stage": "ADAPTIVE_LABEL_ACQUISITION_AND_CANDIDATE_ELIMINATION",
            "lane": "OPERATIONAL",
            "cardinality": {
                "kind": "POST_V35_EXACT_COUNT_AT_MOST",
                "upper": MAXIMUM_TARGET_PROBABILITY_LABELS,
            },
            "counter_paths": list(MODEL_OPERATIONAL_PATHS),
            "query_must_reference_previously_failed_frontier": True,
        },
        {
            "stage": "EXPRESSION_PROPOSAL_FREEZE",
            "lane": "OPERATIONAL",
            "cardinality": 1,
            "counter_paths": [],
            "proposal_must_precede_target_semantics_reveal": True,
        },
        {
            "stage": "EXACT_PROGRAM_PROOF",
            "lane": "OPERATIONAL",
            "cardinality": 1,
            "counter_paths": ["model.exact_program_proof_rows_evaluated"],
            "proposal_must_precede_target_semantics_reveal": True,
        },
        {
            "stage": "PROVED_OVERLAY_FREEZE",
            "lane": "OPERATIONAL",
            "cardinality": 1,
            "counter_paths": ["model.world_model_freezes"],
            "proof_must_precede_overlay_authority": True,
        },
        {
            "stage": "EPISODE_ABSTRACT_PLANNING_AND_CERTIFICATION",
            "lane": "OPERATIONAL",
            "cardinality": MAXIMUM_EPISODES,
            "counter_paths": [
                path
                for path in PLANNING_OPERATIONAL_PATHS
                if not path.startswith("target.")
            ],
            "one_occurrence_per_worker_process": True,
        },
        {
            "stage": "EPISODE_SELECTED_TARGET_EXECUTION",
            "lane": "OPERATIONAL",
            "cardinality": MAXIMUM_EPISODES,
            "counter_paths": [
                path
                for path in PLANNING_OPERATIONAL_PATHS
                if path.startswith("target.")
            ],
            "certificate_must_freeze_before_target_execution": True,
        },
        {
            "stage": "MATCHED_FIRST_FRONTIER_NO_PRIOR_CONTROL",
            "lane": "EVALUATION",
            "cardinality": 1,
            "counter_paths": [
                "evaluation.target_probability_labels_acquired",
                "evaluation.semantic_integrity_checks",
                "evaluation.semantic_protocol_checks",
            ],
            "may_modify_operational_overlay": False,
        },
        {
            "stage": "COLD_EXACT_GROUND_CHECKPOINT_REPLAY",
            "lane": "EVALUATION",
            "cardinality": {
                "kind": "POST_V35_EXACT_COUNT_AT_MOST",
                "upper": MAXIMUM_COLD_CHECKPOINTS,
            },
            "counter_paths": list(EVALUATION_PATHS),
            "may_enter_operational_comparison": False,
        },
        {
            "stage": "PROCESS_AND_IO_SUPERVISION",
            "lane": "OPERATIONAL_AND_EVALUATION_SEPARATED",
            "cardinality": {
                "kind": "DERIVED_FROM_EXACT_STAGE_INVENTORY",
                "upper": 32,
            },
            "counter_paths": list(SHARED_RESOURCE_PATHS),
            "fixed_point_output_bytes_required": True,
        },
    ]


def _document() -> dict[str, Any]:
    profiles = registry_v9.freeze_construction_accounting_registry_v9()
    registry = registry_v9.official_counter_registry_v9()
    registered_paths = {
        *MODEL_OPERATIONAL_PATHS,
        *PLANNING_OPERATIONAL_PATHS,
        *EVALUATION_PATHS,
        *SHARED_RESOURCE_PATHS,
    }
    if not registered_paths.issubset(registry.by_path):
        _fail("V36 accounting path is absent from CounterRegistryV9")
    payload = {
        "schema": "acfqp.standard_2048_adaptive_accounting_preregistration.v36",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "stage_separation_contract_correction": {
            "superseded_v36_preregistration_id": (
                SUPERSEDED_V36_PREREGISTRATION_ID
            ),
            "superseded_preregistration_executed": False,
            "outcomes_known_when_corrected": False,
            "scientific_target_or_workload_changed": False,
            "correction": (
                "SEPARATE_FAILURE_ACQUISITION_PROPOSAL_PROOF_OVERLAY_"
                "PLANNING_AND_EXECUTION_NATIVE_WINDOWS"
            ),
            "partial_superseded_bundles_may_be_reused": False,
        },
        "frozen_predecessors": {
            "v34r1_accounting_preregistration_id": V34R1_PREREGISTRATION_ID,
            "v34r1_accounted_campaign_id": {
                "kind": "PENDING_PREEXECUTION_BINDING",
                "reason": "V34R1_REGISTERED_EXECUTION_ACTIVE_AT_V36_FREEZE",
            },
            "v34r1_accounting_verification_id": {
                "kind": "PENDING_PREEXECUTION_BINDING",
                "reason": "V34R1_INDEPENDENT_VERIFICATION_REQUIRED_BEFORE_V35",
            },
            "v35_adaptive_expression_preregistration_id": V35_PREREGISTRATION_ID,
            "v35_adaptive_expression_campaign_id": {
                "kind": "PENDING_POSTEXECUTION_BINDING",
                "reason": "V35_HAS_NOT_EXECUTED_AT_V36_FREEZE",
            },
            "v35_adaptive_expression_verification_id": {
                "kind": "PENDING_POSTEXECUTION_BINDING",
                "reason": "V35_SEMANTIC_REPLAY_MUST_PRECEDE_V36_ACCOUNTING",
            },
            "V35_execution_may_start_only_after_verified_V34r1": True,
            "V36_accounting_may_start_only_after_verified_V35": True,
        },
        "registered_workload": {
            "logical_occurrence_count": MAXIMUM_EPISODES,
            "planning_horizon": 3,
            "maximum_decisions_per_episode": MAXIMUM_DECISIONS_PER_EPISODE,
            "maximum_total_decisions": (
                MAXIMUM_EPISODES * MAXIMUM_DECISIONS_PER_EPISODE
            ),
            "maximum_target_probability_labels": MAXIMUM_TARGET_PROBABILITY_LABELS,
            "maximum_cold_evaluation_checkpoints": MAXIMUM_COLD_CHECKPOINTS,
            "early_terminal_closure_allowed": True,
            "all_terminal_occurrences_remain_in_denominator": True,
            "scientific_workload_must_equal_verified_V35_bytes": True,
        },
        "frozen_registry_profiles": profiles,
        "registered_stage_plan": _stage_plan(),
        "actual_accounting_protocol": {
            "counter_registry_id": registry.registry_id,
            "stage_profile_id": profiles["stage_profile"]["stage_profile_id"],
            "comparison_profile_id": profiles["comparison_profile"][
                "comparison_profile_id"
            ],
            "actual_projection_profile_id": profiles[
                "actual_projection_profile"
            ]["actual_projection_profile_id"],
            "model_operational_paths": list(MODEL_OPERATIONAL_PATHS),
            "planning_operational_paths": list(PLANNING_OPERATIONAL_PATHS),
            "evaluation_paths": list(EVALUATION_PATHS),
            "shared_resource_paths": list(SHARED_RESOURCE_PATHS),
            "fresh_native_counter_window_required_for_every_stage": True,
            "all_required_leaves_emit_native_zero": True,
            "output_bytes_use_fixed_point_materialization": True,
            "evaluation_lane_excluded_from_operational_comparison": True,
            "summary_to_counter_translation_allowed": False,
            "maximum_worker_processes": MAXIMUM_WORKER_PROCESSES,
            "maximum_tasks_per_worker_process": MAXIMUM_TASKS_PER_WORKER_PROCESS,
            "worker_working_bytes_peak_upper": WORKER_WORKING_BYTES_PEAK_UPPER,
            "parent_working_bytes_peak_upper": PARENT_WORKING_BYTES_PEAK_UPPER,
            "maximum_accounting_output_bytes": MAXIMUM_ACCOUNTING_OUTPUT_BYTES,
            "resource_caps_frozen_before_execution": True,
        },
        "required_positive_conditions": [
            "V34R1_ACCOUNTING_AND_V35_SEMANTICS_VERIFY_BEFORE_ACCOUNTING",
            "FAILURE_ACQUISITION_PROPOSAL_PROOF_OVERLAY_AND_EXECUTION_ARE_SEPARATE",
            "EVERY_OPERATIONAL_LEAF_PROJECTS_EXACTLY_ONCE",
            "ALL_NINE_SHARED_RESOURCE_PATHS_HAVE_NATIVE_MEASUREMENT_RECEIPTS",
            "EVERY_WORKER_PROCESS_EXECUTES_EXACTLY_ONE_OCCURRENCE",
            "EVALUATION_CONTROL_AND_COLD_REPLAY_NEVER_ENTER_OPERATIONAL_COMPARISON",
            "COUNTER_RECORD_WORK_VECTOR_COMPARISON_VECTOR_CHAIN_REPLAYS",
        ],
        "outcome_fields_present": False,
        "accounting_execution_performed": False,
        "counter_records_issued": False,
        "work_vectors_issued": False,
        "comparison_vectors_issued": False,
        "automatic_reusable_world_model_goal_completed": False,
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
        "adaptive_accounting_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048AdaptiveAccountingPreregistrationV36:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("adaptive-accounting preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
        ):
            _fail("adaptive-accounting preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "adaptive_accounting_preregistration_id"
        }
        if (
            document.get("adaptive_accounting_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("adaptive-accounting preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("adaptive-accounting preregistration is not an object")
        return document


def freeze_standard_2048_adaptive_accounting_preregistration_v36(
) -> Standard2048AdaptiveAccountingPreregistrationV36:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["adaptive_accounting_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen adaptive-accounting preregistration changed")
    return Standard2048AdaptiveAccountingPreregistrationV36(
        _ISSUER, raw, identity
    )


def verify_standard_2048_adaptive_accounting_preregistration_v36(
    value: Standard2048AdaptiveAccountingPreregistrationV36,
) -> Standard2048AdaptiveAccountingPreregistrationV36:
    if type(value) is not Standard2048AdaptiveAccountingPreregistrationV36:
        _fail("adaptive-accounting preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("adaptive-accounting preregistration semantics changed")
    return value


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "MODEL_OPERATIONAL_PATHS",
    "PLANNING_OPERATIONAL_PATHS",
    "PREREGISTRATION_ID",
    "SHARED_RESOURCE_PATHS",
    "SUPERSEDED_V36_PREREGISTRATION_ID",
    "Standard2048AdaptiveAccountingPreregistrationV36",
    "freeze_standard_2048_adaptive_accounting_preregistration_v36",
    "verify_standard_2048_adaptive_accounting_preregistration_v36",
)
