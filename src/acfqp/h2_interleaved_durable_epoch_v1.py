"""V0-057 interleaved certificate-triggered durable H2 epoch control.

The public producer consumes the original eight V0-047 live authorities plus
one fresh campaign directory.  It deliberately does not accept a completed
V0-047/V0-053/V0-056 result, a model, row set, plan, delta, cache, or expected
worker output.

This file is also the isolated model-only occurrence worker.  Project modules
used by the live producer are imported only inside the host producer, so the
``--worker`` path imports no domain kernel or recovery implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from typing import Any, Mapping

from acfqp.h2_interleaved_durable_epoch_pins_v1 import (
    EXPECTED_AUDIT_MODULE_SHA256,
    EXPECTED_DURABLE_TRANSPORT_MODULE_SHA256,
    EXPECTED_LIVE_DERIVE_DELTA_SOURCE_SHA256,
    EXPECTED_LIVE_MODULE_SHA256,
    EXPECTED_MULTISTEP_ACQUIRE_SOURCE_SHA256,
    EXPECTED_MULTISTEP_MODULE_SHA256,
    EXPECTED_MULTISTEP_ROUND_TWO_REQUEST_SOURCE_SHA256,
    EXPECTED_ORCHESTRATOR_MODULE_SHA256,
    EXPECTED_PLANNER_MODULE_SHA256,
    EXPECTED_PUBLIC_PRODUCER_SOURCE_SHA256,
    EXPECTED_TEMPORAL_MODULE_SHA256,
    EXPECTED_WORKER_MAIN_SOURCE_SHA256,
)


CONTRACT_VERSION = "1.21.0"
SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "lmb_h2_interleaved_certificate_triggered_durable_epoch_v0"
SUCCESS_STATUS = (
    "CERTIFIED_REGISTERED_H2_INTERLEAVED_CERTIFICATE_TRIGGERED_"
    "DURABLE_EPOCH_CONTROL"
)

QUERY_ORDER = ("Q_R", "Q_S", "Q_R", "Q_S", "Q_R")
SCHEDULE_ORDER = ("A0A0", "A0A1", "A1A1", "A1A0")
LOWER_SLOTS = ("U1", "U0", "P1", "P0", "C0", "C1", "D", "E", "F", "G")

_DOMAIN_TAGS = {
    "query": "acfqp:interleaved-threshold-query:v1",
    "occurrence": "acfqp:interleaved-query-occurrence:v1",
    "preregistration": "acfqp:interleaved-workload-preregistration:v1",
    "eligibility": "acfqp:epoch-threshold-family-eligibility:v1",
    "metric": "acfqp:interleaved-candidate-metric:v1",
    "lower_value": "acfqp:interleaved-lower-proof-value:v1",
    "facet_key": "acfqp:interleaved-query-facet-key:v1",
    "facet_entry": "acfqp:interleaved-query-facet-entry:v1",
    "checkpoint_payload": "acfqp:interleaved-epoch-checkpoint-payload:v1",
    "checkpoint_commit": "acfqp:interleaved-epoch-checkpoint-commit:v1",
    "facet_payload": "acfqp:interleaved-facet-store-payload:v1",
    "facet_commit": "acfqp:interleaved-facet-store-commit:v1",
    "candidate_root": "acfqp:interleaved-candidate-root:v1",
    "proof_request": "acfqp:interleaved-proof-request:v1",
    "proposal": "acfqp:interleaved-plan-proposal:v1",
    "selected_root": "acfqp:interleaved-selected-root:v1",
    "failed_frontier": "acfqp:interleaved-failed-proof-frontier:v1",
    "certificate": "acfqp:interleaved-plan-certificate:v1",
    "occurrence_result": "acfqp:interleaved-occurrence-result:v1",
    "worker_execution": "acfqp:interleaved-worker-execution:v1",
    "authorization": "acfqp:interleaved-ground-repair-authorization:v1",
    "campaign_owner": "acfqp:interleaved-campaign-owner:v1",
    "query_eligibility_freeze": (
        "acfqp:interleaved-query-eligibility-freeze:v1"
    ),
    "event": "acfqp:interleaved-event:v1",
    "event_log": "acfqp:interleaved-event-log:v1",
    "source_chain": "acfqp:interleaved-live-source-chain:v1",
    "accounting": "acfqp:interleaved-epoch-accounting:v1",
    "snapshot": "acfqp:interleaved-campaign-snapshot:v1",
    "result": "acfqp:interleaved-durable-epoch-result:v1",
    "verification": "acfqp:interleaved-durable-epoch-verification:v1",
}

_LIVE_PROFILE_KEY = "lmb_h2_live_query_local_epoch_invalidation_v0"
_LIVE_SCHEMA_VERSION = "1.0.0"
_LIVE_SEMANTICS_ID = (
    "17a7fb36b05d6dcf9ed319cae706a5a5b0fd496359b66348cc444ea16955f264"
)
_EXPECTED_EPOCH_MODEL_IDS = {
    "FIRST": (
        "e3d550b7d46b516bd443881e14ade00b8a1cc673f141039d09dc585fa2b28fba"
    ),
    "FINAL": (
        "a18a29a1c1bd3433ef7ace6d99c67a594a0d587b6b0c2889f71022eaa7437315"
    ),
}
_LIVE_DOMAIN_TAGS = {
    "canonical_input": "acfqp:live-epoch-canonical-input:v1",
    "slice_content": "acfqp:live-epoch-model-slice-content:v1",
    "slice_binding": "acfqp:live-epoch-model-slice-binding:v1",
    "node_key": "acfqp:live-epoch-proof-node-key:v1",
    "node_result": "acfqp:live-epoch-proof-node-result:v1",
    "entry": "acfqp:live-epoch-proof-entry:v1",
}
_AUDIT_DOMAIN_TAGS = {
    "thresholds": "acfqp:partial-audit-thresholds:v1",
    "assignment": "acfqp:partial-contingent-plan-assignment:v1",
    "stage": "acfqp:partial-contingent-plan-stage:v1",
    "plan": "acfqp:frozen-partial-contingent-plan:v1",
}
_MODEL_DOMAIN_TAG = "acfqp:query-scoped-partial-rapm:v3"
_TEMPORAL_STAGE_DOMAIN_TAG = "acfqp:h2-temporal-stage-assignment:v1"
_TEMPORAL_PROFILE_KEY = "lmb_h2_stage_local_bellman_proof_dag_v0"
_PARENT_SLOTS = {
    "U1": (),
    "U0": ("U1",),
    "P1": (),
    "P0": ("P1",),
    "C0": (),
    "C1": ("C0",),
    "D": ("U0", "P0", "C0", "C1"),
    "E": ("D",),
    "F": ("D",),
    "G": ("C0", "C1"),
}
_RESULT_SEMANTICS = {
    "U1": "UNRESTRICTED_BELLMAN_T1",
    "U0": "UNRESTRICTED_BELLMAN_T0",
    "P1": "FIXED_POLICY_BELLMAN_T1",
    "P0": "FIXED_POLICY_BELLMAN_T0",
    "C0": "FORWARD_REACHABILITY_T0",
    "C1": "FORWARD_REACHABILITY_T1",
    "D": "ROOT_VALUE_RISK_METRICS",
    "E": "REGRET_VERDICT",
    "F": "RISK_VERDICT",
    "G": "EXTERNAL_COVERAGE_VERDICT",
}
_FORMULA_IDS = {
    "U1": "STAGE_LOCAL_UNRESTRICTED_BELLMAN_V1",
    "U0": "STAGE_LOCAL_UNRESTRICTED_BELLMAN_V1",
    "P1": "STAGE_LOCAL_FIXED_POLICY_BELLMAN_V1",
    "P0": "STAGE_LOCAL_FIXED_POLICY_BELLMAN_V1",
    "C0": "STAGE_LOCAL_FORWARD_REACHABILITY_V1",
    "C1": "STAGE_LOCAL_FORWARD_REACHABILITY_V1",
    "D": "ROOT_SUPPORT_VALUE_RISK_METRICS_V1",
    "E": "REGRET_THRESHOLD_VERDICT_V1",
    "F": "RISK_THRESHOLD_VERDICT_V1",
    "G": "EXTERNAL_COVERAGE_VERDICT_V1",
}
EXPECTED_EVENT_ORDER = (
    "PREREGISTRATION_FROZEN",
    "QUERY_ELIGIBILITY_FROZEN",
    "AUTHENTIC_V0047_FIRST_EPOCH_STARTED",
    "ROUND_ONE_FOUR_ROWS_COMPLETED",
    "BOUNDARY_THREE_CATALOGUES_COMPLETED",
    "FIRST_11_9_EPOCH_FROZEN",
    "C1_ROOT_FREE_CHECKPOINT_FROZEN",
    "OCCURRENCE_1_Q_R_FIRST_EPOCH_STARTED",
    "OCCURRENCE_1_Q_R_CERTIFIED_ZERO_QUERY_GROUND",
    "OCCURRENCE_2_Q_S_FIRST_EPOCH_STARTED",
    "OCCURRENCE_2_Q_S_SELECTED_FAILURE_FROZEN",
    "ROUND_TWO_REQUEST_DERIVED_FROM_Q_S_FAILURE",
    "ROUND_TWO_NINE_ROWS_AUTHORIZED",
    "ROUND_TWO_NINE_ROWS_COMPLETED",
    "FINAL_20_0_EPOCH_FROZEN",
    "DELTA_AND_28_2_INVALIDATION_FROZEN",
    "C2_58_UNION_30_ACTIVE_FROZEN",
    "OCCURRENCE_2_Q_S_FINAL_REPLAN_STARTED",
    "OCCURRENCE_2_Q_S_CERTIFIED",
    "OCCURRENCE_3_Q_R_FINAL_CERTIFIED",
    "OCCURRENCE_4_Q_S_FINAL_CERTIFIED",
    "OCCURRENCE_5_Q_R_FINAL_CERTIFIED",
    "CAMPAIGN_RESULT_FROZEN",
)
_EVENT_OCCURRENCE_NULL = {
    "kind": "NOT_APPLICABLE",
    "reason": "NO_OCCURRENCE_CONTEXT",
}
_EVENT_EPOCH_NULL = {
    "kind": "NOT_APPLICABLE",
    "reason": "NO_EPOCH_CONTEXT",
}


def _expected_event_context(
    sequence_number: int,
) -> tuple[int | Mapping[str, str], str | Mapping[str, str], int, int, int, int, int]:
    if sequence_number in {8, 9}:
        occurrence: int | Mapping[str, str] = 1
    elif 10 <= sequence_number <= 19:
        occurrence = 2
    elif sequence_number == 20:
        occurrence = 3
    elif sequence_number == 21:
        occurrence = 4
    elif sequence_number == 22:
        occurrence = 5
    else:
        occurrence = _EVENT_OCCURRENCE_NULL
    if 3 <= sequence_number <= 14:
        epoch: str | Mapping[str, str] = "FIRST"
    elif 15 <= sequence_number <= 22:
        epoch = "FINAL"
    else:
        epoch = _EVENT_EPOCH_NULL
    round_one = 4 if sequence_number >= 4 else 0
    boundary = 3 if sequence_number >= 5 else 0
    round_two = 9 if sequence_number >= 14 else 0
    if sequence_number <= 8:
        main = 0
    elif sequence_number <= 10:
        main = 1
    elif sequence_number <= 18:
        main = 2
    else:
        main = min(6, sequence_number - 16)
    reset = 6 if sequence_number == 23 else 0
    return (
        occurrence,
        epoch,
        round_one,
        round_two,
        boundary,
        main,
        reset,
    )


class InterleavedDurableEpochInvariantViolation(ValueError):
    """Raised when the registered V0-057 contract is violated."""


def _canonical_json_bytes(document: Mapping[str, Any]) -> bytes:
    return json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        tag = _DOMAIN_TAGS[role]
    except KeyError as error:
        raise InterleavedDurableEpochInvariantViolation(
            f"unregistered V0-057 content role: {role}"
        ) from error
    return hashlib.sha256(
        tag.encode("utf-8") + b"\x00" + _canonical_json_bytes(payload)
    ).hexdigest()


def _domain_content_id(tag: str, payload: Mapping[str, Any]) -> str:
    if type(tag) is not str or not tag:
        raise InterleavedDurableEpochInvariantViolation(
            "content domain tag is empty"
        )
    return hashlib.sha256(
        tag.encode("utf-8") + b"\x00" + _canonical_json_bytes(payload)
    ).hexdigest()


def _exact_mapping(
    value: Any,
    fields: set[str],
    label: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise InterleavedDurableEpochInvariantViolation(
            f"{label} field set changed"
        )
    return value


def _cid(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise InterleavedDurableEpochInvariantViolation(
            f"{label} is not a canonical SHA-256 identity"
        )
    return value


def _integer(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise InterleavedDurableEpochInvariantViolation(
            f"{label} is not an integer >= {minimum}"
        )
    return value


def _fraction(value: Any, label: str) -> Fraction:
    if type(value) is not Fraction:
        raise InterleavedDurableEpochInvariantViolation(
            f"{label} must be an exact Fraction"
        )
    return value


def _fraction_document(value: Fraction) -> dict[str, int]:
    value = _fraction(value, "fraction document")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _parse_fraction(value: Any, label: str) -> Fraction:
    if (
        type(value) is not dict
        or set(value) != {"numerator", "denominator"}
        or type(value["numerator"]) is not int
        or type(value["denominator"]) is not int
        or value["denominator"] <= 0
    ):
        raise InterleavedDurableEpochInvariantViolation(
            f"{label} is not a reduced rational document"
        )
    result = Fraction(value["numerator"], value["denominator"])
    if _fraction_document(result) != value:
        raise InterleavedDurableEpochInvariantViolation(
            f"{label} is not reduced"
        )
    return result


def _write_exclusive(path: Path, document: Mapping[str, Any]) -> int:
    payload = _canonical_json_bytes(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
    except (FileExistsError, OSError) as error:
        raise InterleavedDurableEpochInvariantViolation(
            f"failed to freeze {path.name}"
        ) from error
    return len(payload)


def _stable_regular_bytes(path: Path) -> bytes:
    if not isinstance(path, Path) or not path.is_file() or path.is_symlink():
        raise InterleavedDurableEpochInvariantViolation(
            f"artifact {getattr(path, 'name', '<unknown>')} is not a regular file"
        )
    before = path.stat()
    if before.st_nlink != 1:
        raise InterleavedDurableEpochInvariantViolation(
            f"artifact {path.name} has multiple hard links"
        )
    payload = path.read_bytes()
    after = path.stat()
    if (
        before.st_ino,
        before.st_dev,
        before.st_size,
        before.st_mtime_ns,
    ) != (
        after.st_ino,
        after.st_dev,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise InterleavedDurableEpochInvariantViolation(
            f"artifact {path.name} changed while being read"
        )
    return payload


def _read_canonical(path: Path) -> tuple[dict[str, Any], int]:
    try:
        raw = _stable_regular_bytes(path)
        document = json.loads(raw)
    except (
        OSError,
        json.JSONDecodeError,
        InterleavedDurableEpochInvariantViolation,
    ) as error:
        raise InterleavedDurableEpochInvariantViolation(
            f"failed to read canonical artifact {path.name}"
        ) from error
    if type(document) is not dict or raw != _canonical_json_bytes(document):
        raise InterleavedDurableEpochInvariantViolation(
            f"artifact {path.name} is not canonical JSON"
        )
    return document, len(raw)


@dataclass(frozen=True, slots=True)
class InterleavedThresholdQueryV1:
    query_code: str
    normalized_regret_tolerance: Fraction
    risk_tolerance: Fraction

    def __post_init__(self) -> None:
        _fraction(
            self.normalized_regret_tolerance,
            "interleaved normalized-regret tolerance",
        )
        _fraction(self.risk_tolerance, "interleaved risk tolerance")
        expected = {
            "Q_R": (Fraction(3, 4), Fraction(1)),
            "Q_S": (Fraction(0), Fraction(0)),
        }
        if (
            self.query_code not in expected
            or (
                self.normalized_regret_tolerance,
                self.risk_tolerance,
            )
            != expected[self.query_code]
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "registered interleaved query changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.interleaved_threshold_query.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "query_code": self.query_code,
            "normalized_regret_tolerance": _fraction_document(
                self.normalized_regret_tolerance
            ),
            "risk_tolerance": _fraction_document(self.risk_tolerance),
        }

    @property
    def query_id(self) -> str:
        return _content_id("query", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "query_id": self.query_id}


def registered_interleaved_queries_v1() -> tuple[
    InterleavedThresholdQueryV1, InterleavedThresholdQueryV1
]:
    return (
        InterleavedThresholdQueryV1("Q_R", Fraction(3, 4), Fraction(1)),
        InterleavedThresholdQueryV1("Q_S", Fraction(0), Fraction(0)),
    )


def _validate_query_document(document: Mapping[str, Any]) -> None:
    query = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "query_code",
            "normalized_regret_tolerance",
            "risk_tolerance",
            "query_id",
        },
        "interleaved query",
    )
    body = {key: value for key, value in query.items() if key != "query_id"}
    if (
        query["schema"] != "acfqp.interleaved_threshold_query.v1"
        or query["schema_version"] != SCHEMA_VERSION
        or query["profile_key"] != PROFILE_KEY
        or query["query_id"] != _content_id("query", body)
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "interleaved query identity changed"
        )
    expected = {
        item.query_code: item.to_document()
        for item in registered_interleaved_queries_v1()
    }
    if query["query_code"] not in expected or query != expected[query["query_code"]]:
        raise InterleavedDurableEpochInvariantViolation(
            "worker received an unregistered interleaved query"
        )


@dataclass(frozen=True, slots=True)
class InterleavedOccurrenceV1:
    occurrence_index: int
    query: InterleavedThresholdQueryV1

    def __post_init__(self) -> None:
        _integer(self.occurrence_index, "occurrence index", 1)
        if (
            self.occurrence_index > len(QUERY_ORDER)
            or type(self.query) is not InterleavedThresholdQueryV1
            or self.query.query_code != QUERY_ORDER[self.occurrence_index - 1]
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "interleaved occurrence order changed"
            )
        self.query.__post_init__()

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.interleaved_query_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_index": self.occurrence_index,
            "query_id": self.query.query_id,
            "query_code": self.query.query_code,
        }

    @property
    def occurrence_id(self) -> str:
        return _content_id("occurrence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_id": self.occurrence_id}


def _validate_occurrence_document(
    document: Mapping[str, Any],
    query: Mapping[str, Any],
) -> None:
    occurrence = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "occurrence_index",
            "query_id",
            "query_code",
            "occurrence_id",
        },
        "interleaved occurrence",
    )
    body = {
        key: value for key, value in occurrence.items()
        if key != "occurrence_id"
    }
    index = occurrence["occurrence_index"]
    if (
        occurrence["schema"] != "acfqp.interleaved_query_occurrence.v1"
        or occurrence["schema_version"] != SCHEMA_VERSION
        or occurrence["profile_key"] != PROFILE_KEY
        or occurrence["occurrence_id"] != _content_id("occurrence", body)
        or type(index) is not int
        or index not in range(1, len(QUERY_ORDER) + 1)
        or occurrence["query_code"] != QUERY_ORDER[index - 1]
        or occurrence["query_id"] != query["query_id"]
        or occurrence["query_code"] != query["query_code"]
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "worker occurrence/query lineage changed"
        )


@dataclass(frozen=True, slots=True)
class InterleavedWorkloadPreregistrationV1:
    source_strict_thresholds_id: str
    queries: tuple[InterleavedThresholdQueryV1, ...]
    occurrences: tuple[InterleavedOccurrenceV1, ...]
    input_authority_ids: Mapping[str, str]
    horizon: int
    goal_id: str
    return_bound_proof_id: str
    return_bound_formula_id: str
    return_upper: Fraction
    unrestricted_upper_formula_id: str
    initial_distribution_digest: str
    reward_basis_digest: str
    policy_class: str
    candidate_order: tuple[str, ...]
    proof_formula_registry_digest: str
    base_model_id: str
    structural_id: str
    environment_instance_id: str
    coordinate_proposal_id: str
    epoch_lineage_profile_id: str
    structural_state_action_concretizer_scope: Mapping[str, Any]
    structural_state_action_concretizer_digest: str
    threshold_only_variation: bool = True
    derived_source_artifact_ids_absent: bool = True
    frozen_before_source_ground: bool = True

    def __post_init__(self) -> None:
        if type(self.input_authority_ids) is not dict:
            raise InterleavedDurableEpochInvariantViolation(
                "preregistered input authority map changed"
            )
        structural_scope_fields = {
            "schema",
            "schema_version",
            "profile_key",
            "base_model_id",
            "structural_id",
            "environment_instance_id",
            "semantics_profile",
            "coordinate_proposal_id",
            "base_cells",
            "base_semantic_actions",
            "base_semantic_realizations",
            "base_concretizer_rows",
            "reward_feature_caps",
        }
        if (
            type(self.structural_state_action_concretizer_scope) is not dict
            or set(self.structural_state_action_concretizer_scope)
            != structural_scope_fields
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "preregistered structural semantic scope changed"
            )
        structural_scope = self.structural_state_action_concretizer_scope
        for value in (
            self.source_strict_thresholds_id,
            self.return_bound_proof_id,
            self.initial_distribution_digest,
            self.reward_basis_digest,
            self.proof_formula_registry_digest,
            self.base_model_id,
            self.structural_id,
            self.environment_instance_id,
            self.coordinate_proposal_id,
            self.epoch_lineage_profile_id,
            self.structural_state_action_concretizer_digest,
            *self.input_authority_ids.values(),
        ):
            _cid(value, "preregistered workload scope identity")
        input_fields = {
            "observation_log_id",
            "semantics_profile_id",
            "observation_authority_id",
            "observed_synthesis_result_id",
            "source_thresholds_id",
            "base_plan_proposal_id",
            "failed_audit_id",
            "kernel_digest",
        }
        if (
            type(self.input_authority_ids) is not dict
            or set(self.input_authority_ids) != input_fields
            or self.input_authority_ids["source_thresholds_id"]
            != self.source_strict_thresholds_id
            or
            type(self.queries) is not tuple
            or self.queries != registered_interleaved_queries_v1()
            or type(self.occurrences) is not tuple
            or len(self.occurrences) != 5
            or tuple(item.query.query_code for item in self.occurrences)
            != QUERY_ORDER
            or self.horizon != 2
            or self.goal_id != "default"
            or self.return_bound_formula_id
            != "canonical-lmb-n6-return-upper-v1"
            or self.return_upper != Fraction(4)
            or self.unrestricted_upper_formula_id
            != "partial-joint-simplex-unrestricted-ground-upper-v1"
            or self.policy_class
            != (
                "DETERMINISTIC_FINITE_HORIZON_"
                "ABSTRACT_CONTINGENT_PLAN"
            )
            or self.candidate_order != SCHEDULE_ORDER
            or self.proof_formula_registry_digest
            != _proof_formula_registry_digest()
            or self.epoch_lineage_profile_id
            != _epoch_lineage_profile_id(self.base_model_id)
            or structural_scope["schema"]
            != (
                "acfqp.interleaved_structural_state_action_"
                "concretizer_scope.v1"
            )
            or structural_scope["schema_version"] != SCHEMA_VERSION
            or structural_scope["profile_key"] != PROFILE_KEY
            or structural_scope["base_model_id"] != self.base_model_id
            or structural_scope["structural_id"] != self.structural_id
            or structural_scope["environment_instance_id"]
            != self.environment_instance_id
            or structural_scope["coordinate_proposal_id"]
            != self.coordinate_proposal_id
            or type(structural_scope["semantics_profile"]) is not dict
            or structural_scope["semantics_profile"].get("profile_id")
            != self.input_authority_ids["semantics_profile_id"]
            or self.structural_state_action_concretizer_digest
            != _structural_state_action_concretizer_digest(
                structural_scope
            )
            or self.threshold_only_variation is not True
            or self.derived_source_artifact_ids_absent is not True
            or self.frozen_before_source_ground is not True
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "interleaved preregistration changed"
            )
        for item in self.occurrences:
            item.__post_init__()

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.interleaved_workload_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_strict_thresholds_id": self.source_strict_thresholds_id,
            "queries": [item.to_document() for item in self.queries],
            "occurrences": [item.to_document() for item in self.occurrences],
            "input_authority_ids": dict(self.input_authority_ids),
            "horizon": self.horizon,
            "goal_id": self.goal_id,
            "return_bound_proof_id": self.return_bound_proof_id,
            "return_bound_formula_id": self.return_bound_formula_id,
            "return_upper": _fraction_document(self.return_upper),
            "unrestricted_upper_formula_id": (
                self.unrestricted_upper_formula_id
            ),
            "initial_distribution_digest": (
                self.initial_distribution_digest
            ),
            "reward_basis_digest": self.reward_basis_digest,
            "policy_class": self.policy_class,
            "candidate_order": list(self.candidate_order),
            "proof_formula_registry_digest": (
                self.proof_formula_registry_digest
            ),
            "base_model_id": self.base_model_id,
            "structural_id": self.structural_id,
            "environment_instance_id": self.environment_instance_id,
            "coordinate_proposal_id": self.coordinate_proposal_id,
            "epoch_lineage_profile_id": self.epoch_lineage_profile_id,
            "structural_state_action_concretizer_scope": dict(
                self.structural_state_action_concretizer_scope
            ),
            "structural_state_action_concretizer_digest": (
                self.structural_state_action_concretizer_digest
            ),
            "threshold_only_variation": self.threshold_only_variation,
            "derived_source_artifact_ids_absent": (
                self.derived_source_artifact_ids_absent
            ),
            "frozen_before_source_ground": self.frozen_before_source_ground,
        }

    @property
    def preregistration_id(self) -> str:
        return _content_id("preregistration", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "preregistration_id": self.preregistration_id,
        }


def registered_interleaved_preregistration_v1(
    source_strict_thresholds_id: str,
    *,
    input_authority_ids: Mapping[str, str],
    goal_id: str,
    return_bound_proof_id: str,
    return_bound_formula_id: str,
    return_upper: Fraction,
    unrestricted_upper_formula_id: str,
    initial_distribution_digest: str,
    reward_basis_digest: str,
    base_model_id: str,
    structural_id: str,
    environment_instance_id: str,
    coordinate_proposal_id: str,
    structural_state_action_concretizer_scope: Mapping[str, Any],
    structural_state_action_concretizer_digest: str,
) -> InterleavedWorkloadPreregistrationV1:
    queries = registered_interleaved_queries_v1()
    by_code = {item.query_code: item for item in queries}
    occurrences = tuple(
        InterleavedOccurrenceV1(index, by_code[code])
        for index, code in enumerate(QUERY_ORDER, 1)
    )
    return InterleavedWorkloadPreregistrationV1(
        source_strict_thresholds_id,
        queries,
        occurrences,
        dict(input_authority_ids),
        2,
        goal_id,
        return_bound_proof_id,
        return_bound_formula_id,
        return_upper,
        unrestricted_upper_formula_id,
        initial_distribution_digest,
        reward_basis_digest,
        (
            "DETERMINISTIC_FINITE_HORIZON_"
            "ABSTRACT_CONTINGENT_PLAN"
        ),
        SCHEDULE_ORDER,
        _proof_formula_registry_digest(),
        base_model_id,
        structural_id,
        environment_instance_id,
        coordinate_proposal_id,
        _epoch_lineage_profile_id(base_model_id),
        dict(structural_state_action_concretizer_scope),
        structural_state_action_concretizer_digest,
    )


def _validate_preregistration_document(
    document: Mapping[str, Any],
) -> InterleavedWorkloadPreregistrationV1:
    record = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "contract_version",
            "profile_key",
            "source_strict_thresholds_id",
            "queries",
            "occurrences",
            "input_authority_ids",
            "horizon",
            "goal_id",
            "return_bound_proof_id",
            "return_bound_formula_id",
            "return_upper",
            "unrestricted_upper_formula_id",
            "initial_distribution_digest",
            "reward_basis_digest",
            "policy_class",
            "candidate_order",
            "proof_formula_registry_digest",
            "base_model_id",
            "structural_id",
            "environment_instance_id",
            "coordinate_proposal_id",
            "epoch_lineage_profile_id",
            "structural_state_action_concretizer_scope",
            "structural_state_action_concretizer_digest",
            "threshold_only_variation",
            "derived_source_artifact_ids_absent",
            "frozen_before_source_ground",
            "preregistration_id",
        },
        "interleaved preregistration",
    )
    source_id = _cid(
        record["source_strict_thresholds_id"],
        "preregistration source thresholds",
    )
    queries = registered_interleaved_queries_v1()
    by_code = {item.query_code: item for item in queries}
    occurrences = tuple(
        InterleavedOccurrenceV1(index, by_code[code])
        for index, code in enumerate(QUERY_ORDER, 1)
    )
    expected = InterleavedWorkloadPreregistrationV1(
        source_id,
        queries,
        occurrences,
        record["input_authority_ids"],
        record["horizon"],
        record["goal_id"],
        _cid(
            record["return_bound_proof_id"],
            "preregistration return-bound proof",
        ),
        record["return_bound_formula_id"],
        _parse_fraction(
            record["return_upper"], "preregistration return upper"
        ),
        record["unrestricted_upper_formula_id"],
        _cid(
            record["initial_distribution_digest"],
            "preregistration initial distribution",
        ),
        _cid(
            record["reward_basis_digest"],
            "preregistration reward basis",
        ),
        record["policy_class"],
        tuple(record["candidate_order"]),
        _cid(
            record["proof_formula_registry_digest"],
            "preregistration formula registry",
        ),
        _cid(record["base_model_id"], "preregistration base model"),
        _cid(record["structural_id"], "preregistration structural fixture"),
        _cid(
            record["environment_instance_id"],
            "preregistration environment instance",
        ),
        _cid(
            record["coordinate_proposal_id"],
            "preregistration coordinate proposal",
        ),
        _cid(
            record["epoch_lineage_profile_id"],
            "preregistration epoch lineage profile",
        ),
        record["structural_state_action_concretizer_scope"],
        _cid(
            record["structural_state_action_concretizer_digest"],
            "preregistration structural semantics",
        ),
        record["threshold_only_variation"],
        record["derived_source_artifact_ids_absent"],
        record["frozen_before_source_ground"],
    )
    if record != expected.to_document():
        raise InterleavedDurableEpochInvariantViolation(
            "interleaved preregistration is not canonical"
        )
    return expected


@dataclass(frozen=True, slots=True)
class EpochThresholdFamilyEligibilityV1:
    preregistration_id: str
    model_id: str
    source_strict_thresholds_id: str
    epoch_strict_thresholds_id: str
    query_ids: tuple[str, ...]
    horizon: int
    initial_distribution_digest: str
    reward_basis_digest: str
    model_semantic_digest: str
    epoch_name: str
    model_query_local: bool = True
    model_promotion_authorized: bool = False
    acquisition_query_neutral: bool = False
    threshold_family_scope_authorized: bool = True
    unrestricted_reuse_authorized: bool = False

    def __post_init__(self) -> None:
        for value in (
            self.preregistration_id,
            self.model_id,
            self.source_strict_thresholds_id,
            self.epoch_strict_thresholds_id,
            *self.query_ids,
            self.initial_distribution_digest,
            self.reward_basis_digest,
            self.model_semantic_digest,
        ):
            _cid(value, "eligibility identity")
        if (
            self.query_ids
            != tuple(item.query_id for item in registered_interleaved_queries_v1())
            or self.horizon != 2
            or self.epoch_name not in {"FIRST", "FINAL"}
            or self.model_query_local is not True
            or self.model_promotion_authorized is not False
            or self.acquisition_query_neutral is not False
            or self.threshold_family_scope_authorized is not True
            or self.unrestricted_reuse_authorized is not False
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "epoch-scoped threshold eligibility changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.epoch_threshold_family_eligibility.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": self.preregistration_id,
            "model_id": self.model_id,
            "source_strict_thresholds_id": self.source_strict_thresholds_id,
            "epoch_strict_thresholds_id": self.epoch_strict_thresholds_id,
            "query_ids": list(self.query_ids),
            "horizon": self.horizon,
            "initial_distribution_digest": self.initial_distribution_digest,
            "reward_basis_digest": self.reward_basis_digest,
            "model_semantic_digest": self.model_semantic_digest,
            "epoch_name": self.epoch_name,
            "model_query_local": self.model_query_local,
            "model_promotion_authorized": self.model_promotion_authorized,
            "acquisition_query_neutral": self.acquisition_query_neutral,
            "threshold_family_scope_authorized": (
                self.threshold_family_scope_authorized
            ),
            "unrestricted_reuse_authorized": (
                self.unrestricted_reuse_authorized
            ),
        }

    @property
    def eligibility_id(self) -> str:
        return _content_id("eligibility", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "eligibility_id": self.eligibility_id}


def _digest_document(document: Any) -> str:
    return hashlib.sha256(
        _canonical_json_bytes({"document": document})
    ).hexdigest()


def _proof_formula_registry_digest() -> str:
    return _digest_document(
        {
            "lower_parent_slots": {
                slot: list(parents)
                for slot, parents in _PARENT_SLOTS.items()
            },
            "lower_formula_ids": dict(_FORMULA_IDS),
            "relaxed_gate_formula_ids": {
                "REGRET": "REGRET_THRESHOLD_VERDICT_V0057",
                "RISK": "RISK_THRESHOLD_VERDICT_V0057",
            },
            "candidate_order": list(SCHEDULE_ORDER),
            "candidate_proof_role": "CANDIDATE_RANKING_AUDIT",
            "selected_proof_role": (
                "INDEPENDENT_SELECTED_PLAN_CERTIFICATE"
            ),
        }
    )


def _epoch_lineage_profile_id(base_model_id: str) -> str:
    return _domain_content_id(
        "acfqp:interleaved-epoch-lineage-profile:v1",
        {
            "schema": "acfqp.interleaved_epoch_lineage_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_profile_key": _LIVE_PROFILE_KEY,
            "base_model_id": _cid(
                base_model_id, "epoch-lineage base model"
            ),
            "round_order": [
                "FIRST_ROUND_ONE_4_PLUS_BOUNDARY_3",
                "CERTIFICATE_TRIGGERED_ROUND_TWO_9",
            ],
            "overlay_versions": [1, 2],
            "query_local": True,
            "promotion_authorized": False,
        },
    )


def _structural_state_action_concretizer_scope(
    model_document: Mapping[str, Any],
    return_bound_proof_document: Mapping[str, Any],
    semantics_profile_document: Mapping[str, Any],
) -> dict[str, Any]:
    model = _exact_mapping(
        model_document,
        set(model_document),
        "preregistration base-model document",
    )
    proof = _exact_mapping(
        return_bound_proof_document,
        set(return_bound_proof_document),
        "preregistration return-bound document",
    )
    semantics = _exact_mapping(
        semantics_profile_document,
        set(semantics_profile_document),
        "preregistration semantics-profile document",
    )
    required_model = {
        "semantics_profile_id",
        "semantics_horizon_cap",
        "coordinate_proposal_id",
        "cells",
        "semantic_actions",
        "semantic_realizations",
        "concretizer_rows",
        "reward_feature_caps",
    }
    if (
        not required_model <= set(model)
        or "structural_id" not in proof
        or "environment_instance_id" not in proof
        or "semantics_profile_id" not in proof
        or model["semantics_profile_id"] != proof["semantics_profile_id"]
        or semantics.get("profile_id") != model["semantics_profile_id"]
        or semantics.get("structural_id") != proof["structural_id"]
        or semantics.get("dynamics_assumption") is None
        or semantics.get("action_catalogue_semantics") is None
        or semantics.get("concretizer_rule") is None
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "preregistration structural scope is incomplete"
        )
    return {
        "schema": (
            "acfqp.interleaved_structural_state_action_"
            "concretizer_scope.v1"
        ),
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "base_model_id": model["model_id"],
        "structural_id": proof["structural_id"],
        "environment_instance_id": proof["environment_instance_id"],
        "semantics_profile": semantics,
        "coordinate_proposal_id": model["coordinate_proposal_id"],
        "base_cells": model["cells"],
        "base_semantic_actions": model["semantic_actions"],
        "base_semantic_realizations": model["semantic_realizations"],
        "base_concretizer_rows": model["concretizer_rows"],
        "reward_feature_caps": model["reward_feature_caps"],
    }


def _structural_state_action_concretizer_digest(
    scope_document: Mapping[str, Any],
) -> str:
    return _digest_document(scope_document)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_callable_source_sha256(path: Path, name: str) -> str:
    import ast

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    candidates = [
        item
        for item in tree.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name == name
    ]
    if len(candidates) != 1:
        raise InterleavedDurableEpochInvariantViolation(
            f"source pin callable {name} is absent or duplicated"
        )
    node = candidates[0]
    start = min(
        [node.lineno, *(item.lineno for item in node.decorator_list)]
    )
    lines = source.splitlines(keepends=True)
    segment = "".join(lines[start - 1 : node.end_lineno])
    return hashlib.sha256(segment.encode("utf-8")).hexdigest()


def _source_pin_actuals_v1() -> dict[str, str]:
    source_root = Path(__file__).resolve().parent
    paths = {
        "EXPECTED_ORCHESTRATOR_MODULE_SHA256": Path(__file__).resolve(),
        "EXPECTED_LIVE_MODULE_SHA256": (
            source_root / "live_query_local_epoch_invalidation_v1.py"
        ),
        "EXPECTED_TEMPORAL_MODULE_SHA256": (
            source_root / "h2_temporal_incremental_proof_dag_v1.py"
        ),
        "EXPECTED_MULTISTEP_MODULE_SHA256": (
            source_root / "multistep_query_refinement_v1.py"
        ),
        "EXPECTED_PLANNER_MODULE_SHA256": (
            source_root / "partial_model_planner_v1.py"
        ),
        "EXPECTED_AUDIT_MODULE_SHA256": (
            source_root / "partial_sound_audit_v1.py"
        ),
        "EXPECTED_DURABLE_TRANSPORT_MODULE_SHA256": (
            source_root / "h2_durable_action_switch_transport_v1.py"
        ),
    }
    actuals = {
        name: _file_sha256(path) for name, path in paths.items()
    }
    actuals.update(
        {
            "EXPECTED_MULTISTEP_ACQUIRE_SOURCE_SHA256": (
                _file_callable_source_sha256(
                    paths["EXPECTED_MULTISTEP_MODULE_SHA256"],
                    "_acquire",
                )
            ),
            "EXPECTED_MULTISTEP_ROUND_TWO_REQUEST_SOURCE_SHA256": (
                _file_callable_source_sha256(
                    paths["EXPECTED_MULTISTEP_MODULE_SHA256"],
                    "_round_two_request",
                )
            ),
            "EXPECTED_LIVE_DERIVE_DELTA_SOURCE_SHA256": (
                _file_callable_source_sha256(
                    paths["EXPECTED_LIVE_MODULE_SHA256"],
                    "_derive_delta",
                )
            ),
            "EXPECTED_PUBLIC_PRODUCER_SOURCE_SHA256": (
                _file_callable_source_sha256(
                    paths["EXPECTED_ORCHESTRATOR_MODULE_SHA256"],
                    "run_lmb_h2_interleaved_durable_epoch_v1",
                )
            ),
            "EXPECTED_WORKER_MAIN_SOURCE_SHA256": (
                _file_callable_source_sha256(
                    paths["EXPECTED_ORCHESTRATOR_MODULE_SHA256"],
                    "_worker_main",
                )
            ),
        }
    )
    return actuals


def _assert_source_pins(*, allow_runtime_imports: bool = True) -> None:
    import importlib
    import inspect
    import re

    pins = importlib.import_module(
        "acfqp.h2_interleaved_durable_epoch_pins_v1"
    )
    expected = {
        "EXPECTED_ORCHESTRATOR_MODULE_SHA256": (
            EXPECTED_ORCHESTRATOR_MODULE_SHA256
        ),
        "EXPECTED_LIVE_MODULE_SHA256": EXPECTED_LIVE_MODULE_SHA256,
        "EXPECTED_TEMPORAL_MODULE_SHA256": EXPECTED_TEMPORAL_MODULE_SHA256,
        "EXPECTED_MULTISTEP_MODULE_SHA256": EXPECTED_MULTISTEP_MODULE_SHA256,
        "EXPECTED_PLANNER_MODULE_SHA256": EXPECTED_PLANNER_MODULE_SHA256,
        "EXPECTED_AUDIT_MODULE_SHA256": EXPECTED_AUDIT_MODULE_SHA256,
        "EXPECTED_DURABLE_TRANSPORT_MODULE_SHA256": (
            EXPECTED_DURABLE_TRANSPORT_MODULE_SHA256
        ),
        "EXPECTED_MULTISTEP_ACQUIRE_SOURCE_SHA256": (
            EXPECTED_MULTISTEP_ACQUIRE_SOURCE_SHA256
        ),
        "EXPECTED_MULTISTEP_ROUND_TWO_REQUEST_SOURCE_SHA256": (
            EXPECTED_MULTISTEP_ROUND_TWO_REQUEST_SOURCE_SHA256
        ),
        "EXPECTED_LIVE_DERIVE_DELTA_SOURCE_SHA256": (
            EXPECTED_LIVE_DERIVE_DELTA_SOURCE_SHA256
        ),
        "EXPECTED_PUBLIC_PRODUCER_SOURCE_SHA256": (
            EXPECTED_PUBLIC_PRODUCER_SOURCE_SHA256
        ),
        "EXPECTED_WORKER_MAIN_SOURCE_SHA256": (
            EXPECTED_WORKER_MAIN_SOURCE_SHA256
        ),
    }
    actual = _source_pin_actuals_v1()
    if (
        set(actual) != set(expected)
        or any(
            type(value) is not str
            or re.fullmatch(r"[0-9a-f]{64}", value) is None
            or value == "0" * 64
            or getattr(pins, name, None) != value
            or actual[name] != value
            for name, value in expected.items()
        )
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "registered V0-057 source pin changed"
        )
    if allow_runtime_imports:
        multistep = importlib.import_module(
            "acfqp.multistep_query_refinement_v1"
        )
        live = importlib.import_module(
            "acfqp.live_query_local_epoch_invalidation_v1"
        )
        runtime_callables = (
            (
                multistep,
                "_acquire",
                EXPECTED_MULTISTEP_ACQUIRE_SOURCE_SHA256,
            ),
            (
                multistep,
                "_round_two_request",
                EXPECTED_MULTISTEP_ROUND_TWO_REQUEST_SOURCE_SHA256,
            ),
            (
                live,
                "_derive_delta",
                EXPECTED_LIVE_DERIVE_DELTA_SOURCE_SHA256,
            ),
        )
        for module, name, expected_digest in runtime_callables:
            candidate = getattr(module, name, None)
            if (
                not callable(candidate)
                or hashlib.sha256(
                    inspect.getsource(candidate).encode("utf-8")
                ).hexdigest()
                != expected_digest
            ):
                raise InterleavedDurableEpochInvariantViolation(
                    f"registered runtime callable {name} changed"
                )


_CANONICAL_SOURCE_PIN_ASSERT = _assert_source_pins


def _invoke_canonical_source_pin_assert(
    *,
    allow_runtime_imports: bool,
) -> None:
    if (
        globals().get("_assert_source_pins")
        is not _CANONICAL_SOURCE_PIN_ASSERT
        or globals().get("_CANONICAL_SOURCE_PIN_ASSERT")
        is not _CANONICAL_SOURCE_PIN_ASSERT
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "source-pin assertion authority was replaced"
        )
    _CANONICAL_SOURCE_PIN_ASSERT(
        allow_runtime_imports=allow_runtime_imports
    )


def _live_canonical_input_digest(document: Mapping[str, Any]) -> str:
    return _domain_content_id(
        _LIVE_DOMAIN_TAGS["canonical_input"],
        {
            "schema": "acfqp.live_epoch_canonical_input.v1",
            "schema_version": _LIVE_SCHEMA_VERSION,
            "profile_key": _LIVE_PROFILE_KEY,
            "document": document,
        },
    )


def _reward_cap_interval(model: Any, weights: Mapping[str, Fraction]) -> tuple[
    Fraction, Fraction
]:
    caps = {item.name: item for item in model.reward_feature_caps}
    lower = Fraction(0)
    upper = Fraction(0)
    for name, weight in weights.items():
        cap = caps[name]
        endpoints = (weight * cap.lower, weight * cap.upper)
        lower += min(endpoints)
        upper += max(endpoints)
    return lower, upper


def _recompute_candidate_value_documents(
    model: Any,
    thresholds: Any,
    plan: Any,
) -> dict[str, dict[str, Any]]:
    """Re-execute the ten active V0-053 lower formulas without importing it.

    Only transport/model/audit modules that have no ground kernel are loaded.
    The equations below are the frozen H=2 U/P/C/D/E/F/G recurrences; the
    resulting canonical documents must exactly equal the persisted values.
    """

    import acfqp.partial_sound_audit_v1 as audit

    active_cells = {
        item.cell_id: item
        for item in model.cells
        if item.planning_kind.value == "active"
    }
    active_ids = tuple(sorted(active_cells))
    state_to_cell = {
        state_id: cell_id
        for cell_id, cell in active_cells.items()
        for state_id in cell.member_state_ids
    }
    realizations: dict[tuple[str, str], tuple[Any, ...]] = {}
    for item in model.semantic_realizations:
        key = (item.cell_id, item.semantic_action_id)
        realizations[key] = (*realizations.get(key, ()), item)
    realizations = {
        key: tuple(sorted(rows, key=lambda item: item.state_id))
        for key, rows in realizations.items()
    }
    stage_maps = {
        stage.time_index: {
            item.cell_id: item.semantic_action_id
            for item in stage.assignments
        }
        for stage in plan.stages
    }
    if (
        set(stage_maps) != {0, 1}
        or any(set(mapping) != set(active_ids) for mapping in stage_maps.values())
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "candidate plan does not cover each active cell at H=2"
        )
    weights = {item.name: item.weight for item in thresholds.reward_weights}
    per_step_lower, per_step_upper = _reward_cap_interval(model, weights)
    return_upper = thresholds.return_bound_proof.return_upper

    def outside_bound(remaining: int) -> Any:
        return audit._outside_bound(
            remaining, per_step_lower, per_step_upper, return_upper
        )

    rows_by_state: dict[str, list[Any]] = {
        state_id: [] for state_id in state_to_cell
    }
    for row in model.ground_rows:
        if row.state_id in rows_by_state:
            rows_by_state[row.state_id].append(row)
    if any(not rows for rows in rows_by_state.values()):
        raise InterleavedDurableEpochInvariantViolation(
            "registered model lacks a complete active action catalogue"
        )

    def compute_u(
        time_index: int,
        parent_cell_upper: Mapping[str, Fraction] | None,
    ) -> tuple[dict[str, Any], dict[str, Fraction], dict[str, Fraction]]:
        remaining = 2 - time_index
        next_upper = {
            cell_id: (
                Fraction(0)
                if parent_cell_upper is None
                else parent_cell_upper[cell_id]
            )
            for cell_id in active_ids
        }
        outside = outside_bound(remaining - 1)
        state_upper: dict[str, Fraction] = {}
        proof_rows: list[dict[str, Any]] = []
        for state_id in sorted(rows_by_state):
            action_values: list[Fraction] = []
            cell_id = state_to_cell[state_id]
            for row in sorted(
                rows_by_state[state_id], key=lambda item: item.ground_row_id
            ):
                ambiguity = row.ambiguity
                _, upper = audit._reward_interval(ambiguity, weights)
                for destination, mass in ambiguity.known_successor_masses:
                    upper += mass * (
                        outside.reward_upper
                        if destination == model.external_boundary_id
                        else next_upper[destination]
                    )
                unknown = audit._validate_joint_simplex(ambiguity)
                if unknown:
                    upper += unknown * max(
                        Fraction(0),
                        outside.reward_upper,
                        *(next_upper[destination] for destination in active_ids),
                    )
                upper = min(return_upper, upper)
                action_values.append(upper)
                proof_rows.append(
                    {
                        "time_index": time_index,
                        "remaining_horizon": remaining,
                        "state_id": state_id,
                        "cell_id": cell_id,
                        "ground_row_id": row.ground_row_id,
                        "ground_action_id": row.ground_action_id,
                        "reward_upper": _fraction_document(upper),
                    }
                )
            state_upper[state_id] = max(action_values)
        cell_upper = {
            cell_id: max(
                state_upper[state_id]
                for state_id in active_cells[cell_id].member_state_ids
            )
            for cell_id in active_ids
        }
        document = {
            "time_index": time_index,
            "cell_upper": [
                {
                    "cell_id": key,
                    "reward_upper": _fraction_document(value),
                }
                for key, value in sorted(cell_upper.items())
            ],
            "state_upper": [
                {
                    "state_id": key,
                    "reward_upper": _fraction_document(value),
                }
                for key, value in sorted(state_upper.items())
            ],
            "rows": sorted(
                proof_rows,
                key=lambda row: (
                    row["time_index"],
                    row["state_id"],
                    row["ground_row_id"],
                ),
            ),
        }
        return document, cell_upper, state_upper

    u1, u1_cells, _ = compute_u(1, None)
    u0, _, u0_states = compute_u(0, u1_cells)

    def compute_p(
        time_index: int,
        parent_table: Mapping[str, Any] | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        remaining = 2 - time_index
        next_by_cell = {
            cell_id: (
                audit._Bound(
                    Fraction(0), Fraction(0), Fraction(0), Fraction(0)
                )
                if parent_table is None
                else parent_table[cell_id]
            )
            for cell_id in active_ids
        }
        outside = outside_bound(remaining - 1)
        table: dict[str, Any] = {}
        rows: list[dict[str, Any]] = []
        assignment = stage_maps[time_index]
        for cell_id in active_ids:
            action_id = assignment[cell_id]
            state_rows = realizations[(cell_id, action_id)]
            state_bounds = tuple(
                audit._realization_bound(
                    item.ambiguity,
                    next_by_cell,
                    active_ids,
                    model.external_boundary_id,
                    outside,
                    weights,
                    return_upper,
                )
                for item in state_rows
            )
            bound = audit._Bound(
                min(item.reward_lower for item in state_bounds),
                max(item.reward_upper for item in state_bounds),
                min(item.failure_lower for item in state_bounds),
                max(item.failure_upper for item in state_bounds),
            )
            table[cell_id] = bound
            ambiguity_documents = tuple(
                item.ambiguity.to_document() for item in state_rows
            )
            rows.append(
                {
                    "time_index": time_index,
                    "remaining_horizon": remaining,
                    "cell_id": cell_id,
                    "action_id": action_id,
                    "representative_state_ids": [
                        item.state_id for item in state_rows
                    ],
                    "missing_ground_row_ids": sorted(
                        {
                            row_id
                            for item in state_rows
                            for row_id in item.missing_ground_row_ids
                        }
                    ),
                    "reward_lower": _fraction_document(bound.reward_lower),
                    "reward_upper": _fraction_document(bound.reward_upper),
                    "failure_lower": _fraction_document(bound.failure_lower),
                    "failure_upper": _fraction_document(bound.failure_upper),
                    "max_shared_unknown_mass": _fraction_document(
                        max(
                            item.ambiguity.joint_simplex_constraint
                            .unknown_atom_mass_sum
                            for item in state_rows
                        )
                    ),
                    "external_boundary_possible": any(
                        item.ambiguity.joint_simplex_constraint
                        .unknown_atom_mass_sum
                        > 0
                        or dict(item.ambiguity.known_successor_masses).get(
                            model.external_boundary_id, Fraction(0)
                        )
                        > 0
                        for item in state_rows
                    ),
                    "representative_disagreement": any(
                        document != ambiguity_documents[0]
                        for document in ambiguity_documents[1:]
                    ),
                }
            )
        return (
            {
                "time_index": time_index,
                "rows": sorted(
                    rows,
                    key=lambda row: (row["time_index"], row["cell_id"]),
                ),
            },
            table,
        )

    p1, p1_table = compute_p(1, None)
    p0, p0_table = compute_p(0, p1_table)

    def compute_c(
        time_index: int,
        parent_next_reach: Mapping[str, Fraction] | None,
    ) -> tuple[
        dict[str, Any],
        dict[str, Fraction],
        tuple[tuple[int, str], ...],
    ]:
        if parent_next_reach is None:
            reach: dict[str, Fraction] = {}
            for item in thresholds.initial_state_distribution:
                cell_id = state_to_cell[item.state_id]
                reach[cell_id] = reach.get(cell_id, Fraction(0)) + item.probability
        else:
            reach = dict(parent_next_reach)
        remaining = 2 - time_index
        next_reach: dict[str, Fraction] = {}
        rows: list[dict[str, Any]] = []
        pairs: list[tuple[int, str]] = []
        assignment = stage_maps[time_index]
        for cell_id in sorted(reach):
            cell_mass = reach[cell_id]
            if not cell_mass:
                continue
            pairs.append((time_index, cell_id))
            action_id = assignment[cell_id]
            state_rows = realizations[(cell_id, action_id)]
            ambiguity_documents = tuple(
                item.ambiguity.to_document() for item in state_rows
            )
            disagreement = any(
                document != ambiguity_documents[0]
                for document in ambiguity_documents[1:]
            )
            for item in state_rows:
                unknown = audit._validate_joint_simplex(item.ambiguity)
                known_external = dict(
                    item.ambiguity.known_successor_masses
                ).get(model.external_boundary_id, Fraction(0))
                rows.append(
                    {
                        "time_index": time_index,
                        "remaining_horizon": remaining,
                        "state_id": item.state_id,
                        "cell_id": cell_id,
                        "action_id": action_id,
                        "support_ground_row_ids": list(
                            item.support_ground_row_ids
                        ),
                        "observed_ground_row_ids": list(
                            item.observed_ground_row_ids
                        ),
                        "missing_ground_row_ids": list(
                            item.missing_ground_row_ids
                        ),
                        "reachable_cell_mass_upper": _fraction_document(
                            cell_mass
                        ),
                        "shared_unknown_mass": _fraction_document(unknown),
                        "known_external_successor_mass": _fraction_document(
                            known_external
                        ),
                        "reachable_unknown_mass_upper": _fraction_document(
                            cell_mass * unknown
                        ),
                        "reachable_external_continuation_mass_upper": (
                            _fraction_document(
                                cell_mass * known_external
                                if remaining > 1
                                else Fraction(0)
                            )
                        ),
                        "representative_disagreement": disagreement,
                        "realization_singleton": item.ambiguity.is_singleton,
                    }
                )
            if remaining > 1:
                for destination in active_ids:
                    upper = max(
                        dict(item.ambiguity.known_successor_masses).get(
                            destination, Fraction(0)
                        )
                        + audit._validate_joint_simplex(item.ambiguity)
                        for item in state_rows
                    )
                    if upper:
                        next_reach[destination] = min(
                            Fraction(1),
                            next_reach.get(destination, Fraction(0))
                            + cell_mass * upper,
                        )
        canonical_pairs = tuple(sorted(set(pairs)))
        document = {
            "time_index": time_index,
            "next_reach": [
                {"cell_id": key, "mass_upper": _fraction_document(value)}
                for key, value in sorted(next_reach.items())
            ],
            "rows": sorted(
                rows,
                key=lambda row: (
                    row["time_index"],
                    row["cell_id"],
                    row["state_id"],
                    row["action_id"],
                ),
            ),
            "reachable_pairs": [
                {"time_index": time, "cell_id": cell_id}
                for time, cell_id in canonical_pairs
            ],
        }
        return document, next_reach, canonical_pairs

    c0, c0_next, c0_pairs = compute_c(0, None)
    c1, _, c1_pairs = compute_c(1, c0_next)

    table = {
        (1, cell_id): bound for cell_id, bound in p1_table.items()
    } | {
        (0, cell_id): bound for cell_id, bound in p0_table.items()
    }
    initial_bounds = audit._build_initial_support_bounds(
        model,
        thresholds,
        active_cells,
        realizations,
        stage_maps,
        state_to_cell,
        table,
    )
    unrestricted_upper = sum(
        (
            support.probability * u0_states[support.state_id]
            for support in thresholds.initial_state_distribution
        ),
        Fraction(0),
    )
    root_reward_lower = sum(
        (
            support.probability
            * initial_bounds[support.state_id].reward_lower
            for support in thresholds.initial_state_distribution
        ),
        Fraction(0),
    )
    root_reward_upper = min(
        return_upper,
        sum(
            (
                support.probability
                * initial_bounds[support.state_id].reward_upper
                for support in thresholds.initial_state_distribution
            ),
            Fraction(0),
        ),
    )
    root_failure_lower = sum(
        (
            support.probability
            * initial_bounds[support.state_id].failure_lower
            for support in thresholds.initial_state_distribution
        ),
        Fraction(0),
    )
    root_failure_upper = sum(
        (
            support.probability
            * initial_bounds[support.state_id].failure_upper
            for support in thresholds.initial_state_distribution
        ),
        Fraction(0),
    )
    support_metrics = tuple(
        (
            support.state_id,
            state_to_cell[support.state_id],
            support.probability,
            u0_states[support.state_id],
            initial_bounds[support.state_id].reward_lower,
            (
                u0_states[support.state_id]
                - initial_bounds[support.state_id].reward_lower
            ),
            (
                u0_states[support.state_id]
                - initial_bounds[support.state_id].reward_lower
            )
            / return_upper,
        )
        for support in thresholds.initial_state_distribution
    )
    raw_regret = unrestricted_upper - root_reward_lower
    d = {
        "unrestricted_upper": _fraction_document(unrestricted_upper),
        "root_reward_lower": _fraction_document(root_reward_lower),
        "root_reward_upper": _fraction_document(root_reward_upper),
        "root_failure_lower": _fraction_document(root_failure_lower),
        "root_failure_upper": _fraction_document(root_failure_upper),
        "raw_distribution_regret": _fraction_document(raw_regret),
        "normalized_distribution_regret": _fraction_document(
            raw_regret / return_upper
        ),
        "reachable_state_time_cell_count": len(
            set((*c0_pairs, *c1_pairs))
        ),
        "support_metrics": [
            {
                "state_id": state_id,
                "cell_id": cell_id,
                "probability": _fraction_document(probability),
                "unrestricted_upper": _fraction_document(unrestricted),
                "policy_lower": _fraction_document(policy_lower),
                "raw_regret": _fraction_document(raw),
                "normalized_regret": _fraction_document(normalized),
            }
            for (
                state_id,
                cell_id,
                probability,
                unrestricted,
                policy_lower,
                raw,
                normalized,
            ) in support_metrics
        ],
    }
    e = {
        "support_certified": [
            normalized <= thresholds.normalized_regret_tolerance
            for *_, normalized in support_metrics
        ],
        "reward_certified": all(
            normalized <= thresholds.normalized_regret_tolerance
            for *_, normalized in support_metrics
        ),
    }
    f = {
        "risk_certified": (
            root_failure_upper <= thresholds.risk_tolerance
        )
    }
    c_rows = sorted(
        [*c0["rows"], *c1["rows"]],
        key=lambda row: (
            row["time_index"],
            row["cell_id"],
            row["state_id"],
            row["action_id"],
        ),
    )
    external_indices = [
        index
        for index, row in enumerate(c_rows)
        if row["remaining_horizon"] > 1
        and (
            _parse_fraction(
                row["reachable_external_continuation_mass_upper"],
                "recomputed C external mass",
            )
            > 0
            or _parse_fraction(
                row["reachable_unknown_mass_upper"],
                "recomputed C unknown mass",
            )
            > 0
        )
    ]
    g = {
        "external_row_indices": external_indices,
        "coverage_certified": not external_indices,
    }
    return {
        "U1": u1,
        "U0": u0,
        "P1": p1,
        "P0": p0,
        "C0": c0,
        "C1": c1,
        "D": d,
        "E": e,
        "F": f,
        "G": g,
    }


def _checkpoint_payload_id(payload: Mapping[str, Any]) -> str:
    body = dict(payload)
    body.pop("payload_id", None)
    return _content_id("checkpoint_payload", body)


def _checkpoint_commit_id(commit: Mapping[str, Any]) -> str:
    body = dict(commit)
    body.pop("commit_id", None)
    return _content_id("checkpoint_commit", body)


def _write_checkpoint(
    root: Path,
    payload_body: Mapping[str, Any],
    *,
    generation: int,
    previous_commit_id: str | None,
    predecessor_store_root: Path | None,
) -> dict[str, Any]:
    if generation not in {1, 2} or (generation == 1) is not (
        previous_commit_id is None and predecessor_store_root is None
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint writer predecessor scope changed"
        )
    if root.exists():
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint root already exists"
        )
    (root / "blobs").mkdir(parents=True)
    (root / "commits").mkdir()
    payload = dict(payload_body)
    payload["payload_id"] = _checkpoint_payload_id(payload)
    payload_bytes = _canonical_json_bytes(payload)
    commit_body = {
        "schema": "acfqp.interleaved_epoch_checkpoint_commit.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "generation": generation,
        "previous_commit_id": (
            previous_commit_id
            if previous_commit_id is not None
            else {"kind": "NOT_APPLICABLE", "reason": "FIRST_EPOCH"}
        ),
        "payload_id": payload["payload_id"],
        "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
        "payload_size_bytes": len(payload_bytes),
        "commit_complete": True,
    }
    commit = {
        **commit_body,
        "commit_id": _content_id("checkpoint_commit", commit_body),
    }
    _write_exclusive(
        root / "blobs" / f"{payload['payload_id']}.json",
        payload,
    )
    _write_exclusive(
        root / "commits" / f"{commit['commit_id']}.json",
        commit,
    )
    loaded, _ = _load_checkpoint(
        root,
        commit["commit_id"],
        expected_previous_commit_id=previous_commit_id,
        predecessor_store_root=predecessor_store_root,
    )
    if loaded != payload:
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint reread changed"
        )
    return commit


def _load_checkpoint(
    root: Path,
    expected_commit_id: str,
    *,
    expected_previous_commit_id: str | None,
    predecessor_store_root: Path | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    expected = _cid(expected_commit_id, "expected checkpoint commit")
    if (
        not root.is_dir()
        or root.is_symlink()
        or {item.name for item in root.iterdir()} != {"blobs", "commits"}
        or any(
            path.is_symlink() or not path.is_dir()
            for path in (root / "blobs", root / "commits")
        )
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint topology changed"
        )
    commits = tuple((root / "commits").iterdir())
    blobs = tuple((root / "blobs").iterdir())
    if len(commits) != 1 or len(blobs) != 1:
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint file cardinality changed"
        )
    commit = _exact_mapping(
        _read_canonical(
            root / "commits" / f"{expected}.json"
        )[0],
        {
            "schema",
            "schema_version",
            "profile_key",
            "generation",
            "previous_commit_id",
            "payload_id",
            "payload_sha256",
            "payload_size_bytes",
            "commit_complete",
            "commit_id",
        },
        "checkpoint commit",
    )
    if (
        commit["schema"]
        != "acfqp.interleaved_epoch_checkpoint_commit.v1"
        or commit["schema_version"] != SCHEMA_VERSION
        or commit["profile_key"] != PROFILE_KEY
        or commit["commit_id"] != expected
        or _checkpoint_commit_id(commit) != expected
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint commit identity changed"
        )
    generation = commit.get("generation")
    if (
        generation == 1
        and (
            expected_previous_commit_id is not None
            or predecessor_store_root is not None
        )
    ) or (
        generation == 2
        and (
            expected_previous_commit_id is None
            or not isinstance(predecessor_store_root, Path)
        )
    ) or generation not in {1, 2}:
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint external predecessor arguments changed"
        )
    predecessor_payload: dict[str, Any] | None = None
    predecessor_commit: dict[str, Any] | None = None
    if generation == 2:
        assert expected_previous_commit_id is not None
        assert predecessor_store_root is not None
        predecessor_payload, predecessor_commit = _load_checkpoint(
            predecessor_store_root,
            expected_previous_commit_id,
            expected_previous_commit_id=None,
            predecessor_store_root=None,
        )
        if (
            commit["previous_commit_id"]
            != predecessor_commit["commit_id"]
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "checkpoint external predecessor identity changed"
            )
    payload_id = _cid(commit.get("payload_id"), "checkpoint payload")
    payload_path = root / "blobs" / f"{payload_id}.json"
    payload, payload_size = _read_canonical(payload_path)
    payload_bytes = _canonical_json_bytes(payload)
    if (
        payload.get("payload_id") != payload_id
        or _checkpoint_payload_id(payload) != payload_id
        or commit.get("payload_sha256")
        != hashlib.sha256(payload_bytes).hexdigest()
        or commit.get("payload_size_bytes") != payload_size
        or commit.get("commit_complete") is not True
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint payload/commit binding changed"
        )
    _validate_checkpoint_payload(payload)
    expected_generation = (
        1 if payload["epoch_name"] == "FIRST" else 2
    )
    if (
        commit["generation"] != expected_generation
        or (
            expected_generation == 1
            and (
                expected_previous_commit_id is not None
                or commit["previous_commit_id"]
                != {
                    "kind": "NOT_APPLICABLE",
                    "reason": "FIRST_EPOCH",
                }
            )
        )
        or (
            expected_generation == 2
            and (
                expected_previous_commit_id is None
                or commit["previous_commit_id"]
                != _cid(
                    expected_previous_commit_id,
                    "expected previous checkpoint",
                )
            )
        )
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint generation/predecessor semantics changed"
        )
    if predecessor_payload is not None:
        assert predecessor_commit is not None
        _validate_cross_store_checkpoint_lineage(
            predecessor_payload,
            predecessor_commit,
            payload,
            commit,
        )
    return payload, commit


def _validate_checkpoint_payload(payload: Mapping[str, Any]) -> None:
    required = {
        "schema",
        "schema_version",
        "profile_key",
        "epoch_name",
        "model_id",
        "model_document",
        "preregistration_document",
        "source_strict_thresholds_document",
        "eligibility",
        "union_lower_entries",
        "active_lower_entry_ids",
        "inactive_lower_entry_ids",
        "candidate_metrics",
        "persisted_root_count",
        "payload_id",
    }
    if set(payload) != required:
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint payload field set changed"
        )
    epoch = payload["epoch_name"]
    expected = {
        "FIRST": (30, 30, 0),
        "FINAL": (58, 30, 28),
    }
    if epoch not in expected:
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint epoch changed"
        )
    if (
        payload["schema"] != "acfqp.interleaved_epoch_checkpoint_payload.v1"
        or payload["schema_version"] != SCHEMA_VERSION
        or payload["profile_key"] != PROFILE_KEY
        or payload["model_id"] != _EXPECTED_EPOCH_MODEL_IDS[epoch]
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint schema/profile/registered model changed"
        )
    try:
        from acfqp.h2_durable_transport_v1 import (
            parse_frozen_partial_audit_thresholds_v1,
            parse_query_scoped_partial_rapm_v3,
        )

        model = parse_query_scoped_partial_rapm_v3(payload["model_document"])
        strict_thresholds = parse_frozen_partial_audit_thresholds_v1(
            payload["source_strict_thresholds_document"]
        )
        preregistration = _validate_preregistration_document(
            payload["preregistration_document"]
        )
    except Exception as error:
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint model/threshold transport reconstruction failed"
        ) from error
    model_body = dict(payload["model_document"])
    model_identity = model_body.pop("model_id", None)
    if (
        model.to_document() != payload["model_document"]
        or model_identity != _domain_content_id(_MODEL_DOMAIN_TAG, model_body)
        or model_identity != payload["model_id"]
        or strict_thresholds.to_document()
        != payload["source_strict_thresholds_document"]
        or strict_thresholds.partial_model_id != model.model_id
        or strict_thresholds.horizon != 2
        or strict_thresholds.normalized_regret_tolerance != 0
        or strict_thresholds.risk_tolerance != 0
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint model/strict-threshold semantics changed"
        )
    union_count, active_count, inactive_count = expected[epoch]
    union = payload["union_lower_entries"]
    active = payload["active_lower_entry_ids"]
    inactive = payload["inactive_lower_entry_ids"]
    metrics = payload["candidate_metrics"]
    if (
        type(union) is not list
        or len(union) != union_count
        or type(active) is not list
        or len(active) != active_count
        or type(inactive) is not list
        or len(inactive) != inactive_count
        or type(metrics) is not list
        or len(metrics) != 4
        or payload["persisted_root_count"] != 0
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint 30/58/28/root-free cardinality changed"
        )
    value_by_entry: dict[str, dict[str, Any]] = {}
    for item in union:
        entry_id = _validate_lower_value_record(
            item,
            model.model_id,
            strict_thresholds,
        )
        if entry_id in value_by_entry:
            raise InterleavedDurableEpochInvariantViolation(
                "checkpoint duplicated a lower entry"
            )
        value_by_entry[entry_id] = item
    entry_ids = list(value_by_entry)
    canonical_union = sorted(
        union,
        key=lambda item: (
            LOWER_SLOTS.index(item["entry"]["key"]["slot"]),
            item["entry"]["key"]["node_key_id"],
        ),
    )
    if (
        union != canonical_union
        or active != sorted(set(active))
        or inactive != sorted(set(inactive))
        or set(active) | set(inactive) != set(entry_ids)
        or set(active) & set(inactive)
        or any(_cid(value, "checkpoint active/inactive entry") != value for value in (*active, *inactive))
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint active/inactive partition changed"
        )
    if tuple(item.get("schedule_code") for item in metrics) != SCHEDULE_ORDER:
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint candidate order changed"
        )
    _validate_and_rederive_candidate_metrics(
        metrics,
        value_by_entry,
        set(active),
        model,
        strict_thresholds,
        epoch,
    )
    eligibility = _exact_mapping(
        payload["eligibility"],
        {
            "schema",
            "schema_version",
            "profile_key",
            "preregistration_id",
            "model_id",
            "source_strict_thresholds_id",
            "epoch_strict_thresholds_id",
            "query_ids",
            "horizon",
            "initial_distribution_digest",
            "reward_basis_digest",
            "model_semantic_digest",
            "epoch_name",
            "model_query_local",
            "model_promotion_authorized",
            "acquisition_query_neutral",
            "threshold_family_scope_authorized",
            "unrestricted_reuse_authorized",
            "eligibility_id",
        },
        "checkpoint eligibility",
    )
    eligibility_body = dict(eligibility)
    eligibility_identity = eligibility_body.pop("eligibility_id")
    initial_digest = _live_canonical_input_digest(
        {
            "initial_distribution": [
                item.to_document()
                for item in strict_thresholds.initial_state_distribution
            ]
        }
    )
    reward_digest = _live_canonical_input_digest(
        {
            "reward_weights": [
                item.to_document() for item in strict_thresholds.reward_weights
            ]
        }
    )
    if (
        eligibility["schema"]
        != "acfqp.epoch_threshold_family_eligibility.v1"
        or eligibility["schema_version"] != SCHEMA_VERSION
        or eligibility["profile_key"] != PROFILE_KEY
        or eligibility_identity != _content_id("eligibility", eligibility_body)
        or eligibility["model_id"] != payload["model_id"]
        or eligibility["source_strict_thresholds_id"]
        != preregistration.source_strict_thresholds_id
        or eligibility["epoch_strict_thresholds_id"]
        != strict_thresholds.thresholds_id
        or eligibility["preregistration_id"]
        != preregistration.preregistration_id
        or eligibility["query_ids"]
        != [
            item.query_id for item in registered_interleaved_queries_v1()
        ]
        or eligibility["horizon"] != 2
        or preregistration.horizon != strict_thresholds.horizon
        or eligibility["initial_distribution_digest"] != initial_digest
        or preregistration.initial_distribution_digest != initial_digest
        or eligibility["reward_basis_digest"] != reward_digest
        or preregistration.reward_basis_digest != reward_digest
        or eligibility["model_semantic_digest"]
        != _digest_document(payload["model_document"])
        or eligibility["epoch_name"] != epoch
        or payload["model_document"].get("base_model_id")
        != preregistration.base_model_id
        or payload["model_document"].get("coordinate_proposal_id")
        != preregistration.coordinate_proposal_id
        or payload["model_document"].get("semantics_profile_id")
        != preregistration.input_authority_ids["semantics_profile_id"]
        or preregistration.return_bound_proof_id
        != payload["source_strict_thresholds_document"][
            "return_bound_proof"
        ]["proof_id"]
        or preregistration.return_bound_formula_id
        != payload["source_strict_thresholds_document"][
            "return_bound_proof"
        ]["formula_id"]
        or preregistration.goal_id
        != payload["source_strict_thresholds_document"]["goal_id"]
        or preregistration.unrestricted_upper_formula_id
        != payload["source_strict_thresholds_document"][
            "unrestricted_upper_formula_id"
        ]
        or preregistration.structural_id
        != payload["source_strict_thresholds_document"][
            "return_bound_proof"
        ]["structural_id"]
        or preregistration.environment_instance_id
        != payload["source_strict_thresholds_document"][
            "return_bound_proof"
        ]["environment_instance_id"]
        or preregistration.return_upper
        != _parse_fraction(
            payload["source_strict_thresholds_document"][
                "return_bound_proof"
            ]["return_upper"],
            "checkpoint preregistered return upper",
        )
        or preregistration.candidate_order != SCHEDULE_ORDER
        or preregistration.proof_formula_registry_digest
        != _proof_formula_registry_digest()
        or preregistration.threshold_only_variation is not True
        or eligibility["model_query_local"] is not True
        or eligibility["model_promotion_authorized"] is not False
        or eligibility["acquisition_query_neutral"] is not False
        or eligibility["threshold_family_scope_authorized"] is not True
        or eligibility["unrestricted_reuse_authorized"] is not False
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint eligibility binding changed"
        )


def _validate_cross_store_checkpoint_lineage(
    first_payload: Mapping[str, Any],
    first_commit: Mapping[str, Any],
    final_payload: Mapping[str, Any],
    final_commit: Mapping[str, Any],
) -> None:
    if (
        first_payload.get("epoch_name") != "FIRST"
        or final_payload.get("epoch_name") != "FINAL"
        or first_commit.get("generation") != 1
        or final_commit.get("generation") != 2
        or final_commit.get("previous_commit_id")
        != first_commit.get("commit_id")
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "cross-store checkpoint epoch lineage changed"
        )
    first_records = {
        item["entry"]["entry_id"]: item
        for item in first_payload["union_lower_entries"]
    }
    final_records = {
        item["entry"]["entry_id"]: item
        for item in final_payload["union_lower_entries"]
    }
    first_active = set(first_payload["active_lower_entry_ids"])
    final_active = set(final_payload["active_lower_entry_ids"])
    final_inactive = set(final_payload["inactive_lower_entry_ids"])
    shared = first_active & final_active
    if (
        set(first_records) != first_active
        or set(final_records) != first_active | final_active
        or len(shared) != 2
        or {
            final_records[entry_id]["entry"]["key"]["slot"]
            for entry_id in shared
        }
        != {"C0"}
        or final_inactive != first_active - shared
        or len(final_inactive) != 28
        or any(
            final_records[entry_id] != first_records[entry_id]
            for entry_id in first_active
        )
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "C2 union does not preserve the exact verified C1 history"
        )


def _lower_value_id(document: Mapping[str, Any]) -> str:
    body = dict(document)
    body.pop("value_id", None)
    return _content_id("lower_value", body)


def _validate_value_document_shape(slot: str, document: Any) -> None:
    if slot in {"U1", "U0"}:
        value = _exact_mapping(
            document,
            {"time_index", "cell_upper", "state_upper", "rows"},
            f"{slot} value",
        )
        if (
            type(value["cell_upper"]) is not list
            or type(value["state_upper"]) is not list
            or type(value["rows"]) is not list
        ):
            raise InterleavedDurableEpochInvariantViolation(
                f"{slot} value arrays changed"
            )
        row_fields = {
            "time_index",
            "remaining_horizon",
            "state_id",
            "cell_id",
            "ground_row_id",
            "ground_action_id",
            "reward_upper",
        }
        for row in value["rows"]:
            _exact_mapping(row, row_fields, f"{slot} row")
    elif slot in {"P1", "P0"}:
        value = _exact_mapping(
            document, {"time_index", "rows"}, f"{slot} value"
        )
        if type(value["rows"]) is not list:
            raise InterleavedDurableEpochInvariantViolation(
                f"{slot} rows changed"
            )
        row_fields = {
            "time_index",
            "remaining_horizon",
            "cell_id",
            "action_id",
            "representative_state_ids",
            "missing_ground_row_ids",
            "reward_lower",
            "reward_upper",
            "failure_lower",
            "failure_upper",
            "max_shared_unknown_mass",
            "external_boundary_possible",
            "representative_disagreement",
        }
        for row in value["rows"]:
            _exact_mapping(row, row_fields, f"{slot} row")
    elif slot in {"C0", "C1"}:
        value = _exact_mapping(
            document,
            {"time_index", "next_reach", "rows", "reachable_pairs"},
            f"{slot} value",
        )
        if (
            type(value["next_reach"]) is not list
            or type(value["rows"]) is not list
            or type(value["reachable_pairs"]) is not list
        ):
            raise InterleavedDurableEpochInvariantViolation(
                f"{slot} value arrays changed"
            )
        row_fields = {
            "time_index",
            "remaining_horizon",
            "state_id",
            "cell_id",
            "action_id",
            "support_ground_row_ids",
            "observed_ground_row_ids",
            "missing_ground_row_ids",
            "reachable_cell_mass_upper",
            "shared_unknown_mass",
            "known_external_successor_mass",
            "reachable_unknown_mass_upper",
            "reachable_external_continuation_mass_upper",
            "representative_disagreement",
            "realization_singleton",
        }
        for row in value["rows"]:
            _exact_mapping(row, row_fields, f"{slot} row")
    elif slot == "D":
        value = _exact_mapping(
            document,
            {
                "unrestricted_upper",
                "root_reward_lower",
                "root_reward_upper",
                "root_failure_lower",
                "root_failure_upper",
                "raw_distribution_regret",
                "normalized_distribution_regret",
                "reachable_state_time_cell_count",
                "support_metrics",
            },
            "D value",
        )
        if type(value["support_metrics"]) is not list:
            raise InterleavedDurableEpochInvariantViolation(
                "D support metrics changed"
            )
        for row in value["support_metrics"]:
            _exact_mapping(
                row,
                {
                    "state_id",
                    "cell_id",
                    "probability",
                    "unrestricted_upper",
                    "policy_lower",
                    "raw_regret",
                    "normalized_regret",
                },
                "D support metric",
            )
    elif slot == "E":
        _exact_mapping(
            document, {"support_certified", "reward_certified"}, "E value"
        )
    elif slot == "F":
        _exact_mapping(document, {"risk_certified"}, "F value")
    elif slot == "G":
        _exact_mapping(
            document, {"external_row_indices", "coverage_certified"}, "G value"
        )
    else:
        raise InterleavedDurableEpochInvariantViolation(
            "checkpoint persisted a root or unknown slot"
        )


def _validate_lower_value_record(
    document: Mapping[str, Any],
    model_id: str,
    strict_thresholds: Any,
) -> str:
    record = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "entry",
            "slice_content",
            "value_document",
            "value_id",
        },
        "lower proof value",
    )
    if (
        record["schema"] != "acfqp.interleaved_lower_proof_value.v1"
        or record["schema_version"] != SCHEMA_VERSION
        or record["profile_key"] != PROFILE_KEY
        or record["value_id"] != _lower_value_id(record)
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "lower proof value identity changed"
        )
    content = _exact_mapping(
        record["slice_content"],
        {
            "schema",
            "schema_version",
            "profile_key",
            "slot",
            "time_index",
            "stage_assignment_id",
            "input_ground_row_ids",
            "canonical_input_digest",
            "facet_kind",
            "content_id",
        },
        "live slice content",
    )
    content_body = dict(content)
    content_identity = content_body.pop("content_id")
    if (
        content["schema"] != "acfqp.model_slice_content.v1"
        or content["schema_version"] != _LIVE_SCHEMA_VERSION
        or content["profile_key"] != _LIVE_PROFILE_KEY
        or content_identity
        != _domain_content_id(_LIVE_DOMAIN_TAGS["slice_content"], content_body)
        or type(content["input_ground_row_ids"]) is not list
        or content["input_ground_row_ids"]
        != sorted(set(content["input_ground_row_ids"]))
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "live slice content identity changed"
        )
    entry = _exact_mapping(
        record["entry"],
        {
            "schema",
            "schema_version",
            "profile_key",
            "key",
            "result_digest",
            "result_semantics",
            "entry_id",
        },
        "live lower entry",
    )
    key = _exact_mapping(
        entry["key"],
        {
            "schema",
            "schema_version",
            "profile_key",
            "slot",
            "semantics_id",
            "model_slice_content_id",
            "time_index",
            "stage_assignment_id",
            "ordered_parent_entry_ids",
            "identity_terms",
            "node_key_id",
        },
        "live lower node key",
    )
    key_body = dict(key)
    key_identity = key_body.pop("node_key_id")
    entry_body = dict(entry)
    entry_identity = entry_body.pop("entry_id")
    slot = key["slot"]
    expected_time = {
        "U1": 1,
        "U0": 0,
        "P1": 1,
        "P0": 0,
        "C0": 0,
        "C1": 1,
        "D": None,
        "E": None,
        "F": None,
        "G": None,
    }.get(slot, object())
    if (
        entry["schema"] != "acfqp.live_epoch_proof_entry.v1"
        or entry["schema_version"] != _LIVE_SCHEMA_VERSION
        or entry["profile_key"] != _LIVE_PROFILE_KEY
        or key["schema"] != "acfqp.live_epoch_proof_node_key.v1"
        or key["schema_version"] != _LIVE_SCHEMA_VERSION
        or key["profile_key"] != _LIVE_PROFILE_KEY
        or key["semantics_id"] != _LIVE_SEMANTICS_ID
        or key["model_slice_content_id"] != content["content_id"]
        or key["time_index"] != expected_time
        or key["time_index"] != content["time_index"]
        or key["stage_assignment_id"] != content["stage_assignment_id"]
        or key_identity
        != _domain_content_id(_LIVE_DOMAIN_TAGS["node_key"], key_body)
        or entry_identity
        != _domain_content_id(_LIVE_DOMAIN_TAGS["entry"], entry_body)
        or entry["result_semantics"] != _RESULT_SEMANTICS.get(slot)
        or type(key["ordered_parent_entry_ids"]) is not list
        or len(key["ordered_parent_entry_ids"]) != len(_PARENT_SLOTS.get(slot, ()))
        or type(key["identity_terms"]) is not list
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "live lower entry/key semantics changed"
        )
    terms: dict[str, str] = {}
    for item in key["identity_terms"]:
        term = _exact_mapping(
            item, {"name", "value"}, "live lower identity term"
        )
        if (
            type(term["name"]) is not str
            or type(term["value"]) is not str
            or term["name"] in terms
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "live lower identity terms are not canonical"
            )
        terms[term["name"]] = term["value"]
    initial_digest = _live_canonical_input_digest(
        {
            "initial_distribution": [
                item.to_document()
                for item in strict_thresholds.initial_state_distribution
            ]
        }
    )
    reward_digest = _live_canonical_input_digest(
        {
            "reward_weights": [
                item.to_document() for item in strict_thresholds.reward_weights
            ]
        }
    )
    common = {
        "formula_id": _FORMULA_IDS[slot],
    }
    if slot in {"U1", "U0", "P1", "P0"}:
        expected_terms = {
            **common,
            "return_bound_proof_id": strict_thresholds.return_bound_proof.proof_id,
            "reward_weights_digest": reward_digest,
        }
    elif slot == "C0":
        expected_terms = {
            **common,
            "initial_distribution_digest": initial_digest,
        }
    elif slot == "C1":
        expected_terms = common
    elif slot == "D":
        expected_terms = {
            **common,
            "initial_distribution_digest": initial_digest,
            "return_bound_proof_id": strict_thresholds.return_bound_proof.proof_id,
            "reward_weights_digest": reward_digest,
        }
    elif slot == "E":
        expected_terms = {
            **common,
            "normalized_regret_tolerance": "0/1",
        }
    elif slot == "F":
        expected_terms = {**common, "risk_tolerance": "0/1"}
    else:
        expected_terms = common
    if (
        terms != expected_terms
        or key["identity_terms"]
        != [
            {"name": name, "value": value}
            for name, value in sorted(expected_terms.items())
        ]
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "live lower formula identity changed"
        )
    _validate_value_document_shape(slot, record["value_document"])
    result_digest = _domain_content_id(
        _LIVE_DOMAIN_TAGS["node_result"],
        {
            "schema": "acfqp.live_epoch_proof_node_result.v1",
            "schema_version": _LIVE_SCHEMA_VERSION,
            "profile_key": _LIVE_PROFILE_KEY,
            "slot": slot,
            "document": record["value_document"],
        },
    )
    if entry["result_digest"] != result_digest:
        raise InterleavedDurableEpochInvariantViolation(
            "persisted lower value differs from its live result digest"
        )
    return entry["entry_id"]


def _metric_id(document: Mapping[str, Any]) -> str:
    body = dict(document)
    body.pop("metric_id", None)
    return _content_id("metric", body)


def _validate_metric_document(document: Mapping[str, Any]) -> None:
    required = {
        "schema",
        "schema_version",
        "profile_key",
        "epoch_name",
        "model_id",
        "schedule_code",
        "semantic_key",
        "stage_assignment_ids",
        "plan_document",
        "plan_id",
        "reward_lower",
        "reward_upper",
        "failure_lower",
        "failure_upper",
        "normalized_regret",
        "external_coverage_certified",
        "ordered_lower_entry_ids",
        "strict_regret_entry_id",
        "strict_risk_entry_id",
        "metric_id",
    }
    if set(document) != required or document.get("metric_id") != _metric_id(document):
        raise InterleavedDurableEpochInvariantViolation(
            "candidate metric identity changed"
        )
    if (
        document["schedule_code"] not in SCHEDULE_ORDER
        or type(document["semantic_key"]) is not list
        or type(document["stage_assignment_ids"]) is not list
        or len(document["stage_assignment_ids"]) != 2
        or type(document["plan_document"]) is not dict
        or type(document["ordered_lower_entry_ids"]) is not list
        or len(document["ordered_lower_entry_ids"]) != 10
        or document["external_coverage_certified"] is not True
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "candidate metric semantics changed"
        )
    _cid(document["model_id"], "candidate metric model")
    _cid(document["plan_id"], "candidate metric plan")
    for value in (
        *document["stage_assignment_ids"],
        *document["ordered_lower_entry_ids"],
        document["strict_regret_entry_id"],
        document["strict_risk_entry_id"],
    ):
        _cid(value, "candidate metric lower entry")
    for name in (
        "reward_lower",
        "reward_upper",
        "failure_lower",
        "failure_upper",
        "normalized_regret",
    ):
        _parse_fraction(document[name], f"candidate metric {name}")


def _stage_assignment_document(
    assignment_index: int,
    plan_stage: Any,
    actions_by_id: Mapping[str, Any],
) -> dict[str, Any]:
    body = {
        "schema": "acfqp.h2_temporal_stage_assignment.v1",
        "schema_version": "1.0.0",
        "profile_key": _TEMPORAL_PROFILE_KEY,
        "assignment_index": assignment_index,
        "ordered_cell_action_labels": [
            {
                "cell_id": item.cell_id,
                "semantic_action_id": item.semantic_action_id,
                "label_values": [
                    int(value)
                    for value in actions_by_id[
                        item.semantic_action_id
                    ].label_values
                ],
            }
            for item in plan_stage.assignments
        ],
    }
    return {
        **body,
        "stage_assignment_id": _domain_content_id(
            _TEMPORAL_STAGE_DOMAIN_TAG, body
        ),
    }


def _validate_and_rederive_candidate_metrics(
    metrics: list[dict[str, Any]],
    value_by_entry: Mapping[str, dict[str, Any]],
    active_entry_ids: set[str],
    model: Any,
    strict_thresholds: Any,
    epoch: str,
) -> None:
    try:
        from acfqp.h2_durable_transport_v1 import (
            parse_frozen_contingent_abstract_plan_v1,
        )
    except Exception as error:
        raise InterleavedDurableEpochInvariantViolation(
            "candidate plan transport unavailable"
        ) from error
    actions_by_id = {
        item.semantic_action_id: item for item in model.semantic_actions
    }
    semantic_cell_order = tuple(
        item.cell_id
        for item in sorted(
            (
                item
                for item in model.cells
                if item.planning_kind.value == "active"
            ),
            key=lambda item: (
                item.coordinate_values,
                item.member_state_ids,
            ),
        )
    )
    parsed: list[tuple[dict[str, Any], Any, tuple[tuple[int, ...], ...]]] = []
    all_stage_keys: set[tuple[int, ...]] = set()
    for metric in metrics:
        _validate_metric_document(metric)
        try:
            plan = parse_frozen_contingent_abstract_plan_v1(
                metric["plan_document"]
            )
        except Exception as error:
            raise InterleavedDurableEpochInvariantViolation(
                "candidate plan transport reconstruction failed"
            ) from error
        if (
            plan.to_document() != metric["plan_document"]
            or plan.plan_id != metric["plan_id"]
            or plan.partial_model_id != model.model_id
            or plan.horizon != 2
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "candidate plan/model identity changed"
            )
        stage_keys_list = []
        for stage in plan.stages:
            mapping = {
                item.cell_id: item.semantic_action_id
                for item in stage.assignments
            }
            if set(mapping) != set(semantic_cell_order):
                raise InterleavedDurableEpochInvariantViolation(
                    "candidate stage does not cover canonical active cells"
                )
            stage_keys_list.append(
                tuple(
                    int(value)
                    for cell_id in semantic_cell_order
                    for value in actions_by_id[
                        mapping[cell_id]
                    ].label_values
                )
            )
        stage_keys = tuple(stage_keys_list)
        all_stage_keys.update(stage_keys)
        parsed.append((metric, plan, stage_keys))
    if len(all_stage_keys) != 2:
        raise InterleavedDurableEpochInvariantViolation(
            "registered model no longer exposes two canonical assignments"
        )
    ordered_stage_keys = tuple(sorted(all_stage_keys))
    for metric, plan, stage_keys in parsed:
        bits = tuple(ordered_stage_keys.index(item) for item in stage_keys)
        expected_code = {
            (0, 0): "A0A0",
            (0, 1): "A0A1",
            (1, 1): "A1A1",
            (1, 0): "A1A0",
        }.get(bits)
        stage_documents = tuple(
            _stage_assignment_document(
                ordered_stage_keys.index(stage_key),
                stage,
                actions_by_id,
            )
            for stage, stage_key in zip(plan.stages, stage_keys)
        )
        ordered_ids = metric["ordered_lower_entry_ids"]
        lineage_checks = {
            "schedule": expected_code == metric["schedule_code"],
            "semantic_key": metric["semantic_key"]
            == [value for stage_key in stage_keys for value in stage_key],
            "stage_assignment_ids": metric["stage_assignment_ids"]
            == [item["stage_assignment_id"] for item in stage_documents],
            "active_membership": not any(
                value not in active_entry_ids for value in ordered_ids
            ),
            "per_request_distinct": len(set(ordered_ids)) == 10,
        }
        if not all(lineage_checks.values()):
            raise InterleavedDurableEpochInvariantViolation(
                "candidate schedule/stage/lower lineage changed: "
                + ",".join(
                    name
                    for name, passed in lineage_checks.items()
                    if not passed
                )
            )
        records = [value_by_entry[value] for value in ordered_ids]
        slots = [item["entry"]["key"]["slot"] for item in records]
        if slots != list(LOWER_SLOTS):
            raise InterleavedDurableEpochInvariantViolation(
                "candidate lower entries are not in canonical slot order"
            )
        by_slot = dict(zip(slots, records))
        for slot, record in by_slot.items():
            expected_parents = [
                by_slot[parent]["entry"]["entry_id"]
                for parent in _PARENT_SLOTS[slot]
            ]
            key = record["entry"]["key"]
            expected_stage_id = {
                "P1": stage_documents[1]["stage_assignment_id"],
                "P0": stage_documents[0]["stage_assignment_id"],
                "C0": stage_documents[0]["stage_assignment_id"],
                "C1": stage_documents[1]["stage_assignment_id"],
                "D": stage_documents[0]["stage_assignment_id"],
            }.get(slot)
            if (
                key["ordered_parent_entry_ids"] != expected_parents
                or key["stage_assignment_id"] != expected_stage_id
            ):
                raise InterleavedDurableEpochInvariantViolation(
                    "candidate parent/stage topology changed"
                )
        expected_values = _recompute_candidate_value_documents(
            model, strict_thresholds, plan
        )
        if any(
            by_slot[slot]["value_document"] != expected_values[slot]
            for slot in LOWER_SLOTS
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "active lower payload differs from model-derived recurrence"
            )
        d_value = expected_values["D"]
        g_value = expected_values["G"]
        expected_body = {
            "schema": "acfqp.interleaved_candidate_metric.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "epoch_name": epoch,
            "model_id": model.model_id,
            "schedule_code": expected_code,
            "semantic_key": [
                value for stage_key in stage_keys for value in stage_key
            ],
            "stage_assignment_ids": [
                item["stage_assignment_id"] for item in stage_documents
            ],
            "plan_document": plan.to_document(),
            "plan_id": plan.plan_id,
            "reward_lower": d_value["root_reward_lower"],
            "reward_upper": d_value["root_reward_upper"],
            "failure_lower": d_value["root_failure_lower"],
            "failure_upper": d_value["root_failure_upper"],
            "normalized_regret": d_value[
                "normalized_distribution_regret"
            ],
            "external_coverage_certified": g_value[
                "coverage_certified"
            ],
            "ordered_lower_entry_ids": ordered_ids,
            "strict_regret_entry_id": by_slot["E"]["entry"]["entry_id"],
            "strict_risk_entry_id": by_slot["F"]["entry"]["entry_id"],
        }
        expected_metric = {
            **expected_body,
            "metric_id": _content_id("metric", expected_body),
        }
        if metric != expected_metric:
            raise InterleavedDurableEpochInvariantViolation(
                "candidate metric is not a D/G-derived exact projection"
            )


def _facet_payload_id(payload: Mapping[str, Any]) -> str:
    body = dict(payload)
    body.pop("payload_id", None)
    return _content_id("facet_payload", body)


def _facet_commit_id(commit: Mapping[str, Any]) -> str:
    body = dict(commit)
    body.pop("commit_id", None)
    return _content_id("facet_commit", body)


def _facet_payload(
    model_id: str,
    epoch_name: str,
    entries: list[dict[str, Any]],
    generation: int,
    previous_commit_id: str | None,
) -> dict[str, Any]:
    body = {
        "schema": "acfqp.interleaved_facet_store_payload.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "model_id": model_id,
        "epoch_name": epoch_name,
        "generation": generation,
        "previous_commit_id": (
            previous_commit_id
            if previous_commit_id is not None
            else {"kind": "NOT_APPLICABLE", "reason": "W0"}
        ),
        "entries": sorted(entries, key=lambda item: item["facet_entry_id"]),
    }
    return {**body, "payload_id": _content_id("facet_payload", body)}


def _facet_commit(payload: Mapping[str, Any]) -> dict[str, Any]:
    payload_bytes = _canonical_json_bytes(payload)
    body = {
        "schema": "acfqp.interleaved_facet_store_commit.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "model_id": payload["model_id"],
        "epoch_name": payload["epoch_name"],
        "generation": payload["generation"],
        "payload_id": payload["payload_id"],
        "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
        "payload_size_bytes": len(payload_bytes),
        "previous_commit_id": payload["previous_commit_id"],
        "commit_complete": True,
    }
    return {**body, "commit_id": _content_id("facet_commit", body)}


def _initialize_facet_store(
    root: Path,
    model_id: str,
    epoch_name: str,
) -> dict[str, Any]:
    if root.exists():
        raise InterleavedDurableEpochInvariantViolation(
            "facet-store root already exists"
        )
    (root / "blobs").mkdir(parents=True)
    (root / "commits").mkdir()
    payload = _facet_payload(model_id, epoch_name, [], 0, None)
    commit = _facet_commit(payload)
    _write_exclusive(root / "blobs" / f"{payload['payload_id']}.json", payload)
    _write_exclusive(root / "commits" / f"{commit['commit_id']}.json", commit)
    return commit


def _load_facet_store(
    root: Path,
    expected_commit_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    expected = _cid(expected_commit_id, "expected facet commit")
    if (
        not root.is_dir()
        or root.is_symlink()
        or {item.name for item in root.iterdir()} != {"blobs", "commits"}
        or any(
            path.is_symlink() or not path.is_dir()
            for path in (root / "blobs", root / "commits")
        )
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "facet store topology changed"
        )
    visited_commits: list[str] = []
    visited_payloads: list[str] = []
    payload_chain: list[dict[str, Any]] = []
    commit_chain: list[dict[str, Any]] = []
    current = expected
    while True:
        if current in visited_commits:
            raise InterleavedDurableEpochInvariantViolation(
                "facet predecessor chain contains a cycle"
            )
        commit = _exact_mapping(
            _read_canonical(
                root / "commits" / f"{current}.json"
            )[0],
            {
                "schema",
                "schema_version",
                "profile_key",
                "model_id",
                "epoch_name",
                "generation",
                "payload_id",
                "payload_sha256",
                "payload_size_bytes",
                "previous_commit_id",
                "commit_complete",
                "commit_id",
            },
            "facet commit",
        )
        if (
            commit["schema"] != "acfqp.interleaved_facet_store_commit.v1"
            or commit["schema_version"] != SCHEMA_VERSION
            or commit["profile_key"] != PROFILE_KEY
            or commit["commit_id"] != current
            or _facet_commit_id(commit) != current
            or commit["commit_complete"] is not True
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "facet commit identity changed"
            )
        payload_id = _cid(commit["payload_id"], "facet payload")
        payload, size = _read_canonical(
            root / "blobs" / f"{payload_id}.json"
        )
        payload = _exact_mapping(
            payload,
            {
                "schema",
                "schema_version",
                "profile_key",
                "model_id",
                "epoch_name",
                "generation",
                "previous_commit_id",
                "entries",
                "payload_id",
            },
            "facet payload",
        )
        if (
            payload["schema"] != "acfqp.interleaved_facet_store_payload.v1"
            or payload["schema_version"] != SCHEMA_VERSION
            or payload["profile_key"] != PROFILE_KEY
            or payload["payload_id"] != payload_id
            or _facet_payload_id(payload) != payload_id
            or commit["payload_sha256"]
            != hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
            or commit["payload_size_bytes"] != size
            or commit["model_id"] != payload["model_id"]
            or commit["epoch_name"] != payload["epoch_name"]
            or commit["generation"] != payload["generation"]
            or commit["previous_commit_id"] != payload["previous_commit_id"]
            or type(payload["entries"]) is not list
            or payload["entries"]
            != sorted(
                payload["entries"],
                key=lambda item: item.get("facet_entry_id", ""),
            )
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "facet payload/commit binding changed"
            )
        seen = set()
        for item in payload["entries"]:
            _validate_facet_entry(item)
            if (
                item["key"]["model_id"] != payload["model_id"]
                or item["facet_key_id"] in seen
            ):
                raise InterleavedDurableEpochInvariantViolation(
                    "facet store aliases a key or crosses model identity"
                )
            seen.add(item["facet_key_id"])
        visited_commits.append(current)
        visited_payloads.append(payload_id)
        payload_chain.append(payload)
        commit_chain.append(commit)
        previous = commit["previous_commit_id"]
        if commit["generation"] == 0:
            if previous != {"kind": "NOT_APPLICABLE", "reason": "W0"}:
                raise InterleavedDurableEpochInvariantViolation(
                    "facet genesis typed null changed"
                )
            break
        if type(previous) is not str:
            raise InterleavedDurableEpochInvariantViolation(
                "facet predecessor identity is not typed"
            )
        current = _cid(previous, "facet predecessor")
    for newer, older in zip(payload_chain, payload_chain[1:]):
        newer_by_id = {
            item["facet_entry_id"]: item for item in newer["entries"]
        }
        if (
            newer["generation"] != older["generation"] + 1
            or newer["model_id"] != older["model_id"]
            or newer["epoch_name"] != older["epoch_name"]
            or any(
                newer_by_id.get(item["facet_entry_id"]) != item
                for item in older["entries"]
            )
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "facet append-only predecessor chain changed"
            )
    expected_commit_files = {
        f"{identity}.json" for identity in visited_commits
    }
    expected_payload_files = {
        f"{identity}.json" for identity in visited_payloads
    }
    if (
        {item.name for item in (root / "commits").iterdir()}
        != expected_commit_files
        or {item.name for item in (root / "blobs").iterdir()}
        != expected_payload_files
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "facet store contains an unreachable object"
        )
    return payload_chain[0], commit_chain[0]


def _append_facet_store(
    root: Path,
    before_commit_id: str,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    before, _ = _load_facet_store(root, before_commit_id)
    if not entries:
        return _read_canonical(
            root / "commits" / f"{before_commit_id}.json"
        )[0]
    existing = {item["facet_key_id"] for item in before["entries"]}
    if any(item["facet_key_id"] in existing for item in entries):
        raise InterleavedDurableEpochInvariantViolation(
            "facet append overwrites an existing key"
        )
    payload = _facet_payload(
        before["model_id"],
        before["epoch_name"],
        [*before["entries"], *entries],
        before["generation"] + 1,
        before_commit_id,
    )
    commit = _facet_commit(payload)
    _write_exclusive(root / "blobs" / f"{payload['payload_id']}.json", payload)
    _write_exclusive(root / "commits" / f"{commit['commit_id']}.json", commit)
    return commit


def _facet_key(
    metric: Mapping[str, Any],
    query: Mapping[str, Any],
    eligibility: Mapping[str, Any],
    preregistration: Mapping[str, Any],
    gate_kind: str,
) -> dict[str, Any]:
    if query.get("query_code") != "Q_R":
        raise InterleavedDurableEpochInvariantViolation(
            "query-facet keys are reserved for the relaxed query"
        )
    if gate_kind == "REGRET":
        tolerance = query["normalized_regret_tolerance"]
        formula = "REGRET_THRESHOLD_VERDICT_V0057"
    elif gate_kind == "RISK":
        tolerance = query["risk_tolerance"]
        formula = "RISK_THRESHOLD_VERDICT_V0057"
    else:
        raise InterleavedDurableEpochInvariantViolation(
            "unknown interleaved gate"
        )
    body = {
        "schema": "acfqp.interleaved_query_facet_key.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "preregistration_id": preregistration["preregistration_id"],
        "eligibility_id": eligibility["eligibility_id"],
        "query_id": query["query_id"],
        "epoch_name": eligibility["epoch_name"],
        "model_id": metric["model_id"],
        "schedule_code": metric["schedule_code"],
        "metric_id": metric["metric_id"],
        "source_d_entry_id": metric["ordered_lower_entry_ids"][6],
        "gate_kind": gate_kind,
        "formula_id": formula,
        "tolerance": tolerance,
    }
    return {**body, "facet_key_id": _content_id("facet_key", body)}


def _facet_entry(
    key: Mapping[str, Any],
    metric: Mapping[str, Any],
) -> dict[str, Any]:
    if key["gate_kind"] == "REGRET":
        value = metric["normalized_regret"]
    else:
        value = metric["failure_upper"]
    passes = _parse_fraction(value, "gate value") <= _parse_fraction(
        key["tolerance"], "gate tolerance"
    )
    body = {
        "schema": "acfqp.interleaved_query_facet_entry.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "key": dict(key),
        "facet_key_id": key["facet_key_id"],
        "gate_kind": key["gate_kind"],
        "value": value,
        "passes": passes,
    }
    return {**body, "facet_entry_id": _content_id("facet_entry", body)}


def _validate_facet_entry(document: Mapping[str, Any]) -> None:
    if (
        type(document) is not dict
        or set(document)
        != {
            "schema",
            "schema_version",
            "profile_key",
            "key",
            "facet_key_id",
            "gate_kind",
            "value",
            "passes",
            "facet_entry_id",
        }
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "facet entry field set changed"
        )
    body = dict(document)
    identity = body.pop("facet_entry_id")
    key = _validate_facet_key(document["key"])
    expected_passes = _parse_fraction(
        document["value"], "facet entry value"
    ) <= _parse_fraction(key["tolerance"], "facet entry tolerance")
    if (
        identity != _content_id("facet_entry", body)
        or document["gate_kind"] not in {"REGRET", "RISK"}
        or type(document["passes"]) is not bool
        or document["passes"] is not expected_passes
        or document["facet_key_id"] != key["facet_key_id"]
        or document["gate_kind"] != key["gate_kind"]
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "facet entry identity changed"
        )
    _cid(document["facet_key_id"], "facet entry key")


def _validate_facet_key(document: Mapping[str, Any]) -> dict[str, Any]:
    key = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "preregistration_id",
            "eligibility_id",
            "query_id",
            "epoch_name",
            "model_id",
            "schedule_code",
            "metric_id",
            "source_d_entry_id",
            "gate_kind",
            "formula_id",
            "tolerance",
            "facet_key_id",
        },
        "query facet key",
    )
    body = dict(key)
    identity = body.pop("facet_key_id")
    relaxed = registered_interleaved_queries_v1()[0]
    expected_tolerance = (
        relaxed.normalized_regret_tolerance
        if key["gate_kind"] == "REGRET"
        else relaxed.risk_tolerance
    )
    if (
        key["schema"] != "acfqp.interleaved_query_facet_key.v1"
        or key["schema_version"] != SCHEMA_VERSION
        or key["profile_key"] != PROFILE_KEY
        or key["schedule_code"] not in SCHEDULE_ORDER
        or key["query_id"] != relaxed.query_id
        or key["epoch_name"] not in {"FIRST", "FINAL"}
        or key["gate_kind"] not in {"REGRET", "RISK"}
        or key["formula_id"]
        != (
            "REGRET_THRESHOLD_VERDICT_V0057"
            if key["gate_kind"] == "REGRET"
            else "RISK_THRESHOLD_VERDICT_V0057"
        )
        or _parse_fraction(
            key["tolerance"], "facet key tolerance"
        )
        != expected_tolerance
        or identity != _content_id("facet_key", body)
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "query facet key identity changed"
        )
    for field in (
        "preregistration_id",
        "eligibility_id",
        "query_id",
        "model_id",
        "metric_id",
        "source_d_entry_id",
    ):
        _cid(key[field], f"facet key {field}")
    return key


def _proof_request_document(
    *,
    occurrence: Mapping[str, Any],
    checkpoint: Mapping[str, Any],
    checkpoint_commit_id: str,
    metric: Mapping[str, Any],
    proof_role: str,
    proposal_id: str | None,
) -> dict[str, Any]:
    if proof_role == "CANDIDATE_RANKING_AUDIT":
        proposal: str | Mapping[str, str] = {
            "kind": "NOT_APPLICABLE",
            "reason": "CANDIDATE_PRECEDES_PROPOSAL",
        }
        if proposal_id is not None:
            raise InterleavedDurableEpochInvariantViolation(
                "candidate proof request acquired a proposal"
            )
    elif proof_role == "INDEPENDENT_SELECTED_PLAN_CERTIFICATE":
        if proposal_id is None:
            raise InterleavedDurableEpochInvariantViolation(
                "selected proof request lacks its proposal"
            )
        proposal = _cid(proposal_id, "proof-request proposal")
    else:
        raise InterleavedDurableEpochInvariantViolation(
            "proof request role changed"
        )
    body = {
        "schema": "acfqp.interleaved_proof_request.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "occurrence_id": occurrence["occurrence_id"],
        "query_id": occurrence["query_id"],
        "checkpoint_commit_id": checkpoint_commit_id,
        "model_id": checkpoint["model_id"],
        "epoch_name": checkpoint["epoch_name"],
        "evidence_request_id": checkpoint["model_document"][
            "evidence_request_id"
        ],
        "metric_id": metric["metric_id"],
        "schedule_code": metric["schedule_code"],
        "proof_role": proof_role,
        "proposal_id": proposal,
    }
    return {
        **body,
        "proof_request_id": _content_id("proof_request", body),
    }


def _root_document(
    role: str,
    occurrence: Mapping[str, Any],
    checkpoint: Mapping[str, Any],
    checkpoint_commit_id: str,
    metric: Mapping[str, Any],
    regret: Mapping[str, Any],
    risk: Mapping[str, Any],
    certified: bool,
    proposal_id: str | None = None,
    failed_frontier_id: str | None = None,
) -> dict[str, Any]:
    proof_role = (
        "CANDIDATE_RANKING_AUDIT"
        if role == "candidate_root"
        else "INDEPENDENT_SELECTED_PLAN_CERTIFICATE"
    )
    proof_request = _proof_request_document(
        occurrence=occurrence,
        checkpoint=checkpoint,
        checkpoint_commit_id=checkpoint_commit_id,
        metric=metric,
        proof_role=proof_role,
        proposal_id=proposal_id,
    )
    body = {
        "schema": (
            "acfqp.interleaved_candidate_root.v1"
            if role == "candidate_root"
            else "acfqp.interleaved_selected_root.v1"
        ),
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "occurrence_id": occurrence["occurrence_id"],
        "query_id": occurrence["query_id"],
        "checkpoint_commit_id": checkpoint_commit_id,
        "model_id": checkpoint["model_id"],
        "epoch_name": checkpoint["epoch_name"],
        "evidence_request_id": checkpoint["model_document"][
            "evidence_request_id"
        ],
        "proof_role": proof_role,
        "proof_request": proof_request,
        "proof_request_id": proof_request["proof_request_id"],
        "metric_id": metric["metric_id"],
        "schedule_code": metric["schedule_code"],
        "regret_facet_entry_id": regret["facet_entry_id"],
        "risk_facet_entry_id": risk["facet_entry_id"],
        "external_coverage_certified": (
            metric["external_coverage_certified"]
        ),
        "certified": certified,
        "proposal_id": (
            proposal_id
            if proposal_id is not None
            else {"kind": "NOT_APPLICABLE", "reason": "CANDIDATE"}
        ),
        "failed_proof_frontier_id": (
            failed_frontier_id
            if failed_frontier_id is not None
            else {"kind": "NOT_APPLICABLE", "reason": "NO_SELECTED_FAILURE"}
        ),
    }
    id_name = "candidate_root_id" if role == "candidate_root" else "selected_root_id"
    return {**body, id_name: _content_id(role, body)}


def _derive_selected_failed_frontier(
    checkpoint: Mapping[str, Any],
    occurrence: Mapping[str, Any],
    query: Mapping[str, Any],
    metric: Mapping[str, Any],
) -> dict[str, Any]:
    records = {
        item["entry"]["entry_id"]: item
        for item in checkpoint["union_lower_entries"]
    }
    by_slot = {
        slot: records[entry_id]["value_document"]
        for slot, entry_id in zip(
            LOWER_SLOTS, metric["ordered_lower_entry_ids"]
        )
    }
    c_rows = sorted(
        [*by_slot["C0"]["rows"], *by_slot["C1"]["rows"]],
        key=lambda row: (
            row["time_index"],
            row["cell_id"],
            row["state_id"],
            row["action_id"],
        ),
    )
    external = [
        row
        for row in c_rows
        if row["remaining_horizon"] > 1
        and (
            _parse_fraction(
                row["reachable_external_continuation_mass_upper"],
                "frontier external mass",
            )
            > 0
            or _parse_fraction(
                row["reachable_unknown_mass_upper"],
                "frontier unknown mass",
            )
            > 0
        )
    ]
    unresolved = [
        row
        for row in c_rows
        if _parse_fraction(
            row["reachable_unknown_mass_upper"],
            "frontier unresolved mass",
        )
        > 0
        or row["representative_disagreement"] is True
    ]
    if external:
        earliest = min(row["time_index"] for row in external)
        selected_rows = [
            row for row in external if row["time_index"] == earliest
        ]
        reason = "EXTERNAL_COVERAGE_ESCAPE"
    elif unresolved:
        earliest = min(row["time_index"] for row in unresolved)
        selected_rows = [
            row for row in unresolved if row["time_index"] == earliest
        ]
        reason = "UNRESOLVED_POLICY_PATH_DISTINCTION"
    else:
        earliest = min(row["time_index"] for row in c_rows)
        selected_rows = [
            row for row in c_rows if row["time_index"] == earliest
        ]
        reason = "KNOWN_FIXED_PLAN_THRESHOLD_FAILURE"
    obligations = [
        {
            "time_index": row["time_index"],
            "remaining_horizon": row["remaining_horizon"],
            "state_id": row["state_id"],
            "cell_id": row["cell_id"],
            "semantic_action_id": row["action_id"],
            "support_ground_row_ids": row["support_ground_row_ids"],
            "observed_ground_row_ids": row["observed_ground_row_ids"],
            "missing_ground_row_ids": row["missing_ground_row_ids"],
            "reachable_cell_mass_upper": row[
                "reachable_cell_mass_upper"
            ],
            "reachable_unknown_mass_upper": row[
                "reachable_unknown_mass_upper"
            ],
            "reachable_external_continuation_mass_upper": row[
                "reachable_external_continuation_mass_upper"
            ],
            "representative_disagreement": row[
                "representative_disagreement"
            ],
        }
        for row in selected_rows
    ]
    unresolved_exposure = sum(
        (
            _parse_fraction(
                row["reachable_unknown_mass_upper"],
                "frontier exposure unknown",
            )
            + _parse_fraction(
                row["reachable_external_continuation_mass_upper"],
                "frontier exposure external",
            )
            for row in selected_rows
        ),
        Fraction(0),
    )
    body = {
        "schema": "acfqp.interleaved_failed_proof_frontier.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "occurrence_id": occurrence["occurrence_id"],
        "query_id": query["query_id"],
        "model_id": checkpoint["model_id"],
        "metric_id": metric["metric_id"],
        "plan_id": metric["plan_id"],
        "earliest_time_index": earliest,
        "remaining_horizon": 2 - earliest,
        "obligations": obligations,
        "unresolved_exposure_sum": _fraction_document(
            unresolved_exposure
        ),
        "value_obligation_failed": (
            _parse_fraction(
                metric["normalized_regret"], "frontier regret"
            )
            > _parse_fraction(
                query["normalized_regret_tolerance"],
                "frontier regret tolerance",
            )
        ),
        "risk_obligation_failed": (
            _parse_fraction(
                metric["failure_upper"], "frontier failure"
            )
            > _parse_fraction(
                query["risk_tolerance"], "frontier risk tolerance"
            )
        ),
        "external_coverage_failed": (
            by_slot["G"]["coverage_certified"] is not True
        ),
        "reason": reason,
        "source_entry_ids": {
            slot: entry_id
            for slot, entry_id in zip(
                LOWER_SLOTS, metric["ordered_lower_entry_ids"]
            )
            if slot in {"C0", "C1", "D", "E", "F", "G"}
        },
        "hint_kind": "NONAUTHORIZING_PROOF_OBLIGATION_HINT_V0057",
        "local_recovery_authorized": False,
        "causal_necessity_claimed": False,
        "causal_sufficiency_claimed": False,
        "infeasibility_claimed": False,
    }
    return {
        **body,
        "frontier_id": _content_id("failed_frontier", body),
    }


def _compute_occurrence_document(
    checkpoint: Mapping[str, Any],
    checkpoint_commit: Mapping[str, Any],
    facet_payload: Mapping[str, Any],
    facet_commit: Mapping[str, Any],
    query: Mapping[str, Any],
    occurrence: Mapping[str, Any],
    *,
    host_model_only_reconstruction: bool = False,
) -> dict[str, Any]:
    _validate_checkpoint_payload(checkpoint)
    _validate_query_document(query)
    _validate_occurrence_document(occurrence, query)
    preregistration = checkpoint["preregistration_document"]
    eligibility = checkpoint["eligibility"]
    registered_occurrence = preregistration["occurrences"][
        occurrence["occurrence_index"] - 1
    ]
    if (
        checkpoint["model_id"] != facet_payload["model_id"]
        or checkpoint["epoch_name"] != facet_payload["epoch_name"]
        or query["query_id"] not in eligibility["query_ids"]
        or eligibility["preregistration_id"]
        != preregistration["preregistration_id"]
        or eligibility["model_id"] != checkpoint["model_id"]
        or eligibility["epoch_name"] != checkpoint["epoch_name"]
        or occurrence != registered_occurrence
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "worker input identity chain changed"
        )
    entries_by_key = {
        item["facet_key_id"]: item for item in facet_payload["entries"]
    }
    appended: list[dict[str, Any]] = []
    gate_by_metric: dict[tuple[str, str], dict[str, Any]] = {}
    query_is_strict = query["query_code"] == "Q_S"
    for metric in checkpoint["candidate_metrics"]:
        for gate_kind in ("REGRET", "RISK"):
            if query_is_strict:
                if gate_kind == "REGRET":
                    value = metric["normalized_regret"]
                    entry_id = metric["strict_regret_entry_id"]
                else:
                    value = metric["failure_upper"]
                    entry_id = metric["strict_risk_entry_id"]
                entry = {
                    "facet_entry_id": entry_id,
                    "passes": _parse_fraction(value, "strict gate value")
                    <= Fraction(0),
                }
                outcome = "CORE_STRICT_HIT"
            else:
                key = _facet_key(
                    metric,
                    query,
                    eligibility,
                    preregistration,
                    gate_kind,
                )
                existing = entries_by_key.get(key["facet_key_id"])
                if existing is None:
                    entry = _facet_entry(key, metric)
                    entries_by_key[key["facet_key_id"]] = entry
                    appended.append(entry)
                    outcome = "BUILT_AFTER_MISS"
                else:
                    expected = _facet_entry(key, metric)
                    if existing != expected:
                        raise InterleavedDurableEpochInvariantViolation(
                            "facet hit value differs from formula replay"
                        )
                    entry = existing
                    outcome = "FACET_HIT"
            gate_by_metric[(metric["metric_id"], gate_kind)] = {
                **entry,
                "lookup_outcome": outcome,
            }
    candidate_rows = []
    for metric in checkpoint["candidate_metrics"]:
        regret = gate_by_metric[(metric["metric_id"], "REGRET")]
        risk = gate_by_metric[(metric["metric_id"], "RISK")]
        certified = (
            regret["passes"]
            and risk["passes"]
            and metric["external_coverage_certified"]
        )
        candidate_rows.append((metric, regret, risk, certified))
    certified_rows = [item for item in candidate_rows if item[3]]
    pool = certified_rows if certified_rows else candidate_rows
    selected = min(
        pool,
        key=lambda item: (
            -_parse_fraction(item[0]["reward_lower"], "selection reward"),
            _parse_fraction(item[0]["failure_upper"], "selection failure"),
            tuple(item[0]["semantic_key"]),
            item[0]["plan_id"],
        ),
    )
    candidate_roots = [
        _root_document(
            "candidate_root",
            occurrence,
            checkpoint,
            checkpoint_commit["commit_id"],
            metric,
            regret,
            risk,
            certified,
        )
        for metric, regret, risk, certified in candidate_rows
    ]
    proposal_body = {
        "schema": "acfqp.interleaved_plan_proposal.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "occurrence_id": occurrence["occurrence_id"],
        "query_id": query["query_id"],
        "checkpoint_commit_id": checkpoint_commit["commit_id"],
        "candidate_root_ids": [
            item["candidate_root_id"] for item in candidate_roots
        ],
        "selected_metric_id": selected[0]["metric_id"],
        "selected_schedule_code": selected[0]["schedule_code"],
        "selection_mode": (
            "CERTIFIED_REWARD_MAX"
            if certified_rows
            else "MIN_FAILURE_RISK_FALLBACK"
        ),
    }
    proposal_id = _content_id("proposal", proposal_body)
    proposal = {**proposal_body, "proposal_id": proposal_id}
    failed_frontier = (
        {
            "kind": "NOT_APPLICABLE",
            "reason": "SELECTED_PLAN_CERTIFIED",
        }
        if selected[3]
        else _derive_selected_failed_frontier(
            checkpoint,
            occurrence,
            query,
            selected[0],
        )
    )
    selected_root = _root_document(
        "selected_root",
        occurrence,
        checkpoint,
        checkpoint_commit["commit_id"],
        selected[0],
        selected[1],
        selected[2],
        selected[3],
        proposal_id,
        (
            None
            if selected[3]
            else failed_frontier["frontier_id"]
        ),
    )
    certificate_body = {
        "schema": "acfqp.interleaved_plan_certificate.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "occurrence_id": occurrence["occurrence_id"],
        "query_id": query["query_id"],
        "checkpoint_commit_id": checkpoint_commit["commit_id"],
        "proposal_id": proposal_id,
        "selected_root_id": selected_root["selected_root_id"],
        "selected_schedule_code": selected[0]["schedule_code"],
        "reward_lower": selected[0]["reward_lower"],
        "reward_upper": selected[0]["reward_upper"],
        "failure_lower": selected[0]["failure_lower"],
        "failure_upper": selected[0]["failure_upper"],
        "normalized_regret": selected[0]["normalized_regret"],
        "external_coverage_certified": selected[0][
            "external_coverage_certified"
        ],
        "certified": selected[3],
        "failed_proof_frontier": failed_frontier,
    }
    certificate = {
        **certificate_body,
        "certificate_id": _content_id("certificate", certificate_body),
    }
    builder_calls = len(appended)
    lower_hits = 50 - builder_calls
    result_body = {
        "schema": "acfqp.interleaved_occurrence_result.v1",
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "occurrence": occurrence,
        "query": query,
        "preregistration_id": preregistration["preregistration_id"],
        "eligibility_id": eligibility["eligibility_id"],
        "epoch_name": checkpoint["epoch_name"],
        "model_id": checkpoint["model_id"],
        "evidence_request_id": checkpoint["model_document"][
            "evidence_request_id"
        ],
        "checkpoint_commit_id": checkpoint_commit["commit_id"],
        "before_facet_commit_id": facet_commit["commit_id"],
        "appended_facet_entries": sorted(
            appended, key=lambda item: item["facet_entry_id"]
        ),
        "query_facet_builder_calls": builder_calls,
        "lower_identity_hits": lower_hits,
        "fresh_root_builder_calls": 5,
        "ground_transition_calls": 0,
        "candidate_roots": candidate_roots,
        "proposal": proposal,
        "selected_root": selected_root,
        "certificate": certificate,
        "matching_buffer_imported": (
            False
            if host_model_only_reconstruction
            else "acfqp.domains.matching_buffer" in sys.modules
        ),
        "live_epoch_module_imported": (
            False
            if host_model_only_reconstruction
            else "acfqp.live_query_local_epoch_invalidation_v1" in sys.modules
        ),
    }
    return {
        **result_body,
        "result_id": _content_id("occurrence_result", result_body),
    }


def _worker_main(arguments: list[str]) -> int:
    if len(arguments) != 10:
        return 2
    (
        checkpoint_root_text,
        checkpoint_commit_id,
        checkpoint_previous_commit_id_text,
        checkpoint_predecessor_store_root_text,
        facet_root_text,
        facet_commit_id,
        query_path_text,
        occurrence_path_text,
        output_path_text,
        expected_parent_pid_text,
    ) = arguments
    try:
        _invoke_canonical_source_pin_assert(
            allow_runtime_imports=False
        )
        expected_parent_pid = int(expected_parent_pid_text)
        if os.getppid() != expected_parent_pid:
            raise InterleavedDurableEpochInvariantViolation(
                "worker parent process changed"
            )
        checkpoint, checkpoint_commit = _load_checkpoint(
            Path(checkpoint_root_text),
            checkpoint_commit_id,
            expected_previous_commit_id=(
                None
                if checkpoint_previous_commit_id_text == "NONE"
                else checkpoint_previous_commit_id_text
            ),
            predecessor_store_root=(
                None
                if checkpoint_predecessor_store_root_text == "NONE"
                else Path(checkpoint_predecessor_store_root_text)
            ),
        )
        facet_payload, facet_commit = _load_facet_store(
            Path(facet_root_text), facet_commit_id
        )
        query, _ = _read_canonical(Path(query_path_text))
        occurrence, _ = _read_canonical(Path(occurrence_path_text))
        result = _compute_occurrence_document(
            checkpoint,
            checkpoint_commit,
            facet_payload,
            facet_commit,
            query,
            occurrence,
        )
        _write_exclusive(Path(output_path_text), result)
    except Exception:
        return 1
    return 0


def _worker_environment() -> dict[str, str]:
    environment = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONHASHSEED": "0",
    }
    for name in ("LANG", "LC_ALL", "TZ"):
        value = os.environ.get(name)
        if value is not None:
            environment[name] = value
    return environment


def _directory_snapshot_id(root: Path, role: str) -> str:
    if (
        not isinstance(root, Path)
        or not root.is_dir()
        or root.is_symlink()
        or type(role) is not str
        or not role
    ):
        raise InterleavedDurableEpochInvariantViolation(
            f"{role} snapshot root is invalid"
        )
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise InterleavedDurableEpochInvariantViolation(
                f"{role} snapshot contains a symlink"
            )
        if path.is_dir():
            continue
        payload = _stable_regular_bytes(path)
        rows.append(
            {
                "path": relative,
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    if not rows:
        raise InterleavedDurableEpochInvariantViolation(
            f"{role} snapshot is empty"
        )
    return _content_id(
        "snapshot",
        {
            "schema": "acfqp.interleaved_campaign_snapshot.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "role": role,
            "files": rows,
        },
    )


def _directory_regular_bytes(root: Path) -> int:
    if not root.is_dir() or root.is_symlink():
        raise InterleavedDurableEpochInvariantViolation(
            "byte-accounting root is invalid"
        )
    return sum(
        len(_stable_regular_bytes(path))
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    )


def _campaign_owner_id(preregistration_id: str) -> str:
    _cid(preregistration_id, "event owner preregistration")
    return _content_id(
        "campaign_owner",
        {
            "schema": "acfqp.interleaved_campaign_owner.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": preregistration_id,
        },
    )


def _query_eligibility_freeze_id(
    preregistration: InterleavedWorkloadPreregistrationV1,
) -> str:
    preregistration.__post_init__()
    return _content_id(
        "query_eligibility_freeze",
        {
            "schema": "acfqp.interleaved_query_eligibility_freeze.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": preregistration.preregistration_id,
            "source_strict_thresholds_id": (
                preregistration.source_strict_thresholds_id
            ),
            "query_ids": [
                item.query_id for item in preregistration.queries
            ],
            "query_order": list(QUERY_ORDER),
            "threshold_only": True,
            "frozen_before_source_ground": True,
        },
    )


_EVENT_ISSUER = object()
_EVENT_LOG_ISSUER = object()
_EVENT_REGISTRY: dict[int, "InterleavedEventV1"] = {}
_EVENT_LOG_REGISTRY: dict[int, "InterleavedEventLogV1"] = {}


@dataclass(frozen=True, slots=True)
class InterleavedEventV1:
    sequence_number: int
    event_kind: str
    artifact_id: str
    owner_id: str
    preregistration_id: str
    previous_event_id: str | Mapping[str, str]
    occurrence_index: int | Mapping[str, str]
    epoch_name: str | Mapping[str, str]
    cumulative_ground_transition_calls: int
    cumulative_round_one_ground_transition_calls: int
    cumulative_round_two_ground_transition_calls: int
    cumulative_boundary_catalogue_calls: int
    cumulative_main_worker_process_count: int
    cumulative_reset_worker_process_count: int
    _instance_mint: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        _integer(self.sequence_number, "event sequence", 1)
        if (
            self.sequence_number > len(EXPECTED_EVENT_ORDER)
            or self.event_kind
            != EXPECTED_EVENT_ORDER[self.sequence_number - 1]
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "interleaved event sequence/kind changed"
            )
        for value in (
            self.artifact_id,
            self.owner_id,
            self.preregistration_id,
        ):
            _cid(value, "interleaved event identity")
        if self.owner_id != _campaign_owner_id(self.preregistration_id):
            raise InterleavedDurableEpochInvariantViolation(
                "interleaved event owner changed"
            )
        if self.sequence_number == 1:
            if self.previous_event_id != {
                "kind": "NOT_APPLICABLE",
                "reason": "EVENT_LOG_GENESIS",
            }:
                raise InterleavedDurableEpochInvariantViolation(
                    "interleaved event genesis changed"
                )
        else:
            _cid(self.previous_event_id, "interleaved previous event")
        expected = _expected_event_context(self.sequence_number)
        for value in (
            self.cumulative_ground_transition_calls,
            self.cumulative_round_one_ground_transition_calls,
            self.cumulative_round_two_ground_transition_calls,
            self.cumulative_boundary_catalogue_calls,
            self.cumulative_main_worker_process_count,
            self.cumulative_reset_worker_process_count,
        ):
            _integer(value, "interleaved cumulative counter")
        if (
            self.occurrence_index != expected[0]
            or self.epoch_name != expected[1]
            or self.cumulative_round_one_ground_transition_calls
            != expected[2]
            or self.cumulative_round_two_ground_transition_calls
            != expected[3]
            or self.cumulative_boundary_catalogue_calls != expected[4]
            or self.cumulative_main_worker_process_count != expected[5]
            or self.cumulative_reset_worker_process_count != expected[6]
            or self.cumulative_ground_transition_calls
            != expected[2] + expected[3]
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "interleaved event registered context/counter changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.interleaved_event.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "sequence_number": self.sequence_number,
            "event_kind": self.event_kind,
            "artifact_id": self.artifact_id,
            "owner_id": self.owner_id,
            "preregistration_id": self.preregistration_id,
            "previous_event_id": self.previous_event_id,
            "occurrence_index": self.occurrence_index,
            "epoch_name": self.epoch_name,
            "cumulative_ground_transition_calls": (
                self.cumulative_ground_transition_calls
            ),
            "cumulative_round_one_ground_transition_calls": (
                self.cumulative_round_one_ground_transition_calls
            ),
            "cumulative_round_two_ground_transition_calls": (
                self.cumulative_round_two_ground_transition_calls
            ),
            "cumulative_boundary_catalogue_calls": (
                self.cumulative_boundary_catalogue_calls
            ),
            "cumulative_main_worker_process_count": (
                self.cumulative_main_worker_process_count
            ),
            "cumulative_reset_worker_process_count": (
                self.cumulative_reset_worker_process_count
            ),
        }

    @property
    def event_id(self) -> str:
        return _content_id("event", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "event_id": self.event_id}


def _mint_interleaved_event(
    *args: Any,
) -> InterleavedEventV1:
    from acfqp._runtime_authority_v1 import bind_runtime_authority_v1

    event = InterleavedEventV1(*args)
    event = bind_runtime_authority_v1(event, issuer=_EVENT_ISSUER)
    _EVENT_REGISTRY[id(event)] = event
    return event


def _require_interleaved_event(
    event: InterleavedEventV1,
) -> InterleavedEventV1:
    if (
        type(event) is not InterleavedEventV1
        or _EVENT_REGISTRY.get(id(event)) is not event
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "interleaved event lacks exact producer ownership"
        )
    try:
        from acfqp._runtime_authority_v1 import require_runtime_authority_v1

        require_runtime_authority_v1(event, issuer=_EVENT_ISSUER)
    except Exception as error:
        raise InterleavedDurableEpochInvariantViolation(
            "interleaved event runtime owner changed"
        ) from error
    event.__post_init__()
    return event


@dataclass(frozen=True, slots=True)
class InterleavedEventLogV1:
    preregistration_id: str
    events: tuple[InterleavedEventV1, ...]
    final_event_count: int = 23
    owner_id: str | None = None
    _instance_mint: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        owner_id = _campaign_owner_id(self.preregistration_id)
        if self.owner_id is None:
            object.__setattr__(self, "owner_id", owner_id)
        if (
            self.owner_id != owner_id
            or type(self.events) is not tuple
            or len(self.events) != 23
            or self.final_event_count != 23
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "interleaved event-log cardinality/owner changed"
            )
        prior_ground = 0
        prior_main = 0
        prior_reset = 0
        for index, event in enumerate(self.events, 1):
            _require_interleaved_event(event)
            expected_previous: str | Mapping[str, str] = (
                {
                    "kind": "NOT_APPLICABLE",
                    "reason": "EVENT_LOG_GENESIS",
                }
                if index == 1
                else self.events[index - 2].event_id
            )
            if (
                event.sequence_number != index
                or event.event_kind != EXPECTED_EVENT_ORDER[index - 1]
                or event.preregistration_id != self.preregistration_id
                or event.owner_id != self.owner_id
                or event.previous_event_id != expected_previous
                or event.cumulative_ground_transition_calls < prior_ground
                or event.cumulative_main_worker_process_count < prior_main
                or event.cumulative_reset_worker_process_count < prior_reset
            ):
                raise InterleavedDurableEpochInvariantViolation(
                    "interleaved event-log context/order changed"
                )
            prior_ground = event.cumulative_ground_transition_calls
            prior_main = event.cumulative_main_worker_process_count
            prior_reset = event.cumulative_reset_worker_process_count

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.interleaved_event_log.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "owner_id": self.owner_id,
            "preregistration_id": self.preregistration_id,
            "events": [item.to_document() for item in self.events],
            "final_event_count": self.final_event_count,
        }

    @property
    def log_id(self) -> str:
        return _content_id("event_log", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "log_id": self.log_id}


def _mint_interleaved_event_log(
    preregistration_id: str,
    events: tuple[InterleavedEventV1, ...],
) -> InterleavedEventLogV1:
    from acfqp._runtime_authority_v1 import bind_runtime_authority_v1

    event_log = InterleavedEventLogV1(
        preregistration_id,
        events,
        23,
        _campaign_owner_id(preregistration_id),
    )
    event_log = bind_runtime_authority_v1(
        event_log, issuer=_EVENT_LOG_ISSUER
    )
    _EVENT_LOG_REGISTRY[id(event_log)] = event_log
    return event_log


def _require_interleaved_event_log(
    event_log: InterleavedEventLogV1,
) -> InterleavedEventLogV1:
    if (
        type(event_log) is not InterleavedEventLogV1
        or _EVENT_LOG_REGISTRY.get(id(event_log)) is not event_log
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "interleaved event log lacks exact producer ownership"
        )
    try:
        from acfqp._runtime_authority_v1 import require_runtime_authority_v1

        require_runtime_authority_v1(
            event_log, issuer=_EVENT_LOG_ISSUER
        )
    except Exception as error:
        raise InterleavedDurableEpochInvariantViolation(
            "interleaved event-log runtime owner changed"
        ) from error
    event_log.__post_init__()
    return event_log


class _InterleavedEventRecorder:
    __slots__ = (
        "_root",
        "_preregistration_id",
        "_owner_id",
        "_events",
    )

    def __init__(
        self,
        root: Path,
        preregistration_id: str,
    ) -> None:
        if root.exists():
            raise InterleavedDurableEpochInvariantViolation(
                "event-ledger root already exists"
            )
        root.mkdir()
        self._root = root
        self._preregistration_id = _cid(
            preregistration_id, "event recorder preregistration"
        )
        self._owner_id = _campaign_owner_id(preregistration_id)
        self._events: list[InterleavedEventV1] = []

    def append(
        self,
        event_kind: str,
        artifact_id: str,
        *,
        ground: int,
        main_workers: int,
        reset_workers: int,
    ) -> InterleavedEventV1:
        sequence = len(self._events) + 1
        if (
            sequence > len(EXPECTED_EVENT_ORDER)
            or event_kind != EXPECTED_EVENT_ORDER[sequence - 1]
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "event recorder live order changed"
            )
        previous: str | Mapping[str, str] = (
            {
                "kind": "NOT_APPLICABLE",
                "reason": "EVENT_LOG_GENESIS",
            }
            if not self._events
            else self._events[-1].event_id
        )
        expected = _expected_event_context(sequence)
        if (
            ground != expected[2] + expected[3]
            or main_workers != expected[5]
            or reset_workers != expected[6]
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "event recorder observed counters differ from profile"
            )
        event = _mint_interleaved_event(
            sequence,
            event_kind,
            artifact_id,
            self._owner_id,
            self._preregistration_id,
            previous,
            expected[0],
            expected[1],
            ground,
            expected[2],
            expected[3],
            expected[4],
            main_workers,
            reset_workers,
        )
        if self._events:
            prior = self._events[-1]
            if (
                ground < prior.cumulative_ground_transition_calls
                or main_workers
                < prior.cumulative_main_worker_process_count
                or reset_workers
                < prior.cumulative_reset_worker_process_count
            ):
                raise InterleavedDurableEpochInvariantViolation(
                    "event recorder cumulative counter regressed"
                )
        _write_exclusive(
            self._root / f"{sequence:02d}-{event_kind}.json",
            event.to_document(),
        )
        self._events.append(event)
        return event

    def freeze(self) -> InterleavedEventLogV1:
        event_log = _mint_interleaved_event_log(
            self._preregistration_id, tuple(self._events)
        )
        _write_exclusive(
            self._root / "event-log.json",
            event_log.to_document(),
        )
        return event_log


@dataclass(frozen=True, slots=True)
class GroundRepairAuthorizationV1:
    preregistration_id: str
    occurrence_id: str
    first_checkpoint_commit_id: str
    failed_occurrence_result_id: str
    failed_certificate_id: str
    failed_frontier_id: str
    failed_certificate_digest: str
    source_strict_selected_audit_id: str
    source_strict_selected_audit_digest: str
    source_typed_frontier_id: str
    evidence_request_id: str
    authorized_ground_row_ids: tuple[str, ...]
    selected_plan_risk_row_count: int = 3
    unrestricted_value_challenger_row_count: int = 9
    requested_distinct_ground_row_count: int = 9
    authorized_exact_kernel_query_count: int = 9
    frozen_before_ground_acquisition: bool = True
    _instance_mint: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        for value in (
            self.preregistration_id,
            self.occurrence_id,
            self.first_checkpoint_commit_id,
            self.failed_occurrence_result_id,
            self.failed_certificate_id,
            self.failed_frontier_id,
            self.failed_certificate_digest,
            self.source_strict_selected_audit_id,
            self.source_strict_selected_audit_digest,
            self.source_typed_frontier_id,
            self.evidence_request_id,
            *self.authorized_ground_row_ids,
        ):
            _cid(value, "ground-repair authorization identity")
        if (
            type(self.authorized_ground_row_ids) is not tuple
            or self.authorized_ground_row_ids
            != tuple(sorted(set(self.authorized_ground_row_ids)))
            or len(self.authorized_ground_row_ids) != 9
            or self.selected_plan_risk_row_count != 3
            or self.unrestricted_value_challenger_row_count != 9
            or self.requested_distinct_ground_row_count != 9
            or self.authorized_exact_kernel_query_count != 9
            or self.frozen_before_ground_acquisition is not True
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "ground-repair authorization scope changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.interleaved_ground_repair_authorization.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": self.preregistration_id,
            "occurrence_id": self.occurrence_id,
            "first_checkpoint_commit_id": self.first_checkpoint_commit_id,
            "failed_occurrence_result_id": self.failed_occurrence_result_id,
            "failed_certificate_id": self.failed_certificate_id,
            "failed_frontier_id": self.failed_frontier_id,
            "failed_certificate_digest": self.failed_certificate_digest,
            "source_strict_selected_audit_id": (
                self.source_strict_selected_audit_id
            ),
            "source_strict_selected_audit_digest": (
                self.source_strict_selected_audit_digest
            ),
            "source_typed_frontier_id": self.source_typed_frontier_id,
            "evidence_request_id": self.evidence_request_id,
            "authorized_ground_row_ids": list(
                self.authorized_ground_row_ids
            ),
            "selected_plan_risk_row_count": (
                self.selected_plan_risk_row_count
            ),
            "unrestricted_value_challenger_row_count": (
                self.unrestricted_value_challenger_row_count
            ),
            "requested_distinct_ground_row_count": (
                self.requested_distinct_ground_row_count
            ),
            "authorized_exact_kernel_query_count": (
                self.authorized_exact_kernel_query_count
            ),
            "frozen_before_ground_acquisition": (
                self.frozen_before_ground_acquisition
            ),
        }

    @property
    def authorization_id(self) -> str:
        return _content_id("authorization", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "authorization_id": self.authorization_id,
        }


_GROUND_AUTH_ISSUER = object()
_GROUND_SEMANTIC_MINT_NONCE = object()
_GROUND_AUTH_REGISTRY: dict[
    int, tuple["GroundRepairAuthorizationV1", "_GroundRepairSemanticAuthority"]
] = {}
_GROUND_AUTH_CONSUMED: set[int] = set()
_GROUND_AUTH_LOCK = threading.Lock()


def _require_ground_repair_authorization(
    authorization: GroundRepairAuthorizationV1,
) -> GroundRepairAuthorizationV1:
    if type(authorization) is not GroundRepairAuthorizationV1:
        raise InterleavedDurableEpochInvariantViolation(
            "ground authorization rejects substitutions"
        )
    try:
        from acfqp._runtime_authority_v1 import require_runtime_authority_v1

        require_runtime_authority_v1(
            authorization, issuer=_GROUND_AUTH_ISSUER
        )
    except Exception as error:
        raise InterleavedDurableEpochInvariantViolation(
            "ground authorization lacks process-local mint"
        ) from error
    registered = _GROUND_AUTH_REGISTRY.get(id(authorization))
    if registered is None or registered[0] is not authorization:
        raise InterleavedDurableEpochInvariantViolation(
            "ground authorization was not minted by the semantic producer"
        )
    authorization.__post_init__()
    return authorization


def _registered_ground_semantic_authority(
    authorization: GroundRepairAuthorizationV1,
) -> "_GroundRepairSemanticAuthority":
    authorization = _require_ground_repair_authorization(authorization)
    registered = _GROUND_AUTH_REGISTRY[id(authorization)]
    semantic_authority = registered[1]
    if (
        type(semantic_authority) is not _GroundRepairSemanticAuthority
        or semantic_authority.authorization_id
        != authorization.authorization_id
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "ground authorization semantic registry changed"
        )
    semantic_authority.validate(authorization)
    return semantic_authority


class _SingleUseGroundRepairGate:
    __slots__ = (
        "_authorization",
        "_semantic_authority",
        "_used",
        "_nonce",
    )

    def __init__(
        self,
        authorization: GroundRepairAuthorizationV1,
        nonce: object,
    ) -> None:
        self._authorization = _require_ground_repair_authorization(
            authorization
        )
        semantic_authority = _registered_ground_semantic_authority(
            self._authorization
        )
        if (
            type(semantic_authority) is not _GroundRepairSemanticAuthority
            or semantic_authority._mint_nonce
            is not _GROUND_SEMANTIC_MINT_NONCE
            or semantic_authority.authorization_id
            != authorization.authorization_id
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "ground gate lacks failed-proof semantic authority"
            )
        semantic_authority.validate(authorization)
        self._semantic_authority = semantic_authority
        self._used = False
        self._nonce = nonce

    def __copy__(self) -> Any:
        raise TypeError("ground-repair gate is noncopyable")

    def __deepcopy__(self, memo: Any) -> Any:
        raise TypeError("ground-repair gate is noncopyable")

    def __reduce__(self) -> Any:
        raise TypeError("ground-repair gate is not serializable")

    def acquire(
        self,
        *,
        multistep: Any,
        request: Any,
        observation_log: Any,
        boundary: Any,
        kernel: Any,
        nonce: object,
    ) -> Any:
        if (
            self._used
            or nonce is not self._nonce
            or request.request_id
            != self._authorization.evidence_request_id
            or tuple(request.requested_ground_row_ids)
            != self._authorization.authorized_ground_row_ids
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "ground-repair gate replay/context mismatch"
            )
        with _GROUND_AUTH_LOCK:
            if id(self._authorization) in _GROUND_AUTH_CONSUMED:
                raise InterleavedDurableEpochInvariantViolation(
                    "ground-repair authorization was already consumed"
                )
            self._used = True
            _GROUND_AUTH_CONSUMED.add(id(self._authorization))
        self._semantic_authority.validate(self._authorization)
        return multistep._acquire(
            2, request, observation_log, boundary, kernel
        )


def _validate_round_two_bundle_semantics(
    request: Any,
    bundle: Any,
    authorization: GroundRepairAuthorizationV1,
) -> None:
    request_rows = tuple(request.requested_ground_row_ids)
    evidence = tuple(bundle.evidence)
    safe = 0
    failure = 0
    if (
        bundle.round_index != 2
        or bundle.request_id != request.request_id
        or bundle.request_id != authorization.evidence_request_id
        or bundle.exact_kernel_query_count != 9
        or bundle.positive_outcome_row_count != 9
        or tuple(bundle.requested_ground_row_ids) != request_rows
        or request_rows != authorization.authorized_ground_row_ids
        or len(evidence) != 9
        or tuple(item.sequence_number for item in evidence)
        != tuple(range(1, 10))
        or tuple(item.ground_row_id for item in evidence) != request_rows
        or any(
            item.request_id != request.request_id
            or item.round_index != 2
            for item in evidence
        )
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "round-two bundle escaped its exact request/sequence"
        )
    for item in evidence:
        item.__post_init__()
        if (
            item.terminal is False
            and item.failure is False
            and item.reward_features == (("match", Fraction(1)),)
        ):
            safe += 1
        elif (
            item.terminal is True
            and item.failure is True
            and item.reward_features == ()
        ):
            failure += 1
        else:
            raise InterleavedDurableEpochInvariantViolation(
                "round-two evidence is neither registered safe nor failure"
            )
    if safe != 3 or failure != 6:
        raise InterleavedDurableEpochInvariantViolation(
            "round-two evidence no longer has the exact 3/6 outcome split"
        )


class _GroundRepairSemanticAuthority:
    __slots__ = (
        "authorization_id",
        "_preregistration",
        "_occurrence",
        "_first_checkpoint_commit",
        "_failed_result",
        "_typed_audit",
        "_request",
        "_mint_nonce",
    )

    def __init__(
        self,
        authorization: GroundRepairAuthorizationV1,
        preregistration: InterleavedWorkloadPreregistrationV1,
        occurrence: InterleavedOccurrenceV1,
        first_checkpoint_commit: Mapping[str, Any],
        failed_result: Mapping[str, Any],
        typed_audit: Any,
        request: Any,
        mint_nonce: object,
    ) -> None:
        if mint_nonce is not _GROUND_SEMANTIC_MINT_NONCE:
            raise InterleavedDurableEpochInvariantViolation(
                "ground semantic authority mint changed"
            )
        self.authorization_id = authorization.authorization_id
        self._preregistration = preregistration
        self._occurrence = occurrence
        self._first_checkpoint_commit = dict(first_checkpoint_commit)
        self._failed_result = dict(failed_result)
        self._typed_audit = typed_audit
        self._request = request
        self._mint_nonce = mint_nonce
        self.validate(authorization)

    def __copy__(self) -> Any:
        raise TypeError("ground semantic authority is noncopyable")

    def __deepcopy__(self, memo: Any) -> Any:
        raise TypeError("ground semantic authority is noncopyable")

    def __reduce__(self) -> Any:
        raise TypeError("ground semantic authority is not serializable")

    def validate(
        self, authorization: GroundRepairAuthorizationV1
    ) -> None:
        if (
            type(self._preregistration)
            is not InterleavedWorkloadPreregistrationV1
            or type(self._occurrence) is not InterleavedOccurrenceV1
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "ground semantic authority context type changed"
            )
        self._preregistration.__post_init__()
        self._occurrence.__post_init__()
        first_commit = _exact_mapping(
            self._first_checkpoint_commit,
            {
                "schema",
                "schema_version",
                "profile_key",
                "generation",
                "payload_id",
                "payload_sha256",
                "payload_size_bytes",
                "previous_commit_id",
                "commit_complete",
                "commit_id",
            },
            "ground semantic first checkpoint commit",
        )
        first_commit_body = dict(first_commit)
        first_commit_identity = first_commit_body.pop("commit_id")
        request_document = self._request.to_document()
        request_rows = tuple(self._request.requested_ground_row_ids)
        request_proof_rows = tuple(
            item.ground_row_id for item in self._request.row_proofs
        )
        if (
            authorization.preregistration_id
            != self._preregistration.preregistration_id
            or self._preregistration.occurrences[1] != self._occurrence
            or self._occurrence.occurrence_index != 2
            or self._occurrence.query.query_code != "Q_S"
            or authorization.occurrence_id
            != self._occurrence.occurrence_id
            or first_commit["schema"]
            != "acfqp.interleaved_epoch_checkpoint_commit.v1"
            or first_commit["schema_version"] != SCHEMA_VERSION
            or first_commit["profile_key"] != PROFILE_KEY
            or first_commit["generation"] != 1
            or first_commit["previous_commit_id"]
            != {"kind": "NOT_APPLICABLE", "reason": "FIRST_EPOCH"}
            or first_commit["commit_complete"] is not True
            or first_commit_identity
            != _content_id("checkpoint_commit", first_commit_body)
            or authorization.first_checkpoint_commit_id
            != first_commit_identity
            or self._request.round_index != 2
            or self._request.maximum_exact_kernel_queries != 9
            or self._request.selected_plan_risk_row_count != 3
            or self._request.unrestricted_value_challenger_row_count != 9
            or len(set(request_rows)) != 9
            or len(self._request.row_proofs) != 9
            or request_proof_rows != request_rows
            or authorization.selected_plan_risk_row_count != 3
            or authorization.unrestricted_value_challenger_row_count != 9
            or authorization.requested_distinct_ground_row_count != 9
            or self._request.request_preparation_kernel_calls != 0
            or self._request.request_preparation_ground_search_calls != 0
            or self._request.local_access_authorized is not True
            or self._request.frontier_local_scope_complete is not True
            or self._request.global_minimum_claimed is not False
            or request_document.get("request_id")
            != authorization.evidence_request_id
            or request_rows != authorization.authorized_ground_row_ids
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "ground semantic authority scope/linkage changed"
            )
        certificate = self._failed_result.get("certificate")
        if type(certificate) is not dict:
            raise InterleavedDurableEpochInvariantViolation(
                "ground semantic source lacks a certificate"
            )
        frontier = certificate.get("failed_proof_frontier")
        audit_result = getattr(self._typed_audit, "audit_result", None)
        typed_frontier = getattr(
            audit_result, "failed_proof_frontier", None
        )
        if (
            certificate.get("certified") is not False
            or type(frontier) is not dict
            or frontier.get("frontier_id")
            != authorization.failed_frontier_id
            or certificate.get("certificate_id")
            != authorization.failed_certificate_id
            or _digest_document(certificate)
            != authorization.failed_certificate_digest
            or self._failed_result.get("result_id")
            != authorization.failed_occurrence_result_id
            or getattr(self._typed_audit, "result_id", None)
            != authorization.source_strict_selected_audit_id
            or _digest_document(self._typed_audit.to_document())
            != authorization.source_strict_selected_audit_digest
            or self._request.source_audit_result_id
            != self._typed_audit.result_id
            or self._request.frontier_id
            != authorization.source_typed_frontier_id
            or typed_frontier is None
            or typed_frontier.frontier_id
            != authorization.source_typed_frontier_id
            or frontier.get("earliest_time_index") != 1
            or frontier.get("remaining_horizon") != 1
            or frontier.get("reason")
            != "UNRESOLVED_POLICY_PATH_DISTINCTION"
            or frontier.get("local_recovery_authorized") is not False
            or typed_frontier.earliest_time_index
            != frontier["earliest_time_index"]
            or typed_frontier.remaining_horizon
            != frontier["remaining_horizon"]
            or typed_frontier.reason.value != frontier["reason"]
            or typed_frontier.value_obligation_failed
            != frontier["value_obligation_failed"]
            or typed_frontier.risk_obligation_failed
            != frontier["risk_obligation_failed"]
            or typed_frontier.external_coverage_failed
            != frontier["external_coverage_failed"]
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "ground semantic authority is not an exact O2 failed proof"
            )


def _mint_ground_repair_authorization(
    *,
    preregistration: InterleavedWorkloadPreregistrationV1,
    occurrence: InterleavedOccurrenceV1,
    first_checkpoint_commit: Mapping[str, Any],
    failed_result: Mapping[str, Any],
    typed_audit: Any,
    request: Any,
) -> tuple[GroundRepairAuthorizationV1, _GroundRepairSemanticAuthority]:
    from acfqp._runtime_authority_v1 import bind_runtime_authority_v1

    certificate = failed_result["certificate"]
    frontier = certificate["failed_proof_frontier"]
    authorization = GroundRepairAuthorizationV1(
        preregistration.preregistration_id,
        occurrence.occurrence_id,
        first_checkpoint_commit["commit_id"],
        failed_result["result_id"],
        certificate["certificate_id"],
        frontier["frontier_id"],
        _digest_document(certificate),
        typed_audit.result_id,
        _digest_document(typed_audit.to_document()),
        typed_audit.audit_result.failed_proof_frontier.frontier_id,
        request.request_id,
        tuple(request.requested_ground_row_ids),
    )
    semantic_authority = _GroundRepairSemanticAuthority(
        authorization,
        preregistration,
        occurrence,
        first_checkpoint_commit,
        failed_result,
        typed_audit,
        request,
        _GROUND_SEMANTIC_MINT_NONCE,
    )
    authorization = bind_runtime_authority_v1(
        authorization, issuer=_GROUND_AUTH_ISSUER
    )
    _GROUND_AUTH_REGISTRY[id(authorization)] = (
        authorization,
        semantic_authority,
    )
    return authorization, semantic_authority


def _validate_proof_request_document(
    document: Mapping[str, Any],
    *,
    occurrence_id: str,
    query_id: str,
    checkpoint_commit_id: str,
    model_id: str,
    epoch_name: str,
    evidence_request_id: str,
    metric_id: str,
    schedule_code: str,
    proof_role: str,
    proposal_id: str | Mapping[str, str],
) -> dict[str, Any]:
    request = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "occurrence_id",
            "query_id",
            "checkpoint_commit_id",
            "model_id",
            "epoch_name",
            "evidence_request_id",
            "metric_id",
            "schedule_code",
            "proof_role",
            "proposal_id",
            "proof_request_id",
        },
        "interleaved proof request",
    )
    body = dict(request)
    identity = body.pop("proof_request_id")
    for value in (
        identity,
        request["occurrence_id"],
        request["query_id"],
        request["checkpoint_commit_id"],
        request["model_id"],
        request["evidence_request_id"],
        request["metric_id"],
    ):
        _cid(value, "proof request identity")
    if (
        request["schema"] != "acfqp.interleaved_proof_request.v1"
        or request["schema_version"] != SCHEMA_VERSION
        or request["profile_key"] != PROFILE_KEY
        or identity != _content_id("proof_request", body)
        or request["occurrence_id"] != occurrence_id
        or request["query_id"] != query_id
        or request["checkpoint_commit_id"] != checkpoint_commit_id
        or request["model_id"] != model_id
        or request["epoch_name"] != epoch_name
        or request["evidence_request_id"] != evidence_request_id
        or request["metric_id"] != metric_id
        or request["schedule_code"] != schedule_code
        or request["proof_role"] != proof_role
        or request["proposal_id"] != proposal_id
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "proof request content/context changed"
        )
    return request


def _validate_root_document(
    document: Mapping[str, Any],
    *,
    role: str,
    occurrence_id: str,
    query_id: str,
    checkpoint_commit_id: str,
    model_id: str,
    epoch_name: str,
    evidence_request_id: str,
) -> dict[str, Any]:
    id_field = (
        "candidate_root_id"
        if role == "candidate_root"
        else "selected_root_id"
    )
    root = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "occurrence_id",
            "query_id",
            "checkpoint_commit_id",
            "model_id",
            "epoch_name",
            "evidence_request_id",
            "proof_role",
            "proof_request",
            "proof_request_id",
            "metric_id",
            "schedule_code",
            "regret_facet_entry_id",
            "risk_facet_entry_id",
            "external_coverage_certified",
            "certified",
            "proposal_id",
            "failed_proof_frontier_id",
            id_field,
        },
        f"{role} document",
    )
    body = dict(root)
    identity = body.pop(id_field)
    expected_schema = (
        "acfqp.interleaved_candidate_root.v1"
        if role == "candidate_root"
        else "acfqp.interleaved_selected_root.v1"
    )
    for value in (
        identity,
        root["occurrence_id"],
        root["query_id"],
        root["checkpoint_commit_id"],
        root["model_id"],
        root["evidence_request_id"],
        root["proof_request_id"],
        root["metric_id"],
        root["regret_facet_entry_id"],
        root["risk_facet_entry_id"],
    ):
        _cid(value, f"{role} identity")
    if (
        root["schema"] != expected_schema
        or root["schema_version"] != SCHEMA_VERSION
        or root["profile_key"] != PROFILE_KEY
        or identity != _content_id(role, body)
        or root["occurrence_id"] != occurrence_id
        or root["query_id"] != query_id
        or root["checkpoint_commit_id"] != checkpoint_commit_id
        or root["model_id"] != model_id
        or root["epoch_name"] != epoch_name
        or root["evidence_request_id"] != evidence_request_id
        or root["schedule_code"] not in SCHEDULE_ORDER
        or type(root["external_coverage_certified"]) is not bool
        or type(root["certified"]) is not bool
    ):
        raise InterleavedDurableEpochInvariantViolation(
            f"{role} content or context changed"
        )
    candidate_null = {"kind": "NOT_APPLICABLE", "reason": "CANDIDATE"}
    no_failure_null = {
        "kind": "NOT_APPLICABLE",
        "reason": "NO_SELECTED_FAILURE",
    }
    if role == "candidate_root":
        proof_role = "CANDIDATE_RANKING_AUDIT"
        proof_proposal: str | Mapping[str, str] = {
            "kind": "NOT_APPLICABLE",
            "reason": "CANDIDATE_PRECEDES_PROPOSAL",
        }
        if (
            root["proposal_id"] != candidate_null
            or root["failed_proof_frontier_id"] != no_failure_null
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "candidate root acquired selected-root authority"
            )
    else:
        proof_role = "INDEPENDENT_SELECTED_PLAN_CERTIFICATE"
        _cid(root["proposal_id"], "selected-root proposal")
        proof_proposal = root["proposal_id"]
        if root["certified"]:
            if root["failed_proof_frontier_id"] != no_failure_null:
                raise InterleavedDurableEpochInvariantViolation(
                    "certified selected root retained a failure"
                )
        else:
            _cid(
                root["failed_proof_frontier_id"],
                "selected-root failed frontier",
            )
    proof_request = _validate_proof_request_document(
        root["proof_request"],
        occurrence_id=occurrence_id,
        query_id=query_id,
        checkpoint_commit_id=checkpoint_commit_id,
        model_id=model_id,
        epoch_name=epoch_name,
        evidence_request_id=evidence_request_id,
        metric_id=root["metric_id"],
        schedule_code=root["schedule_code"],
        proof_role=proof_role,
        proposal_id=proof_proposal,
    )
    if (
        root["proof_role"] != proof_role
        or root["proof_request_id"] != proof_request["proof_request_id"]
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "root proof-request binding changed"
        )
    return root


def _validate_failed_frontier_document(
    document: Mapping[str, Any],
    *,
    occurrence_id: str,
    query_id: str,
    model_id: str,
    metric_id: str,
) -> dict[str, Any]:
    frontier = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "occurrence_id",
            "query_id",
            "model_id",
            "metric_id",
            "plan_id",
            "earliest_time_index",
            "remaining_horizon",
            "obligations",
            "unresolved_exposure_sum",
            "value_obligation_failed",
            "risk_obligation_failed",
            "external_coverage_failed",
            "reason",
            "source_entry_ids",
            "hint_kind",
            "local_recovery_authorized",
            "causal_necessity_claimed",
            "causal_sufficiency_claimed",
            "infeasibility_claimed",
            "frontier_id",
        },
        "failed frontier",
    )
    body = dict(frontier)
    identity = body.pop("frontier_id")
    for value in (
        identity,
        frontier["occurrence_id"],
        frontier["query_id"],
        frontier["model_id"],
        frontier["metric_id"],
        frontier["plan_id"],
    ):
        _cid(value, "failed frontier identity")
    if (
        frontier["schema"]
        != "acfqp.interleaved_failed_proof_frontier.v1"
        or frontier["schema_version"] != SCHEMA_VERSION
        or frontier["profile_key"] != PROFILE_KEY
        or identity != _content_id("failed_frontier", body)
        or frontier["occurrence_id"] != occurrence_id
        or frontier["query_id"] != query_id
        or frontier["model_id"] != model_id
        or frontier["metric_id"] != metric_id
        or type(frontier["earliest_time_index"]) is not int
        or frontier["earliest_time_index"] not in {0, 1}
        or frontier["remaining_horizon"]
        != 2 - frontier["earliest_time_index"]
        or frontier["reason"]
        not in {
            "EXTERNAL_COVERAGE_ESCAPE",
            "UNRESOLVED_POLICY_PATH_DISTINCTION",
            "KNOWN_FIXED_PLAN_THRESHOLD_FAILURE",
        }
        or frontier["hint_kind"]
        != "NONAUTHORIZING_PROOF_OBLIGATION_HINT_V0057"
        or frontier["local_recovery_authorized"] is not False
        or frontier["causal_necessity_claimed"] is not False
        or frontier["causal_sufficiency_claimed"] is not False
        or frontier["infeasibility_claimed"] is not False
        or any(
            type(frontier[field]) is not bool
            for field in (
                "value_obligation_failed",
                "risk_obligation_failed",
                "external_coverage_failed",
            )
        )
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "failed frontier semantics changed"
        )
    source_entries = _exact_mapping(
        frontier["source_entry_ids"],
        {"C0", "C1", "D", "E", "F", "G"},
        "failed frontier source entries",
    )
    for value in source_entries.values():
        _cid(value, "failed frontier source entry")
    if type(frontier["obligations"]) is not list or not frontier["obligations"]:
        raise InterleavedDurableEpochInvariantViolation(
            "failed frontier obligations changed"
        )
    exposure = Fraction(0)
    prior_order: tuple[Any, ...] | None = None
    for obligation in frontier["obligations"]:
        row = _exact_mapping(
            obligation,
            {
                "time_index",
                "remaining_horizon",
                "state_id",
                "cell_id",
                "semantic_action_id",
                "support_ground_row_ids",
                "observed_ground_row_ids",
                "missing_ground_row_ids",
                "reachable_cell_mass_upper",
                "reachable_unknown_mass_upper",
                "reachable_external_continuation_mass_upper",
                "representative_disagreement",
            },
            "failed frontier obligation",
        )
        order = (
            row["time_index"],
            row["cell_id"],
            row["state_id"],
            row["semantic_action_id"],
        )
        if (
            type(row["time_index"]) is not int
            or row["time_index"] != frontier["earliest_time_index"]
            or row["remaining_horizon"] != frontier["remaining_horizon"]
            or type(row["representative_disagreement"]) is not bool
            or prior_order is not None
            and order < prior_order
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "failed frontier obligation order/timing changed"
            )
        prior_order = order
        for field in ("state_id", "cell_id", "semantic_action_id"):
            _cid(row[field], f"failed frontier {field}")
        support = row["support_ground_row_ids"]
        observed = row["observed_ground_row_ids"]
        missing = row["missing_ground_row_ids"]
        for values, label in (
            (support, "support"),
            (observed, "observed"),
            (missing, "missing"),
        ):
            if (
                type(values) is not list
                or values != sorted(set(values))
            ):
                raise InterleavedDurableEpochInvariantViolation(
                    f"failed frontier {label} rows changed"
                )
            for value in values:
                _cid(value, f"failed frontier {label} row")
        if sorted([*observed, *missing]) != support:
            raise InterleavedDurableEpochInvariantViolation(
                "failed frontier row partition changed"
            )
        _parse_fraction(
            row["reachable_cell_mass_upper"],
            "failed frontier reachable mass",
        )
        exposure += _parse_fraction(
            row["reachable_unknown_mass_upper"],
            "failed frontier unknown mass",
        )
        exposure += _parse_fraction(
            row["reachable_external_continuation_mass_upper"],
            "failed frontier external mass",
        )
    if _parse_fraction(
        frontier["unresolved_exposure_sum"],
        "failed frontier exposure sum",
    ) != exposure:
        raise InterleavedDurableEpochInvariantViolation(
            "failed frontier exposure sum changed"
        )
    return frontier


def _validate_occurrence_result_document(
    document: Mapping[str, Any],
    *,
    expected_after_facet_commit_id: str,
) -> dict[str, Any]:
    result = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "contract_version",
            "profile_key",
            "occurrence",
            "query",
            "preregistration_id",
            "eligibility_id",
            "epoch_name",
            "model_id",
            "evidence_request_id",
            "checkpoint_commit_id",
            "before_facet_commit_id",
            "appended_facet_entries",
            "query_facet_builder_calls",
            "lower_identity_hits",
            "fresh_root_builder_calls",
            "ground_transition_calls",
            "candidate_roots",
            "proposal",
            "selected_root",
            "certificate",
            "matching_buffer_imported",
            "live_epoch_module_imported",
            "result_id",
        },
        "occurrence result",
    )
    _validate_query_document(result["query"])
    _validate_occurrence_document(result["occurrence"], result["query"])
    body = dict(result)
    identity = body.pop("result_id")
    for value in (
        identity,
        result["preregistration_id"],
        result["eligibility_id"],
        result["model_id"],
        result["evidence_request_id"],
        result["checkpoint_commit_id"],
        result["before_facet_commit_id"],
        expected_after_facet_commit_id,
    ):
        _cid(value, "occurrence result identity")
    if (
        result["schema"] != "acfqp.interleaved_occurrence_result.v1"
        or result["schema_version"] != SCHEMA_VERSION
        or result["contract_version"] != CONTRACT_VERSION
        or result["profile_key"] != PROFILE_KEY
        or identity != _content_id("occurrence_result", body)
        or result["epoch_name"] not in {"FIRST", "FINAL"}
        or result["model_id"]
        != _EXPECTED_EPOCH_MODEL_IDS[result["epoch_name"]]
        or result["matching_buffer_imported"] is not False
        or result["live_epoch_module_imported"] is not False
        or result["ground_transition_calls"] != 0
        or result["fresh_root_builder_calls"] != 5
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "occurrence result identity/claim changed"
        )
    appended = result["appended_facet_entries"]
    builders = result["query_facet_builder_calls"]
    if (
        type(appended) is not list
        or appended
        != sorted(appended, key=lambda item: item["facet_entry_id"])
        or type(builders) is not int
        or builders not in {0, 8}
        or len(appended) != builders
        or result["lower_identity_hits"] != 50 - builders
        or (
            builders == 0
            and expected_after_facet_commit_id
            != result["before_facet_commit_id"]
        )
        or (
            builders > 0
            and expected_after_facet_commit_id
            == result["before_facet_commit_id"]
        )
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "occurrence facet accounting/commit closure changed"
        )
    seen_facet_keys = set()
    for entry in appended:
        _validate_facet_entry(entry)
        key = entry["key"]
        if (
            key["model_id"] != result["model_id"]
            or key["preregistration_id"] != result["preregistration_id"]
            or key["eligibility_id"] != result["eligibility_id"]
            or key["query_id"] != result["query"]["query_id"]
            or key["epoch_name"] != result["epoch_name"]
            or key["tolerance"]
            != result["query"][
                (
                    "normalized_regret_tolerance"
                    if key["gate_kind"] == "REGRET"
                    else "risk_tolerance"
                )
            ]
            or key["facet_key_id"] in seen_facet_keys
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "occurrence appended facet context changed"
            )
        seen_facet_keys.add(key["facet_key_id"])
    if builders and result["query"]["query_code"] != "Q_R":
        raise InterleavedDurableEpochInvariantViolation(
            "strict query fabricated query-specific facets"
        )
    roots = result["candidate_roots"]
    occurrence_id = result["occurrence"]["occurrence_id"]
    query_id = result["query"]["query_id"]
    checkpoint_id = result["checkpoint_commit_id"]
    if type(roots) is not list or len(roots) != 4:
        raise InterleavedDurableEpochInvariantViolation(
            "occurrence candidate-root cardinality changed"
        )
    validated_roots = [
        _validate_root_document(
            item,
            role="candidate_root",
            occurrence_id=occurrence_id,
            query_id=query_id,
            checkpoint_commit_id=checkpoint_id,
            model_id=result["model_id"],
            epoch_name=result["epoch_name"],
            evidence_request_id=result["evidence_request_id"],
        )
        for item in roots
    ]
    if (
        [item["schedule_code"] for item in validated_roots]
        != list(SCHEDULE_ORDER)
        or len({item["metric_id"] for item in validated_roots}) != 4
        or len(
            {item["candidate_root_id"] for item in validated_roots}
        )
        != 4
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "occurrence candidate-root order/identity changed"
        )
    proposal = _exact_mapping(
        result["proposal"],
        {
            "schema",
            "schema_version",
            "profile_key",
            "occurrence_id",
            "query_id",
            "checkpoint_commit_id",
            "candidate_root_ids",
            "selected_metric_id",
            "selected_schedule_code",
            "selection_mode",
            "proposal_id",
        },
        "occurrence proposal",
    )
    proposal_body = dict(proposal)
    proposal_identity = proposal_body.pop("proposal_id")
    if (
        proposal["schema"] != "acfqp.interleaved_plan_proposal.v1"
        or proposal["schema_version"] != SCHEMA_VERSION
        or proposal["profile_key"] != PROFILE_KEY
        or proposal_identity != _content_id("proposal", proposal_body)
        or proposal["occurrence_id"] != occurrence_id
        or proposal["query_id"] != query_id
        or proposal["checkpoint_commit_id"] != checkpoint_id
        or proposal["candidate_root_ids"]
        != [item["candidate_root_id"] for item in validated_roots]
        or proposal["selected_schedule_code"] not in SCHEDULE_ORDER
        or proposal["selection_mode"]
        not in {"CERTIFIED_REWARD_MAX", "MIN_FAILURE_RISK_FALLBACK"}
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "occurrence proposal identity/linkage changed"
        )
    selected_candidate = next(
        (
            item
            for item in validated_roots
            if item["metric_id"] == proposal["selected_metric_id"]
            and item["schedule_code"]
            == proposal["selected_schedule_code"]
        ),
        None,
    )
    if selected_candidate is None:
        raise InterleavedDurableEpochInvariantViolation(
            "proposal selected no candidate root"
        )
    selected_root = _validate_root_document(
        result["selected_root"],
        role="selected_root",
        occurrence_id=occurrence_id,
        query_id=query_id,
        checkpoint_commit_id=checkpoint_id,
        model_id=result["model_id"],
        epoch_name=result["epoch_name"],
        evidence_request_id=result["evidence_request_id"],
    )
    if (
        selected_root["proposal_id"] != proposal_identity
        or selected_root["metric_id"] != selected_candidate["metric_id"]
        or selected_root["schedule_code"]
        != selected_candidate["schedule_code"]
        or selected_root["regret_facet_entry_id"]
        != selected_candidate["regret_facet_entry_id"]
        or selected_root["risk_facet_entry_id"]
        != selected_candidate["risk_facet_entry_id"]
        or selected_root["external_coverage_certified"]
        is not selected_candidate["external_coverage_certified"]
        or selected_root["certified"] is not selected_candidate["certified"]
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "selected root differs from selected candidate"
        )
    certificate = _exact_mapping(
        result["certificate"],
        {
            "schema",
            "schema_version",
            "profile_key",
            "occurrence_id",
            "query_id",
            "checkpoint_commit_id",
            "proposal_id",
            "selected_root_id",
            "selected_schedule_code",
            "reward_lower",
            "reward_upper",
            "failure_lower",
            "failure_upper",
            "normalized_regret",
            "external_coverage_certified",
            "certified",
            "failed_proof_frontier",
            "certificate_id",
        },
        "occurrence certificate",
    )
    certificate_body = dict(certificate)
    certificate_identity = certificate_body.pop("certificate_id")
    for field in (
        "reward_lower",
        "reward_upper",
        "failure_lower",
        "failure_upper",
        "normalized_regret",
    ):
        _parse_fraction(certificate[field], f"certificate {field}")
    if (
        certificate["schema"] != "acfqp.interleaved_plan_certificate.v1"
        or certificate["schema_version"] != SCHEMA_VERSION
        or certificate["profile_key"] != PROFILE_KEY
        or certificate_identity
        != _content_id("certificate", certificate_body)
        or certificate["occurrence_id"] != occurrence_id
        or certificate["query_id"] != query_id
        or certificate["checkpoint_commit_id"] != checkpoint_id
        or certificate["proposal_id"] != proposal_identity
        or certificate["selected_root_id"]
        != selected_root["selected_root_id"]
        or certificate["selected_schedule_code"]
        != selected_root["schedule_code"]
        or certificate["external_coverage_certified"]
        is not selected_root["external_coverage_certified"]
        or certificate["certified"] is not selected_root["certified"]
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "occurrence certificate identity/linkage changed"
        )
    if certificate["certified"]:
        if (
            certificate["failed_proof_frontier"]
            != {
                "kind": "NOT_APPLICABLE",
                "reason": "SELECTED_PLAN_CERTIFIED",
            }
            or selected_root["failed_proof_frontier_id"]
            != {
                "kind": "NOT_APPLICABLE",
                "reason": "NO_SELECTED_FAILURE",
            }
            or proposal["selection_mode"] != "CERTIFIED_REWARD_MAX"
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "certified occurrence retained a failed frontier"
            )
    else:
        frontier = _validate_failed_frontier_document(
            certificate["failed_proof_frontier"],
            occurrence_id=occurrence_id,
            query_id=query_id,
            model_id=result["model_id"],
            metric_id=selected_root["metric_id"],
        )
        if (
            selected_root["failed_proof_frontier_id"]
            != frontier["frontier_id"]
            or proposal["selection_mode"]
            != "MIN_FAILURE_RISK_FALLBACK"
            or frontier["value_obligation_failed"]
            is not (
                _parse_fraction(
                    certificate["normalized_regret"],
                    "failed certificate regret",
                )
                > _parse_fraction(
                    result["query"]["normalized_regret_tolerance"],
                    "failed query regret tolerance",
                )
            )
            or frontier["risk_obligation_failed"]
            is not (
                _parse_fraction(
                    certificate["failure_upper"],
                    "failed certificate risk",
                )
                > _parse_fraction(
                    result["query"]["risk_tolerance"],
                    "failed query risk tolerance",
                )
            )
            or frontier["external_coverage_failed"]
            is certificate["external_coverage_certified"]
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "failed occurrence frontier/certificate changed"
            )
    return result


def _validate_occurrence_checkpoint_semantics(
    result_document: Mapping[str, Any],
    checkpoint: Mapping[str, Any],
) -> None:
    result = dict(result_document)
    metrics = {
        item["metric_id"]: item
        for item in checkpoint["candidate_metrics"]
    }
    if (
        result["model_id"] != checkpoint["model_id"]
        or result["epoch_name"] != checkpoint["epoch_name"]
        or result["preregistration_id"]
        != checkpoint["preregistration_document"]["preregistration_id"]
        or result["eligibility_id"]
        != checkpoint["eligibility"]["eligibility_id"]
        or result["evidence_request_id"]
        != checkpoint["model_document"]["evidence_request_id"]
        or len(metrics) != 4
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "occurrence/checkpoint identity binding changed"
        )
    query = result["query"]
    occurrence = result["occurrence"]
    expected_facet_entries: dict[str, dict[str, Any]] = {}
    for root in result["candidate_roots"]:
        metric = metrics.get(root["metric_id"])
        if (
            metric is None
            or metric["schedule_code"] != root["schedule_code"]
            or root["proof_request"]["occurrence_id"]
            != occurrence["occurrence_id"]
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "candidate root no longer consumes a checkpoint metric"
            )
        if query["query_code"] == "Q_R":
            regret_key = _facet_key(
                metric,
                query,
                checkpoint["eligibility"],
                checkpoint["preregistration_document"],
                "REGRET",
            )
            risk_key = _facet_key(
                metric,
                query,
                checkpoint["eligibility"],
                checkpoint["preregistration_document"],
                "RISK",
            )
            regret = _facet_entry(regret_key, metric)
            risk = _facet_entry(risk_key, metric)
            expected_facet_entries[regret_key["facet_key_id"]] = regret
            expected_facet_entries[risk_key["facet_key_id"]] = risk
            if (
                root["regret_facet_entry_id"]
                != regret["facet_entry_id"]
                or root["risk_facet_entry_id"]
                != risk["facet_entry_id"]
            ):
                raise InterleavedDurableEpochInvariantViolation(
                    "relaxed root facet differs from checkpoint D parent"
                )
        elif (
            root["regret_facet_entry_id"]
            != metric["strict_regret_entry_id"]
            or root["risk_facet_entry_id"]
            != metric["strict_risk_entry_id"]
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "strict root no longer consumes checkpoint E/F entries"
            )
    appended = result["appended_facet_entries"]
    if query["query_code"] == "Q_R":
        if any(
            expected_facet_entries.get(item["facet_key_id"]) != item
            for item in appended
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "appended facet is not derived from a checkpoint metric"
            )
    elif appended:
        raise InterleavedDurableEpochInvariantViolation(
            "strict occurrence appended relaxed facets"
        )
    selected_root = result["selected_root"]
    selected_metric = metrics.get(selected_root["metric_id"])
    if (
        selected_metric is None
        or selected_metric["schedule_code"]
        != selected_root["schedule_code"]
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "selected root no longer consumes a checkpoint metric"
        )


@dataclass(frozen=True, slots=True)
class InterleavedWorkerExecutionV1:
    execution_lane: str
    execution_label: str
    occurrence_index: int
    checkpoint_commit_id: str
    before_facet_commit_id: str
    after_facet_commit_id: str
    occurrence_result: Mapping[str, Any]
    worker_input_bytes: int
    worker_output_bytes: int
    fresh_os_process: bool = True
    exclusive_worker_output: bool = True
    host_exact_reconstruction_match: bool = True
    host_result_reconstruction_comparison_count: int = 1
    host_semantic_assertion_count: int = 1

    def __post_init__(self) -> None:
        expected_labels = {
            "O1_FIRST": (1, "Q_R", "FIRST"),
            "O2_FAILED_FIRST": (2, "Q_S", "FIRST"),
            "O2_RECERTIFIED_FINAL": (2, "Q_S", "FINAL"),
            "O3_FINAL": (3, "Q_R", "FINAL"),
            "O4_FINAL": (4, "Q_S", "FINAL"),
            "O5_FINAL": (5, "Q_R", "FINAL"),
        }
        if (
            self.execution_lane
            not in {"MAIN_GLOBAL_FACETS", "MATCHED_FACET_RESET"}
            or self.execution_label not in expected_labels
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "worker execution label changed"
            )
        index, query_code, epoch = expected_labels[self.execution_label]
        result = _validate_occurrence_result_document(
            self.occurrence_result,
            expected_after_facet_commit_id=self.after_facet_commit_id,
        )
        for value in (
            self.checkpoint_commit_id,
            self.before_facet_commit_id,
            self.after_facet_commit_id,
            result["result_id"],
        ):
            _cid(value, "worker execution identity")
        if (
            self.occurrence_index != index
            or result["occurrence"]["occurrence_index"] != index
            or result["query"]["query_code"] != query_code
            or result["epoch_name"] != epoch
            or result["checkpoint_commit_id"] != self.checkpoint_commit_id
            or result["before_facet_commit_id"]
            != self.before_facet_commit_id
            or type(self.worker_input_bytes) is not int
            or self.worker_input_bytes <= 0
            or type(self.worker_output_bytes) is not int
            or self.worker_output_bytes <= 0
            or self.fresh_os_process is not True
            or self.exclusive_worker_output is not True
            or self.host_exact_reconstruction_match is not True
            or self.host_result_reconstruction_comparison_count != 1
            or self.host_semantic_assertion_count != 1
            or result["ground_transition_calls"] != 0
            or result["matching_buffer_imported"] is not False
            or result["live_epoch_module_imported"] is not False
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "worker execution/process boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.interleaved_worker_execution.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "execution_lane": self.execution_lane,
            "execution_label": self.execution_label,
            "occurrence_index": self.occurrence_index,
            "checkpoint_commit_id": self.checkpoint_commit_id,
            "before_facet_commit_id": self.before_facet_commit_id,
            "after_facet_commit_id": self.after_facet_commit_id,
            "occurrence_result": dict(self.occurrence_result),
            "worker_input_bytes": self.worker_input_bytes,
            "worker_output_bytes": self.worker_output_bytes,
            "fresh_os_process": self.fresh_os_process,
            "exclusive_worker_output": self.exclusive_worker_output,
            "host_exact_reconstruction_match": (
                self.host_exact_reconstruction_match
            ),
            "host_result_reconstruction_comparison_count": (
                self.host_result_reconstruction_comparison_count
            ),
            "host_semantic_assertion_count": (
                self.host_semantic_assertion_count
            ),
        }

    @property
    def execution_id(self) -> str:
        return _content_id("worker_execution", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "execution_id": self.execution_id}


def _launch_interleaved_worker(
    campaign_root: Path,
    execution_lane: str,
    label: str,
    checkpoint_root: Path,
    checkpoint_commit_id: str,
    checkpoint_previous_commit_id: str | None,
    checkpoint_predecessor_store_root: Path | None,
    facet_root: Path,
    facet_commit_id: str,
    query: InterleavedThresholdQueryV1,
    occurrence: InterleavedOccurrenceV1,
) -> tuple[InterleavedWorkerExecutionV1, dict[str, Any]]:
    checkpoint_payload, checkpoint_commit = _load_checkpoint(
        checkpoint_root,
        checkpoint_commit_id,
        expected_previous_commit_id=checkpoint_previous_commit_id,
        predecessor_store_root=checkpoint_predecessor_store_root,
    )
    facet_payload, facet_commit = _load_facet_store(
        facet_root, facet_commit_id
    )
    checkpoint_snapshot = _directory_snapshot_id(
        checkpoint_root, f"{label}_CHECKPOINT_BEFORE"
    )
    predecessor_snapshot = (
        None
        if checkpoint_predecessor_store_root is None
        else _directory_snapshot_id(
            checkpoint_predecessor_store_root,
            f"{label}_PREDECESSOR_CHECKPOINT_BEFORE",
        )
    )
    facet_snapshot = _directory_snapshot_id(
        facet_root, f"{label}_FACET_BEFORE"
    )
    if execution_lane not in {
        "MAIN_GLOBAL_FACETS",
        "MATCHED_FACET_RESET",
    }:
        raise InterleavedDurableEpochInvariantViolation(
            "worker execution lane changed"
        )
    work_root = (
        campaign_root
        / "workers"
        / execution_lane.lower()
        / label.lower()
    )
    work_root.mkdir(parents=True)
    query_path = work_root / "query.json"
    occurrence_path = work_root / "occurrence.json"
    output_path = work_root / "result.json"
    query_bytes = _write_exclusive(query_path, query.to_document())
    occurrence_bytes = _write_exclusive(
        occurrence_path, occurrence.to_document()
    )
    source_root = Path(__file__).resolve().parents[1]
    module_path = Path(__file__).resolve()
    bootstrap = (
        "import runpy,sys;"
        f"sys.path.insert(0,{str(source_root)!r});"
        f"runpy.run_path({str(module_path)!r},run_name='__main__')"
    )
    command = (
        sys.executable,
        "-I",
        "-s",
        "-B",
        "-c",
        bootstrap,
        "--worker",
        str(checkpoint_root.resolve()),
        checkpoint_commit_id,
        (
            checkpoint_previous_commit_id
            if checkpoint_previous_commit_id is not None
            else "NONE"
        ),
        (
            str(checkpoint_predecessor_store_root.resolve())
            if checkpoint_predecessor_store_root is not None
            else "NONE"
        ),
        str(facet_root.resolve()),
        facet_commit_id,
        str(query_path.resolve()),
        str(occurrence_path.resolve()),
        str(output_path.resolve()),
        str(os.getpid()),
    )
    process = subprocess.Popen(
        command,
        cwd=Path(__file__).resolve().parents[2],
        env=_worker_environment(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = process.communicate(timeout=1200)
    except subprocess.TimeoutExpired as error:
        process.kill()
        process.communicate()
        raise InterleavedDurableEpochInvariantViolation(
            f"{label} model-only worker timed out"
        ) from error
    if process.returncode != 0:
        diagnostic = stderr.decode("utf-8", errors="replace")[-3000:]
        raise InterleavedDurableEpochInvariantViolation(
            f"{label} model-only worker failed: {diagnostic}"
        )
    if stdout:
        raise InterleavedDurableEpochInvariantViolation(
            f"{label} worker emitted unexpected stdout"
        )
    result, output_bytes = _read_canonical(output_path)
    expected = _compute_occurrence_document(
        checkpoint_payload,
        checkpoint_commit,
        facet_payload,
        facet_commit,
        query.to_document(),
        occurrence.to_document(),
        host_model_only_reconstruction=True,
    )
    if result != expected:
        raise InterleavedDurableEpochInvariantViolation(
            f"{label} worker result differs from host lease replay"
        )
    if (
        _directory_snapshot_id(
            checkpoint_root, f"{label}_CHECKPOINT_BEFORE"
        )
        != checkpoint_snapshot
        or (
            checkpoint_predecessor_store_root is not None
            and _directory_snapshot_id(
                checkpoint_predecessor_store_root,
                f"{label}_PREDECESSOR_CHECKPOINT_BEFORE",
            )
            != predecessor_snapshot
        )
        or _directory_snapshot_id(
            facet_root, f"{label}_FACET_BEFORE"
        )
        != facet_snapshot
    ):
        raise InterleavedDurableEpochInvariantViolation(
            f"{label} worker mutated a read-only model/facet input"
        )
    after_commit = _append_facet_store(
        facet_root,
        facet_commit_id,
        result["appended_facet_entries"],
    )
    _load_facet_store(facet_root, after_commit["commit_id"])
    execution = InterleavedWorkerExecutionV1(
        execution_lane,
        label,
        occurrence.occurrence_index,
        checkpoint_commit_id,
        facet_commit_id,
        after_commit["commit_id"],
        result,
        query_bytes + occurrence_bytes,
        output_bytes,
    )
    execution.__post_init__()
    return execution, after_commit


def _lower_record_from_resolution(
    runtime: Any,
    resolution: Any,
    temporal: Any,
) -> dict[str, Any]:
    entry = runtime.entries[resolution.entry_id]
    binding = runtime.bindings[resolution.slice_binding_id]
    value = runtime.live_values[resolution.node_key_id]
    body = {
        "schema": "acfqp.interleaved_lower_proof_value.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "entry": entry.to_document(),
        "slice_content": binding.content.to_document(),
        "value_document": temporal._value_document(entry.key.slot, value),
    }
    return {**body, "value_id": _content_id("lower_value", body)}


def _candidate_metrics_from_receipts(
    runtime: Any,
    receipts: tuple[Any, ...],
    model: Any,
    epoch_name: str,
    live: Any,
    temporal: Any,
) -> list[dict[str, Any]]:
    resolution_by_id = {
        item.resolution_id: item for item in runtime.resolutions
    }
    metrics: list[dict[str, Any]] = []
    if len(receipts) != 4:
        raise InterleavedDurableEpochInvariantViolation(
            "candidate metric source cardinality changed"
        )
    for receipt in receipts:
        lower_resolutions = [
            resolution_by_id[value]
            for value in receipt.resolution_ids
            if resolution_by_id[value].slot
            is not temporal.H2TemporalProofSlot.R
        ]
        if [item.slot.value for item in lower_resolutions] != list(
            LOWER_SLOTS
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "source candidate lower order changed"
            )
        bounds = receipt.audit_result.robust_bounds
        plan = receipt.request.contingent_plan
        semantic_key = [
            value
            for stage in plan.stages
            for value in live._semantic_stage_key(
                model, stage.assignments
            )
        ]
        body = {
            "schema": "acfqp.interleaved_candidate_metric.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "epoch_name": epoch_name,
            "model_id": model.model_id,
            "schedule_code": receipt.request.schedule_code,
            "semantic_key": semantic_key,
            "stage_assignment_ids": list(
                receipt.request.stage_assignment_ids
            ),
            "plan_document": plan.to_document(),
            "plan_id": plan.plan_id,
            "reward_lower": _fraction_document(
                bounds.policy_reward_lower
            ),
            "reward_upper": _fraction_document(
                bounds.policy_reward_upper
            ),
            "failure_lower": _fraction_document(
                bounds.policy_failure_lower
            ),
            "failure_upper": _fraction_document(
                bounds.policy_failure_upper
            ),
            "normalized_regret": _fraction_document(
                bounds.normalized_distribution_regret
            ),
            "external_coverage_certified": (
                bounds.external_coverage_certified
            ),
            "ordered_lower_entry_ids": [
                item.entry_id for item in lower_resolutions
            ],
            "strict_regret_entry_id": lower_resolutions[7].entry_id,
            "strict_risk_entry_id": lower_resolutions[8].entry_id,
        }
        metrics.append({**body, "metric_id": _content_id("metric", body)})
    if [item["schedule_code"] for item in metrics] != list(SCHEDULE_ORDER):
        raise InterleavedDurableEpochInvariantViolation(
            "source candidate schedule order changed"
        )
    return metrics


def _checkpoint_body_from_execution(
    *,
    epoch_name: str,
    runtime: Any,
    candidate_receipts: tuple[Any, ...],
    model: Any,
    strict_thresholds: Any,
    preregistration: InterleavedWorkloadPreregistrationV1,
    active_resolution_offset: int,
    live: Any,
    temporal: Any,
) -> tuple[dict[str, Any], set[str]]:
    active_resolutions = tuple(
        item
        for item in runtime.resolutions[
            active_resolution_offset:active_resolution_offset + 44
        ]
        if item.slot is not temporal.H2TemporalProofSlot.R
    )
    active_ids = {item.entry_id for item in active_resolutions}
    if len(active_resolutions) != 40 or len(active_ids) != 30:
        raise InterleavedDurableEpochInvariantViolation(
            "epoch candidate core no longer has 40 lower lookups/30 identities"
        )
    resolution_for_entry: dict[str, Any] = {}
    for resolution in runtime.resolutions:
        if (
            resolution.slot is not temporal.H2TemporalProofSlot.R
            and resolution.entry_id not in resolution_for_entry
        ):
            resolution_for_entry[resolution.entry_id] = resolution
    union_records = [
        _lower_record_from_resolution(
            runtime, resolution_for_entry[entry_id], temporal
        )
        for entry_id in runtime.entries
        if runtime.entries[entry_id].key.slot
        is not temporal.H2TemporalProofSlot.R
    ]
    union_records.sort(
        key=lambda item: (
            LOWER_SLOTS.index(item["entry"]["key"]["slot"]),
            item["entry"]["key"]["node_key_id"],
        )
    )
    union_ids = {
        item["entry"]["entry_id"] for item in union_records
    }
    inactive_ids = union_ids - active_ids
    initial_digest = live._canonical_input_digest(
        {
            "initial_distribution": [
                item.to_document()
                for item in strict_thresholds.initial_state_distribution
            ]
        }
    )
    reward_digest = live._canonical_input_digest(
        {
            "reward_weights": [
                item.to_document()
                for item in strict_thresholds.reward_weights
            ]
        }
    )
    eligibility = EpochThresholdFamilyEligibilityV1(
        preregistration.preregistration_id,
        model.model_id,
        preregistration.source_strict_thresholds_id,
        strict_thresholds.thresholds_id,
        tuple(item.query_id for item in preregistration.queries),
        2,
        initial_digest,
        reward_digest,
        _digest_document(model.to_document()),
        epoch_name,
    )
    body = {
        "schema": "acfqp.interleaved_epoch_checkpoint_payload.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "epoch_name": epoch_name,
        "model_id": model.model_id,
        "model_document": model.to_document(),
        "preregistration_document": preregistration.to_document(),
        "source_strict_thresholds_document": strict_thresholds.to_document(),
        "eligibility": eligibility.to_document(),
        "union_lower_entries": union_records,
        "active_lower_entry_ids": sorted(active_ids),
        "inactive_lower_entry_ids": sorted(inactive_ids),
        "candidate_metrics": _candidate_metrics_from_receipts(
            runtime, candidate_receipts, model, epoch_name, live, temporal
        ),
        "persisted_root_count": 0,
    }
    return body, active_ids


_RESULT_ISSUER = object()


def _validate_checkpoint_commit_summary(
    document: Mapping[str, Any],
    *,
    generation: int,
    previous_commit_id: str | None,
) -> dict[str, Any]:
    commit = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "generation",
            "previous_commit_id",
            "payload_id",
            "payload_sha256",
            "payload_size_bytes",
            "commit_complete",
            "commit_id",
        },
        "result checkpoint commit",
    )
    body = dict(commit)
    identity = body.pop("commit_id")
    expected_previous: str | Mapping[str, str] = (
        {
            "kind": "NOT_APPLICABLE",
            "reason": "FIRST_EPOCH",
        }
        if previous_commit_id is None
        else previous_commit_id
    )
    for value in (
        identity,
        commit["payload_id"],
        commit["payload_sha256"],
    ):
        _cid(value, "result checkpoint identity")
    if (
        commit["schema"]
        != "acfqp.interleaved_epoch_checkpoint_commit.v1"
        or commit["schema_version"] != SCHEMA_VERSION
        or commit["profile_key"] != PROFILE_KEY
        or identity != _content_id("checkpoint_commit", body)
        or commit["generation"] != generation
        or commit["previous_commit_id"] != expected_previous
        or type(commit["payload_size_bytes"]) is not int
        or commit["payload_size_bytes"] <= 0
        or commit["commit_complete"] is not True
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "result checkpoint summary changed"
        )
    return commit


def _validate_checkpoint_payload_commit_binding(
    payload_document: Mapping[str, Any],
    commit: Mapping[str, Any],
) -> dict[str, Any]:
    if type(payload_document) is not dict:
        raise InterleavedDurableEpochInvariantViolation(
            "result checkpoint payload type changed"
        )
    payload = dict(payload_document)
    _validate_checkpoint_payload(payload)
    payload_bytes = _canonical_json_bytes(payload)
    if (
        payload["payload_id"] != commit["payload_id"]
        or _checkpoint_payload_id(payload) != commit["payload_id"]
        or hashlib.sha256(payload_bytes).hexdigest()
        != commit["payload_sha256"]
        or len(payload_bytes) != commit["payload_size_bytes"]
        or (
            payload["epoch_name"] == "FIRST"
            and commit["generation"] != 1
        )
        or (
            payload["epoch_name"] == "FINAL"
            and commit["generation"] != 2
        )
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "result checkpoint payload/commit binding changed"
        )
    return payload


def _validate_facet_commit_summary(
    document: Mapping[str, Any],
    *,
    model_id: str,
    epoch_name: str,
    generation: int,
) -> dict[str, Any]:
    commit = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "model_id",
            "epoch_name",
            "generation",
            "payload_id",
            "payload_sha256",
            "payload_size_bytes",
            "previous_commit_id",
            "commit_complete",
            "commit_id",
        },
        "result facet commit",
    )
    body = dict(commit)
    identity = body.pop("commit_id")
    for value in (
        identity,
        commit["model_id"],
        commit["payload_id"],
        commit["payload_sha256"],
    ):
        _cid(value, "result facet identity")
    if (
        commit["schema"] != "acfqp.interleaved_facet_store_commit.v1"
        or commit["schema_version"] != SCHEMA_VERSION
        or commit["profile_key"] != PROFILE_KEY
        or identity != _content_id("facet_commit", body)
        or commit["model_id"] != model_id
        or commit["epoch_name"] != epoch_name
        or commit["generation"] != generation
        or type(commit["payload_size_bytes"]) is not int
        or commit["payload_size_bytes"] <= 0
        or commit["commit_complete"] is not True
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "result facet summary changed"
        )
    if generation == 0:
        if commit["previous_commit_id"] != {
            "kind": "NOT_APPLICABLE",
            "reason": "W0",
        }:
            raise InterleavedDurableEpochInvariantViolation(
                "result facet genesis changed"
            )
    else:
        _cid(commit["previous_commit_id"], "result facet predecessor")
    return commit


def _reconstruct_facet_chain_footprint(
    executions: tuple[InterleavedWorkerExecutionV1, ...],
    *,
    model_id: str,
    epoch_name: str,
) -> tuple[int, dict[str, Any]]:
    if not executions:
        raise InterleavedDurableEpochInvariantViolation(
            "facet footprint lacks executions"
        )
    entries: list[dict[str, Any]] = []
    payload = _facet_payload(model_id, epoch_name, entries, 0, None)
    commit = _facet_commit(payload)
    footprint = len(_canonical_json_bytes(payload)) + len(
        _canonical_json_bytes(commit)
    )
    if executions[0].before_facet_commit_id != commit["commit_id"]:
        raise InterleavedDurableEpochInvariantViolation(
            "worker facet chain does not start at canonical genesis"
        )
    for execution in executions:
        if execution.before_facet_commit_id != commit["commit_id"]:
            raise InterleavedDurableEpochInvariantViolation(
                "worker facet chain predecessor changed"
            )
        appended = execution.occurrence_result[
            "appended_facet_entries"
        ]
        if appended:
            entries = sorted(
                [*entries, *appended],
                key=lambda item: item["facet_entry_id"],
            )
            payload = _facet_payload(
                model_id,
                epoch_name,
                entries,
                commit["generation"] + 1,
                commit["commit_id"],
            )
            commit = _facet_commit(payload)
            footprint += len(_canonical_json_bytes(payload)) + len(
                _canonical_json_bytes(commit)
            )
        if execution.after_facet_commit_id != commit["commit_id"]:
            raise InterleavedDurableEpochInvariantViolation(
                "worker facet chain append changed"
            )
    return footprint, commit


def _validate_source_chain_document(
    document: Mapping[str, Any],
) -> dict[str, Any]:
    import acfqp.live_query_local_epoch_invalidation_v1 as live_source
    import acfqp.multistep_query_refinement_v1 as multistep_source

    source = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "input_authority_ids",
            "base_failure_frontier_id",
            "round_one_request",
            "round_one_bundle",
            "boundary_expansion",
            "first_overlay_build",
            "first_threshold_rebase",
            "first_strict_execution",
            "round_two_request",
            "round_two_bundle",
            "final_overlay_build",
            "final_threshold_rebase",
            "epoch_delta",
            "invalidation_manifest",
            "final_strict_execution",
            "source_chain_id",
        },
        "result source chain",
    )
    body = dict(source)
    identity = body.pop("source_chain_id")
    inputs = _exact_mapping(
        source["input_authority_ids"],
        {
            "observation_log_id",
            "semantics_profile_id",
            "observation_authority_id",
            "observed_synthesis_result_id",
            "source_thresholds_id",
            "base_plan_proposal_id",
            "failed_audit_id",
            "kernel_digest",
        },
        "source input authorities",
    )
    for value in (identity, source["base_failure_frontier_id"], *inputs.values()):
        _cid(value, "source-chain identity")
    if (
        source["schema"] != "acfqp.interleaved_live_source_chain.v1"
        or source["schema_version"] != SCHEMA_VERSION
        or source["profile_key"] != PROFILE_KEY
        or identity != _content_id("source_chain", body)
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "source-chain identity changed"
        )
    round_one_request = source["round_one_request"]
    round_one_bundle = source["round_one_bundle"]
    boundary = source["boundary_expansion"]
    first_build = source["first_overlay_build"]
    first_rebase = source["first_threshold_rebase"]
    first_execution = source["first_strict_execution"]
    round_two_request = source["round_two_request"]
    round_two_bundle = source["round_two_bundle"]
    final_build = source["final_overlay_build"]
    final_rebase = source["final_threshold_rebase"]
    delta = source["epoch_delta"]
    invalidation = source["invalidation_manifest"]
    final_execution = source["final_strict_execution"]
    required_documents = (
        round_one_request,
        round_one_bundle,
        boundary,
        first_build,
        first_rebase,
        first_execution,
        round_two_request,
        round_two_bundle,
        final_build,
        final_rebase,
        delta,
        invalidation,
        final_execution,
    )
    if any(type(item) is not dict for item in required_documents):
        raise InterleavedDurableEpochInvariantViolation(
            "source-chain nested artifact type changed"
        )
    request_fields = {
        "schema",
        "schema_version",
        "profile_key",
        "round_index",
        "phase",
        "source_model_id",
        "source_thresholds_id",
        "source_plan_id",
        "source_planner_result_id",
        "source_audit_result_id",
        "frontier_id",
        "requested_ground_row_ids",
        "row_proofs",
        "selected_plan_risk_row_count",
        "unrestricted_value_challenger_row_count",
        "maximum_exact_kernel_queries",
        "request_preparation_kernel_calls",
        "request_preparation_ground_search_calls",
        "local_access_authorized",
        "frontier_local_scope_complete",
        "global_minimum_claimed",
        "request_id",
    }
    round_two_request_fields = request_fields | {
        "requested_distinct_ground_row_count",
    }
    bundle_fields = {
        "schema",
        "schema_version",
        "profile_key",
        "round_index",
        "request_id",
        "kernel_authority_id",
        "evidence",
        "requested_ground_row_ids",
        "evidence_ledger_id",
        "exact_kernel_query_count",
        "positive_outcome_row_count",
        "environment_interaction_count",
        "generative_sample_count",
        "synthetic_rollout_count",
        "extra_ground_row_access_count",
        "bundle_id",
    }
    boundary_fields = {
        "schema",
        "schema_version",
        "profile_key",
        "base_model_id",
        "round_one_request_id",
        "round_one_bundle_id",
        "kernel_authority_id",
        "coordinate_proposal_id",
        "dsl_registry_id",
        "structural_binding_id",
        "catalogues",
        "registered_boundary_state_ids",
        "registered_boundary_ground_row_ids",
        "action_catalogue_query_count",
        "exact_transition_query_count",
        "ground_search_call_count",
        "caller_selected_state_scope",
        "expansion_id",
    }
    build_fields = {
        "schema",
        "schema_version",
        "profile_key",
        "round_index",
        "base_model_id",
        "previous_model_id",
        "source_thresholds_id",
        "source_plan_id",
        "source_failed_typed_audit_result_id",
        "evidence_request_id",
        "evidence_bundle_id",
        "boundary_expansion_id",
        "overlay_ledger_id",
        "model",
        "observed_ground_row_count",
        "missing_ground_row_count",
        "registered_boundary_state_count",
        "registered_boundary_action_count",
        "newly_observed_ground_row_count",
        "cumulative_exact_kernel_query_count",
        "base_model_mutated",
        "transition_closure_claimed",
        "promotion_authorized",
        "result_id",
    }
    rebase_fields = {
        "schema",
        "schema_version",
        "profile_key",
        "overlay_build_result_id",
        "source_thresholds_id",
        "source_partial_model_id",
        "query_scoped_model_id",
        "rebased_thresholds",
        "rebase_id",
    }
    execution_fields = {
        "schema",
        "schema_version",
        "profile_key",
        "epoch",
        "model_id",
        "thresholds_id",
        "request_receipts",
        "plan_proposal",
        "selected_plan_audit",
        "resolution_ids",
        "work",
        "pre_cache_state_id",
        "post_cache_state_id",
        "execution_id",
    }
    delta_fields = {
        "schema",
        "schema_version",
        "profile_key",
        "first_model_id",
        "final_model_id",
        "round_two_request_id",
        "round_two_bundle_id",
        "changed_ground_row_ids",
        "unchanged_ground_row_ids",
        "changed_realization_pairs",
        "direct_changed_slots",
        "affected_descendant_slots",
        "reusable_slots",
        "first_observed_count",
        "first_missing_count",
        "final_observed_count",
        "final_missing_count",
        "delta_id",
    }
    invalidation_fields = {
        "schema",
        "schema_version",
        "profile_key",
        "delta_id",
        "direct_changed_slots",
        "affected_descendant_slots",
        "reusable_slots",
        "matched_request_count",
        "reusable_distinct_entry_count",
        "output_equality_cannot_bypass_parent_change",
        "manifest_id",
    }
    for nested, fields, label in (
        (round_one_request, request_fields, "round-one request"),
        (
            round_two_request,
            round_two_request_fields,
            "round-two request",
        ),
        (round_one_bundle, bundle_fields, "round-one bundle"),
        (round_two_bundle, bundle_fields, "round-two bundle"),
        (boundary, boundary_fields, "boundary expansion"),
        (first_build, build_fields, "first overlay build"),
        (final_build, build_fields, "final overlay build"),
        (first_rebase, rebase_fields, "first threshold rebase"),
        (final_rebase, rebase_fields, "final threshold rebase"),
        (first_execution, execution_fields, "first strict execution"),
        (final_execution, execution_fields, "final strict execution"),
        (delta, delta_fields, "epoch delta"),
        (invalidation, invalidation_fields, "invalidation manifest"),
    ):
        _exact_mapping(nested, fields, f"source {label}")
    required_ids = (
        (round_one_request, "request_id"),
        (round_one_bundle, "bundle_id"),
        (boundary, "expansion_id"),
        (first_build, "result_id"),
        (first_rebase, "rebase_id"),
        (first_execution, "execution_id"),
        (round_two_request, "request_id"),
        (round_two_bundle, "bundle_id"),
        (final_build, "result_id"),
        (final_rebase, "rebase_id"),
        (delta, "delta_id"),
        (invalidation, "manifest_id"),
        (final_execution, "execution_id"),
    )
    for nested, field in required_ids:
        _cid(nested.get(field), f"source-chain {field}")
    for nested, field, role, content_function in (
        (
            round_one_request,
            "request_id",
            "request",
            multistep_source._content_id,
        ),
        (
            round_one_bundle,
            "bundle_id",
            "bundle",
            multistep_source._content_id,
        ),
        (
            boundary,
            "expansion_id",
            "boundary",
            multistep_source._content_id,
        ),
        (
            first_build,
            "result_id",
            "build",
            multistep_source._content_id,
        ),
        (
            first_rebase,
            "rebase_id",
            "rebase",
            multistep_source._content_id,
        ),
        (
            first_execution,
            "execution_id",
            "epoch",
            live_source._content_id,
        ),
        (
            round_two_request,
            "request_id",
            "request",
            multistep_source._content_id,
        ),
        (
            round_two_bundle,
            "bundle_id",
            "bundle",
            multistep_source._content_id,
        ),
        (
            final_build,
            "result_id",
            "build",
            multistep_source._content_id,
        ),
        (
            final_rebase,
            "rebase_id",
            "rebase",
            multistep_source._content_id,
        ),
        (
            delta,
            "delta_id",
            "delta",
            live_source._content_id,
        ),
        (
            invalidation,
            "manifest_id",
            "invalidation",
            live_source._content_id,
        ),
        (
            final_execution,
            "execution_id",
            "epoch",
            live_source._content_id,
        ),
    ):
        nested_body = dict(nested)
        nested_identity = nested_body.pop(field)
        if nested is round_two_request:
            # V0-057 closes the exact 3/9/9 authorization request in its
            # source transport without changing the authenticated upstream
            # V0-047 request identity consumed by the existing source chain.
            nested_body.pop("requested_distinct_ground_row_count")
        if nested_identity != content_function(role, nested_body):
            raise InterleavedDurableEpochInvariantViolation(
                f"source-chain nested {role} identity changed"
            )
    round_two_rows = round_two_request.get("requested_ground_row_ids")
    round_two_evidence = round_two_bundle.get("evidence")
    round_two_evidence_is_typed = (
        type(round_two_evidence) is list
        and all(type(item) is dict for item in round_two_evidence)
    )
    safe_evidence = (
        []
        if not round_two_evidence_is_typed
        else [
            item
            for item in round_two_evidence
            if item.get("terminal") is False
            and item.get("failure") is False
            and item.get("reward_features")
            == [
                {
                    "name": "match",
                    "value": _fraction_document(Fraction(1)),
                }
            ]
        ]
    )
    failure_evidence = (
        []
        if not round_two_evidence_is_typed
        else [
            item
            for item in round_two_evidence
            if item.get("terminal") is True
            and item.get("failure") is True
            and item.get("reward_features") == []
        ]
    )
    if (
        round_one_bundle.get("request_id")
        != round_one_request["request_id"]
        or boundary.get("round_one_request_id")
        != round_one_request["request_id"]
        or boundary.get("round_one_bundle_id")
        != round_one_bundle["bundle_id"]
        or first_build.get("evidence_request_id")
        != round_one_request["request_id"]
        or first_build.get("evidence_bundle_id")
        != round_one_bundle["bundle_id"]
        or first_build.get("boundary_expansion_id")
        != boundary["expansion_id"]
        or first_build.get("model", {}).get("model_id")
        != _EXPECTED_EPOCH_MODEL_IDS["FIRST"]
        or first_rebase.get("overlay_build_result_id")
        != first_build["result_id"]
        or first_execution.get("model_id")
        != _EXPECTED_EPOCH_MODEL_IDS["FIRST"]
        or round_two_request.get("source_model_id")
        != _EXPECTED_EPOCH_MODEL_IDS["FIRST"]
        or round_two_request.get("source_planner_result_id")
        != first_execution.get("plan_proposal", {}).get("result_id")
        or round_two_request.get("source_audit_result_id")
        != first_execution.get("selected_plan_audit", {}).get("result_id")
        or round_two_request.get("frontier_id")
        != first_execution.get("selected_plan_audit", {})
        .get("audit_result", {})
        .get("failed_proof_frontier", {})
        .get("frontier_id")
        or round_two_bundle.get("request_id")
        != round_two_request["request_id"]
        or final_build.get("evidence_request_id")
        != round_two_request["request_id"]
        or final_build.get("evidence_bundle_id")
        != round_two_bundle["bundle_id"]
        or final_build.get("previous_model_id")
        != _EXPECTED_EPOCH_MODEL_IDS["FIRST"]
        or final_build.get("model", {}).get("model_id")
        != _EXPECTED_EPOCH_MODEL_IDS["FINAL"]
        or final_rebase.get("overlay_build_result_id")
        != final_build["result_id"]
        or invalidation.get("delta_id") != delta["delta_id"]
        or delta.get("first_model_id")
        != _EXPECTED_EPOCH_MODEL_IDS["FIRST"]
        or delta.get("final_model_id")
        != _EXPECTED_EPOCH_MODEL_IDS["FINAL"]
        or delta.get("round_two_request_id")
        != round_two_request["request_id"]
        or delta.get("round_two_bundle_id")
        != round_two_bundle["bundle_id"]
        or invalidation.get("direct_changed_slots")
        != delta.get("direct_changed_slots")
        or invalidation.get("affected_descendant_slots")
        != delta.get("affected_descendant_slots")
        or invalidation.get("reusable_slots")
        != delta.get("reusable_slots")
        or final_execution.get("model_id")
        != _EXPECTED_EPOCH_MODEL_IDS["FINAL"]
        or round_one_request.get("round_index") != 1
        or round_two_request.get("round_index") != 2
        or round_one_request.get("maximum_exact_kernel_queries") != 4
        or round_two_request.get("maximum_exact_kernel_queries") != 9
        or round_two_request.get("selected_plan_risk_row_count") != 3
        or round_two_request.get(
            "unrestricted_value_challenger_row_count"
        )
        != 9
        or round_two_request.get(
            "requested_distinct_ground_row_count"
        )
        != 9
        or type(round_two_rows) is not list
        or len(round_two_rows) != 9
        or len(set(round_two_rows)) != 9
        or not round_two_evidence_is_typed
        or len(round_two_evidence) != 9
        or [
            item.get("sequence_number") for item in round_two_evidence
        ]
        != list(range(1, 10))
        or [item.get("ground_row_id") for item in round_two_evidence]
        != round_two_rows
        or any(
            item.get("request_id") != round_two_request["request_id"]
            or item.get("round_index") != 2
            for item in round_two_evidence
        )
        or len(safe_evidence) != 3
        or len(failure_evidence) != 6
        or round_one_bundle.get("exact_kernel_query_count") != 4
        or round_two_bundle.get("exact_kernel_query_count") != 9
        or boundary.get("action_catalogue_query_count") != 3
        or first_build.get("observed_ground_row_count") != 11
        or first_build.get("missing_ground_row_count") != 9
        or final_build.get("observed_ground_row_count") != 20
        or final_build.get("missing_ground_row_count") != 0
        or first_execution.get("epoch") != "FIRST_OVERLAY_V3"
        or first_execution.get("work", {}).get("computed") != 35
        or first_execution.get("work", {}).get("reused") != 20
        or final_execution.get("epoch") != "FINAL_OVERLAY_V3"
        or final_execution.get("work", {}).get("computed") != 33
        or final_execution.get("work", {}).get("reused") != 22
        or delta.get("first_observed_count") != 11
        or delta.get("first_missing_count") != 9
        or delta.get("final_observed_count") != 20
        or delta.get("final_missing_count") != 0
        or invalidation.get("reusable_distinct_entry_count") != 2
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "source-chain nested linkage changed"
        )
    return source


def _validate_accounting_document(
    document: Mapping[str, Any],
    *,
    main_workers: tuple[InterleavedWorkerExecutionV1, ...],
    reset_workers: tuple[InterleavedWorkerExecutionV1, ...],
    first_checkpoint: Mapping[str, Any],
    final_checkpoint: Mapping[str, Any],
    main_facet_footprint: int,
    reset_facet_footprint: int,
) -> dict[str, Any]:
    fields = {
        "schema",
        "schema_version",
        "profile_key",
        "logical_occurrence_count",
        "fresh_worker_process_count",
        "main_fresh_worker_process_count",
        "reset_fresh_worker_process_count",
        "main_host_worker_result_reconstruction_comparison_count",
        "reset_host_worker_result_reconstruction_comparison_count",
        "main_host_worker_semantic_assertion_count",
        "reset_host_worker_semantic_assertion_count",
        "host_checkpoint_store_load_count",
        "host_cross_store_lineage_check_count",
        "host_facet_store_load_count",
        "host_worker_result_reconstruction_comparison_count",
        "host_input_snapshot_hash_count",
        "host_immutability_comparison_count",
        "host_worker_semantic_assertion_count",
        "host_verification_counter_scope",
        "worker_ground_transition_calls",
        "round_one_ground_transition_calls",
        "certificate_triggered_ground_transition_calls",
        "source_ground_transition_calls",
        "boundary_catalogue_calls",
        "first_union_lower_count",
        "first_active_lower_count",
        "final_union_lower_count",
        "final_active_lower_count",
        "final_inactive_lower_count",
        "epoch_lower_recomputations",
        "epoch_lower_lookup_reuses",
        "epoch_distinct_entry_reuses",
        "epoch_reused_slots",
        "main_query_facet_builder_calls",
        "main_lower_identity_hits",
        "reset_query_facet_builder_calls",
        "reset_lower_identity_hits",
        "main_native_query_facet_builder_calls",
        "main_native_lower_identity_hits",
        "reset_native_query_facet_builder_calls",
        "reset_native_lower_identity_hits",
        "campaign_native_query_facet_builder_calls",
        "campaign_native_lower_identity_hits",
        "main_native_fresh_root_builder_calls",
        "reset_native_fresh_root_builder_calls",
        "campaign_native_fresh_root_builder_calls",
        "main_logical_query_facet_builder_calls",
        "main_logical_lower_identity_hits",
        "reset_logical_query_facet_builder_calls",
        "reset_logical_lower_identity_hits",
        "main_recertification_query_facet_builder_calls",
        "main_recertification_lower_identity_hits",
        "reset_recertification_query_facet_builder_calls",
        "reset_recertification_lower_identity_hits",
        "main_worker_input_bytes",
        "main_worker_output_bytes",
        "reset_worker_input_bytes",
        "reset_worker_output_bytes",
        "campaign_worker_input_bytes",
        "campaign_worker_output_bytes",
        "worker_input_byte_scope",
        "worker_output_byte_scope",
        "checkpoint_artifact_bytes",
        "main_facet_artifact_bytes",
        "reset_facet_artifact_bytes",
        "campaign_checkpoint_and_facet_artifact_bytes",
        "artifact_byte_semantics",
        "main_selected_schedule_codes",
        "reset_selected_schedule_codes",
        "model_only_after_final_repair",
        "query_local_nonpromotable",
        "acquisition_query_neutral",
        "counter_registry_complete",
        "official_workvector_claimed",
        "accounting_id",
    }
    accounting = _exact_mapping(document, fields, "epoch accounting")
    body = dict(accounting)
    identity = body.pop("accounting_id")
    _cid(identity, "epoch accounting identity")
    main_builders = [
        item.occurrence_result["query_facet_builder_calls"]
        for item in main_workers
    ]
    main_hits = [
        item.occurrence_result["lower_identity_hits"]
        for item in main_workers
    ]
    reset_builders = [
        item.occurrence_result["query_facet_builder_calls"]
        for item in reset_workers
    ]
    reset_hits = [
        item.occurrence_result["lower_identity_hits"]
        for item in reset_workers
    ]
    main_inputs = [item.worker_input_bytes for item in main_workers]
    main_outputs = [item.worker_output_bytes for item in main_workers]
    reset_inputs = [item.worker_input_bytes for item in reset_workers]
    reset_outputs = [item.worker_output_bytes for item in reset_workers]
    first_epoch_worker_count = sum(
        item.occurrence_result["epoch_name"] == "FIRST"
        for item in (*main_workers, *reset_workers)
    )
    final_epoch_worker_count = sum(
        item.occurrence_result["epoch_name"] == "FINAL"
        for item in (*main_workers, *reset_workers)
    )
    worker_count = len(main_workers) + len(reset_workers)
    checkpoint_footprint = sum(
        item["payload_size_bytes"] + len(_canonical_json_bytes(item))
        for item in (first_checkpoint, final_checkpoint)
    )
    exact_scalars = {
        "logical_occurrence_count": 5,
        "fresh_worker_process_count": 12,
        "main_fresh_worker_process_count": 6,
        "reset_fresh_worker_process_count": 6,
        "main_host_worker_result_reconstruction_comparison_count": sum(
            item.host_result_reconstruction_comparison_count
            for item in main_workers
        ),
        "reset_host_worker_result_reconstruction_comparison_count": sum(
            item.host_result_reconstruction_comparison_count
            for item in reset_workers
        ),
        "main_host_worker_semantic_assertion_count": sum(
            item.host_semantic_assertion_count for item in main_workers
        ),
        "reset_host_worker_semantic_assertion_count": sum(
            item.host_semantic_assertion_count for item in reset_workers
        ),
        "host_checkpoint_store_load_count": (
            3 + first_epoch_worker_count + 2 * final_epoch_worker_count
        ),
        "host_cross_store_lineage_check_count": (
            1 + final_epoch_worker_count
        ),
        "host_facet_store_load_count": 3 * worker_count,
        "host_worker_result_reconstruction_comparison_count": sum(
            item.host_result_reconstruction_comparison_count
            for item in (*main_workers, *reset_workers)
        ),
        "host_input_snapshot_hash_count": (
            4 * worker_count + 2 * final_epoch_worker_count
        ),
        "host_immutability_comparison_count": (
            2 * worker_count + final_epoch_worker_count
        ),
        "host_worker_semantic_assertion_count": sum(
            item.host_semantic_assertion_count
            for item in (*main_workers, *reset_workers)
        ),
        "worker_ground_transition_calls": 0,
        "round_one_ground_transition_calls": 4,
        "certificate_triggered_ground_transition_calls": 9,
        "source_ground_transition_calls": 13,
        "boundary_catalogue_calls": 3,
        "first_union_lower_count": 30,
        "first_active_lower_count": 30,
        "final_union_lower_count": 58,
        "final_active_lower_count": 30,
        "final_inactive_lower_count": 28,
        "epoch_lower_recomputations": 28,
        "epoch_lower_lookup_reuses": 22,
        "epoch_distinct_entry_reuses": 2,
        "main_native_query_facet_builder_calls": sum(main_builders),
        "main_native_lower_identity_hits": sum(main_hits),
        "reset_native_query_facet_builder_calls": sum(reset_builders),
        "reset_native_lower_identity_hits": sum(reset_hits),
        "campaign_native_query_facet_builder_calls": (
            sum(main_builders) + sum(reset_builders)
        ),
        "campaign_native_lower_identity_hits": (
            sum(main_hits) + sum(reset_hits)
        ),
        "main_native_fresh_root_builder_calls": 30,
        "reset_native_fresh_root_builder_calls": 30,
        "campaign_native_fresh_root_builder_calls": 60,
        "main_logical_query_facet_builder_calls": sum(
            main_builders[index] for index in (0, 2, 3, 4, 5)
        ),
        "main_logical_lower_identity_hits": sum(
            main_hits[index] for index in (0, 2, 3, 4, 5)
        ),
        "reset_logical_query_facet_builder_calls": sum(
            reset_builders[index] for index in (0, 2, 3, 4, 5)
        ),
        "reset_logical_lower_identity_hits": sum(
            reset_hits[index] for index in (0, 2, 3, 4, 5)
        ),
        "main_recertification_query_facet_builder_calls": main_builders[2],
        "main_recertification_lower_identity_hits": main_hits[2],
        "reset_recertification_query_facet_builder_calls": reset_builders[2],
        "reset_recertification_lower_identity_hits": reset_hits[2],
        "campaign_worker_input_bytes": sum(main_inputs) + sum(reset_inputs),
        "campaign_worker_output_bytes": (
            sum(main_outputs) + sum(reset_outputs)
        ),
        "checkpoint_artifact_bytes": checkpoint_footprint,
        "main_facet_artifact_bytes": main_facet_footprint,
        "reset_facet_artifact_bytes": reset_facet_footprint,
        "campaign_checkpoint_and_facet_artifact_bytes": (
            checkpoint_footprint
            + main_facet_footprint
            + reset_facet_footprint
        ),
    }
    if (
        accounting["schema"] != "acfqp.interleaved_epoch_accounting.v1"
        or accounting["schema_version"] != SCHEMA_VERSION
        or accounting["profile_key"] != PROFILE_KEY
        or identity != _content_id("accounting", body)
        or any(accounting[key] != value for key, value in exact_scalars.items())
        or accounting["epoch_reused_slots"] != ["C0"]
        or accounting["main_query_facet_builder_calls"] != main_builders
        or accounting["main_lower_identity_hits"] != main_hits
        or accounting["reset_query_facet_builder_calls"] != reset_builders
        or accounting["reset_lower_identity_hits"] != reset_hits
        or accounting["main_worker_input_bytes"] != main_inputs
        or accounting["main_worker_output_bytes"] != main_outputs
        or accounting["reset_worker_input_bytes"] != reset_inputs
        or accounting["reset_worker_output_bytes"] != reset_outputs
        or accounting["main_selected_schedule_codes"] != ["A0A0"] * 6
        or accounting["reset_selected_schedule_codes"] != ["A0A0"] * 6
        or accounting["worker_input_byte_scope"]
        != "QUERY_AND_OCCURRENCE_FILES_ONLY"
        or accounting["worker_output_byte_scope"] != "RESULT_FILE_ONLY"
        or accounting["artifact_byte_semantics"]
        != "SERIALIZED_FOOTPRINT_NOT_IO_TRAFFIC"
        or accounting["host_verification_counter_scope"]
        != "OPERATIONAL_PRE_ACCOUNTING_REGISTERED_CHECKS_ONLY"
        or accounting["model_only_after_final_repair"] is not True
        or accounting["query_local_nonpromotable"] is not True
        or accounting["acquisition_query_neutral"] is not False
        or accounting["counter_registry_complete"] is not False
        or accounting["official_workvector_claimed"] is not False
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "epoch accounting does not replay from native workers"
        )
    return accounting


@dataclass(frozen=True, slots=True)
class InterleavedDurableEpochResultV1:
    preregistration: InterleavedWorkloadPreregistrationV1
    source_chain: Mapping[str, Any]
    first_checkpoint_commit: Mapping[str, Any]
    final_checkpoint_commit: Mapping[str, Any]
    first_checkpoint_payload: Mapping[str, Any]
    final_checkpoint_payload: Mapping[str, Any]
    first_final_facet_commit: Mapping[str, Any]
    final_final_facet_commit: Mapping[str, Any]
    worker_executions: tuple[InterleavedWorkerExecutionV1, ...]
    matched_reset_worker_executions: tuple[
        InterleavedWorkerExecutionV1, ...
    ]
    ground_repair_authorization: GroundRepairAuthorizationV1
    accounting: Mapping[str, Any]
    campaign_snapshot_id: str
    event_log: InterleavedEventLogV1
    query_local_model_only: bool = True
    promotion_authorized: bool = False
    policy_switch_claimed: bool = False
    learned_dynamics_claimed: bool = False
    coordinate_invention_claimed: bool = False
    sample_efficiency_claimed: bool = False
    workload_economics_claimed: bool = False
    official_execution_allowed: bool = False
    status: str = SUCCESS_STATUS
    _instance_mint: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        expected_labels = (
            "O1_FIRST",
            "O2_FAILED_FIRST",
            "O2_RECERTIFIED_FINAL",
            "O3_FINAL",
            "O4_FINAL",
            "O5_FINAL",
        )
        if (
            type(self.preregistration)
            is not InterleavedWorkloadPreregistrationV1
            or type(self.worker_executions) is not tuple
            or len(self.worker_executions) != 6
            or any(
                type(item) is not InterleavedWorkerExecutionV1
                for item in self.worker_executions
            )
            or type(self.matched_reset_worker_executions) is not tuple
            or len(self.matched_reset_worker_executions) != 6
            or any(
                type(item) is not InterleavedWorkerExecutionV1
                for item in self.matched_reset_worker_executions
            )
            or type(self.ground_repair_authorization)
            is not GroundRepairAuthorizationV1
            or type(self.event_log) is not InterleavedEventLogV1
            or self.query_local_model_only is not True
            or self.promotion_authorized is not False
            or self.policy_switch_claimed is not False
            or self.learned_dynamics_claimed is not False
            or self.coordinate_invention_claimed is not False
            or self.sample_efficiency_claimed is not False
            or self.workload_economics_claimed is not False
            or self.official_execution_allowed is not False
            or self.status != SUCCESS_STATUS
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "interleaved campaign claim boundary changed"
            )
        self.preregistration.__post_init__()
        if (
            tuple(
                item.execution_label for item in self.worker_executions
            )
            != expected_labels
            or tuple(
                item.execution_label
                for item in self.matched_reset_worker_executions
            )
            != expected_labels
            or
            any(
                item.execution_lane != "MAIN_GLOBAL_FACETS"
                for item in self.worker_executions
            )
            or any(
                item.execution_lane != "MATCHED_FACET_RESET"
                for item in self.matched_reset_worker_executions
            )
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "worker lane partition changed"
            )
        for item in (
            *self.worker_executions,
            *self.matched_reset_worker_executions,
        ):
            item.__post_init__()
        authorization = _require_ground_repair_authorization(
            self.ground_repair_authorization
        )
        event_log = _require_interleaved_event_log(self.event_log)
        if (
            event_log.preregistration_id
            != self.preregistration.preregistration_id
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "result event log/preregistration changed"
            )
        first_checkpoint = _validate_checkpoint_commit_summary(
            self.first_checkpoint_commit,
            generation=1,
            previous_commit_id=None,
        )
        final_checkpoint = _validate_checkpoint_commit_summary(
            self.final_checkpoint_commit,
            generation=2,
            previous_commit_id=first_checkpoint["commit_id"],
        )
        first_payload = _validate_checkpoint_payload_commit_binding(
            self.first_checkpoint_payload,
            first_checkpoint,
        )
        final_payload = _validate_checkpoint_payload_commit_binding(
            self.final_checkpoint_payload,
            final_checkpoint,
        )
        _validate_cross_store_checkpoint_lineage(
            first_payload,
            first_checkpoint,
            final_payload,
            final_checkpoint,
        )
        for item in (
            *self.worker_executions,
            *self.matched_reset_worker_executions,
        ):
            _validate_occurrence_checkpoint_semantics(
                item.occurrence_result,
                (
                    first_payload
                    if item.occurrence_result["epoch_name"] == "FIRST"
                    else final_payload
                ),
            )
        if (
            any(
                item.checkpoint_commit_id
                != first_checkpoint["commit_id"]
                for item in (
                    self.worker_executions[0],
                    self.worker_executions[1],
                    self.matched_reset_worker_executions[0],
                    self.matched_reset_worker_executions[1],
                )
            )
            or any(
                item.checkpoint_commit_id
                != final_checkpoint["commit_id"]
                for item in (
                    *self.worker_executions[2:],
                    *self.matched_reset_worker_executions[2:],
                )
            )
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "worker/checkpoint epoch binding changed"
            )
        first_facet_footprint, reconstructed_first_facet = (
            _reconstruct_facet_chain_footprint(
                self.worker_executions[:2],
                model_id=_EXPECTED_EPOCH_MODEL_IDS["FIRST"],
                epoch_name="FIRST",
            )
        )
        final_facet_footprint, reconstructed_final_facet = (
            _reconstruct_facet_chain_footprint(
                self.worker_executions[2:],
                model_id=_EXPECTED_EPOCH_MODEL_IDS["FINAL"],
                epoch_name="FINAL",
            )
        )
        first_facet = _validate_facet_commit_summary(
            self.first_final_facet_commit,
            model_id=_EXPECTED_EPOCH_MODEL_IDS["FIRST"],
            epoch_name="FIRST",
            generation=1,
        )
        final_facet = _validate_facet_commit_summary(
            self.final_final_facet_commit,
            model_id=_EXPECTED_EPOCH_MODEL_IDS["FINAL"],
            epoch_name="FINAL",
            generation=1,
        )
        if (
            first_facet != reconstructed_first_facet
            or final_facet != reconstructed_final_facet
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "result facet tip differs from worker append replay"
            )
        reset_facet_footprint = 0
        for execution in self.matched_reset_worker_executions:
            footprint, _ = _reconstruct_facet_chain_footprint(
                (execution,),
                model_id=(
                    _EXPECTED_EPOCH_MODEL_IDS["FIRST"]
                    if execution.occurrence_result["epoch_name"] == "FIRST"
                    else _EXPECTED_EPOCH_MODEL_IDS["FINAL"]
                ),
                epoch_name=execution.occurrence_result["epoch_name"],
            )
            reset_facet_footprint += footprint
        source = _validate_source_chain_document(self.source_chain)
        accounting = _validate_accounting_document(
            self.accounting,
            main_workers=self.worker_executions,
            reset_workers=self.matched_reset_worker_executions,
            first_checkpoint=first_checkpoint,
            final_checkpoint=final_checkpoint,
            main_facet_footprint=(
                first_facet_footprint + final_facet_footprint
            ),
            reset_facet_footprint=reset_facet_footprint,
        )
        main_certified = tuple(
            item.occurrence_result["certificate"]["certified"]
            for item in self.worker_executions
        )
        reset_certified = tuple(
            item.occurrence_result["certificate"]["certified"]
            for item in self.matched_reset_worker_executions
        )
        if (
            main_certified != (True, False, True, True, True, True)
            or reset_certified
            != (True, False, True, True, True, True)
            or source["input_authority_ids"]
            != self.preregistration.input_authority_ids
            or source["first_overlay_build"]["base_model_id"]
            != self.preregistration.base_model_id
            or source["first_overlay_build"]["model"][
                "coordinate_proposal_id"
            ]
            != self.preregistration.coordinate_proposal_id
            or source["first_overlay_build"]["model"][
                "semantics_profile_id"
            ]
            != self.preregistration.input_authority_ids[
                "semantics_profile_id"
            ]
            or authorization.preregistration_id
            != self.preregistration.preregistration_id
            or authorization.occurrence_id
            != self.preregistration.occurrences[1].occurrence_id
            or authorization.first_checkpoint_commit_id
            != first_checkpoint["commit_id"]
            or authorization.failed_occurrence_result_id
            != self.worker_executions[1].occurrence_result["result_id"]
            or authorization.failed_certificate_id
            != self.worker_executions[1].occurrence_result["certificate"][
                "certificate_id"
            ]
            or authorization.failed_frontier_id
            != self.worker_executions[1].occurrence_result["certificate"][
                "failed_proof_frontier"
            ]["frontier_id"]
            or authorization.evidence_request_id
            != source["round_two_request"]["request_id"]
            or authorization.selected_plan_risk_row_count != 3
            or authorization.unrestricted_value_challenger_row_count != 9
            or authorization.requested_distinct_ground_row_count != 9
            or list(authorization.authorized_ground_row_ids)
            != source["round_two_request"]["requested_ground_row_ids"]
            or source["round_two_bundle"]["exact_kernel_query_count"] != 9
            or source["round_one_bundle"]["exact_kernel_query_count"] != 4
            or source["boundary_expansion"][
                "action_catalogue_query_count"
            ]
            != 3
            or source["first_overlay_build"]["observed_ground_row_count"]
            != 11
            or source["first_overlay_build"]["missing_ground_row_count"] != 9
            or source["final_overlay_build"]["observed_ground_row_count"]
            != 20
            or source["final_overlay_build"]["missing_ground_row_count"] != 0
            or source["invalidation_manifest"][
                "reusable_distinct_entry_count"
            ]
            != 2
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "result causal source/authorization semantics changed"
            )
        expected_event_artifacts = (
            self.preregistration.preregistration_id,
            _query_eligibility_freeze_id(self.preregistration),
            source["input_authority_ids"]["failed_audit_id"],
            source["round_one_bundle"]["bundle_id"],
            source["boundary_expansion"]["expansion_id"],
            source["first_overlay_build"]["model"]["model_id"],
            first_checkpoint["commit_id"],
            self.preregistration.occurrences[0].occurrence_id,
            self.worker_executions[0].execution_id,
            self.preregistration.occurrences[1].occurrence_id,
            self.worker_executions[1].execution_id,
            source["round_two_request"]["request_id"],
            authorization.authorization_id,
            source["round_two_bundle"]["bundle_id"],
            source["final_overlay_build"]["model"]["model_id"],
            source["invalidation_manifest"]["manifest_id"],
            final_checkpoint["commit_id"],
            self.preregistration.occurrences[1].occurrence_id,
            self.worker_executions[2].execution_id,
            self.worker_executions[3].execution_id,
            self.worker_executions[4].execution_id,
            self.worker_executions[5].execution_id,
            accounting["accounting_id"],
        )
        if tuple(
            item.artifact_id for item in event_log.events
        ) != expected_event_artifacts:
            raise InterleavedDurableEpochInvariantViolation(
                "event ledger artifact semantics changed"
            )
        _cid(self.campaign_snapshot_id, "campaign snapshot")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.interleaved_durable_epoch_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration": self.preregistration.to_document(),
            "source_chain": dict(self.source_chain),
            "first_checkpoint_commit": dict(
                self.first_checkpoint_commit
            ),
            "final_checkpoint_commit": dict(
                self.final_checkpoint_commit
            ),
            "first_checkpoint_payload": dict(
                self.first_checkpoint_payload
            ),
            "final_checkpoint_payload": dict(
                self.final_checkpoint_payload
            ),
            "first_final_facet_commit": dict(
                self.first_final_facet_commit
            ),
            "final_final_facet_commit": dict(
                self.final_final_facet_commit
            ),
            "worker_executions": [
                item.to_document() for item in self.worker_executions
            ],
            "matched_reset_worker_executions": [
                item.to_document()
                for item in self.matched_reset_worker_executions
            ],
            "ground_repair_authorization": (
                self.ground_repair_authorization.to_document()
            ),
            "accounting": dict(self.accounting),
            "campaign_snapshot_id": self.campaign_snapshot_id,
            "event_log": self.event_log.to_document(),
            "query_local_model_only": self.query_local_model_only,
            "promotion_authorized": self.promotion_authorized,
            "policy_switch_claimed": self.policy_switch_claimed,
            "learned_dynamics_claimed": self.learned_dynamics_claimed,
            "coordinate_invention_claimed": (
                self.coordinate_invention_claimed
            ),
            "sample_efficiency_claimed": self.sample_efficiency_claimed,
            "workload_economics_claimed": (
                self.workload_economics_claimed
            ),
            "official_execution_allowed": self.official_execution_allowed,
            "status": self.status,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def require_interleaved_durable_epoch_result_v1(
    result: InterleavedDurableEpochResultV1,
) -> InterleavedDurableEpochResultV1:
    if type(result) is not InterleavedDurableEpochResultV1:
        raise InterleavedDurableEpochInvariantViolation(
            "interleaved result rejects substitutions"
        )
    try:
        from acfqp._runtime_authority_v1 import require_runtime_authority_v1

        require_runtime_authority_v1(result, issuer=_RESULT_ISSUER)
    except Exception as error:
        raise InterleavedDurableEpochInvariantViolation(
            "interleaved result lacks live producer authority"
        ) from error
    result.__post_init__()
    return result


def _assert_worker_semantics(
    execution: InterleavedWorkerExecutionV1,
    *,
    certified: bool,
    builder_calls: int,
    selected_schedule: str,
) -> None:
    result = execution.occurrence_result
    certificate = result["certificate"]
    if (
        certificate["certified"] is not certified
        or result["query_facet_builder_calls"] != builder_calls
        or result["lower_identity_hits"] != 50 - builder_calls
        or result["fresh_root_builder_calls"] != 5
        or certificate["selected_schedule_code"] != selected_schedule
        or result["selected_root"]["schedule_code"] != selected_schedule
    ):
        raise InterleavedDurableEpochInvariantViolation(
            f"{execution.execution_label} registered result changed"
        )


@dataclass(frozen=True, slots=True)
class _CandidateCore:
    epoch: Any
    start_resolution_index: int
    pre_cache_state_id: str
    receipts: tuple[Any, ...]
    proposal: Any
    stage_maps_by_id: Mapping[str, Mapping[str, str]]
    selected_code: str
    selected_stage_ids: tuple[str, str]
    selected_plan: Any


def _run_candidate_core(
    *,
    runtime: Any,
    epoch: Any,
    observation_log: Any,
    semantics_profile: Any,
    observation_authority: Any,
    build: Any,
    rebase: Any,
    evidence_request: Any,
    evidence_bundle: Any,
    live: Any,
    temporal: Any,
    planner: Any,
    multistep: Any,
) -> _CandidateCore:
    model = build.model
    thresholds = rebase.rebased_thresholds
    _, domains = planner._planner_context(
        observation_log,
        semantics_profile,
        observation_authority,
        model,
        thresholds,
    )
    assignments = tuple(
        sorted(
            planner._stage_assignments(domains),
            key=lambda item: (
                live._semantic_stage_key(model, item),
                tuple(row.semantic_action_id for row in item),
            ),
        )
    )
    if len(assignments) != 2:
        raise InterleavedDurableEpochInvariantViolation(
            "candidate core no longer exposes two assignments"
        )
    stage_artifacts = tuple(
        temporal.H2TemporalStageAssignmentV1(
            index,
            tuple(
                (
                    row.cell_id,
                    row.semantic_action_id,
                    tuple(
                        int(value)
                        for value in next(
                            action.label_values
                            for action in model.semantic_actions
                            if action.semantic_action_id
                            == row.semantic_action_id
                        )
                    ),
                )
                for row in stage
            ),
        )
        for index, stage in enumerate(assignments)
    )
    stage_maps_by_id = {
        artifact.stage_assignment_id: {
            row.cell_id: row.semantic_action_id for row in stage
        }
        for artifact, stage in zip(stage_artifacts, assignments)
    }
    from acfqp.partial_sound_audit_v1 import (
        ContingentPlanStageV1,
        FrozenContingentAbstractPlanV1,
    )

    plans: list[tuple[str, tuple[str, str], Any]] = []
    for code, bits in zip(live.GRAY_CODES, live.GRAY_BITS):
        plan = FrozenContingentAbstractPlanV1(
            model.model_id,
            2,
            tuple(
                ContingentPlanStageV1(time_index, assignments[bit])
                for time_index, bit in enumerate(bits)
            ),
        )
        plans.append(
            (
                code,
                tuple(
                    stage_artifacts[bit].stage_assignment_id
                    for bit in bits
                ),
                plan,
            )
        )
    start = len(runtime.resolutions)
    pre_cache = live._cache_state_id(runtime.scope, runtime.cache)
    receipts = []
    for index, (code, stage_ids, plan) in enumerate(plans, start=1):
        request = live.LiveEpochProofRequestV1(
            epoch,
            index,
            temporal.H2TemporalProofRole.CANDIDATE_RANKING_AUDIT,
            code,
            model.model_id,
            thresholds.thresholds_id,
            plan,
            stage_ids,
            None,
        )
        receipts.append(
            live._run_request(
                runtime,
                epoch,
                request,
                build,
                rebase,
                evidence_request,
                evidence_bundle,
                stage_maps_by_id,
            )
        )
    current = tuple(runtime.resolutions[start:])
    if len(current) != 44:
        raise InterleavedDurableEpochInvariantViolation(
            "candidate core did not resolve four eleven-node requests"
        )
    plan_by_id = {plan.plan_id: plan for _, _, plan in plans}
    summaries = tuple(
        sorted(
            (
                planner._candidate_summary(
                    thresholds,
                    receipt.request.contingent_plan,
                    receipt.audit_result,
                )
                for receipt in receipts
            ),
            key=lambda item: item.contingent_plan_id,
        )
    )
    selection_mode, selected_summary, semantic_key = (
        multistep._select_with_semantic_tie_break(
            model, summaries, plan_by_id
        )
    )
    selected_plan = plan_by_id[selected_summary.contingent_plan_id]
    proposal = multistep.MultiStepPlanProposalV1(
        build.result_id,
        model.model_id,
        rebase.rebase_id,
        thresholds.thresholds_id,
        domains,
        2,
        4,
        summaries,
        selection_mode,
        selected_plan,
        "NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1",
        semantic_key,
        4,
    )
    selected_code, selected_stage_ids, _ = next(
        item for item in plans if item[2].plan_id == selected_plan.plan_id
    )
    return _CandidateCore(
        epoch,
        start,
        pre_cache,
        tuple(receipts),
        proposal,
        stage_maps_by_id,
        selected_code,
        selected_stage_ids,
        selected_plan,
    )


def _complete_selected_bridge(
    *,
    core: _CandidateCore,
    runtime: Any,
    build: Any,
    rebase: Any,
    evidence_request: Any,
    evidence_bundle: Any,
    live: Any,
    temporal: Any,
    multistep: Any,
) -> Any:
    request = live.LiveEpochProofRequestV1(
        core.epoch,
        5,
        temporal.H2TemporalProofRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE,
        core.selected_code,
        build.model.model_id,
        rebase.rebased_thresholds.thresholds_id,
        core.selected_plan,
        core.selected_stage_ids,
        core.proposal.result_id,
    )
    receipt = live._run_request(
        runtime,
        core.epoch,
        request,
        build,
        rebase,
        evidence_request,
        evidence_bundle,
        core.stage_maps_by_id,
    )
    selected_audit = multistep.MultiStepPlanAuditV1(
        build.result_id,
        build.model.model_id,
        evidence_request.request_id,
        evidence_bundle.bundle_id,
        rebase.rebase_id,
        core.proposal.result_id,
        core.selected_plan.plan_id,
        receipt.audit_result,
    )
    current = tuple(
        runtime.resolutions[core.start_resolution_index:]
    )
    if len(current) != 55:
        raise InterleavedDurableEpochInvariantViolation(
            "selected bridge did not close exactly one fresh root"
        )
    return live.LiveEpochProofExecutionV1(
        core.epoch,
        build.model.model_id,
        rebase.rebased_thresholds.thresholds_id,
        (*core.receipts, receipt),
        core.proposal,
        selected_audit,
        tuple(item.resolution_id for item in current),
        live._derive_work(current),
        core.pre_cache_state_id,
        live._cache_state_id(runtime.scope, runtime.cache),
    )


def _execute_lmb_h2_interleaved_durable_epoch_v1(
    observation_log: Any,
    semantics_profile: Any,
    observation_authority: Any,
    observed_synthesis_result: Any,
    thresholds: Any,
    base_plan_proposal: Any,
    failed_audit: Any,
    kernel: Any,
    store_root: Path,
) -> InterleavedDurableEpochResultV1:
    _invoke_canonical_source_pin_assert(allow_runtime_imports=True)
    import acfqp.h2_temporal_incremental_proof_dag_v1 as temporal
    import acfqp.live_query_local_epoch_invalidation_v1 as live
    import acfqp.multistep_query_refinement_v1 as multistep
    import acfqp.partial_model_planner_v1 as planner
    from acfqp._runtime_authority_v1 import bind_runtime_authority_v1
    from acfqp.domains.matching_buffer import LMBKernel
    from acfqp.observation_partial_rapm_v1 import (
        DeterministicObservationProfileV1,
        ObservationLogManifestV1,
        PreregisteredObservationAuthorityV1,
    )
    from acfqp.observed_typed_coordinate_synthesis_v1 import (
        ObservedTypedPartialRAPMResultV1,
    )
    from acfqp.partial_model_planner_v1 import (
        TypedPartialModelPlanProposalResultV2,
    )
    from acfqp.partial_sound_audit_v1 import (
        FrozenPartialAuditThresholdsV1,
        PartialAuditOutcome,
        TypedPartialSoundAuditResultV2,
    )

    if (
        type(observation_log) is not ObservationLogManifestV1
        or type(semantics_profile)
        is not DeterministicObservationProfileV1
        or type(observation_authority)
        is not PreregisteredObservationAuthorityV1
        or type(observed_synthesis_result)
        is not ObservedTypedPartialRAPMResultV1
        or type(thresholds) is not FrozenPartialAuditThresholdsV1
        or type(base_plan_proposal)
        is not TypedPartialModelPlanProposalResultV2
        or type(failed_audit) is not TypedPartialSoundAuditResultV2
        or type(kernel) is not LMBKernel
        or not isinstance(store_root, Path)
        or store_root.exists()
        or not store_root.parent.is_dir()
        or store_root.parent.is_symlink()
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "production runner rejects substituted/fabricated inputs"
        )
    base_input_model = observed_synthesis_result.partial_build_result.model
    base_input_document = base_input_model.to_document()
    thresholds_document = thresholds.to_document()
    return_bound_document = thresholds_document["return_bound_proof"]
    preregistration_initial_digest = _live_canonical_input_digest(
        {
            "initial_distribution": (
                thresholds_document["initial_state_distribution"]
            )
        }
    )
    preregistration_reward_digest = _live_canonical_input_digest(
        {"reward_weights": thresholds_document["reward_weights"]}
    )
    preregistered_input_authority_ids = {
        "observation_log_id": observation_log.log_id,
        "semantics_profile_id": semantics_profile.profile_id,
        "observation_authority_id": observation_authority.authority_id,
        "observed_synthesis_result_id": observed_synthesis_result.result_id,
        "source_thresholds_id": thresholds.thresholds_id,
        "base_plan_proposal_id": base_plan_proposal.result_id,
        "failed_audit_id": failed_audit.result_id,
        "kernel_digest": _digest_document(
            {
                "tile_types": list(kernel.tile_types),
                "blockers": [sorted(value) for value in kernel.blockers],
                "type_count": kernel.type_count,
                "capacity": kernel.capacity,
                "max_layers": kernel.max_layers,
            }
        ),
    }
    preregistered_structural_scope = (
        _structural_state_action_concretizer_scope(
            base_input_document,
            return_bound_document,
            semantics_profile.to_document(),
        )
    )
    preregistration = registered_interleaved_preregistration_v1(
        thresholds.thresholds_id,
        input_authority_ids=preregistered_input_authority_ids,
        goal_id=thresholds_document["goal_id"],
        return_bound_proof_id=return_bound_document["proof_id"],
        return_bound_formula_id=return_bound_document["formula_id"],
        return_upper=_parse_fraction(
            return_bound_document["return_upper"],
            "preregistered return upper",
        ),
        unrestricted_upper_formula_id=thresholds_document[
            "unrestricted_upper_formula_id"
        ],
        initial_distribution_digest=preregistration_initial_digest,
        reward_basis_digest=preregistration_reward_digest,
        base_model_id=base_input_model.model_id,
        structural_id=return_bound_document["structural_id"],
        environment_instance_id=return_bound_document[
            "environment_instance_id"
        ],
        coordinate_proposal_id=base_input_document[
            "coordinate_proposal_id"
        ],
        structural_state_action_concretizer_scope=(
            preregistered_structural_scope
        ),
        structural_state_action_concretizer_digest=(
            _structural_state_action_concretizer_digest(
                preregistered_structural_scope
            )
        ),
    )
    preregistration.__post_init__()
    store_root.mkdir()
    _write_exclusive(
        store_root / "preregistration.json",
        preregistration.to_document(),
    )
    event_recorder = _InterleavedEventRecorder(
        store_root / "events",
        preregistration.preregistration_id,
    )
    event_recorder.append(
        "PREREGISTRATION_FROZEN",
        preregistration.preregistration_id,
        ground=0,
        main_workers=0,
        reset_workers=0,
    )
    event_recorder.append(
        "QUERY_ELIGIBILITY_FROZEN",
        _query_eligibility_freeze_id(preregistration),
        ground=0,
        main_workers=0,
        reset_workers=0,
    )
    event_recorder.append(
        "AUTHENTIC_V0047_FIRST_EPOCH_STARTED",
        failed_audit.result_id,
        ground=0,
        main_workers=0,
        reset_workers=0,
    )

    (
        base_model,
        verified_plan,
        source_plan,
        verified_audit,
        frontier,
    ) = multistep._verified_h2_failure_chain(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        thresholds,
        base_plan_proposal,
        failed_audit,
    )
    request_one = multistep._round_one_request(
        base_model,
        thresholds,
        verified_plan,
        source_plan,
        verified_audit,
        frontier,
    )
    bundle_one = multistep._acquire(
        1, request_one, observation_log, None, kernel
    )
    event_recorder.append(
        "ROUND_ONE_FOUR_ROWS_COMPLETED",
        bundle_one.bundle_id,
        ground=4,
        main_workers=0,
        reset_workers=0,
    )
    boundary = multistep._expand_boundary(
        observation_log,
        observed_synthesis_result,
        request_one,
        bundle_one,
        kernel,
    )
    if (
        boundary.action_catalogue_query_count != 3
        or boundary.exact_transition_query_count != 0
        or boundary.ground_search_call_count != 0
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "registered three-catalogue boundary changed"
        )
    event_recorder.append(
        "BOUNDARY_THREE_CATALOGUES_COMPLETED",
        boundary.expansion_id,
        ground=4,
        main_workers=0,
        reset_workers=0,
    )
    model_one = multistep._assemble_overlay(
        observation_log,
        semantics_profile,
        observed_synthesis_result,
        thresholds,
        source_plan,
        verified_audit,
        request_one,
        bundle_one,
        (bundle_one,),
        boundary,
        base_model.model_id,
    )
    build_one = multistep._build_result(
        1,
        model_one,
        base_model.model_id,
        base_model.model_id,
        thresholds,
        source_plan,
        verified_audit,
        request_one,
        bundle_one,
        boundary,
    )
    rebase_one = multistep._rebase(build_one, thresholds)
    if (
        model_one.model_id != _EXPECTED_EPOCH_MODEL_IDS["FIRST"]
        or build_one.observed_ground_row_count != 11
        or build_one.missing_ground_row_count != 9
        or build_one.cumulative_exact_kernel_query_count != 4
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "registered first V0-047 epoch changed"
        )
    event_recorder.append(
        "FIRST_11_9_EPOCH_FROZEN",
        model_one.model_id,
        ground=4,
        main_workers=0,
        reset_workers=0,
    )
    runtime = live._Runtime(
        live.LiveEpochCacheScope.GLOBAL_CROSS_EPOCH_FACET_DAG,
        live.live_epoch_proof_semantics_v1(),
    )
    first_core = _run_candidate_core(
        runtime=runtime,
        epoch=live.LiveEpochName.FIRST,
        observation_log=observation_log,
        semantics_profile=semantics_profile,
        observation_authority=observation_authority,
        build=build_one,
        rebase=rebase_one,
        evidence_request=request_one,
        evidence_bundle=bundle_one,
        live=live,
        temporal=temporal,
        planner=planner,
        multistep=multistep,
    )
    first_core_work = live._derive_work(
        tuple(runtime.resolutions[first_core.start_resolution_index:])
    )
    if (
        first_core_work.computed != 34
        or first_core_work.reused != 10
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "first four-candidate core reuse profile changed"
        )
    first_checkpoint_body, first_active_ids = (
        _checkpoint_body_from_execution(
            epoch_name="FIRST",
            runtime=runtime,
            candidate_receipts=first_core.receipts,
            model=model_one,
            strict_thresholds=rebase_one.rebased_thresholds,
            preregistration=preregistration,
            active_resolution_offset=0,
            live=live,
            temporal=temporal,
        )
    )
    first_checkpoint = _write_checkpoint(
        store_root / "c1",
        first_checkpoint_body,
        generation=1,
        previous_commit_id=None,
        predecessor_store_root=None,
    )
    event_recorder.append(
        "C1_ROOT_FREE_CHECKPOINT_FROZEN",
        first_checkpoint["commit_id"],
        ground=4,
        main_workers=0,
        reset_workers=0,
    )
    first_facet_commit = _initialize_facet_store(
        store_root / "facets-c1", model_one.model_id, "FIRST"
    )
    by_code = {item.query_code: item for item in preregistration.queries}
    occurrences = preregistration.occurrences
    worker_executions: list[InterleavedWorkerExecutionV1] = []
    event_recorder.append(
        "OCCURRENCE_1_Q_R_FIRST_EPOCH_STARTED",
        occurrences[0].occurrence_id,
        ground=4,
        main_workers=0,
        reset_workers=0,
    )
    o1, first_facet_commit = _launch_interleaved_worker(
        store_root,
        "MAIN_GLOBAL_FACETS",
        "O1_FIRST",
        store_root / "c1",
        first_checkpoint["commit_id"],
        None,
        None,
        store_root / "facets-c1",
        first_facet_commit["commit_id"],
        by_code["Q_R"],
        occurrences[0],
    )
    worker_executions.append(o1)
    _assert_worker_semantics(
        o1,
        certified=True,
        builder_calls=8,
        selected_schedule="A0A0",
    )
    first_certificate = o1.occurrence_result["certificate"]
    if (
        first_certificate["reward_lower"]
        != _fraction_document(Fraction(0))
        or first_certificate["reward_upper"]
        != _fraction_document(Fraction(3))
        or first_certificate["failure_lower"]
        != _fraction_document(Fraction(0))
        or first_certificate["failure_upper"]
        != _fraction_document(Fraction(1))
        or first_certificate["normalized_regret"]
        != _fraction_document(Fraction(3, 4))
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "O1 relaxed bound/certificate changed"
        )
    event_recorder.append(
        "OCCURRENCE_1_Q_R_CERTIFIED_ZERO_QUERY_GROUND",
        o1.execution_id,
        ground=4,
        main_workers=1,
        reset_workers=0,
    )
    event_recorder.append(
        "OCCURRENCE_2_Q_S_FIRST_EPOCH_STARTED",
        occurrences[1].occurrence_id,
        ground=4,
        main_workers=1,
        reset_workers=0,
    )
    o2_failed, first_facet_commit = _launch_interleaved_worker(
        store_root,
        "MAIN_GLOBAL_FACETS",
        "O2_FAILED_FIRST",
        store_root / "c1",
        first_checkpoint["commit_id"],
        None,
        None,
        store_root / "facets-c1",
        first_facet_commit["commit_id"],
        by_code["Q_S"],
        occurrences[1],
    )
    worker_executions.append(o2_failed)
    first_selected_schedule = first_core.selected_code
    _assert_worker_semantics(
        o2_failed,
        certified=False,
        builder_calls=0,
        selected_schedule=first_selected_schedule,
    )
    custom_frontier = o2_failed.occurrence_result["certificate"][
        "failed_proof_frontier"
    ]
    if (
        type(custom_frontier) is not dict
        or custom_frontier.get("earliest_time_index") != 1
        or custom_frontier.get("remaining_horizon") != 1
        or custom_frontier.get("reason")
        != "UNRESOLVED_POLICY_PATH_DISTINCTION"
        or custom_frontier.get("local_recovery_authorized") is not False
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "O2 did not freeze the registered nonauthorizing failed frontier"
        )
    event_recorder.append(
        "OCCURRENCE_2_Q_S_SELECTED_FAILURE_FROZEN",
        o2_failed.execution_id,
        ground=4,
        main_workers=2,
        reset_workers=0,
    )
    # The historical typed selected-root bridge is intentionally constructed
    # only after the O2 model-only failure has been frozen.
    first_execution = _complete_selected_bridge(
        core=first_core,
        runtime=runtime,
        build=build_one,
        rebase=rebase_one,
        evidence_request=request_one,
        evidence_bundle=bundle_one,
        live=live,
        temporal=temporal,
        multistep=multistep,
    )
    first_selected = first_execution.selected_plan_audit.audit_result
    typed_frontier = first_selected.failed_proof_frontier
    if (
        first_execution.work.computed != 35
        or first_execution.work.reused != 20
        or first_selected.outcome
        is not PartialAuditOutcome.FAILED_PROOF_FRONTIER
        or typed_frontier is None
        or typed_frontier.earliest_time_index
        != custom_frontier["earliest_time_index"]
        or typed_frontier.remaining_horizon
        != custom_frontier["remaining_horizon"]
        or typed_frontier.reason.value != custom_frontier["reason"]
        or typed_frontier.value_obligation_failed
        != custom_frontier["value_obligation_failed"]
        or typed_frontier.risk_obligation_failed
        != custom_frontier["risk_obligation_failed"]
        or typed_frontier.external_coverage_failed
        != custom_frontier["external_coverage_failed"]
        or tuple(
            (
                item.time_index,
                item.remaining_horizon,
                item.state_id,
                item.cell_id,
                item.semantic_action_id,
                list(item.support_ground_row_ids),
                list(item.observed_ground_row_ids),
                list(item.missing_ground_row_ids),
            )
            for item in typed_frontier.obligations
        )
        != tuple(
            (
                item["time_index"],
                item["remaining_horizon"],
                item["state_id"],
                item["cell_id"],
                item["semantic_action_id"],
                item["support_ground_row_ids"],
                item["observed_ground_row_ids"],
                item["missing_ground_row_ids"],
            )
            for item in custom_frontier["obligations"]
        )
        or o2_failed.occurrence_result["certificate"]["reward_lower"]
        != _fraction_document(first_selected.robust_bounds.policy_reward_lower)
        or o2_failed.occurrence_result["certificate"]["reward_upper"]
        != _fraction_document(first_selected.robust_bounds.policy_reward_upper)
        or o2_failed.occurrence_result["certificate"]["failure_upper"]
        != _fraction_document(first_selected.robust_bounds.policy_failure_upper)
        or o2_failed.occurrence_result["certificate"]["normalized_regret"]
        != _fraction_document(
            first_selected.robust_bounds.normalized_distribution_regret
        )
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "after-O2 typed bridge differs from the worker-derived frontier"
        )
    request_two = multistep._round_two_request(
        build_one,
        rebase_one,
        first_execution.plan_proposal,
        first_execution.selected_plan_audit,
        boundary,
    )
    event_recorder.append(
        "ROUND_TWO_REQUEST_DERIVED_FROM_Q_S_FAILURE",
        request_two.request_id,
        ground=4,
        main_workers=2,
        reset_workers=0,
    )
    authorization, semantic_authority = (
        _mint_ground_repair_authorization(
            preregistration=preregistration,
            occurrence=occurrences[1],
            first_checkpoint_commit=first_checkpoint,
            failed_result=o2_failed.occurrence_result,
            typed_audit=first_execution.selected_plan_audit,
            request=request_two,
        )
    )
    _write_exclusive(
        store_root / "ground-repair-authorization.json",
        authorization.to_document(),
    )
    event_recorder.append(
        "ROUND_TWO_NINE_ROWS_AUTHORIZED",
        authorization.authorization_id,
        ground=4,
        main_workers=2,
        reset_workers=0,
    )
    gate_nonce = object()
    ground_gate = _SingleUseGroundRepairGate(authorization, gate_nonce)
    bundle_two = ground_gate.acquire(
        multistep=multistep,
        request=request_two,
        observation_log=observation_log,
        boundary=boundary,
        kernel=kernel,
        nonce=gate_nonce,
    )
    _validate_round_two_bundle_semantics(
        request_two, bundle_two, authorization
    )
    event_recorder.append(
        "ROUND_TWO_NINE_ROWS_COMPLETED",
        bundle_two.bundle_id,
        ground=13,
        main_workers=2,
        reset_workers=0,
    )
    model_two = multistep._assemble_overlay(
        observation_log,
        semantics_profile,
        observed_synthesis_result,
        thresholds,
        source_plan,
        verified_audit,
        request_two,
        bundle_two,
        (bundle_one, bundle_two),
        boundary,
        model_one.model_id,
    )
    build_two = multistep._build_result(
        2,
        model_two,
        base_model.model_id,
        model_one.model_id,
        thresholds,
        source_plan,
        verified_audit,
        request_two,
        bundle_two,
        boundary,
    )
    rebase_two = multistep._rebase(build_two, thresholds)
    if (
        model_two.model_id != _EXPECTED_EPOCH_MODEL_IDS["FINAL"]
        or build_two.observed_ground_row_count != 20
        or build_two.missing_ground_row_count != 0
        or build_two.cumulative_exact_kernel_query_count != 13
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "registered final V0-047 epoch changed"
        )
    event_recorder.append(
        "FINAL_20_0_EPOCH_FROZEN",
        model_two.model_id,
        ground=13,
        main_workers=2,
        reset_workers=0,
    )

    class _DeltaSource:
        first_overlay_build = build_one
        final_overlay_build = build_two
        round_two_request = request_two
        round_two_bundle = bundle_two

    delta = live._derive_delta(_DeltaSource())
    invalidation = live.LiveEpochInvalidationManifestV1(
        delta.delta_id,
        delta.direct_changed_slots,
        delta.affected_descendant_slots,
        delta.reusable_slots,
    )
    final_core = _run_candidate_core(
        runtime=runtime,
        epoch=live.LiveEpochName.FINAL,
        observation_log=observation_log,
        semantics_profile=semantics_profile,
        observation_authority=observation_authority,
        build=build_two,
        rebase=rebase_two,
        evidence_request=request_two,
        evidence_bundle=bundle_two,
        live=live,
        temporal=temporal,
        planner=planner,
        multistep=multistep,
    )
    final_core_work = live._derive_work(
        tuple(runtime.resolutions[final_core.start_resolution_index:])
    )
    if (
        final_core_work.computed != 32
        or final_core_work.reused != 12
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "final four-candidate core reuse profile changed"
        )
    final_checkpoint_body, final_active_ids = (
        _checkpoint_body_from_execution(
            epoch_name="FINAL",
            runtime=runtime,
            candidate_receipts=final_core.receipts,
            model=model_two,
            strict_thresholds=rebase_two.rebased_thresholds,
            preregistration=preregistration,
            active_resolution_offset=final_core.start_resolution_index,
            live=live,
            temporal=temporal,
        )
    )
    reused_distinct_ids = first_active_ids & final_active_ids
    if (
        len(first_active_ids) != 30
        or len(final_active_ids) != 30
        or len(reused_distinct_ids) != 2
        or {
            runtime.entries[value].key.slot.value
            for value in reused_distinct_ids
        }
        != {"C0"}
        or len(final_checkpoint_body["union_lower_entries"]) != 58
        or len(final_checkpoint_body["inactive_lower_entry_ids"]) != 28
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "exact 28-recompute/2-C0-reuse epoch transition changed"
        )
    event_recorder.append(
        "DELTA_AND_28_2_INVALIDATION_FROZEN",
        invalidation.manifest_id,
        ground=13,
        main_workers=2,
        reset_workers=0,
    )
    final_checkpoint = _write_checkpoint(
        store_root / "c2",
        final_checkpoint_body,
        generation=2,
        previous_commit_id=first_checkpoint["commit_id"],
        predecessor_store_root=store_root / "c1",
    )
    event_recorder.append(
        "C2_58_UNION_30_ACTIVE_FROZEN",
        final_checkpoint["commit_id"],
        ground=13,
        main_workers=2,
        reset_workers=0,
    )
    final_facet_commit = _initialize_facet_store(
        store_root / "facets-c2", model_two.model_id, "FINAL"
    )
    event_recorder.append(
        "OCCURRENCE_2_Q_S_FINAL_REPLAN_STARTED",
        occurrences[1].occurrence_id,
        ground=13,
        main_workers=2,
        reset_workers=0,
    )
    o2_recertified, final_facet_commit = _launch_interleaved_worker(
        store_root,
        "MAIN_GLOBAL_FACETS",
        "O2_RECERTIFIED_FINAL",
        store_root / "c2",
        final_checkpoint["commit_id"],
        first_checkpoint["commit_id"],
        store_root / "c1",
        store_root / "facets-c2",
        final_facet_commit["commit_id"],
        by_code["Q_S"],
        occurrences[1],
    )
    worker_executions.append(o2_recertified)
    final_selected_schedule = final_core.selected_code
    _assert_worker_semantics(
        o2_recertified,
        certified=True,
        builder_calls=0,
        selected_schedule=final_selected_schedule,
    )
    if (
        o2_recertified.occurrence_result["certificate"][
            "failed_proof_frontier"
        ]
        != {
            "kind": "NOT_APPLICABLE",
            "reason": "SELECTED_PLAN_CERTIFIED",
        }
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "O2 final worker retained a failed frontier"
        )
    # As in FIRST, the typed selected root is completed only after the
    # occurrence worker has independently frozen its model-only certificate.
    final_execution = _complete_selected_bridge(
        core=final_core,
        runtime=runtime,
        build=build_two,
        rebase=rebase_two,
        evidence_request=request_two,
        evidence_bundle=bundle_two,
        live=live,
        temporal=temporal,
        multistep=multistep,
    )
    final_selected = final_execution.selected_plan_audit.audit_result
    if (
        final_execution.work.computed != 33
        or final_execution.work.reused != 22
        or final_selected.outcome
        is not PartialAuditOutcome.CERTIFIED_FIXED_PLAN
        or o2_recertified.occurrence_result["certificate"][
            "reward_lower"
        ]
        != _fraction_document(final_selected.robust_bounds.policy_reward_lower)
        or o2_recertified.occurrence_result["certificate"][
            "failure_upper"
        ]
        != _fraction_document(final_selected.robust_bounds.policy_failure_upper)
        or o2_recertified.occurrence_result["certificate"][
            "normalized_regret"
        ]
        != _fraction_document(
            final_selected.robust_bounds.normalized_distribution_regret
        )
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "after-O2 final typed bridge differs from worker certificate"
        )
    event_recorder.append(
        "OCCURRENCE_2_Q_S_CERTIFIED",
        o2_recertified.execution_id,
        ground=13,
        main_workers=3,
        reset_workers=0,
    )
    for label, occurrence in (
        ("O3_FINAL", occurrences[2]),
        ("O4_FINAL", occurrences[3]),
        ("O5_FINAL", occurrences[4]),
    ):
        query = by_code[occurrence.query.query_code]
        worker, final_facet_commit = _launch_interleaved_worker(
            store_root,
            "MAIN_GLOBAL_FACETS",
            label,
            store_root / "c2",
            final_checkpoint["commit_id"],
            first_checkpoint["commit_id"],
            store_root / "c1",
            store_root / "facets-c2",
            final_facet_commit["commit_id"],
            query,
            occurrence,
        )
        worker_executions.append(worker)
        _assert_worker_semantics(
            worker,
            certified=True,
            builder_calls=8 if label == "O3_FINAL" else 0,
            selected_schedule=final_selected_schedule,
        )
        event_recorder.append(
            {
                "O3_FINAL": "OCCURRENCE_3_Q_R_FINAL_CERTIFIED",
                "O4_FINAL": "OCCURRENCE_4_Q_S_FINAL_CERTIFIED",
                "O5_FINAL": "OCCURRENCE_5_Q_R_FINAL_CERTIFIED",
            }[label],
            worker.execution_id,
            ground=13,
            main_workers=len(worker_executions),
            reset_workers=0,
        )
    matched_reset_worker_executions: list[
        InterleavedWorkerExecutionV1
    ] = []
    reset_specs = (
        (
            "O1_FIRST",
            store_root / "c1",
            first_checkpoint,
            None,
            model_one,
            "FIRST",
            by_code["Q_R"],
            occurrences[0],
            True,
            8,
        ),
        (
            "O2_FAILED_FIRST",
            store_root / "c1",
            first_checkpoint,
            None,
            model_one,
            "FIRST",
            by_code["Q_S"],
            occurrences[1],
            False,
            0,
        ),
        (
            "O2_RECERTIFIED_FINAL",
            store_root / "c2",
            final_checkpoint,
            first_checkpoint["commit_id"],
            model_two,
            "FINAL",
            by_code["Q_S"],
            occurrences[1],
            True,
            0,
        ),
        (
            "O3_FINAL",
            store_root / "c2",
            final_checkpoint,
            first_checkpoint["commit_id"],
            model_two,
            "FINAL",
            by_code["Q_R"],
            occurrences[2],
            True,
            8,
        ),
        (
            "O4_FINAL",
            store_root / "c2",
            final_checkpoint,
            first_checkpoint["commit_id"],
            model_two,
            "FINAL",
            by_code["Q_S"],
            occurrences[3],
            True,
            0,
        ),
        (
            "O5_FINAL",
            store_root / "c2",
            final_checkpoint,
            first_checkpoint["commit_id"],
            model_two,
            "FINAL",
            by_code["Q_R"],
            occurrences[4],
            True,
            8,
        ),
    )
    for (
        label,
        checkpoint_root,
        checkpoint_commit,
        previous_checkpoint_id,
        reset_model,
        reset_epoch,
        query,
        occurrence,
        certified,
        builder_calls,
    ) in reset_specs:
        reset_facet_root = (
            store_root
            / "matched-reset-facets"
            / label.lower()
        )
        reset_genesis = _initialize_facet_store(
            reset_facet_root,
            reset_model.model_id,
            reset_epoch,
        )
        reset_worker, _ = _launch_interleaved_worker(
            store_root,
            "MATCHED_FACET_RESET",
            label,
            checkpoint_root,
            checkpoint_commit["commit_id"],
            previous_checkpoint_id,
            (
                None
                if previous_checkpoint_id is None
                else store_root / "c1"
            ),
            reset_facet_root,
            reset_genesis["commit_id"],
            query,
            occurrence,
        )
        matched_reset_worker_executions.append(reset_worker)
        _assert_worker_semantics(
            reset_worker,
            certified=certified,
            builder_calls=builder_calls,
            selected_schedule=(
                first_selected_schedule
                if reset_epoch == "FIRST"
                else final_selected_schedule
            ),
        )
    if (
        first_selected_schedule != "A0A0"
        or final_selected_schedule != "A0A0"
        or any(
            item.occurrence_result["certificate"][
                "selected_schedule_code"
            ]
            != "A0A0"
            for item in worker_executions
        )
        or any(
            item.occurrence_result["certificate"][
                "selected_schedule_code"
            ]
            != "A0A0"
            for item in matched_reset_worker_executions
        )
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "registered V0-057 semantic schedule changed"
        )
    round_two_request_document = {
        **request_two.to_document(),
        "requested_distinct_ground_row_count": 9,
    }
    source_chain_body = {
        "schema": "acfqp.interleaved_live_source_chain.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "input_authority_ids": dict(
            preregistered_input_authority_ids
        ),
        "base_failure_frontier_id": frontier.frontier_id,
        "round_one_request": request_one.to_document(),
        "round_one_bundle": bundle_one.to_document(),
        "boundary_expansion": boundary.to_document(),
        "first_overlay_build": build_one.to_document(),
        "first_threshold_rebase": rebase_one.to_document(),
        "first_strict_execution": first_execution.to_document(),
        "round_two_request": round_two_request_document,
        "round_two_bundle": bundle_two.to_document(),
        "final_overlay_build": build_two.to_document(),
        "final_threshold_rebase": rebase_two.to_document(),
        "epoch_delta": delta.to_document(),
        "invalidation_manifest": invalidation.to_document(),
        "final_strict_execution": final_execution.to_document(),
    }
    source_chain = {
        **source_chain_body,
        "source_chain_id": _content_id("source_chain", source_chain_body),
    }
    _write_exclusive(
        store_root / "source-chain.json",
        source_chain,
    )
    main_builder_vector = [
        item.occurrence_result["query_facet_builder_calls"]
        for item in worker_executions
    ]
    main_hit_vector = [
        item.occurrence_result["lower_identity_hits"]
        for item in worker_executions
    ]
    reset_builder_vector = [
        item.occurrence_result["query_facet_builder_calls"]
        for item in matched_reset_worker_executions
    ]
    reset_hit_vector = [
        item.occurrence_result["lower_identity_hits"]
        for item in matched_reset_worker_executions
    ]
    main_logical_indices = (0, 2, 3, 4, 5)
    reset_logical_indices = (0, 2, 3, 4, 5)
    main_worker_input_bytes = [
        item.worker_input_bytes for item in worker_executions
    ]
    main_worker_output_bytes = [
        item.worker_output_bytes for item in worker_executions
    ]
    reset_worker_input_bytes = [
        item.worker_input_bytes
        for item in matched_reset_worker_executions
    ]
    reset_worker_output_bytes = [
        item.worker_output_bytes
        for item in matched_reset_worker_executions
    ]
    checkpoint_artifact_bytes = (
        _directory_regular_bytes(store_root / "c1")
        + _directory_regular_bytes(store_root / "c2")
    )
    main_facet_artifact_bytes = (
        _directory_regular_bytes(store_root / "facets-c1")
        + _directory_regular_bytes(store_root / "facets-c2")
    )
    reset_facet_artifact_bytes = sum(
        _directory_regular_bytes(
            store_root / "matched-reset-facets" / label.lower()
        )
        for label, *_ in reset_specs
    )
    accounting_body = {
        "schema": "acfqp.interleaved_epoch_accounting.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "logical_occurrence_count": 5,
        "fresh_worker_process_count": 12,
        "main_fresh_worker_process_count": 6,
        "reset_fresh_worker_process_count": 6,
        "main_host_worker_result_reconstruction_comparison_count": sum(
            item.host_result_reconstruction_comparison_count
            for item in worker_executions
        ),
        "reset_host_worker_result_reconstruction_comparison_count": sum(
            item.host_result_reconstruction_comparison_count
            for item in matched_reset_worker_executions
        ),
        "main_host_worker_semantic_assertion_count": sum(
            item.host_semantic_assertion_count
            for item in worker_executions
        ),
        "reset_host_worker_semantic_assertion_count": sum(
            item.host_semantic_assertion_count
            for item in matched_reset_worker_executions
        ),
        "host_checkpoint_store_load_count": 23,
        "host_cross_store_lineage_check_count": 9,
        "host_facet_store_load_count": 36,
        "host_worker_result_reconstruction_comparison_count": 12,
        "host_input_snapshot_hash_count": 64,
        "host_immutability_comparison_count": 32,
        "host_worker_semantic_assertion_count": 12,
        "host_verification_counter_scope": (
            "OPERATIONAL_PRE_ACCOUNTING_REGISTERED_CHECKS_ONLY"
        ),
        "worker_ground_transition_calls": 0,
        "round_one_ground_transition_calls": 4,
        "certificate_triggered_ground_transition_calls": 9,
        "source_ground_transition_calls": 13,
        "boundary_catalogue_calls": 3,
        "first_union_lower_count": 30,
        "first_active_lower_count": 30,
        "final_union_lower_count": 58,
        "final_active_lower_count": 30,
        "final_inactive_lower_count": 28,
        "epoch_lower_recomputations": 28,
        "epoch_lower_lookup_reuses": 22,
        "epoch_distinct_entry_reuses": 2,
        "epoch_reused_slots": ["C0"],
        "main_query_facet_builder_calls": main_builder_vector,
        "main_lower_identity_hits": main_hit_vector,
        "reset_query_facet_builder_calls": reset_builder_vector,
        "reset_lower_identity_hits": reset_hit_vector,
        "main_native_query_facet_builder_calls": sum(
            main_builder_vector
        ),
        "main_native_lower_identity_hits": sum(main_hit_vector),
        "reset_native_query_facet_builder_calls": sum(
            reset_builder_vector
        ),
        "reset_native_lower_identity_hits": sum(reset_hit_vector),
        "campaign_native_query_facet_builder_calls": (
            sum(main_builder_vector) + sum(reset_builder_vector)
        ),
        "campaign_native_lower_identity_hits": (
            sum(main_hit_vector) + sum(reset_hit_vector)
        ),
        "main_native_fresh_root_builder_calls": sum(
            item.occurrence_result["fresh_root_builder_calls"]
            for item in worker_executions
        ),
        "reset_native_fresh_root_builder_calls": sum(
            item.occurrence_result["fresh_root_builder_calls"]
            for item in matched_reset_worker_executions
        ),
        "campaign_native_fresh_root_builder_calls": sum(
            item.occurrence_result["fresh_root_builder_calls"]
            for item in (
                *worker_executions,
                *matched_reset_worker_executions,
            )
        ),
        "main_logical_query_facet_builder_calls": sum(
            main_builder_vector[index] for index in main_logical_indices
        ),
        "main_logical_lower_identity_hits": sum(
            main_hit_vector[index] for index in main_logical_indices
        ),
        "reset_logical_query_facet_builder_calls": sum(
            reset_builder_vector[index] for index in reset_logical_indices
        ),
        "reset_logical_lower_identity_hits": sum(
            reset_hit_vector[index] for index in reset_logical_indices
        ),
        "main_recertification_query_facet_builder_calls": (
            main_builder_vector[2]
        ),
        "main_recertification_lower_identity_hits": main_hit_vector[2],
        "reset_recertification_query_facet_builder_calls": (
            reset_builder_vector[2]
        ),
        "reset_recertification_lower_identity_hits": reset_hit_vector[2],
        "main_worker_input_bytes": main_worker_input_bytes,
        "main_worker_output_bytes": main_worker_output_bytes,
        "reset_worker_input_bytes": reset_worker_input_bytes,
        "reset_worker_output_bytes": reset_worker_output_bytes,
        "campaign_worker_input_bytes": (
            sum(main_worker_input_bytes) + sum(reset_worker_input_bytes)
        ),
        "campaign_worker_output_bytes": (
            sum(main_worker_output_bytes) + sum(reset_worker_output_bytes)
        ),
        "worker_input_byte_scope": "QUERY_AND_OCCURRENCE_FILES_ONLY",
        "worker_output_byte_scope": "RESULT_FILE_ONLY",
        "checkpoint_artifact_bytes": checkpoint_artifact_bytes,
        "main_facet_artifact_bytes": main_facet_artifact_bytes,
        "reset_facet_artifact_bytes": reset_facet_artifact_bytes,
        "campaign_checkpoint_and_facet_artifact_bytes": (
            checkpoint_artifact_bytes
            + main_facet_artifact_bytes
            + reset_facet_artifact_bytes
        ),
        "artifact_byte_semantics": "SERIALIZED_FOOTPRINT_NOT_IO_TRAFFIC",
        "main_selected_schedule_codes": [
            item.occurrence_result["certificate"][
                "selected_schedule_code"
            ]
            for item in worker_executions
        ],
        "reset_selected_schedule_codes": [
            item.occurrence_result["certificate"][
                "selected_schedule_code"
            ]
            for item in matched_reset_worker_executions
        ],
        "model_only_after_final_repair": True,
        "query_local_nonpromotable": True,
        "acquisition_query_neutral": False,
        "counter_registry_complete": False,
        "official_workvector_claimed": False,
    }
    accounting = {
        **accounting_body,
        "accounting_id": _content_id("accounting", accounting_body),
    }
    _write_exclusive(
        store_root / "accounting.json",
        accounting,
    )
    event_recorder.append(
        "CAMPAIGN_RESULT_FROZEN",
        accounting["accounting_id"],
        ground=13,
        main_workers=6,
        reset_workers=6,
    )
    event_log = event_recorder.freeze()
    campaign_snapshot = _directory_snapshot_id(
        store_root, "V0057_CAMPAIGN"
    )
    result = InterleavedDurableEpochResultV1(
        preregistration,
        source_chain,
        first_checkpoint,
        final_checkpoint,
        {
            **first_checkpoint_body,
            "payload_id": first_checkpoint["payload_id"],
        },
        {
            **final_checkpoint_body,
            "payload_id": final_checkpoint["payload_id"],
        },
        first_facet_commit,
        final_facet_commit,
        tuple(worker_executions),
        tuple(matched_reset_worker_executions),
        authorization,
        accounting,
        campaign_snapshot,
        event_log,
    )
    result.__post_init__()
    return bind_runtime_authority_v1(result, issuer=_RESULT_ISSUER)


def run_lmb_h2_interleaved_durable_epoch_v1(
    observation_log: Any,
    semantics_profile: Any,
    observation_authority: Any,
    observed_synthesis_result: Any,
    thresholds: Any,
    base_plan_proposal: Any,
    failed_audit: Any,
    kernel: Any,
    store_root: Path,
) -> InterleavedDurableEpochResultV1:
    """Run the preregistered five-occurrence V0-057 live interleaving."""

    return _execute_lmb_h2_interleaved_durable_epoch_v1(
        observation_log,
        semantics_profile,
        observation_authority,
        observed_synthesis_result,
        thresholds,
        base_plan_proposal,
        failed_audit,
        kernel,
        store_root,
    )


@dataclass(frozen=True, slots=True)
class InterleavedDurableEpochVerificationReportV1:
    claimed_result_id: str
    replayed_result_id: str
    original_campaign_snapshot_id: str
    exact_document_match: bool
    evaluation_ground_transition_calls: int = 13
    evaluation_worker_process_launches: int = 12
    evaluation_host_checkpoint_store_load_count: int = 23
    evaluation_host_cross_store_lineage_check_count: int = 9
    evaluation_host_facet_store_load_count: int = 36
    evaluation_host_worker_result_reconstruction_comparison_count: int = 12
    evaluation_host_input_snapshot_hash_count: int = 64
    evaluation_host_immutability_comparison_count: int = 32
    evaluation_host_worker_semantic_assertion_count: int = 12
    claimed_result_semantic_validation_count: int = 1
    claimed_campaign_snapshot_hash_count: int = 2
    replayed_document_comparison_count: int = 1
    same_implementation_full_replay: bool = True
    independent_algorithm: bool = False
    evaluation_lane_only: bool = True
    included_in_operational_work: bool = False

    def __post_init__(self) -> None:
        for value in (
            self.claimed_result_id,
            self.replayed_result_id,
            self.original_campaign_snapshot_id,
        ):
            _cid(value, "interleaved verification identity")
        if (
            self.claimed_result_id != self.replayed_result_id
            or self.exact_document_match is not True
            or self.evaluation_ground_transition_calls != 13
            or self.evaluation_worker_process_launches != 12
            or self.evaluation_host_checkpoint_store_load_count != 23
            or self.evaluation_host_cross_store_lineage_check_count != 9
            or self.evaluation_host_facet_store_load_count != 36
            or self.evaluation_host_worker_result_reconstruction_comparison_count
            != 12
            or self.evaluation_host_input_snapshot_hash_count != 64
            or self.evaluation_host_immutability_comparison_count != 32
            or self.evaluation_host_worker_semantic_assertion_count != 12
            or self.claimed_result_semantic_validation_count != 1
            or self.claimed_campaign_snapshot_hash_count != 2
            or self.replayed_document_comparison_count != 1
            or self.same_implementation_full_replay is not True
            or self.independent_algorithm is not False
            or self.evaluation_lane_only is not True
            or self.included_in_operational_work is not False
        ):
            raise InterleavedDurableEpochInvariantViolation(
                "interleaved verification report changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.interleaved_durable_epoch_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "claimed_result_id": self.claimed_result_id,
            "replayed_result_id": self.replayed_result_id,
            "original_campaign_snapshot_id": (
                self.original_campaign_snapshot_id
            ),
            "exact_document_match": self.exact_document_match,
            "evaluation_ground_transition_calls": (
                self.evaluation_ground_transition_calls
            ),
            "evaluation_worker_process_launches": (
                self.evaluation_worker_process_launches
            ),
            "evaluation_host_checkpoint_store_load_count": (
                self.evaluation_host_checkpoint_store_load_count
            ),
            "evaluation_host_cross_store_lineage_check_count": (
                self.evaluation_host_cross_store_lineage_check_count
            ),
            "evaluation_host_facet_store_load_count": (
                self.evaluation_host_facet_store_load_count
            ),
            "evaluation_host_worker_result_reconstruction_comparison_count": (
                self.evaluation_host_worker_result_reconstruction_comparison_count
            ),
            "evaluation_host_input_snapshot_hash_count": (
                self.evaluation_host_input_snapshot_hash_count
            ),
            "evaluation_host_immutability_comparison_count": (
                self.evaluation_host_immutability_comparison_count
            ),
            "evaluation_host_worker_semantic_assertion_count": (
                self.evaluation_host_worker_semantic_assertion_count
            ),
            "claimed_result_semantic_validation_count": (
                self.claimed_result_semantic_validation_count
            ),
            "claimed_campaign_snapshot_hash_count": (
                self.claimed_campaign_snapshot_hash_count
            ),
            "replayed_document_comparison_count": (
                self.replayed_document_comparison_count
            ),
            "same_implementation_full_replay": (
                self.same_implementation_full_replay
            ),
            "independent_algorithm": self.independent_algorithm,
            "evaluation_lane_only": self.evaluation_lane_only,
            "included_in_operational_work": (
                self.included_in_operational_work
            ),
        }

    @property
    def report_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "report_id": self.report_id}


def verify_lmb_h2_interleaved_durable_epoch_v1(
    observation_log: Any,
    semantics_profile: Any,
    observation_authority: Any,
    observed_synthesis_result: Any,
    thresholds: Any,
    base_plan_proposal: Any,
    failed_audit: Any,
    kernel: Any,
    store_root: Path,
    claimed_result: InterleavedDurableEpochResultV1,
) -> InterleavedDurableEpochVerificationReportV1:
    """Verify original bytes and perform a complete evaluation-lane replay."""

    _invoke_canonical_source_pin_assert(allow_runtime_imports=True)
    require_interleaved_durable_epoch_result_v1(claimed_result)
    original_snapshot = _directory_snapshot_id(
        store_root, "V0057_CAMPAIGN"
    )
    if original_snapshot != claimed_result.campaign_snapshot_id:
        raise InterleavedDurableEpochInvariantViolation(
            "claimed result differs from original campaign bytes"
        )
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v0057-verifier-"
    ) as directory:
        replayed = _execute_lmb_h2_interleaved_durable_epoch_v1(
            observation_log,
            semantics_profile,
            observation_authority,
            observed_synthesis_result,
            thresholds,
            base_plan_proposal,
            failed_audit,
            kernel,
            Path(directory) / "campaign",
        )
    if (
        _directory_snapshot_id(store_root, "V0057_CAMPAIGN")
        != original_snapshot
    ):
        raise InterleavedDurableEpochInvariantViolation(
            "original campaign changed during evaluation replay"
        )
    exact = replayed.to_document() == claimed_result.to_document()
    return InterleavedDurableEpochVerificationReportV1(
        claimed_result.result_id,
        replayed.result_id,
        original_snapshot,
        exact,
        evaluation_ground_transition_calls=replayed.accounting[
            "source_ground_transition_calls"
        ],
        evaluation_worker_process_launches=replayed.accounting[
            "fresh_worker_process_count"
        ],
        evaluation_host_checkpoint_store_load_count=replayed.accounting[
            "host_checkpoint_store_load_count"
        ],
        evaluation_host_cross_store_lineage_check_count=replayed.accounting[
            "host_cross_store_lineage_check_count"
        ],
        evaluation_host_facet_store_load_count=replayed.accounting[
            "host_facet_store_load_count"
        ],
        evaluation_host_worker_result_reconstruction_comparison_count=(
            replayed.accounting[
                "host_worker_result_reconstruction_comparison_count"
            ]
        ),
        evaluation_host_input_snapshot_hash_count=replayed.accounting[
            "host_input_snapshot_hash_count"
        ],
        evaluation_host_immutability_comparison_count=replayed.accounting[
            "host_immutability_comparison_count"
        ],
        evaluation_host_worker_semantic_assertion_count=replayed.accounting[
            "host_worker_semantic_assertion_count"
        ],
        claimed_result_semantic_validation_count=1,
        claimed_campaign_snapshot_hash_count=2,
        replayed_document_comparison_count=1,
    )


__all__ = [
    "CONTRACT_VERSION",
    "PROFILE_KEY",
    "SUCCESS_STATUS",
    "EpochThresholdFamilyEligibilityV1",
    "InterleavedEventLogV1",
    "InterleavedEventV1",
    "GroundRepairAuthorizationV1",
    "EXPECTED_EVENT_ORDER",
    "InterleavedDurableEpochInvariantViolation",
    "InterleavedDurableEpochResultV1",
    "InterleavedDurableEpochVerificationReportV1",
    "InterleavedOccurrenceV1",
    "InterleavedThresholdQueryV1",
    "InterleavedWorkerExecutionV1",
    "InterleavedWorkloadPreregistrationV1",
    "registered_interleaved_preregistration_v1",
    "registered_interleaved_queries_v1",
    "require_interleaved_durable_epoch_result_v1",
    "run_lmb_h2_interleaved_durable_epoch_v1",
    "verify_lmb_h2_interleaved_durable_epoch_v1",
]


if __name__ == "__main__":  # pragma: no cover - exercised via host process
    if len(sys.argv) >= 2 and sys.argv[1] == "--worker":
        raise SystemExit(_worker_main(sys.argv[2:]))
    raise SystemExit(2)
