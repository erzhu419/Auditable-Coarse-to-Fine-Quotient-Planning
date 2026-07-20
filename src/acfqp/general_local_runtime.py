"""Isolated stdlib runtime for sparse-affine general local recovery.

The process accepts exactly three read-only JSON files: a cell-level sparse
robust affine capability, its frontier ground slice, and an occurrence-bound
request.  It records mount/file inventory, import visibility, interpreter and
source hashes, and output identity.  This is integrity/reproducibility
evidence; it is not host or process provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
from typing import Any, Sequence


FORBIDDEN_PREFIXES = (
    "acfqp.domains",
    "acfqp.planning",
    "acfqp.ground",
    "acfqp.abstraction",
    "acfqp.local_recovery",
    "acfqp.phase3c",
    "acfqp.portable_planner",
)
FORBIDDEN_MODULES = FORBIDDEN_PREFIXES
ATTESTATION_SCHEMA = "acfqp.general_local_runtime_attestation.v1"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _logical_id(prefix: str, value: Any) -> str:
    return f"{prefix}:{_sha256_bytes(_canonical_json(value).encode('utf-8'))}"


def _forbidden_loaded() -> tuple[str, ...]:
    return tuple(
        sorted(
            name
            for name in sys.modules
            if any(
                name == prefix or name.startswith(prefix + ".")
                for prefix in FORBIDDEN_PREFIXES
            )
        )
    )


def _find_spec(name: str) -> Any:
    try:
        return importlib.util.find_spec(name)
    except (ImportError, ModuleNotFoundError):
        return None


class _AuthorityBlocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path: Any, target: Any = None) -> None:
        if any(
            fullname == prefix or fullname.startswith(prefix + ".")
            for prefix in FORBIDDEN_PREFIXES
        ):
            raise ImportError(
                "general local runtime forbids importing authority module "
                f"{fullname!r}"
            )
        return None


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _load_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        document = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not valid UTF-8 JSON") from error
    if not isinstance(document, dict):
        raise ValueError(f"{label} root must be an object")
    return document, raw


def _write_canonical(path: Path, document: dict[str, Any]) -> bytes:
    raw = (_canonical_json(document) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return raw


def run_isolated(
    capability_path: Path,
    slice_path: Path,
    request_path: Path,
    output_path: Path,
    attestation_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the worker after verifying its complete capability inventory."""

    input_parents = {
        capability_path.parent.resolve(),
        slice_path.parent.resolve(),
        request_path.parent.resolve(),
    }
    if len(input_parents) != 1:
        raise RuntimeError(
            "all general local capabilities must share one inventoried input directory"
        )
    if output_path.parent.resolve() != attestation_path.parent.resolve():
        raise RuntimeError("result and attestation must share one output directory")
    input_regular_files = tuple(
        sorted(path.name for path in capability_path.parent.iterdir() if path.is_file())
    )
    output_regular_files_before = tuple(
        sorted(path.name for path in output_path.parent.iterdir() if path.is_file())
    )
    expected_inputs = tuple(
        sorted((capability_path.name, request_path.name, slice_path.name))
    )
    if input_regular_files != expected_inputs:
        raise RuntimeError(
            "general local input directory contains files outside the three-file "
            f"capability: {input_regular_files!r}"
        )
    if output_regular_files_before:
        raise RuntimeError("general local runtime output directory must be empty")
    if not sys.flags.no_site:
        raise RuntimeError("general local runtime requires Python -S")

    visible_forbidden_modules = tuple(
        name for name in FORBIDDEN_PREFIXES if _find_spec(name) is not None
    )
    forbidden_roots = tuple(
        path
        for path in os.environ.get("ACFQP_FORBIDDEN_ROOTS", "").split(os.pathsep)
        if path
    )
    visible_forbidden_roots = tuple(
        path for path in forbidden_roots if Path(path).exists()
    )
    if visible_forbidden_modules or visible_forbidden_roots:
        raise RuntimeError(
            "general local runtime isolation failed: "
            f"modules={visible_forbidden_modules!r}, "
            f"roots={visible_forbidden_roots!r}"
        )
    loaded_before = _forbidden_loaded()
    if loaded_before:
        raise RuntimeError(
            f"forbidden authority modules already loaded: {loaded_before!r}"
        )

    blocker = _AuthorityBlocker()
    sys.meta_path.insert(0, blocker)
    try:
        if __package__:
            from .general_local_solver import (
                solve_general_local_recovery,
                validate_general_local_result,
            )
            from . import general_local_solver as solver_module
        else:
            import general_local_solver as solver_module  # type: ignore[no-redef]
            from general_local_solver import (  # type: ignore[no-redef]
                solve_general_local_recovery,
                validate_general_local_result,
            )

        capability, capability_raw = _load_json(
            capability_path, "sparse affine capability"
        )
        ground_slice, slice_raw = _load_json(slice_path, "ground slice")
        request, request_raw = _load_json(request_path, "general local request")
        result = solve_general_local_recovery(
            capability, ground_slice, request
        ).to_dict()
        validate_general_local_result(result)
        output_raw = _write_canonical(output_path, result)

        loaded_after = _forbidden_loaded()
        if loaded_after:
            raise RuntimeError(
                f"general local solver imported forbidden modules: {loaded_after!r}"
            )
        loaded_module_origins: list[dict[str, str]] = []
        unexpected_module_origins: list[dict[str, str]] = []
        for name, module in sorted(sys.modules.items()):
            raw_origin = getattr(module, "__file__", None)
            if raw_origin is None:
                continue
            origin = str(Path(raw_origin).resolve())
            record = {"module": name, "origin": origin}
            loaded_module_origins.append(record)
            if not (origin.startswith("/usr/") or origin.startswith("/runtime/")):
                unexpected_module_origins.append(record)
        attestation_payload = {
            "schema": ATTESTATION_SCHEMA,
            "isolation_backend": "bubblewrap_mount_and_network_namespace",
            "isolation_profile": "stdlib_sparse_affine_capability.v1",
            "python_site_disabled": True,
            "project_checkout_visible": False,
            "network_namespace_unshared": True,
            "forbidden_modules_resolved": list(visible_forbidden_modules),
            "input_regular_files": list(input_regular_files),
            "output_regular_files_before": list(output_regular_files_before),
            "capability_sha256": _sha256_bytes(capability_raw),
            "slice_sha256": _sha256_bytes(slice_raw),
            "request_sha256": _sha256_bytes(request_raw),
            "output_sha256": _sha256_bytes(output_raw),
            "request_id": result["request_id"],
            "occurrence_id": result["occurrence_id"],
            "capability_id": result["capability_id"],
            "slice_id": result["slice_id"],
            "result_id": result["result_id"],
            "status": result["status"],
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "python_executable": str(Path(sys.executable).resolve()),
            "python_executable_sha256": _sha256_file(Path(sys.executable)),
            "hash_seed": os.environ.get("PYTHONHASHSEED", "unset"),
            "forbidden_prefixes": list(FORBIDDEN_PREFIXES),
            "forbidden_loaded_before": list(loaded_before),
            "forbidden_loaded_after": list(loaded_after),
            "loaded_acfqp_modules": sorted(
                name
                for name in sys.modules
                if name == "acfqp" or name.startswith("acfqp.")
            ),
            "loaded_module_origins": loaded_module_origins,
            "unexpected_module_origins": unexpected_module_origins,
            "runtime_source_sha256": {
                "acfqp.general_local_solver": _sha256_file(
                    Path(solver_module.__file__)
                ),
                "acfqp.general_local_runtime": _sha256_file(Path(__file__)),
            },
            "claim_boundary": (
                "integrity_and_reproducibility_evidence_only; "
                "not_host_or_process_provenance"
            ),
        }
        attestation = {
            **attestation_payload,
            "attestation_id": _logical_id(
                "general-local-runtime-attestation", attestation_payload
            ),
        }
        if unexpected_module_origins:
            raise RuntimeError(
                "general local runtime loaded modules outside /usr and /runtime: "
                f"{unexpected_module_origins!r}"
            )
        _write_canonical(attestation_path, attestation)
        return result, attestation
    finally:
        if blocker in sys.meta_path:
            sys.meta_path.remove(blocker)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run exact sparse-affine general local recovery"
    )
    parser.add_argument("--capability", type=Path, required=True)
    parser.add_argument("--slice", dest="slice_path", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--attestation", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    run_isolated(
        args.capability,
        args.slice_path,
        args.request,
        args.output,
        args.attestation,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


run = run_isolated

__all__ = [
    "ATTESTATION_SCHEMA",
    "FORBIDDEN_MODULES",
    "FORBIDDEN_PREFIXES",
    "main",
    "run",
    "run_isolated",
]
