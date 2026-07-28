from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import inspect

import pytest

import acfqp.relational_graph_core_v1 as graph_core
from acfqp.relational_graph_core_v1 import (
    AnonymousGraphSourceLogV1,
    GraphProgramContext,
    GraphProgramType,
    GraphTopologyV1,
    RelationalGraphCoordinateProposalV1,
    RelationalGraphCoreInvariantViolation,
    build_registered_multigeometry_source_log_v1,
    evaluate_action_coordinate_v1,
    evaluate_state_coordinate_v1,
    generate_relational_graph_program_registry_v1,
    relational_graph_synthesis_metrics_v1,
    synthesize_relational_graph_proposal_v1,
    verify_relational_graph_proposal_v1,
)


@pytest.fixture(scope="module")
def source_log() -> AnonymousGraphSourceLogV1:
    return build_registered_multigeometry_source_log_v1()


@pytest.fixture(scope="module")
def proposal(
    source_log: AnonymousGraphSourceLogV1,
) -> RelationalGraphCoordinateProposalV1:
    return synthesize_relational_graph_proposal_v1(source_log)


def _all_keys(value: object) -> set[str]:
    if type(value) is dict:
        mapping = value
        return set(mapping) | set().union(
            *(_all_keys(item) for item in mapping.values()),
            set(),
        )
    if type(value) is list:
        return set().union(*(_all_keys(item) for item in value), set())
    return set()


def test_topology_requires_canonical_simple_undirected_encoding() -> None:
    topology = GraphTopologyV1(
        5,
        ((0, 1), (0, 4), (1, 2), (2, 3), (3, 4)),
    )
    assert topology.vertex_count == 5
    assert topology.neighbors(0) == frozenset((1, 4))
    assert len(topology.topology_id) == 64

    invalid_edges = (
        ((1, 0),),
        ((0, 0),),
        ((0, 1), (0, 1)),
        ((1, 2), (0, 1)),
        ((0, 5),),
    )
    for edges in invalid_edges:
        with pytest.raises(RelationalGraphCoreInvariantViolation):
            GraphTopologyV1(5, edges)


def test_registered_source_is_three_nonisomorphic_geometries_and_full_h2(
    source_log: AnonymousGraphSourceLogV1,
) -> None:
    degree_sequences = {
        tuple(
            sorted(
                len(topology.neighbors(vertex))
                for vertex in range(topology.vertex_count)
            )
        )
        for topology in source_log.topologies
    }
    assert degree_sequences == {
        (1, 1, 2, 2),  # path
        (1, 1, 1, 3),  # star
        (1, 2, 2, 3),  # paw
    }
    assert len(source_log.topologies) == 3
    assert len(source_log.rows) == 120
    assert {
        row.state.remaining_horizon for row in source_log.rows
    } == {1, 2}
    assert len({row.state.state_id for row in source_log.rows}) == 51
    assert (
        source_log.source_log_id
        == "c1ac08335f6479ede4334b22a1af0fad5b5e300a85106db2874eac2f1907640f"
    )


def test_truncated_or_topology_incomplete_source_log_fails_closed(
    source_log: AnonymousGraphSourceLogV1,
) -> None:
    with pytest.raises(
        RelationalGraphCoreInvariantViolation,
        match="omits or duplicates",
    ):
        AnonymousGraphSourceLogV1(
            source_log.topologies,
            source_log.rows[1:],
        )
    with pytest.raises(
        RelationalGraphCoreInvariantViolation,
        match="not legal under its topology",
    ):
        AnonymousGraphSourceLogV1(
            source_log.topologies[1:],
            source_log.rows,
        )


