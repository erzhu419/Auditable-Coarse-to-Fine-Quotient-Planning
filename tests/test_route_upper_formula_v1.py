from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp.accounting_v1 import (
    KERNEL_TRANSITION_CALLS,
    NONKERNEL_COMPUTE_EVENTS,
    SHARED_AXES,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.route_upper_formula_v1 import (
    AffineLeafUpperTermV1,
    FORMULA_REPLAY_ONLY,
    LocalCapImpossible,
    RouteUpperDerivationProofV1,
    RouteUpperFormulaV1,
    RouteUpperFormulaV1Error,
    derive_route_upper_v1,
    official_route_upper_formula_v1,
    verify_route_upper_derivation_v1,
)
from acfqp.phase3e_fallback_v1 import GroundFallbackCapProfileV1
from acfqp.routing_v1 import (
    CardinalityEvidenceV1,
    CausalEvidenceV1,
    CausalOutcome,
    DecisionPointV1,
    FrontierSnapshotV1,
    RouteCapProfileV1,
    RouteDecisionContextV1,
    RouteKind,
    RouteUpperBoundEnvelopeV1,
    TransactionV1,
    TypedNotApplicable,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _world():
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    cap = RouteCapProfileV1()
    context = RouteDecisionContextV1(
        _id("preregistration"),
        _id("protocol"),
        profile.comparison_profile_id,
        registry.registry_id,
        _id("structural"),
        _id("query"),
        _id("selected-plan"),
        _id("threshold"),
        _id("build-epoch"),
        _id("logical-occurrence"),
        _id("route-attempt"),
    )
    frontier = FrontierSnapshotV1(
        context.route_decision_context_id, 1, (_id("failed-obligation"),)
    )
    causal = CausalEvidenceV1(
        frontier.frontier_snapshot_id,
        CausalOutcome.FOUND,
        True,
        None,
        3,
        cap.route_cap_profile_id,
        (_id("failed-obligation"),),
    )
    decision = DecisionPointV1(
        context.route_decision_context_id,
        1,
        frontier.frontier_snapshot_id,
        causal.causal_evidence_id,
        _id("common-prefix-work"),
    )
    transaction = TransactionV1(
        context.logical_occurrence_id,
        context.route_attempt_id,
        decision.decision_point_id,
        1,
        frontier.frontier_snapshot_id,
        cap.route_cap_profile_id,
    )
    return registry, profile, cap, context, frontier, causal, decision, transaction


def _fallback_cap() -> GroundFallbackCapProfileV1:
    return GroundFallbackCapProfileV1(
        max_states_expanded=100,
        max_actions_evaluated=200,
        max_ground_steps=200,
        max_outcome_rows=800,
        max_bellman_backups=10_000,
        max_composed_candidates=10_000,
        max_cap_checks=20_000,
        max_positive_outcomes_per_step=4,
    )


def _cardinality(
    route: RouteKind,
    *,
    overrides: dict[str, int] | None = None,
    world=None,
):
    world = world or _world()
    registry, profile, local_cap, context, frontier, *_ = world
    cap = local_cap if route is RouteKind.LOCAL_ATTEMPT else _fallback_cap()
    formula = official_route_upper_formula_v1(
        route, registry=registry, profile=profile, cap_profile=cap
    )
    counts = {name: 0 for name in formula.required_count_names}
    counts.update(overrides or {})
    cardinality = CardinalityEvidenceV1(
        context.route_decision_context_id,
        route,
        cap.route_cap_profile_id,
        (
            frontier.frontier_snapshot_id
            if route is RouteKind.LOCAL_ATTEMPT
            else TypedNotApplicable("fallback cardinality is attempt-scoped")
        ),
        tuple(sorted(counts.items())),
        (_id(f"{route.value}-cardinality-source"),),
    )
    return formula, cardinality


def _derive_local(*, overrides: dict[str, int] | None = None, world=None):
    world = world or _world()
    registry, profile, cap, context, _, causal, decision, transaction = world
    formula, cardinality = _cardinality(
        RouteKind.LOCAL_ATTEMPT, overrides=overrides, world=world
    )
    envelope, proof = derive_route_upper_v1(
        context=context,
        decision_point=decision,
        cardinality=cardinality,
        cap_profile=cap,
        registry=registry,
        profile=profile,
        formula=formula,
        transaction=transaction,
        causal=causal,
    )
    return world, formula, cardinality, envelope, proof


def _derive_fallback(*, overrides: dict[str, int] | None = None, world=None):
    world = world or _world()
    registry, profile, _, context, _, _, decision, _ = world
    cap = _fallback_cap()
    formula, cardinality = _cardinality(
        RouteKind.DIRECT_FALLBACK, overrides=overrides, world=world
    )
    envelope, proof = derive_route_upper_v1(
        context=context,
        decision_point=decision,
        cardinality=cardinality,
        cap_profile=cap,
        registry=registry,
        profile=profile,
        formula=formula,
    )
    return world, formula, cardinality, envelope, proof


def test_official_formulas_cover_every_operational_leaf_exactly_once() -> None:
    registry, profile, cap, *_ = _world()
    expected = tuple(leaf.path for leaf in registry.operational_leaves)
    for route in RouteKind:
        route_cap = cap if route is RouteKind.LOCAL_ATTEMPT else _fallback_cap()
        formula = official_route_upper_formula_v1(
            route, registry=registry, profile=profile, cap_profile=route_cap
        )
        assert tuple(term.target_leaf for term in formula.terms) == expected
        assert len(formula.terms) == 34
        assert len(set(term.source_count for term in formula.terms)) == 34
        assert RouteUpperFormulaV1.from_dict(formula.to_dict()) == formula
    local = official_route_upper_formula_v1(
        RouteKind.LOCAL_ATTEMPT,
        registry=registry,
        profile=profile,
        cap_profile=cap,
    )
    fallback = official_route_upper_formula_v1(
        RouteKind.DIRECT_FALLBACK,
        registry=registry,
        profile=profile,
        cap_profile=_fallback_cap(),
    )
    assert len(local.structural_guards) == 6
    assert fallback.structural_guards == ()
    assert local.formula_id != fallback.formula_id


def test_local_derivation_uses_hard_cap_min_then_official_eight_axis_projection() -> None:
    world, formula, cardinality, envelope, proof = _derive_local(
        overrides={
            "local.causal_candidate_evaluations": 100,
            "local.materialization_ground_steps": 100,
            "local.materialization_outcome_rows": 80,
            "local.postaudit_ground_steps": 7,
            "control.cap_checks": 2,
            "process.launches": 1,
            "io.read_bytes": 20,
            "io.mounted_bytes_peak": 40,
            "memory.working_bytes_peak": 30,
        }
    )
    leaves = dict(proof.leaf_upper_bounds)
    assert leaves["local.causal_candidate_evaluations"] == 32
    assert leaves["local.materialization_ground_steps"] == 16
    assert leaves["local.materialization_outcome_rows"] == 64
    assert dict(envelope.upper_bounds)[KERNEL_TRANSITION_CALLS] == 23
    assert dict(envelope.upper_bounds)[NONKERNEL_COMPUTE_EVENTS] == 98
    assert tuple(axis for axis, _ in envelope.upper_bounds) == SHARED_AXES
    assert proof.comparison_upper_bounds == envelope.upper_bounds
    assert proof.proof_scope == FORMULA_REPLAY_ONLY
    assert proof.authorizes_route_selection is False
    assert envelope.formula_id == formula.formula_id
    assert envelope.cardinality_evidence_id == cardinality.cardinality_evidence_id
    assert RouteUpperBoundEnvelopeV1.from_dict(envelope.to_dict()) == envelope
    assert RouteUpperDerivationProofV1.from_dict(proof.to_dict()) == proof

    registry, profile, cap, context, _, causal, decision, transaction = world
    verify_route_upper_derivation_v1(
        envelope,
        proof,
        context=context,
        decision_point=decision,
        cardinality=cardinality,
        cap_profile=cap,
        registry=registry,
        profile=profile,
        formula=formula,
        transaction=transaction,
        causal=causal,
    )


def test_fallback_derivation_has_explicit_typed_local_nulls_and_native_zeros() -> None:
    _, formula, _, envelope, proof = _derive_fallback(
        overrides={
            "fallback.ground_steps": 11,
            "fallback.actions_evaluated": 9,
            "fallback.bellman_backups": 5,
            "process.launches": 1,
        }
    )
    assert isinstance(envelope.transaction_id, TypedNotApplicable)
    assert isinstance(envelope.frontier_snapshot_id, TypedNotApplicable)
    assert isinstance(proof.causal_evidence_id, TypedNotApplicable)
    assert dict(envelope.upper_bounds)[KERNEL_TRANSITION_CALLS] == 11
    assert dict(envelope.upper_bounds)[NONKERNEL_COMPUTE_EVENTS] == 14
    assert all(
        value == 0
        for path, value in proof.leaf_upper_bounds
        if path.startswith("local.")
    )
    assert envelope.formula_id == formula.formula_id


@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_missing_or_extra_cardinality_input_fails_closed(mutation: str) -> None:
    world = _world()
    registry, profile, cap, context, _, causal, decision, transaction = world
    formula, good = _cardinality(RouteKind.LOCAL_ATTEMPT, world=world)
    counts = dict(good.counts)
    if mutation == "missing":
        counts.pop(next(iter(counts)))
    else:
        counts["unregistered.extra_count"] = 1
    bad = replace(good, counts=tuple(sorted(counts.items())))
    with pytest.raises(RouteUpperFormulaV1Error, match="input mismatch"):
        derive_route_upper_v1(
            context=context,
            decision_point=decision,
            cardinality=bad,
            cap_profile=cap,
            registry=registry,
            profile=profile,
            formula=formula,
            transaction=transaction,
            causal=causal,
        )


@pytest.mark.parametrize(
    ("route", "forbidden_path"),
    [
        (RouteKind.LOCAL_ATTEMPT, "fallback.states_expanded"),
        (RouteKind.LOCAL_ATTEMPT, "rebuild.ground_steps"),
        (RouteKind.DIRECT_FALLBACK, "local.solver_subset_evaluations"),
        (RouteKind.DIRECT_FALLBACK, "rebuild.outcome_rows"),
    ],
)
def test_marginal_formula_rejects_rebuild_and_other_route_family(
    route: RouteKind, forbidden_path: str
) -> None:
    with pytest.raises(RouteUpperFormulaV1Error, match="forbidden nonzero"):
        if route is RouteKind.LOCAL_ATTEMPT:
            _derive_local(overrides={forbidden_path: 1})
        else:
            _derive_fallback(overrides={forbidden_path: 1})


@pytest.mark.parametrize("route", tuple(RouteKind))
def test_marginal_formula_accounts_for_postfreeze_common_verification_suffix(
    route: RouteKind,
) -> None:
    overrides = {
        "common.integrity_checks": 2,
        "common.protocol_checks": 3,
        "common.hash_invocations": 4,
    }
    if route is RouteKind.LOCAL_ATTEMPT:
        _, _, _, envelope, proof = _derive_local(overrides=overrides)
    else:
        _, _, _, envelope, proof = _derive_fallback(overrides=overrides)
    assert dict(proof.leaf_upper_bounds)["common.protocol_checks"] == 3
    assert dict(envelope.upper_bounds)[NONKERNEL_COMPUTE_EVENTS] == 9


def test_structural_cap_overrun_is_typed_local_cap_impossible() -> None:
    with pytest.raises(LocalCapImpossible) as captured:
        _derive_local(overrides={"structural.slice_cells": 65})
    assert captured.value.outcome is CausalOutcome.LOCAL_CAP_IMPOSSIBLE
    assert captured.value.cap_name == "max_slice_cells"
    assert captured.value.hard_cap == 64


def test_formula_profile_route_and_cap_identity_mismatches_fail_closed() -> None:
    world = _world()
    registry, profile, cap, context, _, causal, decision, transaction = world
    formula, cardinality = _cardinality(RouteKind.LOCAL_ATTEMPT, world=world)

    terms = list(formula.terms)
    terms[0] = replace(terms[0], coefficient=2)
    altered_formula = replace(formula, terms=tuple(terms))
    with pytest.raises(RouteUpperFormulaV1Error, match="differs from the official"):
        derive_route_upper_v1(
            context=context,
            decision_point=decision,
            cardinality=cardinality,
            cap_profile=cap,
            registry=registry,
            profile=profile,
            formula=altered_formula,
            transaction=transaction,
            causal=causal,
        )

    stale_formula = replace(formula, route_cap_profile_id=_id("stale-cap"))
    with pytest.raises(RouteUpperFormulaV1Error, match="differs from the official"):
        derive_route_upper_v1(
            context=context,
            decision_point=decision,
            cardinality=cardinality,
            cap_profile=cap,
            registry=registry,
            profile=profile,
            formula=stale_formula,
            transaction=transaction,
            causal=causal,
        )

    fallback_formula = official_route_upper_formula_v1(
        RouteKind.DIRECT_FALLBACK,
        registry=registry,
        profile=profile,
        cap_profile=_fallback_cap(),
    )
    with pytest.raises(RouteUpperFormulaV1Error, match="route mismatch"):
        derive_route_upper_v1(
            context=context,
            decision_point=decision,
            cardinality=cardinality,
            cap_profile=_fallback_cap(),
            registry=registry,
            profile=profile,
            formula=fallback_formula,
        )


def test_stale_decision_transaction_and_causal_bindings_fail_closed() -> None:
    world = _world()
    registry, profile, cap, context, frontier, causal, decision, transaction = world
    formula, cardinality = _cardinality(RouteKind.LOCAL_ATTEMPT, world=world)
    stale_transaction = TransactionV1(
        context.logical_occurrence_id,
        context.route_attempt_id,
        _id("stale-decision"),
        1,
        frontier.frontier_snapshot_id,
        cap.route_cap_profile_id,
    )
    with pytest.raises(RouteUpperFormulaV1Error, match="decision-point mismatch"):
        derive_route_upper_v1(
            context=context,
            decision_point=decision,
            cardinality=cardinality,
            cap_profile=cap,
            registry=registry,
            profile=profile,
            formula=formula,
            transaction=stale_transaction,
            causal=causal,
        )

    stale_causal = CausalEvidenceV1(
        _id("stale-frontier"),
        CausalOutcome.FOUND,
        True,
        None,
        1,
        cap.route_cap_profile_id,
        (_id("failed-obligation"),),
    )
    with pytest.raises(RouteUpperFormulaV1Error, match="causal evidence mismatch"):
        derive_route_upper_v1(
            context=context,
            decision_point=decision,
            cardinality=cardinality,
            cap_profile=cap,
            registry=registry,
            profile=profile,
            formula=formula,
            transaction=transaction,
            causal=stale_causal,
        )


def test_hand_filled_upper_or_proof_cannot_replace_exact_derivation() -> None:
    world, formula, cardinality, envelope, proof = _derive_local()
    registry, profile, cap, context, _, causal, decision, transaction = world
    changed_bounds = tuple(
        (axis, value + (1 if axis == KERNEL_TRANSITION_CALLS else 0))
        for axis, value in envelope.upper_bounds
    )
    forged_envelope = replace(envelope, upper_bounds=changed_bounds)
    with pytest.raises(RouteUpperFormulaV1Error, match="does not recompute"):
        verify_route_upper_derivation_v1(
            forged_envelope,
            proof,
            context=context,
            decision_point=decision,
            cardinality=cardinality,
            cap_profile=cap,
            registry=registry,
            profile=profile,
            formula=formula,
            transaction=transaction,
            causal=causal,
        )

    changed_leaves = list(proof.leaf_upper_bounds)
    path, value = changed_leaves[0]
    changed_leaves[0] = (path, value + 1)
    forged_proof = replace(proof, leaf_upper_bounds=tuple(changed_leaves))
    with pytest.raises(RouteUpperFormulaV1Error, match="does not replay"):
        verify_route_upper_derivation_v1(
            envelope,
            forged_proof,
            context=context,
            decision_point=decision,
            cardinality=cardinality,
            cap_profile=cap,
            registry=registry,
            profile=profile,
            formula=formula,
            transaction=transaction,
            causal=causal,
        )


def test_formula_roundtrip_rejects_extra_field_and_changed_id() -> None:
    formula, _ = _cardinality(RouteKind.DIRECT_FALLBACK)
    extra = formula.to_dict()
    extra["legacy_scalar"] = 0
    with pytest.raises(RouteUpperFormulaV1Error, match="field set mismatch"):
        RouteUpperFormulaV1.from_dict(extra)
    changed = formula.to_dict()
    changed["formula_id"] = _id("forged")
    with pytest.raises(RouteUpperFormulaV1Error, match="content ID mismatch"):
        RouteUpperFormulaV1.from_dict(changed)
