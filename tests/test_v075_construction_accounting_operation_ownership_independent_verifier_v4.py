from __future__ import annotations

import ast
import copy
import inspect
import pickle

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import (
    v075_construction_accounting_operation_ownership_independent_verifier_v4
    as verifier,
)
from test_v075_construction_accounting_operation_ownership_successor_v4 import (
    _freeze_v4,
)


def _verify_v4(monkeypatch: pytest.MonkeyPatch):
    inputs, foundation, schema, prior, _upstream, successor = _freeze_v4(
        monkeypatch
    )
    verification = (
        verifier
        .verify_v075_construction_accounting_operation_ownership_bytes_v4(
            successor_bytes=successor.canonical_bytes,
            registry_successor_bytes=prior.canonical_bytes,
            schema_closure_bytes=schema.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )
    )
    return inputs, foundation, schema, prior, successor, verification


def test_independent_operation_ownership_verification_and_locks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inputs, _foundation, _schema, _prior, successor, verification = (
        _verify_v4(monkeypatch)
    )
    document = verification.to_document()
    assert document["successor_id"] == successor.successor_id
    assert document["counter_registry_id"] == (
        verifier.EXPECTED_COUNTER_REGISTRY_V4_ID
    )
    assert document["stage_profile_id"] == (
        verifier.EXPECTED_STAGE_PROFILE_V4_ID
    )
    assert document["comparison_profile_id"] == (
        verifier.EXPECTED_COMPARISON_PROFILE_V4_ID
    )
    assert document["actual_projection_profile_id"] == (
        verifier.EXPECTED_ACTUAL_PROJECTION_PROFILE_V4_ID
    )
    assert document["producer_imported"] is False
    assert document["producer_entry_called"] is False
    assert document["construction_accounting_v4_core_imported"] is False
    assert document[
        "construction_accounting_v4_core_entry_called"
    ] is False
    assert document["upstream_contract_186_replayed_exactly"] is True
    assert document[
        "v3_prefix_compared_from_verified_upstream_bytes"
    ] is True
    assert document["eight_additions_checked_independently"] is True
    assert document["stage_ownership_checked_independently"] is True
    assert document[
        "projection_106_terms_checked_independently"
    ] is True
    assert document["operation_site_instrumentation_complete"] is False
    assert document["live_counter_record_count"] == 0
    assert document["work_vector_count"] == 0
    assert document[
        "owned_root_cap_result_audit_host_full_replay_allowed"
    ] is False
    assert document["owned_root_cap_no_full_replay_runner_wired"] is False
    assert document["legacy_v2_portable_replay_default_unchanged"] is True
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
            lambda value: value["leaves"][-1].__setitem__(
                "unit", "forged"
            ),
        ),
        (
            "stage_profile",
            lambda value: value["rules"][0][
                "allowed_nonzero_paths"
            ].append("forged.path"),
        ),
        (
            "comparison_profile",
            lambda value: value["terms"][-1].__setitem__(
                "coefficient", 2
            ),
        ),
        (
            "actual_projection_profile",
            lambda value: value["terms"][-1].__setitem__(
                "target_axis", "read_bytes"
            ),
        ),
    ),
)
def test_embedded_v4_profile_tampering_fails(
    monkeypatch: pytest.MonkeyPatch,
    section: str,
    mutator,
) -> None:
    inputs, foundation, schema, prior, _upstream, successor = _freeze_v4(
        monkeypatch
    )
    attacked = copy.deepcopy(successor.to_document())
    mutator(attacked[section])
    with pytest.raises(
        verifier.V075ConstructionAccountingOperationOwnershipIndependentV4Violation
    ):
        verifier.verify_v075_construction_accounting_operation_ownership_bytes_v4(
            successor_bytes=canonical_json_bytes(attacked),
            registry_successor_bytes=prior.canonical_bytes,
            schema_closure_bytes=schema.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )


def test_outer_lock_and_upstream_prefix_tampering_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, foundation, schema, prior, _upstream, successor = _freeze_v4(
        monkeypatch
    )
    attacked = copy.deepcopy(successor.to_document())
    attacked["official_execution_allowed"] = True
    with pytest.raises(
        verifier.V075ConstructionAccountingOperationOwnershipIndependentV4Violation
    ):
        verifier.verify_v075_construction_accounting_operation_ownership_bytes_v4(
            successor_bytes=canonical_json_bytes(attacked),
            registry_successor_bytes=prior.canonical_bytes,
            schema_closure_bytes=schema.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )

    attacked_prior = copy.deepcopy(prior.to_document())
    attacked_prior["counter_registry"]["leaves"][0]["unit"] = "forged"
    with pytest.raises(
        verifier.V075ConstructionAccountingOperationOwnershipIndependentV4Violation
    ):
        verifier.verify_v075_construction_accounting_operation_ownership_bytes_v4(
            successor_bytes=successor.canonical_bytes,
            registry_successor_bytes=canonical_json_bytes(attacked_prior),
            schema_closure_bytes=schema.canonical_bytes,
            foundation_bytes=foundation.canonical_bytes,
            **inputs,
        )


def test_verifier_signature_requires_complete_upstream_replay() -> None:
    assert tuple(
        inspect.signature(
            verifier
            .verify_v075_construction_accounting_operation_ownership_bytes_v4
        ).parameters
    ) == (
        "successor_bytes",
        "registry_successor_bytes",
        "schema_closure_bytes",
        "foundation_bytes",
        "source_code_provenance_bytes",
        "repository_root",
        "portable_bundle_bytes",
        "public_context_closure_bytes",
        "private_generation_seed",
        "private_salt",
    )


def test_verifier_does_not_import_or_call_v4_core_or_producer() -> None:
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
        name.endswith("construction_accounting_registry_v4")
        or name.endswith(
            "v075_construction_accounting_operation_ownership_successor_v4"
        )
        for name in imported
    )
    source = inspect.getsource(verifier)
    assert "official_counter_registry_v4" not in source
    assert (
        "materialize_v075_construction_accounting_operation_ownership_successor_v4"
        not in source
    )
