from __future__ import annotations

from dataclasses import replace
import hashlib
import os
from pathlib import Path
import stat

import pytest

from acfqp import construction_accounting_evidence_closure_v1 as closure_v1
from acfqp import construction_accounting_owner_event_candidates_v1 as owner_events_v1
from acfqp import construction_occurrence_identity_cutoff_join_v1 as join_v1
from acfqp import construction_occurrence_identity_cutoff_semantic_authority_v2 as v2
from acfqp import construction_shared_resource_common_journal_v2 as common_v2
from acfqp import construction_shared_resource_live_envelope_v3 as live_v3
from acfqp import construction_shared_resource_output_journal_v2 as output_v2
from acfqp import construction_shared_resource_receipts_v1 as receipts_v1
from acfqp import construction_shared_resource_resolution_v2 as resolution_v2
from acfqp import construction_shared_resource_transfer_mount_journal_v2 as transfer_v2
from acfqp import construction_shared_resource_verified_envelope_v1 as verified_v1
from acfqp import construction_shared_resource_working_process_evidence_v2 as working_v2
from acfqp import phase3e_ids as ids_v1
from acfqp import v075_k7_authenticated_broker_channel_v2 as channel_v2
from acfqp import v075_k7_broker_worker_entry_v1 as worker_v1
from acfqp import v075_k7_child_business_bundle_v1 as child_bundle_v1
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
from acfqp import v075_k7_production_broker_runtime_v2 as runtime_v2
from acfqp import v075_k7_production_role_manifest_v2 as role_manifest_v2
from acfqp import v075_k7_successor_portable_replay_v1 as portable_v1
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable_evidence_v2
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from tests import test_construction_occurrence_identity_cutoff_join_v1 as join_test
from tests import test_construction_shared_resource_common_journal_v2 as common_test
from tests import test_construction_shared_resource_output_journal_v2 as output_test
from tests import test_construction_shared_resource_transfer_mount_journal_v2 as transfer_test
from tests import test_construction_shared_resource_working_process_evidence_v2 as working_test
from tests import test_v075_k7_child_business_bundle_v1 as child_test


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:test:occurrence-cutoff-semantic-authority:v2\x00"
        + label.encode("utf-8")
    ).hexdigest()


def test_six_domains_are_central_unique_and_role_separated() -> None:
    expected = (
        ids_v1.CONSTRUCTION_K7_OCCURRENCE_IDENTITY_SEMANTIC_AUTHORITY_V2_DOMAIN,
        ids_v1.CONSTRUCTION_K7_OPERATIONAL_CUTOFF_SEMANTIC_AUTHORITY_V2_DOMAIN,
        ids_v1.CONSTRUCTION_K7_OCCURRENCE_CUTOFF_SEMANTIC_AUTHORITY_BUNDLE_V2_DOMAIN,
        ids_v1.CONSTRUCTION_K7_PRODUCTION_MEASUREMENT_START_V2_DOMAIN,
        ids_v1.CONSTRUCTION_K7_PRODUCTION_MEASUREMENT_CUTOFF_V2_DOMAIN,
        ids_v1.CONSTRUCTION_K7_PRODUCTION_TERMINAL_CLOSURE_V2_DOMAIN,
    )
    assert v2.PROPOSED_CONTRACT_VERSION == "2.0.25"
    assert v2.REQUESTED_PHASE3E_DOMAIN_TAGS == expected
    assert len(set(expected)) == 6
    assert set(expected) <= ids_v1.PHASE3E_DOMAIN_TAGS
    payload = {"schema": "same-occurrence-cutoff-payload"}
    assert len({ids_v1.content_id(domain, payload) for domain in expected}) == 6


