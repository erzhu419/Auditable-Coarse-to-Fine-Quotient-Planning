from __future__ import annotations

from collections import deque
import random

import pytest

from acfqp import construction_k7_atomic_composition_preregistration_v49r3 as v49r3
from acfqp.domains.stochastic_inventory_assembly import (
    InventoryAssemblyStatus,
    generate_stochastic_inventory_assembly,
)
from acfqp.domains.stochastic_modular_routing import (
    StochasticModularStatus,
    generate_stochastic_modular_routing,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    GenericLayoutFactorizedWorldModelV5Error,
    align_generic_occurrence_v5,
    discover_generic_layout_v5,
    match_generic_layout_v5,
    match_generic_layout_meta_prior_v5,
    synthesize_layout_factorized_world_model_v5,
    verify_target_layout_compatibility_v5,
)
from acfqp.phase3e_ids import content_id


TERMINAL_TOKENS = {"A": 9_001, "F": 9_007, "S": 9_011}
MODE_TOKENS = (8_001, 8_009, 8_021, 8_039)
CLASS_TOKENS = (8_101, 8_111, 8_117)
DEV_LAYOUT_DOMAIN = v49r3.FUTURE_DOMAINS["observation"]
DEV_PROGRAM_DOMAIN = v49r3.FUTURE_DOMAINS["program"]
DEV_SUPPORT_DOMAIN = v49r3.FUTURE_DOMAINS["support"]


def _permutations(seed: int, state_width: int, action_width: int):
    rng = random.Random(seed ^ 0x5A17)
    states = list(range(state_width))
    actions = list(range(action_width))
    rng.shuffle(states)
    rng.shuffle(actions)
    return tuple(states), tuple(actions)


def _modular(seed: int, occurrence: int, *, node_count: int = 6):
    kernel, _ = generate_stochastic_modular_routing(
        node_count=node_count,
        modulus=7 if node_count == 6 else 11,
        capacity=20 if node_count == 6 else 25,
        step_limit=7 if node_count == 6 else 9,
        mode_deltas=(1, 2, 3) if node_count == 6 else (1, 2, 4, 5),
        seed=seed,
    )
    state_order, action_order = _permutations(seed, 9, 6)
    catalogue = []
    for index, edge in enumerate(kernel.edges):
        semantic = (
            seed * 100 + edge.source,
            seed * 100 + edge.destination,
            MODE_TOKENS[edge.mode],
            edge.magnitude,
            CLASS_TOKENS[edge.cost_class],
            seed * 10_000 + index,
        )
        catalogue.append(
            FlatRawActionV4(
                index, tuple(semantic[position] for position in action_order)
            )
        )

    def encode(state):
        name = (
            "A"
            if state.status is StochasticModularStatus.ACTIVE
            else "S"
            if state.status is StochasticModularStatus.SUCCESS
            else "F"
        )
        semantic = (
            seed * 100 + state.node,
            state.phase,
            state.resource,
            state.steps,
            TERMINAL_TOKENS[name],
            kernel.modulus,
            kernel.capacity,
            kernel.goal_phase,
            seed * 100 + kernel.goal_node,
        )
        return tuple(semantic[position] for position in state_order)

    queue = deque([kernel.initial_distribution()[0][1]])
    seen = set(queue)
    rows = []
    while queue:
        state = queue.popleft()
        legal = kernel.actions(state)
        for action in legal:
            for outcome in kernel.step(state, action):
                successor = outcome.next_state
                legal_after = kernel.actions(successor)
                rows.append(
                    FlatRawTransitionV4(
                        occurrence,
                        len(rows),
                        encode(state),
                        tuple(row.edge for row in legal),
                        catalogue[action.edge],
                        encode(successor),
                        tuple(row.edge for row in legal_after),
                        None
                        if legal_after
                        else successor.status is StochasticModularStatus.SUCCESS,
                    )
                )
                if successor.status is StochasticModularStatus.ACTIVE and successor not in seen:
                    seen.add(successor)
                    queue.append(successor)
    return tuple(rows), tuple(catalogue), state_order, action_order


