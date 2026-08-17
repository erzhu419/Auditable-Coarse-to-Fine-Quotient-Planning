"""Producer-free reconstruction of the frozen V51 factor campaign."""

from __future__ import annotations

from collections import deque
from functools import lru_cache
import hashlib
import random
from typing import Any, Callable, Mapping, NoReturn

from acfqp import construction_k7_cross_schema_factor_preregistration_v51 as pre
from acfqp import construction_k7_layout_factorization_preregistration_v50r1 as v50pre
from acfqp.domains.stochastic_coupled_exchange import (
    CoupledExchangeAction,
    CoupledExchangeState,
    CoupledExchangeStatus,
    generate_stochastic_coupled_exchange,
    select_seeded_coupled_exchange_outcome_v1,
)
from acfqp.domains.stochastic_inventory_assembly import (
    InventoryAssemblyState,
    InventoryAssemblyStatus,
    generate_stochastic_inventory_assembly,
)
from acfqp.domains.stochastic_modular_routing import (
    StochasticModularState,
    StochasticModularStatus,
    generate_stochastic_modular_routing,
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
from acfqp.generic_cross_schema_factor_library_v7 import (
    compile_cross_schema_factor_library_v7,
    compose_target_with_factor_library_v7,
    discover_factor_boundaries_v7,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    DiscoveredLayoutV5,
    GenericLayoutFactorizedWorldModelV5Error,
    align_generic_occurrence_v5,
    discover_generic_layout_v5,
    match_generic_layout_meta_prior_v5,
    match_generic_layout_v5,
)
from acfqp.generic_layout_factorized_world_model_v6 import (
    synthesize_layout_factorized_world_model_v6,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


EXPECTED_CAMPAIGN_ID = "44a63b782201b3e53a32de1bc071d66fb06526903f96a037d2c55c8f3068e144"
EXPECTED_CAMPAIGN_BYTE_COUNT = 254_723
EXPECTED_CAMPAIGN_SHA256 = "124bb3d89ee55b7f942161934c8f7c80236826b5b715473a7c81fa626bc52433"
VERIFICATION_ID = "8d0e1044fe8db610375f35cd0956387b1ce6dca21d786cc62ae9bf1c69c66b3f"
EXPECTED_CANONICAL_BYTE_COUNT = 1_836
EXPECTED_CANONICAL_SHA256 = "fd165290454eb7a51a2f947dd4bd8271e494df699a61442dbc7824188dc00699"


class ConstructionK7CrossSchemaFactorIndependentVerifierV51Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CrossSchemaFactorIndependentVerifierV51Error(message)


def _v50_permutations(seed: int, state_width: int, action_width: int):
    rng = random.Random(seed ^ 0x50A17)
    states = list(range(state_width))
    actions = list(range(action_width))
    rng.shuffle(states)
    rng.shuffle(actions)
    return tuple(states), tuple(actions)


def _token(status: Any, active: Any, success: Any) -> int:
    return v50pre.TERMINAL_TOKENS[
        "A" if status is active else "S" if status is success else "F"
    ]


def _modular_interface(seed: int, kernel: Any):
    state_order, action_order = _v50_permutations(seed, 9, 6)
    catalogue = tuple(
        FlatRawActionV4(
            index,
            tuple(
                (
                    seed * 100 + edge.source,
                    seed * 100 + edge.destination,
                    v50pre.MODE_TOKENS[edge.mode],
                    edge.magnitude,
                    v50pre.CLASS_TOKENS[edge.cost_class],
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
    state_order, action_order = _v50_permutations(seed ^ 0x2233, 7, 5)
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


def _observe_generic(
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


def _reconstruct_v50_source_models() -> tuple[dict[str, dict[str, Any]], int]:
    models: dict[str, dict[str, Any]] = {}
    labels_total = 0
    for family, seeds in (
        ("STOCHASTIC_MODULAR_ROUTING", v50pre.MODULAR_SOURCE_SEEDS),
        ("STOCHASTIC_INVENTORY_ASSEMBLY", v50pre.INVENTORY_SOURCE_SEEDS),
    ):
        rows_by_occurrence = {}
        catalogues = {}
        for occurrence, seed in enumerate(seeds):
            if family == "STOCHASTIC_MODULAR_ROUTING":
                kernel, _ = generate_stochastic_modular_routing(
                    **v50pre.MODULAR_SOURCE_SPEC, seed=seed
                )
                catalogue, encode = _modular_interface(seed, kernel)
                rows, labels, _reachable = _observe_generic(
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
                    stage_count=v50pre.INVENTORY_SOURCE_STAGE_COUNT, seed=seed
                )
                catalogue, encode = _inventory_interface(seed, kernel)
                rows, labels, _reachable = _observe_generic(
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
            labels_total += labels
        models[family] = synthesize_layout_factorized_world_model_v6(
            rows_by_occurrence,
            catalogues,
            layout_domain=v50pre.FUTURE_DOMAINS["layout"],
            program_domain=v50pre.FUTURE_DOMAINS["program"],
            support_domain=v50pre.FUTURE_DOMAINS["support"],
        )
    return models, labels_total


def _permutations(seed: int):
    rng = random.Random(seed ^ 0x51A17)
    states = list(range(10))
    actions = list(range(6))
    rng.shuffle(states)
    rng.shuffle(actions)
    return tuple(states), tuple(actions)


def _interface(seed: int, kernel: Any):
    state_order, action_order = _permutations(seed)
    catalogue = tuple(
        FlatRawActionV4(
            index,
            tuple(
                (
                    seed * 100 + rule.source_stage,
                    seed * 100 + rule.destination_stage,
                    rule.primary_increment,
                    rule.secondary_increment,
                    rule.risk_increment,
                    seed * 10_000 + index,
                )[position]
                for position in action_order
            ),
        )
        for index, rule in enumerate(kernel.rules)
    )

    def encode(state: CoupledExchangeState) -> tuple[int, ...]:
        token = pre.TERMINAL_TOKENS[
            "A"
            if state.status is CoupledExchangeStatus.ACTIVE
            else "S"
            if state.status is CoupledExchangeStatus.SUCCESS
            else "F"
        ]
        semantic = (
            seed * 100 + state.stage,
            state.primary,
            state.secondary,
            state.bonus,
            state.risk,
            state.steps,
            token,
            kernel.risk_capacity,
            kernel.target_primary,
            seed * 100 + kernel.goal_stage,
        )
        return tuple(semantic[position] for position in state_order)

    return catalogue, encode


def _observe(occurrence: int, kernel: Any, catalogue, encode):
    return _observe_generic(
        occurrence,
        kernel.initial_distribution()[0][1],
        catalogue,
        encode,
        kernel.actions,
        kernel.step,
        lambda action: action.exchange,
        lambda state: state.status is CoupledExchangeStatus.ACTIVE,
        lambda state: state.status is CoupledExchangeStatus.SUCCESS,
    )


def _archive(occurrence, seed, catalogue, rows, labels, reachable):
    payload = {
        "schema": "acfqp.cross_schema_factor_raw_observation.v51",
        "family_token": "OPAQUE_HIGHER_ORDER_PARTIAL_STOCHASTIC_TARGET",
        "occurrence": occurrence,
        "seed": seed,
        "anonymous_action_catalogue": [row.to_document() for row in catalogue],
        "raw_transitions": [row.to_document() for row in rows],
        "source_support_labels": labels,
        "reachable_active_state_count": reachable,
        "generation_witness_accessed": False,
        "semantic_layout_names_serialized": False,
        "policy": "WITNESS_BLIND_EXHAUSTIVE_REACHABLE_FRONTIER_ALL_LEGAL_SUPPORTS",
    }
    return {
        **payload,
        "raw_observation_id": content_id(pre.FUTURE_DOMAINS["observation"], payload),
    }


def _calibrate(kernel, catalogue, encode, reference_rows, reference_catalogue, reference_layout):
    initial = kernel.initial_distribution()[0][1]
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
                        tuple(row.exchange for row in legal),
                        catalogue[action.exchange],
                        encode(successor),
                        tuple(row.exchange for row in legal_after),
                        None
                        if legal_after
                        else successor.status is CoupledExchangeStatus.SUCCESS,
                    )
                )
                if successor.status is CoupledExchangeStatus.ACTIVE and successor not in seen:
                    seen.add(successor)
                    queue.append(successor)
            try:
                layout = match_generic_layout_meta_prior_v5(
                    reference_rows,
                    reference_catalogue,
                    reference_layout,
                    tuple(rows),
                    catalogue,
                    layout_domain=pre.FUTURE_DOMAINS["factor_boundary"],
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
    _fail("independent V51 calibration did not recover a stable layout")


def _relations(program: Mapping[str, Any]):
    encoded = canonical_json_bytes(
        [row["expression"] for row in program["compiled_assignments"]]
    ).decode("utf-8")
    return {
        name: rows
        for name, rows in program["occurrence_bindings"][0]["relations"].items()
        if f'"{name}"' in encoded
    }


def _relation_fields(program: Mapping[str, Any]):
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


def _recover(program, binding, state, action, actual, name, relation_input, overlay):
    matches = []
    for candidate in range(pre.MAXIMUM_RELATION_OUTPUT_CANDIDATE + 1):
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
        if predicted == actual:
            matches.append(candidate)
    if len(matches) != 1:
        _fail("independent V51 relation recovery was not unique")
    return matches[0]


def _strict_choice(kernel, state, cache):
    choices = {}
    labels = 0

    @lru_cache(maxsize=None)
    def solve(current):
        nonlocal labels
        if current.status is CoupledExchangeStatus.SUCCESS:
            return True
        if current.status is CoupledExchangeStatus.FAILURE:
            return False
        for action in kernel.actions(current):
            key = (current, action.exchange)
            if key not in cache:
                cache[key] = tuple(row.next_state for row in kernel.step(current, action))
                labels += 1
            if all(solve(successor) for successor in cache[key]):
                choices[current] = action.exchange
                return True
        return False

    if not solve(state) or state not in choices:
        _fail("independent V51 strict planner found no robust continuation")
    return choices[state], solve.cache_info().currsize, labels


def _episode(seed, arm, actions, tapes, planning, peak, labels, layout_labels, local_labels, failures, success):
    payload = {
        "schema": "acfqp.cross_schema_factor_receding_episode.v51",
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


def _reconstruct_campaign_document() -> dict[str, Any]:
    predecessor_models, historical_source_labels = _reconstruct_v50_source_models()
    if historical_source_labels != 370:
        _fail("independent frozen predecessor source labels changed")
    inherited_models = {
        f"SOURCE_MODEL_{index}": model
        for index, (_name, model) in enumerate(sorted(predecessor_models.items()))
    }
    library = compile_cross_schema_factor_library_v7(
        inherited_models, factor_domain=pre.FUTURE_DOMAINS["factor_library"]
    )

    rows_by_occurrence = {}
    catalogues = {}
    archives = []
    source_labels = 0
    for occurrence, seed in enumerate(pre.SOURCE_SEEDS):
        kernel, _ = generate_stochastic_coupled_exchange(
            stage_count=pre.SOURCE_STAGE_COUNT,
            primary_base=pre.SOURCE_PRIMARY_BASE,
            seed=seed,
        )
        catalogue, encode = _interface(seed, kernel)
        rows, labels, reachable = _observe(occurrence, kernel, catalogue, encode)
        if labels > pre.MAXIMUM_SOURCE_LABELS_PER_OCCURRENCE:
            _fail("independent V51 source acquisition exceeded cap")
        rows_by_occurrence[occurrence] = rows
        catalogues[occurrence] = catalogue
        archives.append(_archive(occurrence, seed, catalogue, rows, labels, reachable))
        source_labels += labels
    fallback_model = synthesize_layout_factorized_world_model_v6(
        rows_by_occurrence,
        catalogues,
        layout_domain=pre.FUTURE_DOMAINS["factor_boundary"],
        program_domain=pre.FUTURE_DOMAINS["program"],
        support_domain=pre.FUTURE_DOMAINS["support"],
    )
    reference_layout = discover_generic_layout_v5(
        rows_by_occurrence[0],
        catalogues[0],
        layout_domain=pre.FUTURE_DOMAINS["factor_boundary"],
    )
    aligned_rows = []
    aligned_catalogues = {}
    for occurrence in sorted(rows_by_occurrence):
        layout = (
            reference_layout
            if occurrence == 0
            else match_generic_layout_v5(
                rows_by_occurrence[0],
                catalogues[0],
                reference_layout,
                rows_by_occurrence[occurrence],
                catalogues[occurrence],
                layout_domain=pre.FUTURE_DOMAINS["factor_boundary"],
            )
        )
        rows, catalogue = align_generic_occurrence_v5(
            rows_by_occurrence[occurrence],
            catalogues[occurrence],
            layout,
            canonical_occurrence=occurrence,
        )
        aligned_rows.extend(rows)
        aligned_catalogues[occurrence] = catalogue
    composed_model = compose_target_with_factor_library_v7(
        fallback_model,
        library,
        aligned_rows,
        aligned_catalogues,
        factor_domain=pre.FUTURE_DOMAINS["factor_boundary"],
        program_domain=pre.FUTURE_DOMAINS["program"],
        support_domain=pre.FUTURE_DOMAINS["support"],
    )
    program = composed_model["compiled_program"]
    if composed_model["reused_factor_count"] < pre.MINIMUM_REUSED_FACTOR_COUNT:
        _fail("independent V51 factor reuse fell below preregistration")

    reference_rows = rows_by_occurrence[0]
    reference_catalogue = catalogues[0]
    base_relations = _relations(program)
    relation_fields = _relation_fields(program)
    calibrations = []
    failures = []
    distinctions = []
    overlay: dict[str, dict[int, int]] = {}
    structural = []
    strict = []
    for episode_index, seed in enumerate(pre.TARGET_SEEDS):
        kernel, _ = generate_stochastic_coupled_exchange(
            stage_count=pre.TARGET_STAGE_COUNT,
            primary_base=pre.TARGET_PRIMARY_BASE,
            seed=seed,
        )
        catalogue, encode = _interface(seed, kernel)
        calibration_rows, layout, layout_labels = _calibrate(
            kernel,
            catalogue,
            encode,
            reference_rows,
            reference_catalogue,
            reference_layout,
        )
        calibrations.append(
            {
                "schema": "acfqp.cross_schema_factor_target_calibration.v51",
                "seed": seed,
                "support_labels": layout_labels,
                "raw_transition_count": len(calibration_rows),
                "layout": layout.to_document(),
                "hidden_adapter_layout_accessed": False,
                "policy": "WITNESS_BLIND_BFS_UNTIL_STABLE_MINIMUM_RELATION_GRAPH_MATCH",
            }
        )
        _rows, aligned_catalogue = align_generic_occurrence_v5(
            calibration_rows, catalogue, layout, canonical_occurrence=0
        )
        initial = kernel.initial_distribution()[0][1]
        raw_initial = encode(initial)
        canonical_initial = tuple(
            raw_initial[index] for index in layout.state_canonical_to_raw
        )
        binding = target_binding_from_initial_vector_v4(
            program,
            canonical_initial,
            base_relations=base_relations,
            terminal_tokens=pre.TERMINAL_TOKENS,
        )
        actions = []
        tapes = []
        planning = 0
        peak = 0
        local_labels = 0
        episode_failures = 0
        state = initial
        decision = 0
        while state.status is CoupledExchangeStatus.ACTIVE:
            raw_state = encode(state)
            canonical_state = tuple(
                raw_state[index] for index in layout.state_canonical_to_raw
            )
            missing = sorted(
                {
                    item
                    for action in aligned_catalogue
                    for item in missing_relation_values_v4(
                        program, action, binding, relation_overlay=overlay
                    )
                }
            )
            for name, relation_input in missing:
                failure_payload = {
                    "schema": "acfqp.cross_schema_factor_failed_certificate.v51",
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
                rule = kernel.rules[action.key]
                probe = CoupledExchangeState(
                    rule.source_stage,
                    0,
                    0,
                    0,
                    0,
                    rule.source_stage,
                    CoupledExchangeStatus.ACTIVE,
                )
                raw_probe = encode(probe)
                canonical_probe = tuple(
                    raw_probe[index] for index in layout.state_canonical_to_raw
                )
                actual = {
                    tuple(
                        encode(outcome.next_state)[index]
                        for index in layout.state_canonical_to_raw
                    )
                    for outcome in kernel.step(probe, CoupledExchangeAction(action.key))
                }
                value = _recover(
                    program,
                    binding,
                    canonical_probe,
                    action,
                    actual,
                    name,
                    relation_input,
                    overlay,
                )
                overlay.setdefault(name, {})[relation_input] = value
                distinction_payload = {
                    "schema": "acfqp.cross_schema_factor_local_distinction.v51",
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
            plan, evaluations, cache_size = plan_generic_atomic_program_v4(
                program,
                canonical_state,
                aligned_catalogue,
                binding,
                relation_overlay=overlay,
            )
            key = plan[0]
            outcome, tape = select_seeded_coupled_exchange_outcome_v1(
                kernel.step(state, CoupledExchangeAction(key)),
                seed=seed,
                episode_index=episode_index,
                decision_index=decision,
            )
            state = outcome.next_state
            actions.append(key)
            tapes.append(tape)
            planning += evaluations
            peak = max(peak, cache_size)
            decision += 1
        structural.append(
            _episode(
                seed,
                "CROSS_SCHEMA_FACTOR_COMPOSED_ABSTRACT",
                actions,
                tapes,
                planning,
                peak,
                layout_labels + local_labels,
                layout_labels,
                local_labels,
                episode_failures,
                state.status is CoupledExchangeStatus.SUCCESS,
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
        while strict_state.status is CoupledExchangeStatus.ACTIVE:
            key, compute, labels = _strict_choice(kernel, strict_state, strict_cache)
            outcome, tape = select_seeded_coupled_exchange_outcome_v1(
                kernel.step(strict_state, CoupledExchangeAction(key)),
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
                strict_state.status is CoupledExchangeStatus.SUCCESS,
            )
        )

    target_structural_labels = sum(row["ground_support_labels"] for row in structural)
    target_strict_labels = sum(row["ground_support_labels"] for row in strict)
    cumulative_structural = 419 + source_labels + target_structural_labels
    cumulative_strict = 579 + target_strict_labels
    sample_payload = {
        "schema": "acfqp.cross_schema_factor_sample_tax.v51",
        "historical_v50r1_structural_labels": 419,
        "historical_v50r1_strict_labels": 579,
        "new_domain_source_labels": source_labels,
        "new_domain_target_structural_labels": target_structural_labels,
        "new_domain_target_strict_labels": target_strict_labels,
        "cumulative_structural_labels": cumulative_structural,
        "cumulative_strict_labels": cumulative_strict,
        "cumulative_label_reduction": cumulative_strict - cumulative_structural,
        "factor_fallback_compute_counted_separately_from_sample_labels": True,
        "official_break_even_claimed": False,
    }
    sample_tax = {
        **sample_payload,
        "sample_tax_id": content_id(pre.FUTURE_DOMAINS["sample_tax"], sample_payload),
    }

    fake_payload = {
        "schema": "acfqp.v51.incompatible_factor_probe_program",
        "state_width": 4,
        "action_field_width": 3,
        "compiled_assignments": [
            {
                "target_column": 0,
                "result_type": "INT",
                "expression": ["E13", ["E00", 0], ["E01", 0]],
            }
        ],
    }
    fake_program = {
        **fake_payload,
        "program_id": content_id(pre.FUTURE_DOMAINS["program"], fake_payload),
    }
    fake_boundary = discover_factor_boundaries_v7(
        fake_program, factor_domain=pre.FUTURE_DOMAINS["factor_boundary"]
    )
    shared = {
        row["signature_sha256"] for row in library["cross_schema_subprograms"]
    } & {
        row["signature_sha256"]
        for row in fake_boundary["factors"]
        if row["transferable_without_schema_specific_binding"]
    }
    if shared:
        _fail("independent V51 OOD probe unexpectedly matched")
    ood_payload = {
        "schema": "acfqp.cross_schema_factor_ood_rejection.v51",
        "candidate_schema_pair": [4, 3],
        "shared_transferable_signature_count": 0,
        "minimum_required_reused_factor_count": pre.MINIMUM_REUSED_FACTOR_COUNT,
        "prior_transfer_attempted": False,
        "ood_outcome_execution_performed": False,
        "outcome": "STRICT_FACTOR_SIGNATURE_OOD_NO_TRANSFER",
    }
    ood = {
        **ood_payload,
        "ood_rejection_id": content_id(pre.FUTURE_DOMAINS["ood"], ood_payload),
    }
    payload = {
        "schema": "acfqp.cross_schema_factor_campaign.v51",
        "preregistration_id": pre.PREREGISTRATION_ID,
        "frozen_v50r1_campaign_id": pre.V50R1_CAMPAIGN_ID,
        "source_archives": archives,
        "inherited_factor_library": library,
        "higher_order_partial_stochastic_world_model": {
            "fallback_layout_model": fallback_model,
            "factor_composed_model": composed_model,
        },
        "target_layout_calibrations": calibrations,
        "failed_certificates": failures,
        "local_distinctions": distinctions,
        "relation_overlay": {
            name: [[key, value] for key, value in sorted(rows.items())]
            for name, rows in sorted(overlay.items())
        },
        "structural_episodes": structural,
        "strict_episodes": strict,
        "sample_tax": sample_tax,
        "ood_rejection": ood,
        "accounting": {
            "historical_factor_library_source_labels": historical_source_labels,
            "new_domain_source_labels": source_labels,
            "target_layout_labels": sum(
                row["target_layout_support_labels"] for row in structural
            ),
            "local_ground_labels": sum(
                row["local_ground_support_labels"] for row in structural
            ),
            "structural_execution_steps": sum(
                row["execution_steps"] for row in structural
            ),
            "strict_execution_steps": sum(row["execution_steps"] for row in strict),
            "factor_boundary_compute_events": sum(
                len(row["factors"]) for row in library["factor_boundaries"].values()
            )
            + len(composed_model["target_factor_boundaries"]["factors"]),
            "fallback_atomic_synthesis_compute_events": fallback_model[
                "compiled_program"
            ]["atomic_expression_evaluations"],
            "structural_planning_compute_events": sum(
                row["planning_compute_events"] for row in structural
            ),
            "strict_planning_compute_events": sum(
                row["planning_compute_events"] for row in strict
            ),
            "certificate_compute_events": len(failures),
            "all_axes_separate": True,
        },
        "claim_boundary": {
            "automatic_cross_schema_factor_boundaries_observed": True,
            "cross_schema_subprogram_composition_observed": True,
            "higher_order_partial_stochastic_domain_observed": True,
            "fallback_full_synthesis_compute_separately_accounted": True,
            "factor_prior_sample_savings_claimed_without_ablation": False,
            "arbitrary_schema_or_unbounded_domain_transfer_claimed": False,
        },
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {**payload, "campaign_id": content_id(pre.FUTURE_DOMAINS["campaign"], payload)}


def verify_cross_schema_factor_campaign_bytes_v51(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail("V51 independent verifier requires bytes")
    if (
        len(raw) != EXPECTED_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CAMPAIGN_SHA256
    ):
        _fail("V51 campaign byte identity changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V51 campaign canonical encoding changed")
    prereg = pre.verify_cross_schema_factor_preregistration_v51(
        pre.freeze_cross_schema_factor_preregistration_v51()
    ).to_document()
    if prereg["fresh_v51_registered_outcome_execution_performed"] is not False:
        _fail("V51 preregistration was not outcome-free")
    expected = _reconstruct_campaign_document()
    if expected != document:
        _fail("V51 campaign did not independently reconstruct")
    return {
        "predecessor_source_model_count": 2,
        "source_archive_count": len(document["source_archives"]),
        "cross_schema_library_subprogram_count": len(
            document["inherited_factor_library"]["cross_schema_subprograms"]
        ),
        "target_reused_factor_count": document[
            "higher_order_partial_stochastic_world_model"
        ]["factor_composed_model"]["reused_factor_count"],
        "new_domain_source_labels": document["sample_tax"]["new_domain_source_labels"],
        "target_layout_labels": document["accounting"]["target_layout_labels"],
        "local_ground_labels": document["accounting"]["local_ground_labels"],
        "structural_target_labels": document["sample_tax"][
            "new_domain_target_structural_labels"
        ],
        "strict_target_labels": document["sample_tax"][
            "new_domain_target_strict_labels"
        ],
        "cumulative_structural_labels": document["sample_tax"][
            "cumulative_structural_labels"
        ],
        "cumulative_strict_labels": document["sample_tax"][
            "cumulative_strict_labels"
        ],
        "cumulative_label_reduction": document["sample_tax"][
            "cumulative_label_reduction"
        ],
        "structural_episode_count": len(document["structural_episodes"]),
        "strict_episode_count": len(document["strict_episodes"]),
        "certificate_failure_count": len(document["failed_certificates"]),
        "local_distinction_count": len(document["local_distinctions"]),
        "ood_shared_signature_count": document["ood_rejection"][
            "shared_transferable_signature_count"
        ],
    }


def freeze_cross_schema_factor_verification_v51(campaign_bytes: bytes) -> bytes:
    facts = verify_cross_schema_factor_campaign_bytes_v51(campaign_bytes)
    payload = {
        "schema": "acfqp.cross_schema_factor_independent_verification.v51",
        "campaign_id": EXPECTED_CAMPAIGN_ID,
        "campaign_byte_count": EXPECTED_CAMPAIGN_BYTE_COUNT,
        "campaign_sha256": EXPECTED_CAMPAIGN_SHA256,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "frozen_v50r1_campaign_id": pre.V50R1_CAMPAIGN_ID,
        "frozen_v50r1_verification_id": pre.V50R1_VERIFICATION_ID,
        **facts,
        "predecessor_models_reconstructed_from_raw_registered_generators": True,
        "factor_boundaries_and_cross_schema_library_reconstructed": True,
        "higher_order_target_program_reconstructed": True,
        "certificate_first_local_recovery_reconstructed": True,
        "matched_receding_plans_and_outcome_tapes_replayed": True,
        "separated_sample_and_compute_axes_reconstructed": True,
        "strict_factor_signature_ood_no_transfer_rechecked": True,
        "producer_or_campaign_core_module_imported": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "status": "VERIFIED_DURABLE_NONOFFICIAL_V51_CROSS_SCHEMA_FACTOR_EVIDENCE",
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
        _fail("frozen V51 verification changed")
    return raw


__all__ = (
    "EXPECTED_CAMPAIGN_BYTE_COUNT",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_CAMPAIGN_SHA256",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "VERIFICATION_ID",
    "freeze_cross_schema_factor_verification_v51",
    "verify_cross_schema_factor_campaign_bytes_v51",
)
