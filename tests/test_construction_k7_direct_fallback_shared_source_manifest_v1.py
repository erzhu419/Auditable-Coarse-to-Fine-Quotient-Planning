from __future__ import annotations

import copy
import hashlib
import inspect

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_cap_authority_v1 as cap_v1
from acfqp import phase3e_ids
from acfqp import construction_k7_direct_fallback_shared_source_manifest_v1 as source_v1
from acfqp.construction_shared_cap_authority_v1 import (
    freeze_construction_fallback_decision_candidate_v1,
    freeze_direct_fallback_shared_cap_profile_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json
from acfqp.routing_v1 import RouteDecisionContextV1


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:shared-source-manifest-test:v2\x00" + label.encode("utf-8")
    ).hexdigest()


def test_exact_nine_path_manifest_is_deterministic_and_v6_bound() -> None:
    first = source_v1.freeze_direct_fallback_shared_source_manifest_v1()
    second = source_v1.freeze_direct_fallback_shared_source_manifest_v1()
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)

    assert first.canonical_bytes == second.canonical_bytes
    assert first.manifest_id == second.manifest_id
    assert len(first.sites) == source_v1.EXPECTED_PATH_COUNT == 9
    assert tuple(site.path for site in first.sites) == source_v1.SHARED_RESOURCE_PATHS
    assert len({site.source_site_id for site in first.sites}) == 9
    assert first.counter_registry_id == registry.registry_id
    assert first.stage_profile_id == stage.stage_profile_id
    assert first.comparison_profile_id == comparison.comparison_profile_id
    assert all(
        site.reducer is registry.by_path[site.path].reducer
        and site.unit == registry.by_path[site.path].unit
        for site in first.sites
    )


def test_manifest_freezes_owner_protocol_and_cross_site_ordering() -> None:
    manifest = source_v1.freeze_direct_fallback_shared_source_manifest_v1()
    sites = {site.path: site for site in manifest.sites}
    edges = {
        (edge.predecessor, edge.successor)
        for edge in manifest.cross_site_ordering
    }
    assert all(
        site.successor_owner_module.endswith(
            "construction_k7_direct_fallback_shared_resource_owner_v1"
        )
        for site in manifest.sites
    )
    assert all(
        tuple(step.ordinal for step in site.operation_steps)
        == tuple(range(1, len(site.operation_steps) + 1))
        for site in manifest.sites
    )
    assert ("shared.output:admit", "shared.launch:admit") in edges
    assert ("shared.memory:bind", "shared.launch:admit") in edges
    assert ("shared.memory:reap", "shared.mount:close") in edges
    assert sites["io.read_bytes"].operation_steps[-1].step_key == "authenticate"
    assert sites["io.staged_bytes"].operation_steps[0].step_key == "classify"


