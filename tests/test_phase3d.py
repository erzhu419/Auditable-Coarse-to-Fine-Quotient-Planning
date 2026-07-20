from __future__ import annotations

import copy
from collections import Counter
from fractions import Fraction
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

import acfqp.abstraction.quotient as quotient_module
import acfqp.aliased_safe_chain as aliased_module
import acfqp.build_coverage as coverage_module
import acfqp.local_recovery as local_recovery_module
import acfqp.phase3c as phase3c_module
import acfqp.phase3d as phase3d_module
import acfqp.planning.audit as audit_module
import acfqp.portable as portable_module

from acfqp.build_coverage import SuiteBuildCoverage
from acfqp.domains.g2048 import G2048SafeChainKernel
from acfqp.artifacts import (
    PHASE3D_DOCUMENT_CONTRACTS,
    PHASE3D_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    sha256_file,
    verify_artifact_bundle,
    write_json,
)
from acfqp.phase3d import (
    _authority_accounting,
    construct_safe_chain_context,
    prepare_safe_chain_estimate_context,
    run_phase3d,
)
from acfqp.phase3c import run_phase3c
from acfqp.frozen_phase3c import load_frozen_phase3c_world
from acfqp.portable import logical_id


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_phase3d import verify_phase3d  # noqa: E402


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_document(path: Path):
    if path.suffix == ".jsonl":
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line
        ]
    return _load(path)


@pytest.fixture(scope="session")
def phase3c_source_bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    bundle = tmp_path_factory.mktemp("phase3d-source-phase3c") / "bundle"
    run_phase3c(bundle)
    assert verify_artifact_bundle(bundle) == []
    return bundle


@pytest.fixture(scope="session")
def clean_phase3d_bundle(
    tmp_path_factory: pytest.TempPathFactory,
    phase3c_source_bundle: Path,
) -> tuple[Path, dict, dict]:
    bundle = tmp_path_factory.mktemp("phase3d") / "bundle"
    summary = run_phase3d(bundle, phase3c_source_bundle)
    verification = verify_phase3d(bundle)
    assert verify_artifact_bundle(bundle) == []
    assert verification["verified"], verification["failures"]
    return bundle, summary, verification


def _resign_bundle(bundle: Path) -> None:
    stable = {
        relative: _load_document(bundle / relative)
        for relative in PHASE3D_REQUIRED_PATHS
        if relative != "run.json"
    }
    run_path = bundle / "run.json"
    run = _load(run_path)
    run["semantic_hash"] = canonical_sha256(stable)
    run_id_payload = {
        key: value
        for key, value in run.items()
        if key not in {"run_id", "started_at", "finished_at"}
    }
    run["run_id"] = object_id(run_id_payload, "run")
    write_json(run_path, run)

    manifest_path = bundle / "manifest.json"
    manifest = _load(manifest_path)
    for record in manifest["files"]:
        target = bundle / record["path"]
        record["bytes"] = target.stat().st_size
        record["sha256"] = sha256_file(target)
    manifest["bundle_sha256"] = canonical_sha256(manifest["files"])
    write_json(manifest_path, manifest)
    (bundle / "manifest.sha256").write_text(
        f"{sha256_file(manifest_path)}  manifest.json\n",
        encoding="ascii",
    )