def test_depth_two_typed_closure_is_complete_and_semantically_deduplicated(
    source_log: AnonymousGraphSourceLogV1,
) -> None:
    registry = generate_relational_graph_program_registry_v1(source_log)
    assert registry.syntactic_program_count == 262
    assert registry.semantic_program_count_by_depth == (6, 12, 24)
    assert len(registry.programs) == 42
    assert max(item.depth for item in registry.programs) == 2
    assert all(item.depth <= 2 for item in registry.programs)
    assert {
        item.operation for item in registry.programs
    }.issuperset(
        {
            "all_cells",
            "occupied_cells",
            "legal_actions",
            "survivor_cell",
            "pair_cells",
            "rank_degree_signature",
            "cardinality_cells",
            "cardinality_actions",
            "adjacent_filter",
            "set_difference",
        }
    )


def test_public_producer_has_one_source_log_input_and_no_external_authority() -> None:
    signature = inspect.signature(synthesize_relational_graph_proposal_v1)
    assert tuple(signature.parameters) == ("source_log",)
    producer_source = inspect.getsource(
        synthesize_relational_graph_proposal_v1
    )
    assert "kernel" not in producer_source
    assert "query" not in producer_source
    assert "target" not in producer_source
    module_source = inspect.getsource(graph_core)
    assert "acfqp.domains" not in module_source
    assert "QuerySpec" not in module_source


def test_complete_source_only_search_selects_relational_coordinates(
    source_log: AnonymousGraphSourceLogV1,
    proposal: RelationalGraphCoordinateProposalV1,
) -> None:
    assert (
        proposal.state_program.rendered
        == "cardinality_actions(legal_actions)"
    )
    assert (
        proposal.action_program.rendered
        == "cardinality_cells("
        "adjacent_filter(survivor_cell,occupied_cells))"
    )
    assert proposal.state_program.result_type is GraphProgramType.INTEGER
    assert proposal.state_program.context is GraphProgramContext.STATE
    assert proposal.action_program.result_type is GraphProgramType.INTEGER
    assert (
        proposal.action_program.context
        is GraphProgramContext.STATE_ACTION
    )
    assert (
        proposal.proposal_id
        == "ff3cd610c7ce2549e737e340f89491b6f57c5d4b2e3ac03cb797f8a685e8701d"
    )
    assert verify_relational_graph_proposal_v1(source_log, proposal)


def test_selected_pair_is_compressive_and_width_is_reported_honestly(
    source_log: AnonymousGraphSourceLogV1,
    proposal: RelationalGraphCoordinateProposalV1,
) -> None:
    metrics = relational_graph_synthesis_metrics_v1(source_log, proposal)
    assert metrics.state_integer_program_count == 5
    assert metrics.action_integer_program_count == 5
    assert metrics.evaluated_candidate_count == 25
    assert metrics.admissible_candidate_count == 2
    assert metrics.ground_state_count == 51
    assert metrics.ground_row_count == 120
    assert metrics.abstract_state_count == 4
    assert metrics.abstract_support_count == 7
    assert metrics.alias_pair_count == 1092
    assert metrics.availability_variant_count == 4
    assert metrics.transition_alias_width == Fraction(99, 100)
    assert metrics.reward_alias_width == 0
    assert metrics.sound_alias_width == Fraction(99, 100)
    assert metrics.abstract_state_count < metrics.ground_state_count
    assert metrics.abstract_support_count < metrics.ground_row_count
    assert (
        metrics.metrics_id
        == "67a43678973acc8141474c81fd19212eebce1fca4a0459bfaed3b2613108141a"
    )


