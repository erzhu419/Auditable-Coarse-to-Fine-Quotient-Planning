from __future__ import annotations

import hashlib
import inspect

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_common_journal_v2 as v2
from acfqp import construction_shared_resource_resolution_v2 as resolution_v2
from acfqp.phase3e_ids import loads_canonical_json


def _cid(index: int) -> str:
    return f"{index:064x}"


def _sites() -> tuple[v2.CommonSourceSiteRegistrationV2, ...]:
    rows = (
        (v2.HASH_PATH, "hash.site", "hash_call"),
        (v2.INTEGRITY_PATH, "integrity.site", "integrity_check"),
        (v2.PROTOCOL_PATH, "protocol.site", "protocol_check"),
    )
    return tuple(
        v2.freeze_common_source_site_v2(
            path=path,
            site_key=key,
            source_module="acfqp.synthetic_common_owner_v2",
            source_symbol=symbol,
            source_archive_id=_cid(100 + index),
            source_sha256=hashlib.sha256(key.encode("ascii")).hexdigest(),
            source_byte_count=1000 + index,
        )
        for index, (path, key, symbol) in enumerate(rows)
    )


def _hash_purposes() -> tuple[v2.HashPurposeRegistrationV2, ...]:
    return (
        v2.freeze_hash_purpose_v2(
            purpose_key="business.content_id",
            allowed_site_keys=("hash.site",),
        ),
    )


def _integrity_obligations(
) -> tuple[v2.NamedObligationRegistrationV2, ...]:
    return (
        v2.freeze_named_obligation_v2(
            path=v2.INTEGRITY_PATH,
            obligation_key="artifact.digest_matches",
            site_key="integrity.site",
            predicate_owner_module="acfqp.synthetic_common_owner_v2",
            predicate_owner_symbol="verify_digest",
        ),
    )


def _protocol_obligations(
) -> tuple[v2.NamedObligationRegistrationV2, ...]:
    return (
        v2.freeze_named_obligation_v2(
            path=v2.PROTOCOL_PATH,
            obligation_key="broker.frame_order",
            site_key="protocol.site",
            predicate_owner_module="acfqp.synthetic_common_owner_v2",
            predicate_owner_symbol="verify_frame_order",
        ),
    )


def _session(offset: int = 0) -> v2.CommonJournalSessionV2:
    return v2.CommonJournalSessionV2(
        live_envelope_id=_cid(10 + offset),
        occurrence_id=_cid(11 + offset),
        route_attempt_id=_cid(12 + offset),
        decision_point_id=_cid(13 + offset),
        measurement_window_id=_cid(14 + offset),
        operational_cutoff_id=_cid(15 + offset),
        measurement_start_sequence=50,
        source_sites=_sites(),
        hash_purposes=_hash_purposes(),
        integrity_obligations=_integrity_obligations(),
        protocol_obligations=_protocol_obligations(),
    )


def _record_hash(
    session: v2.CommonJournalSessionV2,
    *,
    observation: int,
    input_id: int,
    output_id: int,
) -> str:
    return session.record_hash_invocation_v2(
        purpose_key="business.content_id",
        site_key="hash.site",
        authenticated_broker_observation_id=_cid(observation),
        input_artifact_ids=(_cid(input_id),),
        output_artifact_ids=(_cid(output_id),),
    )


def _bundle() -> v2.CommonRawEvidenceBundleV2:
    session = _session()
    _record_hash(session, observation=200, input_id=300, output_id=301)
    session.record_integrity_check_v2(
        obligation_key="artifact.digest_matches",
        site_key="integrity.site",
        outcome=v2.NamedObligationOutcomeV2.PASS,
        authenticated_broker_observation_id=_cid(201),
        input_artifact_ids=(_cid(302),),
        output_artifact_ids=(_cid(303),),
    )
    _record_hash(session, observation=202, input_id=304, output_id=305)
    session.record_protocol_check_v2(
        obligation_key="broker.frame_order",
        site_key="protocol.site",
        outcome=v2.NamedObligationOutcomeV2.FAIL,
        authenticated_broker_observation_id=_cid(203),
        input_artifact_ids=(_cid(306),),
        output_artifact_ids=(_cid(307),),
    )
    session.record_integrity_check_v2(
        obligation_key="artifact.digest_matches",
        site_key="integrity.site",
        outcome=v2.NamedObligationOutcomeV2.FAIL,
        authenticated_broker_observation_id=_cid(204),
        input_artifact_ids=(_cid(308),),
        output_artifact_ids=(_cid(309),),
    )
    return session.close_v2()


