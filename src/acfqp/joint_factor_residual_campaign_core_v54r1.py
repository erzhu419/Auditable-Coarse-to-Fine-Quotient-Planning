"""Fresh V54r1 successor with symmetry-free witness-blind layout evidence."""

from __future__ import annotations

from collections import deque
from functools import lru_cache
import random
from typing import Any, Mapping, NoReturn

from acfqp.domains.stochastic_balanced_batch_refinement import (
    generate_stochastic_balanced_batch_refinement,
)
from acfqp.domains.stochastic_batch_refinement import (
    BatchRefinementAction,
    BatchRefinementState,
    BatchRefinementStatus,
    select_seeded_batch_refinement_outcome_v1,
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
from acfqp.generic_joint_factor_residual_world_model_v9 import (
    synthesize_joint_factor_residual_world_model_v9,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    align_generic_occurrence_v5,
    discover_generic_layout_v5,
    match_generic_layout_meta_prior_v5,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id


class JointFactorResidualCampaignCoreV54R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise JointFactorResidualCampaignCoreV54R1Error(message)


def _interface(seed: int, kernel: Any, tokens: Mapping[str, int]):
    state_order = list(range(6))
    action_order = list(range(5))
    random.Random(seed ^ 0x54A17).shuffle(state_order)
    random.Random(seed ^ 0x54B29).shuffle(action_order)
    catalogue = []
    for key, rule in enumerate(kernel.rules):
        semantic = (
            rule.source_stage,
            rule.anonymous_advance_class,
            rule.unit_increment,
            rule.risk_increment,
            1,
        )
        catalogue.append(
            FlatRawActionV4(
                key, tuple(semantic[index] for index in action_order)
            )
        )

    def encode(state: BatchRefinementState) -> tuple[int, ...]:
        status = tokens[
            "A"
            if state.status is BatchRefinementStatus.ACTIVE
            else "S"
            if state.status is BatchRefinementStatus.SUCCESS
            else "F"
        ]
        semantic = (
            state.stage,
            state.units,
            state.risk,
            status,
            kernel.risk_capacity,
            kernel.goal_stage,
        )
        return tuple(semantic[index] for index in state_order)

    return tuple(catalogue), encode


def _observe(occurrence: int, kernel: Any, catalogue, encode):
    queue = deque([kernel.initial_distribution()[0][1]])
    seen = set(queue)
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
                        tuple(row.rule for row in legal),
                        catalogue[action.rule],
                        encode(successor),
                        tuple(row.rule for row in legal_after),
                        None
                        if legal_after
                        else successor.status is BatchRefinementStatus.SUCCESS,
                    )
                )
                if (
                    successor.status is BatchRefinementStatus.ACTIVE
                    and successor not in seen
                ):
                    seen.add(successor)
                    queue.append(successor)
    return tuple(rows), labels, len(seen)


