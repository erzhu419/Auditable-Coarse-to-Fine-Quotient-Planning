from fractions import Fraction
import json
from pathlib import Path

from acfqp.artifacts import object_id, verify_artifact_bundle, write_artifact_bundle


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
