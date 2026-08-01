from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect

import pytest

from acfqp import construction_shared_resource_global_supervisor_journal_v1 as journal_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, content_id


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:global-supervisor-journal-test:v1\x00" + label.encode("utf-8")
    ).hexdigest()


def _scope(label: str = "base") -> journal_v1.GlobalSupervisorScopeV1:
    return journal_v1.GlobalSupervisorScopeV1(
        measurement_identity_binding_id=_id(f"{label}-measurement"),
        execution_profile_id=_id(f"{label}-execution"),
        window_key=f"test.{label}.window",
        supervision_scope_key=f"test.{label}.supervisor",
    )


def _sources(
    scope: journal_v1.GlobalSupervisorScopeV1 | None = None,
) -> tuple[
    journal_v1.WindowStartSourceDocumentV1,
    journal_v1.BusinessCutoffSourceDocumentV1,
    journal_v1.ProcessReapSourceDocumentV1,
    journal_v1.DescendantScanSourceDocumentV1,
    journal_v1.FinalCgroupPeakSourceDocumentV1,
    journal_v1.ParentTerminalSourceDocumentV1,
]:
    scope = scope or _scope()
    return (
        journal_v1.WindowStartSourceDocumentV1(
            scope,
            "monitor.registration.root",
        ),
        journal_v1.BusinessCutoffSourceDocumentV1(
            scope,
            journal_v1.BusinessCutoffClaimV1.BUSINESS_PAYLOAD_COMPLETE,
            "business.frame.root",
            True,
        ),
        journal_v1.ProcessReapSourceDocumentV1(
            scope,
            "process.handle.child",
            0,
            True,
        ),
        journal_v1.DescendantScanSourceDocumentV1(
            scope,
            "process.handle.child",
            0,
            True,
        ),
        journal_v1.FinalCgroupPeakSourceDocumentV1(
            scope,
            "cgroup.scope.child",
            4096,
            True,
        ),
        journal_v1.ParentTerminalSourceDocumentV1(
            scope,
            journal_v1.ParentTerminalClaimV1.COMPLETED,
            "STRUCTURAL_TERMINAL",
            True,
        ),
    )


def _complete_journal() -> journal_v1.FrozenGlobalSupervisorEventJournalV1:
    sources = _sources()
    session = journal_v1.open_global_supervisor_event_journal_v1(sources[0])
    for source in sources[1:]:
        session.append(source)
    return session.freeze()


def test_complete_journal_assigns_one_contiguous_global_sequence() -> None:
    frozen = _complete_journal()

    assert tuple(event.sequence for event in frozen.events) == (1, 2, 3, 4, 5, 6)
    assert tuple(event.kind for event in frozen.events) == journal_v1.EVENT_ORDER
    assert frozen.events[0].prior_event_id is None
    assert all(
        event.prior_event_id == frozen.events[index - 1].event_id
        for index, event in enumerate(frozen.events[1:], start=1)
    )

    document = frozen.to_document()
    assert document["event_count"] == 6
    assert document["global_sequence_origin"] == 1
    assert document["global_sequence_contiguous"] is True
    assert document["typed_source_documents_embedded"] is True
    assert document["opaque_source_ids_accepted_without_documents"] is False
    for event_document in document["events"]:
        assert event_document["source_document"]["source_document_id"] == (
            event_document["source_document_id"]
        )
        assert event_document["sequence_assigned_internally"] is True
        assert event_document["caller_sequence_accepted"] is False


def test_strict_state_machine_rejects_skip_repeat_and_post_terminal_append() -> None:
    sources = _sources()
    session = journal_v1.open_global_supervisor_event_journal_v1(sources[0])

    with pytest.raises(
        journal_v1.ConstructionSharedResourceGlobalSupervisorJournalV1Error,
        match="BUSINESS_CUTOFF",
    ):
        session.append(sources[2])

    session.append(sources[1])
    with pytest.raises(
        journal_v1.ConstructionSharedResourceGlobalSupervisorJournalV1Error,
        match="PROCESS_REAP",
    ):
        session.append(sources[1])

    for source in sources[2:]:
        session.append(source)
    with pytest.raises(
        journal_v1.ConstructionSharedResourceGlobalSupervisorJournalV1Error,
        match="parent terminal",
    ):
        session.append(sources[-1])

    session.freeze()
    with pytest.raises(
        journal_v1.ConstructionSharedResourceGlobalSupervisorJournalV1Error,
        match="freeze",
    ):
        session.append(sources[-1])


