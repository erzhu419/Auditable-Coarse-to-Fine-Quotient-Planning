import json
import shutil
from pathlib import Path

import pytest

from acfqp.artifacts import (
    D4_BASELINE_DOCUMENT_CONTRACTS,
    D4_BASELINE_REQUIRED_PATHS,
    canonical_sha256,
    sha256_file,
    verify_artifact_bundle,
    write_json,
    write_jsonl,
)
from acfqp.d4_baseline import (
    CERTIFIED,
    INVARIANT_VIOLATION,
    run_exact_d4_baseline,
)
from scripts.verify_d4_baseline import (
    _verify_reference_manifest_hashes,
    verify_exact_d4_bundle,
)


@pytest.fixture(scope="module")
def canonical_bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("exact-d4") / "bundle"
    run_exact_d4_baseline(output)
    return output


def _copy_bundle(source: Path, destination: Path) -> Path:
    shutil.copytree(source, destination)
    return destination


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


def test_exact_d4_reference_manifest_pair_is_optional_but_atomic(
    tmp_path: Path,
) -> None:
    run = {"reference_manifest_hashes": {}}
    failures: list[str] = []
    _verify_reference_manifest_hashes(run, failures, root=tmp_path)
    assert failures == []

    run["reference_manifest_hashes"] = {
        "reference/download_manifest.json": "stale"
    }
    failures = []
    _verify_reference_manifest_hashes(run, failures, root=tmp_path)
    assert any("must be empty" in failure for failure in failures)

    reference = tmp_path / "reference"
    reference.mkdir()
    download = reference / "download_manifest.json"
    download.write_text('{"kind":"download"}\n', encoding="utf-8")
    run["reference_manifest_hashes"] = {}
    failures = []
    _verify_reference_manifest_hashes(run, failures, root=tmp_path)
    assert any("pair is incomplete" in failure for failure in failures)

    clone = reference / "repo_clone_manifest.json"
    clone.write_text('{"kind":"repos"}\n', encoding="utf-8")
    run["reference_manifest_hashes"] = {
        "reference/download_manifest.json": sha256_file(download),
        "reference/repo_clone_manifest.json": sha256_file(clone),
    }
    failures = []
    _verify_reference_manifest_hashes(run, failures, root=tmp_path)
    assert failures == []

    run["reference_manifest_hashes"]["reference/download_manifest.json"] = "stale"
    failures = []
    _verify_reference_manifest_hashes(run, failures, root=tmp_path)
    assert any("do not exactly match" in failure for failure in failures)


def test_exact_d4_bundle_is_certified_strictly_compressed_and_recomputes(
    canonical_bundle: Path,
) -> None:
    assert verify_artifact_bundle(canonical_bundle) == []
    report = verify_exact_d4_bundle(canonical_bundle, recompute=True)
    assert report["verified"]
    assert report["status"] == CERTIFIED
    assert report["included_in_positive_claim"] is True
    assert report["semantic_hash"] == report["recomputed_semantic_hash"]

    manifest = json.loads(
        (canonical_bundle / "manifest.json").read_text(encoding="utf-8")
    )
    records = {record["path"]: record for record in manifest["files"]}
    assert set(records) == set(D4_BASELINE_REQUIRED_PATHS)
    for path, (role, schema) in D4_BASELINE_DOCUMENT_CONTRACTS.items():
        assert records[path]["required"] is True
        assert records[path]["role"] == role
        assert records[path]["schema"] == schema
    assert not any(
        marker in path.lower()
        for path in records
        for marker in ("refinement/", "witness", "candidate", "split", "fallback")
    )

    certificate = json.loads(
        (canonical_bundle / "result" / "exact_d4_certificate.json").read_text(
            encoding="utf-8"
        )
    )
    assert certificate["status"] == CERTIFIED
    assert certificate["expected_failure_probability"] == {
        "numerator": 99,
        "denominator": 5000,
    }
    assert certificate["expected_survival_probability"] == {
        "numerator": 4901,
        "denominator": 5000,
    }
    assert certificate["action_restriction_gap"] == {
        "numerator": 0,
        "denominator": 1,
    }
    compression = certificate["compression"]
    assert compression["ground_state_time_count"] == 72
    assert compression["quotient_state_time_count"] == 7
    assert compression["ground_legal_action_count"] == 48
    assert compression["semantic_action_orbit_count"] == 6


