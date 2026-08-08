from __future__ import annotations

import copy
import hashlib

import pytest

from acfqp import construction_k7_h1_production_output_upper_v1 as output_v1
from acfqp import construction_k7_h1_shared_cap_owner_v2 as cap_owner_v2
from acfqp import construction_k7_h1_shared_resource_catalogues_v1 as catalogues_v1
from acfqp import phase3e_ids
from acfqp.phase3e_ids import canonical_json_bytes, content_id


def _program() -> catalogues_v1.H1SharedResourceBranchProgramV1:
    return catalogues_v1.registered_h1_shared_resource_branch_program_candidate_v1()


def _resign_program(document: dict) -> bytes:
    payload = copy.deepcopy(document)
    payload.pop("h1_shared_resource_branch_program_id", None)
    payload["h1_shared_resource_branch_program_id"] = content_id(
        catalogues_v1.BRANCH_PROGRAM_DOMAIN, payload
    )
    return canonical_json_bytes(payload)


def _cap_owner_exercise():
    caps = {path: 1_000 for path in cap_owner_v2.SHARED_RESOURCE_PATHS}
    caps["process.launches"] = 2
    caps["memory.working_bytes_peak"] = 400
    caps["io.output_bytes"] = 120
    caps["io.mounted_bytes_peak"] = 100
    profile = cap_owner_v2.freeze_h1_shared_cap_profile_v2(
        predecision_context_id=hashlib.sha256(b"catalogue-context").hexdigest(),
        current_access_authority_id=hashlib.sha256(b"catalogue-access").hexdigest(),
        route_attempt_id=hashlib.sha256(b"catalogue-attempt").hexdigest(),
        execution_topology_profile_id=hashlib.sha256(b"catalogue-topology").hexdigest(),
        source_archive_id=hashlib.sha256(b"catalogue-source").hexdigest(),
        hard_caps=caps,
        max_control_cap_checks=100,
        outer_hierarchy_cap=350,
        broker_parent_cap=100,
        worker_role_cap=120,
        business_role_cap=150,
        retained_memory_peak_ofd_plan_id=hashlib.sha256(
            b"catalogue-memory-ofd"
        ).hexdigest(),
    )
    manifest = cap_owner_v2.freeze_h1_shared_cap_source_manifest_v2(
        source_archive_id=profile.source_archive_id,
        execution_topology_profile_id=profile.execution_topology_profile_id,
    )
    return cap_owner_v2.prepare_h1_shared_cap_owner_construction_exercise_v2(
        profile=profile,
        source_manifest=manifest,
    )


def test_registered_candidate_binds_all_preregistered_output_dag_leaves() -> None:
    dag = output_v1.registered_h1_production_output_branch_dag_candidate_v1()
    program = _program()
    assert len(dag.contexts) == catalogues_v1.EXPECTED_CONTEXT_COUNT == 10
    assert len(dag.leaves) == catalogues_v1.EXPECTED_BRANCH_COUNT == 90
    assert program.output_branch_dag_id == dag.dag_id
    assert tuple(row.branch_key for row in program.branches) == tuple(
        leaf.branch_key for leaf in dag.leaves
    )
    assert catalogues_v1.NUMERIC_SHARED_OPERAND_ISSUED is False
    assert catalogues_v1.PREDECISION_STRUCTURAL_AUTHORITY is False
    assert (
        catalogues_v1.PREDECISION_STRUCTURAL_CATALOGUE_CANDIDATE_PRESENT is True
    )
    assert catalogues_v1.PRODUCTION_BRANCH_PROGRAM_AUTHORITY_PRESENT is False
    assert catalogues_v1.ROUTE_EXECUTION_AUTHORIZED is False
    assert catalogues_v1.OFFICIAL_EXECUTION_ALLOWED is False
    assert program.to_document()["schema"] == (
        "acfqp.h1_shared_resource_branch_program.v1"
    )


