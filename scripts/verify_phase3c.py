#!/usr/bin/env python3
"""Independently verify a contract-0.8 local-recovery campaign bundle.

The verifier does not call :func:`acfqp.phase3c.run_phase3c` and does not use
the campaign report as authority.  It reconstructs the frozen world model,
replans both portable queries in process, derives the failed-proof DAG and its
DirectBad frontier, rematerializes the exact allowlisted slice, replays the
stdlib-only local solver, stitches the hybrid overlay, and only then evaluates
J0.  The artifact manifest is therefore an integrity index, not the source of
any semantic claim checked here.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acfqp.artifacts import (  # noqa: E402
    PHASE3C_DOCUMENT_CONTRACTS,
    PHASE3C_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    sha256_file,
    to_jsonable,
    verify_artifact_bundle,
)
from acfqp.local_recovery import (  # noqa: E402
    HybridPolicyOverlay,
    LocalRecoveryAuthorization,
    audit_hybrid_policy,
    build_failed_proof_graph,
    build_redacted_boundary_view,
    lift_hybrid_policy,
    materialize_authorized_slice,
    redact_authorized_slice_for_worker,
)
from acfqp.local_solver import solve_local_recovery  # noqa: E402
from acfqp.phase3c import (  # noqa: E402
    ABSTRACT_QUERY_KEY,
    CONTRACT_VERSION,
    ECONOMICS_NOT_RUN,
    EXECUTION_PROFILE,
    FULL_PHASE3_NOT_RUN,
    LOCAL_HYBRID_PASS,
    LOCAL_QUERY_KEY,
    PROFILE_KEY,
    SLICE_PASS,
    SUPPORTED_CLAIMS,
    UNSUPPORTED_CLAIMS,
    _audit_document,
    _authorization_document,
    _decode_policy,
    _frontier_document,
    _overlay_from_result,
    _policy_graph_document,
    _proof_graph_document,
    _query_payload,
    _same_query_all_action_counts,
    _select_recovery_proposal,
    _source_tree_hash,
    _spec_hashes,
    construct_phase3c_world,
)
from acfqp.planning import (  # noqa: E402
    audit_abstract_policy,
    solve_ground_pareto,
)
from acfqp.portable import PortableQuery, PortableRAPM, logical_id  # noqa: E402
from acfqp.portable_planner import (  # noqa: E402
    PortablePlanResult,
    solve_portable_pareto,
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[Any]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _same(actual: Any, expected: Any) -> bool:
    return actual == to_jsonable(expected)


def _expect(failures: list[str], label: str, actual: Any, expected: Any) -> None:
    if not _same(actual, expected):
        failures.append(f"{label} differs from independent replay")


def _canonical_bytes(document: Any) -> bytes:
    return (
        json.dumps(
            to_jsonable(document),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _artifact_json_bytes(document: Any) -> bytes:
    """Match ``acfqp.artifacts.write_json`` byte-for-byte."""

    return (
        json.dumps(
            to_jsonable(document),
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _stdlib_solver_source_failures() -> list[str]:
    """Conservatively reject package or non-stdlib imports in worker sources."""

    failures: list[str] = []
    stdlib = set(getattr(sys, "stdlib_module_names", ()))
    for name in ("local_solver.py", "local_runtime.py"):
        path = ROOT / "src" / "acfqp" / name
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported: list[str] = []
            if isinstance(node, ast.Import):
                imported = [alias.name.split(".", 1)[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    if name == "local_runtime.py" and node.module == "local_solver":
                        continue
                    failures.append(f"{name} contains a relative/package import")
                    continue
                if node.module:
                    imported = [node.module.split(".", 1)[0]]
            for module in imported:
                if (
                    stdlib
                    and module not in stdlib
                    and module != "__future__"
                    and not (name == "local_runtime.py" and module == "local_solver")
                ):
                    failures.append(f"{name} imports non-stdlib module {module!r}")
    return failures


def _validate_portable_attestation(
    attestation: Any,
    *,
    model: PortableRAPM,
    query: PortableQuery,
    result: PortablePlanResult,
) -> list[str]:
    failures: list[str] = []
    if not isinstance(attestation, dict):
        return ["portable planner attestation is not an object"]
    payload = dict(attestation)
    claimed = payload.pop("attestation_id", None)
    if claimed != logical_id("runtime-attestation", payload):
        failures.append("portable planner attestation content ID mismatch")
    expected_sources = {
        f"acfqp.{stem}": sha256_file(ROOT / "src" / "acfqp" / f"{stem}.py")
        for stem in ("portable", "portable_planner", "portable_runtime")
    }
    required = {
        "schema": "acfqp.portable_runtime_attestation.v1",
        "model_id": model.model_id,
        "query_id": query.query_id,
        "result_id": result.result_id,
        "model_sha256": _sha256_bytes(_canonical_bytes(model.to_dict())),
        "query_sha256": _sha256_bytes(_canonical_bytes(query.to_dict())),
        "output_sha256": _sha256_bytes(_canonical_bytes(result.to_dict())),
        "runtime_source_sha256": expected_sources,
        "project_checkout_visible": False,
        "network_namespace_unshared": True,
        "python_site_disabled": True,
        "forbidden_modules_resolved": [],
        "unexpected_module_origins": [],
        "input_regular_files": ["model.json", "query.json"],
        "output_regular_files_before": [],
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            failures.append(f"portable planner attestation field mismatch: {key}")
    return failures


def _isolated_portable_replay(
    model: PortableRAPM,
    query: PortableQuery,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Replay one portable occurrence with no ground/build authority mounted."""

    bubblewrap = shutil.which("bwrap")
    interpreter = shutil.which("python3", path="/usr/bin:/bin")
    if bubblewrap is None or interpreter is None:
        raise ValueError("independent Phase3C verification requires bwrap and system python3")
    with tempfile.TemporaryDirectory(prefix="acfqp-phase3c-verify-portable-") as temporary:
        root = Path(temporary)
        runtime_package = root / "runtime" / "acfqp"
        input_root = root / "input"
        output_root = root / "output"
        runtime_package.mkdir(parents=True)
        input_root.mkdir()
        output_root.mkdir()
        for name in ("portable.py", "portable_planner.py", "portable_runtime.py"):
            shutil.copy2(ROOT / "src" / "acfqp" / name, runtime_package / name)
        (input_root / "model.json").write_bytes(_canonical_bytes(model.to_dict()))
        (input_root / "query.json").write_bytes(_canonical_bytes(query.to_dict()))
        system_mounts: list[str] = []
        for path in ("/usr", "/lib", "/lib64"):
            if Path(path).exists():
                system_mounts.extend(("--ro-bind", path, path))
        process = subprocess.run(
            (
                bubblewrap,
                "--unshare-all",
                "--die-with-parent",
                "--new-session",
                "--clearenv",
                *system_mounts,
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "--tmpfs",
                "/tmp",
                "--ro-bind",
                str(root / "runtime"),
                "/runtime",
                "--ro-bind",
                str(input_root),
                "/input",
                "--dir",
                "/output",
                "--bind",
                str(output_root),
                "/output",
                "--chdir",
                "/output",
                "--setenv",
                "PATH",
                "/usr/bin:/bin",
                "--setenv",
                "PYTHONPATH",
                "/runtime",
                "--setenv",
                "LANG",
                "C.UTF-8",
                "--setenv",
                "ACFQP_FORBIDDEN_ROOTS",
                str(ROOT),
                str(Path(interpreter).resolve()),
                "-B",
                "-S",
                "-m",
                "acfqp.portable_runtime",
                "--model",
                "/input/model.json",
                "--query",
                "/input/query.json",
                "--output",
                "/output/result.json",
                "--attestation",
                "/output/attestation.json",
            ),
            cwd=output_root,
            env={"PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if process.returncode != 0 or process.stdout or process.stderr:
            raise ValueError(
                "fresh isolated portable replay failed: "
                f"rc={process.returncode}, stdout={process.stdout!r}, "
                f"stderr={process.stderr!r}"
            )
        return (
            _load(output_root / "result.json"),
            _load(output_root / "attestation.json"),
        )


def _validate_local_attestation(
    attestation: Any,
    *,
    boundary: dict[str, Any],
    ground_slice: dict[str, Any],
    request: dict[str, Any],
    result: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if not isinstance(attestation, dict):
        return ["local runtime attestation is not an object"]
    payload = dict(attestation)
    claimed = payload.pop("attestation_id", None)
    if claimed != logical_id("local-runtime-attestation", payload):
        failures.append("local runtime attestation content ID mismatch")
    expected_sources = {
        "acfqp.local_solver": sha256_file(ROOT / "src" / "acfqp/local_solver.py"),
        "acfqp.local_runtime": sha256_file(ROOT / "src" / "acfqp/local_runtime.py"),
    }
    required = {
        "schema": "acfqp.local_runtime_attestation.v1",
        "boundary_view_id": boundary["boundary_view_id"],
        "slice_id": ground_slice["slice_id"],
        "result_id": result["result_id"],
        "request_id": request["request_id"],
        "occurrence_id": request["occurrence_id"],
        "boundary_sha256": _sha256_bytes(_canonical_bytes(boundary)),
        "slice_sha256": _sha256_bytes(_canonical_bytes(ground_slice)),
        "request_sha256": _sha256_bytes(_canonical_bytes(request)),
        "output_sha256": _sha256_bytes(_canonical_bytes(result)),
        "runtime_source_sha256": expected_sources,
        "project_checkout_visible": False,
        "network_namespace_unshared": True,
        "python_site_disabled": True,
        "forbidden_modules_resolved": [],
        "forbidden_loaded_before": [],
        "forbidden_loaded_after": [],
        "forbidden_prefixes": [
            "acfqp.domains",
            "acfqp.planning",
            "acfqp.ground",
        ],
        "loaded_acfqp_modules": [],
        "unexpected_module_origins": [],
        "input_regular_files": ["boundary.json", "request.json", "slice.json"],
        "output_regular_files_before": [],
        "claim_boundary": (
            "integrity_and_reproducibility_evidence_only; "
            "not_host_or_process_provenance"
        ),
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            failures.append(f"local runtime attestation field mismatch: {key}")
    return failures


def _isolated_local_replay(
    boundary: dict[str, Any],
    ground_slice: dict[str, Any],
    request: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Replay the three capabilities in a fresh bubblewrap namespace."""

    bubblewrap = shutil.which("bwrap")
    interpreter = shutil.which("python3", path="/usr/bin:/bin")
    if bubblewrap is None or interpreter is None:
        raise ValueError("independent Phase3C verification requires bwrap and system python3")
    with tempfile.TemporaryDirectory(prefix="acfqp-phase3c-verify-local-") as temporary:
        root = Path(temporary)
        runtime = root / "runtime"
        input_root = root / "input"
        output_root = root / "output"
        runtime.mkdir()
        input_root.mkdir()
        output_root.mkdir()
        for name in ("local_solver.py", "local_runtime.py"):
            shutil.copy2(ROOT / "src" / "acfqp" / name, runtime / name)
        (input_root / "boundary.json").write_bytes(_canonical_bytes(boundary))
        (input_root / "slice.json").write_bytes(_canonical_bytes(ground_slice))
        (input_root / "request.json").write_bytes(_canonical_bytes(request))
        system_mounts: list[str] = []
        for path in ("/usr", "/lib", "/lib64"):
            if Path(path).exists():
                system_mounts.extend(("--ro-bind", path, path))
        process = subprocess.run(
            (
                bubblewrap,
                "--unshare-all",
                "--die-with-parent",
                "--new-session",
                "--clearenv",
                *system_mounts,
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "--tmpfs",
                "/tmp",
                "--ro-bind",
                str(runtime),
                "/runtime",
                "--ro-bind",
                str(input_root),
                "/input",
                "--dir",
                "/output",
                "--bind",
                str(output_root),
                "/output",
                "--chdir",
                "/output",
                "--setenv",
                "PATH",
                "/usr/bin:/bin",
                "--setenv",
                "LANG",
                "C.UTF-8",
                "--setenv",
                "ACFQP_FORBIDDEN_ROOTS",
                str(ROOT),
                str(Path(interpreter).resolve()),
                "-B",
                "-S",
                "/runtime/local_runtime.py",
                "--boundary",
                "/input/boundary.json",
                "--slice",
                "/input/slice.json",
                "--request",
                "/input/request.json",
                "--output",
                "/output/result.json",
                "--attestation",
                "/output/attestation.json",
            ),
            cwd=output_root,
            env={"PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if process.returncode != 0 or process.stdout or process.stderr:
            raise ValueError(
                "fresh isolated local replay failed: "
                f"rc={process.returncode}, stdout={process.stdout!r}, "
                f"stderr={process.stderr!r}"
            )
        return (
            _load(output_root / "result.json"),
            _load(output_root / "attestation.json"),
        )


def _request_for_slice(
    request: dict[str, Any], ground_slice: dict[str, Any]
) -> dict[str, Any]:
    payload = dict(request)
    payload.pop("request_id", None)
    payload["slice_id"] = ground_slice["slice_id"]
    payload["slice_sha256"] = _sha256_bytes(_canonical_bytes(ground_slice))
    return {"request_id": object_id(payload, "local-request"), **payload}


def _audit_unique_minimal_localization(
    boundary: dict[str, Any],
    ground_slice: dict[str, Any],
    request: dict[str, Any],
    expected_node_ids: list[str],
) -> list[str]:
    """Exhaust every subset through the first successful cardinality."""

    failures: list[str] = []

    def restricted(cells: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {
            "schema": ground_slice["schema"],
            "frontier_id": ground_slice["frontier_id"],
            "authorization_id": ground_slice["authorization_id"],
            "cells": cells,
        }
        return {**payload, "slice_id": object_id(payload, "authorized-ground-slice")}

    outcomes: dict[tuple[str, ...], bool] = {}
    cells = list(ground_slice["cells"])
    for selected in ([], *([cell] for cell in cells)):
        candidate_slice = restricted(selected)
        candidate_request = _request_for_slice(request, candidate_slice)
        key = tuple(cell["node_id"] for cell in selected)
        try:
            result = solve_local_recovery(boundary, candidate_slice, candidate_request)
            outcomes[key] = result.certified and set(result.localized_node_ids) == set(key)
        except ValueError:
            outcomes[key] = False
    safe_singletons = [key for key, safe in outcomes.items() if len(key) == 1 and safe]
    if outcomes.get((), False):
        failures.append("empty local subset unexpectedly certifies")
    if safe_singletons != [tuple(expected_node_ids)]:
        failures.append(
            "localized frontier subset is not the unique cardinality-minimal certificate"
        )
    return failures


def verify_phase3c(bundle: Path) -> dict[str, Any]:
    """Verify integrity and replay every Phase3C semantic claim."""

    failures = list(verify_artifact_bundle(bundle))
    failures.extend(_stdlib_solver_source_failures())
    recomputed_semantic_hash: str | None = None
    run: dict[str, Any] = {}
    if not (bundle / "manifest.json").is_file():
        return {"verified": False, "failures": tuple(failures)}

    try:
        manifest = _load(bundle / "manifest.json")
        if set(manifest) != {
            "schema",
            "schema_version",
            "required_paths",
            "files",
            "bundle_sha256",
        }:
            failures.append("Phase3C manifest field set mismatch")
        records = {
            record.get("path"): record
            for record in manifest.get("files", [])
            if isinstance(record, dict) and isinstance(record.get("path"), str)
        }
        if set(manifest.get("required_paths", ())) != set(PHASE3C_REQUIRED_PATHS):
            failures.append("Phase3C required-path contract mismatch")
        if set(records) != set(PHASE3C_REQUIRED_PATHS):
            failures.append("Phase3C manifest document set mismatch")
        for path, (role, schema) in PHASE3C_DOCUMENT_CONTRACTS.items():
            record = records.get(path)
            if record is None or record.get("role") != role or record.get("schema") != schema:
                failures.append(f"Phase3C manifest role/schema mismatch: {path}")

        run = _load(bundle / "run.json")
        workload = _load(bundle / "workload/spec.json")
        registry = _load(bundle / "workload/query_registry.json")
        epoch = _load(bundle / "build/epoch.json")
        model_document = _load(bundle / "build/portable_rapm.json")
        query_rows = _load_jsonl(bundle / "campaign/portable_queries.jsonl")
        plan_rows = _load_jsonl(bundle / "campaign/portable_plans.jsonl")
        graph_container = _load(bundle / "campaign/policy_graphs.json")
        pre_documents = _load_jsonl(bundle / "audit/pre_recovery.jsonl")
        proof_document = _load(bundle / "audit/failed_proof_graph.json")
        frontier_document = _load(bundle / "recovery/frontier.json")
        authorization_document = _load(bundle / "recovery/authorization.json")
        ground_slice_document = _load(bundle / "recovery/ground_slice.json")
        boundary_document = _load(bundle / "recovery/boundary_view.json")
        request_document = _load(bundle / "recovery/request.json")
        local_attestation = _load(bundle / "recovery/runtime_attestation.json")
        local_result_document = _load(bundle / "recovery/result.json")
        overlay_document = _load(bundle / "recovery/overlay.json")
        access_trace = _load(bundle / "recovery/access_trace.json")
        post_documents = _load_jsonl(bundle / "audit/post_recovery.jsonl")
        route_certificates = _load_jsonl(bundle / "result/route_certificates.jsonl")
        report = _load(bundle / "result/local_recovery_report.json")
        j0_rows = _load_jsonl(bundle / "evaluation/j0_rows.jsonl")
        locality_document = _load(bundle / "evaluation/locality.json")
        counters_document = _load(bundle / "accounting/work_counters.json")
        metrics_document = _load(bundle / "metrics.json")
        events_document = _load_jsonl(bundle / "events.jsonl")

        # Authority reconstruction: kernel, coverage, eleven-cell partition,
        # exact envelope, and portable RAPM are rebuilt without bundle input.
        world = construct_phase3c_world()
        authoritative_model = world.portable.model
        try:
            loaded_model = PortableRAPM.from_dict(model_document)
            if loaded_model.model_id != loaded_model.recompute_model_id():
                failures.append("base portable model ID does not recompute")
        except (TypeError, ValueError) as error:
            failures.append(f"base portable model is invalid: {error}")
        _expect(failures, "base portable model", model_document, authoritative_model.to_dict())
        expected_base_model_byte_sha256 = _sha256_bytes(
            _artifact_json_bytes(authoritative_model.to_dict())
        )
        expected_base_epoch_byte_sha256 = _sha256_bytes(
            _artifact_json_bytes(world.build_epoch)
        )
        if sha256_file(bundle / "build/portable_rapm.json") != expected_base_model_byte_sha256:
            failures.append("base portable model serialization/byte hash changed")
        if sha256_file(bundle / "build/epoch.json") != expected_base_epoch_byte_sha256:
            failures.append("base BuildEpoch serialization/byte hash changed")
        _expect(failures, "immutable BuildEpoch", epoch, world.build_epoch)

        proposals: list[dict[str, Any]] = []
        for registered in world.queries:
            portable_query = world.portable.query_from_spec(registered.query)
            result = solve_portable_pareto(authoritative_model, portable_query)
            proposal, source = _select_recovery_proposal(result)
            proposals.append(
                {
                    "registered": registered,
                    "ground_query_id": object_id(registered.query, "query"),
                    "portable_query": portable_query,
                    "result": result,
                    "proposal": proposal,
                    "source": source,
                }
            )
        if len(query_rows) != 2 or len(plan_rows) != 2:
            failures.append("Phase3C portable campaign must contain exactly two rows")

        workload_payload = {
            "profile_key": PROFILE_KEY,
            "build_epoch_id": world.build_epoch["build_epoch_id"],
            "portable_rapm_id": authoritative_model.model_id,
            "coverage_id": authoritative_model.coverage_id,
            "ordered_ground_query_ids": tuple(p["ground_query_id"] for p in proposals),
            "ordered_query_keys": tuple(p["registered"].query_key for p in proposals),
            "expected_routes": ("ABSTRACT_CERTIFIED", "LOCAL_GROUND_RECOVERY"),
            "query_occurrence_count": 2,
            "all_portable_proposals_before_local_recovery": True,
            "all_portable_proposals_before_j0": True,
            "base_model_mutation_allowed": False,
            "fallback_allowed": False,
            "rebuild_allowed_for_pass": False,
        }
        expected_workload = {
            "workload_id": object_id(workload_payload, "workload"),
            **workload_payload,
        }
        _expect(failures, "WorkloadSpec/content ID", workload, expected_workload)
        occurrence_ids = tuple(
            object_id(
                {
                    "workload_id": expected_workload["workload_id"],
                    "ordinal": ordinal,
                    "ground_query_id": proposal["ground_query_id"],
                    "portable_query_id": proposal["portable_query"].query_id,
                    "portable_model_id": authoritative_model.model_id,
                },
                "occurrence",
            )
            for ordinal, proposal in enumerate(proposals, start=1)
        )
        expected_registry = {
            "records": tuple(
                {
                    "ordinal": ordinal,
                    "occurrence_id": occurrence_id,
                    "query_key": proposal["registered"].query_key,
                    "ground_query_id": proposal["ground_query_id"],
                    "ground_query": _query_payload(proposal["registered"].query),
                    "portable_query_id": proposal["portable_query"].query_id,
                    "portable_model_id": authoritative_model.model_id,
                    "expected_route": proposal["registered"].expected_route,
                }
                for ordinal, (occurrence_id, proposal) in enumerate(
                    zip(occurrence_ids, proposals, strict=True), start=1
                )
            ),
            "same_base_model_for_every_query": True,
            "query_values_used_to_mutate_base_model": False,
        }
        _expect(failures, "ground/portable query registry", registry, expected_registry)

        expected_query_rows = tuple(
            {
                "occurrence_id": occurrence_id,
                "query_key": proposal["registered"].query_key,
                "ground_query_id": proposal["ground_query_id"],
                "portable_query_id": proposal["portable_query"].query_id,
                "portable_query": proposal["portable_query"].to_dict(),
            }
            for occurrence_id, proposal in zip(occurrence_ids, proposals, strict=True)
        )
        _expect(failures, "portable query stream", query_rows, expected_query_rows)
        for index, (actual, proposal, occurrence_id) in enumerate(
            zip(plan_rows, proposals, occurrence_ids, strict=True)
        ):
            portable_query = proposal["portable_query"]
            result = proposal["result"]
            try:
                parsed = PortablePlanResult.from_dict(
                    actual.get("plan_result"),
                    model=authoritative_model,
                    query=portable_query,
                )
                if parsed.to_dict() != result.to_dict():
                    failures.append(f"portable plan replay mismatch at row {index}")
            except (TypeError, ValueError) as error:
                failures.append(f"portable plan result invalid at row {index}: {error}")
            expected_plan_fields = {
                "occurrence_id": occurrence_id,
                "query_key": proposal["registered"].query_key,
                "ground_query_id": proposal["ground_query_id"],
                "portable_query_id": portable_query.query_id,
                "portable_model_id": authoritative_model.model_id,
                "portable_result_id": result.result_id,
                "plan_result": result.to_dict(),
                "proposal_source": proposal["source"],
                "proposal_policy": proposal["proposal"].policy.to_dict(),
                "fresh_process": True,
                "ground_kernel_available_to_planner": False,
                "ground_j0_available_to_planner": False,
            }
            for key, expected in expected_plan_fields.items():
                if actual.get(key) != to_jsonable(expected):
                    failures.append(f"portable plan field mismatch at row {index}: {key}")
            isolated_plan, isolated_attestation = _isolated_portable_replay(
                authoritative_model, portable_query
            )
            _expect(
                failures,
                f"fresh isolated portable planner result at row {index}",
                isolated_plan,
                result.to_dict(),
            )
            _expect(
                failures,
                f"fresh isolated portable runtime attestation/reuse binding at row {index}",
                actual.get("runtime_attestation"),
                isolated_attestation,
            )
            failures.extend(
                _validate_portable_attestation(
                    actual.get("runtime_attestation"),
                    model=authoritative_model,
                    query=portable_query,
                    result=result,
                )
            )

        # Translate replayed portable selectors back through the ephemeral
        # construction registry, then recompute both pre-recovery certificates.
        frozen = []
        for proposal in proposals:
            # _decode_policy needs the FrozenPortableProposal interface only.
            class _Frozen:
                pass

            item = _Frozen()
            item.proposal = proposal["proposal"]
            item.registered = proposal["registered"]
            item.ground_query_id = proposal["ground_query_id"]
            item.portable_query = proposal["portable_query"]
            item.result = proposal["result"]
            item.proposal_source = proposal["source"]
            frozen.append(item)
        policies = tuple(_decode_policy(world, item) for item in frozen)
        expected_graphs = tuple(
            _policy_graph_document(world, item, policy)
            for item, policy in zip(frozen, policies, strict=True)
        )
        _expect(
            failures,
            "pre-recovery policy graphs",
            graph_container,
            {"policy_graphs": expected_graphs},
        )
        audits = tuple(
            audit_abstract_policy(
                world.kernel,
                item.registered.query,
                world.models.envelope,
                policy,
                regret_tolerance=Fraction(1, 20),
            )
            for item, policy in zip(frozen, policies, strict=True)
        )
        expected_pre = tuple(
            _audit_document(
                audit=audit,
                query_key=item.registered.query_key,
                query_id=item.ground_query_id,
                policy_graph_id=graph["policy_graph_id"],
                model_id=authoritative_model.model_id,
                stage="pre_recovery",
            )
            for item, graph, audit in zip(frozen, expected_graphs, audits, strict=True)
        )
        _expect(failures, "pre-recovery abstract audits", pre_documents, expected_pre)
        if not audits[0].certified or audits[1].certified:
            failures.append("independent pre-recovery route classification changed")

        local_item = frozen[1]
        local_policy = policies[1]
        proof_graph = build_failed_proof_graph(
            world.kernel,
            local_item.registered.query,
            world.models.envelope,
            local_policy,
            audits[1],
        )
        frontier = proof_graph.frontier()
        state_ids = {
            state: object_id(state, "state") for state in world.coverage.covered_states
        }
        expected_proof = _proof_graph_document(
            proof_graph,
            pre_audit_id=expected_pre[1]["audit_id"],
            state_ids=state_ids,
        )
        expected_frontier = _frontier_document(
            frontier, world, expected_proof, state_ids
        )
        _expect(failures, "complete DirectBad proof DAG/witness inventory", proof_document, expected_proof)
        _expect(failures, "earliest DirectBad frontier", frontier_document, expected_frontier)
        if (
            len(proof_graph.nodes) != 4
            or len(proof_graph.direct_bad_nodes) != 2
            or len(proof_graph.inherited_bad_nodes) != 2
            or len(frontier.nodes) != 2
            or any(node.remaining != 1 or not node.direct_bad for node in frontier.nodes)
        ):
            failures.append("DirectBad/inherited frontier golden changed")

        authorization = LocalRecoveryAuthorization.for_frontier(
            world.kernel,
            world.models.envelope,
            frontier,
            proof_graph,
        )
        expected_authorization = _authorization_document(
            authorization,
            model_id=authoritative_model.model_id,
            query_id=local_item.ground_query_id,
        )
        _expect(failures, "40-SA proof authorization", authorization_document, expected_authorization)
        if (
            len(authorization.frontier_state_actions) != 32
            or len(authorization.reverse_dependency_state_actions) != 8
            or len(authorization.allowed_state_actions) != 40
        ):
            failures.append("40-SA authorization golden changed")

        expected_materialized_slice = materialize_authorized_slice(
            world.kernel,
            local_item.registered.query,
            world.models.envelope,
            frontier,
            authorization,
            state_payload=lambda state: {"board": state.board, "status": state.status.value},
            action_payload=lambda action: {
                "first": action.first,
                "second": action.second,
                "survivor": action.survivor,
            },
        )
        expected_slice = redact_authorized_slice_for_worker(
            expected_materialized_slice
        )
        expected_boundary = build_redacted_boundary_view(
            local_item.registered.query,
            world.models.envelope,
            local_policy,
            proof_graph,
            unrestricted_reward_upper=audits[1].unrestricted_reward_upper,
            regret_tolerance=Fraction(1, 20),
        )
        _expect(failures, "frontier-only authorized ground slice", ground_slice_document, expected_slice)
        _expect(failures, "redacted abstract boundary view", boundary_document, expected_boundary)

        request_payload = {
            "schema": "acfqp.local_recovery_request.v1",
            "workload_id": expected_workload["workload_id"],
            "occurrence_id": occurrence_ids[1],
            "portable_model_id": authoritative_model.model_id,
            "build_epoch_id": world.build_epoch["build_epoch_id"],
            "ground_query_id": local_item.ground_query_id,
            "portable_query_id": local_item.portable_query.query_id,
            "portable_result_id": local_item.result.result_id,
            "pre_audit_id": expected_pre[1]["audit_id"],
            "failed_proof_graph_id": proof_graph.graph_id,
            "frontier_id": frontier.frontier_id,
            "authorization_id": authorization.authorization_id,
            "slice_id": expected_slice["slice_id"],
            "slice_sha256": _sha256_bytes(_canonical_bytes(expected_slice)),
            "boundary_view_id": expected_boundary["boundary_view_id"],
            "boundary_sha256": _sha256_bytes(_canonical_bytes(expected_boundary)),
            "worker_inputs": ["boundary.json", "request.json", "slice.json"],
            "portable_rapm_mounted_to_worker": False,
            "ground_kernel_mounted_to_worker": False,
            "coverage_graph_mounted_to_worker": False,
            "j0_mounted_to_worker": False,
            "project_checkout_mounted_to_worker": False,
            "grammar_used": False,
            "selection_rule": (
                "cardinality_minimum_localized_frontier_nodes_then_exact_"
                "failure_reward_action_id_then_value_risk_certificate"
            ),
        }
        expected_request = {
            "request_id": object_id(request_payload, "local-request"),
            **request_payload,
        }
        _expect(failures, "content-addressed local recovery request", request_document, expected_request)

        expected_local_result = solve_local_recovery(
            expected_boundary, expected_slice, expected_request
        ).to_dict()
        _expect(failures, "stdlib local solver replay", local_result_document, expected_local_result)
        failures.extend(
            _audit_unique_minimal_localization(
                expected_boundary,
                expected_slice,
                expected_request,
                expected_local_result["localized_node_ids"],
            )
        )
        isolated_result, isolated_attestation = _isolated_local_replay(
            expected_boundary, expected_slice, expected_request
        )
        _expect(failures, "fresh isolated local solver result", isolated_result, expected_local_result)
        _expect(
            failures,
            "fresh isolated local runtime attestation/reuse binding",
            local_attestation,
            isolated_attestation,
        )
        failures.extend(
            _validate_local_attestation(
                local_attestation,
                boundary=expected_boundary,
                ground_slice=expected_slice,
                request=expected_request,
                result=expected_local_result,
            )
        )

        overlay = _overlay_from_result(
            world,
            local_item,
            local_policy,
            frontier,
            authorization,
            expected_local_result,
        )
        post_audit = audit_hybrid_policy(
            world.kernel,
            local_item.registered.query,
            world.models.envelope,
            overlay,
            regret_tolerance=Fraction(1, 20),
        )
        hybrid_lift = lift_hybrid_policy(
            world.kernel,
            local_item.registered.query,
            world.models.envelope,
            overlay,
        )
        abstract_overlay = HybridPolicyOverlay(
            policies[0],
            (),
            frozen[0].ground_query_id,
            "not-applicable-certified-plan",
        )
        abstract_lift = lift_hybrid_policy(
            world.kernel,
            frozen[0].registered.query,
            world.models.envelope,
            abstract_overlay,
        )
        expected_post = _audit_document(
            audit=post_audit,
            query_key=local_item.registered.query_key,
            query_id=local_item.ground_query_id,
            policy_graph_id=expected_graphs[1]["policy_graph_id"],
            model_id=authoritative_model.model_id,
            stage="post_local_recovery",
        )
        expected_post.update(
            {
                "overlay_id": overlay.overlay_id,
                "local_result_id": expected_local_result["result_id"],
                "exact_hybrid_reward": hybrid_lift.evaluation.expected_reward,
                "exact_hybrid_failure": hybrid_lift.evaluation.failure_probability,
            }
        )
        expected_post["post_recovery_audit_id"] = object_id(
            expected_post, "post-recovery-audit"
        )
        _expect(failures, "post-recovery full-authority audit", post_documents, (expected_post,))
        if (
            not post_audit.certified
            or post_audit.lifted_failure_upper != Fraction(397, 20000)
            or hybrid_lift.evaluation.failure_probability != Fraction(317, 16000)
            or hybrid_lift.patched_decision_count != 8
            or hybrid_lift.abstract_decision_count != 12
        ):
            failures.append("hybrid re-certification/value golden changed")

        localized_node_ids = set(expected_local_result["localized_node_ids"])
        localized_nodes = tuple(node for node in frontier.nodes if node.node_id in localized_node_ids)
        localized_states = tuple(
            state
            for node in localized_nodes
            for state in world.partition.members(node.cell)
            if not world.kernel.is_terminal(state)
        )
        localized_pairs = tuple(
            (state, action)
            for state in localized_states
            for action in world.kernel.actions(state)
        )
        localized_outcomes = sum(
            len(world.kernel.step(state, action)) for state, action in localized_pairs
        )
        ground_distinction_changes = 0
        for decision in overlay.decisions:
            abstract_action = local_policy.action(decision.cell, decision.remaining)
            support = {
                action
                for _, action in world.models.envelope.concretizer(
                    decision.state, abstract_action
                )
            }
            ground_distinction_changes += int(decision.action not in support)
        base_model_sha256 = expected_base_model_byte_sha256
        hybrid_payload = {
            "schema": "acfqp.hybrid_policy_overlay.v1",
            "overlay_id": overlay.overlay_id,
            "request_id": expected_request["request_id"],
            "local_result_id": expected_local_result["result_id"],
            "frontier_id": frontier.frontier_id,
            "ground_query_id": local_item.ground_query_id,
            "base_portable_model_id_before": authoritative_model.model_id,
            "base_portable_model_id_after": authoritative_model.model_id,
            "base_build_epoch_id_before": world.build_epoch["build_epoch_id"],
            "base_build_epoch_id_after": world.build_epoch["build_epoch_id"],
            "base_build_epoch_sha256_before": expected_base_epoch_byte_sha256,
            "base_build_epoch_sha256_after": expected_base_epoch_byte_sha256,
            "base_model_sha256_before": base_model_sha256,
            "base_model_sha256_after": base_model_sha256,
            "base_policy_graph_id": expected_graphs[1]["policy_graph_id"],
            "localized_node_ids": tuple(expected_local_result["localized_node_ids"]),
            "decisions": tuple(
                {
                    "remaining": decision.remaining,
                    "cell": repr(decision.cell),
                    "state_id": object_id(decision.state, "state"),
                    "action_id": object_id(decision.action, "ground-action"),
                }
                for decision in overlay.decisions
            ),
            "localized_state_count": len(localized_states),
            "localized_available_state_action_count": len(localized_pairs),
            "localized_available_outcome_count": localized_outcomes,
            "patch_decision_count": len(overlay.decisions),
            "ground_distinction_changes_from_base_concretizer": ground_distinction_changes,
            "retained_abstract_ground_decision_count": hybrid_lift.abstract_decision_count,
            "grammar_used": False,
            "portable_rapm_rebuilt": False,
            "query_scoped": True,
            "post_recovery_audit_id": expected_post["post_recovery_audit_id"],
        }
        expected_overlay = {
            "hybrid_policy_graph_id": object_id(hybrid_payload, "hybrid-policy-graph"),
            **hybrid_payload,
        }
        _expect(failures, "query-scoped overlay/patch scope", overlay_document, expected_overlay)

        route_payloads = (
            {
                "query_key": frozen[0].registered.query_key,
                "occurrence_id": occurrence_ids[0],
                "ground_query_id": frozen[0].ground_query_id,
                "portable_query_id": frozen[0].portable_query.query_id,
                "portable_model_id": authoritative_model.model_id,
                "build_epoch_id": world.build_epoch["build_epoch_id"],
                "route": "ABSTRACT_CERTIFIED",
                "pre_audit_id": expected_pre[0]["audit_id"],
                "hybrid_policy_graph_id": None,
                "local_ground_nodes": (),
                "certified": True,
                "reward_lower": audits[0].lifted_reward_lower,
                "failure_upper": audits[0].lifted_failure_upper,
                "regret_upper": audits[0].regret_upper,
                "risk_tolerance": audits[0].risk_tolerance,
                "full_ground_fallback_invocations": 0,
                "rebuild_invocations": 0,
            },
            {
                "query_key": local_item.registered.query_key,
                "occurrence_id": occurrence_ids[1],
                "ground_query_id": local_item.ground_query_id,
                "portable_query_id": local_item.portable_query.query_id,
                "portable_model_id": authoritative_model.model_id,
                "build_epoch_id": world.build_epoch["build_epoch_id"],
                "route": "LOCAL_GROUND_RECOVERY",
                "pre_audit_id": expected_pre[1]["audit_id"],
                "failed_proof_graph_id": proof_graph.graph_id,
                "frontier_id": frontier.frontier_id,
                "authorization_id": authorization.authorization_id,
                "local_request_id": expected_request["request_id"],
                "local_result_id": expected_local_result["result_id"],
                "hybrid_policy_graph_id": expected_overlay["hybrid_policy_graph_id"],
                "post_recovery_audit_id": expected_post["post_recovery_audit_id"],
                "local_ground_nodes": tuple(expected_local_result["localized_node_ids"]),
                "certified": True,
                "reward_lower": post_audit.lifted_reward_lower,
                "failure_upper": post_audit.lifted_failure_upper,
                "regret_upper": post_audit.regret_upper,
                "risk_tolerance": post_audit.risk_tolerance,
                "full_ground_fallback_invocations": 0,
                "rebuild_invocations": 0,
            },
        )
        expected_routes = tuple(
            {"certificate_id": object_id(payload, "route-certificate"), **payload}
            for payload in route_payloads
        )
        _expect(failures, "terminal route certificates", route_certificates, expected_routes)
        terminal_payload = {
            "workload_id": expected_workload["workload_id"],
            "route_certificate_ids": tuple(row["certificate_id"] for row in expected_routes),
            "hybrid_policy_graph_id": expected_overlay["hybrid_policy_graph_id"],
            "base_portable_model_id": authoritative_model.model_id,
            "base_build_epoch_id": world.build_epoch["build_epoch_id"],
        }
        terminal_freeze_id = object_id(terminal_payload, "terminal-plan-freeze")

        # J0 is deliberately below terminal-plan reconstruction in this
        # verifier, mirroring the authority boundary encoded by the event log.
        ground_results = tuple(
            solve_ground_pareto(world.kernel, item.registered.query) for item in frozen
        )
        if any(result.selected is None for result in ground_results):
            raise ValueError("independent J0 unexpectedly infeasible")
        ground_points = tuple(result.selected for result in ground_results)
        lifts = (abstract_lift, hybrid_lift)
        expected_j0 = tuple(
            {
                "query_key": item.registered.query_key,
                "occurrence_id": occurrence_id,
                "ground_query_id": item.ground_query_id,
                "route_certificate_id": certificate["certificate_id"],
                "terminal_plan_freeze_id": terminal_freeze_id,
                "j0_started_after_terminal_plan_freeze": True,
                "j0_dependency_role": "evaluation_only",
                "ground_expected_reward": ground.expected_reward,
                "ground_failure_probability": ground.failure_probability,
                "lifted_expected_reward": lift.evaluation.expected_reward,
                "lifted_failure_probability": lift.evaluation.failure_probability,
                "reward_gap": ground.expected_reward - lift.evaluation.expected_reward,
                "failure_gap": lift.evaluation.failure_probability - ground.failure_probability,
                "abstract_composed_candidate_count": item.result.composed_candidate_count,
                "ground_composed_candidate_count": result.composed_candidate_count,
            }
            for item, occurrence_id, certificate, ground, result, lift in zip(
                frozen,
                occurrence_ids,
                expected_routes,
                ground_points,
                ground_results,
                lifts,
                strict=True,
            )
        )
        _expect(failures, "evaluation-only J0 rows", j0_rows, expected_j0)

        full_query_counts = _same_query_all_action_counts(
            world.kernel, local_item.registered.query
        )
        frontier_outcomes = sum(
            len(world.kernel.step(state, action))
            for state, action in authorization.frontier_state_actions
        )
        reverse_outcomes = sum(
            len(world.kernel.step(state, action))
            for state, action in authorization.reverse_dependency_state_actions
        )
        coverage_outcomes = sum(
            len(world.kernel.step(state, action))
            for state in world.coverage.covered_states
            if not world.kernel.is_terminal(state)
            for action in world.kernel.actions(state)
        )
        expected_locality = {
            "portable_model_id_before": authoritative_model.model_id,
            "portable_model_id_after": authoritative_model.model_id,
            "build_epoch_id_before": world.build_epoch["build_epoch_id"],
            "build_epoch_id_after": world.build_epoch["build_epoch_id"],
            "base_build_epoch_sha256_before": expected_base_epoch_byte_sha256,
            "base_build_epoch_sha256_after": expected_base_epoch_byte_sha256,
            "base_model_sha256_before": base_model_sha256,
            "base_model_sha256_after": base_model_sha256,
            "coverage_ground_states": len(world.coverage.covered_states),
            "coverage_ground_state_action_pairs": world.build_epoch["ground_state_action_pairs"],
            "coverage_positive_probability_outcomes": coverage_outcomes,
            "full_same_query_all_action_graph": full_query_counts,
            "frontier_states": expected_frontier["frontier_state_count"],
            "frontier_state_action_pairs": len(authorization.frontier_state_actions),
            "frontier_positive_probability_outcomes": frontier_outcomes,
            "reverse_selected_dependency_state_action_pairs": len(authorization.reverse_dependency_state_actions),
            "reverse_selected_dependency_positive_probability_outcomes": reverse_outcomes,
            "authorized_state_action_pairs": len(authorization.allowed_state_actions),
            "authorized_positive_probability_outcomes": frontier_outcomes + reverse_outcomes,
            "worker_mounted_state_action_pairs": len(authorization.frontier_state_actions),
            "worker_mounted_reverse_dependencies": False,
            "localized_states": len(localized_states),
            "localized_available_state_action_pairs": len(localized_pairs),
            "localized_available_positive_probability_outcomes": localized_outcomes,
            "patch_decisions": len(overlay.decisions),
            "ground_distinction_changes_from_base_concretizer": ground_distinction_changes,
            "retained_abstract_ground_decisions": hybrid_lift.abstract_decision_count,
            "retained_abstract_cell_horizon_pairs": 3,
            "strict_worker_locality": len(authorization.frontier_state_actions) < full_query_counts["state_action_pairs"],
            "strict_authorization_locality": len(authorization.allowed_state_actions) < full_query_counts["state_action_pairs"],
            "strict_coverage_locality": len(authorization.allowed_state_actions) < world.build_epoch["ground_state_action_pairs"],
            "hybrid_retains_abstract_planning": hybrid_lift.abstract_decision_count > 0,
            "base_rapm_immutable": True,
            "coverage_extended": False,
            "full_ground_fallback_invocations": 0,
            "rebuild_invocations": 0,
        }
        _expect(failures, "strict locality accounting", locality_document, expected_locality)

        expected_access = {
            "authorization_id": authorization.authorization_id,
            "slice_id": expected_slice["slice_id"],
            "runtime_attestation_id": local_attestation.get("attestation_id"),
            "trusted_slice_materializer_access_log": expected_materialized_slice["access_log"],
            "trusted_slice_actions_calls": sum(row["operation"] == "actions" for row in expected_materialized_slice["access_log"]),
            "trusted_slice_step_calls": sum(row["operation"] == "step" for row in expected_materialized_slice["access_log"]),
            "worker_input_state_action_rows": len(authorization.frontier_state_actions),
            "reverse_dependency_rows_mounted_to_worker": 0,
            "worker_read_outside_slice": False,
            "project_checkout_visible": False,
            "portable_rapm_visible": False,
            "ground_kernel_visible": False,
            "coverage_visible": False,
            "j0_visible": False,
        }
        _expect(failures, "authorized kernel access trace", access_trace, expected_access)

        def realization_rows(audit: Any, policy: Any) -> int:
            total = 0
            for bound in audit.reachable_bounds:
                if bound.remaining <= 0 or all(
                    world.kernel.is_terminal(state)
                    for state in world.partition.members(bound.cell)
                ):
                    continue
                total += len(
                    world.models.envelope.realizations(
                        bound.cell, policy.action(bound.cell, bound.remaining)
                    )
                )
            return total

        post_behavior_rows = 0
        for bound in post_audit.reachable_bounds:
            if bound.remaining <= 0 or all(
                world.kernel.is_terminal(state)
                for state in world.partition.members(bound.cell)
            ):
                continue
            if overlay.is_localized(bound.cell, bound.remaining):
                post_behavior_rows += sum(
                    not world.kernel.is_terminal(state)
                    for state in world.partition.members(bound.cell)
                )
            else:
                post_behavior_rows += len(
                    world.models.envelope.realizations(
                        bound.cell,
                        local_policy.action(bound.cell, bound.remaining),
                    )
                )
        runtime_model_bytes = len(_canonical_bytes(authoritative_model.to_dict()))
        artifact_model_bytes = len(_artifact_json_bytes(authoritative_model.to_dict()))
        artifact_epoch_bytes = len(_artifact_json_bytes(world.build_epoch))
        worker_slice_bytes = len(_canonical_bytes(expected_slice))
        worker_boundary_bytes = len(_canonical_bytes(expected_boundary))
        worker_request_bytes = len(_canonical_bytes(expected_request))
        worker_result_bytes = len(_canonical_bytes(expected_local_result))
        portable_query_bytes = tuple(
            len(_canonical_bytes(item.portable_query.to_dict())) for item in frozen
        )
        abstract_realization_counts = tuple(
            realization_rows(audit, policy)
            for audit, policy in zip(audits, policies, strict=True)
        )

        expected_counters = {
            "cost_protocol_status": ECONOMICS_NOT_RUN,
            "scalar_break_even": None,
            "build": {
                "build_invocations": 1,
                "covered_ground_states": len(world.coverage.covered_states),
                "ground_state_action_pairs": world.build_epoch["ground_state_action_pairs"],
                "ground_one_step_outcomes": coverage_outcomes,
                "abstract_cells": len(world.partition.cell_ids),
                "abstract_state_action_pairs": len(world.models.nominal.entries),
                "construction_refinement_splits": 1,
                "portable_model_runtime_input_bytes": runtime_model_bytes,
                "portable_model_artifact_bytes": artifact_model_bytes,
                "build_epoch_artifact_bytes": artifact_epoch_bytes,
            },
            "query": (
                {
                    "occurrence_id": occurrence_ids[0],
                    "route": "ABSTRACT_CERTIFIED",
                    "portable_model_load_invocations": 1,
                    "portable_model_loaded_bytes": runtime_model_bytes,
                    "portable_query_load_invocations": 1,
                    "portable_query_loaded_bytes": portable_query_bytes[0],
                    "abstract_plan_invocations": 1,
                    "abstract_plan_composed_candidates": frozen[0].result.composed_candidate_count,
                    "pre_certificate_proof_nodes": len(audits[0].reachable_bounds),
                    "pre_certificate_audit_invocations": 1,
                    "pre_certificate_realization_rows": abstract_realization_counts[0],
                    "frontier_extraction_invocations": 0,
                    "frontier_state_action_pairs": 0,
                    "authorized_state_action_pairs": 0,
                    "slice_materialization_invocations": 0,
                    "local_runtime_invocations": 0,
                    "local_solver_candidate_subsets": 0,
                    "patch_decisions": 0,
                    "hybrid_stitch_invocations": 0,
                    "post_certificate_audit_invocations": 0,
                    "full_fallback_invocations": 0,
                    "rebuild_invocations": 0,
                    "evaluation_only_j0_invocations": 1,
                    "evaluation_only_j0_composed_candidates": ground_results[0].composed_candidate_count,
                    "base_load": {
                        "model_invocations": 1,
                        "model_bytes": runtime_model_bytes,
                        "query_invocations": 1,
                        "query_bytes": portable_query_bytes[0],
                    },
                    "abstract_plan": {
                        "invocations": 1,
                        "composed_candidates": frozen[0].result.composed_candidate_count,
                        "frontier_points": len(frozen[0].result.frontier),
                        "selected_policy_decisions": len(frozen[0].proposal.policy.decisions),
                    },
                    "pre_certificate_audit": {
                        "invocations": 1,
                        "cell_horizon_pairs": len(audits[0].reachable_bounds),
                        "realization_rows": abstract_realization_counts[0],
                    },
                    "frontier_extraction": {"invocations": 0, "nodes": 0},
                    "slice_materialization": {
                        "invocations": 0,
                        "state_action_pairs": 0,
                        "positive_probability_outcomes": 0,
                        "worker_bytes": 0,
                    },
                    "isolated_local_plan": {
                        "invocations": 0,
                        "candidate_subsets": 0,
                        "input_bytes": 0,
                        "result_bytes": 0,
                    },
                    "hybrid_stitch": {
                        "invocations": 0,
                        "patch_decisions": 0,
                        "retained_abstract_ground_decisions": 0,
                    },
                    "post_certificate_audit": {
                        "invocations": 0,
                        "cell_horizon_pairs": 0,
                        "behavior_rows": 0,
                    },
                    "fallback": {"invocations": 0, "composed_candidates": 0},
                    "rebuild": {"invocations": 0},
                    "evaluation_only_j0": {
                        "invocations": 1,
                        "composed_candidates": ground_results[0].composed_candidate_count,
                    },
                },
                {
                    "occurrence_id": occurrence_ids[1],
                    "route": "LOCAL_GROUND_RECOVERY",
                    "portable_model_load_invocations": 1,
                    "portable_model_loaded_bytes": runtime_model_bytes,
                    "portable_query_load_invocations": 1,
                    "portable_query_loaded_bytes": portable_query_bytes[1],
                    "abstract_plan_invocations": 1,
                    "abstract_plan_composed_candidates": frozen[1].result.composed_candidate_count,
                    "pre_certificate_proof_nodes": len(proof_graph.nodes),
                    "pre_certificate_proof_edges": len(proof_graph.edges),
                    "pre_certificate_audit_invocations": 1,
                    "pre_certificate_realization_rows": abstract_realization_counts[1],
                    "complete_realization_pair_witnesses": sum(len(node.witnesses) for node in proof_graph.nodes),
                    "positive_failed_witnesses": expected_proof["positive_witness_count"],
                    "direct_failed_nodes": len(proof_graph.direct_bad_nodes),
                    "inherited_failed_nodes": len(proof_graph.inherited_bad_nodes),
                    "frontier_extraction_invocations": 1,
                    "frontier_nodes": len(frontier.nodes),
                    "frontier_states": expected_frontier["frontier_state_count"],
                    "frontier_state_action_pairs": len(authorization.frontier_state_actions),
                    "frontier_positive_probability_outcomes": frontier_outcomes,
                    "reverse_dependency_state_action_pairs": len(authorization.reverse_dependency_state_actions),
                    "reverse_dependency_positive_probability_outcomes": reverse_outcomes,
                    "authorized_state_action_pairs": len(authorization.allowed_state_actions),
                    "authorization_invocations": 1,
                    "slice_materialization_invocations": 1,
                    "worker_slice_bytes": worker_slice_bytes,
                    "worker_boundary_bytes": worker_boundary_bytes,
                    "worker_request_bytes": worker_request_bytes,
                    "local_runtime_invocations": 1,
                    "local_runtime_result_bytes": worker_result_bytes,
                    "local_solver_candidate_subsets": expected_local_result["candidate_subset_count"],
                    "local_solver_action_rows": len(authorization.frontier_state_actions),
                    "patch_decisions": len(overlay.decisions),
                    "localized_available_state_action_pairs": len(localized_pairs),
                    "hybrid_stitch_invocations": 1,
                    "hybrid_retained_abstract_ground_decisions": hybrid_lift.abstract_decision_count,
                    "post_certificate_audit_invocations": 1,
                    "post_certificate_reachable_pairs": len(post_audit.reachable_bounds),
                    "post_certificate_behavior_rows": post_behavior_rows,
                    "full_fallback_invocations": 0,
                    "rebuild_invocations": 0,
                    "evaluation_only_j0_invocations": 1,
                    "evaluation_only_j0_composed_candidates": ground_results[1].composed_candidate_count,
                    "base_load": {
                        "model_invocations": 1,
                        "model_bytes": runtime_model_bytes,
                        "query_invocations": 1,
                        "query_bytes": portable_query_bytes[1],
                    },
                    "abstract_plan": {
                        "invocations": 1,
                        "composed_candidates": frozen[1].result.composed_candidate_count,
                        "frontier_points": len(frozen[1].result.frontier),
                        "selected_policy_decisions": len(frozen[1].proposal.policy.decisions),
                    },
                    "pre_certificate_audit": {
                        "invocations": 1,
                        "cell_horizon_pairs": len(audits[1].reachable_bounds),
                        "realization_rows": abstract_realization_counts[1],
                        "proof_nodes": len(proof_graph.nodes),
                        "proof_edges": len(proof_graph.edges),
                        "witnesses": sum(len(node.witnesses) for node in proof_graph.nodes),
                    },
                    "frontier_extraction": {
                        "invocations": 1,
                        "direct_failed_nodes": len(proof_graph.direct_bad_nodes),
                        "inherited_failed_nodes": len(proof_graph.inherited_bad_nodes),
                        "frontier_nodes": len(frontier.nodes),
                        "frontier_states": expected_frontier["frontier_state_count"],
                    },
                    "slice_materialization": {
                        "invocations": 1,
                        "state_action_pairs": len(authorization.frontier_state_actions),
                        "positive_probability_outcomes": frontier_outcomes,
                        "worker_bytes": worker_slice_bytes,
                        "trusted_actions_calls": expected_access["trusted_slice_actions_calls"],
                        "trusted_step_calls": expected_access["trusted_slice_step_calls"],
                    },
                    "isolated_local_plan": {
                        "invocations": 1,
                        "candidate_subsets": expected_local_result["candidate_subset_count"],
                        "action_rows": len(authorization.frontier_state_actions),
                        "input_bytes": worker_slice_bytes + worker_boundary_bytes + worker_request_bytes,
                        "result_bytes": worker_result_bytes,
                    },
                    "hybrid_stitch": {
                        "invocations": 1,
                        "patch_decisions": len(overlay.decisions),
                        "localized_cell_horizon_pairs": len(overlay.localized_cell_horizon_pairs),
                        "retained_abstract_ground_decisions": hybrid_lift.abstract_decision_count,
                    },
                    "post_certificate_audit": {
                        "invocations": 1,
                        "cell_horizon_pairs": len(post_audit.reachable_bounds),
                        "behavior_rows": post_behavior_rows,
                    },
                    "fallback": {"invocations": 0, "composed_candidates": 0},
                    "rebuild": {"invocations": 0},
                    "evaluation_only_j0": {
                        "invocations": 1,
                        "composed_candidates": ground_results[1].composed_candidate_count,
                    },
                },
            ),
            "reconciliation": {
                "query_occurrence_count": 2,
                "abstract_certified_routes": 1,
                "local_ground_recovery_routes": 1,
                "full_ground_fallback_routes": 0,
                "rebuild_required_routes": 0,
                "infeasible_query_routes": 0,
                "portable_model_load_invocations": 2,
                "portable_query_load_invocations": 2,
                "abstract_plan_invocations": 2,
                "pre_certificate_audit_invocations": 2,
                "frontier_extraction_invocations": 1,
                "slice_materialization_invocations": 1,
                "local_runtime_invocations": 1,
                "hybrid_stitch_invocations": 1,
                "post_certificate_audit_invocations": 1,
                "full_ground_fallback_invocations": 0,
                "rebuild_invocations": 0,
                "evaluation_only_j0_invocations": 2,
                "authorized_state_action_pairs": len(authorization.allowed_state_actions),
                "full_same_query_state_action_pairs": full_query_counts["state_action_pairs"],
                "coverage_state_action_pairs": world.build_epoch["ground_state_action_pairs"],
                "evaluation_only_j0_composed_candidates": sum(result.composed_candidate_count for result in ground_results),
            },
        }
        _expect(failures, "route-separated work counters", counters_document, expected_counters)

        report_payload = {
            "profile_key": PROFILE_KEY,
            "status": SLICE_PASS,
            "local_hybrid_gate_status": LOCAL_HYBRID_PASS,
            "full_phase3_gate_status": FULL_PHASE3_NOT_RUN,
            "workload_economics_gate_status": ECONOMICS_NOT_RUN,
            "supported_claims": SUPPORTED_CLAIMS,
            "unsupported_claims": UNSUPPORTED_CLAIMS,
            "same_immutable_base_rapm": True,
            "abstract_certified_route_count": 1,
            "local_ground_recovery_route_count": 1,
            "full_ground_fallback_invocations": 0,
            "rebuild_invocations": 0,
            "direct_bad_frontier_used": True,
            "strict_locality_verified": True,
            "hybrid_retains_abstract_planning": True,
            "j0_evaluation_only_after_terminal_freeze": True,
            "grammar_used": False,
            "automatic_predicate_invention_claimed": False,
            "unknown_quotient_discovery_claimed": False,
            "scalar_break_even_claimed": False,
            "manifest_semantics": "sha256_integrity_index_not_public_key_authenticity",
        }
        expected_report = {
            "report_id": object_id(report_payload, "phase3c-report"),
            **report_payload,
        }
        _expect(failures, "Phase3C report/status claims", report, expected_report)
        expected_metrics = {
            "ground_coverage_states": len(world.coverage.covered_states),
            "ground_coverage_state_action_pairs": world.build_epoch["ground_state_action_pairs"],
            "base_abstract_cells": len(world.partition.cell_ids),
            "base_abstract_state_action_pairs": len(world.models.nominal.entries),
            "query_occurrences": 2,
            "routes": ("ABSTRACT_CERTIFIED", "LOCAL_GROUND_RECOVERY"),
            "pre_local_failure_upper": audits[1].lifted_failure_upper,
            "post_local_failure_upper": post_audit.lifted_failure_upper,
            "exact_hybrid_failure": hybrid_lift.evaluation.failure_probability,
            "ground_optimal_failure": ground_points[1].failure_probability,
            "frontier_states": expected_frontier["frontier_state_count"],
            "authorized_state_action_pairs": len(authorization.allowed_state_actions),
            "localized_states": len(localized_states),
            "patch_decisions": len(overlay.decisions),
            "retained_abstract_ground_decisions": hybrid_lift.abstract_decision_count,
            "full_fallback_invocations": 0,
            "rebuild_invocations": 0,
        }
        _expect(failures, "Phase3C metrics", metrics_document, expected_metrics)

        expected_events = (
            {"sequence": 1, "event": "workload_and_base_epoch_frozen"},
            {"sequence": 2, "event": "portable_rapm_roundtrip_verified"},
            {"sequence": 3, "event": "all_portable_proposals_complete"},
            {"sequence": 4, "event": "abstract_control_certificate_passed"},
            {"sequence": 5, "event": "local_query_pre_certificate_failed"},
            {"sequence": 6, "event": "direct_failed_proof_frontier_frozen"},
            {"sequence": 7, "event": "strict_local_authorization_frozen"},
            {"sequence": 8, "event": "isolated_local_result_frozen"},
            {"sequence": 9, "event": "hybrid_overlay_and_post_audit_frozen"},
            {"sequence": 10, "event": "all_terminal_route_certificates_frozen", "terminal_plan_freeze_id": terminal_freeze_id},
            {"sequence": 11, "event": "evaluation_only_j0_started"},
            {"sequence": 12, "event": "evaluation_only_j0_complete"},
            {"sequence": 13, "event": SLICE_PASS},
            {"sequence": 14, "event": LOCAL_HYBRID_PASS},
            {"sequence": 15, "event": FULL_PHASE3_NOT_RUN},
            {"sequence": 16, "event": ECONOMICS_NOT_RUN},
        )
        _expect(failures, "event chronology/J0 authority boundary", events_document, expected_events)

        stable_documents = {}
        for relative in PHASE3C_REQUIRED_PATHS:
            if relative == "run.json":
                continue
            stable_documents[relative] = (
                _load_jsonl(bundle / relative)
                if relative.endswith(".jsonl")
                else _load(bundle / relative)
            )
        recomputed_semantic_hash = canonical_sha256(stable_documents)
        if run.get("semantic_hash") != recomputed_semantic_hash:
            failures.append("Phase3C semantic hash mismatch")
        expected_run_fields = {
            "schema_version": "phase3c.v1",
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "execution_profile": EXECUTION_PROFILE,
            "status": SLICE_PASS,
            "local_hybrid_gate_status": LOCAL_HYBRID_PASS,
            "full_phase3_gate_status": FULL_PHASE3_NOT_RUN,
            "workload_economics_gate_status": ECONOMICS_NOT_RUN,
            "run_id_scope": "all fields except run_id/started_at/finished_at",
            "semantic_hash": recomputed_semantic_hash,
            "source_tree_sha256": _source_tree_hash(),
            "spec_hashes": _spec_hashes(),
        }
        for key, expected in expected_run_fields.items():
            if run.get(key) != to_jsonable(expected):
                failures.append(f"Phase3C run/status field mismatch: {key}")
        run_payload = {
            key: value
            for key, value in run.items()
            if key not in {"run_id", "started_at", "finished_at"}
        }
        if run.get("run_id") != object_id(run_payload, "run"):
            failures.append("Phase3C run content ID mismatch")
        if set(run) != set(expected_run_fields) | {
            "run_id",
            "started_at",
            "finished_at",
            "python",
            "platform",
        }:
            failures.append("Phase3C run field set mismatch")
    except Exception as error:  # noqa: BLE001 - verifier must report, not crash
        failures.append(f"Phase3C verifier exception: {error}")

    return {
        "verified": not failures,
        "failures": tuple(failures),
        "status": run.get("status"),
        "local_hybrid_gate_status": run.get("local_hybrid_gate_status"),
        "semantic_hash": run.get("semantic_hash"),
        "recomputed_semantic_hash": recomputed_semantic_hash,
        "run_id": run.get("run_id"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    arguments = parser.parse_args(argv)
    report = verify_phase3c(arguments.bundle)
    print(json.dumps(to_jsonable(report), ensure_ascii=False, sort_keys=True))
    return 0 if report["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["verify_phase3c"]
