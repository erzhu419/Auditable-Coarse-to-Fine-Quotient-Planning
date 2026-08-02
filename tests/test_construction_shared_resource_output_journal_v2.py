from __future__ import annotations

import hashlib
import inspect
import os
from pathlib import Path

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_output_journal_v2 as v2
from acfqp import construction_shared_resource_resolution_v2 as resolution_v2
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    loads_canonical_json,
)


def _cid(index: int) -> str:
    return f"{index:064x}"


def _business_bytes(payload: str = "answer") -> bytes:
    return canonical_json_bytes(
        {"artifact_role": v2.BUSINESS_ROLE, "payload": payload}
    )


def _renderer(candidate: int) -> dict[str, bytes]:
    return {
        role: canonical_json_bytes(
            {
                "artifact_role": role,
                "io.output_bytes": candidate,
                "payload": f"payload:{role}",
            }
        )
        for role in v2.BROKER_ROLE_ORDER
    }


def _open_directory(path: Path) -> int:
    return os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)


def _commit(fd: int, *, offset: int = 0) -> v2.WorkerBusinessResultCommitV2:
    return v2.commit_worker_business_result_v2(
        output_directory_fd=fd,
        payload_bytes=_business_bytes(),
        live_envelope_id=_cid(10 + offset),
        occurrence_id=_cid(11 + offset),
        route_attempt_id=_cid(12 + offset),
        decision_point_id=_cid(13 + offset),
        measurement_window_id=_cid(14 + offset),
        operational_cutoff_id=_cid(15 + offset),
        measurement_start_sequence=70,
        worker_commit_observation_id=_cid(16 + offset),
    )


def _open_session(
    fd: int,
    commit: v2.WorkerBusinessResultCommitV2,
    *,
    offset: int = 0,
) -> v2.BrokerDurableOutputSessionV2:
    return v2.open_broker_durable_output_session_v2(
        output_directory_fd=fd,
        business_commit=commit,
        worker_reap_observation_id=_cid(30 + offset),
        business_reap_observation_id=_cid(31 + offset),
        child_cgroup_empty_observation_id=_cid(32 + offset),
        broker_outside_child_cgroup_observation_id=_cid(33 + offset),
        exclusive_writer_observation_id=_cid(34 + offset),
    )


def _bundle(tmp_path: Path) -> tuple[
    int, v2.BrokerDurableOutputSessionV2, v2.OutputRawEvidenceBundleV2
]:
    fd = _open_directory(tmp_path)
    commit = _commit(fd)
    session = _open_session(fd, commit)
    bundle = session.finalize_v2(renderer=_renderer)
    return fd, session, bundle


def _raw_kwargs(bundle: v2.OutputRawEvidenceBundleV2) -> dict[str, bytes]:
    return {
        "fixed_point_bytes": bundle.fixed_point_component.raw_bytes,
        "exclusive_writer_bytes": bundle.exclusive_writer_component.raw_bytes,
        "cutoff_bytes": bundle.cutoff_component.raw_bytes,
        "output_manifest_bytes": bundle.output_manifest_component.raw_bytes,
    }


def _document(raw: bytes) -> dict[str, object]:
    value = loads_canonical_json(raw)
    assert type(value) is dict
    return value


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


