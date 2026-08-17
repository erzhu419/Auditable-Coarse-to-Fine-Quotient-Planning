"""Matched V52 factor-composed-prior versus strict-no-prior acquisition.

The prior arm receives only the frozen V51 anonymous compiled program and its
factor-library provenance.  It acquires a witness-blind layout calibration and
then requests a local ground support only after a compiled relation certificate
fails.  The no-prior arm cannot read either artifact; it acquires the complete
reachable state-action support of each occurrence before planning.  Both arms
use the same initial seed and deterministic outcome-tape schedule.  Historical
prior labels, target labels, execution, planning, and certificate work remain
separate axes.
"""

from __future__ import annotations

from collections import deque
from functools import lru_cache
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
from acfqp.generic_layout_factorized_world_model_v5 import (
    GenericLayoutFactorizedWorldModelV5Error,
    align_generic_occurrence_v5,
    discover_generic_layout_v5,
    match_generic_layout_meta_prior_v5,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id


class FactorPriorAcquisitionAblationCoreV52Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise FactorPriorAcquisitionAblationCoreV52Error(message)


def _permutations(seed: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    rng = random.Random(seed ^ 0x52A17)
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


def _parse_v51_reference(document: Mapping[str, Any]):
    archive = document["source_archives"][0]
    catalogue = tuple(
        FlatRawActionV4(row["action_key"], tuple(row["anonymous_fields"]))
        for row in archive["anonymous_action_catalogue"]
    )
    rows = []
    for row in archive["raw_transitions"]:
        selected = row["selected_action"]
        rows.append(
            FlatRawTransitionV4(
                row["occurrence"],
                row["transition_index"],
                tuple(row["pre_vector"]),
                tuple(row["legal_action_keys_before"]),
                FlatRawActionV4(
                    selected["action_key"], tuple(selected["anonymous_fields"])
                ),
                tuple(row["post_vector"]),
                tuple(row["legal_action_keys_after"]),
                row["terminal_acceptance_after"],
                row["outcome_tape_sha256"],
            )
        )
    return tuple(rows), catalogue


def _calibrate(
    kernel: Any,
    catalogue: tuple[FlatRawActionV4, ...],
    encode: Any,
    reference_rows: tuple[FlatRawTransitionV4, ...],
    reference_catalogue: tuple[FlatRawActionV4, ...],
    reference_layout: Any,
    *,
    maximum_labels: int,
    layout_domain: str,
):
    initial = kernel.initial_distribution()[0][1]
    queue = deque([initial])
    seen = {initial}
    rows = []
    labels = 0
    last_mapping = None
    stable_count = 0
    while queue and labels < maximum_labels:
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
    _fail("V52 factor-prior calibration exceeded its registered label cap")


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
        _fail("V52 local relation recovery was not unique")
    return matches[0]


def _acquire_no_prior_exact_support(kernel: Any, encode: Any):
    initial = kernel.initial_distribution()[0][1]
    queue = deque([initial])
    seen = {initial}
    cache = {}
    rows = []
    labels = 0
    while queue:
        state = queue.popleft()
        legal = kernel.actions(state)
        for action in legal:
            labels += 1
            successors = tuple(row.next_state for row in kernel.step(state, action))
            cache[(state, action.task)] = successors
            rows.append(
                {
                    "pre": list(encode(state)),
                    "action_key": action.task,
                    "post_support": sorted([list(encode(row)) for row in successors]),
                }
            )
            for successor in successors:
                if (
                    successor.status is MaintenanceCascadeStatus.ACTIVE
                    and successor not in seen
                ):
                    seen.add(successor)
                    queue.append(successor)
    return (
        cache,
        labels,
        len(seen),
        hashlib.sha256(canonical_json_bytes(rows)).hexdigest(),
    )


def _no_prior_choice(kernel: Any, state: MaintenanceCascadeState, cache: Mapping[Any, Any]):
    choices = {}
    compute = 0

    @lru_cache(maxsize=None)
    def solve(current: MaintenanceCascadeState) -> bool:
        nonlocal compute
        compute += 1
        if current.status is MaintenanceCascadeStatus.SUCCESS:
            return True
        if current.status is MaintenanceCascadeStatus.FAILURE:
            return False
        for action in kernel.actions(current):
            compute += 1
            successors = cache[(current, action.task)]
            if all(solve(successor) for successor in successors):
                choices[current] = action.task
                return True
        return False

    if not solve(state) or state not in choices:
        _fail("V52 no-prior exact planner found no robust continuation")
    return choices[state], compute, solve.cache_info().currsize


def _episode(
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
    domain: str,
):
    payload = {
        "schema": "acfqp.factor_prior_acquisition_ablation_episode.v52",
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


def build_factor_prior_acquisition_ablation_document_v52(
    config: Mapping[str, Any], preregistration_id: str
) -> dict[str, Any]:
    domains = config["domains"]
    predecessor = run_cross_schema_factor_campaign_v51().to_document()
    model = predecessor["higher_order_partial_stochastic_world_model"][
        "factor_composed_model"
    ]
    program = model["compiled_program"]
    if model["reused_factor_count"] < config["minimum_reused_factor_count"]:
        _fail("V52 predecessor factor prior lost its registered reuse evidence")
    reference_rows, reference_catalogue = _parse_v51_reference(predecessor)
    reference_layout = discover_generic_layout_v5(
        reference_rows,
        reference_catalogue,
        layout_domain=domains["acquisition"],
    )
    base_relations = _relations(program)
    relation_fields = _relation_fields(program)
    overlay: dict[str, dict[int, int]] = {}
    prior_acquisitions = []
    no_prior_acquisitions = []
    failures = []
    distinctions = []
    prior_episodes = []
    no_prior_episodes = []

    for episode_index, seed in enumerate(config["target_seeds"]):
        kernel, _generation_witness = generate_stochastic_maintenance_cascade(
            zone_count=config["target_zone_count"],
            repair_base=config["target_repair_base"],
            seed=seed,
        )
        catalogue, encode = _interface(seed, kernel, config["terminal_tokens"])
        calibration_rows, layout, layout_labels = _calibrate(
            kernel,
            catalogue,
            encode,
            reference_rows,
            reference_catalogue,
            reference_layout,
            maximum_labels=config["maximum_prior_layout_labels"],
            layout_domain=domains["acquisition"],
        )
        _aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
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
        while state.status is MaintenanceCascadeStatus.ACTIVE:
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
                    "schema": "acfqp.factor_prior_ablation_failed_certificate.v52",
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
                canonical_probe = tuple(
                    raw_probe[index] for index in layout.state_canonical_to_raw
                )
                actual = {
                    tuple(
                        encode(outcome.next_state)[index]
                        for index in layout.state_canonical_to_raw
                    )
                    for outcome in kernel.step(
                        probe, MaintenanceCascadeAction(action.key)
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
                    "schema": "acfqp.factor_prior_ablation_local_distinction.v52",
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
        prior_label_count = layout_labels + local_labels
        prior_acquisition_payload = {
            "schema": "acfqp.factor_prior_acquisition.v52",
            "seed": seed,
            "arm": "FACTOR_COMPOSED_WORLD_MODEL_PRIOR",
            "layout_support_labels": layout_labels,
            "local_post_certificate_support_labels": local_labels,
            "total_ground_support_labels": prior_label_count,
            "raw_calibration_transition_count": len(calibration_rows),
            "layout": layout.to_document(),
            "factor_library_id": model["factor_library"]["factor_library_id"],
            "factor_composed_program_id": program["program_id"],
            "generation_witness_accessed": False,
            "ground_query_before_failed_certificate": False,
        }
        prior_acquisitions.append(
            {
                **prior_acquisition_payload,
                "acquisition_id": content_id(
                    domains["acquisition"], prior_acquisition_payload
                ),
            }
        )
        prior_episodes.append(
            _episode(
                seed,
                "FACTOR_COMPOSED_WORLD_MODEL_PRIOR",
                actions,
                tapes,
                planning,
                peak,
                prior_label_count,
                layout_labels,
                local_labels,
                episode_failures,
                state.status is MaintenanceCascadeStatus.SUCCESS,
                domains["episode"],
            )
        )

        exact_cache, exact_labels, reachable, exact_digest = (
            _acquire_no_prior_exact_support(kernel, encode)
        )
        no_prior_acquisition_payload = {
            "schema": "acfqp.factor_prior_acquisition.v52",
            "seed": seed,
            "arm": "STRICT_WITNESS_BLIND_EXACT_ACQUISITION_NO_PRIOR",
            "total_ground_support_labels": exact_labels,
            "reachable_active_state_count": reachable,
            "exact_raw_support_sha256": exact_digest,
            "factor_library_accessed": False,
            "compiled_prior_accessed": False,
            "generation_witness_accessed": False,
            "policy": "WITNESS_BLIND_EXHAUSTIVE_REACHABLE_STATE_ACTION_SUPPORT",
        }
        no_prior_acquisitions.append(
            {
                **no_prior_acquisition_payload,
                "acquisition_id": content_id(
                    domains["acquisition"], no_prior_acquisition_payload
                ),
            }
        )
        exact_actions = []
        exact_tapes = []
        exact_planning = 0
        exact_peak = 0
        exact_state = initial
        exact_decision = 0
        while exact_state.status is MaintenanceCascadeStatus.ACTIVE:
            key, compute, cache_size = _no_prior_choice(
                kernel, exact_state, exact_cache
            )
            outcome, tape = select_seeded_maintenance_cascade_outcome_v1(
                kernel.step(exact_state, MaintenanceCascadeAction(key)),
                seed=seed,
                episode_index=episode_index,
                decision_index=exact_decision,
            )
            exact_state = outcome.next_state
            exact_actions.append(key)
            exact_tapes.append(tape)
            exact_planning += compute
            exact_peak = max(exact_peak, cache_size)
            exact_decision += 1
        no_prior_episodes.append(
            _episode(
                seed,
                "STRICT_WITNESS_BLIND_EXACT_ACQUISITION_NO_PRIOR",
                exact_actions,
                exact_tapes,
                exact_planning,
                exact_peak,
                exact_labels,
                0,
                0,
                0,
                exact_state.status is MaintenanceCascadeStatus.SUCCESS,
                domains["episode"],
            )
        )

    if not all(row["success"] for row in prior_episodes + no_prior_episodes):
        _fail("V52 matched acquisition arm failed a held-out occurrence")
    if not failures or len(failures) != len(distinctions):
        _fail("V52 certificate-first local recovery was not observed")
    prior_target_labels = sum(
        row["total_ground_support_labels"] for row in prior_acquisitions
    )
    no_prior_target_labels = sum(
        row["total_ground_support_labels"] for row in no_prior_acquisitions
    )
    offline_labels = config["historical_factor_prior_labels"]
    prior_cumulative = offline_labels + prior_target_labels
    reduction = no_prior_target_labels - prior_cumulative
    prefixes = []
    prior_running = offline_labels
    no_prior_running = 0
    break_even = None
    for index, (prior_row, no_prior_row) in enumerate(
        zip(prior_acquisitions, no_prior_acquisitions, strict=True), start=1
    ):
        prior_running += prior_row["total_ground_support_labels"]
        no_prior_running += no_prior_row["total_ground_support_labels"]
        prefixes.append(
            {
                "occurrence_count": index,
                "factor_prior_cumulative_labels": prior_running,
                "no_prior_cumulative_labels": no_prior_running,
                "net_label_reduction": no_prior_running - prior_running,
            }
        )
        if break_even is None and prior_running < no_prior_running:
            break_even = index
    if reduction <= 0 or break_even is None:
        _fail("V52 factor-prior acquisition did not amortize its frozen sample tax")
    sample_payload = {
        "schema": "acfqp.factor_prior_acquisition_sample_tax.v52",
        "historical_factor_prior_labels": offline_labels,
        "factor_prior_target_labels": prior_target_labels,
        "no_prior_target_labels": no_prior_target_labels,
        "factor_prior_cumulative_labels": prior_cumulative,
        "no_prior_cumulative_labels": no_prior_target_labels,
        "cumulative_label_reduction": reduction,
        "registered_break_even_occurrence_count": break_even,
        "prefix_curve": prefixes,
        "sample_labels_separate_from_execution_and_compute": True,
        "individual_factor_only_causal_effect_claimed": False,
        "factor_composed_prior_pipeline_causal_contrast_observed": True,
        "official_break_even_claimed": False,
    }
    sample_tax = {
        **sample_payload,
        "sample_tax_id": content_id(domains["sample_tax"], sample_payload),
    }
    payload = {
        "schema": "acfqp.factor_prior_acquisition_ablation_campaign.v52",
        "preregistration_id": preregistration_id,
        "frozen_v51_campaign_id": predecessor["campaign_id"],
        "frozen_v51_factor_library_id": model["factor_library"]["factor_library_id"],
        "frozen_v51_factor_composed_program_id": program["program_id"],
        "frozen_v51_reused_factor_count": model["reused_factor_count"],
        "factor_prior_acquisitions": prior_acquisitions,
        "no_prior_acquisitions": no_prior_acquisitions,
        "failed_certificates": failures,
        "local_distinctions": distinctions,
        "relation_overlay": {
            name: [[key, value] for key, value in sorted(rows.items())]
            for name, rows in sorted(overlay.items())
        },
        "factor_prior_episodes": prior_episodes,
        "no_prior_episodes": no_prior_episodes,
        "sample_tax": sample_tax,
        "accounting": {
            "historical_factor_prior_labels": offline_labels,
            "factor_prior_target_layout_labels": sum(
                row["layout_support_labels"] for row in prior_acquisitions
            ),
            "factor_prior_local_ground_labels": sum(
                row["local_post_certificate_support_labels"]
                for row in prior_acquisitions
            ),
            "no_prior_exact_ground_labels": no_prior_target_labels,
            "factor_prior_execution_steps": sum(
                row["execution_steps"] for row in prior_episodes
            ),
            "no_prior_execution_steps": sum(
                row["execution_steps"] for row in no_prior_episodes
            ),
            "factor_prior_planning_compute_events": sum(
                row["planning_compute_events"] for row in prior_episodes
            ),
            "no_prior_planning_compute_events": sum(
                row["planning_compute_events"] for row in no_prior_episodes
            ),
            "certificate_compute_events": len(failures),
            "all_axes_separate": True,
        },
        "claim_boundary": {
            "matched_factor_composed_prior_vs_no_prior_acquisition_observed": True,
            "historical_prior_sample_tax_fully_included": True,
            "cross_occurrence_amortized_sample_reduction_observed": True,
            "individual_factor_only_causal_effect_claimed": False,
            "unbounded_domain_or_schema_transfer_claimed": False,
            "fallback_compute_reclassified_as_sample_labels": False,
        },
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {**payload, "campaign_id": content_id(domains["campaign"], payload)}


__all__ = (
    "FactorPriorAcquisitionAblationCoreV52Error",
    "build_factor_prior_acquisition_ablation_document_v52",
)