def _raw_kwargs(bundle: v2.CommonRawEvidenceBundleV2) -> dict[str, bytes]:
    return {
        "cutoff_bytes": bundle.cutoff_component.raw_bytes,
        "hash_transcript_bytes": bundle.hash_transcript_component.raw_bytes,
        "hash_purpose_registry_bytes": (
            bundle.hash_purpose_registry_component.raw_bytes
        ),
        "hash_site_attestation_bytes": bundle.hash_site_component.raw_bytes,
        "integrity_registry_bytes": bundle.integrity_registry_component.raw_bytes,
        "integrity_transcript_bytes": (
            bundle.integrity_transcript_component.raw_bytes
        ),
        "integrity_site_attestation_bytes": (
            bundle.integrity_site_component.raw_bytes
        ),
        "protocol_registry_bytes": bundle.protocol_registry_component.raw_bytes,
        "protocol_transcript_bytes": (
            bundle.protocol_transcript_component.raw_bytes
        ),
        "protocol_site_attestation_bytes": (
            bundle.protocol_site_component.raw_bytes
        ),
    }


def _document(raw: bytes) -> dict[str, object]:
    result = loads_canonical_json(raw)
    assert type(result) is dict
    return result


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


def test_raw_replay_derives_all_three_counts_without_formal_authority() -> None:
    bundle = _bundle()
    assert bundle.raw_replay.hash_invocation_count == 2
    assert bundle.raw_replay.integrity_check_count == 2
    assert bundle.raw_replay.protocol_check_count == 1
    assert bundle.raw_replay.global_event_count == 5
    assert bundle.raw_replay.semantic_source_verified is False
    assert bundle.raw_replay.counter_record_issuance_authorized is False
    assert not hasattr(v2, "CounterRecordV6")
    assert not hasattr(v2, "materialize_counter_records_v6")


def test_components_match_resolution_catalogue_exactly() -> None:
    bundle = _bundle()
    contracts = {
        row.path: row
        for row in resolution_v2.official_shared_resource_resolution_catalogue_v2()
    }
    sources = bundle.live_sources_v2()
    assert tuple(row.path for row in sources) == v2.SUPPORTED_PATHS
    for source in sources:
        contract = contracts[source.path]
        assert source.exact_source_kind is contract.exact_source_kind
        assert source.provenance_claims == contract.required_provenance
        assert tuple(
            (row.component_key, row.source_schema_id)
            for row in source.components
        ) == tuple(
            (row.component_key, row.source_schema_id)
            for row in contract.required_components
        )
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    envelope = resolution_v2.SharedResourceLiveEnvelopeV2(
        resolution_v2.LIVE_ENVELOPE_SCHEMA_ID,
        bundle.live_envelope_id,
        registry.registry_id,
        stage.stage_profile_id,
        bundle.occurrence_id,
        bundle.route_attempt_id,
        bundle.decision_point_id,
        bundle.measurement_window_id,
        bundle.operational_cutoff_id,
        bundle.measurement_start_sequence,
        bundle.operational_cutoff_sequence,
        resolution_v2.official_shared_resource_catalogue_fingerprint_v2(),
        sources,
    )
    result = resolution_v2.verify_v075_k7_shared_resource_semantics_v2(
        envelope
    )
    by_path = {row.path: row for row in result.resolutions}
    for path in v2.SUPPORTED_PATHS:
        assert by_path[path].missing_component_keys == ()
        assert by_path[path].exact_value is None
        assert by_path[path].pending_reason is (
            resolution_v2.SharedResourcePendingReasonV2
            .SEMANTIC_REPLAYER_NOT_INSTALLED
        )


def test_recording_api_accepts_no_caller_count_or_total() -> None:
    for method in (
        v2.CommonJournalSessionV2.record_hash_invocation_v2,
        v2.CommonJournalSessionV2.record_integrity_check_v2,
        v2.CommonJournalSessionV2.record_protocol_check_v2,
    ):
        parameters = inspect.signature(method).parameters
        assert "count" not in parameters
        assert "total" not in parameters


def test_missing_transcript_event_is_caught_by_exact_registry_coverage() -> None:
    bundle = _bundle()
    document = _document(bundle.hash_transcript_component.raw_bytes)
    events = document["events"]
    assert type(events) is list and len(events) == 2
    events.pop()
    document["path_event_count"] = 1
    document["raw_derived_event_count"] = 1
    kwargs = _raw_kwargs(bundle)
    kwargs["hash_transcript_bytes"] = _refreeze(
        document, v2.HASH_TRANSCRIPT_SCHEMA_ID
    )
    with pytest.raises(
        v2.ConstructionSharedResourceCommonJournalV2Error,
        match="registry coverage has missing",
    ):
        v2.replay_common_raw_evidence_v2(**kwargs)