def test_output_domains_are_central_and_role_separated() -> None:
    assert set(v2.REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
    assert len(v2.REQUESTED_PHASE3E_DOMAIN_TAGS) == len(
        set(v2.REQUESTED_PHASE3E_DOMAIN_TAGS)
    )


def test_durable_eight_role_fixed_point_uses_exact_new_extents(
    tmp_path: Path,
) -> None:
    fd, session, bundle = _bundle(tmp_path)
    try:
        names = set(os.listdir(fd))
        assert names == {v2.ROLE_FILENAMES[role] for role in v2.ROLE_ORDER}
        exact_extent_sum = sum(
            os.stat(name, dir_fd=fd, follow_symlinks=False).st_size
            for name in names
        )
        assert bundle.raw_replay.raw_output_bytes == exact_extent_sum
        assert bundle.raw_replay.semantic_source_verified is False
        assert bundle.raw_replay.counter_record_issuance_authorized is False
        manifest = _document(bundle.output_manifest_component.raw_bytes)
        assert manifest["required_role_order"] == list(v2.ROLE_ORDER)
        assert manifest["raw_derived_output_bytes"] == exact_extent_sum
        assert manifest["nested_serialized_aliases_charged_separately"] is False
        assert session.state is v2.OutputFinalizationStateV2.FINALIZED
    finally:
        session.close()
        os.close(fd)


def test_components_match_output_resolution_catalogue(tmp_path: Path) -> None:
    fd, session, bundle = _bundle(tmp_path)
    try:
        source = bundle.live_source_v2()
        contract = next(
            row
            for row in resolution_v2.official_shared_resource_resolution_catalogue_v2()
            if row.path == v2.OUTPUT_PATH
        )
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
            (source,),
        )
        result = resolution_v2.verify_v075_k7_shared_resource_semantics_v2(
            envelope
        )
        row = next(item for item in result.resolutions if item.path == v2.OUTPUT_PATH)
        assert row.missing_component_keys == ()
        assert row.exact_value is None
        assert row.pending_reason is (
            resolution_v2.SharedResourcePendingReasonV2
            .SEMANTIC_REPLAYER_NOT_INSTALLED
        )
    finally:
        session.close()
        os.close(fd)


def test_public_api_accepts_no_output_total_or_extent(tmp_path: Path) -> None:
    assert "total" not in inspect.signature(
        v2.commit_worker_business_result_v2
    ).parameters
    assert "byte_count" not in inspect.signature(
        v2.commit_worker_business_result_v2
    ).parameters
    assert "total" not in inspect.signature(
        v2.BrokerDurableOutputSessionV2.finalize_v2
    ).parameters
    assert not hasattr(v2, "CounterRecordV6")
    assert not hasattr(v2, "materialize_counter_records_v6")


@pytest.mark.parametrize("variant", ["missing", "extra", "reordered"])
def test_renderer_role_set_must_be_exact(
    tmp_path: Path, variant: str
) -> None:
    fd = _open_directory(tmp_path)
    commit = _commit(fd)
    session = _open_session(fd, commit)

    def forged(candidate: int) -> dict[str, bytes]:
        rows = _renderer(candidate)
        if variant == "missing":
            rows.pop(v2.BROKER_ROLE_ORDER[0])
        elif variant == "extra":
            rows["EXTRA_ROLE"] = canonical_json_bytes(
                {"artifact_role": "EXTRA_ROLE"}
            )
        else:
            first = rows.pop(v2.BROKER_ROLE_ORDER[0])
            rows[v2.BROKER_ROLE_ORDER[0]] = first
        return rows

    try:
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="duplicate, missing, extra, or reordered role",
        ):
            session.finalize_v2(renderer=forged)
        assert session.state is v2.OutputFinalizationStateV2.FAILED
    finally:
        session.close()
        os.close(fd)


def test_same_candidate_self_reference_instability_is_rejected(
    tmp_path: Path,
) -> None:
    fd = _open_directory(tmp_path)
    commit = _commit(fd)
    session = _open_session(fd, commit)
    calls = 0

    def unstable(candidate: int) -> dict[str, bytes]:
        nonlocal calls
        calls += 1
        rows = _renderer(candidate)
        role = v2.BROKER_ROLE_ORDER[0]
        rows[role] = canonical_json_bytes(
            {
                "artifact_role": role,
                "io.output_bytes": candidate,
                "nonce": calls,
            }
        )
        return rows

    try:
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="unstable for one candidate",
        ):
            session.finalize_v2(renderer=unstable)
    finally:
        session.close()
        os.close(fd)


