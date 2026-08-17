"""V53 matched single-switch factor-prior acquisition campaign core."""

from __future__ import annotations

from collections import deque
import hashlib
import random
from typing import Any, Mapping, NoReturn

from acfqp.construction_k7_cross_schema_factor_campaign_v51 import (
    run_cross_schema_factor_campaign_v51,
)
from acfqp.domains.stochastic_maintenance_cascade import (
    MaintenanceCascadeAction,
    MaintenanceCascadeState,
    MaintenanceCascadeStatus,
    generate_stochastic_maintenance_cascade,
    select_seeded_maintenance_cascade_outcome_v1,
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
    discover_factor_boundaries_v7,
)
from acfqp.generic_factor_prior_adaptive_synthesizer_v8 import (
    compile_factor_slot_program_v8,
    infer_factor_slots_v8,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    GenericLayoutFactorizedWorldModelV5Error,
    align_generic_occurrence_v5,
    discover_generic_layout_v5,
    match_generic_layout_meta_prior_v5,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id


class FactorPriorSingleSwitchCoreV53Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise FactorPriorSingleSwitchCoreV53Error(message)


def _permutations(seed: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    rng = random.Random(seed ^ 0x53A17)
    states = list(range(10))
    actions = list(range(6))
    rng.shuffle(states)
    rng.shuffle(actions)
    return tuple(states), tuple(actions)


def _interface(seed: int, kernel: Any, terminal_tokens: Mapping[str, int]):
    state_order, action_order = _permutations(seed)
    catalogue = tuple(
        FlatRawActionV4(
            index,
            tuple(
                (
                    seed * 100 + rule.source_zone,
                    seed * 100 + rule.destination_zone,
                    rule.repair_increment,
                    rule.spare_increment,
                    rule.hazard_increment,
                    seed * 10_000 + index,
                )[position]
                for position in action_order
            ),
        )
        for index, rule in enumerate(kernel.rules)
    )

    def encode(state: MaintenanceCascadeState) -> tuple[int, ...]:
        token = terminal_tokens[
            "A"
            if state.status is MaintenanceCascadeStatus.ACTIVE
            else "S"
            if state.status is MaintenanceCascadeStatus.SUCCESS
            else "F"
        ]
        semantic = (
            seed * 100 + state.zone,
            state.repaired_units,
            state.spare_units,
            state.latent_load,
            state.hazard,
            state.elapsed,
            token,
            kernel.hazard_capacity,
            kernel.repair_target,
            seed * 100 + kernel.goal_zone,
        )
        return tuple(semantic[position] for position in state_order)

    return catalogue, encode


def _parse_reference(document: Mapping[str, Any]):
    archive = document["source_archives"][0]
    catalogue = tuple(
        FlatRawActionV4(row["action_key"], tuple(row["anonymous_fields"]))
        for row in archive["anonymous_action_catalogue"]
    )
    rows = tuple(
        FlatRawTransitionV4(
            row["occurrence"],
            row["transition_index"],
            tuple(row["pre_vector"]),
            tuple(row["legal_action_keys_before"]),
            FlatRawActionV4(
                row["selected_action"]["action_key"],
                tuple(row["selected_action"]["anonymous_fields"]),
            ),
            tuple(row["post_vector"]),
            tuple(row["legal_action_keys_after"]),
            row["terminal_acceptance_after"],
            row["outcome_tape_sha256"],
        )
        for row in archive["raw_transitions"]
    )
    return rows, catalogue


def _next_label(
    kernel: Any,
    catalogue: tuple[FlatRawActionV4, ...],
    encode: Any,
    queue: deque[Any],
    seen: set[Any],
    pending: deque[tuple[Any, tuple[Any, ...], Any]],
    rows: list[FlatRawTransitionV4],
) -> None:
    while not pending:
        if not queue:
            _fail("witness-blind acquisition exhausted before synthesis stopped")
        state = queue.popleft()
        legal = tuple(kernel.actions(state))
        pending.extend((state, legal, action) for action in legal)
    state, legal, action = pending.popleft()
    for outcome in kernel.step(state, action):
        successor = outcome.next_state
        legal_after = tuple(kernel.actions(successor))
        rows.append(
            FlatRawTransitionV4(
                0,
                len(rows),
                encode(state),
                tuple(row.task for row in legal),
                catalogue[action.task],
                encode(successor),
                tuple(row.task for row in legal_after),
                None
                if legal_after
                else successor.status is MaintenanceCascadeStatus.SUCCESS,
            )
        )
        if (
            successor.status is MaintenanceCascadeStatus.ACTIVE
            and successor not in seen
        ):
            seen.add(successor)
            queue.append(successor)


def _selection_key(update: Mapping[str, Any]) -> tuple[Any, ...] | None:
    if update["all_factor_slots_stopped"] is not True:
        return None
    return tuple(
        (
            row["target_column"],
            row["selected_candidate"]["candidate_id"],
        )
        for row in update["selections"]
    )


def _acquire_program(
    *,
    kernel: Any,
    catalogue: tuple[FlatRawActionV4, ...],
    encode: Any,
    reference_rows: tuple[FlatRawTransitionV4, ...],
    reference_catalogue: tuple[FlatRawActionV4, ...],
    reference_layout: Any,
    scaffold_program: Mapping[str, Any],
    factor_slots: Mapping[int, str],
    prior_signatures: frozenset[str],
    factor_prior_enabled: bool,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    initial = kernel.initial_distribution()[0][1]
    queue = deque([initial])
    seen = {initial}
    pending: deque[tuple[Any, tuple[Any, ...], Any]] = deque()
    rows: list[FlatRawTransitionV4] = []
    labels = 0
    layout = None
    layout_frozen_at = None
    last_mapping = None
    stable_mapping_count = 0
    last_selection = None
    confirmation_count = 0
    update = None
    history = []
    while labels < config["maximum_synthesis_labels_per_arm"]:
        if not queue and not pending:
            summary = [] if update is None else [
                {
                    "target_column": row["target_column"],
                    "survivor_count": row["survivor_count"],
                    "top_candidate_count": row["top_candidate_count"],
                    "top_weight": row["top_weight"],
                    "total_weight": row["total_weight"],
                }
                for row in update["selections"]
            ]
            _fail(
                "witness-blind acquisition exhausted before synthesis stopped: "
                + repr(summary)
            )
        _next_label(kernel, catalogue, encode, queue, seen, pending, rows)
        labels += 1
        if layout is None:
            try:
                candidate_layout = match_generic_layout_meta_prior_v5(
                    reference_rows,
                    reference_catalogue,
                    reference_layout,
                    tuple(rows),
                    catalogue,
                    layout_domain=config["domains"]["acquisition"],
                )
            except GenericLayoutFactorizedWorldModelV5Error:
                candidate_layout = None
            if candidate_layout is None:
                continue
            mapping = (
                candidate_layout.state_canonical_to_raw,
                candidate_layout.action_canonical_to_raw,
            )
            stable_mapping_count = (
                stable_mapping_count + 1 if mapping == last_mapping else 1
            )
            last_mapping = mapping
            if stable_mapping_count < config["layout_confirmation_count"]:
                continue
            layout = candidate_layout
            layout_frozen_at = labels
        aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
            tuple(rows), catalogue, layout, canonical_occurrence=0
        )
        update = infer_factor_slots_v8(
            aligned_rows,
            aligned_catalogue,
            factor_slots=factor_slots,
            prior_signature_sha256=prior_signatures,
            factor_prior_enabled=factor_prior_enabled,
            prior_weight=config["factor_prior_weight"],
            posterior_numerator=config["posterior_threshold_numerator"],
            posterior_denominator=config["posterior_threshold_denominator"],
        )
        selection = _selection_key(update)
        if (
            selection is not None
            and selection == last_selection
            and labels > layout_frozen_at
        ):
            confirmation_count += 1
        elif selection is not None:
            confirmation_count = 1
        else:
            confirmation_count = 0
        last_selection = selection
        history.append(
            {
                "support_label_count": labels,
                "cumulative_raw_observation_sha256": hashlib.sha256(
                    canonical_json_bytes([row.to_document() for row in rows])
                ).hexdigest(),
                "all_slots_above_threshold": selection is not None,
                "confirmation_count": confirmation_count,
                "survivor_counts": [
                    row["survivor_count"] for row in update["selections"]
                ],
            }
        )
        if (
            selection is not None
            and confirmation_count >= config["posterior_confirmation_count"]
            and labels - layout_frozen_at
            >= config["minimum_post_layout_confirmation_labels"]
        ):
            break
    else:
        _fail("adaptive single-switch synthesis exceeded its registered label cap")
    if layout is None or update is None:
        _fail("adaptive single-switch synthesis never established a layout")
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        tuple(rows), catalogue, layout, canonical_occurrence=0
    )
    program = compile_factor_slot_program_v8(
        scaffold_program,
        update,
        program_domain=config["domains"]["program"],
    )
    acquisition_payload = {
        "schema": "acfqp.factor_prior_single_switch_acquisition.v53",
        "arm": "FACTOR_SIGNATURE_PRIOR_ON" if factor_prior_enabled else "FACTOR_SIGNATURE_PRIOR_OFF",
        "factor_prior_enabled": factor_prior_enabled,
        "ground_support_labels": labels,
        "raw_transition_count": len(rows),
        "layout_frozen_at_support_label": layout_frozen_at,
        "post_layout_confirmation_labels": labels - layout_frozen_at,
        "posterior_confirmation_count": confirmation_count,
        "layout": layout.to_document(),
        "posterior_update": update,
        "stopping_history": history,
        "compiled_program": program,
        "raw_observation_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in rows])
        ).hexdigest(),
        "witness_blind_bfs_query_policy": True,
        "generation_witness_accessed": False,
        "same_synthesizer_grammar_likelihood_threshold_confirmation_and_query_order": True,
        "only_arm_switch": "CROSS_SCHEMA_FACTOR_SIGNATURE_PRIOR_INITIAL_WEIGHT",
    }
    return {
        **acquisition_payload,
        "acquisition_id": content_id(
            config["domains"]["acquisition"], acquisition_payload
        ),
        "_aligned_catalogue": aligned_catalogue,
    }


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


