from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

from acfqp import (
    construction_k7_recovery_eligible_world_model_loop_independent_verifier_v1
    as subject,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


def _inputs() -> tuple[bytes, bytes, bytes]:
    retained = os.environ.get("ACFQP_RETAINED_RECOVERY_ELIGIBLE_LOOP_INPUTS")
    if not retained:
        pytest.skip("retained recovery-eligible loop inputs are absent")
    root = Path(retained)
    return (
        (root / "CHECKPOINT.json").read_bytes(),
        (root / "GROUND_TRANSACTION.json").read_bytes(),
        (root / "WORLD_MODEL_LOOP.json").read_bytes(),
    )


def test_independent_verifier_import_surface_excludes_both_producers() -> None:
    source_path = Path(subject.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
            imported.update(alias.name for alias in node.names)
    assert not any(
        "construction_k7_recovery_eligible_checkpoint_fixture_v1" in name
        or "construction_k7_recovery_eligible_world_model_loop_v1" in name
        for name in imported
    )


def test_independent_bytes_replay_recomputes_both_h2_proofs_and_fallback_route() -> None:
    checkpoint, transaction, result = _inputs()
    verification = subject.verify_recovery_eligible_world_model_loop_bytes_v1(
        checkpoint_bytes=checkpoint,
        ground_transaction_bytes=transaction,
        world_model_loop_bytes=result,
    )
    assert verification["independently_recomputed_source_h2_proof"] is True
    assert verification["independently_recomputed_successor_h2_proof"] is True
    assert verification["validation_batch_content_ids_recomputed"] is True
    assert verification["validation_aggregate_counts_reconciled"] is True
    assert verification["immutable_overlay_independently_replayed"] is True
    assert verification["unrequested_rows_byte_identical"] is True
    assert verification["proof_still_failed"] is True
    assert verification["verified_next_route"] == "DIRECT_GROUND_FALLBACK"
    assert verification["plan_certificate_verified"] is False
    assert verification["valid"] is True


def test_compact_observer_boundary_is_reported_without_overclaim() -> None:
    checkpoint, transaction, result = _inputs()
    verification = subject.verify_recovery_eligible_world_model_loop_bytes_v1(
        checkpoint_bytes=checkpoint,
        ground_transaction_bytes=transaction,
        world_model_loop_bytes=result,
    )
    assert verification["portable_discovery_batch_replay_present"] is False
    assert verification["observer_rsa_signature_independently_reverified"] is False
    assert verification["compact_observer_closure_summary_only"] is True
    assert verification["verification_lane"] == "EVALUATION"
    assert verification["verification_work_included_in_operational_route_work"] is False
    assert verification["official_execution_allowed"] is False


@pytest.mark.parametrize(
    ("artifact_index", "mutator"),
    (
        (2, lambda document: document.__setitem__("unknown_field", True)),
        (
            2,
            lambda document: document["validation_deltas"][0][
                "signed_validation_batch"
            ].__setitem__("observer_signature_verified", False),
        ),
        (
            1,
            lambda document: document.__setitem__(
                "cap_blocked_rows_not_accessed", False
            ),
        ),
        (
            0,
            lambda document: document.__setitem__(
                "production_latest_epoch_selection_authority", True
            ),
        ),
    ),
)
def test_canonical_resigned_semantic_and_unknown_field_attacks_are_rejected(
    artifact_index,
    mutator,
) -> None:
    artifacts = list(_inputs())
    document = loads_canonical_json(artifacts[artifact_index])
    mutator(document)
    artifacts[artifact_index] = canonical_json_bytes(document)
    with pytest.raises(
        subject.ConstructionK7RecoveryEligibleWorldModelLoopIndependentVerifierV1Error
    ):
        subject.verify_recovery_eligible_world_model_loop_bytes_v1(
            checkpoint_bytes=artifacts[0],
            ground_transaction_bytes=artifacts[1],
            world_model_loop_bytes=artifacts[2],
        )


def test_public_surface_is_verifier_only() -> None:
    assert set(subject.__all__) == {
        "ConstructionK7RecoveryEligibleWorldModelLoopIndependentVerifierV1Error",
        "verify_recovery_eligible_world_model_loop_bytes_v1",
    }