def test_nonconvergent_self_reference_hits_finite_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fd = _open_directory(tmp_path)
    commit = _commit(fd)
    session = _open_session(fd, commit)
    monkeypatch.setattr(v2, "MAX_FIXED_POINT_ITERATIONS", 3)

    def increasing(candidate: int) -> dict[str, bytes]:
        rows = _renderer(candidate)
        role = v2.BROKER_ROLE_ORDER[0]
        rows[role] = canonical_json_bytes(
            {
                "artifact_role": role,
                "io.output_bytes": candidate,
                "padding": "x" * (candidate + 1),
            }
        )
        return rows

    try:
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="did not converge",
        ):
            session.finalize_v2(renderer=increasing)
    finally:
        session.close()
        os.close(fd)


def test_p_directory_entry_replacement_is_detected(tmp_path: Path) -> None:
    fd = _open_directory(tmp_path)
    commit = _commit(fd)
    session = _open_session(fd, commit)
    replaced = False

    def replacing_renderer(candidate: int) -> dict[str, bytes]:
        nonlocal replaced
        if not replaced:
            replaced = True
            os.unlink(v2.ROLE_FILENAMES[v2.BUSINESS_ROLE], dir_fd=fd)
            writer = os.open(
                v2.ROLE_FILENAMES[v2.BUSINESS_ROLE],
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
                0o400,
                dir_fd=fd,
            )
            try:
                replacement = _business_bytes("mutate")
                os.write(writer, replacement)
                os.fsync(writer)
            finally:
                os.close(writer)
            os.fsync(fd)
        return _renderer(candidate)

    try:
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="P mutation or replacement",
        ):
            session.finalize_v2(renderer=replacing_renderer)
    finally:
        session.close()
        os.close(fd)


def test_overlapping_broker_writer_authority_is_rejected(tmp_path: Path) -> None:
    fd = _open_directory(tmp_path)
    commit = _commit(fd)
    first = _open_session(fd, commit)
    try:
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="overlapping or prior broker writer",
        ):
            _open_session(fd, commit, offset=100)
    finally:
        first.close()
        os.close(fd)


def test_duplicate_reap_or_writer_observation_is_rejected(tmp_path: Path) -> None:
    fd = _open_directory(tmp_path)
    commit = _commit(fd)
    try:
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="observations are duplicated",
        ):
            v2.open_broker_durable_output_session_v2(
                output_directory_fd=fd,
                business_commit=commit,
                worker_reap_observation_id=_cid(90),
                business_reap_observation_id=_cid(90),
                child_cgroup_empty_observation_id=_cid(91),
                broker_outside_child_cgroup_observation_id=_cid(92),
                exclusive_writer_observation_id=_cid(93),
            )
    finally:
        os.close(fd)


def test_unfsynced_or_replaced_inode_evidence_is_rejected(tmp_path: Path) -> None:
    fd, session, bundle = _bundle(tmp_path)
    try:
        document = _document(bundle.exclusive_writer_component.raw_bytes)
        rows = document["durable_write_events"]
        assert type(rows) is list
        rows[1]["file_fsync_completed"] = False
        kwargs = _raw_kwargs(bundle)
        kwargs["exclusive_writer_bytes"] = _refreeze(
            document, v2.EXCLUSIVE_WRITER_SCHEMA_ID
        )
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="fsync evidence changed",
        ):
            v2.replay_output_raw_evidence_v2(**kwargs)

        document = _document(bundle.output_manifest_component.raw_bytes)
        rows = document["role_artifacts"]
        assert type(rows) is list
        rows[1]["artifact_identity"] = dict(rows[0]["artifact_identity"])
        rows[1]["artifact_identity"]["byte_extent"] = rows[1][
            "artifact_byte_extent"
        ]
        kwargs = _raw_kwargs(bundle)
        kwargs["output_manifest_bytes"] = _refreeze(
            document, v2.OUTPUT_MANIFEST_SCHEMA_ID
        )
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="alias one inode",
        ):
            v2.replay_output_raw_evidence_v2(**kwargs)
    finally:
        session.close()
        os.close(fd)