def test_every_template_branch_has_total_candidate_site_partitions_only() -> None:
    program = _program()
    common = catalogues_v1.registered_h1_shared_common_catalogue_candidate_v1()
    io = catalogues_v1.registered_h1_shared_io_catalogue_candidate_v1()
    mount = catalogues_v1.registered_h1_physical_mount_catalogue_candidate_v1()
    launch = catalogues_v1.registered_h1_launch_catalogue_candidate_v1()
    universe = {
        **{
            path: tuple(row.site_key for row in common.sites if row.path == path)
            for path in catalogues_v1.COMMON_PATHS
        },
        catalogues_v1.READ_PATH: tuple(row.site_key for row in io.read_sites),
        catalogues_v1.STAGE_PATH: tuple(row.site_key for row in io.stage_sites),
        catalogues_v1.MOUNT_PATH: tuple(row.target_key for row in mount.payloads),
        catalogues_v1.LAUNCH_PATH: tuple(row.site_key for row in launch.launch_sites),
    }
    for branch in program.branches:
        assert tuple(row.path for row in branch.site_partitions) == catalogues_v1.STRUCTURAL_PATHS
        for partition in branch.site_partitions:
            assert not (
                set(partition.reachable_site_prefix)
                & set(partition.typed_unreachable_site_keys)
            )
            assert set(partition.reachable_site_prefix) | set(
                partition.typed_unreachable_site_keys
            ) == set(universe[partition.path])
            assert len(partition.reachable_site_prefix) + len(
                partition.typed_unreachable_site_keys
            ) == len(universe[partition.path])
            assert partition.to_document()["production_reachability_authority_present"] is False
    document = program.to_document()
    assert document["registered_template_partition_totality_present"] is True
    assert document["production_resource_prefix_complete"] is False
    assert document["production_branch_program_authority_present"] is False


def test_copy_same_content_never_deduplicates_different_targets_or_ordinals() -> None:
    digest = hashlib.sha256(b"same bytes in two distinct memfds").hexdigest()
    first = catalogues_v1.derive_copy_structural_target_slot_id_v1(
        source_content_sha256=digest,
        target_role="WORKER",
        target_key="fd:10",
        copy_ordinal=1,
    )
    second = catalogues_v1.derive_copy_structural_target_slot_id_v1(
        source_content_sha256=digest,
        target_role="BUSINESS",
        target_key="fd:10",
        copy_ordinal=1,
    )
    repeated_target = catalogues_v1.derive_copy_structural_target_slot_id_v1(
        source_content_sha256=digest,
        target_role="WORKER",
        target_key="fd:10",
        copy_ordinal=2,
    )
    assert len({first, second, repeated_target}) == 3
    registered_copy_slots = [
        row
        for row in catalogues_v1.registered_h1_physical_mount_catalogue_candidate_v1().payloads
        if row.origin is catalogues_v1.H1PhysicalOriginV1.COPY_TARGET
    ]
    assert len({row.candidate_instance_slot_id for row in registered_copy_slots}) == len(
        registered_copy_slots
    )
    assert all(
        row.to_document()["physical_identity_semantics"]
        == "STRUCTURAL_COPY_TARGET_SLOT_ONLY"
        for row in registered_copy_slots
    )
    assert all(
        row.to_document()["native_physical_instance_authority_present"] is False
        for row in registered_copy_slots
    )
    assert all(
        "physical_instance_id" not in row.to_document()
        for row in registered_copy_slots
    )
    with pytest.raises(
        catalogues_v1.ConstructionK7H1SharedResourceCataloguesV1Error,
        match="deprecated COPY physical-instance",
    ):
        catalogues_v1.derive_copy_physical_instance_id_v1(
            source_content_sha256=digest,
            target_role="WORKER",
            target_key="fd:10",
            copy_ordinal=1,
        )
    with pytest.raises(
        catalogues_v1.ConstructionK7H1SharedResourceCataloguesV1Error,
        match="deprecated payload physical_instance_id",
    ):
        _ = registered_copy_slots[0].physical_instance_id