def test_incomplete_journal_cannot_freeze() -> None:
    sources = _sources()
    session = journal_v1.open_global_supervisor_event_journal_v1(sources[0])
    session.append(sources[1])

    with pytest.raises(
        journal_v1.ConstructionSharedResourceGlobalSupervisorJournalV1Error,
        match="before PARENT_TERMINAL",
    ):
        session.freeze()


def test_sequences_are_not_a_caller_input_and_events_are_private_issued() -> None:
    append_parameters = inspect.signature(
        journal_v1.GlobalSupervisorEventJournalSessionV1.append
    ).parameters
    open_parameters = inspect.signature(
        journal_v1.open_global_supervisor_event_journal_v1
    ).parameters
    assert "sequence" not in append_parameters
    assert "sequence" not in open_parameters

    sources = _sources()
    session = journal_v1.open_global_supervisor_event_journal_v1(sources[0])
    with pytest.raises(TypeError):
        session.append(sources[1], sequence=2)  # type: ignore[call-arg]

    with pytest.raises(
        journal_v1.ConstructionSharedResourceGlobalSupervisorJournalV1Error,
        match="journal-issued",
    ):
        journal_v1.GlobalSupervisorEventV1(
            object(),
            sources[0].scope.scope_id,
            1,
            journal_v1.GlobalSupervisorEventKindV1.WINDOW_START,
            None,
            sources[0],
        )

    frozen = _complete_journal()
    with pytest.raises(
        journal_v1.ConstructionSharedResourceGlobalSupervisorJournalV1Error,
        match="issuer-owned",
    ):
        replace(frozen, _issuer=object())


def test_opaque_source_id_and_wrong_typed_document_are_rejected() -> None:
    sources = _sources()
    session = journal_v1.open_global_supervisor_event_journal_v1(sources[0])

    with pytest.raises(
        journal_v1.ConstructionSharedResourceGlobalSupervisorJournalV1Error,
        match="typed source",
    ):
        session.append(sources[1].source_document_id)  # type: ignore[arg-type]

    with pytest.raises(
        journal_v1.ConstructionSharedResourceGlobalSupervisorJournalV1Error,
        match="WINDOW_START",
    ):
        journal_v1.open_global_supervisor_event_journal_v1(  # type: ignore[arg-type]
            sources[1]
        )


def test_cross_scope_and_cross_process_handle_are_rejected() -> None:
    sources = _sources()
    foreign_sources = _sources(_scope("foreign"))
    session = journal_v1.open_global_supervisor_event_journal_v1(sources[0])
    with pytest.raises(
        journal_v1.ConstructionSharedResourceGlobalSupervisorJournalV1Error,
        match="crossed the journal scope",
    ):
        session.append(foreign_sources[1])

    session.append(sources[1])
    session.append(sources[2])
    crossed_scan = replace(sources[3], process_handle_key="process.handle.other")
    with pytest.raises(
        journal_v1.ConstructionSharedResourceGlobalSupervisorJournalV1Error,
        match="crossed the reaped process handle",
    ):
        session.append(crossed_scan)


@pytest.mark.parametrize(
    ("constructor", "arguments", "message"),
    (
        (
            journal_v1.ProcessReapSourceDocumentV1,
            lambda scope: (scope, "process.handle.child", True, True),
            "wait status must be an exact integer",
        ),
        (
            journal_v1.DescendantScanSourceDocumentV1,
            lambda scope: (scope, "process.handle.child", True, True),
            "descendant count must be an exact integer",
        ),
        (
            journal_v1.FinalCgroupPeakSourceDocumentV1,
            lambda scope: (scope, "cgroup.scope.child", True, True),
            "working bytes peak must be an exact integer",
        ),
        (
            journal_v1.BusinessCutoffSourceDocumentV1,
            lambda scope: (
                scope,
                journal_v1.BusinessCutoffClaimV1.BUSINESS_PAYLOAD_COMPLETE,
                "business.frame.root",
                1,
            ),
            "cutoff_complete must be exact true",
        ),
    ),
)
def test_bool_integer_aliases_and_nonexact_flags_are_rejected(
    constructor: object,
    arguments: object,
    message: str,
) -> None:
    scope = _scope("typing")
    with pytest.raises(
        journal_v1.ConstructionSharedResourceGlobalSupervisorJournalV1Error,
        match=message,
    ):
        constructor(*arguments(scope))  # type: ignore[operator]


