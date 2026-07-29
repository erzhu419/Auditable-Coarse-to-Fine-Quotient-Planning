from __future__ import annotations

from dataclasses import fields
from fractions import Fraction
import hashlib
import inspect
from itertools import combinations, product
from typing import Any

import pytest

from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_independent_exact_ground_evaluator_v1 as exact


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _unsafe_clone(value: Any, **changes: Any) -> Any:
    result = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(
            result,
            field.name,
            changes.get(field.name, getattr(value, field.name)),
        )
    return result


def _world(
    *,
    context: exact.DevelopmentExactGroundContextV1,
    root_ranks: tuple[int, ...],
    delta: Fraction,
):
    anchor = exact.DevelopmentExactGroundSemanticAnchorV1()
    law = exact.DevelopmentExactHiddenLawV1(
        context.context_id,
        context.rank_cap,
        (
            (1, Fraction(9, 10)),
            (2, Fraction(1, 10)),
        ),
    )
    query = exact.development_exact_ground_query_v1(
        context=context,
        root_ranks=root_ranks,
        risk_tolerance=delta,
    )
    terminal = exact.development_exact_ground_terminal_ref_v1(
        anchor=anchor,
        context=context,
        query=query,
        law=law,
        logical_occurrence_id=_id(
            f"{context.control_key}:{root_ranks}:{delta}"
        ),
    )
    result = exact.evaluate_development_independent_exact_ground_v1(
        anchor=anchor,
        context=context,
        query=query,
        law=law,
        terminal_ref=terminal,
    )
    return anchor, context, query, law, terminal, result


@pytest.fixture(scope="module")
def k4_feasible():
    return _world(
        context=exact.development_exact_ground_k4_context_v1(),
        root_ranks=(1, 1, 2, 0),
        delta=Fraction(1, 5),
    )


@pytest.fixture(scope="module")
def k4_infeasible():
    return _world(
        context=exact.development_exact_ground_k4_context_v1(),
        root_ranks=(1, 1, 2, 0),
        delta=Fraction(1, 10),
    )


@pytest.fixture(scope="module")
def k5_feasible():
    return _world(
        context=exact.development_exact_ground_k5_context_v1(),
        root_ranks=(1, 1, 2, 3, 0),
        delta=Fraction(0),
    )


def _golden_brute_force(
    vertex_count: int,
    root: tuple[int, ...],
    delta: Fraction,
    law: tuple[tuple[int, Fraction], ...],
) -> dict[str, Any]:
    """Separate test oracle: raw tuples/Fractions, no evaluator helpers."""

    edges = tuple(combinations(range(vertex_count), 2))
    row_keys: set[
        tuple[tuple[int, ...], int, tuple[int, int, int]]
    ] = set()
    transition_count_by_row: dict[
        tuple[tuple[int, ...], int, tuple[int, int, int]],
        int,
    ] = {}

    def legal(ranks):
        return tuple(
            sorted(
                (first, second, survivor)
                for first, second in edges
                if ranks[first] > 0 and ranks[first] == ranks[second]
                for survivor in (first, second)
            )
        )

    def row(ranks, horizon, action):
        key = (ranks, horizon, action)
        first, second, survivor = action
        source_rank = ranks[first]
        merged = list(ranks)
        merged[first] = 0
        merged[second] = 0
        merged[survivor] = min(source_rank + 1, 4)
        empty = tuple(i for i, rank in enumerate(merged) if rank == 0)
        probabilities = {}
        for position in empty:
            for spawn_rank, spawn_probability in law:
                successor = list(merged)
                successor[position] = spawn_rank
                successor = tuple(successor)
                failure = not legal(successor)
                terminal = failure or horizon == 1
                outcome = (successor, failure, terminal)
                probabilities[outcome] = probabilities.get(
                    outcome,
                    Fraction(0),
                ) + Fraction(1, len(empty)) * spawn_probability
        row_keys.add(key)
        transition_count_by_row[key] = len(probabilities)
        reward = Fraction(2 ** (source_rank + 1), 2 ** 5) / 2
        return tuple(
            (successor, failure, terminal, probability)
            for (
                successor,
                failure,
                terminal,
            ), probability in probabilities.items()
        ), reward

    policy_values = []
    for root_action in legal(root):
        root_outcomes, root_reward = row(root, 2, root_action)
        child_states = tuple(
            sorted(
                {
                    successor
                    for successor, _failure, terminal, _probability
                    in root_outcomes
                    if not terminal
                }
            )
        )
        child_actions = tuple(legal(state) for state in child_states)
        for assignment in product(*child_actions):
            child_rows = {}
            for state, action in zip(child_states, assignment):
                child_rows[state] = row(state, 1, action)
            reward = root_reward
            risk = Fraction(0)
            for state, failure, terminal, probability in root_outcomes:
                if failure:
                    risk += probability
                elif not terminal:
                    outcomes, child_reward = child_rows[state]
                    reward += probability * child_reward
                    risk += probability * sum(
                        (
                            child_probability
                            for (
                                _next,
                                child_failure,
                                _terminal,
                                child_probability,
                            ) in outcomes
                            if child_failure
                        ),
                        Fraction(0),
                    )
            policy_values.append((reward, risk))
    feasible = tuple(value for value in policy_values if value[1] <= delta)
    selected = (
        min(feasible, key=lambda value: (-value[0], value[1]))
        if feasible
        else None
    )
    return {
        "policy_count": len(policy_values),
        "feasible_count": len(feasible),
        "row_count": len(row_keys),
        "transition_count": sum(transition_count_by_row.values()),
        "minimum_risk": min(risk for _reward, risk in policy_values),
        "maximum_reward": max(reward for reward, _risk in policy_values),
        "optimal_reward": None if selected is None else selected[0],
        "optimal_risk": None if selected is None else selected[1],
    }


