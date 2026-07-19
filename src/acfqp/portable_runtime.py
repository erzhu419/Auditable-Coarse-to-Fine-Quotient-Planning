"""Minimal sandbox entry point for the portable RAPM planner.

This module is copied together with :mod:`acfqp.portable` and
:mod:`acfqp.portable_planner` into a temporary namespace package.  The Phase
3B runner executes that package in a bubblewrap mount namespace that contains
no project checkout or ground-planning modules.  The emitted attestation is
descriptive evidence from inside that namespace; the parent verifier still
replays and checks the resulting plan independently.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any

from acfqp.portable import canonical_json, load_model, load_query, logical_id
from acfqp.portable_planner import dump_result, solve_portable_pareto


ATTESTATION_SCHEMA = "acfqp.portable_runtime_attestation.v1"
FORBIDDEN_MODULES = (
    "acfqp.abstraction",
    "acfqp.build_coverage",
    "acfqp.domains",
    "acfqp.enumeration",
    "acfqp.phase3a",
    "acfqp.phase3b",
    "acfqp.planning",
    "acfqp.refinement",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_spec(name: str) -> Any:
    try:
        return importlib.util.find_spec(name)
    except (ImportError, ModuleNotFoundError):
        return None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Solve a portable RAPM query inside the staged runtime"
    )
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--query", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--attestation", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    input_regular_files = tuple(
        sorted(path.name for path in args.model.parent.iterdir() if path.is_file())
    )
    output_regular_files_before = tuple(
        sorted(path.name for path in args.output.parent.iterdir() if path.is_file())
    )
    visible_forbidden_modules = tuple(
        name for name in FORBIDDEN_MODULES if _find_spec(name) is not None
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
            "portable runtime isolation failed: "
            f"modules={visible_forbidden_modules!r}, roots={visible_forbidden_roots!r}"
        )

    model = load_model(args.model)
    query = load_query(args.query, model)
    result = solve_portable_pareto(model, query)
    dump_result(result, args.output)

    loaded_module_origins = []
    unexpected_module_origins = []
    for name, module in sorted(sys.modules.items()):
        raw_origin = getattr(module, "__file__", None)
        if raw_origin is None:
            continue
        origin = str(Path(raw_origin).resolve())
        loaded_module_origins.append({"module": name, "origin": origin})
        if not (origin.startswith("/usr/") or origin.startswith("/runtime/")):
            unexpected_module_origins.append({"module": name, "origin": origin})

    payload = {
        "schema": ATTESTATION_SCHEMA,
        "isolation_backend": "bubblewrap_mount_and_network_namespace",
        "python_site_disabled": True,
        "project_checkout_visible": False,
        "network_namespace_unshared": True,
        "forbidden_modules_resolved": (),
        "input_regular_files": input_regular_files,
        "output_regular_files_before": output_regular_files_before,
        "loaded_acfqp_modules": tuple(
            sorted(
                name
                for name in sys.modules
                if name == "acfqp" or name.startswith("acfqp.")
            )
        ),
        "loaded_module_origins": tuple(loaded_module_origins),
        "unexpected_module_origins": tuple(unexpected_module_origins),
        "runtime_source_sha256": {
            name: _sha256(Path(sys.modules[name].__file__))
            for name in (
                "acfqp.portable",
                "acfqp.portable_planner",
            )
        }
        | {"acfqp.portable_runtime": _sha256(Path(__file__))},
        "model_sha256": _sha256(args.model),
        "query_sha256": _sha256(args.query),
        "output_sha256": _sha256(args.output),
        "model_id": model.model_id,
        "query_id": query.query_id,
        "result_id": result.result_id,
    }
    document = {
        "attestation_id": logical_id("runtime-attestation", payload),
        **payload,
    }
    args.attestation.write_text(canonical_json(document) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through bubblewrap
    raise SystemExit(main())


__all__ = ["ATTESTATION_SCHEMA", "FORBIDDEN_MODULES", "main"]
