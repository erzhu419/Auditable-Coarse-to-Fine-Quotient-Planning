from __future__ import annotations

import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_h1_production_lifecycle_source_candidate_v1 as lifecycle_v1
from acfqp import phase3e_ids
from acfqp.phase3e_ids import canonical_json_bytes, content_id


def _candidate() -> lifecycle_v1.H1ProductionLifecycleSourceCandidateV1:
    return lifecycle_v1.registered_h1_production_lifecycle_source_candidate_v1()


def _resign_candidate(document: dict) -> bytes:
    payload = copy.deepcopy(document)
    payload.pop("h1_production_lifecycle_source_candidate_id", None)
    payload["h1_production_lifecycle_source_candidate_id"] = content_id(
        lifecycle_v1.SOURCE_CANDIDATE_DOMAIN, payload
    )
    return canonical_json_bytes(payload)


def test_exact_source_bytes_ast_and_required_function_spans_are_bound() -> None:
    candidate = _candidate()
    manifest = candidate.source_manifest.to_document()
    assert manifest["complete_module_bytes_bound"] is True
    assert manifest["normalized_ast_bound"] is True
    assert manifest["exact_function_source_spans_bound"] is True
    assert tuple(row["symbol"] for row in manifest["source_spans"]) == (
        lifecycle_v1.SOURCE_BOUND_SYMBOLS
    )
    assert all(row["start_line"] <= row["end_line"] for row in manifest["source_spans"])
    assert all(row["source_byte_count"] > 0 for row in manifest["source_spans"])
    module_bytes = Path(lifecycle_v1.__file__).read_bytes()
    assert (
        lifecycle_v1.derive_h1_production_lifecycle_source_manifest_id_v1(module_bytes)
        == candidate.source_manifest.manifest_id
    )
    changed = module_bytes + b"\n# source-byte identity attack\n"
    assert (
        lifecycle_v1.derive_h1_production_lifecycle_source_manifest_id_v1(changed)
        != candidate.source_manifest.manifest_id
    )


def test_one_table_covers_nine_paths_and_orders_only_the_candidate_lifecycle() -> None:
    program = _candidate().program
    transitions = program.transitions
    assert {row.resource_path for row in transitions if row.resource_path} == set(
        lifecycle_v1.SHARED_RESOURCE_PATHS
    )
    assert transitions[0].operation is lifecycle_v1.H1LifecycleOperationV1.MEMORY_BIND
    output_reserve = next(
        row.ordinal
        for row in transitions
        if row.operation is lifecycle_v1.H1LifecycleOperationV1.OUTPUT_RESERVE
    )
    launch_ordinals = [
        row.ordinal
        for row in transitions
        if row.operation is lifecycle_v1.H1LifecycleOperationV1.LAUNCH_CHILD
    ]
    mount_open_ordinals = [
        row.ordinal
        for row in transitions
        if row.operation is lifecycle_v1.H1LifecycleOperationV1.MOUNT_OPEN
    ]
    reap = next(
        row.ordinal
        for row in transitions
        if row.operation is lifecycle_v1.H1LifecycleOperationV1.DESCENDANT_REAP
    )
    peak = next(
        row.ordinal
        for row in transitions
        if row.operation is lifecycle_v1.H1LifecycleOperationV1.SAME_OFD_PEAK_READ
    )
    mount_close_ordinals = [
        row.ordinal
        for row in transitions
        if row.operation is lifecycle_v1.H1LifecycleOperationV1.MOUNT_CLOSE
    ]
    finalize = next(
        row.ordinal
        for row in transitions
        if row.operation is lifecycle_v1.H1LifecycleOperationV1.OUTPUT_FINALIZE
    )
    assert output_reserve < launch_ordinals[0]
    assert max(mount_open_ordinals) < launch_ordinals[0]
    assert [program.transitions[index - 1].ambiguity_role for index in launch_ordinals] == [
        "WORKER",
        "BUSINESS",
    ]
    assert reap < peak < min(mount_close_ordinals)
    assert max(mount_close_ordinals) < finalize
    assert transitions[-1].operation is lifecycle_v1.H1LifecycleOperationV1.OUTPUT_CLOSE


