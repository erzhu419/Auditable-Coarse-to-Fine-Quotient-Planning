from __future__ import annotations

import inspect

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_resolution_v2 as resolution_v2
from acfqp import construction_shared_resource_transfer_mount_journal_v2 as v2
from acfqp.phase3e_ids import loads_canonical_json


def _cid(index: int) -> str:
    return f"{index:064x}"


def _purposes() -> tuple[v2.TransferMountPurposeRegistrationV2, ...]:
    return tuple(
        v2.freeze_transfer_mount_purpose_v2(
            path=path,
            purpose_key=key,
            payload_role="SEALED_PAYLOAD",
            source_role=source,
            target_role=target,
        )
        for path, key, source, target in (
            (
                v2.MOUNTED_PATH,
                "mount.worker",
                "BROKER",
                "WORKER",
            ),
            (v2.READ_PATH, "read.broker", "SEALED_INPUT", "BROKER"),
            (v2.STAGED_PATH, "stage.worker", "BROKER", "WORKER"),
        )
    )


def _session(offset: int = 0) -> v2.TransferMountJournalSessionV2:
    return v2.TransferMountJournalSessionV2(
        live_envelope_id=_cid(10 + offset),
        occurrence_id=_cid(11 + offset),
        route_attempt_id=_cid(12 + offset),
        decision_point_id=_cid(13 + offset),
        measurement_window_id=_cid(14 + offset),
        operational_cutoff_id=_cid(15 + offset),
        measurement_start_sequence=40,
        purposes=_purposes(),
    )


def _closed_bundle() -> v2.TransferMountRawEvidenceBundleV2:
    session = _session()
    payload = session.register_payload_v2(
        payload_role="SEALED_PAYLOAD", raw_bytes=b"abcdef"
    )
    session.record_read_v2(
        payload=payload,
        purpose_key="read.broker",
        byte_offset=0,
        returned_bytes=b"abc",
    )
    session.record_read_v2(
        payload=payload,
        purpose_key="read.broker",
        byte_offset=3,
        returned_bytes=b"def",
    )
    session.record_stage_v2(
        payload=payload, purpose_key="stage.worker"
    )
    session.record_stage_v2(
        payload=payload, purpose_key="stage.worker"
    )
    first = session.open_mount_visibility_v2(
        payload=payload, purpose_key="mount.worker"
    )
    second = session.open_mount_visibility_v2(
        payload=payload, purpose_key="mount.worker"
    )
    session.close_mount_visibility_v2(first)
    session.close_mount_visibility_v2(second)
    return session.close_v2()


def _raw_kwargs(
    bundle: v2.TransferMountRawEvidenceBundleV2,
) -> dict[str, bytes]:
    return {
        "cutoff_bytes": bundle.cutoff_component.raw_bytes,
        "read_journal_bytes": bundle.read_journal_component.raw_bytes,
        "read_charge_registry_bytes": (
            bundle.read_charge_registry_component.raw_bytes
        ),
        "staged_journal_bytes": bundle.staged_journal_component.raw_bytes,
        "staged_charge_registry_bytes": (
            bundle.staged_charge_registry_component.raw_bytes
        ),
        "mount_payload_registry_bytes": (
            bundle.mount_payload_registry_component.raw_bytes
        ),
        "mount_journal_bytes": bundle.mount_journal_component.raw_bytes,
    }


def _refreeze(document: dict[str, object], schema: str) -> bytes:
    id_field = v2._COMPONENT_ID_FIELD[schema]  # noqa: SLF001
    body = {
        key: value
        for key, value in document.items()
        if key
        not in {
            "schema",
            "schema_version",
            "profile_key",
            "raw_evidence_only",
            "semantic_source_verified",
            "counter_record_issued",
            "formal_value_authorized",
            id_field,
        }
    }
    _artifact_id, raw = v2._freeze_component_bytes(  # noqa: SLF001
        schema, body
    )
    return raw