@pytest.mark.parametrize("delta", [-1, 1])
def test_output_extent_under_or_double_count_is_rejected(
    tmp_path: Path, delta: int
) -> None:
    fd, session, bundle = _bundle(tmp_path)
    try:
        document = _document(bundle.output_manifest_component.raw_bytes)
        document["raw_derived_output_bytes"] += delta
        kwargs = _raw_kwargs(bundle)
        kwargs["output_manifest_bytes"] = _refreeze(
            document, v2.OUTPUT_MANIFEST_SCHEMA_ID
        )
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="under-counted, double-counted",
        ):
            v2.replay_output_raw_evidence_v2(**kwargs)
    finally:
        session.close()
        os.close(fd)


@pytest.mark.parametrize("variant", ["missing", "duplicate", "extra"])
def test_raw_manifest_rejects_missing_duplicate_or_extra_role(
    tmp_path: Path, variant: str
) -> None:
    fd, session, bundle = _bundle(tmp_path)
    try:
        document = _document(bundle.output_manifest_component.raw_bytes)
        rows = document["role_artifacts"]
        assert type(rows) is list
        if variant == "missing":
            rows.pop()
        elif variant == "duplicate":
            rows[1]["artifact_role"] = rows[0]["artifact_role"]
        else:
            rows.append(dict(rows[-1]))
        kwargs = _raw_kwargs(bundle)
        kwargs["output_manifest_bytes"] = _refreeze(
            document, v2.OUTPUT_MANIFEST_SCHEMA_ID
        )
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="missing or extra role|writer, order",
        ):
            v2.replay_output_raw_evidence_v2(**kwargs)
    finally:
        session.close()
        os.close(fd)


def test_cutoff_cannot_hide_one_durable_role(tmp_path: Path) -> None:
    fd, session, bundle = _bundle(tmp_path)
    try:
        document = _document(bundle.cutoff_component.raw_bytes)
        index = document["global_event_index"]
        assert type(index) is list and len(index) == 8
        index.pop()
        document["global_event_count"] = 7
        document["operational_cutoff_sequence"] -= 1
        kwargs = _raw_kwargs(bundle)
        kwargs["cutoff_bytes"] = _refreeze(document, v2.CUTOFF_SCHEMA_ID)
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="cutoff hides",
        ):
            v2.replay_output_raw_evidence_v2(**kwargs)
    finally:
        session.close()
        os.close(fd)


def test_cross_component_occurrence_identity_is_rejected(tmp_path: Path) -> None:
    fd, session, bundle = _bundle(tmp_path)
    try:
        document = _document(bundle.fixed_point_component.raw_bytes)
        document["occurrence_id"] = _cid(999)
        kwargs = _raw_kwargs(bundle)
        kwargs["fixed_point_bytes"] = _refreeze(
            document, v2.FIXED_POINT_SCHEMA_ID
        )
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="crossed occurrence/window identity",
        ):
            v2.replay_output_raw_evidence_v2(**kwargs)
    finally:
        session.close()
        os.close(fd)


def test_worker_commit_rejects_nonempty_directory_and_wrong_role(
    tmp_path: Path,
) -> None:
    fd = _open_directory(tmp_path)
    try:
        existing = os.open(
            "existing",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
            0o600,
            dir_fd=fd,
        )
        os.close(existing)
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="fresh empty output directory",
        ):
            _commit(fd)
    finally:
        os.close(fd)

    second = tmp_path.parent / f"{tmp_path.name}-wrong-role"
    second.mkdir()
    fd = _open_directory(second)
    try:
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="role label differs",
        ):
            v2.commit_worker_business_result_v2(
                output_directory_fd=fd,
                payload_bytes=canonical_json_bytes(
                    {"artifact_role": "WRONG_ROLE"}
                ),
                live_envelope_id=_cid(1),
                occurrence_id=_cid(2),
                route_attempt_id=_cid(3),
                decision_point_id=_cid(4),
                measurement_window_id=_cid(5),
                operational_cutoff_id=_cid(6),
                measurement_start_sequence=0,
                worker_commit_observation_id=_cid(7),
            )
    finally:
        os.close(fd)
