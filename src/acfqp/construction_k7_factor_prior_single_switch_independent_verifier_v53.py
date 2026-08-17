"""Producer-free scientific replay of the frozen V53 single-switch campaign.

The verifier does not import the V53 campaign producer or campaign core.  It
reconstructs the V51 predecessor through its independent verifier, reruns all
1024 matched acquisitions, and independently replays the 16 registered
planning/certificate occurrences.  It verifies the scientific projection and
references the frozen campaign byte identity; it does not claim to regenerate
the producer's 33 MB presentation document byte for byte.
"""

from __future__ import annotations

from collections import deque
from concurrent.futures import ProcessPoolExecutor
import hashlib
import multiprocessing
import random
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_cross_schema_factor_independent_verifier_v51 as v51verify
from acfqp import construction_k7_factor_prior_single_switch_preregistration_v53 as pre
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
from acfqp.generic_cross_schema_factor_library_v7 import discover_factor_boundaries_v7
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
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


EXPECTED_CAMPAIGN_ID = "f99f19fb95af81fe25a8a3229bd0dbc35187e1e3cf9a9f97b824dbc31993d169"
EXPECTED_CAMPAIGN_BYTE_COUNT = 33_058_905
EXPECTED_CAMPAIGN_SHA256 = "6a435b190a2f5fefb4ede21b3483f90dfa199c93c555a6c6faf30aa3f5990234"
VERIFICATION_ID = "13c4e805fdf7457033ca99b9422aa374cef108528aa230514c16bdf6347c9372"
EXPECTED_CANONICAL_BYTE_COUNT = 1_892
EXPECTED_CANONICAL_SHA256 = "68f6d2dee145b4d0513223fc40df0b72240fd95e70014d261943ae934e6d14bc"
MAXIMUM_PROCESSES = 8


class ConstructionK7FactorPriorSingleSwitchIndependentVerifierV53Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FactorPriorSingleSwitchIndependentVerifierV53Error(message)


def _permutations(seed: int):
    rng = random.Random(seed ^ 0x53A17)
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
        token = pre.TERMINAL_TOKENS[
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


def _observe_one(
    kernel: Any,
    catalogue: tuple[FlatRawActionV4, ...],
    encode: Any,
    queue: deque[Any],
    seen: set[Any],
    pending: deque[Any],
    rows: list[FlatRawTransitionV4],
) -> None:
    while not pending:
        if not queue:
            _fail("independent acquisition exhausted before stopping")
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
                tuple(item.task for item in legal),
                catalogue[action.task],
                encode(successor),
                tuple(item.task for item in legal_after),
                None
                if legal_after
                else successor.status is MaintenanceCascadeStatus.SUCCESS,
            )
        )
        if successor.status is MaintenanceCascadeStatus.ACTIVE and successor not in seen:
            seen.add(successor)
            queue.append(successor)


def _selection_key(update: Mapping[str, Any]):
    if update["all_factor_slots_stopped"] is not True:
        return None
    return tuple(
        (row["target_column"], row["selected_candidate"]["candidate_id"])
        for row in update["selections"]
    )


_WORKER_COMMON: dict[str, Any] = {}