def test_bind_targets_remain_distinct_while_inode_ofd_evidence_is_unbound() -> None:
    mount = catalogues_v1.registered_h1_physical_mount_catalogue_candidate_v1()
    assert len(mount.aliases) == 1
    alias = mount.aliases[0]
    unresolved = [
        row
        for row in mount.payloads
        if row.origin is catalogues_v1.H1PhysicalOriginV1.BIND_UNRESOLVED_TARGET
    ]
    assert len(unresolved) == 2
    assert len({row.candidate_instance_slot_id for row in unresolved}) == 2
    assert alias.candidate_shared_instance_slot_id not in {
        row.candidate_instance_slot_id for row in unresolved
    }
    with pytest.raises(
        catalogues_v1.ConstructionK7H1SharedResourceCataloguesV1Error,
        match="deprecated BIND physical_instance_id",
    ):
        _ = alias.physical_instance_id
    with pytest.raises(
        catalogues_v1.ConstructionK7H1SharedResourceCataloguesV1Error,
        match="deprecated alias_authority_id",
    ):
        _ = alias.alias_authority_id
    assert {row.target_key for row in unresolved} == set(alias.target_keys)
    assert alias.runtime_evidence_blocker.evidence_id is None
    for row in unresolved:
        assert row.candidate_instance_slot_id == (
            catalogues_v1.derive_unresolved_bind_target_slot_id_v1(
                source_slot_id=row.source_slot_id,
                target_role=row.target_role,
                target_key=row.target_key,
            )
        )
        assert row.to_document()["typed_inode_ofd_alias_candidate_id"] == (
            alias.alias_candidate_id
        )
        assert "typed_inode_ofd_alias_authority" not in row.to_document()
        with pytest.raises(
            catalogues_v1.ConstructionK7H1SharedResourceCataloguesV1Error,
            match="deprecated payload alias_authority_id",
        ):
            _ = row.alias_authority_id
        with pytest.raises(
            catalogues_v1.ConstructionK7H1SharedResourceCataloguesV1Error,
            match="REQUIRED_UNBOUND",
        ):
            catalogues_v1.derive_bind_physical_instance_id_v1(
                alias_authority=alias, target_key=row.target_key
            )
    with pytest.raises(
        catalogues_v1.ConstructionK7H1SharedResourceCataloguesV1Error
    ):
        catalogues_v1.derive_bind_physical_instance_id_v1(
            alias_authority={"same_content": True},  # type: ignore[arg-type]
            target_key=unresolved[0].target_key,
        )


def test_mount_sweep_counts_overlapping_candidate_slots_once() -> None:
    physical = hashlib.sha256(b"physical-a").hexdigest()
    other = hashlib.sha256(b"physical-b").hexdigest()
    intervals = (
        catalogues_v1.H1BranchMountIntervalV1(
            "a", "target-a", physical, 1, 5, "extent-a"
        ),
        catalogues_v1.H1BranchMountIntervalV1(
            "b", "target-b", physical, 2, 6, "extent-a"
        ),
        catalogues_v1.H1BranchMountIntervalV1(
            "c", "target-c", other, 3, 7, "extent-b"
        ),
    )
    sweep = catalogues_v1.sweep_physical_mount_intervals_v1(intervals)
    by_sequence = {
        row.sequence: row.active_candidate_instance_slot_ids for row in sweep
    }
    assert by_sequence[3] == tuple(sorted((physical, other)))
    assert physical in by_sequence[5]
    assert physical not in by_sequence[6]
    assert by_sequence[7] == ()


def test_memory_scope_continuously_includes_broker_worker_business() -> None:
    memory = catalogues_v1.registered_h1_memory_scope_candidate_v1()
    assert type(memory) is catalogues_v1.H1MemoryScopeCandidateV1
    assert catalogues_v1.MEMORY_CANDIDATE_DOMAIN in (
        catalogues_v1.REQUESTED_PHASE3E_DOMAIN_TAGS
    )
    assert memory.members == ("BROKER", "WORKER", "BUSINESS")
    assert (
        memory.outer_pid_membership_minimum
        == catalogues_v1.EXPECTED_OUTER_PID_MEMBERSHIP_MINIMUM
        == 3
    )
    assert memory.same_ofd_peak_plan.owner_role == "BROKER"
    assert memory.same_ofd_peak_plan.open_before_scope_members_join is True
    assert memory.same_ofd_peak_plan.read_after_all_descendants_reaped is True
    assert all(
        row.numeric_value is None for row in memory.preexecution_numeric_blockers
    )
    assert tuple(row.blocker_key for row in memory.preexecution_numeric_blockers)[-1] == (
        "outer-pids-max"
    )
    assert tuple(row.blocker_key for row in memory.preexecution_evidence_blockers) == (
        "outer-cgroup-pid-membership",
    )
    assert tuple(row.blocker_key for row in memory.postrun_actual_blockers) == (
        "retained-outer-peak-readback",
    )
    document = memory.to_document()
    assert document["schema"] == "acfqp.h1_memory_scope_candidate.v1"
    assert document["h1_memory_scope_candidate_id"] == memory.candidate_id
    assert "h1_memory_scope_authority_id" not in document
    assert document["outer_pid_membership_authority_present"] is False
    assert document["numeric_caps_authoritative"] is False
    assert document["postrun_peak_receipt_authoritative"] is False
    assert document["postrun_actual_may_authorize_preexecution_upper"] is False
    assert document["missing_numeric_value_is_zero"] is False
    assert document["memory_scope_plan_only"] is True
    memory_payload = copy.deepcopy(document)
    memory_payload.pop("h1_memory_scope_candidate_id")
    assert memory.candidate_id == content_id(
        catalogues_v1.MEMORY_CANDIDATE_DOMAIN, memory_payload
    )
    assert memory.candidate_id != content_id(
        phase3e_ids.CONSTRUCTION_K7_H1_MEMORY_SCOPE_AUTHORITY_V1_DOMAIN,
        memory_payload,
    )
    assert document["broker_parent_inside_outer_scope_required_by_candidate"] is True
    assert (
        document[
            "worker_business_join_before_native_launch_required_by_candidate"
        ]
        is True
    )
    assert (
        document[
            "descendants_retained_until_trusted_reap_or_cleanup_required_by_candidate"
        ]
        is True
    )
    for factual_key in (
        "broker_parent_is_inside_outer_scope",
        "worker_and_business_join_before_native_launch",
        "descendants_remain_until_trusted_reap_or_cleanup",
        "broker_remains_through_peak_read_and_accounting_close",
    ):
        assert factual_key not in document
    with pytest.raises(
        catalogues_v1.ConstructionK7H1SharedResourceCataloguesV1Error,
        match="deprecated memory authority_id",
    ):
        _ = memory.authority_id


