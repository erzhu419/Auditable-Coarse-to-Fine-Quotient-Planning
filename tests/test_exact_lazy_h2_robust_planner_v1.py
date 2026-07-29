from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import random

import pytest

import acfqp.exact_lazy_h2_robust_planner_v1 as lazy
import acfqp.partial_support_robust_planner_v1 as robust
import acfqp.transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import canonical_json_bytes


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _masses(
    *items: tuple[str, Fraction, Fraction],
) -> tuple[robust.IntervalDestinationMassV1, ...]:
    return tuple(
        sorted(
            (
                robust.IntervalDestinationMassV1(
                    destination_id,
                    lower,
                    upper,
                )
                for destination_id, lower, upper in items
            ),
            key=lambda item: item.destination_id,
        )
    )


def _context_shaped_model(
    context_key: str,
    child_count: int,
    *,
    partial_other: bool = False,
) -> tuple[
    robust.PartialSupportIntervalModelV1,
    robust.RobustThresholdProfileV1,
]:
    """Small deterministic H2 model bound to a registered graph context.

    These fixtures exercise the exact planner with the W5/K6-family public
    identities while keeping exhaustive cross-validation intentionally small.
    """

    context = observer.public_context_by_key_v1(context_key)
    root_state = _id(f"{context_key}:lazy-root")
    root_cell = _id(f"{context_key}:lazy-root-cell")
    child_cell = _id(f"{context_key}:lazy-child-cell")
    root_semantic = _id(f"{context_key}:lazy-root-semantic")
    child_semantics = (
        _id(f"{context_key}:lazy-child-semantic:0"),
        _id(f"{context_key}:lazy-child-semantic:1"),
    )
    other = _id(f"{context_key}:lazy-other")
    success = _id(f"{context_key}:lazy-success")
    failure = _id(f"{context_key}:lazy-failure")
    child_states = tuple(
        sorted(
            _id(f"{context_key}:lazy-child:{index}")
            for index in range(child_count)
        )
    )
    root_actions = tuple(
        sorted(
            (
                robust.CatalogueActionV1(
                    _id(f"{context_key}:lazy-root-action:{index}"),
                    root_semantic,
                )
                for index in range(2)
            ),
            key=lambda item: item.action_id,
        )
    )
    child_actions = {
        state_id: tuple(
            sorted(
                (
                    robust.CatalogueActionV1(
                        _id(
                            f"{context_key}:lazy-child-action:"
                            f"{state_id}:{action_index}"
                        ),
                        child_semantics[action_index],
                    )
                    for action_index in range(2)
                ),
                key=lambda item: item.action_id,
            )
        )
        for state_id in child_states
    }
    catalogues = (
        robust.StateActionCatalogueV1(root_state, root_cell, root_actions),
        *(
            robust.StateActionCatalogueV1(
                state_id,
                child_cell,
                child_actions[state_id],
            )
            for state_id in child_states
        ),
    )
    active = tuple(
        robust.RegisteredDestinationV1(
            _id(f"{context_key}:lazy-active:{state_id}"),
            robust.DestinationCategory.ACTIVE_STATE,
            state_id,
        )
        for state_id in child_states
    )
    destinations = (
        *active,
        robust.RegisteredDestinationV1(
            success,
            robust.DestinationCategory.SUCCESS_TERMINAL,
        ),
        robust.RegisteredDestinationV1(
            failure,
            robust.DestinationCategory.FAILURE,
        ),
        robust.RegisteredDestinationV1(
            other,
            robust.DestinationCategory.OTHER,
        ),
    )
    if partial_other:
        child_lower = Fraction(9, 10 * child_count)
        child_uppers = (
            child_lower + Fraction(1, 10),
            *(child_lower for _ in range(child_count - 1)),
        )
        other_upper = Fraction(1, 10)
    else:
        child_lower = Fraction(1, child_count)
        child_uppers = tuple(child_lower for _ in range(child_count))
        other_upper = Fraction(0)

    rows: list[robust.IntervalSimplexRowV1] = []
    for root_index, action in enumerate(root_actions):
        rows.append(
            robust.IntervalSimplexRowV1(
                root_state,
                2,
                action.action_id,
                Fraction(1, 64),
                Fraction(1, 64),
                other,
                _masses(
                    *(
                        (
                            destination.destination_id,
                            child_lower,
                            child_uppers[index],
                        )
                        for index, destination in enumerate(active)
                    ),
                    (other, Fraction(0), other_upper),
                ),
            )
        )
    for state_index, state_id in enumerate(child_states):
        for action_index, action in enumerate(child_actions[state_id]):
            # One action weakly dominates the other in every continuation
            # state, which gives branch-and-bound a safe pruning control.
            high = action.action_coordinate_key == child_semantics[1]
            reward = Fraction(2 if high else 1, 64)
            failure_mass = Fraction(0 if high else 1, 100)
            rows.append(
                robust.IntervalSimplexRowV1(
                    state_id,
                    1,
                    action.action_id,
                    reward,
                    reward,
                    other,
                    _masses(
                        (
                            success,
                            Fraction(1) - failure_mass,
                            Fraction(1) - failure_mass,
                        ),
                        (failure, failure_mass, failure_mass),
                        (other, Fraction(0), Fraction(0)),
                    ),
                )
            )
    concretizers = (
        robust.DistinctActionConcretizerEntryV1(
            root_cell,
            root_state,
            root_semantic,
            tuple(action.action_id for action in root_actions),
        ),
        *(
            robust.DistinctActionConcretizerEntryV1(
                child_cell,
                state_id,
                action.action_coordinate_key,
                (action.action_id,),
            )
            for state_id in child_states
            for action in child_actions[state_id]
        ),
    )
    return (
        robust.build_partial_support_model_v1(
            context_id=context.context_id,
            root_state_id=root_state,
            catalogues=catalogues,
            destinations=destinations,
            rows=rows,
            concretizer_entries=concretizers,
        ),
        robust.RobustThresholdProfileV1(
            context.context_id,
            context.risk_tolerance,
            context.reward_ceiling,
        ),
    )