def _acquire(seed: int, enabled: bool):
    common = _WORKER_COMMON
    kernel, _witness = generate_stochastic_maintenance_cascade(
        zone_count=pre.TARGET_ZONE_COUNT,
        repair_base=pre.TARGET_REPAIR_BASE,
        seed=seed,
    )
    catalogue, encode = _interface(seed, kernel)
    initial = kernel.initial_distribution()[0][1]
    queue = deque([initial])
    seen = {initial}
    pending: deque[Any] = deque()
    rows: list[FlatRawTransitionV4] = []
    labels = 0
    layout = None
    layout_at = None
    last_mapping = None
    stable = 0
    update = None
    history = []
    while labels < pre.MAXIMUM_SYNTHESIS_LABELS_PER_ARM:
        _observe_one(kernel, catalogue, encode, queue, seen, pending, rows)
        labels += 1
        if layout is None:
            try:
                candidate = match_generic_layout_meta_prior_v5(
                    common["reference_rows"],
                    common["reference_catalogue"],
                    common["reference_layout"],
                    tuple(rows),
                    catalogue,
                    layout_domain=pre.FUTURE_DOMAINS["acquisition"],
                )
            except GenericLayoutFactorizedWorldModelV5Error:
                candidate = None
            if candidate is None:
                continue
            mapping = (
                candidate.state_canonical_to_raw,
                candidate.action_canonical_to_raw,
            )
            stable = stable + 1 if mapping == last_mapping else 1
            last_mapping = mapping
            if stable < pre.LAYOUT_CONFIRMATION_COUNT:
                continue
            layout = candidate
            layout_at = labels
        aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
            tuple(rows), catalogue, layout, canonical_occurrence=0
        )
        update = infer_factor_slots_v8(
            aligned_rows,
            aligned_catalogue,
            factor_slots=common["factor_slots"],
            prior_signature_sha256=common["prior_signatures"],
            factor_prior_enabled=enabled,
            prior_weight=pre.FACTOR_PRIOR_WEIGHT,
            posterior_numerator=pre.POSTERIOR_THRESHOLD_NUMERATOR,
            posterior_denominator=pre.POSTERIOR_THRESHOLD_DENOMINATOR,
        )
        selection = _selection_key(update)
        history.append(
            (
                labels,
                hashlib.sha256(
                    canonical_json_bytes([row.to_document() for row in rows])
                ).hexdigest(),
                tuple(row["survivor_count"] for row in update["selections"]),
            )
        )
        if (
            selection is not None
            and labels - layout_at >= pre.MINIMUM_POST_LAYOUT_CONFIRMATION_LABELS
        ):
            break
    else:
        _fail("independent synthesis exceeded the frozen label cap")
    if update is None or layout is None:
        _fail("independent synthesis did not freeze a model")
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        tuple(rows), catalogue, layout, canonical_occurrence=0
    )
    program = compile_factor_slot_program_v8(
        common["scaffold"],
        update,
        program_domain=pre.FUTURE_DOMAINS["program"],
    )
    return {
        "labels": labels,
        "history": tuple(history),
        "assignments": program["compiled_assignments"],
        "program": program,
        "layout": layout.to_document(),
        "aligned_catalogue": aligned_catalogue,
    }


def _acquisition_worker(task: tuple[int, int]):
    index, seed = task
    on = _acquire(seed, True)
    off = _acquire(seed, False)
    shared = min(len(on["history"]), len(off["history"]))
    if on["history"][:shared] != off["history"][:shared]:
        _fail("independent single-switch common acquisition prefix changed")
    if on["assignments"] != off["assignments"]:
        _fail("independent single-switch programs differ")
    result = {
        "index": index,
        "seed": seed,
        "on_labels": on["labels"],
        "off_labels": off["labels"],
        "assignment_sha256": hashlib.sha256(
            canonical_json_bytes(on["assignments"])
        ).hexdigest(),
        "common_prefix_exact": True,
    }
    if index < pre.PLANNING_VALIDATION_SEED_COUNT:
        result["planning"] = {
            "on_program": on["program"],
            "off_program": off["program"],
            "layout": on["layout"],
            "aligned_catalogue": on["aligned_catalogue"],
        }
    return result


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
        for child in expression:
            visit(child)

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
) -> int:
    matches = []
    for candidate in range(pre.MAXIMUM_RELATION_OUTPUT_CANDIDATE + 1):
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
        _fail("independent local relation recovery was not unique")
    return matches[0]


def _plan_replay(
    seed: int,
    episode_index: int,
    program: Mapping[str, Any],
    layout: Mapping[str, Any],
    aligned_catalogue: tuple[FlatRawActionV4, ...],
    overlay: dict[str, dict[int, int]],
):
    kernel, _witness = generate_stochastic_maintenance_cascade(
        zone_count=pre.TARGET_ZONE_COUNT,
        repair_base=pre.TARGET_REPAIR_BASE,
        seed=seed,
    )
    _catalogue, encode = _interface(seed, kernel)
    state_map = tuple(layout["state_canonical_to_raw"])
    initial = kernel.initial_distribution()[0][1]
    raw_initial = encode(initial)
    binding = target_binding_from_initial_vector_v4(
        program,
        tuple(raw_initial[index] for index in state_map),
        base_relations=_relations(program),
        terminal_tokens=pre.TERMINAL_TOKENS,
    )
    fields = _relation_fields(program)
    state = initial
    actions = []
    tapes = []
    planning = 0
    peak = 0
    failures = 0
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
            failures += 1
            action = next(
                row
                for row in aligned_catalogue
                if row.fields[fields[name]] == relation_input
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
            )
            overlay.setdefault(name, {})[relation_input] = value
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
    return {
        "actions": actions,
        "tapes": tapes,
        "execution_steps": len(actions),
        "planning_compute_events": planning,
        "peak_planning_cache_entries": peak,
        "failed_certificate_count": failures,
        "success": state.status is MaintenanceCascadeStatus.SUCCESS,
    }


def _verify_sources() -> None:
    expected = pre.freeze_factor_prior_single_switch_preregistration_v53().to_document()[
        "source_closure"
    ]["source_facts"]
    actual = []
    for relative in pre.BOUND_SOURCE_PATHS:
        raw = (pre.SOURCE_ROOT / relative).read_bytes()
        actual.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    if actual != expected:
        _fail("independent V53 source closure changed")


def _replay_projection() -> dict[str, Any]:
    global _WORKER_COMMON
    _verify_sources()
    predecessor = v51verify._reconstruct_campaign_document()
    predecessor_raw = canonical_json_bytes(predecessor)
    if (
        predecessor["campaign_id"] != pre.V51_CAMPAIGN_ID
        or len(predecessor_raw) != v51verify.EXPECTED_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(predecessor_raw).hexdigest()
        != v51verify.EXPECTED_CAMPAIGN_SHA256
    ):
        _fail("independent V51 predecessor identity changed")
    model = predecessor["higher_order_partial_stochastic_world_model"][
        "factor_composed_model"
    ]
    scaffold = model["compiled_program"]
    reference_rows, reference_catalogue = _parse_reference(predecessor)
    reference_layout = discover_generic_layout_v5(
        reference_rows,
        reference_catalogue,
        layout_domain=pre.FUTURE_DOMAINS["acquisition"],
    )
    boundary = discover_factor_boundaries_v7(
        scaffold, factor_domain=pre.FUTURE_DOMAINS["program"]
    )
    reused = {row["target_column"] for row in scaffold["reused_factor_subprograms"]}
    factor_slots = {
        row["target_column"]: row["result_type"]
        for row in boundary["factors"]
        if row["transferable_without_schema_specific_binding"]
        and row["target_column"] in reused
    }
    prior_signatures = frozenset(
        row["signature_sha256"]
        for row in model["factor_library"]["cross_schema_subprograms"]
    )
    _WORKER_COMMON = {
        "scaffold": scaffold,
        "reference_rows": reference_rows,
        "reference_catalogue": reference_catalogue,
        "reference_layout": reference_layout,
        "factor_slots": factor_slots,
        "prior_signatures": prior_signatures,
    }
    tasks = tuple(enumerate(pre.TARGET_SEEDS))
    context = multiprocessing.get_context("fork")
    with ProcessPoolExecutor(
        max_workers=MAXIMUM_PROCESSES,
        mp_context=context,
    ) as executor:
        rows = list(executor.map(_acquisition_worker, tasks, chunksize=4))
    if [row["index"] for row in rows] != list(range(len(pre.TARGET_SEEDS))):
        _fail("independent acquisition order changed")
    on_target = sum(row["on_labels"] for row in rows)
    off_target = sum(row["off_labels"] for row in rows)
    on_running = pre.SHARED_RESIDUAL_SCAFFOLD_LABELS + pre.FACTOR_LIBRARY_LABELS
    off_running = pre.SHARED_RESIDUAL_SCAFFOLD_LABELS
    break_even = None
    for index, row in enumerate(rows, start=1):
        on_running += row["on_labels"]
        off_running += row["off_labels"]
        if break_even is None and off_running - on_running > 0:
            break_even = index
    overlays = {"on": {}, "off": {}}
    planning_totals = {
        "on_steps": 0,
        "off_steps": 0,
        "on_compute": 0,
        "off_compute": 0,
        "on_certificates": 0,
        "off_certificates": 0,
        "matched_action_occurrences": 0,
    }
    for row in rows[: pre.PLANNING_VALIDATION_SEED_COUNT]:
        planning = row["planning"]
        on = _plan_replay(
            row["seed"],
            row["index"],
            planning["on_program"],
            planning["layout"],
            planning["aligned_catalogue"],
            overlays["on"],
        )
        off = _plan_replay(
            row["seed"],
            row["index"],
            planning["off_program"],
            planning["layout"],
            planning["aligned_catalogue"],
            overlays["off"],
        )
        if not on["success"] or not off["success"]:
            _fail("independent planning replay failed")
        if on["actions"] != off["actions"] or on["tapes"] != off["tapes"]:
            _fail("independent matched planning replay changed")
        planning_totals["on_steps"] += on["execution_steps"]
        planning_totals["off_steps"] += off["execution_steps"]
        planning_totals["on_compute"] += on["planning_compute_events"]
        planning_totals["off_compute"] += off["planning_compute_events"]
        planning_totals["on_certificates"] += on["failed_certificate_count"]
        planning_totals["off_certificates"] += off["failed_certificate_count"]
        planning_totals["matched_action_occurrences"] += 1
    incremental = off_target - on_target
    lifetime = incremental - pre.FACTOR_LIBRARY_LABELS
    if (
        on_target != 4_604
        or off_target != 5_120
        or incremental != 516
        or lifetime != 146
        or break_even != 720
    ):
        _fail("independent V53 sample-tax projection changed")
    if (
        planning_totals["on_steps"] != 114
        or planning_totals["off_steps"] != 114
        or planning_totals["on_certificates"] != 8
        or planning_totals["off_certificates"] != 8
    ):
        _fail("independent V53 planning/certificate projection changed")
    return {
        "acquisition_occurrence_count": len(rows),
        "planning_validation_occurrence_count": planning_totals[
            "matched_action_occurrences"
        ],
        "factor_slot_count": len(factor_slots),
        "factor_signature_count": len(prior_signatures),
        "factor_prior_on_target_labels": on_target,
        "factor_prior_off_target_labels": off_target,
        "incremental_target_label_reduction": incremental,
        "historical_factor_library_labels": pre.FACTOR_LIBRARY_LABELS,
        "lifetime_label_reduction": lifetime,
        "diagnostic_break_even_occurrence_count": break_even,
        **planning_totals,
        "all_common_prefixes_exact": all(row["common_prefix_exact"] for row in rows),
        "distinct_compiled_assignment_sha256_count": len(
            {row["assignment_sha256"] for row in rows}
        ),
    }


