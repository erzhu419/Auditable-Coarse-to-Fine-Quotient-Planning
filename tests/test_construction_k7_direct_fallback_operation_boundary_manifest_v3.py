from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_all_path_operation_boundary_manifest_v1 as parent_v1
from acfqp import construction_k7_direct_fallback_operation_boundary_manifest_v2 as manifest_v2
from acfqp import construction_k7_direct_fallback_operation_boundary_manifest_v3 as manifest_v3
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]


def test_v3_manifest_binds_exact_real_owned_ledger_sites() -> None:
    manifest = manifest_v3.freeze_direct_fallback_operation_boundary_manifest_v3()
    assert manifest_v3.PRODUCTION_SOURCE_INTEGRATED is True
    assert manifest_v3.PRODUCTION_CLOSURE_CLAIMED is False
    assert len(manifest.boundaries) == 7
    assert manifest.parent_v2_manifest_id == manifest_v3.EXPECTED_PARENT_V2_MANIFEST_ID
    assert {row.target_path for row in manifest.boundaries} == {
        "control.cap_checks",
        "control.cap_rejections",
        "fallback.states_expanded",
        "fallback.actions_evaluated",
        "fallback.ground_steps",
        "fallback.outcome_rows",
        "fallback.bellman_backups",
    }
    assert all(
        row.operation_source_module == "acfqp.phase3e_fallback_owned_v2"
        and row.operation_source_symbol.startswith("_OwnedFallbackLedgerV2.")
        for row in manifest.boundaries
    )
    registry = registry_v6.official_counter_registry_v6()
    assert manifest.counter_registry_id == registry.registry_id


def test_v3_manifest_independent_document_replay() -> None:
    archive = manifest_v3.load_direct_fallback_operation_source_archive_v3()
    manifest = manifest_v3.freeze_direct_fallback_operation_boundary_manifest_v3()
    replay = manifest_v3.verify_direct_fallback_operation_boundary_manifest_document_v3(
        manifest.to_document(), archive
    )
    assert replay.outcome is manifest_v3.DirectFallbackBoundaryReplayOutcomeV3.VERIFIED
    assert replay.manifest == manifest
    assert replay.blockers == ()


