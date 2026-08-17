"""Producer-free reconstruction of the frozen V52 acquisition ablation."""

from __future__ import annotations

from collections import deque
from functools import lru_cache
import hashlib
import random
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_cross_schema_factor_independent_verifier_v51 as v51verify
from acfqp import construction_k7_factor_prior_ablation_preregistration_v52 as pre
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
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


EXPECTED_CAMPAIGN_ID = "8952b649ce5fb3fb9a5ce3de6e324d52ac42cad334c1a257e88bd2aca18f1898"
EXPECTED_CAMPAIGN_BYTE_COUNT = 88_222
EXPECTED_CAMPAIGN_SHA256 = "fb8e2d80d2acabff1005caf160b67af8f309a087a4262477f253b5ce26e5dfb9"
VERIFICATION_ID = "c64fe32237c35de4a3661db1e8bec724e878d81b19b3c6366d0d04683a9f03b2"
EXPECTED_CANONICAL_BYTE_COUNT = 1_757
EXPECTED_CANONICAL_SHA256 = "66aaec71f4c61b9084c3dcb2db78bbfce270d095dbdecbbf692bc1f11379e811"


class ConstructionK7FactorPriorAblationIndependentVerifierV52Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FactorPriorAblationIndependentVerifierV52Error(message)


def _permutations(seed: int):
    rng = random.Random(seed ^ 0x52A17)
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


def _calibrate(kernel, catalogue, encode, reference_rows, reference_catalogue, reference_layout):
    initial = kernel.initial_distribution()[0][1]
    queue = deque([initial])
    seen = {initial}
    rows = []
    labels = 0
    last_mapping = None
    stable_count = 0
    while queue and labels < pre.MAXIMUM_PRIOR_LAYOUT_LABELS:
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
                    layout_domain=pre.FUTURE_DOMAINS["acquisition"],
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
            if labels >= pre.MAXIMUM_PRIOR_LAYOUT_LABELS:
                break
    _fail("independent V52 layout calibration exceeded cap")


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
        _fail("independent V52 relation recovery was not unique")
    return matches[0]


def _acquire_exact(kernel, encode):
    initial = kernel.initial_distribution()[0][1]
    queue = deque([initial])
    seen = {initial}
    cache = {}
    rows = []
    labels = 0
    while queue:
        state = queue.popleft()
        for action in kernel.actions(state):
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
    if labels > pre.MAXIMUM_NO_PRIOR_LABELS_PER_OCCURRENCE:
        _fail("independent V52 no-prior acquisition exceeded cap")
    return cache, labels, len(seen), hashlib.sha256(canonical_json_bytes(rows)).hexdigest()


def _no_prior_choice(kernel, state, cache):
    choices = {}
    compute = 0

    @lru_cache(maxsize=None)
    def solve(current):
        nonlocal compute
        compute += 1
        if current.status is MaintenanceCascadeStatus.SUCCESS:
            return True
        if current.status is MaintenanceCascadeStatus.FAILURE:
            return False
        for action in kernel.actions(current):
            compute += 1
            if all(solve(row) for row in cache[(current, action.task)]):
                choices[current] = action.task
                return True
        return False

    if not solve(state) or state not in choices:
        _fail("independent V52 no-prior planner found no robust continuation")
    return choices[state], compute, solve.cache_info().currsize


def _episode(seed, arm, actions, tapes, planning, peak, labels, layout_labels, local_labels, failures, success):
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
    return {**payload, "episode_id": content_id(pre.FUTURE_DOMAINS["episode"], payload)}