def test_launch_catalogue_registers_order_but_exposes_missing_business_ambiguity() -> None:
    launch = catalogues_v1.registered_h1_launch_catalogue_candidate_v1()
    assert type(launch) is catalogues_v1.H1LaunchCatalogueCandidateV1
    assert catalogues_v1.LAUNCH_CANDIDATE_DOMAIN in (
        catalogues_v1.REQUESTED_PHASE3E_DOMAIN_TAGS
    )
    assert tuple(row.role for row in launch.launch_sites) == (
        "WORKER",
        "BUSINESS",
    )
    assert tuple(row.ordinal for row in launch.launch_sites) == (1, 2)
    document = launch.to_document()
    assert document["schema"] == "acfqp.h1_launch_catalogue_candidate.v1"
    assert document["h1_launch_catalogue_candidate_id"] == launch.candidate_id
    assert "h1_launch_authority_id" not in document
    assert document["registered_child_launch_count_upper"] == 2
    assert document["broker_is_parent_and_not_a_child_launch"] is True
    assert document["production_launch_prefix_authority_present"] is False
    assert document["production_ambiguity_context_coverage_complete"] is False
    assert document["missing_production_contexts"] == [
        "BUSINESS_LAUNCH_EXISTENCE_AMBIGUOUS"
    ]
    launch_payload = copy.deepcopy(document)
    launch_payload.pop("h1_launch_catalogue_candidate_id")
    assert launch.candidate_id == content_id(
        catalogues_v1.LAUNCH_CANDIDATE_DOMAIN, launch_payload
    )
    assert launch.candidate_id != content_id(
        phase3e_ids.CONSTRUCTION_K7_H1_LAUNCH_AUTHORITY_V1_DOMAIN,
        launch_payload,
    )
    with pytest.raises(
        catalogues_v1.ConstructionK7H1SharedResourceCataloguesV1Error,
        match="deprecated launch authority_id",
    ):
        _ = launch.authority_id


def test_template_prefixes_are_not_promoted_over_missing_admission_failures() -> None:
    program = _program()
    pre = next(
        row
        for row in program.branches
        if row.context_kind == "SHARED_CAP_EXHAUSTED_PRE_BUSINESS"
        and row.output_role_prefix == ()
    )
    final = next(
        row
        for row in program.branches
        if row.context_kind == "EXACT_INFEASIBLE"
        and row.finalization_status == "FINALIZED"
    )
    pre_by_path = {row.path: row for row in pre.site_partitions}
    final_by_path = {row.path: row for row in final.site_partitions}
    assert pre_by_path[catalogues_v1.STAGE_PATH].reachable_site_prefix == ()
    assert pre_by_path[catalogues_v1.MOUNT_PATH].reachable_site_prefix == ()
    assert pre_by_path[catalogues_v1.LAUNCH_PATH].reachable_site_prefix == ()
    assert len(final_by_path[catalogues_v1.STAGE_PATH].reachable_site_prefix) == 10
    assert len(final_by_path[catalogues_v1.LAUNCH_PATH].reachable_site_prefix) == 2
    assert final.output_admission_upper_candidate == 1
    assert final.memory_admission_upper_candidate == 1
    pre_document = pre.to_document()
    final_document = final.to_document()
    assert pre_document["production_resource_prefix_complete"] is False
    assert final_document["production_resource_prefix_complete"] is False
    assert final_document["output_admission_candidate"] == {
        "lower": 0,
        "upper": 1,
        "status": "PRODUCTION_BRANCH_SOURCE_REQUIRED_UNBOUND",
    }


