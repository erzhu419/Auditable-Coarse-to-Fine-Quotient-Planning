#!/usr/bin/env python3
"""Independently verify a contract-0.9 general local-recovery bundle.

This verifier deliberately does not call :func:`acfqp.phase3d.run_phase3d`.
It treats the manifest as an integrity index, reconstructs the authoritative
safe-chain world and the source Phase3C portable-policy graphs, recompiles the
sparse capability, replays the exact joint solver in a fresh isolated process,
performs the full hybrid audit, and rebuilds the algebraic value--risk
trade-off control.  These rebuilds are evaluation-only verifier work: they are
not part of the operational Phase3D route, which must consume the frozen
Phase3C bundle without rebuilding its RAPM.  Consequently, changing artifact
payloads and consistently re-signing their content IDs, manifest, and run
semantic hash cannot manufacture a passing bundle.
"""

from __future__ import annotations

import argparse
import ast
from datetime import datetime
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acfqp.artifacts import (  # noqa: E402
    PHASE3C_DOCUMENT_CONTRACTS,
    PHASE3C_REQUIRED_PATHS,
    PHASE3D_DOCUMENT_CONTRACTS,
    PHASE3D_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    serialized_json_sha256,
    sha256_file,
    to_jsonable,
    verify_artifact_bundle,
)
from acfqp.general_local_recovery import (  # noqa: E402
    CausalSearchStatus,
    FAILURE_UPPER,
    REWARD_LOWER,
)
from acfqp.general_local_runtime import FORBIDDEN_PREFIXES  # noqa: E402
from acfqp.general_local_solver import (  # noqa: E402
    CERTIFIED,
    SEARCH_CAP_EXHAUSTED,
    solve_general_local_recovery,
    validate_general_local_result,
)
from acfqp.frozen_phase3c import _bind_models, _bind_registry  # noqa: E402
from acfqp.local_recovery import (  # noqa: E402
    PatchedAuditKernelView,
    audit_hybrid_policy,
    lift_hybrid_policy,
)
from acfqp.phase3d import (  # noqa: E402
    CAUSAL_EVALUATION_CAP,
    COMPILER_LIMITS,
    CONTRACT_VERSION,
    ECONOMICS_NOT_RUN,
    EXECUTION_PROFILE,
    FULL_PHASE3_NOT_RUN,
    GENERAL_LOCAL_GATE_PASS,
    PHASE3D_PASS,
    PROFILE_KEY,
    SAFE_CHAIN_SEARCH_LIMITS,
    SUPPORTED_CLAIMS,
    SYNTHETIC_SEARCH_LIMITS,
    UNSUPPORTED_CLAIMS,
    _construct_safe_chain_context_from_world,
    _authorization_document,
    _causal_circuit_document,
    _causal_search_document,
    _general_request,
    _overlay_document,
    _overlay_from_result,
    _pre_certificate_document,
    _safe_chain_attacks,
    _synthetic_tradeoff_documents,
)
from acfqp.phase3c import (  # noqa: E402
    Phase3CWorld,
    _audit_document,
    _decode_policy,
    _policy_graph_document,
    construct_phase3c_world,
    run_fresh_portable_proposals,
)
from acfqp.planning import audit_abstract_policy  # noqa: E402
from acfqp.portable import (  # noqa: E402
    PortableBuildResult,
    fraction_from_json,
    logical_id,
)
from acfqp.sparse_capability import parse_sparse_capability  # noqa: E402


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _load(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )


def _load_jsonl(path: Path) -> list[Any]:
    return [
        json.loads(line, object_pairs_hook=_reject_duplicate_keys)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            to_jsonable(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _artifact_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            to_jsonable(value),
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _artifact_jsonl_bytes(values: Any) -> bytes:
    if not isinstance(values, (tuple, list)):
        raise TypeError("JSONL artifact must be a sequence")
    return b"".join(_canonical_bytes(value) for value in values)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fraction_json(value: Fraction | int) -> dict[str, int]:
    rational = Fraction(value)
    return {"numerator": rational.numerator, "denominator": rational.denominator}


def _same(actual: Any, expected: Any) -> bool:
    return actual == to_jsonable(expected)


def _expect(failures: list[str], label: str, actual: Any, expected: Any) -> None:
    if not _same(actual, expected):
        failures.append(f"{label} differs from independent authoritative replay")


def _portable_bound_verifier_world(
    authority_world: Phase3CWorld,
    source_epoch: dict[str, Any],
) -> Phase3CWorld:
    """Bind independently rebuilt ground objects to serialized portable IDs.

    Phase3C's construction-time world names cells with predicate expressions;
    the frozen consumer intentionally names the same cells with their portable
    content IDs.  Phase3D artifacts therefore must be replayed against the
    portable-ID view.  This verifier first rebuilds and compares the complete
    mathematical RAPM, then performs only the deterministic registry binding
    used to obtain that view.  It does not treat this evaluation-only binding
    as operational Phase3D work.
    """

    state_by_id = {
        object_id(state, "state"): state
        for state in authority_world.coverage.covered_states
    }
    if len(state_by_id) != len(authority_world.coverage.covered_states):
        raise ValueError("independent Phase3C rebuild has a state-ID collision")
    counters: dict[str, int] = {}
    partition, registry, _complete_ground_action_records = _bind_registry(
        authority_world.portable.model,
        kernel=authority_world.kernel,
        adapter=authority_world.adapter,
        coverage=authority_world.coverage,
        state_by_id=state_by_id,
        counters=counters,
    )
    models = _bind_models(
        authority_world.portable.model,
        partition,
        registry,
        kernel=authority_world.kernel,
    )
    return Phase3CWorld(
        authority_world.kernel,
        authority_world.adapter,
        authority_world.coverage,
        partition,
        models,
        PortableBuildResult(authority_world.portable.model, registry),
        authority_world.queries,
        authority_world.structural_id,
        source_epoch,
    )


FROZEN_BINDING_COUNTERS = {
    "structural_candidate_states_scanned": 4802,
    "portable_states_bound": 192,
    "kernel_step_calls": 0,
    "transition_closure_calls": 0,
    "semantic_label_candidates_scanned": 136,
    "ground_action_candidates_scanned": 144,
    "serialized_cells_bound": 11,
    "serialized_semantic_actions_bound": 20,
    "serialized_ground_actions_bound": 136,
    "serialized_concretizer_rows_bound": 136,
    "partition_builder_calls": 0,
    "quotient_builder_calls": 0,
    "portable_rapm_builder_calls": 0,
}


def _worker_source_failures() -> list[str]:
    """Reject new package/non-stdlib imports in either worker source."""

    failures: list[str] = []
    stdlib = set(getattr(sys, "stdlib_module_names", ()))
    for name in ("general_local_solver.py", "general_local_runtime.py"):
        path = ROOT / "src" / "acfqp" / name
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported: list[str] = []
            if isinstance(node, ast.Import):
                imported = [alias.name.split(".", 1)[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    if (
                        name == "general_local_runtime.py"
                        and node.module in {"general_local_solver", None}
                    ):
                        continue
                    failures.append(f"{name} contains a forbidden relative import")
                    continue
                if node.module:
                    imported = [node.module.split(".", 1)[0]]
            for module in imported:
                if (
                    stdlib
                    and module not in stdlib
                    and module != "__future__"
                    and not (
                        name == "general_local_runtime.py"
                        and module == "general_local_solver"
                    )
                ):
                    failures.append(f"{name} imports non-stdlib module {module!r}")
    return failures


def _isolated_general_replay(
    capability: Mapping[str, Any],
    ground_slice: Mapping[str, Any],
    request: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Replay the exact three-file capability in a fresh network namespace."""

    bubblewrap = shutil.which("bwrap")
    interpreter = shutil.which("python3", path="/usr/bin:/bin")
    if bubblewrap is None or interpreter is None:
        raise ValueError("independent Phase3D verification requires bwrap and system python3")
    with tempfile.TemporaryDirectory(prefix="acfqp-phase3d-verify-local-") as temporary:
        root = Path(temporary)
        runtime = root / "runtime"
        input_root = root / "input"
        output_root = root / "output"
        runtime.mkdir()
        input_root.mkdir()
        output_root.mkdir()
        for name in ("general_local_solver.py", "general_local_runtime.py"):
            shutil.copy2(ROOT / "src" / "acfqp" / name, runtime / name)
        (input_root / "capability.json").write_bytes(_canonical_bytes(capability))
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
                "PYTHONHASHSEED",
                "0",
                "--setenv",
                "ACFQP_FORBIDDEN_ROOTS",
                str(ROOT),
                str(Path(interpreter).resolve()),
                "-B",
                "-S",
                "/runtime/general_local_runtime.py",
                "--capability",
                "/input/capability.json",
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
                "fresh isolated general local replay failed: "
                f"rc={process.returncode}, stdout={process.stdout!r}, "
                f"stderr={process.stderr!r}"
            )
        return _load(output_root / "result.json"), _load(
            output_root / "attestation.json"
        )


def _runtime_attestation_failures(
    attestation: Any,
    *,
    capability: Mapping[str, Any],
    ground_slice: Mapping[str, Any],
    request: Mapping[str, Any],
    result: Mapping[str, Any],
) -> list[str]:
    failures: list[str] = []
    if not isinstance(attestation, dict):
        return ["general local runtime attestation is not an object"]
    payload = dict(attestation)
    claimed_id = payload.pop("attestation_id", None)
    if claimed_id != logical_id("general-local-runtime-attestation", payload):
        failures.append("general local runtime attestation content ID mismatch")
    exact_fields = {
        "schema",
        "isolation_backend",
        "isolation_profile",
        "python_site_disabled",
        "project_checkout_visible",
        "network_namespace_unshared",
        "forbidden_modules_resolved",
        "input_regular_files",
        "output_regular_files_before",
        "capability_sha256",
        "slice_sha256",
        "request_sha256",
        "output_sha256",
        "request_id",
        "occurrence_id",
        "capability_id",
        "slice_id",
        "result_id",
        "status",
        "working_set_limit_bytes",
        "python_implementation",
        "python_version",
        "python_executable",
        "python_executable_sha256",
        "hash_seed",
        "forbidden_prefixes",
        "forbidden_loaded_before",
        "forbidden_loaded_after",
        "loaded_acfqp_modules",
        "loaded_module_origins",
        "unexpected_module_origins",
        "runtime_source_sha256",
        "claim_boundary",
    }
    if set(payload) != exact_fields:
        failures.append("general local runtime attestation field set mismatch")
    stable = {
        "schema": "acfqp.general_local_runtime_attestation.v1",
        "isolation_backend": "bubblewrap_mount_and_network_namespace",
        "isolation_profile": "stdlib_sparse_affine_capability.v1",
        "python_site_disabled": True,
        "project_checkout_visible": False,
        "network_namespace_unshared": True,
        "forbidden_modules_resolved": [],
        "input_regular_files": ["capability.json", "request.json", "slice.json"],
        "output_regular_files_before": [],
        "capability_sha256": _sha256_bytes(_canonical_bytes(capability)),
        "slice_sha256": _sha256_bytes(_canonical_bytes(ground_slice)),
        "request_sha256": _sha256_bytes(_canonical_bytes(request)),
        "output_sha256": _sha256_bytes(_canonical_bytes(result)),
        "request_id": request["request_id"],
        "occurrence_id": request["occurrence_id"],
        "capability_id": capability["capability_id"],
        "slice_id": ground_slice["slice_id"],
        "result_id": result["result_id"],
        "status": result["status"],
        "working_set_limit_bytes": 256 * 1024 * 1024,
        "hash_seed": "0",
        "forbidden_prefixes": list(FORBIDDEN_PREFIXES),
        "forbidden_loaded_before": [],
        "forbidden_loaded_after": [],
        "loaded_acfqp_modules": [],
        "unexpected_module_origins": [],
        "runtime_source_sha256": {
            "acfqp.general_local_solver": sha256_file(
                ROOT / "src/acfqp/general_local_solver.py"
            ),
            "acfqp.general_local_runtime": sha256_file(
                ROOT / "src/acfqp/general_local_runtime.py"
            ),
        },
        "claim_boundary": (
            "integrity_and_reproducibility_evidence_only; "
            "not_host_or_process_provenance"
        ),
    }
    for key, expected in stable.items():
        if payload.get(key) != expected:
            failures.append(f"general local runtime attestation mismatch: {key}")
    for field in ("python_implementation", "python_version", "python_executable"):
        if not isinstance(payload.get(field), str) or not payload[field]:
            failures.append(f"general local runtime attestation invalid: {field}")
    executable = payload.get("python_executable")
    executable_hash = payload.get("python_executable_sha256")
    if isinstance(executable, str) and Path(executable).is_file():
        if executable_hash != sha256_file(Path(executable)):
            failures.append("general local runtime interpreter hash mismatch")
    elif not isinstance(executable_hash, str) or len(executable_hash) != 64:
        failures.append("general local runtime interpreter identity is invalid")
    origins = payload.get("loaded_module_origins")
    if not isinstance(origins, list):
        failures.append("general local runtime module-origin inventory is invalid")
    else:
        for row in origins:
            if (
                not isinstance(row, dict)
                or set(row) != {"module", "origin"}
                or not isinstance(row["module"], str)
                or not isinstance(row["origin"], str)
                or not row["origin"].startswith(("/usr/", "/runtime/"))
            ):
                failures.append("general local runtime contains an invalid module origin")
                break
    return failures


def _authoritative_documents(loaded: Mapping[str, Any]) -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]
]:
    """Reconstruct every stable document and the safe-chain proof objects."""

    source_model = loaded["safe_chain/base_portable_rapm.json"]
    source_epoch = loaded["safe_chain/base_build_epoch.json"]
    source_run = loaded["safe_chain/source_phase3c_run.json"]
    source_manifest = loaded["safe_chain/source_phase3c_manifest.json"]
    source_local_pre = loaded[
        "safe_chain/source_phase3c_local_pre_certificate.json"
    ]
    source_locality = loaded["safe_chain/source_phase3c_locality.json"]
    source_authorization = loaded[
        "safe_chain/source_phase3c_authorization.json"
    ]
    authority_world = construct_phase3c_world()
    if authority_world.portable.model.to_dict() != source_model:
        raise ValueError("embedded frozen RAPM differs from independent Phase3C rebuild")
    source_epoch_payload = dict(source_epoch)
    source_epoch_id = source_epoch_payload.pop("build_epoch_id", None)
    if source_epoch_id != object_id(source_epoch_payload, "build-epoch"):
        raise ValueError("embedded BuildEpoch content ID mismatch")
    rebuilt_epoch = {
        key: value
        for key, value in authority_world.build_epoch.items()
        if key not in {"build_epoch_id", "source_tree_sha256"}
    }
    comparable_source_epoch = {
        key: value
        for key, value in source_epoch.items()
        if key not in {"build_epoch_id", "source_tree_sha256"}
    }
    if rebuilt_epoch != comparable_source_epoch:
        raise ValueError("embedded BuildEpoch differs from independent Phase3C rebuild")
    # Re-run the same closed portable-planner route used by Phase3C.  The
    # policy-graph identity binds the complete portable result/proposal and
    # decoded decision graph, not merely the resulting policy signature.
    # Reconstructing both graphs also lets the source manifest authenticate
    # the complete graph collection even though Phase3D embeds only the local
    # pre-certificate needed at runtime.
    source_proposals = run_fresh_portable_proposals(authority_world)
    source_policies = tuple(
        _decode_policy(authority_world, proposal) for proposal in source_proposals
    )
    source_policy_graphs = tuple(
        _policy_graph_document(authority_world, proposal, policy)
        for proposal, policy in zip(
            source_proposals, source_policies, strict=True
        )
    )
    source_pre_audits = tuple(
        audit_abstract_policy(
            authority_world.kernel,
            proposal.registered.query,
            authority_world.models.envelope,
            policy,
            regret_tolerance=Fraction(1, 20),
        )
        for proposal, policy in zip(
            source_proposals, source_policies, strict=True
        )
    )
    source_pre_documents = tuple(
        _audit_document(
            audit=audit,
            query_key=proposal.registered.query_key,
            query_id=proposal.ground_query_id,
            policy_graph_id=graph["policy_graph_id"],
            model_id=authority_world.portable.model.model_id,
            stage="pre_recovery",
        )
        for proposal, graph, audit in zip(
            source_proposals,
            source_policy_graphs,
            source_pre_audits,
            strict=True,
        )
    )
    if source_local_pre != to_jsonable(source_pre_documents[1]):
        raise ValueError(
            "embedded source pre-certificate differs from independent replay"
        )
    frozen_upper = fraction_from_json(
        source_local_pre["unrestricted_reward_upper"],
        field="source Phase3C unrestricted_reward_upper",
    )
    world = _portable_bound_verifier_world(authority_world, source_epoch)
    context = _construct_safe_chain_context_from_world(
        world,
        unrestricted_reward_upper=frozen_upper,
        source_phase3c_locality=source_locality,
        source_phase3c_authorization=source_authorization,
    )
    source_run_payload = {
        key: value
        for key, value in source_run.items()
        if key not in {"run_id", "started_at", "finished_at"}
    }
    if source_run.get("run_id") != object_id(source_run_payload, "run"):
        raise ValueError("embedded source Phase3C run_id mismatch")
    expected_source_status = {
        "schema_version": "phase3c.v1",
        "contract_version": "0.8.0",
        "profile_key": "phase3c_certificate_triggered_local_recovery_v0",
        "execution_profile": "phase3c_certificate_triggered_local_recovery",
        "status": "PHASE3C_LOCAL_RECOVERY_PASS",
        "local_hybrid_gate_status": "LOCAL_HYBRID_GATE_PASS",
        "full_phase3_gate_status": "PHASE3_AGGREGATE_NOT_RUN",
        "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
    }
    if any(source_run.get(key) != value for key, value in expected_source_status.items()):
        raise ValueError("embedded source Phase3C run status mismatch")
    if source_manifest.get("required_paths") != sorted(PHASE3C_REQUIRED_PATHS):
        raise ValueError("embedded source Phase3C manifest topology mismatch")
    source_records = {
        row.get("path"): row
        for row in source_manifest.get("files", ())
        if isinstance(row, dict)
    }
    if set(source_records) != set(PHASE3C_REQUIRED_PATHS):
        raise ValueError("embedded source Phase3C manifest catalogue mismatch")
    if source_manifest.get("bundle_sha256") != canonical_sha256(
        source_manifest.get("files", ())
    ):
        raise ValueError("embedded source Phase3C manifest bundle hash mismatch")
    for path, (role, schema) in PHASE3C_DOCUMENT_CONTRACTS.items():
        record = source_records[path]
        if (
            record.get("role") != role
            or record.get("schema") != schema
            or record.get("required") is not True
        ):
            raise ValueError(f"embedded source contract mismatch: {path}")
    for path, document in (
        ("build/portable_rapm.json", source_model),
        ("build/epoch.json", source_epoch),
        ("run.json", source_run),
        ("evaluation/locality.json", source_locality),
        ("recovery/authorization.json", source_authorization),
    ):
        serialized = _artifact_json_bytes(document)
        if (
            source_records[path].get("bytes") != len(serialized)
            or source_records[path].get("sha256") != _sha256_bytes(serialized)
        ):
            raise ValueError(f"embedded source byte link mismatch: {path}")
    replayed_source_files = {
        "campaign/policy_graphs.json": _artifact_json_bytes(
            {"policy_graphs": source_policy_graphs}
        ),
        "audit/pre_recovery.jsonl": _artifact_jsonl_bytes(
            source_pre_documents
        ),
    }
    for path, serialized in replayed_source_files.items():
        record = source_records[path]
        if (
            record.get("bytes") != len(serialized)
            or record.get("sha256") != _sha256_bytes(serialized)
        ):
            raise ValueError(
                f"embedded source replay/manifest link mismatch: {path}"
            )
    model_document = context.world.portable.model.to_dict()
    base_model_sha256 = serialized_json_sha256(model_document)
    base_epoch_sha256 = serialized_json_sha256(source_epoch)
    occurrence_id = object_id(
        {
            "profile_key": PROFILE_KEY,
            "ground_query_id": context.ground_query_id,
            "frontier_id": context.frontier.frontier_id,
            "capability_id": context.capability["capability_id"],
        },
        "occurrence",
    )
    request = _general_request(
        occurrence_id=occurrence_id,
        capability=context.capability,
        ground_slice=context.sparse_slice,
        limits=SAFE_CHAIN_SEARCH_LIMITS,
    )
    result = solve_general_local_recovery(
        context.capability, context.sparse_slice, request
    ).to_dict()
    validate_general_local_result(result)
    if (
        result["status"] != CERTIFIED
        or result["localized_node_ids"]
        != list(context.causal_search.selected_node_ids or ())
        or len(result["decisions"]) != 8
        or result["root_reward_lower"] != _fraction_json(Fraction(3, 64))
        or result["root_failure_upper"] != _fraction_json(Fraction(397, 20000))
        or result["candidate_subset_count"] != 2
        or result["theoretical_total_policy_space"] != 257
        or result["counters"]["policy_assignments"] != 257
        or not result["search_complete"]
        or not result["minimality_proven"]
    ):
        raise ValueError("authoritative safe-chain joint solver golden changed")

    overlay = _overlay_from_result(context, result)
    post_audit_kernel = PatchedAuditKernelView(
        context.world.kernel,
        tuple((decision.state, decision.action) for decision in overlay.decisions),
    )
    post_audit = audit_hybrid_policy(
        post_audit_kernel,
        context.query,
        context.world.models.envelope,
        overlay,
        regret_tolerance=Fraction(1, 20),
        unrestricted_reward_upper=frozen_upper,
    )
    hybrid = lift_hybrid_policy(
        context.world.kernel,
        context.query,
        context.world.models.envelope,
        overlay,
    )
    if (
        not post_audit.certified
        or post_audit.lifted_reward_lower != Fraction(3, 64)
        or post_audit.lifted_failure_upper != Fraction(397, 20000)
        or post_audit.regret_upper != 0
        or hybrid.evaluation.expected_reward != Fraction(3, 64)
        or hybrid.evaluation.failure_probability != Fraction(317, 16000)
        or hybrid.patched_decision_count != 8
        or hybrid.abstract_decision_count != 12
    ):
        raise ValueError("authoritative safe-chain full audit golden changed")
    if (
        sum(
            record.operation == "actions"
            for record in post_audit_kernel.access_log
        )
        != 16
        or sum(
            record.operation == "step"
            for record in post_audit_kernel.access_log
        )
        != 8
    ):
        raise ValueError("authoritative patched post-audit access changed")

    synthetic = _synthetic_tradeoff_documents()
    if (
        synthetic["result"]["status"] != CERTIFIED
        or synthetic["result"]["root_reward_lower"] != _fraction_json(1)
        or synthetic["result"]["root_failure_upper"]
        != _fraction_json(Fraction(1, 25))
        or synthetic["result"]["theoretical_total_policy_space"] != 25
        or synthetic["capped_result"]["status"] != SEARCH_CAP_EXHAUSTED
    ):
        raise ValueError("authoritative joint trade-off control golden changed")

    circuit_document = _causal_circuit_document(context)
    causal_document = _causal_search_document(context, circuit_document)
    authorization_document = _authorization_document(context)
    pre_document = _pre_certificate_document(context)
    overlay_document = _overlay_document(context, overlay, result)
    attacks = _safe_chain_attacks(context, request, result, synthetic)
    post_document = {
        "schema": "acfqp.post_certificate.phase3d.v1",
        "overlay_id": overlay.overlay_id,
        "local_result_id": result["result_id"],
        "unrestricted_reward_upper": post_audit.unrestricted_reward_upper,
        "lifted_reward_lower": post_audit.lifted_reward_lower,
        "lifted_failure_upper": post_audit.lifted_failure_upper,
        "regret_upper": post_audit.regret_upper,
        "regret_tolerance": post_audit.regret_tolerance,
        "risk_tolerance": post_audit.risk_tolerance,
        "exact_hybrid_evaluation_status": (
            "EVALUATION_ONLY_NOT_RUN_IN_OPERATIONAL_RUNNER"
        ),
        "exact_hybrid_reward": None,
        "exact_hybrid_failure": None,
        "patched_decision_count": len(overlay.decisions),
        "abstract_decision_count": None,
        "certified": post_audit.certified,
        "full_authority_replay": True,
        "ground_j0_used": False,
    }
    source_boundary_bytes = len(_canonical_bytes(context.source_boundary))
    capability_bytes = len(_canonical_bytes(context.capability))
    locality = {
        "schema": "acfqp.locality_audit.phase3d.v1",
        "phase3c_direct_frontier_state_actions": 32,
        "phase3c_total_authorized_state_actions": 40,
        "phase3c_total_authorized_outcomes": 160,
        "phase3d_causal_frontier_state_actions": 16,
        "phase3d_total_authorized_state_actions": 24,
        "phase3d_total_authorized_outcomes": 96,
        "state_action_authorization_reduction": Fraction(2, 5),
        "outcome_authorization_reduction": Fraction(2, 5),
        "same_query_all_action_state_actions": 48,
        "coverage_state_actions": 144,
        "strict_query_locality": True,
        "strict_build_locality": True,
        "source_boundary_nodes": 4,
        "source_boundary_realization_rows": 20,
        "worker_input_ports": len(context.capability["input_ports"]),
        "worker_exit_ports": len(context.capability["exit_ports"]),
        "worker_reward_forms": len(context.capability["root_reward_forms"]),
        "worker_failure_forms": len(context.capability["root_failure_forms"]),
        "source_boundary_canonical_bytes": source_boundary_bytes,
        "worker_capability_canonical_bytes": capability_bytes,
        "boundary_byte_reduction": Fraction(
            source_boundary_bytes - capability_bytes, source_boundary_bytes
        ),
        "finite_domain_extensional_sufficiency": True,
        "finite_domain_representation_minimality": True,
        "information_theoretic_minimality_claimed": False,
        "base_rapm_immutable": True,
        "base_model_sha256_before": base_model_sha256,
        "base_model_sha256_after": serialized_json_sha256(model_document),
        "base_epoch_sha256_before": base_epoch_sha256,
        "base_epoch_sha256_after": serialized_json_sha256(source_epoch),
        "operational_rapm_builder_invocations": 0,
        "operational_transition_closure_invocations": 0,
        "operational_ground_steps_before_local_authorization": 0,
        "operational_authorized_frontier_materialization_step_calls": 16,
        "operational_authorized_frontier_materialization_positive_outcomes": 64,
        "operational_patched_post_audit_step_calls": 8,
        "operational_total_ground_step_calls": 24,
        "operational_ground_steps_for_accounting": 0,
        "operational_ground_steps_outside_authorized_or_patched_cells": 0,
        "evaluation_only_exact_hybrid_ground_replay_invocations": 0,
    }
    base_identity = {
        "schema": "acfqp.base_identity.phase3d.v1",
        "portable_model_id": context.world.portable.model.model_id,
        "portable_model_sha256": base_model_sha256,
        "build_epoch_id": source_epoch["build_epoch_id"],
        "build_epoch_sha256": base_epoch_sha256,
        "coverage_id": context.world.portable.model.coverage_id,
        "source_profile": "phase3c_certificate_triggered_local_recovery_v0",
        "source_contract_version": "0.8.0",
        "source_run_id": source_run["run_id"],
        "source_semantic_hash": source_run["semantic_hash"],
        "source_manifest_sha256": _sha256_bytes(
            _artifact_json_bytes(source_manifest)
        ),
        "source_locality_sha256": serialized_json_sha256(source_locality),
        "source_authorization_sha256": serialized_json_sha256(
            source_authorization
        ),
        "source_bundle_integrity_verified": True,
        "binding_mode": "finite_structural_id_scan_without_transitions",
        "binding_counters": FROZEN_BINDING_COUNTERS,
        "frozen_unrestricted_reward_upper": frozen_upper,
        "rapm_builder_invocations": 0,
        "partition_builder_invocations": 0,
        "quotient_builder_invocations": 0,
        "transition_closure_invocations": 0,
        "kernel_step_invocations_during_binding": 0,
        "reused_without_mutation": True,
    }
    profile = {
        "schema": "acfqp.general_local_recovery_profile.phase3d.v1",
        "profile_key": PROFILE_KEY,
        "execution_profile": EXECUTION_PROFILE,
        "contract_version": CONTRACT_VERSION,
        "policy_class": "deterministic_finite_horizon_markov",
        "causal_candidate_scope": "earliest_DirectBad_antichain",
        "causal_search_evaluation_cap": CAUSAL_EVALUATION_CAP,
        "compiler_limits": COMPILER_LIMITS,
        "safe_chain_search_limits": SAFE_CHAIN_SEARCH_LIMITS.to_dict(),
        "synthetic_search_limits": SYNTHETIC_SEARCH_LIMITS.to_dict(),
        "worker_inputs": ["capability.json", "request.json", "slice.json"],
        "joint_search_completeness_scope": (
            "finite deterministic overlays over the authorized antichain; "
            "fixed abstract policy and scalar exits elsewhere; only when caps complete"
        ),
        "deeper_causal_recovery_rule": (
            "full post-audit then a new occurrence-bound transaction"
        ),
        "base_model_source": "verified_frozen_phase3c_artifact_bundle",
        "operational_rebuild_forbidden": True,
        "unrestricted_upper_source": "content_addressed_phase3c_pre_certificate",
        "ground_authority_accounting_source": (
            "verified_phase3c_locality_plus_authorized_slice_materialization"
        ),
        "independent_verifier_rebuild_is_evaluation_only": True,
        "operational_exact_hybrid_ground_replay_forbidden": True,
        "j0_authority": "not_mounted_or_invoked",
        "supported_claims": SUPPORTED_CLAIMS,
        "unsupported_claims": UNSUPPORTED_CLAIMS,
    }
    compiler_counts = context.capability_evidence["recovery_input_compilation"][
        "counts"
    ]
    work = {
        "schema": "acfqp.work_counters.phase3d.v1",
        "safe_chain": {
            "causal_evaluations": context.causal_search.evaluation_count,
            "authorized_state_action_pairs": 24,
            "authorized_outcomes": 96,
            "frontier_worker_state_action_pairs": 16,
            "frontier_worker_outcomes": 64,
            "trusted_frontier_materialization": {
                "step_calls": 16,
                "positive_probability_outcomes": 64,
                "extra_accounting_step_calls": 0,
            },
            "sound_post_audit": {
                "patched_action_checks": 16,
                "patched_step_calls": 8,
                "outside_patch_step_calls": 0,
            },
            "compiler": {
                **context.capability_evidence["enumeration"],
                "recovery_input_counts": compiler_counts,
            },
            "joint_solver": result["counters"],
            "joint_theoretical_policy_space": result[
                "theoretical_total_policy_space"
            ],
        },
        "synthetic": {
            "joint_solver": synthetic["result"]["counters"],
            "joint_theoretical_policy_space": synthetic["result"][
                "theoretical_total_policy_space"
            ],
        },
        "model_binding": FROZEN_BINDING_COUNTERS,
        "ground_j0_invocations": 0,
        "evaluation_only_exact_hybrid_ground_replay_invocations": 0,
        "ground_fallback_invocations": 0,
        "rapm_rebuilds": 0,
    }
    report_payload = {
        "schema": "acfqp.phase3d_report.v1",
        "profile_key": PROFILE_KEY,
        "status": PHASE3D_PASS,
        "general_local_recovery_gate_status": GENERAL_LOCAL_GATE_PASS,
        "full_phase3_gate_status": FULL_PHASE3_NOT_RUN,
        "workload_economics_gate_status": ECONOMICS_NOT_RUN,
        "resolved_risks": ("V0-RISK-004", "V0-RISK-005", "V0-RISK-006"),
        "safe_chain": {
            "baseline_failure_upper": Fraction(5099, 10000),
            "selected_causal_failure_upper": Fraction(397, 20000),
            "selected_causal_nodes": 1,
            "excluded_direct_bad_nodes": 1,
            "authorized_state_action_pairs": 24,
            "authorized_outcomes": 96,
            "root_reward_lower": Fraction(3, 64),
            "root_failure_upper": Fraction(397, 20000),
            "exact_hybrid_evaluation_status": (
                "EVALUATION_ONLY_NOT_RUN_IN_OPERATIONAL_RUNNER"
            ),
            "exact_hybrid_failure": None,
            "patched_decisions": 8,
            "retained_abstract_decisions": None,
        },
        "synthetic_joint_tradeoff": {
            "legacy_certified_value": False,
            "joint_search_certified": True,
            "minimum_localized_cells": 2,
            "root_reward_lower": Fraction(1),
            "root_failure_upper": Fraction(1, 25),
        },
        "base_rapm_immutable": True,
        "fallback_count": 0,
        "rebuild_count": 0,
        "j0_invocations": 0,
        "supported_claims": SUPPORTED_CLAIMS,
        "unsupported_claims": UNSUPPORTED_CLAIMS,
    }
    report = {
        **report_payload,
        "report_id": object_id(report_payload, "phase3d-report"),
    }
    metrics = {
        "schema": "acfqp.metrics.phase3d.v1",
        "status": PHASE3D_PASS,
        "causal_candidate_nodes": len(context.causal_search.candidate_node_ids),
        "causal_selected_nodes": len(context.causal_search.selected_node_ids or ()),
        "causal_excluded_nodes": len(
            context.causal_search.excluded_candidate_node_ids
        ),
        "authorization_pairs_before": 40,
        "authorization_pairs_after": 24,
        "boundary_rows_before": 20,
        "capability_input_ports_after": 1,
        "safe_chain_policy_assignments": result["counters"]["policy_assignments"],
        "synthetic_policy_assignments": synthetic["result"]["counters"][
            "policy_assignments"
        ],
    }
    events = (
        {
            "sequence": 1,
            "event": "verified_frozen_phase3c_bundle_consumed_and_bound",
        },
        {"sequence": 2, "event": "abstract_plan_certificate_failed"},
        {"sequence": 3, "event": "exact_causal_circuit_frozen"},
        {"sequence": 4, "event": "slack_aware_causal_family_completed"},
        {"sequence": 5, "event": "strict_causal_authorization_frozen"},
        {"sequence": 6, "event": "sparse_worker_capability_compiled"},
        {"sequence": 7, "event": "isolated_joint_value_risk_search_completed"},
        {"sequence": 8, "event": "hybrid_overlay_frozen"},
        {"sequence": 9, "event": "full_authority_post_audit_passed"},
        {"sequence": 10, "event": "synthetic_joint_tradeoff_control_passed"},
        {"sequence": 11, "event": "general_local_recovery_gate_frozen"},
    )
    documents: dict[str, Any] = {
        "contract/profile.json": profile,
        "safe_chain/base_identity.json": base_identity,
        "safe_chain/base_portable_rapm.json": source_model,
        "safe_chain/base_build_epoch.json": source_epoch,
        "safe_chain/source_phase3c_run.json": source_run,
        "safe_chain/source_phase3c_manifest.json": source_manifest,
        "safe_chain/source_phase3c_local_pre_certificate.json": source_local_pre,
        "safe_chain/source_phase3c_locality.json": source_locality,
        "safe_chain/source_phase3c_authorization.json": source_authorization,
        "safe_chain/pre_certificate.json": pre_document,
        "safe_chain/causal_circuit.json": circuit_document,
        "safe_chain/causal_search.json": causal_document,
        "safe_chain/authorization.json": authorization_document,
        "safe_chain/ground_slice.json": context.sparse_slice,
        "safe_chain/source_boundary.json": context.source_boundary,
        "safe_chain/capability.json": context.capability,
        "safe_chain/capability_evidence.json": context.capability_evidence,
        "safe_chain/request.json": request,
        "safe_chain/result.json": result,
        "safe_chain/overlay.json": overlay_document,
        "safe_chain/post_certificate.json": post_document,
        "safe_chain/locality.json": locality,
        "synthetic/tradeoff_problem.json": synthetic["problem"],
        "synthetic/capability.json": synthetic["capability"],
        "synthetic/ground_slice.json": synthetic["ground_slice"],
        "synthetic/request.json": synthetic["request"],
        "synthetic/result.json": synthetic["result"],
        "synthetic/legacy_greedy.json": synthetic["legacy"],
        "attacks/regressions.json": attacks,
        "accounting/work_counters.json": work,
        "result/phase3d_report.json": report,
        "metrics.json": metrics,
        "events.jsonl": events,
    }
    return documents, {
        "context": context,
        "overlay": overlay,
        "post_audit": post_audit,
        "hybrid": hybrid,
        "synthetic": synthetic,
    }, request, result


def verify_phase3d(bundle: Path) -> dict[str, Any]:
    """Verify integrity, authority separation, and every Phase 3D claim."""

    bundle = Path(bundle)
    failures = list(verify_artifact_bundle(bundle))
    failures.extend(_worker_source_failures())
    run: dict[str, Any] = {}
    recomputed_semantic_hash: str | None = None
    evaluation_only_exact_hybrid_reward: Fraction | None = None
    evaluation_only_exact_hybrid_failure: Fraction | None = None
    evaluation_only_patched_decision_count: int | None = None
    evaluation_only_abstract_decision_count: int | None = None
    if not (bundle / "manifest.json").is_file():
        return {"verified": False, "failures": tuple(failures)}

    try:
        manifest = _load(bundle / "manifest.json")
        if (bundle / "manifest.json").read_bytes() != _artifact_json_bytes(manifest):
            failures.append("Phase3D manifest serialization is noncanonical")
        detached_expected = (
            f"{sha256_file(bundle / 'manifest.json')}  manifest.json\n".encode("ascii")
        )
        if (bundle / "manifest.sha256").read_bytes() != detached_expected:
            failures.append("Phase3D detached manifest record is noncanonical")
        if set(manifest) != {
            "schema",
            "schema_version",
            "required_paths",
            "files",
            "bundle_sha256",
        }:
            failures.append("Phase3D manifest field set mismatch")
        if manifest.get("schema") != "acfqp.manifest@phase05.v1":
            failures.append("Phase3D manifest schema mismatch")
        if manifest.get("schema_version") != "phase05.v1":
            failures.append("Phase3D manifest schema-version mismatch")
        if manifest.get("required_paths") != sorted(PHASE3D_REQUIRED_PATHS):
            failures.append("Phase3D exact required-path contract mismatch")
        records = {
            row.get("path"): row
            for row in manifest.get("files", [])
            if isinstance(row, dict) and isinstance(row.get("path"), str)
        }
        if len(records) != len(manifest.get("files", [])):
            failures.append("Phase3D manifest has duplicate or malformed records")
        if set(records) != set(PHASE3D_REQUIRED_PATHS):
            failures.append("Phase3D manifest document set mismatch")
        for path, (role, schema) in PHASE3D_DOCUMENT_CONTRACTS.items():
            row = records.get(path)
            if row is None:
                continue
            if set(row) != {"path", "bytes", "sha256", "role", "schema", "required"}:
                failures.append(f"Phase3D manifest record field mismatch: {path}")
            if row.get("role") != role or row.get("schema") != schema:
                failures.append(f"Phase3D manifest role/schema mismatch: {path}")
            if row.get("required") is not True:
                failures.append(f"Phase3D manifest required flag mismatch: {path}")

        loaded: dict[str, Any] = {}
        for path in PHASE3D_REQUIRED_PATHS:
            file_path = bundle / path
            document = _load_jsonl(file_path) if path.endswith(".jsonl") else _load(file_path)
            loaded[path] = document
            expected_bytes = (
                _artifact_jsonl_bytes(document)
                if path.endswith(".jsonl")
                else _artifact_json_bytes(document)
            )
            if file_path.read_bytes() != expected_bytes:
                failures.append(f"Phase3D noncanonical artifact serialization: {path}")
        run = loaded["run.json"]

        expected, authority, request, result = _authoritative_documents(loaded)
        context = authority["context"]
        evaluation_only_hybrid = authority["hybrid"]
        evaluation_only_exact_hybrid_reward = (
            evaluation_only_hybrid.evaluation.expected_reward
        )
        evaluation_only_exact_hybrid_failure = (
            evaluation_only_hybrid.evaluation.failure_probability
        )
        evaluation_only_patched_decision_count = (
            evaluation_only_hybrid.patched_decision_count
        )
        evaluation_only_abstract_decision_count = (
            evaluation_only_hybrid.abstract_decision_count
        )
        parse_sparse_capability(loaded["safe_chain/capability.json"])
        parse_sparse_capability(loaded["synthetic/capability.json"])
        validate_general_local_result(loaded["safe_chain/result.json"])
        validate_general_local_result(loaded["synthetic/result.json"])

        for path, expected_document in expected.items():
            _expect(failures, path, loaded[path], expected_document)

        evidence = loaded["safe_chain/capability_evidence.json"]
        if evidence.get("source_boundary_view_id") != context.source_boundary.get(
            "boundary_view_id"
        ):
            failures.append("capability evidence/source boundary ID mismatch")
        if evidence.get("capability_id") != context.capability.get("capability_id"):
            failures.append("capability evidence/capability ID mismatch")
        if evidence.get("target_frontier_id") != context.frontier.frontier_id:
            failures.append("capability evidence/causal frontier ID mismatch")

        isolated_result, isolated_attestation = _isolated_general_replay(
            context.capability, context.sparse_slice, request
        )
        _expect(failures, "fresh isolated safe-chain result", isolated_result, result)
        _expect(
            failures,
            "fresh isolated runtime attestation",
            loaded["safe_chain/runtime_attestation.json"],
            isolated_attestation,
        )
        failures.extend(
            _runtime_attestation_failures(
                loaded["safe_chain/runtime_attestation.json"],
                capability=context.capability,
                ground_slice=context.sparse_slice,
                request=request,
                result=result,
            )
        )

        # Explicit semantic goldens make report re-signing insufficient.
        causal = context.causal_search
        if (
            causal.status is not CausalSearchStatus.CAUSAL_FAMILY_FOUND
            or not causal.search_complete
            or len(causal.candidate_node_ids) != 2
            or len(causal.selected_node_ids or ()) != 1
            or len(causal.excluded_candidate_node_ids) != 1
            or causal.baseline.root_value(FAILURE_UPPER) != Fraction(5099, 10000)
            or dict(causal.baseline.deficits)[FAILURE_UPPER]
            != Fraction(4599, 10000)
            or dict(causal.baseline.deficits)[REWARD_LOWER] != 0
        ):
            failures.append("slack-aware causal proof golden changed")
        if (
            len(context.capability["input_ports"]) != 1
            or context.capability["exit_ports"] != []
            or len(context.capability["root_reward_forms"]) != 1
            or len(context.capability["root_failure_forms"]) != 1
        ):
            failures.append("minimal sparse capability shape golden changed")

        stable_documents = {
            path: loaded[path]
            for path in PHASE3D_REQUIRED_PATHS
            if path != "run.json"
        }
        recomputed_semantic_hash = canonical_sha256(stable_documents)
        expected_semantic_hash = canonical_sha256(
            {
                **expected,
                "safe_chain/runtime_attestation.json": isolated_attestation,
            }
        )
        if run.get("semantic_hash") != recomputed_semantic_hash:
            failures.append("Phase3D run semantic hash does not bind bundle documents")
        if recomputed_semantic_hash != expected_semantic_hash:
            failures.append("Phase3D semantic hash differs from authoritative replay")

        expected_run = {
            "schema": "acfqp.run.phase3d.v1",
            "schema_version": "phase3d.v1",
            "profile_key": PROFILE_KEY,
            "execution_profile": EXECUTION_PROFILE,
            "contract_version": CONTRACT_VERSION,
            "status": PHASE3D_PASS,
            "general_local_recovery_gate_status": GENERAL_LOCAL_GATE_PASS,
            "full_phase3_gate_status": FULL_PHASE3_NOT_RUN,
            "workload_economics_gate_status": ECONOMICS_NOT_RUN,
            "semantic_hash": recomputed_semantic_hash,
            "required_paths": PHASE3D_REQUIRED_PATHS,
        }
        for key, value in expected_run.items():
            if run.get(key) != to_jsonable(value):
                failures.append(f"Phase3D run/status field mismatch: {key}")
        if set(run) != set(expected_run) | {"started_at", "finished_at", "run_id"}:
            failures.append("Phase3D run field set mismatch")
        run_id_payload = {
            key: value
            for key, value in run.items()
            if key not in {"started_at", "finished_at", "run_id"}
        }
        if run.get("run_id") != object_id(run_id_payload, "run"):
            failures.append("Phase3D run content ID mismatch")
        try:
            started = datetime.fromisoformat(run["started_at"])
            finished = datetime.fromisoformat(run["finished_at"])
            if started.tzinfo is None or finished.tzinfo is None or finished < started:
                failures.append("Phase3D run timestamps are invalid")
        except (KeyError, TypeError, ValueError):
            failures.append("Phase3D run timestamps are invalid")
    except Exception as error:  # noqa: BLE001 - verifier reports rather than crashes
        failures.append(f"Phase3D verifier exception: {error}")

    return {
        "verified": not failures,
        "failures": tuple(failures),
        "status": run.get("status"),
        "general_local_recovery_gate_status": run.get(
            "general_local_recovery_gate_status"
        ),
        "semantic_hash": run.get("semantic_hash"),
        "recomputed_semantic_hash": recomputed_semantic_hash,
        "run_id": run.get("run_id"),
        "evaluation_only_exact_hybrid_reward": (
            evaluation_only_exact_hybrid_reward
        ),
        "evaluation_only_exact_hybrid_failure": (
            evaluation_only_exact_hybrid_failure
        ),
        "evaluation_only_patched_decision_count": (
            evaluation_only_patched_decision_count
        ),
        "evaluation_only_abstract_decision_count": (
            evaluation_only_abstract_decision_count
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    arguments = parser.parse_args(argv)
    report = verify_phase3d(arguments.bundle)
    print(json.dumps(to_jsonable(report), ensure_ascii=False, sort_keys=True))
    return 0 if report["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["verify_phase3d"]
