from __future__ import annotations

from collections import Counter

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_profile_native_zero_rules_v1 as zero_v1
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as boundary_v3
from acfqp.accounting_v1 import LaneEnum
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def _authoritative_partition() -> tuple[set[str], set[str], set[str], set[str]]:
    registry = registry_v6.official_counter_registry_v6()
    manifest = boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    shared = set(zero_v1.SHARED_RESOURCE_PATHS)
    derived = {
        path
        for path in registry.required_paths
        if registry.by_path[path].lane is LaneEnum.DERIVED_ONLY
    }
    emittable = {
        row.target_path
        for row in manifest.boundaries
        if row.to_document()["emittable_in_this_fixture"] is True
    }
    static_zero = set(registry.required_paths) - shared - derived - emittable
    return shared, derived, static_zero, emittable


def test_exact_v6_partition_and_114_path_rule_catalogue() -> None:
    registry = registry_v6.official_counter_registry_v6()
    rules = zero_v1.official_profile_native_zero_rule_registry_v1()
    shared, derived, static_zero, emittable = _authoritative_partition()

    assert len(registry.required_paths) == 202
    assert tuple(map(len, (shared, derived, static_zero, emittable))) == (
        9,
        8,
        114,
        71,
    )
    assert not (shared & derived or shared & static_zero or shared & emittable)
    assert not (derived & static_zero or derived & emittable or static_zero & emittable)
    assert shared | derived | static_zero | emittable == set(registry.required_paths)
    assert set(rules.by_path) == static_zero
    assert rules.to_document()["formal_vectors_allowed"] is False
    assert rules.to_document()["native_zero_attestations_issued"] is False


def test_every_zero_rule_is_path_specific_and_requires_live_evidence() -> None:
    rules = zero_v1.official_profile_native_zero_rule_registry_v1()
    mandatory = {
        zero_v1.ProfileNativeZeroEvidenceKindV1.BRANCH_NONEXECUTION,
        zero_v1.ProfileNativeZeroEvidenceKindV1.EXECUTION_IDENTITY,
        zero_v1.ProfileNativeZeroEvidenceKindV1.LOADED_CODE_IDENTITY,
        zero_v1.ProfileNativeZeroEvidenceKindV1.STAGE_EXECUTION,
        zero_v1.ProfileNativeZeroEvidenceKindV1.ZERO_SEMANTIC_VERIFIER,
    }

    for rule in rules.rules:
        document = rule.to_document()
        kinds = {item.kind for item in rule.evidence_requirements}
        keys = {item.obligation_key for item in rule.evidence_requirements}
        assert mandatory <= kinds
        assert all(key.endswith(rule.path) for key in keys)
        assert rule.path in rule.path_specific_reason
        assert document["absence_is_zero_evidence"] is False
        assert document["live_attestation_allowed"] is False
        assert document["native_zero_attestation_issued"] is False
        if rule.replacement_paths:
            assert (
                zero_v1.ProfileNativeZeroEvidenceKindV1.REPLACEMENT_PATH_RESOLUTION
                in kinds
            )

    assert Counter(rule.reason_code for rule in rules.rules) == {
        zero_v1.ProfileNativeZeroReasonCodeV1.K7_PROFILE_BRANCH_NOT_EXECUTED: 62,
        zero_v1.ProfileNativeZeroReasonCodeV1.FORBIDDEN_STAGE_NOT_EXECUTED: 34,
        zero_v1.ProfileNativeZeroReasonCodeV1.LEGACY_OWNER_REPLACED: 16,
        zero_v1.ProfileNativeZeroReasonCodeV1.LEGACY_SEMANTIC_SPLIT_REPLACED: 2,
    }


