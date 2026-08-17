"""Outcome engine for the V50 layout-factorized world-model campaign.

The producer knows how to turn ground domain objects into anonymous integer
vectors.  Layout discovery and program synthesis receive only those vectors,
anonymous action descriptors, and raw successor observations.
"""

from __future__ import annotations

from collections import deque
from functools import lru_cache
import random
from typing import Any, Callable, Mapping, NoReturn

from acfqp.domains.stochastic_inventory_assembly import (
    InventoryAssemblyAction,
    InventoryAssemblyKernel,
    InventoryAssemblyState,
    InventoryAssemblyStatus,
    generate_stochastic_inventory_assembly,
    select_seeded_inventory_assembly_outcome_v1,
)
from acfqp.domains.stochastic_modular_routing import (
    StochasticModularAction,
    StochasticModularKernel,
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
    synthesize_layout_factorized_world_model_v5,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id


class LayoutFactorizedCampaignCoreV50Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise LayoutFactorizedCampaignCoreV50Error(message)


def _permutations(seed: int, state_width: int, action_width: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    rng = random.Random(seed ^ 0x50A17)
    states = list(range(state_width))
    actions = list(range(action_width))
    rng.shuffle(states)
    rng.shuffle(actions)
    return tuple(states), tuple(actions)


def _status_token(status: Any, active: Any, success: Any, tokens: Mapping[str, int]) -> int:
    return tokens["A" if status is active else "S" if status is success else "F"]


def _modular_interface(
    seed: int,
    kernel: StochasticModularKernel,
    config: Mapping[str, Any],
) -> tuple[tuple[FlatRawActionV4, ...], Callable[[StochasticModularState], tuple[int, ...]]]:
    state_order, action_order = _permutations(seed, 9, 6)
    catalogue = []
    for index, edge in enumerate(kernel.edges):
        semantic = (
            seed * 100 + edge.source,
            seed * 100 + edge.destination,
            config["mode_tokens"][edge.mode],
            edge.magnitude,
            config["class_tokens"][edge.cost_class],
            seed * 10_000 + index,
        )
        catalogue.append(
            FlatRawActionV4(
                index, tuple(semantic[position] for position in action_order)
            )
        )

    def encode(state: StochasticModularState) -> tuple[int, ...]:
        semantic = (
            seed * 100 + state.node,
            state.phase,
            state.resource,
            state.steps,
            _status_token(
                state.status,
                StochasticModularStatus.ACTIVE,
                StochasticModularStatus.SUCCESS,
                config["terminal_tokens"],
            ),
            kernel.modulus,
            kernel.capacity,
            kernel.goal_phase,
            seed * 100 + kernel.goal_node,
        )
        return tuple(semantic[position] for position in state_order)

    return tuple(catalogue), encode


def _inventory_interface(
    seed: int,
    kernel: InventoryAssemblyKernel,
    config: Mapping[str, Any],
) -> tuple[tuple[FlatRawActionV4, ...], Callable[[InventoryAssemblyState], tuple[int, ...]]]:
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

    def encode(state: InventoryAssemblyState) -> tuple[int, ...]:
        semantic = (
            seed * 100 + state.stage,
            state.units,
            state.contamination,
            _status_token(
                state.status,
                InventoryAssemblyStatus.ACTIVE,
                InventoryAssemblyStatus.SUCCESS,
                config["terminal_tokens"],
            ),
            kernel.contamination_capacity,
            kernel.target_units,
            seed * 100 + kernel.goal_stage,
        )
        return tuple(semantic[position] for position in state_order)

    return tuple(catalogue), encode


def _full_observation(
    occurrence: int,
    initial: Any,
    catalogue: tuple[FlatRawActionV4, ...],
    encode: Callable[[Any], tuple[int, ...]],
    actions: Callable[[Any], tuple[Any, ...]],
    step: Callable[[Any, Any], tuple[Any, ...]],
    action_key: Callable[[Any], int],
    is_active: Callable[[Any], bool],
    is_success: Callable[[Any], bool],
) -> tuple[tuple[FlatRawTransitionV4, ...], int, int]:
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
                        None if legal_after else is_success(successor),
                    )
                )
                if is_active(successor) and successor not in seen:
                    seen.add(successor)
                    queue.append(successor)
    return tuple(rows), labels, len(seen)


def _calibration_observation(
    initial: Any,
    catalogue: tuple[FlatRawActionV4, ...],
    encode: Callable[[Any], tuple[int, ...]],
    actions: Callable[[Any], tuple[Any, ...]],
    step: Callable[[Any, Any], tuple[Any, ...]],
    action_key: Callable[[Any], int],
    is_active: Callable[[Any], bool],
    is_success: Callable[[Any], bool],
    reference_rows: tuple[FlatRawTransitionV4, ...],
    reference_catalogue: tuple[FlatRawActionV4, ...],
    reference_layout: DiscoveredLayoutV5,
    *,
    layout_domain: str,
    maximum_labels: int,
) -> tuple[tuple[FlatRawTransitionV4, ...], DiscoveredLayoutV5, int]:
    queue = deque([initial])
    seen = {initial}
    rows: list[FlatRawTransitionV4] = []
    labels = 0
    last_mapping = None
    stable_count = 0
    while queue and labels < maximum_labels:
        state = queue.popleft()
        legal = actions(state)
        for action in legal:
            labels += 1
            for outcome in step(state, action):
                successor = outcome.next_state
                legal_after = actions(successor)
                rows.append(
                    FlatRawTransitionV4(
                        0,
                        len(rows),
                        encode(state),
                        tuple(action_key(row) for row in legal),
                        catalogue[action_key(action)],
                        encode(successor),
                        tuple(action_key(row) for row in legal_after),
                        None if legal_after else is_success(successor),
                    )
                )
                if is_active(successor) and successor not in seen:
                    seen.add(successor)
                    queue.append(successor)
            try:
                layout = match_generic_layout_meta_prior_v5(
                    reference_rows,
                    reference_catalogue,
                    reference_layout,
                    tuple(rows),
                    catalogue,
                    layout_domain=layout_domain,
                )
            except GenericLayoutFactorizedWorldModelV5Error:
                layout = None
            if layout is not None:
                mapping = (
                    layout.state_canonical_to_raw,
                    layout.action_canonical_to_raw,
                )
                stable_count = stable_count + 1 if mapping == last_mapping else 1
                last_mapping = mapping
                if stable_count >= 2:
                    return tuple(rows), layout, labels
            if labels >= maximum_labels:
                break
    if rows:
        try:
            layout = match_generic_layout_meta_prior_v5(
                reference_rows,
                reference_catalogue,
                reference_layout,
                tuple(rows),
                catalogue,
                layout_domain=layout_domain,
            )
            return tuple(rows), layout, labels
        except GenericLayoutFactorizedWorldModelV5Error:
            pass
    _fail("witness-blind target calibration did not identify a unique layout")


def _archive(
    family: str,
    occurrence: int,
    seed: int,
    catalogue: tuple[FlatRawActionV4, ...],
    rows: tuple[FlatRawTransitionV4, ...],
    labels: int,
    reachable: int,
    observation_domain: str,
) -> dict[str, Any]:
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
    return {**payload, "raw_observation_id": content_id(observation_domain, payload)}


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


def _relation_modulus(
    program: Mapping[str, Any],
    relation_name: str,
    binding: Mapping[str, Any],
    state: tuple[int, ...],
) -> int:
    values: set[int] = set()

    def contains(expression: Any) -> bool:
        return type(expression) is list and (
            (len(expression) >= 2 and expression[0] == "E04" and expression[1] == relation_name)
            or any(contains(item) for item in expression)
        )

    def visit(expression: Any) -> None:
        if type(expression) is not list:
            return
        if len(expression) == 3 and expression[0] == "E06" and contains(expression[1]):
            denominator = expression[2]
            if type(denominator) is list and denominator[:1] == ["E00"]:
                values.add(state[denominator[1]])
            elif type(denominator) is list and denominator[:1] == ["E03"]:
                values.add(binding["constants"][denominator[1]])
        for item in expression:
            visit(item)

    for assignment in program["compiled_assignments"]:
        visit(assignment["expression"])
    if len(values) != 1:
        _fail("compiled relation did not expose one finite modulus")
    return next(iter(values))


