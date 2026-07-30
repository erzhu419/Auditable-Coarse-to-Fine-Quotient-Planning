from __future__ import annotations

import ast
import copy
import inspect
import pickle

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import (
    v075_construction_accounting_registry_successor_independent_verifier_v3
    as verifier,
)
from test_v075_construction_accounting_registry_successor_v3 import (
    _freeze,
)


def _verify(monkeypatch: pytest.MonkeyPatch):
    inputs, foundation, schema, _upstream, successor = _freeze(monkeypatch)
    verification = (
        verifier
        .verify_v075_construction_accounting_registry_successor_bytes_v3(
            successor_bytes=successor.canonical_bytes,
            schema_closure_bytes=schema.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )
    )
    return inputs, foundation, schema, successor, verification


def test_independent_successor_verification_and_locks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inputs, _foundation, _schema, successor, verification = _verify(
        monkeypatch
    )
    document = verification.to_document()
    assert document["successor_id"] == successor.successor_id
    assert document["counter_registry_id"] == (
        verifier.EXPECTED_COUNTER_REGISTRY_V3_ID
    )
    assert document["stage_profile_id"] == (
        verifier.EXPECTED_STAGE_PROFILE_V3_ID
    )
    assert document["comparison_profile_id"] == (
        verifier.EXPECTED_COMPARISON_PROFILE_V3_ID
    )
    assert document["actual_projection_profile_id"] == (
        verifier.EXPECTED_ACTUAL_PROJECTION_PROFILE_V3_ID
    )
    assert document["legacy_migration_profile_id"] == (
        verifier.EXPECTED_LEGACY_MIGRATION_PROFILE_V3_ID
    )
    assert document["producer_imported"] is False
    assert document["producer_entry_called"] is False
    assert document["construction_accounting_v3_core_imported"] is False
    assert (
        document["construction_accounting_v3_core_entry_called"] is False
    )
    assert document[
        "embedded_profile_ids_rehashed_independently"
    ] is True
    assert document[
        "legacy_paths_rebuilt_from_verified_foundation_rows"
    ] is True
    assert document[
        "legacy_disposition_partition_checked_independently"
    ] is True
    assert document["operation_site_instrumentation_complete"] is False
    assert document["live_counter_record_count"] == 0
    assert document["work_vector_count"] == 0
    assert document["official_execution_allowed"] is False
    assert document["fresh_heldout_accessed"] is False
    assert document["plan_certificate"] is False
    assert document["infeasibility_certificate"] is False
    with pytest.raises(TypeError):
        pickle.dumps(verification)


@pytest.mark.parametrize(
    ("section", "mutator"),
    (
        (
            "counter_registry",
            lambda value: value["leaves"][0].__setitem__(
                "unit", "forged"
            ),
        ),
        (
            "stage_profile",
            lambda value: value["rules"][0][
                "allowed_nonzero_paths"
            ].append("unknown.path"),
        ),
        (
            "comparison_profile",
            lambda value: value["terms"][0].__setitem__(
                "coefficient", 2
            ),
        ),
        (
            "legacy_migration_profile",
            lambda value: value["rows"][0].__setitem__(
                "disposition", "FORGED_DISPOSITION"
            ),
        ),
    ),
)
def test_embedded_profile_tampering_fails(
    monkeypatch: pytest.MonkeyPatch,
    section: str,
    mutator,
) -> None:
    inputs, foundation, schema, _upstream, successor = _freeze(
        monkeypatch
    )
    attacked = copy.deepcopy(successor.to_document())
    mutator(attacked[section])
    with pytest.raises(
        verifier.V075ConstructionAccountingSuccessorIndependentV3Violation
    ):
        verifier.verify_v075_construction_accounting_registry_successor_bytes_v3(
            successor_bytes=canonical_json_bytes(attacked),
            schema_closure_bytes=schema.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )


def test_outer_lock_or_verified_foundation_tampering_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, foundation, schema, _upstream, successor = _freeze(
        monkeypatch
    )
    attacked_successor = copy.deepcopy(successor.to_document())
    attacked_successor["official_execution_allowed"] = True
    with pytest.raises(
        verifier.V075ConstructionAccountingSuccessorIndependentV3Violation
    ):
        verifier.verify_v075_construction_accounting_registry_successor_bytes_v3(
            successor_bytes=canonical_json_bytes(attacked_successor),
            schema_closure_bytes=schema.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )

    attacked_foundation = copy.deepcopy(foundation.to_document())
    attacked_foundation["coverage_matrix"]["rows"][0][
        "source_path"
    ] = "forged.path"
    with pytest.raises(
        verifier.V075ConstructionAccountingSuccessorIndependentV3Violation
    ):
        verifier.verify_v075_construction_accounting_registry_successor_bytes_v3(
            successor_bytes=successor.canonical_bytes,
            schema_closure_bytes=schema.canonical_bytes,
            foundation_bytes=canonical_json_bytes(attacked_foundation),
            **inputs,
        )


def test_verifier_does_not_import_or_call_core_or_producer() -> None:
    tree = ast.parse(inspect.getsource(verifier))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(
        name.endswith("construction_accounting_registry_v3")
        or name.endswith(
            "v075_construction_accounting_registry_successor_v3"
        )
        for name in imported
    )
    source = inspect.getsource(verifier)
    assert (
        "materialize_v075_construction_accounting_registry_successor_v3"
        not in source
    )
    assert "official_counter_registry_v3" not in source
