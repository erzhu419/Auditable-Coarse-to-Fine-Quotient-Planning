from __future__ import annotations

from copy import deepcopy
import hashlib
import inspect
import os
from pathlib import Path
import stat

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_output_journal_v2 as v2
from acfqp import construction_shared_resource_resolution_v2 as resolution_v2
from acfqp import v075_k7_authenticated_broker_channel_v2 as channel_v2
from acfqp import v075_k7_broker_worker_entry_v1 as worker_v1
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
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


class _FakeRequest:
    def __init__(self, label: str) -> None:
        self.request_id = hashlib.sha256(f"request:{label}".encode()).hexdigest()
        self.route_identity = type(
            "Route",
            (),
            {
                "route_identity_id": hashlib.sha256(
                    f"route:{label}".encode()
                ).hexdigest()
            },
        )()

    def _assert_current(self) -> None:
        return None


class _FakeReplay:
    def __init__(self, label: str) -> None:
        self.request = _FakeRequest(label)
        self.replay_id = hashlib.sha256(f"replay:{label}".encode()).hexdigest()
        self.profile_closure = type(
            "Closure", (), {"_assert_current": lambda self: None}
        )()


class _FakeBusinessBundle:
    def __init__(self, label: str) -> None:
        self.bundle_id = hashlib.sha256(f"bundle:{label}".encode()).hexdigest()
        self._document = {
            "schema": "acfqp.test_business_bundle.v1",
            "child_business_bundle_id": self.bundle_id,
            "payload": {"label": label},
        }
        self.canonical_bytes = canonical_json_bytes(self._document)

    def to_document(self) -> dict[str, object]:
        return deepcopy(self._document)


def _worker_authority(
    monkeypatch: pytest.MonkeyPatch, label: str
) -> tuple[
    _FakeReplay,
    _FakeBusinessBundle,
    ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
]:
    replay = _FakeReplay(label)
    bundle = _FakeBusinessBundle(label)
    monkeypatch.setattr(
        worker_v1.portable_replay,
        "V075K7SuccessorPortableRequestReplayV1",
        _FakeReplay,
    )

    def verify(*, raw: bytes, expected_request_replay: _FakeReplay):
        if type(expected_request_replay) is not _FakeReplay:
            raise ValueError("crossed fake request replay")
        if raw != bundle.canonical_bytes:
            raise ValueError("crossed fake business bundle")
        return bundle

    monkeypatch.setattr(
        worker_v1.business_bundle,
        "verify_v075_k7_child_business_bundle_public_bytes_v1",
        verify,
    )
    binding = ipc_v1.K7OuterAttemptBrokerIPCBindingV1(
        replay.request.request_id,
        replay.request.route_identity.route_identity_id,
        hashlib.sha256(f"spec:{label}".encode()).hexdigest(),
        hashlib.sha256(f"nonce:{label}".encode()).hexdigest(),
    )
    return replay, bundle, binding


def _authenticated_parent_output(
    *,
    binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
    output_byte_count: int,
    output_sha256: str,
) -> channel_v2.K7AuthenticatedBrokerFrameV2:
    raw = ipc_v1.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
        binding=binding,
        role=ipc_v1.K7OuterAttemptBrokerFrameRoleV1.PARENT_OUTPUT,
        payload={
            "output_byte_count": output_byte_count,
            "output_sha256": output_sha256,
        },
    )
    frame = ipc_v1.verify_v075_k7_outer_attempt_broker_ipc_frame_v1(
        raw=raw,
        expected_binding=binding,
        expected_role=ipc_v1.K7OuterAttemptBrokerFrameRoleV1.PARENT_OUTPUT,
    )
    return channel_v2.K7AuthenticatedBrokerFrameV2(
        channel_v2._FRAME_ISSUER,  # noqa: SLF001 - issuer-path fixture
        (1, 2, stat.S_IFSOCK | 0o600, os.geteuid(), os.getegid(), 0),
        (3, 4, stat.S_IFREG | 0o600, os.geteuid(), os.getegid(), 0),
        os.getpid(),
        os.geteuid(),
        os.getegid(),
        frame,
        hashlib.sha256(raw).hexdigest(),
        len(raw),
    )