def test_feasible_and_infeasible_results_are_exact_and_distinct(
    k4_feasible,
    k4_infeasible,
) -> None:
    feasible = k4_feasible[-1]
    infeasible = k4_infeasible[-1]
    assert feasible.status is exact.ExactGroundEvaluationStatusV1.FEASIBLE_OPTIMUM
    assert feasible.optimal_expected_reward == Fraction(3, 16)
    assert feasible.optimal_failure_probability == Fraction(9, 50)
    assert infeasible.status is exact.ExactGroundEvaluationStatusV1.INFEASIBLE
    assert infeasible.selected_policy is None
    assert infeasible.optimal_expected_reward is None
    assert infeasible.minimum_failure_probability == Fraction(9, 50)
    assert feasible.result_id != infeasible.result_id


@pytest.mark.parametrize("fixture_name", ("k4_feasible", "k5_feasible"))
def test_independent_brute_force_golden(
    fixture_name,
    request: pytest.FixtureRequest,
) -> None:
    _anchor, context, query, law, _terminal, result = (
        request.getfixturevalue(fixture_name)
    )
    golden = _golden_brute_force(
        context.vertex_count,
        query.root_ranks,
        query.risk_tolerance,
        law.rank_probabilities,
    )
    assert len(result.policies) == golden["policy_count"]
    assert result.work.feasible_policies_enumerated == golden["feasible_count"]
    assert len(result.rows) == golden["row_count"]
    assert (
        result.work.exact_positive_transition_outcomes
        == golden["transition_count"]
    )
    assert result.minimum_failure_probability == golden["minimum_risk"]
    assert result.maximum_unconstrained_reward == golden["maximum_reward"]
    assert result.optimal_expected_reward == golden["optimal_reward"]
    assert result.optimal_failure_probability == golden["optimal_risk"]


def test_evaluation_work_never_enters_operational_or_sample_lanes(
    k4_feasible,
    k5_feasible,
) -> None:
    for result in (k4_feasible[-1], k5_feasible[-1]):
        work = result.work
        assert work.execution_lane == "STANDALONE_EVALUATION_ONLY"
        assert work.exact_row_evaluations == len(result.rows)
        assert work.deterministic_contingent_policies_enumerated == len(
            result.policies
        )
        assert work.operational_work_records_written == 0
        assert work.accepted_sample_draws == 0
        assert work.online_sample_endpoint_writes == 0
        assert work.source_prior_reads == 0
        assert work.production_model_builder_calls == 0
        assert work.production_planner_calls == 0
        assert work.production_policy_result_reads == 0
        assert result.operational_work_included is False
        assert result.sample_endpoint_mutated is False
        assert result.registered_result_claimed is False


def test_policy_ties_use_semantic_action_key_not_content_hash(
    k4_feasible,
) -> None:
    result = k4_feasible[-1]
    selected = result.selected_policy
    assert selected is not None
    tied = tuple(
        policy
        for policy in result.policies
        if policy.feasible
        and policy.expected_reward == selected.expected_reward
        and policy.failure_probability == selected.failure_probability
    )
    assert len(tied) > 1
    assert selected.semantic_policy_key == min(
        policy.semantic_policy_key for policy in tied
    )


def test_same_implementation_replay_is_explicitly_nonindependent(
    k4_feasible,
) -> None:
    anchor, context, query, law, terminal, result = k4_feasible
    verification = (
        exact.verify_development_exact_ground_same_implementation_replay_v1(
            anchor=anchor,
            context=context,
            query=query,
            law=law,
            terminal_ref=terminal,
            claimed=result,
        )
    )
    assert verification.valid
    assert verification.result_id == result.result_id
    assert verification.production_authority_called is False
    assert verification.same_implementation_deterministic_replay is True
    assert (
        verification.independent_verifier_implementation_claimed is False
    )
    assert verification.separate_brute_force_golden_required is True


