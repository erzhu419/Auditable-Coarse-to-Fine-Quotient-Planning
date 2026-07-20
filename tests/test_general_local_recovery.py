from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from acfqp.general_local_recovery import (
    CausalProofCircuit,
    CausalProofNode,
    CausalRealization,
    CausalRoot,
    CausalSearchStatus,
    CausalSuccessor,
    CertificateObligation,
    FAILURE_UPPER,
    REWARD_LOWER,
    causal_circuit_from_failed_proof,
    evaluate_counterfactual_certificate,
    find_slack_aware_causal_family,
    root_channel_gain,
)


def _leaf(
    node_id: str,
    *failures: Fraction,
    recoverable: bool = True,
    cost: int = 1,
) -> CausalProofNode:
    return CausalProofNode(
        node_id,
        tuple(
            CausalRealization(f"{node_id}:{index}", immediate_failure=value)
            for index, value in enumerate(failures)
        ),
        recoverable=recoverable,
        capability_cost=cost,
    )


def _risk(threshold: Fraction) -> tuple[CertificateObligation, ...]:
    return (CertificateObligation(FAILURE_UPPER, threshold),)


def _safe_chain_circuit() -> CausalProofCircuit:
    common = _leaf(
        "common",
        Fraction(1, 100),
        Fraction(101, 200),
        cost=16,
    )
    rare = _leaf(
        "rare",
        Fraction(99, 100),
        Fraction(199, 200),
        cost=16,
    )
    successors = (
        CausalSuccessor("common", Fraction(99, 100)),
        CausalSuccessor("rare", Fraction(1, 100)),
    )
    roots = tuple(
        CausalProofNode(
            f"root:{index}",
            (CausalRealization(f"root:{index}:selected", successors=successors),),
            recoverable=False,
        )
        for index in range(2)
    )
    return CausalProofCircuit(
        (*roots, common, rare),
        (
            CausalRoot("root:0", Fraction(1, 2)),
            CausalRoot("root:1", Fraction(1, 2)),
        ),
    )


def test_safe_chain_slack_excludes_the_rare_direct_residual() -> None:
    circuit = _safe_chain_circuit()
    obligations = _risk(Fraction(1, 20))
    result = find_slack_aware_causal_family(
        circuit,
        obligations,
        max_evaluations=8,
    )

    assert result.status == CausalSearchStatus.CAUSAL_FAMILY_FOUND
    assert result.search_complete
    assert result.baseline.root_value(FAILURE_UPPER) == Fraction(5099, 10000)
    assert result.baseline.deficit(FAILURE_UPPER) == Fraction(4599, 10000)
    assert result.baseline.eligible_node_ids == ("common", "rare")
    assert result.minimal_cover_node_ids == (("common",),)
    assert result.selected_node_ids == ("common",)
    assert result.selected_activation_trace == ("common",)
    assert result.candidate_node_ids == ("common", "rare")
    assert result.excluded_candidate_node_ids == ("rare",)

    common = evaluate_counterfactual_certificate(
        circuit, obligations, ("common",)
    )
    rare = evaluate_counterfactual_certificate(circuit, obligations, ("rare",))
    both = evaluate_counterfactual_certificate(
        circuit, obligations, ("common", "rare")
    )
    assert common.root_value(FAILURE_UPPER) == Fraction(397, 20000)
    assert common.certified
    assert rare.root_value(FAILURE_UPPER) == Fraction(10197, 20000)
    assert not rare.certified
    assert both.root_value(FAILURE_UPPER) == Fraction(99, 5000)
    assert root_channel_gain(result.baseline, common, FAILURE_UPPER) == Fraction(
        9801, 20000
    )
    assert root_channel_gain(result.baseline, rare, FAILURE_UPPER) == Fraction(
        1, 20000
    )


