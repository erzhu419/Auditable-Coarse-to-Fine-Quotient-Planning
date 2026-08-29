from __future__ import annotations

import ast
import base64
from pathlib import Path

import pytest

from acfqp import (
    construction_k7_campaign_measurement_failure_freeze_v180r12r4r2 as frozen,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "src/acfqp/"
    "construction_k7_campaign_measurement_failure_freeze_v180r12r4r2.py"
)


def test_ordinal8_formal_failure_contract_is_exact_and_claim_bounded() -> None:
    value = frozen.freeze_ordinal8_failure_v180r12r4r2()
    contract = value.to_contract()

    assert set(contract) == {
        "schema",
        "campaign_attempt_id",
        "campaign_attempt_record_id",
        "campaign_failure_id",
        "event_ids",
        "event_kinds",
        "completed_event_count",
        "materialization_terminal_id",
        "outer_service_launch_attempt_id",
        "outer_service_failure_id",
        "inner_launch_attempt_id",
        "inner_launch_failure_id",
        "phase",
        "historical_failure_code",
        "diagnosed_failure_class",
        "historical_failure_code_misclassified",
        "launch_child_created",
        "outer_service_unit_ownership_acquired",
        "full_cgroup_conformance",
        "counter_records_issued",
        "work_vectors_issued",
        "comparison_vectors_issued",
        "gate_statuses",
        "official_execution_allowed",
        "same_identity_rerun_forbidden",
        "terminal_present",
        "independent_replay_present",
        "cgroup_parent_fact",
        "historical_parent_contract",
        "parent_contract_mismatch_fields",
        "full_property_diagnostic_recorded",
    }
    assert contract["campaign_attempt_id"] == frozen.EXPECTED_CAMPAIGN_ATTEMPT_ID
    assert contract["campaign_failure_id"] == frozen.EXPECTED_CAMPAIGN_FAILURE_ID
    assert (
        contract["inner_launch_failure_id"]
        == frozen.EXPECTED_INNER_LAUNCH_FAILURE_ID
    )
    assert (
        contract["outer_service_failure_id"]
        == frozen.EXPECTED_OUTER_SERVICE_FAILURE_ID
    )
    assert contract["event_kinds"] == ["ATTEMPT_OPEN"]
    assert contract["completed_event_count"] == 1
    assert contract["phase"] == "STAGE"
    assert contract["historical_failure_code"] == "SUPERVISOR_BIRTH_FAILURE"
    assert contract["diagnosed_failure_class"] == (
        "CGROUP_TOPOLOGY_CONFORMANCE_FAILURE"
    )
    assert contract["historical_failure_code_misclassified"] is True
    assert contract["launch_child_created"] is False
    assert contract["outer_service_unit_ownership_acquired"] is True
    assert contract["full_cgroup_conformance"] is False
    assert contract["counter_records_issued"] is False
    assert contract["work_vectors_issued"] is False
    assert contract["comparison_vectors_issued"] is False
    assert set(contract["gate_statuses"].values()) == {"NOT_RUN"}
    assert contract["official_execution_allowed"] is False
    assert contract["same_identity_rerun_forbidden"] is True
    assert contract["terminal_present"] is False
    assert contract["independent_replay_present"] is False
    assert contract["cgroup_parent_fact"] == {
        "controllers": ["cpu", "memory", "pids"],
        "subtree_control": ["cpu", "memory", "pids"],
        "self_membership": value.source_membership,
    }
    assert contract["historical_parent_contract"] == {
        "controllers": ["memory", "pids"],
        "subtree_control": ["memory", "pids"],
    }
    assert contract["parent_contract_mismatch_fields"] == [
        "controllers",
        "subtree_control",
    ]
    assert contract["full_property_diagnostic_recorded"] is False


def test_lossless_bundle_restores_only_the_nine_exact_raw_artifacts() -> None:
    documents, raw_by_role = frozen._read_retained_documents(
        frozen._DEFAULT_RETAINED_ROOT
    )

    assert set(documents) == {fact.role for fact in frozen._ARTIFACT_FACTS}
    assert len(raw_by_role) == len(frozen._ARTIFACT_FACTS) == 9
    assert all(
        len(raw_by_role[fact.role]) == fact.byte_count
        for fact in frozen._ARTIFACT_FACTS
    )
    assert documents["attempt_open_event"]["event_kind"] == "ATTEMPT_OPEN"
    assert documents["campaign_failure"]["counter_records_issued"] is False


def test_changed_retained_bundle_is_rejected(tmp_path: Path) -> None:
    retained = tmp_path / "failure"
    retained.mkdir()
    source = frozen._DEFAULT_RETAINED_ROOT / frozen._BUNDLE_NAME
    encoded = source.read_bytes()
    compact = b"".join(encoded.split())
    replacement = b"A" if compact[:1] != b"A" else b"B"
    changed = replacement + compact[1:]
    (retained / frozen._BUNDLE_NAME).write_bytes(
        base64.encodebytes(base64.b64decode(changed))
    )

    with pytest.raises(
        frozen.Ordinal8FailureFreezeV180r12r4r2Error,
        match="unreadable|raw bytes changed",
    ):
        frozen.freeze_ordinal8_failure_v180r12r4r2(retained)


def test_failure_freeze_uses_only_the_standard_library() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
            imported.add((node.module or "").split(".", 1)[0])
    assert imported == {
        "base64",
        "dataclasses",
        "hashlib",
        "io",
        "json",
        "pathlib",
        "tarfile",
        "typing",
    }