def verify_factor_prior_ablation_campaign_bytes_v52(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail("V52 independent verifier requires bytes")
    if (
        len(raw) != EXPECTED_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CAMPAIGN_SHA256
    ):
        _fail("V52 campaign byte identity changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V52 campaign canonical encoding changed")
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    if (
        document.get("campaign_id") != EXPECTED_CAMPAIGN_ID
        or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != EXPECTED_CAMPAIGN_ID
        or document.get("preregistration_id") != pre.PREREGISTRATION_ID
    ):
        _fail("V52 campaign identity join changed")
    prereg = pre.verify_factor_prior_ablation_preregistration_v52(
        pre.freeze_factor_prior_ablation_preregistration_v52()
    ).to_document()
    if prereg["fresh_v52_registered_outcome_execution_performed"] is not False:
        _fail("V52 preregistration was not outcome-free")

    predecessor = v51verify._reconstruct_campaign_document()
    if (
        predecessor["campaign_id"] != pre.V51_CAMPAIGN_ID
        or canonical_json_bytes(predecessor).__len__() != v51verify.EXPECTED_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(canonical_json_bytes(predecessor)).hexdigest()
        != v51verify.EXPECTED_CAMPAIGN_SHA256
    ):
        _fail("V52 frozen predecessor did not independently reconstruct")
    model = predecessor["higher_order_partial_stochastic_world_model"][
        "factor_composed_model"
    ]
    program = model["compiled_program"]
    if (
        model["factor_library"]["factor_library_id"] != pre.V51_FACTOR_LIBRARY_ID
        or program["program_id"] != pre.V51_FACTOR_COMPOSED_PROGRAM_ID
        or model["reused_factor_count"] != pre.MINIMUM_REUSED_FACTOR_COUNT
    ):
        _fail("V52 frozen factor prior identity changed")
    reference_rows, reference_catalogue = _parse_reference(predecessor)
    reference_layout = discover_generic_layout_v5(
        reference_rows,
        reference_catalogue,
        layout_domain=pre.FUTURE_DOMAINS["acquisition"],
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

    for episode_index, seed in enumerate(pre.TARGET_SEEDS):
        kernel, _ = generate_stochastic_maintenance_cascade(
            zone_count=pre.TARGET_ZONE_COUNT,
            repair_base=pre.TARGET_REPAIR_BASE,
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
        prior_labels = layout_labels + local_labels
        acquisition_payload = {
            "schema": "acfqp.factor_prior_acquisition.v52",
            "seed": seed,
            "arm": "FACTOR_COMPOSED_WORLD_MODEL_PRIOR",
            "layout_support_labels": layout_labels,
            "local_post_certificate_support_labels": local_labels,
            "total_ground_support_labels": prior_labels,
            "raw_calibration_transition_count": len(calibration_rows),
            "layout": layout.to_document(),
            "factor_library_id": pre.V51_FACTOR_LIBRARY_ID,
            "factor_composed_program_id": pre.V51_FACTOR_COMPOSED_PROGRAM_ID,
            "generation_witness_accessed": False,
            "ground_query_before_failed_certificate": False,
        }
        prior_acquisitions.append(
            {
                **acquisition_payload,
                "acquisition_id": content_id(
                    pre.FUTURE_DOMAINS["acquisition"], acquisition_payload
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
                prior_labels,
                layout_labels,
                local_labels,
                episode_failures,
                state.status is MaintenanceCascadeStatus.SUCCESS,
            )
        )

        exact_cache, exact_labels, reachable, exact_digest = _acquire_exact(kernel, encode)
        exact_payload = {
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
                **exact_payload,
                "acquisition_id": content_id(
                    pre.FUTURE_DOMAINS["acquisition"], exact_payload
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
            key, compute, cache_size = _no_prior_choice(kernel, exact_state, exact_cache)
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
            )
        )

    if prior_acquisitions != document["factor_prior_acquisitions"]:
        _fail("V52 factor-prior acquisitions did not independently reconstruct")
    if no_prior_acquisitions != document["no_prior_acquisitions"]:
        _fail("V52 no-prior acquisitions did not independently reconstruct")
    if failures != document["failed_certificates"] or distinctions != document["local_distinctions"]:
        _fail("V52 certificate-first recovery did not independently reconstruct")
    if prior_episodes != document["factor_prior_episodes"]:
        _fail("V52 factor-prior episodes did not independently reconstruct")
    if no_prior_episodes != document["no_prior_episodes"]:
        _fail("V52 no-prior episodes did not independently reconstruct")
    expected_overlay = {
        name: [[key, value] for key, value in sorted(rows.items())]
        for name, rows in sorted(overlay.items())
    }
    if expected_overlay != document["relation_overlay"]:
        _fail("V52 immutable overlay did not independently reconstruct")

    prior_target = sum(row["total_ground_support_labels"] for row in prior_acquisitions)
    no_prior_target = sum(row["total_ground_support_labels"] for row in no_prior_acquisitions)
    prior_running = pre.HISTORICAL_FACTOR_PRIOR_LABELS
    no_prior_running = 0
    prefixes = []
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
    sample_payload = {
        "schema": "acfqp.factor_prior_acquisition_sample_tax.v52",
        "historical_factor_prior_labels": pre.HISTORICAL_FACTOR_PRIOR_LABELS,
        "factor_prior_target_labels": prior_target,
        "no_prior_target_labels": no_prior_target,
        "factor_prior_cumulative_labels": pre.HISTORICAL_FACTOR_PRIOR_LABELS
        + prior_target,
        "no_prior_cumulative_labels": no_prior_target,
        "cumulative_label_reduction": no_prior_target
        - pre.HISTORICAL_FACTOR_PRIOR_LABELS
        - prior_target,
        "registered_break_even_occurrence_count": break_even,
        "prefix_curve": prefixes,
        "sample_labels_separate_from_execution_and_compute": True,
        "individual_factor_only_causal_effect_claimed": False,
        "factor_composed_prior_pipeline_causal_contrast_observed": True,
        "official_break_even_claimed": False,
    }
    expected_sample = {
        **sample_payload,
        "sample_tax_id": content_id(pre.FUTURE_DOMAINS["sample_tax"], sample_payload),
    }
    if expected_sample != document["sample_tax"]:
        _fail("V52 sample-tax curve did not independently reconstruct")
    accounting = {
        "historical_factor_prior_labels": pre.HISTORICAL_FACTOR_PRIOR_LABELS,
        "factor_prior_target_layout_labels": sum(
            row["layout_support_labels"] for row in prior_acquisitions
        ),
        "factor_prior_local_ground_labels": sum(
            row["local_post_certificate_support_labels"] for row in prior_acquisitions
        ),
        "no_prior_exact_ground_labels": no_prior_target,
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
    }
    if accounting != document["accounting"]:
        _fail("V52 separated accounting did not independently reconstruct")
    if not (
        document["frozen_v51_campaign_id"] == pre.V51_CAMPAIGN_ID
        and document["frozen_v51_factor_library_id"] == pre.V51_FACTOR_LIBRARY_ID
        and document["frozen_v51_factor_composed_program_id"]
        == pre.V51_FACTOR_COMPOSED_PROGRAM_ID
        and document["frozen_v51_reused_factor_count"] == 5
        and document["claim_boundary"]
        == {
            "matched_factor_composed_prior_vs_no_prior_acquisition_observed": True,
            "historical_prior_sample_tax_fully_included": True,
            "cross_occurrence_amortized_sample_reduction_observed": True,
            "individual_factor_only_causal_effect_claimed": False,
            "unbounded_domain_or_schema_transfer_claimed": False,
            "fallback_compute_reclassified_as_sample_labels": False,
        }
        and document["official_execution_allowed"] is False
        and document["official_scalar_cost"] is None
        and document["official_N_break_even"] is None
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    ):
        _fail("V52 claim boundary changed")
    return {
        "predecessor_reused_factor_count": 5,
        "matched_occurrence_count": len(pre.TARGET_SEEDS),
        "factor_prior_target_labels": prior_target,
        "no_prior_target_labels": no_prior_target,
        "factor_prior_cumulative_labels": expected_sample[
            "factor_prior_cumulative_labels"
        ],
        "no_prior_cumulative_labels": no_prior_target,
        "cumulative_label_reduction": expected_sample["cumulative_label_reduction"],
        "registered_break_even_occurrence_count": break_even,
        "certificate_failure_count": len(failures),
        "local_distinction_count": len(distinctions),
        "factor_prior_execution_steps": accounting["factor_prior_execution_steps"],
        "no_prior_execution_steps": accounting["no_prior_execution_steps"],
    }


def freeze_factor_prior_ablation_verification_v52(campaign_bytes: bytes) -> bytes:
    facts = verify_factor_prior_ablation_campaign_bytes_v52(campaign_bytes)
    payload = {
        "schema": "acfqp.factor_prior_acquisition_ablation_independent_verification.v52",
        "campaign_id": EXPECTED_CAMPAIGN_ID,
        "campaign_byte_count": EXPECTED_CAMPAIGN_BYTE_COUNT,
        "campaign_sha256": EXPECTED_CAMPAIGN_SHA256,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "frozen_v51_campaign_id": pre.V51_CAMPAIGN_ID,
        "frozen_v51_verification_id": pre.V51_VERIFICATION_ID,
        **facts,
        "v51_prior_reconstructed_without_v51_producer_or_core": True,
        "ground_distinct_maintenance_occurrences_regenerated": True,
        "factor_prior_calibration_and_certificate_recovery_reconstructed": True,
        "strict_no_prior_exact_acquisition_reconstructed": True,
        "matched_plans_and_outcome_tapes_replayed": True,
        "historical_and_target_sample_tax_curve_reconstructed": True,
        "sample_execution_planning_and_certificate_axes_reconstructed": True,
        "v52_producer_or_campaign_core_module_imported": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "status": "VERIFIED_DURABLE_NONOFFICIAL_V52_FACTOR_PRIOR_SAMPLE_TAX_ABLATION",
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
        _fail("frozen V52 verification changed")
    return raw


__all__ = (
    "EXPECTED_CAMPAIGN_BYTE_COUNT",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_CAMPAIGN_SHA256",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "VERIFICATION_ID",
    "freeze_factor_prior_ablation_verification_v52",
    "verify_factor_prior_ablation_campaign_bytes_v52",
)
