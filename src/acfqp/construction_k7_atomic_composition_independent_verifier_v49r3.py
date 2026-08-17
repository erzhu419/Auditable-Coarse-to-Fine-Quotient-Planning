"""Producer-free reconstruction of the frozen V49r3 campaign."""

from __future__ import annotations

from collections import deque
from functools import lru_cache
import hashlib
from typing import Any, Callable, Mapping, NoReturn

from acfqp import construction_k7_atomic_composition_preregistration_v49r3 as pre
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
    derive_atomic_dependency_support_v4,
    execute_generic_atomic_support_v4,
    plan_generic_atomic_program_v4,
    synthesize_generic_atomic_program_v4,
    target_binding_from_initial_vector_v4,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


EXPECTED_CAMPAIGN_ID = "50c7786f7ab89872e4e95ce9a94a8691352cc4899a82554518d6fed07ec18fa3"
EXPECTED_CAMPAIGN_BYTE_COUNT = 191_227
EXPECTED_CAMPAIGN_SHA256 = "56db020312691df44fb9960f3abc0656a250b614937bf4ee2d8d37bb556b49fc"
VERIFICATION_ID = "7ae6d7309b493fa3f669eab9869d801eb72e2615df4f06cb8cde4a81064f1be5"
EXPECTED_CANONICAL_BYTE_COUNT = 1_511
EXPECTED_CANONICAL_SHA256 = "5ebced974028e5fd63e89e89a6d659d6aae0f09bc7d8b3c0326e407cf5d5d9f2"


class ConstructionK7AtomicCompositionIndependentVerifierV49R3Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AtomicCompositionIndependentVerifierV49R3Error(message)


def _interface(
    seed: int, kernel: StochasticModularKernel
) -> tuple[
    tuple[FlatRawActionV4, ...],
    Callable[[StochasticModularState], tuple[int, ...]],
    str,
]:
    catalogue = []
    for index, edge in enumerate(kernel.edges):
        semantic = (
            seed * 100 + edge.source,
            seed * 100 + edge.destination,
            pre.SHARED_MODE_TOKENS[edge.mode],
            edge.magnitude,
            pre.SHARED_CLASS_TOKENS[edge.cost_class],
            seed * 10_000 + index,
        )
        catalogue.append(
            FlatRawActionV4(
                index,
                tuple(semantic[position] for position in pre.ACTION_FIELD_ORDER),
            )
        )

    def encode(state: StochasticModularState) -> tuple[int, ...]:
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
            pre.SHARED_TERMINAL_TOKENS[name],
            kernel.modulus,
            kernel.capacity,
            kernel.goal_phase,
            seed * 100 + kernel.goal_node,
        )
        return tuple(semantic[position] for position in pre.STATE_LAYOUT_ORDER)

    layout = {
        "state_width": len(pre.STATE_LAYOUT_ORDER),
        "action_field_width": len(pre.ACTION_FIELD_ORDER),
        "state_layout_commitment": hashlib.sha256(bytes(pre.STATE_LAYOUT_ORDER)).hexdigest(),
        "action_layout_commitment": hashlib.sha256(bytes(pre.ACTION_FIELD_ORDER)).hexdigest(),
        "semantic_role_names_serialized": False,
    }
    return (
        tuple(catalogue),
        encode,
        content_id(pre.FUTURE_DOMAINS["observation"], layout),
    )


def _source_occurrence(
    occurrence: int, seed: int
) -> tuple[tuple[FlatRawActionV4, ...], tuple[FlatRawTransitionV4, ...], dict[str, Any]]:
    kernel, witness = generate_stochastic_modular_routing(**pre.SOURCE_SPEC, seed=seed)
    del witness
    catalogue, encode, layout_id = _interface(seed, kernel)
    initial = kernel.initial_distribution()[0][1]
    queue = deque([initial])
    seen = {initial}
    rows = []
    labels = 0
    while queue:
        state = queue.popleft()
        legal = kernel.actions(state)
        for action in legal:
            labels += 1
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
    payload = {
        "schema": "acfqp.atomic_composition_raw_observation.v49r3",
        "occurrence": occurrence,
        "seed": seed,
        "opaque_layout_id": layout_id,
        "anonymous_action_catalogue": [row.to_document() for row in catalogue],
        "raw_transitions": [row.to_document() for row in rows],
        "source_support_labels": labels,
        "raw_outcome_rows": len(rows),
        "reachable_active_state_count": len(seen),
        "generation_witness_accessed": False,
        "source_policy": "WITNESS_BLIND_EXHAUSTIVE_REACHABLE_FRONTIER_ALL_LEGAL_ACTION_SUPPORTS",
    }
    return (
        catalogue,
        tuple(rows),
        {
            **payload,
            "raw_observation_id": content_id(
                pre.FUTURE_DOMAINS["observation"], payload
            ),
        },
    )


