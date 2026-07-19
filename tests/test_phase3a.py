from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

from acfqp.artifacts import (
    PHASE3A_DOCUMENT_CONTRACTS,
    PHASE3A_REQUIRED_PATHS,
    canonical_sha256,
    sha256_file,
    verify_artifact_bundle,
    write_json,
    write_jsonl,
)
from acfqp.phase3a import run_phase3a


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_phase3a import verify_phase3a  # noqa: E402


@pytest.fixture(scope="session")
def clean_bundle(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    bundle = tmp_path_factory.mktemp("phase3a") / "bundle"
    summary = run_phase3a(bundle)
    assert verify_artifact_bundle(bundle) == []
    return bundle, summary


@pytest.fixture(scope="session")
def clean_report(clean_bundle: tuple[Path, dict]) -> dict:
    bundle, _ = clean_bundle
    return verify_phase3a(bundle, recompute=True)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _resign(bundle: Path, relative_path: str) -> None:
    manifest_path = bundle / "manifest.json"
    manifest = _read_json(manifest_path)
    record = next(item for item in manifest["files"] if item["path"] == relative_path)
    target = bundle / relative_path
    record["bytes"] = target.stat().st_size
    record["sha256"] = sha256_file(target)
    manifest["bundle_sha256"] = canonical_sha256(manifest["files"])
    write_json(manifest_path, manifest)
    (bundle / "manifest.sha256").write_text(
        f"{sha256_file(manifest_path)}  manifest.json\n",
        encoding="ascii",
    )


def _copy(source: Path, destination: Path) -> Path:
    shutil.copytree(source, destination)
    return destination


def test_clean_phase3a_bundle_and_fresh_goldens_verify(
    clean_bundle: tuple[Path, dict],
    clean_report: dict,
) -> None:
    bundle, summary = clean_bundle
    manifest = _read_json(bundle / "manifest.json")
    records = {record["path"]: record for record in manifest["files"]}

    assert summary["status"] == "PHASE3A_SLICE_PASS"
    assert summary["full_phase3_gate_status"] == "PHASE3_AGGREGATE_NOT_RUN"
    assert clean_report["verified"], clean_report["failures"]
    assert clean_report["semantic_hash"] == summary["semantic_hash"]
    assert clean_report["recomputed_semantic_hash"] == summary["semantic_hash"]
    assert set(records) == set(PHASE3A_REQUIRED_PATHS)
    assert set(manifest["required_paths"]) == set(PHASE3A_REQUIRED_PATHS)
    for path, (role, schema) in PHASE3A_DOCUMENT_CONTRACTS.items():
        assert records[path]["required"] is True
        assert records[path]["role"] == role
        assert records[path]["schema"] == schema


def test_phase3a_train_test_isolation_and_cross_automorphism_goldens(
    clean_bundle: tuple[Path, dict],
    clean_report: dict,
) -> None:
    bundle, _ = clean_bundle
    query_registry = _read_json(bundle / "suite/query_registry.json")
    reuse = _read_json(bundle / "evaluation/reuse.json")
    symmetry = _read_json(bundle / "evaluation/symmetry_nontriviality.json")
    report = _read_json(bundle / "result/phase3a_slice_report.json")
    policy_graphs = _read_json(bundle / "evaluation/policy_graphs.json")[
        "policy_graphs"
    ]
    graph_by_id = {graph["policy_graph_id"]: graph for graph in policy_graphs}
    rows = [
        json.loads(line)
        for line in (bundle / "evaluation/j0_jkappa_j2_rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]

    assert clean_report["verified"]
    assert query_registry["construction_inputs"] == "train queries only"
    assert query_registry["heldout_queries_used_in_partition_selection"] is False
    assert [record["split"] for record in query_registry["records"]].count("train") == 3
    assert [record["split"] for record in query_registry["records"]].count("heldout") == 6
    assert all(record["heldout_used_for_construction"] is False for record in reuse.values())
    assert all(
        record["all_heldout_supports_within_train_build"] is True
        for record in reuse.values()
    )
    assert symmetry["g2048"]["automorphism_count"] == 8
    assert symmetry["lmb"]["automorphism_count"] == 4
    assert symmetry["g2048"]["covered_ground_states"] == 192
    assert symmetry["g2048"]["known_symmetry_total_state_orbits"] == 28
    assert symmetry["g2048"]["candidate_total_cells"] == 8
    assert symmetry["g2048"]["active_ground_states"] == 68
    assert symmetry["g2048"]["known_symmetry_state_orbits"] == 9
    assert symmetry["g2048"]["candidate_active_cells"] == 7
    assert symmetry["lmb"]["covered_ground_states"] == 25
    assert symmetry["lmb"]["known_symmetry_total_state_orbits"] == 13
    assert symmetry["lmb"]["candidate_total_cells"] == 5
    assert symmetry["lmb"]["active_ground_states"] == 18
    assert symmetry["lmb"]["known_symmetry_state_orbits"] == 10
    assert symmetry["lmb"]["candidate_active_cells"] == 3
    assert symmetry["g2048"]["known_symmetry_state_action_orbits"] == 18
    assert symmetry["g2048"]["abstract_state_action_pairs"] == 14
    assert all(
        record["active_state_compression"]["numerator"]
        >= 5 * record["active_state_compression"]["denominator"]
        for record in symmetry.values()
    )
    assert symmetry["g2048"]["policy_reachable_mixed_cell_count"] >= 1
    assert symmetry["lmb"]["policy_reachable_mixed_cell_count"] >= 1
    assert len(symmetry["g2048"]["training_policy_reached_orbits"]) == 2
    assert len(symmetry["lmb"]["training_policy_reached_orbits"]) == 1
    for record in symmetry.values():
        assert any(
            cell["cross_automorphism"]
            and cell["reached_physical_orbit_count"] >= 2
            for policy in record["training_policy_reached_orbits"]
            for cell in policy["cells"]
        )
        for policy in record["training_policy_reached_orbits"]:
            graph = graph_by_id[policy["policy_graph_id"]]
            assert graph["query_id"] == policy["query_id"]
            assert graph["abstract_policy_signature"] == policy[
                "abstract_policy_signature"
            ]
            assert graph["lifted_semantic_policy_signature"] == policy[
                "lifted_semantic_policy_signature"
            ]
    assert symmetry["g2048"]["explicit_pair_both_policy_reachable"] is True
    assert symmetry["g2048"]["explicit_pair_same_semantic_action"] is True
    assert symmetry["g2048"]["explicit_pair_semantic_actions"] == [
        "survivor:away_from_nonmerged",
        "survivor:away_from_nonmerged",
    ]
    assert symmetry["lmb"]["explicit_pair_same_behavioral_cell"] is True
    assert symmetry["lmb"]["explicit_pair_same_known_automorphism_orbit"] is False
    assert symmetry["lmb"]["explicit_pair_both_policy_reachable"] is True
    assert symmetry["lmb"]["explicit_pair_same_semantic_action"] is True
    assert len(symmetry["lmb"]["explicit_pair_semantic_actions"]) == 2
    assert (
        symmetry["lmb"]["explicit_pair_semantic_actions"][0]
        == symmetry["lmb"]["explicit_pair_semantic_actions"][1]
    )
    assert symmetry["lmb"]["explicit_pair_cell"] is not None
    bridge = next(
        row
        for row in rows
        if row["query_key"] == "g2048.strict_cross_d4_bridge.h1"
    )
    assert bridge["j0_expected_reward"] == {"numerator": 13, "denominator": 400}
    assert bridge["j0_failure_probability"] == {
        "numerator": 199,
        "denominator": 5000,
    }
    assert bridge["j2_lifted_expected_reward"] == bridge["j0_expected_reward"]
    assert bridge["j2_lifted_failure_probability"] == bridge[
        "j0_failure_probability"
    ]
    assert bridge["audit_reward_lower"] == bridge["j0_expected_reward"]
    assert bridge["audit_failure_upper"] == {"numerator": 1, "denominator": 25}
    assert bridge["audit_regret_upper"] == {"numerator": 0, "denominator": 1}
    policy_graph_ids = set(graph_by_id)
    zero = {"numerator": 0, "denominator": 1}
    assert len(policy_graph_ids) == len(rows) == len(policy_graphs)
    assert all(row["policy_graph_id"] in policy_graph_ids for row in rows)
    assert all(
        row[field] == zero
        for row in rows
        for field in (
            "action_restriction_reward_gap",
            "state_alias_selector_reward_gap",
            "full_reward_gap",
            "action_restriction_failure_gap",
            "state_alias_selector_failure_gap",
            "full_failure_gap",
        )
    )
    assert all(all(checks.values()) for checks in report["domain_checks"].values())


@pytest.mark.parametrize(
    ("case", "expected_failure"),
    [
        ("train_split", "train/test isolation"),
        ("selected_atom", "fresh authoritative artifact mismatch"),
        ("evaluation", "fresh evaluation/golden mismatch"),
        ("automorphism", "automorphism/nontriviality artifact mismatch"),
        ("claim", "narrow slice report/claim mismatch"),
    ],
)
def test_resigned_phase3a_semantic_tampering_is_rejected(
    clean_bundle: tuple[Path, dict],
    clean_report: dict,
    tmp_path: Path,
    case: str,
    expected_failure: str,
) -> None:
    assert clean_report["verified"]
    source, _ = clean_bundle
    bundle = _copy(source, tmp_path / case)

    if case == "train_split":
        relative = "suite/query_registry.json"
        document = _read_json(bundle / relative)
        heldout = next(
            record for record in document["records"] if record["split"] == "heldout"
        )
        heldout["split"] = "train"
        write_json(bundle / relative, document)
    elif case == "selected_atom":
        relative = "oracle/g2048_partition_construction.json"
        document = _read_json(bundle / relative)
        document["selected_atom_ids"][0] = "h2:maximum_normalized_reward"
        write_json(bundle / relative, document)
    elif case == "evaluation":
        relative = "evaluation/j0_jkappa_j2_rows.jsonl"
        rows = [
            json.loads(line)
            for line in (bundle / relative).read_text(encoding="utf-8").splitlines()
            if line
        ]
        rows[0]["j2_lifted_expected_reward"] = {"numerator": 0, "denominator": 1}
        write_jsonl(bundle / relative, rows)
    elif case == "automorphism":
        relative = "evaluation/symmetry_nontriviality.json"
        document = _read_json(bundle / relative)
        document["g2048"]["policy_reachable_mixed_cell_count"] = 0
        document["g2048"]["policy_reachable_mixed_cells"] = []
        write_json(bundle / relative, document)
    else:
        relative = "result/phase3a_slice_report.json"
        document = _read_json(bundle / relative)
        document["supported_claims"][0] = "complete Phase-3 aggregate Gate passed"
        write_json(bundle / relative, document)

    _resign(bundle, relative)
    assert verify_artifact_bundle(bundle) == []
    report = verify_phase3a(bundle, recompute=True)
    assert not report["verified"]
    assert any(expected_failure in failure for failure in report["failures"])


def test_phase3a_unmanifested_artifact_is_rejected(
    clean_bundle: tuple[Path, dict],
    tmp_path: Path,
) -> None:
    source, _ = clean_bundle
    bundle = _copy(source, tmp_path / "extra-artifact")
    write_json(bundle / "unexpected.json", {"claim": "not in contract"})

    report = verify_phase3a(bundle, recompute=False)

    assert not report["verified"]
    assert "unmanifested: unexpected.json" in report["failures"]
