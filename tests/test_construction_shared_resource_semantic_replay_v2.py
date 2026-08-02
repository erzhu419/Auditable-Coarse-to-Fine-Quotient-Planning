from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile

import pytest

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_output_journal_v2 as output_v2
from acfqp import construction_shared_resource_resolution_v2 as resolution_v2
from acfqp import construction_shared_resource_semantic_replay_v2 as replay_v2
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    loads_canonical_json,
)
from tests.test_construction_shared_resource_common_journal_v2 import (
    _bundle as common_bundle,
    _session as common_session,
)
from tests.test_construction_shared_resource_output_journal_v2 import (
    _bundle as synthetic_output_bundle,
    _production_bundle as production_output_bundle,
)
from tests.test_construction_shared_resource_transfer_mount_journal_v2 import (
    _closed_bundle as transfer_bundle,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:shared-resource-semantic-replay-test:v2\x00"
        + label.encode("ascii")
    ).hexdigest()
from tests.test_construction_shared_resource_working_process_evidence_v2 import (
    _FakeCgroup,
    _exact_bundle as working_bundle,
    _open_session as open_working_session,
)


def _source_with_components(
    source: resolution_v2.SharedResourceLiveSourceV2,
    components: tuple[resolution_v2.SharedResourceEvidenceComponentV2, ...],
) -> resolution_v2.SharedResourceLiveSourceV2:
    return resolution_v2.SharedResourceLiveSourceV2(
        source.live_envelope_id,
        source.occurrence_id,
        source.route_attempt_id,
        source.decision_point_id,
        source.measurement_window_id,
        source.operational_cutoff_id,
        source.path,
        source.exact_source_kind,
        source.provenance_claims,
        source.covered_start_sequence,
        source.covered_cutoff_sequence,
        components,
    )


def _replace_component(
    source: resolution_v2.SharedResourceLiveSourceV2,
    replacement: resolution_v2.SharedResourceEvidenceComponentV2,
) -> resolution_v2.SharedResourceLiveSourceV2:
    components = tuple(
        replacement if item.component_key == replacement.component_key else item
        for item in source.components
    )
    return _source_with_components(source, components)


def test_semantic_verifier_domain_is_centrally_registered() -> None:
    assert replay_v2.SEMANTIC_VERIFIER_V2_DOMAIN in PHASE3E_DOMAIN_TAGS


def test_all_nine_fixed_verifiers_replay_exact_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources = [
        *common_bundle().live_sources_v2(),
        *transfer_bundle().live_sources_v2(),
    ]
    with tempfile.TemporaryDirectory(
        prefix="acfqp-semantic-replay-", dir="/tmp"
    ) as raw_root:
        root = Path(raw_root)
        output_root = root / "output"
        working_root = root / "working"
        output_root.mkdir()
        working_root.mkdir()
        output_fd, output_session, output = production_output_bundle(
            output_root, monkeypatch, "semantic-replay"
        )
        try:
            sources.append(output.live_source_v2())
            working = working_bundle(working_root)
            sources.extend(working.live_sources_v2())
            results = {
                source.path: replay_v2.verify_shared_resource_source_exact_v2(
                    source
                )
                for source in sources
            }
        finally:
            output_session.close()
            os.close(output_fd)
    assert set(results) == set(resolution_v2.SHARED_RESOURCE_PATHS)
    assert {path: result.exact_value for path, result in results.items()} == {
        "common.hash_invocations": 2,
        "common.integrity_checks": 2,
        "common.protocol_checks": 1,
        "io.mounted_bytes_peak": 6,
        "io.output_bytes": output.raw_replay.raw_output_bytes,
        "io.read_bytes": 6,
        "io.staged_bytes": 12,
        "memory.working_bytes_peak": 8192,
        "process.launches": 2,
    }
    assert results["io.mounted_bytes_peak"].reducer is ReducerEnum.MAX
    assert results["memory.working_bytes_peak"].reducer is ReducerEnum.MAX
    assert all(
        result.reducer is ReducerEnum.SUM
        for path, result in results.items()
        if path not in {"io.mounted_bytes_peak", "memory.working_bytes_peak"}
    )
    for result in results.values():
        document = result.to_internal_document()
        assert document["semantic_source_verified"] is True
        assert document["source_artifact_ids_replayed"] is True
        assert document["source_bytes_replayed"] is True
        assert document["provenance_replayed"] is True
        assert document["complete_window_verified"] is True
        assert document["identity_binding_verified"] is True
        assert document["reducer_verified"] is True
        assert document["raw_replayer_invoked"] is True
        assert document["counter_record_issuance_authorized"] is False
        assert document["counter_record_issued"] is False
        assert document["work_vector_issued"] is False
        assert document["comparison_vector_issued"] is False
        assert document["formal_vector_authorized"] is False
        assert document["formal_artifact_id"] is None


