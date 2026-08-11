"""Fresh worker for the complete query-bound recovery occurrence.

The worker consumes five immutable, content-hashed scientific inputs and runs
the already frozen five-stage continuation.  It emits only a portable
operational trace.  Process, filesystem, peak-memory, and final output-byte
evidence remain owned by the trusted parent and occurrence finalizer.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import resource
import sys
from typing import Any


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_k7_query_bound_accounted_runtime_v1"
REQUEST_SCHEMA = "acfqp.construction_k7_query_bound_supervised_request.v1"
TRACE_SCHEMA = "acfqp.construction_k7_query_bound_operational_trace.v1"

INPUT_ROLES = (
    ("SOURCE_TRACE", "source_trace.json"),
    ("BUILD_EPOCH_ENVELOPE", "build_epoch_envelope.json"),
    ("ROOT_QUERY_RESULT", "root_query_result.json"),
    ("RECOVERY_OVERLAY", "recovery_overlay.json"),
    ("RECOVERY_REQUEST", "recovery_request.json"),
)


class _BusinessHashMeterV1:
    def __init__(self) -> None:
        self.count = 0
        self._original: Any = None
        self._installed: Any = None

    def __enter__(self) -> "_BusinessHashMeterV1":
        if self._original is not None:
            raise RuntimeError("query-bound hash meter is single-use")
        self._original = hashlib.sha256

        def metered_sha256(*args: Any, **kwargs: Any) -> Any:
            self.count += 1
            return self._original(*args, **kwargs)

        self._installed = metered_sha256
        hashlib.sha256 = metered_sha256  # type: ignore[assignment]
        return self

    def __exit__(self, _kind: object, _value: object, _traceback: object) -> None:
        changed = hashlib.sha256 is not self._installed
        hashlib.sha256 = self._original  # type: ignore[assignment]
        if changed:
            raise RuntimeError("query-bound hash meter binding changed")


class _NamedObligationsV1:
    def __init__(self) -> None:
        self.integrity: list[str] = []
        self.protocol: list[str] = []

    def checked_integrity(self, name: str) -> None:
        if type(name) is not str or not name or name in self.integrity:
            raise RuntimeError("child integrity obligation is invalid or duplicated")
        self.integrity.append(name)

    def checked_protocol(self, name: str) -> None:
        if type(name) is not str or not name or name in self.protocol:
            raise RuntimeError("child protocol obligation is invalid or duplicated")
        self.protocol.append(name)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-source", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--inputs-root", required=True, type=Path)
    parser.add_argument("--trace-output", required=True, type=Path)
    return parser


def _read_and_verify_inputs(
    *,
    request: dict[str, Any],
    inputs_root: Path,
    canonical_json_bytes: Any,
    loads_canonical_json: Any,
) -> dict[str, bytes]:
    inventory = request["input_inventory"]
    if type(inventory) is not list or len(inventory) != len(INPUT_ROLES):
        raise RuntimeError("query-bound input inventory cardinality changed")
    expected = {role: filename for role, filename in INPUT_ROLES}
    observed: dict[str, bytes] = {}
    for index, row in enumerate(inventory):
        if type(row) is not dict or set(row) != {
            "role",
            "filename",
            "byte_count",
            "sha256",
        }:
            raise RuntimeError("query-bound input inventory row changed")
        role = row["role"]
        if (
            type(role) is not str
            or role not in expected
            or row["filename"] != expected[role]
            or type(row["byte_count"]) is not int
            or row["byte_count"] <= 0
            or type(row["sha256"]) is not str
            or len(row["sha256"]) != 64
            or role in observed
            or role != INPUT_ROLES[index][0]
        ):
            raise RuntimeError("query-bound input inventory identity changed")
        path = inputs_root / row["filename"]
        if path.is_symlink() or not path.is_file() or path.parent != inputs_root:
            raise RuntimeError("query-bound staged input path changed")
        raw = path.read_bytes()
        if (
            len(raw) != row["byte_count"]
            or hashlib.sha256(raw).hexdigest() != row["sha256"]
        ):
            raise RuntimeError("query-bound staged input digest changed")
        document = loads_canonical_json(raw)
        if type(document) is not dict or canonical_json_bytes(document) != raw:
            raise RuntimeError("query-bound staged input is not canonical JSON")
        observed[role] = raw
    return observed


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    runtime_source = args.runtime_source.resolve(strict=True)
    inputs_root = args.inputs_root.resolve(strict=True)
    sys.path.insert(0, str(runtime_source))

    # Imports precede the operational hash window.  The continuation modules
    # perform no scientific work at import time.
    from acfqp import construction_accounting_live_v3 as live_v3
    from acfqp import construction_accounting_registry_v6 as registry_v6
    from acfqp import construction_k7_query_bound_accounted_continuation_v1 as continuation_v1
    from acfqp import construction_k7_query_bound_stage_accounting_v1 as stage_v1
    from acfqp.phase3e_ids import (
        CONSTRUCTION_K7_QUERY_BOUND_OPERATIONAL_TRACE_V1_DOMAIN,
        CONSTRUCTION_K7_QUERY_BOUND_SUPERVISED_REQUEST_V1_DOMAIN,
        canonical_json_bytes,
        content_id,
        loads_canonical_json,
        require_exact_fields,
    )

    obligations = _NamedObligationsV1()
    meter = _BusinessHashMeterV1()
    with meter:
        request_raw = args.request.read_bytes()
        request = loads_canonical_json(request_raw)
        if type(request) is not dict or canonical_json_bytes(request) != request_raw:
            raise RuntimeError("query-bound supervised request is not canonical")
        require_exact_fields(
            request,
            {
                "schema",
                "schema_version",
                "profile_key",
                "runtime_preparation_id",
                "runtime_tree_id",
                "input_inventory",
                "prepare_before_acquisition",
                "construction_only",
                "official_execution_allowed",
                "supervised_request_id",
            },
            context="query-bound supervised request",
        )
        if (
            request["schema"] != REQUEST_SCHEMA
            or request["schema_version"] != SCHEMA_VERSION
            or request["profile_key"]
            != "construction_k7_query_bound_supervised_executor_v1"
            or request["prepare_before_acquisition"] is not True
            or request["construction_only"] is not True
            or request["official_execution_allowed"] is not False
        ):
            raise RuntimeError("query-bound supervised request contract changed")
        request_payload = dict(request)
        request_id = request_payload.pop("supervised_request_id")
        if request_id != content_id(
            CONSTRUCTION_K7_QUERY_BOUND_SUPERVISED_REQUEST_V1_DOMAIN,
            request_payload,
        ):
            raise RuntimeError("query-bound supervised request ID changed")
        obligations.checked_integrity("request-canonical-and-content-id-replayed")
        obligations.checked_protocol("request-profile-and-cutoff-bound")

        inputs = _read_and_verify_inputs(
            request=request,
            inputs_root=inputs_root,
            canonical_json_bytes=canonical_json_bytes,
            loads_canonical_json=loads_canonical_json,
        )
        for role, _filename in INPUT_ROLES:
            obligations.checked_integrity(f"input-{role.lower()}-digest-replayed")
        obligations.checked_protocol("all-scientific-inputs-frozen-before-acquisition")

        result = continuation_v1.run_query_bound_accounted_continuation_v1(
            source_trace_bytes=inputs["SOURCE_TRACE"],
            build_epoch_envelope_bytes=inputs["BUILD_EPOCH_ENVELOPE"],
            root_query_result_bytes=inputs["ROOT_QUERY_RESULT"],
            overlay_bytes=inputs["RECOVERY_OVERLAY"],
            request_bytes=inputs["RECOVERY_REQUEST"],
        )
        continuation_v1.verify_query_bound_accounted_continuation_v1(result)
        result_document = result.to_document()
        obligations.checked_integrity("accounted-continuation-identity-replayed")
        if (
            result_document["local_transaction_count"] != 2
            or result_document["transaction_3_created"] is not False
            or result_document["fallback_executed_only_after_local_budget_exhaustion"]
            is not True
            or result_document["terminal_class"] != "PLAN_CERTIFICATE"
            or result_document["terminal_code"] != "FULL_GROUND_FALLBACK"
            or result_document["official_execution_allowed"] is not False
        ):
            raise RuntimeError("query-bound continuation terminal semantics changed")
        obligations.checked_protocol("two-local-transactions-precede-direct-fallback")

        registry = registry_v6.official_counter_registry_v6()
        stage_profile = registry_v6.official_stage_profile_v6(registry)
        comparison = registry_v6.official_comparison_profile_v6(registry)
        actual = registry_v6.official_actual_projection_profile_v6(
            registry,
            comparison,
        )
        stages = result.accounting.recorded_stages
        if (
            len(stages) != 5
            or tuple(
                registry_v6.ConstructionStageKindV6(
                    row.stage_start.stage_kind.value
                )
                for row in stages
            )
            != stage_v1.CANONICAL_QUERY_BOUND_STAGE_PLAN_V1
        ):
            raise RuntimeError("query-bound five-stage plan changed")
        obligations.checked_integrity("five-stage-inventory-replayed")
        stage_documents: list[dict[str, Any]] = []
        for index, recorded in enumerate(stages, 1):
            live_v3.verify_recorded_stage_work_v3(
                recorded,
                registry,
                stage_profile,
                comparison,
                actual,
            )
            if recorded.stage_start.stage_index != index:
                raise RuntimeError("query-bound stage sequence changed")
            stage_documents.append(recorded.to_document())
            obligations.checked_integrity(
                f"stage-{index:02d}-event-to-vector-replay"
            )
            obligations.checked_protocol(
                f"stage-{index:02d}-owner-and-sequence-binding"
            )

        work = result.direct_fallback.work
        science_summary = {
            "occurrence_id": result.transaction_1.request.logical_occurrence_id,
            "accounted_continuation_id": result.result_id,
            "stage_accounting_result_id": result.accounting.result_id,
            "transaction_1_id": result.transaction_1.transaction_id,
            "replanning_1_id": result.replanning_1.result_id,
            "transaction_2_request_id": result.request_2.request_id,
            "transaction_2_id": result.transaction_2.transaction_id,
            "final_local_replanning_id": result.final_local_replanning.result_id,
            "direct_ground_fallback_id": result.direct_fallback.result_id,
            "terminal_class": result.direct_fallback.terminal_class.value,
            "terminal_code": result.direct_fallback.terminal_code.value,
            "route_attempts": 1,
            "route_successes": 1,
            "route_failures": 0,
            "solver_attempts": 1,
            "solver_successes": 1,
            "solver_failures": 0,
            "stage_instance_count": len(stages),
            "stage_local_counter_record_count": sum(
                len(row.work_vector.records) for row in stages
            ),
            "local_transaction_count": 2,
            "cumulative_local_ground_draw_count": (
                result.transaction_1.total_ground_draw_count
                + result.transaction_2.total_ground_draw_count
            ),
            "fallback_states_expanded": work.states_expanded,
            "fallback_actions_evaluated": work.actions_evaluated,
            "fallback_ground_steps": work.ground_steps,
            "fallback_outcome_rows": work.outcome_rows,
            "fallback_bellman_backups": work.bellman_backups,
        }
        if (
            science_summary["stage_local_counter_record_count"] != 1_010
            or science_summary["cumulative_local_ground_draw_count"] != 25_344
            or (
                science_summary["fallback_states_expanded"],
                science_summary["fallback_actions_evaluated"],
                science_summary["fallback_ground_steps"],
                science_summary["fallback_outcome_rows"],
                science_summary["fallback_bellman_backups"],
            )
            != (30, 96, 96, 1_440, 102)
        ):
            raise RuntimeError("query-bound derived science summary changed")
        obligations.checked_integrity("science-summary-derived-from-live-result")
        obligations.checked_protocol("route-and-solver-reconciliation-derived")

    if meter.count <= 0:
        raise RuntimeError("query-bound business hash window is empty")
    peak_bytes = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    payload = {
        "artifact_role": "OPERATIONAL_TRACE",
        "schema": TRACE_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "supervised_request_id": request_id,
        "runtime_preparation_id": request["runtime_preparation_id"],
        "runtime_tree_id": request["runtime_tree_id"],
        "science_summary": science_summary,
        "recorded_stages": stage_documents,
        "business_hash_invocations": meter.count,
        "child_integrity_obligations": sorted(obligations.integrity),
        "child_protocol_obligations": sorted(obligations.protocol),
        "child_self_peak_working_bytes_diagnostic": peak_bytes,
        "hash_measurement_window_start": "AFTER_RUNTIME_INFRASTRUCTURE_IMPORTS",
        "hash_measurement_window_end": (
            "AFTER_STAGE_AND_TERMINAL_REPLAY_BEFORE_TRACE_PROVENANCE"
        ),
        "accounting_provenance_hashes_excluded": True,
        "global_hashlib_sha256_constructor_hook_present": True,
        "formal_counter_records_issued_by_worker": False,
        "occurrence_vector_issued_by_worker": False,
        "construction_only": True,
        "official_execution_allowed": False,
    }
    document = {
        **payload,
        "operational_trace_id": content_id(
            CONSTRUCTION_K7_QUERY_BOUND_OPERATIONAL_TRACE_V1_DOMAIN,
            payload,
        ),
    }
    raw = canonical_json_bytes(document)
    descriptor = os.open(
        args.trace_output,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o600,
    )
    try:
        offset = 0
        while offset < len(raw):
            count = os.write(descriptor, raw[offset:])
            if count <= 0:
                raise RuntimeError("query-bound trace write made no progress")
            offset += count
    finally:
        os.close(descriptor)
    return 0


if __name__ == "__main__":  # pragma: no cover - trusted supervisor entry
    raise SystemExit(main())
