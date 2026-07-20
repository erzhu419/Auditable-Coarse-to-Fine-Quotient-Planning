from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from acfqp.artifacts import object_id
from acfqp.dynamic_router import (
    ABSTRACT_AUDIT_REQUIRED,
    ABSTRACT_CERTIFIED,
    CAUSAL_CAP_EXHAUSTED,
    CAUSAL_FAMILY_FOUND,
    DIRECT_FALLBACK,
    FALLBACK_ATTEMPT_SELECTED,
    FALLBACK_CAP_EXHAUSTED_NO_CERTIFICATE,
    FALLBACK_ESTIMATE_SEMANTICS,
    FULL_GROUND_FALLBACK,
    FULL_GROUND_FALLBACK_REQUIRED,
    INFEASIBLE_QUERY,
    LOCAL_ATTEMPT,
    LOCAL_ATTEMPT_SELECTED,
    LOCAL_ESTIMATE_SEMANTICS,
    LOCAL_GROUND_RECOVERY,
    NEXT_LOCAL_TRANSACTION_REQUIRED,
    NO_SOUND_CAUSAL_COVER,
    REBUILD_REQUIRED,
    RECOVERY_DECISION_REQUIRED,
    ArtifactIntegrityError,
    PreflightEvidence,
    RouteEstimate,
    RouterProtocolError,
    append_route_trace_event,
    decide_preflight,
    resolve_fallback,
    resolve_local_attempt,
    select_recovery_attempt,
    verify_actual_within_estimate,
    verify_route_trace,
    verify_route_trace_documents,
)
from acfqp.phase3b import run_phase3b
from acfqp.phase3e_accounting import (
    COUNTER_COMPLETENESS_NOT_RUN,
    ECONOMICS_NOT_RUN,
    LEGACY_PROJECTION_LABEL,
    NATIVE_REGISTRY_DRAFT,
    ROUTING_MECHANICS_ONLY,
    legacy_phase3b_projection,
    legacy_phase3b_registry,
    phase3e_native_registry_draft,
    phase3e_preregistration_skeleton,
)
from acfqp.work_accounting import (
    BYTE,
    CHARGED_BYTE,
    CHARGED_OP,
    COUNT,
    DERIVED_ALIAS,
    DIAGNOSTIC_CARDINALITY,
    EQUAL,
    EVALUATION_ONLY,
    INCOMPARABLE,
    LEFT_DOMINATES,
    OPERATION,
    OPERATIONAL,
    RIGHT_DOMINATES,
    CounterLeaf,
    CounterRecord,
    CounterRegistry,
    CounterValidationError,
    WorkVector,
    componentwise_cost_relation,
    diagnostic_unit_work_v1,
)


def _small_registry() -> CounterRegistry:
    leaves = (
        CounterLeaf("route.bytes", CHARGED_BYTE, BYTE, OPERATIONAL, "test"),
        CounterLeaf("route.diagnostic", DIAGNOSTIC_CARDINALITY, COUNT, OPERATIONAL, "test"),
        CounterLeaf("route.operations", CHARGED_OP, OPERATION, OPERATIONAL, "test"),
    )
    return CounterRegistry("phase3e-test-registry", "v1", leaves)


def _vector(
    registry: CounterRegistry,
    subject: str,
    *,
    operations: int,
    byte_count: int,
    diagnostic: int = 0,
) -> WorkVector:
    return WorkVector(
        registry.registry_id,
        subject,
        (
            ("route.bytes", byte_count),
            ("route.diagnostic", diagnostic),
            ("route.operations", operations),
        ),
    )


def _failed_preflight() -> object:
    return decide_preflight(
        PreflightEvidence(
            "protocol-candidate",
            "epoch-1",
            "occurrence-1",
            True,
            True,
            True,
            True,
            False,
            True,
            False,
        )
    )


