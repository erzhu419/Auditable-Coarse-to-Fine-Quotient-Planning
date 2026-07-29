"""Typed record for the first anchored V0-072 campaign attempt failure.

This record is historical protocol evidence.  It is neither a campaign
result nor a plan/infeasibility certificate, and it deliberately represents
unrecoverable counters as unknown rather than zero.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    V072_ANCHORED_CAMPAIGN_ATTEMPT_FAILURE_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA = "acfqp.v072_anchored_campaign_attempt_failure.v1"
SCHEMA_VERSION = "1.0.0"
RECORD_DOMAIN = V072_ANCHORED_CAMPAIGN_ATTEMPT_FAILURE_DOMAIN
RECORD_REPOSITORY_PATH = "specs/V072_ANCHORED_ATTEMPT_1_FAILURE.json"

ANCHOR_COMMIT_ID = "b711cc52001419cfb0962e2a94af91cc03c5ffc2"
SOURCE_RECIPE_ID = (
    "d836f0b0c7f3b302541ce81dc5372c077d336add5f28a973ebd6ae611ccbd8b9"
)
MANIFEST_ID = (
    "acbec3e259e9df0e5b56c172ae2261f6d072f29b3a669b1eaafbcbdcae28b1c6"
)
FINAL_PREREGISTRATION_ID = (
    "b6a543a0e30214338214bf025bbf543994f6afc3251608f522d11f5c20e236f2"
)
REMOTE_MAIN_ANCHOR_CLAIM_ID = (
    "41c9aa9509717915777ba91a7d6015071ddb1f55187505f8ab376be2fd122d4f"
)
REMOTE_MAIN_ANCHOR_ID = (
    "157f6c512b912d4e100e76a30fdb4ae43c051cef6ac073778a303dd523e6d88e"
)
REMOTE_MAIN_ANCHOR_ATTESTATION_ID = (
    "4316c8a441db0eee80847c9060b25d9eae454d14895c4e137e1e9c092ff0fe6f"
)
K7_CONTEXT_ID = (
    "5bf58b73e363ff73f65d778f039b46ec96d2176082b9c935423f3ef9bb45681a"
)


class V072AnchoredAttemptFailureInvariantViolation(ValueError):
    """Raised when the historical failure record is missing or altered."""


def _unknown_not_zero() -> dict[str, Any]:
    return {
        "kind": "UNKNOWN_NOT_DURABLY_PERSISTED",
        "must_not_be_interpreted_as_zero": True,
    }


def _payload_v1() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "record_kind": "HISTORICAL_PROTOCOL_FAILURE_NOT_CAMPAIGN_RESULT",
        "attempt_ordinal": 1,
        "authority": {
            "anchor_commit_id": ANCHOR_COMMIT_ID,
            "source_reconstruction_recipe_id": SOURCE_RECIPE_ID,
            "confirmatory_execution_manifest_id": MANIFEST_ID,
            "final_preregistration_id": FINAL_PREREGISTRATION_ID,
            "remote_main_anchor_claim_id": REMOTE_MAIN_ANCHOR_CLAIM_ID,
            "remote_main_anchor_id": REMOTE_MAIN_ANCHOR_ID,
            "remote_main_anchor_attestation_id": (
                REMOTE_MAIN_ANCHOR_ATTESTATION_ID
            ),
        },
        "execution": {
            "command_argv": [
                "python3",
                "scripts/run_v072_registered_campaign.py",
            ],
            "output_repository_path": (
                "artifacts/v072_registered_campaign_result_v1.json"
            ),
            "source_reconstruction_observed_complete": True,
            "target_execution_started": True,
            "result_artifact_written": False,
            "endpoint_evaluated": False,
            "all_registered_occurrences_closed": False,
            "registered_occurrence_denominator": 15,
            "completed_occurrence_count": _unknown_not_zero(),
            "target_draws_and_native_work": _unknown_not_zero(),
            "wall_clock_elapsed": _unknown_not_zero(),
        },
        "last_reached_control_point": {
            "occurrence_ordinal_zero_based": 4,
            "occurrence_number_one_based": 5,
            "minimum_prior_occurrences_completed_by_sequential_control_flow": 4,
            "context_key": "heldout_graph_k7_confirmatory_v1",
            "context_id": K7_CONTEXT_ID,
            "arm": "MATCHED_DIRECT_GROUND",
            "validation_checkpoint": 2048,
            "stage": "INDEPENDENT_COLD_H2_ROW_WORK_REPLAY",
        },
        "failure": {
            "classification": "PROTOCOL_FAILURE",
            "reason": "INCOMPLETE_CAMPAIGN_ARTIFACT",
            "exception_class": "KeyError",
            "exception_key": "MATCHED_DIRECT_CHECKPOINT",
            "module": (
                "acfqp.v072_cold_h2_closure_independent_verifier_v1"
            ),
            "function": "_work_payload",
            "cause": (
                "MATCHED_DIRECT_CHECKPOINT was present in the production "
                "native-work enum but absent from the independent verifier "
                "purpose-to-draw-schedule mapping"
            ),
            "traceback_bytes_persisted": False,
            "traceback_digest": _unknown_not_zero(),
            "typed_campaign_terminal_artifact_minted": False,
            "plan_or_infeasibility_credit_allowed": False,
            "scientific_endpoint_read_allowed": False,
        },
        "disposition": {
            "old_attempt_remains_in_registered_denominator": True,
            "old_attempt_actual_work_may_not_be_reported_as_zero": True,
            "old_target_tape_or_evidence_reuse_allowed": False,
            "resume_from_occurrence_five_allowed": False,
            "replacement_attempt_must_restart_all_15_occurrences": True,
            "replacement_attempt_requires_new_source_recipe": True,
            "replacement_attempt_requires_new_manifest": True,
            "replacement_attempt_requires_new_final_preregistration": True,
            "replacement_attempt_requires_new_remote_main_anchor": True,
            "authorized_repair_scope": [
                "ADD_EXHAUSTIVE_MATCHED_DIRECT_CHECKPOINT_WORK_REPLAY",
                "FAIL_CLOSED_ON_UNEXPECTED_SELECTOR_TERMINAL_OUTCOME",
                "FAIL_CLOSED_ON_UNKNOWN_REGISTERED_ROUTE_KIND",
                "ADD_DURABLE_ATTEMPT_PROGRESS_AND_FAILURE_JOURNAL",
            ],
            "scientific_parameters_changed": False,
            "sample_efficiency_gate_status": "NOT_RUN",
        },
        "claim_boundary": {
            "campaign_result_claimed": False,
            "sample_efficiency_claimed": False,
            "broad_generalization_claimed": False,
            "total_objective_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "workload_economics_gate_status": "NOT_RUN",
            "counter_completeness_gate_status": "NOT_RUN",
        },
    }


def anchored_attempt_1_failure_document_v1() -> dict[str, Any]:
    """Return the one canonical historical failure document."""

    payload = _payload_v1()
    return {
        **payload,
        "record_id": content_id(RECORD_DOMAIN, payload),
    }


def verify_anchored_attempt_1_failure_document_v1(
    document: Mapping[str, Any],
) -> str:
    """Require exact semantic and content equality with the frozen record."""

    try:
        candidate = dict(document)
        record_id = parse_content_id(candidate.pop("record_id"))
        expected = anchored_attempt_1_failure_document_v1()
        expected_id = expected.pop("record_id")
        if candidate != expected:
            raise V072AnchoredAttemptFailureInvariantViolation(
                "anchored-attempt failure semantics changed"
            )
        if record_id != expected_id or record_id != content_id(
            RECORD_DOMAIN,
            candidate,
        ):
            raise V072AnchoredAttemptFailureInvariantViolation(
                "anchored-attempt failure content identity changed"
            )
    except (
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        if isinstance(
            error,
            V072AnchoredAttemptFailureInvariantViolation,
        ):
            raise
        raise V072AnchoredAttemptFailureInvariantViolation(
            "anchored-attempt failure document is malformed"
        ) from error
    return record_id


def load_anchored_attempt_1_failure_record_v1(
    repository_root: Path,
) -> dict[str, Any]:
    """Load canonical tracked bytes and verify the historical record."""

    root = repository_root.resolve(strict=True)
    path = root / RECORD_REPOSITORY_PATH
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode("utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V072AnchoredAttemptFailureInvariantViolation(
            "anchored-attempt failure record cannot be loaded"
        ) from error
    if (
        type(document) is not dict
        or raw not in (
            canonical_json_bytes(document),
            canonical_json_bytes(document) + b"\n",
        )
    ):
        raise V072AnchoredAttemptFailureInvariantViolation(
            "anchored-attempt failure record is not canonical JSON"
        )
    verify_anchored_attempt_1_failure_document_v1(document)
    return document


def verify_anchored_attempt_1_git_authority_v1(
    repository_root: Path,
) -> tuple[str, str, str]:
    """Replay the old commit's three frozen identities without network I/O."""

    root = repository_root.resolve(strict=True)
    try:
        ancestry = subprocess.run(
            (
                "git",
                "-C",
                str(root),
                "merge-base",
                "--is-ancestor",
                ANCHOR_COMMIT_ID,
                "HEAD",
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
            timeout=15,
        )
        if ancestry.returncode != 0:
            raise V072AnchoredAttemptFailureInvariantViolation(
                "attempt-1 anchor commit is not current-history provenance"
            )
        documents: list[dict[str, Any]] = []
        for relative in (
            "specs/V072_SOURCE_RECONSTRUCTION_RECIPE.json",
            "specs/V072_CONFIRMATORY_EXECUTION_MANIFEST.json",
            "specs/V072_FINAL_PREREGISTRATION.json",
        ):
            completed = subprocess.run(
                (
                    "git",
                    "-C",
                    str(root),
                    "show",
                    f"{ANCHOR_COMMIT_ID}:{relative}",
                ),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
            if completed.returncode != 0:
                raise V072AnchoredAttemptFailureInvariantViolation(
                    "attempt-1 anchor commit lacks its frozen identity chain"
                )
            parsed = json.loads(
                completed.stdout.decode("utf-8", errors="strict")
            )
            if type(parsed) is not dict:
                raise V072AnchoredAttemptFailureInvariantViolation(
                    "attempt-1 frozen identity document is malformed"
                )
            documents.append(parsed)
    except (
        OSError,
        subprocess.SubprocessError,
        UnicodeError,
        json.JSONDecodeError,
    ) as error:
        raise V072AnchoredAttemptFailureInvariantViolation(
            "attempt-1 Git provenance replay failed"
        ) from error
    recipe, manifest, preregistration = documents
    identities = (
        recipe.get("recipe_id"),
        manifest.get("manifest_id"),
        preregistration.get("preregistration_id"),
    )
    if identities != (
        SOURCE_RECIPE_ID,
        MANIFEST_ID,
        FINAL_PREREGISTRATION_ID,
    ):
        raise V072AnchoredAttemptFailureInvariantViolation(
            "attempt-1 frozen Git identities differ from the failure record"
        )
    return identities


__all__ = [
    "ANCHOR_COMMIT_ID",
    "FINAL_PREREGISTRATION_ID",
    "MANIFEST_ID",
    "RECORD_DOMAIN",
    "RECORD_REPOSITORY_PATH",
    "REMOTE_MAIN_ANCHOR_ATTESTATION_ID",
    "REMOTE_MAIN_ANCHOR_CLAIM_ID",
    "REMOTE_MAIN_ANCHOR_ID",
    "SCHEMA",
    "SCHEMA_VERSION",
    "SOURCE_RECIPE_ID",
    "V072AnchoredAttemptFailureInvariantViolation",
    "anchored_attempt_1_failure_document_v1",
    "load_anchored_attempt_1_failure_record_v1",
    "verify_anchored_attempt_1_git_authority_v1",
    "verify_anchored_attempt_1_failure_document_v1",
]