def _archive(occurrence, seed, catalogue, rows, labels, reachable, domain):
    payload = {
        "schema": "acfqp.joint_factor_residual_raw_observation.v54r1",
        "family_token": "OPAQUE_BALANCED_STOCHASTIC_BATCH_REFINEMENT",
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


def _relations(program):
    encoded = canonical_json_bytes(
        [row["expression"] for row in program["compiled_assignments"]]
    ).decode("utf-8")
    return {
        name: rows
        for name, rows in program["occurrence_bindings"][0]["relations"].items()
        if f'"{name}"' in encoded
    }


def _relation_fields(program):
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


def _candidate_cap(state, name, registered_cap):
    suffix = name.rsplit("_", 1)[-1]
    if suffix.isascii() and suffix.isdigit():
        column = int(suffix)
        if 0 <= column < len(state) and state[column] > 0:
            return min(registered_cap, state[column] - 1)
    return registered_cap


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
        _fail("V54r1 local residual recovery was not unique")
    return matches[0]


def _strict_choice(kernel, state, cache):
    choices = {}
    labels = 0

    @lru_cache(maxsize=None)
    def solve(current):
        nonlocal labels
        if current.status is BatchRefinementStatus.SUCCESS:
            return True
        if current.status is BatchRefinementStatus.FAILURE:
            return False
        for action in kernel.actions(current):
            key = (current, action.rule)
            if key not in cache:
                cache[key] = tuple(
                    row.next_state for row in kernel.step(current, action)
                )
                labels += 1
            if all(solve(successor) for successor in cache[key]):
                choices[current] = action.rule
                return True
        return False

    if not solve(state) or state not in choices:
        _fail("V54r1 direct planner found no robust continuation")
    return choices[state], solve.cache_info().currsize, labels


def _episode(seed, arm, actions, tapes, planning, peak, labels, layout_labels, local_labels, failures, success, domain):
    payload = {
        "schema": "acfqp.joint_factor_residual_receding_episode.v54r1",
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


def _ood_rows():
    catalogue = tuple(
        FlatRawActionV4(index, (bit, 1))
        for index, bit in enumerate((1, 2, 4))
    )
    tokens = {"A": 9_001, "F": 9_007, "S": 9_011}
    rows = []
    for mask in (0, 1, 2):
        for key, bit in enumerate((1, 2, 4)):
            successor = mask | bit
            status = "F" if successor & 4 else "S" if successor == 3 else "A"
            rows.append(
                FlatRawTransitionV4(
                    0,
                    len(rows),
                    (mask, tokens["A"], 3, 4, 1),
                    (0, 1, 2),
                    catalogue[key],
                    (successor, tokens[status], 3, 4, 1),
                    () if status != "A" else (0, 1, 2),
                    None if status == "A" else status == "S",
                )
            )
    return tuple(rows), catalogue


def build_joint_factor_residual_campaign_document_v54r1(
    config: Mapping[str, Any], preregistration_id: str, factor_library: Mapping[str, Any]
) -> dict[str, Any]:
    domains = config["domains"]
    if factor_library.get("factor_library_id") != config["v51_factor_library_id"]:
        _fail("V54r1 anonymous factor-library identity changed")
    rows_by_occurrence = {}
    catalogues = {}
    archives = []
    source_labels = 0
    for occurrence, seed in enumerate(config["source_seeds"]):
        kernel, _witness = generate_stochastic_balanced_batch_refinement(
            stage_count=config["source_stage_count"],
            unit_base=config["source_unit_base"],
            seed=seed,
        )
        catalogue, encode = _interface(seed, kernel, config["terminal_tokens"])
        rows, labels, reachable = _observe(occurrence, kernel, catalogue, encode)
        if labels > config["maximum_source_labels_per_occurrence"]:
            _fail("V54r1 source label cap exceeded")
        rows_by_occurrence[occurrence] = rows
        catalogues[occurrence] = catalogue
        archives.append(_archive(occurrence, seed, catalogue, rows, labels, reachable, domains["observation"]))
        source_labels += labels
    joint = synthesize_joint_factor_residual_world_model_v9(
        rows_by_occurrence,
        catalogues,
        factor_library,
        layout_domain=domains["layout"],
        program_domain=domains["program"],
        support_domain=domains["support"],
        factor_domain=domains["joint_model"],
        result_domain=domains["joint_model"],
        minimum_reusable_factor_count=config["minimum_reusable_factor_count"],
    )
    if not joint["transfer_admitted"] or joint["residual_schema_bound_count"] < 1:
        _fail("V54r1 joint classification did not meet its frozen boundary")
    program = joint["target_world_model"]["compiled_program"]
    reference_rows = rows_by_occurrence[0]
    reference_catalogue = catalogues[0]
    reference_layout = discover_generic_layout_v5(
        reference_rows, reference_catalogue, layout_domain=domains["layout"]
    )
    base_relations = _relations(program)
    relation_fields = _relation_fields(program)
    calibrations = []
    failures = []
    distinctions = []
    structural = []
    strict = []
    overlay: dict[str, dict[int, int]] = {}
    for episode_index, seed in enumerate(config["target_seeds"]):
        kernel, _witness = generate_stochastic_balanced_batch_refinement(
            stage_count=config["target_stage_count"],
            unit_base=config["target_unit_base"],
            seed=seed,
        )
        catalogue, encode = _interface(seed, kernel, config["terminal_tokens"])
        calibration_rows, layout_labels, reachable = _observe(0, kernel, catalogue, encode)
        if layout_labels > config["maximum_target_layout_labels"]:
            _fail(f"V54r1 target layout label cap exceeded at seed {seed}")
        try:
            layout = match_generic_layout_meta_prior_v5(
                reference_rows,
                reference_catalogue,
                reference_layout,
                calibration_rows,
                catalogue,
                layout_domain=domains["layout"],
            )
        except Exception as error:
            _fail(f"V54r1 target layout failed at seed {seed}: {type(error).__name__}: {error}")
        calibrations.append(
            {
                "seed": seed,
                "support_labels": layout_labels,
                "raw_transition_count": len(calibration_rows),
                "reachable_active_state_count": reachable,
                "layout": layout.to_document(),
                "policy": "WITNESS_BLIND_FULL_FRONTIER_THEN_UNIQUE_STRUCTURAL_MATCH",
                "generation_witness_accessed": False,
                "relation_outputs_consumed_for_target_binding": False,
            }
        )
        _aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
            calibration_rows, catalogue, layout, canonical_occurrence=0
        )
        initial = kernel.initial_distribution()[0][1]
        raw_initial = encode(initial)
        canonical_initial = tuple(raw_initial[index] for index in layout.state_canonical_to_raw)
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
        while state.status is BatchRefinementStatus.ACTIVE:
            raw_state = encode(state)
            canonical_state = tuple(raw_state[index] for index in layout.state_canonical_to_raw)
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
                    "schema": "acfqp.joint_factor_residual_failed_certificate.v54r1",
                    "seed": seed,
                    "episode_index": episode_index,
                    "decision_index": decision,
                    "program_id": program["program_id"],
                    "missing_relation_name": name,
                    "missing_relation_input": relation_input,
                    "ground_query_performed_before_failure": False,
                    "outcome": "FAILED_COMPILED_RELATION_SUPPORT_CERTIFICATE",
                }
                failure = {**failure_payload, "failed_certificate_id": content_id(domains["failed_certificate"], failure_payload)}
                failures.append(failure)
                episode_failures += 1
                field = relation_fields[name]
                aligned_action = next(row for row in aligned_catalogue if row.fields[field] == relation_input)
                rule = kernel.rules[aligned_action.key]
                probe = BatchRefinementState(rule.source_stage, 0, 0, 0, BatchRefinementStatus.ACTIVE)
                raw_probe = encode(probe)
                canonical_probe = tuple(raw_probe[index] for index in layout.state_canonical_to_raw)
                actual = {
                    tuple(encode(outcome.next_state)[index] for index in layout.state_canonical_to_raw)
                    for outcome in kernel.step(probe, BatchRefinementAction(aligned_action.key))
                }
                value = _recover(
                    program,
                    binding,
                    canonical_probe,
                    aligned_action,
                    actual,
                    name,
                    relation_input,
                    overlay,
                    _candidate_cap(canonical_probe, name, config["maximum_relation_output_candidate"]),
                )
                overlay.setdefault(name, {})[relation_input] = value
                distinction_payload = {
                    "schema": "acfqp.joint_factor_residual_local_distinction.v54r1",
                    "failed_certificate_id": failure["failed_certificate_id"],
                    "relation_name": name,
                    "relation_input": relation_input,
                    "relation_output": value,
                    "query_after_failed_certificate": True,
                    "ground_support_labels": 1,
                }
                distinctions.append({**distinction_payload, "local_distinction_id": content_id(domains["distinction"], distinction_payload)})
                local_labels += 1
            plan, evaluations, cache_size = plan_generic_atomic_program_v4(
                program, canonical_state, aligned_catalogue, binding, relation_overlay=overlay
            )
            key = plan[0]
            outcome, tape = select_seeded_batch_refinement_outcome_v1(
                kernel.step(state, BatchRefinementAction(key)),
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
        structural.append(_episode(seed, "JOINT_DISCOVERED_ABSTRACT_WORLD_MODEL", actions, tapes, planning, peak, layout_labels + local_labels, layout_labels, local_labels, episode_failures, state.status is BatchRefinementStatus.SUCCESS, domains["episode"]))

        strict_actions = []
        strict_tapes = []
        strict_planning = 0
        strict_peak = 0
        strict_labels = 0
        strict_state = initial
        strict_cache = {}
        strict_decision = 0
        while strict_state.status is BatchRefinementStatus.ACTIVE:
            key, compute, labels = _strict_choice(kernel, strict_state, strict_cache)
            outcome, tape = select_seeded_batch_refinement_outcome_v1(
                kernel.step(strict_state, BatchRefinementAction(key)),
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
        strict.append(_episode(seed, "STRICT_EXACT_CONTEXT", strict_actions, strict_tapes, strict_planning, strict_peak, strict_labels, 0, 0, 0, strict_state.status is BatchRefinementStatus.SUCCESS, domains["episode"]))
    if not all(row["success"] for row in structural + strict):
        _fail("V54r1 held-out planning did not succeed")
    if [row["action_keys"] for row in structural] != [row["action_keys"] for row in strict]:
        _fail("V54r1 abstract and direct plans changed")
    if not failures or len(failures) != len(distinctions):
        _fail("V54r1 certificate-first recovery was not observed")

    ood_rows, ood_catalogue = _ood_rows()
    ood_model = synthesize_joint_factor_residual_world_model_v9(
        {0: ood_rows},
        {0: ood_catalogue},
        factor_library,
        layout_domain=domains["layout"],
        program_domain=domains["program"],
        support_domain=domains["support"],
        factor_domain=domains["joint_model"],
        result_domain=domains["joint_model"],
        minimum_reusable_factor_count=config["minimum_reusable_factor_count"],
    )
    if ood_model["transfer_admitted"]:
        _fail("V54r1 OOD unexpectedly admitted transfer")
    ood_payload = {
        "schema": "acfqp.joint_factor_residual_ood_rejection.v54r1",
        "joint_model_id": ood_model["joint_model_id"],
        "factorable_reusable_count": ood_model["factorable_reusable_count"],
        "minimum_reusable_factor_count": config["minimum_reusable_factor_count"],
        "complete_ood_program_synthesized_from_raw_observations": True,
        "prior_transfer_attempted": False,
        "ood_outcome_execution_performed": False,
        "outcome": "STRICT_SIGNATURE_THRESHOLD_OOD_NO_TRANSFER",
    }
    ood = {**ood_payload, "ood_rejection_id": content_id(domains["ood"], ood_payload)}
    payload = {
        "schema": "acfqp.joint_factor_residual_campaign.v54r1",
        "preregistration_id": preregistration_id,
        "frozen_failed_v54_predecessor_id": config["v54_failure_id"],
        "frozen_v51_factor_library_id": factor_library["factor_library_id"],
        "v51_target_program_consumed": False,
        "v51_reused_factor_slot_inventory_consumed": False,
        "source_archives": archives,
        "joint_world_model": joint,
        "target_layout_calibrations": calibrations,
        "failed_certificates": failures,
        "local_distinctions": distinctions,
        "relation_overlay": {name: [[key, value] for key, value in sorted(rows.items())] for name, rows in sorted(overlay.items())},
        "structural_episodes": structural,
        "strict_episodes": strict,
        "ood_rejection": ood,
        "accounting": {
            "historical_factor_library_labels": config["factor_library_labels"],
            "fresh_source_support_labels": source_labels,
            "target_layout_support_labels": sum(row["target_layout_support_labels"] for row in structural),
            "local_ground_support_labels": sum(row["local_ground_support_labels"] for row in structural),
            "structural_execution_steps": sum(row["execution_steps"] for row in structural),
            "strict_execution_steps": sum(row["execution_steps"] for row in strict),
            "full_program_atomic_synthesis_compute_events": program["atomic_expression_evaluations"],
            "dependency_classification_count": len(joint["assignment_classifications"]),
            "structural_planning_compute_events": sum(row["planning_compute_events"] for row in structural),
            "strict_planning_compute_events": sum(row["planning_compute_events"] for row in strict),
            "certificate_compute_events": len(failures),
            "all_axes_separate": True,
        },
        "claim_boundary": {
            "joint_factorable_and_residual_discovery_observed": True,
            "fresh_balanced_stochastic_domain_observed": True,
            "certificate_failure_only_local_ground_distinctions_observed": True,
            "strict_incompatible_ood_no_transfer_observed": True,
            "factor_prior_sample_savings_reestimated_in_v54r1": False,
            "arbitrary_domain_transfer_claimed": False,
        },
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {**payload, "campaign_id": content_id(domains["campaign"], payload)}


__all__ = (
    "JointFactorResidualCampaignCoreV54R1Error",
    "build_joint_factor_residual_campaign_document_v54r1",
)