def test_policy_and_result_transplants_are_rejected(
    k4_feasible,
    k4_infeasible,
    k5_feasible,
) -> None:
    anchor, context, query, law, terminal, result = k4_feasible
    foreign_policy = k5_feasible[-1].policies[0]
    forged_policies = tuple(
        sorted(
            (foreign_policy, *result.policies[1:]),
            key=lambda item: item.policy_id,
        )
    )
    forged = _unsafe_clone(result, policies=forged_policies)
    with pytest.raises(
        exact.V072IndependentExactGroundEvaluationViolation,
        match="transplanted|re-signed",
    ):
        exact.verify_development_exact_ground_same_implementation_replay_v1(
            anchor=anchor,
            context=context,
            query=query,
            law=law,
            terminal_ref=terminal,
            claimed=forged,
        )

    with pytest.raises(
        exact.V072IndependentExactGroundEvaluationViolation,
        match="transplanted|re-signed",
    ):
        exact.verify_development_exact_ground_same_implementation_replay_v1(
            anchor=k4_infeasible[0],
            context=k4_infeasible[1],
            query=k4_infeasible[2],
            law=k4_infeasible[3],
            terminal_ref=k4_infeasible[4],
            claimed=result,
        )


def test_re_signed_summary_attack_is_rejected(k4_feasible) -> None:
    anchor, context, query, law, terminal, result = k4_feasible
    forged = _unsafe_clone(
        result,
        maximum_unconstrained_reward=(
            result.maximum_unconstrained_reward + Fraction(1, 10_000)
        ),
    )
    assert forged.result_id != result.result_id
    with pytest.raises(
        exact.V072IndependentExactGroundEvaluationViolation,
        match="transplanted|re-signed",
    ):
        exact.verify_development_exact_ground_same_implementation_replay_v1(
            anchor=anchor,
            context=context,
            query=query,
            law=law,
            terminal_ref=terminal,
            claimed=forged,
        )


def test_missing_terminal_wrong_law_context_and_duck_types_are_rejected(
    k4_feasible,
    k5_feasible,
) -> None:
    anchor, context, query, law, terminal, _result = k4_feasible
    with pytest.raises(
        exact.V072IndependentExactGroundEvaluationViolation,
        match="duck types",
    ):
        exact.evaluate_development_independent_exact_ground_v1(
            anchor=anchor,
            context=context,
            query=query,
            law=law,
            terminal_ref=None,
        )
    with pytest.raises(
        exact.V072IndependentExactGroundEvaluationViolation,
        match="stale",
    ):
        exact.evaluate_development_independent_exact_ground_v1(
            anchor=anchor,
            context=context,
            query=query,
            law=k5_feasible[3],
            terminal_ref=terminal,
        )
    with pytest.raises(
        exact.V072IndependentExactGroundEvaluationViolation,
        match="stale",
    ):
        exact.evaluate_development_independent_exact_ground_v1(
            anchor=anchor,
            context=k5_feasible[1],
            query=query,
            law=law,
            terminal_ref=terminal,
        )

    class DuckLaw:
        context_id = law.context_id
        rank_cap = law.rank_cap
        rank_probabilities = law.rank_probabilities
        law_id = law.law_id

    with pytest.raises(
        exact.V072IndependentExactGroundEvaluationViolation,
        match="duck types",
    ):
        exact.evaluate_development_independent_exact_ground_v1(
            anchor=anchor,
            context=context,
            query=query,
            law=DuckLaw(),
            terminal_ref=terminal,
        )


def test_registered_entry_is_hard_locked_before_any_evaluation_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def forbidden(*_args: object, **_kwargs: object) -> None:
        calls.append("EXACT_ATOM_ACCESS")
        raise AssertionError("pre-anchor evaluation access occurred")

    monkeypatch.setattr(
        observer,
        "evaluation_only_exact_atoms_v2",
        forbidden,
    )
    for nonanchor in (
        None,
        object(),
        exact.RegisteredExactGroundSemanticAnchorDraftV1(),
        observer.bind_target_execution_anchor_placeholder_v1(
            prereg.freeze_transfer_guided_acquisition_preregistration_v1(),
            remote_main_commit_sha="1" * 40,
            remote_main_containment_attestation_id=_id(
                "exact-evaluator-placeholder"
            ),
        ),
    ):
        with pytest.raises(
            exact.RegisteredIndependentExactGroundEvaluationLocked,
            match="V072RemoteMainAnchorV1",
        ):
            exact.evaluate_registered_independent_exact_ground_v1(
                anchor=nonanchor,
                context=object(),
                operational_terminal=object(),
                selected_policy=object(),
            )
    assert calls == []
    assert exact.REGISTERED_EVALUATION_ALLOWED is True
    assert (
        exact.REGISTERED_OPERATIONAL_TERMINAL_AUTHORITY_ENABLED is True
    )
    with pytest.raises(
        exact.RegisteredIndependentExactGroundEvaluationLocked,
        match=exact.REGISTERED_OPERATIONAL_TERMINAL_BLOCKER,
    ):
        exact.mint_registered_occurrence_operational_terminal_policy_v1(
            mint_authority=object(),  # type: ignore[arg-type]
        )