def _estimate(
    registry: CounterRegistry,
    route_candidate: str,
    vector: WorkVector,
    *,
    decision_point: str = "decision-1",
) -> RouteEstimate:
    return RouteEstimate(
        route_candidate=route_candidate,
        estimate_semantics=(
            LOCAL_ESTIMATE_SEMANTICS
            if route_candidate == LOCAL_ATTEMPT
            else FALLBACK_ESTIMATE_SEMANTICS
        ),
        protocol_candidate_id="protocol-candidate",
        epoch_id="epoch-1",
        logical_occurrence_id="occurrence-1",
        decision_point_id=decision_point,
        cap_profile_candidate_id="cap-candidate",
        derivation_id=f"derivation-{route_candidate.lower()}",
        input_cardinality_id=f"cardinality-{route_candidate.lower()}",
        vector=vector,
    )


def test_work_accounting_requires_every_canonical_leaf_and_validates_aliases() -> None:
    leaves = (
        CounterLeaf("compat.operations", DERIVED_ALIAS, OPERATION, OPERATIONAL, "adapter", alias_of="work.operations"),
        CounterLeaf("work.bytes", CHARGED_BYTE, BYTE, OPERATIONAL, "worker"),
        CounterLeaf("work.operations", CHARGED_OP, OPERATION, OPERATIONAL, "worker"),
    )
    registry = CounterRegistry("strict-test", "v1", leaves)
    record = CounterRecord.create(
        registry.registry_id,
        "subject",
        {"compat.operations": 3, "work.bytes": 4096, "work.operations": 3},
    )
    vector = registry.reconcile(record)

    assert diagnostic_unit_work_v1(vector, registry) == 4
    assert CounterRegistry.from_dict(registry.to_dict()) == registry
    assert CounterRecord.from_dict(record.to_dict()) == record
    assert WorkVector.from_dict(vector.to_dict()) == vector

    with pytest.raises(CounterValidationError, match="missing required"):
        registry.reconcile(
            CounterRecord.create(
                registry.registry_id,
                "missing",
                {"compat.operations": 3, "work.operations": 3},
            )
        )
    with pytest.raises(CounterValidationError, match="alias differs"):
        registry.reconcile(
            CounterRecord.create(
                registry.registry_id,
                "bad-alias",
                {"compat.operations": 4, "work.bytes": 4096, "work.operations": 3},
            )
        )

    forged = WorkVector(
        registry.registry_id,
        "forged",
        (("work.operations", 3),),
    )
    with pytest.raises(CounterValidationError, match="component set mismatch"):
        registry.validate_vector(forged)

    tampered = vector.to_dict()
    tampered["values"][0]["value"] += 1
    with pytest.raises(CounterValidationError, match="content ID mismatch"):
        WorkVector.from_dict(tampered)


def test_componentwise_relation_ignores_diagnostics_but_requires_exact_shape() -> None:
    registry = _small_registry()
    local = _vector(registry, "local", operations=1, byte_count=10, diagnostic=999)
    fallback = _vector(registry, "fallback", operations=2, byte_count=20)
    assert componentwise_cost_relation(local, fallback, registry) == LEFT_DOMINATES
    assert componentwise_cost_relation(fallback, local, registry) == RIGHT_DOMINATES
    equal_charged = _vector(registry, "equal", operations=1, byte_count=10)
    assert componentwise_cost_relation(local, equal_charged, registry) == EQUAL
    incomparable = _vector(registry, "cross", operations=2, byte_count=5)
    assert componentwise_cost_relation(local, incomparable, registry) == INCOMPARABLE