def test_output_stays_typed_pending_without_real_worker_adoption(
    tmp_path: Path,
) -> None:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    envelope = resolution_v2.SharedResourceLiveEnvelopeV2(
        resolution_v2.LIVE_ENVELOPE_SCHEMA_ID,
        _id("envelope"),
        registry.registry_id,
        stage.stage_profile_id,
        _id("occurrence"),
        _id("attempt"),
        _id("decision"),
        _id("window"),
        _id("cutoff"),
        0,
        0,
        resolution_v2.official_shared_resource_catalogue_fingerprint_v2(),
        (),
    )
    pending = resolution_v2.verify_v075_k7_shared_resource_semantics_v2(
        envelope
    )
    output = next(
        item for item in pending.resolutions if item.path == "io.output_bytes"
    )
    assert (
        output.status
        is resolution_v2.SharedResourceResolutionStatusV2.PENDING_LIVE_EVIDENCE
    )
    assert (
        output.pending_reason
        is resolution_v2.SharedResourcePendingReasonV2.SOURCE_PATH_ABSENT
    )
    assert output.exact_value is None
    assert output.counter_record_issuance_authorized is False
    with pytest.raises(
        replay_v2.ConstructionSharedResourceSemanticReplayV2Error,
        match="SharedResourceLiveSourceV2",
    ):
        replay_v2.verify_shared_resource_source_exact_v2(output)

    synthetic_root = tmp_path / "synthetic-output"
    synthetic_root.mkdir()
    descriptor, session, synthetic = synthetic_output_bundle(synthetic_root)
    try:
        with pytest.raises(
            output_v2.ConstructionSharedResourceOutputJournalV2Error,
            match="synthetic construction output",
        ):
            synthetic.live_source_v2()
        contract = next(
            item
            for item in resolution_v2.official_shared_resource_resolution_catalogue_v2()
            if item.path == output_v2.OUTPUT_PATH
        )
        components = tuple(
            sorted(
                (
                    synthetic.fixed_point_component,
                    synthetic.exclusive_writer_component,
                    synthetic.cutoff_component,
                    synthetic.output_manifest_component,
                ),
                key=lambda item: item.component_key,
            )
        )
        forged_source = resolution_v2.SharedResourceLiveSourceV2(
            synthetic.live_envelope_id,
            synthetic.occurrence_id,
            synthetic.route_attempt_id,
            synthetic.decision_point_id,
            synthetic.measurement_window_id,
            synthetic.operational_cutoff_id,
            output_v2.OUTPUT_PATH,
            contract.exact_source_kind,
            contract.required_provenance,
            synthetic.measurement_start_sequence,
            synthetic.operational_cutoff_sequence,
            components,
        )
        with pytest.raises(
            replay_v2.ConstructionSharedResourceSemanticReplayV2Error,
            match="raw semantic replay failed",
        ):
            replay_v2.verify_shared_resource_source_exact_v2(forged_source)
    finally:
        session.close()
        os.close(descriptor)


def test_dispatch_is_catalogue_fixed_and_result_is_issuer_owned() -> None:
    source = common_bundle().live_sources_v2()[0]
    with pytest.raises(
        replay_v2.ConstructionSharedResourceSemanticReplayV2Error,
        match="another shared-resource path",
    ):
        replay_v2.verify_integrity_checks_exact_v2(source)
    with pytest.raises(
        replay_v2.ConstructionSharedResourceSemanticReplayV2Error,
        match="caller-minted",
    ):
        replay_v2.SharedResourceSemanticReplayResultV2(
            object(),
            source.path,
            0,
            ReducerEnum.SUM,
            "verify_hash_invocations_exact_v2",
            "1" * 64,
            "acfqp.fake",
            "fake",
            source.live_envelope_id,
            source.occurrence_id,
            source.route_attempt_id,
            source.decision_point_id,
            source.measurement_window_id,
            source.operational_cutoff_id,
            source.covered_start_sequence,
            source.covered_cutoff_sequence,
            source.exact_source_kind,
            source.provenance_claims,
            tuple(item.component_key for item in source.components),
            tuple(item.source_artifact_id for item in source.components),
            tuple(item.source_bytes_sha256 for item in source.components),
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            False,
        )
    assert replay_v2.ALL_NINE_REPLAY_SUPPORTED is False
    assert not hasattr(replay_v2, "verify_all_nine_shared_resources_exact_v2")
    assert not hasattr(replay_v2, "CounterRecordV6")


