from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_persistent_proof_cache_v1 as cache_v1
from acfqp import construction_k7_recovery_eligible_checkpoint_fixture_v1 as checkpoint_v1
from acfqp import construction_k7_recovery_eligible_world_model_loop_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _fresh_id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_domains_and_public_surface_are_additive() -> None:
    assert len(subject.LOCAL_DOMAINS) == 4
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7RecoveryEligibleWorldModelLoopV1Error",
        "ENVIRONMENT_MARKER",
        "LOCAL_DOMAINS",
        "RecoveryEligibleGroundPreparationV1",
        "RecoveryEligibleGroundTransactionV1",
        "RecoveryEligibleNamespaceBindingV1",
        "RecoveryEligibleRowAcquisitionV1",
        "RecoveryEligibleWorldModelLoopV1",
        "compile_recovery_eligible_world_model_loop_v1",
        "execute_prepared_recovery_eligible_ground_transaction_v1",
        "prepare_recovery_eligible_ground_transaction_v1",
        "require_recovery_eligible_world_model_loop_v1",
        "verify_recovery_eligible_ground_transaction_v1",
        "verify_recovery_eligible_world_model_loop_bytes_v1",
        "verify_recovery_eligible_world_model_loop_v1",
    }


@pytest.fixture(scope="module")
def real_world_model_loop():
    retained = os.environ.get("ACFQP_RETAINED_PERSISTENT_PROOF_CACHE_INPUTS")
    real = os.environ.get("ACFQP_RUN_REAL_K7_QUERY_BOUND_GROUND") == "1"
    if not retained or not real:
        pytest.skip("real recovery-eligible world-model loop is disabled")
    root = Path(retained)
    cache = cache_v1.materialize_query_bound_persistent_proof_cache_bytes_v1(
        binding_bytes=(root / "SOURCE_BUNDLE_BINDING.json").read_bytes(),
        snapshot_bytes=(root / "REUSABLE_RAPM_SNAPSHOT.json").read_bytes(),
        transition_bytes=(root / "PROOF_DEPENDENCY_TRANSITION.json").read_bytes(),
    )
    checkpoint = checkpoint_v1.materialize_recovery_eligible_checkpoint_fixture_v1(
        canonical_json_bytes(cache.to_document())
    )
    query = checkpoint_v1.freeze_recovery_eligible_checkpoint_query_v1(
        checkpoint,
        logical_occurrence_id=_fresh_id(
            "recovery-eligible-world-model-loop-occurrence-2"
        ),
        query_ordinal=2,
    )
    consumption = checkpoint_v1.consume_recovery_eligible_checkpoint_v1(
        checkpoint, query
    )
    request = checkpoint_v1.prepare_recovery_eligible_recovery_request_v1(
        checkpoint, consumption
    )
    preparation = subject.prepare_recovery_eligible_ground_transaction_v1(request)
    transaction = subject.execute_prepared_recovery_eligible_ground_transaction_v1(
        preparation
    )
    result = subject.compile_recovery_eligible_world_model_loop_v1(transaction)
    return transaction, result


def test_real_loop_accesses_only_six_preregistered_rows_and_closes_observer(
    real_world_model_loop,
) -> None:
    transaction, result = real_world_model_loop
    transaction_document = transaction.to_document()
    assert transaction_document["requested_row_count"] == 6
    assert transaction_document["cap_blocked_row_count"] == 1
    assert transaction_document["support_discovery_draw_count"] == 384
    assert transaction_document["requested_validation_draw_count"] == 12_288
    assert transaction_document["total_ground_draw_count"] == 12_672
    assert transaction_document["only_requested_rows_executed"] is True
    assert transaction_document["cap_blocked_rows_not_accessed"] is True
    assert transaction_document["observer_closed_and_exactly_reconciled"] is True
    assert len(transaction.observer_closure.appends) == 12
    assert len(transaction.observer_closure.support_freezes) == 6
    assert result.transaction is transaction


def test_real_loop_compiles_immutable_overlay_and_replans_same_h2_query(
    real_world_model_loop,
) -> None:
    _transaction, result = real_world_model_loop
    document = result.to_document()
    assert document["requested_row_count"] == 6
    assert document["cap_blocked_row_count"] == 1
    assert document["changed_row_count"] == 6
    assert document["preserved_row_count"] == 12
    assert document["added_signed_validation_draw_count"] == 12_288
    assert document["total_local_ground_draw_count"] == 12_672
    assert document["horizon"] == 2
    assert document["old_support_frozen_and_reused"] is True
    assert document["unrequested_rows_byte_identical"] is True
    assert document["immutable_query_local_model_compiled"] is True
    assert document["same_multistep_query_replanned"] is True
    assert document["ground_access_after_closed_transaction"] == 0
    # This fresh held-out occurrence remains uncertified.  The construction
    # must report that fact and route onward; it may not manufacture success.
    assert document["proof_still_failed"] is True
    assert document["successor_outcome"] == "FAILED_PROOF_FRONTIER"
    assert document["next_required_action"] == "ROUTE_TO_DIRECT_GROUND_FALLBACK"
    assert document["plan_certificate_issued"] is False
    assert document["official_execution_allowed"] is False


def test_exact_replay_after_closed_transaction_has_no_ground_access(
    real_world_model_loop,
    monkeypatch,
) -> None:
    transaction, result = real_world_model_loop

    def forbidden_ground(*_args, **_kwargs):
        raise AssertionError("exact overlay replay reopened ground access")

    monkeypatch.setattr(
        subject.fixture_v1,
        "prepare_v075_k7_construction_environment_v1",
        forbidden_ground,
    )
    replayed = subject.verify_recovery_eligible_world_model_loop_bytes_v1(
        transaction=transaction,
        result_bytes=canonical_json_bytes(result.to_document()),
    )
    assert replayed.result_id == result.result_id
    assert replayed.successor_model.model_id == result.successor_model.model_id
    assert replayed.successor_proof.proof_id == result.successor_proof.proof_id


def test_resigned_result_semantic_change_is_rejected(real_world_model_loop) -> None:
    transaction, result = real_world_model_loop
    document = result.to_document()
    document["cap_blocked_row_remained_unaccessed"] = False
    with pytest.raises(subject.ConstructionK7RecoveryEligibleWorldModelLoopV1Error):
        subject.verify_recovery_eligible_world_model_loop_bytes_v1(
            transaction=transaction,
            result_bytes=canonical_json_bytes(document),
        )


def test_transaction_and_loop_are_not_caller_mintable() -> None:
    with pytest.raises(subject.ConstructionK7RecoveryEligibleWorldModelLoopV1Error):
        subject.RecoveryEligibleGroundTransactionV1(
            object(), object(), object(), object(), object(), ()
        )
    with pytest.raises(subject.ConstructionK7RecoveryEligibleWorldModelLoopV1Error):
        subject.RecoveryEligibleWorldModelLoopV1(
            object(), object(), object(), object(), (), object(), object()
        )
