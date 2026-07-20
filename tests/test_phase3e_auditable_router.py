from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from acfqp.auditable_router import (
    ABSTRACT_AUDIT,
    ABSTRACT_FAILED,
    AuditableRouterError,
    CACHE_PROOF,
    CAUSAL_SEARCH,
    CERTIFIED,
    COMPATIBILITY,
    FAIL,
    FALLBACK_CAP_EXHAUSTED_ATTEMPT_TERMINAL,
    FALLBACK_RESULT,
    FOUND,
    INCOMPLETE_DUE_TO_CAP,
    INTEGRITY,
    LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL,
    LOCAL_RESULT,
    MATCH,
    MISS,
    NO_SOUND_COVER,
    PASS,
    ROUTE_SELECTION,
    SELECT_FALLBACK_INCOMPARABLE,
    RouteDecisionContext,
    RouteTraceEvent,
    TransitionEvidence,
    append_route_event,
    build_route_envelope,
    evidence_work_subject,
    make_route_selection_evidence,
    replay_route_events,
    verify_route_envelope,
)
from acfqp.phase3b import run_phase3b
from acfqp.phase3e_accounting import (
    legacy_phase3b_projection,
    phase3e_native_registry_draft,
    phase3e_preregistration_skeleton,
)
from acfqp.route_comparison import (
    DIRECT_FALLBACK,
    LOCAL_ATTEMPT,
    AxisTerm,
    CardinalityEvidence,
    ComparisonFormulaCandidate,
    ComparisonProfileCandidate,
    ComparisonValidationError,
    ComparisonVector,
    RouteUpperBoundCandidate,
    compare_route_upper_bounds,
    derive_route_upper_bound,
    verify_route_upper_bound,
)
from acfqp.work_accounting import (
    BYTE,
    CHARGED_BYTE,
    CHARGED_OP,
    INCOMPARABLE,
    LEFT_DOMINATES,
    OPERATION,
    OPERATIONAL,
    CounterLeaf,
    CounterRegistry,
    CounterValidationError,
    WorkVector,
    componentwise_cost_relation,
)


def _registry() -> CounterRegistry:
    return CounterRegistry(
        "auditable-router-test",
        "v1",
        (
            CounterLeaf("work.bytes", CHARGED_BYTE, BYTE, OPERATIONAL, "test"),
            CounterLeaf("work.operations", CHARGED_OP, OPERATION, OPERATIONAL, "test"),
        ),
    )


def _work(
    registry: CounterRegistry,
    context_id: str,
    role: str,
    transaction_id: str | None,
    operations: int = 1,
    byte_count: int = 0,
) -> WorkVector:
    return WorkVector(
        registry.registry_id,
        evidence_work_subject(context_id, role, transaction_id),
        (("work.bytes", byte_count), ("work.operations", operations)),
    )


def _comparison_fixture() -> tuple[
    CounterRegistry,
    ComparisonProfileCandidate,
    RouteDecisionContext,
    RouteUpperBoundCandidate,
    RouteUpperBoundCandidate,
]:
    registry = _registry()
    profile = ComparisonProfileCandidate(
        "shared-resource-candidate",
        "v0",
        ("resource.bytes", "resource.operations"),
    )
    context = RouteDecisionContext(
        preregistration_skeleton_id=phase3e_preregistration_skeleton()["skeleton_id"],
        protocol_candidate_id="protocol-candidate",
        comparison_profile_candidate_id=profile.profile_id,
        counter_registry_id=registry.registry_id,
        structural_id="structural-1",
        query_id="query-1",
        plan_id="plan-1",
        threshold_profile_id="threshold-1",
        epoch_id="epoch-1",
        logical_occurrence_id="occurrence-1",
        route_attempt_id="attempt-1",
    )
    terms = (
        AxisTerm("resource.bytes", "input.bytes", 1),
        AxisTerm("resource.operations", "input.operations", 1),
    )
    local_cardinality = CardinalityEvidence(
        context.context_id,
        LOCAL_ATTEMPT,
        (("input.bytes", 10), ("input.operations", 1)),
        ("local-cardinality-source",),
    )
    fallback_cardinality = CardinalityEvidence(
        context.context_id,
        DIRECT_FALLBACK,
        (("input.bytes", 20), ("input.operations", 2)),
        ("fallback-cardinality-source",),
    )
    local_formula = ComparisonFormulaCandidate(
        profile.profile_id, LOCAL_ATTEMPT, "local-formula-candidate", terms
    )
    fallback_formula = ComparisonFormulaCandidate(
        profile.profile_id, DIRECT_FALLBACK, "fallback-formula-candidate", terms
    )
    return (
        registry,
        profile,
        context,
        derive_route_upper_bound(profile, local_cardinality, local_formula),
        derive_route_upper_bound(profile, fallback_cardinality, fallback_formula),
    )


