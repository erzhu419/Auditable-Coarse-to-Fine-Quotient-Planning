"""Fresh worker for one recovery-eligible world-model occurrence.

The worker reconstructs the preregistered proof cache from three immutable
inputs, replays the cached certificate failure, acquires only the six
requestable ground rows, overlays them, replans in the updated RAPM, and uses
direct exact fallback only after the local frontier is exhausted.  It emits a
portable operational trace; process, I/O, peak memory, and final output bytes
remain owned by the supervisor/finalizer.
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
PROFILE_KEY = "construction_k7_recovery_eligible_accounted_runtime_v1"
REQUEST_SCHEMA = "acfqp.construction_k7_recovery_eligible_supervised_request.v1"
TRACE_SCHEMA = "acfqp.construction_k7_recovery_eligible_operational_trace.v1"

INPUT_ROLES = (
    ("SOURCE_BUNDLE_BINDING", "source_bundle_binding.json"),
    ("REUSABLE_RAPM_SNAPSHOT", "reusable_rapm_snapshot.json"),
    ("PROOF_DEPENDENCY_TRANSITION", "proof_dependency_transition.json"),
)


class _BusinessHashMeterV1:
    def __init__(self) -> None:
        self.count = 0
        self._original: Any = None
        self._installed: Any = None

    def __enter__(self) -> "_BusinessHashMeterV1":
        if self._original is not None:
            raise RuntimeError("recovery hash meter is single-use")
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
            raise RuntimeError("recovery hash meter binding changed")


class _NamedObligationsV1:
    def __init__(self) -> None:
        self.integrity: list[str] = []
        self.protocol: list[str] = []

    def integrity_checked(self, name: str) -> None:
        if type(name) is not str or not name or name in self.integrity:
            raise RuntimeError("child integrity obligation is invalid or duplicated")
        self.integrity.append(name)

    def protocol_checked(self, name: str) -> None:
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


def _read_inputs(
    *,
    request: dict[str, Any],
    inputs_root: Path,
    canonical_json_bytes: Any,
    loads_canonical_json: Any,
) -> dict[str, bytes]:
    inventory = request["input_inventory"]
    if type(inventory) is not list or len(inventory) != len(INPUT_ROLES):
        raise RuntimeError("recovery input inventory cardinality changed")
    observed: dict[str, bytes] = {}
    for index, (role, filename) in enumerate(INPUT_ROLES):
        row = inventory[index]
        if type(row) is not dict or set(row) != {
            "role",
            "filename",
            "byte_count",
            "sha256",
        }:
            raise RuntimeError("recovery input inventory row changed")
        if (
            row["role"] != role
            or row["filename"] != filename
            or type(row["byte_count"]) is not int
            or row["byte_count"] <= 0
            or type(row["sha256"]) is not str
            or len(row["sha256"]) != 64
        ):
            raise RuntimeError("recovery input inventory identity changed")
        path = inputs_root / filename
        if path.is_symlink() or not path.is_file() or path.parent != inputs_root:
            raise RuntimeError("recovery staged input path changed")
        raw = path.read_bytes()
        if (
            len(raw) != row["byte_count"]
            or hashlib.sha256(raw).hexdigest() != row["sha256"]
        ):
            raise RuntimeError("recovery staged input digest changed")
        document = loads_canonical_json(raw)
        if type(document) is not dict or canonical_json_bytes(document) != raw:
            raise RuntimeError("recovery staged input is not canonical JSON")
        observed[role] = raw
    return observed


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    runtime_source = args.runtime_source.resolve(strict=True)
    inputs_root = args.inputs_root.resolve(strict=True)
    sys.path.insert(0, str(runtime_source))

    # Imports precede the business hash window and perform no scientific work.
    from acfqp import construction_accounting_live_v3 as live_v3
    from acfqp import construction_accounting_registry_v6 as registry_v6
    from acfqp import construction_k7_query_bound_persistent_proof_cache_v1 as cache_v1
    from acfqp import construction_k7_recovery_eligible_checkpoint_fixture_v1 as checkpoint_v1
    from acfqp import construction_k7_recovery_eligible_native_accounting_v1 as native_v1
    from acfqp import construction_k7_recovery_eligible_stage_accounting_v1 as stage_v1
    from acfqp.phase3e_ids import (
        CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OPERATIONAL_TRACE_V1_DOMAIN,
        CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SUPERVISED_REQUEST_V1_DOMAIN,
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
            raise RuntimeError("recovery supervised request is not canonical")
        require_exact_fields(
            request,
            {
                "schema",
                "schema_version",
                "profile_key",
                "runtime_preparation_id",
                "runtime_tree_id",
                "input_inventory",
                "logical_occurrence_id",
                "query_ordinal",
                "checkpoint_replayed_before_ground_access",
                "construction_only",
                "official_execution_allowed",
                "supervised_request_id",
            },
            context="recovery supervised request",
        )
        if (
            request["schema"] != REQUEST_SCHEMA
            or request["schema_version"] != SCHEMA_VERSION
            or request["profile_key"]
            != "construction_k7_recovery_eligible_supervised_executor_v1"
            or type(request["logical_occurrence_id"]) is not str
            or len(request["logical_occurrence_id"]) != 64
            or type(request["query_ordinal"]) is not int
            or request["query_ordinal"] <= 1
            or request["checkpoint_replayed_before_ground_access"] is not True
            or request["construction_only"] is not True
            or request["official_execution_allowed"] is not False
        ):
            raise RuntimeError("recovery supervised request contract changed")
        payload = dict(request)
        request_id = payload.pop("supervised_request_id")
        if request_id != content_id(
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SUPERVISED_REQUEST_V1_DOMAIN,
            payload,
        ):
            raise RuntimeError("recovery supervised request ID changed")
        obligations.integrity_checked("request-canonical-and-content-id-replayed")
        obligations.protocol_checked("request-and-fresh-query-frozen-before-launch")

        inputs = _read_inputs(
            request=request,
            inputs_root=inputs_root,
            canonical_json_bytes=canonical_json_bytes,
            loads_canonical_json=loads_canonical_json,
        )
        for role, _filename in INPUT_ROLES:
            obligations.integrity_checked(f"input-{role.lower()}-digest-replayed")
        obligations.protocol_checked("three-cache-inputs-read-before-ground-access")

        persistent = cache_v1.materialize_query_bound_persistent_proof_cache_bytes_v1(
            binding_bytes=inputs["SOURCE_BUNDLE_BINDING"],
            snapshot_bytes=inputs["REUSABLE_RAPM_SNAPSHOT"],
            transition_bytes=inputs["PROOF_DEPENDENCY_TRANSITION"],
        )
        checkpoint = checkpoint_v1.materialize_recovery_eligible_checkpoint_fixture_v1(
            canonical_json_bytes(persistent.to_document())
        )
        query = checkpoint_v1.freeze_recovery_eligible_checkpoint_query_v1(
            checkpoint,
            logical_occurrence_id=request["logical_occurrence_id"],
            query_ordinal=request["query_ordinal"],
        )
        consumption = checkpoint_v1.consume_recovery_eligible_checkpoint_v1(
            checkpoint, query
        )
        recovery_request = checkpoint_v1.prepare_recovery_eligible_recovery_request_v1(
            checkpoint, consumption
        )
        obligations.integrity_checked("persistent-cache-and-checkpoint-replayed")
        obligations.protocol_checked("cached-failure-precedes-local-ground-recovery")

        result = native_v1.execute_recovery_eligible_native_accounted_occurrence_v1(
            recovery_request
        )
        result_document = result.to_document()
        if (
            result_document["logical_occurrence_id"]
            != request["logical_occurrence_id"]
            or result_document["stage_count"] != 3
            or result_document["local_ground_draw_count"] != 12_672
            or result_document["changed_abstract_row_count"] != 6
            or result_document["fallback_ground_step_count"] != 96
            or result_document["terminal_class"] != "PLAN_CERTIFICATE"
            or result_document["terminal_code"] != "FULL_GROUND_FALLBACK"
            or result_document["official_execution_allowed"] is not False
        ):
            raise RuntimeError("recovery native scientific result changed")
        obligations.integrity_checked("native-accounting-identity-replayed")
        obligations.protocol_checked("local-recovery-exhaustion-precedes-fallback")

        registry = registry_v6.official_counter_registry_v6()
        stage_profile = registry_v6.official_stage_profile_v6(registry)
        comparison = registry_v6.official_comparison_profile_v6(registry)
        actual = registry_v6.official_actual_projection_profile_v6(
            registry, comparison
        )
        stages = result.stage_accounting.recorded_stages
        if tuple(
            registry_v6.ConstructionStageKindV6(row.stage_start.stage_kind.value)
            for row in stages
        ) != stage_v1.CANONICAL_STAGE_PLAN_V1:
            raise RuntimeError("recovery three-stage plan changed")
        obligations.integrity_checked("three-stage-inventory-replayed")
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
                raise RuntimeError("recovery stage sequence changed")
            stage_documents.append(recorded.to_document())
            obligations.integrity_checked(f"stage-{index:02d}-event-to-vector-replay")
            obligations.protocol_checked(f"stage-{index:02d}-owner-and-sequence-binding")

        work = result.fallback.work
        science_summary = {
            "occurrence_id": request["logical_occurrence_id"],
            "persistent_proof_cache_id": persistent.cache_id,
            "recovery_eligible_checkpoint_id": checkpoint.checkpoint_id,
            "recovery_request_id": recovery_request.request_id,
            "native_accounting_id": result.result_id,
            "stage_accounting_result_id": result.stage_accounting.result_id,
            "ground_transaction_id": result.world_model_loop.transaction.transaction_id,
            "world_model_loop_id": result.world_model_loop.result_id,
            "direct_ground_fallback_id": result.fallback.result_id,
            "terminal_class": result.fallback.terminal_class.value,
            "terminal_code": result.fallback.terminal_code.value,
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
            "proof_node_reuse_count": len(checkpoint.node_inventory),
            "requested_frontier_row_count": len(recovery_request.requested_rows),
            "local_ground_draw_count": result.world_model_loop.transaction.total_ground_draw_count,
            "changed_abstract_row_count": len(result.world_model_loop.changed_row_binding_ids),
            "fallback_states_expanded": work.states_expanded,
            "fallback_actions_evaluated": work.actions_evaluated,
            "fallback_ground_steps": work.ground_steps,
            "fallback_outcome_rows": work.outcome_rows,
            "fallback_bellman_backups": work.bellman_backups,
        }
        if (
            science_summary["stage_local_counter_record_count"] != 606
            or science_summary["proof_node_reuse_count"] != 41
            or science_summary["requested_frontier_row_count"] != 6
            or (
                science_summary["fallback_states_expanded"],
                science_summary["fallback_actions_evaluated"],
                science_summary["fallback_ground_steps"],
                science_summary["fallback_outcome_rows"],
                science_summary["fallback_bellman_backups"],
            )
            != (30, 96, 96, 1_440, 102)
        ):
            raise RuntimeError("recovery derived science summary changed")
        obligations.integrity_checked("science-summary-derived-from-live-result")
        obligations.protocol_checked("route-and-solver-reconciliation-derived")

    if meter.count <= 0:
        raise RuntimeError("recovery business hash window is empty")
    peak_bytes = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    trace_payload = {
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
        "full_planner_replayed_for_operational_validation": False,
        "standalone_verifier_work_included": False,
        "formal_occurrence_counter_records_issued_by_worker": False,
        "construction_only": True,
        "official_execution_allowed": False,
    }
    trace_document = {
        **trace_payload,
        "operational_trace_id": content_id(
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OPERATIONAL_TRACE_V1_DOMAIN,
            trace_payload,
        ),
    }
    trace_raw = canonical_json_bytes(trace_document)
    descriptor = os.open(
        args.trace_output,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o600,
    )
    try:
        offset = 0
        while offset < len(trace_raw):
            count = os.write(descriptor, trace_raw[offset:])
            if count <= 0:
                raise RuntimeError("recovery trace write made no progress")
            offset += count
    finally:
        os.close(descriptor)
    return 0


if __name__ == "__main__":  # pragma: no cover - trusted supervisor entry
    raise SystemExit(main())
