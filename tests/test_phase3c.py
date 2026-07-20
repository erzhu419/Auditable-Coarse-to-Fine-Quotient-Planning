from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path

import pytest

from acfqp.artifacts import (
    PHASE3C_DOCUMENT_CONTRACTS,
    PHASE3C_REQUIRED_PATHS,
    canonical_sha256,
    object_id,
    sha256_file,
    verify_artifact_bundle,
    write_json,
    write_jsonl,
)
from acfqp.phase3c import run_phase3c


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_phase3c import verify_phase3c  # noqa: E402


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


@pytest.fixture(scope="session")
def clean_phase3c_bundle(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, dict, dict]:
    bundle = tmp_path_factory.mktemp("phase3c") / "bundle"
    summary = run_phase3c(bundle)
    verification = verify_phase3c(bundle)
    assert verify_artifact_bundle(bundle) == []
    assert verification["verified"], verification["failures"]
    return bundle, summary, verification


def _resign_complete_bundle(bundle: Path) -> None:
    """Re-sign SHA and semantic links after a coordinated artifact forgery."""

    stable_documents = {}
    for relative in PHASE3C_REQUIRED_PATHS:
        if relative == "run.json":
            continue
        path = bundle / relative
        stable_documents[relative] = (
            _load_rows(path) if relative.endswith(".jsonl") else _load(path)
        )
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


def test_phase3c_clean_bundle_has_frozen_contract_and_local_hybrid_gate(
    clean_phase3c_bundle: tuple[Path, dict, dict],
) -> None:
    bundle, summary, verification = clean_phase3c_bundle
    manifest = _load(bundle / "manifest.json")
    records = {row["path"]: row for row in manifest["files"]}
    frontier = _load(bundle / "recovery/frontier.json")
    authorization = _load(bundle / "recovery/authorization.json")
    locality = _load(bundle / "evaluation/locality.json")
    local_result = _load(bundle / "recovery/result.json")
    routes = _load_rows(bundle / "result/route_certificates.jsonl")

    assert summary["status"] == "PHASE3C_LOCAL_RECOVERY_PASS"
    assert summary["local_hybrid_gate_status"] == "LOCAL_HYBRID_GATE_PASS"
    assert summary["full_phase3_gate_status"] == "PHASE3_AGGREGATE_NOT_RUN"
    assert verification["semantic_hash"] == verification["recomputed_semantic_hash"]
    assert set(records) == set(PHASE3C_REQUIRED_PATHS)
    assert set(manifest["required_paths"]) == set(PHASE3C_REQUIRED_PATHS)
    for path, (role, schema) in PHASE3C_DOCUMENT_CONTRACTS.items():
        assert records[path]["role"] == role
        assert records[path]["schema"] == schema
        assert records[path]["required"] is True

    assert frontier["frontier_node_count"] == 2
    assert frontier["frontier_state_count"] == 12
    assert all(row["remaining"] == 1 and row["direct_bad"] for row in frontier["nodes"])
    assert authorization["frontier_state_action_count"] == 32
    assert authorization["reverse_dependency_state_action_count"] == 8
    assert authorization["authorized_state_action_count"] == 40
    assert [row["route"] for row in routes] == [
        "ABSTRACT_CERTIFIED",
        "LOCAL_GROUND_RECOVERY",
    ]
    assert locality["patch_decisions"] == 8
    assert locality["ground_distinction_changes_from_base_concretizer"] == 4
    assert locality["retained_abstract_ground_decisions"] == 12
    assert locality["strict_worker_locality"] is True
    assert locality["base_rapm_immutable"] is True
    assert locality["base_model_sha256_before"] == sha256_file(
        bundle / "build/portable_rapm.json"
    )
    assert locality["base_build_epoch_sha256_before"] == sha256_file(
        bundle / "build/epoch.json"
    )
    assert local_result["certified_safe"] is True
    assert local_result["certified_value"] is True
    assert local_result["certified"] is True
    assert local_result["regret_upper"] == {"numerator": 0, "denominator": 1}