def test_every_declared_failure_edge_has_one_exact_first_failure_prefix() -> None:
    candidate = _candidate()
    program = candidate.program
    analysis = candidate.branch_analysis
    assert len(analysis.branches) == 1 + sum(
        len(row.failure_edges) for row in program.transitions
    )
    by_key = analysis.by_key
    for index, transition in enumerate(program.transitions):
        prior = tuple(row.site_key for row in program.transitions[:index])
        for edge in transition.failure_edges:
            branch = by_key[f"FAIL:{transition.site_key}:{edge.outcome.value}"]
            edge_document = edge.to_document()
            branch_document = branch.to_document()
            assert branch.successful_site_prefix == prior
            assert branch.attempted_site_prefix == (*prior, transition.site_key)
            assert branch.failed_edge == edge
            assert edge_document["attempt_closure_issued"] is False
            assert edge_document["terminal_classification_issued"] is False
            assert branch_document["attempt_closure_issued"] is False
            assert branch_document["terminal_classification_issued"] is False
            assert "terminal_class" not in edge_document
            assert "terminal_code" not in edge_document
            assert "terminal_class" not in branch_document
            assert "terminal_code" not in branch_document
            for resource in branch.resource_prefixes:
                universe = tuple(
                    row.site_key
                    for row in program.transitions
                    if row.resource_path == resource.path
                )
                assert set(resource.attempted_site_prefix) | set(
                    resource.unreached_site_keys
                ) == set(universe)
                assert not set(resource.attempted_site_prefix) & set(
                    resource.unreached_site_keys
                )


def test_worker_and_business_native_launch_ambiguity_are_both_explicit() -> None:
    analysis = _candidate().branch_analysis.by_key
    for role in ("WORKER", "BUSINESS"):
        key = (
            f"FAIL:launch:{role}:"
            "NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION"
        )
        branch = analysis[key]
        assert branch.failed_edge is not None
        assert branch.failed_edge.current_site_admitted is True
        assert branch.failed_edge.native_existence is lifecycle_v1.H1NativeExistenceV1.AMBIGUOUS
        prefix = next(
            row
            for row in branch.resource_prefixes
            if row.path == "process.launches"
        )
        assert f"launch:{role}" in prefix.admitted_site_prefix


def test_every_stage_read_and_mount_admission_has_exact_cap_failure_prefix() -> None:
    candidate = _candidate()
    for transition in candidate.program.transitions:
        if transition.operation not in {
            lifecycle_v1.H1LifecycleOperationV1.STAGE_INPUT,
            lifecycle_v1.H1LifecycleOperationV1.READ_INPUT,
            lifecycle_v1.H1LifecycleOperationV1.READ_BUSINESS_RESULT,
            lifecycle_v1.H1LifecycleOperationV1.OUTPUT_ROLE_READBACK,
            lifecycle_v1.H1LifecycleOperationV1.MOUNT_OPEN,
        }:
            continue
        assert transition.reservation_edge is True
        edge = next(
            edge
            for edge in transition.failure_edges
            if edge.outcome
            is lifecycle_v1.H1LifecycleOutcomeV1.CAP_REJECTED_BEFORE_SIDE_EFFECT
        )
        branch = candidate.branch_analysis.by_key[
            f"FAIL:{transition.site_key}:{edge.outcome.value}"
        ]
        prefix = next(
            row
            for row in branch.resource_prefixes
            if row.path == transition.resource_path
        )
        assert transition.site_key in prefix.attempted_site_prefix
        assert transition.site_key not in prefix.admitted_site_prefix
        assert transition.site_key not in prefix.completed_site_prefix


def test_complete_success_and_failure_replay_use_the_declared_table() -> None:
    program = _candidate().program
    success_events = tuple(
        lifecycle_v1.H1LifecycleEventV1(
            row.site_key, lifecycle_v1.H1LifecycleOutcomeV1.SUCCESS
        )
        for row in program.transitions
    )
    replay = lifecycle_v1.replay_h1_production_lifecycle_events_v1(success_events)
    assert replay.full_success_reached is True
    assert replay.first_failure_outcome is None
    assert replay.next_site_key is None
    assert replay.successful_site_prefix == tuple(row.site_key for row in program.transitions)

    business = program.by_site["launch:BUSINESS"]
    prefix = program.transitions[: business.ordinal - 1]
    failure_events = tuple(
        lifecycle_v1.H1LifecycleEventV1(
            row.site_key, lifecycle_v1.H1LifecycleOutcomeV1.SUCCESS
        )
        for row in prefix
    ) + (
        lifecycle_v1.H1LifecycleEventV1(
            business.site_key,
            lifecycle_v1.H1LifecycleOutcomeV1.NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION,
        ),
    )
    failed = lifecycle_v1.replay_h1_production_lifecycle_events_v1(failure_events)
    assert failed.full_success_reached is False
    assert failed.first_failure_outcome is (
        lifecycle_v1.H1LifecycleOutcomeV1.NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION
    )
    assert failed.next_site_key is None
    failed_document = failed.to_document()
    assert failed_document["attempt_closure_issued"] is False
    assert failed_document["terminal_classification_issued"] is False
    assert "terminal_class" not in failed_document
    assert "terminal_code" not in failed_document


