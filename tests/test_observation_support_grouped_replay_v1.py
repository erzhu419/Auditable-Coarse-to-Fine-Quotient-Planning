from __future__ import annotations

import hashlib

import pytest

import acfqp.observation_support_graph_acquisition_v1 as acquisition
import acfqp.observation_support_grouped_replay_v1 as grouped
import acfqp.observation_support_h2_closure_v1 as h2_closure
import acfqp.partial_support_confidence_v1 as confidence
import acfqp.transition_tuple_observer_v1 as observer


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def stream_rows() -> tuple[
    observer.PublicGraphContextV1,
    observer.LegalActionCatalogueV1,
    dict[
        tuple[int, int, int],
        tuple[acquisition.GraphPartialSupportRowV1, ...],
    ],
]:
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    catalogue = observer.legal_action_catalogue_v1(
        context,
        observer.root_state_v1(context),
        2,
    )
    rows: dict[
        tuple[int, int, int],
        tuple[acquisition.GraphPartialSupportRowV1, ...],
    ] = {}
    for action in catalogue.actions[:2]:
        prefix = acquisition.open_graph_partial_support_prefix_v1(
            context,
            catalogue,
            action,
        )
        rows[action] = tuple(
            prefix.extend_validation_to(checkpoint)
            for checkpoint in (2_048, 4_096, 8_192)
        )
    return context, catalogue, rows


def _requests(
    context: observer.PublicGraphContextV1,
    catalogue: observer.LegalActionCatalogueV1,
    rows: tuple[acquisition.GraphPartialSupportRowV1, ...],
) -> tuple[grouped.GroupedRowReplayRequestV1, ...]:
    return tuple(
        grouped.GroupedRowReplayRequestV1(context, catalogue, row)
        for row in rows
    )


def test_grouped_serial_replay_preserves_every_legacy_row_identity(
    stream_rows: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        dict[
            tuple[int, int, int],
            tuple[acquisition.GraphPartialSupportRowV1, ...],
        ],
    ],
) -> None:
    context, catalogue, rows_by_action = stream_rows
    rows = rows_by_action[catalogue.actions[0]]
    legacy = {
        row.partial_row_id:
        acquisition.verify_graph_partial_support_row_v1(
            context,
            catalogue,
            row.binding.action,
            row,
        )
        for row in rows
    }
    replay = grouped.grouped_verify_graph_partial_support_rows_v1(
        _requests(context, catalogue, rows),
        max_workers=1,
    )
    assert replay.verification_by_partial_row_id == legacy
    assert {
        row_id: item.to_document()
        for row_id, item in replay.verification_by_partial_row_id.items()
    } == {
        row_id: item.to_document()
        for row_id, item in legacy.items()
    }
    assert {
        row_id: item.verification_id
        for row_id, item in replay.verification_by_partial_row_id.items()
    } == {
        row_id: item.verification_id
        for row_id, item in legacy.items()
    }
    assert replay.requested_row_count == 3
    assert replay.physical_stream_group_count == 1
    assert replay.logical_replay_observer_draws == sum(
        row.counters.total_observer_draws for row in rows
    )
    assert replay.physical_replay_observer_draws == (
        rows[-1].counters.total_observer_draws
    )
    assert replay.saved_replay_observer_draws > 0
    assert not replay.persistent_cache_used


def test_parallel_group_replay_is_identical_to_serial_group_replay(
    stream_rows: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        dict[
            tuple[int, int, int],
            tuple[acquisition.GraphPartialSupportRowV1, ...],
        ],
    ],
) -> None:
    context, catalogue, rows_by_action = stream_rows
    rows = tuple(
        row
        for action in catalogue.actions[:2]
        for row in rows_by_action[action][:2]
    )
    requests = _requests(context, catalogue, rows)
    serial = grouped.grouped_verify_graph_partial_support_rows_v1(
        requests,
        max_workers=1,
    )
    parallel = grouped.grouped_verify_graph_partial_support_rows_v1(
        requests,
        max_workers=2,
    )
    assert parallel == serial
    assert parallel.to_document() == serial.to_document()
    assert parallel.result_id == serial.result_id
    assert parallel.physical_stream_group_count == 2
    assert parallel.incremental_epoch1_group_count == 2
    assert parallel.requested_row_count == len(rows)