@pytest.mark.parametrize(
    ("context_key", "child_count"),
    (
        ("opaque_graph_w5_v0", 3),
        ("opaque_graph_k6_v0", 4),
        ("opaque_graph_k6_minus_edge_v0", 5),
    ),
)
@pytest.mark.parametrize(
    "solver_kind",
    (
        robust.RobustSolverKind.GROUND_DIRECT,
        robust.RobustSolverKind.QUOTIENT,
    ),
)
def test_exact_lazy_audit_is_byte_identical_to_legacy_on_graph_family(
    context_key: str,
    child_count: int,
    solver_kind: robust.RobustSolverKind,
) -> None:
    assert lazy.PROPOSED_CONTRACT_VERSION == "1.36.0"
    model, threshold = _context_shaped_model(context_key, child_count)
    legacy = (
        robust.solve_ground_direct_robust_h2_v1(model, threshold)
        if solver_kind is robust.RobustSolverKind.GROUND_DIRECT
        else robust.solve_quotient_robust_h2_v1(model, threshold)
    )

    result = lazy.solve_exact_lazy_robust_h2_v1(
        model,
        threshold,
        solver_kind,
    )

    assert result.status is lazy.ExactLazyH2SolveStatus.SOLVED
    assert result.audit == legacy
    assert result.audit is not None
    assert result.audit.audit_id == legacy.audit_id
    assert canonical_json_bytes(result.audit.to_document()) == (
        canonical_json_bytes(legacy.to_document())
    )
    assert result.trace is not None
    assert not result.trace.enters_robust_audit_payload
    assert result.trace.independent_prune_witness_verifier_implemented
    assert result.trace.original_proof.proof_id
    assert "trace" not in result.audit.to_document()


def test_failed_other_counterfactual_is_byte_identical() -> None:
    model, threshold = _context_shaped_model(
        "opaque_graph_w5_v0",
        3,
        partial_other=True,
    )
    legacy = robust.solve_ground_direct_robust_h2_v1(model, threshold)
    assert (
        legacy.counterfactual.status
        is robust.CounterfactualStatus.ZERO_OTHER_CERTIFIED
    )

    result = lazy.solve_exact_lazy_ground_direct_h2_v1(model, threshold)

    assert result.status is lazy.ExactLazyH2SolveStatus.SOLVED
    assert result.audit == legacy
    assert result.trace is not None
    assert result.trace.zero_other_counterfactual is not None


