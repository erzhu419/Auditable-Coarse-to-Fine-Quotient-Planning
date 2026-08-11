from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_accounting_owned_runtime_v1 as hook_v1
from acfqp import construction_k7_query_bound_accounting_manifest_v1 as manifest_v1
from acfqp import construction_k7_query_bound_direct_ground_fallback_v1 as fallback_v1
from acfqp import construction_k7_query_bound_stage_accounting_v1 as subject
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:query-bound-stage-accounting-test:v1\x00" + label.encode()
    ).hexdigest()


def _complete_empty_prefix(session) -> None:
    for stage in subject.CANONICAL_QUERY_BOUND_STAGE_PLAN_V1[:4]:
        session.enter_stage(stage)
        session.exit_stage(stage)


def test_manifest_is_additive_and_binds_open_plus_direct_sources() -> None:
    assert manifest_v1.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    manifest = manifest_v1.official_query_bound_accounting_operation_manifest_v1()
    assert len(manifest.boundaries) == manifest_v1.EXPECTED_BOUNDARY_COUNT == 57
    assert sum(row.stage in manifest_v1.OPEN_STAGES for row in manifest.boundaries) == 46
    assert manifest_v1.EXPECTED_REUSED_OPEN_BOUNDARY_COUNT == 43
    assert manifest_v1.EXPECTED_QUERY_OPEN_BOUNDARY_COUNT == 3
    assert sum(
        row.stage is registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
        for row in manifest.boundaries
    ) == 11
    document = manifest.to_document()
    assert document["stage_local_counter_chain_authorized"] is True
    assert document["complete_source_ast_closure_present"] is False
    assert document["all_reachable_operation_sites_complete"] is False
    assert document["shared_resource_receipts_present"] is False
    assert document["occurrence_work_vector_authorized"] is False


def test_five_stage_lifecycle_materializes_only_stage_local_vectors() -> None:
    with subject.activate_query_bound_stage_accounting_v1(
        occurrence_id=_id("empty-stage-plan")
    ) as session:
        for index, stage in enumerate(subject.CANONICAL_QUERY_BOUND_STAGE_PLAN_V1):
            session.enter_stage(stage)
            session.exit_stage(
                stage,
                output_bindings=((f"OUTPUT_{index}", _id(f"output-{index}")),),
            )
        result = session.complete_occurrence()
    assert len(result.recorded_stages) == 5
    assert sum(len(row.work_vector.records) for row in result.recorded_stages) == 1_010
    assert all(
        row.work_vector.values[path] == 0
        for row in result.recorded_stages
        for path in subject.SHARED_RESOURCE_PATHS
    )
    document = result.to_document()
    assert document["stage_local_counter_chain_present"] is True
    assert document["nine_shared_resource_paths_are_zero_placeholders"] is True
    assert document["shared_resource_receipts_present"] is False
    assert document["occurrence_counter_records_issued"] is False
    assert document["occurrence_work_vector_issued"] is False
    assert document["occurrence_comparison_vector_issued"] is False


def test_direct_fallback_owner_hooks_reconcile_exact_stage_counts() -> None:
    direct = registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    with subject.activate_query_bound_stage_accounting_v1(
        occurrence_id=_id("direct-owner-hooks")
    ) as session:
        _complete_empty_prefix(session)
        session.enter_stage(direct)
        ledger = fallback_v1._QueryBoundFallbackLedgerV1()  # noqa: SLF001
        ledger.begin_route()
        ledger.expand_state()
        ledger.expand_state()
        ledger.evaluate_action()
        ledger.ground_step()
        ledger.record_outcomes(3)
        ledger.begin_solver()
        ledger.bellman_backup()
        ledger.bellman_backup()
        ledger.finish_solver(success=True)
        ledger.finish_route(success=True)
        session.exit_stage(direct)
        result = session.complete_occurrence()
    values = result.recorded_stages[-1].work_vector.values
    assert values["control.cap_checks"] == 7
    assert values["control.cap_rejections"] == 0
    assert values["fallback.states_expanded"] == 2
    assert values["fallback.actions_evaluated"] == 1
    assert values["fallback.ground_steps"] == 1
    assert values["fallback.outcome_rows"] == 3
    assert values["fallback.bellman_backups"] == 2
    assert values["route.attempts"] == 1
    assert values["route.successes"] == 1
    assert values["route.failures"] == 0
    assert values["solver.attempts"] == 1
    assert values["solver.successes"] == 1
    assert values["solver.failures"] == 0


def test_dispatch_cannot_be_forged_by_a_nonowner() -> None:
    direct = registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    with pytest.raises(subject.ConstructionK7QueryBoundStageAccountingV1Error):
        with subject.activate_query_bound_stage_accounting_v1(
            occurrence_id=_id("forged-dispatch")
        ) as session:
            _complete_empty_prefix(session)
            session.enter_stage(direct)
            hook_v1.emit_owned_operation_v1("query-fallback.state.expanded")


def test_stage_order_is_frozen() -> None:
    with pytest.raises(subject.ConstructionK7QueryBoundStageAccountingV1Error):
        with subject.activate_query_bound_stage_accounting_v1(
            occurrence_id=_id("wrong-stage-order")
        ) as session:
            session.enter_stage(
                registry_v6.ConstructionStageKindV6.OPEN_CHECKPOINT_REPLANNING
            )
