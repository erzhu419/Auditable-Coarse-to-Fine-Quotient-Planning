from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_accounting_owned_runtime_v1 as owned_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_heldout_abstract_stage_accounting_v1 as subject
from acfqp import construction_k7_heldout_checkpoint_recertification_v1 as source_v1
from acfqp import construction_k7_heldout_overlay_abstract_reuse_v1 as reuse_v1
from acfqp import observation_support_graph_acquisition_v1 as acquisition
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def accounted_result():
    source = source_v1.run_heldout_checkpoint_recertification_v1()
    reuse = reuse_v1.run_heldout_overlay_abstract_reuse_v1(
        source,
        logical_occurrence_id=_id("heldout-accounted-fresh-occurrence-v1"),
        occurrence_ordinal=3,
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("operational abstract accounting attempted ground access")

    patcher = pytest.MonkeyPatch()
    patcher.setattr(acquisition, "open_graph_partial_support_prefix_v1", forbidden)
    patcher.setattr(observer, "open_target_local_transition_stream_v1", forbidden)
    patcher.setattr(observer, "evaluation_exact_atoms_v1", forbidden)
    patcher.setattr(observer, "evaluation_exact_ground_search_v1", forbidden)
    patcher.setattr(robust, "verify_robust_plan_audit_v1", forbidden)
    patcher.setattr(source_v1, "verify_heldout_checkpoint_recertification_v1", forbidden)
    try:
        stage = subject.record_heldout_abstract_route_v1(reuse)
        yield source, reuse, stage
    finally:
        patcher.undo()


def test_domains_and_public_surface_are_additive() -> None:
    assert len(subject.LOCAL_DOMAINS) == 4
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ABSTRACT_OPERATION_PATHS",
        "CANONICAL_STAGE_PLAN_V1",
        "ConstructionK7HeldoutAbstractStageAccountingV1Error",
        "HeldoutAbstractOperationManifestV1",
        "HeldoutAbstractStageAccountingResultV1",
        "HeldoutAbstractStageProfileV1",
        "LOCAL_DOMAINS",
        "SHARED_PLACEHOLDER_PATHS",
        "official_heldout_abstract_operation_manifest_v1",
        "official_heldout_abstract_stage_profile_v1",
        "record_heldout_abstract_route_v1",
        "run_and_record_heldout_abstract_route_v1",
        "verify_heldout_abstract_stage_accounting_v1",
    }


def test_stage_profile_changes_only_open_abstract_paths() -> None:
    registry = registry_v6.official_counter_registry_v6()
    base = registry_v6.official_stage_profile_v6(registry)
    selected = subject.official_heldout_abstract_stage_profile_v1(registry)
    selected.validate(registry)
    assert selected.v6_stage_profile_id == base.stage_profile_id
    for stage, rule in selected.by_stage.items():
        added = set(rule.allowed_nonzero_paths) - set(
            base.by_stage[stage].allowed_nonzero_paths
        )
        assert added == (
            set(subject.ABSTRACT_OPERATION_PATHS)
            if stage is registry_v6.ConstructionStageKindV6.OPEN_CHECKPOINT_REPLANNING
            else set()
        )


def test_manifest_binds_exact_planner_owners() -> None:
    registry = registry_v6.official_counter_registry_v6()
    stage = subject.official_heldout_abstract_stage_profile_v1(registry)
    manifest = subject.official_heldout_abstract_operation_manifest_v1(
        registry, stage
    )
    manifest.validate(registry, stage)
    assert tuple(row.target_path for row in manifest.boundaries) == (
        "common.abstract_audit_obligations",
        "common.abstract_bellman_backups",
    )
    assert {row.operation_source_symbol for row in manifest.boundaries} == {
        "_make_audit",
        "_evaluate_ground_row",
    }


def test_operational_window_runs_one_owner_bound_abstract_plan(accounted_result) -> None:
    _source, reuse, stage = accounted_result
    document = stage.to_document()
    open_stage = stage.recorded_stages[3]
    assert document["heldout_abstract_reuse_result_id"] == reuse.result_id
    assert document["fresh_planner_called_exactly_once"] is True
    assert document["source_model_or_audit_replayed_operationally"] is False
    assert document["fresh_ground_or_observer_event_count"] == 0
    assert document["abstract_audit_obligations"] == 1
    assert document["abstract_bellman_backups"] > 0
    assert len(open_stage.operation_events) == 2
    assert {row.path for row in open_stage.operation_events} == set(
        subject.ABSTRACT_OPERATION_PATHS
    )
    assert stage.business_hash_invocations > 0


def test_stage_vectors_are_complete_and_shared_paths_are_placeholders(
    accounted_result,
) -> None:
    _source, _reuse, stage = accounted_result
    assert len(stage.recorded_stages) == 5
    for row in stage.recorded_stages:
        assert len(row.work_vector.records) == registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
        assert all(
            row.work_vector.values[path] == 0
            for path in subject.SHARED_PLACEHOLDER_PATHS
        )
    assert stage.recorded_stages[-1].work_vector.values["route.attempts"] == 1
    assert stage.recorded_stages[-1].work_vector.values["route.successes"] == 1
    assert stage.recorded_stages[-1].work_vector.values["route.failures"] == 0


def test_all_local_ground_fallback_and_rebuild_families_are_native_zero(
    accounted_result,
) -> None:
    _source, _reuse, stage = accounted_result
    for row in stage.recorded_stages:
        values = row.work_vector.values
        assert all(
            value == 0
            for path, value in values.items()
            if path.startswith(("local.", "fallback.", "rebuild."))
        )


def test_result_and_every_stage_replay(accounted_result) -> None:
    _source, _reuse, stage = accounted_result
    assert subject.verify_heldout_abstract_stage_accounting_v1(stage) is stage


def test_hooks_are_inactive_without_an_accounting_scope(accounted_result) -> None:
    source, _reuse, _stage = accounted_result
    assert owned_v1._ACTIVE_RUNTIME.get() is None  # noqa: SLF001
    replay = robust.solve_quotient_robust_h2_v1(
        source.final_overlay.bridge.quotient_model,
        source.threshold,
    )
    assert replay.audit_id == source.final_overlay.audit.audit_id


def test_claim_locks_remain_closed(accounted_result) -> None:
    document = accounted_result[-1].to_document()
    assert document["nine_shared_paths_are_stage_placeholders"] is True
    assert document["shared_resource_receipts_issued"] is False
    assert document["occurrence_work_vector_issued"] is False
    assert document["terminal_artifact_issued"] is False
    assert document["campaign_occurrence_closed"] is False
    assert document["scientific_endpoint_credit_allowed"] is False
    assert document["official_execution_allowed"] is False
    assert document["counter_completeness_gate_status"] == (
        "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )
    assert document["workload_economics_gate_status"] == (
        "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    )
