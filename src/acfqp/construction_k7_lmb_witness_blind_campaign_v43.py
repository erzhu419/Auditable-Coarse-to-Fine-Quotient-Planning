"""Witness-blind source acquisition and cross-cardinality LMB reuse for V43."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_lmb_witness_blind_preregistration_v43 as pre
from acfqp.domains.matching_buffer import (
    LMBAction,
    LMBKernel,
    LMBState,
    LMBStatus,
    generate_solvable_lmb,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = "construction_k7_lmb_witness_blind_campaign_v43"
EXPECTED_CAMPAIGN_ID = "d435246de035efd4081922b8d6995f1dceb36216bf08cb5766a76ed5dfdbe00d"
EXPECTED_CANONICAL_BYTE_COUNT = 459_730
EXPECTED_CANONICAL_SHA256 = "918718cef97e62fb4445e346f3e0a30431dcbc945e6eaeb20cc9a7ae7231a443"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_lmb_witness_blind_preregistration_v43.py",
    "src/acfqp/domains/matching_buffer.py",
)


class ConstructionK7LMBWitnessBlindCampaignV43Error(ValueError):
    """The exploration, proposal, certificate, plan, or accounting changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LMBWitnessBlindCampaignV43Error(message)


def _state(state: LMBState) -> dict[str, Any]:
    return {
        "removed_mask": state.removed_mask,
        "buffer_counts": list(state.buffer),
        "status": state.status.value,
    }


def _action(action: LMBAction) -> dict[str, int]:
    return {"tile": action.tile}


def _model_step(kernel: LMBKernel, state: LMBState, action: LMBAction) -> LMBState:
    removed = state.removed_mask | (1 << action.tile)
    selected = kernel.tile_types[action.tile]
    counts = list(state.buffer)
    counts[selected] += 1
    if counts[selected] == 3:
        counts[selected] = 0
    load = sum(counts)
    empty = removed == (1 << kernel.tile_count) - 1
    status = (
        LMBStatus.FAILURE
        if load > kernel.capacity
        else LMBStatus.SUCCESS
        if empty
        else LMBStatus.ACTIVE
    )
    return LMBState(removed, tuple(counts), status)


def _candidate_step(
    kernel: LMBKernel,
    state: LMBState,
    action: LMBAction,
    candidate: tuple[int, int],
) -> LMBState | None:
    removed = state.removed_mask | (1 << action.tile)
    selected = kernel.tile_types[action.tile]
    counts = list(state.buffer)
    counts[selected] = 0 if counts[selected] == candidate[0] else counts[selected] + 1
    if counts[selected] >= 3:
        return None
    load = sum(counts)
    empty = removed == (1 << kernel.tile_count) - 1
    status = (
        LMBStatus.FAILURE
        if load > kernel.capacity + candidate[1]
        else LMBStatus.SUCCESS
        if empty
        else LMBStatus.ACTIVE
    )
    return LMBState(removed, tuple(counts), status)


def _support(kernel: LMBKernel, state: LMBState, action: LMBAction) -> tuple[int, int, bool]:
    return (
        state.buffer[kernel.tile_types[action.tile]],
        sum(state.buffer),
        sum(state.buffer) == kernel.capacity,
    )


def _context(state: LMBState, action: LMBAction) -> str:
    return content_id(
        pre.FUTURE_DOMAINS["distinction"],
        {"role": "EXACT_CONTEXT", "state": _state(state), "action": _action(action)},
    )


def _source_binding() -> dict[str, Any]:
    facts = []
    for relative in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        facts.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return {
        "schema": "acfqp.lmb_witness_blind_source_binding.v43",
        "preregistration_id": pre.PREREGISTRATION_ID,
        "v42_campaign_id": pre.V42_CAMPAIGN_ID,
        "v42_verification_id": pre.V42_VERIFICATION_ID,
        "source_facts": facts,
        "full_producer_source_closure_claimed": False,
        "producer_free_verification_required": True,
    }


