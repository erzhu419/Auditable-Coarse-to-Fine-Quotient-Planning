import json
import shutil
from fractions import Fraction
from pathlib import Path

import pytest

from acfqp.artifacts import (
    PHASE05_DOCUMENT_CONTRACTS,
    PHASE05_REQUIRED_PATHS,
    canonical_sha256,
    sha256_file,
    verify_artifact_bundle,
    write_json,
)
from acfqp.build_coverage import (
    BuildCoverage,
    QueryOutsideBuildCoverageError,
    validate_query_coverage,
)
from acfqp.core import QuerySpec
from acfqp.domains.g2048 import G2048State
from acfqp.phase05 import _fixture, run_fixture
from scripts.verify_phase05 import verify_domain


def _resign_bundle(output: Path, changed_path: str) -> None:
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact = output / changed_path
    for record in manifest["files"]:
        if record["path"] == changed_path:
            record["bytes"] = artifact.stat().st_size
            record["sha256"] = sha256_file(artifact)
            break
    manifest["bundle_sha256"] = canonical_sha256(manifest["files"])
    write_json(manifest_path, manifest)
    (output / "manifest.sha256").write_text(
        sha256_file(manifest_path) + "  manifest.json\n", encoding="ascii"
    )


def test_g2048_phase05_runs_mandatory_split_then_proves_infeasible(tmp_path: Path) -> None:
    output = tmp_path / "g2048"
    summary = run_fixture("g2048", output)
    assert summary["status"] == "INFEASIBLE_QUERY"
    assert summary["leaves_after"] == summary["leaves_before"] + 1
    assert verify_artifact_bundle(output) == []
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert set(PHASE05_REQUIRED_PATHS) <= {
        record["path"] for record in manifest["files"]
    }
    for record in manifest["files"]:
        role, schema = PHASE05_DOCUMENT_CONTRACTS[record["path"]]
        assert record["required"] is True
        assert record["role"] == role
        assert record["schema"] == schema
    run = json.loads((output / "run.json").read_text(encoding="utf-8"))
    structural = json.loads(
        (output / "config" / "structural.json").read_text(encoding="utf-8")
    )
    query = json.loads((output / "config" / "query.json").read_text(encoding="utf-8"))
    enumeration = json.loads(
        (output / "ground" / "enumeration.json").read_text(encoding="utf-8")
    )
    assert run["seed_ledger"]["seed_ledger_id"].startswith("seed-ledger-")
    assert run["contract_version"] == "0.4.0"
    assert run["structural_key"] == "g2048_select_canonical_2x2_v0"
    assert run["benchmark_role"] == "infeasibility_and_soundness_regression"
    assert run["execution_profile"] == "phase05_vertical_slice"
    assert run["phase05_test_override"] is True
    assert run["claim_eligibility"] == "infeasibility_only"
    assert run["known_exact_j0_status"] == "INFEASIBLE"
    assert "initial_law" not in structural
    assert query["initial_distribution_registration"]
    assert run["build_coverage"]["mode"] == "query_support_transition_closure"
    assert run["build_coverage"]["reuse_outside_coverage_forbidden"] is True
    assert len(run["build_coverage"]) == 4
    assert enumeration["covered_state_count"] == len(
        enumeration["covered_state_ids"]
    )
    assert enumeration["covered_state_ids"] == sorted(
        enumeration["covered_state_ids"]
    )
    assert query["normalizer"] == query["normalizer_value"]
    assert query["normalizer_proof_id"]
    assert run["random_tapes"]["tape_ids"] == ["tape-none-exact-enumeration"]
    assert len(enumeration["transition_kernel_sha256"]) == 64
    assert set(enumeration["failure_set"]).isdisjoint(enumeration["success_set"])
    frontier = json.loads(
        (output / "ground" / "j0_frontier.json").read_text(encoding="utf-8")
    )
    assert frontier["feasible"] is False
    assert frontier["exact_j0_proof_id"] == run["known_exact_j0_proof_id"]
    assert frontier["proof_identity"] == {
        "structural_id": run["known_exact_j0_structural_id"],
        "build_id": run["known_exact_j0_build_id"],
        "kernel_hash": run["known_exact_j0_kernel_hash"],
        "query_hash": run["known_exact_j0_query_hash"],
    }
    assert frontier["frontier"][0]["failure_probability"] == {
        "numerator": 383,
        "denominator": 410,
    }


def test_lmb_phase05_runs_split_and_charged_constrained_fallback(tmp_path: Path) -> None:
    output = tmp_path / "lmb"
    first = run_fixture("lmb", output)
    assert first["status"] in {"CERTIFIED", "GROUND_FALLBACK"}
    assert first["leaves_after"] == first["leaves_before"] + 1
    assert verify_artifact_bundle(output) == []
    result = json.loads(
        (output / "result" / "certificate_or_fallback.json").read_text(
            encoding="utf-8"
        )
    )
    assert result["ground_query_feasible"] is True
    if first["status"] == "GROUND_FALLBACK":
        assert result["fallback_location"]["same_query"] is True
        assert result["fallback_location"]["charged"] is True

    # Wall times and UTC provenance vary; the exact semantic payload must not.
    second = run_fixture("lmb", output)
    assert first["semantic_hash"] == second["semantic_hash"]


def test_phase05_verifier_rejects_rehashed_orphan_proof_dependency(
    tmp_path: Path,
) -> None:
    output = tmp_path / "lmb"
    run_fixture("lmb", output)
    result_path = output / "result" / "certificate_or_fallback.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["abstract_audit"]["proof_dependencies"][0]["child_dependency_ids"] = [
        "proof-bound-does-not-exist"
    ]
    write_json(result_path, result)
    _resign_bundle(output, "result/certificate_or_fallback.json")
    report = verify_domain(output, recompute=False)
    assert not report["verified"]
    assert any("unresolved child proof dependency" in failure for failure in report["failures"])


