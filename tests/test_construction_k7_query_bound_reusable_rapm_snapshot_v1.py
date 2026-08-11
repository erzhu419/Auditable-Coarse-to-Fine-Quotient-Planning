from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_query_bound_reusable_rapm_snapshot_v1 as subject
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)
from tests.test_construction_k7_query_bound_final_local_replanning_v1 import (
    real_final_local_replanning,
)
from tests.test_construction_k7_query_bound_ground_transaction_v1 import (
    real_query_bound_ground_transaction,
)
from tests.test_construction_k7_query_bound_overlay_replanning_v1 import (
    real_overlay_replanning,
)
from tests.test_construction_k7_query_bound_second_ground_transaction_v1 import (
    real_second_ground_transaction,
)
from tests.test_construction_k7_query_bound_second_recovery_request_v1 import (
    real_second_request,
)


def _fresh_id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_domains_and_public_surface_are_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(subject.LOCAL_DOMAINS) == 3
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundReusableRAPMSnapshotV1Error",
        "LOCAL_DOMAINS",
        "QueryBoundReusableRAPMQueryResultV1",
        "QueryBoundReusableRAPMQuerySpecV1",
        "QueryBoundReusableRAPMSnapshotV1",
        "freeze_query_bound_reusable_rapm_query_spec_v1",
        "freeze_query_bound_reusable_rapm_snapshot_v1",
        "replay_query_bound_reusable_rapm_snapshot_bytes_v1",
        "require_query_bound_reusable_rapm_snapshot_v1",
        "run_query_bound_reusable_rapm_query_v1",
        "verify_query_bound_reusable_rapm_query_result_bytes_v1",
    }


@pytest.fixture(scope="module")
def real_reusable_snapshot(real_final_local_replanning):
    _transaction, final_local = real_final_local_replanning
    snapshot = subject.freeze_query_bound_reusable_rapm_snapshot_v1(
        final_local
    )
    return final_local, snapshot


def test_real_final_local_model_becomes_portable_query_neutral_snapshot(
    real_reusable_snapshot,
) -> None:
    final_local, snapshot = real_reusable_snapshot
    raw = canonical_json_bytes(snapshot.to_document())
    replayed = subject.replay_query_bound_reusable_rapm_snapshot_bytes_v1(raw)
    document = replayed.to_document()
    assert replayed.snapshot_id == snapshot.snapshot_id
    assert replayed.reusable_model == final_local.successor_model
    assert replayed.reusable_proof.canonical_bytes == (
        final_local.successor_proof.canonical_bytes
    )
    assert document["query_neutral_numerical_model_present"] is True
    assert document["portable_exact_replanning_proof_present"] is True
    assert document["source_occurrence_bundle_binding_present"] is False
    assert document["portable_source_ground_transaction_replay_present"] is False
    assert document["fresh_query_ground_access_authority_present"] is False
    assert document["persistent_proof_dependency_dag_present"] is False
    assert document["changed_row_count"] == 6
    assert document["preserved_row_count"] == 12
    assert document["reusable_row_count"] == 18
    assert document["cumulative_local_ground_draw_count"] == 25_344


def test_fresh_occurrence_replans_entirely_from_reused_snapshot(
    real_reusable_snapshot,
) -> None:
    _final_local, snapshot = real_reusable_snapshot
    query = subject.freeze_query_bound_reusable_rapm_query_spec_v1(
        snapshot=snapshot,
        logical_occurrence_id=_fresh_id("fresh-reusable-rapm-occurrence"),
        query_ordinal=2,
    )
    snapshot_bytes = canonical_json_bytes(snapshot.to_document())
    result = subject.run_query_bound_reusable_rapm_query_v1(
        snapshot_bytes=snapshot_bytes,
        query=query,
    )
    result_bytes = canonical_json_bytes(result.to_document())
    replayed = subject.verify_query_bound_reusable_rapm_query_result_bytes_v1(
        snapshot_bytes=snapshot_bytes,
        result_bytes=result_bytes,
    )
    document = replayed.to_document()
    assert replayed.query.logical_occurrence_id != snapshot.source_logical_occurrence_id
    assert replayed.proof.canonical_bytes == snapshot.reusable_proof.canonical_bytes
    assert document["snapshot_model_reused"] is True
    assert document["model_construction_repeated"] is False
    assert document["new_ground_access_count"] == 0
    assert document["ground_input_parameter_present"] is False
    assert document["observer_or_signer_input_present"] is False
    assert document["exact_abstract_replanning_completed"] is True
    assert document["certificate_failed_frontier_present"] is True
    assert document["query_local_ground_recovery_authorized_here"] is False
    assert document["plan_certificate_issued"] is False
    assert document["next_required_action"] == (
        "QUERY_LOCAL_CERTIFICATE_FRONTIER_RESOLUTION"
    )