def _authenticated(
    binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
    role: ipc_v1.K7OuterAttemptBrokerFrameRoleV1,
    payload: dict[str, object],
    index: int,
    sender_pid: int,
) -> channel_v2.K7AuthenticatedBrokerFrameV2:
    raw = ipc_v1.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
        binding=binding,
        role=role,
        payload=payload,
    )
    frame = ipc_v1.verify_v075_k7_outer_attempt_broker_ipc_frame_v1(
        raw=raw,
        expected_binding=binding,
        expected_role=role,
    )
    return channel_v2.K7AuthenticatedBrokerFrameV2(
        channel_v2._FRAME_ISSUER,  # noqa: SLF001 - exact runtime fixture
        (10 + index, 20 + index, stat.S_IFSOCK | 0o600, os.geteuid(), os.getegid(), 1),
        (30 + index, 40 + index, stat.S_IFREG | 0o400, os.geteuid(), os.getegid(), 1),
        sender_pid,
        os.geteuid(),
        os.getegid(),
        frame,
        hashlib.sha256(raw).hexdigest(),
        len(raw),
    )


def _worker_output_candidate(
    root: Path,
    replay: portable_v1.V075K7SuccessorPortableRequestReplayV1,
    owned,
    portable,
    taint_authority,
    observer_session_public_id: str,
):
    bundle = child_bundle_v1._freeze_bundle(  # noqa: SLF001
        request_replay=replay,
        wrapped=owned,
        portable_bundle=portable,
        expected_session_public_id=observer_session_public_id,
        private_taint_authority=taint_authority,
    )
    binding = ipc_v1.K7OuterAttemptBrokerIPCBindingV1(
        replay.request.request_id,
        replay.request.route_identity.route_identity_id,
        _id("broker-execution-spec"),
        _id("broker-session-nonce"),
    )

    output = worker_v1._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    worker_v1._commit_output(output=output, directory_fd=directory_fd)  # noqa: SLF001
    raw = output.canonical_bytes
    parent = _authenticated(
        binding,
        ipc_v1.K7OuterAttemptBrokerFrameRoleV1.PARENT_OUTPUT,
        {
            "output_byte_count": len(raw),
            "output_sha256": hashlib.sha256(raw).hexdigest(),
        },
        3,
        41001,
    )
    return directory_fd, binding, bundle, output, raw, parent


def _runtime_envelope(
    *,
    role_manifest,
    binding,
    business_bundle,
    output,
    output_raw,
    parent_output,
):
    roles = ipc_v1.K7OuterAttemptBrokerFrameRoleV1
    observations = (
        _authenticated(binding, roles.WORKER_READY, {"worker_replay_id": _id("worker-replay")}, 0, 41001),
        _authenticated(binding, roles.BUSINESS_REQUEST, {"request_ordinal": 0}, 1, 41001),
        _authenticated(binding, roles.BUSINESS_RESULT, {"business_result_id": business_bundle.bundle_id}, 2, 41002),
        parent_output,
        _authenticated(binding, roles.WORKER_EOF, {"clean_close": True}, 4, 41001),
    )
    transcript = ipc_v1.verify_v075_k7_outer_attempt_broker_ipc_stream_v1(
        raw=b"".join(row.frame.framed_bytes for row in observations),
        expected_binding=binding,
    )
    descriptor = runtime_v2._identity_document(  # noqa: SLF001
        (1, 2, stat.S_IFREG | 0o400, os.geteuid(), os.getegid(), 0, len(output_raw), 1, 1, 0, os.O_RDONLY)
    )
    role_rows = tuple(
        {
            "role": role,
            "pid": pid,
            "pidfd_identity": descriptor,
            "native_write_ahead_edge": 1,
            "setup_raw_sha256": hashlib.sha256(role.encode()).hexdigest(),
            "setup_raw_byte_count": len(role),
            "authenticated_frame_ids": [
                row.observation_id for row in observations if row.sender_pid == pid
            ],
            "direct_pidfd_reaped": True,
            "exit_code": 0,
        }
        for role, pid in (("WORKER", 41001), ("BUSINESS", 41002))
    )
    return runtime_v2.K7ProductionBrokerRuntimeEnvelopeV2(
        runtime_v2._ENVELOPE_ISSUER,  # noqa: SLF001 - exact type fixture
        _id("prepared-session"),
        _id("resource-session"),
        role_manifest.manifest_id,
        _id("worker-launch"),
        _id("business-launch"),
        binding,
        role_rows,
        observations,
        transcript,
        business_bundle.bundle_id,
        hashlib.sha256(business_bundle.canonical_bytes).hexdigest(),
        len(business_bundle.canonical_bytes),
        output.output_id,
        hashlib.sha256(output_raw).hexdigest(),
        len(output_raw),
        descriptor,
        f"{runtime_v2.PROMOTED_OUTPUT_PREFIX}{_id('promoted')}.json",
        8192,
        descriptor,
        True,
        True,
    )