def test_typed_formula_schema_has_no_numeric_candidate_or_dummy_terms() -> None:
    manifest = source_v1.freeze_direct_fallback_shared_source_manifest_v1()
    formulas = {row.path: row.to_document() for row in manifest.aggregate_formulas}
    output = formulas["io.output_bytes"]
    memory = formulas["memory.working_bytes_peak"]
    read = formulas["io.read_bytes"]

    def group(row, key):
        return next(
            item for item in row["operand_groups"]
            if item["group_key_semantics"] == key
        )

    assert output["formula_kind"] == "VERIFIED_ROUTE_OUTPUT_FIXED_POINT"
    assert group(output, "registered-output-role")["required_exact_group_count"] == 8
    assert group(output, "fixed-point-attestation")["required_operand_roles"] == [
        "OUTPUT_FIXED_POINT_RESULT_ID"
    ]
    assert "OUTPUT_ROLE_EXTENT_UPPER_BYTES" in group(
        output, "registered-output-role"
    )["required_operand_roles"]
    assert memory["formula_kind"] == "MIN_OUTER_CAP_AND_SUM_ROLE_CAPS"
    assert group(memory, "production-role-cgroup-cap")["required_exact_group_count"] == 2
    assert "OUTER_CGROUP_CAP_BYTES" in group(
        memory, "outer-cgroup-hierarchy"
    )["required_operand_roles"]
    assert "ROLE_CGROUP_CAP_BYTES" in group(
        memory, "production-role-cgroup-cap"
    )["required_operand_roles"]
    assert "SAME_OFD_PEAK_PLAN_ID" in group(
        memory, "outer-cgroup-hierarchy"
    )["required_operand_roles"]
    assert read["formula_kind"] == "SUM_PAIRED_COUNT_TIMES_EXTENT"
    read_group = group(read, "registered-read-family")
    assert "READ_OPERATION_COUNT" in read_group["required_operand_roles"]
    assert "READ_EXTENT_UPPER_BYTES" in read_group["required_operand_roles"]
    assert all(
        group_row["zero_multiplicity_placeholder_allowed"] is False
        for row in formulas.values()
        for group_row in row["operand_groups"]
    )
    assert all(row["numeric_candidate_issued"] is False for row in formulas.values())
    assert all(
        row["operand_evidence_reuse_across_paths_allowed"] is False
        and row["shared_admission_operand_reuse_allowed"] is False
        for row in formulas.values()
    )
    assert not hasattr(source_v1, "freeze_aggregate_cap_evidence_candidate_v1")
    assert source_v1.NUMERICAL_AGGREGATE_CAP_CANDIDATE_ISSUED is False


def test_common_mount_launch_and_admission_schema_are_explicit() -> None:
    manifest = source_v1.freeze_direct_fallback_shared_source_manifest_v1()
    formulas = {row.path: row.to_document() for row in manifest.aggregate_formulas}
    for path in (
        "common.hash_invocations",
        "common.integrity_checks",
        "common.protocol_checks",
    ):
        roles = {
            role
            for group in formulas[path]["operand_groups"]
            for role in group["required_operand_roles"]
        }
        assert "REGISTERED_EVENT_COUNT" in roles
        assert "UNIT_ONE" in roles
    mount_roles = {
        role
        for group in formulas["io.mounted_bytes_peak"]["operand_groups"]
        for role in group["required_operand_roles"]
    }
    assert {
        "PAYLOAD_IDENTITY",
        "PAYLOAD_EXTENT_BYTES",
        "VISIBILITY_OPEN_SEQUENCE",
        "VISIBILITY_CLOSE_SEQUENCE",
    } <= set(mount_roles)
    launch_group = next(
        group
        for group in formulas["process.launches"]["operand_groups"]
        if group["group_key_semantics"] == "registered-production-role"
    )
    assert launch_group["required_exact_group_count"] == 2
    assert all(
        any(
            group["required_operand_roles"] == ["SHARED_ADMISSION_COUNT"]
            and group["required_exact_group_count"] == 1
            for group in row["operand_groups"]
        )
        for row in formulas.values()
    )
    document = manifest.to_document()
    assert document["canonical_owner_control_cap_checks_upper"] == 56
    assert document[
        "every_shared_admission_requires_one_nonrecursive_control_cap_check"
    ] is True
    assert document["failure_path_control_cap_rejection_upper_required"] is True


def test_manifest_is_explicitly_unwired_nonformal_and_domain_registered() -> None:
    manifest = source_v1.freeze_direct_fallback_shared_source_manifest_v1()
    document = manifest.to_document()
    assert set(source_v1.REQUESTED_PHASE3E_DOMAIN_TAGS) <= phase3e_ids.PHASE3E_DOMAIN_TAGS
    assert len(set(source_v1.REQUESTED_PHASE3E_DOMAIN_TAGS)) == 4
    assert document["numeric_aggregate_cap_candidate_issued"] is False
    assert document["source_site_manifest_semantically_verified"] is False
    assert document["production_owner_sites_wired"] is False
    assert document["aggregate_cardinality_evidence_verified"] is False
    assert document["formal_v7_route_decision_authority_present"] is False
    assert document["formal_actual_compliance_eligible"] is False
    assert document["official_execution_allowed"] is False
    assert document["blocker"] == source_v1.BLOCKER


