from __future__ import annotations

from dataclasses import replace
from functools import cache
import hashlib

import pytest

from acfqp import construction_accounting_completion_prerequisite_manifest_v1 as manifest_v1
from acfqp import construction_accounting_completion_readiness_v1 as readiness_v1
from acfqp import construction_accounting_evidence_closure_v1 as closure_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_profile_native_zero_rules_v1 as zero_v1
from acfqp import v075_k7_root_cap_execution_identity_overlay_v1 as execution_v1
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as boundary_v3
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:construction-completion-prerequisite-manifest-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


@cache
def _closure(label: str = "current") -> closure_v1.EvidenceClosureV1:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    boundary = boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    execution = execution_v1.official_v075_k7_root_cap_execution_identity_profile_v1()
    context = closure_v1.EvidenceClosureContextV1(
        registry.registry_id,
        stage.stage_profile_id,
        boundary.manifest_id,
        execution.profile_id,
        _id(f"{label}-transcript"),
        _id(f"{label}-terminal"),
    )
    return closure_v1.initialize_evidence_closure_v1(context)


@cache
def _manifest() -> (
    manifest_v1.ConstructionAccountingCompletionPrerequisiteManifestV1
):
    return manifest_v1.freeze_current_completion_prerequisite_manifest_v1(
        _closure()
    )


def test_manifest_binds_every_exact_authority_and_remains_not_ready() -> None:
    closure = _closure()
    manifest = _manifest()
    replay = manifest_v1.verify_current_completion_prerequisite_manifest_v1(
        manifest, evidence_closure=closure
    )
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    projection = registry_v6.official_actual_projection_profile_v6(
        registry, comparison
    )
    boundary = boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    execution = execution_v1.official_v075_k7_root_cap_execution_identity_profile_v1()
    partition = readiness_v1.official_required_path_partition_v1()
    zero_registry = zero_v1.official_profile_native_zero_rule_registry_v1()
    zero_readiness = zero_v1.current_profile_native_zero_rule_readiness_v1()
    owner_coverage = zero_v1.official_owner_boundary_coverage_profile_v1()

    assert manifest.counter_registry_id == registry.registry_id
    assert manifest.stage_profile_id == stage.stage_profile_id
    assert manifest.comparison_profile_id == comparison.comparison_profile_id
    assert manifest.actual_projection_profile_id == (
        projection.actual_projection_profile_id
    )
    assert manifest.boundary_manifest_id == boundary.manifest_id
    assert manifest.execution_profile_id == execution.profile_id
    assert manifest.required_path_partition_id == partition.partition_id
    assert manifest.profile_native_zero_rule_registry_id == zero_registry.registry_id
    assert manifest.profile_native_zero_rule_readiness_id == zero_readiness.readiness_id
    assert manifest.owner_boundary_coverage_profile_id == (
        owner_coverage.coverage_profile_id
    )
    assert manifest.evidence_closure_context_id == closure.context.context_id
    assert manifest.evidence_closure_id == closure.closure_id
    assert manifest.status is (
        manifest_v1.CompletionPrerequisiteStatusV1
        .NOT_READY_MISSING_SEMANTIC_AUTHORITIES
    )
    assert replay.manifest_id == manifest.manifest_id
    assert replay.status is manifest.status

    document = manifest.to_document()
    assert document["unresolved_path_count"] == 202
    assert document["absence_is_zero_evidence"] is False
    assert document["semantic_source_evidence_verified"] is False
    assert document["counter_records_allowed"] is False
    assert document["work_vector_allowed"] is False
    assert document["comparison_vector_allowed"] is False
    assert document["formal_vector_authorized"] is False
    assert document["official_execution_allowed"] is False
    replay_document = replay.to_document()
    assert replay_document["exact_missing_sets_replayed"] is True
    assert replay_document["semantic_source_evidence_verified"] is False
    assert replay_document["formal_vector_authorized"] is False