def _receipt_set(owned, replay, runtime):
    route = replay.request.route_identity
    start_id = v2.derive_k7_production_measurement_start_id_v2(
        runtime_envelope=runtime, request_replay=replay
    )
    cutoff_id = v2.derive_k7_production_measurement_cutoff_id_v2(
        runtime_envelope=runtime, request_replay=replay
    )
    base = join_test._receipt_set(  # noqa: SLF001
        "positive-v2",
        boundary_profile_id=owned.boundary_profile_id,
        execution_profile_id=owned.execution_profile_id,
        occurrence_id=owned.transcript.start.occurrence_id,
    )
    identity = receipts_v1.SharedResourceIdentityBindingV1(
        base.identity.counter_registry_id,
        base.identity.stage_profile_id,
        base.identity.boundary_profile_id,
        base.identity.execution_profile_id,
        base.identity.occurrence_id,
        route.route_attempt.route_attempt_id,
        route.decision_point.decision_point_id,
    )
    window = receipts_v1.SharedResourceMeasurementWindowV1(
        identity.identity_binding_id,
        "positive.v2.production.window",
        start_id,
        cutoff_id,
        v2.GLOBAL_START_SEQUENCE,
        v2.GLOBAL_CUTOFF_SEQUENCE,
        receipts_v1.MeasurementWindowStateV1.CLOSED,
    )
    receipts = []
    for old in base.receipts:
        evidence = old.source_evidence
        charge = receipts_v1.shared_resource_charge_key_v1(
            measurement_registry_id=base.registry.measurement_registry_id,
            method_id=old.method_id,
            monitor_registration_id=old.monitor_registration_id,
            identity_binding_id=identity.identity_binding_id,
            window_id=window.window_id,
            source_schema_id=evidence.source_schema_id,
            source_artifact_id=evidence.source_artifact_id,
            covered_start_sequence=window.start_sequence,
            covered_cutoff_sequence=window.cutoff_sequence,
        )
        replacement = receipts_v1.SharedResourceSourceEvidenceV1(
            base.registry.measurement_registry_id,
            old.method_id,
            old.monitor_registration_id,
            identity.identity_binding_id,
            window.window_id,
            evidence.evidence_kind,
            evidence.source_schema_id,
            evidence.source_artifact_id,
            evidence.evidence_bytes_sha256,
            charge,
            window.start_sequence,
            window.cutoff_sequence,
            evidence.reported_value,
            evidence.observed_event_count,
            True,
            True,
        )
        receipts.append(
            receipts_v1.SharedResourceReceiptV1(
                base.registry,
                identity,
                window,
                old.path,
                old.status,
                True,
                old.value,
                old.method_id,
                old.monitor_registration_id,
                replacement,
            )
        )
    return receipts_v1.SharedResourceReceiptSetV1(
        base.registry, identity, window, tuple(receipts)
    )


def _common_sources(runtime_id, occurrence, attempt, decision, window):
    session = common_v2.CommonJournalSessionV2(
        live_envelope_id=runtime_id,
        occurrence_id=occurrence,
        route_attempt_id=attempt,
        decision_point_id=decision,
        measurement_window_id=window,
        operational_cutoff_id=_id("common-cutoff"),
        measurement_start_sequence=50,
        source_sites=common_test._sites(),  # noqa: SLF001
        hash_purposes=common_test._hash_purposes(),  # noqa: SLF001
        integrity_obligations=common_test._integrity_obligations(),  # noqa: SLF001
        protocol_obligations=common_test._protocol_obligations(),  # noqa: SLF001
    )
    session.record_hash_invocation_v2(
        purpose_key="business.content_id", site_key="hash.site",
        authenticated_broker_observation_id=_id("hash-observation"),
        input_artifact_ids=(_id("hash-input"),), output_artifact_ids=(_id("hash-output"),),
    )
    session.record_integrity_check_v2(
        obligation_key="artifact.digest_matches", site_key="integrity.site",
        outcome=common_v2.NamedObligationOutcomeV2.PASS,
        authenticated_broker_observation_id=_id("integrity-observation"),
        input_artifact_ids=(_id("integrity-input"),), output_artifact_ids=(_id("integrity-output"),),
    )
    session.record_protocol_check_v2(
        obligation_key="broker.frame_order", site_key="protocol.site",
        outcome=common_v2.NamedObligationOutcomeV2.PASS,
        authenticated_broker_observation_id=_id("protocol-observation"),
        input_artifact_ids=(_id("protocol-input"),), output_artifact_ids=(_id("protocol-output"),),
    )
    return session.close_v2().live_sources_v2()