def _refs(**items: str) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(items.items()))


def _evidence(
    registry: CounterRegistry,
    context: RouteDecisionContext,
    role: str,
    outcome: str,
    refs: tuple[tuple[str, str], ...],
    *,
    transaction_id: str | None = None,
    actual: ComparisonVector | None = None,
) -> TransitionEvidence:
    return TransitionEvidence(
        context.context_id,
        role,
        outcome,
        refs,
        _work(registry, context.context_id, role, transaction_id),
        transaction_id=transaction_id,
        actual_comparison=actual,
    )


def _pre_local_events(
    registry: CounterRegistry,
    profile: ComparisonProfileCandidate,
    context: RouteDecisionContext,
    local_bound: RouteUpperBoundCandidate,
    fallback_bound: RouteUpperBoundCandidate,
) -> tuple[list[RouteTraceEvent], dict[str, RouteUpperBoundCandidate], set[str]]:
    bounds = {local_bound.bound_id: local_bound, fallback_bound.bound_id: fallback_bound}
    verified = {
        "integrity-ok",
        "compatibility-ok",
        "cache-check",
        "abstract-audit",
        "failed-proof",
        "threshold-1",
        "causal-certificate",
        "local-authorization",
        profile.profile_id,
        local_bound.bound_id,
        fallback_bound.bound_id,
    }
    evidence = (
        _evidence(
            registry,
            context,
            INTEGRITY,
            PASS,
            _refs(integrity_attestation="integrity-ok"),
        ),
        _evidence(
            registry,
            context,
            COMPATIBILITY,
            MATCH,
            _refs(compatibility_attestation="compatibility-ok"),
        ),
        _evidence(
            registry,
            context,
            CACHE_PROOF,
            MISS,
            _refs(cache_proof_check="cache-check"),
        ),
        _evidence(
            registry,
            context,
            ABSTRACT_AUDIT,
            FAIL,
            _refs(
                abstract_audit="abstract-audit",
                failed_proof_graph="failed-proof",
                threshold_profile="threshold-1",
            ),
        ),
        _evidence(
            registry,
            context,
            CAUSAL_SEARCH,
            FOUND,
            _refs(
                causal_certificate="causal-certificate",
                local_authorization="local-authorization",
            ),
            transaction_id="transaction-1",
        ),
    )
    events: list[RouteTraceEvent] = []
    for item in evidence:
        events.append(
            append_route_event(
                context=context,
                events=events,
                evidence=item,
                registry=registry,
                bounds=bounds,
                verified_artifact_ids=verified,
            )
        )
    selection = make_route_selection_evidence(
        context=context,
        work_delta=_work(
            registry, context.context_id, ROUTE_SELECTION, "transaction-1"
        ),
        fallback_bound=fallback_bound,
        local_bound=local_bound,
        transaction_id="transaction-1",
    )
    events.append(
        append_route_event(
            context=context,
            events=events,
            evidence=selection,
            registry=registry,
            bounds=bounds,
            verified_artifact_ids=verified,
        )
    )
    return events, bounds, verified


def test_shared_comparison_bounds_are_recomputed_not_raw_accounting_axes() -> None:
    registry, profile, context, local, fallback = _comparison_fixture()
    assert ComparisonProfileCandidate.from_dict(profile.to_dict()) == profile
    assert compare_route_upper_bounds(local, fallback) == LEFT_DOMINATES

    wrong = RouteUpperBoundCandidate(
        local.context_id,
        local.route_candidate,
        local.profile_id,
        local.cardinality_evidence_id,
        local.formula_id,
        ComparisonVector(
            profile.profile_id,
            context.context_id,
            LOCAL_ATTEMPT,
            (("resource.bytes", 11), ("resource.operations", 1)),
        ),
    )
    local_cardinality = CardinalityEvidence(
        context.context_id,
        LOCAL_ATTEMPT,
        (("input.bytes", 10), ("input.operations", 1)),
        ("local-cardinality-source",),
    )
    terms = (
        AxisTerm("resource.bytes", "input.bytes", 1),
        AxisTerm("resource.operations", "input.operations", 1),
    )
    formula = ComparisonFormulaCandidate(
        profile.profile_id, LOCAL_ATTEMPT, "local-formula-candidate", terms
    )
    with pytest.raises(ComparisonValidationError, match="does not recompute"):
        verify_route_upper_bound(wrong, profile, local_cardinality, formula)

    native = phase3e_native_registry_draft()
    local_values = {leaf.path: 0 for leaf in native.canonical_leaves}
    fallback_values = dict(local_values)
    local_values["local.transaction_invocations"] = 1
    fallback_values["fallback.invocations"] = 1
    raw_local = WorkVector(
        native.registry_id, "raw-local", tuple(sorted(local_values.items()))
    )
    raw_fallback = WorkVector(
        native.registry_id, "raw-fallback", tuple(sorted(fallback_values.items()))
    )
    assert componentwise_cost_relation(raw_local, raw_fallback, native) == INCOMPARABLE
    assert registry.registry_id == context.counter_registry_id