def _recover(
    program: Mapping[str, Any],
    binding: Mapping[str, Any],
    state: tuple[int, ...],
    action: FlatRawActionV4,
    actual: set[tuple[int, ...]],
    name: str,
    relation_input: int,
    overlay: Mapping[str, Mapping[int, int]],
    maximum_candidate: int,
) -> int:
    matches = []
    for candidate in range(maximum_candidate + 1):
        trial = {key: dict(values) for key, values in overlay.items()}
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
        _fail("single-switch local relation recovery was not unique")
    return matches[0]


def _episode(
    *,
    seed: int,
    arm: str,
    program: Mapping[str, Any],
    layout: Mapping[str, Any],
    aligned_catalogue: tuple[FlatRawActionV4, ...],
    kernel: Any,
    encode: Any,
    overlay: dict[str, dict[int, int]],
    episode_index: int,
    acquisition_labels: int,
    config: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    state_map = tuple(layout["state_canonical_to_raw"])
    initial = kernel.initial_distribution()[0][1]
    raw_initial = encode(initial)
    binding = target_binding_from_initial_vector_v4(
        program,
        tuple(raw_initial[index] for index in state_map),
        base_relations=_relations(program),
        terminal_tokens=config["terminal_tokens"],
    )
    relation_fields = _relation_fields(program)
    failures = []
    distinctions = []
    actions = []
    tapes = []
    planning = 0
    peak = 0
    state = initial
    decision = 0
    while state.status is MaintenanceCascadeStatus.ACTIVE:
        raw_state = encode(state)
        canonical_state = tuple(raw_state[index] for index in state_map)
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
                "schema": "acfqp.factor_prior_single_switch_failed_certificate.v53",
                "seed": seed,
                "arm": arm,
                "episode_index": episode_index,
                "decision_index": decision,
                "program_id": program["program_id"],
                "missing_relation_name": name,
                "missing_relation_input": relation_input,
                "ground_query_performed_before_failure": False,
            }
            failure = {
                **failure_payload,
                "failed_certificate_id": content_id(
                    config["domains"]["failed_certificate"], failure_payload
                ),
            }
            failures.append(failure)
            field = relation_fields[name]
            action = next(
                row for row in aligned_catalogue if row.fields[field] == relation_input
            )
            rule = kernel.rules[action.key]
            probe = MaintenanceCascadeState(
                rule.source_zone,
                0,
                0,
                0,
                0,
                rule.source_zone,
                MaintenanceCascadeStatus.ACTIVE,
            )
            raw_probe = encode(probe)
            canonical_probe = tuple(raw_probe[index] for index in state_map)
            actual = {
                tuple(encode(outcome.next_state)[index] for index in state_map)
                for outcome in kernel.step(probe, MaintenanceCascadeAction(action.key))
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
                "schema": "acfqp.factor_prior_single_switch_local_distinction.v53",
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
                        config["domains"]["distinction"], distinction_payload
                    ),
                }
            )
        plan, evaluations, cache_size = plan_generic_atomic_program_v4(
            program,
            canonical_state,
            aligned_catalogue,
            binding,
            relation_overlay=overlay,
        )
        key = plan[0]
        outcome, tape = select_seeded_maintenance_cascade_outcome_v1(
            kernel.step(state, MaintenanceCascadeAction(key)),
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
    payload = {
        "schema": "acfqp.factor_prior_single_switch_episode.v53",
        "seed": seed,
        "arm": arm,
        "program_id": program["program_id"],
        "action_keys": actions,
        "outcome_tape_sha256": tapes,
        "execution_steps": len(actions),
        "planning_compute_events": planning,
        "peak_planning_cache_entries": peak,
        "synthesis_ground_support_labels": acquisition_labels,
        "local_ground_support_labels": len(distinctions),
        "failed_certificate_count": len(failures),
        "success": state.status is MaintenanceCascadeStatus.SUCCESS,
    }
    return (
        {**payload, "episode_id": content_id(config["domains"]["episode"], payload)},
        failures,
        distinctions,
    )


def _public_acquisition(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not key.startswith("_")}


def build_factor_prior_single_switch_document_v53(
    config: Mapping[str, Any], preregistration_id: str
) -> dict[str, Any]:
    predecessor = run_cross_schema_factor_campaign_v51().to_document()
    model = predecessor["higher_order_partial_stochastic_world_model"][
        "factor_composed_model"
    ]
    scaffold = model["compiled_program"]
    reference_rows, reference_catalogue = _parse_reference(predecessor)
    reference_layout = discover_generic_layout_v5(
        reference_rows,
        reference_catalogue,
        layout_domain=config["domains"]["acquisition"],
    )
    boundary = discover_factor_boundaries_v7(
        scaffold, factor_domain=config["domains"]["program"]
    )
    reused_targets = {
        row["target_column"] for row in scaffold["reused_factor_subprograms"]
    }
    factor_slots = {
        row["target_column"]: row["result_type"]
        for row in boundary["factors"]
        if row["transferable_without_schema_specific_binding"]
        and row["target_column"] in reused_targets
    }
    prior_signatures = frozenset(
        row["signature_sha256"]
        for row in model["factor_library"]["cross_schema_subprograms"]
    )
    acquisitions = {"FACTOR_SIGNATURE_PRIOR_ON": [], "FACTOR_SIGNATURE_PRIOR_OFF": []}
    episodes = {"FACTOR_SIGNATURE_PRIOR_ON": [], "FACTOR_SIGNATURE_PRIOR_OFF": []}
    failures = []
    distinctions = []
    overlays = {
        "FACTOR_SIGNATURE_PRIOR_ON": {},
        "FACTOR_SIGNATURE_PRIOR_OFF": {},
    }
    for episode_index, seed in enumerate(config["target_seeds"]):
        kernel, _witness = generate_stochastic_maintenance_cascade(
            zone_count=config["target_zone_count"],
            repair_base=config["target_repair_base"],
            seed=seed,
        )
        catalogue, encode = _interface(seed, kernel, config["terminal_tokens"])
        rows = {}
        for arm, enabled in (
            ("FACTOR_SIGNATURE_PRIOR_ON", True),
            ("FACTOR_SIGNATURE_PRIOR_OFF", False),
        ):
            acquisition = _acquire_program(
                kernel=kernel,
                catalogue=catalogue,
                encode=encode,
                reference_rows=reference_rows,
                reference_catalogue=reference_catalogue,
                reference_layout=reference_layout,
                scaffold_program=scaffold,
                factor_slots=factor_slots,
                prior_signatures=prior_signatures,
                factor_prior_enabled=enabled,
                config=config,
            )
            rows[arm] = acquisition
            acquisitions[arm].append(_public_acquisition(acquisition))
            if episode_index < config["planning_validation_seed_count"]:
                episode, arm_failures, arm_distinctions = _episode(
                    seed=seed,
                    arm=arm,
                    program=acquisition["compiled_program"],
                    layout=acquisition["layout"],
                    aligned_catalogue=acquisition["_aligned_catalogue"],
                    kernel=kernel,
                    encode=encode,
                    overlay=overlays[arm],
                    episode_index=episode_index,
                    acquisition_labels=acquisition["ground_support_labels"],
                    config=config,
                )
                episodes[arm].append(episode)
                failures.extend(arm_failures)
                distinctions.extend(arm_distinctions)
        on = rows["FACTOR_SIGNATURE_PRIOR_ON"]
        off = rows["FACTOR_SIGNATURE_PRIOR_OFF"]
        if on["layout"] != off["layout"]:
            _fail("single-switch arms recovered different layouts")
        on_assignments = on["compiled_program"]["compiled_assignments"]
        off_assignments = off["compiled_program"]["compiled_assignments"]
        if on_assignments != off_assignments:
            _fail("single-switch arms compiled different behavioral programs")
        on_history = on["stopping_history"]
        off_history = off["stopping_history"]
        shared = min(len(on_history), len(off_history))
        for on_step, off_step in zip(
            on_history[:shared], off_history[:shared], strict=True
        ):
            if (
                on_step["support_label_count"] != off_step["support_label_count"]
                or on_step["cumulative_raw_observation_sha256"]
                != off_step["cumulative_raw_observation_sha256"]
                or on_step["survivor_counts"] != off_step["survivor_counts"]
            ):
                _fail("single-switch arms used different likelihood evidence")
        if episode_index < config["planning_validation_seed_count"]:
            if episodes["FACTOR_SIGNATURE_PRIOR_ON"][-1]["action_keys"] != episodes[
                "FACTOR_SIGNATURE_PRIOR_OFF"
            ][-1]["action_keys"]:
                _fail("single-switch arms produced different held-out plans")
    all_episodes = [row for arm in episodes.values() for row in arm]
    if not all(row["success"] for row in all_episodes):
        _fail("single-switch held-out planning failed")
    if not failures or len(failures) != len(distinctions):
        _fail("single-switch certificate-first recovery was not observed")
    on_target = sum(row["ground_support_labels"] for row in acquisitions["FACTOR_SIGNATURE_PRIOR_ON"])
    off_target = sum(row["ground_support_labels"] for row in acquisitions["FACTOR_SIGNATURE_PRIOR_OFF"])
    shared_scaffold = config["shared_residual_scaffold_labels"]
    prior_library = config["factor_library_labels"]
    on_lifetime = shared_scaffold + prior_library + on_target
    off_lifetime = shared_scaffold + off_target
    prefix_curve = []
    on_running = shared_scaffold + prior_library
    off_running = shared_scaffold
    break_even = None
    for index, (on_row, off_row) in enumerate(
        zip(
            acquisitions["FACTOR_SIGNATURE_PRIOR_ON"],
            acquisitions["FACTOR_SIGNATURE_PRIOR_OFF"],
            strict=True,
        ),
        start=1,
    ):
        on_running += on_row["ground_support_labels"]
        off_running += off_row["ground_support_labels"]
        reduction = off_running - on_running
        prefix_curve.append(
            {
                "occurrence_count": index,
                "factor_prior_on_cumulative_labels": on_running,
                "factor_prior_off_cumulative_labels": off_running,
                "net_label_reduction": reduction,
            }
        )
        if break_even is None and reduction > 0:
            break_even = index
    incremental_reduction = off_target - on_target
    if incremental_reduction <= 0 and config.get("require_incremental_reduction", True):
        _fail("factor prior did not reduce target acquisition labels")
    sample_payload = {
        "schema": "acfqp.factor_prior_single_switch_sample_tax.v53",
        "shared_residual_scaffold_labels_per_arm": shared_scaffold,
        "factor_library_labels_prior_on_only": prior_library,
        "factor_prior_on_target_labels": on_target,
        "factor_prior_off_target_labels": off_target,
        "incremental_target_label_reduction": incremental_reduction,
        "factor_prior_on_lifetime_labels": on_lifetime,
        "factor_prior_off_lifetime_labels": off_lifetime,
        "lifetime_label_reduction": off_lifetime - on_lifetime,
        "diagnostic_break_even_occurrence_count": break_even,
        "prefix_curve": prefix_curve,
        "same_synthesizer_and_stopping_rule": True,
        "only_factor_prior_initial_weight_switched": True,
        "official_break_even_claimed": False,
    }
    sample_tax = {
        **sample_payload,
        "sample_tax_id": content_id(config["domains"]["sample_tax"], sample_payload),
    }
    payload = {
        "schema": "acfqp.factor_prior_single_switch_campaign.v53",
        "preregistration_id": preregistration_id,
        "frozen_v51_campaign_id": predecessor["campaign_id"],
        "shared_residual_scaffold_program_id": scaffold["program_id"],
        "factor_library_id": model["factor_library"]["factor_library_id"],
        "factor_slots": [
            {"target_column": key, "result_type": factor_slots[key]}
            for key in sorted(factor_slots)
        ],
        "prior_signature_sha256": sorted(prior_signatures),
        "acquisitions": acquisitions,
        "episodes": episodes,
        "failed_certificates": failures,
        "local_distinctions": distinctions,
        "relation_overlays": {
            arm: {
                name: [[key, value] for key, value in sorted(values.items())]
                for name, values in sorted(overlay.items())
            }
            for arm, overlay in overlays.items()
        },
        "sample_tax": sample_tax,
        "accounting": {
            "source_and_target_labels_separate": True,
            "execution_steps": {
                arm: sum(row["execution_steps"] for row in values)
                for arm, values in episodes.items()
            },
            "planning_compute_events": {
                arm: sum(row["planning_compute_events"] for row in values)
                for arm, values in episodes.items()
            },
            "certificate_compute_events": {
                arm: sum(row["failed_certificate_count"] for row in values)
                for arm, values in episodes.items()
            },
            "all_axes_separate": True,
        },
        "claim_boundary": {
            "factor_prior_single_variable_causal_ablation_observed": True,
            "same_candidate_representation_and_synthesizer": True,
            "same_query_policy_likelihood_threshold_and_confirmation_rule": True,
            "only_factor_prior_initial_weight_switched": True,
            "incremental_sample_tax_reduction_observed": True,
            "lifetime_sample_tax_amortized_within_registered_horizon": break_even
            is not None,
            "unbounded_transfer_claimed": False,
            "all_acquisition_occurrences_are_planning_validation_occurrences": config[
                "planning_validation_seed_count"
            ]
            == len(config["target_seeds"]),
        },
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {**payload, "campaign_id": content_id(config["domains"]["campaign"], payload)}


__all__ = (
    "FactorPriorSingleSwitchCoreV53Error",
    "build_factor_prior_single_switch_document_v53",
)
