from __future__ import annotations

import hashlib

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_all_path_operation_boundary_manifest_v1 as parent_v1
from acfqp import (
    construction_k7_direct_fallback_operation_boundary_manifest_v2 as manifest_v2,
)


_EXPECTED_PATHS = {
    "control.cap_checks",
    "control.cap_rejections",
    "fallback.states_expanded",
    "fallback.actions_evaluated",
    "fallback.ground_steps",
    "fallback.outcome_rows",
    "fallback.bellman_backups",
}


def _codes(replay: manifest_v2.DirectFallbackBoundaryReplayV2) -> set[object]:
    return {row.code for row in replay.blockers}


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_exact_seven_site_manifest_and_contract_parent_replay() -> None:
    manifest = manifest_v2.freeze_direct_fallback_operation_boundary_manifest_v2()
    parent = parent_v1.freeze_construction_k7_all_path_operation_boundary_manifest_v1()
    parent_site = parent.by_key[manifest_v2.PARENT_SITE_KEY]
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)

    assert manifest.counter_registry_id == registry.registry_id
    assert manifest.stage_profile_id == stage.stage_profile_id
    assert manifest.stage_kind is registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    assert manifest.parent_manifest_id == parent.manifest_id
    assert manifest.parent_site_id == parent_site.site_id
    assert manifest.parent_manifest_id == manifest_v2.EXPECTED_PARENT_MANIFEST_ID
    assert manifest.parent_site_id == manifest_v2.EXPECTED_PARENT_FALLBACK_SITE_ID
    assert len(manifest.boundaries) == manifest_v2.EXPECTED_BOUNDARY_COUNT == 7
    assert set(manifest.by_path) == _EXPECTED_PATHS
    assert set(manifest.by_dispatch) == {
        "direct-fallback.control.cap-check",
        "direct-fallback.control.cap-rejection",
        "direct-fallback.state.expanded",
        "direct-fallback.action.evaluated",
        "direct-fallback.kernel.transition",
        "direct-fallback.outcome.row",
        "direct-fallback.bellman.backup",
    }
    for path, boundary in manifest.by_path.items():
        assert boundary.reducer is ReducerEnum.SUM
        assert boundary.registered_owner == registry.by_path[path].owner
        assert boundary.parent_site_id == parent_site.site_id
        assert boundary.operation_source_module == manifest_v2.SOURCE_MODULE
    document = manifest.to_document()
    assert document["future_test_owner_source_only"] is True
    assert document["production_source_integrated"] is False
    assert document["runtime_evidence_issued"] is False
    assert document["central_domain_registration_pending"] is True
    assert document["production_closure_claimed"] is False


def test_source_and_portable_manifest_replay_are_exact() -> None:
    archive = manifest_v2.load_direct_fallback_operation_source_archive_v2()
    replay = manifest_v2.replay_direct_fallback_operation_source_archive_v2(
        archive
    )
    assert replay.outcome is manifest_v2.DirectFallbackBoundaryReplayOutcomeV2.VERIFIED
    assert replay.manifest is not None
    portable = manifest_v2.verify_direct_fallback_operation_boundary_manifest_document_v2(
        replay.manifest.to_document(), archive
    )
    assert portable.outcome is manifest_v2.DirectFallbackBoundaryReplayOutcomeV2.VERIFIED
    assert portable.manifest == replay.manifest


def test_missing_source_member_blocks_replay() -> None:
    replay = manifest_v2.replay_direct_fallback_operation_source_archive_v2({})
    codes = _codes(replay)
    assert replay.outcome is manifest_v2.DirectFallbackBoundaryReplayOutcomeV2.BLOCKED
    assert manifest_v2.DirectFallbackBoundaryBlockerCodeV2.SOURCE_MEMBER_SET_CHANGED in codes
    assert manifest_v2.DirectFallbackBoundaryBlockerCodeV2.SOURCE_MEMBER_MISSING in codes


def test_nonstring_or_extra_source_member_is_not_filtered_out() -> None:
    archive = manifest_v2.load_direct_fallback_operation_source_archive_v2()
    raw = archive[manifest_v2.SOURCE_MODULE]
    for extra_key in (7, "acfqp.unregistered_extra_source_v2"):
        replay = manifest_v2.replay_direct_fallback_operation_source_archive_v2(
            {manifest_v2.SOURCE_MODULE: raw, extra_key: b"extra"}
        )
        assert replay.outcome is (
            manifest_v2.DirectFallbackBoundaryReplayOutcomeV2.BLOCKED
        )
        assert (
            manifest_v2.DirectFallbackBoundaryBlockerCodeV2.SOURCE_MEMBER_SET_CHANGED
            in _codes(replay)
        )


def test_nonsemantic_source_byte_mutation_is_not_silently_resigned() -> None:
    archive = manifest_v2.load_direct_fallback_operation_source_archive_v2()
    raw = archive[manifest_v2.SOURCE_MODULE]
    mutated = {manifest_v2.SOURCE_MODULE: raw + b"\n"}
    replay = manifest_v2.replay_direct_fallback_operation_source_archive_v2(
        mutated
    )
    assert manifest_v2.DirectFallbackBoundaryBlockerCodeV2.SOURCE_BYTES_CHANGED in _codes(
        replay
    )