def test_authoritative_safe_chain_projection_has_the_same_one_cell_cone() -> None:
    from acfqp.local_recovery import build_failed_proof_graph
    from acfqp.phase3c import (
        _select_recovery_proposal,
        construct_phase3c_world,
    )
    from acfqp.planning import FiniteHorizonPolicy, audit_abstract_policy
    from acfqp.portable_planner import solve_portable_pareto

    world = construct_phase3c_world()
    query = world.queries[1].query
    portable = solve_portable_pareto(
        world.portable.model,
        world.portable.query_from_spec(query),
    )
    proposal, _ = _select_recovery_proposal(portable)
    policy = FiniteHorizonPolicy.from_mapping(
        world.portable.decode_policy(proposal.policy)
    )
    audit = audit_abstract_policy(
        world.kernel,
        query,
        world.models.envelope,
        policy,
    )
    graph = build_failed_proof_graph(
        world.kernel,
        query,
        world.models.envelope,
        policy,
        audit,
    )
    circuit = causal_circuit_from_failed_proof(
        world.kernel,
        query,
        world.models.envelope,
        policy,
        graph,
    )

    result = find_slack_aware_causal_family(
        circuit,
        _risk(query.delta),
        max_evaluations=8,
    )

    common = next(
        node.node_id
        for node in graph.nodes
        if node.cell == "active|empty=1|hist=((1, 1), (2, 2))"
    )
    rare = next(
        node.node_id
        for node in graph.nodes
        if node.cell == "active|empty=1|hist=((2, 3),)"
    )
    assert result.selected_node_ids == (common,)
    assert result.minimal_cover_node_ids == ((common,),)
    assert result.excluded_candidate_node_ids == (rare,)
    assert circuit.node(common).capability_cost == 16
    assert circuit.node(rare).capability_cost == 16
    assert result.baseline.root_value(FAILURE_UPPER) == Fraction(5099, 10000)
    selected = evaluate_counterfactual_certificate(
        circuit, _risk(query.delta), (common,)
    )
    assert selected.root_value(FAILURE_UPPER) == Fraction(397, 20000)


def test_adapter_opens_only_the_earliest_directbad_layer() -> None:
    """An ancestor+descendant DirectBad DAG cannot become one broad transaction."""

    from acfqp.local_recovery import build_failed_proof_graph
    from acfqp.phase3c import (
        _select_recovery_proposal,
        construct_phase3c_world,
    )
    from acfqp.planning import FiniteHorizonPolicy, audit_abstract_policy
    from acfqp.portable_planner import solve_portable_pareto

    world = construct_phase3c_world()
    query = world.queries[1].query
    portable = solve_portable_pareto(
        world.portable.model,
        world.portable.query_from_spec(query),
    )
    proposal, _ = _select_recovery_proposal(portable)
    policy = FiniteHorizonPolicy.from_mapping(
        world.portable.decode_policy(proposal.policy)
    )
    audit = audit_abstract_policy(
        world.kernel,
        query,
        world.models.envelope,
        policy,
    )
    graph = build_failed_proof_graph(
        world.kernel,
        query,
        world.models.envelope,
        policy,
        audit,
    )
    # The authoritative fixture has DirectBad only at h=1.  Make both h=2
    # ancestors DirectBad as a synthetic adapter regression while preserving
    # the exact realization DAG.
    layered = replace(
        graph,
        nodes=tuple(
            replace(node, direct_bad=True) if node.remaining == 2 else node
            for node in graph.nodes
        ),
        graph_id="synthetic-layered-directbad-graph",
    )
    frontier_ids = frozenset(layered.frontier().node_ids)
    root_ids = frozenset(
        node.node_id for node in layered.nodes if node.remaining == 2
    )
    descendant_ids = frozenset(
        node.node_id for node in layered.nodes if node.remaining == 1
    )
    assert frontier_ids == root_ids
    assert all(
        node.direct_bad for node in layered.nodes if node.node_id in descendant_ids
    )

    circuit = causal_circuit_from_failed_proof(
        world.kernel,
        query,
        world.models.envelope,
        policy,
        layered,
    )

    assert all(circuit.node(node_id).recoverable for node_id in root_ids)
    assert all(not circuit.node(node_id).recoverable for node_id in descendant_ids)