def test_exact_typed_missing_sets_are_complete_and_disjoint_by_role() -> None:
    manifest = _manifest()
    blockers = manifest.blocker_by_code
    assert len(blockers) == 6

    shared = blockers[
        manifest_v1.CompletionPrerequisiteBlockerCodeV1
        .SHARED_RESOURCE_SEMANTIC_JOIN_NOT_AVAILABLE
    ]
    owner = blockers[
        manifest_v1.CompletionPrerequisiteBlockerCodeV1
        .OWNER_COMPLETE_CLOSURES_MISSING
    ]
    zeros = blockers[
        manifest_v1.CompletionPrerequisiteBlockerCodeV1
        .PROFILE_NATIVE_ZERO_ATTESTATIONS_MISSING
    ]
    derived = blockers[
        manifest_v1.CompletionPrerequisiteBlockerCodeV1
        .DERIVED_RECONCILIATION_PROOFS_MISSING
    ]
    occurrence = blockers[
        manifest_v1.CompletionPrerequisiteBlockerCodeV1
        .OCCURRENCE_IDENTITY_SEMANTIC_AUTHORITY_NOT_AVAILABLE
    ]
    cutoff = blockers[
        manifest_v1.CompletionPrerequisiteBlockerCodeV1
        .OPERATIONAL_CUTOFF_SEMANTIC_AUTHORITY_NOT_AVAILABLE
    ]

    assert len(shared.affected_paths) == len(shared.missing_subject_keys) == 9
    assert len(owner.affected_paths) == 71
    assert len(owner.missing_subject_keys) == 445
    assert len(owner.missing_subject_ids) == 89
    assert len(zeros.affected_paths) == 114
    assert len(zeros.missing_subject_keys) == 588
    assert len(zeros.missing_subject_ids) == 114
    assert len(derived.affected_paths) == len(derived.missing_subject_keys) == 8
    assert len(occurrence.affected_paths) == len(cutoff.affected_paths) == 202
    assert set(shared.affected_paths).isdisjoint(owner.affected_paths)
    assert set(shared.affected_paths).isdisjoint(zeros.affected_paths)
    assert set(shared.affected_paths).isdisjoint(derived.affected_paths)
    assert set(owner.affected_paths).isdisjoint(zeros.affected_paths)
    assert set(owner.affected_paths).isdisjoint(derived.affected_paths)
    assert set(zeros.affected_paths).isdisjoint(derived.affected_paths)
    assert (
        set(shared.affected_paths)
        | set(owner.affected_paths)
        | set(zeros.affected_paths)
        | set(derived.affected_paths)
    ) == set(manifest.unresolved_paths)

    for blocker in manifest.blockers:
        document = blocker.to_document()
        assert blocker.reference_state == "NOT_AVAILABLE"
        assert document["evidence_artifact_id"]["kind"] == "NOT_AVAILABLE"
        assert document["absence_is_zero_evidence"] is False
        assert document["semantic_authority_present"] is False
        assert document["formal_accounting_authority"] is False

    document = manifest.to_document()
    assert len(document["profile_native_zero_rule_ids"]) == 114
    assert len(document["profile_native_zero_readiness_row_ids"]) == 114
    assert len(document["owner_boundary_coverage_site_ids"]) == 89
    assert len(document["missing_profile_native_zero_obligation_keys"]) == 588
    assert len(document["missing_owner_boundary_evidence_keys"]) == 445
    assert len(document["semantic_missing_required_paths"]) == 202


def test_cross_profile_identity_and_catalogue_substitution_are_rejected() -> None:
    manifest = _manifest()
    for field_name in (
        "counter_registry_id",
        "stage_profile_id",
        "comparison_profile_id",
        "actual_projection_profile_id",
        "boundary_manifest_id",
        "execution_profile_id",
        "required_path_partition_id",
        "profile_native_zero_rule_registry_id",
        "profile_native_zero_rule_readiness_id",
        "owner_boundary_coverage_profile_id",
    ):
        with pytest.raises(
            manifest_v1.ConstructionAccountingCompletionPrerequisiteV1Error,
            match="exact current missing graph",
        ):
            replace(
                manifest,
                _issuer=manifest_v1._MANIFEST_ISSUER,  # noqa: SLF001 - attack
                **{field_name: _id(f"foreign-{field_name}")},
            )


