from __future__ import annotations

import copy
from fractions import Fraction
import json
from pathlib import Path
import shutil
import subprocess

import pytest

import acfqp.phase3c as phase3c_module
from acfqp.artifacts import object_id, sha256_file, to_jsonable
from acfqp.local_recovery import (
    AuthorizedKernelView,
    GroundPatchDecision,
    HybridPolicyOverlay,
    LocalRecoveryAuthorization,
    PatchedAuditKernelView,
    UnauthorizedLocalRecoveryAccess,
    audit_hybrid_policy,
    build_failed_proof_graph,
    build_redacted_boundary_view,
    lift_hybrid_policy,
    materialize_authorized_slice,
    redact_authorized_slice_for_worker,
)
from acfqp.local_solver import solve_local_recovery
from acfqp.phase3c import (
    _select_recovery_proposal,
    _validate_local_worker_result,
    _worker_input_sha256,
    construct_phase3c_world,
)
from acfqp.planning import FiniteHorizonPolicy, audit_abstract_policy
from acfqp.portable_planner import solve_portable_pareto


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def failed_case() -> dict:
    world = construct_phase3c_world()
    query = world.queries[1].query
    result = solve_portable_pareto(
        world.portable.model,
        world.portable.query_from_spec(query),
    )
    proposal, _ = _select_recovery_proposal(result)
    policy = FiniteHorizonPolicy.from_mapping(
        world.portable.decode_policy(proposal.policy)
    )
    audit = audit_abstract_policy(
        world.kernel,
        query,
        world.models.envelope,
        policy,
    )
    graph = build_failed_proof_graph(
        world.kernel,
        query,
        world.models.envelope,
        policy,
        audit,
    )
    frontier = graph.frontier()
    authorization = LocalRecoveryAuthorization.for_frontier(
        world.kernel,
        world.models.envelope,
        frontier,
        graph,
    )
    materialized_slice = materialize_authorized_slice(
        world.kernel,
        query,
        world.models.envelope,
        frontier,
        authorization,
        graph=graph,
    )
    ground_slice = redact_authorized_slice_for_worker(materialized_slice)
    boundary = build_redacted_boundary_view(
        query,
        world.models.envelope,
        policy,
        graph,
        unrestricted_reward_upper=audit.unrestricted_reward_upper,
        regret_tolerance=audit.regret_tolerance,
    )
    request_payload = {
        "schema": "acfqp.local_recovery_request.v1",
        "workload_id": "test-workload",
        "occurrence_id": "test-occurrence",
        "portable_model_id": world.portable.model.model_id,
        "build_epoch_id": world.build_epoch["build_epoch_id"],
        "ground_query_id": object_id(query, "query"),
        "portable_query_id": "test-portable-query",
        "portable_result_id": result.result_id,
        "pre_audit_id": "test-pre-audit",
        "failed_proof_graph_id": graph.graph_id,
        "frontier_id": frontier.frontier_id,
        "authorization_id": authorization.authorization_id,
        "slice_id": ground_slice["slice_id"],
        "slice_sha256": _worker_input_sha256(ground_slice),
        "boundary_view_id": boundary["boundary_view_id"],
        "boundary_sha256": _worker_input_sha256(boundary),
        "worker_inputs": ["boundary.json", "request.json", "slice.json"],
        "portable_rapm_mounted_to_worker": False,
        "ground_kernel_mounted_to_worker": False,
        "coverage_graph_mounted_to_worker": False,
        "j0_mounted_to_worker": False,
        "project_checkout_mounted_to_worker": False,
        "grammar_used": False,
        "selection_rule": "test-risk-value-certificate",
    }
    request = {
        "request_id": object_id(request_payload, "local-request"),
        **request_payload,
    }
    local_result = solve_local_recovery(boundary, ground_slice, request)
    return {
        "world": world,
        "query": query,
        "policy": policy,
        "audit": audit,
        "graph": graph,
        "frontier": frontier,
        "authorization": authorization,
        "ground_slice": ground_slice,
        "materialized_slice": materialized_slice,
        "boundary": boundary,
        "request": request,
        "local_result": local_result,
    }