def test_extra_or_duplicate_transcript_event_is_rejected() -> None:
    bundle = _bundle()
    document = _document(bundle.hash_transcript_component.raw_bytes)
    events = document["events"]
    assert type(events) is list and len(events) == 2
    forged = dict(events[0])
    forged["path_sequence"] = 3
    events.append(forged)
    document["path_event_count"] = 3
    document["raw_derived_event_count"] = 3
    kwargs = _raw_kwargs(bundle)
    kwargs["hash_transcript_bytes"] = _refreeze(
        document, v2.HASH_TRANSCRIPT_SCHEMA_ID
    )
    with pytest.raises(
        v2.ConstructionSharedResourceCommonJournalV2Error,
        match="does not replay",
    ):
        v2.replay_common_raw_evidence_v2(**kwargs)


def test_reordered_path_events_are_rejected() -> None:
    bundle = _bundle()
    document = _document(bundle.hash_transcript_component.raw_bytes)
    events = document["events"]
    assert type(events) is list and len(events) == 2
    events.reverse()
    kwargs = _raw_kwargs(bundle)
    kwargs["hash_transcript_bytes"] = _refreeze(
        document, v2.HASH_TRANSCRIPT_SCHEMA_ID
    )
    with pytest.raises(
        v2.ConstructionSharedResourceCommonJournalV2Error,
        match="missing, duplicate, or reordered sequence",
    ):
        v2.replay_common_raw_evidence_v2(**kwargs)


def test_duplicate_authenticated_broker_observation_is_rejected() -> None:
    session = _session()
    _record_hash(session, observation=800, input_id=801, output_id=802)
    with pytest.raises(
        v2.ConstructionSharedResourceCommonJournalV2Error,
        match="observation ID is duplicated",
    ):
        session.record_integrity_check_v2(
            obligation_key="artifact.digest_matches",
            site_key="integrity.site",
            outcome=v2.NamedObligationOutcomeV2.PASS,
            authenticated_broker_observation_id=_cid(800),
            input_artifact_ids=(_cid(803),),
            output_artifact_ids=(_cid(804),),
        )


def test_unregistered_site_purpose_and_obligation_are_rejected() -> None:
    session = _session()
    with pytest.raises(
        v2.ConstructionSharedResourceCommonJournalV2Error,
        match="unregistered purpose",
    ):
        session.record_hash_invocation_v2(
            purpose_key="unknown",
            site_key="hash.site",
            authenticated_broker_observation_id=_cid(900),
            input_artifact_ids=(_cid(901),),
            output_artifact_ids=(_cid(902),),
        )
    with pytest.raises(
        v2.ConstructionSharedResourceCommonJournalV2Error,
        match="unregistered source site",
    ):
        session.record_hash_invocation_v2(
            purpose_key="business.content_id",
            site_key="unknown.site",
            authenticated_broker_observation_id=_cid(903),
            input_artifact_ids=(_cid(904),),
            output_artifact_ids=(_cid(905),),
        )
    with pytest.raises(
        v2.ConstructionSharedResourceCommonJournalV2Error,
        match="unregistered obligation",
    ):
        session.record_protocol_check_v2(
            obligation_key="unknown",
            site_key="protocol.site",
            outcome=v2.NamedObligationOutcomeV2.PASS,
            authenticated_broker_observation_id=_cid(906),
            input_artifact_ids=(_cid(907),),
            output_artifact_ids=(_cid(908),),
        )


def test_replay_rejects_unregistered_site_and_registry_key() -> None:
    bundle = _bundle()
    document = _document(bundle.protocol_transcript_component.raw_bytes)
    events = document["events"]
    assert type(events) is list
    events[0]["site_key"] = "unknown.site"
    kwargs = _raw_kwargs(bundle)
    kwargs["protocol_transcript_bytes"] = _refreeze(
        document, v2.PROTOCOL_TRANSCRIPT_SCHEMA_ID
    )
    with pytest.raises(
        v2.ConstructionSharedResourceCommonJournalV2Error,
        match="unregistered source site",
    ):
        v2.replay_common_raw_evidence_v2(**kwargs)

    document = _document(bundle.integrity_transcript_component.raw_bytes)
    events = document["events"]
    assert type(events) is list
    events[0]["registry_key"] = "unknown.obligation"
    kwargs = _raw_kwargs(bundle)
    kwargs["integrity_transcript_bytes"] = _refreeze(
        document, v2.INTEGRITY_TRANSCRIPT_SCHEMA_ID
    )
    with pytest.raises(
        v2.ConstructionSharedResourceCommonJournalV2Error,
        match="unregistered purpose or obligation",
    ):
        v2.replay_common_raw_evidence_v2(**kwargs)


