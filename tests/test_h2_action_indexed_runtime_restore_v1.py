from __future__ import annotations

from dataclasses import fields, replace
from fractions import Fraction
from typing import Any

import pytest

from acfqp.h2_action_indexed_proof_dag_v1 import (
    ActionIndexedEpochExecutionV1,
    ActionIndexedH2QueryV1,
    ActionIndexedProofInvariantViolation,
    ActionIndexedProofRuntimeV1,
    CandidateAction,
    ProofAddress,
    authorize_action_indexed_final_epoch_v1,
    derive_action_indexed_delta_and_invalidation_v1,
    derive_action_indexed_preexecution_invalidation_v1,
    execute_action_indexed_epoch_v1,
    registered_action_indexed_h2_query_v1,
    registered_final_action_indexed_h2_model_v1,
    registered_first_action_indexed_h2_model_v1,
    restore_verified_action_indexed_first_runtime_v1,
)


EXPECTED_FIRST_EXECUTION_ID = (
    "cf36bf88a5cc41e3962e3b51bc87ba39eadb61827aabd909844934717eb51975"
)
EXPECTED_FINAL_EXECUTION_ID = (
    "5d65fd780ca38a9e6c21314156eee9f94b9777566ec42737762e5ecec2cdd240"
)


def _canonical_first():
    model = registered_first_action_indexed_h2_model_v1()
    query = registered_action_indexed_h2_query_v1()
    execution = execute_action_indexed_epoch_v1(
        model,
        query,
        ActionIndexedProofRuntimeV1(),
    )
    return model, query, execution


def _canonical_final(
    first_model,
    query,
    first_execution,
    runtime: ActionIndexedProofRuntimeV1,
):
    final_model = registered_final_action_indexed_h2_model_v1()
    delta, preexecution = derive_action_indexed_preexecution_invalidation_v1(
        first_model,
        final_model,
        first_execution,
    )
    authorize_action_indexed_final_epoch_v1(runtime, preexecution)
    final_execution = execute_action_indexed_epoch_v1(
        final_model,
        query,
        runtime,
    )
    verified_delta, invalidation = derive_action_indexed_delta_and_invalidation_v1(
        first_model,
        final_model,
        first_execution,
        final_execution,
    )
    assert verified_delta.to_document() == delta.to_document()
    return final_model, final_execution, preexecution, invalidation


def _unsafe_exact_clone(instance: Any, **changes: Any) -> Any:
    """Make an exact-class negative-control object without running post-init."""

    clone = object.__new__(type(instance))
    for item in fields(instance):
        object.__setattr__(
            clone,
            item.name,
            changes.get(item.name, getattr(instance, item.name)),
        )
    return clone


def test_exact_first_restore_receipt_snapshot_and_final_continuation() -> None:
    first_model, query, first_execution = _canonical_first()
    empty_snapshot = ActionIndexedProofRuntimeV1().snapshot_id

    runtime, receipt = restore_verified_action_indexed_first_runtime_v1(
        first_model,
        query,
        first_execution,
    )

    assert first_execution.execution_id == EXPECTED_FIRST_EXECUTION_ID
    assert (first_execution.work.lower_computed, first_execution.work.lower_reused) == (
        18,
        0,
    )
    assert first_execution.work.fresh_root_computed == 3
    assert runtime.cache_size == 18
    assert receipt.model_id == first_model.model_id
    assert receipt.query_id == query.query_id
    assert receipt.execution_id == first_execution.execution_id
    assert receipt.ordered_lower_node_ids == tuple(
        node.node_id for node in first_execution.nodes
    )
    assert receipt.pre_runtime_snapshot_id == empty_snapshot
    assert receipt.post_runtime_snapshot_id == runtime.snapshot_id
    assert receipt.pre_runtime_snapshot_id != receipt.post_runtime_snapshot_id
    assert receipt.lower_entries_loaded == 18
    assert receipt.roots_loaded == 0
    assert receipt.semantic_replay_required is True
    assert len(receipt.restore_id) == 64

    _, final_execution, preexecution, invalidation = _canonical_final(
        first_model,
        query,
        first_execution,
        runtime,
    )

    assert final_execution.execution_id == EXPECTED_FINAL_EXECUTION_ID
    assert final_execution.preexecution_invalidation_id == preexecution.plan_id
    assert (final_execution.work.lower_computed, final_execution.work.lower_reused) == (
        10,
        8,
    )
    assert final_execution.work.fresh_root_computed == 3
    assert final_execution.proposal.selected_action is CandidateAction.M
    assert final_execution.audit(CandidateAction.M).certified is True
    assert tuple(item.address for item in final_execution.resolutions if item.outcome.value == "COMPUTED") == (
        ProofAddress.ROW_M,
        ProofAddress.Q_M,
        ProofAddress.U1,
        ProofAddress.U0,
        ProofAddress.PLAN_M,
        ProofAddress.REGRET_N,
        ProofAddress.REGRET_M,
        ProofAddress.RISK_M,
        ProofAddress.COVERAGE_M,
        ProofAddress.SELECTION,
    )
    assert invalidation.recomputed_addresses == tuple(
        item.address
        for item in final_execution.resolutions
        if item.outcome.value == "COMPUTED"
    )