def test_failed_proof_frontier_uses_direct_not_inherited_residuals(
    failed_case: dict,
) -> None:
    audit = failed_case["audit"]
    graph = failed_case["graph"]
    frontier = failed_case["frontier"]

    assert not audit.certified
    assert audit.lifted_failure_upper == Fraction(5099, 10000)
    assert len(graph.nodes) == 4
    assert len(graph.edges) == 4
    assert all(node.inherited_bad and not node.direct_bad for node in graph.nodes[:2])
    assert all(node.direct_bad and not node.inherited_bad for node in graph.nodes[2:])
    assert tuple(node.remaining for node in frontier.nodes) == (1, 1)
    assert sorted(len(node.witnesses) for node in frontier.nodes) == [6, 28]
    assert sorted(node.failure_range for node in frontier.nodes) == [
        Fraction(1, 200),
        Fraction(99, 200),
    ]


def test_authorization_is_strict_and_logs_only_successful_access(
    failed_case: dict,
) -> None:
    world = failed_case["world"]
    authorization = failed_case["authorization"]
    assert len(authorization.frontier_state_actions) == 32
    assert len(authorization.reverse_dependency_state_actions) == 8
    assert len(authorization.allowed_state_actions) == 40

    view = AuthorizedKernelView(world.kernel, authorization)
    state, action = authorization.frontier_state_actions[0]
    assert action in view.actions(state)
    assert sum(
        (outcome.probability for outcome in view.step(state, action)), Fraction(0)
    ) == 1
    before = view.access_log
    with pytest.raises(UnauthorizedLocalRecoveryAccess):
        view.step(state, "not-an-authorized-action")
    assert view.access_log == before
    assert tuple(record.sequence for record in view.access_log) == (0, 1)


def test_patched_post_audit_view_steps_only_frozen_overlay_pairs(
    failed_case: dict,
) -> None:
    world = failed_case["world"]
    state, action = next(
        pair
        for pair in failed_case["authorization"].frontier_state_actions
        if len(world.kernel.actions(pair[0])) > 1
    )
    alternative = next(
        candidate for candidate in world.kernel.actions(state) if candidate != action
    )
    outside_state = next(
        candidate
        for candidate in world.partition.states
        if candidate != state and not world.kernel.is_terminal(candidate)
    )
    view = PatchedAuditKernelView(world.kernel, ((state, action),))

    assert action in view.actions(state)
    assert sum(
        (outcome.probability for outcome in view.step(state, action)), Fraction(0)
    ) == 1
    before = view.access_log
    with pytest.raises(UnauthorizedLocalRecoveryAccess):
        view.step(state, alternative)
    with pytest.raises(UnauthorizedLocalRecoveryAccess):
        view.actions(outside_state)
    assert view.access_log == before


def test_local_solver_selects_cardinality_minimal_complete_cell_patch(
    failed_case: dict,
) -> None:
    result = failed_case["local_result"]
    assert result.localized_node_ids == ("proof-node-058bab68358b1f56",)
    assert len(result.decisions) == 8
    assert len({decision.state_id for decision in result.decisions}) == 8
    assert result.root_reward_lower == Fraction(3, 64)
    assert result.regret_upper == 0
    assert result.root_failure_upper == Fraction(397, 20000)
    assert result.candidate_subset_count == 2
    assert result.certified_safe
    assert result.certified_value
    assert result.certified