def test_registry_exposes_topology_refinement_programs_and_strict_evaluators(
    source_log: AnonymousGraphSourceLogV1,
) -> None:
    registry = generate_relational_graph_program_registry_v1(source_log)
    signature_program = next(
        item
        for item in registry.programs
        if item.rendered == "rank_degree_signature"
    )
    degree_program = next(
        item
        for item in registry.programs
        if item.rendered
        == "cardinality_cells("
        "adjacent_filter(survivor_cell,all_cells))"
    )
    assert signature_program.result_type is GraphProgramType.SIGNATURE
    assert signature_program.context is GraphProgramContext.STATE
    assert degree_program.result_type is GraphProgramType.INTEGER
    assert degree_program.context is GraphProgramContext.STATE_ACTION

    row = source_log.rows[0]
    topology = next(
        item
        for item in source_log.topologies
        if item.topology_id == row.state.topology_id
    )
    state_value = evaluate_state_coordinate_v1(
        signature_program,
        topology,
        row.state,
    )
    action_value = evaluate_action_coordinate_v1(
        degree_program,
        topology,
        row.state,
        row.action,
        row.legal_actions,
    )
    assert state_value[0] == "SIGNATURE"
    assert tuple(sorted(state_value[1])) == state_value[1]
    assert action_value == (
        "INTEGER",
        len(topology.neighbors(row.action.survivor)),
    )

    with pytest.raises(RelationalGraphCoreInvariantViolation):
        evaluate_state_coordinate_v1(
            degree_program,
            topology,
            row.state,
        )
    with pytest.raises(RelationalGraphCoreInvariantViolation):
        evaluate_action_coordinate_v1(
            degree_program,
            topology,
            row.state,
            row.action,
            row.legal_actions[1:],
        )


def test_proposal_contains_only_programs_schema_and_provenance(
    proposal: RelationalGraphCoordinateProposalV1,
) -> None:
    document = proposal.to_document()
    keys = _all_keys(document)
    assert not {
        "rows",
        "outcomes",
        "probabilities",
        "rewards",
        "policy",
        "decisions",
    } & keys
    assert proposal.source_dynamics_included is False
    assert proposal.source_decisions_included is False
    assert proposal.target_identity_included is False
    assert proposal.query_identity_included is False
    assert proposal.support_key_schema.fields == (
        "remaining_horizon",
        "state_coordinate_value",
        "action_coordinate_value",
    )
    assert proposal.support_key_schema.target_instantiation_required is True


def test_verifier_replays_selection_and_rejects_a_valid_but_wrong_program(
    source_log: AnonymousGraphSourceLogV1,
    proposal: RelationalGraphCoordinateProposalV1,
) -> None:
    registry = generate_relational_graph_program_registry_v1(source_log)
    alternative = next(
        item
        for item in registry.programs
        if item.result_type is GraphProgramType.INTEGER
        and item.context is GraphProgramContext.STATE
        and item.program_id != proposal.state_program.program_id
    )
    forged = replace(proposal, state_program=alternative)
    assert forged.proposal_id != proposal.proposal_id
    with pytest.raises(
        RelationalGraphCoreInvariantViolation,
        match="differs from complete source-only replay",
    ):
        verify_relational_graph_proposal_v1(source_log, forged)
    with pytest.raises(
        RelationalGraphCoreInvariantViolation,
        match="noncanonical proposal",
    ):
        relational_graph_synthesis_metrics_v1(source_log, forged)


def test_rebuild_is_deterministic_and_content_ids_are_role_bound(
    source_log: AnonymousGraphSourceLogV1,
    proposal: RelationalGraphCoordinateProposalV1,
) -> None:
    rebuilt = synthesize_relational_graph_proposal_v1(source_log)
    assert rebuilt.to_document() == proposal.to_document()
    assert rebuilt.proposal_id == proposal.proposal_id
    assert proposal.proposal_id != source_log.source_log_id
    assert (
        proposal.support_key_schema.support_schema_id
        != proposal.state_program.program_id
    )


def test_duck_typed_inputs_and_expansive_call_signatures_are_rejected(
    source_log: AnonymousGraphSourceLogV1,
) -> None:
    class DuckLog:
        rows = source_log.rows
        topologies = source_log.topologies
        source_log_id = source_log.source_log_id

    with pytest.raises(RelationalGraphCoreInvariantViolation):
        synthesize_relational_graph_proposal_v1(DuckLog())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        synthesize_relational_graph_proposal_v1(  # type: ignore[call-arg]
            source_log,
            target="forbidden",
        )