def _document(raw: bytes) -> dict[str, object]:
    value = loads_canonical_json(raw)
    assert type(value) is dict
    return value


def test_exact_transfer_sums_and_unique_mounted_peak_are_replayed() -> None:
    bundle = _closed_bundle()
    replay = bundle.raw_replay
    assert replay.read_bytes_sum == 6
    # The identical six-byte payload was staged twice and must be charged
    # twice, not deduplicated like mounted capacity.
    assert replay.staged_bytes_sum == 12
    # Two simultaneous visibility intervals for the same payload identity
    # consume one unique six-byte mounted payload.
    assert replay.mounted_unique_payload_bytes_peak == 6
    assert replay.global_event_count == 8
    assert replay.semantic_source_verified is False
    assert replay.counter_record_issuance_authorized is False
    assert bundle.to_document()["counter_record_issued"] is False
    assert bundle.to_document()["formal_value_authorized"] is False


def test_components_match_resolution_catalogue_exactly() -> None:
    bundle = _closed_bundle()
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    contracts = {
        row.path: row
        for row in resolution_v2.official_shared_resource_resolution_catalogue_v2()
    }
    sources = bundle.live_sources_v2()
    assert tuple(row.path for row in sources) == v2.SUPPORTED_PATHS
    for source in sources:
        expected = contracts[source.path]
        assert source.exact_source_kind is expected.exact_source_kind
        assert source.provenance_claims == expected.required_provenance
        assert tuple(
            (row.component_key, row.source_schema_id)
            for row in source.components
        ) == tuple(
            (row.component_key, row.source_schema_id)
            for row in expected.required_components
        )
    # The resolution layer accepts all three component sets structurally but
    # still does not promote them without the future semantic replayers.
    envelope = resolution_v2.SharedResourceLiveEnvelopeV2(
        live_envelope_schema_id=resolution_v2.LIVE_ENVELOPE_SCHEMA_ID,
        live_envelope_id=bundle.live_envelope_id,
        counter_registry_id=registry.registry_id,
        stage_profile_id=stage.stage_profile_id,
        occurrence_id=bundle.occurrence_id,
        route_attempt_id=bundle.route_attempt_id,
        decision_point_id=bundle.decision_point_id,
        measurement_window_id=bundle.measurement_window_id,
        operational_cutoff_id=bundle.operational_cutoff_id,
        measurement_start_sequence=bundle.measurement_start_sequence,
        operational_cutoff_sequence=bundle.operational_cutoff_sequence,
        catalogue_fingerprint=(
            resolution_v2.official_shared_resource_catalogue_fingerprint_v2()
        ),
        sources=sources,
    )
    result = resolution_v2.verify_v075_k7_shared_resource_semantics_v2(
        envelope
    )
    by_path = {row.path: row for row in result.resolutions}
    for path in v2.SUPPORTED_PATHS:
        assert by_path[path].missing_component_keys == ()
        assert by_path[path].pending_reason is (
            resolution_v2.SharedResourcePendingReasonV2
            .SEMANTIC_REPLAYER_NOT_INSTALLED
        )
        assert by_path[path].exact_value is None


def test_public_recording_api_accepts_no_caller_total() -> None:
    assert "total" not in inspect.signature(
        v2.TransferMountJournalSessionV2.record_read_v2
    ).parameters
    assert "byte_count" not in inspect.signature(
        v2.TransferMountJournalSessionV2.record_read_v2
    ).parameters
    assert "total" not in inspect.signature(
        v2.TransferMountJournalSessionV2.record_stage_v2
    ).parameters
    assert "total" not in inspect.signature(
        v2.TransferMountJournalSessionV2.open_mount_visibility_v2
    ).parameters