def test_phase3c_operational_mode_does_not_replay_local_solver(
    failed_case: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_replay(*_args, **_kwargs):
        raise AssertionError("host local solver replay was called")

    monkeypatch.setattr(phase3c_module, "solve_local_recovery", forbidden_replay)
    _validate_local_worker_result(
        failed_case["local_result"].to_dict(),
        failed_case["boundary"],
        failed_case["ground_slice"],
        failed_case["request"],
        operational_no_full_replay=True,
    )
    with pytest.raises(AssertionError, match="host local solver replay"):
        _validate_local_worker_result(
            failed_case["local_result"].to_dict(),
            failed_case["boundary"],
            failed_case["ground_slice"],
            failed_case["request"],
            operational_no_full_replay=False,
        )


def test_local_solver_rejects_risk_only_patch_when_value_certificate_fails(
    failed_case: dict,
) -> None:
    boundary = copy.deepcopy(failed_case["boundary"])
    boundary["unrestricted_reward_upper"] = {"numerator": 1, "denominator": 1}
    boundary_payload = dict(boundary)
    boundary_payload.pop("boundary_view_id")
    boundary["boundary_view_id"] = object_id(
        boundary_payload, "redacted-boundary-view"
    )
    request = copy.deepcopy(failed_case["request"])
    request["boundary_view_id"] = boundary["boundary_view_id"]
    request["boundary_sha256"] = _worker_input_sha256(boundary)
    request_payload = dict(request)
    request_payload.pop("request_id")
    request["request_id"] = object_id(request_payload, "local-request")

    with pytest.raises(ValueError, match="value/risk"):
        solve_local_recovery(boundary, failed_case["ground_slice"], request)


def _overlay(failed_case: dict) -> HybridPolicyOverlay:
    world = failed_case["world"]
    frontier_by_id = {
        node.node_id: node for node in failed_case["frontier"].nodes
    }
    states = {object_id(state, "state"): state for state in world.partition.states}
    actions = {
        object_id(action, "ground-action"): action
        for state in world.partition.states
        for action in world.kernel.actions(state)
    }
    decisions = tuple(
        GroundPatchDecision(
            decision.remaining,
            frontier_by_id[decision.node_id].cell,
            states[decision.state_id],
            actions[decision.action_id],
        )
        for decision in failed_case["local_result"].decisions
    )
    return HybridPolicyOverlay(
        failed_case["policy"],
        decisions,
        query_id=object_id(failed_case["query"], "query"),
        frontier_id=failed_case["frontier"].frontier_id,
    )


def test_hybrid_overlay_certifies_and_retains_abstract_decisions(
    failed_case: dict,
) -> None:
    world = failed_case["world"]
    overlay = _overlay(failed_case)
    audit = audit_hybrid_policy(
        world.kernel,
        failed_case["query"],
        world.models.envelope,
        overlay,
    )
    lifted = lift_hybrid_policy(
        world.kernel,
        failed_case["query"],
        world.models.envelope,
        overlay,
    )

    assert audit.certified
    assert audit.lifted_reward_lower == Fraction(3, 64)
    assert audit.lifted_failure_upper == Fraction(397, 20000)
    assert audit.regret_upper == 0
    assert lifted.evaluation.expected_reward == Fraction(3, 64)
    assert lifted.evaluation.failure_probability == Fraction(317, 16000)
    assert lifted.patched_decision_count == 8
    assert lifted.abstract_decision_count == 12


def test_local_runtime_isolated_attestation(
    failed_case: dict,
    tmp_path: Path,
) -> None:
    bubblewrap = shutil.which("bwrap")
    if bubblewrap is None:
        pytest.skip("bubblewrap unavailable")
    runtime = tmp_path / "runtime" / "acfqp"
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    runtime.mkdir(parents=True)
    input_root.mkdir()
    output_root.mkdir()
    for name in ("local_solver.py", "local_runtime.py"):
        shutil.copy2(ROOT / "src" / "acfqp" / name, runtime / name)
    (input_root / "boundary.json").write_text(
        json.dumps(
            to_jsonable(failed_case["boundary"]),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    (input_root / "slice.json").write_text(
        json.dumps(
            to_jsonable(failed_case["ground_slice"]),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    (input_root / "request.json").write_text(
        json.dumps(
            to_jsonable(failed_case["request"]),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
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
            str(tmp_path / "runtime"),
            "/runtime",
            "--ro-bind",
            str(input_root),
            "/input",
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
            "ACFQP_FORBIDDEN_ROOTS",
            str(ROOT),
            "/usr/bin/python3",
            "-B",
            "-S",
            "-m",
            "acfqp.local_runtime",
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
        timeout=60,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    assert not process.stdout and not process.stderr
    result = json.loads((output_root / "result.json").read_text(encoding="utf-8"))
    attestation = json.loads(
        (output_root / "attestation.json").read_text(encoding="utf-8")
    )
    assert result["root_failure_upper"] == {"numerator": 397, "denominator": 20000}
    assert attestation["project_checkout_visible"] is False
    assert attestation["network_namespace_unshared"] is True
    assert attestation["python_site_disabled"] is True
    assert attestation["input_regular_files"] == [
        "boundary.json",
        "request.json",
        "slice.json",
    ]
    assert attestation["request_id"] == failed_case["request"]["request_id"]
    assert attestation["output_regular_files_before"] == []
    assert attestation["unexpected_module_origins"] == []
    assert attestation["runtime_source_sha256"] == {
        "acfqp.local_solver": sha256_file(ROOT / "src" / "acfqp" / "local_solver.py"),
        "acfqp.local_runtime": sha256_file(ROOT / "src" / "acfqp" / "local_runtime.py"),
    }