def _cap_join_inputs():
    manifest = source_v1.freeze_direct_fallback_shared_source_manifest_v1()
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    context = RouteDecisionContextV1(
        _id("preregistration"), _id("protocol"), comparison.comparison_profile_id,
        registry.registry_id, _id("structural"), _id("query"), _id("plan"),
        _id("threshold"), _id("epoch"), _id("occurrence"), _id("attempt"),
    )
    candidate = freeze_construction_fallback_decision_candidate_v1(
        route_context=context,
        decision_point_id=_id("point"),
        fallback_upper_candidate_id=_id("upper"),
        preexecution_barrier_id=_id("barrier"),
    )
    return manifest, stage, context, candidate


def test_manifest_bound_join_derives_site_ids_without_caller_input() -> None:
    manifest, stage, context, candidate = _cap_join_inputs()
    join = source_v1.freeze_manifest_bound_shared_cap_profile_join_v1(
        manifest_bytes=manifest.canonical_bytes,
        route_context=context,
        route_decision_candidate=candidate,
        stage_profile_id=stage.stage_profile_id,
        caps={path: 1000 for path in source_v1.SHARED_RESOURCE_PATHS},
        max_control_cap_checks=1000,
    )
    profile = join.cap_profile
    assert profile.source_site_manifest_id == manifest.manifest_id
    assert all(
        profile.by_path[path].source_site_ids == manifest.source_site_ids[path]
        for path in source_v1.SHARED_RESOURCE_PATHS
    )
    assert profile.to_document()["production_owner_sites_wired"] is False
    document = join.to_document()
    assert document["manifest_bytes_independently_replayed"] is True
    assert document["site_ids_derived_internally_from_manifest"] is True
    assert document["caller_supplied_site_ids_accepted"] is False
    assert document["legacy_generic_factory_alone_proves_manifest_join"] is False
    parameters = inspect.signature(
        source_v1.freeze_manifest_bound_shared_cap_profile_join_v1
    ).parameters
    assert "source_site_ids" not in parameters
    assert "source_site_manifest_id" not in parameters


def test_manifest_bound_join_uses_only_byte_derived_sites_under_property_patch(
    monkeypatch,
) -> None:
    manifest, stage, context, candidate = _cap_join_inputs()
    raw_document = loads_canonical_json(manifest.canonical_bytes)
    expected_sites = {
        row["path"]: (row["source_site_id"],)
        for row in raw_document["sites"]
    }

    def forbidden_property(_self):
        raise AssertionError("manifest.source_site_ids must not be authoritative")

    monkeypatch.setattr(
        source_v1.DirectFallbackSharedSourceManifestV1,
        "source_site_ids",
        property(forbidden_property),
    )
    join = source_v1.freeze_manifest_bound_shared_cap_profile_join_v1(
        manifest_bytes=manifest.canonical_bytes,
        route_context=context,
        route_decision_candidate=candidate,
        stage_profile_id=stage.stage_profile_id,
        caps={path: 1000 for path in source_v1.SHARED_RESOURCE_PATHS},
        max_control_cap_checks=1000,
    )
    assert {
        path: join.cap_profile.by_path[path].source_site_ids
        for path in source_v1.SHARED_RESOURCE_PATHS
    } == expected_sites


