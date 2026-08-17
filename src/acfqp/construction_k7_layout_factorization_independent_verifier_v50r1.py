"""Producer-free reconstruction of the frozen V50r1 two-domain campaign."""

from __future__ import annotations

from collections import deque
from functools import lru_cache
import hashlib
import random
from typing import Any, Callable, Mapping, NoReturn

from acfqp import construction_k7_layout_factorization_preregistration_v50r1 as pre
from acfqp.domains.stochastic_inventory_assembly import (
    InventoryAssemblyAction,
    InventoryAssemblyState,
    InventoryAssemblyStatus,
    generate_stochastic_inventory_assembly,
    select_seeded_inventory_assembly_outcome_v1,
)
from acfqp.domains.stochastic_modular_routing import (
    StochasticModularAction,
    StochasticModularState,
    StochasticModularStatus,
    generate_stochastic_modular_routing,
    select_seeded_stochastic_modular_outcome_v1,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
    GenericAtomicExpressionWorldModelV4Error,
    execute_generic_atomic_support_v4,
    missing_relation_values_v4,
    plan_generic_atomic_program_v4,
    target_binding_from_initial_vector_v4,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    DiscoveredLayoutV5,
    GenericLayoutFactorizedWorldModelV5Error,
    align_generic_occurrence_v5,
    discover_generic_layout_v5,
    match_generic_layout_meta_prior_v5,
)
from acfqp.generic_layout_factorized_world_model_v6 import (
    synthesize_layout_factorized_world_model_v6,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


EXPECTED_CAMPAIGN_ID = "24460ce540a835aba601cdba6865ae74f65c95e6eb8f060c00bddd9b0d4f7622"
EXPECTED_CAMPAIGN_BYTE_COUNT = 361_145
EXPECTED_CAMPAIGN_SHA256 = "f962a4a0e2feac85841e12153f3538108d3a165c8e6c482c9e44a7ac4ab176f1"
VERIFICATION_ID = "5998e44d2d1de657b9efee97e717d9301e0af046bac26967a68c8e38f4c2eedb"
EXPECTED_CANONICAL_BYTE_COUNT = 1_554
EXPECTED_CANONICAL_SHA256 = "6e54787ce8efb5892f1b8baa2018852df679bae209420a8c2c6244207d264cb7"


class ConstructionK7LayoutFactorizationIndependentVerifierV50R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LayoutFactorizationIndependentVerifierV50R1Error(message)


def _permutations(seed: int, state_width: int, action_width: int):
    rng = random.Random(seed ^ 0x50A17)
    states = list(range(state_width))
    actions = list(range(action_width))
    rng.shuffle(states)
    rng.shuffle(actions)
    return tuple(states), tuple(actions)


def _token(status: Any, active: Any, success: Any) -> int:
    return pre.TERMINAL_TOKENS[
        "A" if status is active else "S" if status is success else "F"
    ]


def _modular_interface(seed: int, kernel: Any):
    state_order, action_order = _permutations(seed, 9, 6)
    catalogue = tuple(
        FlatRawActionV4(
            index,
            tuple(
                (
                    seed * 100 + edge.source,
                    seed * 100 + edge.destination,
                    pre.MODE_TOKENS[edge.mode],
                    edge.magnitude,
                    pre.CLASS_TOKENS[edge.cost_class],
                    seed * 10_000 + index,
                )[position]
                for position in action_order
            ),
        )
        for index, edge in enumerate(kernel.edges)
    )

    def encode(state: StochasticModularState) -> tuple[int, ...]:
        semantic = (
            seed * 100 + state.node,
            state.phase,
            state.resource,
            state.steps,
            _token(
                state.status,
                StochasticModularStatus.ACTIVE,
                StochasticModularStatus.SUCCESS,
            ),
            kernel.modulus,
            kernel.capacity,
            kernel.goal_phase,
            seed * 100 + kernel.goal_node,
        )
        return tuple(semantic[position] for position in state_order)

    return catalogue, encode


def _inventory_interface(seed: int, kernel: Any):
    state_order, action_order = _permutations(seed ^ 0x2233, 7, 5)
    catalogue = tuple(
        FlatRawActionV4(
            index,
            tuple(
                (
                    seed * 100 + recipe.source_stage,
                    seed * 100 + recipe.destination_stage,
                    recipe.produced_units,
                    recipe.contamination_increment,
                    seed * 10_000 + index,
                )[position]
                for position in action_order
            ),
        )
        for index, recipe in enumerate(kernel.recipes)
    )

    def encode(state: InventoryAssemblyState) -> tuple[int, ...]:
        semantic = (
            seed * 100 + state.stage,
            state.units,
            state.contamination,
            _token(
                state.status,
                InventoryAssemblyStatus.ACTIVE,
                InventoryAssemblyStatus.SUCCESS,
            ),
            kernel.contamination_capacity,
            kernel.target_units,
            seed * 100 + kernel.goal_stage,
        )
        return tuple(semantic[position] for position in state_order)

    return catalogue, encode


def _observe(
    occurrence: int,
    initial: Any,
    catalogue: tuple[FlatRawActionV4, ...],
    encode: Callable[[Any], tuple[int, ...]],
    actions: Callable[[Any], tuple[Any, ...]],
    step: Callable[[Any, Any], tuple[Any, ...]],
    action_key: Callable[[Any], int],
    active: Callable[[Any], bool],
    success: Callable[[Any], bool],
):
    queue = deque([initial])
    seen = {initial}
    rows = []
    labels = 0
    while queue:
        state = queue.popleft()
        legal = actions(state)
        for action in legal:
            labels += 1
            for outcome in step(state, action):
                successor = outcome.next_state
                legal_after = actions(successor)
                rows.append(
                    FlatRawTransitionV4(
                        occurrence,
                        len(rows),
                        encode(state),
                        tuple(action_key(row) for row in legal),
                        catalogue[action_key(action)],
                        encode(successor),
                        tuple(action_key(row) for row in legal_after),
                        None if legal_after else success(successor),
                    )
                )
                if active(successor) and successor not in seen:
                    seen.add(successor)
                    queue.append(successor)
    return tuple(rows), labels, len(seen)


def _archive(family: str, occurrence: int, seed: int, catalogue, rows, labels, reachable):
    payload = {
        "schema": "acfqp.layout_factorized_raw_observation.v50",
        "family": family,
        "occurrence": occurrence,
        "seed": seed,
        "anonymous_action_catalogue": [row.to_document() for row in catalogue],
        "raw_transitions": [row.to_document() for row in rows],
        "source_support_labels": labels,
        "reachable_active_state_count": reachable,
        "layout_positions_preregistered": False,
        "generation_witness_accessed": False,
        "policy": "WITNESS_BLIND_EXHAUSTIVE_REACHABLE_FRONTIER_ALL_LEGAL_SUPPORTS",
    }
    return {
        **payload,
        "raw_observation_id": content_id(pre.FUTURE_DOMAINS["observation"], payload),
    }


def _calibrate(initial, catalogue, encode, kernel, action_key, active, success, reference_rows, reference_catalogue, reference_layout):
    queue = deque([initial])
    seen = {initial}
    rows = []
    labels = 0
    last_mapping = None
    stable_count = 0
    while queue and labels < pre.MAXIMUM_TARGET_LAYOUT_LABELS:
        state = queue.popleft()
        legal = kernel.actions(state)
        for action in legal:
            labels += 1
            for outcome in kernel.step(state, action):
                successor = outcome.next_state
                legal_after = kernel.actions(successor)
                rows.append(
                    FlatRawTransitionV4(
                        0,
                        len(rows),
                        encode(state),
                        tuple(action_key(row) for row in legal),
                        catalogue[action_key(action)],
                        encode(successor),
                        tuple(action_key(row) for row in legal_after),
                        None if legal_after else success(successor),
                    )
                )
                if active(successor) and successor not in seen:
                    seen.add(successor)
                    queue.append(successor)
            try:
                layout = match_generic_layout_meta_prior_v5(
                    reference_rows,
                    reference_catalogue,
                    reference_layout,
                    tuple(rows),
                    catalogue,
                    layout_domain=pre.FUTURE_DOMAINS["layout"],
                )
            except GenericLayoutFactorizedWorldModelV5Error:
                layout = None
            if layout is not None:
                mapping = (layout.state_canonical_to_raw, layout.action_canonical_to_raw)
                stable_count = stable_count + 1 if mapping == last_mapping else 1
                last_mapping = mapping
                if stable_count >= 2:
                    return tuple(rows), layout, labels
            if labels >= pre.MAXIMUM_TARGET_LAYOUT_LABELS:
                break
    _fail("independent target calibration did not recover a stable layout")


def _used_relations(program: Mapping[str, Any]) -> dict[str, list[list[int]]]:
    encoded = canonical_json_bytes(
        [row["expression"] for row in program["compiled_assignments"]]
    ).decode("utf-8")
    return {
        name: rows
        for name, rows in program["occurrence_bindings"][0]["relations"].items()
        if f'"{name}"' in encoded
    }


def _relation_fields(program: Mapping[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}

    def visit(expression: Any) -> None:
        if type(expression) is not list:
            return
        if (
            len(expression) >= 3
            and expression[0] == "E04"
            and type(expression[2]) is list
            and expression[2][:1] == ["E01"]
        ):
            result[expression[1]] = expression[2][1]
        for item in expression:
            visit(item)

    for assignment in program["compiled_assignments"]:
        visit(assignment["expression"])
    return result


def _modulus(program, name, binding, state) -> int:
    values: set[int] = set()

    def contains(expression: Any) -> bool:
        return type(expression) is list and (
            (len(expression) >= 2 and expression[0] == "E04" and expression[1] == name)
            or any(contains(item) for item in expression)
        )

    def visit(expression: Any) -> None:
        if type(expression) is not list:
            return
        if len(expression) == 3 and expression[0] == "E06" and contains(expression[1]):
            denominator = expression[2]
            if denominator[:1] == ["E00"]:
                values.add(state[denominator[1]])
            elif denominator[:1] == ["E03"]:
                values.add(binding["constants"][denominator[1]])
        for item in expression:
            visit(item)

    for assignment in program["compiled_assignments"]:
        visit(assignment["expression"])
    if len(values) != 1:
        _fail("independent relation modulus changed")
    return next(iter(values))


def _recover(program, binding, state, action, support, name, relation_input, overlay):
    matches = []
    for candidate in range(_modulus(program, name, binding, state)):
        trial = {key: dict(rows) for key, rows in overlay.items()}
        trial.setdefault(name, {})[relation_input] = candidate
        try:
            predicted = set(
                execute_generic_atomic_support_v4(
                    program, state, action, binding, relation_overlay=trial
                )
            )
        except (GenericAtomicExpressionWorldModelV4Error, ZeroDivisionError):
            continue
        if predicted == support:
            matches.append(candidate)
    if len(matches) != 1:
        _fail("independent local relation recovery changed")
    return matches[0]


def _strict_choice(kernel, state, cache, success, failure, key_of):
    choices = {}
    labels = 0

    @lru_cache(maxsize=None)
    def solve(current):
        nonlocal labels
        if current.status is success:
            return True
        if current.status is failure:
            return False
        for action in kernel.actions(current):
            key = (current, key_of(action))
            if key not in cache:
                cache[key] = tuple(row.next_state for row in kernel.step(current, action))
                labels += 1
            if all(solve(successor) for successor in cache[key]):
                choices[current] = key_of(action)
                return True
        return False

    if not solve(state) or state not in choices:
        _fail("independent strict planner found no robust continuation")
    return choices[state], solve.cache_info().currsize, labels


def _episode(family, seed, arm, actions, tapes, planning, peak, labels, layout_labels, local_labels, failures, success):
    payload = {
        "schema": "acfqp.layout_factorized_receding_episode.v50",
        "family": family,
        "seed": seed,
        "arm": arm,
        "action_keys": actions,
        "outcome_tape_sha256": tapes,
        "execution_steps": len(actions),
        "planning_compute_events": planning,
        "peak_planning_cache_entries": peak,
        "ground_support_labels": labels,
        "target_layout_support_labels": layout_labels,
        "local_ground_support_labels": local_labels,
        "failed_certificate_count": failures,
        "success": success,
    }
    return {**payload, "episode_id": content_id(pre.FUTURE_DOMAINS["episode"], payload)}


def verify_layout_factorization_campaign_bytes_v50r1(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail("V50r1 independent verifier requires bytes")
    if len(raw) != EXPECTED_CAMPAIGN_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CAMPAIGN_SHA256:
        _fail("V50r1 campaign byte identity changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V50r1 campaign canonical encoding changed")
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    if (
        document.get("campaign_id") != EXPECTED_CAMPAIGN_ID
        or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != EXPECTED_CAMPAIGN_ID
        or document.get("preregistration_id") != pre.PREREGISTRATION_ID
    ):
        _fail("V50r1 campaign identity join changed")
    prereg = pre.verify_layout_factorization_preregistration_v50r1(
        pre.freeze_layout_factorization_preregistration_v50r1()
    ).to_document()
    if prereg["fresh_v50r1_registered_outcome_execution_performed"] is not False:
        _fail("V50r1 preregistration was not outcome-free")

    sources: dict[str, dict[str, Any]] = {}
    archives = []
    source_labels = 0
    for family, seeds in (
        ("STOCHASTIC_MODULAR_ROUTING", pre.MODULAR_SOURCE_SEEDS),
        ("STOCHASTIC_INVENTORY_ASSEMBLY", pre.INVENTORY_SOURCE_SEEDS),
    ):
        rows_by_occurrence = {}
        catalogues = {}
        for occurrence, seed in enumerate(seeds):
            if family == "STOCHASTIC_MODULAR_ROUTING":
                kernel, _ = generate_stochastic_modular_routing(
                    **pre.MODULAR_SOURCE_SPEC, seed=seed
                )
                catalogue, encode = _modular_interface(seed, kernel)
                rows, labels, reachable = _observe(
                    occurrence,
                    kernel.initial_distribution()[0][1],
                    catalogue,
                    encode,
                    kernel.actions,
                    kernel.step,
                    lambda action: action.edge,
                    lambda state: state.status is StochasticModularStatus.ACTIVE,
                    lambda state: state.status is StochasticModularStatus.SUCCESS,
                )
            else:
                kernel, _ = generate_stochastic_inventory_assembly(
                    stage_count=pre.INVENTORY_SOURCE_STAGE_COUNT, seed=seed
                )
                catalogue, encode = _inventory_interface(seed, kernel)
                rows, labels, reachable = _observe(
                    occurrence,
                    kernel.initial_distribution()[0][1],
                    catalogue,
                    encode,
                    kernel.actions,
                    kernel.step,
                    lambda action: action.recipe,
                    lambda state: state.status is InventoryAssemblyStatus.ACTIVE,
                    lambda state: state.status is InventoryAssemblyStatus.SUCCESS,
                )
            rows_by_occurrence[occurrence] = rows
            catalogues[occurrence] = catalogue
            archives.append(
                _archive(family, occurrence, seed, catalogue, rows, labels, reachable)
            )
            source_labels += labels
        model = synthesize_layout_factorized_world_model_v6(
            rows_by_occurrence,
            catalogues,
            layout_domain=pre.FUTURE_DOMAINS["layout"],
            program_domain=pre.FUTURE_DOMAINS["program"],
            support_domain=pre.FUTURE_DOMAINS["support"],
        )
        if model != document["world_models"][family]:
            _fail(f"V50r1 {family} world model did not independently reconstruct")
        sources[family] = {
            "rows": rows_by_occurrence,
            "catalogues": catalogues,
            "model": model,
        }
    if archives != document["source_archives"]:
        _fail("V50r1 raw source archives did not independently reconstruct")

    calibrations = []
    failures = []
    distinctions = []
    structural = []
    strict = []
    overlay: dict[str, dict[int, int]] = {}
    transport_attestations: set[tuple[str, int]] = set()
    for family in ("STOCHASTIC_MODULAR_ROUTING", "STOCHASTIC_INVENTORY_ASSEMBLY"):
        source = sources[family]
        reference_rows = source["rows"][0]
        reference_catalogue = source["catalogues"][0]
        reference_layout = discover_generic_layout_v5(
            reference_rows,
            reference_catalogue,
            layout_domain=pre.FUTURE_DOMAINS["layout"],
        )
        program = source["model"]["compiled_program"]
        relations = _used_relations(program)
        relation_fields = _relation_fields(program)
        aligned_reference, _ = align_generic_occurrence_v5(
            reference_rows, reference_catalogue, reference_layout, canonical_occurrence=0
        )
        source_relation_state = aligned_reference[0].pre
        source_binding = program["occurrence_bindings"][0]
        target_seeds = (
            pre.MODULAR_TARGET_SEEDS
            if family == "STOCHASTIC_MODULAR_ROUTING"
            else pre.INVENTORY_TARGET_SEEDS
        )
        for episode_index, seed in enumerate(target_seeds):
            if family == "STOCHASTIC_MODULAR_ROUTING":
                kernel, _ = generate_stochastic_modular_routing(
                    **pre.MODULAR_TARGET_SPEC, seed=seed, require_last_mode=True
                )
                catalogue, encode = _modular_interface(seed, kernel)
                initial = kernel.initial_distribution()[0][1]
                rows, layout, layout_labels = _calibrate(
                    initial,
                    catalogue,
                    encode,
                    kernel,
                    lambda action: action.edge,
                    lambda state: state.status is StochasticModularStatus.ACTIVE,
                    lambda state: state.status is StochasticModularStatus.SUCCESS,
                    reference_rows,
                    reference_catalogue,
                    reference_layout,
                )
            else:
                kernel, _ = generate_stochastic_inventory_assembly(
                    stage_count=pre.INVENTORY_TARGET_STAGE_COUNT, seed=seed
                )
                catalogue, encode = _inventory_interface(seed, kernel)
                initial = kernel.initial_distribution()[0][1]
                rows, layout, layout_labels = _calibrate(
                    initial,
                    catalogue,
                    encode,
                    kernel,
                    lambda action: action.recipe,
                    lambda state: state.status is InventoryAssemblyStatus.ACTIVE,
                    lambda state: state.status is InventoryAssemblyStatus.SUCCESS,
                    reference_rows,
                    reference_catalogue,
                    reference_layout,
                )
            calibration = {
                "schema": "acfqp.layout_factorized_target_calibration.v50",
                "family": family,
                "seed": seed,
                "policy": "WITNESS_BLIND_BFS_UNTIL_TWO_CONSECUTIVE_IDENTICAL_MINIMUM_GRAPH_MATCHES",
                "support_labels": layout_labels,
                "raw_transition_count": len(rows),
                "layout": layout.to_document(),
                "hidden_adapter_layout_accessed": False,
                "numeric_relation_outputs_reused_as_local_distinctions": False,
            }
            calibrations.append(calibration)
            _aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
                rows, catalogue, layout, canonical_occurrence=0
            )
            raw_initial = encode(initial)
            canonical_initial = tuple(
                raw_initial[index] for index in layout.state_canonical_to_raw
            )
            binding = target_binding_from_initial_vector_v4(
                program,
                canonical_initial,
                base_relations=relations,
                terminal_tokens=pre.TERMINAL_TOKENS,
            )
            actions_taken = []
            tapes = []
            planning = 0
            peak = 0
            local_labels = 0
            episode_failures = 0
            state = initial
            decision = 0
            active_status = (
                StochasticModularStatus.ACTIVE
                if family == "STOCHASTIC_MODULAR_ROUTING"
                else InventoryAssemblyStatus.ACTIVE
            )
            success_status = (
                StochasticModularStatus.SUCCESS
                if family == "STOCHASTIC_MODULAR_ROUTING"
                else InventoryAssemblyStatus.SUCCESS
            )
            while state.status is active_status:
                raw_state = encode(state)
                canonical_state = tuple(
                    raw_state[index] for index in layout.state_canonical_to_raw
                )
                if family == "STOCHASTIC_MODULAR_ROUTING":
                    refresh = {
                        name
                        for name in relation_fields
                        if _modulus(program, name, source_binding, source_relation_state)
                        != _modulus(program, name, binding, canonical_state)
                        and (name, _modulus(program, name, binding, canonical_state))
                        not in transport_attestations
                    }
                    missing = sorted(
                        {
                            item
                            for action in aligned_catalogue
                            for item in missing_relation_values_v4(
                                program, action, binding, relation_overlay=overlay
                            )
                        }
                        | {
                            (name, action.fields[relation_fields[name]])
                            for name in refresh
                            for action in aligned_catalogue
                        }
                    )
                    for name, relation_input in missing:
                        failure_payload = {
                            "schema": "acfqp.layout_factorized_failed_certificate.v50",
                            "family": family,
                            "seed": seed,
                            "episode_index": episode_index,
                            "decision_index": decision,
                            "program_id": program["program_id"],
                            "missing_relation_name": name,
                            "missing_relation_input": relation_input,
                            "ground_query_performed_before_failure": False,
                            "outcome": "FAILED_COMPILED_RELATION_SUPPORT_CERTIFICATE",
                        }
                        failure = {
                            **failure_payload,
                            "failed_certificate_id": content_id(
                                pre.FUTURE_DOMAINS["failed_certificate"], failure_payload
                            ),
                        }
                        failures.append(failure)
                        episode_failures += 1
                        field = relation_fields[name]
                        action = next(
                            row for row in aligned_catalogue if row.fields[field] == relation_input
                        )
                        edge = kernel.edges[action.key]
                        probe = StochasticModularState(
                            edge.source, 0, 0, edge.source, StochasticModularStatus.ACTIVE
                        )
                        probe_raw = encode(probe)
                        probe_state = tuple(
                            probe_raw[index] for index in layout.state_canonical_to_raw
                        )
                        support = {
                            tuple(
                                encode(outcome.next_state)[index]
                                for index in layout.state_canonical_to_raw
                            )
                            for outcome in kernel.step(
                                probe, StochasticModularAction(action.key)
                            )
                        }
                        value = _recover(
                            program,
                            binding,
                            probe_state,
                            action,
                            support,
                            name,
                            relation_input,
                            overlay,
                        )
                        overlay.setdefault(name, {})[relation_input] = value
                        distinction_payload = {
                            "schema": "acfqp.layout_factorized_local_distinction.v50",
                            "failed_certificate_id": failure["failed_certificate_id"],
                            "relation_name": name,
                            "relation_input": relation_input,
                            "relation_output": value,
                            "query_after_failed_certificate": True,
                            "ground_support_labels": 1,
                        }
                        distinctions.append(
                            {
                                **distinction_payload,
                                "local_distinction_id": content_id(
                                    pre.FUTURE_DOMAINS["distinction"], distinction_payload
                                ),
                            }
                        )
                        local_labels += 1
                    for name in refresh:
                        transport_attestations.add(
                            (name, _modulus(program, name, binding, canonical_state))
                        )
                plan, evaluations, cache_size = plan_generic_atomic_program_v4(
                    program,
                    canonical_state,
                    aligned_catalogue,
                    binding,
                    relation_overlay=(
                        overlay if family == "STOCHASTIC_MODULAR_ROUTING" else None
                    ),
                )
                key = plan[0]
                planning += evaluations
                peak = max(peak, cache_size)
                if family == "STOCHASTIC_MODULAR_ROUTING":
                    outcome, tape = select_seeded_stochastic_modular_outcome_v1(
                        kernel.step(state, StochasticModularAction(key)),
                        seed=seed,
                        episode_index=episode_index,
                        decision_index=decision,
                    )
                else:
                    outcome, tape = select_seeded_inventory_assembly_outcome_v1(
                        kernel.step(state, InventoryAssemblyAction(key)),
                        seed=seed,
                        episode_index=episode_index,
                        decision_index=decision,
                    )
                state = outcome.next_state
                actions_taken.append(key)
                tapes.append(tape)
                decision += 1
            structural.append(
                _episode(
                    family,
                    seed,
                    "DERIVED_LAYOUT_STRUCTURAL_PRIOR",
                    actions_taken,
                    tapes,
                    planning,
                    peak,
                    layout_labels + local_labels,
                    layout_labels,
                    local_labels,
                    episode_failures,
                    state.status is success_status,
                )
            )

            strict_actions = []
            strict_tapes = []
            strict_planning = 0
            strict_peak = 0
            strict_labels = 0
            strict_state = initial
            strict_cache = {}
            strict_decision = 0
            while strict_state.status is active_status:
                if family == "STOCHASTIC_MODULAR_ROUTING":
                    key, compute, labels = _strict_choice(
                        kernel,
                        strict_state,
                        strict_cache,
                        StochasticModularStatus.SUCCESS,
                        StochasticModularStatus.FAILURE,
                        lambda action: action.edge,
                    )
                    outcome, tape = select_seeded_stochastic_modular_outcome_v1(
                        kernel.step(strict_state, StochasticModularAction(key)),
                        seed=seed,
                        episode_index=episode_index,
                        decision_index=strict_decision,
                    )
                else:
                    key, compute, labels = _strict_choice(
                        kernel,
                        strict_state,
                        strict_cache,
                        InventoryAssemblyStatus.SUCCESS,
                        InventoryAssemblyStatus.FAILURE,
                        lambda action: action.recipe,
                    )
                    outcome, tape = select_seeded_inventory_assembly_outcome_v1(
                        kernel.step(strict_state, InventoryAssemblyAction(key)),
                        seed=seed,
                        episode_index=episode_index,
                        decision_index=strict_decision,
                    )
                strict_state = outcome.next_state
                strict_actions.append(key)
                strict_tapes.append(tape)
                strict_planning += compute
                strict_peak = max(strict_peak, compute)
                strict_labels += labels
                strict_decision += 1
            strict.append(
                _episode(
                    family,
                    seed,
                    "STRICT_EXACT_CONTEXT",
                    strict_actions,
                    strict_tapes,
                    strict_planning,
                    strict_peak,
                    strict_labels,
                    0,
                    0,
                    0,
                    strict_state.status is success_status,
                )
            )

    if calibrations != document["target_layout_calibrations"]:
        _fail("V50r1 target layout calibrations did not independently reconstruct")
    if failures != document["failed_certificates"] or distinctions != document["local_distinctions"]:
        _fail("V50r1 certificate-first local recovery did not independently reconstruct")
    if structural != document["structural_episodes"] or strict != document["strict_episodes"]:
        _fail("V50r1 matched receding episodes did not independently reconstruct")
    expected_overlay = {
        name: [[key, value] for key, value in sorted(rows.items())]
        for name, rows in sorted(overlay.items())
    }
    if expected_overlay != document["relation_overlay"]:
        _fail("V50r1 immutable relation overlay changed")

    structural_labels = sum(row["ground_support_labels"] for row in structural)
    strict_labels = sum(row["ground_support_labels"] for row in strict)
    savings = strict_labels - structural_labels
    sample_payload = {
        "schema": "acfqp.layout_factorized_sample_tax.v50",
        "offline_source_support_labels": source_labels,
        "structural_target_support_labels": structural_labels,
        "strict_target_support_labels": strict_labels,
        "structural_total_support_labels": source_labels + structural_labels,
        "strict_target_label_savings": savings,
        "sample_labels_separate_from_planning_compute": True,
        "diagnostic_break_even_occurrences": (
            source_labels * len(structural) + savings - 1
        )
        // savings,
        "official_break_even_claimed": False,
    }
    expected_sample = {
        **sample_payload,
        "sample_tax_id": content_id(pre.FUTURE_DOMAINS["sample_tax"], sample_payload),
    }
    if expected_sample != document["sample_tax"]:
        _fail("V50r1 sample tax did not independently reconstruct")
    accounting = {
        "offline_source_support_labels": source_labels,
        "target_layout_support_labels": sum(
            row["target_layout_support_labels"] for row in structural
        ),
        "local_ground_support_labels": sum(
            row["local_ground_support_labels"] for row in structural
        ),
        "structural_execution_steps": sum(row["execution_steps"] for row in structural),
        "strict_execution_steps": sum(row["execution_steps"] for row in strict),
        "layout_relation_evaluations": sum(
            model["layout_relation_evaluations"]
            for model in document["world_models"].values()
        )
        + sum(row["layout"]["relation_evaluations"] for row in calibrations),
        "atomic_synthesis_compute_events": sum(
            model["compiled_program"]["atomic_expression_evaluations"]
            for model in document["world_models"].values()
        ),
        "structural_planning_compute_events": sum(
            row["planning_compute_events"] for row in structural
        ),
        "strict_planning_compute_events": sum(
            row["planning_compute_events"] for row in strict
        ),
        "certificate_compute_events": len(failures),
        "all_axes_separate": True,
    }
    if accounting != document["accounting"]:
        _fail("V50r1 separated accounting axes did not independently reconstruct")
    if not (
        document["frozen_failed_predecessor_id"] == pre.V50_FAILURE_ID
        and document["successor_correction"]["terminal_self_next_dependency_count"] == 0
        and document["ood_rejection"]["prior_transfer_attempted"] is False
        and document["ood_rejection"]["ood_outcome_execution_performed"] is False
        and document["official_execution_allowed"] is False
        and document["official_scalar_cost"] is None
        and document["official_N_break_even"] is None
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    ):
        _fail("V50r1 claim boundary changed")
    return {
        "source_archive_count": len(archives),
        "source_support_labels": source_labels,
        "target_layout_support_labels": accounting["target_layout_support_labels"],
        "local_ground_support_labels": accounting["local_ground_support_labels"],
        "structural_target_support_labels": structural_labels,
        "strict_target_support_labels": strict_labels,
        "structural_total_support_labels": source_labels + structural_labels,
        "net_support_label_reduction": strict_labels - source_labels - structural_labels,
        "diagnostic_break_even_occurrences": expected_sample["diagnostic_break_even_occurrences"],
        "structural_episode_count": len(structural),
        "strict_episode_count": len(strict),
        "certificate_failure_count": len(failures),
        "local_distinction_count": len(distinctions),
        "safe_terminal_model_count": sum(
            model["terminal_self_next_dependency_count"] == 0
            for model in document["world_models"].values()
        ),
    }


def freeze_layout_factorization_verification_v50r1(campaign_bytes: bytes) -> bytes:
    facts = verify_layout_factorization_campaign_bytes_v50r1(campaign_bytes)
    payload = {
        "schema": "acfqp.layout_factorization_independent_verification.v50r1",
        "campaign_id": EXPECTED_CAMPAIGN_ID,
        "campaign_byte_count": EXPECTED_CAMPAIGN_BYTE_COUNT,
        "campaign_sha256": EXPECTED_CAMPAIGN_SHA256,
        "preregistration_id": pre.PREREGISTRATION_ID,
        **facts,
        "raw_sources_replayed_from_preregistered_generators": True,
        "layout_and_safe_programs_reconstructed": True,
        "target_layout_calibrations_reconstructed": True,
        "certificate_first_local_recovery_reconstructed": True,
        "matched_receding_plans_and_outcome_tapes_replayed": True,
        "sample_tax_and_separate_accounting_axes_reconstructed": True,
        "strict_cross_domain_ood_no_transfer_rechecked": True,
        "producer_or_campaign_core_module_imported": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "status": "VERIFIED_DURABLE_NONOFFICIAL_V50R1_LAYOUT_FACTORIZATION_EVIDENCE",
    }
    document = {
        **payload,
        "verification_id": content_id(pre.FUTURE_DOMAINS["verification"], payload),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V50r1 verification changed")
    return raw


__all__ = (
    "EXPECTED_CAMPAIGN_BYTE_COUNT",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_CAMPAIGN_SHA256",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "VERIFICATION_ID",
    "freeze_layout_factorization_verification_v50r1",
    "verify_layout_factorization_campaign_bytes_v50r1",
)