def _worker_output_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    label: str,
) -> tuple[
    int,
    _FakeReplay,
    ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
    bytes,
]:
    replay, bundle, binding = _worker_authority(monkeypatch, label)
    output = worker_v1._freeze_output(  # noqa: SLF001
        request_replay=replay,
        binding=binding,
        bundle=bundle,
    )
    directory_fd = _open_directory(tmp_path)

    def test_filesystem_noreplace(
        directory: int, temporary_name: str, output_name: str
    ) -> None:
        try:
            os.stat(output_name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            os.rename(
                temporary_name,
                output_name,
                src_dir_fd=directory,
                dst_dir_fd=directory,
            )
            return
        raise FileExistsError(output_name)

    monkeypatch.setattr(
        worker_v1, "_rename_noreplace", test_filesystem_noreplace
    )
    worker_v1._commit_output(  # noqa: SLF001
        output=output,
        directory_fd=directory_fd,
    )
    raw = output.canonical_bytes
    return directory_fd, replay, binding, raw


def _production_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    label: str,
) -> tuple[
    int,
    v2.WorkerBusinessResultCommitV2,
    _FakeReplay,
    ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
    channel_v2.K7AuthenticatedBrokerFrameV2,
]:
    directory_fd, replay, binding, raw = _worker_output_candidate(
        tmp_path, monkeypatch, label
    )
    observation = _authenticated_parent_output(
        binding=binding,
        output_byte_count=len(raw),
        output_sha256=hashlib.sha256(raw).hexdigest(),
    )
    commit = _adopt_candidate(
        directory_fd=directory_fd,
        observation=observation,
        replay=replay,
        binding=binding,
    )
    return directory_fd, commit, replay, binding, observation


def _adopt_candidate(
    *,
    directory_fd: int,
    observation: channel_v2.K7AuthenticatedBrokerFrameV2,
    replay: _FakeReplay,
    binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
) -> v2.WorkerBusinessResultCommitV2:
    return v2.adopt_production_worker_operational_output_v2(
        output_directory_fd=directory_fd,
        authenticated_parent_output=observation,
        expected_request_replay=replay,
        expected_binding=binding,
        live_envelope_id=_cid(110),
        occurrence_id=_cid(111),
        route_attempt_id=_cid(112),
        decision_point_id=_cid(113),
        measurement_window_id=_cid(114),
        operational_cutoff_id=_cid(115),
        measurement_start_sequence=70,
    )


def _production_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    label: str,
) -> tuple[int, v2.BrokerDurableOutputSessionV2, v2.OutputRawEvidenceBundleV2]:
    directory_fd, commit, _replay, _binding, _observation = _production_commit(
        tmp_path, monkeypatch, label
    )
    session = _open_session(directory_fd, commit, offset=200)
    bundle = session.finalize_v2(renderer=_renderer)
    return directory_fd, session, bundle


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
    return v2.commit_synthetic_construction_first_role_v2(
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
            "proposed_contract_version",
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


def test_production_adopts_worker_operational_output_and_post_reap_seals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fd, commit, _replay, _binding, observation = _production_commit(
        tmp_path, monkeypatch, "production-adoption"
    )
    before = os.stat(worker_v1.OUTPUT_NAME, dir_fd=fd, follow_symlinks=False)
    assert set(os.listdir(fd)) == {worker_v1.OUTPUT_NAME}
    assert v2.ROLE_FILENAMES[v2.BUSINESS_ROLE] == worker_v1.OUTPUT_NAME
    assert stat.S_IMODE(before.st_mode) == 0o600
    adopted_reader = os.open(
        worker_v1.OUTPUT_NAME,
        os.O_RDONLY | os.O_CLOEXEC,
        dir_fd=fd,
    )
    try:
        adopted_document = _document(
            os.pread(adopted_reader, before.st_size, 0)
        )
    finally:
        os.close(adopted_reader)
    assert "artifact_role" not in adopted_document
    assert commit.production_semantic_eligible is True
    assert commit.authenticated_parent_output_observation_id == (
        observation.observation_id
    )
    with pytest.raises(
        v2.ConstructionSharedResourceOutputJournalV2Error,
        match="already consumed",
    ):
        _adopt_candidate(
            directory_fd=fd,
            observation=observation,
            replay=_replay,
            binding=_binding,
        )
    session = _open_session(fd, commit, offset=300)
    try:
        sealed = os.stat(
            worker_v1.OUTPUT_NAME, dir_fd=fd, follow_symlinks=False
        )
        assert (sealed.st_dev, sealed.st_ino) == (before.st_dev, before.st_ino)
        assert stat.S_IMODE(sealed.st_mode) == 0o400
        bundle = session.finalize_v2(renderer=_renderer)
        assert bundle.raw_replay.production_semantic_eligible is True
        assert bundle.raw_replay.synthetic_construction_only is False
        assert bundle.live_source_v2().path == v2.OUTPUT_PATH
        replayed = v2.replay_production_output_exact_semantic_evidence_v2(
            **_raw_kwargs(bundle)
        )
        assert replayed.raw_output_bytes == bundle.raw_replay.raw_output_bytes
        manifest = _document(bundle.output_manifest_component.raw_bytes)
        first = manifest["role_artifacts"][0]
        assert first["filename"] == worker_v1.OUTPUT_NAME
        assert first["writer_role"] == "WORKER"
        assert first["worker_created_and_durably_committed"] is True
        assert first["broker_post_reap_write_bits_removed"] is True
        assert first["production_semantic_eligible"] is True
        assert "business_result.json" not in os.listdir(fd)
    finally:
        session.close()
        os.close(fd)


@pytest.mark.parametrize("attack", ("replacement", "mutation"))
def test_production_adopted_inode_replacement_or_mutation_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
) -> None:
    fd, commit, _replay, _binding, _observation = _production_commit(
        tmp_path, monkeypatch, f"production-{attack}"
    )
    try:
        if attack == "replacement":
            reader = os.open(
                worker_v1.OUTPUT_NAME,
                os.O_RDONLY | os.O_CLOEXEC,
                dir_fd=fd,
            )
            try:
                raw = os.pread(reader, commit.artifact_byte_extent, 0)
            finally:
                os.close(reader)
            os.unlink(worker_v1.OUTPUT_NAME, dir_fd=fd)
            replacement = os.open(
                worker_v1.OUTPUT_NAME,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
                0o600,
                dir_fd=fd,
            )
            try:
                os.write(replacement, raw)
                os.fsync(replacement)
            finally:
                os.close(replacement)
        else:
            writer = os.open(
                worker_v1.OUTPUT_NAME,
                os.O_WRONLY | os.O_CLOEXEC,
                dir_fd=fd,
            )
            try:
                os.pwrite(writer, b"X", 0)
                os.fsync(writer)
            finally:
                os.close(writer)
        os.fsync(fd)
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="adopted first-role inode|pre-read P",
        ):
            _open_session(fd, commit, offset=400)
    finally:
        os.close(fd)


