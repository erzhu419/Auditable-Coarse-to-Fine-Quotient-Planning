"""Outcome engine for V51 cross-schema factor/subprogram composition."""

from __future__ import annotations

from collections import deque
from functools import lru_cache
import random
from typing import Any, Callable, Mapping, NoReturn

from acfqp.construction_k7_layout_factorization_campaign_v50r1 import (
    run_layout_factorization_campaign_v50r1,
)
from acfqp.domains.stochastic_coupled_exchange import (
    CoupledExchangeAction,
    CoupledExchangeState,
    CoupledExchangeStatus,
    generate_stochastic_coupled_exchange,
    select_seeded_coupled_exchange_outcome_v1,
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
from acfqp.phase3e_ids import canonical_json_bytes, content_id


class CrossSchemaFactorCampaignCoreV51Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise CrossSchemaFactorCampaignCoreV51Error(message)


def _permutations(seed: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    rng = random.Random(seed ^ 0x51A17)
    states = list(range(10))
    actions = list(range(6))
    rng.shuffle(states)
    rng.shuffle(actions)
    return tuple(states), tuple(actions)


def _interface(seed: int, kernel: Any, config: Mapping[str, Any]):
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
        token = config["terminal_tokens"][
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


def _observe(
    occurrence: int,
    kernel: Any,
    catalogue: tuple[FlatRawActionV4, ...],
    encode: Callable[[Any], tuple[int, ...]],
):
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
                        tuple(row.exchange for row in legal),
                        catalogue[action.exchange],
                        encode(successor),
                        tuple(row.exchange for row in legal_after),
                        None
                        if legal_after
                        else successor.status is CoupledExchangeStatus.SUCCESS,
                    )
                )
                if (
                    successor.status is CoupledExchangeStatus.ACTIVE
                    and successor not in seen
                ):
                    seen.add(successor)
                    queue.append(successor)
    return tuple(rows), labels, len(seen)


def _archive(occurrence, seed, catalogue, rows, labels, reachable, domain):
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
    return {**payload, "raw_observation_id": content_id(domain, payload)}


def _calibrate(
    kernel,
    catalogue,
    encode,
    reference_rows,
    reference_catalogue,
    reference_layout: DiscoveredLayoutV5,
    config,
):
    initial = kernel.initial_distribution()[0][1]
    queue = deque([initial])
    seen = {initial}
    rows = []
    labels = 0
    last_mapping = None
    stable_count = 0
    while queue and labels < config["maximum_target_layout_labels"]:
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
                if (
                    successor.status is CoupledExchangeStatus.ACTIVE
                    and successor not in seen
                ):
                    seen.add(successor)
                    queue.append(successor)
            try:
                layout = match_generic_layout_meta_prior_v5(
                    reference_rows,
                    reference_catalogue,
                    reference_layout,
                    tuple(rows),
                    catalogue,
                    layout_domain=config["domains"]["factor_boundary"],
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
            if labels >= config["maximum_target_layout_labels"]:
                break
    _fail("V51 target calibration did not recover a stable anonymous layout")


def _relations(program: Mapping[str, Any]) -> dict[str, list[list[int]]]:
    encoded = canonical_json_bytes(
        [row["expression"] for row in program["compiled_assignments"]]
    ).decode("utf-8")
    return {
        name: rows
        for name, rows in program["occurrence_bindings"][0]["relations"].items()
        if f'"{name}"' in encoded
    }


def _relation_fields(program: Mapping[str, Any]) -> dict[str, int]:
    result = {}

    def visit(expression):
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


def _recover(program, binding, state, action, actual, name, relation_input, overlay, cap):
    matches = []
    for candidate in range(cap + 1):
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
        _fail("V51 local relation recovery was not unique under the registered cap")
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
        _fail("V51 strict planner found no robust continuation")
    return choices[state], solve.cache_info().currsize, labels


def _episode(seed, arm, actions, tapes, planning, peak, labels, layout_labels, local_labels, failures, success, domain):
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
    return {**payload, "episode_id": content_id(domain, payload)}


def build_cross_schema_factor_campaign_document_v51(
    config: Mapping[str, Any], preregistration_id: str
) -> dict[str, Any]:
    domains = config["domains"]
    predecessor = run_layout_factorization_campaign_v50r1().to_document()
    inherited_models = {
        f"SOURCE_MODEL_{index}": model
        for index, (_name, model) in enumerate(
            sorted(predecessor["world_models"].items())
        )
    }
    library = compile_cross_schema_factor_library_v7(
        inherited_models, factor_domain=domains["factor_library"]
    )

    rows_by_occurrence = {}
    catalogues = {}
    archives = []
    source_labels = 0
    for occurrence, seed in enumerate(config["source_seeds"]):
        kernel, _witness = generate_stochastic_coupled_exchange(
            stage_count=config["source_stage_count"],
            primary_base=config["source_primary_base"],
            seed=seed,
        )
        catalogue, encode = _interface(seed, kernel, config)
        rows, labels, reachable = _observe(occurrence, kernel, catalogue, encode)
        if labels > config["maximum_source_labels_per_occurrence"]:
            _fail("V51 source acquisition exceeded its registered cap")
        rows_by_occurrence[occurrence] = rows
        catalogues[occurrence] = catalogue
        archives.append(
            _archive(
                occurrence,
                seed,
                catalogue,
                rows,
                labels,
                reachable,
                domains["observation"],
            )
        )
        source_labels += labels
    fallback_model = synthesize_layout_factorized_world_model_v6(
        rows_by_occurrence,
        catalogues,
        layout_domain=domains["factor_boundary"],
        program_domain=domains["program"],
        support_domain=domains["support"],
    )
    reference_layout = discover_generic_layout_v5(
        rows_by_occurrence[0], catalogues[0], layout_domain=domains["factor_boundary"]
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
                layout_domain=domains["factor_boundary"],
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
        factor_domain=domains["factor_boundary"],
        program_domain=domains["program"],
        support_domain=domains["support"],
    )
    program = composed_model["compiled_program"]
    if max(
        row["selected_composition_depth"]
        for row in fallback_model["compiled_program"]["candidate_evaluations"]
    ) < 2:
        _fail("V51 higher-order expression composition was not observed")
    if composed_model["reused_factor_count"] < config["minimum_reused_factor_count"]:
        _fail("V51 target reused too few cross-schema factor subprograms")

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
    for episode_index, seed in enumerate(config["target_seeds"]):
        kernel, _witness = generate_stochastic_coupled_exchange(
            stage_count=config["target_stage_count"],
            primary_base=config["target_primary_base"],
            seed=seed,
        )
        catalogue, encode = _interface(seed, kernel, config)
        calibration_rows, layout, layout_labels = _calibrate(
            kernel,
            catalogue,
            encode,
            reference_rows,
            reference_catalogue,
            reference_layout,
            config,
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
            terminal_tokens=config["terminal_tokens"],
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
                        domains["failed_certificate"], failure_payload
                    ),
                }
                failures.append(failure)
                episode_failures += 1
                field = relation_fields[name]
                action = next(
                    row
                    for row in aligned_catalogue
                    if row.fields[field] == relation_input
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
                    for outcome in kernel.step(
                        probe, CoupledExchangeAction(action.key)
                    )
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
                    config["maximum_relation_output_candidate"],
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
                            domains["distinction"], distinction_payload
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
                domains["episode"],
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
            key, compute, labels = _strict_choice(
                kernel, strict_state, strict_cache
            )
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
                domains["episode"],
            )
        )
    if not all(row["success"] for row in structural + strict):
        _fail("V51 matched held-out episode did not reach success")
    if not failures or len(failures) != len(distinctions):
        _fail("V51 certificate-first local recovery path was not observed")

    target_structural_labels = sum(row["ground_support_labels"] for row in structural)
    target_strict_labels = sum(row["ground_support_labels"] for row in strict)
    v50_structural = predecessor["sample_tax"]["structural_total_support_labels"]
    v50_strict = predecessor["sample_tax"]["strict_target_support_labels"]
    cumulative_structural = v50_structural + source_labels + target_structural_labels
    cumulative_strict = v50_strict + target_strict_labels
    sample_payload = {
        "schema": "acfqp.cross_schema_factor_sample_tax.v51",
        "historical_v50r1_structural_labels": v50_structural,
        "historical_v50r1_strict_labels": v50_strict,
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
        "sample_tax_id": content_id(domains["sample_tax"], sample_payload),
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
        "program_id": content_id(domains["program"], fake_payload),
    }
    fake_boundary = discover_factor_boundaries_v7(
        fake_program, factor_domain=domains["factor_boundary"]
    )
    library_signatures = {
        row["signature_sha256"] for row in library["cross_schema_subprograms"]
    }
    fake_signatures = {
        row["signature_sha256"]
        for row in fake_boundary["factors"]
        if row["transferable_without_schema_specific_binding"]
    }
    shared = sorted(library_signatures & fake_signatures)
    if shared:
        _fail("V51 incompatible OOD probe unexpectedly matched the factor library")
    ood_payload = {
        "schema": "acfqp.cross_schema_factor_ood_rejection.v51",
        "candidate_schema_pair": [4, 3],
        "shared_transferable_signature_count": 0,
        "minimum_required_reused_factor_count": config["minimum_reused_factor_count"],
        "prior_transfer_attempted": False,
        "ood_outcome_execution_performed": False,
        "outcome": "STRICT_FACTOR_SIGNATURE_OOD_NO_TRANSFER",
    }
    ood = {
        **ood_payload,
        "ood_rejection_id": content_id(domains["ood"], ood_payload),
    }
    payload = {
        "schema": "acfqp.cross_schema_factor_campaign.v51",
        "preregistration_id": preregistration_id,
        "frozen_v50r1_campaign_id": predecessor["campaign_id"],
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
            "historical_factor_library_source_labels": predecessor["sample_tax"][
                "offline_source_support_labels"
            ],
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
                len(row["factors"])
                for row in library["factor_boundaries"].values()
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
    return {**payload, "campaign_id": content_id(domains["campaign"], payload)}


__all__ = (
    "CrossSchemaFactorCampaignCoreV51Error",
    "build_cross_schema_factor_campaign_document_v51",
)