def _recover_relation_value(
    program: Mapping[str, Any],
    binding: Mapping[str, Any],
    state: tuple[int, ...],
    action: FlatRawActionV4,
    actual_support: set[tuple[int, ...]],
    relation_name: str,
    relation_input: int,
    overlay: Mapping[str, Mapping[int, int]],
) -> int:
    matches = []
    for candidate in range(_relation_modulus(program, relation_name, binding, state)):
        trial = {name: dict(rows) for name, rows in overlay.items()}
        trial.setdefault(relation_name, {})[relation_input] = candidate
        try:
            predicted = set(
                execute_generic_atomic_support_v4(
                    program,
                    state,
                    action,
                    binding,
                    relation_overlay=trial,
                )
            )
        except (GenericAtomicExpressionWorldModelV4Error, ZeroDivisionError):
            continue
        if predicted == actual_support:
            matches.append(candidate)
    if len(matches) != 1:
        _fail("local relation distinction was not unique")
    return matches[0]


def _episode_payload(
    family: str,
    seed: int,
    arm: str,
    actions: list[int],
    tapes: list[str],
    planning: int,
    peak: int,
    labels: int,
    layout_labels: int,
    local_labels: int,
    failures: int,
    success: bool,
    episode_domain: str,
) -> dict[str, Any]:
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
    return {**payload, "episode_id": content_id(episode_domain, payload)}


def _strict_modular_choice(
    kernel: StochasticModularKernel,
    state: StochasticModularState,
    cache: dict[tuple[StochasticModularState, int], tuple[StochasticModularState, ...]],
) -> tuple[int, int, int]:
    choices: dict[StochasticModularState, int] = {}
    labels = 0

    @lru_cache(maxsize=None)
    def solve(current: StochasticModularState) -> bool:
        nonlocal labels
        if current.status is StochasticModularStatus.SUCCESS:
            return True
        if current.status is StochasticModularStatus.FAILURE:
            return False
        for action in kernel.actions(current):
            key = (current, action.edge)
            if key not in cache:
                cache[key] = tuple(row.next_state for row in kernel.step(current, action))
                labels += 1
            if all(solve(successor) for successor in cache[key]):
                choices[current] = action.edge
                return True
        return False

    if not solve(state) or state not in choices:
        _fail("strict modular planner found no robust continuation")
    return choices[state], solve.cache_info().currsize, labels


def _strict_inventory_choice(
    kernel: InventoryAssemblyKernel,
    state: InventoryAssemblyState,
    cache: dict[tuple[InventoryAssemblyState, int], tuple[InventoryAssemblyState, ...]],
) -> tuple[int, int, int]:
    choices: dict[InventoryAssemblyState, int] = {}
    labels = 0

    @lru_cache(maxsize=None)
    def solve(current: InventoryAssemblyState) -> bool:
        nonlocal labels
        if current.status is InventoryAssemblyStatus.SUCCESS:
            return True
        if current.status is InventoryAssemblyStatus.FAILURE:
            return False
        for action in kernel.actions(current):
            key = (current, action.recipe)
            if key not in cache:
                cache[key] = tuple(row.next_state for row in kernel.step(current, action))
                labels += 1
            if all(solve(successor) for successor in cache[key]):
                choices[current] = action.recipe
                return True
        return False

    if not solve(state) or state not in choices:
        _fail("strict inventory planner found no robust continuation")
    return choices[state], solve.cache_info().currsize, labels


def build_layout_factorized_campaign_document_v50(
    config: Mapping[str, Any],
    preregistration_id: str,
) -> dict[str, Any]:
    domains = config["domains"]
    source_archives = []
    family_sources: dict[str, dict[str, Any]] = {}
    total_source_labels = 0

    modular_rows = {}
    modular_catalogues = {}
    for occurrence, seed in enumerate(config["modular_source_seeds"]):
        kernel, _ = generate_stochastic_modular_routing(
            **config["modular_source_spec"], seed=seed
        )
        catalogue, encode = _modular_interface(seed, kernel, config)
        rows, labels, reachable = _full_observation(
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
        if labels > config["maximum_source_labels_per_occurrence"]:
            _fail("modular source acquisition exceeded its frozen cap")
        modular_rows[occurrence] = rows
        modular_catalogues[occurrence] = catalogue
        source_archives.append(
            _archive(
                "STOCHASTIC_MODULAR_ROUTING",
                occurrence,
                seed,
                catalogue,
                rows,
                labels,
                reachable,
                domains["observation"],
            )
        )
        total_source_labels += labels
    modular_model = synthesize_layout_factorized_world_model_v5(
        modular_rows,
        modular_catalogues,
        layout_domain=domains["layout"],
        program_domain=domains["program"],
        support_domain=domains["support"],
    )
    family_sources["STOCHASTIC_MODULAR_ROUTING"] = {
        "rows": modular_rows,
        "catalogues": modular_catalogues,
        "model": modular_model,
    }

    inventory_rows = {}
    inventory_catalogues = {}
    for occurrence, seed in enumerate(config["inventory_source_seeds"]):
        kernel, _ = generate_stochastic_inventory_assembly(
            stage_count=config["inventory_source_stage_count"], seed=seed
        )
        catalogue, encode = _inventory_interface(seed, kernel, config)
        rows, labels, reachable = _full_observation(
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
        if labels > config["maximum_source_labels_per_occurrence"]:
            _fail("inventory source acquisition exceeded its frozen cap")
        inventory_rows[occurrence] = rows
        inventory_catalogues[occurrence] = catalogue
        source_archives.append(
            _archive(
                "STOCHASTIC_INVENTORY_ASSEMBLY",
                occurrence,
                seed,
                catalogue,
                rows,
                labels,
                reachable,
                domains["observation"],
            )
        )
        total_source_labels += labels
    inventory_model = synthesize_layout_factorized_world_model_v5(
        inventory_rows,
        inventory_catalogues,
        layout_domain=domains["layout"],
        program_domain=domains["program"],
        support_domain=domains["support"],
    )
    family_sources["STOCHASTIC_INVENTORY_ASSEMBLY"] = {
        "rows": inventory_rows,
        "catalogues": inventory_catalogues,
        "model": inventory_model,
    }

    failed_certificates = []
    local_distinctions = []
    calibrations = []
    structural_episodes = []
    strict_episodes = []
    modular_overlay: dict[str, dict[int, int]] = {}
    modular_transport_attestations: set[tuple[str, int]] = set()

    for family in ("STOCHASTIC_MODULAR_ROUTING", "STOCHASTIC_INVENTORY_ASSEMBLY"):
        source = family_sources[family]
        reference_rows = source["rows"][0]
        reference_catalogue = source["catalogues"][0]
        reference_layout = discover_generic_layout_v5(
            reference_rows,
            reference_catalogue,
            layout_domain=domains["layout"],
        )
        program = source["model"]["compiled_program"]
        relations = _used_relations(program)
        relation_fields = _relation_fields(program)
        aligned_reference_rows, _aligned_reference_catalogue = align_generic_occurrence_v5(
            reference_rows,
            reference_catalogue,
            reference_layout,
            canonical_occurrence=0,
        )
        source_relation_state = aligned_reference_rows[0].pre
        source_relation_binding = program["occurrence_bindings"][0]
        target_seeds = (
            config["modular_target_seeds"]
            if family == "STOCHASTIC_MODULAR_ROUTING"
            else config["inventory_target_seeds"]
        )
        for episode_index, seed in enumerate(target_seeds):
            if family == "STOCHASTIC_MODULAR_ROUTING":
                kernel, _ = generate_stochastic_modular_routing(
                    **config["modular_target_spec"], seed=seed, require_last_mode=True
                )
                catalogue, encode = _modular_interface(seed, kernel, config)
                initial = kernel.initial_distribution()[0][1]
                rows, layout, layout_labels = _calibration_observation(
                    initial,
                    catalogue,
                    encode,
                    kernel.actions,
                    kernel.step,
                    lambda action: action.edge,
                    lambda state: state.status is StochasticModularStatus.ACTIVE,
                    lambda state: state.status is StochasticModularStatus.SUCCESS,
                    reference_rows,
                    reference_catalogue,
                    reference_layout,
                    layout_domain=domains["layout"],
                    maximum_labels=config["maximum_target_layout_labels"],
                )
            else:
                kernel, _ = generate_stochastic_inventory_assembly(
                    stage_count=config["inventory_target_stage_count"], seed=seed
                )
                catalogue, encode = _inventory_interface(seed, kernel, config)
                initial = kernel.initial_distribution()[0][1]
                rows, layout, layout_labels = _calibration_observation(
                    initial,
                    catalogue,
                    encode,
                    kernel.actions,
                    kernel.step,
                    lambda action: action.recipe,
                    lambda state: state.status is InventoryAssemblyStatus.ACTIVE,
                    lambda state: state.status is InventoryAssemblyStatus.SUCCESS,
                    reference_rows,
                    reference_catalogue,
                    reference_layout,
                    layout_domain=domains["layout"],
                    maximum_labels=config["maximum_target_layout_labels"],
                )
            aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
                rows, catalogue, layout, canonical_occurrence=0
            )
            del aligned_rows
            raw_initial = encode(initial)
            canonical_initial = tuple(
                raw_initial[index] for index in layout.state_canonical_to_raw
            )
            binding = target_binding_from_initial_vector_v4(
                program,
                canonical_initial,
                base_relations=relations,
                terminal_tokens=config["terminal_tokens"],
            )
            calibration_payload = {
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
            calibrations.append(calibration_payload)
            by_key = {row.key: row for row in aligned_catalogue}
            actions_taken: list[int] = []
            tapes: list[str] = []
            planning = 0
            peak = 0
            local_labels = 0
            episode_failures = 0
            state = initial
            decision = 0
            while (
                state.status is StochasticModularStatus.ACTIVE
                if family == "STOCHASTIC_MODULAR_ROUTING"
                else state.status is InventoryAssemblyStatus.ACTIVE
            ):
                raw_state = encode(state)
                canonical_state = tuple(
                    raw_state[index] for index in layout.state_canonical_to_raw
                )
                if family == "STOCHASTIC_MODULAR_ROUTING":
                    refresh_names = {
                        name
                        for name in relation_fields
                        if (
                            _relation_modulus(
                                program,
                                name,
                                source_relation_binding,
                                source_relation_state,
                            )
                            != _relation_modulus(
                                program, name, binding, canonical_state
                            )
                            and (
                                name,
                                _relation_modulus(
                                    program, name, binding, canonical_state
                                ),
                            )
                            not in modular_transport_attestations
                        )
                    }
                    missing = sorted(
                        {
                            item
                            for action in aligned_catalogue
                            for item in missing_relation_values_v4(
                                program,
                                action,
                                binding,
                                relation_overlay=modular_overlay,
                            )
                        }
                        | {
                            (name, action.fields[relation_fields[name]])
                            for name in refresh_names
                            for action in aligned_catalogue
                        }
                    )
                    for relation_name, relation_input in missing:
                        failure_payload = {
                            "schema": "acfqp.layout_factorized_failed_certificate.v50",
                            "family": family,
                            "seed": seed,
                            "episode_index": episode_index,
                            "decision_index": decision,
                            "program_id": program["program_id"],
                            "missing_relation_name": relation_name,
                            "missing_relation_input": relation_input,
                            "ground_query_performed_before_failure": False,
                            "outcome": "FAILED_COMPILED_RELATION_SUPPORT_CERTIFICATE",
                        }
                        failure = {
                            **failure_payload,
                            "failed_certificate_id": content_id(
                                domains["failed_certificate"], failure_payload
                            ),
                        }
                        failed_certificates.append(failure)
                        episode_failures += 1
                        field = relation_fields[relation_name]
                        action = next(
                            row for row in aligned_catalogue if row.fields[field] == relation_input
                        )
                        edge = kernel.edges[action.key]
                        probe = StochasticModularState(
                            edge.source,
                            0,
                            0,
                            edge.source,
                            StochasticModularStatus.ACTIVE,
                        )
                        probe_raw = encode(probe)
                        probe_state = tuple(
                            probe_raw[index] for index in layout.state_canonical_to_raw
                        )
                        actual_support = {
                            tuple(
                                encode(outcome.next_state)[index]
                                for index in layout.state_canonical_to_raw
                            )
                            for outcome in kernel.step(
                                probe, StochasticModularAction(action.key)
                            )
                        }
                        value = _recover_relation_value(
                            program,
                            binding,
                            probe_state,
                            action,
                            actual_support,
                            relation_name,
                            relation_input,
                            modular_overlay,
                        )
                        modular_overlay.setdefault(relation_name, {})[relation_input] = value
                        distinction_payload = {
                            "schema": "acfqp.layout_factorized_local_distinction.v50",
                            "failed_certificate_id": failure["failed_certificate_id"],
                            "relation_name": relation_name,
                            "relation_input": relation_input,
                            "relation_output": value,
                            "query_after_failed_certificate": True,
                            "ground_support_labels": 1,
                        }
                        local_distinctions.append(
                            {
                                **distinction_payload,
                                "local_distinction_id": content_id(
                                    domains["distinction"], distinction_payload
                                ),
                            }
                        )
                        local_labels += 1
                    for name in refresh_names:
                        modular_transport_attestations.add(
                            (
                                name,
                                _relation_modulus(
                                    program, name, binding, canonical_state
                                ),
                            )
                        )
                try:
                    plan, evaluations, cache_size = plan_generic_atomic_program_v4(
                        program,
                        canonical_state,
                        aligned_catalogue,
                        binding,
                        relation_overlay=(
                            modular_overlay
                            if family == "STOCHASTIC_MODULAR_ROUTING"
                            else None
                        ),
                    )
                except GenericAtomicExpressionWorldModelV4Error as exc:
                    _fail(
                        "compiled structural planner found no robust continuation "
                        f"for {family} seed {seed} decision {decision}: {exc}"
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
            success = (
                state.status is StochasticModularStatus.SUCCESS
                if family == "STOCHASTIC_MODULAR_ROUTING"
                else state.status is InventoryAssemblyStatus.SUCCESS
            )
            structural_episodes.append(
                _episode_payload(
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
                    success,
                    domains["episode"],
                )
            )

            strict_actions: list[int] = []
            strict_tapes: list[str] = []
            strict_planning = 0
            strict_peak = 0
            strict_labels = 0
            strict_state = initial
            strict_cache: dict[Any, Any] = {}
            strict_decision = 0
            while (
                strict_state.status is StochasticModularStatus.ACTIVE
                if family == "STOCHASTIC_MODULAR_ROUTING"
                else strict_state.status is InventoryAssemblyStatus.ACTIVE
            ):
                if family == "STOCHASTIC_MODULAR_ROUTING":
                    key, compute, labels = _strict_modular_choice(
                        kernel, strict_state, strict_cache
                    )
                    outcome, tape = select_seeded_stochastic_modular_outcome_v1(
                        kernel.step(strict_state, StochasticModularAction(key)),
                        seed=seed,
                        episode_index=episode_index,
                        decision_index=strict_decision,
                    )
                else:
                    key, compute, labels = _strict_inventory_choice(
                        kernel, strict_state, strict_cache
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
            strict_success = (
                strict_state.status is StochasticModularStatus.SUCCESS
                if family == "STOCHASTIC_MODULAR_ROUTING"
                else strict_state.status is InventoryAssemblyStatus.SUCCESS
            )
            strict_episodes.append(
                _episode_payload(
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
                    strict_success,
                    domains["episode"],
                )
            )

    structural_target_labels = sum(row["ground_support_labels"] for row in structural_episodes)
    strict_target_labels = sum(row["ground_support_labels"] for row in strict_episodes)
    episode_count = len(structural_episodes)
    target_label_savings = strict_target_labels - structural_target_labels
    sample_payload = {
        "schema": "acfqp.layout_factorized_sample_tax.v50",
        "offline_source_support_labels": total_source_labels,
        "structural_target_support_labels": structural_target_labels,
        "strict_target_support_labels": strict_target_labels,
        "structural_total_support_labels": total_source_labels + structural_target_labels,
        "strict_target_label_savings": target_label_savings,
        "sample_labels_separate_from_planning_compute": True,
        "diagnostic_break_even_occurrences": (
            None
            if target_label_savings <= 0
            else (total_source_labels * episode_count + target_label_savings - 1)
            // target_label_savings
        ),
        "official_break_even_claimed": False,
    }
    sample_tax = {
        **sample_payload,
        "sample_tax_id": content_id(domains["sample_tax"], sample_payload),
    }
    if not all(row["success"] for row in structural_episodes + strict_episodes):
        _fail("a matched held-out episode did not reach its registered success state")
    if not failed_certificates or len(local_distinctions) != len(failed_certificates):
        _fail("certificate-first local distinction path was not observed exactly")
    if any(
        not row["query_after_failed_certificate"] for row in local_distinctions
    ):
        _fail("a local ground distinction preceded its failed certificate")
    if total_source_labels + structural_target_labels >= strict_target_labels:
        _fail("structural meta-prior did not amortize its offline sample tax")
    ood_payload = {
        "schema": "acfqp.layout_factorized_ood_rejection.v50",
        "source_family": "STOCHASTIC_MODULAR_ROUTING",
        "candidate_family": "STOCHASTIC_INVENTORY_ASSEMBLY",
        "source_state_width": modular_model["compiled_program"]["state_width"],
        "source_action_width": modular_model["compiled_program"]["action_field_width"],
        "candidate_state_width": inventory_model["compiled_program"]["state_width"],
        "candidate_action_width": inventory_model["compiled_program"]["action_field_width"],
        "incompatible_before_prior_transfer": True,
        "prior_transfer_attempted": False,
        "ood_outcome_execution_performed": False,
        "outcome": "STRICT_SCHEMA_OOD_NO_TRANSFER",
    }
    ood = {**ood_payload, "ood_rejection_id": content_id(domains["ood"], ood_payload)}
    payload = {
        "schema": "acfqp.layout_factorized_campaign.v50",
        "preregistration_id": preregistration_id,
        "source_archives": source_archives,
        "world_models": {
            "STOCHASTIC_MODULAR_ROUTING": modular_model,
            "STOCHASTIC_INVENTORY_ASSEMBLY": inventory_model,
        },
        "target_layout_calibrations": calibrations,
        "failed_certificates": failed_certificates,
        "local_distinctions": local_distinctions,
        "structural_episodes": structural_episodes,
        "strict_episodes": strict_episodes,
        "relation_overlay": {
            name: [[key, value] for key, value in sorted(rows.items())]
            for name, rows in sorted(modular_overlay.items())
        },
        "sample_tax": sample_tax,
        "ood_rejection": ood,
        "accounting": {
            "offline_source_support_labels": total_source_labels,
            "target_layout_support_labels": sum(
                row["target_layout_support_labels"] for row in structural_episodes
            ),
            "local_ground_support_labels": sum(
                row["local_ground_support_labels"] for row in structural_episodes
            ),
            "structural_execution_steps": sum(
                row["execution_steps"] for row in structural_episodes
            ),
            "strict_execution_steps": sum(row["execution_steps"] for row in strict_episodes),
            "layout_relation_evaluations": sum(
                model["layout_relation_evaluations"]
                for model in (modular_model, inventory_model)
            )
            + sum(row["layout"]["relation_evaluations"] for row in calibrations),
            "atomic_synthesis_compute_events": sum(
                model["compiled_program"]["atomic_expression_evaluations"]
                for model in (modular_model, inventory_model)
            ),
            "structural_planning_compute_events": sum(
                row["planning_compute_events"] for row in structural_episodes
            ),
            "strict_planning_compute_events": sum(
                row["planning_compute_events"] for row in strict_episodes
            ),
            "certificate_compute_events": len(failed_certificates),
            "all_axes_separate": True,
        },
        "claim_boundary": {
            "automatic_layout_factorization_observed": True,
            "same_generic_atomic_synthesizer_used_in_two_stochastic_domains": True,
            "completely_different_second_domain_observed": True,
            "strict_cross_domain_ood_no_transfer_observed": True,
            "finite_integer_relation_meta_grammar_only": True,
            "arbitrary_tensor_or_open_world_perception_claimed": False,
            "unbounded_domain_general_world_model_claimed": False,
        },
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {**payload, "campaign_id": content_id(domains["campaign"], payload)}


__all__ = (
    "LayoutFactorizedCampaignCoreV50Error",
    "build_layout_factorized_campaign_document_v50",
)