def _inventory(seed: int, occurrence: int, *, stage_count: int = 6):
    kernel, _ = generate_stochastic_inventory_assembly(
        stage_count=stage_count, seed=seed
    )
    state_order, action_order = _permutations(seed ^ 0x2233, 7, 5)
    catalogue = []
    for index, recipe in enumerate(kernel.recipes):
        semantic = (
            seed * 100 + recipe.source_stage,
            seed * 100 + recipe.destination_stage,
            recipe.produced_units,
            recipe.contamination_increment,
            seed * 10_000 + index,
        )
        catalogue.append(
            FlatRawActionV4(
                index, tuple(semantic[position] for position in action_order)
            )
        )

    def encode(state):
        name = (
            "A"
            if state.status is InventoryAssemblyStatus.ACTIVE
            else "S"
            if state.status is InventoryAssemblyStatus.SUCCESS
            else "F"
        )
        semantic = (
            seed * 100 + state.stage,
            state.units,
            state.contamination,
            TERMINAL_TOKENS[name],
            kernel.contamination_capacity,
            kernel.target_units,
            seed * 100 + kernel.goal_stage,
        )
        return tuple(semantic[position] for position in state_order)

    queue = deque([kernel.initial_distribution()[0][1]])
    seen = set(queue)
    rows = []
    while queue:
        state = queue.popleft()
        legal = kernel.actions(state)
        for action in legal:
            for outcome in kernel.step(state, action):
                successor = outcome.next_state
                legal_after = kernel.actions(successor)
                rows.append(
                    FlatRawTransitionV4(
                        occurrence,
                        len(rows),
                        encode(state),
                        tuple(row.recipe for row in legal),
                        catalogue[action.recipe],
                        encode(successor),
                        tuple(row.recipe for row in legal_after),
                        None
                        if legal_after
                        else successor.status is InventoryAssemblyStatus.SUCCESS,
                    )
                )
                if successor.status is InventoryAssemblyStatus.ACTIVE and successor not in seen:
                    seen.add(successor)
                    queue.append(successor)
    return tuple(rows), tuple(catalogue), state_order, action_order


@pytest.mark.parametrize(
    ("builder", "seeds"),
    [
        (_modular, (598_101, 598_102, 598_103)),
        (_inventory, (598_201, 598_202, 598_203)),
    ],
)
def test_relation_graph_recovers_one_shared_layout_under_independent_permutations(
    builder, seeds
) -> None:
    layouts = []
    raw_orders = []
    reference_rows = None
    reference_catalogue = None
    reference_layout = None
    for occurrence, seed in enumerate(seeds):
        rows, catalogue, state_order, action_order = builder(seed, occurrence)
        if reference_layout is None:
            reference_rows = rows
            reference_catalogue = catalogue
            reference_layout = discover_generic_layout_v5(
                rows, catalogue, layout_domain=DEV_LAYOUT_DOMAIN
            )
            layouts.append(reference_layout)
        else:
            layouts.append(
                match_generic_layout_v5(
                    reference_rows,
                    reference_catalogue,
                    reference_layout,
                    rows,
                    catalogue,
                    layout_domain=DEV_LAYOUT_DOMAIN,
                )
            )
        raw_orders.append((state_order, action_order))
    assert len({layout.schema_signature for layout in layouts}) == 1
    assert len(set(raw_orders)) == len(raw_orders)
    assert all(len(set(layout.state_colors)) == len(layout.state_colors) for layout in layouts)
    assert all(len(set(layout.action_colors)) == len(layout.action_colors) for layout in layouts)