def test_central_artifact_id_sha_and_identity_are_replayed() -> None:
    first = common_bundle().live_sources_v2()[0]
    component = first.components[0]
    stale_wrapper = resolution_v2.SharedResourceEvidenceComponentV2(
        component.component_key,
        component.source_schema_id,
        "f" * 64,
        component.source_bytes_sha256,
        component.raw_bytes,
    )
    with pytest.raises(
        replay_v2.ConstructionSharedResourceSemanticReplayV2Error,
        match="wrapper artifact ID",
    ):
        replay_v2.verify_shared_resource_source_exact_v2(
            _replace_component(first, stale_wrapper)
        )

    transcript = first.components[1]
    document = loads_canonical_json(transcript.raw_bytes)
    assert type(document) is dict
    document["raw_derived_event_count"] += 1
    corrupt_raw = canonical_json_bytes(document)
    corrupt = resolution_v2.SharedResourceEvidenceComponentV2(
        transcript.component_key,
        transcript.source_schema_id,
        transcript.source_artifact_id,
        hashlib.sha256(corrupt_raw).hexdigest(),
        corrupt_raw,
    )
    with pytest.raises(
        replay_v2.ConstructionSharedResourceSemanticReplayV2Error,
        match="central content ID",
    ):
        replay_v2.verify_shared_resource_source_exact_v2(
            _replace_component(first, corrupt)
        )

    second = common_bundle().live_sources_v2()[0]
    object.__setattr__(second, "occurrence_id", "e" * 64)
    with pytest.raises(
        replay_v2.ConstructionSharedResourceSemanticReplayV2Error,
        match="crossed its source identity",
    ):
        replay_v2.verify_shared_resource_source_exact_v2(second)


def test_missing_extra_reordered_and_cross_source_components_fail_closed() -> None:
    source = transfer_bundle().live_sources_v2()[1]
    original = source.components
    object.__setattr__(source, "components", original[:-1])
    with pytest.raises(
        replay_v2.ConstructionSharedResourceSemanticReplayV2Error,
        match="missing, extra, reordered",
    ):
        replay_v2.verify_shared_resource_source_exact_v2(source)
    object.__setattr__(source, "components", tuple(reversed(original)))
    with pytest.raises(
        replay_v2.ConstructionSharedResourceSemanticReplayV2Error,
        match="missing, extra, reordered",
    ):
        replay_v2.verify_shared_resource_source_exact_v2(source)
    object.__setattr__(source, "components", original + (original[-1],))
    with pytest.raises(
        replay_v2.ConstructionSharedResourceSemanticReplayV2Error,
        match="missing, extra, reordered",
    ):
        replay_v2.verify_shared_resource_source_exact_v2(source)

    first = common_bundle().live_sources_v2()[0]
    crossed_bundle = common_session(offset=100).close_v2()
    crossed_component = crossed_bundle.live_sources_v2()[0].components[1]
    crossed = _replace_component(first, crossed_component)
    with pytest.raises(
        replay_v2.ConstructionSharedResourceSemanticReplayV2Error,
        match="crossed its source identity",
    ):
        replay_v2.verify_shared_resource_source_exact_v2(crossed)


def test_failure_prefix_cannot_be_promoted_to_exact(tmp_path: Path) -> None:
    cgroup = _FakeCgroup(tmp_path / "failure-cgroup")
    session = open_working_session(cgroup)
    try:
        prefix = session.close_failure_prefix_v2(failure_reason="bootstrap failed")
        for source in prefix.live_sources_v2():
            with pytest.raises(
                replay_v2.ConstructionSharedResourceSemanticReplayV2Error,
                match="failure-prefix",
            ):
                replay_v2.verify_shared_resource_source_exact_v2(source)
    finally:
        session.close()
        cgroup.close()


def test_source_provenance_and_component_order_are_rechecked() -> None:
    source = common_bundle().live_sources_v2()[0]
    original_provenance = source.provenance_claims
    object.__setattr__(source, "provenance_claims", tuple(reversed(original_provenance)))
    with pytest.raises(
        replay_v2.ConstructionSharedResourceSemanticReplayV2Error,
        match="required provenance",
    ):
        replay_v2.verify_shared_resource_source_exact_v2(source)
