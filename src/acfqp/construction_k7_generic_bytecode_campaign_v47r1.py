"""Fresh V47r1 two-domain generic-bytecode and sample-tax campaign."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
import hashlib
import random
from typing import Any, Callable, Mapping, NoReturn

from acfqp import construction_k7_generic_bytecode_successor_preregistration_v47r1 as pre
from acfqp.domains.matching_buffer import (
    LMBAction,
    LMBKernel,
    LMBState,
    LMBStatus,
    generate_solvable_lmb,
)
from acfqp.domains.stochastic_routing import (
    StochasticRoutingAction,
    StochasticRoutingKernel,
    StochasticRoutingState,
    StochasticRoutingStatus,
    generate_stochastic_routing,
    select_seeded_routing_outcome_v1,
)
from acfqp.generic_bytecode_world_model_v2 import (
    GenericBytecodeWorldModelV1Error,
    RawActionV1,
    RawTransitionV1,
    bind_scalar_categorical_target_v2,
    bind_vector_set_target_v1,
    derive_compiled_dependency_support_v2,
    execute_scalar_categorical_bytecode_v2,
    execute_vector_set_bytecode_v2,
    plan_scalar_categorical_v1,
    plan_vector_set_v1,
    synthesize_generic_program_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = "47.1.0"
CAMPAIGN_ID = "ec34a6a4d77e5ea8f1bb5483f0b78eaa0168a1aae302dad2cb9cc0475679fe7a"
EXPECTED_CANONICAL_BYTE_COUNT = 292282
EXPECTED_CANONICAL_SHA256 = "8e9cff93a23fa66d94b11120482c12c6a6142723085c679cb3fbc8c82e3bbb5d"


class ConstructionK7GenericBytecodeCampaignV47R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7GenericBytecodeCampaignV47R1Error(message)


def _token(seed: int, namespace: int, value: int) -> int:
    return seed * 10_000_000 + namespace * 10_000 + value


def _permutation(width: int, seed: int, salt: int) -> tuple[int, ...]:
    values = list(range(width))
    random.Random(seed ^ salt).shuffle(values)
    return tuple(values)


def _lmb_adapter(
    seed: int, kernel: LMBKernel
) -> tuple[tuple[RawActionV1, ...], Callable[[LMBState], tuple[int, ...]], str]:
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
            RawActionV1(tile, tuple(semantic[index] for index in field_order))
        )

    def encode(state: LMBState) -> tuple[int, ...]:
        semantic = (
            state.removed_mask,
            *state.buffer,
            kernel.capacity,
            status_tokens[state.status],
        )
        return tuple(semantic[index] for index in state_order)

    layout_payload = {
        "state_width": kernel.type_count + 3,
        "action_field_width": 4,
        "state_permutation_sha256": hashlib.sha256(bytes(state_order)).hexdigest(),
        "action_permutation_sha256": hashlib.sha256(bytes(field_order)).hexdigest(),
        "semantic_role_names_serialized": False,
    }
    return (
        tuple(catalogue),
        encode,
        content_id(pre.FUTURE_DOMAINS["observation"], layout_payload),
    )


def _routing_adapter(
    seed: int, kernel: StochasticRoutingKernel
) -> tuple[
    tuple[RawActionV1, ...],
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
            RawActionV1(
                edge_index, tuple(semantic[index] for index in field_order)
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

    layout_payload = {
        "state_width": 4,
        "action_field_width": 5,
        "state_permutation_sha256": hashlib.sha256(bytes(state_order)).hexdigest(),
        "action_permutation_sha256": hashlib.sha256(bytes(field_order)).hexdigest(),
        "semantic_role_names_serialized": False,
    }
    return (
        tuple(catalogue),
        encode,
        content_id(pre.FUTURE_DOMAINS["observation"], layout_payload),
    )


def _raw_archive(
    family: str,
    seed: int,
    layout_id: str,
    catalogue: tuple[RawActionV1, ...],
    rows: tuple[RawTransitionV1, ...],
    *,
    synthesis_probe_count: int,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.generic_raw_observation.v47r1",
        "anonymous_family": family,
        "seed": seed,
        "opaque_layout_id": layout_id,
        "anonymous_action_catalogue": [row.to_document() for row in catalogue],
        "raw_transitions": [row.to_document() for row in rows],
        "source_transition_labels": len(rows),
        "source_environment_steps": len(rows),
        "synthesis_probe_count": synthesis_probe_count,
        "generation_witness_accessed": False,
        "semantic_role_names_available_to_synthesizer": False,
    }
    return {
        **payload,
        "raw_observation_id": content_id(pre.FUTURE_DOMAINS["observation"], payload),
    }


def _acquire_lmb_source(
    occurrence: int, seed: int
) -> tuple[dict[str, Any], tuple[RawActionV1, ...], tuple[RawTransitionV1, ...]]:
    kernel, witness = generate_solvable_lmb(seed=seed, **pre.LMB_SOURCE_SPEC)
    del witness
    catalogue, encode, layout_id = _lmb_adapter(seed, kernel)
    repeated_fields = []
    for field_index in range(len(catalogue[0].fields)):
        counts = Counter(row.fields[field_index] for row in catalogue)
        if len(counts) > 1 and len(counts) < len(catalogue) and min(counts.values()) >= 3:
            repeated_fields.append((len(counts), field_index))
    if not repeated_fields:
        _fail("witness-blind catalogue has no repeated anonymous field")
    exploration_field = min(repeated_fields)[1]
    rows: list[RawTransitionV1] = []
    probe_count = 0
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
                RawTransitionV1(
                    occurrence,
                    len(rows),
                    encode(before),
                    tuple(item.tile for item in legal),
                    catalogue[action.tile],
                    encode(state),
                    tuple(item.tile for item in kernel.actions(state)),
                )
            )
            if len(rows) > pre.LMB_MAX_SOURCE_LABELS:
                _fail("fresh LMB source crossed its registered label cap")
        probe_count += 1
        try:
            candidate = synthesize_generic_program_v1(
                tuple(rows),
                {occurrence: catalogue},
                program_domain=pre.FUTURE_DOMAINS["program"],
            )
        except GenericBytecodeWorldModelV1Error:
            continue
        if candidate["selected_template_opcode"] == "T00":
            fitted = True
            break
    if not fitted:
        _fail("fresh LMB source did not identify the generic T00 program")
    frozen_rows = tuple(rows)
    return (
        _raw_archive(
            "D00",
            seed,
            layout_id,
            catalogue,
            frozen_rows,
            synthesis_probe_count=probe_count,
        ),
        catalogue,
        frozen_rows,
    )


def _acquire_routing_source(
    occurrence: int, seed: int
) -> tuple[dict[str, Any], tuple[RawActionV1, ...], tuple[RawTransitionV1, ...]]:
    kernel, witness = generate_stochastic_routing(seed=seed, **pre.ROUTING_SOURCE_SPEC)
    del witness
    catalogue, encode, layout_id = _routing_adapter(seed, kernel)
    rows: list[RawTransitionV1] = []
    field_value_counts: Counter[tuple[int, int]] = Counter()
    for episode in range(pre.ROUTING_SOURCE_EPISODES_PER_SEED):
        state = kernel.initial_distribution()[0][1]
        decision = 0
        while state.status is StochasticRoutingStatus.ACTIVE:
            legal = kernel.actions(state)
            action = min(
                legal,
                key=lambda item: (
                    sum(
                        field_value_counts[(field, value)]
                        for field, value in enumerate(catalogue[item.edge].fields)
                    ),
                    catalogue[item.edge].fields,
                    item.edge,
                ),
            )
            before = state
            selected, tape = select_seeded_routing_outcome_v1(
                kernel.step(state, action),
                seed=seed,
                episode_index=episode,
                decision_index=decision,
            )
            state = selected.next_state
            rows.append(
                RawTransitionV1(
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
                field_value_counts[(field, value)] += 1
            decision += 1
            if len(rows) > pre.ROUTING_MAX_SOURCE_LABELS:
                _fail("fresh stochastic source crossed its registered label cap")
    frozen_rows = tuple(rows)
    candidate = synthesize_generic_program_v1(
        frozen_rows,
        {occurrence: catalogue},
        program_domain=pre.FUTURE_DOMAINS["program"],
    )
    if candidate["selected_template_opcode"] != "T01":
        _fail("fresh stochastic source did not identify the generic T01 program")
    return (
        _raw_archive(
            "D01",
            seed,
            layout_id,
            catalogue,
            frozen_rows,
            synthesis_probe_count=1,
        ),
        catalogue,
        frozen_rows,
    )


def _direct_lmb_plan(
    kernel: LMBKernel,
    initial: LMBState,
    query_cache: dict[tuple[LMBState, int], LMBState],
) -> tuple[tuple[int, ...], int, int, int]:
    labels_before = len(query_cache)
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
            if key not in query_cache:
                query_cache[key] = kernel.step(state, action)[0].next_state
            successor = query_cache[key]
            compute += 1
            ranked.append(
                (
                    (
                        -int(sum(successor.buffer) < sum(state.buffer)),
                        sum(successor.buffer),
                        action.tile,
                    ),
                    action.tile,
                    successor,
                )
            )
        for _rank, action_key, successor in sorted(ranked):
            suffix = solve(successor)
            if suffix is not None:
                peak = max(peak, solve.cache_info().currsize)
                return (action_key, *suffix)
        peak = max(peak, solve.cache_info().currsize)
        return None

    plan = solve(initial)
    if plan is None:
        _fail("strict direct LMB planner found no continuation")
    return plan, len(query_cache) - labels_before, compute, peak


def _direct_routing_plan(
    kernel: StochasticRoutingKernel,
    initial: StochasticRoutingState,
    query_cache: dict[tuple[StochasticRoutingState, int], tuple[Any, ...]],
) -> tuple[tuple[int, ...], int, int, int]:
    labels_before = len(query_cache)
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
            if key not in query_cache:
                query_cache[key] = kernel.step(state, action)
            outcomes = query_cache[key]
            worst = max(outcomes, key=lambda row: row.next_state.resource).next_state
            compute += 1
            ranked.append(
                (
                    (
                        worst.status is StochasticRoutingStatus.FAILURE,
                        worst.resource,
                        action.edge,
                    ),
                    action.edge,
                    worst,
                )
            )
        for _rank, action_key, successor in sorted(ranked):
            suffix = solve(successor)
            if suffix is not None:
                return (action_key, *suffix)
        return None

    plan = solve(initial)
    if plan is None:
        _fail("strict direct stochastic planner found no robust continuation")
    return plan, len(query_cache) - labels_before, compute, solve.cache_info().currsize


def _lmb_target_episode(seed: int, program: Mapping[str, Any]) -> dict[str, Any]:
    kernel, witness = generate_solvable_lmb(seed=seed, **pre.LMB_TARGET_SPEC)
    del witness
    catalogue, encode, layout_id = _lmb_adapter(seed, kernel)
    state = kernel.initial_distribution()[0][1]
    initial_vector = encode(state)
    binding = bind_vector_set_target_v1(
        initial_vector,
        tuple(action.tile for action in kernel.actions(state)),
        catalogue,
    )
    if program["selected_template_opcode"] != binding["template_opcode"]:
        _fail("fresh D00 target did not bind the compiled template")
    vm = (
        binding["initial_vm_state"]["q0"],
        tuple(binding["initial_vm_state"]["q1"]),
        binding["initial_vm_state"]["q2"],
    )
    direct_cache: dict[tuple[LMBState, int], LMBState] = {}
    decisions = []
    meta_planning = strict_planning = certificate_compute = 0
    meta_peak = strict_peak = 0
    strict_labels = 0
    while state.status is LMBStatus.ACTIVE:
        meta_plan, meta_compute, meta_call_peak = plan_vector_set_v1(vm, catalogue, binding)
        direct_plan, new_labels, direct_compute, direct_call_peak = _direct_lmb_plan(
            kernel, state, direct_cache
        )
        if not meta_plan or meta_plan[0] != direct_plan[0]:
            _fail("compiled and strict D00 planners selected different actions")
        simulated = vm
        for action_key in meta_plan:
            simulated = execute_vector_set_bytecode_v2(
                simulated, catalogue[action_key], binding
            )
            certificate_compute += 1
            if simulated[2] == 1:
                _fail("compiled D00 certificate entered failure")
        if simulated[2] != 2:
            _fail("compiled D00 certificate did not prove terminal success")
        action_key = meta_plan[0]
        before_vector = encode(state)
        state = kernel.step(state, LMBAction(action_key))[0].next_state
        vm = execute_vector_set_bytecode_v2(vm, catalogue[action_key], binding)
        if (state.status is LMBStatus.FAILURE) != (vm[2] == 1):
            _fail("compiled D00 VM diverged from actual execution")
        decisions.append(
            {
                "decision_index": len(decisions),
                "pre_vector": list(before_vector),
                "meta_receding_plan": list(meta_plan[: pre.RECEDING_HORIZON]),
                "strict_receding_plan": list(direct_plan[: pre.RECEDING_HORIZON]),
                "selected_action": catalogue[action_key].to_document(),
                "post_vector": list(encode(state)),
                "certificate_status": "PASSED_NO_GROUND_LABEL",
                "meta_local_ground_labels": 0,
                "strict_new_exact_context_labels": new_labels,
            }
        )
        meta_planning += meta_compute
        strict_planning += direct_compute
        strict_labels += new_labels
        meta_peak = max(meta_peak, meta_call_peak)
        strict_peak = max(strict_peak, direct_call_peak)
    if state.status is not LMBStatus.SUCCESS or vm[2] != 2:
        _fail("fresh D00 target did not complete successfully")
    payload = {
        "schema": "acfqp.generic_receding_episode.v47r1",
        "anonymous_family": "D00",
        "seed": seed,
        "opaque_layout_id": layout_id,
        "program_id": program["program_id"],
        "initial_vector": list(initial_vector),
        "anonymous_action_catalogue": [row.to_document() for row in catalogue],
        "target_binding": binding,
        "decisions": decisions,
        "terminal_status": "SUCCESS",
        "execution_steps_per_arm": len(decisions),
        "meta_target_local_labels": 0,
        "strict_target_ground_labels": strict_labels,
        "meta_planning_compute_events": meta_planning,
        "strict_planning_compute_events": strict_planning,
        "certificate_compute_events": certificate_compute,
        "meta_peak_cache_entries": meta_peak,
        "strict_peak_cache_entries": strict_peak,
        "typed_adapter_abstract_state_consumed_by_planner": False,
    }
    return {
        **payload,
        "episode_id": content_id(pre.FUTURE_DOMAINS["episode"], payload),
    }


def _routing_target_episode(seed: int, program: Mapping[str, Any]) -> dict[str, Any]:
    kernel, witness = generate_stochastic_routing(seed=seed, **pre.ROUTING_TARGET_SPEC)
    del witness
    catalogue, encode, layout_id = _routing_adapter(seed, kernel)
    state = kernel.initial_distribution()[0][1]
    initial_vector = encode(state)
    binding = bind_scalar_categorical_target_v2(
        initial_vector,
        tuple(action.edge for action in kernel.actions(state)),
        catalogue,
    )
    if program["selected_template_opcode"] != binding["template_opcode"]:
        _fail("fresh D01 target did not bind the compiled template")
    vm = (
        binding["initial_vm_state"]["q0"],
        binding["initial_vm_state"]["q1"],
        binding["initial_vm_state"]["q2"],
    )
    direct_cache: dict[tuple[StochasticRoutingState, int], tuple[Any, ...]] = {}
    decisions = []
    meta_planning = strict_planning = certificate_compute = 0
    meta_peak = strict_peak = strict_labels = 0
    while state.status is StochasticRoutingStatus.ACTIVE:
        meta_plan, meta_compute, meta_call_peak = plan_scalar_categorical_v1(
            vm, catalogue, binding
        )
        direct_plan, new_labels, direct_compute, direct_call_peak = _direct_routing_plan(
            kernel, state, direct_cache
        )
        if not meta_plan or meta_plan[0] != direct_plan[0]:
            _fail("compiled and strict D01 planners selected different actions")
        certificate_compute += len(meta_plan)
        action_key = meta_plan[0]
        action = StochasticRoutingAction(action_key)
        before = state
        before_vector = encode(before)
        selected, tape = select_seeded_routing_outcome_v1(
            kernel.step(state, action),
            seed=seed,
            episode_index=0,
            decision_index=len(decisions),
        )
        state = selected.next_state
        post_vector = encode(state)
        vm = execute_scalar_categorical_bytecode_v2(
            vm,
            catalogue[action_key],
            binding,
            pre_vector=before_vector,
            post_vector=post_vector,
        )
        if (state.status is StochasticRoutingStatus.FAILURE) != (vm[2] == 1):
            _fail("compiled D01 VM diverged from actual residual")
        decisions.append(
            {
                "decision_index": len(decisions),
                "pre_vector": list(before_vector),
                "meta_receding_plan": list(meta_plan[: pre.RECEDING_HORIZON]),
                "strict_receding_plan": list(direct_plan[: pre.RECEDING_HORIZON]),
                "selected_action": catalogue[action_key].to_document(),
                "post_vector": list(post_vector),
                "outcome_tape_sha256": tape,
                "certificate_status": "PASSED_ROBUST_SUPPORT_NO_GROUND_LABEL",
                "meta_local_ground_labels": 0,
                "strict_new_exact_context_labels": new_labels,
            }
        )
        meta_planning += meta_compute
        strict_planning += direct_compute
        strict_labels += new_labels
        meta_peak = max(meta_peak, meta_call_peak)
        strict_peak = max(strict_peak, direct_call_peak)
    if state.status is not StochasticRoutingStatus.SUCCESS or vm[2] != 2:
        _fail("fresh D01 target did not complete robust execution")
    payload = {
        "schema": "acfqp.generic_receding_episode.v47r1",
        "anonymous_family": "D01",
        "seed": seed,
        "opaque_layout_id": layout_id,
        "program_id": program["program_id"],
        "initial_vector": list(initial_vector),
        "anonymous_action_catalogue": [row.to_document() for row in catalogue],
        "target_binding": binding,
        "decisions": decisions,
        "terminal_status": "SUCCESS",
        "execution_steps_per_arm": len(decisions),
        "meta_target_local_labels": 0,
        "strict_target_ground_labels": strict_labels,
        "meta_planning_compute_events": meta_planning,
        "strict_planning_compute_events": strict_planning,
        "certificate_compute_events": certificate_compute,
        "meta_peak_cache_entries": meta_peak,
        "strict_peak_cache_entries": strict_peak,
        "typed_adapter_abstract_state_consumed_by_planner": False,
    }
    return {
        **payload,
        "episode_id": content_id(pre.FUTURE_DOMAINS["episode"], payload),
    }


def _partial_model(
    program: Mapping[str, Any],
    catalogues: Mapping[int, tuple[RawActionV1, ...]],
    rows: tuple[RawTransitionV1, ...],
) -> dict[str, Any]:
    bindings = {
        row["occurrence"]: row for row in program["occurrence_bindings"]
    }
    counts: dict[int, Counter[int]] = {}
    occurrence_sets: dict[int, set[int]] = {}
    for row in rows:
        binding = bindings[row.occurrence]
        state_roles = binding["state_roles"]
        action_roles = binding["action_roles"]
        magnitude = row.action.fields[action_roles["A2"]]
        delta = row.post[state_roles["R1"]] - row.pre[state_roles["R1"]]
        counts.setdefault(magnitude, Counter())[delta] += 1
        occurrence_sets.setdefault(magnitude, set()).add(row.occurrence)
    support_rows = []
    for magnitude, observed in sorted(counts.items()):
        total = sum(observed.values())
        support_rows.append(
            {
                "anonymous_magnitude": magnitude,
                "source_occurrence_count": len(occurrence_sets[magnitude]),
                "observed_support": sorted(observed),
                "empirical_rational": [
                    {
                        "delta": delta,
                        "empirical_probability": {
                            "numerator": Fraction(count, total).numerator,
                            "denominator": Fraction(count, total).denominator,
                        },
                    }
                    for delta, count in sorted(observed.items())
                ],
                "conservative_probability_interval": [0, 1],
            }
        )
    payload = {
        "schema": "acfqp.generic_stochastic_partial.v47r1",
        "program_id": program["program_id"],
        "support_rows": support_rows,
        "exact_probability_authority": False,
        "support_complete_on_registered_source": all(
            len(row["observed_support"]) == 2 for row in support_rows
        ),
        "planner_probability_input": "NONE_ROBUST_WORST_SUPPORT",
    }
    if not payload["support_complete_on_registered_source"]:
        _fail("registered stochastic source did not observe both support atoms")
    return {
        **payload,
        "partial_model_id": content_id(pre.FUTURE_DOMAINS["stochastic"], payload),
    }


def _document() -> dict[str, Any]:
    preregistration = pre.verify_generic_bytecode_successor_preregistration_v47r1(
        pre.freeze_generic_bytecode_successor_preregistration_v47r1()
    )
    lmb_archives = []
    lmb_catalogues: dict[int, tuple[RawActionV1, ...]] = {}
    lmb_rows: list[RawTransitionV1] = []
    for occurrence, seed in enumerate(pre.LMB_SOURCE_SEEDS, 1000):
        archive, catalogue, rows = _acquire_lmb_source(occurrence, seed)
        lmb_archives.append(archive)
        lmb_catalogues[occurrence] = catalogue
        lmb_rows.extend(rows)
    if len(lmb_rows) > pre.LMB_MAX_SOURCE_LABELS:
        _fail("aggregate D00 source labels crossed the registered cap")
    lmb_program = synthesize_generic_program_v1(
        tuple(lmb_rows),
        lmb_catalogues,
        program_domain=pre.FUTURE_DOMAINS["program"],
    )
    if lmb_program["selected_template_opcode"] != "T00":
        _fail("D00 final program selection changed")

    routing_archives = []
    routing_catalogues: dict[int, tuple[RawActionV1, ...]] = {}
    routing_rows: list[RawTransitionV1] = []
    for occurrence, seed in enumerate(pre.ROUTING_SOURCE_SEEDS, 2000):
        archive, catalogue, rows = _acquire_routing_source(occurrence, seed)
        routing_archives.append(archive)
        routing_catalogues[occurrence] = catalogue
        routing_rows.extend(rows)
    if len(routing_rows) > pre.ROUTING_MAX_SOURCE_LABELS:
        _fail("aggregate D01 source labels crossed the registered cap")
    routing_program = synthesize_generic_program_v1(
        tuple(routing_rows),
        routing_catalogues,
        program_domain=pre.FUTURE_DOMAINS["program"],
    )
    if routing_program["selected_template_opcode"] != "T01":
        _fail("D01 final program selection changed")

    lmb_support = derive_compiled_dependency_support_v2(
        lmb_program, support_domain=pre.FUTURE_DOMAINS["distinction"]
    )
    routing_support = derive_compiled_dependency_support_v2(
        routing_program, support_domain=pre.FUTURE_DOMAINS["distinction"]
    )
    partial_model = _partial_model(
        routing_program, routing_catalogues, tuple(routing_rows)
    )
    episodes = [
        _lmb_target_episode(seed, lmb_program) for seed in pre.LMB_TARGET_SEEDS
    ] + [
        _routing_target_episode(seed, routing_program)
        for seed in pre.ROUTING_TARGET_SEEDS
    ]

    lmb_source_labels = len(lmb_rows)
    routing_source_labels = len(routing_rows)
    source_labels = lmb_source_labels + routing_source_labels
    meta_target_labels = sum(row["meta_target_local_labels"] for row in episodes)
    strict_target_labels = sum(row["strict_target_ground_labels"] for row in episodes)
    cumulative_strict = 0
    cumulative_meta = source_labels
    break_even = None
    for index, episode in enumerate(episodes, 1):
        cumulative_strict += episode["strict_target_ground_labels"]
        cumulative_meta += episode["meta_target_local_labels"]
        if break_even is None and cumulative_meta < cumulative_strict:
            break_even = index
    if source_labels + meta_target_labels >= strict_target_labels:
        _fail("registered structural meta-prior did not reduce total labels")
    if break_even is None:
        _fail("registered diagnostic label break-even was not reached")

    sample_payload = {
        "schema": "acfqp.generic_sample_tax.v47r1",
        "offline_source_labels": {
            "D00": lmb_source_labels,
            "D01": routing_source_labels,
        },
        "meta_target_local_labels": meta_target_labels,
        "strict_target_ground_labels": strict_target_labels,
        "meta_total_labels_including_offline": source_labels + meta_target_labels,
        "strict_total_labels": strict_target_labels,
        "registered_label_saving": strict_target_labels
        - source_labels
        - meta_target_labels,
        "diagnostic_episode_break_even": break_even,
        "official_N_break_even": None,
        "positive_registered_condition_passed": True,
        "broad_cross_domain_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
    }
    sample_tax = {
        **sample_payload,
        "sample_tax_id": content_id(
            pre.FUTURE_DOMAINS["sample_tax"], sample_payload
        ),
    }

    accounting = {
        "offline_source_labels": source_labels,
        "target_local_labels_meta": meta_target_labels,
        "target_ground_labels_strict": strict_target_labels,
        "source_environment_steps": source_labels,
        "target_execution_steps_meta": sum(
            row["execution_steps_per_arm"] for row in episodes
        ),
        "target_execution_steps_strict": sum(
            row["execution_steps_per_arm"] for row in episodes
        ),
        "synthesis_compute_events": len(lmb_rows)
        + len(routing_rows)
        + sum(row["synthesis_probe_count"] for row in lmb_archives + routing_archives),
        "planning_compute_events_meta": sum(
            row["meta_planning_compute_events"] for row in episodes
        ),
        "planning_compute_events_strict": sum(
            row["strict_planning_compute_events"] for row in episodes
        ),
        "certificate_compute_events": sum(
            row["certificate_compute_events"] for row in episodes
        ),
        "peak_program_cache_entries": max(
            max(row["meta_peak_cache_entries"] for row in episodes),
            max(row["strict_peak_cache_entries"] for row in episodes),
        ),
        "labels_steps_compute_and_peak_kept_separate": True,
    }
    ood = {
        "schema": "OPAQUE_CONTINUOUS_REAL_VECTOR",
        "registered_integer_grammar_compatible": False,
        "decision": "OOD_SCHEMA_REJECTED_NO_TRANSFER",
        "prior_access_count": 0,
        "environment_outcome_count": 0,
        "environment_step_count": 0,
    }
    payload = {
        "schema": "acfqp.generic_cross_domain_campaign.v47r1",
        "schema_version": SCHEMA_VERSION,
        "preregistration_id": preregistration.preregistration_id,
        "failed_v47_identity_preserved": True,
        "source_archives": lmb_archives + routing_archives,
        "programs": [lmb_program, routing_program],
        "dependency_support_signatures": [lmb_support, routing_support],
        "stochastic_partial_model": partial_model,
        "episodes": episodes,
        "sample_tax": sample_tax,
        "strict_ood_control": ood,
        "accounting_axes": accounting,
        "one_generic_synthesizer_two_programs": True,
        "compiled_template_opcodes": ["T00", "T01"],
        "lmb_named_primitive_in_compiled_bytecode": False,
        "typed_adapter_abstract_state_consumed_by_planner": False,
        "all_local_ground_labels_follow_failed_certificates": True,
        "successful_certificate_local_ground_label_count": 0,
        "exact_stochastic_probability_authority": False,
        "producer_free_verification_status": "NOT_RUN",
        "broad_world_model_synthesis_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **payload,
        "generic_cross_domain_campaign_id": content_id(
            pre.FUTURE_DOMAINS["campaign"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class GenericBytecodeCampaignV47R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V47r1 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V47r1 campaign bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "generic_cross_domain_campaign_id"
        }
        if document.get("generic_cross_domain_campaign_id") != self.campaign_id or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id:
            _fail("V47r1 campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError
        return value


def freeze_generic_bytecode_campaign_v47r1() -> GenericBytecodeCampaignV47R1:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["generic_cross_domain_campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (identity != CAMPAIGN_ID or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256):
        _fail("frozen V47r1 campaign changed")
    return GenericBytecodeCampaignV47R1(_ISSUER, raw, identity)


def verify_generic_bytecode_campaign_v47r1(
    value: GenericBytecodeCampaignV47R1,
) -> GenericBytecodeCampaignV47R1:
    if type(value) is not GenericBytecodeCampaignV47R1:
        _fail("V47r1 campaign rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("V47r1 campaign semantics changed")
    return value


__all__ = (
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "GenericBytecodeCampaignV47R1",
    "freeze_generic_bytecode_campaign_v47r1",
    "verify_generic_bytecode_campaign_v47r1",
)