def test_deterministic_randomized_legacy_cross_validation() -> None:
    """Persist the development-time exactness sweep as a deterministic test."""

    for seed in range(48):
        generator = random.Random(seed)
        model, threshold = _context_shaped_model(
            "opaque_graph_w5_v0",
            4,
        )
        success = next(
            item.destination_id
            for item in model.destinations
            if item.category is robust.DestinationCategory.SUCCESS_TERMINAL
        )
        failure = next(
            item.destination_id
            for item in model.destinations
            if item.category is robust.DestinationCategory.FAILURE
        )
        other = model.other_destination.destination_id
        rows: list[robust.IntervalSimplexRowV1] = []
        for row in model.rows:
            if row.remaining_horizon == 1:
                failure_probability = Fraction(
                    generator.randrange(0, 8),
                    100,
                )
                reward = Fraction(generator.randrange(0, 3), 64)
                row = replace(
                    row,
                    reward_lower=reward,
                    reward_upper=reward,
                    masses=_masses(
                        (
                            success,
                            Fraction(1) - failure_probability,
                            Fraction(1) - failure_probability,
                        ),
                        (
                            failure,
                            failure_probability,
                            failure_probability,
                        ),
                        (other, Fraction(0), Fraction(0)),
                    ),
                )
            rows.append(row)
        randomized_model = robust.build_partial_support_model_v1(
            context_id=model.context_id,
            root_state_id=model.root_state_id,
            catalogues=model.catalogues,
            destinations=model.destinations,
            rows=rows,
            concretizer_entries=model.concretizer_entries,
        )

        for solver_kind in (
            robust.RobustSolverKind.GROUND_DIRECT,
            robust.RobustSolverKind.QUOTIENT,
        ):
            legacy = (
                robust.solve_ground_direct_robust_h2_v1(
                    randomized_model,
                    threshold,
                )
                if solver_kind is robust.RobustSolverKind.GROUND_DIRECT
                else robust.solve_quotient_robust_h2_v1(
                    randomized_model,
                    threshold,
                )
            )
            result = lazy.solve_exact_lazy_robust_h2_v1(
                randomized_model,
                threshold,
                solver_kind,
            )

            assert result.status is lazy.ExactLazyH2SolveStatus.SOLVED, seed
            assert result.audit == legacy, (seed, solver_kind)
            assert result.audit is not None
            assert result.audit.audit_id == legacy.audit_id
            assert canonical_json_bytes(result.audit.to_document()) == (
                canonical_json_bytes(legacy.to_document())
            )


def test_root_conditioning_uses_lexicographic_defaults_for_irrelevant_units() -> None:
    model, threshold = _context_shaped_model(
        "opaque_graph_w5_v0",
        4,
    )
    active = tuple(
        item
        for item in model.destinations
        if item.category is robust.DestinationCategory.ACTIVE_STATE
    )
    root_rows = tuple(
        item for item in model.rows if item.remaining_horizon == 2
    )
    rewritten: list[robust.IntervalSimplexRowV1] = []
    for index, row in enumerate(root_rows):
        selected = active[index * 2 : index * 2 + 2]
        rewritten.append(
            replace(
                row,
                masses=_masses(
                    *(
                        (
                            destination.destination_id,
                            Fraction(1, 2),
                            Fraction(1, 2),
                        )
                        for destination in selected
                    ),
                    (
                        model.other_destination.destination_id,
                        Fraction(0),
                        Fraction(0),
                    ),
                ),
            )
        )
    conditioned = robust.build_partial_support_model_v1(
        context_id=model.context_id,
        root_state_id=model.root_state_id,
        catalogues=model.catalogues,
        destinations=model.destinations,
        rows=(
            *rewritten,
            *(item for item in model.rows if item.remaining_horizon == 1),
        ),
        concretizer_entries=model.concretizer_entries,
    )
    legacy = robust.solve_ground_direct_robust_h2_v1(
        conditioned,
        threshold,
    )

    result = lazy.solve_exact_lazy_ground_direct_h2_v1(
        conditioned,
        threshold,
    )

    assert result.audit == legacy
    assert result.trace is not None
    assert result.trace.original.irrelevant_decision_units == 4


def test_legacy_cartesian_cap_rejects_but_exact_lazy_solver_succeeds() -> None:
    model, threshold = _context_shaped_model(
        "opaque_graph_k6_v0",
        17,
    )
    with pytest.raises(
        robust.PartialSupportRobustPlannerInvariantViolation,
        match="ground robust policy enumeration exceeds the frozen cap",
    ):
        robust.solve_ground_direct_robust_h2_v1(model, threshold)

    result = lazy.solve_exact_lazy_ground_direct_h2_v1(model, threshold)

    assert result.status is lazy.ExactLazyH2SolveStatus.SOLVED
    assert result.audit is not None
    assert result.audit.complete_reachable_policy
    assert len(result.audit.assignments) == 18
    assert result.trace is not None
    assert result.trace.original.complete_policies < 2 ** 17
    assert result.trace.original.pruned_branches > 0


def test_resource_exhaustion_is_typed_and_emits_no_approximate_audit() -> None:
    model, threshold = _context_shaped_model(
        "opaque_graph_w5_v0",
        3,
    )
    result = lazy.solve_exact_lazy_ground_direct_h2_v1(
        model,
        threshold,
        limits=lazy.ExactLazyH2ResourceLimitsV1(
            max_branch_nodes=1,
            max_complete_policies=10,
            max_root_bound_evaluations=10,
        ),
    )

    assert (
        result.status
        is lazy.ExactLazyH2SolveStatus.EXACT_DP_RESOURCE_EXHAUSTED
    )
    assert result.audit is None
    assert result.trace is None
    assert result.exhaustion is not None
    assert (
        result.exhaustion.code
        is lazy.ExactLazyH2ResourceCode.MAX_BRANCH_NODES
    )
    assert result.exhaustion.terminal_code == "EXACT_DP_RESOURCE_EXHAUSTED"
    assert not result.exhaustion.approximate_audit_emitted