def test_preregistration_is_result_blind_and_counter_incomplete() -> None:
    registry = phase3e_native_registry_draft()
    prereg = phase3e_preregistration_skeleton()
    leaves = registry.by_path

    assert CounterRegistry.from_dict(registry.to_dict()) == registry
    assert prereg["official_execution_allowed"] is False
    assert prereg["official_scalar_cost_functional"] is None
    assert prereg["official_n_break_even"] is None
    assert prereg["native_counter_registry_status"] == NATIVE_REGISTRY_DRAFT
    assert prereg["counter_completeness_gate_status"] == COUNTER_COMPLETENESS_NOT_RUN
    assert prereg["routing_protocol_status"] == ROUTING_MECHANICS_ONLY
    assert prereg["economics_gate_status"] == ECONOMICS_NOT_RUN
    assert prereg["unresolved_questions"] == tuple(f"Q{i}" for i in range(1, 12))
    assert "official_dynamic_route_selection" in prereg["forbidden_before_freeze"]
    assert "pre_audit.invocations" in leaves
    assert "post_audit.invocations" in leaves
    assert "audit.invocations" not in leaves
    assert leaves["local.stitch_decisions"].kind == DIAGNOSTIC_CARDINALITY
    assert leaves["local.stitch_invocations"].kind == CHARGED_OP


def test_legacy_phase3b_projection_is_diagnostic_and_reconciled(tmp_path: Path) -> None:
    bundle = tmp_path / "phase3b"
    run_phase3b(bundle)
    source = json.loads(
        (bundle / "accounting/work_counters.json").read_text(encoding="utf-8")
    )
    projection = legacy_phase3b_projection(source)
    diagnostic = projection["diagnostic_unit_work_v1"]

    assert projection["label"] == LEGACY_PROJECTION_LABEL
    assert projection["economics_gate_status"] == ECONOMICS_NOT_RUN
    assert projection["official_scalar_cost"] is None
    assert projection["official_n_break_even"] is None
    assert projection["source_counts"] == {
        "build_operations": 1022,
        "build_bytes": 207753,
        "query_operations": 185,
        "query_bytes": 1218041,
        "ground_candidates": 114467,
        "ground_invocations_inferred": 11,
        "fallback_invocations": 0,
        "fallback_candidates": 0,
    }
    assert diagnostic["build"] == {"numerator": 4393865, "denominator": 4096}
    assert diagnostic["world_total"] == {"numerator": 3184833, "denominator": 2048}
    assert diagnostic["ground_comparator"] == {"numerator": 114478, "denominator": 1}
    assert diagnostic["registered_order_n_break_even"] == 1
    assert diagnostic["diagnostic_worst_order_n_break_even"] == 5
    trace = projection["per_occurrence_prefix_trace"]
    assert len(trace) == 11
    assert [row["prefix_length"] for row in trace] == list(range(1, 12))
    assert all(row["ground_invocation_inferred"] is True for row in trace)
    assert trace[-1]["cumulative_world"] == diagnostic["world_total"]
    assert trace[-1]["cumulative_ground"] == diagnostic["ground_comparator"]

    legacy_registry = legacy_phase3b_registry()
    inferred = legacy_registry.by_path["comparator.ground_invocations_inferred"]
    assert inferred.kind == DIAGNOSTIC_CARDINALITY
    assert inferred.scope == EVALUATION_ONLY

    bad_alias = copy.deepcopy(source)
    bad_alias["query"][0]["full_fallback_candidate_count"] = 1
    with pytest.raises(CounterValidationError, match="alias mismatch"):
        legacy_phase3b_projection(bad_alias)


@pytest.mark.parametrize(
    ("updates", "expected"),
    (
        ({"identity_compatible": False, "matching_exact_infeasibility_proof": True}, REBUILD_REQUIRED),
        ({"matching_exact_infeasibility_proof": True}, INFEASIBLE_QUERY),
        ({"abstract_audit_complete": False}, ABSTRACT_AUDIT_REQUIRED),
        ({"abstract_certificate_passed": True}, ABSTRACT_CERTIFIED),
        ({}, RECOVERY_DECISION_REQUIRED),
    ),
)
def test_preflight_precedence(updates: dict[str, bool], expected: str) -> None:
    fields = {
        "protocol_candidate_id": "protocol-candidate",
        "epoch_id": "epoch-1",
        "logical_occurrence_id": "occurrence-1",
        "artifact_integrity_valid": True,
        "identity_compatible": True,
        "coverage_compatible": True,
        "semantics_compatible": True,
        "matching_exact_infeasibility_proof": False,
        "abstract_audit_complete": True,
        "abstract_certificate_passed": False,
    }
    fields.update(updates)
    assert decide_preflight(PreflightEvidence(**fields)).status == expected


