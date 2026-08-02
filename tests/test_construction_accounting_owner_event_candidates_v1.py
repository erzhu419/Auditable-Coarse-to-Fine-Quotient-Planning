from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import replace

import pytest

from acfqp import construction_accounting_owner_event_candidates_v1 as candidates
from acfqp import construction_accounting_owned_runtime_v1 as owned
from acfqp import construction_accounting_partial_native_v1 as partial
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as boundary_v3


def _identity(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _archive(*, mutate_module: str | None = None) -> bytes:
    modules = sorted(
        {
            row.operation_source_module
            for row in candidates._emittable_boundaries()  # noqa: SLF001
        }
        | set(candidates._CONTROL_SOURCE_MODULES)  # noqa: SLF001
    )
    output = io.BytesIO()
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_STORED, allowZip64=True
    ) as handle:
        for module in modules:
            raw = candidates._live_source_bytes(module)  # noqa: SLF001
            if module == mutate_module:
                raw += b"\n# source mutation\n"
            info = zipfile.ZipInfo(
                module.replace(".", "/") + ".py",
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = (0o100444 & 0xFFFF) << 16
            handle.writestr(info, raw)
    return output.getvalue()


def _archive_with_sources(sources: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_STORED, allowZip64=True
    ) as handle:
        for module, raw in sorted(sources.items()):
            info = zipfile.ZipInfo(
                module.replace(".", "/") + ".py",
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = (0o100444 & 0xFFFF) << 16
            handle.writestr(info, raw)
    return output.getvalue()


def _binding(raw: bytes, *, occurrence: str | None = None):
    return candidates.OwnerEventExecutionBindingV1(
        candidates._BINDING_ISSUER,  # noqa: SLF001
        _identity("request"),
        _identity("route"),
        occurrence or _identity("occurrence"),
        _identity("logical occurrence"),
        _identity("manifest"),
        _identity("runtime"),
        _identity("broker transcript"),
        _identity("business bundle"),
        _identity("source snapshot"),
        hashlib.sha256(raw).hexdigest(),
        len(raw),
        _identity("postexec binding"),
    )


def _rows():
    manifest = boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    return tuple(
        row
        for row in manifest.boundaries
        if row.to_document()["emittable_in_this_fixture"] is True
    )


def _completed_transcript(*, nonunit: bool = False):
    registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    manifest = boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    rows = _rows()
    by_stage = {}
    for row in rows:
        by_stage.setdefault(row.stage.value, []).append(row)

    # Exercise both sides of one stage-neutral dispatch binding.
    dispatch_stages = {}
    for row in rows:
        dispatch_stages.setdefault(row.dispatch_key, set()).add(row.stage.value)
    shared_dispatch = next(
        key for key, stages in dispatch_stages.items() if len(stages) > 1
    )
    shared_rows = {
        row.stage.value: row for row in rows if row.dispatch_key == shared_dispatch
    }
    multisite_path = next(
        path
        for path in sorted({row.target_path for row in rows})
        if len([row for row in rows if row.target_path == path]) > 1
        and path.startswith("build.initial_")
    )
    multi_rows = [row for row in rows if row.target_path == multisite_path]

    with owned.activate_owned_construction_accounting_v1(
        occurrence_id=_identity("occurrence"),
        recorder_id="test-owner-event-candidates-v1",
        counter_registry=registry,
        stage_profile=stage_profile,
        boundary_profile=manifest,
        _allow_low_level_test_api=True,
    ) as session:
        for stage in partial.ROOT_CAP_FIVE_STAGE_PLAN_V1:
            owned.enter_owned_stage_v1(stage)
            if stage.value in shared_rows:
                row = shared_rows[stage.value]
                owned.emit_owned_sum_v1(
                    row.boundary_key,
                    row.target_path,
                    2 if nonunit else 1,
                )
            if stage is partial.PartialNativeStageV1.INITIAL_MODEL_BUILD:
                for row in multi_rows:
                    owned.emit_owned_sum_v1(row.boundary_key, row.target_path, 1)
            owned.exit_owned_stage_v1(stage)
        transcript = owned.complete_owned_occurrence_v1()
        assert transcript is not None
        assert session.transcript.transcript_id == transcript.transcript_id
    return transcript, shared_rows, multisite_path


def _aborted_transcript():
    registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    manifest = boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    with owned.activate_owned_construction_accounting_v1(
        occurrence_id=_identity("occurrence"),
        recorder_id="test-owner-event-candidates-abort-v1",
        counter_registry=registry,
        stage_profile=stage_profile,
        boundary_profile=manifest,
        _allow_low_level_test_api=True,
    ) as session:
        owned.enter_owned_stage_v1(partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX)
        transcript = owned.abort_owned_occurrence_v1("TEST_ABORT")
        assert transcript is not None
        assert session.transcript.transcript_id == transcript.transcript_id
    return transcript


def test_exact_89_site_71_path_semantic_closure_and_stage_neutral_dispatch():
    raw = _archive()
    transcript, shared_rows, multisite_path = _completed_transcript()
    result = candidates._derive_from_verified_inputs(  # noqa: SLF001
        execution_binding=_binding(raw),
        source_archive_raw=raw,
        transcript_document=transcript.to_document(),
    )
    candidates.verify_owner_event_candidate_set_v1(result)

    assert len(result.site_closures) == 89
    assert len(result.path_candidates) == 71
    assert sum(row.value for row in result.path_candidates) == 4
    assert {
        row.evidence_kind for row in result.path_candidates
    } == {candidates.POSITIVE_KIND, candidates.ZERO_KIND}

    by_path = {row.path: row for row in result.path_candidates}
    assert by_path[multisite_path].value == 2
    assert len(by_path[multisite_path].site_closure_ids) >= 2
    for row in shared_rows.values():
        assert by_path[row.target_path].value == 1

    document = result.to_document()
    assert document["counter_records_materialized"] is False
    assert document["work_vector_materialized"] is False
    assert document["comparison_vector_materialized"] is False
    assert document["formal_materialization_allowed"] is False
    assert document["central_domain_registration_pending"] is False
    assert result.execution_binding.postexec_attestation_exported is False


def test_completed_empty_owner_windows_create_explicit_zeros_not_counter_records():
    raw = _archive()
    transcript, _shared_rows, _multisite_path = _completed_transcript()
    # Delete only operation events by making a new exact five-stage transcript.
    registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    manifest = boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    with owned.activate_owned_construction_accounting_v1(
        occurrence_id=_identity("occurrence"),
        recorder_id="test-owner-event-candidates-empty-v1",
        counter_registry=registry,
        stage_profile=stage_profile,
        boundary_profile=manifest,
    ):
        for stage in partial.ROOT_CAP_FIVE_STAGE_PLAN_V1:
            owned.enter_owned_stage_v1(stage)
            owned.exit_owned_stage_v1(stage)
        empty = owned.complete_owned_occurrence_v1()
        assert empty is not None
    result = candidates._derive_from_verified_inputs(  # noqa: SLF001
        execution_binding=_binding(raw),
        source_archive_raw=raw,
        transcript_document=empty.to_document(),
    )
    assert all(row.value == 0 for row in result.path_candidates)
    assert all(
        row.evidence_kind == candidates.ZERO_KIND for row in result.path_candidates
    )
    assert all(
        row.to_document()["formal_counter_record"] is False
        for row in result.path_candidates
    )


def test_abort_nonunit_cross_occurrence_and_archive_source_change_fail_closed():
    raw = _archive()
    aborted = _aborted_transcript()
    with pytest.raises(
        candidates.ConstructionAccountingOwnerEventCandidatesV1Error,
        match="completed five-stage",
    ):
        candidates._derive_from_verified_inputs(  # noqa: SLF001
            execution_binding=_binding(raw),
            source_archive_raw=raw,
            transcript_document=aborted.to_document(),
        )

    nonunit, _shared, _multi = _completed_transcript(nonunit=True)
    with pytest.raises(
        candidates.ConstructionAccountingOwnerEventCandidatesV1Error,
        match="exact unit primitives",
    ):
        candidates._derive_from_verified_inputs(  # noqa: SLF001
            execution_binding=_binding(raw),
            source_archive_raw=raw,
            transcript_document=nonunit.to_document(),
        )

    completed, _shared, _multi = _completed_transcript()
    with pytest.raises(
        candidates.ConstructionAccountingOwnerEventCandidatesV1Error,
        match="crossed its occurrence",
    ):
        candidates._derive_from_verified_inputs(  # noqa: SLF001
            execution_binding=_binding(raw, occurrence=_identity("foreign occurrence")),
            source_archive_raw=raw,
            transcript_document=completed.to_document(),
        )

    changed_module = _rows()[0].operation_source_module
    changed = _archive(mutate_module=changed_module)
    with pytest.raises(
        candidates.ConstructionAccountingOwnerEventCandidatesV1Error,
        match="archive and loaded source bytes differ",
    ):
        candidates._derive_from_verified_inputs(  # noqa: SLF001
            execution_binding=_binding(changed),
            source_archive_raw=changed,
            transcript_document=completed.to_document(),
        )


def test_independent_chain_node_content_id_and_site_binding_replay():
    raw = _archive()
    transcript, _shared, _multi = _completed_transcript()
    document = transcript.to_document()
    event = next(
        row
        for row in document["chain_nodes"]
        if row["schema"].endswith("operation_event.v1")
    )
    event["amount"] = event["amount"] + 1
    with pytest.raises(
        candidates.ConstructionAccountingOwnerEventCandidatesV1Error,
        match="content identity changed",
    ):
        candidates._derive_from_verified_inputs(  # noqa: SLF001
            execution_binding=_binding(raw),
            source_archive_raw=raw,
            transcript_document=document,
        )

    # Rebuild the complete hash chain after crossing an event to another path.
    # Structural hashes are then valid, so rejection must come from the exact
    # V3 site/path/stage semantic replay.
    first_event = next(
        row
        for row in transcript.nodes
        if type(row) is partial.PartialNativeOperationEventV1
    )
    foreign_path = next(
        row.target_path
        for row in _rows()
        if row.stage.value == first_event.stage_kind.value
        and row.target_path != first_event.path
    )
    rebuilt = []
    predecessor = transcript.start.chain_id
    event_ids = []
    changed = False
    for index, node in enumerate(transcript.nodes, 1):
        updates = {"chain_sequence": index, "predecessor_chain_id": predecessor}
        if type(node) is partial.PartialNativeOperationEventV1:
            if not changed:
                updates["path"] = foreign_path
                changed = True
            new_node = replace(node, **updates)
            event_ids.append(new_node.event_id)
        elif type(node) is partial.PartialNativeOccurrenceCompletionV1:
            new_node = replace(node, emitted_event_ids=tuple(event_ids), **updates)
        else:
            new_node = replace(node, **updates)
        rebuilt.append(new_node)
        predecessor = new_node.chain_id
    semantic_cross = partial.PartialNativeOccurrenceTranscriptV1(
        transcript.start, tuple(rebuilt)
    )
    with pytest.raises(
        candidates.ConstructionAccountingOwnerEventCandidatesV1Error,
        match="exact site/path/stage",
    ):
        candidates._derive_from_verified_inputs(  # noqa: SLF001
            execution_binding=_binding(raw),
            source_archive_raw=raw,
            transcript_document=semantic_cross.to_document(),
        )


def test_archive_hook_inventory_is_exact_even_when_loaded_bytes_match(monkeypatch):
    modules = sorted(
        {
            row.operation_source_module
            for row in candidates._emittable_boundaries()  # noqa: SLF001
        }
        | set(candidates._CONTROL_SOURCE_MODULES)  # noqa: SLF001
    )
    originals = {
        module: candidates._live_source_bytes(module)  # noqa: SLF001
        for module in modules
    }
    selected = _rows()[0].operation_source_module
    needle = b"accounting_runtime.emit_owned_operation_v1("
    assert needle in originals[selected]
    changed = dict(originals)
    changed[selected] = changed[selected].replace(
        needle, b"accounting_runtime.unregistered_operation_hook(", 1
    )
    raw = _archive_with_sources(changed)
    real_loader = candidates._live_source_bytes  # noqa: SLF001

    def matching_loaded_source(module: str) -> bytes:
        return changed[module] if module == selected else real_loader(module)

    monkeypatch.setattr(candidates, "_live_source_bytes", matching_loaded_source)
    transcript, _shared, _multi = _completed_transcript()
    with pytest.raises(
        candidates.ConstructionAccountingOwnerEventCandidatesV1Error,
        match="hook inventory",
    ):
        candidates._derive_from_verified_inputs(  # noqa: SLF001
            execution_binding=_binding(raw),
            source_archive_raw=raw,
            transcript_document=transcript.to_document(),
        )


def test_production_wrapper_rejects_untyped_inputs():
    with pytest.raises(
        candidates.ConstructionAccountingOwnerEventCandidatesV1Error,
        match="foreign artifact",
    ):
        candidates.derive_v075_k7_owner_event_candidates_v1(
            role_manifest=object(),
            runtime_envelope=object(),
            business_bundle_raw=b"{}",
        )
