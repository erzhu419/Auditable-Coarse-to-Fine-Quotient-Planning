"""Outcome-free U005 analysis-only successor for the completed U004 evidence.

U005 repairs one missing import in the analysis program.  It does not create or
retry training or evidence executions.  The completed U002 policy population
and gathered U004 evidence are immutable read-only authorities, while only the
analysis, independent verification, status, and retention products are U005.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.learned_resource_forecast_evidence_successor_protocol_v1 import (
    LEARNED_RESOURCE_FORECAST_EVIDENCE_SUCCESSOR_EXECUTION_IDENTITY_V1,
    build_ratified_learned_resource_forecast_evidence_successor_protocol_v1,
)


PROTOCOL_DOMAIN_V1 = (
    "acfqp:learned-resource-forecast-2048-analysis-only-successor-u005:v1"
)
PROTOCOL_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_2048_analysis_successor_u005_protocol.v1"
)
EXECUTION_IDENTITY_V1 = (
    "acfqp-learned-resource-forecast-2048-pilot-u005-ordinal5-attempt1"
)
ANALYSIS_EXECUTION_ID_V1 = f"{EXECUTION_IDENTITY_V1}:analysis-postprocess"

U004_SOURCE_COMMIT_V1 = "8b47768cfa1287974029ce97c1dfc542d3607dbd"
U004_PROTOCOL_ID_V1 = (
    "f119417433ab07ac9a765841b1c7ed25b7beac0ea3e1a935ed16f64641150728"
)
U004_SOURCE_CHECKOUT_V1 = (
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u004-source"
)
U004_LAUNCH_ROOT_V1 = (
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u004-launch"
)
U004_RESULTS_ROOT_V1 = (
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u004-results"
)
U004_STATUS_ROOT_V1 = (
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u004-status"
)
U004_LOG_ROOT_V1 = (
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u004-logs"
)
U004_ANALYSIS_ROOT_V1 = (
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u004-analysis"
)
U004_RETAINED_ROOT_V1 = (
    "/home/erzhu419/mine_code/"
    "acfqp-learned-resource-forecast-2048-pilot-u004-retained"
)

ANALYSIS_CONTRACT_KEYS_V1 = (
    "training_seed_split",
    "representation_arms",
    "representation_dimensions",
    "raw_prefix_contract",
    "forecast_encoder_contract",
    "classifier_contract",
    "bootstrap_contract",
    "provisional_design_signal_contract",
)
ANALYSIS_OUTPUT_FILENAMES_V1 = (
    "aligned-resource-forecast.encoder.pt",
    "player-shuffled-resource-forecast.encoder.pt",
    "aligned-resource-forecast.receipt.json",
    "player-shuffled-resource-forecast.receipt.json",
    "probe-representation-matrices.npz",
    "probe-representation-matrices.metadata.json",
    "pilot-result.json",
    "independent-verification.json",
    "analysis-successor-receipt.json",
)


class LearnedResourceForecastAnalysisSuccessorProtocolV1Error(ValueError):
    """The U005 analysis identity, authority, or frozen method changed."""


def _fail(message: str) -> NoReturn:
    raise LearnedResourceForecastAnalysisSuccessorProtocolV1Error(message)


def _with_identity_v1(payload: dict[str, Any]) -> dict[str, Any]:
    protocol_id = hashlib.sha256(
        PROTOCOL_DOMAIN_V1.encode("ascii")
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()
    return {**payload, "protocol_id": protocol_id}


def u004_evidence_protocol_v1() -> dict[str, Any]:
    protocol = build_ratified_learned_resource_forecast_evidence_successor_protocol_v1(
        U004_SOURCE_COMMIT_V1
    )
    if (
        protocol["protocol_id"] != U004_PROTOCOL_ID_V1
        or protocol["pilot_execution_identity"]
        != LEARNED_RESOURCE_FORECAST_EVIDENCE_SUCCESSOR_EXECUTION_IDENTITY_V1
    ):
        raise AssertionError("frozen U004 evidence authority changed")
    return protocol


def frozen_analysis_contract_v1() -> dict[str, Any]:
    """Copy the exact U004 split, representations, estimator, and Gate."""

    u004 = u004_evidence_protocol_v1()
    return {key: deepcopy(u004[key]) for key in ANALYSIS_CONTRACT_KEYS_V1}


def _frozen_payload_v1() -> dict[str, Any]:
    u004 = u004_evidence_protocol_v1()
    return {
        "schema": PROTOCOL_SCHEMA_V1,
        "schema_version": "1.0.0",
        "campaign_kind": "LEARNED_RESOURCE_FORECAST_ANALYSIS_ONLY_SUCCESSOR_U005_TEMPLATE",
        "research_question": (
            "With U002 training and completed gathered U004 evidence fixed read-only, "
            "what is the unchanged preregistered U004 provisional design-signal result "
            "after correcting the analysis program's missing symbol import?"
        ),
        "source_commit": None,
        "pilot_execution_identity": None,
        "analysis_execution_id": None,
        "predecessor_training_authority": deepcopy(
            u004["predecessor_training_authority"]
        ),
        "predecessor_evidence_authority": {
            "protocol_id": U004_PROTOCOL_ID_V1,
            "source_commit": U004_SOURCE_COMMIT_V1,
            "pilot_execution_identity": (
                LEARNED_RESOURCE_FORECAST_EVIDENCE_SUCCESSOR_EXECUTION_IDENTITY_V1
            ),
            "source_checkout": U004_SOURCE_CHECKOUT_V1,
            "protocol_path": f"{U004_LAUNCH_ROOT_V1}/protocol.json",
            "manifest_path": f"{U004_LAUNCH_ROOT_V1}/launch-manifest.json",
            "history_scan_receipt_path": (
                f"{U004_LAUNCH_ROOT_V1}/history-scan-receipt.json"
            ),
            "gather_transport_marker_path": (
                f"{U004_LAUNCH_ROOT_V1}/gather-transport-marker.json"
            ),
            "gather_receipt_path": f"{U004_LAUNCH_ROOT_V1}/gather-receipt.json",
            "failed_postprocess_status_path": (
                f"{U004_LAUNCH_ROOT_V1}/postprocess-status.jsonl"
            ),
            "results_root": U004_RESULTS_ROOT_V1,
            "status_root": U004_STATUS_ROOT_V1,
            "log_root": U004_LOG_ROOT_V1,
            "failed_analysis_root": U004_ANALYSIS_ROOT_V1,
            "uncreated_retained_root": U004_RETAINED_ROOT_V1,
            "completed_evidence_jobs": 432,
            "failed_evidence_jobs": 0,
            "completed_evidence_workers": 6,
            "gather_completed": True,
            "evidence_artifacts_are_read_only_inputs": True,
            "evidence_execution_ids_retried_in_u005": False,
            "evidence_measurement_reexecuted_in_u005": False,
        },
        "frozen_analysis_contract": frozen_analysis_contract_v1(),
        "analysis_output_filenames": list(ANALYSIS_OUTPUT_FILENAMES_V1),
        "failure_successor_boundary": {
            "u004_postprocess_identity_consumed": True,
            "u004_failure_stage": "FIT_ENCODERS",
            "u004_failure_kind": "NameError",
            "u004_failure_message": (
                "name 'aligned_forecast_examples_v1' is not defined"
            ),
            "u004_analysis_artifact_count": 0,
            "u004_retention_completed": False,
            "u004_postprocess_retried": False,
            "code_change": (
                "IMPORT_EXISTING_ALIGNED_FORECAST_EXAMPLES_V1_INTO_FROZEN_"
                "NUMERIC_ANALYSIS_PROGRAM"
            ),
        },
        "execution_contract": {
            "phase_roster": ["analysis", "independent_verification", "retention"],
            "analysis_runs_once_on_central_host": True,
            "new_training_execution_ids": [],
            "new_evidence_execution_ids": [],
            "new_tape_roots": [],
            "training_reexecuted": False,
            "evidence_reexecuted": False,
            "new_policy_or_evidence_measurement_executed": False,
            "existing_u004_evidence_transition_replay": True,
            "transition_replay_is_validation_not_new_measurement": True,
            "same_identity_retry_allowed": False,
            "analysis_outputs_must_be_fresh": True,
            "status_created_before_first_analysis_stage": True,
        },
        "claim_boundary": {
            "estimand": "CONDITIONAL_ON_FIXED_U002_POLICIES_AND_U004_EVIDENCE",
            "gate_name": "PROVISIONAL_DESIGN_SIGNAL_GATE",
            "gate_changed": False,
            "split_encoder_classifier_bootstrap_changed": False,
            "new_training_randomness_confirmed": False,
            "confirmatory_claim_authorized": False,
        },
        "execution_authorized": False,
        "authorization": "NOT_AUTHORIZED_UNTIL_CLEAN_U005_SOURCE_COMMIT_IS_RATIFIED",
        "pilot_protocol_ratified": False,
    }


def build_analysis_successor_template_v1() -> dict[str, Any]:
    return _with_identity_v1(_frozen_payload_v1())


def build_ratified_analysis_successor_protocol_v1(
    source_commit: str,
) -> dict[str, Any]:
    if (
        type(source_commit) is not str
        or re.fullmatch(r"[0-9a-f]{40}", source_commit) is None
    ):
        _fail("U005 source commit must be one lowercase full object ID")
    payload = _frozen_payload_v1()
    payload.update(
        {
            "campaign_kind": "LEARNED_RESOURCE_FORECAST_ANALYSIS_ONLY_SUCCESSOR_U005_RATIFIED",
            "source_commit": source_commit,
            "pilot_execution_identity": EXECUTION_IDENTITY_V1,
            "analysis_execution_id": ANALYSIS_EXECUTION_ID_V1,
            "execution_authorized": True,
            "authorization": "RATIFIED_FOR_ONE_ANALYSIS_VERIFICATION_RETENTION_EXECUTION",
            "pilot_protocol_ratified": True,
        }
    )
    return _with_identity_v1(payload)


def validate_ratified_analysis_successor_protocol_v1(
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    if type(protocol) is not dict:
        _fail("U005 analysis-successor protocol must be a plain object")
    source_commit = protocol.get("source_commit")
    protocol_id = protocol.get("protocol_id")
    if (
        type(source_commit) is not str
        or type(protocol_id) is not str
        or re.fullmatch(r"[0-9a-f]{64}", protocol_id) is None
    ):
        _fail("ratified U005 analysis-successor identity changed shape")
    expected = build_ratified_analysis_successor_protocol_v1(source_commit)
    if dict(protocol) != expected:
        _fail("ratified U005 analysis-successor differs from frozen design")
    return dict(protocol)


__all__ = (
    "ANALYSIS_EXECUTION_ID_V1",
    "ANALYSIS_OUTPUT_FILENAMES_V1",
    "EXECUTION_IDENTITY_V1",
    "LearnedResourceForecastAnalysisSuccessorProtocolV1Error",
    "PROTOCOL_DOMAIN_V1",
    "PROTOCOL_SCHEMA_V1",
    "U004_PROTOCOL_ID_V1",
    "U004_SOURCE_COMMIT_V1",
    "build_analysis_successor_template_v1",
    "build_ratified_analysis_successor_protocol_v1",
    "frozen_analysis_contract_v1",
    "u004_evidence_protocol_v1",
    "validate_ratified_analysis_successor_protocol_v1",
)