def test_integrity_failure_is_not_rebuild_route() -> None:
    evidence = PreflightEvidence(
        "protocol-candidate",
        "epoch-1",
        "occurrence-1",
        False,
        False,
        False,
        False,
        False,
        False,
        False,
    )
    with pytest.raises(ArtifactIntegrityError):
        decide_preflight(evidence)


def test_candidate_router_is_conservative_for_equal_or_incomparable_vectors() -> None:
    registry = _small_registry()
    preflight = _failed_preflight()
    fallback = _estimate(
        registry,
        DIRECT_FALLBACK,
        _vector(registry, "fallback", operations=10, byte_count=100),
    )
    local_dominates = _estimate(
        registry,
        LOCAL_ATTEMPT,
        _vector(registry, "local-low", operations=9, byte_count=99, diagnostic=1000),
    )
    selected = select_recovery_attempt(
        preflight=preflight,
        causal_status=CAUSAL_FAMILY_FOUND,
        local_estimate=local_dominates,
        fallback_estimate=fallback,
        registry=registry,
    )
    assert selected.selected_attempt == LOCAL_ATTEMPT_SELECTED
    assert selected.cost_relation == LEFT_DOMINATES
    assert selected.official is False

    cases = (
        (_vector(registry, "equal", operations=10, byte_count=100), EQUAL),
        (_vector(registry, "incomparable", operations=9, byte_count=101), INCOMPARABLE),
        (_vector(registry, "fallback-lower", operations=11, byte_count=101), RIGHT_DOMINATES),
    )
    for vector, relation in cases:
        result = select_recovery_attempt(
            preflight=preflight,
            causal_status=CAUSAL_FAMILY_FOUND,
            local_estimate=_estimate(registry, LOCAL_ATTEMPT, vector),
            fallback_estimate=fallback,
            registry=registry,
        )
        assert result.selected_attempt == FALLBACK_ATTEMPT_SELECTED
        assert result.cost_relation == relation

    for causal in (CAUSAL_CAP_EXHAUSTED, NO_SOUND_CAUSAL_COVER):
        result = select_recovery_attempt(
            preflight=preflight,
            causal_status=causal,
            local_estimate=None,
            fallback_estimate=fallback,
            registry=registry,
        )
        assert result.selected_attempt == FALLBACK_ATTEMPT_SELECTED
        assert result.local_estimate_id is None


def test_route_estimates_reject_post_result_dependency_and_binding_mismatch() -> None:
    registry = _small_registry()
    vector = _vector(registry, "route", operations=1, byte_count=1)
    with pytest.raises(RouterProtocolError, match="post-run"):
        RouteEstimate(
            LOCAL_ATTEMPT,
            LOCAL_ESTIMATE_SEMANTICS,
            "protocol-candidate",
            "epoch-1",
            "occurrence-1",
            "decision-1",
            "cap-candidate",
            "derivation",
            "cardinality",
            vector,
            depends_on_actual_selected_route_counters=True,
        )

    local = _estimate(registry, LOCAL_ATTEMPT, vector, decision_point="other-decision")
    fallback = _estimate(registry, DIRECT_FALLBACK, vector)
    with pytest.raises(RouterProtocolError, match="different decisions"):
        select_recovery_attempt(
            preflight=_failed_preflight(),
            causal_status=CAUSAL_FAMILY_FOUND,
            local_estimate=local,
            fallback_estimate=fallback,
            registry=registry,
        )

    tampered = fallback.to_dict()
    tampered["derivation_id"] = "forged"
    with pytest.raises(RouterProtocolError, match="content ID mismatch"):
        RouteEstimate.from_dict(tampered)


