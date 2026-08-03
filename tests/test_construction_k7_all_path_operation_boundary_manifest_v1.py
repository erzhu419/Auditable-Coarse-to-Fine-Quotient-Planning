from __future__ import annotations

from copy import deepcopy
from dataclasses import fields, replace
from functools import cache

import pytest

from acfqp.accounting_v1 import RouteKindEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_all_path_accounting_profile_v1 as profile_v1
from acfqp import construction_k7_all_path_operation_boundary_manifest_v1 as boundary_v1
from acfqp.routing_v1 import TerminalCode


@cache
def _archive() -> dict[str, bytes]:
    return boundary_v1.load_official_operation_boundary_source_archive_v1()


@cache
def _manifest() -> boundary_v1.ConstructionK7AllPathOperationBoundaryManifestV1:
    return boundary_v1.freeze_construction_k7_all_path_operation_boundary_manifest_v1(
        source_archive=dict(_archive())
    )


def test_exact_catalogue_covers_six_real_families_and_ten_call_sites() -> None:
    manifest = _manifest()

    assert len(manifest.source_members) == 6
    assert len(manifest.sites) == 10
    assert {row.family for row in manifest.sites} == set(
        boundary_v1.BoundaryFamilyV1
    )
    assert len(manifest.by_key) == 10
    assert all(row.source_byte_count == len(_archive()[row.module_name]) for row in manifest.sites)

    document = manifest.to_document()
    assert document["proposed_contract_version"] == "2.0.36"
    assert document["boundary_family_count"] == 6
    assert document["site_count"] == 10
    assert document["source_member_count"] == 6
    assert document["catalogue_only"] is True
    assert document["source_archive_replay_required"] is True
    assert document["all_required_boundary_families_present"] is True
    assert document["execution_performed"] is False
    assert document["counter_records_issued"] == 0
    assert document["work_vectors_issued"] == 0
    assert document["comparison_vectors_issued"] == 0
    assert document["all_path_native_accounting_complete"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_n_break_even"] is None
    assert document["counter_completeness_gate_status"].endswith("NOT_RUN")
    assert document["workload_economics_gate_status"].endswith("NOT_RUN")


def test_stage_route_terminal_and_accounting_bindings_consume_profile() -> None:
    manifest = _manifest()
    profile = profile_v1.freeze_construction_k7_all_path_accounting_profile_v1()
    assert manifest.all_path_accounting_profile_id == profile.profile_id

    expected_stages = {
        boundary_v1.BoundaryFamilyV1.PREOPEN_COMMON: (
            registry_v6.ConstructionStageKindV6.PREOPEN_COMMON_PREFIX
        ),
        boundary_v1.BoundaryFamilyV1.ABSTRACT: (
            registry_v6.ConstructionStageKindV6.FAILED_ABSTRACT_PREFIX
        ),
        boundary_v1.BoundaryFamilyV1.LOCAL: (
            registry_v6.ConstructionStageKindV6.LOCAL_ATTEMPT
        ),
        boundary_v1.BoundaryFamilyV1.FALLBACK: (
            registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
        ),
        boundary_v1.BoundaryFamilyV1.REBUILD: (
            registry_v6.ConstructionStageKindV6.REBUILD
        ),
        boundary_v1.BoundaryFamilyV1.VERIFICATION_TERMINAL: (
            registry_v6.ConstructionStageKindV6
            .CLOSED_RECONCILIATION_AND_TERMINALIZATION
        ),
    }
    for site in manifest.sites:
        assert site.stage_kind is expected_stages[site.family]
        assert site.route_kinds
        assert site.terminal_codes
        assert site.accounting_families
        assert site.evidence_roles
        assert all(item in RouteKindEnum for item in site.route_kinds)
        assert all(item in TerminalCode for item in site.terminal_codes)
        for code in site.terminal_codes:
            rule = profile.terminal_path_rule_by_code[code]
            stage = {row.stage_kind: row.disposition for row in rule.stage_plan}
            assert any(
                route in rule.route_kinds_permitted_in_attempt
                for route in site.route_kinds
            )
            assert stage[site.stage_kind] is not profile_v1.StageDispositionV1.FORBIDDEN
        available_roles = {
            evidence.role
            for code in site.terminal_codes
            for evidence in profile.terminal_path_rule_by_code[
                code
            ].required_evidence_roles
        }
        assert set(site.evidence_roles) <= available_roles

    by_key = manifest.by_key
    assert by_key["local.slice-materialization"].accounting_families == (
        profile_v1.AccountingFamilyV1.LOCAL_OWNER,
    )
    assert by_key["fallback.authorized-ground-search"].accounting_families == (
        profile_v1.AccountingFamilyV1.FALLBACK_OWNER,
    )
    assert by_key["rebuild.registered-rebuild-callback"].accounting_families == (
        profile_v1.AccountingFamilyV1.REBUILD_OWNER,
    )
    assert by_key[
        "verification.terminal-semantic-attestation-replay"
    ].terminal_codes == tuple(TerminalCode)


def test_source_archive_replay_is_exact_and_deterministic() -> None:
    first = boundary_v1.replay_operation_boundary_source_archive_v1(
        dict(_archive())
    )
    second = boundary_v1.replay_operation_boundary_source_archive_v1(
        dict(reversed(tuple(_archive().items())))
    )

    assert first.outcome is boundary_v1.BoundaryReplayOutcomeV1.VERIFIED
    assert second.outcome is boundary_v1.BoundaryReplayOutcomeV1.VERIFIED
    assert first.blockers == second.blockers == ()
    assert first.manifest is not None
    assert second.manifest is not None
    assert first.source_archive_id == second.source_archive_id
    assert first.manifest.manifest_id == second.manifest.manifest_id
    assert first.replay_id == second.replay_id


@pytest.mark.parametrize(
    ("module_name", "family"),
    (
        ("acfqp.phase3e_runner_v1", boundary_v1.BoundaryFamilyV1.PREOPEN_COMMON),
        ("acfqp.phase3e_model_only_v1", boundary_v1.BoundaryFamilyV1.ABSTRACT),
        ("acfqp.phase3e_local_adapter_v1", boundary_v1.BoundaryFamilyV1.LOCAL),
        ("acfqp.phase3e_fallback_v1", boundary_v1.BoundaryFamilyV1.FALLBACK),
        ("acfqp.phase3e_rebuild_runner_v1", boundary_v1.BoundaryFamilyV1.REBUILD),
        ("acfqp.semantic_verification_v1", boundary_v1.BoundaryFamilyV1.VERIFICATION_TERMINAL),
    ),
)
def test_missing_source_for_each_required_family_returns_typed_blocker(
    module_name: str,
    family: boundary_v1.BoundaryFamilyV1,
) -> None:
    archive = dict(_archive())
    del archive[module_name]
    replay = boundary_v1.replay_operation_boundary_source_archive_v1(archive)

    assert replay.outcome is boundary_v1.BoundaryReplayOutcomeV1.BLOCKED
    assert replay.manifest is None
    assert replay.blockers
    assert any(
        row.family is family
        and row.code is boundary_v1.BoundaryBlockerCodeV1.SOURCE_MEMBER_MISSING
        and row.module_name == module_name
        for row in replay.blockers
    )
    assert replay.to_document()["execution_performed"] is False
    assert replay.to_document()["accounting_claim_created"] is False


@pytest.mark.parametrize("module_name", tuple(_archive()))
def test_any_changed_complete_source_bytes_fail_closed(module_name: str) -> None:
    archive = dict(_archive())
    archive[module_name] = archive[module_name] + b"\n# adversarial mutation\n"
    replay = boundary_v1.replay_operation_boundary_source_archive_v1(archive)

    assert replay.outcome is boundary_v1.BoundaryReplayOutcomeV1.BLOCKED
    assert replay.manifest is None
    assert any(
        row.module_name == module_name
        and row.code is boundary_v1.BoundaryBlockerCodeV1.SOURCE_BYTES_CHANGED
        for row in replay.blockers
    )


def test_extra_archive_member_and_nonbytes_member_are_typed_blockers() -> None:
    extra = dict(_archive())
    extra["acfqp.invented_route"] = b"def execute(): pass\n"
    result = boundary_v1.replay_operation_boundary_source_archive_v1(extra)
    assert result.outcome is boundary_v1.BoundaryReplayOutcomeV1.BLOCKED
    assert any(
        row.code is boundary_v1.BoundaryBlockerCodeV1.SOURCE_MEMBER_SET_CHANGED
        for row in result.blockers
    )

    wrong = dict(_archive())
    wrong["acfqp.phase3e_fallback_v1"] = "not bytes"  # type: ignore[assignment]
    result = boundary_v1.replay_operation_boundary_source_archive_v1(wrong)
    assert result.outcome is boundary_v1.BoundaryReplayOutcomeV1.BLOCKED
    assert any(
        row.code is boundary_v1.BoundaryBlockerCodeV1.SOURCE_MEMBER_NOT_BYTES
        for row in result.blockers
    )


def test_manifest_document_replay_rejects_fully_resigned_semantic_change() -> None:
    manifest = _manifest()
    good = boundary_v1.verify_construction_k7_all_path_operation_boundary_manifest_document_v1(
        manifest.to_document(), dict(_archive())
    )
    assert good.outcome is boundary_v1.BoundaryReplayOutcomeV1.VERIFIED
    assert good.manifest is not None
    assert good.manifest.manifest_id == manifest.manifest_id

    attacked = deepcopy(manifest.to_document())
    attacked["sites"][0]["accounting_event_emitted"] = True
    # A caller can replace the displayed ID, but cannot change the independent
    # source/profile replay that defines the authoritative document.
    attacked["operation_boundary_manifest_id"] = "0" * 64
    blocked = boundary_v1.verify_construction_k7_all_path_operation_boundary_manifest_document_v1(
        attacked, dict(_archive())
    )
    assert blocked.outcome is boundary_v1.BoundaryReplayOutcomeV1.BLOCKED
    assert blocked.manifest is None
    assert blocked.blockers[0].code is (
        boundary_v1.BoundaryBlockerCodeV1.MANIFEST_DOCUMENT_CHANGED
    )


def test_caller_cannot_mint_site_manifest_or_spoof_profile() -> None:
    site = _manifest().sites[0]
    with pytest.raises(
        boundary_v1.ConstructionK7AllPathOperationBoundaryManifestV1Error,
        match="caller-minted",
    ):
        replace(site, _issuer=object())
    with pytest.raises(
        boundary_v1.ConstructionK7AllPathOperationBoundaryManifestV1Error,
        match="caller-minted",
    ):
        replace(_manifest(), _issuer=object())

    source_profile = profile_v1.freeze_construction_k7_all_path_accounting_profile_v1()
    # Bypass the profile constructor only to model a hostile in-memory object;
    # the operation-boundary authority must still compare the content identity.
    forged = object.__new__(type(source_profile))
    for descriptor in fields(source_profile):
        object.__setattr__(
            forged,
            descriptor.name,
            "0" * 64
            if descriptor.name == "counter_registry_id"
            else getattr(source_profile, descriptor.name),
        )
    replay = boundary_v1.replay_operation_boundary_source_archive_v1(
        dict(_archive()), profile=forged
    )
    assert replay.outcome is boundary_v1.BoundaryReplayOutcomeV1.BLOCKED
    assert replay.blockers[0].code is (
        boundary_v1.BoundaryBlockerCodeV1.PROFILE_ID_CHANGED
    )


def test_freeze_exposes_typed_blockers_without_creating_partial_manifest() -> None:
    archive = dict(_archive())
    del archive["acfqp.phase3e_fallback_v1"]
    with pytest.raises(
        boundary_v1.ConstructionK7AllPathOperationBoundaryManifestV1Error
    ) as captured:
        boundary_v1.freeze_construction_k7_all_path_operation_boundary_manifest_v1(
            source_archive=archive
        )
    blockers = captured.value.blockers
    assert blockers
    assert all(isinstance(row, boundary_v1.BoundaryBlockerV1) for row in blockers)
    assert any(row.family is boundary_v1.BoundaryFamilyV1.FALLBACK for row in blockers)