def _transfer_sources(runtime_id, occurrence, attempt, decision, window):
    session = transfer_v2.TransferMountJournalSessionV2(
        live_envelope_id=runtime_id,
        occurrence_id=occurrence,
        route_attempt_id=attempt,
        decision_point_id=decision,
        measurement_window_id=window,
        operational_cutoff_id=_id("transfer-cutoff"),
        measurement_start_sequence=40,
        purposes=transfer_test._purposes(),  # noqa: SLF001
    )
    payload = session.register_payload_v2(payload_role="SEALED_PAYLOAD", raw_bytes=b"abcdef")
    session.record_read_v2(payload=payload, purpose_key="read.broker", byte_offset=0, returned_bytes=b"abcdef")
    session.record_stage_v2(payload=payload, purpose_key="stage.worker")
    mounted = session.open_mount_visibility_v2(payload=payload, purpose_key="mount.worker")
    session.close_mount_visibility_v2(mounted)
    return session.close_v2().live_sources_v2()


def _positive_session_resources(tmp_path_factory):
    root = tmp_path_factory.mktemp("occurrence-cutoff-v2")
    marker = "occurrence-cutoff-semantic-authority-v2-genuine-portable"
    generated, salt, namespace, authorization, signer = (
        join_test.observer_fixture._fixture(marker)  # noqa: SLF001
    )
    schedule, schedule_verification = join_test.owned_fixture._exact_schedule(  # noqa: SLF001
        namespace,
        context_index=0,
    )
    session_external_id = _id("exact-owned-session")
    captured = {}
    owned = join_test.owned_v1.run_v075_k7_root_cap_owned_partial_v1(
        repository_root=join_test.owned_fixture.REPOSITORY_ROOT,
        namespace=namespace,
        schedule=schedule,
        schedule_verification=schedule_verification,
        authority=authorization,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
        observer_signer=signer,
        session_external_id=session_external_id,
        evidence_sink=captured.update,
    )
    portable = portable_evidence_v2.freeze_v075_portable_occurrence_evidence_bundle_v2(
        evidence_roots=captured
    )
    replay = child_test._real_request_replay(  # noqa: SLF001
        signer_registry=namespace.signer_registry,
        occurrence_id=schedule.occurrence.occurrence_id,
        schedule_id=schedule.schedule_id,
        session_external_id=session_external_id,
        opaque_environment_commitment_id=(
            namespace.environment_commitment.commitment_id
        ),
    )
    taint_authority = child_bundle_v1._issue_private_taint_authority(  # noqa: SLF001
        request_replay=replay,
        secret_document={
            "secret_material_id": replay.request.sealed_secret_commitment_id,
            "generation_seed_hex": (b"genuine-private-seed-pattern").hex(),
            "private_salt_hex": (b"genuine-private-salt-pattern").hex(),
        },
        key_document={
            "registered_signer_registry_id": namespace.signer_registry.registry_id,
            "registered_public_key_id": (
                namespace.signer_registry.observer_evidence_key.key_id
            ),
            "prime_p_hex": (b"genuine-private-prime-pattern").hex(),
            "prime_q_hex": (b"genuine-private-second-prime").hex(),
            "private_exponent_hex": (b"genuine-private-exponent").hex(),
        },
    )
    observer_session_public_id = (
        captured["controlled_journal_closure"]
        .batch_closure.session_public_id
    )
    private_root = (root / "private").resolve()
    private_root.mkdir(mode=0o700)
    private_key = (private_root / "observer-key.json").resolve()
    private_key.write_bytes(b"occurrence-cutoff-v2-static-test-key")
    private_key.chmod(0o600)
    role_manifest = role_manifest_v2.freeze_v075_k7_production_role_manifest_v2(
        request=replay.request,
        repository_root=Path(__file__).resolve().parents[1],
        signer_private_root=private_root,
        signer_private_key_path=private_key,
    )
    output_root = root / "output"
    output_root.mkdir()
    fd, binding, business, worker_output, worker_raw, parent = _worker_output_candidate(
        output_root,
        replay,
        owned,
        portable,
        taint_authority,
        observer_session_public_id,
    )
    runtime = _runtime_envelope(
        role_manifest=role_manifest,
        binding=binding, business_bundle=business, output=worker_output,
        output_raw=worker_raw, parent_output=parent,
    )
    receipts = _receipt_set(owned, replay, runtime)
    terminal_id = owned.transcript.nodes[-1].chain_id
    closure = closure_v1.initialize_evidence_closure_v1(
        closure_v1.EvidenceClosureContextV1(
            owned.counter_registry_id, owned.stage_profile_id,
            owned.boundary_profile_id, owned.execution_profile_id,
            owned.transcript.transcript_id, terminal_id,
        )
    )
    identity_join = join_v1.freeze_construction_occurrence_identity_join_v1(
        owned_result=owned, evidence_closure=closure, receipt_set=receipts
    )
    route = replay.request.route_identity
    occurrence = route.logical_occurrence.logical_occurrence_id
    attempt = route.route_attempt.route_attempt_id
    decision = route.decision_point.decision_point_id
    output_commit = output_v2.adopt_production_worker_operational_output_v2(
        output_directory_fd=fd,
        authenticated_parent_output=parent,
        expected_request_replay=replay,
        expected_binding=binding,
        live_envelope_id=runtime.envelope_id,
        occurrence_id=occurrence,
        route_attempt_id=attempt,
        decision_point_id=decision,
        measurement_window_id=receipts.window.window_id,
        operational_cutoff_id=_id("output-cutoff"),
        measurement_start_sequence=70,
    )
    output_session = output_v2.open_broker_durable_output_session_v2(
        output_directory_fd=fd,
        business_commit=output_commit,
        worker_reap_observation_id=_id("worker-reap"),
        business_reap_observation_id=_id("business-reap"),
        child_cgroup_empty_observation_id=_id("cgroup-empty"),
        broker_outside_child_cgroup_observation_id=_id("broker-outside"),
        exclusive_writer_observation_id=_id("exclusive-writer"),
    )
    output_bundle = output_session.finalize_v2(renderer=output_test._renderer)  # noqa: SLF001
    common = _common_sources(runtime.envelope_id, occurrence, attempt, decision, receipts.window.window_id)
    transfer = _transfer_sources(runtime.envelope_id, occurrence, attempt, decision, receipts.window.window_id)

    def aligned_open(cgroup):
        return working_v2.open_working_process_evidence_session_v2(
            live_envelope_id=runtime.envelope_id,
            occurrence_id=occurrence,
            route_attempt_id=attempt,
            decision_point_id=decision,
            measurement_window_id=receipts.window.window_id,
            measurement_start_sequence=17,
            memory_peak_fd=cgroup.peak_fd,
            cgroup_directory_fd=cgroup.directory_fd,
        )

    patch = pytest.MonkeyPatch()
    try:
        patch.setattr(working_test, "_open_session", aligned_open)
        patch.setattr(working_test, "_binding", lambda: binding)
        working_root = root / "working"
        working_root.mkdir()
        working = working_test._exact_bundle(working_root)  # noqa: SLF001
    finally:
        patch.undo()
    by_path = {
        row.path: row
        for row in (*common, *transfer, output_bundle.live_source_v2(), *working.live_sources_v2())
    }
    source = live_v3.freeze_k7_production_shared_resource_envelope_v3(
        production_runtime_envelope_id=runtime.envelope_id,
        occurrence_id=occurrence,
        route_attempt_id=attempt,
        decision_point_id=decision,
        measurement_window_id=receipts.window.window_id,
        production_runtime_replay_id=replay.replay_id,
        terminal_closure_observation_id=v2.derive_k7_production_terminal_closure_id_v2(
            runtime_envelope=runtime, request_replay=replay
        ),
        sources=tuple(by_path[path] for path in resolution_v2.SHARED_RESOURCE_PATHS),
    )
    verified = verified_v1.verify_k7_production_shared_resource_envelope_exact_v1(source)
    owner_candidates = owner_events_v1.derive_v075_k7_owner_event_candidates_v1(
        role_manifest=role_manifest,
        runtime_envelope=runtime,
        business_bundle_raw=business.canonical_bytes,
    )
    markers = v2.expected_k7_positive_cutoff_markers_v2(
        identity_join=identity_join, receipt_set=receipts,
        runtime_envelope=runtime, request_replay=replay,
        source_envelope=source, verified_envelope=verified,
        output_bundle=output_bundle,
        owned_result=owned,
        operational_output_bytes=worker_raw,
        owner_event_candidates=owner_candidates,
        role_manifest=role_manifest,
    )
    cutoff = join_v1.freeze_operational_cutoff_attestation_v1(
        identity_join=identity_join, receipt_set=receipts, markers=markers
    )
    kwargs = {
        "identity_join": identity_join,
        "cutoff_attestation": cutoff,
        "owned_result": owned,
        "evidence_closure": closure,
        "receipt_set": receipts,
        "runtime_envelope": runtime,
        "request_replay": replay,
        "source_envelope": source,
        "verified_envelope": verified,
        "output_bundle": output_bundle,
        "operational_output_bytes": worker_raw,
        "owner_event_candidates": owner_candidates,
        "role_manifest": role_manifest,
    }
    yield kwargs
    output_session.close()
    os.close(fd)


