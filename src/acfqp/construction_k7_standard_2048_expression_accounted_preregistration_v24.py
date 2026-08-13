"""Outcome-free measurement Gate for end-to-end V22/V23 actual accounting."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_standard_2048_blind_expression_preregistration_v22 as v22
from acfqp import construction_k7_standard_2048_expression_long_preregistration_v23 as v23
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_CAMPAIGN_V24_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_COUNTER_BUNDLE_V24_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_DECISION_V24_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_EPISODE_V24_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_MEASUREMENT_V24_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_PREREGISTRATION_V24_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_VERIFICATION_V24_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "24.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.183"
PROFILE_KEY = "construction_k7_standard_2048_expression_actual_accounting_v24"
PREREGISTRATION_ID = "122fe5ae5121bc55bebafbac1208810c29b9486924985457f6636de2f9e4979d"
EXPECTED_CANONICAL_BYTE_COUNT = 211688
EXPECTED_CANONICAL_SHA256 = "17e8d3f941d2ac15652e0775dc88397dfff0642ca6fe1d9242104289ff4d6e18"
EPISODE_WORKER_WORKING_BYTES_PEAK_UPPER = 4 * 1024 * 1024 * 1024
CAMPAIGN_PARENT_WORKING_BYTES_PEAK_UPPER = 4 * 1024 * 1024 * 1024
V22_CAMPAIGN_ID = "85a0f59d0751dfcad87517ed8167d66943d4be0ab9159f78aeaaef7f85923c3e"
V22_VERIFICATION_ID = "6b60d2e7d4585716784a6b9a93c7511f96de2f4742ada0d61d6e1ec78aa2e7b2"
V23_CAMPAIGN_ID = "cd198082b21cd1d6365f17081669bbdeac1172ac3da8247b68db4b649a3b0660"
V23_VERIFICATION_ID = "acecc64e9ffe625a1780c49a85fd1bcc256999e9d15adb0f2cb52afbd0ca4b57"

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_PREREGISTRATION_V24_DOMAIN,
    "measurement": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_MEASUREMENT_V24_DOMAIN,
    "counter_bundle": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_COUNTER_BUNDLE_V24_DOMAIN,
    "decision": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_DECISION_V24_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_EPISODE_V24_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_CAMPAIGN_V24_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_VERIFICATION_V24_DOMAIN,
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
MODEL_EVALUATION_PATHS = tuple(
    "evaluation." + path.removeprefix("model.") for path in MODEL_OPERATIONAL_PATHS
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


class ConstructionK7Standard2048ExpressionAccountedPreregistrationV24Error(ValueError):
    """The measured predecessor, registry, workload, or claim lock changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionAccountedPreregistrationV24Error(message)


