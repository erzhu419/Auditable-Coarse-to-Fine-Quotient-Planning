"""Fresh abstract-planning worker with a recursion-safe business hash window.

This entrypoint is staged through an immutable runtime-tree lease.  It keeps
imports and accounting/provenance serialization outside the chargeable hash
window, then globally intercepts ``hashlib.sha256`` while the transported
query is parsed, the RAPM source is reconstructed, and the abstract planner
and sound audit execute.  The wrapper count is therefore an exact count of
business SHA-256 constructor invocations, including content-ID calls and raw
source-byte checks, without recursively charging the evidence that reports
the count.

The worker does not issue CounterRecords.  Its parent independently binds the
sealed runtime manifest, process result, I/O formula, and resource observation
before any V6 authority can be created.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import resource
import sys
from typing import Any


SCHEMA_VERSION = "2.0.0"
WORKER_SCHEMA = "acfqp.phase3e_model_only_accounted_worker_output.v2"


class _BusinessHashMeterV2:
    """Process-local exact SHA-256 constructor meter."""

    def __init__(self) -> None:
        self.count = 0
        self._original: Any = None
        self._installed: Any = None

    def __enter__(self) -> "_BusinessHashMeterV2":
        if self._original is not None:
            raise RuntimeError("business hash meter is single-use")
        self._original = hashlib.sha256

        def metered_sha256(*args: Any, **kwargs: Any) -> Any:
            self.count += 1
            return self._original(*args, **kwargs)

        self._installed = metered_sha256
        hashlib.sha256 = metered_sha256  # type: ignore[assignment]
        return self

    def __exit__(self, _kind: object, _value: object, _traceback: object) -> None:
        original = self._original
        changed = original is None or hashlib.sha256 is not self._installed
        hashlib.sha256 = original  # type: ignore[assignment]
        if changed:
            raise RuntimeError("business hash meter binding changed during execution")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-source", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    sys.path.insert(0, str(args.runtime_source.resolve()))

    # Imports are runtime infrastructure rather than query work.  Load them
    # before opening the business window; subsequent calls still traverse the
    # globally replaced hashlib.sha256 attribute.
    from acfqp.phase3e_model_only_runtime_v1 import (
        _GroundImportDenyFinder,
        _is_forbidden_module_v1,
    )

    sys.meta_path.insert(0, _GroundImportDenyFinder())

    from acfqp.phase3e_ids import (
        CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_WORKER_OUTPUT_V2_DOMAIN,
        canonical_json_bytes,
        content_id,
        loads_canonical_json,
    )
    from acfqp.phase3e_model_only_executor_v1 import (
        ModelOnlyNativeEventTraceV1,
        parse_model_only_execution_request_v1,
        reconstruct_model_only_source_from_request_v1,
        worker_output_document_v1,
    )
    from acfqp.phase3e_model_only_v1 import run_phase3e_model_only_from_source_v1

    events: list[tuple[str, int]] = []

    def count(path: str, amount: int = 1) -> None:
        if path not in {
            "common.abstract_bellman_backups",
            "common.abstract_audit_obligations",
            "common.integrity_checks",
            "common.protocol_checks",
            "common.hash_invocations",
        }:
            raise ValueError(f"unregistered model-only runtime event: {path}")
        if type(amount) is not int or amount <= 0:
            raise ValueError("runtime event amounts must be positive integers")
        events.append((path, amount))

    meter = _BusinessHashMeterV2()
    with meter:
        request_raw = args.request.read_bytes()
        request_document = loads_canonical_json(request_raw)
        count("common.protocol_checks")
        request = parse_model_only_execution_request_v1(request_document)
        count("common.hash_invocations")
        source = reconstruct_model_only_source_from_request_v1(request)
        count("common.hash_invocations", 2)
        count("common.integrity_checks", 5)
        result = run_phase3e_model_only_from_source_v1(
            source,
            regret_tolerance=request.regret_tolerance,
            operation_counter=count,
        )
        forbidden = tuple(
            sorted(name for name in sys.modules if _is_forbidden_module_v1(name))
        )
        count("common.integrity_checks")
        if forbidden:
            raise RuntimeError(
                f"model-only runtime imported forbidden modules: {forbidden!r}"
            )
        count("common.protocol_checks")
        # Retain the historical trace row for compatibility.  The V2 formal
        # hash value comes only from ``meter.count``.
        count("common.hash_invocations")

    if type(meter.count) is not int or meter.count <= 0:
        raise RuntimeError("business hash window produced no SHA-256 observation")

    trace = ModelOnlyNativeEventTraceV1.from_events(events)
    peak_bytes = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    nested = worker_output_document_v1(
        request=request,
        result=result,
        event_trace=trace,
        peak_working_bytes=peak_bytes,
        forbidden_imports=forbidden,
    )
    payload = {
        "schema": WORKER_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "request_id": request.request_id,
        "nested_worker_output": nested,
        "business_hash_invocations": meter.count,
        "hash_measurement_window_start": "AFTER_RUNTIME_INFRASTRUCTURE_IMPORTS",
        "hash_measurement_window_end": "BEFORE_ACCOUNTING_AND_PROVENANCE_SERIALIZATION",
        "accounting_provenance_hashes_excluded": True,
        "global_hashlib_sha256_constructor_hook_present": True,
        "formal_counter_record_issued_by_worker": False,
    }
    document = {
        **payload,
        "accounted_worker_output_id": content_id(
            CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_WORKER_OUTPUT_V2_DOMAIN,
            payload,
        ),
    }
    args.output.write_bytes(canonical_json_bytes(document))
    return 0


if __name__ == "__main__":  # pragma: no cover - executed by the supervisor
    raise SystemExit(main())