def _prediction_key(value: LMBState | None) -> str:
    return repr(None if value is None else _state(value))


def _source_proposal() -> tuple[dict[str, Any], set[tuple[int, int, bool]]]:
    surviving = list(pre.CANDIDATES)
    supports: set[tuple[int, int, bool]] = set()
    rows = []
    episode_closures = []
    for seed in pre.SOURCE_SEEDS:
        if len(surviving) == 1:
            break
        kernel, source_witness = generate_solvable_lmb(seed=seed, **pre.SOURCE_SPEC)
        # The returned witness is destroyed without reading any field.
        del source_witness
        state = kernel.initial_distribution()[0][1]
        episode_start_versions = len(surviving)
        episode_labels = 0
        while state.status is LMBStatus.ACTIVE and len(surviving) > 1:
            ranked = []
            for action in kernel.actions(state):
                groups: dict[str, int] = {}
                for candidate in surviving:
                    key = _prediction_key(_candidate_step(kernel, state, action, candidate))
                    groups[key] = groups.get(key, 0) + 1
                score = (
                    len(groups),
                    -max(groups.values()),
                    sum(state.buffer),
                    state.buffer[kernel.tile_types[action.tile]],
                    -action.tile,
                )
                ranked.append((score, action))
            _score, selected_action = max(ranked)
            before = tuple(surviving)
            outcome = kernel.step(state, selected_action)[0]
            surviving = [
                candidate
                for candidate in surviving
                if _candidate_step(kernel, state, selected_action, candidate)
                == outcome.next_state
            ]
            if not surviving:
                _fail("witness-blind observation eliminated every candidate")
            key = _support(kernel, state, selected_action)
            supports.add(key)
            rows.append(
                {
                    "source_seed": seed,
                    "source_decision_index": episode_labels,
                    "source_state": _state(state),
                    "legal_action_tiles": [action.tile for action in kernel.actions(state)],
                    "selected_action": _action(selected_action),
                    "exploration_score": list(_score),
                    "candidate_count_before": len(before),
                    "candidate_count_after": len(surviving),
                    "observed_successor": _state(outcome.next_state),
                    "observed_failure": outcome.failure,
                    "observed_terminal": outcome.terminal,
                    "support_key": list(key),
                    "source_generation_witness_accessed": False,
                }
            )
            episode_labels += 1
            state = outcome.next_state
            if len(rows) > pre.MAX_SOURCE_LABELS:
                _fail("source exploration exceeded the preregistered label cap")
        episode_closures.append(
            {
                "source_seed": seed,
                "candidate_count_at_start": episode_start_versions,
                "transition_label_count": episode_labels,
                "terminal_status": state.status.value,
                "candidate_count_at_close": len(surviving),
            }
        )
    if surviving != [(2, 0)]:
        _fail("witness-blind exploration did not identify the exact program")
    expressions = [
        ["resource_load", ["SUM_VECTOR", "RESOURCE_COUNT_VECTOR"]],
        ["capacity_slack", ["SUBTRACT", "CAPACITY_LIMIT", "resource_load"]],
        ["selected_class_count", ["SELECT_CLASS_COUNT", "RESOURCE_COUNT_VECTOR", "OPERATION_CLASS"]],
        ["rewrite_on_next", ["EQUALS", "selected_class_count", surviving[0][0]]],
        ["post_operation_load", ["REWRITE_OR_INCREMENT", "resource_load", "rewrite_on_next"]],
        ["future_repair_supply", ["COUNT_AVAILABLE_BY_CLASS", "AVAILABLE_OPERATION_SET", "OPERATION_CLASS"]],
    ]
    payload = {
        "schema": "acfqp.lmb_witness_blind_proposal.v43",
        "schema_version": SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "source_instance_specification": pre.SOURCE_SPEC,
        "initial_candidate_programs": [list(row) for row in pre.CANDIDATES],
        "exploration_score_lexicographic": list(pre.EXPLORATION_SCORE),
        "source_observation_rows": rows,
        "source_episode_closures": episode_closures,
        "source_support_keys": [list(row) for row in sorted(supports)],
        "selected_candidate": list(surviving[0]),
        "compiled_shared_primitives": expressions,
        "offline_source_transition_label_count": len(rows),
        "source_generation_witness_access_count": 0,
        "target_generation_witness_access_count": 0,
        "query_value_reward_or_policy_input_present": False,
        "status": "UNIQUE_WITNESS_BLIND_OBSERVATION_CONSISTENT_PROGRAM",
    }
    return (
        {
            **payload,
            "proposal_id": content_id(pre.FUTURE_DOMAINS["proposal"], payload),
        },
        supports,
    )