def test_output_and_read_extents_remain_typed_unbound() -> None:
    io = catalogues_v1.registered_h1_shared_io_catalogue_candidate_v1()
    output_reads = [
        row
        for row in io.read_sites
        if row.kind is catalogues_v1.H1IOSiteKindV1.OUTPUT_ROLE_READBACK
    ]
    assert len(output_reads) == catalogues_v1.EXPECTED_OUTPUT_ROLE_COUNT
    assert all(row.extent_blocker.numeric_value is None for row in output_reads)
    document = _program().to_document()
    assert document["numeric_shared_operand_issued"] is False
    assert document["catalogues"]["io"]["numeric_extent_authority_present"] is False


def test_exact_canonical_replay_accepts_registered_candidate_only() -> None:
    program = _program()
    assert (
        catalogues_v1.verify_h1_shared_resource_branch_program_candidate_bytes_v1(
            program.canonical_bytes
        )
        is program
    )


def test_broker_omission_attack_fails_even_if_nested_and_outer_ids_are_resigned() -> None:
    document = copy.deepcopy(_program().to_document())
    memory = document["catalogues"]["memory"]
    memory["continuous_scope_members"].remove("BROKER")
    memory.pop("h1_memory_scope_candidate_id")
    memory["h1_memory_scope_candidate_id"] = content_id(
        catalogues_v1.MEMORY_CANDIDATE_DOMAIN, memory
    )
    attacked = _resign_program(document)
    with pytest.raises(
        catalogues_v1.ConstructionK7H1SharedResourceCataloguesV1Error
    ):
        catalogues_v1.verify_h1_shared_resource_branch_program_candidate_bytes_v1(attacked)


@pytest.mark.parametrize(
    "field",
    (
        "decision_point_id",
        "RouteDecisionContext_id",
        "route_decision_context_id",
        "route_upper_bound_envelope_id",
        "formal_v7_route_upper_id",
        "formal_v7_route_decision_id",
    ),
)
def test_future_field_injection_attack_fails_even_if_resigned(field: str) -> None:
    document = copy.deepcopy(_program().to_document())
    document[field] = hashlib.sha256(field.encode("utf-8")).hexdigest()
    attacked = _resign_program(document)
    with pytest.raises(
        catalogues_v1.ConstructionK7H1SharedResourceCataloguesV1Error,
        match="future authority field",
    ):
        catalogues_v1.verify_h1_shared_resource_branch_program_candidate_bytes_v1(attacked)


def test_candidate_output_mount_schedule_is_rejected_by_cap_owner_lifecycle() -> None:
    branch = next(
        row
        for row in _program().branches
        if row.context_kind == "EXACT_INFEASIBLE"
        and row.finalization_status == "FINALIZED"
    )
    owner = _cap_owner_exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    owner.begin_route_output()
    owner.launch_registered_role("WORKER", lambda: None)
    output_payload = next(
        row
        for row in catalogues_v1.registered_h1_physical_mount_catalogue_candidate_v1().payloads
        if row.origin is catalogues_v1.H1PhysicalOriginV1.CREATED_OUTPUT
    )
    output_interval = next(
        row for row in branch.mount_intervals if row.target_key == output_payload.target_key
    )
    assert output_interval.open_sequence >= 450
    assert output_interval.to_document()["shared_cap_owner_lifecycle_compatible"] is False
    with pytest.raises(
        cap_owner_v2.H1SharedCapProtocolFailureV2,
        match="before first child visibility",
    ):
        owner.open_mounted_payload(
            output_payload.candidate_instance_slot_id, 1, lambda: None
        )