def test_runtime_public_manifest_verifier_and_factory_patch_cannot_bypass_bytes(
    monkeypatch,
) -> None:
    manifest, stage, context, candidate = _cap_join_inputs()
    document = loads_canonical_json(manifest.canonical_bytes)
    document["sites"][0]["source_site_id"] = _id("runtime-patch-site")
    payload = {
        key: value
        for key, value in document.items()
        if key != "source_site_manifest_id"
    }
    document["source_site_manifest_id"] = content_id(
        source_v1.SOURCE_MANIFEST_DOMAIN, payload
    )
    monkeypatch.setattr(
        source_v1,
        "verify_direct_fallback_shared_source_manifest_bytes_v1",
        lambda _raw: manifest,
    )
    monkeypatch.setattr(
        source_v1,
        "freeze_direct_fallback_shared_source_manifest_v1",
        lambda: manifest,
    )
    with pytest.raises(
        source_v1.ConstructionK7DirectFallbackSharedSourceManifestV1Error,
        match="differs from exact independent replay",
    ):
        source_v1.freeze_manifest_bound_shared_cap_profile_join_v1(
            manifest_bytes=canonical_json_bytes(document),
            route_context=context,
            route_decision_candidate=candidate,
            stage_profile_id=stage.stage_profile_id,
            caps={path: 1000 for path in source_v1.SHARED_RESOURCE_PATHS},
            max_control_cap_checks=1000,
        )


def test_manifest_canonical_bytes_property_patch_cannot_admit_tampered_raw(
    monkeypatch,
) -> None:
    manifest, stage, context, candidate = _cap_join_inputs()
    document = loads_canonical_json(manifest.canonical_bytes)
    document["sites"][0]["source_site_id"] = _id("property-patch-site")
    payload = {
        key: value
        for key, value in document.items()
        if key != "source_site_manifest_id"
    }
    document["source_site_manifest_id"] = content_id(
        source_v1.SOURCE_MANIFEST_DOMAIN, payload
    )
    tampered_raw = canonical_json_bytes(document)
    monkeypatch.setattr(
        source_v1.DirectFallbackSharedSourceManifestV1,
        "canonical_bytes",
        property(lambda _self: tampered_raw),
    )
    with pytest.raises(
        source_v1.ConstructionK7DirectFallbackSharedSourceManifestV1Error,
        match="differs from exact independent replay",
    ):
        source_v1.freeze_manifest_bound_shared_cap_profile_join_v1(
            manifest_bytes=tampered_raw,
            route_context=context,
            route_decision_candidate=candidate,
            stage_profile_id=stage.stage_profile_id,
            caps={path: 1000 for path in source_v1.SHARED_RESOURCE_PATHS},
            max_control_cap_checks=1000,
        )


def test_runtime_historical_cap_factory_patch_fails_closed(monkeypatch) -> None:
    manifest, stage, context, candidate = _cap_join_inputs()
    monkeypatch.setattr(
        cap_v1,
        "freeze_direct_fallback_shared_cap_profile_v1",
        lambda **_kwargs: None,
    )
    with pytest.raises(
        source_v1.ConstructionK7DirectFallbackSharedSourceManifestV1Error,
        match="factory or live verifier binding changed",
    ):
        source_v1.freeze_manifest_bound_shared_cap_profile_join_v1(
            manifest_bytes=manifest.canonical_bytes,
            route_context=context,
            route_decision_candidate=candidate,
            stage_profile_id=stage.stage_profile_id,
            caps={path: 1000 for path in source_v1.SHARED_RESOURCE_PATHS},
            max_control_cap_checks=1000,
        )