def test_omitted_blocker_or_subject_is_rejected() -> None:
    manifest = _manifest()
    with pytest.raises(
        manifest_v1.ConstructionAccountingCompletionPrerequisiteV1Error,
        match="exact current missing graph",
    ):
        replace(
            manifest,
            _issuer=manifest_v1._MANIFEST_ISSUER,  # noqa: SLF001 - attack
            blockers=manifest.blockers[:-1],
        )

    for field_name in (
        "profile_native_zero_rule_ids",
        "profile_native_zero_readiness_row_ids",
        "owner_boundary_coverage_site_ids",
    ):
        with pytest.raises(
            manifest_v1.ConstructionAccountingCompletionPrerequisiteV1Error,
            match="exact current missing graph",
        ):
            replace(
                manifest,
                _issuer=manifest_v1._MANIFEST_ISSUER,  # noqa: SLF001 - attack
                **{field_name: getattr(manifest, field_name)[:-1]},
            )

    owner_code = (
        manifest_v1.CompletionPrerequisiteBlockerCodeV1
        .OWNER_COMPLETE_CLOSURES_MISSING
    )
    changed = []
    for blocker in manifest.blockers:
        if blocker.code is owner_code:
            blocker = replace(
                blocker,
                _issuer=manifest_v1._BLOCKER_ISSUER,  # noqa: SLF001 - attack
                missing_subject_ids=blocker.missing_subject_ids[1:],
            )
        changed.append(blocker)
    with pytest.raises(
        manifest_v1.ConstructionAccountingCompletionPrerequisiteV1Error,
        match="exact current missing graph",
    ):
        replace(
            manifest,
            _issuer=manifest_v1._MANIFEST_ISSUER,  # noqa: SLF001 - attack
            blockers=tuple(changed),
        )

    zero_code = (
        manifest_v1.CompletionPrerequisiteBlockerCodeV1
        .PROFILE_NATIVE_ZERO_ATTESTATIONS_MISSING
    )
    changed = []
    for blocker in manifest.blockers:
        if blocker.code is zero_code:
            blocker = replace(
                blocker,
                _issuer=manifest_v1._BLOCKER_ISSUER,  # noqa: SLF001 - attack
                missing_subject_keys=blocker.missing_subject_keys[1:],
            )
        changed.append(blocker)
    with pytest.raises(
        manifest_v1.ConstructionAccountingCompletionPrerequisiteV1Error,
        match="exact current missing graph",
    ):
        replace(
            manifest,
            _issuer=manifest_v1._MANIFEST_ISSUER,  # noqa: SLF001 - attack
            blockers=tuple(changed),
        )


def test_stale_occurrence_closure_cannot_replay_an_existing_manifest() -> None:
    original_closure = _closure()
    manifest = _manifest()
    stale_closure = _closure("stale")
    with pytest.raises(
        manifest_v1.ConstructionAccountingCompletionPrerequisiteV1Error,
        match="differs from deterministic replay",
    ):
        manifest_v1.verify_current_completion_prerequisite_manifest_v1(
            manifest, evidence_closure=stale_closure
        )


def test_current_factory_rejects_even_one_synthetic_resolution() -> None:
    closure = _closure()
    zero_path = readiness_v1.official_required_path_partition_v1().profile_static_zero_paths[0]
    changed = closure_v1.resolve_profile_native_zero_v1(
        closure,
        path=zero_path,
        zero_attestation_id=_id("synthetic-zero-attestation"),
    )
    with pytest.raises(
        manifest_v1.ConstructionAccountingCompletionPrerequisiteV1Error,
        match="all-UNRESOLVED 202-path closure",
    ):
        manifest_v1.freeze_current_completion_prerequisite_manifest_v1(changed)


def test_local_domains_are_registered_centrally() -> None:
    assert len(manifest_v1.LOCAL_DOMAIN_TAGS) == 3
    assert manifest_v1.REQUESTED_PHASE3E_DOMAIN_CONSTANTS == tuple(
        sorted(manifest_v1.REQUESTED_PHASE3E_DOMAIN_CONSTANTS)
    )
    assert all(
        value.startswith("acfqp:construction-accounting-completion-prerequisite-")
        and value.endswith(":v1")
        for value in manifest_v1.LOCAL_DOMAIN_TAGS
    )
    assert manifest_v1.LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS
