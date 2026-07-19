from fractions import Fraction
import json
from pathlib import Path

from acfqp.artifacts import (
    ALIASED_CEGAR_DOCUMENT_CONTRACTS,
    ALIASED_CEGAR_REQUIRED_PATHS,
    object_id,
    verify_artifact_bundle,
    write_artifact_bundle,
)


def test_artifact_bundle_is_deterministic_and_verifiable(tmp_path: Path) -> None:
    document = {"states": {3, 1, 2}, "probability": Fraction(1, 3)}
    first_id = object_id(document)
    second_id = object_id({"probability": Fraction(1, 3), "states": {2, 3, 1}})
    assert first_id == second_id

    manifest = write_artifact_bundle(
        tmp_path,
        {"run.json": document, "events.jsonl": [{"event": "complete"}]},
    )
    stored = json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))
    assert stored["probability"] == {"numerator": 1, "denominator": 3}
    assert {record["path"] for record in manifest["files"]} == {
        "run.json",
        "events.jsonl",
    }
    assert verify_artifact_bundle(tmp_path) == []


def test_artifact_verifier_rejects_noncanonical_exact_number_and_contract_role(
    tmp_path: Path,
) -> None:
    write_artifact_bundle(
        tmp_path,
        {"run.json": {"bad_exact_value": {"numerator": 2, "denominator": 4}}},
        roles={"run.json": "wrong_role"},
        required_paths=("run.json",),
    )
    failures = verify_artifact_bundle(tmp_path)
    assert "role mismatch: run.json" in failures
    assert any("unreduced rational" in failure for failure in failures)


def test_aliased_cegar_bundle_uses_its_complete_profile_contract(
    tmp_path: Path,
) -> None:
    documents = {
        path: ([{"event": "complete"}] if path.endswith(".jsonl") else {"path": path})
        for path in ALIASED_CEGAR_REQUIRED_PATHS
    }

    manifest = write_artifact_bundle(
        tmp_path,
        documents,
        required_paths=ALIASED_CEGAR_REQUIRED_PATHS,
    )

    records = {record["path"]: record for record in manifest["files"]}
    assert set(records) == set(ALIASED_CEGAR_REQUIRED_PATHS)
    assert manifest["required_paths"] == sorted(ALIASED_CEGAR_REQUIRED_PATHS)
    for path, (role, schema) in ALIASED_CEGAR_DOCUMENT_CONTRACTS.items():
        assert records[path]["required"] is True
        assert records[path]["role"] == role
        assert records[path]["schema"] == schema
    assert verify_artifact_bundle(tmp_path) == []