def test_missing_sequence_is_rejected_even_after_component_refreeze() -> None:
    bundle = _closed_bundle()
    document = _document(bundle.read_journal_component.raw_bytes)
    events = document["events"]
    assert type(events) is list and len(events) == 2
    events[1]["path_sequence"] = 3
    kwargs = _raw_kwargs(bundle)
    kwargs["read_journal_bytes"] = _refreeze(
        document, v2.READ_JOURNAL_SCHEMA_ID
    )
    with pytest.raises(
        v2.ConstructionSharedResourceTransferMountJournalV2Error,
        match="missing or repeated path sequence",
    ):
        v2.replay_transfer_mount_raw_evidence_v2(**kwargs)


def test_duplicate_transfer_id_is_rejected() -> None:
    bundle = _closed_bundle()
    document = _document(bundle.read_journal_component.raw_bytes)
    events = document["events"]
    assert type(events) is list and len(events) == 2
    events[1]["transfer_id"] = events[0]["transfer_id"]
    kwargs = _raw_kwargs(bundle)
    kwargs["read_journal_bytes"] = _refreeze(
        document, v2.READ_JOURNAL_SCHEMA_ID
    )
    with pytest.raises(
        v2.ConstructionSharedResourceTransferMountJournalV2Error,
        match="transfer ID does not replay",
    ):
        v2.replay_transfer_mount_raw_evidence_v2(**kwargs)


def test_unknown_purpose_is_rejected_at_record_and_replay_boundaries() -> None:
    session = _session()
    payload = session.register_payload_v2(
        payload_role="SEALED_PAYLOAD", raw_bytes=b"payload"
    )
    with pytest.raises(
        v2.ConstructionSharedResourceTransferMountJournalV2Error,
        match="unknown or wrong-path purpose",
    ):
        session.record_stage_v2(payload=payload, purpose_key="unknown")

    bundle = _closed_bundle()
    document = _document(bundle.read_journal_component.raw_bytes)
    events = document["events"]
    assert type(events) is list
    events[0]["purpose_key"] = "unknown"
    kwargs = _raw_kwargs(bundle)
    kwargs["read_journal_bytes"] = _refreeze(
        document, v2.READ_JOURNAL_SCHEMA_ID
    )
    with pytest.raises(
        v2.ConstructionSharedResourceTransferMountJournalV2Error,
        match="unknown purpose",
    ):
        v2.replay_transfer_mount_raw_evidence_v2(**kwargs)


def test_payload_transplant_and_slice_mismatch_are_rejected() -> None:
    first = _session(0)
    second = _session(100)
    payload = first.register_payload_v2(
        payload_role="SEALED_PAYLOAD", raw_bytes=b"abcdef"
    )
    with pytest.raises(
        v2.ConstructionSharedResourceTransferMountJournalV2Error,
        match="transplanted",
    ):
        second.record_stage_v2(
            payload=payload, purpose_key="stage.worker"
        )
    with pytest.raises(
        v2.ConstructionSharedResourceTransferMountJournalV2Error,
        match="registered payload slice",
    ):
        first.record_read_v2(
            payload=payload,
            purpose_key="read.broker",
            byte_offset=0,
            returned_bytes=b"wrong",
        )


@pytest.mark.parametrize("forged_sum", [6, 18])
def test_repeated_stage_under_or_double_count_is_rejected(
    forged_sum: int,
) -> None:
    bundle = _closed_bundle()
    document = _document(bundle.staged_journal_component.raw_bytes)
    document["raw_derived_sum_bytes"] = forged_sum
    kwargs = _raw_kwargs(bundle)
    kwargs["staged_journal_bytes"] = _refreeze(
        document, v2.STAGED_JOURNAL_SCHEMA_ID
    )
    with pytest.raises(
        v2.ConstructionSharedResourceTransferMountJournalV2Error,
        match="under-counted or double-counted",
    ):
        v2.replay_transfer_mount_raw_evidence_v2(**kwargs)