def test_candidate_early_mount_close_is_rejected_by_cap_owner_lifecycle() -> None:
    branch = next(
        row
        for row in _program().branches
        if row.context_kind == "EXACT_INFEASIBLE"
        and row.finalization_status == "FINALIZED"
    )
    owner = _cap_owner_exercise()
    owner.bind_working_hierarchy(lambda _binding: None)
    owner.begin_route_output()
    input_payload = next(
        row
        for row in catalogues_v1.registered_h1_physical_mount_catalogue_candidate_v1().payloads
        if row.origin
        in {
            catalogues_v1.H1PhysicalOriginV1.COPY_TARGET,
            catalogues_v1.H1PhysicalOriginV1.BIND_UNRESOLVED_TARGET,
        }
    )
    input_interval = next(
        row for row in branch.mount_intervals if row.target_key == input_payload.target_key
    )
    assert input_interval.close_sequence in {100, 400}
    assert input_interval.to_document()["shared_cap_owner_lifecycle_compatible"] is False
    token = owner.open_mounted_payload(
        input_payload.candidate_instance_slot_id, 1, lambda: None
    )
    with pytest.raises(
        cap_owner_v2.H1SharedCapProtocolFailureV2,
        match="descendant reap",
    ):
        owner.close_mounted_payload(token, lambda: None)


def test_branch_omission_attack_fails_even_if_resigned() -> None:
    document = copy.deepcopy(_program().to_document())
    document["branches"].pop()
    document["branch_count"] = len(document["branches"])
    attacked = _resign_program(document)
    with pytest.raises(
        catalogues_v1.ConstructionK7H1SharedResourceCataloguesV1Error
    ):
        catalogues_v1.verify_h1_shared_resource_branch_program_candidate_bytes_v1(attacked)


def test_wildcard_or_missing_as_zero_attack_fails() -> None:
    for key in ("wildcard_allowed", "missing_as_zero_allowed"):
        document = copy.deepcopy(_program().to_document())
        document[key] = True
        attacked = _resign_program(document)
        with pytest.raises(
            catalogues_v1.ConstructionK7H1SharedResourceCataloguesV1Error
        ):
            catalogues_v1.verify_h1_shared_resource_branch_program_candidate_bytes_v1(attacked)


def test_callers_cannot_mint_catalogue_or_program() -> None:
    common = catalogues_v1.registered_h1_shared_common_catalogue_candidate_v1()
    with pytest.raises(
        catalogues_v1.ConstructionK7H1SharedResourceCataloguesV1Error
    ):
        catalogues_v1.H1SharedCommonCatalogueV1(
            object(), common.output_branch_dag_id, common.sites
        )
    alias = catalogues_v1.registered_h1_physical_mount_catalogue_candidate_v1().aliases[0]
    with pytest.raises(
        catalogues_v1.ConstructionK7H1SharedResourceCataloguesV1Error
    ):
        catalogues_v1.H1TypedInodeOFDAliasAuthorityV1(
            object(),
            alias.alias_key,
            alias.source_slot_id,
            alias.inode_identity_slot_id,
            alias.open_file_description_slot_id,
            alias.target_keys,
            alias.runtime_evidence_blocker,
        )


@pytest.mark.parametrize(
    "legacy_api,args",
    (
        ("official_h1_shared_common_catalogue_v1", ()),
        ("official_h1_shared_io_catalogue_v1", ()),
        ("official_h1_physical_mount_catalogue_v1", ()),
        ("official_h1_memory_scope_authority_v1", ()),
        ("official_h1_launch_authority_v1", ()),
        ("official_h1_shared_resource_branch_program_v1", ()),
        (
            "verify_h1_shared_resource_branch_program_bytes_v1",
            (_program().canonical_bytes,),
        ),
    ),
)
def test_deprecated_official_or_authority_apis_fail_closed(
    legacy_api: str, args: tuple[object, ...]
) -> None:
    with pytest.raises(
        catalogues_v1.ConstructionK7H1SharedResourceCataloguesV1Error,
        match="deprecated authority API",
    ):
        getattr(catalogues_v1, legacy_api)(*args)

    assert catalogues_v1.OFFICIAL_EXECUTION_ALLOWED is False
    assert catalogues_v1.OFFICIAL_SCALAR_COST is None
    assert catalogues_v1.OFFICIAL_N_BREAK_EVEN is None


@pytest.mark.parametrize(
    "legacy_constructor",
    (
        catalogues_v1.H1MemoryScopeAuthorityV1,
        catalogues_v1.H1LaunchAuthorityV1,
    ),
)
def test_deprecated_authority_constructors_fail_closed(legacy_constructor) -> None:
    with pytest.raises(
        catalogues_v1.ConstructionK7H1SharedResourceCataloguesV1Error,
        match="deprecated authority API",
    ):
        legacy_constructor()