def test_readiness_is_typed_but_all_114_paths_remain_blocked() -> None:
    rules = zero_v1.official_profile_native_zero_rule_registry_v1()
    readiness = zero_v1.current_profile_native_zero_rule_readiness_v1()
    document = readiness.to_document()

    assert readiness.rule_registry_id == rules.registry_id
    assert len(readiness.rows) == 114
    assert tuple(row.path for row in readiness.rows) == tuple(
        rule.path for rule in rules.rules
    )
    for row, rule in zip(readiness.rows, rules.rules, strict=True):
        row_document = row.to_document()
        assert row.status is (
            zero_v1.ProfileNativeZeroRuleReadinessStatusV1
            .BLOCKED_MISSING_PREREQUISITES
        )
        assert row.missing_obligation_keys == tuple(
            sorted(item.obligation_key for item in rule.evidence_requirements)
        )
        assert row_document["satisfied_obligation_keys"] == []
        assert row_document["stage_evidence_present"] is False
        assert row_document["branch_evidence_present"] is False
        assert row_document["loaded_code_evidence_present"] is False
        assert row_document["live_attestation_allowed"] is False

    assert document["blocked_path_count"] == 114
    assert document["live_ready_path_count"] == 0
    assert document["absence_is_zero_evidence"] is False
    assert document["native_zero_attestations_issued"] is False
    assert document["formal_vectors_allowed"] is False


def test_owner_boundary_profile_is_exactly_71_paths_and_89_sites() -> None:
    manifest = boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    expected_rows = tuple(
        row
        for row in manifest.boundaries
        if row.to_document()["emittable_in_this_fixture"] is True
    )
    profile = zero_v1.official_owner_boundary_coverage_profile_v1()
    document = profile.to_document()

    assert len(expected_rows) == len(profile.sites) == 89
    assert len({row.target_path for row in expected_rows}) == 71
    assert len({site.path for site in profile.sites}) == 71
    assert tuple(site.boundary_id for site in profile.sites) == tuple(
        row.boundary_id for row in expected_rows
    )
    assert tuple(site.path for site in profile.sites) == tuple(
        row.target_path for row in expected_rows
    )
    for site in profile.sites:
        assert site.required_evidence_keys == tuple(
            sorted(
                (
                    f"active_stage_binding:{site.boundary_key}",
                    f"direct_caller_owner_binding:{site.boundary_key}",
                    f"loaded_module_bytes:{site.boundary_key}",
                    f"runtime_event_transcript:{site.boundary_key}",
                    f"source_symbol_code_identity:{site.boundary_key}",
                )
            )
        )
        site_document = site.to_document()
        assert site_document["schema_coverage_frozen"] is True
        assert site_document["loaded_code_evidence_present"] is False
        assert site_document["runtime_event_evidence_present"] is False
        assert site_document["live_boundary_closed"] is False

    assert document["emittable_path_count"] == 71
    assert document["emittable_site_count"] == 89
    assert document["schema_coverage_frozen"] is True
    assert document["loaded_code_coverage_ready"] is False
    assert document["runtime_event_coverage_ready"] is False
    assert document["live_owner_boundaries_closed"] is False
    assert document["formal_vectors_allowed"] is False


def test_no_native_zero_attestation_can_be_opened_without_evidence() -> None:
    with pytest.raises(zero_v1.ProfileNativeZeroLiveEvidenceNotReady):
        zero_v1.open_profile_native_zero_attestation_v1(
            path="any.path",
            stage_evidence_id="missing",
            branch_evidence_id="missing",
            loaded_code_evidence_id="missing",
        )


def test_domains_are_unique_and_centrally_registered() -> None:
    assert len(zero_v1.LOCAL_DOMAIN_TAGS) == 6
    assert len(zero_v1.REQUESTED_PHASE3E_DOMAIN_CONSTANTS) == 6
    assert all(
        value.startswith("acfqp:construction-") and value.endswith(":v1")
        for value in zero_v1.LOCAL_DOMAIN_TAGS
    )
    assert zero_v1.REQUESTED_PHASE3E_DOMAIN_CONSTANTS == tuple(
        sorted(zero_v1.REQUESTED_PHASE3E_DOMAIN_CONSTANTS)
    )
    assert zero_v1.LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS
