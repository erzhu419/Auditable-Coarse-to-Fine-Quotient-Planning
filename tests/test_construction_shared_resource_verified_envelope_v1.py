from __future__ import annotations

from dataclasses import fields
import os
from pathlib import Path

import pytest

from acfqp import construction_shared_resource_common_journal_v2 as common_v2
from acfqp import construction_shared_resource_live_envelope_v3 as live_v3
from acfqp import construction_shared_resource_resolution_v2 as resolution_v2
from acfqp import construction_shared_resource_transfer_mount_journal_v2 as transfer_v2
from acfqp import construction_shared_resource_verified_envelope_v1 as verified_v1
from acfqp import construction_shared_resource_working_process_evidence_v2 as working_v2
from tests import test_construction_shared_resource_common_journal_v2 as common_test
from tests import test_construction_shared_resource_live_envelope_v3 as live_test
from tests import test_construction_shared_resource_output_journal_v2 as output_test
from tests import test_construction_shared_resource_transfer_mount_journal_v2 as transfer_test
from tests import test_construction_shared_resource_working_process_evidence_v2 as working_test


def _cid(index: int) -> str:
    return f"{index:064x}"


def _common_bundle() -> common_v2.CommonRawEvidenceBundleV2:
    session = common_v2.CommonJournalSessionV2(
        live_envelope_id=_cid(110),
        occurrence_id=_cid(111),
        route_attempt_id=_cid(112),
        decision_point_id=_cid(113),
        measurement_window_id=_cid(114),
        operational_cutoff_id=_cid(2115),
        measurement_start_sequence=50,
        source_sites=common_test._sites(),  # noqa: SLF001 - raw fixture
        hash_purposes=common_test._hash_purposes(),  # noqa: SLF001
        integrity_obligations=common_test._integrity_obligations(),  # noqa: SLF001
        protocol_obligations=common_test._protocol_obligations(),  # noqa: SLF001
    )
    session.record_hash_invocation_v2(
        purpose_key="business.content_id",
        site_key="hash.site",
        authenticated_broker_observation_id=_cid(2200),
        input_artifact_ids=(_cid(2201),),
        output_artifact_ids=(_cid(2202),),
    )
    session.record_integrity_check_v2(
        obligation_key="artifact.digest_matches",
        site_key="integrity.site",
        outcome=common_v2.NamedObligationOutcomeV2.PASS,
        authenticated_broker_observation_id=_cid(2203),
        input_artifact_ids=(_cid(2204),),
        output_artifact_ids=(_cid(2205),),
    )
    session.record_protocol_check_v2(
        obligation_key="broker.frame_order",
        site_key="protocol.site",
        outcome=common_v2.NamedObligationOutcomeV2.PASS,
        authenticated_broker_observation_id=_cid(2206),
        input_artifact_ids=(_cid(2207),),
        output_artifact_ids=(_cid(2208),),
    )
    return session.close_v2()


def _transfer_bundle() -> transfer_v2.TransferMountRawEvidenceBundleV2:
    session = transfer_v2.TransferMountJournalSessionV2(
        live_envelope_id=_cid(110),
        occurrence_id=_cid(111),
        route_attempt_id=_cid(112),
        decision_point_id=_cid(113),
        measurement_window_id=_cid(114),
        operational_cutoff_id=_cid(3115),
        measurement_start_sequence=40,
        purposes=transfer_test._purposes(),  # noqa: SLF001 - raw fixture
    )
    payload = session.register_payload_v2(
        payload_role="SEALED_PAYLOAD", raw_bytes=b"abcdef"
    )
    session.record_read_v2(
        payload=payload,
        purpose_key="read.broker",
        byte_offset=0,
        returned_bytes=b"abcdef",
    )
    session.record_stage_v2(payload=payload, purpose_key="stage.worker")
    interval = session.open_mount_visibility_v2(
        payload=payload, purpose_key="mount.worker"
    )
    session.close_mount_visibility_v2(interval)
    return session.close_v2()


def _working_bundle(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> working_v2.WorkingProcessRawEvidenceBundleV2:
    def aligned_open(
        cgroup: working_test._FakeCgroup,  # noqa: SLF001 - raw fixture
    ) -> working_v2.WorkingProcessEvidenceSessionV2:
        return working_v2.open_working_process_evidence_session_v2(
            live_envelope_id=_cid(110),
            occurrence_id=_cid(111),
            route_attempt_id=_cid(112),
            decision_point_id=_cid(113),
            measurement_window_id=_cid(114),
            measurement_start_sequence=17,
            memory_peak_fd=cgroup.peak_fd,
            cgroup_directory_fd=cgroup.directory_fd,
        )

    monkeypatch.setattr(working_test, "_open_session", aligned_open)
    return working_test._exact_bundle(root)  # noqa: SLF001 - raw fixture


def _real_envelope(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> live_v3.K7ProductionSharedResourceEnvelopeV3:
    output_root = root / "output"
    working_root = root / "working"
    output_root.mkdir()
    working_root.mkdir()
    common = _common_bundle()
    transfer = _transfer_bundle()
    working = _working_bundle(working_root, monkeypatch)
    output_fd, output_session, output = output_test._production_bundle(  # noqa: SLF001
        output_root, monkeypatch, f"verified-nine:{root.name}"
    )
    try:
        by_path = {
            source.path: source
            for source in (
                *common.live_sources_v2(),
                *transfer.live_sources_v2(),
                output.live_source_v2(),
                *working.live_sources_v2(),
            )
        }
        return live_v3.freeze_k7_production_shared_resource_envelope_v3(
            production_runtime_envelope_id=_cid(110),
            occurrence_id=_cid(111),
            route_attempt_id=_cid(112),
            decision_point_id=_cid(113),
            measurement_window_id=_cid(114),
            production_runtime_replay_id=_cid(116),
            terminal_closure_observation_id=_cid(117),
            sources=tuple(
                by_path[path] for path in resolution_v2.SHARED_RESOURCE_PATHS
            ),
        )
    finally:
        output_session.close()
        os.close(output_fd)


def test_real_nine_sources_replay_and_authorize_materialization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _real_envelope(tmp_path, monkeypatch)
    verified = verified_v1.verify_k7_production_shared_resource_envelope_exact_v1(
        source
    )
    assert tuple(row.path for row in verified.authorizations) == (
        resolution_v2.SHARED_RESOURCE_PATHS
    )
    assert len({row.authorization_id for row in verified.authorizations}) == 9
    assert {path: row.exact_value for path, row in verified.by_path.items()} == {
        "common.hash_invocations": 1,
        "common.integrity_checks": 1,
        "common.protocol_checks": 1,
        "io.mounted_bytes_peak": 6,
        "io.output_bytes": verified.by_path["io.output_bytes"].exact_value,
        "io.read_bytes": 6,
        "io.staged_bytes": 6,
        "memory.working_bytes_peak": 8192,
        "process.launches": 2,
    }
    document = verified.to_document()
    assert document["source_v3_envelope_id"] == source.envelope_id
    assert document["production_runtime_envelope_id"] == _cid(110)
    assert document["production_runtime_replay_id"] == _cid(116)
    assert document["terminal_closure_observation_id"] == _cid(117)
    assert document["fixed_semantic_replay_complete"] is True
    assert document["counter_record_materialization_eligible"] is True
    assert document["counter_records_issued"] is False
    assert document["formal_vector_authorized"] is False
    assert len(
        {
            (row.source_local_start_sequence, row.source_local_cutoff_sequence)
            for row in verified.authorizations
        }
    ) > 1
    replayed_again = (
        verified_v1.verify_k7_production_shared_resource_envelope_exact_v1(source)
    )
    assert replayed_again.verified_envelope_id == verified.verified_envelope_id
    assert tuple(row.authorization_id for row in replayed_again.authorizations) == tuple(
        row.authorization_id for row in verified.authorizations
    )


def test_v3_shape_without_real_semantics_cannot_be_promoted() -> None:
    shaped_only = live_test._freeze(live_test._sources())  # noqa: SLF001
    with pytest.raises(
        verified_v1.ConstructionSharedResourceVerifiedEnvelopeV1Error,
        match="exact semantic replay failed",
    ):
        verified_v1.verify_k7_production_shared_resource_envelope_exact_v1(
            shaped_only
        )


def test_postissuance_source_mutation_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verified = verified_v1.verify_k7_production_shared_resource_envelope_exact_v1(
        _real_envelope(tmp_path, monkeypatch)
    )
    source = verified.source_envelope.bound_sources[0].source
    object.__setattr__(source, "covered_cutoff_sequence", source.covered_cutoff_sequence + 1)
    with pytest.raises(
        verified_v1.ConstructionSharedResourceVerifiedEnvelopeV1Error,
        match="mutated|transplanted",
    ):
        verified.to_document()


def test_duplicate_and_context_transplant_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verified = verified_v1.verify_k7_production_shared_resource_envelope_exact_v1(
        _real_envelope(tmp_path, monkeypatch)
    )
    original = verified.authorizations
    object.__setattr__(verified, "authorizations", original[:-1] + (original[0],))
    with pytest.raises(
        verified_v1.ConstructionSharedResourceVerifiedEnvelopeV1Error,
        match="ordered distinct nine-path set",
    ):
        verified.to_document()
    object.__setattr__(verified, "authorizations", original)
    object.__setattr__(original[0], "source_v3_envelope_id", _cid(9999))
    with pytest.raises(
        verified_v1.ConstructionSharedResourceVerifiedEnvelopeV1Error,
        match="mutated|transplanted",
    ):
        verified.to_document()


def test_authorizations_are_issuer_owned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verified = verified_v1.verify_k7_production_shared_resource_envelope_exact_v1(
        _real_envelope(tmp_path, monkeypatch)
    )
    row = verified.authorizations[0]
    arguments = tuple(getattr(row, item.name) for item in fields(row))
    with pytest.raises(
        verified_v1.ConstructionSharedResourceVerifiedEnvelopeV1Error,
        match="caller-minted",
    ):
        verified_v1.VerifiedSharedResourcePathAuthorizationV1(
            object(), *arguments
        )


def test_successor_domains_are_role_separated_and_centrally_registered() -> None:
    assert verified_v1.REQUESTED_PHASE3E_DOMAIN_TAGS == (
        "acfqp:construction-shared-resource-path-exact-authorization:v1",
        "acfqp:v075-k7-verified-nine-shared-resource-envelope:v1",
    )
    assert len(set(verified_v1.REQUESTED_PHASE3E_DOMAIN_TAGS)) == 2