def test_registry_coverage_cannot_omit_or_add_event_ids() -> None:
    bundle = _bundle()
    document = _document(bundle.hash_purpose_registry_component.raw_bytes)
    coverage = document["purpose_event_coverage"]
    assert type(coverage) is list
    coverage[0]["covered_event_ids"].pop()
    kwargs = _raw_kwargs(bundle)
    kwargs["hash_purpose_registry_bytes"] = _refreeze(
        document, v2.HASH_PURPOSE_REGISTRY_SCHEMA_ID
    )
    with pytest.raises(
        v2.ConstructionSharedResourceCommonJournalV2Error,
        match="registry coverage has missing",
    ):
        v2.replay_common_raw_evidence_v2(**kwargs)


def test_raw_count_under_or_double_count_is_rejected() -> None:
    bundle = _bundle()
    for forged_count in (1, 3):
        document = _document(bundle.hash_transcript_component.raw_bytes)
        document["raw_derived_event_count"] = forged_count
        kwargs = _raw_kwargs(bundle)
        kwargs["hash_transcript_bytes"] = _refreeze(
            document, v2.HASH_TRANSCRIPT_SCHEMA_ID
        )
        with pytest.raises(
            v2.ConstructionSharedResourceCommonJournalV2Error,
            match="under-counted or double-counted",
        ):
            v2.replay_common_raw_evidence_v2(**kwargs)


def test_cutoff_cannot_hide_one_registered_event() -> None:
    bundle = _bundle()
    document = _document(bundle.cutoff_component.raw_bytes)
    index = document["global_event_index"]
    observations = document["authenticated_broker_observation_ids"]
    assert type(index) is list and type(observations) is list
    index.pop()
    observations.pop()
    document["global_event_count"] = 4
    document["operational_cutoff_sequence"] -= 1
    kwargs = _raw_kwargs(bundle)
    kwargs["cutoff_bytes"] = _refreeze(document, v2.CUTOFF_SCHEMA_ID)
    with pytest.raises(
        v2.ConstructionSharedResourceCommonJournalV2Error,
        match="cutoff hides",
    ):
        v2.replay_common_raw_evidence_v2(**kwargs)


def test_cross_component_occurrence_identity_is_rejected() -> None:
    bundle = _bundle()
    document = _document(bundle.integrity_site_component.raw_bytes)
    document["occurrence_id"] = _cid(999)
    kwargs = _raw_kwargs(bundle)
    kwargs["integrity_site_attestation_bytes"] = _refreeze(
        document, v2.INTEGRITY_SITE_SCHEMA_ID
    )
    with pytest.raises(
        v2.ConstructionSharedResourceCommonJournalV2Error,
        match="crossed occurrence/window identity",
    ):
        v2.replay_common_raw_evidence_v2(**kwargs)


def test_input_output_ids_are_canonical_sorted_and_unique() -> None:
    session = _session()
    with pytest.raises(
        v2.ConstructionSharedResourceCommonJournalV2Error,
        match="sorted unique tuple",
    ):
        session.record_hash_invocation_v2(
            purpose_key="business.content_id",
            site_key="hash.site",
            authenticated_broker_observation_id=_cid(700),
            input_artifact_ids=(_cid(702), _cid(701)),
            output_artifact_ids=(_cid(703),),
        )
    with pytest.raises(
        v2.ConstructionSharedResourceCommonJournalV2Error,
        match="sorted unique tuple",
    ):
        session.record_hash_invocation_v2(
            purpose_key="business.content_id",
            site_key="hash.site",
            authenticated_broker_observation_id=_cid(704),
            input_artifact_ids=(_cid(705),),
            output_artifact_ids=(_cid(706), _cid(706)),
        )


def test_registries_are_frozen_and_must_precover_sites() -> None:
    bad_purpose = (
        v2.freeze_hash_purpose_v2(
            purpose_key="business.content_id",
            allowed_site_keys=("missing.site",),
        ),
    )
    with pytest.raises(
        v2.ConstructionSharedResourceCommonJournalV2Error,
        match="unregistered source site",
    ):
        v2.CommonJournalSessionV2(
            live_envelope_id=_cid(1),
            occurrence_id=_cid(2),
            route_attempt_id=_cid(3),
            decision_point_id=_cid(4),
            measurement_window_id=_cid(5),
            operational_cutoff_id=_cid(6),
            measurement_start_sequence=0,
            source_sites=_sites(),
            hash_purposes=bad_purpose,
            integrity_obligations=_integrity_obligations(),
            protocol_obligations=_protocol_obligations(),
        )


def test_close_is_idempotent_and_append_after_close_is_rejected() -> None:
    session = _session()
    bundle = session.close_v2()
    assert session.close_v2() is bundle
    assert session.state is v2.CommonJournalSessionStateV2.CLOSED
    with pytest.raises(
        v2.ConstructionSharedResourceCommonJournalV2Error,
        match="cannot be appended",
    ):
        _record_hash(session, observation=600, input_id=601, output_id=602)