def test_same_payload_mount_double_count_is_rejected() -> None:
    bundle = _closed_bundle()
    document = _document(bundle.mount_journal_component.raw_bytes)
    events = document["events"]
    assert type(events) is list
    # After the second OPEN two intervals exist but only one unique payload.
    assert events[1]["raw_unique_payload_bytes_after_event"] == 6
    events[1]["raw_unique_payload_bytes_after_event"] = 12
    kwargs = _raw_kwargs(bundle)
    kwargs["mount_journal_bytes"] = _refreeze(
        document, v2.MOUNT_JOURNAL_SCHEMA_ID
    )
    with pytest.raises(
        v2.ConstructionSharedResourceTransferMountJournalV2Error,
        match="double-counted or under-counted",
    ):
        v2.replay_transfer_mount_raw_evidence_v2(**kwargs)


def test_unclosed_visibility_interval_prevents_cutoff() -> None:
    session = _session()
    payload = session.register_payload_v2(
        payload_role="SEALED_PAYLOAD", raw_bytes=b"abcdef"
    )
    session.open_mount_visibility_v2(
        payload=payload, purpose_key="mount.worker"
    )
    with pytest.raises(
        v2.ConstructionSharedResourceTransferMountJournalV2Error,
        match="unclosed visibility intervals",
    ):
        session.close_v2()
    assert session.state is v2.TransferMountSessionStateV2.OPEN


def test_closed_session_is_idempotent_but_cannot_append() -> None:
    session = _session()
    payload = session.register_payload_v2(
        payload_role="SEALED_PAYLOAD", raw_bytes=b"abcdef"
    )
    bundle = session.close_v2()
    assert session.close_v2() is bundle
    assert session.state is v2.TransferMountSessionStateV2.CLOSED
    operations = (
        lambda: session.register_payload_v2(
            payload_role="SEALED_PAYLOAD", raw_bytes=b"other"
        ),
        lambda: session.record_stage_v2(
            payload=payload, purpose_key="stage.worker"
        ),
        lambda: session.record_read_v2(
            payload=payload,
            purpose_key="read.broker",
            byte_offset=0,
            returned_bytes=b"",
        ),
        lambda: session.open_mount_visibility_v2(
            payload=payload, purpose_key="mount.worker"
        ),
    )
    for operation in operations:
        with pytest.raises(
            v2.ConstructionSharedResourceTransferMountJournalV2Error,
            match="cannot be appended",
        ):
            operation()


def test_cross_component_occurrence_transplant_is_rejected() -> None:
    bundle = _closed_bundle()
    document = _document(bundle.read_journal_component.raw_bytes)
    document["occurrence_id"] = _cid(999)
    kwargs = _raw_kwargs(bundle)
    kwargs["read_journal_bytes"] = _refreeze(
        document, v2.READ_JOURNAL_SCHEMA_ID
    )
    with pytest.raises(
        v2.ConstructionSharedResourceTransferMountJournalV2Error,
        match="crossed occurrence/window identity",
    ):
        v2.replay_transfer_mount_raw_evidence_v2(**kwargs)


def test_global_cutoff_index_cannot_hide_one_event() -> None:
    bundle = _closed_bundle()
    document = _document(bundle.cutoff_component.raw_bytes)
    event_index = document["global_event_index"]
    assert type(event_index) is list and len(event_index) == 8
    event_index.pop()
    document["global_event_count"] = 7
    document["operational_cutoff_sequence"] -= 1
    kwargs = _raw_kwargs(bundle)
    kwargs["cutoff_bytes"] = _refreeze(document, v2.CUTOFF_SCHEMA_ID)
    with pytest.raises(
        v2.ConstructionSharedResourceTransferMountJournalV2Error,
        match="global event sequence",
    ):
        v2.replay_transfer_mount_raw_evidence_v2(**kwargs)


def test_no_formal_materialization_api_or_authority_is_exposed() -> None:
    bundle = _closed_bundle()
    assert not hasattr(v2, "CounterRecordV6")
    assert not hasattr(v2, "materialize_counter_records_v6")
    assert bundle.raw_replay.semantic_source_verified is False
    assert bundle.raw_replay.counter_record_issuance_authorized is False