def test_actual_work_caps_and_terminal_resolution_are_fail_closed() -> None:
    registry = _small_registry()
    estimate = _estimate(
        registry,
        LOCAL_ATTEMPT,
        _vector(registry, "upper", operations=4, byte_count=40),
    )
    verify_actual_within_estimate(
        _vector(registry, "actual", operations=4, byte_count=39, diagnostic=999),
        estimate,
        registry,
    )
    with pytest.raises(RouterProtocolError, match="exceeds"):
        verify_actual_within_estimate(
            _vector(registry, "too-much", operations=5, byte_count=39),
            estimate,
            registry,
        )

    assert resolve_local_attempt(
        post_audit_certified=True,
        deeper_failed_frontier_exists=False,
        transaction_budget_remaining=False,
    ) == LOCAL_GROUND_RECOVERY
    assert resolve_local_attempt(
        post_audit_certified=False,
        deeper_failed_frontier_exists=True,
        transaction_budget_remaining=True,
    ) == NEXT_LOCAL_TRANSACTION_REQUIRED
    assert resolve_local_attempt(
        post_audit_certified=False,
        deeper_failed_frontier_exists=True,
        transaction_budget_remaining=False,
    ) == FULL_GROUND_FALLBACK_REQUIRED

    assert resolve_fallback(complete=True, feasible=True, cap_exhausted=False) == FULL_GROUND_FALLBACK
    assert resolve_fallback(complete=True, feasible=False, cap_exhausted=False) == INFEASIBLE_QUERY
    assert resolve_fallback(complete=False, feasible=False, cap_exhausted=True) == FALLBACK_CAP_EXHAUSTED_NO_CERTIFICATE
    with pytest.raises(RouterProtocolError):
        resolve_fallback(complete=False, feasible=False, cap_exhausted=False)


def test_route_trace_roundtrip_reconciliation_and_chain_attack() -> None:
    registry = _small_registry()
    events = []
    first = append_route_trace_event(
        events,
        protocol_candidate_id="protocol-candidate",
        epoch_id="epoch-1",
        logical_occurrence_id="occurrence-1",
        route_attempt_id="attempt-1",
        transaction_id=None,
        stage="preflight",
        decision_code="RECOVERY_REQUIRED",
        evidence_ids=("evidence-1",),
        work_delta=_vector(registry, "delta-0", operations=1, byte_count=10),
    )
    events.append(first)
    second = append_route_trace_event(
        events,
        protocol_candidate_id="protocol-candidate",
        epoch_id="epoch-1",
        logical_occurrence_id="occurrence-1",
        route_attempt_id="attempt-1",
        transaction_id="transaction-1",
        stage="local_attempt",
        decision_code="POST_AUDIT_PASS",
        evidence_ids=("evidence-2",),
        work_delta=_vector(registry, "delta-1", operations=2, byte_count=20),
    )
    events.append(second)
    total = verify_route_trace(events, registry)
    assert total.value("route.operations") == 3
    assert total.value("route.bytes") == 30

    documents = [event.to_dict() for event in events]
    replayed, replay_total = verify_route_trace_documents(documents, registry)
    assert replayed == tuple(events)
    assert replay_total.values == total.values

    tampered = copy.deepcopy(documents)
    tampered[1]["decision_code"] = "FORGED"
    with pytest.raises(RouterProtocolError, match="content ID mismatch"):
        verify_route_trace_documents(tampered, registry)

    coordinated = copy.deepcopy(documents)
    coordinated[1]["prev_event_id"] = "wrong-predecessor"
    payload = {key: value for key, value in coordinated[1].items() if key != "event_id"}
    coordinated[1]["event_id"] = object_id(payload, "route-trace-event")
    with pytest.raises(RouterProtocolError, match="hash chain"):
        verify_route_trace_documents(coordinated, registry)