def test_positive_authorities_issue_and_independently_replay(
    positive, monkeypatch
) -> None:
    original_validate = v2._validate_positive_context  # noqa: SLF001
    validation_calls = 0

    def counted_validate(**kwargs):
        nonlocal validation_calls
        validation_calls += 1
        return original_validate(**kwargs)

    monkeypatch.setattr(v2, "_validate_positive_context", counted_validate)
    issued = v2.issue_k7_occurrence_cutoff_semantic_authorities_v2(**positive)
    assert validation_calls == 1
    replayed = v2.replay_k7_occurrence_cutoff_semantic_authorities_v2(
        issued, **positive
    )
    assert validation_calls == 2
    assert replayed.bundle_id == issued.bundle_id
    occurrence = issued.occurrence_authority.to_document()
    cutoff = issued.cutoff_authority.to_document()
    assert occurrence["owner_partial_transcript_chain_semantics_replayed"] is True
    assert occurrence["owner_event_candidate_semantic_authority_verified"] is True
    assert occurrence["terminal_status"] == "CHILD_ACTION_ROW_CAP_EXCEEDED"
    assert occurrence["terminal_kind"] == "COMPLETED"
    assert occurrence["route_attempt_outcome"] == "FAILURE"
    assert (
        occurrence["route_attempt_count"],
        occurrence["route_success_count"],
        occurrence["route_failure_count"],
    ) == (1, 0, 1)
    assert occurrence["real_production_runtime_envelope_required"] is True
    assert cutoff["exact_source_sequences_independently_replayed"] is True
    assert cutoff["post_cutoff_business_work_absence_verified"] is True
    assert cutoff["post_cutoff_tail_output_byte_exclusion_verified"] is True
    assert len(cutoff["source_local_replays"]) == 9
    assert len(cutoff["post_cutoff_tail_components"]) == 4
    assert issued.to_document()["counter_records_issued"] is False