def test_verifier_rejects_rehashed_duplicate_kx_as_invariant_violation(
    canonical_bundle: Path, tmp_path: Path
) -> None:
    output = _copy_bundle(canonical_bundle, tmp_path / "duplicate-kx")
    path = output / "symmetry" / "concretizers.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    record = next(
        record
        for record in document["records"]
        if len(record["distinct_inverse_ground_action_ids"]) > 1
    )
    record["distinct_inverse_ground_action_ids"].append(
        record["distinct_inverse_ground_action_ids"][0]
    )
    record["distinct_inverse_ground_actions"].append(
        record["distinct_inverse_ground_actions"][0]
    )
    write_json(path, document)
    _resign_bundle(output, "symmetry/concretizers.json")

    report = verify_exact_d4_bundle(output, recompute=False)
    assert not report["verified"]
    assert report["status"] == INVARIANT_VIOLATION
    assert report["included_in_positive_claim"] is False
    assert any("distinct action set" in failure for failure in report["failures"])
    assert not (output / "refinement").exists()
    assert not any("fallback" in path.name.lower() for path in output.rglob("*"))


def test_verifier_rejects_rehashed_nonzero_envelope_width(
    canonical_bundle: Path, tmp_path: Path
) -> None:
    output = _copy_bundle(canonical_bundle, tmp_path / "nonzero-width")
    path = output / "rapm" / "envelope_exact.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["maximum_reward_width"] = {"numerator": 1, "denominator": 100}
    document["entries"][0]["interval_width_zero"] = False
    write_json(path, document)
    _resign_bundle(output, "rapm/envelope_exact.json")

    report = verify_exact_d4_bundle(output, recompute=False)
    assert not report["verified"]
    assert report["status"] == INVARIANT_VIOLATION
    assert report["included_in_positive_claim"] is False
    assert any("nonzero maximum_reward_width" in failure for failure in report["failures"])


def test_verifier_classifies_rehashed_automorphism_failure_without_refinement(
    canonical_bundle: Path, tmp_path: Path
) -> None:
    output = _copy_bundle(canonical_bundle, tmp_path / "bad-automorphism")
    path = output / "symmetry" / "automorphism_checks.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["all_passed"] = False
    document["transition_checks"][0]["passed"] = False
    document["transition_checks"][0]["coalesced_exact_kernel_equal"] = False
    write_json(path, document)
    _resign_bundle(output, "symmetry/automorphism_checks.json")

    report = verify_exact_d4_bundle(output, recompute=False)
    assert not report["verified"]
    assert report["status"] == INVARIANT_VIOLATION
    assert report["included_in_positive_claim"] is False
    assert any("automorphism check failed" in failure for failure in report["failures"])
    assert not (output / "refinement").exists()
    assert not any("fallback" in path.name.lower() for path in output.rglob("*"))


def test_verifier_rejects_rehashed_incomplete_state_orbit(
    canonical_bundle: Path, tmp_path: Path
) -> None:
    output = _copy_bundle(canonical_bundle, tmp_path / "missing-orbit-member")
    path = output / "symmetry" / "state_orbits.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    orbit = next(
        orbit
        for orbit in document["orbits"]
        if not orbit["failure"] and len(orbit["member_state_time_ids"]) > 1
    )
    orbit["member_state_time_ids"].pop()
    orbit["member_state_ids"].pop()
    orbit["canonicalizer_record_ids"].pop()
    write_json(path, document)
    _resign_bundle(output, "symmetry/state_orbits.json")

    report = verify_exact_d4_bundle(output, recompute=False)
    assert not report["verified"]
    assert report["status"] == INVARIANT_VIOLATION
    assert report["included_in_positive_claim"] is False
    assert any("partition is incomplete" in failure for failure in report["failures"])


def test_verifier_rejects_rehashed_group_tie_order_change(
    canonical_bundle: Path, tmp_path: Path
) -> None:
    output = _copy_bundle(canonical_bundle, tmp_path / "group-order")
    path = output / "symmetry" / "profile.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    order = document["ordered_group_element_ids"]
    order[0], order[1] = order[1], order[0]
    write_json(path, document)
    _resign_bundle(output, "symmetry/profile.json")

    report = verify_exact_d4_bundle(output, recompute=False)
    assert not report["verified"]
    assert report["status"] == INVARIANT_VIOLATION
    assert report["included_in_positive_claim"] is False
    assert any("profile/order" in failure for failure in report["failures"])


def test_verifier_rejects_rehashed_fallback_event(
    canonical_bundle: Path, tmp_path: Path
) -> None:
    output = _copy_bundle(canonical_bundle, tmp_path / "fallback-event")
    path = output / "events.jsonl"
    events = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    events.append({"sequence": len(events) + 1, "event": "fallback_invoked"})
    write_jsonl(path, events)
    _resign_bundle(output, "events.jsonl")

    report = verify_exact_d4_bundle(output, recompute=False)
    assert not report["verified"]
    assert report["status"] == INVARIANT_VIOLATION
    assert report["included_in_positive_claim"] is False
    assert any("forbidden CEGAR/fallback event" in failure for failure in report["failures"])
