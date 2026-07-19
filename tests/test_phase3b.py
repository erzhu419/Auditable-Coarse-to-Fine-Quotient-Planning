from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

from acfqp.artifacts import (
    PHASE3B_DOCUMENT_CONTRACTS,
    PHASE3B_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    sha256_file,
    verify_artifact_bundle,
    write_json,
    write_jsonl,
)
from acfqp.phase3b import run_phase3b
from acfqp.portable import logical_id


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_phase3b import (  # noqa: E402
    _DYNAMIC_IMPORT_DEPENDENCY,
    _import_dependencies,
    verify_phase3b,
)


@pytest.fixture(scope="session")
def clean_phase3b_bundle(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, dict, dict]:
    bundle = tmp_path_factory.mktemp("phase3b") / "bundle"
    summary = run_phase3b(bundle)
    report = verify_phase3b(bundle)
    assert verify_artifact_bundle(bundle) == []
    assert report["verified"], report["failures"]
    return bundle, summary, report


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _resign(bundle: Path, relative_path: str) -> None:
    manifest_path = bundle / "manifest.json"
    manifest = _load(manifest_path)
    target = bundle / relative_path
    record = next(item for item in manifest["files"] if item["path"] == relative_path)
    record["bytes"] = target.stat().st_size
    record["sha256"] = sha256_file(target)
    manifest["bundle_sha256"] = canonical_sha256(manifest["files"])
    write_json(manifest_path, manifest)
    (bundle / "manifest.sha256").write_text(
        f"{sha256_file(manifest_path)}  manifest.json\n",
        encoding="ascii",
    )


def _resign_complete_bundle(bundle: Path) -> None:
    """Re-sign all linked semantic documents like a coordinated forger."""

    stable_documents = {}
    for relative in PHASE3B_REQUIRED_PATHS:
        if relative == "run.json":
            continue
        path = bundle / relative
        if relative.endswith(".jsonl"):
            stable_documents[relative] = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line
            ]
        else:
            stable_documents[relative] = _load(path)
    run_path = bundle / "run.json"
    run = _load(run_path)
    run["semantic_hash"] = canonical_sha256(stable_documents)
    run_payload = {
        key: value
        for key, value in run.items()
        if key not in {"run_id", "started_at", "finished_at"}
    }
    run["run_id"] = object_id(run_payload, "run")
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


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("from .oracle import solve\n", "acfqp.abstraction.oracle"),
        ("from ..planning import ground\n", "acfqp.planning.ground"),
        ("__import__('acfqp.planning.ground')\n", _DYNAMIC_IMPORT_DEPENDENCY),
        (
            "import importlib as il\nil.import_module('acfqp.planning.ground')\n",
            _DYNAMIC_IMPORT_DEPENDENCY,
        ),
        (
            "from importlib import import_module as load\n"
            "load('acfqp.planning.ground')\n",
            _DYNAMIC_IMPORT_DEPENDENCY,
        ),
        (
            "from builtins import __import__ as load\n"
            "load('acfqp.planning.ground')\n",
            _DYNAMIC_IMPORT_DEPENDENCY,
        ),
        (
            "import importlib\nload = importlib.import_module\n"
            "load('acfqp.planning.ground')\n",
            _DYNAMIC_IMPORT_DEPENDENCY,
        ),
        (
            "import importlib\n"
            "getattr(importlib, 'import_module')('acfqp.planning.ground')\n",
            _DYNAMIC_IMPORT_DEPENDENCY,
        ),
        (
            "exec('import acfqp.planning.ground')\n",
            _DYNAMIC_IMPORT_DEPENDENCY,
        ),
        (
            "import builtins\n"
            "builtins.exec('import acfqp.planning.ground')\n",
            _DYNAMIC_IMPORT_DEPENDENCY,
        ),
    ),
)
def test_dependency_audit_resolves_relative_and_dynamic_imports(
    tmp_path: Path,
    source: str,
    expected: str,
) -> None:
    path = tmp_path / "behavioral.py"
    path.write_text(source, encoding="utf-8")
    dependencies = _import_dependencies(
        path,
        module_name="acfqp.abstraction.behavioral",
    )
    assert expected in dependencies


