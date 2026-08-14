"""Execute the preregistered V42 reusable-model campaign.

The producer learns one generic rewrite/capacity program from four offline
source trajectories.  It then runs the same six held-out LMB instances in two
arms.  The structural arm certifies by a shared primitive support key; the
strict control certifies only exact state-action contexts.  Planning is an
exact deterministic search in the proposed model and never calls
``LMBKernel.step``.  An exact target row is requested only after a missing-
support certificate has been frozen.  The same call is reused as the executed
environment transition, so it is not secretly duplicated.

The result is a bounded second-domain construction, not a broad efficiency or
official economics claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_lmb_reusable_world_model_preregistration_v42 as pre
from acfqp.domains.matching_buffer import (
    LMBAction,
    LMBKernel,
    LMBState,
    LMBStatus,
    generate_solvable_lmb,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = "construction_k7_lmb_reusable_world_model_campaign_v42"
EXPECTED_CAMPAIGN_ID = (
    "c8adada792b7dacfce816bf1916457329643b61e8915f285472708c6c6bd359b"
)
EXPECTED_CANONICAL_BYTE_COUNT = 405_486
EXPECTED_CANONICAL_SHA256 = (
    "4f7cafbb0d1dff989ff6f9e824981e908f5a234ffe95a1f1ea162d3ede293161"
)

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_lmb_reusable_world_model_preregistration_v42.py",
    "src/acfqp/domains/matching_buffer.py",
)


class ConstructionK7LMBReusableWorldModelCampaignV42Error(ValueError):
    """The proposal, model-only plan, certificate, or target replay changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LMBReusableWorldModelCampaignV42Error(message)


def _state_document(state: LMBState) -> dict[str, Any]:
    return {
        "removed_mask": state.removed_mask,
        "buffer_counts": list(state.buffer),
        "status": state.status.value,
    }


def _action_document(action: LMBAction) -> dict[str, int]:
    return {"tile": action.tile}


def _predict_transition(kernel: LMBKernel, state: LMBState, action: LMBAction) -> LMBState:
    """The proposed generic rewrite/capacity law; no kernel transition call."""

    if action not in kernel.actions(state):
        _fail("abstract model received an ineligible operation")
    removed_mask = state.removed_mask | (1 << action.tile)
    operation_class = kernel.tile_types[action.tile]
    buffer_counts = list(state.buffer)
    buffer_counts[operation_class] += 1
    if buffer_counts[operation_class] == 3:
        buffer_counts[operation_class] = 0
    resource_load = sum(buffer_counts)
    board_empty = removed_mask == (1 << kernel.tile_count) - 1
    status = (
        LMBStatus.FAILURE
        if resource_load > kernel.capacity
        else LMBStatus.SUCCESS
        if board_empty
        else LMBStatus.ACTIVE
    )
    return LMBState(removed_mask, tuple(buffer_counts), status)


def _candidate_transition(
    kernel: LMBKernel,
    state: LMBState,
    action: LMBAction,
    *,
    rewrite_trigger_count: int,
    capacity_failure_offset: int,
) -> LMBState | None:
    """Evaluate one finite-grammar hypothesis without a ground transition."""

    removed_mask = state.removed_mask | (1 << action.tile)
    operation_class = kernel.tile_types[action.tile]
    counts = list(state.buffer)
    counts[operation_class] = (
        0
        if counts[operation_class] == rewrite_trigger_count
        else counts[operation_class] + 1
    )
    if counts[operation_class] >= 3:
        return None
    load = sum(counts)
    board_empty = removed_mask == (1 << kernel.tile_count) - 1
    status = (
        LMBStatus.FAILURE
        if load > kernel.capacity + capacity_failure_offset
        else LMBStatus.SUCCESS
        if board_empty
        else LMBStatus.ACTIVE
    )
    return LMBState(removed_mask, tuple(counts), status)


def _support_key(kernel: LMBKernel, state: LMBState, action: LMBAction) -> tuple[int, int, bool]:
    return (
        state.buffer[kernel.tile_types[action.tile]],
        sum(state.buffer),
        sum(state.buffer) == kernel.capacity,
    )