def freeze_factor_prior_single_switch_verification_v53() -> bytes:
    facts = _replay_projection()
    payload = {
        "schema": "acfqp.factor_prior_single_switch_independent_verification.v53",
        "campaign_id": EXPECTED_CAMPAIGN_ID,
        "campaign_byte_count": EXPECTED_CAMPAIGN_BYTE_COUNT,
        "campaign_sha256": EXPECTED_CAMPAIGN_SHA256,
        "preregistration_id": pre.PREREGISTRATION_ID,
        **facts,
        "producer_or_campaign_core_module_imported": False,
        "predecessor_reconstructed_by_independent_v51_verifier": True,
        "all_registered_acquisition_occurrences_replayed": True,
        "same_synthesizer_query_likelihood_threshold_and_confirmation_rechecked": True,
        "only_factor_signature_prior_multiplier_switched": True,
        "compiled_assignments_and_matched_plans_rechecked": True,
        "certificate_failure_before_local_ground_recovery_rechecked": True,
        "scientific_projection_independently_reconstructed": True,
        "full_campaign_presentation_bytes_reconstructed": False,
        "frozen_campaign_byte_identity_referenced": True,
        "maximum_parallel_replay_processes": MAXIMUM_PROCESSES,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "status": "VERIFIED_NONOFFICIAL_V53_FACTOR_PRIOR_SINGLE_SWITCH_SCIENTIFIC_PROJECTION",
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
        _fail("frozen V53 independent verification changed")
    return raw


def verify_factor_prior_single_switch_verification_bytes_v53(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail("V53 verification requires bytes")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V53 verification canonical bytes changed")
    expected = freeze_factor_prior_single_switch_verification_v53()
    if raw != expected:
        _fail("V53 verification bytes do not match independent replay")
    return document


__all__ = (
    "EXPECTED_CAMPAIGN_BYTE_COUNT",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_CAMPAIGN_SHA256",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "MAXIMUM_PROCESSES",
    "VERIFICATION_ID",
    "freeze_factor_prior_single_switch_verification_v53",
    "verify_factor_prior_single_switch_verification_bytes_v53",
)