def _plan(kernel: LMBKernel, state: LMBState) -> tuple[tuple[LMBAction, ...], int, int]:
    memo: dict[LMBState, tuple[LMBAction, ...] | None] = {}
    evaluations = 0
    peak = 0

    def solve(current: LMBState) -> tuple[LMBAction, ...] | None:
        nonlocal evaluations, peak
        if current.status is LMBStatus.SUCCESS:
            return ()
        if current.status is LMBStatus.FAILURE:
            return None
        if current in memo:
            return memo[current]
        candidates = []
        for action in kernel.actions(current):
            successor = _model_step(kernel, current, action)
            evaluations += 1
            rewrite = sum(successor.buffer) < sum(current.buffer)
            available = sum(
                1
                for tile in range(kernel.tile_count)
                if not successor.removed_mask & (1 << tile)
                and all(
                    successor.removed_mask & (1 << blocker)
                    for blocker in kernel.blockers[tile]
                )
            )
            candidates.append(
                ((-int(rewrite), sum(successor.buffer), -available, action.tile), action, successor)
            )
        for _rank, action, successor in sorted(candidates):
            suffix = solve(successor)
            if suffix is not None:
                memo[current] = (action, *suffix)
                peak = max(peak, len(memo))
                return memo[current]
        memo[current] = None
        peak = max(peak, len(memo))
        return None

    result = solve(state)
    if result is None:
        _fail("abstract model found no successful cross-cardinality continuation")
    return result, evaluations, peak


def _certificate(
    proposal_id: str,
    arm: str,
    seed: int,
    index: int,
    state: LMBState,
    action: LMBAction,
    support_key: list[Any],
    status: str,
    failed_id: str | None,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.lmb_witness_blind_certificate.v43",
        "schema_version": SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "proposal_id": proposal_id,
        "arm": arm,
        "episode_seed": seed,
        "decision_index": index,
        "state": _state(state),
        "action": _action(action),
        "support_key": support_key,
        "status": status,
        "failed_certificate_id": failed_id,
        "kernel_step_during_planning": False,
    }
    return {
        **payload,
        "certificate_id": content_id(pre.FUTURE_DOMAINS["distinction"], payload),
    }