def test_snapshot_and_query_replay_reject_resigned_semantic_changes(
    real_reusable_snapshot,
) -> None:
    _final_local, snapshot = real_reusable_snapshot
    document = snapshot.to_document()
    document["fresh_query_ground_access_authority_present"] = True
    payload = dict(document)
    payload.pop("reusable_model")
    payload.pop("reusable_proof")
    payload.pop("query_bound_reusable_rapm_snapshot_id")
    document["query_bound_reusable_rapm_snapshot_id"] = content_id(
        subject.SNAPSHOT_DOMAIN,
        payload,
    )
    with pytest.raises(
        subject.ConstructionK7QueryBoundReusableRAPMSnapshotV1Error
    ):
        subject.replay_query_bound_reusable_rapm_snapshot_bytes_v1(
            canonical_json_bytes(document)
        )

    query = subject.freeze_query_bound_reusable_rapm_query_spec_v1(
        snapshot=snapshot,
        logical_occurrence_id=_fresh_id("fresh-query-mutation"),
        query_ordinal=3,
    )
    result = subject.run_query_bound_reusable_rapm_query_v1(
        snapshot_bytes=canonical_json_bytes(snapshot.to_document()),
        query=query,
    )
    result_document = result.to_document()
    result_document["new_ground_access_count"] = 1
    result_payload = dict(result_document)
    result_payload.pop("query")
    result_payload.pop("numerical_proof")
    result_payload.pop("query_bound_reusable_rapm_query_result_id")
    result_document["query_bound_reusable_rapm_query_result_id"] = content_id(
        subject.QUERY_RESULT_DOMAIN,
        result_payload,
    )
    with pytest.raises(
        subject.ConstructionK7QueryBoundReusableRAPMSnapshotV1Error
    ):
        subject.verify_query_bound_reusable_rapm_query_result_bytes_v1(
            snapshot_bytes=canonical_json_bytes(snapshot.to_document()),
            result_bytes=canonical_json_bytes(result_document),
        )


def test_source_occurrence_cannot_be_relabelled_as_fresh(
    real_reusable_snapshot,
) -> None:
    _final_local, snapshot = real_reusable_snapshot
    with pytest.raises(
        subject.ConstructionK7QueryBoundReusableRAPMSnapshotV1Error
    ):
        subject.freeze_query_bound_reusable_rapm_query_spec_v1(
            snapshot=snapshot,
            logical_occurrence_id=snapshot.source_logical_occurrence_id,
            query_ordinal=1,
        )


def test_snapshot_is_not_caller_mintable() -> None:
    with pytest.raises(
        subject.ConstructionK7QueryBoundReusableRAPMSnapshotV1Error
    ):
        subject.QueryBoundReusableRAPMSnapshotV1(
            object(),
            *("0" * 64 for _ in range(10)),
            object(),
            object(),
            (),
            (),
            1,
            1,
            2,
            1,
        )


def test_canonical_loader_rejects_unknown_snapshot_field(
    real_reusable_snapshot,
) -> None:
    _final_local, snapshot = real_reusable_snapshot
    document = loads_canonical_json(canonical_json_bytes(snapshot.to_document()))
    document["unknown"] = True
    with pytest.raises(
        subject.ConstructionK7QueryBoundReusableRAPMSnapshotV1Error
    ):
        subject.replay_query_bound_reusable_rapm_snapshot_bytes_v1(
            canonical_json_bytes(document)
        )