@pytest.mark.parametrize("attack", ("forged-frame", "wrong-request", "wrong-binding"))
def test_production_adoption_rejects_frame_request_or_binding_attack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
) -> None:
    fd, replay, binding, raw = _worker_output_candidate(
        tmp_path, monkeypatch, f"production-adoption-{attack}"
    )
    expected_replay = replay
    expected_binding = binding
    if attack == "forged-frame":
        observation = _authenticated_parent_output(
            binding=binding,
            output_byte_count=len(raw) + 1,
            output_sha256=hashlib.sha256(raw).hexdigest(),
        )
    else:
        observation = _authenticated_parent_output(
            binding=binding,
            output_byte_count=len(raw),
            output_sha256=hashlib.sha256(raw).hexdigest(),
        )
    if attack == "wrong-request":
        expected_replay = _FakeReplay("foreign-request")
    elif attack == "wrong-binding":
        expected_binding = ipc_v1.K7OuterAttemptBrokerIPCBindingV1(
            binding.request_id,
            binding.route_identity_id,
            _cid(880),
            _cid(881),
        )
    try:
        with pytest.raises(v2.ConstructionSharedResourceOutputJournalV2Error):
            _adopt_candidate(
                directory_fd=fd,
                observation=observation,
                replay=expected_replay,
                binding=expected_binding,
            )
    finally:
        os.close(fd)


def test_pre_reap_seal_and_synthetic_semantic_promotion_are_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    production_dir = tmp_path / "production"
    production_dir.mkdir()
    fd, commit, _replay, _binding, _observation = _production_commit(
        production_dir, monkeypatch, "production-pre-reap-seal"
    )
    try:
        os.chmod(worker_v1.OUTPUT_NAME, 0o400, dir_fd=fd)
        os.fsync(fd)
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="adopted first-role inode|retain exact worker write bits",
        ):
            _open_session(fd, commit, offset=500)
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="finalizer-owned",
        ):
            commit._event_document_after_reap_v2(  # noqa: SLF001
                object(),
                session_id=_cid(501),
                pre_seal_identity=commit.artifact_identity,
                sealed_identity=commit.artifact_identity,
                broker_removed_write_bits=True,
            )
    finally:
        os.close(fd)

    synthetic_dir = tmp_path / "synthetic"
    synthetic_dir.mkdir()
    synthetic_fd, synthetic_session, synthetic = _bundle(synthetic_dir)
    try:
        assert synthetic.raw_replay.production_semantic_eligible is False
        assert synthetic.raw_replay.synthetic_construction_only is True
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="cannot become an exact live source",
        ):
            synthetic.live_source_v2()
        with pytest.raises(
            v2.ConstructionSharedResourceOutputJournalV2Error,
            match="not exact-semantic eligible",
        ):
            v2.replay_production_output_exact_semantic_evidence_v2(
                **_raw_kwargs(synthetic)
            )
    finally:
        synthetic_session.close()
        os.close(synthetic_fd)


def test_components_match_output_resolution_catalogue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fd, session, bundle = _production_bundle(
        tmp_path, monkeypatch, "resolution-catalogue"
    )
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
    assert v2.PROPOSED_CONTRACT_VERSION == "2.0.20"
    assert v2.commit_worker_business_result_v2 is (
        v2.commit_synthetic_construction_first_role_v2
    )
    assert "total" not in inspect.signature(
        v2.commit_worker_business_result_v2
    ).parameters
    assert "byte_count" not in inspect.signature(
        v2.commit_worker_business_result_v2
    ).parameters
    assert "total" not in inspect.signature(
        v2.BrokerDurableOutputSessionV2.finalize_v2
    ).parameters
    adoption_parameters = inspect.signature(
        v2.adopt_production_worker_operational_output_v2
    ).parameters
    assert "payload_bytes" not in adoption_parameters
    assert "output_byte_count" not in adoption_parameters
    assert "output_sha256" not in adoption_parameters
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
        event_core = {
            "schema": "acfqp.construction_shared_resource_durable_write_event.v2",
            "schema_version": v2.SCHEMA_VERSION,
            "proposed_contract_version": v2.PROPOSED_CONTRACT_VERSION,
            "session_id": document["session_id"],
            **{
                key: value
                for key, value in rows[1].items()
                if key != "durable_write_event_id"
            },
        }
        rows[1]["durable_write_event_id"] = v2._hash(  # noqa: SLF001
            v2.DURABLE_WRITE_EVENT_V2_DOMAIN,
            event_core,
        )
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
            match="synthetic BUSINESS_RESULT role label",
        ):
            v2.commit_synthetic_construction_first_role_v2(
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