def _required_relations(program: Mapping[str, Any]) -> dict[str, list[list[int]]]:
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


def _transport_dependencies(
    program: Mapping[str, Any], names: set[str]
) -> tuple[tuple[int, ...], tuple[str, ...]]:
    columns: set[int] = set()
    constants: set[str] = set()

    def contains(expression: Any, name: str) -> bool:
        return type(expression) is list and (
            (len(expression) >= 2 and expression[0] == "E04" and expression[1] == name)
            or any(contains(item, name) for item in expression)
        )

    def visit(expression: Any, name: str) -> None:
        if type(expression) is not list:
            return
        if len(expression) == 3 and expression[0] == "E06" and contains(expression[1], name):
            denominator = expression[2]
            if type(denominator) is list and denominator[:1] == ["E00"]:
                columns.add(denominator[1])
            elif type(denominator) is list and denominator[:1] == ["E03"]:
                constants.add(denominator[1])
        for item in expression:
            visit(item, name)

    for name in names:
        for assignment in program["compiled_assignments"]:
            visit(assignment["expression"], name)
    return tuple(sorted(columns)), tuple(sorted(constants))


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
        _fail("independent V49r3 modulus derivation changed")
    return next(iter(values))


def _recover(
    program: Mapping[str, Any],
    binding: Mapping[str, Any],
    state: tuple[int, ...],
    action: FlatRawActionV4,
    support: set[tuple[int, ...]],
    relation_name: str,
    relation_input: int,
    overlay: Mapping[str, Mapping[int, int]],
) -> int:
    matches = []
    for candidate in range(_relation_modulus(program, relation_name, binding, state)):
        trial = {name: dict(values) for name, values in overlay.items()}
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
        except GenericAtomicExpressionWorldModelV4Error:
            continue
        if predicted == support:
            matches.append(candidate)
    if len(matches) != 1:
        _fail("independent V49r3 local recovery changed")
    return matches[0]


def _strict_choice(
    kernel: StochasticModularKernel,
    state: StochasticModularState,
    cache: dict[tuple[StochasticModularState, int], tuple[StochasticModularState, ...]],
) -> tuple[int, int]:
    choices: dict[StochasticModularState, int] = {}

    @lru_cache(maxsize=None)
    def solve(current: StochasticModularState) -> bool:
        if current.status is StochasticModularStatus.SUCCESS:
            return True
        if current.status is StochasticModularStatus.FAILURE:
            return False
        for action in kernel.actions(current):
            key = (current, action.edge)
            if key not in cache:
                cache[key] = tuple(
                    row.next_state for row in kernel.step(current, action)
                )
            if all(solve(successor) for successor in cache[key]):
                choices[current] = action.edge
                return True
        return False

    if not solve(state):
        _fail("independent V49r3 strict planner changed")
    return choices[state], solve.cache_info().currsize