def _episode(
    seed: int,
    arm: str,
    proposal_id: str,
    source_supports: set[tuple[int, int, bool]],
) -> dict[str, Any]:
    kernel, target_witness = generate_solvable_lmb(seed=seed, **pre.TARGET_SPEC)
    del target_witness
    state = kernel.initial_distribution()[0][1]
    generic_overlay: set[tuple[int, int, bool]] = set()
    context_overlay: set[str] = set()
    decisions = []
    labels = 0
    abstract_compute = 0
    certificate_compute = 0
    peak = 0
    while state.status is LMBStatus.ACTIVE:
        index = len(decisions)
        plan, evaluations, plan_peak = _plan(kernel, state)
        abstract_compute += evaluations
        peak = max(peak, plan_peak)
        action = plan[0]
        predicted = _model_step(kernel, state, action)
        generic_key = _support(kernel, state, action)
        context_key = _context(state, action)
        support_key = list(generic_key) if arm == pre.ARMS[0] else [context_key]
        supported = (
            generic_key in source_supports or generic_key in generic_overlay
            if arm == pre.ARMS[0]
            else context_key in context_overlay
        )
        initial = _certificate(
            proposal_id,
            arm,
            seed,
            index,
            state,
            action,
            support_key,
            "CERTIFIED_MODEL_SUPPORT" if supported else "FAILED_MISSING_SUPPORT",
            None,
        )
        certificate_compute += 1
        distinction = None
        exact = None
        final = initial
        replanned = False
        if not supported:
            exact = kernel.step(state, action)[0]
            labels += 1
            distinction_payload = {
                "schema": "acfqp.lmb_witness_blind_local_distinction.v43",
                "schema_version": SCHEMA_VERSION,
                "preregistration_id": pre.PREREGISTRATION_ID,
                "proposal_id": proposal_id,
                "failed_certificate_id": initial["certificate_id"],
                "arm": arm,
                "episode_seed": seed,
                "decision_index": index,
                "state": _state(state),
                "action": _action(action),
                "support_key": support_key,
                "observed_successor": _state(exact.next_state),
                "observed_failure": exact.failure,
                "observed_terminal": exact.terminal,
                "acquired_after_failed_certificate": True,
            }
            distinction = {
                **distinction_payload,
                "distinction_id": content_id(
                    pre.FUTURE_DOMAINS["distinction"], distinction_payload
                ),
            }
            if arm == pre.ARMS[0]:
                generic_overlay.add(generic_key)
            else:
                context_overlay.add(context_key)
            repeated, evaluations, repeated_peak = _plan(kernel, state)
            abstract_compute += evaluations
            peak = max(peak, repeated_peak)
            if repeated[0] != action:
                _fail("local distinction changed the deterministic selected action")
            replanned = True
            final = _certificate(
                proposal_id,
                arm,
                seed,
                index,
                state,
                action,
                support_key,
                "CERTIFIED_AFTER_LOCAL_DISTINCTION",
                initial["certificate_id"],
            )
            certificate_compute += 1
        outcome = exact or kernel.step(state, action)[0]
        if outcome.next_state != predicted:
            _fail("held-out execution differs from the synthesized world model")
        decisions.append(
            {
                "decision_index": index,
                "source_state": _state(state),
                "plan_prefix": [_action(row) for row in plan[: pre.RECEDING_HORIZON]],
                "selected_action": _action(action),
                "predicted_successor": _state(predicted),
                "initial_certificate": initial,
                "local_distinction": distinction,
                "replanned_after_local_distinction": replanned,
                "final_certificate": final,
                "executed_successor": _state(outcome.next_state),
                "model_matches_execution": True,
            }
        )
        state = outcome.next_state
    if (
        state.status is not LMBStatus.SUCCESS
        or len(decisions) != pre.TARGET_SPEC["tile_count"]
        or labels > pre.MAX_TARGET_LOCAL_LABELS_PER_EPISODE
    ):
        _fail("cross-cardinality episode did not close within its frozen bounds")
    payload = {
        "schema": "acfqp.lmb_cross_cardinality_episode.v43",
        "schema_version": SCHEMA_VERSION,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "proposal_id": proposal_id,
        "arm": arm,
        "episode_seed": seed,
        "instance_specification": pre.TARGET_SPEC,
        "decisions": decisions,
        "terminal_state": _state(state),
        "full_board_cleared": True,
        "source_generation_witness_access_count": 0,
        "target_generation_witness_access_count": 0,
        "target_local_distinction_label_count": labels,
        "execution_environment_step_count": len(decisions),
        "abstract_transition_evaluation_count": abstract_compute,
        "certificate_evaluation_count": certificate_compute,
        "peak_dynamic_program_cache_entries": peak,
        "labels_steps_and_compute_separate": True,
    }
    return {
        **payload,
        "episode_id": content_id(pre.FUTURE_DOMAINS["episode"], payload),
    }