def test_restore_rejects_final_execution_as_first() -> None:
    first_model, query, first_execution = _canonical_first()
    source_runtime, _ = restore_verified_action_indexed_first_runtime_v1(
        first_model,
        query,
        first_execution,
    )
    final_model, final_execution, _, _ = _canonical_final(
        first_model,
        query,
        first_execution,
        source_runtime,
    )

    with pytest.raises(ActionIndexedProofInvariantViolation):
        restore_verified_action_indexed_first_runtime_v1(
            first_model,
            query,
            final_execution,
        )
    with pytest.raises(ActionIndexedProofInvariantViolation):
        restore_verified_action_indexed_first_runtime_v1(
            final_model,
            query,
            final_execution,
        )


def test_restore_rejects_tampered_node_and_resigned_execution() -> None:
    first_model, query, first_execution = _canonical_first()

    tampered_row = replace(
        first_execution.nodes[0],
        input_slice_id=first_execution.nodes[1].input_slice_id,
    )
    tampered_execution = _unsafe_exact_clone(
        first_execution,
        nodes=(tampered_row, *first_execution.nodes[1:]),
    )
    with pytest.raises(ActionIndexedProofInvariantViolation):
        restore_verified_action_indexed_first_runtime_v1(
            first_model,
            query,
            tampered_execution,
        )

    resigned_execution = replace(
        first_execution,
        pre_runtime_snapshot_id="0" * 64,
    )
    assert resigned_execution.execution_id != first_execution.execution_id
    with pytest.raises(ActionIndexedProofInvariantViolation):
        restore_verified_action_indexed_first_runtime_v1(
            first_model,
            query,
            resigned_execution,
        )


def test_restore_rejects_wrong_model_and_query_copies() -> None:
    first_model, query, first_execution = _canonical_first()

    with pytest.raises(ActionIndexedProofInvariantViolation):
        restore_verified_action_indexed_first_runtime_v1(
            registered_final_action_indexed_h2_model_v1(),
            query,
            first_execution,
        )

    wrong_query = _unsafe_exact_clone(
        query,
        risk_tolerance=Fraction(1),
    )
    assert type(wrong_query) is ActionIndexedH2QueryV1
    with pytest.raises(ActionIndexedProofInvariantViolation):
        restore_verified_action_indexed_first_runtime_v1(
            first_model,
            wrong_query,
            first_execution,
        )

    wrong_embedded_query = _unsafe_exact_clone(
        first_execution,
        semantic_query=wrong_query,
    )
    assert type(wrong_embedded_query) is ActionIndexedEpochExecutionV1
    with pytest.raises(ActionIndexedProofInvariantViolation):
        restore_verified_action_indexed_first_runtime_v1(
            first_model,
            query,
            wrong_embedded_query,
        )