def test_registered_signature_accepts_no_caller_law_status_or_counts() -> None:
    signature = inspect.signature(
        exact.evaluate_registered_independent_exact_ground_v1
    )
    assert tuple(signature.parameters) == (
        "anchor",
        "context",
        "operational_terminal",
        "selected_policy",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    assert {
        "query",
        "law",
        "hidden_law_authority",
        "probabilities",
        "status",
        "counts",
        "value",
        "risk",
    }.isdisjoint(signature.parameters)


@pytest.mark.parametrize(
    "fixture_name",
    ("k4_feasible", "k4_infeasible", "k5_feasible"),
)
def test_generic_pareto_dp_is_positive_only_on_disjoint_development_laws(
    fixture_name: str,
    request: pytest.FixtureRequest,
) -> None:
    anchor, context, query, law, terminal, exhaustive = (
        request.getfixturevalue(fixture_name)
    )
    core = exact.evaluate_development_h2_generic_dp_control_v1(
        anchor=anchor,
        context=context,
        query=query,
        law=law,
        terminal_ref=terminal,
    )
    assert core.candidate_extensions > 0
    assert core.frontier_points_retained > 0
    if exhaustive.selected_policy is None:
        assert core.optimal_policy is None
    else:
        assert core.optimal_policy is not None
        assert (
            core.optimal_policy.expected_reward
            == exhaustive.optimal_expected_reward
        )
        assert (
            core.optimal_policy.failure_probability
            == exhaustive.optimal_failure_probability
        )
        assert core.optimal_policy.semantic_key == (
            exhaustive.selected_policy.semantic_policy_key
        )


def test_registered_adapter_names_only_the_evaluation_atom_authority() -> None:
    source = inspect.getsource(exact._evaluate_registered_exact_ground)
    assert "evaluation_only_exact_atoms_v2" in source
    assert "_environment_law" not in source
    assert "_HIDDEN_LAW_SPECS" not in source
    assert "rank_probabilities" not in source


def test_production_planners_builders_and_campaigns_are_not_called(
    k4_feasible,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from acfqp import exact_lazy_h2_robust_planner_v1 as lazy
    from acfqp import observation_support_graph_model_v1 as model
    from acfqp import partial_support_robust_planner_v1 as robust
    from acfqp import certificate_sensitive_greedy_acquisition_v1 as campaign

    def forbidden(*_args, **_kwargs):
        raise AssertionError("production authority was called")

    for module, names in (
        (
            lazy,
            (
                "solve_exact_lazy_robust_h2_v1",
                "solve_exact_lazy_ground_direct_h2_v1",
                "solve_exact_lazy_quotient_h2_v1",
            ),
        ),
        (
            robust,
            (
                "build_partial_support_model_v1",
                "solve_ground_direct_robust_h2_v1",
                "solve_quotient_robust_h2_v1",
            ),
        ),
        (model, ("build_observation_support_graph_models_v1",)),
        (
            campaign,
            (
                "run_certificate_sensitive_greedy_acquisition_v1",
                "run_certificate_sensitive_matched_campaign_v1",
            ),
        ),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)

    anchor, context, query, law, terminal, _result = k4_feasible
    replay = exact.evaluate_development_independent_exact_ground_v1(
        anchor=anchor,
        context=context,
        query=query,
        law=law,
        terminal_ref=terminal,
    )
    assert replay.work.production_model_builder_calls == 0
    assert replay.work.production_planner_calls == 0
    assert replay.work.source_prior_reads == 0


def test_all_fifteen_occurrence_identities_are_distinct_and_bound(
) -> None:
    occurrences = tuple(
        exact.RegisteredOccurrenceIdentityV1(
            _id("unopened-registered-anchor-identity"),
            context.context_id,
            context.context_key,
            arm,
            context_ordinal,
            arm_ordinal,
            context_ordinal * len(prereg.ARM_ORDER) + arm_ordinal,
        )
        for context_ordinal, context in enumerate(
            prereg.registered_heldout_public_contexts_v2()
        )
        for arm_ordinal, arm in enumerate(prereg.ARM_ORDER)
    )
    assert len(occurrences) == 15
    assert tuple(item.occurrence_ordinal for item in occurrences) == tuple(
        range(15)
    )
    assert len({item.occurrence_id for item in occurrences}) == 15
    assert all(
        item.to_document()["schedule_occurrence_count"] == 15
        and item.to_document()["replacement_allowed"] is False
        for item in occurrences
    )


def _fixed_kappa_generic_inventory():
    child_actions = (
        exact.GenericH2ChildActionV1((1, 2, 1), Fraction(2), Fraction(0)),
        exact.GenericH2ChildActionV1(
            (1, 2, 2), Fraction(0), Fraction(1, 5)
        ),
    )
    branch_first = exact.GenericH2ChildBranchV1(
        (2, 1, 0),
        Fraction(9, 10),
        child_actions,
    )
    branch_second = exact.GenericH2ChildBranchV1(
        (2, 1, 0),
        Fraction(1),
        child_actions,
    )
    return (
        exact.GenericH2RootActionV1(
            (0, 1, 0),
            Fraction(1),
            Fraction(1, 10),
            (branch_first,),
        ),
        exact.GenericH2RootActionV1(
            (0, 1, 1),
            Fraction(3),
            Fraction(0),
            (branch_second,),
        ),
    )


def test_fixed_kappa_is_evaluated_as_exact_mixture_not_one_action() -> None:
    roots = _fixed_kappa_generic_inventory()
    root_kappa = exact.GenericH2UniformKappaDecisionV1(
        "semantic-root",
        ((0, 1, 0), (0, 1, 1)),
        (Fraction(1, 2), Fraction(1, 2)),
    )
    child_kappa = exact.GenericH2UniformKappaDecisionV1(
        "semantic-child",
        ((1, 2, 1), (1, 2, 2)),
        (Fraction(1, 2), Fraction(1, 2)),
    )
    result = exact.evaluate_generic_h2_fixed_kappa_policy_v1(
        root_actions=roots,
        root_decision=root_kappa,
        child_decisions=(((2, 1, 0), child_kappa),),
    )
    representative = exact.evaluate_generic_h2_deterministic_policy_v1(
        root_actions=roots,
        root_action=(0, 1, 0),
        child_actions=(((2, 1, 0), (1, 2, 1)),),
    )
    assert result.expected_reward == Fraction(59, 20)
    assert result.failure_probability == Fraction(29, 200)
    assert (
        result.expected_reward,
        result.failure_probability,
    ) != (
        representative.expected_reward,
        representative.failure_probability,
    )
    deterministic_j0 = exact.solve_generic_h2_deterministic_core_v1(
        root_actions=roots,
        risk_tolerance=Fraction(1, 5),
    )
    assert deterministic_j0.optimal_policy is not None
    assert deterministic_j0.optimal_policy.expected_reward == Fraction(5)
    assert deterministic_j0.optimal_policy.root_action == (0, 1, 1)


@pytest.mark.parametrize(
    ("actions", "weights"),
    (
        (
            ((0, 1, 0), (0, 1, 0)),
            (Fraction(1, 2), Fraction(1, 2)),
        ),
        (
            ((0, 1, 0), (0, 1, 1)),
            (Fraction(3, 4), Fraction(1, 4)),
        ),
        (
            ((0, 1, 0), (0, 1, 1)),
            (Fraction(1, 2), Fraction(1, 3)),
        ),
    ),
)
def test_fixed_kappa_rejects_duplicate_support_or_wrong_weights(
    actions: tuple[tuple[int, int, int], ...],
    weights: tuple[Fraction, ...],
) -> None:
    with pytest.raises(
        exact.V072IndependentExactGroundEvaluationViolation,
        match="uniform Fraction",
    ):
        exact.GenericH2UniformKappaDecisionV1(
            "semantic-root",
            actions,
            weights,
        )


def test_fixed_kappa_requires_union_of_all_reachable_child_states() -> None:
    roots = _fixed_kappa_generic_inventory()
    root_kappa = exact.GenericH2UniformKappaDecisionV1(
        "semantic-root",
        ((0, 1, 0), (0, 1, 1)),
        (Fraction(1, 2), Fraction(1, 2)),
    )
    with pytest.raises(
        exact.V072IndependentExactGroundEvaluationViolation,
        match="reachable child-state union",
    ):
        exact.evaluate_generic_h2_fixed_kappa_policy_v1(
            root_actions=roots,
            root_decision=root_kappa,
            child_decisions=(),
        )


def test_partial_fixed_kappa_missing_state_is_exact_policy_abort() -> None:
    roots = _fixed_kappa_generic_inventory()
    root_kappa = exact.GenericH2UniformKappaDecisionV1(
        "semantic-root",
        ((0, 1, 0), (0, 1, 1)),
        (Fraction(1, 2), Fraction(1, 2)),
    )
    result = exact.evaluate_generic_h2_partial_fixed_kappa_policy_v1(
        root_actions=roots,
        root_decision=root_kappa,
        child_decisions=(),
        modeled_child_support_by_root=(
            ((0, 1, 0), ()),
            ((0, 1, 1), ()),
        ),
        globally_modeled_child_states=(),
    )
    assert result.expected_reward == Fraction(2)
    assert result.environment_failure_probability == Fraction(1, 20)
    assert result.policy_abort_failure_probability == Fraction(19, 20)
    assert result.failure_probability == 1
    assert tuple(
        (
            item.root_action,
            item.state_key,
            item.marginal_failure_probability,
        )
        for item in result.policy_abort_branches
    ) == (
        ((0, 1, 0), (2, 1, 0), Fraction(9, 20)),
        ((0, 1, 1), (2, 1, 0), Fraction(1, 2)),
    )
    assert result.missing_reachable_child_semantics == (
        exact.PARTIAL_SUPPORT_POLICY_ABORT_RULE
    )


def test_partial_fixed_kappa_abort_and_child_mixture_are_both_weighted() -> None:
    child_actions = (
        exact.GenericH2ChildActionV1(
            (1, 2, 1),
            Fraction(2),
            Fraction(0),
        ),
        exact.GenericH2ChildActionV1(
            (1, 2, 2),
            Fraction(0),
            Fraction(1, 5),
        ),
    )
    roots = (
        exact.GenericH2RootActionV1(
            (0, 1, 0),
            Fraction(1),
            Fraction(1, 10),
            (
                exact.GenericH2ChildBranchV1(
                    (2, 1, 0),
                    Fraction(9, 10),
                    child_actions,
                ),
            ),
        ),
        exact.GenericH2RootActionV1(
            (0, 1, 1),
            Fraction(3),
            Fraction(0),
            (
                exact.GenericH2ChildBranchV1(
                    (3, 1, 0),
                    Fraction(1),
                    child_actions,
                ),
            ),
        ),
    )
    root_kappa = exact.GenericH2UniformKappaDecisionV1(
        "semantic-root",
        ((0, 1, 0), (0, 1, 1)),
        (Fraction(1, 2), Fraction(1, 2)),
    )
    child_kappa = exact.GenericH2UniformKappaDecisionV1(
        "semantic-child",
        ((1, 2, 1), (1, 2, 2)),
        (Fraction(1, 2), Fraction(1, 2)),
    )
    result = exact.evaluate_generic_h2_partial_fixed_kappa_policy_v1(
        root_actions=roots,
        root_decision=root_kappa,
        child_decisions=(((2, 1, 0), child_kappa),),
        modeled_child_support_by_root=(
            ((0, 1, 0), ((2, 1, 0),)),
            ((0, 1, 1), ()),
        ),
        globally_modeled_child_states=((2, 1, 0),),
    )
    assert result.expected_reward == Fraction(49, 20)
    assert result.environment_failure_probability == Fraction(19, 200)
    assert result.policy_abort_failure_probability == Fraction(1, 2)
    assert result.failure_probability == Fraction(119, 200)
    assert len(result.policy_abort_branches) == 1
    assert result.policy_abort_branches[0].root_action == (0, 1, 1)
    assert result.policy_abort_branches[0].state_key == (3, 1, 0)
    assert (
        result.policy_abort_branches[0].marginal_failure_probability
        == Fraction(1, 2)
    )


def test_partial_fixed_kappa_rejects_wrong_or_extra_child_decision() -> None:
    roots = _fixed_kappa_generic_inventory()
    root_kappa = exact.GenericH2UniformKappaDecisionV1(
        "semantic-root",
        ((0, 1, 0), (0, 1, 1)),
        (Fraction(1, 2), Fraction(1, 2)),
    )
    child_kappa = exact.GenericH2UniformKappaDecisionV1(
        "semantic-child",
        ((1, 2, 1),),
        (Fraction(1),),
    )
    with pytest.raises(
        exact.V072IndependentExactGroundEvaluationViolation,
        match="global frozen model state registry",
    ):
        exact.evaluate_generic_h2_partial_fixed_kappa_policy_v1(
            root_actions=roots,
            root_decision=root_kappa,
            child_decisions=(((9, 9, 9), child_kappa),),
            modeled_child_support_by_root=(
                ((0, 1, 0), ()),
                ((0, 1, 1), ()),
            ),
            globally_modeled_child_states=(),
        )
    wrong_action = exact.GenericH2UniformKappaDecisionV1(
        "wrong-semantic-child",
        ((0, 2, 0),),
        (Fraction(1),),
    )
    with pytest.raises(
        exact.V072IndependentExactGroundEvaluationViolation,
        match="child support is outside exact inventory",
    ):
        exact.evaluate_generic_h2_partial_fixed_kappa_policy_v1(
            root_actions=roots,
            root_decision=root_kappa,
            child_decisions=(((2, 1, 0), wrong_action),),
            modeled_child_support_by_root=(
                ((0, 1, 0), ((2, 1, 0),)),
                ((0, 1, 1), ((2, 1, 0),)),
            ),
            globally_modeled_child_states=((2, 1, 0),),
        )


def test_complete_and_partial_fixed_kappa_helpers_agree_without_abort() -> None:
    roots = _fixed_kappa_generic_inventory()
    root_kappa = exact.GenericH2UniformKappaDecisionV1(
        "semantic-root",
        ((0, 1, 0), (0, 1, 1)),
        (Fraction(1, 2), Fraction(1, 2)),
    )
    child_kappa = exact.GenericH2UniformKappaDecisionV1(
        "semantic-child",
        ((1, 2, 1), (1, 2, 2)),
        (Fraction(1, 2), Fraction(1, 2)),
    )
    complete = exact.evaluate_generic_h2_fixed_kappa_policy_v1(
        root_actions=roots,
        root_decision=root_kappa,
        child_decisions=(((2, 1, 0), child_kappa),),
    )
    partial = exact.evaluate_generic_h2_partial_fixed_kappa_policy_v1(
        root_actions=roots,
        root_decision=root_kappa,
        child_decisions=(((2, 1, 0), child_kappa),),
        modeled_child_support_by_root=(
            ((0, 1, 0), ((2, 1, 0),)),
            ((0, 1, 1), ((2, 1, 0),)),
        ),
        globally_modeled_child_states=((2, 1, 0),),
    )
    assert partial.expected_reward == complete.expected_reward
    assert partial.failure_probability == complete.failure_probability
    assert partial.environment_failure_probability == (
        complete.failure_probability
    )
    assert partial.policy_abort_failure_probability == 0
    assert partial.policy_abort_branches == ()


def test_registered_policy_abort_branch_is_typed_and_exact() -> None:
    branch = exact.RegisteredPolicyAbortBranchWitnessV1(
        _id("abort-occurrence"),
        _id("abort-context"),
        _id("abort-ground-state"),
        (3, 1, 0),
        (0, 1, 1),
        Fraction(1, 2),
        Fraction(3, 5),
        Fraction(3, 10),
        _id("abort-modeled-support"),
        _id("abort-selected-row"),
        _id("abort-partition"),
        _id("abort-exact-root-row"),
        (_id("abort-exact-atom"),),
        _id("abort-global-other"),
        _id("abort-other-handler"),
    )
    document = branch.to_document()
    assert document["exact_child_state_id"] == _id("abort-ground-state")
    assert document["behavior"] == "ABSORBING_POLICY_ABORT_FAILURE"
    assert document["continuation_reward"] == {
        "numerator": 0,
        "denominator": 1,
    }
    assert document["marginal_failure_probability"] == {
        "numerator": 3,
        "denominator": 10,
    }
    assert len(document["branch_witness_id"]) == 64
    with pytest.raises(
        exact.V072IndependentExactGroundEvaluationViolation,
        match="policy-abort branch witness",
    ):
        exact.RegisteredPolicyAbortBranchWitnessV1(
            _id("abort-occurrence"),
            _id("abort-context"),
            _id("abort-ground-state"),
            (3, 1, 0),
            (0, 1, 1),
            Fraction(1, 2),
            Fraction(3, 5),
            Fraction(1, 10),
            _id("abort-modeled-support"),
            _id("abort-selected-row"),
            _id("abort-partition"),
            _id("abort-exact-root-row"),
            (_id("abort-exact-atom"),),
            _id("abort-global-other"),
            _id("abort-other-handler"),
        )


def test_exact_root_branch_partition_is_complete_disjoint_and_exact() -> None:
    atom_ids = tuple(_id(f"partition-atom:{index}") for index in range(3))
    partition = exact.ExactBranchPartitionWitnessV1(
        _id("partition-occurrence"),
        _id("partition-context"),
        (0, 1, 1),
        Fraction(1),
        _id("partition-support"),
        _id("partition-model-row"),
        _id("partition-exact-row"),
        tuple(sorted(atom_ids)),
        tuple(
            sorted(
                zip(
                    atom_ids,
                    (
                        Fraction(1, 5),
                        Fraction(1, 2),
                        Fraction(3, 10),
                    ),
                    strict=True,
                )
            )
        ),
        (atom_ids[0],),
        (atom_ids[1],),
        (atom_ids[2],),
        Fraction(1, 5),
        Fraction(1, 2),
        Fraction(3, 10),
    )
    document = partition.to_document()
    assert document["exact_root_row_id"] == _id("partition-exact-row")
    assert set(document["exact_atom_ids"]) == set(atom_ids)
    assert document["partition_categories"] == [
        "ENVIRONMENT_FAILURE",
        "MODELED_RECURSE",
        "POLICY_ABORT",
    ]
    with pytest.raises(
        exact.V074ModeledSupportExactLiftProtocolViolation,
        match="disjoint union",
    ):
        exact.ExactBranchPartitionWitnessV1(
            _id("partition-occurrence"),
            _id("partition-context"),
            (0, 1, 1),
            Fraction(1),
            _id("partition-support"),
            _id("partition-model-row"),
            _id("partition-exact-row"),
            tuple(sorted(atom_ids)),
            tuple(
                sorted(
                    zip(
                        atom_ids,
                        (
                            Fraction(1, 5),
                            Fraction(1, 2),
                            Fraction(3, 10),
                        ),
                        strict=True,
                    )
                )
            ),
            tuple(sorted((atom_ids[0], atom_ids[1]))),
            (atom_ids[1],),
            (atom_ids[2],),
            Fraction(7, 10),
            Fraction(1, 2),
            Fraction(3, 10),
        )


def test_registered_evaluator_routes_partial_support_through_abort_helper(
) -> None:
    source = inspect.getsource(exact._evaluate_registered_exact_ground)
    assert "evaluate_generic_h2_partial_fixed_kappa_policy_v1" in source
    assert "RegisteredPolicyAbortBranchWitnessV1" in source
    assert "ExactBranchPartitionWitnessV1" in source
    assert "exact_root_row_by_action" in source
    assert "does not cover the union of child states" not in source


def test_v074_result_domains_and_top_level_failure_decomposition_are_explicit(
) -> None:
    source = inspect.getsource(
        exact.RegisteredIndependentExactGroundEvaluationResultV1
    )
    assert "acfqp.v074_modeled_support" in source
    assert "selected_environment_failure_probability" in source
    assert "selected_policy_abort_failure_probability" in source
    assert "modeled_policy_support_authority_id" in source
    assert "operational_envelope_containment_pass" in source
    assert "operational_unrestricted_reward_upper" in source
    assert exact.DOMAIN_TAGS["v074_registered_result"].startswith(
        "acfqp:v074-"
    )
    assert exact.DOMAIN_TAGS["v074_policy_abort_branch"].startswith(
        "acfqp:v074-"
    )
    assert inspect.signature(
        exact.evaluate_registered_independent_exact_ground_v2
    ).parameters.keys() == {
        "anchor",
        "context",
        "operational_terminal",
        "selected_policy",
    }


def test_row_specific_support_aborts_despite_dormant_decision() -> None:
    roots = _fixed_kappa_generic_inventory()
    root_kappa = exact.GenericH2UniformKappaDecisionV1(
        "semantic-root",
        ((0, 1, 0), (0, 1, 1)),
        (Fraction(1, 2), Fraction(1, 2)),
    )
    child_kappa = exact.GenericH2UniformKappaDecisionV1(
        "semantic-child",
        ((1, 2, 1), (1, 2, 2)),
        (Fraction(1, 2), Fraction(1, 2)),
    )
    result = exact.evaluate_generic_h2_partial_fixed_kappa_policy_v1(
        root_actions=roots,
        root_decision=root_kappa,
        child_decisions=(((2, 1, 0), child_kappa),),
        modeled_child_support_by_root=(
            ((0, 1, 0), ((2, 1, 0),)),
            ((0, 1, 1), ()),
        ),
        globally_modeled_child_states=((2, 1, 0),),
    )
    assert result.policy_abort_failure_probability == Fraction(1, 2)
    assert tuple(
        (item.root_action, item.state_key)
        for item in result.policy_abort_branches
    ) == (((0, 1, 1), (2, 1, 0)),)


def test_modeled_support_omission_and_exact_absence_fail_protocol() -> None:
    roots = _fixed_kappa_generic_inventory()
    root_kappa = exact.GenericH2UniformKappaDecisionV1(
        "semantic-root",
        ((0, 1, 0), (0, 1, 1)),
        (Fraction(1, 2), Fraction(1, 2)),
    )
    with pytest.raises(
        exact.V074ModeledSupportExactLiftProtocolViolation,
        match="DECISION_OMISSION",
    ):
        exact.evaluate_generic_h2_partial_fixed_kappa_policy_v1(
            root_actions=roots,
            root_decision=root_kappa,
            child_decisions=(),
            modeled_child_support_by_root=(
                ((0, 1, 0), ((2, 1, 0),)),
                ((0, 1, 1), ()),
            ),
            globally_modeled_child_states=((2, 1, 0),),
        )
    invented = exact.GenericH2UniformKappaDecisionV1(
        "invented",
        ((1, 2, 1),),
        (Fraction(1),),
    )
    with pytest.raises(
        exact.V074ModeledSupportExactLiftProtocolViolation,
        match="NOT_PRESENT",
    ):
        exact.evaluate_generic_h2_partial_fixed_kappa_policy_v1(
            root_actions=roots,
            root_decision=root_kappa,
            child_decisions=(((9, 9, 9), invented),),
            modeled_child_support_by_root=(
                ((0, 1, 0), ((9, 9, 9),)),
                ((0, 1, 1), ()),
            ),
            globally_modeled_child_states=((9, 9, 9),),
        )