def test_legacy_exact_manifest_id_with_fake_site_ids_cannot_be_joined() -> None:
    manifest, stage, context, candidate = _cap_join_inputs()
    fake_sites = manifest.source_site_ids
    fake_sites["io.read_bytes"] = (_id("fake-read-site"),)
    legacy_profile = freeze_direct_fallback_shared_cap_profile_v1(
        route_context=context,
        route_decision_candidate=candidate,
        stage_profile_id=stage.stage_profile_id,
        source_site_manifest_id=manifest.manifest_id,
        caps={path: 1000 for path in source_v1.SHARED_RESOURCE_PATHS},
        source_site_ids=fake_sites,
        max_control_cap_checks=1000,
    )
    assert legacy_profile.source_site_manifest_id == manifest.manifest_id
    assert (
        legacy_profile.by_path["io.read_bytes"].source_site_ids
        != manifest.source_site_ids["io.read_bytes"]
    )
    with pytest.raises(
        source_v1.ConstructionK7DirectFallbackSharedSourceManifestV1Error,
        match="exact manifest-bound cap-profile join type",
    ):
        source_v1.require_manifest_bound_shared_cap_profile_join_v1(
            legacy_profile
        )


def test_manifest_bound_join_rejects_tampered_bytes_with_recomputed_top_id() -> None:
    manifest, stage, context, candidate = _cap_join_inputs()
    document = loads_canonical_json(manifest.canonical_bytes)
    document["sites"][0]["source_site_id"] = _id("tampered-site")
    payload = {
        key: value
        for key, value in document.items()
        if key != "source_site_manifest_id"
    }
    document["source_site_manifest_id"] = content_id(
        source_v1.SOURCE_MANIFEST_DOMAIN, payload
    )
    with pytest.raises(
        source_v1.ConstructionK7DirectFallbackSharedSourceManifestV1Error,
        match="differs from exact independent replay",
    ):
        source_v1.freeze_manifest_bound_shared_cap_profile_join_v1(
            manifest_bytes=canonical_json_bytes(document),
            route_context=context,
            route_decision_candidate=candidate,
            stage_profile_id=stage.stage_profile_id,
            caps={path: 1000 for path in source_v1.SHARED_RESOURCE_PATHS},
            max_control_cap_checks=1000,
        )


def test_manifest_bound_join_object_new_and_reseal_attacks_fail_typed() -> None:
    manifest, stage, context, candidate = _cap_join_inputs()
    join = source_v1.freeze_manifest_bound_shared_cap_profile_join_v1(
        manifest_bytes=manifest.canonical_bytes,
        route_context=context,
        route_decision_candidate=candidate,
        stage_profile_id=stage.stage_profile_id,
        caps={path: 1000 for path in source_v1.SHARED_RESOURCE_PATHS},
        max_control_cap_checks=1000,
    )
    forged = object.__new__(source_v1.ManifestBoundSharedCapProfileJoinV1)
    with pytest.raises(
        source_v1.ConstructionK7DirectFallbackSharedSourceManifestV1Error,
        match="not a live issuer artifact",
    ):
        forged.to_document()

    object.__setattr__(join, "_manifest_id", _id("changed-manifest"))
    object.__setattr__(
        join,
        "_join_id",
        content_id(source_v1.MANIFEST_BOUND_CAP_JOIN_DOMAIN, join._payload_unchecked()),
    )
    with pytest.raises(
        source_v1.ConstructionK7DirectFallbackSharedSourceManifestV1Error,
        match=(
            "manifest ID and source-site IDs|byte-derived identity binding|"
            "changed after issuer sealing"
        ),
    ):
        join.to_document()


def test_manifest_bound_join_rejects_copied_nested_legacy_profile() -> None:
    manifest, stage, context, candidate = _cap_join_inputs()
    join = source_v1.freeze_manifest_bound_shared_cap_profile_join_v1(
        manifest_bytes=manifest.canonical_bytes,
        route_context=context,
        route_decision_candidate=candidate,
        stage_profile_id=stage.stage_profile_id,
        caps={path: 1000 for path in source_v1.SHARED_RESOURCE_PATHS},
        max_control_cap_checks=1000,
    )
    copied = copy.copy(join.cap_profile)
    assert copied is not join.cap_profile
    object.__setattr__(join, "_cap_profile", copied)
    with pytest.raises(
        source_v1.ConstructionK7DirectFallbackSharedSourceManifestV1Error,
        match="failed live replay",
    ):
        join.to_document()