def verify_atomic_composition_campaign_bytes_v49r3(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail("V49r3 independent verifier requires bytes")
    if (
        len(raw) != EXPECTED_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CAMPAIGN_SHA256
    ):
        _fail("V49r3 campaign byte identity changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V49r3 campaign encoding changed")
    payload = {
        key: value
        for key, value in document.items()
        if key != "atomic_composition_campaign_id"
    }
    if (
        document.get("atomic_composition_campaign_id") != EXPECTED_CAMPAIGN_ID
        or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != EXPECTED_CAMPAIGN_ID
    ):
        _fail("V49r3 campaign content identity changed")
    prereg = pre.freeze_atomic_composition_preregistration_v49r3()
    if (
        document.get("preregistration_id") != prereg.preregistration_id
        or document.get("preregistration_canonical_sha256")
        != hashlib.sha256(prereg.canonical_bytes).hexdigest()
    ):
        _fail("V49r3 preregistration join changed")

    rows = []
    catalogues = {}
    archives = []
    source_labels = 0
    source_first_pre = None
    for occurrence, seed in enumerate(pre.SOURCE_SEEDS):
        catalogue, observed, archive = _source_occurrence(occurrence, seed)
        catalogues[occurrence] = catalogue
        rows.extend(observed)
        archives.append(archive)
        source_labels += archive["source_support_labels"]
        source_first_pre = source_first_pre or observed[0].pre
    if archives != document["source_archives"]:
        _fail("V49r3 source archives did not independently reconstruct")
    program = synthesize_generic_atomic_program_v4(
        tuple(rows), catalogues, program_domain=pre.FUTURE_DOMAINS["program"]
    )
    if program != document["compiled_program"]:
        _fail("V49r3 program did not independently reconstruct")
    dependency = derive_atomic_dependency_support_v4(
        program,
        tuple(rows),
        catalogues,
        support_domain=pre.FUTURE_DOMAINS["support"],
    )
    if dependency != document["dependency_support"]:
        _fail("V49r3 dependency support did not independently reconstruct")

    source_relations = _required_relations(program)
    relation_fields = _relation_fields(program)
    columns, constants = _transport_dependencies(program, set(relation_fields))
    if document["relation_transport_dependencies"] != {
        "E00_columns": list(columns),
        "E03_constants": list(constants),
    }:
        _fail("V49r3 transport dependency evidence changed")
    first_kernel, witness = generate_stochastic_modular_routing(
        **pre.TARGET_SPEC, seed=pre.TARGET_SEEDS[0], require_last_mode=True
    )
    del witness
    first_catalogue, first_encode, _layout = _interface(
        pre.TARGET_SEEDS[0], first_kernel
    )
    first_state = first_kernel.initial_distribution()[0][1]
    first_vector = first_encode(first_state)
    first_binding = target_binding_from_initial_vector_v4(
        program,
        first_vector,
        base_relations=source_relations,
        terminal_tokens=pre.SHARED_TERMINAL_TOKENS,
    )
    changed_columns = [column for column in columns if source_first_pre[column] != first_vector[column]]
    changed_constants = [
        name
        for name in constants
        if program["occurrence_bindings"][0]["constants"].get(name)
        != first_binding["constants"].get(name)
    ]
    failure = document["failed_certificates"]
    if (
        len(failure) != 1
        or failure[0]["dependent_E00_columns"] != list(columns)
        or failure[0]["dependent_E03_constants"] != list(constants)
        or failure[0]["changed_E00_columns"] != changed_columns
        or failure[0]["changed_E03_constants"] != changed_constants
        or failure[0]["ground_query_performed_before_failure"] is not False
    ):
        _fail("V49r3 failed transport certificate changed")

    overlay: dict[str, dict[int, int]] = {}
    distinction_index = 0
    for relation_name, field in sorted(relation_fields.items()):
        for relation_input in sorted(
            {action.fields[field] for action in first_catalogue}
        ):
            action = next(
                row for row in first_catalogue if row.fields[field] == relation_input
            )
            edge = first_kernel.edges[action.key]
            probe_state = StochasticModularState(
                edge.source, 0, 0, edge.source, StochasticModularStatus.ACTIVE
            )
            raw_state = first_encode(probe_state)
            actual_support = {
                first_encode(row.next_state)
                for row in first_kernel.step(
                    probe_state, StochasticModularAction(action.key)
                )
            }
            output = _recover(
                program,
                first_binding,
                raw_state,
                action,
                actual_support,
                relation_name,
                relation_input,
                overlay,
            )
            stored = document["local_distinctions"][distinction_index]
            if (
                stored["failed_certificate_id"] != failure[0]["failed_certificate_id"]
                or stored["anonymous_pre_vector"] != list(raw_state)
                or stored["anonymous_action"] != action.to_document()
                or stored["anonymous_successor_support"]
                != [list(row) for row in sorted(actual_support)]
                or stored["relation_name"] != relation_name
                or stored["relation_input_value"] != relation_input
                or stored["relation_output_value"] != output
                or stored["query_after_failed_certificate"] is not True
            ):
                _fail("V49r3 local distinction did not independently reconstruct")
            overlay.setdefault(relation_name, {})[relation_input] = output
            distinction_index += 1
    if distinction_index != len(document["local_distinctions"]):
        _fail("V49r3 local distinction cardinality changed")
    expected_overlay = {
        name: [[key, value] for key, value in sorted(values.items())]
        for name, values in sorted(overlay.items())
    }
    if document["relation_overlay"] != expected_overlay:
        _fail("V49r3 relation overlay changed")

    strict_labels = 0
    structural_steps = 0
    strict_steps = 0
    structural_planning = 0
    strict_planning = 0
    peak_structural = 0
    for episode_index, seed in enumerate(pre.TARGET_SEEDS):
        kernel, witness = generate_stochastic_modular_routing(
            **pre.TARGET_SPEC, seed=seed, require_last_mode=True
        )
        del witness
        catalogue, encode, _layout = _interface(seed, kernel)
        by_key = {row.key: row for row in catalogue}
        binding = target_binding_from_initial_vector_v4(
            program,
            encode(kernel.initial_distribution()[0][1]),
            base_relations=source_relations,
            terminal_tokens=pre.SHARED_TERMINAL_TOKENS,
        )
        stored = document["structural_episodes"][episode_index]
        state = kernel.initial_distribution()[0][1]
        actions = []
        tapes = []
        planning = 0
        peak = 0
        decision = 0
        while state.status is StochasticModularStatus.ACTIVE:
            plan, evaluations, cache_size = plan_generic_atomic_program_v4(
                program,
                encode(state),
                catalogue,
                binding,
                relation_overlay=overlay,
            )
            action_key = plan[0]
            outcomes = kernel.step(state, StochasticModularAction(action_key))
            if set(
                execute_generic_atomic_support_v4(
                    program,
                    encode(state),
                    by_key[action_key],
                    binding,
                    relation_overlay=overlay,
                )
            ) != {encode(row.next_state) for row in outcomes}:
                _fail("V49r3 structural support replay changed")
            selected, tape = select_seeded_stochastic_modular_outcome_v1(
                outcomes,
                seed=seed,
                episode_index=episode_index,
                decision_index=decision,
            )
            state = selected.next_state
            actions.append(action_key)
            tapes.append(tape)
            planning += evaluations
            peak = max(peak, cache_size)
            decision += 1
        if (
            stored["action_keys"] != actions
            or stored["outcome_tape_sha256"] != tapes
            or stored["planning_compute_events"] != planning
            or stored["peak_planning_cache_entries"] != peak
            or stored["success"] is not True
        ):
            _fail("V49r3 structural episode did not independently replay")
        structural_steps += len(actions)
        structural_planning += planning
        peak_structural = max(peak_structural, peak)

        stored = document["strict_episodes"][episode_index]
        state = kernel.initial_distribution()[0][1]
        cache = {}
        actions = []
        tapes = []
        planning = 0
        peak = 0
        decision = 0
        while state.status is StochasticModularStatus.ACTIVE:
            action_key, cache_size = _strict_choice(kernel, state, cache)
            outcomes = kernel.step(state, StochasticModularAction(action_key))
            selected, tape = select_seeded_stochastic_modular_outcome_v1(
                outcomes,
                seed=seed,
                episode_index=episode_index,
                decision_index=decision,
            )
            state = selected.next_state
            actions.append(action_key)
            tapes.append(tape)
            planning += cache_size
            peak = max(peak, len(cache))
            decision += 1
        if (
            stored["action_keys"] != actions
            or stored["outcome_tape_sha256"] != tapes
            or stored["ground_support_labels"] != len(cache)
            or stored["planning_compute_events"] != planning
            or stored["success"] is not True
        ):
            _fail("V49r3 strict episode did not independently replay")
        strict_labels += len(cache)
        strict_steps += len(actions)
        strict_planning += planning

    local_labels = len(document["local_distinctions"])
    composed = source_labels + local_labels
    sample = document["sample_tax"]
    if (
        sample["offline_source_support_labels"] != source_labels
        or sample["target_local_support_labels"] != local_labels
        or sample["composed_total_registered_support_labels"] != composed
        or sample["strict_target_support_labels"] != strict_labels
        or sample["registered_support_label_savings"] != strict_labels - composed
        or sample["sample_tax_reduced_on_frozen_campaign"] is not True
    ):
        _fail("V49r3 sample tax did not independently reconstruct")
    accounting = document["accounting"]
    if accounting != {
        "offline_source_support_labels": source_labels,
        "target_local_support_labels": local_labels,
        "structural_execution_steps": structural_steps,
        "strict_execution_steps": strict_steps,
        "atomic_derivation_compute_events": program["atomic_expression_evaluations"],
        "structural_planning_compute_events": structural_planning,
        "strict_planning_compute_events": strict_planning,
        "certificate_compute_events": dependency["candidate_dependency_count"],
        "peak_structural_cache_entries": peak_structural,
        "all_axes_separate": True,
    }:
        _fail("V49r3 accounting did not independently reconstruct")
    if not (
        document["ood_rejection"]["prior_transfer_attempted"] is False
        and document["ood_rejection"]["outcome_execution_performed"] is False
        and document["official_execution_allowed"] is False
        and document["official_scalar_cost"] is None
        and document["official_N_break_even"] is None
        and document["counter_completeness_gate_status"] == "NOT_RUN"
        and document["workload_economics_gate_status"] == "NOT_RUN"
    ):
        _fail("V49r3 claim locks changed")
    return {
        "source_support_labels": source_labels,
        "local_support_labels": local_labels,
        "strict_support_labels": strict_labels,
        "registered_support_label_savings": strict_labels - composed,
        "source_raw_outcome_rows": len(rows),
        "structural_episode_count": len(pre.TARGET_SEEDS),
        "strict_episode_count": len(pre.TARGET_SEEDS),
        "overlay_reuse_count": document["adaptive_acquisition"]["overlay_reuse_count"],
        "program_id": program["program_id"],
        "dependency_support_id": dependency["dependency_support_id"],
    }


def freeze_atomic_composition_verification_v49r3(campaign_bytes: bytes) -> bytes:
    facts = verify_atomic_composition_campaign_bytes_v49r3(campaign_bytes)
    payload = {
        "schema": "acfqp.atomic_composition_independent_verification.v49r3",
        "campaign_id": EXPECTED_CAMPAIGN_ID,
        "campaign_byte_count": EXPECTED_CAMPAIGN_BYTE_COUNT,
        "campaign_sha256": EXPECTED_CAMPAIGN_SHA256,
        "preregistration_id": pre.PREREGISTRATION_ID,
        **facts,
        "source_archives_replayed_from_preregistered_generators": True,
        "program_reconstructed_from_raw_observations": True,
        "dependency_support_reconstructed_by_exact_deletion": True,
        "ast_complete_transport_certificate_reconstructed": True,
        "local_relation_exemplars_and_overlay_reconstructed": True,
        "target_structural_and_strict_episodes_replayed": True,
        "sample_tax_and_accounting_reconstructed": True,
        "producer_module_imported": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "status": "VERIFIED_DURABLE_NONOFFICIAL_V49R3_EVIDENCE",
    }
    document = {
        **payload,
        "atomic_composition_verification_id": content_id(
            pre.FUTURE_DOMAINS["verification"], payload
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["atomic_composition_verification_id"] != VERIFICATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V49r3 verification changed")
    return raw


__all__ = (
    "EXPECTED_CAMPAIGN_BYTE_COUNT",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_CAMPAIGN_SHA256",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "VERIFICATION_ID",
    "freeze_atomic_composition_verification_v49r3",
    "verify_atomic_composition_campaign_bytes_v49r3",
)