@pytest.mark.parametrize(
    ("case", "expected_failure"),
    (
        ("inherited_root_frontier", "earliest DirectBad frontier"),
        ("missing_frontier_witness", "complete DirectBad proof DAG"),
        ("slice_add_nonfrontier", "frontier-only authorized ground slice"),
        ("slice_missing_action", "frontier-only authorized ground slice"),
        ("patch_outside_scope", "query-scoped overlay/patch scope"),
        ("base_model_changed", "base portable model"),
        ("early_j0_event", "event chronology/J0 authority boundary"),
        ("locality_counter_forged", "strict locality accounting"),
        ("work_counter_forged", "route-separated work counters"),
        ("route_forged", "terminal route certificates"),
        ("post_audit_risk_forged", "post-recovery full-authority audit"),
        ("runtime_attestation_reused", "local runtime attestation"),
        ("portable_attestation_reused", "fresh isolated portable runtime attestation"),
    ),
)
def test_phase3c_verifier_rejects_coordinated_resigned_semantic_forgery(
    clean_phase3c_bundle: tuple[Path, dict, dict],
    tmp_path: Path,
    case: str,
    expected_failure: str,
) -> None:
    source, _, _ = clean_phase3c_bundle
    bundle = tmp_path / case
    shutil.copytree(source, bundle)

    if case == "inherited_root_frontier":
        proof = _load(bundle / "audit/failed_proof_graph.json")
        frontier_path = bundle / "recovery/frontier.json"
        frontier = _load(frontier_path)
        inherited = next(node for node in proof["nodes"] if node["inherited_bad"] and not node["direct_bad"])
        forged = copy.deepcopy(frontier["nodes"][0])
        forged.update(
            {
                "node_id": inherited["node_id"],
                "cell": inherited["cell"],
                "remaining": inherited["remaining"],
                "direct_bad": False,
                "positive_witness_ids": [],
            }
        )
        frontier["nodes"][0] = forged
        write_json(frontier_path, frontier)
    elif case == "missing_frontier_witness":
        path = bundle / "audit/failed_proof_graph.json"
        document = _load(path)
        node = next(node for node in document["nodes"] if node["direct_bad"] and node["witnesses"])
        node["witnesses"].pop()
        write_json(path, document)
    elif case == "slice_add_nonfrontier":
        proof = _load(bundle / "audit/failed_proof_graph.json")
        path = bundle / "recovery/ground_slice.json"
        document = _load(path)
        forged = copy.deepcopy(document["cells"][0])
        forged["node_id"] = proof["root_node_ids"][0]
        forged["remaining"] = 2
        document["cells"].append(forged)
        write_json(path, document)
    elif case == "slice_missing_action":
        path = bundle / "recovery/ground_slice.json"
        document = _load(path)
        document["cells"][0]["members"][0]["actions"].pop()
        write_json(path, document)
    elif case == "patch_outside_scope":
        authorization = _load(bundle / "recovery/authorization.json")
        path = bundle / "recovery/overlay.json"
        document = _load(path)
        outsider = authorization["reverse_selected_dependency_state_actions"][0]
        document["decisions"][0]["state_id"] = outsider["state_id"]
        document["decisions"][0]["action_id"] = outsider["action_id"]
        write_json(path, document)
    elif case == "base_model_changed":
        path = bundle / "build/portable_rapm.json"
        document = _load(path)
        document["horizon"] += 1
        write_json(path, document)
    elif case == "early_j0_event":
        path = bundle / "events.jsonl"
        rows = _load_rows(path)
        terminal = rows[9]
        rows[9] = {"sequence": 10, "event": "evaluation_only_j0_started"}
        rows[10] = {
            "sequence": 11,
            "event": "all_terminal_route_certificates_frozen",
            "terminal_plan_freeze_id": terminal["terminal_plan_freeze_id"],
        }
        write_jsonl(path, rows)
    elif case == "locality_counter_forged":
        path = bundle / "evaluation/locality.json"
        document = _load(path)
        document["authorized_state_action_pairs"] = 41
        write_json(path, document)
    elif case == "work_counter_forged":
        path = bundle / "accounting/work_counters.json"
        document = _load(path)
        local_row = next(
            row for row in document["query"]
            if row["route"] == "LOCAL_GROUND_RECOVERY"
        )
        local_row["isolated_local_plan"]["invocations"] += 1
        write_json(path, document)
    elif case == "route_forged":
        path = bundle / "result/route_certificates.jsonl"
        rows = _load_rows(path)
        rows[1]["route"] = "ABSTRACT_CERTIFIED"
        write_jsonl(path, rows)
    elif case == "post_audit_risk_forged":
        path = bundle / "audit/post_recovery.jsonl"
        rows = _load_rows(path)
        rows[0]["lifted_failure_upper"] = {"numerator": 0, "denominator": 1}
        write_jsonl(path, rows)
    elif case == "runtime_attestation_reused":
        path = bundle / "recovery/runtime_attestation.json"
        document = _load(path)
        payload = dict(document)
        payload.pop("attestation_id")
        payload["occurrence_id"] = "occurrence-from-another-transaction"
        document = {
            **payload,
            "attestation_id": "local-runtime-attestation:"
            + canonical_sha256(payload),
        }
        write_json(path, document)
    elif case == "portable_attestation_reused":
        path = bundle / "campaign/portable_plans.jsonl"
        rows = _load_rows(path)
        rows[0]["runtime_attestation"] = copy.deepcopy(
            rows[1]["runtime_attestation"]
        )
        write_jsonl(path, rows)
    else:  # pragma: no cover - param table and implementation must stay aligned
        raise AssertionError(case)

    _resign_complete_bundle(bundle)
    assert verify_artifact_bundle(bundle) == []
    verification = verify_phase3c(bundle)
    assert not verification["verified"]
    assert any(expected_failure in failure for failure in verification["failures"])


def test_phase3c_verifier_rejects_resigned_manifest_contract_forgery(
    clean_phase3c_bundle: tuple[Path, dict, dict],
    tmp_path: Path,
) -> None:
    source, _, _ = clean_phase3c_bundle
    bundle = tmp_path / "manifest-contract"
    shutil.copytree(source, bundle)
    manifest_path = bundle / "manifest.json"
    manifest = _load(manifest_path)
    record = next(row for row in manifest["files"] if row["path"] == "recovery/frontier.json")
    record["role"] = "forged_frontier_role"
    manifest["bundle_sha256"] = canonical_sha256(manifest["files"])
    write_json(manifest_path, manifest)
    (bundle / "manifest.sha256").write_text(
        f"{sha256_file(manifest_path)}  manifest.json\n",
        encoding="ascii",
    )

    verification = verify_phase3c(bundle)
    assert not verification["verified"]
    assert any("role/schema mismatch" in failure for failure in verification["failures"])