def test_phase3e_estimate_preparation_stops_before_ground_execution(
    phase3c_source_bundle: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("route-specific execution happened before decision freeze")

    # Binding is an explicit pre-decision operation.  Once its immutable
    # model/action catalogues exist, estimate preparation may not consult any
    # live kernel method.
    frozen_world = load_frozen_phase3c_world(phase3c_source_bundle)
    monkeypatch.setattr(G2048SafeChainKernel, "actions", forbidden)
    monkeypatch.setattr(G2048SafeChainKernel, "is_terminal", forbidden)
    monkeypatch.setattr(G2048SafeChainKernel, "step", forbidden)
    monkeypatch.setattr(phase3d_module, "materialize_authorized_slice", forbidden)
    monkeypatch.setattr(phase3d_module, "compile_sparse_recovery_inputs", forbidden)

    prepared = prepare_safe_chain_estimate_context(frozen_world)

    assert not prepared.pre_audit.certified
    assert len(prepared.authorization.frontier_state_actions) == 16
    assert len(prepared.authorization.reverse_dependency_state_actions) == 8
    assert len(prepared.authorization.allowed_state_actions) == 24
    assert not hasattr(prepared, "v1_slice")
    assert not hasattr(prepared, "sparse_slice")
    assert not hasattr(prepared, "capability")


def test_phase3e_estimate_preparation_rejects_an_unbound_bundle_path(
    phase3c_source_bundle: Path,
) -> None:
    with pytest.raises(
        phase3d_module.Phase3DInvariantViolation,
        match="prebound FrozenPhase3CWorld",
    ):
        prepare_safe_chain_estimate_context(phase3c_source_bundle)


def test_phase3d_clean_bundle_closes_general_local_recovery_gate(
    clean_phase3d_bundle: tuple[Path, dict, dict],
    phase3c_source_bundle: Path,
) -> None:
    bundle, summary, verification = clean_phase3d_bundle
    manifest = _load(bundle / "manifest.json")
    records = {row["path"]: row for row in manifest["files"]}
    causal = _load(bundle / "safe_chain/causal_search.json")
    authorization = _load(bundle / "safe_chain/authorization.json")
    capability = _load(bundle / "safe_chain/capability.json")
    evidence = _load(bundle / "safe_chain/capability_evidence.json")
    result = _load(bundle / "safe_chain/result.json")
    post = _load(bundle / "safe_chain/post_certificate.json")
    synthetic = _load(bundle / "synthetic/result.json")
    legacy = _load(bundle / "synthetic/legacy_greedy.json")
    runtime = _load(bundle / "safe_chain/runtime_attestation.json")
    base_identity = _load(bundle / "safe_chain/base_identity.json")
    work = _load(bundle / "accounting/work_counters.json")
    events = _load_document(bundle / "events.jsonl")

    assert summary["status"] == "PHASE3D_GENERAL_LOCAL_RECOVERY_PASS"
    assert summary["general_local_recovery_gate_status"] == (
        "GENERAL_LOCAL_RECOVERY_GATE_PASS"
    )
    assert summary["full_phase3_gate_status"] == "PHASE3_AGGREGATE_NOT_RUN"
    assert verification["verified"]
    assert set(records) == set(PHASE3D_REQUIRED_PATHS)
    for path, contract in PHASE3D_DOCUMENT_CONTRACTS.items():
        assert (records[path]["role"], records[path]["schema"]) == contract

    assert causal["evaluation_count"] == 4
    assert len(causal["selected_node_ids"]) == 1
    assert len(causal["excluded_candidate_node_ids"]) == 1
    assert len(causal["baseline_node_channel_values"]) == 8
    assert all(
        len(row["node_channel_values"]) == 8 for row in causal["evaluations"]
    )
    assert any(
        len(row["active_realization_ids"]) > 1
        for row in causal["baseline_node_channel_values"]
    )
    assert authorization["frontier_state_action_count"] == 16
    assert authorization["ancestor_state_action_count"] == 8
    assert authorization["authorized_state_action_count"] == 24
    assert authorization["authorized_positive_outcome_count"] == 96

    assert len(capability["input_ports"]) == 1
    assert capability["exit_ports"] == []
    assert len(capability["root_reward_forms"]) == 1
    assert len(capability["root_failure_forms"]) == 1
    assert evidence["source_node_count"] == 4
    assert evidence["source_abstract_realization_row_count"] == 20
    assert evidence["enumeration"]["status"] == "COMPLETE"
    assert evidence["recovery_input_compilation"]["enumeration_complete"] is True

    assert result["status"] == "LOCAL_RECOVERY_CERTIFIED"
    assert result["root_reward_lower"] == {"numerator": 3, "denominator": 64}
    assert result["root_failure_upper"] == {
        "numerator": 397,
        "denominator": 20000,
    }
    assert result["theoretical_total_policy_space"] == 257
    assert result["counters"]["policy_assignments"] == 257
    assert result["minimality_proven"] is True
    assert post["exact_hybrid_evaluation_status"] == (
        "EVALUATION_ONLY_NOT_RUN_IN_OPERATIONAL_RUNNER"
    )
    assert post["exact_hybrid_failure"] is None
    assert post["abstract_decision_count"] is None
    assert verification["evaluation_only_exact_hybrid_failure"] == Fraction(
        317, 16000
    )
    assert verification["evaluation_only_abstract_decision_count"] == 12

    assert synthetic["status"] == "LOCAL_RECOVERY_CERTIFIED"
    assert synthetic["theoretical_total_policy_space"] == 25
    assert synthetic["root_reward_lower"] == {"numerator": 1, "denominator": 1}
    assert synthetic["root_failure_upper"] == {"numerator": 1, "denominator": 25}
    assert legacy["certified_value"] is False
    assert legacy["misses_existing_joint_certificate"] is True
    assert runtime["input_regular_files"] == [
        "capability.json",
        "request.json",
        "slice.json",
    ]
    assert runtime["project_checkout_visible"] is False
    assert runtime["unexpected_module_origins"] == []
    assert (
        bundle / "safe_chain/base_portable_rapm.json"
    ).read_bytes() == (
        phase3c_source_bundle / "build/portable_rapm.json"
    ).read_bytes()
    assert (bundle / "safe_chain/base_build_epoch.json").read_bytes() == (
        phase3c_source_bundle / "build/epoch.json"
    ).read_bytes()
    assert (
        bundle / "safe_chain/source_phase3c_locality.json"
    ).read_bytes() == (
        phase3c_source_bundle / "evaluation/locality.json"
    ).read_bytes()
    assert (
        bundle / "safe_chain/source_phase3c_authorization.json"
    ).read_bytes() == (
        phase3c_source_bundle / "recovery/authorization.json"
    ).read_bytes()
    assert base_identity["source_bundle_integrity_verified"] is True
    assert base_identity["binding_mode"] == (
        "finite_structural_id_scan_without_transitions"
    )
    assert base_identity["source_manifest_sha256"] == hashlib.sha256(
        (phase3c_source_bundle / "manifest.json").read_bytes()
    ).hexdigest()
    assert base_identity["binding_counters"]["kernel_step_calls"] == 0
    assert base_identity["binding_counters"]["transition_closure_calls"] == 0
    assert base_identity["rapm_builder_invocations"] == 0
    assert base_identity["partition_builder_invocations"] == 0
    assert base_identity["quotient_builder_invocations"] == 0
    assert work["model_binding"] == base_identity["binding_counters"]
    assert work["safe_chain"]["trusted_frontier_materialization"] == {
        "step_calls": 16,
        "positive_probability_outcomes": 64,
        "extra_accounting_step_calls": 0,
    }
    assert events[0]["event"] == (
        "verified_frozen_phase3c_bundle_consumed_and_bound"
    )


def _forbidden(name: str):
    def fail(*_args, **_kwargs):
        raise AssertionError(f"forbidden operational call: {name}")

    return fail


def test_phase3d_operational_runner_never_rebuilds_or_recomputes_ground_upper(
    phase3c_source_bundle: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_actions = G2048SafeChainKernel.actions
    original_step = G2048SafeChainKernel.step
    action_stage_violations: list[tuple[str, ...]] = []
    step_calls: list[tuple[object, object]] = []

    def tracked_actions(self, state):
        names: list[str] = []
        frame = sys._getframe(1)
        while frame is not None:
            names.append(frame.f_code.co_name)
            frame = frame.f_back
        allowed = {
            "_bind_registry",
            "_validate_cross_ids",
            "materialize_authorized_slice",
            "audit_hybrid_policy",
        }
        if not allowed.intersection(names):
            action_stage_violations.append(tuple(names))
        return original_actions(self, state)

    def tracked_step(self, state, action):
        step_calls.append((state, action))
        return original_step(self, state, action)

    monkeypatch.setattr(G2048SafeChainKernel, "actions", tracked_actions)
    monkeypatch.setattr(G2048SafeChainKernel, "step", tracked_step)
    monkeypatch.setattr(
        phase3c_module,
        "construct_phase3c_world",
        _forbidden("construct_phase3c_world"),
    )
    monkeypatch.setattr(
        aliased_module,
        "build_initial_partition",
        _forbidden("build_initial_partition"),
    )
    monkeypatch.setattr(
        quotient_module,
        "build_quotient_models",
        _forbidden("build_quotient_models"),
    )
    monkeypatch.setattr(
        portable_module,
        "build_portable_rapm",
        _forbidden("build_portable_rapm"),
    )
    monkeypatch.setattr(
        coverage_module,
        "transition_closure",
        _forbidden("transition_closure"),
    )
    monkeypatch.setattr(
        SuiteBuildCoverage,
        "from_queries",
        classmethod(_forbidden("SuiteBuildCoverage.from_queries")),
    )
    monkeypatch.setattr(
        audit_module,
        "unrestricted_upper_envelope",
        _forbidden("abstract unrestricted_upper_envelope"),
    )
    monkeypatch.setattr(
        local_recovery_module,
        "unrestricted_upper_envelope",
        _forbidden("hybrid unrestricted_upper_envelope"),
    )

    summary = run_phase3d(tmp_path / "bundle", phase3c_source_bundle)

    assert summary["status"] == "PHASE3D_GENERAL_LOCAL_RECOVERY_PASS"
    assert action_stage_violations == []
    assert len(step_calls) == 24
    multiplicities = Counter(step_calls)
    assert len(multiplicities) == 16
    assert Counter(multiplicities.values()) == {1: 8, 2: 8}
    source_authorization = _load(
        phase3c_source_bundle / "recovery/authorization.json"
    )
    source_frontier = {
        (row["state_id"], row["action_id"])
        for row in source_authorization["frontier_state_actions"]
    }
    source_reverse = {
        (row["state_id"], row["action_id"])
        for row in source_authorization[
            "reverse_selected_dependency_state_actions"
        ]
    }
    observed = {
        (object_id(state, "state"), object_id(action, "ground-action"))
        for state, action in multiplicities
    }
    assert observed < source_frontier
    assert observed.isdisjoint(source_reverse)


def test_phase3d_pre_certificate_and_accounting_never_step_outside_frontier(
    phase3c_source_bundle: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_step = G2048SafeChainKernel.step
    calls: list[tuple[object, object]] = []

    def tracked_step(self, state, action):
        calls.append((state, action))
        return original_step(self, state, action)

    monkeypatch.setattr(G2048SafeChainKernel, "step", tracked_step)
    context = construct_safe_chain_context(phase3c_source_bundle)

    assert len(calls) == 16
    assert set(calls) == set(context.authorization.frontier_state_actions)
    before_accounting = tuple(calls)
    accounting = _authority_accounting(context)
    assert tuple(calls) == before_accounting
    assert accounting["phase3d"]["frontier_positive_outcomes"] == 64


@pytest.mark.parametrize(
    "case",
    (
        "causal_selection",
        "active_extremizer",
        "capability_coefficient",
        "derived_result_flag",
        "authorization_count",
        "source_manifest_bytes",
    ),
)
def test_phase3d_verifier_rejects_coordinated_resigned_forgery(
    clean_phase3d_bundle: tuple[Path, dict, dict],
    tmp_path: Path,
    case: str,
) -> None:
    source, _, _ = clean_phase3d_bundle
    bundle = tmp_path / case
    shutil.copytree(source, bundle)

    if case == "causal_selection":
        path = bundle / "safe_chain/causal_search.json"
        document = _load(path)
        document["selected_node_ids"] = document["excluded_candidate_node_ids"]
        payload = dict(document)
        payload.pop("causal_search_id")
        document["causal_search_id"] = object_id(payload, "causal-search")
        write_json(path, document)
    elif case == "active_extremizer":
        path = bundle / "safe_chain/causal_search.json"
        document = _load(path)
        row = next(
            item
            for item in document["baseline_node_channel_values"]
            if len(item["active_realization_ids"]) > 1
        )
        row["active_realization_ids"] = row["active_realization_ids"][:-1]
        payload = dict(document)
        payload.pop("causal_search_id")
        document["causal_search_id"] = object_id(payload, "causal-search")
        write_json(path, document)
    elif case == "capability_coefficient":
        path = bundle / "safe_chain/capability.json"
        document = _load(path)
        form = document["root_failure_forms"][0]
        form["terms"][0]["coefficient"] = {"numerator": 1, "denominator": 2}
        form_payload = {"constant": form["constant"], "terms": form["terms"]}
        form["form_id"] = logical_id("sparse-form", form_payload)
        payload = dict(document)
        payload.pop("capability_id")
        document["capability_id"] = logical_id(
            "sparse-robust-affine-capability", payload
        )
        write_json(path, document)
    elif case == "derived_result_flag":
        path = bundle / "safe_chain/result.json"
        document = _load(path)
        document["certified"] = False
        payload = dict(document)
        payload.pop("result_id")
        document["result_id"] = logical_id("general-local-result", payload)
        write_json(path, document)
    elif case == "authorization_count":
        path = bundle / "safe_chain/authorization.json"
        document = _load(path)
        document["authorized_state_action_count"] = 25
        write_json(path, document)
    elif case == "source_manifest_bytes":
        path = bundle / "safe_chain/source_phase3c_manifest.json"
        document = _load(path)
        record = next(
            row
            for row in document["files"]
            if row["path"] == "evaluation/locality.json"
        )
        record["bytes"] += 1
        document["bundle_sha256"] = canonical_sha256(document["files"])
        write_json(path, document)
    else:  # pragma: no cover
        raise AssertionError(case)

    _resign_bundle(bundle)
    assert verify_artifact_bundle(bundle) == []
    verification = verify_phase3d(bundle)
    assert not verification["verified"]
    assert verification["failures"]