def test_linear_output_reads_do_not_claim_the_output_dag_leaf_join() -> None:
    document = _candidate().program.to_document()
    role_sets = tuple(
        tuple(row) for row in document["output_dag_role_presence_sets"]
    )
    linear_roles = tuple(document["linear_output_readback_roles"])
    assert len(role_sets) > 1
    assert linear_roles in role_sets
    assert any(row != linear_roles for row in role_sets)
    assert document["linear_all_roles_matches_every_output_dag_leaf"] is False
    assert document["output_dag_leaf_join_bound"] is False
    assert document["output_read_lifecycle_complete"] is False


def test_replay_rejects_skips_invalid_edges_and_post_first_failure_events() -> None:
    program = _candidate().program
    with pytest.raises(
        lifecycle_v1.ConstructionK7H1ProductionLifecycleSourceCandidateV1Error,
        match="skipped",
    ):
        lifecycle_v1.replay_h1_production_lifecycle_events_v1(
            (
                lifecycle_v1.H1LifecycleEventV1(
                    program.transitions[1].site_key,
                    lifecycle_v1.H1LifecycleOutcomeV1.SUCCESS,
                ),
            )
        )
    with pytest.raises(
        lifecycle_v1.ConstructionK7H1ProductionLifecycleSourceCandidateV1Error,
        match="absent",
    ):
        lifecycle_v1.replay_h1_production_lifecycle_events_v1(
            (
                lifecycle_v1.H1LifecycleEventV1(
                    program.transitions[0].site_key,
                    lifecycle_v1.H1LifecycleOutcomeV1.CLEANUP_FAILED,
                ),
            )
        )
    with pytest.raises(
        lifecycle_v1.ConstructionK7H1ProductionLifecycleSourceCandidateV1Error,
        match="after a first failure",
    ):
        lifecycle_v1.replay_h1_production_lifecycle_events_v1(
            (
                lifecycle_v1.H1LifecycleEventV1(
                    program.transitions[0].site_key,
                    lifecycle_v1.H1LifecycleOutcomeV1.CAP_REJECTED_BEFORE_SIDE_EFFECT,
                ),
                lifecycle_v1.H1LifecycleEventV1(
                    program.transitions[1].site_key,
                    lifecycle_v1.H1LifecycleOutcomeV1.SUCCESS,
                ),
            )
        )


def test_canonical_replay_and_resigned_site_or_branch_omission_attacks_fail() -> None:
    candidate = _candidate()
    assert (
        lifecycle_v1.verify_h1_production_lifecycle_source_candidate_bytes_v1(
            candidate.canonical_bytes
        )
        is candidate
    )
    site_attack = copy.deepcopy(candidate.to_document())
    site_attack["h1_production_lifecycle_program"]["transitions"].pop()
    site_attack["h1_production_lifecycle_program"]["transition_count"] -= 1
    with pytest.raises(
        lifecycle_v1.ConstructionK7H1ProductionLifecycleSourceCandidateV1Error,
        match="differs",
    ):
        lifecycle_v1.verify_h1_production_lifecycle_source_candidate_bytes_v1(
            _resign_candidate(site_attack)
        )

    branch_attack = copy.deepcopy(candidate.to_document())
    branch_attack["h1_production_lifecycle_branch_analysis"]["branches"].pop()
    branch_attack["h1_production_lifecycle_branch_analysis"]["branch_count"] -= 1
    with pytest.raises(
        lifecycle_v1.ConstructionK7H1ProductionLifecycleSourceCandidateV1Error,
        match="differs",
    ):
        lifecycle_v1.verify_h1_production_lifecycle_source_candidate_bytes_v1(
            _resign_candidate(branch_attack)
        )