def test_authorities_are_issuer_owned_and_real_runtime_is_mandatory(positive) -> None:
    issued = v2.issue_k7_occurrence_cutoff_semantic_authorities_v2(**positive)
    with pytest.raises(v2.ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error, match="caller-minted"):
        replace(issued.occurrence_authority, _issuer=object())
    bad = dict(positive)
    bad["runtime_envelope"] = object()
    with pytest.raises(v2.ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error, match="real production runtime"):
        v2.issue_k7_occurrence_cutoff_semantic_authorities_v2(**bad)


def test_transplanted_tail_marker_is_rejected_after_structural_v1_accepts_it(positive) -> None:
    rows = list(positive["cutoff_attestation"].markers)
    rows[-1] = replace(rows[-1], subject_id=_id("foreign-tail"))
    structural = join_v1.freeze_operational_cutoff_attestation_v1(
        identity_join=positive["identity_join"],
        receipt_set=positive["receipt_set"],
        markers=tuple(rows),
    )
    bad = dict(positive)
    bad["cutoff_attestation"] = structural
    with pytest.raises(v2.ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error, match="independently replayed source events"):
        v2.issue_k7_occurrence_cutoff_semantic_authorities_v2(**bad)


def test_independently_held_output_cutoff_cannot_hide_a_source_event(positive) -> None:
    bundle = positive["output_bundle"]
    document = loads_canonical_json(bundle.cutoff_component.raw_bytes)
    assert type(document) is dict
    document["operational_cutoff_sequence"] -= 1
    forged_raw = output_test._refreeze(document, output_v2.CUTOFF_SCHEMA_ID)  # noqa: SLF001
    forged_document = loads_canonical_json(forged_raw)
    assert type(forged_document) is dict
    forged_component = resolution_v2.SharedResourceEvidenceComponentV2(
        bundle.cutoff_component.component_key,
        bundle.cutoff_component.source_schema_id,
        forged_document["operational_cutoff_attestation_id"],
        hashlib.sha256(forged_raw).hexdigest(),
        forged_raw,
    )
    forged_bundle = replace(
        bundle,
        _issuer=output_v2._BUNDLE_ISSUER,  # noqa: SLF001 - attack fixture
        cutoff_component=forged_component,
    )
    bad = dict(positive)
    bad["output_bundle"] = forged_bundle
    with pytest.raises(v2.ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error, match="source bytes failed independent replay"):
        v2.issue_k7_occurrence_cutoff_semantic_authorities_v2(**bad)