def test_phase05_verifier_rejects_mismatched_known_j0_kernel_identity(
    tmp_path: Path,
) -> None:
    output = tmp_path / "g2048"
    run_fixture("g2048", output)
    run_path = output / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["known_exact_j0_kernel_hash"] = "0" * 64
    write_json(run_path, run)
    _resign_bundle(output, "run.json")
    report = verify_domain(output, recompute=False)
    assert not report["verified"]
    assert any("known-J0 provenance" in failure for failure in report["failures"])


def test_phase05_verifier_rejects_coverage_contract_tampering(
    tmp_path: Path,
) -> None:
    cases = (
        ("delete_coverage_state", "authoritative transition closure"),
        ("add_coverage_state", "authoritative transition closure"),
        ("wrong_coverage_count", "count is not parseable"),
        ("delete_no_reuse", "build-coverage restriction"),
        ("wrong_contract_version", "contract version"),
        ("structural_initial_law", "initial_law must not appear"),
        ("rho_with_old_build_id", "build ID does not bind"),
    )
    pristine = tmp_path / "pristine"
    run_fixture("g2048", pristine)

    for case, expected_failure in cases:
        output = tmp_path / case
        shutil.copytree(pristine, output)

        if case in {
            "delete_coverage_state",
            "add_coverage_state",
            "wrong_coverage_count",
        }:
            relative = "ground/enumeration.json"
            path = output / relative
            document = json.loads(path.read_text(encoding="utf-8"))
            if case == "delete_coverage_state":
                document["covered_state_ids"].pop()
                document["covered_state_count"] -= 1
            elif case == "add_coverage_state":
                document["covered_state_ids"].append("state-ffffffffffffffff")
                document["covered_state_ids"].sort()
                document["covered_state_count"] += 1
            else:
                document["covered_state_count"] += 1
        elif case == "delete_no_reuse":
            relative = "run.json"
            path = output / relative
            document = json.loads(path.read_text(encoding="utf-8"))
            del document["build_coverage"]["reuse_outside_coverage_forbidden"]
        elif case == "wrong_contract_version":
            relative = "run.json"
            path = output / relative
            document = json.loads(path.read_text(encoding="utf-8"))
            document["contract_version"] = "0.3.0"
        elif case == "structural_initial_law":
            relative = "config/structural.json"
            path = output / relative
            document = json.loads(path.read_text(encoding="utf-8"))
            document["initial_law"] = "query-owned field injected into structure"
        else:
            relative = "config/query.json"
            path = output / relative
            document = json.loads(path.read_text(encoding="utf-8"))
            first = document["initial_distribution"][0][0]
            second = document["initial_distribution"][1][0]
            document["initial_distribution"][0][0] = second
            document["initial_distribution"][1][0] = first

        write_json(path, document)
        _resign_bundle(output, relative)
        report = verify_domain(output, recompute=False)
        assert not report["verified"]
        assert any(
            expected_failure in failure for failure in report["failures"]
        ), report


def test_rho0_change_preserves_structure_but_changes_query_and_build_identity(
    tmp_path: Path,
) -> None:
    fixture = _fixture("g2048")
    distribution = list(fixture.query.initial_distribution)
    distribution[0], distribution[1] = (
        (distribution[1][0], distribution[0][1]),
        (distribution[0][0], distribution[1][1]),
    )
    changed_query = QuerySpec(
        tuple(distribution),
        fixture.query.horizon,
        fixture.query.reward_weights,
        fixture.query.goal,
        fixture.query.delta,
        fixture.query.normalizer,
        fixture.query.normalizer_proof_id,
    )

    default_output = tmp_path / "default"
    changed_output = tmp_path / "changed"
    run_fixture("g2048", default_output)
    run_fixture("g2048", changed_output, query_override=changed_query)
    default_run = json.loads((default_output / "run.json").read_text(encoding="utf-8"))
    changed_run = json.loads((changed_output / "run.json").read_text(encoding="utf-8"))
    default_enumeration = json.loads(
        (default_output / "ground/enumeration.json").read_text(encoding="utf-8")
    )
    changed_enumeration = json.loads(
        (changed_output / "ground/enumeration.json").read_text(encoding="utf-8")
    )

    assert default_run["fixture_id"] == changed_run["fixture_id"]
    assert default_run["query_id"] != changed_run["query_id"]
    assert default_run["build_id"] != changed_run["build_id"]
    assert (
        default_run["build_coverage"]["initial_support_sha256"]
        != changed_run["build_coverage"]["initial_support_sha256"]
    )
    assert (
        default_enumeration["covered_state_ids"]
        == changed_enumeration["covered_state_ids"]
    )
    assert verify_domain(changed_output, recompute=True)["verified"]


def test_candidate_query_support_outside_cached_coverage_requires_rebuild() -> None:
    fixture = _fixture("g2048")
    coverage = BuildCoverage.from_query(fixture.kernel, fixture.query)
    outside_query = QuerySpec.from_state(
        G2048State((0, 0, 0, 0)),
        horizon=1,
        reward_weights=(('merge', Fraction(1)),),
        normalizer=Fraction(1),
        normalizer_proof_id="g2048.canonical.merge_le_1_per_step.total_le_h.v1",
    )

    with pytest.raises(QueryOutsideBuildCoverageError, match="rebuild required"):
        validate_query_coverage(coverage, outside_query)