@pytest.mark.parametrize(
    ("builder", "seeds", "required_opcodes"),
    [
        (_modular, (598_111, 598_112, 598_113), {"E06", "E07", "E12"}),
        (_inventory, (598_211, 598_212, 598_213), {"E05", "E07", "E12"}),
    ],
)
def test_same_generic_pipeline_synthesizes_both_stochastic_domains(
    builder, seeds, required_opcodes
) -> None:
    rows = {}
    catalogues = {}
    for occurrence, seed in enumerate(seeds):
        rows[occurrence], catalogues[occurrence], _, _ = builder(seed, occurrence)
    model = synthesize_layout_factorized_world_model_v5(
        rows,
        catalogues,
        layout_domain=DEV_LAYOUT_DOMAIN,
        program_domain=DEV_PROGRAM_DOMAIN,
        support_domain=DEV_SUPPORT_DOMAIN,
    )
    assert required_opcodes <= set(model["compiled_program"]["used_opcode_names"])
    assert model["specialized_layout_discovery_pattern_count"] == 0
    assert model["predeclared_layout_or_factor_roles"] == []


def test_incompatible_stochastic_domain_is_rejected_without_transfer() -> None:
    modular_rows = {}
    modular_catalogues = {}
    for occurrence, seed in enumerate((598_121, 598_122, 598_123)):
        modular_rows[occurrence], modular_catalogues[occurrence], _, _ = _modular(
            seed, occurrence
        )
    model = synthesize_layout_factorized_world_model_v5(
        modular_rows,
        modular_catalogues,
        layout_domain=DEV_LAYOUT_DOMAIN,
        program_domain=DEV_PROGRAM_DOMAIN,
        support_domain=DEV_SUPPORT_DOMAIN,
    )
    rows, catalogue, _, _ = _inventory(598_221, 0)
    target = discover_generic_layout_v5(rows, catalogue, layout_domain=DEV_LAYOUT_DOMAIN)
    assert verify_target_layout_compatibility_v5(model, target) is False


def test_nonunique_anonymous_layout_fails_closed() -> None:
    rows, catalogue, _, _ = _inventory(598_231, 0)
    duplicated = tuple(
        FlatRawActionV4(action.key, action.fields + (action.fields[-1],))
        for action in catalogue
    )
    by_key = {action.key: action for action in duplicated}
    forged_rows = tuple(
        FlatRawTransitionV4(
            row.occurrence,
            row.index,
            row.pre,
            row.legal_before,
            by_key[row.action.key],
            row.post,
            row.legal_after,
            row.terminal_acceptance_after,
        )
        for row in rows
    )
    with pytest.raises(GenericLayoutFactorizedWorldModelV5Error):
        discover_generic_layout_v5(
            forged_rows, duplicated, layout_domain=DEV_LAYOUT_DOMAIN
        )


@pytest.mark.parametrize(
    ("builder", "source_seed", "target_seed", "target_kwargs"),
    [
        (_modular, 598_101, 598_301, {"node_count": 7}),
        (_inventory, 598_201, 598_401, {"stage_count": 7}),
    ],
)
def test_structural_meta_prior_recovers_target_layout_from_two_raw_support_labels(
    builder, source_seed, target_seed, target_kwargs
) -> None:
    source_rows, source_catalogue, source_state_order, source_action_order = builder(
        source_seed, 0
    )
    reference = discover_generic_layout_v5(
        source_rows, source_catalogue, layout_domain=DEV_LAYOUT_DOMAIN
    )
    target_rows, target_catalogue, target_state_order, target_action_order = builder(
        target_seed, 0, **target_kwargs
    )
    target = match_generic_layout_meta_prior_v5(
        source_rows,
        source_catalogue,
        reference,
        target_rows[:4],
        target_catalogue,
        layout_domain=DEV_LAYOUT_DOMAIN,
    )
    assert [
        source_state_order[index] for index in reference.state_canonical_to_raw
    ] == [target_state_order[index] for index in target.state_canonical_to_raw]
    assert [
        source_action_order[index] for index in reference.action_canonical_to_raw
    ] == [target_action_order[index] for index in target.action_canonical_to_raw]
    document = target.to_document()
    payload = {
        key: value
        for key, value in document.items()
        if key not in {"schema", "layout_id"}
    }
    assert content_id(DEV_LAYOUT_DOMAIN, payload) == document["layout_id"]
