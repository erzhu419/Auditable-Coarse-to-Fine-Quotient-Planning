from __future__ import annotations

from dataclasses import fields
import hashlib

import pytest

from acfqp import v075_batched_observer_authority_v2 as batched_v2
from acfqp import v075_live_batch_prefix_authority_v2 as prefix_v2
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_private_observer_boundary_v2 as observer_fixture
from tests import (
    test_v075_schedule_bound_acquisition_lifecycle_v2 as lifecycle_fixture,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-live-prefix-test:v2"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _clone(value):
    forged = object.__new__(type(value))
    for item in fields(type(value)):
        if hasattr(value, item.name):
            object.__setattr__(forged, item.name, getattr(value, item.name))
    return forged


def _open(values, marker):
    namespace = values["namespace"]
    occurrence = lifecycle_fixture._occurrence(  # noqa: SLF001
        namespace,
        worker.V075WorkerArmV1.NO_PRIOR,
    )
    context = namespace.family.replicate_contexts[0]
    catalogue = graph.root_catalogue_v1(context)
    rows = tuple(
        graph.observation_row_binding_v1(context, catalogue, action)
        for action in catalogue.actions
    )
    streams = tuple(
        lifecycle_fixture._discovery_stream(  # noqa: SLF001
            namespace,
            row,
            worker.V075WorkerArmV1.NO_PRIOR,
        )
        for row in rows
    )
    adapter = lifecycle_fixture._open_adapter(  # noqa: SLF001
        values,
        occurrence,
        marker,
    )
    return occurrence, streams, adapter


@pytest.fixture(scope="module")
def exact_graph():
    generated, salt, namespace, authorization, signer = (
        observer_fixture._fixture("live-batch-prefix")
    )
    return {
        "generated": generated,
        "salt": salt,
        "namespace": namespace,
        "authorization": authorization,
        "signer": signer,
    }


def _append_discovery(adapter, stream):
    return adapter.observe_batch_v2(
        stream_identity=stream,
        accepted_draw_start=1,
        accepted_draw_count=64,
        accepted_draw_cap=64,
    )


def _close_lineage(values, occurrence, streams, adapter):
    closure = adapter.close_v2()
    return batched_v2.freeze_v075_construction_batch_occurrence_lineage_v2(
        occurrence_identity=occurrence,
        closure=closure,
        authority=values["authorization"],
        namespace=values["namespace"],
        known_stream_identities=streams,
        private_salt=values["salt"],
        private_environment=values["generated"].secret_laws_for_commitment(),
    )


def test_contract_and_production_flags_remain_locked():
    assert prefix_v2.PROPOSED_CONTRACT_VERSION == "1.52.0"
    assert prefix_v2.OFFICIAL_EXECUTION_ALLOWED is False
    assert prefix_v2.PRODUCTION_AUTHORIZING is False
    assert prefix_v2.PER_DRAW_REPLAY_ALLOWED is False
    assert prefix_v2.PRIVATE_LAW_ACCESS_ALLOWED is False
    assert prefix_v2.PLAN_CERTIFICATE_ISSUANCE_ALLOWED is False
    assert prefix_v2.INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED is False


def test_open_session_checkpoints_form_one_strict_signed_prefix_chain(
    exact_graph,
):
    occurrence, streams, adapter = _open(exact_graph, "valid-prefix-chain")
    _append_discovery(adapter, streams[0])
    first = prefix_v2.freeze_v075_live_batch_prefix_checkpoint_v2(
        adapter=adapter
    )
    _append_discovery(adapter, streams[1])
    second = prefix_v2.freeze_v075_live_batch_prefix_checkpoint_v2(
        adapter=adapter,
        parent=first,
    )

    assert first.checkpoint_index == 1
    assert first.parent_checkpoint_id is None
    assert len(first.batch_ids) == 1
    assert second.checkpoint_index == 2
    assert second.parent_checkpoint_id == first.checkpoint_id
    assert second.parent_batch_count == 1
    assert second.batch_ids[:1] == first.batch_ids
    assert second.appended_batch_ids == second.batch_ids[1:]
    assert second.to_document()["per_draw_records_read"] == 0
    assert second.to_document()["private_law_access"] is False
    assert second.to_document()["plan_certificate"] is False
    assert second.to_document()["production_causality_proven"] is False
    replayed_second = (
        prefix_v2.verify_v075_live_batch_prefix_checkpoint_bytes_v2(
            scope=second.scope,
            occurrence_identity=occurrence,
            batches=adapter.batches,
            parent=first,
            claimed_bytes=second.canonical_bytes,
        )
    )
    assert replayed_second.checkpoint_id == second.checkpoint_id
    with pytest.raises(prefix_v2.V075LiveBatchPrefixV2InvariantViolation):
        prefix_v2.verify_v075_live_batch_prefix_checkpoint_bytes_v2(
            scope=second.scope,
            occurrence_identity=occurrence,
            batches=adapter.batches,
            parent=first,
            claimed_bytes=second.canonical_bytes + b" ",
        )

    lineage = _close_lineage(
        exact_graph,
        occurrence,
        streams,
        adapter,
    )
    reconciliation = prefix_v2.reconcile_v075_live_batch_prefix_chain_v2(
        final_lineage=lineage,
        checkpoints=(first, second),
    )
    assert reconciliation.lineage_id == lineage.lineage_id
    assert reconciliation.checkpoint_ids == (
        first.checkpoint_id,
        second.checkpoint_id,
    )
    assert reconciliation.final_batch_count == 2
    assert reconciliation.final_accepted_draw_count == 128
    assert reconciliation.to_document()["last_checkpoint_equals_final_lineage"]
    assert (
        reconciliation.to_document()["intent_bound_append_causality_proven"]
        is False
    )


def test_same_prefix_and_cross_session_parent_are_rejected(exact_graph):
    occurrence, streams, adapter = _open(exact_graph, "parent-a")
    _append_discovery(adapter, streams[0])
    first = prefix_v2.freeze_v075_live_batch_prefix_checkpoint_v2(
        adapter=adapter
    )
    with pytest.raises(prefix_v2.V075LiveBatchPrefixV2InvariantViolation):
        prefix_v2.freeze_v075_live_batch_prefix_checkpoint_v2(
            adapter=adapter,
            parent=first,
        )
    adapter._closed = False  # noqa: SLF001 - simulate stale adapter flag
    with pytest.raises(prefix_v2.V075LiveBatchPrefixV2InvariantViolation):
        prefix_v2.freeze_v075_live_batch_prefix_checkpoint_v2(
            adapter=adapter,
            parent=first,
        )

    _other_occurrence, other_streams, other = _open(exact_graph, "parent-b")
    _append_discovery(other, other_streams[0])
    with pytest.raises(prefix_v2.V075LiveBatchPrefixV2InvariantViolation):
        prefix_v2.freeze_v075_live_batch_prefix_checkpoint_v2(
            adapter=other,
            parent=first,
        )
    adapter.close_v2()
    other.close_v2()


def test_checkpoint_after_close_and_incomplete_final_chain_are_rejected(
    exact_graph,
):
    occurrence, streams, adapter = _open(exact_graph, "closed-prefix")
    _append_discovery(adapter, streams[0])
    first = prefix_v2.freeze_v075_live_batch_prefix_checkpoint_v2(
        adapter=adapter
    )
    _append_discovery(adapter, streams[1])
    lineage = _close_lineage(
        exact_graph,
        occurrence,
        streams,
        adapter,
    )
    with pytest.raises(prefix_v2.V075LiveBatchPrefixV2InvariantViolation):
        prefix_v2.freeze_v075_live_batch_prefix_checkpoint_v2(
            adapter=adapter,
            parent=first,
        )
    with pytest.raises(prefix_v2.V075LiveBatchPrefixV2InvariantViolation):
        prefix_v2.reconcile_v075_live_batch_prefix_chain_v2(
            final_lineage=lineage,
            checkpoints=(first,),
        )


def test_mutated_checkpoint_digest_or_parent_chain_fails_final_replay(
    exact_graph,
):
    occurrence, streams, adapter = _open(exact_graph, "mutated-prefix")
    _append_discovery(adapter, streams[0])
    first = prefix_v2.freeze_v075_live_batch_prefix_checkpoint_v2(
        adapter=adapter
    )
    _append_discovery(adapter, streams[1])
    second = prefix_v2.freeze_v075_live_batch_prefix_checkpoint_v2(
        adapter=adapter,
        parent=first,
    )
    lineage = _close_lineage(
        exact_graph,
        occurrence,
        streams,
        adapter,
    )
    forged = _clone(second)
    object.__setattr__(forged, "_checkpoint_id", _id("foreign-checkpoint"))
    with pytest.raises(prefix_v2.V075LiveBatchPrefixV2InvariantViolation):
        prefix_v2.reconcile_v075_live_batch_prefix_chain_v2(
            final_lineage=lineage,
            checkpoints=(first, forged),
        )
    with pytest.raises(prefix_v2.V075LiveBatchPrefixV2InvariantViolation):
        prefix_v2.reconcile_v075_live_batch_prefix_chain_v2(
            final_lineage=lineage,
            checkpoints=(second,),
        )


def test_production_entry_is_unconditionally_not_ready(monkeypatch):
    monkeypatch.setattr(prefix_v2, "OFFICIAL_EXECUTION_ALLOWED", True)
    monkeypatch.setattr(prefix_v2, "PRODUCTION_AUTHORIZING", True)
    with pytest.raises(prefix_v2.V075LiveBatchPrefixProductionV2NotReady):
        prefix_v2.open_v075_production_live_batch_prefix_authority_v2()