def _document() -> dict[str, Any]:
    frozen = registry_v9.freeze_construction_accounting_registry_v9()
    registry = registry_v9.official_counter_registry_v9()
    if tuple(sorted(MODEL_OPERATIONAL_PATHS)) != MODEL_OPERATIONAL_PATHS:
        _fail("model operational path order changed")
    if any(path not in registry.by_path for path in (*MODEL_OPERATIONAL_PATHS, *MODEL_EVALUATION_PATHS)):
        _fail("model accounting path is not registered")
    payload = {
        "schema": "acfqp.standard_2048_expression_accounted_preregistration.v24",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "measurement_predecessors": {
            "v22_expression_synthesis_campaign_id": V22_CAMPAIGN_ID,
            "v22_independent_verification_id": V22_VERIFICATION_ID,
            "v23_long_reuse_campaign_id": V23_CAMPAIGN_ID,
            "v23_independent_verification_id": V23_VERIFICATION_ID,
            "measurement_replays_already_revealed_target": True,
            "fresh_blind_scientific_confirmation_claimed": False,
            "predecessor_artifacts_relabelled_as_actual_counters": False,
        },
        "frozen_registry_profiles": frozen,
        "registered_model_synthesis_windows": [
            {
                "window": "MODEL_ACQUISITION_AND_SELECTION",
                "allowed_nonzero_paths": list(MODEL_OPERATIONAL_PATHS[:2])
                + list(MODEL_OPERATIONAL_PATHS[3:7]),
                "target_probability_label_cap": v22.MAXIMUM_TARGET_PROBABILITY_QUERIES,
                "structural_context_row_count": len(v22.RAW_CONTEXT_POOL),
                "primitive_expression_count_per_context": 28,
                "expression_candidate_cap": 80,
                "candidate_label_consistency_check_cap": 320,
                "active_query_partition_evaluation_cap": 2560,
            },
            {
                "window": "MODEL_PROOF_AND_FREEZE",
                "allowed_nonzero_paths": [
                    "model.exact_program_proof_rows_evaluated",
                    "model.world_model_freezes",
                ],
                "exact_program_proof_row_cap": 17,
                "world_model_freeze_cap": 1,
            },
        ],
        "registered_long_reuse_workload": {
            "initial_boards": [list(board) for board in v23.INITIAL_BOARDS],
            "episode_seeds": list(v23.EPISODE_SEEDS),
            "episode_count": len(v23.INITIAL_BOARDS),
            "planning_horizon": v23.PLANNING_HORIZON,
            "maximum_decisions_per_episode": v23.MAXIMUM_DECISIONS_PER_EPISODE,
            "maximum_decision_count": len(v23.INITIAL_BOARDS) * v23.MAXIMUM_DECISIONS_PER_EPISODE,
            "cold_evaluation_checkpoint_indices": list(v23.COLD_EVALUATION_CHECKPOINTS),
            "maximum_evaluation_work_vector_count": (
                len(v23.INITIAL_BOARDS) * len(v23.COLD_EVALUATION_CHECKPOINTS)
            ),
            "early_terminal_closure_allowed": True,
        },
        "actual_accounting_protocol": {
            "counter_registry_id": registry.registry_id,
            "stage_profile_id": frozen["stage_profile"]["stage_profile_id"],
            "comparison_profile_id": frozen["comparison_profile"]["comparison_profile_id"],
            "actual_projection_profile_id": frozen["actual_projection_profile"]["actual_projection_profile_id"],
            "model_operational_paths": list(MODEL_OPERATIONAL_PATHS),
            "model_evaluation_paths": list(MODEL_EVALUATION_PATHS),
            "shared_resource_paths": list(SHARED_RESOURCE_PATHS),
            "every_required_leaf_emitted_with_native_zero": True,
            "operational_model_synthesis_planning_and_execution_are_costed": True,
            "standalone_independent_replay_is_evaluation_only": True,
            "output_bytes_use_fixed_point_materialization": True,
            "peak_capacity_and_additive_traffic_remain_separate": True,
            "legacy_summary_to_actual_counter_translation_allowed": False,
            "episode_worker_working_bytes_peak_upper": EPISODE_WORKER_WORKING_BYTES_PEAK_UPPER,
            "campaign_parent_working_bytes_peak_upper": CAMPAIGN_PARENT_WORKING_BYTES_PEAK_UPPER,
            "working_byte_cap_frozen_before_execution": True,
            "observed_ru_maxrss_must_not_exceed_frozen_cap": True,
            "transient_ru_maxrss_not_used_as_content_identity": True,
        },
        "required_positive_conditions": [
            "V22_MODEL_SYNTHESIS_IS_RERUN_UNDER_NATIVE_COUNTER_WINDOWS",
            "V23_LONG_REUSE_IS_RERUN_UNDER_NATIVE_COUNTER_WINDOWS",
            "EVERY_OPERATIONAL_LEAF_PROJECTS_EXACTLY_ONCE",
            "EVALUATION_REPLAY_DOES_NOT_ENTER_OPERATIONAL_COMPARISON",
            "NINE_SHARED_RESOURCE_PATHS_HAVE_NATIVE_MEASUREMENTS",
        ],
        "outcome_fields_present": False,
        "model_synthesis_execution_performed": False,
        "long_reuse_execution_performed": False,
        "counter_records_issued": False,
        "work_vectors_issued": False,
        "comparison_vectors_issued": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "expression_accounted_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ExpressionAccountedPreregistrationV24:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("accounting preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("accounting preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "expression_accounted_preregistration_id"
        }
        if (
            document.get("expression_accounted_preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload) != self.preregistration_id
        ):
            _fail("accounting preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("accounting preregistration is not an object")
        return document


def freeze_standard_2048_expression_accounted_preregistration_v24(
) -> Standard2048ExpressionAccountedPreregistrationV24:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["expression_accounted_preregistration_id"]
    if (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen accounting preregistration identity changed")
    return Standard2048ExpressionAccountedPreregistrationV24(
        _ISSUER, raw, identity
    )


def verify_standard_2048_expression_accounted_preregistration_v24(
    value: Standard2048ExpressionAccountedPreregistrationV24,
) -> Standard2048ExpressionAccountedPreregistrationV24:
    if type(value) is not Standard2048ExpressionAccountedPreregistrationV24:
        _fail("accounting preregistration verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("accounting preregistration differs from frozen semantics")
    return value


__all__ = (
    "CAMPAIGN_PARENT_WORKING_BYTES_PEAK_UPPER",
    "EPISODE_WORKER_WORKING_BYTES_PEAK_UPPER",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "MODEL_EVALUATION_PATHS",
    "MODEL_OPERATIONAL_PATHS",
    "PREREGISTRATION_ID",
    "SHARED_RESOURCE_PATHS",
    "Standard2048ExpressionAccountedPreregistrationV24",
    "freeze_standard_2048_expression_accounted_preregistration_v24",
    "verify_standard_2048_expression_accounted_preregistration_v24",
)
