from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path

import pytest

from acfqp import (
    construction_k7_full_ground_fallback_production_terminal_independent_verifier_v180r7r1
    as verifier,
)


def test_verifier_import_surface_is_producer_free() -> None:
    source = Path(verifier.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    imported_names = {
        f"{node.module or ''}.{alias.name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    imported = imported_modules | imported_names
    assert not any(
        "recovery_eligible_occurrence_accounting" in name for name in imported
    )
    assert not any("production_terminal_finalizer" in name for name in imported)
    assert not any(
        "materialize_v180r7r1_reachable_source_tree" in name for name in imported
    )
    assert "build_construction_source_closure_v2(" in source
    assert "_verify_occurrence_output(" in source


def test_verifier_rejects_absent_retained_output(tmp_path: Path) -> None:
    with pytest.raises(
        verifier.ConstructionK7FullGroundFallbackIndependentVerifierV180r7r1Error,
        match="output root is absent",
    ):
        verifier.verify_full_ground_fallback_terminal_independently_v180r7r1(
            b"{}", tmp_path / "absent"
        )


def test_retained_output_inventory_rejects_a_symlinked_root(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks are unavailable")
    with pytest.raises(
        verifier.ConstructionK7FullGroundFallbackIndependentVerifierV180r7r1Error,
        match="link or nondirectory",
    ):
        verifier._inventory(linked)


def test_authorization_source_fact_adapter_replays_exact_repo_bytes() -> None:
    repository_root = Path(verifier.__file__).resolve().parents[2]
    relative_path = Path(verifier.__file__).resolve().relative_to(
        repository_root
    ).as_posix()
    raw = Path(verifier.__file__).read_bytes()
    document = {
        "source_facts": [
            {
                "relative_path": relative_path,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        ],
        "source_fact_file_count": 1,
        "source_fact_byte_count": len(raw),
        "source_facts_sha256": hashlib.sha256(
            verifier.canonical_json_bytes(
                [
                    {
                        "relative_path": relative_path,
                        "byte_count": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                ]
            )
        ).hexdigest(),
        "source_fact_exclusions": [],
    }
    verifier._replay_authorization_source_facts(document)
    document["source_facts"][0]["sha256"] = "0" * 64
    with pytest.raises(
        verifier.ConstructionK7FullGroundFallbackIndependentVerifierV180r7r1Error,
        match="authorization-bound source bytes changed",
    ):
        verifier._replay_authorization_source_facts(document)


def test_source_output_epoch_is_one_symlink_free_byte_snapshot(
    tmp_path: Path,
) -> None:
    expected: dict[str, bytes] = {}
    for filename in verifier._OUTPUT_FILENAMES:
        raw = verifier.canonical_json_bytes({"artifact_role": filename[:-5]})
        (tmp_path / filename).write_bytes(raw)
        expected[filename] = raw
    epoch = verifier._capture_source_output_epoch(tmp_path)
    (tmp_path / "BUSINESS_RESULT.json").write_bytes(b"{}")
    assert epoch.role_bytes == expected
    assert len(epoch.inventory) == 8


def test_private_semantic_helper_reads_only_the_captured_epoch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_bytes = {
        filename: verifier.canonical_json_bytes(
            {
                "artifact_role": filename[:-5],
                **(
                    {"runtime_preparation": {"runtime": "captured"}}
                    if filename == "BUSINESS_RESULT.json"
                    else {}
                ),
            }
        )
        for filename in verifier._OUTPUT_FILENAMES
    }
    observed_snapshot: Path | None = None

    def replay(
        snapshot: Path,
        *,
        logical_occurrence_id: str,
        prereg_runtime: dict[str, str],
    ) -> dict[str, str]:
        nonlocal observed_snapshot
        observed_snapshot = snapshot
        assert logical_occurrence_id == verifier._LOGICAL_OCCURRENCE_ID
        assert prereg_runtime == {"runtime": "captured"}
        assert stat_mode(snapshot) == 0o700
        assert {
            path.name: path.read_bytes() for path in snapshot.iterdir()
        } == role_bytes
        assert all(stat_mode(path) == 0o400 for path in snapshot.iterdir())
        return {"bundle_id": "captured"}

    def stat_mode(path: Path) -> int:
        return os.stat(path, follow_symlinks=False).st_mode & 0o777

    monkeypatch.setattr(
        verifier.source_output_verifier,
        "_verify_occurrence_output",
        replay,
    )
    assert verifier._replay_source_occurrence_semantics(role_bytes) == {
        "bundle_id": "captured"
    }
    assert observed_snapshot is not None
    assert not observed_snapshot.exists()


def test_outcome_constants_are_unfrozen_before_first_execution() -> None:
    if verifier.EXPECTED_TERMINAL_BUNDLE_ID == "0" * 64:
        assert verifier.EXPECTED_TERMINAL_BYTE_COUNT == 0
        assert verifier.EXPECTED_TERMINAL_SHA256 == "0" * 64
        assert verifier.EXPECTED_VERIFICATION_ID == "0" * 64
        assert verifier.EXPECTED_VERIFICATION_BYTE_COUNT == 0
        assert verifier.EXPECTED_VERIFICATION_SHA256 == "0" * 64


def test_verifier_requires_fresh_protocol_and_separate_construction_axis() -> None:
    source = Path(verifier.__file__).read_text(encoding="utf-8")
    assert "construction_k7_full_ground_fallback_execution_protocol_v180r7r1" in source
    assert "reused the consumed V180r3 fallback slot or nonce" in source
    assert "three_source_v6_route_chains_reconstructed" in source
    assert "construction_axis_replayed_separately" in source
    assert '"occurrence_counter_record_count": 0' in source
    assert '"occurrence_route_work_vector_count": 0' in source
    assert '"occurrence_comparison_vector_count": 0' in source
    assert "terminal_output_fixed_point_replayed" in source


def test_verifier_exactly_locks_materialization_and_terminal_field_sets() -> None:
    assert len(verifier._MATERIALIZATION_MANIFEST_FIELDS) == 38
    assert len(verifier._MATERIALIZED_TREE_FIELDS) == 18
    assert len(verifier._CONSTRUCTION_WORK_FIELDS) == 18
    assert verifier._EXPECTED_REACHABLE_MODULE_COUNT == 307
    assert verifier._EXPECTED_REACHABLE_SOURCE_BYTE_COUNT == 15_129_926
    assert verifier._OUTPUT_FILENAMES == {
        "ACTUAL_PROJECTION_PROOF.json",
        "BUSINESS_RESULT.json",
        "COMPARISON_VECTOR.json",
        "COUNTER_RECORD_SET.json",
        "OPERATIONAL_TRACE.json",
        "OUTPUT_MANIFEST.json",
        "TERMINAL_ARTIFACT.json",
        "WORK_VECTOR.json",
    }


def test_verifier_field_sets_match_the_separate_finalizer_contract() -> None:
    finalizer_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "acfqp"
        / "construction_k7_full_ground_fallback_production_terminal_finalizer_v180r7r1.py"
    )
    tree = ast.parse(finalizer_path.read_text(encoding="utf-8"))

    def assigned_keys(function_name: str, variable_name: str) -> set[str]:
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == function_name
        )
        matches = [
            {
                key.value
                for key in node.value.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            for node in ast.walk(function)
            if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Dict)
            and any(
                isinstance(target, ast.Name) and target.id == variable_name
                for target in node.targets
            )
        ]
        assert len(matches) == 1
        return matches[0]

    assert assigned_keys("_build_occurrence_receipt", "receipt_payload") == (
        verifier._RECEIPT_FIELDS - {"production_occurrence_receipt_id"}
    )
    assert assigned_keys("_materialize_bundle", "payload") == (
        verifier._TOP_LEVEL_FIELDS - {"production_terminal_bundle_id"}
    )


def test_verifier_field_set_matches_the_separate_authorization_contract() -> None:
    authorization_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "acfqp"
        / "construction_k7_full_ground_fallback_execution_authorization_v180r7r1.py"
    )
    tree = ast.parse(authorization_path.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name
        == "build_full_ground_fallback_execution_authorization_v180r7r1"
    )
    matches = [
        {
            key.value
            for key in node.value.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        for node in ast.walk(function)
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Dict)
        and any(
            isinstance(target, ast.Name) and target.id == "payload"
            for target in node.targets
        )
    ]
    assert len(matches) == 1
    assert matches[0] == (
        verifier._AUTHORIZATION_FIELDS
        - {"fallback_execution_authorization_id"}
    )


def test_verifier_field_set_matches_the_separate_protocol_contract() -> None:
    protocol_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "acfqp"
        / "construction_k7_full_ground_fallback_execution_protocol_v180r7r1.py"
    )
    tree = ast.parse(protocol_path.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "build_full_ground_fallback_execution_protocol_v180r7r1"
    )
    matches = [
        {
            key.value
            for key in node.value.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        for node in ast.walk(function)
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Dict)
        and any(
            isinstance(target, ast.Name) and target.id == "payload"
            for target in node.targets
        )
    ]
    assert len(matches) == 1
    assert matches[0] == (
        verifier._PROTOCOL_FIELDS - {"fallback_execution_protocol_id"}
    )
