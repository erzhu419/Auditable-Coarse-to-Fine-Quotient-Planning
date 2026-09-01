"""Outcome-free protocol for the U003 fixed-policy evidence successor.

U002 completed its entire registered training population before its evidence
launcher consumed the U002 evidence-dispatch identity and failed before worker
zero was dispatched.  U003 therefore treats the exact U002 training closure as
read-only predecessor authority and performs a completely fresh measurement of
all 432 frozen policy players.  U003 is not a training retry and never relabels
U002 training artifacts as U003 artifacts.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LEARNED_RESOURCE_FORECAST_EXECUTION_IDENTITY_V1 as U002_EXECUTION_IDENTITY_V1,
    _frozen_payload_v1 as _u002_frozen_payload_v1,
)


LEARNED_RESOURCE_FORECAST_EVIDENCE_SUCCESSOR_PROTOCOL_DOMAIN_V1 = (
    "acfqp:learned-resource-forecast-2048-fixed-policy-evidence-successor:v1"
)
LEARNED_RESOURCE_FORECAST_EVIDENCE_SUCCESSOR_PROTOCOL_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_2048_evidence_successor_protocol.v1"
)
LEARNED_RESOURCE_FORECAST_EVIDENCE_SUCCESSOR_EXECUTION_IDENTITY_V1 = (
    "acfqp-learned-resource-forecast-2048-pilot-u003-ordinal3-attempt1"
)

U002_SOURCE_COMMIT_V1 = "84b021304712cfa7db9e81b4a5e42e541704ba7f"
U002_PROTOCOL_ID_V1 = (
    "399e7af3e69d7b39189cd82d428a1d339ff6fe6be86d189410b113c3a320858f"
)
U002_SOURCE_CHECKOUT_V1 = (
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u002-source"
)
U002_LAUNCH_ROOT_V1 = (
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u002-launch"
)
U002_RESULTS_ROOT_V1 = (
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u002-results"
)
U002_STATUS_ROOT_V1 = (
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u002-status"
)
U002_LOG_ROOT_V1 = (
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u002-logs"
)

MODEL_EVALUATION_TAPE_PREFIX_U003_V1 = (
    "acfqp-learned-resource-forecast-u003-model-evaluation-v1"
)
TRAJECTORY_TAPE_ROOT_U003_V1 = (
    "acfqp-learned-resource-forecast-u003-self-supervised-trajectory-v1"
)
LABEL_TAPE_ROOT_U003_V1 = (
    "acfqp-learned-resource-forecast-u003-skill-label-v1"
)
PROBE_TAPE_ROOT_U003_V1 = (
    "acfqp-learned-resource-forecast-u003-eight-action-probe-v1"
)


class LearnedResourceForecastEvidenceSuccessorProtocolV1Error(ValueError):
    """The fixed U003 design, U002 parent binding, or identity changed."""


def _fail(message: str) -> NoReturn:
    raise LearnedResourceForecastEvidenceSuccessorProtocolV1Error(message)


def _with_identity_v1(payload: dict[str, Any]) -> dict[str, Any]:
    protocol_id = hashlib.sha256(
        LEARNED_RESOURCE_FORECAST_EVIDENCE_SUCCESSOR_PROTOCOL_DOMAIN_V1.encode(
            "ascii"
        )
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()
    return {**payload, "protocol_id": protocol_id}


def predecessor_training_authority_v1() -> dict[str, Any]:
    """Return the exact immutable U002 training authority used by U003."""

    return {
        "protocol_id": U002_PROTOCOL_ID_V1,
        "source_commit": U002_SOURCE_COMMIT_V1,
        "pilot_execution_identity": U002_EXECUTION_IDENTITY_V1,
        "source_checkout": U002_SOURCE_CHECKOUT_V1,
        "source_pythonpath": f"{U002_SOURCE_CHECKOUT_V1}/src",
        "protocol_path": f"{U002_LAUNCH_ROOT_V1}/protocol.json",
        "manifest_path": f"{U002_LAUNCH_ROOT_V1}/launch-manifest.json",
        "training_dispatch_status_path": (
            f"{U002_LAUNCH_ROOT_V1}/training-dispatch.jsonl"
        ),
        "failed_evidence_dispatch_status_path": (
            f"{U002_LAUNCH_ROOT_V1}/evidence-dispatch.jsonl"
        ),
        "results_root": U002_RESULTS_ROOT_V1,
        "status_root": U002_STATUS_ROOT_V1,
        "log_root": U002_LOG_ROOT_V1,
        "completed_training_jobs": 144,
        "model_snapshots": 432,
        "training_worker_status_streams": 6,
        "training_worker_logs": 6,
        "failed_u002_evidence_dispatch_eligible": False,
        "u002_evidence_status_logs_or_artifacts_eligible": False,
        "training_artifacts_are_read_only_inputs": True,
        "training_artifacts_may_be_relabelled_as_u003": False,
    }


def _frozen_payload_v1() -> dict[str, Any]:
    payload = deepcopy(_u002_frozen_payload_v1())
    payload.update(
        {
            "schema": (
                LEARNED_RESOURCE_FORECAST_EVIDENCE_SUCCESSOR_PROTOCOL_SCHEMA_V1
            ),
            "schema_version": "1.0.0",
            "campaign_kind": (
                "LEARNED_RESOURCE_FORECAST_2048_FIXED_POLICY_"
                "EVIDENCE_SUCCESSOR_U003_TEMPLATE"
            ),
            "research_question": (
                "Conditional on the exact completed U002 policy population, can "
                "a label-free representation learned from complete goal-terminated "
                "2048 trajectories add held-out predictive utility to exactly eight "
                "accepted opening actions under wholly fresh measurement tapes?"
            ),
            "source_commit": None,
            "pilot_execution_identity": None,
            "evaluation_tape_prefix": MODEL_EVALUATION_TAPE_PREFIX_U003_V1,
            "trajectory_tape_root": TRAJECTORY_TAPE_ROOT_U003_V1,
            "label_tape_root": LABEL_TAPE_ROOT_U003_V1,
            "probe_tape_root": PROBE_TAPE_ROOT_U003_V1,
            "predecessor_training_authority": predecessor_training_authority_v1(),
            "execution_authorized": False,
            "authorization": (
                "NOT_AUTHORIZED_UNTIL_CLEAN_U003_SOURCE_COMMIT_IS_RATIFIED"
            ),
        }
    )
    tape_roots = (
        payload["training_tape_prefix"],
        payload["evaluation_tape_prefix"],
        payload["trajectory_tape_root"],
        payload["label_tape_root"],
        payload["probe_tape_root"],
    )
    if len(set(tape_roots)) != 5:
        raise AssertionError("U003 parent/fresh tape roots must be pairwise distinct")
    payload["tape_independence_contract"] = {
        "pairwise_distinct_roots": list(tape_roots),
        "training_tape_root_is_read_only_u002_predecessor": True,
        "model_evaluation_trajectory_label_probe_roots_are_fresh_u003": True,
        "u002_evidence_tapes_or_artifacts_reused": False,
        "old_u003_u004_u005_v1_v2_evaluation_tapes_reused": False,
    }
    payload["training"] = {
        **payload["training"],
        "execution_in_this_successor": False,
        "authority": "EXACT_READ_ONLY_U002_TRAINING_CLOSURE",
    }
    payload["policy_population_contract"] = {
        **payload["policy_population_contract"],
        "policy_population_origin": "U002_COMPLETED_TRAINING",
        "training_jobs_are_u003_executions": False,
        "all_432_players_retained_without_outcome_based_selection": True,
    }
    payload["prerequisite_contract"] = {
        **payload["prerequisite_contract"],
        "completed_training_jobs_source": "READ_ONLY_U002_AUTHORITY",
        "model_snapshots_source": "READ_ONLY_U002_AUTHORITY",
        "completed_player_evidence_jobs_source": "FRESH_U003_AUTHORITY",
    }
    payload["fresh_successor_boundary"] = {
        "predecessor_execution_identity": U002_EXECUTION_IDENTITY_V1,
        "predecessor_ordinal": 2,
        "predecessor_attempt": 1,
        "successor_ordinal": 3,
        "successor_attempt": 1,
        "predecessor_training_population_reused_read_only": True,
        "predecessor_training_execution_ids_retried": False,
        "predecessor_failed_evidence_dispatch_identity_retried": False,
        "predecessor_evidence_outputs_reused": False,
        "successor_evidence_execution_ids_are_all_fresh": True,
        "successor_model_evaluation_trajectory_label_probe_tapes_are_all_fresh": (
            True
        ),
        "method_gate_split_classifier_encoder_and_bootstrap_changed": False,
    }
    payload["execution_contract"] = {
        **payload["execution_contract"],
        "phase_roster": ["evidence"],
        "policy_training_execution_id_template": None,
        "parent_policy_training_execution_id_template": (
            "{parent_pilot_execution_identity}:policy-training:{arm}:seed:{seed}"
        ),
        "parent_snapshot_input_and_successor_evidence_output_are_separate": True,
        "parent_training_closure_must_pass_before_global_preflight": True,
        "successor_evidence_output_root_must_be_fresh": True,
        "u002_failed_evidence_dispatch_is_ineligible": True,
    }
    payload["claim_boundary"] = {
        **payload["claim_boundary"],
        "fresh_exploratory_pilot_only": True,
        "fixed_u002_policy_population_conditional_estimand_only": True,
        "new_training_randomness_confirmed": False,
        "positive_result_authorizes_only_new_training_seed_confirmatory_successor": (
            True
        ),
    }
    return payload


def build_learned_resource_forecast_evidence_successor_template_v1() -> dict[str, Any]:
    """Return the complete U003 design without execution authority."""

    return _with_identity_v1(_frozen_payload_v1())


def build_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
    source_commit: str,
) -> dict[str, Any]:
    """Bind the fixed evidence-only design to one clean U003 source commit."""

    if (
        type(source_commit) is not str
        or re.fullmatch(r"[0-9a-f]{40}", source_commit) is None
    ):
        _fail("U003 ratification source commit must be one lowercase full object ID")
    payload = _frozen_payload_v1()
    payload["campaign_kind"] = (
        "LEARNED_RESOURCE_FORECAST_2048_FIXED_POLICY_"
        "EVIDENCE_SUCCESSOR_U003_RATIFIED"
    )
    payload["source_commit"] = source_commit
    payload["pilot_execution_identity"] = (
        LEARNED_RESOURCE_FORECAST_EVIDENCE_SUCCESSOR_EXECUTION_IDENTITY_V1
    )
    payload["execution_authorized"] = True
    payload["authorization"] = (
        "RATIFIED_FOR_FIXED_POLICY_EXPLORATORY_EVIDENCE_EXECUTION"
    )
    payload["pilot_protocol_ratified"] = True
    return _with_identity_v1(payload)


def validate_learned_resource_forecast_evidence_successor_protocol_identity_v1(
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay one canonical U003 protocol identity without granting authority."""

    if type(protocol) is not dict:
        _fail("U003 evidence-successor protocol must be a plain object")
    protocol_id = protocol.get("protocol_id")
    if (
        type(protocol_id) is not str
        or re.fullmatch(r"[0-9a-f]{64}", protocol_id) is None
    ):
        _fail("U003 evidence-successor protocol identity changed shape")
    payload = dict(protocol)
    del payload["protocol_id"]
    if _with_identity_v1(payload)["protocol_id"] != protocol_id:
        _fail("U003 evidence-successor protocol identity is not replayable")
    return dict(protocol)


def validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    """Accept only the exact U003 design bound to its clean source commit."""

    replayed = (
        validate_learned_resource_forecast_evidence_successor_protocol_identity_v1(
            protocol
        )
    )
    source_commit = replayed.get("source_commit")
    if type(source_commit) is not str:
        _fail("ratified U003 evidence-successor protocol has no source commit")
    expected = (
        build_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
            source_commit
        )
    )
    if replayed != expected:
        _fail("ratified U003 evidence-successor protocol differs from frozen design")
    return replayed


__all__ = (
    "LABEL_TAPE_ROOT_U003_V1",
    "LEARNED_RESOURCE_FORECAST_EVIDENCE_SUCCESSOR_EXECUTION_IDENTITY_V1",
    "LEARNED_RESOURCE_FORECAST_EVIDENCE_SUCCESSOR_PROTOCOL_DOMAIN_V1",
    "LEARNED_RESOURCE_FORECAST_EVIDENCE_SUCCESSOR_PROTOCOL_SCHEMA_V1",
    "LearnedResourceForecastEvidenceSuccessorProtocolV1Error",
    "MODEL_EVALUATION_TAPE_PREFIX_U003_V1",
    "PROBE_TAPE_ROOT_U003_V1",
    "TRAJECTORY_TAPE_ROOT_U003_V1",
    "U002_EXECUTION_IDENTITY_V1",
    "U002_LOG_ROOT_V1",
    "U002_PROTOCOL_ID_V1",
    "U002_RESULTS_ROOT_V1",
    "U002_SOURCE_CHECKOUT_V1",
    "U002_SOURCE_COMMIT_V1",
    "U002_STATUS_ROOT_V1",
    "build_learned_resource_forecast_evidence_successor_template_v1",
    "build_ratified_learned_resource_forecast_evidence_successor_protocol_v1",
    "predecessor_training_authority_v1",
    "validate_learned_resource_forecast_evidence_successor_protocol_identity_v1",
    "validate_ratified_learned_resource_forecast_evidence_successor_protocol_v1",
)
