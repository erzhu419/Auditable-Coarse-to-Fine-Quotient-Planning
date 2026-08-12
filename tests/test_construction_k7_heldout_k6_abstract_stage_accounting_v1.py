from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_accounting_owned_runtime_v1 as owned_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_heldout_abstract_stage_accounting_v1 as shared_v1
from acfqp import construction_k7_heldout_k6_abstract_stage_accounting_v1 as subject
from acfqp import construction_k7_heldout_k6_checkpoint_recertification_v1 as source_v1
from acfqp import construction_k7_heldout_k6_overlay_abstract_reuse_v1 as reuse_v1
from acfqp import observation_support_graph_acquisition_v1 as acquisition
from acfqp import observation_support_graph_model_v1 as graph_model
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def accounted_result():
    source = source_v1.run_heldout_k6_checkpoint_recertification_v1()
    query = reuse_v1.freeze_heldout_k6_overlay_query_v1(
        source,
        logical_occurrence_id=_id("heldout-k6-accounted-fresh-occurrence"),
        occurrence_ordinal=8,
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("operational K6 accounting attempted non-planner work")

    patcher = pytest.MonkeyPatch()
    patcher.setattr(acquisition, "open_graph_partial_support_prefix_v1", forbidden)
    patcher.setattr(observer, "open_target_local_transition_stream_v1", forbidden)
    patcher.setattr(observer, "evaluation_exact_atoms_v1", forbidden)
    patcher.setattr(observer, "evaluation_exact_ground_search_v1", forbidden)
    patcher.setattr(graph_model, "build_observation_support_graph_models_v1", forbidden)
    patcher.setattr(robust, "solve_ground_direct_robust_h2_v1", forbidden)
    patcher.setattr(robust, "verify_robust_plan_audit_v1", forbidden)
    patcher.setattr(source_v1, "run_heldout_k6_checkpoint_recertification_v1", forbidden)
    patcher.setattr(source_v1, "verify_heldout_k6_checkpoint_recertification_v1", forbidden)
    patcher.setattr(reuse_v1, "run_heldout_k6_overlay_abstract_reuse_v1", forbidden)
    try:
        stage = subject.run_and_record_heldout_k6_abstract_route_v1(source, query)
    finally:
        patcher.undo()
    return source, query, stage


def test_domain_and_surface_are_additive() -> None:
    assert len(subject.LOCAL_DOMAINS) == 1
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ABSTRACT_OPERATION_PATHS",
        "CANONICAL_STAGE_PLAN_V1",
        "ConstructionK7HeldoutK6AbstractStageAccountingV1Error",
        "HeldoutK6AbstractStageAccountingResultV1",
        "LOCAL_DOMAINS",
        "SHARED_PLACEHOLDER_PATHS",
        "record_heldout_k6_abstract_route_v1",
        "run_and_record_heldout_k6_abstract_route_v1",
        "verify_heldout_k6_abstract_stage_accounting_v1",
    }


def test_k6_reuses_exact_shared_stage_profile_and_operation_manifest() -> None:
    registry = registry_v6.official_counter_registry_v6()
    stage_profile = shared_v1.official_heldout_abstract_stage_profile_v1(registry)
    manifest = shared_v1.official_heldout_abstract_operation_manifest_v1(
        registry, stage_profile
    )
    stage_profile.validate(registry)
    manifest.validate(registry, stage_profile)
    assert tuple(row.target_path for row in manifest.boundaries) == (
        "common.abstract_audit_obligations",
        "common.abstract_bellman_backups",
    )


def test_operational_window_runs_one_owner_bound_k6_plan(accounted_result) -> None:
    source, query, stage = accounted_result
    document = stage.to_document()
    assert stage.reuse_result.query == query
    assert stage.reuse_result.source is source
    assert stage.reuse_result.plan.audit.audit_id == source.overlay.audit.audit_id
    assert document["heldout_k6_abstract_reuse_result_id"] == (
        stage.reuse_result.result_id
    )
    assert document["fresh_planner_called_exactly_once"] is True
    assert document["source_model_or_audit_replayed_operationally"] is False
    assert document["promoted_k6_model_reused_without_rebuild"] is True
    assert document["fresh_ground_or_observer_event_count"] == 0
    assert document["abstract_audit_obligations"] == 1
    assert document["abstract_bellman_backups"] > 0
    assert stage.business_hash_invocations > 0


def test_stage_vectors_are_complete_and_shared_paths_are_placeholders(
    accounted_result,
) -> None:
    _source, _query, stage = accounted_result
    assert len(stage.recorded_stages) == 5
    for row in stage.recorded_stages:
        assert len(row.work_vector.records) == (
            registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
        )
        assert all(
            row.work_vector.values[path] == 0
            for path in subject.SHARED_PLACEHOLDER_PATHS
        )
    terminal = stage.recorded_stages[-1].work_vector.values
    assert terminal["route.attempts"] == 1
    assert terminal["route.successes"] == 1
    assert terminal["route.failures"] == 0


def test_all_ground_fallback_and_rebuild_families_are_native_zero(
    accounted_result,
) -> None:
    _source, _query, stage = accounted_result
    for row in stage.recorded_stages:
        assert all(
            value == 0
            for path, value in row.work_vector.values.items()
            if path.startswith(("local.", "fallback.", "rebuild."))
        )


def test_result_and_every_stage_replay(accounted_result) -> None:
    _source, _query, stage = accounted_result
    assert subject.verify_heldout_k6_abstract_stage_accounting_v1(stage) is stage
    assert owned_v1._ACTIVE_RUNTIME.get() is None  # noqa: SLF001


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
