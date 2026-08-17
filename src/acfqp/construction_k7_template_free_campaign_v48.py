"""Fresh V48 template-free three-domain world-model campaign."""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import hashlib
import random
from typing import Any, Callable, Mapping, NoReturn

from acfqp import construction_k7_template_free_preregistration_v48 as pre
from acfqp.domains.matching_buffer import (
    LMBAction,
    LMBKernel,
    LMBState,
    LMBStatus,
    generate_solvable_lmb,
)
from acfqp.domains.modular_walk import (
    ModularWalkAction,
    ModularWalkKernel,
    ModularWalkState,
    ModularWalkStatus,
    generate_modular_walk,
)
from acfqp.domains.stochastic_routing import (
    StochasticRoutingAction,
    StochasticRoutingKernel,
    StochasticRoutingState,
    StochasticRoutingStatus,
    generate_stochastic_routing,
    select_seeded_routing_outcome_v1,
)
from acfqp.generic_template_free_world_model_v3 import (
    GenericTemplateFreeWorldModelV3Error,
    RawActionV3,
    RawTransitionV3,
    action_relation_value_v3,
    derive_dependency_support_v3,
    execute_compiled_program_v3,
    plan_compiled_program_v3,
    synthesize_template_free_program_v3,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = "48.0.0"
CAMPAIGN_ID = "f8fff551812e7dce6d66bcbe68f5dfa8b1c6be66496f1383f9f6982bb2252a3f"
EXPECTED_CANONICAL_BYTE_COUNT = 188_814
EXPECTED_CANONICAL_SHA256 = "fe0e02652f7d6915526807a39991934ca8ea47cc7b1b0c758ffb4e03a3217740"


class ConstructionK7TemplateFreeCampaignV48Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TemplateFreeCampaignV48Error(message)


def _token(seed: int, namespace: int, value: int) -> int:
    return seed * 10_000_000 + namespace * 10_000 + value


def _permutation(width: int, seed: int, salt: int) -> tuple[int, ...]:
    values = list(range(width))
    random.Random(seed ^ salt).shuffle(values)
    return tuple(values)


def _lmb_raw_interface(
    seed: int, kernel: LMBKernel
) -> tuple[tuple[RawActionV3, ...], Callable[[LMBState], tuple[int, ...]], str]:
    field_order = _permutation(4, seed, pre.ACTION_FIELD_SALT)
    state_order = _permutation(kernel.type_count + 3, seed, pre.FLAT_LAYOUT_SALT)
    type_tokens = tuple(_token(seed, 11, index) for index in range(kernel.type_count))
    status_tokens = {
        LMBStatus.ACTIVE: _token(seed, 12, 1),
        LMBStatus.FAILURE: _token(seed, 12, 101),
        LMBStatus.SUCCESS: _token(seed, 12, 201),
    }
    catalogue = []
    for tile in range(kernel.tile_count):
        semantic = (
            1 << tile,
            sum(1 << blocker for blocker in kernel.blockers[tile]),
            type_tokens[kernel.tile_types[tile]],
            _token(seed, 13, tile),
        )
        catalogue.append(
            RawActionV3(tile, tuple(semantic[index] for index in field_order))
        )

    def encode(state: LMBState) -> tuple[int, ...]:
        semantic = (
            state.removed_mask,
            *state.buffer,
            kernel.capacity,
            status_tokens[state.status],
        )
        return tuple(semantic[index] for index in state_order)

    layout = {
        "state_width": kernel.type_count + 3,
        "action_field_width": 4,
        "state_permutation_sha256": hashlib.sha256(bytes(state_order)).hexdigest(),
        "action_permutation_sha256": hashlib.sha256(bytes(field_order)).hexdigest(),
        "semantic_role_names_serialized": False,
    }
    return (
        tuple(catalogue),
        encode,
        content_id(pre.FUTURE_DOMAINS["observation"], layout),
    )


def _routing_raw_interface(
    seed: int, kernel: StochasticRoutingKernel
) -> tuple[
    tuple[RawActionV3, ...],
    Callable[[StochasticRoutingState], tuple[int, ...]],
    str,
]:
    field_order = _permutation(5, seed, pre.ACTION_FIELD_SALT)
    state_order = _permutation(4, seed, pre.FLAT_LAYOUT_SALT)
    node_tokens = tuple(_token(seed, 21, index) for index in range(kernel.node_count))
    class_tokens = tuple(_token(seed, 22, index) for index in range(3))
    status_tokens = {
        StochasticRoutingStatus.ACTIVE: _token(seed, 23, 1),
        StochasticRoutingStatus.FAILURE: _token(seed, 23, 101),
        StochasticRoutingStatus.SUCCESS: _token(seed, 23, 201),
    }
    catalogue = []
    for edge_index, edge in enumerate(kernel.edges):
        semantic = (
            node_tokens[edge.source],
            node_tokens[edge.destination],
            edge.magnitude,
            class_tokens[edge.cost_class],
            _token(seed, 24, edge_index),
        )
        catalogue.append(
            RawActionV3(
                edge_index,
                tuple(semantic[index] for index in field_order),
            )
        )

    def encode(state: StochasticRoutingState) -> tuple[int, ...]:
        semantic = (
            node_tokens[state.node],
            state.resource,
            status_tokens[state.status],
            kernel.capacity,
        )
        return tuple(semantic[index] for index in state_order)

    layout = {
        "state_width": 4,
        "action_field_width": 5,
        "state_permutation_sha256": hashlib.sha256(bytes(state_order)).hexdigest(),
        "action_permutation_sha256": hashlib.sha256(bytes(field_order)).hexdigest(),
        "semantic_role_names_serialized": False,
    }
    return (
        tuple(catalogue),
        encode,
        content_id(pre.FUTURE_DOMAINS["observation"], layout),
    )


def _modular_raw_interface(
    seed: int, kernel: ModularWalkKernel
) -> tuple[
    tuple[RawActionV3, ...],
    Callable[[ModularWalkState], tuple[int, ...]],
    str,
]:
    field_order = _permutation(4, seed, pre.ACTION_FIELD_SALT)
    node_tokens = tuple(_token(seed, 31, index) for index in range(kernel.node_count))
    status_tokens = {
        ModularWalkStatus.ACTIVE: _token(seed, 32, 1),
        ModularWalkStatus.FAILURE: _token(seed, 32, 101),
        ModularWalkStatus.SUCCESS: _token(seed, 32, 201),
    }
    catalogue = []
    for edge_index, edge in enumerate(kernel.edges):
        semantic = (
            node_tokens[edge.source],
            node_tokens[edge.destination],
            pre.SHARED_MODE_TOKENS[edge.mode],
            _token(seed, 33, edge_index),
        )
        catalogue.append(
            RawActionV3(
                edge_index,
                tuple(semantic[index] for index in field_order),
            )
        )

    def encode(state: ModularWalkState) -> tuple[int, ...]:
        # The six columns are opaque to the synthesizer.  Their order is stable
        # only inside the registered D02 schema identity, which is the exact
        # structural-prior boundary tested by the OOD control.
        return (
            node_tokens[state.node],
            state.residue,
            state.steps,
            status_tokens[state.status],
            kernel.modulus,
            kernel.goal_residue,
        )

    layout = {
        "state_width": 6,
        "action_field_width": 4,
        "state_order_commitment": hashlib.sha256(b"D02:0,1,2,3,4,5").hexdigest(),
        "action_permutation_sha256": hashlib.sha256(bytes(field_order)).hexdigest(),
        "shared_mode_namespace_sha256": hashlib.sha256(
            canonical_json_bytes(list(pre.SHARED_MODE_TOKENS))
        ).hexdigest(),
        "semantic_role_names_serialized": False,
    }
    return (
        tuple(catalogue),
        encode,
        content_id(pre.FUTURE_DOMAINS["observation"], layout),
    )


def _raw_archive(
    family: str,
    seed: int,
    layout_id: str,
    catalogue: tuple[RawActionV3, ...],
    rows: tuple[RawTransitionV3, ...],
    *,
    acquisition_rounds: int,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.template_free_raw_observation.v48",
        "anonymous_family": family,
        "seed": seed,
        "opaque_layout_id": layout_id,
        "anonymous_action_catalogue": [row.to_document() for row in catalogue],
        "raw_transitions": [row.to_document() for row in rows],
        "source_transition_labels": len(rows),
        "source_environment_steps": len(rows),
        "adaptive_acquisition_rounds": acquisition_rounds,
        "generation_witness_accessed": False,
        "semantic_role_names_available_to_synthesizer": False,
    }
    return {
        **payload,
        "raw_observation_id": content_id(pre.FUTURE_DOMAINS["observation"], payload),
    }


def _acquire_lmb_source(
    occurrence: int, seed: int
) -> tuple[dict[str, Any], tuple[RawActionV3, ...], tuple[RawTransitionV3, ...]]:
    kernel, witness = generate_solvable_lmb(seed=seed, **pre.LMB_SOURCE_SPEC)
    del witness
    catalogue, encode, layout_id = _lmb_raw_interface(seed, kernel)
    repeated_fields = []
    for field in range(len(catalogue[0].fields)):
        counts = Counter(row.fields[field] for row in catalogue)
        if 1 < len(counts) < len(catalogue) and min(counts.values()) >= 3:
            repeated_fields.append((len(counts), field))
    if not repeated_fields:
        _fail("D00 witness-blind catalogue has no repeated anonymous field")
    exploration_field = min(repeated_fields)[1]
    rows: list[RawTransitionV3] = []
    rounds = 0
    fitted = False
    for preferred_value in sorted(
        {row.fields[exploration_field] for row in catalogue}
    ):
        state = kernel.initial_distribution()[0][1]
        while state.status is LMBStatus.ACTIVE:
            legal = kernel.actions(state)
            preferred = [
                action
                for action in legal
                if catalogue[action.tile].fields[exploration_field] == preferred_value
            ]
            action = min(preferred or list(legal), key=lambda row: row.tile)
            before = state
            state = kernel.step(state, action)[0].next_state
            rows.append(
                RawTransitionV3(
                    occurrence,
                    len(rows),
                    encode(before),
                    tuple(item.tile for item in legal),
                    catalogue[action.tile],
                    encode(state),
                    tuple(item.tile for item in kernel.actions(state)),
                )
            )
            if len(rows) > pre.MAX_SOURCE_LABELS_PER_FAMILY:
                _fail("D00 source crossed its frozen label cap")
        rounds += 1
        try:
            program = synthesize_template_free_program_v3(
                tuple(rows),
                {occurrence: catalogue},
                program_domain=pre.FUTURE_DOMAINS["program"],
            )
        except GenericTemplateFreeWorldModelV3Error:
            continue
        if program["vm_schema"] == ["INT_SET", "INT_VECTOR", "STATUS"]:
            fitted = True
            break
    if not fitted:
        _fail("D00 source did not identify an exact typed AST")
    frozen = tuple(rows)
    return (
        _raw_archive(
            "D00", seed, layout_id, catalogue, frozen, acquisition_rounds=rounds
        ),
        catalogue,
        frozen,
    )


def _acquire_routing_source(
    occurrence: int, seed: int
) -> tuple[dict[str, Any], tuple[RawActionV3, ...], tuple[RawTransitionV3, ...]]:
    kernel, witness = generate_stochastic_routing(seed=seed, **pre.ROUTING_SOURCE_SPEC)
    del witness
    catalogue, encode, layout_id = _routing_raw_interface(seed, kernel)
    rows: list[RawTransitionV3] = []
    field_counts: Counter[tuple[int, int]] = Counter()
    for episode in range(pre.ROUTING_SOURCE_EPISODES_PER_SEED):
        state = kernel.initial_distribution()[0][1]
        decision = 0
        while state.status is StochasticRoutingStatus.ACTIVE:
            legal = kernel.actions(state)
            action = min(
                legal,
                key=lambda item: (
                    sum(
                        field_counts[(field, value)]
                        for field, value in enumerate(catalogue[item.edge].fields)
                    ),
                    catalogue[item.edge].fields,
                    item.edge,
                ),
            )
            before = state
            outcome, tape = select_seeded_routing_outcome_v1(
                kernel.step(state, action),
                seed=seed,
                episode_index=episode,
                decision_index=decision,
            )
            state = outcome.next_state
            rows.append(
                RawTransitionV3(
                    occurrence,
                    len(rows),
                    encode(before),
                    tuple(item.edge for item in legal),
                    catalogue[action.edge],
                    encode(state),
                    tuple(item.edge for item in kernel.actions(state)),
                    tape,
                )
            )
            for field, value in enumerate(catalogue[action.edge].fields):
                field_counts[(field, value)] += 1
            decision += 1
            if len(rows) > pre.MAX_SOURCE_LABELS_PER_FAMILY:
                _fail("D01 source crossed its frozen label cap")
    frozen = tuple(rows)
    program = synthesize_template_free_program_v3(
        frozen,
        {occurrence: catalogue},
        program_domain=pre.FUTURE_DOMAINS["program"],
    )
    if program["vm_schema"] != ["INT", "INT", "STATUS_SUPPORT"]:
        _fail("D01 source selected the wrong typed AST")
    return (
        _raw_archive(
            "D01",
            seed,
            layout_id,
            catalogue,
            frozen,
            acquisition_rounds=pre.ROUTING_SOURCE_EPISODES_PER_SEED,
        ),
        catalogue,
        frozen,
    )


def _acquire_modular_source(
    occurrence: int, seed: int
) -> tuple[dict[str, Any], tuple[RawActionV3, ...], tuple[RawTransitionV3, ...]]:
    kernel, witness = generate_modular_walk(seed=seed, **pre.MODULAR_SOURCE_SPEC)
    del witness
    catalogue, encode, layout_id = _modular_raw_interface(seed, kernel)
    queue = deque([kernel.initial_distribution()[0][1]])
    seen = set(queue)
    rows: list[RawTransitionV3] = []
    rounds = 0
    while queue:
        state = queue.popleft()
        legal = kernel.actions(state)
        ranked = sorted(
            legal,
            key=lambda action: (
                sum(
                    row.action.fields == catalogue[action.edge].fields for row in rows
                ),
                catalogue[action.edge].fields,
                action.edge,
            ),
        )
        for action in ranked:
            successor = kernel.step(state, action)[0].next_state
            rows.append(
                RawTransitionV3(
                    occurrence,
                    len(rows),
                    encode(state),
                    tuple(item.edge for item in legal),
                    catalogue[action.edge],
                    encode(successor),
                    tuple(item.edge for item in kernel.actions(successor)),
                )
            )
            if (
                successor.status is ModularWalkStatus.ACTIVE
                and successor not in seen
            ):
                seen.add(successor)
                queue.append(successor)
            if len(rows) > pre.MAX_SOURCE_LABELS_PER_FAMILY:
                _fail("D02 source crossed its frozen label cap")
        rounds += 1
    frozen = tuple(rows)
    program = synthesize_template_free_program_v3(
        frozen,
        {occurrence: catalogue},
        program_domain=pre.FUTURE_DOMAINS["program"],
    )
    if program["vm_schema"] != ["INT", "INT", "INT", "STATUS"]:
        _fail("D02 source selected the wrong typed AST")
    return (
        _raw_archive(
            "D02", seed, layout_id, catalogue, frozen, acquisition_rounds=rounds
        ),
        catalogue,
        frozen,
    )


def _bind_lmb_target(
    program: Mapping[str, Any],
    state_vector: tuple[int, ...],
    legal_keys: tuple[int, ...],
    catalogue: tuple[RawActionV3, ...],
) -> dict[str, Any]:
    field_count = len(catalogue[0].fields)
    insertion = []
    for field in range(field_count):
        values = [row.fields[field] for row in catalogue]
        if len(set(values)) == len(values) and all(
            value > 0 and value & (value - 1) == 0 for value in values
        ):
            insertion.append((field, sum(values)))
    if len(insertion) != 1:
        _fail("D00 target did not identify one set-insertion field")
    insertion_field, full_set = insertion[0]
    blocker = [
        field
        for field in range(field_count)
        if field != insertion_field
        and {
            row.key for row in catalogue if row.fields[field] == 0
        }
        == set(legal_keys)
    ]
    if len(blocker) != 1:
        _fail("D00 target did not identify one blocker field")
    blocker_field = blocker[0]
    groups = [
        field
        for field in range(field_count)
        if field not in {insertion_field, blocker_field}
        and 1 < len({row.fields[field] for row in catalogue}) < len(catalogue)
    ]
    if len(groups) != 1:
        _fail("D00 target did not identify one partition field")
    group_field = groups[0]
    group_values = tuple(sorted({row.fields[group_field] for row in catalogue}))
    capacity = [value for value in state_vector if 0 < value < len(catalogue)]
    if len(capacity) != 1:
        _fail("D00 target did not identify one finite capacity")
    return {
        "vm_schema": program["vm_schema"],
        "action_roles": {
            "A0": insertion_field,
            "A1": blocker_field,
            "A2": group_field,
        },
        "relations": {
            "REL0": [[value, index] for index, value in enumerate(group_values)]
        },
        "numeric_literals": {
            "N0": 3,
            "N1": full_set,
            "N2": capacity[0],
        },
        "initial_vm_state": [0, [0] * len(group_values), 0],
        "all_target_registers_bound_without_ground_transition": True,
    }


def _equality_target_roles(
    state_vector: tuple[int, ...],
    legal_keys: tuple[int, ...],
    catalogue: tuple[RawActionV3, ...],
) -> tuple[int, int, int]:
    pairs = []
    for column, value in enumerate(state_vector):
        for field in range(len(catalogue[0].fields)):
            if {
                row.key for row in catalogue if row.fields[field] == value
            } == set(legal_keys):
                sources = {row.fields[field] for row in catalogue}
                for destination_field in range(len(catalogue[0].fields)):
                    if destination_field == field:
                        continue
                    destination_values = {
                        row.fields[destination_field] for row in catalogue
                    }
                    if len(destination_values - sources) == 1:
                        pairs.append((column, field, destination_field))
    if len(pairs) != 1:
        _fail("target equality relation is not unique")
    return pairs[0]


def _bind_routing_target(
    program: Mapping[str, Any],
    state_vector: tuple[int, ...],
    legal_keys: tuple[int, ...],
    catalogue: tuple[RawActionV3, ...],
) -> dict[str, Any]:
    node_column, source_field, destination_field = _equality_target_roles(
        state_vector, legal_keys, catalogue
    )
    remaining = [
        field
        for field in range(len(catalogue[0].fields))
        if field not in {source_field, destination_field}
    ]
    magnitudes = [
        field
        for field in remaining
        if all(0 < row.fields[field] <= 8 for row in catalogue)
    ]
    if len(magnitudes) != 1:
        _fail("D01 target magnitude field is not unique")
    magnitude_field = magnitudes[0]
    classes = [
        field
        for field in remaining
        if field != magnitude_field
        and 1 < len({row.fields[field] for row in catalogue}) < len(catalogue)
    ]
    if len(classes) != 1:
        _fail("D01 target class field is not unique")
    class_field = classes[0]
    source_values = {row.fields[source_field] for row in catalogue}
    goal = next(
        iter({row.fields[destination_field] for row in catalogue} - source_values)
    )
    capacity = [value for value in state_vector if 8 <= value < 100]
    if len(capacity) != 1:
        _fail("D01 target capacity is not unique")
    return {
        "vm_schema": program["vm_schema"],
        "action_roles": {
            "A0": source_field,
            "A1": destination_field,
            "A2": magnitude_field,
            "A3": class_field,
        },
        "relations": {"REL0": []},
        "numeric_literals": {"N0": goal, "N1": capacity[0]},
        "initial_vm_state": [state_vector[node_column], 0, 0],
        "all_target_registers_bound_without_ground_transition": True,
    }


def _base_modular_relation(program: Mapping[str, Any]) -> dict[int, int]:
    relations = []
    for binding in program["occurrence_bindings"]:
        relation = {key: value for key, value in binding["relations"]["REL0"]}
        relations.append(relation)
    if not relations or any(relation != relations[0] for relation in relations[1:]):
        _fail("D02 source relation did not agree across occurrences")
    if set(relations[0]) != set(pre.SHARED_MODE_TOKENS[:-1]):
        _fail("D02 source relation support changed")
    return relations[0]


def _bind_modular_target(
    program: Mapping[str, Any],
    state_vector: tuple[int, ...],
    legal_keys: tuple[int, ...],
    catalogue: tuple[RawActionV3, ...],
) -> dict[str, Any]:
    node_column, source_field, destination_field = _equality_target_roles(
        state_vector, legal_keys, catalogue
    )
    remaining = [
        field
        for field in range(len(catalogue[0].fields))
        if field not in {source_field, destination_field}
    ]
    mode_fields = [
        field
        for field in remaining
        if set(row.fields[field] for row in catalogue)
        <= set(pre.SHARED_MODE_TOKENS)
    ]
    if len(mode_fields) != 1:
        _fail("D02 target mode field is not unique")
    mode_field = mode_fields[0]
    goal = next(
        iter(
            {row.fields[destination_field] for row in catalogue}
            - {row.fields[source_field] for row in catalogue}
        )
    )
    if state_vector[4] != pre.MODULAR_TARGET_SPEC["modulus"]:
        _fail("D02 target fixed-layout modulus changed")
    if not 0 < state_vector[5] < state_vector[4]:
        _fail("D02 target goal residue changed")
    relation = _base_modular_relation(program)
    return {
        "vm_schema": program["vm_schema"],
        "state_roles": {"R0": 0, "R1": 1, "R2": 2, "R3": 3, "R4": 4},
        "action_roles": {
            "A0": source_field,
            "A1": destination_field,
            "A2": mode_field,
        },
        "relations": {"REL0": [[key, value] for key, value in sorted(relation.items())]},
        "numeric_literals": {
            "N0": state_vector[4],
            "N1": goal,
            "N2": state_vector[5],
        },
        "initial_vm_state": [state_vector[node_column], 0, 0, 0],
        "all_target_registers_except_heldout_relation_bound_without_ground_transition": True,
    }


def _direct_lmb_plan(
    kernel: LMBKernel,
    initial: LMBState,
    cache: dict[tuple[LMBState, int], LMBState],
) -> tuple[tuple[int, ...], int, int, int]:
    labels_before = len(cache)
    compute = 0
    peak = 0

    @lru_cache(maxsize=None)
    def solve(state: LMBState) -> tuple[int, ...] | None:
        nonlocal compute, peak
        if state.status is LMBStatus.SUCCESS:
            return ()
        if state.status is LMBStatus.FAILURE:
            return None
        ranked = []
        for action in kernel.actions(state):
            key = (state, action.tile)
            if key not in cache:
                cache[key] = kernel.step(state, action)[0].next_state
            successor = cache[key]
            compute += 1
            ranked.append(
                (
                    (
                        successor.status is LMBStatus.FAILURE,
                        sum(successor.buffer),
                        action.tile,
                    ),
                    action,
                    successor,
                )
            )
        for _score, action, successor in sorted(ranked):
            suffix = solve(successor)
            if suffix is not None:
                peak = max(peak, solve.cache_info().currsize)
                return (action.tile, *suffix)
        peak = max(peak, solve.cache_info().currsize)
        return None

    result = solve(initial)
    if result is None:
        _fail("strict D00 planner found no continuation")
    return result, len(cache) - labels_before, compute, peak


def _direct_routing_plan(
    kernel: StochasticRoutingKernel,
    initial: StochasticRoutingState,
    cache: dict[
        tuple[StochasticRoutingState, int], tuple[StochasticRoutingState, ...]
    ],
) -> tuple[tuple[int, ...], int, int, int]:
    labels_before = len(cache)
    compute = 0

    @lru_cache(maxsize=None)
    def solve(state: StochasticRoutingState) -> tuple[int, ...] | None:
        nonlocal compute
        if state.status is StochasticRoutingStatus.SUCCESS:
            return ()
        if state.status is StochasticRoutingStatus.FAILURE:
            return None
        ranked = []
        for action in kernel.actions(state):
            key = (state, action.edge)
            if key not in cache:
                cache[key] = tuple(
                    outcome.next_state for outcome in kernel.step(state, action)
                )
            support = cache[key]
            worst = max(support, key=lambda row: (row.resource, row.status.value))
            compute += 1
            ranked.append(
                (
                    (
                        worst.status is StochasticRoutingStatus.FAILURE,
                        worst.resource,
                        action.edge,
                    ),
                    action,
                    worst,
                )
            )
        for _score, action, successor in sorted(ranked):
            suffix = solve(successor)
            if suffix is not None:
                return (action.edge, *suffix)
        return None

    result = solve(initial)
    if result is None:
        _fail("strict D01 planner found no robust continuation")
    return result, len(cache) - labels_before, compute, solve.cache_info().currsize


def _direct_modular_plan(
    kernel: ModularWalkKernel,
    initial: ModularWalkState,
    cache: dict[tuple[ModularWalkState, int], ModularWalkState],
) -> tuple[tuple[int, ...], int, int, int]:
    labels_before = len(cache)
    compute = 0

    @lru_cache(maxsize=None)
    def solve(state: ModularWalkState) -> tuple[int, ...] | None:
        nonlocal compute
        if state.status is ModularWalkStatus.SUCCESS:
            return ()
        if state.status is ModularWalkStatus.FAILURE:
            return None
        ranked = []
        for action in kernel.actions(state):
            key = (state, action.edge)
            if key not in cache:
                cache[key] = kernel.step(state, action)[0].next_state
            successor = cache[key]
            compute += 1
            ranked.append(
                (
                    (
                        successor.status is ModularWalkStatus.FAILURE,
                        successor.residue,
                        action.edge,
                    ),
                    action,
                    successor,
                )
            )
        for _score, action, successor in sorted(ranked):
            suffix = solve(successor)
            if suffix is not None:
                return (action.edge, *suffix)
        return None

    result = solve(initial)
    if result is None:
        _fail("strict D02 planner found no continuation")
    return result, len(cache) - labels_before, compute, solve.cache_info().currsize


def _episode_document(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "episode_id": content_id(pre.FUTURE_DOMAINS["episode"], payload),
    }


def _lmb_target_episode(seed: int, program: Mapping[str, Any]) -> dict[str, Any]:
    kernel, witness = generate_solvable_lmb(seed=seed, **pre.LMB_TARGET_SPEC)
    del witness
    catalogue, encode, layout_id = _lmb_raw_interface(seed, kernel)
    state = kernel.initial_distribution()[0][1]
    binding = _bind_lmb_target(
        program,
        encode(state),
        tuple(action.tile for action in kernel.actions(state)),
        catalogue,
    )
    vm: tuple[Any, ...] = (0, tuple(0 for _ in range(kernel.type_count)), 0)
    strict_cache: dict[tuple[LMBState, int], LMBState] = {}
    decisions = []
    meta_compute = strict_compute = certificate_compute = strict_labels = 0
    meta_peak = strict_peak = 0
    while state.status is LMBStatus.ACTIVE:
        meta_plan, meta_events, meta_call_peak = plan_compiled_program_v3(
            program, vm, catalogue, binding
        )
        direct_plan, labels, direct_events, direct_call_peak = _direct_lmb_plan(
            kernel, state, strict_cache
        )
        if not meta_plan or meta_plan[0] != direct_plan[0]:
            _fail("D00 compiled and strict planners diverged")
        action_key = meta_plan[0]
        successor = kernel.step(state, LMBAction(action_key))[0].next_state
        predicted = execute_compiled_program_v3(
            program, vm, catalogue[action_key], binding
        )
        expected = (
            successor.removed_mask,
            successor.buffer,
            1
            if successor.status is LMBStatus.FAILURE
            else 2
            if successor.status is LMBStatus.SUCCESS
            else 0,
        )
        if predicted != expected:
            _fail("D00 compiled successor disagreed with execution")
        decisions.append(
            {
                "decision_index": len(decisions),
                "compiled_receding_plan": list(meta_plan[: pre.RECEDING_HORIZON]),
                "strict_receding_plan": list(direct_plan[: pre.RECEDING_HORIZON]),
                "selected_action_key": action_key,
                "certificate_status": "PASSED_COMPILED_AST_NO_GROUND_LABEL",
                "failed_certificate_id": None,
                "local_distinction": None,
                "structural_target_local_labels": 0,
                "strict_new_exact_context_labels": labels,
                "model_matches_execution": True,
            }
        )
        state = successor
        vm = predicted
        meta_compute += meta_events
        strict_compute += direct_events
        certificate_compute += len(meta_plan)
        strict_labels += labels
        meta_peak = max(meta_peak, meta_call_peak)
        strict_peak = max(strict_peak, direct_call_peak)
    if state.status is not LMBStatus.SUCCESS or vm[-1] != 2:
        _fail("D00 held-out episode did not terminate successfully")
    payload = {
        "schema": "acfqp.template_free_receding_episode.v48",
        "anonymous_family": "D00",
        "seed": seed,
        "opaque_layout_id": layout_id,
        "program_id": program["program_id"],
        "target_binding": binding,
        "decisions": decisions,
        "terminal_status": "SUCCESS",
        "execution_steps_per_arm": len(decisions),
        "structural_target_local_labels": 0,
        "strict_target_ground_labels": strict_labels,
        "structural_planning_compute_events": meta_compute,
        "strict_planning_compute_events": strict_compute,
        "certificate_compute_events": certificate_compute,
        "structural_peak_cache_entries": meta_peak,
        "strict_peak_cache_entries": strict_peak,
        "planner_consumed_compiled_ast_only": True,
    }
    return _episode_document(payload)


def _routing_target_episode(seed: int, program: Mapping[str, Any]) -> dict[str, Any]:
    kernel, witness = generate_stochastic_routing(seed=seed, **pre.ROUTING_TARGET_SPEC)
    del witness
    catalogue, encode, layout_id = _routing_raw_interface(seed, kernel)
    state = kernel.initial_distribution()[0][1]
    binding = _bind_routing_target(
        program,
        encode(state),
        tuple(action.edge for action in kernel.actions(state)),
        catalogue,
    )
    vm: tuple[Any, ...] = tuple(binding["initial_vm_state"])
    strict_cache: dict[
        tuple[StochasticRoutingState, int], tuple[StochasticRoutingState, ...]
    ] = {}
    decisions = []
    meta_compute = strict_compute = certificate_compute = strict_labels = 0
    meta_peak = strict_peak = 0
    while state.status is StochasticRoutingStatus.ACTIVE:
        meta_plan, meta_events, meta_call_peak = plan_compiled_program_v3(
            program, vm, catalogue, binding
        )
        direct_plan, labels, direct_events, direct_call_peak = _direct_routing_plan(
            kernel, state, strict_cache
        )
        if not meta_plan or meta_plan[0] != direct_plan[0]:
            _fail("D01 compiled and strict planners diverged")
        action_key = meta_plan[0]
        action = StochasticRoutingAction(action_key)
        selected, tape = select_seeded_routing_outcome_v1(
            kernel.step(state, action),
            seed=seed,
            episode_index=0,
            decision_index=len(decisions),
        )
        successor = selected.next_state
        delta = successor.resource - state.resource
        magnitude = catalogue[action_key].fields[binding["action_roles"]["A2"]]
        predicted = execute_compiled_program_v3(
            program,
            vm,
            catalogue[action_key],
            binding,
            support_choice="LOW" if delta == 0 else "WORST",
        )
        expected = (
            catalogue[action_key].fields[binding["action_roles"]["A1"]],
            successor.resource,
            1
            if successor.status is StochasticRoutingStatus.FAILURE
            else 2
            if successor.status is StochasticRoutingStatus.SUCCESS
            else 0,
        )
        if delta not in {0, magnitude} or predicted != expected:
            _fail("D01 compiled support disagreed with execution")
        decisions.append(
            {
                "decision_index": len(decisions),
                "compiled_receding_plan": list(meta_plan[: pre.RECEDING_HORIZON]),
                "strict_receding_plan": list(direct_plan[: pre.RECEDING_HORIZON]),
                "selected_action_key": action_key,
                "outcome_tape_sha256": tape,
                "certificate_status": "PASSED_ROBUST_SUPPORT_NO_GROUND_LABEL",
                "failed_certificate_id": None,
                "local_distinction": None,
                "structural_target_local_labels": 0,
                "strict_new_exact_context_labels": labels,
                "model_matches_execution": True,
            }
        )
        state = successor
        vm = predicted
        meta_compute += meta_events
        strict_compute += direct_events
        certificate_compute += len(meta_plan)
        strict_labels += labels
        meta_peak = max(meta_peak, meta_call_peak)
        strict_peak = max(strict_peak, direct_call_peak)
    if state.status is not StochasticRoutingStatus.SUCCESS or vm[-1] != 2:
        _fail("D01 held-out episode did not terminate successfully")
    payload = {
        "schema": "acfqp.template_free_receding_episode.v48",
        "anonymous_family": "D01",
        "seed": seed,
        "opaque_layout_id": layout_id,
        "program_id": program["program_id"],
        "target_binding": binding,
        "decisions": decisions,
        "terminal_status": "SUCCESS",
        "execution_steps_per_arm": len(decisions),
        "structural_target_local_labels": 0,
        "strict_target_ground_labels": strict_labels,
        "structural_planning_compute_events": meta_compute,
        "strict_planning_compute_events": strict_compute,
        "certificate_compute_events": certificate_compute,
        "structural_peak_cache_entries": meta_peak,
        "strict_peak_cache_entries": strict_peak,
        "planner_consumed_compiled_ast_only": True,
    }
    return _episode_document(payload)


def _failed_certificate(
    *,
    seed: int,
    decision: int,
    program_id: str,
    missing_value: int,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.template_free_failed_certificate.v48",
        "seed": seed,
        "decision_index": decision,
        "program_id": program_id,
        "status": "FAILED_MISSING_COMPILED_RELATION_SUPPORT",
        "missing_anonymous_relation_value": missing_value,
        "kernel_step_during_planning": False,
    }
    return {
        **payload,
        "certificate_id": content_id(pre.FUTURE_DOMAINS["support"], payload),
    }


def _modular_target_episode(
    seed: int,
    program: Mapping[str, Any],
    overlay: dict[int, int],
) -> dict[str, Any]:
    kernel, witness = generate_modular_walk(
        seed=seed,
        require_last_mode=True,
        **pre.MODULAR_TARGET_SPEC,
    )
    del witness
    catalogue, encode, layout_id = _modular_raw_interface(seed, kernel)
    state = kernel.initial_distribution()[0][1]
    binding = _bind_modular_target(
        program,
        encode(state),
        tuple(action.edge for action in kernel.actions(state)),
        catalogue,
    )
    vm: tuple[Any, ...] = tuple(binding["initial_vm_state"])
    strict_cache: dict[tuple[ModularWalkState, int], ModularWalkState] = {}
    decisions = []
    meta_compute = strict_compute = certificate_compute = strict_labels = 0
    meta_labels = 0
    meta_peak = strict_peak = 0
    while state.status is ModularWalkStatus.ACTIVE:
        legal = kernel.actions(state)
        base = _base_modular_relation(program)
        known = {**base, **overlay}
        missing_actions = [
            action
            for action in legal
            if action_relation_value_v3(binding, catalogue[action.edge]) not in known
        ]
        failed = None
        local = None
        if missing_actions:
            action = min(missing_actions, key=lambda row: row.edge)
            relation_value = action_relation_value_v3(
                binding, catalogue[action.edge]
            )
            failed = _failed_certificate(
                seed=seed,
                decision=len(decisions),
                program_id=program["program_id"],
                missing_value=relation_value,
            )
            queried = kernel.step(state, action)[0].next_state
            delta = (queried.residue - state.residue) % kernel.modulus
            if relation_value in overlay and overlay[relation_value] != delta:
                _fail("D02 immutable overlay relation changed")
            overlay[relation_value] = delta
            distinction_payload = {
                "schema": "acfqp.template_free_local_distinction.v48",
                "seed": seed,
                "decision_index": len(decisions),
                "program_id": program["program_id"],
                "failed_certificate_id": failed["certificate_id"],
                "action_key": action.edge,
                "anonymous_relation_value": relation_value,
                "observed_modular_delta": delta,
                "pre_vector": list(encode(state)),
                "post_vector": list(encode(queried)),
                "acquired_after_failed_certificate": True,
                "actual_episode_state_mutated_by_query": False,
            }
            local = {
                **distinction_payload,
                "distinction_id": content_id(
                    pre.FUTURE_DOMAINS["distinction"], distinction_payload
                ),
            }
            meta_labels += 1
        meta_plan, meta_events, meta_call_peak = plan_compiled_program_v3(
            program,
            vm,
            catalogue,
            binding,
            relation_overlay=overlay,
        )
        direct_plan, labels, direct_events, direct_call_peak = _direct_modular_plan(
            kernel, state, strict_cache
        )
        if not meta_plan or meta_plan[0] != direct_plan[0]:
            _fail("D02 compiled and strict planners diverged")
        action_key = meta_plan[0]
        successor = kernel.step(state, ModularWalkAction(action_key))[0].next_state
        predicted = execute_compiled_program_v3(
            program,
            vm,
            catalogue[action_key],
            binding,
            relation_overlay=overlay,
        )
        expected = (
            catalogue[action_key].fields[binding["action_roles"]["A1"]],
            successor.residue,
            successor.steps,
            1
            if successor.status is ModularWalkStatus.FAILURE
            else 2
            if successor.status is ModularWalkStatus.SUCCESS
            else 0,
        )
        if predicted != expected:
            _fail("D02 compiled successor disagreed with execution")
        decisions.append(
            {
                "decision_index": len(decisions),
                "compiled_receding_plan": list(meta_plan[: pre.RECEDING_HORIZON]),
                "strict_receding_plan": list(direct_plan[: pre.RECEDING_HORIZON]),
                "selected_action_key": action_key,
                "initial_certificate": failed
                or {
                    "status": "PASSED_COMPILED_RELATION_SUPPORT",
                    "certificate_id": None,
                },
                "local_distinction": local,
                "final_certificate_status": "CERTIFIED_AFTER_LOCAL_DISTINCTION"
                if local
                else "PASSED_COMPILED_RELATION_SUPPORT",
                "replanned_after_local_distinction": local is not None,
                "structural_target_local_labels": int(local is not None),
                "strict_new_exact_context_labels": labels,
                "model_matches_execution": True,
            }
        )
        state = successor
        vm = predicted
        meta_compute += meta_events
        strict_compute += direct_events
        certificate_compute += len(meta_plan) + int(failed is not None)
        strict_labels += labels
        meta_peak = max(meta_peak, meta_call_peak)
        strict_peak = max(strict_peak, direct_call_peak)
    if state.status is not ModularWalkStatus.SUCCESS or vm[-1] != 2:
        _fail("D02 held-out episode did not terminate successfully")
    payload = {
        "schema": "acfqp.template_free_receding_episode.v48",
        "anonymous_family": "D02",
        "seed": seed,
        "opaque_layout_id": layout_id,
        "program_id": program["program_id"],
        "target_binding": binding,
        "decisions": decisions,
        "terminal_status": "SUCCESS",
        "execution_steps_per_arm": len(decisions),
        "structural_target_local_labels": meta_labels,
        "strict_target_ground_labels": strict_labels,
        "structural_planning_compute_events": meta_compute,
        "strict_planning_compute_events": strict_compute,
        "certificate_compute_events": certificate_compute,
        "structural_peak_cache_entries": meta_peak,
        "strict_peak_cache_entries": strict_peak,
        "planner_consumed_compiled_ast_only": True,
        "overlay_entry_count_after_episode": len(overlay),
    }
    return _episode_document(payload)


def _routing_partial_model(
    program: Mapping[str, Any], rows: tuple[RawTransitionV3, ...]
) -> dict[str, Any]:
    support: dict[int, Counter[int]] = {}
    occurrence_binding = {
        row["occurrence"]: row for row in program["occurrence_bindings"]
    }
    for row in rows:
        binding = occurrence_binding[row.occurrence]
        magnitude = row.action.fields[binding["action_roles"]["A2"]]
        resource_column = binding["state_roles"]["R1"]
        delta = row.post[resource_column] - row.pre[resource_column]
        support.setdefault(magnitude, Counter())[delta] += 1
    rows_document = []
    for magnitude, counts in sorted(support.items()):
        total = sum(counts.values())
        rows_document.append(
            {
                "anonymous_magnitude": magnitude,
                "observed_support": sorted(counts),
                "empirical_rational": [
                    {
                        "delta": delta,
                        "probability": Fraction(count, total),
                    }
                    for delta, count in sorted(counts.items())
                ],
                "conservative_probability_interval": [0, 1],
            }
        )
    payload = {
        "schema": "acfqp.template_free_partial_dynamics.v48",
        "program_id": program["program_id"],
        "support_rows": rows_document,
        "support_complete_on_registered_source": all(
            len(row["observed_support"]) == 2 for row in rows_document
        ),
        "exact_probability_authority": False,
        "planner_probability_input": "NONE_ROBUST_WORST_SUPPORT",
    }
    if not payload["support_complete_on_registered_source"]:
        _fail("D01 registered source did not close finite support")
    return {
        **payload,
        "partial_model_id": content_id(pre.FUTURE_DOMAINS["partial"], payload),
    }


def _document() -> dict[str, Any]:
    registration = pre.verify_template_free_preregistration_v48(
        pre.freeze_template_free_preregistration_v48()
    )
    archives = []
    family_rows: dict[str, list[RawTransitionV3]] = {
        "D00": [],
        "D01": [],
        "D02": [],
    }
    family_catalogues: dict[str, dict[int, tuple[RawActionV3, ...]]] = {
        "D00": {},
        "D01": {},
        "D02": {},
    }
    acquisition_functions = (
        ("D00", pre.LMB_SOURCE_SEEDS, 1000, _acquire_lmb_source),
        ("D01", pre.ROUTING_SOURCE_SEEDS, 2000, _acquire_routing_source),
        ("D02", pre.MODULAR_SOURCE_SEEDS, 3000, _acquire_modular_source),
    )
    for family, seeds, start, acquire in acquisition_functions:
        for occurrence, seed in enumerate(seeds, start):
            archive, catalogue, rows = acquire(occurrence, seed)
            archives.append(archive)
            family_catalogues[family][occurrence] = catalogue
            family_rows[family].extend(rows)
        if len(family_rows[family]) > pre.MAX_SOURCE_LABELS_PER_FAMILY:
            _fail(f"{family} aggregate source labels crossed the frozen cap")

    programs = []
    by_family: dict[str, dict[str, Any]] = {}
    for family in ("D00", "D01", "D02"):
        program = synthesize_template_free_program_v3(
            tuple(family_rows[family]),
            family_catalogues[family],
            program_domain=pre.FUTURE_DOMAINS["program"],
        )
        by_family[family] = program
        programs.append(program)
    if len({program["selected_clause_set_sha256"] for program in programs}) != 3:
        _fail("V48 did not synthesize three distinct clause compositions")
    if any(program["whole_program_template_count"] != 0 for program in programs):
        _fail("V48 program unexpectedly used a whole-program template")

    supports = [
        derive_dependency_support_v3(
            program, support_domain=pre.FUTURE_DOMAINS["support"]
        )
        for program in programs
    ]
    partial = _routing_partial_model(
        by_family["D01"], tuple(family_rows["D01"])
    )

    episodes = [
        _lmb_target_episode(seed, by_family["D00"])
        for seed in pre.LMB_TARGET_SEEDS
    ] + [
        _routing_target_episode(seed, by_family["D01"])
        for seed in pre.ROUTING_TARGET_SEEDS
    ]
    overlay: dict[int, int] = {}
    modular_episodes = []
    for seed in pre.MODULAR_TARGET_SEEDS:
        modular_episodes.append(
            _modular_target_episode(seed, by_family["D02"], overlay)
        )
    episodes.extend(modular_episodes)
    if overlay != {pre.SHARED_MODE_TOKENS[-1]: pre.MODULAR_TARGET_SPEC["mode_deltas"][-1]}:
        _fail("D02 immutable overlay did not close to the registered relation")

    source_labels = sum(len(rows) for rows in family_rows.values())
    target_meta_labels = sum(
        episode["structural_target_local_labels"] for episode in episodes
    )
    strict_labels = sum(
        episode["strict_target_ground_labels"] for episode in episodes
    )
    if target_meta_labels != 1:
        _fail("D02 held-out relation was not acquired exactly once")
    if source_labels + target_meta_labels >= strict_labels:
        _fail("V48 registered label-axis sample tax did not decrease")
    cumulative_meta = source_labels
    cumulative_strict = 0
    break_even = None
    for index, episode in enumerate(episodes, 1):
        cumulative_meta += episode["structural_target_local_labels"]
        cumulative_strict += episode["strict_target_ground_labels"]
        if break_even is None and cumulative_meta < cumulative_strict:
            break_even = index
    if break_even is None:
        _fail("V48 diagnostic label break-even was not reached")

    overlay_rows = [
        {"anonymous_relation_value": key, "observed_delta": value}
        for key, value in sorted(overlay.items())
    ]
    acquisition_payload = {
        "schema": "acfqp.template_free_adaptive_acquisition.v48",
        "source_label_counts": {
            family: len(rows) for family, rows in family_rows.items()
        },
        "target_failed_certificate_count": sum(
            decision["local_distinction"] is not None
            for episode in episodes
            for decision in episode["decisions"]
        ),
        "target_local_ground_label_count": target_meta_labels,
        "immutable_overlay_rows": overlay_rows,
        "overlay_reused_occurrence_count": len(pre.MODULAR_TARGET_SEEDS) - 1,
        "every_local_label_follows_failed_certificate": all(
            decision["local_distinction"] is None
            or decision["local_distinction"]["acquired_after_failed_certificate"]
            for episode in episodes
            for decision in episode["decisions"]
        ),
    }
    acquisition = {
        **acquisition_payload,
        "adaptive_acquisition_id": content_id(
            pre.FUTURE_DOMAINS["acquisition"], acquisition_payload
        ),
    }
    sample_payload = {
        "schema": "acfqp.template_free_sample_tax.v48",
        "offline_source_labels": source_labels,
        "structural_target_local_labels": target_meta_labels,
        "structural_total_labels_including_offline": source_labels
        + target_meta_labels,
        "strict_target_ground_labels": strict_labels,
        "registered_label_saving": strict_labels
        - source_labels
        - target_meta_labels,
        "diagnostic_episode_break_even": break_even,
        "positive_registered_condition_passed": True,
        "broad_cross_domain_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_N_break_even": None,
    }
    sample = {
        **sample_payload,
        "sample_tax_id": content_id(
            pre.FUTURE_DOMAINS["sample_tax"], sample_payload
        ),
    }
    accounting = {
        "offline_source_labels": source_labels,
        "target_local_labels_structural": target_meta_labels,
        "target_ground_labels_strict": strict_labels,
        "source_environment_steps": source_labels,
        "target_execution_steps_structural": sum(
            episode["execution_steps_per_arm"] for episode in episodes
        ),
        "target_execution_steps_strict": sum(
            episode["execution_steps_per_arm"] for episode in episodes
        ),
        "synthesis_compute_events": sum(
            candidate["atomic_clause_evaluations"]
            for program in programs
            for candidate in program["candidate_evaluations"]
        ),
        "planning_compute_events_structural": sum(
            episode["structural_planning_compute_events"] for episode in episodes
        ),
        "planning_compute_events_strict": sum(
            episode["strict_planning_compute_events"] for episode in episodes
        ),
        "certificate_compute_events": sum(
            episode["certificate_compute_events"] for episode in episodes
        ),
        "peak_program_cache_entries": max(
            max(episode["structural_peak_cache_entries"] for episode in episodes),
            max(episode["strict_peak_cache_entries"] for episode in episodes),
        ),
        "labels_execution_synthesis_planning_certificate_and_peak_kept_separate": True,
    }
    ood_payload = {
        "schema": "acfqp.template_free_ood_rejection.v48",
        "input_schema": "OPAQUE_CONTINUOUS_REAL_VECTOR",
        "registered_integer_grammar_compatible": False,
        "decision": "OOD_SCHEMA_REJECTED_NO_TRANSFER",
        "prior_access_count": 0,
        "environment_outcome_count": 0,
        "environment_step_count": 0,
    }
    ood = {
        **ood_payload,
        "ood_rejection_id": content_id(pre.FUTURE_DOMAINS["ood"], ood_payload),
    }
    payload = {
        "schema": "acfqp.template_free_cross_domain_campaign.v48",
        "schema_version": SCHEMA_VERSION,
        "preregistration_id": registration.preregistration_id,
        "v47_failure_and_v47r1_success_preserved": True,
        "source_archives": archives,
        "programs": programs,
        "dependency_support_signatures": supports,
        "stochastic_partial_model": partial,
        "adaptive_acquisition": acquisition,
        "episodes": episodes,
        "sample_tax": sample,
        "accounting_axes": accounting,
        "strict_ood_control": ood,
        "one_synthesizer_three_distinct_programs": True,
        "whole_program_template_count": 0,
        "historical_template_opcode_names_in_programs": [],
        "planner_consumed_compiled_ast_only": True,
        "all_local_ground_labels_follow_failed_certificates": True,
        "successful_certificate_local_ground_label_count": 0,
        "D02_overlay_acquired_once_and_reused": True,
        "exact_stochastic_probability_authority": False,
        "producer_free_verification_status": "NOT_RUN",
        "broad_world_model_synthesis_claimed": False,
        "broad_cross_domain_sample_efficiency_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **payload,
        "template_free_campaign_id": content_id(
            pre.FUTURE_DOMAINS["campaign"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TemplateFreeCampaignV48:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V48 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V48 campaign bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "template_free_campaign_id"
        }
        if (
            document.get("template_free_campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload)
            != self.campaign_id
        ):
            _fail("V48 campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def freeze_template_free_campaign_v48() -> TemplateFreeCampaignV48:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["template_free_campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V48 campaign changed")
    return TemplateFreeCampaignV48(_ISSUER, raw, identity)


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "TemplateFreeCampaignV48",
    "freeze_template_free_campaign_v48",
)