@pytest.mark.parametrize(
    ("row_index", "sample_index"),
    (
        (0, 0),
        (1, 3_000),
        (2, 8_191),
    ),
    ids=("early-prefix", "middle-prefix", "final-sample"),
)
def test_early_middle_and_final_sample_tampering_fail_closed(
    stream_rows: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        dict[
            tuple[int, int, int],
            tuple[acquisition.GraphPartialSupportRowV1, ...],
        ],
    ],
    row_index: int,
    sample_index: int,
) -> None:
    context, catalogue, rows_by_action = stream_rows
    rows = list(rows_by_action[catalogue.actions[0]])
    claimed = rows[row_index]
    sample_ids = list(claimed.current_validation_observation_ids)
    sample_ids[sample_index] = _id(
        f"grouped replay tamper {row_index} {sample_index}"
    )
    object.__setattr__(
        claimed,
        "current_validation_observation_ids",
        tuple(sample_ids),
    )
    try:
        with pytest.raises(
            grouped.ObservationSupportGroupedReplayInvariantViolation
        ):
            grouped.grouped_verify_graph_partial_support_rows_v1(
                _requests(context, catalogue, tuple(rows)),
                max_workers=1,
            )
    finally:
        object.__setattr__(
            claimed,
            "current_validation_observation_ids",
            tuple(
                rows_by_action[catalogue.actions[0]][row_index]
                .confidence_authority.validation_evidence.sample_ids
            ),
        )


def test_epoch_two_row_remains_exact_full_legacy_singleton(
    stream_rows: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        dict[
            tuple[int, int, int],
            tuple[acquisition.GraphPartialSupportRowV1, ...],
        ],
    ],
) -> None:
    context, catalogue, rows_by_action = stream_rows
    parent = rows_by_action[catalogue.actions[0]][0]
    assert parent.novel_descriptors
    promoted = acquisition.promote_graph_partial_support_row_v1(
        parent,
        context,
        catalogue,
        parent.binding.action,
        2_048,
    )
    legacy = acquisition.verify_graph_partial_support_row_v1(
        context,
        catalogue,
        promoted.binding.action,
        promoted,
    )
    replay = grouped.grouped_verify_graph_partial_support_rows_v1(
        _requests(context, catalogue, (promoted,)),
        max_workers=2,
    )
    assert replay.verification_by_partial_row_id[
        promoted.partial_row_id
    ] == legacy
    assert replay.incremental_epoch1_group_count == 0
    assert replay.legacy_singleton_group_count == 1
    assert replay.saved_replay_observer_draws == 0


def test_grouped_rows_reconstruct_exact_legacy_h2_closure_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    closure = h2_closure.acquire_observation_support_h2_closure_v1(
        context,
        2_048,
        max_workers=8,
    )
    verification_by_id = {}
    for row in closure.all_rows:
        confidence_verification = (
            confidence.verify_partial_support_confidence_v1(
                row.confidence_authority
            )
        )
        verification_by_id[row.partial_row_id] = (
            acquisition.GraphPartialSupportReplayVerificationV1(
                row.partial_row_id,
                row.physical_evidence_id,
                confidence_verification.verification_id,
                row.support_epoch_index,
                row.counters.total_observer_draws,
                row.counters.total_random_word_calls,
                row.counters.total_rejections,
            )
        )

    def replay_without_resampling(
        _context: observer.PublicGraphContextV1,
        _catalogue: observer.LegalActionCatalogueV1,
        _action: tuple[int, int, int],
        row: acquisition.GraphPartialSupportRowV1,
    ) -> acquisition.GraphPartialSupportReplayVerificationV1:
        return verification_by_id[row.partial_row_id]

    monkeypatch.setattr(
        acquisition,
        "verify_graph_partial_support_row_v1",
        replay_without_resampling,
    )
    legacy = h2_closure.verify_observation_support_h2_closure_v1(
        context,
        closure,
        max_workers=1,
    )
    reconstructed = (
        grouped
        .verify_observation_support_h2_closure_from_grouped_rows_v1(
            context,
            closure,
            verification_by_id,
        )
    )
    assert reconstructed == legacy
    assert reconstructed.to_document() == legacy.to_document()
    assert reconstructed.verification_id == legacy.verification_id
