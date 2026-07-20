"""Contract-0.8 certificate-triggered local-recovery campaign.

The reusable object remains an immutable portable RAPM.  Two queries are
planned against the same eleven-cell model in closed planner processes.  The
one-step query certifies through the nominal abstract-planning interface,
without ground simulator or J0 access.  The canonical two-step query does not:
its complete failed-proof graph authorizes a strict subset of ground
state-action pairs, a second closed process synthesizes a query-scoped decision
overlay, and the hybrid contingent plan is then re-certified.

Ground J0 is evaluation-only and is not started until both terminal route
certificates and the hybrid-plan freeze identity have been materialized.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Hashable, Iterable

from acfqp.abstraction import QuotientModels, build_quotient_models
from acfqp.aliased_safe_chain import (
    TARGET_PREDICATE_ID,
    base_cell_id,
    build_initial_partition,
    geometry_feature_cache,
    geometry_predicates,
)
from acfqp.artifacts import (
    PHASE3C_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    serialized_json_bytes,
    serialized_json_sha256,
    sha256_file,
    to_jsonable,
    verify_artifact_bundle,
    write_artifact_bundle,
)
from acfqp.build_coverage import SuiteBuildCoverage
from acfqp.core import QuerySpec
from acfqp.domains import G2048ActionFrameGeometryAdapter, safe_chain_fixture
from acfqp.planning import (
    FiniteHorizonPolicy,
    audit_abstract_policy,
    evaluate_ground_policy,
    solve_ground_pareto,
)
from acfqp.local_recovery import (
    FailedProofFrontier,
    FailedProofGraph,
    GroundPatchDecision,
    HybridPolicyOverlay,
    LocalRecoveryAuthorization,
    audit_hybrid_policy,
    build_failed_proof_graph,
    build_redacted_boundary_view,
    lift_hybrid_policy,
    materialize_authorized_slice,
    redact_authorized_slice_for_worker,
)
from acfqp.local_solver import solve_local_recovery
from acfqp.portable import (
    PortableBuildResult,
    PortableQuery,
    build_portable_rapm,
    dump_model,
    dump_query,
    fraction_to_json,
    load_model,
    logical_id,
)
from acfqp.portable_planner import (
    PortableParetoPoint,
    PortablePlanResult,
    load_result,
)
from acfqp.refinement import RefinementTracker, SplitStatus, attempt_split


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILE_KEY = "phase3c_certificate_triggered_local_recovery_v0"
EXECUTION_PROFILE = "phase3c_certificate_triggered_local_recovery"
CONTRACT_VERSION = "0.8.0"
STATE_CAP = 50_000

SLICE_PASS = "PHASE3C_LOCAL_RECOVERY_PASS"
LOCAL_HYBRID_PASS = "LOCAL_HYBRID_GATE_PASS"
FULL_PHASE3_NOT_RUN = "PHASE3_AGGREGATE_NOT_RUN"
ECONOMICS_NOT_RUN = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
INVARIANT_FAILURE = "PHASE3C_INVARIANT_VIOLATION"

ABSTRACT_QUERY_KEY = "g2048.safe_chain.h1.delta0.abstract_control"
LOCAL_QUERY_KEY = "g2048.safe_chain.h2.delta05.local_recovery"

SUPPORTED_CLAIMS = (
    "a frozen portable RAPM can answer a certified multi-state query through its nominal abstract-planning interface without ground simulator or J0 access",
    "an uncertified contingent plan can expose a causally derived strict-local ground slice and be re-certified with a query-scoped overlay",
    "the registered local-recovery route preserves the base RAPM and BuildEpoch while retaining abstract decisions in the final hybrid graph",
)

UNSUPPORTED_CLAIMS = (
    "automatic predicate invention or unknown quotient discovery",
    "cardinality-minimal strategic abstraction in general domains",
    "learned or partial-observation world-model induction",
    "workload break-even or amortized speedup",
    "complete Phase-3 aggregate or Phase-5 multiresolution Gate",
    "large-scale, visual, option-level, or cross-domain generality",
)


class Phase3CInvariantViolation(RuntimeError):
    status = INVARIANT_FAILURE


@dataclass(frozen=True, slots=True)
class RegisteredQuery:
    query_key: str
    query: QuerySpec[Any]
    expected_route: str


@dataclass(frozen=True, slots=True)
class Phase3CWorld:
    kernel: Any
    adapter: G2048ActionFrameGeometryAdapter
    coverage: SuiteBuildCoverage[Any]
    partition: Any
    models: QuotientModels
    portable: PortableBuildResult
    queries: tuple[RegisteredQuery, RegisteredQuery]
    structural_id: str
    build_epoch: dict[str, Any]


@dataclass(frozen=True, slots=True)
class FrozenPortableProposal:
    registered: RegisteredQuery
    ground_query_id: str
    portable_query: PortableQuery
    result: PortablePlanResult
    proposal: PortableParetoPoint
    proposal_source: str
    attestation: dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _source_tree_hash() -> str:
    digest = hashlib.sha256()
    paths: list[Path] = []
    for root_name in ("src", "scripts", "specs", "tests"):
        root = PROJECT_ROOT / root_name
        if root.exists():
            paths.extend(
                path
                for path in root.rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and not any(part.endswith(".egg-info") for part in path.parts)
            )
    for name in ("pyproject.toml", "README.md", "DECISION_LEDGER.md"):
        path = PROJECT_ROOT / name
        if path.is_file():
            paths.append(path)
    for path in sorted(set(paths)):
        digest.update(path.relative_to(PROJECT_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _spec_hashes() -> dict[str, str]:
    return {
        path.name: sha256_file(path)
        for path in sorted((PROJECT_ROOT / "specs").glob("*.md"))
    }


def _g2048_normalizer_rules() -> tuple[dict[str, Any], ...]:
    return (
        {
            "proof_id": "g2048.canonical.merge_le_1_per_step.total_le_h.v1",
            "kind": "nonnegative_feature_caps_v1",
            "reward_basis": (
                {"name": "merge", "value": fraction_to_json(Fraction(1))},
            ),
            "feature_caps": (
                {
                    "name": "merge",
                    "per_step_cap": fraction_to_json(Fraction(1)),
                    "total_cap": None,
                },
            ),
        },
    )


def _build_queries(canonical: QuerySpec[Any]) -> tuple[RegisteredQuery, RegisteredQuery]:
    abstract = QuerySpec(
        canonical.initial_distribution,
        1,
        canonical.reward_weights,
        canonical.goal,
        Fraction(0),
        Fraction(1),
        canonical.normalizer_proof_id,
    )
    return (
        RegisteredQuery(ABSTRACT_QUERY_KEY, abstract, "ABSTRACT_CERTIFIED"),
        RegisteredQuery(LOCAL_QUERY_KEY, canonical, "LOCAL_GROUND_RECOVERY"),
    )


def construct_phase3c_world() -> Phase3CWorld:
    """Construct the frozen eleven-cell consumption-time RAPM once."""

    kernel, canonical = safe_chain_fixture()
    adapter = G2048ActionFrameGeometryAdapter()
    queries = _build_queries(canonical)
    coverage = SuiteBuildCoverage.from_queries(
        kernel,
        tuple(item.query for item in queries),
        state_cap=STATE_CAP,
    )
    states = coverage.covered_states
    if len(states) != 192:
        raise Phase3CInvariantViolation("Phase3C coverage must contain 192 states")

    partition = build_initial_partition(kernel, states)
    features = geometry_feature_cache(adapter, kernel, states)
    predicate = next(
        candidate
        for candidate in geometry_predicates(features)
        if candidate.canonical_id == TARGET_PREDICATE_ID
    )
    initial_cell = base_cell_id(kernel, canonical.initial_distribution[0][1])
    split = attempt_split(partition, initial_cell, predicate, RefinementTracker())
    if split.status is not SplitStatus.SPLIT_ACCEPTED:
        raise Phase3CInvariantViolation("frozen first RAPM revision was not accepted")
    partition = split.partition
    if len(partition.cell_ids) != 11:
        raise Phase3CInvariantViolation("Phase3C base RAPM must have eleven cells")

    models = build_quotient_models(
        kernel,
        states,
        partition,
        semantic_adapter=adapter,
    )
    coverage_document = {
        "mode": coverage.mode,
        "declared_support_set_sha256": coverage.declared_support_set_sha256,
        "declared_support_state_ids": coverage.declared_support_state_ids,
        "covered_state_ids": coverage.covered_state_ids,
        "exact_state_cap": coverage.exact_state_cap,
        "admissible_query_support_rule": coverage.admissible_query_support_rule,
        "reuse_outside_coverage_forbidden": (
            coverage.reuse_outside_coverage_forbidden
        ),
    }
    portable = build_portable_rapm(
        models,
        state_ids=lambda state: object_id(state, "state"),
        semantic_action_ids=lambda action: object_id(action, "semantic-source"),
        ground_action_ids=lambda action: object_id(action, "ground-action-source"),
        normalizer_rules=_g2048_normalizer_rules(),
        state_kinds=lambda state: (
            "failure"
            if getattr(getattr(state, "status", None), "value", None) == "failure"
            else "terminal"
            if kernel.is_terminal(state)
            else "active"
        ),
        goal_ids=tuple(kernel.registered_goals),
        coverage=coverage_document,
    )
    model = portable.model
    model_document = model.to_dict()
    if len(model.cells) != 11 or len(model_document["nominal"]) != 20:
        raise Phase3CInvariantViolation("Phase3C 11-cell/20-entry golden changed")
    if load_model_from_document(model_document).model_id != model.model_id:
        raise Phase3CInvariantViolation("portable RAPM round trip changed model ID")

    structural_id = object_id(kernel.structural_key(), "structural")
    epoch_payload = {
        "structural_id": structural_id,
        "kernel_sha256": canonical_sha256(kernel.structural_key()),
        "coverage_id": model.coverage_id,
        "coverage": coverage.descriptor(),
        "portable_rapm_id": model.model_id,
        "partition_id": object_id(model_document["partition"], "partition"),
        "nominal_model_id": object_id(model_document["nominal"], "nominal"),
        "sound_envelope_id": object_id(model_document["envelope"], "envelope"),
        "concretizer_id": object_id(
            model_document["concretizer_registry"], "concretizer"
        ),
        "construction_source": "frozen_v0_026_first_revision_snapshot",
        "consumption_is_query_neutral": True,
        "query_results_used_for_phase3c_build": False,
        "covered_ground_states": 192,
        "ground_state_action_pairs": sum(
            len(kernel.actions(state))
            for state in states
            if not kernel.is_terminal(state)
        ),
        "abstract_cells": len(partition.cell_ids),
        "abstract_state_action_pairs": len(models.nominal.entries),
        "source_tree_sha256": _source_tree_hash(),
    }
    epoch = {
        "build_epoch_id": object_id(epoch_payload, "build-epoch"),
        **epoch_payload,
    }
    return Phase3CWorld(
        kernel,
        adapter,
        coverage,
        partition,
        models,
        portable,
        queries,
        structural_id,
        epoch,
    )


def load_model_from_document(document: dict[str, Any]) -> Any:
    """Validate one model document without relying on a persistent file."""

    from acfqp.portable import PortableRAPM

    return PortableRAPM.from_dict(document)


def _select_recovery_proposal(result: PortablePlanResult) -> tuple[PortableParetoPoint, str]:
    if result.selected is not None:
        return result.selected, "nominal_constrained_selection"
    if not result.frontier:
        raise Phase3CInvariantViolation("portable planner emitted no diagnostic frontier")
    return (
        min(
            result.frontier,
            key=lambda point: (
                -point.expected_reward,
                point.failure_probability,
                point.policy.signature(),
            ),
        ),
        "max_reward_then_min_risk_frontier_for_certificate_recovery",
    )


def _system_mounts() -> tuple[str, ...]:
    mounts: list[str] = []
    for system_path in ("/usr", "/lib", "/lib64"):
        if Path(system_path).exists():
            mounts.extend(("--ro-bind", system_path, system_path))
    return tuple(mounts)


def _isolated_python() -> str:
    """Return an interpreter path guaranteed to exist inside the system mounts."""

    candidate = shutil.which("python3", path="/usr/bin:/bin")
    if candidate is None:
        raise Phase3CInvariantViolation(
            "Phase3C isolation requires a system python3 under /usr/bin or /bin"
        )
    return str(Path(candidate).resolve())


def run_fresh_portable_proposals(
    world: Phase3CWorld,
) -> tuple[FrozenPortableProposal, FrozenPortableProposal]:
    """Freeze both abstract proposals before any local/J0 authority is opened."""

    bubblewrap = shutil.which("bwrap")
    if bubblewrap is None:
        raise Phase3CInvariantViolation("Phase3C requires bubblewrap")
    proposals: list[FrozenPortableProposal] = []
    with tempfile.TemporaryDirectory(prefix="acfqp-phase3c-portable-") as temporary:
        root = Path(temporary)
        runtime_package = root / "runtime" / "acfqp"
        input_root = root / "input"
        runtime_package.mkdir(parents=True)
        input_root.mkdir()
        for module_name in ("portable.py", "portable_planner.py", "portable_runtime.py"):
            shutil.copy2(PROJECT_ROOT / "src" / "acfqp" / module_name, runtime_package)
        model_path = input_root / "model.json"
        dump_model(world.portable.model, model_path)

        for ordinal, registered in enumerate(world.queries, start=1):
            occurrence = root / f"occurrence-{ordinal:03d}"
            occurrence_input = occurrence / "input"
            output_root = occurrence / "output"
            occurrence_input.mkdir(parents=True)
            output_root.mkdir()
            portable_query = world.portable.query_from_spec(registered.query)
            query_path = occurrence_input / "query.json"
            result_path = output_root / "result.json"
            attestation_path = output_root / "attestation.json"
            dump_query(portable_query, query_path)
            process = subprocess.run(
                (
                    bubblewrap,
                    "--unshare-all",
                    "--die-with-parent",
                    "--new-session",
                    "--clearenv",
                    *_system_mounts(),
                    "--proc",
                    "/proc",
                    "--dev",
                    "/dev",
                    "--tmpfs",
                    "/tmp",
                    "--ro-bind",
                    str(root / "runtime"),
                    "/runtime",
                    "--dir",
                    "/input",
                    "--ro-bind",
                    str(model_path),
                    "/input/model.json",
                    "--ro-bind",
                    str(query_path),
                    "/input/query.json",
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
                    str(PROJECT_ROOT),
                    _isolated_python(),
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
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120,
                check=False,
            )
            if process.returncode != 0 or process.stdout or process.stderr:
                raise Phase3CInvariantViolation(
                    "closed portable planner failed: "
                    f"query={registered.query_key!r}, rc={process.returncode}, "
                    f"stdout={process.stdout!r}, stderr={process.stderr!r}"
                )
            result = load_result(
                result_path,
                model=world.portable.model,
                query=portable_query,
            )
            attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
            payload = dict(attestation)
            identifier = payload.pop("attestation_id", None)
            expected_sources = {
                f"acfqp.{module_name[:-3]}": sha256_file(
                    PROJECT_ROOT / "src" / "acfqp" / module_name
                )
                for module_name in (
                    "portable.py",
                    "portable_planner.py",
                    "portable_runtime.py",
                )
            }
            if (
                identifier != logical_id("runtime-attestation", payload)
                or payload.get("schema")
                != "acfqp.portable_runtime_attestation.v1"
                or payload.get("model_id") != world.portable.model.model_id
                or payload.get("query_id") != portable_query.query_id
                or payload.get("result_id") != result.result_id
                or payload.get("project_checkout_visible") is not False
                or payload.get("network_namespace_unshared") is not True
                or payload.get("python_site_disabled") is not True
                or payload.get("forbidden_modules_resolved") != []
                or payload.get("unexpected_module_origins") != []
                or payload.get("input_regular_files") != ["model.json", "query.json"]
                or payload.get("output_regular_files_before") != []
                or payload.get("runtime_source_sha256") != expected_sources
            ):
                raise Phase3CInvariantViolation(
                    "closed portable-planner attestation failed"
                )
            proposal, source = _select_recovery_proposal(result)
            proposals.append(
                FrozenPortableProposal(
                    registered,
                    object_id(registered.query, "query"),
                    portable_query,
                    result,
                    proposal,
                    source,
                    attestation,
                )
            )
    if len(proposals) != 2:
        raise Phase3CInvariantViolation("Phase3C must freeze exactly two proposals")
    return tuple(proposals)  # type: ignore[return-value]


def _decode_policy(
    world: Phase3CWorld, proposal: FrozenPortableProposal
) -> FiniteHorizonPolicy[Any, Any]:
    return FiniteHorizonPolicy.from_mapping(
        world.portable.decode_policy(proposal.proposal.policy)
    )


def _worker_input_bytes(document: Any) -> bytes:
    return (
        json.dumps(
            to_jsonable(document),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _write_canonical_json(path: Path, document: Any) -> None:
    path.write_bytes(_worker_input_bytes(document))


def _worker_input_sha256(document: Any) -> str:
    return hashlib.sha256(_worker_input_bytes(document)).hexdigest()


def run_fresh_local_solver(
    boundary_view: dict[str, Any],
    ground_slice: dict[str, Any],
    request: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the stdlib-only repair worker with no model/kernel/project mount."""

    bubblewrap = shutil.which("bwrap")
    if bubblewrap is None:
        raise Phase3CInvariantViolation("Phase3C local recovery requires bubblewrap")
    with tempfile.TemporaryDirectory(prefix="acfqp-phase3c-local-") as temporary:
        root = Path(temporary)
        runtime = root / "runtime"
        input_root = root / "input"
        output_root = root / "output"
        runtime.mkdir()
        input_root.mkdir()
        output_root.mkdir()
        for module_name in ("local_solver.py", "local_runtime.py"):
            shutil.copy2(PROJECT_ROOT / "src" / "acfqp" / module_name, runtime)
        boundary_path = input_root / "boundary.json"
        slice_path = input_root / "slice.json"
        request_path = input_root / "request.json"
        result_path = output_root / "result.json"
        attestation_path = output_root / "attestation.json"
        _write_canonical_json(boundary_path, boundary_view)
        _write_canonical_json(slice_path, ground_slice)
        _write_canonical_json(request_path, request)
        process = subprocess.run(
            (
                bubblewrap,
                "--unshare-all",
                "--die-with-parent",
                "--new-session",
                "--clearenv",
                *_system_mounts(),
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
                str(PROJECT_ROOT),
                _isolated_python(),
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
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            check=False,
        )
        if process.returncode != 0 or process.stdout or process.stderr:
            raise Phase3CInvariantViolation(
                "isolated local solver failed: "
                f"rc={process.returncode}, stdout={process.stdout!r}, "
                f"stderr={process.stderr!r}"
            )
        result = json.loads(result_path.read_text(encoding="utf-8"))
        attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
        replay = solve_local_recovery(boundary_view, ground_slice, request).to_dict()
        if result != replay:
            raise Phase3CInvariantViolation(
                "isolated local result disagrees with deterministic replay"
            )
        attestation_payload = dict(attestation)
        attestation_id = attestation_payload.pop("attestation_id", None)
        expected_sources = {
            f"acfqp.{module_name[:-3]}": sha256_file(
                PROJECT_ROOT / "src" / "acfqp" / module_name
            )
            for module_name in ("local_solver.py", "local_runtime.py")
        }
        if (
            attestation_id
            != logical_id("local-runtime-attestation", attestation_payload)
            or attestation_payload.get("schema")
            != "acfqp.local_runtime_attestation.v1"
            or attestation_payload.get("isolation_backend")
            != "bubblewrap_mount_and_network_namespace"
            or attestation_payload.get("isolation_profile")
            != "stdlib_json_allowlisted_ground_slice.v1"
            or attestation_payload.get("python_site_disabled") is not True
            or attestation_payload.get("project_checkout_visible") is not False
            or attestation_payload.get("network_namespace_unshared") is not True
            or attestation_payload.get("forbidden_modules_resolved") != []
            or attestation_payload.get("input_regular_files")
            != ["boundary.json", "request.json", "slice.json"]
            or attestation_payload.get("output_regular_files_before") != []
            or attestation_payload.get("boundary_sha256")
            != sha256_file(boundary_path)
            or attestation_payload.get("slice_sha256") != sha256_file(slice_path)
            or attestation_payload.get("request_sha256")
            != sha256_file(request_path)
            or attestation_payload.get("output_sha256") != sha256_file(result_path)
            or attestation_payload.get("request_id") != request["request_id"]
            or attestation_payload.get("occurrence_id") != request["occurrence_id"]
            or attestation_payload.get("boundary_view_id")
            != boundary_view["boundary_view_id"]
            or attestation_payload.get("slice_id") != ground_slice["slice_id"]
            or attestation_payload.get("result_id") != result["result_id"]
            or attestation_payload.get("forbidden_prefixes")
            != ["acfqp.domains", "acfqp.planning", "acfqp.ground"]
            or attestation_payload.get("forbidden_loaded_before") != []
            or attestation_payload.get("forbidden_loaded_after") != []
            or attestation_payload.get("loaded_acfqp_modules") != []
            or attestation_payload.get("unexpected_module_origins") != []
            or attestation_payload.get("runtime_source_sha256") != expected_sources
            or attestation_payload.get("claim_boundary")
            != (
                "integrity_and_reproducibility_evidence_only; "
                "not_host_or_process_provenance"
            )
        ):
            raise Phase3CInvariantViolation("isolated local runtime attestation failed")
        return result, attestation


def _query_payload(query: QuerySpec[Any]) -> dict[str, Any]:
    return {
        "initial_distribution": query.initial_distribution,
        "horizon": query.horizon,
        "reward_weights": query.reward_weights,
        "goal": query.goal,
        "delta": query.delta,
        "normalizer": query.normalizer,
        "normalizer_proof_id": query.normalizer_proof_id,
    }


def _policy_graph_document(
    world: Phase3CWorld,
    proposal: FrozenPortableProposal,
    policy: FiniteHorizonPolicy[Any, Any],
) -> dict[str, Any]:
    payload = {
        "query_key": proposal.registered.query_key,
        "ground_query_id": proposal.ground_query_id,
        "portable_query_id": proposal.portable_query.query_id,
        "portable_model_id": world.portable.model.model_id,
        "portable_result_id": proposal.result.result_id,
        "proposal_source": proposal.proposal_source,
        "selector_class": "deterministic_finite_horizon_markov",
        "decisions": tuple(
            {
                "remaining": decision.remaining,
                "cell": repr(decision.state),
                "semantic_action": repr(decision.action),
            }
            for decision in policy.decisions
        ),
    }
    return {"policy_graph_id": object_id(payload, "policy-graph"), **payload}


def _audit_document(
    *,
    audit: Any,
    query_key: str,
    query_id: str,
    policy_graph_id: str,
    model_id: str,
    stage: str,
) -> dict[str, Any]:
    payload = {
        "query_key": query_key,
        "ground_query_id": query_id,
        "policy_graph_id": policy_graph_id,
        "portable_model_id": model_id,
        "stage": stage,
        "unrestricted_reward_upper": audit.unrestricted_reward_upper,
        "lifted_reward_lower": audit.lifted_reward_lower,
        "lifted_failure_upper": audit.lifted_failure_upper,
        "regret_upper": audit.regret_upper,
        "regret_tolerance": audit.regret_tolerance,
        "risk_tolerance": audit.risk_tolerance,
        "certified": audit.certified,
        "issues": tuple(
            {
                "code": issue.code,
                "cell": repr(issue.cell),
                "remaining": issue.remaining,
                "detail": issue.detail,
            }
            for issue in audit.issues
        ),
        "reachable_bounds": tuple(
            {
                "cell": repr(bound.cell),
                "remaining": bound.remaining,
                "reward_lower": bound.reward_lower,
                "failure_upper": bound.failure_upper,
            }
            for bound in audit.reachable_bounds
        ),
    }
    return {"audit_id": object_id(payload, "audit"), **payload}


def _proof_graph_document(
    graph: FailedProofGraph,
    *,
    pre_audit_id: str,
    state_ids: dict[Hashable, str],
) -> dict[str, Any]:
    nodes = tuple(
        {
            "node_id": node.node_id,
            "cell": repr(node.cell),
            "remaining": node.remaining,
            "selected_action": repr(node.selected_action),
            "normalized_reward_min": node.normalized_reward_min,
            "normalized_reward_max": node.normalized_reward_max,
            "normalized_reward_range": node.normalized_reward_range,
            "failure_min": node.failure_min,
            "failure_max": node.failure_max,
            "failure_range": node.failure_range,
            "max_pair_successor_tv": node.max_pair_successor_tv,
            "direct_bad": node.direct_bad,
            "inherited_bad": node.inherited_bad,
            "audit_reward_lower": node.audit_reward_lower,
            "audit_failure_upper": node.audit_failure_upper,
            "issue_codes": node.issue_codes,
            "witnesses": tuple(
                {
                    "witness_id": witness.witness_id,
                    "left_state_id": state_ids[witness.left_state],
                    "right_state_id": state_ids[witness.right_state],
                    "normalized_reward_gap": witness.normalized_reward_gap,
                    "failure_gap": witness.failure_gap,
                    "successor_tv": witness.successor_tv,
                    "separates": witness.separates,
                }
                for witness in node.witnesses
            ),
        }
        for node in graph.nodes
    )
    edges = tuple(
        {
            "edge_id": edge.edge_id,
            "source_node_id": edge.source_node_id,
            "target_node_id": edge.target_node_id,
            "probability_lower": edge.probability_lower,
            "probability_upper": edge.probability_upper,
            "supporting_state_ids": edge.supporting_state_ids,
        }
        for edge in graph.edges
    )
    return {
        "schema": "acfqp.failed_proof_graph.v1",
        "graph_id": graph.graph_id,
        "pre_audit_id": pre_audit_id,
        "audit_certified": graph.audit_certified,
        "root_node_ids": graph.root_node_ids,
        "nodes": nodes,
        "edges": edges,
        "complete_unordered_realization_pair_inventory": True,
        "positive_witness_count": sum(
            witness["separates"]
            for node in nodes
            for witness in node["witnesses"]
        ),
    }


def _frontier_document(
    frontier: FailedProofFrontier,
    world: Phase3CWorld,
    proof_document: dict[str, Any],
    state_ids: dict[Hashable, str],
) -> dict[str, Any]:
    records = tuple(
        {
            "node_id": node.node_id,
            "cell": repr(node.cell),
            "remaining": node.remaining,
            "member_state_ids": tuple(
                sorted(state_ids[state] for state in world.partition.members(node.cell))
            ),
            "direct_bad": node.direct_bad,
            "strict_direct_bad_ancestor_count": 0,
            "positive_witness_ids": tuple(
                witness.witness_id for witness in node.witnesses if witness.separates
            ),
        }
        for node in frontier.nodes
    )
    return {
        "schema": "acfqp.failed_proof_frontier.v1",
        "frontier_id": frontier.frontier_id,
        "failed_proof_graph_id": frontier.graph_id,
        "pre_audit_id": proof_document["pre_audit_id"],
        "definition": "earliest_policy_reachable_DirectBad_antichain",
        "recursive_ancestor_bounds_are_not_direct_bad": True,
        "nodes": records,
        "frontier_node_count": len(records),
        "frontier_state_count": sum(len(record["member_state_ids"]) for record in records),
        "positive_witness_count": sum(
            len(record["positive_witness_ids"]) for record in records
        ),
    }


def _authorization_document(
    authorization: LocalRecoveryAuthorization,
    *,
    model_id: str,
    query_id: str,
) -> dict[str, Any]:
    def records(pairs: Iterable[tuple[Hashable, Hashable]]) -> tuple[dict[str, str], ...]:
        return tuple(
            {
                "state_id": object_id(state, "state"),
                "action_id": object_id(action, "ground-action"),
            }
            for state, action in pairs
        )

    frontier_records = records(authorization.frontier_state_actions)
    reverse_records = records(authorization.reverse_dependency_state_actions)
    return {
        "schema": "acfqp.local_recovery_authorization.v1",
        "authorization_id": authorization.authorization_id,
        "frontier_id": authorization.frontier_id,
        "portable_model_id": model_id,
        "ground_query_id": query_id,
        "frontier_state_actions": frontier_records,
        "reverse_selected_dependency_state_actions": reverse_records,
        "frontier_state_action_count": len(frontier_records),
        "reverse_dependency_state_action_count": len(reverse_records),
        "authorized_state_action_count": len(frontier_records) + len(reverse_records),
        "reverse_dependency_rule": "strict_ancestor_selected_concretizer_support_only",
        "coverage_extension_allowed": False,
        "full_ground_model_or_j0_allowed": False,
    }


def _same_query_all_action_counts(kernel: Any, query: QuerySpec[Any]) -> dict[str, int]:
    pending = [
        (query.horizon, state)
        for probability, state in query.initial_distribution
        if probability > 0
    ]
    visited: set[tuple[int, Hashable]] = set()
    action_count = 0
    outcome_count = 0
    while pending:
        remaining, state = pending.pop()
        marker = (remaining, state)
        if marker in visited or remaining <= 0 or kernel.is_terminal(state):
            continue
        visited.add(marker)
        for action in kernel.actions(state):
            action_count += 1
            outcomes = tuple(kernel.step(state, action))
            outcome_count += len(outcomes)
            if remaining <= 1:
                continue
            for outcome in outcomes:
                if not outcome.failure and not outcome.terminal and not kernel.is_terminal(
                    outcome.next_state
                ):
                    pending.append((remaining - 1, outcome.next_state))
    return {
        "decision_state_time_pairs": len(visited),
        "state_action_pairs": action_count,
        "positive_probability_outcomes": outcome_count,
    }


def _overlay_from_result(
    world: Phase3CWorld,
    proposal: FrozenPortableProposal,
    policy: FiniteHorizonPolicy[Any, Any],
    frontier: FailedProofFrontier,
    authorization: LocalRecoveryAuthorization,
    result: dict[str, Any],
) -> HybridPolicyOverlay:
    state_by_id = {
        object_id(state, "state"): state for state in world.coverage.covered_states
    }
    action_by_pair = {
        (object_id(state, "state"), object_id(action, "ground-action")): action
        for state, action in authorization.allowed_state_actions
    }
    node_by_id = {node.node_id: node for node in frontier.nodes}
    decisions: list[GroundPatchDecision] = []
    for record in result["decisions"]:
        try:
            node = node_by_id[record["node_id"]]
            state = state_by_id[record["state_id"]]
            action = action_by_pair[(record["state_id"], record["action_id"])]
        except KeyError as error:
            raise Phase3CInvariantViolation(
                "isolated local result escaped its proof authorization"
            ) from error
        if state not in set(world.partition.members(node.cell)):
            raise Phase3CInvariantViolation("local result state is outside its frontier cell")
        decisions.append(
            GroundPatchDecision(record["remaining"], node.cell, state, action)
        )
    return HybridPolicyOverlay(
        policy,
        tuple(decisions),
        proposal.ground_query_id,
        frontier.frontier_id,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/phase3c"))
    arguments = parser.parse_args(argv)
    try:
        summary = run_phase3c(arguments.output)
    except Phase3CInvariantViolation as error:
        print(
            json.dumps(
                {"status": error.status, "detail": str(error)},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(to_jsonable(summary), ensure_ascii=False, sort_keys=True))
    return 0


def run_phase3c(output_dir: Path) -> dict[str, Any]:
    """Run, freeze, and integrity-check the contract-0.8 campaign."""

    started_at = _utc_now()
    world = construct_phase3c_world()
    model_document = world.portable.model.to_dict()
    base_model_sha256 = serialized_json_sha256(model_document)
    base_build_epoch_sha256 = serialized_json_sha256(world.build_epoch)
    proposals = run_fresh_portable_proposals(world)

    workload_payload = {
        "profile_key": PROFILE_KEY,
        "build_epoch_id": world.build_epoch["build_epoch_id"],
        "portable_rapm_id": world.portable.model.model_id,
        "coverage_id": world.portable.model.coverage_id,
        "ordered_ground_query_ids": tuple(
            proposal.ground_query_id for proposal in proposals
        ),
        "ordered_query_keys": tuple(
            proposal.registered.query_key for proposal in proposals
        ),
        "expected_routes": (
            "ABSTRACT_CERTIFIED",
            "LOCAL_GROUND_RECOVERY",
        ),
        "query_occurrence_count": 2,
        "all_portable_proposals_before_local_recovery": True,
        "all_portable_proposals_before_j0": True,
        "base_model_mutation_allowed": False,
        "fallback_allowed": False,
        "rebuild_allowed_for_pass": False,
    }
    workload_spec = {
        "workload_id": object_id(workload_payload, "workload"),
        **workload_payload,
    }
    occurrence_ids = tuple(
        object_id(
            {
                "workload_id": workload_spec["workload_id"],
                "ordinal": ordinal,
                "ground_query_id": proposal.ground_query_id,
                "portable_query_id": proposal.portable_query.query_id,
                "portable_model_id": world.portable.model.model_id,
            },
            "occurrence",
        )
        for ordinal, proposal in enumerate(proposals, start=1)
    )

    policies = tuple(_decode_policy(world, proposal) for proposal in proposals)
    policy_graphs = tuple(
        _policy_graph_document(world, proposal, policy)
        for proposal, policy in zip(proposals, policies, strict=True)
    )
    pre_audits = tuple(
        audit_abstract_policy(
            world.kernel,
            proposal.registered.query,
            world.models.envelope,
            policy,
            regret_tolerance=Fraction(1, 20),
        )
        for proposal, policy in zip(proposals, policies, strict=True)
    )
    pre_documents = tuple(
        _audit_document(
            audit=audit,
            query_key=proposal.registered.query_key,
            query_id=proposal.ground_query_id,
            policy_graph_id=graph["policy_graph_id"],
            model_id=world.portable.model.model_id,
            stage="pre_recovery",
        )
        for proposal, graph, audit in zip(
            proposals, policy_graphs, pre_audits, strict=True
        )
    )
    abstract_audit, local_pre_audit = pre_audits
    if (
        not abstract_audit.certified
        or abstract_audit.lifted_reward_lower != Fraction(1, 32)
        or abstract_audit.lifted_failure_upper != 0
        or abstract_audit.regret_upper != 0
        or local_pre_audit.certified
        or local_pre_audit.lifted_reward_lower != Fraction(3, 64)
        or local_pre_audit.lifted_failure_upper != Fraction(5099, 10000)
        or local_pre_audit.regret_upper != 0
        or proposals[0].result.selected is None
        or proposals[1].result.selected is not None
        or proposals[1].proposal.failure_probability != Fraction(21187, 80000)
    ):
        raise Phase3CInvariantViolation("pre-recovery route goldens changed")

    local_proposal = proposals[1]
    local_policy = policies[1]
    proof_graph = build_failed_proof_graph(
        world.kernel,
        local_proposal.registered.query,
        world.models.envelope,
        local_policy,
        local_pre_audit,
    )
    frontier = proof_graph.frontier()
    state_ids = {
        state: object_id(state, "state") for state in world.coverage.covered_states
    }
    proof_document = _proof_graph_document(
        proof_graph,
        pre_audit_id=pre_documents[1]["audit_id"],
        state_ids=state_ids,
    )
    frontier_document = _frontier_document(
        frontier, world, proof_document, state_ids
    )
    if (
        len(proof_graph.nodes) != 4
        or len(proof_graph.edges) != 4
        or len(proof_graph.direct_bad_nodes) != 2
        or len(proof_graph.inherited_bad_nodes) != 2
        or frontier_document["frontier_node_count"] != 2
        or frontier_document["frontier_state_count"] != 12
        or frontier_document["positive_witness_count"] != 19
        or any(node.remaining != 1 for node in frontier.nodes)
    ):
        raise Phase3CInvariantViolation("failed-proof frontier goldens changed")

    authorization = LocalRecoveryAuthorization.for_frontier(
        world.kernel,
        world.models.envelope,
        frontier,
        proof_graph,
    )
    authorization_document = _authorization_document(
        authorization,
        model_id=world.portable.model.model_id,
        query_id=local_proposal.ground_query_id,
    )
    if (
        authorization_document["frontier_state_action_count"] != 32
        or authorization_document["reverse_dependency_state_action_count"] != 8
        or authorization_document["authorized_state_action_count"] != 40
    ):
        raise Phase3CInvariantViolation("strict-local authorization golden changed")

    materialized_slice = materialize_authorized_slice(
        world.kernel,
        local_proposal.registered.query,
        world.models.envelope,
        frontier,
        authorization,
        state_payload=lambda state: {
            "board": state.board,
            "status": state.status.value,
        },
        action_payload=lambda action: {
            "first": action.first,
            "second": action.second,
            "survivor": action.survivor,
        },
    )
    ground_slice = redact_authorized_slice_for_worker(materialized_slice)
    boundary_view = build_redacted_boundary_view(
        local_proposal.registered.query,
        world.models.envelope,
        local_policy,
        proof_graph,
        unrestricted_reward_upper=local_pre_audit.unrestricted_reward_upper,
        regret_tolerance=local_pre_audit.regret_tolerance,
    )
    local_request_payload = {
        "schema": "acfqp.local_recovery_request.v1",
        "workload_id": workload_spec["workload_id"],
        "occurrence_id": occurrence_ids[1],
        "portable_model_id": world.portable.model.model_id,
        "build_epoch_id": world.build_epoch["build_epoch_id"],
        "ground_query_id": local_proposal.ground_query_id,
        "portable_query_id": local_proposal.portable_query.query_id,
        "portable_result_id": local_proposal.result.result_id,
        "pre_audit_id": pre_documents[1]["audit_id"],
        "failed_proof_graph_id": proof_graph.graph_id,
        "frontier_id": frontier.frontier_id,
        "authorization_id": authorization.authorization_id,
        "slice_id": ground_slice["slice_id"],
        "slice_sha256": _worker_input_sha256(ground_slice),
        "boundary_view_id": boundary_view["boundary_view_id"],
        "boundary_sha256": _worker_input_sha256(boundary_view),
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
    local_request = {
        "request_id": object_id(local_request_payload, "local-request"),
        **local_request_payload,
    }
    local_result, local_attestation = run_fresh_local_solver(
        boundary_view, ground_slice, local_request
    )
    overlay = _overlay_from_result(
        world,
        local_proposal,
        local_policy,
        frontier,
        authorization,
        local_result,
    )
    post_audit = audit_hybrid_policy(
        world.kernel,
        local_proposal.registered.query,
        world.models.envelope,
        overlay,
        regret_tolerance=Fraction(1, 20),
    )
    hybrid_lift = lift_hybrid_policy(
        world.kernel,
        local_proposal.registered.query,
        world.models.envelope,
        overlay,
    )
    abstract_overlay = HybridPolicyOverlay(
        policies[0],
        (),
        proposals[0].ground_query_id,
        "not-applicable-certified-plan",
    )
    abstract_lift = lift_hybrid_policy(
        world.kernel,
        proposals[0].registered.query,
        world.models.envelope,
        abstract_overlay,
    )
    if (
        local_result["localized_node_ids"]
        != [frontier.nodes[0].node_id]
        or len(local_result["decisions"]) != 8
        or local_result["candidate_subset_count"] != 2
        or not local_result["certified_safe"]
        or not local_result["certified_value"]
        or not local_result["certified"]
        or local_result["regret_upper"] != {"numerator": 0, "denominator": 1}
        or not post_audit.certified
        or post_audit.lifted_reward_lower != Fraction(3, 64)
        or post_audit.lifted_failure_upper != Fraction(397, 20000)
        or post_audit.regret_upper != 0
        or hybrid_lift.evaluation.expected_reward != Fraction(3, 64)
        or hybrid_lift.evaluation.failure_probability != Fraction(317, 16000)
        or hybrid_lift.patched_decision_count != 8
        or hybrid_lift.abstract_decision_count != 12
        or abstract_lift.evaluation.expected_reward != Fraction(1, 32)
        or abstract_lift.evaluation.failure_probability != 0
    ):
        raise Phase3CInvariantViolation("hybrid overlay/re-certification golden changed")

    post_document = _audit_document(
        audit=post_audit,
        query_key=local_proposal.registered.query_key,
        query_id=local_proposal.ground_query_id,
        policy_graph_id=policy_graphs[1]["policy_graph_id"],
        model_id=world.portable.model.model_id,
        stage="post_local_recovery",
    )
    post_document.update(
        {
            "overlay_id": overlay.overlay_id,
            "local_result_id": local_result["result_id"],
            "exact_hybrid_reward": hybrid_lift.evaluation.expected_reward,
            "exact_hybrid_failure": hybrid_lift.evaluation.failure_probability,
        }
    )
    post_document["post_recovery_audit_id"] = object_id(
        post_document, "post-recovery-audit"
    )

    localized_node_ids = set(local_result["localized_node_ids"])
    localized_nodes = tuple(
        node for node in frontier.nodes if node.node_id in localized_node_ids
    )
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
        base_support = {
            action
            for _, action in world.models.envelope.concretizer(
                decision.state, abstract_action
            )
        }
        if decision.action not in base_support:
            ground_distinction_changes += 1
    hybrid_payload = {
        "schema": "acfqp.hybrid_policy_overlay.v1",
        "overlay_id": overlay.overlay_id,
        "request_id": local_request["request_id"],
        "local_result_id": local_result["result_id"],
        "frontier_id": frontier.frontier_id,
        "ground_query_id": local_proposal.ground_query_id,
        "base_portable_model_id_before": world.portable.model.model_id,
        "base_portable_model_id_after": world.portable.model.model_id,
        "base_build_epoch_id_before": world.build_epoch["build_epoch_id"],
        "base_build_epoch_id_after": world.build_epoch["build_epoch_id"],
        "base_build_epoch_sha256_before": base_build_epoch_sha256,
        "base_build_epoch_sha256_after": serialized_json_sha256(world.build_epoch),
        "base_model_sha256_before": base_model_sha256,
        "base_model_sha256_after": serialized_json_sha256(
            world.portable.model.to_dict()
        ),
        "base_policy_graph_id": policy_graphs[1]["policy_graph_id"],
        "localized_node_ids": tuple(local_result["localized_node_ids"]),
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
        "ground_distinction_changes_from_base_concretizer": (
            ground_distinction_changes
        ),
        "retained_abstract_ground_decision_count": hybrid_lift.abstract_decision_count,
        "grammar_used": False,
        "portable_rapm_rebuilt": False,
        "query_scoped": True,
        "post_recovery_audit_id": post_document["post_recovery_audit_id"],
    }
    overlay_document = {
        "hybrid_policy_graph_id": object_id(
            hybrid_payload, "hybrid-policy-graph"
        ),
        **hybrid_payload,
    }

    route_payloads = (
        {
            "query_key": proposals[0].registered.query_key,
            "occurrence_id": occurrence_ids[0],
            "ground_query_id": proposals[0].ground_query_id,
            "portable_query_id": proposals[0].portable_query.query_id,
            "portable_model_id": world.portable.model.model_id,
            "build_epoch_id": world.build_epoch["build_epoch_id"],
            "route": "ABSTRACT_CERTIFIED",
            "pre_audit_id": pre_documents[0]["audit_id"],
            "hybrid_policy_graph_id": None,
            "local_ground_nodes": (),
            "certified": True,
            "reward_lower": abstract_audit.lifted_reward_lower,
            "failure_upper": abstract_audit.lifted_failure_upper,
            "regret_upper": abstract_audit.regret_upper,
            "risk_tolerance": abstract_audit.risk_tolerance,
            "full_ground_fallback_invocations": 0,
            "rebuild_invocations": 0,
        },
        {
            "query_key": local_proposal.registered.query_key,
            "occurrence_id": occurrence_ids[1],
            "ground_query_id": local_proposal.ground_query_id,
            "portable_query_id": local_proposal.portable_query.query_id,
            "portable_model_id": world.portable.model.model_id,
            "build_epoch_id": world.build_epoch["build_epoch_id"],
            "route": "LOCAL_GROUND_RECOVERY",
            "pre_audit_id": pre_documents[1]["audit_id"],
            "failed_proof_graph_id": proof_graph.graph_id,
            "frontier_id": frontier.frontier_id,
            "authorization_id": authorization.authorization_id,
            "local_request_id": local_request["request_id"],
            "local_result_id": local_result["result_id"],
            "hybrid_policy_graph_id": overlay_document["hybrid_policy_graph_id"],
            "post_recovery_audit_id": post_document["post_recovery_audit_id"],
            "local_ground_nodes": tuple(local_result["localized_node_ids"]),
            "certified": True,
            "reward_lower": post_audit.lifted_reward_lower,
            "failure_upper": post_audit.lifted_failure_upper,
            "regret_upper": post_audit.regret_upper,
            "risk_tolerance": post_audit.risk_tolerance,
            "full_ground_fallback_invocations": 0,
            "rebuild_invocations": 0,
        },
    )
    route_certificates = tuple(
        {"certificate_id": object_id(payload, "route-certificate"), **payload}
        for payload in route_payloads
    )
    terminal_freeze_payload = {
        "workload_id": workload_spec["workload_id"],
        "route_certificate_ids": tuple(
            certificate["certificate_id"] for certificate in route_certificates
        ),
        "hybrid_policy_graph_id": overlay_document["hybrid_policy_graph_id"],
        "base_portable_model_id": world.portable.model.model_id,
        "base_build_epoch_id": world.build_epoch["build_epoch_id"],
    }
    terminal_freeze_id = object_id(terminal_freeze_payload, "terminal-plan-freeze")

    # Evaluation-only boundary: no ground constrained optimizer is called above.
    ground_results = tuple(
        solve_ground_pareto(world.kernel, proposal.registered.query)
        for proposal in proposals
    )
    if any(result.selected is None for result in ground_results):
        raise Phase3CInvariantViolation("evaluation-only J0 unexpectedly infeasible")
    ground_points = tuple(result.selected for result in ground_results)
    if (
        ground_points[0].expected_reward != Fraction(1, 32)
        or ground_points[0].failure_probability != 0
        or ground_points[1].expected_reward != Fraction(3, 64)
        or ground_points[1].failure_probability != Fraction(99, 5000)
    ):
        raise Phase3CInvariantViolation("evaluation-only J0 golden changed")

    lifts = (abstract_lift, hybrid_lift)
    j0_rows = tuple(
        {
            "query_key": proposal.registered.query_key,
            "occurrence_id": occurrence_id,
            "ground_query_id": proposal.ground_query_id,
            "route_certificate_id": certificate["certificate_id"],
            "terminal_plan_freeze_id": terminal_freeze_id,
            "j0_started_after_terminal_plan_freeze": True,
            "j0_dependency_role": "evaluation_only",
            "ground_expected_reward": ground.expected_reward,
            "ground_failure_probability": ground.failure_probability,
            "lifted_expected_reward": lift.evaluation.expected_reward,
            "lifted_failure_probability": lift.evaluation.failure_probability,
            "reward_gap": ground.expected_reward - lift.evaluation.expected_reward,
            "failure_gap": (
                lift.evaluation.failure_probability - ground.failure_probability
            ),
            "abstract_composed_candidate_count": proposal.result.composed_candidate_count,
            "ground_composed_candidate_count": result.composed_candidate_count,
        }
        for proposal, occurrence_id, certificate, ground, result, lift in zip(
            proposals,
            occurrence_ids,
            route_certificates,
            ground_points,
            ground_results,
            lifts,
            strict=True,
        )
    )

    full_query_counts = _same_query_all_action_counts(
        world.kernel, local_proposal.registered.query
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
    if (
        full_query_counts
        != {
            "decision_state_time_pairs": 20,
            "state_action_pairs": 48,
            "positive_probability_outcomes": 192,
        }
        or frontier_outcomes != 128
        or reverse_outcomes != 32
        or coverage_outcomes != 576
        or not (
            len(authorization.frontier_state_actions)
            < len(authorization.allowed_state_actions)
            < full_query_counts["state_action_pairs"]
            < world.build_epoch["ground_state_action_pairs"]
        )
    ):
        raise Phase3CInvariantViolation("strict-locality accounting golden changed")
    locality = {
        "portable_model_id_before": world.portable.model.model_id,
        "portable_model_id_after": world.portable.model.model_id,
        "build_epoch_id_before": world.build_epoch["build_epoch_id"],
        "build_epoch_id_after": world.build_epoch["build_epoch_id"],
        "base_build_epoch_sha256_before": base_build_epoch_sha256,
        "base_build_epoch_sha256_after": serialized_json_sha256(world.build_epoch),
        "base_model_sha256_before": base_model_sha256,
        "base_model_sha256_after": serialized_json_sha256(
            world.portable.model.to_dict()
        ),
        "coverage_ground_states": len(world.coverage.covered_states),
        "coverage_ground_state_action_pairs": world.build_epoch[
            "ground_state_action_pairs"
        ],
        "coverage_positive_probability_outcomes": coverage_outcomes,
        "full_same_query_all_action_graph": full_query_counts,
        "frontier_states": frontier_document["frontier_state_count"],
        "frontier_state_action_pairs": len(
            authorization.frontier_state_actions
        ),
        "frontier_positive_probability_outcomes": frontier_outcomes,
        "reverse_selected_dependency_state_action_pairs": len(
            authorization.reverse_dependency_state_actions
        ),
        "reverse_selected_dependency_positive_probability_outcomes": (
            reverse_outcomes
        ),
        "authorized_state_action_pairs": len(authorization.allowed_state_actions),
        "authorized_positive_probability_outcomes": (
            frontier_outcomes + reverse_outcomes
        ),
        "worker_mounted_state_action_pairs": len(
            authorization.frontier_state_actions
        ),
        "worker_mounted_reverse_dependencies": False,
        "localized_states": len(localized_states),
        "localized_available_state_action_pairs": len(localized_pairs),
        "localized_available_positive_probability_outcomes": localized_outcomes,
        "patch_decisions": len(overlay.decisions),
        "ground_distinction_changes_from_base_concretizer": (
            ground_distinction_changes
        ),
        "retained_abstract_ground_decisions": hybrid_lift.abstract_decision_count,
        "retained_abstract_cell_horizon_pairs": 3,
        "strict_worker_locality": (
            len(authorization.frontier_state_actions)
            < full_query_counts["state_action_pairs"]
        ),
        "strict_authorization_locality": (
            len(authorization.allowed_state_actions)
            < full_query_counts["state_action_pairs"]
        ),
        "strict_coverage_locality": (
            len(authorization.allowed_state_actions)
            < world.build_epoch["ground_state_action_pairs"]
        ),
        "hybrid_retains_abstract_planning": hybrid_lift.abstract_decision_count > 0,
        "base_rapm_immutable": True,
        "coverage_extended": False,
        "full_ground_fallback_invocations": 0,
        "rebuild_invocations": 0,
    }
    if (
        locality["localized_states"] != 8
        or locality["localized_available_state_action_pairs"] != 16
        or locality["localized_available_positive_probability_outcomes"] != 64
        or locality["patch_decisions"] != 8
        or locality["ground_distinction_changes_from_base_concretizer"] != 4
        or not all(
            locality[key]
            for key in (
                "strict_worker_locality",
                "strict_authorization_locality",
                "strict_coverage_locality",
                "hybrid_retains_abstract_planning",
                "base_rapm_immutable",
            )
        )
    ):
        raise Phase3CInvariantViolation("localized overlay nontriviality changed")

    query_registry = {
        "records": tuple(
            {
                "ordinal": ordinal,
                "occurrence_id": occurrence_id,
                "query_key": proposal.registered.query_key,
                "ground_query_id": proposal.ground_query_id,
                "ground_query": _query_payload(proposal.registered.query),
                "portable_query_id": proposal.portable_query.query_id,
                "portable_model_id": world.portable.model.model_id,
                "expected_route": proposal.registered.expected_route,
            }
            for ordinal, (occurrence_id, proposal) in enumerate(
                zip(occurrence_ids, proposals, strict=True), start=1
            )
        ),
        "same_base_model_for_every_query": True,
        "query_values_used_to_mutate_base_model": False,
    }
    portable_query_rows = tuple(
        {
            "occurrence_id": occurrence_id,
            "query_key": proposal.registered.query_key,
            "ground_query_id": proposal.ground_query_id,
            "portable_query_id": proposal.portable_query.query_id,
            "portable_query": proposal.portable_query.to_dict(),
        }
        for occurrence_id, proposal in zip(occurrence_ids, proposals, strict=True)
    )
    portable_plan_rows = tuple(
        {
            "occurrence_id": occurrence_id,
            "query_key": proposal.registered.query_key,
            "ground_query_id": proposal.ground_query_id,
            "portable_query_id": proposal.portable_query.query_id,
            "portable_model_id": world.portable.model.model_id,
            "portable_result_id": proposal.result.result_id,
            "plan_result": proposal.result.to_dict(),
            "proposal_source": proposal.proposal_source,
            "proposal_policy": proposal.proposal.policy.to_dict(),
            "fresh_process": True,
            "ground_kernel_available_to_planner": False,
            "ground_j0_available_to_planner": False,
            "runtime_attestation": proposal.attestation,
        }
        for occurrence_id, proposal in zip(occurrence_ids, proposals, strict=True)
    )
    access_trace = {
        "authorization_id": authorization.authorization_id,
        "slice_id": ground_slice["slice_id"],
        "runtime_attestation_id": local_attestation["attestation_id"],
        "trusted_slice_materializer_access_log": materialized_slice["access_log"],
        "trusted_slice_actions_calls": sum(
            record["operation"] == "actions"
            for record in materialized_slice["access_log"]
        ),
        "trusted_slice_step_calls": sum(
            record["operation"] == "step"
            for record in materialized_slice["access_log"]
        ),
        "worker_input_state_action_rows": len(
            authorization.frontier_state_actions
        ),
        "reverse_dependency_rows_mounted_to_worker": 0,
        "worker_read_outside_slice": False,
        "project_checkout_visible": False,
        "portable_rapm_visible": False,
        "ground_kernel_visible": False,
        "coverage_visible": False,
        "j0_visible": False,
    }

    def abstract_realization_rows(
        audit: Any, policy: FiniteHorizonPolicy[Any, Any]
    ) -> int:
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

    runtime_model_bytes = len(_worker_input_bytes(model_document))
    artifact_model_bytes = len(serialized_json_bytes(model_document))
    artifact_epoch_bytes = len(serialized_json_bytes(world.build_epoch))
    worker_slice_bytes = len(_worker_input_bytes(ground_slice))
    worker_boundary_bytes = len(_worker_input_bytes(boundary_view))
    worker_request_bytes = len(_worker_input_bytes(local_request))
    worker_result_bytes = len(_worker_input_bytes(local_result))
    work_counters = {
        "cost_protocol_status": ECONOMICS_NOT_RUN,
        "scalar_break_even": None,
        "build": {
            "build_invocations": 1,
            "covered_ground_states": len(world.coverage.covered_states),
            "ground_state_action_pairs": world.build_epoch[
                "ground_state_action_pairs"
            ],
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
                "portable_query_loaded_bytes": len(
                    _worker_input_bytes(proposals[0].portable_query.to_dict())
                ),
                "abstract_plan_invocations": 1,
                "abstract_plan_composed_candidates": proposals[
                    0
                ].result.composed_candidate_count,
                "pre_certificate_proof_nodes": len(
                    abstract_audit.reachable_bounds
                ),
                "pre_certificate_audit_invocations": 1,
                "pre_certificate_realization_rows": abstract_realization_rows(
                    abstract_audit, policies[0]
                ),
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
                "evaluation_only_j0_composed_candidates": ground_results[
                    0
                ].composed_candidate_count,
                "base_load": {
                    "model_invocations": 1,
                    "model_bytes": runtime_model_bytes,
                    "query_invocations": 1,
                    "query_bytes": len(
                        _worker_input_bytes(proposals[0].portable_query.to_dict())
                    ),
                },
                "abstract_plan": {
                    "invocations": 1,
                    "composed_candidates": proposals[0].result.composed_candidate_count,
                    "frontier_points": len(proposals[0].result.frontier),
                    "selected_policy_decisions": len(
                        proposals[0].proposal.policy.decisions
                    ),
                },
                "pre_certificate_audit": {
                    "invocations": 1,
                    "cell_horizon_pairs": len(abstract_audit.reachable_bounds),
                    "realization_rows": abstract_realization_rows(
                        abstract_audit, policies[0]
                    ),
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
                    "composed_candidates": ground_results[
                        0
                    ].composed_candidate_count,
                },
            },
            {
                "occurrence_id": occurrence_ids[1],
                "route": "LOCAL_GROUND_RECOVERY",
                "portable_model_load_invocations": 1,
                "portable_model_loaded_bytes": runtime_model_bytes,
                "portable_query_load_invocations": 1,
                "portable_query_loaded_bytes": len(
                    _worker_input_bytes(proposals[1].portable_query.to_dict())
                ),
                "abstract_plan_invocations": 1,
                "abstract_plan_composed_candidates": proposals[
                    1
                ].result.composed_candidate_count,
                "pre_certificate_proof_nodes": len(proof_graph.nodes),
                "pre_certificate_proof_edges": len(proof_graph.edges),
                "pre_certificate_audit_invocations": 1,
                "pre_certificate_realization_rows": abstract_realization_rows(
                    local_pre_audit, policies[1]
                ),
                "complete_realization_pair_witnesses": sum(
                    len(node.witnesses) for node in proof_graph.nodes
                ),
                "positive_failed_witnesses": proof_document[
                    "positive_witness_count"
                ],
                "direct_failed_nodes": len(proof_graph.direct_bad_nodes),
                "inherited_failed_nodes": len(proof_graph.inherited_bad_nodes),
                "frontier_extraction_invocations": 1,
                "frontier_nodes": len(frontier.nodes),
                "frontier_states": frontier_document["frontier_state_count"],
                "frontier_state_action_pairs": len(
                    authorization.frontier_state_actions
                ),
                "frontier_positive_probability_outcomes": frontier_outcomes,
                "reverse_dependency_state_action_pairs": len(
                    authorization.reverse_dependency_state_actions
                ),
                "reverse_dependency_positive_probability_outcomes": reverse_outcomes,
                "authorized_state_action_pairs": len(
                    authorization.allowed_state_actions
                ),
                "authorization_invocations": 1,
                "slice_materialization_invocations": 1,
                "worker_slice_bytes": worker_slice_bytes,
                "worker_boundary_bytes": worker_boundary_bytes,
                "worker_request_bytes": worker_request_bytes,
                "local_runtime_invocations": 1,
                "local_runtime_result_bytes": worker_result_bytes,
                "local_solver_candidate_subsets": local_result[
                    "candidate_subset_count"
                ],
                "local_solver_action_rows": len(
                    authorization.frontier_state_actions
                ),
                "patch_decisions": len(overlay.decisions),
                "localized_available_state_action_pairs": len(localized_pairs),
                "hybrid_stitch_invocations": 1,
                "hybrid_retained_abstract_ground_decisions": (
                    hybrid_lift.abstract_decision_count
                ),
                "post_certificate_audit_invocations": 1,
                "post_certificate_reachable_pairs": len(
                    post_audit.reachable_bounds
                ),
                "post_certificate_behavior_rows": post_behavior_rows,
                "full_fallback_invocations": 0,
                "rebuild_invocations": 0,
                "evaluation_only_j0_invocations": 1,
                "evaluation_only_j0_composed_candidates": ground_results[
                    1
                ].composed_candidate_count,
                "base_load": {
                    "model_invocations": 1,
                    "model_bytes": runtime_model_bytes,
                    "query_invocations": 1,
                    "query_bytes": len(
                        _worker_input_bytes(proposals[1].portable_query.to_dict())
                    ),
                },
                "abstract_plan": {
                    "invocations": 1,
                    "composed_candidates": proposals[1].result.composed_candidate_count,
                    "frontier_points": len(proposals[1].result.frontier),
                    "selected_policy_decisions": len(
                        proposals[1].proposal.policy.decisions
                    ),
                },
                "pre_certificate_audit": {
                    "invocations": 1,
                    "cell_horizon_pairs": len(local_pre_audit.reachable_bounds),
                    "realization_rows": abstract_realization_rows(
                        local_pre_audit, policies[1]
                    ),
                    "proof_nodes": len(proof_graph.nodes),
                    "proof_edges": len(proof_graph.edges),
                    "witnesses": sum(
                        len(node.witnesses) for node in proof_graph.nodes
                    ),
                },
                "frontier_extraction": {
                    "invocations": 1,
                    "direct_failed_nodes": len(proof_graph.direct_bad_nodes),
                    "inherited_failed_nodes": len(proof_graph.inherited_bad_nodes),
                    "frontier_nodes": len(frontier.nodes),
                    "frontier_states": frontier_document["frontier_state_count"],
                },
                "slice_materialization": {
                    "invocations": 1,
                    "state_action_pairs": len(
                        authorization.frontier_state_actions
                    ),
                    "positive_probability_outcomes": frontier_outcomes,
                    "worker_bytes": worker_slice_bytes,
                    "trusted_actions_calls": access_trace[
                        "trusted_slice_actions_calls"
                    ],
                    "trusted_step_calls": access_trace[
                        "trusted_slice_step_calls"
                    ],
                },
                "isolated_local_plan": {
                    "invocations": 1,
                    "candidate_subsets": local_result["candidate_subset_count"],
                    "action_rows": len(authorization.frontier_state_actions),
                    "input_bytes": (
                        worker_slice_bytes
                        + worker_boundary_bytes
                        + worker_request_bytes
                    ),
                    "result_bytes": worker_result_bytes,
                },
                "hybrid_stitch": {
                    "invocations": 1,
                    "patch_decisions": len(overlay.decisions),
                    "localized_cell_horizon_pairs": len(
                        overlay.localized_cell_horizon_pairs
                    ),
                    "retained_abstract_ground_decisions": (
                        hybrid_lift.abstract_decision_count
                    ),
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
                    "composed_candidates": ground_results[
                        1
                    ].composed_candidate_count,
                },
            },
        ),
    }
    work_counters["reconciliation"] = {
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
        "full_same_query_state_action_pairs": full_query_counts[
            "state_action_pairs"
        ],
        "coverage_state_action_pairs": world.build_epoch[
            "ground_state_action_pairs"
        ],
        "evaluation_only_j0_composed_candidates": sum(
            result.composed_candidate_count for result in ground_results
        ),
    }
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
    report = {
        "report_id": object_id(report_payload, "phase3c-report"),
        **report_payload,
    }
    metrics = {
        "ground_coverage_states": len(world.coverage.covered_states),
        "ground_coverage_state_action_pairs": world.build_epoch[
            "ground_state_action_pairs"
        ],
        "base_abstract_cells": len(world.partition.cell_ids),
        "base_abstract_state_action_pairs": len(world.models.nominal.entries),
        "query_occurrences": 2,
        "routes": ("ABSTRACT_CERTIFIED", "LOCAL_GROUND_RECOVERY"),
        "pre_local_failure_upper": local_pre_audit.lifted_failure_upper,
        "post_local_failure_upper": post_audit.lifted_failure_upper,
        "exact_hybrid_failure": hybrid_lift.evaluation.failure_probability,
        "ground_optimal_failure": ground_points[1].failure_probability,
        "frontier_states": frontier_document["frontier_state_count"],
        "authorized_state_action_pairs": len(authorization.allowed_state_actions),
        "localized_states": len(localized_states),
        "patch_decisions": len(overlay.decisions),
        "retained_abstract_ground_decisions": hybrid_lift.abstract_decision_count,
        "full_fallback_invocations": 0,
        "rebuild_invocations": 0,
    }
    events = (
        {"sequence": 1, "event": "workload_and_base_epoch_frozen"},
        {"sequence": 2, "event": "portable_rapm_roundtrip_verified"},
        {"sequence": 3, "event": "all_portable_proposals_complete"},
        {"sequence": 4, "event": "abstract_control_certificate_passed"},
        {"sequence": 5, "event": "local_query_pre_certificate_failed"},
        {"sequence": 6, "event": "direct_failed_proof_frontier_frozen"},
        {"sequence": 7, "event": "strict_local_authorization_frozen"},
        {"sequence": 8, "event": "isolated_local_result_frozen"},
        {"sequence": 9, "event": "hybrid_overlay_and_post_audit_frozen"},
        {
            "sequence": 10,
            "event": "all_terminal_route_certificates_frozen",
            "terminal_plan_freeze_id": terminal_freeze_id,
        },
        {"sequence": 11, "event": "evaluation_only_j0_started"},
        {"sequence": 12, "event": "evaluation_only_j0_complete"},
        {"sequence": 13, "event": SLICE_PASS},
        {"sequence": 14, "event": LOCAL_HYBRID_PASS},
        {"sequence": 15, "event": FULL_PHASE3_NOT_RUN},
        {"sequence": 16, "event": ECONOMICS_NOT_RUN},
    )

    stable_documents: dict[str, Any] = {
        "workload/spec.json": workload_spec,
        "workload/query_registry.json": query_registry,
        "build/epoch.json": world.build_epoch,
        "build/portable_rapm.json": model_document,
        "campaign/portable_queries.jsonl": portable_query_rows,
        "campaign/portable_plans.jsonl": portable_plan_rows,
        "campaign/policy_graphs.json": {"policy_graphs": policy_graphs},
        "audit/pre_recovery.jsonl": pre_documents,
        "audit/failed_proof_graph.json": proof_document,
        "recovery/frontier.json": frontier_document,
        "recovery/authorization.json": authorization_document,
        "recovery/ground_slice.json": ground_slice,
        "recovery/boundary_view.json": boundary_view,
        "recovery/request.json": local_request,
        "recovery/runtime_attestation.json": local_attestation,
        "recovery/result.json": local_result,
        "recovery/overlay.json": overlay_document,
        "recovery/access_trace.json": access_trace,
        "audit/post_recovery.jsonl": (post_document,),
        "result/route_certificates.jsonl": route_certificates,
        "result/local_recovery_report.json": report,
        "evaluation/j0_rows.jsonl": j0_rows,
        "evaluation/locality.json": locality,
        "accounting/work_counters.json": work_counters,
        "metrics.json": metrics,
        "events.jsonl": events,
    }
    if set(stable_documents) != set(PHASE3C_REQUIRED_PATHS) - {"run.json"}:
        raise Phase3CInvariantViolation("Phase3C artifact topology drifted")
    semantic_hash = canonical_sha256(stable_documents)
    run_payload = {
        "schema_version": "phase3c.v1",
        "contract_version": CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "execution_profile": EXECUTION_PROFILE,
        "status": SLICE_PASS,
        "local_hybrid_gate_status": LOCAL_HYBRID_PASS,
        "full_phase3_gate_status": FULL_PHASE3_NOT_RUN,
        "workload_economics_gate_status": ECONOMICS_NOT_RUN,
        "run_id_scope": "all fields except run_id/started_at/finished_at",
        "semantic_hash": semantic_hash,
        "source_tree_sha256": _source_tree_hash(),
        "spec_hashes": _spec_hashes(),
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    run_document = {
        "run_id": object_id(run_payload, "run"),
        **run_payload,
        "started_at": started_at,
        "finished_at": _utc_now(),
    }
    documents = {"run.json": run_document, **stable_documents}
    manifest = write_artifact_bundle(
        output_dir,
        documents,
        required_paths=PHASE3C_REQUIRED_PATHS,
    )
    manifest_hashes = {
        record["path"]: record["sha256"] for record in manifest["files"]
    }
    if (
        sha256_file(output_dir / "build" / "portable_rapm.json")
        != base_model_sha256
        or manifest_hashes.get("build/portable_rapm.json") != base_model_sha256
        or sha256_file(output_dir / "build" / "epoch.json")
        != base_build_epoch_sha256
        or manifest_hashes.get("build/epoch.json") != base_build_epoch_sha256
    ):
        raise Phase3CInvariantViolation(
            "base RAPM/BuildEpoch serialized-byte invariance failed"
        )
    failures = verify_artifact_bundle(output_dir)
    if failures:
        raise Phase3CInvariantViolation(
            "written Phase3C bundle failed integrity verification: "
            + "; ".join(failures)
        )
    return {
        "status": SLICE_PASS,
        "local_hybrid_gate_status": LOCAL_HYBRID_PASS,
        "full_phase3_gate_status": FULL_PHASE3_NOT_RUN,
        "workload_economics_gate_status": ECONOMICS_NOT_RUN,
        "run_id": run_document["run_id"],
        "semantic_hash": semantic_hash,
        "bundle_sha256": manifest["bundle_sha256"],
        "portable_rapm_id": world.portable.model.model_id,
        "frontier_state_count": frontier_document["frontier_state_count"],
        "authorized_state_action_pairs": len(authorization.allowed_state_actions),
        "localized_state_count": len(localized_states),
        "post_failure_upper": post_audit.lifted_failure_upper,
        "exact_hybrid_failure": hybrid_lift.evaluation.failure_probability,
        "ground_optimal_failure": ground_points[1].failure_probability,
        "output_dir": str(output_dir),
    }


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ABSTRACT_QUERY_KEY",
    "CONTRACT_VERSION",
    "ECONOMICS_NOT_RUN",
    "EXECUTION_PROFILE",
    "FULL_PHASE3_NOT_RUN",
    "INVARIANT_FAILURE",
    "LOCAL_HYBRID_PASS",
    "LOCAL_QUERY_KEY",
    "PROFILE_KEY",
    "SLICE_PASS",
    "Phase3CInvariantViolation",
    "construct_phase3c_world",
    "run_fresh_portable_proposals",
    "run_phase3c",
]