def test_independent_byte_verifier_accepts_only_exact_registered_manifest() -> None:
    manifest = source_v1.freeze_direct_fallback_shared_source_manifest_v1()
    verified = source_v1.verify_direct_fallback_shared_source_manifest_bytes_v1(
        manifest.canonical_bytes
    )
    assert verified.manifest_id == manifest.manifest_id

    document = loads_canonical_json(manifest.canonical_bytes)
    document["sites"][0]["site_key"] = "shared.changed"
    payload = {
        key: value
        for key, value in document.items()
        if key != "source_site_manifest_id"
    }
    document["source_site_manifest_id"] = content_id(
        source_v1.SOURCE_MANIFEST_DOMAIN, payload
    )
    with pytest.raises(
        source_v1.ConstructionK7DirectFallbackSharedSourceManifestV1Error,
        match="differs from exact independent replay",
    ):
        source_v1.verify_direct_fallback_shared_source_manifest_bytes_v1(
            canonical_json_bytes(document)
        )


def test_object_setattr_plus_recomputed_id_cannot_reseal_site_or_formula() -> None:
    manifest = source_v1.freeze_direct_fallback_shared_source_manifest_v1()
    site = manifest.sites[0]
    object.__setattr__(site, "site_key", "shared.changed")
    object.__setattr__(
        site,
        "source_site_id",
        content_id(source_v1.SOURCE_SITE_DOMAIN, site._payload()),
    )
    with pytest.raises(
        source_v1.ConstructionK7DirectFallbackSharedSourceManifestV1Error,
        match="changed after issuance",
    ):
        site.to_document()

    formula = manifest.aggregate_formulas[0]
    object.__setattr__(
        formula,
        "semantic_authority_requirement",
        "changed-semantic-authority",
    )
    object.__setattr__(
        formula,
        "formula_spec_id",
        content_id(source_v1.AGGREGATE_FORMULA_SPEC_DOMAIN, formula._payload()),
    )
    with pytest.raises(
        source_v1.ConstructionK7DirectFallbackSharedSourceManifestV1Error,
        match="changed after issuance",
    ):
        formula.to_document()


def test_source_site_ids_self_validate_and_manifest_reseal_attack_fails() -> None:
    manifest = source_v1.freeze_direct_fallback_shared_source_manifest_v1()
    object.__setattr__(manifest.sites[0], "site_key", "shared.changed")
    with pytest.raises(
        source_v1.ConstructionK7DirectFallbackSharedSourceManifestV1Error,
        match="changed after issuance",
    ):
        _ = manifest.source_site_ids

    manifest = source_v1.freeze_direct_fallback_shared_source_manifest_v1()
    object.__setattr__(manifest, "comparison_profile_id", _id("changed"))
    object.__setattr__(
        manifest,
        "manifest_id",
        content_id(source_v1.SOURCE_MANIFEST_DOMAIN, manifest._payload()),
    )
    with pytest.raises(
        source_v1.ConstructionK7DirectFallbackSharedSourceManifestV1Error,
        match="changed after issuance",
    ):
        manifest.to_document()


def test_object_new_same_bytes_is_not_a_live_issuer_artifact() -> None:
    manifest = source_v1.freeze_direct_fallback_shared_source_manifest_v1()
    site = manifest.sites[0]
    forged = object.__new__(source_v1.DirectFallbackSharedSourceSiteV1)
    for field_name in (
        "path", "site_key", "reducer", "unit", "admission_primitive",
        "successor_owner_module", "successor_owner_symbol", "downstream_module",
        "downstream_symbol", "operation_steps", "source_site_id",
    ):
        object.__setattr__(forged, field_name, getattr(site, field_name))
    with pytest.raises(
        source_v1.ConstructionK7DirectFallbackSharedSourceManifestV1Error,
        match="not a live issuer-retained artifact",
    ):
        forged.to_document()