def test_inactive_no_contribution_residual_is_never_authorized() -> None:
    active = _leaf("active", Fraction(0), Fraction(3, 50))
    inactive = _leaf("inactive", Fraction(0), Fraction(1, 25))
    root = CausalProofNode(
        "root",
        (
            CausalRealization(
                "root:active",
                successors=(CausalSuccessor("active", Fraction(1)),),
            ),
            CausalRealization(
                "root:inactive",
                successors=(CausalSuccessor("inactive", Fraction(1)),),
            ),
        ),
        recoverable=False,
    )
    circuit = CausalProofCircuit(
        (root, active, inactive),
        (CausalRoot("root", Fraction(1)),),
    )

    result = find_slack_aware_causal_family(
        circuit,
        _risk(Fraction(1, 20)),
        max_evaluations=8,
    )

    assert result.selected_node_ids == ("active",)
    assert result.candidate_node_ids == ("active",)
    assert "inactive" not in result.baseline.active_nodes(FAILURE_UPPER)


def test_new_worst_case_branch_can_activate_after_the_first_discharge() -> None:
    first = _leaf("first", Fraction(0), Fraction(1, 10))
    second = _leaf("second", Fraction(0), Fraction(2, 25))
    root = CausalProofNode(
        "root",
        (
            CausalRealization(
                "root:first",
                successors=(CausalSuccessor("first", Fraction(1)),),
            ),
            CausalRealization(
                "root:second",
                successors=(CausalSuccessor("second", Fraction(1)),),
            ),
        ),
        recoverable=False,
    )
    circuit = CausalProofCircuit(
        (root, first, second),
        (CausalRoot("root", Fraction(1)),),
    )

    result = find_slack_aware_causal_family(
        circuit,
        _risk(Fraction(1, 25)),
        max_evaluations=8,
    )

    assert result.minimal_cover_node_ids == (("first", "second"),)
    assert result.selected_activation_trace == ("first", "second")
    first_record = next(
        record for record in result.evaluations if record.discharged_node_ids == ("first",)
    )
    assert first_record.certificate.eligible_node_ids == ("second",)
    assert "second" in first_record.certificate.active_nodes(FAILURE_UPPER)


def test_tied_diamond_keeps_all_extremizers_and_allows_zero_delta_steps() -> None:
    left = _leaf("left", Fraction(0), Fraction(1, 10))
    right = _leaf("right", Fraction(0), Fraction(1, 10))
    root = CausalProofNode(
        "root",
        (
            CausalRealization(
                "root:left",
                successors=(CausalSuccessor("left", Fraction(1)),),
            ),
            CausalRealization(
                "root:right",
                successors=(CausalSuccessor("right", Fraction(1)),),
            ),
        ),
        recoverable=False,
    )
    circuit = CausalProofCircuit(
        (root, left, right),
        (CausalRoot("root", Fraction(1)),),
    )
    obligations = _risk(Fraction(1, 25))

    result = find_slack_aware_causal_family(
        circuit,
        obligations,
        max_evaluations=8,
    )

    assert set(result.baseline.active_nodes(FAILURE_UPPER)) == {
        "left",
        "right",
        "root",
    }
    assert result.baseline.eligible_node_ids == ("left", "right")
    assert result.minimal_cover_node_ids == (("left", "right"),)
    left_only = evaluate_counterfactual_certificate(circuit, obligations, ("left",))
    right_only = evaluate_counterfactual_certificate(circuit, obligations, ("right",))
    assert root_channel_gain(result.baseline, left_only, FAILURE_UPPER) == 0
    assert root_channel_gain(result.baseline, right_only, FAILURE_UPPER) == 0
    assert not left_only.certified and not right_only.certified