def test_complete_auditable_local_route_replays_and_prefix_cannot_certify() -> None:
    registry, profile, context, local_bound, fallback_bound = _comparison_fixture()
    events, bounds, verified = _pre_local_events(
        registry, profile, context, local_bound, fallback_bound
    )
    actual = ComparisonVector(
        profile.profile_id,
        context.context_id,
        LOCAL_ATTEMPT,
        (("resource.bytes", 9), ("resource.operations", 1)),
    )
    verified.update({"local-result", "post-audit-pass", "local-actual-work"})
    result = _evidence(
        registry,
        context,
        LOCAL_RESULT,
        CERTIFIED,
        _refs(
            actual_work="local-actual-work",
            local_result="local-result",
            post_audit_certificate="post-audit-pass",
        ),
        transaction_id="transaction-1",
        actual=actual,
    )
    events.append(
        append_route_event(
            context=context,
            events=events,
            evidence=result,
            registry=registry,
            bounds=bounds,
            verified_artifact_ids=verified,
        )
    )
    envelope = build_route_envelope(
        context=context,
        events=events,
        registry=registry,
        bounds=bounds,
        verified_artifact_ids=verified,
        complete=True,
    )
    assert envelope.final_state == LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL
    assert envelope.accumulated_work.value("work.operations") == len(events)
    verify_route_envelope(
        envelope=envelope,
        context=context,
        registry=registry,
        bounds=bounds,
        verified_artifact_ids=verified,
    )

    prefix = build_route_envelope(
        context=context,
        events=events[:-1],
        registry=registry,
        bounds=bounds,
        verified_artifact_ids=verified,
        complete=False,
    )
    with pytest.raises(AuditableRouterError, match="incomplete route prefix"):
        verify_route_envelope(
            envelope=prefix,
            context=context,
            registry=registry,
            bounds=bounds,
            verified_artifact_ids=verified,
        )
    with pytest.raises(AuditableRouterError, match="nonterminal prefix"):
        build_route_envelope(
            context=context,
            events=events[:-1],
            registry=registry,
            bounds=bounds,
            verified_artifact_ids=verified,
            complete=True,
        )


def test_state_replay_rejects_unverified_refs_wrong_selection_and_over_cap() -> None:
    registry, profile, context, local_bound, fallback_bound = _comparison_fixture()
    events, bounds, verified = _pre_local_events(
        registry, profile, context, local_bound, fallback_bound
    )
    with pytest.raises(AuditableRouterError, match="unverified artifacts"):
        replay_route_events(
            context=context,
            events=events,
            registry=registry,
            bounds=bounds,
            verified_artifact_ids=verified - {"causal-certificate"},
            require_terminal=False,
        )

    bad_selection = TransitionEvidence(
        context.context_id,
        ROUTE_SELECTION,
        SELECT_FALLBACK_INCOMPARABLE,
        _refs(
            comparison_profile=profile.profile_id,
            fallback_upper_bound=fallback_bound.bound_id,
            local_upper_bound=local_bound.bound_id,
        ),
        _work(registry, context.context_id, ROUTE_SELECTION, "transaction-1"),
        transaction_id="transaction-1",
        local_bound_id=local_bound.bound_id,
        fallback_bound_id=fallback_bound.bound_id,
    )
    with pytest.raises(AuditableRouterError, match="disagrees with exact comparison"):
        append_route_event(
            context=context,
            events=events[:-1],
            evidence=bad_selection,
            registry=registry,
            bounds=bounds,
            verified_artifact_ids=verified,
        )

    too_large = ComparisonVector(
        profile.profile_id,
        context.context_id,
        LOCAL_ATTEMPT,
        (("resource.bytes", 11), ("resource.operations", 1)),
    )
    verified.update({"local-result", "post-audit-pass", "local-actual-work"})
    over_cap = _evidence(
        registry,
        context,
        LOCAL_RESULT,
        CERTIFIED,
        _refs(
            actual_work="local-actual-work",
            local_result="local-result",
            post_audit_certificate="post-audit-pass",
        ),
        transaction_id="transaction-1",
        actual=too_large,
    )
    with pytest.raises(AuditableRouterError, match="exceeds selected upper bound"):
        append_route_event(
            context=context,
            events=events,
            evidence=over_cap,
            registry=registry,
            bounds=bounds,
            verified_artifact_ids=verified,
        )