def test_fresh_python_process_clean_archive_replays_verified() -> None:
    code = """
from acfqp import construction_k7_direct_fallback_operation_boundary_manifest_v3 as m
r = m.replay_direct_fallback_operation_source_archive_v3(
    m.load_direct_fallback_operation_source_archive_v3()
)
assert r.outcome is m.DirectFallbackBoundaryReplayOutcomeV3.VERIFIED
assert r.manifest is not None
assert r.blockers == ()
print(r.manifest.manifest_id)
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == (
        manifest_v3.freeze_direct_fallback_operation_boundary_manifest_v3().manifest_id
    )


def test_v2_and_contract_2_0_36_parent_replay_without_identity_drift() -> None:
    parent = parent_v1.freeze_construction_k7_all_path_operation_boundary_manifest_v1()
    site = parent.by_key[manifest_v2.PARENT_SITE_KEY]
    assert parent.manifest_id == manifest_v2.EXPECTED_PARENT_MANIFEST_ID
    assert hashlib.sha256(canonical_json_bytes(parent.to_document())).hexdigest() == (
        manifest_v2.EXPECTED_PARENT_MANIFEST_DOCUMENT_SHA256
    )
    assert site.site_id == manifest_v2.EXPECTED_PARENT_FALLBACK_SITE_ID
    assert hashlib.sha256(canonical_json_bytes(site.to_document())).hexdigest() == (
        manifest_v2.EXPECTED_PARENT_FALLBACK_SITE_DOCUMENT_SHA256
    )
    replay = manifest_v2.replay_direct_fallback_operation_source_archive_v2(
        manifest_v2.load_direct_fallback_operation_source_archive_v2()
    )
    assert replay.outcome is manifest_v2.DirectFallbackBoundaryReplayOutcomeV2.VERIFIED
    assert replay.manifest is not None
    assert replay.blockers == ()


def test_v3_manifest_rejects_source_and_inventory_tampering() -> None:
    archive = manifest_v3.load_direct_fallback_operation_source_archive_v3()
    raw = archive[manifest_v3.SOURCE_MODULE]
    tampered = dict(archive)
    tampered[manifest_v3.SOURCE_MODULE] = raw.replace(
        b'"direct-fallback.state.expanded"',
        b'"direct-fallback.state.changedx"',
        1,
    )
    replay = manifest_v3.replay_direct_fallback_operation_source_archive_v3(tampered)
    assert replay.outcome is manifest_v3.DirectFallbackBoundaryReplayOutcomeV3.BLOCKED
    assert replay.manifest is None
    assert {row.code for row in replay.blockers} & {
        "HOOK_INVENTORY_CHANGED",
        "SYMBOL_AST_CHANGED",
        "SOURCE_BYTES_CHANGED",
    }

    replay = manifest_v3.replay_direct_fallback_operation_source_archive_v3(
        {**archive, "acfqp.foreign": b"pass\n"}
    )
    assert replay.outcome is manifest_v3.DirectFallbackBoundaryReplayOutcomeV3.BLOCKED
    assert any(row.code == "SOURCE_MEMBER_SET_CHANGED" for row in replay.blockers)


def test_v3_manifest_rejects_changed_document() -> None:
    archive = manifest_v3.load_direct_fallback_operation_source_archive_v3()
    document = manifest_v3.freeze_direct_fallback_operation_boundary_manifest_v3().to_document()
    document["production_source_integrated"] = False
    replay = manifest_v3.verify_direct_fallback_operation_boundary_manifest_document_v3(
        document, archive
    )
    assert replay.outcome is manifest_v3.DirectFallbackBoundaryReplayOutcomeV3.BLOCKED
    assert replay.blockers[0].code == "MANIFEST_DOCUMENT_CHANGED"


def test_unchanged_archive_cannot_authorize_replaced_live_owner_class(
    monkeypatch,
) -> None:
    from acfqp import phase3e_fallback_owned_v2 as owned_v2

    archive = manifest_v3.load_direct_fallback_operation_source_archive_v3()
    original_raw = archive[manifest_v3.SOURCE_MODULE]
    fake = type(
        "_OwnedFallbackLedgerV2",
        (),
        {"__module__": owned_v2.__name__},
    )
    monkeypatch.setattr(owned_v2, "_OwnedFallbackLedgerV2", fake)
    assert (
        manifest_v3.load_direct_fallback_operation_source_archive_v3()[
            manifest_v3.SOURCE_MODULE
        ]
        == original_raw
    )
    replay = manifest_v3.replay_direct_fallback_operation_source_archive_v3(
        archive
    )
    assert replay.outcome is manifest_v3.DirectFallbackBoundaryReplayOutcomeV3.BLOCKED
    assert replay.manifest is None
    assert any(row.code == "LIVE_OWNER_BINDING_CHANGED" for row in replay.blockers)


def test_replacing_live_binding_validator_cannot_reauthorize_same_archive(
    monkeypatch,
) -> None:
    from acfqp import phase3e_fallback_owned_v2 as owned_v2

    archive = manifest_v3.load_direct_fallback_operation_source_archive_v3()
    original_binding = owned_v2.require_frozen_owned_fallback_source_binding_v2()
    monkeypatch.setattr(
        owned_v2,
        "require_frozen_owned_fallback_source_binding_v2",
        lambda: original_binding,
    )
    replay = manifest_v3.replay_direct_fallback_operation_source_archive_v3(
        archive
    )
    assert replay.outcome is manifest_v3.DirectFallbackBoundaryReplayOutcomeV3.BLOCKED
    assert replay.manifest is None
    assert any(row.code == "LIVE_OWNER_BINDING_CHANGED" for row in replay.blockers)


def test_in_place_gateway_code_replacement_blocks_clean_archive_and_binding(
    monkeypatch,
) -> None:
    from acfqp import construction_accounting_route_segment_v3 as route_v3

    archive = manifest_v3.load_direct_fallback_operation_source_archive_v3()
    manifest = manifest_v3.freeze_direct_fallback_operation_boundary_manifest_v3()
    replacement = lambda dispatch_key, amount=1: None
    monkeypatch.setattr(
        route_v3.emit_owned_route_operation_v3,
        "__code__",
        replacement.__code__,
    )
    replay = manifest_v3.replay_direct_fallback_operation_source_archive_v3(
        archive
    )
    assert replay.outcome is manifest_v3.DirectFallbackBoundaryReplayOutcomeV3.BLOCKED
    assert replay.manifest is None
    assert any(row.code == "LIVE_OWNER_BINDING_CHANGED" for row in replay.blockers)
    with pytest.raises(
        manifest_v3.ConstructionK7DirectFallbackOperationBoundaryManifestV3Error,
        match="live binding changed",
    ):
        manifest_v3.require_frozen_live_owner_binding_v3(manifest)