def test_stale_v3_occurrence_identity_is_rejected(positive) -> None:
    source = positive["source_envelope"]
    original = source.occurrence_id
    object.__setattr__(source, "occurrence_id", _id("stale-logical-occurrence"))
    try:
        with pytest.raises(v2.ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error, match="nine source-local|stale"):
            v2.issue_k7_occurrence_cutoff_semantic_authorities_v2(**positive)
    finally:
        object.__setattr__(source, "occurrence_id", original)


def test_foreign_role_manifest_archive_and_owner_candidate_are_rejected(positive) -> None:
    manifest = positive["role_manifest"]
    foreign_manifest = replace(
        manifest,
        _issuer=role_manifest_v2._MANIFEST_ISSUER,  # noqa: SLF001 - attack
        source_snapshot_id=_id("foreign-source-snapshot"),
    )
    bad = dict(positive)
    bad["role_manifest"] = foreign_manifest
    with pytest.raises(
        v2.ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error,
        match="owner event candidate semantic authority failed replay",
    ):
        v2.issue_k7_occurrence_cutoff_semantic_authorities_v2(**bad)

    candidates = positive["owner_event_candidates"]
    crossed_binding = replace(
        candidates.execution_binding,
        _issuer=owner_events_v1._BINDING_ISSUER,  # noqa: SLF001 - attack
        source_snapshot_id=_id("transplanted-candidate-source"),
    )
    crossed_candidates = replace(
        candidates,
        _issuer=owner_events_v1._SET_ISSUER,  # noqa: SLF001 - attack
        execution_binding=crossed_binding,
    )
    bad = dict(positive)
    bad["owner_event_candidates"] = crossed_candidates
    with pytest.raises(
        v2.ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error,
        match="crossed transcript/runtime/business/source identity",
    ):
        v2.issue_k7_occurrence_cutoff_semantic_authorities_v2(**bad)


def test_operational_output_bytes_cannot_be_transplanted_or_rewritten(positive) -> None:
    bad = dict(positive)
    raw = positive["operational_output_bytes"]
    bad["operational_output_bytes"] = raw[:-1] + bytes((raw[-1] ^ 1,))
    with pytest.raises(
        v2.ConstructionOccurrenceIdentityCutoffSemanticAuthorityV2Error,
        match="operational output or embedded business result failed public replay",
    ):
        v2.issue_k7_occurrence_cutoff_semantic_authorities_v2(**bad)