def test_phase3b_clean_bundle_has_frozen_contract_and_statuses(
    clean_phase3b_bundle: tuple[Path, dict, dict],
) -> None:
    bundle, summary, verification = clean_phase3b_bundle
    manifest = _load(bundle / "manifest.json")
    records = {record["path"]: record for record in manifest["files"]}

    assert summary["status"] == "PHASE3B_PORTABLE_RAPM_PASS"
    assert summary["full_phase3_gate_status"] == "PHASE3_AGGREGATE_NOT_RUN"
    assert summary["local_hybrid_gate_status"] == "LOCAL_HYBRID_GATE_NOT_RUN"
    assert (
        summary["workload_economics_gate_status"]
        == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    )
    assert verification["semantic_hash"] == summary["semantic_hash"]
    assert verification["recomputed_semantic_hash"] == summary["semantic_hash"]
    assert set(records) == set(PHASE3B_REQUIRED_PATHS)
    assert set(manifest["required_paths"]) == set(PHASE3B_REQUIRED_PATHS)
    for path, (role, schema) in PHASE3B_DOCUMENT_CONTRACTS.items():
        assert records[path]["required"] is True
        assert records[path]["role"] == role
        assert records[path]["schema"] == schema


def test_phase3b_world_models_are_reused_for_eleven_portable_queries(
    clean_phase3b_bundle: tuple[Path, dict, dict],
) -> None:
    bundle, _, _ = clean_phase3b_bundle
    workload = _load(bundle / "workload/spec.json")
    reuse = _load(bundle / "evaluation/reuse.json")
    metrics = _load(bundle / "metrics.json")
    report = _load(bundle / "result/phase3b_report.json")
    epochs = _load(bundle / "build/epochs.json")["epochs"]
    plans = [
        json.loads(line)
        for line in (bundle / "campaign/portable_plans.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    certificates = [
        json.loads(line)
        for line in (bundle / "audit/certificates.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    j0_rows = [
        json.loads(line)
        for line in (bundle / "evaluation/j0_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    graphs = _load(bundle / "campaign/policy_graphs.json")["policy_graphs"]

    assert workload["query_occurrence_count"] == 11
    assert workload["distinct_ground_query_count"] == 11
    assert workload["distinct_portable_query_count"] >= 8
    assert reuse["one_unchanged_model_per_domain"] is True
    assert reuse["per_domain_query_counts"] == {"g2048": 6, "lmb": 5}
    assert all(count >= 4 for count in reuse["per_domain_distinct_portable_query_counts"].values())
    assert len(epochs) == 2
    assert {epoch["covered_ground_states"] for epoch in epochs} == {25, 192}
    assert {epoch["abstract_cells"] for epoch in epochs} == {5, 10}
    assert all(epoch["construction_uses_q_or_value_signatures"] is False for epoch in epochs)
    assert all(epoch["portable_roundtrip_identity"] is True for epoch in epochs)
    assert len(plans) == len(certificates) == len(j0_rows) == len(graphs) == 11
    assert all(plan["fresh_process"] is True for plan in plans)
    assert all(plan["ground_j0_available_to_planner"] is False for plan in plans)
    assert all(certificate["route"] == "ABSTRACT_CERTIFIED" for certificate in certificates)
    assert all(certificate["certified"] is True for certificate in certificates)
    assert all(row["j0_dependency_role"] == "evaluation_only" for row in j0_rows)
    assert all(row["reward_gap"] == {"numerator": 0, "denominator": 1} for row in j0_rows)
    assert all(row["failure_gap"] == {"numerator": 0, "denominator": 1} for row in j0_rows)
    assert any(graph["stochastic_branch_node_count"] > 0 for graph in graphs)
    assert metrics["ground_states"] == {"g2048": 192, "lmb": 25}
    assert metrics["abstract_cells"] == {"g2048": 10, "lmb": 5}
    assert metrics["certified_queries"] == 11
    assert report["local_repair_exercised"] is False
    assert report["scalar_break_even_claimed"] is False


def test_phase3b_verifier_rejects_resigned_portable_model_tampering(
    clean_phase3b_bundle: tuple[Path, dict, dict], tmp_path: Path
) -> None:
    source, _, _ = clean_phase3b_bundle
    bundle = tmp_path / "model-tamper"
    shutil.copytree(source, bundle)
    relative = "build/g2048/portable_rapm.json"
    document = _load(bundle / relative)
    document["horizon"] += 1
    write_json(bundle / relative, document)
    _resign(bundle, relative)

    assert verify_artifact_bundle(bundle) == []
    report = verify_phase3b(bundle)
    assert not report["verified"]
    assert any("model_id mismatch" in failure for failure in report["failures"])


def test_phase3b_verifier_rejects_resigned_plan_tampering(
    clean_phase3b_bundle: tuple[Path, dict, dict], tmp_path: Path
) -> None:
    source, _, _ = clean_phase3b_bundle
    bundle = tmp_path / "plan-tamper"
    shutil.copytree(source, bundle)
    relative = "campaign/portable_plans.jsonl"
    rows = [
        json.loads(line)
        for line in (bundle / relative).read_text(encoding="utf-8").splitlines()
        if line
    ]
    rows[0]["plan_result"]["composed_candidate_count"] += 1
    write_jsonl(bundle / relative, rows)
    _resign(bundle, relative)

    assert verify_artifact_bundle(bundle) == []
    report = verify_phase3b(bundle)
    assert not report["verified"]
    assert any("result_id mismatch" in failure for failure in report["failures"])


def test_phase3b_verifier_rejects_coordinated_ground_query_resigning(
    clean_phase3b_bundle: tuple[Path, dict, dict], tmp_path: Path
) -> None:
    source, _, _ = clean_phase3b_bundle
    bundle = tmp_path / "coordinated-query-forgery"
    shutil.copytree(source, bundle)

    registry_path = bundle / "workload/query_registry.json"
    registry = _load(registry_path)
    old_id = registry["records"][0]["ground_query_id"]
    ground_query = registry["records"][0]["ground_query"]
    ground_query["reward_weights"][0][1] = {"numerator": 7, "denominator": 1}
    new_id = object_id(ground_query, "query")
    registry["records"][0]["ground_query_id"] = new_id
    write_json(registry_path, registry)

    workload_path = bundle / "workload/spec.json"
    workload = _load(workload_path)
    workload["ordered_ground_query_ids"][0] = new_id
    workload_payload = dict(workload)
    workload_payload.pop("workload_id")
    workload["workload_id"] = object_id(workload_payload, "workload")
    write_json(workload_path, workload)

    for relative in (
        "campaign/portable_queries.jsonl",
        "campaign/portable_plans.jsonl",
    ):
        path = bundle / relative
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line
        ]
        assert rows[0]["ground_query_id"] == old_id
        rows[0]["ground_query_id"] = new_id
        write_jsonl(path, rows)

    graphs_path = bundle / "campaign/policy_graphs.json"
    graphs = _load(graphs_path)
    graph = graphs["policy_graphs"][0]
    graph["ground_query_id"] = new_id
    graph_payload = dict(graph)
    graph_payload.pop("policy_graph_id")
    graph["policy_graph_id"] = object_id(graph_payload, "policy-graph")
    write_json(graphs_path, graphs)

    certificate_path = bundle / "audit/certificates.jsonl"
    certificates = [
        json.loads(line)
        for line in certificate_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    certificate = certificates[0]
    certificate["ground_query_id"] = new_id
    certificate["policy_graph_id"] = graph["policy_graph_id"]
    certificate_payload = dict(certificate)
    certificate_payload.pop("certificate_id")
    certificate["certificate_id"] = object_id(certificate_payload, "certificate")
    write_jsonl(certificate_path, certificates)

    j0_path = bundle / "evaluation/j0_rows.jsonl"
    j0_rows = [
        json.loads(line)
        for line in j0_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    j0_rows[0]["ground_query_id"] = new_id
    j0_rows[0]["certificate_id"] = certificate["certificate_id"]
    write_jsonl(j0_path, j0_rows)

    counters_path = bundle / "accounting/work_counters.json"
    counters = _load(counters_path)
    counters["query"][0]["ground_query_id"] = new_id
    write_json(counters_path, counters)
    _resign_complete_bundle(bundle)

    assert verify_artifact_bundle(bundle) == []
    report = verify_phase3b(bundle)
    assert not report["verified"]
    assert any(
        "ground query registry differs" in failure
        or "portable projection is not bound" in failure
        for failure in report["failures"]
    )


def test_phase3b_verifier_rejects_coordinated_evidence_resigning(
    clean_phase3b_bundle: tuple[Path, dict, dict], tmp_path: Path
) -> None:
    source, _, _ = clean_phase3b_bundle
    bundle = tmp_path / "coordinated-evidence-forgery"
    shutil.copytree(source, bundle)
    fake_reward = {"numerator": 7, "denominator": 1}

    graphs_path = bundle / "campaign/policy_graphs.json"
    graphs = _load(graphs_path)
    graph = graphs["policy_graphs"][0]
    graph["stochastic_branch_node_count"] += 7
    graph_payload = dict(graph)
    graph_payload.pop("policy_graph_id")
    graph["policy_graph_id"] = object_id(graph_payload, "policy-graph")
    write_json(graphs_path, graphs)

    certificate_path = bundle / "audit/certificates.jsonl"
    certificates = [
        json.loads(line)
        for line in certificate_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    certificate = certificates[0]
    certificate["policy_graph_id"] = graph["policy_graph_id"]
    certificate["proposal_expected_reward"] = fake_reward
    certificate["reward_lower"] = fake_reward
    certificate_payload = dict(certificate)
    certificate_payload.pop("certificate_id")
    certificate["certificate_id"] = object_id(certificate_payload, "certificate")
    write_jsonl(certificate_path, certificates)

    j0_path = bundle / "evaluation/j0_rows.jsonl"
    j0_rows = [
        json.loads(line)
        for line in j0_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    j0_rows[0]["certificate_id"] = certificate["certificate_id"]
    j0_rows[0]["ground_expected_reward"] = fake_reward
    j0_rows[0]["portable_expected_reward"] = fake_reward
    j0_rows[0]["lifted_expected_reward"] = fake_reward
    write_jsonl(j0_path, j0_rows)

    report_path = bundle / "result/phase3b_report.json"
    phase_report = _load(report_path)
    phase_report["supported_claims"][0] = "coordinated forged claim"
    report_payload = dict(phase_report)
    report_payload.pop("report_id")
    phase_report["report_id"] = object_id(report_payload, "phase3b-report")
    write_json(report_path, phase_report)
    _resign_complete_bundle(bundle)

    assert verify_artifact_bundle(bundle) == []
    verification = verify_phase3b(bundle)
    assert not verification["verified"]
    assert any(
        "policy graph mismatch" in failure
        or "certificate mismatch" in failure
        or "J0 row mismatch" in failure
        or "claims mismatch" in failure
        for failure in verification["failures"]
    )


def test_phase3b_verifier_rejects_coordinated_runtime_attestation_resigning(
    clean_phase3b_bundle: tuple[Path, dict, dict], tmp_path: Path
) -> None:
    source, _, _ = clean_phase3b_bundle
    bundle = tmp_path / "coordinated-runtime-forgery"
    shutil.copytree(source, bundle)

    plans_path = bundle / "campaign/portable_plans.jsonl"
    plans = [
        json.loads(line)
        for line in plans_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    plan = plans[0]
    attestation = plan["runtime_attestation"]
    attestation["project_checkout_visible"] = True
    attestation["python_site_disabled"] = False
    attestation["network_namespace_unshared"] = False
    attestation["forbidden_modules_resolved"] = ["acfqp.planning"]
    attestation["model_sha256"] = "0" * 64
    attestation_payload = dict(attestation)
    attestation_payload.pop("attestation_id")
    attestation["attestation_id"] = logical_id(
        "runtime-attestation", attestation_payload
    )
    plan["project_checkout_visible_to_planner"] = True
    plan["python_site_disabled"] = False
    write_jsonl(plans_path, plans)
    _resign_complete_bundle(bundle)

    assert verify_artifact_bundle(bundle) == []
    verification = verify_phase3b(bundle)
    assert not verification["verified"]
    assert any(
        "runtime isolation attestation mismatch" in failure
        or "portable runtime isolation wrapper mismatch" in failure
        for failure in verification["failures"]
    )