def _exact_context_key(state: LMBState, action: LMBAction) -> str:
    return content_id(
        pre.FUTURE_DOMAINS["local_ground_distinction"],
        {
            "role": "STRICT_NO_PRIOR_EXACT_CONTEXT_KEY",
            "state": _state_document(state),
            "action": _action_document(action),
        },
    )


def _source_binding() -> dict[str, Any]:
    facts = []
    for relative_path in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative_path).read_bytes()
        facts.append(
            {
                "relative_path": relative_path,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return {
        "schema": "acfqp.lmb_reusable_world_model_source_binding.v42",
        "schema_version": SCHEMA_VERSION,
        "lmb_reusable_world_model_preregistration_id": pre.PREREGISTRATION_ID,
        "v41_campaign_id": pre.V41_CAMPAIGN_ID,
        "v41_verification_id": pre.V41_VERIFICATION_ID,
        "bound_source_facts": facts,
        "producer_full_source_closure_claimed": False,
        "independent_verifier_required": True,
    }


def _source_proposal() -> tuple[dict[str, Any], set[tuple[int, int, bool]]]:
    rows: list[dict[str, Any]] = []
    support_keys: set[tuple[int, int, bool]] = set()
    alternate_pool: list[tuple[int, int, LMBKernel, LMBState, LMBAction]] = []
    for seed in pre.SOURCE_OBSERVATION_SEEDS:
        kernel, source_witness = generate_solvable_lmb(
            tile_count=pre.TILE_COUNT,
            type_count=pre.TYPE_COUNT,
            capacity=pre.BUFFER_CAPACITY,
            max_layers=pre.MAX_LAYERS,
            seed=seed,
        )
        state = kernel.initial_distribution()[0][1]
        for decision_index, tile in enumerate(source_witness.target_sequence):
            action = LMBAction(tile)
            alternate_pool.extend(
                (seed, decision_index, kernel, state, candidate)
                for candidate in kernel.actions(state)
                if candidate != action
            )
            predicted = _predict_transition(kernel, state, action)
            outcome = kernel.step(state, action)[0]
            if outcome.next_state != predicted:
                _fail("generic primitive program disagrees with a source observation")
            key = _support_key(kernel, state, action)
            support_keys.add(key)
            rows.append(
                {
                    "source_seed": seed,
                    "decision_index": decision_index,
                    "observation_phase": "WITNESS_TRAJECTORY",
                    "state": _state_document(state),
                    "action": _action_document(action),
                    "selected_class_count": key[0],
                    "resource_load": key[1],
                    "at_capacity": key[2],
                    "observed_successor": _state_document(outcome.next_state),
                    "observed_failure": outcome.failure,
                    "observed_terminal": outcome.terminal,
                }
            )
            state = outcome.next_state
        if state.status is not LMBStatus.SUCCESS:
            _fail("source observation trajectory did not close successfully")

    candidates = tuple(
        (rewrite_trigger_count, capacity_failure_offset)
        for rewrite_trigger_count in (0, 1, 2)
        for capacity_failure_offset in (-1, 0, 1)
    )

    def consistent(
        candidate: tuple[int, int], observations: list[dict[str, Any]]
    ) -> bool:
        for observation in observations:
            kernel, _witness = generate_solvable_lmb(
                tile_count=pre.TILE_COUNT,
                type_count=pre.TYPE_COUNT,
                capacity=pre.BUFFER_CAPACITY,
                max_layers=pre.MAX_LAYERS,
                seed=observation["source_seed"],
            )
            state_record = observation["state"]
            state = LMBState(
                state_record["removed_mask"],
                tuple(state_record["buffer_counts"]),
                LMBStatus(state_record["status"]),
            )
            predicted = _candidate_transition(
                kernel,
                state,
                LMBAction(observation["action"]["tile"]),
                rewrite_trigger_count=candidate[0],
                capacity_failure_offset=candidate[1],
            )
            return_document = None if predicted is None else _state_document(predicted)
            if return_document != observation["observed_successor"]:
                return False
        return True

    initial_versions = list(candidates)
    surviving = [candidate for candidate in candidates if consistent(candidate, rows)]
    after_witness_versions = list(surviving)
    adaptive_trace: list[dict[str, Any]] = []
    while len(surviving) > 1:
        best: tuple[
            tuple[int, int, int, int, int],
            tuple[int, int, LMBKernel, LMBState, LMBAction],
        ] | None = None
        for candidate_row in alternate_pool:
            seed, decision_index, kernel, state, action = candidate_row
            groups: dict[str, int] = {}
            for hypothesis in surviving:
                predicted = _candidate_transition(
                    kernel,
                    state,
                    action,
                    rewrite_trigger_count=hypothesis[0],
                    capacity_failure_offset=hypothesis[1],
                )
                key = repr(None if predicted is None else _state_document(predicted))
                groups[key] = groups.get(key, 0) + 1
            if len(groups) < 2:
                continue
            score = (
                len(groups),
                -max(groups.values()),
                -seed,
                -decision_index,
                -action.tile,
            )
            if best is None or score > best[0]:
                best = (score, candidate_row)
        if best is None:
            _fail("source observations do not identify one primitive program")
        seed, decision_index, kernel, state, action = best[1]
        outcome = kernel.step(state, action)[0]
        key = _support_key(kernel, state, action)
        support_keys.add(key)
        observation = {
            "source_seed": seed,
            "decision_index": decision_index,
            "observation_phase": "ADAPTIVE_CANDIDATE_DISAGREEMENT",
            "state": _state_document(state),
            "action": _action_document(action),
            "selected_class_count": key[0],
            "resource_load": key[1],
            "at_capacity": key[2],
            "observed_successor": _state_document(outcome.next_state),
            "observed_failure": outcome.failure,
            "observed_terminal": outcome.terminal,
        }
        rows.append(observation)
        surviving = [candidate for candidate in surviving if consistent(candidate, [observation])]
        adaptive_trace.append(
            {
                "query_ordinal": len(adaptive_trace),
                "source_seed": seed,
                "decision_index": decision_index,
                "action": _action_document(action),
                "surviving_candidate_count_after_observation": len(surviving),
            }
        )
        alternate_pool.remove(best[1])
    if surviving != [(2, 0)]:
        _fail("observation-derived primitive selector did not identify the exact program")
    selected_rewrite_trigger, selected_capacity_offset = surviving[0]

    expressions = [
        {
            "compatibility_name": "resource_load",
            "expression": ["SUM_VECTOR", "RESOURCE_COUNT_VECTOR"],
        },
        {
            "compatibility_name": "capacity_slack",
            "expression": [
                "SUBTRACT",
                "CAPACITY_LIMIT",
                ["SUM_VECTOR", "RESOURCE_COUNT_VECTOR"],
            ],
        },
        {
            "compatibility_name": "selected_class_count",
            "expression": [
                "SELECT_CLASS_COUNT",
                "RESOURCE_COUNT_VECTOR",
                "OPERATION_CLASS",
            ],
        },
        {
            "compatibility_name": "rewrite_on_next",
            "expression": [
                "EQUALS",
                ["SELECT_CLASS_COUNT", "RESOURCE_COUNT_VECTOR", "OPERATION_CLASS"],
                selected_rewrite_trigger,
            ],
        },
        {
            "compatibility_name": "post_operation_load",
            "expression": [
                "SUBTRACT_IF_REWRITE_ELSE_ADD_ONE",
                ["SUM_VECTOR", "RESOURCE_COUNT_VECTOR"],
                "rewrite_on_next",
            ],
        },
        {
            "compatibility_name": "future_repair_supply",
            "expression": [
                "COUNT_AVAILABLE_BY_CLASS",
                "AVAILABLE_OPERATION_SET",
                "OPERATION_CLASS",
            ],
        },
    ]
    proposal_payload = {
        "schema": "acfqp.lmb_reusable_primitive_proposal.v42",
        "schema_version": SCHEMA_VERSION,
        "lmb_reusable_world_model_preregistration_id": pre.PREREGISTRATION_ID,
        "source_relations": list(pre.GENERIC_SOURCE_RELATIONS),
        "meta_operators": list(pre.GENERIC_META_OPERATORS),
        "selected_expressions": expressions,
        "candidate_program_trace": {
            "candidate_grammar": {
                "rewrite_trigger_counts": [0, 1, 2],
                "capacity_failure_offsets": [-1, 0, 1],
            },
            "initial_candidates": [list(candidate) for candidate in initial_versions],
            "surviving_after_witness_observations": [
                list(candidate) for candidate in after_witness_versions
            ],
            "adaptive_disagreement_queries": adaptive_trace,
            "selected_candidate": list(surviving[0]),
            "selection_rule": "MAX_PARTITION_THEN_BALANCE_THEN_SEED_DECISION_TILE_V1",
        },
        "source_observation_rows": rows,
        "source_support_keys": [list(key) for key in sorted(support_keys)],
        "offline_source_transition_label_count": len(rows),
        "source_generation_witness_used_only_to_schedule_offline_observations": True,
        "heldout_generation_witness_accessed": False,
        "query_value_reward_or_target_policy_input_present": False,
        "all_source_rows_match_proposed_transition_law": True,
        "proposal_acceptance_authority": "EXACT_SOURCE_OBSERVATION_CONSISTENCY_V1",
    }
    proposal = {
        **proposal_payload,
        "lmb_reusable_primitive_proposal_id": content_id(
            pre.FUTURE_DOMAINS["primitive_proposal"], proposal_payload
        ),
    }
    return proposal, support_keys


def _find_success_plan(
    kernel: LMBKernel, state: LMBState
) -> tuple[tuple[LMBAction, ...], int, int]:
    """Model-only feasibility DP with deterministic primitive-based ordering."""

    memo: dict[LMBState, tuple[LMBAction, ...] | None] = {}
    evaluations = 0
    peak_entries = 0

    def solve(current: LMBState) -> tuple[LMBAction, ...] | None:
        nonlocal evaluations, peak_entries
        if current.status is LMBStatus.SUCCESS:
            return ()
        if current.status is LMBStatus.FAILURE:
            return None
        if current in memo:
            return memo[current]
        candidates = []
        for action in kernel.actions(current):
            successor = _predict_transition(kernel, current, action)
            evaluations += 1
            rewrite = sum(successor.buffer) < sum(current.buffer)
            newly_available = sum(
                1
                for tile in range(kernel.tile_count)
                if not successor.removed_mask & (1 << tile)
                and all(
                    successor.removed_mask & (1 << blocker)
                    for blocker in kernel.blockers[tile]
                )
            )
            candidates.append(
                (
                    (
                        -int(rewrite),
                        sum(successor.buffer),
                        -newly_available,
                        action.tile,
                    ),
                    action,
                    successor,
                )
            )
        for _rank, action, successor in sorted(candidates):
            suffix = solve(successor)
            if suffix is not None:
                memo[current] = (action, *suffix)
                peak_entries = max(peak_entries, len(memo))
                return memo[current]
        memo[current] = None
        peak_entries = max(peak_entries, len(memo))
        return None

    plan = solve(state)
    if plan is None:
        _fail("proposed abstract model found no successful continuation")
    return plan, evaluations, peak_entries


def _certificate(
    *,
    proposal_id: str,
    arm: str,
    episode_seed: int,
    decision_index: int,
    state: LMBState,
    action: LMBAction,
    support: list[Any],
    status: str,
    failed_certificate_id: str | None,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.lmb_receding_model_certificate.v42",
        "schema_version": SCHEMA_VERSION,
        "lmb_reusable_world_model_preregistration_id": pre.PREREGISTRATION_ID,
        "lmb_reusable_primitive_proposal_id": proposal_id,
        "acquisition_arm": arm,
        "episode_seed": episode_seed,
        "decision_index": decision_index,
        "state": _state_document(state),
        "action": _action_document(action),
        "support_key": support,
        "planning_horizon": pre.RECEDING_HORIZON,
        "kernel_step_during_planning": False,
        "status": status,
        "failed_certificate_id": failed_certificate_id,
    }
    return {
        **payload,
        "certificate_id": content_id(
            pre.FUTURE_DOMAINS["local_ground_distinction"], payload
        ),
    }


def _episode(
    *,
    seed: int,
    arm: str,
    proposal: dict[str, Any],
    source_support_keys: set[tuple[int, int, bool]],
) -> dict[str, Any]:
    kernel, _discarded_target_witness = generate_solvable_lmb(
        tile_count=pre.TILE_COUNT,
        type_count=pre.TYPE_COUNT,
        capacity=pre.BUFFER_CAPACITY,
        max_layers=pre.MAX_LAYERS,
        seed=seed,
    )
    # The target witness is deliberately never read after construction.
    del _discarded_target_witness
    state = kernel.initial_distribution()[0][1]
    generic_overlay: set[tuple[int, int, bool]] = set()
    context_overlay: set[str] = set()
    decisions: list[dict[str, Any]] = []
    local_label_count = 0
    execution_step_count = 0
    abstract_evaluations = 0
    certificate_evaluations = 0
    peak_dp_entries = 0

    while state.status is LMBStatus.ACTIVE:
        decision_index = len(decisions)
        plan, plan_evaluations, plan_peak = _find_success_plan(kernel, state)
        abstract_evaluations += plan_evaluations
        peak_dp_entries = max(peak_dp_entries, plan_peak)
        action = plan[0]
        predicted = _predict_transition(kernel, state, action)
        generic_key = _support_key(kernel, state, action)
        exact_key = _exact_context_key(state, action)
        support = list(generic_key) if arm == "STRUCTURAL_META_PRIOR" else [exact_key]
        supported = (
            generic_key in source_support_keys or generic_key in generic_overlay
            if arm == "STRUCTURAL_META_PRIOR"
            else exact_key in context_overlay
        )
        initial_status = "CERTIFIED_MODEL_SUPPORT" if supported else "FAILED_MISSING_SUPPORT"
        initial_certificate = _certificate(
            proposal_id=proposal["lmb_reusable_primitive_proposal_id"],
            arm=arm,
            episode_seed=seed,
            decision_index=decision_index,
            state=state,
            action=action,
            support=support,
            status=initial_status,
            failed_certificate_id=None,
        )
        certificate_evaluations += 1
        local_distinction = None
        exact_outcome = None
        final_certificate = initial_certificate
        replan_after_local_distinction = False

        if not supported:
            exact_outcome = kernel.step(state, action)[0]
            local_label_count += 1
            distinction_payload = {
                "schema": "acfqp.lmb_local_ground_distinction.v42",
                "schema_version": SCHEMA_VERSION,
                "lmb_reusable_world_model_preregistration_id": pre.PREREGISTRATION_ID,
                "lmb_reusable_primitive_proposal_id": proposal[
                    "lmb_reusable_primitive_proposal_id"
                ],
                "failed_certificate_id": initial_certificate["certificate_id"],
                "acquisition_arm": arm,
                "episode_seed": seed,
                "decision_index": decision_index,
                "state": _state_document(state),
                "action": _action_document(action),
                "support_key": support,
                "observed_successor": _state_document(exact_outcome.next_state),
                "observed_failure": exact_outcome.failure,
                "observed_terminal": exact_outcome.terminal,
                "acquired_after_failed_certificate": True,
                "acquisition_scope": "EPISODE_IMMUTABLE_OVERLAY",
            }
            local_distinction = {
                **distinction_payload,
                "local_ground_distinction_id": content_id(
                    pre.FUTURE_DOMAINS["local_ground_distinction"],
                    distinction_payload,
                ),
            }
            if arm == "STRUCTURAL_META_PRIOR":
                generic_overlay.add(generic_key)
            else:
                context_overlay.add(exact_key)
            replanned, replan_evaluations, replan_peak = _find_success_plan(kernel, state)
            abstract_evaluations += replan_evaluations
            peak_dp_entries = max(peak_dp_entries, replan_peak)
            if not replanned or replanned[0] != action:
                _fail("local distinction changed the deterministic model plan")
            replan_after_local_distinction = True
            final_certificate = _certificate(
                proposal_id=proposal["lmb_reusable_primitive_proposal_id"],
                arm=arm,
                episode_seed=seed,
                decision_index=decision_index,
                state=state,
                action=action,
                support=support,
                status="CERTIFIED_AFTER_LOCAL_DISTINCTION",
                failed_certificate_id=initial_certificate["certificate_id"],
            )
            certificate_evaluations += 1

        # A failed-certificate query is the same physical transition as the
        # environment execution.  Certified steps execute once and are not
        # converted into new labels.
        actual_outcome = exact_outcome or kernel.step(state, action)[0]
        execution_step_count += 1
        if actual_outcome.next_state != predicted:
            _fail("executed target transition differs from the proposed model")
        decisions.append(
            {
                "decision_index": decision_index,
                "source_state": _state_document(state),
                "receding_plan_prefix": [
                    _action_document(item) for item in plan[: pre.RECEDING_HORIZON]
                ],
                "selected_action": _action_document(action),
                "predicted_successor": _state_document(predicted),
                "initial_certificate": initial_certificate,
                "local_ground_distinction": local_distinction,
                "replanned_after_local_distinction": replan_after_local_distinction,
                "final_certificate": final_certificate,
                "executed_successor": _state_document(actual_outcome.next_state),
                "model_matches_execution": True,
                "kernel_step_during_planning": False,
            }
        )
        state = actual_outcome.next_state

    if state.status is not LMBStatus.SUCCESS or execution_step_count != pre.TILE_COUNT:
        _fail("held-out episode did not clear the full registered board")
    if local_label_count > pre.MAX_LOCAL_DISTINCTION_ROWS_PER_EPISODE:
        _fail("episode exceeded the preregistered local distinction cap")
    payload = {
        "schema": "acfqp.lmb_receding_episode.v42",
        "schema_version": SCHEMA_VERSION,
        "lmb_reusable_world_model_preregistration_id": pre.PREREGISTRATION_ID,
        "lmb_reusable_primitive_proposal_id": proposal[
            "lmb_reusable_primitive_proposal_id"
        ],
        "acquisition_arm": arm,
        "episode_seed": seed,
        "instance_specification": {
            "tile_count": pre.TILE_COUNT,
            "type_count": pre.TYPE_COUNT,
            "buffer_capacity": pre.BUFFER_CAPACITY,
            "max_layers": pre.MAX_LAYERS,
        },
        "initial_state": _state_document(kernel.initial_distribution()[0][1]),
        "decisions": decisions,
        "terminal_state": _state_document(state),
        "terminal_status": state.status.value,
        "full_board_cleared": True,
        "target_generation_witness_access_count": 0,
        "target_local_distinction_label_count": local_label_count,
        "execution_environment_step_count": execution_step_count,
        "abstract_transition_evaluation_count": abstract_evaluations,
        "certificate_evaluation_count": certificate_evaluations,
        "peak_dynamic_programming_cache_entries": peak_dp_entries,
        "sample_labels_and_planning_compute_separate": True,
    }
    return {
        **payload,
        "lmb_receding_episode_id": content_id(
            pre.FUTURE_DOMAINS["episode"], payload
        ),
    }


def build_lmb_reusable_world_model_campaign_document_v42() -> dict[str, Any]:
    preregistration = pre.freeze_lmb_reusable_world_model_preregistration_v42()
    pre.verify_lmb_reusable_world_model_preregistration_v42(preregistration)
    source_binding = _source_binding()
    proposal, source_support_keys = _source_proposal()
    episodes = [
        _episode(
            seed=seed,
            arm=arm,
            proposal=proposal,
            source_support_keys=source_support_keys,
        )
        for arm in pre.ACQUISITION_ARMS
        for seed in pre.HELDOUT_EPISODE_SEEDS
    ]
    structural = [
        row for row in episodes if row["acquisition_arm"] == "STRUCTURAL_META_PRIOR"
    ]
    no_prior = [
        row
        for row in episodes
        if row["acquisition_arm"] == "STRICT_NO_PRIOR_CONTEXT_TABLE"
    ]
    structural_labels = sum(row["target_local_distinction_label_count"] for row in structural)
    no_prior_labels = sum(row["target_local_distinction_label_count"] for row in no_prior)
    if not 0 < structural_labels < no_prior_labels:
        _fail("matched acquisition arms did not exhibit the preregistered label ordering")
    matched_terminal = [row["terminal_status"] for row in structural] == [
        row["terminal_status"] for row in no_prior
    ]
    if not matched_terminal:
        _fail("matched acquisition arms ended differently")
    label_fraction = Fraction(structural_labels, no_prior_labels)
    payload = {
        "schema": "acfqp.lmb_reusable_world_model_campaign.v42",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "lmb_reusable_world_model_preregistration_id": pre.PREREGISTRATION_ID,
        "v41_campaign_id": pre.V41_CAMPAIGN_ID,
        "v41_verification_id": pre.V41_VERIFICATION_ID,
        "source_binding": source_binding,
        "primitive_proposal": proposal,
        "episodes": episodes,
        "matched_summary": {
            "heldout_episode_count_per_arm": len(pre.HELDOUT_EPISODE_SEEDS),
            "structural_meta_prior_target_label_count": structural_labels,
            "strict_no_prior_target_label_count": no_prior_labels,
            "target_label_fraction": {
                "numerator": label_fraction.numerator,
                "denominator": label_fraction.denominator,
            },
            "structural_meta_prior_execution_step_count": sum(
                row["execution_environment_step_count"] for row in structural
            ),
            "strict_no_prior_execution_step_count": sum(
                row["execution_environment_step_count"] for row in no_prior
            ),
            "structural_meta_prior_abstract_compute_events": sum(
                row["abstract_transition_evaluation_count"]
                + row["certificate_evaluation_count"]
                for row in structural
            ),
            "strict_no_prior_abstract_compute_events": sum(
                row["abstract_transition_evaluation_count"]
                + row["certificate_evaluation_count"]
                for row in no_prior
            ),
            "all_episodes_completed": all(row["full_board_cleared"] for row in episodes),
            "matched_terminal_statuses": matched_terminal,
            "every_local_label_has_failed_certificate": all(
                decision["local_ground_distinction"] is None
                or decision["local_ground_distinction"]["failed_certificate_id"]
                == decision["initial_certificate"]["certificate_id"]
                for row in episodes
                for decision in row["decisions"]
            ),
            "planning_kernel_step_count": 0,
            "labels_and_compute_axes_not_collapsed": True,
        },
        "cross_domain_general_sample_efficiency_claimed": False,
        "broad_iid_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **payload,
        "lmb_reusable_world_model_campaign_id": content_id(
            pre.FUTURE_DOMAINS["campaign"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LMBReusableWorldModelCampaignV42:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("LMB campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("LMB campaign bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "lmb_reusable_world_model_campaign_id"
        }
        if (
            document.get("lmb_reusable_world_model_campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("LMB campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError("LMB campaign is not an object")
        return document


def run_lmb_reusable_world_model_campaign_v42(
    output_path: str | Path | None = None,
) -> LMBReusableWorldModelCampaignV42:
    document = build_lmb_reusable_world_model_campaign_document_v42()
    raw = canonical_json_bytes(document)
    identity = document["lmb_reusable_world_model_campaign_id"]
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and (
        identity != EXPECTED_CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen LMB campaign changed")
    if output_path is not None:
        Path(output_path).write_bytes(raw)
    return LMBReusableWorldModelCampaignV42(_ISSUER, raw, identity)


def verify_lmb_reusable_world_model_campaign_v42(
    value: LMBReusableWorldModelCampaignV42,
) -> LMBReusableWorldModelCampaignV42:
    if type(value) is not LMBReusableWorldModelCampaignV42:
        _fail("LMB campaign rejects foreign values")
    value.__post_init__()
    expected = canonical_json_bytes(build_lmb_reusable_world_model_campaign_document_v42())
    if value.canonical_bytes != expected:
        _fail("LMB campaign replay changed")
    return value


__all__ = (
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "LMBReusableWorldModelCampaignV42",
    "build_lmb_reusable_world_model_campaign_document_v42",
    "run_lmb_reusable_world_model_campaign_v42",
    "verify_lmb_reusable_world_model_campaign_v42",
)