def test_reward_lower_uses_the_dual_active_min_derivation() -> None:
    reward = CausalProofNode(
        "reward",
        (
            CausalRealization("reward:low", immediate_reward=Fraction(1, 10)),
            CausalRealization("reward:high", immediate_reward=Fraction(7, 10)),
        ),
    )
    circuit = CausalProofCircuit(
        (reward,),
        (CausalRoot("reward", Fraction(1)),),
    )
    obligations = (CertificateObligation(REWARD_LOWER, Fraction(3, 5)),)

    result = find_slack_aware_causal_family(
        circuit,
        obligations,
        max_evaluations=4,
    )

    assert result.baseline.root_value(REWARD_LOWER) == Fraction(1, 10)
    assert result.baseline.deficit(REWARD_LOWER) == Fraction(1, 2)
    assert result.selected_node_ids == ("reward",)
    repaired = evaluate_counterfactual_certificate(circuit, obligations, ("reward",))
    assert repaired.root_value(REWARD_LOWER) == Fraction(7, 10)
    assert root_channel_gain(result.baseline, repaired, REWARD_LOWER) == Fraction(3, 5)


def test_search_cap_is_explicit_and_never_returns_a_provisional_cover() -> None:
    circuit = _safe_chain_circuit()
    result = find_slack_aware_causal_family(
        circuit,
        _risk(Fraction(1, 20)),
        max_evaluations=1,
    )

    assert result.status == CausalSearchStatus.SEARCH_CAP_REACHED
    assert not result.search_complete
    assert result.evaluation_count == 1
    assert result.selected_node_ids is None
    assert result.minimal_cover_node_ids == ()


def test_invalid_circuit_rejects_cycles_and_nonexact_caps() -> None:
    cyclic = CausalProofNode(
        "cycle",
        (
            CausalRealization(
                "cycle:branch",
                successors=(CausalSuccessor("cycle", Fraction(1)),),
            ),
        ),
    )
    with pytest.raises(ValueError, match="cycle"):
        CausalProofCircuit((cyclic,), (CausalRoot("cycle", Fraction(1)),))

    circuit = _safe_chain_circuit()
    for invalid_cap in (0, True, 1.5, Fraction(3, 2)):
        with pytest.raises(ValueError, match="positive integer"):
            find_slack_aware_causal_family(
                circuit,
                _risk(Fraction(1, 20)),
                max_evaluations=invalid_cap,  # type: ignore[arg-type]
            )


@pytest.mark.parametrize("invalid", (True, 0.5, "1/2"))
def test_causal_numbers_reject_non_symbolic_inputs(invalid: object) -> None:
    with pytest.raises(ValueError, match="exact integers or Fractions"):
        CausalSuccessor("leaf", invalid)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="exact integers or Fractions"):
        CausalRealization("row", immediate_failure=invalid)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="exact integers or Fractions"):
        CausalRoot("leaf", invalid)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid", (True, 1.5, Fraction(3, 2)))
def test_capability_cost_requires_an_integer(invalid: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        CausalProofNode(
            "leaf",
            (CausalRealization("leaf:row"),),
            capability_cost=invalid,  # type: ignore[arg-type]
        )


def test_realization_probability_channels_cannot_overlap() -> None:
    with pytest.raises(ValueError, match="failure plus successor"):
        CausalRealization(
            "impossible",
            immediate_failure=Fraction(3, 5),
            successors=(CausalSuccessor("next", Fraction(1, 2)),),
        )


def test_causal_circuit_rejects_duplicate_root_rows() -> None:
    leaf = _leaf("leaf", Fraction(0))
    with pytest.raises(ValueError, match="duplicate root"):
        CausalProofCircuit(
            (leaf,),
            (
                CausalRoot("leaf", Fraction(1, 2)),
                CausalRoot("leaf", Fraction(1, 2)),
            ),
        )