def build_lmb_witness_blind_campaign_document_v43() -> dict[str, Any]:
    registration = pre.freeze_lmb_witness_blind_preregistration_v43()
    pre.verify_lmb_witness_blind_preregistration_v43(registration)
    proposal, supports = _source_proposal()
    episodes = [
        _episode(seed, arm, proposal["proposal_id"], supports)
        for arm in pre.ARMS
        for seed in pre.HELDOUT_SEEDS
    ]
    structural = episodes[: len(pre.HELDOUT_SEEDS)]
    control = episodes[len(pre.HELDOUT_SEEDS) :]
    structural_labels = sum(row["target_local_distinction_label_count"] for row in structural)
    control_labels = sum(row["target_local_distinction_label_count"] for row in control)
    if not 0 < structural_labels < control_labels:
        _fail("cross-cardinality matched target label ordering changed")
    ratio = Fraction(structural_labels, control_labels)
    payload = {
        "schema": "acfqp.lmb_witness_blind_campaign.v43",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "v41_campaign_id": pre.V41_CAMPAIGN_ID,
        "v41_verification_id": pre.V41_VERIFICATION_ID,
        "v42_campaign_id": pre.V42_CAMPAIGN_ID,
        "v42_verification_id": pre.V42_VERIFICATION_ID,
        "source_binding": _source_binding(),
        "proposal": proposal,
        "episodes": episodes,
        "summary": {
            "offline_source_transition_label_count": proposal[
                "offline_source_transition_label_count"
            ],
            "structural_meta_prior_target_label_count": structural_labels,
            "strict_no_prior_target_label_count": control_labels,
            "target_label_fraction": ratio,
            "heldout_episode_count_per_arm": len(pre.HELDOUT_SEEDS),
            "execution_environment_step_count_per_arm": sum(
                row["execution_environment_step_count"] for row in structural
            ),
            "structural_abstract_compute_events": sum(
                row["abstract_transition_evaluation_count"]
                + row["certificate_evaluation_count"]
                for row in structural
            ),
            "control_abstract_compute_events": sum(
                row["abstract_transition_evaluation_count"]
                + row["certificate_evaluation_count"]
                for row in control
            ),
            "all_episodes_completed": all(row["full_board_cleared"] for row in episodes),
            "all_local_labels_follow_failed_certificates": all(
                decision["local_distinction"] is None
                or decision["local_distinction"]["failed_certificate_id"]
                == decision["initial_certificate"]["certificate_id"]
                for episode in episodes
                for decision in episode["decisions"]
            ),
            "source_generation_witness_access_count": 0,
            "target_generation_witness_access_count": 0,
            "planning_kernel_step_count": 0,
            "labels_steps_and_compute_separate": True,
        },
        "verified_scope_candidate": "REGISTERED_WITNESS_BLIND_LMB_CROSS_CARDINALITY_WORKLOAD_V43",
        "open_ended_operator_invention_claimed": False,
        "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": content_id(pre.FUTURE_DOMAINS["campaign"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LMBWitnessBlindCampaignV43:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V43 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V43 campaign bytes changed")
        payload = {key: value for key, value in document.items() if key != "campaign_id"}
        if (
            document.get("campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
        ):
            _fail("V43 campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError("V43 campaign is not an object")
        return value


def run_lmb_witness_blind_campaign_v43(
    output_path: str | Path | None = None,
) -> LMBWitnessBlindCampaignV43:
    document = build_lmb_witness_blind_campaign_document_v43()
    raw = canonical_json_bytes(document)
    identity = document["campaign_id"]
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and (
        identity != EXPECTED_CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V43 campaign changed")
    if output_path is not None:
        Path(output_path).write_bytes(raw)
    return LMBWitnessBlindCampaignV43(_ISSUER, raw, identity)


__all__ = (
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "LMBWitnessBlindCampaignV43",
    "build_lmb_witness_blind_campaign_document_v43",
    "run_lmb_witness_blind_campaign_v43",
)