def test_descendant_scan_requires_zero_and_source_documents_are_immutable() -> None:
    scope = _scope("descendants")
    with pytest.raises(
        journal_v1.ConstructionSharedResourceGlobalSupervisorJournalV1Error,
        match="exactly zero",
    ):
        journal_v1.DescendantScanSourceDocumentV1(
            scope,
            "process.handle.child",
            1,
            True,
        )

    source = _sources(scope)[0]
    with pytest.raises(AttributeError):
        source.monitor_registration_key = "changed"  # type: ignore[misc]


def test_all_semantic_and_formal_locks_remain_false() -> None:
    frozen = _complete_journal()
    document = frozen.to_document()
    assert document["os_event_semantics_independently_replayed"] is False
    assert document["scope"]["route_identity_joined"] is False
    assert document["scope"]["supervisor_os_authority_bound"] is False

    lock_sets = [document["formal_locks"], document["scope"]["formal_locks"]]
    lock_sets.extend(event["formal_locks"] for event in document["events"])
    lock_sets.extend(
        event["source_document"]["formal_locks"]
        for event in document["events"]
    )
    assert all(
        value is False
        for locks in lock_sets
        for value in locks.values()
    )

    assert journal_v1.OS_SOURCE_PROVENANCE_VERIFIED is False
    assert journal_v1.GLOBAL_SEQUENCE_MAPPED_TO_OS_ORDER_VERIFIED is False
    assert journal_v1.COUNTER_RECORD_AUTHORIZED is False
    assert journal_v1.WORK_VECTOR_AUTHORIZED is False
    assert journal_v1.COMPARISON_VECTOR_AUTHORIZED is False
    assert journal_v1.ACTUAL_PROJECTION_PROOF_AUTHORIZED is False
    assert journal_v1.OFFICIAL_EXECUTION_ALLOWED is False


def test_scope_event_and_frozen_journal_mutation_fail_stale() -> None:
    frozen = _complete_journal()
    scope = frozen.scope
    original_window = scope.window_key
    object.__setattr__(scope, "window_key", "test.mutated.window")
    try:
        with pytest.raises(
            journal_v1.ConstructionSharedResourceGlobalSupervisorJournalV1Error,
            match="scope changed",
        ):
            frozen.to_document()
    finally:
        object.__setattr__(scope, "window_key", original_window)
    frozen.to_document()

    event = frozen.events[2]
    original_sequence = event.sequence
    object.__setattr__(event, "sequence", original_sequence + 10)
    try:
        with pytest.raises(
            journal_v1.ConstructionSharedResourceGlobalSupervisorJournalV1Error,
            match="event changed|sequence",
        ):
            frozen.to_document()
    finally:
        object.__setattr__(event, "sequence", original_sequence)
    frozen.to_document()

    original_events = frozen.events
    object.__setattr__(frozen, "events", tuple(reversed(original_events)))
    try:
        with pytest.raises(
            journal_v1.ConstructionSharedResourceGlobalSupervisorJournalV1Error,
            match="journal changed|event changed",
        ):
            frozen.to_document()
    finally:
        object.__setattr__(frozen, "events", original_events)
    frozen.to_document()


def test_content_domains_are_central_distinct_and_replayable() -> None:
    frozen = _complete_journal()
    assert len(journal_v1.REQUESTED_PHASE3E_DOMAIN_TAGS) == 4
    assert len(set(journal_v1.REQUESTED_PHASE3E_DOMAIN_TAGS)) == 4
    assert set(journal_v1.REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS

    source = frozen.events[0].source_document
    assert source.source_document_id == content_id(
        journal_v1.GLOBAL_SUPERVISOR_SOURCE_DOCUMENT_V1_DOMAIN,
        source._payload(),  # noqa: SLF001 - independent ID replay
    )
    assert frozen.events[0].event_id == content_id(
        journal_v1.GLOBAL_SUPERVISOR_EVENT_V1_DOMAIN,
        frozen.events[0]._payload(),  # noqa: SLF001 - independent ID replay
    )
    assert frozen.journal_id == content_id(
        journal_v1.GLOBAL_SUPERVISOR_EVENT_JOURNAL_V1_DOMAIN,
        frozen._payload(),  # noqa: SLF001 - independent ID replay
    )

    same_payload = {"schema": "same"}
    assert len(
        {
            content_id(domain, same_payload)
            for domain in journal_v1.REQUESTED_PHASE3E_DOMAIN_TAGS
        }
    ) == 4