def test_direct_fallback_cap_exhaustion_is_terminal_noncertificate() -> None:
    registry, profile, context, _, fallback_bound = _comparison_fixture()
    bounds = {fallback_bound.bound_id: fallback_bound}
    verified = {
        "integrity-ok",
        "compatibility-ok",
        "cache-check",
        "abstract-audit",
        "failed-proof",
        "threshold-1",
        "no-cover",
        profile.profile_id,
        fallback_bound.bound_id,
        "fallback-cap",
        "fallback-result",
        "fallback-actual-work",
    }
    evidence = [
        _evidence(registry, context, INTEGRITY, PASS, _refs(integrity_attestation="integrity-ok")),
        _evidence(registry, context, COMPATIBILITY, MATCH, _refs(compatibility_attestation="compatibility-ok")),
        _evidence(registry, context, CACHE_PROOF, MISS, _refs(cache_proof_check="cache-check")),
        _evidence(
            registry,
            context,
            ABSTRACT_AUDIT,
            FAIL,
            _refs(
                abstract_audit="abstract-audit",
                failed_proof_graph="failed-proof",
                threshold_profile="threshold-1",
            ),
        ),
        _evidence(
            registry,
            context,
            CAUSAL_SEARCH,
            NO_SOUND_COVER,
            _refs(causal_exhaustion_attestation="no-cover"),
            transaction_id="transaction-1",
        ),
    ]
    events: list[RouteTraceEvent] = []
    for item in evidence:
        events.append(
            append_route_event(
                context=context,
                events=events,
                evidence=item,
                registry=registry,
                bounds=bounds,
                verified_artifact_ids=verified,
            )
        )
    selection = make_route_selection_evidence(
        context=context,
        work_delta=_work(registry, context.context_id, ROUTE_SELECTION, "transaction-1"),
        fallback_bound=fallback_bound,
        local_bound=None,
        transaction_id="transaction-1",
    )
    events.append(
        append_route_event(
            context=context,
            events=events,
            evidence=selection,
            registry=registry,
            bounds=bounds,
            verified_artifact_ids=verified,
        )
    )
    actual = ComparisonVector(
        profile.profile_id,
        context.context_id,
        DIRECT_FALLBACK,
        (("resource.bytes", 20), ("resource.operations", 2)),
    )
    capped = _evidence(
        registry,
        context,
        FALLBACK_RESULT,
        INCOMPLETE_DUE_TO_CAP,
        _refs(
            actual_work="fallback-actual-work",
            fallback_cap_attestation="fallback-cap",
            fallback_result="fallback-result",
        ),
        transaction_id="transaction-1",
        actual=actual,
    )
    events.append(
        append_route_event(
            context=context,
            events=events,
            evidence=capped,
            registry=registry,
            bounds=bounds,
            verified_artifact_ids=verified,
        )
    )
    envelope = build_route_envelope(
        context=context,
        events=events,
        registry=registry,
        bounds=bounds,
        verified_artifact_ids=verified,
        complete=True,
    )
    assert envelope.final_state == FALLBACK_CAP_EXHAUSTED_ATTEMPT_TERMINAL


@pytest.fixture(scope="module")
def phase3b_accounting_source(tmp_path_factory: pytest.TempPathFactory) -> dict:
    bundle = tmp_path_factory.mktemp("phase3e-strict-phase3b") / "bundle"
    run_phase3b(bundle)
    return json.loads(
        (bundle / "accounting/work_counters.json").read_text(encoding="utf-8")
    )


@pytest.mark.parametrize("attack", ("missing_scalar", "bool_alias", "float_total", "missing_build", "wrong_n"))
def test_strict_legacy_boundary_rejects_python_equality_and_shape_attacks(
    phase3b_accounting_source: dict, attack: str
) -> None:
    document = copy.deepcopy(phase3b_accounting_source)
    if attack == "missing_scalar":
        document.pop("scalar_break_even")
    elif attack == "bool_alias":
        document["query"][0]["full_fallback_candidate_count"] = False
    elif attack == "float_total":
        document["reconciliation"]["query_occurrence_count"] = 11.0
    elif attack == "missing_build":
        document["build"]["g2048"].pop("covered_ground_states")
    elif attack == "wrong_n":
        document["query"].pop()
    with pytest.raises(CounterValidationError):
        legacy_phase3b_projection(document)