def test_source_manifest_identity_and_future_identity_injection_attacks_fail() -> None:
    candidate = _candidate()
    source_attack = copy.deepcopy(candidate.to_document())
    source_attack["h1_production_lifecycle_source_manifest"]["whole_source_sha256"] = (
        "0" * 64
    )
    with pytest.raises(
        lifecycle_v1.ConstructionK7H1ProductionLifecycleSourceCandidateV1Error,
        match="differs",
    ):
        lifecycle_v1.verify_h1_production_lifecycle_source_candidate_bytes_v1(
            _resign_candidate(source_attack)
        )

    identity_attack = copy.deepcopy(candidate.to_document())
    program = identity_attack["h1_production_lifecycle_program"]
    program["h1_execution_topology_profile_id"] = "e" * 64
    program.pop("h1_production_lifecycle_program_id")
    program["h1_production_lifecycle_program_id"] = content_id(
        lifecycle_v1.PROGRAM_DOMAIN, program
    )
    analysis = identity_attack["h1_production_lifecycle_branch_analysis"]
    analysis["h1_production_lifecycle_program_id"] = program[
        "h1_production_lifecycle_program_id"
    ]
    analysis.pop("h1_production_lifecycle_branch_analysis_id")
    analysis["h1_production_lifecycle_branch_analysis_id"] = content_id(
        lifecycle_v1.BRANCH_ANALYSIS_DOMAIN, analysis
    )
    with pytest.raises(
        lifecycle_v1.ConstructionK7H1ProductionLifecycleSourceCandidateV1Error,
        match="differs",
    ):
        lifecycle_v1.verify_h1_production_lifecycle_source_candidate_bytes_v1(
            _resign_candidate(identity_attack)
        )

    future_attack = copy.deepcopy(candidate.to_document())
    future_attack["h1_production_lifecycle_program"]["RouteDecisionContext_id"] = (
        "f" * 64
    )
    with pytest.raises(
        lifecycle_v1.ConstructionK7H1ProductionLifecycleSourceCandidateV1Error,
        match="future authority field",
    ):
        lifecycle_v1.verify_h1_production_lifecycle_source_candidate_bytes_v1(
            _resign_candidate(future_attack)
        )


def test_candidate_is_explicitly_not_source_execution_or_numeric_authority() -> None:
    candidate = _candidate()
    document = candidate.to_document()
    assert document["declarative_lifecycle_source_authority_present"] is False
    assert document["declarative_lifecycle_candidate_present"] is True
    assert document["first_failure_prefixes_complete_for_declared_candidate_edges"] is True
    assert document["production_failure_edge_completeness_claimed"] is False
    assert document["post_failure_cleanup_continuation_program_bound"] is False
    assert document["complete_attempt_branches_issued"] is False
    assert document["external_preregistration_anchor_present"] is False
    assert document["fresh_import_can_self_mint_new_candidate_identity"] is True
    assert document["common_multiplicity_source_bound"] is False
    assert document["shared_cap_owner_semantic_identity_bound"] is False
    assert document["owner_order_compatibility_claimed"] is False
    assert document["output_dag_leaf_join_bound"] is False
    assert document["output_read_lifecycle_complete"] is False
    assert document["attempt_closure_issued"] is False
    assert document["terminal_classification_issued"] is False
    assert document["live_runtime_integration_present"] is False
    assert document["production_execution_authority_present"] is False
    assert document["numeric_ceiling_declared"] is False
    assert document["numeric_shared_operand_issued"] is False
    assert document["formal_v7_route_authority_present"] is False
    assert document["counter_records_issued"] is False
    assert document["work_vector_issued"] is False
    assert document["comparison_vector_issued"] is False
    assert tuple(document["typed_production_blockers"]) == (
        lifecycle_v1.TYPED_PRODUCTION_BLOCKERS
    )
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    payload = copy.deepcopy(document)
    payload.pop("h1_production_lifecycle_source_candidate_id")
    assert candidate.candidate_id == content_id(
        lifecycle_v1.SOURCE_CANDIDATE_DOMAIN, payload
    )
    assert candidate.candidate_id != content_id(
        phase3e_ids.CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_SOURCE_AUTHORITY_V1_DOMAIN,
        payload,
    )
    assert "h1_production_lifecycle_source_authority_id" not in document
    with pytest.raises(ValueError, match="authority_id is unavailable"):
        _ = candidate.authority_id
    with pytest.raises(ValueError, match="source authority is unavailable"):
        lifecycle_v1.H1ProductionLifecycleSourceAuthorityV1()
    legacy_shell = object.__new__(lifecycle_v1.H1ProductionLifecycleSourceAuthorityV1)
    with pytest.raises(ValueError, match="authority_id is unavailable"):
        _ = legacy_shell.authority_id
    with pytest.raises(ValueError, match="source authority is unavailable"):
        lifecycle_v1.official_h1_production_lifecycle_source_authority_v1()
    with pytest.raises(ValueError, match="program authority is unavailable"):
        lifecycle_v1.official_h1_production_lifecycle_program_v1()
    with pytest.raises(ValueError, match="branch-analysis authority is unavailable"):
        lifecycle_v1.official_h1_production_lifecycle_branch_analysis_v1()
    with pytest.raises(ValueError, match="authority verification is unavailable"):
        lifecycle_v1.verify_h1_production_lifecycle_source_authority_bytes_v1(
            candidate.canonical_bytes
        )