def test_missing_extra_and_nonliteral_hooks_are_typed_blockers() -> None:
    archive = manifest_v2.load_direct_fallback_operation_source_archive_v2()
    raw = archive[manifest_v2.SOURCE_MODULE]

    removed = raw.replace(
        b'emit_route_segment_operation_v2("direct-fallback.control.cap-check", 1)',
        b"None",
        1,
    )
    missing = manifest_v2.replay_direct_fallback_operation_source_archive_v2(
        {manifest_v2.SOURCE_MODULE: removed}
    )
    assert manifest_v2.DirectFallbackBoundaryBlockerCodeV2.HOOK_MISSING in _codes(
        missing
    )

    added = raw + (
        b'\nemit_route_segment_operation_v2('
        b'"direct-fallback.control.cap-check", 1)\n'
    )
    extra = manifest_v2.replay_direct_fallback_operation_source_archive_v2(
        {manifest_v2.SOURCE_MODULE: added}
    )
    assert manifest_v2.DirectFallbackBoundaryBlockerCodeV2.HOOK_EXTRA in _codes(extra)

    nonliteral_raw = raw.replace(
        b'"direct-fallback.control.cap-check", 1',
        b'str("direct-fallback.control.cap-check"), 1',
        1,
    )
    nonliteral = manifest_v2.replay_direct_fallback_operation_source_archive_v2(
        {manifest_v2.SOURCE_MODULE: nonliteral_raw}
    )
    assert manifest_v2.DirectFallbackBoundaryBlockerCodeV2.HOOK_NON_LITERAL in _codes(
        nonliteral
    )


def test_portable_manifest_mutation_is_rejected() -> None:
    archive = manifest_v2.load_direct_fallback_operation_source_archive_v2()
    manifest = manifest_v2.freeze_direct_fallback_operation_boundary_manifest_v2()
    document = manifest.to_document()
    document["production_source_integrated"] = True
    replay = manifest_v2.verify_direct_fallback_operation_boundary_manifest_document_v2(
        document, archive
    )
    assert replay.outcome is manifest_v2.DirectFallbackBoundaryReplayOutcomeV2.BLOCKED
    assert manifest_v2.DirectFallbackBoundaryBlockerCodeV2.MANIFEST_DOCUMENT_CHANGED in _codes(
        replay
    )


def test_v2_slice_does_not_add_legacy_emit_owned_operation_calls() -> None:
    archive = manifest_v2.load_direct_fallback_operation_source_archive_v2()
    assert b"emit_owned_operation_v1(" not in archive[manifest_v2.SOURCE_MODULE]


def test_parent_authority_is_replayed_each_time_not_cached(
    monkeypatch,
) -> None:
    # Warm the successful path first.  A persistent parent-site cache would
    # incorrectly let the second replay pass after this authority mutation.
    manifest_v2.freeze_direct_fallback_operation_boundary_manifest_v2()

    def changed_parent_authority():
        raise ValueError("mutated Contract-2.0.36 parent authority")

    monkeypatch.setattr(
        manifest_v2.parent_v1,
        "freeze_construction_k7_all_path_operation_boundary_manifest_v1",
        changed_parent_authority,
    )
    replay = manifest_v2.replay_direct_fallback_operation_source_archive_v2(
        manifest_v2.load_direct_fallback_operation_source_archive_v2()
    )
    assert replay.outcome is manifest_v2.DirectFallbackBoundaryReplayOutcomeV2.BLOCKED
    assert manifest_v2.DirectFallbackBoundaryBlockerCodeV2.PARENT_MANIFEST_CHANGED in _codes(
        replay
    )


def test_structurally_complete_parent_with_arbitrary_identity_is_blocked(
    monkeypatch,
) -> None:
    real = parent_v1.freeze_construction_k7_all_path_operation_boundary_manifest_v1()

    class StructurallyCompleteWrongParent:
        manifest_id = _id("arbitrary-parent-manifest")
        by_key = real.by_key

        @staticmethod
        def to_document():
            document = real.to_document()
            document["operation_boundary_manifest_id"] = (
                StructurallyCompleteWrongParent.manifest_id
            )
            return document

    monkeypatch.setattr(
        manifest_v2.parent_v1,
        "freeze_construction_k7_all_path_operation_boundary_manifest_v1",
        lambda: StructurallyCompleteWrongParent(),
    )
    replay = manifest_v2.replay_direct_fallback_operation_source_archive_v2(
        manifest_v2.load_direct_fallback_operation_source_archive_v2()
    )
    assert replay.outcome is manifest_v2.DirectFallbackBoundaryReplayOutcomeV2.BLOCKED
    assert manifest_v2.DirectFallbackBoundaryBlockerCodeV2.PARENT_MANIFEST_CHANGED in _codes(
        replay
    )


def test_parent_with_expected_ids_but_mutated_document_is_blocked(monkeypatch) -> None:
    real = parent_v1.freeze_construction_k7_all_path_operation_boundary_manifest_v1()

    class MutatedParentDocument:
        manifest_id = manifest_v2.EXPECTED_PARENT_MANIFEST_ID
        by_key = real.by_key

        @staticmethod
        def to_document():
            document = real.to_document()
            document["execution_performed"] = True
            return document

    monkeypatch.setattr(
        manifest_v2.parent_v1,
        "freeze_construction_k7_all_path_operation_boundary_manifest_v1",
        lambda: MutatedParentDocument(),
    )
    replay = manifest_v2.replay_direct_fallback_operation_source_archive_v2(
        manifest_v2.load_direct_fallback_operation_source_archive_v2()
    )
    assert replay.outcome is manifest_v2.DirectFallbackBoundaryReplayOutcomeV2.BLOCKED
    assert manifest_v2.DirectFallbackBoundaryBlockerCodeV2.PARENT_MANIFEST_CHANGED in _codes(
        replay
    )
