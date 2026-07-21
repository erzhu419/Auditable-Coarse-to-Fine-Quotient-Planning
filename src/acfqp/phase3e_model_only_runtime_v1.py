"""Fresh-process runtime for the non-official Phase-3E model-only producer.

The file intentionally performs no :mod:`acfqp` import until ``main`` has
installed the runtime root and a deny-list import finder.  Its only semantic
inputs are a verified source lease plus the exact serialized portable RAPM and
query bytes.  Ground-domain, local-recovery, fallback, and Phase-3D modules are
not part of this execution lane.
"""

from __future__ import annotations

import argparse
import importlib.abc
from pathlib import Path
import resource
import sys
from typing import Any


FORBIDDEN_PREFIXES = (
    "acfqp.domains",
    "acfqp.frozen_phase3c",
    "acfqp.general_local_recovery",
    "acfqp.general_local_runtime",
    "acfqp.general_local_solver",
    "acfqp.local_recovery",
    "acfqp.local_runtime",
    "acfqp.local_solver",
    "acfqp.planning.ground",
    "acfqp.phase3d",
    "acfqp.phase3e_fallback",
    "acfqp.phase3e_ground_handoff",
    "acfqp.phase3e_integrated_fallback",
    "acfqp.phase3e_isolated_fallback",
    "acfqp.phase3e_local_adapter",
    "acfqp.phase3e_local_preselection",
    "acfqp.phase3e_local_semantics",
)


def _is_forbidden_module_v1(fullname: str) -> bool:
    """Match a forbidden family, including its registered ``_vN`` modules.

    ``startswith(prefix + ".")`` does not match a real module such as
    ``acfqp.phase3e_fallback_v1``.  Conversely, a raw prefix match would also
    reject unrelated names such as ``...fallback_victim``.  Restrict the
    suffix form to ``_v`` followed by decimal digits and an optional submodule.
    """

    for prefix in FORBIDDEN_PREFIXES:
        if fullname == prefix or fullname.startswith(prefix + "."):
            return True
        if not fullname.startswith(prefix + "_v"):
            continue
        suffix = fullname[len(prefix) + 2 :]
        version, separator, _submodule = suffix.partition(".")
        if version.isdecimal() and (not separator or _submodule):
            return True
    return False


class _GroundImportDenyFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path: Any = None, target: Any = None) -> None:
        del path, target
        if _is_forbidden_module_v1(fullname):
            raise ImportError(
                f"ground/local/fallback import is forbidden in model-only runtime: {fullname}"
            )
        return None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-source", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    sys.path.insert(0, str(args.runtime_source.resolve()))
    sys.meta_path.insert(0, _GroundImportDenyFinder())

    from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
    from acfqp.phase3e_model_only_executor_v1 import (
        ModelOnlyNativeEventTraceV1,
        parse_model_only_execution_request_v1,
        reconstruct_model_only_source_from_request_v1,
        worker_output_document_v1,
    )
    from acfqp.phase3e_model_only_v1 import run_phase3e_model_only_from_source_v1

    request_raw = args.request.read_bytes()
    request_document = loads_canonical_json(request_raw)
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

    count("common.protocol_checks")
    request = parse_model_only_execution_request_v1(request_document)
    count("common.hash_invocations")  # request content-ID replay
    source = reconstruct_model_only_source_from_request_v1(request)
    # The reconstruction performs two explicit SHA-256 byte checks and five
    # lease/model/query integrity bindings.
    count("common.hash_invocations", 2)
    count("common.integrity_checks", 5)
    result = run_phase3e_model_only_from_source_v1(
        source,
        regret_tolerance=request.regret_tolerance,
        operation_counter=count,
    )
    forbidden = tuple(
        sorted(
            name
            for name in sys.modules
            if _is_forbidden_module_v1(name)
        )
    )
    count("common.integrity_checks")
    if forbidden:
        raise RuntimeError(f"model-only runtime imported forbidden modules: {forbidden!r}")
    count("common.protocol_checks")
    count("common.hash_invocations")  # output content-ID construction
    trace = ModelOnlyNativeEventTraceV1.from_events(events)
    peak_bytes = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    output = worker_output_document_v1(
        request=request,
        result=result,
        event_trace=trace,
        peak_working_bytes=peak_bytes,
        forbidden_imports=forbidden,
    )
    args.output.write_bytes(canonical_json_bytes(output))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through supervisor
    raise SystemExit(main())
